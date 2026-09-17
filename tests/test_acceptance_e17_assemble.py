"""E17's assembler, exercised before the run it will have to render.

`assemble_e17.py` turns `results-<label>.json` into the record's §2. Its
first run must not be the measured one: a renderer that raises, or that
leaks a box path into a committed document, is a defect discovered after
the one measurement it exists to publish. So the whole path -- `render`,
`offenders`, `write_into` -- is driven here over a SYNTHETIC results dict
with every cell word present (a PASS, a STOP, a dropped, a `reported` and
a `measured`) against a COPY of the record.

WHAT THIS FILE HOLDS
--------------------
* The rendered section carries no `/mnt/` and no `/home/` outside the one
  `E17_DIR=` pin row -- the record's own rule, re-applied to what is about
  to be appended to it.
* §1 SURVIVES the write. The lock test's two readers are copied in (not
  imported: a copy that drifts is caught by the lock test itself, and an
  import would make this file fail for the other's reasons) and run on the
  written copy, so a `write_into` that replaced the wrong line reddens
  here rather than in the byte-lock after the fact.
* A dry run is REFUSED by `--write` and rendered by `--dry-ok`, which is
  what lets the rehearsal exercise the renderer without ever being able to
  publish a rehearsal as a measurement.

PRE-REGISTERED MUTANTS FOR THIS MODULE
--------------------------------------
* `offenders` allowing `/home/` (dropping it from `FORBIDDEN`) -- caught by
  `test_a_box_path_in_a_non_pin_row_is_refused`.
* `refuse_dry_run` treating an ABSENT `dry_run` key as false -- caught by
  `test_a_results_file_that_does_not_say_whether_it_was_dry_is_refused`.
* `write_into` appending instead of replacing `Not yet measured.` -- caught
  by `test_write_into_replaces_the_not_yet_line_and_leaves_section_one`.
* `render` rendering a run whose `status` is not `complete` -- caught by
  `test_an_unfinished_run_is_refused`.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "acceptance_e17"))

import assemble_e17                                               # noqa: E402
from assemble_e17 import (PIN, offenders, refuse_dry_run,          # noqa: E402
                          render, write_into)
from e17_cells import CELL_TITLES, RULES                          # noqa: E402
from e17_run import Refused                                       # noqa: E402

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-16-sensorium-e17-mcp.md")
_SPEC = (REPO / "docs" / "superpowers" / "specs"
         / "2026-09-16-sensorium-mcp-stdio-design.md")
_PLAN = (REPO / "docs" / "superpowers" / "plans"
         / "2026-09-16-sensorium-mcp-stdio.md")
_SPEC_HEAD = "## 9. E17, pre-registered"
_PLAN_HEAD = ("## Pre-registration (Task 0 appends this block verbatim to "
              "the record's §1 as a dated amendment; the lock test holds "
              "it there)")

#: A work root and an out directory shaped like the ones `e17.sh` is given.
#: Box-shaped on purpose -- this file's whole job is to prove they do not
#: reach the rendered section -- and built from fragments so no committed
#: line here is itself a box path.
WORK = "/" + "mnt/extra/sensorium-rung2/e17"
#: The launcher's own home, which the scrub turns into `~`, and a
#: directory under NO label, which it cannot reach.
HOME = str(Path.home())
ELSEWHERE = "/" + "mnt/elsewhere"
#: ...and somebody ELSE's home, which no label covers either: the scrub
#: turns THIS launcher's home into `~` and cannot touch another.
OTHER_HOME = "/" + "home/not-this-user"


# -- the lock test's readers, copied (see the module docstring) -------------
def _after(text: str, heading: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip("\n") == heading:
            return lines[i + 1:]
    raise AssertionError(f"no heading {heading!r} in this document")


def body_to_heading(text: str, heading: str) -> str:
    out = []
    for line in _after(text, heading):
        if re.match(r"^#{1,6} ", line):
            break
        out.append(line)
    return "".join(out).strip("\n")


def body_to_rule(text: str, heading: str) -> str:
    out = []
    for line in _after(text, heading):
        if line.rstrip("\n") == "---":
            break
        out.append(line)
    return "".join(out).strip("\n")


# -- the synthetic run ------------------------------------------------------
def _cell(word: str, read: str, detail: dict | None = None) -> dict:
    return {"word": word, "read": read, "detail": detail or {}}


def raw(**over) -> dict:
    """One completed run with every word a cell can reach in it."""
    doc = {
        "status": "complete", "dry_run": False, "label": "e17",
        "part": "DONE-WITH-STOP", "n_db": 273, "seconds": 931.4,
        "started": 1.0, "finished": 932.4, "token_sha8": "41285dda",
        "cells": {
            "H1": _cell("PASS", "0 failure(s); 115 cases / 253 questions",
                        {"clauses": [{"clause": "failures", "word": "PASS",
                                      "read": "0 failure(s)"}],
                         "census": [115, 253]}),
            "H2": _cell("PASS", "pytest exited 0; 10 passed",
                        {"rc": 0, "passed": 10, "skipped": 0}),
            "H3": _cell("PASS", "65392 bytes after the header",
                        {"bytes": 65392, "cli_bytes": 28507987}),
            "H4": _cell("PASS", "9 tools without the flag; 11 with"),
            "H5": _cell("STOP", "the child's group was STILL THERE 2.0 s "
                        "after the cancel",
                        {"clauses": [{"clause": "group-gone", "word": "STOP",
                                      "read": "still there"}]}),
            "H6": _cell("dropped", "`mcp.jsonl` was not read"),
            "H7": _cell("reported", "4 sensorium tool(s) used"),
            "latency": _cell("measured", "median 3812.0 ms vs 3720.0 ms",
                             {"mcp_ms": 3812.0, "cli_ms": 3720.0,
                              "ratio": 1.02, "discover_ms": 41.2}),
        },
        "dropped": [{"cell": "H6", "word": "dropped",
                     "reason": "`mcp.jsonl` was not read"}],
        "phases": [{"name": "preflight", "seconds": 1.2, "error": None},
                   {"name": "h6-secrecy", "seconds": 8.0,
                    "error": "RuntimeError: no run: line"}],
        "versions": {"sensorium": "0.18.0", "expected": "0.18.0",
                     "mcp": "2.2.0", "claude": "2.1.258",
                     "python": "3.13.5"},
        # A LIST of pairs, which is what the instrument writes: the
        # results file is sorted on the way out, and the work root -- which
        # defines `$E17_DIR` for every row under it -- has to stay first.
        "pins": [["work root", WORK],
                 ["the copy (the subject)", "$E17_DIR/store/"],
                 ["H4's store", "$E17_DIR/h4/store/"],
                 ["transcripts", "$E17_DIR/transcripts/"],
                 ["instrument output", "$E17_DIR/out/"],
                 ["copied out of (never written to)", "~/.sensorium"],
                 ["E17_CARGO_BIN", "~/.cargo/bin"],
                 ["E17_NODE_BIN", "~/.nvm/versions/node/v24.16.0/bin"],
                 ["H1's cell timer", "600 s"]],
        "lens": {"work_root": WORK, "store": WORK + "/store",
                 "transcripts": WORK + "/transcripts", "repo": str(REPO),
                 "out": WORK + "/out", "live": HOME + "/.sensorium"},
        "h1": {"runs": [{"case": None, "rc": 0, "seconds": 63.2}]},
        "h3": {"run": "20260901-210236-2d791a", "events": 93283},
    }
    doc.update(over)
    return doc


@pytest.fixture()
def record(tmp_path) -> Path:
    copy = tmp_path / DOC.name
    shutil.copy2(DOC, copy)
    # The live record has been measured (its §2 is written); the tests need the
    # unmeasured shape, so the copy's §2 is reset to the line write_into replaces.
    text = copy.read_text()
    head, sep, _ = text.partition("## 2. Measured")
    assert sep, "the record has no '## 2. Measured' heading"
    copy.write_text(head + sep + "\n\nNot yet measured.\n")
    return copy


# -- the section ------------------------------------------------------------
def test_render_names_every_cell_with_its_word_and_the_specs_rule():
    text = render(raw(), "2026-09-17")
    assert text.startswith("### measured 2026-09-17\n")
    assert "**E17: DONE-WITH-STOP**" in text
    assert "273 traces in the copy" in text
    assert "931.4s wall clock" in text
    for cell, title in CELL_TITLES.items():
        assert f"| {title} |" in text, cell
    # §9's own PASS text rides beside a PASS...
    assert RULES["H2"]["PASS"] in text
    # ...and its STOP text beside the STOP.
    assert RULES["H5"]["STOP"] in text
    # ...and the two rows §9 never gates say so with a dash.
    assert "| H7 the deploy target | **reported** | — |" in text
    assert "| latency | **measured** | — |" in text


def test_render_carries_the_verdict_sentence_in_section_order():
    text = render(raw(), "2026-09-17")
    sentence = [ln for ln in text.splitlines()
                if ln.startswith("Measured once, on this box")][0]
    assert "H1 parity PASS  H2 conformance PASS" in sentence
    for heading in ("#### Pins", "#### Versions", "#### H1 — PASS",
                    "#### H5 — STOP", "#### H6 — dropped",
                    "#### Latency", "#### Phases"):
        assert f"\n{heading}\n" in text, heading
    assert text.index("#### Pins") < text.index("#### Versions")
    assert text.index("#### Versions") < text.index("#### H1 — PASS")
    assert text.index("#### Latency") < text.index("#### Phases")


def test_render_leaves_no_box_path_outside_the_pin_row():
    text = render(raw(), "2026-09-17")
    assert offenders(text) == []
    stray = [ln for ln in text.splitlines()
             if ("/mnt/" in ln or "/home/" in ln)]
    assert len(stray) == 1 and PIN in stray[0], stray
    assert f"`{PIN}{WORK}`" in text
    # ...and the toolchain rows are spelled with `~`, never with a home.
    assert "| E17_CARGO_BIN | `~/.cargo/bin` |" in text
    # The work root is the FIRST row: every row under it reads `$E17_DIR`,
    # and a table that defined the label last would be read top to bottom
    # with eight unresolved references before the definition.
    table = text.split("#### Pins", 1)[1].splitlines()
    assert table[4].startswith("| work root |"), table[:6]


def test_a_box_path_in_a_non_pin_row_is_refused():
    """Catches: `FORBIDDEN` narrowed to one prefix, or the pin exemption
    widened past the one row it is for. Both prefixes are tried: a check
    that only ever saw a `/mnt/` path could lose `/home/` unnoticed."""
    for path in (ELSEWHERE, OTHER_HOME):
        leaky = raw()
        leaky["cells"]["H4"] = _cell("PASS", "the copy under " + path)
        with pytest.raises(Refused):
            render(leaky, "2026-09-17")
        assert offenders(f"| something | `{path}` |") != [], path
    assert offenders("| a token | `sk-e17-"
                     + "a" * 33 + "` |") != []
    assert offenders(f"| work root | `{PIN}{WORK}` |") == []


def test_an_unfinished_run_is_refused():
    with pytest.raises(Refused):
        render(raw(status="refused", refusal="preflight failed"),
               "2026-09-17")


def test_a_dry_run_is_refused_by_render():
    with pytest.raises(Refused):
        render(raw(dry_run=True), "2026-09-17")


def test_a_results_file_that_does_not_say_whether_it_was_dry_is_refused():
    """Catches: an absent `dry_run` key read as false. Absent is not
    false -- it is a results file that never said."""
    blind = raw()
    del blind["dry_run"]
    with pytest.raises(Refused):
        refuse_dry_run(blind)
    refuse_dry_run(raw())            # ...and a real one passes silently


# -- the edit into the record ----------------------------------------------
def test_write_into_replaces_the_not_yet_line_and_leaves_section_one(record):
    """The one edit the lock allows, and the proof it did not disturb §1:
    both locked bodies still equal their sources on the written copy."""
    before = record.read_text()
    assert before.count("Not yet measured.") == 1
    section = render(raw(), "2026-09-17")
    write_into(record, section)
    after = record.read_text()
    assert "Not yet measured." not in after
    lines = after.splitlines()
    first = next(ln for ln in lines[lines.index("## 2. Measured") + 1:]
                 if ln.strip())
    assert first.startswith("### measured 2026-09-17")
    assert (body_to_heading(after, "### 9. E17, pre-registered")
            == body_to_heading(_SPEC.read_text(), _SPEC_HEAD))
    assert (body_to_heading(after, "### The plan's pre-registration block")
            == body_to_rule(_PLAN.read_text(), _PLAN_HEAD))
    stray = [ln for ln in lines
             if ("/mnt/" in ln or "/home/" in ln) and "E17_DIR=" not in ln]
    assert stray == [], stray


def test_write_into_refuses_a_record_already_written(record):
    write_into(record, render(raw(), "2026-09-17"))
    with pytest.raises(Refused):
        write_into(record, render(raw(), "2026-09-18"))


# -- the command line -------------------------------------------------------
def test_dry_ok_renders_to_stdout_and_never_writes(tmp_path, record, capsys):
    """The rehearsal's exercise of the renderer: a dry results file is
    rendered and NOT written, so the first run of `render` is never the
    measured one."""
    path = tmp_path / "results-dry.json"
    path.write_text(json.dumps(raw(dry_run=True, label="dry")))
    before = record.read_text()
    assert assemble_e17.main([str(path), str(record), "--write",
                              "--dry-ok"]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("### measured ")
    assert offenders(printed) == []
    assert record.read_text() == before


def test_write_puts_the_section_into_the_record(tmp_path, record):
    path = tmp_path / "results-e17.json"
    path.write_text(json.dumps(raw()))
    assert assemble_e17.main([str(path), str(record), "--write"]) == 0
    assert "### measured " in record.read_text()


def test_write_refuses_a_dry_results_file(tmp_path, record):
    path = tmp_path / "results-dry.json"
    path.write_text(json.dumps(raw(dry_run=True)))
    with pytest.raises(Refused):
        assemble_e17.main([str(path), str(record), "--write"])
    assert "Not yet measured." in record.read_text()


def test_artifacts_copies_the_transcripts_and_scrubs_them(tmp_path, record):
    src = Path(raw()["lens"]["transcripts"])
    kept = tmp_path / "transcripts"
    kept.mkdir()
    (kept / "h3-tree.txt").write_text(f"$ tree under {src}\nexit 0: ok\n")
    doc = raw()
    doc["lens"]["transcripts"] = str(kept)
    path = tmp_path / "results-e17.json"
    path.write_text(json.dumps(doc))
    dest = tmp_path / "evidence"
    assert assemble_e17.main([str(path), str(record),
                              f"--artifacts={dest}"]) == 0
    written = sorted(p.name for p in dest.iterdir())
    assert "h3-tree.txt" in written
    for one in dest.iterdir():
        assert offenders(one.read_text()) == []


def test_a_pins_dict_still_renders_for_a_hand_written_results_file():
    """The instrument writes a list; a dict is accepted too, so a raw file
    edited by hand does not become unrenderable."""
    doc = raw()
    doc["pins"] = dict(doc["pins"])
    assert "| work root |" in render(doc, "2026-09-17")


def test_a_float_reading_is_rounded_for_the_page_and_not_in_the_raw():
    """`0.10007790196686983` is what the instrument measured and what the
    results file carries; `0.1` is what a reader needs. Rounding happens
    at render time so both stay true."""
    doc = raw()
    doc["cells"]["H5"]["detail"]["group_gone_s"] = 0.10007790196686983
    text = render(doc, "2026-09-17")
    assert "| `group_gone_s` | 0.1 |" in text
    assert "0.10007790196686983" not in text


def test_an_ungated_row_says_why_it_has_no_clause_table():
    text = render(raw(), "2026-09-17")
    assert ("**No clause table (reported).** §9 gives this row no "
            "PASS/STOP column") in text
    assert "**No clause table (dropped).** `mcp.jsonl` was not read" in text


def test_usage_is_refused_without_two_arguments(capsys):
    assert assemble_e17.main([]) == 2
