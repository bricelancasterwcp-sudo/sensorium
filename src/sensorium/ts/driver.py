"""`sensorium ts run`: recognise, wire, spawn, wait, convert.

The order is the design, and every step of it is there because the step
before it can fail in a way that would otherwise leave something behind:

    node --version        refused below 24 (D2) before anything is minted
    the package           refused uninstalled before anything is minted
    recognise             refused before a spool directory exists
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
import hashlib
import importlib.metadata
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

from sensorium import exit as ex
from sensorium import paths
from sensorium.ts import harness as harness_mod
from sensorium.ts import ingest, invocation, pkg as pkg_mod, wrapper

#: Where a run's spools live, under the trace store. One directory per
#: invocation, named by it, holding the record, the spools and the marker.
SPOOL_DIR = "spool"


def run(args) -> int:
    """The `ts run` verb. See the module docstring for the order."""
    command = list(getattr(args, "command", []))
    if command and command[0] == "--":
        command = command[1:]
    try:
        node = pkg_mod.check_node()
        package = pkg_mod.locate()
        pkg_mod.check(package)
    except pkg_mod.PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return ex.BAD_CALL
    cwd = Path.cwd()
    plan = harness_mod.recognise(command, cwd)
    if isinstance(plan, harness_mod.Refusal):
        print(f"error: {plan.message}", file=sys.stderr)
        return ex.BAD_CALL
    try:
        return _record(plan, package, node, cwd, args)
    except wrapper.WrapperError as e:
        print(f"error: {e}", file=sys.stderr)
        return ex.BAD_CALL


def _record(plan, package: Path, node: str, cwd: Path, args) -> int:
    """Everything from the mint to the conversion."""
    inv_id = paths.new_run_id()
    spool = paths.trace_root() / SPOOL_DIR / inv_id
    spool.mkdir(parents=True, exist_ok=True)
    config = (wrapper.home(plan.root) /
              f"{inv_id}{wrapper.CONFIG_SUFFIX}"
              if plan.kind == "vitest" else None)
    _write_record(spool, plan, inv_id, node, package, config)

    files: tuple = ()
    try:
        if plan.kind == "vitest":
            files = wrapper.write(plan.root, inv_id, package,
                                  plan.user_config)
            argv = plan.vitest_command(files[0])
        else:
            argv = plan.node_command(package / "src" / "register.mjs")
        ending = _spawn(argv, _env(spool, inv_id, plan, package, args.tier),
                        cwd)
        (spool / invocation.HARNESS_FILE).write_text(
            json.dumps(ending.to_json(), indent=2) + "\n", encoding="utf-8")
    finally:
        wrapper.remove(files)
    return _convert(spool, inv_id, ending, getattr(args, "jobs", None),
                    args.tier)


# -- the record --------------------------------------------------------------


def _write_record(spool: Path, plan, inv_id: str, node: str, package: Path,
                  config: Path | None) -> None:
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
        recorder=f"sensorium-ts {pkg_mod.version(package)}")
    (spool / invocation.INVOCATION_FILE).write_text(
        json.dumps(record.to_json(), indent=2) + "\n", encoding="utf-8")


def _env_hash() -> str:
    """A digest of the DRIVER's environment, sorted, one `k=v` per line.

    The driver's and not the harness's: the harness's differs from it by the
    six variables written two functions below, which are the recorder's own
    and would make every invocation's hash unique by construction.
    """
    body = "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()))
    return hashlib.sha256(body.encode("utf-8", "surrogateescape")).hexdigest()[:16]


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


def _env(spool: Path, inv_id: str, plan, package: Path, tier: str) -> dict:
    """The harness's environment: the driver's own, plus what the recorder
    inside the harness cannot work out for itself."""
    return dict(os.environ,
                SENSORIUM_SPOOL=str(spool),
                SENSORIUM_TIER=tier,
                SENSORIUM_TS_ROOT=str(plan.root),
                SENSORIUM_TS_PKG=str(package),
                SENSORIUM_INVOCATION=inv_id,
                SENSORIUM_MANIFEST_DIR=str(spool / ingest.MANIFEST_DIR))


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
    exit 2 says the call or the directory has to be fixed.

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
        print(f"error: {e}", file=sys.stderr)
        return ex.BAD_CALL
    ts_cli._report(summaries, inv_id, harness=_ending(ending))
    return _status(ending)
