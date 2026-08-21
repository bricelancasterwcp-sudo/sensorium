"""One activation completely: args, local timeline, return, children."""
from sensorium import paths
from sensorium.query.fmt import (fmt_args, fmt_event, fmt_exc, fmt_value,
                                 parse_fref)
from sensorium.query.tree_cmd import (frame_line, unframed_kind,
                                      unframed_line)
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("frame", help="one activation in full")
    p.add_argument("run")
    p.add_argument("frame", nargs="?", default=None, help="frame ref (f12)")
    p.add_argument("--fn", default=None, help="qualname of the function")
    p.add_argument("--nth", type=int, default=1, help="which activation (1-based)")
    p.set_defaults(func=run)


def _resolve(trace, args):
    """Return (frame, error). `error` is set (and frame is None) whenever
    resolution fails, so `run` can report exactly why instead of a single
    catch-all message -- an out-of-range --nth (<=0, or beyond how many
    activations were actually recorded) must refuse loudly, never silently
    wrap to the wrong activation or raise an uncaught IndexError."""
    if args.frame:
        f = trace.frame(parse_fref(args.frame))
        if f is None:
            return None, f"no such frame: {args.frame} does not exist"
        return f, None
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
                    f"{args.run} {args.fn}")
            return None, ("no such frame: no recorded activations of "
                          f"{args.fn!r}")
        if not (1 <= args.nth <= len(matches)):
            mixed = (f" and {len(calls)} recorded but unframed ({kinds})"
                     if calls else "")
            tail = (f"; its unframed events: sensorium grep {args.run} "
                    f"{args.fn}" if calls else "")
            return None, (
                f"--nth {args.nth} is out of range: {args.fn!r} has "
                f"{len(matches)} framed activation(s){mixed}; valid --nth "
                f"is 1..{len(matches)} over the framed ones{tail}")
        return matches[args.nth - 1], None
    return None, "no such frame; give f<id> or --fn QUALNAME [--nth N]"


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    f, err = _resolve(trace, args)
    if f is None:
        print(err)
        return 1
    code = trace.code(f.code_id)
    end = f"e{f.return_event_id}" if f.return_event_id is not None else "?"
    call = trace.event(f.call_event_id)
    task = ""
    if call is not None and call.task_id is not None:
        t = trace.task(call.task_id)
        name = (t.name if (t is not None and t.name is not None)
                else "name unreadable")
        task = f"  task t{call.task_id} ({name})"
    print(f"f{f.id} {code.file.rsplit('/', 1)[-1]}:{code.qualname}  "
          f"[e{f.call_event_id}..{end}]  thread {f.thread_id}{task}  "
          f"depth {f.depth}  closed: {f.closed_by or 'open'}")
    if trace.parentage_basis() == "assumed":
        print("parentage: assumed (format-1 trace) -- depth and the parent "
              "chain are v1's last-opened-frame guess")
    args_p = (call.payload or {}).get("args", {}) if call else {}
    print("args: " + (fmt_args(args_p, limit=99) or "(none)"))
    lines = [e for e in trace.frame_events(f.id) if e.kind == "LINE"]
    if lines:
        print("timeline:")
        for e in lines:
            # A LINE payload may carry an "unbound" list of names that went
            # out of scope this step (`del x`, or the implicit unbind at the
            # end of `except E as e:`) alongside possibly-empty "deltas".
            # fmt_event already renders both -- reuse it rather than
            # re-deriving the rendering and silently dropping unbound names.
            print("  " + fmt_event(trace, e))
    else:
        mod = code.file.rsplit("/", 1)[-1].removesuffix(".py")
        print("timeline: not captured (locals need line-level focus; "
              f"refocus with --focus {mod}:{code.qualname})")
    if f.closed_by == "unwind":
        print("unwound: " + (fmt_exc(f.unwind_exc) if f.unwind_exc else "?"))
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
    return 0
