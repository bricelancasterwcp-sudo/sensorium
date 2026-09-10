"""S5 slice 2's cells, gathered into its acceptance record's results file.

    python3 assemble_slice2.py <results dir> <out> [PATH=LABEL]...

Slice 2's instruments each write ONE cell per measurement into the store's
`results/` directory (plan P2), so a cell nobody measured is a MISSING FILE
rather than a key someone forgot -- and this assembler turns a missing file
into `{value: null, dropped: [...]}` naming it, never into an omission and
never into a zero.

`assemble.py` (rung 1's) is not extended: it reads an `arms.jsonl` this slice
never produced and derives E1' and E5' from it, and rung 1's record is locked
around the file it wrote. This one reads only the JSON cells, and shares that
assembler's `redact`, `offenders` and `FORBIDDEN` -- the results file is
COMMITTED, so a box path surviving redaction is a refusal, not a warning.

What is GATED here is exactly what slice 2 pre-registered a rule for:
E10'-0's five diagnosis cells (reported against predictions, no verdict, but
one row of the record each), the two E10' verdict cells, the equivalence
gate, E6" and the H-probes. Everything else -- the ladder's rungs, the
content check, the RSS pair, the parallel speedup, the call run's two walls
-- is REPORTED, and is in `reported` for that reason and no other.
"""
import json
import sys
from pathlib import Path

from assemble import FORBIDDEN, offenders, redact  # noqa: F401  (FORBIDDEN re-exported)
from lens import LENS, cell

#: The gated cells, and the file each is read from. `E10'-0` is five files
#: under one row: Arm 0 is one diagnosis, and splitting it into five record
#: rows here would let four of them be quoted without the fifth.
ARM0_CELLS = ("big-j1", "full-j1", "full-j4", "full-j16", "file")
GATED_FILES = {
    "E10′-suite": "e10p-final-full-j16.json",
    "E10′-file": "e10p-final-file.json",
    "E10′-eq": "e10p-eq.json",
    "E6″": "e6pp.json",
    "H-probes": "h-probes.json",
}

#: The record's row order.
ORDER = ["E6″", "E10′-suite", "E10′-file", "E10′-eq", "E10′-0", "H-probes"]

#: The ladder's rungs, reported beside the gated cells they arrived at.
RUNG_STAGES = ("a1", "a3")
RUNG_CELLS = ("big-j1", "full-j16", "file")


def load(path: Path):
    """One cell's JSON, or `_absent` with a reason that carries NO path.

    `str(OSError)` spells the whole filename it failed on, and this file is
    committed: a missing cell would otherwise smuggle the store's box path
    into `dropped` and the redaction refusal would fire on the one branch
    that is supposed to explain itself. The basename is the identifying part
    and it is what the record names.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        return {"_absent": f"{path.name} could not be read: {e.strerror}"}
    except json.JSONDecodeError as e:
        return {"_absent": f"{path.name} is not JSON: {e.msg} "
                           f"(line {e.lineno}, column {e.colno})"}


def read_cell(results: Path, name: str, filename: str) -> dict:
    """One instrument's cell, or a null naming the file that was not there."""
    data = load(results / filename)
    if "_absent" in data:
        return cell(None, 0, [f"{name} was not measured: {data['_absent']}"])
    return data


def arm0(results: Path) -> dict:
    """Arm 0's five cells in one row: `value` is how many were measured."""
    cells, dropped = {}, []
    for label in ARM0_CELLS:
        data = load(results / f"e10p-arm0-{label}.json")
        if "_absent" in data:
            dropped.append(f"Arm 0 cell {label} was not measured: {data['_absent']}")
            cells[label] = None
            continue
        cells[label] = data
    return cell(sum(1 for v in cells.values() if v is not None), len(ARM0_CELLS),
                dropped, cells=cells)


def rungs(results: Path) -> dict:
    """The ladder's intermediate rungs, reported: stage -> cell -> the cell."""
    out = {}
    for stage in RUNG_STAGES:
        for label in RUNG_CELLS:
            data = load(results / f"e10p-{stage}-{label}.json")
            out[f"{stage}-{label}"] = (
                cell(None, 0, [f"the {stage} rung's {label} cell was not "
                               f"measured: {data['_absent']}"])
                if "_absent" in data else data)
    return out


def _median_wall(c) -> float | None:
    return None if not isinstance(c, dict) else c.get("value")


def speedup(results: Path) -> dict:
    """0b/0d on main's converter -- the parallel speedup, spec 3.6."""
    b = load(results / "e10p-arm0-full-j1.json")
    d = load(results / "e10p-arm0-full-j16.json")
    if "_absent" in b or "_absent" in d:
        return cell(None, 0, ["0b or 0d was not measured, so 0b/0d is not a "
                              "number this file can carry"])
    wb, wd = _median_wall(b), _median_wall(d)
    if not wb or not wd:
        return cell(None, 0, ["0b or 0d has a null median: every repetition "
                              "of it was dropped"])
    return cell(round(wb / wd, 4), min(b["n"], d["n"]),
                jobs_1=wb, jobs_16=wd,
                rule="0b / 0d, main's converter, the pinned full-suite set")


def rss(results: Path) -> dict:
    """Peak resident of the heaviest worker, before and after A3 (spec 3.6)."""
    out = {}
    for label, filename in (("before_a3_big_j1", "e10p-arm0-big-j1.json"),
                            ("before_a3_full_j16", "e10p-arm0-full-j16.json"),
                            ("after_a3_big_j1", "e10p-a3-big-j1.json"),
                            ("after_a3_full_j16", "e10p-a3-full-j16.json"),
                            ("final_full_j16", "e10p-final-full-j16.json")):
        data = load(results / filename)
        out[label] = (cell(None, 0, [f"{label} was not measured: {data['_absent']}"])
                      if "_absent" in data
                      else cell(data.get("maxrss_kb"), data.get("n"),
                                unit="kB", converter_rev=data.get("converter_rev")))
    return out


def call_run_walls(results: Path) -> dict:
    """E6″'s call run: the harness wall and the driver wall (spec 3.6).

    The slice's driver converts INLINE, so the driver wall carries the fresh
    set's conversion and the harness wall does not. Their difference is
    reported under its own name rather than called an `ingest` wall it is
    not: it is everything the driver does around the harness.
    """
    data = load(results / "e6pp.json")
    if "_absent" in data:
        return {"walls": cell(None, 0, ["E6″ was not measured: "
                                        f"{data['_absent']}"])}
    run = data.get("call_run") or {}
    harness, driver = run.get("harness_wall"), run.get("driver_wall")
    around = (None if harness is None or driver is None
              else round(driver - harness, 4))
    return {
        "walls": cell(driver, 1, [] if driver is not None else
                      ["the call run recorded no driver wall"],
                      harness_wall=harness, driver_wall=driver,
                      invocation=run.get("invocation"),
                      spool_files=run.get("spool_files"),
                      spool_bytes=run.get("spool_bytes"),
                      spool_lines=run.get("spool_lines")),
        "driver_around_harness": cell(
            around, 1, [] if around is not None else
            ["one of the two walls is missing, so their difference is not a "
             "number"],
            rule="driver wall - harness wall: the fresh set's inline "
                 "conversion plus the driver's own setup and cleanup, which "
                 "this session does not separate"),
    }


def build(results: Path) -> dict:
    payload = {
        "record": "docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md",
        "lens": LENS,
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value with a non-empty dropped list is the only "
                   "representation of 'not measured'; 0 is measured-and-zero"),
        "gated": {"E10′-0": arm0(results)},
        "reported": {},
    }
    for name, filename in GATED_FILES.items():
        payload["gated"][name] = read_cell(results, name, filename)
    payload["gated"] = {k: payload["gated"][k] for k in ORDER
                        if k in payload["gated"]}
    payload["reported"] = {
        "ladder_rungs": rungs(results),
        "E10′-eq-content": read_cell(results, "E10′-eq-content",
                                     "e10p-eq-content.json"),
        "peak_rss_kb": rss(results),
        "parallel_speedup_0b_over_0d": speedup(results),
        **call_run_walls(results),
    }
    return payload


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 2:
        sys.stderr.write("usage: assemble_slice2.py <results dir> <out> "
                         "[PATH=LABEL]...\n")
        return 2
    pairs = []
    for spec in args[2:]:
        if "=" not in spec:
            sys.stderr.write(f"a redaction is PATH=LABEL, not {spec!r}\n")
            return 2
        needle, _, label = spec.partition("=")
        pairs.append((needle, label))
    # Longest needle first: the worktree's own `sensorium` sits UNDER the
    # worktree, and the shorter prefix would half-rewrite it.
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    payload = redact(build(Path(args[0])), pairs)
    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble_slice2: a box path survived redaction and "
                         "this file is committed; add a PATH=LABEL for it:\n")
        for where, value in bad[:10]:
            sys.stderr.write(f"  {where}: {value[:160]}\n")
        return 2
    Path(args[1]).write_text(json.dumps(payload, indent=2) + "\n",
                             encoding="utf-8")
    sys.stderr.write(f"wrote {args[1]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
