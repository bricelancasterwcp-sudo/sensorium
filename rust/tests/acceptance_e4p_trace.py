#!/usr/bin/env python3
"""The E4′ reader's TRACE-STORE half: what a recorded run says, and what a
target's shim directory holds.

Split out of `acceptance_e4p_read.py` on 2026-09-08, at the `# ---- the
store` banner it already carried, when the debts slice's own edit took that
file to 796 of an 800-line ceiling (design R9). A pure move, and the seam is
the material's: everything above the banner parses what `sensorium refocus`
PRINTED, and everything here opens what it RECORDED -- a trace, read-only,
and the hard-linked shims under a cargo target. `acceptance_e4p_read`
imports every name back, so no consumer of either module changes.

Nothing here decides anything: a store this record reads is opened
`mode=ro`, an unread field is `None` and never `0`, and a directory that is
not there is `None` entries rather than an empty one.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ------------------------------------------------------------- the store

def connect_ro(db: Path) -> sqlite3.Connection:
    """A trace, opened READ-ONLY through the URI form.

    Every store this record reads -- the kept one above all -- is opened
    this way, so a reader bug cannot write to the input it is measuring.
    """
    return sqlite3.connect(f"file:{Path(db)}?mode=ro", uri=True)


def meta_value(raw):
    """One `meta` cell, decoded the way the store encodes it: `set_meta`
    writes `json.dumps(value)`, so a run id sits in the column QUOTED. Read
    raw, `"r-1"` would never equal `r-1` and every pair would come back
    unlinked -- and a run with no pair is a STOP."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def trace_meta_ro(db: Path) -> dict:
    """One trace's whole meta table, JSON-decoded, read-only."""
    path = Path(db)
    if not path.is_file():
        return {}
    con = connect_ro(path)
    try:
        rows = dict(con.execute("select key, value from meta"))
    finally:
        con.close()
    return {k: meta_value(v) for k, v in rows.items()}


def pair_candidates(traces_dir, run_id: str, launched_at: float) -> dict:
    """§1.4's PAIR RULE **including R2's child filter**, applied by the
    instrument rather than trusted.

    A trace qualifies on three counts, all necessary: it names `run_id` in
    `refocus_of`, its own recording started at or after `launched_at`, and
    R2 has not set it aside as the child of another candidate. Deliberately
    NOT the CLI's own `find_pair`: this is the check that the CLI paired the
    two traces the STORE supports, so it reads the store itself -- and the
    child rule is re-applied here for the same reason, from the same pid /
    ppid facts (`refocus_rust.find_pair`).

    Every list is returned. "an earlier refocus of the same original", "no
    trace at all" and "a child was excluded" are three different findings.
    """
    linked, qualifying, unreadable = [], [], []
    for path in sorted(Path(traces_dir).glob("*.db")):
        try:
            con = connect_ro(path)
            try:
                rows = dict(con.execute(
                    "select key, value from meta where key in "
                    "('refocus_of', 'start_ts', 'pid', 'ppid')"))
            finally:
                con.close()
        except sqlite3.DatabaseError:
            unreadable.append(path.stem)
            continue
        of = meta_value(rows.get("refocus_of"))
        if of != run_id:
            continue
        linked.append(path.stem)
        started = meta_value(rows.get("start_ts"))
        if not isinstance(started, (int, float)) or started < launched_at:
            continue
        qualifying.append((path.stem, _pid(rows.get("pid")),
                           _pid(rows.get("ppid"))))
    # R2, from `refocus_rust.find_pair`: `pid is not None` keeps the
    # unidentified traces OUT of the set, so an unknown parent can never
    # match an unknown pid and a trace that records neither is a candidate.
    pids = {p for _n, p, _pp in qualifying if p is not None}
    candidates = [n for n, p, pp in qualifying
                  if not (pp in pids and pp != p)]
    children = [n for n, p, pp in qualifying if pp in pids and pp != p]
    return {"linked": sorted(linked), "qualifying": sorted(candidates),
            "children": sorted(children), "unreadable": unreadable,
            "n": len(candidates), "launched_at": launched_at}


def _pid(raw):
    value = meta_value(raw)
    return value if isinstance(value, int) else None


# ---------------------------------------------------------- H4's census

def shim_census(target: Path, driver: Path) -> dict:
    """H4: `<CARGO_TARGET_DIR>/sensorium/shim/*/cargo-sensorium`.

    Three numbers that are printed SEPARATELY and never summed into each
    other: how many entries there are, how many DISTINCT inodes they hold,
    and the bytes -- counted **once per inode**. Under R3 the shims are hard
    links to one file, so a byte total that summed the per-entry sizes would
    report 61 copies of a binary that exists once, which is the measurement
    error this endpoint is about.

    A directory that is not there is `None` entries, never 0: a target that
    never keyed a shim and one that keyed an empty shim are different facts.
    `st_dev` is recorded beside the inode comparison because a link across a
    filesystem boundary is impossible rather than wrong -- §1.2 says the
    finding branch does not apply where the devices differ.
    """
    shim = Path(target) / "sensorium" / "shim"
    drv = Path(driver)
    driver_stat = drv.stat() if drv.is_file() else None
    out = {
        "dir": str(shim), "exists": shim.is_dir(),
        "driver": str(drv),
        "driver_inode": driver_stat.st_ino if driver_stat else None,
        "driver_dev": driver_stat.st_dev if driver_stat else None,
        "driver_bytes": driver_stat.st_size if driver_stat else None,
        "keys": None, "entries": None, "distinct_inodes": None,
        "bytes_once_per_inode": None, "linked_to_the_driver": None,
        "not_linked": None, "same_device": None, "names": None,
        "keys_without_a_binary": None, "entries_cover_every_key": None,
    }
    if not shim.is_dir():
        return out
    keys = sorted(p.name for p in shim.iterdir() if p.is_dir())
    seen, linked, unlinked, devices, total = {}, [], [], set(), 0
    entries, empty = 0, []
    for key in keys:
        binary = shim / key / "cargo-sensorium"
        if not binary.is_file():
            # NAMED, never skipped into silence. A key directory with no
            # binary has no `st_ino`, so H4's gate -- "for every key" --
            # is not met; dropping it here would take it out of the
            # DENOMINATOR too and let `linked == entries` read as though
            # every key had linked. That is the failure `4edd5c7` makes
            # reachable: the install created the directory and could not
            # place the binary.
            empty.append(key)
            continue
        st = binary.stat()
        entries += 1
        devices.add(st.st_dev)
        if st.st_ino not in seen:
            seen[st.st_ino] = st.st_size
            total += st.st_size
        if driver_stat is not None and st.st_ino == driver_stat.st_ino:
            linked.append(key)
        else:
            unlinked.append(key)
    out.update({
        "keys": len(keys), "entries": entries,
        "keys_without_a_binary": empty,
        "entries_cover_every_key": entries == len(keys),
        "distinct_inodes": len(seen), "bytes_once_per_inode": total,
        "linked_to_the_driver": len(linked), "not_linked": sorted(unlinked),
        "same_device": (None if driver_stat is None or not devices
                        else devices == {driver_stat.st_dev}),
        "devices": sorted(devices), "names": keys,
    })
    return out


__all__ = ["connect_ro", "meta_value", "pair_candidates",
           "shim_census", "trace_meta_ro"]
