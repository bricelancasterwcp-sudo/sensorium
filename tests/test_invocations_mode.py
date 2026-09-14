"""The store root is 0700 whichever hand creates it.

`redaction.key` and `invocations.jsonl` are siblings of `traces/` and both
of them are secrets: one makes every digest in the store guessable, the
other names every sensorium invocation and its argv. `paths.traces_dir`
creates the root 0700 and `redact.Key.load_or_create` creates it 0700, and
`invocations.record` is the third hand that can get there first -- it
`mkdir`s the log's parent on a store that may not exist yet.

TWO TESTS, AND THEY ARE NOT THE SAME TEST. The end-to-end one states the
fact a user can check (`sensorium runs` on a fresh `SENSORIUM_DIR` leaves a
private directory) but it cannot fail on this module's mode alone: the
command reaches `paths.traces_dir()` first, which already creates the root
0700, so the log's own `mkdir` finds it there. The direct one is the
discriminating check -- it calls `record` on a root nothing else has made,
which is the state a command that never touches `traces_dir()` leaves, and
it fails the moment the mode is dropped.

An EXISTING directory is never chmod'ed, here or anywhere else: a user's
own permissions on their own store are theirs (`paths.traces_dir`).
"""
import os
import stat
from pathlib import Path

from sensorium import invocations
from tests.helpers import run_cli


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def test_the_log_creates_the_store_root_private(tmp_path, monkeypatch):
    """`record` reaching a store nobody has made yet. The log is appended
    0600 and the directory it goes in is created 0700 -- the two halves of
    one rule, and this is the half no other test covers."""
    root = Path(tmp_path) / "fresh"
    monkeypatch.setenv("SENSORIUM_DIR", str(root))
    invocations.record(["runs"], 1, None)
    assert _mode(root) == 0o700
    assert _mode(root / "invocations.jsonl") == 0o600


def test_a_command_against_a_store_that_does_not_exist_leaves_it_private(
        tmp_path):
    """End to end, the fact a user can check for themselves."""
    root = Path(tmp_path) / "sdir"
    r = run_cli(["runs"], cwd=tmp_path, sensorium_dir=root)
    assert r.returncode == 1, r.stdout + r.stderr
    assert _mode(root) == 0o700
    assert _mode(root / "invocations.jsonl") == 0o600


def test_a_store_root_that_already_exists_keeps_its_own_mode(tmp_path,
                                                             monkeypatch):
    """The fence. `mkdir(exist_ok=True)` ignores the mode of a directory
    that is already there, which is the intent: a user who widened their
    own store did so on purpose, and a logger is not the command that
    argues with them."""
    root = Path(tmp_path) / "loose"
    root.mkdir(mode=0o755)
    monkeypatch.setenv("SENSORIUM_DIR", str(root))
    invocations.record(["runs"], 1, None)
    assert _mode(root) == 0o755
