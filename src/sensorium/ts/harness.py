"""Which harness a typed command names, and what it takes to wire it.

`sensorium ts run` takes the harness command AFTER `--`, as the user types
it, and does not re-implement a harness's command line (design section 2.3).
So this module's whole job is to read that command and answer one of three
things: it is vitest, it is `node --test`, or it is refused with a sentence
that names the fix.

The refusals are the interesting part, and each one exists because guessing
would be worse than refusing:

* `npm test`, `npm run test`, `npm t` and the pnpm and yarn equivalents are
  read from the nearest `package.json` only when `scripts.test` is a simple
  `vitest` or `node --test` command. A shell metacharacter, a missing
  script, or a manifest that is not in the working directory is a refusal
  that names the script text: this module does not spawn a shell and does
  not change directory;
* any other package script is refused, because a script cannot take the
  flags the driver appends and guessing a shell string would be a guess;
* `jest` was not measured and the consumer does not run it, so a wiring for
  it would be a claim nobody has checked;
* anything else names neither harness, and a driver that spawned it anyway
  would record nothing and exit 0 -- the one failure this recorder must
  never have.

Nothing here spawns or writes. It reads `package.json` only to expand the
test-script forms above.
"""
import json
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

#: Command prefixes that mean "resolve the next token from the project's
#: bin directory". They are kept in the spawned command: which `vitest` runs
#: is the user's choice, and dropping `npx` would run a different one.
RUNNERS = ("npx", "pnpm", "yarn")

#: The package managers whose script verbs are refused. `npx` is not one of
#: them: `npx test` names a binary, not a script.
MANAGERS = ("npm", "pnpm", "yarn")
SCRIPT_VERBS = ("test", "run", "t")

#: vitest's own config search, in vitest's own order, looked for in the
#: ROOT. Written out rather than globbed so the order is the contract.
CONFIG_NAMES = tuple(f"{stem}.config.{ext}"
                     for stem in ("vitest", "vite")
                     for ext in ("ts", "mts", "cts", "js", "mjs", "cjs"))

_BOTH = ("sensorium ts run -- vitest run …, or "
         "sensorium ts run -- node --test …")

JEST = ("jest is not supported: not measured, and the consumer does not "
        "run it")


@dataclass(frozen=True)
class Refusal:
    """Why this command was not wired. One sentence, and the whole answer."""

    message: str


@dataclass(frozen=True)
class Plan:
    """A recognised command, and everything the driver needs to wire it.

    `argv` is what the user typed, kept whole for the record; `stripped` is
    the same command with the flags the driver re-issues taken out, and is
    what the spawned command is built from. They differ exactly when the
    user passed `--root` or `--config`.
    """

    kind: str
    argv: list[str]
    stripped: list[str]
    harness_args: list[str]
    root: Path
    user_config: Path | None
    harness_index: int

    def vitest_command(self, config: Path) -> list[str]:
        """The command to spawn, with the wrapper re-issued ONCE at the end.

        Last wins in vitest's own parser, and appending is what makes the
        re-issue independent of where the user's own flags were: a config
        inserted in the middle could be overridden by a later one of theirs.
        """
        return [*self.stripped, "--config", str(config),
                "--root", str(self.root)]

    def node_command(self, register: Path) -> list[str]:
        """The command to spawn, with the loader hook on NODE's side.

        `--import` is node's own flag. After `--test` it would be an
        argument to the test runner, which would either refuse it or pass it
        to the file.
        """
        cut = self.harness_index + 1
        return [*self.stripped[:cut], "--import", str(register),
                *self.stripped[cut:]]


#: Characters that make `scripts.test` a shell program rather than an argv.
#: `&&` and `||` are covered by `&` and `|`. A newline is one of them.
_SHELL_META = frozenset("&|;<>`$\n\r")


def recognise(cmd: list[str], cwd: Path, *, expand: bool = True) -> Plan | Refusal:
    """Read a typed command. See the module docstring for the rules."""
    cwd = Path(cwd)
    if not cmd:
        return Refusal(f"no harness command given: {_BOTH}")
    if expand and _is_test_script(cmd):
        return _expand_test_script(cmd, cwd)
    start = _skip_runners(cmd)
    if isinstance(start, Refusal):
        # `npm run jest` is both a script and jest, and the script sentence's
        # advice -- run the harness directly -- would send them at a harness
        # this recorder does not wire. The jest sentence is the one they get.
        return Refusal(JEST) if _script_names_jest(cmd) else start
    head = cmd[start]
    # The HARNESS token, and no other (R44, finding 11). Scanning every token
    # refused `vitest run src/jest` -- an ordinary vitest run over a directory
    # somebody called `jest` -- with a sentence naming a harness that appears
    # nowhere in what they typed.
    if _names(head, "jest"):
        return Refusal(JEST)
    if _names(head, "vitest"):
        return _vitest(cmd, start, cwd)
    if _names(head, "node") and "--test" in cmd[start + 1:]:
        return _node_test(cmd, start, cwd)
    return Refusal(f"{' '.join(cmd)} names no harness this recorder wires: "
                   f"{_BOTH}")


def _is_test_script(cmd: list[str]) -> bool:
    """The exact forms whose `scripts.test` this recorder will read.

    `npm run unit` is not one of them, and neither is `npm test -- src`:
    extra tokens are arguments a script would receive, and appending them
    is a second guess. `npm run jest` is jest's sentence, decided later.
    """
    if not cmd or cmd[0] not in MANAGERS:
        return False
    if len(cmd) == 2 and cmd[1] in ("test", "t"):
        return True
    return len(cmd) == 3 and cmd[1] == "run" and cmd[2] == "test"


def _expand_test_script(cmd: list[str], cwd: Path) -> Plan | Refusal:
    """Replace `npm test` with the argv `scripts.test` names, or refuse.

    The plan's `argv` stays what was typed. `stripped` is the script's
    argv, which is what the driver spawns. No shell.
    """
    manifest = _package_json(cwd)
    if manifest is None:
        return Refusal(
            "no package.json found, so scripts.test was not read. "
            f"Run the harness directly, {_BOTH}")
    if manifest.parent.resolve() != Path(cwd).resolve():
        return Refusal(
            f"{' '.join(cmd)} would run scripts.test from {manifest.parent}, "
            "and this recorder does not change directory. "
            f"Run the harness directly, {_BOTH}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Refusal(
            f"{manifest} does not parse as JSON, so scripts.test was not "
            f"read. Run the harness directly, {_BOTH}")
    scripts = data.get("scripts") if isinstance(data, dict) else None
    script = scripts.get("test") if isinstance(scripts, dict) else None
    if not isinstance(script, str):
        return Refusal(
            "package.json has no scripts.test string. "
            f"Run the harness directly, {_BOTH}")
    if any(ch in _SHELL_META for ch in script):
        return Refusal(
            f"package.json scripts.test is {script!r}, which is a shell "
            "command, and this recorder does not spawn a shell. "
            f"Run the harness directly, {_BOTH}")
    try:
        argv = shlex.split(script)
    except ValueError:
        return Refusal(
            f"package.json scripts.test is {script!r}, which is not a "
            "simple command. Run the harness directly, {_BOTH}")
    inner = recognise(argv, cwd, expand=False)
    if isinstance(inner, Plan):
        return Plan(kind=inner.kind, argv=list(cmd), stripped=inner.stripped,
                    harness_args=inner.harness_args, root=inner.root,
                    user_config=inner.user_config,
                    harness_index=inner.harness_index)
    if inner.message == JEST:
        return Refusal(
            f"package.json scripts.test is {script!r}, and {JEST}. "
            f"Run the harness directly, {_BOTH}")
    return Refusal(
        f"package.json scripts.test is {script!r}, which is not a vitest "
        "or node --test command this recorder can run without a shell. "
        f"Run the harness directly, {_BOTH}")


def _package_json(cwd: Path) -> Path | None:
    """The nearest `package.json`, walking parents the way npm does."""
    here = Path(cwd).resolve()
    for directory in [here, *here.parents]:
        candidate = directory / "package.json"
        if candidate.is_file():
            return candidate
    return None


def _script_names_jest(cmd: list[str]) -> bool:
    """Whether a refused package-script command runs a script called jest.

    The token straight after the manager's verb is the SCRIPT's name, which
    is the closest thing such a command has to a harness token -- unlike
    the file arguments further along, which name nothing.
    """
    for i, token in enumerate(cmd[:-2]):
        if token in MANAGERS and cmd[i + 1] in SCRIPT_VERBS:
            return _names(cmd[i + 2], "jest")
    return False


def _names(token: str, program: str) -> bool:
    """A bare name, or any path ending in it. `./node_modules/.bin/vitest`
    is vitest; `vitest-helper` is not."""
    return token == program or token.endswith("/" + program)


def _skip_runners(cmd: list[str]) -> int | Refusal:
    """The index of the harness token, past any runner prefix."""
    i = 0
    while i < len(cmd):
        token, following = cmd[i], (cmd[i + 1] if i + 1 < len(cmd) else None)
        if token in MANAGERS and following in SCRIPT_VERBS:
            return Refusal(
                f"{token} {following} runs a package script, and a script "
                "cannot take the flags this recorder appends: run the "
                "harness directly, sensorium ts run -- vitest run …")
        if token in RUNNERS:
            i += 2 if token != "npx" and following == "exec" else 1
            continue
        return i
    return Refusal(f"{' '.join(cmd)} names no harness this recorder wires: "
                   f"{_BOTH}")


def _vitest(cmd: list[str], start: int, cwd: Path) -> Plan:
    kept, root_arg, config_arg = _consume(cmd[start + 1:])
    root = _under(cwd, root_arg) or cwd
    config = _under(cwd, config_arg) or _search(root)
    return Plan(kind="vitest", argv=list(cmd),
                stripped=[*cmd[:start + 1], *kept], harness_args=kept,
                root=root, user_config=config, harness_index=start)


def _node_test(cmd: list[str], start: int, cwd: Path) -> Plan:
    """node's command line is node's. Nothing is consumed from it: a
    `--config` there is an argument to the program under test."""
    return Plan(kind="node-test", argv=list(cmd), stripped=list(cmd),
                harness_args=cmd[start + 1:], root=cwd, user_config=None,
                harness_index=start)


def _consume(args: list[str]) -> tuple[list[str], str | None, str | None]:
    """`--root` and `--config` out, in all six spellings, everything else
    kept in order."""
    kept: list[str] = []
    values: dict[str, str | None] = {"--root": None, "--config": None}
    aliases = {"-r": "--root", "-c": "--config"}
    i = 0
    while i < len(args):
        arg = args[i]
        name = aliases.get(arg, arg)
        if name in values:
            values[name] = args[i + 1] if i + 1 < len(args) else None
            i += 2
            continue
        prefix = next((k for k in values if arg.startswith(k + "=")), None)
        if prefix is not None:
            values[prefix] = arg[len(prefix) + 1:]
            i += 1
            continue
        kept.append(arg)
        i += 1
    return kept, values["--root"], values["--config"]


def _under(cwd: Path, value: str | None) -> Path | None:
    """A command-line path, resolved the way vitest resolves it: against the
    directory the command was typed in.

    `normpath` and not `resolve`: a symlinked checkout is a real place a
    consumer works in, and rewriting their root to its target would make
    every path in every trace name a directory they never mentioned.
    """
    if value is None:
        return None
    return Path(os.path.normpath(cwd / value))


def _search(root: Path) -> Path | None:
    """vitest's own config search, in the root. No config is a FACT: a
    project can have none, and the wrapper then merges onto `{}`."""
    for name in CONFIG_NAMES:
        if (root / name).is_file():
            return root / name
    return None
