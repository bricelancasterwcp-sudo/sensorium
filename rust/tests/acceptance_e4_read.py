#!/usr/bin/env python3
"""The E4 instrument's READERS: the parsers over what `sensorium refocus`
and `sensorium watch` print, the sqlite reads over a converted trace, and the
re-derivation of §1.1's 61 names from the clone's own sources.

Split from the phases for the reason `acceptance_e9_read.py` is split from
`acceptance_e9_phases.py`: a parser tested against pasted output is a
different thing from a protocol that runs a command, and only the first can
be tested without the box. Every function here takes TEXT or a path and
returns facts; none of them runs anything, decides a verdict, or knows what
§1 predicted.

WHERE THE INPUT SHAPES COME FROM
--------------------------------
Not from prose. Every regex below is written against a line this repository
already pins somewhere a test can fail on:

* `corpus/rust/refocus_match/questions.yaml` -- the MATCH headline, the
  `refocus-of:` line, the granted licence sentence, the two `unverifiable`
  markers and the Rust blind-spot lines;
* `corpus/rust/refocus_diverged/questions.yaml` -- `verdict: DIVERGED at
  causal step 1` with its `common` / `A:` / `B:` rows;
* `corpus/rust/refocus_refused_many/questions.yaml` -- the pre-rerun refusal
  sentence and its exit 2;
* `src/sensorium/query/refocus_rust.py` and `refocus_cmd.py` -- the `run:`,
  `trace:`, `env:`, `exit:` and `threads:`/`tasks:` lines, which the corpus
  does not pin line for line;
* `src/sensorium/query/watch_cmd.py::_no_match` -- W3's class, which E9's
  four-class table does not contain.

No location is written into this file. `/tmp` reaches it only through
`acceptance_e9_read.temp_root`, from the OBSERVED `TMPDIR`.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from acceptance_e9_read import VERDICT_CLASSES as E9_VERDICT_CLASSES
from acceptance_e9_read import outcome_counts  # noqa: F401
from acceptance_e9_read import parse_watch as _parse_watch_e9
from acceptance_e9_read import temp_root  # noqa: F401
from acceptance_e9_read import test_results  # noqa: F401

# ------------------------------------------------------- `sensorium refocus`

#: `refocus_rust.run`: printed BEFORE the re-run, so it exists even on a run
#: whose driver child then failed. The `cmd:` half is the driver argv §2.3
#: composes, recorded whole rather than re-derived here.
REFOCUS_OF = re.compile(r"^refocus-of: (?P<run>\S+)\s+cmd: (?P<cmd>.*)$", re.M)
CWD_LINE = re.compile(r"^cwd: (?P<cwd>.*)$", re.M)
FOCUS_LINE = re.compile(r"^focus: (?P<focus>.*?)\s\s+window: (?P<window>.*)$",
                        re.M)

#: `refocus_world._source_state` / `_env_state` (the Rust env line is
#: `refocus_rust._env_of`'s, which appends the recorder's own uncompared
#: names). Three statuses each, and the third is `unverifiable` -- which is
#: never counted as verified anywhere in this record.
SOURCE_LINE = re.compile(r"^source: (?P<rest>.*)$", re.M)
ENV_LINE = re.compile(r"^env: (?P<rest>.*)$", re.M)
STATUSES = ("unchanged", "CHANGED", "unverifiable")

#: `refocus_rust._verify`, after the `--- verdict ---` banner.
NEW_RUN = re.compile(r"^run: (?P<run>\S+)$", re.M)
NEW_TRACE = re.compile(r"^trace: (?P<path>.*)$", re.M)
EXIT_LINE = re.compile(r"^exit: rerun (?P<rerun>\S+)\s+original "
                       r"(?P<original>\S+)\s*$", re.M)
DRIVER_REPORTED = re.compile(r"^driver reported: (?P<line>run: .*)$", re.M)

#: `refocus_cmd.report`: the one headline, in its three verdict words.
REFOCUS_VERDICT = re.compile(r"^refocus verdict: (?P<word>MATCH|DIVERGED|"
                             r"REFUSED)\b(?P<rest>.*)$", re.M)

#: `refocus_cmd.report`'s licence, in its two shapes.
LICENCE_GRANTED = re.compile(r"^licence: verified against (?P<run>\S+) on "
                             r"exactly these points, and no others:$", re.M)
LICENCE_WITHHELD = re.compile(r"^licence: WITHHELD\b(?P<rest>.*)$", re.M)

#: `refocus_rust._print_unverifiable`, and the two markers it lists
#: (`refocus_world.UNVERIFIABLE`). An UNVERIFIABLE check is REPORTED and is
#: never counted as verified in any total -- §1's H4 rule, enforced by
#: keeping the two lists apart from the first read onwards.
UNVERIFIABLE_HEADER = re.compile(
    r"^checks that could not run on this pair\b.*$", re.M)
UNVERIFIABLE_OUTPUT = "output: unverifiable (not recorded)"
UNVERIFIABLE_CHILDREN = "children: unverifiable (not witnessed)"

#: `refocus_cmd._refuse`, on STDERR, exit 2: nothing was re-run. The design
#: §2.3 sentence is everything after the colon.
PRE_RERUN_REFUSAL = re.compile(
    r"^error: cannot refocus (?P<run>\S+): (?P<sentence>.*)$", re.M)

#: `refocus_rust._refused_after_rerun`: exit 3, the STOP class of §1's kill 2.
#: Told apart from the pre-rerun refusal by the sentence that carries it --
#: the driver DID run.
REFUSED_AFTER = re.compile(r"^refocus verdict: REFUSED -- (?P<why>.*)$", re.M)

#: `diff_cmd._print_divergence`, pinned by `corpus/rust/refocus_diverged`.
#: `desc` renders one causal step as `e<id> <KIND padded> <qualname>
#: (<file>)`, and the three row labels are `common`, `A:` and `B:`.
DIVERGED_STEP = re.compile(r"^verdict: DIVERGED at causal step (?P<i>\d+)$",
                           re.M)
STEP_ROW = re.compile(r"^\s{2}(?P<side>common|A:|B:)\s+e(?P<event>\d+) "
                      r"(?P<kind>[A-Z]+)\s+(?P<qualname>\S+)\s+"
                      r"\((?P<file>[^)]*)\)(?P<tail>.*)$", re.M)
#: `diff_cmd._print_match`, printed above the refocus headline on a MATCH.
DIFF_VERDICT = re.compile(r"^verdict: MATCH(?P<modulo> modulo location)? -- "
                          r"identical causal streams \((?P<events>\d+) "
                          r"events?\)", re.M)
THREADS_LINE = re.compile(r"^threads: (?P<rest>.*)$", re.M)
TASKS_LINE = re.compile(r"^tasks: (?P<rest>.*)$", re.M)

#: cargo's own reported build time, inside the driver child's stderr. Two
#: spellings: `in 12.34s` and `in 1m 02s`. H6's second reading.
CARGO_FINISHED = re.compile(
    r"^\s*Finished .*? in (?:(?P<min>\d+)m )?(?P<secs>[0-9.]+)s\s*$", re.M)


def _status_of(rest: str | None) -> str | None:
    """Which of `unchanged` / `CHANGED` / `unverifiable` a status line is.

    `None` for a line that is none of them, never a guess: a fourth spelling
    is a change in the command, and reading it as one of these three is how
    a check that did not run gets counted as one that passed.
    """
    if rest is None:
        return None
    for status in STATUSES:
        if rest.startswith(status):
            return status
    return None


def bullets_after(text: str, header: str) -> list[str]:
    """The contiguous `  - ` bullets directly under `header`.

    Contiguity is what keeps the three bullet blocks of one answer apart:
    the licence's facts, the blind-spot block's lines and the unverifiable
    markers all print as `  - `, and a scan that took every bullet in the
    text would fold the recorder's categorical blind spots into the licence
    the record then counts.
    """
    lines = text.splitlines()
    try:
        start = lines.index(header)
    except ValueError:
        return []
    out = []
    for line in lines[start + 1:]:
        if not line.startswith("  - "):
            break
        out.append(line[4:].strip())
    return out


def parse_refocus(text: str) -> dict:
    """One `sensorium refocus <run> --focus <name>` answer, whole.

    Decides nothing. The verdict WORD and the exit status are read
    separately and are never derived from each other -- §1's H3 makes a
    disagreement between them a finding -- and the licence's verified list
    and its unverifiable list are two fields that are never summed.
    """
    out: dict = {
        "refocus_of": None, "driver_cmd": None, "cwd": None,
        "focus": None, "window": None,
        "source_line": None, "source_status": None,
        "env_line": None, "env_status": None,
        "exit_line": None, "exit_rerun": None, "exit_original": None,
        "exit_status_equal": None,
        "new_run": None, "new_trace": None, "driver_run_lines": [],
        "verdict_word": None, "verdict_line": None,
        "diff_verdict_line": None, "diff_events": None,
        "threads_line": None, "tasks_line": None,
        "licence": None, "licence_line": None, "licence_facts": [],
        "licence_caveats": [],
        "unverifiable": [], "unverifiable_header": None,
        "pre_rerun_refusal": None, "pre_rerun_refusal_run": None,
        "refused_after_rerun": None,
        "diverged_step": None, "step_rows": [],
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
    m = EXIT_LINE.search(text)
    if m:
        out["exit_line"] = m.group(0).strip()
        out["exit_rerun"] = m.group("rerun")
        out["exit_original"] = m.group("original")
        # The pair's own reading of "the two runs ended the same way". A
        # licence caveat says so too; this is the printed evidence beside
        # it, so a disagreement between the two is visible.
        out["exit_status_equal"] = m.group("rerun") == m.group("original")
    m = NEW_RUN.search(text)
    if m:
        out["new_run"] = m.group("run")
    m = NEW_TRACE.search(text)
    if m:
        out["new_trace"] = m.group("path").strip()
    out["driver_run_lines"] = [m.group("line")
                               for m in DRIVER_REPORTED.finditer(text)]
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
    out["step_rows"] = [{"side": r.group("side").rstrip(":"),
                         "event": int(r.group("event")),
                         "kind": r.group("kind"),
                         "qualname": r.group("qualname"),
                         "file": r.group("file"),
                         "text": r.group(0).strip()}
                        for r in STEP_ROW.finditer(text)]
    return out


def licence_counts(parsed: dict) -> dict:
    """H4's four numbers for ONE pair, kept apart from each other.

    `source`, `env` and `exit` are checks that RAN: each is verified, not
    verified, or could not run. `output` and `children` are UNVERIFIABLE by
    construction on a Rust pair and are counted in their own field -- never
    added to a verified total, which is the rule §1.4 binds this record to.
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
    """Every `Finished ... in <n>s` cargo printed, in seconds.

    A list, not a number: a re-run can rebuild more than one profile, and a
    reading that took the first would report one of them as the whole build.
    Both spellings are read -- `12.34s` and `1m 02s` -- because a build long
    enough for the minute form is exactly the one H6 is reporting on.
    """
    out = []
    for m in CARGO_FINISHED.finditer(text):
        secs = float(m.group("secs"))
        if m.group("min"):
            secs += 60.0 * int(m.group("min"))
        out.append(round(secs, 3))
    return out


# ----------------------------------------------------------------- `watch`

#: W3's class, which E9's four-class table has no row for: `watch` takes its
#: `_no_match` branch when no recorded code object matches `--at`, prints
#: this line and returns NEGATIVE (1). E9's W3 ran against a whole-file
#: trace where the frame existed; here the trace is a single `--exact` test
#: binary, so the class necessarily differs and the exit is the gate.
NO_MATCH = re.compile(r"^error: no recorded code matches --at (?P<at>.*)$",
                      re.M)
RECORDED_CODES = re.compile(r"^this trace recorded (?P<n>\d+) code object",
                            re.M)

#: E9's four, plus the fifth. Extended rather than re-spelled so a change to
#: a shared class is made once.
E4_VERDICT_CLASSES = E9_VERDICT_CLASSES + (
    ("no recorded code matches", NO_MATCH),)


def parse_watch(text: str) -> dict:
    """E9's `watch` reader, widened by the one class W3 needs.

    The bucket counts, the verdict line and the refusal line are E9's
    unchanged; the CLASS is recomputed over the five-row table, and the rule
    is E9's own: exactly one class may match, and a text carrying two is a
    defect in the command rather than a reading to be resolved by taking the
    first.
    """
    out = _parse_watch_e9(text)
    classes = [name for name, pat in E4_VERDICT_CLASSES if pat.search(text)]
    out["classes"] = classes
    out["verdict_class"] = classes[0] if len(classes) == 1 else None
    m = NO_MATCH.search(text)
    out["no_match_line"] = m.group(0).strip() if m else None
    m = RECORDED_CODES.search(text)
    out["recorded_code_objects"] = int(m.group("n")) if m else None
    return out


# ---------------------------------------------------------------- the trace


def _connect(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db)}?mode=ro", uri=True)


#: The thread serial the Rust converter reserves for the MAIN stream
#: (`rust/cargo-sensorium/src/convert/frames.rs:23`). Every other thread's
#: causal events are written as a TASK: `task_id = (thread_id !=
#: MAIN_SERIAL).then_some(thread_id)` (`frames.rs:161`), and the per-thread
#: `fingerprints` table therefore holds exactly one row, the main one.
MAIN_SERIAL = 1


def fingerprint_tables(db: Path) -> dict:
    """One trace's `fingerprints` and `task_fingerprints`, as facts.

    Both tables, never one: on a Rust trace the MAIN stream is the single
    `fingerprints` row and every spawned thread is a `task_fingerprints`
    row, so a reading that took only the first would be blind to exactly the
    four worker threads §1.2's hazard is about.
    """
    con = _connect(db)
    try:
        threads = [{"thread_id": tid, "hash": h, "n_events": n}
                   for tid, h, n in con.execute(
                       "select thread_id, hash, n_events from fingerprints "
                       "order by thread_id")]
        tasks = [{"task_id": tid, "name": name, "hash": h, "n_events": n}
                 for tid, name, h, n in con.execute(
                     "select task_id, name, hash, n_events from "
                     "task_fingerprints order by task_id")]
    finally:
        con.close()
    main = next((t for t in threads if t["thread_id"] == MAIN_SERIAL), None)
    return {
        "threads": threads,
        "tasks": tasks,
        "main_thread_id": MAIN_SERIAL,
        "main": main,
        "main_hash": (main or {}).get("hash"),
        "main_events": (main or {}).get("n_events"),
        "task_count": len(tasks),
        "task_events_total": sum(t["n_events"] for t in tasks),
        # What `diff_cmd.compare_tasks` actually compares: the multiset of
        # (name, hash). Sorted so two runs' lists are comparable as values.
        "task_shapes": sorted((t["name"], t["hash"]) for t in tasks),
        # The PARTITION -- how the shared work split between the workers.
        # §1.2's hazard is a different partition of the same total.
        "task_partition": sorted(t["n_events"] for t in tasks),
    }


#: §1.2's three server tests, and §1.4's amendment (R-H1) reading of a
#: DIVERGED on one of them. Named here so the discriminator cannot be
#: applied to a test §1 did not pre-register it for.
HAZARD_TESTS = (
    "the_refusal_advises_a_window_that_actually_places",
    "the_advice_never_exceeds_the_window_the_agent_already_had",
    "the_journal_records_the_advice_alongside_the_refusal_arithmetic",
)

#: `serve_fake`'s `WORKER_COUNT` (`crates/bloomery-daemon/src/http.rs:35`),
#: as §1.2 records it. Used only to REPORT whether the premise of §1.4's
#: phrase ("the four worker tasks") held, never to decide the class.
WORKER_COUNT = 4


def discriminate(orig_db: Path, new_db: Path, name: str) -> dict:
    """§1.4's amendment (2), computed: is this DIVERGED the named hazard?

    The amendment's two conditions, and only those two:

    1. **the total causal event count over the four worker tasks is the
       same in both traces** -- a scheduler that split the same ten requests
       differently moves work BETWEEN the workers and changes neither the
       total nor the main stream;
    2. **the MAIN stream's fingerprint MATCHes** -- the test body itself
       took the same path.

    Both hold: the scheduler nondeterminism §1.2 pre-registers, a MISS the
    section already accounts for. Either fails: H3's finding, like any other
    DIVERGED, with no prior explanation available to it.

    Applied ONLY to the three tests §1.2 names. Every other test's DIVERGED
    is the finding H3 means and this function is not asked about it.

    Where §1 is silent: it does not say what to do when a trace holds a
    number of task streams other than four. The premise of its phrase is
    reported (`four_worker_tasks`, `task_count_equal`) beside the class
    rather than folded into it, so a reader can see that the sentence's
    subject held -- and a class computed over a premise that did not is
    published with that fact attached rather than silently.
    """
    a, b = fingerprint_tables(orig_db), fingerprint_tables(new_db)
    total_preserved = a["task_events_total"] == b["task_events_total"]
    main_matches = (a["main_hash"] is not None
                    and a["main_hash"] == b["main_hash"])
    counts_equal = a["task_count"] == b["task_count"]
    four = a["task_count"] == b["task_count"] == WORKER_COUNT
    hazard = bool(total_preserved and main_matches)
    caveats = []
    if not four:
        caveats.append(
            f"§1.4's phrase names FOUR worker tasks; this pair recorded "
            f"{a['task_count']} task stream(s) in the original and "
            f"{b['task_count']} in the re-run (`WORKER_COUNT` is "
            f"{WORKER_COUNT})")
    return {
        "test": name,
        "is_a_pre_registered_hazard_test": name in HAZARD_TESTS,
        "original": a, "new": b,
        "task_events_total_original": a["task_events_total"],
        "task_events_total_new": b["task_events_total"],
        "total_causal_events_preserved": total_preserved,
        "main_fingerprint_original": a["main_hash"],
        "main_fingerprint_new": b["main_hash"],
        "main_fingerprint_matches": main_matches,
        "task_count_original": a["task_count"],
        "task_count_new": b["task_count"],
        "task_count_equal": counts_equal,
        "four_worker_tasks": four,
        "partition_original": a["task_partition"],
        "partition_new": b["task_partition"],
        "task_shapes_equal": a["task_shapes"] == b["task_shapes"],
        "class": "hazard" if hazard else "finding",
        "reading": (
            "§1.2's named scheduler hazard: the same total causal work over "
            "the worker tasks, split differently, with the MAIN stream "
            "identical"
            if hazard else
            "H3's finding: §1.4's discriminator does not hold, so this "
            "DIVERGED reads as any other would"),
        "classification_caveats": caveats,
    }


# ------------------------------------------------- the clone's own sources

#: `#[test]` and the two attributes §1.1 asserts are absent. Matched on the
#: STRIPPED line so an indented attribute is still seen -- §1.1's claim is
#: that there are none anywhere in the seven files, not that there are none
#: at column 0.
ATTR = re.compile(r"^\s*#\[")
TEST_ATTR = re.compile(r"^\s*#\[test\]\s*$")
IGNORE_ATTR = re.compile(r"^\s*#\[ignore")
SHOULD_PANIC_ATTR = re.compile(r"^\s*#\[should_panic")
#: §1's `--focus` value is the BARE qualname, which `visit.rs::qualname`
#: returns for an item at empty scope -- a `fn` at column 0.
FN_AT_COLUMN_0 = re.compile(r"^fn ([A-Za-z0-9_]+)")


def enumerate_tests_in(path: Path) -> dict:
    """Every `#[test]` fn of one file, with the line §1.1 records.

    §1.1's line is the `fn`'s own line, one-based, and its name is the bare
    item name. An attribute block that does not end in a column-0 `fn` is
    recorded under `unmatched` rather than skipped: a test the derivation
    cannot see is a difference from §1.1, and a silent skip would make the
    two agree by both being blind.
    """
    text = path.read_text()
    lines = text.splitlines()
    rows, unmatched = [], []
    for i, line in enumerate(lines):
        if not TEST_ATTR.match(line):
            continue
        j, attrs = i + 1, ["#[test]"]
        while j < len(lines) and ATTR.match(lines[j]):
            attrs.append(lines[j].strip())
            j += 1
        m = FN_AT_COLUMN_0.match(lines[j]) if j < len(lines) else None
        if not m:
            unmatched.append({"attr_line": i + 1,
                              "next": lines[j] if j < len(lines) else None})
            continue
        rows.append({"line": j + 1, "name": m.group(1), "attrs": attrs})
    return {
        "file": path.name,
        "tests": rows,
        "count": len(rows),
        "unmatched": unmatched,
        "ignore_attrs": sum(1 for ln in lines if IGNORE_ATTR.match(ln)),
        "should_panic_attrs": sum(1 for ln in lines
                                  if SHOULD_PANIC_ATTR.match(ln)),
    }


def enumerate_tests(tests_dir: Path, targets) -> dict:
    """§1.1's table, re-derived from the clone, file by file and in order.

    The comparison against §1.1 is the caller's; this only reads. A file
    that is not there is recorded as missing rather than counted as empty --
    zero tests in a file that exists and zero tests in a file that does not
    are different facts about the clone.
    """
    per_file, rows, missing = {}, [], []
    for target in targets:
        path = Path(tests_dir) / f"{target}.rs"
        if not path.is_file():
            missing.append(str(path))
            per_file[target] = {"missing": str(path)}
            continue
        rec = enumerate_tests_in(path)
        per_file[target] = rec
        rows += [(target, t["line"], t["name"]) for t in rec["tests"]]
    return {
        "tests_dir": str(tests_dir),
        "per_file": per_file,
        "rows": rows,
        "names": [name for _t, _ln, name in rows],
        "total": len(rows),
        "missing_files": missing,
        "counts": {t: (r.get("count") if "missing" not in r else None)
                   for t, r in per_file.items()},
        "ignore_attrs": sum((r.get("ignore_attrs") or 0)
                            for r in per_file.values()),
        "should_panic_attrs": sum((r.get("should_panic_attrs") or 0)
                                  for r in per_file.values()),
        "unmatched": {t: r.get("unmatched") for t, r in per_file.items()
                      if r.get("unmatched")},
    }


def table_diff(derived, expected) -> dict:
    """§1.1's table against the clone's, as NAMED differences.

    Order matters and is compared: §1's pass-1 order is §1.1's order, and a
    table that agreed as a set but not as a sequence would run the 61 in a
    different order than the one pre-registered.
    """
    d, e = list(derived), list(expected)
    ds, es = {(f, ln, n) for f, ln, n in d}, {(f, ln, n) for f, ln, n in e}
    by_name_d = {n: (f, ln) for f, ln, n in d}
    by_name_e = {n: (f, ln) for f, ln, n in e}
    return {
        "equal": d == e,
        "same_set": ds == es,
        "same_order": [n for _f, _l, n in d] == [n for _f, _l, n in e],
        "only_in_the_clone": sorted(f"{f}:{ln} {n}" for f, ln, n in ds - es),
        "only_in_the_document": sorted(f"{f}:{ln} {n}"
                                       for f, ln, n in es - ds),
        "line_moved": sorted(
            f"{n}: clone {by_name_d[n]} vs §1.1 {by_name_e[n]}"
            for n in set(by_name_d) & set(by_name_e)
            if by_name_d[n] != by_name_e[n]),
        "derived_total": len(d), "expected_total": len(e),
    }


# ------------------------------------------------------------ the shim census


def shim_census(target: Path) -> dict:
    """H6's census of `<CARGO_TARGET_DIR>/sensorium/shim/*`.

    Entries and total bytes, measured once at the end
    (`rust/cargo-sensorium/src/rt_build.rs:207-211`). A directory that is not
    there is `None` entries, never 0: a target the run never keyed a shim
    into and a target that keyed one and left it empty are different facts.
    """
    shim = Path(target) / "sensorium" / "shim"
    if not shim.is_dir():
        return {"dir": str(shim), "exists": False, "entries": None,
                "bytes": None, "names": None}
    names = sorted(p.name for p in shim.iterdir())
    total = sum(f.stat().st_size for f in shim.rglob("*") if f.is_file())
    return {"dir": str(shim), "exists": True, "entries": len(names),
            "bytes": total, "names": names}


# ------------------------------------------------------------- the pair rule

#: `refocus_rust.run` prints this immediately BEFORE `_launch`, so its
#: presence is the instrument's own evidence that the driver child was
#: launched -- H1's second reading, which the CLI's exit alone cannot give.
RERUN_BANNER = ("--- rerunning (the driver's build output is above and "
                "below; the lines below are its own) ---")
#: `refocus_rust._refused_after_rerun` names the child's exit inside the
#: sentence; H2's build-failure reading reads it from there.
DRIVER_EXIT = re.compile(r"driver exit (?P<rc>-?\d+)")


def _meta_value(raw):
    """One `meta` cell, decoded the way the store encodes it.

    `store.db.set_meta` writes `json.dumps(value)` and the Rust converter
    writes a `serde_json::Value`, so a run id sits in the column as a QUOTED
    string. Read raw, `"r-1"` would never equal `r-1` and every pair would
    come back unlinked -- and a run refused for having no pair is a STOP.
    """
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def pair_candidates(traces_dir, run_id: str, launched_at: float) -> dict:
    """§1.4's PAIR RULE, applied by the instrument rather than trusted.

    A trace qualifies on two counts and both are necessary: it names
    `run_id` in `refocus_of` (the driver stamped it) and its own recording
    started at or after `launched_at`. Zero or more than one is a REFUSED by
    count, never a guess -- and per H3 a REFUSED after the rerun is a STOP.

    Deliberately NOT the CLI's own `find_pair`: this is the check that the
    CLI paired the two traces the store supports, so it reads the store
    itself. Both lists are returned -- the qualifying ids and every trace
    linked to `run_id` whatever its timestamp -- because "an earlier refocus
    of the same original" and "no trace at all" are different findings.
    """
    linked, qualifying, unreadable = [], [], []
    for path in sorted(Path(traces_dir).glob("*.db")):
        try:
            con = _connect(path)
            try:
                rows = dict(con.execute(
                    "select key, value from meta where key in "
                    "('refocus_of', 'start_ts')"))
            finally:
                con.close()
        except sqlite3.DatabaseError:
            unreadable.append(path.stem)
            continue
        of = _meta_value(rows.get("refocus_of"))
        if of is None:
            continue
        if of != run_id:
            continue
        linked.append(path.stem)
        started = _meta_value(rows.get("start_ts"))
        started = started if isinstance(started, (int, float)) else None
        if started is not None and started >= launched_at:
            qualifying.append(path.stem)
    return {"linked": sorted(linked), "qualifying": sorted(qualifying),
            "unreadable": unreadable, "n": len(qualifying),
            "launched_at": launched_at}
