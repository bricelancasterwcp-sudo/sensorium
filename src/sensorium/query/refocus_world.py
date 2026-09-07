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
import hashlib
from pathlib import Path

from sensorium.query.caps import witness_gap
# The site-mark lookup, imported rather than rebuilt. `meta.sites` joins to
# `code_objects` on a workspace-relative path against an absolute one, and
# two implementations of that join are two ways for one trace to be read.
from sensorium.query.exceptions_rust import _marks as _site_marks
from sensorium.query.vocab import terms
from sensorium.store.reader import Trace

# A check that CANNOT RUN on this pair, because the recorder declares it
# does not produce what the check reads. Distinct from every other string in
# this file, and deliberately so: the caveats below are findings -- a signal
# that fired -- and these two are the absence of a signal to fire.
#
# The bug class they exist for is the one this whole file is arranged
# around, one step further on. `_output_difference` over two recordings that
# captured no output compares two EMPTY sets, finds them equal, and adds no
# caveat -- so a licence granted over a Rust pair silently claimed the
# observer-effect cross-check had passed, when it had never run. Naming the
# gap is the only honest answer; withholding the licence for it would be the
# opposite error, reporting a recorder's declared scope as evidence against
# the run.
#: The narrowest recorded source digest a comparison may rest on: 64 bits of
#: sha256, which is what `boot.hash_file` keeps. Anything shorter is reported
#: as unverifiable rather than compared.
_MIN_DIGEST = 16

UNVERIFIABLE_OUTPUT = "output: unverifiable (not recorded)"
UNVERIFIABLE_CHILDREN = "children: unverifiable (not witnessed)"
UNVERIFIABLE = (UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN)

#: The same two checks named for a line that has ALREADY said the word
#: "unverifiable" once -- `info`'s replay of the stamp. Each keeps its own
#: reason; only the repeated word goes. A name this table does not know is
#: printed exactly as it was stamped: an older reader must not rewrite the
#: words a later version wrote into a trace.
_SHORT_UNVERIFIABLE = {
    UNVERIFIABLE_OUTPUT: "output (not recorded)",
    UNVERIFIABLE_CHILDREN: "children (not witnessed)",
}


def unverifiable_line(checks) -> str | None:
    """`info`'s one line for the checks a pair could not run, or None.

    None both for a trace that names no such check and for one that predates
    the stamp: neither is "every check ran", and a line asserting that from
    an absent key would be exactly the reading `unverifiable_checks` exists
    to prevent, printed one command further on.
    """
    names = [_SHORT_UNVERIFIABLE.get(c, c) for c in checks or []]
    if not names:
        return None
    return "licence unverifiable: " + ", ".join(names)


def unverifiable_checks(orig: Trace, new: Trace) -> list[str]:
    """Which of the licence's checks this pair cannot run at all.

    Keyed on the CAPABILITY, never on the language: what makes the check
    impossible is the recorder's own declaration that it does not produce
    the record, and that is the same fact whichever recorder said it. A
    trace that declares the capability true, or that predates declarations
    entirely, is not in this state -- for those the caveats below still
    apply, because there the record's absence is a contradiction or an
    unknown rather than a scope.
    """
    out = []
    if any(t.declares("output") is False for t in (orig, new)):
        out.append(UNVERIFIABLE_OUTPUT)
    if any(t.declares("children") is False for t in (orig, new)):
        out.append(UNVERIFIABLE_CHILDREN)
    return out


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
def _still_hashes_to(path: str, digest: str) -> bool:
    """Whether `path`'s bytes still hash to the digest recorded for them.

    Compared at the WIDTH the recorder wrote, and that is the whole reason
    this is a function. Both recorders digest the same bytes with sha256 and
    write DIFFERENT amounts of it: `boot.hash_file` keeps the first 16 hex
    characters, `cargo-sensorium`'s wrapper writes all 64. A straight
    inequality against `hash_file`'s answer therefore read every Rust file
    as changed -- a false accusation of the most expensive kind, since it
    withholds the licence AND tells the reader their source moved under
    them. A prefix comparison is exact for each recorder, because a prefix
    of a digest is a digest of the same bytes.

    Unreadable now is NOT a match: a file that cannot be hashed has not been
    shown to be unchanged, and the caller reports it among the changed. The
    recorded digest's own width is the caller's business (`_MIN_DIGEST`):
    every digest reaching here has already been shown wide enough to
    identify a file.
    """
    try:
        with open(path, "rb") as fh:
            now = hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return False
    return isinstance(digest, str) and now[:len(digest)] == digest


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
    # A digest too narrow to identify a file matches almost anything under a
    # prefix comparison -- `""` matches EVERY file -- so it is reported as a
    # check that could not run, never as one that passed. The floor is the
    # narrowest width this project's own recorders write (`boot.hash_file`
    # keeps 16 hex characters; `cargo-sensorium` writes all 64), so no trace
    # either of them produced is refused by it.
    short = sorted(p for p, digest in was.items()
                   if digest is not None
                   and (not isinstance(digest, str)
                        or len(digest) < _MIN_DIGEST))
    if short:
        names = ", ".join(Path(p).name for p in short[:6])
        return (f"source: unverifiable -- {len(short)} of {len(was)} "
                f"file(s) recorded a digest too short to identify their "
                f"contents ({names})",
                f"{len(short)} source file(s) could not be checked "
                f"({names}) -- their recorded digest is under "
                f"{_MIN_DIGEST} hex characters, which would match files "
                "this run never saw, so nothing rules out an edit between "
                "the runs", None)
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
               if not _still_hashes_to(p, digest)]
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


def harness_threads(trace: Trace) -> set[int]:
    """The threads this trace's RECORDER started, not the program.

    `cargo test` runs every `#[test]` function on a thread libtest spawns
    for it, so a `cargo test` trace always carries one non-main thread the
    program did not start -- and the untraced-thread caveat below fired on
    all 61 pairs of E4 for that reason and no other (E4 section 5.2, design
    2026-09-07 R1). A clause that cannot NOT fire is not a finding, and the
    precedent for taking it out is one this licence already sets: the
    recorder's own environment variables are excluded from the environment
    comparison, by name.

    A harness thread is a NON-MAIN thread whose ROOT frame's site the
    manifest marks `#[test]`. The root is what makes the rule sound in both
    directions. A thread the test itself spawns enters through a closure or
    an ordinary fn -- `sensorium-transform` marks every closure site
    `test: false` -- so its root is never a test fn and it is never
    excluded; and a test fn called from somewhere deeper on another thread
    says nothing about who started that thread, so a mark below the root
    excludes nothing either.

    Empty for a recorder whose traces carry no site marks at all -- every
    Python trace -- and empty unless the main thread is a RECORDED fact.
    `main_thread_id()` never reports "the trace does not say": it falls
    back to the thread of whichever event got id 1, which under `--focus`
    filtering or ordinary scheduling jitter can name a worker. Subtracting
    on a guess is the one way this rule can take a thread out of a count it
    was never in, so `main_thread_basis()` -- "recorded", "inferred", or
    None for a trace with no events at all -- is what the exclusion rests
    on. Neither empty case is a harness thread that went unfound: both
    leave every count exactly as it was, the direction that claims less.
    """
    if trace.main_thread_basis() != "recorded":
        return set()
    main = trace.main_thread_id()
    marks = _site_marks(trace.meta)
    found = set()
    for root in trace.roots():
        if root.thread_id == main:
            continue
        code = trace.code(root.code_id)
        if marks.get((code.qualname, code.file)) == "test":
            found.add(root.thread_id)
    return found


def harness_exclusion(trace: Trace) -> tuple[int, str]:
    """How many threads this recorder started itself, and the clause that
    NAMES them wherever one of its thread counts is printed.

    The clause travels with the count on purpose. A subtraction that showed
    only its result would put a smaller number where a larger one used to
    be with nothing on the line to say why -- a number that looks measured
    standing in for a fact that was removed, which is this project's own
    bug class one level up.
    """
    phrase = terms(trace).harness_thread
    if phrase is None:
        return 0, ""
    n = len(harness_threads(trace))
    if not n:
        return 0, ""
    return n, f" and {n} harness thread{'' if n == 1 else 's'} ({phrase})"


def harness_note(trace: Trace) -> str:
    """The harness exclusion as a clause of its OWN, for a line whose counts
    it is not one of.

    `harness_exclusion`'s clause follows a count and joins it (" and 1
    harness thread ..."); on a line that counts what was NOT compared, the
    same words would say the harness thread is one of them. Same fact, same
    vocabulary, a grammatical slot that does not lie. Empty where the
    recorder starts no thread of its own.
    """
    n, _clause = harness_exclusion(trace)
    if not n:
        return ""
    plural, verb = ("", "is") if n == 1 else ("s", "are")
    return (f"; {n} harness thread{plural} ({terms(trace).harness_thread}) "
            f"{verb} not among these counts")


def compared_threads(trace: Trace) -> set[int]:
    """The threads whose call shape this trace actually had compared.

    NOT `fingerprints()`. The Rust converter writes exactly ONE thread row
    -- the main thread's -- and routes every other thread's events into
    `task_fingerprints` (`convert/frames.rs`), so a count of thread rows
    reported every non-main Rust thread as one that "ran no traced code,
    left no fingerprint, and was NOT compared" while its whole call shape
    had been compared, on the very thread the code under test runs on.

    A task row is followed back to its thread through the `tasks` table
    rather than assumed to be one: in Python a task is an asyncio task and
    many of them share a thread, so adding task rows to a thread count
    would be the same error facing the other way. A task whose `tasks` row
    is missing names no thread and adds none -- that reports MORE
    uncompared threads, which is the direction that claims less.
    """
    threads = set(trace.fingerprints())
    thread_of = {task.id: task.thread_id for task in trace.tasks()}
    for task_id in trace.task_fingerprints():
        thread = thread_of.get(task_id)
        if thread is not None:
            threads.add(thread)
    return threads


def uncompared_threads(trace: Trace) -> int | None:
    """How many threads this trace records STARTING and did not compare.

    None when it does not record how many threads it started: absence of
    the record is not a record of absence, and a count derived from a
    missing key is the one number a line about what went uncompared must
    never print.

    Harness threads are the recorder's own, so they are not among the
    program's uncompared threads -- but only the ones NOT already compared
    are subtracted, or a harness thread whose stream WAS compared (the
    ordinary case: it is the thread the `#[test]` fn runs on) would come
    off the count twice. Clamped at zero rather than printed negative: a
    thread can leave a fingerprint without the audit hook counting its
    creation -- a C extension's thread in Python -- and a negative here
    would be arithmetic across two populations reported as a measurement.
    """
    started = trace.meta.get("threads_started")
    if started is None:
        return None
    compared = compared_threads(trace)
    unfound_harness = harness_threads(trace) - compared
    return max(started - len(compared - {trace.main_thread_id()})
               - len(unfound_harness), 0)


def _licence_caveats(orig: Trace, new: Trace) -> list[str]:
    """Every reason this MATCH is not a statement about the whole run.

    Each entry is a signal sensorium actually checked and found. Anything it
    cannot check belongs in `_BLIND_SPOTS`, which is printed regardless.
    """
    out = []
    # Decided once, up front: two of the checks below cannot run on this
    # pair at all, and both the branch that would have run them and the
    # branch that would have reported their absence as a finding have to
    # read the same answer.
    unverifiable = unverifiable_checks(orig, new)
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
        # The recorder's own harness threads come OUT of this count and are
        # named in the same sentence (R1). `> 0` and not truthiness: a
        # harness thread has a spool of its own, so the converter's count
        # already includes it and the difference cannot go below zero on a
        # trace this project wrote -- and a hand-built one that says
        # otherwise gets no caveat rather than a negative count printed as
        # though it had been measured.
        harness, harness_clause = harness_exclusion(trace)
        started = meta["threads_started"] - harness
        if started > 0:
            out.append(
                f"{label} started {started} thread(s) besides the main "
                f"one{harness_clause}. "
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
    # NOT consulted when the pair declares no output capture. Two empty
    # captures are equal, and this function returning None over them is the
    # difference between "the cross-check passed" and "there was nothing to
    # cross-check" -- reported instead as UNVERIFIABLE_OUTPUT below.
    if UNVERIFIABLE_OUTPUT not in unverifiable:
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
        # The declared-false case is UNVERIFIABLE_CHILDREN, reported ONCE
        # for the pair below rather than once per side: the marker names no
        # side, and saying it twice would read as two findings.
        if UNVERIFIABLE_CHILDREN not in unverifiable and (
                "spawn_syscalls" not in meta):
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
    # Last, and reported here so that every reader of the licence caveats
    # sees them. `refocus_rust` takes them back out of the WITHHOLDING
    # decision -- a check that could not run is not a finding against the
    # pair -- and prints and stamps them separately; a caller that reads
    # this list and nothing else is still told which checks did not run.
    out.extend(unverifiable)
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
    # The noun is the recorder's, for the reason `vocab.py` exists: on a
    # Rust trace the row is outside the test and spawned threads, and
    # `asyncio` there names a runtime that never ran. `scope` decides
    # WHETHER the clause appears (one derivation, read once); `terms`
    # decides what it calls the units.
    outside = f" outside any {terms(new).task_noun}" if scope else ""
    # The thread clause is a PROVENANCE claim -- "through Python's own
    # threading/_thread" says how the threads this run did not start would
    # have come to exist -- so it comes from the trace's own vocabulary
    # table, for the reason `vocab.py` exists at all. The Python string is
    # unchanged, character for character: `PYTHON.thread_origin` IS this
    # clause, moved.
    # ...and where the recorder started a thread of its own, the clause
    # NAMES it instead of making the provenance claim: design 2026-09-07
    # section 2's line, verbatim. What a granted licence rests on is a
    # bounded list, so the harness thread appears on it as an exclusion
    # rather than being dropped from a sentence that then reads as though
    # only the main thread ever ran.
    harness, harness_clause = harness_exclusion(new)
    thread_fact = (
        f"no thread started besides the main one{harness_clause}"
        if harness else
        f"no thread started besides the main one "
        f"{terms(new).thread_origin}, and none left running when recording "
        "stopped")
    facts = [
        f"identical call shape across {len(fps)} compared fingerprint(s), "
        f"holding {events} causal event(s){outside}",
        thread_fact,
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
    #
    # The capability clause is the same rule stated where it cannot be
    # missed: a recorder that DECLARES it does not witness children can
    # never support this fact, whatever `spawn_witnessing` happens to say.
    # Today no such trace carries the key, so the clause changes no output;
    # it is here because "the pair cannot vouch for this" must not depend on
    # a second key agreeing.
    if (_spawn_witnessed(orig.meta) and _spawn_witnessed(new.meta)
            and UNVERIFIABLE_CHILDREN not in unverifiable_checks(orig, new)):
        facts.append(
            "no child process witnessed, by any mechanism sensorium watches")
    return facts
