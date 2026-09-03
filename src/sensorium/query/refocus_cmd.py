"""Re-run a recorded command with deeper capture, then verify -- via causal
fingerprints -- that the rerun really was the same execution.

The whole value of this command is that its verdict can be trusted. A false
MATCH would let someone draw conclusions about a run that never happened, so
every part of this file is arranged around refusing rather than guessing.

THREE SEPARATE THINGS, NEVER CONFLATED
---------------------------------------
An earlier version of this command printed one verdict and one confident
sentence, and was wrong three ways at once: a rerun with a different
environment, a rerun where only a worker thread took another path, and a
rerun the recorder itself perturbed all came back MATCH with the full "answers
about the original run" licence. The root cause was a category error -- MATCH
is a statement about *call shape*, and the licence sentence is a statement
about *the whole run*. They are now three different things:

* **VERDICT** (MATCH / DIVERGED / REFUSED) is about causal shape, across
  EVERY recorded thread AND every asyncio task. `diff_cmd.compare()` owns
  the compared thread and pinpoints where it parted; `_thread_divergence`
  widens that to the rest, because spec section 4 says refocus compares
  per-thread fingerprints and a worker that took another path means the
  rerun was a different execution. `_task_divergence` is the same argument
  one level down: under the per-task basis the compared thread stream holds
  only what ran outside every task, so a task that took another path leaves
  it identical -- and `compare()` reports that as DIVERGED with no `index`,
  because the difference is not a step of the stream those keys describe.
  Task streams are matched by CONTENT, never by the order they interleaved
  in, which is why an order flip is a MATCH and the ordering is named in the
  blind spots rather than compared.
* **LICENCE** is withheld on *every* honesty signal this tool can check --
  a source file's contents moved, the environment moved, the program's own
  output differs, the two runs exited differently, threads were involved at
  all or one was still running when recording stopped, the compared thread
  is inferred rather than recorded, a subprocess ran unwitnessed. It is
  withheld just as firmly when a check could not RUN, because the granted
  sentence claims they all agreed. They are listed, not summarised.
* **BLIND SPOTS** are stated on every verdict -- MATCH, DIVERGED and
  REFUSED alike, because "every verdict" has to include the verdict that
  says nothing or the sentence is not true. See OBSERVER EFFECT below: the
  biggest blind spot is structural.

A verdict over nothing is not a verdict. Two EMPTY causal streams compare
equal, so a target whose code was never traced at all -- resolved outside
the run's root, or filtered away by an inherited `--include`/`--exclude` --
used to produce a serene MATCH over zero events with the licence granted on
the line after "there was nothing to compare". `compare()` now refuses that
case at the seam, and `_licence_caveats` withholds on a zero-thread
comparison as well, because two independent things had to be wrong for it to
escape.

WHAT A MATCH LICENSES, AND WHAT IT DOES NOT
-------------------------------------------
MATCH means: every recorded thread -- and every asyncio task beside it --
produced the identical sequence of (file, qualname, kind) for
CALL/RETURN/RAISE/HANDLED. That is the *shape* of the execution and nothing
else. It does NOT say the arguments were the same, the return values were
the same, the timing was the same, the per-line state was the same, or that
the threads interleaved the same way -- or the tasks.

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

THE VERDICT LIVES IN THE TRACE, NOT JUST ON STDOUT
---------------------------------------------------
`refocus_of` is written by the recorder at boot; the verdict is stamped here
the moment it is known. Both are read back by `sensorium info` and
`sensorium runs`, so a DIVERGED or REFUSED rerun can never later pass itself
off as a verified one just because the terminal has scrolled away.

WHAT IS AND IS NOT RESTORED
----------------------------
The rerun uses the recorded `argv`, the recorded `cwd`, and the recorded
`include`/`exclude` filters -- the last of these because they gate the causal
stream itself, so a rerun that filtered differently would be compared against
a stream the original never had. `focus` and `window` are the only settings a
caller may change, and only ever to capture MORE, because they gate LINE
events alone.

The process ENVIRONMENT is deliberately NOT restored. Overwriting a live
process's environment resurrects whatever the original happened to carry -- a
`TMPDIR` that no longer exists, a stale `VIRTUAL_ENV`, the recorder's own
`SENSORIUM_DIR` -- and the target runs in-process, so the swap would hit the
recorder too. But not restoring it is no excuse for not LOOKING: both traces
store the full `env` dict, so `_env_state` diffs them and any non-volatile
difference withholds the licence. `_UNCOMPARED_ENV` exists only to drop the
handful of shell-bookkeeping keys that change between any two consecutive
commands; it is deliberately tiny, because every name on it is a name this
tool has stopped checking.

The SOURCE is checked by content, never by `git_dirty_hash` -- see
`_source_state`. That hash covers a list of paths, so a file that was
already dirty when the original ran can be rewritten wholesale without
moving it, and "source: unchanged" would have been a claim about nothing.

OBSERVER EFFECT -- A STRUCTURAL BLIND SPOT
-------------------------------------------
Deeper capture is not free: LINE events run `capture_value` on every local,
which calls the program's own `__repr__`. A `__repr__` with a side effect
(a counter, a log line, a lazy load) therefore behaves differently under
`--focus` than it did in the original recording.

This CANNOT be detected by the fingerprint, and any claim that it "shows up
as DIVERGED" is false. The recorder calls into the program from inside its
own hooks, where `tls.in_hook` is set, and `_on_start`/`_on_return` return
immediately while it is -- so every frame the instrument itself provokes is
suppressed from the trace by construction. The instrument's footprint is
invisible to the very hash that is supposed to prove nothing changed.

The one cross-check available is the program's own captured output, which
`_output_difference` compares and reports. It is a real signal (it catches
the counting-`__repr__` case) but it is not a proof: a side effect that
prints nothing leaves nothing to compare. So the blind spot is stated on
every verdict rather than papered over.

WHERE THE CODE IS
-----------------
This file owns the verdict, the assessment that ties the findings to it, the
stamp and the report. The FINDINGS themselves -- the source-tree check, the
environment check, the output comparison, the licence caveats and the
verified facts -- live in `refocus_world`, which decides nothing and prints
nothing. Every name below that starts `_source_`, `_env_`, `_output_`,
`_licence_` or `_verified_` is imported from there and re-exported here.
"""
import os
import sys
from collections import Counter
from pathlib import Path

from sensorium import paths
from sensorium.query.caps import require
from sensorium.query.vocab import terms
from sensorium.query.diff_cmd import (compare, print_comparison,
                                      task_drill_lines)
# The evidence layer, split out at this file's 800-line ceiling. Re-exported
# so `refocus_cmd.<name>` keeps resolving: these are one command's internals
# living in two files, not two modules with two surfaces.
from sensorium.query.refocus_world import (  # noqa: F401
    _UNCOMPARED_ENV, _clip, _env_diff, _env_state, _licence_caveats,
    _output_difference, _output_text, _source_state, _spawn_witnessed,
    _verified_facts)
from sensorium.store import db
from sensorium.store.reader import Trace

# Printed on every verdict, and CATEGORICAL on purpose.
#
# An earlier version listed the mechanisms sensorium cannot see. Two more
# arrived within a day -- a `multiprocessing` child spawned through
# `_posixsubprocess.fork_exec`, and a `COLUMNS` change hidden by the volatile
# denylist -- and the list was worse than useless for them: it read as
# EXHAUSTIVE, so a reader who checked it concluded their multiprocessing
# child had been witnessed. An enumeration that looks complete is more
# dangerous than no enumeration. The statement below is bounded by what the
# instrument IS rather than by what has been thought of so far, so it stays
# true when the next mechanism appears.
_BLIND_SPOTS = (
    "what sensorium sees at all: Python code that this run traced, in files "
    "under the run's own root. Nothing else. No verdict here -- MATCH, "
    "DIVERGED or REFUSED -- says anything about:",
    "  - any child process, by any mechanism. Some are noticed and listed "
    "above; an empty list is NOT evidence that none ran",
    "  - any thread not started through Python's own threading/_thread",
    "  - any file the program read or wrote. Only SOURCE files are hashed, "
    "so config, fixtures, databases and inputs move unseen",
    "  - any code outside the run's root: the stdlib, site-packages, "
    "installed dependencies, PYTHONPATH modules, and whatever this run's "
    "own --include/--exclude filtered out",
    # NOT "and nothing outside the environment is compared at all": source
    # contents, stdout/stderr and exit status are all compared, and the
    # source line saying so prints twelve lines above this block.
    "  - any environment variable this run did not compare; the ones it "
    "skipped are named above",
    "  - the clock, the network, and everything else the machine did",
    # The task clause is not decoration: this version deliberately compares
    # task streams as a multiset, so an order flip comes back MATCH. The
    # thing a verdict is built on NOT looking at has to be stated on every
    # verdict, or the MATCH reads as "the tasks ran the same way".
    "  - argument and return values, per-line state, timing, the order "
    "threads ran in relative to one another, and the order asyncio tasks "
    "interleaved in: recorded, never compared",
    "  - the recorder's own footprint: deeper capture runs the program's "
    "__repr__ inside hooks that suppress themselves, so an instrument that "
    "changes the program leaves no mark on the fingerprint",
)


def _print_blind_spots() -> None:
    for line in _BLIND_SPOTS:
        print(line)


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
def _refusal(meta: dict, trace: Trace | None = None) -> str | None:
    """Why re-running this recorded command would be illegitimate.

    Order is load-bearing: `incomplete` is checked before `stdin_consumed`
    because an incomplete trace does not have a `stdin_consumed` key to
    check -- see the module docstring. The fingerprint-basis check comes
    before the argv/cwd gates for a different reason: those two ask whether
    the world still allows a rerun, and this one asks whether any verdict
    against this trace could mean anything. A trace whose directory is also
    gone is better told the durable reason -- re-recording is the fix for
    both, and restoring the directory is the fix for neither.

    `trace` is optional only so the metadata-shaped refusals stay callable
    from a bare dict; every real call site passes the opened trace.
    """
    if trace is not None:
        # First, and before anything is read about the run: a recorder that
        # declares it cannot be refocused is refusing the whole command, not
        # failing one of its checks. Asking the other questions of such a
        # trace would report the first one it happens to fail as the reason.
        declared = require(trace, "refocus", "refocus")
        if declared:
            return declared
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
    # A trace recorded before task fingerprints existed defines its thread
    # stream to INCLUDE the events that ran inside asyncio tasks; this
    # version defines it to exclude them and compares the tasks separately.
    # Comparing across that seam would put every task event on one side
    # only, so `diff` refuses it -- and refusing it here as well means the
    # rerun, which has side effects, never happens for an answer that could
    # not have been issued anyway.
    tasks = trace.tasks() if trace is not None else []
    if tasks and trace.fingerprint_basis == "per-thread":
        return (f"original was recorded under the per-thread fingerprint "
                f"basis and ran {len(tasks)} asyncio task(s); this version "
                "compares tasks by content and defines thread streams "
                "without them, so no verdict against it would compare like "
                "with like -- re-record it with this version")
    if not meta.get("argv"):
        return "original trace records no command to re-run"
    cwd = meta.get("cwd")
    if not cwd:
        return "original trace records no working directory to re-run from"
    if not os.path.isdir(cwd):
        return (f"original working directory {cwd} no longer exists -- the "
                "rerun could not start where the original did")
    return None


def _refuse(orig_name: str, problem: str, trace: Trace) -> int:
    """The refusal, and what may be done instead -- in the words of the
    trace that was refused. `sensorium run --focus ...` cannot read a Rust
    recording, so offering it there sends the reader to a second refusal;
    the trace is required rather than defaulted, so no call site can reach
    this line without saying which language it is speaking."""
    print(f"error: cannot refocus {orig_name}: {problem}", file=sys.stderr)
    print(terms(trace).no_rerun_note, file=sys.stderr)
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
    look for it. Two orderings matter, and both are asserted by `run()`:

    * BEFORE the chdir -- the path is relative to the invoking directory,
      not to the target's.
    * BEFORE the environment snapshot the licence check compares. The
      snapshot must be of the environment the target actually EXECUTES
      under, and this rewrite mutates that environment. Snapshotting first
      left the check describing an environment the program never saw: a run
      recorded with SENSORIUM_DIR=sdir wrote into `sdir`, the rerun wrote
      into `/tmp/.../sdir`, and the output said `env: unchanged (76
      variables compared)` and granted the full licence.

    Reporting the tool's own bookkeeping as an environment change the user
    should worry about would be noise, not honesty -- so SENSORIUM_DIR is in
    `_UNCOMPARED_ENV` instead, where it is NAMED rather than hidden, and a
    program that reads it goes explicitly unchecked.
    """
    sdir = os.environ.get("SENSORIUM_DIR")
    if sdir and not os.path.isabs(sdir):
        os.environ["SENSORIUM_DIR"] = str(Path(sdir).resolve())


# -- the whole-run verdict -------------------------------------------------
def _thread_shapes(trace: Trace) -> Counter:
    """The multiset of per-thread causal fingerprints.

    A multiset, not a mapping: thread IDs are OS handles and never repeat
    across processes, so the two runs' threads cannot be paired by identity.
    Two threads doing identical work share a hash and are counted twice,
    which is the correct comparison -- "the same shapes ran, the same number
    of times".
    """
    return Counter(h for h, _n in trace.fingerprints().values())


def _thread_scope(orig: Trace, new: Trace) -> str:
    """What the compared thread rows cover, when it is not everything.

    Under the per-task basis a thread's fingerprint covers only the events
    that ran in NO asyncio task -- so a thread whose traced code all ran
    inside one has a row of its own with zero events, and "2 recorded
    fingerprint(s) compared" would otherwise invite the reader to think
    those rows account for the whole run. The tasks are compared too, on
    the line below; this says where the boundary between the two is.

    Empty when neither run recorded a task: nothing was excluded, and a
    parenthetical about a distinction that made no difference is noise.
    """
    if any(t.fingerprint_basis == "per-task" and t.tasks()
           for t in (orig, new)):
        return " (events outside any asyncio task)"
    return ""


def _thread_divergence(orig: Trace, new: Trace) -> str | None:
    """How the two runs' per-thread shapes differ, or None if they do not."""
    a, b = _thread_shapes(orig), _thread_shapes(new)
    if a == b:
        return None
    only_a = sorted(h[:12] for h in (a - b).elements())
    only_b = sorted(h[:12] for h in (b - a).elements())
    return (f"{sum(a.values())} thread(s) recorded originally, "
            f"{sum(b.values())} on the rerun; fingerprints only in the "
            f"original: {', '.join(only_a) or '-'}; only in the rerun: "
            f"{', '.join(only_b) or '-'}")


def _task_divergence(res: dict) -> str | None:
    """How the two runs' asyncio task streams differ, in one line, or None.

    `compare_tasks()` did the comparing -- by CONTENT, as a multiset of
    (name, hash), so a different interleaving is not a difference here and
    the blind-spot block says so. This only phrases the finding for the
    refocus verdict; refocus prints `diff`'s task section with `tasks=False`
    and adds the drill-in commands itself beside this line (D1 of the final
    wave), so the finding is stated exactly once.

    The hashes are part of the sentence, not decoration: this string is
    stamped into the trace as `refocus_diverge_tasks` and read back by
    `info`, where diff's section is not printed above it -- and "only in A:
    task-B; only in B: task-B" without them says two different things
    happened under one name while looking like a contradiction.
    """
    t = res.get("tasks")
    if not t or t["verdict"] != "DIVERGED":
        return None

    def fmt(rows):
        return ", ".join(f"{n if n is not None else '(unnamed)'} {h[:12]}"
                         + ("" if k == 1 else f" x{k}") for n, h, k in rows
                         ) or "-"
    s = (f"{t['n_a']} task stream(s) originally, {t['n_b']} on the rerun; "
         f"only in A: {fmt(t['only_a'])}; only in B: {fmt(t['only_b'])}")
    p = t["pair"]
    if p:
        # A pair with no name on either side was matched by creation order,
        # which is a guide to look at and not a claim that the two are the
        # same task. Saying "first difference inside (unnamed)" without that
        # qualification would assert an identity nothing established.
        guide = (" (paired by creation order -- a guide, not a match)"
                 if p["by_order"] else "")
        s += (f"; first difference inside {p['name'] or '(unnamed)'}"
              f"{guide} at causal step {p['index']}: A {p['a_desc']} / "
              f"B {p['b_desc']}")
    return s


def final_verdict(orig: Trace, new: Trace,
                  res: dict) -> tuple[str, str | None, str | None]:
    """(verdict, thread-divergence description or None, task-divergence
    description or None).

    `compare()` decides on one thread and says exactly where it parted.
    This widens the answer to every recorded thread, because a worker that
    took a different path means the rerun was a different execution -- and
    reporting that as MATCH-with-a-note is how the previous version handed
    out a licence next to the words "this MATCH is about the worker".

    The tasks are the same argument one level down. Under the per-task basis
    the compared thread stream is only what ran OUTSIDE every asyncio task,
    so a rerun whose task took another path can leave that stream identical:
    `compare()` reports DIVERGED with `index` None for exactly this case,
    and a verdict that read only `index` would call it a MATCH.
    """
    if res["verdict"] == "REFUSED":
        return res["verdict"], None, None
    threads = _thread_divergence(orig, new)
    tasks = _task_divergence(res)
    if res["verdict"] == "DIVERGED" and res.get("index") is not None:
        # The compared thread itself parted; `print_comparison` has already
        # pinpointed where, and the thread-shape multiset cannot add to it.
        return "DIVERGED", None, tasks
    # ADDITIVE, never subtractive: `compare()`'s DIVERGED stands whatever
    # this function finds. Today a DIVERGED with no `index` always carries a
    # task divergence, so the two agree -- but that is an invariant of
    # another module which nothing here asserts, and reading only `threads
    # or tasks` would turn a disagreement into a MATCH with the licence
    # granted on top of it. The verdict may only ever be widened.
    return ("DIVERGED" if (res["verdict"] == "DIVERGED" or threads or tasks)
            else "MATCH"), threads, tasks


# -- the assessment --------------------------------------------------------
def assess(orig: Trace, new: Trace, res: dict, world_caveats=(),
           world_verified=()) -> dict:
    """Everything the two traces support, decided once.

    `world_caveats` and `world_verified` are findings about the world outside
    the traces (the source files, the environment) that only the caller can
    establish; everything else is derived here. Computed in one place because
    the verdict is printed, stamped into the new trace, and turned into an
    exit code -- and those three must never be able to disagree.
    """
    verdict, threads, task_divergence = final_verdict(orig, new, res)
    # Computed ONCE and passed down: `_verified_facts` needs the same answer
    # this dict carries, and two calls to the same derivation are two places
    # for it to come out differently.
    scope = _thread_scope(orig, new)
    world = list(world_caveats)
    caveats = ((world + _licence_caveats(orig, new))
               if verdict == "MATCH" else [])
    licence = None
    verified = []
    if verdict == "MATCH":
        licence = "withheld" if caveats else "granted"
        if not caveats:
            facts = _verified_facts(orig, new, scope)
            verified = facts[:1] + list(world_verified) + facts[1:]
    # Everything the report and the stamp need, derived ONCE. `report` used
    # to reach back into `res` for `index` and `tasks` beside this dict,
    # which is two sources for one verdict -- the exact shape that let the
    # printed line, the stamped label and the exit code disagree before.
    return {"verdict": verdict, "threads": threads,
            "task_divergence": task_divergence,
            "tasks": res.get("tasks"),
            "thread_stream_parted": (res["verdict"] == "DIVERGED"
                                     and res["index"] is not None),
            "thread_scope": scope,
            "world": world, "caveats": caveats, "licence": licence,
            "verified": verified}


# -- reporting -------------------------------------------------------------
def _stamp(path: Path, res: dict, a: dict) -> None:
    """Label the new trace with its verdict AND its licence, permanently.

    The licence is stamped for the same reason the verdict is: a listing
    that shows a bare `verdict:MATCH` for a run whose licence was withheld
    on every count is the "reads as a pedigree" failure one level down.
    """
    conn = db.open_trace(path)
    try:
        db.set_meta(conn, "refocus_verdict", a["verdict"])
        # `thread_stream_parted` is False when the divergence is not a step
        # of the compared thread's stream at all (the tasks parted and that
        # stream did not). Writing the index anyway would persist "diverged
        # at step None" as if it were a position, and the task description
        # below is the real one. `res` is read only for the VALUES; whether
        # they apply is `assess`'s answer, so the label and the printed line
        # cannot come from two different readings.
        if a["thread_stream_parted"]:
            db.set_meta(conn, "refocus_diverge_index", res["index"])
            db.set_meta(conn, "refocus_diverge_a", res["a_desc"])
            db.set_meta(conn, "refocus_diverge_b", res["b_desc"])
        elif a["verdict"] == "REFUSED":
            db.set_meta(conn, "refocus_refused_reasons", res["reasons"])
        if a["threads"]:
            db.set_meta(conn, "refocus_thread_divergence", a["threads"])
        if a["task_divergence"]:
            db.set_meta(conn, "refocus_diverge_tasks", a["task_divergence"])
        if a["licence"]:
            db.set_meta(conn, "refocus_licence", a["licence"])
            db.set_meta(conn, "refocus_licence_reasons", a["caveats"])
            db.set_meta(conn, "refocus_licence_verified", a["verified"])
        conn.commit()
    finally:
        conn.close()


def _print_thread_line(orig: Trace, new: Trace, a: dict) -> None:
    """The `threads:` line, in the four shapes it comes in."""
    if a["threads"]:
        print(f"threads: DIVERGED -- {a['threads']}")
    elif a["thread_stream_parted"]:
        # Keyed on whether the compared STREAM parted, not on the verdict: a
        # DIVERGED with no index is a divergence of the tasks, and the
        # compared thread stream matched. Saying it "already diverged" there
        # would be false, and would hide that every thread row did match.
        print("threads: not compared -- the compared thread already diverged")
    elif new.fingerprints():
        # NOT "all N threads matched". That sentence asserted completeness
        # this tool cannot have: a thread whose body is entirely stdlib
        # leaves no fingerprint, so it is not among the N and was never
        # compared. Say how many were compared, and say plainly when more
        # existed than that.
        n = len(new.fingerprints())
        unseen = max(orig.meta.get("threads_started", 0),
                     new.meta.get("threads_started", 0)) + 1 - n
        tail = (f"; {unseen} further thread(s) ran no traced code, left no "
                "fingerprint, and were NOT compared" if unseen > 0 else "")
        print(f"threads: {n} recorded fingerprint(s) compared"
              f"{a['thread_scope']}, all matching{tail}")
    else:
        print("threads: no per-thread fingerprints were recorded on either "
              "side -- there was nothing to compare beyond the stream above")


def _diverged_why(a: dict) -> str:
    """What this DIVERGED is attributed to, in the report's own words."""
    if a["threads"]:
        return "a thread other than the compared one took a different path"
    if a["thread_stream_parted"]:
        return "the compared thread took a different path"
    if a["task_divergence"]:
        # "took a different path" presumes both sides ran one. When a side
        # ran no task stream at all there is no path to have differed, and
        # naming which side is the whole finding.
        t = a["tasks"] or {}
        if t.get("n_a") == 0:
            return "the rerun ran a task stream the original did not"
        if t.get("n_b") == 0:
            return "the original ran a task stream the rerun did not"
        return "a task took a different path"
    # Unreachable through `compare()`, which reports DIVERGED with no index
    # only when the tasks parted. Stated rather than assumed, for the same
    # reason `final_verdict` never downgrades a DIVERGED: if the two modules
    # ever disagree, the honest line is the one that does not name a culprit
    # it has not found.
    return ("the comparison reported a divergence this report could not "
            "attribute to a thread or a task")


def report(orig: Trace, new: Trace, res: dict, orig_name: str, new_name: str,
           a: dict) -> int:
    """Print the comparison and the verdict; return the exit code."""
    # `tasks=False`: the task finding is printed below, in the words that
    # are also stamped into the trace, with the drill-in commands beside
    # them. Letting `diff` print its own version too gave this output two
    # `tasks:` lines that said different amounts about one finding.
    print_comparison(orig, new, res, orig_name, new_name, tasks=False)
    # `res` belongs to `print_comparison` above and to nothing else here:
    # every fact this function decides on comes from `assess`.
    verdict, threads = a["verdict"], a["threads"]
    task_divergence, tasks = a["task_divergence"], a["tasks"] or {}

    if verdict == "REFUSED":
        print("threads: not compared -- no verdict was issued")
        print(f"refocus verdict: REFUSED -- {new_name} was recorded and is "
              f"queryable, but it could NOT be verified against "
              f"{orig_name}: treat it as a separate, UNVERIFIED execution")
        # Stated here too: "on every verdict" has to include the verdict
        # that says nothing, or the sentence is not true.
        _print_blind_spots()
        return 2

    _print_thread_line(orig, new, a)

    if task_divergence:
        # The only `tasks:` line in this output, and the same sentence
        # `_stamp` writes -- so what the terminal says and what `info`
        # replays afterwards cannot drift apart.
        print(f"tasks: DIVERGED -- {task_divergence}")
        for line in task_drill_lines(tasks.get("pair"), orig_name, new_name):
            print(line)
    elif tasks.get("verdict") == "MATCH":
        print(f"tasks: {tasks['n_b']} task stream(s) compared by content, "
              "all matching; the ordering between tasks is not compared")

    if verdict == "DIVERGED":
        why = _diverged_why(a)
        print(f"refocus verdict: DIVERGED -- {why}. {new_name} is a "
              f"DIFFERENT execution than {orig_name}; it is still queryable, "
              f"every `sensorium info {new_name}` says so, and nothing it "
              f"shows is a fact about {orig_name}")
        # Only the WORLD findings, never the trace-derived ones: differing
        # output and a differing exit status are consequences of a
        # divergence, and offering a consequence as a possible cause would
        # send the reader looking in the wrong direction.
        if a["world"]:
            print("differences in the world between the two runs, any of "
                  "which may be why:")
            for caveat in a["world"]:
                print(f"  - {caveat}")
        print("note: a divergence can also be caused by the deeper capture "
              "itself -- capturing values runs the program's own __repr__ "
              "and slows the run down; the fingerprint cannot tell that "
              "apart from the program genuinely taking another path")
        _print_blind_spots()
        return 1

    # The headline may claim only what was compared. Under the per-task
    # basis the thread rows cover what ran OUTSIDE every task, so for a run
    # with tasks the unqualified sentence is false in the most misleading
    # direction available: the raw per-thread sequence of an order-flipped
    # rerun genuinely differs, and it is the SPLIT -- each thread outside
    # its tasks, plus the task multiset -- that matched.
    if a["thread_scope"]:
        print("refocus verdict: MATCH -- every recorded thread produced the "
              "identical CALL/RETURN/RAISE/HANDLED sequence outside its "
              "asyncio tasks, and every task stream matched by content")
    else:
        print("refocus verdict: MATCH -- every recorded thread produced the "
              "identical CALL/RETURN/RAISE/HANDLED sequence")
    if a["caveats"]:
        print("licence: WITHHELD -- this MATCH is about call shape, and "
              "these checks say it is not a statement about the run as a "
              "whole:")
        for caveat in a["caveats"]:
            print(f"  - {caveat}")
    else:
        print(f"licence: verified against {orig_name} on exactly these "
              "points, and no others:")
        for fact in a["verified"]:
            print(f"  - {fact}")
    _print_blind_spots()
    return 0


# -- driving ---------------------------------------------------------------
def _rerun_and_verify(args, orig: Trace, orig_name: str, meta: dict,
                      env: dict) -> int:
    from sensorium.record import boot

    argv = list(meta["argv"])
    try:
        boot.resolve_target(argv)      # refuse before announcing a rerun
    except boot.TargetError as e:
        return _refuse(orig_name, str(e), orig)

    focus = _merged_focus(meta, args.focus)
    window = args.window if args.window is not None else meta.get("window")
    source, source_caveat, source_fact = _source_state(meta)
    env_line, env_caveat, env_fact = _env_state(meta, env)

    print(f"refocus-of: {orig_name}   cmd: {' '.join(argv)}")
    print(f"cwd: {os.getcwd()}")
    print(f"focus: {', '.join(focus)}   window: {window or '-'}")
    print(source)
    print(env_line)
    print("--- rerunning (the lines below are the program's own output) ---")

    new_id, status = boot.run_target(
        argv, focus=focus, include=meta.get("include") or (),
        exclude=meta.get("exclude") or (), window=window,
        refocus_of=meta.get("run_id", orig_name))

    new_path = (paths.traces_dir() / f"{new_id}.db").resolve()
    new = Trace.open(new_path)
    res = compare(orig, new)
    a = assess(orig, new, res,
               [c for c in (source_caveat, env_caveat) if c],
               [f for f in (source_fact, env_fact) if f])
    _stamp(new_path, res, a)

    print("--- verdict ---")
    print(f"run: {new_id}")
    print(f"trace: {new_path}")
    print(f"exit: rerun {status}   original {meta.get('exit_status', '?')}")
    return report(orig, new, res, orig_name, new_id, a)


def run(args) -> int:
    orig_path = paths.find_trace(args.run).resolve()
    orig_name = orig_path.stem
    orig = Trace.open(orig_path)
    meta = orig.meta

    problem = _refusal(meta, orig)
    if problem:
        return _refuse(orig_name, problem, orig)

    # Pin first, THEN snapshot: the environment compared must be the one the
    # target is executed with, not the one this process started with. The pin
    # rewrites SENSORIUM_DIR, which is why that key is in _UNCOMPARED_ENV and
    # named in the output -- snapshotting before the pin instead left the
    # check describing an environment the program never saw.
    _pin_trace_store()
    env = dict(os.environ)
    prev_cwd = os.getcwd()
    os.chdir(meta["cwd"])
    try:
        return _rerun_and_verify(args, orig, orig_name, meta, env)
    finally:
        os.chdir(prev_cwd)
