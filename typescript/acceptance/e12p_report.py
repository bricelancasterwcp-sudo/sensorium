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
* **the PREDICTED NUMBERS** are this slice's, in `RECORD`'s §1.2-§1.4 --
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
import re
from pathlib import Path

from e12_report import LABELS, one, subsection

#: `typescript/acceptance/e12p_report.py` -> the repo root, the same two
#: parents up `lens.py` and `bin.sh` both spell.
REPO = Path(__file__).resolve().parents[2]

#: THIS slice's record: §1.1's hash list and §1.2-§1.4's predicted numbers.
#: The QUESTIONS are `e12_report.RECORD`'s, which is rung 4's own.
RECORD = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-12-sensorium-s5-rung4-debts.md")

#: H2′'s hand count, sha-pinned as §1's second-to-last line.
HANDCOUNT = (REPO / "docs" / "superpowers" / "acceptance"
             / "2026-09-12-sensorium-s5-rung4-debts-h2-handcount.md")

#: The rung-4 record's own results file: where the SUITE half of H2′ is read
#: from. The suite lines are not in any read transcript -- they are vitest's,
#: printed by the arms -- and rung 4 saved them in its H2 cell. §1.2 predicts
#: them "exactly as the rung-4 record's §4.2 quotes it", so the cell compares
#: the saved measurement against the record's quotation of it.
RUNG4_RESULTS = (REPO / "docs" / "superpowers" / "acceptance"
                 / "2026-09-11-sensorium-s5-rung4-focus.results.json")

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

#: Spelled-out counts, for the one number §1.1 writes as a word ("its first
#: six lines"). A spelling table, not a prediction: the count itself is read
#: from the record.
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "thirteen": 13}


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
