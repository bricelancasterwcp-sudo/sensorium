"""E8': are the five swallow shapes still seen?

    python3 e8.py <check.mjs json>

The probe checker asserts each shape's rows, its exception and (for shape 5)
that both raises carry one serial; shape 3 is the rejection nobody handles,
asserted by its own three checks. A shape counts as SEEN when every check
whose id names it passed -- so a shape cannot be counted by one check
passing while another about the same shape failed.

`value` is the number of shapes seen, out of five, and `per_shape` says
which checks each verdict rests on.
"""
import json
import re
import sys
from pathlib import Path

from lens import cell, emit, usage

SHAPES = ("shape1", "shape2", "shape3", "shape4", "shape5")
#: `swallow:<shape>:<what>` -- the checker's own id grammar.
ID = re.compile(r"^swallow:(shape\d):")


def measure(check_json: Path) -> dict:
    try:
        report = json.loads(check_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return cell(None, len(SHAPES),
                    [f"the probe checker's JSON could not be read: {e}"])
    per_shape = {s: {"checks": [], "ok": None} for s in SHAPES}
    for check in report.get("checks", []):
        m = ID.match(check.get("id", ""))
        if m and m.group(1) in per_shape:
            per_shape[m.group(1)]["checks"].append(
                {"id": check["id"], "ok": check["ok"]})
    dropped = []
    for shape, entry in per_shape.items():
        if not entry["checks"]:
            entry["ok"] = None
            dropped.append(f"{shape}: the checker asserted nothing about it")
        else:
            entry["ok"] = all(c["ok"] for c in entry["checks"])
    seen = sum(1 for e in per_shape.values() if e["ok"])
    return cell(seen, len(SHAPES), dropped, per_shape=per_shape)


def main(argv) -> int:
    if len(argv) != 2:
        usage("usage: e8.py <check.mjs json>")
    emit(measure(Path(argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
