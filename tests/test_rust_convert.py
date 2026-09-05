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
# Not a module-level `pytestmark`: only the test that actually drives the
# built binary needs it skipped. `test_every_case_pins_a_named_invariant_
# and_asserts_something` below is a pure JSON self-check over the fixtures
# and needs no Rust toolchain at all -- it belongs on the Python matrix, not
# skipped alongside the tests that do need SENSORIUM_CARGO_SENSORIUM.
_SKIP_REASON = ("SENSORIUM_CARGO_SENSORIUM is not set -- built only by CI's "
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


@pytest.mark.skipif(not CARGO_SENSORIUM, reason=_SKIP_REASON)
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
    expected_spawns = [s for m in case.get("manifests", {}).values()
                       for s in m.get("spawns", [])]
    for db_path in dbs:
        try:
            trace = Trace.open(db_path)
        except TraceFormatError as e:
            pytest.fail(f"{case_name}: {db_path.name} refused at open: {e}")
        missing = db.missing_required(trace._c)
        assert missing == [], (
            f"{case_name}: {db_path.name} is missing required meta key(s) "
            f"{missing}")
        # The manifest's `spawns` entries reach the trace WHOLE. The converter
        # carries an entry as opaque JSON (`convert/spool.rs`'s
        # `Vec<serde_json::Value>`), so no Rust code names `qualname` or
        # `ordinal` and nothing but a read of the finished trace says the two
        # fields `docs/TRACE-FORMAT.md` §4 promises survived the crossing.
        # Only cases whose single process registers every unit reach this --
        # `spawns` is scoped to the units a process registered, and the one
        # case that declares any (`spawn-sites`) has exactly one process.
        if expected_spawns:
            assert trace.meta.get("spawns") == expected_spawns, (
                f"{case_name}: {db_path.name} meta spawns "
                f"{trace.meta.get('spawns')!r} is not the manifest's "
                f"{expected_spawns!r}")
        _check_err_flow_payloads(case_name, db_path.name, trace)
        if case_name == "errflow":
            _check_errflow_chain_terminals(db_path.name, trace)


def _check_err_flow_payloads(case_name: str, db_name: str, trace) -> None:
    """Every `exc` object a Rust trace carries says which KIND of thing it
    is, and the two kinds' serials never collide.

    `docs/TRACE-FORMAT.md` §5: a Rust RAISE/HANDLED carries `exc.kind` --
    `"err"` for an `Err` value, `"panic"` for a panic -- and the `Err` chain
    serials are minted in a namespace starting at `1 << 32`, disjoint from
    the per-thread panic serials that start at 1. A rule that instead read
    `type == "panic"` would misread a workspace error type spelled that way,
    and a shared serial namespace would let one panic and one chain claim to
    be the same thing. An `err` event also carries the `chain` object the
    rung-3 disposition rules are computed from; a panic RAISE carries none.
    """
    for e in trace.events():
        if e.kind not in ("RAISE", "HANDLED"):
            continue
        exc = (e.payload or {}).get("exc")
        where = f"{case_name}/{db_name}: e{e.id} {e.kind}"
        assert exc is not None, f"{where} carries no exc object"
        kind = exc.get("kind")
        assert kind in ("err", "panic"), (
            f"{where} carries exc.kind {kind!r}; a Rust exc object says "
            "which of the two kinds it is")
        serial = exc.get("serial")
        # Named before it is compared: an absent serial would otherwise fail
        # as a TypeError against `2 ** 32`, which says nothing about the
        # trace.
        assert isinstance(serial, int), (
            f"{where} carries exc.serial {serial!r}; every Rust exc object "
            "is identified by an integer serial")
        chain = (e.payload or {}).get("chain")
        if kind == "err":
            assert serial >= 2 ** 32, (
                f"{where} is an Err with serial {serial}, below the "
                "1 << 32 the chain namespace starts at -- it could collide "
                "with a panic serial on the same thread")
            assert isinstance(chain, dict), (
                f"{where} is an Err with chain {chain!r}; the disposition "
                "rules read a chain object off every err-flow event")
            assert set(chain) >= {"serial", "hop", "origin", "translated"}, (
                f"{where} chain is {sorted(chain)}, missing one of "
                "serial/hop/origin/translated")
            assert chain["serial"] == serial, (
                f"{where} chain serial {chain['serial']} is not the exc's "
                f"{serial}")
        else:
            assert serial < 2 ** 32, (
                f"{where} is a panic with serial {serial}, inside the "
                "chain namespace")
            assert chain is None, (
                f"{where} is a panic carrying a chain object {chain!r}")


def _chains(trace) -> dict:
    """`(thread, chain serial)` -> the chain's events in trace order, the
    same grouping `query/exceptions_rust.Index` does. Serials are minted
    per THREAD, so the thread is half the key."""
    out: dict = {}
    for e in trace.events(kind=("RAISE", "HANDLED")):
        p = e.payload or {}
        if (p.get("exc") or {}).get("kind") != "err":
            continue
        out.setdefault((e.thread_id, p["chain"]["serial"]), []).append(e)
    return out


def _check_errflow_chain_terminals(db_name: str, trace) -> None:
    """The `errflow` case's two chains end with the exact terminals the
    §2a machine owes them, and every event before a chain's last carries
    NO terminal at all.

    This is the one place the two halves of the rung are held against each
    other by VALUE. `_check_err_flow_payloads` above pins that a `chain`
    object exists and `tests/test_exceptions_rust.py` pins what each
    terminal MEANS, but both would stay green if the converter stopped
    writing terminals: the shape check does not require the key, and the
    Python tests build their own traces. Deleting `terminal` from the
    machine would then be a silent change that turned every real Rust
    answer into "the recording records no ending for this chain".

    The fixture is two chains of one `Err` type: `inner`'s first `Err`,
    which `swallow`'s `.ok()` absorbs before `swallow` returns ok
    (`swallowed_candidate` on the HANDLED), and `inner`'s second, which
    `run` takes by `?` and returns from a `#[test]` fn
    (`returned_to_harness` on the synthesised `exit` RAISE that is the
    chain's last event). Both were BORN at an instrumented site, so both
    say `origin: "workspace"` -- `"outside"` there would be the trace
    claiming an `Err` it watched being made had arrived from a dependency.
    """
    chains = _chains(trace)
    assert len(chains) == 2, (
        f"errflow/{db_name}: {len(chains)} err chains, expected 2 "
        f"({sorted(chains)})")
    ends = {}
    for key, events in chains.items():
        for e in events[:-1]:
            assert "terminal" not in e.payload["chain"], (
                f"errflow/{db_name}: e{e.id} is not chain {key[1]}'s last "
                f"event and carries terminal "
                f"{e.payload['chain']['terminal']!r}; the key rides the last "
                "event and is omitted everywhere else")
        for e in events:
            assert e.payload["chain"]["origin"] == "workspace", (
                f"errflow/{db_name}: e{e.id} says origin "
                f"{e.payload['chain']['origin']!r}; this chain was born at "
                "an instrumented site")
        last = events[-1]
        chain = last.payload["chain"]
        # Named, not indexed: a converter that stopped writing terminals
        # would otherwise fail here as a KeyError, which says nothing about
        # the trace to whoever reads the run.
        assert "terminal" in chain, (
            f"errflow/{db_name}: e{last.id} is chain {key[1]}'s last event "
            "and carries no terminal; the disposition rules read a chain's "
            "ending from there and recompute nothing, so a chain with no "
            "terminal reads as one whose ending was never recorded")
        ends[chain["terminal"]] = (last.kind, last.payload["how"])
    assert ends == {"swallowed_candidate": ("HANDLED", "sink_ok"),
                    "returned_to_harness": ("RAISE", "exit")}, ends
    hops = {key: [e.payload["chain"]["hop"] for e in events]
            for key, events in chains.items()}
    assert sorted(hops.values()) == [[1, 1], [1, 2, 3]], hops


def test_gen_refuses_an_err_flow_how_that_belongs_to_the_other_record_kind():
    """A fixture cannot describe a record no runtime could write.

    The transformer writes the manifest row and the runtime writes the `how`
    byte from ONE splice, so a RAISE carrying a sink's `how` is corruption --
    the converter refuses it by name, and a case that spelled one would be
    pinning the refusal by accident instead of the shape it meant to.
    """
    with pytest.raises(ValueError, match="belongs to a handled record"):
        gen._encode_op({"op": "raise", "unit": 0, "site": 0, "seq": 0,
                        "ts": 1, "how": "sink_ok"})
    with pytest.raises(ValueError, match="belongs to a raise record"):
        gen._encode_op({"op": "handled", "unit": 0, "site": 0, "seq": 0,
                        "ts": 1, "how": "try"})
    # 8 is `exit`, the converter's own synthesised origin, which never
    # appears on the wire -- so a case cannot write one by name either.
    with pytest.raises(ValueError, match="unknown err-flow how 'exit'"):
        gen._encode_op({"op": "raise", "unit": 0, "site": 0, "seq": 0,
                        "ts": 1, "how": "exit"})


def test_every_case_pins_a_named_invariant_and_asserts_something():
    """`docs/TRACE-FORMAT.md` §8's rule for the Python vectors, restated for
    the Rust-side ones: a question with no assertion always passes, which is
    the one thing a conformance suite must not contain."""
    assert CASES, "no rust-spool fixtures found"
    for name in ("identical-pair", "panic-unwind", "live-thread",
                 "child-linked", "unwitnessed-exit", "unnamed-task",
                 "spawn-sites", "errflow"):
        assert name in CASES, f"missing fixture case {name!r}"
    for case_name in CASES:
        case, questions = _load_case(case_name)
        assert case.get("processes"), f"{case_name}: no processes"
        # A manifest spawn entry carries every field `docs/TRACE-FORMAT.md`
        # §4 names, `qualname` and `ordinal` included -- a fixture that
        # dropped one would still convert and still answer its questions,
        # and the passthrough it is here to exercise would go untested.
        for metadata, m in case.get("manifests", {}).items():
            for i, spawn in enumerate(m.get("spawns", [])):
                assert set(spawn) == {"file", "line", "wrapped", "reason",
                                      "qualname", "ordinal"}, (
                    f"{case_name}/{metadata}: spawn entry {i} is "
                    f"{sorted(spawn)}, not the manifest's spawn shape")
                assert (spawn["ordinal"] is None) != bool(spawn["wrapped"]), (
                    f"{case_name}/{metadata}: spawn entry {i} has "
                    f"wrapped={spawn['wrapped']} with ordinal="
                    f"{spawn['ordinal']!r}; a declared site takes no ordinal "
                    "and a wrapped one always has its rank")
        assert questions, f"{case_name}: questions.json asserts nothing"
        for q in questions:
            where = f"{case_name}/{q.get('id')}"
            assert q.get("id") and q.get("ask"), f"{where}: needs id and ask"
            assert isinstance(q.get("command"), list) and q["command"], where
            assert any(q.get(k) for k in
                      ("expect_contains", "expect_line", "expect_count")), (
                f"{where}: asserts nothing -- needs a non-empty "
                "expect_contains / expect_line / expect_count")
