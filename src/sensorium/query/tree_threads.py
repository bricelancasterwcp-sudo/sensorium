"""Headings for OS threads in `tree`.

Task groups say which asyncio task a root ran in. They do not say which
OS thread, and a `Thread` body is a root of its own, so without a heading
it looks like a second entry point. The heading is printed only when the
trace recorded `thread_starts` AND more than one OS thread has roots.
Both conditions are required: a missing key is an older trace (or another
language) and must render as it does today, and a single thread must stay
byte-identical to that rendering, heading and all.

The link is a frame id taken from that meta and checked against the
trace. No id, or an id the trace does not hold, is "starter not recorded".
Nothing here invents `f0`.
"""


def _start_index(trace) -> dict | None:
    """thread serial -> {name, frame}, or None if the key was not recorded.

    None and an empty dict are different. None means this trace predates
    the key (or is not a Python recording) and `tree` must not group by
    thread. An empty dict means the recorder looked and stored no starts;
    extra threads still get a heading, without a link.
    """
    meta = trace.meta
    if "thread_starts" not in meta:
        return None
    raw = meta.get("thread_starts")
    out: dict = {}
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        tid = item.get("thread")
        # First row wins. A serial is minted once; a later duplicate would
        # be a second opinion about the same thread.
        if type(tid) is not int or tid in out:
            continue
        name = item.get("name")
        frame = item.get("frame")
        out[tid] = {
            "name": name if type(name) is str and name else None,
            "frame": frame if type(frame) is int else None,
        }
    return out


def _started_by(trace, frame_id) -> str | None:
    """`started by fN qualname` when `frame_id` is a frame this trace holds.

    The qualname is read from the trace, not from meta. An id that does
    not resolve is not a link: printing it would name a frame the trace
    does not contain.
    """
    if type(frame_id) is not int:
        return None
    frame = trace.frame(frame_id)
    if frame is None:
        return None
    try:
        qual = trace.code(frame.code_id).qualname
    except (KeyError, TypeError):
        return None
    if type(qual) is not str or not qual:
        return None
    return f"started by f{frame.id} {qual}"


def thread_heading(trace, thread_id: int) -> str:
    """One heading. The name is the recorded one, else `thread <id>`."""
    index = _start_index(trace) or {}
    info = index.get(thread_id) or {}
    name = info.get("name")
    if type(name) is str and name:
        # A newline in a name would forge a second tree line.
        shown = name.replace("\r", " ").replace("\n", " ")
        label = f"thread {shown}"
    else:
        label = f"thread {thread_id}"
    link = _started_by(trace, info.get("frame"))
    if link is None:
        return f"{label}  starter not recorded"
    return f"{label}  {link}"


def _recorded_main(trace) -> int | None:
    """The main thread, only when the trace recorded it.

    `main_thread_id()` otherwise guesses from event 1, and a worker's first
    event can land first. A heading built on that guess would name the
    wrong thread as extra.
    """
    if trace.main_thread_basis() != "recorded":
        return None
    main = trace.main_thread_id()
    return main if type(main) is int else None


def thread_note(trace, frame) -> str | None:
    """One line for `--root` / `--around`, or None.

    Those views show one neighbourhood, not the process. Listing every
    thread above them would describe threads the slice does not contain.
    The line is only when this frame itself ran off the main thread, and
    only when the trace recorded `thread_starts`. A missing key keeps the
    historical subtree, with no added line. No recorded main thread means
    no note: there is nothing to compare the frame's thread against.
    """
    if frame is None or _start_index(trace) is None:
        return None
    main = _recorded_main(trace)
    tid = frame.thread_id
    if main is None or tid is None or tid == main:
        return None
    return thread_heading(trace, tid)


def split_extra_threads(trace, groups):
    """None, or `(main_groups, extras)`.

    None means render `groups` unchanged. That is every trace without
    `thread_starts`, every trace whose roots share one OS thread, and any
    trace that did not record its main thread: heading all of them would
    be a guess about which group is "extra". An inferred main thread is
    not that record.

    `extras` is `(thread_id, items)` ordered by each thread's first event.
    Items are in event order. Task groups keep their order, with the extra
    threads' items removed and emptied groups dropped, so a one-thread
    trace that does not reach this split stays byte-identical and a trace
    with tasks keeps its task headers for the main thread.
    """
    if _start_index(trace) is None:
        return None
    distinct = set()
    for _gid, items in groups:
        for item in items:
            tid = item[2].thread_id
            if tid is not None:
                distinct.add(tid)
    if len(distinct) <= 1:
        return None
    main = _recorded_main(trace)
    # Without a recorded main thread every heading would be a guess about
    # which group is the extra one. Leave the historical grouping in place.
    if main is None:
        return None
    extras: dict = {}
    main_groups = []
    for gid, items in groups:
        keep = []
        for item in items:
            tid = item[2].thread_id
            if tid is not None and tid != main:
                extras.setdefault(tid, []).append(item)
            else:
                keep.append(item)
        if keep:
            main_groups.append((gid, keep))
    if not extras:
        return None
    ordered = []
    for tid, items in extras.items():
        items.sort(key=lambda item: item[0])
        ordered.append((tid, items))
    ordered.sort(key=lambda pair: pair[1][0][0])
    return main_groups, ordered
