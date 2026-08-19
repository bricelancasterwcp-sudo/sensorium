"""Call-tree slices: what actually ran, in what order."""
from sensorium import paths
from sensorium.query.fmt import (fmt_args, fmt_exc, fmt_value, parse_eref,
                                 parse_fref)
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("tree", help="call-tree slice")
    p.add_argument("run")
    p.add_argument("--root", default=None, help="frame ref (f12)")
    p.add_argument("--around", default=None, help="event ref (e40)")
    p.add_argument("--depth", type=int, default=4)
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(func=run)


def frame_line(trace, frame) -> str:
    code = trace.code(frame.code_id)
    call = trace.event(frame.call_event_id)
    args = fmt_args((call.payload or {}).get("args", {})) if call else ""
    if frame.closed_by == "unwind":
        tail = (f" !! {fmt_exc(frame.unwind_exc)}" if frame.unwind_exc
                else " !! unwound")
    elif frame.return_event_id is not None:
        ret = trace.event(frame.return_event_id)
        tail = f" -> {fmt_value((ret.payload or {}).get('value'))}"
    else:
        tail = " (open)"
    return f"f{frame.id} e{frame.call_event_id} {code.qualname}({args}){tail}"


def render_tree(trace, roots, depth_limit, max_lines):
    lines: list[str] = []
    cut = [0]

    def walk(frame, depth):
        if len(lines) >= max_lines or depth > depth_limit:
            cut[0] += 1
            return
        lines.append("  " * depth + frame_line(trace, frame))
        for ch in trace.children(frame.id):
            walk(ch, depth + 1)

    for r in roots:
        walk(r, 0)
    return lines, cut[0]


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    if args.around:
        f = trace.frame_containing(parse_eref(args.around))
        if f is None:
            print(f"no frame contains {args.around}")
            return 1
        chain = [f]
        while chain[-1].parent_id is not None:
            chain.append(trace.frame(chain[-1].parent_id))
        ancestors = list(reversed(chain[1:]))
        for depth, fr in enumerate(ancestors):
            print("  " * depth + frame_line(trace, fr))
        lines, cut = render_tree(trace, [f], args.depth, args.limit)
        for ln in lines:
            print("  " * len(ancestors) + ln)
    else:
        roots = ([trace.frame(parse_fref(args.root))] if args.root
                 else trace.roots())
        lines, cut = render_tree(trace, [r for r in roots if r], args.depth,
                                 args.limit)
        for ln in lines:
            print(ln)
        if cut:
            print(f"... {cut} subtree(s) beyond --depth {args.depth} or "
                  f"--limit {args.limit}; narrow with --root fN")
    return 0
