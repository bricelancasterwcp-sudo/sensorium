"""The E4″ additions to the E4′ reader: the session clause, the strip
clause, and the rt hash the recorder's own fragment carries.

Every line below is what `sensorium refocus` ACTUALLY printed over a pair
built to the shape E4″ measures -- an original recorded under one driver
build and a re-run under another, so the rt hashes differ and the strip
clause has something to fire on. The three hand-built cases are the ones a
pair cannot be driven into (a printed list at its 8-name cap, and a line
with no clause at all); each names the function whose format string it
copies.
"""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4p_read as rd                                   # noqa: E402
from tests.refocus_rust_fixtures import (ORIG, PAIR, _drive,       # noqa: E402
                                         libtest_original)

#: The driver's own `RUSTDOCFLAGS` fragment, as `cargo sensorium` writes it
#: (`refocus_env.RECORDER_FRAGMENT`'s shape): `--extern sensorium_rt=` and
#: the `-L dependency=` that resolves it, both naming ONE directory whose
#: 16-hex component is a digest of the driver binary and the `sensorium-rt`
#: sources -- which is why it moves with every driver build, and why E4″
#: reads an original recorded under 0.5.0 with a driver that is 0.5.2.
ORIG_RT = "d9ce385a08c66466"
RERUN_RT = "83d9294b8135c157"


def _flags(root: str, rt: str, panic: str = "unwind") -> str:
    d = f"{root}/sensorium/rt/{rt}/{panic}"
    return (f"--cfg sensorium --extern sensorium_rt={d}/libsensorium_rt.rlib "
            f"-L dependency={d}")


def _side(root: str, rt: str, **extra) -> dict:
    return dict({
        "PATH": "/usr/bin",
        "HOME": "/home/someone",
        "CARGO_TARGET_DIR": root,
        "CARGO_BIN_EXE_app": f"{root}/debug/app",
        "LD_LIBRARY_PATH": f"{root}/debug:/usr/lib",
        "RUSTDOCFLAGS": _flags(root, rt),
    }, **extra)


def _pair(tmp_path, monkeypatch, capsys, *, orig, rerun, program_threads=0):
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)],
           program=partial(libtest_original, env=orig,
                           program_threads=program_threads),
           build=partial(libtest_original, env=rerun,
                         program_threads=program_threads))
    return capsys.readouterr().out


# --------------------------------------------------- the session clause

def test_a_session_only_difference_leaves_the_env_UNCHANGED_and_names_it(
        tmp_path, monkeypatch, capsys):
    """A-§3's line, on the shape arm A expects on all 61: the launch shell
    differs on one session variable and on nothing else, so the licence
    still holds and the set is NAMED with its size."""
    out = _pair(tmp_path, monkeypatch, capsys,
                orig=_side("/build/target-a", ORIG_RT,
                           CLAUDE_CODE_SESSION_ID="one"),
                rerun=_side("/build/target-b", RERUN_RT,
                            CLAUDE_CODE_SESSION_ID="two"))
    p = rd.parse_refocus(out)
    assert p["env_status"] == "unchanged"
    assert p["env_unchanged_outside_session"] is True
    assert p["env_session_n"] == 1
    assert p["env_session_keys"] == ["CLAUDE_CODE_SESSION_ID"]
    assert p["env_session_keys_truncated"] is False
    assert p["env_changed_n"] == 0


def test_the_strip_clause_NAMES_the_key_it_stripped(
        tmp_path, monkeypatch, capsys):
    """R1's clause, `refocus_env.stripped_clause` verbatim. The two sides'
    rt hashes differ -- the one condition E4′ could not create -- so a
    strip that did not fire would leave `RUSTDOCFLAGS` in the CHANGED
    list, which is H2's STOP."""
    out = _pair(tmp_path, monkeypatch, capsys,
                orig=_side("/build/target-a", ORIG_RT),
                rerun=_side("/build/target-b", RERUN_RT))
    p = rd.parse_refocus(out)
    assert p["env_stripped_keys"] == ["RUSTDOCFLAGS"]
    assert p["env_changed_keys"] == []
    assert "RUSTDOCFLAGS" not in (p["env_changed_keys"] or [])
    assert p["env_relocated_keys"] == ["CARGO_BIN_EXE_app",
                                       "CARGO_TARGET_DIR",
                                       "LD_LIBRARY_PATH"]


def test_a_key_OUTSIDE_the_session_set_still_CHANGES_the_line(
        tmp_path, monkeypatch, capsys):
    """Arm B's shape. The session clause and the CHANGED list are two
    readings of one line and are read apart: a session key on the line must
    not be counted as a changed one, and a changed key must not hide behind
    the session count."""
    out = _pair(tmp_path, monkeypatch, capsys,
                orig=_side("/build/target-a", ORIG_RT,
                           CLAUDE_CODE_SESSION_ID="one"),
                rerun=_side("/build/target-b", RERUN_RT,
                            CLAUDE_CODE_SESSION_ID="two", E4PP_INPUT="1"))
    p = rd.parse_refocus(out)
    assert p["env_status"] == "CHANGED"
    assert p["env_unchanged_outside_session"] is False
    assert p["env_changed_keys"] == ["E4PP_INPUT"]
    assert p["env_changed_n"] == 1
    # ...and the session clause is STILL read on the CHANGED line, where it
    # sits between `(names only)` and the two-space clause join.
    assert p["env_session_n"] == 1
    assert p["env_session_keys"] == ["CLAUDE_CODE_SESSION_ID"]
    assert p["env_stripped_keys"] == ["RUSTDOCFLAGS"]


def test_arm_Cs_shape_puts_the_injected_key_on_the_session_list(
        tmp_path, monkeypatch, capsys):
    """Arm C: a key of session set 1, absent from both sides, set on the
    re-run alone. K goes up by exactly one and the licence word does not
    move."""
    out = _pair(tmp_path, monkeypatch, capsys,
                orig=_side("/build/target-a", ORIG_RT,
                           CLAUDE_CODE_SESSION_ID="one"),
                rerun=_side("/build/target-b", RERUN_RT,
                            CLAUDE_CODE_SESSION_ID="two", TMUX="/tmp/s,1,0"))
    p = rd.parse_refocus(out)
    assert p["env_status"] == "unchanged"
    assert p["env_session_n"] == 2
    assert p["env_session_keys"] == ["CLAUDE_CODE_SESSION_ID", "TMUX"]


def test_a_pair_whose_environments_MATCH_names_no_session_key(
        tmp_path, monkeypatch, capsys):
    """`[]` and `0`, not `None`: the line WAS read and it named none."""
    same = _side("/build/target-a", ORIG_RT)
    out = _pair(tmp_path, monkeypatch, capsys, orig=same, rerun=same)
    p = rd.parse_refocus(out)
    assert p["env_session_keys"] == []
    assert p["env_session_n"] == 0
    assert p["env_unchanged_outside_session"] is False
    # ...and the strip clause STILL names `RUSTDOCFLAGS`. `_env_diff` strips
    # the fragment on both sides of every key BEFORE comparing, so the key
    # is named whether or not its two values differed -- "a variable this
    # tool removed part of before comparing is a variable it checked less
    # of". Which is exactly why H2's second reading publishes the two rt
    # hashes: a strip that fired on a pair whose hashes were EQUAL is a
    # strip that pair could not have tested.
    assert p["env_stripped_keys"] == ["RUSTDOCFLAGS"]


def test_an_env_line_that_never_printed_is_None_on_every_new_field():
    """None-vs-empty, on this side too. A pair with no `env:` line has no
    lists; `[]` there would claim the line said nothing moved."""
    p = rd.parse_refocus("nothing was printed\n")
    assert p["env_stripped_keys"] is None
    assert p["env_session_keys"] is None
    assert p["env_session_n"] is None
    assert p["env_unchanged_outside_session"] is None


def test_a_printed_session_list_AT_ITS_CAP_is_read_as_bounded():
    """§1.4's kill 7. `refocus_world._capped` prints at most eight names and
    counts the rest, so on K > 8 the COUNT is authoritative and the names
    are short -- recorded as two fields with the truncation stated, never
    as a complete list."""
    names = ", ".join(f"K{i}" for i in range(1, 9)) + ", +3 more"
    line = ("env: unchanged outside session set 1 (73 variables compared; "
            f"not compared: OLDPWD, PWD, SHLVL, _; 11 session variable(s) "
            f"differ: {names})  the recorder's own fragment stripped before "
            "comparing: RUSTDOCFLAGS")
    p = rd.parse_refocus(line + "\n")
    assert p["env_session_n"] == 11
    assert p["env_session_keys"] == [f"K{i}" for i in range(1, 9)]
    assert p["env_session_keys_truncated"] is True
    assert p["env_stripped_keys"] == ["RUSTDOCFLAGS"]


def test_the_strip_clause_is_read_when_the_RELOCATION_clause_precedes_it():
    """The two clauses join with `; ` (`refocus_world._env_state`), so the
    strip names must not swallow the relocation's, nor stop at its comma."""
    line = ("env: unchanged (73 variables compared; not compared: OLDPWD, "
            "PWD, SHLVL, _)  4 variable(s) differ only by the target "
            "directory: CARGO_BIN_EXE_a, CARGO_BIN_EXE_b, CARGO_TARGET_DIR, "
            "LD_LIBRARY_PATH; treated as unchanged; the recorder's own "
            "fragment stripped before comparing: RUSTDOCFLAGS")
    p = rd.parse_refocus(line + "\n")
    assert p["env_stripped_keys"] == ["RUSTDOCFLAGS"]
    assert p["env_relocated_keys"] == ["CARGO_BIN_EXE_a", "CARGO_BIN_EXE_b",
                                       "CARGO_TARGET_DIR", "LD_LIBRARY_PATH"]
    assert p["env_session_n"] == 0


# ------------------------------------------------------------ the rt hash

def test_the_rt_hash_is_read_from_each_sides_recorded_RUSTDOCFLAGS():
    """§1.5's proof that the two builds are not the same build. Read with
    this instrument's OWN pattern, never by importing the rule under
    test."""
    got = rd.rt_hash_of(_side("/build/target-a", ORIG_RT))
    assert got["value"] == ORIG_RT
    # ONE fragment, whose directory the value names TWICE (`--extern` and
    # the `-L dependency=` that resolves it). The two counts are kept apart
    # rather than one standing in for the other.
    assert got["fragments"] == 1
    assert got["occurrences"] == 2
    assert got["reason"] is None


def test_two_sides_with_the_SAME_hash_are_a_strip_that_was_never_tested():
    """H2's second reading: a strip that fired on a pair whose two hashes
    were EQUAL could not have been tested by that pair."""
    a = rd.rt_hash_of(_side("/build/target-a", ORIG_RT))
    b = rd.rt_hash_of(_side("/build/target-b", ORIG_RT))
    assert a["value"] == b["value"]


def test_an_environment_with_no_fragment_reads_null_WITH_its_reason():
    """Not `""` and not `0`: an environment that carries no fragment has no
    hash, and the reason says which of the two it was."""
    got = rd.rt_hash_of({"PATH": "/usr/bin"})
    assert got["value"] is None
    assert got["fragments"] == 0
    assert "RUSTDOCFLAGS" in got["reason"]
    assert rd.rt_hash_of(None)["value"] is None
    assert rd.rt_hash_of(None)["reason"]


# =============== fix round 3: the dry run's own three lines ==============
#
# These are the lines `sensorium refocus` ACTUALLY printed in the E4″ dry
# run of 2026-09-08, copied out of `p2-01-….log` and the two arm logs. They
# carry no path of any kind -- the clauses name KEYS, never values -- which
# is why they can live in a committed test.
#
# The dry existed to catch what they caught: `ENV_STRIPPED`'s body was a
# character class with no terminator of its own, so it ran on past the
# TWO-SPACE clause join into the Rust branch's "the recorder's own, also
# not compared: …" and read eleven of the recorder's uncompared variables
# as keys the strip had touched. `H2.strip_clause_named` came back 0 of 2.

#: The Rust branch's LAST clause (`refocus_rust._env_of`), which is what the
#: strip clause's names were running into.
RECORDER_OWN = (
    "the recorder's own, also not compared: "
    "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER, RUSTC_WORKSPACE_WRAPPER, "
    "SENSORIUM_CARGO_SENSORIUM, SENSORIUM_FOCUS, SENSORIUM_INVOCATION, "
    "SENSORIUM_RT_DIR, SENSORIUM_SPOOL, SENSORIUM_TARGET, SENSORIUM_TIER, "
    "SENSORIUM_TOOL_HASH, SENSORIUM_WS")
#: `refocus_world._env_state`'s two clauses, joined by `; `, then the
#: recorder's-own clause two spaces later.
CLAUSES = ("  4 variable(s) differ only by the target directory: "
           "CARGO_BIN_EXE_bloomery-daemon, CARGO_BIN_EXE_flywheel-tool, "
           "CARGO_TARGET_DIR, LD_LIBRARY_PATH; treated as unchanged; the "
           "recorder's own fragment stripped before comparing: RUSTDOCFLAGS"
           "  " + RECORDER_OWN)
#: What the run's own `_UNCOMPARED_ENV` came to on the day.
NOT_COMPARED = "OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _"

#: Arm A, verbatim.
DRY_ARM_A = (
    f"env: unchanged outside session set 1 (104 variables compared; not "
    f"compared: {NOT_COMPARED}; 1 session variable(s) differ: "
    f"CLAUDE_CODE_SESSION_ID){CLAUSES}")
#: Arm B, verbatim: the injected key on no list is CHANGED, and the session
#: clause sits after `(names only)` rather than inside the brackets.
DRY_ARM_B = (
    "env: CHANGED since the original run -- 1 variable(s) differ: "
    "E4PP_INPUT   (names only); 1 session variable(s) differ: "
    f"CLAUDE_CODE_SESSION_ID{CLAUSES}")
#: Arm C, verbatim: the chosen session key joins the set, K goes to 2.
DRY_ARM_C = (
    f"env: unchanged outside session set 1 (104 variables compared; not "
    f"compared: {NOT_COMPARED}; 2 session variable(s) differ: "
    f"CLAUDE_CODE_SESSION_ID, TERM_SESSION_ID){CLAUSES}")

RELOCATED_FOUR = ["CARGO_BIN_EXE_bloomery-daemon",
                  "CARGO_BIN_EXE_flywheel-tool", "CARGO_TARGET_DIR",
                  "LD_LIBRARY_PATH"]


@pytest.mark.parametrize("line", [DRY_ARM_A, DRY_ARM_B, DRY_ARM_C])
def test_the_strip_clause_STOPS_at_the_two_space_join(line):
    """The defect the dry run found. `RUSTDOCFLAGS` and nothing else: the
    eleven names after it belong to a DIFFERENT clause about a DIFFERENT
    claim -- "the recorder does not compare this" is not "the recorder
    removed part of this before comparing"."""
    p = rd.parse_refocus(line + "\n")
    assert p["env_stripped_keys"] == ["RUSTDOCFLAGS"]


@pytest.mark.parametrize("line", [DRY_ARM_A, DRY_ARM_B, DRY_ARM_C])
def test_the_recorders_OWN_clause_is_read_apart_and_whole(line):
    """The other half of the same join: the eleven names are read, in
    full, under the field that means what they mean."""
    p = rd.parse_refocus(line + "\n")
    own = p["env_recorder_own_keys"]
    assert own[0] == "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER"
    assert own[-1] == "SENSORIUM_WS"
    assert len(own) == 11
    assert "RUSTDOCFLAGS" not in own


@pytest.mark.parametrize("line", [DRY_ARM_A, DRY_ARM_B, DRY_ARM_C])
def test_the_relocated_four_survive_the_same_line(line):
    """`ENV_RELOCATED` is terminated by a literal of its own (`; treated as
    unchanged`), so it never had this defect -- pinned here so it cannot
    acquire one."""
    p = rd.parse_refocus(line + "\n")
    assert p["env_relocated_keys"] == RELOCATED_FOUR
    assert p["env_relocated_n"] == 4


def test_arm_As_real_line_reads_its_session_set_and_stays_unchanged():
    p = rd.parse_refocus(DRY_ARM_A + "\n")
    assert p["env_status"] == "unchanged"
    assert p["env_unchanged_outside_session"] is True
    assert p["env_session_n"] == 1
    assert p["env_session_keys"] == ["CLAUDE_CODE_SESSION_ID"]
    assert p["env_session_keys_truncated"] is False
    assert p["env_changed_keys"] == []
    assert p["env_changed_n"] == 0


def test_arm_Bs_real_line_reads_the_injected_key_as_CHANGED():
    p = rd.parse_refocus(DRY_ARM_B + "\n")
    assert p["env_status"] == "CHANGED"
    assert p["env_unchanged_outside_session"] is False
    assert p["env_changed_keys"] == ["E4PP_INPUT"]
    assert p["env_changed_n"] == 1
    # ...and the session clause, which on this branch sits between
    # `(names only)` and the two-space clause join.
    assert p["env_session_n"] == 1
    assert p["env_session_keys"] == ["CLAUDE_CODE_SESSION_ID"]


def test_arm_Cs_real_line_reads_K_of_two_with_both_names():
    p = rd.parse_refocus(DRY_ARM_C + "\n")
    assert p["env_status"] == "unchanged"
    assert p["env_session_n"] == 2
    assert p["env_session_keys"] == ["CLAUDE_CODE_SESSION_ID",
                                     "TERM_SESSION_ID"]
    assert p["env_changed_keys"] == []


@pytest.mark.parametrize("line", [DRY_ARM_A, DRY_ARM_B, DRY_ARM_C])
def test_NO_clause_of_the_real_lines_swallows_another(line):
    """Item 3 of the round, mechanical: every clause the four regexes read
    is disjoint, and together they account for the names on the line. A
    regex that ran past its own clause would show up here as a name in two
    fields at once."""
    p = rd.parse_refocus(line + "\n")
    fields = [p["env_stripped_keys"], p["env_relocated_keys"],
              p["env_recorder_own_keys"], p["env_changed_keys"],
              p["env_session_keys"]]
    seen = [n for f in fields for n in (f or [])]
    assert len(seen) == len(set(seen)), sorted(seen)
    # ...and no field carries a fragment of a neighbouring clause's PROSE.
    for name in seen:
        assert " " not in name, name
        assert ":" not in name, name
