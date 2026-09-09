"""E4': do sites keep their lines and columns?

    python3 sites.py <check.mjs json> <plain log> <driven log> <planted file>

Two halves, and the cell PASSES only if both do.

The twenty shapes: the probe project's own checker (`probes/check.mjs`)
already holds every `// SITE` marker to the line under it, so this reads its
verdict rather than re-deriving it -- `sites:count` must be 20 and
`sites:lines` must have `wrong: []`. Reading a checker's own JSON is the
point of the checker; re-implementing it here would give the endpoint a
second, unpinned opinion.

The planted assertion: one `expect(1).toBe(2)` in one test file of a
throwaway copy of the lens, run plain and run through the driver. What is
compared is what VITEST said about it -- the `FAIL` header and every
`file:line:col` it printed for the planted file -- and the rule is
byte-identical, so this compares the extracted text and not a summary of it.

`value` is the number of the twenty shapes on their exact line; `report_identical`
carries the second half. A `null` value means the checker's JSON could not be read.
"""
import json
import re
import sys
from pathlib import Path

from lens import cell, emit, usage

#: How many `// SITE` shapes the pre-registration counts.
SHAPES = 20
#: Vitest's own reference form: `<path>:<line>:<col>`, wherever it appears
#: (the `FAIL` header, the stack arrow, the code frame).
REF = re.compile(r"[\w./@-]+\.[cm]?[jt]sx?:\d+:\d+")
#: ANSI colour, which vitest emits when it thinks it has a terminal and
#: which is not part of what it SAID about the failure.
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fail_block(text: str, planted: str) -> dict:
    """What vitest printed about the planted file, extracted verbatim.

    `fail_lines` are its `FAIL` headers naming that file; `refs` is every
    `path:line:col` it printed for it, in order and with duplicates kept --
    a report that named the site once and a report that named it three times
    are not the same report.
    """
    clean = [ANSI.sub("", line).rstrip() for line in text.splitlines()]
    fail_lines = [line.strip() for line in clean
                  if line.lstrip().startswith("FAIL") and planted in line]
    refs = [m for line in clean for m in REF.findall(line) if planted in m]
    return {"fail_lines": fail_lines, "refs": refs}


def sites_half(report: dict) -> dict:
    checks = {c["id"]: c for c in report.get("checks", [])}
    count = checks.get("sites:count")
    lines = checks.get("sites:lines")
    on_line = None
    if lines is not None and isinstance(lines.get("detail"), dict):
        on_line = lines["detail"].get("on_line")
    return {
        "markers": None if count is None else count.get("detail"),
        "on_line": on_line,
        "wrong": (lines or {}).get("detail", {}).get("wrong")
                 if isinstance((lines or {}).get("detail"), dict) else None,
        "count_ok": bool(count and count["ok"]),
        "lines_ok": bool(lines and lines["ok"]),
    }


def measure(check_json: Path, plain_log: Path, driven_log: Path,
            planted: str) -> dict:
    dropped = []
    try:
        report = json.loads(check_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return cell(None, 0, [f"the probe checker's JSON could not be read: {e}"])
    sites = sites_half(report)

    planted_half = {"file": planted}
    try:
        plain = fail_block(plain_log.read_text(encoding="utf-8", errors="replace"), planted)
        driven = fail_block(driven_log.read_text(encoding="utf-8", errors="replace"), planted)
    except OSError as e:
        planted_half["dropped"] = f"a run log could not be read: {e}"
        dropped.append(planted_half["dropped"])
        plain = driven = None

    identical = None
    if plain is not None:
        identical = plain == driven
        planted_half.update(plain=plain, driven=driven, identical=identical)
        if not plain["fail_lines"] and not plain["refs"]:
            planted_half["dropped"] = ("the plain run printed no FAIL and no "
                                       "site reference for the planted file")
            dropped.append(planted_half["dropped"])
            identical = None

    # The rule's number is "20/20 on the exact line", so the value is the
    # count on their exact line; whether the checker also found twenty
    # markers to look for is `shapes.count_ok` beside it, and a run that
    # found nineteen markers cannot reach 20 here by construction.
    return cell(sites["on_line"], SHAPES, dropped,
                shapes=sites, planted=planted_half,
                report_identical=identical)


def main(argv) -> int:
    if len(argv) != 5:
        usage("usage: sites.py <check.mjs json> <plain log> <driven log> "
              "<planted file, root-relative>")
    emit(measure(Path(argv[1]), Path(argv[2]), Path(argv[3]), argv[4]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
