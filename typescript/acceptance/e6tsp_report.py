"""E6-TS′'s JSON: what the invocation's `exceptions` answer says, and what
the adjudication of its SWALLOWED shapes came to.

Two halves, and they are deliberately not the same thing:

  * the ANSWER is parsed here -- shapes by disposition, the tally, the
    escaped-ambiguous count, and one row per SWALLOWED shape with its sink
    site resolved to `file:line` out of the trace the bracket names;
  * the ADJUDICATION is read from the markdown table a HUMAN reader fills in
    against the consumer's own source (P9). Until that file exists `value` is
    `null` and `dropped` says the gate has not been read -- a shape count is
    not an accusation count, and a report that printed 0 before anybody had
    read a line would answer the endpoint by construction.

`value` is the number of FALSE rows: the pre-registered gate is 0.

WHY THE SITE IS RESOLVED FROM THE TRACE AND NOT FROM THE LINE
-------------------------------------------------------------
The verdict prints `(<qualname> L<line>)` and adds the file's basename only
where two shapes of one answer would otherwise collide. An adjudicator needs
the file for EVERY row -- they have to go and read it -- so each SWALLOWED
row's sink event is looked up in the trace the bracket names and its code
object's file is taken from there. That is the same `(file, line, qualname)`
the grouper keyed the shape on, so the row names the place the verdict is
about and not a place that prints the same words.
"""
import json
import os
import re
import sys
from pathlib import Path

from lens import cell, emit

#: The block grammar `exceptions_group.print_shape` prints (2/4/6 spaces).
HEAD = re.compile(r"^  (e\d+) (.*)$")
VERDICT = re.compile(r"^    ([A-Z][A-Z-]*) -- (.*)$")
DETAIL = re.compile(r"^      (.*)$")
#: `  [×3 over 2 processes: first e12 in <run>, +2]` / `  [in <run>]`.
BRACKET = re.compile(r"\s*\[(?:×(\d+) over [^:]*: first e(\d+) in (\S+?), \+\d+"
                     r"|in (\S+?))\]\s*$")
#: The one sentence that prints the literal token this endpoint is about.
SWALLOWED = re.compile(r"^caught by (\S+) at e(\d+) \((.+?)\) in f(\d+), "
                       r"which returned$")
#: §3.3 rule 5's escaped-or-opaque reason -- reported beside the gate.
ESCAPED = re.compile(r"^caught at e(\d+) \((\S+?)\), and the error or a "
                     r"rendering of it left the handler; not followed$")
#: The adjudication table's header, and the column each fact is in.
TABLE_HEADER = ("| id | site | how | source | verdict | second reading | reason |")


def blocks(text: str) -> list[dict]:
    """Every printed shape, in printed order, with its ids and its lines."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        head = HEAD.match(line)
        if not head or i + 1 >= len(lines):
            continue
        verdict = VERDICT.match(lines[i + 1])
        if not verdict:
            continue
        rest = verdict.group(2)
        bracket = BRACKET.search(rest)
        detail = []
        for follow in lines[i + 2:]:
            more = DETAIL.match(follow)
            if not more:
                break
            detail.append(more.group(1))
        out.append({
            "origin": head.group(1), "head": head.group(2),
            "disposition": verdict.group(1),
            "verdict": rest[:bracket.start()].strip() if bracket else rest,
            "n": int(bracket.group(1)) if bracket and bracket.group(1) else 1,
            "run": (bracket.group(3) or bracket.group(4)) if bracket else None,
            "detail": detail,
        })
    return out


class Traces:
    """The invocation's member traces, opened once each.

    An answer over 372 processes asks the same trace for many sinks; opening
    it per row would be the difference between a second and a minute, and a
    cache is the only reason this is a class.
    """

    def __init__(self, store: str) -> None:
        os.environ["SENSORIUM_DIR"] = store
        self._open: dict[str, object] = {}

    def file_of(self, run: str | None, event_id: int | None) -> str | None:
        """The event's code object's file, or None where it cannot be read."""
        if not run or event_id is None:
            return None
        try:
            if run not in self._open:
                from sensorium import paths
                from sensorium.store.reader import Trace
                self._open[run] = Trace.open(paths.find_trace(run))
            trace = self._open[run]
            event = trace.event(event_id)
            if event is None or event.code_id is None:
                return None
            return trace.code(event.code_id).file
        except Exception:  # noqa: BLE001 -- unreadable is a null, not a crash
            return None


def swallowed_rows(traces: "Traces", shapes: list[dict]) -> list[dict]:
    """One row per SWALLOWED shape: what the adjudicator has to go and read."""
    rows = []
    for i, shape in enumerate(s for s in shapes if s["disposition"] == "SWALLOWED"):
        m = SWALLOWED.match(shape["verdict"])
        how = m.group(1) if m else None
        sink = int(m.group(2)) if m else None
        at = m.group(3) if m else None
        rows.append({
            "id": f"S{i + 1}", "how": how, "sink_event": f"e{sink}" if m else None,
            "at": at, "file": traces.file_of(shape["run"], sink),
            "n": shape["n"], "run": shape["run"], "origin": shape["origin"],
            "head": shape["head"], "verdict": shape["verdict"],
            "detail": shape["detail"],
            "unparsed": None if m else shape["verdict"],
        })
    return rows


def how_tally(store: str, invocation: str | None) -> dict:
    """§1's ungated report: HANDLED records per `how` over the whole run.

    Read off the invocation's MEMBER TRACES rather than the answer, because
    the answer is a set of shapes and this is a count of records: a `how`
    that never reached a verdict still says what the transform wrote and
    what the wire carried.
    """
    if not invocation:
        return {"read": False, "why": "no invocation id"}
    try:
        os.environ["SENSORIUM_DIR"] = store
        from sensorium.query import exceptions_invocation
        from sensorium.store.reader import Trace
        _inv, members = exceptions_invocation.resolve_invocation(invocation)
        counts: dict[str, int] = {}
        for path in members:
            trace = Trace.open(path)
            for event in trace.events(kind="HANDLED"):
                word = (event.payload or {}).get("how") or "?"
                counts[word] = counts.get(word, 0) + 1
        return {"read": True, "members": len(members),
                "counts": dict(sorted(counts.items()))}
    except Exception as e:  # noqa: BLE001
        return {"read": False, "why": f"{type(e).__name__}: {e}"}


def tally_of(text: str) -> tuple[str | None, dict]:
    """The `dispositions:` line, parsed WHOLE (E6-TS's rule, same reason)."""
    line = next((ln.strip() for ln in text.splitlines()
                 if ln.startswith("dispositions:")), None)
    if line is None:
        return None, {}
    terms = {}
    for part in line[len("dispositions:"):].split(","):
        word, _, count = part.strip().rpartition(" ")
        if not word or not count.isdigit():
            return line, {}
        terms[word] = int(count)
    return line, terms


def adjudication(path: str) -> dict:
    """The human's table: verdicts by shape id, or why it was not read."""
    if not path:
        return {"read": False, "why": "no adjudication file was named"}
    file = Path(path)
    if not file.is_file():
        return {"read": False,
                "why": f"{file.name} does not exist: no line has been adjudicated"}
    rows, bad = {}, []
    for line in file.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| S") or "|" not in line[2:]:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 7:
            bad.append(f"row {cols[0] if cols else '?'} has {len(cols)} columns, "
                       "the table has 7")
            continue
        verdict = cols[4].upper()
        if verdict not in ("TRUE", "FALSE"):
            bad.append(f"row {cols[0]}: verdict {cols[4]!r} is neither TRUE nor "
                       "FALSE; §7 has no third word and an undecidable row is "
                       "FALSE")
            continue
        rows[cols[0]] = {"verdict": verdict,
                         "second_reading": cols[5].strip().lower() in
                                           ("yes", "y", "true"),
                         "reason": cols[6]}
    return {"read": True, "rows": rows, "malformed": bad}


def main() -> int:
    env = os.environ
    text = Path(env["E6TSP_TRANSCRIPT"]).read_text(encoding="utf-8",
                                                   errors="replace")
    store = env.get("E6TSP_STORE") or env.get("SENSORIUM_DIR") or ""
    shapes = blocks(text)
    rows = swallowed_rows(Traces(store), shapes)
    line, terms = tally_of(text)
    written = [ln for ln in Path(env["E6TSP_JSONL"]).read_text(encoding="utf-8")
               .splitlines() if ln.strip()]
    run = json.loads(written[0]) if written else {}
    verdicts = adjudication(env.get("E6TSP_ADJUDICATION", ""))

    dropped, blocking = [], []
    if not run.get("ok"):
        dropped.append("the call run's suite was not 372/4278: "
                       + "; ".join(run.get("why_not_ok") or ["no run recorded"]))
    if any(ln.startswith("more:") for ln in text.splitlines()):
        blocking.append("the answer was paged: shapes were left unprinted, and "
                        "an adjudication of the ones that fit is not an "
                        "adjudication")
    for row in rows:
        if row["unparsed"]:
            blocking.append(f"{row['id']}: the SWALLOWED sentence did not parse")
    false_rows, second, missing = [], 0, []
    if verdicts["read"]:
        blocking.extend(verdicts["malformed"])
        for row in rows:
            got = verdicts["rows"].get(row["id"])
            if got is None:
                missing.append(row["id"])
                continue
            row["adjudged"] = got["verdict"]
            row["reason"] = got["reason"]
            second += 1 if got["second_reading"] else 0
            if got["verdict"] == "FALSE":
                false_rows.append(row)
        if missing:
            blocking.append("shapes with no row in the adjudication table: "
                            + ", ".join(missing))
    else:
        blocking.append(verdicts["why"])

    # A count of FALSE rows is the gate only when every row was read off a
    # complete answer. Anything in `blocking` means it was not, and the cell
    # says `null` rather than a number over part of the question.
    dropped.extend(blocking)
    gated = None if blocking else len(false_rows)
    emit(cell(
        gated, len(rows), dropped,
        rule="0 false SWALLOWED; a false one -> STOP",
        invocation=env.get("E6TSP_INVOCATION") or None,
        exceptions_exit=(int(env["E6TSP_EXCEPTIONS_EXIT"])
                         if env.get("E6TSP_EXCEPTIONS_EXIT") else None),
        limit=int(env.get("E6TSP_LIMIT") or 0) or None,
        recorder=env.get("E6TSP_RECORDER"), recorder_rev=env.get("E6TSP_REV"),
        recorder_bin=env.get("E6TSP_BIN"),
        spool_set=env.get("E6TSP_SPOOL_NAME") or None,
        tally_line=line, tally=terms,
        shapes_total=len(shapes),
        shapes_by_disposition={d: sum(1 for s in shapes if s["disposition"] == d)
                               for d in sorted({s["disposition"] for s in shapes})},
        escaped_ambiguous=sum(1 for s in shapes
                              if s["disposition"] == "AMBIGUOUS"
                              and ESCAPED.match(s["verdict"])),
        needed_a_second_reading=second if verdicts["read"] else None,
        handled_by_how=how_tally(store, env.get("E6TSP_INVOCATION")),
        false_accusations=[{"id": r["id"], "printed": r["verdict"],
                            "file": r["file"], "reason": r.get("reason")}
                           for r in false_rows],
        call_run={k: run.get(k) for k in
                  ("wall", "harness_wall", "load_1min", "exit",
                   "suite_files_ok", "suite_tests_ok", "ok", "invocation",
                   "duration_line", "spool_files", "spool_bytes",
                   "spool_lines")},
        manifest={"lines": int(env.get("E6TSP_MANIFEST_LINES") or 0),
                  "sha256": env.get("E6TSP_MANIFEST_SHA"),
                  "before_exit": int(env.get("E6TSP_MANIFEST_BEFORE_STATUS") or 0),
                  "after_exit": int(env.get("E6TSP_MANIFEST_AFTER_STATUS") or 0),
                  "after_ok": int(env.get("E6TSP_MANIFEST_AFTER_OK") or 0)},
        wrapper=env.get("E6TSP_WRAPPER"),
        wrapper_listing=env.get("E6TSP_WRAPPER_LISTING"),
        markers=Path(env["E6TSP_MARKERS"]).read_text(encoding="utf-8")
        if env.get("E6TSP_MARKERS") and Path(env["E6TSP_MARKERS"]).is_file() else None,
        swallowed_shapes=rows,
        table_header=TABLE_HEADER,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
