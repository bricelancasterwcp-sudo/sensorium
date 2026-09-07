"""The E4 PASS PROTOCOLS, tested without the box.

Split out of `tests/test_acceptance_e4.py` at that file's 800-line ceiling,
along the seam the material has: the lock, §1.1's table, the locations and the
log roots are the RUNNER's, and what each pass RECORDS -- the store pair
versus the printed id, the licence counts, the verdict word beside its exit,
a second converted process, and the discriminator's SCOPE -- is the phases'.

Nothing here runs a command: `phases.guarded` is monkeypatched to return a
canned answer in the shape the real commands print, and `pair_candidates`,
`has_trace` and `discriminate` are monkeypatched so no `.db` is opened.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4_phases as phases                              # noqa: E402
import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402

# The same collection-order restore the sibling suites make.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS


# -- what each pass records ------------------------------------------------


_CANNED_MATCH = "\n".join([
    "refocus-of: orig-1   cmd: <driver> --refocus-of orig-1",
    "cwd: /clone", "focus: a_test   window: -",
    "source: unchanged (3 file(s) compared by content)",
    "--- rerunning (the driver's build output is above and below; the lines "
    "below are its own) ---",
    "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered "
    "out; finished in 0.02s",
    "--- verdict ---", "run: PRINTED-ID", "trace: /store/traces/x.db",
    "env: unchanged (9 variables compared; not compared: PWD)",
    "exit: rerun 0   original 0",
    "refocus verdict: MATCH -- every recorded thread produced the identical "
    "CALL/RETURN/RAISE/HANDLED sequence",
    "licence: verified against orig-1 on exactly these points, and no "
    "others:",
    "  - identical call shape across 1 compared fingerprint(s), holding 4 "
    "causal event(s)",
    "checks that could not run on this pair -- the recorder declares it does "
    "not produce them, so nothing here is evidence either way:",
    "  - output: unverifiable (not recorded)",
    "  - children: unverifiable (not witnessed)",
])


def _canned(out: str, err: str = ""):
    def guarded(cmd, _cwd, _log, _env, timeout, _tag):
        return {"rc": 0, "out": out, "err": err, "wall": 1.0,
                "log": "<log>", "timed_out": False, "kill_s": timeout,
                "command": " ".join(str(c) for c in cmd)}
    return guarded


def test_a_refocus_record_keeps_the_STORE_pair_and_the_licence_COUNTS(
        monkeypatch, tmp_path):
    """Two facts the record must not let the PRINTED answer overwrite.

    `new_run` is the store's answer under §1.4's pair rule -- "the driver's
    `run:` lines are recorded in the report and decide nothing" -- and the
    printed id rides beside it as a cross-check. `licence` is the four
    COUNTS H4 reads; the printed word is one field inside them. A record
    built by splicing the whole parse over the measured facts would replace
    both with the printed values, and H4 would then read a string where it
    expects a mapping."""
    monkeypatch.setattr(phases, "guarded", _canned(_CANNED_MATCH))
    monkeypatch.setattr(phases, "pair_candidates",
                        lambda _d, run, at: {"linked": ["STORE-ID"],
                                             "qualifying": ["STORE-ID"],
                                             "unreadable": [], "n": 1,
                                             "launched_at": at})
    monkeypatch.setattr(phases, "has_trace", lambda _p, _r: False)
    paths = {"sensorium_dir": tmp_path, "sensorium_driver": tmp_path / "d",
             "sensorium_e4_target": tmp_path / "t"}
    got = phases.refocus_one(paths, {"tests": [1], "refocus_timeout": 1800},
                             {"index": 1, "name": "a_test",
                              "target": "pager_test", "run": "orig-1"})
    assert got["new_run"] == "STORE-ID"
    assert got["printed_new_run"] == "PRINTED-ID"
    assert got["pair_agrees_with_the_printed_id"] is False
    assert isinstance(got["licence"], dict)
    assert got["licence"]["licence"] == "granted"
    assert got["licence"]["output_unverifiable"] is True
    assert got["licence"]["verified_facts"] == 1
    # the verdict word and the exit are read separately, never derived
    assert got["verdict_word"] == "MATCH" and got["rc"] == 0
    assert got["verdict_and_exit_agree"] is True
    assert got["child_launched"] is True


def test_a_verdict_word_that_disagrees_with_its_exit_is_a_recorded_finding(
        monkeypatch, tmp_path):
    """§1's H3 second reading. Neither is derived from the other, so a
    MATCH returned at exit 1 is visible instead of being silently resolved
    in favour of the friendlier one."""
    def guarded(cmd, _cwd, _log, _env, timeout, _tag):
        return {"rc": 1, "out": _CANNED_MATCH, "err": "", "wall": 1.0,
                "log": "<log>", "timed_out": False, "kill_s": timeout,
                "command": " ".join(str(c) for c in cmd)}
    monkeypatch.setattr(phases, "guarded", guarded)
    monkeypatch.setattr(phases, "pair_candidates",
                        lambda _d, _r, at: {"linked": [], "qualifying": [],
                                            "unreadable": [], "n": 0,
                                            "launched_at": at})
    monkeypatch.setattr(phases, "has_trace", lambda _p, _r: False)
    paths = {"sensorium_dir": tmp_path, "sensorium_driver": tmp_path / "d",
             "sensorium_e4_target": tmp_path / "t"}
    got = phases.refocus_one(paths, {"tests": [1], "refocus_timeout": 1800},
                             {"index": 1, "name": "a_test",
                              "target": "pager_test", "run": "orig-1"})
    assert got["verdict_word"] == "MATCH" and got["rc"] == 1
    assert got["verdict_and_exit_agree"] is False
    # and zero qualifying traces is a REFUSED BY COUNT, never a guess
    assert got["new_run"] is None
    assert "needs exactly one" in got["pair_refusal"]


def test_more_than_one_process_is_a_recorded_fact_not_a_pick(monkeypatch,
                                                             tmp_path):
    """§2.3's `invocation_processes` refusal needs a single-target
    invocation, and `--test <file>` is one. If a pass-1 invocation ever
    leaves two converted processes, which trace pass 2 refocused would be a
    guess -- so the runner records the fact and takes no run id at all."""
    two_lines = ("run: a  pid: 1  exe: /x/a  events: 3  threads: 1  exit: 0\n"
                 "run: b  pid: 2  exe: /x/b  events: 5  threads: 1  exit: 0\n")
    monkeypatch.setattr(phases, "guarded", _canned(two_lines))
    monkeypatch.setattr(phases, "has_trace", lambda _p, _r: False)
    paths = {"sensorium_dir": tmp_path, "sensorium_driver": tmp_path / "d",
             "sensorium_e4_target": tmp_path / "t",
             "sensorium_bloomery": tmp_path / "clone"}
    got = phases.record_one(paths, {"tests": [1], "cargo_timeout": 1800},
                            1, "pager_test", "a_test")
    assert got["processes"] == 2 and got["multi_process"] is True
    assert got["run"] is None
    assert got["run_candidates"] == ["a", "b"]


# -- the discriminator's SCOPE ---------------------------------------------


def test_the_discriminator_is_NEVER_asked_about_a_test_1_2_did_not_name(
        monkeypatch, tmp_path):
    """§1.2 pre-registers an explanation for a DIVERGED on THREE tests and
    for no others. `_classify` must decide that from the name alone, before
    any arithmetic: a scope that let every test through would publish a
    DIVERGED on, say, `a_pager_can_be_shared_across_threads` -- whose one
    spawned thread trivially preserves its own total and leaves MAIN equal --
    as `H3.named_hazard` instead of `H3.findings`, which is the exact
    inversion R-H1's amendment forbids.

    `discriminate` is monkeypatched to FAIL, so the test proves the
    arithmetic is never reached rather than that it happened to agree."""
    monkeypatch.setattr(
        phases, "discriminate",
        lambda *_a, **_k: pytest.fail("the discriminator was applied to a "
                                      "test §1.2 does not name"))
    (tmp_path / "traces").mkdir()
    paths = {"sensorium_dir": tmp_path}
    got = phases._classify(paths, {"name": "a_pager_can_be_shared_across_"
                                           "threads",
                                   "original": "orig-1", "new_run": "new-1"})
    assert got["class"] == "finding"
    assert got["is_a_pre_registered_hazard_test"] is False
    assert "§1.2 pre-registers no explanation" in got["reading"]


def test_the_three_named_tests_DO_reach_the_discriminator(monkeypatch,
                                                          tmp_path):
    """The other half: a scope that let nothing through would report every
    DIVERGED as a finding and §1.4's amendment would never fire. Both
    traces must be on disk for the arithmetic to run at all."""
    from acceptance_e4_read import HAZARD_TESTS
    traces = tmp_path / "traces"
    traces.mkdir()
    for name in ("orig-1.db", "new-1.db"):
        (traces / name).write_bytes(b"")
    seen = []
    monkeypatch.setattr(phases, "discriminate",
                        lambda a, b, n: seen.append(n) or {"class": "hazard"})
    got = phases._classify({"sensorium_dir": tmp_path},
                           {"name": HAZARD_TESTS[0], "original": "orig-1",
                            "new_run": "new-1"})
    assert seen == [HAZARD_TESTS[0]]
    assert got["class"] == "hazard"


# -- the build-failure STOP names its ambiguity ----------------------------


def test_the_build_failure_STOP_says_what_its_class_cannot_tell_apart():
    """§1's kill 1 is a focused COMPILE failure. What the instrument can
    actually observe -- no libtest summary and a non-zero exit -- also
    covers a driver or converter failure on the way to one, which is NOT
    the finding §1 means. The class stays; the ambiguity is published
    beside it with the child's own exit and the log that settles it, so §3
    cannot read `compile failure` off a class that covers two things."""
    one = {"by_name": {"a": {"outcome": None, "summary_lines": []}}}
    two = {"refocuses": [{"name": "a", "target": "f", "child_launched": True,
                          "summary_lines": [], "outcome": None, "rc": 3,
                          "driver_exit": 101, "timed_out": False,
                          "log": "<ledger>/logs/pass2/p2-01-a.log"}],
           "killed": []}
    got = phases.phase_h2(one, two)
    assert got["build_failures"] == ["a"]
    caveat = got["build_failure_caveat"]
    assert "COMPILE failure" in caveat and "driver/converter" in caveat
    assert "101" in caveat and "p2-01-a.log" in caveat
    # the per-test caveat names THAT test's own exit and log; the phase-level
    # one names them per failing test, so the two are not the same string
    per = got["per_test"][0]["build_failure_caveat"]
    assert "driver_exit = 101" in per and "p2-01-a.log" in per
    assert "'a': 101" in caveat
    # a run with no build failure carries no caveat at all
    two["refocuses"][0]["summary_lines"] = ["test result: ok. 1 passed;"]
    assert phases.phase_h2(one, two)["build_failure_caveat"] is None

