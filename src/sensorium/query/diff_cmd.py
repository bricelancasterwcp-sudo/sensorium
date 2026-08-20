"""Compare two runs' causal streams and pinpoint the first divergence.

Causal stream = (file, qualname, kind) per CAUSAL_KINDS event (CALL / RETURN
/ RAISE / HANDLED) on one thread. Values, timing, and LINE events are
excluded by construction (see fingerprint.py), so a MATCH means the same
*shape* of execution -- the same sequence of calls, returns, raises and
handles -- not that the two runs are "the same" in every sense. It says
nothing about argument values, return values, wall-clock timing, per-line
state, or any thread other than the one compared.

WHICH THREAD "THE ONE COMPARED" ACTUALLY IS
--------------------------------------------
`Trace.main_thread_id()` prefers a value the recorder writes at boot time
(`meta["main_thread_ident"]`); traces recorded before that key existed fall
back to "the thread of whichever event got id 1", a heuristic that a
worker thread starting before the main thread's own first *traced* event
(under `--focus`/`--window` filtering, or ordinary scheduling jitter) can
silently defeat. `Trace.main_thread_basis()` says which case a trace is in
-- `"recorded"` or `"inferred"` -- and `diff` reads it: the header names the
actual thread id compared and its basis, a MATCH's own verdict line only
says "the main thread" when both sides are `"recorded"`, and an inferred
side gets an explicit note rather than a silent guess dressed as a fact.

REFUSAL, NOT A HEDGE
--------------------
A run whose recording died mid-flight (killed process, failed `install()`)
has a causal stream that may simply STOP -- not because the program took a
different path, but because nothing after that point was ever recorded.
Comparing against it with the ordinary algorithm would report DIVERGED at
the truncation point: a confident, false claim that the two programs took
different paths, when the truth is "this trace has nothing to say past
here." `meta["incomplete"]` marks exactly this.

`meta["late_writes"]` is a related, quieter hazard: it counts writes that
arrived after the database sealed and is a LOWER BOUND (a live thread that
never got to flush its tail is not counted at all). A non-zero value means
events are missing from the stream -- possibly causal ones -- so a verdict
against that trace is unsafe for the same reason.

A THIRD WAY TO HAVE NOTHING TO SAY
-----------------------------------
Two EMPTY causal streams are also equal, and the ordinary algorithm reports
MATCH for them with exactly the confidence it reports MATCH for a thousand
matching events. That is reachable without any damage to the recording at
all: a target that resolves outside the run's root (reached through `..`, or
an installed console script), or `--include`/`--exclude` that match nothing,
records a complete, healthy trace of zero traced events. A verdict over
nothing is not a verdict, so it is refused too. One empty side is a
different matter -- that is a real difference between the two runs, and
stays DIVERGED.

`compare()` therefore has three possible verdicts, not two: MATCH, DIVERGED,
and REFUSED. REFUSED means "no verdict could be issued" -- it is the honest
alternative to guessing. This is deliberately load-bearing for `refocus`,
which reuses `compare()` unchanged: a refocus built on an incomplete, lossy,
or empty recording must refuse exactly the same way, so the check lives here
once rather than being re-implemented (and possibly forgotten) at each call
site.
"""
from sensorium import paths
from sensorium.store.reader import Trace

CAUSAL = ("CALL", "RETURN", "RAISE", "HANDLED")


def first_divergence(a: list, b: list) -> int | None:
    """Index of the first element where `a` and `b` differ on (file,
    qualname, kind) -- the leading three slots of each causal-stream tuple;
    a trailing event id is ignored if present. `None` means one is a prefix
    of the other and both prefixes are equal in length (i.e. truly
    identical); otherwise, if lengths differ with no earlier mismatch, the
    index returned is the length of the shorter one (where it ran out)."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x[:3] != y[:3]:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def _desc(step) -> str:
    file, qual, kind, eid = step
    return f"e{eid} {kind:<7} {qual}  ({file})"


def _unsafe_reasons(trace: Trace, label: str) -> list[str]:
    """Why `trace` (labelled A or B) must not be handed a MATCH/DIVERGED
    verdict. Empty means the trace's causal stream is safe to trust."""
    m = trace.meta
    reasons = []
    if m.get("incomplete"):
        reasons.append(
            f"{label} is INCOMPLETE: recording ended without a finalize "
            "pass (process killed mid-record, or install() failed) -- its "
            "causal stream can stop at any point with no signal that it "
            "did, so a MATCH or DIVERGED verdict against it would be a "
            "confident false claim, not an approximation")
    late = m.get("late_writes", 0)
    if late:
        reasons.append(
            f"{label} dropped >={late} trace write(s) after its database "
            "sealed (late_writes is a LOWER BOUND -- a thread that never "
            "got to flush its tail is not counted at all): events, "
            "possibly causal ones, are missing from its stream, so a "
            "verdict against it is unsafe for the same reason as an "
            "incomplete trace")
    return reasons


def _refused(reasons: list[str]) -> dict:
    return {"verdict": "REFUSED", "index": None, "a_event": None,
            "b_event": None, "a_desc": None, "b_desc": None,
            "reasons": reasons, "a_stream": None, "b_stream": None}


def compare(trace_a: Trace, trace_b: Trace) -> dict:
    """Compare the main-thread causal streams of two traces.

    Returns a dict with `verdict` in {"MATCH", "DIVERGED", "REFUSED"}.

    MATCH / DIVERGED also carry `index`, `a_event`, `b_event`, `a_desc`,
    `b_desc` (all `None` on MATCH; `index` is the divergence position and
    the rest describe the two sides' next step on DIVERGED), plus the full
    `a_stream` / `b_stream` used, for callers that want more context.

    REFUSED means no verdict could be issued, and comes in two shapes that
    share one contract (`reasons` says which, everything else is `None`):
    the streams could not be TRUSTED, so they were never read; or they were
    read and held nothing to compare. Both are the honest alternative to a
    confident answer -- the second one because two empty streams are equal,
    and calling that MATCH is a verdict about nothing.
    """
    reasons = _unsafe_reasons(trace_a, "A") + _unsafe_reasons(trace_b, "B")
    if reasons:
        return _refused(reasons)
    sa = trace_a.causal_stream()
    sb = trace_b.causal_stream()
    if not sa and not sb:
        # Two empty streams are equal, and `first_divergence` would duly
        # report MATCH -- a verdict about nothing, delivered with the same
        # confidence as a verdict about a thousand events. One empty side is
        # different: that is a real, reportable difference between the runs,
        # and stays DIVERGED.
        return _refused([
            "neither trace recorded a single causal event on the compared "
            "thread, so there was nothing to compare. A MATCH here would be "
            "a verdict about nothing. This usually means the target's code "
            "was never traced at all: it resolves outside the run's root "
            "(a target reached through `..`, or an installed console "
            "script), or --include/--exclude filtered everything out"])
    i = first_divergence(sa, sb)
    if i is None:
        return {"verdict": "MATCH", "index": None, "a_event": None,
                "b_event": None, "a_desc": None, "b_desc": None,
                "reasons": [], "a_stream": sa, "b_stream": sb}
    a_step = sa[i] if i < len(sa) else None
    b_step = sb[i] if i < len(sb) else None
    return {
        "verdict": "DIVERGED",
        "index": i,
        "a_event": a_step[3] if a_step else None,
        "b_event": b_step[3] if b_step else None,
        "a_desc": _desc(a_step) if a_step else "(stream ended)",
        "b_desc": _desc(b_step) if b_step else "(stream ended)",
        "reasons": [],
        "a_stream": sa, "b_stream": sb,
    }


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


def safety_notes(trace_a: Trace, trace_b: Trace) -> list[str]:
    """Honesty notes that do not change the verdict but must never be
    silently dropped: a compared thread identified by inference rather than
    the recorder's own record may not be the thread a reader assumes, a
    MATCH on one thread is not a MATCH on the whole run if either side has
    other threads, and comparing two traces of different commands is
    comparing unrelated programs."""
    notes = []
    aa, bb = trace_a.meta.get("argv"), trace_b.meta.get("argv")
    if aa != bb:
        notes.append(
            f"different commands recorded -- A: {' '.join(aa or [])!r}"
            f"  B: {' '.join(bb or [])!r}")
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
        return [f"{label} predates the recorder's thread bookkeeping, so how "
                f"many threads it ran cannot be established -- {fps} left a "
                "fingerprint, and only the thread named above was compared; "
                "absence of the record is not a record of absence"]
    started = meta["threads_started"]
    if not started and fps <= 1:
        return []
    return [f"{label} recorded more than one thread: {started} started "
            f"through Python's own threading/_thread, {fps} left a "
            "fingerprint; only the thread named above was compared -- a "
            "MATCH here is not a MATCH on the whole run, and a thread that "
            "ran no traced code leaves no fingerprint to compare at all"]


def print_comparison(trace_a, trace_b, res, name_a, name_b, context=3) -> None:
    print(_thread_header("A", name_a, trace_a))
    print(_thread_header("B", name_b, trace_b))
    for note in safety_notes(trace_a, trace_b):
        print(f"note: {note}")
    if res["verdict"] == "REFUSED":
        print("verdict: REFUSED -- cannot issue a MATCH/DIVERGED verdict")
        for reason in res["reasons"]:
            print(f"  {reason}")
        return
    if res["verdict"] == "MATCH":
        n = len(res["a_stream"])
        exact = (trace_a.main_thread_basis() == "recorded"
                and trace_b.main_thread_basis() == "recorded")
        where = "the main thread" if exact else "the thread named above"
        print(f"verdict: MATCH -- identical causal streams ({n} events): "
              "the same sequence of (file, qualname, kind) for "
              f"CALL/RETURN/RAISE/HANDLED on {where}; values, "
              "timing, and LINE events were not compared")
        return
    i = res["index"]
    print(f"verdict: DIVERGED at causal step {i}")
    for step in res["a_stream"][max(0, i - context):i]:
        print(f"  common  {_desc(step)}")
    print(f"  A:      {res['a_desc']}")
    print(f"  B:      {res['b_desc']}")
    if res["a_event"]:
        print(f"drill into A: sensorium tree {name_a} "
              f"--around e{res['a_event']}")
    if res["b_event"]:
        print(f"drill into B: sensorium tree {name_b} "
              f"--around e{res['b_event']}")


def add_parser(sub) -> None:
    p = sub.add_parser(
        "diff", help="first causal divergence between two runs")
    p.add_argument("run_a")
    p.add_argument("run_b")
    p.add_argument("--context", type=int, default=3,
                   help="common causal steps to show before a divergence")
    p.set_defaults(func=run)


def run(args) -> int:
    pa, pb = paths.find_trace(args.run_a), paths.find_trace(args.run_b)
    ta, tb = Trace.open(pa), Trace.open(pb)
    res = compare(ta, tb)
    print_comparison(ta, tb, res, pa.stem, pb.stem, args.context)
    if res["verdict"] == "REFUSED":
        return 2
    return 0 if res["verdict"] == "MATCH" else 1
