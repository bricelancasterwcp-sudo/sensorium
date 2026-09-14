"""Which names the TypeScript branch calls the recorder's own -- an exact
set, pinned against the one function that sets them.

R33, 2026-09-14. `is_recorder_key` was `name.startswith("SENSORIUM_")`, the
same rule and the same hole E16 part A measured on the Rust branch (§2, H3):
the predicate's answer is what `refocus_licence.env_of` removes before it
compares anything, so a variable of the MEASURED PROGRAM that happens to
carry the prefix -- the pre-registered `SENSORIUM_E16_TOKEN`, or any
`SENSORIUM_`-shaped name a person exports -- was never compared, and a
re-run whose value had been rotated still earned a full licence. E16 read
that pair on the Rust arm only, because §1 exercised TypeScript's env clause
through `tests/test_refocus_redaction.py` rather than live; the defect was
the same one, in the same shape, one module over.

The TypeScript set has ONE source, which makes the pin tighter than the Rust
one: `sensorium.ts.driver._env` builds the harness's whole environment in a
single function, so this test parses that function and holds the set equal
to what it finds. `SENSORIUM_REDACT_KEY` is added rather than found, because
`_env` sets it through `redact.KEY_VAR` and no literal spells it.
"""
import ast
from pathlib import Path

import pytest

from sensorium import redact
from sensorium.query import refocus_typescript

DRIVER = (Path(__file__).resolve().parents[1]
          / "src" / "sensorium" / "ts" / "driver.py")


def _env_function() -> ast.FunctionDef:
    for node in ast.walk(ast.parse(DRIVER.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and node.name == "_env":
            return node
    raise AssertionError(f"no _env in {DRIVER}")


def set_by_the_driver() -> set[str]:
    """Every `SENSORIUM_…` name `_env` puts into the harness's environment.

    Two spellings, because the function uses two: a keyword to
    `dict(os.environ, SENSORIUM_SPOOL=…)`, and `env["SENSORIUM_FOCUS"] = …`
    for the one that is conditional. A `pop` is deliberately NOT a set site
    -- `_env` pops `SENSORIUM_FOCUS` and the key variable on the branches
    where it declines to set them, and a rule that counted a deletion would
    be counting the opposite of what it means to.
    """
    found = set()
    for node in ast.walk(_env_function()):
        if isinstance(node, ast.keyword) and node.arg:
            if node.arg.startswith("SENSORIUM_"):
                found.add(node.arg)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if not isinstance(target, ast.Subscript):
                    continue
                key = target.slice
                if (isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                        and key.value.startswith("SENSORIUM_")):
                    found.add(key.value)
    return found


def test_the_function_this_test_parses_is_where_it_expects_it():
    """A parse that found no `_env`, or an `_env` that set nothing, would
    compare an empty set against an empty set and pass for the wrong
    reason."""
    assert DRIVER.is_file(), DRIVER
    assert len(set_by_the_driver()) >= 6


def test_the_recorder_key_set_is_exactly_what_the_driver_sets():
    """The set and `_env`, held equal in both directions.

    A variable the driver starts handing the harness without a line in the
    set would be COMPARED on every refocus that mints a fresh one -- the
    licence withheld forever on the instrument's own footprint. A name left
    in the set after `_env` stopped setting it would keep a variable of the
    PROGRAM out of the comparison, which is the defect this replaces.
    """
    assert (set_by_the_driver() | {redact.KEY_VAR}
            == refocus_typescript.RECORDER_KEYS)


# -- the two directions the Rust branch read the wrong way ------------------
def test_a_users_sensorium_named_variable_is_compared():
    """E16's pre-registered token, on this branch. The TypeScript recorder
    never set it and never will; a re-run whose value changed is a re-run of
    a different world."""
    assert not refocus_typescript.is_recorder_key("SENSORIUM_E16_TOKEN")


@pytest.mark.parametrize("name", ["SENSORIUM_NO_REDACT",
                                  "SENSORIUM_REDACT_NAMES",
                                  "SENSORIUM_REDACT_ALLOW"])
def test_the_three_redaction_knobs_are_the_users_and_are_compared(name):
    """`_env` passes all three on untouched -- what a recording was made
    under is the user's statement, not the recorder's bookkeeping -- so a
    pair made under two different ones is a pair the licence must not
    certify."""
    assert not refocus_typescript.is_recorder_key(name)


@pytest.mark.parametrize("name", sorted({
    "SENSORIUM_SPOOL", "SENSORIUM_TIER", "SENSORIUM_TS_ROOT",
    "SENSORIUM_TS_PKG", "SENSORIUM_INVOCATION", "SENSORIUM_MANIFEST_DIR",
    "SENSORIUM_FOCUS", "SENSORIUM_REDACT_KEY"}))
def test_every_variable_the_driver_itself_sets_is_still_its_own(name):
    """The exclusion that has to survive the narrowing: three of these
    differ on every refocus by construction and a fourth whenever the call
    deepens the focus, so comparing them would withhold every licence on the
    instrument's own footprint."""
    assert refocus_typescript.is_recorder_key(name)
