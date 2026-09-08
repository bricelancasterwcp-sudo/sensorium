"""The E4′ instrument against its byte-locked pre-registration.

Everything a launch would discover expensively, discovered here instead: the
lock, §1.1's 61 rows, §1.2's partition, the argv, the environment contract,
the ceilings, the kill wording, and the rule that no module of this
instrument names a box path.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4p as runner                                    # noqa: E402
import acceptance_e4p_phases as phases                             # noqa: E402
import acceptance_e4p_rows as rows                                 # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

#: The locked range's sha256 at the AMENDED lock (`d5efaab`) -- what the
#: runner refuses on, and what the live document must hash to.
DOC_SHA = "04aa4b6b0cdf20ee67f21b7e5741819f3e324d150dc2bd1b3969b68b7a3e3967"
#: And at the ORIGINAL lock (`2991c3b`), Task 0's commit, carried beside it
#: so the amendment is a checkable fact rather than a claim in prose.
ORIGINAL_DOC_SHA = ("82152208e2fa57f54c573dea8305be28097529fd2544e2be5caa"
                    "bd16e6bf3528")

#: DERIVED, like `TEST_FILES` below and for the same reason: a hand-written
#: list is a guard that goes stale the next time a module is added, and this
#: one did — `acceptance_e4p_preflight.py` arrived when the runner crossed
#: the 800-line ceiling.
INSTRUMENT = tuple(sorted(
    p.name for p in (REPO / "rust" / "tests").glob("acceptance_e4p*.py"))
) + ("render_e4p.py",)


def test_the_scanned_module_list_covers_every_module_of_this_instrument():
    assert len(INSTRUMENT) >= 10, INSTRUMENT
    for name in ("acceptance_e4p.py", "acceptance_e4p_preflight.py",
                 "acceptance_e4p_read.py", "render_e4p.py"):
        assert name in INSTRUMENT


# -- the byte-lock ---------------------------------------------------------

def _require_lock_commit(*shas):
    """A shallow checkout has no such commit. Skip BY NAME rather than pass
    on a missing one -- a skipped lock check must never look like a passed
    one."""
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) — skipped "
                        "BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout — "
                        "skipped BY NAME, not passed")


def test_the_runner_carries_BOTH_locks():
    """Two shas, and they are no longer one.

    `BYTE_LOCK` is what the runner refuses on -- the AMENDED §1, whose
    §1.5 (amendment A1) records the env-clause finding and the launch
    environment, dated before any E4′ number was read. `ORIGINAL_LOCK` is
    Task 0's commit, before the instrument existed. Both are carried so the
    amendment is visible in the record: a runner that dropped the original
    would make a post-lock edit indistinguishable from no edit at all, and
    one that refused on the original would refuse on the document as it now
    stands."""
    assert runner.BYTE_LOCK == "d5efaab"
    assert runner.ORIGINAL_LOCK == "2991c3b"
    assert runner.BYTE_LOCK != runner.ORIGINAL_LOCK


def test_the_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a
    stray edit to §1 is caught before a run is launched rather than by a
    refusal with a driver already built. The LIVE document must hash to the
    AMENDED sha -- not to the original, which is what a lock left behind by
    an amendment would accept."""
    _require_lock_commit(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_sha256"] == DOC_SHA
    assert rec["locked_sha256"] != ORIGINAL_DOC_SHA


def test_the_record_names_BOTH_shas_and_the_amendment_flag():
    """§1 was amended after the original lock and before any number was
    read. The record must say so with two shas and a flag: a record
    reporting no amendment would be describing another document, and one
    reporting only the amended sha would leave a reader unable to check
    that the expectation, the H-table and the kills did not move."""
    _require_lock_commit(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["locked_sha256"] == DOC_SHA
    assert rec["original_lock_sha256"] == ORIGINAL_DOC_SHA
    assert rec["amended_after_the_original_lock"] is True
    assert rec["amendment_bytes"] > 0
    assert rec["original_lock"] == "2991c3b"


def test_the_amendment_ADDED_section_1_5_and_moved_no_earlier_row():
    """A1 inserted §1.5 before `## 2` and changed nothing above it: every
    `|` row of the locked range -- §1.1's 61 originals, §1.2's partition,
    the H-table -- is byte-identical at the two commits. That is what makes
    "expectation, H-table and kills unchanged" checkable rather than
    claimed."""
    _require_lock_commit(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    before = _section1_at(runner.ORIGINAL_LOCK)
    after = _section1_at(runner.BYTE_LOCK)
    assert [ln for ln in before.splitlines() if ln.startswith("|")] == \
           [ln for ln in after.splitlines() if ln.startswith("|")]
    assert "### 1.5 Amendment A1" in after
    assert "### 1.5" not in before
    assert after.startswith(before.split("### 1.5")[0][:200])


def _section1_at(sha: str) -> str:
    """§1 as committed at `sha`, by the lock's own extraction."""
    text = subprocess.run(
        ["git", "show", f"{sha}:{runner.DOC.relative_to(REPO).as_posix()}"],
        cwd=REPO, capture_output=True, text=True).stdout
    return rung3.section1(text)


def test_the_byte_lock_REFUSES_a_document_that_differs_by_one_byte(tmp_path):
    """The check has to be able to fail, or `identical is True` above is an
    assertion about nothing."""
    _require_lock_commit(runner.BYTE_LOCK)
    doc = tmp_path / runner.DOC.name
    doc.write_text(runner.DOC.read_text().replace("Granted 57", "Granted 58",
                                                  1))
    with pytest.raises(Refused) as e:
        rung3.byte_lock_check(doc, runner.BYTE_LOCK, runner.ORIGINAL_LOCK,
                              read_committed=lambda _p, _c:
                              runner.DOC.read_text())
    assert "differs from the byte-lock" in str(e.value)


def test_an_unset_lock_REFUSES_rather_than_measuring(monkeypatch):
    """A pre-registration that can still be edited is not one."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked yet" in str(e.value)


# -- §1.1's table ----------------------------------------------------------

def _table_from_the_locked_document() -> list[tuple]:
    """§1.1's enumeration, read out of the document itself: the
    `### 1.1` … `### 1.2` slice and its `| # | fn | file | run |` rows."""
    text, keep, buf = runner.DOC.read_text(), False, []
    for line in text.splitlines():
        if line.startswith("### 1.1"):
            keep = True
        elif line.startswith("### 1.2"):
            break
        if keep:
            buf.append(line)
    out = []
    for line in buf:
        m = re.match(r"^\| (\d+) \| `([A-Za-z0-9_]+)` \| "
                     r"`([a-z0-9_]+\.rs)` \| `([0-9a-f-]+)` \|\s*$", line)
        if m:
            out.append((int(m.group(1)), m.group(2), m.group(3)[:-3],
                        m.group(4)))
    return out


def test_the_61_row_table_IS_1_1s_table_row_for_row():
    """The instrument keeps a CONSTANT -- a runner must not parse prose at
    measurement time -- and this is the pin between the constant and the
    byte-locked document. A retyped digit in a run id would copy the wrong
    trace; a name that drifted by one character would refocus something
    §1.1 never enumerated."""
    _require_lock_commit(runner.BYTE_LOCK)
    from_doc = _table_from_the_locked_document()
    assert len(from_doc) == 61, len(from_doc)
    assert from_doc == list(rows.ROWS)
    assert rows.GATE_N == 61
    assert len(rows.TARGETS) == 7


def test_the_derived_table_actually_reads_the_document():
    """The pin above is only worth anything if the derivation can fail: a
    regex that matched nothing would make the equality an assertion about
    two empty lists. §1.1's seven counts, checked."""
    from collections import Counter
    from_doc = _table_from_the_locked_document()
    assert from_doc, "the §1.1 slice yielded no rows"
    assert Counter(t for _i, _n, t, _r in from_doc) == {
        "pager_codec_gate_test": 20, "pager_obligation_test": 15,
        "pager_refusal_advice_test": 4, "pager_remove_agent_test": 4,
        "pager_reservation_test": 8, "pager_test": 4,
        "pager_weights_test": 6}
    assert len({r for _i, _n, _t, r in from_doc}) == 61, "a run id repeats"
    assert len({n for _i, n, _t, _r in from_doc}) == 61, "a name repeats"


def test_1_2s_partition_is_the_four_names_and_their_program_thread_counts():
    """§1.2, written first: granted 57, WITHHELD on exactly four, with the
    program's own thread count (1, 4, 4, 4) after the harness thread comes
    out. A count of 2 or 5 here would be the RAW number and would mean the
    rule never fired."""
    assert rows.EXPECTED_WITHHELD == {
        "a_pager_can_be_shared_across_threads": 1,
        "the_refusal_advises_a_window_that_actually_places": 4,
        "the_advice_never_exceeds_the_window_the_agent_already_had": 4,
        "the_journal_records_the_advice_alongside_the_refusal_arithmetic": 4}
    assert len(rows.EXPECTED_GRANTED) == 57
    assert set(rows.EXPECTED_GRANTED).isdisjoint(rows.EXPECTED_WITHHELD)
    assert set(rows.EXPECTED_GRANTED) | set(rows.EXPECTED_WITHHELD) == set(
        rows.NAMES)
    assert rows.EXPECTED_HARNESS_THREADS == 1


def test_the_fourth_advice_test_is_GRANTED_and_not_one_of_the_four():
    """§1.2 names it: `unmeasured_vram_advises_nothing…` drives the
    substrate directly with no server and spawns nothing, so it is one of
    the 57. Including it would have made the partition 56/5."""
    name = "unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess"
    assert name in rows.EXPECTED_GRANTED
    assert name not in rows.EXPECTED_WITHHELD


def test_the_predicted_numbers_come_from_1_2_and_are_not_derived_from_a_run():
    assert rows.EXPECTED_MATCH == 61
    assert rows.EXPECTED_PAIRS_OF_ONE == 61
    assert rows.EXPECTED_EXCLUDED_CHILDREN == 0
    assert rows.EXPECTED_SHIM_KEYS == 61


# -- the argv and the environment -----------------------------------------

def test_the_argv_form_is_exactly_1s():
    """§1's table: pass 1 is NOT RUN, and pass 2 is
    `sensorium refocus <run> --focus <name>` and nothing else. No `--tier`:
    §1.4 says this record does not set one."""
    argv = phases.refocus_argv("a_test", "r-orig")
    assert argv[1:] == ["-m", "sensorium", "refocus", "r-orig", "--focus",
                        "a_test"]
    assert argv[0].endswith("/.venv/bin/python")
    assert "--tier" not in argv


def test_the_refocus_environment_carries_the_three_the_CLI_needs(monkeypatch):
    """And nothing else: `plain_env()` strips every `SENSORIUM_*`, and what
    goes back is named here rather than inherited from the launcher."""
    monkeypatch.setenv("SENSORIUM_TIER", "line")
    monkeypatch.setenv("SENSORIUM_NO_INVOCATION_LOG", "1")
    env = phases.refocus_env({"sensorium_dir": Path("/s"),
                              "sensorium_driver": Path("/d/cargo-sensorium"),
                              "sensorium_e4p_target": Path("/t")})
    assert env["SENSORIUM_DIR"] == "/s"
    assert env["SENSORIUM_CARGO_SENSORIUM"] == "/d/cargo-sensorium"
    assert env["CARGO_TARGET_DIR"] == "/t"
    assert "SENSORIUM_TIER" not in env
    assert "SENSORIUM_NO_INVOCATION_LOG" not in env


def test_the_fresh_store_is_the_only_one_a_refocus_can_write_into():
    """§1.3 forbids a refocus pointing at the kept store, and this function
    is where that is true or false: `SENSORIUM_DIR` is the FRESH store's
    key, never `sensorium_e4_store`."""
    src = (RUST_TESTS / "acceptance_e4p_phases.py").read_text()
    body = src[src.index("def refocus_env"):src.index("def guarded")]
    assert '"SENSORIUM_DIR": str(paths["sensorium_dir"])' in body
    assert "sensorium_e4_store" not in body


def test_every_missing_location_is_named_in_ONE_refusal(monkeypatch):
    for key in runner.E4P_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_e4p()
    for key in runner.E4P_ENV:
        assert key in str(e.value)


def test_the_launcher_exports_every_variable_the_runner_refuses_without():
    """The launcher is the only thing that knows the box's paths, and a
    variable the runner needs but the launcher does not export is a refusal
    fourteen seconds into a detached run."""
    launch = (REPO / ".superpowers" / "sdd"
              / "2026-09-07-sensorium-rung4-debts" / "acceptance-e4p"
              / "launch.sh")
    if not launch.is_file():
        pytest.skip("the launcher is ledger-local and not in this checkout")
    text = launch.read_text()
    for key in runner.E4P_ENV:
        assert f"export {key}=" in text, key
    # The CLI resolves the driver through this one, and `plain_env()` strips
    # it, so the launcher must export it AND the phases must re-add it.
    assert "export SENSORIUM_CARGO_SENSORIUM=" in text
    assert "unset TMPDIR" in text
    assert text.rstrip().endswith("rust/tests/acceptance_e4p.py")


def test_a_fresh_location_that_is_not_fresh_is_REFUSED(tmp_path):
    (tmp_path / "leftover").mkdir()
    with pytest.raises(Refused) as e:
        runner._require_fresh(tmp_path, "SENSORIUM_DIR")
    assert "not FRESH" in str(e.value)


def test_the_config_records_TMPDIR_as_observed_and_what_it_RESOLVED_to(
        monkeypatch, tmp_path):
    """§1.4 observes `TMPDIR` and says it binds nothing here. What the
    process actually resolved is recorded beside it, because an unset
    variable does not by itself say what `gettempdir()` returned."""
    monkeypatch.delenv("TMPDIR", raising=False)
    paths = {"sensorium_e4p_target": tmp_path / "t"}
    cfg = runner.e4p_config(paths)
    assert cfg["tmpdir_observed"] is None
    assert cfg["tempfile_gettempdir"]
    assert cfg["corpus_target"].name == "t-corpus"
    assert cfg["corpus_target_from_env"] is False


def test_the_row_table_can_be_replaced_only_through_an_EXPLICIT_hook(
        tmp_path):
    """The dry-run hook. §1.1's table is the default; a caller may pass a
    smaller one, and the config records how many rows it is running."""
    paths = {"sensorium_e4p_target": tmp_path / "t"}
    assert runner.e4p_config(paths)["gate_n"] == 61
    small = runner.e4p_config(paths, rows=[(1, "n", "t", "r")])
    assert small["gate_n"] == 1
    assert small["gate_n_locked"] == 61


def test_a_dry_run_cannot_be_reached_from_the_launcher():
    """It takes an argv flag, and the launcher passes none. A dry run whose
    numbers could land in the tracked `results.json` would be worse than no
    dry run at all."""
    launch = (REPO / ".superpowers" / "sdd"
              / "2026-09-07-sensorium-rung4-debts" / "acceptance-e4p"
              / "launch.sh")
    if launch.is_file():
        assert "--dry-rows" not in launch.read_text()
    src = (RUST_TESTS / "acceptance_e4p.py").read_text()
    assert '"--dry-rows" in argv' in src
    body = src[src.index("def assemble_only"):]
    assert "results-e4p-dry.results.json" in body


# -- the ceilings and the kills -------------------------------------------

def test_the_ceilings_are_1_4s():
    """1800 s per `sensorium refocus`, and the whole LOOP bounded at
    1 h 15 min. Not two hours: this record runs one pass, and E4's bound was
    for two."""
    assert runner.REFOCUS_TIMEOUT == 1800
    assert runner.LOOP_BUDGET_S == 75 * 60


def test_a_kill_is_a_RECORDED_fact_and_not_an_exception(tmp_path,
                                                        monkeypatch):
    """§1.4's kill rules make a bound reached a recorded not-measured, never
    a crash that takes the endpoints already read down with it."""
    monkeypatch.setattr(phases, "LOGS", tmp_path)
    res = phases.guarded([sys.executable, "-c", "import time; time.sleep(30)"],
                         REPO, "sleep.log", {"PATH": "/usr/bin:/bin"}, 1,
                         "T")
    assert res["timed_out"] is True
    assert res["rc"] is None
    assert res["kill"]["still_alive"] is False
    assert (tmp_path / "sleep.log").is_file()


def test_the_kill_signals_the_GROUP_and_verifies_with_ps(tmp_path,
                                                         monkeypatch):
    """A child that spawns a grandchild is the case that matters: killing
    the leader alone leaves the grandchild holding cores for the rest of the
    record. The group is signalled, and `ps -p` -- never `pkill -f` -- says
    whether it went."""
    monkeypatch.setattr(phases, "LOGS", tmp_path)
    script = ("import subprocess, sys, time; "
              "subprocess.Popen([sys.executable, '-c', "
              "'import time; time.sleep(60)']); time.sleep(60)")
    res = phases.guarded([sys.executable, "-c", script], REPO, "group.log",
                         {"PATH": "/usr/bin:/bin"}, 2, "T")
    assert res["timed_out"] is True
    assert res["kill"]["pgid"] is not None
    assert res["kill"]["term"] is not None
    assert res["kill"]["still_alive"] is False


def test_no_module_of_this_instrument_ever_shells_out_to_pkill():
    """It self-matches: a `-f` pattern naming this instrument matches the
    runner's own argv, so it never reaps and can reap the wrong process.

    The scan is for the ARGV LITERAL -- the name in quotes, as it would have
    to appear to be executed -- so the prose that explains the rule does not
    trip the rule."""
    for name in INSTRUMENT:
        text = (RUST_TESTS / name).read_text()
        for literal in ('"pkill"', "'pkill'", '"killall"', "'killall'"):
            assert literal not in text, f"{name} shells out to {literal}"


def test_the_STOP_classes_implement_the_WORDS_of_each_kill_sentence():
    """§1's three cross-references are off by one -- H5 and §1.3's mtime
    sentence both say "STOP" while citing kill 4, and §1.3's run-id sentence
    says "a refusal to start (before any number)" while citing kill 3. The
    runner implements the WORDS: the partition, the verdict, the pair, the
    instrument's own schema and the kept store are all read AFTER a number,
    so each is a STOP; the run-id mismatch is raised as a Refusal before any
    number, which is the infrastructure kill."""
    stops = runner._stops({
        "raw_h1": {"partition_as_predicted": False, "granted_n": 55},
        "raw_h2": {"match_as_predicted": False, "non_match": [{"n": 1}]},
        "raw_h3": {"pairs_as_predicted": False, "not_one": [{"n": 0}]},
        "raw_h5": {"as_predicted": False, "raw_schema_version": None},
        "cleanup": {"kept_store_unchanged": False,
                    "kept_census_differences": ["r-1.db: st_mtime_ns"]},
    })
    joined = "; ".join(stops)
    assert len(stops) == 5
    assert "H1 (kill 1)" in joined and "H2 (kill 2)" in joined
    assert "H3 (kill 3)" in joined
    assert "erratum" in joined      # H5 and §1.3 say STOP, cite kill 4
    assert "the KEPT store changed" in joined


def test_a_run_that_measured_everything_as_predicted_STOPS_on_nothing():
    assert runner._stops({
        "raw_h1": {"partition_as_predicted": True},
        "raw_h2": {"match_as_predicted": True},
        "raw_h3": {"pairs_as_predicted": True},
        "raw_h5": {"as_predicted": True},
        "raw_h6": {"all_green": True},
        "cleanup": {"kept_store_unchanged": True},
    }) == []


# -- no box path anywhere --------------------------------------------------

#: The three box-path prefixes no committed file of this instrument may
#: name, ASSEMBLED rather than written: this file is one of the files the
#: scan below reads, and a literal here would make it fail on itself.
BOX_PATHS = ("/" + "mnt/", "/" + "home/brice", "/" + "tmp/claude")


@pytest.mark.parametrize("name", INSTRUMENT)
def test_no_module_of_this_instrument_names_a_box_path(name):
    """Every location is an environment variable. A path compiled into a
    module would make the record's own §2 a claim about somewhere else."""
    text = (RUST_TESTS / name).read_text()
    for needle in BOX_PATHS:
        assert needle not in text, f"{name} names {needle}"


#: DERIVED, never listed: a hand-written list is a guard that goes stale
#: the next time a test file is added, which is exactly what happened when
#: `test_acceptance_e4p_phases.py` arrived.
TEST_FILES = sorted(p.name for p in (REPO / "tests").glob(
    "test_acceptance_e4p*.py"))


def test_the_scanned_test_list_covers_every_file_of_this_instrument():
    assert len(TEST_FILES) >= 5, TEST_FILES
    assert "test_acceptance_e4p_phases.py" in TEST_FILES


@pytest.mark.parametrize("name", TEST_FILES)
def test_no_test_of_this_instrument_names_a_box_path(name):
    """The same rule on this side of the line: a test that hard-coded the
    box's store would pass here and nowhere else."""
    path = REPO / "tests" / name
    if not path.is_file():
        pytest.skip(f"{name} is not in this checkout")
    text = path.read_text()
    for needle in BOX_PATHS:
        assert needle not in text, f"{name} names {needle}"


def test_the_scan_would_actually_CATCH_a_box_path():
    """The scan above is only worth anything if it can fail."""
    sample = "STORE = Path('" + BOX_PATHS[0] + "extra/sensorium-dir/e4')"
    assert any(n in sample for n in BOX_PATHS)
    assert all(n not in "STORE = Path(os.environ['SENSORIUM_DIR'])"
               for n in BOX_PATHS)


@pytest.mark.parametrize("name", INSTRUMENT)
def test_every_module_of_this_instrument_is_under_800_lines(name):
    n = len((RUST_TESTS / name).read_text().splitlines())
    assert n <= 800, f"{name} is {n} lines"


# -- the review's honesty items -------------------------------------------

def test_the_preflight_refuses_while_any_cargo_is_running(monkeypatch):
    """This run builds the driver, rebuilds 61 units into a fresh target and
    finally runs `cargo test --workspace`. A second cargo sharing the box
    changes every wall the record reports and can hold a lock the build
    needs. `pgrep -x` — the EXACT process name, never `-f`, whose pattern
    would match this runner's own argv and refuse against itself."""
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)
        import subprocess as sp
        return sp.CompletedProcess(cmd, 0, stdout="12345\n", stderr="")
    monkeypatch.setattr(runner.subprocess, "run", fake)
    with pytest.raises(Refused) as e:
        runner.cargo_running()
    assert calls[0] == ["pgrep", "-x", "cargo"]
    assert "-f" not in calls[0]
    assert "12345" in str(e.value)


def test_the_cargo_check_RECORDS_its_result_when_nothing_is_running(
        monkeypatch):
    """Recorded either way: "no cargo was running" is a lens fact of the
    run, and a check whose passing leaves no trace cannot be audited."""
    def fake(cmd, **kw):
        import subprocess as sp
        return sp.CompletedProcess(cmd, 1, stdout="", stderr="")
    monkeypatch.setattr(runner.subprocess, "run", fake)
    rec = runner.cargo_running()
    assert rec["command"] == "pgrep -x cargo"
    assert rec["running"] is False
    assert rec["pids"] == []


def test_a_KILLED_invocation_is_named_by_the_KILLS_words_not_by_H1():
    """The review's finding: a row killed at its ceiling leaves its licence
    unread, `partition_as_predicted` goes False, and the first line Task 6
    reads used to attribute a kill-4/5 event to kill 1 (the partition).
    The kill is named FIRST, by the words of the rule that applies."""
    stops = runner._stops({
        "numbers_read": True,
        "raw_pass2": {"killed": ["a_pager_can_be_shared_across_threads"],
                      "budget_exhausted": [], "n": 61, "measured": 61},
        "raw_h1": {"partition_as_predicted": False, "granted_n": 60,
                   "n": 61},
    })
    first = stops[0]
    assert "KILLED" in first
    assert "a number had already been read" in first
    assert "STOP" in first
    assert "kill 1" not in first
    assert any("kill 1" in s for s in stops[1:]), "H1 still says its piece"


def test_a_kill_BEFORE_any_number_is_named_as_the_INFRASTRUCTURE_kill():
    """§1.4's rule 4 by its WORDS: a `.FAILED` before any number has been
    read is infrastructure — the run is archived, the fresh locations
    emptied, the 61 copies re-made, and it is relaunched from zero."""
    stops = runner._stops({
        "numbers_read": False,
        "raw_pass2": {"killed": ["x"], "budget_exhausted": [], "n": 61,
                      "measured": 61},
    })
    assert stops
    assert "infrastructure" in stops[0]
    assert "relaunched from zero" in stops[0]
    assert "STOP" not in stops[0]


def test_the_H1_stop_sentence_names_a_real_denominator():
    """It used to render "granted 0 of ?" — dividing a count by the length
    of its own list. §1.2's denominator is the 61."""
    stops = runner._stops({
        "numbers_read": True,
        "raw_h1": {"partition_as_predicted": False, "granted_n": 0,
                   "n": 61, "expected_granted_n": 57}})
    assert "0 of 61" in stops[0]
    assert " of ?" not in stops[0]


def test_numbers_read_is_flushed_the_moment_the_first_number_is_read(
        tmp_path):
    """Not computed at the end: a run that dies between the first reading
    and the marker must still leave a raw record that SAYS a number was
    read, or §1.4's rules 4 and 5 cannot be applied to it at all."""
    res = {"started": "now"}
    path = tmp_path / "raw.json"
    runner.mark_numbers_read(res, path, "pass 2 read a verdict for row 1")
    assert res["numbers_read"] is True
    assert res["numbers_read_because"] == "pass 2 read a verdict for row 1"
    assert res["numbers_read_at"]
    import json
    assert json.loads(path.read_text())["numbers_read"] is True


def test_marking_it_twice_keeps_the_FIRST_reason(tmp_path):
    """The field records when the first number was read, not the last."""
    res, path = {}, tmp_path / "raw.json"
    runner.mark_numbers_read(res, path, "the first")
    first_at = res["numbers_read_at"]
    runner.mark_numbers_read(res, path, "the second")
    assert res["numbers_read_because"] == "the first"
    assert res["numbers_read_at"] == first_at
