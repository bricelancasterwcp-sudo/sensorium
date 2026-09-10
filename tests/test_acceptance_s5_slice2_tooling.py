"""S5 slice 2's acceptance TOOLING, tested without the box.

Nothing here runs vitest, touches the lens, reads a spool it did not itself
write in `tmp_path`, or needs an environment variable set by whoever launched
pytest. What it tests is the four places this slice could publish a wrong
number while every command it ran exited 0:

* **a dropped run's load reading outliving its wall.** `assemble.arm_stats`
  collected `loads` over EVERY row of an arm while `walls` skipped the rows
  that were not ok. A dropped run's load then sat in the cell beside four
  walls it did not guard, and the record's "all readings under 4.0" would be
  a claim about a run that was thrown away. The ledger names it as a latent
  misalignment; E6″ is the first endpoint whose verdict rides on it.
* **the band's arithmetic.** E6″'s timing clause is `median(after)` inside
  `median(before) ± range(before)`. A band computed from the wrong arm, or
  with the range taken over the rows rather than the usable walls, is a
  clause that cannot fail — which is what E6′'s single-wall band was.
* **an unmeasured clause reading as a held one.** Fewer than four usable
  walls in either arm is `STOP by instrument`, not a pass and not a STOP on
  the recorder: the band or the median was never measured.
* **a box path reaching the committed results file.** `assemble_slice2`
  writes a file this repository commits; a surviving `/mnt/` string is a
  refusal, never a redaction someone forgot to pass.

Every test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "typescript" / "acceptance"))

import assemble                                                    # noqa: E402
import assemble_slice2                                             # noqa: E402
import e6pp_report                                                 # noqa: E402


def row(arm: str, run: int, wall: float, load: float, ok: bool = True) -> dict:
    """One `e6pp.jsonl` line, in the shape `arm_line.py` writes."""
    out = {"arm": arm, "batch": 1, "run": run, "wall": wall,
           "harness_wall": None, "load_1min": load, "exit": 0 if ok else 1,
           "suite_files_ok": ok, "suite_tests_ok": ok, "ok": ok,
           "duration_line": None, "transform_s": None, "invocation": None,
           "log": f"{arm}-{run}.log", "lens": "a lens"}
    if not ok:
        out["why_not_ok"] = ["Test Files line is not 372 passed (372)"]
    return out


# -- the loads fix ----------------------------------------------------------


def test_arm_stats_drops_a_runs_load_reading_with_its_wall():
    """A run whose suite was not the suite is dropped: its wall leaves
    `walls`, and its load reading must leave `loads` in the same step.

    Catches: the pre-fix assembler, where `loads` was built over every row of
    the arm. It would report three readings beside two walls, so the guard
    audit in the record would cover a run that no number came from.
    """
    rows = [row("before", 1, 22.31, 0.5),
            row("before", 2, 40.00, 3.9, ok=False),
            row("before", 3, 22.59, 0.7)]

    stats = assemble.arm_stats(rows, "before", "wall")

    assert stats["walls"] == [22.31, 22.59]
    assert stats["loads"] == [0.5, 0.7]
    assert len(stats["loads"]) == len(stats["walls"]) == 2
    assert stats["runs"] == 3
    assert len(stats["dropped"]) == 1


def test_arm_stats_drops_the_load_of_a_run_that_recorded_no_wall():
    """The other way a wall leaves: the key is absent (a driver arm whose
    `harness.json` was never written). Its load goes with it.

    Catches: a fix that filtered only on `ok` and left the missing-key branch
    appending to `dropped` while its load stayed in `loads`.
    """
    rows = [row("call", 1, 22.31, 0.5), row("call", 2, 22.59, 0.7)]
    rows[0]["harness_wall"] = 21.0

    stats = assemble.arm_stats(rows, "call", "harness_wall")

    assert stats["walls"] == [21.0]
    assert stats["loads"] == [0.5]
    assert stats["dropped"] == ["call run 2: no harness_wall was recorded"]


# -- the band ---------------------------------------------------------------

#: E1''s plain arm, the five walls spec 2.2 derives its worked example from.
E1P_WALLS = [22.3136, 22.3252, 22.5925, 22.6142, 22.7221]


def test_the_band_is_the_before_arms_median_plus_or_minus_its_own_range():
    """Spec 2.2's worked example, to the digit: median 22.5925, range
    22.7221 - 22.3136 = 0.4085, band [22.184, 23.001].

    Catches: a band taken from the after arm, a range read as a standard
    deviation or a multiplier, or a half-range — each of which changes which
    verdict the same five walls give.
    """
    rows = [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS)]
    before = assemble.arm_stats(rows, "before", "wall")

    assert before["median"] == 22.5925
    assert e6pp_report.band_of(before["walls"]) == [22.184, 23.001]


def test_the_band_is_taken_over_the_usable_walls_only():
    """A dropped run's wall must not widen the band it was thrown out of.

    Catches: a range computed over `walls` including dropped rows — a single
    infrastructure kill at 60 s would open the band so wide that no after
    median could ever fall outside it.
    """
    rows = [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS)]
    rows.append(row("before", 6, 60.0, 0.5, ok=False))
    before = assemble.arm_stats(rows, "before", "wall")

    assert e6pp_report.band_of(before["walls"]) == [22.184, 23.001]


def test_in_band_is_false_when_the_after_median_sits_above_the_band():
    """23.01 is nine thousandths of a second above the band's top, and the
    clause is a STOP.

    Catches: a comparison written with the wrong strictness on the wrong
    side, or one that compared a wall rather than the arm's median.
    """
    before = assemble.arm_stats(
        [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS)],
        "before", "wall")
    after_walls = [23.0, 23.005, 23.01, 23.02, 23.03]
    after = assemble.arm_stats(
        [row("after", i + 1, w, 0.5) for i, w in enumerate(after_walls)],
        "after", "wall")

    timing = e6pp_report.timing(before, after)

    assert after["median"] == 23.01
    assert timing["band"] == [22.184, 23.001]
    assert timing["in_band"] is False
    assert timing["clause"] == "STOP"


def test_the_band_tests_the_after_arms_median_not_its_worst_wall():
    """An after arm whose median sits well inside the band but whose slowest
    wall sits far outside it: the clause HOLDS.

    Catches the failure E6″ exists to remove — E6′ compared ONE wall against
    a band and stopped on it. A report that tested the max, the mean, or any
    single wall would call this session contaminated on the strength of one
    slow run, which is the reading spec 2.2 refused to carry forward.
    """
    before = assemble.arm_stats(
        [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS)],
        "before", "wall")
    after_walls = [22.5, 22.55, 22.6, 22.65, 23.5]
    after = assemble.arm_stats(
        [row("after", i + 1, w, 0.5) for i, w in enumerate(after_walls)],
        "after", "wall")

    timing = e6pp_report.timing(before, after)

    assert after["median"] == 22.6 and after["max"] == 23.5
    assert timing["band"] == [22.184, 23.001]
    assert timing["in_band"] is True
    assert timing["clause"] == "held"


def test_in_band_is_true_at_the_bands_own_edge():
    """The band is closed: its endpoints hold.

    Catches: a strict `<` that would turn the pre-registered inclusive rule
    into a narrower one after the numbers were read.
    """
    before = assemble.arm_stats(
        [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS)],
        "before", "wall")
    after = assemble.arm_stats(
        [row("after", i + 1, 23.001, 0.5) for i in range(5)], "after", "wall")

    timing = e6pp_report.timing(before, after)

    assert timing["in_band"] is True
    assert timing["clause"] == "held"


# -- the unmeasured clause --------------------------------------------------


def test_three_usable_walls_in_an_arm_is_a_stop_by_instrument():
    """Two of the after arm's five runs dropped: the median was not measured
    over the five the rule names, so the clause is neither held nor a STOP on
    the recorder.

    Catches: a report that computed a median over whatever survived and
    called the clause held — the failure mode where an instrument's own bad
    session is published as a property of the subject.
    """
    before = assemble.arm_stats(
        [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS)],
        "before", "wall")
    after_rows = [row("after", i + 1, 22.5, 0.5) for i in range(3)]
    after_rows += [row("after", 4, 22.5, 0.5, ok=False),
                   row("after", 5, 22.5, 0.5, ok=False)]
    after = assemble.arm_stats(after_rows, "after", "wall")

    timing = e6pp_report.timing(before, after)

    assert timing["usable"] == {"before": 5, "after": 3}
    assert timing["clause"] == "STOP by instrument"
    assert timing["in_band"] is None


def test_a_short_before_arm_is_also_a_stop_by_instrument():
    """The rule names EITHER arm, and the band is the one the before arm
    could not supply.

    Catches: a guard written only over the after arm, which would publish a
    band derived from three walls as though five had been measured.
    """
    before = assemble.arm_stats(
        [row("before", i + 1, w, 0.5) for i, w in enumerate(E1P_WALLS[:3])],
        "before", "wall")
    after = assemble.arm_stats(
        [row("after", i + 1, 22.5, 0.5) for i in range(5)], "after", "wall")

    assert e6pp_report.timing(before, after)["clause"] == "STOP by instrument"


def test_five_clauses_are_counted_and_the_band_counts_only_when_it_held():
    """`value` is how many of the five clauses held; `STOP by instrument` is
    not one of them.

    Catches: a `value` that counted the four contamination clauses and
    reported 4/5 as though the band had been weighed.
    """
    contamination = {"manifest_identical": True, "suite_is_the_suite": True,
                     "zero_markers": True, "wrapper_gone": True}

    held = e6pp_report.clauses(contamination, "held")
    stopped = e6pp_report.clauses(contamination, "STOP")
    unmeasured = e6pp_report.clauses(contamination, "STOP by instrument")

    assert (held["value"], held["n"]) == (5, 5)
    assert held["clauses"]["plain_band"] is True
    assert stopped["value"] == 4 and stopped["clauses"]["plain_band"] is False
    assert unmeasured["value"] == 4
    assert unmeasured["clauses"]["plain_band"] is None


# -- the assembler's refusal ------------------------------------------------


def test_assemble_slice2_refuses_a_surviving_mnt_string(tmp_path, capsys):
    """The results file is committed. A cell naming a box path, with no
    `PATH=LABEL` for it, must refuse rather than write.

    Catches: an assembler that inherited `redact` but not `offenders`, or one
    whose new `reported` branch built strings after the check ran.
    """
    results = tmp_path / "results"
    results.mkdir()
    (results / "e6pp.json").write_text(json.dumps(
        {"value": 5, "n": 5, "lens": "a lens", "dropped": [],
         "wrapper_dir": "/mnt/example/lens/frontend/node_modules"}),
        encoding="utf-8")
    out = tmp_path / "slice2.results.json"

    rc = assemble_slice2.main(["assemble_slice2.py", str(results), str(out)])

    assert rc == 2
    assert not out.exists()
    assert "/mnt/example/lens/frontend" in capsys.readouterr().err


def test_assemble_slice2_writes_when_the_path_is_redacted(tmp_path):
    """The same cell with its redaction pair passed writes, and the label is
    what the file carries.

    Catches: a refusal that fires on the pre-redaction payload, which would
    make every real run unwritable.
    """
    results = tmp_path / "results"
    results.mkdir()
    (results / "e6pp.json").write_text(json.dumps(
        {"value": 5, "n": 5, "lens": "a lens", "dropped": [],
         "wrapper_dir": "/mnt/example/lens/frontend/node_modules"}),
        encoding="utf-8")
    out = tmp_path / "slice2.results.json"

    rc = assemble_slice2.main(
        ["assemble_slice2.py", str(results), str(out),
         "/mnt/example/lens/frontend=<lens>"])

    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gated"]["E6″"]["wrapper_dir"] == "<lens>/node_modules"


def test_assemble_slice2_reports_a_missing_cell_as_null_and_dropped(tmp_path):
    """A cell nobody measured is a missing file, and the assembler says so by
    name rather than leaving a key out.

    Catches: an assembler that skipped absent files, which would let a
    never-measured endpoint read as an omission instead of a null.
    """
    results = tmp_path / "results"
    results.mkdir()
    out = tmp_path / "slice2.results.json"

    rc = assemble_slice2.main(["assemble_slice2.py", str(results), str(out)])

    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    for name in ("E10′-suite", "E10′-file", "E10′-eq", "E6″", "H-probes"):
        assert payload["gated"][name]["value"] is None
        assert payload["gated"][name]["dropped"]
