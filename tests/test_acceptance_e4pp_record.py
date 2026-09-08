"""E4″'s record: what a cell may say, and what it may never say.

Every rule here is one this project has been bitten by. A phase that did not
run must not publish a `0` a later reader sums; a loop that stopped short
must not publish a count over "the 61" as though it were one; a killed
invocation must not leave an empty string where a number belongs; no
endpoint may be filled from §1's predictions, which are in the room; and
`H6.injected_key` must be DERIVED from `pins.injected_session_key` rather
than chosen a second time.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4pp_cells as cells                              # noqa: E402
import acceptance_e4pp_rows as e4pp                                # noqa: E402
import render_e4pp                                                 # noqa: E402
from acceptance_e4pp_schema import SCHEMA_VERSION, assemble_e4pp   # noqa: E402

sys.path.insert(0, str(REPO / "tests"))
from test_acceptance_e4pp_phases import (INJECTED, SESSION_PIN,    # noqa: E402
                                         _arm, _arm_c, _two)

ENDPOINTS = ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8")


def _raw(**over) -> dict:
    """A raw record with every phase present and every gate met."""
    import acceptance_e4p_phases as eph
    import acceptance_e4pp_arms as arms
    import acceptance_e4pp_phases as ph
    import acceptance_e4p_rows as rows

    two = _two()
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    arm_b = _arm(arms.ARM_B_KEY, "1",
                 {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
                  for n in names})
    arm_c = _arm_c()
    raw = {
        "schema_version": SCHEMA_VERSION,
        "runner": "rust/tests/acceptance_e4pp.py",
        "document": ("docs/superpowers/acceptance/"
                     "2026-09-08-sensorium-rung4-e4pp.md"),
        "started": "now", "finished": "later", "numbers_read": True,
        "byte_lock": {"doc": ("docs/superpowers/acceptance/"
                              "2026-09-08-sensorium-rung4-e4pp.md"),
                      "identical": True, "commit": "2acdc21"},
        "rows_digest": {"identical": True, "sha256": e4pp.ROWS[0][3]},
        "pins": {"session_keys_differing": SESSION_PIN,
                 "injected_session_key": INJECTED,
                 "injected_session_key_choice": {"key": INJECTED,
                                                 "skipped": []},
                 "sensorium_version_metadata_probe": {
                     "token": "0.8.5", "reason": None, "rc": 0}},
        "raw_pass2": two,
        "raw_arm_b": arm_b, "raw_arm_c": arm_c,
        "raw_h1": eph.phase_h1(two),
        "raw_h2": ph.phase_h2_fragment(two),
        "raw_h3": ph.phase_h3_verdict_pair(two),
        "raw_h4": ph.phase_h4_session(two, SESSION_PIN),
        "raw_h5": ph.phase_h5_input(arm_b),
        "raw_h6": ph.phase_h6_session_key(two, arm_c, SESSION_PIN, INJECTED),
        "raw_h8": {"corpus_rc": 0, "pytest_rc": 0, "cargo_rc": 0,
                   "pytest_summary": "1952 passed", "corpus_cases": 33,
                   "spawned_test_fn_present": True, "verdict": "PASS",
                   "as_predicted": True, "dropped": [],
                   "corpus_args": ["--require-driver"]},
        "cleanup": {"kept_store_unchanged": True},
    }
    raw["raw_h7"] = ph.phase_h7_instrument(raw)
    raw.update(over)
    return raw


# ---------------------------------------------------------- the schema

def test_the_assembled_record_carries_the_raws_schema_and_its_OWN():
    record = assemble_e4pp(_raw())
    assert record["schema_version"] == SCHEMA_VERSION == "e4pp/1"
    assert record["assembled"]["schema_version"] == SCHEMA_VERSION


def test_a_raw_that_names_NO_schema_assembles_to_null_and_not_to_e4pp_1():
    """R4: the raw record's token is COPIED, never asserted."""
    raw = _raw()
    raw.pop("schema_version")
    assert assemble_e4pp(raw)["schema_version"] is None


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_every_declared_cell_IS_a_measurement_in_the_assembled_block(
        endpoint):
    """A cell added to a block and forgotten in `MEASUREMENT_CELLS` would
    escape the drop rules and publish a number from a loop that never
    finished."""
    block = assemble_e4pp(_raw())["endpoints"][endpoint]
    declared = set(cells.MEASUREMENT_CELLS[endpoint])
    assert declared <= cells.measurement_keys(block), endpoint


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_no_measurement_cell_is_published_without_a_lens(endpoint):
    block = assemble_e4pp(_raw())["endpoints"][endpoint]
    for name in cells.measurement_keys(block):
        assert block[name]["lens"], f"{endpoint}.{name}"


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_a_phase_that_never_RAN_publishes_null_with_a_reason(endpoint):
    raw = _raw()
    raw.pop(f"raw_{endpoint.lower()}", None)
    block = assemble_e4pp(raw)["endpoints"][endpoint]
    for name in cells.MEASUREMENT_CELLS[endpoint]:
        assert block[name]["value"] is None, f"{endpoint}.{name}"
        assert block[name]["dropped"], f"{endpoint}.{name}"


@pytest.mark.parametrize("endpoint", ["H1", "H2", "H3", "H4"])
def test_a_loop_that_STOPPED_SHORT_nulls_every_count_over_the_61(endpoint):
    raw = _raw()
    raw["raw_pass2"] = dict(raw["raw_pass2"], budget_exhausted=["x", "y"],
                            measured=59)
    block = assemble_e4pp(raw)["endpoints"][endpoint]
    for name in cells.MEASUREMENT_CELLS[endpoint]:
        assert block[name]["value"] is None, f"{endpoint}.{name}"
        assert any("never run" in d for d in block[name]["dropped"])


def test_a_KILLED_invocation_in_an_ARM_nulls_that_arms_cells():
    raw = _raw()
    raw["raw_arm_b"] = dict(raw["raw_arm_b"], killed=["a_row"])
    block = assemble_e4pp(raw)["endpoints"]["H5"]
    for name in cells.MEASUREMENT_CELLS["H5"]:
        assert block[name]["value"] is None
        assert any("KILLED" in d for d in block[name]["dropped"])


def test_H7_and_H8_do_NOT_depend_on_the_loop():
    """H7 is about this record's own instrument and H8 about this
    repository; a short loop says nothing about either."""
    raw = _raw()
    raw["raw_pass2"] = dict(raw["raw_pass2"], budget_exhausted=["x"])
    ends = assemble_e4pp(raw)["endpoints"]
    assert ends["H8"]["corpus_rc"]["value"] == 0
    assert ends["H7"]["headline"]["value"] == 0


# -------------------------------------------------- §1.4's field names

def test_EVERY_field_name_the_H_table_reads_is_in_the_record():
    """§1.4 names each gate's cells by path. A gate the document names and
    the runner does not write is a defect, and this is where it is caught
    rather than at 1 h 20 into a detached run."""
    ends = assemble_e4pp(_raw())["endpoints"]
    for path in ("H1.headline", "H1.withheld",
                 "H2.rustdocflags_in_changed", "H2.strip_clause_named",
                 "H2.relocated_set",
                 "H3.headline", "H3.pairs_of_one",
                 "H3.word_and_exit_disagree",
                 "H4.session_names", "H4.session_k",
                 "H4.withholding_cites_a_session_key",
                 "H5.headline", "H5.env_caveat_names_the_key",
                 "H5.thread_reason_kept",
                 "H6.headline", "H6.session_names", "H6.session_k",
                 "H6.injected_key",
                 "H7.headline", "H7.counts_carry_their_source_line",
                 "H7.licence_verified_counts", "H7.version_probe",
                 "H8.corpus_rc", "H8.spawned_test_fn_present",
                 "H8.pytest_rc", "H8.cargo_rc"):
        end, cell = path.split(".")
        assert cell in ends[end], path


def test_the_two_PINS_the_H_table_reads_are_in_the_record():
    record = assemble_e4pp(_raw())
    assert record["pins"]["session_keys_differing"] == SESSION_PIN
    assert record["pins"]["injected_session_key"] == INJECTED


def test_H6s_injected_key_is_DERIVED_from_the_pin_and_never_re_chosen():
    """Task 3's finding 3. The cell and the pin are one value; if they ever
    differed, that would itself be the finding."""
    record = assemble_e4pp(_raw())
    cell = record["endpoints"]["H6"]["injected_key"]
    assert cell["value"] == record["pins"]["injected_session_key"]
    assert "pins.injected_session_key" in cell["lens"]


# ---------------------------------------------------- the predictions

def test_the_predictions_are_published_under_their_OWN_names():
    p = assemble_e4pp(_raw())["predictions"]
    assert p["granted"] == 57
    assert p["gate_n"] == 61
    assert p["relocated_set"] == list(e4pp.EXPECTED_RELOCATED)
    assert p["arm_n"] == 4
    assert p["spawned_case"] == e4pp.SPAWNED_CASE


def test_no_endpoint_falls_back_to_a_prediction_when_its_phase_is_absent():
    raw = _raw()
    for key in list(raw):
        if key.startswith("raw_"):
            raw.pop(key)
    ends = assemble_e4pp(raw)["endpoints"]
    assert ends["H1"]["headline"]["value"] is None
    assert ends["H2"]["relocated_set"]["value"] is None
    assert ends["H5"]["headline"]["value"] is None


# ------------------------------------------------------- the renderer

def test_the_renderer_prints_every_endpoint_and_the_schema_sentence():
    text = "\n".join(render_e4pp.environment(assemble_e4pp(_raw()))
                     + render_e4pp.results(assemble_e4pp(_raw())))
    for endpoint in ENDPOINTS:
        assert f"### {endpoint} " in text, endpoint
    assert "e4pp/1" in text


def test_a_not_measured_cell_RENDERS_as_not_measured_and_never_as_a_dash():
    raw = _raw()
    raw.pop("raw_h2")
    text = "\n".join(render_e4pp.results(assemble_e4pp(raw)))
    assert "not measured" in text


def test_the_record_round_trips_through_json():
    record = assemble_e4pp(_raw())
    assert json.loads(json.dumps(record, default=str))["schema_version"] == (
        SCHEMA_VERSION)


def test_the_renderer_stays_well_under_the_documents_remaining_budget():
    """§0 and §1 are 441 lines of an 800-line ceiling, and §4 and §5 are
    Task 8's prose. §2 and §3 together have to leave room for both."""
    record = assemble_e4pp(_raw())
    lines = (render_e4pp.environment(record) + render_e4pp.results(record))
    assert len(lines) <= 260, len(lines)


def test_EVERY_reported_cell_section_1_5_names_is_in_the_record():
    """§1.5's list, published without a gate -- and each with the lens it
    is read through, because a number quoted without its instrument is not
    a property of the subject."""
    rep = assemble_e4pp(_raw())["reported"]
    for key in ("rt_hashes", "driver_version", "session_set", "walls_s",
                "arm_b_verdicts", "licence_verified_counts",
                "dropped_lists", "store", "kept_store_unchanged",
                "invocation_log_rows", "disk_free_gb",
                "load_at_each_phase"):
        assert key in rep, key
    assert rep["rt_hashes"]["note"]
    assert rep["session_set"]["note"]
    assert rep["walls_s"]["note"]
    assert rep["arm_b_verdicts"]["note"]
    assert rep["licence_verified_counts"]["note"]


def test_the_wall_per_arm_is_reported_for_ALL_THREE_arms():
    walls = assemble_e4pp(_raw())["reported"]["walls_s"]
    for arm in ("A", "B", "C"):
        assert walls[arm]["n"], arm
        assert walls[arm]["first_focus"] is not None


def test_the_pairs_table_carries_every_arms_rows_each_naming_its_arm():
    pairs = assemble_e4pp(_raw())["pairs"]
    assert pairs["by_arm"] == {"A": 61, "armB": 4, "armC": 4}
    assert pairs["n"] == 69


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_no_measurement_cell_is_published_without_its_DENOMINATOR(endpoint):
    """A count with no `n` is a number a reader cannot place: "0 null cells"
    over 4 rows and over 69 are different claims."""
    block = assemble_e4pp(_raw())["endpoints"][endpoint]
    for name in cells.MEASUREMENT_CELLS[endpoint]:
        assert block[name]["n"] is not None, f"{endpoint}.{name}"
