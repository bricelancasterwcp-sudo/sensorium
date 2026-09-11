# Sourced by every shell instrument in this directory that runs `sensorium`:
# the branch's own binary, or nothing.
#
#   . "$HERE/bin.sh"
#
# Rung 2 found instruments defaulting `SENSORIUM_BIN` to the bare word
# `sensorium`, which resolves through `PATH` to whatever is globally
# installed -- `main`'s tool, not this branch's, whenever the caller forgot
# to override it. This file removes the default: `SENSORIUM_BIN` is always
# `<repo root>/.venv/bin/sensorium`, and a script that wants to measure
# anything else is not a script this directory can commit. `lens.py`'s
# `sensorium_bin()` is the same rule for the instruments that are Python.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SENSORIUM_BIN="$REPO_ROOT/.venv/bin/sensorium"
if [ ! -x "$SENSORIUM_BIN" ] || [[ "$(realpath "$SENSORIUM_BIN")" != "$REPO_ROOT"/* ]]; then
  echo "refused: sensorium resolves to '$SENSORIUM_BIN', not the branch's .venv under $REPO_ROOT" >&2
  exit 3
fi
