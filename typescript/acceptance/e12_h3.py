"""H3: one LINE per completed statement, against the hand count.

    .venv/bin/python typescript/acceptance/e12_h3.py <store> <handcount.md> <out>

The gate is the COUNT: the first activation of `parseDiceGroups` in F1 carries
N LINE rows, N the hand count's, and any other count is a STOP with the diff of
lines. The second reading is the rows' `line` values in order. Both are read
here off the trace itself rather than off a printed transcript, because the
hand count predicts `deltas` and `unbound` names as well as lines and a printed
row renders values it does not name.

WHERE N COMES FROM
------------------
The hand-count FILE's LAST line (`N = 9`), not the table's row count and not a
number typed here: the table and the sentence are two statements of one
prediction and the file's own last line is the one §1 calls the gate. If the
table's rows and that last line disagree, this instrument refuses rather than
picking a winner -- a prediction that contradicts itself has not been made.

The file is pinned by sha256 as §1's last line and the lock test recomputes
it, so a table edited after a number is read is caught in the suite; this
instrument recomputes the same sha into the cell so the record can quote it.

WHICH ACTIVATION
----------------
The first: the frame of the named function with the smallest `call_event_id`
in F1's trace. §1.1 says why that is `parseDiceGroups('1d20')` -- a `describe`
callback only registers, the `it` bodies run in file order -- and this
instrument does not re-derive it, it takes the first activation the trace
holds and reports the CALL's arguments beside the rows so the record can say
which activation was read.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

from e12_report import table_cells
from lens import cell, emit, usage

#: The hand count's table row: `| 1 | 69 | `...` | groups | - | §3.2 ... |`.
#: Five columns are read; the sixth (the rule) is carried for the record.
COLUMNS = ("row", "line", "statement", "deltas", "unbound", "rule")

#: A dash is the table's spelling of "none", in both name columns.
NONE = {"-", "--", "—", ""}


def names(text: str) -> list[str]:
    """One name column as a list: `count, sides` -> `["count", "sides"]`."""
    text = text.strip().strip("`")
    if text in NONE:
        return []
    return [part.strip().strip("`") for part in text.split(",") if part.strip()]


def handcount(path: Path) -> dict:
    """The table's five columns, plus N from the file's own LAST line."""
    text = path.read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        cells = table_cells(line)
        if len(cells) >= len(COLUMNS) and re.fullmatch(r"\d+", cells[0]):
            rows.append({"row": int(cells[0]), "line": int(cells[1]),
                         "statement": cells[2],
                         "deltas": names(cells[3]),
                         "unbound": names(cells[4]), "rule": cells[5]})
    last = next((ln.strip() for ln in reversed(text.splitlines()) if ln.strip()),
                "")
    m = re.fullmatch(r"N = (\d+)", last)
    if not m:
        usage(f"the hand count's last line is {last!r}, not `N = <count>`; "
              "N is the gate and it is read from that line")
    n = int(m.group(1))
    if n != len(rows):
        usage(f"the hand count's last line says N = {n} and its table has "
              f"{len(rows)} rows; a prediction that contradicts itself has "
              "not been made, and nothing is measured against it")
    fn = re.search(r"the LINE rows of `(\w+)\(", text)
    if not fn:
        usage("the hand count does not name the function it counts "
              "(`the LINE rows of `<fn>(`)")
    return {"n": n, "rows": rows, "function": fn.group(1),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "path": path.name}


def activation(conn, qualname: str) -> dict | None:
    """The FIRST activation of `qualname`: its frame, its CALL, its LINE rows."""
    frame = conn.execute(
        "SELECT f.id, f.call_event_id, c.file FROM frames f "
        "JOIN code_objects c ON c.id = f.code_id WHERE c.qualname = ? "
        "ORDER BY f.call_event_id LIMIT 1", (qualname,)).fetchone()
    if frame is None:
        return None
    fid, call_id, file = frame
    call = conn.execute("SELECT payload FROM events WHERE id = ?",
                        (call_id,)).fetchone()
    rows = []
    for eid, line, payload in conn.execute(
            "SELECT id, line, payload FROM events WHERE frame_id = ? "
            "AND kind = 'LINE' ORDER BY id", (fid,)):
        body = json.loads(payload) if payload else {}
        rows.append({"event": f"e{eid}", "line": line,
                     "deltas": list((body.get("deltas") or {}).keys()),
                     "unbound": list(body.get("unbound") or []),
                     "rendered": {k: v.get("v") if isinstance(v, dict) else v
                                  for k, v in (body.get("deltas") or {}).items()}})
    return {"frame": f"f{fid}", "file": file, "rows": rows,
            "call_args": json.loads(call[0]) if call and call[0] else None}


def diff_of_lines(want: list[int], got: list[int]) -> list[str]:
    """The diff §1's H3 asks for when the count is wrong: position by
    position, and what each side ran out of."""
    out = []
    for i in range(max(len(want), len(got))):
        w = want[i] if i < len(want) else None
        g = got[i] if i < len(got) else None
        if w != g:
            out.append(f"row {i + 1}: hand count {w}, trace {g}")
    return out


def main(argv) -> int:
    if len(argv) != 4:
        usage("usage: e12_h3.py <store> <handcount.md> <out dir>")
    store, table, out = Path(argv[1]), Path(argv[2]), Path(argv[3])
    out.mkdir(parents=True, exist_ok=True)
    hand = handcount(table)
    reads = out / "e12-reads.json"
    if not reads.is_file():
        usage(f"{reads} is not there: H3 reads F1's run id from the reads "
              "this session already took, and the reads come first")
    f1 = json.loads(reads.read_text(encoding="utf-8"))["run_ids"]["F1"]
    path = store / "traces" / f"{f1}.db"
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    got = activation(conn, hand["function"])
    conn.close()

    if got is None:
        payload = cell(None, hand["n"], [
            f"F1 carries no activation of {hand['function']}: the gate is a "
            "count of that activation's LINE rows and there is none"],
            hand_count=hand, run=f1)
    else:
        want_lines = [r["line"] for r in hand["rows"]]
        got_lines = [r["line"] for r in got["rows"]]
        claims = {
            f"N = {hand['n']} LINE rows": len(got["rows"]) == hand["n"],
            "the rows' `line` values equal §1.1's list in order":
                got_lines == want_lines,
            "each row's delta names equal the table's, in order":
                [r["deltas"] for r in got["rows"]]
                == [r["deltas"] for r in hand["rows"]],
            "each row's unbound names equal the table's, in order":
                [r["unbound"] for r in got["rows"]]
                == [r["unbound"] for r in hand["rows"]],
        }
        payload = cell(
            sum(1 for v in claims.values() if v), len(claims), [],
            rule=f"N = {hand['n']} -> PASS; any other count a STOP with the "
                 "diff of lines",
            claims=claims, rows_measured=len(got["rows"]),
            n_predicted=hand["n"], lines_predicted=want_lines,
            lines_measured=got_lines,
            diff_of_lines=diff_of_lines(want_lines, got_lines),
            deltas_predicted=[r["deltas"] for r in hand["rows"]],
            deltas_measured=[r["deltas"] for r in got["rows"]],
            unbound_predicted=[r["unbound"] for r in hand["rows"]],
            unbound_measured=[r["unbound"] for r in got["rows"]],
            activation={"frame": got["frame"], "call_args": got["call_args"]},
            rows=got["rows"], hand_count=hand, run=f1)
    payload["recorder"] = os.environ.get("E12_RECORDER")
    payload["recorder_rev"] = os.environ.get("E12_REV")
    (out / "e12-h3.json").write_text(json.dumps(payload, indent=2) + "\n",
                                     encoding="utf-8")
    emit({"value": payload["value"], "n": payload["n"],
          "dropped": payload["dropped"],
          "claims": payload.get("claims"),
          "diff_of_lines": payload.get("diff_of_lines")})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
