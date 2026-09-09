"""E4″'s kill rules and its exit codes: `acceptance_e4pp_kills`.

Split out of `test_acceptance_e4pp.py` on 2026-09-08, when the debts slice's
own tests took that file to 843 of an 800-line ceiling, at the seam the
instrument itself was split at the same day: everything here drives
`acceptance_e4pp_kills` -- which gated endpoint missed and on which side
(§1.4's kill 2), whether a `.FAILED` is a STOP or infrastructure (rules 4
and 5), and which shape of exit 9 a run was. No test moved by a character.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4pp as runner                                   # noqa: E402


# --------------------------------------------------------------- the kills

def test_a_KILLED_invocation_is_named_by_the_KILLS_words_not_by_H1():
    stops = runner._stops({
        "numbers_read": True,
        "raw_pass2": {"killed": ["a_pager_can_be_shared_across_threads"],
                      "budget_exhausted": [], "n": 61, "measured": 61},
        "raw_h1": {"partition_as_predicted": False, "granted_n": 60,
                   "n": 61, "expected_granted_n": 57}})
    first = stops[0]
    assert "KILLED" in first
    assert "a number had already been read" in first
    assert "STOP" in first
    assert "kill 1" not in first
    assert any("kill 1" in s for s in stops[1:])


def test_a_kill_BEFORE_any_number_is_named_as_the_INFRASTRUCTURE_kill():
    stops = runner._stops({
        "numbers_read": False,
        "raw_pass2": {"killed": ["x"], "budget_exhausted": [], "n": 61,
                      "measured": 61}})
    assert stops
    assert "infrastructure" in stops[0]
    assert "relaunched from zero" in stops[0]
    assert "STOP" not in stops[0]


@pytest.mark.parametrize("phase, number", [
    ("raw_h2", "H2"), ("raw_h3", "H3"), ("raw_h4", "H4"),
    ("raw_h5", "H5"), ("raw_h6", "H6"), ("raw_h8", "H8")])
def test_a_miss_on_any_gated_phase_is_a_STOP_with_ITS_NUMBER(phase, number):
    """§1.4's kill 2: "a miss on H2, H3, H4, H5, H6 or H8 is a STOP with its
    number"."""
    stops = runner._stops({"numbers_read": True,
                           phase: {"verdict": "STOP", "as_predicted": False,
                                   "gate": "the gate"}})
    assert any(s.startswith(number) for s in stops), stops


def test_a_gated_miss_with_a_WHOLE_reading_is_a_STOP_of_the_subject():
    """The control for the two below: a phase that read everything it asked
    for and simply did not match the gate missed on the side the endpoint
    measures, and the sentence is the one it always was."""
    res = {"numbers_read": True,
           "raw_h3": {"verdict": "STOP", "as_predicted": False,
                      "gate": "the gate", "dropped": []}}
    assert any("This is a STOP of the subject" in s
               for s in runner._stops(res))
    side = runner.stop_sides(res)[0]
    assert (side["declared"], side["derived"]) == ("subject", "subject")
    assert side["agree"] is True


def test_a_gated_miss_the_READER_could_not_make_names_BOTH_sides():
    """E4″ gap 2. The `stop` sentence and the `.FAILED` marker both ended
    "This is a STOP of the subject" because the label hung off the endpoint
    id; on the real run H8's miss was this instrument's -- three green
    return codes and a case that had run. A phase that recorded a reason it
    could not READ something missed on the instrument's side, whatever the
    endpoint is gated on, and §1.4's kill 2 asks for both."""
    res = {"numbers_read": True,
           "raw_h8": {"verdict": "STOP", "as_predicted": False,
                      "gate": "the gate",
                      "dropped": ["`x` is among the 63 name(s) the listing "
                                  "printed under neither spelling"]}}
    stops = runner._stops(res)
    assert any("INSTRUMENT" in s and "under neither spelling" in s
               for s in stops), stops
    # BOTH, never one instead of the other.
    assert any("subject" in s for s in stops), stops
    side = runner.stop_sides(res)[0]
    assert (side["declared"], side["derived"]) == ("subject", "instrument")
    assert side["agree"] is False


def test_a_BLOCKED_reading_is_the_instruments_miss_too():
    """`as_predicted` null -- a short loop, a killed row -- is a reading
    nobody made, and naming it a STOP of the subject reports a finding
    about the tool from a number the run never got."""
    res = {"numbers_read": True,
           "raw_h2": {"verdict": "STOP", "as_predicted": None,
                      "gate": "the gate",
                      "dropped": ["59 of 61 invocation(s) ran"]}}
    side = runner.stop_sides(res)[0]
    assert side["derived"] == "instrument" and side["blocked"] is True


def test_a_miss_on_H7_is_a_STOP_OF_THE_INSTRUMENT_and_says_so():
    """§1.4's kill 2 again: a miss on H7 is distinguished IN THE RECORD from
    a STOP of the subject."""
    stops = runner._stops({"numbers_read": True,
                           "raw_h7": {"verdict": "STOP",
                                      "as_predicted": False,
                                      "gate": "the gate"}})
    assert any("INSTRUMENT" in s for s in stops), stops
    assert any("not of the subject" in s for s in stops), stops


def test_a_phase_that_PASSED_is_no_stop_at_all():
    assert runner._stops({"numbers_read": True,
                          "raw_h2": {"verdict": "PASS",
                                     "as_predicted": True}}) == []


def test_a_KEPT_STORE_that_changed_is_a_STOP():
    stops = runner._stops({"numbers_read": True,
                           "cleanup": {"kept_store_unchanged": False,
                                       "kept_census_differences": ["x"]}})
    assert any("KEPT store" in s for s in stops)


# ============ the exit codes' own two minors (CARRIED-DEBT) ==============

def test_a_DRY_run_KILLED_after_a_reading_is_INFRASTRUCTURE_not_a_STOP():
    """Minor 6. §1.3's words are that a dry run measures nothing about the
    subject, so a dry that fails is infrastructure and never a STOP -- but
    `_infrastructure` looked only at `numbers_read`, and a dry whose row
    was killed after a reading answered False and exited 7. That told the
    controller a FINDING had been made by a run that made none."""
    killed = {"raw_pass2": {"killed": ["a_row"], "budget_exhausted": []}}
    assert runner._infrastructure(dict(killed, dry_run=True,
                                       numbers_read=True)) is True
    # The real run is unchanged: after a number, rule 5 still stands.
    assert runner._infrastructure(dict(killed, numbers_read=True)) is False
    assert runner._infrastructure(dict(killed, numbers_read=False)) is True


@pytest.mark.parametrize("res, shape", [
    ({"dry_run_did_not_check_the_instrument": "…"}, "dry_did_not_check"),
    ({"kill_is_infrastructure": True}, "before_a_number"),
    ({"kill_is_infrastructure": True, "dry_run": True},
     "killed_in_a_dry_run"),
    ({"kill_is_infrastructure": False}, None),
    ({}, None),
])
def test_exit_9s_SHAPES_are_told_apart_in_the_record(res, shape):
    """Minor 7: 9 meant "relaunch from zero" in more than one shape and the
    marker's prose was the only place that said which. A field, so a reader
    -- and the controller -- gets the distinction without parsing English;
    `None` where the run was not an infrastructure kill at all, which is
    itself what a reader of a 7 wants to know."""
    assert runner.infrastructure_shape(res) == shape
    if shape:
        assert shape in runner.INFRASTRUCTURE_SHAPES
        assert runner.INFRASTRUCTURE_SHAPES[shape]


def test_every_named_shape_of_exit_9_is_reachable_from_the_runner():
    """A name in the table that nothing can produce is a sentence a marker
    would never carry -- and one produced with no name in the table would
    print the runner's fallback."""
    produced = {runner.infrastructure_shape(r) for r in (
        {"dry_run_did_not_check_the_instrument": "…"},
        {"kill_is_infrastructure": True},
        {"kill_is_infrastructure": True, "dry_run": True})}
    assert produced == set(runner.INFRASTRUCTURE_SHAPES)
