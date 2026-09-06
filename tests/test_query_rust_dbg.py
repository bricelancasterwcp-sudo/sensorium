"""`watch` and `flow` over a FOCUSED Rust trace: `::`, and what `dbg` means.

Two claims are pinned here, and they are the only two the query side gains
for Rust (design 2026-09-06 §4).

  * A qualname spec selects on the boundary the language actually uses.
    `Counter` selects `Counter::new` the way `Pot` already selects `Pot.add`,
    and `Counters::new` is a different function -- a prefix that does not end
    at a boundary is not a match, or `--at Counter` would silently answer
    about code the reader did not name.
  * A `dbg` capture is Debug TEXT, and reading it is defined rather than
    guessed: `resolve` maps the text to the value it spells (an integer, a
    float, a bool, a quoted string, else the text itself), and `matches`
    compares a literal's Debug RENDERING with the recorded text. Both refuse
    a truncated capture, because what the trace holds is then a prefix of the
    rendering and not the rendering.

The one thing neither of them may do is answer from a rendering that cannot
carry the answer: `len(name)` over Debug text would be the length of the
SPELLING (`"A1"` is four characters, the string is two), so the site is
reported as one the predicate could not be checked at -- UNSETTLED, never a
comparison to nothing.
"""
import math

import pytest

from sensorium import cli
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from sensorium.query.expr import NOT_CAPTURED, TRUNCATED, resolve
from sensorium.query.flow_values import ObjTarget, matches
from sensorium.query.rust_debug import debug_text
from sensorium.query.watch_cmd import _qual_matches
from tests.rust_traces import dbg, focused_trace, out


# -- (a) the qualname boundary ---------------------------------------------
def test_a_qualname_spec_selects_on_the_rust_boundary_too():
    """`::` is Rust's boundary, `.` is Python's, and ONE helper knows both:
    `watch --at` is a capability dispatcher, not a language switch."""
    assert _qual_matches("Counter::new", "Counter") is True
    assert _qual_matches("Counter::new", "Counter::new") is True
    # a prefix that does not end at a boundary is a DIFFERENT function
    assert _qual_matches("Counters::new", "Counter") is False
    # and the dot rule is untouched
    assert _qual_matches("Pot.add", "Pot") is True
    assert _qual_matches("Pots.add", "Pot") is False


# -- (b) reading a dbg capture ---------------------------------------------
def test_resolve_reads_the_value_a_debug_text_spells():
    assert resolve(dbg("5")) == 5
    assert resolve(dbg("-3")) == -3
    assert resolve(dbg("2.5")) == 2.5
    assert resolve(dbg("true")) is True
    assert resolve(dbg("false")) is False
    # the exponent spellings Rust prints for the extremes, READ back as the
    # floats they are -- `flow --value 1e20` sights them, so a predicate at
    # that site has to see a number too (design amendment A11)
    assert resolve(dbg("1e20")) == 1e20
    assert resolve(dbg("1e-5")) == 1e-5
    assert resolve(dbg("1.5e-7")) == 1.5e-7
    assert resolve(dbg("None")) is None        # `Option::None`, the value


def test_resolve_unquotes_a_debug_string_and_undoes_its_escapes():
    r"""Rust's `Debug` for a string quotes it and escapes `"` `\` and the
    unprintables. The value is what is INSIDE, unescaped -- so `s == "a"b"`
    compares the string the program held, not its spelling."""
    assert resolve(dbg('"A1"')) == "A1"
    assert resolve(dbg(r'"a\"b"')) == 'a"b'
    assert resolve(dbg(r'"caf\u{e9}"')) == "café"
    assert resolve(dbg(r'"one\ttwo\nthree\\"')) == "one\ttwo\nthree\\"
    # non-ASCII is NOT escaped by Rust, and must survive being read back
    assert resolve(dbg('"café 日"')) == "café 日"


def test_resolve_reads_the_floats_rust_spells_as_words():
    """`inf`, `-inf` and `NaN` are Rust's spellings for the three floats
    that are not digits (measured). They are read as those floats, because
    `flow --value 1e400` sights one and the two commands may not disagree
    about a capture (design amendment A11)."""
    assert resolve(dbg("inf")) == float("inf")
    assert resolve(dbg("-inf")) == float("-inf")
    assert math.isnan(resolve(dbg("NaN")))


def test_resolve_hands_back_the_text_when_it_spells_no_literal():
    """A struct, an enum, a Vec: the text is what the trace holds, so the
    text is what a predicate sees."""
    assert resolve(dbg("Counter { n: 7 }")) == "Counter { n: 7 }"
    assert resolve(dbg("[1, 2, 3]")) == "[1, 2, 3]"
    assert resolve(dbg("Basic")) == "Basic"
    assert resolve(dbg("Some(3)")) == "Some(3)"


def test_resolve_refuses_a_truncated_dbg_and_an_unread_delta():
    """The cap stopped the formatter mid-value, so what is recorded is a
    PREFIX of the rendering: comparing it would be a claim about characters
    the trace does not hold."""
    assert resolve(dbg("[1, 2, 3, ", trunc=True)) is TRUNCATED
    assert resolve(dbg('"A1"', trunc=True)) is TRUNCATED
    assert resolve({"k": "unread"}) is NOT_CAPTURED


# -- the two directions are inverses (design amendment A11) ----------------
# Every literal a command can name, spelled by the side that writes Debug
# text and read back by the side that reads it. The list is the domain: an
# entry either round-trips or the two commands can disagree about one
# capture, which is what A11 exists to prevent.
LITERALS = [0, 5, -3, 2.0, -3.5, 1e20, 1e-5, float("inf"), float("-inf"),
            True, False, None, "A1", 'q"uote', "café 日", "", "Basic"]


@pytest.mark.parametrize("literal", LITERALS, ids=repr)
def test_resolve_reads_back_everything_debug_text_can_spell(literal):
    """`resolve(dbg(debug_text(L))) == L`, for every L. Measured against the
    disagreement it fixes: `flow --value 1e20` used to report a sighting at
    a site where `watch --expr x == 1e20` said `not satisfied`."""
    text = debug_text(literal)
    assert text is not None, "debug_text must spell every literal"
    got = resolve(dbg(text))
    assert got == literal
    # `0 == False` in Python, so equality alone would let a bool pass for a
    # number and back again
    assert isinstance(got, bool) is isinstance(literal, bool)
    assert (got is None) is (literal is None)


def test_the_one_literal_that_does_not_read_back_is_nan():
    """As in Rust, and as in Python: NaN equals nothing, itself included.
    The rendering still round-trips to A float that is NaN."""
    assert debug_text(float("nan")) == "NaN"
    assert math.isnan(resolve(dbg(debug_text(float("nan")))))


# -- (c) matching a literal against a dbg capture --------------------------
def test_matches_compares_a_literal_with_its_debug_rendering():
    assert matches(dbg("5"), 5) is True
    assert matches(dbg("2.5"), 2.5) is True
    assert matches(dbg("2.0"), 2.0) is True
    assert matches(dbg("true"), True) is True
    assert matches(dbg('"A1"'), "A1") is True
    assert matches(dbg("None"), None) is True


def test_matches_is_the_rendering_and_not_the_python_text():
    """`str(target)` would report a sighting of the string A1 at a capture
    whose Debug is `A1` -- an enum variant, a type name, a bare word. The
    quotes are how Rust says "this one is a string"."""
    assert matches(dbg("A1"), "A1") is False
    assert matches(dbg('"A1"'), "A1") is True
    assert matches(dbg("True"), True) is False      # Rust spells it `true`
    assert matches(dbg("5"), True) is False         # a bool is not a 1 or a 5
    assert matches(dbg("5"), 5.0) is False          # nor 5 the float `5.0`


def test_matches_refuses_a_truncated_dbg_and_never_reports_an_object():
    assert matches(dbg('"A1"', trunc=True), "A1") is False
    assert matches(dbg("5", trunc=True), 5) is False
    # `--object` on a Rust trace is refused before this, but the rule holds
    # here too: a Debug text carries no address, so it is nobody's identity.
    assert matches(dbg("Counter { n: 7 }"), ObjTarget(140, "Counter")) is False


def test_debug_text_spells_a_literal_the_way_rust_does():
    """Measured against `rustc` (2026-09-06), not assumed: `{:?}` prints
    `2.0` for 2.0, `1e20` where Python's repr says `1e+20`, and `1e-5` where
    it says `1e-05`."""
    assert debug_text(5) == "5"
    assert debug_text(-3) == "-3"
    assert debug_text(2.0) == "2.0"
    assert debug_text(2.5) == "2.5"
    assert debug_text(1e20) == "1e20"
    assert debug_text(1e-5) == "1e-5"
    assert debug_text(True) == "true"
    assert debug_text(False) == "false"
    assert debug_text(None) == "None"
    assert debug_text("A1") == '"A1"'
    assert debug_text('a"b\\') == r'"a\"b\\"'
    assert debug_text("one\ttwo\n") == r'"one\ttwo\n"'
    assert debug_text("café 日") == '"café 日"'      # Rust escapes neither
    assert debug_text("bell\x07") == r'"bell\u{7}"'


# -- (d) end to end, on a focused Rust trace -------------------------------
def test_watch_answers_over_the_line_rows_of_a_focused_rust_trace(
        tmp_path, monkeypatch, capsys):
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "fill",
                     "--expr", "b == 2"]) == ANSWERED
    text = out(capsys)
    assert "verdict: SATISFIED at 2 of the 2 site(s)" in text
    assert "state: b=2" in text


def test_watch_says_not_satisfied_where_the_line_rows_disagree(
        tmp_path, monkeypatch, capsys):
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "fill",
                     "--expr", "b == 3"]) == NEGATIVE
    assert "verdict: not satisfied" in out(capsys)


def test_watch_at_a_container_selects_the_functions_under_it(
        tmp_path, monkeypatch, capsys):
    """The boundary rule, reaching site selection: `--at Counter` is the
    whole impl block, and the trace answers about `Counter::new`."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "Counter",
                     "--expr", "n == 7"]) == ANSWERED
    assert "state: n=7" in out(capsys)


def test_flow_value_sights_a_number_and_a_string_in_the_line_deltas(
        tmp_path, monkeypatch, capsys):
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--value", "2"]) == ANSWERED
    text = out(capsys)
    assert "[local b]" in text
    assert "sightings: 1 event(s), 1 capture(s)" in text

    # both spellings name the same STRING: `parse_literal` strips the
    # quotes the shell needed, and the Debug rendering puts Rust's back on
    for spelled in ('"A1"', "A1"):
        assert cli.main(["flow", run_id, "--value", spelled]) == ANSWERED
        text = out(capsys)
        assert "[local s]" in text
        assert "sightings: 1 event(s), 1 capture(s)" in text


def test_a_bare_word_debug_text_is_not_a_sighting_of_that_string(
        tmp_path, monkeypatch, capsys):
    """`Tier::Basic` prints as the bare word `Basic`; a string prints with
    QUOTES. So `--value Basic` -- which searches for the string, however the
    shell spelled it -- does not sight the variant, and the predicate, where
    text is compared as text, is how to ask about one."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--value", "Basic"]) == NEGATIVE
    assert "sightings: 0 event(s), 0 capture(s)" in out(capsys)

    assert cli.main(["watch", run_id, "--at", "fill",
                     "--expr", 'tier == "Basic"']) == ANSWERED
    assert "verdict: SATISFIED" in out(capsys)


@pytest.mark.parametrize("name,spelled,literal", [
    ("big", "1e20", "1e20"),
    ("huge", "1e400", "1e400"),      # `float("1e400")` is inf, and Rust's
    ("opt", "None", "None"),         # `Option::None` is the word `None`
], ids=["exponent-float", "infinity", "none"])
def test_flow_and_watch_agree_about_one_capture(
        name, spelled, literal, tmp_path, monkeypatch, capsys):
    """The disagreement A11 was written for: each of these three used to be
    a sighting for `flow` and a `not satisfied` for `watch`, about the same
    capture at the same site. Both now answer yes."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--value", spelled]) == ANSWERED
    assert f"[local {name}]" in out(capsys)

    assert cli.main(["watch", run_id, "--at", "fill",
                     "--expr", f"{name} == {literal}"]) == ANSWERED
    assert "verdict: SATISFIED" in out(capsys)


# -- (e) the length of a rendering is not the length of the value ----------
def test_len_over_a_dbg_string_is_reported_unsettled_never_answered(
        tmp_path, monkeypatch, capsys):
    """`len(s)` over `"A1"` would be 4 if the text were taken for the value,
    or 2 if the quotes were stripped and the escapes believed -- and neither
    is a length the recorder measured. The site is reported, not answered."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "fill",
                     "--expr", "len(s) > 1"]) == UNSETTLED
    text = out(capsys)
    assert "verdict: NOTHING WAS CHECKED" in text
    assert "s: recorded as a value that has no length" in text
    # the guidance under it, in full: the reason line says what is missing,
    # this says what to do about it, and it must not send a reader after
    # scope (the name IS bound here) or after a re-recording (nothing about
    # a rendering has a length to record)
    assert ("what the trace holds there is the value itself -- a number, a "
            "bool, or a rendering the recorder could only format -- and none "
            "of those carries a recorded length; compare the name itself "
            "instead") in " ".join(text.split())
    assert "'hits: 0' here means 'could not evaluate'" in text
    # and no count of characters leaked into the answer
    assert "hits: 0" in text and "SATISFIED at" not in text
