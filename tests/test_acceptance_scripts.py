"""E-branch: do the acceptance instruments run the branch's own binary, and
does only the assembler mint the lens label? (S5 rung 3, spec 4.3, plan P9.)

Rung 2 found two ways an acceptance instrument could publish a number that
was never about this branch:

* **the wrong binary.** Three `.py` instruments (`e11_report.py`,
  `firstuse.py`, `reported.py`) spawned the bare word `sensorium`, which
  resolves through `PATH` to whatever is globally installed -- `main`'s
  tool, not this branch's, whenever a caller forgot to override
  `SENSORIUM_BIN`. Six `.sh` instruments carried the same hazard as a
  default: `SENSORIUM_BIN="${SENSORIUM_BIN:-sensorium}"`. `bin.sh` and
  `lens.sensorium_bin()` remove the default rather than fix the caller: the
  branch's own `.venv/bin/sensorium`, or a refusal naming the path.
* **the wrong label.** `lens.cell()` used to embed `LENS.txt`'s CONTENT at
  MEASUREMENT time -- whatever the file said at the moment an instrument
  happened to run, not necessarily the rung that instrument was measuring
  for. Six committed cells carry another rung's label because of exactly
  this. `cell()` no longer embeds one; `lens.stamp()` adds it once, at
  ASSEMBLY time, to a whole record at once, and refuses (in `strict` mode) a
  cell that arrives already carrying its own.

Nothing here runs vitest, ingests a trace, or touches a store: every check is
static (source text, an AST walk, or `bin.sh` sourced against a throwaway
`tmp_path` repo). The scripts this walks are `typescript/acceptance/*.sh` and
`*.py`, enumerated from `git ls-files` so an untracked scratch file cannot
widen or narrow what the gate covers.

Scope on (a): spec 4.3 governs -- "every script under `typescript/
acceptance/` that invokes `sensorium`" -- not the T0 census, which pinned
the state found at the time and does not bound what this task fixes. Every
tracked `.sh` is walked; a script "invokes sensorium" when it either
references `$SENSORIUM_BIN` or contains a bare `sensorium <subcommand>`
call, and every such script must source `bin.sh` and must contain neither
the insecure default nor a bare invocation. Ten scripts qualify: the T0
census's six (`arms.sh`, `e10p.sh`, `e3.sh`, `e6pp.sh`, `e6tsp.sh`, `e7.sh`)
plus four earlier rungs' frozen instruments that called the bare word with
no `SENSORIUM_BIN` concept at all (`e10.sh`, `e11.sh`, `e5ts_split.sh`,
`planted_change.sh`) -- fixed the same way, sourcing `bin.sh` and calling
`"$SENSORIUM_BIN"`, though none of them is re-run here. `e10p_eq.sh` (takes
BOTH converters as explicit command-line arguments, by design, to compare
main's against a slice's) and `e6.sh` (checks for a leftover
`node_modules/.sensorium` FILE, not a command) mention the word but invoke
nothing -- they are not in the ten, and stay as they are.

Every test states the failure it would catch.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"

sys.path.insert(0, str(ACCEPT))
import lens  # noqa: E402


def _tracked(pattern: str) -> tuple[str, ...]:
    """Tracked files matching `pattern`, repo-relative. Skips the module
    rather than reporting an empty (falsely green) enumeration when `git`
    cannot answer."""
    proc = subprocess.run(["git", "ls-files", "--", pattern], cwd=REPO,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip(f"git ls-files failed: {proc.stderr.strip()}",
                     allow_module_level=True)
    paths = tuple(p for p in proc.stdout.splitlines() if p)
    if not paths:
        pytest.skip(f"git ls-files found nothing for {pattern!r}",
                     allow_module_level=True)
    return paths


SH_FILES = _tracked("typescript/acceptance/*.sh")
PY_FILES = _tracked("typescript/acceptance/*.py")

#: The CLI's own subcommands, as this directory's instruments call them
#: (`sensorium <word>`, or `sensorium ts <word>`). Used only to keep the
#: bare-invocation regex below off decorative text -- `.venv/bin/sensorium`
#: in a comment, `node_modules/.sensorium` as a filename, `sensorium` as a
#: Python package name -- none of which is followed by one of these.
SUBCOMMANDS = ("ts", "diff", "info", "tree", "frame", "grep", "exceptions",
              "watch", "flow", "runs", "refocus")

#: A bare shell invocation: `sensorium` not immediately preceded by `.`, a
#: word character or `$` (which rules out `.sensorium`, `SENSORIUM_BIN`,
#: `SENSORIUM_DIR` and `$sensorium`), followed by whitespace and one of the
#: CLI's own words.
BARE_INVOCATION = re.compile(
    r"(?<![.\w$])\bsensorium\b\s+(?:" + "|".join(SUBCOMMANDS) + r")\b")


def _code_lines(text: str) -> list[str]:
    """Every line that is not a whole-line shell comment. A `#` this
    directory ever uses for real code appears mid-line inside a quoted
    string (`'#...'`), never as an executable token, so dropping
    comment-only lines is enough -- no line in these six scripts has both
    live code and a trailing `#` comment."""
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def _is_print_line(line: str) -> bool:
    """A `printf`/`echo` call, once any leading `{` or `(` grouping is
    stripped. These print a LABEL for a transcript (`$ sensorium exceptions
    ...`) -- decorative text, not a command this shell executes -- so the
    bare-invocation check below does not read their argument as a spawn."""
    return line.lstrip().lstrip("{(").lstrip().startswith(("printf", "echo"))


def _invokes_sensorium(text: str) -> bool:
    """True when a `.sh` file's CODE (not its comments) either resolves
    `$SENSORIUM_BIN` or calls the bare word directly -- the two shapes rung
    2 found, and the only two ways a shell instrument in this directory has
    ever run the CLI. A file that only mentions the word (`.venv/bin/
    sensorium` in prose, `node_modules/.sensorium` as a filename, `sensorium
    diff <a> <b>` inside a doc comment) does not invoke anything."""
    lines = _code_lines(text)
    return any("SENSORIUM_BIN" in ln or BARE_INVOCATION.search(ln)
              for ln in lines)


def _scripts_that_invoke_sensorium() -> list[str]:
    """Every tracked `.sh` that invokes `sensorium` at all -- spec 4.3's
    "every script", not the T0 census's six. `bin.sh` itself is excluded:
    it DEFINES `$SENSORIUM_BIN` and is not a caller of its own rule."""
    return [p for p in SH_FILES if Path(p).name != "bin.sh"
           and _invokes_sensorium((REPO / p).read_text(encoding="utf-8"))]


# -- (a) every .sh resolves the branch's binary, or refuses --------------


def test_the_insecure_default_is_gone_everywhere():
    """Catches: the historical default reappearing in ANY tracked `.sh`,
    inside this rung's census or out of it -- the string itself, not just
    its use, is what rung 2's finding names."""
    offenders = [p for p in SH_FILES
                if "SENSORIUM_BIN:-sensorium" in (REPO / p).read_text(encoding="utf-8")]
    assert offenders == [], f"still defaults to the global tool: {offenders}"


def test_every_sh_file_that_invokes_sensorium_sources_bin_sh():
    """Catches: a script that resolves `$SENSORIUM_BIN` or calls the bare
    word (either the census's six or the four fixed in pre-review) without
    going through the one place that refuses -- `bin.sh`. Spec 4.3 governs:
    EVERY script that invokes `sensorium`, not the T0 census alone."""
    users = _scripts_that_invoke_sensorium()
    assert len(users) >= 10, f"expected at least the ten known users, got: {users}"
    missing = [p for p in users
              if not re.search(r'^\s*\.\s+"\$HERE/bin\.sh"\s*$',
                                (REPO / p).read_text(encoding="utf-8"),
                                re.MULTILINE)]
    assert missing == [], f"invokes sensorium without sourcing bin.sh: {missing}"


def test_no_bare_sensorium_invocation_anywhere_it_is_invoked():
    """Catches: a script that sources `bin.sh` for the default case but
    still calls the bare word directly on one line -- the half-fixed script
    that made the rung-2 finding a partial fix rather than a closed one.
    Walks every script that invokes `sensorium` at all, not just the T0
    census's six."""
    offenders = {}
    for p in _scripts_that_invoke_sensorium():
        lines = _code_lines((REPO / p).read_text(encoding="utf-8"))
        hits = [ln.strip() for ln in lines
               if not _is_print_line(ln) and BARE_INVOCATION.search(ln)]
        if hits:
            offenders[p] = hits
    assert offenders == {}, f"bare `sensorium` invocation(s): {offenders}"


# -- (b) every .py resolves the branch's binary, or refuses --------------


def _bare_argv0_spawns(tree: ast.Module) -> list[int]:
    """Line numbers of every `subprocess.run`/`Popen`/... call whose first
    argument is a list or tuple literally starting with `"sensorium"`."""
    spawners = {"run", "Popen", "call", "check_call", "check_output"}
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else (
            func.id if isinstance(func, ast.Name) else None)
        if name not in spawners or not node.args:
            continue
        first = node.args[0]
        if not isinstance(first, (ast.List, ast.Tuple)) or not first.elts:
            continue
        head = first.elts[0]
        if isinstance(head, ast.Constant) and head.value == "sensorium":
            hits.append(node.lineno)
    return hits


def test_no_py_file_spawns_the_bare_sensorium_argv0():
    """Catches: the exact rung-2 finding -- `subprocess.run(["sensorium",
    ...])` with no override, which runs whatever is on `PATH`. The fix is
    `[lens.sensorium_bin(), ...]`, which this AST walk cannot mistake for
    the literal because `sensorium_bin()` is a Call, not a Constant."""
    offenders = {}
    for p in PY_FILES:
        source = (REPO / p).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=p)
        hits = _bare_argv0_spawns(tree)
        if hits:
            offenders[p] = hits
    assert offenders == {}, f"bare sensorium argv[0] at: {offenders}"


# -- (c) only the assembler mints the lens label --------------------------


def test_lens_key_literal_is_written_only_by_lens_and_the_assemblers():
    """Catches: an instrument that mints its own `"lens"` field -- the
    other half of rung 2's finding, and the one `lens.stamp(strict=True)`
    exists to refuse when it happens at assembly time instead of being
    caught here, in source, first."""
    pattern = re.compile(r'["\']lens["\']\s*:')
    offenders = []
    for p in PY_FILES:
        name = Path(p).name
        if name == "lens.py" or name.startswith("assemble"):
            continue
        if pattern.search((REPO / p).read_text(encoding="utf-8")):
            offenders.append(p)
    assert offenders == [], f"writes its own lens key: {offenders}"


# -- (d) bin.sh's refusal, sourced standalone ------------------------------


def _fake_repo(tmp_path: Path) -> Path:
    """A tmp copy of just enough tree for `bin.sh` to compute a repo root
    two parents above itself, matching the real layout."""
    accept = tmp_path / "typescript" / "acceptance"
    accept.mkdir(parents=True)
    (accept / "bin.sh").write_text(
        (ACCEPT / "bin.sh").read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _source_bin_sh(fake_root: Path) -> subprocess.CompletedProcess:
    script = fake_root / "typescript" / "acceptance" / "bin.sh"
    return subprocess.run(
        ["bash", "-c", f'source "{script}" && printf \'resolved:%s\' "$SENSORIUM_BIN"'],
        capture_output=True, text=True)


def test_bin_sh_refuses_when_the_venv_binary_is_absent(tmp_path):
    """Catches: a `bin.sh` that only checks `realpath`'s prefix and forgets
    the executable has to exist at all -- there is no `.venv` here."""
    fake_root = _fake_repo(tmp_path)

    proc = _source_bin_sh(fake_root)

    assert proc.returncode == 3, proc.stderr
    assert "refused: sensorium resolves to" in proc.stderr
    assert str(fake_root) in proc.stderr


def test_bin_sh_refuses_when_the_binary_escapes_the_repo_root(tmp_path):
    """Catches: a `bin.sh` that checks executability but not `realpath` --
    a symlink under `.venv/bin/` pointing outside the tree it claims to be
    the branch's own."""
    fake_root = _fake_repo(tmp_path)
    venv_bin = fake_root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    outside = tmp_path.parent / "outside-sensorium"
    outside.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    outside.chmod(0o755)
    (venv_bin / "sensorium").symlink_to(outside)

    proc = _source_bin_sh(fake_root)

    assert proc.returncode == 3, proc.stderr
    assert "refused: sensorium resolves to" in proc.stderr


def test_bin_sh_resolves_an_executable_inside_the_root(tmp_path):
    """The positive control: a real, in-tree `.venv/bin/sensorium` is
    accepted rather than always refusing regardless of input."""
    fake_root = _fake_repo(tmp_path)
    venv_bin = fake_root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    binary = venv_bin / "sensorium"
    binary.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    binary.chmod(0o755)

    proc = _source_bin_sh(fake_root)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == f"resolved:{binary}"


# -- (e) lens.sensorium_bin(), in this worktree ----------------------------


def test_lens_sensorium_bin_resolves_under_this_repo_root():
    """This worktree carries a real editable `.venv`, so the branch's own
    rule should resolve rather than refuse -- and the path it returns must
    sit under the repo root, not merely exist somewhere."""
    resolved = lens.sensorium_bin()

    assert resolved.startswith(str(REPO) + "/")
    assert Path(resolved).is_file()
    assert Path(resolved) == REPO / ".venv" / "bin" / "sensorium"
