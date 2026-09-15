"""Rule v1's content rule -- the §2.2 patterns, pinned to the same fixture
`test_redact.py` reads (`docs/trace-format/redaction-v1.json`'s `content`
list), which `sensorium-rt`'s converter and `typescript/test/redact.test.mjs`
read too. A case belongs there, not in this file: three implementations of
one rule agree only on what all three are asked.

Two operations exist in rule v1 (§2.3): a NAME hit redacts the whole value,
a CONTENT hit replaces the matched SPAN and keeps everything around it. This
module is the content half, tested here in isolation from the name rule
`test_redact.py` already covers.
"""
import json
from pathlib import Path

import pytest

from sensorium.redact_content import PATTERNS, content, triggers

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "docs" / "trace-format" / "redaction-v1.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["content"]

#: Every row name a positive case must exist for -- the whole of §2.2, table
#: order. A pattern added to `PATTERNS` without a name here is a pattern the
#: fixture is never asked to cover.
PATTERN_NAMES = [name for name, _, _ in PATTERNS]


def _ids(cases):
    return [f"{i}-{c['pattern']}" for i, c in enumerate(cases)]


@pytest.mark.parametrize("case", CASES, ids=_ids(CASES))
def test_content(case):
    assert content(case["text"]) == (case["after"], case["after"] != case["text"])


def test_every_pattern_has_a_positive_and_a_negative_row():
    """A pattern with no positive is a pattern nothing here proves fires; a
    pattern with no negative is a pattern nothing here proves has a floor."""
    by_pattern = {}
    for case in CASES:
        by_pattern.setdefault(case["pattern"], []).append(
            case["after"] != case["text"])
    for name in PATTERN_NAMES:
        hits = by_pattern.get(name, [])
        assert any(hits), f"{name} has no positive row"
        assert not all(hits), f"{name} has no negative row"


def test_every_positive_passes_the_trigger():
    """B18's pre-check: a positive case that the trigger misses is a secret
    the content rule would silently never look at.

    `triggers`, never one of its two halves: the case-sensitive alternation
    alone answered False on `Authorization: BEARER <token>` and the table
    never ran (ruling R21), which is exactly what this test exists to catch.
    """
    for case in CASES:
        if case["after"] != case["text"]:
            assert triggers(case["text"]), (
                f"{case['pattern']!r}'s positive does not pass the trigger: "
                f"{case['text']!r}")


def test_the_rule_is_a_fixed_point():
    """A text that has been through the rule once holds no trigger the rule
    would act on again -- the marker itself contains none of §2.2's shapes."""
    for case in CASES:
        assert content(case["after"])[0] == case["after"]


def test_a_marker_is_never_re_redacted():
    """The bare marker, alone, is never mistaken for a value to redact."""
    from sensorium.redact import REDACTED
    assert content(REDACTED) == (REDACTED, False)


def test_a_url_userinfo_marker_in_context_is_a_no_op():
    """§2.3's boundary case: `hit` means the TEXT CHANGED, not that a pattern
    matched. `url-userinfo` matches `postgres://u:<redacted>@h/db` (its group
    is already the marker), and the converter counts on this staying a
    no-op."""
    from sensorium.redact import REDACTED
    text = f"postgres://u:{REDACTED}@h/db"
    assert content(text) == (text, False)


def test_empty_string_is_a_no_op():
    assert content("") == ("", False)


def test_a_string_with_no_trigger_is_the_cheap_common_case():
    text = "just some ordinary log line"
    assert content(text) == (text, False)
