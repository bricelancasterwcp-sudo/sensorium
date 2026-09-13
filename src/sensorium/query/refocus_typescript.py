"""`refocus` on a TypeScript trace: re-run the whole harness invocation,
then compare ONE container of it.

`refocus_cmd` owns the command and `refocus_rust` is the shape this file
follows; what is here is the ONE thing a TypeScript recording does
differently, and it is not the thing Rust's file is about. A Rust refocus
cannot re-run in this process either, but what it asks the driver for is one
build of one target, and the driver hands back one trace. A vitest
invocation is a POOL: `npx vitest run src/config` starts a harness that
starts as many worker containers as it likes, each recording its own trace,
and the reader asked about exactly one of them. So this branch re-runs the
whole invocation -- there is no way to ask a harness for one container
without changing what it does -- and then has to say WHICH of the traces
that came back is the pair, and what it is claiming about the rest.

Everything else -- the comparator, the verdict, the assessment, the report,
the stamps, the licence, the environment rule -- is called unchanged, from
`refocus_cmd`, `refocus_report` and `refocus_world`. Three verdict
vocabularies for one question is how three languages would come to disagree
about what MATCH means (design 2026-09-07, G2).

WHAT THIS FILE MAY REFUSE, AND WHY EACH REFUSAL IS BEFORE THE RE-RUN
---------------------------------------------------------------------
A suite costs minutes and has side effects of its own. Every condition that
would make the answer meaningless is therefore checked BEFORE anything is
launched, and each one exits 2 (`BAD_CALL`, "fix the call") rather than 3,
for the reason `_refuse` states: nothing ran, so the reader's next move is a
different command. The seven, in the order design 2026-09-13 section 2.3
fixes:

1. `--window` -- this recorder has no per-activation gate at all. Accepting
   the flag and ignoring it would report a narrowing that never happened.
2. the original was recorded at `--tier off` -- it holds no causal stream,
   so the comparison the re-run is FOR could not be made whatever came
   back. Cheap to check and the fix is a re-recording, not a flag.
3. no `harness_command` -- a trace from a driver before the key existed.
   There is nothing to re-run, and guessing a command is guessing.
4. no `harness_cwd` -- sensorium ts 0.13.0 or earlier. The command's own
   arguments are relative to the directory it was TYPED in, which is a
   third directory beside the container's `cwd` and the plan's `root`
   (design section 2.2); without it the re-run has nowhere to start.
5. `harness_cwd` gone -- the same fact the Python branch checks about `cwd`
   and the Rust branch about `workspace_root`.
6. `root` gone -- the project the plan was made against. A harness cwd that
   still exists over a project that does not is a different fact and gets a
   different sentence.
7. the container was a REUSED WORKER -- it ran more than one test file, so
   "which container of the re-run is its pair" has no answer at all. This is
   the one Rust has no counterpart for; `test_files_run` below is the half
   of it that the harness does not report.

The sentences carry no `REFUSED:` prefix of their own: `_refuse` prints
`error: cannot refocus <run>: <sentence>`, and two announcements of one
refusal read as two refusals. Everything after the design's prefix is
verbatim, `; nothing was re-run` included.

THE PAIR IS FOUND IN THE STORE, BY TEST FILE, AND NEVER PARSED
---------------------------------------------------------------
The driver prints a `run:` line per container. Reading the new run ids off
them would put a load-bearing link in this process's memory only, and a
changed print would break `refocus` silently (design 2026-09-07, G3). So the
driver stamps `refocus_of` into every trace of the invocation and
`find_pair` asks the STORE which traces carry it; the `run:` lines go to the
terminal and decide nothing.

Linked is not the same as PAIRED, and that is this branch's own problem. A
suite of 372 test files re-runs as 372 linked traces, of which the reader
asked about one. `pair_key` is what picks it: the container's `test_file`
where it has one, its whole `argv` where it does not (a `node --test`
process, a script). The rest are SIBLINGS -- counted on the pair line and
stamped as a count, never compared, and `runs` lists them under the new
invocation with no verdict, which is exactly what they have. A count rather
than a list of ids because the invocation id already names them and 371 ids
is not something a reader follows.

The timestamp filter in `find_pair` is not belt-and-braces, for the reason
`refocus_rust.find_pair` gives at length: without it the SECOND refocus of
one original finds the first one's traces as well as its own, and "more than
one candidate" is a refusal -- so a second refocus of any run would fail
permanently. A trace that records no readable `start_ts` is EXCLUDED rather
than assumed recent: it cannot be shown to be this re-run's.

NOTHING IS CAPTURED, AND NOTHING PRINTED IS PARSED
---------------------------------------------------
All three streams are inherited. The Rust branch captures stdout so it can
echo the driver's `run:` lines after a rebuild that printed nothing for
minutes; a test suite prints continuously and the person who asked for a
refocus is watching it -- a captured suite is a suite that appears to hang.
No timeout, for the reason the other two branches give: a suite's length is
the caller's to judge, and a timeout that killed one half way would leave
the store in exactly the state ("no trace linked to this run") this file
reports as REFUSED.
"""
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from sensorium import paths
# The two verdict paths this branch shares with the Rust one. Imported, not
# copied: both print sentences with no language in them -- "the re-run
# happened and produced no comparable pair" is one verdict with one exit
# code, and "these checks could not run" is one finding about a pair --
# and two spellings of one sentence is how two branches come to report the
# same fact differently (ruling P2, 2026-09-13).
from sensorium.query.refocus_rust import (_print_unverifiable,
                                          _refused_after_rerun)
# The licence and world code at its shared home. `env_of` takes this
# branch's own `is_recorder_key` because which variables are the recorder's
# bookkeeping is the one part of the environment rule that is per-language;
# everything done with the answer is shared.
from sensorium.query.refocus_world import (_source_state, env_of, relicense,
                                           stamp_unverifiable,
                                           unverifiable_checks)
from sensorium.store import db
from sensorium.store.reader import Trace

#: The meta key holding how many OTHER containers of the re-run invocation
#: were linked to the original. Stamped on the pair alone (design section
#: 2.4): it is a fact about the comparison, and a sibling has no comparison.
SIBLINGS_KEY = "refocus_siblings"

#: What a test file's name looks like to this reader. vitest's own default
#: `include` is `**/*.{test,spec}.?(c|m)[jt]s?(x)`, so the two infixes are
#: the harness's own convention and not this tool's invention.
_TEST_INFIXES = (".test.", ".spec.")


def is_recorder_key(name: str) -> bool:
    """Whether this variable is the RECORDER's own bookkeeping.

    The same judgement `_UNCOMPARED_ENV` makes about `SENSORIUM_DIR`, and
    for the same measured reason -- reporting the tool's own footprint as a
    change the world made is noise, not honesty. Here it is not optional: a
    focused re-run changes `SENSORIUM_FOCUS` by definition and mints a fresh
    `SENSORIUM_INVOCATION` and `SENSORIUM_SPOOL` per container, so compared,
    those fire on EVERY TypeScript refocus -- and a check that always fires
    says nothing.

    A PREFIX, unlike the Rust predicate's third clause, because every
    variable this recorder sets is under one: `SENSORIUM_TS_PKG`,
    `SENSORIUM_TS_ROOT`, `SENSORIUM_MANIFEST_DIR` and `SENSORIUM_TIER`
    beside the three above. The names are printed beside the count rather
    than hidden behind it, which is the rule the shell list follows too.
    """
    return name.startswith("SENSORIUM_")


# -- what the trace says its tests ran in ----------------------------------
def _relative_to_root(path: str, root) -> str:
    """`path` under `root`, or `path` exactly as it was recorded.

    Root-relative where it CAN be, because `meta.test_file` and
    `meta.test_files` are the harness's own spelling and that spelling is
    relative to the project root: two spellings of one file would read as
    two files and refuse a container that ran one. As recorded otherwise --
    a file outside the root has no relative spelling, and inventing one
    (`../../x.test.ts`) would name a path neither the trace nor the harness
    ever used.
    """
    if not root:
        return path
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return path


def test_files_run(trace: Trace) -> list[str]:
    """The distinct test files this container's tests ROOTED in, sorted.

    Ruling P3, condition (b), and it exists because the harness does not
    report the fact condition (a) reads. Under vitest 4.1.9 `--no-isolate
    --maxWorkers 1` ONE container runs both test files, but the setup file's
    top-level `rt.fileStart(...)` runs once under a shared module cache, so
    the trace records `test_file` (singular, the first file) and never
    `test_files`. The trace still KNOWS: a test is a task, its root frame is
    the callback vitest invoked, and that frame's code object names the file
    it was written in.

    A task ROOT frame is a depth-0 frame whose CALL ran inside a task --
    read through the reader's own accessors (`frames`, `event`, `code`), the
    same path `frame_cmd` takes to name a frame's task, because a second SQL
    spelling of "which task is this frame in" is a second answer waiting to
    disagree with the first.

    Only files whose name carries `.test.` or `.spec.` are counted, and that
    is the BOUND blind spot 42 states: a second test file whose callbacks
    all root in a shared helper is invisible here, and the container pairs
    by its first file. Counting every distinct root file instead would
    refuse every suite that keeps its assertions in a helper -- a refusal on
    a single-file container is the worse of the two errors, because the
    reader can do nothing about it.
    """
    root = trace.meta.get("root")
    files = set()
    for frame in trace.frames():
        if frame.depth != 0:
            continue
        call = trace.event(frame.call_event_id)
        if call is None or call.task_id is None:
            continue
        path = trace.code(frame.code_id).file
        if any(infix in os.path.basename(path) for infix in _TEST_INFIXES):
            files.add(_relative_to_root(path, root))
    return sorted(files)


# -- may this recording be re-run at all? ----------------------------------
def refusal(meta: dict, args, trace: Trace) -> str | None:
    """Why re-running this TypeScript recording would be illegitimate.

    Order is the design's and is load-bearing in one direction: the cheap,
    always-answerable questions about the CALL come first, then the ones
    about the world, then the one about the harness's own scheduling --
    so a call that is wrong in two ways is told about the one the reader can
    act on soonest.

    `trace` is required rather than defaulted: refusal 7 is derived from the
    trace's own frames, and a call site that passed only the metadata would
    silently skip the check that the harness this refusal exists for is the
    only one that needs.
    """
    if getattr(args, "window", None) is not None:
        return ("--window is not available for a TypeScript trace (the "
                "recorder has no per-activation gate); nothing was re-run")
    run = meta.get("run_id") or "this run"
    if (meta.get("env") or {}).get("SENSORIUM_TIER") == "off":
        return (f"run {run} was recorded at --tier off and holds no causal "
                "stream to compare against; nothing was re-run")
    if not meta.get("harness_command"):
        return (f"run {run} records no harness command to re-run (recorded "
                "by a driver before the key existed); nothing was re-run")
    cwd = meta.get("harness_cwd")
    if not cwd:
        return (f"run {run} records no working directory to re-run from "
                "(recorded by sensorium ts 0.13.0 or earlier); nothing was "
                "re-run")
    if not os.path.isdir(cwd):
        return f"directory {cwd} no longer exists; nothing was re-run"
    root = meta.get("root")
    # Absent `root` is not checked: the key arrived with the same driver
    # `harness_cwd` did, so a trace that has one has both, and a refusal on
    # its absence would be a second sentence for the fact refusal 4 already
    # reported.
    if root and not os.path.isdir(root):
        return f"project root {root} no longer exists; nothing was re-run"
    # The converter's own report where it made one, the trace's frames
    # otherwise -- never both: a converter that lists the file starts has
    # seen every one of them, including files whose tests rooted in a
    # helper, and second-guessing it with a narrower derivation would
    # report the smaller number as the fact.
    declared = meta.get("test_files")
    n = len(declared) if declared else len(test_files_run(trace))
    if n >= 2:
        return (f"run {run} ran {n} test files in one container (a reused "
                "worker); which container of a re-run would be its pair is "
                "the harness's scheduling, not a fact; nothing was re-run")
    return None


# -- the re-run ------------------------------------------------------------
def rerun_argv(meta: dict, requested_focus, run_id: str) -> list[str]:
    """The invocation that re-records this run's whole suite, deeper.

    `sys.executable -m sensorium`, never a `sensorium` on PATH: the re-run
    must be recorded by THIS sensorium, and a name on the path could resolve
    to another version entirely -- the pair would then be compared across
    two recorders, which is the one thing the verdict may not rest on.

    `--refocus-of` is what makes the new traces findable afterwards, so it is
    first and unconditional. `--tier` is the ORIGINAL's, read from its
    recorded environment: omitted when the key is absent, so the driver's own
    default applies rather than this file asserting one. The focus list is
    `refocus_cmd._merged_focus`'s -- the original's values then the caller's,
    never fewer than the original's -- and reusing that function is the
    point: "a refocus only ever captures MORE" must mean the same thing in
    all three languages.

    `harness_command` goes last, after a bare `--`, and verbatim: it is the
    tokens as they were typed, and the `--` is what stops the driver reading
    the harness's own flags as its own.
    """
    from sensorium.query.refocus_cmd import _merged_focus

    argv = [sys.executable, "-m", "sensorium", "ts", "run",
            "--refocus-of", run_id]
    tier = (meta.get("env") or {}).get("SENSORIUM_TIER")
    if tier:
        argv += ["--tier", str(tier)]
    for value in _merged_focus(meta, requested_focus):
        argv += ["--focus", value]
    return argv + ["--", *[str(a) for a in meta["harness_command"]]]


def _launch(argv: list[str], cwd: str, store: Path) -> tuple[float, object]:
    """Run the harness from the directory it was typed in, under the
    original's store.

    `SENSORIUM_DIR` is the resolved ABSOLUTE store of the original, for the
    reason `refocus_cmd._pin_trace_store` states one level up: a relative
    value would follow the child into the project and write the new traces
    where `find_pair` -- and `sensorium runs` -- will never look. Nothing
    else is set or stripped, so the environment the re-run executed under is
    the caller's, and the two traces' own recorded environments are what the
    licence check compares afterwards.

    No stream is captured. The harness's output is what a person waiting on
    a suite is watching, and the driver's own `run:` lines print live with
    it; a captured suite is a suite that appears to hang. Nothing printed is
    parsed -- the pair comes out of the store.
    """
    launched_at = time.time()
    proc = subprocess.run(
        argv, cwd=cwd, env={**os.environ, "SENSORIUM_DIR": str(store)})
    return launched_at, proc


# -- the pair --------------------------------------------------------------
def pair_key(meta: dict) -> tuple:
    """What identifies "the same container" across the two invocations.

    The test file where there is one: a worker's slot, pid and thread are
    all whatever the pool handed it, and the file it ran is the only thing
    about a container that the reader asked about. Its whole `argv`
    otherwise -- a `node --test` process or a plain script carries no
    `test_file`, and its command line is what it is.

    A falsy `test_file` falls through to the argv key deliberately: null or
    empty is not a file, and `("test_file", None)` would pair two containers
    on the strength of both failing to record one.

    The BOUND: a container carrying `test_files` (a reused worker) has no
    key of its own here and reads as its argv. It cannot be the ORIGINAL of
    a refocus -- refusal 7 stops that -- so this is only reachable as a
    candidate, where an argv key can pair a reused worker with the container
    the reader asked about. `test_files_run` does not run over candidates:
    it needs a second store read of the frames per trace, and the comparator
    reads that pair as DIVERGED (named) rather than as a false MATCH.
    """
    if meta.get("test_file"):
        return ("test_file", meta["test_file"])
    return ("argv", *[str(a) for a in (meta.get("argv") or [])])


def _key_text(key: tuple) -> str:
    """The key as a refusal names it, in the reader's own vocabulary."""
    if key[0] == "test_file":
        return key[1]
    return "argv " + " ".join(key[1:])


def find_pair(traces_dir, run_id: str, launched_at: float,
              key: tuple) -> tuple[list[str], list[str]]:
    """(the candidates, the siblings) this re-run produced, in name order.

    A trace is LINKED on two counts, and BOTH are necessary: it names
    `run_id` in `refocus_of` (the driver stamped it, so the link is durable
    and the same one `info` prints), and its own recording started at or
    after `launched_at` (so an EARLIER refocus of the same original is not
    mistaken for this one -- see the module docstring).

    A linked trace is then a CANDIDATE when its `pair_key` equals the
    original's, and a SIBLING otherwise. The split is what makes a suite
    refocusable at all: every container of the invocation is linked, and
    counted as candidates they would be "more than one" on every re-run of
    every suite with two test files in it.
    """
    linked = []
    for path in sorted(Path(traces_dir).glob("*.db")):
        try:
            conn = db.open_trace(path)
        except (OSError, sqlite3.DatabaseError, db.TraceFormatError):
            # A file this process cannot open is not a trace the driver
            # just wrote. Skipped rather than reported: the answer this
            # function owes is "which traces are linked", and a store may
            # hold a half-written or newer-format file for its own reasons.
            continue
        try:
            of = db.get_meta(conn, "refocus_of")
            started = db.get_meta(conn, "start_ts")
            meta = db.all_meta(conn)
        finally:
            conn.close()
        if of != run_id:
            continue
        if not isinstance(started, (int, float)) or started < launched_at:
            continue
        linked.append((path.stem, pair_key(meta)))

    candidates = [name for name, k in linked if k == key]
    siblings = [name for name, k in linked if k != key]
    return candidates, siblings


def siblings_note(n: int) -> str:
    """The clause that says what the re-run produced beside the pair.

    One sentence, used wherever the outcome of the lookup is announced --
    on the pair line and again by `info` after the terminal has scrolled --
    because a reader told about the same fact in two wordings has to work
    out whether they are the same fact. It names the count AND what is being
    claimed about them, which is nothing: they were re-run, and no
    comparison was made of any of them.
    """
    return f"siblings in the re-run: {n} (not compared; UNVERIFIED)"


def stamp_siblings(path: Path, n: int) -> None:
    """Write the sibling COUNT into the pair's trace.

    Stamped even when it is zero, for `stamp_unverifiable`'s reason one key
    over: `0` says the lookup ran over this invocation and found the pair
    alone, while an ABSENT key says the trace was written before the count
    existed. A key that only appears sometimes cannot tell a later reader
    which of the two it is looking at.

    The ids are NOT stamped: the new invocation id already names them --
    `runs` groups by it -- and a list of 371 run ids is not a thing a reader
    follows.
    """
    conn = db.open_trace(path)
    try:
        db.set_meta(conn, SIBLINGS_KEY, n)
        conn.commit()
    finally:
        conn.close()


# -- the verdict -----------------------------------------------------------
def _harness_exit(meta: dict) -> str:
    """One invocation's ending, as the driver WAITED for it.

    `harness_exit`, never the container's `exit_status`: a vitest worker is
    killed by its pool and its own exit is unwitnessed (`exit_status_basis:
    unwitnessed`, null on every trace this recorder writes), so printing
    that would put a `?` on both sides of a line whose whole job is to say
    how the two runs ended. The basis travels with the number, because "0"
    learned by waiting and "0" read off a self-report are different claims.
    """
    ending = meta.get("harness_exit")
    if not isinstance(ending, dict):
        return "?"
    basis = ending.get("basis") or "?"
    if ending.get("signal"):
        return f"signal {ending['signal']} ({basis})"
    status = ending.get("status")
    return f"{'?' if status is None else status} ({basis})"


def _verify(args, orig: Trace, orig_name: str, meta: dict, new_id: str,
            source_caveat, source_fact, siblings: list[str]) -> int:
    """Compare the pair, assess it, stamp it, report it."""
    from sensorium.query.diff_cmd import compare
    from sensorium.query.refocus_cmd import _stamp, assess, report

    new_path = (paths.traces_dir() / f"{new_id}.db").resolve()
    new = Trace.open(new_path)
    env_line, env_caveat, env_fact = env_of(meta, new, is_recorder_key)
    world_verified = [f for f in (source_fact, env_fact) if f]
    res = compare(orig, new)
    a = assess(orig, new, res,
               [c for c in (source_caveat, env_caveat) if c], world_verified)
    checks = unverifiable_checks(orig, new)
    a = relicense(a, orig, new, world_verified)
    _stamp(new_path, res, a)
    stamp_unverifiable(new_path, checks)
    stamp_siblings(new_path, len(siblings))

    print("--- verdict ---")
    # The pair line, and the only place a reader is told what ELSE the
    # re-run produced: which trace the verdict is about and which traces it
    # is not about are one fact, so they are one line. The invocation is on
    # it because that is what `runs` groups the siblings under -- the reader
    # who wants to see them has the id in front of them.
    print(f"run: {new_id}   invocation: {new.meta.get('invocation')}   "
          f"{siblings_note(len(siblings))}")
    print(f"trace: {new_path}")
    print(env_line)
    print(f"exit: rerun {_harness_exit(new.meta)}   original "
          f"{_harness_exit(meta)}")
    # `report` prints the blind-spot block, this recorder's own lines
    # included (`vocab.blind_spots`); what follows it is the pair's own
    # unrun checks, which are findings about THIS pair rather than about the
    # recorder, and are stamped as well as printed.
    code = report(orig, new, res, orig_name, new_id, a)
    _print_unverifiable(checks)
    return code


def run(args, orig: Trace, orig_name: str, meta: dict) -> int:
    """The TypeScript branch of `sensorium refocus`, whole."""
    from sensorium.query.refocus_cmd import (_merged_focus, _pin_trace_store,
                                             _refuse)

    problem = refusal(meta, args, orig)
    if problem:
        return _refuse(orig_name, problem, orig)

    # Pinned and resolved BEFORE the child is launched, for
    # `_pin_trace_store`'s reason: a relative SENSORIUM_DIR would resolve
    # against the project the harness runs in, not against the directory
    # this command was invoked from, and the new traces would land where
    # the pair lookup never looks.
    _pin_trace_store()
    store = paths.trace_root().resolve()
    traces = paths.traces_dir().resolve()
    cwd = meta["harness_cwd"]
    run_id = meta.get("run_id") or orig_name
    argv = rerun_argv(meta, args.focus, run_id)

    # The original's source digests are ABSOLUTE (`ts/build.py`'s `_on_file`
    # records the resolved path), so they re-hash from any directory and
    # there is nothing to chdir for. Checked before the re-run, as the other
    # branches check it: a source that has changed is worth knowing before
    # a suite is spent on it.
    source, source_caveat, source_fact = _source_state(meta)

    # The command as a person would type it, not as this process runs it:
    # `argv[:3]` is the interpreter and `-m sensorium`, which is the next
    # line's business, and a reader who wants to run it again themselves
    # should be able to copy this one.
    print(f"refocus-of: {orig_name}   cmd: "
          + " ".join(["sensorium", *argv[3:]]))
    print(f"via: {sys.executable} -m sensorium")
    print(f"cwd: {cwd}")
    print(f"focus: {', '.join(_merged_focus(meta, args.focus))}   window: -")
    print(source)
    print("--- rerunning (the harness's own output follows; the driver's "
          "run: lines print with it) ---")
    launched_at, proc = _launch(argv, cwd, store)

    key = pair_key(meta)
    ids, siblings = find_pair(traces, run_id, launched_at, key)
    if not ids:
        # The count is of what WAS linked, so a reader can tell "the suite
        # never ran" from "the suite ran and this container was not in it"
        # -- a filter, a `--maxWorkers` change, a file that no longer
        # exists. The harness's exit is named beside it for the same reason.
        return _refused_after_rerun(
            orig, f"the re-run produced {len(siblings)} trace(s) linked to "
                  f"{run_id} and none ran {_key_text(key)} (harness exit "
                  f"{proc.returncode}); see the harness's output above")
    if len(ids) > 1:
        return _refused_after_rerun(
            orig, f"the re-run produced {len(ids)} traces linked to "
                  f"{run_id} that each ran {_key_text(key)} "
                  f"({', '.join(ids)}); two containers of one invocation "
                  "claiming one test file is a fact about the harness this "
                  "tool will not guess through")
    return _verify(args, orig, orig_name, meta, ids[0], source_caveat,
                   source_fact, siblings)
