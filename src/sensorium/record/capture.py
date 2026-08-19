"""Structured value capture with hard caps and marked truncation.

Captures may be smaller than the real value; they are never silently so:
anything cut carries "trunc": true and bumps capture_stats["truncated"].
"""
from itertools import islice

CAPS = {"str": 200, "repr": 200, "sample": 8, "depth": 3}

capture_stats = {"truncated": 0}


def _trunc_str(s: str, cap: int) -> tuple[str, bool]:
    if len(s) <= cap:
        return s, False
    capture_stats["truncated"] += 1
    return s[:cap], True


def capture_value(obj, depth: int = 0) -> dict:
    if obj is None:
        return {"k": "none"}
    if isinstance(obj, bool):
        return {"k": "bool", "v": obj}
    if isinstance(obj, (int, float)):
        return {"k": "num", "v": obj}
    if isinstance(obj, str):
        s, t = _trunc_str(obj, CAPS["str"])
        out = {"k": "str", "v": s}
        if t:
            out["trunc"] = True
        return out
    if isinstance(obj, (list, tuple, set, frozenset)):
        return _capture_sized(obj, depth, "seq",
                              lambda o, d: [capture_value(x, d)
                                            for x in islice(iter(o), CAPS["sample"])])
    if isinstance(obj, dict):
        return _capture_sized(obj, depth, "map",
                              lambda o, d: [[capture_value(k, d), capture_value(v, d)]
                                            for k, v in islice(o.items(), CAPS["sample"])])
    return _capture_obj(obj)


def _capture_sized(obj, depth, kind, sampler) -> dict:
    out = {"k": kind, "type": type(obj).__name__, "len": len(obj), "oid": id(obj)}
    if depth >= CAPS["depth"]:
        out["trunc"] = True
        capture_stats["truncated"] += 1
        return out
    out["sample"] = sampler(obj, depth + 1)
    if len(obj) > CAPS["sample"]:
        out["trunc"] = True
        capture_stats["truncated"] += 1
    return out


def _capture_obj(obj) -> dict:
    out = {"k": "obj", "type": type(obj).__name__, "oid": id(obj)}
    try:
        r = repr(obj)
    except BaseException:
        r = f"<{type(obj).__name__} repr-raised>"
        out["trunc"] = True
        capture_stats["truncated"] += 1
    s, t = _trunc_str(r, CAPS["repr"])
    out["repr"] = s
    if t:
        out["trunc"] = True
    return out


def capture_exc(exc: BaseException) -> dict:
    msg, _ = _trunc_str(str(exc), CAPS["str"])
    return {"type": type(exc).__name__, "msg": msg, "oid": id(exc)}
