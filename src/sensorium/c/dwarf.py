"""DWARF image index for the C recorder.

One pass over the compilation units builds a ``Func`` per ``low_pc``.
Types are the plain objects ``decode.py`` walks; nothing here is asked
again on the per-call path. Addresses are unrelocated ELF ``low_pc``
values, the same numbers a ``.scplan`` stores. The converter subtracts
the load bias from ``objs.txt`` before lookup, so PIE and non-PIE use
the same numbers.
"""
from __future__ import annotations

import os
from bisect import bisect_right

from sensorium.c.decode import UNREAD, VOID, CType, Member
from sensorium.c.plan import classify_return

try:
    from elftools.dwarf.descriptions import describe_form_class
    from elftools.elf.elffile import ELFFile
except ImportError as e:  # pragma: no cover - the tests skip this case
    raise ImportError(
        "pyelftools is required to read DWARF (pip install pyelftools)"
    ) from e

_DW_OP_REG6 = 0x56
_DW_OP_BREG6 = 0x76
_DW_OP_FBREG = 0x91
_DW_OP_CFA = 0x9C
_DW_OP_PLUS_UCONST = 0x23

_STRIP = {
    "DW_TAG_typedef", "DW_TAG_const_type", "DW_TAG_volatile_type",
    "DW_TAG_restrict_type",
}
_FUNC_TYPES = {"STT_FUNC", "STT_GNU_IFUNC", "STT_LOOS"}


class Param:
    """One formal parameter. ``off`` is None when the slot is not a
    plain ``DW_OP_fbreg`` (optimized out, a register, or a location list)."""

    __slots__ = ("name", "off", "typ")

    def __init__(self, name, off, typ):
        self.name = name
        self.off = off
        self.typ = typ


class Func:
    """One subprogram. ``ret_type`` is the type ``classify_return`` saw,
    so a mixed struct still carries its eightbyte map."""

    __slots__ = (
        "addr", "name", "file", "line", "params", "ret_type",
        "ret_class", "ret_nreg", "ret_size",
    )

    def __init__(self, addr, name, file, line, params, ret_type):
        self.addr = addr
        self.name = name
        self.file = file
        self.line = line
        self.params = params
        self.ret_type = ret_type if ret_type is not None else VOID
        cls, nreg, size = classify_return(self.ret_type)
        self.ret_class = cls
        self.ret_nreg = nreg
        self.ret_size = size


class DwarfImage:
    """Functions keyed by unrelocated ``low_pc``."""

    def __init__(self, path):
        self.path = os.fspath(path)
        self.funcs: dict[int, Func] = {}
        self._types: dict[int, CType] = {}
        self._names: dict[int, str] = {}
        self._spans: list[tuple] = []
        self._starts: list[int] = []
        self._syms: list[tuple] = []
        self._sym_addrs: list[int] = []
        with open(self.path, "rb") as fh:
            elf = ELFFile(fh)
            self._load_syms(elf)
            if elf.has_dwarf_info():
                dwarf = elf.get_dwarf_info()
                for cu in dwarf.iter_CUs():
                    self._cu(dwarf, cu)
        self._finish_lines()

    def line_at(self, addr):
        """``(file, line)`` for an unrelocated address, or None in a gap."""
        if not self._starts:
            return None
        i = bisect_right(self._starts, addr) - 1
        if i < 0:
            return None
        start, end, file, line = self._spans[i]
        if start <= addr < end:
            return (file, line)
        return None

    def symbol_at(self, addr):
        """Innermost function symbol covering an unrelocated address."""
        if not self._sym_addrs:
            return None
        i = bisect_right(self._sym_addrs, addr) - 1
        best = None
        best_span = None
        while i >= 0:
            val, end, name = self._syms[i]
            if best is not None and addr - val >= best_span:
                break
            if val <= addr < end:
                span = end - val
                if best is None or span < best_span:
                    best = name
                    best_span = span
            i -= 1
        return best

    def _cu(self, dwarf, cu) -> None:
        top = cu.get_top_DIE()
        comp = _text(top, "DW_AT_comp_dir") or ""
        cu_name = _text(top, "DW_AT_name") or "?"
        version = cu.header.version
        files = _files(dwarf, cu, comp)
        self._lines(dwarf, cu, files, version)
        for die in cu.iter_DIEs():
            if die.tag != "DW_TAG_subprogram":
                continue
            addr = _low_pc(die)
            if addr is None or addr in self.funcs:
                continue
            if _flag(die, "DW_AT_declaration") and "DW_AT_low_pc" not in die.attributes:
                continue
            origin = _named(die)
            name = _text(origin, "DW_AT_name") or f"fn_{addr:x}"
            file = _decl_file(die, origin, files, comp, cu_name, version)
            line = _decl_line(die) or _decl_line(origin)
            kind = _frame_kind(die) or _frame_kind(origin)
            params = _params(self, die, origin, kind)
            tdie = _follow(origin, "DW_AT_type") or _follow(die, "DW_AT_type")
            ret = VOID if tdie is None else self._type(tdie)
            self.funcs[addr] = Func(addr, name, file, line, params, ret)

    def _lines(self, dwarf, cu, files, version) -> None:
        try:
            lp = dwarf.line_program_for_CU(cu)
        except Exception:
            return
        if lp is None:
            return

        def fidx(i):
            slot = i if version >= 5 else i - 1
            if isinstance(slot, int) and 0 <= slot < len(files):
                return files[slot]
            return "<unknown>"

        open_row = None
        for entry in lp.get_entries():
            st = entry.state
            if st is None:
                continue
            if open_row is not None:
                start, file, line = open_row
                if st.address > start:
                    self._spans.append((start, st.address, file, line))
                open_row = None
            if not st.end_sequence:
                open_row = (st.address, fidx(st.file), st.line)

    def _finish_lines(self) -> None:
        spans = sorted(self._spans, key=lambda s: (s[0], s[1]))
        dedup = {}
        order = []
        for start, end, file, line in spans:
            if start not in dedup:
                order.append(start)
            dedup[start] = (start, end, file, line)
        self._spans = [dedup[s] for s in order]
        self._starts = order

    def _load_syms(self, elf) -> None:
        rows = []
        for sec in (".symtab", ".dynsym"):
            table = elf.get_section_by_name(sec)
            if table is None:
                continue
            for sym in table.iter_symbols():
                if sym["st_info"]["type"] not in _FUNC_TYPES:
                    continue
                name = sym.name
                if not name:
                    continue
                val = int(sym["st_value"])
                size = int(sym["st_size"] or 0)
                if val == 0 and size == 0:
                    continue
                rows.append((val, val + max(size, 1), name))
        rows.sort()
        self._syms = rows
        self._sym_addrs = [r[0] for r in rows]

    def _type(self, die, depth=0):
        if die is None or depth > 24:
            return UNREAD
        seen = die.offset
        hit = self._types.get(seen)
        if hit is not None:
            return hit
        die = _strip(die)
        if die is None:
            self._types[seen] = UNREAD
            return UNREAD
        key = die.offset
        cached = self._types.get(key)
        if cached is not None:
            self._types[seen] = cached
            return cached
        tag = die.tag
        if tag == "DW_TAG_base_type":
            return self._store(seen, key, _base(die))
        if tag == "DW_TAG_pointer_type":
            return self._pointer(die, seen, key, depth)
        if tag == "DW_TAG_enumeration_type":
            return self._store(seen, key, self._enum(die))
        if tag in ("DW_TAG_structure_type", "DW_TAG_union_type",
                   "DW_TAG_class_type"):
            return self._struct(die, seen, key, tag, depth)
        if tag == "DW_TAG_array_type":
            return self._array(die, seen, key, depth)
        if tag == "DW_TAG_subroutine_type":
            return self._store(seen, key, CType("ptr", 8, "void ()"))
        if tag == "DW_TAG_unspecified_type":
            return self._store(seen, key, VOID)
        return self._store(seen, key, UNREAD)

    def _store(self, seen, key, typ):
        self._types[key] = typ
        self._types[seen] = typ
        return typ

    def _pointer(self, die, seen, key, depth):
        size = _size_attr(die) or 8
        typ = CType("ptr", size, "void *")
        self._types[key] = typ
        self._types[seen] = typ
        target_die = _follow(die, "DW_AT_type")
        target = self._type(target_die, depth + 1) if target_die is not None else None
        if target_die is None:
            typ.name = "void *"
        else:
            typ.name = self._render(target_die) + " *"
        typ.is_cstr = bool(
            target is not None and target.kind == "int"
            and target.is_char and target.size == 1)
        return typ

    def _enum(self, die):
        size = _size_attr(die) or 4
        enc = _int_attr(die, "DW_AT_encoding")
        signed = enc not in (0x07, 0x08)
        members = {}
        bits = size * 8
        for child in die.iter_children():
            if child.tag != "DW_TAG_enumerator":
                continue
            name = _text(child, "DW_AT_name")
            val = child.attributes.get("DW_AT_const_value")
            if name is None or val is None:
                continue
            try:
                n = int(val.value)
            except (TypeError, ValueError):
                continue
            if signed and bits and 0 <= n < (1 << bits) and n >= (1 << (bits - 1)):
                n -= 1 << bits
            members[n] = name
        raw = _text(die, "DW_AT_name")
        label = "enum " + raw if raw else "enum"
        return CType("enum", size, label, signed=signed, enums=members)

    def _struct(self, die, seen, key, tag, depth):
        kind = "union" if tag == "DW_TAG_union_type" else "struct"
        label = self._render(die)
        size = _size_attr(die) or 0
        typ = CType(kind, size, label, members=[])
        self._types[key] = typ
        self._types[seen] = typ
        members = []
        for child in die.iter_children():
            if child.tag != "DW_TAG_member":
                continue
            mname = _text(child, "DW_AT_name") or "?"
            mtyp = self._type(_follow(child, "DW_AT_type"), depth + 1)
            off = _member_off(child)
            bit = _int_attr(child, "DW_AT_bit_size")
            members.append(Member(
                mname, off, mtyp, bit_size=bit,
                bit_pos=_bit_pos(child, off, bit, mtyp)))
        typ.members = members
        if not typ.size:
            end = 0
            for m in members:
                if m.bit_size or m.typ is None:
                    continue
                end = max(end, m.offset + (m.typ.size or 0))
            typ.size = end
        return typ

    def _array(self, die, seen, key, depth):
        elem = self._type(_follow(die, "DW_AT_type"), depth + 1)
        count = _array_count(die)
        es = elem.size if elem is not None else 0
        size = _size_attr(die)
        if size is None and count is not None and es:
            size = count * es
        label = self._render(die)
        typ = CType("array", size or 0, label, elem=elem, count=count)
        return self._store(seen, key, typ)

    def _render(self, die, stack=None) -> str:
        """Display name. Typedefs expand. const, volatile and restrict stay."""
        if die is None:
            return "void"
        off = die.offset
        hit = self._names.get(off)
        if hit is not None:
            return hit
        if stack is None:
            stack = set()
        if off in stack:
            return "..."
        stack.add(off)
        try:
            tag = die.tag
            if tag == "DW_TAG_typedef":
                name = self._render(_follow(die, "DW_AT_type"), stack)
            elif tag == "DW_TAG_const_type":
                name = "const " + self._render(_follow(die, "DW_AT_type"), stack)
            elif tag == "DW_TAG_volatile_type":
                name = "volatile " + self._render(_follow(die, "DW_AT_type"), stack)
            elif tag == "DW_TAG_restrict_type":
                name = "restrict " + self._render(_follow(die, "DW_AT_type"), stack)
            elif tag == "DW_TAG_pointer_type":
                name = self._render(_follow(die, "DW_AT_type"), stack) + " *"
            elif tag == "DW_TAG_base_type":
                name = _text(die, "DW_AT_name") or "void"
            elif tag == "DW_TAG_structure_type":
                raw = _text(die, "DW_AT_name")
                name = "struct " + raw if raw else "struct"
            elif tag == "DW_TAG_union_type":
                raw = _text(die, "DW_AT_name")
                name = "union " + raw if raw else "union"
            elif tag == "DW_TAG_class_type":
                raw = _text(die, "DW_AT_name")
                name = "class " + raw if raw else "class"
            elif tag == "DW_TAG_enumeration_type":
                raw = _text(die, "DW_AT_name")
                name = "enum " + raw if raw else "enum"
            elif tag == "DW_TAG_array_type":
                elem = self._render(_follow(die, "DW_AT_type"), stack)
                count = _array_count(die)
                name = f"{elem}[{count}]" if count is not None else f"{elem}[]"
            elif tag == "DW_TAG_subroutine_type":
                name = "void ()"
            elif tag == "DW_TAG_unspecified_type":
                name = _text(die, "DW_AT_name") or "void"
            else:
                name = _text(die, "DW_AT_name") or "?"
        finally:
            stack.discard(off)
        self._names[off] = name
        return name


def _params(image, die, origin, kind):
    kids = [c for c in die.iter_children()
            if c.tag == "DW_TAG_formal_parameter"]
    if not kids and origin is not die:
        kids = [c for c in origin.iter_children()
                if c.tag == "DW_TAG_formal_parameter"]
    out = []
    for i, child in enumerate(kids):
        if _flag(child, "DW_AT_artificial"):
            continue
        src = _named(child)
        name = _text(src, "DW_AT_name") or _text(child, "DW_AT_name") or f"arg{i}"
        typ = image._type(_follow(src, "DW_AT_type") or _follow(child, "DW_AT_type"))
        off = _param_off(child, kind)
        if off is None:
            off = _param_off(src, kind)
        out.append(Param(name, off, typ))
    return out


def _low_pc(die):
    attr = die.attributes.get("DW_AT_low_pc")
    if attr is None:
        return None
    try:
        return int(attr.value)
    except (TypeError, ValueError):
        return None


def _frame_kind(die):
    """``cfa`` when the frame base is ``DW_OP_call_frame_cfa`` (gcc -O0).
    ``rbp`` when it is ``DW_OP_reg6`` (clang -O0). Anything else is not
    a single offset the runtime can add to ``rbp + 16``."""
    if die is None:
        return None
    fb = die.attributes.get("DW_AT_frame_base")
    if fb is None or describe_form_class(fb.form) != "exprloc":
        return None
    raw = list(_as_bytes(fb.value))
    if raw == [_DW_OP_CFA]:
        return "cfa"
    if raw == [_DW_OP_REG6]:
        return "rbp"
    return None


def _param_off(die, kind):
    """CFA-relative slot, or None. ``DW_OP_fbreg`` is already CFA-relative
    when the frame base is the CFA. An ``rbp`` frame base, and
    ``DW_OP_breg6``, sit 16 bytes below the CFA (saved rbp and the
    return address). Extra ops are not a slot."""
    if die is None or kind is None:
        return None
    loc = die.attributes.get("DW_AT_location")
    if loc is None or describe_form_class(loc.form) != "exprloc":
        return None
    raw = _as_bytes(loc.value)
    if not raw:
        return None
    if raw[0] == _DW_OP_FBREG:
        off, n = _sleb(raw, 1)
        if off is None or n != len(raw):
            return None
        if kind == "rbp":
            off -= 16
        return off
    if raw[0] == _DW_OP_BREG6:
        off, n = _sleb(raw, 1)
        if off is None or n != len(raw):
            return None
        return off - 16
    return None


def _bit_pos(die, byte_off, bit_size, typ):
    """LSB of a bitfield from the start of the value.

    ``DW_AT_data_bit_offset`` is already that position. GCC's
    ``DW_AT_bit_offset`` counts down from the high bit of the container.
    """
    if bit_size is None:
        return None
    data = _int_attr(die, "DW_AT_data_bit_offset")
    if data is not None:
        return data
    bit_off = _int_attr(die, "DW_AT_bit_offset")
    if bit_off is None:
        return None
    container = _size_attr(die) or (typ.size if typ is not None else 0) or 0
    cbits = container * 8
    if cbits <= 0:
        return None
    lsb = cbits - bit_off - bit_size
    if lsb < 0:
        return None
    return byte_off * 8 + lsb


def _member_off(die) -> int:
    attr = die.attributes.get("DW_AT_data_member_location")
    if attr is None:
        return 0
    if isinstance(attr.value, int):
        return attr.value
    raw = _as_bytes(attr.value)
    if raw[:1] == bytes([_DW_OP_PLUS_UCONST]):
        n, _i = _uleb(raw, 1)
        return n or 0
    if len(raw) == 1 and 0x30 <= raw[0] <= 0x4F:
        return raw[0] - 0x30
    return 0


def _base(die):
    enc = _int_attr(die, "DW_AT_encoding") or 0
    size = _size_attr(die) or 0
    name = _text(die, "DW_AT_name") or "int"
    if enc == 0x02:
        return CType("bool", size or 1, name)
    if enc == 0x04:
        return CType("float", size, name)
    signed = enc in (0x05, 0x06)
    # char-sized signed_char / unsigned_char, and a 1-byte type named
    # char. A pointer to that is FLAG_CSTR; a pointer to a pointer is not.
    # Clang sometimes tags plain char as DW_ATE_signed (5) or unsigned (7).
    is_char = size == 1 and (
        enc in (0x06, 0x08)
        or name in ("char", "signed char", "unsigned char"))
    if enc in (0x05, 0x06, 0x07, 0x08, 0x01) or name:
        return CType("int", size, name, signed=signed, is_char=is_char)
    return UNREAD


def _array_count(die):
    for child in die.iter_children():
        if child.tag != "DW_TAG_subrange_type":
            continue
        count = _int_attr(child, "DW_AT_count")
        if count is not None:
            return count
        upper = _int_attr(child, "DW_AT_upper_bound")
        if upper is None:
            return None
        lower = _int_attr(child, "DW_AT_lower_bound") or 0
        return upper - lower + 1
    return None


def _files(dwarf, cu, comp):
    """Line-table order, index 0 first. DWARF 4 directory 0 is ``comp_dir``
    and the file numbers are 1-based. DWARF 5 directories include
    ``comp_dir`` at index 0 and the file numbers are 0-based."""
    try:
        lp = dwarf.line_program_for_CU(cu)
    except Exception:
        return []
    if lp is None:
        return []
    version = cu.header.version
    dirs = []
    for entry in getattr(lp.header, "include_directory", []) or []:
        dirs.append(_dec(entry))
    out = []
    for entry in lp.header.file_entry:
        name = _dec(getattr(entry, "name", entry))
        di = getattr(entry, "dir_index", 0) or 0
        if version >= 5:
            directory = dirs[di] if 0 <= di < len(dirs) else ""
        elif di == 0:
            directory = comp
        elif 0 <= di - 1 < len(dirs):
            directory = dirs[di - 1]
        else:
            directory = ""
        out.append(_join_file(comp, directory, name))
    return out


def _join_file(comp, directory, name):
    if not name:
        return "?"
    if os.path.isabs(name):
        return os.path.normpath(name)
    if directory:
        if os.path.isabs(directory) or not comp or directory == comp:
            base = directory
        else:
            base = os.path.join(comp, directory)
    else:
        base = comp
    if base:
        return os.path.normpath(os.path.join(base, name))
    return os.path.normpath(name)


def _decl_file(die, origin, files, comp, cu_name, version):
    for src in (die, origin):
        if src is None:
            continue
        idx = _int_attr(src, "DW_AT_decl_file")
        if idx is None:
            continue
        slot = idx if version >= 5 else idx - 1
        if 0 <= slot < len(files):
            return files[slot]
    if comp and cu_name and not os.path.isabs(cu_name):
        return os.path.normpath(os.path.join(comp, cu_name))
    return cu_name or "?"


def _decl_line(die) -> int:
    if die is None:
        return 0
    n = _int_attr(die, "DW_AT_decl_line")
    return n or 0


def _strip(die):
    seen = set()
    while die is not None and id(die) not in seen:
        seen.add(id(die))
        if die.tag not in _STRIP:
            return die
        die = _follow(die, "DW_AT_type")
    return None


def _named(die):
    seen = set()
    cur = die
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if "DW_AT_name" in cur.attributes:
            return cur
        nxt = _follow(cur, "DW_AT_abstract_origin") or _follow(
            cur, "DW_AT_specification")
        if nxt is None:
            return cur
        cur = nxt
    return die


def _follow(die, attr):
    if die is None or attr not in die.attributes:
        return None
    try:
        return die.get_DIE_from_attribute(attr)
    except Exception:
        return None


def _text(die, attr):
    if die is None:
        return None
    a = die.attributes.get(attr)
    if a is None:
        return None
    return _dec(a.value)


def _dec(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, str):
        return value
    name = getattr(value, "name", None)
    if name is not None and name is not value:
        return _dec(name)
    return str(value) if value is not None else None


def _int_attr(die, attr):
    a = die.attributes.get(attr)
    if a is None:
        return None
    try:
        return int(a.value)
    except (TypeError, ValueError):
        return None


def _size_attr(die):
    return _int_attr(die, "DW_AT_byte_size")


def _flag(die, attr) -> bool:
    a = die.attributes.get(attr)
    if a is None:
        return False
    return bool(a.value)


def _as_bytes(value) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, list):
        return bytes(x & 0xFF for x in value)
    return b""


def _uleb(buf, i):
    n = shift = 0
    while i < len(buf):
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            return n, i
        shift += 7
    return None, i


def _sleb(buf, i):
    n = shift = 0
    while i < len(buf):
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            if b & 0x40:
                n -= 1 << shift
            return n, i
    return None, i
