"""E15's ten endpoints, cell by cell: §1's rules, turned into `holds`.

`e15_read.py` parses and decides nothing; this file decides and parses
nothing. Every rule below is §1's table row for that endpoint, and the four
words a cell may carry are §1's own vocabulary:

* **PASS** -- the endpoint's pre-committed reading held;
* **finding** -- §1 says so IN THAT ROW. Only H2 ("a harness that ended
  differently is a **finding** carrying the exit, not a STOP") and H4's
  unexpected DIVERGED ("an unexpected DIVERGED is a **finding** recorded
  with the divergent event") carry it;
* **STOP** -- §1 says so in that row (H3's refusal after the re-run, H4's
  comparator REFUSED), or §1 gates the endpoint and names no softer word.
  An endpoint that §1 gates and does not downgrade is a STOP: that is this
  record family's default, and writing it down here is what keeps the
  instrument from inventing a gentler one after a number is read;
* **reported** -- H9 alone. §1: "reported, no gate".

THE SHAPE
---------
Each cell is `lens.cell(value, n, dropped, holds=…, evidence=…)`, which is
`{value, n, dropped, holds, evidence}` -- and `lens.stamp` adds `lens` once,
at assembly time. The record's none-versus-zero rule runs through it: a
`value` of `null` with a non-empty `dropped` is the only spelling of "not
measured", and a `0` is measured-and-zero and carries no reason.

`holds` is `True`/`False` where §1 gates, `None` where it does not (H9) and
`None` where the phase did not run. A cell whose phase is missing is nulled
whole rather than scored over an empty population: a `0 of 0` that reads as
a pass is the failure this rule exists for.

THE RAW RECORD THIS READS
--------------------------
`typescript/acceptance/e15.py` writes it, and the keys used here are:

    preflight   {dry_run, driver_version, …}
    originals   {U, harness_exit, invocation, …}
    loop        {rows: [{n, test_file, klass, focus, exit, wall_s,
                harness_duration_s, wall_minus_harness_s, spool_bytes,
                trace_bytes, transcript, parsed}]}
    controls    {B: {…, parsed}, C: {…, traces_before, traces_after, parsed}}
    fences      {checks: [{name, command, exit, wall_s}], needle, e_fences}
    reads       {reads: [{label, row, kind, command, predicted_class,
                predicted_exit, exit, parsed}]}

`survey` is `e15_read.parse_survey(…)["rows"]`: the locked table, which is
where every row's CLASS comes from. H4 asks a different question of a
deterministic row than of a nondeterministic one, and taking the class from
anywhere but the byte-locked table would let the population move after a
verdict printed.
"""
from __future__ import annotations

import json
from pathlib import Path

from lens import cell

#: §1's own words for the failing side of each endpoint. `finding` where §1
#: writes it, `STOP` where §1 gates without naming a softer word. H4 decides
#: between the two per row and is not in this table.
FAIL_WORD = {"H1": "STOP", "H2": "finding", "H3": "STOP", "H5": "STOP",
             "H6": "STOP", "H7": "STOP", "H8": "STOP", "H10": "STOP"}

NOT_MEASURED = "not measured"

#: Design 2026-09-13 §2.3, refusal 1 -- the sentence control C predicts,
#: carried here as a literal because it is what H8 COMPARES against. The cell
#: publishes both what it wanted and what it got, so a changed sentence reads
#: as a finding rather than as a silent pass.
WINDOW_REFUSAL = ("--window is not available for a TypeScript trace (the "
                  "recorder has no per-activation gate); nothing was re-run")

#: `refocus_licence.env_of`'s clause: the recorder's own variables, named on
#: every line rather than counted. H5 requires it on all 31.
RECORDER_SET = "the recorder's own, also not compared:"
#: `refocus_world._sets_clause`'s two halves for harness set 1. The count
#: clause is required only where the set actually fired.
HARNESS_SET = "harness set 1"
HARNESS_COUNT = " harness variable(s) differ: "


def _null(reason: str, n=None) -> dict:
    return cell(None, n, [reason], holds=None,
                evidence={"word": NOT_MEASURED, "rule": reason})


def _rows(raw) -> list[dict] | None:
    loop = (raw or {}).get("loop")
    if not isinstance(loop, dict):
        return None
    rows = loop.get("rows")
    return rows if isinstance(rows, list) else None


def _measured(rows) -> list[dict]:
    """The rows the loop actually ran. A row it skipped carries `not_run` and
    is counted nowhere: a smaller population published as the answer is what
    §1's kill rules forbid."""
    return [r for r in rows if "not_run" not in r]


def _word(holds: bool, endpoint: str) -> str:
    return "PASS" if holds else FAIL_WORD[endpoint]


def _compared(seen) -> tuple[list, list]:
    """The rows that actually produced a pair, and why the others did not.

    A row whose `refocus` refused BEFORE the re-run never ran a suite, so it
    has no harness exit, no candidate, no verdict and no licence. H1 counts
    it -- and gates at 0, so one of them already STOPs this record -- and
    H2-H5 drop it BY NAME rather than scoring it as a re-run that ended
    differently, a pair that was not found and a verdict that was not MATCH.
    One fact reported at four endpoints reads as four failures.

    The `dropped` list is `lens.cell`'s partial-measurement shape: a non-null
    value with a non-empty `dropped` says some rows were dropped and the rest
    measured, which is a fact the record can print.
    """
    refused = [r for r in seen if (r.get("parsed") or {}).get("refusal")]
    rest = [r for r in seen if r not in refused]
    if not refused:
        return rest, []
    return rest, [f"{len(refused)} row(s) refused before the re-run and ran no "
                  "suite, so they carry no pair to read: "
                  + ", ".join(f"{r['n']} ({r['test_file']})"
                              for r in refused[:6])
                  + (" …" if len(refused) > 6 else "")]


def _by_class(rows, survey) -> dict:
    """Each row's CLASS, from the locked survey and from nowhere else."""
    table = {r["n"]: r["klass"] for r in survey}
    return {r["n"]: table.get(r["n"], r.get("klass")) for r in rows}


NO_LOOP = ("the loop did not run, so there is nothing to read over the "
           "survey's rows")


# ------------------------------------------------------------------- H1


def h1(raw, survey) -> dict:
    """§1: **0 of 31** refusals -- each member carries `harness_command`,
    `harness_cwd`, one `test_file`, tier `call`.

    A pre-rerun refusal is `refocus_cmd._refuse`'s: exit 2, one sentence,
    nothing re-run. Counted separately from the refusal the pair lookup
    raises AFTER a whole suite has run, which is H3's.
    """
    rows = _rows(raw)
    if rows is None:
        return _null(NO_LOOP)
    seen = _measured(rows)
    refusals = [{"n": r["n"], "test_file": r["test_file"],
                 "exit": r.get("exit"),
                 "sentence": (r.get("parsed") or {}).get("refusal")}
                for r in seen if (r.get("parsed") or {}).get("refusal")]
    holds = not refusals
    return cell(len(refusals), len(seen), [], holds=holds,
                evidence={"word": _word(holds, "H1"),
                          "rule": "0 refusals before the re-run, of the rows "
                                  "the loop ran",
                          "refusals": refusals})


# ------------------------------------------------------------------- H2


def h2(raw, survey) -> dict:
    """§1: **31 of 31** harness exits equal to `U`'s (status, signal,
    `waited`); a harness that ended differently is a **finding** carrying the
    exit, not a STOP.

    The re-run's side is read off the transcript's own `exit: rerun …
    original …` line and compared against the ORIGINALS' invocation exit,
    which is what `U` is.
    """
    rows = _rows(raw)
    if rows is None:
        return _null(NO_LOOP)
    want = ((raw or {}).get("originals") or {}).get("harness_exit")
    seen, dropped = _compared(_measured(rows))
    equal, findings = 0, []
    for r in seen:
        got = (r.get("parsed") or {}).get("exit_rerun")
        if got is not None and got == want:
            equal += 1
        else:
            findings.append({"n": r["n"], "test_file": r["test_file"],
                             "exit_rerun": got, "expected": want,
                             "exit_original": (r.get("parsed") or {}).get(
                                 "exit_original"),
                             "process_exit": r.get("exit")})
    holds = not findings and bool(seen)
    return cell(equal, len(seen), dropped, holds=holds,
                evidence={"word": _word(holds, "H2"),
                          "rule": "the re-run's harness exit equals the "
                                  "originals' invocation exit, on every row",
                          "originals_harness_exit": want,
                          "findings": findings})


# ------------------------------------------------------------------- H3


def h3(raw, survey) -> dict:
    """§1: **31 of 31** exactly one candidate by `test_file`; linked count =
    `U`'s member count on **31 of 31**; a REFUSED after the re-run on the
    lookup is a **STOP** (the pairing).

    The linked count is `siblings + 1`: the pair is one of the traces the
    re-run linked, and the sibling count on the pair line is the rest.
    """
    rows = _rows(raw)
    if rows is None:
        return _null(NO_LOOP)
    u = ((raw or {}).get("originals") or {}).get("U")
    seen, dropped = _compared(_measured(rows))
    lookup, linked_findings, both = [], [], 0
    for r in seen:
        p = r.get("parsed") or {}
        one = not p.get("lookup_refusal")
        siblings = (p.get("pair") or {}).get("siblings")
        linked = None if siblings is None else siblings + 1
        if not one:
            lookup.append({"n": r["n"], "test_file": r["test_file"],
                           "sentence": p.get("refused_after_rerun")})
        if linked != u:
            linked_findings.append({"n": r["n"], "test_file": r["test_file"],
                                    "linked": linked, "U": u,
                                    "siblings": siblings})
        if one and linked == u:
            both += 1
    holds = not lookup and not linked_findings and bool(seen)
    return cell(both, len(seen), dropped, holds=holds,
                evidence={"word": _word(holds, "H3"),
                          "rule": "exactly one candidate by test file AND a "
                                  "linked count equal to U, on every row",
                          "exactly_one_candidate": len(seen) - len(lookup),
                          "linked_equal_to_U": len(seen) - len(linked_findings),
                          "U": u,
                          "lookup_refusals": lookup,
                          "linked_findings": linked_findings})


# ------------------------------------------------------------------- H4


def h4(raw, survey) -> dict:
    """§1: MATCH on every deterministic row; an unexpected DIVERGED is a
    **finding** recorded with the divergent event; a REFUSED from the
    comparator is a **STOP**.

    The population is the DETERMINISTIC rows of the locked survey. A
    nondeterministic or unsurveyed row's verdict is a READING: it is
    published under its own name and gates nothing, which is the whole
    reason the survey classes anything.
    """
    rows = _rows(raw)
    if rows is None:
        return _null(NO_LOOP)
    klass = _by_class(rows, survey)
    seen, dropped = _compared(_measured(rows))
    expected = [r for r in seen if klass.get(r["n"]) == "deterministic"]
    matched, findings, refusals, readings = 0, [], [], []
    for r in seen:
        p = r.get("parsed") or {}
        verdict = p.get("verdict")
        if verdict == "REFUSED" and not p.get("lookup_refusal"):
            refusals.append({"n": r["n"], "test_file": r["test_file"],
                             "why": p.get("refused_after_rerun"),
                             "klass": klass.get(r["n"])})
            continue
        if klass.get(r["n"]) != "deterministic":
            readings.append({"n": r["n"], "test_file": r["test_file"],
                             "klass": klass.get(r["n"]), "verdict": verdict,
                             "divergent_line": p.get("divergent_line")})
            continue
        if verdict == "MATCH":
            matched += 1
        else:
            findings.append({"n": r["n"], "test_file": r["test_file"],
                             "verdict": verdict,
                             "diverged_step": p.get("diverged_step"),
                             "divergent_line": p.get("divergent_line")})
    holds = not findings and not refusals and bool(expected)
    if holds:
        word = "PASS"
    elif refusals:
        word = "STOP"
    else:
        word = "finding"
    return cell(matched, len(expected), dropped, holds=holds,
                evidence={"word": word,
                          "rule": "MATCH on every deterministic row of the "
                                  "locked survey; a nondeterministic or "
                                  "unsurveyed row's verdict is a reading",
                          "findings": findings,
                          "comparator_refusals": refusals,
                          "readings": readings})


# ------------------------------------------------------------------- H5


def _h5_sums(seen, deterministic) -> tuple[dict, dict, list]:
    """§5's row, summed over the rows the loop ran."""
    from e15_read import (UNVERIFIABLE_CHILDREN, UNVERIFIABLE_OUTPUT,
                          UNVERIFIABLE_THREADS, claims_an_unverifiable_check)
    sums = {"rows": len(seen), "source_verified": 0, "env_verified": 0,
            "recorder_set_named": 0, "harness_set_named": 0,
            "harness_set_counted": 0, "unverifiable_output": 0,
            "unverifiable_children": 0, "unverifiable_threads": 0,
            "harness_exit_equal": 0, "claims_an_unverifiable_check": 0}
    claims: list = []
    for r in seen:
        p = r.get("parsed") or {}
        env_line = p.get("env_line") or ""
        unverifiable = p.get("unverifiable") or []
        sums["source_verified"] += p.get("source_status") == "unchanged"
        sums["env_verified"] += p.get("env_status") == "unchanged"
        sums["recorder_set_named"] += RECORDER_SET in env_line
        if HARNESS_SET in env_line:
            sums["harness_set_named"] += 1
            sums["harness_set_counted"] += HARNESS_COUNT in env_line
        sums["unverifiable_output"] += UNVERIFIABLE_OUTPUT in unverifiable
        sums["unverifiable_children"] += UNVERIFIABLE_CHILDREN in unverifiable
        sums["unverifiable_threads"] += UNVERIFIABLE_THREADS in unverifiable
        sums["harness_exit_equal"] += bool(p.get("exit_equal"))
        bad = claims_an_unverifiable_check(p)
        if bad:
            sums["claims_an_unverifiable_check"] += len(bad)
            claims.append({"n": r["n"], "test_file": r["test_file"],
                           "points": bad,
                           "unverifiable": unverifiable})
    granted = sum(1 for r in deterministic
                  if (r.get("parsed") or {}).get("licence") == "granted")
    expected_granted = [r for r in deterministic
                        if (r.get("parsed") or {}).get("verdict") == "MATCH"]
    sums["granted_on_expected_granted"] = (
        f"{granted} of {len(expected_granted)}")
    return sums, {"granted": granted,
                  "expected_granted": len(expected_granted),
                  "expected_granted_rows": [r["n"] for r in expected_granted]}, claims


def h5(raw, survey) -> dict:
    """§1: reported per pair and summed -- source verified 31 of 31;
    environment verified 31 of 31 with the recorder's set NAMED on every line
    and harness set 1's count where it differs; output, children, threads
    UNVERIFIABLE 31 of 31, each printed; harness exit equal 31 of 31; **0**
    licence lines claiming an unverifiable check as verified; GRANTED on
    every MATCHed deterministic row.

    The value is how many of those seven clauses held, out of seven, on
    `e_fences.py`'s "X of Y" shape: a reader sees which clause failed rather
    than a bare `False` whose population is invisible. The sums themselves
    are in the evidence, one per clause.
    """
    rows = _rows(raw)
    if rows is None:
        return _null(NO_LOOP)
    klass = _by_class(rows, survey)
    seen, dropped = _compared(_measured(rows))
    deterministic = [r for r in seen if klass.get(r["n"]) == "deterministic"]
    sums, granted, claims = _h5_sums(seen, deterministic)
    n = len(seen)
    clauses = {
        "source verified on every row": sums["source_verified"] == n,
        "environment verified on every row": sums["env_verified"] == n,
        "the recorder's set named on every line":
            sums["recorder_set_named"] == n,
        "harness set 1's count printed wherever the set differs":
            sums["harness_set_counted"] == sums["harness_set_named"],
        "output, children and threads printed UNVERIFIABLE on every row":
            (sums["unverifiable_output"] == n
             and sums["unverifiable_children"] == n
             and sums["unverifiable_threads"] == n),
        "harness exit equal on every row": sums["harness_exit_equal"] == n,
        "0 licence lines claiming an unverifiable check as verified":
            sums["claims_an_unverifiable_check"] == 0,
        "GRANTED on every MATCHed deterministic row":
            granted["granted"] == granted["expected_granted"],
    }
    held = sum(1 for v in clauses.values() if v)
    holds = held == len(clauses) and bool(seen)
    return cell(held, len(clauses), dropped, holds=holds,
                evidence={"word": _word(holds, "H5"),
                          "rule": "§5's row, summed over every row the loop "
                                  "ran; an UNVERIFIABLE check is printed and "
                                  "never counted as verified",
                          "clauses": clauses, "sums": sums,
                          "granted": granted, "claims": claims})


# ------------------------------------------------------------------- H6


def h6(raw, survey) -> dict:
    """§1: three `watch --at <spec> --expr …` triples and one `flow --value`
    on three NEW traces named in §1, answering as predicted (verdict class
    and exit).

    Both halves are compared, because §1 names both. A read that answered
    with the predicted word under a different exit is a finding about the
    command, and an instrument that compared only the word would never see
    it.
    """
    block = (raw or {}).get("reads")
    reads = (block or {}).get("reads")
    if not isinstance(reads, list):
        return _null("the reads did not run, so §1's four predictions were "
                     "never compared")
    ok, findings = 0, []
    for r in reads:
        got = (r.get("parsed") or {}).get("verdict")
        same = (got == r.get("predicted_class")
                and r.get("exit") == r.get("predicted_exit"))
        if same:
            ok += 1
        else:
            findings.append({"label": r.get("label"), "row": r.get("row"),
                             "kind": r.get("kind"),
                             "command": r.get("command"),
                             "verdict": got,
                             "predicted_class": r.get("predicted_class"),
                             "exit": r.get("exit"),
                             "predicted_exit": r.get("predicted_exit")})
    holds = ok == len(reads) and bool(reads)
    return cell(ok, len(reads), [], holds=holds,
                evidence={"word": _word(holds, "H6"),
                          "rule": "each read's verdict class AND its exit "
                                  "equal to the survey's prediction",
                          "reads": reads, "findings": findings})


# ------------------------------------------------------------------- H7


def h7(raw, survey) -> dict:
    """§1, control B: `plant_edit.py` appends one failing test to one
    selected file in the copy; its refocus reads `source: CHANGED` naming the
    file and `licence: WITHHELD` with that reason, whatever the verdict;
    **1 of 1**.

    "Naming the file" is the BASENAME: `refocus_world._source_state` prints
    `Path(p).name` for each changed file, and asserting a repo-relative path
    would be asserting a spelling the command never uses.
    """
    b = ((raw or {}).get("controls") or {}).get("B")
    if not isinstance(b, dict) or not b.get("ran"):
        return _null("control B did not run", 1)
    p = b.get("parsed") or {}
    name = Path(b.get("test_file") or "").name
    source_line = p.get("source_line") or ""
    reasons = p.get("withheld_reasons") or []
    claims = {
        "`source: CHANGED` names the edited file":
            p.get("source_status") == "CHANGED" and bool(name)
            and name in source_line,
        "`licence: WITHHELD`": p.get("licence") == "WITHHELD",
        "a withheld reason names the source change":
            any("source" in r.lower() and name in r for r in reasons),
    }
    holds = all(claims.values())
    return cell(1 if holds else 0, 1, [], holds=holds,
                evidence={"word": _word(holds, "H7"),
                          "rule": "source CHANGED naming the file and a "
                                  "WITHHELD licence carrying that reason; "
                                  "the verdict is a reading",
                          "claims": claims,
                          "verdict": p.get("verdict"),
                          "row": b.get("row"), "test_file": b.get("test_file"),
                          "source_line": source_line,
                          "withheld_reasons": reasons,
                          # Where the source finding went when the verdict was
                          # DIVERGED: `report` prints no licence line at all
                          # then -- the licence belongs to a MATCH -- and the
                          # world findings are printed under "differences in
                          # the world between the two runs". Evidence, so §3
                          # can state WHERE the reason appeared; the claims
                          # above stay §1's words.
                          "world_caveats": p.get("world_caveats") or [],
                          "licence_is_absent_on_a_diverged_verdict": (
                              p.get("verdict") == "DIVERGED"
                              and p.get("licence") is None),
                          # The LENS is never written: the runner restores the
                          # edited file from it and compares the sha.
                          "lens_restored": bool(b.get("restored")
                                                and b.get("sha_equal")),
                          "process_exit": b.get("exit")})


# ------------------------------------------------------------------- H8


def h8(raw, survey) -> dict:
    """§1, control C: `refocus <member> --window 1` on one original: exit 2,
    the §2.3 sentence, and the store's trace count UNCHANGED before and
    after; **1 of 1**.

    The store count is the half that tests the claim rather than the print:
    "nothing was re-run" is a statement about the world.
    """
    c = ((raw or {}).get("controls") or {}).get("C")
    if not isinstance(c, dict) or not c.get("ran"):
        return _null("control C did not run", 1)
    p = c.get("parsed") or {}
    before, after = c.get("traces_before"), c.get("traces_after")
    claims = {
        "exit 2": c.get("exit") == 2,
        "the §2.3 refusal-1 sentence, verbatim": p.get("refusal") ==
                                                 WINDOW_REFUSAL,
        "the trace count is unchanged":
            before is not None and before == after,
    }
    holds = all(claims.values())
    return cell(1 if holds else 0, 1, [], holds=holds,
                evidence={"word": _word(holds, "H8"),
                          "rule": "exit 2, design §2.3's refusal-1 sentence, "
                                  "and a trace count equal before and after",
                          "claims": claims,
                          "expected_sentence": WINDOW_REFUSAL,
                          "sentence": p.get("refusal"),
                          "row": c.get("row"),
                          # §1 spells control C as `refocus <member> --window
                          # 1`. `--focus` is a REQUIRED argument of the
                          # command, so the row's own spec is passed with the
                          # window; without it argparse refuses the CALL with
                          # a usage line (also exit 2) and refusal 1 never
                          # runs at all. The literal form is run too and
                          # recorded here, so §3 states the gap rather than a
                          # reader inferring it.
                          "as_written": c.get("as_written"),
                          "focus_added_because": (
                              "`--focus` is required by `sensorium refocus`; "
                              "§1's shorthand omits it and argparse would "
                              "refuse the call before design §2.3's refusal "
                              "1 could run"),
                          "traces_before": before, "traces_after": after})


# ------------------------------------------------------------------- H9


def h9(raw, survey) -> dict:
    """§1: reported, no gate -- per refocus the wall from launch to verdict,
    the harness's own `Duration`, the spool bytes and trace bytes the
    invocation added; the store and spool totals at the end.

    The third number is `wall_minus_harness_s` and is NAMED as that, never as
    something narrower: neither `ts/driver._convert` nor `ts/ingest.
    ingest_dir` prints a wall of its own, so what the subtraction leaves
    holds the driver's resolver, the spawn, the ingest and `refocus`'s own
    compare together, and no instrument here can say how it divides.
    """
    rows = _rows(raw)
    if rows is None:
        return _null(NO_LOOP)
    seen = _measured(rows)
    per = [{"n": r["n"], "test_file": r["test_file"], "focus": r.get("focus"),
            "wall_s": r.get("wall_s"),
            "harness_duration_s": r.get("harness_duration_s"),
            "wall_minus_harness_s": r.get("wall_minus_harness_s"),
            "spool_bytes": r.get("spool_bytes"),
            "trace_bytes": r.get("trace_bytes")}
           for r in seen]

    def total(key):
        values = [p[key] for p in per if p[key] is not None]
        return round(sum(values), 3) if values else None

    totals = {key: total(key) for key in
              ("wall_s", "harness_duration_s", "wall_minus_harness_s",
               "spool_bytes", "trace_bytes")}
    measured = sum(1 for p in per if p["wall_s"] is not None)
    return cell(measured, len(seen), [], holds=None,
                evidence={"word": "reported",
                          "rule": "reported, no gate: per refocus the wall, "
                                  "vitest's own Duration, the difference "
                                  "between them named as `wall minus "
                                  "harness`, and the bytes the invocation "
                                  "added",
                          "per_refocus": per, "totals": totals,
                          # The originals' own cost, and only that: the whole
                          # block carries a member per test file and is
                          # published once under `reported`, so copying it
                          # here would put 372 rows of meta inside a cost
                          # cell.
                          "originals": {k: ((raw or {}).get("originals")
                                            or {}).get(k)
                                        for k in ("exit", "wall_s",
                                                  "harness_duration_s",
                                                  "spool_bytes", "U",
                                                  "invocation")},
                          "store_at_the_end": (raw or {}).get("cleanup")})


# ------------------------------------------------------------------- H10


def h10(raw, survey) -> dict:
    """§1: corpus every case equal, all three languages, `--require-driver`,
    the three new cases included; pytest; `cargo test --workspace`; `npm
    --prefix typescript test`; the probes; `tests/test_ceiling.py`; the E7
    needle on the new output; `e_fences.py` legacy and branch, with the
    fence's report listing NO fenced path.

    The fence's own REPORT is a claim of its own, beside the two fence cells:
    a green `e_fences.py` whose `diff_stat_lines` names a file would mean
    this slice moved something §1 says it does not touch.
    """
    fences = (raw or {}).get("fences")
    if not isinstance(fences, dict):
        return _null("the fences did not run")
    checks = fences.get("checks") or []
    needle = fences.get("needle") or {}
    ef = fences.get("e_fences") or {}
    claims, findings = {}, []
    for chk in checks:
        ok = chk.get("exit") == 0
        claims[f"{chk.get('name')} exits 0"] = ok
        if not ok:
            findings.append({"name": chk.get("name"),
                             "command": chk.get("command"),
                             "exit": chk.get("exit"),
                             "wall_s": chk.get("wall_s")})
    hits = needle.get("hits") or []
    claims["the E7 needle finds no `sensorium run --focus`"] = not hits
    if hits:
        findings.append({"name": "E7 needle", "hits": hits})
    for name in ("E-legacy", "E-branch"):
        got = ef.get(name) or {}
        ok = (got.get("value") is not None and got.get("n")
              and got.get("value") == got.get("n"))
        claims[f"{name} holds every claim it makes"] = bool(ok)
        if not ok:
            findings.append({"name": name, "cell": got})
    listed = (ef.get("E-legacy") or {}).get("diff_stat_lines")
    claims["the fence's report lists no fenced path"] = listed == []
    if listed:
        findings.append({"name": "E-legacy report", "diff_stat_lines": listed})
    held = sum(1 for v in claims.values() if v)
    holds = held == len(claims) and bool(claims)
    return cell(held, len(claims), [], holds=holds,
                evidence={"word": _word(holds, "H10"),
                          "rule": "every suite exits 0, the needle finds "
                                  "nothing, and the fence's report lists no "
                                  "fenced path",
                          "claims": claims, "findings": findings,
                          "checks": checks, "needle": needle})


CELLS = {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5,
         "H6": h6, "H7": h7, "H8": h8, "H9": h9, "H10": h10}


def cells(raw: dict, survey: list) -> dict:
    """§1's ten endpoints, in §1's order."""
    return {name: fn(raw, survey) for name, fn in CELLS.items()}


def stops(payload: dict) -> list[str]:
    """Every cell whose word is STOP, named. `assemble_e15.py` turns a
    non-empty list into `DONE-WITH-STOP`."""
    return [f"{name}: {json.dumps(c['evidence']['rule'])}"
            for name, c in payload.items()
            if isinstance(c, dict) and (c.get("evidence") or {}).get("word")
            == "STOP"]
