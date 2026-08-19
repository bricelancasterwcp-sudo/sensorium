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
                                    "LINE")))
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
        for reason in m.get("refocus_refused_reasons") or []:
            print(f"  refused: {reason}")
    hot = sorted(((c, len(t.frames(code_id=c.id))) for c in t.codes()),
                 key=lambda x: -x[1])[:8]
    if hot:
        print("hot functions:")
        for code, n in hot:
            if n:
                print(f"  {n}x {code.file.rsplit('/', 1)[-1]}:{code.qualname}")
    return 0
