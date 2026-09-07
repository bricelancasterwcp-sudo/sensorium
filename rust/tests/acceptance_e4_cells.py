"""The E4 endpoints, cell by cell: H1-H7 in the pre-registered shape.

A module of its own for the reason `acceptance_e9_cells.py` is one: no file
in this repository may pass 800 lines, and the seam is the schema's own. This
file builds the SEVEN ENDPOINT BLOCKS and owns the rules that decide when a
cell is not-measured; `acceptance_e4_schema.assemble_e4` puts them beside the
environment, the predictions and the ungated block. Every name here is
re-exported from the schema, so no caller's spelling changes.

THREE RULES THIS FILE ENFORCES BY ITSELF
----------------------------------------
* **A count over fewer than 61 pairs is not this record's number.** §1's
  kill 6 -- "a reader at its ceiling is the record" -- makes a smaller view a
  not-measured with its reason, never a smaller number published as the
  answer. Two drop lists carry that: `_incomplete_drops` (a pass that did not
  run, or a test the 2-hour bound never reached) nulls every cell of every
  endpoint; `_killed_drops` (an invocation cut off at its 1800 s ceiling)
  nulls every cell except the ones `SURVIVES_A_KILL` names, because a killed
  command leaves partial text that parses exactly like a whole answer.
* **An UNVERIFIABLE check is never counted as verified.** H4 publishes the
  verified counts and the unverifiable counts as separate cells and nothing
  here sums them. A licence line that CLAIMED an unverifiable check is its
  own cell, gated at 0.
* **No cell is ever filled from a prediction.** §1's numbers -- the 61
  names, the expected-MATCH list of all 61, the three triples' classes and
  exits -- are published under `predictions`, beside the measurements and
  never inside one.
"""

from __future__ import annotations

from acceptance_lib import meas
from acceptance_schema_rung3 import _drop                          # noqa: F401

#: Every endpoint's measurement cells, listed so `measurement_keys` can be
#: CHECKED against what the schema actually publishes: a cell added to a
#: block and forgotten here would escape the drop rules entirely and publish
#: a number from a loop that never finished.
MEASUREMENT_CELLS = {
    "H1": ("headline", "reached_the_driver", "exit_2_without_a_sentence"),
    "H2": ("headline", "build_failures", "outcomes_equal",
           "outcomes_unreadable"),
    "H3": ("headline", "diverged", "named_hazard", "findings",
           "refused_after_rerun", "readings_disagree"),
    "H4": ("headline", "env_verified", "exit_verified",
           "output_unverifiable", "children_unverifiable",
           "licences_granted", "claims_an_unverifiable_check"),
    "H5": ("headline", "class_as_predicted", "exit_as_predicted",
           "readings_disagree"),
    "H6": ("headline", "later_focus_mean_s", "later_focus_max_s",
           "shim_entries", "shim_bytes"),
    "H7": ("headline", "corpus_rc", "corpus_errors", "corpus_skipped",
           "pytest_rc", "pytest_summary", "cargo_rc"),
}


def measurement_keys(block: dict) -> set:
    """Every key of one endpoint whose value IS a measurement.

    Derived from the assembled block rather than declared, so
    `MEASUREMENT_CELLS` can be CHECKED against what the schema publishes.
    """
    return {k for k, v in block.items()
            if isinstance(v, dict)
            and {"value", "n", "lens", "dropped"} <= set(v)}


#: The one sentence every "this phase did not run" reason is built from, so
#: the cells cannot drift apart in what they say they did not measure.
NOT_RUN = "the phase did not run, so there is nothing to compare"

#: The cells that survive a KILLED invocation, and why. H1's headline is the
#: count of PRE-RERUN refusals: `refocus` prints its §2.3 sentence and exits
#: 2 BEFORE the driver child is launched, so an invocation that ran long
#: enough to hit an 1800 s ceiling had already passed that gate and cannot be
#: hiding one. Nothing else is in this position: every other number is over
#: what came back.
#:
#: No cell survives an INCOMPLETE pass. A test the 2-hour bound never reached
#: could have refused, so even H1's headline is a smaller number about a
#: smaller question there.
SURVIVES_A_KILL = {"H1": ("headline",)}

#: Which passes each endpoint's numbers are only true of. H7 is about THIS
#: repository rather than about the pairs, so it depends on neither.
NEEDS = {"H1": ("raw_pass2",), "H2": ("raw_pass1", "raw_pass2"),
         "H3": ("raw_pass1", "raw_pass2"), "H4": ("raw_pass2",),
         "H5": ("raw_pass2",), "H6": ("raw_pass1", "raw_pass2"), "H7": ()}


def _null(reason: str, lens: str, n=None) -> dict:
    return meas(None, n, lens, [reason])


def _null_cells(block: dict, names, reasons: list) -> dict:
    """Turn the named cells of `block` into not-measured, keeping their lens
    and their `n` and carrying every reason.

    A cell that is not a measurement (a raw sub-table, a command string) is
    left alone, and one that is already `null` keeps the reason it has.
    """
    if not reasons:
        return block
    for name in names:
        cell = block.get(name)
        if not isinstance(cell, dict) or "lens" not in cell:
            continue
        if cell.get("value") is None:
            cell["dropped"] = list(dict.fromkeys(
                list(cell["dropped"]) + reasons))
            continue
        nulled = _null(reasons[0], cell["lens"], cell["n"])
        nulled["dropped"] = list(dict.fromkeys(
            nulled["dropped"] + list(cell["dropped"]) + reasons[1:]))
        block[name] = nulled
    return block


def _pass(raw, key: str) -> dict:
    return raw.get(key) or {}


def _incomplete_drops(raw, endpoint: str) -> list[str]:
    """Why a count over "the 61" may not be trusted, named per pass.

    A pass that is absent from the record, and a pass whose loop did not
    reach every test, are both here: the first has no numbers at all and the
    second has numbers over a smaller set, and §1's kill 6 makes both a
    not-measured rather than a smaller answer.
    """
    out = []
    for key in NEEDS.get(endpoint, ()):
        p = raw.get(key)
        if not p:
            out.append(f"{key} is absent from the record")
            continue
        missing = p.get("budget_exhausted") or []
        if missing:
            out.append(f"{key}: {len(missing)} invocation(s) were never run "
                       f"-- §1.4's 2-hour loop bound was reached "
                       f"({missing[:3]}{' …' if len(missing) > 3 else ''})")
        n, measured = p.get("n"), p.get("measured")
        if (n is not None and measured is not None and measured != n
                and not missing):
            out.append(f"{key}: {measured} of {n} invocation(s) ran")
    return out


def _killed_drops(raw, endpoint: str) -> list[str]:
    """Invocations cut off at their 1800 s ceiling, as reasons."""
    out = []
    for key in NEEDS.get(endpoint, ()):
        killed = _pass(raw, key).get("killed") or []
        if killed:
            out.append(f"{key}: invocation(s) {killed[:3]}"
                       f"{' …' if len(killed) > 3 else ''} were KILLED at "
                       f"the ceiling; their output is partial")
    return out


def _apply_drops(block: dict, endpoint: str, raw) -> dict:
    """Both rules, applied once per endpoint so seven copies cannot drift."""
    incomplete = _incomplete_drops(raw, endpoint)
    killed = _killed_drops(raw, endpoint)
    names = MEASUREMENT_CELLS.get(endpoint, ())
    _null_cells(block, names, incomplete)
    keep = SURVIVES_A_KILL.get(endpoint, ())
    _null_cells(block, [n for n in names if n not in keep], killed)
    return block


def _reader_drop(block: dict | None, name: str) -> list[str]:
    """A reader command that hit its ceiling, as a reason."""
    if not block:
        return []
    if block.get("timed_out"):
        return [f"`{name}` was KILLED at {block.get('kill_s')} s; its output "
                "is partial"]
    return []


# ------------------------------------------------------------------- H1

H1_LENS = ("the 61 `sensorium refocus <run> --focus <name>` invocations of "
           "pass 2: the CLI's own exit and its printed `error: cannot "
           "refocus <run>: …; nothing was re-run` sentence (design §2.3's "
           "refusal table)")


def _h1(raw) -> dict:
    r = raw.get("raw_h1")
    if not r:
        return {
            "headline": _null(NOT_RUN, "pre-rerun refusals; " + H1_LENS, 61),
            "reached_the_driver": _null(NOT_RUN, "invocations that reached "
                                                 "the driver", 61),
            "exit_2_without_a_sentence": _null(
                NOT_RUN, "exit-2 answers carrying no §2.3 sentence", 61),
        }
    n = r.get("n")
    block = {
        "headline": meas(
            r.get("pre_rerun_refusal_count"), n,
            "FIRST reading, and the gate: pre-rerun refusals, of the "
            "invocations made -- the gate is 0, because each original is a "
            "single-target invocation with a live `workspace_root` and a "
            "driver on `SENSORIUM_CARGO_SENSORIUM`; " + H1_LENS, []),
        "reached_the_driver": meas(
            r.get("reached_the_driver"), n,
            "SECOND reading, on the count that can move independently: "
            "invocations whose driver child was LAUNCHED, read from the "
            "banner `refocus` prints immediately before it launches one -- "
            "not derived from the exit status", []),
        "exit_2_without_a_sentence": meas(
            len(r.get("exit_2_without_a_sentence") or []), n,
            "exit-2 answers carrying NO §2.3 sentence: the CLI refusing the "
            "CALL rather than the design's pre-rerun gate, which is neither "
            "reading's number and is named on its own", []),
        "refusals": r.get("pre_rerun_refusals"),
        "did_not_reach_the_driver": r.get("did_not_reach_the_driver"),
    }
    return _apply_drops(block, "H1", raw)


# ------------------------------------------------------------------- H2

H2_LENS = ("each re-run's own output: a libtest `test result:` line is the "
           "discriminator -- a unit that printed one was compiled and ran -- "
           "and the driver child's exit is recorded beside it")


def _h2(raw) -> dict:
    r = raw.get("raw_h2")
    if not r:
        return {
            "headline": _null(NOT_RUN, "re-runs that completed; " + H2_LENS,
                              61),
            "build_failures": _null(NOT_RUN, "focused build failures", 61),
            "outcomes_equal": _null(NOT_RUN, "re-runs whose libtest counts "
                                             "equal the original's", 61),
            "outcomes_unreadable": _null(NOT_RUN, "pairs where a summary "
                                                  "line could not be read",
                                         61),
        }
    n = r.get("n")
    block = {
        "headline": meas(
            r.get("completed"), n,
            "FIRST reading, and the gate: re-runs that COMPLETED, of the "
            "re-runs made; " + H2_LENS, []),
        "build_failures": meas(
            len(r.get("build_failures") or []), n,
            "focused BUILD failures -- the child launched and no libtest "
            "summary was printed. §1's kill 1 makes any a STOP: no fallback "
            "to an unfocused build, no retry under a narrower focus, no "
            "skipped test", []),
        "outcomes_equal": meas(
            r.get("outcomes_equal"), n,
            "SECOND reading: re-runs whose summed libtest "
            "passed/failed/ignored/measured/filtered counts equal the "
            "original's, of the pairs", []),
        "outcomes_unreadable": meas(
            len(r.get("outcomes_unreadable") or []), n,
            "pairs where one side printed no summary at all, so `equal` is "
            "`None` rather than `False`: an unparsed outcome is not an "
            "outcome", []),
        "failed_tests": r.get("build_failures"),
        "unequal_tests": r.get("outcomes_unequal"),
    }
    return _apply_drops(block, "H2", raw)


# ------------------------------------------------------------------- H3

H3_LENS = ("`diff_cmd.compare(orig, new)` through `refocus`, on the pair "
           "§1.4's pair rule found in the STORE (exactly one trace whose "
           "`refocus_of` is the original and whose recording started after "
           "the launch); the printed verdict word and the returned exit are "
           "read separately")


def _h3(raw) -> dict:
    r = raw.get("raw_h3")
    if not r:
        return {
            "headline": _null(NOT_RUN, "MATCH verdicts; " + H3_LENS, 61),
            "diverged": _null(NOT_RUN, "DIVERGED verdicts", 61),
            "named_hazard": _null(NOT_RUN, "DIVERGED reading as §1.2's "
                                           "named hazard", 61),
            "findings": _null(NOT_RUN, "DIVERGED reading as H3's finding",
                              61),
            "refused_after_rerun": _null(NOT_RUN, "REFUSED after the rerun",
                                         61),
            "readings_disagree": _null(NOT_RUN, "verdict word and exit "
                                                "disagreeing", 61),
        }
    n = r.get("n")
    block = {
        "headline": meas(
            r.get("match"), n,
            "THE GATE: MATCH verdicts, of the pairs compared; §1.2's "
            "expected-MATCH list is all 61; " + H3_LENS, []),
        "diverged": meas(
            len(r.get("diverged") or []), n,
            "DIVERGED verdicts, of the pairs -- a finding, not a STOP, "
            "recorded with its divergent event", []),
        "named_hazard": meas(
            len(r.get("diverged_named_hazard") or []), n,
            "DIVERGED on one of §1.2's three server tests where §1.4's "
            "DISCRIMINATOR holds -- the total causal event count over the "
            "worker tasks is preserved AND the MAIN stream MATCHes -- so it "
            "reads as the scheduler nondeterminism §1.2 pre-registers", []),
        "findings": meas(
            len(r.get("diverged_findings") or []), n,
            "DIVERGED that §1.4's discriminator does NOT excuse: the finding "
            "H3 means, with no prior explanation available to it", []),
        "refused_after_rerun": meas(
            len(r.get("refused_after_rerun") or []), n,
            "REFUSED AFTER the rerun -- §1's kill 2, a STOP: the instrument "
            "or the pairing, not the subject", []),
        "readings_disagree": meas(
            len(r.get("readings_disagree") or []), n,
            "SECOND reading: pairs where the printed verdict word and the "
            "returned exit (MATCH 0 / DIVERGED 1 / REFUSED 3) do not agree "
            "-- itself a finding, reported as one", []),
        "verdict_words": r.get("verdict_words"),
        "exits": r.get("exits"),
        "diverged_tests": r.get("diverged"),
        "unclassified": r.get("diverged_unclassified"),
        "per_test": [{k: v for k, v in p.items() if k != "step_rows"}
                     for p in (r.get("per_test") or [])],
        "divergent_events": {p["name"]: p.get("step_rows")
                             for p in (r.get("per_test") or [])
                             if p.get("step_rows")},
    }
    return _apply_drops(block, "H3", raw)


# ------------------------------------------------------------------- H4

H4_LENS = ("the licence block `refocus` prints after each verdict, and the "
           "`refocus_licence*` stamps in the NEW trace's meta. REPORTED, no "
           "gate -- and the verified counts and the unverifiable counts are "
           "two numbers that are never summed")


def _h4(raw) -> dict:
    r = raw.get("raw_h4")
    if not r:
        return {
            "headline": _null(NOT_RUN, "source checks verified; " + H4_LENS,
                              61),
            "env_verified": _null(NOT_RUN, "environment checks verified", 61),
            "exit_verified": _null(NOT_RUN, "exit-status checks verified",
                                   61),
            "output_unverifiable": _null(NOT_RUN, "output checks that could "
                                                  "not run", 61),
            "children_unverifiable": _null(NOT_RUN, "children checks that "
                                                    "could not run", 61),
            "licences_granted": _null(NOT_RUN, "licences granted", 61),
            "claims_an_unverifiable_check": _null(
                NOT_RUN, "licence lines claiming an unverifiable check", 61),
        }
    n = r.get("n")
    block = {
        "headline": meas(
            r.get("source_verified"), n,
            "SOURCE verified: the original's `source_hashes` re-hashed now "
            "and unchanged by content, of the pairs; " + H4_LENS, []),
        "env_verified": meas(
            r.get("env_verified"), n,
            "ENVIRONMENT verified: the two traces' recorded `env` compared "
            "and unchanged (the recorder's own variables named, not "
            "compared), of the pairs", []),
        "exit_verified": meas(
            r.get("exit_verified"), n,
            "EXIT verified: the re-run ended the same way as the original, "
            "read off the printed `exit: rerun <a>   original <b>` line", []),
        "output_unverifiable": meas(
            r.get("output_unverifiable"), n,
            "OUTPUT: `unverifiable (not recorded)` -- "
            "`capabilities.output` is false on a Rust trace, so the check "
            "could not run. REPORTED, and never counted as verified", []),
        "children_unverifiable": meas(
            r.get("children_unverifiable"), n,
            "CHILDREN: `unverifiable (not witnessed)` -- "
            "`capabilities.children` is false, so the check could not run. "
            "REPORTED, and never counted as verified", []),
        "licences_granted": meas(
            r.get("granted"), n,
            "licences GRANTED, of the pairs; a WITHHELD one lists its "
            "caveats and is counted separately", []),
        "claims_an_unverifiable_check": meas(
            len(r.get("claims_an_unverifiable_check") or []), n,
            "licence lines that CLAIM an unverifiable check as verified -- "
            "the named bug class; the gate is 0 and any is a finding rather "
            "than a pass", []),
        "withheld": r.get("withheld"),
        "no_licence_line": r.get("no_licence_line"),
        "reading": r.get("reading"),
        "per_test": r.get("per_test"),
    }
    return _apply_drops(block, "H4", raw)


# ------------------------------------------------------------------- H5

H5_LENS = ("§1.3's three triples, each `watch <NEW run> --at <qualname> "
           "--expr <expr>` on the refocused trace named there; the verdict "
           "CLASS printed and the EXIT returned are read separately, and W3 "
           "gates on the EXIT alone with its class REPORTED")


def _h5(raw) -> dict:
    r = raw.get("raw_h5")
    if not r:
        return {
            "headline": _null(NOT_RUN, "triples as predicted on their "
                                       "gates; " + H5_LENS, 3),
            "class_as_predicted": _null(NOT_RUN, "verdict classes as "
                                                 "predicted", 3),
            "exit_as_predicted": _null(NOT_RUN, "exit statuses as "
                                                "predicted", 3),
            "readings_disagree": _null(NOT_RUN, "triples where class and "
                                                "exit disagree", 3),
        }
    rows = r.get("triples") or []
    measured = [t for t in rows if "dropped" not in t]
    killed = [t["id"] for t in measured if t.get("timed_out")]
    missing = [t["id"] for t in rows if "dropped" in t]
    dropped = [f"{t['id']}: {t['dropped']}" for t in rows if "dropped" in t]
    if killed:
        dropped = dropped + [f"{i} was KILLED; its answer is partial"
                             for i in killed]
    n = len(rows)
    # A triple that was DROPPED (its NEW trace never reached the disk) is as
    # fatal to "all three as predicted" as one that was killed: two of three
    # is a smaller number about a smaller question, and §1's kill 6 makes
    # that a not-measured with its reason rather than the answer.
    if not measured or killed or missing:
        why = ("every triple was dropped" if not measured
               else f"triple(s) {killed} hit the reader ceiling" if killed
               else f"triple(s) {missing} had no NEW trace to run against")
        block = {k: _null(why, H5_LENS, n) for k in
                 ("headline", "class_as_predicted", "exit_as_predicted",
                  "readings_disagree")}
        for cell in block.values():
            cell["dropped"] += dropped
    else:
        block = {
            "headline": meas(
                r.get("as_predicted_on_their_gates"), n,
                "THE GATE: triples as §1.3 predicts them ON THEIR OWN GATE "
                "-- W1 and W4 on both readings, W3 on the exit; " + H5_LENS,
                dropped),
            "class_as_predicted": meas(
                r.get("class_as_predicted"), n,
                "FIRST reading: verdict classes as predicted (SATISFIED / "
                "SATISFIED / `error: no recorded code matches`)", dropped),
            "exit_as_predicted": meas(
                r.get("exit_as_predicted"), n,
                "SECOND reading: exit statuses as predicted (0 / 0 / 1)",
                dropped),
            "readings_disagree": meas(
                len(r.get("class_disagreements") or []), n,
                "triples where the class and the exit do not agree -- itself "
                "a finding about `Verdict`/`STATUS`", dropped),
        }
    block["triples"] = [{k: v for k, v in t.items() if k != "stdout"}
                        for t in rows]
    block["stdout"] = {t["id"]: t.get("stdout") for t in rows
                       if t.get("stdout")}
    block["reported_classes"] = r.get("reported_classes")
    block["bucket_counts"] = {
        t.get("id"): {k: t.get(k) for k in
                      ("sites", "evaluated", "hits", "not_captured",
                       "errors", "counts_line")}
        for t in rows if "dropped" not in t}
    return _apply_drops(block, "H5", raw)


# ------------------------------------------------------------------- H6

H6_LENS = ("the runner's own timing per invocation, with the FIRST focus "
           "distinguished from the later ones (the first pays for the rt "
           "build; the later ones for a fresh shim and the matched units); "
           "cargo's own `Finished … in <n>s` beside it; and the census of "
           "`<CARGO_TARGET_DIR>/sensorium/shim/*` taken once at the end")


def _h6(raw) -> dict:
    r = raw.get("raw_h6")
    if not r:
        return {
            "headline": _null(NOT_RUN, "the FIRST focus's wall, s; "
                              + H6_LENS),
            "later_focus_mean_s": _null(NOT_RUN, "later focuses' mean wall, "
                                                 "s"),
            "later_focus_max_s": _null(NOT_RUN, "the slowest later focus, s"),
            "shim_entries": _null(NOT_RUN, "entries under "
                                           "`<target>/sensorium/shim/*`"),
            "shim_bytes": _null(NOT_RUN, "bytes under "
                                         "`<target>/sensorium/shim/*`"),
        }
    first = r.get("first_focus") or {}
    census = r.get("shim_census") or {}
    later = r.get("later_focus_walls_s") or []
    block = {
        "headline": meas(
            first.get("wall_s"), 1,
            "REPORTED, NOT GATED. FIRST reading: the wall of the FIRST "
            "`sensorium refocus` invocation, seconds; " + H6_LENS, []),
        "later_focus_mean_s": meas(
            r.get("later_focus_mean_s"), len(later),
            "the mean wall of the LATER focuses, seconds, of the later "
            "invocations", []),
        "later_focus_max_s": meas(
            r.get("later_focus_max_s"), len(later),
            "the slowest later focus, seconds", []),
        "shim_entries": meas(
            census.get("entries"), None,
            "entries under `<CARGO_TARGET_DIR>/sensorium/shim/*`, counted "
            "once at the end (`rt_build.rs:207-211`); `null` is a directory "
            "that is not there, `0` is one that is empty", []),
        "shim_bytes": meas(
            census.get("bytes"), census.get("entries"),
            "total bytes under the shim directory, of its entries", []),
        "first_focus": first,
        "refocus_walls_s": r.get("refocus_walls_s"),
        "refocus_total_s": r.get("refocus_total_s"),
        "pass1_total_s": r.get("pass1_total_s"),
        "cargo_build_s": r.get("cargo_build_s"),
        "libtest_s": r.get("libtest_s"),
        "trace_bytes": r.get("trace_bytes"),
        "shim_census": census,
    }
    return _apply_drops(block, "H6", raw)


# ------------------------------------------------------------------- H7

H7_LENS = ("THIS repository, not the clone: `corpus/run_corpus.py --json` "
           "over EVERY case (design §3.4's three new `refocus` cases "
           "included) under a FRESH corpus target and "
           "`SENSORIUM_CARGO_SENSORIUM`; the whole Python suite under "
           "`plain_env()` plus that same variable; and `cargo test "
           "--workspace` in `rust/` under the workspace target")


def _h7(raw) -> dict:
    r = raw.get("raw_h7")
    dropped = _drop(raw, "raw_h7")
    if not r:
        return {"headline": _null(NOT_RUN, "corpus failures; " + H7_LENS),
                "corpus_rc": _null(NOT_RUN, "the collector's exit status"),
                "corpus_errors": _null(NOT_RUN, "cases that crashed the "
                                                "collector"),
                "corpus_skipped": _null(NOT_RUN, "cases the collector "
                                                 "SKIPPED"),
                "pytest_rc": _null(NOT_RUN, "`pytest -q` exit status"),
                "pytest_summary": _null(NOT_RUN, "the suite's summary line"),
                "cargo_rc": _null(NOT_RUN, "`cargo test --workspace` exit "
                                           "status")}
    c, py, cargo = ((r.get("corpus") or {}), (r.get("python") or {}),
                    (r.get("cargo") or {}))
    c_drop = dropped + _reader_drop(c, "run_corpus")
    failures = c.get("failures")
    out = {
        "headline": meas(
            (len(failures) if failures is not None else None),
            c.get("questions"),
            "FIRST reading: corpus questions whose printed answer is not the "
            "case's registered expectation, of the questions asked; "
            + H7_LENS,
            c_drop + ([] if failures is not None
                      else ["the collector printed no JSON to read failures "
                            "from"])),
        "corpus_rc": meas(c.get("rc"), c.get("cases"),
                          "SECOND reading: the collector's exit status, of "
                          "the cases it ran -- 0 is every case equal",
                          c_drop),
        "corpus_errors": meas(
            (len(c.get("errors") or []) if c.get("json") is not None
             else None), c.get("cases"),
            "harness errors -- a case that crashed the collector answered "
            "nothing and is not a pass",
            c_drop + ([] if c.get("json") is not None
                      else ["the collector printed no JSON"])),
        "corpus_skipped": meas(
            (len(c.get("skipped") or []) if c.get("json") is not None
             else None), c.get("cases"),
            "cases the collector SKIPPED, of the cases -- `run_corpus` skips "
            "a cargo case when it can find no driver and still exits 0, so a "
            "green H7 over a skipped corpus is not `every case equal`; the "
            "gate is 0",
            c_drop + ([] if c.get("json") is not None
                      else ["the collector printed no JSON"])),
        "pytest_rc": meas(py.get("rc"), None,
                          "`pytest -q` exit status -- 0 is green",
                          dropped + _reader_drop(py, "pytest")),
        "pytest_summary": meas(py.get("summary"), None,
                               "the suite's own summary line, recorded whole",
                               dropped + _reader_drop(py, "pytest")),
        "cargo_rc": meas(cargo.get("rc"),
                         len(cargo.get("result_lines") or []),
                         "`cargo test --workspace` exit status, of its `test "
                         "result:` lines",
                         dropped + _reader_drop(cargo, "cargo test")),
        "corpus_failures": failures,
        "corpus_skipped_cases": c.get("skipped"),
        "corpus_cases": c.get("cases"),
        "corpus_questions": c.get("questions"),
        "cargo_result_lines": cargo.get("result_lines"),
        "walls_s": {"corpus": c.get("wall_s"), "python": py.get("wall_s"),
                    "cargo": cargo.get("wall_s")},
        "logs": {"corpus": c.get("log"), "python": py.get("log"),
                 "cargo": cargo.get("log")},
        "driver_sha256_after": r.get("driver_sha256_after"),
    }
    # The same rule everywhere else, applied to H7's three commands: a
    # collector, a suite or a `cargo test` cut off at its ceiling printed
    # part of an answer, and the exit status it never returned is `None`.
    for names, block_, label in (
            (("headline", "corpus_rc", "corpus_errors", "corpus_skipped"),
             c, "run_corpus"),
            (("pytest_rc", "pytest_summary"), py, "pytest"),
            (("cargo_rc",), cargo, "cargo test")):
        _null_cells(out, names, _reader_drop(block_, label))
    return out
