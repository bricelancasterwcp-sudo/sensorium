"""The E6⁗ acceptance tooling: the results document, and the shared log
pointer.

The other half of `test_acceptance_e6q`, split at that file's own
`# -- the schema` banner on 2026-09-08. That file sat at exactly 800 lines,
so the ceiling left no room for the next test either half needs. The first
file covers the run's MECHANICS -- the §1 byte lock, the three arms, the
environment the control needs, the base driver's identity, the flip diff, the
control's computed evidence, the two prep builds. This one covers what the run
WRITES: every field `assemble_e6q` publishes, the provenance of each number,
none-versus-zero, and the log pointer the runner re-points on import. The
header is re-derived rather than imported from the first file, as
`tests/test_acceptance_e4pp_phases2.py:20-27` does for its own sibling.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_e6q as runner                                    # noqa: E402
from acceptance_schema_e6q import assemble_e6q                     # noqa: E402

# The same restoration the first file makes, for the same reason and by the
# same argument: importing the runner re-points the SHARED log pointers, and
# which of the suites that import it pytest collects first is not fixed.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS


# -- the schema ------------------------------------------------------------


RAW_ARMS = {
    "raw_arm_a": {
        "swallowed_count": 3, "chains_in_scope": 9, "processes": 1,
        "union_swallowed_count": 3, "unparsed_swallowed": 0,
        "tally": {"swallowed": 3}, "tally_line": "dispositions: swallowed 3",
        "selector": ["-p", "bloomery-daemon"], "tail": ["--lib"],
        "driver_role": "head",
        "sweep": {"swallowed_count": 0, "processes_swept": 0, "swept": [],
                  "swallowed_parsed": []}},
    "raw_arm_ws": {
        "swallowed_count": 2, "chains_in_scope": 5, "processes": 40,
        "union_swallowed_count": 9, "unparsed_swallowed": 0,
        "tally": {"swallowed": 2}, "tally_line": "dispositions: swallowed 2",
        "selector": ["--workspace"], "tail": [], "driver_role": "head",
        "sweep": {"swallowed_count": 7, "processes_swept": 39,
                  "swallowed_parsed": [{"unparsed": False}] * 7,
                  "swept": [{"tally_line": "dispositions: swallowed 3"},
                            {"tally_line": "dispositions: swallowed 4, "
                                           "ambiguous 2"}]}},
    "raw_arm_ws0": {
        "swallowed_count": 4, "chains_in_scope": 6, "processes": 40,
        "union_swallowed_count": 11, "unparsed_swallowed": 0,
        "tally": {"swallowed": 4}, "tally_line": "dispositions: swallowed 4",
        "selector": ["--workspace"], "tail": [], "driver_role": "base",
        "sweep": {"swallowed_count": 7, "processes_swept": 39,
                  "swallowed_parsed": [{"unparsed": False}] * 7,
                  "swept": []}},
}


def test_neither_ws_arms_false_accusation_count_is_ever_invented():
    doc = assemble_e6q({"raw_arm_a": {"swallowed_count": 3, "union_swallowed_count": 3}, "raw_arm_ws": {"swallowed_count": 1, "union_swallowed_count": 9}, "raw_arm_ws0": {"swallowed_count": 2, "union_swallowed_count": 11}})
    for k in ("E6qA", "E6qWS", "E6qWS0"):
        assert doc["endpoints"][k]["headline"]["value"] is None
        assert doc["endpoints"][k]["headline"]["dropped"]


def test_the_control_verdict_is_not_measured_until_the_hand_adjudication_is_pasted():
    doc = assemble_e6q({"raw_arm_ws0": {"swallowed_count": 0, "union_swallowed_count": 0}})
    assert doc["endpoints"]["E6qWS0"]["discriminating"]["value"] is None


def test_the_controls_computed_evidence_is_published_beside_its_null_verdict():
    """A null verdict with nothing beside it leaves the hand adjudication no
    numbers to work from: the COUNT is computed, the verdict is not."""
    doc = assemble_e6q({"raw_arm_ws0": {"swallowed_count": 4,
                                        "union_swallowed_count": 11},
                        "raw_flip_lines": {"ws0": {"count": 2, "lines": [],
                                                   "unresolved": 0,
                                                   "flip_sites": 11}}})
    m = doc["endpoints"]["E6qWS0"]["lines_at_flipped_sites"]
    assert m["value"] == 2 and m["dropped"] == []
    assert doc["endpoints"]["E6qWS0"]["discriminating"]["value"] is None


def test_the_flip_gate_cells_carry_the_frozen_delta_and_the_measured_count():
    doc = assemble_e6q({"raw_flip": {"changed_count": 7, "only_handled_to_ambiguous": True, "named_all_flipped": True}, "frozen_census": {"arms_handled_before": 65, "arms_handled_after": 58}})
    assert doc["endpoints"]["Eflip"]["changed_equals_delta"]["value"] is True
    assert doc["endpoints"]["Eflip"]["changed_equals_delta"]["n"] == 7


def test_the_flip_headline_counts_the_transitions_the_gate_forbids():
    doc = assemble_e6q({"raw_flip": {"changed_count": 3,
                                     "transitions": {
                                         "arm_handled->arm_ambiguous": 2,
                                         "arm_handled->arm_propagate": 1},
                                     "only_handled_to_ambiguous": False,
                                     "named_all_flipped": True},
                        "frozen_census": runner.FROZEN_CENSUS})
    e = doc["endpoints"]["Eflip"]
    assert e["headline"]["value"] == 1 and e["headline"]["n"] == 3
    assert e["changed_equals_delta"]["value"] is False


def test_a_flip_diff_without_a_transition_table_is_null_not_a_clean_zero():
    doc = assemble_e6q({"raw_flip": {"changed_count": 7,
                                     "only_handled_to_ambiguous": True}})
    h = doc["endpoints"]["Eflip"]["headline"]
    assert h["value"] is None and h["dropped"]


def test_the_frozen_census_is_the_five_numbers_section_1_actually_carries():
    """The delta the flip gate is taken against is FROZEN before the lock. A
    runner that re-derived it at run time would have no frozen denominator at
    all -- and a number stamped `source: "§1"` that §1 does not carry would
    give a ledger line the standing of a pre-registered pin."""
    assert runner.FROZEN_CENSUS == {
        "arms_handled_before": 65, "arms_handled_after": 54,
        "arms_escaped_before": 121, "arms_escaped_after": 132,
        "arm_sites": 225, "source": "§1"}
    assert (runner.FROZEN_CENSUS["arms_handled_before"]
            - runner.FROZEN_CENSUS["arms_handled_after"]) == 11
    # §1 freezes five numbers and no sixth.
    assert "arms_propagate" not in runner.FROZEN_CENSUS
    assert len(runner.FROZEN_CENSUS) == 6                # five + the source
    doc = (runner.DOC.read_text() if runner.DOC.is_file() else "")
    if doc:
        s1 = doc[doc.index("## 1. Pre-registration"):doc.index("\n## 2. ")]
        for k, v in runner.FROZEN_CENSUS.items():
            if k != "source":
                assert f"`{k} = {v}`" in s1, k
        assert "arms_propagate" not in s1


def test_the_census_number_section_1_does_not_freeze_carries_its_own_source():
    """`arms_propagate` is a T0/T1 ledger line, published beside the frozen
    five and never under their label."""
    assert runner.LEDGER_CENSUS["arms_propagate"] == 39
    assert "NOT frozen in §1" in runner.LEDGER_CENSUS["source"]
    doc = assemble_e6q({"frozen_census": runner.FROZEN_CENSUS,
                        "ledger_census": runner.LEDGER_CENSUS})
    env = doc["environment"]
    assert env["frozen_census"] == runner.FROZEN_CENSUS
    assert env["ledger_census"] == runner.LEDGER_CENSUS
    assert "arms_propagate" not in env["frozen_census"]


def test_the_schemas_arm_descriptions_match_the_runners_arms():
    """The schema names each arm's command in prose (it may not import the
    runner: the runner imports it). A drift between the two would put one
    command in the lens and another in the record."""
    import acceptance_schema_e6q as schema
    for key, arm in (("E6qA", runner.ARM_A), ("E6qWS", runner.ARM_WS),
                     ("E6qWS0", runner.ARM_WS0)):
        spec = schema.ARMS[key]
        assert spec["key"] == f"raw_arm_{arm['label']}"
        assert spec["selector"] == " ".join(arm["selector"])
        assert spec["tail"] == " ".join(arm["tail"])
        assert spec["driver"] == arm["driver"]


def test_the_union_is_the_primary_plus_the_sweep():
    doc = assemble_e6q(RAW_ARMS)
    ws = doc["endpoints"]["E6qWS"]
    assert ws["swallowed_lines"]["value"] == 2
    assert ws["sweep_swallowed_lines"]["value"] == 7
    assert ws["union_swallowed_lines"]["value"] == 9


def test_an_arm_that_swept_nothing_reports_null_not_a_measured_zero():
    doc = assemble_e6q(RAW_ARMS)
    a = doc["endpoints"]["E6qA"]["sweep_swallowed_lines"]
    assert a["value"] is None and a["n"] == 0
    assert any("0 of 0" in d for d in a["dropped"]), a["dropped"]


def test_the_guarded_arm_count_is_published_with_its_provenance():
    """Design B4 wants the guarded-arm count beside both readings. It RESTATES
    the hand adjudication §4.4 of this document carries (§5.3 repeats it), so
    an arm that RAN names that provenance and drops nothing, while an arm that
    never ran has nothing to restate and stays null with a reason."""
    doc, none = assemble_e6q(RAW_ARMS), assemble_e6q({})
    for key, want in (("E6qA", 2), ("E6qWS", 374), ("E6qWS0", 374)):
        g = doc["endpoints"][key]["guarded_arms"]
        assert g["value"] == want and g["dropped"] == []
        assert "§4.4" in g["provenance"]
        assert none["endpoints"][key]["guarded_arms"]["value"] is None


def test_a_phase_that_did_not_run_is_null_with_a_reason_never_zero():
    doc = assemble_e6q({})
    for key in ("E6qA", "E6qWS", "E6qWS0"):
        m = doc["endpoints"][key]["swallowed_lines"]
        assert m["value"] is None and m["dropped"]
    assert doc["endpoints"]["E6again"]["headline"]["value"] is None
    assert doc["endpoints"]["Eflip"]["changed_count"]["value"] is None
    assert doc["endpoints"]["E0ppp"]["headline"]["value"] is None


def test_e6again_and_e7q_and_e0ppp_are_the_committed_rung3_schema_not_copies():
    """§1 calls them "verbatim". A second schema would be a second protocol,
    free to disagree with the one the rung-3 and E6‴ records used."""
    from acceptance_schema_rung3 import _e0pp, _e6 as rung3_e6, _e7pp
    raw = {"raw_e6": {"cases": [{"case": "rust/x", "questions": [{
        "id": "q", "printed_swallowed_count": 1, "expected_swallowed": 1,
        "swallow_set_equal": True, "printed_tally": "dispositions: swallowed 1",
        "tally_pinned": "dispositions: swallowed 1", "tally_equal": True,
        "extra_swallowed_lines": [], "missing_swallow_groups": [],
        "swallow_set_nonempty_ok": True, "corpus_check_failures": [],
        "rc": 0, "expect_exit": 0, "printed_swallowed": ["SWALLOWED -- x"],
    }]}]},
        "raw_e7pp": {"ok": ["e7_a"], "fail": [], "skip": [], "rc": 0},
        "raw_e0ppp": {"kill_s": 60.0, "run": "r1", "arms": {
            "info": {"wall": 1.0, "under_ceiling": True},
            "diff": {"wall": 2.0, "under_ceiling": True}}}}
    doc = assemble_e6q(raw)
    assert doc["endpoints"]["E6again"] == rung3_e6(raw)
    assert doc["endpoints"]["E7q"] == _e7pp(raw)
    # E0‴ is the committed block with ONLY its lens rewritten (below).
    from acceptance_schema_e6q import E0_LENS_SUBS
    got, want = doc["endpoints"]["E0ppp"], _e0pp({"raw_e0pp": raw["raw_e0ppp"]})
    assert set(got) == set(want)
    for k, v in want.items():
        if isinstance(v, dict) and isinstance(v.get("lens"), str):
            lens = v["lens"]
            for was, now in E0_LENS_SUBS:
                lens = lens.replace(was, now)
            assert got[k] == dict(v, lens=lens)
        else:
            assert got[k] == v


def test_the_e0ppp_lens_names_the_trace_this_run_actually_read():
    """The rung-3 string says "the E6' trace". This run passes the E6⁗-WS
    arm's process with the most events, and a lens naming another document's
    arm would misdescribe every wall in the row."""
    doc = assemble_e6q({"raw_e0ppp": {"kill_s": 60.0, "run": "r1", "arms": {
        "info": {"wall": 1.0, "under_ceiling": True}}}})
    for k in ("headline", "info_wall_s", "diff_wall_s", "max_wall_s"):
        lens = doc["endpoints"]["E0ppp"][k]["lens"]
        assert "E6⁗-WS process with the most events" in lens, k
        assert "E6' trace" not in lens, k


def test_the_lens_substitution_is_GRAMMATICAL_in_every_slot_it_meets():
    """A1's review minors. The rung-3 lens uses "the E6' trace" as a plain
    noun, as a possessive ("the E6' trace's size in bytes") and in a
    compound ("the E6' trace file's size"); the substitution was one blind
    `str.replace`, which turns the second into "…with the most events's
    size". No committed record carries that string -- the cells with the
    genitive are in the rung-3 record's own block and were never passed
    through this substitution -- so the defect is latent, and this is what
    makes it stay that way."""
    from acceptance_schema_e6q import E0_LENS_IS, E0_LENS_SUBS, E0_LENS_WAS

    def sub(text):
        for was, now in E0_LENS_SUBS:
            text = text.replace(was, now)
        return text

    assert sub(f"RAISE events on the {E0_LENS_WAS}") == (
        f"RAISE events on the {E0_LENS_IS}")
    got = sub(f"the {E0_LENS_WAS}'s size in bytes divided by its event count")
    assert "events's" not in got
    assert got == (f"the {E0_LENS_IS}' size in bytes divided by its event "
                   "count")
    got = sub(f"the {E0_LENS_WAS} file's size")
    assert "events file's" not in got
    assert got == f"the {E0_LENS_IS}' own trace file's size"


def test_a_prep_whose_arm_rows_carry_no_COUNT_is_null_WITH_a_reason():
    """A1's review minors: `arm_sites_distinct`'s `dropped` came from
    `_drop`, which can be `[]`, and the guard beside it tested the arms
    BLOCK rather than the cell's own value -- so a prep whose arm rows
    carried no `distinct` count published a null with no reason at all,
    against this module's own rule. Unreachable today only because
    `arm_rows` always writes one, which is not a property this module can
    see."""
    raw = {"raw_prep_head": {"label": "head", "build": {"rc": 0},
                             "arms": {"raw": 7, "by_how": {"try": 7}}}}
    cell = assemble_e6q(raw)["reported"]["prep_head"]["arm_sites_distinct"]
    assert cell["value"] is None
    assert cell["dropped"] == ["this prep build's arm rows carry no "
                               "`distinct` count"]
    # ...and the other shape keeps the reason it had.
    empty = assemble_e6q({"raw_prep_head": {"label": "head",
                                            "build": {"rc": 0}}})
    other = empty["reported"]["prep_head"]["arm_sites_distinct"]
    assert other["value"] is None and other["dropped"]
    assert "no `kind: \"arm\"` manifest rows" in other["dropped"][0]


def test_a_reported_cell_that_did_not_run_carries_its_reason_not_an_empty_list():
    """A `null` with an empty `dropped` renders as `not measured (no reason
    recorded)` — this module's own rule broken at the two cells that say how
    much of the tree each build declared and which flipped arms each arm
    reached."""
    rep = assemble_e6q({})["reported"]
    for key in ("prep_head", "prep_base"):
        m = rep[key]["arm_sites_distinct"]
        assert m["value"] is None and m["dropped"], key
    for label, e in rep["executed_flipped_arms"].items():
        assert e["executed"]["value"] is None and e["executed"]["dropped"], label
    # ... and a cell that DID run keeps its measured value with no reason.
    ran = assemble_e6q({"raw_prep_head": {"arms": {"distinct": 7}}})
    m = ran["reported"]["prep_head"]["arm_sites_distinct"]
    assert m["value"] == 7 and m["dropped"] == []


def test_the_renderer_prints_not_measured_rather_than_a_dash():
    """A dash in a results table is indistinguishable from a zero at a
    glance. The renderer must say what was not measured and why."""
    from render_e6q import results
    doc = assemble_e6q(RAW_ARMS)
    doc["acceptance"] = "x.md"
    text = "\n".join(results(doc))
    assert "not measured (adjudicated by hand" in text
    assert "E6⁗-A" in text and "E6⁗-WS" in text and "E6⁗-WS0" in text
    assert "not measured (decided by the hand adjudication" in text


def test_results_json_if_present_matches_the_committed_schema():
    """After the run, the published `results.json` must be reproducible from
    the raw record by the committed assembler -- not by a one-off script."""
    p = (REPO / "docs" / "superpowers" / "acceptance"
         / "2026-09-05-sensorium-rung3-e6q.results.json")
    if not p.is_file():
        pytest.skip("not measured yet")
    doc = json.loads(p.read_text())
    assert doc["acceptance"].endswith("2026-09-05-sensorium-rung3-e6q.md")
    assert set(doc["endpoints"]) == {"E6qA", "E6qWS", "E6qWS0", "Eflip",
                                     "E6again", "E7q", "E0ppp"}
    for key in ("E6qA", "E6qWS", "E6qWS0"):
        assert doc["endpoints"][key]["headline"]["value"] is None


# -- the shared log pointer ------------------------------------------------


def test_logs_at_moves_the_shared_log_directory_and_restores_it(tmp_path):
    before = lib.LOGS
    with runner.logs_at(tmp_path / "arm-ws"):
        assert lib.LOGS == tmp_path / "arm-ws"
        assert lib.LOGS.is_dir()
    assert lib.LOGS == before


def test_importing_the_runner_leaves_the_shared_log_pointer_on_THIS_document():
    """`acceptance_rung3` AND `acceptance_e6ppp` re-point
    `acceptance_lib.LOGS`/`LEDGER` in their module bodies, and
    `e6ppp.phase_prep_build` resolves `e6ppp.LOGS`/`BASE` in ITS namespace.
    All five must land on THIS document or a log lands beside another record
    (the E6‴ §2 lesson). Reloaded rather than read off the session, because
    the sibling suite asserts the same invariant and both modules are imported
    at collection time; the pointers are restored afterwards."""
    saved = (lib.LOGS, lib.LEDGER, ph.LOGS, e6ppp.LOGS, e6ppp.BASE)
    try:
        importlib.reload(runner)
        assert lib.LOGS == runner.LOGS
        assert lib.LEDGER == runner.LEDGER
        assert ph.LOGS == runner.LOGS
        assert e6ppp.LOGS == runner.LOGS
        assert e6ppp.BASE == runner.BASE
    finally:
        lib.LOGS, lib.LEDGER, ph.LOGS, e6ppp.LOGS, e6ppp.BASE = saved
