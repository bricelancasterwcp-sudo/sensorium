"""E12's thirteen reads, and the five endpoints read off them.

    .venv/bin/python typescript/acceptance/e12_report.py <store> <arms> <out>

Nothing here records. The store is opened for READING only: the thirteen
commands of the record's §1.5 are run once each, in §1.5's order, their
transcripts saved raw and redacted, and H1, H2, H4, H5 and H6 are read off
those saved texts and off the two traces the arms left behind.

EVERY EXPECTATION IS READ FROM §1, NEVER TYPED HERE
---------------------------------------------------
`section1()` cuts the record's locked §1 out of the record file and the
readers below take the subject, the three focus specs, the refusal sentence,
§1.2's three `watch` triples, §1.3's two sightings, §1.4's two identity lines
and §1.5's thirteen commands out of it. A constant typed into an instrument
is a second pre-registration nobody locked, and the whole point of the byte
lock on §1 is that there is only one.

The two run ids do not exist until the arms have run: `U1` and `F1` in §1.5's
list stand for them and are substituted here from `arms.jsonl`, which is what
§1.5 itself says happens.

ONE ORDER CHANGE, AND WHY
-------------------------
§1.5 lists `flow F1 --object e<id>:dice` ninth and `grep F1 dice --kind LINE`
tenth, and §1.4 makes the grep the LOOKUP that produces `e<id>`. Both cannot
be honoured: the ninth command's argument is the tenth command's answer. The
grep therefore runs at its lookup position, immediately before the flow, and
the other eleven keep §1.5's order. The SET and the COUNT are §1.5's, which
is what the journal's pre-registered delta is about; the swap is recorded in
the record's §2.3 before any number was read.

WHAT A MISSING LOOKUP DOES
--------------------------
If §1.4's lookup finds no row, `flow --object` is NOT run: an event id this
rung invented is not a lookup. H6 is then a null cell naming why, and the
journal's delta is twelve rather than thirteen -- which the assembler reports
as the arithmetic it is. Nothing is substituted to keep a count round.
"""
import hashlib
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from pathlib import Path

from lens import REPO_ROOT, cell, emit, sensorium_bin, usage

#: The record whose §1 is the locked contract every expectation is read from.
RECORD = (REPO_ROOT / "docs" / "superpowers" / "acceptance"
          / "2026-09-11-sensorium-s5-rung4-focus.md")


def record_path() -> Path:
    """The record §1 is read from -- the rung's own, or a DRY RUN's.

    `E12_RECORD` points a dry run at a scratch §1 written for the probe
    project, so the readers, the thirteen reads, the lookup and the journal
    arithmetic are all exercised end to end before the session starts. It is
    not a hole in the pre-registration: `e12-reads.json` records which file
    was read AND its sha256, and `assemble_rung4.py` refuses to assemble a
    record whose §1 is not the one the reads were taken against."""
    return Path(os.environ["E12_RECORD"]) if os.environ.get("E12_RECORD") \
        else RECORD

#: A read row as every listing command prints it:
#: `e11 LINE    loopCounter L43  total=3`, optionally `   [local total]`.
ROW = re.compile(r"^\s*(?:HIT\s+)?e(?P<eid>\d+) (?P<kind>[A-Z]+)\s+"
                 r"(?P<qual>\S+)(?: L(?P<line>\d+))?(?:\s\s(?P<rest>.*))?$")

#: `flow`'s trailing label list: `   [local total]`, `   [arg formula]`.
LABELS = re.compile(r"\[([^\]]*)\]\s*$")

#: The environment the driver owns; inherited, it would focus or spool a read.
SCRUB = ("SENSORIUM_FOCUS", "SENSORIUM_SPOOL", "SENSORIUM_MANIFEST_DIR")


# -- §1, read ---------------------------------------------------------------


def section1(text: str) -> str:
    """The record's §1, byte-for-byte, from `## 1.` to `## 2.`."""
    start = text.index("## 1. Pre-registration")
    return text[start:text.index("\n## 2.", start)]


def one(pattern: str, s1: str, what: str, group: int = 1) -> str:
    m = re.search(pattern, s1, re.S)
    if not m:
        usage(f"§1 does not carry {what} where this instrument reads it "
              f"({pattern!r}); the record and the instrument have parted "
              "company and no number may be read until they agree")
    return m.group(group)


#: A markdown table splits on `|`, EXCEPT the `\|` a cell uses to hold a
#: literal pipe -- the hand count's row 3 (`let m: RegExpExecArray \| null;`)
#: is exactly that, and a naive split read it as two columns and shifted
#: every prediction on the row by one.
CELL_SPLIT = re.compile(r"(?<!\\)\|")


def table_cells(line: str) -> list[str]:
    """One markdown table row as its cells, escaped pipes restored."""
    body = line.strip()
    if not body.startswith("|"):
        return []
    return [c.strip().replace("\\|", "|")
            for c in CELL_SPLIT.split(body.strip("|"))]


def subsection(s1: str, heading: str) -> str:
    """One `### x.y` sub-section of §1, whole, to the next `###` or the end.

    A `\n\n`-terminated slice would stop at the blank line that follows the
    heading itself, which is how the first draft of this reader read §1.2's
    table as empty -- and an empty prediction table is a cell that passes
    because it asked nothing."""
    start = s1.index(heading)
    rest = s1.find("\n### ", start + len(heading))
    return s1[start:] if rest == -1 else s1[start:rest]


def read_commands(s1: str) -> list[str]:
    """§1.5's fenced list, one command per line, in the order it is written."""
    block = one(r"### 1\.5 The read commands.*?```\n(.*?)```", s1,
                "§1.5's fenced command list")
    return [ln.strip() for ln in block.splitlines() if ln.strip()]


def focus_specs(s1: str) -> list[str]:
    """The three `--focus` specs, deduplicated, in the order §1 writes them.

    §1 also writes `--focus diceQueue.ts:<each of the three>` in the verbatim
    spec block, whose `<each` is not a spec, and the last of the three is
    followed immediately by the closing backtick of its sentence; the shape
    the pattern matches drops the first and does not swallow the second."""
    seen = []
    for spec in re.findall(r"--focus ([\w./-]+:[\w.]+)", s1):
        if spec not in seen:
            seen.append(spec)
    return seen


def triples(s1: str) -> list[dict]:
    """§1.2's three `watch` rows: `--at`, `--expr`, the verdict word, exit."""
    out = []
    for line in subsection(s1, "### 1.2 ").splitlines():
        cells = table_cells(line)
        if len(cells) >= 6 and re.fullmatch(r"W\d", cells[0]):
            out.append({"id": cells[0], "at": cells[1].strip("`"),
                        "expr": cells[2].strip("`"),
                        "verdict": cells[3].strip("`*"),
                        "exit": int(cells[4].strip("`")),
                        "reading": cells[5]})
    return out


def sightings(s1: str) -> list[dict]:
    """§1.3's two rows: the command, the literal, the name and the line."""
    out = []
    for line in subsection(s1, "### 1.3 ").splitlines():
        cells = table_cells(line)
        if len(cells) >= 5 and re.fullmatch(r"S\d", cells[0]):
            out.append({"id": cells[0], "command": cells[1].strip("`"),
                        "literal": cells[2].strip("`"),
                        "name": cells[3].strip("`"),
                        "line": int(cells[4].strip("`").rsplit(":", 1)[1])})
    return out


def preregistration() -> dict:
    """Everything §1 tells this instrument, read once, before anything runs."""
    path = record_path()
    s1 = section1(path.read_text(encoding="utf-8"))
    refusals = {m for m in re.findall(r"`(REFUSED: watch needs line[^`]*)`", s1)}
    if len(refusals) != 1:
        usage("§1 carries " + str(len(refusals)) + " distinct spellings of "
              "H1's refusal sentence; one is what this instrument reads")
    return {
        "record": str(path),
        "record_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "subject": one(r"\*\*The subject:\*\* `([^`]+)`", s1, "the subject"),
        "module": one(r"three pure functions of\s+`([^`]+)`", s1,
                      "the module the three functions live in"),
        "specs": focus_specs(s1),
        "refusal": refusals.pop(),
        "line_rows_when_unfocused": int(one(r"LINE rows\s*=?\s*(\d+)", s1,
                                            "H1's LINE-row count")),
        "triples": triples(s1),
        "while_line": int(one(r"no HIT at line (\d+)", s1,
                              "the `while` statement's line")),
        "sightings": sightings(s1),
        "identity": {
            "callee": one(r"the first LINE row of `([\w.]+)` carrying", s1,
                          "the function §1.4's lookup greps in"),
            "name": one(r"the first LINE row of `[\w.]+` carrying `([\w.]+)`",
                        s1, "the name §1.4's lookup greps for"),
            "caller": one(r"that `([\w.]+)` called", s1,
                          "the activation's caller (ruling R8)"),
            "lines": [
                int(one(r"exactly two sightings\*\*\s*—\s*the\s+"
                        r"`[^`]*?:(\d+)`\s+row and the\s+`[^`]*?:(\d+)`",
                        s1, "§1.4's two identity lines", g)) for g in (1, 2)],
        },
        "call_first_line": one(r"--kind CALL` prints\s+`([^`]+)` first", s1,
                               "H2's third reading"),
        "commands": read_commands(s1),
    }


# -- the store, read --------------------------------------------------------


def db(store: Path, run_id: str) -> sqlite3.Connection:
    """One trace, opened READ-ONLY: the hash list is verified after the reads
    and an instrument that could write to a trace could move a hash."""
    path = store / "traces" / f"{run_id}.db"
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def meta(conn) -> dict:
    """The trace's meta, decoded: every value is stored JSON-encoded."""
    return {k: json.loads(v)
            for k, v in conn.execute("SELECT key, value FROM meta")}


def argv_of(line: str, expr_flag: str = "--expr") -> list[str]:
    """One §1.5 line as argv. `--expr` takes the REST of the line as ONE
    argument: §1.5 writes the predicate unquoted (`--expr groups == 0`) and
    says each `--expr` is one shell argument, so a plain `shlex.split` would
    hand `watch` three arguments and a usage error."""
    cut = line.find(expr_flag + " ")
    if cut == -1:
        return shlex.split(line)
    return (shlex.split(line[:cut])
            + [expr_flag, line[cut + len(expr_flag) + 1:].strip()])


def slug(line: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", line).strip("-")[:70]


class Reads:
    """The thirteen commands, run once each, saved raw and redacted."""

    def __init__(self, store: Path, out: Path, pairs):
        self.store, self.out, self.pairs = store, out, pairs
        self.raw = out / "reads"
        self.red = out / "reads-redacted"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.red.mkdir(parents=True, exist_ok=True)
        self.log: list[dict] = []
        self.bin = sensorium_bin()

    def redact(self, text: str) -> str:
        for needle, label in self.pairs:
            if needle:
                text = text.replace(needle.rstrip("/"), label)
        return text

    def run(self, label_line: str, argv: list[str]) -> dict:
        """One read, saved raw and redacted.

        `label_line` is §1.5's own line with `U1`/`F1` left standing -- two
        run ids in a transcript header are noise a reader has to look up --
        but with `e<id>` REPLACED by the id the lookup produced, because
        that one substitution is the whole of §1.4 and a header that hid it
        would leave the reader unable to say which event was followed."""
        env = {k: v for k, v in os.environ.items() if k not in SCRUB}
        env["SENSORIUM_DIR"] = str(self.store)
        proc = subprocess.run([self.bin] + argv, capture_output=True,
                              text=True, env=env)
        nn = f"{len(self.log) + 1:02d}"
        body = (f"$ sensorium {label_line}\n" + proc.stdout + proc.stderr
                + f"--- exit {proc.returncode}\n")
        name = f"{nn}-{slug(label_line)}.txt"
        (self.raw / name).write_text(body, encoding="utf-8")
        (self.red / name).write_text(self.redact(body), encoding="utf-8")
        row = {"n": nn, "as_written": label_line,
               "argv": argv, "exit": proc.returncode, "transcript": name,
               "stdout": proc.stdout, "stderr": proc.stderr}
        self.log.append(row)
        return row


# -- the endpoints ----------------------------------------------------------


def rows_of(text: str) -> list[dict]:
    """Every event row a listing command printed, parsed."""
    out = []
    for line in text.splitlines():
        m = ROW.match(line.rstrip())
        if not m:
            continue
        rest = (m.group("rest") or "").strip()
        labels = LABELS.search(line)
        out.append({"eid": int(m.group("eid")), "kind": m.group("kind"),
                    "qualname": m.group("qual"),
                    "line": int(m.group("line")) if m.group("line") else None,
                    "rest": rest, "hit": line.strip().startswith("HIT"),
                    "labels": [s.strip() for s in
                               labels.group(1).split(",")] if labels else [],
                    "text": line.strip()})
    return out


def h1(pre: dict, u1: str, store: Path, refusal_read: dict) -> dict:
    """H1: does an unfocused run stay unfocused?"""
    conn = db(store, u1)
    m = meta(conn)
    caps = m.get("capabilities") or {}
    recorder = m.get("recorder")
    lines = conn.execute(
        "SELECT count(*) FROM events WHERE kind='LINE'").fetchone()[0]
    conn.close()
    printed = refusal_read["stdout"].splitlines()
    first = printed[0] if printed else ""
    want = pre["line_rows_when_unfocused"]
    claims = {
        "capabilities.line is false": caps.get("line") is False,
        "capabilities.locals is false": caps.get("locals") is False,
        f"LINE rows = {want}": lines == want,
        "watch refuses in §1's words, exit 3":
            first == pre["refusal"] and refusal_read["exit"] == 3,
    }
    # The second reading: the version token in the refusal is the trace's own
    # `recorder`, not a string §1 and the reader happen to share.
    token = re.search(r"which recorder (.+?) declares", first)
    return cell(sum(1 for v in claims.values() if v), len(claims), [],
                rule=("capabilities line/locals false, LINE rows 0, watch "
                      "REFUSED with exit 3 -> else STOP"),
                claims=claims, capabilities=caps, line_rows=lines,
                refusal_printed=first, refusal_expected=pre["refusal"],
                refusal_exit=refusal_read["exit"],
                second_reading={"trace.recorder": recorder,
                                "token in the refusal":
                                    token.group(1) if token else None,
                                "equal": bool(token)
                                         and token.group(1) == recorder},
                recorder=os.environ.get("E12_RECORDER"),
                recorder_rev=os.environ.get("E12_REV"))


def h2(pre: dict, arms: list[dict], store: Path, f1: str, call_read: dict,
       resolve_json: Path) -> dict:
    """H2: does a focus resolve and run?

    The resolver's answer is `e12.sh`'s own timed run of `resolve.mjs`, which
    sits beside `arms.jsonl` because one session wrote both."""
    resolver = (json.loads(resolve_json.read_text(encoding="utf-8"))
                if resolve_json.is_file() else {})
    matched = [f"{m['rel']}:{m['qualname']}" for m in resolver.get("matched", [])]
    want = [f"{pre['module']}:{spec.split(':', 1)[1]}" for spec in pre["specs"]]
    u1row = next(r for r in arms if r["arm"] == "U" and r["run"] == 1)
    f1row = next(r for r in arms if r["arm"] == "F" and r["run"] == 1)
    printed = [ln for ln in call_read["stdout"].splitlines() if ln.strip()]
    first = printed[0].strip() if printed else ""
    conn = db(store, f1)
    m = meta(conn)
    focus_matched = m.get("focus_matched") or []
    functions_focused = m.get("functions_focused")
    conn.close()
    claims = {
        "the resolver names exactly the three sites":
            sorted(matched) == sorted(want),
        "F1's `Test Files` line equals U1's":
            f1row["test_files_line"] == u1row["test_files_line"]
            and u1row["test_files_line"] is not None,
        "F1's `Tests` line equals U1's":
            f1row["tests_line"] == u1row["tests_line"]
            and u1row["tests_line"] is not None,
        "`grep --kind CALL` prints §1's line first":
            first.startswith(pre["call_first_line"])
            or pre["call_first_line"] in first,
    }
    return cell(sum(1 for v in claims.values() if v), len(claims), [],
                rule=("three sites named, the suite's counts unmoved, the "
                      "focused CALL printed as §1 writes it -> else STOP"),
                claims=claims, resolver_matched=matched, expected=want,
                unmatched=resolver.get("unmatched"),
                suite={"U1": {"files": u1row["test_files_line"],
                              "tests": u1row["tests_line"],
                              "exit": u1row["exit"]},
                       "F1": {"files": f1row["test_files_line"],
                              "tests": f1row["tests_line"],
                              "exit": f1row["exit"]}},
                call_first_line=first,
                # R22/R31, reported beside the gate: the invocation's matched
                # specs and this container's transform tally are two facts,
                # and `info` folds the second away only when they agree.
                r22_r31={"meta.functions_focused": functions_focused,
                         "len(meta.focus_matched)": len(focus_matched),
                         "focus_matched": focus_matched,
                         "equal": functions_focused == len(focus_matched)},
                recorder=os.environ.get("E12_RECORDER"),
                recorder_rev=os.environ.get("E12_REV"))


def h4(pre: dict, reads: list[dict]) -> dict:
    """H4: does `watch` answer? Three triples, §1.2's."""
    per = []
    for want, got in zip(pre["triples"], reads):
        text = got["stdout"]
        verdict = next((ln for ln in text.splitlines()
                        if ln.startswith("verdict:")), "")
        said = want["verdict"] in verdict
        hits = [r for r in rows_of(text) if r["hit"]]
        at_while = [r for r in hits if r["line"] == pre["while_line"]]
        extra = ("no HIT at line " + str(pre["while_line"])) in want["reading"] \
            or "no HIT row at" in want["reading"]
        ok = said and got["exit"] == want["exit"] and (not extra or not at_while)
        per.append({**want, "verdict_line": verdict, "got_exit": got["exit"],
                    "verdict_word_seen": said, "hits": [r["text"] for r in hits],
                    "hit_at_while_line": [r["text"] for r in at_while],
                    "extra_clause_applies": extra,
                    "sites_line": next((ln for ln in text.splitlines()
                                        if ln.startswith("sites:")), None),
                    "not_captured": next((ln for ln in text.splitlines()
                                          if ln.startswith("not captured")), None),
                    "ok": ok})
    return cell(sum(1 for t in per if t["ok"]), len(pre["triples"]), [],
                rule=("all three triples as §1.2 predicts (verdict word, exit, "
                      "and W2's no-HIT clause) -> PASS; a verdict/exit "
                      "disagreement is a finding, reported"),
                triples=per,
                recorder=os.environ.get("E12_RECORDER"),
                recorder_rev=os.environ.get("E12_REV"))


def h5(pre: dict, reads: list[dict], focused: set) -> dict:
    """H5: does `flow --value` see it? Two sightings, §1.3's."""
    found, elsewhere, unpredicted = [], [], []
    for want, got in zip(pre["sightings"], reads):
        rows = rows_of(got["stdout"])
        pop, out, names = [], [], set()
        for r in rows:
            # The gated population is §1.3's: the LINE `deltas` and the CALL
            # `args` of the three functions §1 names. `flow` labels a
            # sighting `[local <name>]`, `[arg <name>]` or `[return]`, and a
            # row can carry several -- one object sighted under two names --
            # so every label is read, not just the first.
            mine = [l for l in r["labels"]
                    if (r["kind"] == "LINE" and l.startswith("local "))
                    or (r["kind"] == "CALL" and l.startswith("arg "))]
            if r["qualname"] in focused and mine:
                pop.append(r)
                names |= {(l.split(" ", 1)[1], r["line"]) for l in mine}
            else:
                out.append(r)
        triples_seen = sorted(names)
        hit = [t for t in triples_seen if t == (want["name"], want["line"])]
        found.append({**want, "seen": bool(hit),
                      "in_population": [r["text"] for r in pop],
                      "triples_in_population": [list(t) for t in triples_seen],
                      "sightings_line": next(
                          (ln for ln in got["stdout"].splitlines()
                           if ln.startswith("sightings:")), None),
                      "exit": got["exit"]})
        unpredicted += [list(t) for t in triples_seen
                        if t != (want["name"], want["line"])]
        elsewhere += [r["text"] for r in out]
    claims = {f"{s['id']} found": s["seen"] for s in found}
    claims["no unpredicted triple in the focused population"] = not unpredicted
    return cell(sum(1 for v in claims.values() if v), len(claims), [],
                rule=("both sightings found and no third triple in the three "
                      "focused functions' LINE deltas and CALL args -> PASS; "
                      "sightings elsewhere reported, not gated"),
                claims=claims, sightings=found, unpredicted=unpredicted,
                elsewhere_not_gated=elsewhere, focused_functions=sorted(focused),
                recorder=os.environ.get("E12_RECORDER"),
                recorder_rev=os.environ.get("E12_REV"))


def lookup(pre: dict, store: Path, f1: str, grep_read: dict) -> dict:
    """§1.4's lookup, run on the grep this rung already printed (ruling R8).

    The first LINE row of the callee carrying the name, restricted to the
    activation the named caller made -- a fact the printed row cannot carry,
    so the frame's parent is read from the trace beside it."""
    want_line = pre["identity"]["lines"][0]
    rows = [r for r in rows_of(grep_read["stdout"])
            if r["qualname"] == pre["identity"]["callee"]
            and r["line"] == want_line]
    conn = db(store, f1)
    parents = {}
    for r in rows:
        got = conn.execute(
            "SELECT c.qualname FROM events e JOIN frames f ON f.id = e.frame_id "
            "JOIN frames p ON p.id = f.parent_id "
            "JOIN code_objects c ON c.id = p.code_id WHERE e.id = ?",
            (r["eid"],)).fetchone()
        parents[r["eid"]] = got[0] if got else None
    conn.close()
    called = [r for r in rows if parents[r["eid"]] == pre["identity"]["caller"]]
    return {"rows_at_line": [r["text"] for r in rows], "parents": parents,
            "called_by_the_caller": [r["text"] for r in called],
            "eid": called[0]["eid"] if called else None}


def h6(pre: dict, store: Path, f1: str, look: dict, flow_read) -> dict:
    """H6: is identity exact?"""
    if flow_read is None:
        return cell(None, 4, [
            "§1.4's lookup found no LINE row of "
            f"{pre['identity']['callee']} carrying "
            f"{pre['identity']['name']} at line {pre['identity']['lines'][0]} "
            f"in an activation {pre['identity']['caller']} called, so "
            "`flow --object` was never run: an event id this rung invented "
            "would not be a lookup"], lookup=look,
            recorder=os.environ.get("E12_RECORDER"),
            recorder_rev=os.environ.get("E12_REV"))
    text = flow_read["stdout"]
    head = re.search(r"flow of object #(\d+) \(([^)]*)\)", text)
    rows = rows_of(text)
    got_lines = [r["line"] for r in rows]
    conn = db(store, f1)
    types = {}
    for r in rows:
        payload = conn.execute("SELECT payload FROM events WHERE id = ?",
                               (r["eid"],)).fetchone()
        body = json.loads(payload[0]) if payload and payload[0] else {}
        for bucket in ("deltas", "args"):
            for name, v in (body.get(bucket) or {}).items():
                if isinstance(v, dict) and v.get("oid") is not None:
                    types[f"e{r['eid']}:{name}"] = {"oid": v["oid"],
                                                    "type": v.get("type")}
    conn.close()
    target_oid = int(head.group(1)) if head else None
    mine = {k: v for k, v in types.items() if v["oid"] == target_oid}
    covered = {int(k[1:].split(":", 1)[0]) for k in mine}
    claims = {
        "exactly two sightings, at §1.4's two lines":
            got_lines == pre["identity"]["lines"],
        # One serial: every printed sighting is a capture of THAT serial, and
        # the target has one. A row the target's oid does not cover would be
        # a second identity printed under one flow.
        "one serial": target_oid is not None and bool(rows)
                      and covered == {r["eid"] for r in rows},
        "continuity: exact (serial identity)":
            "continuity: exact (serial identity)" in text,
        "both sightings' type is Array":
            len(mine) == 2 and all(v["type"] == "Array" for v in mine.values()),
    }
    return cell(sum(1 for v in claims.values() if v), len(claims), [],
                rule=("exactly two sightings, one serial, continuity exact, "
                      "both types Array -> PASS"),
                claims=claims, lookup=look, target=head.group(0) if head else None,
                sighting_lines=got_lines, sightings=[r["text"] for r in rows],
                sightings_line=next((ln for ln in text.splitlines()
                                     if ln.startswith("sightings:")), None),
                captures=types, exit=flow_read["exit"],
                recorder=os.environ.get("E12_RECORDER"),
                recorder_rev=os.environ.get("E12_REV"))


# -- the session ------------------------------------------------------------


def journal_lines(store: Path) -> int:
    path = store / "invocations.jsonl"
    if not path.is_file():
        return 0
    return sum(1 for _ in path.open("rb"))


def run_all(pre: dict, store: Path, out: Path, u1: str, f1: str,
            pairs) -> tuple:
    """The thirteen, in §1.5's order but with the lookup before its flow."""
    reads = Reads(store, out, pairs)
    lines = list(pre["commands"])
    grep_line = next(ln for ln in lines if ln.startswith("grep ")
                     and f"{pre['identity']['name']} --kind LINE" in ln)
    flow_line = next(ln for ln in lines if "--object" in ln)
    ordered = []
    for line in lines:
        if line == grep_line:
            continue                       # it runs at its lookup position
        if line == flow_line:
            ordered.append(grep_line)
        ordered.append(line)

    by_line: dict[str, dict] = {}
    look = None
    for line in ordered:
        argv = argv_of(line.replace("U1", u1).replace("F1", f1))
        label = line
        if line == flow_line:
            look = lookup(pre, store, f1, by_line[grep_line])
            if look["eid"] is None:
                continue
            argv = [a.replace("e<id>", f"e{look['eid']}") for a in argv]
            label = line.replace("e<id>", f"e{look['eid']}")
        by_line[line] = reads.run(label, argv)
    return reads, by_line, look, grep_line, flow_line


def main(argv) -> int:
    if len(argv) != 4:
        usage("usage: e12_report.py <store> <arms> <out dir>")
    store, arms_path, out = Path(argv[1]), Path(argv[2]), Path(argv[3])
    out.mkdir(parents=True, exist_ok=True)
    pre = preregistration()
    arms = [json.loads(ln) for ln in arms_path.read_text(encoding="utf-8")
            .splitlines() if ln.strip()]
    ids = {}
    for arm in ("U", "F"):
        row = next((r for r in arms if r["arm"] == arm and r["run"] == 1), None)
        if row is None or not row.get("run_id"):
            usage(f"arms.jsonl carries no single run id for {arm}1; §1.5's "
                  "`U1`/`F1` stand for the two run ids and there is no other "
                  "place to read them from")
        ids[arm] = row["run_id"]
    u1, f1 = ids["U"], ids["F"]

    conn = db(store, f1)
    lens_root = meta(conn).get("cwd", "")
    conn.close()
    pairs = sorted([(str(store), "<store>"), (lens_root, "<lens>"),
                    (str(REPO_ROOT), "<repo>"), (str(Path.home()), "<home>")],
                   key=lambda p: len(p[0]), reverse=True)

    before = journal_lines(store)
    reads, by_line, look, grep_line, flow_line = run_all(
        pre, store, out, u1, f1, pairs)
    after = journal_lines(store)

    # Matched by the words §1 writes, never by position: a triple read
    # against the wrong transcript is the one mistake this cell cannot see.
    watch_lines = [next(ln for ln in pre["commands"]
                        if ln.startswith("watch F1") and ln.endswith(t["expr"]))
                   for t in pre["triples"]]
    flow_value_lines = [s["command"] for s in pre["sightings"]]
    call_line = next(ln for ln in pre["commands"] if "--kind CALL" in ln)
    refusal_line = next(ln for ln in pre["commands"] if ln.startswith("watch U1"))
    focused = {spec.split(":", 1)[1] for spec in pre["specs"]}

    cells = {
        "H1": h1(pre, u1, store, by_line[refusal_line]),
        "H2": h2(pre, arms, store, f1, by_line[call_line],
                 arms_path.parent / "resolve.json"),
        "H4": h4(pre, [by_line[ln] for ln in watch_lines]),
        "H5": h5(pre, [by_line[ln] for ln in flow_value_lines], focused),
        "H6": h6(pre, store, f1, look, by_line.get(flow_line)),
    }
    payload = {
        "cells": cells,
        "run_ids": {"U1": u1, "F1": f1},
        "commands_as_written": pre["commands"],
        "commands_run": [{k: v for k, v in r.items()
                          if k not in ("stdout", "stderr")}
                         for r in reads.log],
        "order_change": (f"{grep_line!r} runs before {flow_line!r}: §1.4 makes "
                         "the grep the lookup that produces the flow's "
                         "argument. The set and the count are §1.5's"),
        "journal": {"before_reads": before, "after_reads": after,
                    "delta": after - before,
                    "commands_in_section_1_5": len(pre["commands"])},
        "transcripts": {"raw": str(reads.raw.relative_to(out)),
                        "redacted": str(reads.red.relative_to(out))},
        "record": pre["record"], "record_sha256": pre["record_sha256"],
        "preregistration": {k: v for k, v in pre.items() if k != "commands"},
    }
    (out / "e12-reads.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    emit({name: {"value": c["value"], "n": c["n"], "dropped": c["dropped"]}
          for name, c in cells.items()} | {"journal": payload["journal"]})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
