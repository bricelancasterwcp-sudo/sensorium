"""E9: are tests tasks, and named as vitest names them?

    python3 e9.py <store dir> <invocation id> <vitest json> <sample file>

Two halves, both over ONE full-suite invocation.

The tally: sum the `tasks` rows of every trace of the invocation against the
sum of their `tests_seen`, and sum `task_name_conflicts`. The rule reads
tasks = tests_seen (4,278) and conflicts = 0 as PASS; a shortfall is named
by shape and STOPs above 1%. "By shape" is the per-file breakdown this
prints: every trace whose tasks and tests_seen disagree, with its delta,
so a shortfall is a list of files and not a single number.

The sample: the first 20 task names of the trace for `<sample file>`,
against the first 20 `fullName`s vitest's own JSON reporter printed for a
plain run of the same file -- order and text, compared as lists.

`value` is the difference `tasks - tests_seen` over the invocation: `0` is
the PASS. It is `null` when the store holds no trace for the invocation.
"""
import json
import sys
from pathlib import Path

from lens import cell, emit, usage
from sensorium.store.reader import Trace

#: How many names the pre-registration compares.
SAMPLE = 20

#: How this recorder joins a describe chain to a test name. Reported, not
#: assumed: `separator_normalised_identical` says whether the two name lists
#: agree once this string is replaced by a space, which is the difference
#: between "the recorder named a different test" and "the recorder spelled
#: the same chain another way". The first would be a defect; the second is a
#: fact about two spellings, and the record says which one was measured.
JOIN = " > "


def full_names(report: dict) -> list[str]:
    """Every `fullName` in a vitest JSON report, in the reporter's order.

    The reporter nests assertions under one entry per file; this run's
    report holds one file, but the walk does not assume that -- an extra
    file would show up as extra names rather than as a silent truncation.
    """
    names = []
    for result in report.get("testResults", []):
        for assertion in result.get("assertionResults", []):
            if "fullName" in assertion:
                names.append(assertion["fullName"])
    return names


def measure(store: Path, invocation: str, report_path: Path,
            sample_file: str) -> dict:
    traces = []
    for db in sorted((store / "traces").glob("*.db")):
        trace = Trace.open(db)
        if trace.meta.get("invocation") == invocation:
            traces.append((db.stem, trace))
    if not traces:
        return cell(None, 0, [f"no trace in the store names invocation "
                              f"{invocation}"], invocation=invocation)

    tasks = seen = conflicts = 0
    per_file_shortfall = []
    sample_trace = None
    for run_id, trace in traces:
        meta = trace.meta
        n_tasks = len(trace.tasks())
        n_seen = int(meta.get("tests_seen", 0))
        tasks += n_tasks
        seen += n_seen
        conflicts += int(meta.get("task_name_conflicts", 0))
        if n_tasks != n_seen:
            per_file_shortfall.append(
                {"run": run_id, "file": meta.get("test_file"),
                 "tasks": n_tasks, "tests_seen": n_seen,
                 "delta": n_tasks - n_seen})
        if meta.get("test_file") == sample_file:
            sample_trace = (run_id, trace)

    sample = {"file": sample_file}
    if sample_trace is None:
        sample["dropped"] = f"no trace of this invocation recorded {sample_file}"
    else:
        run_id, trace = sample_trace
        got = [t.name for t in sorted(trace.tasks(), key=lambda t: t.id)][:SAMPLE]
        try:
            want = full_names(json.loads(report_path.read_text(encoding="utf-8")))[:SAMPLE]
        except OSError as e:
            sample["dropped"] = f"the vitest report could not be read: {e}"
            want = []
        sample.update(run=run_id, n=SAMPLE, trace_names=got,
                      vitest_full_names=want, identical=got == want,
                      separator_normalised_identical=(
                          [g.replace(JOIN, " ") for g in got] == want),
                      join=JOIN,
                      first_difference=next(
                          (i for i, (a, b) in enumerate(zip(got, want))
                           if a != b), None if got == want else min(len(got), len(want))))

    shortfall = seen - tasks
    return cell(
        tasks - seen, len(traces),
        invocation=invocation,
        tasks=tasks, tests_seen=seen, task_name_conflicts=conflicts,
        shortfall=shortfall,
        shortfall_pct=round(100.0 * shortfall / seen, 4) if seen else None,
        files_disagreeing=per_file_shortfall,
        sample=sample,
    )


def main(argv) -> int:
    if len(argv) != 5:
        usage("usage: e9.py <store dir> <invocation id> <vitest json> "
              "<sample file, root-relative>")
    store = Path(argv[1])
    if not (store / "traces").is_dir():
        usage(f"{store} holds no traces/ directory -- is it a store?")
    emit(measure(store, argv[2], Path(argv[3]), argv[4]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
