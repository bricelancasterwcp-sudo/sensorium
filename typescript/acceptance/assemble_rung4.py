"""S5 rung 4's cells, gathered into its acceptance record's results file.

    .venv/bin/python typescript/acceptance/assemble_rung4.py \\
        <results dir> <out> <recorder> <rev> [PATH=LABEL]...

The argument order is `assemble_rung3.py`'s, unchanged, so the two read the
same way at a call site.

Rung 3's assembler plus the two checks this rung's pre-registration puts on
the assembler rather than on an endpoint:

* **the hashed set.** `sha256sum -c` the T9 list from the STORE ROOT, after
  every read. Every entry must verify EXCEPT `invocations.jsonl`, which the
  reads themselves append to -- so that one is checked as an APPEND: the
  journal's first `<T9 line count>` lines must still hash to the listed
  value. A journal that was rewritten rather than appended to fails that,
  and a trace or spool that moved fails the plain check.
* **the journal's delta.** Exactly one new line per read command in §1.5's
  list -- and the length of that list is READ FROM THE RECORD, never typed
  here (ruling R6). The record says thirteen; if it ever says fourteen, this
  file expects fourteen without being edited.

Neither check is a verdict about the recorder: both are about whether the
numbers in the record came off the bytes the record pins. A failure is
carried in the payload, named, and the assembler exits non-zero -- the
results file is written either way, because a reader diagnosing a failed
verification needs the cells it failed over.

`lens.stamp(..., strict=True)`: every instrument this assembler reads was
written in this rung, after `cell()` stopped embedding the lens label, so a
cell arriving with a `lens` of its own is a defect and not history.
"""
import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

from assemble import FORBIDDEN, offenders, redact  # noqa: F401
from assemble_rung2 import OWN, STAMPED, load, stamp
from e12_report import RECORD, read_commands, section1
from lens import LENS, cell
from lens import stamp as lens_stamp

#: The five cells `e12_report.py` writes in ONE file: five readings of ONE
#: set of thirteen reads, and splitting them across files would invite a
#: reader to think the store was opened five times.
READS_FILE = "e12-reads.json"
READS_CELLS = ("H1", "H2", "H4", "H5", "H6")

#: The endpoint cells read straight from one instrument's JSON.
GATED_FILES = {"H3": "e12-h3.json", "H7": "e12-h7.json", "H8": "e12-h8.json"}

#: The two fences, run FIRST and reported beside H8 (rulings R12, R35).
FENCE_FILES = {"E-legacy": "e-legacy.json", "E-branch": "e-branch.json"}

#: The record's §3 row order.
ORDER = ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"]

#: The one entry of the hashed set the reads are EXPECTED to have appended to.
JOURNAL = "invocations.jsonl"


def read_cell(results: Path, name: str, filename: str) -> dict:
    """One instrument's cell, or a null naming the file that was not there."""
    data = load(results / filename)
    if "_absent" in data:
        return cell(None, 0, [f"{name} was not measured: {data['_absent']}"])
    return data


def reads(results: Path) -> tuple[dict, dict]:
    """The five cells of the thirteen reads, and the reads' own record."""
    data = load(results / READS_FILE)
    if "_absent" in data:
        return ({name: cell(None, 0, [f"{name} was not measured: "
                                      f"{data['_absent']}"])
                 for name in READS_CELLS}, data)
    got = data.get("cells") or {}
    return ({name: got.get(name) or cell(
        None, 0, [f"{name} is missing from {READS_FILE}"])
        for name in READS_CELLS}, data)


def verify_hashes(store: Path, hashes: Path, journal_at_t9: int) -> dict:
    """`sha256sum -c` from the store root, with the journal read as an append.

    The list is taken after the arms and before any read; the reads then
    append one line per command to `invocations.jsonl`, so that one entry is
    EXPECTED to fail the plain check and is verified against the file's first
    `journal_at_t9` lines instead."""
    if not hashes.is_file():
        return {"ok": False, "why": [f"no hash list at {hashes.name}"]}
    proc = subprocess.run(["sha256sum", "-c", str(hashes)], cwd=store,
                          capture_output=True, text=True)
    rows = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    bad = [ln for ln in rows if not ln.endswith(": OK")]
    unexpected = [ln for ln in bad if not ln.startswith(f"{JOURNAL}:")]
    listed = {}
    for line in hashes.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name:
            listed[name.strip()] = digest.strip()
    # The journal, as an append: its first `journal_at_t9` lines, hashed.
    head = None
    path = store / JOURNAL
    if path.is_file():
        with path.open("rb") as fh:
            head = hashlib.sha256(
                b"".join(itertools.islice(fh, journal_at_t9))).hexdigest()
    append_only = head is not None and head == listed.get(JOURNAL)
    why = [f"a hashed file moved: {ln}" for ln in unexpected]
    if not append_only:
        why.append(f"{JOURNAL} is not the T9 file plus new lines: its first "
                   f"{journal_at_t9} line(s) hash to {head}, and the list "
                   f"says {listed.get(JOURNAL)}")
    return {"ok": not why, "why": why, "entries": len(listed),
            "checked": len(rows), "verified": len(rows) - len(bad),
            "journal_append_only": append_only,
            "journal_head_sha256": head, "journal_listed_sha256":
                listed.get(JOURNAL), "unexpected_failures": unexpected,
            "hash_list_sha256": hashlib.sha256(hashes.read_bytes()).hexdigest(),
            "exit": proc.returncode}


def verify_journal(store: Path, journal_at_t9: int, expected: int,
                   reads_record: dict) -> dict:
    """The journal's delta: exactly one new line per §1.5 command.

    Two readings of one fact -- the store's own line count against the count
    taken when the hash list was written, and `e12_report.py`'s before/after
    around the reads it ran. They should agree; if they do not, something
    else called the CLI against this store and the record must say so."""
    path = store / JOURNAL
    now = sum(1 for _ in path.open("rb")) if path.is_file() else 0
    from_store = now - journal_at_t9
    from_reads = (reads_record.get("journal") or {}).get("delta")
    why = []
    if from_store != expected:
        why.append(f"the journal grew by {from_store} line(s) since the hash "
                   f"list was written; §1.5 lists {expected} read command(s)")
    if from_reads is not None and from_reads != from_store:
        why.append(f"the reads counted a delta of {from_reads} and the store "
                   f"shows {from_store}: something other than the reads "
                   "called the CLI against this store")
    return {"ok": not why, "why": why, "expected": expected,
            "at_hash_time": journal_at_t9, "now": now,
            "delta_from_store": from_store, "delta_from_reads": from_reads}


def build(results: Path) -> tuple[dict, dict]:
    cells, reads_record = reads(results)
    payload = {
        "record": "docs/superpowers/acceptance/"
                  "2026-09-11-sensorium-s5-rung4-focus.md",
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
    for name, filename in FENCE_FILES.items():
        payload["reported"][name] = read_cell(results, name, filename)
    payload["reported"]["the_session"] = read_cell(
        results, "the session", "e12.json")
    payload["reported"]["the_thirteen_reads"] = (
        {"not_measured": reads_record["_absent"]}
        if "_absent" in reads_record else
        {k: reads_record.get(k) for k in
         ("run_ids", "commands_as_written", "commands_run", "order_change",
          "journal", "transcripts")})
    return payload, reads_record


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 4:
        sys.stderr.write("usage: assemble_rung4.py <results dir> <out> "
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

    # The two checks this rung puts on the assembler. The store and the hash
    # list come from the session's own cell, and the expected delta from the
    # record -- never from a literal here (ruling R6).
    session = payload["reported"]["the_session"]
    store = Path(session.get("store", ""))
    hashes = Path(session.get("hash_list", {}).get("path", ""))
    at_t9 = session.get("journal_lines_at_hash_time") or 0
    expected = len(read_commands(section1(RECORD.read_text(encoding="utf-8"))))
    # The reads must have been taken against THIS record's §1. A dry run
    # points `e12_report.py` at a scratch record (`E12_RECORD`); assembling
    # such reads into the rung's own results file would publish numbers read
    # against a pre-registration nobody locked.
    want_sha = hashlib.sha256(RECORD.read_bytes()).hexdigest()
    got_sha = reads_record.get("record_sha256")
    checks = {
        "reads_read_this_record": {
            "ok": got_sha == want_sha, "record_sha256": want_sha,
            "reads_read_sha256": got_sha,
            "why": [] if got_sha == want_sha else [
                "the reads were taken against a §1 whose sha256 is "
                f"{got_sha}, and this record's is {want_sha}"]},
        "hashed_set": verify_hashes(store, hashes, at_t9),
        "journal_delta": verify_journal(store, at_t9, expected, reads_record),
    }
    payload["verification"] = checks

    payload["recorded_by"] = {"recorder": recorder, "commit": rev}
    # The lens label first, strictly -- then the recorder provenance, which
    # expects `lens` to already be on the cell.
    payload = redact(stamp(lens_stamp(payload, strict=True), recorder, rev),
                     pairs)
    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble_rung4: a box path survived redaction and "
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
