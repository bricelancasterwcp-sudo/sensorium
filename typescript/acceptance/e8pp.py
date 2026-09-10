"""E8″: is every marked shape's record there?

    python3 e8pp.py <check.mjs json> <probes dir>

§1 fixes the population: "every `// SWALLOW` / `// ESCAPE` marker in
`swallow.probe.test.ts` and `escape.probe.test.ts`, one check per marker",
and the rule is "every marker's record present per shape; a missing one →
STOP". So the denominator is counted HERE, out of the probe sources, and not
taken from the checker: a checker that stopped asserting a marker would
otherwise shrink the population and the ratio would stay 1.

`e8.py` (rung 1's) is left alone. It counts FIVE swallow shapes and rung 1's
record is locked around that number; this rung has twelve of them plus an
escape file, and editing rung 1's instrument would move a cell in a record
that is closed.

The checker's grain is coarser than one check per marker -- a shape's rows
are compared as a SET (`swallow:<id>:rows`) and the escape file's `how`
words all at once (`escape:how`) -- so a marker counts as SEEN when every
check about its shape passed, and the escape file's own detail
(`as_marked`, `wrong`) resolves that half marker by marker. A shape whose
set comparison failed contributes ZERO seen markers and is named: which of
its markers moved is not a fact the checker's output carries, and guessing
would be the one thing this endpoint must not do.

`value` is how many markers were seen, out of how many were written.
"""
import json
import os
import re
import sys
from pathlib import Path

from lens import cell, emit, usage

#: `check.mjs`'s own marker grammar, transferred literally: an indented
#: `// <TAG> <args…>` line, and the record it describes is on the NEXT line.
MARKER = "^\\s*//\\s+{tag}\\s+(.+?)\\s*$"
#: `swallow:<shape>:<what>` -- the checker's id grammar for the swallow file.
SWALLOW_ID = re.compile(r"^swallow:(shape\d+):")


def markers(path: Path, tag: str) -> list[dict]:
    """Every marker in one probe file: its arguments and the line it marks."""
    rx = re.compile(MARKER.format(tag=tag))
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
        m = rx.match(line)
        if m:
            out.append({"args": m.group(1).split(), "line": i + 2})
    return out


def swallow_half(report: dict, marks: list[dict]) -> dict:
    """Per shape: its markers, the checks about it, and whether all passed."""
    per_shape: dict[str, dict] = {}
    for mark in marks:
        shape = per_shape.setdefault(mark["args"][0],
                                     {"markers": 0, "checks": [], "seen": 0})
        shape["markers"] += 1
    for check in report.get("checks", []):
        m = SWALLOW_ID.match(check.get("id", ""))
        if m and m.group(1) in per_shape:
            per_shape[m.group(1)]["checks"].append({"id": check["id"],
                                                    "ok": bool(check["ok"])})
    for shape in per_shape.values():
        # `None` where the checker asserted NOTHING about the shape: "not
        # asked" and "asked and wrong" are different facts and the cell says
        # which. Neither contributes a seen marker.
        ok = (all(c["ok"] for c in shape["checks"]) if shape["checks"] else None)
        shape["ok"] = ok
        shape["seen"] = shape["markers"] if ok else 0
    return per_shape


def escape_half(report: dict, marks: list[dict]) -> dict:
    """The escape file: `escape:how`'s own per-marker detail, plus the count."""
    by_id = {c.get("id"): c for c in report.get("checks", [])}
    how = by_id.get("escape:how")
    count = by_id.get("escape:count")
    detail = (how or {}).get("detail") or {}
    seen = detail.get("as_marked")
    return {
        "markers": len(marks),
        "seen": int(seen) if isinstance(seen, int) else 0,
        "count_check": None if count is None else bool(count["ok"]),
        "how_check": None if how is None else bool(how["ok"]),
        "wrong": detail.get("wrong") or [],
        "asserted": how is not None and count is not None,
    }


def measure(check_json: Path, probes: Path) -> dict:
    try:
        report = json.loads(check_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return cell(None, 0, [f"the probe checker's JSON could not be read: {e}"])
    swallow_marks = markers(probes / "src/swallow.probe.test.ts", "SWALLOW")
    escape_marks = markers(probes / "src/escape.probe.test.ts", "ESCAPE")
    shapes = swallow_half(report, swallow_marks)
    escape = escape_half(report, escape_marks)

    dropped = []
    for name, shape in sorted(shapes.items()):
        if not shape["checks"]:
            dropped.append(f"{name}: the checker asserted nothing about it, so "
                           f"its {shape['markers']} marker(s) are unmeasured")
        elif not shape["ok"]:
            dropped.append(f"{name}: a check about it failed, so none of its "
                           f"{shape['markers']} marker(s) counts as seen")
    if not escape["asserted"]:
        dropped.append("the escape file: `escape:count` or `escape:how` is "
                       "missing from the checker's output")
    total = len(swallow_marks) + len(escape_marks)
    seen = sum(s["seen"] for s in shapes.values()) + escape["seen"]
    return cell(
        seen, total, dropped,
        rule="every marker's record present per shape; a missing one -> STOP",
        swallow_markers=len(swallow_marks), escape_markers=len(escape_marks),
        per_shape=shapes, escape=escape,
        checker={"ok": report.get("ok"), "mode": report.get("mode"),
                 "spools": report.get("spools"),
                 "checks": len(report.get("checks", [])),
                 "failures": report.get("failures", [])},
        recorder=os.environ.get("E8PP_RECORDER"),
        recorder_rev=os.environ.get("E8PP_REV"),
    )


def main(argv) -> int:
    if len(argv) != 3:
        usage("usage: e8pp.py <check.mjs json> <probes dir>")
    emit(measure(Path(argv[1]), Path(argv[2])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
