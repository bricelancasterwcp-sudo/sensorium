"""Compare two runs' causal streams and pinpoint the first divergence.

Causal stream = (file, qualname, kind) per CAUSAL_KINDS event (CALL / RETURN
/ RAISE / HANDLED) on one thread. Values, timing, and LINE events are
excluded by construction (see fingerprint.py), so a MATCH means the same
*shape* of execution -- the same sequence of calls, returns, raises and
handles -- not that the two runs are "the same" in every sense. It says
nothing about argument values, return values, wall-clock timing, per-line
state, or any thread other than the one compared (the main thread, unless a
caller passes another).

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

`compare()` therefore has three possible verdicts, not two: MATCH, DIVERGED,
and REFUSED. REFUSED means "the causal streams were never compared" -- it is
the honest alternative to guessing. This is deliberately load-bearing for
Task 15's `refocus`, which reuses `compare()` unchanged: a refocus run built
from an incomplete or lossy recording must refuse exactly the same way, so
the check lives here once rather than being re-implemented (and possibly
forgotten) at each call site.
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


def compare(trace_a: Trace, trace_b: Trace) -> dict:
    """Compare the main-thread causal streams of two traces.

    Returns a dict with `verdict` in {"MATCH", "DIVERGED", "REFUSED"}.

    MATCH / DIVERGED also carry `index`, `a_event`, `b_event`, `a_desc`,
    `b_desc` (all `None` on MATCH; `index` is the divergence position and
    the rest describe the two sides' next step on DIVERGED), plus the full
    `a_stream` / `b_stream` used, for callers that want more context.

    REFUSED means the comparison was never attempted -- `reasons` names
    which trace(s) are unsafe and why; `index`/`a_event`/`b_event`/
    `a_desc`/`b_desc`/`a_stream`/`b_stream` are all `None`.
    """
    reasons = _unsafe_reasons(trace_a, "A") + _unsafe_reasons(trace_b, "B")
    if reasons:
        return {"verdict": "REFUSED", "index": None, "a_event": None,
                "b_event": None, "a_desc": None, "b_desc": None,
                "reasons": reasons, "a_stream": None, "b_stream": None}
    sa = trace_a.causal_stream()
    sb = trace_b.causal_stream()
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


def safety_notes(trace_a: Trace, trace_b: Trace) -> list[str]:
    """Honesty notes that do not change the verdict but must never be
    silently dropped: a MATCH on the main thread is not a MATCH on the
    whole run if either side has other threads, and comparing two traces of
    different commands is comparing unrelated programs."""
    notes = []
    aa, bb = trace_a.meta.get("argv"), trace_b.meta.get("argv")
    if aa != bb:
        notes.append(
            f"different commands recorded -- A: {' '.join(aa or [])!r}"
            f"  B: {' '.join(bb or [])!r}")
    fa, fb = trace_a.fingerprints(), trace_b.fingerprints()
    if len(fa) > 1:
        notes.append(
            f"A recorded {len(fa)} threads; only the main thread was "
            "compared -- a MATCH here is not a MATCH on the whole run")
    if len(fb) > 1:
        notes.append(
            f"B recorded {len(fb)} threads; only the main thread was "
            "compared -- a MATCH here is not a MATCH on the whole run")
    return notes


def print_comparison(trace_a, trace_b, res, name_a, name_b, context=3) -> None:
    fa, fb = trace_a.fingerprints(), trace_b.fingerprints()
    print(f"A {name_a}: threads {len(fa)}  "
          f"main fp {list(fa.values())[0][0] if fa else '-'}")
    print(f"B {name_b}: threads {len(fb)}  "
          f"main fp {list(fb.values())[0][0] if fb else '-'}")
    for note in safety_notes(trace_a, trace_b):
        print(f"note: {note}")
    if res["verdict"] == "REFUSED":
        print("verdict: REFUSED -- cannot issue a MATCH/DIVERGED verdict")
        for reason in res["reasons"]:
            print(f"  {reason}")
        return
    if res["verdict"] == "MATCH":
        n = len(res["a_stream"])
        print(f"verdict: MATCH -- identical causal streams ({n} events): "
              "the same sequence of (file, qualname, kind) for "
              "CALL/RETURN/RAISE/HANDLED on the main thread; values, "
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
