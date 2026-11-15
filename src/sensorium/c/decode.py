"""Decode raw argument and return bytes into sensorium value tags.

Types are plain objects built once by ``dwarf.py``. Decoding never touches
a DIE. Non-finite floats are ``dbg`` strings so the payload stays JSON.
"""
from __future__ import annotations

import math
import struct

from sensorium.c.format import RET_INT, RET_MEM, RET_SSE, RET_VOID, STR_CAP

_MASK64 = (1 << 64) - 1
_DEPTH = 4
_MEMBERS = 16
_ARRAY = 8


class Member:
    """One struct or union field. ``bit_pos`` is the LSB from the start
    of the value, or None when the bit offset was not in the DWARF."""

    __slots__ = ("name", "offset", "typ", "bit_size", "bit_pos")

    def __init__(self, name, offset, typ, bit_size=None, bit_pos=None):
        self.name = name
        self.offset = offset
        self.typ = typ
        self.bit_size = bit_size
        self.bit_pos = bit_pos


class CType:
    """A resolved type. ``eights`` is set only for a register-returned
    aggregate whose eightbytes are not all the same class."""

    __slots__ = (
        "kind", "size", "name", "signed", "is_cstr", "is_char",
        "enums", "members", "elem", "count", "eights",
    )

    def __init__(self, kind, size=0, name="", signed=False, is_cstr=False,
                 is_char=False, enums=None, members=None, elem=None,
                 count=None, eights=None):
        self.kind = kind
        self.size = size
        self.name = name
        self.signed = signed
        self.is_cstr = is_cstr
        self.is_char = is_char
        self.enums = enums
        self.members = members
        self.elem = elem
        self.count = count
        self.eights = eights


VOID = CType("void", 0, "void")
UNREAD = CType("unread", 0, "?")


def decode_param(typ, raw, slen, sbytes):
    """``raw`` is the parameter's bytes. ``slen`` / ``sbytes`` are the
    ``FLAG_CSTR`` capture: -2 NULL, -1 fault, 0 empty, else the bytes
    before the NUL. Anything else, including a missing slot, is unread."""
    if typ is None or typ.kind in ("void", "unread"):
        return {"k": "unread"}
    raw = raw or b""
    if typ.kind == "ptr" and typ.is_cstr and slen is not None:
        return _cstr(typ, slen, sbytes)
    return _value(typ, raw, 0)


def decode_return(typ, ret_class, rax, rdx, xmm0, xmm1, mem_bytes):
    """None for void. RET_INT packs rax, plus rdx when the value is wider
    than 8 bytes. RET_SSE unpacks xmm0, plus xmm1 when wider than 8, and
    the scalar float path reads f32 or f64 from the low bytes. RET_MEM
    decodes ``mem_bytes``. A short buffer is unread.

    A struct whose eightbytes use both register files keeps that map on
    the type. The V record always carries rax, rdx, xmm0 and xmm1, so the
    bytes are reassembled from the class of each eightbyte."""
    if typ is None or typ.kind == "void" or ret_class == RET_VOID:
        return None
    if ret_class == RET_MEM:
        buf = mem_bytes or b""
        if typ.size and len(buf) < typ.size:
            return {"k": "unread"}
        return decode_param(typ, buf, None, None)
    if typ.eights:
        raw = _assemble(typ, rax, rdx, xmm0, xmm1)
    elif ret_class == RET_SSE:
        raw = _pack(xmm0)
        if typ.size > 8:
            raw += _pack(xmm1)
    elif ret_class == RET_INT:
        raw = _pack(rax)
        if typ.size > 8:
            raw += _pack(rdx)
    else:
        return {"k": "unread"}
    if typ.size and len(raw) < typ.size:
        return {"k": "unread"}
    return decode_param(typ, raw, None, None)


def _pack(word) -> bytes:
    return struct.pack("<Q", int(word) & _MASK64)


def _assemble(typ, rax, rdx, xmm0, xmm1) -> bytes:
    pools = {"INT": [rax, rdx], "SSE": [xmm0, xmm1]}
    used = {"INT": 0, "SSE": 0}
    out = bytearray(8 * len(typ.eights))
    for i, cls in enumerate(typ.eights):
        if cls not in pools:
            continue
        n = used[cls]
        used[cls] = n + 1
        word = pools[cls][n] if n < 2 else 0
        out[i * 8:i * 8 + 8] = _pack(word)
    if typ.size and typ.size < len(out):
        return bytes(out[:typ.size])
    return bytes(out)


def _cstr(typ, slen, sbytes):
    if slen == -2:
        return {"k": "dbg", "v": f"({typ.name}) NULL"}
    if slen < 0:
        return {"k": "unread", "type": "char *"}
    if slen == 0:
        return {"k": "str", "v": ""}
    blob = sbytes or b""
    if b"\0" in blob:
        blob = blob.split(b"\0", 1)[0]
        cut = False
    else:
        cut = slen >= STR_CAP and len(blob) >= STR_CAP
    text = blob.decode("utf-8", "replace")
    out = {"k": "str", "v": text}
    if cut:
        out["trunc"] = True
    return out


def _scalar(typ, raw, bit_size):
    if typ.kind == "bool":
        n = _int(raw, typ.size, False, bit_size)
        if n is None:
            return {"k": "unread"}
        return {"k": "bool", "v": n != 0}
    if typ.kind == "float":
        return _float(raw, typ.size)
    if typ.kind == "ptr":
        if len(raw) < 8 and typ.size >= 8:
            return {"k": "unread"}
        width = typ.size or 8
        p = int.from_bytes(raw[:width], "little")
        shown = "NULL" if p == 0 else hex(p)
        return {"k": "dbg", "v": f"({typ.name}) {shown}"}
    if typ.kind == "enum":
        n = _int(raw, typ.size, typ.signed, bit_size)
        if n is None:
            return {"k": "unread"}
        name = typ.enums.get(n) if typ.enums else None
        if name is None:
            return {"k": "num", "v": n}
        return {"k": "dbg", "v": name}
    if typ.kind == "int":
        n = _int(raw, typ.size, typ.signed, bit_size)
        if n is None:
            return {"k": "unread"}
        return {"k": "num", "v": n}
    return {"k": "unread"}


def _int(raw, size, signed, bit_size):
    if bit_size:
        if len(raw) < 1:
            return None
        return int.from_bytes(raw, "little", signed=False)
    if size <= 0 or len(raw) < size:
        return None
    return int.from_bytes(raw[:size], "little", signed=signed)


def _float(raw, size):
    if size == 4 and len(raw) >= 4:
        v = struct.unpack("<f", raw[:4])[0]
    elif size == 8 and len(raw) >= 8:
        v = struct.unpack("<d", raw[:8])[0]
    elif size == 16 and len(raw) >= 16:
        return {"k": "dbg", "v": "0x" + raw[:16].hex()}
    else:
        return {"k": "unread"}
    if isinstance(v, float) and math.isnan(v):
        return {"k": "dbg", "v": "nan"}
    if isinstance(v, float) and math.isinf(v):
        return {"k": "dbg", "v": "-inf" if v < 0 else "inf"}
    return {"k": "num", "v": v}


def _bits(raw, bit_pos, bit_size, signed):
    nbytes = (bit_pos + bit_size + 7) // 8
    if bit_pos < 0 or bit_size <= 0 or len(raw) < nbytes:
        return None
    val = int.from_bytes(raw[:nbytes], "little")
    val = (val >> bit_pos) & ((1 << bit_size) - 1)
    if signed and val >> (bit_size - 1):
        val -= 1 << bit_size
    return val


def _value(typ, raw, depth):
    if typ is None or typ.kind in ("void", "unread"):
        return {"k": "unread"}
    raw = raw or b""
    if typ.kind in ("struct", "union"):
        if typ.size and not raw:
            return {"k": "unread"}
        return _aggregate(typ, raw, depth)
    if typ.kind == "array":
        return _array(typ, raw, depth)
    if typ.size and len(raw) < typ.size:
        return {"k": "unread"}
    return _scalar(typ, raw, 0)


def _aggregate(typ, raw, depth):
    if depth >= _DEPTH:
        return {"k": "dbg", "v": f"{typ.name} {{...}}"}
    parts = []
    members = typ.members or ()
    for m in members[:_MEMBERS]:
        parts.append(f"{m.name}={_show(_member(m, raw, depth))}")
    if len(members) > _MEMBERS:
        parts.append("...")
    return {"k": "dbg", "v": f"{typ.name} {{{', '.join(parts)}}}"}


def _member(m, raw, depth):
    if m.bit_size:
        if m.bit_pos is None:
            return {"k": "unread"}
        n = _bits(raw, m.bit_pos, m.bit_size, bool(m.typ and m.typ.signed))
        if n is None:
            return {"k": "unread"}
        if m.typ is not None and m.typ.kind == "enum":
            name = m.typ.enums.get(n) if m.typ.enums else None
            if name is not None:
                return {"k": "dbg", "v": name}
        if m.typ is not None and m.typ.kind == "bool":
            return {"k": "bool", "v": n != 0}
        return {"k": "num", "v": n}
    return _value(m.typ, raw[m.offset:], depth + 1)


def _array(typ, raw, depth):
    elem = typ.elem
    if elem is not None and elem.is_char:
        n = typ.count if typ.count is not None else len(raw)
        blob = raw[:n]
        nul = blob.find(b"\0")
        if nul >= 0:
            blob = blob[:nul]
        return {"k": "str", "v": blob.decode("utf-8", "replace")}
    if elem is None:
        return {"k": "unread"}
    n = typ.count or 0
    es = elem.size or 1
    shown = []
    for i in range(min(n, _ARRAY)):
        shown.append(_show(_value(elem, raw[i * es:(i + 1) * es], depth + 1)))
    if n > _ARRAY:
        shown.append("...")
    return {"k": "dbg", "v": "[" + ", ".join(shown) + "]"}


def _show(v) -> str:
    """Field text inside a struct. A field that did not decode is ``?``.

    The word ``unread`` is a capture kind, not something to paste into a
    value that did decode: a struct return is one ``dbg`` string, and a
    reader searching that string must not see a failure the field did
    not have.
    """
    if not isinstance(v, dict):
        return "?"
    k = v.get("k")
    if k == "str":
        return '"' + str(v.get("v", "")).replace("\\", "\\\\").replace(
            '"', '\\"') + '"'
    if k == "bool":
        return "true" if v.get("v") else "false"
    if k == "num":
        return str(v.get("v"))
    if k == "dbg":
        return str(v.get("v", "?"))
    return "?"
