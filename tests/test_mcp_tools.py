"""Which commands are tools, what they say, and what a call becomes.

`schema` derives a tool's fields from its command's parser; `tools` is
the table those tools sit in. The table is EXPLICIT (P1): a command is a
query tool, an executing tool, or not a tool at all, and someone says
which. `test_every_query_module_is_placed` closes the three tuples over
`cli._QUERY_MODULES`, so a command added to the CLI fails this suite
until it is placed -- the alternative, "every command in the list is a
tool", would have shipped `redact` as an MCP tool the day it was
written, and a surface that can execute is the wrong place for a new
entry to arrive silently.

The tests below run against the REAL modules and the REAL `run` parser,
never a fixture: the one thing worth checking here is that the table
still describes the CLI this repository has.

PRE-REGISTERED MUTATIONS (task 2, step 5), each with the test that
catches it:

* add `redact_cmd` to `QUERY_MODULES` ->
  `test_table_without_flag_is_the_nine_in_order`. The closure test still
  passes -- `redact` in two tuples at once is still a placed command --
  so the table tests are the ones that catch it, and what they meet is
  `derive`'s boot refusal: `redact`'s parser has no `description=`,
  because it was never meant to be described to anyone.
* drop `record` from the flagged table ->
  `test_table_with_flag_adds_refocus_then_record`.
* retype `focus`'s description instead of reading `_add_run_parser`'s
  `help` -> `test_record_schema_carries_every_non_suppressed_run_option`.
* put `cwd` into argv -> `test_command_argv_for_record`.
* reorder `NARROWING` (`limit` before `depth`) ->
  `test_narrowing_fields` (P28: `tree`'s trailer reads `depth, limit,
  around`).
* drop `_record_schema`'s boot refusals ->
  `test_record_refuses_to_boot_on_a_blank_flag_help` and
  `test_record_refuses_to_boot_on_a_blank_description`.
* re-add `outputSchema` to `to_wire` (`wire["outputSchema"] = {...}`) ->
  `test_to_wire_has_title_only_when_structured_and_never_output_schema`
  (task 12, R18). A declared output schema is what invites a client to
  send structured content, and the deploy target shows the model that
  INSTEAD of the answer.
"""
import argparse

import pytest

from sensorium import cli
from sensorium.mcp import schema, tools
from sensorium.query import redact_cmd, refocus_cmd

#: The nine, in the order a client is shown them: the two that open a
#: trace, then the four that read one, then the three that compare and
#: check.
THE_NINE = ["runs", "info", "tree", "frame", "grep", "exceptions", "flow",
            "watch", "diff"]


def _run_parser():
    """`_add_run_parser`'s own subparsers object and its `run` choice --
    built here the way `derive` builds one, so this test reads the same
    parser `RECORD` was read off without either depending on a live
    CLI."""
    parser = argparse.ArgumentParser(prog="sensorium", exit_on_error=False)
    sub = parser.add_subparsers(dest="cmd")
    cli._add_run_parser(sub)
    return sub, sub.choices["run"]


# -- the tables -------------------------------------------------------------
def test_every_query_module_is_placed():
    """P1: the closure. A command added to `cli._QUERY_MODULES` is a
    query tool, an executing tool, or not a tool, and this fails until
    someone says which."""
    assert set(cli._QUERY_MODULES) == (set(tools.QUERY_MODULES)
                                       | set(tools.EXECUTE_MODULES)
                                       | set(tools.NOT_TOOLS))
    assert tools.EXECUTE_MODULES == (refocus_cmd,)
    assert tools.NOT_TOOLS == (redact_cmd,)


def test_table_without_flag_is_the_nine_in_order():
    """`redact` is a command and not a tool: it rewrites a stored trace,
    which is not a question, and no client is offered it."""
    assert list(tools.table(allow_run=False)) == THE_NINE
    assert all(not tool.executes
               for tool in tools.table(allow_run=False).values())


def test_table_with_flag_adds_refocus_then_record():
    """The gate adds exactly two, at the end, and `record` is the CLI's
    `run` under the name D2 gave it."""
    table = tools.table(allow_run=True)
    assert list(table) == THE_NINE + ["refocus", "record"]
    assert table["record"].schema.command == "run"
    assert table["record"].executes and table["refocus"].executes


# -- `record`, the one hand-written schema ----------------------------------
def test_record_schema_carries_every_non_suppressed_run_option():
    """D7: a flag added to `sensorium run` fails this until `record`
    carries it, and every sentence it says is the parser's own -- a
    retyped one is right on the day it is typed."""
    sub, p = _run_parser()
    actions = {a.dest: a for a in p._actions
               if a.option_strings
               and not isinstance(a, argparse._HelpAction)
               and a.help is not argparse.SUPPRESS}
    assert set(actions) == {"focus", "include", "exclude", "window"}

    by_name = {f.name: f for f in tools.RECORD.fields}
    assert set(actions) <= set(by_name)
    for dest, action in actions.items():
        assert by_name[dest].description == action.help, dest
        assert by_name[dest].option == action.option_strings[0], dest
    for name in ("command", "cwd", "python"):
        assert by_name[name].option is None, name

    (choice,) = [c for c in sub._choices_actions if c.dest == "run"]
    assert tools.RECORD.help == choice.help
    assert tools.RECORD.description == p.description
    assert tools.RECORD.command == "run"

    js = schema.json_schema(tools.RECORD)
    assert list(js["properties"]) == ["command", "focus", "include",
                                      "exclude", "window", "cwd", "python"]
    assert js["required"] == ["command"]
    assert js["properties"]["command"]["type"] == "array"
    assert js["properties"]["command"]["minItems"] == 1
    for name in ("cwd", "python"):
        assert js["properties"][name]["type"] == "string"
        assert name not in js["required"]
        assert js["properties"][name]["description"]


def _blanking(**edit):
    """`cli._add_run_parser`, with one thing it says taken away.

    A `help=` or a `description=` deleted upstream is the failure these
    two tests exist for, and the only honest way to stage it is to
    delete one -- a fixture parser of our own would prove the guard
    works on a parser nobody ships."""
    original = cli._add_run_parser

    def blanked(sub):
        original(sub)
        p = sub.choices["run"]
        for dest, value in edit.items():
            if dest == "description":
                p.description = value
                continue
            (action,) = [a for a in p._actions if a.dest == dest]
            action.help = value
    return blanked


def test_record_refuses_to_boot_on_a_blank_flag_help(monkeypatch):
    """`RECORD` is hand-written, which is exactly why it must not be the
    one schema that can ship a field saying nothing: without this,
    `record`'s `inputSchema` reaches the model as `"description": null`
    for a flag it is being asked to use."""
    monkeypatch.setattr(cli, "_add_run_parser", _blanking(focus=None))
    with pytest.raises(schema.SchemaError) as excinfo:
        tools._record_schema()
    assert str(excinfo.value) == (
        "run: field 'focus' has no help; the server refuses to boot")


def test_record_refuses_to_boot_on_a_blank_description(monkeypatch):
    """...and the same for the sentence the tool itself says, in the
    words `derive` uses for every other command."""
    monkeypatch.setattr(cli, "_add_run_parser", _blanking(description=""))
    with pytest.raises(schema.SchemaError) as excinfo:
        tools._record_schema()
    assert str(excinfo.value) == (
        "run: the command has no description; the server refuses to boot")


def test_record_fields_the_run_parser_does_not_have_say_what_they_are():
    """`command`, `cwd` and `python` are the three sentences nobody can
    read off the parser: `target` is a `REMAINDER` with no help, and the
    other two are the child runner's, not argv's."""
    by_name = {f.name: f for f in tools.RECORD.fields}
    assert by_name["command"].description == (
        "the program to record, as its own argv: a .py file, `-m` and a "
        "module, or a console script, followed by its arguments; never "
        "`python`")
    assert by_name["cwd"].description == (
        "directory to record from; only code under it is recorded; "
        "default the server's")
    assert by_name["python"].description == (
        "interpreter to record under; must import sensorium and the "
        "program's dependencies; default the server's own")


# -- what a client is shown -------------------------------------------------
def test_descriptions_are_help_then_sentence():
    """D3: the two strings `sensorium <cmd> --help` prints, joined by a
    full stop -- one source, two surfaces."""
    table = tools.table(allow_run=True)
    assert table["grep"].description == (
        "search events by name or value. Every CALL, RETURN, RAISE, "
        "HANDLED or LINE event whose name or rendered value contains the "
        "pattern; `--after` resumes from an event id a previous answer "
        "showed.")
    assert table["record"].description == (
        "record one execution. Runs the command under the recorder from "
        "`cwd` and writes one trace; only code under `cwd` is recorded; "
        "the command is a .py file, a `-m` module or a console script, "
        "never `python` itself.")


def test_annotations_by_kind():
    """D9. `record` and `refocus` run a program that may do anything;
    the other nine read a file that is already written."""
    assert tools.ANNOTATIONS_QUERY == {"readOnlyHint": True,
                                       "destructiveHint": False,
                                       "idempotentHint": True,
                                       "openWorldHint": False}
    assert tools.ANNOTATIONS_EXECUTE == {"readOnlyHint": False,
                                         "destructiveHint": False,
                                         "idempotentHint": False,
                                         "openWorldHint": True}
    table = tools.table(allow_run=True)
    for name in THE_NINE:
        assert table[name].annotations == tools.ANNOTATIONS_QUERY, name
    for name in ("refocus", "record"):
        assert table[name].annotations == tools.ANNOTATIONS_EXECUTE, name


def test_to_wire_has_title_only_when_structured_and_never_output_schema():
    """`Tool.title` arrived in 2025-06-18, so a 2025-03-26 client is not
    sent one: an unknown key is a validation failure in some clients and
    noise in the rest. NO revision is sent an `outputSchema` (R18): a
    declared one invites the structured content the deploy target shows
    the model INSTEAD of the answer, and the exit is the header line.
    """
    tool = tools.table(allow_run=False)["grep"]
    old = tools.to_wire(tool, structured=False)
    assert list(old) == ["name", "description", "inputSchema", "annotations"]
    assert old["name"] == "grep"
    assert old["description"] == tool.description
    assert old["inputSchema"] == schema.json_schema(tool.schema)
    assert old["annotations"] == tools.ANNOTATIONS_QUERY

    new = tools.to_wire(tool, structured=True)
    assert list(new) == ["name", "description", "inputSchema", "annotations",
                         "title"]
    assert new["title"] == "grep"
    assert not hasattr(tools, "OUTPUT_SCHEMA")
    for wire in (old, new):
        assert "outputSchema" not in wire


def test_narrowing_fields():
    """P28: `depth` before `limit`, so `tree`'s trailer reads `narrow
    with: depth, limit, around` -- the order §5.1's example and the
    locked H3 row both say."""
    table = tools.table(allow_run=False)
    assert tools.narrowing_fields(table["tree"]) == ("depth", "limit",
                                                     "around")
    assert tools.narrowing_fields(table["grep"]) == ("limit", "after", "fn",
                                                     "kind")
    assert tools.narrowing_fields(table["runs"]) == ()


# -- a call becomes argv ----------------------------------------------------
def test_command_argv_for_record():
    """`run [--focus ...] [--window ...] -- <command...>`, and the two
    fields the CLI has no flag for ride alongside as extras."""
    record = tools.table(allow_run=True)["record"]
    assert tools.command_argv(record, {"command": ["main.py", "-x"],
                                       "focus": ["main:handle"],
                                       "cwd": "/w"}) == (
        ["run", "--focus", "main:handle", "--", "main.py", "-x"],
        {"cwd": "/w", "python": None})


def test_command_argv_for_record_repeats_arrays_in_field_order():
    """...and `--` separates them from the target's own argv, so a
    target flag the recorder also has (`-m`, `--include`) is the
    target's."""
    record = tools.table(allow_run=True)["record"]
    argv, extras = tools.command_argv(record, {
        "command": ["-m", "pytest", "--include", "x"],
        "focus": ["a", "b"], "include": ["src/*"], "exclude": ["tests/*"],
        "window": "main:handle", "python": "/v/bin/python"})
    assert argv == ["run", "--focus", "a", "--focus", "b",
                    "--include", "src/*", "--exclude", "tests/*",
                    "--window", "main:handle",
                    "--", "-m", "pytest", "--include", "x"]
    assert extras == {"cwd": None, "python": "/v/bin/python"}


def test_command_argv_for_record_refuses_by_the_same_rules():
    """R6: `record` builds argv of its own but is refused by
    `schema.validate`, so an unknown field is named the same way here as
    on every other tool, and a missing `command` is `missing_fields`
    rather than a `KeyError`."""
    record = tools.table(allow_run=True)["record"]
    with pytest.raises(schema.Rejection) as unknown:
        tools.command_argv(record, {"command": ["main.py"], "cwdd": "/w"})
    assert unknown.value.reason == "unknown_fields"
    assert unknown.value.fields == ("cwdd",)
    assert "command, focus, include, exclude, window, cwd, python" in (
        unknown.value.message)

    with pytest.raises(schema.Rejection) as missing:
        tools.command_argv(record, {"focus": ["a"]})
    assert missing.value.reason == "missing_fields"
    assert missing.value.fields == ("command",)


def test_command_argv_for_a_query_has_no_extras():
    """Only `record` has anything the child runner must be told that
    argv cannot carry."""
    grep = tools.table(allow_run=False)["grep"]
    assert tools.command_argv(grep, {"pattern": "compute"}) == (
        ["grep", "last", "compute"], {})
    refocus = tools.table(allow_run=True)["refocus"]
    assert tools.command_argv(refocus, {"run": "r1", "focus": ["a"]}) == (
        ["refocus", "r1", "--focus", "a"], {})
