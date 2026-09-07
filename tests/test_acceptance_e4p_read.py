"""The E4′ reader's own parsers, exercised on output the REAL command wrote.

Why a second parser rather than E4's. E4's record is CLOSED: its reader is
evidence for a published measurement and is not edited. Two things moved
under it since:

* R2 gave the pair line a clause -- `run: <id>   child runs excluded from
  the pair: <ids>` -- and E4's `^run: (?P<run>\\S+)$` is anchored at the end
  of the line, so it matches the OLD shape and misses the new one entirely.
  A pair id read as `None` would be recorded as "no pair", which under H3 is
  a STOP: the instrument would manufacture the kill it is meant to detect.
* R1 rewrote the licence's thread sentences, which is the thing E4′ measures.

So the parsers here are the E4′ record's own, and every one of them is
tested against text `sensorium refocus` actually printed (the fixtures build
a `cargo test`-shaped pair and the command runs whole) rather than against a
string this file made up to match its own regex.
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

#: Design §2's clause, as one harness thread renders it -- the same constant
#: `tests/test_refocus_licence_rust.py` pins the command against.
HARNESS_PHRASE = ("1 harness thread (libtest's per-test thread, excluded as "
                  "the recorder's own)")


def _refocus(tmp_path, monkeypatch, capsys, **kw) -> str:
    """The whole command over a `cargo test`-shaped pair, both sides built
    the same way, and everything it printed."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)],
           program=partial(libtest_original, **kw))
    return capsys.readouterr().out


# ------------------------------------------------------- the pair `run:` line

def test_the_pair_line_parses_when_no_child_was_excluded(
        tmp_path, monkeypatch, capsys):
    out = _refocus(tmp_path, monkeypatch, capsys)
    p = rd.parse_refocus(out)
    assert p["pair_run"] == PAIR
    assert p["excluded_children"] == []
    assert p["child_clause"] is None


def test_the_pair_line_parses_WITH_the_child_clause(tmp_path, monkeypatch,
                                                    capsys):
    """R2's shape. The id must still come back -- a parser anchored at the
    end of the line reads this as no pair at all, and "no pair" is H3's
    STOP. The excluded ids come back beside it, because H3's second reading
    is that the list is EMPTY on all 61 and a non-empty one is a finding."""
    from tests.refocus_rust_fixtures import CHILD, CHILD_PID, PARENT_PID
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG), (CHILD, ORIG)],
           pair_meta={PAIR: {"pid": PARENT_PID, "ppid": 1},
                      CHILD: {"pid": CHILD_PID, "ppid": PARENT_PID}})
    out = capsys.readouterr().out
    p = rd.parse_refocus(out)
    assert p["pair_run"] == PAIR, out
    assert p["excluded_children"] == [CHILD], out
    assert "child runs excluded from the pair" in (p["child_clause"] or "")


def test_the_prefix_parse_reads_BOTH_shapes_of_one_line():
    """The discriminator, stated as a unit: the two spellings differ only in
    the clause, and both must yield the same id."""
    bare = rd.parse_refocus("--- verdict ---\nrun: r-1\n")
    withc = rd.parse_refocus(
        "--- verdict ---\nrun: r-1   child runs excluded from the pair: "
        "c-1, c-2\n")
    assert bare["pair_run"] == withc["pair_run"] == "r-1"
    assert bare["excluded_children"] == []
    assert withc["excluded_children"] == ["c-1", "c-2"]


def test_the_E4_readers_own_regex_would_have_MISSED_the_new_shape():
    """The reason this module exists, asserted rather than asserted-in-prose.
    If E4's pattern ever starts matching the clause, the duplication here has
    no justification left and should be revisited."""
    from acceptance_e4_read import NEW_RUN
    line = "run: r-1   child runs excluded from the pair: c-1\n"
    assert NEW_RUN.search(line) is None
    assert rd.parse_refocus("--- verdict ---\n" + line)["pair_run"] == "r-1"


# ------------------------------------------------------ the R1 licence lines

def test_a_granted_licence_names_the_excluded_harness_thread(
        tmp_path, monkeypatch, capsys):
    """The 57. Program threads 0, harness 1, and the line SAYS so -- H1's
    second reading is that a granted licence hiding the exclusion is a
    finding even when the word is the predicted one."""
    out = _refocus(tmp_path, monkeypatch, capsys)
    p = rd.parse_refocus(out)
    part = rd.licence_partition(p)
    assert part["licence"] == "granted"
    assert part["program_threads"] == 0
    assert part["harness_threads"] == 1
    assert part["names_the_exclusion"] is True
    assert part["harness_phrase"] == ("libtest's per-test thread, excluded "
                                      "as the recorder's own")


@pytest.mark.parametrize("program", [1, 4])
def test_a_withheld_licence_names_the_PROGRAMS_OWN_count(
        tmp_path, monkeypatch, capsys, program):
    """The four. §1.2: the reason names the program's own thread count (1,
    4, 4, 4) AND states the harness thread was excluded. A reason naming the
    RAW count (2, 5) never subtracted, and is H1's STOP."""
    out = _refocus(tmp_path, monkeypatch, capsys, program_threads=program)
    part = rd.licence_partition(rd.parse_refocus(out))
    assert part["licence"] == "WITHHELD"
    assert part["program_threads"] == program
    assert part["harness_threads"] == 1
    assert part["names_the_exclusion"] is True
    assert part["raw_thread_count"] == program + 1


def test_both_sides_are_read_and_their_AGREEMENT_is_a_recorded_fact(
        tmp_path, monkeypatch, capsys):
    """§1.2: "the original and the rerun agree on N for every pair". Read
    from both labels, so a disagreement is visible rather than resolved by
    whichever sentence the regex reached first."""
    out = _refocus(tmp_path, monkeypatch, capsys, program_threads=4)
    part = rd.licence_partition(rd.parse_refocus(out))
    assert part["per_label"] == {"the original": 4, "the rerun": 4}
    assert part["sides_agree"] is True


def test_a_granted_line_that_HIDES_the_exclusion_is_read_as_such():
    """H1's second reading has to be able to fire. The unmarked-thread
    branch of `harness_threads` prints the provenance clause instead, and
    the parser must report `names_the_exclusion` False there rather than
    defaulting to True and making the finding unreachable."""
    text = ("--- verdict ---\n"
            "licence: verified against r-1 on exactly these points, and no "
            "others:\n"
            "  - identical call shape across 1 compared fingerprint(s)\n"
            "  - no thread started besides the main one as OS threads "
            "(libtest's per-test threads and threads spawned by workspace "
            "code), and none left running when recording stopped\n")
    part = rd.licence_partition(rd.parse_refocus(text))
    assert part["licence"] == "granted"
    assert part["names_the_exclusion"] is False
    assert part["harness_threads"] is None
    assert part["program_threads"] == 0


def test_an_unparsed_licence_is_None_everywhere_and_never_zero():
    """None-vs-zero, at the one place it decides a gate. A pair whose
    licence line never printed has NO partition; reading it as `0 program
    threads, granted` would put a measured-looking cell where a missing one
    belongs."""
    part = rd.licence_partition(rd.parse_refocus("nothing was printed\n"))
    assert part["licence"] is None
    assert part["program_threads"] is None
    assert part["harness_threads"] is None
    assert part["names_the_exclusion"] is None
    assert part["sides_agree"] is None


def test_the_threads_line_carries_the_same_partition(tmp_path, monkeypatch,
                                                     capsys):
    """`harness_note`'s clause, on a line whose counts the harness thread is
    NOT one of. Read separately from the licence's, so the two readings of
    one fact can be compared rather than assumed equal."""
    out = _refocus(tmp_path, monkeypatch, capsys)
    p = rd.parse_refocus(out)
    assert p["threads_line"] is not None
    assert p["threads_harness"] == 1
    assert "not among these counts" in p["threads_line"]


# --------------------------------------------------------- the rest of a pair

def test_the_verdict_word_and_the_exit_are_read_apart(tmp_path, monkeypatch,
                                                      capsys):
    out = _refocus(tmp_path, monkeypatch, capsys)
    p = rd.parse_refocus(out)
    assert p["verdict_word"] == "MATCH"
    assert rd.VERDICT_EXIT[p["verdict_word"]] == 0


def test_the_two_unverifiable_checks_are_kept_out_of_the_verified_list(
        tmp_path, monkeypatch, capsys):
    """§1.4's rule: output and children are UNVERIFIABLE by construction on
    a Rust pair and are never counted as verified, nor summed into one."""
    out = _refocus(tmp_path, monkeypatch, capsys)
    counts = rd.licence_counts(rd.parse_refocus(out))
    assert counts["output_unverifiable"] is True
    assert counts["children_unverifiable"] is True
    assert counts["unverifiable_checks"] == 2
    assert "verified_total" not in counts


# ---------------------------------------------------------- H4's census

def _shim(tmp_path, keys, driver_bytes=1000):
    """A driver and a shim tree, with each key either HARD-LINKED to the
    driver or a copy of it -- the two outcomes R3 can produce."""
    driver = tmp_path / "driver" / "cargo-sensorium"
    driver.parent.mkdir(parents=True)
    driver.write_bytes(b"x" * driver_bytes)
    shim = tmp_path / "target" / "sensorium" / "shim"
    for key, linked in keys:
        d = shim / key
        d.mkdir(parents=True)
        binary = d / "cargo-sensorium"
        if linked:
            import os
            os.link(driver, binary)
        else:
            binary.write_bytes(b"y" * driver_bytes)
    return tmp_path / "target", driver


def test_the_census_counts_bytes_ONCE_PER_INODE_and_never_per_entry(tmp_path):
    """§1.4's H4 second reading, and the measurement error the endpoint is
    about: 61 hard links to one 40 MB binary hold 40 MB, not 2.4 GB. The
    three numbers are separate and the byte total is never the sum of the
    per-entry sizes.

    A monkeypatched census cannot check this -- the arithmetic IS the
    endpoint -- so the tree here is real and the links are real.
    """
    target, driver = _shim(tmp_path, [(f"k{i}", True) for i in range(5)],
                           driver_bytes=1000)
    c = rd.shim_census(target, driver)
    assert c["keys"] == 5 and c["entries"] == 5
    assert c["distinct_inodes"] == 1
    assert c["bytes_once_per_inode"] == 1000
    assert c["bytes_once_per_inode"] != 5 * 1000
    assert c["linked_to_the_driver"] == 5
    assert c["not_linked"] == []


def test_a_COPY_is_a_distinct_inode_and_its_bytes_are_counted(tmp_path):
    """The other side: a key that was copied rather than linked holds bytes
    of its own, and both the inode count and the total must say so."""
    target, driver = _shim(tmp_path, [("k0", True), ("k1", False),
                                      ("k2", True)], driver_bytes=1000)
    c = rd.shim_census(target, driver)
    assert c["entries"] == 3
    assert c["distinct_inodes"] == 2
    assert c["bytes_once_per_inode"] == 2000
    assert c["linked_to_the_driver"] == 2
    assert c["not_linked"] == ["k1"]


def test_a_census_path_that_is_not_there_is_None_entries_and_never_zero(
        tmp_path):
    """A target that never keyed a shim and one that keyed an empty shim are
    different facts."""
    driver = tmp_path / "cargo-sensorium"
    driver.write_bytes(b"x")
    c = rd.shim_census(tmp_path / "nowhere", driver)
    assert c["exists"] is False
    assert c["entries"] is None and c["distinct_inodes"] is None
    assert c["bytes_once_per_inode"] is None


def test_the_device_is_recorded_beside_the_inode_comparison(tmp_path):
    """§1.2: a link across a filesystem boundary is impossible rather than
    wrong, so `st_dev` decides whether H4's finding branch applies at all."""
    target, driver = _shim(tmp_path, [("k0", True)])
    c = rd.shim_census(target, driver)
    assert c["same_device"] is True
    assert c["driver_dev"] in c["devices"]
    assert c["driver_inode"] is not None
