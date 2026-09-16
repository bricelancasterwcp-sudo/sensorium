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
an `--all` pass; an in-flight trace is skipped (C8). Only
`live_tmp` touches the filesystem, to unlink a dead pid's leftover.
"""
import hashlib
import json
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
