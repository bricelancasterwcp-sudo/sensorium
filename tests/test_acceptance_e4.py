"""The E4 acceptance TOOLING, tested without the box.

Nothing here runs cargo, the driver or the query CLI, opens the clone, reads
anything under `/mnt`, or needs an environment variable to be set by whoever
launched pytest. The only real files it opens are this repository's own: the
acceptance document (for the byte-lock) and the instrument's modules (for the
path scan).

What it tests is the places an E4 run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock — a lock that compared the wrong slice, that passed on a
  changed §1, or that fell through while `BYTE_LOCK` is `None`, lets an
  endpoint move after a number is read;
* §1.1's table, derived from the LOCKED document and asserted equal to the
  instrument's constant — the 61 argv lines pass 1 runs come from that
  constant, so a row that drifted would run 61 commands about something else;
* the two argv forms and the two environments, which are what makes pass 2 a
  re-run of pass 1's original rather than a fresh recording;
* the locations the run touches, each one an environment variable, refused
  together when missing and refused when a fresh one is not fresh;
* the 2-hour bound, which must be a recorded not-run rather than a silently
  shortened pass;
* each phases module's log root in ITS OWN namespace — the wiring the entry
  slice's first launch died on.

The parsers and the sqlite reads are in `tests/test_acceptance_e4_read.py`;
the schema and the renderer are in `tests/test_acceptance_e4_record.py`.

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

import acceptance_e4 as runner                                     # noqa: E402
import acceptance_e4_phases as phases                              # noqa: E402
import acceptance_e4_phases2 as phases2                            # noqa: E402
import acceptance_e6ppp as e6ppp                                   # noqa: E402
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

#: The locked range's sha256 at the AMENDED lock (`413f601`) -- what the
#: runner refuses on -- and at the ORIGINAL lock (`8e7d837`), carried beside
#: it so the amendment is a checkable fact rather than a claim.
DOC_SHA = "09d2f8da30f6e216fb07e97c27481d35d0c285e40c2bccb9295e0ef07863ff42"
ORIGINAL_DOC_SHA = ("87abc779ea3acf867e07a0055d92de6281b4fd5571aaadb489"
                    "98ac7d9afe18c4")

INSTRUMENT = ("acceptance_e4.py", "acceptance_e4_cells.py",
              "acceptance_e4_phases.py", "acceptance_e4_phases2.py",
              "acceptance_e4_read.py", "acceptance_e4_schema.py",
              "acceptance_e4_tests.py", "render_e4.py")


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


def test_the_runner_carries_BOTH_locks():
    """The two facts the whole pre-registration hangs on.

    `BYTE_LOCK` is what the runner refuses on -- the AMENDED §1, whose lens
    states the survey's scope and gives §1.2's three-test hazard its
    discriminator (R-H1). `ORIGINAL_LOCK` is Task 0's commit, before the
    instrument existed. Both are carried so the amendment is visible in the
    record; a runner that dropped the original would make a post-lock edit
    indistinguishable from no edit at all, and one that refused on the
    original would refuse on the document as it now stands."""
    assert runner.BYTE_LOCK == "413f601"
    assert runner.ORIGINAL_LOCK == "8e7d837"
    assert runner.BYTE_LOCK != runner.ORIGINAL_LOCK


def test_the_e4_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a
    stray edit to §1 is caught before a run is launched rather than by a
    refusal with a clone already built."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_sha256"] == DOC_SHA


def test_the_e4_record_carries_both_shas_and_the_amendment_flag():
    """§1 was amended after the original lock and before the instrument
    existed. The record must say so with two shas and a flag: a record that
    reported no amendment would be describing another document, and one
    that reported only the amended sha would leave a reader unable to check
    that nothing but the lens moved."""
    _require_lock_commits(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["locked_sha256"] == DOC_SHA
    assert rec["original_lock_sha256"] == ORIGINAL_DOC_SHA
    assert rec["amended_after_the_original_lock"] is True
    assert rec["amendment_bytes"] > 0


def _section1(sha) -> str:
    rel = runner.DOC.relative_to(REPO).as_posix()
    text = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                          capture_output=True, text=True).stdout
    return rung3.section1(text)


def test_the_amendment_moved_no_ROW_of_the_pre_registration():
    """The claim the record makes in prose, checked mechanically: no
    endpoint, method, derivation or table row moved. Every `|` row of §1 --
    the H-table, §1.1's 61 rows, §1.2's survey and §1.3's three triples --
    must be byte-identical at the two commits. A lens amendment that also
    edited a row would be an endpoint moving after the lock."""
    _require_lock_commits(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    rows = {sha: [ln for ln in _section1(sha).splitlines()
                  if ln.startswith("|")]
            for sha in (runner.ORIGINAL_LOCK, runner.BYTE_LOCK)}
    a, b = rows[runner.ORIGINAL_LOCK], rows[runner.BYTE_LOCK]
    assert a == b
    assert len(a) > 50, "the row scan found almost nothing to compare"


def test_the_amendment_ADDS_and_removes_nothing():
    """The other half: the amendment is an addition. A line the original
    §1 carried and the amended one does not would be a deletion inside the
    locked range, which no lens amendment may make."""
    _require_lock_commits(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    before = _section1(runner.ORIGINAL_LOCK).splitlines()
    after = _section1(runner.BYTE_LOCK).splitlines()
    assert after[:len(before) - 1] == before[:-1], "a line before the "\
        "amendment moved"
    added = [ln for ln in after if ln not in before]
    assert added, "the amendment added nothing"
    assert any("Amended 2026-09-07" in ln for ln in added)
    assert any("discriminator" in ln.lower() for ln in added)


def test_the_e4_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """A lock that passed on a changed §1 would be no lock. The comparison
    is run against a doctored working copy so the failure is exercised
    rather than assumed."""
    doc = tmp_path / "e4.md"
    doc.write_text(runner.DOC.read_text().replace(
        "**The expected-MATCH list is all 61**",
        "**The expected-MATCH list is all 60**", 1))
    with pytest.raises(Refused) as e:
        rung3.byte_lock_check(doc, runner.BYTE_LOCK, runner.ORIGINAL_LOCK,
                              read_committed=lambda _rel, _c:
                              runner.DOC.read_text())
    assert "differs from the byte-lock" in str(e.value)


def test_an_unset_lock_REFUSES_rather_than_measuring(monkeypatch):
    """A pre-registration that can still be edited is not one. The runner
    refuses outright rather than measuring against it."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked yet" in str(e.value)


# -- §1.1's table ----------------------------------------------------------


def _table_from_the_locked_document() -> list[tuple]:
    """§1.1's enumeration, read out of the document itself.

    The `### 1.1` … `### 1.2` slice, then the `**<file>.rs — <n>**` headers
    and the `| <line> | \\`<name>\\` |` rows under each. The header row and
    the survey tables of §1.2 do not match, because neither is inside the
    slice and neither has a bare number in its first cell.
    """
    import re
    text, keep, buf = runner.DOC.read_text(), False, []
    for line in text.splitlines():
        if line.startswith("### 1.1"):
            keep = True
        elif line.startswith("### 1.2"):
            break
        if keep:
            buf.append(line)
    rows, current = [], None
    for line in buf:
        m = re.match(r"^\*\*`([a-z_]+\.rs)` — (\d+)\*\*$", line)
        if m:
            current = m.group(1)
            continue
        m = re.match(r"^\| (\d+) \| `([A-Za-z0-9_]+)` \|\s*$", line)
        if m and current:
            rows.append((current[:-3], int(m.group(1)), m.group(2)))
    return rows


def test_the_61_test_table_IS_1_1s_table_row_for_row():
    """The 61 argv lines pass 1 runs are built from this constant, and pass
    2 refocuses each original under the same name. A constant retyped from
    prose can drift by one row and still count 61 -- a `403 -> 430` typo
    would refuse a clone that is exactly right, and a swapped name would run
    a test §1.1 never enumerated under a name it did.

    So the table is DERIVED from the byte-locked document here and asserted
    equal to the instrument's constant. The runner keeps the constant (it
    must not parse prose at run time, and the lock is what makes the
    constant trustworthy); this is the pin between them."""
    _require_lock_commits(runner.BYTE_LOCK)
    from_doc = _table_from_the_locked_document()
    assert len(from_doc) == 61, len(from_doc)
    assert from_doc == list(runner.TESTS)
    assert runner.GATE_N == 61
    assert len(runner.TARGETS) == 7


def test_the_derived_table_actually_reads_the_document():
    """The pin above is only worth anything if the derivation can fail. A
    regex that matched nothing would make `from_doc == TESTS` an assertion
    about two empty lists."""
    from_doc = _table_from_the_locked_document()
    assert from_doc, "the §1.1 slice yielded no rows"
    from collections import Counter
    counts = Counter(f for f, _ln, _n in from_doc)
    assert counts == {"pager_codec_gate_test": 20, "pager_obligation_test": 15,
                      "pager_refusal_advice_test": 4,
                      "pager_remove_agent_test": 4,
                      "pager_reservation_test": 8, "pager_test": 4,
                      "pager_weights_test": 6}
    assert len({n for _f, _l, n in from_doc}) == 61, "a name repeats"


def test_the_three_hazard_tests_are_1_2s_three_and_come_from_one_file():
    """§1.2 names three tests of `pager_refusal_advice_test` -- the ones
    that drive `serve_fake`'s four worker threads. The FOURTH test of that
    file drives `FakeSubstrate` directly and carries no such hazard, so
    including it would excuse a DIVERGED §1 offers no explanation for."""
    from acceptance_e4_read import HAZARD_TESTS
    advice = [n for f, _l, n in runner.TESTS
              if f == "pager_refusal_advice_test"]
    assert len(advice) == 4
    assert set(HAZARD_TESTS) < set(advice)
    assert len(HAZARD_TESTS) == 3
    assert ("unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess"
            in advice)
    assert ("unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess"
            not in HAZARD_TESTS)


# -- the two argv forms ----------------------------------------------------


def test_the_two_argv_forms_are_exactly_1s():
    """§1's table spells both commands verbatim. Pass 1 must carry no
    `--focus` and no `--tier` (§1.4 leaves the coarse tier at `call`, so an
    original and its pair differ only by the added focus), and the bare `--`
    must separate the driver's flags from cargo's so `<name> --exact` reaches
    libtest and exactly one test runs."""
    paths = {"sensorium_driver": Path("/d/cargo-sensorium")}
    argv = phases.pass1_argv(paths, "pager_obligation_test", "a_test")
    assert argv == ["/d/cargo-sensorium", "sensorium", "test",
                    "-p", "bloomery-daemon", "--test",
                    "pager_obligation_test", "--", "a_test", "--exact"]
    assert "--focus" not in argv and "--tier" not in argv
    assert argv.index("--") == 7      # after `--test <target>`

    two = phases.pass2_argv("a_test", "r-orig")
    assert two[1:] == ["-m", "sensorium", "refocus", "r-orig",
                       "--focus", "a_test"]
    assert two[0].endswith("/.venv/bin/python")


def test_the_recording_environment_re_adds_only_what_1_names(monkeypatch):
    """`plain_env()` strips every `SENSORIUM_*` and `CARGO_TARGET_DIR`; a
    pass-1 recording needs exactly two back. `SENSORIUM_TIER` must NOT be
    set (§1.4) and `SENSORIUM_NO_INVOCATION_LOG` must not be either (§1.4
    does not silence the audit log), so both facts belong to this function
    rather than to whoever launched the run."""
    monkeypatch.setenv("SENSORIUM_TIER", "line")
    monkeypatch.setenv("SENSORIUM_NO_INVOCATION_LOG", "1")
    env = phases.record_env({"sensorium_e4_target": Path("/t"),
                             "sensorium_dir": Path("/s")})
    assert env["CARGO_TARGET_DIR"] == "/t"
    assert env["SENSORIUM_DIR"] == "/s"
    assert "SENSORIUM_TIER" not in env
    assert "SENSORIUM_NO_INVOCATION_LOG" not in env


def test_the_refocus_environment_carries_the_three_the_CLI_needs(monkeypatch):
    """Three variables, each load-bearing, and the third is the one a reader
    would forget: the CLI passes its OWN environment to the driver child
    (`refocus_rust._launch`), so without `CARGO_TARGET_DIR` the re-run's
    rebuild lands in the clone's own `target/` instead of the FRESH E4
    target -- which would write into the READ-ONLY clone and measure the
    cost of a different build."""
    monkeypatch.setenv("SENSORIUM_TIER", "line")
    env = phases.refocus_env({"sensorium_dir": Path("/s"),
                              "sensorium_driver": Path("/d/cargo-sensorium"),
                              "sensorium_e4_target": Path("/t")})
    assert env["SENSORIUM_DIR"] == "/s"
    assert env["SENSORIUM_CARGO_SENSORIUM"] == "/d/cargo-sensorium"
    assert env["CARGO_TARGET_DIR"] == "/t"
    assert "SENSORIUM_TIER" not in env


# -- the locations ---------------------------------------------------------


def test_every_missing_location_is_named_in_ONE_refusal(monkeypatch):
    """One launch must report every unset variable, not one per attempt: a
    two-hour run that refused three times over three variables costs three
    launches to find out."""
    for key in runner.E4_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_e4()
    for key in runner.E4_ENV:
        assert key in str(e.value)


def test_the_five_locations_are_the_ones_the_run_touches(monkeypatch,
                                                         tmp_path):
    """The names are the contract with the launcher. A renamed variable
    would refuse a correct launch, and a dropped one would let the run
    measure into whatever the environment happened to hold."""
    assert set(runner.E4_ENV) == {
        "SENSORIUM_DRIVER", "SENSORIUM_BLOOMERY", "SENSORIUM_E4_TARGET",
        "SENSORIUM_DIR", "SENSORIUM_RUST_TARGET"}
    for key in runner.E4_ENV:
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    paths = runner.env_paths_e4()
    assert set(paths) == set(runner.E4_ENV.values())
    assert all(isinstance(v, Path) for v in paths.values())


def test_the_launcher_exports_every_variable_the_runner_refuses_without():
    """The launcher is ledger material and is not committed, so this test
    SKIPS BY NAME when it is absent rather than passing. Where it is
    present -- the box a run is launched from -- a variable the runner
    refuses without and the launcher does not export is a launch that dies
    in the preflight after a driver build."""
    launch = (runner.BASE / "launch.sh")
    if not launch.is_file():
        pytest.skip("no launcher in this checkout (ledger material is "
                    "gitignored) — skipped BY NAME, not passed")
    text = launch.read_text()
    for key in runner.E4_ENV:
        assert f"export {key}=" in text, key
    # The CLI resolves the driver through this one; without it every pass-2
    # invocation is a pre-rerun refusal about the launch.
    assert "export SENSORIUM_CARGO_SENSORIUM=" in text
    # §1.4 pre-registers the `temp_dir()` reading, which needs TMPDIR unset.
    assert "unset TMPDIR" in text
    assert runner.RUNNER in text


def test_a_fresh_location_that_is_not_fresh_is_REFUSED(tmp_path):
    """§1.4 says FRESH. A warm store or target would answer with another
    run's artifacts -- and the pair rule would find another run's refocus."""
    warm = tmp_path / "warm"
    warm.mkdir()
    (warm / "leftover").write_text("x")
    with pytest.raises(Refused) as e:
        runner._require_fresh(warm, "SENSORIUM_DIR")
    assert "not empty" in str(e.value)
    empty = tmp_path / "empty"
    runner._require_fresh(empty, "SENSORIUM_DIR")
    assert empty.is_dir()


def test_the_corpus_target_is_derived_from_an_env_var_when_unset(
        monkeypatch, tmp_path):
    """§1.4 requires H7's corpus target to be FRESH but names no variable
    for it. A path derived from `SENSORIUM_E4_TARGET` is still not a
    location compiled into the instrument, and the record says which of the
    two it was."""
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    paths = {"sensorium_e4_target": tmp_path / "bloomery-target-e4",
             "sensorium_bloomery": tmp_path / "clone"}
    cfg = runner.e4_config(paths)
    assert cfg["corpus_target"] == tmp_path / "bloomery-target-e4-corpus"
    assert cfg["corpus_target_from_env"] is False
    monkeypatch.setenv("SENSORIUM_CORPUS_TARGET", str(tmp_path / "named"))
    cfg = runner.e4_config(paths)
    assert cfg["corpus_target"] == tmp_path / "named"
    assert cfg["corpus_target_from_env"] is True


def test_the_config_records_TMPDIR_as_observed(monkeypatch, tmp_path):
    """§1.4's substitution rule: W1's and W4's literals are derived from
    `std::env::temp_dir()`, which is `/tmp` only while `TMPDIR` is unset. A
    run under a set `TMPDIR` must read the SAME predictions with the prefix
    substituted rather than the wrong ones silently."""
    paths = {"sensorium_e4_target": tmp_path / "t",
             "sensorium_bloomery": tmp_path / "clone"}
    monkeypatch.delenv("TMPDIR", raising=False)
    cfg = runner.e4_config(paths)
    assert cfg["tmpdir_observed"] is None and cfg["temp_root"] == "/tmp"
    w1, _w3, w4 = phases2.watch_triples(cfg)
    assert w1["expr"] == 'dir == "/tmp/bloomery-pager-contract"'
    assert w4["expr"] == 'dir == "/tmp/bloomery-pager-remove-unknown"'

    monkeypatch.setenv("TMPDIR", "/scratch/tmp/")
    cfg = runner.e4_config(paths)
    assert cfg["tmpdir_observed"] == "/scratch/tmp/"
    assert cfg["temp_root"] == "/scratch/tmp"
    w1, _w3, w4 = phases2.watch_triples(cfg)
    assert w1["expr"] == 'dir == "/scratch/tmp/bloomery-pager-contract"'
    assert w4["expr"] == ('dir == "/scratch/tmp/'
                          'bloomery-pager-remove-unknown"')


# -- §1.3's triples --------------------------------------------------------


def test_the_watch_triples_are_1_3s_and_W3_gates_on_the_EXIT():
    """§1.3 splits W3's two readings deliberately: the EXIT is the gate,
    byte-identical to E9's 1, and the printed CLASS is REPORTED because it
    necessarily differs -- `pager_with_model` is defined in another test
    binary, which a single `--exact` invocation never builds into the run.

    A runner that gated on E9's `not satisfied` class would be gating on a
    prediction derivably false from the source, and would report a STOP on a
    correct reader."""
    cfg = {"temp_root": "/tmp"}
    w1, w3, w4 = phases2.watch_triples(cfg)
    assert [t["id"] for t in (w1, w3, w4)] == ["W1", "W3", "W4"]
    assert w1["of"] == w3["of"] == (
        "missing_stats_is_a_contract_violation_not_a_reply")
    assert w4["of"] == "remove_agent_on_unknown_id_is_named"
    assert (w1["predicted_class"], w1["predicted_exit"], w1["line"]) == (
        "SATISFIED", 0, 251)
    assert (w3["predicted_class"], w3["predicted_exit"]) == (
        "no recorded code matches", 1)
    assert (w4["predicted_class"], w4["predicted_exit"], w4["line"]) == (
        "SATISFIED", 0, 61)
    assert w1["gate"] == w4["gate"] == "class and exit"
    assert w3["gate"] == "exit"
    assert w3["at"] == "pager_with_model"
    # Every triple runs on a NEW (refocused) trace: an original is unfocused
    # and `watch` on it is E9's capability refusal, not this record's
    # question.
    assert all(t["of"] in {n for _f, _l, n in runner.TESTS}
               for t in (w1, w3, w4))


# -- the loop's bound and its kills ----------------------------------------


def test_a_kill_is_recorded_as_a_fact_and_not_raised(tmp_path, monkeypatch):
    """§1's kill criteria make a timed-out arm a recorded not-measured. A
    `TimeoutExpired` that escaped would take every later phase down with it
    and lose the endpoints already read to one slow command — and
    `acceptance_lib.run` writes its log only after the call returns, so a
    killed command otherwise leaves no evidence at all."""
    import acceptance_e9_phases as e9ph

    def killed(*_a, **_k):
        raise subprocess.TimeoutExpired(["cargo"], 1800, output=b"partial\n")

    monkeypatch.setattr(e9ph, "run", killed)
    monkeypatch.setattr(lib, "LOGS", tmp_path / "logs")
    res = phases.guarded(["cargo", "x"], tmp_path, "p1.log", {}, 1800, "P1/1")
    assert res["timed_out"] is True and res["rc"] is None
    assert res["out"] == "partial\n" and res["kill_s"] == 1800
    assert Path(res["log"]).is_file()
    assert "KILLED at 1800 s" in Path(res["log"]).read_text()


def test_the_ceilings_are_1_4s(tmp_path, monkeypatch):
    """§1.4 fixes them: 1800 s per `cargo sensorium`, 1800 s per `sensorium
    refocus`, and the whole loop at 2 hours."""
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4_config({"sensorium_e4_target": tmp_path / "t",
                            "sensorium_bloomery": tmp_path / "c"})
    assert cfg["cargo_timeout"] == 1800
    assert cfg["refocus_timeout"] == 1800
    assert cfg["loop_budget_s"] == 7200


def test_the_2_hour_bound_is_a_recorded_not_run_and_not_a_shortened_pass(
        tmp_path, monkeypatch):
    """A loop that ran past its bound would publish counts over a machine
    already over budget; one that RAISED at the bound would lose every
    number already read. So the deadline is checked before each invocation
    and the tests it never reached are rows carrying `not_run` — which is
    what `_incomplete_drops` then nulls the endpoints on."""
    monkeypatch.setattr(phases, "LOGS", tmp_path / "logs")
    calls = []

    def fake_record(_paths, _cfg, index, target, name):
        calls.append(name)
        return {"index": index, "target": target, "name": name, "rc": 0,
                "run": f"r{index}", "wall_s": 1.0, "timed_out": False,
                "multi_process": False, "meta": None, "summary_lines": []}

    monkeypatch.setattr(phases, "record_one", fake_record)
    cfg = {"tests": [["f", 1, "a"], ["f", 2, "b"]], "loop_budget_s": 0,
           "cargo_timeout": 1800}
    got = phases.pass_one({"sensorium_dir": tmp_path}, cfg)
    assert calls == [], "the bound did not stop the loop"
    assert got["budget_exhausted"] == ["P1/a", "P1/b"]
    assert all("not_run" in r for r in got["runs"])
    assert got["measured"] == 0 and got["n"] == 2


def test_pass_2_inherits_pass_1s_deadline_and_does_not_open_a_second(
        tmp_path, monkeypatch):
    """§1.4 bounds THE LOOP at 2 hours, not each pass at 2 hours. A pass 2
    that opened its own budget would let the two passes run for four in
    silence, and every count would be over a machine long past the bound."""
    monkeypatch.setattr(phases, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(phases, "refocus_one",
                        lambda *_a, **_k: pytest.fail("pass 2 ran past the "
                                                      "loop's deadline"))
    one = {"runs": [{"index": 1, "target": "f", "name": "a", "run": "r1"}],
           "loop_deadline_monotonic": 0.0, "killed": []}
    got = phases.pass_two({}, {"tests": [1], "refocus_timeout": 1800,
                               "loop_budget_s": 7200}, one)
    assert got["budget_exhausted"] == ["P2/a"]
    assert got["loop_deadline_inherited_from_pass1"] is True
    assert got["measured"] == 0


def test_the_STOP_classes_are_1s_two_and_a_DIVERGED_is_not_one():
    """§1 has exactly two STOP classes: a focused BUILD failure (H2) and a
    REFUSED after the rerun (H3). An unexpected DIVERGED is a FINDING and
    must not stop the rung, and a pre-rerun refusal is H1's number -- both
    of them are things a correct instrument can meet on a subject that is
    simply nondeterministic or mis-called."""
    stops = runner._stops({"raw_h2": {"build_failures": ["a"]},
                           "raw_h3": {"refused_after_rerun": ["b"]}})
    assert len(stops) == 2
    assert "kill 1" in stops[0] and "build failure" in stops[0]
    assert "kill 2" in stops[1] and "REFUSED after the rerun" in stops[1]
    assert runner._stops({
        "raw_h2": {"build_failures": []},
        "raw_h3": {"refused_after_rerun": [], "diverged": ["x"],
                   "diverged_findings": ["x"]}}) == []


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


# -- the log roots ---------------------------------------------------------


def test_the_runner_gives_BOTH_phases_modules_the_runs_log_root():
    """The wiring the entry slice's first detached launch died on: each
    phases module opens `logs_at(LOGS / "<phase>")` in the namespace it
    lives in, and a front door that assigned only the shared pointers left
    that name unset — a `NameError` fourteen seconds in, after the byte-lock
    and the preflight and before one number was measured. E4 has TWO such
    modules, so there are two pointers to get wrong."""
    assert phases.LOGS == runner.LOGS
    assert phases2.LOGS == runner.LOGS
    assert runner.LOGS == runner.BASE / "logs"
    src = (REPO / "rust" / "tests" / "acceptance_e4.py").read_text()
    for assignment in ("lib.LOGS = LOGS", "ph.LOGS = LOGS",
                       "eph.LOGS = LOGS", "eph2.LOGS = LOGS",
                       "e6ppp.LOGS = LOGS", "e6ppp.BASE = BASE"):
        assert src.count(assignment) >= 1, assignment


@pytest.mark.parametrize("module", ["acceptance_e4_phases",
                                    "acceptance_e4_phases2"])
def test_a_phases_module_declares_the_name_and_owns_no_location(module):
    """The other half, where the runner's assignment cannot mask it: a FRESH
    load, with no front door to hand it a pointer. A default copied from
    `acceptance_lib.LOGS` would equal this run's root today by import order
    and silently stop doing so on any reorder."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        module + "__fresh", REPO / "rust" / "tests" / f"{module}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "LOGS" in vars(mod)
    assert mod.LOGS is None


# -- no box path -----------------------------------------------------------


def test_no_module_of_this_instrument_names_a_box_path():
    """Every location is an environment variable. A path compiled into the
    runner would make the record unreproducible and the file wrong on any
    other machine. The only box strings allowed anywhere are this test's own
    literals."""
    for name in INSTRUMENT:
        text = (REPO / "rust" / "tests" / name).read_text()
        assert "/mnt/" not in text, name
        assert "/home/" not in text, name


def _crate_test_files():
    """Every test file of every Rust crate, `golden*/` fixtures excluded."""
    for pattern in ("rust/*/tests/**/*.rs", "rust/*/tests/**/*.py"):
        for path in sorted(REPO.glob(pattern)):
            if any(part.startswith("golden") for part in path.parts):
                continue
            yield path


def test_no_rust_crate_test_file_names_a_box_path():
    """The scan the E9 suite widened, run again here: an instrument-only
    scan let a box path sit in `sensorium-transform/tests/census.rs` since
    `089768d` with no test able to see it."""
    offenders = []
    for path in _crate_test_files():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if "/mnt/" in line or "/home/" in line:
                offenders.append(
                    f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert not offenders, (
        "a box-local path in a committed test file makes the suite wrong on "
        "any other machine:\n" + "\n".join(offenders))


def test_the_widened_scan_actually_reaches_the_file_that_motivated_it():
    """A scan that matched nothing would pass for the wrong reason -- an
    empty walk is not a clean tree. `census.rs` is the file the debt named,
    so the walk has to contain it, and it has to be more than the instrument
    (which the test above covers on its own path)."""
    reached = {p.relative_to(REPO).as_posix() for p in _crate_test_files()}
    assert "rust/sensorium-transform/tests/census.rs" in reached
    assert len(reached) > len(INSTRUMENT)
    assert not any("/golden" in name for name in reached), reached
