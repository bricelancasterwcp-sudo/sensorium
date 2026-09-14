"""Two rules the shared licence code gained when a THIRD recorder arrived.

Both are the same move the output and children checks already made, one
signal further on:

* **threads can be unverifiable.** `sensorium-ts` declares
  `capabilities.threads: false` -- a vitest worker is a process, and the
  recorder witnesses no thread of its own -- so the thread bookkeeping the
  licence reads was never written. Reported until now as a witness GAP
  ("recorder ... declares threads not witnessed"), which is a finding
  against the pair and withholds; it is not a finding at all, it is a check
  that could not run. The marker is the honest answer, and it does not vote.
* **harness set 1 beside session set 1.** A vitest pool hands each worker
  its slot number, and a re-run gets another slot. That is bookkeeping about
  where the work ran, never input to what a program computes -- session set
  1's rule, applied to the pool instead of the shell.

Written against the fixture builders rather than a live harness, for
`tests/ts_traces.py`'s reason: a rule test must not depend on Node, vitest
or a transform running.
"""
from sensorium import paths
from sensorium.query import refocus_world
from sensorium.query.refocus_env import (HARNESS_DIFFER, HARNESS_ORDER,
                                         HARNESS_SET, SESSION_EXACT,
                                         SESSION_PREFIXES, is_env_rule_note,
                                         is_harness_key)
from sensorium.query.refocus_world import (UNVERIFIABLE,
                                           UNVERIFIABLE_CHILDREN,
                                           UNVERIFIABLE_ENV,
                                           UNVERIFIABLE_OUTPUT,
                                           UNVERIFIABLE_THREADS, _env_diff,
                                           _env_state, _licence_caveats,
                                           _verified_facts, relicense,
                                           unverifiable_checks,
                                           unverifiable_line)
from sensorium.query.vocab import RUST
from sensorium.store.reader import Trace
from tests.rust_traces import rerunnable_trace
from tests.ts_traces import TS_CAPABILITIES, call, frame, ret, ts_trace


def _open(run: str) -> Trace:
    return Trace.open(paths.traces_dir() / f"{run}.db")


def _ts_pair(tmp_path, monkeypatch) -> tuple[Trace, Trace]:
    """Two TypeScript traces of one call, both declaring threads unwitnessed.

    `TS_CAPABILITIES` already says `threads: False`; it is spelled out in
    the override so the test states the fact it turns on rather than
    depending on a fixture constant staying that way.
    """
    runs = []
    for run_id in ("20260101-000000-ts0001", "20260101-000000-ts0002"):
        runs.append(ts_trace(
            tmp_path, monkeypatch,
            codes=[["/w/app/src/config.ts", "load", 4]],
            frames=[frame(1, 1, 2)],
            events=[call(1000, 1, 4), ret(2000, 1, 1)],
            run_id=run_id,
            capabilities={**TS_CAPABILITIES, "threads": False}))
    return _open(runs[0]), _open(runs[1])


# -- the third marker ------------------------------------------------------

def test_a_recorder_that_declares_threads_unwitnessed_gets_the_marker(
        tmp_path, monkeypatch):
    """The three checks a `sensorium-ts` pair cannot run, in the order
    `unverifiable_checks` asks them: output, children, threads -- and not
    the fourth, which no trace of this pair gives it a reason to add."""
    a, b = _ts_pair(tmp_path, monkeypatch)
    assert unverifiable_checks(a, b) == [UNVERIFIABLE_OUTPUT,
                                         UNVERIFIABLE_CHILDREN,
                                         UNVERIFIABLE_THREADS]
    # The fourth is rule v1's and is asked of the two METAS rather than of
    # a capability, so a pair that declares nothing false never carries it;
    # `tests/test_refocus_redaction.py` is where it is stated.
    assert UNVERIFIABLE == (UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN,
                            UNVERIFIABLE_THREADS, UNVERIFIABLE_ENV)
    assert UNVERIFIABLE_THREADS == "threads: unverifiable (not witnessed)"


def test_info_replays_the_threads_marker_without_repeating_the_word():
    """`unverifiable_line`'s table knows the new name too. A marker it did
    not know would be printed in full, so the line would say
    "unverifiable" twice about one check."""
    assert unverifiable_line([UNVERIFIABLE_THREADS]) == (
        "licence unverifiable: threads (not witnessed)")


def test_the_marker_replaces_the_thread_witness_gap_sentence(
        tmp_path, monkeypatch):
    """The gap sentence is about a recorder that WITNESSES threads and wrote
    no record anyway. Where the recorder declares it witnesses none, saying
    it again as a caveat would withhold the licence for the recorder's own
    declared scope -- the bug class this whole file is arranged around."""
    a, b = _ts_pair(tmp_path, monkeypatch)
    caveats = _licence_caveats(a, b)
    assert not any("declares threads not witnessed" in c for c in caveats)
    assert not any("thread(s) running when recording stopped" in c
                   for c in caveats)
    # ...and the marker is still there, once for the pair, last.
    assert caveats == [UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN,
                       UNVERIFIABLE_THREADS]


def test_a_rust_pair_still_gets_exactly_the_two_old_markers(
        tmp_path, monkeypatch):
    """The discriminating control. `cargo-sensorium` declares
    `threads: true`, so nothing about this pair changed: two markers, and
    the thread bookkeeping is read exactly as it was."""
    run = rerunnable_trace(tmp_path, monkeypatch)
    t = _open(run)
    assert t.declares("threads") is True
    assert unverifiable_checks(t, t) == [UNVERIFIABLE_OUTPUT,
                                         UNVERIFIABLE_CHILDREN]
    assert UNVERIFIABLE_THREADS not in _licence_caveats(t, t)


def test_the_three_markers_alone_still_grant_the_licence(
        tmp_path, monkeypatch):
    """A check that could not run is not a finding against the pair, so it
    does not vote. The third marker joins the other two in that.

    And what the granted licence then RESTS on may not include the thread
    sentence: `relicense` takes the marker out of the withholding decision
    and calls `_verified_facts`, so without a guard there a pair whose
    recorder declares it witnesses no thread would positively assert "no
    thread started besides the main one" over bookkeeping nobody wrote --
    a check that never ran, reported as a check that passed.
    """
    a, b = _ts_pair(tmp_path, monkeypatch)
    assessment = {"verdict": "MATCH", "thread_scope": "",
                  "caveats": [UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN,
                              UNVERIFIABLE_THREADS],
                  "licence": "withheld", "verified": []}
    out = relicense(assessment, a, b, ["3 source file(s) unchanged"])
    assert out["caveats"] == []
    assert out["licence"] == "granted"
    assert "3 source file(s) unchanged" in out["verified"]
    assert not any("thread started" in f for f in out["verified"])
    # ...and the call-shape fact it DOES rest on is still first, so the
    # world's facts splice in after it exactly as `assess` splices them.
    assert out["verified"][0].startswith("identical call shape across")


def test_a_rust_pairs_granted_licence_still_rests_on_the_thread_sentence(
        tmp_path, monkeypatch):
    """The byte-identity fence for the guard above. `cargo-sensorium`
    declares `threads: true`, so the record the sentence reads exists and
    the sentence is the one it always was -- the Rust provenance clause,
    from that recorder's own vocabulary table."""
    run = rerunnable_trace(tmp_path, monkeypatch)
    t = _open(run)
    facts = _verified_facts(t, t, "")
    assert facts[1] == (
        "no thread started besides the main one "
        f"{RUST.thread_origin}, and none left running when recording "
        "stopped")


def test_the_witnessing_side_of_a_mixed_pair_keeps_its_thread_findings(
        tmp_path, monkeypatch):
    """The skip is THIS side's declaration, never the pair's marker.

    The marker fires when EITHER trace declares `threads: false`, so gating
    the per-side loop on it would drop the WITNESSING side's `started` and
    `live_threads` findings -- real findings about a record that exists,
    lost because the other trace came from another recorder. The pair still
    gets the marker once, because one of its two sides cannot be read.
    """
    orig_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[["/w/app/src/config.ts", "load", 4]],
        frames=[frame(1, 1, 2)], events=[call(1000, 1, 4), ret(2000, 1, 1)],
        run_id="20260101-000000-tsmix1",
        capabilities={**TS_CAPABILITIES, "threads": False})
    new_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[["/w/app/src/config.ts", "load", 4]],
        frames=[frame(1, 1, 2)], events=[call(1000, 1, 4), ret(2000, 1, 1)],
        run_id="20260101-000000-tsmix2",
        capabilities={**TS_CAPABILITIES, "threads": True},
        threads_started=1, live_threads=[])
    orig, new = _open(orig_id), _open(new_id)
    assert orig.declares("threads") is False
    assert new.declares("threads") is True

    caveats = _licence_caveats(orig, new)
    assert any(c.startswith("the rerun started 1 thread(s) besides the "
                            "main one") for c in caveats)
    # The declaring-false side says nothing at all: no gap sentence, and no
    # count read off a record it never wrote.
    assert not any(c.startswith("the original") for c in caveats)
    assert not any("declares threads not witnessed" in c for c in caveats)
    # ...and the pair is still marked, once, because one side cannot be read.
    assert caveats.count(UNVERIFIABLE_THREADS) == 1


# -- harness set 1 ---------------------------------------------------------

def test_is_harness_key_is_exact_membership_and_nothing_looser():
    """No prefix, for `is_session_key`'s reason: a family resemblance would
    exempt variables nobody put on the list."""
    assert is_harness_key("VITEST_POOL_ID") is True
    assert is_harness_key("VITEST_WORKER_ID") is True
    assert is_harness_key("VITEST_POOL_IDX") is False
    assert is_harness_key("VITEST") is False
    assert is_harness_key("VITEST_") is False


def test_harness_set_1_is_these_two_names_in_this_order():
    assert HARNESS_SET == 1
    assert HARNESS_ORDER == ("VITEST_POOL_ID", "VITEST_WORKER_ID")


def test_the_two_sets_do_not_overlap():
    """A key in both would be counted and named twice on one line."""
    assert set(HARNESS_ORDER).isdisjoint(SESSION_EXACT)
    assert not any(n.startswith(p)
                   for n in HARNESS_ORDER for p in SESSION_PREFIXES)


def test_a_harness_key_is_partitioned_out_of_the_changed_list():
    """The partition itself, not only its rendering: a differing pool slot
    is on the harness list and on no other, so it never withholds."""
    (changed, relocated, stripped, session, harness,
     uncomparable) = _env_diff({"VITEST_POOL_ID": "1", "A": "x"},
                               {"VITEST_POOL_ID": "2", "A": "x"})
    assert changed == []
    assert harness == ["VITEST_POOL_ID"]
    assert relocated == [] and stripped == [] and session == []
    assert uncomparable == []


def test_the_env_line_names_harness_set_1_and_counts_it(capsys):
    """Counted EXACTLY and named the way the changed names are: an
    exemption whose size and members a reader cannot see is a silent one,
    and the set is versioned in the sentence so it can be argued with."""
    line, caveat, fact = _env_state(
        {"env": {"VITEST_WORKER_ID": "1", "A": "x"}},
        {"VITEST_WORKER_ID": "3", "A": "x"})
    assert line.startswith("env: unchanged outside harness set 1 (")
    assert "2 variables compared" in line
    assert "1 harness variable(s) differ: VITEST_WORKER_ID" in line
    assert caveat is None
    assert "unchanged outside harness set 1 in the environment" in fact
    assert "1 harness variable(s) differ: VITEST_WORKER_ID" in fact


def test_both_sets_are_named_in_one_phrase_session_first():
    """Two exemptions, one `outside ...` phrase, and the counted clauses in
    the same order -- two channels carrying the same names in two orders
    are two sentences to keep in step."""
    line, caveat, fact = _env_state(
        {"env": {"CLAUDE_CODE_SESSION_ID": "a1", "VITEST_POOL_ID": "1",
                 "VITEST_WORKER_ID": "1", "A": "x"}},
        {"CLAUDE_CODE_SESSION_ID": "b2", "VITEST_POOL_ID": "2",
         "VITEST_WORKER_ID": "3", "A": "x"})
    assert line == (
        "env: unchanged outside session set 1 and harness set 1 "
        "(4 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, "
        "SHLVL, _; 1 session variable(s) differ: CLAUDE_CODE_SESSION_ID; "
        "2 harness variable(s) differ: VITEST_POOL_ID, VITEST_WORKER_ID)")
    assert caveat is None
    assert fact == (
        "4 environment variable(s) compared and unchanged outside session "
        "set 1 and harness set 1 in the environment the rerun executed "
        "under; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; "
        "1 session variable(s) differ: CLAUDE_CODE_SESSION_ID; 2 harness "
        "variable(s) differ: VITEST_POOL_ID, VITEST_WORKER_ID")


def test_a_pair_with_neither_set_reads_exactly_as_it_always_did():
    """The fence. Every string printed for a pair that has no harness key
    and no session key is byte for byte the one it was."""
    line, caveat, fact = _env_state({"env": {"A": "x"}}, {"A": "x"})
    assert line == ("env: unchanged (1 variables compared; not compared: "
                    "OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _)")
    assert caveat is None
    assert fact == ("1 environment variable(s) compared and unchanged in "
                    "the environment the rerun executed under; not "
                    "compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _")


def test_the_harness_clause_travels_into_a_withheld_pairs_own_record():
    """`is_env_rule_note` decides which world-facts survive a WITHHELD
    licence, and it already carries the session clause for this reason: a
    trace that kept only the accusation replays less than its own screen
    said. The harness clause is beside it, so it is recognised beside it.
    """
    line, _caveat, fact = _env_state(
        {"env": {"TZ": "UTC", "VITEST_POOL_ID": "1"}},
        {"TZ": "CET", "VITEST_POOL_ID": "2"})
    said = f"1{HARNESS_DIFFER}VITEST_POOL_ID"
    assert line.startswith("env: CHANGED since the original run -- "
                           "1 variable(s) differ: TZ   (names only); ")
    assert said in line
    assert fact == said
    assert is_env_rule_note(fact) is True


def test_refocus_world_reaches_the_moved_licence_helpers():
    """The names the Rust branch used to own, at their shared home. Moved
    rather than copied: a second language needs them, and two copies of a
    licence rule is how two languages come to grant two licences."""
    assert refocus_world.UNVERIFIABLE_KEY == "refocus_licence_unverifiable"
    assert callable(refocus_world.relicense)
    assert callable(refocus_world.stamp_unverifiable)
    assert callable(refocus_world.env_of)
