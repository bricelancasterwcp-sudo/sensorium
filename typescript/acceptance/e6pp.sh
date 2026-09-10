#!/usr/bin/env bash
# E6": is a plain run contaminated by a recording having happened?
#
#   e6pp.sh <lens dir> <manifest file> <store dir> <out dir>
#
# E6''s question, re-asked with the four things its single plain run could
# not supply (spec 2.1-2.3):
#
#   * a LOAD GUARD before every run -- the same rule `arms.sh` used
#     (1-minute load under 4.0, up to 90 tries 20 s apart), the reading
#     written beside the wall it guarded;
#   * a BEFORE ARM of five plain runs, so the band is derived from an arm
#     this session measured rather than from another endpoint's history;
#   * an AFTER ARM of five, so the clause tests a MEDIAN over five guarded
#     runs and not one wall -- which is what E6' stopped on;
#   * the MANIFEST verified both BEFORE the session (a lens that moved since
#     rung 1 is not the lens the band's history was taken on, and the session
#     stops before it starts) and AFTER the after arm.
#
# The order is spec 2.1's and is not an implementation detail: the manifest
# is checked last so that the last thing to have touched the lens is the
# after arm, which is what the clause is about.
#
#   1. manifest, before        `sha256sum -c` from inside the lens
#   2. before arm              5 x guarded `npx vitest run`
#   3. the call run            `sensorium ts run -- npx vitest run`
#   4. after arm               5 x guarded `npx vitest run`
#   5. manifest, after; the marker grep; the wrapper listing
#
# The expected OK count is the manifest's own line count rather than a
# literal 748: a dry run carries a two-file manifest of its own, and an
# instrument that can only be exercised on the subject is one nobody checks
# before the fifteen minutes start. The manifest's own sha256 is written into
# the artifact, so "748 OK" is anchored to WHICH manifest, not just to a
# count -- a truncated manifest would pass a count and fail that hash.
#
# `E6PP_N` (default 5) is for DRY RUNS ONLY and is recorded in the JSON: a
# session that ran fewer than five per arm is a `STOP by instrument`, and the
# report says so from this number.
#
# This prints the record's cell on stdout and nothing else; the runs, the
# two manifest checks, the grep and the wrapper listing stay under <out dir>.
# Every comparison -- the band, the five clauses, the verdict word -- is
# `e6pp_report.py`'s and the record's.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

LENS_DIR="${1-}"; MANIFEST="${2-}"; STORE="${3-}"; OUT="${4-}"
[ -n "$LENS_DIR" ] && [ -n "$MANIFEST" ] && [ -n "$STORE" ] && [ -n "$OUT" ] ||
  refuse "usage: e6pp.sh <lens dir> <manifest file> <store dir> <out dir>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"
[ -f "$MANIFEST" ] || refuse "no such manifest: $MANIFEST"

#: The suite the lens is pinned at, spelled as `arms.sh` and `e6.sh` spell
#: it. A run that does not read both lines ran a different suite and is
#: dropped by the report, never averaged in.
WANT_FILES=' Test Files  372 passed (372)'
WANT_TESTS='      Tests  4278 passed (4278)'
#: The pre-registered load refusal, and how long the guard waits. Identical
#: to `arms.sh`'s and `e10p.sh`'s: two instruments in one slice that guard at
#: different thresholds do not measure the same box.
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20
#: Runs per arm. Five is the rule; anything else is a dry run and says so.
N="${E6PP_N:-5}"
case "$N" in ''|*[!0-9]*) refuse "E6PP_N must be a positive integer: $N" ;; esac
[ "$N" -ge 1 ] || refuse "E6PP_N must be a positive integer: $N"
#: The recorder under measurement. The default is the global tool; the
#: session passes THIS slice's `.venv/bin/sensorium`, which is the whole
#: point of running E6" last.
SENSORIUM_BIN="${SENSORIUM_BIN:-sensorium}"
E6PP_REV="${E6PP_REV:-}"
[ -n "$E6PP_REV" ] ||
  refuse "E6PP_REV is required: a contamination reading without the recorder's rev names no recorder"
#: What the cell says RECORDED it. The `lens` string comes from `LENS.txt`
#: and names the recorder that produced the LENS -- a different recorder
#: from the one a later slice runs -- so the sentence and the full sha are
#: both required here and `e6pp_report.py` refuses without them.
E6PP_RECORDER="${E6PP_RECORDER:-}"
[ -n "$E6PP_RECORDER" ] ||
  refuse "E6PP_RECORDER is required: name the recorder that ran (its versions and its commit); the lens string names the LENS's recorder, not this one"
E6PP_RECORDER_REV="${E6PP_RECORDER_REV:-}"
[ -n "$E6PP_RECORDER_REV" ] ||
  refuse "E6PP_RECORDER_REV is required: the FULL sha of the commit the recorder ran at"

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
JSONL="$OUT/e6pp.jsonl"
: >"$JSONL"
BEFORE_CHECK="$OUT/e6pp-manifest-before.txt"
AFTER_CHECK="$OUT/e6pp-manifest-after.txt"
MARKERS="$OUT/e6pp-markers.txt"
WRAPPER_LS="$OUT/e6pp-wrapper.txt"

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

# one_run <arm> <index> -- run one arm, append one JSON line.
one_run() {
  local arm="$1" idx="$2"
  local log="$OUT/logs/e6pp-$arm-$idx.log"
  local load start end status wall inv spool
  load="$(wait_for_load)"
  # `refuse` inside a command substitution kills only the substitution's own
  # shell, so the guard's refusal is re-raised here or the run would go ahead
  # under a load the pre-registration refuses.
  [ -n "$load" ] || refuse "the load guard refused before the $arm arm's run $idx"
  start="$(date +%s.%N)"
  case "$arm" in
    before|after) ( cd "$LENS_DIR" && npx vitest run ) >"$log" 2>&1 ;;
    call) ( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
            "$SENSORIUM_BIN" ts run -- npx vitest run ) >"$log" 2>&1 ;;
    *) refuse "unknown arm: $arm" ;;
  esac
  status=$?
  end="$(date +%s.%N)"

  inv=''; wall=''; spool=''
  if [ "$arm" = call ]; then
    inv="$(sed -n 's/^invocation: \([^ ]*\).*/\1/p' "$log" | tail -1)"
    if [ -n "$inv" ] && [ -f "$STORE/spool/$inv/harness.json" ]; then
      wall="$(python3 -c 'import json,sys; h=json.load(open(sys.argv[1])); print(repr(h["wall_end_ts"]-h["wall_start_ts"]))' \
              "$STORE/spool/$inv/harness.json")"
      spool="$STORE/spool/$inv"
    fi
  fi

  ARM="$arm" IDX="$idx" BATCH=1 LOG="$log" LOAD="$load" \
  START="$start" END="$end" STATUS="$status" INV="$inv" HARNESS_WALL="$wall" \
  SPOOL="$spool" LENS="$ACCEPT_LENS" WANT_FILES="$WANT_FILES" \
  WANT_TESTS="$WANT_TESTS" python3 "$HERE/arm_line.py" >>"$JSONL"
}

# 1. the manifest, verified BEFORE anything -- a lens that moved since rung 1
#    is not the lens this band's history was taken on.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$BEFORE_CHECK" 2>&1
before_status=$?
MANIFEST_LINES="$(wc -l <"$MANIFEST" | tr -d ' ')"
before_ok="$(grep -c ': OK$' "$BEFORE_CHECK" || true)"
if [ "$before_status" -ne 0 ] || [ "$before_ok" != "$MANIFEST_LINES" ] ||
   grep -q FAILED "$BEFORE_CHECK"; then
  refuse "the lens moved: $BEFORE_CHECK reads $before_ok OK of $MANIFEST_LINES (exit $before_status); nothing is measured on a lens that is not the one the band's history was taken on"
fi

# 2-4. the three arms, in the order spec 2.1 fixes.
for ((k = 1; k <= N; k++)); do one_run before "$k"; done
one_run call 1
for ((k = 1; k <= N; k++)); do one_run after "$k"; done

# 5a. the manifest again, now that the after arm is the last thing to have
#     touched the lens.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$AFTER_CHECK" 2>&1
after_status=$?

# 5b. the marker grep, over every cache directory a vite/vitest run writes.
#     The searched list is written down, so "0 hits" is never "0 directories".
: >"$MARKERS"
for d in "$LENS_DIR"/node_modules/.vite* "$LENS_DIR"/.vite "$LENS_DIR"/node_modules/.vitest*; do
  [ -e "$d" ] || continue
  printf 'searched: %s\n' "${d#"$LENS_DIR"/}" >>"$MARKERS"
  grep -rl -- '__srt' "$d" 2>/dev/null | sed "s#^$LENS_DIR/#hit: #" >>"$MARKERS"
done

# 5c. the wrapper directory the driver writes for the run and removes after.
wrapper='absent'
: >"$WRAPPER_LS"
if [ -e "$LENS_DIR/node_modules/.sensorium" ]; then
  wrapper='present'
  ls -la "$LENS_DIR/node_modules/.sensorium" >>"$WRAPPER_LS" 2>&1
else
  printf 'node_modules/.sensorium: absent\n' >>"$WRAPPER_LS"
fi

E6PP_JSONL="$JSONL" E6PP_MARKERS="$MARKERS" \
E6PP_MANIFEST_BEFORE="$BEFORE_CHECK" E6PP_MANIFEST_AFTER="$AFTER_CHECK" \
E6PP_MANIFEST_BEFORE_STATUS="$before_status" \
E6PP_MANIFEST_AFTER_STATUS="$after_status" \
E6PP_MANIFEST_LINES="$MANIFEST_LINES" \
E6PP_MANIFEST_SHA="$(sha256sum "$MANIFEST" | cut -d' ' -f1)" \
E6PP_WRAPPER="$wrapper" E6PP_WRAPPER_LISTING="$(cat "$WRAPPER_LS")" \
E6PP_N="$N" E6PP_BIN="$SENSORIUM_BIN" E6PP_REV="$E6PP_REV" \
E6PP_RECORDER="$E6PP_RECORDER" E6PP_RECORDER_REV="$E6PP_RECORDER_REV" \
  python3 "$HERE/e6pp_report.py"
