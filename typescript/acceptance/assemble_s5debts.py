"""S5 rung 4's debts: this slice's cells, gathered into its results file.

    .venv/bin/python typescript/acceptance/assemble_s5debts.py \\
        <results dir> <out> <recorder> <rev> [PATH=LABEL]...

The argument order is `assemble_rung4.py`'s, unchanged, so the two read the
same way at a call site.

Rung 4's assembler minus the two checks that belonged to a RECORDING session
and plus the one this slice's pre-registration puts on the assembler:

* **the hashed set, §1.1's.** E12′ re-adjudicates data that is already
  committed, so the question is not "did the store move since the arms" but
  "were these numbers read off the bytes §1.1 pins". The thirteen transcripts
  are re-hashed here against §1.1's list, and the store the reads were taken
  against is re-checked against the hash list §1.1 cites -- twelve entries
  plainly and `invocations.jsonl` as an APPEND, for the reason §1.1 gives.
  `e12p_report.py` already refuses at exit 4 on a mismatch; doing it again
  here is the difference between "the instrument says it checked" and "the
  results file was assembled from bytes that verify".
* **the reads were taken against THIS record.** A dry run points
  `e12_report.record_path()` at a scratch §1; assembling such reads into this
  slice's results file would publish numbers read against a pre-registration
  nobody locked.

There is no journal-delta check: nothing in E12′ calls the CLI against rung
4's store, and H8′ records into a store of its own.

A failure is carried in the payload, named, and the assembler exits non-zero
-- the results file is written either way, because a reader diagnosing a
failed verification needs the cells it failed over.

`lens.stamp(..., strict=True)`: every instrument this assembler reads was
written in this slice, after `cell()` stopped embedding the lens label, so a
cell arriving with a `lens` of its own is a defect and not history.
"""
import hashlib
import json
import sys
from pathlib import Path

from assemble import FORBIDDEN, offenders, redact  # noqa: F401
from assemble_rung2 import OWN, STAMPED, load, stamp
from e12_report import RECORD as RUNG4_RECORD
from e12p_pre import RECORD, hash_list, verify_store, verify_transcripts
from lens import LENS, cell
from lens import stamp as lens_stamp

#: The three cells `e12p_report.py` writes in ONE file: three readings of ONE
#: set of committed transcripts, and splitting them across files would invite
#: a reader to think the data was opened three times.
READS_FILE = "e12p-reads.json"
READS_CELLS = ("H2p", "H4p", "H5p")

#: The endpoint cells read straight from one instrument's JSON.
GATED_FILES = {"H8p": "e12p-h8.json", "E13": "e13.json", "E14": "e14.json",
               "E6TSp": "e6tsp.json"}

#: The two fences, run FIRST and reported beside H8′ (rung 4's rulings R12,
#: R35, unchanged).
FENCE_FILES = {"E-legacy": "e-legacy.json", "E-branch": "e-branch.json"}

#: The record's §3 row order.
ORDER = ["H2p", "H4p", "H5p", "H8p", "E13", "E14", "E6TSp"]

#: §1.8's suites, as the operator writes them into the results directory:
#: `{"<label>": {"command": "<as run>", "exit": 0, "tail": ["…"]}}`.
SUITES_FILE = "suites.json"


def read_cell(results: Path, name: str, filename: str) -> dict:
    """One instrument's cell, or a null naming the file that was not there."""
    data = load(results / filename)
    if "_absent" in data:
        return cell(None, 0, [f"{name} was not measured: {data['_absent']}"])
    return data


def reads(results: Path) -> tuple[dict, dict]:
    """E12′'s three cells, and the reads' own record."""
    data = load(results / READS_FILE)
    if "_absent" in data:
        return ({name: cell(None, 0, [f"{name} was not measured: "
                                      f"{data['_absent']}"])
                 for name in READS_CELLS}, data)
    got = data.get("cells") or {}
    return ({name: got.get(name) or cell(
        None, 0, [f"{name} is missing from {READS_FILE}"])
        for name in READS_CELLS}, data)


def verify_hashes(reads_record: dict) -> dict:
    """§1.1's list, re-verified from the paths the reads say they used."""
    listed = hash_list()
    where = reads_record.get("reads_dir")
    store = reads_record.get("store")
    if not where or not store:
        return {"ok": False, "why": [
            f"{READS_FILE} does not say which directory and store it read, so "
            "§1.1's list cannot be re-verified against them"]}
    transcripts = verify_transcripts(Path(where), listed["transcripts"])
    saved = verify_store(Path(store), listed["store_list"],
                         listed["journal_head"])
    return {"ok": transcripts["ok"] and saved["ok"],
            "why": transcripts["why"] + saved["why"],
            "transcripts": transcripts, "store": saved}


def build(results: Path) -> tuple[dict, dict]:
    cells, reads_record = reads(results)
    payload = {
        "record": "docs/superpowers/acceptance/"
                  "2026-09-12-sensorium-s5-rung4-debts.md",
        "lens": LENS,
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value with a non-empty dropped list is the only "
                   "representation of 'not measured'; 0 is measured-and-zero"),
        "gated": {},
        "reported": {},
    }
    payload["gated"].update(cells)
    for name, filename in GATED_FILES.items():
        payload["gated"][name] = read_cell(results, name, filename)
    payload["gated"] = {k: payload["gated"][k] for k in ORDER
                        if k in payload["gated"]}
    payload["reported"]["fences"] = {
        name: read_cell(results, name, filename)
        for name, filename in FENCE_FILES.items()}
    suites = load(results / SUITES_FILE)
    payload["reported"]["suites"] = (
        {"not_measured": suites["_absent"]} if "_absent" in suites else suites)
    # The census and the transform diff are E13's evidence, and §1.5 asks for
    # both to be readable without opening a cell: a reader who wants to know
    # WHICH function's wrapper moved should not have to know that E13 is where
    # that lives.
    e13 = payload["gated"].get("E13") or {}
    payload["reported"]["census"] = e13.get("census") or {
        "not_measured": "E13 was not measured"}
    payload["reported"]["transform_diff"] = e13.get("transform_diff") or {
        "not_measured": "E13 was not measured"}
    payload["reported"]["the_three_readings"] = (
        {"not_measured": reads_record["_absent"]}
        if "_absent" in reads_record else
        {k: reads_record.get(k) for k in
         ("run_id", "reads", "record", "record_sha256", "questions_from",
          "questions_sha256")})
    return payload, reads_record


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 4:
        sys.stderr.write("usage: assemble_s5debts.py <results dir> <out> "
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

    results = Path(args[0])
    payload, reads_record = build(results)

    # The reads must have been taken against BOTH locked §1s: this slice's,
    # whose §1.2-§1.4 are the predicted numbers, and rung 4's, whose §1 is the
    # questions. A dry run overrides the second with `E12_RECORD`.
    checks = {"hashed_set": verify_hashes(reads_record)}
    for label, path, got in (
            ("reads_read_this_record", RECORD,
             reads_record.get("record_sha256")),
            ("questions_read_rung_fours_record", RUNG4_RECORD,
             reads_record.get("questions_sha256"))):
        want = hashlib.sha256(path.read_bytes()).hexdigest()
        checks[label] = {
            "ok": got == want, "expected_sha256": want, "read_sha256": got,
            "why": [] if got == want else [
                f"the reads were taken against a {path.name} whose sha256 is "
                f"{got}, and this tree's is {want}"]}
    payload["verification"] = checks

    payload["recorded_by"] = {"recorder": recorder, "commit": rev}
    # The lens label first, strictly -- then the recorder provenance, which
    # expects `lens` to already be on the cell.
    payload = redact(stamp(lens_stamp(payload, strict=True), recorder, rev),
                     pairs)
    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble_s5debts: a box path survived redaction and "
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
    for name, got in checks.items():
        sys.stderr.write(f"{name}: {'OK' if got['ok'] else 'FAILED'}"
                         + ("" if got["ok"] else " -- " + "; ".join(got["why"]))
                         + "\n")
    return 0 if all(c["ok"] for c in checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
