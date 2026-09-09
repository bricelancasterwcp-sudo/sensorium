#!/usr/bin/env python3
"""THROWAWAY: assemble results.json for the TypeScript mechanics spike from the
artifacts under /mnt/extra/sensorium-s5. None-versus-zero: an unmeasured
value is null with a reason in `dropped`."""
import glob
import json
import statistics
import subprocess
from pathlib import Path

B = Path("/mnt/extra/sensorium-s5")
PLAIN_FILES, PLAIN_TESTS = "372 passed (372)", "4278 passed (4278)"


def m(value, n, lens, dropped=()):
    return {"value": value, "n": n, "lens": lens, "dropped": list(dropped)}


def e0():
    files = sorted(glob.glob(str(B / "spool/full-call-2/*.jsonl")))
    pids, per, events, tasks, bytes_ = set(), [], 0, 0, 0
    causal = 0
    t0, t1 = None, None
    for f in files:
        boot = None
        nfiles = ntasks = n = 0
        for line in open(f):
            r = json.loads(line)
            n += 1
            e = r["e"]
            if e == "BOOT":
                boot = r
                t0 = boot["startTs"] if t0 is None else min(t0, boot["startTs"])
            elif e == "EXIT":
                t1 = r["endTs"] if t1 is None else max(t1, r["endTs"])
            elif e == "FILE" and ".test." in r["path"]:
                nfiles += 1
            elif e == "TASK":
                ntasks += 1
            if e in ("CALL", "RETURN", "RAISE", "HANDLED"):
                causal += 1
        pids.add(boot["pid"])
        per.append((nfiles, boot["threadId"], boot["isMainThread"]))
        events += n
        tasks += ntasks
        bytes_ += Path(f).stat().st_size
    kinds = {"child process per test file": sum(1 for p in per if p[2] and p[1] == 0)}
    return {
        "containers": m(len(files), 1, "full suite, tier call, run full-call-2"),
        "distinct_pids": m(len(pids), 1, "BOOT records"),
        "test_files_per_container": m({"min": min(p[0] for p in per), "max": max(p[0] for p in per), "sum": sum(p[0] for p in per)}, 1, "FILE records naming a .test. path"),
        "container_kind": kinds,
        "tasks": m(tasks, 1, "TASK records = vitest test() boundaries"),
        "spool_lines": m(events, 1, "all record kinds"),
        "causal_events": m(causal, 1, "CALL/RETURN/RAISE/HANDLED"),
        "spool_bytes": m(bytes_, 1, "sum of spool file sizes"),
        "bytes_per_line": m(round(bytes_ / events, 1), 1, "spool bytes / lines"),
        "lines_per_second": m(round(events / (t1 - t0), 0) if t0 and t1 else None, 1, "lines / (last EXIT - first BOOT)", () if t0 and t1 else ("no BOOT/EXIT span",)),
        "verdict": "(a) container = child process, one per test file; test files as tasks; per-file identity holds",
    }


def e1():
    rows = [json.loads(l) for l in open(B / "arms.jsonl") if l.strip() and not l.startswith("DONE")]
    out = {}
    walls = {}
    for arm in ("plain", "off", "call"):
        rs = [r for r in rows if r["arm"] == arm]
        valid = [r for r in rs if r["rc"] == 0 and PLAIN_FILES in r["files"] and PLAIN_TESTS in r["tests"]]
        dropped = [f"run {r['i']}: rc={r['rc']} files={r['files']!r} tests={r['tests']!r}" for r in rs if r not in valid]
        ws = [r["wall"] for r in valid]
        walls[arm] = ws
        out[arm] = {
            "wall_median": m(statistics.median(ws) if len(ws) >= 5 else None, len(ws), f"{arm} arm, full suite, n planned 5", dropped if len(ws) < 5 else dropped),
            "walls": ws, "spread": round(max(ws) - min(ws), 2) if ws else None,
            "durations": [r["duration"] for r in valid],
        }
    if len(walls["plain"]) >= 5 and len(walls["off"]) >= 5:
        ratio = statistics.median(walls["off"]) / statistics.median(walls["plain"])
        out["off_over_plain"] = m(round(ratio, 4), 5, "medians", ())
        out["off_gate"] = "PASS (<= 1.10)" if ratio <= 1.10 else "FAIL (> 1.10): transform must be cached or the tier compiled"
    else:
        out["off_over_plain"] = m(None, 0, "medians", ("fewer than 5 valid runs in an arm",))
    if len(walls["plain"]) >= 5 and len(walls["call"]) >= 5:
        out["call_over_plain"] = m(round(statistics.median(walls["call"]) / statistics.median(walls["plain"]), 4), 5, "medians; reported beside Python 2.7x and Rust 2.16x, ungated")
    return out


def e2():
    c = json.load(open(B / "census.json"))
    big = {k: v for k, v in c["excluded"].items() if v / c["eligible"] > 0.01}
    return {
        "files": c["files"], "failed_files": c["failed_files"], "instrumented": c["instrumented"],
        "eligible": c["eligible"], "excluded": c["excluded"], "by_kind": c["by_kind"],
        "ratio": m(round(c["ratio"], 4), 1, "transform over the census set (frontend/src minus tests, .d.ts, test-setup)"),
        "excluded_over_1pct_unreasoned": big,
        "bloat": m(round(c["bloat"], 4), 1, "output chars / input chars"),
        "not_counted": ["new Function / eval bodies", "functions inside vi.mock factories (test files only, excluded by rule)"],
        "gate": "PASS" if c["ratio"] >= 0.95 and not big else "FAIL",
    }


def e3_e4_e8():
    d = json.load(open(B / "check-probes-3.json"))
    nt = json.load(open(B / "check-nodetest-2.json")) if (B / "check-nodetest-2.json").exists() else None
    e3 = {env: {k: v["pass"] for k, v in r.items() if isinstance(v, dict)} for env, r in d["E3"].items()}
    e3["node:test harness"] = {k: v["pass"] for k, v in nt["E3"]["node"].items() if isinstance(v, dict)} if nt else None
    e3["gate"] = "PASS" if all(all(v.values()) for k, v in e3.items() if isinstance(v, dict)) else "FAIL"
    e3["negative_control"] = {env: r["negative control"] for env, r in d["E3"].items()}
    e4 = {"hits": d["E4"]["hits"], "sites": d["E4"]["sites"], "gate": "PASS" if d["E4"]["pass"] else "FAIL",
          "rows": d["E4"]["rows"]}
    e8 = d["E8"]
    return e3, e4, e8


def e6():
    before = (B / "manifest-before.txt").read_text()
    after = (B / "manifest-after.txt").read_text() if (B / "manifest-after.txt").exists() else None
    plain_after = (B / "e6-plain-after.txt").read_text() if (B / "e6-plain-after.txt").exists() else ""
    marker = (B / "e6-marker-grep.txt").read_text() if (B / "e6-marker-grep.txt").exists() else None
    return {
        "manifest_identical": None if after is None else before == after,
        "plain_after": plain_after.strip(),
        "marker_hits_in_caches": None if marker is None else marker.strip(),
        "gate": None if after is None else ("PASS" if before == after and PLAIN_FILES in plain_after and (marker or "").strip() == "0" else "FAIL"),
    }


def main():
    e3, e4, e8 = e3_e4_e8()
    res = {"E0": e0(), "E1": e1(), "E2": e2(), "E3": e3, "E4": e4,
           "E5": {"vitest via Vite plugin": "PASS (probes-3: 5 probe files pass, expected rows produced)",
                  "node --test via loader hook": "PASS (nodetest-2: 7 tests, E3 all pass on its spool)",
                  "jest": None, "dropped": ["jest: not measured, VTT does not use it"]},
           "E6": e6(), "E7": {"verbatim": str(B / "e7-reader.txt")}, "E8": e8}
    (B / "results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: (v.get("gate") if isinstance(v, dict) else None) for k, v in res.items()}))
    print("E1:", {k: v for k, v in res["E1"].items() if k in ("off_over_plain", "off_gate", "call_over_plain")})


if __name__ == "__main__":
    main()
