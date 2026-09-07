"""The E4 instrument's READERS, tested without the box.

Nothing here runs cargo, the driver or the query CLI, opens the clone, reads
anything under `/mnt`, or needs an environment variable to be set by whoever
launched pytest. Every input is either a pasted answer in the shape the real
commands print -- taken from the lines `corpus/rust/refocus_*` and
`tests/test_refocus_rust.py` already pin -- or a sqlite file this test builds.

What it tests is the places a parser could report a wrong number while every
command it read had succeeded:

* the licence's bullets versus the blind-spot block's, which print with the
  same `  - ` prefix directly under each other -- a scan that took every
  bullet would count the recorder's categorical blind spots as verified
  points;
* the two UNVERIFIABLE markers, which are counted in their own field and
  never summed into a verified total;
* W3's class, which E9's four-class table has no row for;
* §1.4's DISCRIMINATOR, on synthetic fingerprint tables where the hazard and
  the finding differ by one number;
* §1.4's pair rule, where a SECOND refocus of one original would otherwise
  find the first one's trace as well as its own.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4_read as rd                                    # noqa: E402

# -- the shapes the real commands print -------------------------------------

#: The Rust blind-spot block, verbatim from `vocab.blind_spots` on a Rust
#: trace. Present in every sample below because its bullets are the ones a
#: careless licence scan would swallow.
BLIND_SPOTS = [
    "what sensorium sees at all: Rust code in the workspace units cargo "
    "rebuilt through this recorder's wrapper. Nothing else. No verdict here "
    "-- MATCH, DIVERGED or REFUSED -- says anything about:",
    "  - any child process, by any mechanism. Some are noticed and listed "
    "above; an empty list is NOT evidence that none ran",
    "  - any thread whose body ran no instrumented code: it leaves no "
    "fingerprint, so it is not among the compared",
    "  - output not recorded (capabilities.output: false)",
    "  - threads from dependency code are unnamed",
    "  - the re-run's rebuild is its own cost: --focus keys a fresh shim and "
    "a rebuild of the matched units",
]

MATCH_ANSWER = "\n".join([
    "refocus-of: r-orig   cmd: /d/cargo-sensorium --refocus-of r-orig "
    "--focus missing_stats_is_a_contract_violation_not_a_reply test -p "
    "bloomery-daemon --test pager_obligation_test -- "
    "missing_stats_is_a_contract_violation_not_a_reply --exact",
    "cwd: /clone",
    "focus: missing_stats_is_a_contract_violation_not_a_reply   window: -",
    "source: unchanged (37 file(s) compared by content; data files, untraced "
    "code and installed dependencies are NOT covered -- see blind spots "
    "below)",
    rd.RERUN_BANNER,
    "   Compiling bloomery-daemon v0.1.0 (/clone/crates/bloomery-daemon)",
    "    Finished `test` profile [unoptimized + debuginfo] target(s) in "
    "41.53s",
    "     Running tests/pager_obligation_test.rs",
    "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 14 filtered "
    "out; finished in 0.02s",
    "run: r-new  pid: 4242  exe: /t/pager_obligation_test-abc  events: 812  "
    "threads: 2  exit: 0",
    "driver reported: run: r-new  pid: 4242  exe: "
    "/t/pager_obligation_test-abc  events: 812  threads: 2  exit: 0",
    "--- verdict ---",
    "run: r-new",
    "trace: /store/traces/r-new.db",
    "env: unchanged (94 variables compared; not compared: OLDPWD, PWD, "
    "SENSORIUM_DIR, SHLVL, _)  the recorder's own, also not compared: "
    "RUSTC_WORKSPACE_WRAPPER, SENSORIUM_FOCUS",
    "exit: rerun 0   original 0",
    "A r-orig: 2 thread(s)",
    "B r-new: 2 thread(s)",
    "verdict: MATCH -- identical causal streams (406 events): the same "
    "sequence of (file, qualname, kind) for CALL/RETURN/RAISE/HANDLED on the "
    "main thread; values, timing, and LINE events were not compared",
    "threads: 1 recorded fingerprint(s) compared outside its asyncio tasks, "
    "all matching",
    "tasks: 1 task stream(s) compared by content, all matching; the ordering "
    "between tasks is not compared",
    "refocus verdict: MATCH -- every recorded thread produced the identical "
    "CALL/RETURN/RAISE/HANDLED sequence",
    "licence: verified against r-orig on exactly these points, and no "
    "others:",
    "  - identical call shape across 1 compared fingerprint(s), holding 406 "
    "causal event(s)",
    "  - 37 source file(s) unchanged by content",
    "  - 94 environment variable(s) compared and unchanged in the "
    "environment the rerun executed under; not compared: OLDPWD, PWD, "
    "SENSORIUM_DIR, SHLVL, _",
    "  - no thread started besides the main one, and none left running when "
    "recording stopped",
    *BLIND_SPOTS,
    "checks that could not run on this pair -- the recorder declares it does "
    "not produce them, so nothing here is evidence either way:",
    "  - output: unverifiable (not recorded)",
    "  - children: unverifiable (not witnessed)",
])

DIVERGED_ANSWER = "\n".join([
    "refocus-of: r-orig   cmd: /d/cargo-sensorium --refocus-of r-orig "
    "--focus the_refusal_advises_a_window_that_actually_places test",
    "cwd: /clone",
    "focus: the_refusal_advises_a_window_that_actually_places   window: -",
    "source: unchanged (37 file(s) compared by content)",
    rd.RERUN_BANNER,
    "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 3 filtered "
    "out; finished in 0.31s",
    "--- verdict ---",
    "run: r-new",
    "trace: /store/traces/r-new.db",
    "env: unchanged (94 variables compared; not compared: OLDPWD, PWD, "
    "SENSORIUM_DIR, SHLVL, _)",
    "exit: rerun 0   original 0",
    "verdict: DIVERGED at causal step 1",
    "  common  e1 CALL    main  (src/main.rs)",
    "  A:      e2 CALL    first_path  (src/main.rs)",
    "  B:      e4 CALL    other  (src/main.rs)",
    "drill into A: sensorium tree r-orig --around e2",
    "threads: not compared -- the compared thread already diverged",
    "refocus verdict: DIVERGED -- the compared thread took a different path. "
    "r-new is a DIFFERENT execution than r-orig; it is still queryable, "
    "every `sensorium info r-new` says so, and nothing it shows is a fact "
    "about r-orig",
    *BLIND_SPOTS,
    "checks that could not run on this pair -- the recorder declares it does "
    "not produce them, so nothing here is evidence either way:",
    "  - output: unverifiable (not recorded)",
    "  - children: unverifiable (not witnessed)",
])

#: `corpus/rust/refocus_refused_many` pins this sentence and its exit 2.
PRE_RERUN_REFUSAL_ANSWER = (
    "error: cannot refocus r-orig: run r-orig is one of 2 processes of its "
    "invocation (test binaries and doctests); refocus needs an invocation "
    "with a single-target selector (--lib, --test X, --bin X) so one trace "
    "is the answer; nothing was re-run\n"
    "no rerun was attempted; `cargo sensorium --focus ... test|run` will "
    "record a fresh, UNVERIFIED trace if that is what you want\n")

REFUSED_AFTER_ANSWER = "\n".join([
    "refocus-of: r-orig   cmd: /d/cargo-sensorium --refocus-of r-orig",
    "cwd: /clone",
    "focus: x   window: -",
    "source: unchanged (37 file(s) compared by content)",
    rd.RERUN_BANNER,
    "error[E0308]: mismatched types",
    "refocus verdict: REFUSED -- the re-run produced no trace linked to "
    "r-orig (driver exit 101); see the driver's output above",
    *BLIND_SPOTS,
])


# -- the refocus parser -----------------------------------------------------


def test_a_MATCH_answer_is_read_field_by_field():
    """The one answer every other reading hangs off. A parser that missed
    the verdict word would leave H3 counting `None`s, and one that missed
    the new run id would leave the pair unfindable."""
    p = rd.parse_refocus(MATCH_ANSWER)
    assert p["refocus_of"] == "r-orig"
    assert p["new_run"] == "r-new"
    assert p["new_trace"] == "/store/traces/r-new.db"
    assert p["verdict_word"] == "MATCH"
    assert p["cwd"] == "/clone"
    assert p["focus"] == ["missing_stats_is_a_contract_violation_not_a_reply"]
    assert p["window"] == "-"
    assert p["diff_events"] == 406
    assert p["threads_line"].startswith("threads: 1 recorded")
    assert p["tasks_line"].startswith("tasks: 1 task stream")
    assert p["driver_run_lines"] == [
        "run: r-new  pid: 4242  exe: /t/pager_obligation_test-abc  "
        "events: 812  threads: 2  exit: 0"]


def test_the_licence_bullets_stop_at_the_blind_spot_block():
    """The failure this parser exists to avoid. `licence:` is followed by
    its verified facts as `  - ` bullets, and the categorical blind-spot
    block follows in the SAME shape; a scan that took every bullet in the
    answer would report the recorder's blind spots as points the licence
    verified, and H4's count would grow by nine on every pair."""
    p = rd.parse_refocus(MATCH_ANSWER)
    assert p["licence"] == "granted"
    assert len(p["licence_facts"]) == 4
    assert p["licence_facts"][0].startswith("identical call shape across 1")
    assert p["licence_facts"][-1].startswith("no thread started besides")
    assert not any("child process" in f for f in p["licence_facts"])
    assert not any("blind" in f for f in p["licence_facts"])


def test_the_two_unverifiable_markers_are_their_own_list():
    """§1.4's rule: an UNVERIFIABLE check is never counted as verified. The
    parser keeps them in a field of their own from the first read, so no
    later arithmetic can fold them into the verified facts."""
    p = rd.parse_refocus(MATCH_ANSWER)
    assert p["unverifiable"] == [rd.UNVERIFIABLE_OUTPUT,
                                 rd.UNVERIFIABLE_CHILDREN]
    assert rd.UNVERIFIABLE_OUTPUT not in p["licence_facts"]
    counts = rd.licence_counts(p)
    assert counts["output_unverifiable"] is True
    assert counts["children_unverifiable"] is True
    assert counts["verified_facts"] == 4
    assert counts["unverifiable_checks"] == 2
    # The two numbers exist side by side and nothing here adds them.
    assert counts["verified_facts"] != counts["unverifiable_checks"]


def test_source_env_and_exit_are_three_separate_checks():
    """H4's three checks that RAN. Each is verified, not verified, or could
    not run, and `unverifiable` is never read as `unchanged` -- the bug
    class the licence code itself names."""
    p = rd.parse_refocus(MATCH_ANSWER)
    c = rd.licence_counts(p)
    assert (c["source_status"], c["source_verified"]) == ("unchanged", True)
    assert (c["env_status"], c["env_verified"]) == ("unchanged", True)
    assert c["exit_verified"] is True
    assert p["exit_rerun"] == "0" and p["exit_original"] == "0"


def test_an_unverifiable_source_line_is_not_a_verified_one():
    """`source: unverifiable -- the original trace records no source
    digests` is a check that could not run. Read as `unchanged` it would be
    counted as a check that passed, which is the failure §1.4 forbids by
    name."""
    text = MATCH_ANSWER.replace(
        "source: unchanged (37 file(s) compared by content; data files, "
        "untraced code and installed dependencies are NOT covered -- see "
        "blind spots below)",
        "source: unverifiable -- the original trace records no source "
        "digests (recorded before they existed), so sensorium cannot tell "
        "whether the code changed")
    c = rd.licence_counts(rd.parse_refocus(text))
    assert c["source_status"] == "unverifiable"
    assert c["source_verified"] is False


def test_a_changed_environment_is_read_as_changed():
    """The other direction: `env: CHANGED` must not read as unchanged. The
    Rust env line also carries the recorder's own uncompared names appended
    after two spaces, so the status is taken from the START of the line."""
    text = MATCH_ANSWER.replace(
        "env: unchanged (94 variables compared",
        "env: CHANGED since the original run -- 1 variable(s) differ: TZ  "
        "(names only)   was: env: unchanged (94 variables compared")
    c = rd.licence_counts(rd.parse_refocus(text))
    assert c["env_status"] == "CHANGED" and c["env_verified"] is False


def test_a_differing_exit_status_is_not_verified():
    """The exit check is read off the printed line, not inferred from the
    verdict: a MATCH whose two runs ended differently still withholds."""
    text = MATCH_ANSWER.replace("exit: rerun 0   original 0",
                                "exit: rerun 101   original 0")
    p = rd.parse_refocus(text)
    assert p["exit_status_equal"] is False
    assert rd.licence_counts(p)["exit_verified"] is False


def test_a_WITHHELD_licence_yields_caveats_and_no_facts():
    """A withheld licence lists the checks that say the MATCH is not a
    statement about the run as a whole. Counted as verified they would turn
    the strongest evidence against a pair into evidence for it."""
    text = MATCH_ANSWER.replace(
        "licence: verified against r-orig on exactly these points, and no "
        "others:",
        "licence: WITHHELD -- this MATCH is about call shape, and these "
        "checks say it is not a statement about the run as a whole:")
    p = rd.parse_refocus(text)
    assert p["licence"] == "WITHHELD"
    assert p["licence_facts"] == []
    assert len(p["licence_caveats"]) == 4
    assert rd.licence_counts(p)["licence"] == "WITHHELD"


def test_a_DIVERGED_answer_carries_its_step_and_both_sides():
    """H3 records a DIVERGED with its divergent event. `corpus/rust/
    refocus_diverged` pins these three rows; a parser that read only the
    step number would leave the finding without the fact that names it."""
    p = rd.parse_refocus(DIVERGED_ANSWER)
    assert p["verdict_word"] == "DIVERGED"
    assert p["diverged_step"] == 1
    sides = {r["side"]: r for r in p["step_rows"]}
    assert sides["common"]["qualname"] == "main"
    assert (sides["A"]["event"], sides["A"]["qualname"]) == (2, "first_path")
    assert (sides["B"]["event"], sides["B"]["qualname"]) == (4, "other")
    assert sides["B"]["kind"] == "CALL"


def test_a_pre_rerun_refusal_is_told_apart_from_one_after_the_rerun():
    """H1 counts pre-rerun refusals (exit 2, nothing was re-run); §1's kill
    2 is a REFUSED AFTER the rerun (exit 3, the driver DID run). Collapsing
    them would either stop the rung on a mistyped focus or hide the STOP."""
    before = rd.parse_refocus(PRE_RERUN_REFUSAL_ANSWER)
    assert before["pre_rerun_refusal"].endswith("nothing was re-run")
    assert before["pre_rerun_refusal_run"] == "r-orig"
    assert before["refused_after_rerun"] is None
    # The banner the CLI prints immediately before it launches the child is
    # absent: nothing was re-run, which is what the sentence claims.
    assert rd.RERUN_BANNER not in PRE_RERUN_REFUSAL_ANSWER

    after = rd.parse_refocus(REFUSED_AFTER_ANSWER)
    assert after["pre_rerun_refusal"] is None
    assert after["verdict_word"] == "REFUSED"
    assert after["refused_after_rerun"].startswith("the re-run produced no "
                                                   "trace linked to r-orig")
    assert rd.RERUN_BANNER in REFUSED_AFTER_ANSWER
    assert rd.DRIVER_EXIT.search(REFUSED_AFTER_ANSWER).group("rc") == "101"


def test_a_build_failure_prints_no_libtest_summary():
    """H2's discriminator, on the two answers side by side: a re-run that
    COMPLETED printed `test result:`, and one whose focused unit did not
    compile printed none. Reading the CLI's exit instead would call a
    DIVERGED an incomplete build."""
    assert rd.test_results(MATCH_ANSWER)[0]["passed"] == 1
    assert rd.test_results(REFUSED_AFTER_ANSWER) == []


def test_cargos_own_build_time_is_read_in_both_spellings():
    """H6's second reading. `1m 02s` is exactly the build long enough to be
    worth reporting, and a parser that read only `12.34s` would drop it."""
    assert rd.cargo_finished_seconds(MATCH_ANSWER) == [41.53]
    assert rd.cargo_finished_seconds(
        "    Finished `test` profile [unoptimized] target(s) in 1m 02s\n"
    ) == [62.0]
    assert rd.cargo_finished_seconds("nothing here") == []


# -- `watch` ----------------------------------------------------------------


def test_W3s_class_is_the_no_match_branch_E9_has_no_row_for():
    """§1.3's one token that necessarily differs from E9's. `watch` takes
    its `_no_match` branch on a single-`--exact` trace, prints this line and
    returns 1. E9's four-class table would leave the class `None`, and H5
    would report `not satisfied`-as-predicted as a miss."""
    text = ("error: no recorded code matches --at 'pager_with_model'\n"
            "this trace recorded 12 code object(s):\n"
            "  pager_obligation_test:missing_stats_is_a_contract_violation"
            "_not_a_reply\n")
    p = rd.parse_watch(text)
    assert p["verdict_class"] == "no recorded code matches"
    assert p["classes"] == ["no recorded code matches"]
    assert p["recorded_code_objects"] == 12
    assert p["no_match_line"].endswith("--at 'pager_with_model'")


def test_the_four_E9_classes_still_read_the_same():
    """The fifth class is an ADDITION. A table that replaced the four would
    leave W1 and W4 unreadable."""
    sat = ("sites: 5   evaluated: 2   hits: 2   not-captured: 3   errors: 0\n"
           "verdict: SATISFIED at 2 of the 2 site(s) the predicate could be "
           "evaluated at\n")
    p = rd.parse_watch(sat)
    assert p["verdict_class"] == "SATISFIED"
    assert (p["sites"], p["evaluated"], p["hits"], p["not_captured"]) == (
        5, 2, 2, 3)
    assert p["no_match_line"] is None


def test_two_verdict_sentences_leave_the_class_null():
    """E9's rule, preserved through the widening: a text carrying two
    classes is a defect in the command, not a reading to be resolved by
    taking the first."""
    text = ("verdict: SATISFIED at 1 of the 1 site(s)\n"
            "error: no recorded code matches --at 'x'\n")
    p = rd.parse_watch(text)
    assert sorted(p["classes"]) == ["SATISFIED", "no recorded code matches"]
    assert p["verdict_class"] is None


# -- the fingerprint tables and the discriminator ---------------------------


def _trace(path: Path, main: tuple, tasks: list) -> Path:
    """A trace with just the two fingerprint tables the discriminator reads.

    Built rather than recorded: the discriminator's whole job is arithmetic
    over these two tables, and a fixture that had to be produced by a build
    could not be run in this suite at all.
    """
    con = sqlite3.connect(path)
    con.execute("create table fingerprints (thread_id integer primary key, "
                "hash text not null, n_events integer not null)")
    con.execute("create table task_fingerprints (task_id integer primary "
                "key, name text, hash text not null, n_events integer not "
                "null)")
    con.execute("insert into fingerprints values (?, ?, ?)",
                (rd.MAIN_SERIAL, main[0], main[1]))
    for tid, (name, h, n) in enumerate(tasks, start=2):
        con.execute("insert into task_fingerprints values (?, ?, ?, ?)",
                    (tid, name, h, n))
    con.commit()
    con.close()
    return path


def test_the_main_stream_is_the_fingerprints_row_and_workers_are_tasks(
        tmp_path):
    """The Rust converter writes MAIN to `fingerprints` and every spawned
    thread to `task_fingerprints` (`convert/frames.rs:161,504`). A reading
    that took only `fingerprints` would be blind to exactly the four worker
    threads §1.2's hazard is about."""
    db = _trace(tmp_path / "a.db", ("mainhash", 100),
                [("w1", "h1", 6), ("w2", "h2", 4), ("w3", "h3", 0),
                 ("w4", "h4", 0)])
    f = rd.fingerprint_tables(db)
    assert f["main_hash"] == "mainhash" and f["main_events"] == 100
    assert f["task_count"] == 4
    assert f["task_events_total"] == 10
    assert f["task_partition"] == [0, 0, 4, 6]


def test_a_different_partition_of_the_same_total_is_the_named_hazard(
        tmp_path):
    """§1.4's amendment (2), the hazard half: the scheduler split the same
    ten requests differently, so the workers' per-task fingerprints moved
    while their TOTAL and the MAIN stream did not. Read as a finding, this
    would stop the rung on the subject's own nondeterminism, which §1.2
    already accounts for."""
    a = _trace(tmp_path / "a.db", ("mainhash", 100),
               [("w", "h1", 6), ("w", "h2", 4), ("w", "h3", 0),
                ("w", "h4", 0)])
    b = _trace(tmp_path / "b.db", ("mainhash", 100),
               [("w", "h5", 5), ("w", "h6", 5), ("w", "h7", 0),
                ("w", "h8", 0)])
    d = rd.discriminate(a, b, rd.HAZARD_TESTS[0])
    assert d["total_causal_events_preserved"] is True
    assert d["main_fingerprint_matches"] is True
    assert d["four_worker_tasks"] is True
    assert d["class"] == "hazard"
    assert d["classification_caveats"] == []
    assert d["partition_original"] != d["partition_new"]


def test_a_changed_total_is_H3s_finding(tmp_path):
    """The finding half: work that APPEARED or vanished is not a different
    partition of the same total, and §1.2 offers no prior explanation for
    it."""
    a = _trace(tmp_path / "a.db", ("mainhash", 100),
               [("w", "h1", 6), ("w", "h2", 4)])
    b = _trace(tmp_path / "b.db", ("mainhash", 100),
               [("w", "h5", 6), ("w", "h6", 5)])
    d = rd.discriminate(a, b, rd.HAZARD_TESTS[1])
    assert d["total_causal_events_preserved"] is False
    assert d["class"] == "finding"


def test_a_moved_MAIN_stream_is_H3s_finding(tmp_path):
    """The other half of the same amendment: the test body itself took a
    different path. The workers' total is preserved here, so a
    discriminator that checked only the total would excuse a real
    divergence."""
    a = _trace(tmp_path / "a.db", ("mainhash", 100),
               [("w", "h1", 6), ("w", "h2", 4)])
    b = _trace(tmp_path / "b.db", ("OTHERHASH", 100),
               [("w", "h5", 5), ("w", "h6", 5)])
    d = rd.discriminate(a, b, rd.HAZARD_TESTS[2])
    assert d["total_causal_events_preserved"] is True
    assert d["main_fingerprint_matches"] is False
    assert d["class"] == "finding"


def test_a_task_count_that_is_not_four_is_reported_beside_the_class(
        tmp_path):
    """Where §1 is silent. Its sentence names "the four worker tasks"; a
    pair with some other number does not meet that premise, and the
    instrument publishes the fact rather than folding it into the class or
    dropping it."""
    a = _trace(tmp_path / "a.db", ("mainhash", 100), [("w", "h1", 10)])
    b = _trace(tmp_path / "b.db", ("mainhash", 100), [("w", "h2", 10)])
    d = rd.discriminate(a, b, rd.HAZARD_TESTS[0])
    assert d["four_worker_tasks"] is False
    assert d["task_count_equal"] is True
    assert d["classification_caveats"], "the premise failure is not reported"
    assert "FOUR worker tasks" in d["classification_caveats"][0]


def test_the_discriminator_knows_which_tests_it_may_be_asked_about():
    """§1.2 names three tests and no others. The list is carried here so a
    caller cannot excuse a fourth test's DIVERGED with an explanation §1
    did not pre-register for it."""
    assert len(rd.HAZARD_TESTS) == 3
    assert all(n.startswith(("the_", "unmeasured_")) for n in rd.HAZARD_TESTS)
    assert "unmeasured_vram_advises_nothing_rather_than_a_byte_derived_" \
           "guess" not in rd.HAZARD_TESTS
    assert rd.WORKER_COUNT == 4


# -- the pair rule ----------------------------------------------------------


def _pair_trace(path: Path, refocus_of, start_ts) -> None:
    con = sqlite3.connect(path)
    con.execute("create table meta (key text primary key, value text)")
    # JSON-encoded, as `store.db.set_meta` and the Rust converter write it:
    # a run id sits in the column as a QUOTED string.
    if refocus_of is not None:
        con.execute("insert into meta values ('refocus_of', ?)",
                    (json.dumps(refocus_of),))
    if start_ts is not None:
        con.execute("insert into meta values ('start_ts', ?)",
                    (json.dumps(start_ts),))
    con.commit()
    con.close()


def test_the_pair_is_the_one_trace_linked_AND_started_after_the_launch(
        tmp_path):
    """§1.4's pair rule. Without the timestamp half, a SECOND refocus of one
    original finds the FIRST one's trace as well as its own -- and "more
    than one" is a refusal, so every later refocus of any run would fail
    permanently."""
    _pair_trace(tmp_path / "old.db", "r-orig", 100.0)
    _pair_trace(tmp_path / "new.db", "r-orig", 300.0)
    _pair_trace(tmp_path / "other.db", "r-else", 300.0)
    _pair_trace(tmp_path / "plain.db", None, 300.0)
    got = rd.pair_candidates(tmp_path, "r-orig", launched_at=200.0)
    assert got["qualifying"] == ["new"]
    assert got["linked"] == ["new", "old"]
    assert got["n"] == 1


def test_a_trace_with_no_start_ts_is_EXCLUDED_and_not_assumed_recent(
        tmp_path):
    """It cannot be shown to be this re-run's. Assumed recent it would make
    the pair ambiguous, and the record would report a REFUSED by count on a
    pair that was fine."""
    _pair_trace(tmp_path / "a.db", "r-orig", None)
    _pair_trace(tmp_path / "b.db", "r-orig", 300.0)
    got = rd.pair_candidates(tmp_path, "r-orig", launched_at=200.0)
    assert got["qualifying"] == ["b"]


def test_zero_and_two_qualifying_traces_are_both_visible(tmp_path):
    """The two shapes of the refusal: none at all, and more than one. Both
    are counted, and the count is what the phase reports -- never a guess at
    which trace was meant."""
    assert rd.pair_candidates(tmp_path, "r-orig", 0.0)["n"] == 0
    _pair_trace(tmp_path / "a.db", "r-orig", 300.0)
    _pair_trace(tmp_path / "b.db", "r-orig", 301.0)
    assert rd.pair_candidates(tmp_path, "r-orig", 200.0)["n"] == 2


# -- the clone's own sources ------------------------------------------------


SAMPLE_RS = '''\
mod common;

use common::pager::fresh_dir;

#[test]
fn first_test() {
    assert!(true);
}

#[test]
fn second_test() {
    let dir = fresh_dir("x");
}

fn not_a_test() {}
'''


def test_the_enumeration_finds_the_fn_line_not_the_attribute_line(tmp_path):
    """§1.1's line is the `fn`'s own line, one-based. An enumeration that
    reported the `#[test]` line would differ from the locked table on every
    row and refuse a clone that is exactly right."""
    (tmp_path / "pager_test.rs").write_text(SAMPLE_RS)
    got = rd.enumerate_tests(tmp_path, ["pager_test"])
    assert got["rows"] == [("pager_test", 6, "first_test"),
                           ("pager_test", 11, "second_test")]
    assert got["total"] == 2
    assert got["counts"] == {"pager_test": 2}
    assert got["ignore_attrs"] == 0 and got["should_panic_attrs"] == 0


def test_an_ignored_test_is_COUNTED_because_exact_would_not_run_it(tmp_path):
    """§1.1 rests on there being none: libtest's `--exact <name>` does not
    run an ignored test unless `--ignored` is given, so an ignored test
    would have to be pre-registered as EXCLUDED and N would drop by one. A
    count that missed it would leave the runner measuring 61 names of which
    one never ran."""
    (tmp_path / "pager_test.rs").write_text(
        SAMPLE_RS.replace("#[test]\nfn second_test",
                          "#[test]\n#[ignore]\nfn second_test"))
    got = rd.enumerate_tests(tmp_path, ["pager_test"])
    assert got["ignore_attrs"] == 1
    assert got["rows"][1] == ("pager_test", 12, "second_test")
    assert got["per_file"]["pager_test"]["tests"][1]["attrs"] == [
        "#[test]", "#[ignore]"]


def test_a_missing_file_is_missing_and_not_an_empty_one(tmp_path):
    """Zero tests in a file that exists and zero in a file that does not are
    different facts about the clone; a count of 0 for both would read as the
    first."""
    got = rd.enumerate_tests(tmp_path, ["pager_test"])
    assert got["missing_files"] and got["total"] == 0
    assert got["counts"] == {"pager_test": None}


def test_the_table_diff_names_rows_and_checks_the_ORDER(tmp_path):
    """§1's pass-1 order IS §1.1's order. A table that agreed as a set but
    not as a sequence would run the 61 in an order the pre-registration does
    not name, and the first (cold-build) invocation would be a different
    test than the record says."""
    doc = [("f", 1, "a"), ("f", 2, "b")]
    assert rd.table_diff(doc, doc)["equal"] is True
    flipped = rd.table_diff([("f", 2, "b"), ("f", 1, "a")], doc)
    assert flipped["equal"] is False and flipped["same_set"] is True
    assert flipped["same_order"] is False
    moved = rd.table_diff([("f", 9, "a"), ("f", 2, "b")], doc)
    assert moved["line_moved"] == ["a: clone ('f', 9) vs §1.1 ('f', 1)"]
    extra = rd.table_diff(doc + [("f", 3, "c")], doc)
    assert extra["only_in_the_clone"] == ["f:3 c"]
    assert extra["only_in_the_document"] == []


# -- the shim census --------------------------------------------------------


def test_the_shim_census_counts_entries_and_bytes(tmp_path):
    """H6's census, `rt_build.rs:207-211`."""
    shim = tmp_path / "sensorium" / "shim"
    shim.mkdir(parents=True)
    (shim / "a").write_bytes(b"x" * 10)
    (shim / "b").mkdir()
    (shim / "b" / "c").write_bytes(b"y" * 5)
    got = rd.shim_census(tmp_path)
    assert got["entries"] == 2 and got["bytes"] == 15
    assert got["names"] == ["a", "b"] and got["exists"] is True


def test_a_shim_directory_that_is_not_there_is_None_and_not_zero(tmp_path):
    """A target the run never keyed a shim into and one that keyed a shim
    and left it empty are different facts; `0` for both would report the
    first as the second."""
    got = rd.shim_census(tmp_path)
    assert got["exists"] is False
    assert got["entries"] is None and got["bytes"] is None
