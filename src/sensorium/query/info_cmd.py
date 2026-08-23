"""Summarize one trace: shape, exceptions, caps, honesty flags.

`meta` only guarantees every key for a run that finished normally. A run
whose `install()` failed is written with `incomplete=True` and never gets
its finalize pass, so it has no `exit_status`, no `uncaught`, no `children`
and no `truncated_count` at all -- every read below goes through `.get()`
with a fallback, and the INCOMPLETE flag is printed first, not buried.
"""
from sensorium import paths
from sensorium.query.fmt import fmt_exc
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("info", help="summarize one trace")
    p.add_argument("run")
    p.set_defaults(func=run)


_BOOKKEEPING = ("children", "threads_started", "spawn_syscalls",
                "audit_errors")


def unwitnessed_lines(m: dict) -> list[str]:
    """Everything the recorder NOTICED starting and could not witness.

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
            f"threads started: {started} besides the main one, through "
            "Python's own threading/_thread -- one that ran no traced code "
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
    # An incomplete run is missing all of these for a reason already printed
    # at the top; saying it twice would bury the one that is news.
    missing = [k for k in _BOOKKEEPING if k not in m]
    if missing and not m.get("incomplete"):
        out.append("not recorded in this trace: " + ", ".join(missing)
                   + " -- it predates that bookkeeping, so absence of the "
                     "record is not a record of absence")
    return out


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
    print(f"python {m.get('python', '?')}  env:{m.get('env_hash', '?')}  "
          f"exit: {m.get('exit_status', '?')}  events: {sum(counts.values())}"
          f"{dur}")
    print("recorded: " + "  ".join(f"{k} {counts.get(k, 0)}" for k in
                                   ("CALL", "RETURN", "RAISE", "HANDLED",
                                    "YIELD", "RESUME", "LINE")))
    focus = m.get("focus") or []
    print(f"focus: {', '.join(focus) if focus else '-'}    "
          f"window: {m.get('window') or '-'}")
    caps = m.get("caps", {})
    print("caps: " + " ".join(f"{k}={v}" for k, v in caps.items())
          + f"   truncated values: {m.get('truncated_count', 0)}")
    for tid, (h, n) in sorted(t.fingerprints().items()):
        tag = " (main)" if tid == t.main_thread_id() else ""
        print(f"fingerprint thread {tid}{tag}: {h} ({n} causal events)")
    if m.get("uncaught"):
        print(f"uncaught: {fmt_exc(m['uncaught'])}")
    for child in m.get("children") or []:
        print(f"unwitnessed subprocess: {' '.join(child)}")
    for line in unwitnessed_lines(m):
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
        names = ", ".join(
            f"t{k.id} {k.name if k.name is not None else '(name unreadable)'}"
            for k in t.tasks())
        print(f"tasks: {len(t.tasks())} ({names})")
    else:
        # Not "no loop ran": a loop can run and never make a task -- and
        # loop callbacks run inside it with no current task at all.
        print("tasks: none (no event ran inside an asyncio task)")
    task_errors = m.get("task_errors", 0)
    if task_errors:
        print(f"task identity errors: {task_errors} -- the task identity "
              "lookup raised that many times (current_task(), or a Task "
              "subclass's __hash__/__eq__); those events carry NULL task_id "
              "meaning 'could not tell', not 'no task'")
    # late_writes is a lower bound: writes that arrive after this count was
    # captured can never be counted either. Only surface it when non-zero,
    # so a reader never mistakes a printed "0" for proof nothing was lost.
    late_writes = m.get("late_writes", 0)
    if late_writes:
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
        if m.get("refocus_thread_divergence"):
            print(f"  diverged on threads: {m['refocus_thread_divergence']}")
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
    return 0
