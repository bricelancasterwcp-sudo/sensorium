#!/usr/bin/env python3
"""E15's phases: the copy, the originals, the survey check, the loop, the two
controls, the fences and the four reads.

`e15.py` holds the locations, the preflight, the markers and `main`; this
module holds the seven phases after the preflight and the handful of shared
primitives they all need. The seam is `rust/tests/acceptance_e4_phases.py`'s
and it exists for the reason that file states: no file in this repository may
pass 800 lines, and the protocols and the runner that sequences them are the
natural cut.

Every phase returns RAW FACTS and decides nothing. `e15_report.cells` is
where §1's rules turn them into `holds`, and §2-§5 of the acceptance record
are written by hand from the assembled results.

THREE RULES THAT RUN THROUGH ALL OF THEM
-----------------------------------------
* **the printed lines are bookkeeping, the store is the authority.** The
  driver prints a `run:` line per container carrying `file:`; this module
  records those lines AND opens each trace read-only for its own
  `test_file`, and the mapping the loop uses is the TRACE's (design
  2026-09-07 G3, restated for this branch in `refocus_typescript`'s
  docstring). A changed print must not be able to change which original a
  row refocuses.
* **nothing writes to the lens.** The subject is the copy `copy_lens.sh`
  makes. Control B edits the COPY and this module restores that file FROM
  the lens afterwards and compares the sha; every trace is opened through a
  `mode=ro` URI.
* **a bound reached is a recorded fact.** The loop carries a three-hour
  budget and each refocus 900 s (§1's kill rules). A row the budget never
  reached is `not_run` with its reason, which the cells publish as
  not-measured rather than as a pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

from e15_read import (h6_argv, parse_flow, parse_refocus, parse_survey,
                      parse_watch)
from lens import REPO_ROOT

# -- the pre-registered bounds ----------------------------------------------

#: The load guard, `e6pp.sh`'s exactly: two instruments in one slice that
#: guard at different thresholds do not measure the same box.
LOAD_MAX, LOAD_TRIES, LOAD_SLEEP = 4.0, 90, 20
#: §1's kill rules: the loop is bounded at three hours, each refocus at
#: 900 s, each reader at 120 s.
LOOP_BUDGET_S = 3 * 3600
REFOCUS_TIMEOUT = 900
READER_TIMEOUT = 120
#: Not §1's -- the originals are one whole-suite recording and the fences are
#: three test suites and a cargo build. Generous, and recorded, so a bound
#: reached is a fact rather than an exception.
ORIGINALS_TIMEOUT = 3600
FENCE_TIMEOUT = 7200
#: The floor the preflight refuses under (rulings: E15 needs ~13 GB
#: transient).
DISK_FLOOR_GB = 30

#: The E7 needle: this spelling must not appear in any transcript this run
#: produced. A `refocus` that told a reader to re-record by hand would be
#: offering the very thing the command exists to replace.
NEEDLE = "sensorium run --focus"

RUN_LINE = re.compile(r"^run: (?P<run>\S+)\s+pid: (?P<pid>\S+)\s+"
                      r"file: (?P<file>\S+)\s+events: (?P<events>\d+)\s+"
                      r"tasks: (?P<tasks>\d+)\s*$", re.M)
INVOCATION = re.compile(r"^invocation: (?P<inv>\S+)\s+traces: (?P<n>\d+)"
                        r"(?:\s+harness exit: (?P<exit>.+))?$", re.M)
DURATION = re.compile(r"^\s*Duration\s+(?P<n>[0-9.]+)(?P<unit>ms|s)\b", re.M)


class Refused(Exception):
    """A refusal with the exit code its marker carries."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


# -- primitives -------------------------------------------------------------


def sh(*args, cwd=None) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True,
                          text=True).stdout.strip()


def free_gb(path: Path) -> float:
    return shutil.disk_usage(str(path)).free / 1e9


def dir_bytes(path: Path) -> int | None:
    if not Path(path).is_dir():
        return None
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            p = Path(root) / name
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def loadavg() -> float:
    return os.getloadavg()[0]


def wait_for_load(step=print) -> dict:
    """Block until the 1-minute load is under the ceiling, `e6pp.sh`'s guard.

    Returns the reading it went ahead on and how many tries it took, so the
    record can say whether the box was quiet or merely became quiet.
    """
    load = loadavg()
    for tries in range(LOAD_TRIES):
        load = loadavg()
        if load < LOAD_MAX:
            return {"load": round(load, 2), "tries": tries, "waited": False
                    if tries == 0 else True}
        step(f"load {load:.2f} >= {LOAD_MAX}; waiting {LOAD_SLEEP}s "
             f"({tries + 1}/{LOAD_TRIES})")
        time.sleep(LOAD_SLEEP)
    raise Refused(3, f"preflight: load -- the 1-minute load never dropped "
                     f"below {LOAD_MAX} in {LOAD_TRIES} tries (last {load})")


def plain_env() -> dict:
    """The launcher's environment minus every `SENSORIUM_*` and
    `CARGO_TARGET_DIR`. What a phase needs is put back explicitly, so every
    variable a child sees is a property of this file rather than of whoever
    launched the run."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith("SENSORIUM_") and k != "CARGO_TARGET_DIR"} | {
        "PYTHONDONTWRITEBYTECODE": "1"}


def guarded(cmd, cwd, env, timeout, log: Path | None = None) -> dict:
    """One child, bounded, with its whole output kept.

    A killed child's partial output is saved and `timed_out` is True: §1's
    kill rules make a bound reached a recorded fact, and a phase that raised
    on one would take down every number already read.
    """
    started = time.monotonic()
    try:
        proc = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env,
                              capture_output=True, text=True, timeout=timeout)
        out, err, rc, killed = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        rc, killed = None, True
    wall = time.monotonic() - started
    text = out + err
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(text, encoding="utf-8")
    return {"command": " ".join(str(c) for c in cmd), "cwd": str(cwd),
            "exit": rc, "wall_s": round(wall, 3), "timed_out": killed,
            "timeout_s": timeout, "out": out, "err": err, "text": text,
            "log": str(log) if log else None}


def duration_s(text: str) -> float | None:
    """vitest's own `Duration` line, in seconds. The LAST one in the text."""
    last = None
    for m in DURATION.finditer(text):
        value = float(m.group("n"))
        last = value / 1000.0 if m.group("unit") == "ms" else value
    return None if last is None else round(last, 4)


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def trace_meta(store: Path, run_id: str) -> dict:
    """One trace's meta, READ-ONLY.

    Opened through a `mode=ro` URI rather than `db.open_trace`, which
    connects read-write: this run must be able to say it added nothing to a
    trace it only read.
    """
    path = Path(store) / "traces" / f"{run_id}.db"
    if not path.is_file():
        return {}
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {k: json.loads(v)
                for k, v in conn.execute("SELECT key, value FROM meta")}
    finally:
        conn.close()


def store_snapshot(store: Path) -> dict:
    """What is in the store right now: the spool directories and the traces,
    by name, so a later snapshot can name exactly what an invocation added."""
    traces = Path(store) / "traces"
    spool = Path(store) / "spool"
    return {
        "spools": sorted(p.name for p in spool.iterdir()) if spool.is_dir()
        else [],
        "traces": {p.name: p.stat().st_size
                   for p in traces.glob("*.db")} if traces.is_dir() else {},
    }


def store_delta(store: Path, before: dict, after: dict) -> dict:
    """The bytes one invocation added, named by what it added them under."""
    new_spools = [s for s in after["spools"] if s not in before["spools"]]
    new_traces = [t for t in after["traces"] if t not in before["traces"]]
    spool_bytes = sum(dir_bytes(Path(store) / "spool" / s) or 0
                      for s in new_spools)
    trace_bytes = sum(after["traces"][t] for t in new_traces)
    return {"new_spools": new_spools, "new_traces": new_traces,
            "spool_bytes": spool_bytes if new_spools else 0,
            "trace_bytes": trace_bytes if new_traces else 0}


# -- copy -------------------------------------------------------------------


def phase_copy(ctx, res) -> dict:
    """A throwaway copy of the lens, `copy_lens.sh`'s, with `node_modules`
    symlinked. The lens is the INPUT and nothing in this run writes to it."""
    script = ctx["accept"] / "copy_lens.sh"
    dst = ctx["copy"]
    got = guarded(["bash", "-c",
                   f'set -e; . "{script}"; copy_lens "$1" "$2"', "_",
                   str(ctx["lens_dir"]), str(dst)],
                  REPO_ROOT, plain_env(), ORIGINALS_TIMEOUT,
                  ctx["out"] / "copy.txt")
    if got["exit"] != 0:
        raise Refused(5, f"copy: copy_lens exited {got['exit']} -- "
                         f"{got['text'][-400:]}")
    node_modules = dst / "node_modules"
    # The vitest version, read FROM THE COPY: preflight records it, but the
    # copy is what carries the `node_modules` symlink the version is resolved
    # through, so the reading happens here and lands in `preflight` beside
    # node's (the phase order §1 fixes puts the copy after the preflight).
    vitest = guarded(["npx", "vitest", "--version"], dst, plain_env(), 300,
                     ctx["out"] / "vitest-version.txt")
    version = (vitest["out"] or "").strip().splitlines()[-1:] or [None]
    res.setdefault("preflight", {})["vitest"] = version[0]
    res["preflight"]["vitest_read_in"] = "the copy, after copy_lens"
    return {"copy": str(dst), "lens_dir": str(ctx["lens_dir"]),
            "node_modules_is_a_symlink": node_modules.is_symlink(),
            "node_modules_points_at": (str(os.readlink(node_modules))
                                       if node_modules.is_symlink() else None),
            "test_files": len(list(dst.rglob("*.test.ts")))
            + len(list(dst.rglob("*.test.tsx"))),
            "copy_lens": {k: v for k, v in got.items()
                          if k not in ("out", "err", "text")},
            "vitest_version": version[0],
            "vitest_command": vitest["command"]}


# -- the originals ----------------------------------------------------------


def phase_originals(ctx, res) -> dict:
    """ONE unfocused recording of the whole suite: `sensorium ts run -- npx
    vitest run` from the copy's root, the harness command as the survey's
    originals block names it.

    `U` is the count of `run:` lines; every later count is read against it.
    """
    ctx["step"]("originals: one unfocused whole-suite recording")
    guard = wait_for_load(ctx["step"])
    before = store_snapshot(ctx["store"])
    env = plain_env() | {"SENSORIUM_DIR": str(ctx["store"])}
    got = guarded([ctx["bin"], "ts", "run", "--", "npx", "vitest", "run"],
                  ctx["copy"], env, ORIGINALS_TIMEOUT,
                  ctx["out"] / "originals.txt")
    lines = [{"run": m.group("run"), "pid": m.group("pid"),
              "file": m.group("file"), "events": int(m.group("events")),
              "tasks": int(m.group("tasks"))}
             for m in RUN_LINE.finditer(got["text"])]
    inv = INVOCATION.search(got["text"])
    after = store_snapshot(ctx["store"])
    members, by_file, disagreements = {}, {}, []
    for line in lines:
        meta = trace_meta(ctx["store"], line["run"])
        test_file = meta.get("test_file")
        member = {
            "run": line["run"], "test_file": test_file,
            "printed_file": line["file"],
            "harness_command": meta.get("harness_command"),
            "harness_cwd": meta.get("harness_cwd"),
            "tier": (meta.get("env") or {}).get("SENSORIUM_TIER"),
            "invocation": meta.get("invocation"),
            "recorder": meta.get("recorder"),
            "driver_version": meta.get("driver_version"),
            "vitest": meta.get("vitest"), "node": meta.get("node"),
            "events": line["events"], "tasks": line["tasks"],
        }
        members[line["run"]] = member
        if test_file is None:
            disagreements.append({"run": line["run"], "why": "the trace "
                                  "records no single test_file"})
        else:
            if test_file != line["file"]:
                disagreements.append({"run": line["run"],
                                      "trace": test_file,
                                      "printed": line["file"]})
            by_file.setdefault(test_file, []).append(line["run"])
    return {
        "command": got["command"], "cwd": str(ctx["copy"]),
        "exit": got["exit"], "wall_s": got["wall_s"],
        "timed_out": got["timed_out"],
        "harness_duration_s": duration_s(got["text"]),
        "U": len(lines), "run_lines": lines,
        "invocation": inv.group("inv") if inv else None,
        "traces_reported": int(inv.group("n")) if inv else None,
        "harness_exit": (inv.group("exit") or "").strip() if inv else None,
        "members": members, "by_test_file": by_file,
        "printed_and_recorded_disagree": disagreements,
        "spool_bytes": dir_bytes(Path(ctx["store"]) / "spool" /
                                 inv.group("inv")) if inv else None,
        "store": store_delta(ctx["store"], before, after),
        "load_guard": guard, "transcript": str(ctx["out"] / "originals.txt"),
    }


# -- the survey check -------------------------------------------------------


def phase_survey_check(ctx, res) -> dict:
    """The locked table, parsed, and every row's test file matched to a
    member of the originals.

    A row whose file is not among the members REFUSES at `exit=4`: the loop's
    population is §1's, and a loop that quietly skipped a row would publish a
    30-row answer under a 31-row gate.
    """
    originals = res.get("originals") or {}
    by_file = originals.get("by_test_file") or {}
    dry = (res.get("preflight") or {}).get("dry_run_rows")
    if dry:
        rows = [dict(r) for r in dry]
        h6 = parse_survey(ctx["survey"].read_text(encoding="utf-8"))["h6"]
        source = "the DRY RUN table derived in preflight"
    else:
        survey = parse_survey(ctx["survey"].read_text(encoding="utf-8"))
        rows, h6 = [dict(r) for r in survey["rows"]], survey["h6"]
        source = str(ctx["survey"].relative_to(REPO_ROOT))
    limit = (res.get("preflight") or {}).get("rows_override")
    if limit:
        rows = rows[:limit]
    missing = []
    for row in rows:
        candidates = by_file.get(row["test_file"]) or []
        row["original"] = candidates[0] if len(candidates) == 1 else None
        row["candidates"] = candidates
        if len(candidates) != 1:
            missing.append({"n": row["n"], "test_file": row["test_file"],
                            "candidates": candidates})
    if missing:
        raise Refused(4, "survey_check: " + ", ".join(
            f"{m['test_file']} ({len(m['candidates'])} member(s))"
            for m in missing))
    return {"rows": rows, "n": len(rows), "h6": h6, "source": source,
            "U": originals.get("U"), "missing": missing}


# -- the loop ---------------------------------------------------------------


def refocus_one(ctx, row, transcript: Path, extra=()) -> dict:
    """One `sensorium refocus <run> --focus <spec>`, timed, with its whole
    transcript saved and parsed.

    The wall is taken around the WHOLE invocation -- launch to verdict -- and
    vitest's own `Duration` is parsed out of the transcript beside it, so
    H9's third number is the difference and is named as that.
    """
    env = plain_env() | {"SENSORIUM_DIR": str(ctx["store"])}
    before = store_snapshot(ctx["store"])
    cmd = [ctx["bin"], "refocus", row["original"], "--focus", row["focus"],
           *extra]
    got = guarded(cmd, REPO_ROOT, env, REFOCUS_TIMEOUT, transcript)
    after = store_snapshot(ctx["store"])
    delta = store_delta(ctx["store"], before, after)
    harness = duration_s(got["text"])
    parsed = parse_refocus(got["text"])
    return {
        "n": row["n"], "test_file": row["test_file"], "klass": row.get("klass"),
        "focus": row["focus"], "original": row["original"],
        "command": got["command"], "exit": got["exit"],
        "wall_s": got["wall_s"], "timed_out": got["timed_out"],
        "harness_duration_s": harness,
        "wall_minus_harness_s": (None if harness is None
                                 else round(got["wall_s"] - harness, 3)),
        "spool_bytes": delta["spool_bytes"], "trace_bytes": delta["trace_bytes"],
        "store_delta": delta,
        "transcript": str(transcript.relative_to(ctx["out"])),
        "parsed": parsed,
    }


def loop_incomplete(exhausted, n) -> str | None:
    """The sentence a loop that did not finish is refused with, or None.

    A `.DONE` over a loop that stopped at row 23 would publish PASS words
    over a population §1 fixes at 31, so the runner turns this into
    `.FAILED exit=5` -- the marker is the first thing a reader looks at, and
    it has to say that the loop is short before any cell is read.
    """
    if not exhausted:
        return None
    return (f"loop: budget exhausted after {n - len(exhausted)} of {n} "
            f"(rows not run: {exhausted[:6]}"
            + (" …" if len(exhausted) > 6 else "") + ")")


def phase_loop(ctx, res) -> dict:
    """The 31 refocuses, in the survey's order, each behind the load guard.

    One deadline for the whole loop (§1's three hours). A row the deadline
    stopped is `not_run` with the bound as its reason; a row that reached its
    own 900 s ceiling is recorded with `timed_out` and its partial text.
    """
    rows = (res.get("survey_check") or {}).get("rows") or []
    started = time.monotonic()
    deadline = started + LOOP_BUDGET_S
    out_rows, exhausted, guards = [], [], []
    for row in rows:
        if time.monotonic() >= deadline:
            exhausted.append(row["n"])
            out_rows.append({"n": row["n"], "test_file": row["test_file"],
                             "klass": row.get("klass"), "focus": row["focus"],
                             "original": row.get("original"),
                             "not_run": "the three-hour loop bound was "
                                        "reached before this refocus"})
            continue
        guard = wait_for_load(ctx["step"])
        guards.append({"n": row["n"], **guard})
        stem = Path(row["test_file"]).stem
        got = refocus_one(ctx, row,
                          ctx["out"] / "transcripts" / f"{row['n']}-{stem}.txt")
        got["load_guard"] = guard
        out_rows.append(got)
        p = got["parsed"]
        ctx["step"](f"loop {row['n']}/{len(rows)} {row['test_file']}: "
                    f"exit={got['exit']} verdict={p['verdict']} "
                    f"licence={p['licence']} wall={got['wall_s']}s")
        res["loop"] = {"rows": out_rows, "n": len(rows),
                       "partial": True}
        ctx["write"](res)
    return {"rows": out_rows, "n": len(rows), "partial": False,
            "budget_exhausted": exhausted, "loop_budget_s": LOOP_BUDGET_S,
            "incomplete": loop_incomplete(exhausted, len(rows)),
            "load_guards": guards,
            "wall_s": round(time.monotonic() - started, 3)}


# -- the two controls -------------------------------------------------------


def phase_controls(ctx, res) -> dict:
    """B: a planted edit on the COPY, refocused. C: `--window 1`, refused.

    B's file is restored FROM THE LENS afterwards and the sha compared, so
    the copy is left as the lens has it and the claim "the lens is never
    written" is measured rather than asserted.
    """
    rows = (res.get("survey_check") or {}).get("rows") or []
    out = {}
    out["B"] = _control_b(ctx, rows)
    out["C"] = _control_c(ctx, rows)
    return out


def _control_b(ctx, rows) -> dict:
    row = next((r for r in rows if r["n"] == 2), None)
    if row is None or not row.get("original"):
        return {"ran": False, "why": "row 2 has no original to refocus"}
    rel = row["test_file"]
    planted = guarded([ctx["python"], str(ctx["accept"] / "plant_edit.py"),
                       str(ctx["copy"]), rel, "e15-planted"],
                      REPO_ROOT, plain_env(), 120,
                      ctx["out"] / "control-b-plant.txt")
    if planted["exit"] != 0:
        return {"ran": False, "why": f"plant_edit exited {planted['exit']}",
                "plant": planted["text"][-400:]}
    guard = wait_for_load(ctx["step"])
    got = refocus_one(ctx, row, ctx["out"] / "control-b.txt")
    # Restored from the LENS, which is the only copy this run treats as
    # authoritative, and the sha compared both ways.
    source, target = ctx["lens_dir"] / rel, ctx["copy"] / rel
    shutil.copyfile(source, target)
    lens_sha, copy_sha = sha256_file(source), sha256_file(target)
    return {"ran": True, "row": row["n"], "test_file": rel,
            "plant": json.loads(planted["out"]) if planted["out"] else None,
            "restored": True, "lens_sha256": lens_sha,
            "copy_sha256": copy_sha, "sha_equal": lens_sha == copy_sha,
            "load_guard": guard,
            **{k: got[k] for k in
               ("command", "exit", "wall_s", "timed_out",
                "harness_duration_s", "wall_minus_harness_s", "transcript",
                "parsed")}}


def _control_c(ctx, rows) -> dict:
    """§1's control C: `refocus <row 3's original> --window 1`.

    Run TWICE, and the second is the one H8 reads. `--focus` is a REQUIRED
    argument of `sensorium refocus`, so §1's shorthand -- `refocus <member>
    --window 1` -- is refused by argparse with a usage line before design
    §2.3's refusal 1 can run; that literal form is run first and kept under
    `as_written`, and the form carrying the row's own focus spec is what
    reaches the refusal the endpoint is about. Both exits and both texts are
    recorded, so §3 states the gap rather than a reader inferring it.
    """
    row = next((r for r in rows if r["n"] == 3), None)
    if row is None or not row.get("original"):
        return {"ran": False, "why": "row 3 has no original to refocus"}
    traces = Path(ctx["store"]) / "traces"
    env = plain_env() | {"SENSORIUM_DIR": str(ctx["store"])}
    before = len(list(traces.glob("*.db"))) if traces.is_dir() else 0
    literal = guarded([ctx["bin"], "refocus", row["original"],
                       "--window", "1"], REPO_ROOT, env, READER_TIMEOUT,
                      ctx["out"] / "control-c-as-written.txt")
    # Counted BETWEEN the two invocations, so each cell reads its OWN pair:
    # H8 the literal form's `before -> between`, H8' the `--focus` form's
    # `between -> after`. One span covering both would let either run move
    # the store without the other's cell seeing it.
    between = len(list(traces.glob("*.db"))) if traces.is_dir() else 0
    got = guarded([ctx["bin"], "refocus", row["original"],
                   "--focus", row["focus"], "--window", "1"],
                  REPO_ROOT, env, READER_TIMEOUT,
                  ctx["out"] / "control-c.txt")
    after = len(list(traces.glob("*.db"))) if traces.is_dir() else 0
    return {"ran": True, "row": row["n"], "test_file": row["test_file"],
            "command": got["command"], "exit": got["exit"],
            "wall_s": got["wall_s"], "stderr": got["err"].strip(),
            "traces_before": before, "traces_between": between,
            "traces_after": after,
            "transcript": "control-c.txt",
            "as_written": {"command": literal["command"],
                           "exit": literal["exit"],
                           "stderr": literal["err"].strip(),
                           "transcript": "control-c-as-written.txt",
                           "parsed": parse_refocus(literal["text"])},
            "parsed": parse_refocus(got["text"])}


# -- the fences -------------------------------------------------------------

#: What the needle is searched OVER: the transcripts this run's own
#: `sensorium` commands produced, and nothing else. Deliberately not every
#: `*.txt` under the out directory -- the fence logs hold a whole pytest run
#: and the corpus's own `expect_absent` lines, which quote this very string,
#: and a needle that hit one of those would report the corpus asserting the
#: rule as the rule being broken.
NEEDLE_GLOBS = ("originals.txt", "transcripts/*.txt", "control-b.txt",
                "control-c.txt", "control-c-as-written.txt", "reads/*.txt")


def needle(ctx) -> dict:
    """§1's E7 needle over every transcript this run produced."""
    searched, hits = [], []
    for pattern in NEEDLE_GLOBS:
        for path in sorted(Path(ctx["out"]).glob(pattern)):
            searched.append(str(path.relative_to(ctx["out"])))
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if NEEDLE in text:
                hits.append(str(path.relative_to(ctx["out"])))
    return {"needle": NEEDLE, "globs": list(NEEDLE_GLOBS),
            "searched": len(searched), "searched_files": searched,
            "hits": hits}


def fence_commands(ctx) -> list[dict]:
    """§1's H10 list, each with the command as it is run.

    `npm --prefix typescript run check` and not `npx tsc -p typescript/
    tsconfig.json`: the repo root has no `node_modules`, and CI's own R4 says
    the type-check runs from inside `typescript/` where `tsc` resolves the
    pinned local install.
    """
    # `e12_h8.sh:82` runs the probes with a spool and a manifest directory of
    # their own and `SENSORIUM_TIER=call`; `plain_env()` strips every
    # `SENSORIUM_*`, so the three are put back here and nowhere else, under
    # this run's own out directory.
    probe_spool = ctx["out"] / "fences" / "probe-spool"
    probe_manifests = ctx["out"] / "fences" / "probe-manifests"
    probe_spool.mkdir(parents=True, exist_ok=True)
    probe_manifests.mkdir(parents=True, exist_ok=True)
    return [
        {"name": "corpus",
         "cmd": [ctx["python"], "corpus/run_corpus.py", "--require-driver"],
         "cwd": REPO_ROOT, "env": plain_env()},
        {"name": "pytest",
         "cmd": [ctx["python"], "-m", "pytest", "-q", "-p", "no:cacheprovider"],
         "cwd": REPO_ROOT, "env": plain_env()},
        {"name": "cargo test --workspace",
         "cmd": ["cargo", "test", "--workspace"], "cwd": REPO_ROOT / "rust",
         "env": plain_env() | ({"CARGO_TARGET_DIR": ctx["cargo_target"]}
                               if ctx["cargo_target"] else {})},
        {"name": "npm --prefix typescript test",
         "cmd": ["npm", "--prefix", "typescript", "test"], "cwd": REPO_ROOT,
         "env": plain_env()},
        {"name": "tsc", "cmd": ["npm", "--prefix", "typescript", "run",
                                "check"], "cwd": REPO_ROOT,
         "env": plain_env()},
        # §1 H10's "the probes": the recorder's own probe project, which
        # records ITSELF under vitest and reads the spools back
        # (`typescript/probes/check.mjs`). Run exactly as `e12_h8.sh:82`
        # runs it.
        {"name": "npm-probes",
         "cmd": ["npm", "--prefix", "typescript/probes", "run", "probe"],
         "cwd": REPO_ROOT,
         "env": plain_env() | {"SENSORIUM_SPOOL": str(probe_spool),
                               "SENSORIUM_MANIFEST_DIR": str(probe_manifests),
                               "SENSORIUM_TIER": "call"}},
        {"name": "ceiling",
         "cmd": [ctx["python"], "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 "tests/test_ceiling.py"], "cwd": REPO_ROOT,
         "env": plain_env()},
    ]


def phase_fences(ctx, res) -> dict:
    """§1's H10: the two fences, the corpus, the suites, and the needle."""
    out_dir = ctx["out"] / "fences"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = ctx["fence_base"]
    fences_env = plain_env() | {
        "E_FENCES_RECORDER": ctx["recorder"], "E_FENCES_REV": ctx["head"]}
    ef = guarded([ctx["python"], "typescript/acceptance/e_fences.py", base,
                  str(out_dir)], REPO_ROOT, fences_env, FENCE_TIMEOUT,
                 ctx["out"] / "e-fences.txt")
    cells = {}
    for name, filename in (("E-legacy", "e-legacy.json"),
                           ("E-branch", "e-branch.json")):
        path = out_dir / filename
        try:
            cells[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            cells[name] = {"_absent": f"{filename}: {e}"}
    checks = []
    for spec in fence_commands(ctx):
        ctx["step"](f"fence: {spec['name']}")
        got = guarded(spec["cmd"], spec["cwd"], spec["env"], FENCE_TIMEOUT,
                      out_dir / (spec["name"].replace(" ", "-") + ".txt"))
        tail = [ln for ln in got["text"].splitlines() if ln.strip()]
        checks.append({"name": spec["name"], "command": got["command"],
                       "cwd": got["cwd"], "exit": got["exit"],
                       "wall_s": got["wall_s"], "timed_out": got["timed_out"],
                       "last_line": tail[-1] if tail else ""})
        res["fences"] = {"checks": checks, "partial": True}
        ctx["write"](res)
    return {"checks": checks, "e_fences": cells, "fence_base": base,
            "e_fences_run": {k: v for k, v in ef.items()
                             if k not in ("out", "err", "text")},
            "needle": needle(ctx), "partial": False}


# -- the four reads ---------------------------------------------------------


def phase_reads(ctx, res) -> dict:
    """§1's H6: the four commands the survey's `### H6 reads` block names, on
    the NEW traces rows 1, 16 and 31's refocuses produced."""
    h6 = (res.get("survey_check") or {}).get("h6") or []
    rows = (res.get("loop") or {}).get("rows") or []
    trace_of_row = {}
    for row in rows:
        pair = ((row.get("parsed") or {}).get("pair") or {})
        if pair.get("run"):
            trace_of_row[row["n"]] = pair["run"]
    env = plain_env() | {"SENSORIUM_DIR": str(ctx["store"])}
    out = []
    for i, read in enumerate(h6, start=1):
        record = {k: read[k] for k in ("label", "row", "kind", "command",
                                       "predicted_class", "predicted_exit")}
        if read["row"] not in trace_of_row:
            record["not_run"] = (f"row {read['row']} produced no refocused "
                                 "trace in this run")
            out.append(record)
            continue
        argv = h6_argv(read["command"], trace_of_row)
        transcript = ctx["out"] / "reads" / f"{i}-{read['kind']}.txt"
        got = guarded([ctx["bin"], *argv], REPO_ROOT, env, READER_TIMEOUT,
                      transcript)
        parse = parse_watch if read["kind"] == "watch" else parse_flow
        record.update({"trace": trace_of_row[read["row"]],
                       "argv": argv, "resolved_command": got["command"],
                       "exit": got["exit"], "wall_s": got["wall_s"],
                       "timed_out": got["timed_out"],
                       "transcript": str(transcript.relative_to(ctx["out"])),
                       "parsed": parse(got["text"])})
        ctx["step"](f"read {i}/{len(h6)} {read['label']}: exit={got['exit']} "
                    f"verdict={record['parsed']['verdict']}")
        out.append(record)
    # The needle again, now that the reads have written their own
    # transcripts: `fences` runs before `reads` (§1's order), so the reading
    # it took could not have covered them. H10 reads
    # `fences.needle`, so this replaces it rather than publishing a second
    # number about one question.
    recomputed = needle(ctx)
    if isinstance(res.get("fences"), dict):
        res["fences"]["needle"] = recomputed
        res["fences"]["needle_recomputed_after_the_reads"] = True
    return {"reads": out, "n": len(out), "needle": recomputed}
