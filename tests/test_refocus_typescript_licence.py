"""What a TypeScript pair's licence rests on: the two environment sets, the
two exit clauses, and the words the verdict says them in.

Split from `tests/test_refocus_typescript.py` -- which owns the refusals,
the re-run, the pair lookup and the stamps -- because that file stands at
783 of this repository's 800-line ceiling and this task's tests are sixty
lines of their own. The fixtures are shared (`tests/refocus_ts_fixtures.py`),
so both files describe ONE recording and not two.

The subject here is the difference between a check that PASSED and a check
that was never made. A vitest container's own `exit_status` is null on both
sides of every pair this recorder writes (`exit_status_basis: unwitnessed`),
so the shared clause over it compares null with null, finds them equal and
says nothing -- which is why the branch has clauses of its own over the two
endings somebody really did observe: `harness_exit`, which the driver
waited for, and `exit_self_reported`, which the container said of itself on
the way out.

PRE-REGISTERED MUTATIONS (task 4, step 5), each with the test that catches
it:

* `is_recorder_key` returns False for everything ->
  `test_the_env_line_names_the_recorders_own_variables_and_grants` (the
  fixture's `SENSORIUM_SPOOL` differs by construction, so the licence is
  withheld on the recorder's own footprint).
* `refocus_world._env_diff` appends the harness keys to `changed` ->
  the same test (`VITEST_POOL_ID` withholds).
* `exit_clauses` reads `exit_status` instead of `harness_exit` ->
  `test_two_harnesses_that_ended_differently_withhold_and_name_both`.
* the fact is emitted when a side records no `harness_exit` ->
  `test_a_missing_harness_exit_is_a_caveat_and_never_a_fact`.
"""
from sensorium.query import refocus_typescript
from sensorium.query.refocus_typescript import exit_clauses
from sensorium.query.vocab import TYPESCRIPT
from tests.refocus_ts_fixtures import (ORIG_ENV, PAIR, PAIR_ENV, _drive,
                                       _never, args, original, refuse)

#: The two endings a pair agrees on, as the fixtures write them: the driver
#: waited for the harness, and the container reported the signal its pool
#: killed it with. Built here as literals rather than read off a trace, so
#: a fixture that quietly changed shape would break these tests rather than
#: move what they assert.
WAITED_0 = {"status": 0, "signal": None, "basis": "waited"}
WAITED_1 = {"status": 1, "signal": None, "basis": "waited"}
SELF_SIGTERM = {"code": None, "signal": "SIGTERM"}
SELF_CODE_1 = {"code": 1, "signal": None}
AGREED = {"harness_exit": WAITED_0, "exit_self_reported": SELF_SIGTERM}
EXIT_FACT = "harness exit equal (0, waited); container endings equal"


def _licence_points(out: str) -> list[str]:
    """The bullets under `licence: verified against ...`, in order.

    Read off the transcript rather than out of the assessment dict, because
    what this file is about is what a READER is told: a fact the assessment
    holds and the report never prints is not a point the licence rests on
    as far as anyone can see.
    """
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("licence: verified against "):
            break
    else:
        raise AssertionError("no granted licence in this transcript")
    points = []
    for line in lines[i + 1:]:
        if not line.startswith("  - "):
            break
        points.append(line[4:])
    return points


# -- the environment's two sets --------------------------------------------
def test_the_env_line_names_the_recorders_own_variables_and_grants(
        tmp_path, monkeypatch, capsys):
    """The fixture's pair differs on exactly two variables, one from each
    set that never withholds: `SENSORIUM_SPOOL` (the recorder mints one per
    invocation) and `VITEST_POOL_ID` (the pool hands out whichever slot is
    free). Both are NAMED -- neither is hidden behind a count -- and the
    licence is granted, because neither is input to what the program
    computes."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out

    env = next(ln for ln in out.splitlines() if ln.startswith("env: "))
    assert env.startswith("env: unchanged outside harness set 1")
    assert "1 harness variable(s) differ: VITEST_POOL_ID" in env
    assert ("the recorder's own, also not compared: SENSORIUM_SPOOL, "
            "SENSORIUM_TIER") in env
    assert "licence: verified against " in out
    assert "WITHHELD" not in out


def test_a_world_variable_that_changed_withholds_and_names_itself(
        tmp_path, monkeypatch, capsys):
    """`HOME` belongs to no set: the default stands, and a program that
    reads it got different input."""
    _drive(tmp_path, monkeypatch,
           pairs=[(PAIR, {"env": {**PAIR_ENV, "HOME": "/elsewhere"}})])
    out = capsys.readouterr().out

    assert "env: CHANGED since the original run" in out
    assert "1 variable(s) differ: HOME" in out
    assert "licence: WITHHELD" in out


def test_a_name_that_merely_resembles_a_harness_member_still_withholds(
        tmp_path, monkeypatch, capsys):
    """`VITEST_POOL_IDX` is not `VITEST_POOL_ID`. Harness set 1 is exact
    membership, so a family resemblance exempts nothing -- an exemption
    that swallowed a name nobody enumerated would grant a licence over a
    real difference."""
    _drive(tmp_path, monkeypatch,
           pairs=[(PAIR, {"env": {**PAIR_ENV, "VITEST_POOL_IDX": "9"}})])
    out = capsys.readouterr().out

    assert "1 variable(s) differ: VITEST_POOL_IDX" in out
    assert "licence: WITHHELD" in out


def test_a_session_key_beside_a_real_change_withholds_and_names_both(
        tmp_path, monkeypatch, capsys):
    """The exempt sets do not cover for each other. A pair launched from
    another terminal AND reading a changed `HOME` is withheld on the
    `HOME`, and the session key is still counted and named beside it --
    the reader is told both facts, and only one of them votes."""
    _drive(tmp_path, monkeypatch,
           pairs=[(PAIR, {"env": {**PAIR_ENV, "HOME": "/elsewhere",
                                  "TMUX": "/tmp/tmux-2,9,1"}})])
    out = capsys.readouterr().out

    env = next(ln for ln in out.splitlines() if ln.startswith("env: "))
    assert "1 variable(s) differ: HOME" in env
    assert "1 session variable(s) differ: TMUX" in env
    assert "licence: WITHHELD" in out


# -- the two exits, as clauses ---------------------------------------------
def test_two_invocations_that_ended_alike_verify_one_fact():
    """Both endings agreed, so the licence gains ONE point naming both --
    not two, because "how the two runs ended" is one question and a reader
    told it twice has to work out whether it is the same answer."""
    assert exit_clauses(dict(AGREED), dict(AGREED)) == ([], [EXIT_FACT])


def test_the_fact_renders_a_harness_killed_by_a_signal_by_its_name():
    """A process killed by a signal chose no status, so `(None, waited)`
    would be a number nobody set."""
    killed = {"harness_exit": {"status": None, "signal": "SIGTERM",
                               "basis": "waited"},
              "exit_self_reported": SELF_SIGTERM}
    caveats, facts = exit_clauses(dict(killed), dict(killed))
    assert caveats == []
    assert facts == ["harness exit equal (signal SIGTERM, waited); "
                     "container endings equal"]


def test_two_harnesses_that_ended_differently_withhold_and_name_both():
    """The clause the container's own `exit_status` cannot carry: null on
    both sides, compared, reads as agreement."""
    caveats, facts = exit_clauses(
        {**AGREED, "exit_status": None},
        {"harness_exit": WAITED_1, "exit_self_reported": SELF_SIGTERM,
         "exit_status": None})
    assert caveats == ["the two invocations' harnesses ended differently: "
                       "exit 0 originally, exit 1 on the rerun"]
    assert facts == []


def test_a_harness_killed_by_a_signal_is_named_beside_a_status():
    caveats, _facts = exit_clauses(
        dict(AGREED),
        {"harness_exit": {"status": None, "signal": "SIGKILL",
                          "basis": "waited"},
         "exit_self_reported": SELF_SIGTERM})
    assert caveats == ["the two invocations' harnesses ended differently: "
                       "exit 0 originally, signal SIGKILL on the rerun"]


def test_two_containers_that_reported_different_endings_withhold():
    """A signal by its name, a code as an exit: the container's record
    carries one or the other and never both."""
    caveats, facts = exit_clauses(
        dict(AGREED),
        {"harness_exit": WAITED_0, "exit_self_reported": SELF_CODE_1})
    assert caveats == ["the two containers reported different endings: "
                       "SIGTERM originally, exit 1 on the rerun"]
    assert facts == []


def test_a_missing_harness_exit_is_a_caveat_and_never_a_fact():
    """An absent record is not an agreement. The side is named, because
    which of the two was not witnessed is the reader's next question."""
    caveats, facts = exit_clauses({"exit_self_reported": SELF_SIGTERM},
                                  dict(AGREED))
    assert caveats == ["the original's harness exit was not recorded"]
    assert facts == []

    caveats, facts = exit_clauses(dict(AGREED),
                                  {"exit_self_reported": SELF_SIGTERM})
    assert caveats == ["the rerun's harness exit was not recorded"]
    assert facts == []


def test_a_container_that_reported_no_ending_is_a_caveat_and_never_a_fact():
    """`exit_self_reported` is absent on a container killed before it could
    observe its own ending -- which is not the same fact as one that ended
    at 0."""
    caveats, facts = exit_clauses({"harness_exit": WAITED_0}, dict(AGREED))
    assert caveats == ["the original's container reported no ending"]
    assert facts == []

    caveats, facts = exit_clauses(dict(AGREED), {"harness_exit": WAITED_0})
    assert caveats == ["the rerun's container reported no ending"]
    assert facts == []


def test_the_containers_own_exit_status_is_never_read():
    """`exit_status` is null with basis `unwitnessed` on every trace this
    recorder writes, and a pair whose two nulls differ (a hand-built trace,
    or a later recorder that witnesses one) must not move these clauses:
    what they are about is what somebody waited for."""
    assert exit_clauses({**AGREED, "exit_status": 0},
                        {**AGREED, "exit_status": 1}) == ([], [EXIT_FACT])


def test_the_pairs_licence_rests_on_the_exit_fact_and_not_on_the_unrun(
        tmp_path, monkeypatch, capsys):
    """The granted licence names the exits it compared, and never the three
    checks it could not run: those are printed and stamped separately, and
    a marker listed as a verified point would claim an empty set had
    agreed."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out

    points = _licence_points(out)
    assert EXIT_FACT in points
    for short in ("output (not recorded)", "children (not witnessed)",
                  "threads (not witnessed)"):
        assert short not in points
    for marker in ("output: unverifiable (not recorded)",
                   "children: unverifiable (not witnessed)",
                   "threads: unverifiable (not witnessed)"):
        assert marker not in points


# -- the words the verdict says it in --------------------------------------
def test_the_four_blind_spots_are_printed_in_order_and_the_retired_one_is_gone(
        tmp_path, monkeypatch, capsys):
    """Rung 4 gave this recorder arguments at a focused site, so the line
    that said they are not read has been false since; what replaces it
    bounds the re-run MECHANISM, which is this branch's own."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out

    assert TYPESCRIPT.refocus_blind_spots == (
        "output not recorded (capabilities.output: false)",
        "the whole recorded invocation was re-run; its other containers "
        "were not compared and stay UNVERIFIED",
        "the harness's worker-slot variables (harness set 1) were not "
        "compared",
        "a worker thread or forked child of the program is its own trace, "
        "unlinked to this pair")
    at = [out.index(f"  - {line}")
          for line in TYPESCRIPT.refocus_blind_spots]
    assert at == sorted(at)
    assert "arguments are not read" not in out


def test_every_refusal_says_a_rerun_may_be_recorded_and_not_that_it_cannot(
        tmp_path, monkeypatch, capsys):
    """`refocus` IS this recorder's now, so the note is the Python and Rust
    shape: nothing was re-run HERE, and the command that would record a
    fresh, unverified invocation is named -- never `sensorium run --focus`,
    which cannot read a TypeScript trace."""
    run, _ = original(tmp_path, monkeypatch)
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    _code, err = refuse(capsys, run, "compute", window="x")
    assert "no rerun was attempted; " in err
    assert "`sensorium ts run --focus <file>:<qualname> -- <harness " \
           "command>` will record a fresh, UNVERIFIED invocation if that " \
           "is what you want" in err
    assert "refocus is not yet" not in err
    assert "sensorium run --focus" not in err


def test_the_note_reaches_a_refusal_raised_after_the_capability_gate(
        tmp_path, monkeypatch, capsys):
    """A second refusal path, so the note is pinned to the TRACE's language
    and not to the one branch that happens to print it first."""
    run, _ = original(tmp_path, monkeypatch,
                      env={**ORIG_ENV, "SENSORIUM_TIER": "off"})
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    _code, err = refuse(capsys, run, "compute")
    assert "no rerun was attempted; " in err
    assert "refocus is not yet" not in err


def test_the_command_refuses_before_it_ever_reaches_the_exit_clauses(
        tmp_path, monkeypatch, capsys):
    """A refusal is not a licence: nothing was compared, so no exit clause
    -- caveat or fact -- may appear in a transcript that re-ran nothing."""
    run, _ = original(tmp_path, monkeypatch)
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute", window="x")
    assert code == 2
    assert "harness exit equal" not in err
    assert "ended differently" not in err


def test_the_transcript_of_a_granted_pair_carries_the_exit_line_too(
        tmp_path, monkeypatch, capsys):
    """The `exit:` line and the exit FACT are two channels for one
    observation, and both are printed: the line says what each side did,
    the fact says the licence rests on their agreeing."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out

    assert "exit: rerun 0 (waited)   original 0 (waited)" in out
    assert EXIT_FACT in _licence_points(out)


def test_a_pair_whose_harness_exits_differ_is_withheld_end_to_end(
        tmp_path, monkeypatch, capsys):
    """The clause reaching `assess` through `world_caveats`, on a real
    pair: a MATCH on call shape whose two harnesses ended differently is
    not a statement about the run as a whole."""
    _drive(tmp_path, monkeypatch,
           pairs=[(PAIR, {"harness_exit": WAITED_1})])
    out = capsys.readouterr().out

    assert "refocus verdict: MATCH" in out
    assert "licence: WITHHELD" in out
    assert ("  - the two invocations' harnesses ended differently: exit 0 "
            "originally, exit 1 on the rerun") in out


def test_a_pair_whose_containers_disagree_is_withheld_end_to_end(
        tmp_path, monkeypatch, capsys):
    _drive(tmp_path, monkeypatch,
           pairs=[(PAIR, {"exit_self_reported": SELF_CODE_1})])
    out = capsys.readouterr().out

    assert "licence: WITHHELD" in out
    assert ("  - the two containers reported different endings: SIGTERM "
            "originally, exit 1 on the rerun") in out


def test_is_recorder_key_says_why_the_three_that_always_differ_are_its_own():
    """The docstring is the register the Rust predicate's is in, and it
    names the three rather than counting them -- `refocus`'s own rule about
    exemptions, applied to the sentence that describes one. `SENSORIUM_FOCUS`
    is not among the three: it differs only when the call deepens the
    focus, so the docstring must say that qualification rather than
    claiming it always differs."""
    doc = refocus_typescript.is_recorder_key.__doc__
    for name in ("SENSORIUM_INVOCATION", "SENSORIUM_SPOOL",
                 "SENSORIUM_MANIFEST_DIR"):
        assert name in doc
    assert "SENSORIUM_FOCUS" in doc
    assert "deepens the focus" in doc
    assert "leaves it identical" in doc
    assert "always fires says nothing" in doc
