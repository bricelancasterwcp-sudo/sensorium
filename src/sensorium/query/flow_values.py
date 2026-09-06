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

CONTAINER_KINDS = ("obj", "seq", "map")

_NUMERIC = re.compile(r"[+-]?(\d[\d_]*\.?[\d_]*|\.\d[\d_]*)([eE][+-]?\d+)?")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class ObjTarget:
    """One object, as well as this trace can name one."""
    oid: int
    type: str


def parse_literal(s: str):
    """The literal `--value` names.

    Digits are a number, so quote to force a string (`--value "'1800'"`) --
    otherwise a string of digits would be unsearchable. Words that `float()`
    happens to accept ("nan", "inf", "infinity") stay strings: silently
    turning a search for the word into a search for the float would report
    zero sightings for a value the trace may well hold.
    """
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1]
    if s == "None":
        return None
    if s in ("True", "False"):
        return s == "True"
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


def matches(cap: dict, target) -> bool:
    """Whether one capture is a sighting of `target`.

    Bools and numbers are kept apart on the capture's own kind, because
    `True == 1` in Python and a trace holding both must not report one as a
    sighting of the other. A clipped string never matches: what was recorded
    is a strict prefix of the real string, so the real string is longer than
    -- and therefore unequal to -- anything it is compared with.
    """
    k = cap.get("k")
    if isinstance(target, ObjTarget):
        return (k in CONTAINER_KINDS and cap.get("oid") == target.oid
                and cap.get("type") == target.type)
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


def find_in_value(v: dict, target, path: str = "") -> list[str]:
    """The paths inside `v` at which `target` was captured."""
    return [p for p, cap in _walk(v, path) if matches(cap, target)]
