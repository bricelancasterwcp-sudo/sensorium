"""Merge a child spool into the parent trace.

Split from `children.py` so that module stays under the line ceiling. The
parent calls `merge_children` there; these helpers only read a finished
spool and replay it through the parent's writer.
"""
import json
import os
import sqlite3
from pathlib import Path

from sensorium.record.fingerprint import CAUSAL_KINDS, Fingerprint


def merge_one(guard, path: Path) -> bool:
    conn = sqlite3.connect(path)
    try:
        frame_link = meta(conn, "parent_frame", None)
        if not frame_exists(guard, frame_link):
            frame_link = None
        depth_delta = link_depth(guard, frame_link)
        strings = _strings(conn)
        codes = {
            row[0]: (row[1], row[2], row[3])
            for row in conn.execute(
                "SELECT id, file, qualname, firstlineno FROM code_objects")
        }
        frames = {
            row[0]: row
            for row in conn.execute(
                "SELECT id, parent_id, code_id, call_event_id, depth, "
                "thread_id, kind, return_event_id, closed_by, unwind_exc "
                "FROM frames")
        }
        by_call = {row[3]: row for row in frames.values()}
        events = list(conn.execute(
            "SELECT id, ts_ns, thread_id, kind, frame_id, code_id, line, "
            "payload FROM events ORDER BY id"))
    finally:
        conn.close()
    if not frames:
        return False
    code_ids: dict[int, int] = {}
    frame_ids: dict[int, int] = {}
    thread_ids: dict[int, int] = {}
    next_thread = max_thread(guard) + 1
    fps: dict[int, Fingerprint] = {}
    for (eid, ts, tid, kind, fid, cid, line, payload) in events:
        if cid not in codes:
            continue
        file, qual, first = codes[cid]
        if cid not in code_ids:
            code_ids[cid] = guard.intern_code(file, qual, first)
        if tid not in thread_ids:
            thread_ids[tid] = next_thread
            next_thread += 1
        new_tid = thread_ids[tid]
        new_fid = frame_ids.get(fid) if fid is not None else None
        new_eid = guard.add_event(
            ts, new_tid, kind, new_fid, code_ids[cid], line,
            _payload(payload, strings), task_id=None)
        if kind in CAUSAL_KINDS:
            fps.setdefault(new_tid, Fingerprint()).update(file, qual, kind)
        opened = by_call.get(eid)
        if kind == "CALL" and opened is not None:
            parent_old = opened[1]
            if parent_old is None:
                parent_new = frame_link
            else:
                parent_new = frame_ids.get(parent_old)
            frame_ids[opened[0]] = guard.open_frame(
                parent_new, code_ids[cid], new_eid,
                int(opened[4]) + depth_delta, new_tid,
                opened[6] or "function")
        row = frames.get(fid) if fid is not None else None
        if row is not None and row[7] == eid and fid in frame_ids:
            exc = row[9]
            if isinstance(exc, str):
                try:
                    exc = json.loads(exc)
                except json.JSONDecodeError:
                    exc = None
            guard.close_frame(frame_ids[fid], new_eid, row[8] or "return", exc)
    for tid, fp in fps.items():
        guard.write_fingerprint(tid, fp.hexdigest(), fp.count)
    return True


def frame_exists(guard, fid) -> bool:
    if not isinstance(fid, int) or fid <= 0:
        return False
    writer = guard._w
    writer.flush()
    row = writer._conn.execute(
        "SELECT 1 FROM frames WHERE id = ?", (fid,)).fetchone()
    return row is not None


def link_depth(guard, fid) -> int:
    """How much to add so a child root sits one deeper than its parent."""
    if not isinstance(fid, int) or fid <= 0:
        return 0
    writer = guard._w
    row = writer._conn.execute(
        "SELECT depth FROM frames WHERE id = ?", (fid,)).fetchone()
    if row is None:
        return 0
    return int(row[0]) + 1


def spool_status(path: Path) -> tuple[bool, int | None]:
    conn = sqlite3.connect(path)
    try:
        done = meta(conn, "incomplete", True) is False
    finally:
        conn.close()
    try:
        pid = int(path.stem)
    except ValueError:
        pid = None
    return done, pid


def process_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def max_thread(guard) -> int:
    writer = guard._w
    writer.flush()
    found = 0
    for table in ("events", "fingerprints", "frames"):
        row = writer._conn.execute(
            f"SELECT COALESCE(MAX(thread_id), 0) FROM {table}").fetchone()
        found = max(found, row[0] or 0)
    return found


def _strings(conn) -> dict[int, str]:
    try:
        return {i: body for i, body in conn.execute(
            "SELECT id, body FROM strings")}
    except sqlite3.OperationalError:
        return {}


def _payload(raw, strings: dict[int, str]):
    if raw is None:
        return None
    if isinstance(raw, str) and raw.startswith("#") and raw[1:].isdigit():
        body = strings.get(int(raw[1:]))
        raw = body
        if raw is None:
            return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def meta(conn, key, default):
    row = conn.execute(
        "SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return default
