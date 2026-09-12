"""What `--focus` selected, settled before the run.

The driver cannot answer a focus itself: which functions a spec selects is a
property of the consumer's own AST, read with the consumer's own TypeScript,
by the same pass one the transform splices from. So it asks the recorder's
Node package -- `src/resolve.mjs`, one process, one JSON line -- and turns
what comes back into either a list of matches or a list of refusals.

The refusal is the reason this happens BEFORE anything is minted. A spec
that matches nothing splices no probes at all, and the run that follows
records a program the caller did not ask about while declaring it looked; a
spec that matches only a function this recorder never instruments (an
overload signature, a `declare`, a vitest-hoisted factory) does the same and
is not the caller's spelling mistake at all. Both are cheap to say up front
and expensive to discover in a trace.
"""
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from sensorium.ts import pkg as pkg_mod

#: The unit separator the specs are joined with on their way to the harness
#: and to the resolver. A spec may hold a path, a dot and a colon; this is the
#: one byte it cannot. `typescript/src/focus.mjs` splits on the same one.
SEP = "\x1f"

#: The resolver, inside the package. Named here rather than built at the call
#: site so the refusal for its absence can name it too.
SCRIPT = Path("src") / "resolve.mjs"


@dataclass(frozen=True)
class Resolution:
    """What the resolver saw: what each spec selected, and what it walked.

    `matched` is one entry per FUNCTION (`rel`, `qualname`, `line`, `kind`),
    deduplicated across specs -- two specs naming one function focus it once.
    `unmatched` and `excluded_only` are one entry per bad SPEC, each carrying
    the spec as typed so the refusal can quote it back.
    """

    matched: list[dict]
    unmatched: list[dict]
    excluded_only: list[dict]
    files_scanned: int
    files_unparsable: int
    wall: float

    @property
    def matched_specs(self) -> list[str]:
        """`rel:qualname` for every match, sorted -- what `invocation.json`
        carries as `focus_matched` and what a reader is shown when they ask
        what a recording was focused on. Sorted and not in match order: it is
        a set of functions, and the order the walk happened to reach them in
        is not a fact about the recording.

        A set in the other sense too (R30). `matched` is one entry per
        FUNCTION, and two functions can share a `rel:qualname`: anonymous
        twins on one line are indistinguishable by name, and listing
        `src/a.ts:<anonymous>` twice answers nothing twice."""
        return sorted({f"{m['rel']}:{m['qualname']}" for m in self.matched})


def resolve(root: Path, package: Path, specs: list[str],
            node: str = "node") -> Resolution:
    """Run the resolver over `root` and read its one line back.

    Raises `pkg.PackageError` -- the driver's existing refusal for "the Node
    side cannot be used" -- when the script is absent, cannot be started, or
    answers with anything but one JSON object at exit 0. The resolver itself
    treats an unmatched spec as an ANSWER and exits 0 with it; a non-zero
    exit means the call it was given made no sense, and its sentence is the
    one worth showing.
    """
    script = Path(package) / SCRIPT
    if not script.is_file():
        raise pkg_mod.PackageError(
            f"the recorder's Node package at {package} has no {SCRIPT}: a "
            f"`--focus` is resolved against the project before the run, and "
            f"this package cannot answer one")
    env = dict(os.environ, SENSORIUM_TS_ROOT=str(root),
               SENSORIUM_TS_PKG=str(package), SENSORIUM_FOCUS=SEP.join(specs))
    start = time.perf_counter()
    try:
        out = subprocess.run([node, str(script)], env=env, cwd=root,
                             capture_output=True, text=True)
    except OSError as e:
        raise pkg_mod.PackageError(
            f"cannot run `{node} {script}`: {e.strerror}") from None
    wall = time.perf_counter() - start
    if out.returncode != 0:
        raise pkg_mod.PackageError(
            f"{script} refused: {_one_line(out.stderr) or f'exit {out.returncode}, nothing said'}")
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise pkg_mod.PackageError(
            f"{script} answered something this driver cannot read: "
            f"{_one_line(out.stdout) or 'nothing at all'}") from None
    return Resolution(matched=data["matched"], unmatched=data["unmatched"],
                      excluded_only=data["excluded_only"],
                      files_scanned=data["files_scanned"],
                      files_unparsable=data["files_unparsable"], wall=wall)


def _one_line(text: str) -> str:
    """The first thing said, on one line. Every refusal the driver prints is
    one line, and a Node stack trace pasted into it would bury the sentence
    the caller has to act on."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def refusals(res: Resolution, root: Path) -> list[str]:
    """One line per bad spec, or an empty list when every spec selected
    something.

    Two sentences, because they are two different problems. "Matches no
    function" is a spelling to fix, and the closest eligible names are what
    fixes it -- dropped, rather than printed empty, when there is nothing to
    suggest. "Matches only functions this recorder does not instrument" is
    not a spelling problem at all: the name IS in the tree, and the reason
    it cannot be recorded belongs to the recorder, so the reason is named.

    The unmatched come first and the excluded-only after; within each, the
    order is the order the specs were given.
    """
    lines = []
    for item in res.unmatched:
        tail = (f" Closest: {', '.join(item['closest'])}"
                if item["closest"] else "")
        lines.append(f"--focus {item['spec']} matches no function under "
                     f"{root}; nothing was run.{tail}")
    for item in res.excluded_only:
        reasons = ", ".join(f"{k} x{n}"
                            for k, n in sorted(item["reasons"].items()))
        lines.append(f"--focus {item['spec']} matches only functions this "
                     f"recorder does not instrument ({reasons}); nothing was "
                     f"run.")
    return lines
