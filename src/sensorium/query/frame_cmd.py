"""One activation completely: args, local timeline, return, children."""
from sensorium import paths
from sensorium.query.fmt import (fmt_args, fmt_event, fmt_exc, fmt_value,
                                 parse_fref)
from sensorium.query.tree_cmd import frame_line
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
        if not matches:
            return None, ("no such frame: no recorded activations of "
                          f"{args.fn!r}")
        if not (1 <= args.nth <= len(matches)):
            return None, (
                f"--nth {args.nth} is out of range: {args.fn!r} has "
                f"{len(matches)} recorded activation(s); valid --nth is "
                f"1..{len(matches)}")
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
    print(f"f{f.id} {code.file.rsplit('/', 1)[-1]}:{code.qualname}  "
          f"[e{f.call_event_id}..{end}]  thread {f.thread_id}  "
          f"depth {f.depth}  closed: {f.closed_by or 'open'}")
    call = trace.event(f.call_event_id)
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
    kids = trace.children(f.id)
    if kids:
        print(f"children ({len(kids)}):")
        for ch in kids:
            print("  " + frame_line(trace, ch))
    else:
        print("children: (none)")
    return 0
