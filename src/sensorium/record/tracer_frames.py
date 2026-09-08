"""Which frames the recorder decides to watch, and the identities it mints
for them.

Split out of `tracer.py` at that file's 800-line ceiling. Nothing here writes
an event: the whole file answers one question -- given a code object, a task
or a caller, is it traced, is it focused, and which fingerprint does it feed?
`Tracer` inherits the decisions as `_FrameDecisions`, so `self` is the same
object with the same locks and tables; these are one recorder's internals
across its files, not separate modules with surfaces of their own.

`_SENSORIUM_DIR` lives HERE because `_classify` is its only reader, and a
monkeypatch of the guard must therefore name THIS module -- see
`tests/test_tracer_serials.py::test_the_recorders_own_code_is_never_traced`.
"""

import sys
from fnmatch import fnmatch
from pathlib import Path

from sensorium.record.capture import plain_str
from sensorium.record.fingerprint import Fingerprint

_SENSORIUM_DIR = str(Path(__file__).resolve().parent.parent)
_CO_GENERATOR, _CO_COROUTINE, _CO_ASYNC_GENERATOR = 0x20, 0x80, 0x200
# Derived, never restated: the suspendable flag set is written down ONCE, and
# `_frame_kind` -- its only reader -- ladders over the same three flags. A flag
# added to one and not the other would silently label a new suspendable kind
# "generator".
_GENLIKE = _CO_GENERATOR | _CO_COROUTINE | _CO_ASYNC_GENERATOR


def _frame_kind(code) -> str:
    """Which kind of frame this code opens (frames.kind): every traced code
    object opens one -- arc 2 -- so this is a label, not a gate."""
    flags = code.co_flags
    if not flags & _GENLIKE:
        return "function"
    if flags & _CO_ASYNC_GENERATOR:
        return "async_generator"
    if flags & _CO_COROUTINE:
        return "coroutine"
    return "generator"


def module_name_for(file: str, root: Path) -> str | None:
    try:
        rel = Path(file).resolve().relative_to(root)
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


class FocusSpec:
    def __init__(self, entries: list[str]) -> None:
        self._entries = []
        for e in entries:
            mod, _, qual = e.partition(":")
            self._entries.append((e, mod, qual or None))

    def __bool__(self) -> bool:
        return bool(self._entries)

    def _hit(self, mod, qual, module, qualname) -> bool:
        if module != mod:
            return False
        return qual is None or qualname == qual or qualname.startswith(qual + ".")

    def matches(self, module: str | None, qualname: str) -> bool:
        if module is None:
            return False
        return any(self._hit(m, q, module, qualname) for _e, m, q in self._entries)

    def entries_matching(self, module: str | None, qualname: str) -> list[str]:
        """Every entry, as the user wrote it, that this code satisfies."""
        if module is None:
            return []
        return [e for e, m, q in self._entries if self._hit(m, q, module, qualname)]


class WindowSpec:
    """The one function whose activations bound line-level capture.

    Accepts `module:qualname` to name it unambiguously, or a bare `qualname`
    that matches that name in ANY module. The bare form is why two same-named
    functions across a `--focus` set could share a window: the old matcher was
    `qual == self.window`, a bare-string equality that a `module:qualname`
    target could never satisfy (so it silently matched nothing) and that a bare
    name matched in every module at once. `key()` still resolves bare vs
    `module:qualname` matching; its non-None result marks the window TARGET,
    whose descendants are in the window by ANCESTRY. Nothing is counted.
    """
    def __init__(self, spec: str | None) -> None:
        if spec is None:
            self._mod, self._qual = None, None
        else:
            mod, sep, qual = spec.partition(":")
            self._mod, self._qual = (mod, qual) if sep else (None, mod)

    def __bool__(self) -> bool:
        return self._qual is not None

    def key(self, module: str | None, qualname: str):
        """The window key for this code, or None if it is not the window."""
        if self._qual is None or qualname != self._qual:
            return None
        if self._mod is not None and module != self._mod:
            return None
        return (module, qualname)


class _FrameDecisions:
    """`Tracer`'s classification half. Never instantiated on its own:
    every attribute it reads is bound by `Tracer.__init__`."""

    # -- classification ----------------------------------------------------
    def _decide(self, code):
        d = self._decisions.get(id(code))
        if d is None:
            d = self._classify(code)
            self._decisions[id(code)] = d
            self._seen_codes.append(code)
        return d

    def _classify(self, code):
        file = code.co_filename
        untraced = (False, None, None, False, "function", None)
        if not file.startswith("/") or file.startswith(_SENSORIUM_DIR):
            return untraced
        p = str(Path(file).resolve())
        rootp = str(self.root)
        if not p.startswith(rootp + "/"):
            return untraced
        if ("/site-packages/" in p or "/.venv/" in p
                or p.startswith(sys.prefix) or p.startswith(sys.base_prefix)):
            return untraced
        rel = p[len(rootp) + 1:]
        if self.include and not any(fnmatch(rel, g) for g in self.include):
            return untraced
        if any(fnmatch(rel, g) for g in self.exclude):
            return untraced
        module = module_name_for(p, self.root)
        focused = self.focus.matches(module, code.co_qualname)
        win_key = self.window.key(module, code.co_qualname)
        return (True, rel, code.co_qualname, focused, _frame_kind(code),
                win_key)

    def _fp(self, tid: int) -> Fingerprint:
        # `tid` is a per-thread SERIAL (see `_TLS.thread_serial`), the same
        # identity events and frames carry, so two short-lived threads that
        # recycle one OS id still key here to distinct fingerprints.
        with self._fp_lock:
            fp = self._fps.get(tid)
            if fp is None:
                fp = self._fps[tid] = Fingerprint()
            return fp

    def _fp_for(self, tid: int, task) -> Fingerprint:
        """The fingerprint this event belongs to: the task's when it ran in
        an asyncio task, else the thread's (spec D6). One event, one
        fingerprint -- the thread's covers exactly the events with
        task_id NULL, which is what makes the two rows comparable
        separately.

        The task's entry is normally already there: `_task_serial` creates
        it when it mints the serial, so that a task minted at a YIELD,
        RESUME or LINE -- none of which reach this function -- still has a
        row. The get-or-create stays because this is the only path that
        needs the object, and a task whose serial predates that rule would
        otherwise silently lose its events.

        A thread that runs a causal event gets a row even when every one of
        them ran inside a task, so its COUNT may be 0. That zero is a fact
        with content -- "this thread ran traced code, all of it inside
        asyncio tasks" -- and it is not the same fact as having no row,
        which every reader here takes to mean the thread ran no traced code
        at all. A loop thread entered through stdlib
        (`Thread(target=asyncio.run, ...)`) is exactly that case: without
        this, it would vanish from `fingerprints()` and be counted among the
        threads that did nothing.
        """
        if task is None:
            return self._fp(tid)
        if tid not in self._fps:      # unlocked probe; the create is locked
            self._fp(tid)
        with self._fp_lock:
            fp = self._task_fps.get(task)
            if fp is None:
                fp = self._task_fps[task] = Fingerprint()
            return fp

    def _parent_of(self, tls, caller):
        """The live entry for `caller`, or None -- and None is an answer.

        A hit requires the address to be live AND the code to match. Arc 2
        opens frames for suspendable code too; while one is suspended its
        entry is not here but in `_parked` (see `_park`/`_adopt`), and a
        caller is by definition running, so this map is the right place to
        look. The code check is what keeps a recycled address from answering
        for a frame that is not the caller's."""
        if caller is None:
            return None
        entry = tls.live.get(id(caller))
        if entry is None or entry[1] is not caller.f_code:
            return None
        return entry

    def _park(self, tls, frame, entry) -> None:
        """Hand a just-suspended frame's entry to whatever thread resumes it.

        It MOVES the entry out of the suspending thread's map rather than
        copying it. A copy left behind is a second owner of one mutable
        entry, and on the very shape this exists for -- a frame opened on one
        thread and closed on another -- the copy is never removed again,
        because the thread that closes the frame can only reach its own map.
        Published after the YIELD row is written, so no other thread can
        record this frame's RESUME before the YIELD it answers.
        """
        key = id(frame)
        tls.live.pop(key, None)
        with self._parked_lock:
            self._parked[key] = entry

    def _adopt(self, tls, frame, code):
        """The parked entry for this activation, moved into THIS thread's
        live map -- or None, which is an answer.

        `entry[1] is code` is the same identity guard `_parent_of` uses, and
        it is what keeps `id(frame)` sound across the hand-off: a parked
        frame is alive (whatever suspended it holds it), so its address
        cannot be recycled while its entry waits here. `depth` and the
        parent stay exactly as the frame was opened. That is why a frame's
        rows can name two threads and both be true: the frames row keeps the
        thread that OPENED it, each event carries the thread that produced
        THAT event.
        """
        key = id(frame)
        with self._parked_lock:
            entry = self._parked.get(key)
            if entry is None or entry[1] is not code:
                return None
            del self._parked[key]
        tls.live[key] = entry
        return entry

    def _live_entry(self, tls, frame, code):
        """This activation's open-frame entry, or None: this thread's live
        map first, then the parked table for a frame another thread opened.

        A live hit whose code does not match is a stale entry at a recycled
        address, not an answer -- it must not shadow a parked entry for the
        frame that is actually running here, so it is treated as a miss."""
        entry = tls.live.get(id(frame))
        if entry is not None and entry[1] is code:
            return entry
        return self._adopt(tls, frame, code)

    def _note_caller(self, payload, caller) -> None:
        """When there is no parent frame, record WHO called instead of
        guessing: the caller's interned code if it is traced (code that
        started before recording did, so it never opened a frame), or the
        literal "untraced" (the event loop, a C callback's Python caller in a
        library, sensorium's own boot). No caller at all writes nothing,
        which is distinct from both."""
        if caller is None:
            return
        ccode = caller.f_code
        traced, _rel, cqual, _f, _kind, _w = self._decide(ccode)
        if traced:
            payload["caller_code"] = self.writer.intern_code(
                ccode.co_filename, cqual, ccode.co_firstlineno)
        else:
            payload["caller"] = "untraced"

    def _bind_asyncio(self):
        """(`_get_running_loop`, `current_task`) from the asyncio the PROGRAM
        imported, or None if it is not (fully) there yet. Both are C
        functions (`_asyncio`) on 3.12-3.14; `_get_running_loop` returns
        None outside a loop instead of raising, which is why it is the gate.

        Guarded because `sys.modules["asyncio"]` is a slot the PROGRAM can
        write: a stand-in module's `__getattr__` is program code, and
        `getattr(..., None)` swallows only AttributeError, so anything else
        it raises would come out of a monitoring callback. A failed bind is
        not counted and not remembered -- the next event simply retries, the
        same way it does while a real asyncio is still half-imported."""
        try:
            mod = sys.modules.get("asyncio")
            events = getattr(mod, "events", None)
            get_loop = getattr(events, "_get_running_loop", None)
            cur_task = getattr(mod, "current_task", None)
        except BaseException:
            return None
        if get_loop is None or cur_task is None:
            return None
        self._asyncio = (get_loop, cur_task)
        return self._asyncio

    def _count_task_error(self) -> None:
        with self._task_lock:
            self.task_errors += 1

    def _task_serial(self, tls):
        """The minted serial of the asyncio task running on this thread right
        now, or None: no asyncio, no running loop, no current task, or a task
        object that broke the lookup (counted in `task_errors`, never raised
        into the program). Only IDENTITY failures are counted: a task whose
        `get_name` raises still gets its serial and still attributes its
        events, and is recorded as a task with no name, not as an error.
        Must be called inside an `in_hook` region: a Task subclass's
        `get_name` is program code.

        Minting is also where the task's `Fingerprint` is created, so that
        every `tasks` row has a `task_fingerprints` row whatever kind of
        event brought the task into view (spec D6). A task that is minted
        here and never reaches `_fp_for` ends with a zero-count row, which
        says it ran no causal event while traced -- a different fact from
        having no row at all."""
        if "asyncio" not in sys.modules:
            return None
        fns = self._asyncio or self._bind_asyncio()
        if fns is None:
            return None
        get_loop, cur_task = fns
        try:
            if get_loop() is None:
                return None
            task = cur_task()
        except BaseException:
            self._count_task_error()
            return None
        if task is None:
            return None
        cache = tls.task_cache
        if cache is not None and cache[0] is task:
            return cache[1]
        try:
            with self._task_lock:
                serial = self._task_serials.get(task)
                minted = serial is None
                if minted:
                    self._next_task += 1
                    serial = self._next_task
                    self._task_serials[task] = serial
        except BaseException:          # hostile __hash__/__eq__ on a subclass
            self._count_task_error()
            return None
        if minted:
            try:
                name = plain_str(task.get_name())
            except BaseException:
                name = None
            self.writer.add_task(serial, name, tls.thread_serial)
            # Every `tasks` row gets its `task_fingerprints` row, HERE and
            # not in `_fp_for`, because a serial is minted at any event with
            # a current task -- YIELD, RESUME and LINE included -- and
            # `_fp_for` only ever runs on a causal one. A task whose only
            # traced frames are a RESUMEd generator otherwise had a row in
            # one table and none in the other, which every reader of the
            # pair takes for a lossy recording. A zero-count row means "this
            # task ran no causal event while traced"; no row at all means
            # the task was never recorded.
            #
            # The `_task_lock` block above is CLOSED by this point -- it is
            # the `with` inside the `try` further up -- so `_fp_lock` is
            # taken with no other tracer lock held, as everywhere else.
            with self._fp_lock:
                self._task_fps.setdefault(serial, Fingerprint())
        tls.task_cache = (task, serial)
        return serial
