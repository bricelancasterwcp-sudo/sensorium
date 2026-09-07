"""The E4 RECORD: the raw facts -> `results.json` schema, and the renderer.

Split from `tests/test_acceptance_e4.py` on the seam the modules under test
already have: the lock, the locations and the two passes are the RUNNER's,
and the none-versus-zero rules are the SCHEMA's.

Nothing here runs a command or opens a location. `_raw()` below is a
hand-written COMPLETE raw record -- the same fixture the `--assemble` /
`--render` dry run is exercised over -- and every test mutates one fact of it
and asserts what the derived document then says.

The fixture holds THREE pairs rather than 61. The schema's rules are about
the loop's completeness and about each command's own ceiling -- `n` versus
`measured`, `budget_exhausted`, `killed` -- and none of them is about the
number 61, so a three-pair record exercises them exactly and the assertions
stay readable.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4 as runner                                     # noqa: E402
import acceptance_e4_phases2 as phases2                            # noqa: E402
import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import render_e4                                                   # noqa: E402
from acceptance_e4_schema import (MEASUREMENT_CELLS, NEEDS,        # noqa: E402
                                  SURVIVES_A_KILL, assemble_e4,
                                  measurement_keys)

# The same collection-order restore `tests/test_acceptance_e4.py` makes, and
# for the same reason: importing a runner re-points the SHARED log pointers,
# every suite is imported at COLLECTION time, and whichever collected last
# would otherwise own them.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS

DOC_SHA = "09d2f8da30f6e216fb07e97c27481d35d0c285e40c2bccb9295e0ef07863ff42"
ORIGINAL_DOC_SHA = ("87abc779ea3acf867e07a0055d92de6281b4fd5571aaadb489"
                    "98ac7d9afe18c4")

#: Three of §1.1's 61, in §1.1's order -- the first (the cold build), the one
#: §1.3's W1/W3 run on, and the one W4 runs on.
THREE = (("pager_obligation_test", 250,
          "missing_stats_is_a_contract_violation_not_a_reply"),
         ("pager_refusal_advice_test", 89,
          "the_refusal_advises_a_window_that_actually_places"),
         ("pager_remove_agent_test", 60,
          "remove_agent_on_unknown_id_is_named"))

OUTCOME = {"targets": 1, "passed": 1, "failed": 0, "ignored": 0,
           "measured": 0, "filtered_out": 14, "verdicts": ["ok"]}
SUMMARY = ["test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; "
           "14 filtered out; finished in 0.02s"]


def _pass1() -> dict:
    runs = []
    for i, (target, _line, name) in enumerate(THREE, start=1):
        runs.append({
            "index": i, "target": target, "name": name,
            "command": f"<driver> sensorium test --test {target}",
            "cwd": "<clone>", "rc": 0, "wall_s": 610.5 if i == 1 else 12.0,
            "timed_out": False, "kill_s": 1800, "log": "<log>",
            "cargo_exit": 0,
            "run_lines": [{"run": f"orig-{i}"}], "processes": 1,
            "multi_process": False, "run": f"orig-{i}",
            "run_candidates": None, "test_results": [{"line": SUMMARY[0]}],
            "summary_lines": SUMMARY, "outcome": dict(OUTCOME),
            "libtest_secs": 0.02, "cargo_finished_s": [41.53],
            "trace_bytes": 900_000,
            "meta": {"recorder": "sensorium-rt 0.4.0",
                     "driver_version": "cargo-sensorium 0.5.0",
                     "fingerprint_basis": "per-task",
                     "capabilities": {"line": False}},
        })
    return {"runs": runs, "by_name": {r["name"]: r for r in runs},
            "n": len(runs), "measured": len(runs), "budget_exhausted": [],
            "killed": [], "non_zero_exit": [], "multi_process": [],
            "no_trace": [],
            "versions": {"from_run": "orig-1",
                         "recorder": "sensorium-rt 0.4.0",
                         "driver_version": "cargo-sensorium 0.5.0",
                         "fingerprint_basis": "per-task"},
            "walls_s": {r["name"]: r["wall_s"] for r in runs}}


def _pass2() -> dict:
    rows = []
    for i, (target, _line, name) in enumerate(THREE, start=1):
        rows.append({
            "index": i, "target": target, "name": name,
            "original": f"orig-{i}",
            "command": f"<py> -m sensorium refocus orig-{i} --focus {name}",
            "cwd": "<repo>", "rc": 0, "wall_s": 120.0 if i == 1 else 30.0,
            "timed_out": False, "kill_s": 1800, "log": "<log>",
            "launched_at": 1000.0 + i, "child_launched": True,
            "driver_exit": None, "test_results": [{"line": SUMMARY[0]}],
            "summary_lines": SUMMARY, "outcome": dict(OUTCOME),
            "libtest_secs": 0.02, "cargo_finished_s": [9.1],
            "pair": {"linked": [f"new-{i}"], "qualifying": [f"new-{i}"],
                     "unreadable": [], "n": 1, "launched_at": 1000.0 + i},
            "new_run": f"new-{i}", "pair_refusal": None,
            "printed_new_run": f"new-{i}",
            "pair_agrees_with_the_printed_id": True,
            "licence": {"source_status": "unchanged", "source_verified": True,
                        "env_status": "unchanged", "env_verified": True,
                        "exit_verified": True, "licence": "granted",
                        "output_unverifiable": True,
                        "children_unverifiable": True,
                        "verified_facts": 4, "unverifiable_checks": 2},
            "stdout": "…", "stderr": "…",
            "refocus_of": f"orig-{i}", "driver_cmd": "<driver> --refocus-of",
            "verdict_word": "MATCH",
            "verdict_line": "refocus verdict: MATCH -- …",
            "diff_verdict_line": "verdict: MATCH -- identical causal "
                                 "streams (406 events): …",
            "threads_line": "threads: 1 recorded fingerprint(s) compared",
            "tasks_line": "tasks: 1 task stream(s) compared by content",
            "licence_line": f"licence: verified against orig-{i} on exactly "
                            "these points, and no others:",
            "licence_facts": ["identical call shape across 1 …",
                              "37 source file(s) unchanged by content",
                              "94 environment variable(s) compared …",
                              "no thread started besides the main one …"],
            "licence_caveats": [],
            "unverifiable": ["output: unverifiable (not recorded)",
                             "children: unverifiable (not witnessed)"],
            "unverifiable_header": "checks that could not run on this pair …",
            "pre_rerun_refusal": None, "pre_rerun_refusal_run": None,
            "refused_after_rerun": None, "diverged_step": None,
            "step_rows": [], "source_line": "source: unchanged (37 file(s) …",
            "env_line": "env: unchanged (94 variables compared …",
            "exit_line": "exit: rerun 0   original 0",
            "exit_rerun": "0", "exit_original": "0",
            "exit_status_equal": True,
            "verdict_exit_expected": 0, "verdict_and_exit_agree": True,
            "new_trace_bytes": 1_100_000,
            "new_meta": {"refocus_of": f"orig-{i}",
                         "refocus_verdict": "MATCH",
                         "refocus_licence": "granted",
                         "refocus_licence_unverifiable": [
                             "output: unverifiable (not recorded)",
                             "children: unverifiable (not witnessed)"]},
        })
    return {"refocuses": rows, "by_name": {r["name"]: r for r in rows},
            "n": len(rows), "measured": len(rows), "budget_exhausted": [],
            "killed": [], "pair_refusals": [],
            "walls_s": {r["name"]: r["wall_s"] for r in rows}}


def _raw(**over) -> dict:
    """A COMPLETE raw record: both passes ran, nothing was killed, nothing
    was left unreached. The fixture the schema tests mutate, and the same
    shape `--assemble` is exercised over in the dry run."""
    one, two = _pass1(), _pass2()
    cfg = {"temp_root": "/tmp"}
    raw = {
        "runner": runner.RUNNER,
        "document": str(runner.DOC.relative_to(REPO)),
        "byte_lock": {"doc": "docs/superpowers/acceptance/"
                             "2026-09-07-sensorium-rung4-e4.md",
                      "commit": "413f601", "locked_sha256": DOC_SHA,
                      "identical": True, "footnotes_in_range": [],
                      "original_lock": "8e7d837",
                      "original_lock_sha256": ORIGINAL_DOC_SHA,
                      "original_lock_bytes": 33378,
                      "amended_after_the_original_lock": True,
                      "amendment_bytes": 1205,
                      "range": "awk '/^## 1/,/^## 2/' PLUS the definition of "
                               "every footnote §1 references",
                      "extraction": "awk '/^## 1/,/^## 2/'",
                      "locked_bytes": 34583},
        "config": {"tests": [list(t) for t in THREE],
                   "targets": [t for t, _l, _n in THREE],
                   "gate_n": 3, "temp_root": "/tmp",
                   "tmpdir_observed": None, "cargo_timeout": 1800,
                   "refocus_timeout": 1800, "reader_timeout": 120,
                   "loop_budget_s": 7200, "corpus_timeout": 7200,
                   "pytest_timeout": 3600, "cargo_test_timeout": 7200},
        "predictions": {
            "expected_match": [n for _t, _l, n in THREE], "gate_n": 3,
            "hazard_tests": list(
                __import__("acceptance_e4_read").HAZARD_TESTS),
            "watch_triples": [{k: t[k] for k in
                               ("id", "of", "at", "expr", "predicted_class",
                                "predicted_exit", "line", "gate")}
                              for t in phases2.watch_triples(cfg)]},
        "pins": {"repo_commit": "deadbeef", "repo_branch": "feat/x",
                 "repo_porcelain": "", "clone": "<clone>",
                 "clone_head": lib.CLONE_PIN, "clone_pin": lib.CLONE_PIN,
                 "clone_porcelain": "", "clone_cargo_lock_sha256": "lock0",
                 "tests_dir": "<clone>/crates/bloomery-daemon/tests",
                 "the_61_names": {"diff": {"equal": True}, "ignore_attrs": 0,
                                  "should_panic_attrs": 0},
                 "driver": "<driver>", "driver_sha256": "abc",
                 "driver_profile": "debug",
                 "driver_rebuilt_by_this_run": True,
                 "driver_mtime": "2026-09-07T08:00:00+0000",
                 "versions_from_the_first_trace": one["versions"],
                 "tmpdir_observed": None, "temp_root": "/tmp",
                 "tmpdir_reading": "TMPDIR was unset…",
                 "sensorium_tier": "unset — default `call`",
                 "invocation_log": "NOT silenced",
                 "sensorium_dir": "<store>", "e4_target": "<target>",
                 "rust_target": "<rust>", "corpus_target": "<corpus>",
                 "corpus_target_from_env": False,
                 "rustc": "rustc 1.x", "cargo": "cargo 1.x",
                 "python": "Python 3.12", "sensorium_version": "0.8.4",
                 "nproc": 16, "governor": "performance",
                 "load_1min_at_start": 0.3, "repo_disk_free_gb": 4.0,
                 "target_disk_free_gb": 100.0,
                 "built_from": {"cargo_rc": 0, "rebuilt": True,
                                "command": "cargo build -p cargo-sensorium",
                                "cargo_wall_s": 30.0,
                                "repo_head_at_build": "deadbeef"}},
        "raw_pass1": one,
        "raw_pass2": two,
        "raw_h1": {"n": 3, "pre_rerun_refusals": [],
                   "pre_rerun_refusal_count": 0,
                   "exit_2_without_a_sentence": [], "reached_the_driver": 3,
                   "did_not_reach_the_driver": [], "killed": []},
        "raw_h2": {"n": 3, "completed": 3, "build_failures": [],
                   "outcomes_equal": 3, "outcomes_unequal": [],
                   "outcomes_unreadable": [], "killed": [],
                   "per_test": [{"name": r["name"], "completed": True,
                                 "build_failure": False,
                                 "outcome_equal": True,
                                 "child_launched": True}
                                for r in two["refocuses"]]},
        "raw_h3": {"n": 3, "gate_n": 3, "match": 3, "diverged": [],
                   "diverged_named_hazard": [], "diverged_findings": [],
                   "diverged_unclassified": [], "refused_after_rerun": [],
                   "readings_disagree": [], "no_verdict_word": [],
                   "killed": [],
                   "verdict_words": {r["name"]: "MATCH"
                                     for r in two["refocuses"]},
                   "exits": {r["name"]: 0 for r in two["refocuses"]},
                   "per_test": [{"name": r["name"], "verdict_word": "MATCH",
                                 "exit": 0, "readings_agree": True,
                                 "classification": None, "step_rows": [],
                                 "stamped_verdict": "MATCH"}
                                for r in two["refocuses"]]},
        "raw_h4": {"n": 3, "source_verified": 3, "env_verified": 3,
                   "exit_verified": 3, "output_unverifiable": 3,
                   "children_unverifiable": 3, "granted": 3, "withheld": 0,
                   "no_licence_line": [], "claims_an_unverifiable_check": [],
                   "killed": [],
                   "reading": "the verified counts and the unverifiable "
                              "counts are two numbers and are never summed",
                   "per_test": [{"name": r["name"], "licence": "granted",
                                 "source_status": "unchanged",
                                 "env_status": "unchanged",
                                 "unverifiable": r["unverifiable"]}
                                for r in two["refocuses"]]},
        "raw_h5": {"triples": [
            {**t, "run_id": "new-1", "command": "sensorium watch …",
             "rc": t["predicted_exit"], "timed_out": False, "log": "<log>",
             "wall_s": 0.4, "stdout": "verdict: …",
             "verdict_class": t["predicted_class"],
             "classes": [t["predicted_class"]],
             "sites": 5, "evaluated": 2, "hits": 2, "not_captured": 3,
             "errors": 0,
             "counts_line": "sites: 5   evaluated: 2   hits: 2   "
                            "not-captured: 3   errors: 0",
             "class_as_predicted": True, "exit_as_predicted": True,
             "readings_agree": True, "as_predicted_on_its_gate": True}
            for t in phases2.watch_triples(cfg)],
            "measured": 3, "as_predicted_on_their_gates": 3,
            "class_as_predicted": 3, "exit_as_predicted": 3,
            "class_disagreements": [], "killed": [],
            "reported_classes": {"W1": "SATISFIED",
                                 "W3": "no recorded code matches",
                                 "W4": "SATISFIED"}},
        "raw_h6": {"n": 3,
                   "first_focus": {"name": THREE[0][2], "wall_s": 120.0,
                                   "cargo_finished_s": [9.1]},
                   "later_focus_walls_s": [30.0, 30.0],
                   "later_focus_total_s": 60.0, "later_focus_mean_s": 30.0,
                   "later_focus_max_s": 30.0, "later_focus_min_s": 30.0,
                   "refocus_walls_s": two["walls_s"],
                   "refocus_total_s": 180.0,
                   "cargo_build_s": {r["name"]: [9.1]
                                     for r in two["refocuses"]},
                   "cargo_build_reported_for": [r["name"]
                                                for r in two["refocuses"]],
                   "pass1_walls_s": one["walls_s"], "pass1_total_s": 634.5,
                   "libtest_s": {r["name"]: 0.02 for r in two["refocuses"]},
                   "pass1_libtest_s": {r["name"]: 0.02
                                       for r in one["runs"]},
                   "trace_bytes": {"originals": {}, "refocused": {}},
                   "shim_census": {"dir": "<target>/sensorium/shim",
                                   "exists": True, "entries": 3,
                                   "bytes": 4_000_000,
                                   "names": ["a", "b", "c"]}},
        "raw_h7": {"corpus": {"rc": 0, "wall_s": 300.0, "timed_out": False,
                              "cases": 61, "questions": 135, "failures": [],
                              "errors": [], "skipped": [], "json": {},
                              "log": "…", "command": "…",
                              "target": "<corpus>"},
                   "python": {"rc": 0, "wall_s": 90.0, "timed_out": False,
                              "summary": "1520 passed in 88.0s", "log": "…",
                              "command": "…"},
                   "cargo": {"rc": 0, "wall_s": 120.0, "timed_out": False,
                             "result_lines": ["test result: ok. 5 passed; …"],
                             "log": "…", "command": "…", "target": "<rust>"},
                   "driver_sha256_after": "abc"},
        "cleanup": {"clone_head_after": lib.CLONE_PIN,
                    "clone_porcelain_after": "", "repo_porcelain_after": "",
                    "clone_cargo_lock_sha256_after": "lock1",
                    "clone_cargo_lock_moved": True,
                    "clone_cargo_lock_back_on_the_pin": True,
                    "repo_disk_free_gb_after": 3.9,
                    "target_disk_free_gb_after": 88.0,
                    "e4_target_bytes": 5_000_000_000,
                    "corpus_target_bytes": 1_000_000,
                    "driver_sha256_after": "abc", "driver_unchanged": True,
                    "traces_recorded": 6, "store_bytes": 6_000_000,
                    "invocations_jsonl_lines": 9},
        "logs": "<ledger>/acceptance-e4/logs",
        "arm_loads": [{"arm": "pass1", "load_1min": 0.3}],
        "steps": ["one"],
        "started": "2026-09-07T09:00:00+0000",
        "finished": "2026-09-07T11:00:00+0000",
    }
    raw.update(over)
    return raw


def _cells(doc) -> list[tuple[str, str, dict]]:
    return [(h, k, doc["endpoints"][h][k])
            for h, keys in MEASUREMENT_CELLS.items() for k in keys]


# -- the shape -------------------------------------------------------------


def test_every_endpoint_publishes_every_cell_of_its_pre_registered_shape():
    """A cell that vanished from the record would read as `not measured
    (absent from results.json)` in the renderer and as nothing at all in the
    document -- a missing endpoint that looks like a formatting choice."""
    doc = assemble_e4(_raw())
    assert set(doc["endpoints"]) == set(MEASUREMENT_CELLS)
    for h, k, m in _cells(doc):
        assert set(m) >= {"value", "n", "lens", "dropped"}, (h, k)
        assert m["lens"], f"{h}.{k} has no lens"


def test_a_complete_run_measures_every_headline():
    """The fixture is a run in which everything worked. A cell that came
    back `null` on it would be a schema that cannot report a success."""
    doc = assemble_e4(_raw())
    for h, k, m in _cells(doc):
        assert m["value"] is not None, (h, k, m["dropped"])
        assert m["dropped"] == [], (h, k, m["dropped"])
    e = doc["endpoints"]
    assert e["H1"]["headline"]["value"] == 0
    assert e["H2"]["headline"]["value"] == 3
    assert e["H3"]["headline"]["value"] == 3
    assert e["H5"]["headline"]["value"] == 3
    assert e["H7"]["headline"]["value"] == 0


def test_no_cell_is_ever_null_without_a_reason():
    """`null` plus an empty `dropped` is the one shape the schema forbids:
    it is indistinguishable from a value nobody looked for."""
    doc = assemble_e4({})
    for _h, _k, m in _cells(doc):
        assert m["value"] is None
        assert m["dropped"], (_h, _k)


def test_a_phase_that_did_not_run_is_null_and_not_a_zero():
    """`0` is measured-and-zero. A phase that never ran publishing `0`
    would read in §3 as `no refusals` and `no divergences` -- the friendliest
    possible answer, produced by measuring nothing."""
    doc = assemble_e4({})
    for h in ("H1", "H2", "H3", "H4", "H5", "H6", "H7"):
        m = doc["endpoints"][h]["headline"]
        assert m["value"] is None and m["value"] != 0
        assert any("did not run" in d for d in m["dropped"]), (h, m)


def test_the_declared_cell_list_is_what_the_schema_publishes():
    """`MEASUREMENT_CELLS` must not drift from the blocks: a cell in a block
    but not in the list escapes the drop rules entirely, and a name in the
    list but not in a block makes the rule a no-op for it."""
    doc = assemble_e4(_raw())
    for h, block in doc["endpoints"].items():
        assert measurement_keys(block) == set(MEASUREMENT_CELLS[h]), h


# -- the drop rules --------------------------------------------------------


def _all_killed() -> dict:
    """Every invocation of both passes cut off at its 1800 s ceiling."""
    raw = _raw()
    for key, rows in (("raw_pass1", "runs"), ("raw_pass2", "refocuses")):
        for r in raw[key][rows]:
            r["timed_out"] = True
        raw[key]["killed"] = [r["name"] for r in raw[key][rows]]
    return raw


def test_a_KILLED_pass_publishes_nulls_with_the_kill_as_the_reason():
    """The rule, walked over what the schema ACTUALLY publishes rather than
    over the list it declares -- a cell added to a block and forgotten in
    `MEASUREMENT_CELLS` escapes the rule entirely, which is the defect this
    walk exists to catch the next time.

    A killed command leaves partial text that parses exactly like a whole
    answer, so a MATCH count read off three killed re-runs is a number about
    nothing."""
    doc = assemble_e4(_all_killed())
    seen = 0
    for h, block in doc["endpoints"].items():
        if not NEEDS[h]:
            # H7 measures THIS repository, not the pairs, so no killed
            # invocation of the loop can drop it. Asserted from the map
            # rather than from a hand-written exemption.
            assert h == "H7", h
            continue
        for k in measurement_keys(block):
            if k in SURVIVES_A_KILL.get(h, ()):
                continue
            m, seen = block[k], seen + 1
            assert m["value"] is None, f"{h}.{k} survived a killed pass"
            assert m["dropped"], f"{h}.{k} is null with no reason"
            assert any("KILLED" in d for d in m["dropped"]), (h, k,
                                                              m["dropped"])
    assert seen >= 20, f"only {seen} cells walked -- the record shrank"


def test_H1s_refusal_count_survives_a_KILL_and_says_why():
    """The one cell `SURVIVES_A_KILL` names, and the reason it may. A
    pre-rerun refusal exits 2 BEFORE the driver child is launched, so an
    invocation that ran long enough to hit an 1800 s ceiling had already
    passed that gate and cannot be hiding one."""
    doc = assemble_e4(_all_killed())
    assert SURVIVES_A_KILL == {"H1": ("headline",)}
    assert doc["endpoints"]["H1"]["headline"]["value"] == 0
    assert doc["endpoints"]["H1"]["reached_the_driver"]["value"] is None


def test_an_INCOMPLETE_loop_nulls_even_the_cell_that_survives_a_kill():
    """§1's kill 6: a reader at its ceiling is the record, and a smaller
    view is a not-measured rather than a smaller number. A test the 2-hour
    bound never reached COULD have refused, so even H1's headline is a
    smaller number about a smaller question there -- which is the difference
    between the two drop lists."""
    raw = _raw()
    raw["raw_pass2"]["budget_exhausted"] = ["P2/x"]
    raw["raw_pass2"]["measured"] = 2
    doc = assemble_e4(raw)
    for h, block in doc["endpoints"].items():
        if not NEEDS[h]:
            continue
        for k in measurement_keys(block):
            m = block[k]
            assert m["value"] is None, f"{h}.{k} survived an unfinished loop"
            assert any("2-hour" in d or "never run" in d
                       for d in m["dropped"]), (h, k, m["dropped"])


def test_a_pass_that_measured_fewer_than_it_listed_is_also_a_drop():
    """The other way a loop can come up short: rows that were skipped for a
    reason of their own (an original that left no single run id) rather than
    by the bound. A count over them is still a count over a smaller set."""
    raw = _raw()
    raw["raw_pass2"]["measured"] = 2
    doc = assemble_e4(raw)
    m = doc["endpoints"]["H3"]["headline"]
    assert m["value"] is None
    assert any("2 of 3" in d for d in m["dropped"]), m["dropped"]


def test_H7s_own_commands_null_their_own_cells_when_they_are_killed():
    """H7 reads no pair, so the walk above cannot reach it -- and its three
    commands have ceilings of their own. A `cargo test` cut off at two hours
    has no exit status, and `None` published as a number would read as the
    green 0."""
    raw = _raw()
    for key in ("corpus", "python", "cargo"):
        raw["raw_h7"][key]["timed_out"] = True
        raw["raw_h7"][key]["kill_s"] = 7200
    h7 = assemble_e4(raw)["endpoints"]["H7"]
    for k in MEASUREMENT_CELLS["H7"]:
        assert h7[k]["value"] is None, k
        assert any("KILLED" in d for d in h7[k]["dropped"]), (k, h7[k])
    raw = _raw()
    raw["raw_h7"]["cargo"]["timed_out"] = True
    h7 = assemble_e4(raw)["endpoints"]["H7"]
    assert h7["cargo_rc"]["value"] is None
    assert h7["headline"]["value"] == 0 and h7["pytest_rc"]["value"] == 0


def test_a_dropped_watch_triple_nulls_H5_and_names_which(tmp_path):
    """H5's three triples run on NEW traces. A refocus that produced none
    leaves its triple undroppable-into-a-number, and the record must say
    which one rather than reporting two of three as the answer."""
    raw = _raw()
    raw["raw_h5"]["triples"][1] = {
        **raw["raw_h5"]["triples"][1],
        "dropped": "the refocus of x produced no NEW trace on disk"}
    h5 = assemble_e4(raw)["endpoints"]["H5"]
    assert h5["headline"]["value"] is None
    assert any("W3" in d for d in h5["headline"]["dropped"])


# -- no cell is filled from a prediction -----------------------------------


def test_no_headline_is_ever_filled_from_1s_predictions():
    """§1's numbers are in the room. A block that fell back to one when a
    phase did not run would report the pre-registration as its own result,
    and no endpoint could fail."""
    doc = assemble_e4({"predictions": _raw()["predictions"],
                       "config": _raw()["config"]})
    assert doc["predictions"]["gate_n"] == 3
    assert len(doc["predictions"]["watch_triples"]) == 3
    for _h, _k, m in _cells(doc):
        assert m["value"] is None, (_h, _k)


def test_H4s_verified_and_unverifiable_counts_are_never_summed():
    """§1.4's rule, at the schema. The two are separate cells; a record
    that reported `5 of 5 checks verified` by adding them would turn the
    recorder's declared absence of output capture into evidence FOR the
    pair."""
    e = assemble_e4(_raw())["endpoints"]["H4"]
    assert e["headline"]["value"] == 3            # source
    assert e["env_verified"]["value"] == 3
    assert e["exit_verified"]["value"] == 3
    assert e["output_unverifiable"]["value"] == 3
    assert e["children_unverifiable"]["value"] == 3
    assert "never counted as verified" in e["output_unverifiable"]["lens"]
    assert e["claims_an_unverifiable_check"]["value"] == 0


def test_a_licence_that_claims_an_unverifiable_check_is_a_finding():
    """The named bug class: a licence line listing `output: unverifiable`
    among the points it VERIFIED. Gated at 0 and reported as a finding
    rather than folded into the granted count."""
    raw = _raw()
    raw["raw_h4"]["claims_an_unverifiable_check"] = [
        {"name": "x", "facts": ["output: unverifiable (not recorded)"]}]
    e = assemble_e4(raw)["endpoints"]["H4"]
    assert e["claims_an_unverifiable_check"]["value"] == 1


# -- provenance and round-trip ---------------------------------------------


def test_the_acceptance_field_is_DERIVED_from_the_raw_records_byte_lock():
    """R-G15: the document a record names is the one the run was locked
    against, taken from the raw record rather than from a module constant
    that a later edit could move."""
    raw = _raw()
    raw["byte_lock"]["doc"] = "docs/superpowers/acceptance/other.md"
    assert assemble_e4(raw)["acceptance"].endswith("other.md")
    raw = _raw()
    raw.pop("byte_lock")
    assert assemble_e4(raw)["acceptance"].endswith(
        "2026-09-07-sensorium-rung4-e4.md")


def test_the_whole_record_round_trips_through_json():
    """The record is written with `json.dumps(..., default=str)` and read
    back by the renderer. A value that survived assembly but not the
    round-trip would lose the run its §3."""
    doc = assemble_e4(_raw())
    back = json.loads(json.dumps(doc, default=str))
    assert back["endpoints"]["H3"]["headline"]["value"] == 3
    assert back["pairs"]["n"] == 3


def test_the_config_the_runner_stores_is_json_writable(monkeypatch,
                                                       tmp_path):
    """`_cfg_json` exists because `Path` and `frozenset` are not JSON. A
    config that raised here would lose the whole raw record at the last
    act of a two-hour run."""
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4_config({"sensorium_e4_target": tmp_path / "t",
                            "sensorium_bloomery": tmp_path / "c"})
    text = json.dumps(runner._cfg_json(cfg))
    assert "corpus_target" in text and str(tmp_path) in text


def test_a_record_with_one_unwritable_value_still_writes_the_rest():
    """A two-hour run must lose one value to a serialisation defect, not
    all of them."""
    text = runner._partial_json({"good": 1, "bad": {object(): 2}})
    back = json.loads(text)
    assert back["good"] == 1
    assert back["keys_that_could_not_be_serialised"] == ["bad"]


# -- the pairs table -------------------------------------------------------


def test_the_pairs_table_has_one_row_per_name_including_the_unrun():
    """One row per §1.1 name, whether or not it ran. A table of the tests
    that happened to work is not a record of a loop."""
    raw = _raw()
    raw["raw_pass1"]["runs"][2] = {
        "index": 3, "target": THREE[2][0], "name": THREE[2][2],
        "not_run": "the 2-hour loop bound was reached before this invocation"}
    raw["raw_pass2"]["refocuses"][2] = {
        "index": 3, "target": THREE[2][0], "name": THREE[2][2],
        "original": None, "not_run": "pass 1 did not run this test"}
    doc = assemble_e4(raw)
    rows = doc["pairs"]["rows"]
    assert [r["name"] for r in rows] == [n for _t, _l, n in THREE]
    assert rows[2]["pass1_not_run"]
    assert rows[0]["verdict_word"] == "MATCH"
    assert rows[0]["licence"] == "granted"


# -- the renderer ----------------------------------------------------------


def test_the_renderer_produces_2_and_3_from_the_record():
    """The text Task 8 pastes, produced by committed code rather than by a
    one-off script."""
    doc = assemble_e4(_raw())
    text = "\n".join(render_e4.environment(doc) + [""]
                     + render_e4.results(doc))
    assert text.startswith("## 2. Environment")
    assert "## 3. Results" in text
    for head in ("### H1", "### H2", "### H3", "### H4", "### H5", "### H6",
                 "### H7", "### The 61 pairs",
                 "### Reported without a gate"):
        assert head in text, head
    # BOTH locks, in §2, as facts rather than as prose.
    assert DOC_SHA in text and ORIGINAL_DOC_SHA in text
    assert "413f601" in text and "8e7d837" in text
    # the version tokens, read from the trace
    assert "sensorium-rt 0.4.0" in text and "cargo-sensorium 0.5.0" in text
    # W3's split reading is visible in the triple table
    assert "no recorded code matches" in text
    assert "| W3 |" in text


def test_a_null_renders_as_not_measured_and_never_as_a_zero_or_a_dash():
    """The renderer's one rule. A `null` printed as `0` or `—` would read as
    a measured zero -- the friendliest number in the table."""
    text = "\n".join(render_e4.results(assemble_e4({})))
    assert "not measured (" in text
    assert "| 0 |" not in text


def test_a_stop_and_a_bound_are_rendered_as_what_they_are():
    """§1's two STOP classes and its 2-hour bound are different facts and
    must not be reported as each other -- the first stops the rung, the
    second says the loop did not finish."""
    doc = assemble_e4(_raw(stop="§1 kill 1: focused build failure(s) on [x]",
                           bound_reached="§1.4's 2-hour loop bound was "
                                         "reached; 4 invocation(s)"))
    text = "\n".join(render_e4.results(doc))
    assert "**STOP.** §1 kill 1" in text
    assert "**BOUND REACHED.**" in text


def test_the_ungated_block_reaches_the_renderer():
    """§1.4's reported-without-a-gate list: the walls, the shim census, the
    audit rows and the discriminator table. Assembled but never rendered,
    they would be facts nobody reads."""
    doc = assemble_e4(_raw())
    text = "\n".join(render_e4.ungated(doc))
    assert "shim census" in text and "4000000 bytes" in text.replace(",", "")
    assert "invocation-log rows at the end" in text
    assert "pair-rule refusals" in text


def test_the_discriminator_table_renders_when_it_was_applied():
    """A DIVERGED on one of §1.2's three tests is adjudicated by arithmetic,
    and the arithmetic is published: a class with no numbers beside it is a
    verdict a reader cannot check."""
    raw = _raw()
    raw["raw_h3"]["per_test"][1]["classification"] = {
        "class": "hazard", "task_events_total_original": 10,
        "task_events_total_new": 10, "main_fingerprint_matches": True,
        "task_count_original": 4, "task_count_new": 4}
    text = "\n".join(render_e4.ungated(assemble_e4(raw)))
    assert "worker-task events A / B" in text
    assert "| 10 / 10 |" in text and "| hazard |" in text


def test_the_build_failure_caveat_is_rendered_beside_H2s_STOP():
    """The class §1 names covers two things -- a focused compile failure and
    a driver/converter failure on the way to one. §3 must state that where
    the number is, or a reader takes the STOP for the first."""
    raw = _raw()
    raw["raw_h2"]["build_failures"] = ["a_test"]
    raw["raw_h2"]["build_failure_caveat"] = (
        "no libtest summary and a non-zero exit -- a focused COMPILE "
        "failure … OR a driver/converter failure …; the discriminator is "
        "the pass-2 log (driver_exit = {'a_test': 101}, log = …)")
    text = "\n".join(render_e4._h2(assemble_e4(raw)))
    assert "What the class does not tell apart" in text
    assert "driver/converter failure" in text
    # and a clean run says nothing of the sort
    assert "What the class does not tell apart" not in "\n".join(
        render_e4._h2(assemble_e4(_raw())))

