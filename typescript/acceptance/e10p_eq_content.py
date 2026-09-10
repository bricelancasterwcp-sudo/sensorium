"""E10′-eq-content: the 372 pairs compared row for row, reported not gated.

Pre-registered in the record's §5.A on 2026-09-10, AFTER E10′-eq was read and
BEFORE this file existed, and it cannot move that verdict. The gate it stands
beside used `sensorium diff`, which compares causal structure — its own
verdict line says values, timing and LINE events were not compared — and two
ungated readings that are row COUNTS, not row CONTENTS. This closes that
distance: every row of every table, every column, both sides.

    e10p_eq_content.py <store> <log-A> <log-B>

`<store>` is the one store both sides' traces live in — side B's, with side
A's hard-linked into it, exactly as `e10p_eq.sh` leaves it. The two ingest
logs give the pairing, and they give it through `e10p_eq_report`'s own
`_side`/`_pairs`, so there is ONE pairing implementation in this directory
and this check cannot pair differently from the gate it reports beside.

A pair is `identical` when, for every table in `TABLES`, `SELECT * FROM
<t> ORDER BY rowid` is the same sequence on both sides, and `meta` differs in
nothing but `run_id`. `differing` names every (file, table) that is not, with
the rowid of the first row that differs — the rowid is read but NOT compared,
because the pre-registration compares `SELECT *`, and a rowid is the sequence
position this check already holds the two sides to.

`meta_keys_differing` carries the same meaning as the gate cell's field: the
union over every pair of the keys whose values differ, so the expected
reading is `["run_id"]` and a pair with only that is identical.

The four `E10P_EQ_{BIN,REV}_{A,B}` variables `e10p_eq.sh` already exports are
REQUIRED here and are written verbatim into `converter_a` / `converter_b`.
This is the cell whose provenance is least obvious -- it reads two stores
that some earlier command produced, and it can be pointed at any pair of
them -- so a cell without the two converters named is refused rather than
emitted: a comparison quoted without the writers it compared is not evidence
about either of them.
"""
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from pathlib import Path

from e10p_eq_report import TABLES, _pairs, _side
from lens import cell, emit, usage

#: Rows pulled per fetch. `fetchmany` returns a short batch only at the end
#: of a result set, so a length difference between the two batches is a real
#: difference between the two tables and never a misalignment.
BATCH = 20_000

#: Four at a time, as the gate's diffs were. Read-only throughout.
WORKERS = 4


def _first_difference(ca, cb, table: str):
    """The rowid of the first row of `table` that differs, or None."""
    ra = ca.execute(f"SELECT rowid, * FROM {table} ORDER BY rowid")
    rb = cb.execute(f"SELECT rowid, * FROM {table} ORDER BY rowid")
    while True:
        ba, bb = ra.fetchmany(BATCH), rb.fetchmany(BATCH)
        if not ba and not bb:
            return None
        for row_a, row_b in zip_longest(ba, bb):
            if row_a is None:
                return row_b[0]
            if row_b is None:
                return row_a[0]
            if row_a[1:] != row_b[1:]:
                return row_a[0]


def _meta_difference(ca, cb) -> list:
    """The meta keys whose values differ, `run_id` included if it does."""
    ma = dict(ca.execute("SELECT key, value FROM meta"))
    mb = dict(cb.execute("SELECT key, value FROM meta"))
    return sorted(k for k in set(ma) | set(mb) if ma.get(k) != mb.get(k))


def _one(store: Path, pair: tuple) -> dict:
    """One pair, every table and then meta. Read-only connections."""
    name, run_a, run_b = pair
    ca = sqlite3.connect(f"file:{store / 'traces' / (run_a + '.db')}?mode=ro", uri=True)
    cb = sqlite3.connect(f"file:{store / 'traces' / (run_b + '.db')}?mode=ro", uri=True)
    try:
        differing = []
        for table in TABLES:
            rowid = _first_difference(ca, cb, table)
            if rowid is not None:
                differing.append({"file": name, "table": table,
                                  "first_differing_rowid": rowid})
        meta = _meta_difference(ca, cb)
    finally:
        ca.close()
        cb.close()
    return {"file": name, "differing": differing, "meta_keys_differing": meta,
            "identical": not differing and set(meta) <= {"run_id"}}


#: Written verbatim into the cell; every one is required (see the docstring).
PROVENANCE = ("E10P_EQ_BIN_A", "E10P_EQ_REV_A", "E10P_EQ_BIN_B", "E10P_EQ_REV_B")


def _converters() -> tuple[dict, dict]:
    """The two converters this comparison is about, or refuse the call."""
    missing = [name for name in PROVENANCE if not os.environ.get(name)]
    if missing:
        usage(f"{', '.join(missing)} required: a comparison quoted without "
              "the converters it compared names neither of them")
    env = os.environ
    return ({"bin": env["E10P_EQ_BIN_A"], "rev": env["E10P_EQ_REV_A"]},
            {"bin": env["E10P_EQ_BIN_B"], "rev": env["E10P_EQ_REV_B"]})


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        usage("usage: e10p_eq_content.py <store> <log-A> <log-B>")
    conv_a, conv_b = _converters()
    store = Path(argv[0])
    if not (store / "traces").is_dir():
        usage(f"no traces/ under {store}: this is not a sensorium store")
    pairs = _pairs(_side(argv[1], "A")[0], _side(argv[2], "B")[0])
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda p: _one(store, p), pairs))
    keys, differing = set(), []
    for r in results:
        keys.update(r["meta_keys_differing"])
        differing.extend(r["differing"])
    emit(cell(
        sum(1 for r in results if r["identical"]), len(pairs), [],
        differing=differing, meta_keys_differing=sorted(keys),
        converter_a=conv_a, converter_b=conv_b,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
