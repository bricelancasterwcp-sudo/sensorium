#!/usr/bin/env python3
"""Render E16 part C's §4 from `results-c.json`.

    .venv/bin/python tests/acceptance_e16/assemble_e16c.py \\
        <results-c.json> <record.md> \\
        [--write | --append | --artifacts=<dir> [PATH=LABEL]...] \\
        [--suffix=<heading tail>]

Prints the section. With `--write` it replaces the record's single remaining
`Not yet measured.` line -- §2's and §3's having been written when parts A
and B were measured, §4's is the only one left -- which is the one edit
`tests/test_acceptance_e16_lock.py::test_part_c_begins_not_yet_measured_or_a
_measured_heading` allows. With `--append` it puts the section at the END of
the record, beside an earlier run's, which is how a re-measurement after a
fix is recorded.

WHAT IS CHECKED HERE RATHER THAN TRUSTED
----------------------------------------
Parts A's and B's four, unchanged in substance: the raw is not a rehearsal
(`refuse_dry_run`), the run completed, no box path leaves the pin table, and
nothing shaped like part A's token reaches a committed file. Part C's own
`offenders_c` differs from part A's `offenders` in one character: the
sanctioned pin is `E16C_DIR=`, not `E16_DIR=`, because §1's amendment pins
part C's tree somewhere else (parts A's and B's were freed on 2026-09-15).
A single shared function spelling one pin would silently allow the other
part's path into this section.

WHAT PART C'S SECTION SAYS THAT THE OTHERS DO NOT
-------------------------------------------------
* **the token is not this instrument's, and it is not one value.** The
  values were in the traces already (P10) and this box's token rotated, so
  §4 cites EVERY distinct value's `sha256[:8]` beside the number of traces
  holding it (R15), plus the recorder distribution of the traces the copy
  held -- what WROTE the secrets, not what the measurement minted.
* **the amendments come out of the RAW record**, as part B's do: what §4
  says the run was amended by is then what the run was actually made under,
  and not prose this module carries on its own.
* **H4's four clauses get a table of their own.** §9 states one claim in
  four parts and the cell decides it as four (P13); a verdict word with no
  clause table beside it cannot show a reader which of the four carried it.
* **before and after are one table.** H4 is a difference: what the copy held
  before the pass and what it held after, counted the same way by the same
  function, with §9's own 273 beside the copy's count and gated by nothing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Parts A's assembler, for the checks and the edits that are one rule in one
# place. `FORBIDDEN`, `TOKEN_SHAPE` and `NOT_YET` are that module's facts
# about what a committed file may hold; `write_into` and `append_into` are
# its two ways of putting a section into the record.
from assemble_e16a import (FORBIDDEN, NOT_YET, TOKEN_SHAPE,  # noqa: E402,F401
                           Refused, append_into, refuse_dry_run, scrub,
                           write_into)
from e16c import (CELL_TITLES, DRY_TIMERS, EXPECTED_TRACES,  # noqa: E402
                  EXPECTED_VERSION, RULES, TIMERS, TOKEN_VAR)

#: The one sanctioned place a path on this box is written down in §4.
PIN = "E16C_DIR="

#: What §4 may say instead of a box path. `~` and not `$HOME`: the live
#: store is spelled `~/.sensorium` in every committed file and in §1's
#: amendment, and a section that spelled it two ways would read as two
#: stores.
LABELS = ("$E16C_DIR", "$REPO", "~")


def offenders_c(text: str) -> list[str]:
    """Every line §4 may not carry: a box path outside the `E16C_DIR=` pin,
    or anything shaped like part A's minted token."""
    return [ln for ln in text.splitlines()
            if (any(f in ln for f in FORBIDDEN) and PIN not in ln)
            or TOKEN_SHAPE.search(ln)]


def _rel_c(lens: dict, key: str) -> str:
    """One of the instrument's locations, as `$E16C_DIR/<name>`."""
    root = Path(lens["work_root"])
    try:
        return "$E16C_DIR/" + str(Path(lens[key]).relative_to(root))
    except ValueError:
        return str(lens[key])


def pin_table_c(lens: dict) -> list[str]:
    """§4's pin table: the work root spelled once, everything under it
    relative to that, and the live store as the name it has everywhere else.

    The last row is a LABEL rather than a location: `~/.sensorium` is what
    §1's amendment, `docs/redaction.md` and the CHANGELOG all call it, and
    the copy is what this measurement is about.
    """
    rows = [("work root", f"`{PIN}{lens['work_root']}`"),
            ("the copy (the subject)", f"`{_rel_c(lens, 'store')}/`"),
            ("transcripts", f"`{_rel_c(lens, 'transcripts')}/`"),
            ("instrument output", f"`{_rel_c(lens, 'out')}/`"),
            ("copied out of (never written to)", "`~/.sensorium`")]
    return (["| pin | path |", "|---|---|"]
            + [f"| {name} | {value} |" for name, value in rows])


def scrub_pairs_c(lens: dict, extra=()) -> list[tuple[str, str]]:
    """(needle, label) longest first, so a path under another path is not
    half-replaced by the shorter one. Part A's function with part C's
    labels: its `$E16_DIR` is part A's work root, which is not this one."""
    pairs = [(lens["work_root"], "$E16C_DIR"), (lens["repo"], "$REPO"),
             (str(Path.home()), "~"), *extra]
    return sorted(pairs, key=lambda pair: -len(pair[0]))


# -- the tables ------------------------------------------------------------
def verdict_table(raw: dict) -> list[str]:
    out = ["| cell | word | §9's rule | what was read |", "|---|---|---|---|"]
    for cell, result in raw["cells"].items():
        word = result["word"]
        out.append(f"| {CELL_TITLES[cell]} | **{word}** | "
                   f"{RULES[cell].get(word, '--')} | {result['read']} |")
    for row in raw["dropped"]:
        out.append(f"| {row['cell']} | dropped | -- | {row['reason']} |")
    return out


def versions_table(raw: dict) -> list[str]:
    """What produced the traces, and what retrofitted them.

    No driver-build row: part C rebuilds nothing, because it records
    nothing. What it must say instead is the version of the COMMAND
    (`preflight` refuses unless the venv reads it) and which recorders wrote
    the traces the copy held -- read from each trace's own `meta.recorder`,
    since §9's H4 is a claim about a store filled by three of them over a
    year.
    """
    versions = raw.get("versions") or {}
    rows = [("`sensorium` (the venv the command ran from)",
             versions.get("sensorium"), versions.get("expected",
                                                     EXPECTED_VERSION))]
    for name, count in (versions.get("recorders") or {}).items():
        label = "(none recorded — a Python trace)" if name == "None" else name
        rows.append((f"`recorder:` on {count} trace(s)", label, "--"))
    return (["| version | read | §1 expected |", "|---|---|---|"]
            + [f"| {name} | {got or '(none recorded)'} | {want} |"
               for name, got, want in rows])


def clause_table(raw: dict) -> list[str]:
    """H4's four clauses, each with what was read and the word it reached.

    Dropped whole when the cell never got to decide them: a table of four
    dashes reads as four measurements that came out empty, which is not the
    same fact as a cell that lost its input.
    """
    clauses = (raw["cells"].get("H4") or {}).get("clauses") or []
    if not clauses:
        return ["**The clause table: dropped.** " + (raw["cells"].get("H4")
                or {}).get("read", "the cell was never decided")]
    out = ["| # | the clause | what was read | word |", "|---|---|---|---|"]
    for row in clauses:
        out.append(f"| {row['clause']} | {row['what']} | {row['read']} | "
                   f"**{row['word']}** |")
    return out


def count_lines(raw: dict) -> list[str]:
    """§9's "the count line matches the dry run", as the two lines
    themselves plus the digests of the two whole stdouts.

    The summary line is quoted VERBATIM and carries no path; the sha256s are
    what makes clause 4 checkable by a reader who has the committed
    transcripts and not the run.
    """
    dry, real = raw.get("dry") or {}, raw.get("real") or {}
    out = ["| pass | exit | seconds | the summary line |",
           "|---|---|---|---|"]
    for label, row in (("`--dry-run`", dry), ("real", real)):
        out.append(f"| {label} | {row.get('rc')} | {row.get('seconds')} | "
                   f"`{row.get('summary') or '(no summary line)'}` |")
    same = raw.get("identical")
    verdict = ("byte-identical" if same is True else
               "NOT identical" if same is False else "not compared")
    out += ["", f"The two stdouts were {verdict}: "
                f"`sha256(dry) = {dry.get('stdout_sha256', '--')[:16]}`, "
                f"`sha256(real) = {real.get('stdout_sha256', '--')[:16]}`. "
                f"`--dry-run` said on stderr: "
                f"`{(dry.get('stderr') or '').strip() or '(nothing)'}`."]
    return out


def before_after(raw: dict) -> list[str]:
    """What the copy held before the pass and what it held after, counted by
    the same function over the same root. Every row is REPORTED; the gate is
    the clause table above."""
    before, after = raw.get("before") or {}, raw.get("after") or {}
    copied, modes = raw.get("copy") or {}, raw.get("modes") or {}
    rows = [
        (f"traces in the copy (`*.db`), against §9's {EXPECTED_TRACES}",
         copied.get("n_db"), "--"),
        (f"traces whose environment held `{TOKEN_VAR}`",
         copied.get("traces_holding_the_variable"), "--"),
        ("distinct values of it, each swept on its own (R15)",
         copied.get("distinct_tokens"), after.get("values_swept")),
        ("files holding any of those values' bytes",
         before.get("files_holding_a_value"),
         after.get("files_holding_a_value")),
        ("occurrences of them, summed", before.get("occurrences_total"),
         "--"),
        ("files whose count could not be read", "--",
         len(after.get("unreadable") or [])),
        ("files swept", len(before.get("files") or []) or None,
         after.get("files_examined")),
        ("`-wal` files", copied.get("n_wal"), after.get("n_wal")),
        ("`-shm` files", copied.get("n_shm"), after.get("n_shm")),
        ("files at mode 0600", "--",
         f"{modes.get('files_at_600')} of {modes.get('files')}"),
        ("`traces/` mode", "--", modes.get("traces_dir_mode")),
    ]
    per_value = (after.get("per_value") or {})
    return (["| reading | before | after |", "|---|---|---|"]
            + [f"| {name} | {_cell(b)} | {_cell(a)} |"
               for name, b, a in rows]
            + [f"| occurrences of `{sha8}` after | -- | {total} |"
               for sha8, total in sorted(per_value.items())]
            + ["", "The two file counts are not one-for-one: the sweep "
               "before the pass counted the `-wal`/`-shm` sidecars that "
               "`apply` then unlinked with the inode it replaced (C7), and "
               "the sweep after it counts the `invocations.jsonl` the "
               "command wrote into the copy as it ran. Both sweeps are the "
               "same function over the same root, so every file present at "
               "the time is in the count."])


def _token_digests(raw: dict) -> str:
    """Every distinct value as `sha256[:8] (N traces)`, in one clause.

    Digests and counts, never a value and never a length that would narrow
    one: this is the whole of what §4 is allowed to say about the secret it
    is a claim about.
    """
    rows = raw.get("token_sha8") or []
    if not rows:
        return "no digest was recorded"
    return ("`sha256(value)[:8]` = "
            + ", ".join(f"`{row['sha8']}` ({row['traces']} trace(s))"
                        for row in rows))


def _cell(value) -> str:
    """A reading, or `--`. Never a blank and never a zero for a number
    nobody took: `None` is what a phase that did not run leaves."""
    return "--" if value is None else str(value)


def amendments(raw: dict) -> list[str]:
    """The pre-registration amendments, from `raw["amendments"]`.

    §1's block is LOCKED and stays as written; an amendment is recorded
    beside it, stating the clause it corrects and why, so that a reader can
    check the difference rather than having to trust that nobody edited the
    pre-registration after the fact. Read from the raw record rather than
    from this module, so the section says what the run was made under.
    """
    return [line for line in (raw.get("amendments") or [])]


def dry_timer_phrase() -> str:
    """Part C's rehearsal timers, as they actually are. Not part A's: that
    table has a driver build and a refocus timer part C does not have, and a
    record that prints another instrument's settings under its own heading
    is a record whose numbers a reader cannot use."""
    return (f"each `redact` pass capped at {DRY_TIMERS['redact']} s, the "
            f"`info` sweep at {DRY_TIMERS['info']} s, each grep at "
            f"{DRY_TIMERS['grep']} s and the part at {DRY_TIMERS['part']} s "
            f"(a tenth of the measurement's {TIMERS['part']} s)")


def dry_run_block(raw: dict) -> list[str]:
    """The rehearsal's reading, from `dry_run_findings` in the raw record.

    §1's own instrument sentence requires a dry run, so §4 has to say what
    it found and what changed between it and the measurement. Part A's
    function with part C's decoy sentence and part C's timers.
    """
    findings = raw.get("dry_run_findings") or []
    if not findings:
        return []
    return (["", "#### The dry run", "",
             "Before the measurement, on a FABRICATED store of three "
             "synthetic traces carrying a `dry-` decoy that no content "
             f"pattern matches (P11), with {dry_timer_phrase()}, into a "
             "work root of its own that was deleted afterwards. What it "
             "found, and what changed in the instrument between it and the "
             "run above:", ""]
            + [f"- {line}" for line in findings])


# -- the section -----------------------------------------------------------
def render(raw: dict, date: str, suffix: str = "") -> str:
    refuse_dry_run(raw)
    if raw.get("status") != "complete":
        raise Refused("this results file is not a completed run "
                      f"(status = {raw.get('status')!r}: "
                      f"{raw.get('refusal')})")
    cells = raw["cells"]
    words = "  ".join(f"{CELL_TITLES[c]} {r['word']}"
                      for c, r in cells.items())
    body = [
        f"### measured {date}{suffix}",
        "",
        f"Measured once, on this box, under `e16c.sh`. **Part C: "
        f"{raw['part']}** — {words}. The subject was a COPY of "
        f"`~/.sensorium/traces` and its `redaction.key`: "
        f"{raw.get('n_db')} traces against §9's {EXPECTED_TRACES}, copied "
        f"into the work root and retrofitted there, so the live store was "
        f"read and never written (the retrofit of it is a post-merge chore, "
        f"C18). The token was NOT minted (P10) and it is not one value: "
        f"the traces already held {raw.get('distinct_tokens')} distinct "
        f"value(s) of `{TOKEN_VAR}` (the token rotated over the store's "
        f"life), each read from its own trace's `meta.env` through a "
        f"read-only connection and swept one at a time (R15, amended "
        f"below), never printed and never written anywhere but `grep`'s "
        f"own argument — {_token_digests(raw)}. "
        f"{raw['seconds']}s wall clock.",
        "",
    ]
    body += verdict_table(raw) + ["", "#### Pins", ""]
    body += pin_table_c(raw["lens"])
    body += dry_run_block(raw)
    block = amendments(raw)
    if block:
        body += ["", "#### Amendments, beside §1", ""] + block
    body += ["", "#### Versions", ""] + versions_table(raw)
    body += ["", "#### H4 — the four clauses", ""] + clause_table(raw)
    body += ["", "#### The count line", ""] + count_lines(raw)
    body += ["", "#### Before and after", ""] + before_after(raw)
    body += ["", "#### Phases", "", "| phase | seconds |", "|---|---|"]
    body += [f"| {p['name']} | {p['seconds']} |" for p in raw["phases"]]
    text = scrub("\n".join(body) + "\n", scrub_pairs_c(raw["lens"]))
    # The pin row is the ONE sanctioned place the work root is spelled, and
    # the scrub above turned it into a label naming itself. Restored after,
    # rather than exempted from, the scrub: a section that skipped the
    # scrubber for one line would be a section with one unchecked line.
    text = text.replace(f"`{PIN}$E16C_DIR`",
                        f"`{PIN}{raw['lens']['work_root']}`")
    bad = offenders_c(text)
    if bad:
        raise Refused("a box path outside the pin table: " + "; ".join(bad))
    return text


# -- the evidence committed beside the record ------------------------------
#: The transcripts §4 is worth committing: the two stdouts, byte for byte,
#: so clause 4 can be re-checked with `diff`, and the two stderrs. NOT the
#: `info` sweep's -- one file per trace, each printing the `argv` and `cwd`
#: of a program somebody ran a year ago, is a directory of somebody's shell
#: history rather than evidence for this claim. Their READING (exit code and
#: the `by` word, per trace) is in the results file.
KEPT = ("redact-dry.txt", "redact-real.txt", "redact-dry.stderr.txt",
        "redact-real.stderr.txt")


def artifacts(raw: dict, raw_path: Path, record: Path, dest: Path,
              extra=()) -> list[Path]:
    """`results-c.json` and the four redact transcripts, scrubbed."""
    pairs = scrub_pairs_c(raw["lens"], extra)
    dest.mkdir(parents=True, exist_ok=True)
    written = [record.with_suffix(f".results-{raw.get('label', 'c')}.json")]
    written[0].write_text(scrub(raw_path.read_text(), pairs))
    src = Path(raw["lens"]["transcripts"])
    for name in KEPT:
        one = src / name
        if not one.is_file():
            continue
        out = dest / one.name
        out.write_text(scrub(one.read_text(), pairs))
        written.append(out)
    bad = [f"{path}: {line}" for path in written
           for line in offenders_c(path.read_text())]
    if bad:
        raise Refused("a box path survived the scrub: " + "; ".join(bad[:5]))
    return written


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 2
    raw = json.loads(Path(argv[0]).read_text())
    record = Path(argv[1])
    date = __import__("datetime").date.today().isoformat()
    rest = argv[2:]
    extra = tuple(tuple(a.split("=", 1)) for a in rest if "=" in a
                  and not a.startswith("--"))
    if any(a.startswith("--artifacts=") for a in rest):
        refuse_dry_run(raw)
        dest = Path(next(a for a in rest
                         if a.startswith("--artifacts=")).split("=", 1)[1])
        for path in artifacts(raw, Path(argv[0]), record, dest, extra):
            print(f"wrote {path}")
        return 0
    section = render(raw, date, _opt(rest, "--suffix=") or "")
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
