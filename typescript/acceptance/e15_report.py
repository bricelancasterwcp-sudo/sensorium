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
from lens import cell

#: §1's own words for the failing side of each endpoint. `finding` where §1
#: writes it, `STOP` where §1 gates without naming a softer word. H4 decides
#: between the two per row and is not in this table.
FAIL_WORD = {"H1": "STOP", "H2": "finding", "H3": "STOP", "H5": "STOP",
             "H6": "STOP", "H7": "STOP", "H7p": "STOP", "H8": "STOP",
             "H8p": "STOP", "H10": "STOP"}

#: The endpoints whose population is the LOCKED 31. A row the loop did not
#: reach makes each of them a partial reading, and §1's kill rules -- "a
#: reader at its ceiling is the record" -- say a smaller population is not
#: this record's number. So a `not_run` row NAMES itself in every loop cell's
#: `dropped` and takes `holds` to False on these five.
LOOP_GATED = ("H1", "H2", "H3", "H4", "H5")

NOT_MEASURED = "not measured"

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
    """The rows the loop actually ran.

    A row it skipped carries `not_run` and is scored NOWHERE -- but it is
    never silent either: `_not_run` below names it in every loop cell's
    `dropped`, and `LOOP_GATED`'s five cells cannot hold while one exists.
    A smaller population published as the answer is what §1's kill rules
    forbid, and a PASS over 29 of 31 rows would be exactly that.
    """
    return [r for r in rows if "not_run" not in r]


def _not_run(rows) -> list[str]:
    """One reason per row the loop did not reach, NAMED.

    The reason is the row's own (`not_run`), so a budget-exhausted loop and a
    row skipped for any later cause read differently in the record.
    """
    return [f"row {r['n']} not run: {r.get('not_run')}"
            for r in rows if "not_run" in r]


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
    missing = _not_run(rows)
    refusals = [{"n": r["n"], "test_file": r["test_file"],
                 "exit": r.get("exit"),
                 "sentence": (r.get("parsed") or {}).get("refusal")}
                for r in seen if (r.get("parsed") or {}).get("refusal")]
    holds = not refusals and not missing
    return cell(len(refusals), len(seen), missing, holds=holds,
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
    dropped = _not_run(rows) + dropped
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
    holds = not findings and bool(seen) and not _not_run(rows)
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
    dropped = _not_run(rows) + dropped
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
    holds = (not lookup and not linked_findings and bool(seen)
             and not _not_run(rows))
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
    dropped = _not_run(rows) + dropped
    # Ruling P18, first half: a row whose pair LOOKUP refused is H3's STOP,
    # and H3 alone. H4 names it here and scores it nowhere, so one fact is
    # not reported twice under two endpoints.
    lookup = [r for r in seen if (r.get("parsed") or {}).get("lookup_refusal")]
    seen = [r for r in seen if r not in lookup]
    dropped = dropped + [f"row {r['n']}: lookup refused -- see H3"
                         for r in lookup]
    expected = [r for r in seen if klass.get(r["n"]) == "deterministic"]
    matched, findings, refusals, readings, silent = 0, [], [], [], []
    for r in seen:
        p = r.get("parsed") or {}
        verdict = p.get("verdict")
        if verdict == "REFUSED":
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
        elif verdict is None:
            # Ruling P18, second half: §1's `finding` is for an UNEXPECTED
            # DIVERGED, which is a verdict the comparator issued. A row that
            # issued none at all -- a killed invocation, a crash, a transcript
            # that ends mid-answer -- is not that; it is this module's own
            # default for a gate that did not hold, which is STOP.
            silent.append({"n": r["n"], "test_file": r["test_file"],
                           "exit": r.get("exit"),
                           "timed_out": r.get("timed_out"),
                           "why": "the row produced no verdict at all"})
        else:
            findings.append({"n": r["n"], "test_file": r["test_file"],
                             "verdict": verdict,
                             "diverged_step": p.get("diverged_step"),
                             "divergent_line": p.get("divergent_line")})
    holds = (not findings and not refusals and not silent and bool(expected)
             and not _not_run(rows))
    if holds:
        word = "PASS"
    elif refusals or silent or _not_run(rows):
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
                          "no_verdict": silent,
                          "lookup_refused_owned_by_H3": [r["n"] for r in
                                                         lookup],
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
    dropped = _not_run(rows) + dropped
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
    holds = held == len(clauses) and bool(seen) and not _not_run(rows)
    return cell(held, len(clauses), dropped, holds=holds,
                evidence={"word": _word(holds, "H5"),
                          "rule": "§5's row, summed over every row the loop "
                                  "ran; an UNVERIFIABLE check is printed and "
                                  "never counted as verified",
                          "clauses": clauses, "sums": sums,
                          "granted": granted, "claims": claims})


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
    missing = _not_run(rows)
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
    # `holds` stays None -- §1 gates nothing here -- but a row the loop never
    # reached is still NAMED, so a smaller cost table is visibly smaller.
    return cell(measured, len(seen), missing, holds=None,
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


def _controls() -> dict:
    """The control, read and fence cells, imported at CALL time.

    `e15_cells_controls` imports `_word`, `_null` and `cell` from this module
    -- one table of §1's four words, not two -- so importing it at the top
    here would be a cycle. The idiom is `refocus_licence`'s and the reason is
    the same: the direction is still one way, and nothing there runs at
    import time.
    """
    import e15_cells_controls as cc                            # noqa: PLC0415
    return {"H6": cc.h6, "H7": cc.h7, "H7p": cc.h7p, "H8": cc.h8,
            "H8p": cc.h8p, "H10": cc.h10}

#: §1's own ten, for a caller that wants the locked list without the primed
#: readings beside it.
ENDPOINTS = tuple(f"H{n}" for n in range(1, 11))


#: The published order: §1's ten in §1's order, each followed by its primed
#: reading where ruling P16 gives one.
ORDER = ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H7p", "H8", "H8p",
         "H9", "H10")


def cells(raw: dict, survey: list) -> dict:
    """§1's ten endpoints, in §1's order, plus ruling P16's two primed
    readings beside the controls they re-read."""
    table = {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5, "H9": h9,
             **_controls()}
    return {name: table[name](raw, survey) for name in ORDER}


def stops(payload: dict) -> list[str]:
    """Every cell whose word is STOP, named. `assemble_e15.py` turns a
    non-empty list into `DONE-WITH-STOP`."""
    return [f"{name}: {json.dumps(c['evidence']['rule'])}"
            for name, c in payload.items()
            if isinstance(c, dict) and (c.get("evidence") or {}).get("word")
            == "STOP"]
