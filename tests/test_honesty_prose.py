"""The tool's own words about SWALLOWED are the ledger's words (design N1/N2).

`rust/HONESTY-ERR-FLOW.md` §11 is the one home of the definition; the sentence the
tool prints under an escaped arm, and the four load-bearing phrases of the
definition, must be found there verbatim -- so the promise a reader meets
in the output cannot drift from the promise the ledger makes.

The section moved to `rust/HONESTY-ERR-FLOW.md` on 2026-09-06 (the focus
tier's own split, the way §1 and §8's list moved before it), wording and
order unchanged. What this file pins is the DEFINITION, not the path it
lives at, so the reader below follows the section and the assertions are
untouched."""
from pathlib import Path

from sensorium.query import exceptions_rust

REPO = Path(__file__).resolve().parents[1]


def _section_11() -> str:
    text = (REPO / "rust" / "HONESTY-ERR-FLOW.md").read_text()
    start = text.index("\n## 11. Err flow")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


def _swallowed_bullet() -> str:
    """§11's SWALLOWED bullet alone -- from `- **SWALLOWED**` to the next
    verdict bullet.

    The definition is what these phrases belong to, and §11 is a whole
    section: it also states the recorded grammar, chain identity, the four
    other verdicts and the capability refusal. Pinning the phrases to the
    SECTION let any of them satisfy the test from a paragraph that is not
    the definition -- so a sentence deleted from the definition and left
    standing anywhere else in §11 stayed green. Narrowed 2026-09-08 (the
    §11 sweep N1, finished): every phrase below is a PROMISE the SWALLOWED
    verdict makes, and the slice is the promise's own text.
    """
    s = _section_11()
    start = s.index("- **SWALLOWED**")
    return s[start:s.index("- **PANICKED**", start)]


def test_the_tools_escaped_sentence_is_in_the_swallowed_definition():
    assert exceptions_rust.ESCAPED_DETAIL in _swallowed_bullet()


def test_the_tools_escaped_sentence_names_reading_as_not_leaving():
    assert "only reads it (a guard, a predicate), formats or logs it" in exceptions_rust.ESCAPED_DETAIL


def test_the_definition_carries_its_four_load_bearing_phrases():
    """Each one a clause the verdict rests on, read from the bullet that
    makes the promise rather than from the section that contains it."""
    s = _swallowed_bullet()
    for phrase in ("no value derived from the `Err` left the arm",
                   "Reading the error does not carry it out",
                   "a guarded arm's disposition is its body's",
                   "0 of them"):
        assert phrase in s, phrase


def test_the_bullet_is_a_slice_of_the_section_and_not_the_whole_of_it():
    """The narrowing has to be a real one: a `_swallowed_bullet` that
    quietly returned all of §11 would pass every assertion above while
    restoring exactly the hole this change closed."""
    section, bullet = _section_11(), _swallowed_bullet()
    assert bullet in section and len(bullet) < len(section)
    assert bullet.startswith("- **SWALLOWED**")
    # The other verdicts' bullets are OUT: they are §11's promises too, and
    # they are not this definition.
    for other in ("- **PANICKED**", "- **RETURNED_TO_HARNESS**",
                  "- **PROPAGATED**", "- **AMBIGUOUS**"):
        assert other in section, other
        assert other not in bullet, other


def test_the_index_row_states_the_definition_in_its_post_N1_form():
    """`rust/HONESTY-INDEX.md`'s §11 row is the promise a reader meets
    first, and it stated the pre-N1 definition -- the sink and the `ok`
    close, without the clause N1 added -- for three days after the rule
    changed under it. An index row that says less than the rule is a
    promise the ledger does not keep.
    """
    row = [ln for ln in
           (REPO / "rust" / "HONESTY-INDEX.md").read_text().splitlines()
           if ln.startswith("| 11 |") and "SWALLOWED is claimed only" in ln]
    assert len(row) == 1, row
    for phrase in ("no value derived from the `Err` leaving the arm",
                   "reading the error does not carry it out",
                   "a guarded arm's disposition is its body's"):
        assert phrase in row[0], phrase
