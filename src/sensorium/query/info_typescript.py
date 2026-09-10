"""What `info` prints about a trace only the TypeScript recorder writes.

Split from `info_cmd` for the reason `info_rust` is: these are facts about
how a HARNESS and a CONTAINER produced a recording -- which harness the
driver waited for, which test file this worker ran, how many tests the
transform reached of the ones the harness registered, what the transform
excluded -- and none of them exist in a Python or a Rust trace. Keeping
them here means `info_cmd.run` gets one call on a gate it already
computes, and no other trace's output can drift by accident.

THREE EXIT FACTS, THREE LINES, NEVER MERGED
-------------------------------------------
`typescript/HONESTY.md` section 6 states the rule and this module keeps it:

* `exit_status` / `exit_status_basis` -- the CONTAINER's status, always
  `null` / `unwitnessed`, because the driver spawned the harness and not
  its workers. Printed by the shared `vocab.exit_phrase` on `info`'s own
  interpreter line, as `exit: unwitnessed`.
* `exit_self_reported` -- what the container said about its OWN ending,
  from inside, on the way out. Nobody waited for it, and the line says so.
* `harness_exit` -- what the driver really did wait for, with the basis
  attached.

Three processes, three facts. Rendering any of them wearing another's name
is the failure the whole exit rule exists to stop.

Every line is gated on the meta key it reports, never on the language: a
TypeScript trace written by an older converter that carries none of these
keys prints none of these lines, which is the rule the rest of `info`
follows. Zero counts are printed where the count IS the finding
(`throw flow outside frames` is not: a zero there is silence about records
that arrived nowhere) and where the recorder can prove it looked -- the
`unhandledRejection` listener always ran, so on a COMPLETE trace a zero is
measured, and on an incomplete one it is only how far the count got.
"""


def interp_suffix(m: dict) -> str:
    """What ran the program, beyond the interpreter: ` (vitest 4.1.9,
    jsdom)`.

    `node v24.16.0` alone is true and nearly useless -- every container of
    every TypeScript recording says it. The harness version and the DOM
    environment are what change a run's behaviour, and both are recorded
    per invocation, so they belong on the line a reader compares two runs
    by. Each half is gated on its own key; with neither there is no
    parenthesis, not an empty one.
    """
    parts = []
    if m.get("vitest"):
        parts.append(f"vitest {m['vitest']}")
    if m.get("environment"):
        parts.append(m["environment"])
    return f" ({', '.join(parts)})" if parts else ""


def typescript_lines(trace, m: dict) -> list[str]:
    """The TypeScript block, in the order `info` prints it: what ran the
    harness, what this container was, how it ended, then what the recording
    reached and what it did not.

    The harness comes first because it is the only line about a process the
    reader can go and look at another trace of; the container's own
    identity follows, and the counts that qualify what every number below
    them means come after both.
    """
    return (_harness_line(m)
            + _container_line(m)
            + _self_reported_line(m)
            + _tests_line(trace, m)
            + _files_line(m)
            + _flow_lines(m))


def _harness_line(m: dict) -> list[str]:
    """The command the driver spawned and waited for, AS TYPED (R26).

    `harness_command` is the tokens the user gave after `--`, before the
    driver consumed `--root`/`--config` out of them and before it re-issued
    its own. Nothing else here is a command: `harness` is the KIND the
    driver recognised and `harness_args` is what survived the consumption,
    so joining the two builds a string nobody typed -- `node-test --test
    test/` names no program, and the user's `--root` is simply gone from
    it. That join is kept only as the fallback for a trace whose converter
    predates the key, where the alternative is printing nothing.

    Shared with `runs`' invocation header by rule and not by call: the two
    print the same fact in two different layouts, and this is the sentence
    both are checked against (`v23`, `v28`).
    """
    typed = m.get("harness_command")
    if typed:
        cmd = " ".join(typed)
    elif m.get("harness"):
        cmd = " ".join([m["harness"], *(m.get("harness_args") or [])]).rstrip()
    else:
        return []
    return [f"harness: {cmd}{_harness_ending(m)}"]


def _harness_ending(m: dict) -> str:
    """`  exit: 1 (waited)`, and nothing at all with no record.

    An absent `harness_exit` is a driver killed before the harness returned
    -- `ingest` is re-runnable over exactly that spool directory -- and is
    not a harness that ended at 0. `status` and `signal` are exclusive.
    """
    ending = m.get("harness_exit")
    if not ending:
        return ""
    basis = ending.get("basis", "waited")
    if ending.get("status") is not None:
        return f"  exit: {ending['status']} ({basis})"
    if ending.get("signal") is not None:
        return f"  exit: signal {ending['signal']} ({basis})"
    return ""


def _container_line(m: dict) -> list[str]:
    """Which process and thread this trace IS, and which test file it ran.

    `(main|worker)` is `is_main_thread`, and it is worth a word because it
    decides what the absence of a `threads_started` record means here: a
    worker's siblings are other traces of this same invocation, unlinked.
    """
    if "pid" not in m:
        return []
    line = f"container: pid {m['pid']}"
    if "thread_id_os" in m:
        where = "main" if m.get("is_main_thread") else "worker"
        line += f"  thread {m['thread_id_os']} ({where})"
    one = m.get("test_file")
    several = m.get("test_files")
    if one:
        line += f"  file: {one}"
    elif several:
        line += f"  files: {len(several)}"
    return [line]


def _self_reported_line(m: dict) -> list[str]:
    """What the container said about its own ending on the way out.

    `(nobody waited)` is not decoration: this number came from inside the
    process that was ending, which is exactly the kind of status the exit
    rule refuses to print bare. A container that never got to observe its
    own ending carries no key and gets no line -- which is not the same
    fact as one that ended at 0.
    """
    ending = m.get("exit_self_reported")
    if not ending:
        return []
    if ending.get("code") is not None:
        return [f"container exit: self-reported code {ending['code']} "
                "(nobody waited)"]
    if ending.get("signal") is not None:
        return [f"container exit: self-reported signal {ending['signal']} "
                "(nobody waited)"]
    # The record exists and carries neither. Said rather than dropped: a
    # missing line means "no EXIT record", and this is not that.
    return ["container exit: self-reported, but the record carries neither "
            "a code nor a signal"]


def _tests_line(trace, m: dict) -> list[str]:
    """How many tests the transform reached, of the ones the harness ran.

    The shortfall is the finding. A test the transform did not wrap ran and
    was recorded by nothing, so a bare count of tasks would read as the
    whole test file; the setup file counts what the HARNESS registered so
    the difference can be stated instead of being silence
    (`typescript/HONESTY.md` section 2).

    Where nobody counted -- `node --test`, which runs no setup file -- the
    key is absent and the clause is not printed at all (R38). It read
    `tests: 2 as tasks, 0 seen by the harness` there, a zero nothing
    measured, which invites exactly the subtraction the clause exists to
    make possible.
    """
    tasks = len(trace.tasks())
    line = f"tests: {tasks} as tasks"
    seen = m.get("tests_seen")
    if seen is not None:
        line += f", {seen} seen by the harness"
        if seen > tasks:
            line += (f"; {seen - tasks} registered through a shape the "
                     "transform did not wrap")
    line += _naming(m)
    return [line]


def _naming(m: dict) -> str:
    """Which rule named this trace's tasks, and how often it disagreed.

    A conflict is a provider name that did not end with the string literal
    the transform passed; the task then falls back to its lexical title and
    the disagreement is counted rather than resolved. The count travels
    with the basis it qualifies -- alone it would name no rule to doubt.
    """
    basis = m.get("task_name_basis")
    conflicts = m.get("task_name_conflicts") or 0
    if basis:
        return (f"; task names: {basis}"
                + (f", {conflicts} conflict(s)" if conflicts else ""))
    return f"; {conflicts} task name conflict(s)" if conflicts else ""


def _files_line(m: dict) -> list[str]:
    """What the transform edited, and what it refused, BY REASON.

    A count of exclusions with no reasons is a number a reader cannot act
    on; the reasons are the difference between "nothing happened in that
    file" and "nothing was watching it". An empty exclusion map prints no
    clause, because there is nothing to name.
    """
    if "files_transformed" not in m:
        return []
    line = f"files: {m['files_transformed']} transformed"
    excluded = m.get("transform_excluded") or {}
    if excluded:
        detail = ", ".join(f"{reason} x{n}"
                           for reason, n in sorted(excluded.items()))
        line += f"; excluded: {sum(excluded.values())} ({detail})"
    return [line]


def _flow_lines(m: dict) -> list[str]:
    """The two things this recorder counts instead of writing an event for.

    An unhandled rejection has no site, and a throw with no open frame has
    no frame -- a causal event with no `code_id` is refused by the contract
    and inventing a code object would put a site in the program that has
    none (`typescript/HONESTY.md` section 4). The count is the only trace
    of either.

    The rejection count prints its ZERO on a complete trace, because the
    listener always ran: that zero is measured. On an incomplete trace it
    is only how far the counting got, and is withheld on the `late_writes`
    precedent. The outside-frames count is withheld at zero on that
    precedent either way -- nothing in the recording proves a throw at
    module scope would have been noticed.
    """
    out = []
    rejections = m.get("unhandled_rejections")
    if rejections or (rejections is not None and not m.get("incomplete")):
        out.append(f"unhandled rejections: {len(rejections)}")
    outside = m.get("throw_flow_outside_frames") or 0
    if outside:
        out.append(f"throw flow outside frames: {outside}")
    return out
