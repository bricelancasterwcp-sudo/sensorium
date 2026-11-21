"""The agent skill file, and `sensorium skill show` / `skill install`.

The file agents read is `skills/sensorium/SKILL.md`. A wheel has no
checkout, so the same bytes are package data at `sensorium/_skill/SKILL.md`.
`install` copies them and refuses to replace an existing file unless
`--force` is passed. The directories are the ones each agent documents;
the help text is where a path this command does not write is named.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from sensorium import cli, skill
from sensorium.mcp import tools

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sensorium" / "SKILL.md"

_FLAG = re.compile(r"--[A-Za-z][A-Za-z0-9-]*")


@pytest.fixture
def proj(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "store"))
    home = tmp_path / "home"
    monkeypatch.setattr(skill.Path, "home", staticmethod(lambda: home))
    return project


def _options() -> set[str]:
    """Every flag the Python CLI accepts, including nested subcommands."""
    parser = argparse.ArgumentParser(prog="sensorium")
    sub = parser.add_subparsers(dest="cmd")
    cli._add_run_parser(sub)
    from sensorium.ts import cli as ts_cli
    from sensorium.c import cli as c_cli
    from sensorium.mcp import cmd as mcp_cmd
    from sensorium.store.gc import add_parsers as add_gc_parsers
    ts_cli.add_parser(sub)
    c_cli.add_parser(sub)
    mcp_cmd.add_parser(sub)
    skill.add_parser(sub)
    add_gc_parsers(sub)
    for mod in cli._QUERY_MODULES:
        mod.add_parser(sub)
    found: set[str] = set()

    def walk(p):
        for action in p._actions:
            found.update(action.option_strings)
            if isinstance(action, argparse._SubParsersAction):
                for choice in action.choices.values():
                    walk(choice)

    walk(parser)
    return found


def test_skill_file_is_frontmatter_and_stays_short():
    text = SKILL.read_text()
    assert len(text.splitlines()) <= 200
    head, _body = text.split("---", 2)[1:]
    assert "name: sensorium" in head
    assert "failing test" in head
    assert "Python, Rust, TypeScript, or C" in head
    assert "MCP" in head
    for sentence in (
        "REFUSED:",
        "verdict: NOTHING WAS CHECKED -- the predicate could not be "
        "evaluated at any of the N recorded site(s)",
        "'hits: 0' here means 'could not evaluate', NOT 'the invariant held'",
        "refocus verdict: MATCH -- every recorded thread produced the "
        "identical CALL/RETURN/RAISE/HANDLED sequence",
        "refocus verdict: DIVERGED --",
        "refocus verdict: REFUSED --",
        "verdict: REFUSED -- cannot issue a MATCH/DIVERGED verdict",
        "verdict: DIVERGED at causal step N",
    ):
        assert sentence in text
    # The two examples are the corpus runs, not a paraphrased bug.
    assert "corpus/silent_swallow/main.py" in text
    assert "parse_row(row='carol,x7')" in text
    assert "dispositions: swallowed 2" in text
    assert "corpus/unit_mismatch/main.py" in text
    assert "shipping_cost(weight_kg=1800)" in text
    assert "item_weight -> 1800" in text


#: Flags of the tools the skill tells the agent to put after `--`,
#: not flags of sensorium. Each one has to stay next to that tool's name.
_OTHER_TOOLS = {"--prefix": "npm ci --prefix typescript",
                "--test": "node --test"}


def test_every_flag_in_the_skill_is_a_real_cli_flag():
    """A flag the skill teaches has to be one the CLI's own parser has.

    `cargo sensorium`'s flags are the same spellings the Python `run` and
    `ts run` parsers already accept (`--focus`, `--tier`, `--max-events`,
    `--max-bytes`, `--max-calls`, `--no-cap`, `--refocus-of`), so this
    walk covers them. `npm ci --prefix` and `node --test` are the other
    tools' flags and are checked by the phrase they appear in. A flag
    invented for sensorium fails here.
    """
    known = _options()
    text = SKILL.read_text()
    mentioned = set(_FLAG.findall(text))
    missing = sorted(mentioned - known - set(_OTHER_TOOLS))
    assert not missing, missing
    for flag, phrase in _OTHER_TOOLS.items():
        assert flag in mentioned
        assert phrase in text


def test_skill_is_not_an_mcp_tool():
    assert "skill" not in tools.table(allow_run=True)
    assert "skill" not in tools.table(allow_run=False)


def test_show_prints_the_file(capsys, proj):
    assert cli.main(["skill", "show"]) == 0
    out = capsys.readouterr().out
    assert out == SKILL.read_text()


def test_locate_reads_the_checkout():
    assert skill.locate() == SKILL


def test_locate_prefers_a_checkout_over_the_wheel_copy(tmp_path):
    init = tmp_path / "src" / "sensorium" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text("")
    checkout = tmp_path / "skills" / "sensorium" / "SKILL.md"
    checkout.parent.mkdir(parents=True)
    checkout.write_text("from-checkout\n")
    wheel = init.parent / "_skill" / "SKILL.md"
    wheel.parent.mkdir(parents=True)
    wheel.write_text("from-wheel\n")
    assert skill._locate(init) == checkout


def test_locate_uses_the_wheel_copy_when_there_is_no_checkout(tmp_path):
    init = tmp_path / "site-packages" / "sensorium" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text("")
    wheel = init.parent / "_skill" / "SKILL.md"
    wheel.parent.mkdir(parents=True)
    wheel.write_text("---\nname: sensorium\n---\n")
    assert skill._locate(init) == wheel


def test_locate_names_both_places_when_the_file_is_missing(tmp_path):
    init = tmp_path / "site-packages" / "sensorium" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text("")
    with pytest.raises(skill.SkillError) as ei:
        skill._locate(init)
    assert "skills/sensorium/SKILL.md" in str(ei.value)
    assert "sensorium/_skill/SKILL.md" in str(ei.value)


def test_default_install_writes_claude_and_agents(capsys, proj):
    assert cli.main(["skill", "install"]) == 0
    out = capsys.readouterr().out
    claude = proj / ".claude" / "skills" / "sensorium" / "SKILL.md"
    agents = proj / ".agents" / "skills" / "sensorium" / "SKILL.md"
    assert claude.read_text() == SKILL.read_text()
    assert agents.read_text() == SKILL.read_text()
    assert str(claude) in out and str(agents) in out
    assert cli.main(["skill", "install"]) == 2
    captured = capsys.readouterr()
    assert "pass --force" in captured.err
    assert claude.read_text() == SKILL.read_text()


def test_install_refuses_when_any_destination_exists(capsys, proj):
    claude = proj / ".claude" / "skills" / "sensorium" / "SKILL.md"
    claude.parent.mkdir(parents=True)
    claude.write_text("keep me\n")
    assert cli.main(["skill", "install", "--project"]) == 2
    captured = capsys.readouterr()
    assert "pass --force" in captured.err
    assert claude.read_text() == "keep me\n"
    assert not (proj / ".agents" / "skills" / "sensorium" / "SKILL.md").exists()
    assert cli.main(["skill", "install", "--force"]) == 0
    assert claude.read_text() == SKILL.read_text()
    assert (proj / ".agents" / "skills" / "sensorium" / "SKILL.md").is_file()


@pytest.mark.parametrize("target", ["cursor", "codex", "agents"])
def test_cursor_codex_and_agents_share_the_agents_directory(capsys, proj, target):
    assert cli.main(["skill", "install", "--target", target]) == 0
    dest = proj / ".agents" / "skills" / "sensorium" / "SKILL.md"
    assert dest.is_file()
    assert not (proj / ".claude" / "skills" / "sensorium").exists()
    assert not (proj / ".cursor" / "skills" / "sensorium").exists()
    capsys.readouterr()


def test_user_claude_writes_under_home(capsys, proj, tmp_path):
    assert cli.main(["skill", "install", "--user", "--target", "claude"]) == 0
    dest = tmp_path / "home" / ".claude" / "skills" / "sensorium" / "SKILL.md"
    assert dest.read_text() == SKILL.read_text()
    assert not (proj / ".claude").exists()
    capsys.readouterr()


def test_path_target_is_the_skill_directory(capsys, proj):
    assert cli.main(["skill", "install", "--target", "custom/sensorium"]) == 0
    dest = proj / "custom" / "sensorium" / "SKILL.md"
    assert dest.read_text() == SKILL.read_text()
    capsys.readouterr()
    assert cli.main(["skill", "install", "--target", "custom/sensorium",
                     "--project"]) == 2
    assert "do not pass --project or --user" in capsys.readouterr().err
    assert dest.read_text() == SKILL.read_text()


def test_unknown_target_writes_nothing(capsys, proj):
    assert cli.main(["skill", "install", "--target", "windsurf"]) == 2
    assert "unknown target" in capsys.readouterr().err
    assert list(proj.iterdir()) == []


def test_project_and_user_together_are_rejected(proj):
    with pytest.raises(SystemExit) as ei:
        cli.main(["skill", "install", "--project", "--user"])
    assert ei.value.code == 2


def test_install_help_names_the_paths_and_the_ones_it_does_not_write(capsys):
    with pytest.raises(SystemExit) as ei:
        cli.main(["skill", "install", "--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert ".claude/skills/sensorium" in out
    assert ".agents/skills/sensorium" in out
    assert ".cursor/skills" in out
    assert ".codex/skills" in out
    assert "--force" in out
    assert "code.claude.com/docs/en/skills" in out
    assert "developers.openai.com/codex/skills" in out


def test_pyproject_ships_the_skill_as_package_data():
    text = (ROOT / "pyproject.toml").read_text()
    assert '"skills/sensorium/SKILL.md" = "sensorium/_skill/SKILL.md"' in text
