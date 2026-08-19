"""Shared plain-text formatting: dense, stable, one fact per line."""


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
        return f"{v['type']}[{v['len']}]=[{inner}{more}]"
    if k == "map":
        pairs = ", ".join(f"{fmt_value(a)}: {fmt_value(b)}"
                          for a, b in v.get("sample", []))
        more = ", ..." if v.get("trunc") else ""
        return f"{v['type']}[{v['len']}]={{{pairs}{more}}}"
    if k == "obj":
        return f"{v['type']}#{v['oid']}"
    return "?"


def fmt_args(args: dict, limit: int = 4) -> str:
    parts = [f"{n}={fmt_value(v)}" for n, v in list(args.items())[:limit]]
    if len(args) > limit:
        parts.append("...")
    return ", ".join(parts)


def fmt_exc(e: dict) -> str:
    return f"{e['type']}({e['msg']!r})"


def fmt_event(trace, e) -> str:
    code = trace.code(e.code_id) if e.code_id is not None else None
    q = code.qualname if code else "?"
    p = e.payload or {}
    if e.kind == "CALL":
        body = f"{q}({fmt_args(p.get('args', {}))})"
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
    empty deltas and a non-empty unbound -- render both, drop neither."""
    deltas = ", ".join(f"{n}={fmt_value(v)}"
                       for n, v in p.get("deltas", {}).items())
    unbound = p.get("unbound", [])
    parts = [s for s in (deltas, f"unbound:{','.join(unbound)}"
                          if unbound else "") if s]
    return "  " + "  ".join(parts) if parts else ""


def more_note(total: int, shown: int, hint: str) -> str | None:
    if shown >= total:
        return None
    return f"... {total - shown} more; continue with: {hint}"


def parse_eref(s: str) -> int:
    return int(s.lstrip("ef"))


def parse_fref(s: str) -> int:
    return int(s.lstrip("ef"))
