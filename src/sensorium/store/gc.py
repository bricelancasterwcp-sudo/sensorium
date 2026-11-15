"""Delete traces the store no longer needs to keep.

``gc`` removes a trace when it is older than the age limit, past the keep
count, or what has to go to bring the store under its size budget. A pinned
run and the most recent run are never deleted, even when that leaves the
store over the count or the budget. ``--dry-run`` prints the same set and
deletes nothing.

Pins live in ``$SENSORIUM_DIR/pins.json`` (``{"runs": [...]}``, mode 0600),
outside any trace file. Automatic cleanup after a recording calls
``maybe_auto``, which is a no-op unless a retention rule is set in the
environment or the config file, and which never changes the recorded
program's exit status.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from sensorium.limits import LimitsError, store_policy


class GcError(ValueError):
    """A retention rule or a pins file that cannot be acted on."""


@dataclass(frozen=True)
class Item:
    path: Path
    run_id: str
    mtime: float
    size: int


@dataclass(frozen=True)
class Plan:
    victims: tuple[Item, ...]
    kept: tuple[Item, ...]
    protected: frozenset[str]
    total_before: int


def format_bytes(n: int) -> str:
    n = int(n)
    for unit, step in (("GiB", 1024 ** 3), ("MiB", 1024 ** 2), ("KiB", 1024)):
        if abs(n) >= step:
            return f"{n / step:.1f} {unit}"
    return f"{n} B"


def _root(environ: dict | None = None) -> Path:
    env = os.environ if environ is None else environ
    raw = env.get("SENSORIUM_DIR")
    return Path(raw) if raw else Path.home() / ".sensorium"


def _pins_path(root: Path) -> Path:
    return root / "pins.json"


def load_pins(root: Path | None = None) -> list[str]:
    """Run ids ``gc`` must not delete. A missing file is an empty list.

    A file that exists and is not ``{"runs": [...]}`` is an error: treating
    it as empty would delete a run the user had pinned.
    """
    path = _pins_path(root or _root())
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise GcError(f"cannot read {path}: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        raise GcError(f"{path} must be a JSON object with a runs list")
    runs = []
    for item in data["runs"]:
        if not isinstance(item, str) or not item or item != Path(item).name:
            raise GcError(f"{path} has a run id that is not a single name")
        runs.append(item)
    return runs


def save_pins(runs: list[str], root: Path | None = None) -> Path:
    root = root or _root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = _pins_path(root)
    payload = json.dumps({"runs": runs}, indent=2) + "\n"
    tmp = path.with_suffix(".json.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    return path


def _trace_size(path: Path) -> int:
    total = path.stat().st_size
    for ext in ("-wal", "-shm"):
        side = Path(str(path) + ext)
        if side.is_file():
            total += side.stat().st_size
    return total


def list_traces(root: Path | None = None) -> list[Item]:
    """``*.db`` files already in the store. Does not create the directory."""
    directory = (root or _root()) / "traces"
    if not directory.is_dir():
        return []
    base = directory.resolve()
    found = []
    for path in directory.glob("*.db"):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved.parent != base:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        found.append(Item(path, path.stem, stat.st_mtime, _trace_size(path)))
    return found


def plan(policy, *, root: Path | None = None,
         now: float | None = None) -> Plan:
    """Which traces ``policy`` would delete. Reads pins; deletes nothing."""
    root = root or _root()
    items = list_traces(root)
    pins = set(load_pins(root))
    if not items:
        return Plan((), (), frozenset(pins), 0)
    newest_first = sorted(items, key=lambda item: (item.mtime, item.run_id),
                          reverse=True)
    protected = set(pins)
    protected.add(newest_first[0].run_id)
    victims: dict[str, Item] = {}
    moment = time.time() if now is None else now
    if policy.older_than is not None:
        cutoff = moment - policy.older_than
        for item in newest_first:
            if item.run_id not in protected and item.mtime < cutoff:
                victims[item.run_id] = item
    if policy.keep is not None:
        kept = 0
        for item in newest_first:
            if item.run_id in victims:
                continue
            if kept < policy.keep:
                kept += 1
                continue
            if item.run_id not in protected:
                victims[item.run_id] = item
    remaining = [item for item in newest_first if item.run_id not in victims]
    if policy.max_bytes is not None:
        total = sum(item.size for item in remaining)
        for item in reversed(remaining):
            if total <= policy.max_bytes:
                break
            if item.run_id in protected:
                continue
            victims[item.run_id] = item
            total -= item.size
    victim_list = tuple(item for item in reversed(newest_first)
                        if item.run_id in victims)
    kept_list = tuple(item for item in newest_first
                      if item.run_id not in victims)
    return Plan(victim_list, kept_list, frozenset(protected),
                sum(item.size for item in items))


def _unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
    for ext in ("-wal", "-shm"):
        Path(str(path) + ext).unlink(missing_ok=True)


def vacuum(path: Path) -> None:
    """Checkpoint and rebuild one remaining trace so deleted pages are gone."""
    conn = sqlite3.connect(path)
    try:
        conn.isolation_level = None
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
    finally:
        conn.close()


def apply(chosen: Plan, *, dry_run: bool = False) -> tuple[int, int, list[str]]:
    """Delete ``chosen.victims``. Returns ``(count, bytes, vacuum notes)``.

    Dry-run deletes nothing and does not vacuum. Vacuum runs only after a
    real deletion, and only on the traces that remain.
    """
    if dry_run or not chosen.victims:
        return 0, 0, []
    freed = 0
    for item in chosen.victims:
        freed += item.size
        _unlink(item.path)
    notes = []
    for item in chosen.kept:
        try:
            vacuum(item.path)
        except sqlite3.Error as e:
            notes.append(f"{item.run_id}: {e}")
    return len(chosen.victims), freed, notes


def render(chosen: Plan, *, dry_run: bool, deleted: int, freed: int,
           notes: list[str]) -> str:
    if not chosen.victims:
        return "nothing to delete"
    lines = []
    verb = "would delete" if dry_run else "deleted"
    shown = chosen.victims if dry_run else chosen.victims
    for item in shown:
        lines.append(f"{verb} {item.run_id} ({format_bytes(item.size)})")
    if dry_run:
        total = sum(item.size for item in chosen.victims)
        lines.append(
            f"dry-run: {len(chosen.victims)} traces, {format_bytes(total)}")
    else:
        lines.append(f"deleted {deleted} traces, freed {format_bytes(freed)}")
    return "\n".join(lines)


def maybe_auto(environ: dict | None = None) -> str | None:
    """Apply the configured retention rule. ``None`` when there is no rule
    or nothing to delete. A failure here is the caller's to report."""
    policy = store_policy(environ=environ)
    if policy.is_empty():
        return None
    chosen = plan(policy, root=_root(environ))
    if not chosen.victims:
        return None
    deleted, freed, _notes = apply(chosen)
    if not deleted:
        return None
    return (f"sensorium: gc deleted {deleted} traces, "
            f"freed {format_bytes(freed)}")


def _policy_from_args(args):
    from sensorium.limits import parse_duration
    older = None if args.older_than is None else parse_duration(args.older_than)
    return store_policy(max_bytes=args.max_bytes, keep=args.keep,
                        older_than=older)


def gc_main(args) -> int:
    try:
        policy = _policy_from_args(args)
    except (LimitsError, GcError) as e:
        print(f"error: {e}", file=_err())
        return 2
    if policy.is_empty():
        print("error: gc needs --older-than, --keep, or --max-bytes "
              "(or the same rule in the environment or the config file)",
              file=_err())
        return 2
    try:
        chosen = plan(policy)
    except GcError as e:
        print(f"error: {e}", file=_err())
        return 2
    deleted, freed, notes = apply(chosen, dry_run=args.dry_run)
    print(render(chosen, dry_run=args.dry_run, deleted=deleted, freed=freed,
                 notes=notes))
    for note in notes:
        print(f"sensorium: vacuum failed: {note}", file=_err())
    return 0


def pin_main(args) -> int:
    from sensorium import paths
    try:
        path = paths.find_trace(args.run)
        runs = load_pins()
    except (paths.TraceLookupError, GcError) as e:
        print(f"error: {e}", file=_err())
        return 2
    run_id = path.stem
    if run_id not in runs:
        runs.append(run_id)
        save_pins(runs)
    print(f"pinned: {run_id}")
    return 0


def unpin_main(args) -> int:
    from sensorium import paths
    try:
        runs = load_pins()
    except GcError as e:
        print(f"error: {e}", file=_err())
        return 2
    target = args.run
    try:
        target = paths.find_trace(args.run).stem
    except paths.TraceLookupError:
        target = args.run
    if target not in runs:
        print(f"error: {args.run!r} is not pinned", file=_err())
        return 2
    save_pins([run for run in runs if run != target])
    print(f"unpinned: {target}")
    return 0


def _err():
    import sys
    return sys.stderr


def add_parsers(sub) -> None:
    gc = sub.add_parser(
        "gc", help="delete traces the store no longer needs",
        description="Removes traces by age, by how many to keep, or by a "
                    "total size. A pinned trace and the most recent trace "
                    "are kept even when that exceeds the rule. With no rule "
                    "on the command, in the environment, or in the config "
                    "file, nothing is deleted.",
        epilog="exit: 0 done, 2 fix the call")
    gc.add_argument("--dry-run", action="store_true",
                    help="print the traces that would be deleted and delete nothing")
    gc.add_argument("--older-than", default=None,
                    help="delete traces older than this duration (30d, 12h, 2w, 45m)")
    gc.add_argument("--keep", default=None,
                    help="how many of the newest traces to keep; must be >= 1")
    gc.add_argument("--max-bytes", default=None,
                    help="delete the oldest traces until the store is under this size")
    gc.set_defaults(func=gc_main)

    pin = sub.add_parser(
        "pin", help="keep one trace from gc",
        description="Records the run id in the store's pins file. gc never "
                    "deletes a pinned trace.",
        epilog="exit: 0 pinned, 2 fix the call")
    pin.add_argument("run", help="a run id, a unique prefix, or last")
    pin.set_defaults(func=pin_main)

    unpin = sub.add_parser(
        "unpin", help="drop a trace from the pins file",
        description="Removes the run id from the store's pins file. The "
                    "trace itself is left where it is.",
        epilog="exit: 0 unpinned, 2 fix the call")
    unpin.add_argument("run", help="a run id, a unique prefix, or last")
    unpin.set_defaults(func=unpin_main)
