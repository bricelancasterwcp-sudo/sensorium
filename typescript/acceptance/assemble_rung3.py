"""S5 rung 3's cells, gathered into its acceptance record's results file.

    python3 assemble_rung3.py <results dir> <out> <recorder> <rev> [PATH=LABEL]...

Rung 2's assembler, minus the derivations rung 3 has no arms for. Every
instrument writes ONE cell per endpoint into `<results dir>`, so a cell
nobody measured is a MISSING FILE and this file turns that into `{value:
null, dropped: [...]}` naming the file -- never an omission, never a zero.
`redact`, `offenders` and `FORBIDDEN` are `assemble.py`'s: the results file
is COMMITTED, so a box path surviving redaction is a REFUSAL.

TWO THINGS ARE DELIBERATELY STRICTER HERE THAN IN RUNG 2'S
-----------------------------------------------------------
* **`lens.stamp(..., strict=True)`.** Every instrument this assembler reads
  was built or extended in rung 3, AFTER `cell()` stopped embedding the lens
  label at measurement time. So a cell arriving with a `lens` of its own is
  not history here, it is a defect -- some instrument minted a label nothing
  asked it for -- and the assembler refuses (exit 3) naming the cell rather
  than keeping it. Rung 2's assembler cannot do this: it re-assembles cells
  committed under the old rule.
* **every cell records its own recorder.** `e6tsppp.py`, `e6ts.py`,
  `e8pp.py` and `e7_report.py` are all handed `<recorder>`/`<rev>` in their
  environment, so `recorder_basis` should read `own` on every row; the
  assembler's own stamp stays as the backstop that says so when it does not.

Nothing here is gated. The verdict WORDS are the rule's, written by hand into
the record's 3 beside the rule that produced them; what this assembles is the
numbers those verdicts are read off.
"""
import json
import sys
from pathlib import Path

from assemble import FORBIDDEN, offenders, redact  # noqa: F401
from assemble_rung2 import OWN, STAMPED, load, stamp
from lens import LENS, cell
from lens import stamp as lens_stamp

#: The endpoint cells read straight from one instrument's JSON.
GATED_FILES = {
    "E6-TS": "e6ts.json",
    "E8‴": "e8ppp.json",
    "E7‴": "e7.json",
    "E-legacy": "e-legacy.json",
    "E-branch": "e-branch.json",
}

#: The three cells `e6tsppp.py` writes in ONE file, because they are three
#: readings of ONE re-read and splitting them across files would invite a
#: reader to think the transcript was read three times.
REREAD_FILE = "e6tsppp.json"
REREAD_CELLS = ("E6-TS‴", "E6-TS′-fence", "E-places")

#: The record's 3 row order.
ORDER = ["E6-TS‴", "E6-TS′-fence", "E-places", "E6-TS", "E8‴", "E7‴",
         "E-legacy", "E-branch"]


def read_cell(results: Path, name: str, filename: str) -> dict:
    """One instrument's cell, or a null naming the file that was not there."""
    data = load(results / filename)
    if "_absent" in data:
        return cell(None, 0, [f"{name} was not measured: {data['_absent']}"])
    return data


def reread(results: Path) -> dict:
    """The three cells of the one re-read, plus what the re-read itself was."""
    data = load(results / REREAD_FILE)
    if "_absent" in data:
        return {name: cell(None, 0, [f"{name} was not measured: "
                                     f"{data['_absent']}"])
                for name in REREAD_CELLS}
    cells = data.get("cells") or {}
    out = {}
    for name in REREAD_CELLS:
        got = cells.get(name)
        out[name] = got if got is not None else cell(
            None, 0, [f"{name} is missing from {REREAD_FILE}"])
    return out


def build(results: Path) -> dict:
    payload = {
        "record": "docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3.md",
        "lens": LENS,
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value with a non-empty dropped list is the only "
                   "representation of 'not measured'; 0 is measured-and-zero"),
        "gated": {},
        "reported": {},
    }
    payload["gated"].update(reread(results))
    for name, filename in GATED_FILES.items():
        payload["gated"][name] = read_cell(results, name, filename)
    payload["gated"] = {k: payload["gated"][k] for k in ORDER
                        if k in payload["gated"]}
    raw = load(results / REREAD_FILE)
    payload["reported"]["the_one_re_read"] = (
        {"not_measured": raw["_absent"]} if "_absent" in raw else
        {k: raw.get(k) for k in
         ("invocation", "command", "exit", "transcript", "transcript_sha256",
          "transcript_lines", "rung2_transcript_sha256", "reason_line",
          "reasons", "hash_list_verified")})
    return payload


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 4:
        sys.stderr.write("usage: assemble_rung3.py <results dir> <out> "
                         "<recorder> <rev> [PATH=LABEL]...\n")
        return 2
    recorder, rev = args[2], args[3]
    if len(rev) != 40:
        sys.stderr.write("the rev is the FULL 40-character sha the cells were "
                         f"recorded at, not {rev!r}\n")
        return 2
    pairs = []
    for spec in args[4:]:
        if "=" not in spec:
            sys.stderr.write(f"a redaction is PATH=LABEL, not {spec!r}\n")
            return 2
        needle, _, label = spec.partition("=")
        pairs.append((needle, label))
    # Longest needle first: the worktree's own `sensorium` sits UNDER the
    # worktree, and the shorter prefix would half-rewrite it.
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    payload = build(Path(args[0]))
    payload["recorded_by"] = {"recorder": recorder, "commit": rev}
    # The lens label first, strictly -- then the recorder provenance, which
    # expects `lens` to already be on the cell.
    payload = redact(stamp(lens_stamp(payload, strict=True), recorder, rev),
                     pairs)
    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble_rung3: a box path survived redaction and "
                         "this file is committed; add a PATH=LABEL for it:\n")
        for where, value in bad[:10]:
            sys.stderr.write(f"  {where}: {value[:160]}\n")
        return 2
    basis = sorted({c.get("recorder_basis") for c in payload["gated"].values()
                    if isinstance(c, dict)})
    Path(args[1]).write_text(json.dumps(payload, indent=2) + "\n",
                             encoding="utf-8")
    sys.stderr.write(f"wrote {args[1]} (recorder_basis: {basis}; "
                     f"{OWN!r} is an instrument's own, otherwise {STAMPED!r})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
