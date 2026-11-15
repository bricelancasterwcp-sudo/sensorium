"""C signal crashes, as `exceptions` reads them.

A crash is a RAISE whose `exc.kind` is `"signal"`. A `longjmp` closes
frames with `closed_by` unwind and kind `longjmp` and writes no RAISE;
those are not exceptions. There is no HANDLED event and no swallow.

`uncaught` is the normal crash: the raising frame's unwind is that
signal, and either the process has `exit_signal` set or every ancestor
through the root closed by unwind. `ambiguous` is the rare case where a
RAISE exists and the frames returned anyway. The reason says which.

Single-trace output is this module's own lines. Invocation mode groups
through `exceptions_group`, which imports the site helpers below; this
module does not import the grouper.
"""
import re
import shlex
from pathlib import Path

from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from sensorium.query import caps
from sensorium.query.exceptions_cmd import Disposition
from sensorium.query.fmt import fmt_exc, more_note

TAG_ORDER = ("uncaught", "ambiguous")

_ID = re.compile(r"\b([ef])\d+\b")


def mask(text: str) -> str:
    """`e12` -> `e#`, `f3` -> `f#`. No exemption: a C verdict's `f<n>` is
    a frame id this tool minted, not a type name."""
    return _ID.sub(r"\1#", text)


def _exc(event) -> dict:
    return ((event.payload or {}).get("exc")) or {}


def _shown(exc: dict) -> str:
    if "type" not in exc:
        return "?"
    if "msg" not in exc and "msg" not in (exc.get("unread") or ()):
        return f"{exc['type']}(?)"
    return fmt_exc(exc)


def _site(trace, event) -> tuple:
    """`(file, line, qualname)` of the event's code, or `?` where the
    trace does not carry it."""
    code = trace.code(event.code_id) if event.code_id is not None else None
    return ((code.file if code is not None else "?"), event.line,
            (code.qualname if code is not None else "?"))


def site_text(site) -> str:
    _file, line, qualname = site
    shown = line if line is not None else "?"
    return f"{qualname} L{shown}"


def site_file(site) -> str:
    return Path(site[0]).name


def _at(trace, event) -> str:
    return site_text(_site(trace, event))


def _hops_line(trace, unit) -> str | None:
    """A signal raise has no journey to print."""
    return None


class Signal:
    """One unit: a single signal RAISE. `origin` is the event the grouper
    keys and brackets on."""

    def __init__(self, origin):
        self.origin = origin


class Index:
    """The signal RAISES, in id order, and whether the recording finished."""

    def __init__(self, trace):
        self.trace = trace
        self.incomplete = bool(trace.meta.get("incomplete"))
        found = []
        for event in trace.events(kind="RAISE"):
            if _exc(event).get("kind") == "signal":
                found.append(event)
        self.raises = sorted(found, key=lambda event: event.id)
        self.units = [Signal(event) for event in self.raises]


def _same_signal(raise_exc: dict, unwind_exc: dict) -> bool:
    """The frame's unwind is this RAISE's signal.

    `kind` may be absent on an older unwind row; a present kind must be
    `signal`. Types must match. Signal numbers must match when both rows
    carry one.
    """
    if not unwind_exc:
        return False
    kind = unwind_exc.get("kind")
    if kind not in (None, "signal"):
        return False
    if unwind_exc.get("type") != raise_exc.get("type"):
        return False
    raised = raise_exc.get("signal")
    unwound = unwind_exc.get("signal")
    if raised is not None and unwound is not None and raised != unwound:
        return False
    return True


def _frame(trace, event):
    if event.frame_id is None:
        return None
    return trace.frame(event.frame_id)


def _why_not_uncaught(trace, event, frame, exc: dict) -> str:
    """Why this RAISE is not the crash. Names the frame that returned,
    stayed open, or unwound as something else."""
    if frame is None:
        if event.frame_id is None:
            return "the RAISE names no frame"
        return f"f{event.frame_id} is missing"
    if frame.closed_by == "return":
        return f"f{frame.id} returned"
    if frame.closed_by != "unwind":
        how = frame.closed_by or "open"
        if how == "open":
            return f"f{frame.id} is still open"
        return f"f{frame.id} closed by {how}"
    unwind = frame.unwind_exc or {}
    kind = unwind.get("kind")
    if kind and unwind.get("type"):
        words = f"{kind} {unwind['type']}"
    elif kind:
        words = str(kind)
    else:
        words = "a different unwind"
    return f"f{frame.id} unwound with {words}, not this signal"


def _ancestors_unwound(trace, frame) -> tuple[bool, str]:
    """Every parent through the root closed by unwind.

    The root has no parent, so a signal that unwinds the root is uncaught
    on this test alone. A missing parent, or one that returned or is still
    open, is the reason the crash is not certain.
    """
    seen = set()
    current = frame
    while current.parent_id is not None:
        if current.id in seen:
            return False, f"f{current.id} is its own ancestor"
        seen.add(current.id)
        parent = trace.frame(current.parent_id)
        if parent is None:
            return False, f"f{current.parent_id} is missing"
        if parent.closed_by != "unwind":
            how = parent.closed_by or "open"
            if how == "return":
                return False, f"f{parent.id} returned"
            if how == "open":
                return False, f"f{parent.id} is still open"
            return False, f"f{parent.id} closed by {how}"
        current = parent
    return True, ""


def _disposition(trace, event) -> Disposition:
    exc = _exc(event)
    frame = _frame(trace, event)
    if frame is None or frame.closed_by != "unwind" or not _same_signal(
            exc, frame.unwind_exc or {}):
        return Disposition(
            tag="ambiguous",
            verdict="AMBIGUOUS: " + _why_not_uncaught(trace, event, frame, exc))
    if trace.meta.get("exit_signal") is not None:
        return Disposition(tag="uncaught",
                           verdict="UNCAUGHT: killed the process")
    ok, why = _ancestors_unwound(trace, frame)
    if ok:
        return Disposition(tag="uncaught",
                           verdict="UNCAUGHT: killed the process")
    return Disposition(tag="ambiguous", verdict="AMBIGUOUS: " + why)


def classify(trace, unit, idx) -> Disposition:
    return _disposition(trace, unit.origin)


def _raise_line(trace, event) -> str:
    exc = _exc(event)
    fid = f"f{event.frame_id}" if event.frame_id is not None else "?"
    code = trace.code(event.code_id) if event.code_id is not None else None
    if code is None:
        place = "?:?"
    else:
        place = f"{code.file}:{code.qualname}"
    line = f"L{event.line}" if event.line is not None else "L?"
    return f"  e{event.id}  {fid} {place} {line}  {_shown(exc)}"


def _gap(trace) -> tuple[str, int]:
    if trace.meta.get("incomplete"):
        return "no RAISE events recorded (see INCOMPLETE above)", UNSETTLED
    if trace.meta.get("trace_truncated"):
        return "no exceptions recorded (see TRUNCATED above)", UNSETTLED
    return "no exceptions recorded", NEGATIVE


def run(trace, args, after: int) -> int:
    """`exceptions` on a C trace. `--limit` and `--after` are already
    checked and parsed by `exceptions_cmd.run`."""
    caps.print_incomplete(
        trace, "a signal recorded after the cut is not below, and its "
               "absence here is not evidence it had none")
    idx = Index(trace)
    if not idx.raises:
        line, status = _gap(trace)
        print(line)
        return status

    judged = [(event, _disposition(trace, event)) for event in idx.raises]
    seen = []
    for event, disposition in judged:
        if disposition.tag != "uncaught":
            continue
        text = _shown(_exc(event))
        if text in seen:
            continue
        seen.append(text)
        print(f"uncaught: {text}")

    scope = [(event, disposition) for event, disposition in judged
             if event.id > after]
    skipped = len(judged) - len(scope)
    if skipped:
        print(f"raised ({len(scope)} of {len(idx.raises)}; {skipped} "
              f"earlier raise(s) skipped by --after e{after}):")
    else:
        print(f"raised ({len(scope)}):")

    shown, last = 0, after
    for event, disposition in scope:
        if shown >= args.limit:
            break
        print(_raise_line(trace, event))
        print(f"    {disposition.verdict}")
        shown, last = shown + 1, event.id
    note = more_note(
        len(scope), shown,
        f"sensorium exceptions {shlex.quote(args.run)} "
        f"--after e{last} --limit {args.limit}")
    if note:
        print(note)
    return ANSWERED
