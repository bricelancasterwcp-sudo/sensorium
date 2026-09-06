"""The rung-4 entry-slice acceptance TOOLING, tested without the box.

Nothing here runs cargo or pytest, opens a kept trace store, reads anything
under `/mnt`, or needs an environment variable to be set by whoever launched
pytest. Every trace this module reads it built itself in `tmp_path`; the one
real file it opens is the COMMITTED E6⁗ `results.json`, which is the oracle
and lives in this repository.

What it tests is the places this run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock -- a lock that compared the wrong slice, that passed on a
  changed §1, or that fell through while `BYTE_LOCK` is still `None`, lets an
  endpoint move after a number is read;
* none-versus-zero -- a phase that did not run is `null` with a reason, and
  no headline may ever be filled from the oracle, which is the one number in
  the room that is already known;
* the renderer, the locations the run touches, the kill that must be recorded
  rather than raised, and each phase's log root in ITS OWN namespace.

The READER's own tests -- the shape parser, the header parser, the oracle,
the site comparison, the sqlite join and the ungated counts -- are in
`tests/test_acceptance_grain_read.py`, which mirrors the module they test.
This file crossed the 800-line ceiling at Task 5's fix round and was split
along that seam on 2026-09-05 (Task 7, fix round 2); no test moved by a
character.

Every test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_grain as runner                                  # noqa: E402
import acceptance_grain_phases as phases                           # noqa: E402
import acceptance_grain_read as read                               # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
import render_grain                                                # noqa: E402
from acceptance_grain_schema import assemble_grain                 # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

# Importing this runner re-points the SHARED log pointers at THIS document's
# workspace (its job). `tests/test_acceptance_e6q.py` and `..._e6ppp.py`
# assert the same invariant for THEIR runners and all of them are imported at
# COLLECTION time, so whichever pytest collected last would own the pointer
# and a sibling assertion would fail on collection order alone. Restoring
# E6‴'s pointers here makes every suite order-independent and costs nothing:
# each phase runs inside a `logs_at` block.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS


# -- the byte-lock on the new document -------------------------------------


def _require_lock_commits(*shas):
    """The real-document lock tests read `git show <sha>:<doc>`; a shallow
    checkout has no such commit, and before this task's last step there is no
    lock sha at all. Skip BY NAME rather than pass on a missing commit -- a
    skipped lock check must never look like a passed one."""
    import subprocess
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) -- the "
                        "byte-lock test is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) -- the byte-lock test is skipped "
                        "BY NAME, not passed")


def test_the_grain_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a stray
    edit to §1 is caught before a run is launched rather than by a refusal
    with a store already read."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True


def test_the_grain_lock_is_one_sha_and_records_no_amendment():
    """§1 of this document is committed once and never amended. A record that
    silently reported an amendment would be describing another document."""
    _require_lock_commits(runner.BYTE_LOCK)
    assert runner.ORIGINAL_LOCK is None
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    # No footnote is referenced by this §1, so the extended range and §1 are
    # the same bytes -- asserted, because a footnote added later would
    # silently widen the locked range.
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"]


def test_the_grain_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself. A check that computes two shas, reports them
    unequal and proceeds is not a lock."""
    if not runner.DOC.is_file():
        pytest.skip("the acceptance document does not exist yet (§1 is "
                    "committed ALONE by a later step) -- skipped BY NAME, "
                    "not passed")
    text = runner.DOC.read_text()
    moved = text.replace("**20 of 20 equal**", "**19 of 20 equal**", 1)
    assert moved != text, "the §1 phrase this test moves is gone"
    doc = tmp_path / "moved.md"
    doc.write_text(moved)
    with pytest.raises(Refused):
        rung3.byte_lock_check(doc, "aaaaaaa", None, lambda rel, commit: text)


def test_the_runner_REFUSES_to_measure_while_section_1_is_unlocked(
        monkeypatch):
    """The state this file is committed in: the tooling exists and §1 does
    not. A `None` lock that fell through to "no commit to compare with" would
    measure against a pre-registration that could still be edited."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked" in str(e.value)


# -- none versus zero, in the schema ---------------------------------------


def _raw(**over) -> dict:
    raw = {"runner": "rust/tests/acceptance_grain.py",
           "oracle": runner.oracle(runner.ORACLE)}
    raw.update(over)
    return raw


def test_a_phase_that_did_not_run_is_null_with_a_reason():
    """The schema's one rule. A phase absent from the raw record must reach
    the document as `not measured (<why>)`, never as a dash or a zero."""
    doc = assemble_grain(_raw())
    for key in ("H1", "H2", "H3", "H4", "H5", "H6"):
        m = doc["endpoints"][key]["headline"]
        assert m["value"] is None, key
        assert m["dropped"], key


def test_H4s_headline_is_never_filled_from_the_oracle():
    """MUTANT: the schema falling back to the oracle when the measurement is
    absent. The oracle already holds 91 sites and 782 lines; a headline that
    quietly took them would report the record as its own measurement and H4
    could not fail."""
    doc = assemble_grain(_raw())
    h4 = doc["endpoints"]["H4"]
    assert h4["headline"]["value"] is None
    assert "not measured" not in str(h4["headline"]["value"])
    for arm in ("ws", "ws0"):
        assert h4["arms"][arm]["site_differences"]["value"] is None
        assert h4["arms"][arm]["site_differences"]["dropped"]
    # ...while the oracle it was NOT allowed to borrow from is published
    # beside it, under its own name.
    assert doc["oracle"]["sites"] == {"a": 5, "ws": 91, "ws0": 98}


def test_a_measured_zero_is_a_measured_zero():
    """The other half of the rule: 0 differences is the PASS, and it must not
    read as not-measured."""
    doc = assemble_grain(_raw(raw_h2={
        "run": "r1", "rc": 0, "wall": 1.0, "groups": 5, "chains": 14,
        "compare": {"equal": True, "differences": 0, "missing": [],
                    "extra": [], "count_diffs": [], "measured_lines": 14,
                    "expected_lines": 14},
        "tally_line": "dispositions: swallowed 14, ambiguous 8",
        "tally_line_equal": True, "unresolved_sinks": 0}))
    m = doc["endpoints"]["H2"]["headline"]
    assert m["value"] == 0 and m["dropped"] == []


# -- the renderer ----------------------------------------------------------


def test_the_renderer_prints_not_measured_with_the_reason():
    """A null that rendered as a dash, an empty cell or a 0 would publish a
    phase that did not run as one that found nothing."""
    doc = assemble_grain(_raw())
    text = "\n".join(render_grain.results(doc))
    assert "not measured (" in text
    assert "| — |" not in text


def test_the_renderer_prints_a_measured_zero_as_zero():
    doc = assemble_grain(_raw(raw_h2={
        "run": "r1", "rc": 0, "wall": 1.0, "groups": 5, "chains": 14,
        "compare": {"equal": True, "differences": 0, "missing": [],
                    "extra": [], "count_diffs": [], "measured_lines": 14,
                    "expected_lines": 14},
        "tally_line": "dispositions: swallowed 14, ambiguous 8",
        "tally_line_equal": True, "unresolved_sinks": 0}))
    line = [ln for ln in render_grain.results(doc) if ln.startswith("| H2 |")]
    assert line and "| 0 (rule:" in line[0], line


# -- the locations this run touches ----------------------------------------


def test_the_four_locations_are_refused_TOGETHER_when_unset(monkeypatch):
    """One launch reports every missing variable, not one per attempt. A run
    launched with the stores set and the corpus target not would refuse only
    after H2, H3 and H4 had already read the stores."""
    for k in runner.GRAIN_ENV:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_grain()
    for k in runner.GRAIN_ENV:
        assert k in str(e.value)


def test_each_arm_reads_its_own_kept_store_and_H1_records_into_neither(
        tmp_path):
    """The kept stores are the INPUTS. An arm pointed at the wrong one would
    compare `ws0`'s traces against `ws`'s table; a corpus recording landing
    in one would change the evidence the record cites."""
    p = {"e6q_stores": tmp_path / "e6q", "sensorium_dir": tmp_path / "fresh"}
    dirs = {label: runner.store_paths(p, label)["sensorium_dir"]
            for label in ("a", "ws", "ws0")}
    assert len(set(dirs.values())) == 3
    for label, d in dirs.items():
        assert d == p["e6q_stores"] / label
        assert d != p["sensorium_dir"]


def test_a_killed_answer_is_recorded_as_a_kill_and_not_raised(
        tmp_path, monkeypatch):
    """H5's ceiling. A `TimeoutExpired` that escaped would take H1 and H6
    down with it and lose four measured endpoints to one slow answer, so the
    kill is a FACT of the record: the wall, whatever the command had printed
    before it fired, and a log of its own — `acceptance_lib.run` writes its
    log only after the call returns, so a killed command otherwise leaves no
    evidence at all."""
    import subprocess

    def killed(*a, **k):
        # BYTES, which is what `subprocess.run(text=True)` attaches on some
        # platforms -- and the branch that decodes them is the one that
        # carried the `LookupError` this test was written for.
        raise subprocess.TimeoutExpired(["sensorium"], 60,
                                        output=b"partial\n")

    # Patched on the PHASES module, not on the front door: `acceptance_grain`
    # re-exports `_ask` by NAME, and `_ask` resolves `sensorium_cli` in the
    # namespace it was defined in. Patching the re-export would leave the
    # real command in place -- the same lesson as E6‴ §2's `logs_at`.
    monkeypatch.setattr(phases, "sensorium_cli", killed)
    monkeypatch.setattr(lib, "LOGS", tmp_path / "logs")
    p = {"e6q_stores": tmp_path / "e6q", "sensorium_dir": tmp_path / "fresh"}
    res = runner._ask(p, "ws", "inv", {"limit": 10, "cli_timeout": 99},
                      "h4-ws", kill=60)
    assert res["timed_out"] is True
    assert res["rc"] is None
    assert res["out"] == "partial\n"
    assert res["stdout_bytes"] == 8
    assert Path(res["log"]).is_file()
    assert "KILLED at 60 s" in Path(res["log"]).read_text()


def test_no_module_of_this_instrument_names_a_box_path():
    """Every location is an environment variable. A path compiled into the
    runner would make the record unreproducible and the file wrong on any
    other machine."""
    for name in ("acceptance_grain.py", "acceptance_grain_read.py",
                 "acceptance_grain_phases.py", "acceptance_grain_schema.py",
                 "render_grain.py"):
        text = (REPO / "rust" / "tests" / name).read_text()
        assert "/mnt/" not in text, name
        assert "/home/" not in text, name

# -- fix round 1: the record must survive being written --------------------


def test_the_whole_raw_record_and_the_assembled_document_serialise():
    """The round trip the runner's LAST act depends on.

    `oracle()`'s per-arm tables are keyed by `(file, line)` TUPLES, and
    `json.dumps` cannot write a tuple KEY at all -- `default=` applies to
    values only, so nothing rescues it. Storing them raw made the raw-json
    write raise `TypeError` after an hour of measurement, losing the record,
    the `results.json` AND both markers. `oracle_json` is what the runner
    stores, and this asserts the whole shape goes out and comes back."""
    raw = {"runner": "rust/tests/acceptance_grain.py",
           "oracle": runner.oracle_json(runner.oracle(runner.ORACLE)),
           "config": {"oracle_record": "x", "oracle_commit": "y"},
           "pins": {}, "cleanup": {}}
    text = json.dumps(raw, indent=2, default=str)
    assert json.loads(text)["oracle"]["ws"], "the ws site table is empty"
    doc = assemble_grain(raw)
    back = json.loads(json.dumps(doc, indent=2, default=str))
    assert back["oracle"]["sites"] == {"a": 5, "ws": 91, "ws0": 98}


def test_the_oracles_site_tables_are_stringified_and_keep_every_count():
    """`"<file>:<line>"`, and the same multiset. A projection that lost a
    site or merged two would move H2's and H4's expected tables."""
    orc = runner.oracle(runner.ORACLE)
    js = runner.oracle_json(orc)
    for arm in ("a", "ws", "ws0"):
        assert all(isinstance(k, str) for k in js[arm]), arm
        assert len(js[arm]) == len(orc[arm]), arm
        assert sum(js[arm].values()) == sum(orc[arm].values()), arm
    assert js["ws"][
        "/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-core/src/"
        "geometry.rs:192"] > 0


def test_a_record_with_one_unwritable_value_still_writes_the_rest():
    """The fallback the guarded write uses. A run that measured for an hour
    must lose the one value a serialisation defect touched, not all of them,
    and a reader must be told which key went."""
    text = runner._partial_json({"started": "t", "bad": {("a", 1): 2},
                                 "steps": ["one"]})
    got = json.loads(text)
    assert got["started"] == "t" and got["steps"] == ["one"]
    assert got["keys_that_could_not_be_serialised"] == ["bad"]
    assert "bad" not in got


# -- fix round 2: every phase's log root exists in ITS OWN namespace --------


def test_the_runner_gives_the_phases_module_the_run_s_log_root():
    """The wiring the first launch of 2026-09-05 died on.

    Fix round 1 moved the five phases out of `acceptance_grain.py` into
    `acceptance_grain_phases.py`, and each one opens `logs_at(LOGS /
    "<phase>")` in the namespace it now lives in. The front door assigned
    `acceptance_lib.LOGS` and `acceptance_phases.LOGS` and not that third
    pointer, so H2 raised `NameError: name 'LOGS' is not defined` fourteen
    seconds into a detached run -- after the byte-lock, the preflight and the
    oracle, and before one number was measured. This asserts the assignment
    the runner makes, not the default the module carries."""
    assert phases.LOGS == runner.LOGS
    assert runner.LOGS == runner.BASE / "logs"


def test_phase_h2_opens_its_log_directory_under_that_root(tmp_path, monkeypatch):
    """...and the phase actually RUNS with it: `monkeypatch.setattr` refuses
    a name the module does not define, and `logs_at` is the first statement
    inside every phase, so this is the crash reproduced end to end with the
    two box-touching calls stubbed out."""
    answer = ("raised (1):\n"
              "  e1 HANDLED f handled io::Error('x') L156\n"
              "    SWALLOWED -- absorbed by sink_ok at e1 (f L156) in f1, "
              "which returned ok\n"
              "dispositions: swallowed 1\n")
    monkeypatch.setattr(phases, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(phases, "_ask", lambda *a, **k: {
        "rc": 0, "out": answer, "err": "", "wall": 0.01,
        "log": str(tmp_path / "logs" / "h2" / "cli-h2-a.log"),
        "command": "sensorium exceptions <run> --limit 100000",
        "timed_out": False, "stdout_bytes": len(answer),
        "stdout_lines": len(answer.splitlines())})
    monkeypatch.setattr(phases, "measure_sites", lambda *a, **k: {
        "sites": Counter({("/w/memory.rs", 156): 1}), "groups": 1,
        "chains": 1, "unresolved_count": 0, "unresolved": [],
        "runs_named": {"20260905-091115-5da3dc"}})
    orc = {"a": Counter({("/w/memory.rs", 156): 1}),
           "per_process": {"a": {"20260905-091115-5da3dc":
                                 "dispositions: swallowed 1"}}}
    out = phases.phase_h2({"e6q_stores": tmp_path / "e6q",
                           "sensorium_dir": tmp_path / "fresh"},
                          {"limit": 100000, "cli_timeout": 99}, orc)
    assert (tmp_path / "logs" / "h2").is_dir()
    assert out["groups"] == 1 and out["chains"] == 1
    assert out["tally_line_equal"] is True
    assert out["compare"]["differences"] == 0


def test_the_phases_module_declares_the_name_and_owns_no_location():
    """The other half, tested where the runner's assignment cannot mask it: a
    FRESH load of the module, with no front door to hand it a pointer.

    The name must EXIST (a module that defined it nowhere would still look
    wired inside this suite, because importing `acceptance_grain` creates the
    attribute) and must hold no location: a default copied from
    `acceptance_lib.LOGS` would equal this run's root today, by the order the
    front door happens to import in, and would silently stop doing so on any
    reorder -- writing an hour of evidence somewhere plausible and wrong."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "acceptance_grain_phases__fresh",
        REPO / "rust" / "tests" / "acceptance_grain_phases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "LOGS" in vars(mod)
    assert mod.LOGS is None


# -- fix round 1 of the RECORD: the zero-fill is where the document is
# -- derived ----------------------------------------------------------------


def test_assembling_an_old_raw_record_zero_fills_the_vary_count(tmp_path):
    """The RAW record is evidence and is never rewritten, so the zero-fill
    has to happen where the document is derived. A raw `reported` recorded
    before this fix -- exactly the one this slice measured -- must assemble
    with `details: 0`, and with every other number untouched."""
    raw = {"raw_reported": {"vary_lines_by_kind": {"messages": 152,
                                                   "origins": 38,
                                                   "routes": 38},
                            "vary_counted_over": ["H2"],
                            "busiest_ws_process": {"run": "r"}}}
    doc = assemble_grain(raw)
    assert doc["reported"]["vary_lines_by_kind"] == {
        "messages": 152, "origins": 38, "routes": 38, "details": 0}
    # nothing else in the block moved
    assert doc["reported"]["busiest_ws_process"] == {"run": "r"}
    assert doc["reported"]["vary_counted_over"] == ["H2"]
