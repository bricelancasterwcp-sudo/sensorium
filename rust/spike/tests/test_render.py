"""THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike): `render.py`'s one hard rule.

The renderer's docstring promises that a measurement whose `value` is `null`
prints as `not measured (<reason>)` and *never* as anything else -- no dash, no
zero, no blank cell. That promise is what keeps an unmeasured endpoint from
reading like a measured one in the published findings document, and nothing
tested it until this file.

Each test below was mutation-checked (break the line it pins, the test fails,
restore) -- see `task-5-report.md`'s fix report for the transcript.
"""

import pytest

import render


def null_meas(reason="the arm was dropped"):
    return {"value": None, "n": 0, "lens": "a lens", "dropped": [reason]}


def real_meas(value=1.5):
    return {"value": value, "n": 3, "lens": "a lens", "dropped": []}


class TestCell:
    def test_a_null_value_renders_as_not_measured_with_its_reason(self):
        assert render.cell(null_meas("cargo exit 101")) == "not measured (cargo exit 101)"

    def test_every_dropped_reason_survives_into_the_cell(self):
        m = {"value": None, "n": 0, "lens": "l", "dropped": ["load 5.1 > 4.0", "disk 1.2 GB"]}
        assert render.cell(m) == "not measured (load 5.1 > 4.0; disk 1.2 GB)"

    def test_a_null_with_no_reason_still_says_not_measured(self):
        # The dangerous case: a null that lost its reason must NOT render blank.
        m = {"value": None, "n": 0, "lens": "l", "dropped": []}
        assert render.cell(m) == "not measured (no reason recorded)"

    def test_a_missing_measurement_says_not_measured(self):
        assert render.cell(None).startswith("not measured (")

    def test_zero_is_measured_and_zero_not_not_measured(self):
        # None-vs-zero: 0 is a measurement and must never read as absent.
        assert render.cell(real_meas(0)) == "0"
        assert "not measured" not in render.cell(real_meas(0))

    def test_a_real_value_uses_the_format(self):
        assert render.cell(real_meas(8.2517), "{:.2f} s") == "8.25 s"

    def test_the_format_is_never_applied_to_a_null(self):
        # A format string on a null must not raise and must not print a number.
        assert render.cell(null_meas(), "{:.2f} s") == "not measured (the arm was dropped)"


class TestNum:
    """`num` is the guard for a cell a threshold is compared against: it must
    RAISE rather than print a hole where a gated number belongs."""

    def test_a_null_raises_instead_of_printing_anything(self):
        with pytest.raises(render.NullValue):
            render.num(null_meas())

    def test_a_missing_measurement_raises(self):
        with pytest.raises(render.NullValue):
            render.num(None)

    def test_zero_does_not_raise(self):
        assert render.num(real_meas(0)) == "0"

    def test_a_real_value_formats(self):
        assert render.num(real_meas(0.9975), "{:.4f}") == "0.9975"


class TestHeadlineRows:
    """The five gated rows are where a null would do the most damage."""

    @staticmethod
    def endpoints(e0=None, e1=None, e2=None, e7=None, e8=None):
        return {"E0": {"headline": e0 or real_meas(0.03)},
                "E1": {"headline": e1 or real_meas(0.9975)},
                "E2": {"headline": e2 or real_meas(1.0)},
                "E7": {"headline": e7 or real_meas(0)},
                "E8": {"headline": e8 or real_meas(0)}}

    def test_a_null_endpoint_renders_as_not_measured_in_its_row(self):
        rows = render.headline_rows(self.endpoints(e1=null_meas("cargo exit 101 on 5 of 5 rounds")))
        e1 = next(r for r in rows if r.startswith("| E1 |"))
        assert "not measured (cargo exit 101 on 5 of 5 rounds)" in e1
        assert "×" not in e1, "a null must not be dressed as a ratio"

    def test_a_null_endpoint_never_renders_as_zero_or_a_dash(self):
        rows = render.headline_rows(self.endpoints(e7=null_meas("the probe build failed")))
        e7 = next(r for r in rows if r.startswith("| E7 |"))
        assert "0 differences" not in e7
        assert "| — |" not in e7.split("|", 3)[2]

    def test_a_measured_zero_still_renders_as_zero(self):
        rows = render.headline_rows(self.endpoints())
        e8 = next(r for r in rows if r.startswith("| E8 |"))
        assert "0 failed checks" in e8
        assert "not measured" not in e8

    def test_every_row_carries_its_n_and_its_lens_and_its_dropped(self):
        rows = render.headline_rows(self.endpoints(e0=null_meas("disk floor")))
        for row in rows:
            cols = [c.strip() for c in row.strip("|").split("|")]
            assert len(cols) == 5, row
            assert cols[2] != "", "n must never be blank"
            assert cols[3] != "", "the lens must never be blank"
            assert cols[4] != "", "dropped must say `none`, never nothing"
        assert "| none |" in rows[1]
        assert "disk floor" in rows[0]


class TestE1Table:
    @staticmethod
    def e1(runs):
        arms = {a: {"median_s": real_meas(8.2), "min_s": 8.1, "max_s": 8.3} for a in "POC"}
        return {"raw_runs": runs, "arms": arms}

    def test_a_dropped_round_prints_its_reason_not_a_blank(self):
        runs = [{"round": 1, "arm": a, "wall": 8.2} for a in "POC"]
        runs[1] = {"round": 1, "arm": "O", "wall": None, "dropped": "1-min load 5.2 > 4.0"}
        out = render.e1_table(self.e1(runs))
        assert "dropped (1-min load 5.2 > 4.0)" in out[2]

    def test_a_round_that_never_ran_says_so(self):
        runs = [{"round": 1, "arm": "P", "wall": 8.2}]
        out = render.e1_table(self.e1(runs))
        assert "not measured (the round was never started)" in out[2]

    def test_an_arm_with_no_scored_run_has_no_min_or_max_number(self):
        arms = {a: {"median_s": null_meas("every round dropped"), "min_s": None, "max_s": None}
                for a in "POC"}
        out = render.e1_table({"raw_runs": [{"round": 1, "arm": "P", "wall": 8.2}], "arms": arms})
        assert "not measured (every round dropped)" in out[3]
        assert "not measured (no scored run)" in out[4]
        assert "not measured (no scored run)" in out[5]
