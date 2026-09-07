"""What the licence's environment check may call a change.

A `refocus` re-run happens under whatever `CARGO_TARGET_DIR` the caller
gives it, and E4' gives it a fresh one on purpose -- the kept store is never
written, so the re-run builds somewhere else. Cargo then hands the test
binary four variables that embed the target root (`CARGO_TARGET_DIR`,
`CARGO_BIN_EXE_*`, `LD_LIBRARY_PATH`, `RUSTDOCFLAGS`), so the recorded
environments of the two runs differ on all four and the env clause fired on
every pair Task 5's dry run measured.

A clause that cannot not fire is not a finding -- the same rule R1 applied
to libtest's thread, one check along. Ruling (controller, 2026-09-07): a
re-run from another target directory is a normal use of the tool, and the
env clause must not read the target root's RELOCATION as a change the world
made. It must not blanket-exclude those keys either: a real
`LD_LIBRARY_PATH` change still fires, and the tests below are that
distinction and nothing else.
"""
from functools import partial

from tests.refocus_rust_fixtures import ORIG, PAIR, _drive, _read_meta, original

OLD_ROOT = "/build/target-a"
NEW_ROOT = "/build/target-b"

#: The four cargo hands a test binary that embed the target root, in the
#: three shapes they come in: a bare root, a single path under it, a
#: colon list whose first entry is under it, and a flag string carrying one.
def cargo_env(root, ld_extra="", root_as=None):
    """`root_as` spells CARGO_TARGET_DIR differently from the root the
    derived paths are built on -- the trailing-separator case, which is a
    difference in how one directory is written and not in which one it is.
    Cargo derives the paths itself, so they carry no double separator."""
    return {"PATH": "/usr/bin",
            "CARGO_TARGET_DIR": root if root_as is None else root_as,
            "CARGO_BIN_EXE_demo": f"{root}/debug/demo",
            "LD_LIBRARY_PATH": f"{root}/debug/deps:/usr/lib" + ld_extra,
            "RUSTDOCFLAGS": f"-L {root}/debug/deps"}


def _pair(tmp_path, monkeypatch, was, now):
    """The whole command over a pair recorded under two environments."""
    return _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)], env=was,
                  build=partial(original, env=now))


RELOCATED_4 = ("4 variable(s) differ only by the target directory: "
               "CARGO_BIN_EXE_demo, CARGO_TARGET_DIR, LD_LIBRARY_PATH, "
               "RUSTDOCFLAGS; treated as unchanged")


def test_a_relocated_target_directory_is_not_a_change_the_world_made(
        tmp_path, monkeypatch, capsys):
    """All four keys differ, all four differ only by the root. The licence
    is granted and the line NAMES the four rather than hiding them behind a
    count that quietly shrank."""
    _pair(tmp_path, monkeypatch, cargo_env(OLD_ROOT), cargo_env(NEW_ROOT))
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert (f"env: unchanged (5 variables compared; not compared: OLDPWD, "
            f"PWD, SENSORIUM_DIR, SHLVL, _)  {RELOCATED_4}") in out
    assert "licence: WITHHELD" not in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"
    assert any(f"; {RELOCATED_4}" in f
               for f in _read_meta(PAIR, "refocus_licence_verified"))


def test_a_trailing_slash_on_the_recorded_root_is_not_a_change_either(
        tmp_path, monkeypatch, capsys):
    """One side recorded the root with a trailing separator. Same directory,
    said two ways -- and a check that reported it would be reporting a
    string, not a world."""
    _pair(tmp_path, monkeypatch,
          cargo_env(OLD_ROOT, root_as=OLD_ROOT + "/"), cargo_env(NEW_ROOT))
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"


def test_a_real_library_path_change_still_withholds_the_licence(
        tmp_path, monkeypatch, capsys):
    """The discriminating control. `LD_LIBRARY_PATH` differs by the root AND
    carries an entry the original did not: the root part is explained, the
    extra entry is not, and an extra directory on the loader's path is
    exactly the kind of thing that changes what a program does."""
    _pair(tmp_path, monkeypatch, cargo_env(OLD_ROOT),
          cargo_env(NEW_ROOT, ld_extra=":/opt/lib"))
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "LD_LIBRARY_PATH   (names only)  3 variable(s) differ only by "
            "the target directory: CARGO_BIN_EXE_demo, CARGO_TARGET_DIR, "
            "RUSTDOCFLAGS; treated as unchanged") in out
    assert "licence: WITHHELD" in out
    assert ("1 environment variable(s) differ between the two runs "
            "(LD_LIBRARY_PATH); a program that reads them got different "
            "input") in _read_meta(PAIR, "refocus_licence_reasons")


def test_without_a_recorded_target_root_nothing_is_normalised(
        tmp_path, monkeypatch, capsys):
    """The fence. A trace with no `CARGO_TARGET_DIR` -- every Python trace,
    by construction -- normalises nothing, so a differing variable is a
    difference and the two lines are the strings they always were."""
    _pair(tmp_path, monkeypatch, {"PATH": "/usr/bin", "TZ": "UTC"},
          {"PATH": "/usr/bin", "TZ": "CET"})
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "TZ   (names only)\n") in out
    assert "target directory" not in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_path_that_merely_starts_like_the_root_is_still_a_change(
        tmp_path, monkeypatch, capsys):
    """`/build/target-abc` is not `/build/target-a` relocated: the root is
    substituted where it names a path, not wherever its characters appear.
    Getting this wrong grants a licence over a directory that really did
    move."""
    was = {**cargo_env(OLD_ROOT), "LD_LIBRARY_PATH": "/build/target-abc/lib"}
    now = {**cargo_env(NEW_ROOT), "LD_LIBRARY_PATH": "/build/target-bbc/lib"}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "LD_LIBRARY_PATH") in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
