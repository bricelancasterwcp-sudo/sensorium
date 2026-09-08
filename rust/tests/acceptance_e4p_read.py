#!/usr/bin/env python3
"""The E4′ reader: what one `sensorium refocus` answer says, read by this
record's own parsers.

WHY THIS IS NOT `acceptance_e4_read`
------------------------------------
E4's record is CLOSED. Its reader is evidence for a published measurement
and is not edited to suit a later one. Two things moved under it since:

* **R2 gave the pair line a clause.** `refocus_rust` prints
  `run: <id>   child runs excluded from the pair: <ids>` where a child run
  was set aside. E4's `NEW_RUN` is `^run: (?P<run>\\S+)$` -- anchored at the
  end of the line -- so it matches the old shape and returns `None` for the
  new one. A `None` pair id is recorded as "no pair", and under §1's H3 a
  pair count other than 1 is a **STOP**: the instrument would manufacture
  the very kill it exists to detect. This module parses `run: <id>` as a
  PREFIX and reads the clause beside it.
* **R1 rewrote the licence's thread sentences**, which is exactly what this
  record measures. A parser written before the change cannot be the one that
  reads the change.

Every pattern below is copied FROM THE SOURCE that prints it -- named in
each docstring -- and `tests/test_acceptance_e4p_read.py` exercises each one
against text the real command wrote, never against a string invented to
match the regex.

WHAT IT DECIDES: NOTHING
------------------------
The verdict WORD and the exit status are read apart and never derived from
each other; the licence's verified list and its unverifiable list are two
fields that are never summed; an unread field is `None` and never `0`.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4pp_read import (read_e4pp_clauses,          # noqa: E402
                                  rt_hash_of)

# ------------------------------------------------------------ the verdict

#: `refocus_cmd.report`, in its three words, and the exit each is paired
#: with (`refocus_rust`). Carried so a disagreement between the printed word
#: and the process exit is a FINDING rather than a number one of them wins.
VERDICT_EXIT = {"MATCH": 0, "DIVERGED": 1, "REFUSED": 3}
PRE_RERUN_REFUSAL_EXIT = 2

REFOCUS_VERDICT = re.compile(r"^refocus verdict: (?P<word>MATCH|DIVERGED|"
                             r"REFUSED)\b(?P<rest>.*)$", re.M)
DIFF_VERDICT = re.compile(r"^verdict: MATCH(?P<modulo> modulo location)? -- "
                          r"identical causal streams \((?P<events>\d+) "
                          r"events?\)", re.M)
DIVERGED_STEP = re.compile(r"^verdict: DIVERGED at causal step (?P<i>\d+)$",
                           re.M)

# --------------------------------------------------------- the pair line

#: `refocus_rust._verify`:
#:
#:     print(f"run: {new_id}" + (f"   {note}" if note else ""))
#:
#: A PREFIX pattern, deliberately. `(?P<rest>.*)$` swallows R2's clause when
#: one is there and matches the empty string when it is not, so ONE pattern
#: reads both shapes and the id comes back either way.
PAIR_RUN = re.compile(r"^run: (?P<run>\S+)(?P<rest>.*)$", re.M)
#: `refocus_rust.children_note`, verbatim. The ids are comma-separated and
#: the clause is absent -- not empty -- when nothing was excluded, which is
#: why `child_clause` is `None` rather than `""` on the 61 expected here.
CHILD_NOTE = re.compile(r"child runs excluded from the pair: (?P<ids>.+?)\s*$")

NEW_TRACE = re.compile(r"^trace: (?P<path>.*)$", re.M)
REFOCUS_OF = re.compile(r"^refocus-of: (?P<run>\S+)\s+cmd: (?P<cmd>.*)$", re.M)
CWD_LINE = re.compile(r"^cwd: (?P<cwd>.*)$", re.M)
FOCUS_LINE = re.compile(r"^focus: (?P<focus>.*?)\s\s+window: (?P<window>.*)$",
                        re.M)
EXIT_LINE = re.compile(r"^exit: rerun (?P<rerun>\S+)\s+original "
                       r"(?P<original>\S+)\s*$", re.M)
DRIVER_REPORTED = re.compile(r"^driver reported: (?P<line>run: .*)$", re.M)

# ------------------------------------------------------- the world checks

#: `refocus_world._source_state` / `refocus_rust._env_of`. Three statuses,
#: and the third -- `unverifiable` -- is never counted as verified anywhere.
SOURCE_LINE = re.compile(r"^source: (?P<rest>.*)$", re.M)
ENV_LINE = re.compile(r"^env: (?P<rest>.*)$", re.M)
STATUSES = ("unchanged", "CHANGED", "unverifiable")

#: Task 5b's clause, `refocus_env.relocated_clause` verbatim. §1.4 gives the
#: re-run a FRESH `CARGO_TARGET_DIR`, so the four variables cargo derives
#: from the target root differ on EVERY pair of this record; 5b asks whether
#: each difference disappears when the original's root is rewritten to the
#: re-run's, and names the keys it explained that way. They are recorded per
#: pair -- named, never counted away -- because "the tool re-ran your
#: program somewhere else" and "your environment changed" are the two
#: readings this endpoint has to keep apart.
ENV_RELOCATED = re.compile(
    r"(?P<n>\d+) variable\(s\) differ only by the target directory: "
    r"(?P<keys>.+?); treated as unchanged")
#: `refocus_world._env_state`'s CHANGED branch. Its name list is CAPPED at
#: eight and then carries `, +N more`, so the COUNT is authoritative and the
#: names may be short -- recorded as two fields, with the truncation stated.
ENV_CHANGED = re.compile(
    r"^env: CHANGED since the original run -- (?P<n>\d+) variable\(s\) "
    r"differ: (?P<keys>.+?)\s{3}\(names only\)", re.M)
ENV_CHANGED_MORE = re.compile(r",\s*\+(?P<n>\d+) more$")
#: `refocus_rust._env_of` appends this LAST, after the relocated clause.
#: Its own field: "the recorder does not compare this" and "the world moved
#: this" are different claims about one variable.
ENV_RECORDER_OWN = re.compile(
    r"the recorder's own, also not compared: (?P<keys>.+?)\s*$", re.M)

#: `refocus_rust._print_unverifiable` and `refocus_world.UNVERIFIABLE`.
UNVERIFIABLE_HEADER = re.compile(
    r"^checks that could not run on this pair\b.*$", re.M)
UNVERIFIABLE_OUTPUT = "output: unverifiable (not recorded)"
UNVERIFIABLE_CHILDREN = "children: unverifiable (not witnessed)"

#: `refocus_cmd._refuse` (exit 2, nothing re-run) and
#: `refocus_rust._refused_after_rerun` (exit 3, the driver DID run). Told
#: apart by which sentence carried them, never by the exit alone.
PRE_RERUN_REFUSAL = re.compile(
    r"^error: cannot refocus (?P<run>\S+): (?P<sentence>.*)$", re.M)
REFUSED_AFTER = re.compile(r"^refocus verdict: REFUSED -- (?P<why>.*)$", re.M)

#: `refocus_rust.run` prints this immediately before `_launch`, so its
#: presence is the instrument's own evidence that the driver child started.
RERUN_BANNER = ("--- rerunning (the driver's build output is above and "
                "below; the lines below are its own) ---")
DRIVER_EXIT = re.compile(r"driver exit (?P<rc>-?\d+)")

#: cargo's own reported build time inside the driver child's stderr, in both
#: spellings. Reported, never gated: nothing here is gated on a wall.
CARGO_FINISHED = re.compile(
    r"^\s*Finished .*? in (?:(?P<min>\d+)m )?(?P<secs>[0-9.]+)s\s*$", re.M)

# --------------------------------------------------- R1: the licence lines

#: `refocus_cmd.report`'s licence, in its two shapes.
LICENCE_GRANTED = re.compile(r"^licence: verified against (?P<run>\S+) on "
                             r"exactly these points, and no others:$", re.M)
LICENCE_WITHHELD = re.compile(r"^licence: WITHHELD\b(?P<rest>.*)$", re.M)

#: `refocus_world._verified_facts`, the R1 branch:
#:
#:     f"no thread started besides the main one{harness_clause}"
#:
#: where `harness_exclusion` builds the clause as
#: `" and {n} harness thread{s} ({phrase})"`. The OTHER branch -- taken
#: where the recorder started no thread of its own -- prints the provenance
#: clause instead, and this pattern must NOT match it: a granted line that
#: hides the exclusion is H1's second-reading finding, and a parser that
#: read it as though the exclusion were named would make that finding
#: unreachable.
GRANTED_THREADS = re.compile(
    r"no thread started besides the main one and (?P<harness>\d+) harness "
    r"thread(?:s)? \((?P<phrase>[^)]*)\)")
#: The same clause on the other side of the licence:
#: `refocus_world._licence_caveats`'s
#:
#:     f"{label} started {started} thread(s) besides the main "
#:     f"one{harness_clause}. "
#:
#: `started` is already NET of the harness threads (R1 subtracts before it
#: prints), so this is the PROGRAM's own count -- the number §1.2 predicts
#: as 1, 4, 4, 4. The raw count is derived from it, never read instead.
WITHHELD_THREADS = re.compile(
    r"(?P<label>the original|the rerun) started (?P<program>\d+) thread\(s\) "
    r"besides the main one and (?P<harness>\d+) harness thread(?:s)? "
    r"\((?P<phrase>[^)]*)\)\.")
#: A withheld thread caveat with NO harness clause: the shape a reason takes
#: when the rule did NOT fire. §1.2 calls a reason naming the raw count
#: (2, 5, 5, 5) H1's STOP, so it has to be readable as itself.
WITHHELD_THREADS_UNSUBTRACTED = re.compile(
    r"(?P<label>the original|the rerun) started (?P<program>\d+) thread\(s\) "
    r"besides the main one\.")

#: `refocus_cmd._print_thread_line`, carrying `refocus_world.harness_note`'s
#: clause: the same fact in the grammatical slot for a line whose counts the
#: harness thread is NOT one of.
THREADS_LINE = re.compile(r"^threads: (?P<rest>.*)$", re.M)
TASKS_LINE = re.compile(r"^tasks: (?P<rest>.*)$", re.M)
HARNESS_NOTE = re.compile(
    r"; (?P<harness>\d+) harness thread(?:s)? \((?P<phrase>[^)]*)\) "
    r"(?:is|are) not among these counts")

#: A caveat saying the thread bookkeeping could not be read AT ALL, in all
#: three shapes `caps.witness_gap` gives it (`_licence_caveats`'s legacy
#: sentence, the declared-false one, and the declared-true-but-missing one).
#: Every one ends with the same clause, which is what this anchors on.
#:
#: It exists for the fallback below and for one reason: the ABSENCE of a
#: thread sentence means zero only because `_licence_caveats` emits one
#: above zero. Where the record itself could not be read, that inference
#: does not hold, and a `0` printed there would be an invented number.
THREAD_RECORD_UNAVAILABLE = re.compile(
    r"^(?:the original|the rerun)\b.*\bthread\b.*absence of the record is "
    r"not a record of absence")


def _status_of(rest: str | None) -> str | None:
    """Which of the three statuses a line is -- `None` for a fourth
    spelling, never a guess. Reading an unknown status as one of these is
    how a check that did not run gets counted as one that passed."""
    if rest is None:
        return None
    for status in STATUSES:
        if rest.startswith(status):
            return status
    return None


def bullets_after(text: str, header: str) -> list[str]:
    """The contiguous `  - ` bullets directly under `header`.

    Contiguity keeps one answer's bullet blocks apart: the verified list,
    the caveat list and the blind-spot block are all `  - ` bullets, and a
    reader that took every bullet in the output would merge three different
    claims into one.
    """
    idx = text.find(header)
    if idx < 0:
        return []
    out = []
    for line in text[idx + len(header):].splitlines()[1:]:
        if line.startswith("  - "):
            out.append(line[4:].strip())
        elif line.strip():
            break
    return out


def parse_refocus(text: str) -> dict:
    """One `sensorium refocus <run> --focus <name>` answer, whole."""
    out: dict = {
        "refocus_of": None, "driver_cmd": None, "cwd": None,
        "focus": None, "window": None,
        "source_line": None, "source_status": None,
        "env_line": None, "env_status": None,
        "env_relocated_keys": None, "env_relocated_n": None,
        "env_changed_keys": None, "env_changed_n": None,
        "env_changed_keys_truncated": None,
        "env_changed_for_other_keys": None,
        "env_recorder_own_keys": None,
        # E4″: R1's strip and R4's session set, read from the same line and
        # kept apart from the changed list, which is the only one that
        # withholds.
        "env_stripped_keys": None,
        "env_session_n": None, "env_session_keys": None,
        "env_session_keys_truncated": None,
        "env_unchanged_outside_session": None, "env_session_set": None,
        "exit_line": None, "exit_rerun": None, "exit_original": None,
        "exit_status_equal": None,
        "pair_run": None, "pair_run_line": None,
        "child_clause": None, "excluded_children": [],
        "new_trace": None, "driver_run_lines": [],
        "verdict_word": None, "verdict_line": None,
        "diff_verdict_line": None, "diff_events": None,
        "threads_line": None, "threads_harness": None,
        "threads_harness_phrase": None,
        "tasks_line": None,
        "licence": None, "licence_line": None, "licence_facts": [],
        "licence_caveats": [],
        "unverifiable": [], "unverifiable_header": None,
        "pre_rerun_refusal": None, "pre_rerun_refusal_run": None,
        "refused_after_rerun": None,
        "diverged_step": None,
        "child_launched": RERUN_BANNER in text,
        "driver_exit": None,
    }
    m = REFOCUS_OF.search(text)
    if m:
        out["refocus_of"] = m.group("run")
        out["driver_cmd"] = m.group("cmd").strip()
    m = CWD_LINE.search(text)
    if m:
        out["cwd"] = m.group("cwd").strip()
    m = FOCUS_LINE.search(text)
    if m:
        focus = m.group("focus").strip()
        out["focus"] = [] if focus == "-" else [f.strip()
                                                for f in focus.split(",")]
        out["window"] = m.group("window").strip()
    m = SOURCE_LINE.search(text)
    if m:
        out["source_line"] = m.group(0).strip()
        out["source_status"] = _status_of(m.group("rest"))
    m = ENV_LINE.search(text)
    if m:
        out["env_line"] = m.group(0).strip()
        out["env_status"] = _status_of(m.group("rest"))
        _read_env_clauses(out["env_line"], out)
    m = EXIT_LINE.search(text)
    if m:
        out["exit_line"] = m.group(0).strip()
        out["exit_rerun"] = m.group("rerun")
        out["exit_original"] = m.group("original")
        out["exit_status_equal"] = m.group("rerun") == m.group("original")
    _read_pair_line(text, out)
    m = NEW_TRACE.search(text)
    if m:
        out["new_trace"] = m.group("path").strip()
    out["driver_run_lines"] = [d.group("line")
                               for d in DRIVER_REPORTED.finditer(text)]
    m = REFOCUS_VERDICT.search(text)
    if m:
        out["verdict_word"] = m.group("word")
        out["verdict_line"] = m.group(0).strip()
    m = DIFF_VERDICT.search(text)
    if m:
        out["diff_verdict_line"] = m.group(0).strip()
        out["diff_events"] = int(m.group("events"))
    m = THREADS_LINE.search(text)
    if m:
        out["threads_line"] = m.group(0).strip()
        note = HARNESS_NOTE.search(out["threads_line"])
        if note:
            out["threads_harness"] = int(note.group("harness"))
            out["threads_harness_phrase"] = note.group("phrase")
    m = TASKS_LINE.search(text)
    if m:
        out["tasks_line"] = m.group(0).strip()
    m = LICENCE_GRANTED.search(text)
    if m:
        out["licence"] = "granted"
        out["licence_line"] = m.group(0)
        out["licence_facts"] = bullets_after(text, m.group(0))
    else:
        m = LICENCE_WITHHELD.search(text)
        if m:
            out["licence"] = "WITHHELD"
            out["licence_line"] = m.group(0).strip()
            out["licence_caveats"] = bullets_after(text, m.group(0))
    m = UNVERIFIABLE_HEADER.search(text)
    if m:
        out["unverifiable_header"] = m.group(0).strip()
        out["unverifiable"] = bullets_after(text, m.group(0))
    m = PRE_RERUN_REFUSAL.search(text)
    if m:
        out["pre_rerun_refusal"] = m.group("sentence").strip()
        out["pre_rerun_refusal_run"] = m.group("run")
    m = REFUSED_AFTER.search(text)
    if m:
        out["refused_after_rerun"] = m.group("why").strip()
    m = DIVERGED_STEP.search(text)
    if m:
        out["diverged_step"] = int(m.group("i"))
    m = DRIVER_EXIT.search(text)
    if m:
        out["driver_exit"] = int(m.group("rc"))
    return out


def _read_pair_line(text: str, out: dict) -> None:
    """The `run:` line under `--- verdict ---`, and R2's clause beside it.

    The FIRST `run:` line at the start of a line after the verdict banner.
    Not simply the first in the output: the driver's own `run:` lines are
    echoed above under a `driver reported: ` prefix (so they do not start a
    line and cannot match), but a future spelling that did would otherwise
    silently take this one's place.
    """
    banner = text.find("--- verdict ---")
    m = PAIR_RUN.search(text, banner if banner >= 0 else 0)
    if not m:
        return
    out["pair_run"] = m.group("run")
    out["pair_run_line"] = m.group(0).strip()
    note = CHILD_NOTE.search(m.group("rest"))
    if note:
        out["child_clause"] = note.group(0).strip()
        out["excluded_children"] = [i.strip()
                                    for i in note.group("ids").split(",")
                                    if i.strip()]


def _read_env_clauses(line: str, out: dict) -> None:
    """Task 5b's two readings of ONE `env:` line, kept apart.

    `env_relocated_keys` is what the target-root rule explained; it is `[]`
    -- not `None` -- when the line printed no such clause, because the line
    WAS read and it named none. `env_changed_for_other_keys` is whether the
    clause fired for anything else, which is the reading that still
    withholds a licence.

    Both stay `None` when there is no `env:` line at all: a pair with no
    reading has no lists, and `[]` there would claim the line said nothing
    moved.
    """
    m = ENV_RELOCATED.search(line)
    if m:
        out["env_relocated_keys"] = [k.strip()
                                     for k in m.group("keys").split(",")
                                     if k.strip()]
        out["env_relocated_n"] = int(m.group("n"))
    else:
        out["env_relocated_keys"], out["env_relocated_n"] = [], 0
    m = ENV_CHANGED.search(line)
    if m:
        shown = m.group("keys").strip()
        more = ENV_CHANGED_MORE.search(shown)
        if more:
            shown = shown[:more.start()]
        out["env_changed_keys"] = [k.strip() for k in shown.split(",")
                                   if k.strip()]
        out["env_changed_n"] = int(m.group("n"))
        out["env_changed_keys_truncated"] = bool(more)
    else:
        out["env_changed_keys"], out["env_changed_n"] = [], 0
        out["env_changed_keys_truncated"] = False
    # Derived from the COUNT, never from the name list, which the printer
    # caps at eight.
    out["env_changed_for_other_keys"] = bool(out["env_changed_n"])
    m = ENV_RECORDER_OWN.search(line)
    out["env_recorder_own_keys"] = ([k.strip()
                                     for k in m.group("keys").split(",")
                                     if k.strip()] if m else [])
    read_e4pp_clauses(line, out)


def licence_partition(parsed: dict) -> dict:
    """H1's endpoint for ONE pair: the word, and the thread arithmetic under
    it.

    Three numbers that are never conflated. `program_threads` is the
    program's OWN count -- what R1 leaves after the subtraction, and what
    §1.2 predicts as 0 on the 57 and 1/4/4/4 on the four.
    `harness_threads` is what was taken out, which the sentence must NAME.
    `raw_thread_count` is their sum, DERIVED here so §1.2's "a reason naming
    the raw count never subtracted" can be checked without reading a second
    sentence.

    Everything is `None` for a licence line that never printed. A pair whose
    licence could not be read has NO partition, and `0 program threads,
    granted` would put a measured-looking cell where a missing one belongs.

    **Where each count came from is recorded beside it** (E4′ §5's gap 1).
    The licence's own thread sentence is the first reading; the `threads:`
    line is the second, and `_fall_back_to_the_threads_line` takes it where
    the first is silent. `counts_source` says which -- `"licence-clause"`
    when both counts came from the licence, `"threads-line"` when either
    came from the line beside it, `None` when neither was read -- and
    `counts_source_by_count` says it per count, because the two can differ
    on one pair (a granted line that hides the exclusion states its program
    count and withholds its harness one).
    """
    out = {
        "licence": parsed.get("licence"),
        "program_threads": None, "harness_threads": None,
        "raw_thread_count": None, "harness_phrase": None,
        "names_the_exclusion": None, "per_label": {}, "sides_agree": None,
        "unsubtracted_labels": [],
        "counts_source": None,
        "counts_source_by_count": {"program_threads": None,
                                   "harness_threads": None},
        "counts_unread_reason": None,
    }
    if out["licence"] == "granted":
        # A granted licence's thread FACT. Program threads are 0 by the
        # sentence's own words -- "no thread started besides the main one"
        # -- whether or not the harness clause follows; what the clause
        # decides is whether the exclusion was NAMED, which is the second
        # reading, not the count.
        facts = parsed.get("licence_facts") or []
        stated = [f for f in facts
                  if f.startswith("no thread started besides the main one")]
        if stated:
            out["program_threads"] = 0
            out["counts_source_by_count"]["program_threads"] = (
                "licence-clause")
            m = GRANTED_THREADS.search(stated[0])
            out["names_the_exclusion"] = bool(m)
            if m:
                out["harness_threads"] = int(m.group("harness"))
                out["harness_phrase"] = m.group("phrase")
                out["raw_thread_count"] = int(m.group("harness"))
                out["counts_source_by_count"]["harness_threads"] = (
                    "licence-clause")
            else:
                out["raw_thread_count"] = 0
            out["sides_agree"] = True
    elif out["licence"] == "WITHHELD":
        caveats = parsed.get("licence_caveats") or []
        named, harness, phrases, unsubtracted = {}, set(), set(), []
        for caveat in caveats:
            m = WITHHELD_THREADS.search(caveat)
            if m:
                named[m.group("label")] = int(m.group("program"))
                harness.add(int(m.group("harness")))
                phrases.add(m.group("phrase"))
                continue
            u = WITHHELD_THREADS_UNSUBTRACTED.search(caveat)
            if u:
                named[u.group("label")] = int(u.group("program"))
                unsubtracted.append(u.group("label"))
        if named:
            out["per_label"] = named
            values = set(named.values())
            out["sides_agree"] = len(values) == 1
            out["program_threads"] = (next(iter(values)) if len(values) == 1
                                      else max(values))
            out["counts_source_by_count"]["program_threads"] = (
                "licence-clause")
            out["names_the_exclusion"] = not unsubtracted and bool(harness)
            out["unsubtracted_labels"] = unsubtracted
            if len(harness) == 1:
                out["harness_threads"] = next(iter(harness))
                out["raw_thread_count"] = (out["program_threads"]
                                           + out["harness_threads"])
                out["counts_source_by_count"]["harness_threads"] = (
                    "licence-clause")
            if len(phrases) == 1:
                out["harness_phrase"] = next(iter(phrases))
    if out["licence"] is not None and (out["program_threads"] is None
                                       or out["harness_threads"] is None):
        _fall_back_to_the_threads_line(parsed, out)
    sources = set(out["counts_source_by_count"].values())
    out["counts_source"] = (
        None if sources == {None}
        else "threads-line" if "threads-line" in sources
        else "licence-clause")
    return out


def _fall_back_to_the_threads_line(parsed: dict, out: dict) -> None:
    """E4′ §5's gap 1: the counts the licence's own sentence left silent,
    taken from the `threads:` line -- or NOT taken, with the reason.

    `_licence_caveats` emits its thread sentence only where the program's
    own count is ABOVE ZERO, so a pair withheld for something else and
    running no thread of its own carries no thread sentence at all. E4′
    published `null` for both counts on all 61 pairs for exactly that
    reason, which took `harness_threads_all_one` to false over 61 pairs
    each printing one harness thread on the line directly beside it.

    Two things this does NOT do, and both are the point:

    * it does not fire where a caveat says the thread record could not be
      read at all -- there the absence of a sentence is not a zero;
    * it does not repair `names_the_exclusion`. A granted line that hid the
      exclusion still hid it; the fallback supplies the missing NUMBER, and
      H1's second reading about the WORDING is left able to fire.
    """
    caveats = parsed.get("licence_caveats") or []
    blocked = next((c for c in caveats
                    if THREAD_RECORD_UNAVAILABLE.search(c)), None)
    if blocked:
        out["counts_unread_reason"] = (
            "the licence printed no thread sentence AND a caveat says the "
            "thread record could not be read at all, so the absence of a "
            f"sentence is not a count of zero: {blocked[:160]}")
        return
    harness = parsed.get("threads_harness")
    if harness is None:
        out["counts_unread_reason"] = (
            "the licence's thread sentence is silent and the `threads:` "
            "line carries no harness note, so there is no second reading "
            "to fall back to")
        return
    if out["program_threads"] is None:
        # Zero BY THE PRINTER'S OWN RULE (`_licence_caveats`: `if started >
        # 0`), not by assumption -- and only after the block above has
        # ruled out a pair whose bookkeeping was unreadable.
        out["program_threads"] = 0
        out["counts_source_by_count"]["program_threads"] = "threads-line"
    if out["harness_threads"] is None:
        out["harness_threads"] = harness
        out["harness_phrase"] = (out["harness_phrase"]
                                 or parsed.get("threads_harness_phrase"))
        out["counts_source_by_count"]["harness_threads"] = "threads-line"
    out["raw_thread_count"] = out["program_threads"] + out["harness_threads"]


def licence_counts(parsed: dict) -> dict:
    """The four verified/unverifiable counts for ONE pair, kept apart.

    `source`, `env` and `exit` are checks that RAN. `output` and `children`
    are UNVERIFIABLE by construction on a Rust pair and are counted in their
    own field -- never added into a verified total, which is the rule §1.4
    binds this record to and the reason no `verified_total` key exists here.
    """
    return {
        "source_status": parsed.get("source_status"),
        "source_verified": parsed.get("source_status") == "unchanged",
        "env_status": parsed.get("env_status"),
        "env_verified": parsed.get("env_status") == "unchanged",
        "exit_verified": parsed.get("exit_status_equal"),
        "licence": parsed.get("licence"),
        "output_unverifiable": UNVERIFIABLE_OUTPUT in (
            parsed.get("unverifiable") or []),
        "children_unverifiable": UNVERIFIABLE_CHILDREN in (
            parsed.get("unverifiable") or []),
        "verified_facts": len(parsed.get("licence_facts") or []),
        "unverifiable_checks": len(parsed.get("unverifiable") or []),
    }


def cargo_finished_seconds(text: str) -> list[float]:
    """Every `Finished ... in <n>s` cargo printed, in seconds. A list: one
    re-run can rebuild more than one profile, and a reading that took the
    first would report one of them as the whole build."""
    out = []
    for m in CARGO_FINISHED.finditer(text):
        secs = float(m.group("secs"))
        if m.group("min"):
            secs += 60.0 * int(m.group("min"))
        out.append(round(secs, 3))
    return out


# ------------------------------------------------------------- the store

def connect_ro(db: Path) -> sqlite3.Connection:
    """A trace, opened READ-ONLY through the URI form.

    Every store this record reads -- the kept one above all -- is opened
    this way, so a reader bug cannot write to the input it is measuring.
    """
    return sqlite3.connect(f"file:{Path(db)}?mode=ro", uri=True)


def meta_value(raw):
    """One `meta` cell, decoded the way the store encodes it: `set_meta`
    writes `json.dumps(value)`, so a run id sits in the column QUOTED. Read
    raw, `"r-1"` would never equal `r-1` and every pair would come back
    unlinked -- and a run with no pair is a STOP."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def trace_meta_ro(db: Path) -> dict:
    """One trace's whole meta table, JSON-decoded, read-only."""
    path = Path(db)
    if not path.is_file():
        return {}
    con = connect_ro(path)
    try:
        rows = dict(con.execute("select key, value from meta"))
    finally:
        con.close()
    return {k: meta_value(v) for k, v in rows.items()}


def pair_candidates(traces_dir, run_id: str, launched_at: float) -> dict:
    """§1.4's PAIR RULE **including R2's child filter**, applied by the
    instrument rather than trusted.

    A trace qualifies on three counts, all necessary: it names `run_id` in
    `refocus_of`, its own recording started at or after `launched_at`, and
    R2 has not set it aside as the child of another candidate. Deliberately
    NOT the CLI's own `find_pair`: this is the check that the CLI paired the
    two traces the STORE supports, so it reads the store itself -- and the
    child rule is re-applied here for the same reason, from the same pid /
    ppid facts (`refocus_rust.find_pair`).

    Every list is returned. "an earlier refocus of the same original", "no
    trace at all" and "a child was excluded" are three different findings.
    """
    linked, qualifying, unreadable = [], [], []
    for path in sorted(Path(traces_dir).glob("*.db")):
        try:
            con = connect_ro(path)
            try:
                rows = dict(con.execute(
                    "select key, value from meta where key in "
                    "('refocus_of', 'start_ts', 'pid', 'ppid')"))
            finally:
                con.close()
        except sqlite3.DatabaseError:
            unreadable.append(path.stem)
            continue
        of = meta_value(rows.get("refocus_of"))
        if of != run_id:
            continue
        linked.append(path.stem)
        started = meta_value(rows.get("start_ts"))
        if not isinstance(started, (int, float)) or started < launched_at:
            continue
        qualifying.append((path.stem, _pid(rows.get("pid")),
                           _pid(rows.get("ppid"))))
    # R2, from `refocus_rust.find_pair`: `pid is not None` keeps the
    # unidentified traces OUT of the set, so an unknown parent can never
    # match an unknown pid and a trace that records neither is a candidate.
    pids = {p for _n, p, _pp in qualifying if p is not None}
    candidates = [n for n, p, pp in qualifying
                  if not (pp in pids and pp != p)]
    children = [n for n, p, pp in qualifying if pp in pids and pp != p]
    return {"linked": sorted(linked), "qualifying": sorted(candidates),
            "children": sorted(children), "unreadable": unreadable,
            "n": len(candidates), "launched_at": launched_at}


def _pid(raw):
    value = meta_value(raw)
    return value if isinstance(value, int) else None


# ---------------------------------------------------------- H4's census

def shim_census(target: Path, driver: Path) -> dict:
    """H4: `<CARGO_TARGET_DIR>/sensorium/shim/*/cargo-sensorium`.

    Three numbers that are printed SEPARATELY and never summed into each
    other: how many entries there are, how many DISTINCT inodes they hold,
    and the bytes -- counted **once per inode**. Under R3 the shims are hard
    links to one file, so a byte total that summed the per-entry sizes would
    report 61 copies of a binary that exists once, which is the measurement
    error this endpoint is about.

    A directory that is not there is `None` entries, never 0: a target that
    never keyed a shim and one that keyed an empty shim are different facts.
    `st_dev` is recorded beside the inode comparison because a link across a
    filesystem boundary is impossible rather than wrong -- §1.2 says the
    finding branch does not apply where the devices differ.
    """
    shim = Path(target) / "sensorium" / "shim"
    drv = Path(driver)
    driver_stat = drv.stat() if drv.is_file() else None
    out = {
        "dir": str(shim), "exists": shim.is_dir(),
        "driver": str(drv),
        "driver_inode": driver_stat.st_ino if driver_stat else None,
        "driver_dev": driver_stat.st_dev if driver_stat else None,
        "driver_bytes": driver_stat.st_size if driver_stat else None,
        "keys": None, "entries": None, "distinct_inodes": None,
        "bytes_once_per_inode": None, "linked_to_the_driver": None,
        "not_linked": None, "same_device": None, "names": None,
        "keys_without_a_binary": None, "entries_cover_every_key": None,
    }
    if not shim.is_dir():
        return out
    keys = sorted(p.name for p in shim.iterdir() if p.is_dir())
    seen, linked, unlinked, devices, total = {}, [], [], set(), 0
    entries, empty = 0, []
    for key in keys:
        binary = shim / key / "cargo-sensorium"
        if not binary.is_file():
            # NAMED, never skipped into silence. A key directory with no
            # binary has no `st_ino`, so H4's gate -- "for every key" --
            # is not met; dropping it here would take it out of the
            # DENOMINATOR too and let `linked == entries` read as though
            # every key had linked. That is the failure `4edd5c7` makes
            # reachable: the install created the directory and could not
            # place the binary.
            empty.append(key)
            continue
        st = binary.stat()
        entries += 1
        devices.add(st.st_dev)
        if st.st_ino not in seen:
            seen[st.st_ino] = st.st_size
            total += st.st_size
        if driver_stat is not None and st.st_ino == driver_stat.st_ino:
            linked.append(key)
        else:
            unlinked.append(key)
    out.update({
        "keys": len(keys), "entries": entries,
        "keys_without_a_binary": empty,
        "entries_cover_every_key": entries == len(keys),
        "distinct_inodes": len(seen), "bytes_once_per_inode": total,
        "linked_to_the_driver": len(linked), "not_linked": sorted(unlinked),
        "same_device": (None if driver_stat is None or not devices
                        else devices == {driver_stat.st_dev}),
        "devices": sorted(devices), "names": keys,
    })
    return out


__all__ = ["VERDICT_EXIT", "PRE_RERUN_REFUSAL_EXIT", "RERUN_BANNER",
           "THREAD_RECORD_UNAVAILABLE",
           "UNVERIFIABLE_OUTPUT", "UNVERIFIABLE_CHILDREN",
           "bullets_after", "cargo_finished_seconds", "connect_ro",
           "licence_counts", "licence_partition", "meta_value",
           "read_e4pp_clauses", "rt_hash_of",
           "pair_candidates", "parse_refocus", "shim_census",
           "trace_meta_ro"]
