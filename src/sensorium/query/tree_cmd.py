"""Call-tree slices: what actually ran, in what order -- and who called it.

Parentage is DERIVED on format-2 traces (the caller frame, verified by code
identity) and ASSUMED on format-1 ones (v1's last-opened-frame guess); the
footer says which. Coroutines and generators open no frame and are shown as
events in their true position: under the frame that called them when that
frame was open, otherwise at the top of their task group. A framed call whose
caller has no frame is tagged with the caller's name and never re-parented.
"""
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


def task_label(trace, task_id) -> str:
    # A NULL name means one thing only: get_name() raised and the name could
    # not be read (the identity was still minted). Say that, rather than
    # "(unnamed)", which would claim the task HAD no name.
    if task_id is None:
        return "outside any event loop"
    t = trace.task(task_id)
    name = (t.name if (t is not None and t.name is not None)
            else "(name unreadable)")
    return f"task t{task_id}: {name}"


def _caller_tag(trace, frame) -> str:
    """`<- QUAL (unframed)` when the frame's caller is traced code that has
    no frame (a generator or coroutine body). Nothing for a true root or an
    untraced caller -- and nothing on a format-1 trace, which has no record."""
    if frame.parent_id is not None:
        return ""
    call = trace.event(frame.call_event_id)
    cc = (call.payload or {}).get("caller_code") if call else None
    if cc is None:
        return ""
    return f"  <- {trace.code(cc).qualname} (unframed)"


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
    return (f"f{frame.id} e{frame.call_event_id} {code.qualname}({args}){tail}"
            + _caller_tag(trace, frame))


def unframed_kind(ev) -> str:
    # Format-1 traces recorded no kind; "generator/coroutine" is all v1 knew.
    return (ev.payload or {}).get("unframed", "generator/coroutine")


def unframed_line(trace, ev) -> str:
    code = trace.code(ev.code_id)
    args = fmt_args((ev.payload or {}).get("args", {}))
    return f"e{ev.id} {code.qualname}({args})  [{unframed_kind(ev)}, unframed]"


def index_unframed(trace):
    """(by_parent_frame, parentless): every unframed call, split by whether
    its caller's frame was open. Computed once per command."""
    by_parent: dict[int, list] = {}
    parentless = []
    for ev in trace.unframed_calls():
        pf = (ev.payload or {}).get("parent_frame")
        if pf is None:
            parentless.append(ev)
        else:
            by_parent.setdefault(pf, []).append(ev)
    return by_parent, parentless


def render_tree(trace, roots, depth_limit, max_lines, unframed_by_parent=None):
    """Return (lines, cut_frames, cut_unframed): `cut_frames` is the actual
    Frame objects withheld because they crossed --depth or --limit, in
    encounter order -- never just a count. A caller that only reports the
    count and drops the frames themselves cannot point a reader at what was
    hidden. `cut_unframed` is the unframed-call events --limit withheld; they
    have no subtree, so they never cross --depth.

    Unframed calls whose caller is a frame in this subtree render as that
    frame's children, merged with the framed children by event id."""
    ubp = unframed_by_parent if unframed_by_parent is not None else {}
    lines: list[str] = []
    cut_frames: list = []
    cut_unframed: list = []

    def walk(frame, depth):
        if len(lines) >= max_lines or depth > depth_limit:
            cut_frames.append(frame)
            return
        lines.append("  " * depth + frame_line(trace, frame))
        kids = ([("f", ch.call_event_id, ch) for ch in trace.children(frame.id)]
                + [("u", ev.id, ev) for ev in ubp.get(frame.id, [])])
        kids.sort(key=lambda k: k[1])
        for kind, _eid, obj in kids:
            if kind == "f":
                walk(obj, depth + 1)
            elif len(lines) < max_lines:
                lines.append("  " * (depth + 1) + unframed_line(trace, obj))
            else:
                cut_unframed.append(obj)

    for r in roots:
        walk(r, 0)
    return lines, cut_frames, cut_unframed


def _truncation_note(run_ref, depth, limit, cut_frames,
                     cut_unframed=()) -> str | None:
    """Every branch that can withhold subtrees must report it -- silence
    here is indistinguishable from "that's the whole tree", which is
    exactly the unsupported claim this project forbids. The hint is a
    fully-instantiated, copy-pasteable command (a real frame id, the run
    ref actually in hand), not a template like "fN"."""
    parts = []
    if cut_frames:
        parts.append(f"{len(cut_frames)} subtree(s) beyond --depth {depth} or "
                     f"--limit {limit}; continue with: "
                     f"sensorium tree {run_ref} --root f{cut_frames[0].id}")
    if cut_unframed:
        parts.append(f"{len(cut_unframed)} unframed call(s) withheld by "
                     f"--limit {limit}; see them with: sensorium grep "
                     f"{run_ref} CALL")
    return ("... " + "; ".join(parts)) if parts else None


def _grouped(trace, roots, parentless):
    """Group roots and parentless unframed calls by task, in event order.
    Returns [(task_id, [(event_id, kind, obj)])] with None first."""
    groups: dict = {}
    for f in roots:
        call = trace.event(f.call_event_id)
        tid = call.task_id if call else None
        groups.setdefault(tid, []).append((f.call_event_id, "f", f))
    for ev in parentless:
        groups.setdefault(ev.task_id, []).append((ev.id, "u", ev))
    order = sorted(groups, key=lambda t: (t is not None, t or 0))
    return [(t, sorted(groups[t], key=lambda i: i[0])) for t in order]


def _has_caller_code(trace, frame) -> bool:
    call = trace.event(frame.call_event_id)
    return bool(call and (call.payload or {}).get("caller_code") is not None)


def _footers(trace, n_unframed: int) -> list[str]:
    out = []
    if trace.tasks():
        out.append("order between tasks is wall-clock (event ids), not causal; "
                   "within one task it is causal")
    if n_unframed:
        out.append(f"{n_unframed} unframed call(s) shown as events: "
                   "coroutine/generator code opens no frame in this version "
                   "(no tree, frame, focus or watch inside them)")
    if trace.parentage_basis() == "assumed":
        out.append("parentage: ASSUMED -- recorded by a format-1 sensorium, "
                   "whose parent was the last frame opened on the thread, not "
                   "the caller; async, generators and C callbacks break that. "
                   "Re-record to derive it.")
    return out


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
    by_parent, parentless = index_unframed(trace)
    n_unframed = sum(len(v) for v in by_parent.values()) + len(parentless)
    if args.around:
        eid = parse_eref(args.around)
        f = trace.frame_containing(eid)
        if f is None:
            ev = trace.event(eid)
            # frame_containing is None for a CALL event only when no frame
            # was opened for it: that is what "unframed" means.
            if ev is not None and ev.kind == "CALL" and ev.code_id is not None:
                q = trace.code(ev.code_id).qualname
                print(f"e{eid} is an unframed CALL of {q} ({unframed_kind(ev)}); "
                      f"no frame contains it. Its events: sensorium grep "
                      f"{args.run} {q}")
            else:
                print(f"no frame contains {args.around}")
            return 1
        chain = [f]
        while chain[-1].parent_id is not None:
            chain.append(trace.frame(chain[-1].parent_id))
        ancestors = list(reversed(chain[1:]))
        for depth, fr in enumerate(ancestors):
            print("  " * depth + frame_line(trace, fr))
        lines, cut_frames, cut_u = render_tree(trace, [f], args.depth,
                                               args.limit, by_parent)
        for ln in lines:
            print("  " * len(ancestors) + ln)
        note = _truncation_note(args.run, args.depth, args.limit, cut_frames,
                                cut_u)
        if note:
            print(note)
        for ln in _footers(trace, 0):
            print(ln)
        return 0
    if args.root:
        # Resolve and refuse a missing frame, like `--around` and
        # `frame f<id>`. Filtering it silently to `[]` reaches the "no
        # frames recorded" line below -- a false claim (the trace HAS
        # frames) delivered as success (exit 0) on a bad reference.
        root = trace.frame(parse_fref(args.root))
        if root is None:
            print(f"no such frame: {args.root} does not exist")
            return 1
        lines, cut_frames, cut_u = render_tree(trace, [root], args.depth,
                                               args.limit, by_parent)
        for ln in lines:
            print(ln)
        note = _truncation_note(args.run, args.depth, args.limit, cut_frames,
                                cut_u)
        if note:
            print(note)
        for ln in _footers(trace, 0):
            print(ln)
        return 0
    # One path for every trace. A synchronous trace has no tasks, so it is
    # one unlabelled group whose roots render at indent 0 in event order --
    # byte-identical to v1 -- and --limit is one budget across the whole
    # output, as it was.
    show_headers = bool(trace.tasks())
    cut_frames_all: list = []
    cut_unframed_all: list = []
    printed = 0
    for tid, items in _grouped(trace, trace.roots(), parentless):
        if show_headers:
            print(task_label(trace, tid))
        for _eid, kind, obj in items:
            budget = args.limit - printed
            if kind == "u":
                if budget <= 0:
                    cut_unframed_all.append(obj)
                    continue
                print(("  " if show_headers else "") + unframed_line(trace, obj))
                printed += 1
                continue
            if budget <= 0:
                cut_frames_all.append(obj)
                continue
            base = ((1 if show_headers else 0)
                    + (1 if _has_caller_code(trace, obj) else 0))
            lines, cut, cut_u = render_tree(trace, [obj], args.depth, budget,
                                            by_parent)
            cut_frames_all += cut
            cut_unframed_all += cut_u
            for ln in lines:
                print("  " * base + ln)
            printed += len(lines)
    note = _truncation_note(args.run, args.depth, args.limit, cut_frames_all,
                            cut_unframed_all)
    if note:
        print(note)
    elif printed == 0:
        print("no frames recorded")
    for ln in _footers(trace, n_unframed):
        print(ln)
    return 0
