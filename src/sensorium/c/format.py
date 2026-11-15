"""On-wire spool for the C recorder. Version 1. Little-endian.

The runtime (``c/rt/sensorium_c_rt.c``) and this module are the two
writers of one layout. Change either only together with the other.

Directory ``$SENSORIUM_C_ROOT/<pid>/`` per instrumented process:

  threads/t<N>.bin   per-thread record stream (main is tid 1)
  argv.json          this process's argv, a JSON list of strings
  boot.json          {"start_ts": <time.time()>}
  exit.json          {"status": int} or {"signal": int}
  threads.json       {"started": <extra threads created>, "live": [tid, ...]}
                     written at exit and from the fatal-signal handler
  warn.txt           one warning per line (``cet: ...``)
  objs.txt           ``<bias hex> <path>`` from dl_iterate_phdr; the main
                     executable's path is the literal ``<exe>``
  forks.json         [child pid, ...] if this process called fork

The driver owns ``$SENSORIUM_C_ROOT/side.json`` (invocation, the command
the user typed, the pid it waited on, harness_exit, compiler,
build_warnings, cwd) plus ``stdout.bin`` and ``stderr.bin`` for that pid.

A capture plan sits beside each linked image: ``<image>.scplan``.
Addresses in the plan are unrelocated ELF ``low_pc`` values.

Plan file
---------
``SCPL`` magic, ``u32`` version ``1``, ``u32`` count, then count
functions sorted by address:

  addr u64, ret_class u8, ret_nreg u8, ret_size u16, nparams u16
  then nparams times: off i32, size u16, flags u16

``ret_class`` is ``RET_VOID`` (0), ``RET_INT`` (1, rax and maybe rdx),
``RET_SSE`` (2, xmm0 and maybe xmm1), or ``RET_MEM`` (3, rax points at
the struct, ``ret_size`` bytes). ``off == NO_SLOT`` means the parameter
has no frame slot (optimized out, or a location list). ``FLAG_CSTR``
asks the runtime to copy a NUL-terminated byte string through
``process_vm_readv``.

Thread file
-----------
``SCR1`` magic, ``u32`` tid, then records. Each record header is 56
bytes (``<BxxxQQQQQQI``: kind, 3 zero pad bytes, seq, ts, a, b, c, d,
extra_len) plus ``extra``:

  kind u8, pad 3 zero bytes, seq u64, ts u64, a u64, b u64, c u64, d u64,
  extra_len u32, extra bytes

Kinds:

  E  enter. a=fn, b=call site, c=cfa (rbp+16), d=0.
     extra is an argument blob (below).
  X  cyg exit hook, before the ret. a=fn, b=call site.
  V  return trampoline. a=rax, b=rdx, c=xmm0 bits, d=xmm1 bits.
     extra is the memory return bytes when the plan says ``RET_MEM``.
  S  fatal signal. a=signo, b=si_addr, c=rip, d=si_code.
     extra is up to 512 bytes at rsp.
  A  assert, before abort. a=line. extra is
     ``assertion\\0file\\0function`` in utf-8, each part clipped.
  J  longjmp. a=target rbp, b=target rsp, c=target pc,
     d=number of shadow frames abandoned.
  F  fork, in the parent. a=child pid.

Argument blob
-------------
``nparams u16``, ``pad u16``, then each parameter in plan order:

  off i32, size u16, flags u16, raw[size] if size else nothing,
  and if ``FLAG_CSTR``: slen i32, then ``slen`` bytes when ``slen > 0``.

``slen`` is ``-1`` if the read faulted, ``-2`` if the pointer was NULL,
``0`` for an empty string, or the byte count before the NUL. A count of
``STR_CAP`` with no NUL in those bytes is a truncated string.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIC_PLAN = b"SCPL"
MAGIC_THREAD = b"SCR1"
VERSION = 1

RET_VOID = 0
RET_INT = 1
RET_SSE = 2
RET_MEM = 3

NO_SLOT = -0x80000000
FLAG_CSTR = 1
FLAG_TRUNC = 2

STR_CAP = 64
STACK_BYTES = 512

KIND_ENTER = ord("E")
KIND_EXIT = ord("X")
KIND_RET = ord("V")
KIND_SIGNAL = ord("S")
KIND_ASSERT = ord("A")
KIND_LONGJMP = ord("J")
KIND_FORK = ord("F")

_PLAN_HEAD = struct.Struct("<4sII")
_FUNC = struct.Struct("<QBBHH")
_PARAM = struct.Struct("<iHH")
_THREAD_HEAD = struct.Struct("<4sI")
_REC = struct.Struct("<BxxxQQQQQQI")
_ARG_HEAD = struct.Struct("<HH")
_SLEN = struct.Struct("<i")


@dataclass(frozen=True)
class ParamPlan:
    off: int
    size: int
    flags: int


@dataclass(frozen=True)
class FuncPlan:
    addr: int
    ret_class: int
    ret_nreg: int
    ret_size: int
    params: tuple[ParamPlan, ...]


def write_plan(path, funcs: list[FuncPlan]) -> None:
    """Write ``path`` as a version-1 plan, functions sorted by address."""
    ordered = sorted(funcs, key=lambda f: f.addr)
    out = bytearray(_PLAN_HEAD.pack(MAGIC_PLAN, VERSION, len(ordered)))
    for fn in ordered:
        out += _FUNC.pack(fn.addr, fn.ret_class, fn.ret_nreg, fn.ret_size,
                          len(fn.params))
        for p in fn.params:
            out += _PARAM.pack(p.off, p.size, p.flags)
    with open(path, "wb") as fh:
        fh.write(out)


def read_plan(path) -> list[FuncPlan]:
    """Read a plan file. Raises ``ValueError`` on a bad header."""
    data = open(path, "rb").read()
    if len(data) < _PLAN_HEAD.size:
        raise ValueError(f"{path}: plan shorter than a header")
    magic, version, count = _PLAN_HEAD.unpack_from(data, 0)
    if magic != MAGIC_PLAN or version != VERSION:
        raise ValueError(f"{path}: not a version-{VERSION} plan")
    out = []
    i = _PLAN_HEAD.size
    for _ in range(count):
        if i + _FUNC.size > len(data):
            raise ValueError(f"{path}: truncated function")
        addr, cls, nreg, size, nparams = _FUNC.unpack_from(data, i)
        i += _FUNC.size
        params = []
        for _p in range(nparams):
            if i + _PARAM.size > len(data):
                raise ValueError(f"{path}: truncated parameter")
            off, psz, flags = _PARAM.unpack_from(data, i)
            i += _PARAM.size
            params.append(ParamPlan(off, psz, flags))
        out.append(FuncPlan(addr, cls, nreg, size, tuple(params)))
    return out


@dataclass(frozen=True)
class ArgRaw:
    off: int
    size: int
    flags: int
    raw: bytes
    slen: int | None
    sbytes: bytes | None


def pack_args(args: list[ArgRaw]) -> bytes:
    out = bytearray(_ARG_HEAD.pack(len(args), 0))
    for a in args:
        out += _PARAM.pack(a.off, a.size, a.flags)
        if a.size:
            if len(a.raw) != a.size:
                raise ValueError("raw length does not match size")
            out += a.raw
        if a.flags & FLAG_CSTR:
            slen = -1 if a.slen is None else a.slen
            out += _SLEN.pack(slen)
            if slen > 0:
                blob = a.sbytes or b""
                if len(blob) != slen:
                    raise ValueError("string length does not match slen")
                out += blob
    return bytes(out)


def unpack_args(blob: bytes) -> list[ArgRaw]:
    if len(blob) < _ARG_HEAD.size:
        raise ValueError("argument blob shorter than a header")
    n, _pad = _ARG_HEAD.unpack_from(blob, 0)
    i = _ARG_HEAD.size
    out = []
    for _ in range(n):
        if i + _PARAM.size > len(blob):
            raise ValueError("truncated argument")
        off, size, flags = _PARAM.unpack_from(blob, i)
        i += _PARAM.size
        raw = b""
        if size:
            if i + size > len(blob):
                raise ValueError("truncated argument bytes")
            raw = blob[i:i + size]
            i += size
        slen = None
        sbytes = None
        if flags & FLAG_CSTR:
            if i + _SLEN.size > len(blob):
                raise ValueError("truncated string length")
            slen = _SLEN.unpack_from(blob, i)[0]
            i += _SLEN.size
            if slen > 0:
                if i + slen > len(blob):
                    raise ValueError("truncated string bytes")
                sbytes = blob[i:i + slen]
                i += slen
        out.append(ArgRaw(off, size, flags, raw, slen, sbytes))
    return out


@dataclass(frozen=True)
class Rec:
    kind: int
    seq: int
    ts: int
    a: int
    b: int
    c: int
    d: int
    extra: bytes


def write_thread(path, tid: int, recs: list[Rec]) -> None:
    out = bytearray(_THREAD_HEAD.pack(MAGIC_THREAD, tid))
    for r in recs:
        out += _REC.pack(r.kind, r.seq, r.ts, r.a, r.b, r.c, r.d,
                         len(r.extra))
        out += r.extra
    with open(path, "wb") as fh:
        fh.write(out)


def read_thread(path) -> tuple[int, list[Rec]]:
    data = open(path, "rb").read()
    if len(data) < _THREAD_HEAD.size:
        raise ValueError(f"{path}: thread file shorter than a header")
    magic, tid = _THREAD_HEAD.unpack_from(data, 0)
    if magic != MAGIC_THREAD:
        raise ValueError(f"{path}: not a thread spool")
    out = []
    i = _THREAD_HEAD.size
    while i < len(data):
        if i + _REC.size > len(data):
            raise ValueError(f"{path}: truncated record header")
        kind, seq, ts, a, b, c, d, n = _REC.unpack_from(data, i)
        i += _REC.size
        if i + n > len(data):
            raise ValueError(f"{path}: truncated record extra")
        out.append(Rec(kind, seq, ts, a, b, c, d, data[i:i + n]))
        i += n
    return tid, out
