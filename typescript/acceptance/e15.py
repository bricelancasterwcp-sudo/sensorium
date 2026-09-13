#!/usr/bin/env python3
"""The E15 runner: §1's single pre-registered measurement, made ONCE.

    E15_LENS=<lens> E15_WORK=<work root> E15_OUT=<out dir> \\
        [E15_ROWS=<n>] [E15_CARGO_TARGET=<dir>] \\
        setsid nohup .venv/bin/python typescript/acceptance/e15.py \\
            > <out>/e15.log 2>&1 &

`typescript/acceptance/e15.sh` is the launcher that spells that; this file
is what it launches. The last act is `<out>/e15.DONE` or `<out>/e15.FAILED`
carrying `exit=<n>`, so silence is distinguishable from success, and
`results-e15-raw.json` is rewritten after EVERY phase with the phase it had
reached and whether that phase finished -- a three-hour run must not be able
to lose two hours of facts to an exception in the third.

WHAT IT DOES (§1, in the order §1 fixes)
-----------------------------------------
    preflight      the lens string, the branch's own `sensorium`, the venv's
                   version (0.14.0 or `.FAILED exit=3`), node, the load
                   guard, the disk floor, the git head
    copy           `copy_lens.sh` -- a throwaway copy, `node_modules`
                   symlinked; vitest's version, read from the copy
    originals      ONE `sensorium ts run -- npx vitest run`; `U`
    survey_check   the locked table, every row's file matched to a member
                   (`.FAILED exit=4` on a file no member ran)
    loop           31 × `sensorium refocus <member> --focus <spec>`
    controls       B (a planted edit) and C (`--window 1`)
    fences         the two fences, the corpus, the suites, the E7 needle
    reads          §1's four H6 commands on the new traces

EVERY LOCATION IS AN ENVIRONMENT VARIABLE
------------------------------------------
No box path appears in this file or in any module it imports. `E15_LENS`,
`E15_WORK` and `E15_OUT` are refused TOGETHER when missing, so one launch
reports all three. `E15_CARGO_TARGET` is optional and is passed to H10's
`cargo test --workspace` alone -- unset, cargo uses `rust/target`, which is
slower and not wrong.

`E15_ROWS=<n>` IS FOR DRY RUNS ONLY
-----------------------------------
It caps the loop at the first `n` rows AND, on a lens that is not the
survey's subject, substitutes a table derived from `corpus/typescript`'s own
three `refocus_*` cases so the plumbing can be exercised end to end before
the real fifteen minutes start. The raw records `preflight.dry_run: true`,
and `assemble_e15.py` REFUSES such a raw: no number from a dry run is kept
anywhere.
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from e15_phases import (DISK_FLOOR_GB, Refused, dir_bytes,          # noqa: E402
                        free_gb, loadavg, phase_controls, phase_copy,
                        phase_fences, phase_loop, phase_originals,
                        phase_reads, phase_survey_check, sh, wait_for_load)
from lens import LENS, REPO_ROOT, sensorium_bin                     # noqa: E402

#: The three locations, and the keys they land under in the record.
E15_ENV = {"E15_LENS": "lens_dir", "E15_WORK": "work",
           "E15_OUT": "out"}

#: Plan ruling A8: the Python driver version §1 cites on every trace of this
#: record. The preflight refuses on anything else, because a stale editable
#: install would stamp the previous release's number on this slice's data.
DRIVER_VERSION = "0.14.0"

#: A commit, spelled whole. `e_fences.py`'s base must be one (Finding 5).
FULL_SHA = re.compile(r"[0-9a-f]{40}")

RUNNER = "typescript/acceptance/e15.py"
RAW_NAME = "results-e15-raw.json"
DOC = ("docs/superpowers/acceptance/"
       "2026-09-13-sensorium-e15-refocus-typescript.md")
SURVEY_REL = ("docs/superpowers/acceptance/"
              "2026-09-13-sensorium-e15-refocus-typescript-survey.md")

#: The DRY RUN's table: `corpus/typescript`'s own three `refocus_*` cases,
#: one focus spec each, every row classed `deterministic`. Plumbing only --
#: these three cases are not the survey's subject and `assemble_e15.py`
#: refuses a raw that carries them. Sorted by directory, so row 2 (control
#: B's planted edit) and row 3 (control C's `--window`) are stable.
DRY_SPECS = {"refocus_diverged": "choose", "refocus_match": "fill",
             "refocus_refused_reused_worker": "one"}

#: The phases, in §1's order. `preflight` is here rather than in
#: `e15_phases.py` because it is what decides whether the run may start.
PHASES = ("preflight", "copy", "originals", "survey_check", "loop",
          "controls", "fences", "reads")

STEPS: list[str] = []


def step(message: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    STEPS.append(line)
    print(line, flush=True)


# -- the locations ----------------------------------------------------------


def env_paths() -> dict:
    """Every location this run touches, from the environment, refused
    TOGETHER when missing -- one launch reports all of them."""
    missing = [k for k in E15_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(2, "unset environment variable(s): "
                         + ", ".join(missing)
                         + " -- this run needs the read-only lens to copy, a "
                           "work root for the copy and the fresh store, and "
                           "an out directory for the transcripts and the "
                           "markers")
    return {name: Path(os.environ[key]).resolve()
            for key, name in E15_ENV.items()}


def dry_rows(lens: Path) -> list[dict]:
    """The DRY RUN's three rows, derived from the lens's own `refocus_*`
    directories. Raises when the lens has none, so a dry run against the real
    subject refuses instead of inventing a table for it."""
    rows = []
    for n, (case, spec) in enumerate(sorted(DRY_SPECS.items()), start=1):
        tests = sorted((lens / case).glob("*.test.ts"))
        if not tests:
            raise Refused(4, f"survey_check: E15_ROWS is set but the lens has "
                             f"no {case}/*.test.ts to build a dry-run table "
                             "from")
        rows.append({"n": n,
                     "test_file": f"{case}/{tests[0].name}",
                     "klass": "deterministic",
                     "reason": "dry run -- not surveyed",
                     "focus": spec, "resolver_matched": None})
    return rows


# -- the preflight ----------------------------------------------------------


def check_fence_base(base) -> str:
    """§1's H10 rests on `e_fences.py`'s diff against the BRANCH POINT.

    `sh()` returns `""` for a `git merge-base` that failed, and `e_fences.py`
    would then run `git diff ..HEAD` -- which is `HEAD..HEAD`, empty -- so
    E-legacy would report "the fenced files show zero diff" over a comparison
    it never made. A base that does not name a commit refuses the run here
    instead of passing vacuously three phases later.
    """
    if not FULL_SHA.fullmatch(base or ""):
        raise Refused(3, "preflight: fence_base -- `git merge-base HEAD main` "
                         f"returned {base!r}, which is not a 40-character "
                         "commit; `e_fences.py` would diff HEAD against HEAD "
                         "and E-legacy would pass over a comparison it never "
                         "made")
    return base


def phase_preflight(ctx, res) -> dict:
    """What THIS run touches, and nothing else.

    Refuses on: a venv whose `sensorium` is not §1's version (`exit=3
    preflight: driver_version`); a work root under the disk floor (`exit=3
    preflight: disk`); a box whose 1-minute load never drops below the guard
    (`exit=3 preflight: load`).
    """
    step("E15 preflight")
    binary = ctx["bin"]
    version = sh(ctx["python"], "-c", "import importlib.metadata as m; "
                                      "print(m.version('sensorium'))")
    if version != DRIVER_VERSION:
        raise Refused(3, f"preflight: driver_version -- the venv reports "
                         f"sensorium {version!r} and §1 cites "
                         f"{DRIVER_VERSION} on every trace of this record; "
                         "run `uv pip install -p .venv/bin/python -e .`")
    check_fence_base(ctx["fence_base"])
    ctx["work"].mkdir(parents=True, exist_ok=True)
    ctx["out"].mkdir(parents=True, exist_ok=True)
    free = free_gb(ctx["work"])
    if free < DISK_FLOOR_GB:
        raise Refused(3, f"preflight: disk -- {ctx['work']} has {free:.1f} GB "
                         f"free and this run needs {DISK_FLOOR_GB} GB "
                         "(33 whole-suite spools)")
    guard = wait_for_load(step)
    rows_override = os.environ.get("E15_ROWS")
    limit = int(rows_override) if rows_override else None
    dry = limit is not None
    ts_pkg = json.loads((REPO_ROOT / "typescript" / "package.json")
                        .read_text(encoding="utf-8"))
    out = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runner": RUNNER, "document": DOC, "survey": SURVEY_REL,
        # `typescript/acceptance/LENS.txt`, verbatim, through the one module
        # that reads it. NOT under a `"lens"` key: that literal is
        # `lens.stamp`'s and the assemblers' alone
        # (`tests/test_acceptance_scripts.py`'s E-branch fence), because rung
        # 2 found six cells stamped with another rung's label by instruments
        # that minted one at MEASUREMENT time. This is a pin, not a cell, and
        # it says so in its name.
        "lens_line": LENS,
        "lens_dir": str(ctx["lens_dir"]), "work": str(ctx["work"]),
        "out": str(ctx["out"]), "store": str(ctx["store"]),
        "copy": str(ctx["copy"]),
        "sensorium_bin": binary,
        "python": ctx["python"], "python_version": sh(ctx["python"], "-V"),
        "driver_version": version,
        "recorder": ctx["recorder"],
        "sensorium_ts_version": ts_pkg.get("version"),
        "node": sh("node", "--version"),
        # Read from the COPY in the `copy` phase -- the copy is what carries
        # the `node_modules` symlink `npx vitest` resolves through, and the
        # phase order §1 fixes puts the copy after this.
        "vitest": None, "vitest_read_in": None,
        "load_guard": guard, "load_1min_at_start": round(loadavg(), 2),
        "work_disk_free_gb": round(free, 2),
        "disk_floor_gb": DISK_FLOOR_GB,
        "cargo_target": ctx["cargo_target"],
        "git_head": ctx["head"], "git_branch": ctx["branch"],
        "git_porcelain": sh("git", "-C", str(REPO_ROOT), "status",
                            "--porcelain"),
        "fence_base": ctx["fence_base"],
        "nproc": os.cpu_count(),
        "dry_run": dry, "rows_override": limit, "dry_run_rows": None,
    }
    if dry:
        out["dry_run_rows"] = dry_rows(ctx["lens_dir"])
        out["dry_run_reading"] = (
            "E15_ROWS was set, so this run is PLUMBING: the rows are the "
            "lens's own `refocus_*` cases and not the survey's 31, and "
            "`assemble_e15.py` refuses this raw record")
    step(f"preflight ok: sensorium {version}, node {out['node']}, load "
         f"{guard['load']}, {free:.1f} GB free, dry_run={dry}")
    return out


# -- the markers and the raw record -----------------------------------------


def _partial_json(res: dict) -> str:
    """Whatever of the record CAN be serialised, key by key, with the keys
    that could not NAMED. A run that measured for three hours must lose one
    value to a serialisation defect, not all of them."""
    kept, lost = {}, []
    for k, v in res.items():
        try:
            json.dumps({k: v}, default=str)
        except (TypeError, ValueError):
            lost.append(k)
        else:
            kept[k] = v
    kept["keys_that_could_not_be_serialised"] = lost
    return json.dumps(kept, indent=2, default=str)


def make_writer(raw_path: Path):
    def write(res: dict) -> None:
        try:
            raw_path.write_text(json.dumps(res, indent=2, default=str),
                                encoding="utf-8")
        except (TypeError, ValueError):
            raw_path.write_text(_partial_json(res), encoding="utf-8")
    return write


def context(paths) -> dict:
    head = sh("git", "-C", str(REPO_ROOT), "rev-parse", "HEAD")
    base = (sh("git", "-C", str(REPO_ROOT), "merge-base", "HEAD", "main")
            or sh("git", "-C", str(REPO_ROOT), "merge-base", "HEAD",
                  "origin/main"))
    python = str(REPO_ROOT / ".venv" / "bin" / "python")
    version = sh(python, "-c", "import importlib.metadata as m; "
                               "print(m.version('sensorium'))")
    ts_pkg = json.loads((REPO_ROOT / "typescript" / "package.json")
                        .read_text(encoding="utf-8"))
    return {
        "lens_dir": paths["lens_dir"], "work": paths["work"],
        "out": paths["out"],
        "copy": paths["work"] / "lens", "store": paths["work"] / "store",
        "accept": HERE, "survey": REPO_ROOT / SURVEY_REL,
        "bin": sensorium_bin(), "python": python,
        "cargo_target": os.environ.get("E15_CARGO_TARGET"),
        "head": head, "fence_base": base,
        "branch": sh("git", "-C", str(REPO_ROOT), "rev-parse",
                     "--abbrev-ref", "HEAD"),
        "recorder": (f"sensorium {version} / sensorium-ts "
                     f"{ts_pkg.get('version')} at {head[:12]}"),
        "step": step,
    }


PHASE_FN = {"preflight": phase_preflight, "copy": phase_copy,
            "originals": phase_originals, "survey_check": phase_survey_check,
            "loop": phase_loop, "controls": phase_controls,
            "fences": phase_fences, "reads": phase_reads}


def cleanup(ctx) -> dict:
    """What the run left behind. `None` is "there is nothing there to
    count"; `0` is counted-and-zero."""
    store, traces = ctx["store"], ctx["store"] / "traces"
    spool = ctx["store"] / "spool"
    return {
        "store_bytes": dir_bytes(store),
        "spool_bytes": dir_bytes(spool),
        "traces": len(list(traces.glob("*.db"))) if traces.is_dir() else None,
        "spools": len([p for p in spool.iterdir()]) if spool.is_dir() else None,
        "copy_bytes": dir_bytes(ctx["copy"]),
        "work_disk_free_gb": round(free_gb(ctx["work"]), 2)
        if ctx["work"].is_dir() else None,
        "repo_porcelain_after": sh("git", "-C", str(REPO_ROOT), "status",
                                   "--porcelain"),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


#: The two marker names, and the exit a SIGTERM writes. 143 is 128 + 15, the
#: shell's own spelling for a process terminated by signal 15, so a reader
#: who sees it in the marker recognises it without a table.
DONE_MARKER, FAILED_MARKER = "e15.DONE", "e15.FAILED"
SIGTERM_EXIT = 143


def write_marker(out_dir: Path, rc: int, why: str = "") -> Path:
    """`<out>/e15.DONE` on 0, `<out>/e15.FAILED` otherwise, carrying
    `exit=<n>`.

    The ONE place a marker is written, so every exit path -- a phase
    refusal, an exception, a `SystemExit` raised inside `lens.sensorium_bin`,
    a Ctrl-C, a SIGTERM -- writes the same shape, and a test can make each of
    them happen. Silence is what the marker exists to rule out, so a failure
    to write one is printed rather than swallowed.
    """
    path = out_dir / (DONE_MARKER if rc == 0 else FAILED_MARKER)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n{why}\n",
            encoding="utf-8")
    except OSError as e:                                       # noqa: BLE001
        sys.stderr.write(f"could not write {path}: {e}\n")
    return path


def exit_code_of(exc: BaseException) -> int:
    """The exit a raised exception should carry into the marker.

    `SystemExit` carries its own -- `lens.sensorium_bin()` raises
    `SystemExit(3)` when the branch's binary is not where it must be, and
    that 3 is the number a reader of the marker needs. `KeyboardInterrupt`
    is 130, the shell's 128 + 2. Everything else is this runner's generic
    phase failure, 5.
    """
    if isinstance(exc, SystemExit):
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    if isinstance(exc, KeyboardInterrupt):
        return 130
    return 5


def install_sigterm(out_dir: Path, res: dict, write) -> None:
    """Write a marker if this process is terminated.

    A three-hour loop is the kind of thing an operator, an OOM sweep or a
    reboot kills, and a run that vanished without a marker is
    indistinguishable from one still going. The handler writes the raw record
    it has and the marker, then `os._exit` -- not `sys.exit`, which raises
    `SystemExit` in whatever the main thread happens to be doing and would
    write a SECOND marker on the way out.
    """
    def handler(signum, _frame):                               # noqa: ARG001
        res["status"] = "signalled"
        res["signal"] = "SIGTERM"
        res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        res["exit"] = SIGTERM_EXIT
        try:
            write(res)
        except Exception:                                      # noqa: BLE001
            pass
        write_marker(out_dir, SIGTERM_EXIT, "signal: SIGTERM")
        os._exit(SIGTERM_EXIT)                                 # noqa: SLF001

    try:
        signal.signal(signal.SIGTERM, handler)
    except ValueError:
        # Not the main thread (a test importing this module from a worker).
        # Recorded rather than raised: the handler is a safety net, and the
        # run itself is unaffected.
        sys.stderr.write("could not install the SIGTERM handler (not the "
                         "main thread); a terminated run will leave no "
                         "marker\n")


def run_phases(ctx, res, write) -> tuple[int, str]:
    """§1's eight phases, in §1's order. Returns (exit, why).

    A phase's own `Refused` carries its exit; anything else is 5. A loop that
    did not finish is `5` too, and by its own sentence: a `.DONE` over 23 of
    31 rows would publish PASS words over a population §1 fixes at 31.
    """
    for name in PHASES:
        res["phase"], res["status"] = name, "running"
        write(res)
        started = time.monotonic()
        try:
            res[name] = PHASE_FN[name](ctx, res)
        except Refused as e:
            res["status"] = "refused"
            res["refused"] = {"phase": name, "message": str(e),
                              "exit": e.code}
            step(f"REFUSED in {name}: {e}")
            return e.code, str(e)
        res["phases"][name] = {"ok": True,
                               "wall_s": round(time.monotonic() - started, 3)}
        res["status"] = "ok"
        write(res)
        step(f"phase {name} ok in {res['phases'][name]['wall_s']}s")
        short = (res[name] or {}).get("incomplete") if isinstance(
            res[name], dict) else None
        if short:
            res["status"] = "incomplete"
            res["incomplete"] = {"phase": name, "message": short}
            step(f"INCOMPLETE in {name}: {short}")
            return 5, short
    return 0, ""


def main(argv) -> int:
    try:
        paths = env_paths()
    except Refused as e:
        # The only path with no marker, because there is no out directory to
        # write one in: the variable that names it is the one that is unset.
        sys.stderr.write(f"refused: {e}\n")
        return e.code
    out_dir = paths["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for marker in (DONE_MARKER, FAILED_MARKER):
        (out_dir / marker).unlink(missing_ok=True)
    raw_path = out_dir / RAW_NAME
    write = make_writer(raw_path)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": RUNNER, "document": DOC, "survey": SURVEY_REL,
                 "phase": None, "status": "starting", "phases": {}}
    install_sigterm(out_dir, res, write)
    ctx, rc, why, raised = None, 0, "", None
    try:
        # INSIDE the try: `context()` calls `lens.sensorium_bin()`, which
        # raises `SystemExit(3)` when the branch's binary is not where it
        # must be -- an exit path that used to leave no marker at all.
        ctx = context(paths)
        ctx["write"] = write
        rc, why = run_phases(ctx, res, write)
    except BaseException as e:                                 # noqa: BLE001
        rc = exit_code_of(e)
        why = f"{type(e).__name__}: {e}".strip()
        res["status"] = "error"
        res["error"] = {"phase": res.get("phase"), "exit": rc,
                        "traceback": traceback.format_exc()}
        step(f"ERROR in {res.get('phase')}:\n{res['error']['traceback']}")
        sys.stderr.write(res["error"]["traceback"])
        # Re-raised AFTER the marker is written, never instead of it: an
        # interrupt is the operator's, and swallowing it would leave them
        # holding a terminal that did not stop.
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raised = e
    if ctx is not None:
        try:
            res["cleanup"] = cleanup(ctx)
        except Exception:                                      # noqa: BLE001
            res["cleanup"] = {"error": traceback.format_exc()}
    res["steps"] = list(STEPS)
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    res["exit"] = rc
    write(res)
    write_marker(out_dir, rc, why)
    step(f"done rc={rc}; raw facts at {raw_path}")
    if raised is not None:
        raise raised
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
