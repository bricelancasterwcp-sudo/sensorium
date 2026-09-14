"""Which names the Rust branch calls the recorder's own -- an exact set,
pinned against the sources that set them.

E16 part A measured what the prefix cost (§2, H3): `_is_recorder_key`
answered True for EVERY `SENSORIUM_`-prefixed name, so the pre-registered
`SENSORIUM_E16_TOKEN` -- a variable of the measured program, not of the
recorder -- was removed before `env_of` compared anything. The unchanged
pair granted the licence while naming the token as not compared, and the
CHANGED pair, whose whole point was a rotated secret, granted it too. A
prefix is a promise about names nobody has written yet; the driver's own
variables are a list, and this is where the list is held to the sources.

The structural test is the one that keeps the list true, and it greps for
what the driver SETS -- `.env("SENSORIUM_…"` in
`rust/cargo-sensorium/src/{launch,runner,driver}.rs` -- and never for a bare
literal. R34, 2026-09-14: the first spelling of this test matched any quoted
`SENSORIUM_…` in those files, so `SENSORIUM_INNER_RUNNER`, which `runner.rs`
READS and no source sets, was pinned into the set as though it were ours. It
is the user's: it names the runner program they configured, which this
driver chains by running it as the executable, so a re-run under a different
one runs the binary under a different program and the licence has to say so.
A read-site is not a set-site, and the grep now knows the difference.

The behavioural tests are the two directions E16 read the wrong way, the
two variables that turned out to be the user's, and the ones the fix must
not break.
"""
import re
from pathlib import Path

import pytest

from sensorium import redact
from sensorium.query import refocus_rust

#: The three modules that could put a variable into the recorded process's
#: environment: `launch.rs` sets them all on the cargo it spawns, `runner.rs`
#: is the other half of the same binary, and `driver.rs` is where a fourth
#: would most likely be added.
SOURCES = ("launch.rs", "runner.rs", "driver.rs")

SRC = Path(__file__).resolve().parents[1] / "rust" / "cargo-sensorium" / "src"

#: A SET site: `.env("SENSORIUM_…", value)` on the `Command` the driver
#: spawns, and nothing else. Not a bare `"SENSORIUM_…"` literal, which is
#: also how a variable is READ (`non_empty_env("SENSORIUM_INNER_RUNNER")`)
#: and how a test names one -- reading a variable the user set is the
#: opposite of owning it. Backticked names in prose match neither.
SET_SITE = re.compile(r'\.env\("(SENSORIUM_[A-Z_]+)"')


def set_by_the_rust_sources() -> set[str]:
    return {name
            for source in SOURCES
            for name in SET_SITE.findall(
                (SRC / source).read_text(encoding="utf-8"))}


def test_the_sources_this_test_greps_are_where_it_expects_them():
    """A grep over three files that are not there would find nothing and
    compare an empty set against an empty set. The floor is the eight
    `launch.rs` alone sets, so a moved module is a failure and not a pass."""
    for source in SOURCES:
        assert (SRC / source).is_file(), SRC / source
    assert len(set_by_the_rust_sources()) >= 8


def test_the_recorder_key_set_is_exactly_what_the_rust_sources_name():
    """The set and the sources, held equal in both directions.

    A name the driver starts setting and nobody adds here would be COMPARED
    on every focused re-run -- it differs by construction, so the licence
    would be withheld forever on the instrument's own footprint. A name
    dropped from the driver and left here would keep a variable of the
    program out of the comparison, which is the E16 defect exactly.

    `SENSORIUM_REDACT_KEY` is added here rather than found: `launch.rs` sets
    it through the constant (`.env(sensorium_rt::redact::KEY_VAR, hex)`), so
    no literal spells it. Every recorder deletes it from what it records, and
    a trace converted before rule v1 existed still carries it -- so comparing
    it would report the tool's own key as a change the world made.
    """
    assert (set_by_the_rust_sources() | {redact.KEY_VAR}
            == refocus_rust.RECORDER_KEYS)


# -- the two E16 read the wrong way, and the two that must not break -------
def test_a_users_sensorium_named_variable_is_compared():
    """E16's pre-registered token. It is inside the old prefix and is the
    measured program's own: a Rust re-run whose value CHANGED still earned a
    full licence, because the name never reached the comparison."""
    assert not refocus_rust._is_recorder_key("SENSORIUM_E16_TOKEN")


def test_a_runner_the_user_configured_is_compared():
    """R34. `SENSORIUM_INNER_RUNNER` is READ by `runner.rs` and set by no
    source: it names the runner program the user had configured, which this
    driver chains by running it as the executable with the test binary as its
    argument. Change it between the recording and the re-run and the binary
    ran under a different program -- which is the difference a licence exists
    to name, not one it should hide."""
    assert not refocus_rust._is_recorder_key("SENSORIUM_INNER_RUNNER")


def test_the_driver_locator_is_the_users_too():
    """The same case one variable over, and the one the first pass caught:
    nothing in `cargo-sensorium` sets `SENSORIUM_CARGO_SENSORIUM` either. It
    is the Python side's knob for WHICH driver binary to re-run with, so a
    pair recorded under two drivers is a pair of two different tools."""
    assert not refocus_rust._is_recorder_key("SENSORIUM_CARGO_SENSORIUM")


@pytest.mark.parametrize("name", ["SENSORIUM_NO_REDACT",
                                  "SENSORIUM_REDACT_NAMES",
                                  "SENSORIUM_REDACT_ALLOW"])
def test_the_three_redaction_knobs_are_the_users_and_are_compared(name):
    """They are not the recorder's bookkeeping: they are the statement a
    person made about what this recording redacts. A re-run made under a
    different one is a re-run of a different thing, and the licence has to
    say so."""
    assert not refocus_rust._is_recorder_key(name)


@pytest.mark.parametrize("name", sorted({
    "SENSORIUM_FOCUS", "SENSORIUM_INVOCATION",
    "SENSORIUM_RT_DIR", "SENSORIUM_SPOOL", "SENSORIUM_TARGET",
    "SENSORIUM_TIER", "SENSORIUM_TOOL_HASH", "SENSORIUM_WS",
    "SENSORIUM_REDACT_KEY", "RUSTC_WORKSPACE_WRAPPER",
    "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER"}))
def test_every_variable_the_driver_itself_sets_is_still_its_own(name):
    """The exclusion that has to survive the narrowing: each of these
    differs between a recording and its focused re-run by construction, and
    a check that always fires says nothing."""
    assert refocus_rust._is_recorder_key(name)
