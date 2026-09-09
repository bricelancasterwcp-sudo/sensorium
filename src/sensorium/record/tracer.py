"""sys.monitoring-based recorder.

Default tier: CALL/RETURN/RAISE/HANDLED for user code (files under root,
excluding stdlib/site-packages/sensorium itself). Focus tier adds LINE events
carrying local-variable deltas for focused code. Re-entrancy: recorder frames
are never traced and capture runs behind a thread-local in_hook flag.

LINE events, and every value captured anywhere, are NEVER fingerprinted: a
fingerprint must depend only on the (code object, causal kind) sequence, which
is what lets `refocus` re-run a program with deeper capture and prove it was
the same execution. `_on_line` must never touch `_fp`.

A LINE event fires BEFORE its line runs. So the deltas on a LINE event describe
state produced by the PRECEDING executed line, while the event's `line` column
is the line that is about to execute. This is deliberate: read a run of LINE
events as a state timeline, where each row says "just before line N, these
locals had just become these values". `deltas` holds only the names whose
captured value differs from the previous capture in that same frame, and no
event is written at all when nothing changed.

Names that went away carry their own sibling key: `payload["unbound"]` is a
sorted list of names bound at the previous line and gone at this one, present
only when non-empty. It is kept out of `deltas` so every delta value stays a
`capture_value` result and consumers need no type check. Both `del x` and the
implicit unbind that ends an `except ... as x` handler are reported this way,
and an unbind alone is enough to emit an event -- otherwise a `del` whose line
changes nothing else would leave no trace, and a consumer folding deltas would
keep a dead binding alive for the rest of the frame.

A LINE event's `frame_id` is always set. Every traced code object opens a
frame, generators and coroutines included (arc 2); a suspendable frame keeps
its entry across its suspensions -- parked in a tracer-level table between
YIELD and RESUME, so the thread that resumes it need not be the one that
opened it -- and leaves through PY_RETURN/PY_UNWIND like any other. The
dropped-while-suspended case arrives as PY_THROW(GeneratorExit) + PY_UNWIND.
Each suspension is recorded: YIELD names the TYPE being awaited and RESUME
carries the exception thrown in, if any. Neither is fingerprinted --
how often a coroutine parks is the event loop's business, not the program's.
An exception thrown into a suspended TRACED frame is `identify`d at PY_THROW
so its RESUME row and the PY_UNWIND that follows carry ONE serial; that
equality, not the type, is what lets a reader call a frame cancelled or
abandoned rather than merely raised. Untraced frames mint nothing: PY_THROW
fires on the frame that will unwind, so an untraced one writes no row at
either end and a serial for it would only evict a live one. A call whose
caller has no open frame gets `parent_id NULL` and `caller_code` / `caller`
naming who called it: the parent is never guessed.

Every RAISE/HANDLED payload carries an exception `serial`: an exact per-thread
identity, minted the first time this recorder sees an exception object and
reused for every later event of that same object. It exists because `oid`
(`id(exc)`) is NOT an identity -- CPython recycles addresses, and a plain retry
loop measurably gives three distinct exceptions one address. Serials never
reach a fingerprint: `Fingerprint.update` takes only (file, qualname, kind),
and payloads are not hashed, which is what keeps `refocus` verdicts stable.

Serials live in a per-thread TABLE (`_ExcRefs`), never in a "current serial"
slot. Slots cannot express "several exceptions are alive and any of them may
come back", and both shapes that broke earlier attempts are exactly that:

  * an exception stored by a handler (`except E as e: return e`) and raised
    again after some *other* exception has been handled in between, and
  * an exception in flight through a `finally` that raises and handles an
    exception of its own before the original resumes.

With one slot the first loses its serial and the second inherits the
interloper's -- one object under two identities, or two objects under one.
A table keyed by the object has neither failure.

The one place this recorder measurably outlives the program's own references:
that table holds a STRONG reference to each exception it remembers. It has to
be strong -- `BaseException` does not support weak references at all -- and
being strong is also what makes `id(exc)` a sound key, since a retained
address cannot be recycled while we hold the object. The cost is real and is
bounded on purpose: each retained exception pins its traceback and therefore
the frames and locals reachable from it, so at most `_RETAIN_MAX` per live
thread are kept, the oldest being dropped when a newer one arrives. Past that
bound the recorder simply forgets, a later raise of a forgotten object mints a
fresh serial, and `sensorium exceptions` refuses to call such an exception
swallowed rather than pretending the two are unrelated. Control-flow
exceptions thrown INTO a frame are serialled from a second, much smaller
table (`_CONTROL_RETAIN_MAX`), so that dropping generators -- which ordinary
code does constantly -- cannot evict the real exceptions this machinery
exists to link. A thread's tables die with the thread, and `uninstall` clears
every live thread's tables and in-flight slot, after which this recorder
holds no exception object at all.
"""
import sys
import threading
import time
import weakref
from pathlib import Path

from sensorium.record.capture import (capture_exc, capture_value, plain_str,
                                      type_name)
from sensorium.record.fingerprint import Fingerprint
# The exception-retention layer, split out at this file's 800-line ceiling.
# Re-exported so `tracer.<name>` keeps resolving: these are one recorder's
# internals across its files, not separate modules with surfaces of their
# own.
from sensorium.record.tracer_exc import (  # noqa: F401
    _CONTROL_RETAIN_MAX, _RETAIN_MAX, _ExcRefs, _TLS, _is_control_flow)
# The frame-classification layer, split out at the same ceiling, re-exported
# for the same reason.
from sensorium.record.tracer_frames import (  # noqa: F401
    FocusSpec, WindowSpec, _FrameDecisions, module_name_for)

M = sys.monitoring
TOOL = M.PROFILER_ID


def locals_snapshot(frame) -> dict | None:
    """`frame.f_locals` as a plain dict with exact-`str` keys, or None.

    Reading a frame's locals looks like reading interpreter data. Two parts
    of it are the observed program's own code:

    * **`f_locals` may BE a mapping the program supplied.** `exec(code,
      globals, mapping)` and a metaclass `__prepare__` both hand the frame an
      arbitrary object, so `.items()` is an overridable method. Measured: a
      `dict` subclass whose `items()` raises killed a traced program that
      runs clean standalone, at this line.
    * **The KEYS may be `str` subclasses.** A class body's `locals()[K("x")]
      = 1`, or the 3.13+ write-through `f_locals` proxy, puts a program-
      defined object where a name should be -- and the recorder then hashes
      it, compares it (`prev.get(name)`, the set difference) and SORTS it
      (`sorted(gone)`). Measured: two such keys going out of scope on one
      line reached `sorted`, whose `__lt__` killed the program and was then
      reported by `exceptions` as the program's own uncaught bug, at a line
      that never raised.

    So: one guarded read of `.items()`, then exact-`str` keys built by
    `plain_str`, which cannot raise. Nothing downstream touches a key the
    program owns. None means the locals could not be read at all -- the
    callers record that, they do not paper over it.

    Two names that normalise to the SAME string collapse, last one wins.
    That is the honest outcome: the plain string is the only name the trace
    can report, and a program that binds both `x` and `K("x")` has two
    things the trace cannot tell apart by name anyway.
    """
    try:
        items = list(frame.f_locals.items())
    except BaseException:
        return None
    return {plain_str(k): v for k, v in items}


class Tracer(_FrameDecisions):
    def __init__(self, writer, root: Path, focus: FocusSpec,
                 include=(), exclude=(), window: str | None = None) -> None:
        self.writer = writer
        self.root = Path(root).resolve()
        self.focus = focus
        self.include = tuple(include)
        self.exclude = tuple(exclude)
        self.window = WindowSpec(window)
        # id(code) -> (traced, fp_file, qualname, focused, kind, win_key)
        self._decisions: dict[int, tuple] = {}
        # id(frame) -> the live entry of a frame SUSPENDED right now, for
        # every thread at once. A suspended frame runs on no thread, so the
        # thread that resumes it need not be the one that opened it: a
        # generator first `next`ed where it was made and stepped from a
        # thread pool afterwards (Starlette's `iterate_in_threadpool`, which
        # is what `StreamingResponse(sync_gen)` does) resumes on a worker,
        # where a per-thread map cannot possibly hold its entry. An entry is
        # owned HERE or by exactly one thread's `live`, never by both.
        self._parked: dict[int, list] = {}
        self._parked_lock = threading.Lock()
        self._seen_codes: list = []    # pins code objects so id() cannot recycle
        self._fps: dict[int, Fingerprint] = {}
        self._task_fps: dict[int, Fingerprint] = {}   # task serial -> fp
        self._fp_lock = threading.Lock()
        # Weak values: a thread's table dies with the thread, so a program
        # that spawns thousands of short-lived threads does not accumulate
        # their retained exceptions here.
        self._exc_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._refs_lock = threading.Lock()
        # Recorded thread identity: a monotonic serial minted once per distinct
        # thread, NOT `threading.get_ident()`, which the OS recycles once a
        # thread ends -- reuse would merge two short-lived threads' events,
        # frames and fingerprints under one id.
        self._serial_lock = threading.Lock()
        self._next_serial = 0
        # asyncio task identity: a minted serial per task object, weakly held
        # so finished tasks do not accumulate. Bound lazily from sys.modules
        # (never imported here) so a program that never uses asyncio pays one
        # dict probe per event and sees its sys.modules untouched.
        self._asyncio: tuple | None = None
        self._task_serials: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._task_lock = threading.Lock()
        self._next_task = 0
        self.task_errors = 0       # lookups a hostile task object broke
        self._tls = _TLS(self._assign_thread_serial, self._register_refs)
        # The thread constructing the Tracer runs `_TLS.__init__` above, so it
        # is the first serial (1). `run_target` runs the target on this same
        # thread, which is why this is the run's main-thread identity.
        self.main_thread_serial: int = self._tls.thread_serial

    def _assign_thread_serial(self) -> int:
        with self._serial_lock:
            self._next_serial += 1
            return self._next_serial

    def _register_refs(self, serial: int, refs: _ExcRefs) -> None:
        with self._refs_lock:
            self._exc_refs[serial] = refs

    def _live_exc_refs(self) -> list:
        with self._refs_lock:
            return list(self._exc_refs.values())

    # -- callbacks ---------------------------------------------------------
    def _on_start(self, code, offset):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, kind, win_key = self._decide(code)
        if not traced:
            return M.DISABLE
        tls.in_hook = True
        try:
            frame = sys._getframe(1)
            names = code.co_varnames[:code.co_argcount + code.co_kwonlyargcount]
            # Through the same snapshot as `_on_line`, for the same reason.
            # A frame with parameters always has interpreter-built locals, so
            # this path is not the one that was reachable -- but "reachable
            # only because of the order things happen in" is the argument
            # this project has already watched rot twice, and the snapshot
            # makes it structural instead.
            loc = locals_snapshot(frame)
            args = ({} if loc is None else
                    {n: capture_value(loc[n]) for n in names if n in loc})
            payload = {"args": args} if loc is not None else {
                "args": {}, "unread": ["locals"]}
            tid = tls.thread_serial
            task = self._task_serial(tls)
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            caller = frame.f_back
            parent = self._parent_of(tls, caller)
            if parent is None:
                self._note_caller(payload, caller)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "CALL",
                                        None, cid, code.co_firstlineno,
                                        payload, task_id=task)
            pfid = parent[0] if parent is not None else None
            depth = parent[4] + 1 if parent is not None else 0
            fid = self.writer.open_frame(pfid, cid, eid, depth, tid, kind)
            in_window = bool(win_key is not None
                             or (parent is not None and parent[5]))
            tls.live[id(frame)] = [fid, code, cid, {}, depth, in_window,
                                   False]
            self._fp_for(tid, task).update(fp_file, qual, "CALL")
        finally:
            tls.in_hook = False
        return None

    def _on_return(self, code, offset, retval):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, _kind, _win_key = self._decide(code)
        if not traced:
            return M.DISABLE
        tls.in_hook = True
        try:
            tid = tls.thread_serial
            frame = sys._getframe(1)
            entry = self._live_entry(tls, frame, code)
            fid = None
            if entry is not None:
                del tls.live[id(frame)]
                fid = entry[0]
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            task = self._task_serial(tls)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "RETURN",
                                        fid, cid, None,
                                        {"value": capture_value(retval)},
                                        task_id=task)
            if fid is not None:
                self.writer.close_frame(fid, eid, "return")
            self._fp_for(tid, task).update(fp_file, qual, "RETURN")
        finally:
            tls.in_hook = False
        return None

    def _on_unwind(self, code, offset, exc):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, _kind, _win_key = self._decide(code)
        if not traced:
            return None                      # exception events can't DISABLE
        tls.in_hook = True
        try:
            frame = sys._getframe(1)
            entry = self._live_entry(tls, frame, code)
            if entry is not None:
                del tls.live[id(frame)]
                self.writer.close_frame(
                    entry[0], None, "unwind",
                    capture_exc(exc, self.serial_of(exc)))
        finally:
            tls.in_hook = False
        return None

    # -- suspension --------------------------------------------------------
    def _suspension(self, code, frame, kind, payload_factory, disable_ok=True):
        """Shared body of the YIELD/RESUME callbacks. `frame` is the
        triggering frame, read as `sys._getframe(1)` OF THE REGISTERED
        CALLBACK and passed down -- the same convention `_on_raise` and
        `_on_handled` follow, and for the same reason: read one frame deeper,
        here, it would be tracer.py's own.

        `payload_factory` is a callable, not a payload. Building the payload
        runs the observed program (`capture_exc` calls its `__str__`,
        `type_name` reads a possibly-computed `__name__`), so it must happen
        INSIDE the `in_hook` region -- otherwise a traced helper called from
        that `__str__` is recorded as real execution: a phantom CALL/RETURN
        pair, a live entry, and a fingerprint update minted from hook time.

        Never fingerprinted. A fingerprint must depend only on the (code
        object, causal kind) sequence -- suspending is not a causal step, and
        how many times a coroutine parks depends on the event loop's
        scheduling, so hashing it would make two identical runs disagree.
        """
        tls = self._tls
        if tls.in_hook:
            return None
        traced, _fp_file, _qual, _focused, _kind, _win = self._decide(code)
        if not traced:
            # PY_YIELD/PY_RESUME may be disabled per code object like any
            # other local event, and untraced code suspends constantly (the
            # event loop, every stdlib generator), so saying so is worth
            # real time. PY_THROW may NOT: CPython refuses to disable it,
            # exactly as it refuses RAISE and PY_UNWIND, and a DISABLE from
            # that callback raises ValueError *into the traced program* and
            # unregisters the callback -- measured, not assumed.
            return M.DISABLE if disable_ok else None
        tls.in_hook = True
        try:
            entry = self._live_entry(tls, frame, code)
            if entry is None:
                return None
            suspending = kind == "YIELD"
            entry[6] = suspending
            self.writer.add_event(time.monotonic_ns(), tls.thread_serial, kind,
                                  entry[0], entry[2], frame.f_lineno,
                                  payload_factory(),
                                  task_id=self._task_serial(tls))
            if suspending:
                self._park(tls, frame, entry)
        finally:
            tls.in_hook = False
        return None

    def _on_yield(self, code, offset, value):
        # The TYPE name, never `repr(value)`: a repr is program code run from
        # a hook, unbounded in size, and different on every run (addresses),
        # which would make the column useless for grouping and diffing.
        # `type_name` is the capture module's guarded funnel and runs inside
        # the hook region -- a metaclass `__name__` is program code too.
        return self._suspension(code, sys._getframe(1), "YIELD",
                                lambda: {"awaiting": type_name(value)})

    def _on_resume(self, code, offset):
        return self._suspension(code, sys._getframe(1), "RESUME", lambda: None)

    def _on_throw(self, code, offset, exc):
        """An exception is being thrown into a suspended frame.

        Decide BEFORE minting. `identify` retains a strong reference in a
        bounded table, so minting for untraced code would pour every
        generator finalisation and every asyncio cancellation in the process
        into it and evict serials a stored re-raise still wants. Unlike RAISE
        (where the raising frame may be untraced while the frame that unwinds
        is traced), PY_THROW fires on the very frame that will PY_UNWIND: if
        it is untraced, no row is written at either end and the serial buys
        nothing.

        Which table, for the same reason at a finer grain. `_exc_event`
        deliberately keeps control-flow types out of the real table, and this
        door is the one they would otherwise arrive by: a `for ... break`, a
        short-circuiting `any(genexpr)`, any dropped generator throws
        GeneratorExit into a frame this recorder may well be tracing. They
        still need a serial -- `abandoned` is the RESUME serial matching the
        unwind's, nothing else -- so they get one from `cf_exc`, a small
        table of their own (`_CONTROL_RETAIN_MAX`).

        Knowingly given up: an exception thrown into an UNTRACED generator
        that escapes into a traced caller's unwind has no serial there, so
        that frame reads `raised` rather than `thrown` -- no D2 state on a
        traced frame depends on it.

        For a traced frame the serial is minted inside the hook region, so
        the RESUME row, the RAISE the interpreter fires next, and the UNWIND
        all carry ONE serial. That equality -- not the type -- is what lets
        the reader say "cancelled" or "abandoned".
        """
        tls = self._tls
        if tls.in_hook or not self._decide(code)[0]:
            return None                    # PY_THROW may not DISABLE
        refs = tls.cf_exc if _is_control_flow(exc) else tls.exc
        return self._suspension(
            code, sys._getframe(1), "RESUME",
            lambda: {"thrown": capture_exc(exc, refs.identify(exc))},
            disable_ok=False)

    # The triggering frame is sys._getframe(1) *of the registered callback*,
    # so it is read here and passed down rather than inside _exc_event, which
    # sits one frame deeper and would otherwise report tracer.py's own lines.
    def _on_raise(self, code, offset, exc):
        return self._exc_event(code, exc, "RAISE", sys._getframe(1))

    def _on_handled(self, code, offset, exc):
        return self._exc_event(code, exc, "HANDLED", sys._getframe(1))

    def _on_reraise(self, code, offset, exc):
        """RERAISE is not a recorded kind; it only maintains in-flight state.

        A bare ``raise``, and the implicit re-raise that ends a ``finally`` or
        a ``__exit__``, put the same exception back in flight. Without this,
        the EXCEPTION_HANDLED that CPython fires on *entry* to a finally block
        -- which happens even when nothing is caught, because ``finally`` is
        compiled as an implicit handler -- would disarm the de-dupe
        mid-propagation and the next frame's RAISE would be recorded as a
        second origin.

        It deliberately does not touch ``origin_recorded``: re-arming resumes a
        propagation, it never reopens the origin. Only a fresh RAISE of a
        different object does that.
        """
        tls = self._tls
        if not tls.in_hook and not _is_control_flow(exc):
            tls.exc.last_exc = exc
        return None

    def _exc_event(self, code, exc, kind, frame):
        tls = self._tls
        if tls.in_hook:
            return None
        # Control-flow exceptions are neither recorded nor allowed to disturb
        # in-flight state: a generator finishing during cleanup must not clear
        # the real exception that is propagating. Matched by TYPE, not name, so
        # a user class merely sharing a control-flow name is recorded rather
        # than silently dropped; see `_is_control_flow`.
        if _is_control_flow(exc):
            return None
        # In-flight bookkeeping runs whether or not this frame is traced --
        # handlers and cleanup blocks are frequently foreign code. Being in
        # flight is tracked separately from having recorded an origin: library
        # code routinely raises, handles and re-raises internally before the
        # exception ever surfaces in user code, so "already in flight" must not
        # by itself suppress the row. The origin is the first *traced* frame the
        # exception reaches. HANDLED ends the flight -- which is what makes a
        # later raise of the same object a new origin -- but note it does not
        # imply anything was caught; see _on_reraise.
        # The serial rides along on decisions this machine already takes; it
        # never changes one. It is looked up per event, from the object, so
        # that an exception handled between this one's raise and its re-raise
        # -- or raised and handled inside a `finally` while this one is still
        # in flight -- cannot displace it. Nothing here is a "current serial":
        # `refs.identify` answers for the object it is given and no other.
        refs = tls.exc
        if kind == "RAISE":
            if refs.last_exc is not exc:
                refs.last_exc = exc
                tls.origin_recorded = False   # a fresh raise reopens the origin
            if tls.origin_recorded:
                return None                   # propagating an origin we logged
            serial = refs.identify(exc)
        else:
            # Remembered (or recognised) here as well as on RAISE, so a later
            # `raise e` of this same object resumes its serial; see _ExcRefs
            # for why the reference is strong and why it is bounded.
            serial = refs.identify(exc)
            refs.last_exc = None
        traced, fp_file, qual, focused, _fkind, _win_key = self._decide(code)
        if not traced:
            return None
        if kind == "RAISE":
            tls.origin_recorded = True
        tls.in_hook = True
        try:
            tid = tls.thread_serial
            entry = tls.live.get(id(frame))
            fid = entry[0] if (entry is not None and entry[1] is code) else None
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            task = self._task_serial(tls)
            self.writer.add_event(time.monotonic_ns(), tid, kind, fid, cid,
                                  frame.f_lineno,
                                  {"exc": capture_exc(exc, serial)},
                                  task_id=task)
            self._fp_for(tid, task).update(fp_file, qual, kind)
        finally:
            tls.in_hook = False
        return None

    def _on_line(self, code, line):
        """Record the locals that changed since this frame's previous line.

        Fires *before* `line` executes, so the deltas belong to the line before
        it; see the module docstring. Never fingerprints.
        """
        tls = self._tls
        if tls.in_hook:
            return None
        traced, _fp_file, _qual, focused, _kind, _win_key = self._decide(code)
        if not traced or not focused:
            return M.DISABLE      # nothing here will ever be worth recording
        frame = sys._getframe(1)
        entry = self._live_entry(tls, frame, code)
        if entry is None:
            return None           # no open frame for this activation
        if self.window and not entry[5]:
            # Outside the window: no ancestor of THIS activation is the
            # window target. Not DISABLE -- another activation of the same
            # code may be inside it later.
            return None
        tls.in_hook = True        # capture_value runs user __repr__ code
        try:
            prev = entry[3]
            snap = locals_snapshot(frame)
            if snap is None:
                # The locals could not be read at all. Record the site with
                # that said plainly rather than skip it: a site nobody
                # checked must not look like a site where nothing changed,
                # and `prev` is deliberately left in place, because this
                # step establishes nothing about what went out of scope.
                self.writer.add_event(time.monotonic_ns(),
                                      tls.thread_serial, "LINE",
                                      entry[0], entry[2], line,
                                      {"deltas": {}, "unread": ["locals"]},
                                      task_id=self._task_serial(tls))
                return None
            cur, deltas = {}, {}
            for name, val in snap.items():
                cap = capture_value(val)
                cur[name] = cap
                # Captures, never live objects -- and NAMES that are exact
                # `str`, never the program's own key objects. Both halves
                # were false once: a capture EMBEDDED `str`/`int`/`float`
                # subclass instances until `capture_value` normalised them,
                # and the keys came straight out of `f_locals` until
                # `locals_snapshot` did. Either one turns the dict lookup
                # below, the set difference, or the `sorted` further down
                # into a call into the observed program, from a hook, with
                # no guard anywhere on the path.
                if prev.get(name) != cap:
                    deltas[name] = cap
            gone = prev.keys() - cur.keys()
            entry[3] = cur
            if deltas or gone:
                payload = {"deltas": deltas}
                if gone:
                    # Sibling key, never a sentinel inside deltas: that would
                    # widen capture_value's codomain and force a type check on
                    # every value. Readers that ignore it lose nothing else.
                    payload["unbound"] = sorted(gone)
                self.writer.add_event(time.monotonic_ns(),
                                      tls.thread_serial, "LINE",
                                      entry[0], entry[2], line, payload,
                                      task_id=self._task_serial(tls))
        finally:
            tls.in_hook = False
        return None

    def serial_of(self, exc) -> int | None:
        """The serial this thread holds for `exc`, or None if it has none.

        `boot` calls this from its own `except BaseException` clause. That
        clause is untraced code, so the EXCEPTION_HANDLED it fires cleared
        `last_exc` -- but the identity table still holds the object, which is
        why the uncaught record can be tied to the RAISE row that produced it.

        Both of this thread's tables are asked, because a frame closed by a
        GeneratorExit thrown into it must read the serial its RESUME row
        carries -- that equality is the whole of `abandoned`. The two are
        disjoint by construction (`_exc_event` never records a control-flow
        type, `_on_throw` sends only control-flow types to `cf_exc`), so
        asking both cannot return the wrong one.

        Never mints: a caller asking after the fact must be told "no serial"
        rather than handed a fresh one that matches no recorded row.
        """
        tls = self._tls
        serial = tls.exc.serial_of(exc)
        return serial if serial is not None else tls.cf_exc.serial_of(exc)

    # -- lifecycle ---------------------------------------------------------
    def install(self) -> None:
        E = M.events
        try:
            M.use_tool_id(TOOL, "sensorium")
        except ValueError as e:
            owner = M.get_tool(TOOL)
            raise RuntimeError(
                f"cannot install monitoring: tool id {TOOL} is already in use"
                f" by {owner!r} ({e}). Another profiler or debugger is "
                "active; stop it and re-run.") from None
        M.register_callback(TOOL, E.PY_START, self._on_start)
        M.register_callback(TOOL, E.PY_RETURN, self._on_return)
        M.register_callback(TOOL, E.PY_UNWIND, self._on_unwind)
        M.register_callback(TOOL, E.RAISE, self._on_raise)
        M.register_callback(TOOL, E.RERAISE, self._on_reraise)
        M.register_callback(TOOL, E.EXCEPTION_HANDLED, self._on_handled)
        M.register_callback(TOOL, E.LINE, self._on_line)
        M.register_callback(TOOL, E.PY_YIELD, self._on_yield)
        M.register_callback(TOOL, E.PY_RESUME, self._on_resume)
        M.register_callback(TOOL, E.PY_THROW, self._on_throw)
        events = (E.PY_START | E.PY_RETURN | E.PY_UNWIND
                  | E.RAISE | E.RERAISE | E.EXCEPTION_HANDLED
                  | E.PY_YIELD | E.PY_RESUME | E.PY_THROW)
        if self.focus:
            events |= E.LINE
        M.set_events(TOOL, events)
        M.restart_events()

    def uninstall(self) -> None:
        E = M.events
        # Events off FIRST, and only then the tables. Clearing another
        # thread's retention table while its callbacks are still live races
        # the eviction loop's unguarded `next(iter(...))`: a worker between
        # the `len()` check and the `next()` would raise StopIteration from
        # inside a monitoring callback -- the recorder killing a traced
        # thread, which is the one thing it must never do.
        M.set_events(TOOL, 0)
        # Drop every exception this recorder is holding, on every live thread
        # -- not just the one calling uninstall, whose table is the only one
        # `self._tls` can reach. Nothing can resume a serial once recording
        # has stopped, and a worker parked in a `finally` must not keep its
        # last exception (and that exception's frames and locals) alive for
        # the rest of the process.
        for refs in self._live_exc_refs():
            refs.clear()
        # Whatever is still parked was suspended when recording stopped --
        # the one residual state (spec D2). Nothing is written for it: the
        # reader derives "suspended at end of recording" from the frame's
        # last YIELD row, which is evidence the trace already holds.
        # Dropping the entries here is what stops this recorder holding a
        # dead frame's locals for the rest of the process.
        with self._parked_lock:
            self._parked.clear()
        self._tls.task_cache = None
        for ev in (E.PY_START, E.PY_RETURN, E.PY_UNWIND, E.RAISE,
                   E.RERAISE, E.EXCEPTION_HANDLED, E.LINE,
                   E.PY_YIELD, E.PY_RESUME, E.PY_THROW):
            M.register_callback(TOOL, ev, None)
        M.free_tool_id(TOOL)
        # Snapshot under the lock, as every other access to `_fps` does. Events
        # are off, but a callback already dispatched on another thread can still
        # be mid-flight and reach `_fp` to insert its first entry -- iterating
        # the live dict here would raise `dictionary changed size during
        # iteration` out of `run_target`'s `finally`, before `w.close()`,
        # leaking the connection and leaving the trace `incomplete`. A thread
        # that inserts after this snapshot was still alive when recording
        # stopped, and is already reported as such (`_recording_gaps`).
        with self._fp_lock:
            fps = list(self._fps.items())
            tfps = list(self._task_fps.items())
        for tid, fp in fps:
            self.writer.write_fingerprint(tid, fp.hexdigest(), fp.count)
        # A task's row is written whatever state the task was left in: a
        # stream that was recorded is a stream, and one still parked at
        # uninstall is exactly the case a comparison most wants to see.
        # ALL of them in one transaction: a commit is an fsync, this runs
        # after the recorded program has finished, and one per task made
        # exit cost scale with the task count (see
        # `TraceWriter.write_task_fingerprints`).
        self.writer.write_task_fingerprints(
            [(task, fp.hexdigest(), fp.count) for task, fp in tfps])
