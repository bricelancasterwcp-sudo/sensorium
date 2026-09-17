"""A tool's fields are the parser's own, and a call is rebuilt into argv.

`schema.derive` reads a query command's `add_parser` and answers what an
MCP client must be told: the field names, their JSON types, which are
required, and the sentence each one says. Nothing is retyped. A second,
hand-written table would be correct on the day it was written and wrong
the first time an `add_argument` changed underneath it -- and the error it
produces is the worst kind, a tool table that describes a CLI nobody has.

So the tests below are all run against the REAL modules (`grep_cmd`,
`watch_cmd`, ...), not against fixtures that imitate them: a fixture would
only prove the derivation is self-consistent. The two exceptions are the
module-like objects at the bottom of this header's file, which exist to
exercise the two cases no shipped parser may ever have -- a suppressed
field and an unwritten help.

`test_from_argv_round_trips_every_corpus_question` is the widest of them:
every question the corpus asks, of every recorder, parsed to a call and
rebuilt to argv, with the two parses compared. That is 250 real calls
covering every option the tool has in anger, and it is what stops
`to_argv` from being right about the shapes someone thought to write a
case for.

PRE-REGISTERED MUTATIONS (task 1, step 7), each with the test that catches
it:

* drop the `run` -> `last` default (D5) ->
  `test_grep_derives_run_optional_last_pattern_required_kind_enum_limit_integer`
  and `test_to_argv_rebuilds_grep`.
* drop the `action.required` rule (P2), leaving positionals alone ->
  `test_watch_required_options_are_required`.
* make a true boolean emit `--ignore-moves false` instead of the bare
  flag -> `test_to_argv_true_boolean_is_a_bare_flag_false_is_omitted`.
* drop the `type(v) is bool` guard before the integer check ->
  `test_to_argv_rejects_bad_type_and_enum` (`limit: True` is accepted,
  because Python's `bool` is an `int`).
* drop the empty-help refusal -> `test_empty_help_refuses_to_boot`.
* make `from_argv` keep values equal to the parser's default (P25) ->
  `test_from_argv_drops_defaults`.
* accept `[]` on a required array (drop `_absent`'s array clause) ->
  `test_to_argv_rejects_an_empty_required_array` (the call is neither
  bad nor missing, and argparse refuses the argv it builds).
"""
import argparse

import pytest

pytest.importorskip("yaml")

from corpus.cases import load_cases                        # noqa: E402
from sensorium import cli                                  # noqa: E402
from sensorium.mcp.schema import (Rejection, SchemaError,  # noqa: E402
                                  derive, from_argv, json_schema, parser_for,
                                  to_argv, validate)
from sensorium.query import (diff_cmd, flow_cmd, frame_cmd,  # noqa: E402
                             grep_cmd, redact_cmd, refocus_cmd, watch_cmd)


class _ToyModule:
    """A module-like object: `derive` asks for `add_parser` and nothing
    else, so a class with one static method IS a module to it."""

    @staticmethod
    def add_parser(sub):
        p = sub.add_parser("toy", help="a toy tool",
                           description="A toy tool, for this file alone.")
        p.add_argument("thing", help="the thing")
        p.add_argument("--hidden", default=None, help=argparse.SUPPRESS)
        p.set_defaults(func=lambda args: 0)


class _MuteModule:
    """...and the one no shipped parser may look like: a field whose help
    was never written."""

    @staticmethod
    def add_parser(sub):
        p = sub.add_parser("mute", help="a toy tool that forgot a help",
                           description="A toy tool, for this file alone.")
        p.add_argument("thing", help="the thing")
        p.add_argument("--loose", default=None)
        p.set_defaults(func=lambda args: 0)


# -- derivation -------------------------------------------------------------
def test_grep_derives_run_optional_last_pattern_required_kind_enum_limit_integer():
    schema = json_schema(derive(grep_cmd))
    props = schema["properties"]
    assert props["run"]["default"] == "last"
    assert "run" not in schema["required"]
    assert "pattern" in schema["required"]
    assert props["kind"]["enum"] == ["CALL", "RETURN", "RAISE", "HANDLED",
                                     "LINE"]
    assert props["limit"]["type"] == "integer"
    assert props["limit"]["default"] == 50
    assert schema["additionalProperties"] is False


def test_watch_required_options_are_required():
    """`--at` and `--expr` are `required=True` OPTIONS. A rule that only
    required positionals would call them optional, and a model that
    omitted them would meet argparse's exit 2 for a field the schema said
    it could leave out."""
    schema = json_schema(derive(watch_cmd))
    assert "at" in schema["required"]
    assert "expr" in schema["required"]
    assert "limit" not in schema["required"]


def test_refocus_focus_is_a_required_array_with_min_items_one():
    schema = json_schema(derive(refocus_cmd))
    focus = schema["properties"]["focus"]
    assert focus["type"] == "array"
    assert focus["items"] == {"type": "string"}
    assert focus["minItems"] == 1
    assert "focus" in schema["required"]


def test_diff_run_a_and_run_b_required_and_ignore_moves_boolean():
    schema = json_schema(derive(diff_cmd))
    assert schema["required"] == ["run_a", "run_b"]
    assert schema["properties"]["ignore_moves"]["type"] == "boolean"
    assert schema["properties"]["context"]["default"] == 3


def test_frame_optional_positional_frame_is_not_required():
    """`nargs="?"`: the frame ref may be left out and `--fn` used
    instead."""
    schema = json_schema(derive(frame_cmd))
    assert "frame" in schema["properties"]
    assert "frame" not in schema["required"]
    assert "run" not in schema["required"]        # D5


def test_flow_value_and_object_both_optional_strings():
    """D6: the two are argparse's mutually exclusive group with
    `required=True`, which means EXACTLY ONE -- a rule no JSON Schema
    `required` list can say. Reading the group's flag would mark both
    fields required and refuse every legal call; `required` comes from the
    action alone, and the command's own refusal names the one that is
    missing."""
    schema = json_schema(derive(flow_cmd))
    for name in ("value", "object"):
        assert schema["properties"][name]["type"] == "string"
        assert name not in schema["required"]


def test_suppressed_options_do_not_exist():
    """`help=argparse.SUPPRESS` is how this CLI spells "not for callers"
    (`run --run-id`, `run --refocus-of`): suppressed from `--help`, and
    absent from a tool's fields for the same reason."""
    schema = derive(_ToyModule)
    assert [f.name for f in schema.fields] == ["thing"]
    assert "hidden" not in json_schema(schema)["properties"]


def test_empty_help_refuses_to_boot():
    """A field with no help is a field the caller must guess. The server
    refuses to start rather than shipping a tool table with a blank in
    it, and the refusal names the command and the field."""
    with pytest.raises(SchemaError) as excinfo:
        derive(_MuteModule)
    message = str(excinfo.value)
    assert "mute" in message and "'loose'" in message


# -- a call becomes argv ----------------------------------------------------
def test_to_argv_rebuilds_grep():
    schema = derive(grep_cmd)
    assert to_argv(schema, {"pattern": "compute", "kind": "RETURN"}) == [
        "grep", "last", "compute", "--kind", "RETURN"]


def test_to_argv_true_boolean_is_a_bare_flag_false_is_omitted():
    schema = derive(diff_cmd)
    call = {"run_a": "r1", "run_b": "r2"}
    assert to_argv(schema, {**call, "ignore_moves": True}) == [
        "diff", "r1", "r2", "--ignore-moves"]
    assert to_argv(schema, {**call, "ignore_moves": False}) == [
        "diff", "r1", "r2"]


def test_to_argv_array_repeats_the_option():
    schema = derive(refocus_cmd)
    assert to_argv(schema, {"run": "r1", "focus": ["a", "b"]}) == [
        "refocus", "r1", "--focus", "a", "--focus", "b"]


def test_validate_is_what_to_argv_runs_first():
    """`to_argv` rebuilds and validates; `record` (`mcp.tools`) validates
    without rebuilding, because its argv is not the one these rules
    build. One function, so the two surfaces refuse the same calls in the
    same words rather than drifting apart."""
    ts = derive(grep_cmd)
    assert validate(ts, {"pattern": "x", "kind": "RETURN"}) is None
    with pytest.raises(Rejection) as from_validate:
        validate(ts, {"pattern": "x", "regex": "y"})
    with pytest.raises(Rejection) as from_to_argv:
        to_argv(ts, {"pattern": "x", "regex": "y"})
    assert from_validate.value.reason == from_to_argv.value.reason
    assert from_validate.value.fields == from_to_argv.value.fields
    assert from_validate.value.message == from_to_argv.value.message


def test_to_argv_rejects_unknown_field_naming_all_fields():
    """The refusal is the next call's instructions: a model that guessed
    `regex` is told the six names it may use, so its retry is informed
    rather than another guess."""
    schema = derive(grep_cmd)
    with pytest.raises(Rejection) as excinfo:
        to_argv(schema, {"pattern": "x", "regex": "y"})
    assert excinfo.value.reason == "unknown_fields"
    assert excinfo.value.fields == ("regex",)
    assert excinfo.value.message == (
        "unknown field 'regex' for grep; fields: run, pattern, kind, fn, "
        "after, limit")


def test_to_argv_rejects_bad_type_and_enum():
    schema = derive(grep_cmd)
    for arguments, message in (
        ({"pattern": "x", "limit": "5"},
         "bad value for 'limit' on grep: expected integer"),
        ({"pattern": "x", "limit": True},
         "bad value for 'limit' on grep: expected integer"),
        ({"pattern": "x", "kind": "CALLS"},
         "bad value for 'kind' on grep: expected one of CALL, RETURN, "
         "RAISE, HANDLED, LINE"),
    ):
        with pytest.raises(Rejection) as excinfo:
            to_argv(schema, arguments)
        assert excinfo.value.reason == "bad_fields", arguments
        assert excinfo.value.message == message


def test_to_argv_rejects_missing_required():
    schema = derive(watch_cmd)
    with pytest.raises(Rejection) as excinfo:
        to_argv(schema, {"run": "r1"})
    assert excinfo.value.reason == "missing_fields"
    assert excinfo.value.fields == ("at", "expr")
    assert excinfo.value.message == (
        "missing required field(s) for watch: at, expr")


def test_to_argv_rejects_an_empty_required_array():
    """`--focus` repeated zero times IS `--focus` not given.

    `[]` is a well-typed array and the key IS present, so neither check
    caught it, and `to_argv` built `["refocus", "r1"]` -- argv the CLI
    then refuses with `error: the following arguments are required:
    --focus` and exit 2. `json_schema` says `minItems: 1`, so a client
    that validates locally already refuses this call; `to_argv` must
    refuse the same one, in the words argparse would have used.
    """
    schema = derive(refocus_cmd)
    with pytest.raises(Rejection) as excinfo:
        to_argv(schema, {"run": "r1", "focus": []})
    assert excinfo.value.reason == "missing_fields"
    assert excinfo.value.fields == ("focus",)
    assert excinfo.value.message == (
        "missing required field(s) for refocus: focus")


# -- argv becomes a call ----------------------------------------------------
def test_from_argv_drops_defaults():
    """P25: argparse cannot tell "given as the default" from "defaulted",
    and the answer does not depend on the difference."""
    schema = derive(grep_cmd)
    assert from_argv(schema, ["r1", "x", "--limit", "50"]) == {
        "run": "r1", "pattern": "x"}
    assert from_argv(schema, ["r1", "x", "--limit", "10"]) == {
        "run": "r1", "pattern": "x", "limit": 10}


def _corpus_commands():
    """Every corpus question's command, run ids substituted, `redact`
    dropped -- it is not a tool."""
    commands = []
    for case in load_cases():
        for question in case.questions:
            command = [word.replace("$RUN2", "r2").replace("$RUN", "r1")
                       for word in question["command"]]
            if command[0] == "redact":
                continue
            commands.append((f"{case.name}:{question['id']}", command))
    return commands


CORPUS_COMMANDS = _corpus_commands()


def test_the_corpus_sweep_below_has_something_to_sweep():
    """A guard on the guard: an empty corpus load would leave the round
    trip passing while checking nothing."""
    assert len(CORPUS_COMMANDS) >= 200, len(CORPUS_COMMANDS)
    assert not any(c[0] == "redact" for _, c in CORPUS_COMMANDS)


def test_from_argv_round_trips_every_corpus_question():
    """P23: for every real call the corpus makes, argv -> arguments ->
    argv parses to the same namespace. The comparison is the PARSE, not
    the argv: `diff --ignore-moves r1 r2` and `diff r1 r2 --ignore-moves`
    are the same call, and a rebuild is free to differ there."""
    schemas = {derive(m).command: derive(m) for m in cli._QUERY_MODULES
               if m is not redact_cmd}
    for label, command in CORPUS_COMMANDS:
        schema = schemas[command[0]]
        parser = parser_for(schema)
        rebuilt = to_argv(schema, from_argv(schema, command[1:]))
        assert parser.parse_args(rebuilt[1:]) == parser.parse_args(
            command[1:]), label
        assert rebuilt[0] == command[0], label
