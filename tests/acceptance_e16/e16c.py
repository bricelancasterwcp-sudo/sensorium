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

THE TOKENS
----------
NOT minted (P10), and there is more than one. `CLAUDE_CODE_MESSAGING_TOKEN`'s
value is already in the copy's own traces -- FOUR distinct values on this
box, because the token rotated over the store's life -- so the instrument
reads every trace's own value through a read-only connection and sweeps the
DISTINCT set one value at a time (ruling R15, recorded as an amendment
beside §1). Every value is held in memory, never printed and never written
anywhere but `grep`'s `-e` argument; the record cites each one's
`sha256(value)[:8]` beside the number of traces holding it. A rehearsal
fabricates traces carrying two `dry-` decoys instead, and never touches the
live store's copy (P11).

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
from e16c_cells import (AMENDMENTS, CELL_TITLES, CLAUSES,  # noqa: E402,F401
                        DROPPED, DRY_TIMERS, EXPECTED_TRACES,
                        EXPECTED_VERSION, RULES, SUMMARY, TIMERS, TOKEN_VAR,
                        Refused, h4, parse_lines, part_word)

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

#: The runs a rehearsal fabricates, and which of TWO decoys each carries.
#: Two, in the live store's own shape (one dominant value and a rotation),
#: because the sweep is over a SET (R15) and a rehearsal with one value
#: would exercise the loop exactly once -- which is the shape that cannot
#: catch a sweep that silently drops every value but the first.
DRY_RUNS = (("20260101-000001-dry001", 0), ("20260101-000002-dry002", 0),
            ("20260101-000003-dry003", 1))
DRY_DECOYS = 2


def _run_split(argv, cwd, env, timeout) -> dict:
    """Part A's `_run` with the two streams KEPT APART (see the docstring
    above), in its own session, killed BY GROUP on the timer, and stdout
    captured as BYTES.

    Bytes because clause 4 says "byte for byte" and means it: `text=True`
    would put the two captures through a decoder and a newline translation
    before they were ever compared, so two stdouts differing in an
    undecodable byte or a line ending would compare equal. The bytes are
    what is hashed and what `compare` diffs; a decoded copy is made for
    parsing and for the transcripts, which is a reading OF the bytes rather
    than the thing compared.

    A kill leaves `out: None`, which every reader below treats as a hole; an
    empty string would parse as a run that printed no line, which is a STOP
    about a measurement nobody made.
    """
    started = time.time()
    proc = subprocess.Popen(
        [str(a) for a in argv], cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
            "out": None if killed else (out or b""),
            "err": (err or b"").decode("utf-8", "replace"),
            "seconds": round(time.time() - started, 3)}


def fabricate(store: Path, decoys: list[str]) -> dict:
    """A rehearsal's whole subject: three Python-shaped traces at 0644 with
    the decoys where the NAME rule reaches them, their `-wal`/`-shm`
    sidecars beside them, and a `redaction.key`.

    Ruling R14 fixes WHERE the decoy goes: the environment, one `str` RETURN
    under a callee the rule fires on (`secret`), one LINE delta bound to
    `token` -- and NOT an output row or a `children` element, which only the
    CONTENT rule reaches: `dry-` plus four characters matches no content
    pattern, so a decoy there would survive the retrofit and read as
    residue. `env_hash` MUST reproduce or `plan()` refuses the trace (C3)
    and the rehearsal measures a refusal instead of a retrofit.

    THE SIDECARS ARE THE POINT of the staging step. `TraceWriter.close()`
    checkpoints and removes the `-wal`/`-shm`, so a store built in place has
    none -- and a rehearsal over a store with no sidecars cannot tell a
    working sidecar count from one that is structurally zero, which is
    exactly the bug this file shipped with (`Path("x.db-wal").suffix` is
    `".db-wal"`, so counting suffixes counted nothing). Each trace is
    therefore built under `staging/`, opened by a second connection that
    materialises its sidecars, and the three files copied out while that
    connection is still open -- which leaves the copy in the shape every
    live store is in: sidecars on disk, nobody holding them.
    """
    from sensorium.redact_key import Key
    from sensorium.store.writer import TraceWriter
    from tests.helpers import finalize_synthetic

    traces, staging = store / "traces", store / "staging"
    traces.mkdir(parents=True)
    staging.mkdir(parents=True)
    holders, of_run = [], {}
    for run, which in DRY_RUNS:
        decoy = decoys[which]
        of_run[run] = decoy
        env = {TOKEN_VAR: decoy, "HOME": "/h"}
        env_hash = hashlib.sha256(
            json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]
        src = staging / f"{run}.db"
        w = TraceWriter(src, batch=1)
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
        # Held open across the copy, and closed only once every trace has
        # been copied: a connection that closed first would checkpoint its
        # sidecars away before they were taken.
        holder = sqlite3.connect(src)
        holder.execute("SELECT count(*) FROM meta").fetchone()
        holders.append(holder)
        for suffix in ("", "-wal", "-shm"):
            one = src.with_name(src.name + suffix)
            if one.exists():
                out = traces / (f"{run}.db" + suffix)
                shutil.copy2(one, out)
                out.chmod(0o644)
    for holder in holders:
        holder.close()
    shutil.rmtree(staging)
    return {"runs": [run for run, _ in DRY_RUNS], "of_run": of_run,
            "key_id": Key.load_or_create(store).key_id}


def _sidecars(traces: Path, suffix: str) -> int:
    """How many `<run>.db<suffix>` files sit beside the databases.

    By NAME, not by `Path.suffix`: `Path("x.db-wal").suffix` is `".db-wal"`,
    so the obvious `p.suffix == "-wal"` is structurally false and counts
    zero over any store at all. It shipped that way and §4 would have
    reported a 273-sidecar copy as holding none -- the rehearsal could not
    catch it, because a fabricated store had no sidecars either. It has them
    now (`fabricate`), and this counts them by the name they actually have.
    """
    if not traces.is_dir():
        return 0
    return sum(1 for one in traces.iterdir() if one.name.endswith(suffix))


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
        # Part A's `_keep` scrubs `self.token` and `self.fresh`; part C
        # holds a SET of values (R15) and overrides `_keep` to scrub all of
        # them, so these two stay empty strings and the parent's own
        # replacement is a no-op over text this class has already cleaned.
        self.token = self.fresh = ""
        #: Every distinct `TOKEN_VAR` value in the copy, sorted, and which
        #: trace holds which. Never printed, never written but as grep's
        #: argument.
        self.tokens: list[str] = []
        self.token_of: dict[str, str] = {}
        self.stems: list[str] | None = None
        # stdout as BYTES (what clause 4 compares) and as text (what is
        # parsed and kept). See `_run_split`.
        self.dry_out: bytes | None = None
        self.real_out: bytes | None = None
        self.dry_text: str | None = None
        self.real_text: str | None = None
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

    # -- phase 2: the copy, and the values it already holds ---------------
    def copy(self) -> dict:
        """The subject: `traces/` and `redaction.key` copied out of the live
        store, or fabricated traces when this is a rehearsal (P11). Then
        read once, through read-only connections: every trace's OWN
        `TOKEN_VAR` value, its `incomplete` and its `recorder`.

        `shutil.copytree` where P12 says `cp -a`: it copies with `copy2`, so
        modes and mtimes are preserved and the sidecars come with their
        databases, which is what P12 asks for. It differs from `cp -a` in
        two ways that do not arise here -- it follows symlinks rather than
        preserving them (the store holds none) and it does not preserve
        ownership (a copy read by the user who made it).

        Refused on a `.<run>.db.tmp` or an `incomplete` trace -- H4 is about
        COMPLETED traces, and a file another process holds open in WAL mode
        is not one this pass may claim to have rewritten (C8). Refused, too,
        on a trace whose `env` is not a dict or which names no `TOKEN_VAR`
        at all: either would drop silently out of the census, and a trace
        with no value of its own has no premise for `count-before` to check.

        The census of DISTINCT values is the subject, not a curiosity
        (R15): this box's token rotated over the store's life, so the sweep
        is over a SET and `count-before` asks each trace for ITS OWN value.
        """
        traces = self.store / "traces"
        if self.dry:
            decoys = [DRY_PREFIX + "".join(secrets.choice(_ALPHABET)
                                           for _ in range(DRY_BODY))
                      for _ in range(DRY_DECOYS)]
            made = fabricate(self.store, decoys)
        else:
            shutil.copytree(self.live / "traces", traces)
            shutil.copy2(self.live / "redaction.key",
                         self.store / "redaction.key")
            made = {"copied_from": "~/.sensorium"}
        made.pop("of_run", None)
        tmps = sorted(p.name for p in traces.glob(".*.db*.tmp"))
        if tmps:
            raise Refused(f"the copy holds {len(tmps)} in-flight tmp "
                          f"file(s): {', '.join(tmps[:5])}. Something was "
                          "writing to the store while it was copied")
        dbs = sorted(traces.glob("*.db"))
        if not dbs:
            raise Refused("the copy holds no `*.db`")
        self.stems = [p.stem for p in dbs]
        incomplete, unreadable, absent, census = [], [], [], {}
        recorders: dict = {}
        for path in dbs:
            meta = _read_meta(path)
            if meta.get("incomplete") is not False:
                incomplete.append(path.stem)
            rec = meta.get("recorder")
            recorders[rec] = recorders.get(rec, 0) + 1
            env = meta.get("env")
            if not isinstance(env, dict):
                unreadable.append(f"{path.stem} (env is "
                                  f"{type(env).__name__})")
                continue
            value = env.get(TOKEN_VAR)
            if value is None:
                absent.append(path.stem)
                continue
            self.token_of[path.stem] = value
            census[_sha8(value)] = census.get(_sha8(value), 0) + 1
        if incomplete:
            raise Refused(f"{len(incomplete)} trace(s) in the copy are in "
                          f"flight: {', '.join(incomplete[:5])}. H4 is "
                          "about completed traces")
        if unreadable:
            raise Refused(f"{len(unreadable)} trace(s) in the copy store no "
                          f"environment map: {', '.join(unreadable[:5])}. "
                          "A trace the census cannot read is a trace H4 "
                          "would be silently not about")
        if absent:
            raise Refused(f"{len(absent)} trace(s) in the copy name no "
                          f"{TOKEN_VAR}: {', '.join(absent[:5])}. Every "
                          "trace must hold a value of its own for the "
                          "premise to mean anything")
        self.tokens = sorted(set(self.token_of.values()))
        return {**made, "n_db": len(dbs),
                "distinct_tokens": len(self.tokens),
                "token_sha8": [{"sha8": sha8, "traces": n}
                               for sha8, n in sorted(census.items(),
                                                     key=lambda kv: -kv[1])],
                "token_lengths": sorted({len(v) for v in self.tokens}),
                "traces_holding_the_variable": len(self.token_of),
                "recorders": {str(k): v for k, v in sorted(
                    recorders.items(), key=lambda kv: -kv[1])},
                "n_wal": _sidecars(traces, "-wal"),
                "n_shm": _sidecars(traces, "-shm")}

    # -- phase 3: H4's premise ---------------------------------------------
    def _sweep(self) -> tuple[list[dict], dict]:
        """`_grep_counts` once per DISTINCT value, merged by path.

        Two readings, because the two questions differ: the merged rows are
        "does this file hold ANY of them", which is what clause 2 gates on,
        and the per-value map is "does this trace hold ITS OWN", which is
        what the premise asks. A `None` count for any single value makes the
        merged count `None` and keeps it there -- a file one sweep could not
        read is not a file that holds none, and clause 2 has to see the hole
        rather than a sum that quietly dropped a term.
        """
        per_value: dict = {}
        merged: dict = {}
        for value in self.tokens:
            rows = _grep_counts(value, [self.store], self.work)
            per_value[_sha8(value)] = {r["path"]: r["count"] for r in rows}
            for row in rows:
                path, count = row["path"], row["count"]
                if path not in merged:
                    merged[path] = count
                elif merged[path] is None or count is None:
                    merged[path] = None
                else:
                    merged[path] += count
        return ([{"path": path, "count": count}
                 for path, count in sorted(merged.items())], per_value)

    def count_before(self) -> dict:
        """Every `*.db` in the copy holds ITS OWN value at least once BEFORE
        the run. A PRECONDITION: "0 everywhere after" is true of a store
        that never held the secret, so a copy that does not carry it is not
        the store §9 describes and the run refuses rather than publishing a
        pass about nothing.

        Its own value and not the first trace's (R15): this box's token
        rotated, so asking all 273 traces for one trace's value would refuse
        262 of them over a fact about the calendar. The refusal names the
        census in digests -- never a value.
        """
        rows, per_value = self._sweep()
        bad = []
        for stem in self.stems or []:
            own = _sha8(self.token_of[stem])
            path = _rel(self.store / "traces" / f"{stem}.db", self.work)
            if not per_value.get(own, {}).get(path):
                bad.append(f"{stem} (sha8 {own}: "
                           f"{per_value.get(own, {}).get(path)})")
        if bad:
            census = ", ".join(f"{sha8} in {len(
                [s for s in self.token_of if _sha8(self.token_of[s]) == sha8]
            )} trace(s)" for sha8 in sorted({_sha8(v) for v in self.tokens}))
            raise Refused(
                f"{len(bad)} of {len(self.stems or [])} `*.db` in the copy "
                f"do not hold their own {TOKEN_VAR} value: "
                f"{', '.join(bad[:5])}"
                + (f" and {len(bad) - 5} more" if len(bad) > 5 else "")
                + f". The copy holds {len(self.tokens)} distinct value(s): "
                + census + ". H4's premise is that every trace holds the "
                "value its own environment names")
        held = [row for row in rows if row["count"]]
        return {"files": rows, "files_holding_a_value": len(held),
                "occurrences_total": sum(row["count"] or 0 for row in held),
                "values_swept": len(self.tokens)}

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
        raw = r["out"]
        text = None if raw is None else raw.decode("utf-8", "replace")
        setattr(self, f"{label}_out", raw)
        setattr(self, f"{label}_text", text)
        self._keep_stream(f"redact-{label}", text or "")
        self._keep_stream(f"redact-{label}.stderr", r["err"])
        if r["killed"]:
            raise RuntimeError(f"the {label} pass hit its "
                               f"{self.timers['redact']}s timer")
        rows = parse_lines(text) or {}
        lines = (text or "").splitlines()
        return {"rc": r["rc"], "seconds": r["seconds"], "killed": False,
                "lines": len(lines), "trace_lines": len(rows),
                "summary": next((ln for ln in lines if SUMMARY.match(ln)),
                                None),
                "stdout_bytes": len(raw or b""),
                "stdout_sha256": hashlib.sha256(raw or b"").hexdigest(),
                "stderr": r["err"][:4000],
                "values_total": sum(row["values"] or 0
                                    for row in rows.values()),
                "rows": rows}

    # -- phase 6: H4's clause 4 --------------------------------------------
    def compare(self) -> bool:
        """The two stdouts as the BYTES each command wrote -- never the
        decoded text, which a codec and a newline translation stand between
        (see `_run_split`). A pass that left no stdout raises, so the cell
        drops rather than reading two missing strings as equal."""
        if self.dry_out is None or self.real_out is None:
            raise RuntimeError("one of the two passes left no stdout")
        return self.dry_out == self.real_out

    # -- phase 7: H4's clause 2 --------------------------------------------
    def grep_after(self) -> dict:
        """`count-before`'s sweep again -- every distinct value, over the
        same root, merged the same way -- after the real run, and what is
        left of the sidecars, which `apply` unlinks with the inode it
        replaced (C7)."""
        rows, per_value = self._sweep()
        traces = self.store / "traces"
        return {"files": rows, "files_examined": len(rows),
                "files_holding_a_value": sum(1 for r in rows if r["count"]),
                "unreadable": sorted(r["path"] for r in rows
                                     if r["count"] is None),
                "per_value": {sha8: sum(c or 0 for c in counts.values())
                              for sha8, counts in per_value.items()},
                "values_swept": len(self.tokens),
                "n_wal": _sidecars(traces, "-wal"),
                "n_shm": _sidecars(traces, "-shm")}

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
            # `killed` travels with the row: `_run` leaves `rc: None` on a
            # timer, and a cell that read that as "did not exit 0" would
            # publish an infrastructure event as a trace the retrofit broke.
            # `_clause_three` drops on it instead.
            rows.append({"run": stem, "exit": r["rc"],
                         "killed": r["killed"],
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

    def _scrubbed(self, text: str) -> str:
        """Every value in the set replaced, not just one (R15). The command
        prints variable NAMES only, so this must be a no-op; it is what
        keeps a surprise out of a committed file rather than a reason to
        stop checking."""
        for value in self.tokens:
            text = text.replace(value, "<token>")
        return text

    def _keep(self, name: str, r: dict) -> None:
        """Part A's transcript keeper, over text this class has already
        scrubbed of the whole token SET. The parent scrubs `self.token` and
        `self.fresh`, which part C leaves empty: one instrument holds one
        value and part C holds several, so the set is taken out here and the
        parent's own replacement runs over text that no longer carries any
        of them."""
        super()._keep(name, {**r, "out": self._scrubbed(r["out"] or "")})

    def _keep_stream(self, name: str, text: str) -> None:
        """One captured stream, on disk, byte for byte -- no header, so the
        two `redact-*.txt` files can be diffed by hand and reach clause 4's
        own answer."""
        self.transcripts.mkdir(parents=True, exist_ok=True)
        path = self.transcripts / f"{name}.txt"
        path.write_text(self._scrubbed(text))
        os.chmod(path, 0o600)


# -- the run ---------------------------------------------------------------
def main() -> int:
    work = Path(os.environ["E16_WORK"]).resolve()
    out = Path(os.environ["E16_OUT"]).resolve()
    part = PartC(work, out, dry=os.environ.get("E16_DRY") == "1",
                 label=os.environ["E16_LABEL"])
    result = {"dry_run": part.dry, "started": time.time(),
              "dry_run_findings": dry_run_findings(),
              "amendments": list(AMENDMENTS),
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
        # A LIST of `{sha8, traces}`, and their count: the store holds more
        # than one value (R15) and a single digest would name whichever
        # trace happened to sort first.
        result["token_sha8"] = (copied or {}).get("token_sha8")
        result["distinct_tokens"] = (copied or {}).get("distinct_tokens")
        cells["H4"] = h4(part.stems, parse_lines(part.dry_text),
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
