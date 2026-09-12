"""The corpus loader and its refusals; the harness runs next door.

Two different things are tested here and in `test_corpus_harness.py`, and
they must not be confused. That file's last test runs the real corpus end to
end -- that is the regression suite for the query layer. Everything else
tests the HARNESS, because a harness that reports success when a question's
expectation is absent is worse than no corpus at all: it converts every case
into a comment while continuing to print "0 failures".

So each assertion form gets a test that the harness NOTICES its violation,
and `expect_line` additionally gets a test that a group satisfied by two
different lines is a FAILURE -- that is the whole reason the form exists,
and the one mutation a naive implementation would pass. Those two live in
the harness file, which imports `GOOD_QUESTION` and `_load_one` from here
rather than keeping a second copy: the halves were split 2026-09-12 (S5 rung
4's debts) so each file stays under the repo-wide 800-line ceiling.
"""

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
    assert len(cases) >= 20
    ids = [(c.name, q["id"]) for c in cases for q in c.questions]
    assert len(ids) == len(set(ids))


def test_the_classifiers_under_claim_is_registered_somewhere():
    """An `ambiguous` verdict must be pinned by a case, not left to absence.

    The under-claim rows are exactly the ones that regress silently into
    over-claiming, which is `exceptions`' worst failure. A corpus that
    respects the contract only by never reaching it would not notice.
    """
    cases = {c.name: c for c in run_corpus.load_cases()}
    # `generator_swallow` held this pin until coroutine frames made its
    # generator decidable -- the under-claim now lives where it is still the
    # honest answer: a handler frame that is STILL SUSPENDED when recording
    # stops, and so has no closed_by to read.
    q, = [q for q in cases["suspended_handler"].questions
          if q["command"][0] == "exceptions"]
    assert "dispositions: ambiguous 1" in q["expect_contains"]
    assert "SWALLOWED" in q["expect_absent"]
    assert "dispositions: swallowed" in q["expect_absent"]


def test_every_rust_exceptions_question_preregisters_its_swallow_set():
    """E6 (design R15) compares the printed SWALLOWED lines against a
    PRE-REGISTERED set, and the `dispositions:` tally WHOLE. Both live in the
    question file and both are checked here rather than trusted, because the
    two ways a rung-3 case can quietly stop testing anything are silent:

    * a question that pins a verdict sentence but not the tally lets a chain
      change disposition without failing anything, since the sentence for
      the OTHER chains is still on some line somewhere;
    * a question that pins neither a `SWALLOWED` line nor an explicit absence
      registers no swallow set at all, and a collector reading it would take
      that as "the empty set" -- an accusation-count of zero asserted by
      nobody. Ten of the seventeen rung-3 cases legitimately have an empty
      swallow set, so the empty case has to be SAID.

    The `no exceptions recorded` answers are the third shape: they carry no
    tally line at all, so what they must pin is that none was printed.
    """
    for case in run_corpus.load_cases():
        if not case.is_cargo:
            continue
        for q in case.questions:
            if q["command"][0] != "exceptions":
                continue
            where = f"{case.name}/{q['id']}"
            contains = q.get("expect_contains") or []
            absent = q.get("expect_absent") or []
            swallows = [g for g in (q.get("expect_line") or [])
                        if g[0] == "SWALLOWED"]
            if "no exceptions recorded" in contains:
                assert "dispositions:" in absent, (
                    f"{where}: an empty answer must pin that no tally was "
                    "printed")
                continue
            tally = [c for c in contains if c.startswith("dispositions: ")]
            assert len(tally) == 1, (
                f"{where}: needs exactly one whole `dispositions: ...` line "
                f"in expect_contains, found {tally}")
            if swallows:
                assert q.get("expect_count", {}).get("SWALLOWED") == \
                    len(swallows), (
                        f"{where}: {len(swallows)} SWALLOWED line(s) "
                        "registered but expect_count does not pin that many")
            else:
                assert "SWALLOWED" in absent, (
                    f"{where}: registers no swallow and does not say so")
                assert "dispositions: swallowed" in absent, (
                    f"{where}: must pin that the tally carries no swallow")


def test_every_cli_command_is_exercised_by_some_question():
    used = {q["command"][0] for c in run_corpus.load_cases()
            for q in c.questions}
    assert CLI_COMMANDS - used == set(), (
        "no corpus question exercises: " + ", ".join(sorted(CLI_COMMANDS
                                                            - used)))


LOGGING_TOOLS = ("dbg!", "RUST_LOG", "RUST_BACKTRACE")

#: The vitest corpus's three channels. Unlike `LOGGING_TOOLS` above -- where a
#: Rust question need only rule out ONE tool, because different chains fail
#: differently -- every vitest question is checked against ALL THREE: this
#: corpus's questions were written to show that `console.log`, `DEBUG` and a
#: stack trace all fail the same way, and a question naming only one or two
#: has not shown that. `DEBUG` is a word, not the literal `DEBUG=*`
#: invocation, because a `why_logs_fail` may spell the channel either way.
TS_LOGGING_CHANNELS = ("console.log", "DEBUG", "stack trace")


def test_every_cargo_question_names_the_logging_tool_that_fails():
    """The Rust corpus's own version of `why_logs_fail`, per the spec: each
    question names which of `dbg!`, RUST_LOG or RUST_BACKTRACE fails and why.

    Checked rather than trusted, because a `why_logs_fail` that argues in the
    abstract -- "no log line says which execution it came from" -- reads as a
    real justification while never being tested against the tool a Rust
    developer would actually reach for. Three of the first thirteen cases
    drifted that way; this is what stops the twenty-eighth.
    """
    for case in run_corpus.load_cases():
        if not case.is_cargo:
            continue
        for q in case.questions:
            why = q["why_logs_fail"]
            assert any(tool in why for tool in LOGGING_TOOLS), (
                f"{case.name}/{q['id']}: why_logs_fail names none of "
                + ", ".join(LOGGING_TOOLS))


def test_every_vitest_question_names_all_three_logging_channels():
    """The TypeScript corpus's own version of the guard above.

    Every `program: vitest` question's `why_logs_fail` must name ALL THREE
    of `console.log`, `DEBUG` and `stack trace` -- not merely one of them,
    the way a cargo question may. Checked rather than trusted, for the same
    reason the Rust guard is: a justification that reads as real prose while
    naming only one of the three channels would still pass a check that only
    looked for "some tool", and the point of these thirteen cases is that
    all three ordinary channels fail them the same way.
    """
    for case in run_corpus.load_cases():
        if not case.is_vitest:
            continue
        for q in case.questions:
            why = q["why_logs_fail"]
            missing = [c for c in TS_LOGGING_CHANNELS if c not in why]
            assert not missing, (
                f"{case.name}/{q['id']}: why_logs_fail does not name "
                + ", ".join(missing))


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
    """One Python recording is one process, so `$RUN2` needs a `second_run`.

    A cargo recording is one trace per PROCESS, and a vitest recording is one
    trace per TEST FILE, so either may legally take `$RUN2` from the second
    trace of a single invocation (`rust/abort` records a parent and the child
    it spawned; `typescript/pass_vs_fail` records two test files) and is
    checked at run time against the ids the recording really produced. The
    rule is scoped here rather than dropped: a Python case that used `$RUN2`
    without declaring a second run would still be a mistake, and this is what
    says so.
    """
    for case in run_corpus.load_cases():
        if case.is_cargo or case.is_vitest:
            continue
        uses = any("$RUN2" in q["command"] for q in case.questions)
        assert uses == (case.second_run is not None), case.name


def test_a_cargo_case_that_uses_run2_declares_a_source_for_it():
    """...and the cargo half of that rule, as far as YAML can carry it.

    A cargo case using `$RUN2` either declares a `second_run` or expects its
    single invocation to record two processes. The second is not decidable
    from the file, so what is checked here is that such a case exists and is
    the one it is meant to be -- a case using `$RUN2` with no `second_run`
    is a deliberate shape, not a typo that slipped through.
    """
    without = {c.name for c in run_corpus.load_cases()
               if c.is_cargo and c.second_run is None
               and any("$RUN2" in q["command"] for q in c.questions)}
    assert without == {"rust/abort"}


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
