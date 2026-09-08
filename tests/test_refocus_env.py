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


# -- what the review found the first round left open -----------------------

def test_an_entry_the_rerun_LOST_is_still_a_change(
        tmp_path, monkeypatch, capsys):
    """The mirror of the control above, and the half the entry-count check
    had no fence on: `LD_LIBRARY_PATH` here DROPS a directory the original
    had. A loader path that lost an entry is as much a change as one that
    gained it, and a count check enforced in one direction only is a check
    that reads whichever way the last edit left it."""
    _pair(tmp_path, monkeypatch, cargo_env(OLD_ROOT, ld_extra=":/opt/lib"),
          cargo_env(NEW_ROOT))
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "LD_LIBRARY_PATH   (names only)  3 variable(s) differ only by "
            "the target directory: CARGO_BIN_EXE_demo, CARGO_TARGET_DIR, "
            "RUSTDOCFLAGS; treated as unchanged") in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_relative_root_matches_only_at_a_path_segment_start(
        tmp_path, monkeypatch, capsys):
    """`CARGO_TARGET_DIR=target-a` is a directory named `target-a` under the
    workspace, so the root is anchored on the left as well as the right:
    `mytarget-a` ENDS with it and is a different directory. The right
    boundary was anchored from the start; the left one was anchored only by
    the accident that an absolute root begins with a separator, and a
    relative root has no such accident."""
    was = {"PATH": "/usr/bin", "CARGO_TARGET_DIR": "target-a",
           "LD_LIBRARY_PATH": "/ws/mytarget-a/lib"}
    now = {"PATH": "/usr/bin", "CARGO_TARGET_DIR": "target-b",
           "LD_LIBRARY_PATH": "/ws/mytarget-b/lib"}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "LD_LIBRARY_PATH   (names only)  1 variable(s) differ only by "
            "the target directory: CARGO_TARGET_DIR; treated as unchanged"
            ) in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_relative_root_still_relocates_where_it_does_name_the_path(
        tmp_path, monkeypatch, capsys):
    """...and the anchor is an anchor, not a refusal: the same relative root
    under a real path segment relocates exactly as an absolute one does."""
    was = {"PATH": "/usr/bin", "CARGO_TARGET_DIR": "target-a",
           "LD_LIBRARY_PATH": "/ws/target-a/lib:/usr/lib"}
    now = {"PATH": "/usr/bin", "CARGO_TARGET_DIR": "target-b",
           "LD_LIBRARY_PATH": "/ws/target-b/lib:/usr/lib"}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"


def test_a_withheld_pair_keeps_the_relocated_names_too(
        tmp_path, monkeypatch, capsys):
    """Both channels or neither, in the branch that was neither. The
    terminal named the three keys the check explained; before this the
    trace kept only the accusation, so `info` replayed a withheld licence
    whose screen had said more than the record does. A reader coming back
    to the trace must be able to see that three of the four differences
    were the tool's own doing."""
    _pair(tmp_path, monkeypatch, cargo_env(OLD_ROOT),
          cargo_env(NEW_ROOT, ld_extra=":/opt/lib"))
    capsys.readouterr()
    relocated = ("3 variable(s) differ only by the target directory: "
                 "CARGO_BIN_EXE_demo, CARGO_TARGET_DIR, RUSTDOCFLAGS; "
                 "treated as unchanged")
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
    assert relocated in _read_meta(PAIR, "refocus_licence_verified")
    from sensorium import cli
    assert cli.main(["info", PAIR]) == 0
    replayed = capsys.readouterr().out
    assert f"  licence verified: {relocated}" in replayed
    assert "licence withheld: 1 environment variable(s) differ" in replayed


def test_a_withheld_pair_with_no_relocation_records_nothing_extra(
        tmp_path, monkeypatch, capsys):
    """The fence on the fix above: a pair that relocated nothing keeps the
    empty verified list it always kept, so no trace gains a `licence
    verified:` line it did not earn."""
    _pair(tmp_path, monkeypatch, {"PATH": "/usr/bin", "TZ": "UTC"},
          {"PATH": "/usr/bin", "TZ": "CET"})
    capsys.readouterr()
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
    assert _read_meta(PAIR, "refocus_licence_verified") == []


# -- R1: the recorder's own fragment ---------------------------------------
#: The two rt hashes E4' really recorded (that record's section 4): the driver
#: embeds a digest of its own binary and the `sensorium-rt` sources in the
#: path, so the hash moves with every driver build and the fragment differs
#: between an original and a re-run built from a different commit. Fixtures
#: use the measured pair rather than invented hex, because "16 hex characters"
#: is the regex's claim and these are the strings it has to hold for.
RT_WAS = "d9ce385a08c6646b"
RT_NOW = "83d9294b8135c157"


def fragment(root, rt_hash, profile="unwind"):
    """`RUSTDOCFLAGS` as `cargo sensorium` writes it: two tokens naming ONE
    directory under the target root."""
    d = f"{root}/sensorium/rt/{rt_hash}/{profile}"
    return f"--extern sensorium_rt={d}/libsensorium_rt.rlib -L dependency={d}"


def test_the_recorders_own_fragment_is_stripped_before_the_compare(
        tmp_path, monkeypatch, capsys):
    """(a) The E4' shape exactly: the target root moved AND the rt hash moved,
    because the re-run is built by a different driver. Stripped from both
    sides, `RUSTDOCFLAGS` has nothing left to differ by -- so it is named by
    the strip clause and by no other list, and the licence holds."""
    from sensorium.query.refocus_world import _env_diff

    was = {**cargo_env(OLD_ROOT), "RUSTDOCFLAGS": fragment(OLD_ROOT, RT_WAS)}
    now = {**cargo_env(NEW_ROOT), "RUSTDOCFLAGS": fragment(NEW_ROOT, RT_NOW)}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert ("env: unchanged (5 variables compared; not compared: OLDPWD, "
            "PWD, SENSORIUM_DIR, SHLVL, _)  3 variable(s) differ only by the "
            "target directory: CARGO_BIN_EXE_demo, CARGO_TARGET_DIR, "
            "LD_LIBRARY_PATH; treated as unchanged; the recorder's own "
            "fragment stripped before comparing: RUSTDOCFLAGS") in out
    assert "licence: WITHHELD" not in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"

    # The partition itself, not only its rendering: RUSTDOCFLAGS is on
    # neither the changed nor the relocated list.
    changed, relocated, stripped = _env_diff(was, now)
    assert changed == []
    assert relocated == ["CARGO_BIN_EXE_demo", "CARGO_TARGET_DIR",
                         "LD_LIBRARY_PATH"]
    assert stripped == ["RUSTDOCFLAGS"]


def test_a_world_flag_beside_the_fragment_still_withholds(
        tmp_path, monkeypatch, capsys):
    """(b) The discriminating control. `--cfg docsrs` is the WORLD's flag and
    only the original carries it; strip ours and the remainder still differs,
    so the licence is withheld naming `RUSTDOCFLAGS`. A strip that swallowed
    the whole variable would grant a licence over a real difference."""
    was = {**cargo_env(OLD_ROOT),
           "RUSTDOCFLAGS": "--cfg docsrs " + fragment(OLD_ROOT, RT_WAS)}
    now = {**cargo_env(NEW_ROOT), "RUSTDOCFLAGS": fragment(NEW_ROOT, RT_NOW)}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "RUSTDOCFLAGS   (names only)") in out
    assert "licence: WITHHELD" in out
    # Stripped AND changed: the clause says what was removed even where the
    # remainder still accuses.
    assert ("the recorder's own fragment stripped before comparing: "
            "RUSTDOCFLAGS") in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_two_tokens_naming_different_directories_are_not_our_fragment(
        tmp_path, monkeypatch, capsys):
    """(c) The backreference IS the rule. `--extern` and `-L dependency=`
    that name two different rt directories are not the shape this recorder
    writes, so nothing is stripped and the world's compare sees the whole
    value -- which differs by more than the root and withholds."""
    def mixed(root, first, second):
        a = f"{root}/sensorium/rt/{first}/unwind"
        b = f"{root}/sensorium/rt/{second}/unwind"
        return (f"--extern sensorium_rt={a}/libsensorium_rt.rlib "
                f"-L dependency={b}")

    was = {**cargo_env(OLD_ROOT),
           "RUSTDOCFLAGS": mixed(OLD_ROOT, RT_WAS, RT_NOW)}
    now = {**cargo_env(NEW_ROOT),
           "RUSTDOCFLAGS": mixed(NEW_ROOT, RT_NOW, RT_WAS)}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "RUSTDOCFLAGS   (names only)") in out
    assert "the recorder's own fragment stripped" not in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_pair_with_no_fragment_reads_exactly_as_it_did(
        tmp_path, monkeypatch, capsys):
    """(d) The legacy fence. A Python pair carries no fragment, so the strip
    removes nothing, no clause is appended, and both channels are the strings
    they were before this rule existed -- the line down to its newline and the
    verified fact as a whole element, not a substring of one."""
    env = {"PATH": "/usr/bin", "TZ": "UTC"}
    _pair(tmp_path, monkeypatch, env, dict(env))
    out = capsys.readouterr().out
    assert ("env: unchanged (2 variables compared; not compared: OLDPWD, "
            "PWD, SENSORIUM_DIR, SHLVL, _)\n") in out
    assert ("2 environment variable(s) compared and unchanged in the "
            "environment the rerun executed under; not compared: OLDPWD, "
            "PWD, SENSORIUM_DIR, SHLVL, _"
            ) in _read_meta(PAIR, "refocus_licence_verified")


def test_a_withheld_pair_keeps_the_strip_note_on_its_own(
        tmp_path, monkeypatch, capsys):
    """The strip is a finding of its own, and it survives a withheld licence
    with NOTHING relocated beside it: a re-run into the SAME target
    directory under a rebuilt driver, with one real difference next to it.
    Recognising only the relocation phrase would drop this note, and `info`
    would replay a licence whose screen had said more than the record
    does."""
    from sensorium import cli

    was = {"PATH": "/usr/bin", "TZ": "UTC", "CARGO_TARGET_DIR": OLD_ROOT,
           "RUSTDOCFLAGS": fragment(OLD_ROOT, RT_WAS)}
    now = {**was, "TZ": "CET", "RUSTDOCFLAGS": fragment(OLD_ROOT, RT_NOW)}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    note = ("the recorder's own fragment stripped before comparing: "
            "RUSTDOCFLAGS")
    assert "target directory" not in out          # nothing relocated
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
    assert note in _read_meta(PAIR, "refocus_licence_verified")
    assert cli.main(["info", PAIR]) == 0
    assert f"  licence verified: {note}" in capsys.readouterr().out


def test_what_the_strip_removes_and_what_it_counts():
    """(e) The unit. Every match removed, the space that surrounded it
    collapsed with it, the ends trimmed, and the COUNT returned -- the count
    is what puts the key on the strip list, so a removal that did not report
    itself would be a silent exclusion."""
    from sensorium.query.refocus_env import strip_recorder_fragment

    frag = fragment(OLD_ROOT, RT_WAS)
    assert strip_recorder_fragment("") == ("", 0)
    assert strip_recorder_fragment(frag) == ("", 1)
    assert strip_recorder_fragment("--cfg docsrs " + frag) == (
        "--cfg docsrs", 1)
    assert strip_recorder_fragment(f"{frag} {fragment(NEW_ROOT, RT_NOW)}") == (
        "", 2)
