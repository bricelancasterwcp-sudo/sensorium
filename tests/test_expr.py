"""The restricted predicate language: what it accepts, and what it refuses.

Two properties are load-bearing and are tested as properties, not as
happy paths:

* the language is CLOSED. Everything outside names, literals, one comparison,
  and/or/not, unary minus, five arithmetic operators and `len(name)` is a
  compile-time error. It never sees a live object -- it reads primitives out
  of a database -- but the boundary is tested as a real boundary anyway,
  because a restricted evaluator that is only restricted by the shape of its
  inputs is one refactor away from being `eval`.

* a name that cannot be evaluated says WHY. "not in scope", "recorded as an
  object", "recorded as a container" and "recorded truncated" send a reader
  to four different fixes, and `watch` prints the difference. Collapsing them
  into one silent False is the failure this whole task exists to prevent.
"""
import pytest

from sensorium.query.expr import (CLIPPED, CONTAINER, NO_LENGTH, NO_VALUE,
                                  NOT_CAPTURED, OUT_OF_SCOPE, TRUNCATED,
                                  EvalError, ExprError, NotCaptured, _Sized,
                                  compile_expr, resolve)


# -- the language it accepts -----------------------------------------------
def test_comparison_and_boolean_ops():
    e = compile_expr("used > 100 and not done")
    assert e.eval({"used": 150, "done": False}) is True
    assert e.eval({"used": 50, "done": False}) is False
    assert e.names == {"used", "done"}


def test_len_on_sized_and_str():
    e = compile_expr("len(buf) >= 3")
    assert e.eval({"buf": _Sized(5)}) is True
    assert e.eval({"buf": "ab"}) is False


def test_arithmetic():
    assert compile_expr("a + b * 2 == 7").eval({"a": 1, "b": 3}) is True
    assert compile_expr("a - b == 1").eval({"a": 4, "b": 3}) is True
    assert compile_expr("a / b == 2").eval({"a": 4, "b": 2}) is True
    assert compile_expr("a % b == 1").eval({"a": 7, "b": 3}) is True


def test_unary_minus_and_or_and_string_literals():
    assert compile_expr("-a < 0").eval({"a": 3}) is True
    assert compile_expr("a > 5 or b > 5").eval({"a": 1, "b": 9}) is True
    assert compile_expr("mode == 'fast'").eval({"mode": "fast"}) is True
    assert compile_expr("x != None").eval({"x": None}) is False


def test_eval_returns_a_real_bool_not_the_operand():
    """`bool`, always: a caller that stored the raw operand would report a
    non-empty string as a hit and then print it as the verdict."""
    got = compile_expr("used").eval({"used": 7})
    assert got is True
    assert compile_expr("used").eval({"used": 0}) is False


def test_names_excludes_the_len_builtin():
    assert compile_expr("len(buf) > len(other)").names == {"buf", "other"}


# -- short-circuit: a determinate answer beats a refusal --------------------
def test_and_short_circuits_past_an_uncaptured_name():
    """`False and <anything>` is False whatever the right side is. Refusing
    there would count a site as "could not check" when the trace decides it,
    which inflates the one number a reader uses to discount a 0-hit run."""
    e = compile_expr("used > 100 and mode == 'fast'")
    assert e.eval({"used": 5}) is False


def test_or_short_circuits_past_an_uncaptured_name():
    e = compile_expr("used > 100 or mode == 'fast'")
    assert e.eval({"used": 500}) is True


def test_short_circuit_stops_only_when_the_answer_is_determined():
    """The mirror of the two above: when the missing half decides it, the
    refusal must still happen."""
    with pytest.raises(NotCaptured):
        compile_expr("used > 100 and mode == 'fast'").eval({"used": 500})
    with pytest.raises(NotCaptured):
        compile_expr("used > 100 or mode == 'fast'").eval({"used": 5})


# -- why a name could not be evaluated -------------------------------------
def test_missing_name_raises_not_captured():
    with pytest.raises(NotCaptured):
        compile_expr("x > 1").eval({})


def test_missing_name_is_out_of_scope_not_uncaptured():
    with pytest.raises(NotCaptured) as ei:
        compile_expr("x > 1").eval({})
    assert ei.value.name == "x" and ei.value.reason == OUT_OF_SCOPE


def test_a_name_bound_to_an_object_is_not_out_of_scope():
    """`e` after `except ValueError as e` IS in scope; what is missing is a
    comparable value. Reporting that as "out of scope" would send a reader to
    refocus, which cannot help: an object has no value to capture."""
    with pytest.raises(NotCaptured) as ei:
        compile_expr("e > 1").eval({"e": NOT_CAPTURED})
    assert ei.value.reason == NO_VALUE


def test_bare_container_name_is_not_captured():
    with pytest.raises(NotCaptured):
        compile_expr("buf == 3").eval({"buf": _Sized(3)})


def test_bare_container_name_points_at_len():
    with pytest.raises(NotCaptured) as ei:
        compile_expr("buf == 3").eval({"buf": _Sized(3)})
    assert ei.value.reason == CONTAINER
    assert "len(buf)" in str(ei.value)


def test_clipped_string_refuses_rather_than_compare_a_prefix():
    """A clipped capture is a PREFIX. Comparing it is a claim about
    characters that were never recorded."""
    for src in ("msg == 'abc'", "len(msg) > 2"):
        with pytest.raises(NotCaptured) as ei:
            compile_expr(src).eval({"msg": TRUNCATED})
        assert ei.value.reason == CLIPPED


def test_len_of_a_value_with_no_length_says_so():
    with pytest.raises(NotCaptured) as ei:
        compile_expr("len(n) > 1").eval({"n": 5})
    assert ei.value.reason == NO_LENGTH


def test_len_of_a_missing_or_object_name_keeps_its_own_reason():
    with pytest.raises(NotCaptured) as ei:
        compile_expr("len(n) > 1").eval({})
    assert ei.value.reason == OUT_OF_SCOPE
    with pytest.raises(NotCaptured) as ei:
        compile_expr("len(n) > 1").eval({"n": NOT_CAPTURED})
    assert ei.value.reason == NO_VALUE


# -- values the predicate cannot be applied to -----------------------------
def test_type_mismatch_is_an_error_not_a_false():
    """`'five' > 3` is not a miss. A site where the predicate could not be
    applied has to be counted apart from a site where it was applied and came
    back False."""
    with pytest.raises(EvalError):
        compile_expr("n > 3").eval({"n": "five"})


def test_division_by_zero_is_an_error_not_a_crash():
    with pytest.raises(EvalError):
        compile_expr("a / b > 1").eval({"a": 1, "b": 0})


def test_eval_error_carries_the_underlying_cause():
    with pytest.raises(EvalError) as ei:
        compile_expr("n > 3").eval({"n": "five"})
    assert isinstance(ei.value.cause, TypeError)
    assert "TypeError" in str(ei.value)


# -- the closed boundary ---------------------------------------------------
@pytest.mark.parametrize("bad", [
    "__import__('os')", "x.attr > 1", "x[0] > 1", "f(x)", "x if y else z",
    "lambda: 1", "x < y < z",
])
def test_disallowed_syntax_rejected_at_compile(bad):
    with pytest.raises(ExprError):
        compile_expr(bad)


@pytest.mark.parametrize("bad", [
    "x ** 2 > 1",                 # power: unbounded cost from two small ints
    "x << 1 > 1", "x | 1 > 1", "x & 1", "x ^ 1", "x // 2 > 1",
    "~x > 1", "+x > 1",           # invert / unary plus
    "x in y", "x not in y", "x is None", "x is not None",
    "[1, 2] == x", "(1, 2) == x", "{'a': 1} == x", "{1, 2} == x",
    "f'{x}'", "x.__class__", "().__class__.__bases__",
    "len(x, y)", "len(1)", "len(x=1)", "len(len(x))", "len",
    "len(x) if y else 1", "sum(x) > 1", "print(x)",
    "[i for i in x]", "x := 1", "*x", "await x", "yield x",
    "", "   ", "x >", "and", "1 2",
])
def test_more_disallowed_syntax_rejected_at_compile(bad):
    with pytest.raises(ExprError):
        compile_expr(bad)


def test_dunder_attribute_is_refused_before_anything_is_evaluated():
    """The refusal is at COMPILE time -- once, on the command line, before a
    single site is read -- not per site and not at eval time."""
    with pytest.raises(ExprError) as ei:
        compile_expr("().__class__.__bases__[0].__subclasses__()")
    assert "unsupported syntax" in str(ei.value) or "call" in str(ei.value)


def test_bare_len_name_is_refused_rather_than_read_from_the_environment():
    """Without this, `len > 1` compiles to a name lookup for "len", which is
    never in a captured environment -- so it would report "not in scope" for
    a builtin and send the reader looking for a variable that never existed.
    """
    with pytest.raises(ExprError) as ei:
        compile_expr("len > 1")
    assert "len(name)" in str(ei.value)


def test_deep_nesting_is_refused_at_compile_not_by_a_recursion_error():
    """`ast.parse` happily builds a tree a thousand levels deep; `_validate`
    and `_eval` both recurse once per node and neither survives it. Measured:
    a thousand `+ x` used to escape as a RecursionError traceback."""
    with pytest.raises(ExprError) as ei:
        compile_expr("x" + " + x" * 1000 + " > 1")
    assert "nests deeper than 50 levels" in str(ei.value)
    for src in ("-" * 3000 + "x > 1", "not " * 400 + "x"):
        with pytest.raises(ExprError):
            compile_expr(src)


def test_parser_stack_overflow_is_refused_not_raised():
    """`_MAX_DEPTH` guards `_validate`, which never runs if there is no tree.
    The parser has its own bounded stack and overflows first: measured, 60000
    unary minus and `not ` x20000 both raise `MemoryError: Parser stack
    overflowed`, and both fit in one argv entry (MAX_ARG_STRLEN is 128 KB),
    so this is reachable from an ordinary command line."""
    for src in ("-" * 60000 + "x > 1", "not " * 20000 + "x"):
        with pytest.raises(ExprError) as ei:
            compile_expr(src)
        assert "too large or too deeply nested for the parser" in str(ei.value)


def test_a_predicate_just_inside_the_depth_cap_still_evaluates():
    """The cap is what GUARANTEES `_eval` cannot recurse to death at a site:
    anything that validates must also evaluate."""
    e = compile_expr("x" + " + x" * 45 + " > 1")
    assert e.eval({"x": 1}) is True
    assert e.eval({"x": 0}) is False


def test_syntax_error_message_names_the_expression_problem():
    with pytest.raises(ExprError) as ei:
        compile_expr("used >")
    assert "not a valid expression" in str(ei.value)


# -- near-miss distance ----------------------------------------------------
def test_margin_for_numeric_ordering():
    e = compile_expr("used > 100")
    assert e.margin({"used": 99}) == 1
    assert compile_expr("a == b").margin({"a": 1, "b": 2}) is None


def test_margin_for_every_ordering_operator_and_none_for_the_rest():
    for op in ("<", "<=", ">", ">="):
        assert compile_expr(f"used {op} 100").margin({"used": 97}) == 3
    for op in ("==", "!="):
        assert compile_expr(f"used {op} 100").margin({"used": 97}) is None
    assert compile_expr("a > 1 and b > 1").margin({"a": 0, "b": 0}) is None
    assert compile_expr("not (a > 1)").margin({"a": 0}) is None


def test_margin_is_none_when_the_comparison_cannot_be_evaluated():
    e = compile_expr("used > 100")
    assert e.margin({}) is None                      # out of scope
    assert e.margin({"used": "many"}) is None        # not a number
    assert e.margin({"used": _Sized(4)}) is None     # a container
    assert compile_expr("a / b > 1").margin({"a": 1, "b": 0}) is None


def test_margin_refuses_bools_which_would_read_as_a_distance_of_one():
    assert compile_expr("flag > 0").margin({"flag": True}) is None


def test_margin_over_arithmetic_and_len():
    assert compile_expr("len(buf) > 100").margin({"buf": _Sized(88)}) == 12
    assert compile_expr("a + b > 10").margin({"a": 4, "b": 5}) == 1


def test_has_boundary_reports_whether_near_misses_are_even_defined():
    assert compile_expr("used > 100").has_boundary is True
    assert compile_expr("a == b").has_boundary is False


# -- resolving captures ----------------------------------------------------
def test_resolve_mapping():
    assert resolve({"k": "num", "v": 3}) == 3
    assert resolve({"k": "none"}) is None
    assert isinstance(resolve({"k": "seq", "type": "list", "len": 4,
                               "oid": 1}), _Sized)
    assert resolve({"k": "obj", "type": "X", "oid": 1,
                    "repr": "<X>"}) is NOT_CAPTURED


def test_resolve_keeps_bools_and_strings():
    assert resolve({"k": "bool", "v": True}) is True
    assert resolve({"k": "str", "v": "ab"}) == "ab"


def test_resolve_marks_a_clipped_string_rather_than_hand_back_the_prefix():
    assert resolve({"k": "str", "v": "abc", "trunc": True}) is TRUNCATED


def test_resolve_of_a_map_is_sized_and_a_depth_capped_one_still_has_its_len():
    """A depth-capped container omits `sample` ENTIRELY. `len` is written
    before any cap is applied, so the length is exact even when `trunc` is
    set -- which is why a truncated container is still usable under len()."""
    capped = {"k": "map", "type": "dict", "len": 9, "oid": 1, "trunc": True}
    assert "sample" not in capped
    got = resolve(capped)
    assert isinstance(got, _Sized) and got.n == 9
    assert compile_expr("len(cfg) > 8").eval({"cfg": got}) is True


def test_resolve_refuses_a_length_the_recorder_could_not_read():
    """A container whose own `__len__` raised is captured with `len: None`.
    That is the absence of a size, not the size 0: `len(bag) > 0` must land
    in `watch`'s not-captured bucket, never come back False as a fact."""
    unread = {"k": "seq", "type": "Evil", "len": None, "oid": 1,
              "unread": ["len"]}
    assert resolve(unread) is NOT_CAPTURED
    with pytest.raises(NotCaptured) as ei:
        compile_expr("len(bag) > 0").eval({"bag": resolve(unread)})
    assert ei.value.reason == NO_VALUE


def test_sized_and_markers_have_readable_reprs():
    assert repr(_Sized(4)) == "<len 4>"
    assert "NOT_CAPTURED" in repr(NOT_CAPTURED)
    assert "TRUNCATED" in repr(TRUNCATED)
