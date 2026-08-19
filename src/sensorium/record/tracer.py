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

A LINE event's `frame_id` is always set. Generators and coroutines are
frameless (no frame is opened for them), so LINE stays permanently disabled for
their code even when focused -- there would be no frame to attach to.

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
swallowed rather than pretending the two are unrelated. A thread's table dies
with the thread, and `uninstall` clears every live thread's table and
in-flight slot, after which this recorder holds no exception object at all.
"""
import sys
import threading
import time
import weakref
from fnmatch import fnmatch
from pathlib import Path

from sensorium.record.capture import capture_exc, capture_value, plain_str
from sensorium.record.fingerprint import Fingerprint

M = sys.monitoring
TOOL = M.PROFILER_ID
_SENSORIUM_DIR = str(Path(__file__).resolve().parent.parent)
_GENLIKE = 0x20 | 0x80 | 0x200        # CO_GENERATOR|CO_COROUTINE|CO_ASYNC_GEN
_CONTROL_FLOW_EXC = (StopIteration, StopAsyncIteration, GeneratorExit)


def _is_control_flow(exc) -> bool:
    """True for the interpreter's own iterator/generator control-flow
    exceptions, matched by TYPE IDENTITY.

    A NAME match dropped any exception whose class merely happened to be
    called ``StopIteration`` -- a user class shadowing the builtin, unrelated
    to the iterator protocol -- with no RAISE, no HANDLED and no serial, so a
    real caught exception surfaced as ``no exceptions recorded``. ``type(exc)``
    is a C-level ``Py_TYPE`` read that cannot run a dunder; ``is`` (not
    ``in (...)``) because a hostile metaclass ``__eq__`` could raise inside a
    membership test. When the type is anything else -- including one that lies
    about its name -- the exception is RECORDED, never silently dropped.
    """
    t = type(exc)
    return t is StopIteration or t is StopAsyncIteration or t is GeneratorExit


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


# How many exception objects one thread remembers. Every one of them is held
# by a strong reference and pins its traceback, so this is a memory bound on
# the recorder's influence, not a tuning knob: raising it links more stored
# re-raises and keeps more of the program's dead frames alive. Exceeding it is
# not a silent loss -- see the module docstring and exceptions_cmd.
_RETAIN_MAX = 64


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
            self._entries.append((mod, qual or None))

    def __bool__(self) -> bool:
        return bool(self._entries)

    def matches(self, module: str | None, qualname: str) -> bool:
        if module is None:
            return False
        for mod, qual in self._entries:
            if module != mod:
                continue
            if qual is None or qualname == qual or qualname.startswith(qual + "."):
                return True
        return False


class _ExcRefs:
    """One thread's exception identity table -- and the only place this
    recorder holds a reference to an exception object.

    `serials` maps `id(exc)` -> `(exc, serial)`, insertion-ordered, capped at
    `_RETAIN_MAX`. Holding the object is what makes `id()` a sound key: the
    address cannot be recycled underneath us, so two distinct exceptions can
    never alias onto one serial. Weak references were tried first and are not
    an option at all -- `BaseException` does not support them
    (`TypeError: cannot create weak reference to 'ValueError' object`), and
    catching that error silently disabled the whole mechanism, which is the
    kind of quiet fallback this project bans.

    `last_exc` (the exception currently in flight) lives here too, so that
    `clear` really does release everything this recorder is holding, on
    whichever thread it is called for.
    """
    __slots__ = ("last_exc", "serials", "minted", "__weakref__")

    def __init__(self) -> None:
        self.last_exc = None           # exception currently in flight, if any
        self.serials: dict[int, tuple] = {}
        self.minted = 0                # monotonic per-thread serial source

    def serial_of(self, exc) -> int | None:
        """This thread's serial for `exc`, or None if it holds none.

        `id(exc)` alone is a sound key here, with no `is` re-check needed:
        object and serial go into the table together and only ever leave
        together, so while a key is present this table holds that object and
        no other object can have its address.
        """
        held = self.serials.get(id(exc))
        return held[1] if held is not None else None

    def identify(self, exc) -> int:
        """`exc`'s serial, minting and remembering one if it is new."""
        serial = self.serial_of(exc)
        if serial is not None:
            return serial
        self.minted += 1
        self.serials[id(exc)] = (exc, self.minted)
        while len(self.serials) > _RETAIN_MAX:
            oldest, held = next(iter(self.serials.items()))
            del self.serials[oldest]
            if held[0] is self.last_exc:
                # Never forget what is arming or propagating right now. An
                # exception paused inside a `finally` is not that -- its
                # EXCEPTION_HANDLED already cleared `last_exc` -- so a long
                # enough cleanup can push it out, and the query side hedges
                # rather than reading the fresh serial as another exception.
                self.serials[oldest] = held
        return self.minted

    def clear(self) -> None:
        self.last_exc = None
        self.serials.clear()


class _TLS(threading.local):
    """Per-thread recorder state.

    `threading.local` calls `__init__` again on every thread that touches the
    object, which is how each thread's `_ExcRefs` gets registered with the
    tracer -- without that registry, `uninstall` could only ever drop the
    exceptions held by the thread that happens to call it.
    """
    def __init__(self, register) -> None:
        self.stack: list = []          # [frame_id, code, code_id, locals_snapshot]
        self.in_hook = False
        self.window_depth = 0
        self.origin_recorded = False   # whether the in-flight exc got a row
        self.exc = _ExcRefs()
        register(self.exc)


class Tracer:
    def __init__(self, writer, root: Path, focus: FocusSpec,
                 include=(), exclude=(), window: str | None = None) -> None:
        self.writer = writer
        self.root = Path(root).resolve()
        self.focus = focus
        self.include = tuple(include)
        self.exclude = tuple(exclude)
        self.window = window
        # id(code) -> (traced, fp_file, qualname, focused, frameless)
        self._decisions: dict[int, tuple] = {}
        self._seen_codes: list = []    # pins code objects so id() cannot recycle
        self._fps: dict[int, Fingerprint] = {}
        self._fp_lock = threading.Lock()
        # Weak values: a thread's table dies with the thread, so a program
        # that spawns thousands of short-lived threads does not accumulate
        # their retained exceptions here.
        self._exc_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._refs_lock = threading.Lock()
        self._tls = _TLS(self._register_refs)

    def _register_refs(self, refs: _ExcRefs) -> None:
        with self._refs_lock:
            self._exc_refs[threading.get_ident()] = refs

    def _live_exc_refs(self) -> list:
        with self._refs_lock:
            return list(self._exc_refs.values())

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
        untraced = (False, None, None, False, False)
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
        frameless = bool(code.co_flags & _GENLIKE)
        return (True, rel, code.co_qualname, focused, frameless)

    def _fp(self, tid: int) -> Fingerprint:
        # Keyed by `threading.get_ident()`, the same identity events and frames
        # carry (see `boot.main_thread_ident`). That id is reused once a thread
        # ends, so two short-lived threads that run back-to-back share one
        # fingerprint here -- a known, accepted limitation: their events already
        # share the id everywhere else, so no downstream key could tell them
        # apart either. It surfaces only as a fingerprint COUNT that depends on
        # scheduling; a program that keeps its workers concurrent (as any real
        # thread-pool does) never hits it.
        with self._fp_lock:
            fp = self._fps.get(tid)
            if fp is None:
                fp = self._fps[tid] = Fingerprint()
            return fp

    # -- callbacks ---------------------------------------------------------
    def _on_start(self, code, offset):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
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
            tid = threading.get_ident()
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "CALL",
                                        None, cid, code.co_firstlineno,
                                        payload)
            if not frameless:
                parent = tls.stack[-1][0] if tls.stack else None
                fid = self.writer.open_frame(parent, cid, eid,
                                             len(tls.stack), tid)
                tls.stack.append([fid, code, cid, {}])
            self._fp(tid).update(fp_file, qual, "CALL")
            # Frameless code is excluded on purpose: an abandoned generator
            # never reaches PY_RETURN/PY_UNWIND, so counting its PY_START would
            # leak depth and wedge the window open for the rest of the run.
            # The gate must open and close on the same set of events.
            if not frameless and self.window and qual == self.window:
                tls.window_depth += 1
        finally:
            tls.in_hook = False
        return None

    def _on_return(self, code, offset, retval):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced:
            return M.DISABLE
        tls.in_hook = True
        try:
            tid = threading.get_ident()
            fid = None
            if not frameless and tls.stack and tls.stack[-1][1] is code:
                fid = tls.stack.pop()[0]
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "RETURN",
                                        fid, cid, None,
                                        {"value": capture_value(retval)})
            if fid is not None:
                self.writer.close_frame(fid, eid, "return")
            self._fp(tid).update(fp_file, qual, "RETURN")
            if (not frameless and self.window and qual == self.window
                    and tls.window_depth):
                tls.window_depth -= 1
        finally:
            tls.in_hook = False
        return None

    def _on_unwind(self, code, offset, exc):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced:
            return None                      # exception events can't DISABLE
        tls.in_hook = True
        try:
            if not frameless and tls.stack and tls.stack[-1][1] is code:
                fid = tls.stack.pop()[0]
                self.writer.close_frame(
                    fid, None, "unwind",
                    capture_exc(exc, self.serial_of(exc)))
            if (not frameless and self.window and qual == self.window
                    and tls.window_depth):
                tls.window_depth -= 1
        finally:
            tls.in_hook = False
        return None

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
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced:
            return None
        if kind == "RAISE":
            tls.origin_recorded = True
        tls.in_hook = True
        try:
            tid = threading.get_ident()
            fid = tls.stack[-1][0] if (not frameless and tls.stack
                                       and tls.stack[-1][1] is code) else None
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            self.writer.add_event(time.monotonic_ns(), tid, kind, fid, cid,
                                  frame.f_lineno,
                                  {"exc": capture_exc(exc, serial)})
            self._fp(tid).update(fp_file, qual, kind)
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
        traced, _fp_file, _qual, focused, frameless = self._decide(code)
        if not traced or not focused or frameless:
            return M.DISABLE      # nothing here will ever be worth recording
        if self.window and tls.window_depth == 0:
            # Outside the window *right now*. Deliberately not DISABLE: that is
            # permanent per code location, and this frame may run again inside
            # the window later.
            return None
        if not tls.stack or tls.stack[-1][1] is not code:
            return None           # no open frame for this activation
        entry = tls.stack[-1]
        frame = sys._getframe(1)
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
                                      threading.get_ident(), "LINE",
                                      entry[0], entry[2], line,
                                      {"deltas": {}, "unread": ["locals"]})
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
                                      threading.get_ident(), "LINE",
                                      entry[0], entry[2], line, payload)
        finally:
            tls.in_hook = False
        return None

    def serial_of(self, exc) -> int | None:
        """The serial this thread holds for `exc`, or None if it has none.

        `boot` calls this from its own `except BaseException` clause. That
        clause is untraced code, so the EXCEPTION_HANDLED it fires cleared
        `last_exc` -- but the identity table still holds the object, which is
        why the uncaught record can be tied to the RAISE row that produced it.

        Never mints: a caller asking after the fact must be told "no serial"
        rather than handed a fresh one that matches no recorded row.
        """
        return self._tls.exc.serial_of(exc)

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
        events = (E.PY_START | E.PY_RETURN | E.PY_UNWIND
                  | E.RAISE | E.RERAISE | E.EXCEPTION_HANDLED)
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
        for ev in (E.PY_START, E.PY_RETURN, E.PY_UNWIND, E.RAISE,
                   E.RERAISE, E.EXCEPTION_HANDLED, E.LINE):
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
        for tid, fp in fps:
            self.writer.write_fingerprint(tid, fp.hexdigest(), fp.count)
