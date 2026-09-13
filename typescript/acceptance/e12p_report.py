"""E12′: rung 4's H2, H4 and H5, re-read by an instrument without the four
defects its own post-mortem named.

    .venv/bin/python typescript/acceptance/e12p_report.py \\
        <reads dir> <store> <out dir>

NOTHING HERE RECORDS AND NOTHING HERE RE-RUNS. The data is rung 4's, already
committed: the thirteen read transcripts under
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/` and
the store those reads were taken against, opened READ-ONLY for the one fact a
printed row cannot carry -- a CALL's code-object line. The question is not
"what did the recorder do" (rung 4 answered that, once) but "can an instrument
without the four defects read what rung 4's post-mortem read by hand".

THE FOUR DEFECTS, AND WHAT CHANGED
----------------------------------
Each is a sentence of the rung-4 record's §4.4/§4.5 and a line of the design's
§3.2:

1. **A CALL row's name is the token before its `(`.** `flow` prints
   `parseDiceGroups(formula='1d20')` where `e12_report.ROW`'s `\\S+` took the
   whole thing, so `qualname in {the three focused}` failed on the row that IS
   the sighting. `ROW2` stops the qualname at `(` and keeps the argument list
   in `args`.
2. **A CALL row's line is the code object's, read from the trace.** A printed
   CALL carries no `L<line>`; §1.3's `diceQueue.ts:68` is the definition line,
   which lives in the trace's `code_objects` table. `call_line_of` reads it.
3. **A RETURN row's arrow takes one space or two.** `-> 20` and `->  20` are
   one shape; `ROW`'s `\\s\\s` saw only the second.
4. **A `watch` HIT is classed by its payload, not its line.** A row carrying
   `unbound` is a `while`'s completion row; a row on the same line carrying
   deltas and no `unbound` is a head row. `rows_of2` parses `unbound:` so the
   class is readable.

WHICH RECORD SAYS WHAT
----------------------
Two records are read, and they say different things (controller ruling P1):

* **the QUESTIONS** are rung 4's, in `e12_report.RECORD`'s §1 -- the read
  commands, §1.2's three `watch` triples, §1.3's two sightings, the three
  focus specs. `preregistration()` is imported unchanged and reads them, so
  this instrument asks rung 4's questions in rung 4's own words.
* **the PREDICTED NUMBERS** are this slice's, in `e12p_pre.RECORD`'s
  §1.2-§1.4 --
  N = 6, `focus_matched` = 5, W2's 52/0/2, W3's 15, S1's 9, S2's `e10`/68,
  `elsewhere_not_gated` = 5, the two `sightings:` totals. They are parsed out
  of that file's §1 by regex, the way `e12_report.one()` does it, and never
  typed here: a cell then compares what the instrument READ against what §1
  SAYS, and an edit to either is visible in the JSON.

THE HASH PREFLIGHT
------------------
§1.1 of this slice's record lists the thirteen transcripts with their sha256
and cites the store's own hash list by sha256. Both are verified BEFORE any
cell is computed and a mismatch is **exit 4 and no number**: a reading of data
the record does not describe is not the reading §1 pre-registers. The store's
thirteenth entry, `invocations.jsonl`, is checked as an APPEND -- its first
`journal head` lines must still hash to what rung 4 listed -- because rung 4's
hash list was taken before rung 4's own reads, which appended to it.
"""
import json
import os
import re
import sys
from pathlib import Path

from e12_report import (LABELS, cell, db, emit, meta, one, preregistration,
                        record_path, subsection, usage)
from e12p_pre import (RUNG4_RESULTS, handcount_rows, preflight, predictions)

#: A row as every listing command prints it, read correctly for a CALL
#: (`name(args…)` before any `L<line>`) and for a RETURN whose `->` follows
#: ONE space. `qual` stops at `(` or whitespace; `args` is the parenthesised
#: text when present.
ROW2 = re.compile(r"^\s*(?:HIT\s+)?e(?P<eid>\d+) (?P<kind>[A-Z]+)\s+"
                  r"(?P<qual>[^\s(]+)(?P<args>\([^)]*\))?"
                  r"(?: L(?P<line>\d+))?(?:\s+->\s+(?P<ret>.*?))?"
                  r"(?:\s\s(?P<rest>.*))?$")

#: The names a block-like statement's completion row drops, as the row prints
#: them: `unbound:count,sides`. Its PRESENCE is the class (defect 4); the
#: names are what §1.3's W2 clause is about ("a row whose `unbound` names
#: `count`").
UNBOUND = re.compile(r"unbound:([A-Za-z_$][\w$]*(?:,[A-Za-z_$][\w$]*)*)")

#: `watch`'s own tallies, one line: `sites: 165   evaluated: 77   hits: 52
#: …`. The HIT ROWS are capped by `--limit`, so the total is read here and
#: never counted off the printed rows -- rung 4's W2 transcript prints 20 of
#: 52 and says so.
TALLY = re.compile(r"^sites:\s+(?P<sites>\d+)\s+evaluated:\s+(?P<evaluated>\d+)"
                   r"\s+hits:\s+(?P<hits>\d+)\s+not-captured:\s+"
                   r"(?P<not_captured>\d+)\s+errors:\s+(?P<errors>\d+)\s*$")

#: `flow`'s own total: `sightings: 10 event(s), 10 capture(s)`.
SIGHTINGS = re.compile(r"^sightings:\s+(\d+) event")

# -- the rows ---------------------------------------------------------------


def rows_of2(text: str) -> list[dict]:
    """Every event row a listing command printed, parsed without the four.

    `rows_of`'s keys, plus three the defects need: `args` (a CALL's
    parenthesised argument text, or None), `ret` (a RETURN's value, or None)
    and `unbound` (the names the row dropped, `[]` when it dropped none --
    which is what makes a head row a head row).
    """
    out = []
    for line in text.splitlines():
        m = ROW2.match(line.rstrip())
        if not m:
            continue
        rest = (m.group("rest") or "").strip()
        labels = LABELS.search(line)
        unbound = UNBOUND.search(rest)
        out.append({"eid": int(m.group("eid")), "kind": m.group("kind"),
                    "qualname": m.group("qual"),
                    "args": m.group("args"),
                    "ret": m.group("ret"),
                    "line": int(m.group("line")) if m.group("line") else None,
                    "rest": rest, "hit": line.strip().startswith("HIT"),
                    "unbound": unbound.group(1).split(",") if unbound else [],
                    "labels": [s.strip() for s in
                               labels.group(1).split(",")] if labels else [],
                    "text": line.strip()})
    return out


def tally_of(text: str) -> dict:
    """`watch`'s own `sites: … evaluated: … hits: …` line, as integers.

    The HIT TOTAL is read here and never counted off the printed rows. Rung
    4's W2 transcript prints twenty of its fifty-two and says `... 32 more`,
    so a reader that counted rows would publish 20 where §1.3 predicts 52 --
    a fifth defect nobody has had yet, and this is where it does not start.
    What IS read off the rows is the CLASS question (defect 4): which of the
    printed HITs sit on a completion row, and which at line 72.
    """
    for line in text.splitlines():
        m = TALLY.match(line.strip())
        if m:
            return {k: int(v) for k, v in m.groupdict().items()}
    return {}


def verdict_of(text: str) -> str:
    """`watch`'s verdict line, whole, or the empty string."""
    return next((ln for ln in text.splitlines()
                 if ln.startswith("verdict:")), "")


def exit_of(text: str) -> int | None:
    """A saved transcript's own `--- exit <n>` trailer.

    The committed transcripts are `Reads.run`'s files, which end with the
    exit status the command returned; re-reading them is how a re-adjudication
    gets the exit §1.2 predicts without re-running anything.
    """
    m = re.search(r"^--- exit (-?\d+)\s*$", text, re.M)
    return int(m.group(1)) if m else None


def sightings_total(text: str) -> int | None:
    """`flow`'s own `sightings: <n> event(s), <n> capture(s)` total."""
    for line in text.splitlines():
        m = SIGHTINGS.match(line.strip())
        if m:
            return int(m.group(1))
    return None


def split_population(rows: list[dict], focused: set) -> tuple[list, list]:
    """§1.3's gated population, and every row outside it.

    The population is `e12_report.h5`'s, unchanged in RULE: the LINE `deltas`
    and CALL `args` of the three focused functions, matched by `flow`'s own
    `[local <name>]` / `[arg <name>]` labels, every label read rather than
    just the first. What changed is that a CALL row now reaches this test
    with its qualname parsed off the token before `(` (defect 1), so the row
    §1.3 names as S2 lands in the population instead of outside it.

    Each population row gains `names`: the labelled names it sighted.
    """
    population, elsewhere = [], []
    for row in rows:
        mine = [label for label in row["labels"]
                if (row["kind"] == "LINE" and label.startswith("local "))
                or (row["kind"] == "CALL" and label.startswith("arg "))]
        target = population if (row["qualname"] in focused and mine) \
            else elsewhere
        target.append({**row, "names": [m.split(" ", 1)[1] for m in mine]})
    return population, elsewhere


def resolver_sites_in_record(text: str) -> list[str]:
    """`node resolve.mjs`'s six sites, as the rung-4 record's §4.2 quotes it.

    The session's own `resolve.json` was written under rung 4's out directory
    and is not committed; what IS committed is §4.2's fenced copy of it,
    which is the reading the new record's §3.3 names ("`node resolve.mjs`
    output in the record"). A live `resolve.json` -- H8′'s, at Task 11 --
    is read instead when one is handed in, and the cell says which it read.
    """
    block = one(r"```\n(.*?)```", subsection(text, "### 4.2 "),
                "§4.2's fenced resolver output")
    return [ln.strip() for ln in block.splitlines()
            if re.fullmatch(r"\S+:\S+", ln.strip())]


def call_line_of(conn, eid: int) -> int | None:
    """One event's code object's own first line, read from the trace.

    Defect 2. `flow` prints no `L<line>` on a CALL row, and §1.4's `line` for
    S2 is `diceQueue.ts:68` -- the function's definition line, which the
    trace holds on the code object rather than on the event.

    SCHEMA, NOT API, and which was checked: `src/sensorium/query/` exposes no
    reader that hands back an event's code object (a grep for `firstlineno`
    over that package finds one use, on a `code` row its TypeScript
    exceptions reader assembles itself), so this is the join
    `e12_report.lookup()` already uses. The table is `code_objects`, columns
    `(id, file, qualname, firstlineno)` -- not `codes`.
    """
    row = conn.execute(
        "SELECT c.firstlineno FROM events e "
        "JOIN code_objects c ON c.id = e.code_id WHERE e.id = ?",
        (eid,)).fetchone()
    return row[0] if row else None


# -- the three endpoints ----------------------------------------------------


def _flat(text: str) -> str:
    """One line's whitespace collapsed, for comparing a quoted suite line.

    §1.2 quotes vitest's two lines inside backticks and markdown wrapped one
    of them across a newline; the wrap is the record's typography, not a
    difference in the measurement, so the comparison is on the words and the
    raw forms are reported beside it.
    """
    return " ".join(text.split())


def _stamp(**detail) -> dict:
    """What every cell of this instrument says about where it came from."""
    return {"instrument": "e12p_report.py",
            "data": "committed transcripts of 2026-09-11",
            "recorder": os.environ.get("E12P_RECORDER"),
            "recorder_rev": os.environ.get("E12P_REV"), **detail}


def h2p(pre, handcount_rows, resolve_json, conn, *, suite=None,
        call_read=None) -> dict:
    """H2′: do the hand count, the resolver and the trace say one number?

    The four positional arguments are the interface's. `suite` and
    `call_read` are keyword-only and carry §1.2's third bullet, the suite
    half: those two lines are vitest's, printed by rung 4's arms, and live in
    rung 4's saved H2 cell rather than in any read transcript. Passed none,
    the cell drops those clauses BY NAME rather than scoring a reading nobody
    took.
    """
    pred = predictions()
    sites, source = resolver_sites(resolve_json)
    hand = [r["qualname"] for r in handcount_rows]
    m = meta(conn)
    focus_matched = m.get("focus_matched") or []
    functions_focused = m.get("functions_focused")
    shared = sorted({n for n in hand if hand.count(n) == 2})
    resolver_names = [s.split(":", 1)[1] for s in sites]
    dropped = []
    claims = {
        f"hand count, resolver sites and `functions_focused` are all "
        f"{pred['functions_focused']}":
            len(hand) == len(sites) == functions_focused
            == pred["functions_focused"],
        f"`meta.focus_matched` is {pred['focus_matched']}":
            len(focus_matched) == pred["focus_matched"],
        f"the one qualname two sites share is `{pred['shared_qualname']}`":
            shared == [pred["shared_qualname"]]
            and sorted({n for n in resolver_names
                        if resolver_names.count(n) == 2}) == shared,
    }
    if suite is None:
        dropped.append("the suite half was not handed in: §1.2's two vitest "
                       "lines are rung 4's arms', and no read transcript "
                       "carries them")
    else:
        want = [_flat(line) for line in pred["suite_lines"]]
        got = [[_flat(suite[arm]["files"]), _flat(suite[arm]["tests"])]
               for arm in ("U1", "F1")]
        claims["the suite half is §1.2's two lines, both arms, both exit 0"] = (
            all(pair == want for pair in got)
            and all(suite[arm]["exit"] == 0 for arm in ("U1", "F1")))
    if call_read is None:
        dropped.append("the `grep --kind CALL` transcript was not handed in")
        first = None
    else:
        rows = rows_of2(call_read)
        first = (rows[0]["qualname"] + (rows[0]["args"] or "")) if rows else None
        claims[f"`grep --kind CALL` prints `{pred['call_first']}` first"] = (
            first == pred["call_first"])
    return cell(sum(1 for v in claims.values() if v), len(claims), dropped,
                rule=("one number three ways (hand count, resolver, trace), "
                      "`focus_matched` one lower for the shared qualname, and "
                      "the suite half unmoved -> else STOP"),
                **_stamp(claims=claims, predicted=pred["functions_focused"],
                         hand_count=handcount_rows, hand_n=len(hand),
                         resolver_sites=sites, resolver_source=source,
                         meta_functions_focused=functions_focused,
                         meta_focus_matched=focus_matched,
                         shared_qualname=shared,
                         suite=suite, suite_expected=pred["suite_lines"],
                         call_first_read=first,
                         call_first_expected=pred["call_first"],
                         data_recorder=m.get("recorder")))


def resolver_sites(resolve_json) -> tuple[list[str], str]:
    """The resolver's site list, and which copy of it was read.

    Rung 4's own `resolve.json` was written under its out directory and is
    not committed; §4.2 of the rung-4 record quotes it, which is the reading
    §3.3 names ("`node resolve.mjs` output in the record"). A live
    `resolve.json` -- H8′'s, at Task 11 -- is preferred when one is handed
    in, and the cell records which was used rather than leaving a reader to
    guess.
    """
    path = Path(resolve_json) if resolve_json else None
    if path is not None and path.is_file():
        body = json.loads(path.read_text(encoding="utf-8"))
        return ([f"{m['rel']}:{m['qualname']}"
                 for m in body.get("matched", [])], f"resolve.json ({path.name})")
    sites = resolver_sites_in_record(
        record_path().read_text(encoding="utf-8"))
    return sites, "the rung-4 record's §4.2, quoted"


def h4p(pre, watch_reads) -> dict:
    """H4′: does `watch` answer, and is W2's clause read off the payload?

    `pre` is rung 4's §1.2 (the verdict word and the exit); the counts are
    §1.3 of this record. The clause rung 4's instrument read too strongly --
    "no HIT at line 72" where §1.2 wrote "no HIT at line 72's `while`-
    completion row" -- is read here off `unbound`, which is the only thing
    that tells the two rows apart (defect 4).
    """
    pred = predictions()
    by_expr = {t["expr"]: t for t in pre["triples"]}
    per, dropped = [], []
    for want in pred["triples"]:
        rung4 = by_expr.get(want["expr"])
        got = watch_reads.get(want["expr"])
        if got is None or rung4 is None:
            dropped.append(f"{want['id']} (`{want['expr']}`) has no committed "
                           "transcript under §1.2's words")
            continue
        tally = tally_of(got["text"])
        verdict = verdict_of(got["text"])
        hits = [r for r in rows_of2(got["text"]) if r["hit"]]
        at_line = [r for r in hits if r["line"] == want["line"]]
        on_completion = [r for r in hits
                         if want["unbound_name"] in r["unbound"]] \
            if want["unbound_name"] else []
        claims = {
            f"verdict says {rung4['verdict']}": rung4["verdict"] in verdict,
            f"exit {rung4['exit']}": got["exit"] == rung4["exit"],
            f"hits = {want['hits']}": tally.get("hits") == want["hits"],
        }
        if want["evaluated"] is not None:
            claims[f"evaluated at {want['evaluated']} site(s)"] = (
                tally.get("evaluated") == want["evaluated"])
        if want["on_completion_rows"] is not None:
            claims[f"{want['on_completion_rows']} HIT(s) on a row whose "
                   f"`unbound` names `{want['unbound_name']}`"] = (
                len(on_completion) == want["on_completion_rows"])
        if want["at_line_count"] is not None:
            claims[f"{want['at_line_count']} HIT(s) at line {want['line']}, "
                   "all head rows (no `unbound`)"] = (
                len(at_line) == want["at_line_count"]
                and all(not r["unbound"] for r in at_line))
        if want["unbound_carried"] is not None:
            claims[f"every printed HIT is at line {want['line']} carrying "
                   f"`unbound:{','.join(want['unbound_carried'])}`"] = (
                bool(hits)
                and all(r["line"] == want["line"]
                        and r["unbound"] == want["unbound_carried"]
                        for r in hits))
        per.append({**want, "transcript": got["name"], "verdict_line": verdict,
                    "exit": got["exit"], "tally": tally,
                    "printed_hits": len(hits),
                    "hits_at_line": [r["text"] for r in at_line],
                    "hits_on_completion_rows": [r["text"] for r in on_completion],
                    "claims": claims, "ok": all(claims.values())})
    return cell(sum(1 for t in per if t["ok"]), len(pred["triples"]), dropped,
                rule=("all three triples as §1.3 re-registers them -- verdict, "
                      "exit, hit total, and W2's clause read off `unbound` "
                      "rather than off a line number -> else STOP"),
                **_stamp(triples=per,
                         note=("the hit TOTAL is `watch`'s own tally line; the "
                               "CLASS questions are read off the printed rows, "
                               "which `--limit` caps at 20")))


def h5p(pre, flow_reads, focused, conn) -> dict:
    """H5′: does `flow --value` see both sightings?

    The population rule is rung 4's; what changed is that a CALL row reaches
    it with a parsed qualname (defect 1) and takes its line from the trace's
    code object (defect 2), and that a RETURN row with a one-space arrow is
    visible at all (defect 3), so `elsewhere_not_gated` is the five rows the
    two transcripts print rather than the one rung 4's cell listed.
    """
    pred = predictions()
    found, elsewhere, unpredicted, totals = [], [], [], []
    dropped = []
    for want in pre["sightings"]:
        got = flow_reads.get(want["command"])
        if got is None:
            dropped.append(f"{want['id']} (`{want['command']}`) has no "
                           "committed transcript")
            continue
        rows = rows_of2(got["text"])
        population, outside = split_population(rows, focused)
        seen = set()
        for row in population:
            line = row["line"] if row["line"] is not None \
                else call_line_of(conn, row["eid"])
            row["resolved_line"] = line
            seen |= {(name, line) for name in row["names"]}
        hit = [r for r in population
               if (want["name"], want["line"])
               in {(n, r["resolved_line"]) for n in r["names"]}]
        totals.append(sightings_total(got["text"]))
        found.append({**want, "transcript": got["name"], "seen": bool(hit),
                      "rows": [{"eid": r["eid"], "kind": r["kind"],
                                "qualname": r["qualname"],
                                "line": r["resolved_line"],
                                "names": r["names"], "text": r["text"]}
                               for r in hit],
                      "triples_in_population": sorted(
                          [list(t) for t in seen], key=repr),
                      "printed_total": sightings_total(got["text"]),
                      "exit": got["exit"]})
        unpredicted += [list(t) for t in sorted(seen, key=repr)
                        if t != (want["name"], want["line"])]
        elsewhere += [r["text"] for r in outside]
    s2 = next((f for f in found if f["id"] == pred["s2_id"]), None)
    claims = {f"{f['id']} found": f["seen"] for f in found}
    claims[f"`unpredicted` = {pred['unpredicted']}"] = (
        len(unpredicted) == pred["unpredicted"])
    claims[f"`elsewhere_not_gated` = {pred['elsewhere_not_gated']}"] = (
        len(elsewhere) == pred["elsewhere_not_gated"])
    claims[f"the transcripts print `sightings:` "
           f"{' and '.join(str(n) for n in pred['sightings_totals'])}"] = (
        totals == pred["sightings_totals"])
    claims[f"S2 is event e{pred['s2']['eid']}, a {pred['s2']['kind']} row of "
           f"`{pred['s2']['qualname']}` at line {pred['s2']['line']}"] = bool(
        s2 and s2["rows"]
        and s2["rows"][0]["eid"] == pred["s2"]["eid"]
        and s2["rows"][0]["kind"] == pred["s2"]["kind"]
        and s2["rows"][0]["qualname"] == pred["s2"]["qualname"]
        and s2["rows"][0]["line"] == pred["s2"]["line"])
    s1 = next((f for f in found if f["id"] == pred["s1_id"]), None)
    claims[f"{pred['s1_id']} is sighted {pred['s1_sightings']} time(s)"] = bool(
        s1 and len(s1["rows"]) == pred["s1_sightings"])
    return cell(sum(1 for v in claims.values() if v), len(claims), dropped,
                rule=("both sightings found, no third triple in the gated "
                      "population, and the ungated rows counted as §1.4 "
                      "re-registers them -> else STOP"),
                **_stamp(claims=claims, sightings=found,
                         unpredicted=unpredicted,
                         elsewhere_not_gated=elsewhere,
                         printed_totals=totals,
                         focused_functions=sorted(focused)))




# -- the session ------------------------------------------------------------


def transcripts(reads_dir: Path) -> dict:
    """Every committed transcript, keyed by the §1.5 command that wrote it.

    `e12_report.Reads.run` wrote each file with its own command as the first
    line (`$ sensorium <command>`), so a read is found here by the WORDS §1.5
    writes and never by a file's position in a sorted listing -- a triple
    adjudicated against the wrong transcript is the one mistake a cell cannot
    see, and matching on the command is what rung 4's own `main` did.
    """
    out = {}
    for path in sorted(reads_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        head = text.splitlines()[0] if text else ""
        key = head[len("$ sensorium "):] if head.startswith("$ sensorium ") \
            else head
        out[key] = {"name": path.name, "text": text, "exit": exit_of(text)}
    return out


def run_id_of(text: str) -> str | None:
    """The run id an `info` transcript names on its first printed line."""
    m = re.search(r"^run (\S+)", text, re.M)
    return m.group(1) if m else None


def saved_suite() -> dict | None:
    """Rung 4's own H2 cell's `suite` block: vitest's two lines, both arms.

    Not a second measurement -- it is the reading rung 4 published, in its
    committed results file -- and §1.2 predicts it "exactly as the rung-4
    record's §4.2 quotes it", so the cell compares the published measurement
    against the record's quotation of it.
    """
    if not RUNG4_RESULTS.is_file():
        return None
    body = json.loads(RUNG4_RESULTS.read_text(encoding="utf-8"))
    return ((body.get("gated") or {}).get("H2") or {}).get("suite")


def main(argv) -> int:
    if len(argv) != 4:
        usage("usage: e12p_report.py <reads dir> <store> <out dir>")
    reads_dir, store, out = Path(argv[1]), Path(argv[2]), Path(argv[3])
    out.mkdir(parents=True, exist_ok=True)

    # §1.1 FIRST. A cell read off data this record does not describe is not
    # the reading §1 pre-registers, so the hashes are checked before the
    # record is even parsed for numbers, and a mismatch is exit 4.
    checks = preflight(reads_dir, store)
    if not checks["ok"]:
        (out / "e12p-preflight.json").write_text(
            json.dumps(checks, indent=2) + "\n", encoding="utf-8")
        sys.stderr.write(
            "refused: §1.1's hashes do not describe this data, so no number "
            "is read.\n" + "\n".join(
                f"  {why}" for why in checks["transcripts"]["why"]
                + checks["store"]["why"]) + "\n")
        return 4

    pre = preregistration()                # rung 4's §1: the QUESTIONS
    pred = predictions()                   # this slice's §1: the NUMBERS
    reads = transcripts(reads_dir)

    def need(command: str) -> dict:
        got = reads.get(command)
        if got is None:
            usage(f"no committed transcript for `{command}`, which §1.5 "
                  "lists; the reads are found by their own first line and "
                  "never by position")
        return got

    f1 = run_id_of(need("info F1")["text"])
    if not f1:
        usage("`info F1`'s transcript names no run id, and the trace is where "
              "a CALL row's line is read from")
    conn = db(store, f1)
    try:
        watch_reads = {t["expr"]: need(
            next(ln for ln in pre["commands"]
                 if ln.startswith("watch F1") and ln.endswith(t["expr"])))
            for t in pre["triples"]}
        flow_reads = {s["command"]: need(s["command"])
                      for s in pre["sightings"]}
        call_line = next(ln for ln in pre["commands"] if "--kind CALL" in ln)
        focused = {spec.split(":", 1)[1] for spec in pre["specs"]}
        cells = {
            "H2p": h2p(pre, handcount_rows(), os.environ.get("E12P_RESOLVE"),
                       conn, suite=saved_suite(),
                       call_read=need(call_line)["text"]),
            "H4p": h4p(pre, watch_reads),
            "H5p": h5p(pre, flow_reads, focused, conn),
        }
    finally:
        conn.close()

    payload = {
        "cells": cells,
        "run_id": f1,
        "reads": {key: got["name"] for key, got in sorted(reads.items())},
        "preflight": checks,
        "record": pred["record"], "record_sha256": pred["record_sha256"],
        "questions_from": pre["record"],
        "questions_sha256": pre["record_sha256"],
        "predictions": pred,
        # The store's real path, for the assembler's own hash verification.
        # Redacted to `<store>` before anything is committed: this file is an
        # artefact under <out>, not a committed one.
        "store": str(store),
        "reads_dir": str(reads_dir),
    }
    (out / "e12p-reads.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    emit({name: {"value": c["value"], "n": c["n"], "dropped": c["dropped"],
                 "claims": c.get("claims") or
                 {t["id"]: t["ok"] for t in c.get("triples", [])}}
          for name, c in cells.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
