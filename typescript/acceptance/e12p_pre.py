"""§1, read: what this slice's record PREDICTS, and the hashes it pins.

The half of E12′ that reads the RECORD rather than the data.
`e12p_report.py` is the half that reads the data, and it imports this; the
two are separate files because one of them is about what was written down
before any number existed and the other about what the bytes say, and
because `tests/test_ceiling.py` holds this directory's files under 800 lines.

Controller ruling P1 is what this file exists to honour: every number E12′
compares against is parsed out of
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md`'s own §1
text, the way `e12_report.one()` parses rung 4's. A constant typed into an
instrument is a second pre-registration nobody locked -- and §1 of that
record is byte-locked by `tests/test_acceptance_s5_debts_lock.py`, so there
is exactly one.

§1.1's hashes are checked here too, and they are checked FIRST: a reading
taken off data the record does not describe is not the reading §1
pre-registers, which is why `main` makes a mismatch exit 4 and no number.
"""
import hashlib
import itertools
import re
import subprocess
from pathlib import Path

from e12_report import one, section1, subsection, table_cells, usage


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

#: Spelled-out counts, for the one number §1.1 writes as a word ("its first
#: six lines"). A spelling table, not a prediction: the count itself is read
#: from the record.
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "thirteen": 13}

#: The one entry of the hashed set rung 4's own reads appended to.
JOURNAL = "invocations.jsonl"



# -- §1 of THIS record: the predicted numbers -------------------------------


def _rel(path: Path) -> str:
    """A path as the repository spells it, or its basename when it is not in
    the tree. A committed instrument names no box path, so a record a dry run
    points at from a scratch directory is cited by name and never by where it
    happened to sit."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return path.name


def handcount_rows() -> list[dict]:
    """§1.2's hand count, one dict per site.

    Rows are split on UNESCAPED pipes -- `table_cells`' rule, which is the
    lock test's -- so a cell holding a literal `|` keeps its column.
    """
    out = []
    for line in HANDCOUNT.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| \d+ \|", line):
            continue
        cells = table_cells(line)
        out.append({"n": int(cells[0]), "qualname": cells[1].strip("`"),
                    "line": int(cells[2]), "kind": cells[3],
                    "how": cells[4]})
    return out


def _triple_predictions(s13: str) -> list[dict]:
    """§1.3's three `watch` rows, each number matched by the WORDS beside it.

    Never by position: W1 carries two numbers, W2 four and W3 one, and a
    reader that took "the second bold number" would silently give W3 W2's
    reading the day a row gained a clause.
    """
    out = []
    for line in s13.splitlines():
        cells = table_cells(line)
        if len(cells) < 3 or not re.fullmatch(r"W\d", cells[0]):
            continue
        said = cells[2]

        def group(pattern, text=said):
            m = re.search(pattern, text)
            return m.group(1) if m else None

        def num(pattern):
            got = group(pattern)
            return int(got) if got is not None else None

        carried = group(r"`unbound:([\w,]+)`")
        out.append({
            "id": cells[0], "expr": cells[1].strip("`"),
            "hits": num(r"\*\*(\d+)\*\* HITs"),
            "evaluated": num(r"of \*\*(\d+)\*\* evaluable sites"),
            "on_completion_rows": num(
                r"of which \*\*(\d+)\*\* sit on a row whose `unbound` names"),
            # The NAME §1.3's W2 clause is about ("a row whose `unbound`
            # names `count`") and, for W3, the names its rows must carry.
            "unbound_name": group(r"whose `unbound` names `(\w+)`"),
            "unbound_carried": carried.split(",") if carried else None,
            "at_line_count": num(r"and \*\*(\d+)\*\* sit at line"),
            "line": num(r"sit at line (\d+)") or num(r"all at line (\d+)"),
            "reading": said})
    return out


def predictions() -> dict:
    """Every number §1.2-§1.4 of THIS record pre-registers, read from it.

    Controller ruling P1: a constant typed into an instrument is a second
    pre-registration nobody locked. Each value below is a regex over the
    record's own §1 text, so the cell compares what the instrument READ
    against what §1 SAYS and an edit to either shows up in the JSON.
    """
    text = RECORD.read_text(encoding="utf-8")
    s1 = section1(text)
    two, three = subsection(s1, "### 1.2 "), subsection(s1, "### 1.3 ")
    four = subsection(s1, "### 1.4 ")
    suite_quoted = re.findall(r"`([^`]*(?:Test Files|Tests  )[^`]*)`", two, re.S)
    return {
        "record": _rel(RECORD),
        "record_sha256": hashlib.sha256(RECORD.read_bytes()).hexdigest(),
        "handcount": _rel(HANDCOUNT),
        "handcount_sha256": hashlib.sha256(HANDCOUNT.read_bytes()).hexdigest(),
        # §1.2 -- H2′
        "functions_focused": int(one(
            r"\*\*The count \(the gate\): N = (\d+)\.\*\*", two,
            "§1.2's gate count")),
        "focus_matched": int(one(r"`meta\.focus_matched` = (\d+)", two,
                                 "§1.2's `focus_matched`")),
        "shared_qualname": one(
            r"the one\s+qualname two sites share is `([^`]+)`", two,
            "§1.2's shared qualname"),
        "suite_lines": suite_quoted,
        "call_first": one(r"printing\s+`([^`]+)` first", two,
                          "§1.2's first CALL row"),
        # §1.3 -- H4′
        "triples": _triple_predictions(three),
        # §1.4 -- H5′
        "s1_id": one(r"\*\*(S\d) found:\*\*\s+\*\*\d+\*\*", four,
                     "§1.4's counted sighting"),
        "s1_sightings": int(one(r"\*\*S\d found:\*\*\s+\*\*(\d+)\*\*", four,
                                "§1.4's S1 count")),
        "s2_id": one(r"\*\*(S\d) found:\*\* event", four,
                     "§1.4's event sighting"),
        "s2": {"eid": int(one(r"event \*\*`e(\d+)`\*\*", four, "§1.4's S2 id")),
               "kind": one(r"a \*\*([A-Z]+)\*\* row", four, "§1.4's S2 kind"),
               "qualname": one(r"qualname \*\*`([^`]+)`\*\*", four,
                               "§1.4's S2 qualname"),
               "line": int(one(r"and line \*\*(\d+)\*\*", four,
                               "§1.4's S2 line"))},
        "elsewhere_not_gated": int(one(
            r"\*\*`elsewhere_not_gated` = (\d+)\*\*", four, "§1.4's ungated")),
        "sightings_totals": [int(n) for n in re.findall(
            r"\*\*`sightings:\s*(\d+)`\*\*", four, re.S)],
        "unpredicted": int(one(r"\*\*`unpredicted` = (\d+)\*\*", four,
                               "§1.4's unpredicted count")),
    }


# -- §1.1: the hash preflight ----------------------------------------------


def _sha_rows(block: str) -> list[tuple[str, str]]:
    """A `sha256sum`-format block as `(digest, path)` pairs."""
    rows = []
    for line in block.splitlines():
        digest, _, name = line.strip().partition("  ")
        if digest and name:
            rows.append((digest.strip(), name.strip()))
    return rows


def hash_list() -> dict:
    """§1.1's two fenced blocks, and the journal head count it spells out.

    The first block is the thirteen transcripts, `git ls-files` order; the
    second is the store's own hash list, cited by its sha256. The journal
    head is written as a word ("its first six lines"), because §1.1 is prose;
    `NUMBER_WORDS` is the spelling table that reads it, not the number.
    """
    body = subsection(section1(RECORD.read_text(encoding="utf-8")), "### 1.1 ")
    blocks = re.findall(r"```\n(.*?)```", body, re.S)
    if len(blocks) != 2:
        usage(f"§1.1 carries {len(blocks)} fenced block(s) where this "
              "instrument reads two: the thirteen transcripts and the store's "
              "hash list. No number may be read until they agree")
    word = one(r"its first (\w+) lines", body, "§1.1's journal head count")
    if word not in NUMBER_WORDS:
        usage(f"§1.1 spells its journal head count {word!r}, which is not a "
              "number this instrument can read")
    return {"transcripts": _sha_rows(blocks[0]),
            "store_list": _sha_rows(blocks[1]),
            "journal_head": NUMBER_WORDS[word]}


def verify_transcripts(reads_dir: Path, listed: list[tuple[str, str]]) -> dict:
    """Every transcript §1.1 lists, hashed where it was handed in.

    §1.1 lists repo-relative paths; the directory is an argument so a dry run
    can point at a copy, and only the BASENAMES are taken from the list. An
    extra `.txt` in the directory is a failure too: a fourteenth transcript
    would be data this record does not describe.
    """
    checked, bad = [], []
    for digest, rel in listed:
        path = reads_dir / Path(rel).name
        got = (hashlib.sha256(path.read_bytes()).hexdigest()
               if path.is_file() else None)
        checked.append({"file": Path(rel).name, "listed": digest, "read": got})
        if got != digest:
            bad.append(f"{Path(rel).name}: {'absent' if got is None else got}"
                       f" != {digest}")
    extra = sorted({p.name for p in reads_dir.glob("*.txt")}
                   - {Path(rel).name for _, rel in listed})
    bad += [f"{name}: in the reads directory and not in §1.1" for name in extra]
    return {"ok": not bad, "why": bad, "checked": checked, "extra": extra,
            "listed": len(listed)}


def verify_store(store: Path, listed: list[tuple[str, str]],
                 journal_head: int) -> dict:
    """The store, against the hash list §1.1 cites by sha256.

    Twelve of the thirteen must verify plainly. The thirteenth,
    `invocations.jsonl`, is checked as an APPEND: rung 4's list was taken
    after its arms and BEFORE its reads, and the reads then wrote one journal
    line each, so a plain check on that entry is expected to fail and a
    PASSING one would mean the journal had been rewritten rather than
    appended to.
    """
    if len(listed) != 1:
        return {"ok": False, "why": ["§1.1's second block is not one line"]}
    digest, rel = listed[0]
    path = REPO / rel
    own = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() \
        else None
    why = []
    if own != digest:
        why.append(f"{Path(rel).name}: the store's hash list is {own}, and "
                   f"§1.1 cites {digest}")
    proc = subprocess.run(["sha256sum", "-c", str(path)], cwd=store,
                          capture_output=True, text=True)
    rows = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    failures = [ln for ln in rows if not ln.endswith(": OK")]
    unexpected = [ln for ln in failures if not ln.startswith(f"{JOURNAL}:")]
    why += [f"a hashed file moved: {ln}" for ln in unexpected]
    wanted = dict((name, d) for d, name in _sha_rows(
        path.read_text(encoding="utf-8")))
    head = None
    journal = store / JOURNAL
    if journal.is_file():
        with journal.open("rb") as fh:
            head = hashlib.sha256(
                b"".join(itertools.islice(fh, journal_head))).hexdigest()
    append_only = head is not None and head == wanted.get(JOURNAL)
    if not append_only:
        why.append(f"{JOURNAL} is not rung 4's file plus new lines: its first "
                   f"{journal_head} line(s) hash to {head}, and the list says "
                   f"{wanted.get(JOURNAL)}")
    return {"ok": not why, "why": why, "hash_list": Path(rel).name,
            "hash_list_sha256": own, "checked": len(rows),
            "verified": len(rows) - len(failures),
            "journal_append_only": append_only, "journal_head_lines":
                journal_head, "journal_head_sha256": head,
            "journal_listed_sha256": wanted.get(JOURNAL),
            "unexpected_failures": unexpected, "exit": proc.returncode}


def preflight(reads_dir: Path, store: Path) -> dict:
    """§1.1, whole, before any cell. A mismatch is exit 4 and no number."""
    listed = hash_list()
    transcripts = verify_transcripts(reads_dir, listed["transcripts"])
    saved = verify_store(store, listed["store_list"], listed["journal_head"])
    return {"ok": transcripts["ok"] and saved["ok"],
            "transcripts": transcripts, "store": saved,
            "record": _rel(RECORD),
            "record_sha256": hashlib.sha256(RECORD.read_bytes()).hexdigest()}
