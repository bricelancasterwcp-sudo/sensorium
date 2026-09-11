#!/usr/bin/env bash
# The §10 control E5-TS, the split: can the verifier see through a move?
#
#   e5ts_split.sh <lens dir> <copy dir> <store> <out dir> <test file> \
#                 <module rel> <dest rel> <name a> <name b>
#
# On a throwaway copy of the consumer tree: record the test file, move the
# two named functions to a new file (re-exported from the old, so no import
# and no call site changes), record the same test file again, and ask `diff`
# twice.
#
#   plain          DIVERGED -- the fingerprint hashes the file, so a moved
#                  function is a different key
#   --ignore-moves MATCH modulo location, with exactly those two code
#                  objects in `moved:` and every task paired
#
# Anything else STOPs: the verifier cannot see through a move.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"
. "$HERE/copy_lens.sh"
. "$HERE/bin.sh"

LENS_DIR="${1-}"; COPY="${2-}"; STORE="${3-}"; OUT="${4-}"; TEST_FILE="${5-}"
MODULE="${6-}"; DEST="${7-}"; NAME_A="${8-}"; NAME_B="${9-}"
[ -n "$LENS_DIR" ] && [ -n "$COPY" ] && [ -n "$STORE" ] && [ -n "$OUT" ] &&
  [ -n "$TEST_FILE" ] && [ -n "$MODULE" ] && [ -n "$DEST" ] &&
  [ -n "$NAME_A" ] && [ -n "$NAME_B" ] ||
  refuse "usage: e5ts_split.sh <lens dir> <copy dir> <store> <out dir> <test file> <module rel> <dest rel> <name a> <name b>"

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
copy_lens "$LENS_DIR" "$COPY" || refuse "could not copy the lens to $COPY"

record() {
  local label="$1" log="$OUT/logs/e5ts-$1.log"
  ( cd "$COPY" && SENSORIUM_DIR="$STORE" \
    "$SENSORIUM_BIN" ts run -- npx vitest run "$TEST_FILE" ) >"$log" 2>&1
  printf '%s\t%s\t%s\n' "$label" "$?" \
    "$(sed -n 's/^run: \([^ ]*\).*/\1/p' "$log" | tail -1)"
}

record before >"$OUT/e5ts-runs.txt"

# The preamble the moved code needs: the two type-only imports its
# signatures mention. Type imports are erased, so the cycle they form with
# the module they came from is a compile-time one only.
PREAMBLE="import type { Cell } from './distance';
import type { GridShape, HexShape } from './$(basename "$MODULE" .ts)';"

python3 "$HERE/split_edit.py" "$COPY" "$MODULE" "$DEST" "$PREAMBLE" \
        "$NAME_A" "$NAME_B" >"$OUT/e5ts-edit.json" 2>"$OUT/logs/e5ts-edit.err" ||
  refuse "the split could not be applied: $(cat "$OUT/logs/e5ts-edit.err")"

record after >>"$OUT/e5ts-runs.txt"

A="$(awk -F'\t' '$1=="before" {print $3}' "$OUT/e5ts-runs.txt")"
B="$(awk -F'\t' '$1=="after"  {print $3}' "$OUT/e5ts-runs.txt")"
[ -n "$A" ] && [ -n "$B" ] || refuse "one of the two recordings left no trace"

SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" diff "$A" "$B" >"$OUT/logs/e5ts-diff.txt" 2>&1
plain_code=$?
SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" diff --ignore-moves "$A" "$B" \
  >"$OUT/logs/e5ts-diff-ignore-moves.txt" 2>&1
moves_code=$?

E5TS_RUNS="$OUT/e5ts-runs.txt" E5TS_EDIT="$OUT/e5ts-edit.json" \
E5TS_PLAIN="$OUT/logs/e5ts-diff.txt" E5TS_MOVES="$OUT/logs/e5ts-diff-ignore-moves.txt" \
E5TS_PLAIN_CODE="$plain_code" E5TS_MOVES_CODE="$moves_code" \
E5TS_NAMES="$NAME_A,$NAME_B" E5TS_FILE="$TEST_FILE" \
  python3 "$HERE/control_report.py" split
