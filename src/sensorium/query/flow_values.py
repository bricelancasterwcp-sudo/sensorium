"""The value layer `flow` searches: a literal, and what matches it.

Split out of `flow_cmd.py` at that file's 800-line ceiling, along the seam
the material has. Turning `--value`'s argument into a literal, and deciding
whether one capture is a sighting of a target, are decisions about CAPTURED
VALUES: they know nothing about events, frames, or the gap analysis that
reads them. Everything here is re-exported by `flow_cmd`, so a caller (or a
test) that reaches for `flow_cmd.matches` still finds it.
"""
import re
from dataclasses import dataclass

from sensorium.query.fmt import fmt_value
from sensorium.query.rust_debug import debug_text

CONTAINER_KINDS = ("obj", "seq", "map")

_NUMERIC = re.compile(r"[+-]?(\d[\d_]*\.?[\d_]*|\.\d[\d_]*)([eE][+-]?\d+)?")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class ObjTarget:
    """One object, as well as this trace can name one."""
    oid: int
    type: str


#: The words that name a value rather than a string, in both spellings the
#: reader may know (ruling R33). `--expr` already reads `null`, `true` and
#: `false` as values in every language (`expr._CONSTANTS`), and a reader
#: debugging a TypeScript trace writes them at `flow` too; a search that
#: quietly looked for the four-character STRING "null" instead would report
#: zero sightings of a value the trace holds. Language-neutral, like the
#: predicate's own constants: on a Rust trace `--value null` sights an
#: `Option::None` capture, which is the same value in the reader's terms.
#: `undefined` has no spelling here -- no writer can render it (a capture
#: that holds it is JavaScript's, and `inspect_text` returns None for the
#: marker) -- and neither has a BigInt; both are carried debts, not
#: silences: `--expr x == undefined` is what answers about one.
_WORDS = {"None": None, "null": None,
          "True": True, "true": True,
          "False": False, "false": False}


def parse_literal(s: str):
    """The literal `--value` names.

    Digits are a number, so quote to force a string (`--value "'1800'"`) --
    otherwise a string of digits would be unsearchable. Words that `float()`
    happens to accept ("nan", "inf", "infinity") stay strings: silently
    turning a search for the word into a search for the float would report
    zero sightings for a value the trace may well hold. The six words above
    are the exception, and quoting still forces the string: `--value "'null'"`
    searches for the four characters.
    """
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1]
    if s in _WORDS:
        return _WORDS[s]
    if not _NUMERIC.fullmatch(s):
        return s
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def matches(cap: dict, target, write=debug_text) -> bool:
    """Whether one capture is a sighting of `target`.

    Bools and numbers are kept apart on the capture's own kind, because
    `True == 1` in Python and a trace holding both must not report one as a
    sighting of the other. A clipped string never matches: what was recorded
    is a strict prefix of the real string, so the real string is longer than
    -- and therefore unequal to -- anything it is compared with.

    `write` is how the trace's own recorder would SPELL a literal
    (`query/dbg_dialects`). Rust's by default, which is what every caller
    written before a second dialect existed passes (plan P10) -- and what a
    Python trace, whose captures are typed, never consults.
    """
    k = cap.get("k")
    if isinstance(target, ObjTarget):
        # A rendered capture carries an identity when the recorder minted
        # one for it (`oid`/`type` on an object or a function, on nothing
        # else). The identity is a KEY on the capture, never something read
        # out of the text: matching on the text would splice every object
        # that renders the same way into one lineage, which is the worst
        # failure this command has -- the output looks exactly like a
        # correct answer.
        return ((k in CONTAINER_KINDS or (k == "dbg" and "oid" in cap))
                and cap.get("oid") == target.oid
                and cap.get("type") == target.type)
    if k == "dbg":
        # Rendered TEXT (design 2026-09-06 §4.2): a sighting is the
        # literal's own RENDERING, spelled the way that recorder spells it
        # -- so `"A1"` sights a Rust `String`, `'A1'` a JavaScript one, and
        # the bare word `A1` sights an enum variant or a type name instead.
        # A truncated text is a prefix of a rendering and equals none.
        text = write(target)
        return (not cap.get("trunc") and text is not None
                and cap.get("v") == text)
    if target is None:
        return k == "none"
    if isinstance(target, bool):
        return k == "bool" and cap.get("v") == target
    if isinstance(target, (int, float)):
        return k == "num" and cap.get("v") == target
    return k == "str" and not cap.get("trunc") and cap.get("v") == target


def _key_step(kcap: dict) -> str:
    """How to render "the value under this key" in a path label."""
    v = kcap.get("v")
    if (kcap.get("k") == "str" and not kcap.get("trunc")
            and isinstance(v, str) and _IDENT.fullmatch(v)):
        return f".{v}"
    return f"[{fmt_value(kcap)}]"


def _walk(v: dict, path: str = ""):
    """Every capture inside `v`, with the path that names it.

    A depth-capped container omits `sample` entirely rather than supplying an
    empty list, so it is always read with `.get` -- never `v["sample"]`.
    """
    yield path, v
    k = v.get("k")
    if k == "seq":
        for i, x in enumerate(v.get("sample", [])):
            yield from _walk(x, f"{path}[{i}]")
    elif k == "map":
        for i, pair in enumerate(v.get("sample", [])):
            kcap, vcap = pair
            yield from _walk(kcap, f"{path}[key {i}]")
            yield from _walk(vcap, path + _key_step(kcap))


def find_in_value(v: dict, target, path: str = "",
                  write=debug_text) -> list[str]:
    """The paths inside `v` at which `target` was captured."""
    return [p for p, cap in _walk(v, path) if matches(cap, target, write)]
