#!/usr/bin/env bash
# E11: is the loss model honest? Two halves, one mode each.
#
#   e11.sh a <store> <run id> <out dir>
#   e11.sh b <lens dir> <store> <out dir> <test file, root-relative>
#
# (a) A probe test whose promise never settles under vitest's timeout: its
#     frame must read `~ suspended … at end of recording` in `tree`, and the
#     trace must be COMPLETE -- no INCOMPLETE banner from `info`. A frame
#     that never returned is not a recording that was cut off, and the two
#     must not be confused.
#
# (b) One container SIGKILLed mid-file. Its trace must read `incomplete:
#     true`, `info` must print the INCOMPLETE banner, and `diff` against a
#     complete trace of the same file must REFUSE (exit 3) rather than
#     answer.
#
#     The container is found by the recorder's OWN evidence: each container
#     spools to `<pid>-<threadId>.jsonl` and declares its test file in a
#     FILE_START record, so the pid to kill is read out of the spool that
#     names the file. That is exact. `pkill -f` is never used: an unanchored
#     pattern matches this script's own command line first.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

MODE="${1-}"
case "$MODE" in a|b) ;; *) refuse "usage: e11.sh a <store> <run id> <out dir> | e11.sh b <lens dir> <store> <out dir> <test file>" ;; esac

if [ "$MODE" = a ]; then
  STORE="${2-}"; RUN="${3-}"; OUT="${4-}"
  [ -n "$STORE" ] && [ -n "$RUN" ] && [ -n "$OUT" ] ||
    refuse "usage: e11.sh a <store> <run id> <out dir>"
  mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
  SENSORIUM_DIR="$STORE" sensorium tree "$RUN" --depth 6 >"$OUT/logs/e11a-tree.txt" 2>&1
  tree_status=$?
  SENSORIUM_DIR="$STORE" sensorium info "$RUN" >"$OUT/logs/e11a-info.txt" 2>&1
  info_status=$?
  E11_MODE=a E11_RUN="$RUN" E11_STORE="$STORE" \
  E11A_TREE="$OUT/logs/e11a-tree.txt" E11A_INFO="$OUT/logs/e11a-info.txt" \
  E11A_TREE_STATUS="$tree_status" E11A_INFO_STATUS="$info_status" \
    python3 "$HERE/e11_report.py"
  exit 0
fi

LENS_DIR="${2-}"; STORE="${3-}"; OUT="${4-}"; TEST_FILE="${5-}"
[ -n "$LENS_DIR" ] && [ -n "$STORE" ] && [ -n "$OUT" ] && [ -n "$TEST_FILE" ] ||
  refuse "usage: e11.sh b <lens dir> <store> <out dir> <test file>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"
mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"

BEFORE="$OUT/logs/e11b-spooldirs-before.txt"
LOG="$OUT/logs/e11b-run.log"
KILLED="$OUT/logs/e11b-kill.txt"
ls -1 "$STORE/spool" 2>/dev/null | sort >"$BEFORE" || : >"$BEFORE"

# The driver in the background, and NOT in a new session: the only process
# this script ever kills is the one container it identified by pid, so there
# is no process group to reap, and a `setsid` whose parent stays in this
# shell's group would put this shell inside any group kill. If the script has
# to give up it TERMs the driver it started, by its own pid.
env SENSORIUM_DIR="$STORE" bash -c \
  'cd "$1" && exec sensorium ts run -- npx vitest run' _ "$LENS_DIR" \
  >"$LOG" 2>&1 &
DRIVER_PID=$!

: >"$KILLED"
printf 'driver pid: %s\n' "$DRIVER_PID" >>"$KILLED"

# give_up <message> -- stop the driver we started, then refuse.
give_up() {
  kill -TERM "$DRIVER_PID" 2>/dev/null
  wait "$DRIVER_PID" 2>/dev/null
  refuse "$1"
}

# Wait for this invocation's spool directory to appear.
INV=''
for _ in $(seq 1 600); do
  INV="$(ls -1 "$STORE/spool" 2>/dev/null | sort | comm -13 "$BEFORE" - | tail -1)"
  [ -n "$INV" ] && break
  python3 -c 'import time; time.sleep(0.2)'
done
[ -n "$INV" ] || give_up "no new spool directory appeared"
printf 'invocation: %s\n' "$INV" >>"$KILLED"

# Wait for the container that declared the target file, and kill it.
VICTIM=''
for _ in $(seq 1 1200); do
  VICTIM="$(grep -l -F -- "$TEST_FILE" "$STORE/spool/$INV"/*.jsonl 2>/dev/null | head -1)"
  [ -n "$VICTIM" ] && break
  python3 -c 'import time; time.sleep(0.2)'
done
if [ -z "$VICTIM" ]; then
  wait "$DRIVER_PID"
  refuse "no container declared $TEST_FILE before the run ended"
fi
VICTIM_PID="$(basename "$VICTIM" .jsonl | cut -d- -f1)"
printf 'spool: %s\nvictim pid: %s\ncmdline: %s\n' "$(basename "$VICTIM")" \
  "$VICTIM_PID" "$(tr '\0' ' ' <"/proc/$VICTIM_PID/cmdline" 2>/dev/null)" >>"$KILLED"
if [ -d "/proc/$VICTIM_PID" ]; then
  kill -9 "$VICTIM_PID"
  printf 'kill -9 %s: sent\n' "$VICTIM_PID" >>"$KILLED"
else
  printf 'kill -9 %s: NOT SENT, the process had already gone\n' "$VICTIM_PID" >>"$KILLED"
fi

wait "$DRIVER_PID"
DRIVER_STATUS=$?
printf 'driver exit: %s\n' "$DRIVER_STATUS" >>"$KILLED"

E11_MODE=b E11_STORE="$STORE" E11B_INV="$INV" E11B_LOG="$LOG" \
E11B_KILLED="$KILLED" E11B_FILE="$TEST_FILE" E11B_OUT="$OUT" \
E11B_DRIVER_STATUS="$DRIVER_STATUS" python3 "$HERE/e11_report.py"
