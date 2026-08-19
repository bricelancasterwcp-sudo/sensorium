"""Structured value capture with hard caps and marked truncation.

Captures may be smaller than the real value; they are never silently so.
Anything cut carries "trunc": true; anything the object REFUSED to hand over
carries "unread": [names], naming which reads failed. Both bump
capture_stats["truncated"], which `info` reports as "truncated values".

Every read in this module is a call INTO the observed program. `__len__`,
`__iter__`, `items()`, `__str__`, `__repr__` -- and even `__class__`, which
`isinstance` consults, and the type's own `__name__` -- are all overridable,
and every one of them runs from inside a `sys.monitoring` callback. An
exception escaping one of them does not fail the capture: it propagates into
the observed program's frame, kills a program that runs clean standalone, and
is then reported by `exceptions` as that program's own bug, at the user's own
line, with a confident disposition. So every such read is guarded, and its
failure is RECORDED rather than invented around.
"""
from itertools import islice

CAPS = {"str": 200, "repr": 200, "sample": 8, "depth": 3}

capture_stats = {"truncated": 0}


def _guarded(read, unread: list, name: str):
    """One read against the observed object, which can never escape.

    Returns None on failure and appends `name` to `unread`, so the capture
    says which read it could not perform instead of inventing a value for it.
    `BaseException` because a hostile dunder may raise anything at all, and
    because letting anything out of a monitoring callback is strictly worse
    than absorbing it here: the alternative is an exception attributed to the
    program at a line that never raised.
    """
    try:
        return read()
    except BaseException:
        unread.append(name)
        capture_stats["truncated"] += 1
        return None


def _type_name(obj) -> str:
    """`type(obj).__name__` -- which a metaclass property can make raise."""
    try:
        return type(obj).__name__
    except BaseException:
        return "?"


def _trunc_str(s: str, cap: int) -> tuple[str, bool]:
    if len(s) <= cap:
        return s, False
    capture_stats["truncated"] += 1
    return s[:cap], True


def capture_value(obj, depth: int = 0) -> dict:
    """Capture one value. Never raises -- see the module docstring.

    The outer guard is not belt-and-braces over the inner ones: `isinstance`
    consults `obj.__class__`, so the very first branch of `_capture` is
    already a call into user code, as is `_trunc_str`'s `len()` on a `str`
    subclass. Whatever gets past the specific guards still may not reach the
    program.
    """
    try:
        return _capture(obj, depth)
    except BaseException:
        capture_stats["truncated"] += 1
        return {"k": "unread", "type": _type_name(obj), "oid": id(obj),
                "unread": ["value"]}


def _capture(obj, depth: int) -> dict:
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
    """A container's size and a sample of it, each read separately.

    `len` and the sample are two independent calls into the object and fail
    independently: a `list` subclass with a raising `__iter__` still has a
    readable length, and a `dict` subclass with a raising `__len__` can still
    be sampled. `len` is None when it could not be read -- never 0, which
    `watch` would compare against as a fact -- and "sample" is absent rather
    than partial, because half a materialised sample is not a sample of
    anything.
    """
    unread: list = []
    n = _guarded(lambda: len(obj), unread, "len")
    out = {"k": kind, "type": _type_name(obj), "len": n, "oid": id(obj)}
    if depth >= CAPS["depth"]:
        out["trunc"] = True
        capture_stats["truncated"] += 1
    else:
        sample = _guarded(lambda: sampler(obj, depth + 1), unread, "sample")
        if sample is not None:
            out["sample"] = sample
        # Only a length that was actually read can say the sample fell short.
        if n is not None and n > CAPS["sample"]:
            out["trunc"] = True
            capture_stats["truncated"] += 1
    if unread:
        out["unread"] = unread
    return out


def _capture_obj(obj) -> dict:
    out = {"k": "obj", "type": _type_name(obj), "oid": id(obj)}
    try:
        r = repr(obj)
    except BaseException:
        r = f"<{_type_name(obj)} repr-raised>"
        out["trunc"] = True
        out["unread"] = ["repr"]
        capture_stats["truncated"] += 1
    s, t = _trunc_str(r, CAPS["repr"])
    out["repr"] = s
    if t:
        out["trunc"] = True
    return out


def capture_exc(exc: BaseException, serial: int | None = None) -> dict:
    """Capture one exception.

    `oid` is `id(exc)` and is NOT an identity: CPython recycles addresses, so
    two distinct exceptions routinely share one -- measured, in a plain retry
    loop. `serial` is the exact identity, minted by the tracer's exception
    state machine while it holds a strong reference to the object, and is
    absent only where the recorder genuinely does not know it (and in traces
    recorded before serials existed).

    `str(exc)` is the observed program's `__str__`, guarded like every other
    read here: an exception whose message cannot be read is reported as
    exactly that, never as an exception with an empty message.
    """
    unread: list = []
    text = _guarded(lambda: str(exc), unread, "msg")
    msg = "" if text is None else _trunc_str(text, CAPS["str"])[0]
    out = {"type": _type_name(exc), "msg": msg, "oid": id(exc)}
    if unread:
        out["unread"] = unread
    if serial is not None:
        out["serial"] = serial
    return out
