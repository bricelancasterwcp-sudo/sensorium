"""`run_corpus.py --require-driver`: a skip is a failure where one is a lie.

The harness reports a case it could not record as skipped BY NAME and still
exits 0, which is right on the Python CI matrix -- there is no Rust toolchain
there and never will be. It is wrong on the `rust` job, which builds a driver
precisely so those cases run: if the driver went missing there, every cargo
case would be reported skipped and the job would go green having recorded
nothing. The flag is how a caller says "I expect every case to run", and the
gate it buys is the whole point, so each half of it is pinned here.
"""
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from corpus import run_corpus                                    # noqa: E402


def _drive(monkeypatch, results):
    """Run `main` over a fixed list of `CaseResult`s, loading no corpus.

    The harness's own loading and recording are tested in
    `tests/test_corpus.py`; what is under test here is the summary and the
    exit code, so the cases are stand-ins and `run_case` hands back whatever
    outcome the test wants to see reported.
    """
    cases = [run_corpus.Case(r.name, Path("."), "p") for r in results]
    monkeypatch.setattr(run_corpus, "load_cases", lambda *a, **k: cases)
    handed = iter(results)
    monkeypatch.setattr(run_corpus, "run_case",
                        lambda *a, **k: next(handed))


def _skipped(name="rust/panic", reason=None):
    return run_corpus.CaseResult(
        name, skipped=reason or run_corpus.NO_DRIVER)


def _ran(name="silent_swallow", asked=2):
    res = run_corpus.CaseResult(name)
    res.asked = asked
    return res


SENTENCE = "--require-driver was given and 1 case(s) could not run"


def test_a_skip_under_the_flag_exits_one_and_says_why(monkeypatch, capsys):
    _drive(monkeypatch, [_skipped(), _ran()])
    assert run_corpus.main(["--require-driver"]) == 1
    out = capsys.readouterr().out
    # The skip is still reported the way it always was -- the flag changes
    # what the run is worth, not what happened.
    assert "skip  rust/panic" in out
    assert "no cargo-sensorium" in out
    assert f"; {SENTENCE}" in out


def test_the_same_run_without_the_flag_still_exits_zero(monkeypatch, capsys):
    """The Python matrix's ordinary state, unchanged by this feature."""
    _drive(monkeypatch, [_skipped(), _ran()])
    assert run_corpus.main([]) == 0
    out = capsys.readouterr().out
    assert "2 cases (1 skipped: no cargo-sensorium), 2 questions" in out
    assert "--require-driver" not in out


def test_the_flag_leaves_a_run_with_nothing_skipped_alone(monkeypatch,
                                                          capsys):
    _drive(monkeypatch, [_ran("a"), _ran("b")])
    assert run_corpus.main(["--require-driver"]) == 0
    out = capsys.readouterr().out
    assert "2 cases, 4 questions, 0 failures, 0 error(s)" in out
    assert "--require-driver" not in out


def test_the_count_is_the_number_of_cases_that_could_not_run(monkeypatch,
                                                             capsys):
    _drive(monkeypatch,
           [_skipped("rust/panic"), _skipped("rust/abort"), _ran()])
    assert run_corpus.main(["--require-driver"]) == 1
    out = capsys.readouterr().out
    assert "; --require-driver was given and 2 case(s) could not run" in out


def test_any_skip_counts_not_only_a_missing_driver(monkeypatch, capsys):
    """The flag says "every case ran", not "a driver was found".

    `NO_DRIVER` is the only reason the harness skips for today. If a second
    one is ever added, a caller that asked for every case to run must not
    have to remember to ask again for the new reason too.
    """
    _drive(monkeypatch, [_skipped(reason="no such thing"), _ran()])
    assert run_corpus.main(["--require-driver"]) == 1
    assert f"; {SENTENCE}" in capsys.readouterr().out


def test_the_json_carries_the_flag_and_the_reason_it_exited(monkeypatch,
                                                            capsys):
    import json
    _drive(monkeypatch, [_skipped(), _ran()])
    assert run_corpus.main(["--require-driver", "--json"]) == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["require_driver"] is True
    assert doc["exit_reason"] == SENTENCE
    # The skip list is what it always was: the flag adds a verdict, it does
    # not rewrite the record of what happened.
    assert doc["skipped"] == [{"case": "rust/panic",
                               "reason": run_corpus.NO_DRIVER}]


def test_the_json_says_false_and_names_no_reason_without_the_flag(monkeypatch,
                                                                  capsys):
    import json
    _drive(monkeypatch, [_skipped(), _ran()])
    assert run_corpus.main(["--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["require_driver"] is False
    assert "exit_reason" not in doc


def test_the_json_names_no_reason_when_the_flag_forced_nothing(monkeypatch,
                                                               capsys):
    import json
    _drive(monkeypatch, [_ran("a")])
    assert run_corpus.main(["--require-driver", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["require_driver"] is True
    assert "exit_reason" not in doc


def test_the_flag_is_in_the_help(monkeypatch, capsys):
    """A gate nobody can find is a gate nobody uses."""
    with pytest.raises(SystemExit):
        run_corpus.main(["--help"])
    assert "--require-driver" in capsys.readouterr().out
