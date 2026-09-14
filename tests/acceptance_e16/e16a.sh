#!/usr/bin/env bash
# E16 part A's launcher: start `e16a.py` DETACHED and print where to look.
#
#   e16a.sh <work root> <out dir> <node bin dir> <cargo-sensorium dir>
#
# Part A records three programs, sweeps two trees, re-runs four refocus
# pairs and greps everything it made. §1 caps it at 45 minutes, so it
# outlives the terminal it was started from and the only honest way to read
# it is to wait for the marker rather than for the process. `setsid` puts it
# in a session of its own, `nohup` detaches it from this terminal's HUP, and
# everything it prints goes to `<out>/e16a.log`.
#
# Nothing here is a location. All four are arguments, and the work root is
# where every byte this measurement writes goes -- the store, the three
# disposable copies, the cargo target directory, the transcripts and the
# minted token. The two PATH arguments exist because a scrubbed environment
# has to be given the node and driver directories rather than inherit them:
# see `e16a.py`'s ALLOWLIST.
#
#   E16_DRY=1  DRY RUNS ONLY -- plant a `dry-` decoy that cannot be the
#              token, cap every timer at a minute, and stamp
#              `dry_run: true` in the raw record, which
#              `assemble_e16a.py` refuses. Point it at a work root of its
#              own: a dry run leaves a store, a target directory and copies
#              behind, and the measurement is made into a FRESH one.
#
# Read nothing before `<out>/e16a.DONE` (or `.FAILED`) exists: a raw record
# written mid-phase is a partial record, and it says so in its own `status`.
#
# The token's value is never printed -- not by this file, not by `e16a.py`,
# not into the log -- and the record cites `sha256(token)[:8]` only.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

refuse() { printf 'refused: %s\n' "$1" >&2; exit 2; }

WORK="${1-}"; OUT="${2-}"; NODE_BIN="${3-}"; DRIVER_DIR="${4-}"
[ -n "$WORK" ] && [ -n "$OUT" ] && [ -n "$NODE_BIN" ] && [ -n "$DRIVER_DIR" ] ||
  refuse "usage: e16a.sh <work root> <out dir> <node bin dir> <cargo-sensorium dir>"
[ -x "$REPO/.venv/bin/python" ] ||
  refuse "no $REPO/.venv/bin/python: part A runs under this branch's own venv"
[ -x "$NODE_BIN/node" ] || refuse "no node under $NODE_BIN"
[ -x "$NODE_BIN/npx" ] || refuse "no npx under $NODE_BIN"
[ -x "$DRIVER_DIR/cargo-sensorium" ] ||
  refuse "no cargo-sensorium under $DRIVER_DIR"
[ -d "$REPO/corpus/typescript/node_modules/vitest" ] ||
  refuse "no installed vitest under corpus/typescript (npm ci)"

# The store is the recorder's to create -- H2 is a claim about the mode a
# recorder chose -- so this refuses a work root that already holds one
# rather than measuring into it a second time.
[ -e "$WORK/store-a" ] &&
  refuse "$WORK/store-a exists: part A is measured ONCE, into a fresh store"
[ -e "$OUT/e16a.DONE" ] || [ -e "$OUT/e16a.FAILED" ] &&
  refuse "$OUT already holds a marker from an earlier run"

mkdir -p "$WORK" || refuse "cannot write under $WORK"
mkdir -p "$OUT" || refuse "cannot write under $OUT"

# Absolute, so a relative argument cannot resolve against the runner's cwd.
WORK="$(cd "$WORK" && pwd)"
OUT="$(cd "$OUT" && pwd)"
NODE_BIN="$(cd "$NODE_BIN" && pwd)"
DRIVER_DIR="$(cd "$DRIVER_DIR" && pwd)"

export E16_WORK="$WORK" E16_OUT="$OUT"
export E16_NODE_BIN="$NODE_BIN" E16_DRIVER_DIR="$DRIVER_DIR"
export E16_DRY="${E16_DRY:-0}"
export PYTHONDONTWRITEBYTECODE=1

setsid nohup "$REPO/.venv/bin/python" "$HERE/e16a.py" \
  > "$OUT/e16a.log" 2>&1 &
pid=$!

printf 'e16a launched: pid %s\n' "$pid"
printf '  work:    %s\n' "$WORK"
printf '  out:     %s\n' "$OUT"
printf '  log:     %s/e16a.log\n' "$OUT"
printf '  raw:     %s/results-a.json\n' "$OUT"
printf '  markers: %s/e16a.DONE | %s/e16a.FAILED\n' "$OUT" "$OUT"
printf '  dry run: %s\n' "$E16_DRY"
