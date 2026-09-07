"""`refocus` on a Rust trace: re-invoke `cargo sensorium`, then compare.

`refocus_cmd` owns the command; this file owns the ONE thing a Rust
recording does differently -- it cannot be re-run in this process. A Python
refocus imports the target and runs it under a deeper recorder; a Rust
refocus has to ask the driver to rebuild the crate with a `--focus` spliced
in, from the workspace root, and then FIND the trace that came back. Every
other part of the command -- the comparator, the verdict, the assessment,
the report, the stamps -- is `refocus_cmd`'s and is called here unchanged,
because two verdict vocabularies for one question is how the two languages
would come to disagree about what MATCH means (design 2026-09-07, G2).

WHAT THIS FILE MAY REFUSE, AND WHY EACH REFUSAL IS BEFORE THE RE-RUN
---------------------------------------------------------------------
A cargo rebuild has side effects and costs minutes. Every condition that
would make the answer meaningless is therefore checked BEFORE anything is
launched, and each one exits 2 (`BAD_CALL`, "fix the call") rather than 3,
for the reason `_refuse` states: nothing ran, so the reader's next move is a
different command. The five, in the order design 2026-09-07 section 2.3
fixes:

1. `--window` -- rung 4 gives Rust LINE events under `--focus` and no
   window gate at all. Accepting the flag and ignoring it would report a
   narrowing that never happened.
2. the invocation ran more than one process -- `cargo test` on a crate with
   two test binaries produces two traces, and "which one is the re-run of
   this trace" has no answer. A single-target selector is what makes it one.
3. no `workspace_root` -- a trace from cargo-sensorium 0.4.0 or earlier. It
   records no directory to re-run from, and guessing one is guessing.
4. `workspace_root` gone -- the same fact the Python branch checks about
   `cwd`, one level up.
5. no driver -- there is nothing to re-run WITH.

The sentences carry no `REFUSED:` prefix of their own: `_refuse` prints
`error: cannot refocus <run>: <sentence>`, and two announcements of one
refusal read as two refusals. Everything after the design's prefix is
verbatim, `; nothing was re-run` included.

THE PAIR IS FOUND IN THE STORE, NEVER PARSED OUT OF THE DRIVER'S OUTPUT
-----------------------------------------------------------------------
The driver prints a `run:` line per process. Reading the new run id off it
would put a load-bearing link in this process's memory only, and a changed
print would break `refocus` silently (design 2026-09-07, G3: two approaches
were rejected for exactly this). Instead the driver stamps `refocus_of` into
every trace of the invocation, and `find_pair` asks the STORE which traces
carry it. The `run:` lines are printed back to the reader and decide
nothing.

The timestamp filter in `find_pair` is not belt-and-braces. The second
refocus of one original would otherwise find the FIRST one's trace as well
as its own, and "more than one" is a refusal -- so without the filter a
second refocus of any run fails permanently. `start_ts` is the process's own
CLOCK_REALTIME start (`convert/mod.rs`: `start_realtime_ns / 1e9`), the same
wall clock `time.time()` reads, so the comparison is between like and like.
A trace that records no `start_ts` is EXCLUDED rather than assumed recent:
it cannot be shown to be this re-run's.

NO TIMEOUT
----------
Deliberate, and design 2026-09-07 section 2.3 says so: Python's `refocus`
has none, a cargo build's length is the user's to judge, and a timeout that
killed a rebuild half way would leave the store in exactly the state
("no trace linked to this run") that this file reports as REFUSED. The
child's stderr is not captured, so a build that is slow is a build the
reader can watch.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from sensorium import paths
from sensorium.exit import UNSETTLED
from sensorium.query.refocus_world import (UNVERIFIABLE, _UNCOMPARED_ENV,
                                           _env_state, _source_state,
                                           _verified_facts,
                                           unverifiable_checks)
from sensorium.query.vocab import terms
from sensorium.store import db
from sensorium.store.reader import Trace

#: The meta key `_stamp` may not write, because the checks it records are
#: NOT reasons a licence was withheld -- they are checks that could not run.
#: Stamped beside `refocus_licence_reasons` rather than inside it, so a
#: reader of the trace and a reader of the terminal are told the same thing.
UNVERIFIABLE_KEY = "refocus_licence_unverifiable"


def driver() -> str | None:
    """The `cargo-sensorium` this re-run will use, or None.

    `SENSORIUM_CARGO_SENSORIUM` first, then PATH -- character for character
    the rule `corpus/run_corpus.py::cargo_driver` applies, so the driver a
    corpus case records with and the driver a `refocus` question re-runs
    with are the same binary. COPIED rather than imported: `corpus/` is a
    development tree beside the package and is not in the wheel
    (`pyproject.toml` packages `src/sensorium` only), so importing it would
    make this command work from a checkout and fail from an install.
    """
    return os.environ.get("SENSORIUM_CARGO_SENSORIUM") or shutil.which(
        "cargo-sensorium")


# -- may this recording be re-run at all? ----------------------------------
def refusal(meta: dict, args, driver: str | None) -> str | None:
    """Why re-running this Rust recording would be illegitimate, or None.

    Order is the design's and is load-bearing in one direction: the cheap,
    always-answerable questions come first, so a call that is wrong in two
    ways is told about the one the reader can act on without a toolchain.
    """
    if getattr(args, "window", None) is not None:
        return ("--window is not available for a Rust trace (rung 4 leaves "
                "it out); nothing was re-run")
    run = meta.get("run_id") or "this run"
    n = meta.get("invocation_processes")
    if n != 1:
        # `n` absent is a trace from before the key existed. It is named as
        # unrecorded rather than rendered as `None` or defaulted to a count:
        # the refusal must not report a number nothing measured.
        count = n if n is not None else "an unrecorded number of"
        return (f"run {run} is one of {count} processes of its invocation "
                "(test binaries and doctests); refocus needs an invocation "
                "with a single-target selector (--lib, --test X, --bin X) "
                "so one trace is the answer; nothing was re-run")
    root = meta.get("workspace_root")
    if not root:
        return (f"run {run} records no workspace_root (recorded by "
                "cargo-sensorium 0.4.0 or earlier); nothing was re-run")
    if not os.path.isdir(root):
        return f"workspace {root} no longer exists; nothing was re-run"
    if not driver:
        return ("no cargo-sensorium to re-run with -- set "
                "SENSORIUM_CARGO_SENSORIUM or put cargo-sensorium on PATH; "
                "nothing was re-run")
    return None


# -- the re-run ------------------------------------------------------------
def rerun_argv(meta: dict, requested_focus, driver: str) -> list[str]:
    """The driver invocation that re-records this run under more focus.

    `--refocus-of` is what makes the new trace findable afterwards, so it is
    first and unconditional. `--tier` is the ORIGINAL's, read from its
    recorded environment: omitted when the key is absent, so the driver's
    own default applies rather than this file asserting one. The focus list
    is `refocus_cmd._merged_focus`'s -- the original's values then the
    caller's, never fewer than the original's -- and reusing that function
    is the point: "a refocus only ever captures more" must mean the same
    thing in both languages. It also drops a value the caller re-typed,
    which the driver's own set rule would have collapsed anyway.

    `cargo_args` goes last and verbatim: it is cargo's argv, starting with
    the subcommand, and the driver splits its own flags off the front (only
    before the first bare `--`, so a test binary's arguments are safe).
    """
    from sensorium.query.refocus_cmd import _merged_focus

    argv = [driver, "--refocus-of", meta.get("run_id") or ""]
    tier = (meta.get("env") or {}).get("SENSORIUM_TIER")
    if tier:
        argv += ["--tier", str(tier)]
    for value in _merged_focus(meta, requested_focus):
        argv += ["--focus", value]
    return argv + [str(a) for a in (meta.get("cargo_args") or [])]


def find_pair(traces_dir, run_id: str, launched_at: float) -> list[str]:
    """The run ids of every trace this re-run produced, in name order.

    A trace qualifies on two counts, and BOTH are necessary: it names
    `run_id` in `refocus_of` (the driver stamped it, so the link is durable
    and the same one `info` prints), and its own recording started at or
    after `launched_at` (so an EARLIER refocus of the same original is not
    mistaken for this one -- see the module docstring).
    """
    out = []
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
            linked = db.get_meta(conn, "refocus_of")
            started = db.get_meta(conn, "start_ts")
        finally:
            conn.close()
        if linked != run_id:
            continue
        if not isinstance(started, (int, float)) or started < launched_at:
            continue
        out.append(path.stem)
    return out


def _run_lines(stdout: str) -> list[str]:
    """The driver's own `run:` lines, for the report and for nothing else."""
    return [ln for ln in stdout.splitlines() if ln.startswith("run: ")]


def _launch(argv: list[str], root: str, store: Path) -> tuple[float, object]:
    """Run the driver from the workspace root, under the original's store.

    `SENSORIUM_DIR` is the resolved ABSOLUTE store of the original, for the
    reason `refocus_cmd._pin_trace_store` states one level up: a relative
    value would follow the child into the workspace and write the new trace
    where `find_pair` -- and `sensorium runs` -- will never look. Nothing
    else is set or stripped, so the environment the re-run executed under is
    the caller's, and the two traces' own recorded environments are what the
    licence check compares afterwards.

    stderr is NOT captured: a focused rebuild takes minutes and its progress
    belongs to the person waiting for it.
    """
    launched_at = time.time()
    proc = subprocess.run(
        argv, cwd=root, env={**os.environ, "SENSORIUM_DIR": str(store)},
        stdout=subprocess.PIPE, stderr=None, text=True)
    return launched_at, proc


# -- the assessment, with two checks that could not run --------------------
def _relicense(a: dict, orig: Trace, new: Trace, world_verified) -> dict:
    """Take the UNVERIFIABLE markers out of the WITHHOLDING decision.

    `_licence_caveats` reports them, because a reader of the licence must be
    told which checks did not run. But a caveat withholds the licence, and
    withholding it here would say the recorder's declared absence of output
    capture is a finding AGAINST this pair -- it is not a finding at all.
    The markers are printed and stamped separately (`_print_unverifiable`,
    `UNVERIFIABLE_KEY`), so nothing is hidden by the removal; what is
    removed is only their vote.

    The verified list is rebuilt exactly as `assess` builds it -- the
    world's fact spliced after the first -- because two splices of one list
    is two orders for the same evidence.
    """
    caveats = [c for c in a["caveats"] if c not in UNVERIFIABLE]
    if caveats == a["caveats"]:
        return a
    licence, verified = a["licence"], a["verified"]
    if a["verdict"] == "MATCH" and not caveats:
        licence = "granted"
        facts = _verified_facts(orig, new, a["thread_scope"])
        verified = facts[:1] + list(world_verified) + facts[1:]
    return {**a, "caveats": caveats, "licence": licence,
            "verified": verified}


def _print_unverifiable(checks: list[str]) -> None:
    if not checks:
        return
    print("checks that could not run on this pair -- the recorder declares "
          "it does not produce them, so nothing here is evidence either "
          "way:")
    for check in checks:
        print(f"  - {check}")


def _stamp_unverifiable(path: Path, checks: list[str]) -> None:
    """Write the unrun checks into the new trace, beside the licence.

    Stamped even when the list is empty -- and even when the licence is
    withheld for other reasons -- so `info` on any Rust re-run says which
    checks the verdict does NOT rest on, rather than leaving a reader to
    infer it from the absence of a key.
    """
    conn = db.open_trace(path)
    try:
        db.set_meta(conn, UNVERIFIABLE_KEY, checks)
        conn.commit()
    finally:
        conn.close()


# -- the verdict paths -----------------------------------------------------
def _refused_after_rerun(orig: Trace, reason: str) -> int:
    """A re-run that happened and produced no comparable pair.

    Exit 3, not 2: the driver DID run, so no edit to the command settles
    this -- the second of `refocus`'s two gates, exactly as `report` uses
    it. `report` itself cannot be reached here, because it prints a
    comparison and there is no second trace to compare.
    """
    from sensorium.query.refocus_cmd import _print_blind_spots

    print(f"refocus verdict: REFUSED -- {reason}")
    _print_blind_spots()
    return UNSETTLED


def _is_recorder_key(name: str) -> bool:
    """Whether this variable is the RECORDER's own bookkeeping.

    The same judgement `_UNCOMPARED_ENV` makes about `SENSORIUM_DIR`, and
    for the same measured reason -- reporting the tool's own footprint as a
    change the world made is noise, not honesty. Here it is not optional:
    a focused re-run changes `SENSORIUM_FOCUS` by definition, mints a new
    `SENSORIUM_INVOCATION` and `SENSORIUM_SPOOL`, and -- because `--focus`
    keys a fresh shim -- hands cargo different `RUSTC_WORKSPACE_WRAPPER`
    and `CARGO_TARGET_<TRIPLE>_RUNNER` values. Compared, those six fire on
    EVERY Rust refocus, and a check that always fires says nothing.

    Not applied to the Python branch, and not added to `_UNCOMPARED_ENV`:
    these are variables of a recorder Python's traces never carry. The
    names are printed beside the count rather than hidden behind it, which
    is the rule the shell list follows too.
    """
    return (name.startswith("SENSORIUM_")
            or name == "RUSTC_WORKSPACE_WRAPPER"
            or (name.startswith("CARGO_TARGET_")
                and name.endswith("_RUNNER")))


def _env_of(meta: dict, new: Trace):
    """(status line, caveat, fact) for the environment, from BOTH traces.

    Design section 3.2's `reads` column: the Rust environment check is
    `env` recorded in both traces, not the caller's process environment.
    Comparing the recorded test-binary environment against this CLI's would
    diff cargo's own variables against their absence and report a changed
    world on every single run -- a check that always fires says nothing.
    """
    was, now = meta.get("env"), new.meta.get("env")
    if not isinstance(now, dict):
        return ("env: unverifiable -- the re-run's trace records no "
                "environment to compare against",
                "the environment could not be checked at all -- the "
                "re-run's trace holds none to compare -- so nothing rules "
                "out the two runs getting different input through it", None)
    # `_UNCOMPARED_ENV`'s names are already printed by `_env_state`; listing
    # them twice would read as two separate holes in one check.
    mine = sorted({k for k in ((was if isinstance(was, dict) else {}) | now)
                   if _is_recorder_key(k) and k not in _UNCOMPARED_ENV})
    line, caveat, fact = _env_state(
        {**meta, "env": {k: v for k, v in was.items()
                         if not _is_recorder_key(k)}}
        if isinstance(was, dict) else meta,
        {k: v for k, v in now.items() if not _is_recorder_key(k)})
    if mine:
        named = f"; the recorder's own, also not compared: {', '.join(mine)}"
        line += f"  {named[2:]}"
        fact = f"{fact}{named}" if fact else fact
    return line, caveat, fact


def _verify(args, orig: Trace, orig_name: str, meta: dict, new_id: str,
            source_caveat, source_fact) -> int:
    """Compare the pair, assess it, stamp it, report it."""
    from sensorium.query.refocus_cmd import (_stamp, assess, report)
    from sensorium.query.diff_cmd import compare

    new_path = (paths.traces_dir() / f"{new_id}.db").resolve()
    new = Trace.open(new_path)
    env_line, env_caveat, env_fact = _env_of(meta, new)
    world_verified = [f for f in (source_fact, env_fact) if f]
    res = compare(orig, new)
    a = assess(orig, new, res,
               [c for c in (source_caveat, env_caveat) if c], world_verified)
    checks = unverifiable_checks(orig, new)
    a = _relicense(a, orig, new, world_verified)
    _stamp(new_path, res, a)
    _stamp_unverifiable(new_path, checks)

    print("--- verdict ---")
    print(f"run: {new_id}")
    print(f"trace: {new_path}")
    print(env_line)
    print(f"exit: rerun {new.meta.get('exit_status', '?')}   original "
          f"{meta.get('exit_status', '?')}")
    code = report(orig, new, res, orig_name, new_id, a)
    _print_unverifiable(checks)
    spots = terms(new).refocus_blind_spots
    if spots:
        print("and, for this recorder specifically, no verdict here says "
              "anything about:")
        for line in spots:
            print(f"  - {line}")
    return code


def run(args, orig: Trace, orig_name: str, meta: dict) -> int:
    """The Rust branch of `sensorium refocus`, whole."""
    from sensorium.query.refocus_cmd import _merged_focus, _refuse

    drv = driver()
    problem = refusal(meta, args, drv)
    if problem:
        return _refuse(orig_name, problem, orig)

    # Resolved BEFORE the chdir below and before the child is launched, for
    # `_pin_trace_store`'s reason: a relative SENSORIUM_DIR would resolve
    # against the workspace, not against the directory this command was
    # invoked from.
    store = paths.trace_root().resolve()
    traces = paths.traces_dir().resolve()
    root = meta["workspace_root"]
    run_id = meta.get("run_id") or orig_name
    argv = rerun_argv(meta, args.focus, drv)

    # The original's source digests are workspace-RELATIVE (the wrapper
    # records `a/src/lib.rs`, never an absolute path), so they can only be
    # re-hashed from the workspace root. Checked before the re-run, as the
    # Python branch checks it: a source that has changed is worth knowing
    # before spending a rebuild on it.
    prev = os.getcwd()
    os.chdir(root)
    try:
        source, source_caveat, source_fact = _source_state(meta)
    finally:
        os.chdir(prev)

    print(f"refocus-of: {orig_name}   cmd: {' '.join(argv)}")
    print(f"cwd: {root}")
    print(f"focus: {', '.join(_merged_focus(meta, args.focus))}   window: -")
    print(source)
    print("--- rerunning (the driver's build output is above and below; the "
          "lines below are its own) ---")
    launched_at, proc = _launch(argv, root, store)
    # Captured, then printed back: the design captures the child's stdout so
    # the `run:` lines can be reported, and printing it afterwards means the
    # program's own output is delayed, never withheld.
    sys.stdout.write(proc.stdout or "")
    for line in _run_lines(proc.stdout or ""):
        print(f"driver reported: {line}")

    ids = find_pair(traces, run_id, launched_at)
    if not ids:
        return _refused_after_rerun(
            orig, f"the re-run produced no trace linked to {run_id} (driver "
                  f"exit {proc.returncode}); see the driver's output above")
    if len(ids) > 1:
        return _refused_after_rerun(
            orig, f"the re-run produced {len(ids)} traces linked to "
                  f"{run_id} ({', '.join(ids)}); refocus needs an invocation "
                  "with a single-target selector (--lib, --test X, --bin X) "
                  "so one trace is the answer")
    return _verify(args, orig, orig_name, meta, ids[0], source_caveat,
                   source_fact)
