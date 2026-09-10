#!/usr/bin/env bash
# Superseded by e10p.sh (E10′, slice 2); kept as E10's instrument.
# E10: what does conversion cost?
#
#   e10.sh <spool dir> <scratch dir> <label> [n]
#
# `sensorium ts ingest` over a copy of a spool set a run already left behind,
# n times, median reported. A COPY each time, and a fresh store each time,
# because ingest writes `ingested.json` into the directory it converted and
# refuses a second pass over it -- which is the design, not an obstacle: the
# marker is what stops one recording being minted twice.
#
# The copy and the store teardown are outside the timed region; what is timed
# is the command and nothing else.
#
# The rule compares the FULL-SUITE median against the plain wall's median.
# That comparison is the assembler's; this prints the walls.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

SPOOL="${1-}"; SCRATCH="${2-}"; LABEL="${3-}"; N="${4-3}"
[ -n "$SPOOL" ] && [ -n "$SCRATCH" ] && [ -n "$LABEL" ] ||
  refuse "usage: e10.sh <spool dir> <scratch dir> <label> [n]"
[ -d "$SPOOL" ] || refuse "no such spool directory: $SPOOL"

mkdir -p "$SCRATCH/logs" || refuse "cannot write under $SCRATCH"
WALLS="$SCRATCH/e10-$LABEL-walls.txt"
: >"$WALLS"

spools="$(find "$SPOOL" -maxdepth 1 -name '*.jsonl' | wc -l)"
bytes="$(find "$SPOOL" -maxdepth 1 -name '*.jsonl' -printf '%s\n' | awk '{t+=$1} END {print t+0}')"

for ((k = 1; k <= N; k++)); do
  copy="$SCRATCH/e10-$LABEL-copy-$k"
  store="$SCRATCH/e10-$LABEL-store-$k"
  rm -rf "$copy" "$store"
  cp -r "$SPOOL" "$copy" || refuse "could not copy the spool set"
  rm -f "$copy/ingested.json"
  log="$SCRATCH/logs/e10-$LABEL-$k.log"
  start="$(date +%s.%N)"
  SENSORIUM_DIR="$store" sensorium ts ingest "$copy" >"$log" 2>&1
  status=$?
  end="$(date +%s.%N)"
  traces="$(sed -n 's/.*traces: \([0-9]*\).*/\1/p' "$log" | tail -1)"
  printf '%s\t%s\t%s\t%s\n' "$k" \
    "$(python3 -c 'import sys; print(float(sys.argv[2])-float(sys.argv[1]))' "$start" "$end")" \
    "$status" "${traces:-0}" >>"$WALLS"
  rm -rf "$copy" "$store"
done

E10_WALLS="$WALLS" E10_LABEL="$LABEL" E10_SPOOLS="$spools" E10_BYTES="$bytes" \
  python3 "$HERE/e10_report.py"
