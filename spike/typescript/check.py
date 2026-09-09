#!/usr/bin/env python3
"""THROWAWAY checker for E3 (async attribution), E4 (sites), E8 (swallows).
Reads the spool JSONL files of one probe invocation. Prints JSON.
Usage: check.py <spool-dir> <probes-dir>"""
import json
import re
import sys
from pathlib import Path

E3_NAMED = {"a", "b", "c", "p", "fanout", "work", "viaTimer", "viaEmitter", "handler"}
E3_EXPECTED = {
    "S1 chain": [("CALL", "a"), ("CALL", "b"), ("CALL", "c"), ("YIELD", "c"), ("YIELD", "b"), ("YIELD", "a"),
                 ("RESUME", "c"), ("RETURN", "c", "2"), ("RESUME", "b"), ("RETURN", "b", "3"),
                 ("RESUME", "a"), ("RETURN", "a", "4")],
    "S2 fanout": [("CALL", "fanout"), ("CALL", "p"), ("YIELD", "p"), ("CALL", "p"), ("YIELD", "p"), ("YIELD", "fanout"),
                  ("RESUME", "p"), ("RETURN", "p", "10"), ("RESUME", "p"), ("RETURN", "p", "20"),
                  ("RESUME", "fanout"), ("RETURN", "fanout", "[10,20]")],
    "S3 timer": [("CALL", "viaTimer"), ("YIELD", "viaTimer"), ("CALL", "work"), ("RETURN", "work", "7"),
                 ("RESUME", "viaTimer"), ("RETURN", "viaTimer", "7")],
    "S4 emitter": [("CALL", "viaEmitter"), ("CALL", "handler"), ("RETURN", "handler"), ("YIELD", "viaEmitter"),
                   ("CALL", "handler"), ("RETURN", "handler"), ("RESUME", "viaEmitter"), ("RETURN", "viaEmitter", "2")],
}
S2_ORDER_FREE = {"S2 fanout"}  # the two RESUME p / RETURN p pairs may swap


def load(spool: Path):
    recs = [json.loads(l) for l in spool.read_text().splitlines() if l.strip()]
    files = {r["id"]: r for r in recs if r["e"] == "FILE"}
    tasks = {r["id"]: r["name"] for r in recs if r["e"] == "TASK"}
    frames = {}
    rows = []
    for r in recs:
        if r["e"] == "CALL":
            qual, line = files[r["file"]]["codes"][r["c"]]
            frames[r["f"]] = (qual, line)
            rows.append({"kind": "CALL", "qual": qual, "task": r.get("t"), "f": r["f"]})
        elif r["e"] in ("RETURN", "YIELD", "RESUME", "UNWIND"):
            qual = frames.get(r["f"], ("?", 0))[0]
            row = {"kind": r["e"], "qual": qual, "task": r.get("t"), "f": r["f"]}
            if r["e"] == "RETURN":
                row["value"] = r["v"].get("v")
            rows.append(row)
        elif r["e"] in ("RAISE", "HANDLED"):
            qual = frames.get(r["f"], ("?", 0))[0] if r.get("f") is not None else None
            rows.append({"kind": r["e"], "qual": qual, "task": r.get("t"), "exc": r["x"], "line": r.get("l"),
                         "sink": r.get("sink"), "basis": r.get("basis")})
    return files, tasks, rows


def last_seg(q):
    return q.rsplit(".", 1)[-1]


def check_e3(files, tasks, rows):
    out = {}
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task"], []).append(row)
    for name, expected in E3_EXPECTED.items():
        tid = next((t for t, n in tasks.items() if n == name), None)
        got = [r for r in by_task.get(tid, []) if last_seg(r["qual"]) in E3_NAMED and r["kind"] in ("CALL", "RETURN", "YIELD", "RESUME")]
        exp_t = [tuple(e) for e in expected]
        # a RETURN row's value is compared only where the expected row names one
        got_t = []
        for i, r in enumerate(got):
            t = (r["kind"], last_seg(r["qual"]))
            if r["kind"] == "RETURN" and i < len(exp_t) and len(exp_t[i]) == 3:
                t = t + (re.sub(r"\s", "", str(r["value"])),)
            got_t.append(t)
        if name in S2_ORDER_FREE:
            ok = sorted(got_t) == sorted(exp_t) and got_t[:6] == exp_t[:6] and got_t[-2:] == exp_t[-2:]
        else:
            ok = got_t == exp_t
        out[name] = {"pass": ok, "expected": exp_t, "got": got_t}
    # negative control: rows of T2's a() carrying T1's task after T1's RETURN a
    t1 = next((t for t, n in tasks.items() if n == "T1 control"), None)
    t2 = next((t for t, n in tasks.items() if n == "T2 control"), None)
    t1_rows = [r for r in by_task.get(t1, []) if last_seg(r["qual"]) in E3_NAMED]
    t2_rows = [r for r in by_task.get(t2, []) if last_seg(r["qual"]) in E3_NAMED]
    t1_done = [i for i, r in enumerate(t1_rows) if r["kind"] == "RETURN" and last_seg(r["qual"]) == "a"]
    leaked = len(t1_rows) - (t1_done[-1] + 1) if t1_done else None
    out["negative control"] = {"pass": leaked == 0 and len(t2_rows) == 12,
                               "t1_rows_after_return_a": leaked, "t2_rows": len(t2_rows),
                               "t2_all_own_task": all(r["task"] == t2 for r in t2_rows)}
    out["all_pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict))
    return out


def check_e4(files, probes_dir: Path):
    expected = {}
    for pf in ("sites.probe.test.ts", "sites.component.tsx"):
        lines = (probes_dir / pf).read_text().splitlines()
        for i, l in enumerate(lines):
            m = re.match(r"\s*// SITE (\S+)", l)
            if m:
                expected[m.group(1)] = (pf, i + 2)  # the line after the marker, 1-based
    got = {}
    for f in files.values():
        for qual, line in f["codes"]:
            got.setdefault(last_seg(qual), []).append((Path(f["path"]).name, line))
    rows = []
    hits = 0
    for name, (pf, exp_line) in expected.items():
        cands = [g for g in got.get(name, []) if g[0] == pf]
        ok = any(g[1] == exp_line for g in cands)
        hits += ok
        rows.append({"site": name, "expected": exp_line, "got": [g[1] for g in cands], "pass": ok})
    return {"sites": len(expected), "hits": hits, "pass": hits >= 19, "rows": rows}


def check_e8(rows):
    ra = [r for r in rows if r["kind"] == "RAISE"]
    ha = [r for r in rows if r["kind"] == "HANDLED"]

    def find(kind_rows, msg=None, typ=None, sink=None, basis=None):
        return [r for r in kind_rows if (msg is None or r["exc"]["msg"] == msg) and (typ is None or r["exc"]["type"] == typ)
                and (sink is None or r.get("sink") == sink) and (basis is None or r.get("basis") == basis)]

    s1r, s1h = find(ra, msg="e1"), find(ha, msg="e1", sink="empty_catch")
    s2h = find(ha, msg="e2", sink="empty_catch_callback")
    s3r = find(ra, msg="e3", basis="unhandledRejection")
    s4r, s4h = find(ra, msg="not-an-error", typ="string"), find(ha, msg="not-an-error")
    s5r, s5h = find(ra, msg="e5"), find(ha, msg="e5")
    s5_same_serial = len(s5r) == 2 and len({r["exc"]["serial"] for r in s5r}) == 1
    shapes = {
        "1 empty catch clause": {"pass": len(s1r) == 1 and len(s1h) == 1, "raise": len(s1r), "handled_empty_catch": len(s1h)},
        "2 empty catch callback": {"pass": len(s2h) == 1 and not find(ra, msg="e2"), "handled": len(s2h), "raise": len(find(ra, msg="e2"))},
        "3 unhandled rejection": {"pass": len(s3r) == 1, "raise_unhandled": len(s3r)},
        "4 throw a string": {"pass": len(s4r) == 1 and len(s4h) == 1, "raise": len(s4r), "handled": len(s4h)},
        "5 rethrow same serial": {"pass": len(s5r) == 2 and len(s5h) == 2 and s5_same_serial, "raise": len(s5r), "handled": len(s5h), "same_serial": s5_same_serial},
    }
    return {"seen": sum(v["pass"] for v in shapes.values()), "of": 5, "shapes": shapes}


def main():
    spool_dir, probes_dir = Path(sys.argv[1]), Path(sys.argv[2])
    all_rows, all_files, per_env = [], {}, {}
    for sp in sorted(spool_dir.glob("*.jsonl")):
        files, tasks, rows = load(sp)
        paths = [f["path"] for f in files.values()]
        all_rows += rows
        all_files.update({(sp.name, k): v for k, v in files.items()})
        if any("async.probe" in p or "async.nodetest.probe" in p for p in paths):
            per_env["node"] = check_e3(files, tasks, rows)
        if any("async-jsdom.probe" in p for p in paths):
            per_env["jsdom"] = check_e3(files, tasks, rows)
    e4 = check_e4({k: v for k, v in all_files.items()}, probes_dir)
    e8 = check_e8(all_rows)
    print(json.dumps({"E3": per_env, "E4": e4, "E8": e8}, indent=1))


if __name__ == "__main__":
    main()
