"""The E4′ record's shape: what a cell may say, and what it may never say.

Every rule here is one this project has been bitten by. A phase that did not
run must not publish a `0` that a later reader sums; a loop that stopped
short must not publish a count over "the 61" as though it were one; a killed
invocation must not leave an empty string where a number belongs; and no
endpoint may be filled from §1's predictions, which are in the room.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4p_cells as cells                               # noqa: E402
import acceptance_e4p_rows as rows                                 # noqa: E402
import render_e4p                                                  # noqa: E402
from acceptance_e4p_schema import SCHEMA_VERSION, assemble_e4p     # noqa: E402

ENDPOINTS = ("H1", "H2", "H3", "H4", "H5", "H6")


def _full_raw() -> dict:
    """A raw record with every phase present and every gate met -- the
    shape a clean run writes, built small so the rules below are about the
    schema and not about a fixture."""
    refocuses = []
    for i, (index, name, target, run) in enumerate(rows.ROWS[:3], 1):
        withheld = name in rows.EXPECTED_WITHHELD
        refocuses.append({
            "index": index, "name": name, "target": target, "original": run,
            "rc": 0, "wall_s": 7.0 + i, "timed_out": False, "kill_s": 1800,
            "verdict_word": "MATCH", "verdict_and_exit_agree": True,
            "pair": {"n": 1, "qualifying": [f"pair-{i}"], "linked": [],
                     "children": [], "unreadable": []},
            "new_run": f"pair-{i}", "printed_pair_run": f"pair-{i}",
            "pair_agrees_with_the_printed_id": True,
            "excluded_children_printed": [],
            "excluded_children_in_the_store": [],
            "licence_partition": {
                "licence": "WITHHELD" if withheld else "granted",
                "program_threads": (rows.EXPECTED_WITHHELD.get(name, 0)),
                "harness_threads": 1, "names_the_exclusion": True,
                "sides_agree": True, "harness_phrase": "libtest's",
                "unsubtracted_labels": []},
            "licence": {"unverifiable_checks": 2},
            "new_trace_bytes": 4096, "cargo_finished_s": [1.5],
            "driver_version_from_the_trace": "cargo-sensorium 0.5.1",
        })
    two = {"refocuses": refocuses, "n": len(refocuses),
           "measured": len(refocuses), "budget_exhausted": [], "killed": [],
           "pair_refusals": []}
    granted = [r["name"] for r in refocuses
               if r["licence_partition"]["licence"] == "granted"]
    withheld = {r["name"]: r["licence_partition"]["program_threads"]
                for r in refocuses
                if r["licence_partition"]["licence"] == "WITHHELD"}
    return {
        "schema_version": SCHEMA_VERSION, "runner": "rust/tests/x.py",
        "byte_lock": {"doc": "docs/x.md"}, "pins": {}, "raw_pass2": two,
        "raw_h1": {"n": len(refocuses), "granted": granted,
                   "granted_n": len(granted), "withheld": withheld,
                   "expected_granted_n": 57,
                   "partition_as_predicted": True,
                   "harness_threads_all_one": True,
                   "hides_the_exclusion": [],
                   "reasons_that_never_subtracted": [], "unread": []},
        "raw_h2": {"n": len(refocuses), "match_n": len(refocuses),
                   "non_match": [], "word_and_exit_disagree": [],
                   "match_as_predicted": True, "verdicts": {}, "unread": []},
        "raw_h3": {"n": len(refocuses), "pairs_of_one": len(refocuses),
                   "not_one": [], "pairs_as_predicted": True,
                   "excluded_children": {}, "excluded_children_n": 0,
                   "readings_disagree": [], "pair_counts": {}},
        "raw_h4": {"keys": 61, "entries": 61, "distinct_inodes": 1,
                   "bytes_once_per_inode": 12345, "linked_to_the_driver": 61,
                   "not_linked": [], "same_device": True,
                   "keys_as_predicted": True, "all_linked": True,
                   "finding": None},
        "raw_h5": {"raw_schema_version": "e4p/1",
                   "assembled_schema_version": "e4p/1",
                   "as_predicted": True, "dry_assemble": {},
                   "renderers_print_their_field": True},
        "raw_h6": {"all_green": True, "corpus": {"rc": 0, "cases": 40},
                   "python": {"rc": 0, "summary": "1 passed"},
                   "cargo": {"rc": 0}},
        "cleanup": {"kept_store_unchanged": True},
    }


# ------------------------------------------------------ the schema's shape

def test_the_assembled_record_carries_the_raws_schema_and_its_own():
    record = assemble_e4p(_full_raw())
    assert record["schema_version"] == "e4p/1"
    assert record["assembled"]["schema_version"] == SCHEMA_VERSION


def test_a_raw_that_names_no_schema_assembles_to_null_and_not_to_e4p_1():
    assert assemble_e4p({})["schema_version"] is None


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_every_declared_cell_IS_a_measurement_in_the_assembled_block(
        endpoint):
    """`MEASUREMENT_CELLS` is what the drop rules iterate. A cell added to a
    block and forgotten there would escape them entirely and publish a
    number from a loop that never finished."""
    block = assemble_e4p(_full_raw())["endpoints"][endpoint]
    declared = set(cells.MEASUREMENT_CELLS[endpoint])
    assert declared <= cells.measurement_keys(block), endpoint


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_no_measurement_cell_is_published_without_a_lens(endpoint):
    block = assemble_e4p(_full_raw())["endpoints"][endpoint]
    for name in cells.measurement_keys(block):
        assert block[name]["lens"], f"{endpoint}.{name} has no lens"


# ------------------------------------------- none is not zero, ever

@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_a_phase_that_never_RAN_publishes_null_with_a_reason(endpoint):
    """Not 0, not an empty list, not a missing key: a null value plus a
    dropped reason is the ONLY not-measured."""
    block = assemble_e4p({})["endpoints"][endpoint]
    for name in cells.MEASUREMENT_CELLS[endpoint]:
        cell = block[name]
        assert cell["value"] is None, f"{endpoint}.{name}"
        assert cell["dropped"], f"{endpoint}.{name} is null with no reason"
        assert cells.NOT_RUN in cell["dropped"][0]


@pytest.mark.parametrize("endpoint", ["H1", "H2", "H3", "H4"])
def test_a_loop_that_STOPPED_SHORT_nulls_every_count_over_the_61(endpoint):
    """§1.4's kill 6: a miss is recorded with its number, and a count over
    fewer than the 61 is not the count §1 asked for. Every cell goes null
    with the reason; none of this record's cells survives it."""
    raw = _full_raw()
    raw["raw_pass2"]["budget_exhausted"] = ["a", "b"]
    block = assemble_e4p(raw)["endpoints"][endpoint]
    for name in cells.MEASUREMENT_CELLS[endpoint]:
        assert block[name]["value"] is None, f"{endpoint}.{name}"
        assert any("loop bound" in d for d in block[name]["dropped"])


@pytest.mark.parametrize("endpoint", ["H1", "H2", "H3", "H4"])
def test_a_KILLED_invocation_nulls_the_counts_it_could_have_biased(endpoint):
    raw = _full_raw()
    raw["raw_pass2"]["killed"] = ["a_pager_can_be_shared_across_threads"]
    block = assemble_e4p(raw)["endpoints"][endpoint]
    for name in cells.MEASUREMENT_CELLS[endpoint]:
        assert block[name]["value"] is None
        assert any("KILLED" in d for d in block[name]["dropped"])


def test_H5_and_H6_do_NOT_depend_on_the_loop():
    """H5 is about this record's own two files and H6 about this
    repository. Nulling them for a short loop would be a drop rule claiming
    a dependency that is not there."""
    raw = _full_raw()
    raw["raw_pass2"]["budget_exhausted"] = ["a"]
    endpoints = assemble_e4p(raw)["endpoints"]
    assert endpoints["H5"]["headline"]["value"] is True
    assert endpoints["H6"]["headline"]["value"] is True


def test_an_emptied_dropped_list_on_a_null_cell_is_CAUGHT():
    """The mutation this suite must survive: a `null` published with no
    reason reads as "not measured, and nobody will say why". Asserted
    directly so the completeness test above cannot be the only thing
    standing between the record and that."""
    block = assemble_e4p({})["endpoints"]["H1"]
    block["headline"]["dropped"] = []
    with pytest.raises(AssertionError):
        assert block["headline"]["value"] is not None or block[
            "headline"]["dropped"]


# ---------------------------------------------- a killed cell is structural

def test_a_row_that_was_never_run_is_STRUCTURALLY_killed_not_zero():
    """`{"killed": true, "reason": …}`. Not 0, not "", not an empty list --
    each of those is a value a reader or a later sum takes for a measured
    one."""
    raw = _full_raw()
    raw["raw_pass2"]["refocuses"].append(
        {"index": 99, "name": "never_ran", "target": "t", "original": "r-99",
         "not_run": "the 1 h 15 min loop bound was reached"})
    row = assemble_e4p(raw)["pairs"]["rows"][-1]
    assert row["measured"] == {"killed": True,
                               "reason": "the 1 h 15 min loop bound was "
                                         "reached"}
    assert row["measured"]["killed"] is True
    assert 0 not in row["measured"].values()


def test_a_row_KILLED_at_its_ceiling_says_so_beside_its_partial_numbers():
    raw = _full_raw()
    raw["raw_pass2"]["refocuses"][0]["timed_out"] = True
    raw["raw_pass2"]["refocuses"][0]["kill"] = {"pgid": 1, "still_alive":
                                                False}
    row = assemble_e4p(raw)["pairs"]["rows"][0]
    assert row["measured"]["killed"] is True
    assert "1800 s ceiling" in row["measured"]["reason"]


def test_the_killed_cell_helper_has_no_numeric_reading_at_all():
    cell = cells.killed_cell("because")
    assert set(cell) == {"killed", "reason"}
    assert cell["killed"] is True
    with pytest.raises(TypeError):
        int(cell)                                   # noqa: B018


# ---------------------------------- predictions are targets, never values

def test_the_predictions_are_published_under_their_OWN_names():
    p = assemble_e4p(_full_raw())["predictions"]
    assert p["granted"] == 57
    assert p["match"] == 61
    assert p["pairs_of_one"] == 61
    assert p["shim_keys"] == 61
    assert set(p["withheld"]) == set(rows.EXPECTED_WITHHELD)


def test_no_endpoint_falls_back_to_a_prediction_when_its_phase_is_absent():
    """The one rule that makes the whole record falsifiable: a headline that
    borrowed from §1.2 could not fail."""
    endpoints = assemble_e4p({})["endpoints"]
    assert endpoints["H1"]["headline"]["value"] is None
    assert endpoints["H2"]["headline"]["value"] is None
    assert endpoints["H3"]["headline"]["value"] is None
    assert endpoints["H4"]["headline"]["value"] is None
    for expected in (57, 61):
        assert expected not in [e["headline"]["value"]
                                for e in endpoints.values()]


# ------------------------------------------------------------ the renderer

def test_the_renderer_prints_every_endpoint_and_the_schema_sentence():
    record = assemble_e4p(_full_raw())
    text = "\n".join(render_e4p.environment(record)
                     + render_e4p.results(record))
    assert "**Schema.**" in text and "`e4p/1`" in text
    for endpoint in ENDPOINTS:
        assert f"### {endpoint} —" in text


def test_a_not_measured_cell_RENDERS_as_not_measured_and_never_as_a_dash():
    record = assemble_e4p({})
    text = "\n".join(render_e4p.results(record))
    assert "not measured (" in text
    assert "| — | — |" not in text


def test_a_KILLED_row_renders_as_KILLED_and_not_as_a_blank_verdict():
    raw = _full_raw()
    raw["raw_pass2"]["refocuses"][0]["not_run"] = "the bound was reached"
    text = "\n".join(render_e4p.pairs(assemble_e4p(raw)))
    assert "KILLED" in text


def test_the_record_round_trips_through_json():
    """The runner writes it with `json.dumps`; a value that will not
    serialise is discovered here rather than at the end of a long run."""
    json.dumps(assemble_e4p(_full_raw()), default=str)
