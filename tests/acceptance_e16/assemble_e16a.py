#!/usr/bin/env python3
"""Render E16 part A's §2 from `results-a.json`.

    .venv/bin/python tests/acceptance_e16/assemble_e16a.py \\
        <results-a.json> <record.md> \\
        [--write | --append | --artifacts=<dir> [PATH=LABEL]...] \\
        [--suffix=<heading tail>] [--previous=<earlier results.json>]

Prints the section. With `--write` it replaces the record's single
`Not yet measured.` line under `## 2. Part A` with it, which is the one edit
`tests/test_acceptance_e16_lock.py::test_part_a_begins_not_yet_measured_or_a_
measured_heading` allows. With `--append` it puts the section at the END of
§2, beside an earlier run's, which is how a re-measurement after a fix is
recorded: §2's first non-blank line stays the first run's heading.
`--suffix` extends the `### measured <date>` heading (`" — run 2, after the
H2 and H3 fixes"`), and `--previous` names the earlier run's results file so
the section can say which run is the first PASS for each cell -- read from
that file rather than retyped.

WHAT IS CHECKED HERE RATHER THAN TRUSTED
----------------------------------------
* **the raw is not a dry run.** The dry run plants `dry-` plus four
  characters and caps every timer at a minute; its cells are about a
  different string, and rendering them under §1's endpoints would publish a
  number about a different subject. Absent is not false: a record with no
  `dry_run` key came from an instrument that did not stamp it.
* **the run completed.** A refused or killed run leaves `status` saying so
  and cells that were never filled. Rendering those would put `dropped`
  rows into §2 under a heading that says the part was measured.
* **no box path leaves the pin table.** Everything the instrument wrote is
  relative to the work root, and the ONE absolute path in the section is the
  `E16_DIR=` pin -- which is also the one shape the record's own no-box-path
  test allows through. `offenders` refuses anything else rather than letting
  it reach a document that travels with the repository.

The verdict words are not computed here. They are `e16a.py`'s cells, already
decided, carried through; `RULES` is imported from the same module so the
clause printed beside a word is §9's own -- one copy of the rule table, held
against the record on disk by the cell tests.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e16a import (DROPPED, EXPECTED, PREDICTIONS,  # noqa: E402,F401
                  RULES, TOKEN_VAR, read_driver_build)


class Refused(Exception):
    """A results file this assembler will not render."""


#: The record's own rule, re-applied to what is about to be appended to it:
#: a line may name a box path only as the `E16_DIR=` pin.
FORBIDDEN = ("/mnt/", "/home/")
PIN = "E16_DIR="

#: The token's SHAPE, so `offenders` can refuse a line carrying one without
#: ever being handed the value. `sk-e16-` plus at least ten of the token's
#: alphabet: the minted values are 33 characters long, and both of them --
#: the recording token and the value H3 re-exported -- are the same shape,
#: so one pattern covers the pair. It does NOT match the record's own
#: prose: `` `sk-e16-` plus 33 characters `` has a backtick where a token
#: has its body. This module's docstring claimed the check existed before
#: the check did; it exists now.
TOKEN_SHAPE = re.compile(r"sk-e16-[A-Za-z0-9]{10,}")

#: The four cells part A measures, with the words §1 gives each one, in the
#: order §9's table lists them.
CELL_TITLES = {"H1": "H1 (environment)", "H2": "H2", "H3": "H3",
               "H6": "H6 (`redaction.env`)"}

#: The pin table's last row: see `pin_table`.
DRIVER_ROW = ("| driver (the committed transcripts' label) | `$DRIVER_DIR` "
              "— the release `cargo-sensorium`'s own directory, outside the work root |")


def refuse_dry_run(raw: dict) -> None:
    """The one refusal the dry run exists to exercise. `None` on a real
    record, which is what makes a caller's `refuse_dry_run(raw)` a
    statement and not a value nobody looks at."""
    dry = raw.get("dry_run")
    if dry is not True and dry is not False:
        raise Refused("this results file does not say whether it was a dry "
                      f"run (dry_run = {dry!r}); absent is not false")
    if dry:
        raise Refused("this results file was written by a DRY RUN: its "
                      "token is a decoy and its timers were a minute, so "
                      "none of its cells is about §1's subject")


def offenders(text: str) -> list[str]:
    """Every line that may not be committed: a box path outside the
    `E16_DIR=` pin, or anything shaped like the token itself."""
    return [ln for ln in text.splitlines()
            if (any(f in ln for f in FORBIDDEN) and PIN not in ln)
            or TOKEN_SHAPE.search(ln)]


def _rel(lens: dict, key: str) -> str:
    """One of the instrument's locations, as `$E16_DIR/<name>`."""
    root = Path(lens["work_root"])
    try:
        return "$E16_DIR/" + str(Path(lens[key]).relative_to(root))
    except ValueError:
        return str(lens[key])


def pin_table(lens: dict) -> list[str]:
    rows = [("work root", f"`{PIN}{lens['work_root']}`"),
            ("store", f"`{_rel(lens, 'store')}`"),
            ("transcripts", f"`{_rel(lens, 'transcripts')}/`"),
            ("Python case copy", f"`{_rel(lens, 'python_case')}/`"),
            ("crate copy", f"`{_rel(lens, 'rust_crate')}/`"),
            ("vitest project copy", f"`{_rel(lens, 'ts_project')}/`"),
            ("cargo target", f"`{_rel(lens, 'cargo_target')}/`"),
            ("instrument output", f"`{_rel(lens, 'out')}/`")]
    # A label rather than a location: the release driver's directory is a
    # build output outside the work root, and `refocus_rust` prints the argv
    # it launched -- so the committed transcripts name it and this row says
    # what the name means, without writing the path.
    return (["| pin | path |", "|---|---|"]
            + [f"| {name} | {value} |" for name, value in rows]
            + [DRIVER_ROW])


def verdict_table(raw: dict) -> list[str]:
    out = ["| cell | word | §9's rule | what was read |", "|---|---|---|---|"]
    for cell, result in raw["cells"].items():
        word = result["word"]
        rule = RULES[cell].get(word, "--")
        out.append(f"| {CELL_TITLES[cell]} | **{word}** | {rule} | "
                   f"{result['why']} |")
    for row in raw["dropped"]:
        out.append(f"| {row['cell']} | dropped | -- | {row['reason']} |")
    return out


def versions_table(raw: dict) -> list[str]:
    """The versions, under the line that says which BINARY produced them.

    Dropped whole when the R37 rebuild left no stamp: every string below
    comes from the source tree or from a trace, and none of them can tell a
    current driver from a stale one -- which is the failure that made the
    rebuild a phase.
    """
    build = read_driver_build(raw.get("driver_build"))
    if build["word"] != "measured":
        return [f"**Versions: dropped.** {build['why']}"]
    b = build["build"]
    when = _iso(b["mtime"])
    driver_line = (
        f"**Driver built by the run (R37):** `cargo build --release -p "
        f"cargo-sensorium` in {b['seconds']}s before anything was recorded; "
        f"`{b['binary']}`, {b['size']} bytes, mtime {when}."
        # No code span around cargo's own line: it contains backticks of its
        # own (`Finished \`release\` profile`) and a span around them ends
        # early, leaving the rest of the sentence in code font.
        + (f" cargo said: {b['finished_line']}"
           if b.get("finished_line") else ""))
    versions = raw["versions"]
    rows = [("`sensorium` (installed)", versions["sensorium"],
             EXPECTED["sensorium"])]
    for arm in ("python", "rust", "typescript"):
        rows.append((f"`recorder:` on the {arm} trace",
                     versions["recorder"].get(arm), _expected_recorder(arm)))
    for arm, value in sorted(versions["driver_version"].items()):
        rows.append((f"`driver_version` on the {arm} trace", value, "--"))
    for tool, value in sorted((versions["tools"] or {}).items()):
        rows.append((f"`{tool}` under the scrubbed environment", value, "--"))
    return ([driver_line, "",
             "| version | read | §1 expected |", "|---|---|---|"]
            + [f"| {name} | {got or '(none recorded)'} | {want} |"
               for name, got, want in rows])


def _iso(epoch: float) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(epoch).isoformat(timespec="seconds")


def _expected_recorder(arm: str) -> str:
    key = {"python": "sensorium", "rust": "sensorium-rt",
           "typescript": "sensorium-ts"}[arm]
    return f"{key} {EXPECTED[key]}"


#: The prefixes whose files §1 names one by one. Everything else swept is
#: summarised by its top directory: the cargo build tree and the vitest
#: project copy are hundreds of files that no recorder wrote, and a table
#: nobody can read is not a table anybody checks. Every count is in
#: `results-a.json`, committed beside this record.
NAMED = ("store-{label}/", "rust-target/sensorium/spool/")


def named_prefixes(raw: dict) -> tuple[str, ...]:
    """The prefixes §1 names one by one, for THIS run's store. A
    re-measurement's store carries the run label, and a table keyed on the
    first run's name would summarise the second run's own artifacts into a
    count -- the rows §1 asks for by name."""
    label = raw.get("label", "a")
    return tuple(p.format(label=label) for p in NAMED)


def h1_table(raw: dict) -> list[str]:
    sweep = raw["h1_sweep"]
    prefixes = named_prefixes(raw)
    named = [f for f in sweep["files"] if f["path"].startswith(prefixes)]
    rest: dict = {}
    for f in sweep["files"]:
        if f["path"].startswith(prefixes):
            continue
        top = f["path"].split("/")[0]
        agg = rest.setdefault(top, {"n": 0, "a": 0, "b": 0})
        agg["n"] += 1
        agg["a"] = max(agg["a"], f["count"])
        agg["b"] = max(agg["b"], f["fresh_count"] or 0)
    out = ["| file (under `$E16_DIR`) | count, recording token | "
           "count, refocus token |", "|---|---|---|"]
    for f in named:
        out.append(f"| `{f['path']}` | {f['count']} | {f['fresh_count']} |")
    for top, agg in sorted(rest.items()):
        out.append(f"| `{top}/` — {agg['n']} further file(s) swept, "
                   f"summarised | max {agg['a']} | max {agg['b']} |")
    out.append(f"| `{sweep['excluded'][1]}/` — the instrument's own output, "
               f"{len(sweep['instrument_output'])} file(s), swept but "
               f"outside §1's scope | max "
               f"{max([r['count'] for r in sweep['instrument_output']] or [0])}"
               f" | -- |")
    return out


def h2_table(raw: dict) -> list[str]:
    rows = raw["h2_sweep"]
    gated = [r for r in rows if r["scope"] == "in"]
    out = ["| path (under `$E16_DIR`) | mode | wanted |", "|---|---|---|"]
    for r in sorted(gated, key=lambda r: r["path"]):
        want = "700" if r["kind"] == "dir" else "600"
        mark = "" if r["mode"] == want else "  ← **STOP**"
        out.append(f"| `{r['path']}`{'/' if r['kind'] == 'dir' else ''} | "
                   f"{r['mode']} | {want}{mark} |")
    out.append("")
    out.append("This table and H1's cover different sets, and deliberately: "
               "the mode sweep is taken straight after the three recordings "
               "and before any query, so it describes what the RECORDERS "
               "left \u2014 a reader that opens a WAL database creates "
               "`-shm`/`-wal` beside it, and those are files the runs did "
               "not make. H1's sweep runs last, over everything present at "
               "the end, so it also covers the four refocus re-runs' spools "
               "and traces, which is why it lists more paths than this.")
    out.append("")
    out.append("Swept and listed, outside this cell's scope — the "
               "instrument's own directories, and the driver's shared "
               "build-support trees under the cargo target directory "
               "(their top directories; §1's H2 is a claim about the "
               "store and the spools):")
    out.append("")
    out += ["| path (under `$E16_DIR`) | mode |", "|---|---|"]
    for r in sorted((r for r in rows if r["scope"] == "out"),
                    key=lambda r: r["path"]):
        out.append(f"| `{r['path'] or '.'}` | {r['mode']} |")
    return out


def h3_table(raw: dict) -> list[str]:
    out = []
    for pair in raw["cells"]["H3"]["pairs"]:
        mark = "as predicted" if pair["ok"] else "**the other way**"
        out.append(f"**{pair['name']}** — predicted {pair['predicted']}, "
                   f"{mark}. Exit {pair['exit']}, {pair['seconds']}s.")
        out.append("")
        out.append("```")
        for line in ("env_line", "verdict_line", "licence_line"):
            if pair[line]:
                out.append(pair[line])
        out.append("```")
        out.append("")
        if not pair["ok"]:
            out.append(f"> {pair['why']}")
            out.append("")
    return out


def h6_table(raw: dict) -> list[str]:
    out = ["| trace | arm | vars stored | `redaction.env` names |",
           "|---|---|---|---|"]
    for row in raw["h6_traces"]:
        names = ", ".join(f"`{n}`" for n in row["names"]) or "(none)"
        out.append(f"| `{row['run']}` | {row['arm']} | {row['vars']} | "
                   f"{names} |")
    return out


def amendments(raw: dict) -> list[str]:
    """R27 and the readings this run had to fix before it could be made.

    Recorded BESIDE §1, never edited into it: §1 is locked, and a
    pre-registration error found before launch is pinned by an amendment
    with the corrected clause next to it. Predictions are not amended --
    only the names, paths and readings the pre-registration got wrong about
    the instrument."""
    return [
        "- **R27, the Rust focus.** §1's block names `--focus compute` "
        "\"(the case's focused fn; read `corpus/rust/aliasing/questions."
        "yaml` for the name)\". That crate has no `compute`; its seeded-bug "
        "function is `derive_sandbox`. Corrected clause: **`--focus "
        "derive_sandbox`**, in both arms — `corpus/aliasing/main.py` "
        "carries a `derive_sandbox` too, so §1's Python `--focus main` is "
        "amended the same way and the two arms focus the same function.",
        "- **R27, the TypeScript case.** Decision A10 names "
        "`corpus/typescript/aliasing`, which does not exist. Corrected "
        "clause: **`corpus/typescript/async_interleaved`**, recorded with "
        "`sensorium ts run -- npx vitest run async_interleaved`.",
        "- **The TypeScript spool's location.** The plan's instrument sketch "
        "puts it at `store-a/ts-spools`; `sensorium.ts.driver` writes it to "
        "`<trace root>/spool/<invocation>/`. The sweep is recursive over the "
        "whole work root, so the directory is covered wherever it is, and "
        "the tables name it as it actually is.",
        "- **\"among the compared\" (H3).** §1 predicts the env line "
        "\"names the redacted variable among the compared\". "
        "`refocus_world._env_state` never names a compared variable — it "
        "counts them and names only what was excluded. Reading applied, "
        "stated before the run: the variable is among the compared when the "
        "trace recorded it (H6) **and** the env line names it on no "
        "exclusion list. The prediction itself is unchanged.",
        "- **The instrument's path.** §1's spec block names the instrument "
        "`tests/acceptance/e16.sh`. It is `tests/acceptance_e16/e16a.sh`, "
        "with `e16a.py`, `e16a_cells.py` and `assemble_e16a.py` beside it — "
        "which is what §1's own plan block already says, the two halves of "
        "§1 having been written at different times. Corrected clause: "
        "**`tests/acceptance_e16/e16a.sh`**.",
        "- **The grep sweep is wider than §1's.** §1 sweeps the store and "
        "the spool directories; this one sweeps everything under the work "
        "root except the token file, and for the refocus value as well as "
        "the recording one. Wider in the only direction that can find a "
        "leak; the gate is still §1's — the recording token, every count 0.",
    ]


#: What each STOP points at, rendered only when that cell STOPped. These
#: are readings of the measurement, marked as readings: the numbers above
#: are what was measured, and each note names the function whose behaviour
#: produced them so the next person can check the reading rather than take
#: it. Nothing here changes a verdict.
STOP_NOTES = {
    "H2": (
        "All ten paths are made by callers that do not go through the "
        "0700/0600 helpers. `sensorium.ts.driver` creates "
        "`<trace root>/spool/<invocation>/` with a bare `mkdir(parents=True, "
        "exist_ok=True)` and writes `invocation.json`, `harness.json`, "
        "`ingested.json` and `manifests/*.json` with plain `write_text`; "
        "`cargo-sensorium`'s `invocation::write_invocation` writes its own "
        "`invocation.json` with `std::fs::write`. Each lands "
        "0666/0777-under-the-umask — 0664/0775 on this box — instead of "
        "0600/0700. What DOES hold: every file that carries a recorded "
        "environment is 0600 — the TypeScript `<pid>-<n>.jsonl`, the Rust "
        "`.spool`, `.proc.json` and `.runner.json` — and the store itself "
        "is 0600/0700 throughout, `redaction.key` included. §5.5's claim is "
        "categorical, so a file beside the spool that holds argv and config "
        "paths at 0664 is a STOP and not a footnote."),
    "H3": (
        "Both failing readings are the Rust pair, and both have one cause: "
        "`refocus_rust._is_recorder_key` treats EVERY `SENSORIUM_`-prefixed "
        "name as the recorder's own bookkeeping and removes it before "
        "`refocus_licence.env_of` compares anything. The pre-registered "
        "variable is `SENSORIUM_E16_TOKEN`, which is inside that prefix, so "
        "on a Rust pair it is never compared: the unchanged pair grants the "
        "licence while naming the token on the not-compared list, and the "
        "changed pair grants it as well — a rotated secret the Rust licence "
        "cannot see. The Python pair read exactly as §1 predicted in both "
        "directions, so what failed is the Rust branch's exclusion rule and "
        "not rule v1's environment redaction. Two things to rule on, not "
        "one: (1) the prefix is wider than the six variables its docstring "
        "justifies and silently swallows any `SENSORIUM_`-named variable a "
        "user's program actually reads; (2) §1 chose a token name inside "
        "that prefix, and no part of the pre-registration noticed — this "
        "measurement is where it surfaced."),
}


def stop_notes(raw: dict) -> list[str]:
    stopped = [c for c, r in raw["cells"].items()
               if r["word"] == "STOP" and c in STOP_NOTES]
    if not stopped:
        return []
    out = ["", "#### What the STOPs point at", ""]
    for cell in stopped:
        out.append(f"- **{CELL_TITLES[cell]}.** {STOP_NOTES[cell]}")
    return out


# -- the evidence committed beside the record ------------------------------
#: What a committed artifact may say instead of a box path. The record's §2
#: pin table is where each label is defined, and it is the one sanctioned
#: place a path on this box is written down.
LABELS = ("$E16_DIR", "$REPO", "$HOME")


def scrub_pairs(lens: dict, extra=()) -> list[tuple[str, str]]:
    """(needle, label) longest first, so a path under another path is not
    half-replaced by the shorter one.

    `extra` is `assemble_e15.py`'s trailing `PATH=LABEL` idiom: a transcript
    can name a directory the lens does not hold -- the release driver's, on
    a Rust pair, because `refocus_rust` prints the argv it launched -- and
    naming it on the command line is how one gets a label without the
    instrument's own lens growing a field after the run it describes."""
    pairs = [(lens["work_root"], "$E16_DIR"), (lens["repo"], "$REPO"),
             (str(Path.home()), "$HOME"), *extra]
    return sorted(pairs, key=lambda pair: -len(pair[0]))


def scrub(text: str, pairs) -> str:
    for needle, label in pairs:
        text = text.replace(needle, label)
    return text


def artifacts(raw: dict, raw_path: Path, record: Path, dest: Path,
              extra=()) -> list[Path]:
    """`results-a.json` and the four refocus transcripts, scrubbed.

    A transcript is EVIDENCE and is copied whole -- the `cwd:`, `trace:` and
    `refocus-of:` lines are half of what makes it readable -- so the three
    roots are replaced by the labels §2's pin table defines rather than the
    lines being dropped. The token's own value was already replaced with
    `<token>` when the transcript was written; `offenders` re-checks both
    facts on the way out, because a committed file is the last place to
    find out."""
    pairs = scrub_pairs(raw["lens"], extra)
    dest.mkdir(parents=True, exist_ok=True)
    written = [record.with_suffix(f".results-{raw.get('label', 'a')}.json")]
    written[0].write_text(scrub(raw_path.read_text(), pairs))
    src = Path(raw["lens"]["transcripts"])
    for name, _predicted in PREDICTIONS:
        one = src / f"refocus-{name}.txt"
        out = dest / one.name
        out.write_text(scrub(one.read_text(), pairs))
        written.append(out)
    bad = [f"{path}: {line}" for path in written
           for line in offenders(path.read_text())]
    if bad:
        raise Refused("a box path survived the scrub: " + "; ".join(bad[:5]))
    return written


#: Which commits closed each of run 1's STOPs, as Task 8c's brief states
#: them. Named in §2 because "run 2 is the first PASS" is only half a fact
#: without what changed in between -- §9's H1 clause asks the record to say
#: which run is the first PASS, and ruling R30 extends that to H2 and H3.
FIX_COMMITS = {
    "H2": "`6a719e4` (the TypeScript driver's spool, manifests and records, "
          "and the Rust invocation record, 0700/0600) and `e36d5dd` "
          "(`db.py`'s traces creator)",
    "H3": "`1f60dd6` and `9d8f16a` (the refocus branches' recorder keys are "
          "exact sets of what each driver SETS, not a `SENSORIUM_` prefix)",
}


def first_pass_block(raw: dict, previous: dict | None) -> list[str]:
    """Per cell, how this run reads against the one before it.

    §9's H1 clause requires the record to say WHICH RUN IS THE FIRST PASS
    after a fix, and ruling R30 extends that to H2 and H3. The previous
    run's words are read out of its own committed results file rather than
    retyped here, so this cannot claim a cell STOPped when the record beside
    it says otherwise.
    """
    if not previous:
        return []
    was = {c: r["word"] for c, r in (previous.get("cells") or {}).items()}
    now = {c: r["word"] for c, r in raw["cells"].items()}
    rows = []
    for cell in RULES:
        before, after = was.get(cell), now.get(cell)
        if before == "PASS":
            rows.append(f"- **{CELL_TITLES[cell]}** passed in run 1 and "
                        f"reads **{after}** here.")
        elif after == "PASS":
            rows.append(
                f"- **{CELL_TITLES[cell]} — this run is the first PASS.** "
                f"The run before it read {before}: "
                f"{_sentence(previous['cells'][cell]['why'])} Fixed by "
                f"{FIX_COMMITS.get(cell, 'the branch')}. This run reads: "
                f"{_sentence(raw['cells'][cell]['why'])}")
        else:
            rows.append(
                f"- **{CELL_TITLES[cell]} — still {after}, no first PASS "
                f"yet.** The run before it read {before}: "
                f"{_sentence(previous['cells'][cell]['why'])} This run "
                f"reads: {_sentence(raw['cells'][cell]['why'])}")
    return ["", "#### Against run 1 — which run is the first PASS", ""] + rows


def _sentence(why: str) -> str:
    """A cell's `why` ends without punctuation -- it is a clause meant for a
    table. Run into prose it swallows the next sentence, so it is closed
    here rather than each caller remembering."""
    why = why.strip()
    return why if why.endswith((".", "!", "?")) else why + "."


def dry_run_block(raw: dict) -> list[str]:
    """The dry-run reading, from `dry_run_findings` in the raw record.

    §1's own instrument sentence requires a dry run ("dry-run first on a
    4-character decoy to check every artifact path it reads exists"), so §2
    has to say what that dry run found and what changed between it and the
    measurement. Rendered here when the instrument carried the findings;
    empty when it did not, and then §2 carries a paragraph written by hand
    that says so -- which is what run 1 did, the field having been added
    after run 1 was measured.
    """
    findings = raw.get("dry_run_findings") or []
    if not findings:
        return []
    return (["", "#### The dry run", "",
             "Before the measurement, with a `dry-` decoy that cannot match "
             "the content rule and every timer at 60 s, into a work root of "
             "its own that was deleted afterwards. What it found, and what "
             "changed in the instrument between it and the run above:", ""]
            + [f"- {line}" for line in findings])


def render(raw: dict, date: str, suffix: str = "",
           previous: dict | None = None) -> str:
    refuse_dry_run(raw)
    if raw.get("status") != "complete":
        raise Refused("this results file is not a completed run "
                      f"(status = {raw.get('status')!r}: "
                      f"{raw.get('refusal')})")
    cells = raw["cells"]
    words = "  ".join(f"{c} {r['word']}" for c, r in cells.items())
    body = [
        f"### measured {date}{suffix}",
        "",
        f"Measured once, on this box, under `e16a.sh`. **Part A: "
        f"{raw['part']}** — {words}. The token was `sk-e16-` plus 33 "
        f"characters, minted by the instrument, never printed and never "
        f"committed: `sha256(token)[:8] = {raw['token']['sha8']}`, and the "
        f"value H3 re-exported `{raw['token']['fresh_sha8']}`. Every "
        f"recording and every refocus ran under a scrubbed environment of "
        f"exactly "
        + ", ".join(f"`{n}`" for n in raw["preflight"]["allowlist"])
        + " — no other name reached a recorder, and the instrument refuses "
          "to start unless none of them fires rule v1, which is what makes "
          f"H6's \"exactly one name\" a fact about the token. "
          f"{raw['seconds']}s wall clock.",
        "",
        "| cell | word | §9's rule | what was read |".join([]),
    ]
    body = body[:-1] + verdict_table(raw) + ["", "#### Pins", ""]
    body += pin_table(raw["lens"])
    body += first_pass_block(raw, previous)
    body += dry_run_block(raw)
    body += stop_notes(raw) + ["", "#### Amendments, beside §1", ""]
    body += amendments(raw) + ["", "#### Versions", ""]
    body += versions_table(raw)
    body += ["", "#### H1 (environment) — the token's bytes, per file", ""]
    body += h1_table(raw)
    body += ["", "#### H2 — the modes", ""] + h2_table(raw)
    body += ["", "#### H3 — the four refocus readings", ""] + h3_table(raw)
    body += ["", "#### H6 (`redaction.env`) — the names", ""] + h6_table(raw)
    body += ["", "#### Phases", "",
             "| phase | seconds |", "|---|---|"]
    body += [f"| {p['name']} | {p['seconds']} |" for p in raw["phases"]]
    text = "\n".join(body) + "\n"
    bad = offenders(text)
    if bad:
        raise Refused("a box path outside the pin table: " + "; ".join(bad))
    return text


NOT_YET = "Not yet measured."


def write_into(record: Path, section: str) -> None:
    text = record.read_text()
    if NOT_YET not in text:
        raise Refused(f"{record} no longer carries {NOT_YET!r}: §2 has "
                      "already been written, and part A is measured once")
    record.write_text(text.replace(NOT_YET, section.rstrip("\n"), 1))


def append_into(record: Path, section: str) -> None:
    """A re-measurement's section, BESIDE the one before it.

    §2's first non-blank line has to stay the first run's heading -- that is
    what `tests/test_acceptance_e16_lock.py` accepts and what keeps a later
    run from reading as the only one -- so a re-measurement is appended at
    the end and never spliced above. Refused if §2 was never written, and
    refused if this exact heading is already there: an assembler run twice
    would otherwise leave two copies of one measurement in a document whose
    whole claim is that each was made once.
    """
    text = record.read_text()
    if NOT_YET in text:
        raise Refused(f"{record} still says {NOT_YET!r}: there is no earlier "
                      "run for this one to be appended beside")
    heading = section.splitlines()[0]
    if heading in text:
        raise Refused(f"{record} already carries {heading!r}")
    record.write_text(text.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 2
    raw = json.loads(Path(argv[0]).read_text())
    record = Path(argv[1])
    date = __import__("datetime").date.today().isoformat()
    rest = argv[2:]
    # Trailing `PATH=LABEL` pairs only -- anything starting with `--` is a
    # flag, and a flag read as a scrub pair would rewrite the section with
    # its own name.
    extra = tuple(tuple(a.split("=", 1)) for a in rest if "=" in a
                  and not a.startswith("--"))
    if any(a.startswith("--artifacts=") for a in rest):
        refuse_dry_run(raw)
        dest = Path(next(a for a in rest
                         if a.startswith("--artifacts=")).split("=", 1)[1])
        for path in artifacts(raw, Path(argv[0]), record, dest,
                              extra):
            print(f"wrote {path}")
        return 0
    suffix = _opt(rest, "--suffix=") or ""
    prev_path = _opt(rest, "--previous=")
    previous = json.loads(Path(prev_path).read_text()) if prev_path else None
    section = render(raw, date, suffix, previous)
    if "--append" in rest:
        append_into(record, section)
        print(f"appended to {record}")
    elif "--write" in rest:
        write_into(record, section)
        print(f"written into {record}")
    else:
        sys.stdout.write(section)
    return 0


def _opt(rest: list[str], flag: str) -> str | None:
    return next((a.split("=", 1)[1] for a in rest if a.startswith(flag)), None)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        sys.exit(2)
