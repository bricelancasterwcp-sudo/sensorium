"""The corpus asked through the MCP server: `--via mcp`, `--compare-cli`.

The corpus has had exactly one seam to the tool since it was written --
`run_corpus._cli`, a subprocess running `python -m sensorium <argv>` --
and every pre-registered question is checked against what that seam
printed. The MCP server is a SECOND surface answering those same
questions, and a second surface nobody's regression suite covers is a
second surface free to answer differently. `--via mcp` asks every
question that IS a tool through a real server started per case;
`--compare-cli` asks the read-only ones both ways and reports any
answer the two do not agree on.

What is pinned here, and why each pin bites:

* `redact` is not a tool, and its three questions (all in
  `redact_retrofit`) are asked through the CLI and NAMED -- never
  skipped, because the two questions after them read the store those
  three rewrote (P7).
* the per-case server's environment is `_cli`'s and not the case's
  `env:`, so the two seams answer from one environment (P8).
* `--compare-cli` never re-runs an executing tool: a second `refocus`
  would compare two executions rather than two seams, and would leave
  a third trace behind for the next question to find (P26).
* the JSON payload's new keys are conditional, so a `cli`-mode run's
  document is byte-for-byte the one it always was.

MUTATION-TESTED. Each mutant below was applied to the committed tree,
the named test confirmed to FAIL, and the tree restored:

* `is_tool` answers True for every word, so `redact` is routed through
  the server -> `test_run_case_under_via_mcp_names_the_cli_questions`
  fails: the server answers `Unknown tool: redact`, the retrofit never
  happens, and the two questions after it fail too.
* `PYTHONDONTWRITEBYTECODE` dropped from `CaseServer.env`, and
  `--max-output` dropped from its argv ->
  `test_case_server_env_is_the_cli_seams` fails on each. The first of
  those two SURVIVED the first time it was run: `env` is built over
  `os.environ` and the mutation run had set that variable itself, so
  the assertion passed over a `CaseServer` that set nothing. The test
  deletes both variables from this process before building one now,
  which is what makes the mutant fail.
* the `executes` guard dropped, so a `refocus` question is run through
  the CLI a second time ->
  `test_compare_never_reruns_refocus_through_the_cli` fails.
* `via_cli` written into the JSON payload unconditionally ->
  `test_json_keys_are_conditional` fails.
"""
from __future__ import annotations

import json
import shutil

import pytest

pytest.importorskip("yaml")

from corpus import run_corpus, via_mcp                        # noqa: E402
from corpus.cases import load_cases                           # noqa: E402


def _case(name: str):
    """One Python corpus case by name, loaded the way the runner loads
    it -- a stand-in would test this module against a case shape the
    corpus does not have."""
    for case in load_cases(only_dir="."):
        if case.name == name:
            return case
    raise AssertionError(f"no corpus case named {name!r}")


@pytest.fixture(autouse=True)
def restore_mode():
    """`VIA` and `COMPARE` are module state, and `main` writes them.

    Without this, a test here that runs `main --via mcp` would leave
    every later test in the session -- in this file and in
    `tests/test_corpus.py` -- recording through a server nobody asked
    for.
    """
    before = (via_mcp.VIA, via_mcp.COMPARE)
    yield
    via_mcp.VIA, via_mcp.COMPARE = before


def _mcp_mode(compare: bool = False) -> None:
    via_mcp.VIA, via_mcp.COMPARE = "mcp", compare


def _plant_x(monkeypatch):
    """Make the CLI seam answer one byte differently from the server.

    Only for QUESTIONS: a `run` is a recording, and an `X` appended to
    its stdout would break the `run:` line `_run_ids` reads.
    """
    real = run_corpus._cli

    def planted(args, cwd, sdir, extra_env=None):
        out = real(args, cwd, sdir, extra_env)
        if args and args[0] != "run":
            out.stdout += "X"
        return out

    monkeypatch.setattr(run_corpus, "_cli", planted)


# -- the table --------------------------------------------------------------
def test_is_tool():
    """The server's own table answers, not a list kept here: `redact`
    is a command and deliberately not a tool, and `ts` is not a query
    at all."""
    assert via_mcp.is_tool("runs")
    assert not via_mcp.is_tool("redact")
    assert not via_mcp.is_tool("ts")


def test_executes_is_the_tool_tables_own_answer():
    """P26's predicate: `refocus` runs the recorded program, `runs`
    reads a file that is already written."""
    assert via_mcp.executes("refocus")
    assert not via_mcp.executes("runs")
    assert not via_mcp.executes("redact")      # not a tool at all


# -- one real question through one real server ------------------------------
def test_ask_routes_a_real_question_through_the_server(tmp_path):
    """The whole point, at its smallest: a corpus question, asked
    through the server, satisfies the expectations the corpus
    registered for it before any output was looked at."""
    case = _case("silent_swallow")
    wd = tmp_path / case.name
    shutil.copytree(case.dir, wd)
    sdir = wd / ".sensorium"
    recorded = run_corpus._cli(["run", "--", "main.py"], wd, sdir)
    ids = run_corpus._run_ids(recorded.stdout)
    assert ids, recorded.stdout + recorded.stderr
    spec = case.questions[0]
    q = run_corpus.sub_run_ids(spec, ids[0], None)

    with via_mcp.CaseServer(wd, sdir) as server:
        out = via_mcp.ask(server, [str(a) for a in q["command"]])

    assert out.via == "mcp"
    assert run_corpus.check_question(
        q, out.stdout + out.stderr, out.returncode) == []


def test_ask_answers_an_unknown_tool_rather_than_raising(tmp_path):
    """A word the server has no tool for comes back as an exit-2
    answer, not as an exception out of `run_case`: the harness reports
    a failed question, which is what a routing mistake IS."""
    case = _case("silent_swallow")
    wd = tmp_path / case.name
    shutil.copytree(case.dir, wd)
    sdir = wd / ".sensorium"
    run_corpus._cli(["run", "--", "main.py"], wd, sdir)

    with via_mcp.CaseServer(wd, sdir) as server:
        out = via_mcp.ask(server, ["redact", "last", "--dry-run"])

    assert (out.stdout, out.returncode, out.via) == ("", 2, "mcp")
    assert out.stderr == "error: Unknown tool: redact"


# -- the seams the server is started with -----------------------------------
def test_case_server_env_is_the_cli_seams(tmp_path, monkeypatch):
    """P8. The server's environment is what `_cli` hands a question's
    child and nothing else: a case's `env:` reaches the RECORDING only,
    so a server carrying it would answer from an environment the CLI it
    is compared against never had.

    Both variables are DELETED from this process's first: `env` is
    built over `os.environ`, and pytest is often launched with
    `PYTHONDONTWRITEBYTECODE=1` itself -- inherited, the assertion
    below would pass over a `CaseServer` that sets nothing at all.
    """
    case = _case("redact_retrofit")
    assert case.env, "this case is the one with an env: block"
    for inherited in ("SENSORIUM_DIR", "PYTHONDONTWRITEBYTECODE"):
        monkeypatch.delenv(inherited, raising=False)
    sdir = tmp_path / ".sensorium"
    server = via_mcp.CaseServer(tmp_path, sdir)

    assert server.env["SENSORIUM_DIR"] == str(sdir)
    assert server.env["PYTHONDONTWRITEBYTECODE"] == "1"
    for name in case.env:
        assert name not in server.env, name
    assert server.argv[-2:] == ["--max-output", "1048576"]
    assert "--allow-run" in server.argv
    assert ["--store", str(sdir)] == server.argv[-4:-2]


# -- routing ----------------------------------------------------------------
def test_run_case_under_via_mcp_names_the_cli_questions(tmp_path):
    """P7. `redact_retrofit` is the one case with questions that are
    not tools: the three `redact` ones go through the CLI and are named
    by id, and the two after them -- which read the store those three
    rewrote -- still pass."""
    _mcp_mode()
    res = run_corpus.run_case(_case("redact_retrofit"), tmp_path)

    assert res.failures == []
    assert res.via_cli == ["what-would-the-retrofit-take",
                           "the-retrofit-rewrites-once",
                           "a-second-pass-finds-nothing"]
    assert res.asked == 5


def test_compare_reports_a_planted_difference(tmp_path, monkeypatch):
    """The comparison has to be able to FAIL. With the CLI seam
    answering one byte more than the server, every read-only question
    is reported as a stdout difference -- and the question itself still
    passes, because what was checked is the server's answer."""
    _mcp_mode(compare=True)
    _plant_x(monkeypatch)
    res = run_corpus.run_case(_case("silent_swallow"), tmp_path)

    assert res.failures == []
    assert len(res.differences) == 2
    for d in res.differences:
        assert d["case"] == "silent_swallow"
        assert d["field"] == "stdout"
        assert "X" in str(d["cli"])
        assert d["mcp"] != d["cli"]
    assert [d["id"] for d in res.differences] == ["what-was-dropped",
                                                  "which-inputs"]


def test_compare_never_reruns_refocus_through_the_cli(tmp_path, monkeypatch):
    """P26. `nondeterministic` asks a `refocus` and then a `runs`. The
    refocus RUNS the recorded program: a second one would compare two
    executions rather than two seams, and would leave a third trace in
    the store for the `runs` question to find."""
    _mcp_mode(compare=True)
    real = run_corpus._cli

    def guard(args, cwd, sdir, extra_env=None):
        if args and args[0] == "refocus":
            raise AssertionError(f"refocus re-run through the CLI: {args}")
        return real(args, cwd, sdir, extra_env)

    monkeypatch.setattr(run_corpus, "_cli", guard)
    res = run_corpus.run_case(_case("nondeterministic"), tmp_path)

    assert res.failures == []
    assert res.differences == []
    assert res.asked == 2


# -- what the run reports ---------------------------------------------------
def test_json_keys_are_conditional(capsys):
    """A `cli`-mode payload is the document it always was -- the exact
    dict `tests/test_corpus_harness.py` pins -- and each new key
    appears only where it says something."""
    assert run_corpus.main(["--only", "silent_swallow", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "cases": 1, "questions": 2, "skipped": [], "failures": [],
        "errors": [], "require_driver": False}

    assert run_corpus.main(["--only", "silent_swallow", "--via", "mcp",
                            "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["via"] == "mcp"
    assert "via_cli" not in payload        # every question here is a tool
    assert "mcp_differences" not in payload           # no --compare-cli

    assert run_corpus.main(["--only", "redact_retrofit", "--via", "mcp",
                            "--compare-cli", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["via"] == "mcp"
    assert payload["via_cli"] == [
        "redact_retrofit/what-would-the-retrofit-take",
        "redact_retrofit/the-retrofit-rewrites-once",
        "redact_retrofit/a-second-pass-finds-nothing"]
    assert payload["mcp_differences"] == []


def test_summary_sentences(capsys, monkeypatch):
    """Both clauses, after the sentence the summary always printed.

    A comparison that found nothing says so. `; 0 MCP/CLI
    difference(s)` is the whole claim this mode is run for, and a
    summary silent about it cannot be told from one where the flag was
    never passed -- which is the same failure `--require-driver`
    exists to prevent one line up.
    """
    assert run_corpus.main(["--only", "redact_retrofit", "--via", "mcp",
                            "--compare-cli"]) == 0
    assert ("5 questions, 0 failures, 0 error(s); 3 question(s) asked "
            "through the CLI (not tools); 0 MCP/CLI difference(s)"
            ) in capsys.readouterr().out

    # ...and a run that compared nothing claims nothing.
    assert run_corpus.main(["--only", "silent_swallow", "--via", "mcp"]) == 0
    out = capsys.readouterr().out
    assert "2 questions, 0 failures, 0 error(s)\n" in out
    assert "MCP/CLI difference" not in out
    assert "question(s) asked through the CLI" not in out

    _plant_x(monkeypatch)
    assert run_corpus.main(["--only", "silent_swallow", "--via", "mcp",
                            "--compare-cli"]) == 1
    out = capsys.readouterr().out
    assert "; 2 MCP/CLI difference(s)" in out
    assert "  diff silent_swallow/what-was-dropped: stdout mcp=" in out
    assert "question(s) asked through the CLI" not in out


def test_compare_cli_without_via_mcp_is_exit_2(capsys):
    """There is nothing to compare against: a flag that quietly did
    nothing would report a clean run over a comparison never made."""
    assert run_corpus.main(["--compare-cli"]) == 2
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1
    assert "--compare-cli" in err[0] and "--via mcp" in err[0]


def test_help_lists_via_and_compare_cli():
    """Both flags, and what each says -- whitespace-folded, because
    argparse wraps a help string to the terminal it is printed on."""
    text = " ".join(run_corpus._parser().format_help().split())
    assert "--via {cli,mcp}" in text
    assert ("ask every tool question through a sensorium mcp server "
            "started per case; non-tool questions still go through the "
            "CLI and are named") in text
    assert "--compare-cli" in text
    assert ("with --via mcp: also run each read-only question through the "
            "CLI and report any stdout or exit difference") in text
