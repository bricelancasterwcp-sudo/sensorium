"""The honesty notes `diff` prints beside a verdict, and never instead of one.

Split from `diff_cmd` at that file's 800-line ceiling -- one command's
internals in two files, not two modules with two surfaces. Everything here
answers the same question: what does a MATCH or a DIVERGED on ONE thread's
stream not cover? Which thread was compared and whether that identification
was recorded or inferred; how many other threads the run had; and whether
the two traces are of the same command at all.

None of these change the verdict. All of them must survive to the screen: a
MATCH with the note missing is a stronger claim than the comparison made.
"""
from sensorium.query.caps import witness_gap
from sensorium.query.vocab import terms
from sensorium.store.reader import Trace


_BASIS_LABEL = {"recorded": "recorded main thread",
               "inferred": "INFERRED main thread -- see note below"}


def _thread_header(label: str, name: str, trace: Trace) -> str:
    """One line naming exactly which thread this side's causal stream came
    from, and whether that identification is a recorded fact or a guess --
    never just "main fp ..." with the reader left to assume it is right."""
    fps = trace.fingerprints()
    mtid = trace.main_thread_id()
    if mtid is None:
        return f"{label} {name}: threads {len(fps)}  compared: - (no events)"
    basis = trace.main_thread_basis()
    fp = fps.get(mtid, (None, None))[0]
    return (f"{label} {name}: threads {len(fps)}  "
            f"compared: t{mtid} [{_BASIS_LABEL[basis]}]  fp {fp or '-'}")


def _argv_note(trace_a: Trace, trace_b: Trace) -> list[str]:
    """Comparing two traces of different commands is comparing unrelated
    programs; whatever else is compared, that must be said."""
    aa, bb = trace_a.meta.get("argv"), trace_b.meta.get("argv")
    if aa == bb:
        return []
    return [f"different commands recorded -- A: {' '.join(aa or [])!r}"
            f"  B: {' '.join(bb or [])!r}"]


def safety_notes(trace_a: Trace, trace_b: Trace) -> list[str]:
    """Honesty notes that do not change the verdict but must never be
    silently dropped: a compared thread identified by inference rather than
    the recorder's own record may not be the thread a reader assumes, a
    MATCH on one thread is not a MATCH on the whole run if either side has
    other threads, and comparing two traces of different commands is
    comparing unrelated programs."""
    notes = _argv_note(trace_a, trace_b)
    for label, trace in (("A", trace_a), ("B", trace_b)):
        if trace.main_thread_basis() == "inferred":
            notes.append(
                f"{label}'s compared thread is INFERRED, not recorded: "
                "this trace predates main_thread_ident, so the thread of "
                "whichever event happened to get id 1 stands in for it -- "
                "under --focus/--window filtering, or if a worker thread's "
                "first traced event landed before the main thread's own, "
                "that stand-in can be a WORKER thread; re-record to get an "
                "exact answer")
        notes.extend(_thread_notes(label, trace))
    return notes


def _thread_notes(label: str, trace: Trace) -> list[str]:
    """How many threads this side ran, counted the way `refocus` counts them.

    The count here used to be `len(fingerprints())`, which answers a
    different question: a worker whose body is entirely stdlib runs no traced
    code, so it leaves no fingerprint row at all. Two runs of exactly that
    program -- a stdlib-only worker writing 4 bytes in one run and 20 in the
    other -- gave `diff` `threads 1` and a clean MATCH with no note, while
    `refocus` withheld its licence on the same pair citing "started 1
    thread(s) besides the main one". One trace, two commands, two answers.

    The audit hook's count of thread CREATION is the sound signal; a
    fingerprint row is the one that can be missing. Both are reported,
    because they are two different facts and neither subsumes the other: a
    thread started by a C extension without going through `_thread` is
    counted by neither, but if it runs traced Python it still leaves a
    fingerprint.
    """
    fps = len(trace.fingerprints())
    meta = trace.meta
    if "threads_started" not in meta:
        legacy = (f"predates the recorder's thread bookkeeping, so how "
                  f"many threads it ran cannot be established -- {fps} left "
                  "a fingerprint, and only the thread named above was "
                  "compared; absence of the record is not a record of "
                  "absence")
        gap = witness_gap(trace, "threads", "thread", legacy)
        # "A recorder X declares ..." reads like an indefinite article; the
        # legacy sentence already opens with "predates" and needs no joiner.
        joiner = "'s" if trace.declares("threads") is not None else ""
        return [f"{label}{joiner} {gap}"]
    started = meta["threads_started"]
    if not started and fps <= 1:
        return []
    return [f"{label} recorded more than one thread: {started} started "
            f"{terms(trace).thread_origin}, {fps} left a "
            "fingerprint; only the thread named above was compared -- a "
            "MATCH here is not a MATCH on the whole run, and a thread that "
            "ran no traced code leaves no fingerprint to compare at all"]
