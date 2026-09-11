#!/usr/bin/env bash
# E6-TS′: does the recorder accuse falsely on somebody else's suite?
#
#   e6tsp.sh <lens dir> <store dir> <out dir>
#
# ONE guarded call-tier run of the consumer's whole suite through THIS rung's
# recorder, then the invocation's `exceptions` answer with the limit raised
# until nothing is paged away. That answer is what the adjudication is read
# off, line by line, against the consumer's own source — so this script's job
# is to produce it once, keep it verbatim, and prove that the lens it was
# taken on is the lens the pins name.
#
# The run doubles as E5″'s vitest half (the plan's order): a suite that is not
# 372/4278 is not a lens sweep, it is an infrastructure kill, and the JSON says
# which of the two lines failed rather than averaging a broken run in.
#
#   1. manifest, before        `sha256sum -c` from inside the lens
#   2. the call run            guarded; `sensorium ts run -- npx vitest run`
#   3. the answer              `exceptions <invocation> --limit 10000`
#   4. manifest, after; the marker grep; the wrapper listing
#
# The transcript is COMMITTED beside the record (§1), so three literal paths
# are rewritten in the saved copy — the store root to `<store>`, the lens root
# to `<lens>` and the home directory to `<home>` — exactly as `e7.sh` does it.
# The raw answer stays under <out dir>, unredacted, for anyone re-reading the
# gate on this box.
#
# `--limit 10000` is the pre-registered number and paging is by RAISING the
# limit (§4.2's rule that a limit counts SHAPES). The report refuses a
# transcript whose `more:` note says shapes were left unprinted: an
# adjudication of the shapes that fit is not an adjudication.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

LENS_DIR="${1-}"; STORE="${2-}"; OUT="${3-}"
[ -n "$LENS_DIR" ] && [ -n "$STORE" ] && [ -n "$OUT" ] ||
  refuse "usage: e6tsp.sh <lens dir> <store dir> <out dir>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"

#: The manifest the lens is pinned by. An environment variable and not an
#: argument only because the three positional arguments are the brief's;
#: required either way, since a sweep on an unverified lens is not this sweep.
MANIFEST="${E6TSP_MANIFEST:-}"
[ -n "$MANIFEST" ] ||
  refuse "E6TSP_MANIFEST is required: the sha256 manifest the lens is pinned by"
[ -f "$MANIFEST" ] || refuse "no such manifest: $MANIFEST"

#: The suite the lens is pinned at, spelled as `arms.sh` and `e6pp.sh` spell it.
WANT_FILES=' Test Files  372 passed (372)'
WANT_TESTS='      Tests  4278 passed (4278)'
#: The pre-registered load refusal, identical to every other instrument's.
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20
#: The pre-registered limit: paging raises it, so this is "print every shape".
LIMIT="${E6TSP_LIMIT:-10000}"
#: The interpreter the REPORT runs under. It opens the traces to resolve each
#: sink's file, so it needs `sensorium` importable -- which the system python
#: is not obliged to have. The runs above need nothing but the standard
#: library, so they stay on `python3`.
: "${E6TSP_PYTHON:=python3}"

#: The recorder under measurement: always this branch's own
#: `.venv/bin/sensorium`, resolved by `bin.sh` -- the point this rung used to
#: make by convention, `bin.sh` now makes by refusal.
. "$HERE/bin.sh"
E6TSP_REV="${E6TSP_REV:-}"
[ -n "$E6TSP_REV" ] ||
  refuse "E6TSP_REV is required: the FULL sha of the commit the recorder ran at"
E6TSP_RECORDER="${E6TSP_RECORDER:-}"
[ -n "$E6TSP_RECORDER" ] ||
  refuse "E6TSP_RECORDER is required: name the recorder that ran (its versions); the lens string names the LENS's recorder, not this one"

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
JSONL="$OUT/e6tsp.jsonl"
: >"$JSONL"
BEFORE_CHECK="$OUT/e6tsp-manifest-before.txt"
AFTER_CHECK="$OUT/e6tsp-manifest-after.txt"
MARKERS="$OUT/e6tsp-markers.txt"
WRAPPER_LS="$OUT/e6tsp-wrapper.txt"
RAW="$OUT/e6tsp-exceptions-raw.txt"
TRANSCRIPT="$OUT/e6tsp-exceptions.txt"

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

# 1. the manifest, verified BEFORE anything.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$BEFORE_CHECK" 2>&1
before_status=$?
MANIFEST_LINES="$(wc -l <"$MANIFEST" | tr -d ' ')"
before_ok="$(grep -c ': OK$' "$BEFORE_CHECK" || true)"
if [ "$before_status" -ne 0 ] || [ "$before_ok" != "$MANIFEST_LINES" ] ||
   grep -q FAILED "$BEFORE_CHECK"; then
  refuse "the lens moved: $BEFORE_CHECK reads $before_ok OK of $MANIFEST_LINES (exit $before_status); nothing is measured on a lens that is not the one the pins name"
fi

# 2. the one call-tier run.
log="$OUT/logs/e6tsp-call-1.log"
load="$(wait_for_load)"
# `refuse` inside a command substitution kills only the substitution's own
# shell, so the guard's refusal is re-raised here.
[ -n "$load" ] || refuse "the load guard refused before the call run"
start="$(date +%s.%N)"
( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
  "$SENSORIUM_BIN" ts run -- npx vitest run ) >"$log" 2>&1
status=$?
end="$(date +%s.%N)"

inv="$(sed -n 's/^invocation: \([^ ]*\).*/\1/p' "$log" | tail -1)"
wall=''; spool=''
if [ -n "$inv" ] && [ -f "$STORE/spool/$inv/harness.json" ]; then
  wall="$(python3 -c 'import json,sys; h=json.load(open(sys.argv[1])); print(repr(h["wall_end_ts"]-h["wall_start_ts"]))' \
          "$STORE/spool/$inv/harness.json")"
  spool="$STORE/spool/$inv"
fi
ARM=call IDX=1 BATCH=1 LOG="$log" LOAD="$load" \
START="$start" END="$end" STATUS="$status" INV="$inv" HARNESS_WALL="$wall" \
SPOOL="$spool" LENS="$ACCEPT_LENS" WANT_FILES="$WANT_FILES" \
WANT_TESTS="$WANT_TESTS" python3 "$HERE/arm_line.py" >>"$JSONL"

# 3. the answer. Kept even when the run was not clean: a transcript nobody
#    may adjudicate is still evidence about what happened.
excs_status=''
if [ -n "$inv" ]; then
  { printf '$ sensorium exceptions %s --limit %s\n' "$inv" "$LIMIT"
    SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" exceptions "$inv" --limit "$LIMIT" 2>&1
    excs_status=$?
    printf -- '--- exit %s\n' "$excs_status"
  } >"$RAW"
  excs_status="$(sed -n 's/^--- exit \([0-9]*\)$/\1/p' "$RAW" | tail -1)"
else
  printf 'the call run printed no invocation id; nothing to ask\n' >"$RAW"
fi

# The committed copy: three literal paths become labels, nothing else moves.
python3 - "$RAW" "$TRANSCRIPT" "$STORE" "$LENS_DIR" "$HOME" <<'PY'
import sys
raw, out = sys.argv[1:3]
text = open(raw, encoding="utf-8", errors="replace").read()
# Longest first: the store may live under the lens, or either under $HOME.
for needle, label in sorted(zip(sys.argv[3:6], ("<store>", "<lens>", "<home>")),
                            key=lambda p: len(p[0]), reverse=True):
    if needle:
        text = text.replace(needle.rstrip("/"), label)
open(out, "w", encoding="utf-8").write(text)
PY

# 4a. the manifest again, now that the sweep is the last thing to have run.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$AFTER_CHECK" 2>&1
after_status=$?

# 4b. the marker grep, over every cache directory a vite/vitest run writes.
: >"$MARKERS"
for d in "$LENS_DIR"/node_modules/.vite* "$LENS_DIR"/.vite "$LENS_DIR"/node_modules/.vitest*; do
  [ -e "$d" ] || continue
  printf 'searched: %s\n' "${d#"$LENS_DIR"/}" >>"$MARKERS"
  grep -rl -- '__srt' "$d" 2>/dev/null | sed "s#^$LENS_DIR/#hit: #" >>"$MARKERS"
done

# 4c. the wrapper directory the driver writes for the run and removes after.
wrapper='absent'
: >"$WRAPPER_LS"
if [ -e "$LENS_DIR/node_modules/.sensorium" ]; then
  wrapper='present'
  ls -la "$LENS_DIR/node_modules/.sensorium" >>"$WRAPPER_LS" 2>&1
else
  printf 'node_modules/.sensorium: absent\n' >>"$WRAPPER_LS"
fi

E6TSP_JSONL="$JSONL" E6TSP_TRANSCRIPT="$TRANSCRIPT" \
E6TSP_STORE="$STORE" \
E6TSP_EXCEPTIONS_EXIT="${excs_status:-}" E6TSP_INVOCATION="$inv" \
E6TSP_SPOOL_NAME="$(basename "${spool:-}")" \
E6TSP_MARKERS="$MARKERS" \
E6TSP_MANIFEST_BEFORE_STATUS="$before_status" \
E6TSP_MANIFEST_AFTER_STATUS="$after_status" \
E6TSP_MANIFEST_LINES="$MANIFEST_LINES" \
E6TSP_MANIFEST_AFTER_OK="$(grep -c ': OK$' "$AFTER_CHECK" || true)" \
E6TSP_MANIFEST_SHA="$(sha256sum "$MANIFEST" | cut -d' ' -f1)" \
E6TSP_WRAPPER="$wrapper" E6TSP_WRAPPER_LISTING="$(cat "$WRAPPER_LS")" \
E6TSP_LIMIT="$LIMIT" E6TSP_BIN="$SENSORIUM_BIN" E6TSP_REV="$E6TSP_REV" \
E6TSP_RECORDER="$E6TSP_RECORDER" \
E6TSP_ADJUDICATION="${E6TSP_ADJUDICATION:-}" \
  "${E6TSP_PYTHON:-python3}" "$HERE/e6tsp_report.py"
