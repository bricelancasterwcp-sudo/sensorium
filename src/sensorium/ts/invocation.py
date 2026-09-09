"""The driver's own record of one run, and the harness's ending.

Two small files sit beside the spools in a spool directory, and both are
written by the driver (`sensorium ts run`) and read by the converter
(`sensorium ts ingest`). They exist because a spool cannot say these
things: a container knows its own pid and its own environment, but not
which command produced it, not where the project root is, and not what the
harness exited with -- nobody inside the harness waits for the harness.

    invocation.json   written before the harness is spawned
    harness.json      written after it returns; ABSENT when the driver
                      died first, which is why every reader of it treats
                      absence as a fact and not as a zero

The dataclasses here are the contract between the two commands. They are
in this module rather than in either one so that neither owns it: `ingest`
imports `Invocation` to read, `run` imports it to write, and a field
either adds is a field the other sees.
"""
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

#: The two harnesses this recorder wires. `vitest` runs the Vite plugin;
#: `node-test` runs the loader hook. Anything else is a driver refusal, not
#: something the converter has to have an opinion about.
HARNESSES = ("vitest", "node-test")

INVOCATION_FILE = "invocation.json"
HARNESS_FILE = "harness.json"


class InvocationError(Exception):
    """A spool directory's own record is missing or unreadable. Always
    names the file: the caller's next move is to look at it."""


@dataclass(frozen=True)
class Invocation:
    """What the driver knew before it spawned anything.

    `root` is the project directory every path in a trace is made relative
    to; `cwd` is where the driver was standing, which is not necessarily
    the same place. `recorder` is the fallback for a spool whose BOOT
    record carries no `version` -- the driver read it out of the recorder's
    own package, and a BOOT that names its writer wins over it (R5).
    """

    invocation: str
    harness: str
    harness_args: list[str]
    root: str
    cwd: str
    argv: list[str]
    env_hash: str
    start_ts: float
    wrapper: str
    vitest: str | None
    node: str
    driver_version: str
    recorder: str

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> "Invocation":
        missing = [f.name for f in fields(cls) if f.name not in data]
        if missing:
            raise InvocationError(
                f"{INVOCATION_FILE} lacks {', '.join(missing)}")
        return cls(**{f.name: data[f.name] for f in fields(cls)})


@dataclass(frozen=True)
class HarnessExit:
    """What the driver witnessed when the harness returned.

    `basis` is always `"waited"` -- the file exists only because somebody
    waited -- and it is carried into the trace beside the status so no
    reader has to remember which of the two exit facts it is holding
    (TRACE-FORMAT section 4). `status` and `signal` are exclusive: a
    process killed by a signal chose no status.
    """

    status: int | None
    signal: str | None
    wall_start_ts: float
    wall_end_ts: float
    basis: str = "waited"

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> "HarnessExit":
        missing = [f.name for f in fields(cls)
                   if f.name not in data and f.name != "basis"]
        if missing:
            raise InvocationError(f"{HARNESS_FILE} lacks {', '.join(missing)}")
        return cls(**{f.name: data[f.name] for f in fields(cls)
                      if f.name in data})

    def meta(self) -> dict:
        """The `harness_exit` value a trace carries: the ending and how it
        was learned, and nothing about the driver's own clock -- the walls
        are the driver's business, not a fact about the recorded program."""
        return {"status": self.status, "signal": self.signal,
                "basis": self.basis}


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise InvocationError(f"no {path.name} in {path.parent}: this is not "
                              "a spool directory a driver wrote") from None
    except json.JSONDecodeError as e:
        raise InvocationError(f"{path} is not readable JSON: {e}") from None
    if not isinstance(data, dict):
        raise InvocationError(f"{path} is not an object")
    return data


def read_invocation(spool_dir: Path) -> Invocation:
    return Invocation.from_json(_load(Path(spool_dir) / INVOCATION_FILE))


def read_harness(spool_dir: Path) -> HarnessExit | None:
    """The harness's ending, or None when nobody recorded one.

    Absence is a fact and never an error: the driver writes this file after
    the harness returns, so a driver that was killed first leaves a spool
    directory that is complete in every other way. `ingest` is re-runnable
    over exactly that directory.
    """
    path = Path(spool_dir) / HARNESS_FILE
    if not path.is_file():
        return None
    return HarnessExit.from_json(_load(path))
