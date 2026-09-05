"""The grain-REPAIR runner, tested without the box.

Nothing here runs cargo or pytest, opens a kept trace store, reads anything
under `/mnt`, or needs an environment variable. The parsers, the oracle, the
site comparison and the schema are `acceptance_grain`'s and are tested in
`tests/test_acceptance_grain.py`; this file tests the only two things that
are new:

* the §1 byte-lock on the REPAIR document -- the first record's H4 was a
  STOP, and a repair whose pre-registration could still be edited after a
  number was read would be worth nothing at all;
* that this runner IS the first one. The whole claim of a sibling is that the
  instrument did not change while the document did, so every name the two
  modules share must be the SAME OBJECT, and the ones that differ must be
  exactly the document, the lock, the paths and the markers -- the list the
  sibling itself publishes as `OVERRIDES`.

Every test states the failure it would catch. The mutations run against them
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
import acceptance_grain as grain                                   # noqa: E402
import acceptance_grain_phases as gph                              # noqa: E402
import acceptance_grain_repair as runner                           # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

# Importing either grain runner re-points the SHARED log pointers at ITS
# document's workspace (their job), and all of them are imported at
# COLLECTION time, so whichever pytest collected last would own the pointer.
# `tests/test_acceptance_grain.py` restores E6‴'s pointers for exactly this
# reason; this file does the same, so no suite depends on collection order.
# The repair runner's `main` re-asserts its own pointers before any phase.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS
gph.LOGS = grain.LOGS


# -- the byte-lock on the repair document ----------------------------------


def _require_lock_commits(*shas):
    """The real-document lock tests read `git show <sha>:<doc>`; a shallow
    checkout has no such commit, and before this task's last step there is no
    lock sha at all. Skip BY NAME rather than pass on a missing commit -- a
    skipped lock check must never look like a passed one."""
    for sha in shas:
        if not sha:
            pytest.skip("§1′ is not locked yet (BYTE_LOCK is None) -- the "
                        "byte-lock test is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) -- the byte-lock test is skipped "
                        "BY NAME, not passed")


def test_the_repair_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a stray
    edit to §1′ is caught before a run is launched rather than by a refusal
    with a store already read."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True


def test_the_repair_lock_is_one_sha_and_records_no_amendment():
    """§1′ is committed once and never amended. A record that silently
    reported an amendment would be describing another document."""
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


def test_the_repair_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself. A check that computes two shas, reports them
    unequal and proceeds is not a lock."""
    if not runner.DOC.is_file():
        pytest.skip("the repair acceptance document does not exist yet (§1′ "
                    "is committed ALONE by a later step) -- skipped BY NAME, "
                    "not passed")
    text = runner.DOC.read_text()
    moved = text.replace("**20 of 20 equal**", "**19 of 20 equal**", 1)
    assert moved != text, "the §1′ phrase this test moves is gone"
    doc = tmp_path / "moved.md"
    doc.write_text(moved)
    with pytest.raises(Refused):
        rung3.byte_lock_check(doc, "aaaaaaa", None, lambda rel, commit: text)


def test_the_repair_runner_REFUSES_to_measure_while_section_1_is_unlocked(
        monkeypatch):
    """The state this runner is committed in: the tooling exists and §1′ does
    not. A `None` lock that fell through to "no commit to compare with" would
    measure against a pre-registration that could still be edited."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked" in str(e.value)


def test_the_repair_runner_checks_ITS_OWN_lock_and_not_the_first_record_s():
    """The failure this catches is the one that makes a sibling worthless: a
    `check_byte_lock` that read `acceptance_grain.BYTE_LOCK` would compare
    the FIRST record's §1 -- locked, unchanged and irrelevant -- and pass
    while §1′ was still being written."""
    assert runner.DOC != grain.DOC
    assert runner.BYTE_LOCK != grain.BYTE_LOCK or runner.BYTE_LOCK is None
    assert runner.check_byte_lock is not grain.check_byte_lock
    # `check_byte_lock` reads the module global, so patching it must move
    # what the check compares.
    src = runner.check_byte_lock.__code__.co_names
    assert "BYTE_LOCK" in src and "DOC" in src, src


# -- the sibling IS the first runner ---------------------------------------


def _public(mod) -> dict:
    """The module's own public names, minus the modules it imported: two
    runners importing `json` is not a difference between them."""
    import types
    return {k: v for k, v in vars(mod).items()
            if not k.startswith("_") and not isinstance(v, types.ModuleType)}


def test_the_sibling_shares_every_name_it_does_not_declare_an_override_for():
    """The whole claim of a sibling runner, checked. If a phase, the oracle,
    the preflight, the config or the kill ceiling were re-implemented here,
    the repair would be measured by a DIFFERENT instrument than the STOP it
    repairs, and the two records could not be read against each other."""
    mine, theirs = _public(runner), _public(grain)
    shared = set(mine) & set(theirs)
    differ = sorted(k for k in shared if mine[k] is not theirs[k])
    assert differ == sorted(k for k in runner.OVERRIDES if k in shared), differ
    # and nothing was invented that the first runner does not have, beyond
    # the declared overrides
    extra = sorted(set(mine) - set(theirs))
    assert set(extra) <= set(runner.OVERRIDES), extra


def test_every_override_is_the_document_the_lock_a_path_or_a_marker():
    """The overrides are allowed to exist; they are not allowed to be
    anything else. A sibling that quietly overrode `ARMS`, `KILL_S` or the
    oracle would still pass the test above."""
    allowed = {"DOC", "BYTE_LOCK", "BASE", "LOGS", "RESULTS", "RAW",
               "MARKER_DONE", "MARKER_FAILED", "RUNNER", "OVERRIDES",
               "grain_config", "check_byte_lock", "main", "assemble_only",
               "render_only"}
    assert set(runner.OVERRIDES) == allowed
    # the shared instrument's own settings are untouched
    for name in ("ARMS", "KILL_S", "ORACLE", "ORACLE_COMMIT", "GRAIN_ENV",
                 "DRIVER_VERSION", "LEDGER", "REPO", "PLAN"):
        assert getattr(runner, name) is getattr(grain, name), name


def test_this_run_writes_nowhere_the_first_record_s_evidence_lives():
    """A repair that overwrote the STOP it repairs would destroy the only
    record of the defect. Every path this runner writes carries
    `grain-repair` or sits under `acceptance-grain-repair/`."""
    assert runner.BASE == grain.PLAN / "acceptance-grain-repair"
    assert runner.LOGS == runner.BASE / "logs"
    assert runner.BASE != grain.BASE and runner.LOGS != grain.LOGS
    assert runner.RESULTS != grain.RESULTS
    assert "grain-repair" in runner.RESULTS.name
    assert "grain-repair" in runner.RAW
    assert runner.MARKER_DONE == "grain-repair.DONE"
    assert runner.MARKER_FAILED == "grain-repair.FAILED"
    assert runner.RUNNER == "rust/tests/acceptance_grain_repair.py"
    # the marker names are the ones `main` actually writes, not two spellings
    assert {"MARKER_DONE", "MARKER_FAILED", "RAW", "RUNNER"} <= set(
        runner.main.__code__.co_names)


def test_the_config_differs_only_in_the_workdir_that_is_a_ledger_path(
        tmp_path):
    """H1 copies twenty corpus cases into `cfg["e6_workdir"]`, and the first
    runner's `grain_config` reads ITS OWN module's `LOGS` for that path --
    module globals resolve where a function was defined. Unwrapped, this run
    would fill the first record's evidence directory with its own cases."""
    paths = {"corpus_target_env": tmp_path / "target",
             "sensorium_driver": tmp_path / "drv",
             "sensorium_dir": tmp_path / "sdir",
             "e6q_stores": tmp_path / "stores",
             "rust_target": tmp_path / "rt"}
    mine, theirs = runner.grain_config(paths), grain.grain_config(paths)
    assert mine["e6_workdir"] == runner.LOGS / "e6-cases"
    assert theirs["e6_workdir"] == grain.LOGS / "e6-cases"
    assert {k: v for k, v in mine.items() if k != "e6_workdir"} == {
        k: v for k, v in theirs.items() if k != "e6_workdir"}


def test_the_sibling_produces_the_first_record_s_schema(monkeypatch,
                                                        tmp_path):
    """§2-§5 of the repair document are rendered by the same code that
    rendered the first record's, from a record with the SAME SHAPE -- so the
    two are readable against each other line for line. A sibling that
    assembled its own shape would make that comparison a re-reading.

    Assembled here rather than compared by inspection: both runners are given
    one raw record and their two `results.json` must agree everywhere except
    the four provenance fields that are supposed to differ.
    """
    import json
    raw = {"runner": runner.RUNNER, "oracle": grain.oracle(grain.ORACLE)}
    monkeypatch.setattr(runner, "RESULTS", tmp_path / "repair.json")
    monkeypatch.setattr(grain, "RESULTS", tmp_path / "first.json")
    assert runner.assemble_only(raw) == 0
    assert grain.assemble_only(raw) == 0
    mine = json.loads((tmp_path / "repair.json").read_text())
    theirs = json.loads((tmp_path / "first.json").read_text())
    assert set(mine) == set(theirs)
    assert mine["endpoints"] == theirs["endpoints"]
    assert set(mine["assembled"]) == set(theirs["assembled"])
    # ... and the provenance says which run wrote it, so two records on one
    # disk can never be mistaken for each other
    assert mine["assembled"]["from"] == runner.RAW
    assert mine["assembled"]["by"].startswith(runner.RUNNER)
    assert mine["assembled"]["from"] != theirs["assembled"]["from"]
