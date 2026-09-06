"""The E9 acceptance TOOLING, tested without the box.

Nothing here runs cargo, the driver or the query CLI, opens the clone, reads
anything under `/mnt`, or needs an environment variable to be set by whoever
launched pytest. The only real files it opens are this repository's own: the
acceptance document (for the byte-lock) and the instrument's modules (for the
path scan).

What it tests is the places an E9 run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock — a lock that compared the wrong slice, that passed on a
  changed §1, or that fell through while `BYTE_LOCK` is `None`, lets an
  endpoint move after a number is read;
* none-versus-zero — a phase that did not run is `null` with a reason, a
  killed recording or reader publishes nulls with the kill as the reason, and
  no cell is ever filled from §1's predictions, which are the numbers already
  in the room;
* the locations the run touches, each one an environment variable, refused
  together when missing and refused when a fresh one is not fresh;
* each phase's log root in ITS OWN namespace — the wiring the entry slice's
  first launch died on.

The parsers and the sqlite joins are in `tests/test_acceptance_e9_read.py`;
the schema and the renderer are in `tests/test_acceptance_e9_record.py`. Each
mirrors the module it tests, and this file was split along that seam when it
reached the repository's 800-line ceiling.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_e9 as runner                                     # noqa: E402
import acceptance_e9_phases as phases                              # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

# Importing this runner re-points the SHARED log pointers at THIS document's
# workspace (its job). The sibling suites assert the same invariant for THEIR
# runners and all of them are imported at COLLECTION time, so whichever
# pytest collected last would own the pointer. Restoring E6‴'s pointers here
# makes every suite order-independent and costs nothing: each phase runs
# inside a `logs_at` block.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS

DOC_SHA = "15f0537587f55ec949a60c86543e6c4e1f7a0929cc57eb4a15320424185b67a5"

INSTRUMENT = ("acceptance_e9.py", "acceptance_e9_phases.py",
              "acceptance_e9_read.py", "acceptance_e9_schema.py",
              "render_e9.py")


# -- the byte-lock ---------------------------------------------------------


def _require_lock_commits(*shas):
    """The lock tests read `git show <sha>:<doc>`; a shallow checkout has no
    such commit. Skip BY NAME rather than pass on a missing commit — a
    skipped lock check must never look like a passed one."""
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) — the "
                        "byte-lock test is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) — skipped BY NAME, not passed")


def test_the_lock_sha_is_task_zeros_commit():
    """The one fact the whole pre-registration hangs on. A runner locked to
    a later commit would be locked to a §1 that could have moved after the
    instrument was written."""
    assert runner.BYTE_LOCK == "a4264b5"
    assert runner.ORIGINAL_LOCK is None


def test_the_e9_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a
    stray edit to §1 is caught before a run is launched rather than by a
    refusal with a clone already built."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_sha256"] == DOC_SHA


def test_the_e9_lock_is_one_sha_and_records_no_amendment():
    """§1 of this document is committed once and never amended. A record
    that silently reported an amendment would be describing another
    document, and one that referenced a footnote would have a hole at
    exactly the sentence the lock exists to pin."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"] == DOC_SHA


def test_the_e9_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself. A check that computes two shas, reports them
    unequal and proceeds is not a lock."""
    text = runner.DOC.read_text()
    doc = tmp_path / "e9.md"
    doc.write_text(text.replace("N = 26", "N = 27", 1))
    assert doc.read_text() != text, "the fixture did not change a byte"
    with pytest.raises(Refused) as e:
        rung3.byte_lock_check(doc, runner.BYTE_LOCK, None,
                              read_committed=lambda rel, c: text)
    assert "differs from the byte-lock" in str(e.value)


def test_an_unset_lock_REFUSES_rather_than_measuring(monkeypatch):
    """A `None` lock must stop the run. Falling through would measure
    against a pre-registration that can still be edited — which is the
    whole failure the lock exists to prevent."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked yet" in str(e.value)


# -- the locations ---------------------------------------------------------


def test_every_missing_location_is_named_in_ONE_refusal(monkeypatch):
    """One launch must report all of them. A preflight that refused on the
    first would cost five launches to discover five unset variables."""
    for key in runner.E9_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_e9()
    for key in runner.E9_ENV:
        assert key in str(e.value)


def test_the_five_locations_are_the_ones_the_run_touches(monkeypatch,
                                                         tmp_path):
    """Each variable lands under the key the phases resolve, and no location
    is compiled in. A key that did not match would send a recording into the
    wrong target while every command still succeeded."""
    for key, name in runner.E9_ENV.items():
        monkeypatch.setenv(key, str(tmp_path / name))
    p = runner.env_paths_e9()
    assert set(p) == set(runner.E9_ENV.values())
    assert p["sensorium_dir"] == tmp_path / "sensorium_dir"
    assert p["sensorium_bloomery"] == tmp_path / "sensorium_bloomery"
    assert p["sensorium_e9_target"] == tmp_path / "sensorium_e9_target"


def test_a_fresh_location_that_is_not_fresh_is_REFUSED(tmp_path):
    """§1.4 says FRESH. A warm target would record H2's build against
    another run's artifacts and a warm store could answer with another run's
    trace."""
    d = tmp_path / "warm"
    d.mkdir()
    (d / "leftover").write_text("x")
    with pytest.raises(Refused) as e:
        runner._require_fresh(d, "SENSORIUM_DIR")
    assert "not empty" in str(e.value)
    # and an absent one is created rather than refused
    runner._require_fresh(tmp_path / "cold", "SENSORIUM_DIR")
    assert (tmp_path / "cold").is_dir()


def test_the_corpus_target_is_derived_from_an_env_var_when_unset(
        monkeypatch, tmp_path):
    """§1.4 requires H7's corpus target to be FRESH but names no variable
    for it. The derived default must still be a location the environment
    chose — a constant here would be a box path in the instrument."""
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    paths = {"sensorium_e9_target": tmp_path / "t"}
    cfg = runner.e9_config(paths)
    assert cfg["corpus_target"] == tmp_path / "t-corpus"
    assert cfg["corpus_target_from_env"] is False
    monkeypatch.setenv("SENSORIUM_CORPUS_TARGET", str(tmp_path / "named"))
    cfg = runner.e9_config(paths)
    assert cfg["corpus_target"] == tmp_path / "named"
    assert cfg["corpus_target_from_env"] is True


def test_the_config_records_TMPDIR_as_observed(monkeypatch, tmp_path):
    """§1.4: `TMPDIR` is EXPECTED unset and RECORDED as observed. A config
    that assumed it was unset would build W1/W3/S1/S2 against the wrong
    prefix and report four MISSES on a correct recorder."""
    paths = {"sensorium_e9_target": tmp_path / "t"}
    monkeypatch.delenv("TMPDIR", raising=False)
    cfg = runner.e9_config(paths)
    assert cfg["tmpdir_observed"] is None and cfg["temp_root"] == "/tmp"
    monkeypatch.setenv("TMPDIR", "/scratch")
    cfg = runner.e9_config(paths)
    assert cfg["tmpdir_observed"] == "/scratch"
    assert cfg["temp_root"] == "/scratch"
    assert phases.watch_triples(cfg)[0]["expr"] == (
        'dir == "/scratch/bloomery-pager-contract"')
    assert phases.flow_sightings(cfg)[1]["literal"] == (
        "/scratch/bloomery-pager-contract2/j.jsonl")


def test_a_driver_outside_a_cargo_profile_directory_is_REFUSED(tmp_path,
                                                               monkeypatch):
    """§1.4 has the runner BUILD the driver. The profile is read from the
    binary's own parent so the build lands where `SENSORIUM_DRIVER` points;
    a path that names no profile would otherwise refresh the OTHER profile
    and report `rebuilt: False` about a stale binary — the pre-repair-binary
    trap of the E6⁗ record.

    `run` is replaced with a raise, so the refusal must happen BEFORE any
    command is issued: a check that ran cargo first and refused afterwards
    would have spent a build on a path it was going to reject, and this
    suite would no longer be box-free."""
    def no_commands(*a, **k):
        raise AssertionError("the refusal must precede every command")

    monkeypatch.setattr(runner, "run", no_commands)
    d = tmp_path / "somewhere"
    d.mkdir()
    (d / "cargo-sensorium").write_text("")
    with pytest.raises(Refused) as e:
        runner.build_driver_e9({"sensorium_driver": d / "cargo-sensorium"})
    assert "cargo profile" in str(e.value)


# -- the four runs ---------------------------------------------------------


def test_the_four_run_commands_are_exactly_ones_1_names(tmp_path):
    """The argv column of §1's run table. A `--focus` placed after the
    subcommand would be handed to cargo, and a focused run would record
    unfocused at exit 0 — the failure `parsed_focus` exists to catch."""
    p = {"sensorium_driver": tmp_path / "cargo-sensorium"}
    d = str(p["sensorium_driver"])
    assert phases.argv_of(p, "U1") == [
        d, "sensorium", "test", "-p", "bloomery-daemon",
        "--test", "pager_obligation_test"]
    assert phases.argv_of(p, "F1") == [
        d, "sensorium", "--focus", phases.FOCUS_A, "test",
        "-p", "bloomery-daemon", "--test", "pager_obligation_test"]
    assert phases.argv_of(p, "U2") == [
        d, "sensorium", "test", "-p", "bloomery-daemon",
        "--test", "pager_codec_gate_test"]
    assert phases.argv_of(p, "F2") == [
        d, "sensorium", "--focus", phases.FOCUS_B, "test",
        "-p", "bloomery-daemon", "--test", "pager_codec_gate_test"]


def test_the_recording_environment_re_adds_only_what_1_names(tmp_path):
    """§1.4 leaves `SENSORIUM_TIER` at its default and does NOT silence the
    audit log. `plain_env()` strips every `SENSORIUM_*`, so a variable put
    back here is the only way either could be set — and an inherited
    `CARGO_TARGET_DIR` would build somewhere the record does not name."""
    p = {"sensorium_e9_target": tmp_path / "t",
         "sensorium_dir": tmp_path / "s"}
    env = phases.record_env(p)
    assert env["CARGO_TARGET_DIR"] == str(tmp_path / "t")
    assert env["SENSORIUM_DIR"] == str(tmp_path / "s")
    assert "SENSORIUM_TIER" not in env
    assert "SENSORIUM_NO_INVOCATION_LOG" not in env
    assert [k for k in env if k.startswith("SENSORIUM_")] == ["SENSORIUM_DIR"]


def test_the_test_binarys_process_is_picked_by_a_stated_rule():
    """A `cargo test --test <t>` can leave more than one converted process
    behind, and every number is about the test binary. Picking silently
    would let a build script's trace answer H1's LINE count."""
    lines = [{"run": "a", "exe": "/t/debug/deps/build-script-build",
              "events": 900},
             {"run": "b", "exe": "/t/debug/deps/pager_obligation_test-9f",
              "events": 12}]
    got = phases.pick_run(lines, "pager_obligation_test")
    assert got["run"] == "b"
    assert "exe basename" in got["rule"]
    # and when no exe says so, the fallback NAMES itself
    fb = phases.pick_run(lines, "other_test")
    assert fb["run"] == "a" and fb["rule"].startswith("FALLBACK")
    assert phases.pick_run([], "x")["run"] is None


def test_a_run_line_without_a_trace_on_disk_is_a_DROP_and_not_a_crash(
        tmp_path):
    """A KILLED `cargo sensorium` can still have printed a `run:` line for a
    process the converter never finished writing, and
    `sqlite3.connect(..., mode=ro)` on a missing file RAISES — which would
    take the whole run down inside a phase and lose every endpoint already
    measured, instead of leaving a drop in the record."""
    paths = {"sensorium_dir": tmp_path / "store"}
    (tmp_path / "store" / "traces").mkdir(parents=True)
    assert phases.has_trace(paths, {"run": None}) is False
    assert phases.has_trace(paths, {"run": "20260906-x"}) is False
    (tmp_path / "store" / "traces" / "20260906-x.db").write_text("")
    assert phases.has_trace(paths, {"run": "20260906-x"}) is True


def test_the_watch_triples_and_sightings_are_ones_1_2_and_1_3_pin():
    """The predictions, spelled once. A triple whose predicted exit did not
    match its class would make H4's disagreement field meaningless."""
    cfg = {"temp_root": "/tmp"}
    ws = phases.watch_triples(cfg)
    assert [(t["id"], t["run"], t["predicted_class"], t["predicted_exit"],
             t["line"]) for t in ws] == [
        ("W1", "F1", "SATISFIED", 0, 251),
        ("W2", "F1", "NOTHING WAS CHECKED", 3, 282),
        ("W3", "F2", "not satisfied", 1, 22)]
    assert ws[1]["expr"] == "len(events) == 0"
    ss = phases.flow_sightings(cfg)
    assert [(s["id"], s["literal"], s["line"]) for s in ss] == [
        ("S1", "/tmp/bloomery-pager-contract", 251),
        ("S2", "/tmp/bloomery-pager-contract2/j.jsonl", 264)]


def test_the_expected_line_table_is_1_1s_hand_count():
    """N is 26 because §1.1 counted 26 lines. A table that had drifted from
    the count would make the gate and the diff disagree, and H3's MISS
    reading would name lines against the wrong reference."""
    assert sum(runner.EXPECTED_BY_LINE.values()) == runner.GATE_N == 26
    assert len(runner.EXPECTED_BY_LINE) == 26
    assert all(v == 1 for v in runner.EXPECTED_BY_LINE.values())
    assert min(runner.EXPECTED_BY_LINE) == 250
    assert max(runner.EXPECTED_BY_LINE) == 300
    # the two lines §1.1 deliberately does NOT count, named so a table that
    # quietly grew a row would fail here
    assert 260 not in runner.EXPECTED_BY_LINE
    assert 280 not in runner.EXPECTED_BY_LINE
    assert runner.ACCOUNTED_N == frozenset({25, 26, 27})


def test_a_kill_is_recorded_as_a_fact_and_not_raised(tmp_path, monkeypatch):
    """§1's kill criteria make a timed-out arm a recorded not-measured. A
    `TimeoutExpired` that escaped would take every later phase down with it
    and lose the endpoints already read to one slow command — and
    `acceptance_lib.run` writes its log only after the call returns, so a
    killed command otherwise leaves no evidence at all."""
    def killed(*a, **k):
        # BYTES, which is what `subprocess.run(text=True)` attaches on some
        # platforms; the branch that decodes them is the one that carried a
        # `LookupError` on a sibling runner.
        raise subprocess.TimeoutExpired(["cargo"], 3600, output=b"partial\n")

    monkeypatch.setattr(phases, "run", killed)
    monkeypatch.setattr(lib, "LOGS", tmp_path / "logs")
    res = phases.guarded(["cargo", "x"], tmp_path, "u1.log", {}, 3600, "U1")
    assert res["timed_out"] is True and res["rc"] is None
    assert res["out"] == "partial\n" and res["kill_s"] == 3600
    assert Path(res["log"]).is_file()
    assert "KILLED at 3600 s" in Path(res["log"]).read_text()


# -- the log root ----------------------------------------------------------


def test_the_runner_gives_the_phases_module_the_runs_log_root():
    """The wiring the entry slice's first detached launch died on: the
    phases open `logs_at(LOGS / "<phase>")` in the namespace they live in,
    and a front door that assigned only the shared pointers left that third
    name unset — a `NameError` fourteen seconds in, after the byte-lock and
    the preflight and before one number was measured."""
    assert phases.LOGS == runner.LOGS
    assert runner.LOGS == runner.BASE / "logs"
    # `acceptance_e6ppp.LOGS`/`BASE` are the FOURTH and FIFTH pointers —
    # `build_driver` and `logs_at` resolve them where they are defined — but
    # their runtime values belong to whichever runner was imported last at
    # collection time, so the assignment is asserted at the source rather
    # than at a value another suite owns.
    src = (REPO / "rust" / "tests" / "acceptance_e9.py").read_text()
    for assignment in ("lib.LOGS = LOGS", "ph.LOGS = LOGS",
                       "eph.LOGS = LOGS", "e6ppp.LOGS = LOGS",
                       "e6ppp.BASE = BASE"):
        assert src.count(assignment) >= 1, assignment


def test_the_phases_module_declares_the_name_and_owns_no_location():
    """The other half, where the runner's assignment cannot mask it: a FRESH
    load, with no front door to hand it a pointer. A default copied from
    `acceptance_lib.LOGS` would equal this run's root today by import order
    and silently stop doing so on any reorder."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "acceptance_e9_phases__fresh",
        REPO / "rust" / "tests" / "acceptance_e9_phases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "LOGS" in vars(mod)
    assert mod.LOGS is None


def test_no_module_of_this_instrument_names_a_box_path():
    """Every location is an environment variable. A path compiled into the
    runner would make the record unreproducible and the file wrong on any
    other machine. The only box strings allowed anywhere are this test's own
    literals."""
    for name in INSTRUMENT:
        text = (REPO / "rust" / "tests" / name).read_text()
        assert "/mnt/" not in text, name
        assert "/home/" not in text, name
