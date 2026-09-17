#!/usr/bin/env bash
# E17's launcher: start `e17.py` DETACHED and print where to look.
#
#   e17.sh <work root> <out dir> <run label> [h1 timer seconds]
#
# `setsid nohup`: the measurement outlives the terminal that started it and
# owns its own process group, so a hung child is reaped by group and a
# closed session cannot take the run with it. The instrument is the only
# thing that writes the markers, and NOTHING under <out dir> should be read
# before `<out>/e17.DONE` (or `.FAILED`) exists -- a results file read
# mid-run is a partial measurement quoted as a whole one.
#
# Everything a path is needed for arrives through the environment, so no
# location on this box is written into a file that travels with the repo.
#
#   E17_DRY=1        rehearse: two corpus cases, a tenth of the timers, and
#                    an `assemble_e17.py` that REFUSES to write the result.
#   E17_LIVE=<dir>   the store to copy (default ~/.sensorium), read-only.
#
# The fourth argument is H1's cell timer, which §1 fixes at `3 × the
# CLI-path corpus wall time, never below 10 min` -- measured at Task 10
# step 1 and recorded in the pin table, not guessed here.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

refuse() { printf 'refused: %s\n' "$1" >&2; exit 2; }

WORK="${1-}"; OUT="${2-}"; LABEL="${3-}"; H1_TIMER="${4-600}"
[ -n "$WORK" ] && [ -n "$OUT" ] && [ -n "$LABEL" ] ||
  refuse "usage: e17.sh <work root> <out dir> <run label> [h1 timer seconds]"
case "$LABEL" in
  *[!a-z0-9]*) refuse "run label must be lowercase letters and digits: $LABEL" ;;
esac
case "$H1_TIMER" in
  *[!0-9]*|"") refuse "the h1 timer must be whole seconds: $H1_TIMER" ;;
esac
[ -x "$REPO/.venv/bin/python" ] ||
  refuse "no $REPO/.venv/bin/python: E17 runs under this branch's own venv"

LIVE="${E17_LIVE:-$HOME/.sensorium}"
[ -d "$LIVE/traces" ] || refuse "no traces directory under $LIVE"

[ -e "$WORK/store" ] &&
  refuse "$WORK/store exists: E17 is measured ONCE, into a fresh copy; delete it before measuring again"
{ [ -e "$OUT/e17.DONE" ] || [ -e "$OUT/e17.FAILED" ]; } &&
  refuse "$OUT already holds a marker from an earlier run"

mkdir -p "$WORK" || refuse "cannot write under $WORK"
mkdir -p "$OUT" || refuse "cannot write under $OUT"

# Absolute, so a relative argument cannot resolve against the runner's cwd.
WORK="$(cd "$WORK" && pwd)"
OUT="$(cd "$OUT" && pwd)"
LIVE="$(cd "$LIVE" && pwd)"

CARGO_BIN=""; NODE_BIN=""
command -v cargo >/dev/null && CARGO_BIN="$(dirname "$(command -v cargo)")"
command -v node >/dev/null && NODE_BIN="$(dirname "$(command -v node)")"
if [ "${E17_DRY:-0}" = "0" ]; then
  [ -n "$CARGO_BIN" ] || refuse "no cargo on PATH: the Rust corpus cases would skip and H1 would STOP"
  [ -n "$NODE_BIN" ] || refuse "no node on PATH: the TypeScript cases would skip and H1 would STOP"
fi

export E17_WORK="$WORK" E17_OUT="$OUT" E17_LIVE="$LIVE"
export E17_LABEL="$LABEL"
export E17_DRY="${E17_DRY:-0}"
export E17_CARGO_BIN="$CARGO_BIN"
export E17_NODE_BIN="$NODE_BIN"
export E17_H1_TIMER="$H1_TIMER"
export PYTHONDONTWRITEBYTECODE=1

setsid nohup "$REPO/.venv/bin/python" "$HERE/e17.py" \
  > "$OUT/e17.log" 2>&1 &
pid=$!

printf 'e17 launched: pid %s\n' "$pid"
printf '  work:      %s\n' "$WORK"
printf '  out:       %s\n' "$OUT"
printf '  copied:    %s\n' "$LIVE"
printf '  log:       %s/e17.log\n' "$OUT"
printf '  raw:       %s/results-%s.json\n' "$OUT" "$LABEL"
printf '  markers:   %s/e17.DONE | %s/e17.FAILED\n' "$OUT" "$OUT"
printf '  label:     %s\n' "$LABEL"
printf '  dry run:   %s\n' "$E17_DRY"
printf '  h1 timer:  %s s\n' "$E17_H1_TIMER"
printf '  cargo bin: %s\n' "${CARGO_BIN:-(none)}"
printf '  node bin:  %s\n' "${NODE_BIN:-(none)}"
printf '  driver:    %s\n' "${SENSORIUM_CARGO_SENSORIUM:-(unset)}"
