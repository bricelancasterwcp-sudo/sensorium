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

TASKS ARE NOT THREADS, AND THEIR ORDER IS NOT CONTENT
-----------------------------------------------------
Under the per-task fingerprint basis a thread's causal stream is the events
that ran in NO task, and every asyncio task has a stream of its own. The
two are compared differently on purpose. A thread stream is compared step
by step, because the order of events on one thread is the program's own
doing. Task streams are compared as a MULTISET of (name, hash): the event
loop decides when each task gets to run, so which task ran first is a
scheduling fact, not a fact about the program -- comparing the interleaving
would manufacture a DIVERGED out of two runs that did exactly the same work.

A name is content here, not a label: `task-A` matches `task-A`, and a task
with no name of its own only ever matches another unnamed one. `asyncio`
names every task it is not given a name for `Task-<N>` from a process-global
counter, so that "name" IS creation order -- it is read as no name at all
(Ruling 4), and `--task` refuses it rather than pretend it identifies
anything.

Two traces recorded under different bases are refused outright when either
ran a task: one side's thread stream contains the task events and the
other's does not, so the two streams are not the same kind of thing and a
verdict comparing them would be about the definition, not the program.

`compare()` therefore has three possible verdicts, not two: MATCH, DIVERGED,
and REFUSED. REFUSED means "no verdict could be issued" -- it is the honest
alternative to guessing. This is deliberately load-bearing for `refocus`,
which reuses `compare()` unchanged: a refocus built on an incomplete, lossy,
or empty recording must refuse exactly the same way, so the check lives here
once rather than being re-implemented (and possibly forgotten) at each call
site.
"""
import re
from collections import Counter

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
            "reasons": reasons, "a_stream": None, "b_stream": None,
            "tasks": None}


_DEFAULT_NAME = re.compile(r"^Task-\d+\Z")


def _unnamed(name: str | None) -> bool:
    """Whether `name` identifies a task or merely numbers it.

    `asyncio` names every task it is not given a name for `Task-<N>` from a
    process-global counter, so such a name encodes creation order and
    nothing else -- exactly what this comparison must not compare, since
    `gather(*coros)` and one-task-per-request servers create tasks in
    data-dependent order (Ruling 4)."""
    return name is None or _DEFAULT_NAME.match(name) is not None


def _shapes(trace: Trace) -> Counter:
    """`Trace.task_shapes()` with asyncio's default `Task-N` names read as
    no name. The reader owns the multiset; this owns the one thing that is
    a comparison policy and not a fact about the trace, so the raw name
    stays in the table and in `info` -- it is dropped for the comparison,
    not everywhere."""
    out: Counter = Counter()
    for (name, h), k in trace.task_shapes().items():
        out[(None if _unnamed(name) else name, h)] += k
    return out


def _shape_difference(a: Counter, b: Counter):
    """(only_a, only_b): the (name, hash, count) entries one multiset has
    and the other lacks. Unnamed tasks carry name None and therefore only
    ever match unnamed tasks -- a name is content here, not a label."""
    def rows(c):
        return sorted(((n, h, k) for (n, h), k in c.items()),
                      key=lambda r: (r[0] is None, r[0] or "", r[1]))
    return rows(a - b), rows(b - a)


def _basis_reasons(trace_a: Trace, trace_b: Trace) -> list[str]:
    """Two traces recorded under different fingerprint bases define their
    thread streams differently; if either ran a task the comparison would
    put task events on one side only. No task anywhere: the definitions
    coincide and nothing is refused."""
    ba, bb = trace_a.fingerprint_basis, trace_b.fingerprint_basis
    if ba == bb or not (trace_a.tasks() or trace_b.tasks()):
        return []
    return ["the two traces were recorded under different fingerprint "
            f"bases (A: {ba}, B: {bb}): one thread stream includes the "
            "events that ran inside asyncio tasks and the other does not, "
            "so they are not the same kind of stream -- re-record the "
            "older side with this version to compare them"]


def _task_row_reasons(trace: Trace, label: str) -> list[str]:
    """Why a trace that RAN tasks but recorded none of their fingerprints
    cannot be compared at all.

    It is not the same thing as a trace with no tasks. The per-task basis is
    a meta marker, so `causal_stream()` narrows this trace's thread stream
    to the events that ran in no task whether or not the task rows made it
    to disk -- and with no task fingerprints to compare, everything those
    tasks did drops out of the comparison silently. What is left is the
    module scaffolding, and a MATCH on it reads as a verdict on the run.

    Traces in exactly this state exist: until this arc the writer's
    `INSERT ... SELECT` over an unflushed `tasks` table wrote zero rows for
    every recording made through the CLI.
    """
    tasks = trace.tasks()
    if (trace.fingerprint_basis != "per-task" or not tasks
            or trace.task_fingerprints()):
        return []
    return [f"{label} ran {len(tasks)} asyncio task(s) but recorded no task "
            "fingerprints (its per-thread stream excludes their events), so "
            "the tasks cannot be compared and the thread stream alone would "
            "say less than it seems -- re-record it with this version"]


def _pair(trace_a, trace_b, ta, tb, name, by_order=False) -> dict | None:
    """Two task streams and their first differing step; `None` when they do
    not actually differ (same shape, different serial numbering) -- there is
    nothing to show, and showing a step anyway would invent a difference."""
    sa, sb = trace_a.task_stream(ta), trace_b.task_stream(tb)
    i = first_divergence(sa, sb)
    if i is None:
        return None
    a_step = sa[i] if i < len(sa) else None
    b_step = sb[i] if i < len(sb) else None
    return {"name": name, "index": i, "a_task": ta, "b_task": tb,
            "by_order": by_order,
            "a_event": a_step[3] if a_step else None,
            "b_event": b_step[3] if b_step else None,
            "a_desc": _desc(a_step) if a_step else "(stream ended)",
            "b_desc": _desc(b_step) if b_step else "(stream ended)"}


def _first_pair_sharing_a_name(trace_a, trace_b, only_a,
                               only_b) -> dict | None:
    """For the first name present on both 'only' lists, the two task streams
    and their first differing step -- None when no name is shared (then
    every unmatched stream is simply listed)."""
    names_b = {n for n, _h, _k in only_b if n is not None}
    for name, ha, _k in only_a:
        if name is None or name not in names_b:
            continue
        hb = next(h for n, h, _c in only_b if n == name)
        ta = next(t for t, (n, h, _c) in trace_a.task_fingerprints().items()
                  if n == name and h == ha)
        tb = next(t for t, (n, h, _c) in trace_b.task_fingerprints().items()
                  if n == name and h == hb)
        pair = _pair(trace_a, trace_b, ta, tb, name)
        if pair is not None:
            return pair
    return None


def _lowest_unmatched_unnamed(trace: Trace, rows) -> int | None:
    """The unnamed task with the lowest serial whose shape went unmatched.
    Which of several same-shaped tasks is "the" unmatched one is not
    knowable -- this picks by creation order, and every caller says so."""
    wanted = {h for n, h, _k in rows if n is None}
    return min((t for t, (n, h, _c) in trace.task_fingerprints().items()
                if _unnamed(n) and h in wanted), default=None)


def _first_unnamed_pair(trace_a, trace_b, only_a, only_b) -> dict | None:
    """Ruling 4c: when the unmatched streams carry no name on either side
    there is nothing to match them on, so the drill-in pairs the first
    unmatched unnamed stream on each side by ascending task serial. That is
    a guide to look at, not a claim that the two are the same task, and the
    printed line says exactly that."""
    ta = _lowest_unmatched_unnamed(trace_a, only_a)
    tb = _lowest_unmatched_unnamed(trace_b, only_b)
    if ta is None or tb is None:
        return None
    return _pair(trace_a, trace_b, ta, tb, None, by_order=True)


def compare_tasks(trace_a: Trace, trace_b: Trace) -> dict:
    """Tasks compared as a multiset of (name, hash): order-independent, so a
    different interleaving cannot manufacture a DIVERGED, and two tasks
    sharing a name are matched by content. verdict None = no task on either
    side (nothing to say)."""
    a, b = _shapes(trace_a), _shapes(trace_b)       # Ruling 4 normalisation
    n_a, n_b = a.total(), b.total()
    if not n_a and not n_b:
        return {"verdict": None, "only_a": [], "only_b": [], "pair": None,
                "n_a": 0, "n_b": 0}
    only_a, only_b = _shape_difference(a, b)
    if not only_a and not only_b:
        return {"verdict": "MATCH", "only_a": [], "only_b": [], "pair": None,
                "n_a": n_a, "n_b": n_b}
    pair = (_first_pair_sharing_a_name(trace_a, trace_b, only_a, only_b)
            or _first_unnamed_pair(trace_a, trace_b, only_a, only_b))
    return {"verdict": "DIVERGED", "only_a": only_a, "only_b": only_b,
            "pair": pair, "n_a": n_a, "n_b": n_b}


def compare(trace_a: Trace, trace_b: Trace) -> dict:
    """Compare the main-thread causal streams of two traces.

    Returns a dict with `verdict` in {"MATCH", "DIVERGED", "REFUSED"}.

    MATCH / DIVERGED also carry `index`, `a_event`, `b_event`, `a_desc`,
    `b_desc` (all `None` on MATCH; `index` is the divergence position and
    the rest describe the two sides' next step on DIVERGED), plus the full
    `a_stream` / `b_stream` used, for callers that want more context.

    `tasks` carries `compare_tasks()`'s own result (`None` when REFUSED, and
    a `verdict` of `None` inside it when neither side ran a task). A pair
    can diverge on the tasks alone: the verdict is then DIVERGED with
    `index` -- and `a_event`/`b_event`/`a_desc`/`b_desc` -- left `None`,
    because the divergence is not a step of the thread stream those keys
    describe. A caller reading `index` to locate a divergence must handle
    that `None` rather than assume DIVERGED means "on this stream".

    REFUSED means no verdict could be issued, and comes in two shapes that
    share one contract (`reasons` says which, everything else is `None`):
    the streams could not be TRUSTED, so they were never read; or they were
    read and held nothing to compare. Both are the honest alternative to a
    confident answer -- the second one because two empty streams are equal,
    and calling that MATCH is a verdict about nothing.
    """
    reasons = (_unsafe_reasons(trace_a, "A") + _unsafe_reasons(trace_b, "B")
               + _basis_reasons(trace_a, trace_b)
               + _task_row_reasons(trace_a, "A")
               + _task_row_reasons(trace_b, "B"))
    if reasons:
        return _refused(reasons)
    sa = trace_a.causal_stream()
    sb = trace_b.causal_stream()
    tasks = compare_tasks(trace_a, trace_b)
    if not sa and not sb and tasks["verdict"] is None:
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
        # The thread streams are identical. That is not the whole run: a
        # task that took another path is a divergence of this pair, and
        # `index` stays None because it is not a step of THIS stream.
        return {"verdict": ("DIVERGED" if tasks["verdict"] == "DIVERGED"
                            else "MATCH"),
                "index": None, "a_event": None,
                "b_event": None, "a_desc": None, "b_desc": None,
                "reasons": [], "a_stream": sa, "b_stream": sb,
                "tasks": tasks}
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
        "tasks": tasks,
    }


def _task_choices(trace: Trace) -> str:
    """What `--task` could have been given on this side."""
    fps = trace.task_fingerprints()
    named = sorted({n for n, _h, _c in fps.values() if not _unnamed(n)})
    numbered = sum(1 for n, _h, _c in fps.values() if _unnamed(n))
    have = ", ".join(named) if named else "no task with a name of its own"
    if numbered:
        have += (f"; plus {numbered} task(s) asyncio numbered by creation "
                 "order, which no name can pick")
    return have


def _task_named(trace: Trace, label: str, name: str):
    """(task_id, []) for the one task called `name`, or (None, [why not])."""
    fps = trace.task_fingerprints()
    hits = sorted(t for t, (n, _h, _c) in fps.items() if n == name)
    if len(hits) == 1:
        return hits[0], []
    if len(hits) > 1:
        return None, [f"'{name}' names {len(hits)} tasks on {label}; a name "
                      "must pick exactly one task to compare -- picking one "
                      "of them would be picking by creation order, which is "
                      "what comparing tasks by name exists to avoid"]
    if not fps and trace.fingerprint_basis != "per-task":
        return None, [f"{label} predates per-task fingerprints (it was "
                      "recorded under the per-thread basis), so it has no "
                      "task stream to compare by name -- re-record it with "
                      "this version"]
    return None, [f"no task named '{name}' on {label} "
                  f"({label} has: {_task_choices(trace)})"]


def compare_task_streams(trace_a: Trace, trace_b: Trace, name: str) -> dict:
    """`compare()` for one named asyncio task instead of the thread streams.

    Same keys, plus `a_task` / `b_task` (the task ids compared). The name
    must pick exactly one task on each side: no task by that name, two tasks
    sharing it, or asyncio's own `Task-N` numbering are all REFUSED rather
    than resolved by creation order -- see `_unnamed`.
    """
    unresolved = {"a_task": None, "b_task": None}
    if _DEFAULT_NAME.match(name):
        return {**_refused(
            [f"'{name}' is asyncio's default name and encodes creation "
             "order, not identity; name the task in the program "
             "(asyncio.create_task(..., name=...)) to compare it by name"]),
            **unresolved}
    # These come first and alone: a trace whose task rows never reached the
    # disk has no task to name, and "no task named 'task-A' on A" would
    # describe the symptom as if it were the program's doing.
    reasons = (_unsafe_reasons(trace_a, "A") + _unsafe_reasons(trace_b, "B")
               + _task_row_reasons(trace_a, "A")
               + _task_row_reasons(trace_b, "B"))
    if reasons:
        return {**_refused(reasons), **unresolved}
    ia, why_a = _task_named(trace_a, "A", name)
    ib, why_b = _task_named(trace_b, "B", name)
    reasons = why_a + why_b
    if reasons:
        return {**_refused(reasons), **unresolved}
    found = {"a_task": ia, "b_task": ib}
    sa, sb = trace_a.task_stream(ia), trace_b.task_stream(ib)
    if not sa and not sb:
        return {**_refused(
            [f"task '{name}' recorded no causal event on either side, so "
             "there was nothing to compare -- a MATCH here would be a "
             "verdict about nothing"]), **found}
    i = first_divergence(sa, sb)
    if i is None:
        return {"verdict": "MATCH", "index": None, "a_event": None,
                "b_event": None, "a_desc": None, "b_desc": None,
                "reasons": [], "a_stream": sa, "b_stream": sb,
                "tasks": None, **found}
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
        "tasks": None, **found,
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


def _print_refusal(res) -> None:
    print("verdict: REFUSED -- cannot issue a MATCH/DIVERGED verdict")
    for reason in res["reasons"]:
        print(f"  {reason}")


def _print_divergence(res, name_a, name_b, context) -> None:
    """The first differing step of two streams, with the common run-up and
    the two commands that show it in full."""
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


def _print_thread_match(trace_a, trace_b, res) -> None:
    """The thread streams are identical. Whether that is the run's verdict
    depends on the tasks: a task that took another path is a divergence of
    this pair, and calling the whole thing MATCH would be a verdict on the
    half that happened to agree."""
    n = len(res["a_stream"])
    if res["verdict"] == "DIVERGED":
        print("verdict: " + ("the thread stream held no causal events on "
                             "either side" if not n else
                             f"MATCH on the thread stream ({n} events)")
              + "; DIVERGED on the tasks (below)")
        return
    if not n:
        # Reachable only because a task ran: two empty streams with no task
        # on either side are refused outright. "Identical causal streams (0
        # events)" would be the verdict about nothing this command refuses
        # everywhere else, dressed as agreement.
        print("verdict: MATCH -- no causal event ran outside a task on "
              "either side, so the thread streams held nothing to compare; "
              "the tasks below carry the whole verdict")
        return
    exact = (trace_a.main_thread_basis() == "recorded"
            and trace_b.main_thread_basis() == "recorded")
    where = "the main thread" if exact else "the thread named above"
    print(f"verdict: MATCH -- identical causal streams ({n} events): "
          "the same sequence of (file, qualname, kind) for "
          f"CALL/RETURN/RAISE/HANDLED on {where}; values, "
          "timing, and LINE events were not compared")


def _fmt_shapes(rows) -> str:
    return ", ".join(f"{n if n is not None else '(unnamed)'} "
                     f"{h[:12]}{'' if k == 1 else f' x{k}'}"
                     for n, h, k in rows) or "-"


def _print_tasks(res, name_a, name_b) -> None:
    """The task section: what the multiset comparison found, and -- when a
    pair can be picked out -- the first step where the two streams parted."""
    t = res.get("tasks")
    if not t or t["verdict"] is None:
        return
    if t["verdict"] == "MATCH":
        print(f"tasks: {t['n_a']} task stream(s) on each side, compared by "
              "content as (name, hash): all matched; the ordering between "
              "tasks is not compared")
        return
    print(f"tasks: DIVERGED -- {t['n_a']} task stream(s) on A, {t['n_b']} "
          f"on B; only in A: {_fmt_shapes(t['only_a'])}; only in B: "
          f"{_fmt_shapes(t['only_b'])}; the ordering between tasks is not "
          "compared")
    p = t["pair"]
    if not p:
        return
    guide = (" (paired by creation order -- a guide, not a match)"
             if p["by_order"] else "")
    print(f"first difference inside {p['name'] or '(unnamed)'} "
          f"(A task t{p['a_task']}, B task t{p['b_task']}) at causal step "
          f"{p['index']}{guide}:")
    print(f"  A:      {p['a_desc']}")
    print(f"  B:      {p['b_desc']}")
    if p["a_event"]:
        print(f"drill into A: sensorium tree {name_a} "
              f"--around e{p['a_event']}")
    if p["b_event"]:
        print(f"drill into B: sensorium tree {name_b} "
              f"--around e{p['b_event']}")


def print_comparison(trace_a, trace_b, res, name_a, name_b, context=3) -> None:
    print(_thread_header("A", name_a, trace_a))
    print(_thread_header("B", name_b, trace_b))
    for note in safety_notes(trace_a, trace_b):
        print(f"note: {note}")
    if res["verdict"] == "REFUSED":
        _print_refusal(res)
        return
    if res["index"] is None:
        _print_thread_match(trace_a, trace_b, res)
    else:
        _print_divergence(res, name_a, name_b, context)
    _print_tasks(res, name_a, name_b)


def print_task_comparison(trace_a, trace_b, res, name_a, name_b, task,
                          context=3) -> None:
    """`--task NAME`: one task stream per side, and nothing else claimed."""
    if res["verdict"] == "REFUSED":
        print(f"A {name_a}, B {name_b}: compared: task {task} -- "
              "not resolved")
        _print_refusal(res)
        return
    print(f"A {name_a}: compared: task {task} (t{res['a_task']})")
    print(f"B {name_b}: compared: task {task} (t{res['b_task']})")
    for note in _argv_note(trace_a, trace_b):
        print(f"note: {note}")
    print(f"note: only task {task} was compared -- nothing is claimed here "
          "about the thread streams, the other tasks, or the order any of "
          "them ran in")
    if res["verdict"] == "MATCH":
        print(f"verdict: MATCH -- identical causal streams "
              f"({len(res['a_stream'])} events): the same sequence of "
              "(file, qualname, kind) for CALL/RETURN/RAISE/HANDLED inside "
              f"task {task}; values, timing, and LINE events were not "
              "compared")
        return
    _print_divergence(res, name_a, name_b, context)


def add_parser(sub) -> None:
    p = sub.add_parser(
        "diff", help="first causal divergence between two runs")
    p.add_argument("run_a")
    p.add_argument("run_b")
    p.add_argument("--context", type=int, default=3,
                   help="common causal steps to show before a divergence")
    p.add_argument("--task", default=None, metavar="NAME",
                   help="compare one asyncio task's stream by name instead "
                        "of the thread streams")
    p.set_defaults(func=run)


def run(args) -> int:
    pa, pb = paths.find_trace(args.run_a), paths.find_trace(args.run_b)
    ta, tb = Trace.open(pa), Trace.open(pb)
    if args.task:
        res = compare_task_streams(ta, tb, args.task)
        print_task_comparison(ta, tb, res, pa.stem, pb.stem, args.task,
                              args.context)
    else:
        res = compare(ta, tb)
        print_comparison(ta, tb, res, pa.stem, pb.stem, args.context)
    if res["verdict"] == "REFUSED":
        return 2
    return 0 if res["verdict"] == "MATCH" else 1
