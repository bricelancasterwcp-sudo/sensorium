"""The second `dbg` dialect, held to a table the recorder itself wrote.

`typescript/test/fixtures/inspect-table.json` is not a transcription of what
`util.inspect` is believed to print: every row's text came out of `dbg()`,
the one function every capture this recorder puts on the wire goes through,
under this Node (`node typescript/test/fixtures/gen-inspect-table.mjs`
regenerates it). So the two claims below are checked against a MEASUREMENT
rather than against a second opinion:

  * `read_inspect` reads each row's text as the value the row names --
    design 2026-09-11 section 4.1 -- and a text that spells no value comes
    back as text.
  * `inspect_text` WRITES each scalar row's text, so `flow --value` searches
    for the very characters the recorder wrote. A11's property, in the
    second dialect: `read_inspect(inspect_text(L)) == L` over the literal
    domain a command accepts -- integers BELOW 2**53, and above that the
    double JavaScript holds instead of the integer typed (ruling R34; there
    is no distinct number up there to round-trip to).

THE ROWS THAT SURPRISE
----------------------
Two of them, and both are why the table is measured:

  * the 150-character string carries `trunc: false`. Its rendering was cut
    by inspect's own `maxStringLength`, not by the 200-byte wire cap, so the
    flag every other clipped capture raises is DOWN and the only evidence
    that characters are missing is the `... 50 more characters` tail. The
    reader answers TRUNCATED off the tail (plan P7), and `inspect_text`
    returns None for any string past 100 characters rather than spelling a
    tail of its own.
  * node names `\\n \\t \\r \\b \\f` and spells the vertical tab `\\x0B`
    (uppercase hex), so a writer that emitted `\\v` -- as a table read off
    JavaScript's own escape list would -- writes characters this recorder
    never writes, and `flow --value` would report no sighting of a string
    the trace holds. The reader still undoes `\\v`: undoing an escape the
    writer did not have to make is harmless, refusing one is not (the rule
    `rust_debug` states for `\\'`).
"""
import json
import math
from pathlib import Path

import pytest

from sensorium.query.expr import TRUNCATED, UNDEFINED, _DbgText
from sensorium.query.js_inspect import inspect_text, js_number, read_inspect

TABLE = (Path(__file__).resolve().parents[1] / "typescript" / "test"
         / "fixtures" / "inspect-table.json")
ROWS = json.loads(TABLE.read_text())

#: A value with no literal at all -- a function, a class, a Map, a Date. What
#: the reader must do with such a text is hand it back AS text.
OPAQUE = object()

#: The one-key objects the fixture uses for values JSON cannot spell.
MARKERS = ("bigint", "undefined", "nan", "inf", "negzero", "opaque")


def literal_of(lit):
    """The Python value one row's `literal` field names, or `OPAQUE`."""
    if isinstance(lit, dict) and len(lit) == 1 and next(iter(lit)) in MARKERS:
        (key, val), = lit.items()
        if key == "bigint":
            return int(val)
        if key == "undefined":
            return UNDEFINED
        if key == "nan":
            return float("nan")
        if key == "inf":
            return math.inf * val
        if key == "negzero":
            return -0.0
        return OPAQUE                          # key == "opaque"
    if isinstance(lit, (dict, list)):
        # An array or an object: a real JSON value, and still no literal a
        # command can name -- `--value` takes scalars.
        return OPAQUE
    return lit


def ids_for(rows):
    return [f"{i:02d}:{r['text'][:24]}" for i, r in enumerate(rows)]


def clipped(value) -> bool:
    """Whether inspect cut this row's own rendering (`maxStringLength`)."""
    return isinstance(value, str) and len(value) > 100


# -- the table is what this file is about ----------------------------------
def test_the_table_is_the_recorder_s_own_and_covers_every_shape():
    """A guard on the guard: a fixture that stopped holding rows, or that
    grew a row whose text came from somewhere other than `dbg`, would let
    every parametrised test below pass by having nothing to check."""
    assert len(ROWS) >= 39, len(ROWS)
    assert all(set(r) == {"literal", "text", "trunc"} for r in ROWS)
    texts = {r["text"] for r in ROWS}
    for wanted in ("'abc'", '"it\'s"', "undefined", "null", "true", "false",
                   "1e+21", "-0", "123n", "[ 1, 2 ]", "[Function: foo]"):
        assert wanted in texts, wanted


def test_no_row_tripped_the_wire_cap_so_trunc_says_nothing_here():
    """Every rendering in the table is under 200 bytes, the 150-character
    string included: its tail is INSPECT's truncation and the capture's own
    `trunc` flag is false. That is the whole reason the reader may not read
    truncation off the flag alone."""
    assert not any(r["trunc"] for r in ROWS)
    long_row = next(r for r in ROWS if "more characters" in r["text"])
    assert long_row["trunc"] is False


@pytest.mark.parametrize("row", ROWS, ids=ids_for(ROWS))
def test_every_row_reads_as_the_value_it_names(row):
    value, text = literal_of(row["literal"]), row["text"]
    got = read_inspect(text)
    if value is OPAQUE:
        # A struct, a function, a Map: the text is what the trace holds, so
        # the text is what a predicate sees.
        assert isinstance(got, _DbgText) and got == text
        return
    if clipped(value):
        assert got is TRUNCATED
        return
    if value is UNDEFINED:
        assert got is UNDEFINED
        return
    if isinstance(value, float) and math.isnan(value):
        assert isinstance(got, float) and math.isnan(got)
        return
    assert got == value
    # `0 == False` and `0.0 == -0.0` in Python, so equality alone would let
    # a bool pass for a number and a negative zero for a positive one.
    assert isinstance(got, bool) is isinstance(value, bool)
    assert (got is None) is (value is None)
    if isinstance(value, float) and value == 0:
        assert math.copysign(1.0, got) == math.copysign(1.0, value)


@pytest.mark.parametrize("row", ROWS, ids=ids_for(ROWS))
def test_every_scalar_row_is_written_exactly_as_the_recorder_wrote_it(row):
    """The writer's half. Three kinds of row are excluded, each for a
    reason a comment states rather than for convenience."""
    value, text = literal_of(row["literal"]), row["text"]
    if value is OPAQUE or value is UNDEFINED:
        # No literal to write: `--value` takes scalars, and `undefined` is
        # not one a command line can name (it parses as the word).
        assert inspect_text(value) is None
        return
    if clipped(value):
        # P7: what the recorder wrote is a PREFIX, and a prefix equals
        # nothing. Spelling inspect's tail here would report a sighting of
        # characters that were never recorded.
        assert inspect_text(value) is None
        return
    if isinstance(value, int) and not isinstance(value, bool) and "n" in text:
        # A BigInt's text is `123n` and a command's `--value 123` is the
        # NUMBER 123, which JavaScript spells `123`. The reader still reads
        # `123n` as 123, so `watch --expr x == 123` answers at a site
        # `flow --value 123` does not list; declared, not hidden.
        assert inspect_text(value) == "123" != text
        return
    assert inspect_text(value) == text


# -- the property, over the domain a command accepts -----------------------
# Every literal `parse_literal` can hand `flow --value`, spelled by the side
# that writes inspect text and read back by the side that reads it. An entry
# either round-trips or the two commands can disagree about one capture.
LITERALS = [0, 5, -5, 2, 2.5, -3.5, 1e21, 1e-7, 1e-6, 123456789.123,
            1.5e300, 5e-324, -0.0, math.inf, -math.inf, True, False, None,
            "abc", "it's", 'it\'s "x"', "it's \"x\" `y`", "a\nb\tc\\d",
            "café 日", "", "x" * 100, "[Function: foo]",
            'it\'s "x" ${y}', "${y}", "a\bb\fc\vd"]


@pytest.mark.parametrize("literal", LITERALS, ids=repr)
def test_read_inspect_reads_back_everything_inspect_text_can_spell(literal):
    text = inspect_text(literal)
    assert text is not None, "inspect_text must spell every literal"
    got = read_inspect(text)
    assert got == literal
    assert isinstance(got, bool) is isinstance(literal, bool)
    assert (got is None) is (literal is None)


def test_the_one_literal_that_does_not_read_back_is_nan():
    """As in JavaScript, and as in Python: NaN equals nothing, itself
    included. The rendering still round-trips to A float that is NaN."""
    assert inspect_text(float("nan")) == "NaN"
    assert math.isnan(read_inspect(inspect_text(float("nan"))))


def test_an_integral_float_is_its_integer_which_is_rusts_opposite():
    """In JavaScript `5.0` IS `5` -- there is no other number -- so
    `flow --value 5.0` must sight a capture whose text is `5`. Rust's
    `Debug` prints `2.0` for 2.0 and `debug_text` spells it that way; the
    two dialects disagree here on purpose."""
    assert inspect_text(5.0) == "5"
    assert inspect_text(2.0) == "2"
    assert inspect_text(-0.0) == "-0"
    assert read_inspect("5") == 5


def test_a_string_past_the_cap_is_written_by_nobody_and_read_as_a_prefix():
    assert inspect_text("x" * 100) == "'" + "x" * 100 + "'"
    assert inspect_text("x" * 101) is None
    assert read_inspect("'xxx'... 1 more character") is TRUNCATED
    assert read_inspect("'xxx'... 50 more characters") is TRUNCATED
    # ...and a string whose CONTENT ends that way is not a prefix: the
    # closing quote is what tells the two apart.
    assert read_inspect("'... 50 more characters'") == "... 50 more characters"


def test_the_quote_choice_is_inspects_own():
    assert inspect_text("abc") == "'abc'"
    assert inspect_text("it's") == '"it\'s"'
    assert inspect_text('it\'s "x"') == '`it\'s "x"`'
    assert inspect_text("it's \"x\" `y`") == "'it\\'s \"x\" `y`'"


def test_a_template_hole_rules_the_backtick_out():
    """Measured. A backtick is chosen only where the text holds neither a
    backtick nor a template HOLE -- one around `${y}` would read as an
    interpolation rather than as text -- and a lone `$` is not a hole. A
    writer that stopped at "no backtick" spells a text this recorder never
    writes, and `flow --value` then reports no sighting of a string the
    trace holds."""
    assert inspect_text('it\'s "x" ${y}') == "'it\\'s \"x\" ${y}'"
    assert inspect_text('it\'s "x" $y') == '`it\'s "x" $y`'
    assert inspect_text("${y}") == "'${y}'"
    assert read_inspect("'it\\'s \"x\" ${y}'") == 'it\'s "x" ${y}'


def test_the_escapes_are_the_ones_node_writes_and_the_reader_takes_more():
    r"""Measured (`gen-inspect-table.mjs`): `\b` and `\f` are named, `\v`
    is not -- it is `\x0B`, in uppercase hex, like every other control
    character and like DEL and the C1 block. The reader undoes `\v` all the
    same, because a text that spells it is still unambiguous."""
    assert inspect_text("a\bb\fc\vd") == "'a\\bb\\fc\\x0Bd'"
    assert inspect_text("a\x00b\x1bc\x7fd\x85e") == "'a\\x00b\\x1Bc\\x7Fd\\x85e'"
    assert read_inspect("'a\\x0Bb'") == "a\vb"
    assert read_inspect("'a\\vb'") == "a\vb"
    assert read_inspect("'a\\u00e9b'") == "aéb"
    assert read_inspect("'a\\u{1f600}b'") == "a\U0001f600b"
    # an escape the table does not know is left EXACTLY as it was read
    assert read_inspect("'a\\qb'") == "a\\qb"
    # U+2028, U+00A0 and the rest are printable to node and are not escaped
    assert inspect_text("a b c") == "'a b c'"


def test_a_text_that_spells_no_value_comes_back_as_text():
    for text in ("[Function: foo]", "[class Foo]", "Map(1) { 'a' => 1 }",
                 "{ a: 1, b: 'x' }", "[ 1, 2 ]", "{}",
                 "1970-01-01T00:00:00.000Z", "Foo { x: 1 }", "/a+/g"):
        got = read_inspect(text)
        assert isinstance(got, _DbgText) and got == text


def test_the_bare_words_are_values_and_undefined_is_its_own():
    assert read_inspect("null") is None
    assert read_inspect("true") is True
    assert read_inspect("false") is False
    assert read_inspect("undefined") is UNDEFINED
    assert repr(UNDEFINED) == "<undefined>"
    # equal only to itself: a marker that compared equal to None would let
    # `x == null` answer yes at a site that recorded `undefined`
    assert UNDEFINED != None                                    # noqa: E711
    assert UNDEFINED != UNDEFINED.__class__("<undefined>")


def test_a_bigint_is_an_integer_and_a_number_is_not_a_bigint():
    assert read_inspect("123n") == 123
    assert read_inspect("-123n") == -123
    assert read_inspect("123") == 123
    assert isinstance(read_inspect("123n"), int)


# -- the number port, branch by branch -------------------------------------
#: Every number in the fixture, with the text node printed for it. The three
#: reachable placement branches of `js_number` are each named below as well,
#: so a mutation to one is caught by a test that says which it broke.
def is_number(row) -> bool:
    """A JavaScript NUMBER -- which a BigInt is not. `123n` reads back as
    the int 123 and is spelled `123n` by nobody: `js_number` is the port of
    `Number::toString` and is not asked about it."""
    value = literal_of(row["literal"])
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and not row["text"].endswith("n"))


NUMBERS = [(literal_of(r["literal"]), r["text"]) for r in ROWS
           if is_number(r)]


def test_the_number_rows_are_all_sixteen_of_them():
    """Thirteen from the brief's list (which says twelve and gives
    thirteen: `5 -5 2.5 1e21 1e-7 -0 0.000001 123456789.123 1.5e300 5e-324
    NaN Infinity -Infinity`), plus the three ruling R34 added at the
    2**53 boundary. Every one of them is measured, not asserted."""
    assert len(NUMBERS) == 16, [t for _, t in NUMBERS]


@pytest.mark.parametrize("value,text", NUMBERS, ids=[t for _, t in NUMBERS])
def test_js_number_spells_what_node_spelled(value, text):
    got = js_number(value)
    assert got == text


def test_js_number_places_the_digits_the_way_the_four_branches_say():
    """One case per placement, named. The integral shortcut answers every
    integer BELOW 2**53 (where the exact expansion is already the shortest
    round-trip); from there up the first placement answers, writing the
    shortest digits out with the zeros they do not carry."""
    # k <= n <= 21: an integral value, written out
    assert js_number(float(2 ** 53)) == "9007199254740992"
    assert js_number(float(2 ** 60)) == "1152921504606847000"
    assert js_number(1e20) == "100000000000000000000"
    # 0 < n <= 21: a decimal point inside the digits
    assert js_number(2.5) == "2.5"
    assert js_number(123456789.123) == "123456789.123"
    assert js_number(0.30000000000000004) == "0.30000000000000004"
    # -6 < n <= 0: leading zeros, no exponent
    assert js_number(1e-6) == "0.000001"
    assert js_number(1.5e-6) == "0.0000015"
    # otherwise: the exponent form, at both ends
    assert js_number(1e21) == "1e+21"
    assert js_number(1e-7) == "1e-7"
    assert js_number(1.5e300) == "1.5e+300"
    assert js_number(5e-324) == "5e-324"
    assert js_number(-1e-7) == "-1e-7"
    # ...and the shortcut itself
    assert js_number(2.0) == "2"
    assert js_number(float(2 ** 53 - 1)) == "9007199254740991"
    assert js_number(0.0) == "0"
    assert js_number(-0.0) == "-0"
    assert js_number(-5) == "-5"


def test_an_integer_above_2_53_is_written_as_the_double_that_holds_it():
    r"""Ruling R34, and the divergence it closes. JavaScript has one number
    type: `2**60` is HELD as a double and printed as that double's shortest
    digits, `1152921504606847000`. Writing the exact expansion
    (`1152921504606846976`, which is what `str(int)` gives) spells a text no
    recorder ever wrote, so `flow --value 1152921504606847000` would report
    zero sightings of a capture the trace holds.

    The boundary is exact on both sides: at 2**53 - 1 the expansion IS the
    shortest round-trip and the shortcut answers, and past the double's own
    range there is no number left to print -- JavaScript says `Infinity`,
    and so does this, rather than raising `OverflowError` out of a search.
    """
    assert inspect_text(2 ** 60) == "1152921504606847000"
    assert str(2 ** 60) == "1152921504606846976"          # what it is NOT
    assert inspect_text(2 ** 53) == "9007199254740992"
    assert inspect_text(2 ** 53 - 1) == "9007199254740991"
    assert inspect_text(123456789012345680000) == "123456789012345680000"
    assert inspect_text(-(2 ** 60)) == "-1152921504606847000"
    assert inspect_text(10 ** 400) == "Infinity"
    assert inspect_text(-(10 ** 400)) == "-Infinity"
