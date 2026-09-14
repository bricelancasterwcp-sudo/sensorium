"""`sensorium ts run`: recognise, wire, spawn, wait, convert.

The order is the design, and every step of it is there because the step
before it can fail in a way that would otherwise leave something behind:

    --refocus-of          refused before the Node check: it is about the
                          call and nothing else, so a bad link costs no
                          version probe and no spawn
    node --version        refused below 24 (D2) before anything is minted
    the package           refused uninstalled before anything is minted
    recognise             refused before a spool directory exists
    the root's typescript refused once the plan names the root, and still
                          before anything is minted
    --focus               resolved against the root by the recorder's own
                          resolver, and refused there: the last thing that
                          can be settled before a recording exists
    mint, invocation.json the record of what is about to be spawned
    the wrapper           two files, in a `finally` from here on
    spawn, wait           the harness's stdio is the user's; the driver
                          only holds the clock
    harness.json          written whether the harness passed or failed --
                          the run an agent most wants to read is the red one
    remove the wrapper    on every path, exception included
    ingest                one trace per container, into the same store

The driver never applies the query CLI's 0/1/2/3 table to itself: it exits
with the harness's own status, and `128 + n` when a signal ended it. A
recorder whose exit status meant something different from the command it
wrapped could not be put in front of an existing command line at all.
"""
import importlib.metadata
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from sensorium import exit as ex
from sensorium import paths, redact
from sensorium.ts import focus as focus_mod
from sensorium.ts import harness as harness_mod
from sensorium.ts import ingest, invocation, pkg as pkg_mod, wrapper

#: Where a run's spools live, under the trace store. One directory per
#: invocation, named by it, holding the record, the spools and the marker.
SPOOL_DIR = "spool"


class LinkError(Exception):
    """`--refocus-of` named something this store cannot link to. A refusal
    like every other bad call, and the FIRST of them: the value is about
    the call and nothing else, so it is settled before the Node version,
    the package and `recognise` -- none of which could make a bad link
    good, and all of which cost something to ask."""


class SpawnError(Exception):
    """The harness binary could not be started at all. `recognise` reads a
    command and does not check that the program exists -- which `vitest`
    runs is the user's choice, and resolving it there would resolve a
    different one -- so this is where a name that is not a program is
    found, and it is a refusal like every other bad call."""


def run(args) -> int:
    """The `ts run` verb. See the module docstring for the order."""
    command = list(getattr(args, "command", []))
    if command and command[0] == "--":
        command = command[1:]
    try:
        link = _refocus_link(getattr(args, "refocus_of", None))
    except LinkError as e:
        return _refuse(str(e))
    try:
        node = pkg_mod.check_node()
        package = pkg_mod.locate()
        pkg_mod.check(package)
    except pkg_mod.PackageError as e:
        return _refuse(str(e))
    cwd = Path.cwd()
    plan = harness_mod.recognise(command, cwd)
    if isinstance(plan, harness_mod.Refusal):
        return _refuse(plan.message)
    # After `recognise`, because only the plan knows the root -- and still
    # before anything is minted.
    try:
        pkg_mod.check_root(plan.root)
    except pkg_mod.PackageError as e:
        return _refuse(str(e))
    # And after THAT, because resolving a focus parses the root's files with
    # the root's own TypeScript. Still nothing minted: a focus that selects
    # nothing is a call to fix, and a half-recorded run of it would be a
    # recording of a question nobody asked (spec section 2.2).
    focus = list(args.focus or [])
    resolution = None
    if any(spec.strip() == "" for spec in focus):
        # An empty spec has an empty qualname, and an empty qualname is a
        # prefix of every name there is: dropped it does nothing, honoured
        # it records the whole program. Neither is what was typed.
        return _refuse("--focus was given nothing to name: a spec is a "
                       "<qualname> or a <file>:<qualname>")
    if focus:
        try:
            # `node` here is the VERSION `check_node` read, not a program:
            # the resolver runs the same `node` on PATH the harness will.
            resolution = focus_mod.resolve(plan.root, package, focus)
        except pkg_mod.PackageError as e:
            return _refuse(str(e))
        bad = focus_mod.refusals(resolution, plan.root)
        if bad:
            return _refuse(*bad)
    try:
        return _record(plan, package, node, cwd, args, focus, resolution,
                       link)
    except (wrapper.WrapperError, SpawnError) as e:
        return _refuse(str(e))


def _refuse(*messages: str) -> int:
    """One line on stderr per refusal, exit 2, nothing left behind. Every
    refusal this driver makes before the harness is spawned goes through
    here, so they are one shape and not six -- and a call with two mistakes
    in it is told both, rather than sent round the loop twice."""
    for message in messages:
        print(f"error: {message}", file=sys.stderr)
    return ex.BAD_CALL


def _refocus_link(value: str | None) -> str | None:
    """The run id `--refocus-of` names, or None where it was not given.

    One trailing `.db` is stripped rather than refused: the store holds
    `<id>.db` files, so that is what tab-completion and a copied `ls` line
    hand a person, and the id inside it is unambiguous.

    Both refusals end `nothing was run.` because that is the fact the
    caller needs: this check happens before anything is minted or spawned,
    so a re-run refused here has left no half-recording behind to clean up.
    The second names the STORE, not the file it looked for -- a person
    given the directory can list it; a person given a path that does not
    exist has been told what they already knew.
    """
    if value is None:
        return None
    run_id = value[:-3] if value.endswith(".db") else value
    if not paths.is_valid_run_id(run_id):
        # `../x`, `a/b`, `.`: an id flows straight into `traces_dir() /
        # f"{id}.db"`, so one that is not a single path component would
        # read outside the store. The value is echoed AS GIVEN, suffix and
        # all, because that is what the caller typed and has to correct.
        raise LinkError(f"--refocus-of {value} is not a run id; "
                        "nothing was run.")
    if not (paths.traces_dir() / f"{run_id}.db").is_file():
        raise LinkError(f"--refocus-of {run_id} names no trace in "
                        f"{paths.trace_root()}; nothing was run.")
    return run_id


def _record(plan, package: Path, node: str, cwd: Path, args,
            focus: Sequence[str], resolution,
            link: str | None = None) -> int:
    """Everything from the mint to the conversion."""
    inv_id = paths.new_run_id()
    # One level at a time, 0700 each, for `paths.traces_dir()`'s reason:
    # `Path.mkdir(parents=True, mode=...)` applies the mode to the directory
    # it NAMES and gives every parent it creates on the way the default, so
    # a single `spool.mkdir(parents=True, mode=0o700)` would leave
    # `<store>/spool` -- and the store root above it, where `redaction.key`
    # lives -- at 0775. Measured at 0775 by E16 part A (H2). An existing
    # directory is never chmod'ed: the user's own store is theirs.
    root = paths.trace_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    (root / SPOOL_DIR).mkdir(exist_ok=True, mode=0o700)
    spool = root / SPOOL_DIR / inv_id
    spool.mkdir(exist_ok=True, mode=0o700)
    config = (wrapper.home(plan.root) /
              f"{inv_id}{wrapper.CONFIG_SUFFIX}"
              if plan.kind == "vitest" else None)
    _write_record(spool, plan, inv_id, node, package, config, focus,
                  [] if resolution is None else resolution.matched_specs,
                  None if resolution is None else resolution.wall,
                  refocus_of=link)

    files: tuple = ()
    try:
        if plan.kind == "vitest":
            files = wrapper.write(plan.root, inv_id, package,
                                  plan.user_config)
            argv = plan.vitest_command(files[0])
        else:
            argv = plan.node_command(package / "src" / "register.mjs")
        try:
            ending = _spawn(argv,
                            _env(spool, inv_id, plan, package, args.tier,
                                 focus),
                            cwd)
        except OSError as e:
            # Nothing ran, so there is nothing to convert and nothing to
            # keep: the record of an invocation that never happened would
            # be listed by `runs` forever.
            _discard(spool)
            raise SpawnError(
                f"{argv[0]} could not be started: {e.strerror}") from None
        invocation.write_record(
            spool / invocation.HARNESS_FILE,
            json.dumps(ending.to_json(), indent=2) + "\n")
    finally:
        wrapper.remove(files)
    return _convert(spool, inv_id, ending, getattr(args, "jobs", None),
                    args.tier)


def _discard(spool: Path) -> None:
    """Take back a spool directory nothing was recorded into, and the
    `spool/` above it when this invocation is what made it. Stops at a
    directory another invocation is still using, exactly as
    `wrapper.remove` does."""
    for path in sorted(spool.iterdir()):
        path.unlink(missing_ok=True)
    for directory in (spool, spool.parent):
        try:
            directory.rmdir()
        except OSError:
            return


# -- the record --------------------------------------------------------------


def _write_record(spool: Path, plan, inv_id: str, node: str, package: Path,
                  config: Path | None, focus: Sequence[str] = (),
                  focus_matched: Sequence[str] = (),
                  resolver_wall_s: float | None = None,
                  refocus_of: str | None = None) -> None:
    """`invocation.json`, written BEFORE the harness is spawned.

    It is the only thing that can say what a spool directory came out of: a
    container knows its own pid and its own environment, but not which
    command produced it and not where the project root is.
    """
    record = invocation.Invocation(
        invocation=inv_id, harness=plan.kind,
        harness_args=list(plan.harness_args), root=str(plan.root),
        # `plan.argv` is the tokens as typed, kept whole by `recognise`
        # before `_consume` takes `--root`/`--config` out and before either
        # `vitest_command`/`node_command` re-issues anything. That is the
        # one list a reader can be shown and recognise as their own (R26).
        command=list(plan.argv),
        cwd=str(Path.cwd()), argv=list(plan.argv), env_hash=_env_hash(),
        start_ts=time.time(), wrapper="" if config is None else str(config),
        vitest=_vitest_version(plan), node=node,
        driver_version=_driver_version(),
        recorder=f"sensorium-ts {pkg_mod.version(package)}",
        # Both, and always: the specs as typed and the functions they
        # selected. A reader of this directory should not have to know which
        # driver version wrote it to know that nothing was focused.
        focus=list(focus), focus_matched=list(focus_matched),
        # What resolving them cost, so an instrument can time the resolver
        # without timing the driver around it. `None` where no focus was
        # given: the resolver did not run, and 0.0 would say it did.
        resolver_wall_s=resolver_wall_s,
        # The run this one re-runs, validated before anything was minted.
        # `None` is a command a person typed, and the converter then writes
        # no `refocus_of` key at all: an absent key is what every reader of
        # a trace branches on.
        refocus_of=refocus_of)
    invocation.write_record(spool / invocation.INVOCATION_FILE,
                            json.dumps(record.to_json(), indent=2) + "\n")


def _env_hash() -> str:
    """A digest of the DRIVER's environment, by the recipe both this
    recorder's halves use (`invocation.env_hash`).

    The driver's and not the harness's: the harness's differs from it by the
    variables written two functions below, which are the recorder's own and
    would make every invocation's hash unique by construction -- the
    redaction key most of all, which is 64 characters no two stores share.
    """
    return invocation.env_hash(os.environ)


def _driver_version() -> str:
    try:
        return importlib.metadata.version("sensorium")
    except importlib.metadata.PackageNotFoundError:
        return "sensorium (uninstalled source tree)"


def _vitest_version(plan) -> str | None:
    """Which vitest the consumer's tree holds, or None.

    None for `node --test`, which has no vitest, and None for a vitest run
    whose package cannot be read -- an absent version is written as no key
    at all by the converter, never as an empty string.
    """
    if plan.kind != "vitest":
        return None
    manifest = plan.root / "node_modules" / "vitest" / "package.json"
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'"version"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else None


def _env(spool: Path, inv_id: str, plan, package: Path, tier: str,
         focus: Sequence[str]) -> dict:
    """The harness's environment: the driver's own, plus what the recorder
    inside the harness cannot work out for itself.

    `SENSORIUM_FOCUS` is set only when there IS a focus, and holds the specs
    as typed, joined by the separator. One variable answers for all three
    readers inside the harness -- the Vite plugin, the loader hook and the
    runtime -- and an EMPTY one is not the same as an absent one to the last
    of them: the runtime declares `line` and `locals` from its presence, and
    an empty value would declare capabilities nothing was going to write.

    It is the one inherited variable this driver overrides rather than
    passes on. A `SENSORIUM_FOCUS` left in a shell would otherwise focus a
    run whose own record says `focus: []` -- the recording would carry
    statement rows nobody asked for, and the record beside it would deny it.

    `SENSORIUM_REDACT_KEY` is the eighth, and the one the harness could not
    work out even in principle: the runtime only ever PARSES a key, because
    creating one means a directory, a temporary, a link and a race and the
    runtime is linked into somebody else's test suite (design section 3). So
    the STORE's key -- the same `<trace root>/redaction.key` the Python
    recorder and `cargo-sensorium` use, minted here on first use -- is handed
    down as hex. Set only when there IS a key: absent and malformed read
    identically to the runtime, and an unkeyed store POPS whatever the
    launching shell was carrying, because a key from some other store would
    have the recorder write digests nothing here can verify.

    The three knob variables are the USER's and are passed on untouched: what
    a recording was made under is the user's statement, and the BOOT records
    it.
    """
    env = dict(os.environ,
               SENSORIUM_SPOOL=str(spool),
               SENSORIUM_TIER=tier,
               SENSORIUM_TS_ROOT=str(plan.root),
               SENSORIUM_TS_PKG=str(package),
               SENSORIUM_INVOCATION=inv_id,
               SENSORIUM_MANIFEST_DIR=str(spool / ingest.MANIFEST_DIR))
    if focus:
        env["SENSORIUM_FOCUS"] = focus_mod.SEP.join(focus)
    else:
        env.pop("SENSORIUM_FOCUS", None)
    key = redact.Key.load_or_create(paths.trace_root())
    if key.material is None:
        env.pop(redact.KEY_VAR, None)
    else:
        env[redact.KEY_VAR] = key.material.hex()
    return env


# -- the run -----------------------------------------------------------------


def _spawn(argv: list[str], env: dict, cwd: Path) -> invocation.HarnessExit:
    """Run the harness with the caller's own stdio and wait for it.

    Inherited stdio, not captured: the harness's output is what the user
    came for, it is often interactive, and a recorder that buffered a
    ten-minute test run would look like a hang.
    """
    start = time.time()
    completed = subprocess.run(argv, env=env, cwd=cwd)
    end = time.time()
    if completed.returncode < 0:
        name = signal.Signals(-completed.returncode).name
        return invocation.HarnessExit(None, name, start, end)
    return invocation.HarnessExit(completed.returncode, None, start, end)


def _status(ending: invocation.HarnessExit) -> int:
    """The driver's own exit status: the harness's, `128 + n` on a signal --
    the number a shell reports for exactly that death."""
    if ending.signal is not None:
        return 128 + int(signal.Signals[ending.signal])
    return ending.status or 0


def _ending(ending: invocation.HarnessExit) -> str:
    """How the run line says the harness ended. `basis` is always `waited`
    and is printed: it is the one exit fact in a TypeScript recording that
    somebody actually witnessed."""
    if ending.signal is not None:
        return f"signal {ending.signal} (waited)"
    return f"{ending.status} (waited)"


def _convert(spool: Path, inv_id: str, ending, jobs: int | None,
             tier: str) -> int:
    """One trace per container, then the run's own lines.

    A spool the converter refuses prints its refusal and does NOT change the
    exit status: the status belongs to the harness. An ingest that could not
    start at all is the exception -- there is no recording to report, and
    exit 2 says the call or the directory has to be fixed. Where the WRAPPER
    is what refused, its own sentence is printed instead of the converter's
    (R41): only it knows why the run recorded nothing.

    At tier `off` there is nothing to convert BY DESIGN -- the transform
    still runs, the runtime emits nothing, and the invocation's whole value
    is the harness's own wall time. So the empty directory is reported as
    the zero it is, and never as the failure it would be at tier `call`,
    where an empty directory means the recorder was wired in and recorded
    nothing.
    """
    from sensorium.ts import cli as ts_cli
    if tier == "off":
        ts_cli._report([], inv_id, harness=_ending(ending))
        return _status(ending)
    try:
        summaries = ingest.ingest_dir(spool, paths.trace_root(), jobs=jobs)
    except (ingest.IngestError, invocation.InvocationError) as e:
        # The wrapper's own refusal FIRST (R41). "nothing was recorded, or
        # the recorder wrote somewhere else" is what this looks like from
        # here, and it names neither the cause nor the fix; the config that
        # refused knows both, and left the sentence behind.
        return _refuse(wrapper.refusal(spool) or str(e))
    ts_cli._report(summaries, inv_id, harness=_ending(ending))
    return _status(ending)
