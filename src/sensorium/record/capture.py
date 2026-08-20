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


def plain_str(s):
    """`s` as an EXACT `str`; `s` unchanged if it is not a `str` at all.

    A `str` subclass instance in a payload is a live object with live
    dunders, and a payload outlives every guard in this module: `_on_line`
    compares captures with `!=` (running `__eq__`) and `writer.add_event`
    json-encodes them with `default=repr` (running `__repr__`), both on the
    recorder's own thread and both outside anything here. Measured at
    6649bf0, on programs that run clean standalone: a `str` subclass with a
    raising `__eq__` killed the traced program at `tracer.py:467`, and one
    whose `__len__` overshot the cap while its `__getitem__` returned an
    object with a raising `__repr__` killed it inside `json.dumps` -- the
    latter in DEFAULT mode, through ordinary argument capture.

    `str.__str__` rather than `str(s)`: `str()` honours a `__str__`
    override, which can hand back another subclass instance (measured:
    `str(ES("abc"))` returned an `ES`), while the unbound base slot reads
    the underlying buffer and cannot be intercepted -- it also returns the
    TRUE characters rather than whatever the override claims. Total by
    construction: it can neither raise nor return a subclass.
    """
    if type(s) is str:
        return s
    try:
        out = str.__str__(s)
    except BaseException:
        return s
    return out if type(out) is str else s


def plain_num(n):
    """An `int`/`float` subclass as its exact base type; `n` unchanged else.

    Same hazard and same reasoning as `plain_str` -- `{"k": "num", "v": obj}`
    embedded the live object -- with one addition: `int()` and `float()`
    honour `__int__`/`__float__`, which can both LIE about the value and hand
    back another subclass instance (measured: `int(EI(7))` returned 99). The
    unbound base slots read the underlying value.

    `issubclass(type(n), ...)`, NOT `isinstance(n, ...)`: isinstance consults
    the INSTANCE's `__class__` when the type check is not an exact match, and a
    `__class__` property can make that raise -- the very kind of program dunder
    this normalisation exists to keep out of a payload. Dispatching on the type
    touches no instance dunder, so like `plain_str` this is total by
    construction: it can neither raise nor return a subclass.
    """
    t = type(n)
    if t is int or t is float or t is bool:
        return n
    try:
        if issubclass(t, int):
            out = int.__int__(n)
        elif issubclass(t, float):
            out = float.__float__(n)
        else:
            return n
    except BaseException:
        return n
    return out if type(out) in (int, float) else n


def type_name(obj) -> str:
    """`type(obj).__name__` -- which a metaclass property can make raise,
    and which it can also make return a live `str` subclass instance."""
    try:
        return plain_str(type(obj).__name__)
    except BaseException:
        return "?"


def _trunc_str(s: str, cap: int) -> tuple[str, bool]:
    """Clip a string to `cap`, and NORMALISE it on the way through.

    The single funnel every string in a payload passes: the `str` branch of
    `_capture`, `_capture_obj`'s repr, and `capture_exc`'s message. `repr()`
    and `str()` are both free to return a `str` SUBCLASS, so normalising
    here rather than at each call site is what makes "no payload holds a
    live object" a property of the module instead of a habit -- and it also
    means `len(s)` and `s[:cap]` below run against a plain string rather
    than against the observed program's `__len__` and `__getitem__`.
    """
    s = plain_str(s)
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
        return {"k": "unread", "type": type_name(obj), "oid": id(obj),
                "unread": ["value"]}


def _capture(obj, depth: int) -> dict:
    if obj is None:
        return {"k": "none"}
    if isinstance(obj, bool):
        return {"k": "bool", "v": obj}     # `bool` cannot be subclassed
    if isinstance(obj, (int, float)):
        return {"k": "num", "v": plain_num(obj)}
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
    out = {"k": kind, "type": type_name(obj), "len": n, "oid": id(obj)}
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
    out = {"k": "obj", "type": type_name(obj), "oid": id(obj)}
    try:
        r = repr(obj)
    except BaseException:
        r = f"<{type_name(obj)} repr-raised>"
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
    # The clip is INSIDE the guard: `str(exc)` may return a `str` subclass,
    # and normalising one runs no user code but reading a hostile `__len__`
    # would -- see `_trunc_str`. `capture_exc` is its own entry point, with
    # no outer guard above it, so nothing here may raise.
    msg = _guarded(lambda: _trunc_str(str(exc), CAPS["str"])[0], unread, "msg")
    out = {"type": type_name(exc), "msg": "" if msg is None else msg,
           "oid": id(exc)}
    if unread:
        out["unread"] = unread
    if serial is not None:
        out["serial"] = serial
    return out
