"""Spec §10's first use: the six invocations, on the product, in order.

    python3 firstuse.py <store> <inv A> <inv B> <test file> <fn> <out dir>

Two full-suite invocations are NOT recorded here -- they are the call arm's
first two runs, already made and already counted; re-running them for a
demonstration would be two more recordings whose numbers nobody agreed to
read. So this asks the other four questions of those two:

    sensorium runs                       two groups, 372 files each
    sensorium diff <A:file> <B:same>     MATCH, per file
    sensorium tree <A:file> --depth 3    tests as task groups
    sensorium frame <A:file> --fn <fn>   one activation, return value

Spec §10 wrote its example against a `src/fog/compute.test.ts` and a
function called `compute`; this lens has neither, so the file and the
function are named on the command line and printed in the output -- the
question is the same one, asked of a file this consumer actually has.

`value` is the number of the four that answered as §10 says they should.
"""
import re
import subprocess
import sys
from pathlib import Path

from lens import cell, emit, sensorium_bin, usage
from sensorium.store.reader import Trace


def run(store: Path, args: list[str], out: Path) -> tuple[int, str]:
    import os
    proc = subprocess.run([sensorium_bin(), *args], capture_output=True, text=True,
                          env={**os.environ, "SENSORIUM_DIR": str(store)})
    text = proc.stdout + proc.stderr
    out.write_text(text, encoding="utf-8")
    return proc.returncode, text


def run_for(store: Path, invocation: str, test_file: str) -> str | None:
    for db in sorted((store / "traces").glob("*.db")):
        meta = Trace.open(db).meta
        if meta.get("invocation") == invocation and meta.get("test_file") == test_file:
            return db.stem
    return None


def measure(store: Path, inv_a: str, inv_b: str, test_file: str, fn: str,
            out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    a = run_for(store, inv_a, test_file)
    b = run_for(store, inv_b, test_file)
    dropped = []
    if a is None or b is None:
        dropped.append(f"one of the two invocations recorded no {test_file}")

    runs_code, runs_text = run(store, ["runs"], out / "firstuse-runs.txt")
    # `runs` prints one header per invocation and one indented line per
    # trace under it, so a group's size is counted from the block, not read
    # off the header -- the header does not carry a count.
    groups, counts, current = [], {}, None
    for line in runs_text.splitlines():
        if line.startswith("invocation "):
            current = line.split()[1].rstrip(":")
            counts.setdefault(current, 0)
            if current in (inv_a, inv_b):
                groups.append(line.strip())
        elif current is not None and line.startswith("  ") and line.strip():
            counts[current] = counts.get(current, 0) + 1

    results = {}
    results["runs"] = {
        "exit": runs_code,
        "lines_for_the_two_invocations": groups,
        "traces_per_invocation": {k: counts.get(k) for k in (inv_a, inv_b)},
        "ok": runs_code == 0 and len(groups) == 2,
    }
    for key, args, want in (
            ("diff", ["diff", a or "", b or ""], "MATCH"),
            ("tree", ["tree", a or "", "--depth", "3"], None),
            ("frame", ["frame", a or "", "--fn", fn], None)):
        if a is None or b is None:
            results[key] = {"dropped": "no trace to ask"}
            continue
        code, text = run(store, args, out / f"firstuse-{key}.txt")
        verdict = next((ln.strip() for ln in text.splitlines()
                        if ln.startswith("verdict:")), None)
        results[key] = {
            "exit": code, "verdict": verdict,
            "first_lines": [ln.rstrip() for ln in text.splitlines()[:6]],
            "ok": code == 0 and (want is None or (verdict or "").startswith(f"verdict: {want}")
                                 or (verdict or "").find(want) >= 0),
        }
    ok = sum(1 for r in results.values() if r.get("ok"))
    return cell(ok, len(results), dropped, invocation_a=inv_a,
                invocation_b=inv_b, test_file=test_file, fn=fn,
                run_a=a, run_b=b, invocations=results)


def main(argv) -> int:
    if len(argv) != 7:
        usage("usage: firstuse.py <store> <inv A> <inv B> <test file> <fn> "
              "<out dir>")
    emit(measure(Path(argv[1]), argv[2], argv[3], argv[4], argv[5],
                 Path(argv[6])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
