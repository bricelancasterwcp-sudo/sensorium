#!/usr/bin/env python3
"""The E9 instrument's READERS: the parsers over what the driver and the
query CLI print, and the sqlite joins over a converted trace.

Split from the phases for the reason `acceptance_grain_read.py` is split from
`acceptance_grain_phases.py`: a parser tested against pasted output is a
different thing from a protocol that runs a command, and only the first can
be tested without the box. Every function here takes TEXT or a `.db` path and
returns facts; none of them runs anything, decides a verdict, or knows what
§1 predicted.

No location is written into this file. The two path-shaped constants below
(`/tmp`) are not a box location: `std::env::temp_dir()` returns `/tmp` when
`TMPDIR` is unset, which is what §1.4's W1/W3/S1/S2 derivations rest on, and
`temp_root` takes the OBSERVED `TMPDIR` so a run under a set `TMPDIR` reads
the same predictions with the prefix substituted rather than the wrong ones.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# --------------------------------------------------------------- the driver

#: `cargo-sensorium` prints one of these per matched qualname, on stderr,
#: BEFORE cargo is invoked (`driver.rs`: `eprintln!("focus: {qualname}")`).
#: This is H2's resolution evidence.
FOCUS_LINE = re.compile(r"^focus: (.+)$", re.M)

#: libtest's own summary, from which H2 takes the outcome counts and H6 its
#: first reading of the wall (libtest's `finished in`).
TEST_RESULT = re.compile(
    r"^test result: (?P<verdict>\w+)\. (?P<passed>\d+) passed; "
    r"(?P<failed>\d+) failed; (?P<ignored>\d+) ignored; "
    r"(?P<measured>\d+) measured; (?P<filtered>\d+) filtered out"
    r"(?:; finished in (?P<secs>[0-9.]+)s)?", re.M)

#: The driver's refusal of a focus that names nothing / only skipped items.
FOCUS_REFUSAL = re.compile(r"^REFUSED: --focus .*$", re.M)


def focus_lines(text: str) -> list[str]:
    """Every qualname the driver said the focus matched, in printed order."""
    return [m.strip() for m in FOCUS_LINE.findall(text)]


def test_results(text: str) -> list[dict]:
    """Every libtest summary in `text`, parsed.

    A list, not a single row: `cargo test` prints one per test target, and a
    comparison that silently took the first would compare U1's binary against
    F1's doc-tests if cargo ever added one.
    """
    out = []
    for m in TEST_RESULT.finditer(text):
        d = m.groupdict()
        out.append({"verdict": d["verdict"],
                    "passed": int(d["passed"]), "failed": int(d["failed"]),
                    "ignored": int(d["ignored"]),
                    "measured": int(d["measured"]),
                    "filtered_out": int(d["filtered"]),
                    "libtest_secs": (float(d["secs"]) if d["secs"] is not None
                                     else None),
                    "line": m.group(0)})
    return out


def outcome_counts(rows: list[dict]) -> dict | None:
    """The pass/fail/ignored triple a focused run is compared against.

    Summed over every target, so a run that grew a target differs from one
    that did not instead of matching on the first line they share. `None`
    when nothing was parsed -- which is not a zero outcome, and the caller
    must publish it as not-measured rather than as `0 passed`.
    """
    if not rows:
        return None
    keys = ("passed", "failed", "ignored", "measured", "filtered_out")
    return {"targets": len(rows), **{k: sum(r[k] for r in rows) for k in keys},
            "verdicts": [r["verdict"] for r in rows]}


# ------------------------------------------------------------------ `info`

INFO_RECORDER = re.compile(r"^recorder: (?P<rec>.+?)\s\s+lang: (?P<lang>\S+)\s\s+"
                           r"capabilities: (?P<caps>.*)$", re.M)
INFO_RECORDED = re.compile(r"^recorded: (.*)$", re.M)
INFO_FOCUS = re.compile(r"^focus: (?P<focus>.*?)\s\s+window: (?P<window>.*)$",
                        re.M)


def parse_info(text: str) -> dict:
    """`sensorium info <run>`'s recorder, capability and focus rows.

    The capability dict is parsed from the printed `k=yes|no` pairs -- the
    row a reader of the record would look at. It is NOT the gate: H1 reads
    `capabilities` from the trace's own `meta`, and this is the printed
    evidence beside it, so a divergence between the two is visible.
    """
    out: dict = {"recorder": None, "lang": None, "capabilities": {},
                 "capabilities_text": None, "recorded": {}, "focus": None,
                 "window": None}
    m = INFO_RECORDER.search(text)
    if m:
        out["recorder"] = m.group("rec").strip()
        out["lang"] = m.group("lang")
        out["capabilities_text"] = m.group("caps").strip()
        for pair in m.group("caps").split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                out["capabilities"][k] = {"yes": True, "no": False}.get(v, v)
    m = INFO_RECORDED.search(text)
    if m:
        parts = m.group(1).split()
        out["recorded"] = {parts[i]: int(parts[i + 1])
                           for i in range(0, len(parts) - 1, 2)
                           if parts[i + 1].isdigit()}
    m = INFO_FOCUS.search(text)
    if m:
        focus = m.group("focus").strip()
        out["focus"] = ([] if focus == "-"
                        else [f.strip() for f in focus.split(",")])
        out["window"] = m.group("window").strip()
    return out


# ----------------------------------------------------------------- `watch`

#: The four things `watch` can say, and the class each one is. Matched on the
#: sentence's OPENING, never on the whole line: the counts inside it move
#: with the trace, and a class read from the counts would be no class at all.
#: `REFUSED` is not one of `Says` -- it is the capability refusal H1 predicts,
#: which `watch` prints before it evaluates anything.
VERDICT_CLASSES = (
    ("REFUSED", re.compile(r"^REFUSED: ", re.M)),
    ("SATISFIED", re.compile(r"^verdict: SATISFIED\b", re.M)),
    ("NOTHING WAS CHECKED", re.compile(r"^verdict: NOTHING WAS CHECKED\b",
                                       re.M)),
    ("not satisfied", re.compile(r"^verdict: not satisfied\b", re.M)),
)

SATISFIED_AT = re.compile(
    r"^verdict: SATISFIED at (?P<hits>\d+) of the (?P<evaluated>\d+) site", re.M)
NOTHING_AT = re.compile(
    r"^verdict: NOTHING WAS CHECKED -- the predicate could not be evaluated "
    r"at any of the (?P<sites>\d+) recorded site", re.M)
NOT_SATISFIED_AT = re.compile(
    r"^verdict: not satisfied at any of the (?P<n>\d+) (?:recorded )?site", re.M)


def parse_watch(text: str) -> dict:
    """The verdict CLASS `watch` printed, and the numbers beside it.

    Exactly one class may match: a text carrying two verdict sentences is a
    defect in the command, not a reading to be resolved by taking the first,
    so `classes` carries them all and `verdict_class` is `None` unless
    exactly one fired. §1's H4 compares the class and the exit status
    separately and reports a disagreement as a finding, so neither is
    derived from the other here.
    """
    classes = [name for name, pat in VERDICT_CLASSES if pat.search(text)]
    out: dict = {"classes": classes,
                 "verdict_class": classes[0] if len(classes) == 1 else None,
                 "hits": None, "evaluated": None, "sites": None,
                 "verdict_line": None, "refusal_line": None,
                 "hit_rows": [ln.strip() for ln in text.splitlines()
                              if ln.strip().startswith("HIT ")]}
    for line in text.splitlines():
        if line.startswith("verdict: ") and out["verdict_line"] is None:
            out["verdict_line"] = line.strip()
        if line.startswith("REFUSED: ") and out["refusal_line"] is None:
            out["refusal_line"] = line.strip()
    m = SATISFIED_AT.search(text)
    if m:
        out["hits"] = int(m.group("hits"))
        out["evaluated"] = int(m.group("evaluated"))
    m = NOTHING_AT.search(text)
    if m:
        out["sites"] = int(m.group("sites"))
        out["evaluated"] = 0
    m = NOT_SATISFIED_AT.search(text)
    if m:
        out["hits"] = 0
        out["sites"] = int(m.group("n"))
    return out


def refusal_sentence(recorder: str, cap: str = "line",
                     command: str = "watch") -> str:
    """H1's pinned refusal, with §2's OBSERVED recorder token substituted.

    `src/sensorium/query/caps.py::require` builds this sentence and prints it
    behind `REFUSED: `. §1 pins the sentence and reads the version token from
    `trace.recorder` rather than from an expectation, so the token is a
    PARAMETER here: a runner that spelled `0.4.0` into the gate would be
    checking the design's plan for the version, not the trace's claim.
    """
    return (f"REFUSED: {command} needs {cap}, which recorder {recorder} "
            f"declares it does not produce (capabilities.{cap}: false); "
            f"nothing was checked")


# ------------------------------------------------------------------ `flow`

SIGHTINGS = re.compile(r"^sightings: (?P<events>\d+) event\(s\), "
                       r"(?P<captures>\d+) capture\(s\)", re.M)
SCOPE = re.compile(r"^scope: (?P<captures>\d+) capture\(s\) searched across "
                   r"(?P<events>\d+) event\(s\)", re.M)

#: `fmt.fmt_event`: `e<id> <KIND padded to 7> <qualname> L<line><tail>`, and
#: `flow` prints it indented with its labels in trailing brackets.
EVENT_ROW = re.compile(
    r"^\s*e(?P<event>\d+) (?P<kind>[A-Z]+)\s+(?P<body>.*?)"
    r"(?:\s+\[(?P<labels>[^\]]*)\])?\s*$")
BODY_AT_LINE = re.compile(r"^(?P<qualname>\S+) L(?P<line>\d+)(?P<tail>.*)$")


def parse_event_row(line: str) -> dict | None:
    """One printed event row -> its event id, kind, qualname, line, labels.

    Returns `None` for a line that is not an event row, so a caller can walk
    a whole answer without deciding in advance which lines are rows.
    """
    m = EVENT_ROW.match(line)
    if not m:
        return None
    body = m.group("body").strip()
    row = {"event": int(m.group("event")), "kind": m.group("kind"),
           "body": body, "qualname": None, "line": None, "tail": "",
           "labels": [s.strip() for s in (m.group("labels") or "").split(",")
                      if s.strip()], "text": line.strip()}
    at = BODY_AT_LINE.match(body)
    if at:
        row["qualname"] = at.group("qualname")
        row["line"] = int(at.group("line"))
        row["tail"] = at.group("tail").strip()
    elif " -> " in body:                       # a RETURN: `<qualname> -> <v>`
        row["qualname"] = body.split(" -> ", 1)[0].strip()
    elif "(" in body:                          # a CALL: `<qualname>(<args>)`
        row["qualname"] = body.split("(", 1)[0].strip()
    return row


def parse_flow(text: str) -> dict:
    """`flow <run> --value <literal>`: the totals, and every sighting row."""
    rows = [r for r in (parse_event_row(ln) for ln in text.splitlines())
            if r]
    s, sc = SIGHTINGS.search(text), SCOPE.search(text)
    return {
        "sighting_events": int(s.group("events")) if s else None,
        "sighting_captures": int(s.group("captures")) if s else None,
        "scope_captures": int(sc.group("captures")) if sc else None,
        "scope_events": int(sc.group("events")) if sc else None,
        "sightings_line": s.group(0) if s else None,
        "scope_line": sc.group(0) if sc else None,
        "rows": rows,
    }


def line_deltas_of(rows: list[dict], qualname: str) -> list[dict]:
    """H5's FIRST reading: the sighting rows that are LINE deltas of one
    focus value. The second reading is `rows` itself -- every sighting
    anywhere in the trace, which §1 reports beside the gate because the
    unfocused helpers are still instrumented at the call tier."""
    return [r for r in rows
            if r["kind"] == "LINE" and r["qualname"] == qualname]


# ---------------------------------------------------------------- the trace


def temp_root(tmpdir: str | None) -> str:
    """What `std::env::temp_dir()` returns, from the OBSERVED `TMPDIR`.

    §1.4 expects `TMPDIR` unset, which makes it `/tmp` and makes W1, W3, S1
    and S2 derivable; if it is set at measurement time the same predictions
    read against `<TMPDIR>/…`. That substitution happens HERE, once, so no
    literal is spelled twice and the record can say which reading was taken.
    """
    if not tmpdir:
        return "/tmp"
    return tmpdir.rstrip("/") or "/"


def _connect(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(db)}?mode=ro", uri=True)


def line_rows_total(db: Path) -> int:
    """H1's `select count(*) from events where kind='LINE'` over the WHOLE
    trace -- the count that must be 0 on an unfocused run."""
    con = _connect(db)
    try:
        return con.execute(
            "select count(*) from events where kind = 'LINE'").fetchone()[0]
    finally:
        con.close()


def line_qualnames(db: Path) -> dict:
    """Every qualname carrying LINE rows, with its row count.

    H2's SECOND reading of "resolved to that one": the set of distinct
    qualnames with LINE rows must be exactly the focus value's.
    """
    con = _connect(db)
    try:
        rows = con.execute(
            "select c.qualname, count(*) from events e "
            "join code_objects c on c.id = e.code_id "
            "where e.kind = 'LINE' group by c.qualname").fetchall()
    finally:
        con.close()
    return {q: n for q, n in rows}


def line_histogram(db: Path, qualname: str) -> dict:
    """H3: the LINE rows of the activations of one focus value.

    Two joins, both recorded. The FRAME join is §1's ("the LINE rows of the
    single activation"): the rows of the frames whose code object is the
    focus value. The CODE join is the same rows counted by the event's own
    `code_id`. They must agree; a disagreement means a LINE row was
    attributed to a frame that is not its code object's, which is a finding
    about the recorder and not a number to pick between.
    """
    con = _connect(db)
    try:
        codes = [r[0] for r in con.execute(
            "select id from code_objects where qualname = ?",
            (qualname,)).fetchall()]
        frames = [r[0] for r in con.execute(
            "select f.id from frames f join code_objects c "
            "on c.id = f.code_id where c.qualname = ? order by f.id",
            (qualname,)).fetchall()]
        by_frame: dict = {}
        for fid in frames:
            rows = con.execute(
                "select line, count(*) from events where kind = 'LINE' "
                "and frame_id = ? group by line order by line",
                (fid,)).fetchall()
            by_frame[fid] = {int(ln): int(n) for ln, n in rows}
        code_rows = con.execute(
            "select e.line, count(*) from events e join code_objects c "
            "on c.id = e.code_id where e.kind = 'LINE' and c.qualname = ? "
            "group by e.line order by e.line", (qualname,)).fetchall()
    finally:
        con.close()
    merged: dict = {}
    for hist in by_frame.values():
        for ln, n in hist.items():
            merged[ln] = merged.get(ln, 0) + n
    by_code = {int(ln): int(n) for ln, n in code_rows}
    return {
        "qualname": qualname,
        "code_object_ids": codes,
        "frame_ids": frames,
        "activations": len(frames),
        "by_line": dict(sorted(merged.items())),
        "total": sum(merged.values()),
        "by_line_via_code_id": dict(sorted(by_code.items())),
        "total_via_code_id": sum(by_code.values()),
        "joins_agree": dict(sorted(merged.items())) == by_code,
    }


def histogram_diff(measured: dict, expected: dict) -> dict:
    """The diff §1.1's table exists to make readable: which lines are
    missing, which are unexpected, and where a count differs.

    Keys are ints on both sides; a caller reading either from JSON must
    convert first, and `int_keys` below is what does it.
    """
    m, e = dict(measured or {}), dict(expected or {})
    missing = sorted(ln for ln in e if ln not in m)
    extra = sorted(ln for ln in m if ln not in e)
    diffs = sorted((ln, m[ln], e[ln]) for ln in m if ln in e and m[ln] != e[ln])
    return {
        "missing_lines": missing,
        "unexpected_lines": extra,
        "count_diffs": [{"line": ln, "measured": a, "expected": b}
                        for ln, a, b in diffs],
        "differences": len(missing) + len(extra) + len(diffs),
        "measured_total": sum(m.values()),
        "expected_total": sum(e.values()),
    }


def int_keys(d: dict | None) -> dict:
    """A `{line: count}` map read back from JSON, with its keys ints again."""
    return {int(k): v for k, v in (d or {}).items()}
