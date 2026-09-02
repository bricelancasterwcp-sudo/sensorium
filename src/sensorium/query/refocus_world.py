"""The world the two runs happened in, and what it lets the verdict claim.

Split out of `refocus_cmd` along the seam the material has: everything here
establishes FACTS -- about the source tree, the process environment, the
program's own output, the threads and children each run started -- and
nothing here decides a verdict or prints one. `refocus_cmd` owns the verdict,
the assessment that ties the facts to it, and the report; it calls in here
for the evidence. The two halves were one 1004-line file, over this
project's 800-line ceiling.

A verdict is about CALL SHAPE. A licence is about the whole run, and it is
withheld on every signal below that fired -- and just as firmly on every one
that could not RUN, because the granted sentence claims they all agreed.
That asymmetry is the reason these checks are worth their length: each one
returns a caveat when it finds something AND a caveat when it could not
look, and only a third, positive answer when it actually verified something.

`_UNCOMPARED_ENV` is the one deliberate hole, and it is named rather than
counted for the same reason.
"""
from pathlib import Path

from sensorium.query.caps import witness_gap
from sensorium.store.reader import Trace


# Shell bookkeeping that differs between any two consecutive commands and
# says nothing about the program. Deliberately tiny: every name here is a
# name refocus has stopped checking.
_UNCOMPARED_ENV = frozenset({
    "_",            # bash: the previous command's last argument
    "OLDPWD",
    "PWD",          # os.chdir does not update it; it names the calling shell
    "SHLVL",
    # Not shell bookkeeping: the recorder's OWN variable, which
    # `_pin_trace_store` rewrites from a relative path to the absolute form
    # of the same directory before the target runs. The environment compared
    # here is snapshotted AFTER that rewrite, so it is the environment the
    # program actually executed under -- and this key is excluded rather
    # than reported as a change the world made, because the change is ours.
    # A program that reads SENSORIUM_DIR therefore goes unchecked, which is
    # exactly why the name is printed rather than hidden behind a count.
    "SENSORIUM_DIR",
})
# COLUMNS and LINES were on this list and are not any more. They are terminal
# geometry, which most shells do not export at all and which changes only on
# a resize -- so ignoring them bought almost nothing, and cost a real hole: a
# program that sizes its output by COLUMNS wrote 80 bytes in one run and 9000
# in the other under a full licence. Every name above is a name this tool has
# stopped checking, so the list stays as short as it can be, and the names
# themselves are printed beside the count rather than left as "5 keys".


# -- the world the rerun will run in ---------------------------------------
def _source_state(meta: dict) -> tuple[str, str | None, str | None]:
    """(status line, caveat or None, verified fact or None), by CONTENTS.

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
                "edit between the runs", None)
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
                f"recorded, so nothing rules out an edit between the runs",
                None)
    changed = [p for p, digest in sorted(was.items())
               if boot.hash_file(p) != digest]
    if not changed:
        return (f"source: unchanged ({len(was)} file(s) compared by "
                "content; data files, untraced code and installed "
                "dependencies are NOT covered -- see blind spots below)",
                None,
                f"{len(was)} source file(s) unchanged by content")
    shown = ", ".join(Path(p).name for p in changed[:6])
    if len(changed) > 6:
        shown += f", +{len(changed) - 6} more"
    return (f"source: CHANGED since the original run -- {len(changed)} of "
            f"{len(was)} file(s) differ by content: {shown}",
            f"{len(changed)} source file(s) CHANGED between the two runs "
            f"({shown}), so the rerun executed different code than the "
            f"recording did", None)


def _env_diff(was: dict, now: dict) -> list[str]:
    """Names of non-volatile variables whose values differ. Names only --
    values are never printed, because environments carry secrets."""
    keys = (set(was) | set(now)) - _UNCOMPARED_ENV
    return sorted(k for k in keys if was.get(k) != now.get(k))


def _env_state(meta: dict, env: dict) -> tuple[str, str | None, str | None]:
    """(status line, caveat, verified fact) for the rerun's environment.

    The ignored keys are NAMED, not counted. "4 volatile keys ignored" is
    not something a reader can judge; `COLUMNS` sitting silently on that
    list is how a program that sized its output by terminal width earned a
    full licence while writing 80 bytes one run and 9000 the next.
    """
    was = meta.get("env")
    if not isinstance(was, dict):
        return ("env: unverifiable -- the original trace records no "
                "environment to compare against",
                "the environment could not be checked at all, so nothing "
                "rules out the rerun getting different input through it",
                None)
    names = _env_diff(was, env)
    if not names:
        compared = len((set(was) | set(env)) - _UNCOMPARED_ENV)
        ignored = ", ".join(sorted(_UNCOMPARED_ENV))
        return (f"env: unchanged ({compared} variables compared; not "
                f"compared: {ignored})", None,
                f"{compared} environment variable(s) compared and unchanged "
                f"in the environment the rerun executed under; not compared: "
                f"{ignored}")
    shown = ", ".join(names[:8])
    if len(names) > 8:
        shown += f", +{len(names) - 8} more"
    return (f"env: CHANGED since the original run -- {len(names)} "
            f"variable(s) differ: {shown}   (names only)",
            f"{len(names)} environment variable(s) differ between the two "
            f"runs ({shown}); a program that reads them got different input",
            None)


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
            legacy = ("predates the thread bookkeeping this check reads, "
                      "so how many threads it ran cannot be established -- "
                      "absence of the record is not a record of absence")
            gap = witness_gap(trace, "threads", "thread", legacy)
            joiner = "'s" if trace.declares("threads") is not None else ""
            out.append(f"{label}{joiner} {gap}")
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
    output_undeclared = False
    for label, trace in (("the original", orig), ("the rerun", new)):
        if trace.declares("output") is False:
            output_undeclared = True
            out.append(
                f"the program's output was not recorded on {label} (recorder "
                f"{trace.recorder} declares output: false), so the "
                "observer-effect cross-check did not run")
    if not output_undeclared:
        diff = _output_difference(orig, new)
        if diff:
            out.append(diff)
    was, now = orig.meta.get("exit_status"), new.meta.get("exit_status")
    if was != now:
        out.append(f"the two runs ended differently: exit {was} originally, "
                   f"exit {now} on the rerun")
    for label, trace in (("the original", orig), ("the rerun", new)):
        meta = trace.meta
        # Two independent observations of the same thing, reported as ONE
        # caveat. `subprocess.Popen` nests a spawn syscall, so a single list
        # would count every subprocess twice; two lists that are never summed
        # avoid that, and either being non-empty answers the only question
        # asked here -- was a child witnessed. Neither being non-empty means
        # only that none was NOTICED, never that none ran.
        if "spawn_syscalls" not in meta:
            legacy = ("predates the spawn-syscall record, so a child "
                      "started through multiprocessing or a bare "
                      "posix_spawn would leave no trace here -- absence of "
                      "the record is not a record of absence")
            gap = witness_gap(trace, "children", "spawn-syscall", legacy)
            joiner = "'s" if trace.declares("children") is not None else ""
            out.append(f"{label}{joiner} {gap}")
        kids = meta.get("children") or []
        spawns = meta.get("spawn_syscalls") or 0
        if kids or spawns:
            named = (f"{len(kids)} named" if kids else "none named")
            out.append(
                f"{label} started at least one child process ({named}, "
                f"{spawns} low-level spawn syscall(s) seen); sensorium does "
                "not witness what any child did")
    return out


# -- what a granted licence rests on ---------------------------------------
def _spawn_witnessed(meta: dict) -> bool:
    """Whether this trace's interpreter could witness a `multiprocessing`
    spawn at all.

    False on CPython < 3.14 -- where no parent-side audit event fires for a
    spawn/forkserver child, so `spawn_syscalls == 0` cannot be read as "none
    ran" -- and on a trace recorded before the capability was noted. The
    recorder stamps the answer at record time (`boot._SPAWN_WITNESSED`).
    """
    return bool(meta.get("spawn_witnessing"))


def _verified_facts(orig: Trace, new: Trace, scope: str) -> list[str]:
    """What a granted licence is actually based on, stated positively.

    `scope` is `refocus_cmd._thread_scope`'s answer, passed in rather than
    recomputed: the same string goes into the assessment dict, and one
    derivation read twice is one derivation that can be read two ways.

    The granted line used to read "every signal sensorium can check agrees",
    which invites the reader to treat the check-list as complete -- and every
    review round has falsified that reading by finding another path through
    it. Naming the concrete, bounded findings instead cannot be falsified by
    a mechanism nobody has thought of yet: it claims these things and no
    others.
    """
    fps = new.fingerprints()
    # HOW MUCH was compared, not just how many rows. Under the per-task
    # basis a thread row covers only what ran outside every task, and the
    # commonest async shape -- an entry that does nothing but
    # `asyncio.run` -- leaves it covering the module frame, or nothing at
    # all. "Identical call shape across 1 compared fingerprint(s)" over two
    # events of scaffolding reads as a statement about the run; the count
    # and the scope are what make it a bounded claim instead.
    events = sum(c for _h, c in fps.values())
    outside = " outside any asyncio task" if scope else ""
    facts = [
        f"identical call shape across {len(fps)} compared fingerprint(s), "
        f"holding {events} causal event(s){outside}",
        "no thread started besides the main one through Python's own "
        "threading/_thread, and none left running when recording stopped",
    ]
    # Stated only when there were tasks: a run with none must not be given
    # a fact about zero of them, and the count is the rerun's rows because
    # a stream present on one side only is a divergence, never a MATCH.
    # Spec D6's sentence in full -- the ordering clause travels with the
    # claim, because "compared by content" is only bounded by what content
    # means here.
    n_tasks = len(new.task_fingerprints())
    if n_tasks:
        facts.insert(1, f"{n_tasks} task stream(s) compared by content; "
                        "the ordering between tasks is not compared")
    # The child-witnessing claim rests on an audit event only CPython 3.14+
    # raises for a multiprocessing/forkserver spawn. If EITHER run was recorded
    # where that signal does not exist, the pair cannot vouch that no such child
    # ran, so the line is omitted rather than asserted -- the blind-spot block
    # printed on every verdict still states categorically that no child process
    # is covered, so the gap is stated, not hidden.
    if _spawn_witnessed(orig.meta) and _spawn_witnessed(new.meta):
        facts.append(
            "no child process witnessed, by any mechanism sensorium watches")
    return facts
