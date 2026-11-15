"""Failed tests, and the frame each one failed in.

`exceptions` judges throw and Err flow. A vitest `expect` throws inside
the harness and writes no RAISE, and a Rust `assert!` is a panic, which
that command counts and does not list. Both are already on the trace:
the test's frame closed by unwind, and the panic's message is on that
unwind (and on a RAISE when the panic fired inside a frame). This
command reads that record. It does not invent a RAISE the recorder did
not write, and a test that caught its exception and returned is not a
failure.
"""
import shlex

from sensorium import paths
from sensorium.exit import ANSWERED, BAD_CALL
from sensorium.query.caps import none_status, print_incomplete
from sensorium.query.exceptions_rust import _marks
from sensorium.query.fmt import fmt_exc, more_note
from sensorium.query.help import LIMIT_HELP, RUN_HELP
from sensorium.store.reader import Trace

_INCOMPLETE = ("a failure recorded after the cut is not below, and its "
               "absence here is not evidence it had none")


def add_parser(sub) -> None:
    p = sub.add_parser(
        "failures", help="failed tests and the frame they failed in",
        description="Each failed test mapped to the frame and the "
                    "assertion, panic or exception recorded there. A "
                    "vitest expect, a Rust panic, and a C crash or "
                    "assert in a test_ frame are listed here; "
                    "exceptions still judges throw and Err flow and "
                    "does not list them.",
        epilog="exit: 0 yes, 1 no, 2 fix the call, 3 change the recording")
    p.add_argument("run", help=RUN_HELP)
    p.add_argument("--limit", type=int, default=50, help=LIMIT_HELP)
    p.set_defaults(func=run)


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return BAD_CALL
    trace = Trace.open(paths.find_trace(args.run))
    lang = trace.lang
    if lang == "rust":
        rows, empty = _rust(trace)
    elif lang == "typescript":
        rows, empty = _typescript(trace)
    elif lang == "c":
        rows, empty = _c(trace)
    else:
        rows, empty = _python(trace)
    print_incomplete(trace, _INCOMPLETE)
    if not rows:
        print(empty)
        return none_status(trace)
    _print(args, rows)
    return ANSWERED


def _print(args, rows) -> None:
    shown = rows[:args.limit]
    print(f"failed ({len(rows)}):")
    for row in shown:
        print(f"  {row[0]}  {row[1]}")
        at = f"    at {row[2]}"
        if row[3] is not None:
            at += f" L{row[3]}"
        print(at)
        print(f"    {row[4]}")
    note = more_note(
        len(rows), len(shown),
        "sensorium failures "
        + shlex.quote(args.run)
        + f" --limit {len(rows)}")
    if note:
        print(note)


def _same(a, b) -> bool:
    """One escaping exception. Serial when both rows have one; otherwise
    the legacy (type, msg, oid) triple, which is all an older trace holds."""
    if not a or not b:
        return False
    sa, sb = a.get("serial"), b.get("serial")
    if sa is not None and sb is not None:
        return sa == sb
    return ((a.get("type"), a.get("msg"), a.get("oid"))
            == (b.get("type"), b.get("msg"), b.get("oid")))


def _text(exc, loc=None) -> str:
    if not exc or "type" not in exc:
        text = "?"
    else:
        text = fmt_exc(exc)
    if loc:
        text += f" at {loc}"
    return text


def _place(trace, frame) -> str:
    code = trace.code(frame.code_id)
    return f"f{frame.id} {code.file}:{code.qualname}"


def _title(trace, frame) -> str:
    return trace.code(frame.code_id).qualname.rsplit(".", 1)[-1]


def _is_test_name(qualname: str) -> bool:
    return qualname.rsplit(".", 1)[-1].startswith("test_")


def _descendants(trace, root_id: int):
    """`root_id` and every frame under it, parents before children."""
    out = []
    stack = [root_id]
    while stack:
        fid = stack.pop()
        frame = trace.frame(fid)
        if frame is None:
            continue
        out.append(frame)
        stack.extend(reversed([c.id for c in trace.children(fid)]))
    return out


def _origin(trace, root, frames):
    """The deepest frame under `root` whose unwind is the exception that
    escaped `root`, and the RAISE of that exception in that frame if the
    recorder wrote one. No RAISE means the failure was born in untraced
    code: the frame is still named, and the line is absent."""
    unwind = root.unwind_exc or {}
    raised = [f for f in frames
              if trace.frame_state(f).state == "raised"
              and _same(f.unwind_exc or {}, unwind)]
    origin = max(raised, key=lambda f: (f.depth, f.id)) if raised else root
    match = [e for e in trace.events(kind="RAISE", frame_id=origin.id)
             if _same((e.payload or {}).get("exc") or {}, unwind)]
    event = match[-1] if match else None
    return origin, (event.line if event is not None else None)


def _python(trace):
    tests = [f for f in trace.frames()
             if f.code_id is not None
             and _is_test_name(trace.code(f.code_id).qualname)]
    if not tests:
        return [], "no test frames recorded"
    rows = []
    for test in tests:
        if trace.frame_state(test).state != "raised":
            continue
        origin, line = _origin(trace, test, _descendants(trace, test.id))
        rows.append((_title(trace, test), _place(trace, test),
                     _place(trace, origin), line,
                     _text(test.unwind_exc)))
    if not rows:
        return [], "no test failures recorded"
    return rows, None


def _panic_loc(event, exc) -> str | None:
    if event is not None:
        payload = event.payload or {}
        return payload.get("loc") or (payload.get("exc") or {}).get("loc")
    return (exc or {}).get("loc")


def _rust(trace):
    sites = trace.meta.get("sites") or []
    if not any(r.get("test") for r in sites if isinstance(r, dict)):
        return [], "no test functions recorded"
    marks = _marks(trace.meta)
    # A test failed when ITS frame closed raised by a panic. A panic a
    # test caught (the frame then returned) is not a failure. The RAISE,
    # when one was written, supplies the line and the message.
    failed = []
    for frame in trace.frames():
        if frame.code_id is None:
            continue
        code = trace.code(frame.code_id)
        if marks.get((code.qualname, code.file)) != "test":
            continue
        exc = frame.unwind_exc or {}
        if (trace.frame_state(frame).state != "raised"
                or exc.get("kind") != "panic"):
            continue
        failed.append(frame)
    if not failed:
        return [], "no test failures recorded"
    rows = []
    for holder in failed:
        best = None
        for frame in _descendants(trace, holder.id):
            for event in trace.events(kind="RAISE", frame_id=frame.id):
                exc = (event.payload or {}).get("exc") or {}
                if exc.get("kind") != "panic":
                    continue
                rank = (frame.depth, event.id)
                if best is None or rank > best[0]:
                    best = (rank, frame, event)
        if best is None:
            rows.append((
                trace.code(holder.code_id).qualname,
                _place(trace, holder), _place(trace, holder), None,
                _text(holder.unwind_exc, _panic_loc(None, holder.unwind_exc)),
            ))
            continue
        _rank, origin, event = best
        exc = (event.payload or {}).get("exc") or holder.unwind_exc or {}
        rows.append((
            trace.code(holder.code_id).qualname,
            _place(trace, holder), _place(trace, origin), event.line,
            _text(exc, _panic_loc(event, exc)),
        ))
    return rows, None


def _call_task(trace, frame):
    event = (trace.event(frame.call_event_id)
             if frame.call_event_id is not None else None)
    return event.task_id if event is not None else None


def _task_root(trace, frame, task_id) -> bool:
    if _call_task(trace, frame) != task_id:
        return False
    if frame.parent_id is None:
        return True
    parent = trace.frame(frame.parent_id)
    if parent is None:
        return True
    return _call_task(trace, parent) != task_id


def _typescript(trace):
    tasks = trace.tasks()
    if not tasks:
        return [], "no tests recorded"
    rows = []
    for task in tasks:
        roots = [f for f in trace.frames()
                 if _task_root(trace, f, task.id)
                 and trace.frame_state(f).state == "raised"]
        for root in roots:
            origin, line = _origin(trace, root, _descendants(trace, root.id))
            name = task.name if task.name else "(unnamed)"
            rows.append((name, f"task t{task.id}", _place(trace, origin),
                         line, _text(root.unwind_exc)))
    if not rows:
        return [], "no test failures recorded"
    return rows, None


def _c_test_name(qualname: str) -> bool:
    """The qualname itself, not a dotted suffix: `test_foo` and `TestFoo`."""
    return qualname.startswith("test_") or qualname.startswith("Test")


def _c(trace):
    """A C test fails when its frame closed raised by a signal or a
    longjmp. The deepest RAISE of that unwind under the test supplies the
    line; a longjmp, which writes no RAISE, names the test frame and no
    line."""
    tests = []
    for frame in trace.frames():
        if frame.code_id is None:
            continue
        name = trace.code(frame.code_id).qualname
        if _c_test_name(name):
            tests.append(frame)
    if not tests:
        return [], "no test functions recorded"
    rows = []
    for test in tests:
        exc = test.unwind_exc or {}
        if (trace.frame_state(test).state != "raised"
                or exc.get("kind") not in ("signal", "longjmp")):
            continue
        best = None
        want = (exc.get("kind"), exc.get("type"))
        for frame in _descendants(trace, test.id):
            for event in trace.events(kind="RAISE", frame_id=frame.id):
                got = (event.payload or {}).get("exc") or {}
                if (got.get("kind"), got.get("type")) != want:
                    continue
                rank = (frame.depth, event.id)
                if best is None or rank > best[0]:
                    best = (rank, frame, event)
        title = trace.code(test.code_id).qualname
        if best is None:
            rows.append((title, _place(trace, test), _place(trace, test),
                         None, _text(exc)))
            continue
        _rank, origin, event = best
        got = (event.payload or {}).get("exc") or exc
        rows.append((title, _place(trace, test), _place(trace, origin),
                     event.line, _text(got)))
    if not rows:
        return [], "no test failures recorded"
    return rows, None
