"""Pytest's elapsed time is not the program's output differing.

The licence cross-check compares captured stdout byte for byte. Pytest
writes wall-clock duration into that stream, so two runs of the same
tests used to withhold (or, where the streams had also parted, report
a difference that was only the clock). Counts, failure text, and which
test a duration line names still count. Arbitrary numbers still count.
"""
from sensorium.query.refocus_facts import _output_difference


class _Captured:
    """Enough of a trace for `_output_difference`: the chunks, nothing else."""

    def __init__(self, text, stream="stdout"):
        self._text = text
        self._stream = stream

    def output_chunks(self):
        return [(0, self._stream, self._text)]


def _diff(left, right):
    return _output_difference(_Captured(left), _Captured(right))


def test_a_pytest_footer_that_differs_only_in_seconds_is_not_a_difference():
    left = ("============================== 1 passed in 0.02s "
            "==============================\n")
    right = ("============================== 1 passed in 0.04s "
             "==============================\n")
    assert _diff(left, right) is None
    # The same token with no `=` padding, which is the line once the
    # terminal-width decoration is not what changed.
    assert _diff("1 passed in 0.02s\n", "1 passed in 0.04s\n") is None


def test_a_longer_time_token_that_changes_the_padding_is_still_not_one():
    """`9.99s` and `10.00s` are different widths, so pytest's `=` run
    changes length. The result words did not."""
    left = ("============================== 1 passed in 9.99s "
            "==============================")
    right = ("============================= 1 passed in 10.00s "
             "=============================")
    assert _diff(left, right) is None


def test_passed_versus_failed_is_a_difference_at_the_same_time():
    left = ("============================== 1 passed in 0.02s "
            "==============================\n")
    right = ("============================== 1 failed in 0.02s "
             "==============================\n")
    found = _diff(left, right)
    assert found is not None
    assert "passed" in found and "failed" in found


def test_a_duration_line_that_differs_only_in_seconds_is_not_a_difference():
    assert _diff("0.02s call test_foo\n", "0.03s call test_foo\n") is None
    assert _diff("0.02s call     tests/test_foo.py::test_foo\n",
                 "0.03s call     tests/test_foo.py::test_foo\n") is None


def test_a_duration_line_that_names_another_test_is_a_difference():
    found = _diff("0.02s call test_foo\n", "0.02s call test_bar\n")
    assert found is not None
    assert "test_foo" in found and "test_bar" in found
    phase = _diff("0.02s call test_foo\n", "0.02s setup test_foo\n")
    assert phase is not None
    assert "setup" in phase


def test_a_real_assertion_is_reported_even_when_the_footer_also_differs():
    left = (
        "E       AssertionError: expected 1\n"
        "============================== 1 failed in 0.02s "
        "==============================\n")
    right = (
        "E       AssertionError: expected 2\n"
        "============================== 1 failed in 0.04s "
        "==============================\n")
    found = _diff(left, right)
    assert found is not None
    assert "line 1" in found
    assert "expected 1" in found and "expected 2" in found
    assert "0.02s" not in found and "0.04s" not in found


def test_a_timing_line_above_a_real_one_is_skipped():
    left = (
        "============================== 1 passed in 0.02s "
        "==============================\n"
        "answer 1\n")
    right = (
        "============================== 1 passed in 0.04s "
        "==============================\n"
        "answer 2\n")
    found = _diff(left, right)
    assert found is not None
    assert "line 2" in found
    assert "answer 1" in found and "answer 2" in found


def test_an_ordinary_number_is_still_a_difference():
    """Not every `in Ns`, and not every digit. Only pytest's two shapes."""
    found = _diff("loaded in 0.02s\n", "loaded in 0.03s\n")
    assert found is not None
    assert "0.02s" in found and "0.03s" in found
    counted = _diff("count 1\n", "count 2\n")
    assert counted is not None
    assert "count 1" in counted and "count 2" in counted


def test_whitespace_that_is_not_pytest_timing_is_still_reported():
    found = _diff("hello\n", "hello")
    assert found is not None
    assert "whitespace" in found
