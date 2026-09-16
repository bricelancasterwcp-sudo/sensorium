#!/usr/bin/env python3
"""E16 part C: the phases, the readers and the one cell.

Launched detached by `e16c.sh`, which passes every location in the
environment so that no path on one box is written into a file that travels
with the repository. What this measures is fixed by the record's §1 -- spec
§9, plan A's block and the dated amendment that pre-registers part C -- and
narrowed to part C by it: **H4 in full**, on a COPY of this box's own store.
H1, H2, H3, H5 and H6 were parts A's and B's; each is written into the
results file as `dropped` with the part that owns it, never as a number and
never as PASS.

WHAT IS COPIED, AND WHY A COPY
------------------------------
`~/.sensorium/traces` and `redaction.key`, into `store-<label>/` under the
work root (P12). The live store is never written to: the retrofit rewrites
every trace on disk, and a measurement that ran it on the store it is a
claim about would have nothing left to re-measure if it STOPped. The chore
that retrofits the live store is Brice's, after the merge and conditional on
this section reading PASS (C18).

THE TOKEN
---------
NOT minted (P10). `CLAUDE_CODE_MESSAGING_TOKEN`'s value is already in the
copy's own traces, read from the first `*.db`'s `meta.env` through a
read-only connection, held in memory, never printed and never written
anywhere but `grep`'s `-e` argument; the record cites `sha256(value)[:8]`. A
rehearsal fabricates three traces carrying a `dry-` decoy instead, and never
touches the live store's copy (P11).

Part A's rule for what a phase may write holds unchanged: `None`, or a
measurement, never a default -- and `h4` turns a `None` anywhere in its
input into `dropped`, because the one thing this instrument must not be able
to do is report a hole as a pass.

WHY THE TWO REDACT RUNS DO NOT USE PART A'S RUNNER
--------------------------------------------------
`e16a._run` merges stderr INTO stdout, which is right for a recording whose
whole output is evidence and wrong here: `--dry-run` prints `dry run:
nothing was written` on STDERR precisely so its stdout stays byte-identical
to the real run's (C10), and a merged capture would make H4's clause 4
compare the one line the design put out of the way.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Part A's runner, imported whole: the timed phase, the transcript keeper,
# the subprocess runner and the sweeps are one instrument's machinery used
# by three parts, and `e16a.py` is a measured record's instrument -- read,
# never edited.
from e16a import (Part, _grep_counts, _installed_version,  # noqa: E402,F401
                  _rel, _run, _sha8, _stat_tree, dry_run_findings)
# The decision layer, split out exactly as parts A's and B's are and
# re-exported whole, so `e16c.h4` and `assemble_e16c`'s imports mean one
# thing.
from e16c_cells import (CELL_TITLES, CLAUSES, DROPPED,  # noqa: E402,F401
                        DRY_TIMERS, EXPECTED_TRACES, EXPECTED_VERSION,
                        RULES, SUMMARY, TIMERS, TOKEN_VAR, Refused, h4,
                        parse_lines, part_word)

#: The phases that are PRECONDITIONS rather than measurements, and whose
#: failure therefore ends the run instead of dropping the cell: `preflight`
#: (a retrofit measured under 0.16.0 is a measurement of a command that is
#: not there), `copy` (the subject; a half-copied store is a different
#: claim, not a smaller one) and `count-before` (H4's PREMISE -- "0
#: everywhere after" is true of a store that never held the value).
#: `tests/test_acceptance_e16_phase.py` holds this list against `main`'s own
#: call sites, so dropping `critical=True` from any of the three reddens
#: there rather than silently restoring the fail-open R37 closed.
CRITICAL_PHASES = ("preflight", "copy", "count-before")

#: `info_cmd.redaction_line`'s `by` word, anchored on that line: `by` is an
#: English word and a trace's `argv` is printed two lines above it.
BY = re.compile(r"^redaction:.*?\bby (?P<by>\w+)", re.M)

#: The decoy a rehearsal plants, in parts A's and B's shape. It matches no
#: content pattern, so the NAME rule is the only hand that can reach it --
#: which is why `fabricate` puts it only where a name rule looks (R14).
DRY_PREFIX, DRY_BODY = "dry-", 4
_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

#: The three runs a rehearsal fabricates: a run id is a file stem and this
#: instrument reads stems, so these are the rehearsal's whole namespace.
DRY_RUNS = ("20260101-000001-dry001", "20260101-000002-dry002",
            "20260101-000003-dry003")


def _run_split(argv, cwd, env, timeout) -> dict:
    """Part A's `_run` with the two streams KEPT APART (see the docstring
    above), in its own session, killed BY GROUP on the timer.

    A kill leaves `out: None`, which every reader below treats as a hole; an
    empty string would parse as a run that printed no line, which is a STOP
    about a measurement nobody made.
    """
    started = time.time()
    proc = subprocess.Popen(
        [str(a) for a in argv], cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    killed = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        killed = True
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
    return {"argv": [str(a) for a in argv], "cwd": str(cwd),
            "rc": None if killed else proc.returncode, "killed": killed,
            "out": None if killed else (out or ""), "err": err or "",
            "seconds": round(time.time() - started, 3)}


def fabricate(store: Path, decoy: str) -> dict:
    """A rehearsal's whole subject: three Python-shaped traces at 0644 with
    the decoy where the NAME rule reaches it, and a `redaction.key`.

    Ruling R14 fixes WHERE: the environment, one `str` RETURN under a callee
    the rule fires on (`secret`), one LINE delta bound to `token` -- and NOT
    an output row or a `children` element, which only the CONTENT rule
    reaches: `dry-` plus four characters matches no content pattern, so a
    decoy there would survive the retrofit and read as residue. `env_hash`
    MUST reproduce or `plan()` refuses the trace (C3) and the rehearsal
    measures a refusal instead of a retrofit.
    """
    from sensorium.redact_key import Key
    from sensorium.store.writer import TraceWriter
    from tests.helpers import finalize_synthetic

    env = {TOKEN_VAR: decoy, "HOME": "/h"}
    env_hash = hashlib.sha256(
        json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]
    traces = store / "traces"
    traces.mkdir(parents=True)
    for run in DRY_RUNS:
        path = traces / f"{run}.db"
        w = TraceWriter(path, batch=1)
        code = w.intern_code("prog.py", "secret", 1)
        call = w.add_event(1, 1, "CALL", None, code, 1,
                           {"args": {"n": {"k": "num", "v": 1}}})
        frame = w.open_frame(None, code, call, 0, 1)
        w.add_event(2, 1, "LINE", frame, code, 2, {"deltas": {
            "token": {"k": "str", "v": decoy, "trunc": False}}})
        ret = w.add_event(3, 1, "RETURN", frame, code, None, {
            "value": {"k": "str", "v": decoy, "trunc": False}})
        w.close_frame(frame, ret, "return")
        finalize_synthetic(w, run_id=run, env=dict(env), env_hash=env_hash)
        w.close()
        path.chmod(0o644)
    return {"runs": list(DRY_RUNS), "key_id": Key.load_or_create(store).key_id}


def _read_meta(path: Path) -> dict:
    """One trace's whole `meta` table, through a READ-ONLY connection: the
    copy is the subject, and an instrument that opened it read-write would
    checkpoint a WAL and change the bytes `count-before` is about to count.
    """
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT key, value FROM meta").fetchall()
    finally:
        con.close()
    out = {}
    for key, value in rows:
        try:
            out[key] = json.loads(value)
        except (TypeError, ValueError):
            out[key] = value
    return out


class PartC(Part):
    """One part-C measurement: the live store it copies, the copy, and the
    phases that read it.

    Part A's `__init__` is deliberately NOT called: it derives a node
    directory, a release driver, a cargo target tree and three disposable
    case copies, none of which part C has -- no recorder runs here, and the
    only subprocesses are this branch's own `python -m sensorium`. What is
    inherited is `phase()` (the timed, critical-aware runner) and `_keep()`
    (the scrubbed transcript), which is what those two exist for.
    """

    def __init__(self, work: Path, out: Path, dry: bool, label: str):
        self.work, self.out, self.label, self.dry = work, out, label, dry
        self.timers = DRY_TIMERS if dry else TIMERS
        self.live = Path(os.environ.get("E16_LIVE",
                                        str(Path.home() / ".sensorium")))
        # Every per-run directory carries the label, so one work root holds
        # a measurement and a re-measurement without either sweeping the
        # other's files.
        self.store = work / f"store-{label}"
        self.transcripts = work / f"{label}-transcripts"
        self.python = str(REPO / ".venv" / "bin" / "python")
        # `_keep` scrubs both out of every transcript; part C mints nothing.
        self.token = self.fresh = ""
        self.stems: list[str] | None = None
        self.dry_out: str | None = None
        self.real_out: str | None = None
        self.phases: list[dict] = []
        self.started = time.time()

    def env(self) -> dict:
        """Part A's `ALLOWLIST` less the two names part C has no use for
        (`CARGO_TARGET_DIR`, and the token variable itself -- nothing is
        recorded here), with `SENSORIUM_DIR` pointed at the COPY.

        A complete dict rather than an overlay (`env -i` with the allowlist
        put back), and not for tidiness: `SENSORIUM_REDACT_NAMES` and
        `SENSORIUM_REDACT_ALLOW` are the CALLER's knobs (C4), stamped into
        every trace this pass rewrites, so a stale export in the launching
        shell would silently change what the measurement measured.
        """
        values = {"PATH": os.pathsep.join(["/usr/local/bin", "/usr/bin",
                                           "/bin"]),
                  "HOME": str(Path.home()),
                  "USER": os.environ.get("USER", ""),
                  "LANG": os.environ.get("LANG", "C.UTF-8"),
                  "TMPDIR": str(self.work / "tmp"),
                  "SENSORIUM_DIR": str(self.store)}
        knobs = sorted(n for n in values if n.startswith("SENSORIUM_"))
        assert knobs == ["SENSORIUM_DIR"], knobs
        return values

    # -- phase 1: what has to be true before anything is copied ------------
    def preflight(self) -> dict:
        """The live store is there and keyed, the venv is this branch's, and
        the command exists -- `--help` exiting 0 being the cheapest proof
        that `cli._QUERY_MODULES` carries it."""
        traces = self.live / "traces"
        if not traces.is_dir():
            raise Refused("no traces directory under the live store")
        live_db = sorted(traces.glob("*.db"))
        if not live_db:
            raise Refused("the live store holds no `*.db`: there is nothing "
                          "to copy and H4 has no subject")
        if not (self.live / "redaction.key").is_file():
            raise Refused("the live store has no redaction.key: a retrofit "
                          "would mint one and the digests would be under a "
                          "key nobody has seen")
        version = _installed_version()
        if version != EXPECTED_VERSION:
            raise Refused(f"the venv's sensorium reads {version}, not "
                          f"{EXPECTED_VERSION}: this would measure another "
                          "version of the command")
        if self.store.exists():
            raise Refused(f"{_rel(self.store, self.work)} already exists: "
                          "part C is measured ONCE, into a fresh copy")
        if not os.access(self.python, os.X_OK):
            raise Refused(f"not executable: {self.python}")
        (self.work / "tmp").mkdir(parents=True, exist_ok=True)
        self.transcripts.mkdir(parents=True, exist_ok=True)
        r = _run([self.python, "-m", "sensorium", "redact", "--help"],
                 self.work, self.env(), 120)
        self._keep("redact-help", r)
        if r["rc"] != 0:
            raise Refused(f"`sensorium redact --help` exited {r['rc']}: the "
                          "command is not registered in this venv")
        return {"sensorium": version, "expected_version": EXPECTED_VERSION,
                "live_db": len(live_db), "expected_traces": EXPECTED_TRACES,
                "free_bytes": shutil.disk_usage(self.work).free,
                "dry_run": self.dry, "help_exit": r["rc"]}

    # -- phase 2: the copy, and the value it already holds ------------------
    def copy(self) -> dict:
        """The subject: `traces/` and `redaction.key` copied out of the live
        store (P12), or three fabricated traces when this is a rehearsal
        (P11). Then read once, through read-only connections: the token's
        value out of the FIRST `*.db`, and every trace's `incomplete`,
        `recorder` and own token digest.

        Refused on a `.<run>.db.tmp` or an `incomplete` trace -- H4 is about
        COMPLETED traces, and a file another process holds open in WAL mode
        is not one this pass may claim to have rewritten (C8).

        The census of DISTINCT values is reported, gated by nothing: how
        many times a box's token rotated is a fact about the box, and
        `count-before` is where it becomes a premise.
        """
        traces = self.store / "traces"
        if self.dry:
            self.token = DRY_PREFIX + "".join(secrets.choice(_ALPHABET)
                                              for _ in range(DRY_BODY))
            made = fabricate(self.store, self.token)
        else:
            shutil.copytree(self.live / "traces", traces)
            shutil.copy2(self.live / "redaction.key",
                         self.store / "redaction.key")
            made = {"copied_from": "~/.sensorium"}
        tmps = sorted(p.name for p in traces.glob(".*.db*.tmp"))
        if tmps:
            raise Refused(f"the copy holds {len(tmps)} in-flight tmp "
                          f"file(s): {', '.join(tmps[:5])}. Something was "
                          "writing to the store while it was copied")
        dbs = sorted(traces.glob("*.db"))
        if not dbs:
            raise Refused("the copy holds no `*.db`")
        self.stems = [p.stem for p in dbs]
        incomplete, census, recorders, holders = [], {}, {}, 0
        for path in dbs:
            meta = _read_meta(path)
            if meta.get("incomplete") is not False:
                incomplete.append(path.stem)
            rec = meta.get("recorder")
            recorders[rec] = recorders.get(rec, 0) + 1
            env = meta.get("env") if isinstance(meta.get("env"), dict) else {}
            value = env.get(TOKEN_VAR)
            if value is None:
                continue
            holders += 1
            census[_sha8(value)] = census.get(_sha8(value), 0) + 1
            if not self.dry and not self.token:
                self.token = value
        if incomplete:
            raise Refused(f"{len(incomplete)} trace(s) in the copy are in "
                          f"flight: {', '.join(incomplete[:5])}. H4 is "
                          "about completed traces")
        if not self.token:
            raise Refused(f"no trace in the copy holds {TOKEN_VAR} in its "
                          "environment: H4's subject is not in this store")
        sides = [p.suffix for p in traces.iterdir()]
        return {**made, "n_db": len(dbs), "token_sha8": _sha8(self.token),
                "token_length": len(self.token),
                "traces_holding_the_variable": holders,
                "token_census": dict(sorted(census.items(),
                                            key=lambda kv: -kv[1])),
                "recorders": {str(k): v for k, v in sorted(
                    recorders.items(), key=lambda kv: -kv[1])},
                "n_wal": sides.count("-wal"), "n_shm": sides.count("-shm")}

    # -- phase 3: H4's premise ---------------------------------------------
    def count_before(self) -> dict:
        """Every `*.db` in the copy holds the value at least once BEFORE the
        run. A PRECONDITION: "0 everywhere after" is true of a store that
        never held it, so a copy that does not carry the secret is not the
        store §9 describes and the run refuses rather than publishing a pass
        about nothing. The refusal names the census, since the likeliest
        reason a trace lacks THIS value is that it holds another.
        """
        rows = _grep_counts(self.token, [self.store], self.work)
        by_path = {row["path"]: row["count"] for row in rows}
        bad = []
        for stem in self.stems or []:
            path = _rel(self.store / "traces" / f"{stem}.db", self.work)
            if not by_path.get(path):
                bad.append(f"{stem} ({by_path.get(path)})")
        if bad:
            raise Refused(
                f"{len(bad)} of {len(self.stems or [])} `*.db` in the copy "
                f"do not hold the value read from the first trace "
                f"(sha8 {_sha8(self.token)}): {', '.join(bad[:5])}"
                + (f" and {len(bad) - 5} more" if len(bad) > 5 else "")
                + ". H4's premise is that every trace holds it")
        held = [row for row in rows if row["count"]]
        return {"files": rows, "files_holding_the_value": len(held),
                "occurrences_total": sum(row["count"] or 0 for row in held)}

    # -- phases 4 and 5: the two passes ------------------------------------
    def dry_run(self) -> dict:
        return self._redact(True)

    def real_run(self) -> dict:
        return self._redact(False)

    def _redact(self, dry: bool) -> dict:
        """One `redact --all` pass, its two streams kept apart. The stdout
        is held in memory for `compare` -- the byte comparison is made
        BEFORE any scrub, so it compares what the command printed -- and
        written to a transcript of its own, so the two committed files can
        be diffed by hand and reach clause 4's own answer."""
        label = "dry" if dry else "real"
        argv = [self.python, "-m", "sensorium", "redact", "--all"]
        r = _run_split(argv + (["--dry-run"] if dry else []), self.work,
                       self.env(), self.timers["redact"])
        setattr(self, f"{label}_out", r["out"])
        self._keep_stream(f"redact-{label}", r["out"] or "")
        self._keep_stream(f"redact-{label}.stderr", r["err"])
        if r["killed"]:
            raise RuntimeError(f"the {label} pass hit its "
                               f"{self.timers['redact']}s timer")
        rows = parse_lines(r["out"]) or {}
        lines = (r["out"] or "").splitlines()
        return {"rc": r["rc"], "seconds": r["seconds"], "killed": False,
                "lines": len(lines), "trace_lines": len(rows),
                "summary": next((ln for ln in lines if SUMMARY.match(ln)),
                                None),
                "stdout_sha256": hashlib.sha256(
                    (r["out"] or "").encode()).hexdigest(),
                "stderr": r["err"][:4000],
                "values_total": sum(row["values"] or 0
                                    for row in rows.values()),
                "rows": rows}

    # -- phase 6: H4's clause 4 --------------------------------------------
    def compare(self) -> bool:
        """The two stdouts, as bytes. A pass that left no stdout raises, so
        the cell drops rather than reading two missing strings as equal."""
        if self.dry_out is None or self.real_out is None:
            raise RuntimeError("one of the two passes left no stdout")
        return self.dry_out == self.real_out

    # -- phase 7: H4's clause 2 --------------------------------------------
    def grep_after(self) -> dict:
        """`count-before`'s sweep again, over the same root, after the real
        run -- and what is left of the sidecars, which `apply` unlinks with
        the inode it replaced (C7)."""
        rows = _grep_counts(self.token, [self.store], self.work)
        traces = self.store / "traces"
        sides = [p.suffix for p in traces.iterdir()] if traces.is_dir() else []
        return {"files": rows, "files_examined": len(rows),
                "files_holding_the_value": sum(1 for r in rows if r["count"]),
                "n_wal": sides.count("-wal"), "n_shm": sides.count("-shm")}

    # -- phase 8: H4's clause 3 --------------------------------------------
    def info_sweep(self) -> list[dict]:
        """`sensorium info` on every trace: it still opens, and it says
        which hand took its secrets. The sweep has ONE budget (§1's
        amendment caps `info` per sweep, not per trace), so the remaining
        seconds are what each call is given and an exhausted budget ends the
        phase rather than letting 273 timers add up to an afternoon."""
        deadline = time.time() + self.timers["info"]
        rows: list[dict] = []
        for stem in self.stems or []:
            left = deadline - time.time()
            if left <= 0:
                raise RuntimeError(
                    f"the info sweep's {self.timers['info']}s budget ran out "
                    f"after {len(rows)} of {len(self.stems or [])} traces")
            r = _run([self.python, "-m", "sensorium", "info", stem],
                     self.work, self.env(), left)
            self._keep(f"info-{stem}", r)
            m = BY.search(r["out"] or "")
            rows.append({"run": stem, "exit": r["rc"],
                         "by": m.group("by") if m else None,
                         "seconds": r["seconds"]})
        return rows

    # -- phase 9: reported, never gated ------------------------------------
    def mode_sweep(self) -> dict:
        """Every mode under the copy after the run. §9's H2 was part A's
        claim about what a RECORDER leaves; this is what the RETROFIT
        leaves, which §1's amendment reports and gates on nothing."""
        rows, status = _stat_tree(self.store, "store", self.work)
        files = [row for row in rows if row["kind"] == "file"]
        return {"entries": rows, "root": status, "files": len(files),
                "files_at_600": sum(1 for r in files if r["mode"] == "600"),
                "traces_dir_mode": next(
                    (r["mode"] for r in rows
                     if r["path"] == _rel(self.store / "traces", self.work)),
                    None)}

    def _keep_stream(self, name: str, text: str) -> None:
        """One captured stream, on disk, byte for byte -- no header, so the
        two `redact-*.txt` files can be diffed by hand. The token's value is
        scrubbed if it is ever there; it must not be, since the command
        prints variable NAMES only, and the scrub keeps a surprise out of a
        committed file rather than being a reason to stop checking."""
        if self.token:
            text = text.replace(self.token, "<token>")
        self.transcripts.mkdir(parents=True, exist_ok=True)
        path = self.transcripts / f"{name}.txt"
        path.write_text(text)
        os.chmod(path, 0o600)


# -- the run ---------------------------------------------------------------
def main() -> int:
    work = Path(os.environ["E16_WORK"]).resolve()
    out = Path(os.environ["E16_OUT"]).resolve()
    part = PartC(work, out, dry=os.environ.get("E16_DRY") == "1",
                 label=os.environ["E16_LABEL"])
    result = {"dry_run": part.dry, "started": time.time(),
              "dry_run_findings": dry_run_findings(),
              "expected_traces": EXPECTED_TRACES}
    # Bound to the result up front, so a phase that ends the run late still
    # leaves every cell decided before it in the raw record.
    cells: dict = {}
    result["cells"] = cells
    try:
        result["preflight"] = part.phase("preflight", part.preflight,
                                         critical=True)
        copied = part.phase("copy", part.copy, critical=True)
        result["copy"] = copied
        result["before"] = part.phase("count-before", part.count_before,
                                      critical=True)
        result["dry"] = part.phase("dry-run", part.dry_run)
        result["real"] = part.phase("real", part.real_run)
        result["identical"] = part.phase("compare", part.compare)
        after = part.phase("grep-after", part.grep_after)
        result["after"] = after
        result["infos"] = part.phase("info", part.info_sweep)
        result["modes"] = part.phase("modes", part.mode_sweep)
        result["versions"] = {"sensorium": _installed_version(),
                              "expected": EXPECTED_VERSION,
                              "recorders": (copied or {}).get("recorders")}
        result["n_db"] = (copied or {}).get("n_db")
        result["token_sha8"] = (copied or {}).get("token_sha8")
        cells["H4"] = h4(part.stems, parse_lines(part.dry_out),
                         (after or {}).get("files"), result["infos"],
                         result["identical"])
        result["dropped"] = [{"cell": c, "reason": why, "word": "dropped"}
                             for c, why in DROPPED]
        result["part"] = part_word(cells)
        result["status"] = "complete"
    except Refused as exc:
        result["status"] = "refused"
        result["refusal"] = str(exc)
    result["phases"] = part.phases
    result["finished"] = time.time()
    result["seconds"] = round(result["finished"] - result["started"], 1)
    result["label"] = part.label
    result["pins"] = {"store": _rel(part.store, work),
                      "transcripts": _rel(part.transcripts, work),
                      "out": _rel(out, work)}
    result["lens"] = {"work_root": str(work), "store": str(part.store),
                      "transcripts": str(part.transcripts),
                      "repo": str(REPO), "out": str(out)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "results-c.json").write_text(json.dumps(result, indent=2,
                                                   sort_keys=True) + "\n")
    ok = result["status"] == "complete"
    (out / ("e16c.DONE" if ok else "e16c.FAILED")).write_text(
        result.get("part", result.get("refusal", "?")) + "\n")
    print(("done: " + result["part"]) if ok
          else ("FAILED: " + result["refusal"]), flush=True)
    if ok:
        print(f"H4: {cells['H4']['word']} -- {cells['H4']['read']}",
              flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
