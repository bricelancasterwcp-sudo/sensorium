#!/usr/bin/env bash
# The §10 planted change: does the verifier see a reordering nobody else can?
#
#   planted_change.sh <lens dir> <copy dir> <store> <out dir> <test file> \
#                     <file rel> <move needle> <before needle>
#
# On its own throwaway copy: record the test file, move one call site past
# another inside one function the test exercises, record again, `diff`.
# DIVERGED naming the step is the pass; a MATCH voids the verifier and STOPs.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"
. "$HERE/copy_lens.sh"
. "$HERE/bin.sh"

LENS_DIR="${1-}"; COPY="${2-}"; STORE="${3-}"; OUT="${4-}"; TEST_FILE="${5-}"
FILE_REL="${6-}"; MOVE="${7-}"; BEFORE="${8-}"
[ -n "$LENS_DIR" ] && [ -n "$COPY" ] && [ -n "$STORE" ] && [ -n "$OUT" ] &&
  [ -n "$TEST_FILE" ] && [ -n "$FILE_REL" ] && [ -n "$MOVE" ] && [ -n "$BEFORE" ] ||
  refuse "usage: planted_change.sh <lens dir> <copy dir> <store> <out dir> <test file> <file rel> <move needle> <before needle>"

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
copy_lens "$LENS_DIR" "$COPY" || refuse "could not copy the lens to $COPY"

record() {
  local label="$1" log="$OUT/logs/planted-$1.log"
  ( cd "$COPY" && SENSORIUM_DIR="$STORE" \
    "$SENSORIUM_BIN" ts run -- npx vitest run "$TEST_FILE" ) >"$log" 2>&1
  printf '%s\t%s\t%s\n' "$label" "$?" \
    "$(sed -n 's/^run: \([^ ]*\).*/\1/p' "$log" | tail -1)"
}

record before >"$OUT/planted-runs.txt"
python3 "$HERE/swap_edit.py" "$COPY" "$FILE_REL" "$MOVE" "$BEFORE" \
  >"$OUT/planted-edit.json" 2>"$OUT/logs/planted-edit.err" ||
  refuse "the swap could not be applied: $(cat "$OUT/logs/planted-edit.err")"
record after >>"$OUT/planted-runs.txt"

A="$(awk -F'\t' '$1=="before" {print $3}' "$OUT/planted-runs.txt")"
B="$(awk -F'\t' '$1=="after"  {print $3}' "$OUT/planted-runs.txt")"
[ -n "$A" ] && [ -n "$B" ] || refuse "one of the two recordings left no trace"

SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" diff "$A" "$B" >"$OUT/logs/planted-diff.txt" 2>&1
plain_code=$?

E5TS_RUNS="$OUT/planted-runs.txt" E5TS_EDIT="$OUT/planted-edit.json" \
E5TS_PLAIN="$OUT/logs/planted-diff.txt" E5TS_PLAIN_CODE="$plain_code" \
E5TS_FILE="$TEST_FILE" python3 "$HERE/control_report.py" planted
