"""E15's control, read and fence cells: H6, H7, H7', H8, H8' and H10.

A module of its own for `rust/tests/acceptance_e4_cells.py`'s reason -- no
file in this repository may pass 800 lines -- and the seam is the material's
own: every cell in `e15_report.py` is read over the 31 rows of the locked
survey and shares one population, and nothing here is. The shared vocabulary
(`_word`, `_null`, `FAIL_WORD`, the record's cell shape) stays there and is
imported, so there is ONE table of §1's four words and not two.

Ruling P16's two primed readings live here beside the controls they re-read:
H7' asks whether control B's source finding was PRINTED in the block the
report prints for the verdict it reached, and H8' asks whether the `--focus`
form of control C reaches design §2.3's refusal 1. Neither widens §1's own
cell; both are published beside it, so a second answer cannot stand in for
the first.
"""
from __future__ import annotations

from pathlib import Path

from e15_report import _null, _word, cell

#: Design 2026-09-13 §2.3, refusal 1 -- the sentence control C predicts,
#: carried here as a literal because it is what H8 and H8' COMPARE against.
#: Both cells publish what they wanted and what they got, so a changed
#: sentence reads as a finding rather than as a silent pass.
WINDOW_REFUSAL = ("--window is not available for a TypeScript trace (the "
                  "recorder has no per-activation gate); nothing was re-run")


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

#: The two blocks a source finding can be printed in, and the verdict each
#: belongs to. `refocus_report.report` prints a `licence:` line ONLY on a
#: MATCH -- a DIVERGED prints the world findings under its own header and no
#: licence at all -- so "the reason was printed" is one question with two
#: places to look, and H7′ (ruling P16) is the cell that asks it that way.
SOURCE_REASON_BLOCK = {"MATCH": "the WITHHELD licence's reasons",
                       "DIVERGED": "the `differences in the world between "
                                   "the two runs` block"}


def _control_b(raw):
    """(control B's record, its parse, the edited file's basename).

    The basename is what `refocus_world._source_state` prints for a changed
    file (`Path(p).name`), so a claim about "naming the file" is asserted in
    the spelling the command actually uses.
    """
    b = ((raw or {}).get("controls") or {}).get("B")
    if not isinstance(b, dict) or not b.get("ran"):
        return None, {}, ""
    return b, (b.get("parsed") or {}), Path(b.get("test_file") or "").name


def h7(raw, survey) -> dict:
    """§1, control B, read LITERALLY: `plant_edit.py` appends one failing test
    to one selected file in the copy; its refocus reads `source: CHANGED`
    naming the file and `licence: WITHHELD` with that reason, **whatever the
    verdict**; **1 of 1**.

    "Whatever the verdict" is §1's own phrase and this cell keeps it: the
    licence line asked for here is `licence: WITHHELD`, and a DIVERGED prints
    none. Where the reason DID appear is published in the evidence and read
    as a gate by `h7p` -- never folded into this cell, because a pinned
    prediction that is satisfied by a different line is not the prediction
    that was pinned.
    """
    b, p, name = _control_b(raw)
    if b is None:
        return _null("control B did not run", 1)
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
                          "rule": "§1 LITERALLY: source CHANGED naming the "
                                  "file and a `licence: WITHHELD` line "
                                  "carrying that reason, whatever the "
                                  "verdict; the verdict itself is a reading",
                          "claims": claims,
                          "verdict": p.get("verdict"),
                          "row": b.get("row"), "test_file": b.get("test_file"),
                          "source_line": source_line,
                          "withheld_reasons": reasons,
                          # Where the source finding went when the verdict was
                          # DIVERGED. Evidence here, a gate in H7′.
                          "world_caveats": p.get("world_caveats") or [],
                          "licence_is_absent_on_a_diverged_verdict": (
                              p.get("verdict") == "DIVERGED"
                              and p.get("licence") is None),
                          "read_as_a_gate_by": "H7p",
                          # The LENS is never written: the runner restores the
                          # edited file from it and compares the sha.
                          "lens_restored": bool(b.get("restored")
                                                and b.get("sha_equal")),
                          "process_exit": b.get("exit")})


def h7p(raw, survey) -> dict:
    """H7′ (ruling P16): control B, read against the block the command
    actually prints for the verdict it reached.

    Same two facts H7 asks for -- the source change was SEEN, and it was
    REPORTED to the reader -- with the second one looked for where
    `refocus_report.report` puts it: the WITHHELD licence's reasons on a
    MATCH, the `differences in the world between the two runs` block on a
    DIVERGED. **1 of 1**.

    A separate cell and not a widening of H7, because the two answer
    different questions: H7 asks whether the pre-registered LINE appeared,
    and this asks whether the FINDING did. Publishing only the second would
    let a prediction pass on a line it never named.
    """
    b, p, name = _control_b(raw)
    if b is None:
        return _null("control B did not run", 1)
    verdict = p.get("verdict")
    source_line = p.get("source_line") or ""
    if verdict == "MATCH":
        printed, where = (p.get("withheld_reasons") or []), "MATCH"
    elif verdict == "DIVERGED":
        printed, where = (p.get("world_caveats") or []), "DIVERGED"
    else:
        printed, where = [], None
    named = [r for r in printed if "source" in r.lower() and name and name in r]
    claims = {
        "`source: CHANGED` names the edited file":
            p.get("source_status") == "CHANGED" and bool(name)
            and name in source_line,
        "the verdict is one whose block this cell knows":
            where is not None,
        "the source reason is printed in that block":
            bool(named),
    }
    holds = all(claims.values())
    return cell(1 if holds else 0, 1, [], holds=holds,
                evidence={"word": _word(holds, "H7p"),
                          "rule": "source CHANGED naming the file, and the "
                                  "source reason printed in the block the "
                                  "report prints for the verdict reached "
                                  "(the WITHHELD licence on a MATCH, the "
                                  "world block on a DIVERGED)",
                          "claims": claims, "verdict": verdict,
                          "block_read": SOURCE_REASON_BLOCK.get(where),
                          "reasons_in_that_block": printed,
                          "reasons_naming_the_source": named,
                          "row": b.get("row"), "test_file": b.get("test_file"),
                          "source_line": source_line,
                          "reads_the_literal_clause_at": "H7"})


# ------------------------------------------------------------------- H8


def _window_claims(exit_code, sentence, before, after) -> dict:
    """§1's three clauses for control C, over one invocation's answer."""
    return {
        "exit 2": exit_code == 2,
        "the §2.3 refusal-1 sentence, verbatim": sentence == WINDOW_REFUSAL,
        "the trace count is unchanged":
            before is not None and before == after,
    }


def h8(raw, survey) -> dict:
    """§1, control C, read LITERALLY: `refocus <member> --window 1` on one
    original -- exit 2, the §2.3 sentence, and the store's trace count
    UNCHANGED before and after; **1 of 1**.

    The command judged here is the one §1's locked text spells, with no
    `--focus`. On this tree `--focus` is a REQUIRED argument of `sensorium
    refocus`, so argparse refuses the CALL with a usage line before design
    §2.3's refusal 1 can run: the exit is 2 and the sentence is not §2.3's,
    and this cell STOPs on that clause. That is the finding, and softening it
    -- judging the `--focus`-bearing form here and filing the literal one as
    evidence -- would be answering a question §1 did not ask. The form that
    DOES reach refusal 1 is H8′ below.

    The store count is the half that tests the claim rather than the print:
    "nothing was re-run" is a statement about the world, and the literal
    form's own pair of counts is read (`traces_before` → `traces_between`).
    """
    c = ((raw or {}).get("controls") or {}).get("C")
    if not isinstance(c, dict) or not c.get("ran"):
        return _null("control C did not run", 1)
    literal = c.get("as_written") or {}
    before = c.get("traces_before")
    after = c.get("traces_between", c.get("traces_after"))
    parsed = literal.get("parsed") or {}
    claims = _window_claims(literal.get("exit"), parsed.get("refusal"),
                            before, after)
    holds = all(claims.values())
    return cell(1 if holds else 0, 1, [], holds=holds,
                evidence={"word": _word(holds, "H8"),
                          "rule": "§1 LITERALLY (`refocus <run> --window 1`, "
                                  "no --focus): exit 2, design §2.3's "
                                  "refusal-1 sentence, and a trace count "
                                  "equal before and after",
                          "claims": claims,
                          "command": literal.get("command"),
                          "expected_sentence": WINDOW_REFUSAL,
                          "sentence": parsed.get("refusal"),
                          "stderr": literal.get("stderr"),
                          "row": c.get("row"),
                          "read_as_a_gate_by": "H8p",
                          "traces_before": before, "traces_after": after})


def h8p(raw, survey) -> dict:
    """H8′ (ruling P16): control C with the `--focus <spec>` the command
    requires, which is the form that reaches design §2.3's refusal 1.

    Same three clauses -- exit 2, refusal 1's sentence verbatim, and a trace
    count equal before and after -- over the invocation that actually
    exercised the refusal. **1 of 1**.

    A separate cell and not a widening of H8, for H7′'s reason one control
    over: H8 asks whether §1's literal command answers as §1 predicted, and
    this asks whether the REFUSAL does. One cell carrying both would let the
    second answer stand in for the first.
    """
    c = ((raw or {}).get("controls") or {}).get("C")
    if not isinstance(c, dict) or not c.get("ran"):
        return _null("control C did not run", 1)
    p = c.get("parsed") or {}
    before = c.get("traces_between", c.get("traces_before"))
    after = c.get("traces_after")
    claims = _window_claims(c.get("exit"), p.get("refusal"), before, after)
    holds = all(claims.values())
    return cell(1 if holds else 0, 1, [], holds=holds,
                evidence={"word": _word(holds, "H8p"),
                          "rule": "the same three clauses over `refocus "
                                  "<run> --focus <spec> --window 1`, the "
                                  "form that reaches design §2.3's refusal 1",
                          "claims": claims,
                          "command": c.get("command"),
                          "expected_sentence": WINDOW_REFUSAL,
                          "sentence": p.get("refusal"),
                          "row": c.get("row"),
                          "focus_added_because": (
                              "`--focus` is required by `sensorium refocus`; "
                              "§1's shorthand omits it and argparse refuses "
                              "the call before refusal 1 can run"),
                          "reads_the_literal_clause_at": "H8",
                          "traces_before": before, "traces_after": after})


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


#: §1's ten endpoints in §1's order, each followed by its primed reading
#: where ruling P16 gives one. H7′ and H8′ are NOT §1's -- §1 is byte-locked
#: and nothing was added to it -- they are second readings of the same two
#: controls, published beside the literal ones so that neither answer can
#: stand in for the other.
