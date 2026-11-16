"""Who started a thread, as a frame id the trace actually holds.

A `threading.Thread` body is a root: its caller is the stdlib bootstrap on
the new thread, so parentage never reaches the `start` or `submit` that
created it. The audit hook only counts those creations. This log records,
per thread the run actually started through `Thread.start`, the tracer
serial events use, the thread's name, and the recorded frame that asked
for it.

The OS ident is not stored. It is recycled, and `events.thread_id` is the
tracer serial minted in `_assign_thread_serial`, not `get_ident()`. The
serial is minted on the new thread's first monitoring callback, which is
`_bootstrap`, before `_bootstrap_inner` publishes the Thread. The Thread
object is already the `self` of that `_bootstrap` frame, so the link is
made there, against the object the parent registered before `start`
returned. Calling `current_thread()` here would insert a `_DummyThread`.
"""
import os
import sys
import threading
import weakref


_SELF = os.path.realpath(__file__)
_THREADING = os.path.realpath(threading.__file__)


def _norm(filename: str) -> str:
    return filename.replace("\\", "/")


def _same_file(filename: str, target: str) -> bool:
    try:
        return os.path.realpath(filename) == target
    except OSError:
        return False


def _is_start_machinery(filename: str) -> bool:
    """Frames that sit between the user's call and the new thread.

    `Thread.start` itself, and `Executor.submit`'s path through
    `concurrent.futures`, are not the caller `tree` should name. This
    module is the wrapper around `start` and is not that caller either.
    """
    if _same_file(filename, _SELF) or _same_file(filename, _THREADING):
        return True
    norm = _norm(filename)
    return ("/concurrent/futures/" in norm
            or norm.endswith("/concurrent/futures.py"))


def _starter_frame(tracer) -> int | None:
    """The recorded frame that called `start` or `submit`, or None.

    The nearest frame outside the start machinery is the caller. It counts
    only when this recorder opened it: a frame that ran before tracing, or
    in a C extension, or in code this run did not trace, is not a frame id
    the trace holds, and a further-out frame is a different call.
    """
    tls = tracer._tls
    frame = sys._getframe()
    while frame is not None:
        if not _is_start_machinery(frame.f_code.co_filename):
            entry = tls.live.get(id(frame))
            if entry is not None and entry[1] is frame.f_code:
                fid = entry[0]
                if type(fid) is int:
                    return fid
            return None
        frame = frame.f_back
    return None


def _plain_name(thread) -> str | None:
    """The thread's name as a plain str, or None if it cannot be read.

    Read on the parent, before `start`, so a name the child changes later
    is not what the starter asked for. A failing `name` must not stop the
    thread from starting.
    """
    try:
        name = thread.name
    except BaseException:
        return None
    if type(name) is not str:
        try:
            name = str.__str__(name)
        except BaseException:
            return None
    if type(name) is not str or name == "":
        return None
    return name


def _is_real_thread(obj) -> bool:
    try:
        if isinstance(obj, threading._DummyThread):
            return False
        return isinstance(obj, threading.Thread)
    except BaseException:
        return False


def _born_thread():
    """The Thread object whose serial is being minted, or None.

    Once the thread is in `_active`, that entry is the Thread. The mint
    happens earlier, inside `_bootstrap`, where the same object is the
    frame's `self` and `_active` does not have it yet. `current_thread()`
    is not used: on a miss it inserts a `_DummyThread`, and the monitoring
    callback that runs inside that dummy's deleter inserts another one
    which is still alive after the worker has been joined. A thread that
    did not come through `Thread` (a C extension, `_thread.start_new_thread`
    with no Thread) has neither, and stays unlinked.
    """
    try:
        current = threading._active.get(threading.get_ident())
    except BaseException:
        current = None
    if _is_real_thread(current):
        return current
    frame = sys._getframe()
    while frame is not None:
        code = frame.f_code
        if (code.co_name in ("_bootstrap", "_bootstrap_inner", "run")
                and _same_file(code.co_filename, _THREADING)):
            try:
                self_ = frame.f_locals.get("self")
            except BaseException:
                self_ = None
            if _is_real_thread(self_):
                return self_
        frame = frame.f_back
    return None


class _Log:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._records: list = []
        self._closed = False
        self._orig = None
        self._wrapped = None
        self._hook = None

    def arm(self, tracer) -> None:
        if self._orig is not None:
            return
        self._orig = threading.Thread.start
        self._hook = self._note
        tracer._thread_born = self._hook

        def wrapped(thread, /, *args, **kwargs):
            return self._call_start(tracer, thread, args, kwargs)

        self._wrapped = wrapped
        threading.Thread.start = wrapped

    def _call_start(self, tracer, thread, args, kwargs):
        # Register before the real start. The child can enter `_bootstrap`
        # and mint its serial before `start` returns, and the pending entry
        # has to be visible by then. A failure to describe the start must
        # not stop the thread: the heading then says the starter was not
        # recorded, which is what happened.
        try:
            frame = _starter_frame(tracer)
            name = _plain_name(thread)
            with self._lock:
                if not self._closed:
                    self._pending[thread] = (name, frame)
        except BaseException:
            pass
        try:
            return self._orig(thread, *args, **kwargs)
        except BaseException:
            with self._lock:
                self._pending.pop(thread, None)
            raise

    def _note(self, serial: int) -> None:
        thread = _born_thread()
        if thread is None:
            return
        with self._lock:
            if self._closed:
                return
            info = self._pending.pop(thread, None)
            if info is None:
                return
            name, frame = info
            self._records.append({
                "thread": serial,
                "name": name,
                "frame": frame,
            })

    def _restore_start(self) -> None:
        wrapped = self._wrapped
        orig = self._orig
        self._wrapped = None
        self._orig = None
        # Only if we are still the installed start. The program may have
        # replaced it; putting ours back would hide that.
        if (wrapped is not None and orig is not None
                and threading.Thread.start is wrapped):
            threading.Thread.start = orig

    def finish(self, tracer) -> list:
        # No new mint joins after this. An in-flight `_note` either holds
        # the lock (its row is in the copy) or sees `_closed` and drops,
        # so the list handed to meta is not half-updated.
        if getattr(tracer, "_thread_born", None) is self._hook:
            tracer._thread_born = None
        with self._lock:
            self._closed = True
            rows = [dict(row) for row in self._records]
        self._restore_start()
        return rows


def arm_thread_starts(tracer) -> None:
    """Wrap `Thread.start` for the duration of one recorded run."""
    log = _Log()
    # On the tracer before `arm`, so a failure mid-wrap is still undone by
    # `finish` (it is the finally that puts `Thread.start` back).
    tracer._thread_start_log = log
    try:
        log.arm(tracer)
    except BaseException:
        tracer._thread_start_log = None
        if tracer._thread_born is log._hook:
            tracer._thread_born = None
        log._restore_start()
        raise


def finish_thread_starts(tracer) -> list:
    """Restore `Thread.start` and return the `thread_starts` rows.

    Safe when `arm_thread_starts` never ran. Does not raise: finalizing a
    trace must not skip `close` because the wrapper could not be put back.
    """
    log = getattr(tracer, "_thread_start_log", None)
    tracer._thread_start_log = None
    if log is None:
        return []
    try:
        return log.finish(tracer)
    except BaseException:
        try:
            log._restore_start()
        except BaseException:
            pass
        try:
            if getattr(tracer, "_thread_born", None) is log._hook:
                tracer._thread_born = None
        except BaseException:
            pass
        return []
