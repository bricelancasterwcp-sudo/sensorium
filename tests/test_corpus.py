"""The corpus, and the harness that runs it.

Two different things are tested here and they must not be confused. The last
test runs the real corpus end to end -- that is the regression suite for the
query layer. Everything above it tests the HARNESS, because a harness that
reports success when a question's expectation is absent is worse than no
corpus at all: it converts every case into a comment while continuing to
print "0 failures".

So each assertion form gets a test that the harness NOTICES its violation,
and `expect_line` additionally gets a test that a group satisfied by two
different lines is a FAILURE -- that is the whole reason the form exists,
and the one mutation a naive implementation would pass.
"""
import textwrap

import pytest

pytest.importorskip("yaml")

from corpus import run_corpus                                    # noqa: E402

# Every command the CLI offers. The corpus is meant to demonstrate that each
# one answers a question the others cannot, so a command that quietly loses
# its only corpus question should fail here rather than go unnoticed.
CLI_COMMANDS = {"runs", "info", "tree", "frame", "grep", "flow", "exceptions",
                "watch", "diff", "refocus"}

PROGRAM = """\
def inner(n):
    return n * 2


def main():
    inner(21)


if __name__ == "__main__":
    main()
"""

GOOD_QUESTION = {
    "id": "doubles",
    "ask": "What did inner return?",
    "truth": "42",
    "why_logs_fail": "nothing is printed",
    "command": ["grep", "$RUN", "inner", "--kind", "RETURN"],
    "expect_contains": ["matches: 1"],
}


def _case(tmp_path, questions, program=PROGRAM, **top):
    """A synthetic one-program case on disk, loaded through `load_cases`."""
    d = tmp_path / "synth"
    d.mkdir(parents=True, exist_ok=True)
    (d / "main.py").write_text(program)
    spec = {"program": "main.py", "questions": questions, **top}
    import yaml
    (d / "questions.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
    return d


def _load_one(tmp_path, questions, **top):
    _case(tmp_path, questions, **top)
    cases = run_corpus.load_cases(tmp_path)
    assert len(cases) == 1
    return cases[0]


# -- the corpus itself -----------------------------------------------------
def test_all_cases_load_and_validate():
    cases = run_corpus.load_cases()
    assert len(cases) >= 11
    ids = [(c.name, q["id"]) for c in cases for q in c.questions]
    assert len(ids) == len(set(ids))


def test_the_classifiers_under_claim_is_registered_somewhere():
    """An `ambiguous` verdict must be pinned by a case, not left to absence.

    The under-claim rows are exactly the ones that regress silently into
    over-claiming, which is `exceptions`' worst failure. A corpus that
    respects the contract only by never reaching it would not notice.
    """
    cases = {c.name: c for c in run_corpus.load_cases()}
    q, = cases["generator_swallow"].questions
    assert "dispositions: ambiguous 2" in q["expect_contains"]
    assert "SWALLOWED" in q["expect_absent"]
    assert "dispositions: swallowed" in q["expect_absent"]


def test_every_cli_command_is_exercised_by_some_question():
    used = {q["command"][0] for c in run_corpus.load_cases()
            for q in c.questions}
    assert CLI_COMMANDS - used == set(), (
        "no corpus question exercises: " + ", ".join(sorted(CLI_COMMANDS
                                                            - used)))


def test_every_question_registers_a_real_why_logs_fail():
    """The field that decides whether a case justifies the tool at all.

    A one-word placeholder there is how a corpus quietly fills up with cases
    a print() would have answered, so the floor is checked rather than
    trusted.
    """
    for case in run_corpus.load_cases():
        for q in case.questions:
            why = q["why_logs_fail"].strip()
            assert len(why.split()) >= 12, f"{case.name}/{q['id']}: {why!r}"


def test_second_run_is_declared_wherever_run2_is_used():
    for case in run_corpus.load_cases():
        uses = any("$RUN2" in q["command"] for q in case.questions)
        assert uses == (case.second_run is not None), case.name


# -- schema validation: a bad question must not load silently --------------
def test_main_isolates_a_harness_error_in_one_case(monkeypatch, capsys,
                                                   tmp_path):
    """A crash inside `run_case` for one case must not abandon the whole run
    and drop every already-computed result. It is reported as a distinct ERROR
    -- not a failed question -- the later cases still run, and the run exits
    non-zero. The case is placed FIRST so its crash would, unfixed, keep the
    second from running at all."""
    bad = run_corpus.Case(name="bad_case", dir=tmp_path, program="main.py")
    good = run_corpus.Case(name="good_case", dir=tmp_path, program="main.py")
    monkeypatch.setattr(run_corpus, "load_cases", lambda *a, **k: [bad, good])

    def fake_run_case(case, workdir):
        if case.name == "bad_case":
            raise RuntimeError("copytree exploded")
        r = run_corpus.CaseResult(case.name)
        r.asked = 1
        return r

    monkeypatch.setattr(run_corpus, "run_case", fake_run_case)

    rc = run_corpus.main([])
    out = capsys.readouterr().out
    assert rc == 1                              # a harness error fails the run
    assert "good_case" in out                   # the later case still ran
    assert "harness error" in out
    assert "RuntimeError" in out and "copytree exploded" in out
    assert "1 error" in out                     # counted, distinct from failures


def test_unknown_question_key_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="unknown"):
        _load_one(tmp_path, [{**GOOD_QUESTION, "expect_contian": ["x"]}])


def test_unknown_top_level_key_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="unknown keys"):
        _load_one(tmp_path, [GOOD_QUESTION], focus=["main:inner"])


def test_missing_required_key_is_an_error(tmp_path):
    q = {k: v for k, v in GOOD_QUESTION.items() if k != "why_logs_fail"}
    with pytest.raises(ValueError, match="why_logs_fail"):
        _load_one(tmp_path, [q])


def test_a_question_that_asserts_nothing_is_refused(tmp_path):
    """The failure this whole file exists for: a question that always passes."""
    q = {**GOOD_QUESTION, "expect_contains": []}
    with pytest.raises(ValueError, match="asserts nothing"):
        _load_one(tmp_path, [q])


def test_duplicate_question_ids_are_refused(tmp_path):
    with pytest.raises(ValueError, match="duplicate question id"):
        _load_one(tmp_path, [GOOD_QUESTION, dict(GOOD_QUESTION)])


def test_run2_without_a_second_run_is_refused_at_load(tmp_path):
    q = {**GOOD_QUESTION, "command": ["diff", "$RUN", "$RUN2"]}
    with pytest.raises(ValueError, match="no second_run"):
        _load_one(tmp_path, [q])


def test_empty_command_is_refused(tmp_path):
    with pytest.raises(ValueError, match="non-empty list"):
        _load_one(tmp_path, [{**GOOD_QUESTION, "command": []}])


def test_malformed_expect_line_group_is_refused(tmp_path):
    q = {**GOOD_QUESTION, "expect_line": ["not-a-group"]}
    with pytest.raises(ValueError, match="non-empty list of substrings"):
        _load_one(tmp_path, [q])


def test_malformed_expect_count_is_refused(tmp_path):
    q = {**GOOD_QUESTION, "expect_count": ["nope"]}
    with pytest.raises(ValueError, match="expect_count must be a mapping"):
        _load_one(tmp_path, [q])


def test_depends_on_accepts_a_question_declared_earlier(tmp_path):
    case = _load_one(tmp_path, [GOOD_QUESTION,
                                {**GOOD_QUESTION, "id": "second",
                                 "depends_on": "doubles"}])
    assert [q["id"] for q in case.questions] == ["doubles", "second"]


def test_depends_on_a_later_question_is_refused(tmp_path):
    """A reorder must fail at LOAD, not as a puzzling missing-output error.

    `nondeterministic`'s `runs` question only sees a refocus verdict because
    the refocus question ran first; nothing else in the schema records that.
    """
    with pytest.raises(ValueError, match="must name a question earlier"):
        _load_one(tmp_path, [{**GOOD_QUESTION, "id": "first",
                              "depends_on": "second"},
                             {**GOOD_QUESTION, "id": "second"}])


def test_depends_on_itself_is_refused(tmp_path):
    with pytest.raises(ValueError, match="must name a question earlier"):
        _load_one(tmp_path, [{**GOOD_QUESTION, "depends_on": "doubles"}])


def test_depends_on_an_unknown_id_is_refused(tmp_path):
    with pytest.raises(ValueError, match="must name a question earlier"):
        _load_one(tmp_path, [GOOD_QUESTION,
                             {**GOOD_QUESTION, "id": "second",
                              "depends_on": "typo"}])


def test_depends_on_must_be_a_string(tmp_path):
    with pytest.raises(ValueError, match="depends_on must be the id"):
        _load_one(tmp_path, [GOOD_QUESTION,
                             {**GOOD_QUESTION, "id": "second",
                              "depends_on": ["doubles"]}])


def test_a_question_that_is_not_a_mapping_is_refused(tmp_path):
    with pytest.raises(ValueError, match="must be a mapping"):
        _load_one(tmp_path, ["just a string"])


def test_expect_contains_given_as_a_bare_string_is_refused(tmp_path):
    """`expect_contains: matches` would otherwise match per CHARACTER."""
    with pytest.raises(ValueError, match="expect_contains must be a list"):
        _load_one(tmp_path, [{**GOOD_QUESTION, "expect_contains": "matches"}])


def test_a_case_missing_program_or_questions_is_refused(tmp_path):
    d = tmp_path / "synth"
    d.mkdir(parents=True)
    (d / "questions.yaml").write_text("program: main.py\n")
    with pytest.raises(ValueError, match="needs both"):
        run_corpus.load_cases(tmp_path)


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
    assert "uses $RUN2 but no second_run declared" in res.failures[0]


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
    assert payload == {"cases": 1, "questions": 2, "failures": [],
                       "errors": []}


def test_corpus_passes():
    assert run_corpus.main([]) == 0
