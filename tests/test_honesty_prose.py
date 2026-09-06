"""The tool's own words about SWALLOWED are the ledger's words (design N1/N2).

`rust/HONESTY.md` §11 is the one home of the definition; the sentence the
tool prints under an escaped arm, and the four load-bearing phrases of the
definition, must be found there verbatim -- so the promise a reader meets
in the output cannot drift from the promise the ledger makes."""
from pathlib import Path

from sensorium.query import exceptions_rust

REPO = Path(__file__).resolve().parents[1]


def _section_11() -> str:
    text = (REPO / "rust" / "HONESTY.md").read_text()
    start = text.index("\n## 11. Err flow")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


def test_the_tools_escaped_sentence_is_in_honesty_section_11():
    assert exceptions_rust.ESCAPED_DETAIL in _section_11()


def test_the_tools_escaped_sentence_names_reading_as_not_leaving():
    assert "only reads it (a guard, a predicate), formats or logs it" in exceptions_rust.ESCAPED_DETAIL


def test_the_definition_carries_its_four_load_bearing_phrases():
    s = _section_11()
    for phrase in ("no value derived from the `Err` left the arm",
                   "Reading the error does not carry it out",
                   "a guarded arm's disposition is its body's",
                   "0 of them"):
        assert phrase in s, phrase
