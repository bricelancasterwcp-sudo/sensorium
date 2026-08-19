"""Re-run a recorded command with deeper capture, then verify -- via causal
fingerprints -- that the rerun really was the same execution.

The whole value of this command is that its verdict can be trusted. A false
MATCH would let someone draw conclusions about a run that never happened, so
every part of this file is arranged around refusing rather than guessing.

WHAT A MATCH LICENSES, AND WHAT IT DOES NOT
-------------------------------------------
MATCH means: the two runs produced the identical sequence of
(file, qualname, kind) for CALL/RETURN/RAISE/HANDLED on the compared thread.
That is the *shape* of the execution and nothing else. It does NOT say the
arguments were the same, the return values were the same, the timing was the
same, the per-line state was the same, or that any thread besides the one
named was compared at all. What it does license is the one thing this command
exists for: the deeper capture in the new trace describes the same path the
original took, so reading it answers questions about the original mystery.

Deterministic replay is explicitly out of scope. For a program whose control
flow depends on state outside the process, DIVERGED is not a failure of this
command -- it is the correct and honest answer, and the new trace is still
recorded, still queryable, and permanently labelled.

TWO DIFFERENT QUESTIONS, TWO DIFFERENT GATES
--------------------------------------------
`_refusal` answers "may this program be re-run at all", and is checked BEFORE
anything executes -- re-running has side effects, so it is not something to
do speculatively. `diff_cmd.compare` answers "can a verdict be issued", and
is asked after the rerun. Keeping them apart is what makes the treatment of
the two damaged-trace shapes coherent rather than arbitrary:

* An INCOMPLETE original never got its finalize pass, so it never recorded
  `stdin_consumed`. The stdin gate below would read that missing key as False
  and wave through exactly the run it exists to stop. "We do not know whether
  this run read stdin" is not "it did not" -- so the rerun is refused
  outright, with no trace written.
* A finalized-but-lossy original (`late_writes > 0`) has trustworthy
  metadata; only some events are missing. Re-running it is legitimate and
  still buys a deeper trace, so it runs and the verdict comes back REFUSED.

REFUSED is a third verdict, never a synonym for either of the other two.
`compare()` returns it before reading either causal stream, and this command
prints it, stamps it, and exits 2 -- it is never collapsed into MATCH (which
would be a lie) or DIVERGED (which would be a confident false claim about
where two programs parted ways).

THE VERDICT LIVES IN THE TRACE, NOT JUST ON STDOUT
---------------------------------------------------
`refocus_of` is written by the recorder at boot; the verdict is stamped here
the moment it is known. Both are read back by `sensorium info`, so a
DIVERGED or REFUSED rerun can never later pass itself off as a verified one
just because the terminal it was printed to has scrolled away.

WHAT IS AND IS NOT RESTORED
----------------------------
The rerun uses the recorded `argv`, the recorded `cwd`, and the recorded
`include`/`exclude` filters -- the last of these because they gate the causal
stream itself, so a rerun that filtered differently would be compared against
a stream the original never had. `focus` and `window` are the only settings a
caller may change, and only ever to capture MORE, because they gate LINE
events alone.

The process ENVIRONMENT is deliberately NOT restored. The design sketch says
it is; implementing that turned out to be a bad trade. Overwriting a live
process's environment resurrects whatever the original run happened to carry
-- a `TMPDIR` that no longer exists, a stale `VIRTUAL_ENV`, the recorder's own
`SENSORIUM_DIR` -- and warning on every difference is no better, because
shells export volatile variables (`_`, `PWD`, `OLDPWD`, `SHLVL`) that change
between any two consecutive commands, so the warning would fire almost always
and mean almost nothing. What is left is honest and quiet: both traces carry
`env_hash`, `sensorium info` prints it on each, and a reader who suspects the
environment can compare the two in one glance. An environment difference that
actually changed the execution shows up as DIVERGED regardless.

OBSERVER EFFECT
---------------
Deeper capture is not free: LINE events run `capture_value` on every local,
which calls the program's own `__repr__` code and slows the run down. A
program sensitive to either can genuinely take a different path the second
time. That shows up as DIVERGED, which is the honest outcome -- but it is
worth knowing that the instrument is part of what changed.
"""
import os
import sys
from pathlib import Path

from sensorium import paths
from sensorium.query.diff_cmd import compare, print_comparison
from sensorium.store import db
from sensorium.store.reader import Trace

_NOT_VERIFIED = (
    "NOT verified by this MATCH: argument and return values, timing, "
    "per-line state, and any thread other than the one compared -- only the "
    "CALL/RETURN/RAISE/HANDLED sequence was checked")

_CHANGED_TREE = (
    "warning: the working tree CHANGED between the two runs -- read this "
    "verdict in that light: the rerun executed DIFFERENT source than the "
    "recording did")


def add_parser(sub) -> None:
    p = sub.add_parser(
        "refocus",
        help="re-run a recorded command with deeper capture, verified")
    p.add_argument("run")
    p.add_argument(
        "--focus", action="append", default=[], required=True,
        help="pkg.module or pkg.module:qualname; repeatable. Added to the "
             "original run's focus, never replacing it.")
    p.add_argument(
        "--window", default=None,
        help="qualname gate for LINE capture; defaults to the original's")
    p.set_defaults(func=run)


# -- may this program be re-run at all? ------------------------------------
def _refusal(meta: dict) -> str | None:
    """Why re-running this recorded command would be illegitimate.

    Order is load-bearing: `incomplete` is checked before `stdin_consumed`
    because an incomplete trace does not have a `stdin_consumed` key to
    check -- see the module docstring.
    """
    if meta.get("incomplete"):
        return ("original trace is INCOMPLETE -- recording ended without a "
                "finalize pass, so it never recorded whether the run "
                "consumed stdin, and its causal stream can stop anywhere "
                "without saying so. Neither the rerun nor a verdict against "
                "it would mean anything")
    if meta.get("stdin_consumed"):
        return ("original run consumed stdin -- marked non-refocusable: a "
                "rerun reads different stdin, or none, so it could not be "
                "the same execution and no verdict about it would be honest")
    if not meta.get("argv"):
        return "original trace records no command to re-run"
    cwd = meta.get("cwd")
    if not cwd:
        return "original trace records no working directory to re-run from"
    if not os.path.isdir(cwd):
        return (f"original working directory {cwd} no longer exists -- the "
                "rerun could not start where the original did")
    return None


def _refuse(orig_name: str, problem: str) -> int:
    print(f"error: cannot refocus {orig_name}: {problem}", file=sys.stderr)
    print("no rerun was attempted; `sensorium run --focus ...` will record a "
          "fresh, UNVERIFIED trace if that is what you want", file=sys.stderr)
    return 2


# -- run settings ----------------------------------------------------------
def _merged_focus(meta: dict, requested) -> list[str]:
    """The original's focus plus what was asked for.

    A refocus only ever captures MORE: dropping the original's focus would
    make the new trace shallower than the one it is meant to explain.
    Widening it cannot move the verdict, because focus (and window) gate
    only LINE events, which are never fingerprinted and never enter a
    causal stream. `include`/`exclude` are a different matter entirely --
    they gate the causal stream itself, so they are inherited verbatim and
    are deliberately not overridable here.
    """
    focus = list(meta.get("focus") or [])
    for entry in requested:
        if entry not in focus:
            focus.append(entry)
    return focus


def _pin_trace_store() -> None:
    """Keep the rerun in the store the original came from.

    A relative SENSORIUM_DIR would follow the chdir into the original cwd
    and silently write the new trace somewhere `sensorium runs` will never
    look for it.
    """
    sdir = os.environ.get("SENSORIUM_DIR")
    if sdir and not os.path.isabs(sdir):
        os.environ["SENSORIUM_DIR"] = str(Path(sdir).resolve())


def _source_state(meta: dict, cwd: str) -> tuple[str, bool]:
    """(one status line, did the tree change?).

    A changed tree is a WARNING, never a refusal: the fingerprint speaks to
    the execution path, not to file bytes, so an edit that leaves the causal
    stream untouched still earns an honest MATCH. What it costs is the right
    to assume the *values* were the same, which is why the change is said
    loudly and repeated next to the verdict.
    """
    from sensorium.record import boot

    was_sha, was_dirty = meta.get("git_sha"), meta.get("git_dirty_hash")
    now = boot.git_info(Path(cwd))
    if was_sha is None or now["git_sha"] is None:
        return (f"source: unverifiable -- no git repository at {cwd}, so "
                "sensorium cannot tell whether the code changed since the "
                "original run", False)
    if was_sha == now["git_sha"] and was_dirty == now["git_dirty_hash"]:
        return (f"source: unchanged (git {was_sha[:12]}, "
                f"working tree {was_dirty})", False)
    return (f"source: CHANGED since the original run "
            f"(git {was_sha[:12]}/{was_dirty} -> "
            f"{now['git_sha'][:12]}/{now['git_dirty_hash']})", True)


# -- the verdict -----------------------------------------------------------
def _stamp(path: Path, res: dict) -> None:
    """Label the new trace with its verdict, permanently."""
    conn = db.open_trace(path)
    try:
        db.set_meta(conn, "refocus_verdict", res["verdict"])
        if res["verdict"] == "DIVERGED":
            db.set_meta(conn, "refocus_diverge_index", res["index"])
            db.set_meta(conn, "refocus_diverge_a", res["a_desc"])
            db.set_meta(conn, "refocus_diverge_b", res["b_desc"])
        elif res["verdict"] == "REFUSED":
            db.set_meta(conn, "refocus_refused_reasons", res["reasons"])
        conn.commit()
    finally:
        conn.close()


def report(orig: Trace, new: Trace, res: dict, orig_name: str, new_name: str,
           *, source_changed: bool) -> int:
    """Print the comparison and the verdict; return this command's exit code.

    Split out from `run` so all three verdicts can be exercised: a REFUSED
    result comes from a trace shape the recorder cannot be made to produce
    on demand (see `diff_cmd`), and a branch no test can reach is a branch
    nobody has checked.
    """
    print_comparison(orig, new, res, orig_name, new_name)
    if source_changed:
        print(_CHANGED_TREE)
    if res["verdict"] == "REFUSED":
        print(f"REFUSED -- no verdict. {new_name} was recorded and is "
              f"queryable, but it could NOT be verified against "
              f"{orig_name}: treat it as a separate, UNVERIFIED execution")
        return 2
    if res["verdict"] == "DIVERGED":
        print(f"DIVERGED -- {new_name} is a DIFFERENT execution than "
              f"{orig_name}. It is still queryable, and every `sensorium "
              f"info {new_name}` will say so; nothing it shows is a fact "
              f"about {orig_name}")
        return 1
    if (orig.main_thread_basis() == "recorded"
            and new.main_thread_basis() == "recorded"):
        print("verified same execution on the recorded main thread")
    else:
        print("verified same execution on the thread named above, which is "
              "INFERRED rather than recorded -- a weaker verdict than one "
              "against a recorded main thread: if that inference named a "
              "worker thread, this MATCH is about the worker and not about "
              "the original run")
    # The strong claim is withheld outright when the tree moved: the shapes
    # match, but they are the shapes of two different pieces of source, so
    # "answers about the original run" would be exactly the overreach this
    # command exists to prevent.
    if source_changed:
        print("licence: this trace describes the original run's CONTROL "
              "FLOW only -- the rerun executed different source, so values "
              "may differ at every step")
    else:
        print("licence: answers from this trace are answers about the "
              "original run")
    print(_NOT_VERIFIED)
    return 0


# -- driving ---------------------------------------------------------------
def _rerun_and_verify(args, orig: Trace, orig_name: str, meta: dict) -> int:
    from sensorium.record import boot

    argv = list(meta["argv"])
    try:
        boot.resolve_target(argv)      # refuse before announcing a rerun
    except boot.TargetError as e:
        return _refuse(orig_name, str(e))

    focus = _merged_focus(meta, args.focus)
    window = args.window if args.window is not None else meta.get("window")
    source, changed = _source_state(meta, os.getcwd())
    print(f"refocus-of: {orig_name}   cmd: {' '.join(argv)}")
    print(f"cwd: {os.getcwd()}")
    print(f"focus: {', '.join(focus)}   window: {window or '-'}")
    print(source)
    print("--- rerunning (the lines below are the program's own output) ---")

    new_id, status = boot.run_target(
        argv, focus=focus, include=meta.get("include") or (),
        exclude=meta.get("exclude") or (), window=window,
        refocus_of=meta.get("run_id", orig_name))

    new_path = (paths.traces_dir() / f"{new_id}.db").resolve()
    new = Trace.open(new_path)
    res = compare(orig, new)
    _stamp(new_path, res)

    print("--- verdict ---")
    print(f"run: {new_id}")
    print(f"trace: {new_path}")
    was = meta.get("exit_status", "?")
    print(f"exit: rerun {status}   original {was}")
    if status != was:
        print("note: exit status differs -- the causal shape can match while "
              "the value that decided the exit does not")
    return report(orig, new, res, orig_name, new_id, source_changed=changed)


def run(args) -> int:
    orig_path = paths.find_trace(args.run).resolve()
    orig_name = orig_path.stem
    orig = Trace.open(orig_path)
    meta = orig.meta

    problem = _refusal(meta)
    if problem:
        return _refuse(orig_name, problem)

    _pin_trace_store()
    prev_cwd = os.getcwd()
    os.chdir(meta["cwd"])
    try:
        return _rerun_and_verify(args, orig, orig_name, meta)
    finally:
        os.chdir(prev_cwd)
