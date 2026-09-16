#!/usr/bin/env python3
"""E16 part C's DECISION layer: what §1's amendment fixed, and the one cell.

Split from `e16c.py` on the seam parts A and B found: everything here is a
pure function over rows somebody could type by hand, and nothing here runs a
subprocess, reads the clock or knows where the box keeps its files. That is
what lets `tests/test_acceptance_e16c_cells.py` exercise every verdict --
including every STOP -- without the measurement, which runs once, on a copy
of a store that took a year to fill.

`e16c.py` re-exports every name below, so `e16c.h4` and `assemble_e16c`'s
imports mean one thing.

WHAT PART C MEASURES, AND WHAT IT DOES NOT
------------------------------------------
H4 in full, and nothing else. H1-env, H2, H3 and H6-env were part A's;
H1-values, H5 and H6-values were part B's. Each of those seven is written
into the results file as `dropped` with the part that owns it -- never as a
number, and never as PASS.

H4 IS FOUR CLAUSES, AND ALL FOUR ARE ONE WORD
---------------------------------------------
§9's H4 row states one claim in four parts, and plan P13 reads them as four
rows of one cell: (1) the dry run names `CLAUDE_CODE_MESSAGING_TOKEN` on
every trace in the copy; (2) the value's bytes are gone from every file
after the real run; (3) every trace still opens and says `by retrofit`; (4)
the dry run's stdout is the real run's, byte for byte. PASS iff all four.
The STOP names the FIRST failing clause and the offender it failed over --
a verdict word with no name attached is a verdict nobody can act on.

WHAT A CELL MAY DECIDE
----------------------
PASS, STOP, or `dropped`. `dropped` is the answer whenever an input is
`None` -- which is what `e16c.py` writes for a phase that did not run -- and
whenever an input list is EMPTY: three of H4's four clauses are "every one
of these is so", which is vacuously true over nothing, so a copy that held
no trace or a grep that examined no file would otherwise publish as a clean
sweep. The verdict words come from `RULES`, which is §9's own PASS/STOP
column; the cell test holds it against the record on disk.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Part A's decision layer, imported rather than copied: the refusal type is
# one instrument's machinery used by three parts, and a second copy of it is
# a second thing to keep true.
from e16a_cells import Refused                              # noqa: E402,F401

#: The variable §9's H4 row names. Not minted and not a probe (P10): it is
#: the value this box's own traces already hold -- values, plural, since
#: the token rotated over the store's life, so the instrument reads EVERY
#: distinct value out of the copy and sweeps the set (R15, `AMENDMENTS`).
TOKEN_VAR = "CLAUDE_CODE_MESSAGING_TOKEN"

#: §9's PASS/STOP column for the one row part C decides, copied from the
#: record's §1 table -- the clause WHOLE, and the cell test checks it by
#: EQUALITY against the row's own cell rather than by substring: a substring
#: check cannot see a clause cut short.
RULES = {
    "H4": {"PASS": "all",
           "STOP": "any residue, any trace that no longer opens, or "
                   "dry-run ≠ real"},
}

#: What §3 calls the row part C measures. §9 gives it no qualifier -- part C
#: measures H4 whole -- so the title is the row's own name.
CELL_TITLES = {"H4": "H4"}

#: The cells part C does NOT measure, and which part owns each.
DROPPED = (("H1-env", "part A"), ("H1-values", "part B"),
           ("H2", "part A"), ("H3", "part A"), ("H5", "part B"),
           ("H6-env", "part A"), ("H6-values", "part B"))

#: §9's own expectation for the store's size, written when §9 was written.
#: REPORTED beside the count the copy actually held and gated by nothing
#: (P13): a store that grew by one trace since §9 was typed is not a finding
#: about the retrofit, and a run that refused over it would be measuring the
#: calendar.
EXPECTED_TRACES = 273

#: The version the venv must read for this to be a measurement of PR C
#: (C19). Checked in `preflight`, which is a PRECONDITION: a retrofit
#: measured under 0.16.0 is a measurement of a command that does not exist.
EXPECTED_VERSION = "0.17.0"

#: §1's amendment's kill rules, in seconds. `redact` is per RUN (the dry one
#: and the real one), `info` is the whole sweep over every trace, `grep` is
#: one sweep of the copy.
TIMERS = {"copy": 600, "redact": 900, "info": 900, "grep": 300, "part": 2700}
#: The rehearsal's, a tenth of each: the fabricated store is three traces,
#: and a rehearsal that waited out a real store's timers would be measuring
#: nothing for a quarter of an hour.
DRY_TIMERS = {name: seconds // 10 for name, seconds in TIMERS.items()}

#: `redact_cmd.line_for`'s three printable forms, pinned to the character.
#: An instrument that reads nothing reports a green run over an unmeasured
#: claim, so these are held against the command's own source by the cell
#: test rather than trusted.
LINE = re.compile(r"^run (?P<id>\S+): env (?P<n>\d+) redacted "
                  r"\((?P<names>[^)]*)\); values (?P<v>\d+); "
                  r"mode (?P<mode>.+)$")
CLEAN = re.compile(r"^run (?P<id>\S+): nothing to redact; "
                   r"mode (?P<mode>.+)$")
#: Every other `run <id>: …` line -- `in flight (incomplete), skipped` and
#: `REFUSED: <reason>`. Parsed, rather than left unmatched, so that a STOP
#: over a trace the dry run did not name can say WHY it did not name it.
OTHER = re.compile(r"^run (?P<id>\S+): (?P<note>.+)$")
#: `redact_cmd.summary`'s first words. The rest of the line carries the
#: spools sentence and the optional sweep and directory clauses, which the
#: record prints verbatim rather than parsing.
SUMMARY = re.compile(r"^redacted \d+ of \d+ traces ")

#: What `_capped` appends past eight names (`refocus_world._capped`). A line
#: that hit the cap and does NOT show the token is UNREADABLE: the token may
#: be among the names it counted instead of listing. Read as a hole, never
#: as an absence -- which is the one thing this instrument must not be able
#: to do.
CAP = re.compile(r", \+(?P<more>\d+) more$")


def parse_lines(stdout: str | None) -> dict[str, dict] | None:
    """Every `run <id>: …` line of one `redact` stdout, keyed by run id.

    Each row is `{"names": [...], "values": int | None, "note": str | None,
    "capped": int | None}`. A `nothing to redact` line is names `[]` and
    values `0` -- the command said so, and that is a measurement. A skipped
    or refused line is `values: None` with the sentence in `note`: nothing
    was counted, and a zero invented for it would be a number nobody read.

    `None` in, `None` out: a run that was killed has no stdout to parse.
    """
    if stdout is None:
        return None
    rows: dict[str, dict] = {}
    for raw in stdout.splitlines():
        line = raw.rstrip("\n")
        m = LINE.match(line)
        if m:
            blob = m.group("names")
            cap = CAP.search(blob)
            if cap:
                blob = blob[:cap.start()]
            rows[m.group("id")] = {
                "names": [n.strip() for n in blob.split(",") if n.strip()],
                "values": int(m.group("v")), "note": None,
                "capped": int(cap.group("more")) if cap else None}
            continue
        m = CLEAN.match(line)
        if m:
            rows[m.group("id")] = {"names": [], "values": 0, "note": None,
                                   "capped": None}
            continue
        m = OTHER.match(line)
        if m:
            rows[m.group("id")] = {"names": [], "values": None,
                                   "note": m.group("note"), "capped": None}
    return rows


#: H4's four clauses, in the order §1's amendment states them, with what
#: each one is a claim about.
CLAUSES = (
    (1, f"every `*.db` in the copy has a dry-run line naming {TOKEN_VAR}"),
    (2, "every `grep -rc` count over the copy is 0 after the real run"),
    (3, "`sensorium info` exits 0 on every trace and reads `by retrofit`"),
    (4, "the dry run's stdout is the real run's, byte for byte"),
)

#: How many offenders a STOP names before it counts the rest. A store of 273
#: traces can fail a clause 273 times, and a sentence that lists every one of
#: them is a sentence nobody reads to the end.
NAMED = 5


def _dropped(why: str) -> dict:
    return {"word": "dropped", "read": why, "clauses": []}


def _named(items: list[str]) -> str:
    shown = ", ".join(items[:NAMED])
    return shown + (f", and {len(items) - NAMED} more"
                    if len(items) > NAMED else "")


def _clause_one(stems: list[str], dry_rows: dict[str, dict]) -> dict:
    """Every trace in the copy is named by the dry run, and the name is the
    token's. The set of ids whose names hold `TOKEN_VAR` must EQUAL the set
    of `*.db` stems: a trace the run never printed a line for is as much a
    failure as one it printed the wrong line for."""
    missing, unreadable = [], []
    for stem in stems:
        row = dry_rows.get(stem)
        if row and TOKEN_VAR in row["names"]:
            continue
        if row and row["capped"]:
            unreadable.append(f"{stem} (+{row['capped']} names not shown)")
        elif row and row["note"]:
            missing.append(f"{stem} ({row['note']})")
        elif row:
            missing.append(f"{stem} (env {', '.join(row['names']) or 'none'})")
        else:
            missing.append(f"{stem} (no line)")
    extra = sorted(rid for rid, row in dry_rows.items()
                   if TOKEN_VAR in row["names"] and rid not in set(stems))
    if unreadable:
        return {"word": "dropped",
                "read": f"{len(unreadable)} dry-run line(s) hit the eight-"
                        f"name cap without showing the token, so whether it "
                        f"fired cannot be read: {_named(unreadable)}"}
    if missing:
        return {"word": "STOP",
                "read": f"{len(missing)} trace(s) without the name in the "
                        f"dry run: {_named(missing)}"}
    if extra:
        return {"word": "STOP",
                "read": f"{len(extra)} dry-run line(s) name a trace the copy "
                        f"does not hold: {_named(extra)}"}
    return {"word": "PASS",
            "read": f"{len(stems)} traces, every one named in the dry run"}


def _clause_two(after_counts: list[dict]) -> dict:
    """Not one byte of the value left anywhere under the copy -- the
    databases, the sidecars that remain, `redaction.key`, the invocation
    log. A file whose count could not be read is a hole, not a zero."""
    unread = sorted(row["path"] for row in after_counts
                    if row.get("count") is None)
    if unread:
        return {"word": "dropped",
                "read": f"{len(unread)} file(s) the sweep could not count: "
                        f"{_named(unread)}"}
    held = sorted((row["path"], row["count"]) for row in after_counts
                  if row["count"])
    if held:
        return {"word": "STOP",
                "read": f"{len(held)} file(s) still hold the value: "
                        + _named([f"{p} ({n})" for p, n in held])}
    return {"word": "PASS",
            "read": f"0 occurrences in {len(after_counts)} files after"}


def _clause_three(stems: list[str], infos: list[dict]) -> dict:
    """Every trace still opens, and says which hand took its secrets. Both
    halves: an `info` that exits 0 on a trace still stamped `recorder` would
    mean the file survived a pass that never reached it.

    A KILLED reading is a hole and not a failure. `e16a._run` returns
    `rc: None` with `killed: true` when a call hit the phase's timer, and
    reading that `None` as "did not exit 0" would publish an infrastructure
    event -- a loaded box, a sweep that ran out of budget -- as a trace the
    retrofit broke. The same rule `_clause_two` applies to a count the
    sweep could not take.
    """
    seen = {row["run"]: row for row in infos}
    killed = [stem for stem in stems if (seen.get(stem) or {}).get("killed")]
    if killed:
        return {"word": "dropped",
                "read": f"{len(killed)} info call(s) were killed on the "
                        f"phase's own timer, so whether the trace opens was "
                        f"never read: {_named(killed)}"}
    bad = []
    for stem in stems:
        row = seen.get(stem)
        if row is None:
            bad.append(f"run {stem}: no info reading")
        elif row.get("exit") != 0:
            bad.append(f"run {stem}: info exit {row.get('exit')}")
        elif row.get("by") != "retrofit":
            bad.append(f"run {stem}: by {row.get('by') or 'nothing'}, "
                       "not retrofit")
    if bad:
        return {"word": "STOP", "read": _named(bad)}
    return {"word": "PASS",
            "read": f"{len(stems)}/{len(stems)} info exit 0, by retrofit"}


def _clause_four(identical: bool) -> dict:
    if not identical:
        return {"word": "STOP", "read": "dry-run stdout != real"}
    return {"word": "PASS", "read": "stdouts identical"}


def h4(stems: list[str] | None, dry_rows: dict[str, dict] | None,
       after_counts: list[dict] | None, infos: list[dict] | None,
       identical: bool | None) -> dict:
    """§9's H4, read as plan P13 reads it: four clauses, one word.

    Every input is what one phase left behind, and `None` is what a phase
    that did not run leaves. A `None` anywhere is `dropped` naming the
    phase -- the one thing this instrument must not be able to do is report
    a hole as a pass -- and so is an EMPTY list, which three of the four
    clauses would otherwise satisfy vacuously.
    """
    for value, phase in ((stems, "copy"), (dry_rows, "dry-run"),
                         (after_counts, "grep-after"), (infos, "info"),
                         (identical, "compare")):
        if value is None:
            return _dropped(f"{phase} did not run")
    if not stems:
        return _dropped("the copy held no `*.db` file at all")
    if not after_counts:
        return _dropped("the sweep after the real run examined no file")
    if not infos:
        return _dropped("no trace was opened after the real run")
    rows = [_clause_one(stems, dry_rows), _clause_two(after_counts),
            _clause_three(stems, infos), _clause_four(identical)]
    clauses = [{"clause": n, "what": what, "read": row["read"],
                "word": row["word"]}
               for (n, what), row in zip(CLAUSES, rows)]
    stop = next((c for c in clauses if c["word"] == "STOP"), None)
    held = next((c for c in clauses if c["word"] == "dropped"), None)
    # A STOP OUTRANKS A DROP, and the sentence names both. A clause that
    # actually failed is a finding about the retrofit; a clause nobody could
    # read is a hole in the instrument. Reporting the hole and swallowing
    # the finding would turn a measured failure into "we did not look" --
    # and reporting the finding without the hole would let a reader think
    # the other three clauses had all been read.
    if stop:
        read = f"clause {stop['clause']}: {stop['read']}"
        if held:
            read += (f" (and clause {held['clause']} could not be read: "
                     f"{held['read']})")
        return {"word": "STOP", "clauses": clauses, "read": read}
    if held:
        out = _dropped(f"clause {held['clause']}: {held['read']}")
        out["clauses"] = clauses
        return out
    return {"word": "PASS", "clauses": clauses,
            "read": "; ".join(c["read"] for c in clauses)}


#: The pre-registration amendments this run was measured under, recorded
#: BESIDE §1's locked text and never edited into it (part B's `AMENDMENTS`
#: pattern). Each entry states §1's own clause, what was run instead, and
#: why -- an amendment a reader cannot check against the locked text is
#: indistinguishable from a changed mind. These are DATA in the raw record,
#: so what §4 renders is what the run was actually made under and not prose
#: the assembler carries on its own.
AMENDMENTS = [
    "- **R15, the token is a SET of values, not one.** §1's amendment "
    "pre-registers the token as \"the value of `CLAUDE_CODE_MESSAGING_TOKEN` "
    "in the copy's own traces, read by the instrument from the first "
    "trace's `meta.env`\", and makes it a precondition that \"every `*.db` "
    "in the copy must hold the value at least once before the run\". "
    "Measured read-only before the run, this box's store holds FOUR "
    "distinct values of that variable across its 273 traces (254 / 11 / 5 / "
    "3 — the token rotated over the store's life), and the first `*.db` in "
    "sorted order carries the one held by 11. Read literally, the "
    "precondition therefore refuses 262 of 273 traces for a reason that has "
    "nothing to do with the retrofit. Corrected clause: **the instrument "
    "reads every trace's own value, sweeps the DISTINCT set one value at a "
    "time, and requires each trace to hold ITS OWN value at least once "
    "before the run; clause 2 requires every one of the values to read 0 in "
    "every file after it.** That is strictly stronger than the "
    "pre-registered single-value reading — it makes clause 2 a claim about "
    "all 273 traces instead of 11 — and it cannot pass where the "
    "pre-registered one would. The record cites each value's "
    "`sha256[:8]` with the number of traces holding it; no value is ever "
    "printed.",
]


def part_word(cells: dict) -> str:
    """The part's own word. `DONE` only when H4 PASSed -- read out of the
    dict by name, so a cell that was never written is the STOP side rather
    than an absent key nobody notices."""
    return ("DONE" if cells.get("H4", {}).get("word") == "PASS"
            else "DONE-WITH-STOP")
