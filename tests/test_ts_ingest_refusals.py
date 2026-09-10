"""The refusal `sensorium ts ingest` makes when a directory holds no spool.

Everything else that command refuses -- a torn record, a second ingest, a
directory with no invocation record -- is `tests/test_ts_ingest_meta.py`,
beside the traces it converts. These live here because that module is at the
800-line ceiling, and because a NO-SPOOL directory is a subject of its own:
the harness ran, the recorder saw files, and the tallies beside the missing
spools are the only witness to what became of them.
"""
import json
from pathlib import Path

from tests.helpers import run_cli
from tests.ts_spools import FIXTURES


def spool_with_tallies(tmp_path: Path, tallies: dict) -> Path:
    """A spool directory as the driver leaves one -- `invocation.json` and a
    `manifests/` -- holding no `.jsonl` at all.

    The invocation record is `async-chain`'s own bytes: what these tests are
    about is the tallies, and a hand-written invocation would be a second
    copy of a contract `sensorium.ts.invocation` already holds.
    """
    spool = tmp_path / "spool"
    (spool / "manifests").mkdir(parents=True)
    (spool / "invocation.json").write_bytes(
        (FIXTURES / "async-chain" / "invocation.json").read_bytes())
    for name, tally in tallies.items():
        (spool / "manifests" / name).write_text(json.dumps(tally))
    return spool


def ingest(tmp_path: Path, spool: Path):
    return run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                   sensorium_dir=tmp_path / "sdir")


def test_a_directory_with_only_commonjs_tallies_and_no_spool_names_the_exclusions(
        tmp_path):
    """R45. `node --test` over a CommonJS-only suite runs GREEN and records
    nothing, and what met the caller was "nothing was recorded, or the
    recorder wrote somewhere else" -- a sentence naming neither the cause
    nor the fix. The tallies know: every file this run met was excluded.
    """
    spool = spool_with_tallies(tmp_path, {
        "_tally-1.json": {"files_transformed": 0, "excluded": {"commonjs": 2}}})
    r = ingest(tmp_path, spool)
    assert r.returncode == 2, f"{r.stdout}{r.stderr}"
    assert ("this run transformed 0 files and excluded 2 "
            "(commonjs x2 across 1 tallies)") in r.stderr, r.stderr
    assert "this recorder instruments ES modules only" in r.stderr, r.stderr


def test_a_directory_with_a_transformed_file_keeps_the_old_sentence(tmp_path):
    """The other arm, and the reason the new sentence is conditional. A run
    that DID transform a file and still wrote no spool went wrong somewhere
    no tally can see -- the runtime never loaded, the spool went elsewhere --
    and a converter that named CommonJS there would be guessing.
    """
    spool = spool_with_tallies(tmp_path, {
        "_tally-1.json": {"files_transformed": 1, "excluded": {"commonjs": 1}}})
    r = ingest(tmp_path, spool)
    assert r.returncode == 2, f"{r.stdout}{r.stderr}"
    assert ("nothing was recorded, or the recorder wrote somewhere "
            "else") in r.stderr, r.stderr
    assert "commonjs" not in r.stderr, r.stderr


def test_every_reason_is_named_with_its_own_count(tmp_path):
    """P6's whole point: one bare reason loses the split as soon as there
    are two, and a file the transform could not PARSE is not a file it
    declined to instrument. Three tallies and two reasons here, so no two
    of the three numbers in the sentence can stand in for each other.
    """
    spool = spool_with_tallies(tmp_path, {
        "_tally.json": {"files_transformed": 0,
                        "excluded": {"commonjs": 2, "parse-error": 1}},
        "_tally-9.json": {"files_transformed": 0, "excluded": {"commonjs": 1}},
        "_tally-11.json": {"files_transformed": 0, "excluded": {"commonjs": 1}}})
    r = ingest(tmp_path, spool)
    assert r.returncode == 2, f"{r.stdout}{r.stderr}"
    assert ("excluded 5 (commonjs x4, parse-error x1 across 3 tallies)"
            ) in r.stderr, r.stderr
    assert "this recorder instruments ES modules only" in r.stderr, r.stderr


def test_the_es_modules_clause_rides_on_commonjs_being_a_reason(tmp_path):
    """The other half of P6. A suite whose files all failed to PARSE was
    excluded too, and it is not a CommonJS suite: the sentence still counts
    what happened, and says nothing about ES modules, because "your suite is
    CommonJS" would be false advice about a file this recorder could not
    read.
    """
    spool = spool_with_tallies(tmp_path, {
        "_tally-1.json": {"files_transformed": 0,
                          "excluded": {"parse-error": 2}}})
    r = ingest(tmp_path, spool)
    assert r.returncode == 2, f"{r.stdout}{r.stderr}"
    assert ("excluded 2 (parse-error x2 across 1 tallies)") in r.stderr
    assert "ES modules only" not in r.stderr, r.stderr
