"""E-legacy and E-branch: the two fences that run before the re-read.

    .venv/bin/python typescript/acceptance/e_fences.py <base sha> <out dir>

P12 orders them first for one reason: a fence that failed AFTER the single
re-read would have tainted a number already read, and a rung cannot unread
one. So both are measured here, their cells written, and only then does
`e6tsppp.py` open the store.

E-LEGACY is two claims and both are checked:

  * the fenced files show ZERO diff against the branch point -- the Rust and
    Python readers, the whole `rust/` tree and their tests. `git diff --stat`
    over exactly those paths, empty;
  * their tests are green, plus `test_exceptions_typescript_grouping.py::
    test_the_rust_key_is_todays_tuple_verbatim`, which states the Rust key as
    a TUPLE EQUALITY rather than as prose -- the one check that a rung-3
    rewrite of the grouper could not talk its way past.

The fence names files that exist. The pre-registration spelled the Python
reader's tests `tests/test_exceptions_python*.py`, and no file in this tree
has ever been spelled that way -- the reader
(`src/sensorium/query/exceptions.py`) is tested by `test_exceptions.py` and
`test_exceptions_synthetic.py`. Until 2026-09-11 the phantom pattern was kept
above, matching nothing and saying so in `dropped`, with the two real files
run BESIDE the gate and only REPORTED. Both are inside the fence now, and
`existing()` refuses at exit 2 on any pattern that matches no file: a fence
over an empty set is not a fence, and one that reports what it declines to
gate is a fence in name only.

E-BRANCH is `tests/test_acceptance_scripts.py`: do the instruments run THIS
branch's binary, and does only the assembler mint the lens label. It gates
the instruments that take every other number in this rung, which is why it
is read before any of them and not after.

Both cells are `{value, n, dropped}` with the instrument's own recorder: the
value is how many of the cell's claims held, out of how many were made, so a
reader sees `2 of 2` rather than a bare `true` whose population is invisible.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from lens import REPO_ROOT, cell, emit, usage

#: The Global Constraints' fence: the files rung 3 promised not to move a
#: byte of. Spelled as the constraints spell them, except that the Python
#: reader's tests are named (`test_exceptions.py`,
#: `test_exceptions_synthetic.py`) where the pre-registration's
#: `tests/test_exceptions_python*.py` named nothing -- see the docstring.
FENCED = ("src/sensorium/query/exceptions_rust.py",
          "src/sensorium/query/exceptions.py",
          "rust/",
          "tests/test_exceptions_rust*.py",
          "tests/test_exceptions_invocation.py",
          "tests/test_exceptions.py",
          "tests/test_exceptions_synthetic.py")

#: The fenced tests, as GLOBS where the Global Constraints spell one, so a
#: fenced test file added since the branch point is run rather than silently
#: left out of the fence it belongs to. The last two are the Python reader's
#: own tests, named (see the docstring) rather than left to a pattern that
#: matched nothing.
FENCED_TESTS = ("tests/test_exceptions_rust*.py",
                "tests/test_exceptions_invocation.py",
                "tests/test_exceptions.py",
                "tests/test_exceptions_synthetic.py")

KEY_FENCE = ("tests/test_exceptions_typescript_grouping.py"
             "::test_the_rust_key_is_todays_tuple_verbatim")

BRANCH_TEST = "tests/test_acceptance_scripts.py"


def run(cmd: list[str]) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("SENSORIUM_MANIFEST_DIR", "SENSORIUM_SPOOL")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                          env=env)
    tail = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()]
    return {"command": " ".join(cmd), "exit": proc.returncode,
            "stdout": proc.stdout, "last_line": tail[-1] if tail else ""}


def existing(patterns) -> list[str]:
    """The fenced test files, expanded from their globs. A pattern that
    matches nothing REFUSES the whole run at exit 2, naming the pattern:
    the fence's population is what makes it a fence, and a fence that
    quietly measures a smaller set than it names passes forever."""
    out = []
    for pattern in patterns:
        hits = sorted(str(p.relative_to(REPO_ROOT))
                      for p in REPO_ROOT.glob(pattern))
        if not hits:
            sys.stderr.write(
                f"refused: fence pattern {pattern!r} matches no file\n")
            raise SystemExit(2)
        out += hits
    return out


def legacy(base: str) -> dict:
    diff = run(["git", "diff", f"{base}..HEAD", "--stat", "--"] + list(FENCED))
    tests = existing(FENCED_TESTS)
    suite = run([".venv/bin/python", "-m", "pytest", "-q",
                 "-p", "no:cacheprovider"] + tests + [KEY_FENCE])
    changed = [ln for ln in diff["stdout"].splitlines() if ln.strip()]
    claims = {"the fenced files show zero diff against the branch point":
                  not changed and diff["exit"] == 0,
              "the fenced tests and the Rust key's tuple equality are green":
                  suite["exit"] == 0}
    return cell(sum(1 for v in claims.values() if v), len(claims), [],
                rule=("byte-unchanged against the branch point, tests green "
                      "-> else STOP"),
                base=base, claims=claims, fenced_paths=list(FENCED),
                diff_stat_lines=changed, diff=diff,
                tests_run=tests + [KEY_FENCE], suite=suite,
                recorder=os.environ.get("E_FENCES_RECORDER"),
                recorder_rev=os.environ.get("E_FENCES_REV"))


def branch() -> dict:
    suite = run([".venv/bin/python", "-m", "pytest", "-q",
                 "-p", "no:cacheprovider", BRANCH_TEST])
    claims = {f"{BRANCH_TEST} is green": suite["exit"] == 0}
    return cell(sum(1 for v in claims.values() if v), len(claims), [],
                rule="green -> else STOP",
                claims=claims, suite=suite,
                recorder=os.environ.get("E_FENCES_RECORDER"),
                recorder_rev=os.environ.get("E_FENCES_REV"))


def main(argv) -> int:
    if len(argv) != 3:
        usage("usage: e_fences.py <base sha> <out dir>")
    out = Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    cells = {"e-legacy.json": legacy(argv[1]), "e-branch.json": branch()}
    for name, payload in cells.items():
        (out / name).write_text(json.dumps(payload, indent=2) + "\n",
                                encoding="utf-8")
    emit({name: {"value": c["value"], "n": c["n"], "dropped": c["dropped"],
                 "claims": c["claims"]} for name, c in cells.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
