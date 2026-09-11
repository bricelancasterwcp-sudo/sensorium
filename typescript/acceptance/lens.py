"""The one place every Python instrument in this directory reads the lens from.

A measurement quoted without its instrument named is not a property of the
subject, so every cell an acceptance record carries the same lens string --
but it is no longer this file's `cell()` that puts it there. Rung 2 found six
cells stamped with ANOTHER rung's lens label, because `cell()` used to embed
`LENS` at MEASUREMENT time: whatever `LENS.txt` said at the moment an
instrument happened to run, which is not necessarily the rung that instrument
was measuring for. `stamp()` below is the fix -- it adds the label once, at
ASSEMBLY time, to a whole payload at once, so every cell in one record carries
the label the assembler meant and no instrument can mint its own.

`sensorium_bin()` is the other half of the same rung's finding: three reused
instruments called the bare `sensorium` on `PATH`, which runs `main`'s
globally installed tool rather than this branch's. Every Python instrument
that spawns the CLI resolves it here instead.

The emitted shape is the record's own (none-versus-zero): `value` is `null`
exactly when the quantity was not measured, and `dropped` then says why. A
`0` is measured-and-zero and never carries a `dropped` reason.
"""
import json
import os
import sys
from pathlib import Path

#: The lens, one line, beside this file. Deliberately holds no filesystem
#: path: paths belong to the record's §2 pins, not to a committed instrument.
LENS = (Path(__file__).with_name("LENS.txt")).read_text(encoding="utf-8").strip()

#: `typescript/acceptance/lens.py` -> `typescript/acceptance` -> `typescript`
#: -> the repo root. The same two-parents-up this file's `bin.sh` spells with
#: `dirname .../../..`, so a Python instrument and a shell one resolve the
#: identical path.
REPO_ROOT = Path(__file__).resolve().parents[2]


def cell(value, n, dropped=None, **detail) -> dict:
    """One measurement, in the record's schema -- minus `lens`.

    `dropped` is a list of reasons; a non-empty one with a non-null `value`
    is a partial measurement (some runs dropped, the rest measured), which
    is a fact the record can print and not a contradiction.

    Carries no `lens` key: `stamp()` adds that, once, to the whole record at
    assembly time. A cell this returns that already had one stamped onto it
    by a caller is not this function's business -- nothing here writes one.
    """
    out = {"value": value, "n": n, "dropped": list(dropped or [])}
    out.update(detail)
    return out


def _is_cell(node) -> bool:
    """A cell is a dict carrying the record's schema, `lens` aside -- the one
    field `stamp()` exists to add, so requiring it here would make a fresh
    cell unrecognisable before its first stamp."""
    return isinstance(node, dict) and all(k in node for k in ("value", "n", "dropped"))


def stamp(node, *, strict: bool = False):
    """Add the lens label to every cell under `node`, at assembly time.

    Walks the whole payload -- a cell nested under `reported`, or one of many
    under a dict-of-cells like `controls`, is stamped like a top-level one --
    and returns a NEW structure; `node` is not mutated.

    A cell that already carries `lens` is history: an instrument measured
    under the OLD rule, before this file stopped embedding it, and its
    committed JSON still has the label baked in. Left alone by default, so
    the three rungs' assemblers keep re-assembling their own saved cells
    unchanged. `strict=True` removes that allowance: it is for an assembler
    over instruments that were ALL built after this rule, where a cell that
    still arrives with its own `lens` is not history, it is a defect -- some
    instrument minted a label nothing here asked it to -- and the assembler
    refuses (`SystemExit(3)`) naming the cell rather than silently keep it.
    """
    if isinstance(node, list):
        return [stamp(item, strict=strict) for item in node]
    if not isinstance(node, dict):
        return node
    out = {key: stamp(value, strict=strict) for key, value in node.items()}
    if _is_cell(out) and "lens" not in out:
        out = {**out, "lens": LENS}
    elif _is_cell(out) and strict:
        sys.stderr.write(
            "refused: a cell already carries its own lens label "
            f"({out['lens']!r}); only the assembler stamps one -- cell: "
            f"{json.dumps(out, sort_keys=True)[:300]}\n")
        raise SystemExit(3)
    return out


def sensorium_bin() -> str:
    """The branch's own `sensorium`, resolved the way `bin.sh` resolves it.

    `<repo root>/.venv/bin/sensorium`, refused -- resolved path printed, exit
    3 -- when that file is not an executable or when its `realpath` is not
    under the repo root. One rule, two spellings (`bin.sh`'s and this one),
    one refusal sentence, so a reader who hits it in either language reads
    the same words.
    """
    candidate = REPO_ROOT / ".venv" / "bin" / "sensorium"
    resolved = candidate.resolve() if candidate.exists() else candidate
    under_root = str(resolved).startswith(str(REPO_ROOT) + os.sep)
    if not (candidate.is_file() and os.access(candidate, os.X_OK) and under_root):
        sys.stderr.write(
            f"refused: sensorium resolves to '{candidate}', not the "
            f"branch's .venv under {REPO_ROOT}\n")
        raise SystemExit(3)
    return str(candidate)


def emit(payload) -> None:
    """Print one instrument's JSON on stdout and nothing else."""
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


def usage(message: str):
    """Refuse the call by name, on stderr, with exit 2."""
    sys.stderr.write(message.rstrip() + "\n")
    raise SystemExit(2)
