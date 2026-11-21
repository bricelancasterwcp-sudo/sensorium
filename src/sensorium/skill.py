"""Print and install the Agent Skills file.

The file agents read is ``skills/sensorium/SKILL.md`` in a checkout and
``sensorium/_skill/SKILL.md`` in a wheel. ``install`` copies that one file.
It does not overwrite an existing ``SKILL.md`` unless ``--force`` is given.

Where each named target writes, checked November 2026:

* ``claude`` — Claude Code's project skill directory
  ``.claude/skills/<name>/`` and, with ``--user``,
  ``~/.claude/skills/<name>/`` (code.claude.com/docs/en/skills).
* ``cursor``, ``codex``, and ``agents`` — ``.agents/skills/<name>/`` and,
  with ``--user``, ``~/.agents/skills/<name>/``. Codex reads
  ``.agents/skills`` from the working directory up to the repository root,
  and ``$HOME/.agents/skills`` for a user skill
  (developers.openai.com/codex/skills). Cursor's install guides also name
  ``.cursor/skills/<name>/``. Older Codex pages still say
  ``.codex/skills`` and ``~/.codex/skills``. Neither of those is written
  unless the caller passes the directory as a path.

With no ``--target``, both the Claude Code directory and the
``.agents/skills`` directory are written, so one install covers Claude
Code and Codex. Cursor loads both of those trees in current install
guides; ``.cursor/skills`` is still a path the caller passes explicitly.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sensorium

_SKILL_DIR = Path("skills") / "sensorium"
_FILENAME = "SKILL.md"

#: Relative skill directory for each named target. ``cursor``, ``codex``,
#: and ``agents`` share one path on purpose; the help text says so.
_NAMED: dict[str, Path] = {
    "claude": Path(".claude") / "skills" / "sensorium",
    "cursor": Path(".agents") / "skills" / "sensorium",
    "codex": Path(".agents") / "skills" / "sensorium",
    "agents": Path(".agents") / "skills" / "sensorium",
}

#: Written when ``--target`` is omitted. Two directories, not three copies
#: of the ``.agents`` path.
_DEFAULT = ("claude", "agents")


class SkillError(Exception):
    """The skill file or the requested destination cannot be used."""


def locate() -> Path:
    """The ``SKILL.md`` this install should copy. See ``_locate``."""
    return _locate(Path(sensorium.__file__).resolve())


def _locate(here: Path) -> Path:
    """Checkout first, then the wheel path next to the package.

    ``here`` is ``sensorium/__init__.py``. In a checkout its grandparent
    is the repository and ``skills/sensorium/SKILL.md`` sits there. In a
    wheel that grandparent is not the repository; the file is
    ``sensorium/_skill/SKILL.md``.
    """
    checkout = here.parents[2] / _SKILL_DIR / _FILENAME
    if checkout.is_file():
        return checkout
    installed = here.parent / "_skill" / _FILENAME
    if installed.is_file():
        return installed
    raise SkillError(
        "cannot find SKILL.md. A checkout keeps it at "
        "skills/sensorium/SKILL.md. A wheel ships it at "
        "sensorium/_skill/SKILL.md.")


def _is_path(target: str) -> bool:
    """A target the caller spelled as a directory, not a name."""
    return (target.startswith("~") or target.startswith("/")
            or "/" in target or target in {".", ".."})


def destinations(target: str | None, *, user: bool, project: bool,
                 cwd: Path, home: Path) -> list[Path]:
    """The ``SKILL.md`` paths ``install`` will write.

    ``user`` and ``project`` are the two flags. Neither means project.
    A path target is the skill directory itself and rejects both flags.
    """
    if user and project:
        raise SkillError("--project and --user are mutually exclusive")
    if target is not None and _is_path(target):
        if user or project:
            raise SkillError(
                "a path is already a location; do not pass --project or "
                "--user with it")
        directory = Path(target).expanduser()
        if not directory.is_absolute():
            directory = cwd / directory
        return [directory / _FILENAME]
    names = _DEFAULT if target is None else (target,)
    unknown = [n for n in names if n not in _NAMED]
    if unknown:
        raise SkillError(
            f"unknown target {unknown[0]!r}; use claude, cursor, codex, "
            "agents, or a directory path")
    root = home if user else cwd
    return [root / _NAMED[n] / _FILENAME for n in names]


def _target_help() -> str:
    claude = _NAMED["claude"].as_posix()
    agents = _NAMED["agents"].as_posix()
    return (
        "claude, cursor, codex, agents, or a skill directory. "
        f"claude writes {claude}/SKILL.md under the current directory, "
        f"or ~/{claude}/SKILL.md with --user "
        "(Claude Code: code.claude.com/docs/en/skills). "
        f"cursor, codex, and agents all write {agents}/SKILL.md "
        "(Codex reads .agents/skills from the working directory up to "
        "the repo root, and ~/.agents/skills for a user skill: "
        "developers.openai.com/codex/skills). "
        "Cursor install guides also name .cursor/skills/<name>/, and "
        "older Codex pages still say .codex/skills and ~/.codex/skills. "
        "This command writes neither unless you pass that directory as "
        "a path. A target containing a slash, starting with ~, or "
        "absolute is the skill directory: SKILL.md is written inside "
        "it, and --project/--user are refused. With no --target, both "
        "the Claude Code directory and the .agents/skills directory "
        "are written. If any destination already exists, nothing is "
        "written unless --force."
    )


def add_parser(sub) -> None:
    p = sub.add_parser(
        "skill",
        help="print or install the agent skill",
        description="The Agent Skills file skills/sensorium/SKILL.md. "
                    "`show` prints it. `install` copies it into the "
                    "directory an agent reads. It does not overwrite an "
                    "existing SKILL.md unless --force is given.")
    commands = p.add_subparsers(dest="skill_cmd", required=True)

    show = commands.add_parser(
        "show", help="print SKILL.md",
        description="Print the packaged SKILL.md on stdout.")
    show.set_defaults(func=_show)

    inst = commands.add_parser(
        "install", help="copy SKILL.md into an agent's skill directory",
        description="Copy SKILL.md. Named targets use the directories in "
                    "--target's help. A path receives the file directly. "
                    "If any destination already exists, nothing is written "
                    "unless --force.",
        epilog="exit: 0 copied, 2 fix the call (including a refusal to "
               "overwrite)")
    inst.add_argument("--target", default=None, help=_target_help())
    scope = inst.add_mutually_exclusive_group()
    scope.add_argument(
        "--project", action="store_true",
        help="write under the current directory (the default)")
    scope.add_argument(
        "--user", action="store_true",
        help="write under the home directory")
    inst.add_argument(
        "--force", action="store_true",
        help="replace an existing SKILL.md")
    inst.set_defaults(func=_install)


def _show(_args) -> int:
    try:
        text = locate().read_text(encoding="utf-8")
    except SkillError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def _install(args) -> int:
    try:
        src = locate()
        text = src.read_text(encoding="utf-8")
        dests = destinations(
            args.target, user=args.user, project=args.project,
            cwd=Path.cwd(), home=Path.home())
    except SkillError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    blocked = [d for d in dests if d.exists() and not args.force]
    if blocked:
        for d in blocked:
            print(f"error: {d} exists; pass --force to overwrite",
                  file=sys.stderr)
        return 2
    source = src.resolve()
    for dest in dests:
        if dest.resolve() == source:
            print(f"error: {dest} is the packaged SKILL.md; refusing "
                  "to overwrite the source", file=sys.stderr)
            return 2
    try:
        for dest in dests:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for dest in dests:
        print(f"installed: {dest}")
    return 0
