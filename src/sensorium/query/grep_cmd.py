"""Search events by qualname or captured-value content.

The pattern is a plain substring matched against the *rendered* `fmt_event`
line, which is what lets one flag search both names and values: the same
query finds `parse_row` the function and `'carol,x7'` the argument it was
called with. The rendered line also carries `e<id>` and the kind, so a
pattern like `RETURN` matches every return -- that is a documented
consequence of matching what is printed, not a bug.

Anything withheld is stated, and the continuation hint is a fully
instantiated command carrying every filter of the search it continues. A
hint that dropped `--kind`/`--fn` would resume a *different* search and
quietly show rows the first page had excluded.
"""
import shlex

from sensorium import paths
from sensorium.exit import ANSWERED, BAD_CALL, UNSETTLED
from sensorium.query.caps import none_status, print_incomplete
from sensorium.query.fmt import fmt_event, more_note, parse_eref
from sensorium.store.reader import Trace

KINDS = ("CALL", "RETURN", "RAISE", "HANDLED", "LINE")


def add_parser(sub) -> None:
    p = sub.add_parser("grep", help="search events by name or value")
    p.add_argument("run")
    p.add_argument("pattern")
    p.add_argument("--kind", default=None, choices=KINDS)
    p.add_argument("--fn", default=None, help="qualname substring filter")
    p.add_argument("--after", default=None, help="event ref to resume from")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=run)


def continue_cmd(args, last: int) -> str:
    """The exact command that shows the next page of *this* search."""
    parts = ["sensorium", "grep", shlex.quote(args.run),
             shlex.quote(args.pattern)]
    if args.kind:
        parts += ["--kind", args.kind]
    if args.fn:
        parts += ["--fn", shlex.quote(args.fn)]
    parts += ["--limit", str(args.limit), "--after", f"e{last}"]
    return " ".join(parts)


def _no_line_capture(trace, args) -> bool:
    """`--kind LINE` against a run that recorded no LINE event at all.

    Zero matches here is not the trace saying "no": nothing of that kind was
    ever written down, so the search had nothing to be true or false about.
    The note below and the exit status are the same fact, so both read it
    from here -- deciding the status by matching the note's wording would
    break the next time the wording improves.
    """
    return args.kind == "LINE" and not trace.counts().get("LINE")


def _empty_note(trace, args, scanned: int, considered: int,
                after: int) -> list[str]:
    """Zero matches is ambiguous on its own -- say what was searched.

    Every active filter has to be named. Reporting "scanned 11 event(s); none
    contained 'alice'" when `--fn` removed the three that did contain it
    states a false fact about the trace, so the rows `--fn` took out are
    counted separately and the claim is scoped to what actually remained.
    """
    where = f" after e{after}" if after else ""
    scope = f" of kind {args.kind}" if args.kind else ""
    head = f"scanned {scanned} event(s){scope}{where}"
    if args.fn is not None:
        lines = [f"{head}; {scanned - considered} excluded by "
                 f"--fn {args.fn!r}; none of the remaining {considered} "
                 f"contained {args.pattern!r}"]
    else:
        lines = [f"{head}; none contained {args.pattern!r}"]
    if _no_line_capture(trace, args):
        lines.append("this run recorded no LINE events at all: line-level "
                     "capture needs --focus MODULE[:QUALNAME] at record time")
    return lines


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return BAD_CALL
    after = parse_eref(args.after) if args.after else 0
    trace = Trace.open(paths.find_trace(args.run))
    # Above the rows, because `matches: 0` on such a trace exits 3 and a 3
    # the output does not explain is a number the reader cannot act on.
    print_incomplete(trace, "the events searched below are not all the "
                            "events this run had")
    shown = total = 0
    scanned = considered = 0
    last = after
    for e in trace.events(kind=args.kind, after=after):
        if e.code_id is None:
            continue
        scanned += 1
        if args.fn and args.fn not in trace.code(e.code_id).qualname:
            continue
        considered += 1
        line = fmt_event(trace, e)
        if args.pattern not in line:
            continue
        total += 1
        if shown < args.limit:
            print(line)
            shown += 1
            last = e.id
    clipped = f" (showing {shown})" if shown < total else ""
    print(f"matches: {total}{clipped}")
    if total == 0:
        for note in _empty_note(trace, args, scanned, considered, after):
            print(note)
        if _no_line_capture(trace, args):
            # The recording, not the program, is why there is nothing to
            # show: re-record with --focus and ask again.
            return UNSETTLED
        # Nothing matched. Whether that is the trace answering "none" or a
        # recording that stopped before the match would have been written
        # is the one question `none_status` answers, for every command that
        # can print an empty result.
        return none_status(trace)
    note = more_note(total, shown, continue_cmd(args, last))
    if note:
        print(note)
    return ANSWERED
