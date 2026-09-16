"""`sensorium redact`'s JUDGEMENT: what a trace already on disk becomes.

Parts A and B put rule v1 at the three recorders' writers, so nothing NEW
reaches disk in plaintext; this is the other half. All 273 traces this box
holds predate the rule, each with a live token in `meta.env` at 0644. `plan()`
decides what one becomes -- the environment and its hash, every changed
payload row, `unwind_exc`, output row and `children` element, the stamp, the
counts (C2) -- and returns a `Plan`. It writes NOTHING (C14, P1): `apply()` is
the only writer, and `--dry-run` is this function alone.

The rule is not re-implemented: `redact.fires` and `redact_values` answer for
the retrofit what they answer for the recorders, which is what makes a second
pass idempotent (C5). **The environment pass is the NAME rule only** (C1) -- a
retrofit doing more to an old trace than a recorder does to a new one would be
two rules wearing one name -- and `redact.env` refuses by its docstring to
meet the already redacted environment a re-visit always is, so `_env_pass` is
its loop with two skips (C5, P4). **`env_hash` is reproduced BEFORE it is
recomputed** (C3): a retrofit that cannot get the stored hash out of the
stored environment cannot claim the new one is the same formula.

The stamp is always `by: "retrofit"` (C6) and its `values` ADDITIVE (P2): a
content hit leaves text rather than a marker, so what a trace HOLDS cannot be
recounted and the sum of the hands' counts is honest. It is written when
anything else changed or the trace was not already `mode: "on"` -- a pre-rule
or `mode: "off"` trace is stamped even when nothing fired (P5), an UNKEYED one
becomes keyed (P6), a settled one left alone. Rows go in id order, a RETURN
under the name `code_objects` holds (P7), an unchanged one unwritten (P8).

Nothing escapes as an exception: a newer format, a format-4 trace missing
required meta, an unknown lang (those three in `db.open_trace`'s words minus
its leading path), a non-reproducing hash, another key, a live tmp, a file
SQLite cannot open, a file another process removed, a meta row that is not
JSON -- each is a sentence on the `Plan` (C9), so one refusal does not end
an `--all` pass; an in-flight trace is skipped (C8). Of the judgement
only `live_tmp` touches the filesystem, to unlink a dead pid's leftover.

`apply()` is the other half and the only hand that writes: C7's backup ->
rewrite -> checkpoint -> fsync -> rename -> sidecars, on a private copy, so
the original is whole up to one atomic rename. A row the plan did not name
is a row it does not touch.
"""
import hashlib
import json
import os
import sqlite3
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from sensorium import redact
from sensorium import redact_values as rv
from sensorium.redact_key import Key, _pid_alive
from sensorium.store import db
from sensorium.ts.invocation import env_hash as _kv_env_hash

#: The rewrite's tmp is `.<run>.db.redact.<pid>.tmp` beside the trace: a
#: dotfile, so every glob for `*.db` walks past it.
TMP_SUFFIX = ".redact"

#: What SQLite leaves beside a WAL database; a result carries neither.
_SIDECARS = ("-wal", "-shm")

#: The recorders whose `env_hash` is the sorted `k=v` join. An absent
#: `lang` predates the key and is the Python recorder's.
KV_LANGS = frozenset({"rust", "typescript"})

#: What a trace is left at, and what `tightens` measures against (C11).
TIGHT = 0o600

#: The writers' own separators (`store/writer.add_event`), so a row this
#: rewrites differs from the recorder's only where the rule fired.
_SEP = (",", ":")

_SKIPPED = "in flight (incomplete)"


@dataclass(frozen=True)
class Plan:
    """One trace's whole future, in memory: `apply()` touches nothing this
    does not name, and a plan that refuses or skips names nothing at all.
    `env_names` is what the environment pass took and `values` what every
    other site did; `meta` is the keys to (re)write (a subset of `env`,
    `env_hash`, `redaction`, `children`); the row maps hold FINISHED text.
    """
    path: Path
    run: str
    lang: str
    refused: str | None = None
    skipped: str | None = None
    env_names: tuple[str, ...] = ()
    values: int = 0
    meta: dict = field(default_factory=dict)
    payloads: dict[int, str] = field(default_factory=dict)
    unwinds: dict[int, str] = field(default_factory=dict)
    outputs: dict[int, str] = field(default_factory=dict)
    mode_before: int = TIGHT

    @property
    def rewrites(self) -> bool:
        return bool(self.meta or self.payloads or self.unwinds or self.outputs)

    @property
    def tightens(self) -> bool:
        return self.mode_before != TIGHT

    @property
    def changes(self) -> bool:
        return (not self.refused and not self.skipped
                and (self.rewrites or self.tightens))


def env_hash_for(lang: str, env: Mapping[str, str]) -> str:
    """The `env_hash` `lang`'s recorder would write for `env`: two formulas,
    because it is a per-recorder identity (ruled 2026-09-02)."""
    if lang in KV_LANGS:
        return _kv_env_hash(env)
    return hashlib.sha256(
        json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]


def live_tmp(path: Path) -> str | None:
    """The refusal sentence if another `redact` holds this trace, else None.

    A killed retrofit leaves the original whole and its tmp behind (C7), and
    whose it was is in the name: a live pid holds the trace, a dead one left
    litter, swept here because no other moment is sure to come; a middle
    that is not a positive pid is nobody's to delete (`sweep_stale`)."""
    path = Path(path)
    prefix = f".{path.stem}.db{TMP_SUFFIX}."
    for tmp in sorted(path.parent.glob(f"{prefix}*.tmp")):
        try:
            pid = int(tmp.name.removeprefix(prefix).removesuffix(".tmp"))
        except ValueError:
            continue
        if pid <= 0:
            continue
        if _pid_alive(pid):
            return f"another redact is rewriting it (pid {pid})"
        try:
            tmp.unlink()
        except OSError:
            pass          # a leftover this cannot remove is not a refusal
    return None


def plan(path: Path, key: Key, knobs: redact.Knobs) -> Plan:
    """What `path` becomes under `key` and the caller's `knobs` -- the
    command's own environment as `redact_cmd` read it (C4). Nothing here
    reads `os.environ`, so a `SENSORIUM_NO_REDACT` in the shell running the
    retrofit cannot quietly turn it off."""
    # C4, forced at the one point the knobs enter: `redact.env` returns
    # early on `off` but `redact.fires` deliberately ignores it, so an
    # unforced `off` would take every firing value and then have
    # `redact.meta` stamp the two-key `mode: "off"` shape over an
    # environment whose plaintext is gone. Running the command IS the
    # decision (§7), and `mode` is always "on".
    knobs = replace(knobs, off=False)
    path = Path(path)
    run = path.stem
    try:
        mode_before = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        mode_before = TIGHT    # the open below refuses it, by name
    busy = live_tmp(path)
    if busy is not None:
        return Plan(path, run, "", refused=busy, mode_before=mode_before)
    try:
        conn = db.open_trace(path)
    except db.TraceFormatError as e:
        # Its sentence opens with the path; the per-trace line names the run.
        return Plan(path, run, "", mode_before=mode_before,
                    refused=str(e).removeprefix(f"{path} "))
    except sqlite3.DatabaseError as e:
        return Plan(path, run, "", mode_before=mode_before,
                    refused=f"not a database this sensorium can open: {e}")
    except ValueError as e:
        return Plan(path, run, "", mode_before=mode_before,
                    refused=f"meta is not JSON: {e}")
    except OSError as e:
        # A trace another process removed between the walk and this open:
        # an `--all` pass loses that trace and not the rest of them.
        return Plan(path, run, "", mode_before=mode_before,
                    refused=f"cannot open: {e}")
    try:
        return _judge(path, run, conn, key, knobs, mode_before)
    finally:
        conn.close()


def _judge(path: Path, run: str, conn: sqlite3.Connection, key: Key,
           knobs: redact.Knobs, mode_before: int) -> Plan:
    """`plan`'s decision with the connection open, split off so one
    `finally` closes it whichever way out is taken."""
    try:
        meta = db.all_meta(conn)
    except ValueError as e:
        return Plan(path, run, "", mode_before=mode_before,
                    refused=f"meta is not JSON: {e}")
    lang = meta.get("lang") or "python"
    if meta.get("incomplete") is True:
        # The Python recorder writes in place: another process holds this
        # open in WAL mode right now (C8).
        return Plan(path, run, lang, skipped=_SKIPPED, mode_before=mode_before)
    env = meta.get("env")
    env = env if isinstance(env, dict) else {}
    if env_hash_for(lang, env) != meta.get("env_hash"):
        return Plan(path, run, lang, mode_before=mode_before,
                    refused=f"env_hash does not reproduce under the "
                            f"{lang} formula")
    prev = meta.get("redaction")
    already_on = isinstance(prev, dict) and prev.get("mode") == "on"
    if already_on and prev.get("keyed") and prev.get("key_id") != key.key_id:
        # C5: a stamp naming one key must be true of every digest under it.
        return Plan(path, run, lang, mode_before=mode_before,
                    refused=f"digests under key {prev.get('key_id')}, the "
                            f"store's is {key.key_id or 'none'}; "
                            f"nothing rewritten")
    table = dict(prev.get("env") or {}) if already_on else {}
    stored, names = _env_pass(env, table, key, knobs)
    writes: dict = {}
    rv.install(key, knobs)
    try:
        payloads, unwinds, outputs, values = _rows(conn)
        values += _children(meta, writes)
    finally:
        rv.reset()
    if stored != env:
        writes["env"] = stored
        writes["env_hash"] = env_hash_for(lang, stored)
    if writes or payloads or unwinds or outputs or not already_on:
        before = prev.get("values", 0) if isinstance(prev, dict) else 0
        writes["redaction"] = {**redact.meta(key, knobs, table, by="retrofit"),
                               "values": before + values}
    return Plan(path, run, lang, env_names=tuple(names), values=values,
                meta=writes, payloads=payloads, unwinds=unwinds,
                outputs=outputs, mode_before=mode_before)


def _env_pass(env: dict, table: dict, key: Key,
              knobs: redact.Knobs) -> tuple[dict, list[str]]:
    """The environment to store and the names THIS pass took, sorted.
    `table` is the previous stamp's map, extended in place, and the two
    `continue`s are C5's and P4's."""
    stored = {n: v for n, v in env.items() if n != redact.KEY_VAR}
    names = []
    for name in sorted(stored):
        if name in table or stored[name] == redact.REDACTED:
            continue
        if not redact.fires(name, knobs):
            continue
        table[name] = key.digest(stored[name])
        stored[name] = redact.REDACTED
        names.append(name)
    return stored, names


def _rows(conn: sqlite3.Connection) -> tuple[dict, dict, dict, int]:
    """Every row the writers reach (C2) -- payloads, `unwind_exc`, output --
    as three id -> text maps, and what they now withhold. `task_id` is not
    named: the store's 18 oldest traces are format 1 and have no column."""
    payloads: dict[int, str] = {}
    unwinds: dict[int, str] = {}
    outputs: dict[int, str] = {}
    values = 0
    for eid, kind, text, qualname in conn.execute(
            "SELECT e.id, e.kind, e.payload, c.qualname FROM events e "
            "LEFT JOIN code_objects c ON c.id = e.code_id "
            "WHERE e.payload IS NOT NULL ORDER BY e.id").fetchall():
        obj = json.loads(text)
        new = _transform_payload(kind, obj, qualname)
        if new != obj:
            payloads[eid] = json.dumps(new, separators=_SEP)
            values += rv.count(new) - rv.count(obj)
    for fid, text in conn.execute(
            "SELECT id, unwind_exc FROM frames "
            "WHERE unwind_exc IS NOT NULL").fetchall():
        obj = json.loads(text)
        new = rv.exc(obj)
        if new != obj:
            unwinds[fid] = json.dumps(new, separators=_SEP)
            values += rv.count_capture(new) - rv.count_capture(obj)
    for oid, data in conn.execute(
            "SELECT id, data FROM output ORDER BY id").fetchall():
        after, hit = rv.text(data)
        if hit:
            outputs[oid] = after
            values += 1
    return payloads, unwinds, outputs, values


def _transform_payload(kind: str, obj: dict, qualname: str | None) -> dict:
    """One payload under rule v1, as its writer would have stored it: a NEW
    dict in the row's own key order, so one this leaves alone re-encodes
    byte for byte. A key outside the capture vocabulary is copied across,
    never guessed at; a RETURN with no `code_id` takes `value` (P7)."""
    out = {}
    for name, item in obj.items():
        if name in ("args", "deltas") and isinstance(item, dict):
            out[name] = {n: (rv.named(n, c) if isinstance(c, dict) else c)
                         for n, c in item.items()}
        elif name == "value" and isinstance(item, dict):
            out[name] = (rv.named_return(qualname, item)
                         if kind == "RETURN" and qualname else rv.value(item))
        elif name in ("exc", "thrown") and isinstance(item, dict):
            out[name] = rv.exc(item)
        else:
            out[name] = item
    return out


def _children(meta: dict, writes: dict) -> int:
    """`meta.children` under the CONTENT rule, element by element (R25), and
    how many elements it took: a command line has positions rather than
    bindings, so no name to read; `writes` gains the list only if it
    changed."""
    children = meta.get("children")
    if not isinstance(children, list):
        return 0
    after, hits = [], 0
    for command in children:
        if not isinstance(command, list):
            after.append(command)
            continue
        ruled = [rv.text(element) for element in command]
        hits += sum(1 for _text, hit in ruled if hit)
        after.append([text for text, _hit in ruled])
    if hits:
        writes["children"] = after
    return hits



def tmp_path_for(path: Path) -> Path:
    """The private copy `apply` builds this trace's replacement in:
    `TMP_SUFFIX`'s name, BESIDE the trace because `os.replace` is atomic
    only within one filesystem and a store can sit on any mount, and
    carrying this pid because that is what `live_tmp` reads to tell a
    live run's workspace from a killed one's litter."""
    path = Path(path)
    return path.with_name(f".{path.stem}.db{TMP_SUFFIX}.{os.getpid()}.tmp")


def _unlink_sidecars(path: Path) -> int:
    """`path`'s `-wal` and `-shm` removed, and how many there were.
    Absent is the ordinary case and not an error; any other `OSError` is
    raised, because a `-wal` this cannot remove is a file still holding
    the plaintext pages the rewrite just took out."""
    gone = 0
    for suffix in _SIDECARS:
        try:
            path.with_name(path.name + suffix).unlink()
        except FileNotFoundError:
            continue
        gone += 1
    return gone


def apply(p: Plan) -> None:
    """Put `p` on disk (C7, C11). The only writer in the retrofit.

    In a private copy and never in place: a retrofit dying mid-rewrite
    would leave a trace that is neither the old one nor the new. The copy
    is `Connection.backup` and not a byte copy of the `.db` because a
    committed row can be living in the `-wal` with nobody yet
    checkpointing it -- in the DATABASE and not in that file -- and a copy
    that drops it is a different trace (R37's lesson).

    The TRUNCATE checkpoint comes BEFORE the close, so the copy is whole
    in one file when it is renamed and the result carries no sidecars of
    its own. The directory is fsynced after the rename because a rename
    is durable only when its directory entry is. The ORIGINAL's
    `-wal`/`-shm` go LAST because they belong to the inode the rename
    displaced: unlinking them earlier would take pages the backup had not
    read, and a reader holding that inode keeps them open regardless.

    What a kill leaves: before the create, nothing; between it and the
    rename, the original whole and a tmp this pid owns, swept by the next
    `redact` to reach the trace once the pid is dead (C7); after it, the
    redacted trace, the displaced inode's sidecars gone in a `finally` so
    that only a signal ending the process outright can leave them. A
    failure this process sees rather than dies from clears its own tmp
    and is raised to the caller.
    """
    if p.refused or p.skipped or not p.changes:
        return
    if not p.rewrites:
        # C11: nothing to carry, so nothing is copied. A trace already
        # redacted but sitting at 0644 is CHANGED, and the sidecars are
        # tightened in place, not removed: nothing rewrote their pages.
        os.chmod(p.path, TIGHT)
        for suffix in _SIDECARS:
            sidecar = p.path.with_name(p.path.name + suffix)
            if sidecar.exists():
                os.chmod(sidecar, TIGHT)
        return
    tmp = tmp_path_for(p.path)
    try:
        # O_EXCL, so a taken name is a failure and never a file this
        # writes over blind; the pid in it makes that this process's own
        # leftover. Another live process's tmp was `plan`'s refusal (C7).
        os.close(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, TIGHT))
        _copy_and_rewrite(p, tmp)
        _fsync(tmp)
        os.chmod(tmp, TIGHT)
        os.replace(tmp, p.path)
        try:
            _fsync(p.path.parent)
        finally:
            # In a `finally` and not after the `try`: past the rename the
            # displaced inode's log is a file of plaintext pages beside a
            # redacted database, and SQLite will recover it OVER that
            # database -- serving the secrets back, or refusing the trace
            # as malformed. A directory fsync that fails, or a Ctrl-C
            # during an `--all` pass, must not be what leaves it there.
            _unlink_sidecars(p.path)
    except BaseException:
        # The database first: `_unlink_sidecars` raises on an OSError that
        # is not absence, and a tmp holding a whole plaintext copy must
        # not survive because its `-wal` could not be removed.
        tmp.unlink(missing_ok=True)
        _unlink_sidecars(tmp)
        raise


def _copy_and_rewrite(p: Plan, tmp: Path) -> None:
    """The copy, the rewrite and the checkpoint -- `apply`'s middle. One
    transaction, so the copy is never a half-redacted database even for an
    instant; the rows go in as the plan finished them, every judgement
    having been made before anything was opened for writing. The original
    is read and closed here and touched no further."""
    dst = sqlite3.connect(tmp)
    try:
        src = sqlite3.connect(p.path)
        try:
            src.backup(dst)
        finally:
            src.close()
        dst.executemany("UPDATE events SET payload = ? WHERE id = ?",
                        [(t, i) for i, t in p.payloads.items()])
        dst.executemany("UPDATE frames SET unwind_exc = ? WHERE id = ?",
                        [(t, i) for i, t in p.unwinds.items()])
        dst.executemany("UPDATE output SET data = ? WHERE id = ?",
                        [(t, i) for i, t in p.outputs.items()])
        for name, value in p.meta.items():
            db.set_meta(dst, name, value)
        dst.commit()
        dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        dst.close()
    # Past the checkpoint a surviving log is litter, not a reader's.
    _unlink_sidecars(tmp)


def _fsync(path: Path) -> None:
    """`path` on the platter, file or directory: a rename is only as
    durable as the two things it names."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
