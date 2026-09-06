"""The E9 RECORD: the raw facts -> `results.json` schema, and the renderer.

Split from `tests/test_acceptance_e9.py` when that file reached the
repository's 800-line ceiling, on the seam the module under test already has:
the lock, the locations and the four runs are the RUNNER's, and the
none-versus-zero rules are the SCHEMA's. No test moved by a character.

Nothing here runs a command or opens a location. `_raw()` below is a
hand-written COMPLETE raw record — the same fixture the `--assemble` /
`--render` dry run is exercised over — and every test mutates one fact of it
and asserts what the derived document then says.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_e9 as runner                                     # noqa: E402
import acceptance_e9_phases as phases                              # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import render_e9                                                   # noqa: E402
from acceptance_e9_schema import (MEASUREMENT_CELLS, NEEDS,       # noqa: E402
                                  SURVIVES_A_DROPPED_RECORDING,
                                  assemble_e9, measurement_keys)

# The same collection-order restore `tests/test_acceptance_e9.py` makes, and
# for the same reason: importing a runner re-points the SHARED log pointers,
# every suite is imported at COLLECTION time, and whichever collected last
# would otherwise own them.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS

DOC_SHA = "473f86203189bede2b56b19068770dbedba34f012b2c4a7f79012593d8960163"
ORIGINAL_DOC_SHA = ("15f0537587f55ec949a60c86543e6c4e1f7a0929cc57eb4a1"
                    "5320424185b67a5")


# -- the record ------------------------------------------------------------


def _raw(**over) -> dict:
    """A COMPLETE raw record: every phase ran, nothing was killed. The
    fixture the schema tests mutate, and the same shape `--assemble` is
    exercised over in the dry run."""
    runs = {
        "U1": {"name": "U1", "command": "cargo-sensorium sensorium test",
               "rc": 0, "wall_s": 610.5, "timed_out": False, "kill_s": 3600,
               "run": "20260906-101010-aaaaaa", "focus_lines": [],
               "focus_refusal": None, "cargo_exit": 0, "trace_bytes": 900,
               "libtest_secs": 0.4, "run_pick_rule": "exe basename",
               "outcome": {"targets": 1, "passed": 1, "failed": 0,
                           "ignored": 0, "measured": 0, "filtered_out": 0,
                           "verdicts": ["ok"]},
               "test_results": [{"line": "test result: ok. 1 passed; …",
                                 "failed": 0, "libtest_secs": 0.4}],
               "outcome_class": "completed", "outcome_class_why": "exit 0",
               "truncated_count": 0,
               "census": {"line_events": 0, "line_deltas": 0,
                          "line_deltas_unread": 0,
                          "line_deltas_truncated": 0,
                          "line_rows_with_dropped_locals": 0,
                          "bit0_ever_set": False,
                          "unread_delta_names": {},
                          "truncated_delta_names": {},
                          "all_captures": 8, "all_captures_unread": 2,
                          "all_captures_truncated": 0},
               "meta": {"counts": {"LINE": 0}}},
    }
    for name, wall, focus in (("F1", 44.0, [phases.FOCUS_A]),
                              ("U2", 12.0, []),
                              ("F2", 30.0, [phases.FOCUS_B])):
        runs[name] = dict(runs["U1"], name=name, wall_s=wall,
                          focus_lines=focus,
                          run=f"20260906-1010-{name.lower()}")
    raw = {
        "runner": runner.RUNNER,
        "document": str(runner.DOC.relative_to(REPO)),
        "byte_lock": {"doc": "docs/superpowers/acceptance/"
                             "2026-09-06-sensorium-rung4-e9.md",
                      "commit": "ffaed19", "locked_sha256": DOC_SHA,
                      "identical": True, "footnotes_in_range": [],
                      "original_lock": "a4264b5",
                      "original_lock_sha256": ORIGINAL_DOC_SHA,
                      "original_lock_bytes": 23424,
                      "amended_after_the_original_lock": True,
                      "amendment_bytes": 671,
                      "range": "awk '/^## 1/,/^## 2/' PLUS the definition of "
                               "every footnote §1 references",
                      "extraction": "awk '/^## 1/,/^## 2/'",
                      "locked_bytes": 24095,
                      },
        "config": {"focus_a": phases.FOCUS_A, "focus_b": phases.FOCUS_B,
                   "gate_n": 26, "accounted_n": [25, 26, 27],
                   "expected_by_line": {str(k): v for k, v in
                                        runner.EXPECTED_BY_LINE.items()},
                   "temp_root": "/tmp", "tmpdir_observed": None},
        "pins": {"repo_commit": "deadbeef", "repo_branch": "feat/x",
                 "repo_porcelain": "",
                 "clone": "<clone>", "clone_head": lib.CLONE_PIN,
                 "clone_pin": lib.CLONE_PIN, "clone_porcelain": "",
                 "clone_cargo_lock_sha256": "lock0",
                 "driver": "<driver>", "driver_sha256": "abc",
                 "driver_profile": "debug",
                 "driver_rebuilt_by_this_run": True,
                 "driver_mtime": "2026-09-06T08:00:00+0000",
                 "tmpdir_observed": None, "temp_root": "/tmp",
                 "tmpdir_reading": "TMPDIR was unset…",
                 "sensorium_tier": "unset — default `call`",
                 "invocation_log": "NOT silenced",
                 "sensorium_dir": "<store>", "e9_target": "<target>",
                 "rust_target": "<rust>", "corpus_target": "<corpus>",
                 "corpus_target_from_env": False,
                 "rustc": "rustc 1.x", "cargo": "cargo 1.x",
                 "python": "Python 3.12", "sensorium_version": "0.8.1",
                 "nproc": 16, "governor": "performance",
                 "load_1min_at_start": 0.3, "repo_disk_free_gb": 4.0,
                 "target_disk_free_gb": 100.0,
                 "built_from": {"cargo_rc": 0, "rebuilt": True,
                                "command": "cargo build -p cargo-sensorium",
                                "cargo_wall_s": 30.0,
                                "repo_head_at_build": "deadbeef"}},
        "predictions": {
            "watch_triples": [{k: t[k] for k in
                               ("id", "run", "at", "expr", "predicted_class",
                                "predicted_exit", "line")}
                              for t in phases.watch_triples(
                                  {"temp_root": "/tmp"})],
            "flow_sightings": [{k: s[k] for k in
                                ("id", "literal", "binding", "line")}
                               for s in phases.flow_sightings(
                                   {"temp_root": "/tmp"})]},
        "raw_records": {"runs": runs, "focused_build_failed": [],
                        "focused_compile_failures": [],
                        "focused_refusals": [], "focused_test_failures": [],
                        "focused_killed": [],
                        "outcome_classes": {n: "completed" for n in runs},
                        "killed": []},
        "raw_h1": {"run": "20260906-101010-aaaaaa",
                   "capabilities_line": False, "capabilities_locals": False,
                   "recorder": "sensorium-rt 0.4.0", "line_rows": 0,
                   "watch_exit": 3, "refusal_equal": True,
                   "expected_refusal": "REFUSED: watch needs line…",
                   "line_rows_query": "select count(*) …",
                   "info": {"rc": 0, "stdout": "info…"},
                   "watch": {"rc": 3, "verdict_class": "REFUSED",
                             "classes": ["REFUSED"], "timed_out": False,
                             "refusal_line": "REFUSED: watch needs line…",
                             "stdout": "REFUSED…", "command": "sensorium…"}},
        "raw_h2": {"resolution": {
            "F1": {"value": phases.FOCUS_A, "focus_lines": [phases.FOCUS_A],
                   "matched": 1, "resolved_to_exactly_one": True,
                   "refusal": None},
            "F2": {"value": phases.FOCUS_B, "focus_lines": [phases.FOCUS_B],
                   "matched": 1, "resolved_to_exactly_one": True,
                   "refusal": None}},
            "line_qualnames": {
                "F1": {"set": [phases.FOCUS_A],
                       "is_exactly_the_focus_value": True},
                "F2": {"set": [phases.FOCUS_B],
                       "is_exactly_the_focus_value": True}},
            "pairs": {"F1/U1": {"outcome_equal": True,
                                "exit_status_equal": True,
                                "focused_summary_lines": ["ok"],
                                "unfocused_summary_lines": ["ok"]},
                      "F2/U2": {"outcome_equal": True,
                                "exit_status_equal": True,
                                "focused_summary_lines": ["ok"],
                                "unfocused_summary_lines": ["ok"]}},
            "focused_build_failed": []},
        "raw_h3": {"run": "20260906-1010-f1", "N": 26, "gate_N": 26,
                   "expected_total": 26, "equals_gate": True,
                   "in_accounted_range": True, "accounted_range": [25, 26, 27],
                   "stop": False, "activations": 1, "frame_ids": [1],
                   "joins_agree": True,
                   "by_line": {str(k): 1 for k in runner.EXPECTED_BY_LINE},
                   "by_line_via_code_id": {str(k): 1 for k in
                                           runner.EXPECTED_BY_LINE},
                   "diff": {"differences": 0, "missing_lines": [],
                            "unexpected_lines": [], "count_diffs": [],
                            "measured_total": 26, "expected_total": 26}},
        "raw_h4": {"triples": [
            {"id": t["id"], "run": t["run"], "at": t["at"], "expr": t["expr"],
             "predicted_class": t["predicted_class"],
             "predicted_exit": t["predicted_exit"], "line": t["line"],
             "verdict_class": t["predicted_class"],
             "rc": t["predicted_exit"], "timed_out": False,
             "class_as_predicted": True, "exit_as_predicted": True,
             "readings_agree": True, "stdout": "verdict: …",
             "sites": 5, "evaluated": 2, "hits": 2, "not_captured": 3,
             "errors": 0,
             "counts_line": "sites: 5   evaluated: 2   hits: 2   "
                            "not-captured: 3   errors: 0"}
            for t in phases.watch_triples({"temp_root": "/tmp"})],
            "measured": 3, "as_predicted": 3, "class_disagreements": [],
            "killed": []},
        "raw_h5": {"sightings": [
            {"id": s["id"], "literal": s["literal"], "line": s["line"],
             "binding": s["binding"], "timed_out": False,
             "sighting_events": 2, "gated_count": 1,
             "found_at_predicted_line": True, "unpredicted_gated_rows": [],
             "printed_row_count": 2, "gated_rows": ["e5 LINE …"],
             "whole_trace_rows": ["e5 LINE …", "e2 RETURN …"],
             "page_truncated": False, "rows_printed": 2, "showing": None,
             "flow_limit": 1000, "stdout": "sightings: …"}
            for s in phases.flow_sightings({"temp_root": "/tmp"})],
            "both_found": True, "unpredicted": 0, "killed": [],
            "page_truncated": []},
        "raw_h6": {"walls_s": {n: r["wall_s"] for n, r in runs.items()},
                   "libtest_s": {n: r["libtest_secs"] for n, r in runs.items()},
                   "trace_bytes": {n: 900 for n in runs},
                   "pairs": {"F1/U1": {"focused_libtest_s": 0.4,
                                       "unfocused_libtest_s": 0.4,
                                       "focused_invocation_s": 44.0,
                                       "unfocused_invocation_s": 610.5},
                             "F2/U2": {"focused_libtest_s": 0.4,
                                       "unfocused_libtest_s": 0.4,
                                       "focused_invocation_s": 30.0,
                                       "unfocused_invocation_s": 12.0}}},
        "raw_h7": {"corpus": {"rc": 0, "wall_s": 300.0, "timed_out": False,
                              "cases": 31, "questions": 96, "failures": [],
                              "errors": [], "skipped": [], "json": {},
                              "log": "…"},
                   "python": {"rc": 0, "wall_s": 90.0, "timed_out": False,
                              "summary": "1801 passed in 88.0s", "log": "…"},
                   "cargo": {"rc": 0, "wall_s": 120.0, "timed_out": False,
                             "result_lines": ["test result: ok. 5 passed; …"],
                             "log": "…"},
                   "driver_sha256_after": "abc"},
        "cleanup": {"clone_head_after": lib.CLONE_PIN,
                    "clone_porcelain_after": "",
                    "repo_porcelain_after": "",
                    "clone_cargo_lock_sha256_after": "lock1",
                    "repo_disk_free_gb_after": 3.9,
                    "target_disk_free_gb_after": 88.0,
                    "e9_target_bytes": 5_000_000_000,
                    "corpus_target_bytes": 1_000_000,
                    "clone_cargo_lock_moved": True,
                    "clone_cargo_lock_back_on_the_pin": True,
                    "driver_sha256_after": "abc", "driver_unchanged": True,
                    "traces_recorded": 4, "store_bytes": 4000,
                    "invocations_jsonl_lines": 7},
        "logs": "<ledger>/acceptance-e9/logs",
        "arm_loads": [{"arm": "records", "load_1min": 0.3}],
        "steps": ["one"],
        "started": "2026-09-06T09:00:00+0000",
        "finished": "2026-09-06T11:00:00+0000",
    }
    raw.update(over)
    return raw


def _cells(doc) -> list[tuple[str, str, dict]]:
    return [(h, k, doc["endpoints"][h][k])
            for h, keys in MEASUREMENT_CELLS.items() for k in keys]


def test_every_endpoint_publishes_every_cell_of_its_pre_registered_shape():
    """A cell that vanished from the record would read as `not measured
    (absent from results.json)` in the renderer and as nothing at all in the
    document — a missing endpoint that looks like a formatting choice."""
    doc = assemble_e9(_raw())
    assert set(doc["endpoints"]) == set(MEASUREMENT_CELLS)
    for h, k, m in _cells(doc):
        assert isinstance(m, dict), f"{h}.{k}"
        assert set(m) >= {"value", "n", "lens", "dropped"}, f"{h}.{k}"
        assert m["lens"], f"{h}.{k} has no lens"


def test_a_complete_run_measures_every_headline():
    """The passing case, asserted so a schema that published `null`
    everywhere could not sail past the none-versus-zero test below."""
    doc = assemble_e9(_raw())
    for h in MEASUREMENT_CELLS:
        m = doc["endpoints"][h]["headline"]
        assert m["value"] is not None, h
        assert m["dropped"] == [], h
    assert doc["endpoints"]["H1"]["headline"]["value"] == 0
    assert doc["endpoints"]["H3"]["headline"]["value"] == 26
    assert doc["endpoints"]["H7"]["headline"]["value"] == 0


def test_no_cell_is_ever_null_without_a_reason():
    """The one shape this schema forbids: `null` renders as not-measured, so
    a `null` with an empty `dropped` reports a gap while naming none."""
    for raw in (_raw(), {}, _raw(raw_h3=None, raw_h5=None),
                _raw(raw_records={"runs": {}, "focused_build_failed": []})):
        for h, k, m in _cells(assemble_e9(raw)):
            if m["value"] is None:
                assert m["dropped"], f"{h}.{k} is null with no reason"


def test_a_phase_that_did_not_run_is_null_and_not_a_zero():
    """`0` is measured-and-zero. A phase that never ran publishing `0`
    differences would read as a PASS of the strictest kind."""
    doc = assemble_e9(_raw(raw_h3=None, raw_h4=None, raw_h5=None))
    for h in ("H3", "H4", "H5"):
        m = doc["endpoints"][h]["headline"]
        assert m["value"] is None, h
        assert m["dropped"], h


def test_a_KILLED_recording_publishes_nulls_with_the_kill_as_the_reason():
    """The rule the entry slice's review added. A killed `cargo sensorium`
    leaves partial text that parses exactly like a whole answer, so every
    number derived from it must become not-measured — otherwise H3 could
    report N from a build that was cut off."""
    raw = _raw()
    raw["raw_records"]["runs"]["F1"]["timed_out"] = True
    doc = assemble_e9(raw)
    for h in ("H3", "H4", "H5"):
        m = doc["endpoints"][h]["headline"]
        assert m["value"] is None, h
        assert any("KILLED" in d for d in m["dropped"]), (h, m["dropped"])
    # H1 reads U1, which was not killed, so it still measures
    assert doc["endpoints"]["H1"]["headline"]["value"] == 0
    # ...and the other way round: a killed U1 takes H1's cells with it, and
    # leaves H3 — which reads F1 — measured. Both directions, because a rule
    # applied to only one endpoint would let the other publish a number from
    # a recording that was cut off.
    raw = _raw()
    raw["raw_records"]["runs"]["U1"]["timed_out"] = True
    doc = assemble_e9(raw)
    for k in ("headline", "capabilities_line", "watch_exit"):
        m = doc["endpoints"]["H1"][k]
        assert m["value"] is None, k
        assert any("KILLED" in d for d in m["dropped"]), (k, m["dropped"])
    assert doc["endpoints"]["H3"]["headline"]["value"] == 26


def test_a_KILLED_reader_publishes_nulls_for_the_answers_it_cut_off():
    """A `watch` killed at its ceiling has printed part of an answer; the
    class parsed out of it is not the class the command would have printed."""
    raw = _raw()
    raw["raw_h4"]["triples"][1]["timed_out"] = True
    doc = assemble_e9(raw)
    m = doc["endpoints"]["H4"]["headline"]
    assert m["value"] is None
    assert any("KILLED" in d for d in m["dropped"])
    raw = _raw()
    raw["raw_h5"]["sightings"][0]["timed_out"] = True
    m = assemble_e9(raw)["endpoints"]["H5"]["headline"]
    assert m["value"] is None and any("KILLED" in d for d in m["dropped"])


def test_a_focused_run_that_did_not_complete_drops_every_number_it_carries():
    """§1's kill 1. A focused build failure is a STOP, and no endpoint that
    reads a focused trace may publish a number from it."""
    raw = _raw()
    raw["raw_records"]["runs"]["F1"]["rc"] = 101
    raw["raw_records"]["focused_build_failed"] = ["F1"]
    doc = assemble_e9(raw)
    assert doc["endpoints"]["H3"]["headline"]["value"] is None
    assert any("exited 101" in d
               for d in doc["endpoints"]["H3"]["headline"]["dropped"])
    assert doc["endpoints"]["H2"]["focused_build_failures"]["value"] == 1


def test_no_headline_is_ever_filled_from_1s_predictions():
    """The numbers are already in the room. A schema that fell back to §1
    when a phase did not run would report the pre-registration as its own
    result, and H3 could not fail."""
    doc = assemble_e9(_raw(raw_h3=None, raw_h4=None, raw_h5=None))
    assert doc["predictions"]["N"] == 26
    assert doc["endpoints"]["H3"]["headline"]["value"] is None
    assert doc["endpoints"]["H4"]["headline"]["value"] is None
    assert doc["endpoints"]["H5"]["headline"]["value"] is None
    # and the predictions are published under their OWN name, once
    preds = json.dumps(doc["predictions"])
    assert "W1" in preds and "S2" in preds


def test_the_acceptance_field_is_DERIVED_from_the_raw_records_byte_lock():
    """R-G15: a sibling runner assembled a `results.json` naming a document
    it had never read. The document is whatever the LOCK was taken over."""
    raw = _raw()
    raw["byte_lock"]["doc"] = "docs/other.md"
    assert assemble_e9(raw)["acceptance"] == "docs/other.md"
    # with no lock at all there is nothing to derive from, so the raw
    # record's own `document` stands, and only then the module constant
    raw = _raw(byte_lock=None)
    assert assemble_e9(raw)["acceptance"] == str(
        runner.DOC.relative_to(REPO))
    assert assemble_e9({})["acceptance"].endswith("rung4-e9.md")


def test_the_whole_record_round_trips_through_json():
    """The runner's LAST act. A key JSON cannot write (a tuple, a
    `frozenset`) would raise outside every `try` and leave no raw record, no
    `results.json` and NO MARKER — the one state the marker exists to make
    impossible."""
    raw = _raw()
    text = json.dumps(raw, indent=2, default=str)
    doc = assemble_e9(json.loads(text))
    back = json.loads(json.dumps(doc, indent=2, default=str))
    assert back["endpoints"]["H3"]["headline"]["value"] == 26
    assert back["reported"]["walls_s"]["U1"] == 610.5


def test_the_config_the_runner_stores_is_json_writable(tmp_path,
                                                       monkeypatch):
    """`accounted_n` is a `frozenset` and `expected_by_line` has int keys;
    `json.dumps`'s `default=` applies to VALUES only, so neither survives
    without the projection."""
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e9_config({"sensorium_e9_target": tmp_path / "t"})
    out = json.loads(json.dumps(runner._cfg_json(cfg)))
    assert out["accounted_n"] == [25, 26, 27]
    assert out["expected_by_line"]["250"] == 1
    assert out["corpus_target"].endswith("t-corpus")


def test_a_record_with_one_unwritable_value_still_writes_the_rest():
    """The guarded write's fallback. A run that measured for two hours must
    lose the one value a serialisation defect touched, not all of them, and
    a reader must be told which key went."""
    text = runner._partial_json({"started": "t", "bad": {("a", 1): 2},
                                 "steps": ["one"]})
    got = json.loads(text)
    assert got["started"] == "t" and got["steps"] == ["one"]
    assert got["keys_that_could_not_be_serialised"] == ["bad"]
    assert "bad" not in got


# -- the renderer ----------------------------------------------------------


def test_the_renderer_produces_2_and_3_from_the_record():
    """§2 and §3 are pasted from committed code, not from a one-off script.
    A renderer that crashed on a complete record would leave Task 8 writing
    the numbers by hand."""
    doc = assemble_e9(json.loads(json.dumps(_raw(), default=str)))
    env = render_e9.environment(doc)
    res = render_e9.results(doc)
    assert env[0] == "## 2. Environment"
    assert res[0] == "## 3. Results"
    text = "\n".join(env + res)
    for h in MEASUREMENT_CELLS:
        assert f"### {h} —" in text, h
    assert "ffaed19" in text                 # the lock the runner refuses on
    assert "a4264b5" in text                 # the ORIGINAL lock, beside it
    assert ORIGINAL_DOC_SHA in text
    assert "Amended: yes" in text
    assert phases.FOCUS_A in text


def test_a_null_renders_as_not_measured_and_never_as_a_zero_or_a_dash():
    """The renderer's one rule. A dash where a `null` is would let a reader
    take a gap for a small number."""
    doc = assemble_e9(_raw(raw_h3=None))
    text = "\n".join(render_e9.results(doc))
    assert "not measured (" in text
    h3 = [ln for ln in text.splitlines() if ln.startswith("| N — ")]
    assert h3 and "not measured" in h3[0]
    assert "| N — the LINE rows of A's activation (the gate: 26) | 0 |" \
        not in text


def test_a_stop_is_rendered_as_a_stop():
    """§1's kills are STOPs. A record that carried one and rendered without
    it would read as a completed measurement."""
    doc = assemble_e9(_raw(stop="§1 kill 4: H3's N = 31"))
    text = "\n".join(render_e9.results(doc))
    assert "**STOP.**" in text and "N = 31" in text


# -- fix round 1: the killed-cell rule is STRUCTURAL ------------------------


def _all_killed() -> dict:
    """A raw record in which EVERY recording hit its ceiling."""
    raw = _raw()
    for r in raw["raw_records"]["runs"].values():
        r["timed_out"] = True
        r["outcome_class"] = "killed"
    raw["raw_records"]["focused_killed"] = ["F1", "F2"]
    raw["raw_records"]["focused_build_failed"] = ["F1", "F2"]
    return raw


def test_NO_cell_survives_a_record_whose_every_recording_was_killed():
    """The rule, walked over what the schema ACTUALLY publishes rather than
    over the list it declares.

    `MEASUREMENT_CELLS` is what `_apply_record_drops` iterates, so a cell
    added to a block and forgotten in the list escapes the rule entirely —
    which is what happened to H3's `in_the_accounted_range`, published as
    `True` beside a `null` headline on a killed F1. Walking every
    measurement-shaped value in the assembled record catches the next one
    without anybody having to remember."""
    doc = assemble_e9(_all_killed())
    seen = 0
    for h, block in doc["endpoints"].items():
        if h not in NEEDS:
            # H7 measures THIS repository, not the clone, so no recording of
            # the clone can drop it. Asserted from the map rather than from a
            # hand-written exemption, so an endpoint that stopped needing a
            # recording could not quietly leave the walk.
            assert h == "H7", h
            continue
        for k in measurement_keys(block):
            if k in SURVIVES_A_DROPPED_RECORDING.get(h, ()):
                continue
            m, seen = block[k], seen + 1
            assert m["value"] is None, f"{h}.{k} survived a killed recording"
            assert m["dropped"], f"{h}.{k} is null with no reason"
            assert any("KILLED" in d for d in m["dropped"]), (h, k,
                                                              m["dropped"])
    assert seen >= 20, f"only {seen} cells walked — the record shrank"


def test_H7s_own_commands_null_their_own_cells_when_they_are_killed():
    """H7 reads no recording, so the walk above cannot reach it — and its
    three commands have ceilings of their own. A `cargo test` cut off at two
    hours has no exit status, and `None` published as a number would read as
    the green 0."""
    raw = _raw()
    for key in ("corpus", "python", "cargo"):
        raw["raw_h7"][key]["timed_out"] = True
        raw["raw_h7"][key]["kill_s"] = 7200
    h7 = assemble_e9(raw)["endpoints"]["H7"]
    for k in MEASUREMENT_CELLS["H7"]:
        assert h7[k]["value"] is None, k
        assert any("KILLED" in d for d in h7[k]["dropped"]), (k, h7[k])
    # one killed command does not null the other two
    raw = _raw()
    raw["raw_h7"]["cargo"]["timed_out"] = True
    h7 = assemble_e9(raw)["endpoints"]["H7"]
    assert h7["cargo_rc"]["value"] is None
    assert h7["headline"]["value"] == 0 and h7["pytest_rc"]["value"] == 0


def test_the_declared_cell_list_is_what_the_schema_publishes():
    """The other half: `MEASUREMENT_CELLS` must not drift from the blocks.

    A cell in a block but not in the list escapes the drop rule; a name in
    the list but not in a block makes `_apply_record_drops` a no-op for it
    and the completeness test vacuous."""
    doc = assemble_e9(_raw())
    for h, block in doc["endpoints"].items():
        assert measurement_keys(block) == set(MEASUREMENT_CELLS[h]), h
    # and on the did-not-run path, where the blocks are built by a different
    # branch that has drifted from the measured one before
    empty = assemble_e9({})
    for h, block in empty["endpoints"].items():
        assert measurement_keys(block) == set(MEASUREMENT_CELLS[h]), h


def test_H3s_accounted_range_cell_dies_with_a_killed_F1():
    """The CRITICAL of fix round 1, pinned by name. The assembled record read
    `H3.headline None` beside `in_the_accounted_range True`, and the renderer
    printed the second — a killed build reporting that N was inside
    {25, 26, 27} when no N had been measured at all."""
    raw = _raw()
    raw["raw_records"]["runs"]["F1"]["timed_out"] = True
    raw["raw_records"]["runs"]["F1"]["outcome_class"] = "killed"
    h3 = assemble_e9(raw)["endpoints"]["H3"]
    assert h3["headline"]["value"] is None
    assert h3["in_the_accounted_range"]["value"] is None
    assert h3["in_the_accounted_range"]["dropped"]


# -- fix round 1: H5's page, H7's skips, the kill-1 label -------------------


def test_a_TRUNCATED_flow_page_nulls_EVERY_H5_cell():
    """`flow`'s default page is 50 and both of H5's gated numbers are read
    off the printed rows. A gate over a truncated page is a smaller number
    about a smaller question, and would read as a PASS with sightings unseen.

    The SECOND reading goes with them. Its number is `flow`'s own whole-scope
    `sightings:` count, so a truncated page does not understate it — but on a
    truncated answer the two readings were computed over different things,
    and publishing one beside a nulled gate would let a reader take the pair
    for a comparison."""
    raw = _raw()
    raw["raw_h5"]["sightings"][0]["page_truncated"] = True
    raw["raw_h5"]["page_truncated"] = ["S1"]
    h5 = assemble_e9(raw)["endpoints"]["H5"]
    for k in MEASUREMENT_CELLS["H5"]:
        assert h5[k]["value"] is None, k
        assert any("SMALLER than the sighting set" in d
                   for d in h5[k]["dropped"]), (k, h5[k]["dropped"])
    # the untruncated case still measures, all three
    ok = assemble_e9(_raw())["endpoints"]["H5"]
    assert ok["headline"]["value"] == 2
    assert all(ok[k]["value"] is not None for k in MEASUREMENT_CELLS["H5"])


def test_H5s_second_reading_is_flows_whole_scope_count_not_the_page():
    """§1 pre-registers the second reading as "every sighting of that literal
    ANYWHERE in the trace". The printed rows are a page; `flow`'s own
    `sightings:` line is computed over its whole scope
    (`flow_cmd._print_footer`), so it is the number that answers the
    question. Publishing `len(rows)` would silently report the page size
    under a name that claims the whole trace."""
    raw = _raw()
    for s in raw["raw_h5"]["sightings"]:
        s["sighting_events"] = 9      # what flow counted over its whole scope
        s["printed_row_count"] = 2    # what it printed
    m = assemble_e9(raw)["endpoints"]["H5"]["whole_trace_sightings"]
    assert m["value"] == {"S1": 9, "S2": 9}
    assert "ANYWHERE in the trace" in m["lens"]


def test_skipped_corpus_cases_are_a_measurement_with_gate_zero():
    """`run_corpus` skips a cargo case it can find no driver for and exits 0.
    H7 read only the exit status and the failures would call a corpus that
    ran nothing green — the strongest possible pass over no evidence."""
    doc = assemble_e9(_raw())
    assert doc["endpoints"]["H7"]["corpus_skipped"]["value"] == 0
    raw = _raw()
    raw["raw_h7"]["corpus"]["skipped"] = [
        {"case": "rust/focus_let_chain", "reason": "no cargo-sensorium"}]
    h7 = assemble_e9(raw)["endpoints"]["H7"]
    assert h7["corpus_skipped"]["value"] == 1
    assert h7["corpus_rc"]["value"] == 0        # green, and NOT every case
    assert h7["corpus_skipped_cases"][0]["case"] == "rust/focus_let_chain"


def test_a_libtest_failure_is_not_1s_kill_1():
    """§1's kill 1 is a COMPILE failure of a focused unit. A failing
    assertion in the clone's own suite exits non-zero WITH a summary line;
    calling that "a compile failure of a focused unit" would stop the rung on
    the clone's test and put the wrong finding in the record."""
    raw = _raw()
    raw["raw_records"]["runs"]["F1"].update(
        rc=101, outcome_class="test_failure",
        outcome_class_why="exit 101 with 1 libtest summary line(s), 1 "
                          "test(s) failed: the unit compiled and ran")
    raw["raw_records"].update(focused_test_failures=["F1"],
                              focused_build_failed=["F1"])
    doc = assemble_e9(raw)
    assert doc["recordings"]["F1"]["outcome_class"] == "test_failure"
    # it still drops the numbers derived from that recording ...
    assert doc["endpoints"]["H3"]["headline"]["value"] is None
    # ... and H2's count of focused runs that did not complete is the honest
    # one, because that cell survives a dropped recording by name
    assert doc["endpoints"]["H2"]["focused_build_failures"]["value"] == 1


def test_the_ungated_honesty_counts_reach_the_record_and_the_renderer():
    """§1.4 pre-registers them without a gate: the unread deltas, the
    truncated ones, whether `flags.bit0` was ever set, and `watch`'s bucket
    counts. A block that was measured and never published is a measurement
    nobody can read."""
    doc = assemble_e9(_raw())
    u = doc["reported"]["unread_and_truncated_captures"]
    assert set(u["per_run"]) == {"U1", "F1", "U2", "F2"}
    assert u["bit0_ever_set"]["F1"] is False
    assert u["recorder_truncated_count"]["F1"] == 0
    assert doc["reported"]["watch_bucket_counts"]["W1"]["not_captured"] == 3
    assert doc["reported"]["flow_pages"]["S1"]["limit"] == 1000
    text = "\n".join(render_e9.results(doc))
    assert "§1.4's honesty counts" in text
    assert "not-captured" in text


def test_an_unparsed_outcome_is_None_and_never_a_failed_comparison():
    """`outcome_equal: False` is a claim about two outcomes. A run whose
    output carried no summary line has no outcome, and reporting the pair as
    unequal would make H2 fail on a missing parse rather than on a
    difference."""
    raw = _raw()
    raw["raw_h2"]["pairs"]["F1/U1"]["outcome_equal"] = None
    m = assemble_e9(raw)["endpoints"]["H2"]["outcomes_equal"]
    assert m["value"] == 1 and m["n"] == 2      # the OTHER pair still counts
