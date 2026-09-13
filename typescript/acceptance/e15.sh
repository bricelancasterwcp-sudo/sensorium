#!/usr/bin/env bash
# E15's launcher: start `e15.py` DETACHED and print where to look.
#
#   e15.sh <lens> <work root> <out dir>
#
# The loop is 31 whole-suite re-runs -- §1 bounds it at three hours -- so it
# outlives the terminal it was started from, and the only honest way to read
# it is to wait for the marker rather than for the process. `setsid` puts it
# in a session of its own, `nohup` detaches it from this terminal's HUP, and
# everything it prints goes to `<out>/e15.log`.
#
# Nothing here is a location: all three are arguments, and the two optional
# variables below are passed through from the caller's environment.
#
#   E15_ROWS         DRY RUNS ONLY -- cap the loop and substitute the lens's
#                    own `refocus_*` cases for the survey's rows. The raw
#                    records `dry_run: true` and `assemble_e15.py` refuses it.
#   E15_CARGO_TARGET H10's `cargo test --workspace` target directory. Unset,
#                    cargo uses `rust/target`, which is slower and not wrong.
#                    Passed as a variable so no box path is written here.
#
# Read nothing before `<out>/e15.DONE` (or `.FAILED`) exists: a raw record
# written mid-phase is a partial record, and it says so in its own `status`.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

refuse() { printf 'refused: %s\n' "$1" >&2; exit 2; }

LENS="${1-}"; WORK="${2-}"; OUT="${3-}"
[ -n "$LENS" ] && [ -n "$WORK" ] && [ -n "$OUT" ] ||
  refuse "usage: e15.sh <lens> <work root> <out dir>"
[ -d "$LENS" ] || refuse "no such lens directory: $LENS"
[ -x "$REPO/.venv/bin/python" ] ||
  refuse "no $REPO/.venv/bin/python: E15 runs under this branch's own venv"

mkdir -p "$OUT" || refuse "cannot write under $OUT"
mkdir -p "$WORK" || refuse "cannot write under $WORK"

# Absolute, so a relative argument cannot resolve against the runner's cwd.
LENS="$(cd "$LENS" && pwd)"
WORK="$(cd "$WORK" && pwd)"
OUT="$(cd "$OUT" && pwd)"

export E15_LENS="$LENS" E15_WORK="$WORK" E15_OUT="$OUT"
export PYTHONDONTWRITEBYTECODE=1

setsid nohup "$REPO/.venv/bin/python" "$HERE/e15.py" \
  > "$OUT/e15.log" 2>&1 &
pid=$!

printf 'e15 launched: pid %s\n' "$pid"
printf '  lens:    %s\n' "$LENS"
printf '  work:    %s\n' "$WORK"
printf '  out:     %s\n' "$OUT"
printf '  log:     %s/e15.log\n' "$OUT"
printf '  raw:     %s/results-e15-raw.json\n' "$OUT"
printf '  markers: %s/e15.DONE | %s/e15.FAILED\n' "$OUT" "$OUT"
# No apostrophe inside the default: bash parses `${x:-…}` within double
# quotes and a stray `'` there opens a quote the file never closes.
rows="${E15_ROWS:-}"
printf '  rows:    %s\n' "${rows:-all 31, the surveyed rows}"
