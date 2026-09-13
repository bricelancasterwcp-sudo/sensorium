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
E15_ENV = {"E15_LENS": "lens", "E15_WORK": "work", "E15_OUT": "out"}

#: Plan ruling A8: the Python driver version §1 cites on every trace of this
#: record. The preflight refuses on anything else, because a stale editable
#: install would stamp the previous release's number on this slice's data.
DRIVER_VERSION = "0.14.0"

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
        # that reads it -- no instrument mints a lens label of its own.
        "lens": LENS,
        "lens_dir": str(ctx["lens"]), "work": str(ctx["work"]),
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
        out["dry_run_rows"] = dry_rows(ctx["lens"])
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
        "lens": paths["lens"], "work": paths["work"], "out": paths["out"],
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


def main(argv) -> int:
    try:
        paths = env_paths()
    except Refused as e:
        sys.stderr.write(f"refused: {e}\n")
        return e.code
    out_dir = paths["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for marker in ("e15.DONE", "e15.FAILED"):
        (out_dir / marker).unlink(missing_ok=True)
    raw_path = out_dir / RAW_NAME
    write = make_writer(raw_path)
    ctx = context(paths)
    ctx["write"] = write
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": RUNNER, "document": DOC, "survey": SURVEY_REL,
                 "phase": None, "status": "starting", "phases": {}}
    rc, why = 0, ""
    for name in PHASES:
        res["phase"], res["status"] = name, "running"
        write(res)
        started = time.monotonic()
        try:
            res[name] = PHASE_FN[name](ctx, res)
        except Refused as e:
            rc, why = e.code, str(e)
            res["status"] = "refused"
            res["refused"] = {"phase": name, "message": str(e),
                              "exit": e.code}
            step(f"REFUSED in {name}: {e}")
            break
        except Exception:                                      # noqa: BLE001
            rc, why = 5, traceback.format_exc().strip().splitlines()[-1]
            res["status"] = "error"
            res["error"] = {"phase": name, "traceback": traceback.format_exc()}
            step(f"ERROR in {name}:\n{res['error']['traceback']}")
            sys.stderr.write(res["error"]["traceback"])
            break
        res["phases"][name] = {"ok": True,
                               "wall_s": round(time.monotonic() - started, 3)}
        res["status"] = "ok"
        write(res)
        step(f"phase {name} ok in {res['phases'][name]['wall_s']}s")
    try:
        res["cleanup"] = cleanup(ctx)
    except Exception:                                          # noqa: BLE001
        res["cleanup"] = {"error": traceback.format_exc()}
    res["steps"] = list(STEPS)
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    res["exit"] = rc
    write(res)
    (out_dir / ("e15.DONE" if rc == 0 else "e15.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n{why}\n",
        encoding="utf-8")
    step(f"done rc={rc}; raw facts at {raw_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
