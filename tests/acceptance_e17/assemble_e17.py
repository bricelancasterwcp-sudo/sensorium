#!/usr/bin/env python3
"""Render E17's §2 from `results-<label>.json`.

    .venv/bin/python tests/acceptance_e17/assemble_e17.py \\
        <results.json> <record.md> [--write] [--artifacts=<dir>] [--dry-ok]

Prints the section. With `--write` it replaces the record's single
`Not yet measured.` line, which is the one edit
`tests/test_acceptance_e17_lock.py::test_section_two_begins_not_yet_
measured_or_a_measured_heading` allows. `--dry-ok` renders a REHEARSAL's
results to stdout and never writes: that is how the renderer gets its first
run before the measurement, rather than on it.

WHAT IS CHECKED HERE RATHER THAN TRUSTED
----------------------------------------
* **The raw is not a rehearsal.** `refuse_dry_run` reads `dry_run` and
  refuses both `True` and ABSENT: a results file that never said whether
  it was a rehearsal is not a results file this may publish.
* **The run completed.** A `status` that is not `complete` carries a
  refusal, not a measurement.
* **No box path leaves the pin row.** Every location is scrubbed to
  `$E17_DIR`, `$REPO` or `~`, the ONE `E17_DIR=` row is restored after the
  scrub rather than exempted from it, and `offenders` re-checks the result.
  R16: the two toolchain rows are written with `~` by the instrument, so
  the only line in a rendered section that may hold `/mnt/` or `/home/` is
  the work root's.
* **Nothing shaped like H6's minted token.** `TOKEN_SHAPE` refuses a line
  carrying one without this module ever being handed the value; the
  results file carries `sha256[:8]` and nothing else.

Self-contained by P14: `assemble_e16a.py` is another record's assembler
with another record's pin spelling, and one shared function spelling one
pin would silently admit the other part's path into this section.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e17_cells import CELL_TITLES, RULES                          # noqa: E402
from e17_run import Refused                                       # noqa: E402

#: The one sanctioned place a path on this box is written down in §2.
PIN = "E17_DIR="
#: What §2 may say instead of a box path. `~` and not `$HOME`: the live
#: store is spelled `~/.sensorium` in §1 and in every committed file, and
#: a section that spelled it two ways would read as two stores.
LABELS = ("$E17_DIR", "$REPO", "~")
FORBIDDEN = ("/mnt/", "/home/")
#: H6's token SHAPE, so `offenders` can refuse a line carrying one without
#: ever being handed the value. Not matched by §2's own prose, which says
#: `` `sk-e17-` plus 33 characters `` -- a backtick where a token has body.
TOKEN_SHAPE = re.compile(r"sk-e17-[A-Za-z0-9]{10,}")
NOT_YET = "Not yet measured."
#: The two rows §9 gives `—` in both columns, whose verdict-table rule
#: cell is therefore a dash and not a clause.
UNGATED = ("reported", "measured")


def refuse_dry_run(raw: dict) -> None:
    """The one refusal the rehearsal exists to exercise. Silent on a real
    record, which is what makes a caller's `refuse_dry_run(raw)` a
    statement rather than a value nobody looks at."""
    dry = raw.get("dry_run")
    if dry is not True and dry is not False:
        raise Refused("this results file does not say whether it was a dry "
                      f"run (dry_run = {dry!r}); absent is not false")
    if dry:
        raise Refused("this results file was written by a DRY RUN: it asked "
                      "two corpus cases under a tenth of the timers, so "
                      "none of its cells is about §1's subject. Pass "
                      "--dry-ok to render it to stdout.")


def offenders(text: str) -> list[str]:
    """Every line §2 may not carry: a box path outside the `E17_DIR=` pin,
    or anything shaped like H6's minted token."""
    return [ln for ln in text.splitlines()
            if (any(bad in ln for bad in FORBIDDEN) and PIN not in ln)
            or TOKEN_SHAPE.search(ln)]


def scrub_pairs(lens: dict) -> list[tuple[str, str]]:
    """(needle, label) longest first, so a path under another path is not
    half-replaced by the shorter one."""
    pairs = [(lens.get("work_root", ""), "$E17_DIR"),
             (lens.get("repo", ""), "$REPO"),
             (str(Path.home()), "~")]
    return sorted([p for p in pairs if p[0]], key=lambda pair: -len(pair[0]))


def scrub(text: str, pairs) -> str:
    for needle, label in pairs:
        text = text.replace(needle, label)
    return text


def _cell(value) -> str:
    """A reading, or `—`. Never a blank and never a zero for a number
    nobody took: `None` is what a phase that did not run leaves.

    A float is rounded for the page and NOT in the raw: `0.100077901966`
    is what the instrument measured and what `results-<label>.json`
    carries, and `0.1` is what a reader needs. Rounding at render time
    keeps both true.
    """
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


# -- the tables -------------------------------------------------------------
def verdict_table(raw: dict) -> list[str]:
    """§9's own PASS/STOP clause beside the word the cell reached. The two
    ungated rows get `—`, which is exactly what §9's table gives them."""
    out = ["| cell | word | §9's rule | what was read |", "|---|---|---|---|"]
    for cell, row in raw["cells"].items():
        word = row["word"]
        rule = "—" if word in UNGATED else RULES.get(cell, {}).get(word, "—")
        out.append(f"| {CELL_TITLES.get(cell, cell)} | **{word}** | {rule} | "
                   f"{row['read']} |")
    return out


def pin_table(pins) -> list[str]:
    """§2's pin table, straight from the raw record's `pins` block: the
    work root spelled once behind `E17_DIR=`, everything under it as
    `$E17_DIR/…`, and the two toolchain directories with `~`.

    A LIST of pairs or a dict: the instrument writes the list, because the
    order matters (the work root defines `$E17_DIR` for every row under
    it) and the results file is sorted on the way out.
    """
    pairs = pins.items() if isinstance(pins, dict) else [tuple(p) for p in pins]
    rows = [f"| {name} | `{PIN + value if name == 'work root' else value}` |"
            for name, value in pairs]
    return ["| pin | path |", "|---|---|", *rows]


def versions_table(raw: dict) -> list[str]:
    """The lens §1 puts on every number: the four versions it pins."""
    got = raw.get("versions") or {}
    rows = [("`sensorium` (the venv the server ran from)",
             got.get("sensorium"), got.get("expected", "0.18.0")),
            ("Python", got.get("python"), "—"),
            ("`mcp` (H2's oracle, the official SDK)", got.get("mcp"),
             "2.2.x"),
            ("Claude Code (H7's client)", got.get("claude"), "—")]
    return (["| version | read | §1 expected |", "|---|---|---|"]
            + [f"| {name} | {_cell(read)} | {want} |"
               for name, read, want in rows])


def clause_table(row: dict) -> list[str]:
    """One cell's clauses, each with what was read and the word it
    reached. A cell with none says so rather than printing an empty table,
    which would read as clauses that came out blank."""
    clauses = (row.get("detail") or {}).get("clauses") or []
    if not clauses:
        why = ("§9 gives this row no PASS/STOP column, so it has no clauses"
               if row["word"] in UNGATED else row["read"])
        return [f"**No clause table ({row['word']}).** {why}"]
    return (["| clause | what was read | word |", "|---|---|---|"]
            + [f"| {c['clause']} | {c['read']} | **{c['word']}** |"
               for c in clauses])


def detail_table(row: dict) -> list[str]:
    """The readings beside the clauses -- everything the cell put in
    `detail` but the clause list, which has a table of its own."""
    detail = {k: v for k, v in (row.get("detail") or {}).items()
              if k != "clauses"}
    if not detail:
        return []
    return ["", "| reading | value |", "|---|---|"] + [
        f"| `{name}` | {_cell(value)} |"
        for name, value in sorted(detail.items())]


def latency_block(raw: dict) -> list[str]:
    """§9's never-gated row, as the three numbers it is."""
    row = raw["cells"].get("latency") or {}
    detail = row.get("detail") or {}
    return (["| reading | value |", "|---|---|",
             f"| median `runs` through the wire | "
             f"{_cell(detail.get('mcp_ms'))} ms |",
             f"| median `runs` through the CLI | "
             f"{_cell(detail.get('cli_ms'))} ms |",
             f"| ratio | {_cell(detail.get('ratio'))}× |",
             f"| server spawn to the `server/discover` answer | "
             f"{_cell(detail.get('discover_ms'))} ms |"])


def phases_table(raw: dict) -> list[str]:
    rows = ["| phase | seconds | error |", "|---|---|---|"]
    for phase in raw.get("phases") or []:
        rows.append(f"| {phase['name']} | {phase['seconds']} | "
                    f"{_cell(phase.get('error'))} |")
    return rows


# -- the section ------------------------------------------------------------
def render(raw: dict, date: str) -> str:
    refuse_dry_run(raw)
    if raw.get("status") != "complete":
        raise Refused("this results file is not a completed run "
                      f"(status = {raw.get('status')!r}: "
                      f"{raw.get('refusal')})")
    cells = raw["cells"]
    words = "  ".join(f"{CELL_TITLES.get(c, c)} {row['word']}"
                      for c, row in cells.items())
    body = [
        f"### measured {date}",
        "",
        f"Measured once, on this box, under `e17.sh`. **E17: "
        f"{raw['part']}** — {words}. {raw.get('n_db')} traces in the copy. "
        f"{raw.get('seconds')}s wall clock.",
        "",
    ]
    body += verdict_table(raw)
    body += ["", "#### Pins", ""] + pin_table(raw.get("pins") or {})
    body += ["", "#### Versions", ""] + versions_table(raw)
    for cell, row in cells.items():
        if cell == "latency":
            continue
        body += ["", f"#### {cell} — {row['word']}", ""]
        body += clause_table(row) + detail_table(row)
    body += ["", "#### Latency", ""] + latency_block(raw)
    body += ["", "#### Phases", ""] + phases_table(raw)
    text = scrub("\n".join(body) + "\n", scrub_pairs(raw.get("lens") or {}))
    # The pin row is the ONE sanctioned place the work root is spelled, and
    # the scrub above turned it into a label naming itself. Restored AFTER
    # the scrub rather than exempted from it: a section that skipped the
    # scrubber for one line would be a section with one unchecked line.
    text = text.replace(f"`{PIN}$E17_DIR`",
                        f"`{PIN}{(raw.get('lens') or {}).get('work_root')}`")
    bad = offenders(text)
    if bad:
        raise Refused("a box path or a token outside the pin row: "
                      + "; ".join(bad[:5]))
    return text


def write_into(record: Path, section: str) -> None:
    text = record.read_text()
    if NOT_YET not in text:
        raise Refused(f"{record} no longer carries {NOT_YET!r}: §2 has "
                      "already been written, and E17 is measured once")
    record.write_text(text.replace(NOT_YET, section.rstrip("\n"), 1))


# -- the evidence committed beside the record ------------------------------
def artifacts(raw: dict, raw_path: Path, record: Path,
              dest: Path) -> list[Path]:
    """The results file and every kept transcript, scrubbed. A transcript
    is EVIDENCE and is copied whole -- its `$ argv` and `# cwd` lines are
    half of what makes it readable -- so the roots are replaced by the
    labels §2's pin table defines rather than the lines being dropped.
    `offenders` re-checks on the way out: a committed file is the last
    place to find that out."""
    pairs = scrub_pairs(raw.get("lens") or {})
    dest.mkdir(parents=True, exist_ok=True)
    written = [record.with_suffix(f".results-{raw.get('label', 'e17')}.json")]
    written[0].write_text(scrub(raw_path.read_text(), pairs))
    src = Path((raw.get("lens") or {}).get("transcripts", ""))
    if src.is_dir():
        for one in sorted(src.iterdir()):
            if not one.is_file():
                continue
            out = dest / one.name
            out.write_text(scrub(one.read_text(errors="replace"), pairs))
            written.append(out)
    bad = [f"{path.name}: {line}" for path in written
           for line in offenders(path.read_text())]
    if bad:
        raise Refused("a box path survived the scrub: " + "; ".join(bad[:5]))
    return written


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    raw_path, record = Path(argv[0]), Path(argv[1])
    doc = json.loads(raw_path.read_text())
    rest, date = argv[2:], datetime.date.today().isoformat()
    kept = next((a.split("=", 1)[1] for a in rest
                 if a.startswith("--artifacts=")), None)
    if kept is not None:
        refuse_dry_run(doc)
        for path in artifacts(doc, raw_path, record, Path(kept)):
            print(f"wrote {path}")
        return 0
    if "--dry-ok" in rest:
        # The rehearsal's path: rendered, printed, never written -- so a
        # dry run cannot reach the record by adding one flag to the line
        # that would have written a real one.
        doc = {**doc, "dry_run": False}
        sys.stdout.write(render(doc, date))
        return 0
    section = render(doc, date)
    if "--write" in rest:
        write_into(record, section)
        print(f"written into {record}")
    else:
        sys.stdout.write(section)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        sys.exit(2)
