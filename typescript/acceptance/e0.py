"""E0': is the trace unit still the test file under the product?

    python3 e0.py <store dir> <invocation id>

Opens every trace one invocation of the full suite left in a store and asks
three things of it, which together are the pre-registered claim "372
containers, one file each":

  containers        how many traces the invocation produced
  one_file          traces carrying `test_file` -- exactly one file started
  many_files        traces carrying `test_files` -- two or more started in
                    ONE container, which the rule STOPs on
  no_file           traces carrying neither, which the rule STOPs on too
  distinct_files    distinct `test_file` values across the invocation

`value` is the number of containers that carry exactly one test file and
whose files are all distinct from one another -- i.e. the number the rule
compares against 372 -- and it is `null` only when the store holds no trace
for the invocation at all, which is a call that measured nothing.

Nothing here is a re-run: it reads a store.
"""
import sys
from collections import Counter
from pathlib import Path

from lens import cell, emit, usage
from sensorium.store.reader import Trace


def traces_of(store: Path, invocation: str):
    """Every trace in `store` whose meta names `invocation`, by path."""
    found = []
    for db in sorted((store / "traces").glob("*.db")):
        trace = Trace.open(db)
        if trace.meta.get("invocation") == invocation:
            found.append((db.stem, trace))
    return found


def measure(store: Path, invocation: str) -> dict:
    found = traces_of(store, invocation)
    if not found:
        return cell(None, 0, [f"no trace in the store names invocation "
                              f"{invocation}"], invocation=invocation)
    one_file, many_files, no_file = [], [], []
    for run_id, trace in found:
        meta = trace.meta
        if "test_files" in meta:
            many_files.append({"run": run_id, "files": meta["test_files"]})
        elif "test_file" in meta:
            one_file.append((run_id, meta["test_file"]))
        else:
            no_file.append(run_id)
    counts = Counter(f for _, f in one_file)
    repeated = {f: n for f, n in counts.items() if n > 1}
    return cell(
        len(one_file), len(found),
        invocation=invocation,
        containers=len(found),
        one_file=len(one_file),
        many_files=many_files,
        no_file=no_file,
        distinct_files=len(counts),
        repeated_files=repeated,
    )


def main(argv) -> int:
    if len(argv) != 3:
        usage("usage: e0.py <store dir> <invocation id>")
    store = Path(argv[1])
    if not (store / "traces").is_dir():
        usage(f"{store} holds no traces/ directory -- is it a store?")
    emit(measure(store, argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
