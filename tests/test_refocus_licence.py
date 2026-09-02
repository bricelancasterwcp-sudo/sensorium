"""What a `refocus` MATCH is allowed to claim.

A first version of this command printed one verdict and one confident
sentence, and four separate reruns earned "verdict: MATCH" plus the full
"answers about the original run" licence while being demonstrably about a
different execution: one read its input from an environment variable that was
gone the second time, one had a worker thread take the other branch, one was
perturbed by the recorder itself, and one traced nothing at all and compared
two empty streams. A fifth certified a rerun of rewritten code as
`source: unchanged`, because the check behind that phrase hashed a list of
file PATHS rather than their contents. Each is a fixture here.

The rule those failures produced, and that this file pins:

* VERDICT is about causal shape, across every recorded thread -- and there
  is no verdict at all when there was nothing to compare.
* LICENCE is withheld on ANY signal sensorium can check and finds -- and on
  any check it could not run at all, because the licence claims every check
  agreed. "Could not run" and "ran and found nothing" are the two states the
  earlier versions kept confusing.
* BLIND SPOTS are stated on every verdict -- MATCH, DIVERGED and REFUSED --
  because they can never be checked.

The seam tests at the bottom drive `report()` directly, for verdicts and
trace shapes the recorder cannot be made to produce on demand (see
`diff_cmd`).
"""
import sys

import pytest

from sensorium.query import refocus_cmd
from sensorium.query.diff_cmd import compare
from sensorium.record.boot import git_info
from sensorium.store.reader import Trace
from tests.helpers import run_cli
from tests.refocus_programs import (COUNTER, ENV_LIMIT, EXIT_FROM_FILE,
                                    JOINED_UNTRACED_WORKER, LIB, LOOP,
                                    MULTIPROCESSING_CHILD, READS_COLUMNS,
                                    SHELLS_OUT, SIDE_EFFECT_REPR, SPAWNS,
                                    TWO_FILES, TWO_WORKERS, UNTRACED_WORKER,
                                    drop_meta, new_run, rec, rec_in_git,
                                    recorded_output, refocus, set_meta,
                                    synthetic, trace)


# -- the licence is granted only when every check ran and agreed ------------

def test_refocus_grants_the_licence_when_every_check_passes(tmp_path):
    """The positive control. A licence that is never granted teaches people
    to ignore it, so the one path that earns it has to be pinned: unchanged
    source contents, an unchanged environment, one thread, identical output,
    identical exit status, no subprocess, and a recorded (not inferred) main
    thread. Deliberately NOT inside a git repo -- the source check reads file
    contents, so a repository is not what makes the claim checkable."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: unchanged" in r.stdout
    assert "env: unchanged" in r.stdout
    assert "refocus verdict: MATCH" in r.stdout
    # the licence states positively and boundedly what it rests on, and
    # never that "every signal sensorium can check agrees" -- a sentence
    # that invites the check-list to be read as complete
    assert f"licence: verified against {run_id} on exactly these points, " \
        "and no others:" in r.stdout
    assert "  - identical call shape across 1 compared fingerprint(s)" \
        in r.stdout
    assert "  - 1 source file(s) unchanged by content" in r.stdout
    assert ("environment variable(s) compared and unchanged in the "
            "environment the rerun executed under") in r.stdout
    if sys.version_info >= (3, 14):
        assert ("  - no child process witnessed, by any mechanism sensorium "
                "watches") in r.stdout
    else:
        # < 3.14 raises no audit event for a multiprocessing spawn, so the
        # pair cannot vouch that none ran: the line is omitted, and the
        # licence still rests on the checks that DID run
        assert "no child process witnessed" not in r.stdout
    # the thread fact carries the same hedge as the child fact: what was
    # verified is "none through Python's own threading", not "none at all"
    assert ("no thread started besides the main one through Python's own "
            "threading/_thread") in r.stdout
    assert "licence: WITHHELD" not in r.stdout
    assert "every signal sensorium can check agrees" not in r.stdout
    # a single-threaded run has no uncompared threads, and must not claim
    # otherwise: the tail is a finding, not decoration
    assert "further thread(s) ran no traced code" not in r.stdout
    assert "threads: 1 recorded fingerprint(s) compared, all matching" \
        in r.stdout.replace(";", "\n")
    # ...and the blind spots are still stated, licence or no licence
    assert "what sensorium sees at all" in r.stdout


def test_refocus_withholds_the_licence_when_it_cannot_check_the_source(
        tmp_path):
    """A trace recorded before source digests existed cannot be compared
    against. That is a fact about the CHECK, not evidence that nothing
    changed, so it withholds: the licence claims every check agreed, and
    here one of them never ran."""
    run_id, sdir = rec(tmp_path, LOOP)
    drop_meta(sdir / "traces" / f"{run_id}.db", "source_hashes")

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: unverifiable" in r.stdout
    assert "source: CHANGED" not in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "the source could not be checked at all" in r.stdout


# -- false MATCH 1: the environment -----------------------------------------

def test_refocus_withholds_the_licence_when_the_environment_differs(
        tmp_path, monkeypatch):
    """`REFOCUS_TEST_LIMIT=10` at record time, absent at refocus time:
    different input, different output, identical call shape. MATCH is the
    right verdict about shape; the licence must not follow it."""
    monkeypatch.setenv("REFOCUS_TEST_LIMIT", "10")
    run_id, sdir = rec(tmp_path, ENV_LIMIT)
    assert "over: 1" in recorded_output(sdir, run_id)
    monkeypatch.delenv("REFOCUS_TEST_LIMIT")

    r = refocus(sdir, run_id, "--focus", "prog:over")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "\nover: 2\n" in r.stdout            # the rerun got other input
    assert "refocus verdict: MATCH" in r.stdout
    assert "env: CHANGED since the original run" in r.stdout
    assert "REFOCUS_TEST_LIMIT" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "environment variable(s) differ" in r.stdout
    assert "answers about the original run" not in r.stdout


def test_refocus_never_prints_environment_values(tmp_path, monkeypatch):
    """Environments carry secrets: the diff names variables, never values."""
    monkeypatch.setenv("REFOCUS_TEST_LIMIT", "10")
    run_id, sdir = rec(tmp_path, ENV_LIMIT)
    monkeypatch.setenv("REFOCUS_TEST_LIMIT", "999333111")

    r = refocus(sdir, run_id, "--focus", "prog:over")
    assert "REFOCUS_TEST_LIMIT" in r.stdout
    assert "999333111" not in r.stdout
    assert "999333111" not in r.stderr


def test_refocus_withholds_the_licence_when_it_cannot_check_the_env(tmp_path):
    """A trace recorded before `env` was stored cannot be compared against.
    Like the missing git repository, that is a fact about the check, and the
    licence claims every check agreed."""
    run_id, sdir = rec(tmp_path, LOOP)
    drop_meta(sdir / "traces" / f"{run_id}.db", "env")

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "env: unverifiable" in r.stdout
    assert "the environment could not be checked at all" in r.stdout
    assert "licence: WITHHELD" in r.stdout


def test_refocus_does_not_report_its_own_trace_store_rewrite(tmp_path):
    """`_pin_trace_store` rewrites a relative SENSORIUM_DIR to the absolute
    path of the SAME directory, so the rerun's store survives the chdir. The
    environment diff compares strings, so taking its snapshot after that
    rewrite would report the tool's own bookkeeping as the world changing
    under the program."""
    work = tmp_path / "work"
    work.mkdir(parents=True)
    (work / "prog.py").write_text(LOOP)
    first = run_cli(["run", "--", "prog.py"], cwd=work,
                    sensorium_dir="../sdir")
    assert first.returncode == 0, first.stderr
    run_id = new_run(first.stdout)
    sdir = tmp_path / "sdir"
    assert (sdir / "traces" / f"{run_id}.db").exists()

    r = refocus(sdir, run_id, "--focus", "prog:accumulate", cwd=work,
                sensorium_dir="../sdir")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "env: unchanged" in r.stdout
    # SENSORIUM_DIR is excluded from the comparison rather than reported as
    # a change the world made -- but it is NAMED, because a program that
    # reads it goes unchecked and the reader has to be able to see that
    assert "not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _" in r.stdout


def test_refocus_ignores_volatile_shell_variables(tmp_path, monkeypatch):
    """`_` and friends change between any two consecutive shell commands. If
    they counted, the env check would fire on every real invocation and mean
    nothing -- the denylist is what keeps a CHANGED verdict informative."""
    monkeypatch.setenv("_", "/usr/bin/something")
    monkeypatch.setenv("SHLVL", "1")
    run_id, sdir = rec(tmp_path, LOOP)
    monkeypatch.setenv("_", "/usr/bin/something-else")
    monkeypatch.setenv("SHLVL", "9")

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "env: unchanged" in r.stdout
    assert "env: CHANGED" not in r.stdout


# -- false MATCH 2: the instrument ------------------------------------------

def test_refocus_reports_output_the_recorder_itself_changed(tmp_path):
    """The deeper capture calls the program's own `__repr__`, which counts
    its calls. Those frames are `in_hook`-suppressed, so the fingerprint
    cannot see the perturbation at all -- the captured output is the only
    cross-check there is, and the blind spot must be stated outright."""
    run_id, sdir = rec(tmp_path, SIDE_EFFECT_REPR)
    assert "reprs: 0" in recorded_output(sdir, run_id)

    r = refocus(sdir, run_id, "--focus", "prog:step")
    reruns = recorded_output(sdir, new_run(r.stdout))
    assert "reprs: 0" not in reruns, "the instrument did not perturb the run"

    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout      # the shape did match
    assert "licence: WITHHELD" in r.stdout
    assert "the program's own captured stdout differs" in r.stdout
    assert "'reprs: 0' -> " in r.stdout
    assert "answers about the original run" not in r.stdout
    assert "leaves no mark on the fingerprint" in r.stdout


def _blind_spot_block(out: str) -> str:
    lines = out.splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if ln.startswith("what sensorium sees at all"))
    body = [ln for ln in lines[start + 1:] if ln.startswith("  - ")]
    assert body, out
    return "\n".join(body)


def test_refocus_states_its_blind_spots_on_every_verdict(tmp_path):
    """A limitation mentioned only when convenient is not a limitation."""
    run_id, sdir = rec(tmp_path, LOOP)
    match = refocus(sdir, run_id, "--focus", "prog:accumulate")
    counter, csdir = rec(tmp_path / "c", COUNTER)
    diverged = refocus(csdir, counter, "--focus", "prog:bump")
    assert match.returncode == 0 and diverged.returncode == 1

    for out in (match.stdout, diverged.stdout):
        blind = _blind_spot_block(out)
        for claim in ("values", "timing", "__repr__", "fingerprint"):
            assert claim in blind, blind


def test_blind_spots_name_task_ordering(tmp_path):
    """The interleaving between asyncio tasks is now deliberately NOT
    compared -- that is what lets an order flip come back MATCH -- so it is
    a blind spot, and a blind spot the tool relies on has to be stated on
    every verdict rather than mentioned where it happens to apply."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:helper")
    assert ("the order threads ran in relative to one another, and the "
            "order asyncio tasks interleaved in: recorded, never compared"
            ) in r.stdout


def test_blind_spots_name_the_gaps_the_source_check_cannot_reach(tmp_path):
    """The four `source_hashes` gaps were documented in the source and
    invisible on screen, and three attacks landed inside them for a full
    licence each: a config file the check does not hash, a module outside
    the run's root, and a direct os.posix_spawn. A limitation a user cannot
    read is a limitation they will walk into."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr

    blind = _blind_spot_block(r.stdout)
    # CATEGORICAL, not a list of mechanisms: the header bounds it by what
    # the instrument is, so it stays true when the next mechanism appears
    header = next(ln for ln in r.stdout.splitlines()
                  if ln.startswith("what sensorium sees at all"))
    assert "Python code that this run traced" in header
    assert "under the run's own root" in header
    assert "Nothing else" in header
    assert "any child process, by any mechanism" in blind
    assert "an empty list is NOT evidence that none ran" in blind
    assert "any file the program read or wrote" in blind
    assert "any code outside the run's root" in blind
    assert "any environment variable this run did not compare" in blind
    assert "the clock, the network" in blind
    assert "threading/_thread" in blind
    # ...and the source line itself does not read as a blanket all-clear
    assert ("data files, untraced code and installed dependencies are NOT "
            "covered") in r.stdout
    # The block whose whole purpose is precision must not contain a FALSE
    # sentence. "nothing outside the environment is compared at all" stood
    # here, twelve lines under `source: unchanged (1 file(s) compared by
    # content)` -- and stdout, stderr and exit status are compared too.
    assert "nothing outside the environment" not in r.stdout
    assert "source: unchanged (1 file(s) compared by content" in r.stdout


def test_refocus_admits_a_divergence_may_be_its_own_doing(tmp_path):
    """The observer effect cuts both ways: deeper capture can push a program
    onto another path, and the fingerprint cannot tell that apart from the
    program genuinely diverging."""
    run_id, sdir = rec(tmp_path, COUNTER)
    r = refocus(sdir, run_id, "--focus", "prog:bump")
    assert r.returncode == 1, r.stdout + r.stderr
    assert ("a divergence can also be caused by the deeper capture itself"
            in r.stdout)


# -- what a whole-run MATCH still does not cover ----------------------------

def test_refocus_withholds_the_licence_when_threads_were_involved(tmp_path):
    """Every thread's own call shape matched -- that is what makes this a
    MATCH rather than a DIVERGED. What was never compared is the ORDER the
    threads ran in relative to each other, and interleaving is what most
    concurrency bugs are made of."""
    run_id, sdir = rec(tmp_path, TWO_WORKERS)
    assert len(trace(sdir, run_id).fingerprints()) == 3     # main + 2 workers

    r = refocus(sdir, run_id, "--focus", "prog:tally")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "threads: 3 recorded fingerprint(s) compared, all matching" \
        in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "3 threads were recorded" in r.stdout
    assert "the INTERLEAVING between them was never compared" in r.stdout
    assert "answers about the original run" not in r.stdout


@pytest.mark.parametrize("src, focus", [(SPAWNS, "prog:spawn"),
                                        (SHELLS_OUT, "prog:shell")])
def test_refocus_withholds_the_licence_when_a_subprocess_ran(tmp_path, src,
                                                             focus):
    """A child process is observed and never witnessed: nothing in either
    trace says what it did, so a MATCH cannot speak for the run.

    `os.system` is the second case for a reason -- it starts a shell without
    ever touching `subprocess`, so a hook watching only `subprocess.Popen`
    recorded `children == []` and granted the licence."""
    run_id, sdir = rec(tmp_path, src)
    assert trace(sdir, run_id).meta["children"]             # precondition

    r = refocus(sdir, run_id, "--focus", focus)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "started at least one child process" in r.stdout
    assert "sensorium does not witness what any child did" in r.stdout
    assert "answers about the original run" not in r.stdout


def test_refocus_withholds_when_an_untraced_worker_ran_and_finished(tmp_path):
    """The fifth false licence. This worker's body is entirely stdlib, so it
    leaves NO fingerprint row, and it is joined before the run ends, so it is
    gone from `live_threads` too -- invisible on both counts while doing file
    I/O that differs between the runs. Counting thread CREATION through the
    audit hook is the only sound signal, and it is what catches this."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "payload.txt").write_text("first payload")
    run_id, sdir = rec(tmp_path, JOINED_UNTRACED_WORKER)
    t = trace(sdir, run_id)
    assert len(t.fingerprints()) == 1        # the trap: looks single-threaded
    assert t.meta["live_threads"] == []      # ...and nothing was left running
    assert t.meta["threads_started"] == 1    # but a thread was created

    # the worker copies different bytes the second time
    (tmp_path / "payload.txt").write_text("a completely different payload")
    r = refocus(sdir, run_id, "--focus", "prog:deliver")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "delivered.txt").read_text() == (
        "a completely different payload")

    assert "refocus verdict: MATCH" in r.stdout
    # the sentence that used to assert completeness it could not have
    assert "all 1 recorded thread(s) matched" not in r.stdout
    assert "1 recorded fingerprint(s) compared, all matching" in r.stdout
    assert "further thread(s) ran no traced code" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "started 1 thread(s) besides the main one" in r.stdout
    assert "answers about the original run" not in r.stdout


@pytest.mark.parametrize("missing", [
    ("live_threads",), ("threads_started",),
    ("live_threads", "threads_started"),
])
def test_refocus_withholds_when_the_thread_record_predates_the_check(tmp_path,
                                                                     missing):
    """A trace from before the thread bookkeeping existed reads as "no
    threads" under `meta.get(...) or []`. Absence of the record is not a
    record of absence -- `_source_state` withholds for exactly this shape
    four lines away, and these must agree.

    Each key is dropped on its own as well as together: a check that only
    looks for one of them still reports the other's absence as agreement.
    """
    run_id, sdir = rec(tmp_path, LOOP)
    drop_meta(sdir / "traces" / f"{run_id}.db", *missing)

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    # `rec()` uses today's recorder, which declares `threads` True at run
    # start -- `drop_meta` deletes the witness key afterward, so this is
    # the declared-True-but-missing state, not a genuine pre-declaration
    # trace: it must read as a contradiction on record, never "predates".
    assert ("declares threads witnessed, but this trace carries no thread "
            "record") in r.stdout
    assert "the recording did not finish, or the record was removed" in r.stdout
    assert "absence of the record is not a record of absence" in r.stdout
    assert "predates" not in r.stdout
    assert "answers about the original run" not in r.stdout


def test_refocus_withholds_when_the_audit_hook_malfunctioned(tmp_path):
    """The audit hook may never raise -- that would break the program it is
    observing -- but swallowing silently is how a hook bug becomes an empty
    `children` list that reads as "no subprocess ran". Failures are counted,
    and a non-zero count withholds."""
    run_id, sdir = rec(tmp_path, LOOP)
    set_meta(sdir / "traces" / f"{run_id}.db", audit_errors=2)

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "audit hook malfunctioned" in r.stdout
    assert "cannot be read as 'nothing was spawned'" in r.stdout


def test_refocus_withholds_when_a_thread_left_no_fingerprint(tmp_path):
    """A worker whose body is entirely stdlib produces NO fingerprint row,
    so counting fingerprints reports a single-threaded run while a second
    thread is still running. The recorder notes which threads were alive
    when it stopped; that is the signal that catches it."""
    run_id, sdir = rec(tmp_path, UNTRACED_WORKER)
    t = trace(sdir, run_id)
    assert len(t.fingerprints()) == 1                # the trap: looks single
    assert "untraced-worker" in t.meta["live_threads"]

    r = refocus(sdir, run_id, "--focus", "prog:start")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "threads: 1 recorded fingerprint(s) compared, all matching" \
        in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "thread(s) running when recording stopped" in r.stdout
    assert "untraced-worker" in r.stdout
    assert "answers about the original run" not in r.stdout


# -- exit status and the changed source tree --------------------------------

def test_refocus_withholds_the_licence_when_the_runs_ended_differently(
        tmp_path):
    """A MATCH on shape says nothing about the value that decided the exit."""
    run_id, sdir = rec(tmp_path, EXIT_FROM_FILE)
    r = refocus(sdir, run_id, "--focus", "prog:attempt")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert ("the two runs ended differently: exit 0 originally, exit 1 on "
            "the rerun") in r.stdout
    assert "licence: WITHHELD" in r.stdout


def test_refocus_warns_about_changed_source_and_still_reports_match(tmp_path):
    """The fingerprint speaks to execution PATH, not to file bytes. When the
    edit leaves the causal stream untouched, MATCH is the honest verdict --
    and the changed source is exactly why it must not be read as "same
    run"."""
    run_id, sdir = rec(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(LOOP.replace("[5, 10, 20]", "[1, 2]"))

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert "sum: 3 2" in r.stdout              # different code really ran
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: CHANGED since the original run" in r.stdout
    assert "1 of 1 file(s) differ by content: prog.py" in r.stdout
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "1 source file(s) CHANGED between the two runs" in r.stdout
    assert "answers about the original run" not in r.stdout


def test_refocus_catches_an_edit_git_status_cannot_see(tmp_path):
    """`git_dirty_hash` is sha256 of `git status --porcelain` -- a list of
    PATHS, not contents. A file that was already dirty when the original ran
    can be rewritten wholesale between the runs and that hash never moves,
    so a licence gate built on it would certify a rerun of different code as
    `source: unchanged`. Contents are what get compared."""
    run_id, sdir = rec_in_git(tmp_path, LOOP,
                              uncommitted=LOOP.replace("[5, 10, 20]", "[4]"))
    before = git_info(tmp_path)["git_dirty_hash"]
    assert before                                   # we really are in a repo
    (tmp_path / "prog.py").write_text(
        LOOP.replace("[5, 10, 20]", "[1, 2, 3, 9]"))
    assert git_info(tmp_path)["git_dirty_hash"] == before   # git sees nothing

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert "sum: 15 2" in r.stdout                  # different code really ran
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: CHANGED since the original run" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "answers about the original run" not in r.stdout


def test_refocus_names_changed_source_as_a_possible_cause_of_divergence(
        tmp_path):
    """On a DIVERGED verdict there is no licence to withhold, but "the
    source moved" is the likeliest answer to the reader's next question and
    must sit next to the verdict, not only in the header that scrolled by."""
    run_id, sdir = rec(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(
        LOOP.replace("total = total + op", "total = helper(total + op) - 1"))

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "source: CHANGED since the original run" in r.stdout
    assert "differences in the world between the two runs" in r.stdout
    assert "1 source file(s) CHANGED between the two runs" in r.stdout
    assert "refocus verdict: DIVERGED" in r.stdout
    assert "licence:" not in r.stdout          # nothing to license


def test_refocus_compares_every_file_the_original_executed(tmp_path):
    """The check covers each file the original interned traced code from,
    not just the entry script: an edit to an imported module is exactly the
    change a reader would most want flagged."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib.py").write_text(LIB)
    run_id, sdir = rec(tmp_path, TWO_FILES)
    assert len(trace(sdir, run_id).meta["source_hashes"]) == 2

    (tmp_path / "lib.py").write_text(LIB.replace("x * 2", "x * 5"))
    r = refocus(sdir, run_id, "--focus", "prog:main")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 of 2 file(s) differ by content: lib.py" in r.stdout
    assert "licence: WITHHELD" in r.stdout


# -- the reporting seam -----------------------------------------------------

def test_report_refuses_a_verdict_when_the_new_trace_is_lossy(tmp_path,
                                                              capsys):
    """REFUSED is neither MATCH nor DIVERGED and must never collapse into
    either. `late_writes > 0` is one shape that produces it, and the
    recorder cannot be made to record a non-zero count on demand (see
    diff_cmd), so the reporting seam is exercised directly."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-origaa")
    b = synthetic(sdir, "20260101-000000-newbbb", late_writes=3)
    ta, tb = Trace.open(a), Trace.open(b)
    res = compare(ta, tb)
    assert res["verdict"] == "REFUSED"                      # precondition

    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem,
                            refocus_cmd.assess(ta, tb, res))
    out = capsys.readouterr().out
    assert rc == 2
    assert "refocus verdict: REFUSED" in out and "UNVERIFIED" in out
    assert "refocus verdict: MATCH" not in out
    assert "refocus verdict: DIVERGED" not in out
    assert "licence:" not in out
    assert "threads: not compared -- no verdict was issued" in out


def test_report_withholds_the_licence_when_the_thread_is_inferred(tmp_path,
                                                                   capsys):
    """A MATCH verified against an INFERRED thread may not be about the
    thread the reader assumes, so it withholds rather than merely softening
    its wording -- softening is what let the old output say "this MATCH is
    about the worker" and grant the licence in the next breath."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-legacya", main_thread_ident=None)
    b = synthetic(sdir, "20260101-000000-legacyb", main_thread_ident=None)
    ta, tb = Trace.open(a), Trace.open(b)
    assert ta.main_thread_basis() == "inferred"             # precondition
    res = compare(ta, tb)
    assert res["verdict"] == "MATCH"

    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem,
                            refocus_cmd.assess(ta, tb, res))
    out = capsys.readouterr().out
    assert rc == 0
    assert "refocus verdict: MATCH" in out
    assert "licence: WITHHELD" in out
    assert "the original's compared thread is INFERRED, not recorded" in out
    assert "the rerun's compared thread is INFERRED, not recorded" in out
    assert "answers about the original run" not in out


def test_report_passes_world_findings_through_to_the_licence(tmp_path,
                                                             capsys):
    """Findings about the world outside the traces -- the source tree, the
    environment -- can only be established by the caller, and must land in
    the same list as the trace-derived ones."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-srcaaa")
    b = synthetic(sdir, "20260101-000000-srcbbb")
    ta, tb = Trace.open(a), Trace.open(b)

    res = compare(ta, tb)
    rc = refocus_cmd.report(
        ta, tb, res, a.stem, b.stem,
        refocus_cmd.assess(ta, tb, res, ["the sky turned green"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "licence: WITHHELD" in out
    assert "  - the sky turned green" in out
    assert "answers about the original run" not in out


def test_report_withholds_when_no_thread_fingerprint_was_recorded(tmp_path,
                                                                   capsys):
    """`compare()` refuses two empty streams before this is reached for a
    real recording, so this gate is defence in depth -- but "no fingerprint
    was recorded" still means the whole-thread comparison never ran, and a
    check that did not run can never support the licence. Driven at the
    seam, because the recorder cannot be asked for a trace that has causal
    events and no fingerprint."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-nofpaa", fingerprint=None)
    b = synthetic(sdir, "20260101-000000-nofpbb", fingerprint=None)
    ta, tb = Trace.open(a), Trace.open(b)
    assert ta.fingerprints() == {}                          # precondition
    res = compare(ta, tb)
    assert res["verdict"] == "MATCH"        # the streams themselves matched

    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem,
                            refocus_cmd.assess(ta, tb, res))
    out = capsys.readouterr().out
    assert rc == 0
    assert "refocus verdict: MATCH" in out
    assert "licence: WITHHELD" in out
    assert "no per-thread fingerprint was recorded on either side" in out
    assert "answers about the original run" not in out


def test_refocus_withholds_when_a_source_digest_was_never_taken(tmp_path):
    """A file the recorder could not read has a None digest. Comparing that
    against a failed read now would make two failures agree and report
    "unchanged" over a file nobody has ever hashed."""
    run_id, sdir = rec(tmp_path, LOOP)
    path = sdir / "traces" / f"{run_id}.db"
    hashes = dict(trace(sdir, run_id).meta["source_hashes"])
    set_meta(path, source_hashes={p: None for p in hashes})

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "source: unverifiable" in r.stdout
    assert "had no digest recorded" in r.stdout
    assert "source: unchanged" not in r.stdout
    assert "licence: WITHHELD" in r.stdout
    assert "could not be checked" in r.stdout


def test_report_grants_the_licence_when_nothing_is_found(tmp_path, capsys):
    """The negative control for the seam: with no world findings and two
    clean traces the licence really is granted, so every WITHHELD assertion
    above is failing for its stated reason and not by construction."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-cleana")
    b = synthetic(sdir, "20260101-000000-cleanb")
    ta, tb = Trace.open(a), Trace.open(b)

    res = compare(ta, tb)
    rc = refocus_cmd.report(ta, tb, res, a.stem, b.stem,
                            refocus_cmd.assess(ta, tb, res))
    out = capsys.readouterr().out
    assert rc == 0
    assert f"licence: verified against {a.stem}" in out
    assert "identical call shape across 1 compared fingerprint(s)" in out
    assert "licence: WITHHELD" not in out


def test_stamp_records_why_a_verdict_was_refused(tmp_path):
    """A REFUSED rerun must carry its reason in the trace, not only in the
    terminal it was printed to."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-stampa")
    b = synthetic(sdir, "20260101-000000-stampb", late_writes=2)
    ta, tb = Trace.open(a), Trace.open(b)
    res = compare(ta, tb)
    assert res["verdict"] == "REFUSED"

    refocus_cmd._stamp(b, res, refocus_cmd.assess(ta, tb, res))
    m = Trace.open(b).meta
    assert m["refocus_verdict"] == "REFUSED"
    assert any("dropped >=2 trace write(s)" in reason
               for reason in m["refocus_refused_reasons"])


# -- round 4: the sixth and seventh paths, and the shape of the claim -------

def test_refocus_withholds_when_multiprocessing_spawned_a_child(tmp_path):
    """The sixth false licence. `multiprocessing` with spawn/forkserver
    reaches the OS through `_posixsubprocess.fork_exec` and never raises
    `subprocess.Popen`, so `children` stayed empty and the full licence was
    granted while the child copied a different payload.

    The audit event that catches that syscall was only added in CPython 3.14,
    so this splits by capability: on 3.14+ the spawn IS witnessed and the
    licence is WITHHELD; below it the spawn is invisible, so the licence cannot
    be withheld on it -- but it must NOT claim `no child witnessed` either. Both
    halves are the same rule: never assert what the trace cannot support."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "payload.txt").write_text("ORIGINAL payload")
    run_id, sdir = rec(tmp_path, MULTIPROCESSING_CHILD)
    m = trace(sdir, run_id).meta
    assert m["children"] == []                # the trap: nothing in `children`
    assert m["audit_errors"] == 0

    (tmp_path / "payload.txt").write_text("A COMPLETELY DIFFERENT payload")
    r = refocus(sdir, run_id, "--focus", "prog:deliver")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "delivered.txt").read_text() == (
        "A COMPLETELY DIFFERENT payload")
    assert "refocus verdict: MATCH" in r.stdout

    if sys.version_info >= (3, 14):
        assert m["spawn_syscalls"] > 0            # the syscall was seen...
        assert "licence: WITHHELD" in r.stdout    # ...so the licence withholds
        assert "started at least one child process (none named," in r.stdout
        assert "low-level spawn syscall(s) seen)" in r.stdout
        assert "licence: verified against" not in r.stdout
    else:
        assert m["spawn_syscalls"] == 0           # invisible on this interpreter
        # the licence cannot withhold on a syscall it never saw, but it also
        # must not vouch that no child ran -- the claim is simply absent
        assert "no child process witnessed" not in r.stdout


def test_refocus_omits_the_child_claim_when_spawns_are_unwitnessable(tmp_path):
    """A trace recorded where no audit event fires for a multiprocessing spawn
    (CPython < 3.14) cannot have its licence vouch `no child witnessed` -- that
    check could not run. Forced through meta so the rule holds on every
    interpreter, not only the ones that happen to lack the audit event."""
    run_id, sdir = rec(tmp_path, LOOP)
    set_meta(sdir / "traces" / f"{run_id}.db", spawn_witnessing=False)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: verified against" in r.stdout       # still granted...
    assert "no child process witnessed" not in r.stdout  # ...but not this claim
    # the categorical blind-spot block still states the gap on every verdict
    assert "any child process, by any mechanism" in r.stdout


def test_refocus_no_longer_ignores_terminal_geometry(tmp_path, monkeypatch):
    """The seventh false licence. COLUMNS sat on the volatile denylist, so a
    program that sized its output by terminal width wrote 80 bytes in one run
    and 9000 in the other under a full licence. Terminal geometry is not
    shell bookkeeping that moves between consecutive commands -- it changes
    only on a resize -- so ignoring it bought almost nothing."""
    monkeypatch.setenv("COLUMNS", "80")
    run_id, sdir = rec(tmp_path, READS_COLUMNS)
    assert (tmp_path / "out.txt").stat().st_size == 80

    monkeypatch.setenv("COLUMNS", "9000")
    r = refocus(sdir, run_id, "--focus", "prog:width")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "out.txt").stat().st_size == 9000

    assert "refocus verdict: MATCH" in r.stdout
    assert "env: CHANGED since the original run" in r.stdout
    assert "COLUMNS" in r.stdout
    assert "licence: WITHHELD" in r.stdout


def test_the_ignored_volatile_keys_are_named_not_counted(tmp_path):
    """"4 volatile keys ignored" is not something a reader can judge. The
    names are what let them notice that a key they care about is on it."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    # the env LINE names them, not merely the licence fact further down:
    # asserting against the whole of stdout let one stand in for the other
    env_line = next(ln for ln in r.stdout.splitlines()
                    if ln.startswith("env: "))
    assert "not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _" in env_line
    fact = next(ln for ln in r.stdout.splitlines()
                if "environment variable(s) compared and unchanged" in ln)
    assert "not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _" in fact
    assert "volatile shell keys ignored" not in r.stdout      # the old count
    assert "ignoring only" not in r.stdout       # an exhaustive-sounding claim
    # COLUMNS and LINES are no longer among them
    assert "COLUMNS" not in r.stdout and "LINES" not in r.stdout


def test_refocus_withholds_when_the_spawn_record_predates_the_check(tmp_path):
    """A trace recorded before spawn syscalls were counted would otherwise
    read as "no child process witnessed, by any mechanism sensorium watches"
    -- the strongest of the five verified facts, granted on a key that was
    never written. The thread bookkeeping already handles this shape; these
    must agree."""
    run_id, sdir = rec(tmp_path, LOOP)
    drop_meta(sdir / "traces" / f"{run_id}.db", "spawn_syscalls")

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    # `rec()` uses today's recorder, which declares `children` True at run
    # start -- `drop_meta` deletes the witness key afterward, so this is
    # the declared-True-but-missing state, not a genuine pre-declaration
    # trace: it must read as a contradiction on record, never "predates".
    assert ("declares children witnessed, but this trace carries no "
            "spawn-syscall record") in r.stdout
    assert "the recording did not finish, or the record was removed" in r.stdout
    assert "absence of the record is not a record of absence" in r.stdout
    assert "predates" not in r.stdout
    assert "licence: verified against" not in r.stdout


def test_licence_names_an_undeclared_output_capability_as_a_blind_spot(
        tmp_path, monkeypatch):
    from sensorium.query.refocus_world import _licence_caveats
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"output": False, "threads": True},
                       threads_started=0, live_threads=[])
    w.write_fingerprint(1, "aa" * 16, 1)
    w.close()
    from sensorium import paths
    from sensorium.store.reader import Trace
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    caveats = _licence_caveats(t, t)
    assert any("output was not recorded" in c and "cross-check did not run" in c
               for c in caveats)
