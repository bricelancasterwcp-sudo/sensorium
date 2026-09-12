#!/usr/bin/env bash
# H8′: ONE live run on the lens, and the eight things §1.9 checks about it.
#
#   e12p.sh <lens dir> <manifest file> <store dir> <out dir> <base checkout>
#
# The LAST thing this slice does. E12′ re-adjudicates rung 4's committed
# transcripts and records nothing; this records once, on the same lens, under
# this slice's driver and recorder, and asks whether the rows still read the
# same. Nothing here judges anything: `e12p_h8.py <out dir>` reads these
# artefacts into the eight `{holds, evidence}` clauses of the record's §1.9.
#
# The order is §1.9's and is not an implementation detail:
#
#   1. manifest, before      `sha256sum -c` from inside the lens; a lens that
#                            moved is not the lens rung 4's rows were read on,
#                            and the session stops before it starts
#   2. the run               ONE `ts run --focus <the three specs> -- npx
#                            vitest run <subject>`, behind the slice-2 load
#                            guard (`e6pp.sh`'s: 1-minute load under 4.0, up
#                            to 90 tries 20 s apart)
#   3. the resolver          `node <pkg>/src/resolve.mjs` on the same three
#                            specs -> `resolve.json` (clause 2)
#   4. info                  clause 3, `focus matched: 5 … (6 functions)`
#   5. frame                 clause 4, the nine LINE rows of the first
#                            `parseDiceGroups` activation -- the one with
#                            `formula='1d20'`, which is the first in file
#                            order and therefore the one `--fn` prints first
#   6. the transform diff    clause 8: `<base checkout>`'s `transform.mjs`
#                            against this tree's, over the same
#                            `diceQueue.ts` with the same three specs. The
#                            focused file carries no return-inside-a-finally
#                            shape (§1.5's census pins that), so the diff must
#                            be EMPTY
#   7. manifest, after       the run is the last thing to have touched the
#                            lens, which is what clause 1 is about
#   8. the markers           clause 6: `__srt` in any vite/vitest cache, with
#                            every searched directory written down, so "0
#                            hits" is never "0 directories"
#   9. the wrapper           clause 7: `node_modules/.sensorium`, which the
#                            driver writes for the run and removes after
#
# WHAT IS PRE-REGISTERED AND WHAT IS A DRY RUN
# --------------------------------------------
# `SUBJECT` and `FOCUS_SPECS` are §1.9's, written down: `src/lib/
# diceQueue.test.ts` and the three `--focus diceQueue.ts:<fn>` specs.
# `E12P_TEST` and `E12P_FOCUS` override them for DRY RUNS ONLY, are recorded
# in `session.json`, and `e12p_h8.py` says in the cell whether the session was
# the pre-registered one. An instrument that can only be exercised on the
# subject is one nobody checks before the session starts.
#
# `CARGO_TARGET_DIR` is inherited, never set here, and no path in this file is
# a box path: every one of them is an argument.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"
. "$HERE/bin.sh"

LENS_DIR="${1-}"; MANIFEST="${2-}"; STORE="${3-}"; OUT="${4-}"; BASE="${5-}"
[ -n "$LENS_DIR" ] && [ -n "$MANIFEST" ] && [ -n "$STORE" ] && [ -n "$OUT" ] &&
  [ -n "$BASE" ] ||
  refuse "usage: e12p.sh <lens dir> <manifest file> <store dir> <out dir> <base checkout>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"
[ -f "$MANIFEST" ] || refuse "no such manifest: $MANIFEST"
[ -f "$BASE/typescript/src/transform.mjs" ] ||
  refuse "no transform at $BASE/typescript/src/transform.mjs: <base checkout> is a git worktree of the commit clause 8 compares against"

#: The driver sets these three itself, per container; inherited from a caller
#: they would focus, spool or manifest a run nobody asked to.
unset SENSORIUM_FOCUS SENSORIUM_SPOOL SENSORIUM_MANIFEST_DIR

#: §1.9's subject and the three specs, in this slice's own words. Overridden
#: only by a dry run, which says so in the JSON.
SUBJECT="${E12P_TEST:-src/lib/diceQueue.test.ts}"
DEFAULT_FOCUS='diceQueue.ts:parseDiceGroups diceQueue.ts:forcedDiceFromSource diceQueue.ts:buildDiceQueueEntry'
FOCUS_SPECS="${E12P_FOCUS:-$DEFAULT_FOCUS}"
#: The file clause 8's diff is taken over, relative to the lens.
SUBJECT_SOURCE="${E12P_SOURCE:-src/lib/diceQueue.ts}"
#: The activation clause 4 reads. `frame F1 --fn parseDiceGroups` is the
#: rung-4 record's §1.5 command, word for word; the override is a dry run's
#: and says so in `session.json` like the other two.
FRAME_FN="${E12P_FRAME_FN:-parseDiceGroups}"

#: What RECORDED this session, named by the caller rather than inherited from
#: `LENS.txt` -- that string names the recorder that produced the LENS, which
#: is a different recorder from the one running here.
E12P_RECORDER="${E12P_RECORDER:-}"
[ -n "$E12P_RECORDER" ] ||
  refuse "E12P_RECORDER is required: name the recorder that ran (its versions and its commit); the lens string names the LENS's recorder, not this one"
E12P_REV="${E12P_REV:-}"
[ -n "$E12P_REV" ] ||
  refuse "E12P_REV is required: the FULL sha of the commit the recorder ran at"
export E12P_RECORDER E12P_REV

#: The load guard, identical to `e6pp.sh`'s, `arms.sh`'s and `e12.sh`'s: two
#: instruments in one slice that guard at different thresholds do not measure
#: the same box.
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20

REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
mkdir -p "$STORE" || refuse "cannot create the store"

BEFORE_CHECK="$OUT/e12p-manifest-before.txt"
AFTER_CHECK="$OUT/e12p-manifest-after.txt"
RESOLVE_OUT="$OUT/resolve.json"
RUN_LOG="$OUT/logs/e12p-run.log"
INFO_OUT="$OUT/info.txt"
FRAME_OUT="$OUT/frame.txt"
DIFF_JSON="$OUT/transform-diff.json"
DIFF_TEXT="$OUT/transform.diff"
MARKERS="$OUT/e12p-markers.txt"
WRAPPER_LS="$OUT/e12p-wrapper.txt"
STATUSES="$OUT/statuses.txt"
: >"$STATUSES"

note() { printf '%s\t%s\n' "$1" "$2" >>"$STATUSES"; }

# The three specs as `--focus` flags, and as the unit-separated variable the
# driver hands the resolver. `read -a` rather than an unquoted expansion, so
# the split is on whitespace and on nothing else.
read -r -a SPEC_ARRAY <<<"$FOCUS_SPECS"
FOCUS_FLAGS=()
DIFF_FLAGS=()
for spec in "${SPEC_ARRAY[@]}"; do
  FOCUS_FLAGS+=(--focus "$spec")
  DIFF_FLAGS+=(--focus "$spec")
done
FOCUS_ENV="$(printf '%s' "${SPEC_ARRAY[0]}")"
for spec in "${SPEC_ARRAY[@]:1}"; do FOCUS_ENV+=$'\x1f'"$spec"; done

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

# 1. the manifest, before anything.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$BEFORE_CHECK" 2>&1
before_status=$?
MANIFEST_LINES="$(wc -l <"$MANIFEST" | tr -d ' ')"
before_ok="$(grep -c ': OK$' "$BEFORE_CHECK" || true)"
note manifest-before "$before_status"
if [ "$before_status" -ne 0 ] || [ "$before_ok" != "$MANIFEST_LINES" ] ||
   grep -q FAILED "$BEFORE_CHECK"; then
  refuse "the lens moved: $BEFORE_CHECK reads $before_ok OK of $MANIFEST_LINES (exit $before_status); nothing is recorded on a lens that is not the one rung 4's rows were read on"
fi

# 2. the one run, guarded.
load="$(wait_for_load)"
# `refuse` inside a command substitution kills only the substitution's own
# shell, so the guard's refusal is re-raised here or the run would go ahead
# under a load the pre-registration refuses.
[ -n "$load" ] || refuse "the load guard refused before the run"
start="$(date +%s.%N)"
( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
    "$SENSORIUM_BIN" ts run "${FOCUS_FLAGS[@]}" -- npx vitest run "$SUBJECT" ) \
  >"$RUN_LOG" 2>&1
run_status=$?
end="$(date +%s.%N)"
note run "$run_status"

RUN_ID="$(grep '^run: ' "$RUN_LOG" | tail -1 | awk '{print $2}')"
[ -n "$RUN_ID" ] ||
  refuse "the driver printed no 'run:' line in $RUN_LOG; there is no trace to read clauses 3 and 4 off"

# 3. the resolver, on the same three specs.
SENSORIUM_TS_ROOT="$LENS_DIR" SENSORIUM_FOCUS="$FOCUS_ENV" \
  node "$REPO_ROOT/typescript/src/resolve.mjs" >"$RESOLVE_OUT" 2>"$OUT/resolve-err.txt"
note resolve "$?"

# 4. info, and 5. the frame. Both read the store this run wrote; neither
#    records. The frame command is §1.5's, word for word.
( SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" info "$RUN_ID" ) >"$INFO_OUT" 2>&1
note info "$?"
( SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" frame "$RUN_ID" --fn "$FRAME_FN" ) \
  >"$FRAME_OUT" 2>&1
note frame "$?"

# 6. the transform diff: the base checkout's transform against this tree's,
#    over the same source with the same specs. Clause 8 is that it is EMPTY.
node "$HERE/transform_diff.mjs" "$BASE" "$LENS_DIR" \
  "$LENS_DIR/$SUBJECT_SOURCE" "${DIFF_FLAGS[@]}" >"$DIFF_JSON" 2>"$OUT/transform-diff-err.txt"
note transform-diff "$?"
python3 -c 'import json,sys;from pathlib import Path
body = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
Path(sys.argv[2]).write_text("".join(f["diff"] for f in body["files"]), encoding="utf-8")' \
  "$DIFF_JSON" "$DIFF_TEXT" 2>/dev/null || : >"$DIFF_TEXT"

# 7. the manifest again.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$AFTER_CHECK" 2>&1
note manifest-after "$?"

# 8. the marker grep, over every cache directory a vite/vitest run writes.
#    The searched list is written down, so "0 hits" is never "0 directories".
: >"$MARKERS"
for d in "$LENS_DIR"/node_modules/.vite* "$LENS_DIR"/.vite "$LENS_DIR"/node_modules/.vitest*; do
  [ -e "$d" ] || continue
  printf 'searched: %s\n' "${d#"$LENS_DIR"/}" >>"$MARKERS"
  grep -rl -- '__srt' "$d" 2>/dev/null | sed "s#^$LENS_DIR/#hit: #" >>"$MARKERS"
done

# 9. the wrapper directory the driver writes for the run and removes after.
: >"$WRAPPER_LS"
if [ -e "$LENS_DIR/node_modules/.sensorium" ]; then
  printf 'node_modules/.sensorium: present\n' >>"$WRAPPER_LS"
  ls -la "$LENS_DIR/node_modules/.sensorium" >>"$WRAPPER_LS" 2>&1
else
  printf 'node_modules/.sensorium: absent\n' >>"$WRAPPER_LS"
fi

# The session's own facts, for `e12p_h8.py` to read. It gates nothing.
E12P_RUN_ID="$RUN_ID" E12P_START="$start" E12P_END="$end" E12P_LOAD="$load" \
E12P_SUBJECT="$SUBJECT" E12P_SUBJECT_SOURCE="$SUBJECT_SOURCE" \
E12P_FOCUS_SPECS="$FOCUS_SPECS" E12P_DEFAULT_FOCUS="$DEFAULT_FOCUS" \
E12P_MANIFEST_LINES="$MANIFEST_LINES" E12P_BASE="$BASE" \
E12P_FRAME_FN="$FRAME_FN" \
E12P_BIN="$SENSORIUM_BIN" E12P_LOAD_MAX="$LOAD_MAX" \
E12P_LENS="$LENS_DIR" E12P_STORE_DIR="$STORE" \
  python3 - "$OUT" <<'PY'
import json
import os
import sys
from pathlib import Path

out = Path(sys.argv[1])
env = os.environ
default = env["E12P_DEFAULT_FOCUS"]
payload = {
    "run_id": env["E12P_RUN_ID"],
    "wall": round(float(env["E12P_END"]) - float(env["E12P_START"]), 4),
    "load_1min": float(env["E12P_LOAD"]),
    "subject": env["E12P_SUBJECT"],
    "subject_source": env["E12P_SUBJECT_SOURCE"],
    "frame_fn": env["E12P_FRAME_FN"],
    "focus_specs": env["E12P_FOCUS_SPECS"].split(),
    "preregistered_subject": (env["E12P_SUBJECT"] == "src/lib/diceQueue.test.ts"
                              and env["E12P_FOCUS_SPECS"] == default
                              and env["E12P_SUBJECT_SOURCE"] == "src/lib/diceQueue.ts"
                              and env["E12P_FRAME_FN"] == "parseDiceGroups"),
    "manifest_lines": int(env["E12P_MANIFEST_LINES"]),
    "base_checkout": env["E12P_BASE"],
    "recorder": env["E12P_RECORDER"],
    "recorder_rev": env["E12P_REV"],
    "recorder_bin": env["E12P_BIN"],
    "load_max": float(env["E12P_LOAD_MAX"]),
    "lens_dir": env["E12P_LENS"],
    "store": env["E12P_STORE_DIR"],
}
(out / "session.json").write_text(json.dumps(payload, indent=2) + "\n",
                                  encoding="utf-8")
PY
printf 'wrote %s\n' "$OUT/session.json"
