"""E15's results file: the ten cells, stamped, with their provenance checked.

    .venv/bin/python typescript/acceptance/assemble_e15.py \\
        <raw> <survey> <record> <out.json> <recorder> <rev> [PATH=LABEL]...

The argument order is `assemble_s5debts.py`'s idea -- inputs, output, then
who recorded it at which commit -- with the two documents this record defers
to named explicitly, because both are checked rather than trusted.

FOUR PROVENANCE CHECKS, AND WHY EACH ONE EXISTS
------------------------------------------------
* **the raw is not a dry run.** `e15.py` records `preflight.dry_run: true`
  when `E15_ROWS` overrode the survey's population (brief Step 5). A dry run
  plumbs the instrument against `corpus/typescript`, whose three test files
  are not the survey's 31; assembling one would publish numbers about a
  different subject under §1's endpoints. This is the check the dry run
  itself is run to exercise.
* **the driver is 0.14.0.** §1 requires it on every trace this record cites
  (plan ruling A8). `e15.py`'s preflight refuses at `exit=3` on anything
  else; re-checking it here is the difference between "the instrument says
  it checked" and "the results file was assembled from a run that did".
* **§1 has not moved.** Its sha256 is recomputed from the record on disk and
  compared against `tests/test_acceptance_e15_lock.BYTE_LOCK`. The constants
  are IMPORTED from the lock test rather than re-spelled: two copies of one
  lock is one lock that can be half-updated.
* **the survey has not moved.** Its sha256 against `SURVEY_LOCK`. The survey
  is where every row's CLASS comes from, and H4 asks a different question of
  a deterministic row -- so a table corrected after 31 verdicts printed would
  rewrite the prediction rather than the reading.

A failure is carried IN the payload under its own name and the assembler
exits 1 -- the results file is written either way, because a reader
diagnosing a failed verification needs the cells it failed over (ruling P9 of
the debts slice, unchanged).

`lens.stamp(..., strict=True)`: every cell here was minted by `e15_report.py`
in this slice, after `cell()` stopped embedding the lens label, so a cell
arriving with a `lens` of its own is a defect and not history.

The optional trailing `PATH=LABEL` pairs are `assemble_s5debts.py`'s
redaction, for the one thing this record's cells can carry that no other
slice's could: a DIVERGED row's step line prints the diverging function's
FILE, which on E15's subject is a path under the throwaway copy. The
redaction is applied last and `offenders()` refuses at exit 2 on anything
that survives it, so a results file committed by Task 8 cannot carry one.
"""
import hashlib
import json
import sys
from pathlib import Path

from assemble import FORBIDDEN, offenders, redact                  # noqa: F401
from e15_read import parse_survey
from e15_report import ENDPOINTS, ORDER, cells, stops
from lens import LENS, REPO_ROOT
from lens import stamp as lens_stamp

sys.path.insert(0, str(REPO_ROOT))

from tests.test_acceptance_e15_lock import (BYTE_LOCK,  # noqa: E402
                                            SURVEY_LOCK, byte_lock_facts)

#: The Python driver version §1 requires on every trace this record cites.
DRIVER_VERSION = "0.14.0"

RECORD_REL = ("docs/superpowers/acceptance/"
              "2026-09-13-sensorium-e15-refocus-typescript.md")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(raw: dict, survey_path: Path, record_path: Path) -> dict:
    """The four checks, each with what it wanted and what it got."""
    pre = raw.get("preflight") or {}
    dry = pre.get("dry_run")
    got_version = pre.get("driver_version")
    survey_sha = _sha256(survey_path)
    facts = byte_lock_facts(record_path.read_text(encoding="utf-8"), BYTE_LOCK)
    return {
        "not_a_dry_run": {
            "ok": dry is False, "dry_run": dry,
            "why": [] if dry is False else [
                "this raw record was written by a DRY RUN "
                f"(preflight.dry_run = {dry!r}); its rows are "
                "corpus/typescript's, not the survey's 31, and no number "
                "from a dry run is kept"]},
        "driver_version": {
            "ok": got_version == DRIVER_VERSION,
            "expected": DRIVER_VERSION, "read": got_version,
            "why": [] if got_version == DRIVER_VERSION else [
                f"the run recorded driver_version {got_version!r}; §1 cites "
                f"{DRIVER_VERSION} on every trace"]},
        "section_one_has_not_moved": {
            "ok": facts["identical"], "expected_sha256": BYTE_LOCK,
            "read_sha256": facts["working_tree_sha256"],
            "range": facts["range"],
            "why": [] if facts["identical"] else [
                f"§1 of {RECORD_REL} hashes to "
                f"{facts['working_tree_sha256']} and the lock is "
                f"{BYTE_LOCK}"]},
        "the_survey_has_not_moved": {
            "ok": survey_sha == SURVEY_LOCK, "expected_sha256": SURVEY_LOCK,
            "read_sha256": survey_sha,
            "why": [] if survey_sha == SURVEY_LOCK else [
                f"the survey hashes to {survey_sha} and §1 pins "
                f"{SURVEY_LOCK}"]},
    }


def build(raw: dict, survey_rows: list) -> dict:
    gated = cells(raw, survey_rows)
    stopped = stops(gated)
    return {
        "record": RECORD_REL,
        "lens": LENS,
        "schema": ("every measurement is {value, n, lens, dropped, holds, "
                   "evidence}; a null value with a non-empty dropped list is "
                   "the only representation of 'not measured'; 0 is "
                   "measured-and-zero"),
        "gated": gated,
        # §1's own ten, named apart from ruling P16's two primed readings, so
        # a reader of the results file can tell the locked endpoints from the
        # cells that re-read two of them.
        "endpoints": list(ENDPOINTS),
        "primed_readings": [name for name in ORDER if name not in ENDPOINTS],
        # Every STOP counts, the primed readings' included: a STOP is a STOP
        # whichever cell raised it.
        "word": "DONE-WITH-STOP" if stopped else "DONE",
        "stops": stopped,
        "reported": {
            "preflight": raw.get("preflight"),
            "originals": raw.get("originals"),
            "survey_check": raw.get("survey_check"),
            "controls": {k: {kk: vv for kk, vv in (v or {}).items()
                             if kk != "parsed"}
                         for k, v in (raw.get("controls") or {}).items()},
            "fences": raw.get("fences"),
            "cleanup": raw.get("cleanup"),
            "phases": raw.get("phases"),
        },
    }


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 6:
        sys.stderr.write(
            "usage: assemble_e15.py <raw> <survey> <record> <out.json> "
            "<recorder> <rev> [PATH=LABEL]...\n")
        return 2
    raw_path, survey_path, record_path, out_path = (Path(a) for a in args[:4])
    recorder, rev = args[4], args[5]
    if len(rev) != 40:
        sys.stderr.write("the rev is the FULL 40-character sha the cells were "
                         f"recorded at, not {rev!r}\n")
        return 2
    pairs = []
    for spec in args[6:]:
        if "=" not in spec:
            sys.stderr.write(f"a redaction is PATH=LABEL, not {spec!r}\n")
            return 2
        needle, _, label = spec.partition("=")
        pairs.append((needle, label))
    # Longest needle first: a worktree path sits UNDER its parent directory,
    # and the shorter prefix would half-rewrite it.
    pairs.sort(key=lambda p: len(p[0]), reverse=True)

    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"cannot read the raw record {raw_path}: {e}\n")
        return 2
    survey_text = survey_path.read_text(encoding="utf-8")
    payload = build(raw, parse_survey(survey_text)["rows"])
    payload["verification"] = verify(raw, survey_path, record_path)
    payload["recorded_by"] = {"recorder": recorder, "commit": rev}
    payload = redact(lens_stamp(payload, strict=True), pairs)

    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble_e15: a box path survived redaction and "
                         "this file is committed; add a PATH=LABEL for it:\n")
        for where, value in bad[:10]:
            sys.stderr.write(f"  {where}: {value[:160]}\n")
        return 2
    out_path.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                        encoding="utf-8")
    checks = payload["verification"]
    sys.stderr.write(f"wrote {out_path} (word: {payload['word']})\n")
    for name, got in checks.items():
        sys.stderr.write(f"{name}: {'OK' if got['ok'] else 'FAILED'}"
                         + ("" if got["ok"] else " -- " + "; ".join(got["why"]))
                         + "\n")
    return 0 if all(c["ok"] for c in checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
