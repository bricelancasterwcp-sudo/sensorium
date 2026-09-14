#!/usr/bin/env python3
"""E16 part B's DECISION layer: what §1's amendment fixed, and the three
cells.

Split from `e16b.py` on the seam part A's split found: everything here is a
pure function over rows somebody could type by hand, and nothing here runs a
subprocess, reads the clock or knows where the box keeps its files. That is
what lets `tests/test_acceptance_e16b_cells.py` exercise every verdict --
including every STOP -- without the measurement, which runs once.

`e16b.py` re-exports every name below, so `e16b.cell_h1_values` and
`assemble_e16b`'s imports mean one thing.

WHAT PART B MEASURES, AND WHAT IT DOES NOT
------------------------------------------
H1 restricted to VALUES, H5 in full, H6 restricted to `redaction.values`.
H1-env, H2, H3 and H6-env were part A's and are already in the record; H4 is
part C's. Each of those five is written into the results file as `dropped`
with the part that owns it -- never as a number, and never as PASS.

WHAT A CELL MAY DECIDE
----------------------
PASS, STOP, or `dropped` -- except H5, which decides `measured` and nothing
else: §9's own PASS/STOP column for it is `n/a` twice over, because cost is
reported and never gated (rust/HONESTY.md §10). `dropped` is the answer
whenever a row a cell needs is `None`, and whenever an input list is EMPTY:
three of H1-values' four readings are "every count 0", which is vacuously
true over nothing, so a mistyped root would otherwise publish as a clean
sweep. The verdict words come from `RULES`, which is §9's own PASS/STOP
column; the cell tests hold every clause below against the record on disk.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Part A's decision layer, imported rather than copied: the token's name,
# the three arms, the refusal type and the driver-build reading are one
# part's facts about the other's subject, and a second copy of any of them
# is a second thing to keep true. The token's SHAPE, the decoy's and the
# allowlist stay where `Part.mint` and `Part.env` read them -- part B
# records under part A's, unchanged, by inheriting its runner.
from e16a_cells import (ARMS, TOKEN_VAR, Refused,  # noqa: E402,F401
                        read_driver_build)

# -- what §1's amendment fixed --------------------------------------------

#: §9's PASS/STOP column for the three rows part B decides, copied from the
#: record's §1 table -- each clause WHOLE, and the cell test checks it by
#: EQUALITY against the row's own cell rather than by substring: a substring
#: check cannot see a clause cut short. H5's two `n/a`s are not an omission;
#: they are §9 saying this row has no gate.
RULES = {
    "H1": {"PASS": "every count 0 where 0 is required",
           "STOP": "any non-zero: a missed path. Named, fixed, and the "
                   "whole of E16 re-measured from zero with a fresh token "
                   "— an acceptance test of correctness is re-run after "
                   "a fix, and the record says which run is the first PASS"},
    "H5": {"PASS": "n/a",
           "STOP": "n/a — an outlier ratio is a finding for "
                   "CARRIED-DEBT, not a stop"},
    "H6": {"PASS": "exact",
           "STOP": "any other number: an over- or under-firing rule"},
}

#: The cells part B measures, the §9 row each one is read against, and what
#: §3 calls it. Two names for one row is deliberate: §9's H1 covers the
#: environment AND the values, and part A measured the first half.
RULE_OF = {"H1-values": "H1", "H5": "H5", "H6-values": "H6"}
CELL_TITLES = {"H1-values": "H1 (values)", "H5": "H5 (overhead)",
               "H6-values": "H6 (`redaction.values`)"}

#: The cells part B does NOT measure, and which part owns each.
DROPPED = (("H1-env", "part A"), ("H2", "part A"), ("H3", "part A"),
           ("H4", "part C"), ("H6-env", "part A"))

#: The planted count per arm (§1's amendment, row by row). Python 5:
#: `secret`'s RETURN by name, the `token` LINE delta by name, the `headers`
#: map value under `authorization` by name, `send(token)`'s CALL argument by
#: name, and the `print` chunk by CONTENT. TypeScript 4: the CALL argument
#: `token` by name, the `copy` delta by content, the `headers` delta by
#: content, `secret`'s RETURN by name. Rust 4: the parameters row's `token`
#: delta by name (tag 4), `copy` by content, the `Headers` `Debug` text by
#: content, `secret`'s RETURN by name.
EXPECTED_VALUES = {"python": 5, "typescript": 4, "rust": 4}

#: What a DRY run predicts instead. The decoy is `dry-` plus four
#: characters, which no content pattern matches, so only the NAME rows can
#: fire: Python loses its `print` chunk, and Rust and TypeScript lose `copy`
#: and `headers`. Reported by the dry run so it can say "as predicted", and
#: gated by nothing -- a dry run's census is about a different string.
DRY_NAME_ROWS = {"python": 4, "typescript": 2, "rust": 2}

#: The Rust `.spool` files hold the token exactly this many times (B16), and
#: the three occurrences are the three rows the CONVERTER redacts: `copy`,
#: the `Headers` `Debug` text and `secret`'s RETURN. The fourth Rust row --
#: the `token` parameter delta -- is taken by the recorder before the spool
#: is written, which is why the number is three and not four.
SPOOL_OCCURRENCES = 3

#: The commit H5's baseline tree is built at: the merge that closed S5's
#: refocus-for-TypeScript slice, the last commit before PR A.
BASELINE = "7dd25d2"
#: `bench.report(reps=...)` in each tree. Five, per §1's amendment; the dry
#: run uses one, which measures the plumbing and no machine.
BENCH_REPS = 5
DRY_BENCH_REPS = 1

#: The versions §1's amendment expects; `versions` records what they were.
EXPECTED = {"sensorium": "0.16.0", "sensorium-rt": "0.7.0",
            "cargo-sensorium": "0.8.0", "sensorium-ts": "0.6.0"}

#: The focus each arm records under. Python's is `module:qualname` (R11
#: below); the Rust and TypeScript recorders take a bare function name.
FOCUS = {"python": "main:handle", "rust": "handle", "typescript": "handle"}

#: The probe sources, per arm, under `tests/acceptance_e16/probes/<arm>/`.
PROBES = {"python": ("main.py",),
          "rust": ("Cargo.toml", "src/main.rs"),
          "typescript": ("secret.ts", "secret.test.ts")}

#: Where the two TypeScript probe files are copied inside the disposable
#: copy of `corpus/typescript`, and the one case directory that copy omits.
#: `vitest.config.ts` includes `*/**/*.test.ts`, so a probe at the project
#: root would not be collected at all; and `vitest run secret` is a
#: SUBSTRING filter over test-file paths, so the corpus's own
#: `secret_in_env/secret_in_env.test.ts` matches it too (see `AMENDMENTS`).
TS_PROBE_DIR = "e16_probe"
TS_OMITTED_CASE = "secret_in_env"

#: §1's amendment's kill rules, in seconds. `bench` is per TABLE: two runs
#: of `bench.report(reps=5)`, one per tree.
TIMERS = {"build": 1800, "baseline": 600, "record": 600, "record_rust": 600,
          "bench": 1200, "part": 60 * 60}
#: The dry run caps the recordings at a minute and each bench table at five,
#: and leaves the driver build and the baseline worktree alone: a cold
#: `cargo build --release` and a `uv pip install` are minutes of work that
#: say nothing about the instrument's plumbing, and killing either would
#: only test the refusal.
DRY_TIMERS = {"build": 1800, "baseline": 600, "record": 60, "record_rust": 60,
              "bench": 300, "part": 25 * 60}

#: The pre-registration errors this run was measured under, recorded BESIDE
#: §1's locked text and never edited into it (R11). Each entry states §1's
#: own clause, what was run instead, and why -- an amendment a reader cannot
#: check against the locked text is indistinguishable from a changed mind.
#: These are DATA in the raw record, so what §3 renders is what the run was
#: actually made under, not prose the assembler carries on its own.
AMENDMENTS = [
    "- **R11, the Python probe's focus.** §1's part B block records the "
    "Python probe with `sensorium run --focus handle -- main.py`. A bare "
    "`--focus handle` names a MODULE: `FocusSpec` splits each entry on `:` "
    "into `module` and an optional `qualname` (`record/tracer_frames.py`), "
    "so `handle` alone matches only code whose module is called `handle` — "
    "nothing in `main.py` — and the recording would carry no LINE deltas at "
    "all, which is three of the five rows §1 counts. Corrected clause: "
    "**`sensorium run --focus main:handle -- main.py`**, which is how "
    "`corpus/secret_in_env/questions.yaml` spells the same focus for the "
    "corpus's own case. The Rust arm (`cargo sensorium --focus handle run`) "
    "and the TypeScript arm (`--focus handle`) are unchanged: neither "
    "recorder's focus spec is module-qualified.",
    "- **The TypeScript project copy omits `corpus/typescript/"
    "secret_in_env`.** §1 records the TypeScript probe with `npx vitest run "
    "secret`, and vitest's positional filter is a SUBSTRING match over test "
    "file paths: the corpus's own `secret_in_env/secret_in_env.test.ts` "
    "matches it as surely as the probe's `e16_probe/secret.test.ts` does. "
    "Both would be recorded into one trace and that case's four planted "
    "rows counted into the probe's census of four. The disposable copy "
    "therefore leaves that one case directory out; the command, the probe "
    "and the predicted count are unchanged. (The probe is copied into a "
    "SUBDIRECTORY for the same reason it is copied at all: the corpus "
    "project's `vitest.config.ts` includes `*/**/*.test.ts`, which a file "
    "at the project root does not match.)",
]


# -- the cells -------------------------------------------------------------
def _dropped(why: str) -> dict:
    return {"word": "dropped", "why": why}


#: H1-values' four readings, in the order §1's amendment states them, with
#: what each one is a claim about. The Rust spools are the one set whose
#: answer is not zero.
H1_SETS = (("store", "every file under the store"),
           ("headers", "every Rust `<pid>.proc.json`"),
           ("spools", "the Rust `.spool` files together"),
           ("ts_spools", "the TypeScript spool directory"))
#: The three of them that must read zero.
H1_ZERO = ("store", "headers", "ts_spools")


def cell_h1_values(store_files: list[dict] | None,
                   header_files: list[dict] | None,
                   spool_files: list[dict] | None,
                   ts_spool_files: list[dict] | None,
                   other_files: list[dict] | None = None) -> dict:
    """H1 restricted to VALUES: the token's bytes, counted as OCCURRENCES.

    Occurrences and not lines (part A's `grep -rc` counted lines): the three
    rows the Rust converter redacts can share a line, and "exactly 3" is a
    claim about how many times the value is present, not about how many
    lines mention it.

    Every one of the four inputs is one row per file EXAMINED, zeros
    included, and an EMPTY list is dropped rather than passed for all four.
    Three of the readings are "every count 0", which is true of nothing at
    all; the fourth is an exact total, which a sweep that found no spool
    would read as 0 and STOP on -- naming the wrong finding.

    `other_files` is everything else the run swept -- the disposable copies,
    the transcripts, the cargo build tree, the two UNGATED Rust spool files
    (`<pid>.runner.json`, `invocation.json`), the TMPDIR and the
    instrument's own output. It changes NO verdict: §1's amendment names
    four readings and those are the gate. What it does is get SAID -- a
    non-zero row out there is named in `why`, where a reader meets it beside
    the word, rather than sitting in a summary table nobody reads twice.
    `None` means the run handed none, and this cell never drops on it.
    """
    sets = {"store": store_files, "headers": header_files,
            "spools": spool_files, "ts_spools": ts_spool_files}
    for key, label in H1_SETS:
        if sets[key] is None:
            return _dropped(f"{label} was not swept")
        if not sets[key]:
            return _dropped(f"{label}: the sweep examined no file at all")
    unread = sorted(row["path"] for rows in sets.values() for row in rows
                    if row.get("occurrences") is None)
    if unread:
        return _dropped("occurrences missing for: " + ", ".join(unread))
    # One entry per FILE, not one per reading. The TypeScript spool lives
    # under the store, so its files are in two of the four sets, and a
    # per-reading list would name the same leak twice and count the same
    # file twice -- a record whose "N file(s) examined" is larger than the
    # number of files there are.
    by_path: dict[str, dict] = {}
    for key, _label in H1_SETS:
        for row in sets[key]:
            entry = by_path.setdefault(row["path"],
                                       {"path": row["path"],
                                        "occurrences": row["occurrences"],
                                        "sets": []})
            entry["occurrences"] = max(entry["occurrences"],
                                       row["occurrences"])
            entry["sets"].append(key)
    offenders = [entry for entry in by_path.values()
                 if entry["occurrences"]
                 and not set(entry["sets"]).isdisjoint(H1_ZERO)]
    total = sum(row["occurrences"] for row in sets["spools"])
    examined = len(by_path)
    # Ungated, reported. A file that could not be read out there is named
    # too: "swept and clean" and "swept and unreadable" are not one fact.
    beyond = [row for row in (other_files or []) if row.get("occurrences")]
    unread_beyond = [row["path"] for row in (other_files or [])
                     if row.get("occurrences") is None]
    out = {"word": "PASS", "offenders": offenders,
           "spool_occurrences": total, "files_examined": examined,
           "beyond_the_readings": beyond,
           "other_examined": len(other_files or [])}
    why = []
    if offenders:
        why.append(f"the token's bytes appear in {len(offenders)} file(s) "
                   "that must hold none: "
                   + ", ".join(f"{o['path']} ({o['occurrences']})"
                               for o in offenders))
    if total != SPOOL_OCCURRENCES:
        why.append(f"the Rust spools hold {total} occurrence(s), not the "
                   f"{SPOOL_OCCURRENCES} the converter is meant to be the "
                   "only reader of")
    if why:
        out["word"] = "STOP"
        out["why"] = "; ".join(why)
    else:
        out["why"] = (f"{examined} file(s) examined: every count 0 under the "
                      f"store, in every proc header and in the TypeScript "
                      f"spool, and exactly {total} occurrence(s) in the Rust "
                      "spools")
    if other_files is not None:
        note = (f"; {len(other_files)} further file(s) swept outside the "
                "four readings (not gated)")
        if beyond:
            note += (", " + str(len(beyond)) + " holding the token: "
                     + ", ".join(f"{row['path']} ({row['occurrences']})"
                                 for row in beyond))
        elif unread_beyond:
            note += ", none holding the token, " + str(len(unread_beyond)) \
                + " unreadable: " + ", ".join(sorted(unread_beyond))
        else:
            note += ", none holding the token"
        out["why"] += note
    return out


# -- H5: the two overhead tables -------------------------------------------
#: One row of `bench.report`'s table, as `corpus/_bench/bench.py::_row`
#: prints it: `{workload:<19} {tier:<8} {baseline:>9.4f} {recorded:>9.4f}
#: {multiplier:>7.1f} {events:>9} {us_per_event:>9}`, where the last two are
#: `-` when the run could not count events.
#:
#: Anchored on the TIER word rather than on whitespace alone, which is what
#: keeps it off the three lines around a row that also start with a word:
#: the header (second field `tier`), the `n/a` line a workload with no focus
#: target prints, and the two sentences under the table. The cell tests hold
#: it against a line `_row` itself built, and against each of those four.
BENCH_ROW = re.compile(
    r"^(?P<workload>[A-Za-z_][A-Za-z0-9_]*)\s+(?P<tier>default|focused)"
    r"\s+(?P<baseline_s>\d+\.\d{4})\s+(?P<recorded_s>\d+\.\d{4})"
    r"\s+(?P<multiplier>\d+\.\d)\s+(?P<events>\d+|-)"
    r"\s+(?P<us_per_event>\d+\.\d|-)\s*$", re.M)


def parse_bench(text: str | None) -> dict:
    """Every measured row of one `bench.report` table, keyed `(workload,
    tier)`. A table that printed no row parses to `{}`, which the cell
    treats as a table that did not parse -- never as a table of no rows."""
    rows = {}
    for m in BENCH_ROW.finditer(text or ""):
        rows[(m.group("workload"), m.group("tier"))] = {
            "workload": m.group("workload"), "tier": m.group("tier"),
            "baseline_s": float(m.group("baseline_s")),
            "recorded_s": float(m.group("recorded_s")),
            "multiplier": float(m.group("multiplier")),
            "events": (None if m.group("events") == "-"
                       else int(m.group("events"))),
            "us_per_event": (None if m.group("us_per_event") == "-"
                             else float(m.group("us_per_event"))),
            "line": m.group(0)}
    return rows


def _ratio(row: dict | None) -> float | None:
    """`recorded / baseline` for one row, or `None`.

    `None` when the row is missing and `None` when the baseline printed as
    `0.0000`: `{:>9.4f}` rounds a fast enough program to zero, and a ratio
    taken against that is not a large number, it is no number at all.
    """
    if not row or not row["baseline_s"]:
        return None
    return row["recorded_s"] / row["baseline_s"]


def cell_h5(baseline_table: str | None, head_table: str | None) -> dict:
    """H5: the overhead tables at `7dd25d2` and at HEAD, and their ratios.

    `measured`, never PASS and never STOP. §9's row gates nothing (`n/a`
    twice), because cost is a fact about a machine and a workload rather
    than a property of the tool; an outlier is a CARRIED-DEBT finding.

    What is reported is what §1's amendment asks for: both tables verbatim,
    and per workload row the `recorded/baseline` ratio at 7dd25d2, the same
    at HEAD, and HEAD's over 7dd25d2's. A row only one table carried keeps
    its own ratio and gets no comparison -- the two trees are different
    commits, and inventing one would be a number about a comparison nobody
    made.
    """
    if baseline_table is None:
        return _dropped(f"the {BASELINE} bench table was not produced")
    if head_table is None:
        return _dropped("the HEAD bench table was not produced")
    base, head = parse_bench(baseline_table), parse_bench(head_table)
    if not base:
        return _dropped(f"the {BASELINE} bench table did not parse: no row "
                        "in the shape `bench._row` prints")
    if not head:
        return _dropped("the HEAD bench table did not parse: no row in the "
                        "shape `bench._row` prints")
    rows = []
    for key in sorted(set(base) | set(head)):
        b, h = base.get(key), head.get(key)
        rb, rh = _ratio(b), _ratio(h)
        rows.append({"workload": key[0], "tier": key[1],
                     "baseline": b, "head": h,
                     "ratio_baseline": rb, "ratio_head": rh,
                     "ratio_of_ratios": (rh / rb if rb and rh else None)})
    lopsided = sorted({r["workload"] for r in rows
                       if r["baseline"] is None or r["head"] is None})
    # No reps in this sentence: the cell is handed two texts and cannot see
    # what they were run at. The tables say it themselves ("best of N timed
    # runs"), and the assembler prints the run's own number from the bench
    # rows -- a caption built from a constant would have said `reps=5` over
    # a dry run's `reps=1`, which is the dry run that caught it.
    why = f"{len(rows)} workload row(s); both tables parsed"
    if lopsided:
        why += (" -- read in one table only: " + ", ".join(lopsided))
    return {"word": "measured", "why": why, "rows": rows,
            "baseline_table": baseline_table, "head_table": head_table}


# -- H6: the census, per arm -----------------------------------------------
def cell_h6_values(rows: list[dict] | None) -> dict:
    """H6 restricted to `redaction.values`: `values redacted: N` equals the
    planted count on every arm, and `redaction.env` names exactly the token.

    Both directions are a STOP -- fewer is an under-firing rule and more an
    over-firing one -- which is why the check is equality and not a lower
    bound. And on every ARM: the census is a claim about all three
    recorders, so a reading missing for one of them drops the cell rather
    than letting the other two answer for it. Two readings for one arm drop
    it too: the count is a per-TRACE claim, and a recording that split over
    two traces matches neither the number §1 predicted nor its double.
    """
    if rows is None or not rows:
        return _dropped("no trace was read")
    seen: dict[str, list[str]] = {}
    for row in rows:
        seen.setdefault(row.get("arm"), []).append(row.get("run"))
    absent = [arm for arm in ARMS if arm not in seen]
    if absent:
        return _dropped("no trace read for: " + ", ".join(absent))
    twice = sorted(arm for arm in ARMS if len(seen[arm]) > 1)
    if twice:
        return _dropped("more than one trace for: "
                        + "; ".join(f"{arm} ({', '.join(seen[arm])})"
                                    for arm in twice))
    unread = sorted(row["run"] for row in rows
                    if row.get("values") is None or row.get("names") is None)
    if unread:
        return _dropped("the census could not be read for: "
                        + ", ".join(unread))
    bad = []
    for row in rows:
        want = EXPECTED_VALUES.get(row["arm"])
        if row["values"] != want:
            bad.append(f"{row['arm']} ({row['run']}) counted "
                       f"{row['values']} value(s), not {want}")
        if set(row["names"]) != {TOKEN_VAR}:
            bad.append(f"{row['arm']} ({row['run']}) redacted "
                       f"{sorted(row['names'])}, not exactly [{TOKEN_VAR}]")
    out = {"word": "STOP" if bad else "PASS", "offenders": bad,
           "traces": len(rows)}
    out["why"] = "; ".join(bad) if bad else (
        f"{len(rows)} trace(s): "
        + ", ".join(f"{row['arm']} {row['values']}" for row in rows)
        + f", each redacting exactly {TOKEN_VAR}")
    return out


#: The cells part B GATES on. H5 is not one of them and never can be.
GATED = ("H1-values", "H6-values")


def part_word(cells: dict) -> str:
    """The part's own word. `DONE` only when both gated cells PASSed --
    read out of the dict by name, so a cell that was never written is the
    STOP side rather than an absent key nobody notices. H5's `measured` is
    not a pass and is not asked to be one."""
    return ("DONE" if all(cells.get(c, {}).get("word") == "PASS"
                          for c in GATED) else "DONE-WITH-STOP")
