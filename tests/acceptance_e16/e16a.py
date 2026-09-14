#!/usr/bin/env python3
"""E16 part A: the phases, the readers and the four cells.

Launched detached by `e16a.sh`, which passes every location in the
environment so that no path on one box is written into a file that travels
with the repository. What this measures is fixed by the record's §1
(`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md`) and
narrowed to part A by the plan's pre-registration block: H1 restricted to
the ENVIRONMENT, H2 in full, H3 in full, H6 restricted to `redaction.env`.
H1-values, H4, H5 and H6-values belong to parts B and C and are written into
the results file as `dropped` with the part that owns them -- never as a
number, and never as PASS.

THE ENVIRONMENT EVERY RECORDING RUNS UNDER
------------------------------------------
`ALLOWLIST` and nothing else, with the token added. Every subprocess below
is given a complete `env` dict rather than an overlay, which is `env -i`
with the allowlist put back: the launching shell's own secrets never reach a
recorder, so `redaction.env` holding exactly one name is a fact about the
rule and not a fact about whichever terminal started the run. `preflight`
re-checks the second half of that -- that no allowlisted name FIRES rule v1
-- rather than trusting the claim, because "exactly one name" is only true
by construction while that holds.

THE TOKEN
---------
`sk-e16-` plus 33 characters, minted here into `<work>/token` at 0600,
exported, and never printed: no phase logs it, the transcripts hold variable
NAMES only, and the results file cites `sha256(token)[:8]`. H3 needs a
SECOND value (the pre-registered "re-exported to a fresh value"), minted the
same way and kept out of the record the same way. A dry run plants `dry-`
plus four characters instead -- a string that cannot match the content rule
part B will measure -- caps every timer at a minute, and stamps
`dry_run: true`, which `assemble_e16a` refuses.

WHAT A PHASE MAY WRITE INTO THE RESULTS FILE
--------------------------------------------
`None`, or a measurement. Never a default. A phase that was killed, a file
that could not be stat'ed, a transcript that did not parse: each leaves
`None` in the row it owns, and every cell below turns a `None` anywhere in
its input into `dropped`. The one thing this instrument must not be able to
do is report a hole as a pass.

WHY THE SWEEPS RUN IN THIS ORDER
--------------------------------
Modes are read straight after the three recordings and before any query, so
what is measured is what the RECORDERS left: a reader that opens a WAL
database creates `-shm`/`-wal` beside it, and those would be files the runs
did not make. The grep sweep runs LAST, over everything, so it also covers
the traces `refocus` wrote and the transcripts the instrument kept -- a
wider check than §1's, in the only direction that can find a leak.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The decision layer, split out at this file's 800-line ceiling and
# re-exported whole: `e16a.cell_h1` and `assemble_e16a`'s imports mean
# what they meant before the split, and one module still owns every
# verdict word.
from e16a_cells import (ALLOWLIST, ARMS, DROPPED,  # noqa: E402,F401
                        DRY_BODY, DRY_PREFIX, DRY_TIMERS, EXPECTED, FOCUS,
                        GATED_ROOTS, PREDICTIONS, RULES, TIMERS, TOKEN_BODY,
                        TOKEN_PREFIX, TOKEN_VAR, _ALPHABET, Refused,
                        cell_h1, cell_h2, cell_h3, cell_h6, part_word,
                        read_pair)


# -- running things --------------------------------------------------------
def _run(argv, cwd, env, timeout, capture=True) -> dict:
    """One subprocess, in its own session, killed BY GROUP on the timer.

    `start_new_session` plus `killpg`: a `cargo` or `npx` that hangs has
    children, and killing the leader alone leaves them holding the cores.
    A kill leaves `rc: None` and `killed: true`, which every reader below
    treats as a hole rather than as a failure of the thing measured.
    """
    started = time.time()
    proc = subprocess.Popen(
        [str(a) for a in argv], cwd=str(cwd), env=env,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True, start_new_session=True)
    killed = False
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        killed = True
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = proc.communicate()
    return {"argv": [str(a) for a in argv], "cwd": str(cwd),
            "rc": None if killed else proc.returncode, "killed": killed,
            "out": out or "", "seconds": round(time.time() - started, 3)}


RUN_LINE = re.compile(r"^run: (\d{8}-\d{6}-[0-9a-f]{6})(?:$|  )", re.M)


class Part:
    """One part-A measurement: its locations, its token, its phases."""

    def __init__(self, work: Path, out: Path, node_bin: str, driver_dir: str,
                 dry: bool):
        self.work, self.out = work, out
        self.node_bin, self.driver_dir, self.dry = node_bin, driver_dir, dry
        self.timers = DRY_TIMERS if dry else TIMERS
        self.store = work / "store-a"
        self.target = work / "rust-target"
        self.transcripts = work / "a-transcripts"
        self.py_case, self.rust_crate = work / "py-case", work / "rust-crate"
        self.ts_project = work / "ts-project"
        self.python = str(REPO / ".venv" / "bin" / "python")
        self.driver = str(Path(driver_dir) / "cargo-sensorium")
        self.token = self.fresh = ""
        self.phases: list[dict] = []
        self.runs: dict = {}
        self.started = time.time()

    # -- the environment ---------------------------------------------------
    def env(self, token: str) -> dict:
        """The whole environment a phase runs under: `ALLOWLIST`, filled."""
        path = os.pathsep.join([self.node_bin, self.driver_dir,
                                str(Path.home() / ".cargo" / "bin"),
                                "/usr/local/bin", "/usr/bin", "/bin"])
        values = {"PATH": path, "HOME": str(Path.home()),
                  "USER": os.environ.get("USER", ""),
                  "LANG": os.environ.get("LANG", "C.UTF-8"),
                  "TMPDIR": str(self.work / "tmp"),
                  "CARGO_TARGET_DIR": str(self.target),
                  "SENSORIUM_DIR": str(self.store), TOKEN_VAR: token}
        assert set(values) == set(ALLOWLIST), sorted(set(values) ^
                                                     set(ALLOWLIST))
        return values

    def phase(self, name: str, fn):
        started = time.time()
        try:
            value = fn()
            error = None
        except Refused:
            raise
        except Exception as exc:                       # noqa: BLE001
            value, error = None, f"{type(exc).__name__}: {exc}"
        self.phases.append({"name": name, "seconds":
                            round(time.time() - started, 3), "error": error})
        elapsed = time.time() - self.started
        print(f"[{elapsed:7.1f}s] {name}: "
              f"{self.phases[-1]['seconds']}s{' ERROR ' + error if error else ''}",
              flush=True)
        if elapsed > self.timers["part"]:
            raise Refused(f"the part's {self.timers['part']}s cap passed "
                          f"after {name}: this is an infrastructure kill, "
                          f"not a measurement")
        return value

    # -- phase 0: what has to be true before anything is recorded ----------
    def preflight(self) -> dict:
        from sensorium import redact

        knobs = redact.Knobs.from_environ({})
        fires = [n for n in ALLOWLIST if n != TOKEN_VAR
                 and redact.fires(n, knobs)]
        if fires:
            raise Refused("these allowlisted names fire rule v1, so H6's "
                          f"'exactly one name' would not be about the "
                          f"token: {fires}")
        if not redact.fires(TOKEN_VAR, knobs):
            raise Refused(f"{TOKEN_VAR} does not fire rule v1: the whole "
                          "part would measure a rule that never ran")
        if self.store.exists():
            raise Refused(f"{self.store} already exists: part A is measured "
                          "ONCE into a fresh store")
        for path in (self.python, self.driver):
            if not os.access(path, os.X_OK):
                raise Refused(f"not executable: {path}")
        node_modules = REPO / "corpus" / "typescript" / "node_modules"
        if not (node_modules / "vitest").is_dir():
            raise Refused(f"no installed vitest under {node_modules}")
        (self.work / "tmp").mkdir(parents=True, exist_ok=True)
        env = self.env("preflight-not-a-token")
        tools = {}
        for label, argv in (("cargo", ["cargo", "--version"]),
                            ("node", ["node", "--version"]),
                            ("vitest", ["npx", "vitest", "--version"])):
            r = _run(argv, REPO / "corpus" / "typescript", env, 120)
            tools[label] = r["out"].strip().splitlines()[-1] if r["out"] \
                else None
        free = shutil.disk_usage(self.work)
        return {"tools": tools, "rule_fires_on_the_token": True,
                "allowlist": list(ALLOWLIST),
                "free_bytes": free.free, "dry_run": self.dry}

    # -- phase 1: the token ------------------------------------------------
    def mint(self) -> dict:
        def one() -> str:
            prefix, body = ((DRY_PREFIX, DRY_BODY) if self.dry
                            else (TOKEN_PREFIX, TOKEN_BODY))
            return prefix + "".join(secrets.choice(_ALPHABET)
                                    for _ in range(body))

        self.token, self.fresh = one(), one()
        path = self.work / "token"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(self.token + "\n")
        return {"sha8": _sha8(self.token), "fresh_sha8": _sha8(self.fresh),
                "length": len(self.token)}

    # -- phase 2: the three copies -----------------------------------------
    def copies(self) -> dict:
        """The disposable copies each arm records in, on
        `corpus/run_corpus.py::_copy_case`'s discipline -- a cargo case's
        build output and a vitest project's installed tree are not its
        source. They persist: H3's re-runs start from the trace's own
        `cwd`/`workspace_root`, and a copy deleted after recording would
        turn every refocus into a refusal about a missing directory."""
        ignore = shutil.ignore_patterns("__pycache__", "target", "Cargo.lock",
                                        ".sensorium")
        corpus = REPO / "corpus"
        shutil.copytree(corpus / "aliasing", self.py_case, ignore=ignore)
        shutil.copytree(corpus / "rust" / "aliasing", self.rust_crate,
                        ignore=ignore)
        ts = corpus / "typescript"
        shutil.copytree(ts, self.ts_project, ignore=shutil.ignore_patterns(
            "__pycache__", "node_modules", ".sensorium", "run_count.txt"))
        (self.ts_project / "node_modules").symlink_to(
            ts / "node_modules", target_is_directory=True)
        self.transcripts.mkdir(parents=True, exist_ok=True)
        return {"python": self.py_case.name, "rust": self.rust_crate.name,
                "typescript": self.ts_project.name}

    def _record(self, label: str, argv, cwd, timer: str) -> list[str]:
        r = _run(argv, cwd, self.env(self.token), self.timers[timer])
        self._keep(f"record-{label}", r)
        if r["killed"]:
            raise Refused(f"the {label} recording hit its "
                          f"{self.timers[timer]}s timer: an infrastructure "
                          "kill, not a measurement")
        ids = RUN_LINE.findall(r["out"])
        if not ids:
            raise Refused(f"the {label} recording produced no run: line "
                          f"(exit {r['rc']})")
        return ids

    # -- phases 3-5: the three recordings ----------------------------------
    def record_python(self):
        self.runs["python"] = self._record(
            "python", [self.python, "-m", "sensorium", "run", "--",
                       "main.py"], self.py_case, "record")

    def record_rust(self):
        self.runs["rust"] = self._record(
            "rust", [self.driver, "sensorium", "run"], self.rust_crate,
            "record_rust")

    def record_typescript(self):
        self.runs["typescript"] = self._record(
            "typescript", [self.python, "-m", "sensorium", "ts", "run", "--",
                           "npx", "vitest", "run", "async_interleaved"],
            self.ts_project, "record")

    # -- phase 6: the modes ------------------------------------------------
    def modes(self) -> dict:
        """The mode sweep: the rows, and one status per gated tree.

        Taken straight after the three recordings and before any query, so
        what it describes is what the RECORDERS left -- a reader that opens
        a WAL database creates `-shm`/`-wal` beside it, and those are files
        the runs did not make.
        """
        rows: list[dict] = []
        roots: list[dict] = []
        for root, scope in ((self.store, "in"),
                            (self.target / "sensorium" / "spool", "in")):
            found, status = _stat_tree(root, scope, self.work)
            rows += found
            roots.append(status)
        # Listed and not gated: the driver's shared build-support trees under
        # the cargo target directory, and the directories this instrument
        # made itself. A reader can see they were looked at; neither is what
        # §1's H2 is a claim about.
        support = self.target / "sensorium"
        if support.is_dir():
            for child in sorted(support.iterdir()):
                if child.name != "spool":
                    rows += _stat_one(child, "out", self.work)
            rows += _stat_one(support, "out", self.work)
        for made in (self.work, self.target, self.py_case, self.rust_crate,
                     self.ts_project, self.transcripts, self.out):
            rows += _stat_one(made, "out", self.work)
        return {"entries": rows, "roots": roots}

    # -- phase 7: the four refocus pairs -----------------------------------
    def refocus(self, in_recorded_env: dict) -> list[dict]:
        pairs = []
        for name, predicted in PREDICTIONS:
            arm, which = name.split("-")
            token = self.token if which == "unchanged" else self.fresh
            run = self.runs[arm][0]
            cwd = self.py_case if arm == "python" else self.rust_crate
            r = _run([self.python, "-m", "sensorium", "refocus", run,
                      "--focus", FOCUS], cwd, self.env(token),
                     self.timers["refocus"])
            self._keep(f"refocus-{name}", r)
            if r["killed"]:
                raise Refused(f"the {name} refocus hit its "
                              f"{self.timers['refocus']}s timer")
            pairs.append(read_pair(name, predicted, r["out"],
                                   in_recorded_env.get(arm, False)))
            pairs[-1]["exit"] = r["rc"]
            pairs[-1]["seconds"] = r["seconds"]
        return pairs

    # -- phase 8: `info` on the three traces -------------------------------
    def info(self) -> list[dict]:
        rows = []
        for arm in ("python", "rust", "typescript"):
            for run in self.runs[arm]:
                r = _run([self.python, "-m", "sensorium", "info", run],
                         self.work, self.env(self.token), 300)
                self._keep(f"info-{arm}-{run}", r)
                row = _parse_info(r["out"])
                row.update(run=run, arm=arm, exit=r["rc"])
                rows.append(row)
        return rows

    # -- phase 9: the grep sweep -------------------------------------------
    def grep(self) -> dict:
        """§1's H1, over everything under the work root except the token
        file and this instrument's own output directory.

        The second value is swept too and reported beside the first: the
        four refocus re-runs recorded under it, so it is a secret this
        apparatus put through the recorders exactly as it did the first, and
        a sweep that looked for only one of them would leave half the
        recordings unchecked. §1 gates on the recording token; the fresh
        one's counts are a reading in the same table.
        """
        roots = [p for p in sorted(self.work.iterdir())
                 if p.name not in ("token", self.out.name)]
        if not roots:
            raise Refused("nothing under the work root to sweep")
        first = _grep_counts(self.token, roots, self.work)
        second = _grep_counts(self.fresh, roots, self.work)
        by_path = {row["path"]: row["count"] for row in second}
        for row in first:
            row["fresh_count"] = by_path.get(row["path"])
        outdir = _grep_counts(self.token, [self.out], self.work) \
            if self.out.is_dir() else []
        return {"files": first, "excluded": ["token", self.out.name],
                "instrument_output": outdir}

    # -- keeping what was read ---------------------------------------------
    def _keep(self, name: str, r: dict) -> None:
        """One command's whole output, on disk, with the token's VALUE
        scrubbed if it is ever there. It must not be -- the transcripts
        print variable names only, which is H1's own claim about them -- and
        the scrub is what keeps a surprise out of a committed file rather
        than a reason to stop checking."""
        text = r["out"]
        for value in (self.token, self.fresh):
            if value:
                text = text.replace(value, "<token>")
        path = self.transcripts / f"{name}.txt"
        path.write_text(f"$ {' '.join(r['argv'])}\n"
                        f"# cwd {r['cwd']}  exit {r['rc']}  "
                        f"{r['seconds']}s\n{text}")
        os.chmod(path, 0o600)


def _sha8(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def _stat_one(path: Path, scope: str, work: Path) -> list[dict]:
    r = subprocess.run(["stat", "-c", "%a %n", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return [{"path": _rel(path, work), "mode": None,
                 "kind": "dir" if path.is_dir() else "file", "scope": scope}]
    mode, _, _name = r.stdout.strip().partition(" ")
    return [{"path": _rel(path, work), "mode": mode,
             "kind": "dir" if path.is_dir() else "file", "scope": scope}]


def _stat_tree(root: Path, scope: str,
               work: Path) -> tuple[list[dict], dict]:
    """`find <root> -exec stat -c '%a %n' {} +`, and whether it could run.

    The status is the point. `find` over a root that is not there prints
    nothing and exits non-zero, and this used to return `[]` for both that
    and a tree it read: `cell_h2` was then handed a short list it could not
    tell from a complete one, and a run whose Rust arm never recorded would
    have passed on the store alone. Now the root's own reading travels with
    the rows and the cell drops on it.
    """
    rel = _rel(root, work)
    if not root.exists():
        return [], {"root": rel, "ok": False, "why": "no such directory"}
    r = subprocess.run(["find", str(root), "-exec", "stat", "-c", "%a %n",
                        "{}", "+"], capture_output=True, text=True)
    rows = []
    for line in r.stdout.splitlines():
        mode, _, name = line.partition(" ")
        path = Path(name)
        rows.append({"path": _rel(path, work), "mode": mode or None,
                     "kind": "dir" if path.is_dir() else "file",
                     "scope": scope})
    ok = r.returncode == 0 and bool(rows)
    why = ("" if ok else
           f"find exited {r.returncode}: {r.stderr.strip()[:120]}"
           if r.returncode else "find listed nothing")
    return rows, {"root": rel, "ok": ok, "why": why}


def _rel(path: Path, work: Path) -> str:
    """Every path in the results file is relative to the work root: the one
    place a box path is written down is the record's §2 pin table."""
    try:
        return str(Path(path).relative_to(work))
    except ValueError:
        return str(path)


def _grep_counts(needle: str, roots: list[Path], work: Path) -> list[dict]:
    """`grep -rc --binary-files=text -F <needle>` over `roots`, per file.

    `-r` and not `-R`: the vitest project's `node_modules` is a SYMLINK to
    the checkout's installed tree, and following it would sweep hundreds of
    megabytes that no recorder wrote. Exit 1 is "no line selected anywhere",
    which is the passing case and not an error.
    """
    r = subprocess.run(["grep", "-rc", "--binary-files=text", "-F",
                        "-e", needle, "--", *[str(p) for p in roots]],
                       capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise Refused(f"grep exited {r.returncode}: {r.stderr.strip()[:200]}")
    rows = []
    for line in r.stdout.splitlines():
        path, _, count = line.rpartition(":")
        rows.append({"path": _rel(Path(path), work),
                     "count": int(count) if count.isdigit() else None})
    return sorted(rows, key=lambda row: row["path"])


#: `info_cmd.env_field`: `env:<hash> (<n> vars, <m> redacted: <names>)`, or
#: the two-field form when the rule fired on nothing. `_capped` would append
#: `and N more` past eight names, which this refuses rather than truncating.
_ENV_FIELD = re.compile(r"env:(?P<hash>\S+) \((?P<vars>\d+) vars"
                        r"(?:, (?P<n>\d+) redacted(?:: (?P<names>[^)]*))?)?\)")
_RECORDER = re.compile(r"^recorder: (?P<recorder>.+?)  lang: ", re.M)


def _parse_info(text: str) -> dict:
    """The three facts §2 quotes from `sensorium info`: how many variables
    the trace stored, which of them rule v1 took out, and which recorder
    wrote it. `None` for anything the output did not carry -- never a
    default, which for `names` would be an empty set that reads as a
    measured zero."""
    m, rec = _ENV_FIELD.search(text), _RECORDER.search(text)
    names = None
    if m:
        blob = m.group("names")
        if blob is None:
            names = []
        elif "more" in blob:
            raise Refused(f"info capped the redacted-name list: {blob!r}")
        else:
            names = [n.strip() for n in blob.split(",") if n.strip()]
    return {"names": names, "vars": int(m.group("vars")) if m else None,
            "env_hash": m.group("hash") if m else None,
            "recorder": rec.group("recorder") if rec else None}


def _driver_versions(store: Path, runs: dict) -> dict:
    """`driver_version` where a recorder writes one -- `cargo-sensorium
    0.7.0` on a Rust trace, the Python driver's own version on a TypeScript
    one, nothing at all on a Python one. Read from the trace rather than
    from a `--version` flag the driver does not have."""
    import sqlite3

    out = {}
    for arm, ids in runs.items():
        for run in ids:
            path = store / "traces" / f"{run}.db"
            if not path.exists():
                continue
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                row = con.execute("select value from meta where key = ?",
                                  ("driver_version",)).fetchone()
            finally:
                con.close()
            out[arm] = json.loads(row[0]) if row else None
    return out


# -- the run ---------------------------------------------------------------
def main() -> int:
    work = Path(os.environ["E16_WORK"]).resolve()
    out = Path(os.environ["E16_OUT"]).resolve()
    part = Part(work, out, os.environ["E16_NODE_BIN"],
                os.environ["E16_DRIVER_DIR"],
                dry=os.environ.get("E16_DRY") == "1")
    result = {"dry_run": part.dry, "started": time.time(),
              "dry_run_findings": dry_run_findings()}
    try:
        result["preflight"] = part.phase("preflight", part.preflight)
        result["token"] = part.phase("mint", part.mint)
        result["copies"] = part.phase("copies", part.copies)
        part.phase("record-python", part.record_python)
        part.phase("record-rust", part.record_rust)
        part.phase("record-typescript", part.record_typescript)
        modes = part.phase("modes", part.modes) or {}
        info = part.phase("info-pre", part.info)
        held = {row["arm"]: TOKEN_VAR in (row["names"] or [])
                for row in info}
        pairs = part.phase("refocus", lambda: part.refocus(held))
        # BEFORE the sweep, not after: a read-only sqlite connection cannot
        # checkpoint a WAL, so opening a trace here leaves `-wal`/`-shm`
        # beside it -- and files this instrument made after the grep are
        # files the grep never looked at. Measured in the dry run, which is
        # what a dry run is for.
        result["versions"] = part.phase("versions", lambda: {
            "expected": EXPECTED,
            "recorder": {row["arm"]: row["recorder"] for row in info},
            "driver_version": _driver_versions(part.store, part.runs),
            "sensorium": _installed_version(),
            "tools": result["preflight"]["tools"]})
        sweep = part.phase("grep", part.grep)
        result["runs"] = part.runs
        result["cells"] = {
            "H1": cell_h1(sweep["files"] if sweep else None),
            "H2": cell_h2(modes.get("entries"), modes.get("roots")),
            "H3": cell_h3(pairs),
            # `arm` travels with the row: H6 is a claim about all three
            # recorders, and the cell has to be able to see one missing.
            "H6": cell_h6([{"run": r["run"], "arm": r["arm"],
                            "names": r["names"], "vars": r["vars"]}
                           for r in (info or [])])}
        result["h1_sweep"] = sweep
        result["h2_sweep"] = modes.get("entries")
        result["h2_roots"] = modes.get("roots")
        result["h6_traces"] = info
        result["dropped"] = [{"cell": c, "reason": why, "word": "dropped"}
                             for c, why in DROPPED]
        result["part"] = part_word(result["cells"])
        result["status"] = "complete"
    except Refused as exc:
        result["status"] = "refused"
        result["refusal"] = str(exc)
    result["phases"] = part.phases
    result["finished"] = time.time()
    result["seconds"] = round(result["finished"] - result["started"], 1)
    result["lens"] = {"work_root": str(work), "store": str(part.store),
                      "transcripts": str(part.transcripts),
                      "rust_crate": str(part.rust_crate),
                      "python_case": str(part.py_case),
                      "ts_project": str(part.ts_project),
                      "cargo_target": str(part.target),
                      "repo": str(REPO), "out": str(out)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "results-a.json").write_text(json.dumps(result, indent=2,
                                                   sort_keys=True) + "\n")
    ok = result["status"] == "complete"
    (out / ("e16a.DONE" if ok else "e16a.FAILED")).write_text(
        result.get("part", result.get("refusal", "?")) + "\n")
    print(("done: " + result["part"]) if ok
          else ("FAILED: " + result["refusal"]), flush=True)
    return 0 if ok else 1


#: How the dry run that preceded a measurement reports itself into the raw
#: record: one finding per line in `E16_DRY_FINDINGS`, passed through by
#: `e16a.sh`. §2 has to carry a dry-run reading -- what the dry run found
#: and what changed in the instrument between it and the measurement -- and
#: a field the assembler can render is what keeps that from depending on
#: somebody remembering to type it. Empty on a dry run itself, and empty on
#: a measurement whose operator wrote the paragraph by hand (which is what
#: run 1 did, and §2 says so).
DRY_FINDINGS_VAR = "E16_DRY_FINDINGS"


def dry_run_findings() -> list[str]:
    return [line.strip() for line in
            os.environ.get(DRY_FINDINGS_VAR, "").splitlines() if line.strip()]


def _installed_version() -> str | None:
    import importlib.metadata as md

    try:
        return md.version("sensorium")
    except md.PackageNotFoundError:
        return None


if __name__ == "__main__":
    sys.exit(main())
