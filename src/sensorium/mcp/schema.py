"""A tool's fields, derived from the query command's own argparse parser.

The CLI already says what every query command takes, in the one place
that cannot drift from what the command does: its `add_parser`. This
module reads that parser and answers what an MCP server asks of it --
what fields a tool has (`derive`), how a client is shown them
(`json_schema`), and what argv a call becomes (`to_argv`, and
`from_argv` back again). A hand-written second table would be right on
the day it was written and wrong the first time an `add_argument`
changed, and the error it produces is the worst kind: a tool table
describing a CLI nobody has.

WHAT THE PARSER SAYS, AND WHAT THIS MAKES OF IT
-----------------------------------------------
| the action                  | the field                          |
|-----------------------------|------------------------------------|
| `argparse._HelpAction`      | skipped -- `-h` is not a field     |
| `dest`                      | the field's name                   |
| `_StoreTrueAction`          | boolean                            |
| `_AppendAction`             | array of string                    |
| `choices=`                  | enum of those choices              |
| `type=int`                  | integer                            |
| anything else               | string                             |
| positional, `nargs=None`    | required                           |
| positional, `nargs="?"`     | optional                           |
| `action.required` (P2)      | required; an array also `minItems` |
| positional named `run` (D5) | optional, default `last`           |
| `help=argparse.SUPPRESS`    | no field at all                    |
| `help=` empty or None       | `SchemaError`: refuse to boot      |
| a default not None/[]/False | the field's `"default"`            |

P2 is what a positional-only reading misses: `watch --at`, `watch
--expr` and `refocus --focus` are required OPTIONS, and a model that
omitted one because the schema called it optional would meet argparse's
exit 2 for a field it was told it could leave out.

D6 is the opposite case. `flow --value` and `--object` sit in a mutually
exclusive group with `required=True`, which means EXACTLY ONE -- a rule
no JSON Schema `required` list can state. `required` is read from the
ACTION alone, never from the group, so both are optional here and `flow`
itself refuses by name when neither is given.

D5 is `run`. Every query command takes one and `last` is what a caller
almost always means, so a default here spares it a `runs` call before
every question. It lives in the schema and in `to_argv` and never in the
parser: the CLI's own `run` positional is still required.

`json_schema` sets `"additionalProperties": false` so a client that
validates locally refuses exactly what `to_argv` refuses -- a field this
tool does not have is worth catching before the call, not after.

`from_argv` is the inverse (P25): argv WITHOUT the command word becomes
`{dest: value}`, dropping `None`, `[]`, `False` and any value equal to
the parser's own default, which argparse cannot tell from a defaulted
one. `tests/test_mcp_schema.py` pins the round trip over every corpus
question, compared as parses.
"""
from __future__ import annotations

import argparse
import contextlib
import io
from dataclasses import dataclass, field as _dataclass_field

#: D5: what `run` means when a call leaves it out.
RUN_DEFAULT = "last"

#: The JSON type each field kind is shown as. An enum is a string with a
#: closed set; an array's items are strings throughout this CLI.
_JSON_TYPE = {"string": "string", "integer": "integer",
              "boolean": "boolean", "array": "array", "enum": "string"}

#: ...and what a refusal calls it when the value is of the wrong one.
_EXPECTED = {"string": "string", "integer": "integer",
             "boolean": "boolean", "array": "array of string"}


class SchemaError(Exception):
    """A parser this server cannot describe: raised while deriving,
    never while answering. The server refuses to boot rather than ship a
    tool whose field says nothing."""


class Rejection(Exception):
    """A call that will not be made, and the reason a caller can act on."""

    def __init__(self, reason: str, fields, message: str) -> None:
        super().__init__(message)
        #: "unknown_fields" | "bad_fields" | "missing_fields"
        self.reason = reason
        #: The offending field names, all of them, in schema order.
        self.fields = tuple(fields)
        self.message = message


@dataclass(frozen=True)
class Field:
    name: str
    kind: str                     # string|integer|boolean|array|enum
    required: bool
    description: str
    default: object = None
    enum: tuple[str, ...] = ()
    positional: bool = False
    option: str | None = None     # "--kind"


@dataclass(frozen=True)
class ToolSchema:
    command: str                  # the argv word: "grep"
    fields: tuple[Field, ...]     # positionals in parser order, then options
    help: str                     # add_parser's help=
    description: str              # ...and its description=
    #: The parser the fields were read off, so `from_argv` parses by the
    #: very rules the CLI applies. Reached through `parser_for`, and out
    #: of `==`: two schemas are equal when they say the same thing.
    parser: argparse.ArgumentParser = _dataclass_field(repr=False,
                                                       compare=False)


# -- derivation -------------------------------------------------------------
def derive(module) -> ToolSchema:
    """The tool schema for a query module -- anything with `add_parser`.

    The parser is built here rather than taken from `cli.main`'s:
    deriving must not depend on a live CLI."""
    parser = argparse.ArgumentParser(prog="sensorium", exit_on_error=False)
    sub = parser.add_subparsers(dest="cmd")
    module.add_parser(sub)
    (command, subparser), = sub.choices.items()
    description = subparser.description or ""
    if not description:
        raise SchemaError(f"{command}: the command has no description; "
                          "the server refuses to boot")
    positionals, options = [], []
    for action in subparser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if action.help is argparse.SUPPRESS:
            continue
        if not action.help:
            raise SchemaError(f"{command}: field {action.dest!r} has no "
                              "help; the server refuses to boot")
        field = _field(action)
        (positionals if field.positional else options).append(field)
    return ToolSchema(command, tuple(positionals + options),
                      _command_help(sub, command), description, subparser)


def parser_for(ts: ToolSchema) -> argparse.ArgumentParser:
    """The subparser `derive` read, for `from_argv` and for tests."""
    return ts.parser


def _command_help(sub, command: str) -> str:
    """`add_parser`'s `help=`, which argparse keeps on the pseudo-action
    it made for the choice rather than on the subparser itself."""
    for choice in sub._choices_actions:
        if choice.dest == command and choice.help:
            return choice.help
    raise SchemaError(f"{command}: the command has no help; the server "
                      "refuses to boot")


def _field(action) -> Field:
    positional = not action.option_strings
    default = action.default
    if default is None or default == [] or default is False:
        default = None
    if positional:
        required = action.nargs is None
    else:
        required = bool(action.required)                       # P2
    if positional and action.dest == "run":                    # D5
        required, default = False, RUN_DEFAULT
    return Field(name=action.dest, kind=_kind(action), required=required,
                 description=action.help, default=default,
                 enum=tuple(action.choices) if action.choices else (),
                 positional=positional,
                 option=None if positional else action.option_strings[0])


def _kind(action) -> str:
    if isinstance(action, argparse._StoreTrueAction):
        return "boolean"
    if isinstance(action, argparse._AppendAction):
        return "array"
    if action.choices:
        return "enum"
    if action.type is int:
        return "integer"
    return "string"


# -- what a client is shown -------------------------------------------------
def json_schema(ts: ToolSchema) -> dict:
    return {
        "type": "object",
        "properties": {f.name: _property(f) for f in ts.fields},
        "required": [f.name for f in ts.fields if f.required],
        "additionalProperties": False,
    }


def _property(f: Field) -> dict:
    prop: dict = {"type": _JSON_TYPE[f.kind]}
    if f.kind == "enum":
        prop["enum"] = list(f.enum)
    if f.kind == "array":
        prop["items"] = {"type": "string"}
        if f.required:
            prop["minItems"] = 1
    prop["description"] = f.description
    if f.default is not None:
        prop["default"] = f.default
    return prop


# -- a call becomes argv ----------------------------------------------------
def validate(ts: ToolSchema, arguments: dict) -> None:
    """Raise the `Rejection` this call has earned, or return.

    Whole and in this order: a caller told of one bad field at a time
    needs one round trip per mistake, and a missing field reported ahead
    of a misspelt one sends the retry after the wrong thing. Public
    because `record` (`mcp.tools`) is refused by these rules and then
    builds argv of its own -- `run --focus … -- <command>` is not the
    shape `to_argv` makes -- and two copies of a refusal drift.
    """
    by_name = {f.name: f for f in ts.fields}
    _reject_unknown(ts, arguments, by_name)
    _reject_bad_values(ts, arguments, by_name)
    _reject_missing(ts, arguments)


def to_argv(ts: ToolSchema, arguments: dict) -> list[str]:
    """`[command, *options, "--", *positionals]` for a validated call.

    THE SHAPE IS THE ESCAPE A TOOL CALLER DOES NOT HAVE. Emitted as two
    words (`["--fn", value]`) with the positionals bare, ANY value
    beginning with `-` was read by the child's argparse as an option:
    `grep {"pattern": "-x"}` came back *the following arguments are
    required: pattern*, naming the one field the model HAD supplied.
    A shell user types `sensorium grep last -- -x`; a model has no
    field and no spelling to reach for, and `-1` happened to work
    (argparse matches negative numbers), which made the dead end look
    arbitrary rather than structural.

    So: `--name=value`, which cannot be mistaken for a flag-plus-value,
    and one `--` before the positional block, which ends option parsing
    for good. The `--` is omitted when there are no positionals (`runs`
    has no fields at all) rather than emitted as a word with nothing
    after it. `record`'s argv is `tools.command_argv`'s, not this one:
    its `--` separates the TARGET's argv and means something else.
    """
    validate(ts, arguments)
    options: list[str] = []
    for f in ts.fields:
        if f.positional or f.name not in arguments:
            continue
        value = arguments[f.name]
        if f.kind == "boolean":
            if value:
                options.append(f.option)
        elif f.kind == "array":
            options.extend(f"{f.option}={item}" for item in value)
        else:
            options.append(f"{f.option}={_word(f, value)}")
    positionals: list[str] = []
    for f in ts.fields:
        if not f.positional:
            continue
        if f.name in arguments:
            positionals.append(_word(f, arguments[f.name]))
        elif f.default is not None:
            positionals.append(str(f.default))                 # D5
    if not positionals:
        return [ts.command, *options]
    return [ts.command, *options, "--", *positionals]


def _word(f: Field, value) -> str:
    return str(value) if f.kind == "integer" else value


def _reject_unknown(ts: ToolSchema, arguments: dict, by_name: dict) -> None:
    unknown = [name for name in arguments if name not in by_name]
    if not unknown:
        return
    raise Rejection(
        "unknown_fields", unknown,
        f"unknown field{'s' if len(unknown) > 1 else ''} "
        f"{', '.join(repr(n) for n in unknown)} for {ts.command}; fields: "
        f"{', '.join(f.name for f in ts.fields)}")


def _reject_bad_values(ts: ToolSchema, arguments: dict,
                       by_name: dict) -> None:
    bad, clauses = [], []
    for name, value in arguments.items():
        f = by_name[name]
        if _well_typed(f, value):
            continue
        bad.append(name)
        expected = ("one of " + ", ".join(f.enum) if f.kind == "enum"
                    else _EXPECTED[f.kind])
        clauses.append(f"bad value for {name!r} on {ts.command}: "
                       f"expected {expected}")
    if bad:
        raise Rejection("bad_fields", bad, "; ".join(clauses))


def _well_typed(f: Field, value) -> bool:
    # `type(value) is bool` before the integer check, always: Python's
    # `bool` IS an `int`, so `isinstance(True, int)` would accept `true`
    # for `--limit` and hand argparse the word "True".
    if f.kind == "boolean":
        return type(value) is bool
    if f.kind == "integer":
        return type(value) is not bool and isinstance(value, int)
    if f.kind == "array":
        return (isinstance(value, list)
                and all(isinstance(item, str) for item in value))
    if f.kind == "enum":
        return isinstance(value, str) and value in f.enum
    return isinstance(value, str)


def _reject_missing(ts: ToolSchema, arguments: dict) -> None:
    missing = [f.name for f in ts.fields
               if f.required and _absent(f, arguments)]
    if missing:
        raise Rejection("missing_fields", missing,
                        f"missing required field(s) for {ts.command}: "
                        f"{', '.join(missing)}")


def _absent(f: Field, arguments: dict) -> bool:
    """...and `--focus: []` is absent too, not an empty one.

    An `_AppendAction` repeated zero times IS the flag not given: argparse
    would answer `error: the following arguments are required: --focus`,
    and `json_schema` already says `minItems: 1`. Counting `[]` as present
    let `to_argv` build argv the CLI then refused with exit 2 -- the one
    thing this validation exists to prevent -- and reported as "missing"
    is what argparse itself would have called it.
    """
    if f.name not in arguments:
        return True
    return f.kind == "array" and arguments[f.name] == []


# -- argv becomes a call ----------------------------------------------------
def from_argv(ts: ToolSchema, argv: list[str]) -> dict:
    """`{dest: value}` for argv WITHOUT the command word (P25).

    Argparse's own parse, so what the CLI would refuse is refused here
    in the same words -- as a `Rejection`, never as the process exit
    argparse reaches for on a command line."""
    parser = parser_for(ts)
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            namespace = parser.parse_args(list(argv))
    except (argparse.ArgumentError, SystemExit) as exc:
        raise Rejection("bad_fields", (),
                        stderr.getvalue().strip() or str(exc)) from None
    parsed = vars(namespace)
    defaults = {a.dest: a.default for a in parser._actions}
    call = {}
    for f in ts.fields:
        if f.name not in parsed:
            continue
        value = parsed[f.name]
        if value is None or value == [] or value is False:
            continue
        if f.name in defaults and value == defaults[f.name]:
            continue
        call[f.name] = value
    return call
