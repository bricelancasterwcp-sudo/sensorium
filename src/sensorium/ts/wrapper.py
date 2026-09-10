"""The two files the driver puts in the consumer's tree, and takes away.

They live under `<root>/node_modules/.sensorium/` (D9) and nowhere else: a
wrapper config has to sit under a `node_modules` for its own bare imports
(`vitest/config`) to resolve from the consumer's tree, `node_modules` is
gitignored by every project, and nothing there is a source file anybody
edits. Both are named by the invocation, so two runs of one project do not
share a file, and both are removed in the driver's `finally`.

Three rules the text obeys, each of them a measured hazard:

* the runtime is declared external as a **RegExp** (R16). `server.deps.external`
  matches a STRING entry only as `<moduleDirectory>/<entry>` -- vitest joins
  it onto `/node_modules/` -- so an absolute path written as a string matches
  nothing at all, and the run silently gets two runtimes: one through Vite's
  module runner for the instrumented modules, one native for the setup file;
* every path is spelled ABSOLUTELY, the package included. The package's
  `exports` map has no `./src/*` entry, so a bare `sensorium-ts/src/vite.mjs`
  would not resolve, and a relative path would be relative to a directory
  the consumer chose;
* a user config exported as a FUNCTION is called with vitest's own
  `ConfigEnv` before the merge, because `mergeConfig` merges objects and
  would otherwise be handed a function.

`mergeConfig` appends to `setupFiles` and `plugins` rather than replacing
them: the consumer's setup assumes their own environment, and that is the
consumer's business (design section 2.2).

The config also REFUSES one shape by name (R41). A `test.projects` or
`test.workspace` config makes vitest run each project with its own
resolved config, and this wrapper merges onto ONE: the plugin never
reaches the projects' pipelines, so the suite runs and nothing is
recorded. Measured, that ended as the converter's own sentence -- "no
spools in <dir>: nothing was recorded, or the recorder wrote somewhere
else" -- which names neither the cause nor the fix. So the config throws,
and writes `wrapper-refusal.json` into the spool directory on the way out:
vitest's own error goes to the harness's stderr, where it is one line
among a config trace, and the driver needs the sentence to give back as
its own refusal.
"""
import json
from pathlib import Path

#: The directory both files live in, under the consumer's `node_modules`.
DIRNAME = ".sensorium"
CONFIG_SUFFIX = ".config.mts"
SETUP_SUFFIX = ".setup.mjs"

#: What `typescript/src/setup.mjs` carries where the package's path goes.
PLACEHOLDER = "__PKG__"

#: What the wrapper config leaves in the spool directory when it refuses,
#: and the sentence it refuses with. Read by the driver, which has nothing
#: else to go on: a config that threw wrote no spool.
REFUSAL_FILE = "wrapper-refusal.json"
PROJECTS_REFUSAL = ("vitest projects/workspaces are not supported by "
                    "sensorium-ts 0.2.0")

#: Every character a JavaScript RegExp literal gives a meaning to, `/`
#: included -- it ends the literal.
META = ".*+?^${}()|[]\\/"


class WrapperError(Exception):
    """The wrapper cannot be written. Always names the directory (D9): the
    caller's next move is to look at its permissions."""


#: The four characters JavaScript counts as line terminators, none of
#: which may appear raw inside a single-quoted string. LF and CR are the
#: obvious two; U+2028 and U+2029 are invisible in every editor and legal
#: in a POSIX filename, which is exactly what makes them worth escaping.
LINE_TERMINATORS = (("\n", "\\n"), ("\r", "\\r"),
                    ("\u2028", "\\u2028"), ("\u2029", "\\u2029"))


def js_string(text: str) -> str:
    """`text` inside a single-quoted JavaScript string. The backslash goes
    first, or the escape this adds would itself be escaped."""
    out = text.replace("\\", "\\\\").replace("'", "\\'")
    for raw, escape in LINE_TERMINATORS:
        out = out.replace(raw, escape)
    return out


def js_regexp(text: str) -> str:
    """`text` matched literally inside a `/.../` RegExp."""
    return "".join("\\" + c if c in META else c for c in text)


def home(root: Path) -> Path:
    return Path(root) / "node_modules" / DIRNAME


#: The refusal, spelled once, in the config's own words. Four spellings,
#: because vitest has read the list from `test.projects` and from
#: `test.workspace`, and a root-level `projects`/`workspace` is the shape a
#: consumer writes by mistake -- refusing a config we cannot instrument is
#: right whichever of the four it is.
REFUSAL_BLOCK = (
    "const projects = resolved?.test?.projects ?? resolved?.test?.workspace\n"
    "  ?? resolved?.projects ?? resolved?.workspace;\n"
    "if (projects !== undefined) {\n"
    f"  const reason = '{PROJECTS_REFUSAL}';\n"
    "  const spool = process.env.SENSORIUM_SPOOL;\n"
    "  if (spool) {\n"
    "    fs.mkdirSync(spool, { recursive: true });\n"
    f"    fs.writeFileSync(path.join(spool, '{REFUSAL_FILE}'), "
    "JSON.stringify({ reason }));\n"
    "  }\n"
    "  throw new Error(reason);\n"
    "}\n")


def refusal(spool) -> str | None:
    """What the wrapper config refused, or None if it did not.

    Never raises: this is read on a path where something has ALREADY gone
    wrong, and a second failure here would replace the sentence the caller
    came for with one about a file it has no reason to care about.
    """
    try:
        data = json.loads(
            (Path(spool) / REFUSAL_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    reason = data.get("reason") if isinstance(data, dict) else None
    return reason if isinstance(reason, str) and reason else None


def config_text(root, invocation: str, pkg_dir, user_config) -> str:
    """The wrapper config, exactly as it is written."""
    root, pkg_dir = Path(root), Path(pkg_dir)
    rt = js_string(f"{pkg_dir}/src/rt.mjs")
    pkg = js_string(str(pkg_dir))
    here = js_string(str(root))
    setup = js_string(str(home(root) / f"{invocation}{SETUP_SUFFIX}"))
    base = ("" if user_config is None
            else f"import base from '{js_string(str(user_config))}';\n")
    return (
        f"// written by sensorium ts run for invocation {invocation}; "
        "removed when it exits\n"
        "import fs from 'node:fs';\n"
        "import path from 'node:path';\n"
        "import { mergeConfig } from 'vitest/config';\n"
        f"import sensorium from '{pkg}/src/vite.mjs';\n"
        f"{base}"
        f"const user = {'base' if user_config is not None else '{}'};\n"
        "const resolved = typeof user === 'function' "
        "? await user({ command: 'serve', mode: 'test' }) : user;\n"
        + REFUSAL_BLOCK +
        "export default mergeConfig(resolved, {\n"
        f"  root: '{here}',\n"
        f"  plugins: [sensorium({{ root: '{here}', pkgDir: '{pkg}', "
        f"rtPath: '{rt}' }})],\n"
        "  test: {\n"
        f"    setupFiles: ['{setup}'],\n"
        f"    server: {{ deps: {{ external: [/{js_regexp(rt)}/] }} }},\n"
        "  },\n"
        "});\n")


def setup_text(pkg_dir) -> str:
    """The package's setup template with its placeholder resolved.

    One template, two readings: the probes import the runtime by a relative
    path and need no driver, and a driven run gets this. Keeping them one
    text is what stops the driven wiring from drifting away from the wiring
    the probes assert against.
    """
    pkg_dir = Path(pkg_dir)
    template = (pkg_dir / "src" / "setup.mjs").read_text(encoding="utf-8")
    return template.replace(PLACEHOLDER, js_string(str(pkg_dir)))


def write(root, invocation: str, pkg_dir, user_config) -> tuple[Path, Path]:
    """Both files, or a refusal naming the directory that would not take
    them. A partial write is cleaned up here: the caller's `finally` sees
    the same two paths either way, but a config with no setup file beside it
    would make vitest fail about a file the consumer never wrote."""
    root = Path(root)
    config = home(root) / f"{invocation}{CONFIG_SUFFIX}"
    setup = home(root) / f"{invocation}{SETUP_SUFFIX}"
    try:
        home(root).mkdir(parents=True, exist_ok=True)
        setup.write_text(setup_text(pkg_dir), encoding="utf-8")
        config.write_text(config_text(root, invocation, pkg_dir, user_config),
                          encoding="utf-8")
    except OSError as e:
        remove((config, setup))
        raise WrapperError(
            f"cannot write this run's config into {root / 'node_modules'}: "
            f"{e}; the wrapper has to live under node_modules for "
            "`vitest/config` to resolve from your tree") from None
    return config, setup


def remove(paths) -> None:
    """Both files, then the directories that are now empty.

    Runs in a `finally`, so it also runs over paths a failed write never
    created and must not turn one failure into two. It stops at the first
    directory that still holds something: a second invocation of the same
    project has its own two files in there, and `node_modules` itself is
    empty only when this driver is what made it.
    """
    paths = list(paths)
    for path in paths:
        Path(path).unlink(missing_ok=True)
    if not paths:
        return
    directory = Path(paths[0]).parent
    for _ in range(2):                       # .sensorium, then node_modules
        try:
            directory.rmdir()
        except OSError:
            return
        directory = directory.parent
