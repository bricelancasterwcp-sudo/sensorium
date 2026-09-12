"""The harness half of `test_corpus.py`, moved 2026-09-12 (S5 rung 4's debts)
so the file stays under 800; the last test runs the real corpus.

The split is by subject, not by size: everything here is about the HARNESS --
the cargo and vitest cases the Python recorder never touches, what each
assertion form must bite on, and the end-to-end path from recording to
verdict. `tests/test_corpus.py` keeps the loader and its refusals, and the
shared fixtures (`GOOD_QUESTION`, `_load_one`) are imported from it rather
than duplicated: two copies of a question template drift, and a drifted
template is a test that stops testing what it names.
"""
import subprocess
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("yaml")

from corpus import run_corpus                                    # noqa: E402
from tests.test_corpus import GOOD_QUESTION, _load_one           # noqa: E402

# -- the cargo half: a case the Python recorder never touches --------------
CARGO_QUESTION = {**GOOD_QUESTION, "command": ["tree", "$RUN"]}


def _cargo_spec(**over):
    return {"program": "cargo", "cargo_args": ["run"],
            "questions": [CARGO_QUESTION], **over}


def _write(root, rel, spec):
    import yaml
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "questions.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
    return d


def test_a_cargo_case_is_found_under_rust_and_named_for_it(tmp_path):
    """`rust/panic` and a Python `panic` must be two different cases.

    The name carries the subdirectory, which is what keeps `--only`, the
    per-case report line and the (case, question id) uniqueness check from
    conflating a port with its original.
    """
    _write(tmp_path, "rust/panic", _cargo_spec())
    _write(tmp_path, "panic", {"program": "main.py",
                               "questions": [GOOD_QUESTION]})
    names = [c.name for c in run_corpus.load_cases(tmp_path)]
    assert names == ["panic", "rust/panic"]
    assert [c.is_cargo for c in run_corpus.load_cases(tmp_path)] == [False,
                                                                    True]


def test_a_cargo_case_needs_cargo_args(tmp_path):
    _write(tmp_path, "rust/synth", {"program": "cargo",
                                    "questions": [CARGO_QUESTION]})
    with pytest.raises(ValueError, match="needs a non-empty cargo_args"):
        run_corpus.load_cases(tmp_path)


def test_an_empty_cargo_args_is_refused(tmp_path):
    _write(tmp_path, "rust/synth", _cargo_spec(cargo_args=[]))
    with pytest.raises(ValueError, match="needs a non-empty cargo_args"):
        run_corpus.load_cases(tmp_path)


@pytest.mark.parametrize("key,value", [("record", {"focus": ["main:inner"]}),
                                       ("argv", ["1000"])])
def test_a_cargo_case_refuses_the_python_recorders_keys(tmp_path, key, value):
    """The failure this refusal exists for: a `record: {focus: …}` that
    reaches no recorder would leave every question passing against a
    call-tier trace while the file says it was recorded line by line."""
    _write(tmp_path, "rust/synth", _cargo_spec(**{key: value}))
    with pytest.raises(ValueError, match="the Python recorder's key"):
        run_corpus.load_cases(tmp_path)


def test_cargo_args_on_a_python_case_is_refused(tmp_path):
    _write(tmp_path, "synth", {"program": "main.py", "cargo_args": ["run"],
                               "questions": [GOOD_QUESTION]})
    with pytest.raises(ValueError, match="cargo_args belongs to"):
        run_corpus.load_cases(tmp_path)


def test_a_cargo_second_run_needs_its_own_cargo_args(tmp_path):
    _write(tmp_path, "rust/synth", _cargo_spec(second_run={"argv": ["1001"]}))
    with pytest.raises(ValueError, match="second_run of a 'cargo' case"):
        run_corpus.load_cases(tmp_path)


def _vitest_spec(**over):
    return {"program": "vitest", "harness_args": ["run", "fog/"],
            "questions": [GOOD_QUESTION], **over}


def _recorded_argv(tmp_path, monkeypatch, **over):
    """The argv a vitest case's recording WOULD run, without running it."""
    _write(tmp_path, "typescript/fog", _vitest_spec(**over))
    case, = run_corpus.load_cases(tmp_path)
    seen, out = [], "run: 20260101-000000-abcdef\n"
    monkeypatch.setattr(run_corpus.subprocess, "run", lambda a, **kw: (
        seen.append(a) or subprocess.CompletedProcess(a, 0, out, "")))
    ids, _2, _e = run_corpus._record_both(case, tmp_path, tmp_path, None)
    assert ids == ["20260101-000000-abcdef"] and len(seen) == 1
    return case, seen[0][seen[0].index("ts"):]


@pytest.mark.parametrize("over,want", [
    ({}, ["ts", "run", "--", "npx", "vitest", "run", "fog/"]),
    ({"record": {"focus": ["fog.ts:compute", "Fog"]}},
     ["ts", "run", "--focus", "fog.ts:compute", "--focus", "Fog", "--",
      "npx", "vitest", "run", "fog/"]),
])
def test_a_vitest_focus_reaches_the_command_in_order(tmp_path, monkeypatch,
                                                     over, want):
    """One `--focus` per entry, all of them BEFORE the `--`. Checked on the
    argv: a focus that never reached the driver records a call-tier trace
    whose per-line questions all answer "nothing was checked" -- which reads
    as the recorder's refusal rather than as a key the harness lost."""
    case, argv = _recorded_argv(tmp_path, monkeypatch, **over)
    assert case.record == (over.get("record") or {})
    assert argv == want


@pytest.mark.parametrize("over,says", [
    # Named as outside the vitest driver's closed key set, not as another
    # recorder's: `window` happens to be Python's, and a typo is nobody's.
    ({"record": {"window": "main"}},
     "record 'window' is not a key a 'vitest' case's record may carry"),
    ({"record": {"focus": ["f"], "window": "m"}},
     "the set is closed and holds one, 'focus'"),
    ({"record": {"focus": "fill"}}, "non-empty list of function specs"),
    ({"record": {"focus": []}}, "non-empty list of function specs"),
    ({"record": {"focus": [3]}}, "non-empty list of function specs"),
    ({"argv": ["1000"]}, "'argv' is the Python recorder's key"),
])
def test_a_vitest_case_refuses_everything_but_a_focus(tmp_path, over, says):
    # Asserted on the message, not `match=`: tmp_path carries the test's own
    # name, so a pattern spelling `window`/`focus` is satisfied by the PATH.
    _write(tmp_path, "typescript/fog", _vitest_spec(**over))
    with pytest.raises(ValueError) as ei:
        run_corpus.load_cases(tmp_path)
    assert says in str(ei.value)


def test_a_cargo_case_with_no_driver_is_skipped_by_name(tmp_path,
                                                        monkeypatch):
    """Not a pass, and not a failure: a third outcome with a reason.

    The Python CI matrix has no Rust toolchain, so this is the ordinary
    state there -- and a harness that counted these as passes would report
    a green suite for 27 cases it never ran.
    """
    _write(tmp_path / "spec", "rust/synth", _cargo_spec())
    case, = run_corpus.load_cases(tmp_path / "spec")
    monkeypatch.setattr(run_corpus, "cargo_driver", lambda: None)
    res = run_corpus.run_case(case, tmp_path / "work")
    assert res.skipped == run_corpus.NO_DRIVER
    assert res.asked == 0 and res.failures == [] and res.error is None
    # Nothing was copied and nothing was recorded: a skip is a decision made
    # before the work, not a failure discovered during it.
    assert not (tmp_path / "work").exists()


def test_the_summary_line_names_the_skips_and_still_exits_zero(monkeypatch,
                                                               capsys):
    skipped = run_corpus.CaseResult("rust/panic",
                                    skipped=run_corpus.NO_DRIVER)
    ran = run_corpus.CaseResult("silent_swallow")
    ran.asked = 2
    monkeypatch.setattr(run_corpus, "load_cases",
                        lambda *a, **k: [run_corpus.Case("x", Path("."), "p")])
    monkeypatch.setattr(run_corpus, "run_case",
                        lambda *a, **k: [ran, skipped].pop())
    assert run_corpus.main([]) == 0
    out = capsys.readouterr().out
    assert "skip  rust/panic" in out
    assert "no cargo-sensorium" in out
    assert "1 cases (1 skipped: no cargo-sensorium), 0 questions" in out


def test_sub_run_ids_reaches_expectations_not_only_the_command():
    """A question that asserts a run id must have the real one substituted.

    `rust/abort` pins that the parent's `info` prints `child runs: 1 --
    <the child's id>`; with substitution limited to the command, that
    expectation could only name the prefix, and "a child is linked" is not
    the claim -- "THAT child is linked" is.
    """
    q = {"command": ["info", "$RUN"],
         "expect_contains": ["child runs: 1 -- $RUN2"],
         "expect_line": [["$RUN2", "open"]],
         "expect_count": {"$RUN": 1},
         "expect_exit": 0}
    got = run_corpus.sub_run_ids(q, "AAA", "BBB")
    assert got["command"] == ["info", "AAA"]
    assert got["expect_contains"] == ["child runs: 1 -- BBB"]
    assert got["expect_line"] == [["BBB", "open"]]
    assert got["expect_count"] == {"AAA": 1}
    assert got["expect_exit"] == 0


def test_sub_run_ids_substitutes_run2_before_run():
    """`$RUN` first would turn `$RUN2` into `<run-id>2` -- a silently wrong
    lookup instead of an absent one."""
    assert run_corpus.sub_run_ids("$RUN2", "AAA", "BBB") == "BBB"
    assert run_corpus.sub_run_ids("$RUN2", "AAA", None) == "$RUN2"


# -- each assertion form must actually bite --------------------------------
OUT = textwrap.dedent("""\
    e4 CALL    price(points=1000, total=100.0)
    e5 CALL    silver(total=100.0)
    matches: 2
""")


def _q(**over):
    """A question over `OUT`. `expect_contains` starts EMPTY unless given, so
    each test's assertion is the only one in play and a failure names the
    form under test rather than a leftover from the template."""
    return {**GOOD_QUESTION, "expect_contains": [], **over}


def test_expect_contains_notices_an_absent_substring():
    assert run_corpus.check_question(
        _q(expect_contains=["matches: 2"]), OUT, 0) == []
    bad = run_corpus.check_question(
        _q(expect_contains=["matches: 3"]), OUT, 0)
    assert bad and "missing" in bad[0]


def test_expect_line_requires_one_line_to_carry_the_whole_group():
    """The point of the form: satisfied by two different lines is a FAIL.

    'price(points=1000' and 'silver' both appear in this output, and a whole
    -output substring check would call that "the 1000-point order took
    silver". It is not: those are two lines, and the pairing is the claim.
    """
    assert run_corpus.check_question(
        _q(expect_line=[["e4", "price(points=1000"]]), OUT, 0) == []
    bad = run_corpus.check_question(
        _q(expect_line=[["price(points=1000", "silver"]]), OUT, 0)
    assert bad and "no single line contains all of" in bad[0]


def test_expect_count_notices_the_wrong_number_of_occurrences():
    assert run_corpus.check_question(
        _q(expect_count={"CALL": 2}), OUT, 0) == []
    bad = run_corpus.check_question(_q(expect_count={"CALL": 3}), OUT, 0)
    assert bad and "appears 2 time(s), expected 3" in bad[0]


def test_expect_absent_notices_a_forbidden_substring():
    assert run_corpus.check_question(_q(expect_absent=["gold"]), OUT, 0) == []
    bad = run_corpus.check_question(_q(expect_absent=["silver"]), OUT, 0)
    assert bad and "unexpected 'silver'" in bad[0]


def test_exit_status_is_checked_even_when_the_text_matches():
    bad = run_corpus.check_question(_q(), OUT, 1)
    assert bad == ["exit 1 != 0"]
    assert run_corpus.check_question(_q(expect_exit=1), OUT, 1) == []


def test_every_violated_expectation_is_reported_not_just_the_first():
    bad = run_corpus.check_question(
        _q(expect_contains=["nope"], expect_absent=["silver"],
           expect_count={"CALL": 9}), OUT, 2)
    assert len(bad) == 4


# -- end-to-end: the harness records, queries and judges -------------------
def test_run_case_passes_a_question_whose_answer_is_really_there(tmp_path):
    case = _load_one(tmp_path / "spec", [GOOD_QUESTION])
    res = run_corpus.run_case(case, tmp_path / "work")
    assert res.failures == []
    assert res.asked == 1


def test_run_case_fails_a_question_whose_expectation_is_absent(tmp_path):
    """A false expectation must fail against a REAL recording and query.

    Checked end to end rather than against a canned string, because the
    failure mode being guarded is the harness reporting success -- and it
    reports on the whole pipeline, not on `check_question` alone.
    """
    q = _q(id="wrong", expect_contains=["matches: 7"],
           expect_line=[["RETURN", "inner -> 43"]])
    case = _load_one(tmp_path / "spec", [q])
    res = run_corpus.run_case(case, tmp_path / "work")
    assert res.asked == 1
    assert len(res.failures) == 1
    assert "missing 'matches: 7'" in res.failures[0]
    assert "no single line contains all of" in res.failures[0]
    # The failure has to be usable: it names the case, the question, the
    # exact command run, and what came back instead.
    assert "synth/wrong" in res.failures[0]
    assert "sensorium grep" in res.failures[0]
    assert "inner -> 42" in res.failures[0]


def test_cli_pins_the_trace_store_to_the_directory_it_is_given(tmp_path,
                                                               monkeypatch):
    """The corpus must never read or write the user's own ~/.sensorium.

    Asserted on the env actually handed to the subprocess rather than by
    observing side effects: the failure being guarded is a corpus run that
    silently lands in the real store, and by the time that is observable it
    has already happened.
    """
    import subprocess
    seen = {}

    def fake(argv, **kw):
        seen.update(kw)
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(run_corpus.subprocess, "run", fake)
    run_corpus._cli(["runs"], tmp_path, tmp_path / "store")
    assert seen["env"]["SENSORIUM_DIR"] == str(tmp_path / "store")
    assert seen["cwd"] == tmp_path
    assert seen["argv"][1:] == ["-m", "sensorium", "runs"]


def test_run_case_keeps_its_trace_store_inside_the_disposable_workdir(tmp_path):
    case = _load_one(tmp_path / "spec", [GOOD_QUESTION])
    work = tmp_path / "work"
    assert run_corpus.run_case(case, work).failures == []
    traces = list((work / "synth" / ".sensorium" / "traces").glob("*.db"))
    assert len(traces) == 1


def test_run_case_reports_a_recording_that_never_started(tmp_path):
    case = _load_one(tmp_path / "spec", [GOOD_QUESTION],
                     program="raise SystemError('boom')\n")
    case.program = "no_such_file.py"
    res = run_corpus.run_case(case, tmp_path / "work")
    assert len(res.failures) == 1
    assert "recording failed" in res.failures[0]
    assert res.asked == 0


def test_a_recording_that_wrote_nothing_still_names_what_failed(tmp_path):
    """A driver that is not the driver exits non-zero and prints nothing.

    Without the code and the command in the line, the whole report is
    `recording failed: ` -- which names neither what ran nor that it
    refused, and reads like a harness bug rather than a bad
    SENSORIUM_CARGO_SENSORIUM.
    """
    _write(tmp_path / "spec", "rust/synth", _cargo_spec())
    case, = run_corpus.load_cases(tmp_path / "spec")
    res = run_corpus.run_case(case, tmp_path / "work", driver="/bin/false")
    assert res.asked == 0 and len(res.failures) == 1
    assert "recording failed" in res.failures[0]
    assert "/bin/false sensorium run" in res.failures[0]
    assert "exited 1" in res.failures[0]


def test_run2_substitution_reaches_the_second_recording(tmp_path):
    q = _q(id="two-runs", command=["diff", "$RUN", "$RUN2"],
           expect_contains=["verdict: MATCH"], expect_exit=0)
    case = _load_one(tmp_path / "spec", [q], second_run={"argv": []})
    res = run_corpus.run_case(case, tmp_path / "work")
    assert res.failures == []


def test_record_options_reach_the_recorder(tmp_path):
    """`record: {focus, window}` must actually gate capture, not sit unread.

    Checked by consequence: with line-level focus the frame's locals are in
    the trace, and `watch` can evaluate them; without it there is nothing to
    evaluate and the same question comes back NOTHING WAS CHECKED.
    """
    q = _q(id="locals", command=["watch", "$RUN", "--at", "main:inner",
                                 "--expr", "n > 20"],
           # A LINE site only exists because --focus was passed through; the
           # CALL site would be there either way.
           expect_line=[["HIT", "LINE", "inner", "n=21"]],
           expect_absent=["NOTHING WAS CHECKED"])
    case = _load_one(tmp_path / "spec", [q],
                     record={"focus": ["main:inner"], "window": "main"})
    assert run_corpus.run_case(case, tmp_path / "work").failures == []


def test_run2_in_a_command_is_refused_at_run_time_too(tmp_path):
    """The load-time guard is the one that fires in practice; this is the
    belt-and-braces one, for a Case built in code rather than from YAML."""
    case = _load_one(tmp_path / "spec", [GOOD_QUESTION])
    case.questions = [_q(id="late", command=["diff", "$RUN", "$RUN2"])]
    res = run_corpus.run_case(case, tmp_path / "work")
    assert res.asked == 1
    # The message says which of the two sources of a second id was missing,
    # because both are legitimate: no `second_run`, and only one trace out of
    # the recording.
    assert "uses $RUN2" in res.failures[0]
    assert "no second_run" in res.failures[0]
    assert "produced 1 trace(s)" in res.failures[0]


def test_main_refuses_when_no_case_matches(capsys):
    assert run_corpus.main(["--only", "nothing-called-this"]) == 2
    assert "no cases found" in capsys.readouterr().err


def test_main_show_prints_the_registered_question_and_its_command(capsys):
    assert run_corpus.main(["--only", "silent_swallow", "--show"]) == 0
    out = capsys.readouterr().out
    assert "silent_swallow/what-was-dropped: The total is lower" in out
    assert "$ sensorium exceptions $RUN" in out


def test_main_json_reports_the_same_totals(capsys):
    import json
    assert run_corpus.main(["--only", "silent_swallow", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    # `require_driver` is always present and `exit_reason` never is unless
    # the flag decided the exit -- `tests/test_run_corpus_require_driver.py`
    # is where that pair is pinned; here it only has to stay in the payload.
    assert payload == {"cases": 1, "questions": 2, "skipped": [],
                       "failures": [], "errors": [],
                       "require_driver": False}


def test_corpus_passes():
    assert run_corpus.main([]) == 0
