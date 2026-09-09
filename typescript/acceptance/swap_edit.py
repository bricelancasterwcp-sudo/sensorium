"""The §10 planted change, applied: one call site moved past another.

    python3 swap_edit.py <root> <file rel> <move needle> <before needle>

The line containing `<move needle>` is cut and re-inserted immediately above
the line containing `<before needle>`, with its own indentation preserved.
Nothing else in the file is touched, and both needles must match EXACTLY ONE
line each -- two matches is a refusal, because an edit that picked one of two
candidates would not be the edit anybody wrote down.

That is the whole planted change: two call sites execute in the opposite
order. When the two calls are to different functions the recorder's causal
stream -- a sequence of `(file, qualname, kind)` -- must move, and `diff`
must read DIVERGED. A MATCH voids the verifier.

Prints a JSON summary of what moved and where.
"""
import json
import sys
from pathlib import Path


def apply(root: Path, rel: str, move: str, before: str) -> dict:
    path = root / rel
    lines = path.read_text(encoding="utf-8").split("\n")
    hits = [i for i, ln in enumerate(lines) if move in ln]
    anchors = [i for i, ln in enumerate(lines) if before in ln]
    if len(hits) != 1:
        raise SystemExit(f"swap_edit: {len(hits)} lines contain {move!r}; "
                         "exactly one is required")
    if len(anchors) != 1:
        raise SystemExit(f"swap_edit: {len(anchors)} lines contain "
                         f"{before!r}; exactly one is required")
    src, dst = hits[0], anchors[0]
    if src == dst:
        raise SystemExit("swap_edit: the two needles matched the same line")
    line = lines.pop(src)
    dst = dst - 1 if src < dst else dst
    lines.insert(dst, line)
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"file": rel, "moved_line": line.strip(),
            "from_line_1based": src + 1, "to_line_1based": dst + 1,
            "now_above": lines[dst + 1].strip()}


def main(argv) -> int:
    if len(argv) != 5:
        sys.stderr.write("usage: swap_edit.py <root> <file rel> "
                         "<move needle> <before needle>\n")
        return 2
    json.dump(apply(Path(argv[1]), argv[2], argv[3], argv[4]),
              sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
