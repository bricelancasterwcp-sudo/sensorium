#!/usr/bin/env python3
"""E17's MACHINERY layer: the refusal, the phase runner, the environment.

Self-contained by P14: `tests/acceptance_e16/` is another measurement's
instrument, and importing it would couple two records to one file. What is
mirrored here is its SHAPE -- `phase()`'s timed, critical-aware semantics,
`_run()`'s own-session kill ladder, `_keep()`'s transcripts -- not its code.

`env()` builds the COMPLETE environment §1's kill-rules paragraph pins, as
a dict and never as an overlay on the launching shell's: `PATH` = the
venv's `bin`, then `E17_CARGO_BIN`, `E17_NODE_BIN` and the three system
directories; `HOME`; `LANG`; `PYTHONDONTWRITEBYTECODE=1`; and
`SENSORIUM_CARGO_SENSORIUM` when the launching environment set it. That
makes "no `sensorium` on PATH ahead of the venv's", "`PYTEST_ADDOPTS`
unset" and "`SENSORIUM_NO_INVOCATION_LOG` unset" facts by construction
rather than assertions about whichever terminal started the run.

A phase leaves `None` or a measurement, never a default. `phase()` records
a non-critical exception and returns `None`, so a cell that lost its input
DROPS instead of the run dying with six cells unread; a `critical` phase is
a PRECONDITION and its failure raises `Refused`, ending the run. A `_run`
killed on its timer comes back `rc: None` with `killed: true`, which every
reader treats as a hole rather than as a failure of the thing measured.
"""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: §1's kill rules: every cell 10 min, the part 45 min PLUS H1's timer
#: (`3 × the CLI-path corpus wall time, never below 10 min`, arriving
#: through `E17_H1_TIMER`).
CELL_TIMER = 600
PART_TIMER = 2700
DEFAULT_H1_TIMER = 600
#: The rehearsal's. A dry run that waited out a real store's timers would
#: be measuring nothing for three quarters of an hour.
DRY_TIMERS = {"cell": 120, "h1": 120, "part": 900}


class Refused(Exception):
    """A precondition that failed, or a cap that passed: either way the
    run ends here rather than publishing a partial measurement as one."""


class Part:
    """One E17 measurement: its locations, its environment, its phases."""

    def __init__(self, work: Path, out: Path, label: str, dry: bool,
                 live: Path) -> None:
        self.work, self.out, self.label = Path(work), Path(out), label
        self.dry, self.live = dry, Path(live)
        #: The venv's own interpreter, ABSOLUTE: §1's subject is
        #: `<venv>/bin/python -m sensorium`, and a bare `python` would be
        #: whatever the launching shell's PATH resolved.
        self.python = str(REPO / ".venv" / "bin" / "python")
        self.store = self.work / "store"
        self.transcripts = self.work / "transcripts"
        self.cargo_bin = os.environ.get("E17_CARGO_BIN", "")
        self.node_bin = os.environ.get("E17_NODE_BIN", "")
        h1 = _int(os.environ.get("E17_H1_TIMER"), DEFAULT_H1_TIMER)
        self.timers = (dict(DRY_TIMERS) if dry else
                       {"cell": CELL_TIMER, "h1": h1,
                        "part": PART_TIMER + h1})
        self.phases: list[dict] = []
        self.started = time.time()

    def env(self, extra: dict | None = None) -> dict:
        """§1's pinned environment plus a cell's (module docstring)."""
        path = os.pathsep.join(
            [str(REPO / ".venv" / "bin"), *[d for d in (self.cargo_bin,
                                                        self.node_bin) if d],
             "/usr/local/bin", "/usr/bin", "/bin"])
        values = {"PATH": path, "HOME": str(Path.home()),
                  "LANG": os.environ.get("LANG", "C.UTF-8"),
                  "PYTHONDONTWRITEBYTECODE": "1"}
        driver = os.environ.get("SENSORIUM_CARGO_SENSORIUM")
        if driver:
            values["SENSORIUM_CARGO_SENSORIUM"] = driver
        values.update(extra or {})
        return values

    def phase(self, name: str, fn, critical: bool = False):
        """One phase, timed, with its own failure recorded rather than
        raised -- so a cell that lost its input drops instead of the run
        dying with six cells unread.

        `critical` inverts that for the phases that are PRECONDITIONS
        rather than measurements: E16's part A watched a swallowed build
        failure carry an unrebuilt binary all the way to a DONE.
        """
        started = time.time()
        try:
            value, error = fn(), None
        except Refused:
            raise
        except Exception as exc:                        # noqa: BLE001
            value, error = None, f"{type(exc).__name__}: {exc}"
            if critical:
                self._phase_done(name, started, error)
                raise Refused(f"{name} is a precondition and it failed: "
                              f"{error}") from exc
        self._phase_done(name, started, error)
        elapsed = time.time() - self.started
        if elapsed > self.timers["part"]:
            raise Refused(f"the part's {self.timers['part']}s cap passed "
                          f"after {name}: this is an infrastructure kill, "
                          f"not a measurement")
        return value

    def _phase_done(self, name: str, started: float, error) -> None:
        row = {"name": name, "seconds": round(time.time() - started, 3),
               "error": error}
        self.phases.append(row)
        print(f"[{time.time() - self.started:7.1f}s] {name}: "
              f"{row['seconds']}s" + (f" ERROR {error}" if error else ""),
              flush=True)

    def _run(self, argv, cwd, env, timeout) -> dict:
        """One subprocess, in its own session, killed BY GROUP on the timer.

        `start_new_session` plus `killpg`: a `cargo` or an `npx` that hangs
        has children, and killing the leader alone leaves them holding the
        cores. SIGTERM, two seconds, then SIGKILL.
        """
        started = time.time()
        proc = subprocess.Popen(
            [str(a) for a in argv], cwd=str(cwd), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", start_new_session=True)
        killed = False
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            killed = True
            _killpg(proc.pid, signal.SIGTERM)
            try:
                out, err = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                _killpg(proc.pid, signal.SIGKILL)
                out, err = proc.communicate()
        return {"argv": [str(a) for a in argv], "cwd": str(cwd),
                "rc": None if killed else proc.returncode, "killed": killed,
                "out": out or "", "err": err or "",
                "seconds": round(time.time() - started, 3)}

    def _keep(self, name: str, payload) -> Path:
        """One command's whole output on disk, at 0600. A dict is written
        as a `_run` transcript with its argv and exit; anything else is
        written as the text it is."""
        self.transcripts.mkdir(parents=True, exist_ok=True)
        path = self.transcripts / f"{name}.txt"
        if isinstance(payload, dict):
            text = (f"$ {' '.join(payload.get('argv') or [])}\n"
                    f"# cwd {payload.get('cwd')}  exit {payload.get('rc')}  "
                    f"{payload.get('seconds')}s\n{payload.get('out') or ''}"
                    + (f"\n--- stderr ---\n{payload['err']}"
                       if payload.get("err") else ""))
        else:
            text = str(payload)
        path.write_text(text, encoding="utf-8")
        os.chmod(path, 0o600)
        return path

    def installed_version(self) -> str | None:
        """What `sensorium` reads IN THE VENV -- through `self.python`, not
        through this process: the instrument may be launched by another
        interpreter, and the subject is the venv's package."""
        r = self._run([self.python, "-c", "import importlib.metadata as m; "
                       "print(m.version('sensorium'))"], REPO, self.env(), 60)
        return r["out"].strip() if r["rc"] == 0 else None

    def rel(self, path, root=None) -> str:
        """A path as the work root sees it: the one place a box path is
        written down is the record's §2 pin table."""
        try:
            return str(Path(path).relative_to(Path(root or self.work)))
        except ValueError:
            return str(path)


def _killpg(pid: int, sig) -> None:
    try:
        os.killpg(os.getpgid(pid), sig)
    except (ProcessLookupError, PermissionError):
        pass


def _int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def sha8(text: str) -> str:
    """`sha256(value)[:8]` -- how a secret is named in a committed file."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def median(values) -> float | None:
    """The middle reading, or `None` over nothing -- which is the whole
    reason this is not `statistics.median`: an empty sample is a
    measurement nobody took, not a zero."""
    rows = sorted(values)
    if not rows:
        return None
    mid = len(rows) // 2
    return (rows[mid] if len(rows) % 2
            else (rows[mid - 1] + rows[mid]) / 2)


