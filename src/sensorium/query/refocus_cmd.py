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
  EVERY recorded thread. `diff_cmd.compare()` owns the compared thread and
  pinpoints where it parted; `_thread_divergence` widens that to the rest,
  because spec section 4 says refocus compares per-thread fingerprints and a
  worker that took another path means the rerun was a different execution.
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
MATCH means: every recorded thread produced the identical sequence of
(file, qualname, kind) for CALL/RETURN/RAISE/HANDLED. That is the *shape* of
the execution and nothing else. It does NOT say the arguments were the same,
the return values were the same, the timing was the same, the per-line state
was the same, or that the threads interleaved the same way.

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
difference withholds the licence. `_VOLATILE_ENV` exists only to drop the
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
"""
import os
import sys
from collections import Counter
from pathlib import Path

from sensorium import paths
from sensorium.query.diff_cmd import compare, print_comparison
from sensorium.store import db
from sensorium.store.reader import Trace

# Shell bookkeeping that differs between any two consecutive commands and
# says nothing about the program. Deliberately tiny: every name here is a
# name refocus has stopped checking.
_VOLATILE_ENV = frozenset({
    "_",            # bash: the previous command's last argument
    "OLDPWD",
    "PWD",          # os.chdir does not update it; it names the calling shell
    "SHLVL",
    "COLUMNS",
    "LINES",
})

# Printed in full on every verdict. These belong in the OUTPUT, not only in
# this file's docstrings: a limitation a user cannot read is a limitation
# that will be walked into. Three separate attacks landed inside gaps that
# were documented in the source and invisible on screen -- a config file the
# source check does not hash, a module outside the run's root, and a spawn
# mechanism the audit hook does not watch -- and each earned a full licence.
_BLIND_SPOTS = (
    "never checked by ANY verdict:",
    "  - argument and return values, and per-line state: captured, never "
    "compared, and never fingerprinted",
    "  - timing, and the order threads ran in relative to each other",
    "  - the recorder's own footprint: deeper capture calls the program's "
    "__repr__ from inside the recorder's hooks, where the tracer suppresses "
    "itself, so an instrument that changes the program leaves no mark on the "
    "fingerprint at all",
    "  - the DATA the program read: only source files are hashed, so a "
    "config file, a fixture or a database can change between the runs "
    "freely and silently",
    "  - code that was never traced: the stdlib, site-packages and installed "
    "dependencies, anything outside the run's root (a PYTHONPATH module), "
    "and anything this run's own --include/--exclude filtered out",
    "  - what any subprocess did -- and a child started by a direct "
    "os.posix_spawn is not even noticed, because watching that event as well "
    "would double-count every subprocess.Popen",
    "  - a thread started by a C extension rather than through Python's own "
    "_thread module",
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
    look for it. Two orderings matter: this must run BEFORE the chdir (the
    path is relative to the invoking directory, not to the target's), and
    AFTER the environment snapshot the licence check compares -- the rewrite
    names the same directory in a different spelling, and reporting the
    tool's own bookkeeping as an environment change the user should worry
    about would be noise, not honesty.
    """
    sdir = os.environ.get("SENSORIUM_DIR")
    if sdir and not os.path.isabs(sdir):
        os.environ["SENSORIUM_DIR"] = str(Path(sdir).resolve())


# -- the world the rerun will run in ---------------------------------------
def _source_state(meta: dict) -> tuple[str, str | None]:
    """(status line, caveat or None), by comparing file CONTENTS.

    Deliberately not `git_dirty_hash`. That hash covers the output of
    `git status --porcelain` -- a list of paths and status letters -- so a
    file already dirty when the original ran can be edited arbitrarily,
    including the program being executed, without moving it. It would let
    the tool print "source: unchanged" over a rerun of different code, which
    is the one thing a licence gate must never do. Gitignored and
    out-of-repo files are outside it too.

    `source_hashes` is the digest of every file the ORIGINAL run interned
    traced code from, plus its entry target, taken at record time. Comparing
    those same paths' contents now is a claim the tool has actually
    verified. What it does NOT cover: code that was never traced -- stdlib,
    site-packages, anything the run's filters excluded -- and any file the
    RERUN reaches that the original never touched.

    A changed file is a WARNING, never a refusal: the fingerprint speaks to
    the execution path, not to file bytes, so an edit that leaves the causal
    stream untouched still earns an honest MATCH. What it costs is the right
    to assume the *values* were the same.
    """
    from sensorium.record import boot

    was = meta.get("source_hashes")
    if not isinstance(was, dict) or not was:
        return ("source: unverifiable -- the original trace records no "
                "source digests (recorded before they existed), so "
                "sensorium cannot tell whether the code changed",
                "the source could not be checked at all -- the original "
                "trace holds no file digests -- so nothing rules out an "
                "edit between the runs")
    # A file the recorder could not read has a None digest. Comparing it
    # against a None read now would make two failures agree and print
    # "unchanged" over a file nobody has ever hashed -- the same shape as
    # every other bug in this round: a check that did not run, reported as a
    # check that passed.
    unread = sorted(p for p, digest in was.items() if digest is None)
    if unread:
        names = ", ".join(Path(p).name for p in unread[:6])
        return (f"source: unverifiable -- {len(unread)} of {len(was)} "
                f"file(s) had no digest recorded ({names})",
                f"{len(unread)} source file(s) could not be checked "
                f"({names}) -- they were unreadable when the original was "
                f"recorded, so nothing rules out an edit between the runs")
    changed = [p for p, digest in sorted(was.items())
               if boot.hash_file(p) != digest]
    if not changed:
        return (f"source: unchanged ({len(was)} file(s) compared by "
                "content; data files, untraced code and installed "
                "dependencies are NOT covered -- see blind spots below)",
                None)
    shown = ", ".join(Path(p).name for p in changed[:6])
    if len(changed) > 6:
        shown += f", +{len(changed) - 6} more"
    return (f"source: CHANGED since the original run -- {len(changed)} of "
            f"{len(was)} file(s) differ by content: {shown}",
            f"{len(changed)} source file(s) CHANGED between the two runs "
            f"({shown}), so the rerun executed different code than the "
            f"recording did")


def _env_diff(was: dict, now: dict) -> list[str]:
    """Names of non-volatile variables whose values differ. Names only --
    values are never printed, because environments carry secrets."""
    keys = (set(was) | set(now)) - _VOLATILE_ENV
    return sorted(k for k in keys if was.get(k) != now.get(k))


def _env_state(meta: dict, env: dict) -> tuple[str, str | None]:
    """(status line, caveat or None) for the environment the rerun will get."""
    was = meta.get("env")
    if not isinstance(was, dict):
        return ("env: unverifiable -- the original trace records no "
                "environment to compare against",
                "the environment could not be checked at all, so nothing "
                "rules out the rerun getting different input through it")
    names = _env_diff(was, env)
    if not names:
        compared = len((set(was) | set(env)) - _VOLATILE_ENV)
        return (f"env: unchanged ({compared} variables compared; "
                f"{len(_VOLATILE_ENV)} volatile shell keys ignored)", None)
    shown = ", ".join(names[:8])
    if len(names) > 8:
        shown += f", +{len(names) - 8} more"
    return (f"env: CHANGED since the original run -- {len(names)} "
            f"variable(s) differ: {shown}   (names only)",
            f"{len(names)} environment variable(s) differ between the two "
            f"runs ({shown}); a program that reads them got different input")


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


def final_verdict(orig: Trace, new: Trace,
                  res: dict) -> tuple[str, str | None]:
    """(verdict, thread-divergence description or None).

    `compare()` decides on one thread and says exactly where it parted.
    This widens the answer to every recorded thread, because a worker that
    took a different path means the rerun was a different execution -- and
    reporting that as MATCH-with-a-note is how the previous version handed
    out a licence next to the words "this MATCH is about the worker".
    """
    if res["verdict"] != "MATCH":
        return res["verdict"], None
    threads = _thread_divergence(orig, new)
    return ("DIVERGED" if threads else "MATCH"), threads


# -- everything else that bears on the licence -----------------------------
def _output_text(trace: Trace) -> dict[str, str]:
    out: dict[str, str] = {}
    for _eid, stream, data in trace.output_chunks():
        out[stream] = out.get(stream, "") + data
    return out


def _clip(s: str, cap: int = 60) -> str:
    return repr(s if len(s) <= cap else s[:cap] + "...")


def _output_difference(orig: Trace, new: Trace) -> str | None:
    """The first place the two runs' captured output parts company.

    The only cross-check that can catch a recorder-induced change in the
    program: the fingerprint is blind to the instrument by construction (see
    OBSERVER EFFECT), but a `__repr__` that counts its own calls and prints
    the total shows up right here.
    """
    a, b = _output_text(orig), _output_text(new)
    for stream in sorted(set(a) | set(b)):
        was, now = a.get(stream, ""), b.get(stream, "")
        if was == now:
            continue
        wl, nl = was.splitlines(), now.splitlines()
        for i in range(max(len(wl), len(nl))):
            x = wl[i] if i < len(wl) else "(no more output)"
            y = nl[i] if i < len(nl) else "(no more output)"
            if x != y:
                return (f"the program's own captured {stream} differs, first "
                        f"at line {i + 1}: {_clip(x)} -> {_clip(y)}")
        return f"the program's own captured {stream} differs in whitespace"
    return None


def _licence_caveats(orig: Trace, new: Trace) -> list[str]:
    """Every reason this MATCH is not a statement about the whole run.

    Each entry is a signal sensorium actually checked and found. Anything it
    cannot check belongs in `_BLIND_SPOTS`, which is printed regardless.
    """
    out = []
    for label, trace in (("the original", orig), ("the rerun", new)):
        if trace.main_thread_basis() == "inferred":
            out.append(f"{label}'s compared thread is INFERRED, not recorded "
                       "-- it may not be the thread you think it is")
    threads = max(len(orig.fingerprints()), len(new.fingerprints()))
    if not threads:
        # Defence in depth: `compare()` refuses two empty streams before this
        # is reached for a real recording. It stays because "no fingerprint
        # was recorded" means the whole-thread comparison did not run, and a
        # check that did not run can never support the licence.
        out.append(
            "no per-thread fingerprint was recorded on either side, so the "
            "whole-thread comparison could not run at all")
    elif threads > 1:
        out.append(
            f"{threads} threads were recorded; each thread's own call shape "
            "matched, but the INTERLEAVING between them was never compared, "
            "and interleaving is what most concurrency bugs are made of")
    # A thread whose body is entirely stdlib runs no traced code, so it gets
    # no fingerprint row -- and once joined it is gone from `live_threads`
    # too, invisible on both counts while doing file I/O of its own. The
    # audit hook counts thread CREATION, which is the only one of the three
    # signals that is sound rather than "usually right".
    for label, trace in (("the original", orig), ("the rerun", new)):
        meta = trace.meta
        if "threads_started" not in meta or "live_threads" not in meta:
            out.append(
                f"{label} predates the thread bookkeeping this check reads, "
                "so how many threads it ran cannot be established -- absence "
                "of the record is not a record of absence")
            continue
        started = meta["threads_started"]
        if started:
            out.append(
                f"{label} started {started} thread(s) besides the main one. "
                "A thread that ran no traced code has no fingerprint to "
                "compare, and the order the threads ran in was never "
                "compared for any of them")
        live = meta["live_threads"]
        if live:
            out.append(
                f"{label} still had {len(live)} thread(s) running when "
                f"recording stopped ({', '.join(sorted(live)[:4])}); whatever "
                "they did after that point is in neither trace")
    if (orig.meta.get("audit_errors") or new.meta.get("audit_errors")):
        out.append(
            "the recorder's audit hook malfunctioned during one of the runs, "
            "so its record of subprocesses and threads is incomplete -- a "
            "short list there cannot be read as 'nothing was spawned'")
    diff = _output_difference(orig, new)
    if diff:
        out.append(diff)
    was, now = orig.meta.get("exit_status"), new.meta.get("exit_status")
    if was != now:
        out.append(f"the two runs ended differently: exit {was} originally, "
                   f"exit {now} on the rerun")
    for label, trace in (("the original", orig), ("the rerun", new)):
        kids = trace.meta.get("children") or []
        if kids:
            out.append(f"{label} spawned {len(kids)} subprocess(es), which "
                       "sensorium does not witness at all")
    return out


# -- the assessment --------------------------------------------------------
def assess(orig: Trace, new: Trace, res: dict, world_caveats=()) -> dict:
    """Everything the two traces support, decided once.

    `world_caveats` are findings about the world outside the traces (the
    source files, the environment) that only the caller can establish;
    everything else is derived here. Computed in one place because the
    verdict is printed, stamped into the new trace, and turned into an exit
    code -- and those three must never be able to disagree.
    """
    verdict, threads = final_verdict(orig, new, res)
    world = list(world_caveats)
    caveats = ((world + _licence_caveats(orig, new))
               if verdict == "MATCH" else [])
    licence = None
    if verdict == "MATCH":
        licence = "withheld" if caveats else "granted"
    return {"verdict": verdict, "threads": threads, "world": world,
            "caveats": caveats, "licence": licence}


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
        if res["verdict"] == "DIVERGED":
            db.set_meta(conn, "refocus_diverge_index", res["index"])
            db.set_meta(conn, "refocus_diverge_a", res["a_desc"])
            db.set_meta(conn, "refocus_diverge_b", res["b_desc"])
        elif res["verdict"] == "REFUSED":
            db.set_meta(conn, "refocus_refused_reasons", res["reasons"])
        if a["threads"]:
            db.set_meta(conn, "refocus_thread_divergence", a["threads"])
        if a["licence"]:
            db.set_meta(conn, "refocus_licence", a["licence"])
            db.set_meta(conn, "refocus_licence_reasons", a["caveats"])
        conn.commit()
    finally:
        conn.close()


def report(orig: Trace, new: Trace, res: dict, orig_name: str, new_name: str,
           a: dict) -> int:
    """Print the comparison and the verdict; return the exit code."""
    print_comparison(orig, new, res, orig_name, new_name)
    verdict, threads = a["verdict"], a["threads"]

    if res["verdict"] == "REFUSED":
        print("threads: not compared -- no verdict was issued")
        print(f"refocus verdict: REFUSED -- {new_name} was recorded and is "
              f"queryable, but it could NOT be verified against "
              f"{orig_name}: treat it as a separate, UNVERIFIED execution")
        # Stated here too: "on every verdict" has to include the verdict
        # that says nothing, or the sentence is not true.
        _print_blind_spots()
        return 2

    if threads:
        print(f"threads: DIVERGED -- {threads}")
    elif res["verdict"] != "MATCH":
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
        print(f"threads: {n} recorded fingerprint(s) compared, all "
              f"matching{tail}")
    else:
        print("threads: no per-thread fingerprints were recorded on either "
              "side -- there was nothing to compare beyond the stream above")

    if verdict == "DIVERGED":
        why = ("a thread other than the compared one took a different path"
               if threads else "the compared thread took a different path")
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

    print("refocus verdict: MATCH -- every recorded thread produced the "
          "identical CALL/RETURN/RAISE/HANDLED sequence")
    if a["caveats"]:
        print("licence: WITHHELD -- this MATCH is about call shape, and "
              "these checks say it is not a statement about the run as a "
              "whole:")
        for caveat in a["caveats"]:
            print(f"  - {caveat}")
    else:
        print("licence: answers from this trace are answers about the "
              "original run -- every signal sensorium can check agrees")
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
        return _refuse(orig_name, str(e))

    focus = _merged_focus(meta, args.focus)
    window = args.window if args.window is not None else meta.get("window")
    source, source_caveat = _source_state(meta)
    env_line, env_caveat = _env_state(meta, env)

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
    a = assess(orig, new, res, [c for c in (source_caveat, env_caveat) if c])
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

    problem = _refusal(meta)
    if problem:
        return _refuse(orig_name, problem)

    # Snapshot before the pin, pin before the chdir: see _pin_trace_store.
    env = dict(os.environ)
    _pin_trace_store()
    prev_cwd = os.getcwd()
    os.chdir(meta["cwd"])
    try:
        return _rerun_and_verify(args, orig, orig_name, meta, env)
    finally:
        os.chdir(prev_cwd)
