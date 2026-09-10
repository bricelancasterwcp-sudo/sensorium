"""The equivalence gate's JSON: 372 pairs, one reader, one verdict each.

`value` is how many pairs came back MATCH and `n` is how many pairs there
were, so the gate's rule -- 372 MATCH, 0 DIVERGED, 0 REFUSED -- is read off
`value`, `n`, `diverged` and `refused` without arithmetic. `matches +
diverged + refused + other == n` always; `other` is a diff that did not
answer at all (exit 2, the call was wrong), and those pairs are ALSO named
in `dropped`, because a pair whose diff never ran is not a measurement of
anything. A DIVERGED is a measurement -- it is the gate's answer -- so it is
never dropped; it is named in `mismatches` with the diff's own verdict line.

The pairing is spec 3.5's and plan P3's: the test file each `run:` line
prints. The run ids differ by construction (they are minted with a random
token), so they cannot be the key; the spool file name would also serve, but
the pre-registration named the test file and the pre-registration is what
this instrument implements. A side that printed the same test file twice, or
two sides whose file sets differ, REFUSE the gate by name rather than pair
something with something else.

Reported beside the verdict, ungated (spec 3.5): the per-table row counts,
as the number of pairs whose seven tables all matched, and the union over
every pair of the meta keys whose values differ. That union is expected to
be exactly the minted `run_id`; anything else in it is a converter that
changed what it wrote about the run, and belongs in the record.
"""
import os
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from lens import cell, emit, usage

#: `Summary.line()`'s shape, field for field (`tests/ts_spools.py::RUN_LINE`).
RUN_LINE = re.compile(
    r"^run: (?P<run_id>\S+)  pid: (?P<pid>\d+)  file: (?P<file>\S+)  "
    r"events: (?P<events>\d+)  tasks: (?P<tasks>\d+)$", re.MULTILINE)

#: The other line an ingest prints per spool: `refused: <file>  <why>`.
REFUSED_LINE = re.compile(r"^refused: (?P<file>\S+)  (?P<why>.*)$", re.MULTILINE)

#: The seven tables spec 3.5 counts. `meta` is compared key by key instead.
TABLES = ("events", "frames", "tasks", "code_objects", "fingerprints",
          "task_fingerprints", "output")

#: `src/sensorium/exit.py`: 0 answered, 1 negative, 2 bad call, 3 unsettled.
VERDICTS = {0: "MATCH", 1: "DIVERGED", 3: "REFUSED"}

#: Four at a time. The reader is read-only and the diffs are not timed, so
#: this only decides how long the gate takes, never what it reads.
WORKERS = 4


def _side(log: str, label: str) -> tuple[dict, list]:
    """One ingest log as {test_file: run_id}, plus its refusals by name."""
    text = Path(log).read_text(encoding="utf-8", errors="replace")
    runs: dict[str, str] = {}
    for m in RUN_LINE.finditer(text):
        name = m.group("file")
        if name in runs:
            usage(f"side {label} converted the test file {name} twice: the "
                  "pairing key repeats, so no pair can be trusted")
        runs[name] = m.group("run_id")
    if not runs:
        usage(f"side {label} printed no run line: nothing was converted")
    refused = [f"side {label} refused {m.group('file')}: {m.group('why')}"
               for m in REFUSED_LINE.finditer(text)]
    return runs, refused


def _pairs(a: dict, b: dict) -> list[tuple[str, str, str]]:
    """(test_file, run-A, run-B) for every file, or refuse the whole gate."""
    if set(a) != set(b):
        only_a = sorted(set(a) - set(b))[:5]
        only_b = sorted(set(b) - set(a))[:5]
        usage(f"the two sides converted different test files -- "
              f"{len(a)} on A, {len(b)} on B; only in A: {only_a}; "
              f"only in B: {only_b}")
    return [(f, a[f], b[f]) for f in sorted(a)]


def _counts(db: Path) -> dict:
    """One trace's row count per table."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in TABLES}
    finally:
        conn.close()


def _meta(db: Path) -> dict:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return dict(conn.execute("SELECT key, value FROM meta"))
    finally:
        conn.close()


def _verdict_line(proc) -> str:
    """The diff's own verdict line, or its first line of output."""
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    for line in lines:
        if line.startswith("verdict:"):
            return line
    err = [ln for ln in (proc.stderr or "").splitlines() if ln.strip()]
    return (lines + err + ["(the diff printed nothing)"])[0]


def _one(env: dict, pair: tuple[str, str, str]) -> dict:
    """One pair: B's reader on both ids, then the two ungated comparisons."""
    name, run_a, run_b = pair
    store_b = Path(env["E10P_EQ_STORE_B"])
    proc = subprocess.run([env["E10P_EQ_BIN_B"], "diff", run_a, run_b],
                          env={**os.environ, "SENSORIUM_DIR": str(store_b)},
                          capture_output=True, text=True)
    db_a, db_b = store_b / "traces" / f"{run_a}.db", store_b / "traces" / f"{run_b}.db"
    counts_a, counts_b = _counts(db_a), _counts(db_b)
    meta_a, meta_b = _meta(db_a), _meta(db_b)
    differing = sorted(k for k in set(meta_a) | set(meta_b)
                       if meta_a.get(k) != meta_b.get(k))
    return {"file": name, "run_a": run_a, "run_b": run_b,
            "exit": proc.returncode,
            "verdict": VERDICTS.get(proc.returncode, "other"),
            "verdict_line": _verdict_line(proc),
            "counts_equal": counts_a == counts_b,
            "counts_a": counts_a, "counts_b": counts_b,
            "meta_keys_differing": differing}


def _tally(results: list[dict]) -> dict:
    """The four exit tallies, the two ungated readings, and what was named."""
    by = {"MATCH": 0, "DIVERGED": 0, "REFUSED": 0, "other": 0}
    mismatches, dropped, keys = [], [], set()
    for r in results:
        by[r["verdict"]] += 1
        keys.update(r["meta_keys_differing"])
        if r["verdict"] != "MATCH":
            mismatches.append({"file": r["file"], "verdict": r["verdict"],
                               "exit": r["exit"], "line": r["verdict_line"]})
        if r["verdict"] == "other":
            dropped.append(f"{r['file']}: diff exited {r['exit']} -- "
                           f"{r['verdict_line']}")
    return {"by": by, "mismatches": mismatches, "dropped": dropped,
            "meta_keys_differing": sorted(keys),
            "counts_equal": sum(1 for r in results if r["counts_equal"]),
            "counts_differing": [{"file": r["file"], "a": r["counts_a"],
                                  "b": r["counts_b"]}
                                 for r in results if not r["counts_equal"]]}


def main() -> int:
    env = dict(os.environ)
    runs_a, refused_a = _side(env["E10P_EQ_LOG_A"], "A")
    runs_b, refused_b = _side(env["E10P_EQ_LOG_B"], "B")
    pairs = _pairs(runs_a, runs_b)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda p: _one(env, p), pairs))
    t = _tally(results)
    emit(cell(
        t["by"]["MATCH"], len(pairs), t["dropped"] + refused_a + refused_b,
        spools=int(env["E10P_EQ_SPOOLS"]),
        diverged=t["by"]["DIVERGED"], refused=t["by"]["REFUSED"],
        other=t["by"]["other"],
        row_counts_equal_pairs=t["counts_equal"],
        row_counts_differing=t["counts_differing"],
        meta_keys_differing=t["meta_keys_differing"],
        mismatches=t["mismatches"],
        converter_a={"bin": env["E10P_EQ_BIN_A"], "rev": env["E10P_EQ_REV_A"]},
        converter_b={"bin": env["E10P_EQ_BIN_B"], "rev": env["E10P_EQ_REV_B"]},
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
