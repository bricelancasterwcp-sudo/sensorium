"""Cross-recorder conformance: fixtures described in JSON
(`tests/fixtures/rust-spools/<case>/case.json`), converted by the REAL
`cargo-sensorium convert` binary, then every question in the case's
`questions.json` asked of the REAL Python CLI -- exactly as
`tests/test_vectors.py` asks its questions of a Python-built trace. A rule
that passes here and in `test_vectors.py` is a rule both recorders keep; a
trace this converter writes that the Python reader refuses (`TraceFormatError`
or a missing required meta key) is the one drift this module exists to
catch.

Skipped BY NAME (never silently) unless `SENSORIUM_CARGO_SENSORIUM` names a
built `cargo-sensorium` binary: the Python CI matrix has no Rust toolchain,
so this module runs only where a `rust` job built one and set the variable.
"""
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from corpus.run_corpus import check_question
from sensorium.store import db
from sensorium.store.db import TraceFormatError
from sensorium.store.reader import Trace
from tests.helpers import run_cli

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "rust-spools"

# `rust-spools` has a hyphen, so it is not an importable package name --
# loaded by path, the same technique `tests/helpers.py`'s `load_module` uses
# for a fixture program.
_spec = importlib.util.spec_from_file_location("rust_spools_gen",
                                               FIXTURES / "gen.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

CASES = sorted(p.name for p in FIXTURES.iterdir()
               if (p / "case.json").is_file())

CARGO_SENSORIUM = os.environ.get("SENSORIUM_CARGO_SENSORIUM")
pytestmark = pytest.mark.skipif(
    not CARGO_SENSORIUM,
    reason="SENSORIUM_CARGO_SENSORIUM is not set -- built only by CI's "
           "`rust` job; set it by hand to a built cargo-sensorium binary "
           "to run this module locally")

_RUN_LINE = re.compile(
    r"^run: (?P<run_id>\S+)  pid: (?P<pid>\d+)  exe: (?P<exe>\S+)  "
    r"events: (?P<events>\d+)  threads: (?P<threads>\d+)  "
    r"exit: (?P<exit>.+)$", re.MULTILINE)


def _sub(value, run_id: str, run_id2: str | None):
    """`$RUN` / `$RUN2` -> the real run ids this case converted to, over
    EVERY string in a question -- command, expect_contains, expect_line
    groups, expect_absent, expect_count keys -- not just the command. A
    question here checks for a run id `runid::mint` chose at conversion
    time, which questions.json cannot spell literally the way a vector's
    hand-built meta can (`tests/vectors.py`'s `sub` substitutes only the
    command for exactly that reason: a vector's `meta.child_runs` already
    holds the literal id). `$RUN2` first, same rule as `tests/vectors.py`:
    substituting `$RUN` first turns `$RUN2` into `<run-id>2`, a silent wrong
    lookup instead of an absent one.
    """
    if isinstance(value, str):
        if run_id2 is not None:
            value = value.replace("$RUN2", run_id2)
        return value.replace("$RUN", run_id)
    if isinstance(value, list):
        return [_sub(v, run_id, run_id2) for v in value]
    if isinstance(value, dict):
        return {k: _sub(v, run_id, run_id2) for k, v in value.items()}
    return value


def _convert(spool_dir: Path, sdir: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, SENSORIUM_DIR=str(sdir))
    return subprocess.run([CARGO_SENSORIUM, "convert", str(spool_dir)],
                          env=env, capture_output=True, text=True, check=False)


def _run_ids(stdout: str) -> list[str]:
    return [m.group("run_id") for m in _RUN_LINE.finditer(stdout)]


def _load_case(case_name: str) -> tuple[dict, list[dict]]:
    case_dir = FIXTURES / case_name
    case = json.loads((case_dir / "case.json").read_text())
    questions = json.loads((case_dir / "questions.json").read_text())
    return case, questions


@pytest.mark.parametrize("case_name", CASES)
def test_case_converts_and_answers_every_question(case_name, tmp_path):
    case, questions = _load_case(case_name)
    assert questions, f"{case_name}: questions.json asserts nothing"

    spool_dir = gen.materialize(case, tmp_path / "fixture")
    sdir = tmp_path / "sdir"
    result = _convert(spool_dir, sdir)
    assert result.returncode == 0, (
        f"{case_name}: cargo-sensorium convert failed (exit "
        f"{result.returncode}):\n{result.stdout}{result.stderr}")

    run_ids = _run_ids(result.stdout)
    assert run_ids, f"{case_name}: no `run:` line in:\n{result.stdout}"
    run_id, run_id2 = run_ids[0], (run_ids[1] if len(run_ids) > 1 else None)

    # Byte-exact pin of the `run:` line's own format, on the one case whose
    # every field is fully determined by the fixture: two-space separators,
    # the literal field names, and `exit: unwitnessed` for a process with no
    # `<pid>.runner.json`. Every other case's line is checked only through
    # `_run_ids` above (it must exist and parse) -- pinning the format twice
    # would be two tests of one fact.
    if case_name == "unwitnessed-exit":
        expected = (f"run: {run_id}  pid: 5001  exe: fixture-solo  "
                    "events: 2  threads: 1  exit: unwitnessed")
        assert expected in result.stdout.splitlines(), result.stdout

    for q in questions:
        subbed = _sub(q, run_id, run_id2)
        cmd = subbed["command"]
        r = run_cli(cmd, cwd=tmp_path, sensorium_dir=sdir)
        bad = check_question(subbed, r.stdout + r.stderr, r.returncode)
        assert not bad, (
            f"{case_name}/{q['id']}: " + "; ".join(bad)
            + f"\n    ask: {q['ask']}"
            + f"\n    cmd: sensorium {' '.join(cmd)}"
            + f"\n    got: {r.stdout}{r.stderr}")

    # The one check every case runs regardless of what it otherwise pins:
    # the Python reader must open every trace this converter wrote with no
    # TraceFormatError, and must find no required meta key missing -- a
    # Rust-writer/contract drift is exactly what would fail here.
    dbs = sorted((sdir / "traces").glob("*.db"))
    assert dbs, f"{case_name}: no trace file written under {sdir / 'traces'}"
    for db_path in dbs:
        try:
            trace = Trace.open(db_path)
        except TraceFormatError as e:
            pytest.fail(f"{case_name}: {db_path.name} refused at open: {e}")
        missing = db.missing_required(trace._c)
        assert missing == [], (
            f"{case_name}: {db_path.name} is missing required meta key(s) "
            f"{missing}")


def test_every_case_pins_a_named_invariant_and_asserts_something():
    """`docs/TRACE-FORMAT.md` §8's rule for the Python vectors, restated for
    the Rust-side ones: a question with no assertion always passes, which is
    the one thing a conformance suite must not contain."""
    assert CASES, "no rust-spool fixtures found"
    for name in ("identical-pair", "panic-unwind", "live-thread",
                 "child-linked", "unwitnessed-exit", "unnamed-task"):
        assert name in CASES, f"missing fixture case {name!r}"
    for case_name in CASES:
        case, questions = _load_case(case_name)
        assert case.get("processes"), f"{case_name}: no processes"
        assert questions, f"{case_name}: questions.json asserts nothing"
        for q in questions:
            where = f"{case_name}/{q.get('id')}"
            assert q.get("id") and q.get("ask"), f"{where}: needs id and ask"
            assert isinstance(q.get("command"), list) and q["command"], where
            assert any(q.get(k) for k in
                      ("expect_contains", "expect_line", "expect_count")), (
                f"{where}: asserts nothing -- needs a non-empty "
                "expect_contains / expect_line / expect_count")
