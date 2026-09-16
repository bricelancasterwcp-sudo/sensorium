"""`redact_key.sweep_stale` -- the stale key tmp sweep (A's R15 hazard,
CARRIED-DEBT "PR C", spec C13).

`Key.load_or_create` writes the new key's 32 bytes into a private
`redaction.key.<pid>.tmp` and unlinks it in a `finally` on every path back
out (R15). A process KILLED between that write finishing and the `finally`
running is the one path a `finally` cannot cover, and it leaves the tmp
behind -- a 32-byte secret half nobody will ever finish writing. Nothing
swept it before this module; `sweep_stale` is that sweep, and a later task
wires it into `sensorium redact`.
"""
import os
import stat

from sensorium import redact_key


def _dead_pid() -> int:
    """A pid this box provably does not have: walk down from `2**22 - 1`
    until `os.kill(pid, 0)` says so. `PermissionError` means the pid is
    real but not ours to signal, so it is skipped, not accepted."""
    pid = 2**22 - 1
    while pid > 1:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except OSError:
            pass
        pid -= 1
    raise RuntimeError("no dead pid found below 2**22")


def test_a_dead_pids_tmp_is_unlinked_and_returned(tmp_path):
    pid = _dead_pid()
    tmp = tmp_path / f"{redact_key.KEY_FILE}.{pid}.tmp"
    tmp.write_bytes(b"\x00" * redact_key.KEY_BYTES)

    assert redact_key.sweep_stale(tmp_path) == [tmp]
    assert not tmp.exists()


def test_a_live_pids_tmp_is_kept(tmp_path):
    tmp = tmp_path / f"{redact_key.KEY_FILE}.{os.getpid()}.tmp"
    tmp.write_bytes(b"\x00" * redact_key.KEY_BYTES)

    assert redact_key.sweep_stale(tmp_path) == []
    assert tmp.exists()


def test_the_key_file_itself_is_never_touched(tmp_path):
    """The glob is `redaction.key.*.tmp`: `redaction.key` on its own has no
    `.tmp` suffix and cannot match it. A dead pid's tmp sits beside it so
    the sweep does real work in this test, not none at all."""
    key_path = tmp_path / redact_key.KEY_FILE
    material = os.urandom(redact_key.KEY_BYTES)
    key_path.write_bytes(material)
    tmp = tmp_path / f"{redact_key.KEY_FILE}.{_dead_pid()}.tmp"
    tmp.write_bytes(b"\x00" * redact_key.KEY_BYTES)

    swept = redact_key.sweep_stale(tmp_path)

    assert swept == [tmp]
    assert key_path.read_bytes() == material


def test_a_name_whose_pid_is_not_an_int_is_left(tmp_path):
    tmp = tmp_path / f"{redact_key.KEY_FILE}.abc.tmp"
    tmp.write_bytes(b"\x00" * redact_key.KEY_BYTES)

    assert redact_key.sweep_stale(tmp_path) == []
    assert tmp.exists()


def test_a_missing_root_returns_nothing(tmp_path):
    assert redact_key.sweep_stale(tmp_path / "does-not-exist") == []


def test_a_pid_outside_the_c_int_range_never_raises_and_is_kept(tmp_path):
    """`os.kill` raises `OverflowError` -- not an `OSError` -- for a pid
    past the platform's signed-int range (`2**31` on this interpreter): a
    `.tmp` name is trusted only as digits, and digits can spell a number
    no real pid ever is. `_pid_alive` must read that as "cannot check,
    call it alive," not let it propagate out of `sweep_stale`."""
    tmp = tmp_path / f"{redact_key.KEY_FILE}.2147483648.tmp"
    tmp.write_bytes(b"\x00" * redact_key.KEY_BYTES)

    assert redact_key.sweep_stale(tmp_path) == []
    assert tmp.exists()


def test_a_negative_or_zero_middle_is_left(tmp_path):
    """`os.kill` treats a negative number as a process GROUP, not the pid
    the name encodes, and pid 0 means the caller's own group -- neither is
    the pid this name claims, so both are refused like a non-int middle,
    before `_pid_alive` is ever asked."""
    negative = tmp_path / f"{redact_key.KEY_FILE}.-5.tmp"
    zero = tmp_path / f"{redact_key.KEY_FILE}.0.tmp"
    negative.write_bytes(b"\x00" * redact_key.KEY_BYTES)
    zero.write_bytes(b"\x00" * redact_key.KEY_BYTES)

    assert redact_key.sweep_stale(tmp_path) == []
    assert negative.exists()
    assert zero.exists()


def test_never_raises_on_an_unlinkable_file(tmp_path):
    """0500 keeps read and traversal but drops write on the directory
    itself, which is what unlink needs: the file is still there afterward,
    and the sweep neither raises nor claims it."""
    tmp = tmp_path / f"{redact_key.KEY_FILE}.{_dead_pid()}.tmp"
    tmp.write_bytes(b"\x00" * redact_key.KEY_BYTES)
    original_mode = stat.S_IMODE(tmp_path.stat().st_mode)
    os.chmod(tmp_path, 0o500)
    try:
        swept = redact_key.sweep_stale(tmp_path)
    finally:
        os.chmod(tmp_path, original_mode)

    assert set(swept) <= {tmp}
    if not swept:
        assert tmp.exists()
