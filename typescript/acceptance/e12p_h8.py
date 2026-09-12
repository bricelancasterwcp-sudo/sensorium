"""H8′: §1.9's eight clauses, read off `e12p.sh`'s artefacts.

    .venv/bin/python typescript/acceptance/e12p_h8.py <out dir>

`e12p.sh` runs the lens once and writes down what happened; nothing there
judges anything. This reads those files into eight `{holds, evidence}` clauses
and one cell, `e12p-h8.json`.

THE CLAUSES ARE THE RECORD'S, ENUMERATED BY THE RECORD
------------------------------------------------------
§1.9 of `docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md`
is a `| # | clause |` table, and this file reads it: the clause NUMBERS, the
clause TEXT, and the literals inside the text (`748 OK / 0 FAILED`,
`focus matched: 5 … (6 functions)`, `26 passed (26)`) all come from there. A
threshold typed here would be a second pre-registration nobody locked, and a
clause added to §1.9 without a reader here fails loudly rather than silently
going unchecked.

CLAUSE 4, AND WHY IT IS TWO READINGS
------------------------------------
"H3's nine LINE rows are TEXT-equal to the rung-4 record's §1.1 hand count --
event ids may differ, the row text may not." The hand count is a table of
`| row | line | statement | deltas | unbound | rule |`, so "text-equal" is
read cell by cell: each printed row's `L<line>` against the table's `line`,
the names its deltas bind against the `deltas` cell, and the names it drops
against the `unbound` cell. Event ids are not compared, which is the
allowance the clause writes. The rows are parsed with `e12p_report.rows_of2`
-- the same parser E12′ uses, so H8′ and E12′ cannot disagree about what a
row says.

THE CENSUS COMPARER LIVES HERE
------------------------------
`census_matches` (controller ruling P3) is E13's first clause and not H8′'s,
but it is the same kind of reading as clause 4 -- a hand table against an
instrument's JSON -- so it lives beside it and `e13_report.py` imports it.
"""
import json
import os
import re
import sys
from pathlib import Path

from e12_report import cell, emit, subsection, table_cells, usage
from e12p_pre import RECORD, predictions, section1
from e12p_report import record_path, resolver_sites_in_record, rows_of2

#: The rung-4 hand count, whose nine rows clause 4 compares against. Pinned by
#: sha256 as the rung-4 record's §1's last line and recomputed by that rung's
#: lock test, so this file need not re-verify it.
RUNG4_HANDCOUNT = (RECORD.parent / "2026-09-11-sensorium-s5-rung4-handcount.md")

#: The census's table header, byte-locked at Task 0 (ruling P3).
CENSUS_HEADER = "| file | qualname | line |"

#: A delta prints as `name=<inspect text>`.
DELTA = re.compile(r"^\s*([A-Za-z_$][\w$]*)=")


# -- reading one printed row's deltas ---------------------------------------


def _top_level_parts(text: str) -> list[str]:
    """`text` split on the commas that are NOT inside brackets or quotes.

    A delta's own inspect text carries commas of its own (`m=[ '1d20', '1',
    …]`, `dice=[ { sides: 20 } ], skippedCount=0`), so a naive `split(", ")`
    would read six deltas off a row that binds one. Bracket depth and quote
    state are enough for every shape these transcripts print; a string
    literal containing an unbalanced bracket would defeat it, and that is
    written here rather than left for a reader to discover.
    """
    parts, depth, quote, start = [], 0, None, 0
    for i, ch in enumerate(text):
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def delta_names(row: dict) -> list[str]:
    """The names a printed row's deltas bind, in the order it printed them.

    Not the values: the hand count's `deltas` column is a list of NAMES, and
    a value is what the run computed rather than what the statement writes.
    The `unbound:` names, a `watch` HIT's `state:` tail and `flow`'s trailing
    `[local x]` label are cut first -- none of the three is a delta.
    """
    text = re.sub(r"\s+unbound:[\w$,]+", "", row.get("rest") or "")
    text = re.split(r"\s{2,}state:", text)[0]
    text = re.sub(r"\s*\[[^\]]*\]\s*$", "", text)
    return [m.group(1) for m in
            (DELTA.match(part) for part in _top_level_parts(text)) if m]


def handcount_rung4() -> list[dict]:
    """Rung 4's §1.1 hand count: the nine rows, by line, deltas and unbound.

    Split on UNESCAPED pipes (`table_cells`' rule, which is the lock test's):
    row 3's statement is `let m: RegExpExecArray \\| null;`, whose one pipe a
    markdown cell cannot hold bare.
    """
    def names(text: str) -> list[str]:
        return [] if text.strip() == "-" else [
            n.strip() for n in text.split(",") if n.strip()]

    rows = []
    for line in RUNG4_HANDCOUNT.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| \d+ \|", line):
            continue
        cells = table_cells(line)
        rows.append({"row": int(cells[0]), "line": int(cells[1]),
                     "statement": cells[2], "deltas": names(cells[3]),
                     "unbound": names(cells[4]), "rule": cells[5]})
    return rows


def nine_rows(frame_text: str) -> dict:
    """Clause 4: the frame's LINE rows against rung 4's hand count, cell by
    cell. Event ids are not compared; everything else is."""
    want = handcount_rung4()
    got = [r for r in rows_of2(frame_text) if r["kind"] == "LINE"]
    per, differences = [], []
    for i in range(max(len(want), len(got))):
        w = want[i] if i < len(want) else None
        g = got[i] if i < len(got) else None
        reading = {
            "row": i + 1,
            "expected": None if w is None else
                {"line": w["line"], "deltas": w["deltas"],
                 "unbound": w["unbound"], "statement": w["statement"]},
            "read": None if g is None else
                {"line": g["line"], "deltas": delta_names(g),
                 "unbound": g["unbound"], "text": g["text"]},
        }
        ok = (w is not None and g is not None
              and g["line"] == w["line"]
              and delta_names(g) == w["deltas"]
              and g["unbound"] == w["unbound"])
        reading["equal"] = ok
        if not ok:
            differences.append(reading)
        per.append(reading)
    return {"holds": not differences and len(got) == len(want),
            "n": len(want), "read": len(got), "rows": per,
            "differences": differences}


# -- the census comparer (ruling P3) ----------------------------------------


def census_tables(text: str) -> list[dict]:
    """The census's three tables, in file order, each with its `N =` line.

    A table is the `CENSUS_HEADER` line, its separator, zero or more data
    rows, and -- after whatever prose follows -- the next `N = <count>`. An
    EMPTY table is the point of two of the three, so "no data rows" is a
    shape this reads rather than a table it fails to find.
    """
    lines = text.splitlines()
    tables = []
    for i, line in enumerate(lines):
        if line.strip() != CENSUS_HEADER:
            continue
        heading = next((ln.lstrip("# ").strip() for ln in reversed(lines[:i])
                        if ln.startswith("## ")), f"table {len(tables) + 1}")
        rows = []
        for nxt in lines[i + 2:]:                       # skip the separator
            if not nxt.startswith("| "):
                break
            cells = table_cells(nxt)
            rows.append((cells[0].strip("`"), cells[1].strip("`"),
                         int(cells[2])))
        declared = next((int(ln.split("=")[1]) for ln in lines[i + 2:]
                         if re.fullmatch(r"N = \d+", ln.strip())), None)
        tables.append({"heading": heading, "rows": rows, "declared": declared})
    return tables


def census_matches(census_md, census_json) -> dict:
    """The hand census against `census_deferred.mjs`'s JSON, table by table.

    `census_md` is the sha-pinned hand table written at Task 0; `census_json`
    is the script's output, whose shape is::

        {"roots": [{"root": "<label>",
                    "deferred": [{"rel": "corpus/typescript/…/finally.ts",
                                  "qualname": "settle", "line": 7}, …],
                    "files_scanned": 12}, … three, in the table's order]}

    `rel` is spelled as the census table spells `file`: repository-relative
    for an in-tree root, and as the census writes it for the lens. The roots
    are matched BY POSITION because the record fixes the order (probes,
    corpus, lens) and a root's label is a path this slice does not commit.

    Returns `{holds, missing, extra, per_table}` -- `missing` is a triple the
    hand table names and the script did not print, `extra` the reverse, each
    tagged with the table it belongs to.
    """
    tables = census_tables(Path(census_md).read_text(encoding="utf-8"))
    body = json.loads(Path(census_json).read_text(encoding="utf-8"))
    roots = body.get("roots") if isinstance(body, dict) else body
    roots = roots or []
    missing, extra, per_table = [], [], {}
    for i, table in enumerate(tables):
        root = roots[i] if i < len(roots) else None
        printed = {(d["rel"], d["qualname"], int(d["line"]))
                   for d in (root or {}).get("deferred", [])}
        hand = set(table["rows"])
        gone = sorted(hand - printed)
        added = sorted(printed - hand)
        missing += [{"table": table["heading"], "triple": list(t)} for t in gone]
        extra += [{"table": table["heading"], "triple": list(t)} for t in added]
        per_table[table["heading"]] = {
            "hand": sorted(list(t) for t in hand),
            "printed": sorted(list(t) for t in printed),
            "declared_n": table["declared"],
            "hand_rows": len(hand),
            "files_scanned": (root or {}).get("files_scanned"),
            "root_present": root is not None,
            "equal": not gone and not added
                     and table["declared"] == len(hand) == len(printed),
        }
    holds = (bool(tables) and len(tables) == len(roots)
             and all(t["equal"] for t in per_table.values()))
    return {"holds": holds, "missing": missing, "extra": extra,
            "per_table": per_table, "tables": len(tables), "roots": len(roots)}


# -- §1.9's table, and the eight readers ------------------------------------


def clause_rows() -> list[dict]:
    """§1.9's `| # | clause |` table, in the order it is written."""
    body = subsection(section1(RECORD.read_text(encoding="utf-8")), "### 1.9 ")
    rows = []
    for line in body.splitlines():
        cells = table_cells(line)
        if len(cells) >= 2 and re.fullmatch(r"\d+", cells[0]):
            rows.append({"n": int(cells[0]), "clause": cells[1]})
    return rows


def check_file(path: Path) -> dict:
    """One `sha256sum -c` transcript, read back."""
    if not path.is_file():
        return {"ok": 0, "failed": [f"{path.name} was not written"], "lines": 0}
    rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"ok": sum(1 for ln in rows if ln.endswith(": OK")),
            "failed": [ln for ln in rows if "FAILED" in ln], "lines": len(rows)}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") \
        if path.is_file() else ""


def clauses(out: Path) -> dict:
    """The eight, each `{holds, evidence}`, in §1.9's own order."""
    said = {row["n"]: row["clause"] for row in clause_rows()}
    pred = predictions()
    session = json.loads(_text(out / "session.json") or "{}")
    statuses = dict(
        (ln.split("\t")[0], int(ln.split("\t")[1]))
        for ln in _text(out / "statuses.txt").splitlines() if "\t" in ln)
    got = {}

    # 1 -- the manifest, before AND after.
    before = check_file(out / "e12p-manifest-before.txt")
    after = check_file(out / "e12p-manifest-after.txt")
    # `748 OK / 0 FAILED` is §1.9's own text, not the manifest's line count:
    # comparing a check against the file it checked would pass on the WRONG
    # manifest, which is the one substitution clause 1 exists to refuse.
    want_ok = int(re.search(r"(\d+) OK", said.get(1, "0 OK")).group(1))
    want_failed = int(re.search(r"(\d+) FAILED", said.get(1, "0 FAILED"))
                      .group(1))
    lines = session.get("manifest_lines")
    got[1] = {"holds": before["ok"] == after["ok"] == want_ok == lines
              and len(before["failed"]) == len(after["failed"]) == want_failed,
              "evidence": {"before": before, "after": after,
                           "manifest_lines": lines, "expected_ok": want_ok,
                           "failed_allowed": want_failed}}

    # 2 -- the resolver's six sites, against the rung-4 record's §4.2.
    resolved = json.loads(_text(out / "resolve.json") or "{}")
    sites = [f"{m['rel']}:{m['qualname']}"
             for m in resolved.get("matched", [])]
    rung4_sites = resolver_sites_in_record(
        record_path().read_text(encoding="utf-8"))
    got[2] = {"holds": sorted(sites) == sorted(rung4_sites) and bool(sites),
              "evidence": {"read": sites, "rung4": rung4_sites,
                           "exit": statuses.get("resolve")}}

    # 3 -- `info`'s focus line, both numbers.
    info = _text(out / "info.txt")
    line = next((ln for ln in info.splitlines()
                 if ln.startswith("focus matched:")), "")
    m = re.search(r"focus matched: (\d+).*?\((\d+) function", line)
    got[3] = {"holds": bool(m)
              and int(m.group(1)) == pred["focus_matched"]
              and int(m.group(2)) == pred["functions_focused"],
              "evidence": {"line": line,
                           "expected_matched": pred["focus_matched"],
                           "expected_functions": pred["functions_focused"]}}

    # 4 -- the nine rows.
    nine = nine_rows(_text(out / "frame.txt"))
    got[4] = {"holds": nine["holds"], "evidence": nine}

    # 5 -- the suite line, whose literal §1.9 writes.
    want_suite = re.search(r"`([^`]+)`", said.get(5, ""))
    run_log = _text(out / "logs" / "e12p-run.log")
    suite_line = next((ln.rstrip() for ln in run_log.splitlines()
                       if ln.strip().startswith("Tests ")), "")
    got[5] = {"holds": bool(want_suite) and want_suite.group(1) in suite_line,
              "evidence": {"line": suite_line,
                           "expected": want_suite.group(1) if want_suite else None,
                           "run_exit": statuses.get("run")}}

    # 6 -- the marker grep. `searched:` lines say what was looked in, so a
    #      clean read is never an unsearched one.
    markers = _text(out / "e12p-markers.txt").splitlines()
    searched = [ln for ln in markers if ln.startswith("searched: ")]
    hits = [ln for ln in markers if ln.startswith("hit: ")]
    got[6] = {"holds": not hits and bool(searched),
              "evidence": {"searched": searched, "hits": hits}}

    # 7 -- the wrapper directory.
    wrapper = _text(out / "e12p-wrapper.txt")
    got[7] = {"holds": "node_modules/.sensorium: absent" in wrapper,
              "evidence": {"listing": wrapper.splitlines()}}

    # 8 -- the transform diff, which must be EMPTY.
    diff_text = _text(out / "transform.diff")
    diff_body = json.loads(_text(out / "transform-diff.json") or "{}")
    got[8] = {"holds": diff_text.strip() == ""
              and diff_body.get("changed") == 0
              and (diff_body.get("files_compared") or 0) > 0
              and statuses.get("transform-diff") == 0,
              "evidence": {"base": diff_body.get("base")
                           or session.get("base_checkout"),
                           "base_node_modules_linked":
                               diff_body.get("base_node_modules_linked"),
                           "files_compared": diff_body.get("files_compared"),
                           "changed": diff_body.get("changed"),
                           "diff_bytes": len(diff_text),
                           "diff": diff_text[:2000]}}

    missing = sorted(set(said) - set(got))
    if missing:
        usage(f"§1.9 lists clause(s) {missing} that this instrument has no "
              "reader for; a clause nobody reads is a clause nobody checks")
    return {n: {**got[n], "clause": said.get(n)} for n in sorted(got)}


def main(argv) -> int:
    if len(argv) != 2:
        usage("usage: e12p_h8.py <out dir>")
    out = Path(argv[1])
    if not out.is_dir():
        usage(f"no such out directory: {out}")
    eight = clauses(out)
    session = json.loads(_text(out / "session.json") or "{}")
    dropped = []
    if session.get("preregistered_subject") is False:
        dropped.append("the subject or the focus specs were overridden: a DRY "
                       "RUN, not §1.9's one run on the pre-registered subject")
    payload = cell(
        sum(1 for c in eight.values() if c["holds"]), len(eight), dropped,
        rule="all eight clauses of §1.9 hold -> PASS; any one is a STOP "
             "recorded as a finding",
        instrument="e12p_h8.py",
        data="one live run on the lens, this slice's own",
        clauses=eight,
        session={k: v for k, v in session.items()
                 if k not in ("lens_dir", "store", "base_checkout")},
        lens_dir=session.get("lens_dir"), store=session.get("store"),
        base_checkout=session.get("base_checkout"),
        recorder=session.get("recorder") or os.environ.get("E12P_RECORDER"),
        recorder_rev=session.get("recorder_rev") or os.environ.get("E12P_REV"))
    (out / "e12p-h8.json").write_text(json.dumps(payload, indent=2) + "\n",
                                      encoding="utf-8")
    emit({"value": payload["value"], "n": payload["n"],
          "dropped": payload["dropped"],
          "clauses": {n: c["holds"] for n, c in eight.items()}})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
