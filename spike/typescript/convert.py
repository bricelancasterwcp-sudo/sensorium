#!/usr/bin/env python3
"""THROWAWAY spike converter: one spool (pid-threadId.jsonl) -> one format-4
SQLite trace, written with sensorium's own store module so E7 reads a trace
the real reader opens. Usage: convert.py <spool-dir> <store-dir> [--json]."""
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from sensorium.store import db  # noqa: E402

CAUSAL = ("CALL", "RETURN", "RAISE", "HANDLED")
RECORDER = "sensorium-ts 0.0.0-spike"
CAPABILITIES = {"line": False, "locals": False, "return_value": True, "tasks": True,
                "threads": False, "children": False, "stdin": False, "output": False,
                "object_identity": False, "refocus": False, "err_flow": True}


class Fp:
    def __init__(self):
        self.h = hashlib.blake2b(digest_size=16)
        self.n = 0

    def update(self, file, qual, kind):
        self.h.update(f"{file}\x1f{qual}\x1f{kind}\n".encode())
        self.n += 1


def run_id(start_ts):
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(start_ts)) + "-" + secrets.token_hex(3)


def convert(spool: Path, store: Path, invocation: str) -> dict:
    recs = [json.loads(line) for line in spool.read_text().splitlines() if line.strip()]
    boot = next(r for r in recs if r["e"] == "BOOT")
    exit_rec = next((r for r in recs if r["e"] == "EXIT"), None)
    rid = run_id(boot["startTs"])
    traces = store / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    path = traces / f"{rid}.db"
    conn = db.create_trace(path)
    cur = conn.cursor()

    files = {}      # file id -> (rel, [(qual, line)], sha)
    code_ids = {}   # (rel, qual, line) -> code id
    frames = {}     # rt frame id -> {"db": id, "code": code id, "depth": d, "task": t}
    fp_thread = Fp()
    fp_tasks = {}
    task_names = {}
    ev_id = 0
    truncated = 0
    counts = {k: 0 for k in ("CALL", "RETURN", "RAISE", "HANDLED", "YIELD", "RESUME", "UNWIND", "TASK", "FILE")}

    def code_for(file_id, idx):
        rel, codes, _ = files[file_id]
        qual, line = codes[idx]
        key = (rel, qual, line)
        if key not in code_ids:
            cur.execute("INSERT INTO code_objects (file, qualname, firstlineno) VALUES (?, ?, ?)", key)
            code_ids[key] = cur.lastrowid
        return code_ids[key], rel, qual

    def event(kind, frame_db, code_db, line, payload, task, ts):
        nonlocal ev_id
        ev_id += 1
        cur.execute("INSERT INTO events (id, ts_ns, thread_id, kind, frame_id, code_id, line, payload, task_id) "
                    "VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)",
                    (ev_id, ts, kind, frame_db, code_db, line, json.dumps(payload), task))
        return ev_id

    def touch_fp(task, rel, qual, kind):
        if kind not in CAUSAL:
            return
        fp = fp_tasks.setdefault(task, Fp()) if task is not None else fp_thread
        fp.update(rel, qual, kind)

    for r in recs:
        e = r["e"]
        if e in counts:
            counts[e] += 1
        if e == "FILE":
            files[r["id"]] = (r["path"], [tuple(c) for c in r["codes"]], r["sha"])
        elif e == "TASK":
            task_names[r["id"]] = r["name"]
            cur.execute("INSERT INTO tasks (id, name, thread_id) VALUES (?, ?, 1)", (r["id"], r["name"]))
            fp_tasks.setdefault(r["id"], Fp())
        elif e == "CALL":
            code_db, rel, qual = code_for(r["file"], r["c"])
            parent = frames.get(r["p"]) if r.get("p") is not None else None
            depth = parent["depth"] + 1 if parent else 0
            eid = event("CALL", None, code_db, None, {"args": {}, "unread": ["locals"]}, r.get("t"), r["ts"])
            cur.execute("INSERT INTO frames (parent_id, code_id, call_event_id, return_event_id, depth, thread_id, "
                        "closed_by, unwind_exc, kind) VALUES (?, ?, ?, NULL, ?, 1, NULL, NULL, 'function')",
                        (parent["db"] if parent else None, code_db, eid, depth))
            fdb = cur.lastrowid
            cur.execute("UPDATE events SET frame_id = ? WHERE id = ?", (fdb, eid))
            frames[r["f"]] = {"db": fdb, "code": code_db, "depth": depth, "rel": rel, "qual": qual}
            touch_fp(r.get("t"), rel, qual, "CALL")
        elif e in ("RETURN", "YIELD", "RESUME", "UNWIND"):
            f = frames.get(r["f"])
            if f is None:
                continue
            if e == "RETURN":
                v = r["v"]
                if v.get("trunc"):
                    truncated += 1
                eid = event("RETURN", f["db"], f["code"], None, {"value": v, "outcome": "ok"}, r.get("t"), r["ts"])
                cur.execute("UPDATE frames SET return_event_id = ?, closed_by = 'return' WHERE id = ?", (eid, f["db"]))
                touch_fp(r.get("t"), f["rel"], f["qual"], "RETURN")
            elif e == "YIELD":
                event("YIELD", f["db"], f["code"], None, {"awaiting": "Promise"}, r.get("t"), r["ts"])
            elif e == "RESUME":
                event("RESUME", f["db"], f["code"], None, {}, r.get("t"), r["ts"])
            else:
                exc = dict(r["x"], kind="throw")
                cur.execute("UPDATE frames SET closed_by = 'unwind', unwind_exc = ? WHERE id = ?",
                            (json.dumps(exc), f["db"]))
        elif e in ("RAISE", "HANDLED"):
            f = frames.get(r["f"]) if r.get("f") is not None else None
            exc = dict(r["x"], kind=r.get("basis", "throw"))
            payload = {"exc": exc}
            if r.get("sink"):
                payload["sink"] = r["sink"]
            if r.get("basis"):
                payload["basis"] = r["basis"]
            event(e, f["db"] if f else None, f["code"] if f else None, r.get("l"), payload, r.get("t"), r["ts"])
            if f:
                touch_fp(r.get("t"), f["rel"], f["qual"], e)

    cur.execute("INSERT INTO fingerprints (thread_id, hash, n_events) VALUES (1, ?, ?)",
                (fp_thread.h.hexdigest(), fp_thread.n))
    for tid, fp in fp_tasks.items():
        cur.execute("INSERT INTO task_fingerprints (task_id, name, hash, n_events) VALUES (?, ?, ?, ?)",
                    (tid, task_names.get(tid), fp.h.hexdigest(), fp.n))

    end_ts = exit_rec["endTs"] if exit_rec else (recs[-1]["ts"] - boot["ts"]) / 1e9 + boot["startTs"]
    meta = {
        "run_id": rid, "argv": boot["argv"], "cwd": boot["cwd"], "env_hash": boot["envHash"],
        "start_ts": boot["startTs"], "end_ts": end_ts,
        "exit_status": None, "exit_status_basis": "unwitnessed",
        "exit_self_reported": exit_rec["code"] if exit_rec else None,
        "main_thread_ident": 1, "fingerprint_basis": "per-task", "truncated_count": truncated,
        "source_hashes": {rel: sha for rel, _, sha in files.values()},
        "recorder": RECORDER, "lang": "typescript", "capabilities": CAPABILITIES,
        "invocation": invocation, "container": {"pid": boot["pid"], "ppid": boot["ppid"],
                                                 "threadId": boot["threadId"], "isMainThread": boot["isMainThread"]},
        "node": boot["node"], "tier": boot["tier"],
    }
    for k, v in meta.items():
        db.set_meta(conn, k, v)
    conn.commit()
    missing = db.missing_required(conn)
    conn.close()
    return {"run": rid, "trace": str(path), "spool": spool.name, "events": ev_id, "counts": counts,
            "tasks": len(task_names), "missing_required": missing}


def main():
    spool_dir, store = Path(sys.argv[1]), Path(sys.argv[2])
    out = [convert(p, store, spool_dir.name) for p in sorted(spool_dir.glob("*.jsonl"))]
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        for o in out:
            print(f"run: {o['run']}  spool: {o['spool']}  events: {o['events']}  tasks: {o['tasks']}  "
                  f"missing: {o['missing_required']}")


if __name__ == "__main__":
    main()
