#!/usr/bin/env bash
# E3-TS: false DIVERGED? One pre-named test file recorded twenty times through
# the product, then `diff` of each recording against the first.
#
#   e3.sh <lens dir> <store dir> <out dir> <test file, root-relative>
#
# The rule: DIVERGED 0/19 and REFUSED 0/19. `diff`'s exit status IS the
# verdict -- 0 MATCH, 1 DIVERGED, 3 REFUSED, 2 a bad call -- so this counts
# statuses and keeps every transcript, and a 2 is reported as a call this
# script got wrong rather than folded into either bucket.
#
# The load guard runs before every recording, as the pre-registration says.
# A recording that leaves no trace is named in `dropped` and its pair is not
# invented.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

LENS_DIR="${1-}"; STORE="${2-}"; OUT="${3-}"; TEST_FILE="${4-}"
[ -n "$LENS_DIR" ] && [ -n "$STORE" ] && [ -n "$OUT" ] && [ -n "$TEST_FILE" ] ||
  refuse "usage: e3.sh <lens dir> <store dir> <out dir> <test file>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"

#: The recorder AND the comparator under measurement -- both are this binary,
#: which is the point: `diff` reads traces THIS recorder wrote. Always this
#: branch's own `.venv/bin/sensorium`, resolved by `bin.sh`; rung 1's reading
#: of the global tool as the default is exactly the ambiguity S5 rung 3 makes
#: impossible.
. "$HERE/bin.sh"

RUNS=20
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
RUNIDS="$OUT/e3-runs.txt"
: >"$RUNIDS"

wait_for_load() {
  local i load
  for ((i = 0; i < LOAD_TRIES; i++)); do
    load="$(cut -d' ' -f1 /proc/loadavg)"
    awk -v l="$load" -v m="$LOAD_MAX" 'BEGIN { exit !(l < m) }' && { printf '%s' "$load"; return 0; }
    python3 -c 'import time,sys; time.sleep(float(sys.argv[1]))' "$LOAD_SLEEP"
  done
  return 1
}

for ((k = 1; k <= RUNS; k++)); do
  load="$(wait_for_load)" || refuse "1-minute load never dropped below $LOAD_MAX"
  log="$OUT/logs/e3-run-$k.log"
  ( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
    "$SENSORIUM_BIN" ts run -- npx vitest run "$TEST_FILE" ) >"$log" 2>&1
  status=$?
  run_id="$(sed -n 's/^run: \([^ ]*\).*/\1/p' "$log" | tail -1)"
  printf '%s\t%s\t%s\t%s\n' "$k" "${run_id:--}" "$status" "$load" >>"$RUNIDS"
done

# The pairs: run 1 against each of runs 2..20.
DIFFS="$OUT/e3-diffs.txt"
: >"$DIFFS"
first="$(awk -F'\t' 'NR==1 {print $2}' "$RUNIDS")"
[ "$first" != '-' ] && [ -n "$first" ] || refuse "the first recording left no trace: nothing to compare against"
while IFS=$'\t' read -r k run_id _ _; do
  [ "$k" = 1 ] && continue
  if [ "$run_id" = '-' ]; then
    printf '%s\t%s\t%s\t%s\n' "$k" '-' 'no-trace' '' >>"$DIFFS"
    continue
  fi
  out="$OUT/logs/e3-diff-$k.txt"
  SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" diff "$first" "$run_id" >"$out" 2>&1
  code=$?
  verdict="$(sed -n 's/^verdict: \(.*\)$/\1/p' "$out" | head -1)"
  printf '%s\t%s\t%s\t%s\n' "$k" "$run_id" "$code" "$verdict" >>"$DIFFS"
done <"$RUNIDS"

E3_RUNS="$RUNIDS" E3_DIFFS="$DIFFS" E3_FIRST="$first" E3_FILE="$TEST_FILE" \
  python3 "$HERE/e3_report.py"
