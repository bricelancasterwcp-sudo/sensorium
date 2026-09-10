"""The one place every Python instrument in this directory reads the lens from.

A measurement quoted without its instrument named is not a property of the
subject, so every cell these instruments emit carries the same lens string --
and it is read from `LENS.txt` beside this file rather than repeated, so the
twelve instruments cannot drift apart on what they measured.

The emitted shape is the record's own (none-versus-zero): `value` is `null`
exactly when the quantity was not measured, and `dropped` then says why. A
`0` is measured-and-zero and never carries a `dropped` reason.
"""
import json
import sys
from pathlib import Path

#: The lens, one line, beside this file. Deliberately holds no filesystem
#: path: paths belong to the record's §2 pins, not to a committed instrument.
LENS = (Path(__file__).with_name("LENS.txt")).read_text(encoding="utf-8").strip()


def cell(value, n, dropped=None, **detail) -> dict:
    """One measurement, in the record's schema.

    `dropped` is a list of reasons; a non-empty one with a non-null `value`
    is a partial measurement (some runs dropped, the rest measured), which
    is a fact the record can print and not a contradiction.
    """
    out = {"value": value, "n": n, "lens": LENS,
           "dropped": list(dropped or [])}
    out.update(detail)
    return out


def emit(payload) -> None:
    """Print one instrument's JSON on stdout and nothing else."""
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


def usage(message: str):
    """Refuse the call by name, on stderr, with exit 2."""
    sys.stderr.write(message.rstrip() + "\n")
    raise SystemExit(2)
