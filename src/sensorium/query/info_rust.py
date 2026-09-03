"""What `info` prints about a trace only the Rust recorder writes.

Split from `info_cmd` for one reason: these are facts about how a BUILD
recorded a process -- which units were instrumented, which fell back, which
file was never reached, whether recording refused a further unit -- and none
of them exist in a Python trace. Keeping them here means `info_cmd.run` has
one extra call and no extra branch, and a Python trace's output cannot drift
by accident.

Every line is gated on the meta key it reports, never on the language: a
Rust trace written by an older converter that carries none of these keys
prints none of these lines, which is the same rule the rest of `info`
follows. Zero counts are printed where the count IS the finding (`units:`),
and withheld where a printed zero would read as proof (`seq gaps`,
`records dropped`, `panics unrecorded`) -- the `late_writes` precedent.
"""
from collections import Counter


def rust_lines(trace, m: dict) -> list[str]:
    """The Rust block, in the order `info` prints it: what built this
    process, what it recorded, then everything it could not follow.

    The declaration comes BEFORE the counts it qualifies, and the child runs
    immediately after the declaration that says spawns were not witnessed:
    a list of joined children read on its own is an inventory, and the
    declaration is what stops it being read as a complete one.
    """
    # Local: `info_cmd` imports THIS module, and the two halves of its
    # unwitnessed block are what this order rearranges -- importing them at
    # module level would be a cycle, and duplicating their wording here
    # would be two sentences about one fact.
    from sensorium.query.info_cmd import declaration_lines, witnessed_counts
    return (_build_lines(m)
            + declaration_lines(trace, m)
            + _child_runs(m)
            + _live_threads(m)
            + witnessed_counts(trace, m)
            + _loss_lines(m)
            + _panic_lines(m))


def _build_lines(m: dict) -> list[str]:
    out = []
    if m.get("invocation"):
        binary = str(m.get("exe", "?")).rsplit("/", 1)[-1]
        out.append(f"invocation: {m['invocation']}  binary: {binary}  "
                   f"pid: {m.get('pid', '?')}")
    if "instrumented_units" in m:
        out.append(_units_line(m))
    unreached = m.get("unreached_files") or []
    if unreached:
        # Named, never counted alone: "1 file was not reached" leaves the
        # reader unable to tell whether the code they are looking for is in
        # it. A file nothing reached is a hole in the trace with an address.
        out.append(f"unreached files: {len(unreached)} -- "
                   + ", ".join(unreached))
    refused = m.get("units_refused") or {}
    if refused.get("refused"):
        # The most consequential absence this recorder can have: everything
        # after this point in the process is missing, and nothing else in
        # the trace says so. A reader who takes the event list as complete
        # after a ceiling is reading a truncated run as a whole one.
        out.append(f"unit ceiling: recording REFUSED at unit "
                   f"{refused.get('at', '?')} -- every later call in this "
                   "process is unrecorded")
    return out


def _units_line(m: dict) -> str:
    """One line for the build: instrumented, fell back, skipped, spawn
    sites. The zeros are printed here because the count is the claim -- "0
    fell back" is what says the whole workspace was instrumented -- and each
    non-zero carries its reasons, because "3 skipped" without them cannot be
    told from "3 functions this recorder cannot see"."""
    units = m.get("instrumented_units") or []
    spawns = m.get("spawns") or []
    wrapped = sum(1 for s in spawns if s.get("wrapped"))
    return (f"units: {len(units)} instrumented, "
            f"{_with_reasons(m.get('uninstrumented'), 'fell back')}, "
            f"{_with_reasons(m.get('skipped'), 'skipped')}, "
            f"{len(spawns)} spawn sites ({wrapped} wrapped)")


def _with_reasons(entries, verb: str) -> str:
    entries = entries or []
    if not entries:
        return f"0 {verb}"
    reasons = Counter(e.get("reason") or "?" for e in entries)
    detail = ", ".join(f"{r} x{n}" for r, n in sorted(reasons.items()))
    return f"{len(entries)} {verb} ({detail})"


def _child_runs(m: dict) -> list[str]:
    kids = m.get("child_runs") or []
    if not kids:
        return []
    return [f"child runs: {len(kids)} -- "
            + ", ".join(str(k.get("run_id", "?")) for k in kids)]


def _live_threads(m: dict) -> list[str]:
    """Threads that never ended. The process DID finish, so the trace is not
    INCOMPLETE -- and that is exactly the pair a reader misreads one way or
    the other (`rust/HONESTY.md` section 4), so both halves are said."""
    live = m.get("live_threads") or []
    if not live:
        return []
    return [f"live threads: {len(live)} -- " + ", ".join(str(t) for t in live)
            + " -- still running when the process ended: their frames are "
              "left open and no ending for them was recorded, which is not "
              "the same fact as an INCOMPLETE recording and is not printed "
              "as one"]


def _loss_lines(m: dict) -> list[str]:
    """Two different numbers, never merged: `seq_gaps` is INFERRED from a
    hole in the process-global sequence, `records_dropped` is WITNESSED by a
    writer that knew it could not write. Both are bounded losses and both
    make `diff` refuse a verdict (`Trace.dropped_writes`)."""
    out = []
    gaps = m.get("seq_gaps") or 0
    if gaps:
        out.append(f"seq gaps: {gaps} -- records minted and never found in "
                   "any spool (one lost mid-write per thread at most; see "
                   "rust/HONESTY.md §4)")
    dropped = m.get("records_dropped") or {}
    total = sum(int(v) for v in dropped.values() if v is not None)
    if total:
        detail = ", ".join(f"thread {k}: {v}" for k, v in
                           sorted(dropped.items(), key=_serial_key))
        out.append(f"records dropped: {total} -- records the runtime knew it "
                   f"could not write ({detail}); a thread whose spool could "
                   "not be mapped or grown is inert from that point on")
    return out


def _serial_key(item) -> tuple:
    """Thread serials are NUMBERS carried in JSON object keys, which are
    strings: sorting them as strings puts thread 10 before thread 2, and a
    reader scanning for a thread finds it in the wrong place. Anything not a
    plain integer sorts after the numbers, by its own text, rather than
    raising on a key this reader did not write."""
    key = str(item[0])
    return (0, int(key), "") if key.isdigit() else (1, 0, key)


def _panic_lines(m: dict) -> list[str]:
    out = []
    unrecorded = m.get("panics_unrecorded") or 0
    if unrecorded:
        out.append(f"panics unrecorded: {unrecorded} -- frames that unwound "
                   "with no PANIC record on their thread (hook replaced, or "
                   "the panic began before recording)")
    outside = m.get("panics_outside_frames") or 0
    if outside:
        out.append(f"panics outside frames: {outside} -- panics recorded on "
                   "a thread with no open frame, so there is no frame to "
                   "attach a RAISE to and none was written")
    return out
