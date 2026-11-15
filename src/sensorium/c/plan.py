"""Capture plans. One plan per image, addresses are unrelocated low_pc.

SysV x86-64 return class, simplified
------------------------------------
void (no type): RET_VOID, nreg 0, size 0.

Base float, double, and a 16-byte float (__float128, and long double,
which this pass does not put in x87): RET_SSE, nreg 1, or nreg 2 when
the size is greater than 8 and at most 16. Larger than 16 is RET_MEM.

Integers, enums, and pointers: RET_INT, nreg 1, or nreg 2 for a value
wider than 8 and at most 16 (__int128). Wider than 16 is RET_MEM.

Struct, union, class, and array: split into 8-byte eightbytes.

* An eightbyte is INTEGER if it holds any integer, pointer, or enum,
  SSE if it holds only float or double.
* MEMORY if a member crosses an eightbyte boundary, the aggregate is
  larger than 16 bytes, it needs more than two eightbytes, a field is
  unaligned for its type, or it has a flexible array member.
* Merging two classes in one eightbyte: MEMORY if either is MEMORY,
  else INTEGER if either is INTEGER, else SSE.
* More than two INTEGER or two SSE registers is MEMORY.

A mix of INTEGER and SSE eightbytes does not fit one plan class. INTEGER
wins for the label (RET_INT) and the eightbyte map is stored on the type
so the decoder can pull each eightbyte from rax/rdx or xmm0/xmm1. The V
record always carries all four registers.

RET_MEM records the real byte size up to 4096. The runtime caps the copy
at 256. RET_INT and RET_SSE store ret_size 0 and ret_nreg 1 or 2.
"""
from __future__ import annotations

from sensorium.c.format import (
    FLAG_CSTR, NO_SLOT, RET_INT, RET_MEM, RET_SSE, RET_VOID, FuncPlan,
    ParamPlan, write_plan,
)

_CAP = 4096


def write_image_plan(elf_path, out_path) -> None:
    """Write ``out_path`` for ``elf_path`` via ``format.write_plan``."""
    from sensorium.c.dwarf import DwarfImage

    image = DwarfImage(elf_path)
    funcs = []
    for addr, fn in image.funcs.items():
        params = []
        for p in fn.params:
            if p.off is None:
                params.append(ParamPlan(NO_SLOT, 0, 0))
                continue
            size = p.typ.size if p.typ is not None else 0
            if size < 0:
                size = 0
            if size > 256:
                size = 256
            flags = FLAG_CSTR if p.typ is not None and p.typ.is_cstr else 0
            params.append(ParamPlan(int(p.off), int(size), int(flags)))
        funcs.append(FuncPlan(int(addr), int(fn.ret_class), int(fn.ret_nreg),
                              int(fn.ret_size), tuple(params)))
    write_plan(out_path, funcs)


def classify_return(typ):
    """(ret_class, ret_nreg, ret_size) for a resolved type."""
    if typ is None or typ.kind == "void":
        return RET_VOID, 0, 0
    if typ.kind == "float":
        return _scalar(RET_SSE, typ.size)
    if typ.kind in ("int", "bool", "ptr", "enum"):
        return _scalar(RET_INT, typ.size)
    if typ.kind in ("struct", "union", "array"):
        return _aggregate(typ)
    return _scalar(RET_INT, typ.size)


def _scalar(cls, size):
    size = size or 0
    if size <= 0:
        return cls, 0, 0
    if size <= 8:
        return cls, 1, 0
    if size <= 16:
        return cls, 2, 0
    return RET_MEM, 0, min(size, _CAP)


def _mem(typ):
    return RET_MEM, 0, min(max(typ.size or 0, 0), _CAP)


def _aggregate(typ):
    if _flex(typ, set()) or (typ.size or 0) > 16:
        return _mem(typ)
    if not _aligned(typ, 0, set()):
        return _mem(typ)
    leaves = []
    if not _leaves(typ, 0, leaves, set()):
        return _mem(typ)
    size = typ.size or 0
    if size <= 0:
        return RET_INT, 0, 0
    n = (size + 7) // 8
    if n > 2:
        return _mem(typ)
    classes = ["NO"] * n
    for off, width, cls in leaves:
        if width <= 0:
            continue
        start = off // 8
        end = (off + width - 1) // 8
        if start != end or not 0 <= start < n:
            return _mem(typ)
        classes[start] = _merge(classes[start], cls)
    if "MEM" in classes:
        return _mem(typ)
    ints = sum(c == "INT" for c in classes)
    sses = sum(c == "SSE" for c in classes)
    if ints > 2 or sses > 2:
        return _mem(typ)
    used = tuple(c for c in classes if c in ("INT", "SSE"))
    if not used:
        return RET_INT, 0, 0
    if ints and sses:
        # Both register files. INTEGER wins the plan class; the map tells
        # the decoder which file each eightbyte came from.
        typ.eights = used
        return RET_INT, len(used), 0
    if ints:
        return RET_INT, ints, 0
    return RET_SSE, sses, 0


def _merge(a, b):
    if a == "NO" or a is None:
        return b
    if b == "NO" or b is None:
        return a
    if a == "MEM" or b == "MEM":
        return "MEM"
    if a == "INT" or b == "INT":
        return "INT"
    return "SSE"


def _cross(off, size):
    if size <= 0:
        return False
    return off // 8 != (off + size - 1) // 8


def _leaves(typ, base, out, stack):
    if typ is None:
        return False
    mark = id(typ)
    if mark in stack:
        return False
    if typ.kind in ("struct", "union"):
        stack.add(mark)
        try:
            for m in typ.members or ():
                if m.bit_size:
                    if m.bit_pos is None or _bit_cross(m.bit_pos, m.bit_size):
                        return False
                    out.append((m.bit_pos // 8, 1, "INT"))
                    continue
                if not _leaves(m.typ, base + m.offset, out, stack):
                    return False
            return True
        finally:
            stack.discard(mark)
    if typ.kind == "array":
        if typ.count is None or typ.elem is None:
            return False
        stack.add(mark)
        try:
            es = typ.elem.size or 0
            for i in range(typ.count):
                if not _leaves(typ.elem, base + i * es, out, stack):
                    return False
            return True
        finally:
            stack.discard(mark)
    if typ.kind == "float":
        if _cross(base, typ.size):
            return False
        out.append((base, typ.size, "SSE"))
        return True
    if _cross(base, typ.size or 1):
        return False
    out.append((base, typ.size or 1, "INT"))
    return True


def _bit_cross(bit_pos, bit_size):
    if bit_size <= 0:
        return False
    return bit_pos // 64 != (bit_pos + bit_size - 1) // 64


def _flex(typ, stack):
    if typ is None:
        return False
    mark = id(typ)
    if mark in stack:
        return False
    if typ.kind == "array":
        return typ.count is None
    if typ.kind in ("struct", "union"):
        stack.add(mark)
        try:
            return any(_flex(m.typ, stack) for m in (typ.members or ()))
        finally:
            stack.discard(mark)
    return False


def _nat(size):
    if size >= 16:
        return 16
    if size >= 8:
        return 8
    if size >= 4:
        return 4
    if size >= 2:
        return 2
    return 1


def _align(typ):
    if typ is None:
        return 1
    if typ.kind == "ptr":
        return 8
    if typ.kind in ("int", "bool", "float", "enum"):
        return _nat(typ.size or 1)
    if typ.kind == "array":
        return _align(typ.elem)
    if typ.kind in ("struct", "union"):
        als = [_align(m.typ) for m in (typ.members or ()) if not m.bit_size]
        return max(als) if als else 1
    return 1


def _aligned(typ, base, stack):
    if typ is None:
        return True
    mark = id(typ)
    if mark in stack:
        return True
    if typ.kind == "struct":
        stack.add(mark)
        try:
            for m in typ.members or ():
                if m.bit_size:
                    continue
                if (base + m.offset) % _align(m.typ) != 0:
                    return False
                if not _aligned(m.typ, base + m.offset, stack):
                    return False
            return True
        finally:
            stack.discard(mark)
    if typ.kind == "union":
        stack.add(mark)
        try:
            return all(
                _aligned(m.typ, base + m.offset, stack)
                for m in (typ.members or ()) if not m.bit_size)
        finally:
            stack.discard(mark)
    if typ.kind == "array" and typ.elem is not None:
        return _aligned(typ.elem, base, stack)
    return True
