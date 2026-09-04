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
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from sensorium.query.moves import (Moves, desc, detect_moves, for_b,
                                   modulo_location, print_key_line,
                                   print_moves_section, project, task_hashes)
from sensorium.query.vocab import PYTHON, terms
from sensorium.store.reader import Trace
# The honesty-note layer, split out at this file's 800-line ceiling.
# Re-exported so `diff_cmd.<name>` keeps resolving: these are one command's
# internals living in two files, not two modules with two surfaces.
from sensorium.query.diff_notes import (  # noqa: F401  (re-exported)
    _argv_note, _thread_header, _thread_notes, safety_notes)

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
    late = trace.dropped_writes()
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
            "tasks": None, "moves": None}


_DEFAULT_NAME = re.compile(r"^Task-\d+\Z")


def _unnamed(name: str | None, words=PYTHON) -> bool:
    """Whether `name` identifies a unit of work or merely numbers it.

    `asyncio` names every task it is not given a name for `Task-<N>` from a
    process-global counter, so such a name encodes creation order and
    nothing else -- exactly what this comparison must not compare, since
    `gather(*coros)` and one-task-per-request servers create tasks in
    data-dependent order (Ruling 4).

    A language that mints no such names (`Terms.default_name_note is None`)
    has no numbering to read a name AS: a Rust test called `Task-1` would be
    a name its program chose, and dropping it would erase content this
    comparison exists to compare. `words` defaults to the Python table so
    every existing caller and test reads exactly as before."""
    if name is None:
        return True
    return (words.default_name_note is not None
            and _DEFAULT_NAME.match(name) is not None)


def _shapes(trace: Trace, moves: Moves | None = None) -> Counter:
    """`Trace.task_shapes()` with asyncio's default `Task-N` names read as
    no name. The reader owns the multiset; this owns the one thing that is
    a comparison policy and not a fact about the trace, so the raw name
    stays in the table and in `info` -- it is dropped for the comparison,
    not everywhere.

    With `moves` (a Moves object, its mapping empty for the B side) the
    shapes are RE-HASHED from each task's stream, projected through it:
    `--ignore-moves` must hash both sides one way, and the stored rows were
    hashed over a root-relative file."""
    out: Counter = Counter()
    words = terms(trace)
    if moves is None:
        for (name, h), k in trace.task_shapes().items():
            out[(None if _unnamed(name, words) else name, h)] += k
        return out
    for name, h in task_hashes(trace, moves).values():
        out[(None if _unnamed(name, words) else name, h)] += 1
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
            f"bases (A: {ba}, B: {bb}): the per-thread side's thread stream "
            "includes its task events, which this version compares "
            "separately, so the two are not the same kind of stream -- "
            "re-record the older side with this version to compare them"]


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
    every recording made through the CLI. A cleanly finished recording no
    longer produces the state -- every minted task serial gets its
    fingerprint when it is minted (Ruling 9) and the rows are written in one
    transaction at uninstall -- but an unclean death still can: a run killed
    after its first batch flush has `tasks` rows and no `task_fingerprints`
    rows (beside `incomplete`), and a callback still in flight at uninstall
    can mint a serial after the snapshot. So the check stays for two
    reasons: files already on disk, and recordings that did not finish.
    """
    tasks = trace.tasks()
    if (trace.fingerprint_basis != "per-task" or not tasks
            or trace.task_fingerprints()):
        return []
    return [f"{label} ran {len(tasks)} {terms(trace).task_noun_plural} but "
            "recorded no task "
            "fingerprints (its per-thread stream excludes their events), so "
            "the tasks cannot be compared and the thread stream alone would "
            "say less than it seems -- re-record it with this version"]


def _pair(trace_a, trace_b, ta, tb, name, by_order=False,
          moves=None) -> dict | None:
    """Two task streams and their first differing step; `None` when they do
    not actually differ (same shape, different serial numbering) -- there is
    nothing to show, and showing a step anyway would invent a difference.

    Projected under `--ignore-moves` like every other compared stream: the
    raw streams part at the first moved CALL, and reporting THAT as the
    task's first difference would point at the move the flag exists to
    look past."""
    sa, sb = trace_a.task_stream(ta), trace_b.task_stream(tb)
    if moves:
        sa, sb = project(sa, moves), project(sb, for_b(moves))
    i = first_divergence(sa, sb)
    if i is None:
        return None
    a_step = sa[i] if i < len(sa) else None
    b_step = sb[i] if i < len(sb) else None
    return {"name": name, "index": i, "a_task": ta, "b_task": tb,
            "by_order": by_order,
            "a_event": a_step[3] if a_step else None,
            "b_event": b_step[3] if b_step else None,
            "a_desc": desc(a_step, moves) if a_step else "(stream ended)",
            "b_desc": desc(b_step) if b_step else "(stream ended)"}


def _first_pair_sharing_a_name(trace_a, trace_b, only_a, only_b,
                               moves=None) -> dict | None:
    """For the first name present on both 'only' lists, the two task streams
    and their first differing step -- None when no name is shared (then
    every unmatched stream is simply listed)."""
    names_b = {n for n, _h, _k in only_b if n is not None}
    for name, ha, _k in only_a:
        if name is None or name not in names_b:
            continue
        hb = next(h for n, h, _c in only_b if n == name)
        ta = next(t for t, (n, h) in task_hashes(trace_a, moves).items()
                  if n == name and h == ha)
        tb = next(t for t, (n, h) in task_hashes(trace_b, for_b(moves)).items()
                  if n == name and h == hb)
        pair = _pair(trace_a, trace_b, ta, tb, name, moves=moves)
        if pair is not None:
            return pair
    return None


def _lowest_unmatched_unnamed(trace: Trace, rows, moves=None) -> int | None:
    """The unnamed task with the lowest serial whose shape went unmatched.
    Which of several same-shaped tasks is "the" unmatched one is not
    knowable -- this picks by creation order, and every caller says so."""
    wanted = {h for n, h, _k in rows if n is None}
    return min((t for t, (n, h) in task_hashes(trace, moves).items()
                if _unnamed(n) and h in wanted), default=None)


def _first_unnamed_pair(trace_a, trace_b, only_a, only_b,
                        moves=None) -> dict | None:
    """Ruling 4c: when the unmatched streams carry no name on either side
    there is nothing to match them on, so the drill-in pairs the first
    unmatched unnamed stream on each side by ascending task serial. That is
    a guide to look at, not a claim that the two are the same task, and the
    printed line says exactly that."""
    ta = _lowest_unmatched_unnamed(trace_a, only_a, moves)
    tb = _lowest_unmatched_unnamed(trace_b, only_b, for_b(moves))
    if ta is None or tb is None:
        return None
    return _pair(trace_a, trace_b, ta, tb, None, by_order=True, moves=moves)


def compare_tasks(trace_a: Trace, trace_b: Trace,
                  moves: Moves | None = None) -> dict:
    """Tasks compared as a multiset of (name, hash): order-independent, so a
    different interleaving cannot manufacture a DIVERGED, and two tasks
    sharing a name are matched by content. verdict None = no task on either
    side (nothing to say)."""
    a, b = (_shapes(trace_a, moves),
            _shapes(trace_b, for_b(moves)))        # Ruling 4 normalisation
    n_a, n_b = a.total(), b.total()
    if not n_a and not n_b:
        return {"verdict": None, "only_a": [], "only_b": [], "pair": None,
                "n_a": 0, "n_b": 0}
    only_a, only_b = _shape_difference(a, b)
    if not only_a and not only_b:
        return {"verdict": "MATCH", "only_a": [], "only_b": [], "pair": None,
                "n_a": n_a, "n_b": n_b}
    pair = (_first_pair_sharing_a_name(trace_a, trace_b, only_a, only_b,
                                       moves)
            or _first_unnamed_pair(trace_a, trace_b, only_a, only_b, moves))
    return {"verdict": "DIVERGED", "only_a": only_a, "only_b": only_b,
            "pair": pair, "n_a": n_a, "n_b": n_b}


def compare(trace_a: Trace, trace_b: Trace,
            moves: Moves | None = None) -> dict:
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
    sa = (project(trace_a.causal_stream(), moves) if moves
          else trace_a.causal_stream())
    sb = (project(trace_b.causal_stream(), for_b(moves)) if moves
          else trace_b.causal_stream())
    tasks = compare_tasks(trace_a, trace_b, moves)
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
                "tasks": tasks, "moves": moves}
    a_step = sa[i] if i < len(sa) else None
    b_step = sb[i] if i < len(sb) else None
    return {
        "verdict": "DIVERGED",
        "index": i,
        "a_event": a_step[3] if a_step else None,
        "b_event": b_step[3] if b_step else None,
        "a_desc": desc(a_step, moves) if a_step else "(stream ended)",
        "b_desc": desc(b_step) if b_step else "(stream ended)",
        "reasons": [],
        "a_stream": sa, "b_stream": sb,
        "tasks": tasks, "moves": moves,
    }


def _task_choices(trace: Trace) -> str:
    """What `--task` could have been given on this side."""
    fps = trace.task_fingerprints()
    words = terms(trace)
    named = sorted({n for n, _h, _c in fps.values()
                    if not _unnamed(n, words)})
    numbered = sum(1 for n, _h, _c in fps.values() if _unnamed(n, words))
    have = ", ".join(named) if named else "no task with a name of its own"
    if numbered:
        have += f"; plus {numbered} {words.numbered_task_note}"
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
        # Not "it has no task stream": a per-thread trace can be full of
        # task-tagged events, and saying otherwise describes the recording
        # as emptier than it is. What is missing is the table this version
        # resolves a NAME through.
        return None, [
            f"{label} recorded {len(trace.tasks())} "
            f"{terms(trace).task_noun_plural} and no "
            "task_fingerprints rows: this version resolves task names "
            "through task_fingerprints, which the recording's version did "
            "not write -- re-record it to compare by name"]
    return None, [f"no task named '{name}' on {label} "
                  f"({label} has: {_task_choices(trace)})"]


def compare_task_streams(trace_a: Trace, trace_b: Trace, name: str,
                         moves: Moves | None = None) -> dict:
    """`compare()` for one named asyncio task instead of the thread streams.

    Same keys, plus `a_task` / `b_task` (the task ids compared). The name
    must pick exactly one task on each side: no task by that name, two tasks
    sharing it, or asyncio's own `Task-N` numbering are all REFUSED rather
    than resolved by creation order -- see `_unnamed`.
    """
    unresolved = {"a_task": None, "b_task": None}
    # Read on A's table: the argument is one string compared against both
    # sides, and a language that mints no default names has no note to
    # print -- there the name is looked up like any other.
    note = terms(trace_a).default_name_note
    if note and _DEFAULT_NAME.match(name):
        return {**_refused([note.format(name=name)]), **unresolved}
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
    if moves:
        sa, sb = project(sa, moves), project(sb, for_b(moves))
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
                "tasks": None, "moves": moves, **found}
    a_step = sa[i] if i < len(sa) else None
    b_step = sb[i] if i < len(sb) else None
    return {
        "verdict": "DIVERGED",
        "index": i,
        "a_event": a_step[3] if a_step else None,
        "b_event": b_step[3] if b_step else None,
        "a_desc": desc(a_step, moves) if a_step else "(stream ended)",
        "b_desc": desc(b_step) if b_step else "(stream ended)",
        "reasons": [],
        "a_stream": sa, "b_stream": sb,
        "tasks": None, "moves": moves, **found,
    }


def _print_refusal(res) -> None:
    print("verdict: REFUSED -- cannot issue a MATCH/DIVERGED verdict")
    for reason in res["reasons"]:
        print(f"  {reason}")


def _print_divergence(res, name_a, name_b, context) -> None:
    """The first differing step of two streams, with the common run-up and
    the two commands that show it in full."""
    i = res["index"]
    print(f"verdict: DIVERGED at causal step {i}")
    moves = res.get("moves")          # A's stream is projected; name A's files
    for step in res["a_stream"][max(0, i - context):i]:
        print(f"  common  {desc(step, moves)}")
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
    if modulo_location(res.get("moves")):
        nm = len(res["moves"].moved)
        print(f"verdict: MATCH modulo location -- identical causal streams "
              f"({n} events) once {nm} moved code object(s) are paired by "
              f"qualname on {where}; values, timing, and LINE events were "
              "not compared")
        return
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
    for line in task_drill_lines(p, name_a, name_b):
        print(line)


def task_drill_lines(pair, name_a, name_b) -> list[str]:
    """The `sensorium tree --around` command for each side of a task pair's
    first difference, or [] when there is no pair to drill into.

    Shared rather than duplicated: `refocus` prints the task finding in its
    own words (the same sentence it stamps into the trace) and still owes
    the reader these two commands.
    """
    if not pair:
        return []
    out = []
    if pair["a_event"]:
        out.append(f"drill into A: sensorium tree {name_a} "
                   f"--around e{pair['a_event']}")
    if pair["b_event"]:
        out.append(f"drill into B: sensorium tree {name_b} "
                   f"--around e{pair['b_event']}")
    return out


def print_comparison(trace_a, trace_b, res, name_a, name_b, context=3,
                     tasks=True) -> None:
    """`diff`'s full comparison. `tasks=False` omits the task section for a
    caller that reports the task finding itself -- `refocus` does, in the
    words it also stamps into the trace, and two `tasks:` lines saying
    different amounts about one finding read as two findings."""
    print(_thread_header("A", name_a, trace_a))
    print(_thread_header("B", name_b, trace_b))
    print_key_line(res.get("moves"))
    for note in safety_notes(trace_a, trace_b):
        print(f"note: {note}")
    if res["verdict"] == "REFUSED":
        _print_refusal(res)
        return
    if res["index"] is None:
        _print_thread_match(trace_a, trace_b, res)
    else:
        _print_divergence(res, name_a, name_b, context)
    if tasks:
        _print_tasks(res, name_a, name_b)
    print_moves_section(res.get("moves"))


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
    print_key_line(res.get("moves"))
    for note in _argv_note(trace_a, trace_b):
        print(f"note: {note}")
    print(f"note: only task {task} was compared -- nothing is claimed here "
          "about the thread streams, the other tasks, or the order any of "
          "them ran in")
    if res["verdict"] != "MATCH":
        _print_divergence(res, name_a, name_b, context)
    elif modulo_location(res.get("moves")):
        nm = len(res["moves"].moved)
        print(f"verdict: MATCH modulo location -- identical causal streams "
              f"({len(res['a_stream'])} events) once {nm} moved code "
              f"object(s) are paired by qualname inside task {task}; values, "
              "timing, and LINE events were not compared")
    else:
        print(f"verdict: MATCH -- identical causal streams "
              f"({len(res['a_stream'])} events): the same sequence of "
              "(file, qualname, kind) for CALL/RETURN/RAISE/HANDLED inside "
              f"task {task}; values, timing, and LINE events were not "
              "compared")
    print_moves_section(res.get("moves"))


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
    p.add_argument("--ignore-moves", action="store_true",
                   help="pair a function that left one file with the same-"
                        "named function that appeared in another, then "
                        "compare; the pairing is printed with the verdict")
    p.set_defaults(func=run)


def run(args) -> int:
    pa, pb = paths.find_trace(args.run_a), paths.find_trace(args.run_b)
    ta, tb = Trace.open(pa), Trace.open(pb)
    moves = detect_moves(ta, tb) if args.ignore_moves else None
    if args.task:
        res = compare_task_streams(ta, tb, args.task, moves)
        print_task_comparison(ta, tb, res, pa.stem, pb.stem, args.task,
                              args.context)
    else:
        res = compare(ta, tb, moves)
        print_comparison(ta, tb, res, pa.stem, pb.stem, args.context)
    # A refusal is not a bad call: the command was well formed and the
    # traces were readable. What it says is that no comparison could be
    # made against THESE recordings -- incomplete, dropped writes, empty on
    # both sides, mismatched fingerprint bases, tasks with no fingerprints,
    # a name that picks none or two -- and every one of those is fixed by
    # recording again, which is what 3 means (X5). The `error:` exits in
    # `cli.main` keep 2: an unreadable trace or an unresolvable ref IS the
    # call being wrong.
    if res["verdict"] == "REFUSED":
        return UNSETTLED
    return ANSWERED if res["verdict"] == "MATCH" else NEGATIVE
