"""Which hand applied rule v1 to a TypeScript spool, and whether it runs.

Two decisions, both read off the BOOT record and both taken ONCE per spool,
because every value site in `build.py` needs the same answer:

* **`rule_runs`** -- whether rule v1 applies to this spool's captures at all
  (B26). A recording made with the rule off is converted as it was written.
* **`ran_the_value_rule`** -- whether the RECORDER already applied the NAME
  half, which decides both what `build.py` has left to do and the `by` word
  the trace carries (B2).

Its own module for the reason `cargo-sensorium`'s `convert/redaction.rs` is
one: the converter's mapping is long enough already, and this is the part of
it that has to be read against the design's §5.4 rather than against the
wire.
"""
import re

#: The `sensorium-ts` the value half of rule v1 shipped in (B2). A BOOT
#: below it says `mode: "on"` about its ENVIRONMENT and nothing else, so the
#: converter runs the name rule over its captures itself.
VALUES_FROM = (0, 6, 0)


def ran_the_value_rule(boot: dict) -> bool:
    """Whether the RECORDER applied rule v1 to its own captures (B2).

    Two facts together: the BOOT says `mode: "on"`, and it was written by a
    recorder that HAD the value rules. 0.5.0 says `mode: "on"` about its
    environment while its captures are plaintext, and a converter that
    trusted the word alone would pass those through as recorded.
    """
    recorded = boot.get("redaction")
    return (isinstance(recorded, dict) and recorded.get("mode") == "on"
            and version_tuple(boot.get("version")) >= VALUES_FROM)


def rule_runs(boot: dict) -> bool:
    """Whether rule v1 runs over this spool's captures at all (B26).

    True for a spool written before the rule existed -- it is exactly the
    spool whose captures nobody has judged -- and for one whose BOOT says
    `mode: "on"`. False for `mode: "off"`, for a mode this converter does
    not know, and for a `redaction` that is not an object: the same set
    `_redaction` passes through untouched, because a converter that added a
    judgement to a header it could not read would be reporting one nobody
    made.
    """
    recorded = boot.get("redaction")
    if not recorded:
        return True
    return isinstance(recorded, dict) and recorded.get("mode") == "on"


def version_tuple(reported) -> tuple[int, ...]:
    """`"0.6.0"` -> `(0, 6, 0)`, and `()` for anything unreadable.

    The empty tuple sorts BELOW every real version, so a spool that names no
    writer is treated as older than the rule -- the safe direction, where
    the converter applies it rather than assuming somebody else did.
    """
    if not isinstance(reported, str):
        return ()
    return tuple(int(n) for n in re.findall(r"\d+", reported)[:3])
