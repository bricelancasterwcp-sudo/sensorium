"""E4''s planted assertion: one failing `expect` appended to one test file.

    python3 plant_edit.py <root> <file rel> <test name>

Appends exactly one test, whose body is one `expect(1).toBe(2);`, to the end
of `<file rel>` and prints the line the assertion now sits on. The COLUMN is
deliberately not predicted here: which column vitest points at is part of
what E4' measures, and an instrument that asserted its own guess would be
answering the question instead of asking it.
Appended rather than substituted so that nothing already in the file moves:
every other line keeps its number, and what E4' compares -- the `FAIL` header
and the `file:line:col` vitest prints -- is about the planted line alone.

The file must already import `test` or `it` and `expect` from vitest; the
script reads which of `test`/`it` it imports and uses that one, and refuses
rather than add an import (an import is a change to the file's own head, and
that is not what was planted).
"""
import json
import re
import sys
from pathlib import Path

BLOCK = "\n{kw}('{name}', () => {{\n  expect(1).toBe(2);\n}});\n"


def main(argv) -> int:
    if len(argv) != 4:
        sys.stderr.write("usage: plant_edit.py <root> <file rel> <test name>\n")
        return 2
    path = Path(argv[1]) / argv[2]
    text = path.read_text(encoding="utf-8")
    head = text.split("\n", 1)[0]
    imports = re.search(r"import\s*\{([^}]*)\}\s*from\s*'vitest'", text)
    if not imports:
        sys.stderr.write(f"plant_edit: {argv[2]} does not import from "
                         "'vitest'; nothing was planted\n")
        return 2
    names = {n.strip() for n in imports.group(1).split(",")}
    kw = "test" if "test" in names else ("it" if "it" in names else None)
    if kw is None or "expect" not in names:
        sys.stderr.write(f"plant_edit: {argv[2]} imports {sorted(names)}; it "
                         "needs `expect` and one of `test`/`it`\n")
        return 2
    if not text.endswith("\n"):
        text += "\n"
    before = text.count("\n")
    block = BLOCK.format(kw=kw, name=argv[3])
    path.write_text(text + block, encoding="utf-8")
    json.dump({"file": argv[2], "keyword": kw, "first_line": head,
               "lines_before": before,
               "assertion_line_1based": before + 3,
               "block": block}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
