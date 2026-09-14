#!/usr/bin/env bash
# E16 part A's launcher: start `e16a.py` DETACHED and print where to look.
#
#   e16a.sh <work root> <out dir> <node bin dir> <cargo-sensorium dir> \
#           <run label>
#
# Part A records three programs, sweeps two trees, re-runs four refocus
# pairs and greps everything it made. §1 caps it at 45 minutes, so it
# outlives the terminal it was started from and the only honest way to read
# it is to wait for the marker rather than for the process. `setsid` puts it
# in a session of its own, `nohup` detaches it from this terminal's HUP, and
# everything it prints goes to `<out>/e16a.log`.
#
# THE DRIVER IS REBUILT BY THE RUN ITSELF (ruling R37), as `e16a.py`'s
# first phase, into the cargo target directory the `<cargo-sensorium dir>`
# argument sits in -- and the run refuses if that build fails. The comment
# this replaces asked the operator to remember; a dry run after E16 run 1
# read an H2 STOP on the Rust `invocation.json` because the fix was in the
# tree and not in the binary, and read PASS after
# `cargo build --release -p cargo-sensorium`. A binary is not a source tree
# and no argument can date one, so the rebuild is a phase and its outcome,
# path, mtime and size are stamped into the raw record.
#
# `<run label>` names this run's own directories under the work root:
# `store-<label>`, `<label>-transcripts`, and the three disposable copies.
# One work root can then hold a first measurement and a re-measurement side
# by side without either sweeping the other's files.
#
# Nothing here is a location. All five are arguments, and the work root is
# where every byte this measurement writes goes -- the store, the three
# disposable copies, the cargo target directory, the transcripts and the
# minted token. The two PATH arguments exist because a scrubbed environment
# has to be given the node and driver directories rather than inherit them:
# see `e16a.py`'s ALLOWLIST.
#
#   E16_DRY_FINDINGS
#              What the dry run that preceded THIS measurement found, one
#              finding per line, carried into the raw record so §2 can say
#              it. §1's record has to show a dry-run reading; a field beats
#              somebody remembering to type one. Empty is allowed and means
#              the reading is written into §2 by hand.
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

WORK="${1-}"; OUT="${2-}"; NODE_BIN="${3-}"; DRIVER_DIR="${4-}"; LABEL="${5-}"
[ -n "$WORK" ] && [ -n "$OUT" ] && [ -n "$NODE_BIN" ] && [ -n "$DRIVER_DIR" ] &&
  [ -n "$LABEL" ] ||
  refuse "usage: e16a.sh <work root> <out dir> <node bin dir> <cargo-sensorium dir> <run label>"
case "$LABEL" in
  *[!a-z0-9]*) refuse "run label must be lowercase letters and digits: $LABEL" ;;
esac
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
[ -e "$WORK/store-$LABEL" ] &&
  refuse "$WORK/store-$LABEL exists: part A is measured ONCE, into a fresh store"
[ -e "$OUT/e16a.DONE" ] || [ -e "$OUT/e16a.FAILED" ] &&
  refuse "$OUT already holds a marker from an earlier run"

# The cargo target directory is shared between runs by design (R29 puts the
# Rust spool where the sweeps reach it), and an earlier run's spool tree
# left in it would be swept as if THIS run's recorders had made it -- run
# 1's 0664 `invocation.json` would read as a run-2 H2 STOP. Refused rather
# than tolerated: the caller deletes it, deliberately, and the record says
# so.
[ -e "$WORK/rust-target/sensorium/spool" ] &&
  refuse "$WORK/rust-target/sensorium/spool holds an earlier run's spools; delete $WORK/rust-target before measuring again"

mkdir -p "$WORK" || refuse "cannot write under $WORK"
mkdir -p "$OUT" || refuse "cannot write under $OUT"

# Absolute, so a relative argument cannot resolve against the runner's cwd.
WORK="$(cd "$WORK" && pwd)"
OUT="$(cd "$OUT" && pwd)"
NODE_BIN="$(cd "$NODE_BIN" && pwd)"
DRIVER_DIR="$(cd "$DRIVER_DIR" && pwd)"

export E16_WORK="$WORK" E16_OUT="$OUT"
export E16_NODE_BIN="$NODE_BIN" E16_DRIVER_DIR="$DRIVER_DIR"
export E16_LABEL="$LABEL"
export E16_DRY="${E16_DRY:-0}"
export E16_DRY_FINDINGS="${E16_DRY_FINDINGS:-}"
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
printf '  label:   %s\n' "$LABEL"
printf '  dry run: %s\n' "$E16_DRY"
printf '  dry findings carried: %s\n' \
  "$(printf '%s' "$E16_DRY_FINDINGS" | grep -c . || true)"
