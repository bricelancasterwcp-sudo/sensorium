"""The tool table: which commands are tools, and what a call becomes.

`schema` answers what a tool's fields are by reading its command's own
parser. This module answers the questions no parser can: which of the
CLI's commands a client is offered at all, which of those may execute,
what each tool is called, and what sentence it says about itself.

THE TABLES ARE EXPLICIT (P1). `QUERY_MODULES` names nine; `refocus` is
the one query that runs a program, so it appears only under
`--allow-run`; `redact` rewrites a stored trace, which is not a
question anyone asks a debugger, so it is in `NOT_TOOLS`. Deriving the
table from `cli._QUERY_MODULES` instead would have made `redact` a tool
the day it was written, and the NEXT command a tool the day IT is
written -- a silent default a surface with two executing tools cannot
afford. Field derivation stays automatic; only placement is by hand,
and `test_every_query_module_is_placed` fails until one is placed.

`record` IS THE CLI'S `run` (D2). As a tool name `run` reads as
"execute" in every client's prior and collides with the `run` FIELD
every query carries; `record` is the README's first verb. It is also
the one schema `derive` cannot build (D7): `run`'s target is an
argparse `REMAINDER` with no help, two of its flags are suppressed, and
two of its fields -- `cwd` and `python` -- are not argv at all but
instructions to whoever spawns the child. So `RECORD` is written out
here, with every sentence it can READ read off `_add_run_parser`: a
retyped help is right on the day it is typed and wrong the first time
the flag's own wording improves.

`command_argv` is the seam to the child runner: `(argv, extras)`, where
`extras` is empty for every tool but `record` and holds exactly the two
fields that must never reach argv.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from sensorium import cli
from sensorium.mcp import schema
from sensorium.mcp.schema import Field, ToolSchema
from sensorium.query import (diff_cmd, exceptions_cmd, flow_cmd, frame_cmd,
                             grep_cmd, info_cmd, redact_cmd, refocus_cmd,
                             runs_cmd, tree_cmd, watch_cmd)

#: The nine a client is always offered, in the order it is shown them.
QUERY_MODULES = (runs_cmd, info_cmd, tree_cmd, frame_cmd, grep_cmd,
                 exceptions_cmd, flow_cmd, watch_cmd, diff_cmd)

#: ...and the one query that re-runs the recorded command: offered only
#: under `--allow-run`.
EXECUTE_MODULES = (refocus_cmd,)

#: A command, deliberately not a tool: `redact` rewrites a stored trace.
NOT_TOOLS = (redact_cmd,)

#: The fields a capped answer suggests narrowing by, in the order the
#: trailer lists them (P28: `depth` before `limit`, so `tree` reads
#: "narrow with: depth, limit, around").
NARROWING = ("depth", "limit", "after", "around", "context", "misses", "fn",
             "kind")

#: D9. Nine tools read a file that is already written...
ANNOTATIONS_QUERY = {"readOnlyHint": True, "destructiveHint": False,
                     "idempotentHint": True, "openWorldHint": False}

#: ...and two run a program that may do anything.
ANNOTATIONS_EXECUTE = {"readOnlyHint": False, "destructiveHint": False,
                       "idempotentHint": False, "openWorldHint": True}

#: Every tool answers the same structured content: the child's exit
#: status, `null` when it was killed before it had one.
OUTPUT_SCHEMA = {"type": "object",
                 "properties": {"exit": {"type": ["integer", "null"]}},
                 "required": ["exit"]}

#: The three sentences `_add_run_parser` cannot supply: `target` is a
#: `REMAINDER` with no help, and the other two are the child's process.
_COMMAND_HELP = ("the program to record, as its own argv: a .py file, `-m` "
                 "and a module, or a console script, followed by its "
                 "arguments; never `python`")
_CWD_HELP = ("directory to record from; only code under it is recorded; "
             "default the server's")
_PYTHON_HELP = ("interpreter to record under; must import sensorium and the "
                "program's dependencies; default the server's own")


def _record_schema() -> ToolSchema:
    """`record`'s schema, read off `sensorium run`'s parser (D7).

    Built the way `derive` builds one -- a private subparsers object --
    so the read does not depend on a live CLI, and REFUSED the way
    `derive` refuses. A hand-written table must not be the one that can
    ship a field saying nothing: a `help=` deleted from
    `_add_run_parser` would otherwise reach a client as `"description":
    null`, and the three sentences below would be all `record` said.
    """
    parser = argparse.ArgumentParser(prog="sensorium", exit_on_error=False)
    sub = parser.add_subparsers(dest="cmd")
    cli._add_run_parser(sub)
    p = sub.choices["run"]
    said = {a.dest: a.help for a in p._actions}
    flag = {a.dest: a.option_strings[0] for a in p._actions
            if a.option_strings}
    spec = (("focus", "array"), ("include", "array"),
            ("exclude", "array"), ("window", "string"))
    if not p.description:
        raise schema.SchemaError("run: the command has no description; "
                                 "the server refuses to boot")
    for name, _ in spec:
        if not said.get(name):
            raise schema.SchemaError(f"run: field {name!r} has no help; "
                                     "the server refuses to boot")
    flags = [Field(name=name, kind=kind, required=False,
                   description=said[name], option=flag[name])
             for name, kind in spec]
    fields = (
        Field(name="command", kind="array", required=True,
              description=_COMMAND_HELP, positional=True),
        *flags,
        # The two with no `option`: `command_argv` hands them to the
        # child runner and never to argv.
        Field(name="cwd", kind="string", required=False,
              description=_CWD_HELP),
        Field(name="python", kind="string", required=False,
              description=_PYTHON_HELP),
    )
    # `_command_help` rather than a second copy of the same four lines:
    # a `run` whose help went missing must refuse to boot in the words
    # every other command's would.
    return ToolSchema("run", fields, schema._command_help(sub, "run"),
                      p.description, p)


#: The CLI's `run`, as the tool `record`.
RECORD = _record_schema()


@dataclass(frozen=True)
class Tool:
    """One entry of the table: what a client is offered, and whether
    answering it starts a program."""

    name: str
    schema: ToolSchema
    executes: bool

    @property
    def description(self) -> str:
        """D3: the parser's `help=`, a full stop, and its `description=`
        -- the same two strings `sensorium <cmd> --help` prints."""
        return f"{self.schema.help}. {self.schema.description}"

    @property
    def annotations(self) -> dict:
        return dict(ANNOTATIONS_EXECUTE if self.executes
                    else ANNOTATIONS_QUERY)


def table(allow_run: bool) -> dict[str, Tool]:
    """The tools this server offers, in the order it lists them.

    `schema.SchemaError` propagates: a command whose field lost its help
    is a boot refusal, not a tool with a blank in it."""
    tools = {}
    for module in QUERY_MODULES:
        ts = schema.derive(module)
        tools[ts.command] = Tool(ts.command, ts, executes=False)
    if allow_run:
        for module in EXECUTE_MODULES:
            ts = schema.derive(module)
            tools[ts.command] = Tool(ts.command, ts, executes=True)
        tools["record"] = Tool("record", RECORD, executes=True)
    return tools


def to_wire(tool: Tool, structured: bool) -> dict:
    """The `tools/list` entry for one tool.

    `title` and `outputSchema` both arrived in 2025-06-18, so a
    2025-03-26 client is sent neither: an unknown key is a validation
    failure in some clients and noise in the rest."""
    wire = {"name": tool.name,
            "description": tool.description,
            "inputSchema": schema.json_schema(tool.schema),
            "annotations": tool.annotations}
    if structured:
        wire["title"] = tool.name
        wire["outputSchema"] = OUTPUT_SCHEMA
    return wire


def narrowing_fields(tool: Tool) -> tuple[str, ...]:
    """The fields a capped answer tells the caller to narrow by: this
    tool's, in `NARROWING`'s order rather than the parser's."""
    names = {f.name for f in tool.schema.fields}
    return tuple(name for name in NARROWING if name in names)


def command_argv(tool: Tool, arguments: dict) -> tuple[list[str], dict]:
    """`(argv, extras)` for a call: the child's command line, and what
    the runner must be told that no command line can carry.

    `record` is the one tool `to_argv` cannot build for. Its target is
    the argv AFTER a `--` -- which is what keeps a target's own `-m` or
    `--include` the target's -- and `cwd`/`python` are the child's
    process, not its arguments. It is refused by `schema.validate`
    first all the same, so an unknown or missing field is named here in
    the words every other tool uses.
    """
    if tool.schema is not RECORD:
        return schema.to_argv(tool.schema, arguments), {}
    schema.validate(RECORD, arguments)
    argv = ["run"]
    for f in RECORD.fields:
        if f.option is None or f.name not in arguments:
            continue
        value = arguments[f.name]
        if f.kind == "array":
            for item in value:
                argv.extend([f.option, item])
        else:
            argv.extend([f.option, value])
    argv.extend(["--", *arguments["command"]])
    return argv, {"cwd": arguments.get("cwd"),
                  "python": arguments.get("python")}
