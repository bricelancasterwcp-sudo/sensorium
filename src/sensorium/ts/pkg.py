"""Where the Node library is, and whether this box can run it.

Two questions the driver has to settle BEFORE it mints an invocation or
spawns anything, because both of them have answers a recording cannot
recover from: a Node older than the one the recorder was measured on, and a
package that has never been installed. Each is a refusal with a sentence
naming the fix, and neither leaves a spool directory behind.

The package's location is one rule in one place (`locate`). `SENSORIUM_TS_PKG`
names it when the library lives somewhere else -- a wheel install beside a
checkout, a test pointing at an empty directory -- and otherwise it is the
`typescript/` directory beside `src/`, found from this module's own file.
The same variable is exported to the harness, so what the driver checked and
what the loader hook resolves are the same directory by construction.
"""
import os
import re
import subprocess
from pathlib import Path

import sensorium

#: The variable that names the package, and the only one. Read here and
#: exported to the harness by the driver.
ENV_VAR = "SENSORIUM_TS_PKG"

#: The Node the recorder was measured on (D2). Below it nothing was
#: measured, so nothing is claimed: the driver refuses rather than record a
#: run whose async semantics it has never seen.
NODE_FLOOR = 24

#: The one file whose presence says the package has been installed. The
#: transform bare-imports `magic-string`, so its absence is not a missing
#: nicety -- it is an `ERR_MODULE_NOT_FOUND` thrown deep inside a Vite
#: transform, minutes later, about a module the consumer never mentioned.
INSTALLED = Path("node_modules") / "magic-string"


class PackageError(Exception):
    """The Node side cannot be used, and the sentence says what to do."""


def locate() -> Path:
    """The `sensorium-ts` package directory.

    An EMPTY variable is not a location -- `or` and not a presence test, so
    `SENSORIUM_TS_PKG=` falls through to the checkout rather than resolving
    to the process's working directory.
    """
    return Path(os.environ.get(ENV_VAR)
                or Path(sensorium.__file__).resolve().parents[2] / "typescript")


def check(pkg: Path) -> None:
    """Refuse a package whose dependencies were never installed."""
    if not (pkg / INSTALLED).is_dir():
        raise PackageError(
            f"the recorder's Node package at {pkg} has no {INSTALLED}: "
            f"install it with `npm ci --prefix {pkg}`")


def version(pkg: Path) -> str:
    """The package's own version, for the `recorder` a spool without one
    falls back to (R5).

    Read as text rather than as JSON, and never an error: this is a
    FALLBACK, used only for a spool whose BOOT record did not name its own
    writer, and a manifest this cannot read is not a reason to refuse a
    recording that would otherwise happen.
    """
    try:
        text = (pkg / "package.json").read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    m = re.search(r'"version"\s*:\s*"([^"]*)"', text)
    return m.group(1) if m else "unknown"


def node_version(node: str = "node") -> tuple[str, tuple[int, ...]]:
    """What `node --version` says, as it said it and as numbers.

    The reported string is carried into the trace verbatim (`meta.node` is
    what the container itself reports; this is what the DRIVER saw), so it
    is returned beside the parse rather than replaced by it.
    """
    try:
        out = subprocess.run([node, "--version"], capture_output=True,
                             text=True)
    except OSError:
        raise PackageError(
            f"cannot run `{node} --version`: this recorder drives node, and "
            f"Node {NODE_FLOOR} or newer is the version it was measured on"
        ) from None
    reported = out.stdout.strip()
    parts = tuple(int(n) for n in re.findall(r"\d+", reported)[:3])
    if out.returncode != 0 or not parts:
        raise PackageError(
            f"`{node} --version` answered nothing this recorder can read "
            f"({reported!r}): it needs Node {NODE_FLOOR} or newer")
    return reported, parts


def check_node(node: str = "node") -> str:
    """The Node version string, or a refusal naming the floor."""
    reported, parts = node_version(node)
    if parts[0] < NODE_FLOOR:
        raise PackageError(
            f"node {reported} is below this recorder's floor of "
            f"{NODE_FLOOR}: Node {NODE_FLOOR} is the version its async "
            "model was measured on, and nothing older was")
    return reported
