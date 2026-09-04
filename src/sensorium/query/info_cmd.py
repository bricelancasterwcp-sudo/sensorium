"""Summarize one trace: shape, exceptions, caps, honesty flags.

`meta` only guarantees every key for a run that finished normally. A run
whose `install()` failed is written with `incomplete=True` and never gets
its finalize pass, so it has no `exit_status`, no `uncaught`, no `children`
and no `truncated_count` at all -- every read below goes through `.get()`
with a fallback, and the INCOMPLETE flag is printed first, not buried.
"""
import re
from collections import Counter

from sensorium import paths
from sensorium.exit import ANSWERED
from sensorium.query.caps import witness_gap
from sensorium.query.fmt import fmt_exc
from sensorium.query.info_rust import rust_lines
from sensorium.query.vocab import exit_phrase, terms
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser(
        "info", help="summarize one trace",
        epilog="exit: 0 yes, 1 no, 2 fix the call, 3 change the recording")
    p.add_argument("run")
    p.set_defaults(func=run)


_BOOKKEEPING = ("children", "threads_started", "spawn_syscalls",
                "audit_errors")
_THREAD_BOOKKEEPING = ("threads_started",)
_CHILD_BOOKKEEPING = ("children", "spawn_syscalls", "audit_errors")


def unwitnessed_lines(trace, m: dict) -> list[str]:
    """Everything the recorder NOTICED starting and could not witness, in
    the order a Python trace has always printed it.

    The two halves are separate functions because `info_rust` prints them
    in the other order (declaration first, then the counts it qualifies)
    and adds its own lines between them. Neither half's WORDING moves.
    """
    return witnessed_counts(trace, m) + declaration_lines(trace, m)


def witnessed_counts(trace, m: dict) -> list[str]:
    """The counts of what the recorder saw start and could not follow.

    `children` was for a long time the only one of these `info` printed, so a
    `multiprocessing` run whose child is visible ONLY as a spawn syscall, and
    every thread a run started, left no mark on the durable record at all --
    while `refocus` withholds its licence on exactly these keys. Two commands
    reading one trace must not answer the same question differently.

    Non-zero values only, on the `late_writes` precedent: a printed `spawn
    syscalls: 0` would be read as proof no child ran, which is precisely what
    it is not. A trace that never recorded the key at all is a third state,
    and says so rather than reading as a zero.
    """
    out = []
    started = m.get("threads_started")
    if started:
        out.append(
            f"threads started: {started} besides the main one, "
            f"{terms(trace).thread_origin} -- one that ran no traced code "
            "has no fingerprint above and was not otherwise seen")
    spawns = m.get("spawn_syscalls")
    if spawns:
        out.append(
            f"spawn syscalls: {spawns} -- low-level process starts, counted "
            "apart from any subprocess named above because one Popen nests "
            "one; a multiprocessing 'spawn'/'forkserver' child is visible "
            "here and nowhere else")
    errors = m.get("audit_errors")
    if errors:
        out.append(
            f"audit hook errors: {errors} -- the subprocess and thread "
            "records above are INCOMPLETE, and a short list there cannot be "
            "read as 'nothing was started'")
    return out


def declaration_lines(trace, m: dict) -> list[str]:
    """Why each absent bookkeeping key is absent -- as a declaration from
    format 4 on, as "predates" only for a trace that really does."""
    out: list[str] = []
    # An incomplete run is missing all of these for a reason already printed
    # at the top; saying it twice would bury the one that is news.
    if m.get("incomplete"):
        return out
    if trace.declares("threads") is None:
        # Predates declarations outright (no `capabilities` key): one
        # merged line, in the original key order and the original wording
        # -- this task changes nothing about a pre-format-4 trace's output.
        missing = [k for k in _BOOKKEEPING if k not in m]
        if missing:
            out.append("not recorded in this trace: " + ", ".join(missing)
                       + " -- it predates that bookkeeping, so absence of "
                         "the record is not a record of absence")
        return out
    # From format 4 an absence is a declaration, and `threads` and
    # `children` can be declared two different ways on the same trace --
    # grouped so a mixed case never borrows one capability's declaration to
    # describe the other's.
    missing_threads = [k for k in _THREAD_BOOKKEEPING if k not in m]
    if missing_threads:
        out.append("not recorded in this trace: "
                   + ", ".join(missing_threads) + " -- "
                   + witness_gap(trace, "threads", "thread", ""))
    missing_children = [k for k in _CHILD_BOOKKEEPING if k not in m]
    if missing_children:
        out.append("not recorded in this trace: "
                   + ", ".join(missing_children) + " -- "
                   + witness_gap(trace, "children", "child-process", ""))
    return out


def capabilities_line(trace) -> str:
    """What the trace DECLARES -- never what a reader assumed on its behalf.

    `Trace.capabilities` fills in `boot.CAPABILITIES` (every one true) for a
    Python trace carrying no `capabilities` key. That is the right reading
    for a command deciding whether to refuse -- the only recorder that
    existed had every capability -- but printing it here rendered an
    assumption as a declaration: a format-1 trace said `capabilities:
    children=yes line=yes ... tasks=yes threads=yes` two lines above
    `tasks: not recorded (format-1 trace; parentage assumed)`, about the
    same trace. `declares()` returns None for exactly that case and for no
    other, so it is what the branch reads.
    """
    if trace.declares("threads") is None:
        return ("undeclared (pre-format-4 Python recorder; read as full by "
                "every command)")
    return (" ".join(f"{k}={'yes' if v else 'no'}"
                     for k, v in sorted(trace.capabilities.items()))
            or "(none declared)")


def run(args) -> int:
    t = Trace.open(paths.find_trace(args.run))
    m = t.meta
    counts = t.counts()

    print(f"run {m.get('run_id', t.path.stem)}  trace: {t.path}")
    if m.get("incomplete"):
        print("INCOMPLETE: recording ended without a finalize pass "
              "(process died mid-record); exit/uncaught/children/"
              "truncated-count fields below are UNKNOWN, not zero")

    dur = ""
    if m.get("end_ts") and m.get("start_ts"):
        dur = f"  duration: {m['end_ts'] - m['start_ts']:.2f}s"
    print(f"cmd: {' '.join(m.get('argv', []))}    cwd: {m.get('cwd', '?')}")
    # meta["env"] is the entire process environment -- never print it
    # wholesale; env_hash lets two runs be compared without leaking it.
    words = terms(t)
    print(f"{words.interp_line(m)}  env:{m.get('env_hash', '?')}  "
          f"exit: {exit_phrase(m)}  events: {sum(counts.values())}"
          f"{dur}")
    print(f"recorder: {t.recorder}  lang: {t.lang}  "
          f"capabilities: {capabilities_line(t)}")
    print("recorded: " + "  ".join(f"{k} {counts.get(k, 0)}" for k in
                                   ("CALL", "RETURN", "RAISE", "HANDLED",
                                    "YIELD", "RESUME", "LINE")))
    focus = m.get("focus") or []
    print(f"focus: {', '.join(focus) if focus else '-'}    "
          f"window: {m.get('window') or '-'}")
    caps = m.get("caps", {})
    print("caps: " + " ".join(f"{k}={v}" for k, v in caps.items())
          + f"   truncated values: {m.get('truncated_count', 0)}")
    # A Rust trace's build facts, and its unwitnessed block, come BEFORE the
    # fingerprints: what a fingerprint row covers depends on which units
    # were instrumented at all, and a ceiling above it changes what every
    # count below means. A Python trace prints neither here and keeps its
    # unwitnessed block in its own place, below.
    rust = t.lang == "rust"
    if rust:
        for line in rust_lines(t, m):
            print(line)
    # What a fingerprint row covers is not readable from the hash, and plan
    # 2b narrowed it: under the per-task basis a thread row holds only what
    # ran in no asyncio task, and each task has a row of its own. Two traces
    # whose rows mean different things print identically without this, and a
    # reader comparing them by eye has nothing to go on.
    per_task = t.fingerprint_basis == "per-task"
    # The narrowing is a fact about THIS run, not only about the recorder's
    # version: a run that never made a task had nothing narrowed away, and
    # "(4 causal events outside any asyncio task)" beside "0 task
    # fingerprint(s)" invites a reader to go looking for the tasks. So the
    # qualifier and the count are gated on the run having tasks -- which is
    # the same gate `refocus._thread_scope` uses, and the two commands must
    # not describe one trace differently.
    ran_tasks = per_task and bool(t.tasks())
    scope = f" outside any {words.task_noun}" if ran_tasks else ""
    for tid, (h, n) in sorted(t.fingerprints().items()):
        tag = " (main)" if tid == t.main_thread_id() else ""
        print(f"fingerprint thread {tid}{tag}: {h} ({n} causal events{scope})")
    if per_task:
        # The basis line stays whatever the run did: it says how this
        # recorder defines a thread row, which is what a reader comparing
        # two traces by eye needs. Under Ruling 9 every task has a
        # fingerprint row, so this count is the task count -- a zero-count
        # row means that task ran no causal event while traced.
        beside = (f"; {len(t.task_fingerprints())} task fingerprint(s) "
                  "beside it" if ran_tasks else "")
        print("fingerprints: per-task basis -- each thread row covers the "
              f"events that ran in no {words.task_noun}{beside}")
    else:
        # Never claimed retroactively: a trace recorded before the marker
        # existed was fingerprinted the other way, and saying "0 task
        # fingerprints" about it would read as "no task ran".
        print("fingerprints: per-thread basis -- each thread row covers "
              "every causal event on the thread, task events included; no "
              "task fingerprints were recorded (recorded before they "
              "existed)")
    if m.get("uncaught"):
        print(f"uncaught: {fmt_exc(m['uncaught'])}")
    for child in m.get("children") or []:
        print(f"unwitnessed subprocess: {' '.join(child)}")
    if not rust:
        for line in unwitnessed_lines(t, m):
            print(line)
    # Always the JOIN, on every format. Arc 2 opens a frame for every traced
    # code object -- function, generator, coroutine, or async generator -- so
    # a format-3 trace is expected to have none of these, and the zero SAYS
    # so: a bare "unframed calls: 0" on an older trace means only that this
    # run happened to make none. But the reason is printed for a counted
    # zero, never instead of counting: reading the format and reporting a
    # count is the instrument describing a version number as though it had
    # looked at the trace.
    unframed = t.unframed_calls()
    if t.format >= 3 and not unframed:
        print("unframed calls: 0 (all calls framed in format 3)")
    else:
        kinds: dict[str, int] = {}
        for ev in unframed:
            k = (ev.payload or {}).get("unframed", "generator/coroutine")
            kinds[k] = kinds.get(k, 0) + 1
        detail = ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))
        print(f"unframed calls: {len(unframed)}"
              + (f" ({detail})" if detail else ""))
    if t.format < 2:
        print("tasks: not recorded (format-1 trace; parentage assumed)")
    elif t.tasks():
        print(f"tasks: {len(t.tasks())} ({_task_names(t.tasks(), words)})")
    else:
        # Not "no loop ran": a loop can run and never make a task -- and
        # loop callbacks run inside it with no current task at all.
        print(f"tasks: none (no event ran inside {words.a_task})")
    task_errors = m.get("task_errors", 0)
    if task_errors:
        print(f"task identity errors: {task_errors} -- the task identity "
              "lookup raised that many times (current_task(), or a Task "
              "subclass's __hash__/__eq__); those events carry NULL task_id "
              "meaning 'could not tell', not 'no task'")
    # late_writes is a lower bound: writes that arrive after this count was
    # captured can never be counted either. Only surface it when non-zero,
    # so a reader never mistakes a printed "0" for proof nothing was lost.
    late_writes = t.dropped_writes()
    # ...unless the loss was already reported, key by key, above: a Rust
    # trace's `seq_gaps` and `records_dropped` are two different facts with
    # two different provenances, and "late writes dropped" is neither.
    if late_writes and not (m.get("seq_gaps") or m.get("records_dropped")):
        print(f"late writes dropped: >={late_writes} (trace is incomplete "
              "for still-live threads; the true count may be higher)")
    if m.get("refocus_of"):
        # The verdict never travels alone. A bare MATCH here would read as a
        # clean bill of health for a rerun whose licence was withheld on
        # every count, and a bare DIVERGED gives the reader no way to see
        # WHAT diverged without re-running the comparison by hand.
        licence = m.get("refocus_licence")
        print(f"refocus-of: {m['refocus_of']}  "
              f"verdict: {m.get('refocus_verdict', 'UNVERIFIED')}"
              + (f"  licence: {licence}" if licence else ""))
        # Three ways a rerun can part, three separate stamps -- and a rerun
        # is stamped with the ones that apply, never with all of them. The
        # positional line is absent for a divergence that was not a step of
        # the compared thread's stream at all (`refocus` deliberately writes
        # no index for one), which is precisely when the task line below is
        # the whole answer: without it `info` printed a bare DIVERGED and
        # left the reader to re-run the comparison by hand.
        index = m.get("refocus_diverge_index")
        if index is not None:
            # Indexed, not `.get(..., '?')`: `refocus._stamp` writes these
            # three keys in one block and always has, so a '?' here could
            # only ever be printed by a trace this project did not write. A
            # fallback for that case is a fallback nothing can reach, and it
            # reads as though the value were sometimes genuinely unknown.
            print(f"  diverged at causal step {index}: "
                  f"A {m['refocus_diverge_a']} / B {m['refocus_diverge_b']}")
        if m.get("refocus_thread_divergence"):
            print(f"  diverged on threads: {m['refocus_thread_divergence']}")
        if m.get("refocus_diverge_tasks"):
            print(f"  diverged on tasks: {m['refocus_diverge_tasks']}")
        for reason in m.get("refocus_licence_reasons") or []:
            print(f"  licence withheld: {reason}")
        # A granted licence without its points is the bad news keeping its
        # qualifications while the good news loses them. The terminal prints
        # five itemised facts and the blind spots; what persisted was the
        # word "granted", which reads as unbounded -- exactly the failure the
        # comment in `runs_cmd` names one level up. `refocus` has been
        # stamping these into the trace all along; nothing read them.
        verified = m.get("refocus_licence_verified") or []
        for fact in verified:
            print(f"  licence verified: {fact}")
        if licence == "granted" and not verified:
            print("  licence granted, but this trace does not record WHAT it "
                  "was granted on -- it predates that record; re-run "
                  "`sensorium refocus` for the bounded list")
        for reason in m.get("refocus_refused_reasons") or []:
            print(f"  refused: {reason}")
    counts_by_code = t.call_counts()
    hot = sorted(((c, counts_by_code.get(c.id, 0)) for c in t.codes()),
                 key=lambda x: -x[1])[:8]
    if hot:
        print("hot functions:")
        for code, n in hot:
            if n:
                print(f"  {n}x {code.file.rsplit('/', 1)[-1]}:{code.qualname}")
    return ANSWERED


_DEFAULT_TASK_NAME = re.compile(r"^Task-\d+\Z")
_TASK_LIST_CAP = 8


def _task_names(tasks, words) -> str:
    """Up to eight tasks: every one, `tN name`. More: names grouped and
    counted, most frequent first, asyncio's default `Task-N` names (a
    creation counter, not an identity) folded into one group. A FastAPI test
    run recorded 166 tasks and the flat list said nothing a reader could
    use; "2 distinct name(s): …coro x120, Task-N x46" does."""
    default_names = words.default_name_note is not None
    if len(tasks) <= _TASK_LIST_CAP:
        return ", ".join(
            f"t{k.id} {k.name if k.name is not None else words.unnamed_task}"
            for k in tasks)
    groups = Counter()
    for k in tasks:
        if k.name is None:
            label = words.unnamed_task
        elif default_names and _DEFAULT_TASK_NAME.match(k.name):
            label = "Task-N (asyncio default names)"
        else:
            label = k.name
        groups[label] += 1
    shown = groups.most_common(6)
    rest = len(groups) - len(shown)
    body = ", ".join(f"{name} x{n}" for name, n in shown)
    tail = f"; and {rest} more name(s)" if rest else ""
    return f"{len(groups)} distinct name(s): {body}{tail}"
