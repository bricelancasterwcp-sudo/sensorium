"""Every tool a model can call says what it is, and so does every field.

An MCP client shows a tool's description and its fields' descriptions and
nothing else: there is no `--help` to type and no epilog to read. So a
field whose `help=` was never written is a field the caller must guess,
and the seventeen that were empty here were exactly the ones a human
reader could infer from the command's shape (`run`, `--limit`, `pattern`)
and a caller reading JSON cannot. This file is the gate that keeps them
written -- a new `add_argument` with no `help=` fails here, before it ever
reaches a tool table.

The parser's `description=` is the other half. `sensorium <cmd> --help`
printed a one-line `help=` and nothing more; the sentence that says what
the answer CLAIMS lives in `description=` now, so the CLI reader and the
tool caller are given the same words from one source (D3) rather than two
that drift.

`redact_cmd` is in `cli._QUERY_MODULES` and is NOT a tool: it writes to
the store rather than answering a question about a trace, so it is
excluded here by identity, not by name, and its own empty `run` help
stays as it is.

`exit.MEANING` is the third string set: the four exit statuses as
sentences, so a caller that receives a status can be told what it means
without the server retyping the convention.
"""
import argparse

import pytest

from sensorium import cli
from sensorium import exit as sensorium_exit
from sensorium.query import redact_cmd

#: Everything in `cli._QUERY_MODULES` that answers a question about a
#: trace -- which is every module there but `redact_cmd`.
TOOL_MODULES = [m for m in cli._QUERY_MODULES if m is not redact_cmd]

QUERY_EPILOG = "exit: 0 yes, 1 no, 2 fix the call, 3 change the recording"


def _parser(module):
    """The command word and the parser `module.add_parser` builds."""
    parser = argparse.ArgumentParser(prog="sensorium")
    sub = parser.add_subparsers(dest="cmd")
    module.add_parser(sub)
    (name, subparser), = sub.choices.items()
    return name, subparser


def _ids(modules):
    return [_parser(m)[0] for m in modules]


def test_the_module_list_is_the_ten_tools_and_not_redact():
    """A guard on the guard: every test below iterates `TOOL_MODULES`, so
    a list that silently emptied -- or that swept `redact` back in --
    would leave them passing while checking nothing."""
    assert len(TOOL_MODULES) == 10, _ids(TOOL_MODULES)
    assert redact_cmd not in TOOL_MODULES
    assert redact_cmd in cli._QUERY_MODULES


@pytest.mark.parametrize("module", TOOL_MODULES, ids=_ids(TOOL_MODULES))
def test_every_tool_field_and_command_has_help(module):
    name, parser = _parser(module)
    assert parser.description, f"{name}: the parser has no description"
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if action.help is argparse.SUPPRESS:
            continue
        assert action.help, f"{name}: field {action.dest!r} has no help"


@pytest.mark.parametrize("module", TOOL_MODULES, ids=_ids(TOOL_MODULES))
def test_epilogs_survive(module):
    """The description is an ADDITION: the exit-status epilog every query
    parser prints is untouched by it (`tests/test_help_epilogs.py` pins
    the same line through `cli.main`; this one pins it on the parser a
    tool table derives from)."""
    name, parser = _parser(module)
    assert QUERY_EPILOG in parser.format_help(), name


def test_meaning_is_the_four_sentences():
    """The four statuses as sentences, keyed by the constants themselves:
    a table keyed by the literal numbers would still pass if a constant
    moved, which is the one thing this convention must not allow."""
    assert sensorium_exit.MEANING == {
        sensorium_exit.ANSWERED: "the trace answered affirmatively",
        sensorium_exit.NEGATIVE: "the trace answered negatively -- no "
                                 "match, no frame, no exception, none",
        sensorium_exit.BAD_CALL: "the call is wrong -- fix the arguments "
                                 "and ask again",
        sensorium_exit.UNSETTLED: "the trace cannot settle it -- change "
                                  "the recording and re-record",
    }
    assert len(sensorium_exit.MEANING) == 4
