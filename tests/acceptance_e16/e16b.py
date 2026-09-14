#!/usr/bin/env python3
"""E16 part B: the three probes, the phases and the three cells.

Launched detached by `e16b.sh`, which passes every location in the
environment so that no path on one box is written into a file that travels
with the repository. What this measures is fixed by the record's §1 -- spec
§9, plan A's block, and the dated amendment that pre-registers part B -- and
narrowed to part B by it: **H1 restricted to VALUES**, **H5 in full**, **H6
restricted to `redaction.values`**. H1-env, H2, H3 and H6-env were part A's
and H4 is part C's; each is written into the results file as `dropped` with
the part that owns it, never as a number and never as PASS.

WHAT IS RECORDED, AND WHY THESE PROBES
--------------------------------------
Three programs under `probes/`, one per recorder, each planting the token in
the places §1's amendment counts: a `secret()` that reads it out of the
environment, a focused `handle` that binds it to a local, puts it in a
header value under `authorization`, and (Python only) prints it alone. Two
of the bindings in the Rust and TypeScript probes -- `copy` and `headers` --
are names rule v1 does NOT fire on, so the only thing that can reach them is
the CONTENT rule; that is why the token is minted as `sk-e16-` plus 33
characters, inside the `sk-` pattern, and why a dry run's `dry-` decoy
exercises the NAME rows alone.

THE ENVIRONMENT EVERY RECORDING RUNS UNDER
------------------------------------------
Part A's `ALLOWLIST` and nothing else, with the token added -- `env -i` with
the allowlist put back, so `redaction.env` holding exactly one name is a
fact about the rule and not about whichever terminal started the run. The
two BENCH runs are the exception and deliberately so: they run with a
placeholder in the token's variable, because H5 writes into trees H1 does
not sweep and a secret in one of those is a secret nobody checked.

WHAT A PHASE MAY WRITE INTO THE RESULTS FILE
--------------------------------------------
`None`, or a measurement. Never a default. `build-driver`, `preflight` and
`baseline` are PRECONDITIONS (`CRITICAL_PHASES`): each ends the run rather
than dropping a cell, because a run that recorded with a stale binary, or
compared against a baseline tree that was never built, produces output that
looks exactly like a finding.

WHY THE SWEEPS RUN IN THIS ORDER
--------------------------------
`info` and `versions` open traces, and a read-only sqlite connection cannot
checkpoint a WAL -- so both run BEFORE the grep sweep, which part A learned
in its own dry run. The two bench tables run LAST: they are the longest
phases by far, and the sweep's answer should be in hand before the part's
clock is spent.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Part A's runner, imported whole: the scrubbed environment, the timed
# phase, the R37 driver rebuild, the token mint, the transcript keeper and
# the subprocess runner are one instrument's machinery used by two parts,
# and `e16a.py` is a measured record's instrument -- read, never edited.
from e16a import (RUN_LINE, Part, _driver_versions,  # noqa: E402,F401
                  _installed_version, _parse_info, _rel, _run, _sha8,
                  dry_run_findings)
# The decision layer, split out at this file's 800-line ceiling and
# re-exported whole, exactly as part A's is.
from e16b_cells import (AMENDMENTS, ARMS, BASELINE,  # noqa: E402,F401
                        BENCH_REPS, BENCH_ROW, CELL_TITLES, DROPPED,
                        DRY_BENCH_REPS, DRY_TIMERS, EXPECTED,
                        EXPECTED_VALUES, DRY_NAME_ROWS, FOCUS, PROBES,
                        RULE_OF, RULES, SPOOL_OCCURRENCES, TIMERS, TOKEN_VAR,
                        TS_OMITTED_CASE, TS_PROBE_DIR, Refused,
                        cell_h1_values, cell_h5, cell_h6_values, parse_bench,
                        part_word, read_driver_build)

#: The phases that are PRECONDITIONS rather than measurements, and whose
#: failure therefore ends the run instead of dropping one cell. Part A's two
#: plus `baseline`: H5's whole claim is a comparison against `7dd25d2`, and
#: a baseline worktree that half-built would leave the HEAD table reading as
#: a measurement of nothing in particular.
#: `tests/test_acceptance_e16_phase.py` holds this list against `main`'s own
#: call sites.
CRITICAL_PHASES = ("build-driver", "preflight", "baseline")

#: §1's amendment's H5 command, verbatim, with the reps the run uses.
BENCH_CODE = "from corpus._bench import bench; bench.report(reps={reps})"

#: `info_cmd.redaction_line`: `; values redacted: <n>` rides both forms the
#: rule ran under, and only when the recorder actually counted. Absent means
#: a recording made before the count existed -- `None`, never a zero nobody
#: measured.
_VALUES = re.compile(r"values redacted: (\d+)")


class PartB(Part):
    """One part-B measurement: part A's locations, plus H5's two trees."""

    def __init__(self, work: Path, out: Path, node_bin: str, driver_dir: str,
                 dry: bool, label: str):
        super().__init__(work, out, node_bin, driver_dir, dry, label)
        self.timers = DRY_TIMERS if dry else TIMERS
        self.reps = DRY_BENCH_REPS if dry else BENCH_REPS
        #: H5's two trees. The baseline worktree is §1's amendment's own
        #: path; the scratch store is where both `bench.report` runs point
        #: `SENSORIUM_DIR`, so that neither can write into the store H1
        #: sweeps.
        self.baseline = work / f"baseline-{BASELINE}"
        self.bench_dir = work / f"bench-{label}"
        self.uv = shutil.which("uv") or ""

    # -- phase 1: what has to be true before anything is recorded ----------
    def preflight(self) -> dict:
        """Part A's preflight -- the allowlist census, the store's absence,
        the two binaries, an installed vitest -- and what part B adds: the
        three probes are on disk, `uv` is findable, the baseline commit
        resolves, and the baseline worktree is not already there."""
        base = super().preflight()
        probes = REPO / "tests" / "acceptance_e16" / "probes"
        missing = [f"{arm}/{name}" for arm, names in PROBES.items()
                   for name in names if not (probes / arm / name).is_file()]
        if missing:
            raise Refused(f"probe source(s) missing under {probes}: "
                          + ", ".join(missing))
        if not self.uv:
            raise Refused("no `uv` on the launching PATH: the baseline "
                          "worktree's interpreter and install need it")
        if self.baseline.exists():
            raise Refused(f"{self.baseline} already exists: H5's baseline "
                          "tree is built once, from zero")
        r = _run(["git", "-C", str(REPO), "rev-parse", f"{BASELINE}^{{commit}}"],
                 self.work, self.env("preflight-not-a-token"), 120)
        if r["rc"] != 0:
            raise Refused(f"{BASELINE} does not resolve in {REPO}: "
                          f"{r['out'].strip()[:200]}")
        base.update(probes=sorted(f"{a}/{n}" for a, ns in PROBES.items()
                                  for n in ns),
                    baseline_commit=r["out"].strip().splitlines()[-1],
                    bench_reps=self.reps)
        return base

    # -- phase 2: H5's baseline tree ---------------------------------------
    def build_baseline(self) -> dict:
        """A worktree at `7dd25d2` with its own 3.13 virtual environment and
        this package installed into it.

        A PRECONDITION, not a measurement: H5 is a comparison, and a
        comparison against a tree that half-built is not a smaller reading,
        it is a different claim. Every step's failure is a refusal naming
        the command, and the worktree is refused outright if the path is
        already there -- a stale tree from an earlier attempt would be at
        whatever commit that attempt used.
        """
        if self.baseline.exists():
            raise Refused(f"{self.baseline} already exists")
        env = self.env("baseline-not-a-token")
        steps = [("worktree", ["git", "-C", str(REPO), "worktree", "add",
                               str(self.baseline), BASELINE]),
                 ("venv", [self.uv, "venv", "-p", "3.13",
                           str(self.baseline / ".venv")]),
                 ("install", [self.uv, "pip", "install", "-p",
                              str(self.baseline / ".venv" / "bin" / "python"),
                              "-e", f"{self.baseline}[dev]"])]
        seconds = {}
        for name, argv in steps:
            r = _run(argv, self.work, env, self.timers["baseline"])
            self._keep(f"baseline-{name}", r)
            if r["killed"] or r["rc"] != 0:
                raise Refused(f"the baseline {name} step exited {r['rc']} "
                              f"(killed: {r['killed']}): H5 has no tree to "
                              "compare against")
            seconds[name] = r["seconds"]
        python = self.baseline / ".venv" / "bin" / "python"
        if not os.access(python, os.X_OK):
            raise Refused(f"no interpreter at {python} after the venv step")
        version = _run([str(python), "--version"], self.baseline, env, 60)
        return {"built": True, "commit": BASELINE,
                "path": f"$E16_DIR/{self.baseline.name}",
                "python": f"$E16_DIR/{self.baseline.name}/.venv/bin/python",
                "python_version": version["out"].strip() or None,
                "seconds": seconds}

    # -- phase 4: the three copies -----------------------------------------
    def copies(self) -> dict:
        """The disposable copies each arm records in.

        The TypeScript one is a copy of `corpus/typescript` for its config
        and its installed `node_modules`, with the probe put in a
        SUBDIRECTORY (the project's `vitest.config.ts` includes
        `*/**/*.test.ts`, which a file at the root does not match) and the
        corpus's own `secret_in_env` case left out (`vitest run secret` is a
        substring filter over test-file paths, and it matches that case as
        surely as the probe). Both are stated in `AMENDMENTS`, and the
        second is CHECKED below rather than trusted: the filter has to
        select the probe and nothing else, or this run's TypeScript census
        would be about two programs.
        """
        probes = REPO / "tests" / "acceptance_e16" / "probes"
        ignore = shutil.ignore_patterns("__pycache__", "target", "Cargo.lock",
                                        ".sensorium")
        shutil.copytree(probes / "python", self.py_case, ignore=ignore)
        shutil.copytree(probes / "rust", self.rust_crate, ignore=ignore)
        ts = REPO / "corpus" / "typescript"
        shutil.copytree(ts, self.ts_project, ignore=shutil.ignore_patterns(
            "__pycache__", "node_modules", ".sensorium", "run_count.txt",
            TS_OMITTED_CASE))
        (self.ts_project / "node_modules").symlink_to(
            ts / "node_modules", target_is_directory=True)
        probe_dir = self.ts_project / TS_PROBE_DIR
        probe_dir.mkdir()
        for name in PROBES["typescript"]:
            shutil.copy(probes / "typescript" / name, probe_dir / name)
        selected = self._vitest_filter_selects()
        want = [f"{TS_PROBE_DIR}/secret.test.ts"]
        if selected != want:
            raise Refused("`vitest run secret` would select "
                          f"{selected}, not {want}: the TypeScript census "
                          "would be about more than the probe")
        self.transcripts.mkdir(parents=True, exist_ok=True)
        return {"python": self.py_case.name, "rust": self.rust_crate.name,
                "typescript": self.ts_project.name,
                "typescript_probe": TS_PROBE_DIR,
                "typescript_omitted": TS_OMITTED_CASE,
                "vitest_selects": selected}

    def _vitest_filter_selects(self) -> list[str]:
        """Every test file in the copy whose path carries `secret` -- which
        is what vitest's positional filter matches on. `find`, so the
        `node_modules` symlink is not walked."""
        r = subprocess.run(["find", str(self.ts_project), "-name",
                            "*.test.ts", "-type", "f"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise Refused(f"find over the vitest copy exited {r.returncode}")
        rel = sorted(str(Path(p).relative_to(self.ts_project))
                     for p in r.stdout.splitlines() if p)
        return [p for p in rel if "secret" in p]

    # -- phases 5-7: the three recordings ----------------------------------
    def record_python(self):
        """R11: `--focus main:handle`, not §1's bare `--focus handle`. A
        bare entry names a MODULE, so `handle` would focus nothing and the
        recording would carry none of the three LINE deltas §1 counts."""
        self.runs["python"] = self._record(
            "python", [self.python, "-m", "sensorium", "run",
                       "--focus", FOCUS["python"], "--", "main.py"],
            self.py_case, "record")

    def record_rust(self):
        self.runs["rust"] = self._record(
            "rust", [self.driver, "sensorium", "--focus", FOCUS["rust"],
                     "run"], self.rust_crate, "record_rust")

    def record_typescript(self):
        self.runs["typescript"] = self._record(
            "typescript", [self.python, "-m", "sensorium", "ts", "run",
                           "--focus", FOCUS["typescript"], "--", "npx",
                           "vitest", "run", "secret"],
            self.ts_project, "record")

    # -- phase 8: `info` on the three traces -------------------------------
    def info(self) -> list[dict]:
        """The census, per trace: how many values the rule took, which
        names it took in the environment, and which recorder wrote it.

        `values` is `None` when the redaction line carried no count --
        never a zero, which would read as a measured "the rule took
        nothing"."""
        rows = []
        for arm in ARMS:
            for run in self.runs.get(arm, []):
                r = _run([self.python, "-m", "sensorium", "info", run],
                         self.work, self.env(self.token), 300)
                self._keep(f"info-{arm}-{run}", r)
                row = _parse_info(r["out"])
                m = _VALUES.search(r["out"])
                row.update(run=run, arm=arm, exit=r["rc"],
                           values=int(m.group(1)) if m else None)
                rows.append(row)
        return rows

    # -- phase 10: the grep sweep, as OCCURRENCES --------------------------
    def grep_values(self) -> dict:
        """§1's amendment's four readings, and everything else this run
        made, swept for the token's bytes.

        Part A's stores are NOT read -- the amendment says so -- so the
        sweep is over this run's own trees: the store, the Rust spool tree,
        the three disposable copies, the transcripts and the cargo target
        directory. Counted as OCCURRENCES (`grep -a -o -F | wc -l` per
        file), because "exactly 3" is a claim about how many times the value
        is present and the three rows the converter redacts can share a
        line.
        """
        store = _files_under(self.store)
        spool_root = self.target / "sensorium" / "spool"
        rust = _files_under(spool_root)
        ts_root = self.store / "spool"
        counted = set(store) | set(rust)
        # Wider than the four readings, in the only direction that can find
        # a leak: the three disposable copies, the transcripts, the cargo
        # build tree, the TMPDIR every recording ran under and this
        # instrument's own output. Not the baseline worktree and not the
        # bench scratch store -- the token was never in the environment
        # either was run under, which is what the prose says and what makes
        # not sweeping them honest rather than convenient. (The bench
        # directories do not exist yet at this point either: H5 runs last.)
        other = [p for root in (self.py_case, self.rust_crate,
                                self.ts_project, self.transcripts,
                                self.target, self.work / "tmp", self.out)
                 for p in _files_under(root) if p not in counted]
        sets = {
            "store": store,
            "headers": [p for p in rust if p.name.endswith(".proc.json")],
            "spools": [p for p in rust if p.suffix == ".spool"],
            "ts_spools": [p for p in store
                          if _under(p, ts_root)],
            "other": sorted(set(other)),
        }
        out = {key: _grep_occurrences(self.token, paths, self.work)
               for key, paths in sets.items()}
        out["roots"] = {"store": _rel(self.store, self.work),
                        "rust_spool": _rel(spool_root, self.work),
                        "ts_spool": _rel(ts_root, self.work)}
        return out

    # -- phases 11-12: H5, one table per tree ------------------------------
    def bench(self, label: str, tree: Path, python: str) -> dict:
        """One `bench.report` table, in one tree, against a scratch store.

        The token is NOT in this environment: H5's trees are not swept by
        H1, and the only honest way to say nothing leaked into them is for
        nothing to have been there. A killed or failing run leaves
        `text: None`, which drops H5 -- overhead is never gated, so a
        missing table costs a reading and nothing else.
        """
        sdir = self.bench_dir / label
        sdir.mkdir(parents=True, exist_ok=True)
        env = {**self.env("bench-not-a-token"), "SENSORIUM_DIR": str(sdir)}
        r = _run([python, "-c", BENCH_CODE.format(reps=self.reps)],
                 tree, env, self.timers["bench"])
        self._keep(f"bench-{label}", r)
        ok = not r["killed"] and r["rc"] == 0
        return {"text": r["out"] if ok else None, "rc": r["rc"],
                "killed": r["killed"], "seconds": r["seconds"],
                "reps": self.reps, "tree": label,
                "why": None if ok else f"exit {r['rc']}, killed {r['killed']}"}


# -- reading the box -------------------------------------------------------
def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _files_under(root: Path) -> list[Path]:
    """Every regular file under `root`, symlinked directories not walked.

    `find`, like part A's `grep -r`: the vitest project's `node_modules` is
    a SYMLINK to the checkout's installed tree, and walking it would sweep
    hundreds of megabytes no recorder wrote. A root that is not there is a
    refusal rather than an empty list -- the cells drop on an empty set, but
    a missing tree is a fact about this instrument's paths and the run
    should end on it.
    """
    if not root.exists():
        raise Refused(f"nothing to sweep at {root}")
    r = subprocess.run(["find", str(root), "-type", "f"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise Refused(f"find over {root} exited {r.returncode}: "
                      f"{r.stderr.strip()[:200]}")
    return sorted(Path(p) for p in r.stdout.splitlines() if p)


def _grep_occurrences(needle: str, paths: list[Path],
                      work: Path) -> list[dict]:
    """`grep -a -o -F <needle> <file> | wc -l`, per file -- §1's
    amendment's own method.

    OCCURRENCES, not lines: part A counted lines with `grep -rc`, which is
    the right reading for "this file must hold none" and the wrong one for
    "these files hold exactly three". Exit 1 is "no match", which is the
    passing case; anything else leaves `None` in the row and drops the cell
    naming the file.
    """
    rows = []
    for path in paths:
        r = subprocess.run(["grep", "-a", "-o", "-F", "-e", needle, "--",
                            str(path)], capture_output=True, text=True)
        rows.append({"path": _rel(path, work),
                     "occurrences": (len(r.stdout.splitlines())
                                     if r.returncode in (0, 1) else None),
                     "grep_exit": r.returncode})
    return rows


def dry_census(rows: list[dict] | None) -> dict:
    """What a DRY run's census read, against the NAME rows alone.

    Reported, never gated: the decoy is `dry-` plus four characters, which
    no content pattern matches, so a dry run can only fire the name rows --
    Python 4, TypeScript 2, Rust 2. A run that reads those is the plumbing
    working; a run that reads anything else is a FINDING about the probes or
    the rules, and it belongs in the dry run's own report rather than in a
    cell about a different string.
    """
    if not rows:
        return {"word": "dropped", "why": "no trace was read"}
    read = {row["arm"]: row["values"] for row in rows}
    as_predicted = read == DRY_NAME_ROWS
    return {"word": "measured", "read": read, "predicted": DRY_NAME_ROWS,
            "as_predicted": as_predicted,
            "why": ("the name rows fired as predicted: "
                    if as_predicted else "NOT as predicted -- read ")
            + ", ".join(f"{arm} {read.get(arm)}" for arm in ARMS)
            + f" against {DRY_NAME_ROWS}"}


# -- the run ---------------------------------------------------------------
def main() -> int:
    work = Path(os.environ["E16_WORK"]).resolve()
    out = Path(os.environ["E16_OUT"]).resolve()
    part = PartB(work, out, os.environ["E16_NODE_BIN"],
                 os.environ["E16_DRIVER_DIR"],
                 dry=os.environ.get("E16_DRY") == "1",
                 label=os.environ["E16_LABEL"])
    result = {"dry_run": part.dry, "started": time.time(),
              "dry_run_findings": dry_run_findings(),
              "amendments": list(AMENDMENTS)}
    # Bound to the result up front, so a phase that ends the run late still
    # leaves every cell decided before it in the raw record.
    cells: dict = {}
    result["cells"] = cells
    try:
        result["driver_build"] = part.phase("build-driver",
                                            part.build_driver, critical=True)
        result["preflight"] = part.phase("preflight", part.preflight,
                                         critical=True)
        result["baseline"] = part.phase("baseline", part.build_baseline,
                                        critical=True)
        result["token"] = part.phase("mint", part.mint)
        result["copies"] = part.phase("copies", part.copies)
        part.phase("record-python", part.record_python)
        part.phase("record-rust", part.record_rust)
        part.phase("record-typescript", part.record_typescript)
        info = part.phase("info", part.info)
        result["versions"] = part.phase("versions", lambda: {
            "expected": EXPECTED,
            "recorder": {row["arm"]: row["recorder"] for row in (info or [])},
            "driver_version": _driver_versions(part.store, part.runs),
            "sensorium": _installed_version(),
            "tools": result["preflight"]["tools"]})
        sweep = part.phase("grep-values", part.grep_values)
        result["runs"] = part.runs
        result["h1_values"] = sweep
        result["h6_values"] = [{"run": r["run"], "arm": r["arm"],
                                "values": r["values"], "names": r["names"],
                                "vars": r["vars"]} for r in (info or [])]
        read = ["store", "headers", "spools", "ts_spools"]
        cells["H1-values"] = cell_h1_values(
            *[(sweep or {}).get(key) for key in read])
        cells["H6-values"] = cell_h6_values(result["h6_values"])
        base = part.phase("bench-baseline", lambda: part.bench(
            BASELINE, part.baseline, str(part.baseline / ".venv" / "bin"
                                         / "python")))
        head = part.phase("bench-head",
                          lambda: part.bench("head", REPO, part.python))
        result["bench"] = {"baseline": base, "head": head}
        cells["H5"] = cell_h5((base or {}).get("text"),
                              (head or {}).get("text"))
        # The cells in §9's order, whatever order they were decided in.
        result["cells"] = {c: cells[c] for c in CELL_TITLES if c in cells}
        result["dropped"] = [{"cell": c, "reason": why, "word": "dropped"}
                             for c, why in DROPPED]
        result["part"] = part_word(result["cells"])
        if part.dry:
            result["dry_census"] = dry_census(result["h6_values"])
        result["status"] = "complete"
    except Refused as exc:
        result["status"] = "refused"
        result["refusal"] = str(exc)
    result["phases"] = part.phases
    result["finished"] = time.time()
    result["seconds"] = round(result["finished"] - result["started"], 1)
    result["label"] = part.label
    result["lens"] = {"work_root": str(work), "store": str(part.store),
                      "transcripts": str(part.transcripts),
                      "rust_crate": str(part.rust_crate),
                      "python_case": str(part.py_case),
                      "ts_project": str(part.ts_project),
                      "cargo_target": str(part.target),
                      "baseline": str(part.baseline),
                      "bench": str(part.bench_dir),
                      "repo": str(REPO), "out": str(out)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "results-b.json").write_text(json.dumps(result, indent=2,
                                                   sort_keys=True) + "\n")
    ok = result["status"] == "complete"
    (out / ("e16b.DONE" if ok else "e16b.FAILED")).write_text(
        result.get("part", result.get("refusal", "?")) + "\n")
    print(("done: " + result["part"]) if ok
          else ("FAILED: " + result["refusal"]), flush=True)
    if part.dry and result.get("dry_census"):
        print("dry census: " + result["dry_census"]["why"], flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
