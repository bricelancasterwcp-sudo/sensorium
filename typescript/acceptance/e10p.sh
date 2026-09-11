#!/usr/bin/env bash
# E10': what does conversion cost, under a guard, at a named job count?
#
#   e10p.sh <spool copy> <scratch dir> <label> <jobs> [n]
#
# E10's instrument (`e10.sh`) with the three things record 5 gap 5 said it
# was missing, and nothing else changed:
#
#   * a LOAD GUARD before every timed repetition -- the same rule `arms.sh`
#     already used (1-minute load under 4.0, up to 90 tries 20 s apart), and
#     the reading is written beside the wall it guarded, so a wall measured
#     on a busy box is a fact in the file rather than a suspicion;
#   * the JOB COUNT as an argument, because the ladder's cells differ only
#     in `--jobs` and a cell that cannot name its job count is not a cell;
#   * the PEAK RSS of the heaviest worker, via `rss_run.py`, which spec 3.6
#     reports ungated on either side of the streaming reader.
#
# Unchanged from `e10.sh`, on purpose: a COPY of the spool set per
# repetition and a FRESH store per repetition, both made and removed OUTSIDE
# the timed region. `ingest` writes `ingested.json` into the directory it
# converted and refuses a second pass over it -- that marker is the design,
# not an obstacle, and it is what stops one recording being minted twice.
#
# The converter is always this branch's `.venv/bin/sensorium` (`bin.sh`
# resolves it, and refuses anything else). `CONVERTER_REV` is REQUIRED and
# written verbatim into every cell: a wall quoted without the converter that
# produced it cannot be compared against the rung above it, which is the
# whole ladder.
#
# This prints the walls and their median. Every comparison -- against the
# reference wall, against the rung below -- is the record's.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

SPOOL="${1-}"; SCRATCH="${2-}"; LABEL="${3-}"; JOBS="${4-}"; N="${5-3}"
[ -n "$SPOOL" ] && [ -n "$SCRATCH" ] && [ -n "$LABEL" ] && [ -n "$JOBS" ] ||
  refuse "usage: e10p.sh <spool copy> <scratch dir> <label> <jobs> [n]"
[ -d "$SPOOL" ] || refuse "no such spool directory: $SPOOL"
case "$JOBS" in ''|*[!0-9]*) refuse "jobs must be a positive integer: $JOBS" ;; esac
[ "$JOBS" -ge 1 ] || refuse "jobs must be a positive integer: $JOBS"
case "$N" in ''|*[!0-9]*) refuse "n must be a positive integer: $N" ;; esac
[ "$N" -ge 1 ] || refuse "n must be a positive integer: $N"

#: The converter under measurement: always this branch's own
#: `.venv/bin/sensorium`, resolved by `bin.sh`. S5 rung 3 closes the door
#: Arm 0 used to walk through (defaulting here to the GLOBAL tool) -- an
#: instrument that can silently measure main's converter instead of the
#: branch's is the defect this rung exists to make impossible. `CONVERTER_REV`
#: stays required below: a wall without its converter's rev cannot be
#: compared even when the converter can no longer be the wrong one.
. "$HERE/bin.sh"
CONVERTER_REV="${CONVERTER_REV:-}"
[ -n "$CONVERTER_REV" ] ||
  refuse "CONVERTER_REV is required: a wall without its converter's rev cannot be compared"

#: The pre-registered load refusal, and how long the guard waits for it.
#: Identical to `arms.sh`'s, deliberately: two instruments in one slice that
#: guard at different thresholds do not measure the same box.
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20

# wait_for_load -- block until the 1-minute load is under LOAD_MAX, echo it.
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

mkdir -p "$SCRATCH/logs" || refuse "cannot write under $SCRATCH"
WALLS="$SCRATCH/e10p-$LABEL-walls.txt"
: >"$WALLS"

spools="$(find "$SPOOL" -maxdepth 1 -name '*.jsonl' | wc -l)"
bytes="$(find "$SPOOL" -maxdepth 1 -name '*.jsonl' -printf '%s\n' | awk '{t+=$1} END {print t+0}')"

for ((k = 1; k <= N; k++)); do
  # `refuse` inside a command substitution kills only the substitution's own
  # shell, so the guard's refusal is re-raised here -- otherwise the
  # repetition would go ahead under a load the pre-registration refuses.
  load="$(wait_for_load)"
  [ -n "$load" ] || refuse "the load guard refused before repetition $k"

  copy="$SCRATCH/e10p-$LABEL-copy-$k"
  store="$SCRATCH/e10p-$LABEL-store-$k"
  rm -rf "$copy" "$store"
  cp -r "$SPOOL" "$copy" || refuse "could not copy the spool set"
  rm -f "$copy/ingested.json"
  log="$SCRATCH/logs/e10p-$LABEL-$k.log"

  start="$(date +%s.%N)"
  SENSORIUM_DIR="$store" python3 "$HERE/rss_run.py" -- \
    "$SENSORIUM_BIN" ts ingest --jobs "$JOBS" "$copy" >"$log" 2>&1
  status=$?
  end="$(date +%s.%N)"

  traces="$(sed -n 's/.*traces: \([0-9]*\).*/\1/p' "$log" | tail -1)"
  maxrss="$(sed -n 's/^maxrss_kb=\([0-9]*\)$/\1/p' "$log" | tail -1)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$k" \
    "$(python3 -c 'import sys; print(float(sys.argv[2])-float(sys.argv[1]))' "$start" "$end")" \
    "$status" "${traces:-0}" "$load" "${maxrss:-0}" >>"$WALLS"
  rm -rf "$copy" "$store"
done

E10P_WALLS="$WALLS" E10P_LABEL="$LABEL" E10P_JOBS="$JOBS" \
  E10P_SPOOLS="$spools" E10P_BYTES="$bytes" \
  E10P_BIN="$SENSORIUM_BIN" E10P_REV="$CONVERTER_REV" \
  python3 "$HERE/e10p_report.py"
