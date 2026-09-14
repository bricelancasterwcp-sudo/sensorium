#!/usr/bin/env python3
"""Render E16 part A's §2 from `results-a.json`.

    .venv/bin/python tests/acceptance_e16/assemble_e16a.py \\
        <results-a.json> <record.md> [--write]

Prints the section. With `--write` it replaces the record's single
`Not yet measured.` line under `## 2. Part A` with it, which is the one edit
`tests/test_acceptance_e16_lock.py::test_part_a_begins_not_yet_measured_or_a_
measured_heading` allows.

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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e16a import DROPPED, EXPECTED, RULES, TOKEN_VAR    # noqa: E402,F401


class Refused(Exception):
    """A results file this assembler will not render."""


#: The record's own rule, re-applied to what is about to be appended to it:
#: a line may name a box path only as the `E16_DIR=` pin.
FORBIDDEN = ("/mnt/", "/home/")
PIN = "E16_DIR="

#: The four cells part A measures, with the words §1 gives each one, in the
#: order §9's table lists them.
CELL_TITLES = {"H1": "H1 (environment)", "H2": "H2", "H3": "H3",
               "H6": "H6 (`redaction.env`)"}


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
    return [ln for ln in text.splitlines()
            if any(f in ln for f in FORBIDDEN) and PIN not in ln]


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
    return (["| pin | path |", "|---|---|"]
            + [f"| {name} | {value} |" for name, value in rows])


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
    return (["| version | read | §1 expected |", "|---|---|---|"]
            + [f"| {name} | {got or '(none recorded)'} | {want} |"
               for name, got, want in rows])


def _expected_recorder(arm: str) -> str:
    key = {"python": "sensorium", "rust": "sensorium-rt",
           "typescript": "sensorium-ts"}[arm]
    return f"{key} {EXPECTED[key]}"


#: The prefixes whose files §1 names one by one. Everything else swept is
#: summarised by its top directory: the cargo build tree and the vitest
#: project copy are hundreds of files that no recorder wrote, and a table
#: nobody can read is not a table anybody checks. Every count is in
#: `results-a.json`, committed beside this record.
NAMED = ("store-a/", "rust-target/sensorium/spool/")


def h1_table(raw: dict) -> list[str]:
    sweep = raw["h1_sweep"]
    named = [f for f in sweep["files"] if f["path"].startswith(NAMED)]
    rest: dict = {}
    for f in sweep["files"]:
        if f["path"].startswith(NAMED):
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
        "- **The grep sweep is wider than §1's.** §1 sweeps the store and "
        "the spool directories; this one sweeps everything under the work "
        "root except the token file, and for the refocus value as well as "
        "the recording one. Wider in the only direction that can find a "
        "leak; the gate is still §1's — the recording token, every count 0.",
    ]


def render(raw: dict, date: str) -> str:
    refuse_dry_run(raw)
    if raw.get("status") != "complete":
        raise Refused("this results file is not a completed run "
                      f"(status = {raw.get('status')!r}: "
                      f"{raw.get('refusal')})")
    cells = raw["cells"]
    words = "  ".join(f"{c} {r['word']}" for c, r in cells.items())
    body = [
        f"### measured {date}",
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
    body += pin_table(raw["lens"]) + ["", "#### Amendments, beside §1", ""]
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


def main(argv: list[str]) -> int:
    if not 2 <= len(argv) <= 3:
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 2
    raw = json.loads(Path(argv[0]).read_text())
    record = Path(argv[1])
    date = __import__("datetime").date.today().isoformat()
    section = render(raw, date)
    if len(argv) == 3 and argv[2] == "--write":
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
