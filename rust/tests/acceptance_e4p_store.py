#!/usr/bin/env python3
"""§1.3: the 61 originals into a FRESH store, and the proof the kept one was
never written.

THE STATEMENT IS PRE-REGISTERED; ITS EXECUTOR IS A LENS FACT
-----------------------------------------------------------
§1.3 locks the SQL:

    sqlite3 <kept>/traces/<run>.db "VACUUM INTO '<fresh>/traces/<run>.db'"

and says the executor is "either the `sqlite3` CLI, when one is on `PATH`,
or Python's `sqlite3` module executing the identical SQL -- §2 records which
was used and the SQLite library version, because they are lens facts and
neither changes the bytes the statement produces". There is no `sqlite3` CLI
on this box, so the module runs it; `engine` says so in the raw record
rather than leaving a reader to assume.

`VACUUM INTO` and not a file copy: it writes a checkpointed single-file
database, so any WAL content is folded into the destination and the
destination is complete on its own. The source is opened `mode=ro` here as
well -- the statement itself only reads, and the URI is the second lock on
the one input this record must not touch.

THREE PROOFS, NOT ONE
---------------------
1. **The kept store is unchanged**: every `.db`'s `st_mtime` and size,
   censused before and after the whole run, and compared FILE BY FILE. A
   census compared by count would call two different stores identical.
2. **Each copy is the original it claims to be**: the destination's
   `meta.run_id` is read back and must equal `<run>`. A mismatch is a
   refusal to start -- before any number, so the INFRASTRUCTURE kill (the
   locked §1.3 cites "kill 3" for it; the words "a refusal to start
   (before any number)" are what this module implements, and §2 files the
   cross-reference erratum).
3. **The fresh store holds only the copies**: a listing count taken the
   moment the loop opens.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4p_read import connect_ro, meta_value               # noqa: E402
from acceptance_lib import Refused, step                             # noqa: E402

#: §1.3's statement, with the one hole the SQL grammar leaves. `VACUUM INTO`
#: takes no bound parameter, so the destination is interpolated -- and
#: `vacuum_sql` refuses a path that could close the quote rather than
#: escaping one. Every path this record uses comes from an environment
#: variable, which is exactly the input a runner does not own.
VACUUM_INTO = "VACUUM INTO '{dst}'"


def vacuum_sql(dst: Path) -> str:
    """§1.3's statement for one destination, or a refusal.

    Refused rather than escaped: an escaped path would still RUN, and the
    only paths this record can legitimately be given are ones that need no
    escaping. A quote or a newline in a store path is a mistake in the
    launcher, and finding it before 61 copies is the cheap moment.
    """
    text = str(dst)
    if "'" in text or '"' in text:
        raise Refused(f"the destination path carries a quote and cannot be "
                      f"interpolated into §1.3's statement: {text!r}")
    if "\n" in text or "\r" in text:
        raise Refused(f"the destination path carries a newline and cannot be "
                      f"interpolated into §1.3's statement: {text!r}")
    return VACUUM_INTO.format(dst=text)


def sqlite3_cli() -> str | None:
    """The `sqlite3` CLI, if there is one. `None` on this box -- recorded,
    not assumed, because the executor is a lens fact §2 publishes."""
    return shutil.which("sqlite3")


def traces_dir(store: Path) -> Path:
    return Path(store) / "traces"


def check_the_originals(kept: Path, rows) -> dict:
    """§1.1's re-check, before the loop opens and before anything is copied.

    "All 61 run ids are distinct, and every one names an existing
    `<run>.db` under the kept store ... re-checked by the runner before the
    loop opens; a missing or duplicated original is a refusal to start, not
    a smaller N."

    EVERY missing id is named in one refusal. A refusal that named the first
    would cost one full re-copy per missing file to discover the rest.
    """
    runs = [r for _i, _n, _t, r in rows]
    seen, duplicates = set(), []
    for run in runs:
        (duplicates.append(run) if run in seen else seen.add(run))
    if duplicates:
        raise Refused(f"§1.1's table has duplicated run id(s) "
                      f"{sorted(set(duplicates))}: the 61 originals must be "
                      f"distinct, and a duplicate is a refusal to start")
    missing = [r for r in runs if not (traces_dir(kept) / f"{r}.db").is_file()]
    if missing:
        raise Refused(f"{len(missing)} of §1.1's {len(runs)} originals are "
                      f"not in the kept store {traces_dir(kept)}: {missing}; "
                      "a missing original is a refusal to start, not a "
                      "smaller N")
    return {"n": len(runs), "distinct": len(set(runs)),
            "kept_traces": str(traces_dir(kept)), "all_present": True}


def copy_one(src: Path, dst: Path, run_id: str) -> dict:
    """One original, copied by §1.3's statement and verified by its own id.

    The engine, the statement and the SQLite version are recorded for every
    copy -- not once for the run -- so a fallback that fired on copy 34 is
    visible rather than averaged away.
    """
    src, dst = Path(src), Path(dst)
    if not src.is_file():
        raise Refused(f"the original {run_id} is not in the kept store "
                      f"({src}); a missing original is a refusal to start, "
                      "not a smaller N")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise Refused(f"the fresh store already holds {dst.name}: §1.3's "
                      "fresh store holds ONLY the 61 copies, so a "
                      "destination that exists is a leftover, not a re-copy")
    sql = vacuum_sql(dst)
    cli = sqlite3_cli()
    t0 = time.monotonic()
    if cli:
        proc = subprocess.run([cli, str(src), sql], capture_output=True,
                              text=True, timeout=600)
        engine = "sqlite3 CLI"
        if proc.returncode != 0:
            raise Refused(f"§1.3's statement failed for {run_id}: "
                          f"{cli} exit {proc.returncode}: "
                          f"{(proc.stderr or '').strip()[:200]}")
    else:
        # The IDENTICAL SQL. `mode=ro` on the source is this module's own
        # second lock on the kept store; the statement only reads it either
        # way, and a URI that could not open read-only would refuse here
        # rather than write.
        con = connect_ro(src)
        try:
            con.execute(sql)
        finally:
            con.close()
        engine = "python sqlite3 module"
    wall = time.monotonic() - t0
    got = meta_value(_meta_of(dst).get("run_id"))
    if got != run_id:
        raise Refused(f"the copy of {run_id} carries meta.run_id {got!r}: "
                      "§1.3 verifies each copy is the original it claims to "
                      "be, and a mismatch is a refusal to start -- never a "
                      "silently renamed file")
    return {"run": run_id, "src": str(src), "dst": str(dst),
            "engine": engine, "statement": sql,
            "sqlite_version": sqlite3.sqlite_version,
            "sqlite3_cli": cli, "copied": True,
            "src_bytes": src.stat().st_size, "dst_bytes": dst.stat().st_size,
            "wall_s": round(wall, 3), "verified_run_id": got}


def _meta_of(db: Path) -> dict:
    con = connect_ro(db)
    try:
        return dict(con.execute("select key, value from meta"))
    finally:
        con.close()


def copy_originals(kept: Path, fresh: Path, rows) -> dict:
    """§1.3's copy, for every row of §1.1, before the loop opens."""
    check_the_originals(kept, rows)
    copies = []
    for _index, _name, _target, run in rows:
        copies.append(copy_one(traces_dir(kept) / f"{run}.db",
                               traces_dir(fresh) / f"{run}.db", run))
    listing = sorted(p.name for p in traces_dir(fresh).glob("*"))
    expected = sorted(f"{r}.db" for _i, _n, _t, r in rows)
    out = {
        "copied": len(copies), "copies": copies,
        "engines": sorted({c["engine"] for c in copies}),
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite3_cli": sqlite3_cli(),
        "fresh_listing": listing,
        "fresh_listing_n": len(listing),
        "fresh_holds_only_the_copies": listing == expected,
        "unexpected_in_fresh": [n for n in listing if n not in expected],
        "bytes_copied": sum(c["dst_bytes"] for c in copies),
    }
    step(f"§1.3: {out['copied']} original(s) copied by {out['engines']} "
         f"({out['bytes_copied']} byte(s)); the fresh store holds "
         f"{out['fresh_listing_n']} file(s), only-the-copies="
         f"{out['fresh_holds_only_the_copies']}")
    return out


# ------------------------------------------------------- the read-only proof

def store_census(store: Path) -> dict:
    """Every `.db` under `<store>/traces`, with its size and `st_mtime_ns`.

    `st_mtime_ns` and not `st_mtime`: a float second can round two different
    writes to one number, and this census exists to catch exactly one write.
    """
    traces = traces_dir(store)
    files = {}
    if traces.is_dir():
        for path in sorted(traces.glob("*.db")):
            stat = path.stat()
            files[path.name] = {"bytes": stat.st_size,
                                "mtime_ns": stat.st_mtime_ns}
    return {"store": str(store), "traces": str(traces),
            "exists": traces.is_dir(), "n": len(files), "files": files,
            "taken_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def census_diff(before: dict, after: dict) -> list[str]:
    """Every way the two censuses differ, named. Empty is the proof §1.3
    asks for; anything else is reported file by file, because "one mtime
    moved" and "the store was rewritten" must not read the same."""
    out = []
    b, a = before.get("files") or {}, after.get("files") or {}
    for name in sorted(set(b) - set(a)):
        out.append(f"{name} was REMOVED from the kept store")
    for name in sorted(set(a) - set(b)):
        out.append(f"{name} APPEARED in the kept store")
    for name in sorted(set(a) & set(b)):
        if b[name]["mtime_ns"] != a[name]["mtime_ns"]:
            out.append(f"{name}: st_mtime_ns {b[name]['mtime_ns']} -> "
                       f"{a[name]['mtime_ns']}")
        if b[name]["bytes"] != a[name]["bytes"]:
            out.append(f"{name}: size {b[name]['bytes']} -> "
                       f"{a[name]['bytes']}")
    return out


__all__ = ["VACUUM_INTO", "census_diff", "check_the_originals", "connect_ro",
           "copy_one", "copy_originals", "sqlite3_cli", "store_census",
           "traces_dir", "vacuum_sql"]
