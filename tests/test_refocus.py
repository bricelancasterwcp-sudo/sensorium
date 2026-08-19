"""`refocus`: re-run a recording with deeper capture, and say -- honestly --
whether the rerun was the same execution.

Every rerun test drives the real CLI in a subprocess against real recorded
traces, because the behaviour under test IS the re-running: no synthetic
trace can show whether `refocus` chdir'd to the right place, inherited the
right filters, or actually captured anything the original lacked. Even the
INCOMPLETE original is real -- the recorder is SIGKILLed mid-run rather than
hand-built, so the test also proves which metadata survives that death.

The only synthetic pieces are the two shapes the recorder cannot be made to
produce on demand (see `diff_cmd`): a trace with dropped late writes, and a
legacy trace with no recorded main thread. Those are fed to the reporting
seam directly, because a branch no test can reach is a branch nobody has
checked -- and REFUSED is the branch that must never collapse into MATCH.
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from sensorium import cli
from sensorium.query import refocus_cmd
from sensorium.query.diff_cmd import compare
from sensorium.store import db
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script, run_cli

# Deterministic. `accumulate`'s loop calls nothing, so editing its input list
# changes the printed value but NOT the causal stream -- which is exactly the
# shape the changed-source tests need.
LOOP = """
def helper(n):
    return n + 1

def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    print("sum:", accumulate([5, 10, 20]), helper(1))

if __name__ == "__main__":
    main()
"""

# Control flow decided by state OUTSIDE the process, so the rerun genuinely
# takes the other branch -- and does so deterministically, unlike a coin
# flip, which would make a DIVERGED test flaky in the direction of a false
# pass.
COUNTER = """
import pathlib

def bump():
    p = pathlib.Path("counter.txt")
    n = int(p.read_text()) if p.exists() else 0
    p.write_text(str(n + 1))
    return n

def first():
    return "first"

def again():
    return "again"

def main():
    print(first() if bump() == 0 else again())

if __name__ == "__main__":
    main()
"""

# Same causal shape both times; only the value that decides the exit status
# differs. A MATCH here is correct and yet the two runs ended differently.
EXIT_FROM_FILE = """
import pathlib
import sys

def attempt():
    p = pathlib.Path("n.txt")
    n = int(p.read_text()) if p.exists() else 0
    p.write_text(str(n + 1))
    return n

def main():
    sys.exit(attempt())

if __name__ == "__main__":
    main()
"""

READS_STDIN = """
def main():
    line = input()
    print("got", line)

if __name__ == "__main__":
    main()
"""

# Writes a marker, then blocks: lets a test kill the recorder at a known
# point and get a genuinely incomplete trace.
SLEEPER = """
import pathlib
import time

def spin():
    time.sleep(60)

def main():
    pathlib.Path("ready").write_text("1")
    spin()

if __name__ == "__main__":
    main()
"""

TWO_FILES = """
import lib

def main():
    print("n:", lib.compute(3))

if __name__ == "__main__":
    main()
"""

LIB = """
def helper(x):
    return x * 2

def compute(x):
    return helper(x) + 1
"""


# -- fixtures ---------------------------------------------------------------

def _rec(tmp_path, src, extra=(), stdin_text=None):
    run_id, _trace, r = record_script(tmp_path, src, extra=extra,
                                      stdin_text=stdin_text)
    assert run_id, r.stderr + r.stdout
    return run_id, tmp_path / "sdir"


def _rec_in_git(tmp_path, src):
    """Record inside a real git repo with `prog.py` committed.

    Committing matters: an untracked file shows as `?? prog.py` before and
    after an edit, so `git_dirty_hash` would not move and the changed-tree
    warning this fixture exists to exercise would never fire.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "prog.py").write_text(src)
    for cmd in (["init", "-q", "-b", "main"],
                ["add", "prog.py"],
                ["-c", "user.email=t@example.invalid", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", "p"]):
        subprocess.run(["git", *cmd], cwd=tmp_path, check=True,
                       capture_output=True)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", "--", "prog.py"], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr
    run_id = re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)
    assert Trace.open(sdir / "traces" / f"{run_id}.db").meta["git_sha"]
    return run_id, sdir


def _record_killed(tmp_path, src):
    """A genuinely incomplete recording: SIGKILL the recorder mid-run."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "prog.py").write_text(src)
    sdir = tmp_path / "sdir"
    proc = subprocess.Popen(
        [sys.executable, "-m", "sensorium", "run", "--", "prog.py"],
        cwd=tmp_path, env=dict(os.environ, SENSORIUM_DIR=str(sdir)),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = tmp_path / "ready"
    deadline = time.monotonic() + 60
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert ready.exists(), "the recorded program never reached its marker"
    proc.kill()
    proc.wait(timeout=60)
    return sdir


def _refocus(sdir, run_id, *extra, cwd=None, sensorium_dir=None):
    return run_cli(["refocus", run_id, *extra], cwd=cwd or sdir.parent,
                   sensorium_dir=sensorium_dir or sdir)


def _new_run(out):
    m = re.search(r"^run: (\S+)$", out, re.M)
    assert m, f"no new run id in output:\n{out}"
    return m.group(1)


def _trace(sdir, run_id):
    return Trace.open(sdir / "traces" / f"{run_id}.db")


def _dbs(sdir):
    return sorted(p.name for p in (sdir / "traces").glob("*.db"))


def _set_meta(path, **kv):
    conn = db.open_trace(path)
    for k, v in kv.items():
        db.set_meta(conn, k, v)
    conn.commit()
    conn.close()


def _synthetic(sdir, run_id, *, argv=("prog.py",), cwd=None, late_writes=0,
               main_thread_ident=1):
    """A hand-built trace, for shapes the recorder cannot produce on demand:
    dropped late writes, a legacy trace with no recorded main thread, and
    corrupt metadata that must be refused rather than crashed on."""
    path = Path(sdir) / "traces" / f"{run_id}.db"
    w = TraceWriter(path)
    w.set_meta("run_id", run_id)
    if argv is not None:
        w.set_meta("argv", list(argv))
    if cwd is not None:
        w.set_meta("cwd", str(cwd))
    w.set_meta("incomplete", False)
    w.set_meta("late_writes", late_writes)
    if main_thread_ident is not None:
        w.set_meta("main_thread_ident", main_thread_ident)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    w.close()
    return path


# -- MATCH ------------------------------------------------------------------

def test_refocus_match_captures_line_state_the_original_lacked(tmp_path):
    """A MATCH that captured nothing new is a useless success."""
    run_id, sdir = _rec(tmp_path, LOOP)
    assert _trace(sdir, run_id).events(kind="LINE") == []      # precondition

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sum: 35 2" in r.stdout            # the program really ran again
    assert "verdict: MATCH" in r.stdout
    assert "verified same execution on the recorded main thread" in r.stdout
    assert ("licence: answers from this trace are answers about the "
            "original run") in r.stdout

    t = _trace(sdir, _new_run(r.stdout))
    assert t.meta["refocus_of"] == run_id
    assert t.meta["refocus_verdict"] == "MATCH"
    lines = t.events(kind="LINE")
    assert lines, "the deeper capture landed nothing"
    assert {t.code(e.code_id).qualname for e in lines} == {"accumulate"}
    assert "exit: rerun 0   original 0" in r.stdout
    assert "exit status differs" not in r.stdout


def test_refocus_match_states_what_it_does_not_license(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    caveat = next(ln for ln in r.stdout.splitlines()
                  if ln.startswith("NOT verified"))
    for claim in ("values", "timing", "per-line state", "thread"):
        assert claim in caveat, caveat


def test_refocus_adds_to_the_original_focus_instead_of_replacing_it(tmp_path):
    """A refocus only ever goes deeper -- never shallower than the trace it
    is supposed to explain."""
    run_id, sdir = _rec(tmp_path, LOOP, extra=["--focus", "prog:helper"])

    added = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert added.returncode == 0, added.stdout + added.stderr
    t = _trace(sdir, _new_run(added.stdout))
    assert t.meta["focus"] == ["prog:helper", "prog:accumulate"]
    assert {t.code(e.code_id).qualname for e in t.events(kind="LINE")} == {
        "helper", "accumulate"}

    # asking again for what the original already focused adds nothing twice
    same = _refocus(sdir, run_id, "--focus", "prog:helper")
    assert same.returncode == 0, same.stdout + same.stderr
    assert _trace(sdir, _new_run(same.stdout)).meta["focus"] == ["prog:helper"]


@pytest.mark.parametrize("filters", [["--exclude", "lib.py"],
                                     ["--include", "prog.py"]])
def test_refocus_inherits_the_original_include_exclude_filters(tmp_path,
                                                               filters):
    """Focus and window only gate LINE events, but include/exclude gate the
    CAUSAL stream itself: dropping either one would change what is compared
    and make every verdict meaningless."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib.py").write_text(LIB)
    run_id, sdir = _rec(tmp_path, TWO_FILES, extra=filters)
    orig = _trace(sdir, run_id)
    assert not any(c.qualname == "compute" for c in orig.codes())

    r = _refocus(sdir, run_id, "--focus", "prog:main")
    assert r.returncode == 0, r.stdout + r.stderr
    new = _trace(sdir, _new_run(r.stdout))
    assert new.meta["include"] == orig.meta["include"]
    assert new.meta["exclude"] == orig.meta["exclude"]
    assert not any(c.qualname == "compute" for c in new.codes())
    assert "verdict: MATCH" in r.stdout


def test_refocus_inherits_the_window_and_lets_it_be_overridden(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP, extra=["--focus", "prog:accumulate",
                                               "--window", "main"])
    kept = _refocus(sdir, run_id, "--focus", "prog:helper")
    assert kept.returncode == 0, kept.stdout + kept.stderr
    assert "window: main" in kept.stdout
    assert _trace(sdir, _new_run(kept.stdout)).meta["window"] == "main"

    over = _refocus(sdir, run_id, "--focus", "prog:helper",
                    "--window", "accumulate")
    assert over.returncode == 0, over.stdout + over.stderr
    assert _trace(sdir, _new_run(over.stdout)).meta["window"] == "accumulate"


def test_refocus_reports_a_differing_exit_status_under_a_match(tmp_path):
    """The exit code of `refocus` is the VERDICT, never the program's own --
    and a MATCH on shape does not mean the two runs ended the same way."""
    run_id, sdir = _rec(tmp_path, EXIT_FROM_FILE)
    r = _refocus(sdir, run_id, "--focus", "prog:attempt")
    assert "verdict: MATCH" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0
    assert "exit: rerun 1   original 0" in r.stdout
    assert "exit status differs" in r.stdout


def test_info_reports_a_verified_refocus_as_match(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    new_id = _new_run(r.stdout)
    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    assert info.returncode == 0, info.stderr
    assert f"refocus-of: {run_id}  verdict: MATCH" in info.stdout


# -- DIVERGED ---------------------------------------------------------------

def test_refocus_diverges_when_state_outside_the_process_changed(tmp_path):
    run_id, sdir = _rec(tmp_path, COUNTER)
    assert (tmp_path / "counter.txt").read_text() == "1"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    r = _refocus(sdir, run_id, "--focus", "prog:bump", cwd=elsewhere)

    # establish that the executions really did differ before asserting on
    # anything the tool says about them
    assert (tmp_path / "counter.txt").read_text() == "2"
    assert not (elsewhere / "counter.txt").exists()   # reran in the orig cwd
    assert "\nagain\n" in r.stdout                    # the other branch ran

    assert r.returncode == 1, r.stdout + r.stderr
    assert "verdict: DIVERGED" in r.stdout
    new_id = _new_run(r.stdout)
    # A is the original and B is the rerun -- swapping them would point the
    # reader's drill-down commands at the wrong trace
    assert f"A {run_id}:" in r.stdout and f"B {new_id}:" in r.stdout
    t = _trace(sdir, new_id)
    assert t.meta["refocus_verdict"] == "DIVERGED"
    assert t.meta["refocus_diverge_index"] is not None
    assert "first" in t.meta["refocus_diverge_a"]
    assert "again" in t.meta["refocus_diverge_b"]


def test_a_diverged_trace_cannot_pass_itself_off_as_verified(tmp_path):
    run_id, sdir = _rec(tmp_path, COUNTER)
    r = _refocus(sdir, run_id, "--focus", "prog:bump")
    assert r.returncode == 1, r.stdout + r.stderr
    new_id = _new_run(r.stdout)
    info = run_cli(["info", new_id], cwd=tmp_path, sensorium_dir=sdir)
    assert info.returncode == 0, info.stderr
    assert f"refocus-of: {run_id}" in info.stdout
    assert "verdict: DIVERGED" in info.stdout
    assert "verdict: MATCH" not in info.stdout


# -- refusals ---------------------------------------------------------------

def test_refocus_refuses_a_stdin_consuming_original(tmp_path):
    run_id, sdir = _rec(tmp_path, READS_STDIN, stdin_text="hello\n")
    assert _trace(sdir, run_id).meta["stdin_consumed"] is True
    before = _dbs(sdir)

    r = _refocus(sdir, run_id, "--focus", "prog:main")
    assert r.returncode == 2
    assert "stdin" in r.stderr and "non-refocusable" in r.stderr
    assert "no rerun was attempted" in r.stderr
    assert _dbs(sdir) == before, "a refusal must not re-run the program"


def test_refocus_refuses_an_incomplete_original(tmp_path):
    """An incomplete trace never got its finalize pass, so it never recorded
    whether the run consumed stdin: the stdin gate would read the missing
    key as False and wave through exactly the run it exists to stop."""
    sdir = _record_killed(tmp_path, SLEEPER)
    [db_name] = _dbs(sdir)
    m = _trace(sdir, db_name[:-3]).meta
    assert m["incomplete"] is True
    assert "stdin_consumed" not in m
    assert m["argv"] == ["prog.py"]          # boot-time meta did survive

    r = _refocus(sdir, db_name[:-3], "--focus", "prog:spin")
    assert r.returncode == 2
    assert "INCOMPLETE" in r.stderr
    assert "stdin" in r.stderr
    assert _dbs(sdir) == [db_name]


def test_refocus_refuses_when_the_target_no_longer_resolves(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    (tmp_path / "prog.py").unlink()
    before = _dbs(sdir)

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 2
    assert "cannot resolve target" in r.stderr
    assert _dbs(sdir) == before


def test_refocus_refuses_when_the_original_cwd_is_gone(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    gone = tmp_path / "deleted-since"
    _set_meta(sdir / "traces" / f"{run_id}.db", cwd=str(gone))
    before = _dbs(sdir)

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 2
    assert "no longer exists" in r.stderr and str(gone) in r.stderr
    assert _dbs(sdir) == before


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
    _synthetic(sdir, "20260101-000000-broken", **kwargs)

    r = _refocus(sdir, "20260101-000000-broken", "--focus", "prog:main")
    assert r.returncode == 2
    assert expected in r.stderr
    assert "Traceback" not in r.stderr


def test_refocus_requires_a_focus(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    r = _refocus(sdir, run_id)
    assert r.returncode == 2
    assert "--focus" in r.stderr


def test_refocus_rejects_an_unknown_run_reference(tmp_path):
    _rec(tmp_path, LOOP)
    r = _refocus(tmp_path / "sdir", "no-such-run", "--focus", "prog:main")
    assert r.returncode == 2
    assert "error:" in r.stderr and "no trace matches" in r.stderr


# -- the changed working tree: a warning, never a refusal -------------------

def test_refocus_warns_about_a_changed_tree_and_still_reports_match(tmp_path):
    """The fingerprint speaks to execution PATH, not to file bytes. When the
    edit leaves the causal stream untouched, MATCH is the honest verdict --
    and the changed tree is exactly why it must not be read as "same run"."""
    run_id, sdir = _rec_in_git(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(LOOP.replace("[5, 10, 20]", "[1, 2]"))

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert "sum: 3 2" in r.stdout             # different code really ran
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: CHANGED since the original run" in r.stdout
    assert "working tree CHANGED between the two runs" in r.stdout
    assert "verdict: MATCH" in r.stdout
    assert "values may differ" in r.stdout
    # the claim a clean MATCH earns and a changed tree does not
    assert "answers about the original run" not in r.stdout


def test_refocus_warns_about_a_changed_tree_on_a_diverging_verdict(tmp_path):
    run_id, sdir = _rec_in_git(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(
        LOOP.replace("total = total + op", "total = helper(total + op) - 1"))

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "source: CHANGED since the original run" in r.stdout
    assert "working tree CHANGED between the two runs" in r.stdout
    assert "verdict: DIVERGED" in r.stdout


def test_refocus_notices_a_new_commit_even_when_the_tree_is_clean(tmp_path):
    """Committing the edit puts `git status --porcelain` back exactly where
    it was, so only the HEAD sha moves. Reading just the dirty hash would
    call this tree unchanged."""
    run_id, sdir = _rec_in_git(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(LOOP.replace("[5, 10, 20]", "[1, 2]"))
    subprocess.run(["git", "-c", "user.email=t@example.invalid",
                    "-c", "user.name=t", "-c", "commit.gpgsign=false",
                    "commit", "-q", "-am", "edit"],
                   cwd=tmp_path, check=True, capture_output=True)

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: CHANGED since the original run" in r.stdout
    assert "values may differ" in r.stdout


def test_refocus_reports_an_unchanged_tree_as_unchanged(tmp_path):
    run_id, sdir = _rec_in_git(tmp_path, LOOP)
    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: unchanged" in r.stdout
    assert "source: CHANGED" not in r.stdout
    assert "working tree CHANGED" not in r.stdout


def test_refocus_says_the_source_state_is_unverifiable_without_git(tmp_path):
    """No repository means sensorium cannot tell whether the code moved --
    which is a fact about the check, not evidence that nothing changed."""
    run_id, sdir = _rec(tmp_path, LOOP)
    r = _refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: unverifiable" in r.stdout
    assert "no git repository" in r.stdout
    assert "source: CHANGED" not in r.stdout


# -- the trace store must not follow the chdir ------------------------------

def test_refocus_keeps_the_rerun_in_the_same_trace_store(tmp_path):
    """A relative SENSORIUM_DIR must not follow the chdir into the original
    cwd and strand the new trace in a store nobody will look in."""
    run_id, sdir = _rec(tmp_path, LOOP)
    runner = tmp_path / "runner"
    runner.mkdir()

    r = _refocus(sdir, run_id, "--focus", "prog:accumulate",
                 cwd=runner, sensorium_dir="../sdir")
    assert r.returncode == 0, r.stdout + r.stderr
    new_id = _new_run(r.stdout)
    assert (sdir / "traces" / f"{new_id}.db").exists()
    assert not (tmp_path.parent / "sdir").exists()


# -- REFUSED, and the weaker MATCH: the reporting seam ----------------------

def test_report_refuses_a_verdict_when_the_new_trace_is_lossy(tmp_path,
                                                              capsys):
    """REFUSED is neither MATCH nor DIVERGED and must never collapse into
    either. `late_writes > 0` is one shape that produces it, and the
    recorder cannot be made to record a non-zero count on demand (see
    diff_cmd), so the reporting seam is exercised directly."""
    sdir = tmp_path / "sdir"
    a = _synthetic(sdir, "20260101-000000-origaa")
    b = _synthetic(sdir, "20260101-000000-newbbb", late_writes=3)
    ta, tb = Trace.open(a), Trace.open(b)
    res = compare(ta, tb)
    assert res["verdict"] == "REFUSED"                      # precondition

    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem, source_changed=False)
    out = capsys.readouterr().out
    assert rc == 2
    assert "REFUSED" in out and "UNVERIFIED" in out
    assert "verdict: MATCH" not in out and "verdict: DIVERGED" not in out
    assert "verified same execution" not in out


def test_report_does_not_claim_the_main_thread_when_it_is_inferred(tmp_path,
                                                                    capsys):
    """A MATCH verified against an INFERRED thread is weaker than one
    verified against the recorded main thread, and must say so rather than
    assert both cases equally."""
    sdir = tmp_path / "sdir"
    a = _synthetic(sdir, "20260101-000000-legacya", main_thread_ident=None)
    b = _synthetic(sdir, "20260101-000000-legacyb", main_thread_ident=None)
    ta, tb = Trace.open(a), Trace.open(b)
    assert ta.main_thread_basis() == "inferred"             # precondition
    res = compare(ta, tb)
    assert res["verdict"] == "MATCH"

    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem, source_changed=False)
    out = capsys.readouterr().out
    assert rc == 0
    assert "verified same execution" in out
    assert "INFERRED rather than recorded" in out
    assert "verified same execution on the recorded main thread" not in out


def test_report_marks_a_match_against_changed_source(tmp_path, capsys):
    sdir = tmp_path / "sdir"
    a = _synthetic(sdir, "20260101-000000-srcaaa")
    b = _synthetic(sdir, "20260101-000000-srcbbb")
    ta, tb = Trace.open(a), Trace.open(b)
    res = compare(ta, tb)
    assert res["verdict"] == "MATCH"

    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem, source_changed=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert "working tree CHANGED between the two runs" in out
    assert "values may differ" in out
    assert "answers about the original run" not in out


def test_stamp_records_why_a_verdict_was_refused(tmp_path):
    """A REFUSED rerun must carry its reason in the trace, not only in the
    terminal it was printed to."""
    sdir = tmp_path / "sdir"
    a = _synthetic(sdir, "20260101-000000-stampa")
    b = _synthetic(sdir, "20260101-000000-stampb", late_writes=2)
    res = compare(Trace.open(a), Trace.open(b))
    assert res["verdict"] == "REFUSED"

    refocus_cmd._stamp(b, res)
    m = Trace.open(b).meta
    assert m["refocus_verdict"] == "REFUSED"
    assert any("dropped >=2 trace write(s)" in reason
               for reason in m["refocus_refused_reasons"])


def test_refocus_restores_the_working_directory(tmp_path, monkeypatch,
                                                capsys):
    """`refocus` chdirs into the original run's cwd; an in-process caller
    must get its own directory back afterwards."""
    run_id, sdir = _rec(tmp_path, LOOP)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = os.getcwd()
    monkeypatch.chdir(before)          # restore even if the assert below trips

    assert cli.main(["refocus", run_id, "--focus", "prog:accumulate"]) == 0
    assert os.getcwd() == before
    assert "verdict: MATCH" in capsys.readouterr().out
