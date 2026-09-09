"""Which harness a typed command names, and what the driver refuses.

Every row of the recognition table (design section 2.2) is a case here, and
so is every refusal, WORD FOR WORD: a refusal is the whole of what a caller
gets back -- there is no second chance to explain -- so its sentence is part
of the contract and not a message that may drift.

Nothing in this module spawns anything. `recognise` reads a command and a
directory and answers; the driver is what acts on the answer.
"""
from pathlib import Path

import pytest

from sensorium.ts import harness


def plan_for(cmd, cwd):
    got = harness.recognise(list(cmd), Path(cwd))
    assert isinstance(got, harness.Plan), got
    return got


def refusal_for(cmd, cwd):
    got = harness.recognise(list(cmd), Path(cwd))
    assert isinstance(got, harness.Refusal), got
    return got.message


# -- the table --------------------------------------------------------------

VITEST = [
    ("bare", ["vitest", "run"]),
    ("npx", ["npx", "vitest", "run"]),
    ("pnpm", ["pnpm", "vitest", "run"]),
    ("pnpm exec", ["pnpm", "exec", "vitest", "run"]),
    ("yarn", ["yarn", "vitest", "run"]),
    ("yarn exec", ["yarn", "exec", "vitest", "run"]),
    ("a path", ["./node_modules/.bin/vitest", "run"]),
    ("an absolute path", ["/usr/local/bin/vitest", "run"]),
]


@pytest.mark.parametrize("label,cmd", VITEST, ids=[c[0] for c in VITEST])
def test_every_spelling_of_vitest_is_recognised(label, cmd, tmp_path):
    got = plan_for(cmd, tmp_path)
    assert got.kind == "vitest"
    assert got.harness_args == ["run"]
    # The command is spawned AS TYPED: the runner prefix is the user's
    # business, and a driver that dropped `npx` would run a vitest the user
    # did not choose.
    assert got.stripped == cmd


def test_node_with_test_among_its_arguments_is_the_node_harness(tmp_path):
    got = plan_for(["node", "--test", "src/a.test.ts"], tmp_path)
    assert got.kind == "node-test"
    assert got.harness_args == ["--test", "src/a.test.ts"]


def test_test_may_come_after_other_node_flags(tmp_path):
    got = plan_for(["node", "--experimental-strip-types", "--test", "src/"],
                   tmp_path)
    assert got.kind == "node-test"


def test_a_path_ending_in_node_is_the_node_harness_too(tmp_path):
    got = plan_for(["/usr/bin/node", "--test", "src/"], tmp_path)
    assert got.kind == "node-test"


def test_node_without_test_is_not_a_harness(tmp_path):
    """A plain `node script.js` is a program, not a test run. It is refused
    by the same sentence as any other unrecognised command, which names
    `node --test` -- exactly the edit that would fix it."""
    message = refusal_for(["node", "script.js"], tmp_path)
    assert "vitest" in message and "node --test" in message


# -- the three refusals -----------------------------------------------------

SCRIPTS = [["npm", "test"], ["npm", "run", "test"], ["npm", "t"],
           ["pnpm", "test"], ["pnpm", "run", "unit"], ["pnpm", "t"],
           ["yarn", "test"], ["yarn", "run", "unit"], ["yarn", "t"]]


@pytest.mark.parametrize("cmd", SCRIPTS, ids=[" ".join(c) for c in SCRIPTS])
def test_a_package_script_is_refused_naming_the_direct_form(cmd, tmp_path):
    message = refusal_for(cmd, tmp_path)
    assert message == (
        f"{cmd[0]} {cmd[1]} runs a package script, and a script cannot take "
        "the flags this recorder appends: run the harness directly, "
        "sensorium ts run -- vitest run …")


JESTS = [["jest"], ["npx", "jest"], ["npx", "jest", "--ci"],
         ["./node_modules/.bin/jest"], ["yarn", "exec", "jest"]]


@pytest.mark.parametrize("cmd", JESTS, ids=[" ".join(c) for c in JESTS])
def test_jest_is_refused_by_name(cmd, tmp_path):
    assert refusal_for(cmd, tmp_path) == (
        "jest is not supported: not measured, and the consumer does not "
        "run it")


def test_jest_wins_over_the_package_script_refusal(tmp_path):
    """`npm run jest` is both a script and jest. Telling the caller to run
    the harness directly would be telling them to run a harness this
    recorder does not wire, so the jest sentence is the one they get."""
    assert refusal_for(["npm", "run", "jest"], tmp_path).startswith("jest")


UNRECOGNISED = [["mocha"], ["ava"], ["python", "-m", "pytest"],
                ["cargo", "test"], ["npm", "exec", "vitest"]]


@pytest.mark.parametrize("cmd", UNRECOGNISED,
                         ids=[" ".join(c) for c in UNRECOGNISED])
def test_anything_else_is_refused_naming_both_harnesses(cmd, tmp_path):
    assert refusal_for(cmd, tmp_path) == (
        f"{' '.join(cmd)} names no harness this recorder wires: "
        "sensorium ts run -- vitest run …, or sensorium ts run -- "
        "node --test …")


def test_an_empty_command_is_refused_naming_both_harnesses(tmp_path):
    assert refusal_for([], tmp_path) == (
        "no harness command given: sensorium ts run -- vitest run …, or "
        "sensorium ts run -- node --test …")


# -- --root and --config ----------------------------------------------------

ROOTS = [["--root", "sub"], ["-r", "sub"], ["--root=sub"]]


@pytest.mark.parametrize("flag", ROOTS, ids=[" ".join(f) for f in ROOTS])
def test_every_spelling_of_root_is_consumed_and_resolved(flag, tmp_path):
    (tmp_path / "sub").mkdir()
    got = plan_for(["vitest", "run", *flag], tmp_path)
    assert got.root == tmp_path / "sub"
    assert got.stripped == ["vitest", "run"]
    assert got.harness_args == ["run"]


CONFIGS = [["--config", "mine.ts"], ["-c", "mine.ts"], ["--config=mine.ts"]]


@pytest.mark.parametrize("flag", CONFIGS, ids=[" ".join(f) for f in CONFIGS])
def test_every_spelling_of_config_is_consumed_and_resolved(flag, tmp_path):
    (tmp_path / "mine.ts").write_text("export default {}\n")
    got = plan_for(["vitest", "run", *flag], tmp_path)
    assert got.user_config == tmp_path / "mine.ts"
    assert got.stripped == ["vitest", "run"]


def test_root_and_config_resolve_against_the_cwd_not_each_other(tmp_path):
    """vitest resolves both against the directory it was invoked from, so a
    `--config` beside the caller and a `--root` below them are two
    independent paths -- never the config read out of the new root."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "mine.ts").write_text("export default {}\n")
    got = plan_for(["vitest", "run", "--root", "sub", "-c", "mine.ts"],
                   tmp_path)
    assert (got.root, got.user_config) == (tmp_path / "sub",
                                           tmp_path / "mine.ts")


def test_the_root_defaults_to_the_cwd(tmp_path):
    assert plan_for(["vitest", "run"], tmp_path).root == tmp_path


def test_root_and_config_are_only_consumed_for_vitest(tmp_path):
    """`node --test --config x` is node's argument, not vitest's, and the
    driver hands node's command line back untouched."""
    got = plan_for(["node", "--test", "--config", "x"], tmp_path)
    assert got.stripped == ["node", "--test", "--config", "x"]
    assert got.root == tmp_path


# -- the config search ------------------------------------------------------

SEARCH = ["vitest.config.ts", "vitest.config.mts", "vitest.config.cts",
          "vitest.config.js", "vitest.config.mjs", "vitest.config.cjs",
          "vite.config.ts", "vite.config.mts", "vite.config.cts",
          "vite.config.js", "vite.config.mjs", "vite.config.cjs"]


@pytest.mark.parametrize("name", SEARCH)
def test_each_searched_config_name_is_found_in_the_root(name, tmp_path):
    (tmp_path / name).write_text("export default {}\n")
    assert plan_for(["vitest", "run"], tmp_path).user_config == tmp_path / name


def test_the_search_prefers_vitest_config_over_vite_config(tmp_path):
    (tmp_path / "vite.config.ts").write_text("export default {}\n")
    (tmp_path / "vitest.config.cjs").write_text("module.exports = {}\n")
    got = plan_for(["vitest", "run"], tmp_path)
    assert got.user_config == tmp_path / "vitest.config.cjs"


def test_the_search_follows_the_extension_order(tmp_path):
    (tmp_path / "vitest.config.js").write_text("export default {}\n")
    (tmp_path / "vitest.config.mts").write_text("export default {}\n")
    got = plan_for(["vitest", "run"], tmp_path)
    assert got.user_config == tmp_path / "vitest.config.mts"


def test_the_search_happens_in_the_root_and_not_the_cwd(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "vitest.config.ts").write_text("export default {}\n")
    (tmp_path / "sub" / "vitest.config.ts").write_text("export default {}\n")
    got = plan_for(["vitest", "run", "--root", "sub"], tmp_path)
    assert got.user_config == tmp_path / "sub" / "vitest.config.ts"


def test_no_config_at_all_is_a_fact_and_not_a_refusal(tmp_path):
    assert plan_for(["vitest", "run"], tmp_path).user_config is None


def test_an_explicit_config_wins_over_one_the_search_would_find(tmp_path):
    (tmp_path / "vitest.config.ts").write_text("export default {}\n")
    (tmp_path / "mine.mts").write_text("export default {}\n")
    got = plan_for(["vitest", "run", "--config", "mine.mts"], tmp_path)
    assert got.user_config == tmp_path / "mine.mts"


# -- what gets spawned ------------------------------------------------------

def test_the_wrapper_flags_are_reissued_once_each_at_the_end(tmp_path):
    got = plan_for(["npx", "vitest", "run", "-c", "mine.ts", "--root=."],
                   tmp_path)
    argv = got.vitest_command(tmp_path / "w.config.mts")
    assert argv == ["npx", "vitest", "run", "--config",
                    str(tmp_path / "w.config.mts"), "--root", str(tmp_path)]
    assert argv.count("--config") == 1 and argv.count("--root") == 1
    assert "-c" not in argv and "-r" not in argv


def test_the_register_import_lands_directly_after_the_node_token(tmp_path):
    """`--import` is node's own flag and has to be on node's side of the
    script: after `--test` it would be an argument to the test runner."""
    got = plan_for(["node", "--test", "src/a.test.ts"], tmp_path)
    reg = tmp_path / "register.mjs"
    assert got.node_command(reg) == ["node", "--import", str(reg), "--test",
                                     "src/a.test.ts"]


def test_the_command_as_typed_is_kept_whole_for_the_record(tmp_path):
    """`argv` is what the user typed, flags and all. It is what the trace
    reports the invocation as, so consuming `--root` out of it would make
    the record disagree with the shell history that produced it."""
    cmd = ["npx", "vitest", "run", "--root=.", "src/a.test.ts"]
    got = plan_for(cmd, tmp_path)
    assert got.argv == cmd
    assert got.stripped == ["npx", "vitest", "run", "src/a.test.ts"]
