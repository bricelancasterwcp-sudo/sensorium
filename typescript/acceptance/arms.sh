#!/usr/bin/env bash
# E1': one interleaved triple of the three arms -- plain, off, call -- on a
# consumer's own suite, appended to `arms.jsonl`.
#
#   arms.sh <lens dir> <store dir> <out dir> <batch>
#
# ONE triple per call, in the foreground, on purpose: five triples detached
# for half an hour hide a hung run until the end, and the whole point of the
# interleave is that the three arms share whatever the box was doing.
#
# What each arm is:
#   plain   npx vitest run                        -- the consumer's own command
#   off     sensorium ts run --tier off -- npx vitest run
#   call    sensorium ts run -- npx vitest run
#
# and what is timed:
#   plain   this script's own clock around the command
#   off     the HARNESS wall out of the invocation's `harness.json`
#           (`wall_end_ts - wall_start_ts`), which the driver writes around
#           the spawn -- conversion is excluded, as the rule says
#   call    the same; the driver's TOTAL wall (conversion included) is
#           written beside it as `driver_wall`, ungated
#
# Before every run the 1-minute load must be under 4.0 (the pre-registered
# refusal): the script waits for it and refuses if it never drops.
#
# Every run's suite counts, vitest `Duration` line, exit status and (for the
# driver arms) invocation id and spool size go into one JSON object per run.
# A run whose suite is not 372/4278 is still written down, with `ok: false`
# and the reason -- an arm is dropped by the assembler, never by silence here.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

LENS_DIR="${1-}"; STORE="${2-}"; OUT="${3-}"; BATCH="${4-}"
[ -n "$LENS_DIR" ] && [ -n "$STORE" ] && [ -n "$OUT" ] && [ -n "$BATCH" ] ||
  refuse "usage: arms.sh <lens dir> <store dir> <out dir> <batch>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"

#: The suite the lens is pinned at. A run that does not read both lines is
#: infrastructure, not a slow arm.
WANT_FILES=' Test Files  372 passed (372)'
WANT_TESTS='      Tests  4278 passed (4278)'
#: The recorder the two driver arms run: always this branch's own
#: `.venv/bin/sensorium`, resolved by `bin.sh`, which refuses rather than
#: fall back to whatever `sensorium` resolves to on `PATH`. Rung 1 read this
#: default as the GLOBAL tool; S5 rung 3 closes that -- an instrument that
#: can silently measure `main` instead of the branch is the defect, not a
#: feature a caller opts out of.
. "$HERE/bin.sh"

#: The pre-registered load refusal, and how long the guard is willing to wait.
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
JSONL="$OUT/arms.jsonl"

# wait_for_load -- block until the 1-minute load is under LOAD_MAX.
wait_for_load() {
  local i load
  for ((i = 0; i < LOAD_TRIES; i++)); do
    load="$(cut -d' ' -f1 /proc/loadavg)"
    if awk -v l="$load" -v m="$LOAD_MAX" 'BEGIN { exit !(l < m) }'; then
      printf '%s' "$load"
      return 0
    fi
    python3 -c 'import time,sys; time.sleep(float(sys.argv[1]))' "$LOAD_SLEEP"
  done
  refuse "1-minute load never dropped below $LOAD_MAX (last: $load)"
}

# one_run <arm> <index> -- run one arm, append one JSON line, echo nothing.
one_run() {
  local arm="$1" idx="$2"
  local log="$OUT/logs/arm-$arm-$idx.log"
  local load start end status wall inv spool
  load="$(wait_for_load)"
  # `refuse` inside a command substitution kills only the substitution's own
  # shell, so the guard's refusal has to be re-raised here or the run would
  # go ahead under a load the pre-registration refuses.
  [ -n "$load" ] || refuse "the load guard refused before arm $arm run $idx"
  start="$(date +%s.%N)"
  case "$arm" in
    plain) ( cd "$LENS_DIR" && npx vitest run ) >"$log" 2>&1 ;;
    off)   ( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
             "$SENSORIUM_BIN" ts run --tier off -- npx vitest run ) >"$log" 2>&1 ;;
    call)  ( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
             "$SENSORIUM_BIN" ts run -- npx vitest run ) >"$log" 2>&1 ;;
    *) refuse "unknown arm: $arm" ;;
  esac
  status=$?
  end="$(date +%s.%N)"

  inv=''; wall=''; spool=''
  if [ "$arm" != plain ]; then
    inv="$(sed -n 's/^invocation: \([^ ]*\).*/\1/p' "$log" | tail -1)"
    if [ -n "$inv" ] && [ -f "$STORE/spool/$inv/harness.json" ]; then
      wall="$(python3 -c 'import json,sys; h=json.load(open(sys.argv[1])); print(repr(h["wall_end_ts"]-h["wall_start_ts"]))' \
              "$STORE/spool/$inv/harness.json")"
      spool="$STORE/spool/$inv"
    fi
  fi

  ARM="$arm" IDX="$idx" BATCH="$BATCH" LOG="$log" LOAD="$load" \
  START="$start" END="$end" STATUS="$status" INV="$inv" HARNESS_WALL="$wall" \
  SPOOL="$spool" WANT_FILES="$WANT_FILES" \
  WANT_TESTS="$WANT_TESTS" python3 "$HERE/arm_line.py" >>"$JSONL"
}

for arm in plain off call; do
  one_run "$arm" "$BATCH"
done
printf 'batch %s written to %s\n' "$BATCH" "$JSONL"
