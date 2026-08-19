"""sys.monitoring-based recorder.

Default tier: CALL/RETURN/RAISE/HANDLED for user code (files under root,
excluding stdlib/site-packages/sensorium itself). Focus tier (Task 7) adds
LINE events with local deltas. Re-entrancy: recorder frames are never traced
and capture runs behind a thread-local in_hook flag.
"""
import sys
import threading
import time
from fnmatch import fnmatch
from pathlib import Path

from sensorium.record.capture import capture_exc, capture_value
from sensorium.record.fingerprint import Fingerprint

M = sys.monitoring
TOOL = M.PROFILER_ID
_SENSORIUM_DIR = str(Path(__file__).resolve().parent.parent)
_GENLIKE = 0x20 | 0x80 | 0x200        # CO_GENERATOR|CO_COROUTINE|CO_ASYNC_GEN
_CONTROL_FLOW_EXC = ("StopIteration", "StopAsyncIteration", "GeneratorExit")


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


class _TLS(threading.local):
    def __init__(self) -> None:
        self.stack: list = []          # [frame_id, code, code_id, locals_snapshot]
        self.in_hook = False
        self.window_depth = 0
        self.last_exc = None           # exception currently in flight, if any
        self.origin_recorded = False   # ...and whether its origin got a row


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
        self._tls = _TLS()

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
            loc = frame.f_locals
            args = {n: capture_value(loc[n]) for n in names if n in loc}
            tid = threading.get_ident()
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "CALL",
                                        None, cid, code.co_firstlineno,
                                        {"args": args})
            if not frameless:
                parent = tls.stack[-1][0] if tls.stack else None
                fid = self.writer.open_frame(parent, cid, eid,
                                             len(tls.stack), tid)
                tls.stack.append([fid, code, cid, {}])
            self._fp(tid).update(fp_file, qual, "CALL")
            if self.window and qual == self.window:
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
            if self.window and qual == self.window and tls.window_depth:
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
                self.writer.close_frame(fid, None, "unwind", capture_exc(exc))
            if self.window and qual == self.window and tls.window_depth:
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
        if not tls.in_hook and type(exc).__name__ not in _CONTROL_FLOW_EXC:
            tls.last_exc = exc
        return None

    def _exc_event(self, code, exc, kind, frame):
        tls = self._tls
        if tls.in_hook:
            return None
        # Control-flow exceptions are neither recorded nor allowed to disturb
        # in-flight state: a generator finishing during cleanup must not clear
        # the real exception that is propagating.
        if type(exc).__name__ in _CONTROL_FLOW_EXC:
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
        if kind == "RAISE":
            if tls.last_exc is not exc:
                tls.last_exc = exc
                tls.origin_recorded = False   # a fresh raise reopens the origin
            if tls.origin_recorded:
                return None                   # propagating an origin we logged
        else:
            tls.last_exc = None
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
                                  frame.f_lineno, {"exc": capture_exc(exc)})
            self._fp(tid).update(fp_file, qual, kind)
        finally:
            tls.in_hook = False
        return None

    def _on_line(self, code, line):      # focus tier: implemented in Task 7
        return M.DISABLE

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
        M.set_events(TOOL, 0)
        for ev in (E.PY_START, E.PY_RETURN, E.PY_UNWIND, E.RAISE,
                   E.RERAISE, E.EXCEPTION_HANDLED, E.LINE):
            M.register_callback(TOOL, ev, None)
        M.free_tool_id(TOOL)
        for tid, fp in self._fps.items():
            self.writer.write_fingerprint(tid, fp.hexdigest(), fp.count)
