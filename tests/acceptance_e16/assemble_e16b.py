#!/usr/bin/env python3
"""Render E16 part B's §3 from `results-b.json`.

    .venv/bin/python tests/acceptance_e16/assemble_e16b.py \\
        <results-b.json> <record.md> \\
        [--write | --append | --artifacts=<dir> [PATH=LABEL]...] \\
        [--suffix=<heading tail>]

Prints the section. With `--write` it replaces the record's single
remaining `Not yet measured.` line -- §2 having been written when part A was
measured, §3's is the only one left -- which is the one edit
`tests/test_acceptance_e16_lock.py::test_part_b_begins_not_yet_measured_or_a_
measured_heading` allows. With `--append` it puts the section at the END of
the record, beside an earlier run's, which is how a re-measurement after a
fix is recorded.

WHAT IS CHECKED HERE RATHER THAN TRUSTED
----------------------------------------
Part A's four, unchanged and imported rather than re-implemented: the raw is
not a dry run (`refuse_dry_run`), the run completed, no box path leaves the
pin table (`offenders`), and nothing shaped like the token reaches a
committed file. One rule, one place.

WHAT IS PART B'S OWN
--------------------
* **the verdict words are the cells'.** `RULES` is §9's PASS/STOP column for
  H1, H5 and H6, held against the record by the cell tests. H5's word is
  `measured` and the clause printed beside it is §9's own "n/a — an outlier
  ratio is a finding for CARRIED-DEBT, not a stop": a row with no gate says
  so in the table rather than being quietly given one.
* **the amendments come out of the RAW record.** Part A's assembler carries
  its amendment prose in the module; part B's reads
  `raw["amendments"]`, which `e16b.py` writes from `e16b_cells.AMENDMENTS`.
  What §3 says the run was amended by is then what the run was actually made
  under, and not what somebody later typed beside it.
* **the dry-run sentence is built from PART B's timers.** A's
  `dry_timer_phrase` reads A's `DRY_TIMERS` -- a different table, with a
  refocus timer part B does not have and no bench timer at all -- so
  reusing it would print part A's settings under part B's heading.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Part A's assembler, for the checks that are one rule in one place. `_rel`
# is private to that module by name only: it is the shared "this path, as
# `$E16_DIR/<name>`" reading that the pin table's rows are built from, and
# a second copy here would be a second thing to keep true.
from assemble_e16a import (Refused, _rel, offenders,  # noqa: E402,F401
                           pin_table, refuse_dry_run, scrub, scrub_pairs)
from e16b import (BASELINE, CELL_TITLES, DRY_TIMERS,  # noqa: E402
                  EXPECTED, EXPECTED_VALUES, RULE_OF, RULES,
                  SPOOL_OCCURRENCES, read_driver_build)


def _expected_recorder(arm: str) -> str:
    key = {"python": "sensorium", "rust": "sensorium-rt",
           "typescript": "sensorium-ts"}[arm]
    return f"{key} {EXPECTED[key]}"


# -- the tables ------------------------------------------------------------
def _rule_clause(cell: str, word: str) -> str:
    """§9's own clause for the word a cell reached.

    H5 never reaches PASS or STOP -- §9 gives it neither -- so the clause
    printed beside `measured` is the one §9 writes in its STOP column, which
    is the sentence saying there is no gate. A dash there would read as "no
    rule was stated", which is the opposite of what §9 says about cost.
    """
    clauses = RULES[RULE_OF[cell]]
    if word in clauses:
        return clauses[word]
    return clauses["STOP"] if cell == "H5" else "--"


def verdict_table(raw: dict) -> list[str]:
    out = ["| cell | word | §9's rule | what was read |", "|---|---|---|---|"]
    for cell, result in raw["cells"].items():
        word = result["word"]
        out.append(f"| {CELL_TITLES[cell]} | **{word}** | "
                   f"{_rule_clause(cell, word)} | {result['why']} |")
    for row in raw["dropped"]:
        out.append(f"| {row['cell']} | dropped | -- | {row['reason']} |")
    return out


def pins(lens: dict) -> list[str]:
    """Part A's pin table, plus the two trees H5 needs.

    The baseline worktree is a location like any other and §1's amendment
    pins it by name (`$E16_DIR/baseline-7dd25d2`); the bench scratch store
    is where the two `bench.report` runs point `SENSORIUM_DIR`, so that
    neither table can write into the store H1 sweeps. Inserted BEFORE the
    driver row, which part A's table keeps last because it is a label rather
    than a path.
    """
    rows = pin_table(lens)
    extra = [f"| baseline worktree (`{BASELINE}`) | "
             f"`{_rel(lens, 'baseline')}/` |",
             f"| bench scratch store | `{_rel(lens, 'bench')}/` |"]
    return rows[:-1] + extra + [rows[-1]]


def versions_table(raw: dict) -> list[str]:
    """The versions, under the line that says which BINARY produced them.

    Part A's shape and part A's reason, against part B's expectations: every
    string below comes from the source tree or from a trace, and none of
    them can tell a current driver from a stale one, so an unstamped run
    drops the whole block rather than letting them read as a statement about
    the binary.
    """
    build = read_driver_build(raw.get("driver_build"))
    if build["word"] != "measured":
        return [f"**Versions: dropped.** {build['why']}"]
    if not raw.get("versions"):
        # The phase left `None`, so there is nothing to read. Said, not
        # crashed: a renderer that raises here leaves the operator with a
        # traceback instead of a section that names the hole.
        return ["**Versions: dropped.** the versions phase did not run, so "
                "no recorder, driver or tool version was read"]
    b = build["build"]
    driver_line = (
        f"**Driver built by the run (R37):** `cargo build --release -p "
        f"cargo-sensorium` in {b['seconds']}s before anything was recorded; "
        f"`{b['binary']}`, {b['size']} bytes, mtime {_iso(b['mtime'])}."
        # No code span around cargo's own line: it carries backticks of its
        # own, and a span around them ends early.
        + (f" cargo said: {b['finished_line']}"
           if b.get("finished_line") else ""))
    versions = raw["versions"]
    rows = [("`sensorium` (installed)", versions["sensorium"],
             EXPECTED["sensorium"])]
    for arm in ("python", "rust", "typescript"):
        rows.append((f"`recorder:` on the {arm} trace",
                     versions["recorder"].get(arm), _expected_recorder(arm)))
    for arm, value in sorted(versions["driver_version"].items()):
        # Spelled as the trace spells it -- `cargo-sensorium 0.8.0`, not a
        # bare `0.8.0` beside it, which reads as a difference where there is
        # none. Only the Rust driver has a pre-registered version: the
        # TypeScript row carries the PYTHON driver's, which §1 does not name
        # in this column.
        want = (f"cargo-sensorium {EXPECTED['cargo-sensorium']}"
                if arm == "rust" else "--")
        rows.append((f"`driver_version` on the {arm} trace", value, want))
    for tool, value in sorted((versions["tools"] or {}).items()):
        rows.append((f"`{tool}` under the scrubbed environment", value, "--"))
    rows.append((f"`python` in the `{BASELINE}` worktree",
                 (raw.get("baseline") or {}).get("python_version"), "--"))
    return ([driver_line, "",
             "| version | read | §1 expected |", "|---|---|---|"]
            + [f"| {name} | {got or '(none recorded)'} | {want} |"
               for name, got, want in rows])


def _iso(epoch: float) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(epoch).isoformat(timespec="seconds")


#: The four sets H1-values reads, in §1's amendment's order, with what each
#: one is required to hold.
H1_COLUMNS = (("store", "every file under the store", "0"),
              ("headers", "Rust `<pid>.proc.json`", "0"),
              ("spools", "Rust `.spool`", f"{SPOOL_OCCURRENCES} together"),
              ("ts_spools", "TypeScript spool", "0"))


def h1_values_table(raw: dict) -> list[str]:
    """Every file, its set, its occurrences and what the set required.

    Named one by one, all four sets: part B sweeps this run's own trees
    only -- §1's amendment says part A's stores are not read -- so the table
    is short enough to print whole, which is what "checked with `grep`, per
    file" asks for. Everything else the instrument swept (the disposable
    copies, the transcripts, the cargo build tree) is summarised under it as
    a reading outside the four.
    """
    sweep = raw["h1_values"]
    out = ["| file (under `$E16_DIR`) | set | occurrences | required |",
           "|---|---|---|---|"]
    # One row per FILE. The TypeScript spool lives under the store, so its
    # files are in two of the four readings, and a row per reading would
    # print the same file twice -- and name the same leak twice under it.
    seen: dict[str, dict] = {}
    for key, label, want in H1_COLUMNS:
        for row in sweep[key]:
            entry = seen.setdefault(row["path"],
                                    {"labels": [], "wants": [],
                                     "occurrences": row["occurrences"]})
            entry["labels"].append(label)
            entry["wants"].append(want)
    for path, entry in seen.items():
        want = " / ".join(dict.fromkeys(entry["wants"]))
        mark = ("  ← **STOP**" if entry["occurrences"]
                and "0" in entry["wants"] else "")
        out.append(f"| `{path}` | {' + '.join(entry['labels'])} | "
                   f"{entry['occurrences']} | {want}{mark} |")
    total = sum(r["occurrences"] for r in sweep["spools"])
    out += ["", f"The Rust `.spool` files hold {total} occurrence(s) "
            f"together, against the {SPOOL_OCCURRENCES} §1's amendment "
            "predicts: the three rows the CONVERTER redacts (`copy`, the "
            "`Headers` `Debug` text and `secret`'s RETURN) are plaintext in "
            "the spool until it runs, and the fourth Rust row — the "
            "`token` parameter delta — is taken by the recorder before the "
            "spool is written."]
    rest: dict = {}
    for row in sweep.get("other") or []:
        top = row["path"].split("/")[0]
        agg = rest.setdefault(top, {"n": 0, "max": 0})
        agg["n"] += 1
        agg["max"] = max(agg["max"], row["occurrences"] or 0)
    if rest:
        out += ["", "Swept and listed, outside the four readings and gated "
                "by none of them — the disposable copies, the transcripts, "
                "the cargo build tree (the two Rust spool files §1's "
                "amendment does not name among them: `<pid>.runner.json` "
                "and `invocation.json`), the TMPDIR every recording ran "
                "under and this instrument's own output, by top directory:",
                "",
                "| path (under `$E16_DIR`) | files swept | max occurrences |",
                "|---|---|---|"]
        # A non-zero out here decides nothing — the gate is §1's four
        # readings — but a number a reader has to notice for themselves in a
        # summary row is a number that gets missed. Marked, and named under
        # the table.
        out += [f"| `{top}/` | {agg['n']} | {agg['max']}"
                + ("  ← **not gated, but non-zero**" if agg["max"] else "")
                + " |"
                for top, agg in sorted(rest.items())]
        beyond = [row for row in (sweep.get("other") or [])
                  if row["occurrences"]]
        if beyond:
            out += ["", "Outside the gate and non-zero — named here because "
                    "§9's locked H1 is a claim about every file, and these "
                    "are files this run made: "
                    + ", ".join(f"`{row['path']}` ({row['occurrences']})"
                                for row in beyond) + "."]
    return out


def h5_tables(raw: dict) -> list[str]:
    """Both tables verbatim, then the three ratios per row.

    Verbatim because a bench table is a measurement of one machine and one
    day, and a summary of it is a different claim; the ratios because §1's
    amendment asks for `recorded/baseline` at each commit and for HEAD's
    over the baseline's, which is the only one of the three that is about
    this branch rather than about this box.
    """
    cell = raw["cells"]["H5"]
    if cell["word"] != "measured":
        return [f"**H5: dropped.** {cell['why']}"]
    out = [f"`python -c \"from corpus._bench import bench; "
           f"bench.report(reps={_reps(raw)})\"`, in each tree, back to back "
           "on this box.", "",
           f"**At `{BASELINE}`:**", "", "```",
           cell["baseline_table"].strip(), "```", "",
           "**At HEAD (this branch):**", "", "```",
           cell["head_table"].strip(), "```", "",
           f"| workload | tier | recorded/baseline at `{BASELINE}` | "
           "recorded/baseline at HEAD | HEAD over "
           f"`{BASELINE}` |", "|---|---|---|---|---|"]
    for row in cell["rows"]:
        out.append(f"| {row['workload']} | {row['tier']} | "
                   f"{_ratio(row['ratio_baseline'])} | "
                   f"{_ratio(row['ratio_head'])} | "
                   f"{_ratio(row['ratio_of_ratios'])} |")
    out += ["", "Never gated (§9, and rust/HONESTY.md §10: cost is "
            "reported, never gated). An outlier is a CARRIED-DEBT finding, "
            "not a stop."]
    return out


def _reps(raw: dict) -> str:
    """The `reps` the two bench runs ACTUALLY used, read off the run.

    Not `BENCH_REPS`: the dry run's tables are taken at one rep, and a
    caption built from the constant printed `reps=5` over `best of 1 timed
    runs` in the evidence directly beneath it. The two trees are stated
    separately if they ever differ, which they must not.
    """
    used = [str((raw.get("bench") or {}).get(tree, {}).get("reps"))
            for tree in ("baseline", "head")]
    return used[0] if used[0] == used[1] else " and ".join(used)


def _ratio(value: float | None) -> str:
    """A ratio, or `--` -- never a zero and never a blank cell: a row one
    table did not carry is a reading nobody took."""
    return "--" if value is None else f"{value:.2f}"


def h6_values_table(raw: dict) -> list[str]:
    out = ["| trace | arm | `values redacted:` | §1 expected | "
           "`redaction.env` names |", "|---|---|---|---|---|"]
    for row in raw["h6_values"]:
        names = ", ".join(f"`{n}`" for n in (row["names"] or [])) or "(none)"
        want = EXPECTED_VALUES.get(row["arm"], "--")
        mark = "" if row["values"] == want else "  ← **STOP**"
        out.append(f"| `{row['run']}` | {row['arm']} | {row['values']} | "
                   f"{want}{mark} | {names} |")
    return out


def amendments(raw: dict) -> list[str]:
    """The pre-registration errors this run was measured under, as the
    INSTRUMENT recorded them.

    Beside §1, never edited into it: §1 is locked, and an error found before
    launch is pinned by an amendment with the corrected clause next to it.
    Read from the raw record rather than carried here, so the block is a
    statement about the run and not about the assembler. Empty when the run
    carried none -- an empty list prints nothing rather than a sentence
    claiming there was nothing to amend.
    """
    return list(raw.get("amendments") or [])


def dry_timer_phrase() -> str:
    """Part B's dry-run timers, as they actually are.

    Not part A's: that table has a refocus timer part B does not have and no
    bench timer at all, and a record that prints another instrument's
    settings under its own heading is a record whose numbers a reader cannot
    use.
    """
    return (f"the recordings capped at {DRY_TIMERS['record']} s, each bench "
            f"table at {DRY_TIMERS['bench']} s, the driver build at "
            f"{DRY_TIMERS['build']} s and the baseline worktree at "
            f"{DRY_TIMERS['baseline']} s")


def dry_run_block(raw: dict) -> list[str]:
    """The dry-run reading, from `dry_run_findings` in the raw record.

    §1's own instrument sentence requires a dry run, so §3 has to say what
    that dry run found and what changed between it and the measurement.
    Part A's function with part B's timer sentence -- see
    `dry_timer_phrase`.
    """
    findings = raw.get("dry_run_findings") or []
    if not findings:
        return []
    return (["", "#### The dry run", "",
             "Before the measurement, with a `dry-` decoy that cannot match "
             f"the content rule and {dry_timer_phrase()}, into a work root "
             "of its own that was deleted afterwards. What it found, and "
             "what changed in the instrument between it and the run above:",
             ""]
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
        f"Measured once, on this box, under `e16b.sh`. **Part B: "
        f"{raw['part']}** — {words}. The token was `sk-e16-` plus 33 "
        f"characters, minted by the instrument, never printed and never "
        f"committed: `sha256(token)[:8] = {raw['token']['sha8']}`. Every "
        f"recording ran under a scrubbed environment of exactly "
        + ", ".join(f"`{n}`" for n in raw["preflight"]["allowlist"])
        + " — no other name reached a recorder, and the instrument refuses "
          "to start unless none of them fires rule v1, which is what makes "
          "H6's \"exactly one name\" a fact about the token. The two bench "
          "tables ran with the token OUT of the environment: H5 is a "
          "measurement of overhead, and a secret in a tree H1 does not "
          f"sweep is a secret nobody checked. {raw['seconds']}s wall clock.",
        "",
    ]
    body += verdict_table(raw) + ["", "#### Pins", ""]
    body += pins(raw["lens"])
    body += dry_run_block(raw)
    block = amendments(raw)
    if block:
        body += ["", "#### Amendments, beside §1", ""] + block
    body += ["", "#### Versions", ""] + versions_table(raw)
    body += ["", "#### H1 (values) — the token's bytes, per file", ""]
    body += h1_values_table(raw)
    body += ["", "#### H5 — the overhead, before and after", ""]
    body += h5_tables(raw)
    body += ["", "#### H6 (`redaction.values`) — the census", ""]
    body += h6_values_table(raw)
    body += ["", "#### Phases", "", "| phase | seconds |", "|---|---|"]
    body += [f"| {p['name']} | {p['seconds']} |" for p in raw["phases"]]
    text = "\n".join(body) + "\n"
    bad = offenders(text)
    if bad:
        raise Refused("a box path outside the pin table: " + "; ".join(bad))
    return text


NOT_YET = "Not yet measured."


def write_into(record: Path, section: str) -> None:
    """Replace the ONE remaining `Not yet measured.`, which is §3's.

    Refused when there are two: §2's was replaced the day part A was
    measured, and an assembler that cannot tell which part it is writing
    into would put part B's section under part A's heading.
    """
    text = record.read_text()
    left = text.count(NOT_YET)
    if left != 1:
        raise Refused(f"{record} carries {left} {NOT_YET!r} line(s), not 1: "
                      "§3's is meant to be the only one left, and part B is "
                      "measured once")
    record.write_text(text.replace(NOT_YET, section.rstrip("\n"), 1))


def append_into(record: Path, section: str) -> None:
    """A re-measurement's section, BESIDE the one before it."""
    text = record.read_text()
    if NOT_YET in text:
        raise Refused(f"{record} still says {NOT_YET!r}: there is no earlier "
                      "run for this one to be appended beside")
    heading = section.splitlines()[0]
    if heading in text:
        raise Refused(f"{record} already carries {heading!r}")
    record.write_text(text.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n")


# -- the evidence committed beside the record ------------------------------
def artifacts(raw: dict, raw_path: Path, record: Path, dest: Path,
              extra=()) -> list[Path]:
    """`results-b.json` and every transcript, scrubbed.

    A transcript is EVIDENCE and is copied whole, so the roots are replaced
    by the labels §3's pin table defines rather than the lines being
    dropped. The token's own value was already replaced with `<token>` when
    the transcript was written; `offenders` re-checks both facts on the way
    out, because a committed file is the last place to find out.
    """
    pairs = scrub_pairs(raw["lens"], extra)
    dest.mkdir(parents=True, exist_ok=True)
    written = [record.with_suffix(f".results-{raw.get('label', 'b')}.json")]
    written[0].write_text(scrub(raw_path.read_text(), pairs))
    src = Path(raw["lens"]["transcripts"])
    for one in sorted(src.glob("*.txt")):
        out = dest / one.name
        out.write_text(scrub(one.read_text(), pairs))
        written.append(out)
    bad = [f"{path}: {line}" for path in written
           for line in offenders(path.read_text())]
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
