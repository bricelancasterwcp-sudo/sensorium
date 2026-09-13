"""E15's assembler and its runner: the provenance gate, and the locations.

The sibling of `tests/test_acceptance_e15.py` rather than its continuation:
the two were one file until it crossed `tests/test_ceiling.py`'s 800 lines,
and the seam is the material's -- there the reader and the cells are given
text and dicts, here the assembler and the runner are CALLED and their exit
statuses, their refusals and the files they write are read.

The assembler is the only thing standing between a dry run's numbers and
this slice's results file, so every one of its four provenance checks has a
test that makes that check fail on its own.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"
sys.path.insert(0, str(ACCEPT))

import assemble_e15 as assembler                                  # noqa: E402
import e15                                                        # noqa: E402
import e15_phases as ph                                           # noqa: E402
from test_acceptance_e15_cells import (SURVEY_3,          # noqa: E402
                                       raw_of, three_rows)
from test_acceptance_e15_lock import BYTE_LOCK, SURVEY_LOCK        # noqa: E402

SURVEY = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-13-sensorium-e15-refocus-typescript-survey.md")
RECORD = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-13-sensorium-e15-refocus-typescript.md")
REV = "0" * 40

INSTRUMENT = ("e15.py", "e15_phases.py", "e15_read.py", "e15_report.py",
              "assemble_e15.py", "e15.sh")


def write_raw(tmp_path: Path, raw: dict) -> Path:
    path = tmp_path / "results-e15-raw.json"
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    return path


def assemble(tmp_path: Path, raw: dict, record: Path = RECORD,
             survey: Path = SURVEY) -> tuple[int, Path]:
    out = tmp_path / "e15.results.json"
    rc = assembler.main(["assemble_e15.py", str(write_raw(tmp_path, raw)),
                         str(survey), str(record), str(out),
                         "a recorder", REV])
    return rc, out


# -- the assembler ----------------------------------------------------------


def test_assemble_writes_the_word_stamps_every_cell_and_exits_zero(tmp_path):
    """Catches: an assembler that publishes unstamped cells. `lens.stamp` is
    the ONLY thing that mints a lens label -- `cell()` stopped embedding one
    -- and `strict=True` refuses a cell that arrived with its own."""
    rc, out = assemble(tmp_path, raw_of(three_rows()))
    assert rc == 0, out.read_text()[:400]
    doc = json.loads(out.read_text())
    assert doc["word"] == "DONE" and doc["stops"] == []
    assert list(doc["gated"]) == ["H1", "H2", "H3", "H4", "H5", "H6", "H7",
                                  "H7p", "H8", "H8p", "H9", "H10"]
    # §1's own ten are named apart from ruling P16's two primed readings, so
    # a reader can tell the locked endpoints from the cells that re-read two
    # of them. Nothing was added to §1; it is byte-locked.
    assert doc["endpoints"] == [f"H{n}" for n in range(1, 11)]
    assert doc["primed_readings"] == ["H7p", "H8p"]
    for name, c in doc["gated"].items():
        assert c["lens"] == assembler.LENS, name
    assert doc["recorded_by"] == {"recorder": "a recorder", "commit": REV}
    assert all(v["ok"] for v in doc["verification"].values())


def test_assemble_words_a_STOP_as_DONE_WITH_STOP(tmp_path):
    """Catches: a word that is decided by hand. §1's kill rules make a STOP a
    property of the cells, and the word has to follow them -- including a
    STOP raised by one of ruling P16's primed readings, which is a STOP
    whichever cell raised it."""
    raw = raw_of(three_rows())
    # §1's LITERAL control C, answered by argparse's usage refusal rather
    # than by design §2.3's refusal 1: exit 2, but not the sentence.
    raw["controls"]["C"]["as_written"]["parsed"] = {
        "refusal": None, "refusal_run": None}
    rc, out = assemble(tmp_path, raw)
    assert rc == 0
    doc = json.loads(out.read_text())
    assert doc["word"] == "DONE-WITH-STOP"
    assert any(s.startswith("H8:") for s in doc["stops"]), doc["stops"]

    # …and the same when it is the PRIMED reading that stops.
    raw2 = raw_of(three_rows())
    raw2["controls"]["C"]["traces_after"] = 9          # the store moved
    rc2, out2 = assemble(tmp_path, raw2)
    assert rc2 == 0
    doc2 = json.loads(out2.read_text())
    assert doc2["word"] == "DONE-WITH-STOP"
    assert any(s.startswith("H8p:") for s in doc2["stops"]), doc2["stops"]


def test_assemble_REFUSES_a_dry_run_and_still_writes_the_file(tmp_path):
    """Catches: an assembler that will publish a dry run's numbers. `E15_ROWS`
    substitutes `corpus/typescript`'s three cases for the survey's 31, so
    such a raw is about a different subject -- and the file is still written,
    because a reader diagnosing the refusal needs the cells it failed over."""
    raw = raw_of(three_rows())
    raw["preflight"]["dry_run"] = True
    raw["preflight"]["rows_override"] = 3
    rc, out = assemble(tmp_path, raw)
    assert rc == 1
    doc = json.loads(out.read_text())
    assert doc["verification"]["not_a_dry_run"]["ok"] is False
    assert "DRY RUN" in doc["verification"]["not_a_dry_run"]["why"][0]
    assert doc["gated"]["H1"]["value"] == 0       # the cells are still there


def test_assemble_REFUSES_a_driver_version_that_is_not_this_slices(tmp_path):
    """Catches: an assembler that trusts the runner's own preflight. A stale
    editable install stamps the previous release's number on every trace, and
    §1 cites 0.14.0 on all of them (plan ruling A8)."""
    raw = raw_of(three_rows())
    raw["preflight"]["driver_version"] = "0.13.0"
    rc, out = assemble(tmp_path, raw)
    assert rc == 1
    got = json.loads(out.read_text())["verification"]["driver_version"]
    assert got["ok"] is False and got["read"] == "0.13.0"
    assert got["expected"] == assembler.DRIVER_VERSION == "0.14.0"


def test_assemble_REFUSES_a_section_one_that_moved_by_one_byte(tmp_path):
    """Catches: a lock that is written down and never recomputed. The
    mutation is H2's gate -- `31 of 31` harness exits equal -- one of the
    numbers most worth widening once 31 re-runs have printed."""
    moved = tmp_path / RECORD.name
    text = RECORD.read_text(encoding="utf-8")
    tampered = text.replace("**31 of 31** harness exits equal",
                            "**30 of 31** harness exits equal", 1)
    assert tampered != text, "the mutation target is no longer in §1"
    moved.write_text(tampered, encoding="utf-8")
    rc, out = assemble(tmp_path, raw_of(three_rows()), record=moved)
    assert rc == 1
    got = json.loads(out.read_text())["verification"]["section_one_has_not_moved"]
    assert got["ok"] is False
    assert got["expected_sha256"] == BYTE_LOCK
    assert got["read_sha256"] != BYTE_LOCK


def test_assemble_REFUSES_a_survey_that_moved_by_one_byte(tmp_path):
    """Catches: the same failure one file over. The survey is where every
    row's CLASS comes from and H4 asks a different question of a
    deterministic row, so a table corrected after 31 verdicts printed would
    rewrite the prediction rather than the reading."""
    moved = tmp_path / SURVEY.name
    moved.write_text(SURVEY.read_text(encoding="utf-8").replace(
        "`mergeSheetSnapshot.ts:isDeepEqual` | 3 |",
        "`mergeSheetSnapshot.ts:isDeepEqual` | 4 |", 1), encoding="utf-8")
    rc, out = assemble(tmp_path, raw_of(three_rows()), survey=moved)
    assert rc == 1
    got = json.loads(out.read_text())["verification"]["the_survey_has_not_moved"]
    assert got["ok"] is False and got["expected_sha256"] == SURVEY_LOCK


def test_assemble_refuses_a_short_rev_and_a_malformed_redaction(tmp_path):
    """Catches: provenance recorded from a short sha, which names no commit
    uniquely, and a `PATH=LABEL` typo silently ignored."""
    raw_path = write_raw(tmp_path, raw_of(three_rows()))
    out = tmp_path / "x.json"
    base = ["assemble_e15.py", str(raw_path), str(SURVEY), str(RECORD),
            str(out)]
    assert assembler.main(base + ["a recorder", "abc1234"]) == 2
    assert assembler.main(base + ["a recorder", REV, "not-a-pair"]) == 2
    assert assembler.main(base[:4]) == 2


def test_assemble_redacts_a_named_path_and_refuses_one_that_survives(tmp_path):
    """Catches: a results file committed with a box path in it. A DIVERGED
    row's step line prints the diverging function's FILE, which on E15's
    subject is a path under the throwaway copy."""
    rows = three_rows()
    rows[2]["parsed"]["divergent_line"] = (
        "tasks: DIVERGED -- at causal step 7: A e5 CALL left "
        "(/tmp/e15/lens/src/c.ts)")
    rc, out = assemble(tmp_path, raw_of(rows))
    assert rc == 2, "a surviving box path must refuse"
    raw_path = write_raw(tmp_path, raw_of(rows))
    rc = assembler.main(["assemble_e15.py", str(raw_path), str(SURVEY),
                         str(RECORD), str(out), "a recorder", REV,
                         "/tmp/e15/lens=<copy>"])
    assert rc == 0
    assert "<copy>/src/c.ts" in out.read_text()


# -- the runner's locations -------------------------------------------------


def test_no_committed_instrument_file_carries_a_box_path():
    """Catches: a location compiled into the instrument. Every one of E15's
    is an environment variable or an argument, which is what lets the same
    five files be dry-run on a scratch directory and then run on the lens."""
    for name in INSTRUMENT:
        text = (ACCEPT / name).read_text(encoding="utf-8")
        for needle in ("/mnt/", "/home/", "/root/", "/tmp/"):
            assert needle not in text, f"{name}: {needle}"


def test_the_runner_refuses_every_missing_location_together(monkeypatch):
    """Catches: a runner that refuses one variable at a time, so a
    misconfigured launch has to be fixed three times."""
    for key in e15.E15_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ph.Refused) as e:
        e15.env_paths()
    for key in e15.E15_ENV:
        assert key in str(e.value), key
    assert e.value.code == 2


def test_the_runner_names_the_phases_section_one_fixes():
    """Catches: a phase silently dropped. §1's order is the record's, and a
    runner that skipped `survey_check` would loop over a population nobody
    checked against the locked table."""
    assert e15.PHASES == ("preflight", "copy", "originals", "survey_check",
                          "loop", "controls", "fences", "reads")
    assert set(e15.PHASE_FN) == set(e15.PHASES)


def test_the_dry_run_table_comes_from_the_lens_and_is_refused_when_absent(
        tmp_path):
    """Catches: a dry-run table with a path in it. It is derived from the
    lens's own `refocus_*` directories, and a lens without them refuses at
    exit 4 rather than inventing a table."""
    rows = e15.dry_rows(REPO / "corpus" / "typescript")
    assert [r["n"] for r in rows] == [1, 2, 3]
    assert rows[1]["test_file"] == "refocus_match/refocus_match.test.ts"
    assert [r["focus"] for r in rows] == ["choose", "fill", "one"]
    assert all(r["klass"] == "deterministic" for r in rows)
    with pytest.raises(ph.Refused) as e:
        e15.dry_rows(tmp_path)
    assert e.value.code == 4 and "survey_check:" in str(e.value)


def test_the_launcher_detaches_and_prints_the_markers(tmp_path):
    """Catches: a launcher that blocks. The loop is 31 whole-suite re-runs and
    outlives its terminal, so the only honest way to read it is the marker --
    which means the launcher has to print where it is."""
    text = (ACCEPT / "e15.sh").read_text(encoding="utf-8")
    assert "setsid nohup" in text
    assert "e15.DONE" in text and "e15.FAILED" in text
    for key in ("E15_LENS", "E15_WORK", "E15_OUT"):
        assert f"export {key}" in text or f'{key}="' in text, key
    got = subprocess.run(["bash", str(ACCEPT / "e15.sh")],
                         capture_output=True, text=True,
                         env={**os.environ, "PATH": os.environ["PATH"]})
    assert got.returncode == 2
    assert "usage: e15.sh <lens> <work root> <out dir>" in got.stderr


def test_the_needle_and_the_bounds_are_the_pre_registered_ones():
    """Catches: a bound quietly widened. §1's kill rules give the loop three
    hours and each refocus 900 s, and `e6pp.sh`'s load guard is 4.0 over 90
    tries 20 s apart -- two instruments in one slice that guard at different
    thresholds do not measure the same box."""
    assert (ph.LOAD_MAX, ph.LOAD_TRIES, ph.LOAD_SLEEP) == (4.0, 90, 20)
    assert ph.LOOP_BUDGET_S == 3 * 3600
    assert ph.REFOCUS_TIMEOUT == 900
    assert ph.READER_TIMEOUT == 120
    assert ph.DISK_FLOOR_GB == 30
    assert ph.NEEDLE == "sensorium run --focus"


# -- every exit path leaves a marker (Finding 4) ----------------------------


def test_write_marker_is_the_one_place_a_marker_is_written(tmp_path):
    """Catches: a marker shape that drifts between exit paths. Silence is
    what the marker exists to rule out, so `.DONE` on 0 and `.FAILED
    exit=<n>` on anything else come from one function that every path
    calls."""
    done = e15.write_marker(tmp_path, 0)
    assert done.name == "e15.DONE"
    assert done.read_text().startswith("exit=0\n")
    failed = e15.write_marker(tmp_path, 3, "preflight: fence_base")
    assert failed.name == "e15.FAILED"
    body = failed.read_text().splitlines()
    assert body[0] == "exit=3" and body[2] == "preflight: fence_base"
    # …and a directory that does not exist yet still gets one.
    deep = tmp_path / "not" / "there"
    assert e15.write_marker(deep, 5, "boom").is_file()


def test_a_SystemExit_carries_its_own_code_into_the_marker():
    """Catches: an exit code invented for an exception that carried one.
    `lens.sensorium_bin()` raises `SystemExit(3)` when the branch's binary is
    not where it must be, and that 3 is the number a reader of the marker
    needs."""
    assert e15.exit_code_of(SystemExit(3)) == 3
    assert e15.exit_code_of(SystemExit()) == 0
    assert e15.exit_code_of(SystemExit("a message")) == 1
    assert e15.exit_code_of(KeyboardInterrupt()) == 130
    assert e15.exit_code_of(RuntimeError("boom")) == 5
    assert e15.SIGTERM_EXIT == 143


def _launch(monkeypatch, tmp_path, boom):
    """Run `e15.main` with `context()` replaced by something that raises.

    `context()` is where `lens.sensorium_bin()` is called from, and it used
    to run OUTSIDE the try that writes the marker -- the exact path the
    review found.
    """
    import signal
    monkeypatch.setenv("E15_LENS", str(tmp_path))
    monkeypatch.setenv("E15_WORK", str(tmp_path / "work"))
    monkeypatch.setenv("E15_OUT", str(tmp_path / "out"))
    monkeypatch.delenv("E15_ROWS", raising=False)

    def raise_it(_paths):
        raise boom

    monkeypatch.setattr(e15, "context", raise_it)
    previous = signal.getsignal(signal.SIGTERM)
    try:
        return e15.main([])
    finally:
        signal.signal(signal.SIGTERM, previous)


def test_a_context_that_raises_SystemExit_still_leaves_a_marker(
        monkeypatch, tmp_path):
    """Catches: the marker-less exit path, at its root. `sensorium_bin()`
    raising `SystemExit(3)` used to escape `except Exception` and end the
    process with no `.DONE` and no `.FAILED` -- silence, which is the one
    thing the markers exist to rule out. The interrupt is re-raised AFTER the
    marker is written, never instead of it."""
    with pytest.raises(SystemExit) as e:
        _launch(monkeypatch, tmp_path, SystemExit(3))
    assert e.value.code == 3
    marker = tmp_path / "out" / "e15.FAILED"
    assert marker.is_file(), "no marker was written"
    assert marker.read_text().startswith("exit=3\n")
    assert "SystemExit" in marker.read_text()
    assert not (tmp_path / "out" / "e15.DONE").exists()
    raw = json.loads((tmp_path / "out" / "results-e15-raw.json").read_text())
    assert raw["exit"] == 3 and raw["status"] == "error"


def test_a_generic_exception_before_the_first_phase_leaves_a_marker_too(
        monkeypatch, tmp_path):
    """Catches: the same hole for anything that is not a `SystemExit` -- and
    that one is NOT re-raised, because it is this runner's own failure and
    the exit status carries it."""
    rc = _launch(monkeypatch, tmp_path, RuntimeError("the store is gone"))
    assert rc == 5
    marker = tmp_path / "out" / "e15.FAILED"
    assert marker.is_file()
    assert marker.read_text().startswith("exit=5\n")
    assert "the store is gone" in marker.read_text()


def test_the_runner_refuses_a_fence_base_that_names_no_commit():
    """Catches: E-legacy passing vacuously. `sh()` swallows a failed `git
    merge-base` into `""`, and `e_fences.py` would then diff `HEAD..HEAD` --
    empty by construction -- and report the fenced files unchanged over a
    comparison it never made."""
    assert e15.check_fence_base("0" * 40) == "0" * 40
    for bad in ("", None, "abc1234", "0" * 39, "Z" * 40):
        with pytest.raises(ph.Refused) as e:
            e15.check_fence_base(bad)
        assert e.value.code == 3, bad
        assert "preflight: fence_base" in str(e.value), bad


def test_a_loop_that_did_not_finish_is_FAILED_and_says_how_far_it_got():
    """Catches: `.DONE exit=0` over a budget-exhausted loop. The marker is
    the first thing a reader looks at, and it has to say the loop is short
    before any cell is read."""
    assert ph.loop_incomplete([], 31) is None
    short = ph.loop_incomplete([24, 25, 26], 31)
    assert short is not None
    assert short.startswith("loop: budget exhausted after 28 of 31")
    assert "24" in short
    # …and the runner turns that into the exit the marker carries.
    src = (ACCEPT / "e15.py").read_text(encoding="utf-8")
    assert '"incomplete"' in src and "return 5, short" in src


def test_the_fences_run_the_probes_suite_as_e12_h8_runs_it():
    """Catches: §1's H10 list read short. It names `npm --prefix typescript
    test; the probes; tests/test_ceiling.py`, and the probes are the
    recorder's own probe project -- which needs a spool, a manifest directory
    and `SENSORIUM_TIER=call`, all of which `plain_env()` strips."""
    ctx = {"python": ".venv/bin/python", "out": REPO / "does-not-exist-here",
           "cargo_target": None}
    try:
        specs = ph.fence_commands(ctx)
    finally:
        import shutil
        shutil.rmtree(ctx["out"], ignore_errors=True)
    names = [s["name"] for s in specs]
    assert names == ["corpus", "pytest", "cargo test --workspace",
                     "npm --prefix typescript test", "tsc", "npm-probes",
                     "ceiling"]
    probes = next(s for s in specs if s["name"] == "npm-probes")
    assert probes["cmd"] == ["npm", "--prefix", "typescript/probes", "run",
                             "probe"]
    for key in ("SENSORIUM_SPOOL", "SENSORIUM_MANIFEST_DIR"):
        assert probes["env"][key], key
    assert probes["env"]["SENSORIUM_TIER"] == "call"
    # …and nothing else inherits them.
    assert "SENSORIUM_TIER" not in next(
        s for s in specs if s["name"] == "pytest")["env"]
