"""`refocus`: re-run a recording with deeper capture, and decide -- across
every recorded thread -- whether the rerun was the same execution.

This file covers running, refusing, and the VERDICT. What the verdict is
allowed to claim lives in `test_refocus_licence.py`.

Every rerun test drives the real CLI in a subprocess against real recorded
traces, because the behaviour under test IS the re-running: no synthetic
trace can show whether `refocus` chdir'd to the right place, inherited the
right filters, or actually captured anything the original lacked. Even the
INCOMPLETE original is real -- the recorder is SIGKILLed mid-run rather than
hand-built, so the test also proves which metadata survives that death.
"""
import os
import sys

import pytest

from sensorium import cli
from tests.helpers import run_cli
from tests.refocus_programs import (COUNTER, EXIT_FROM_FILE, LIB, LOOP,
                                    OUTSIDE_ROOT, READS_STDIN, SLEEPER,
                                    THREAD_BRANCH, THREAD_COUNT, TWO_FILES,
                                    WORKER_ON_SECOND_RUN, dbs, drop_meta,
                                    new_run, rec, record_killed,
                                    recorded_output, refocus, set_meta,
                                    synthetic, trace)


# -- MATCH ------------------------------------------------------------------

def test_refocus_match_captures_line_state_the_original_lacked(tmp_path):
    """A MATCH that captured nothing new is a useless success."""
    run_id, sdir = rec(tmp_path, LOOP)
    assert trace(sdir, run_id).events(kind="LINE") == []        # precondition

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sum: 35 2" in r.stdout             # the program really ran again
    assert "refocus verdict: MATCH" in r.stdout
    assert "threads: 1 recorded fingerprint(s) compared, all matching" \
        in r.stdout

    t = trace(sdir, new_run(r.stdout))
    assert t.meta["refocus_of"] == run_id
    assert t.meta["refocus_verdict"] == "MATCH"
    lines = t.events(kind="LINE")
    assert lines, "the deeper capture landed nothing"
    assert {t.code(e.code_id).qualname for e in lines} == {"accumulate"}
    assert "exit: rerun 0   original 0" in r.stdout


def test_refocus_adds_to_the_original_focus_instead_of_replacing_it(tmp_path):
    """A refocus only ever goes deeper -- never shallower than the trace it
    is supposed to explain."""
    run_id, sdir = rec(tmp_path, LOOP, extra=["--focus", "prog:helper"])

    added = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert added.returncode == 0, added.stdout + added.stderr
    t = trace(sdir, new_run(added.stdout))
    assert t.meta["focus"] == ["prog:helper", "prog:accumulate"]
    assert {t.code(e.code_id).qualname for e in t.events(kind="LINE")} == {
        "helper", "accumulate"}

    # asking again for what the original already focused adds nothing twice
    same = refocus(sdir, run_id, "--focus", "prog:helper")
    assert same.returncode == 0, same.stdout + same.stderr
    assert trace(sdir, new_run(same.stdout)).meta["focus"] == ["prog:helper"]


@pytest.mark.parametrize("filters", [["--exclude", "lib.py"],
                                     ["--include", "prog.py"]])
def test_refocus_inherits_the_original_include_exclude_filters(tmp_path,
                                                               filters):
    """Focus and window only gate LINE events, but include/exclude gate the
    CAUSAL stream itself: dropping either one would change what is compared
    and make every verdict meaningless."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib.py").write_text(LIB)
    run_id, sdir = rec(tmp_path, TWO_FILES, extra=filters)
    orig = trace(sdir, run_id)
    assert not any(c.qualname == "compute" for c in orig.codes())

    r = refocus(sdir, run_id, "--focus", "prog:main")
    assert r.returncode == 0, r.stdout + r.stderr
    new = trace(sdir, new_run(r.stdout))
    assert new.meta["include"] == orig.meta["include"]
    assert new.meta["exclude"] == orig.meta["exclude"]
    assert not any(c.qualname == "compute" for c in new.codes())
    assert "refocus verdict: MATCH" in r.stdout


def test_refocus_inherits_the_window_and_lets_it_be_overridden(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP, extra=["--focus", "prog:accumulate",
                                              "--window", "main"])
    kept = refocus(sdir, run_id, "--focus", "prog:helper")
    assert kept.returncode == 0, kept.stdout + kept.stderr
    assert "window: main" in kept.stdout
    assert trace(sdir, new_run(kept.stdout)).meta["window"] == "main"

    over = refocus(sdir, run_id, "--focus", "prog:helper",
                   "--window", "accumulate")
    assert over.returncode == 0, over.stdout + over.stderr
    assert trace(sdir, new_run(over.stdout)).meta["window"] == "accumulate"


def test_info_reports_a_verified_refocus_as_match(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    new_id = new_run(r.stdout)
    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    assert info.returncode == 0, info.stderr
    assert f"refocus-of: {run_id}  verdict: MATCH" in info.stdout


# -- DIVERGED ---------------------------------------------------------------

def test_refocus_diverges_when_state_outside_the_process_changed(tmp_path):
    run_id, sdir = rec(tmp_path, COUNTER)
    assert (tmp_path / "counter.txt").read_text() == "1"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    r = refocus(sdir, run_id, "--focus", "prog:bump", cwd=elsewhere)

    # establish that the executions really did differ before asserting on
    # anything the tool says about them
    assert (tmp_path / "counter.txt").read_text() == "2"
    assert not (elsewhere / "counter.txt").exists()   # reran in the orig cwd
    assert "\nagain\n" in r.stdout                    # the other branch ran

    assert r.returncode == 1, r.stdout + r.stderr
    assert "verdict: DIVERGED" in r.stdout
    assert ("refocus verdict: DIVERGED -- the compared thread took a "
            "different path") in r.stdout
    new_id = new_run(r.stdout)
    # A is the original and B is the rerun -- swapping them would point the
    # reader's drill-down commands at the wrong trace
    assert f"A {run_id}:" in r.stdout and f"B {new_id}:" in r.stdout
    t = trace(sdir, new_id)
    assert t.meta["refocus_verdict"] == "DIVERGED"
    assert t.meta["refocus_diverge_index"] is not None
    assert "first" in t.meta["refocus_diverge_a"]
    assert "again" in t.meta["refocus_diverge_b"]


def test_refocus_diverges_when_only_a_worker_thread_took_another_path(
        tmp_path):
    """The compared (main) thread matches exactly; a worker took the other
    branch. Both fingerprints are sitting in both traces, so comparing only
    one of them and calling the run a MATCH was a choice, not a limit."""
    run_id, sdir = rec(tmp_path, THREAD_BRANCH)
    assert "['A']" in recorded_output(sdir, run_id)
    assert len(trace(sdir, run_id).fingerprints()) > 1     # precondition

    r = refocus(sdir, run_id, "--focus", "prog:work")
    # establish the divergence before asserting anything about the report
    assert (tmp_path / "turn.txt").read_text() == "2"
    assert "\n['B']\n" in r.stdout

    assert "verdict: MATCH" in r.stdout          # ...on the compared thread
    assert r.returncode == 1, r.stdout + r.stderr
    assert "threads: DIVERGED" in r.stdout
    assert ("refocus verdict: DIVERGED -- a thread other than the compared "
            "one took a different path") in r.stdout
    t = trace(sdir, new_run(r.stdout))
    assert t.meta["refocus_verdict"] == "DIVERGED"
    assert "only in the rerun" in t.meta["refocus_thread_divergence"]


def test_refocus_diverges_when_the_same_worker_shape_ran_a_different_number(
        tmp_path):
    """Two runs can record the identical SET of per-thread fingerprints and
    still be different executions: here the rerun starts one more worker of
    exactly the same shape. Comparing shapes as a set would call that a
    MATCH; they are compared as a multiset for this reason."""
    run_id, sdir = rec(tmp_path, THREAD_COUNT)
    before = trace(sdir, run_id).fingerprints()
    assert len(before) == 3                       # main + 2 workers

    r = refocus(sdir, run_id, "--focus", "prog:tally")
    after = trace(sdir, new_run(r.stdout)).fingerprints()
    assert len(after) == 4                        # main + 3 workers
    # the SET of shapes really is the same on both sides
    assert ({h for h, _n in before.values()}
            == {h for h, _n in after.values()})

    assert r.returncode == 1, r.stdout + r.stderr
    assert "verdict: MATCH" in r.stdout           # ...on the compared thread
    assert "threads: DIVERGED" in r.stdout
    assert "3 thread(s) recorded originally, 4 on the rerun" in r.stdout


def test_a_diverged_trace_cannot_pass_itself_off_as_verified(tmp_path):
    run_id, sdir = rec(tmp_path, COUNTER)
    r = refocus(sdir, run_id, "--focus", "prog:bump")
    assert r.returncode == 1, r.stdout + r.stderr
    new_id = new_run(r.stdout)
    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    assert info.returncode == 0, info.stderr
    assert f"refocus-of: {run_id}" in info.stdout
    assert "verdict: DIVERGED" in info.stdout
    assert "verdict: MATCH" not in info.stdout


def test_runs_shows_the_verdict_beside_the_refocus_label(tmp_path):
    """A bare `refocus-of:` reads as a pedigree. Without the verdict beside
    it, a DIVERGED rerun looks in this listing exactly like a verified one."""
    run_id, sdir = rec(tmp_path, COUNTER)
    r = refocus(sdir, run_id, "--focus", "prog:bump")
    assert r.returncode == 1, r.stdout + r.stderr
    new_id = new_run(r.stdout)

    listing = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    assert listing.returncode == 0, listing.stderr
    line = next(ln for ln in listing.stdout.splitlines()
                if ln.startswith(new_id))
    assert f"refocus-of:{run_id}" in line
    assert "verdict:DIVERGED" in line
    orig_line = next(ln for ln in listing.stdout.splitlines()
                     if ln.startswith(run_id))
    assert "refocus-of" not in orig_line


def test_runs_shows_the_licence_beside_a_match(tmp_path):
    """A bare `verdict:MATCH` in the listing reads as a clean bill of health
    for a rerun whose licence was withheld on every count -- the same
    failure as a bare `refocus-of`, one level down."""
    run_id, sdir = rec(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(LOOP.replace("[5, 10, 20]", "[1, 2]"))
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert "licence: WITHHELD" in r.stdout
    new_id = new_run(r.stdout)

    listing = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    line = next(ln for ln in listing.stdout.splitlines()
                if ln.startswith(new_id))
    assert "verdict:MATCH(withheld:2,see-info)" in line

    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    assert "licence: withheld" in info.stdout
    assert "licence withheld: 1 source file(s) CHANGED" in info.stdout


def test_the_granted_licence_keeps_its_bounds_where_it_persists(tmp_path):
    """The good news must not lose its qualifications while the bad news
    keeps them. The terminal itemises five points and prints the blind
    spots; what persisted was the bare word "granted", in `info` and in the
    `runs` listing both -- while a WITHHELD licence itemised its reasons in
    `info`. `_stamp` has been writing `refocus_licence_verified` all along
    and nothing read it."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert "licence: verified against" in r.stdout, r.stdout
    new_id = new_run(r.stdout)

    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    facts = [ln for ln in info.stdout.splitlines()
             if ln.startswith("  licence verified: ")]
    # the child-witnessing point is a 3.14+ capability (no audit event fires for
    # a multiprocessing spawn below it), so the granted list is one shorter
    n_facts = 5 if sys.version_info >= (3, 14) else 4
    assert len(facts) == n_facts, info.stdout
    assert any("identical call shape" in f for f in facts)
    assert any("source file(s) unchanged by content" in f for f in facts)
    assert any("compared and unchanged" in f for f in facts)
    assert any("no thread started besides the main one" in f for f in facts)
    if sys.version_info >= (3, 14):
        assert any("no child process witnessed" in f for f in facts)
    else:
        assert not any("no child process witnessed" in f for f in facts)
    assert "does not record WHAT it was granted on" not in info.stdout

    listing = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    line = next(ln for ln in listing.stdout.splitlines()
                if ln.startswith(new_id))
    assert f"verdict:MATCH(granted:{n_facts},see-info)" in line


def test_a_licence_stamped_without_its_points_says_so(tmp_path):
    """A trace stamped before the points were recorded must not present a
    bare "granted" as if the bounds were merely elsewhere."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    new_id = new_run(r.stdout)
    drop_meta(sdir / "traces" / f"{new_id}.db", "refocus_licence_verified")

    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    assert "licence verified:" not in info.stdout
    assert "does not record WHAT it was granted on" in info.stdout

    listing = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    line = next(ln for ln in listing.stdout.splitlines()
                if ln.startswith(new_id))
    assert "verdict:MATCH(granted,points-not-recorded)" in line


def test_info_names_what_diverged_across_threads(tmp_path):
    """`refocus_thread_divergence` was stamped and read by nothing, so
    `info` said DIVERGED without ever saying what diverged."""
    run_id, sdir = rec(tmp_path, THREAD_BRANCH)
    r = refocus(sdir, run_id, "--focus", "prog:work")
    assert r.returncode == 1, r.stdout + r.stderr

    info = run_cli(["info", new_run(r.stdout)], cwd=tmp_path,
                   sensorium_dir=sdir)
    assert info.returncode == 0, info.stderr
    assert "verdict: DIVERGED" in info.stdout
    assert "diverged on threads:" in info.stdout
    assert "only in the rerun" in info.stdout


# -- REFUSED: a verdict over nothing is not a verdict ------------------------

def test_refocus_refuses_a_verdict_over_two_empty_causal_streams(tmp_path):
    """`../tool.py` resolves outside the run's root, so `_classify` traces
    nothing and the trace is complete, healthy, and empty. Two empty streams
    compare EQUAL, which produced a serene MATCH over zero events -- with
    "there was nothing to compare" printed one line above the granted
    licence -- for two runs that visibly took different branches."""
    work = tmp_path / "work"
    work.mkdir(parents=True)
    (tmp_path / "tool.py").write_text(OUTSIDE_ROOT)
    sdir = tmp_path / "sdir"

    first = run_cli(["run", "--", "../tool.py"], cwd=work, sensorium_dir=sdir)
    assert first.returncode == 0, first.stderr
    assert "FIRST-RUN" in first.stdout
    run_id = new_run(first.stdout)
    assert trace(sdir, run_id).counts() == {}      # nothing was traced at all

    r = refocus(sdir, run_id, "--focus", "tool:main", cwd=work)
    assert "SECOND-RUN" in r.stdout                # a different execution
    # the target itself is digested even though it produced no traced code,
    # so "did the program change" is still answerable for a run like this
    assert "source: unchanged (1 file(s) compared by content" in r.stdout
    assert r.returncode == 2, r.stdout + r.stderr
    assert "verdict: REFUSED" in r.stdout
    assert "nothing to compare" in r.stdout
    assert "licence:" not in r.stdout
    assert "refocus verdict: MATCH" not in r.stdout
    t = trace(sdir, new_run(r.stdout))
    assert t.meta["refocus_verdict"] == "REFUSED"
    assert "refocus_licence" not in t.meta


def test_refocus_states_its_blind_spots_on_a_refused_verdict(tmp_path):
    """"Stated on every verdict" has to include the verdict that says
    nothing, or the sentence in the docstring is not true."""
    work = tmp_path / "work"
    work.mkdir(parents=True)
    (tmp_path / "tool.py").write_text(OUTSIDE_ROOT)
    sdir = tmp_path / "sdir"
    first = run_cli(["run", "--", "../tool.py"], cwd=work, sensorium_dir=sdir)
    run_id = new_run(first.stdout)

    r = refocus(sdir, run_id, "--focus", "tool:main", cwd=work)
    assert r.returncode == 2
    lines = r.stdout.splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if ln.startswith("what sensorium sees at all"))
    blind = "\n".join(ln for ln in lines[start + 1:] if ln.startswith("  - "))
    assert "__repr__" in blind and "fingerprint" in blind


# -- refusals ---------------------------------------------------------------

def test_refocus_refuses_a_stdin_consuming_original(tmp_path):
    run_id, sdir = rec(tmp_path, READS_STDIN, stdin_text="hello\n")
    assert trace(sdir, run_id).meta["stdin_consumed"] is True
    before = dbs(sdir)

    r = refocus(sdir, run_id, "--focus", "prog:main")
    assert r.returncode == 2
    assert "stdin" in r.stderr and "non-refocusable" in r.stderr
    assert "no rerun was attempted" in r.stderr
    assert dbs(sdir) == before, "a refusal must not re-run the program"


def test_refocus_refuses_an_incomplete_original(tmp_path):
    """An incomplete trace never got its finalize pass, so it never recorded
    whether the run consumed stdin: the stdin gate would read the missing
    key as False and wave through exactly the run it exists to stop."""
    sdir = record_killed(tmp_path, SLEEPER)
    [db_name] = dbs(sdir)
    m = trace(sdir, db_name[:-3]).meta
    assert m["incomplete"] is True
    assert "stdin_consumed" not in m
    assert m["argv"] == ["prog.py"]           # boot-time meta did survive

    r = refocus(sdir, db_name[:-3], "--focus", "prog:spin")
    assert r.returncode == 2
    assert "INCOMPLETE" in r.stderr
    assert "stdin" in r.stderr
    assert dbs(sdir) == [db_name]


def test_refocus_refuses_when_the_target_no_longer_resolves(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    (tmp_path / "prog.py").unlink()
    before = dbs(sdir)

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 2
    assert "cannot resolve target" in r.stderr
    assert dbs(sdir) == before


def test_refocus_refuses_when_the_original_cwd_is_gone(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    gone = tmp_path / "deleted-since"
    set_meta(sdir / "traces" / f"{run_id}.db", cwd=str(gone))
    before = dbs(sdir)

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 2
    assert "no longer exists" in r.stderr and str(gone) in r.stderr
    assert dbs(sdir) == before


@pytest.mark.parametrize("kwargs, expected", [
    ({"argv": None, "cwd": "/tmp"}, "records no command to re-run"),
    ({"cwd": None}, "records no working directory to re-run from"),
])
def test_refocus_refuses_a_trace_with_nothing_to_re_run(tmp_path, kwargs,
                                                        expected):
    """Corrupt or hand-built metadata is a refusal, never a traceback: an
    agent parsing this output is worse served by a stack trace than a
    human is."""
    sdir = tmp_path / "sdir"
    synthetic(sdir, "20260101-000000-broken", **kwargs)

    r = refocus(sdir, "20260101-000000-broken", "--focus", "prog:main")
    assert r.returncode == 2
    assert expected in r.stderr
    assert "Traceback" not in r.stderr


def test_refocus_requires_a_focus(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id)
    assert r.returncode == 2
    assert "--focus" in r.stderr


def test_refocus_rejects_an_unknown_run_reference(tmp_path):
    rec(tmp_path, LOOP)
    r = refocus(tmp_path / "sdir", "no-such-run", "--focus", "prog:main")
    assert r.returncode == 2
    assert "error:" in r.stderr and "no trace matches" in r.stderr


# -- the process the rerun happens in ---------------------------------------

def test_refocus_keeps_the_rerun_in_the_same_trace_store(tmp_path):
    """A relative SENSORIUM_DIR must not follow the chdir into the original
    cwd and strand the new trace in a store nobody will look in."""
    run_id, sdir = rec(tmp_path, LOOP)
    runner = tmp_path / "runner"
    runner.mkdir()

    r = refocus(sdir, run_id, "--focus", "prog:accumulate",
                cwd=runner, sensorium_dir="../sdir")
    assert r.returncode == 0, r.stdout + r.stderr
    new_id = new_run(r.stdout)
    assert (sdir / "traces" / f"{new_id}.db").exists()
    assert not (tmp_path.parent / "sdir").exists()


def test_refocus_restores_the_working_directory(tmp_path, monkeypatch,
                                                capsys):
    """`refocus` chdirs into the original run's cwd; an in-process caller
    must get its own directory back afterwards."""
    run_id, sdir = rec(tmp_path, LOOP)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = os.getcwd()
    monkeypatch.chdir(before)         # restore even if the assert below trips

    assert cli.main(["refocus", run_id, "--focus", "prog:accumulate"]) == 0
    assert os.getcwd() == before
    assert "refocus verdict: MATCH" in capsys.readouterr().out


def test_refocus_reports_a_differing_exit_status(tmp_path):
    """The exit code of `refocus` is the VERDICT, never the program's own."""
    run_id, sdir = rec(tmp_path, EXIT_FROM_FILE)
    r = refocus(sdir, run_id, "--focus", "prog:attempt")
    assert "refocus verdict: MATCH" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0
    assert "exit: rerun 1   original 0" in r.stdout


def test_refocus_counts_uncompared_threads_from_the_side_that_had_them(
        tmp_path):
    """The two sides can be asymmetric: this worker starts only on the
    rerun. Counting the uncompared threads from the SMALLER side would
    report none at all, so the reader would never learn that a thread ran
    which nothing compared."""
    run_id, sdir = rec(tmp_path, WORKER_ON_SECOND_RUN)
    assert trace(sdir, run_id).meta["threads_started"] == 0   # none yet

    r = refocus(sdir, run_id, "--focus", "prog:maybe_worker")
    assert r.returncode == 0, r.stdout + r.stderr
    new = trace(sdir, new_run(r.stdout))
    assert new.meta["threads_started"] == 1        # the rerun started one
    assert len(new.fingerprints()) == 1            # and it left no fingerprint

    assert "1 further thread(s) ran no traced code" in r.stdout
    assert "were NOT compared" in r.stdout
    assert "licence: WITHHELD" in r.stdout
