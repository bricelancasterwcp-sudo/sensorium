"""Shared plain-text formatting: dense, stable, one fact per line."""


def _size(v: dict) -> str:
    """A container's length, or `?` where the object's `__len__` raised.

    `len` is None exactly when the capture could not read it (see
    `capture.py`). Printing 0 there would be the recorder inventing a size.
    """
    n = v.get("len")
    return "?" if n is None else str(n)


def _unread(v: dict) -> str:
    """Which reads the observed object refused, named rather than implied."""
    names = v.get("unread")
    return f" <unread: {','.join(names)}>" if names else ""


def fmt_value(v: dict | None) -> str:
    if v is None:
        return "?"
    k = v.get("k")
    if k == "none":
        return "None"
    if k in ("num", "bool"):
        return repr(v["v"])
    if k == "str":
        return repr(v["v"]) + ("~" if v.get("trunc") else "")
    if k == "seq":
        # A depth-capped capture omits "sample" entirely rather than
        # supplying an empty list -- always read it with .get, never [].
        inner = ", ".join(fmt_value(x) for x in v.get("sample", []))
        more = ", ..." if v.get("trunc") else ""
        return f"{v['type']}[{_size(v)}]=[{inner}{more}]{_unread(v)}"
    if k == "map":
        pairs = ", ".join(f"{fmt_value(a)}: {fmt_value(b)}"
                          for a, b in v.get("sample", []))
        more = ", ..." if v.get("trunc") else ""
        return f"{v['type']}[{_size(v)}]={{{pairs}{more}}}{_unread(v)}"
    if k == "obj":
        return f"{v['type']}#{v['oid']}{_unread(v)}"
    if k == "unread":
        # Nothing about this value could be read at all -- not even which
        # kind it is. Say so; do not render it as an object with no repr.
        return f"<unreadable {v.get('type', '?')}#{v.get('oid', '?')}>"
    return "?"


def fmt_args(args: dict, limit: int = 4) -> str:
    parts = [f"{n}={fmt_value(v)}" for n, v in list(args.items())[:limit]]
    if len(args) > limit:
        parts.append("...")
    return ", ".join(parts)


def fmt_exc(e: dict) -> str:
    # An exception whose `__str__` raised has no message the trace can quote.
    # `''` there would read as an exception raised with no message at all.
    if "msg" in (e.get("unread") or ()):
        return f"{e['type']}(<message unreadable: __str__ raised>)"
    return f"{e['type']}({e['msg']!r})"


def fmt_event(trace, e) -> str:
    code = trace.code(e.code_id) if e.code_id is not None else None
    q = code.qualname if code else "?"
    p = e.payload or {}
    if e.kind == "CALL":
        body = f"{q}({fmt_args(p.get('args', {}))}){_unread(p)}"
    elif e.kind == "RETURN":
        body = f"{q} -> {fmt_value(p.get('value'))}"
    elif e.kind in ("RAISE", "HANDLED"):
        body = f"{q} {e.kind.lower()} {fmt_exc(p['exc'])} L{e.line}"
    elif e.kind == "LINE":
        body = f"{q} L{e.line}{_fmt_line_tail(p)}"
    else:
        body = q
    return f"e{e.id} {e.kind:<7} {body}"


def _fmt_line_tail(p: dict) -> str:
    """LINE payloads carry "deltas" and may carry a sibling "unbound" list
    (names that went out of scope this step: `del x`, or the implicit
    unbind at the end of `except E as e:`). A step can legitimately have
    empty deltas and a non-empty unbound -- render both, drop neither.

    They may also carry `unread: ["locals"]`, when the frame's locals could
    not be read at all -- a mapping the program supplied, whose `items()`
    raised. That MUST render: empty deltas alone read as "nothing changed
    here", which is the opposite of what this event says."""
    deltas = ", ".join(f"{n}={fmt_value(v)}"
                       for n, v in p.get("deltas", {}).items())
    unbound = p.get("unbound", [])
    parts = [s for s in (deltas, f"unbound:{','.join(unbound)}"
                          if unbound else "", _unread(p).strip()) if s]
    return "  " + "  ".join(parts) if parts else ""


def more_note(total: int, shown: int, hint: str) -> str | None:
    if shown >= total:
        return None
    return f"... {total - shown} more; continue with: {hint}"


class RefError(ValueError):
    """A malformed event or frame reference given on the command line.

    Raised rather than let `int()` escape: every command that takes a ref
    (`grep --after`, `exceptions --after`, `flow --after`, `tree --root` /
    `--around`, `frame f<id>`) used to die with an uncaught ValueError
    traceback on a typo. `cli.main` turns this into a one-line refusal and
    exit 2 -- a traceback is a poor answer for a human and an actively
    confusing one for an agent parsing the output.
    """


def _parse_ref(s: str, sigil: str, kind: str) -> int:
    """`e12` / `12` -> 12. Anything else is a user error, not a crash.

    Only ONE leading sigil is accepted: `int(s.lstrip("ef"))` took "eef12"
    and "fe12" as 12, which quietly answers a question nobody asked.
    """
    body = s[1:] if s[:1] == sigil else s
    if not body.isdigit():
        raise RefError(f"{s!r} is not {kind} reference; expected "
                       f"{sigil}<id> such as {sigil}42")
    return int(body)


def parse_eref(s: str) -> int:
    return _parse_ref(s, "e", "an event")


def parse_fref(s: str) -> int:
    return _parse_ref(s, "f", "a frame")
