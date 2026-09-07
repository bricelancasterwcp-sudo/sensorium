#!/usr/bin/env python3
"""The E4 phases, part two: H4-H7, over the pairs `acceptance_e4_phases.py`
produced.

The seam is the pass protocols: part one runs the 61 originals and the 61
re-runs and asks the three endpoints derived directly from them (H1's
refusals, H2's completions, H3's verdicts); this file asks the four that read
what the pairs left behind -- the licence block (H4), the three `watch`
triples on the NEW traces (H5), the cost (H6) and the rest of the repository
(H7). Neither file may pass 800 lines, which is why there are two.

Nothing here decides a verdict either. H4 and H6 are REPORTED without a gate
by §1's own table, and they are recorded as facts with their lens beside
them.
"""

from __future__ import annotations

import json as _json
from pathlib import Path

from acceptance_e4_read import parse_watch, shim_census
from acceptance_e6ppp import logs_at, mark_load
from acceptance_e9_phases import _read as read_cli
from acceptance_e9_phases import guarded
from acceptance_lib import REPO, plain_env, sha256_file, step

#: Assigned by `acceptance_e4`, for `acceptance_e4_phases.LOGS`'s reason.
LOGS: Path | None = None

#: §1.3's three triples, in §1.3's words. `of` names the TEST whose NEW
#: (refocused) trace the triple runs against -- never an original, which is
#: unfocused and would be E9's H1 capability refusal rather than this
#: record's question.
#:
#: `gate` is what §1.3 pre-commits as the gate for that row. W1 and W4 gate
#: on BOTH readings; W3 gates on the EXIT alone, because the class it prints
#: necessarily differs from E9's -- `pager_with_model` lives in another test
#: binary, which this single-`--exact` invocation never builds into the run,
#: so `watch` takes its `_no_match` branch. §1.3 pre-registers the printed
#: class as REPORTED for exactly that reason.
W1_OF = "missing_stats_is_a_contract_violation_not_a_reply"
W4_OF = "remove_agent_on_unknown_id_is_named"


def watch_triples(cfg) -> list[dict]:
    """§1.3's W1, W3 and W4, with the temp-directory prefix substituted once.

    The predicted class and exit are carried BESIDE each triple as comparison
    targets, never as values a cell can fall back to.
    """
    root = cfg["temp_root"]
    return [
        {"id": "W1", "of": W1_OF, "at": W1_OF,
         "expr": f'dir == "{root}/bloomery-pager-contract"',
         "predicted_class": "SATISFIED", "predicted_exit": 0, "line": 251,
         "gate": "class and exit"},
        {"id": "W3", "of": W1_OF, "at": "pager_with_model",
         "expr": f'dir == "{root}/bloomery-pager-contract"',
         "predicted_class": "no recorded code matches", "predicted_exit": 1,
         "line": None, "gate": "exit"},
        {"id": "W4", "of": W4_OF, "at": W4_OF,
         "expr": f'dir == "{root}/bloomery-pager-remove-unknown"',
         "predicted_class": "SATISFIED", "predicted_exit": 0, "line": 61,
         "gate": "class and exit"},
    ]


# --------------------------------------------------------------------- H4


def phase_h4(two: dict) -> dict:
    """H4: what does the licence say? REPORTED, no gate.

    Four numbers, and the rule that binds them: `source` and `env` run for
    real and are counted as verified or not; the exit-status comparison is
    the third check that runs. `output` and `children` are UNVERIFIABLE BY
    CONSTRUCTION on a Rust pair -- `capabilities.output` and
    `capabilities.children` are false, so there is nothing to compare -- and
    are counted in their OWN field. The verified count and the unverifiable
    count are never summed, here or anywhere downstream: an UNVERIFIABLE
    check is never counted as verified.

    A licence line that said "verified" for either would be the named bug
    class, and is reported as `claims_an_unverifiable_check` rather than as
    a pass.
    """
    mark_load("H4")
    rows = [r for r in two["refocuses"] if "not_run" not in r]
    per_test, bad = [], []
    for r in rows:
        lic = r.get("licence") or {}
        facts = r.get("licence_facts") or []
        claims = [f for f in facts
                  if "unverifiable" in f or f.startswith("output: ")
                  or f.startswith("children: ")]
        if claims:
            bad.append({"name": r["name"], "facts": claims})
        per_test.append({
            "name": r["name"],
            "licence": lic.get("licence"),
            "source_status": lic.get("source_status"),
            "source_verified": lic.get("source_verified"),
            "env_status": lic.get("env_status"),
            "env_verified": lic.get("env_verified"),
            "exit_verified": lic.get("exit_verified"),
            "output_unverifiable": lic.get("output_unverifiable"),
            "children_unverifiable": lic.get("children_unverifiable"),
            "verified_facts": lic.get("verified_facts"),
            "unverifiable_checks": lic.get("unverifiable_checks"),
            "licence_line": r.get("licence_line"),
            "licence_facts": r.get("licence_facts"),
            "licence_caveats": r.get("licence_caveats"),
            "unverifiable": r.get("unverifiable"),
            "source_line": r.get("source_line"),
            "env_line": r.get("env_line"),
            "exit_line": r.get("exit_line"),
            "stamped_unverifiable": (r.get("new_meta") or {}).get(
                "refocus_licence_unverifiable"),
            "stamped_licence": (r.get("new_meta") or {}).get(
                "refocus_licence"),
        })
    count = lambda key: sum(1 for p in per_test if p[key])          # noqa: E731
    out = {
        "n": len(rows),
        "per_test": per_test,
        "source_verified": count("source_verified"),
        "env_verified": count("env_verified"),
        "exit_verified": count("exit_verified"),
        "output_unverifiable": count("output_unverifiable"),
        "children_unverifiable": count("children_unverifiable"),
        "granted": sum(1 for p in per_test if p["licence"] == "granted"),
        "withheld": sum(1 for p in per_test if p["licence"] == "WITHHELD"),
        "no_licence_line": [p["name"] for p in per_test
                            if p["licence"] is None],
        "claims_an_unverifiable_check": bad,
        "reading": ("the verified counts and the unverifiable counts are two "
                    "numbers and are never summed: a check that could not "
                    "run is never counted as one that passed"),
        "killed": two["killed"],
    }
    step(f"H4: source {out['source_verified']}/{out['n']} env "
         f"{out['env_verified']}/{out['n']} exit {out['exit_verified']}/"
         f"{out['n']} verified; output {out['output_unverifiable']} children "
         f"{out['children_unverifiable']} UNVERIFIABLE; granted "
         f"{out['granted']}")
    return out


# --------------------------------------------------------------------- H5


def phase_h5(paths, cfg, two: dict) -> dict:
    """H5: does the loop close? §1.3's three triples, on the NEW traces.

    Both readings are recorded separately -- the verdict class `watch`
    printed and the exit status it returned -- and their agreement is a
    field, not a resolution: §1 makes a disagreement between them a finding
    about `Verdict`/`STATUS`, so neither is derived from the other. W3's
    gate is the EXIT; its class is reported.
    """
    mark_load("H5")
    by_name = two["by_name"]
    rows = []
    with logs_at(LOGS / "h5"):
        for t in watch_triples(cfg):
            src = by_name.get(t["of"]) or {}
            new_run = src.get("new_run")
            db = (paths["sensorium_dir"] / "traces" / f"{new_run}.db"
                  if new_run else None)
            if not new_run or not db.is_file():
                rows.append({**t, "dropped": (
                    f"the refocus of {t['of']} produced no NEW trace on disk "
                    f"(new_run {new_run!r})")})
                continue
            args = ["watch", new_run, "--at", t["at"], "--expr", t["expr"]]
            res = read_cli(paths, args, f"h5-{t['id'].lower()}", cfg)
            p = parse_watch("\n".join((res["out"], res["err"])))
            row = {**t, "run_id": new_run, "command": res["command"],
                   "rc": res["rc"], "timed_out": res["timed_out"],
                   "log": res["log"], "wall_s": round(res["wall"], 3),
                   "stdout": "\n".join((res["out"], res["err"])), **p}
            row["class_as_predicted"] = (p["verdict_class"]
                                         == t["predicted_class"])
            row["exit_as_predicted"] = res["rc"] == t["predicted_exit"]
            row["readings_agree"] = (row["class_as_predicted"]
                                     == row["exit_as_predicted"])
            # §1.3 splits W3's readings: the exit is the gate, byte-identical
            # to E9's, and the class is REPORTED because it necessarily
            # differs. Every other row gates on both.
            row["as_predicted_on_its_gate"] = (
                row["exit_as_predicted"] if t["gate"] == "exit"
                else row["exit_as_predicted"] and row["class_as_predicted"])
            rows.append(row)
            step(f"H5 {t['id']}: class {p['verdict_class']!r} (predicted "
                 f"{t['predicted_class']!r}), exit {res['rc']} (predicted "
                 f"{t['predicted_exit']}); gate {t['gate']}; sites "
                 f"{p['sites']} hits {p['hits']} not-captured "
                 f"{p['not_captured']}")
    measured = [r for r in rows if "dropped" not in r]
    return {
        "triples": rows,
        "measured": len(measured),
        "as_predicted_on_their_gates": sum(
            1 for r in measured if r["as_predicted_on_its_gate"]),
        "class_as_predicted": sum(1 for r in measured
                                  if r["class_as_predicted"]),
        "exit_as_predicted": sum(1 for r in measured
                                 if r["exit_as_predicted"]),
        "class_disagreements": [r["id"] for r in measured
                                if not r["readings_agree"]],
        "reported_classes": {r["id"]: r["verdict_class"] for r in measured},
        "killed": [r["id"] for r in measured if r["timed_out"]],
    }


# --------------------------------------------------------------------- H6


def phase_h6(paths, one: dict, two: dict) -> dict:
    """H6: what does it cost? REPORTED, no gate, under both readings.

    First reading: the invocation wall per refocus, with the FIRST focus
    distinguished from the later ones -- the first pays for the rt build,
    the later ones for a fresh shim and the matched units. Second reading:
    cargo's own reported build time inside each, read from the `Finished …
    in <n>s` line the driver's child printed on the stderr this runner
    captured (§2.3's "streams through" is for a person at a terminal; a
    runner is not one, and the evidence lands in the per-item log either
    way).

    Beside them: the shim census, measured ONCE at the end.
    """
    mark_load("H6")
    ordered = [r for r in two["refocuses"] if "not_run" not in r]
    first = ordered[0] if ordered else None
    later = ordered[1:]
    walls = [r["wall_s"] for r in ordered if r.get("wall_s") is not None]
    later_walls = [r["wall_s"] for r in later if r.get("wall_s") is not None]
    builds = {r["name"]: r.get("cargo_finished_s") for r in ordered}
    census = shim_census(paths["sensorium_e4_target"])
    out = {
        "n": len(ordered),
        "first_focus": ({"name": first["name"], "wall_s": first.get("wall_s"),
                         "cargo_finished_s": first.get("cargo_finished_s")}
                        if first else None),
        "later_focus_walls_s": later_walls,
        "later_focus_total_s": round(sum(later_walls), 3) if later_walls
        else None,
        "later_focus_mean_s": (round(sum(later_walls) / len(later_walls), 3)
                               if later_walls else None),
        "later_focus_max_s": max(later_walls) if later_walls else None,
        "later_focus_min_s": min(later_walls) if later_walls else None,
        "refocus_walls_s": {r["name"]: r.get("wall_s") for r in ordered},
        "refocus_total_s": round(sum(walls), 3) if walls else None,
        "cargo_build_s": builds,
        "cargo_build_reported_for": [n for n, v in builds.items() if v],
        "pass1_walls_s": one.get("walls_s"),
        "pass1_total_s": (round(sum(v for v in (one.get("walls_s") or {}
                                                ).values() if v is not None),
                                3)),
        "libtest_s": {r["name"]: r.get("libtest_secs") for r in ordered},
        "pass1_libtest_s": {r["name"]: r.get("libtest_secs")
                            for r in one["runs"] if "not_run" not in r},
        "trace_bytes": {
            "originals": {r["name"]: r.get("trace_bytes")
                          for r in one["runs"] if "not_run" not in r},
            "refocused": {r["name"]: r.get("new_trace_bytes")
                          for r in ordered}},
        "shim_census": census,
    }
    step(f"H6: first focus {out['first_focus']}; {len(later_walls)} later "
         f"focus(es), mean {out['later_focus_mean_s']}s; shim census "
         f"{census['entries']} entries / {census['bytes']} bytes")
    return out


# --------------------------------------------------------------------- H7


def phase_h7(paths, cfg) -> dict:
    """H7: did nothing else move? THIS repository, not the clone.

    Three commands, each with its own generous ceiling and its own log: the
    corpus collector over EVERY case (design §3.4's three new `refocus`
    cases included), the whole Python suite, and `cargo test --workspace`.

    The corpus runs under a FRESH target of its own (§1.4) and under
    `SENSORIUM_CARGO_SENSORIUM`, the one variable `run_corpus` reads to find
    a driver; the Python suite runs under `plain_env()` plus that same
    variable, so the module that is skipped without a built driver RUNS and
    no store of this run can answer a test's question. H7 runs LAST because
    `cargo test --workspace` shares the driver's target and could relink the
    binary every other phase measured with.
    """
    mark_load("H7")
    driver = str(paths["sensorium_driver"])
    py = str(REPO / ".venv" / "bin" / "python")
    with logs_at(LOGS / "h7"):
        step("H7(corpus): the collector over every case")
        corpus_env = plain_env() | {
            "PYTHONDONTWRITEBYTECODE": "1",
            "SENSORIUM_CARGO_SENSORIUM": driver,
            "CARGO_TARGET_DIR": str(cfg["corpus_target"])}
        corpus = guarded([py, "corpus/run_corpus.py", "--json"], REPO,
                         "h7-corpus.log", corpus_env, cfg["corpus_timeout"],
                         "h7-corpus")
        step("H7(python): the whole suite")
        py_env = plain_env() | {"PYTHONDONTWRITEBYTECODE": "1",
                                "SENSORIUM_CARGO_SENSORIUM": driver}
        suite = guarded([py, "-m", "pytest", "-q"], REPO, "h7-pytest.log",
                        py_env, cfg["pytest_timeout"], "h7-pytest")
        step("H7(rust): cargo test --workspace")
        cargo_env = plain_env() | {
            "PYTHONDONTWRITEBYTECODE": "1",
            "CARGO_TARGET_DIR": str(paths["sensorium_rust_target"])}
        cargo = guarded(["cargo", "test", "--workspace"], REPO / "rust",
                        "h7-cargo.log", cargo_env, cfg["cargo_test_timeout"],
                        "h7-cargo")
    try:
        parsed = _json.loads(corpus["out"])
    except (ValueError, TypeError):
        parsed = None
    tail = [ln for ln in "\n".join((suite["out"], suite["err"])).splitlines()
            if ln.strip()]
    summary = next((ln for ln in reversed(tail)
                    if " passed" in ln or " failed" in ln or " error" in ln),
                   None)
    results = [ln for ln in "\n".join(
        (cargo["out"], cargo["err"])).splitlines()
        if ln.startswith("test result:")]
    out = {
        "corpus": {"rc": corpus["rc"], "wall_s": round(corpus["wall"], 3),
                   "log": corpus["log"], "timed_out": corpus["timed_out"],
                   "command": corpus["command"],
                   "target": str(cfg["corpus_target"]),
                   "json": parsed,
                   "cases": (parsed or {}).get("cases"),
                   "questions": (parsed or {}).get("questions"),
                   "failures": (parsed or {}).get("failures"),
                   "errors": (parsed or {}).get("errors"),
                   "skipped": (parsed or {}).get("skipped")},
        "python": {"rc": suite["rc"], "wall_s": round(suite["wall"], 3),
                   "summary": summary, "log": suite["log"],
                   "timed_out": suite["timed_out"],
                   "command": suite["command"]},
        "cargo": {"rc": cargo["rc"], "wall_s": round(cargo["wall"], 3),
                  "result_lines": results, "log": cargo["log"],
                  "timed_out": cargo["timed_out"],
                  "command": cargo["command"],
                  "target": str(paths["sensorium_rust_target"])},
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
    }
    step(f"H7: corpus rc {corpus['rc']} ({out['corpus']['cases']} cases, "
         f"{len(out['corpus']['failures'] or [])} failures); pytest rc "
         f"{suite['rc']}; cargo rc {cargo['rc']}")
    return out


__all__ = ["LOGS", "W1_OF", "W4_OF", "phase_h4", "phase_h5", "phase_h6",
           "phase_h7", "watch_triples"]
