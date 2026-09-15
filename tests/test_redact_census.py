"""The static census of BINDING names: every name the corpus programs, the
format vectors and the TypeScript spool fixtures bind that rule v1's NAME
rule fires on.

PR A censused the ENVIRONMENT (`tests/fixtures/benign-env-names.txt`, and
`test_census_fires_on_exactly_the_listed_subset` beside it): real variable
names, with the subset the rule is expected to fire on written out by hand.
PR B redacts captured VALUES, so the same question is put to the other
surface the rule is about to meet -- the names the recorders BIND and store:
a parameter, a local, a function whose qualname carries the segment, an
`args` key in a format vector, a delta name in a spool fixture.

`tests/fixtures/corpus-firing-names.txt` is that list, one
`<repo-relative path>: <name>` per line. Every line is a binding this branch
will render as the redaction marker instead of its value, so every line was
READ once, in Task 0, before any renderer moved: a case whose QUESTION is
about the name keeps it (the expectation moves with the rule, in the tasks
that change the renderers), and a case that merely happened to spell a local
`key` was renamed there and then -- so the later tasks meet a list rather
than a surprise.

The scan is STATIC: it parses and greps sources and runs no program. That is
what lets it be the thing that fails when a new corpus case lands carrying a
secret-shaped name, months after anyone remembers this rule exists.

WHAT THIS SCAN IS NOT
---------------------
It is not a parser for three languages. Python is read with `ast` and is
exact; TypeScript and Rust are read with the small regex tables below, which
are deliberately GENEROUS -- a name they over-report costs one line in the
fixture that a reader dismisses, while a name they miss is the surprise this
census exists to prevent. Every firing word in these trees was cross-checked
once, by hand, against a whole-word grep of the same files.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from sensorium import redact
from sensorium.redact import Knobs

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "corpus-firing-names.txt"

#: The rule as an unconfigured recorder runs it -- no `SENSORIUM_REDACT_*`
#: knob amends the judgement the fixture records.
PLAIN = Knobs(False, frozenset(), frozenset())

#: The command that writes the fixture, named in its header too.
HARVEST = ("python tests/test_redact_census.py "
           "> tests/fixtures/corpus-firing-names.txt")

#: Directory names a scan never descends into: built artefacts and vendored
#: code bind names this repository did not write and cannot rename.
SKIP = frozenset({"node_modules", "target", "__pycache__", ".venv", "dist"})

# -- the three languages -------------------------------------------------

#: A declaration's own name, a `catch` binding, and every parameter list --
#: one pattern each, applied to the whole source INDEPENDENTLY. A single
#: alternation cannot do this: `function parseKey(key: string)` matches the
#: declaration alternative, the scan resumes after `parseKey`, and the
#: parameter `key` is never seen.
_TS = (
    re.compile(r"\b(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\bcatch\s*\(\s*([A-Za-z_$][\w$]*)"),
    re.compile(r"\b([A-Za-z_$][\w$]*)\s*=>"),
)

#: A parameter list: the text between parentheses that is followed by an
#: arrow, a return-type annotation or a body. Catches a function
#: declaration's, a method's and an arrow's alike.
_TS_PARAMS = re.compile(r"\(([^()]*)\)\s*(?::\s*[^{;=]+)?\s*(?:=>|\{)")

#: A `let` (or `let mut`) binding, a function's own name, a `for` binding, a
#: pattern binding (`Some(k)`, `Ok(v) =>`) and every parameter list.
_RUST = (
    re.compile(r"\blet\s+(?:mut\s+)?([A-Za-z_]\w*)"),
    re.compile(r"\bfn\s+([A-Za-z_]\w*)"),
    re.compile(r"\bfor\s+(?:mut\s+)?([A-Za-z_]\w*)\s+in\b"),
    re.compile(r"\b(?:Some|Ok|Err)\s*\(\s*(?:mut\s+)?([a-z_]\w*)\s*\)"),
)

_RUST_PARAMS = re.compile(r"\bfn\s+[A-Za-z_]\w*\s*(?:<[^>]*>)?\s*\(([^()]*)\)")

#: One parameter's binding names: the identifier it opens with, plus each
#: word of a destructuring pattern. `...rest`, `mut x`, `{ member = false }`
#: and `items: number[]` all reduce to the names they bind.
_PARAM_NAME = re.compile(r"(?:^|[,{\[(]\s*)\s*(?:\.\.\.|mut\s+|&\s*)*"
                         r"([A-Za-z_$][\w$]*)")


def _python_names(src: str) -> list[str]:
    """Every name a Python module binds: a function's own name, every
    parameter, every `Name` in a store context (assignment, `for`, `with`,
    comprehension, walrus) and every `except ... as` name."""
    names = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.append(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.append(node.name)
    return names


def _regex_names(src: str, singles, params) -> list[str]:
    """The regex tables' answer for one TypeScript or Rust source: the
    single-name patterns, then every name inside every parameter list."""
    names = [m.group(1) for pattern in singles for m in pattern.finditer(src)]
    for match in params.finditer(src):
        for part in match.group(1).split(","):
            names.extend(_PARAM_NAME.findall(part))
    return names


def _json_keys(node, wanted: tuple[str, ...]) -> list[str]:
    """Every key of every `wanted` mapping anywhere under `node` -- a
    vector's `payload.args`/`payload.deltas`, a spool record's `a`/`d`."""
    names = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in wanted and isinstance(value, dict):
                names.extend(value)
            names.extend(_json_keys(value, wanted))
    elif isinstance(node, list):
        for value in node:
            names.extend(_json_keys(value, wanted))
    return names


def _files(root: Path, suffix: str):
    for path in sorted(root.rglob(f"*{suffix}")):
        if SKIP.isdisjoint(path.parts) and path.is_file():
            yield path


def _scan() -> set[tuple[str, str]]:
    """Every `(repo-relative path, bound name)` the rule fires on."""
    found: set[tuple[str, str]] = set()

    def take(path: Path, names) -> None:
        rel = path.relative_to(REPO).as_posix()
        found.update((rel, name) for name in names
                     if redact.fires(name, PLAIN))

    corpus = REPO / "corpus"
    for path in _files(corpus, ".py"):
        take(path, _python_names(path.read_text(encoding="utf-8")))
    for path in _files(corpus, ".ts"):
        take(path, _regex_names(path.read_text(encoding="utf-8"),
                                _TS, _TS_PARAMS))
    for path in _files(corpus / "rust", ".rs"):
        take(path, _regex_names(path.read_text(encoding="utf-8"),
                                _RUST, _RUST_PARAMS))
    for path in _files(REPO / "docs" / "trace-format" / "vectors", ".json"):
        take(path, _json_keys(json.loads(path.read_text(encoding="utf-8")),
                              ("args", "deltas")))
    for path in _files(REPO / "tests" / "fixtures" / "ts-spools", ".jsonl"):
        names = []
        for line in path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
            try:
                names.extend(_json_keys(json.loads(line), ("a", "d")))
            except ValueError:
                continue  # a torn-spool fixture; its whole records still read
        take(path, names)
    return found


def _listed() -> set[tuple[str, str]]:
    """The fixture's lines, `#` header dropped."""
    pairs = set()
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        path, _, name = line.partition(": ")
        pairs.add((path.strip(), name.strip()))
    return pairs


def _render(pairs: set[tuple[str, str]]) -> str:
    header = (f"# Every binding name in corpus/, docs/trace-format/vectors/ "
              f"and tests/fixtures/ts-spools/\n"
              f"# that rule v1's NAME rule fires on -- so PR B's renderers "
              f"meet a list, not a surprise.\n"
              f"# Harvested by: {HARVEST}\n")
    return header + "".join(f"{path}: {name}\n"
                            for path, name in sorted(pairs))


def test_the_name_rule_fires_on_exactly_the_listed_binding_names():
    """Catches: a corpus case, vector or spool fixture that grows a
    secret-shaped binding name after this branch taught the recorders to
    redact by name -- a value that silently stops being in the recording
    while a question still expects to read it."""
    found = _scan()
    listed = _listed()
    assert found == listed, (
        f"unlisted: {sorted(found - listed)}\n"
        f"gone: {sorted(listed - found)}\n"
        f"re-harvest with: {HARVEST}")


def test_the_census_file_holds_paths_and_names_and_no_box_paths():
    """A fixture harvested with absolute paths would pin this list to one
    machine's checkout."""
    text = FIXTURE.read_text(encoding="utf-8")
    assert "/mnt/" not in text and "/home/" not in text
    assert text == _render(_listed()), f"not the harvest's own shape: {HARVEST}"


if __name__ == "__main__":  # the harvest, run from the repository root
    print(_render(_scan()), end="")
