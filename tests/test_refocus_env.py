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

import pytest

from sensorium.query.refocus_env import SESSION_ORDER
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
    changed, relocated, stripped, session = _env_diff(was, now)
    assert changed == []
    assert relocated == ["CARGO_BIN_EXE_demo", "CARGO_TARGET_DIR",
                         "LD_LIBRARY_PATH"]
    assert stripped == ["RUSTDOCFLAGS"] and session == []


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
    # No match, no edit: the trim belongs to the removal and to nothing
    # else, or the compare quietly widens on every key in the environment.
    assert strip_recorder_fragment("  --cfg a  ") == ("  --cfg a  ", 0)


# -- R4 / A-section-3: session set 1 ---------------------------------------
def _session_pair(tmp_path, monkeypatch, name, was_value, now_value):
    """One variable differing between the two runs, everything else equal."""
    base = {"PATH": "/usr/bin", "TZ": "UTC"}
    return _pair(tmp_path, monkeypatch, {**base, name: was_value},
                 {**base, name: now_value})


def test_a_session_variable_that_differs_is_named_and_never_withholds(
        tmp_path, monkeypatch, capsys):
    """(f) The whole of A-section-3's problem, on this box: a re-run launched
    from another agent session differs on `CLAUDE_CODE_SESSION_ID` and on
    nothing else. Named, counted, and the licence still granted -- the line
    says which set it is unchanged OUTSIDE of, so a reader is never told
    'unchanged' about an environment that was not."""
    _session_pair(tmp_path, monkeypatch, "CLAUDE_CODE_SESSION_ID", "a1", "b2")
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert ("env: unchanged outside session set 1 (3 variables compared; not "
            "compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; 1 session "
            "variable(s) differ: CLAUDE_CODE_SESSION_ID)\n") in out
    assert "licence: WITHHELD" not in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"
    assert ("3 environment variable(s) compared and unchanged outside session "
            "set 1 in the environment the rerun executed under; not compared: "
            "OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; 1 session variable(s) "
            "differ: CLAUDE_CODE_SESSION_ID"
            ) in _read_meta(PAIR, "refocus_licence_verified")


def test_a_key_outside_the_session_set_withholds_exactly_as_before(
        tmp_path, monkeypatch, capsys):
    """(g) The default is what it always was. `TZ` is on no exemption list
    anyone would write, a program reads it, and the line and the caveat are
    the strings they were before session set 1 existed."""
    _pair(tmp_path, monkeypatch, {"PATH": "/usr/bin", "TZ": "UTC"},
          {"PATH": "/usr/bin", "TZ": "CET"})
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "TZ   (names only)\n") in out
    assert "session set" not in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_session_key_beside_a_real_one_withholds_and_names_both(
        tmp_path, monkeypatch, capsys):
    """(h) The two halves do not hide each other. `TZ` withholds, and the
    session key is still counted and named on the same line -- a reader who
    saw only the accusation would not know the re-run also came from another
    shell, and a reader who saw only the shell would not know why the
    licence was refused."""
    _pair(tmp_path, monkeypatch,
          {"PATH": "/usr/bin", "TZ": "UTC", "CLAUDE_CODE_SESSION_ID": "a1"},
          {"PATH": "/usr/bin", "TZ": "CET", "CLAUDE_CODE_SESSION_ID": "b2"})
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "TZ   (names only); 1 session variable(s) differ: "
            "CLAUDE_CODE_SESSION_ID\n") in out
    assert "licence: WITHHELD" in out
    assert ("1 environment variable(s) differ between the two runs (TZ); a "
            "program that reads them got different input"
            ) in _read_meta(PAIR, "refocus_licence_reasons")


def test_the_withheld_pairs_own_record_carries_the_session_clause_too(
        tmp_path, monkeypatch, capsys):
    """(h2) `info` replays exactly what the screen said, on a WITHHELD pair.

    The screen of (h) names both halves; the trace kept only the accusation,
    so a reader who came back to it through `info` was told `TZ` differed
    and never told the re-run had come from another agent session -- the
    same asymmetry the relocation and strip clauses were given their own
    fact to close, one rule along. The session clause now travels with them
    (`is_env_rule_note` recognises all three), and the fact is the CLAUSES
    alone: a withheld licence still vouches for nothing.
    """
    _pair(tmp_path, monkeypatch,
          {"PATH": "/usr/bin", "TZ": "UTC", "CLAUDE_CODE_SESSION_ID": "a1"},
          {"PATH": "/usr/bin", "TZ": "CET", "CLAUDE_CODE_SESSION_ID": "b2"})
    from sensorium import cli

    capsys.readouterr()
    said = "1 session variable(s) differ: CLAUDE_CODE_SESSION_ID"
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
    assert _read_meta(PAIR, "refocus_licence_verified") == [said]
    assert cli.main(["info", PAIR]) == 0
    replayed = capsys.readouterr().out
    assert f"  licence verified: {said}\n" in replayed
    assert "licence withheld: 1 environment variable(s) differ" in replayed


def test_a_withheld_pair_that_relocated_and_changed_sessions_names_both(
        tmp_path, monkeypatch, capsys):
    """(h3) Two clauses in one fact, joined the way the line joins them.

    The order is the line's order -- session first, then the rules that
    explained keys away -- because two channels that carry the same names in
    two orders are two sentences to keep in step.
    """
    _pair(tmp_path, monkeypatch,
          dict(cargo_env(OLD_ROOT), TZ="UTC", CLAUDE_CODE_SESSION_ID="a1"),
          dict(cargo_env(NEW_ROOT), TZ="CET", CLAUDE_CODE_SESSION_ID="b2"))
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
    assert _read_meta(PAIR, "refocus_licence_verified") == [
        "1 session variable(s) differ: CLAUDE_CODE_SESSION_ID; "
        + RELOCATED_4]


@pytest.mark.parametrize("session_name", [*SESSION_ORDER, "CLAUDE_CODE_X"])
def test_every_member_of_session_set_1_is_named_and_never_withholds(
        tmp_path, monkeypatch, capsys, session_name):
    """(i) Each of the fourteen exact names, and the prefix, driven through
    the whole command. The set is a POSITIVE, versioned list precisely so
    that every member of it can be enumerated by a test and argued with by a
    reader; a negative list could be neither."""
    _session_pair(tmp_path, monkeypatch, session_name, "one", "two")
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert f"1 session variable(s) differ: {session_name}" in out
    assert "licence: WITHHELD" not in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"


@pytest.mark.parametrize("name", ["CLAUDE_CODEX", "XDG_SESSION_IDX"])
def test_a_name_that_merely_resembles_a_session_key_still_withholds(
        tmp_path, monkeypatch, capsys, name):
    """(j) The set is exact names and one prefix, not a family resemblance.
    `CLAUDE_CODEX` does not carry the `CLAUDE_CODE_` prefix and
    `XDG_SESSION_IDX` is not `XDG_SESSION_ID`; a membership test loose enough
    to admit either would exempt variables nobody put on the list."""
    _session_pair(tmp_path, monkeypatch, name, "one", "two")
    out = capsys.readouterr().out
    assert (f"env: CHANGED since the original run -- 1 variable(s) differ: "
            f"{name}   (names only)") in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_session_key_present_on_one_side_only_is_still_a_session_key(
        tmp_path, monkeypatch, capsys):
    """(k) A key that APPEARED is a difference -- as it always was -- and
    then it is partitioned like any other. A re-run launched outside tmux
    has no `TMUX` at all, which is the same fact about the launcher as a
    `TMUX` that differs, and must not read as the world changing."""
    from sensorium.query.refocus_world import _env_diff

    was = {"PATH": "/usr/bin"}
    now = {"PATH": "/usr/bin", "TMUX": "/tmp/tmux-1000/default,17,0"}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert "1 session variable(s) differ: TMUX" in out
    assert "licence: WITHHELD" not in out
    changed, relocated, stripped, session = _env_diff(was, now)
    assert changed == [] and relocated == [] and stripped == []
    assert session == ["TMUX"]


# -- fix round 1: what the review found ------------------------------------

def test_a_whitespace_only_difference_is_still_a_difference(
        tmp_path, monkeypatch, capsys):
    """The strip must not widen the compare on a key it did not touch. A
    trailing space on a value the world wrote is a difference between two
    recorded environments, and a `strip()` applied whether or not a fragment
    matched would have quietly called it unchanged -- on NEITHER channel,
    because the key never reaches the strip list."""
    _pair(tmp_path, monkeypatch, {"PATH": "/usr/bin", "TZ": "UTC "},
          {"PATH": "/usr/bin", "TZ": "UTC"})
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "TZ   (names only)\n") in out
    assert "the recorder's own fragment stripped" not in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_session_set_1_is_these_fourteen_names_in_this_order():
    """The set, written out. The parametrised test above iterates the tuple
    itself, so it would pass over any list at all; this is the one place a
    name added, removed or reordered fails a test. The order is the design's
    (amendment A-section-3) and E4''s arm C picks its injected key by it."""
    from sensorium.query import refocus_env as env

    assert env.SESSION_SET == 1
    assert env.SESSION_ORDER == (
        "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID", "TERM_SESSION_ID",
        "WINDOWID", "TMUX", "TMUX_PANE", "SSH_AGENT_PID", "SSH_AUTH_SOCK",
        "SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY", "INVOCATION_ID",
        "JOURNAL_STREAM", "SYSTEMD_EXEC_PID")
    assert env.SESSION_EXACT == frozenset(env.SESSION_ORDER)
    assert env.SESSION_PREFIXES == ("CLAUDE_CODE_",)


def test_all_four_lists_at_once_on_a_withheld_pair(
        tmp_path, monkeypatch, capsys):
    """Every rule firing on one pair, and the WHOLE line pinned. The
    accusation comes first over the changed names alone, then the session
    clause it must not be confused with, then the two explanations -- swap
    any pair of them and this fails. `LD_LIBRARY_PATH` gained a directory,
    so it is the one thing here the world really did."""
    was = {**cargo_env(OLD_ROOT), "RUSTDOCFLAGS": fragment(OLD_ROOT, RT_WAS),
           "CLAUDE_CODE_SESSION_ID": "a1"}
    now = {**cargo_env(NEW_ROOT, ld_extra=":/opt/lib"),
           "RUSTDOCFLAGS": fragment(NEW_ROOT, RT_NOW),
           "CLAUDE_CODE_SESSION_ID": "b2"}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert ("env: CHANGED since the original run -- 1 variable(s) differ: "
            "LD_LIBRARY_PATH   (names only); 1 session variable(s) differ: "
            "CLAUDE_CODE_SESSION_ID  2 variable(s) differ only by the target "
            "directory: CARGO_BIN_EXE_demo, CARGO_TARGET_DIR; treated as "
            "unchanged; the recorder's own fragment stripped before "
            "comparing: RUSTDOCFLAGS\n") in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_a_session_only_pair_still_carries_both_clauses(
        tmp_path, monkeypatch, capsys):
    """The same four rules with the world's difference taken away: the
    session count sits INSIDE the compared-count parenthesis and the two
    explanations follow it, and the licence holds. This is the shape E4''
    expects on a granted pair, printed in full."""
    was = {**cargo_env(OLD_ROOT), "RUSTDOCFLAGS": fragment(OLD_ROOT, RT_WAS),
           "CLAUDE_CODE_SESSION_ID": "a1"}
    now = {**cargo_env(NEW_ROOT), "RUSTDOCFLAGS": fragment(NEW_ROOT, RT_NOW),
           "CLAUDE_CODE_SESSION_ID": "b2"}
    _pair(tmp_path, monkeypatch, was, now)
    out = capsys.readouterr().out
    assert "env: CHANGED" not in out
    assert ("env: unchanged outside session set 1 (6 variables compared; not "
            "compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; 1 session "
            "variable(s) differ: CLAUDE_CODE_SESSION_ID)  3 variable(s) "
            "differ only by the target directory: CARGO_BIN_EXE_demo, "
            "CARGO_TARGET_DIR, LD_LIBRARY_PATH; treated as unchanged; the "
            "recorder's own fragment stripped before comparing: "
            "RUSTDOCFLAGS\n") in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"
