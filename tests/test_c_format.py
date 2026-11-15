"""The C spool layout round-trips without a compiler.

`sensorium.c.format` is the contract the runtime writes. A plan comes
back sorted by address, a string argument keeps its bytes, and a signal
record keeps the signo and the faulting PC.
"""
from sensorium.c.format import (
    FLAG_CSTR, FLAG_TRUNC, KIND_ENTER, KIND_SIGNAL, NO_SLOT, RET_INT,
    RET_MEM, RET_VOID, ArgRaw, FuncPlan, ParamPlan, Rec, pack_args,
    read_plan, read_thread, unpack_args, write_plan, write_thread,
)


def test_plan_roundtrip_sorts_by_address(tmp_path):
    """Functions are stored by address, whatever order they were handed over."""
    path = tmp_path / "hello.scplan"
    write_plan(path, [
        FuncPlan(0x2000, RET_INT, 1, 4, (
            ParamPlan(-16, 4, 0),
            ParamPlan(NO_SLOT, 0, FLAG_TRUNC),
        )),
        FuncPlan(0x1000, RET_VOID, 0, 0, ()),
        FuncPlan(0x3000, RET_MEM, 0, 24, (
            ParamPlan(-48, 8, FLAG_CSTR),
        )),
    ])
    got = read_plan(path)
    assert [f.addr for f in got] == [0x1000, 0x2000, 0x3000], got
    assert got[0] == FuncPlan(0x1000, RET_VOID, 0, 0, ())
    assert got[1].params[1].off == NO_SLOT
    assert got[1].params[1].flags == FLAG_TRUNC
    assert got[2].ret_class == RET_MEM and got[2].ret_size == 24
    assert got[2].params[0].flags == FLAG_CSTR
    assert path.read_bytes()[:4] == b"SCPL"


def test_plan_rejects_a_bad_header(tmp_path):
    path = tmp_path / "bad.scplan"
    path.write_bytes(b"NOPE" + b"\x00" * 16)
    try:
        read_plan(path)
    except ValueError as e:
        assert "not a version-1 plan" in str(e), e
    else:
        raise AssertionError("a bad magic was accepted")


def test_string_argument_roundtrip():
    """A NUL-terminated copy keeps its length. NULL and a failed read do too."""
    blob = pack_args([
        ArgRaw(-24, 8, FLAG_CSTR, b"\x10\x00\x00\x00\x00\x00\x00\x00",
               5, b"brice"),
        ArgRaw(-16, 8, FLAG_CSTR, b"\x00" * 8, -2, None),
        ArgRaw(-8, 8, FLAG_CSTR, b"\x00" * 8, None, None),
        ArgRaw(0, 8, FLAG_CSTR, b"\x00" * 8, 0, b""),
    ])
    got = unpack_args(blob)
    assert got[0].sbytes == b"brice" and got[0].slen == 5, got[0]
    assert got[1].slen == -2 and got[1].sbytes is None, got[1]
    # `None` is how a caller spells "the read faulted"; the wire stores -1.
    assert got[2].slen == -1 and got[2].sbytes is None, got[2]
    assert got[3].slen == 0 and got[3].sbytes is None, got[3]


def test_pack_args_rejects_a_length_mismatch():
    try:
        pack_args([ArgRaw(0, 4, 0, b"\x00\x00", None, None)])
    except ValueError as e:
        assert "raw length" in str(e), e
    else:
        raise AssertionError("a short raw buffer was packed")
    try:
        pack_args([ArgRaw(0, 0, FLAG_CSTR, b"", 3, b"ab")])
    except ValueError as e:
        assert "string length" in str(e), e
    else:
        raise AssertionError("a short string was packed")


def test_thread_roundtrip_carries_a_string_arg_and_a_signal(tmp_path):
    """Enter's extra is the argument blob. The signal record keeps signo,
    the fault address, the PC and si_code, plus the stack bytes."""
    extra = pack_args([
        ArgRaw(-24, 8, FLAG_CSTR, b"\x10\x00\x00\x00\x00\x00\x00\x00",
               5, b"brice"),
    ])
    stack = b"\x11" * 16
    path = tmp_path / "t1.bin"
    write_thread(path, 1, [
        Rec(KIND_ENTER, 1, 100, 0x401000, 0x401100, 0x7FFF0000, 0, extra),
        Rec(KIND_SIGNAL, 2, 200, 11, 0, 0x401234, 1, stack),
    ])
    tid, recs = read_thread(path)
    assert tid == 1
    assert len(recs) == 2, recs
    assert recs[0].kind == KIND_ENTER
    assert recs[0].a == 0x401000 and recs[0].seq == 1
    args = unpack_args(recs[0].extra)
    assert args[0].sbytes == b"brice" and args[0].slen == 5, args
    assert recs[1].kind == KIND_SIGNAL
    assert (recs[1].a, recs[1].b, recs[1].c, recs[1].d) == (11, 0, 0x401234, 1)
    assert recs[1].extra == stack


def test_thread_rejects_a_bad_magic(tmp_path):
    path = tmp_path / "nope.bin"
    path.write_bytes(b"XXXX" + b"\x00" * 8)
    try:
        read_thread(path)
    except ValueError as e:
        assert "not a thread spool" in str(e), e
    else:
        raise AssertionError("a bad thread magic was accepted")
