"""The §10 split, applied: two functions moved out of one module, verbatim.

    python3 split_edit.py <root> <module rel> <dest rel> <preamble> <name>...

A MOVE and nothing else. Each named function's block -- its JSDoc comment,
if the lines immediately above it are one, through the `}` in column 0 that
closes it -- is cut out of `<module rel>` byte for byte and pasted into a new
`<dest rel>`, under `<preamble>` (the type imports the moved code needs; it
is the caller's, because only the caller knows which types the two functions
mention). The module then imports the names back and re-exports them, so
every existing import in the tree still resolves and no call site changes.

Nothing is reformatted, no body is touched, and the script refuses rather
than guesses: a name it cannot find, or a block it cannot see the end of,
is an error and not a partial edit.

Prints a JSON summary of what it moved.
"""
import json
import re
import sys
from pathlib import Path


class EditError(Exception):
    """The edit cannot be made exactly. Names what could not be found."""


def block(lines: list[str], name: str) -> tuple[int, int]:
    """`[start, end)` line indices of `export function <name>`'s block."""
    head = re.compile(rf"^export (?:async )?function {re.escape(name)}\b")
    start = next((i for i, ln in enumerate(lines) if head.match(ln)), None)
    if start is None:
        raise EditError(f"no `export function {name}` in the module")
    # The JSDoc immediately above, if there is one.
    top = start
    if top > 0 and lines[top - 1].rstrip().endswith("*/"):
        j = top - 1
        while j >= 0 and not lines[j].lstrip().startswith("/**"):
            j -= 1
        if j < 0:
            raise EditError(f"{name}'s comment above it has no `/**` opener")
        top = j
    end = next((i + 1 for i in range(start, len(lines)) if lines[i] == "}"),
               None)
    if end is None:
        raise EditError(f"{name}'s block has no closing `}}` in column 0")
    return top, end


def apply(root: Path, module_rel: str, dest_rel: str, preamble: str,
          names: list[str]) -> dict:
    module = root / module_rel
    text = module.read_text(encoding="utf-8")
    lines = text.split("\n")

    cuts = []
    for name in names:
        top, end = block(lines, name)
        cuts.append((top, end, name))
    cuts.sort()
    for (a1, b1, n1), (a2, _, n2) in zip(cuts, cuts[1:]):
        if b1 > a2:
            raise EditError(f"{n1}'s block overlaps {n2}'s")

    moved = []
    # Highest first, so the earlier blocks' indices stay valid.
    for top, end, name in reversed(cuts):
        moved.append({"name": name, "lines": end - top,
                      "first_line_1based": top + 1})
        del lines[top:end]

    body = "\n".join(
        "\n".join(text.split("\n")[t:e]) for t, e, _ in cuts)
    dest = root / dest_rel
    dest.write_text(preamble.rstrip("\n") + "\n\n" + body.strip("\n") + "\n",
                    encoding="utf-8")

    # The import back, placed after the module's last top-level import, and
    # the re-export beside it: the names have to be BOUND in this module
    # (`neighbors` and `hexStepsBetween` call them), and a bare
    # `export … from` would re-export without binding.
    stem = Path(dest_rel).stem
    last_import = max((i for i, ln in enumerate(lines)
                       if ln.startswith("import ")), default=None)
    if last_import is None:
        raise EditError("the module has no top-level import to place the "
                        "move's own import after")
    joined = ", ".join(sorted(names))
    lines[last_import + 1:last_import + 1] = [
        f"import {{ {joined} }} from './{stem}';",
        "",
        f"export {{ {joined} }};",
    ]
    module.write_text("\n".join(lines), encoding="utf-8")
    return {"module": module_rel, "dest": dest_rel,
            "moved": sorted(moved, key=lambda m: m["name"]),
            "import_after_line": last_import + 1}


def main(argv) -> int:
    if len(argv) < 6:
        sys.stderr.write("usage: split_edit.py <root> <module rel> "
                         "<dest rel> <preamble> <name>...\n")
        return 2
    try:
        out = apply(Path(argv[1]), argv[2], argv[3], argv[4], argv[5:])
    except (EditError, OSError) as e:
        sys.stderr.write(f"split_edit: {e}\n")
        return 2
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
