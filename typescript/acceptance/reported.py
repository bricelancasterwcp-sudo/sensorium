"""The quantities §8 reports WITHOUT a gate, over two full-suite invocations.

    python3 reported.py <store> <invocation A> <invocation B> [reps]

Three of them, and none decides anything:

  latency        `info` and `diff` on the largest trace of A, `reps` times,
                 median. Largest by the trace file's own size on disk, which
                 is what a reader waits for.
  diverged_pairs every test file recorded by BOTH invocations, `diff`ed A
                 against B. A non-zero count names a nondeterministic test,
                 which is a finding about the CONSUMER and not about the
                 recorder -- so the files are named, not just counted.

`value` is the number of DIVERGED pairs; the latencies sit beside it.
"""
import statistics
import subprocess
import sys
import time
from pathlib import Path

from lens import cell, emit, usage
from sensorium.store.reader import Trace

DIVERGED = 1


def by_file(store: Path, invocation: str) -> dict[str, tuple[str, int]]:
    """`test_file` -> (run id, trace bytes) for one invocation."""
    out = {}
    for db in sorted((store / "traces").glob("*.db")):
        meta = Trace.open(db).meta
        if meta.get("invocation") != invocation:
            continue
        f = meta.get("test_file")
        if f is not None:
            out[f] = (db.stem, db.stat().st_size)
    return out


def timed(store: Path, args: list[str]) -> tuple[float, int]:
    start = time.perf_counter()
    proc = subprocess.run(["sensorium", *args], capture_output=True,
                          text=True, env={**_env(store)})
    return time.perf_counter() - start, proc.returncode


def _env(store: Path) -> dict:
    import os
    return {**os.environ, "SENSORIUM_DIR": str(store)}


def measure(store: Path, inv_a: str, inv_b: str, reps: int) -> dict:
    a = by_file(store, inv_a)
    b = by_file(store, inv_b)
    dropped = []
    if not a:
        return cell(None, 0, [f"no trace names invocation {inv_a}"])

    largest_file = max(a, key=lambda f: a[f][1])
    largest_run, largest_bytes = a[largest_file]
    other = b.get(largest_file, (None, None))[0]

    info_walls = [timed(store, ["info", largest_run])[0] for _ in range(reps)]
    diff_walls = ([timed(store, ["diff", largest_run, other])[0]
                   for _ in range(reps)] if other else [])
    if not other:
        dropped.append(f"{inv_b} recorded no counterpart for the largest "
                       "trace, so `diff` latency was not measured")

    shared = sorted(set(a) & set(b))
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    verdicts = {"match": [], "diverged": [], "refused": [], "bad_call": []}
    for f in shared:
        proc = subprocess.run(["sensorium", "diff", a[f][0], b[f][0]],
                              capture_output=True, text=True, env=_env(store))
        name = {0: "match", 1: "diverged", 2: "bad_call",
                3: "refused"}.get(proc.returncode)
        if name is None:
            dropped.append(f"{f}: diff exited {proc.returncode}")
            continue
        verdicts[name].append(f)

    return cell(
        len(verdicts["diverged"]), len(shared), dropped,
        invocation_a=inv_a, invocation_b=inv_b,
        files_a=len(a), files_b=len(b), compared=len(shared),
        only_in_a=only_a, only_in_b=only_b,
        diverged_files=verdicts["diverged"],
        refused_files=verdicts["refused"],
        bad_call_files=verdicts["bad_call"],
        matched=len(verdicts["match"]),
        largest={"file": largest_file, "run": largest_run,
                 "trace_bytes": largest_bytes,
                 "info_median_s": round(statistics.median(info_walls), 4),
                 "info_walls": [round(w, 4) for w in info_walls],
                 "diff_median_s": (round(statistics.median(diff_walls), 4)
                                   if diff_walls else None),
                 "diff_walls": [round(w, 4) for w in diff_walls],
                 "n": reps},
    )


def main(argv) -> int:
    if len(argv) not in (4, 5):
        usage("usage: reported.py <store> <invocation A> <invocation B> [reps]")
    store = Path(argv[1])
    if not (store / "traces").is_dir():
        usage(f"{store} holds no traces/ directory -- is it a store?")
    emit(measure(store, argv[2], argv[3], int(argv[4]) if len(argv) == 5 else 3))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
