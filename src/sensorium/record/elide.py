"""Put an elided frame back into the trace because a failure is crossing it.

The raising frame and each elided ancestor are written outermost-first, so
the parent row exists before the child names it. The payload is a skeleton:
the arguments were not read. ``note_failure`` spends one elided count, so a
second callback for the same activation does not write a second CALL.
"""
from __future__ import annotations

import time

_WALK = 64


def materialize_elided(tracer, tls, frame) -> None:
    budget = tracer._budget
    if budget is None or frame is None:
        return
    chain = []
    seen = 0
    current = frame
    while current is not None and seen < _WALK:
        seen += 1
        key = id(current)
        if key in tls.live or tracer._parked_has(key):
            break
        code = current.f_code
        if budget.slot(id(code)) is not None:
            chain.append(current)
        current = current.f_back
    for current in reversed(chain):
        _one(tracer, tls, current)


def _one(tracer, tls, frame) -> None:
    if id(frame) in tls.live:
        return
    code = frame.f_code
    traced, fp_file, qual, _focused, kind, win_key = tracer._decide(code)
    if not traced or not tracer._budget.note_failure(id(code)):
        return
    tid = tls.thread_serial
    task = tracer._task_serial(tls)
    cid = tracer.writer.intern_code(code.co_filename, qual, code.co_firstlineno)
    parent = tracer._parent_of(tls, frame.f_back)
    payload = {"args": {}, "unread": ["locals"], "skeleton": "failure"}
    eid = tracer.writer.add_event(
        time.monotonic_ns(), tid, "CALL", None, cid, code.co_firstlineno,
        payload, task_id=task)
    pfid = parent[0] if parent is not None else None
    depth = parent[4] + 1 if parent is not None else 0
    fid = tracer.writer.open_frame(pfid, cid, eid, depth, tid, kind)
    in_window = bool(win_key is not None or (parent is not None and parent[5]))
    tls.live[id(frame)] = [fid, code, cid, {}, depth, in_window, False]
    tracer._fp_for(tid, task).update(fp_file, qual, "CALL")
