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


def test_ALL_FOUR_walls_section_1_5_names_are_in_the_reported_block():
    """E4″ gap 5. The bullet pre-commits four -- A, B, C and the DRY run --
    "with cargo's own build time inside each" and "the driver build's wall
    separately"; `reported.walls_s` held three and a note. Every missing
    piece was recorded somewhere in the raw (or in the dry run's own
    record), so this gathers and never re-measures."""
    raw = _raw()
    raw["pins"]["built_from"] = {"cargo_wall_s": 0.025, "rebuilt": False}
    walls = assemble_e4pp(raw)["reported"]["walls_s"]
    assert walls["driver_build"]["value"] == 0.025
    assert walls["driver_build"]["rebuilt"] is False
    assert walls["cargo_s"]["A"]["first_focus"] == 3.3
    assert walls["cargo_s"]["A"]["n"] == 61
    assert walls["cargo_s"]["A"]["rows_without_a_cargo_time"] == 0
    for arm in ("A", "B", "C"):
        assert walls[arm]["n"], arm


def test_cargos_own_time_is_SUMMED_per_row_and_rows_without_one_counted():
    """One `sensorium refocus` can drive more than one cargo invocation, so
    the row's time is the SUM of its `Finished in` lines -- and a row that
    printed none is counted apart rather than entering the mean as a zero,
    which would report a build that took no time."""
    import acceptance_e4p_rows as rows
    two = _two({rows.NAMES[0]: {"cargo": (1.5, 2.0)},
                rows.NAMES[1]: {"cargo": ()}})
    walls = assemble_e4pp(_raw(raw_pass2=two))["reported"]["walls_s"]
    assert walls["cargo_s"]["A"]["first_focus"] == 3.5
    assert walls["cargo_s"]["A"]["n"] == 60
    assert walls["cargo_s"]["A"]["rows_without_a_cargo_time"] == 1


def test_a_DRY_runs_walls_are_carried_in_from_the_record_it_wrote(tmp_path):
    """The fourth wall. A dry run measures nothing about the subject, so
    its walls are not among this run's rows -- they are in the record the
    dry launch wrote, which this one names."""
    dry = _raw()
    dry["dry_run"] = True
    (tmp_path / "dry.json").write_text(json.dumps(dry, default=str))
    raw = dict(_raw(), dry_raw=str(tmp_path / "dry.json"))
    walls = assemble_e4pp(raw)["reported"]["walls_s"]["dry"]
    assert walls["reason"] is None
    assert walls["arms"]["A"]["first_focus"] == 7.0
    assert walls["cargo_s"]["A"]["first_focus"] == 3.3


def test_a_MISSING_dry_record_is_null_WITH_the_path_it_looked_at(tmp_path):
    """None-vs-zero on a wall: a run whose dry record is not there reports
    that, and a reader is told where to look rather than reading a 0."""
    raw = dict(_raw(), dry_raw=str(tmp_path / "absent.json"))
    walls = assemble_e4pp(raw)["reported"]["walls_s"]["dry"]
    assert walls["value"] is None
    assert "could not be read" in walls["reason"]
    assert walls["path"] == str(tmp_path / "absent.json")
    # ...and a DRY run's own record says so instead of pointing at itself.
    own = assemble_e4pp(dict(_raw(), dry_run=True,
                             dry_raw=str(tmp_path / "absent.json"))
                        )["reported"]["walls_s"]["dry"]
    assert own["value"] is None and "IS the dry run" in own["reason"]


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


# ================ fix round 1 =========================================

def test_the_UNREAD_hash_count_is_a_cell_of_its_own_beside_the_two(): 
    """Important 2: `hashes_differ` read 0 whether no pair differed or no
    pair was readable. Three numbers, and the differ cell's denominator is
    the READABLE pairs."""
    import acceptance_e4pp_phases as ph
    sys.path.insert(0, str(REPO / "tests"))
    from test_acceptance_e4pp_phases import _two
    raw = _raw()
    raw["raw_h2"] = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {"rerun_rt": None}}))
    e = assemble_e4pp(raw)["endpoints"]["H2"]
    assert e["hashes_differ"]["value"] == 60
    assert e["hashes_differ"]["n"] == 60
    assert e["hashes_differ"]["dropped"]
    assert e["hashes_unread"]["value"] == [
        "unknown_model_mutating_verbs_is_false"]
    assert e["hashes_unread"]["n"] == 61


def test_the_FRAGMENT_cell_reaches_the_endpoint_AND_the_reported_block():
    """E4″ gap 4, at the two addresses §1.4 and §1.5 point at: an `H2` cell
    of the record's own `{value, n, lens, dropped}` shape, and
    `reported.rt_hashes`, whose `by_pair[*]` carries the per-side counts
    themselves."""
    import acceptance_e4pp_phases as ph
    sys.path.insert(0, str(REPO / "tests"))
    from test_acceptance_e4pp_phases import _two
    raw = _raw()
    raw["raw_h2"] = ph.phase_h2_fragment(_two())
    out = assemble_e4pp(raw)
    cell = out["endpoints"]["H2"]["fragments_per_side"]
    assert cell["value"] == {"original": 1, "rerun": 1}
    assert cell["n"] == 61 and cell["dropped"] == []
    assert "fragments" in cell["lens"]
    rt = out["reported"]["rt_hashes"]
    assert rt["fragments_per_side"] == {"original": 1, "rerun": 1}
    assert rt["pairs_whose_fragments_were_readable"] == 61
    row = rt["by_pair"]["unknown_model_mutating_verbs_is_false"]
    assert row["original_fragments"] == 1 and row["rerun_fragments"] == 1


def test_a_DISAGREEING_fragment_count_is_null_WITH_its_reason_in_the_cell():
    """The honesty half: no single number where the pairs did not agree,
    and the cell says so rather than publishing one of the two."""
    import acceptance_e4pp_phases as ph
    sys.path.insert(0, str(REPO / "tests"))
    from test_acceptance_e4pp_phases import _two
    raw = _raw()
    raw["raw_h2"] = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {"rerun_frags": 0}}))
    cell = assemble_e4pp(raw)["endpoints"]["H2"]["fragments_per_side"]
    assert cell["value"] is None
    assert cell["dropped"] and "did not agree" in cell["dropped"][0]


def test_the_renderer_prints_ALL_THREE_hash_readings():
    import acceptance_e4pp_phases as ph
    sys.path.insert(0, str(REPO / "tests"))
    from test_acceptance_e4pp_phases import _two
    raw = _raw()
    raw["raw_h2"] = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {"rerun_rt": None}}))
    text = "\n".join(render_e4pp.results(assemble_e4pp(raw)))
    assert "could not be read" in text or "unread" in text.lower()
    assert "EQUAL" in text
    for label in ("differ", "unread"):
        assert label in text.lower()


def test_the_verified_counts_render_WITHOUT_their_note():
    """minor (h): the whole dict, note and all, went into one table cell."""
    record = assemble_e4pp(_raw())
    text = "\n".join(render_e4pp.results(record))
    note = record["endpoints"]["H7"]["licence_verified_counts"]["value"][
        "note"]
    assert note not in text
    assert "source 61" in text or "source_verified" in text


def test_a_dry_run_records_whether_the_ARMS_were_rehearsed():
    record = assemble_e4pp(dict(_raw(), dry_run=True, dry_arms=True,
                                dry_check={"ok": True, "arms_ok": True,
                                           "reading": "…"}))
    assert record["dry_run"] is True
    assert record["dry_arms"] is True
    assert record["dry_check"]["arms_ok"] is True


def test_a_null_session_k_carries_ITS_REASON_and_never_an_empty_dropped():
    """Item 3. `session_k` went `value: null, dropped: []` when the
    readable pairs disagreed on K -- a not-measured with no reason, which
    is the one shape §1.3 forbids."""
    import acceptance_e4pp_phases as ph
    sys.path.insert(0, str(REPO / "tests"))
    from test_acceptance_e4pp_phases import _arm_c, _two
    raw = _raw()
    raw["raw_h4"] = ph.phase_h4_session(_two({
        "unknown_model_mutating_verbs_is_false": {
            "session": SESSION_PIN + ["TMUX"]}}), SESSION_PIN)
    cell = assemble_e4pp(raw)["endpoints"]["H4"]["session_k"]
    assert cell["value"] is None
    assert cell["dropped"], "a null with no reason is not a not-measured"

    names = [r["name"] for r in
             __import__("acceptance_e4pp_arms").arm_rows(
                 __import__("acceptance_e4p_rows").ROWS)]
    raw["raw_h6"] = ph.phase_h6_session_key(
        _two(), _arm_c({names[0]: {"session": SESSION_PIN}}),
        SESSION_PIN, INJECTED)
    cell = assemble_e4pp(raw)["endpoints"]["H6"]["session_k"]
    assert cell["value"] is None
    assert cell["dropped"]


def test_a_MEASURED_session_k_still_carries_no_dropped_reason():
    cell = assemble_e4pp(_raw())["endpoints"]["H4"]["session_k"]
    assert cell["value"] == 1
    assert cell["dropped"] == []


# ================ the seven instrument minors (CARRIED-DEBT) ==============

def test_a_K_the_pairs_DISAGREE_on_says_so_in_PROSE_not_a_list_repr():
    """Minor 2: `_k_reason` interpolated the Python list `[1, 2]` into a
    sentence a person reads. The numbers are the same; the record is prose
    and a `repr` in it is a leak from the instrument that wrote it."""
    import acceptance_e4p_rows as rows
    raw = _raw()
    h4 = raw["raw_h4"]
    h4["session_k"] = None
    h4["session_k_by_name"] = {rows.NAMES[0]: 1, rows.NAMES[1]: 2}
    cell = assemble_e4pp(raw)["endpoints"]["H4"]["session_k"]
    assert cell["value"] is None
    reason = " ".join(cell["dropped"])
    assert "did not agree on K (1, 2)" in reason
    assert "[1, 2]" not in reason


def test_an_arm_that_ran_over_the_WRONG_NUMBER_of_rows_nulls_its_cells():
    """Minor 4: `_drops` had no `n != <locked>` clause -- the phases catch a
    short table first, and an assembler that publishes a count over a table
    that was not the locked one is one phase-check away from a wrong number.
    §1.1 locks 61 for arm A and §1.3 locks 4 for each control."""
    raw = _raw()
    raw["raw_pass2"] = dict(raw["raw_pass2"], n=59, measured=59)
    block = assemble_e4pp(raw)["endpoints"]["H3"]
    for name in cells.MEASUREMENT_CELLS["H3"]:
        assert block[name]["value"] is None, name
        assert any("not §1's 61" in d for d in block[name]["dropped"]), name
    raw = _raw()
    raw["raw_arm_b"] = dict(raw["raw_arm_b"], n=3, measured=3)
    h5 = assemble_e4pp(raw)["endpoints"]["H5"]["headline"]
    assert h5["value"] is None and any("not §1's 4" in d
                                       for d in h5["dropped"])


def test_H7s_own_DENOMINATOR_is_stated_on_the_cell_and_not_only_in_n():
    """Minor 5: H7 gates over a census it computes itself -- the rows of
    every arm that came back with a licence WORD -- which is neither the 61
    nor the 69. A reader comparing "0 of 69" with "0 of 66" is comparing
    two different claims, so the cell's lens says what the number is over."""
    block = assemble_e4pp(_raw())["endpoints"]["H7"]
    for name in ("headline", "counts_carry_their_source_line"):
        assert "censused" in block[name]["lens"], name
        assert "neither the 61" in block[name]["lens"], name
    assert block["headline"]["n"] == _raw()["raw_h7"]["censused"]
