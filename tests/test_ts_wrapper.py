"""The two files the driver writes into the consumer's tree, and their exit.

The wrapper config is the only thing this recorder puts in front of a
consumer's own vitest config, so its text is pinned BYTE FOR BYTE here
rather than parsed: a line that moves is a line vitest may read differently,
and a test that only checked for substrings would let the difference
through.

Two properties this module exists to hold, both of them measured hazards:

* the runtime is declared external as a **RegExp** (R16). A string entry is
  matched by vitest only as `<moduleDirectory>/<entry>`, so an absolute path
  written as a string matches NOTHING and the run quietly gets two runtimes;
* the setup file names the package by its ABSOLUTE path, because the
  package's `exports` map has no `./src/*` entry and a bare specifier would
  not resolve from the consumer's tree.

Nothing here runs node. What the text does under vitest 4.1.9 is the live
test's business (`tests/test_ts_live.py`).
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

from sensorium.ts import wrapper

INV = "20260909-120000-abcdef"


def fake_pkg(tmp_path: Path) -> Path:
    """A package directory with the one file `setup_text` reads."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "setup.mjs").write_text(
        "import * as rt from '__PKG__/src/rt.mjs';\n")
    return pkg


def consumer(tmp_path: Path) -> Path:
    """A project directory with an INSTALLED `node_modules`. Not empty on
    purpose: `remove` takes away a `node_modules` it made itself, and one
    with nothing in it is one nobody installed into."""
    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "node_modules" / ".package-lock.json").write_text("{}\n")
    return root


#: Every character a JavaScript RegExp literal gives a meaning to, `/`
#: included -- it ends the literal. Spelled out here so the golden escapes
#: independently of the code under test.
META = ".*+?^${}()|[]\\/"


def esc(text: str) -> str:
    return "".join("\\" + c if c in META else c for c in text)


def golden(root: Path, pkg: Path, user_config: Path | None) -> str:
    """The wrapper config as it must be written, spelled out once."""
    rt = f"{pkg}/src/rt.mjs"
    escaped = esc(rt)
    base = "" if user_config is None else f"import base from '{user_config}';\n"
    return (
        f"// written by sensorium ts run for invocation {INV}; "
        "removed when it exits\n"
        "import fs from 'node:fs';\n"
        "import path from 'node:path';\n"
        "import { mergeConfig } from 'vitest/config';\n"
        f"import sensorium from '{pkg}/src/vite.mjs';\n"
        f"{base}"
        f"const user = {'base' if user_config else '{}'};\n"
        "const resolved = typeof user === 'function' "
        "? await user({ command: 'serve', mode: 'test' }) : user;\n"
        # R41, narrowed: inline project objects are instrumented; a string
        # project is refused by name. Spelled out here rather than imported
        # from the module under test, which is what makes this a golden.
        f"const __layer = () => ({{\n"
        f"  root: '{root}',\n"
        f"  plugins: [sensorium({{ root: '{root}', pkgDir: '{pkg}', "
        f"rtPath: '{rt}' }})],\n"
        "  test: {\n"
        f"    setupFiles: ['{root}/node_modules/.sensorium/{INV}.setup.mjs'],\n"
        f"    server: {{ deps: {{ external: [/{escaped}/] }} }},\n"
        "  },\n"
        "});\n"
        "function __plist(cfg) {\n"
        "  if (cfg == null || typeof cfg !== 'object') return null;\n"
        "  if (cfg.test && cfg.test.projects !== undefined) "
        "return ['test', 'projects', cfg.test.projects];\n"
        "  if (cfg.test && cfg.test.workspace !== undefined) "
        "return ['test', 'workspace', cfg.test.workspace];\n"
        "  if (cfg.projects !== undefined) return ['', 'projects', cfg.projects];\n"
        "  if (cfg.workspace !== undefined) "
        "return ['', 'workspace', cfg.workspace];\n"
        "  return null;\n"
        "}\n"
        "function __inline(list) {\n"
        "  return Array.isArray(list) && list.every((p) => p !== null && "
        "typeof p === 'object' && !Array.isArray(p));\n"
        "}\n"
        "function __instrument(cfg) {\n"
        "  const found = __plist(cfg);\n"
        "  if (found === null) return mergeConfig(cfg, __layer());\n"
        "  if (!__inline(found[2])) return null;\n"
        "  const wrapped = [];\n"
        "  for (const p of found[2]) {\n"
        "    const w = __instrument(p);\n"
        "    if (w === null) return null;\n"
        "    wrapped.push(w);\n"
        "  }\n"
        "  if (found[0] === 'test') return { ...cfg, test: { ...cfg.test, "
        "[found[1]]: wrapped } };\n"
        "  return { ...cfg, [found[1]]: wrapped };\n"
        "}\n"
        "const __out = __instrument(resolved);\n"
        "if (__out === null) {\n"
        "  const reason = 'vitest project globs and config-file projects are "
        "not supported by sensorium-ts 0.6.2: a string in test.projects or "
        "test.workspace names another config this wrapper does not merge, so "
        "that project would run unrecorded. Inline project objects are "
        "instrumented. Run one project directly, sensorium ts run -- vitest "
        "run --project <name>';\n"
        "  const spool = process.env.SENSORIUM_SPOOL;\n"
        "  if (spool) {\n"
        "    fs.mkdirSync(spool, { recursive: true });\n"
        "    fs.writeFileSync(path.join(spool, 'wrapper-refusal.json'), "
        "JSON.stringify({ reason }));\n"
        "  }\n"
        "  throw new Error(reason);\n"
        "}\n"
        "export default __out;\n")


# -- the text ---------------------------------------------------------------

def test_the_config_text_is_exact_with_a_user_config(tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    user = root / "vitest.config.ts"
    user.write_text("export default {}\n")
    assert wrapper.config_text(root, INV, pkg, user) == golden(root, pkg, user)


def test_the_config_text_is_exact_with_no_user_config(tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    assert wrapper.config_text(root, INV, pkg, None) == golden(root, pkg, None)


def test_the_two_texts_differ_in_exactly_one_line_and_one_word(tmp_path):
    """The `import base` line, and `base` against `{}`. Everything else is
    the same text, so a reader comparing a driven run with and without a
    consumer config has one difference to look at."""
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    user = root / "vitest.config.ts"
    with_ = wrapper.config_text(root, INV, pkg, user).splitlines()
    without = wrapper.config_text(root, INV, pkg, None).splitlines()
    assert len(with_) == len(without) + 1
    assert with_[5] == f"import base from '{user}';"
    assert (with_[6], without[5]) == ("const user = base;", "const user = {};")
    assert with_[7:] == without[6:]


def test_the_setup_text_names_the_package_absolutely(tmp_path):
    pkg = fake_pkg(tmp_path)
    assert wrapper.setup_text(pkg) == f"import * as rt from '{pkg}/src/rt.mjs';\n"
    assert "__PKG__" not in wrapper.setup_text(pkg)


def test_the_real_template_still_carries_the_placeholder(tmp_path):
    """`setup_text` is a substitution, and a template that stopped carrying
    the placeholder would substitute nothing and ship a setup file importing
    a specifier that does not resolve -- silently, with an empty spool as the
    only symptom."""
    from sensorium.ts import pkg as pkg_mod
    template = (pkg_mod.locate() / "src" / "setup.mjs").read_text()
    assert "__PKG__" in template
    out = wrapper.setup_text(pkg_mod.locate())
    assert "__PKG__" not in out
    assert f"'{pkg_mod.locate()}/src/rt.mjs'" in out


# -- the escaping -----------------------------------------------------------

def test_a_path_with_regexp_metacharacters_is_escaped_in_both_places(
        tmp_path):
    """A real directory name can hold `.` and `+` (`v1.2+build`), and both
    are RegExp metacharacters: unescaped, `.` matches any character and `+`
    repeats the character before it, so the declaration would match a
    different set of modules than the one file it names."""
    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    pkg = tmp_path / "pkg-1.2+build"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "setup.mjs").write_text("'__PKG__/src/rt.mjs'\n")
    text = wrapper.config_text(root, INV, pkg, None)
    rt = f"{pkg}/src/rt.mjs"
    assert f"external: [/{esc(rt)}/]" in text
    assert "\\.2\\+build" in text
    # The same path inside a single-quoted string keeps its own characters:
    # a JS string gives none of them a meaning.
    assert f"rtPath: '{rt}'" in text


def test_a_quote_in_a_path_cannot_end_the_string_it_sits_in(tmp_path):
    """Not a path anyone means to have, and exactly why it is escaped: an
    unescaped `'` would close the specifier and the rest of the path would
    become code."""
    assert wrapper.js_string("a'b\\c") == "a\\'b\\\\c"


def test_a_line_terminator_in_a_path_cannot_break_the_line_it_sits_in():
    """A JavaScript single-quoted string may not contain a raw line
    terminator, and JavaScript counts four: LF, CR, U+2028 and U+2029. A
    path holding one -- a directory somebody named by pasting -- would have
    ended the string mid-token and turned the rest of the config into a
    syntax error at best. The two Unicode ones are the subtle half: they are
    invisible in every editor and legal in a POSIX filename.

    The backslash pass still runs first, so an escape this adds is never
    itself escaped.
    """
    assert wrapper.js_string("a\nb") == r"a\nb"
    assert wrapper.js_string("a\rb") == r"a\rb"
    assert wrapper.js_string("a\u2028b") == r"a\u2028b"
    assert wrapper.js_string("a\u2029b") == r"a\u2029b"
    assert wrapper.js_string("a\\\nb") == "a" + r"\\" + r"\n" + "b"
    # Nothing else moved: the two escapes that shipped are unchanged.
    assert wrapper.js_string("a'b\\c") == "a\\'b\\\\c"


def test_the_regexp_escape_covers_every_metacharacter():
    for ch in ".*+?^${}()|[]\\/":
        assert wrapper.js_regexp(f"a{ch}b") == f"a\\{ch}b"


# -- writing and removing ---------------------------------------------------

def test_write_puts_both_files_under_node_modules_dot_sensorium(tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    config, setup = wrapper.write(root, INV, pkg, None)
    home = root / "node_modules" / ".sensorium"
    assert config == home / f"{INV}.config.mts"
    assert setup == home / f"{INV}.setup.mjs"
    assert config.read_text() == wrapper.config_text(root, INV, pkg, None)
    assert setup.read_text() == wrapper.setup_text(pkg)


def test_write_touches_nothing_else_in_the_consumers_tree(tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    (root / "vitest.config.ts").write_text("export default {}\n")
    before = sorted(p.relative_to(root) for p in root.rglob("*"))
    wrapper.write(root, INV, pkg, None)
    after = sorted(p.relative_to(root) for p in root.rglob("*"))
    assert [str(p) for p in after if p not in before] == [
        "node_modules/.sensorium",
        f"node_modules/.sensorium/{INV}.config.mts",
        f"node_modules/.sensorium/{INV}.setup.mjs"]


def test_remove_takes_both_files_and_the_directory_it_made(tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    paths = wrapper.write(root, INV, pkg, None)
    wrapper.remove(paths)
    assert not (root / "node_modules" / ".sensorium").exists()
    assert (root / "node_modules").is_dir()


def test_remove_leaves_a_directory_another_invocation_is_still_using(
        tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    paths = wrapper.write(root, INV, pkg, None)
    other = wrapper.write(root, "20260909-120001-fedcba", pkg, None)
    wrapper.remove(paths)
    home = root / "node_modules" / ".sensorium"
    assert home.is_dir()
    assert sorted(p.name for p in home.iterdir()) == sorted(
        p.name for p in other)


def test_remove_is_quiet_about_a_file_that_is_already_gone(tmp_path):
    """The removal runs in a `finally`, so it also runs on paths a failed
    write never created. It must not turn one failure into two."""
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    home = root / "node_modules" / ".sensorium"
    wrapper.remove((home / "a.config.mts", home / "a.setup.mjs"))


def test_a_node_modules_the_driver_created_goes_with_it(tmp_path):
    """A workspace package can have no `node_modules` of its own and still
    run vitest from a hoisted one. The wrapper has to live under a
    `node_modules` all the same (bare `vitest/config` resolves from there),
    so the driver makes one -- and takes it away again."""
    root = tmp_path / "app"
    root.mkdir()
    pkg = fake_pkg(tmp_path)
    wrapper.remove(wrapper.write(root, INV, pkg, None))
    assert not (root / "node_modules").exists()
    assert root.is_dir()


@pytest.mark.skipif(os.geteuid() == 0,
                    reason="root writes into a read-only directory anyway")
def test_a_read_only_node_modules_is_refused_by_name(tmp_path):
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    nm = root / "node_modules"
    nm.chmod(0o500)
    try:
        with pytest.raises(wrapper.WrapperError) as e:
            wrapper.write(root, INV, pkg, None)
    finally:
        nm.chmod(0o700)
    assert str(nm) in str(e.value)


def _run_config(tmp_path, user_source, spool=None):
    """Import the generated config under a stub `vitest/config`.

    `mergeConfig` records each call and returns a marked object, so the
    test sees which configs received a layer and does not need vitest.
    """
    root, pkg = consumer(tmp_path), fake_pkg(tmp_path)
    (pkg / "src" / "vite.mjs").write_text(
        "export default function sensorium(opts) {"
        " return { name: 'sensorium', opts }; }\n")
    vitest = root / "node_modules" / "vitest"
    vitest.mkdir(parents=True)
    # Node ESM resolves the extensionless `vitest/config` only through exports.
    (vitest / "package.json").write_text(
        '{"type": "module", "exports": {"./config": "./config.js"}}\n')
    (vitest / "config.js").write_text(
        "export const calls = [];\n"
        "export function mergeConfig(a, b) {\n"
        "  calls.push(b);\n"
        "  return { __merged: true, base: a, layer: b };\n"
        "}\n")
    user = root / "vitest.config.js"
    user.write_text(user_source)
    config = root / "wrap.mjs"
    config.write_text(wrapper.config_text(root, INV, pkg, user))
    env = os.environ.copy()
    if spool is not None:
        env["SENSORIUM_SPOOL"] = str(spool)
    else:
        env.pop("SENSORIUM_SPOOL", None)
    return subprocess.run(
        ["node", "--input-type=module", "-e",
         "import cfg from " + json.dumps(config.as_uri()) + ";\n"
         "import { calls } from 'vitest/config';\n"
         "console.log(JSON.stringify({ out: cfg, calls: calls.length }));\n"],
        cwd=root, capture_output=True, text=True, env=env)


def test_inline_projects_each_receive_a_layer_and_the_root_does_not(tmp_path):
    """Vitest 4 does not pass a root plugin into a project. Each inline
    object is merged with its own layer, and the root is not, so a project
    that extends the root is not instrumented twice."""
    r = _run_config(tmp_path, """
export default {
  test: {
    projects: [
      { test: { name: 'alpha', include: ['a.test.ts'] } },
      { test: { name: 'beta' } },
    ],
  },
};
""")
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert got["calls"] == 2
    projects = got["out"]["test"]["projects"]
    assert len(projects) == 2
    assert all(p["__merged"] and p["layer"]["plugins"][0]["name"] == "sensorium"
               for p in projects)
    assert "plugins" not in got["out"]


def test_a_string_project_is_refused_and_a_leaf_config_is_wrapped(tmp_path):
    spool = tmp_path / "spool"
    refused = _run_config(tmp_path, """
export default { test: { projects: ['./vitest.config.unit.ts'] } };
""", spool=spool)
    assert refused.returncode != 0
    assert "config-file projects are not supported" in refused.stderr
    assert "Inline project objects are instrumented" in refused.stderr
    reason = json.loads((spool / "wrapper-refusal.json").read_text())["reason"]
    assert reason == wrapper.PROJECTS_REFUSAL

    leaf = _run_config(tmp_path / "leaf", """
export default { test: { include: ['a.test.ts'] } };
""")
    assert leaf.returncode == 0, leaf.stderr
    got = json.loads(leaf.stdout)
    assert got["calls"] == 1
    assert got["out"]["__merged"] is True
    assert got["out"]["layer"]["test"]["setupFiles"]
