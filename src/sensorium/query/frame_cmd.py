"""One activation completely: args, local timeline, return, children."""
from sensorium import paths
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE
from sensorium.query.fmt import (fmt_args, fmt_event, fmt_exc, fmt_value,
                                 parse_fref, unread_marker)
from sensorium.query.tree_cmd import (frame_line, unframed_kind,
                                      unframed_line)
from sensorium.query.vocab import terms
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("frame", help="one activation in full")
    p.add_argument("run")
    p.add_argument("frame", nargs="?", default=None, help="frame ref (f12)")
    p.add_argument("--fn", default=None, help="qualname of the function")
    p.add_argument("--nth", type=int, default=1, help="which activation (1-based)")
    p.set_defaults(func=run)


def _resolve(trace, args):
    """Return (frame, error, exit status). `error` is set (and frame is
    None) whenever resolution fails, so `run` can report exactly why
    instead of a single catch-all message -- an out-of-range --nth (<=0, or
    beyond how many activations were actually recorded) must refuse loudly,
    never silently wrap to the wrong activation or raise an uncaught
    IndexError.

    The status travels WITH the message because the two say the same thing
    and only this function knows which it is: a reference the trace simply
    does not hold is the trace answering "no" (NEGATIVE), while an --nth
    past the end or no reference at all is the call being wrong
    (BAD_CALL). Deciding that in `run` would mean matching on the message
    text, and the text is rewritten whenever it can be made clearer."""
    if args.frame:
        f = trace.frame(parse_fref(args.frame))
        if f is None:
            return (None, f"no such frame: {args.frame} does not exist",
                    NEGATIVE)
        return f, None, ANSWERED
    if args.fn:
        matches = [f for f in trace.frames()
                   if trace.code(f.code_id).qualname == args.fn]
        # Computed for BOTH branches: one qualname can name several code
        # objects (two modules, a def rebound), and some of them can be
        # coroutines while others are plain functions. Counting only the
        # frames then reports a total `grep` contradicts.
        codes = [c for c in trace.codes() if c.qualname == args.fn]
        calls = [e for c in codes for e in trace.unframed_calls(code_id=c.id)]
        kinds = "/".join(sorted({unframed_kind(c) for c in calls}))
        if not matches:
            if calls:
                # Recorded, not framed: the activations are in the trace,
                # as CALL events -- denying them contradicts `grep` on the
                # same trace, which is what v1 did. The kinds are a SET:
                # naming the first call's kind would claim every one of them
                # was that kind.
                return None, (
                    f"{args.fn!r} was recorded as {len(calls)} call(s) but "
                    f"not framed ({kinds}): no frame, locals "
                    "or children to show; its events: sensorium grep "
                    f"{args.run} {args.fn}"), NEGATIVE
            return None, ("no such frame: no recorded activations of "
                          f"{args.fn!r}"), NEGATIVE
        if not (1 <= args.nth <= len(matches)):
            mixed = (f" and {len(calls)} recorded but unframed ({kinds})"
                     if calls else "")
            tail = (f"; its unframed events: sensorium grep {args.run} "
                    f"{args.fn}" if calls else "")
            return None, (
                f"--nth {args.nth} is out of range: {args.fn!r} has "
                f"{len(matches)} framed activation(s){mixed}; valid --nth "
                f"is 1..{len(matches)} over the framed ones{tail}"), BAD_CALL
        return matches[args.nth - 1], None, ANSWERED
    return (None, "no such frame; give f<id> or --fn QUALNAME [--nth N]",
            BAD_CALL)


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    # `status` is carried past the refusal branch and returned at the end:
    # `_resolve` is the one place that decides this command's answer, and a
    # second ANSWERED written down here would be a second place to change.
    f, err, status = _resolve(trace, args)
    if f is None:
        print(err)
        return status
    code = trace.code(f.code_id)
    end = f"e{f.return_event_id}" if f.return_event_id is not None else "?"
    call = trace.event(f.call_event_id)
    task = ""
    if call is not None and call.task_id is not None:
        t = trace.task(call.task_id)
        name = t.name if t is not None else None
        # The parentheses belong to the LABEL, not to the name: a unit whose
        # name could not be read has a whole sentence of its own, and what
        # that sentence says differs by language (`vocab.Terms`).
        label = (f"({name})" if name is not None
                 else terms(trace).unnamed_task)
        task = f"  task t{call.task_id} {label}"
    # A non-function kind is marked exactly as `tree` marks it (frame_line):
    # nothing for an ordinary call, `[coroutine]`/`[generator]`/etc. for the
    # rest. The state tail is derived by `frame_state` (spec D2) and shown
    # whenever it says something arc 1's `closed: {closed_by}` did not
    # already say -- a plain function that simply returned, raised, or is
    # still open keeps the byte-identical arc-1 header; every suspension
    # state (and every non-function kind, even one that returned normally)
    # gets its own `state:` segment because "closed: return" alone would
    # hide THAT it suspended along the way.
    state = trace.frame_state(f)
    kind_marker = f"  [{f.kind}]" if f.kind != "function" else ""
    show_state = (f.kind != "function"
                  or state.state not in ("returned", "raised", "open"))
    state_tail = ((f"  state: {state.state}"
                   + (f" at L{state.line}" if state.line else ""))
                  if show_state else "")
    print(f"f{f.id} {code.file.rsplit('/', 1)[-1]}:{code.qualname}{kind_marker}  "
          f"[e{f.call_event_id}..{end}]  thread {f.thread_id}{task}  "
          f"depth {f.depth}  closed: {f.closed_by or 'open'}{state_tail}")
    if trace.parentage_basis() == "assumed":
        print("parentage: assumed (format-1 trace) -- depth and the parent "
              "chain are v1's last-opened-frame guess")
    call_p = (call.payload or {}) if call else {}
    # "(none)" is only true when the arguments were READ and there were
    # none. When the payload says they went unread, that marker is the whole
    # answer: "(none)" there is a positive claim about the call the trace
    # never made -- the same marker `grep` and `tree` print for this event.
    rendered = fmt_args(call_p.get("args", {}), limit=99)
    marker = unread_marker(call_p)
    print("args: " + (rendered + marker if rendered else marker.lstrip()
                      or "(none)"))
    # LINE rows need --focus to be captured at all; YIELD/RESUME rows do
    # not -- they mark a real suspension point regardless. Interleaving both
    # kinds (in event order, since frame_events is ORDER BY id) means a
    # focused coroutine's timeline shows exactly where it parked and resumed
    # alongside its locals, not just the two disconnected facts.
    lines = [e for e in trace.frame_events(f.id)
             if e.kind in ("LINE", "YIELD", "RESUME")]
    line_rows = [e for e in lines if e.kind == "LINE"]
    if line_rows:
        print("timeline:")
        for e in lines:
            # A LINE payload may carry an "unbound" list of names that went
            # out of scope this step (`del x`, or the implicit unbind at the
            # end of `except E as e:`) alongside possibly-empty "deltas".
            # fmt_event already renders both -- reuse it rather than
            # re-deriving the rendering and silently dropping unbound names.
            prefix = "~ " if e.kind in ("YIELD", "RESUME") else ""
            print("  " + prefix + fmt_event(trace, e))
    else:
        mod = code.file.rsplit("/", 1)[-1].removesuffix(".py")
        # The reason a timeline is missing is not the same in both
        # languages, and naming a `--focus` command on a trace whose
        # recorder produces no LINE events -- and whose `refocus` refuses --
        # would send the reader to a command that cannot help.
        print("timeline: not captured ("
              + terms(trace).timeline_hint.format(mod=mod,
                                                  qualname=code.qualname)
              + ")")
        # Locals were never captured, but a suspension is not a local -- it
        # is still a fact this trace holds, and hiding it because --focus
        # wasn't on THIS frame would be a second, needless loss on top of
        # the first.
        susp_rows = [e for e in lines if e.kind != "LINE"]
        if susp_rows:
            print("timeline (suspensions only):")
            for e in susp_rows:
                print("  ~ " + fmt_event(trace, e))
    if f.closed_by == "unwind":
        # A Rust panic carries the `loc` it fired at, which is not the
        # frame's own line: printing it is the difference between "this
        # frame unwound" and "this frame unwound HERE".
        exc = f.unwind_exc or {}
        loc = exc.get("loc")
        print("unwound: " + (fmt_exc(exc) if f.unwind_exc else "?")
              + (f" at {loc}" if loc else ""))
    elif f.return_event_id is not None:
        ret = trace.event(f.return_event_id)
        print(f"return: {fmt_value((ret.payload or {}).get('value'))}")
    # Both kinds of callee, merged by event id: a frame whose only callees
    # were coroutines or generators has NO framed children, and listing only
    # those printed "(none)" over calls the trace plainly holds -- the same
    # contradiction with `grep` that `--fn` was fixed for.
    kids = sorted([(ch.call_event_id, "f", ch) for ch in trace.children(f.id)]
                  + [(ev.id, "u", ev) for ev in trace.unframed_calls()
                     if (ev.payload or {}).get("parent_frame") == f.id],
                  key=lambda k: k[0])
    if kids:
        print(f"children ({len(kids)}):")
        for _eid, kind, obj in kids:
            print("  " + (frame_line(trace, obj) if kind == "f"
                          else unframed_line(trace, obj)))
    else:
        print("children: (none)")
    return status
