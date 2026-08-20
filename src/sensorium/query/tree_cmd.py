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
    """Return (lines, cut_frames): `cut_frames` is the actual Frame objects
    withheld because they crossed --depth or --limit, in encounter order --
    never just a count. A caller that only reports the count and drops the
    frames themselves cannot point a reader at what was hidden."""
    lines: list[str] = []
    cut_frames: list = []

    def walk(frame, depth):
        if len(lines) >= max_lines or depth > depth_limit:
            cut_frames.append(frame)
            return
        lines.append("  " * depth + frame_line(trace, frame))
        for ch in trace.children(frame.id):
            walk(ch, depth + 1)

    for r in roots:
        walk(r, 0)
    return lines, cut_frames


def _truncation_note(run_ref, depth, limit, cut_frames) -> str | None:
    """Every branch that can withhold subtrees must report it -- silence
    here is indistinguishable from "that's the whole tree", which is
    exactly the unsupported claim this project forbids. The hint is a
    fully-instantiated, copy-pasteable command (a real frame id, the run
    ref actually in hand), not a template like "fN"."""
    if not cut_frames:
        return None
    return (f"... {len(cut_frames)} subtree(s) beyond --depth {depth} or "
            f"--limit {limit}; continue with: "
            f"sensorium tree {run_ref} --root f{cut_frames[0].id}")


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return 2
    if args.depth < 0:
        print(f"--depth must be >= 0 (got {args.depth}); "
              "depth 0 shows the root frames alone")
        return 2
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
        lines, cut_frames = render_tree(trace, [f], args.depth, args.limit)
        for ln in lines:
            print("  " * len(ancestors) + ln)
        note = _truncation_note(args.run, args.depth, args.limit, cut_frames)
        if note:
            print(note)
    else:
        if args.root:
            # Resolve and refuse a missing frame, like `--around` and
            # `frame f<id>`. Filtering it silently to `[]` reaches the "no
            # frames recorded" line below -- a false claim (the trace HAS
            # frames) delivered as success (exit 0) on a bad reference.
            root = trace.frame(parse_fref(args.root))
            if root is None:
                print(f"no such frame: {args.root} does not exist")
                return 1
            roots = [root]
        else:
            roots = trace.roots()
        lines, cut_frames = render_tree(trace, roots, args.depth, args.limit)
        for ln in lines:
            print(ln)
        note = _truncation_note(args.run, args.depth, args.limit, cut_frames)
        if note:
            print(note)
        elif not lines:
            print("no frames recorded")
    return 0
