"""E6''s JSON: the four contamination facts, read off what `e6.sh` produced.

`value` is the number of `__srt` markers found in the caches -- the number
whose PASS is 0 -- and every other fact is beside it, because a single
number cannot carry four claims and a cell that reported only the grep
would look like a pass while the manifest had moved.
"""
import os
import sys
from pathlib import Path

from lens import cell, emit

WANT_FILES = " Test Files  372 passed (372)"
WANT_TESTS = "      Tests  4278 passed (4278)"


def main() -> int:
    env = os.environ
    check = Path(env["E6_CHECK"]).read_text(encoding="utf-8", errors="replace")
    plain = Path(env["E6_PLAIN"]).read_text(encoding="utf-8", errors="replace")
    markers_text = Path(env["E6_MARKERS"]).read_text(encoding="utf-8", errors="replace")

    ok_lines = sum(1 for ln in check.splitlines() if ln.endswith(": OK"))
    failed = [ln for ln in check.splitlines() if "FAILED" in ln]
    hits = [ln[len("hit: "):] for ln in markers_text.splitlines()
            if ln.startswith("hit: ")]
    searched = [ln[len("searched: "):] for ln in markers_text.splitlines()
                if ln.startswith("searched: ")]

    wall = round(float(env["E6_WALL"]), 4)
    lo, hi = float(env["E6_LO"]), float(env["E6_HI"])
    duration = next((ln.strip() for ln in plain.splitlines()
                     if ln.lstrip().startswith("Duration")), None)

    dropped = []
    if not searched:
        dropped.append("no vite/vitest cache directory existed to search -- "
                       "0 markers here is 0 files searched, not 0 found")

    emit(cell(
        len(hits), len(searched), dropped,
        manifest={"exit": int(env["E6_MANIFEST_STATUS"]), "ok": ok_lines,
                  "failed": failed, "identical": int(env["E6_MANIFEST_STATUS"]) == 0
                  and not failed},
        plain_after={"exit": int(env["E6_PLAIN_STATUS"]),
                     "files": WANT_FILES in plain, "tests": WANT_TESTS in plain,
                     "wall": wall, "band": [lo, hi], "in_band": lo <= wall <= hi,
                     "duration_line": duration},
        markers={"searched": searched, "hits": hits},
        wrapper_dir=env["E6_WRAPPER"],
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
