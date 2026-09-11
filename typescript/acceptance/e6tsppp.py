"""S5 rung 3's ONE re-read of the kept rung-2 invocation, and its comparisons.

    .venv/bin/python typescript/acceptance/e6tsppp.py \
        <store> <invocation> <rung-2 transcript> <hand read.md> \
        <hashes.txt> <out dir> [--dry]

Nothing is recorded. The store is opened read-only: the T0 hash list is
verified from the store root FIRST and a single mismatch refuses the whole
instrument (exit 4) rather than reading a lens that is not the pre-registered
one. Then `sensorium exceptions <invocation> --limit 10000` runs ONCE, its
output is saved (raw, and redacted for committing), and every comparison this
rung's endpoints need is made against that one saved text. No number is read
twice and no command is run twice.

Three endpoints are measured off the one transcript, and one more (E7''')
is measured by `e7_report.py` over the same saved file.

WHAT THE FENCE COMPARES, AND WHY IT IS NOT A LINE-BY-LINE DIFF
--------------------------------------------------------------
Decided BEFORE the re-read ran, on the rung-2 transcript and the rung-3
reader's source alone; recorded in the acceptance record's 2.3 with this
file's commit. The pre-registration holds two clauses that cannot both be
true once the rung-3 key lands:

* **E-places** pre-registers the merge: `TS_MASK` stops exempting the four
  `f16`/`f32`/`f64`/`f128` spellings Rust's float types own, so the three
  rung-2 SWALLOWED blocks for one `catch` in `useAiAssist.ts` at L56
  (`probeAiConfigured`, frames f174, f128 and f32 -- adjudication rows S1,
  S11, S17) become ONE block, and the printed SWALLOWED shape count falls
  from 30 to 28.
* **E6-TS'-fence** pre-registers that every `SWALLOWED --` line of the
  re-read is byte-identical to the rung-2 transcript's, "brackets and ids
  included".

A merge cannot satisfy the second. Two of those three blocks stop being
printed at all, and the survivor's INVOCATION bracket counts chains and
processes across the whole invocation (`exceptions_invocation.bracket`), so
merging three shapes necessarily rewrites it. A literal line-by-line diff
would therefore STOP on precisely the change the other endpoint exists to
pre-register.

Note also that the three lines are NOT "three identical lines": they name
three different events (e404, e370, e77) and three different frames, so no
reading that keeps ids can make two of them disappear without a difference.

**The reading taken.** The fence's own question, in the record's words, is
*"Did the new reader move a verdict?"*. A verdict is the SENTENCE; the
trailing `[...]` bracket is the grouper's occurrence bookkeeping and is
E-places' business, not the fence's. So the gate is read on the verdict
sentence with its bracket stripped:

  1. every verdict sentence the re-read prints must appear, byte-identical,
     in the rung-2 transcript's sentence list -- a NEW or CHANGED sentence is
     a moved verdict and a STOP;
  2. every rung-2 sentence the re-read does NOT print must belong to the
     merge E-places pre-registers -- any other disappearance is a STOP;
  3. the `dispositions:` line is compared WHOLE and byte-identical, bracket
     or no bracket: merging shapes moves no unit between dispositions.

and the RAW line-by-line diff -- brackets, ids, order, everything -- is
carried in the cell whole (`raw_diff`) and quoted in the record, so a reader
can see every byte that moved and judge this reading rather than take it.
The literal reading's own difference count is reported beside it
(`literal_differences`) and is not hidden by the reading that was chosen.

HOW A PRINTED NAME IS MATCHED TO A HAND-READ ROW (ruled at T0)
--------------------------------------------------------------
By the ORIGIN SITE TEXT -- the head line's `<qualname>` and its `L<line>`,
the event id stripped -- and not by block identity. The rung-3 key puts the
untraced catcher's PARENT in the site, so one rung-2 block that aggregated
raises under several test functions SPLITS into one block per parent; every
split block is compared against the same row. The seventeen `(qualname,
line)` pairs are distinct, which is what makes the key usable.

The converse also happens: several origins under ONE test frame print as one
block with `origins: N distinct (first shown)`, and the reader cannot show
the ones it did not print. Each block is matched on the origin it DOES show;
where a block covers more than one origin the count is carried so the record
can say what the comparison could not see.

A printed name for an origin with no row is a FALSE name: the table is
complete by construction (17 rows for the 17 catch-all origins).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from lens import cell, emit, sensorium_bin, usage

#: A block's head line: `e2305 RAISE   fetchCompendium raise Error('..') L11`.
#: The site text this rung matches on is `(qualname, line)`; the event id and
#: the rendered error are not part of it, because a shape that splits prints
#: a different member's id and may print a different message.
HEAD = re.compile(r"^e(?P<eid>\d+) (?P<tag>[A-Z]+)\s+(?P<qual>\S+) "
                  r"(?P<verb>\w+) (?P<exc>.*) L(?P<line>\d+)$")

#: The untraced-catcher verdict, as `exceptions_typescript._untraced_catcher`
#: prints it. The three fates are read off the tail.
NAMED = re.compile(
    r"^AMBIGUOUS -- caught by untraced code inside (?P<parent>.+) "
    r"\((?P<file>[^()]*)\): f(?P<child>\d+) unwound, (?P<fate>.+)$")

#: The five line kinds the fence extracts, in the order the record names them.
VERDICTS = ("SWALLOWED --", "RE-RAISED --", "PROPAGATED --", "UNCAUGHT --")

#: The trailing invocation bracket: `  [in <run>]` or
#: `  [×N over M processes: first e<id> in <run>, +K]`.
BRACKET = re.compile(r"\s*\[(?:in |×)[^\]]*\]$")

#: E-places' pre-registered merge, by the site its verdicts name: the three
#: rung-2 SWALLOWED blocks this key joins into one.
MERGED_SITE = "(probeAiConfigured L56)"

#: The three rung-2 SWALLOWED blocks the pre-registration names as keeping
#: their `origins: N distinct` line -- the key takes the ORIGIN only where the
#: verdict names no site, so a sink with several origins stays one block.
MULTI_ORIGIN_SITES = ("(useBuilderContent.<anonymous> L72)",
                      "(GuardedButton.<anonymous> L29)",
                      "(createHooks.dispatch L98)")


# -- the store, unchanged --------------------------------------------------


def verify(store: Path, hashes: Path) -> tuple[bool, list[str]]:
    """`sha256sum -c` the T0 list from the store root. Nothing else reads."""
    proc = subprocess.run(["sha256sum", "-c", str(hashes)], cwd=store,
                          capture_output=True, text=True)
    bad = [ln for ln in proc.stdout.splitlines() if not ln.endswith(": OK")]
    bad += [ln for ln in proc.stderr.splitlines() if ln.strip()]
    return proc.returncode == 0 and not bad, bad[:20]


def read(store: Path, invocation: str, out: Path) -> dict:
    """The ONE re-read. Saves the raw text and the redacted transcript."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("SENSORIUM_MANIFEST_DIR", "SENSORIUM_SPOOL")}
    env["SENSORIUM_DIR"] = str(store)
    cmd = [sensorium_bin(), "exceptions", invocation, "--limit", "10000"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    body = proc.stdout + proc.stderr
    raw = (f"$ sensorium exceptions {invocation} --limit 10000\n"
           f"{body}--- exit {proc.returncode}\n")
    (out / "e6tsppp-exceptions-raw.txt").write_text(raw, encoding="utf-8")
    return {"exit": proc.returncode, "text": raw,
            "command": f"sensorium exceptions {invocation} --limit 10000"}


def redacted(text: str, store: Path) -> str:
    """The committed copy: the store root by label, the home directory too."""
    pairs = sorted([(str(store).rstrip("/"), "<store>"),
                    (str(Path.home()).rstrip("/"), "<home>")],
                   key=lambda p: len(p[0]), reverse=True)
    for needle, label in pairs:
        if needle:
            text = text.replace(needle, label)
    return text


# -- blocks ----------------------------------------------------------------


def blocks(text: str) -> list[dict]:
    """Every printed block: its head, its verdict, its bracket, its details.

    A head is indented two spaces, its verdict four and its detail lines six
    -- the shape `exceptions_group.print_shape` writes and the rung-2
    transcript shows. Anything else (the header, the tally, the reason line)
    is not a block and is read elsewhere.
    """
    out: list[dict] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 2 and HEAD.match(stripped):
            m = HEAD.match(stripped)
            out.append({"head": stripped, "eid": int(m.group("eid")),
                        "tag": m.group("tag"), "qualname": m.group("qual"),
                        "line": int(m.group("line")),
                        "verdict": None, "bracket": "", "details": []})
        elif indent == 4 and out and out[-1]["verdict"] is None:
            out[-1]["bracket"] = (BRACKET.search(stripped).group(0)
                                  if BRACKET.search(stripped) else "")
            out[-1]["verdict"] = BRACKET.sub("", stripped)
        elif indent >= 6 and out:
            out[-1]["details"].append(stripped)
    return [b for b in out if b["verdict"] is not None]


def origin_key(qualname: str, line: int) -> str:
    """`fetchCompendium L11` -- the origin SITE TEXT a row is matched on."""
    return f"{qualname} L{line}"


def tally_line(text: str, prefix: str) -> str | None:
    return next((ln.strip() for ln in text.splitlines()
                 if ln.strip().startswith(prefix)), None)


def terms(line: str | None, prefix: str) -> dict:
    """`dispositions: swallowed 261, ambiguous 53` -> `{swallowed: 261, ...}`."""
    if line is None:
        return {}
    got = {}
    for part in line[len(prefix):].split(","):
        word, _, count = part.strip().rpartition(" ")
        if not word or not count.isdigit():
            return {}
        got[word] = int(count)
    return got


# -- the hand read ---------------------------------------------------------


def handread(path: Path) -> dict:
    """The seventeen rows, by origin site text.

    Columns, in the locked order: `#`, `origin as printed`, `raise site`,
    `traced callers to the test`, `untraced catcher the source shows`,
    `predicted variant`, `predicted parent qualname`, `reading`. Backticks
    are markdown, not content.
    """
    rows: dict[str, dict] = {}
    order: list[str] = []
    predicted_unnamed = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("predicted unnamed after rung 3:"):
            tail = line.rpartition(":")[2].strip()
            predicted_unnamed = int(tail) if tail.isdigit() else None
            continue
        if not (line.startswith("| ") and line.endswith(" |")):
            continue
        cells = [c.strip().strip("`").strip() for c in line.strip("|").split("|")]
        if len(cells) != 8 or not cells[0].isdigit():
            continue
        m = HEAD.match(cells[1])
        if m is None:
            raise SystemExit(f"row {cells[0]}: unreadable origin {cells[1]!r}")
        key = origin_key(m.group("qual"), int(m.group("line")))
        rows[key] = {"row": int(cells[0]), "origin": cells[1],
                     "raise_site": cells[2], "callers": cells[3],
                     "catcher": cells[4], "variant": cells[5],
                     "parent": cells[6], "reading": cells[7],
                     "origin_key": key}
        order.append(key)
    return {"rows": rows, "order": order, "predicted_unnamed": predicted_unnamed}


def variant_of(fate: str) -> str:
    if fate.startswith("its caller f") and "returned; not followed" in fate:
        return "returned"
    if "later unwound with" in fate:
        return "later unwound"
    if "had not closed at the end of the recording" in fate:
        return "had not closed"
    return "unreadable"


def origins_shown(block: dict) -> int:
    """How many distinct origins this block covers, from its own vary line."""
    for detail in block["details"]:
        m = re.match(r"^origins: (\d+) distinct", detail)
        if m:
            return int(m.group(1))
    return 1


# -- E6-TS''' --------------------------------------------------------------


def compare_names(new: list[dict], table: dict) -> dict:
    """Every printed untraced-catcher block against its row. Rows only."""
    comparisons = []
    for block in new:
        m = NAMED.match(block["verdict"])
        if m is None:
            continue
        key = origin_key(block["qualname"], block["line"])
        row = table["rows"].get(key)
        got_parent = m.group("parent")
        got_variant = variant_of(m.group("fate"))
        why = []
        if row is None:
            why.append("no hand-read row predicts a name for this origin: "
                       "the table is the seventeen catch-all origins and is "
                       "complete, so a name here is FALSE")
        else:
            if got_parent != row["parent"]:
                why.append(f"parent printed {got_parent!r}, the table "
                           f"predicts {row['parent']!r}")
            if got_variant != row["variant"]:
                why.append(f"variant printed {got_variant!r}, the table "
                           f"predicts {row['variant']!r}")
        comparisons.append({
            "origin_key": key, "row": None if row is None else row["row"],
            "head": block["head"], "verdict": block["verdict"],
            "bracket": block["bracket"].strip(),
            "printed_parent": got_parent, "predicted_parent":
                None if row is None else row["parent"],
            "printed_file": m.group("file"),
            "printed_variant": got_variant, "predicted_variant":
                None if row is None else row["variant"],
            "origins_in_block": origins_shown(block),
            "false": bool(why), "why": why})
    named_keys = {c["origin_key"] for c in comparisons if c["row"] is not None}
    missed = [k for k in table["order"] if k not in named_keys]
    splits = {}
    for c in comparisons:
        splits.setdefault(c["origin_key"], []).append(c)
    return {
        "comparisons": comparisons,
        "false_names": [c for c in comparisons if c["false"]],
        "rows_named": sorted(named_keys),
        "rows_missed": missed,
        "splits": {k: len(v) for k, v in splits.items() if len(v) > 1},
        "blocks_covering_several_origins":
            [{"origin_key": c["origin_key"], "origins": c["origins_in_block"]}
             for c in comparisons if c["origins_in_block"] > 1],
    }


# -- E6-TS'-fence -----------------------------------------------------------


def verdict_lines(text: str) -> list[str]:
    """The five gated line kinds, in printed order, exactly as printed."""
    out = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if any(line.startswith(v) for v in VERDICTS) or \
                line.startswith("dispositions:"):
            out.append(line)
    return out


def fence(old_text: str, new_text: str) -> dict:
    """The fence, under the reading this module's docstring states."""
    old, new = verdict_lines(old_text), verdict_lines(new_text)
    raw_diff = [f"- {ln}" for ln in old if ln not in new] + \
               [f"+ {ln}" for ln in new if ln not in old]
    literal = [f"{i}: rung2={o!r} rung3={n!r}"
               for i, (o, n) in enumerate(zip(old, new), 1) if o != n]
    if len(old) != len(new):
        literal.append(f"line counts differ: rung2 {len(old)}, rung3 {len(new)}")
    old_s = [BRACKET.sub("", ln) for ln in old]
    new_s = [BRACKET.sub("", ln) for ln in new]
    appeared = [ln for ln in new_s if ln not in old_s]
    vanished = [ln for ln in old_s if ln not in new_s]
    merged_away = [ln for ln in vanished if MERGED_SITE in ln]
    unexplained = [ln for ln in vanished if MERGED_SITE not in ln]
    old_tally = tally_line(old_text, "dispositions:")
    new_tally = tally_line(new_text, "dispositions:")
    why = []
    if appeared:
        why += [f"a verdict sentence the rung-2 transcript does not carry: {ln}"
                for ln in appeared]
    if unexplained:
        why += [f"a rung-2 verdict sentence the re-read does not print, and "
                f"it is not the pre-registered merge: {ln}"
                for ln in unexplained]
    if old_tally != new_tally:
        why.append(f"the tally moved: rung2 {old_tally!r}, rung3 {new_tally!r}")
    return {
        "rule": ("every verdict SENTENCE identical (the invocation bracket is "
                 "E-places' and is stripped), no sentence appearing, no "
                 "sentence disappearing but the pre-registered merge's, and "
                 "the `dispositions:` line whole"),
        "sentences_rung2": len(old), "sentences_rung3": len(new),
        "appeared": appeared, "vanished": vanished,
        "vanished_to_the_pre_registered_merge": merged_away,
        "vanished_unexplained": unexplained,
        "tally_rung2": old_tally, "tally_rung3": new_tally,
        "tally_identical": old_tally == new_tally,
        "literal_differences": len(literal),
        "literal_detail": literal,
        "raw_diff": raw_diff,
        "differences": len(why), "why": why,
    }


# -- E-places ---------------------------------------------------------------


def places(old_text: str, new_text: str) -> dict:
    """The SWALLOWED shape count, the merge, and the three multi-origin sinks."""
    old = [b for b in blocks(old_text) if b["verdict"].startswith("SWALLOWED --")]
    new = [b for b in blocks(new_text) if b["verdict"].startswith("SWALLOWED --")]
    merged = [b for b in new if MERGED_SITE in b["verdict"]]
    old_merged = [b for b in old if MERGED_SITE in b["verdict"]]
    kept = {}
    for site in MULTI_ORIGIN_SITES:
        hits = [b for b in new if site in b["verdict"]]
        kept[site] = {"blocks": len(hits),
                      "origins": [origins_shown(b) for b in hits],
                      "verdicts": [b["verdict"] for b in hits]}
    why = []
    if len(new) != 28:
        why.append(f"{len(new)} SWALLOWED blocks, the pre-registration says 28")
    if len(merged) != 1:
        why.append(f"the useAiAssist.ts L56 sink prints {len(merged)} block(s), "
                   "the pre-registration says one")
    for site, got in kept.items():
        if got["blocks"] != 1:
            why.append(f"{site} prints {got['blocks']} blocks, the "
                       "pre-registration keeps it one")
    return {
        "rule": ("exactly 28 SWALLOWED blocks, one per distinct sink site; "
                 "the useAiAssist.ts L56 sink (rung-2 rows S1/S11/S17, three "
                 "blocks over 30 printed lines) printed once; every other "
                 "rung-2 SWALLOWED block unchanged"),
        "swallowed_blocks_rung2": len(old), "swallowed_blocks_rung3": len(new),
        "merged_block": [{"head": b["head"], "verdict": b["verdict"],
                          "bracket": b["bracket"].strip(),
                          "details": b["details"]} for b in merged],
        "merged_in_rung2": [{"head": b["head"], "verdict": b["verdict"],
                             "bracket": b["bracket"].strip()}
                            for b in old_merged],
        "multi_origin_sinks_kept_single": kept,
        "differences": len(why), "why": why,
    }


# -- the cells --------------------------------------------------------------


def measure(store: Path, invocation: str, old_path: Path, table_path: Path,
            out: Path) -> dict:
    table = handread(table_path)
    run = read(store, invocation, out)
    new_text = run["text"]
    old_text = old_path.read_text(encoding="utf-8")
    transcript = out / "e6tsppp-exceptions.txt"
    transcript.write_text(redacted(new_text, store), encoding="utf-8")

    names = compare_names(blocks(new_text), table)
    fenced = fence(old_text, new_text)
    placed = places(old_text, new_text)
    reason_line = tally_line(new_text, "ambiguous by reason:")
    reasons = terms(reason_line, "ambiguous by reason:")
    provenance = {
        "recorder": os.environ.get("E6TSPPP_RECORDER"),
        "recorder_rev": os.environ.get("E6TSPPP_REV"),
    }
    unnamed_after = reasons.get("unnamed", 0) + reasons.get("orphan", 0)
    catch_all = sum(1 for b in blocks(new_text)
                    if "no rule of this recorder" in b["verdict"])
    return {
        "invocation": invocation,
        "command": run["command"],
        "exit": run["exit"],
        "transcript": transcript.name,
        "transcript_sha256": hashlib.sha256(
            transcript.read_bytes()).hexdigest(),
        "transcript_lines": len(new_text.splitlines()),
        "rung2_transcript_sha256": hashlib.sha256(
            old_path.read_bytes()).hexdigest(),
        "reason_line": reason_line,
        "reasons": reasons,
        "cells": {
            "E6-TS‴": cell(
                len(names["false_names"]), len(names["comparisons"]), [],
                rule=("0 false names: a printed untraced-catcher line whose "
                      "parent qualname is not the hand-read row's, or printed "
                      "for an origin the table predicted `unnamed`, is false "
                      "-> STOP. A row the reader leaves unnamed is a MISS, "
                      "reported with its count and not a stop."),
                false_names=names["false_names"],
                rows_in_table=len(table["order"]),
                rows_named=len(names["rows_named"]),
                rows_missed=names["rows_missed"],
                misses=len(names["rows_missed"]),
                splits=names["splits"],
                blocks_covering_several_origins=
                    names["blocks_covering_several_origins"],
                predicted_unnamed_after=table["predicted_unnamed"],
                unnamed_after=unnamed_after,
                catch_all_blocks_still_printed=catch_all,
                reason_line=reason_line, reasons=reasons,
                comparisons=names["comparisons"], **provenance),
            "E6-TS′-fence": cell(
                fenced["differences"], fenced["sentences_rung3"], [],
                **fenced, **provenance),
            "E-places": cell(
                placed["swallowed_blocks_rung3"], 28, [],
                **placed, **provenance),
        },
    }


def main(argv) -> int:
    args = [a for a in argv[1:] if a != "--dry"]
    if len(args) != 6:
        usage("usage: e6tsppp.py <store> <invocation> <rung-2 transcript> "
              "<hand read.md> <hashes.txt> <out dir> [--dry]")
    for stray in ("SENSORIUM_SPOOL", "SENSORIUM_MANIFEST_DIR"):
        os.environ.pop(stray, None)
    store, invocation, old, table, hashes, out = args
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, bad = verify(Path(store), Path(hashes).resolve())
    if not ok:
        sys.stderr.write(
            "refused: the store's trace set is not the one T0 hashed, so this "
            "re-read would not be the pre-registered lens. `sha256sum -c` "
            f"reported:\n" + "\n".join(f"  {ln}" for ln in bad) + "\n")
        return 4
    payload = measure(Path(store), invocation, Path(old), Path(table), out_dir)
    payload["hash_list_verified"] = True
    (out_dir / "e6tsppp.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
