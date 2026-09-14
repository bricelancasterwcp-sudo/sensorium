#!/usr/bin/env python3
"""E16 part A's DECISION layer: what §1 fixed, and the four cells.

Split from `e16a.py` at the repository's 800-line ceiling, on the seam that
was already there: everything here is a pure function over rows somebody
could type by hand, and nothing here runs a subprocess, reads the clock or
knows where the box keeps its files. That is what lets
`tests/test_acceptance_e16_cells.py` exercise every verdict -- including
every STOP -- without the measurement, which runs once.

`e16a.py` re-exports every name below, so `e16a.cell_h1` and
`assemble_e16a`'s imports mean what they always meant.

WHAT A CELL MAY DECIDE
----------------------
PASS, STOP, or `dropped`, and never anything else. `dropped` is the answer
whenever a row it needs is `None` -- a phase that was killed, a file that
could not be stat'ed, a transcript that did not parse -- and whenever the
input is EMPTY, because "no file held the token" and "no file was examined"
are one mistyped path apart. The verdict words come from `RULES`, which is
§9's own PASS/STOP column: the cell tests hold every clause below against
the record on disk, so a rule softened here reddens there rather than
quietly deciding the measurement.
"""

from __future__ import annotations

import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rust" / "tests"))

from acceptance_e4_read import parse_refocus                      # noqa: E402

# -- what §1 fixed ---------------------------------------------------------

#: The variable the three recordings carry (§1, the plan's block).
TOKEN_VAR = "SENSORIUM_E16_TOKEN"
TOKEN_PREFIX, TOKEN_BODY = "sk-e16-", 33
#: The dry run's decoy. NOT `sk-`: part B's content rule keys on that
#: prefix, and a decoy that could match it would exercise a rule this part
#: does not ship while pretending to be a plumbing check.
DRY_PREFIX, DRY_BODY = "dry-", 4
_ALPHABET = string.ascii_letters + string.digits

#: The whole environment a recording sees, `PATH` first. Preflighted by the
#: controller and re-checked in `preflight`: not one of these names fires
#: rule v1, which is what makes H6's "exactly one name" a statement about
#: the token rather than about this box's shell.
ALLOWLIST = ("PATH", "HOME", "USER", "LANG", "TMPDIR", "CARGO_TARGET_DIR",
             "SENSORIUM_DIR", TOKEN_VAR)

#: §9's PASS/STOP column, copied from the record's §1 table -- each clause
#: WHOLE, and the test below checks it by EQUALITY against the row's own
#: cell rather than by substring: a substring check cannot see a clause cut
#: short, and H1's was, losing the sentence that says a fix is followed by a
#: re-measurement from zero. `tests/test_acceptance_e16_cells.py::test_the_
#: rule_table_is_the_records_own_words` is what holds this against the
#: record on disk, so a rule softened here reddens there rather than
#: deciding the measurement.
RULES = {
    "H1": {"PASS": "every count 0 where 0 is required",
           "STOP": "any non-zero: a missed path. Named, fixed, and the "
                   "whole of E16 re-measured from zero with a fresh token "
                   "\u2014 an acceptance test of correctness is re-run after "
                   "a fix, and the record says which run is the first PASS"},
    "H2": {"PASS": "all", "STOP": "any other mode"},
    "H3": {"PASS": "both", "STOP": "either the wrong way"},
    "H6": {"PASS": "exact",
           "STOP": "any other number: an over- or under-firing rule"},
}

#: The cells part A does NOT measure, and which part owns each. Written into
#: the results file as `dropped` with this reason: a cell nobody measured
#: and a cell that passed are two different rows.
DROPPED = (("H1-values", "part B"), ("H4", "part C"),
           ("H5", "part B"), ("H6-values", "part B"))

#: §1's four refocus readings, in the order they are run: both pairs with
#: the token unchanged, then both again after it is re-exported.
PREDICTIONS = (("python-unchanged", "granted"), ("rust-unchanged", "granted"),
               ("python-changed", "WITHHELD"), ("rust-changed", "WITHHELD"))

#: The three recorders part A records, and the arm names every phase keys
#: by. H6 expects ONE reading per arm and drops when a reading is missing:
#: "the traces I happened to read all passed" is not "the census matched on
#: every trace", and a phase that lost one recorder would otherwise report
#: the other two as the whole answer.
ARMS = ("python", "rust", "typescript")

#: The two trees H2 gates, named as `Part.modes` names them (relative to the
#: work root). Both have to EXIST and be readable: `find` over a missing
#: root prints nothing, and a cell handed nothing about the Rust spool would
#: PASS on the store alone -- the same short-input hole H3 and H6 had.
GATED_ROOTS = ("store-a", "rust-target/sensorium/spool")

#: The focused function, in both arms. R27: §1 guessed `compute` for Rust
#: and `main` for Python; `derive_sandbox` is the aliasing case's own
#: seeded-bug function in each language, and the amendment is recorded in
#: the record's §2 beside §1 rather than edited into it.
FOCUS = "derive_sandbox"

#: The versions §1 expects; `versions` records what they were.
EXPECTED = {"sensorium": "0.15.0", "sensorium-rt": "0.6.0",
            "cargo-sensorium": "0.7.0", "sensorium-ts": "0.5.0"}

#: §1's kill rules, in seconds, and the dry run's minute. The Rust arm has
#: its own entry because §1 allows it 1200 s if the cold build needs one;
#: measured on this box it is under a second, and the row records that.
TIMERS = {"record": 600, "record_rust": 600, "refocus": 900, "part": 45 * 60}
DRY_TIMERS = {"record": 60, "record_rust": 60, "refocus": 60, "part": 15 * 60}


class Refused(Exception):
    """A precondition this instrument will not run without."""


# -- the cells -------------------------------------------------------------
def _dropped(why: str) -> dict:
    return {"word": "dropped", "why": why}


def cell_h1(files: list[dict] | None) -> dict:
    """H1-env: the token's bytes, per file, over everything swept.

    `files` is one row per file EXAMINED -- `grep -rc` prints a count for
    every file it read, including the zeros -- so an empty list is a sweep
    that examined nothing, which is dropped rather than passed. That is the
    failure this cell is most exposed to: a mistyped root makes "no file
    held the token" and "no file was looked at" the same output.
    """
    if files is None:
        return _dropped("the grep sweep did not run")
    if not files:
        return _dropped("the grep sweep examined no file at all")
    unread = [f["path"] for f in files if f.get("count") is None]
    if unread:
        return _dropped("counts missing for: " + ", ".join(sorted(unread)))
    bad = sorted(f["path"] for f in files if f["count"])
    out = {"word": "STOP" if bad else "PASS", "offenders": bad,
           "files_examined": len(files)}
    out["why"] = (f"the token's bytes appear in {len(bad)} file(s): "
                  + ", ".join(bad)) if bad else (
        f"{len(files)} file(s) examined, every count 0")
    return out


def cell_h2(entries: list[dict] | None, roots: list[dict] | None) -> dict:
    """H2: 0600 on every file and 0700 on every directory a recorder made.

    A row's `scope` decides whether it is gated. `out` rows -- the
    instrument's own directories and cargo's build tree -- are carried so a
    reader can see they were looked at and are answered for by nobody here;
    gating them would make this cell a statement about `cargo build`.

    `roots` is one status per tree in `GATED_ROOTS`, and it is a REQUIRED
    argument rather than one with a default: `find` over a root that is not
    there prints nothing and exits non-zero, so without it a run whose Rust
    arm never recorded would sweep the store, find every mode right, and
    PASS -- reporting a claim about two trees having looked at one. A
    missing or failed root drops the cell and names the root.
    """
    if entries is None or roots is None:
        return _dropped("the mode sweep did not run")
    missing = [r for r in GATED_ROOTS
               if r not in {row["root"] for row in roots}]
    if missing:
        return _dropped("no sweep status for: " + ", ".join(missing))
    failed = [row for row in roots if not row["ok"]]
    if failed:
        return _dropped("the sweep could not read: "
                        + "; ".join(f"{row['root']} ({row['why']})"
                                    for row in failed))
    if not entries:
        return _dropped("the mode sweep found no file at all")
    unread = [e["path"] for e in entries if e.get("mode") is None]
    if unread:
        return _dropped("modes missing for: " + ", ".join(sorted(unread)))
    gated = [e for e in entries if e["scope"] == "in"]
    if not gated:
        return _dropped("no file in this cell's scope was swept")
    bad = [{"path": e["path"], "mode": e["mode"], "kind": e["kind"],
            "want": "700" if e["kind"] == "dir" else "600"}
           for e in gated
           if e["mode"] != ("700" if e["kind"] == "dir" else "600")]
    out = {"word": "STOP" if bad else "PASS", "offenders": bad,
           "in_scope": len(gated), "out_of_scope": len(entries) - len(gated)}
    out["why"] = (f"{len(bad)} path(s) carry another mode: "
                  + ", ".join(f"{b['mode']} {b['path']} (want {b['want']})"
                              for b in bad)) if bad else (
        f"{len(gated)} path(s) in scope, every file 600 and directory 700")
    return out


def read_pair(name: str, predicted: str, text: str,
              in_recorded_env: bool) -> dict:
    """One refocus transcript, read against what §1 predicted of it.

    Two halves, and both are needed. NEGATIVE: the env line names only what
    the check EXCLUDED -- the shell's own bookkeeping, a recorder's
    variables, an uncomparable digest, a differing name -- so a granted pair
    that names the token has excluded it, whatever the licence says.
    POSITIVE: the original trace has to have recorded the variable at all,
    which is H6's reading handed in here rather than re-derived, because a
    pair whose trace never held it compared nothing to nothing.

    `parse_refocus` is `rust/tests/acceptance_e4_read.py`'s, imported rather
    than re-written: one parser over `refocus`'s output, and E4's suite is
    what keeps it honest.
    """
    p = parse_refocus(text)
    line = p["env_line"] or ""
    differ = ""
    m = re.search(r"variable\(s\) differ: (?P<names>.*?)(?:  |$)", line)
    if m:
        differ = m.group("names")
    row = {"name": name, "predicted": predicted,
           "licence": p["licence"], "env_status": p["env_status"],
           "env_line": p["env_line"], "verdict_word": p["verdict_word"],
           "verdict_line": p["verdict_line"],
           "licence_line": p["licence_line"],
           "token_on_env_line": TOKEN_VAR in line,
           "token_in_changed": TOKEN_VAR in differ,
           "token_in_recorded_env": in_recorded_env}
    if p["licence"] is None or p["env_status"] is None:
        row["ok"] = None
        row["why"] = "the transcript carries no licence or no env status"
        return row
    if predicted == "granted":
        row["ok"] = (p["licence"] == "granted"
                     and p["env_status"] == "unchanged"
                     and in_recorded_env
                     and not row["token_on_env_line"])
        row["why"] = ("licence granted, environment unchanged, and the "
                      "token named on no exclusion list") if row["ok"] else (
            f"predicted a granted licence with {TOKEN_VAR} among the "
            f"compared; read licence {p['licence']}, env {p['env_status']}, "
            f"token named on the env line: {row['token_on_env_line']}, "
            f"token in the recorded environment: {in_recorded_env}")
    else:
        row["ok"] = (p["licence"] == "WITHHELD"
                     and p["env_status"] == "CHANGED"
                     and row["token_in_changed"])
        row["why"] = (f"licence WITHHELD over {TOKEN_VAR} in the changed "
                      f"list") if row["ok"] else (
            f"predicted WITHHELD with {TOKEN_VAR} in the changed list; read "
            f"licence {p['licence']}, env {p['env_status']}, token in the "
            f"changed list: {row['token_in_changed']}")
    return row


def cell_h3(pairs: list[dict] | None) -> dict:
    """H3: all four pairs as predicted, or the cell STOPs naming the ones
    that were not.

    Three pairs out of four is not "both", and this cell used to say so in
    prose while passing on any non-empty list. Every name in `PREDICTIONS`
    has to be present before a verdict is reached; a pair whose transcript
    did not parse is a hole, and one hole drops the cell."""
    if pairs is None or not pairs:
        return _dropped("no refocus pair ran")
    absent = [name for name, _predicted in PREDICTIONS
              if name not in {p["name"] for p in pairs}]
    if absent or len(pairs) != len(PREDICTIONS):
        return _dropped(f"{len(pairs)} of {len(PREDICTIONS)} pre-registered "
                        "pair(s) read"
                        + (": missing " + ", ".join(absent) if absent else ""))
    unread = [p["name"] for p in pairs if p.get("ok") is None]
    if unread:
        return _dropped("unreadable transcript(s): " + ", ".join(unread))
    bad = [p["name"] for p in pairs if not p["ok"]]
    out = {"word": "STOP" if bad else "PASS", "offenders": bad,
           "pairs": pairs}
    out["why"] = (f"{len(bad)} of {len(pairs)} pair(s) read the other way: "
                  + "; ".join(f"{p['name']}: {p['why']}"
                              for p in pairs if not p["ok"])) if bad else (
        f"all {len(pairs)} pair(s) read as predicted")
    return out


def cell_h6(traces: list[dict] | None) -> dict:
    """H6-env: `redaction.env` holds exactly `{SENSORIUM_E16_TOKEN}` on every
    trace. Both directions are a STOP -- a second name is an over-firing
    rule and an empty table an under-firing one -- which is why the check is
    set equality and not a lower bound.

    And on every ARM: the census is a claim about all three recorders, so a
    reading missing for one of them drops the cell rather than letting the
    other two answer for it."""
    if traces is None or not traces:
        return _dropped("no trace was read")
    absent = [a for a in ARMS if a not in {t.get("arm") for t in traces}]
    if absent:
        return _dropped("no trace read for: " + ", ".join(absent))
    unread = [t["run"] for t in traces if t.get("names") is None]
    if unread:
        return _dropped("names unreadable for: " + ", ".join(sorted(unread)))
    bad = [t["run"] for t in traces if set(t["names"]) != {TOKEN_VAR}]
    out = {"word": "STOP" if bad else "PASS", "offenders": bad,
           "traces": len(traces)}
    out["why"] = ("redacted names other than the token on: "
                  + ", ".join(f"{t['run']} {sorted(t['names'])}"
                              for t in traces
                              if t["run"] in bad)) if bad else (
        f"{len(traces)} trace(s), each redacting exactly {TOKEN_VAR}")
    return out


def part_word(cells: dict) -> str:
    """The part's own word. `DONE` only when every cell PASSed: a dropped
    cell is not a passed one, and the part says so in its word rather than
    in a footnote under a `DONE`."""
    return ("DONE" if all(c["word"] == "PASS" for c in cells.values())
            else "DONE-WITH-STOP")

