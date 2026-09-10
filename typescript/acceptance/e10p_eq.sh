#!/usr/bin/env bash
# E10' equivalence: does the slice's converter write the trace main's wrote?
#
#   e10p_eq.sh <spool copy> <scratch dir> <bin-A> <rev-A> <bin-B> <rev-B>
#
# A converter that is faster and DIFFERENT has changed the product. Spec 3.5
# converts the pinned set twice -- once by main's converter at the T0 commit
# (side A), once by the slice's final converter (side B), each from its own
# fresh copy into its own fresh store -- pairs the traces by the test file
# each `run:` line names (plan P3), and runs `sensorium diff` once per pair.
#
# Nothing here is timed. The two ingests are the cost of the gate, not a
# measurement of it, and no load guard precedes them: a wall is never read
# from this instrument, so a busy box cannot bias it.
#
# THREE THINGS THIS SCRIPT DOES THAT THE GATE WOULD BE WRONG WITHOUT:
#
#   * ONE READER FOR EVERY PAIR. `sensorium diff <a> <b>` resolves both run
#     ids under ONE `$SENSORIUM_DIR`, so side A's traces are hard-linked
#     (`ln`, same filesystem, no copy, no rewrite) into side B's `traces/`
#     under their own names and every diff runs there with B's binary. A
#     DIVERGED then cannot be two readers disagreeing -- it is the writers.
#   * NO JOURNAL LEFT BEHIND. Both converters checkpoint on close, so a
#     `-wal` or `-shm` beside a `.db` means a trace was not finished being
#     written. The link would then carry a partial file into B's store and
#     the diff would read it as the trace. This script REFUSES on any such
#     file and deletes none of them: the leftover is the evidence.
#   * A RUN ID COLLISION IS A REFUSAL, not an overwrite. Ids are minted with
#     a random token, so a collision across the two stores is vanishingly
#     unlikely -- and if it happened, linking would silently make one side's
#     trace stand in for the other's, which is the one failure this gate
#     cannot notice on its own.
#
# The copies are removed once they have been converted; the two stores are
# LEFT IN PLACE. They are what the verdict was read from, and the caller --
# who knows whether the gate passed -- removes them.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

SPOOL="${1-}"; SCRATCH="${2-}"
BIN_A="${3-}"; REV_A="${4-}"; BIN_B="${5-}"; REV_B="${6-}"
[ -n "$SPOOL" ] && [ -n "$SCRATCH" ] && [ -n "$BIN_A" ] && [ -n "$REV_A" ] &&
  [ -n "$BIN_B" ] && [ -n "$REV_B" ] ||
  refuse "usage: e10p_eq.sh <spool copy> <scratch dir> <bin-A> <rev-A> <bin-B> <rev-B>"
[ -d "$SPOOL" ] || refuse "no such spool directory: $SPOOL"
command -v "$BIN_A" >/dev/null 2>&1 || refuse "side A's converter is not runnable: $BIN_A"
command -v "$BIN_B" >/dev/null 2>&1 || refuse "side B's converter is not runnable: $BIN_B"

mkdir -p "$SCRATCH/logs" || refuse "cannot write under $SCRATCH"
COPY_A="$SCRATCH/e10p-eq-copy-a"; STORE_A="$SCRATCH/e10p-eq-store-a"
COPY_B="$SCRATCH/e10p-eq-copy-b"; STORE_B="$SCRATCH/e10p-eq-store-b"
LOG_A="$SCRATCH/logs/e10p-eq-ingest-a.log"
LOG_B="$SCRATCH/logs/e10p-eq-ingest-b.log"

# ingest_side <label> <bin> <copy> <store> <log>  -- one fresh copy converted
# into one fresh store, at the converter's own default job count.
ingest_side() {
  local label="$1" bin="$2" copy="$3" store="$4" log="$5" status
  rm -rf "$copy" "$store"
  cp -r "$SPOOL" "$copy" || refuse "side $label: could not copy the spool set"
  rm -f "$copy/ingested.json"
  mkdir -p "$store" || refuse "side $label: cannot make a store"
  SENSORIUM_DIR="$store" "$bin" ts ingest "$copy" >"$log" 2>&1
  status=$?
  [ "$status" -eq 0 ] || refuse "side $label: ingest exited $status -- see $log"
  rm -rf "$copy"
}

# no_journal <label> <store>  -- refuse if any trace kept a WAL or a shm.
no_journal() {
  local label="$1" left
  left="$(find "$2/traces" -maxdepth 1 \( -name '*-wal' -o -name '*-shm' \) -printf '%f ' 2>/dev/null)"
  [ -z "$left" ] ||
    refuse "side $label left a journal beside a trace, so a trace was not finished: $left"
}

# link_a_into_b -- side A's traces under side B's store, one reader for both.
link_a_into_b() {
  local db name
  for db in "$STORE_A"/traces/*.db; do
    [ -e "$db" ] || refuse "side A wrote no traces"
    name="$(basename "$db")"
    [ -e "$STORE_B/traces/$name" ] &&
      refuse "run id collision across the two stores: $name -- linking would hide one trace behind the other"
    ln "$db" "$STORE_B/traces/$name" ||
      refuse "could not hard-link $name into side B's store (are the stores on one filesystem?)"
  done
}

ingest_side A "$BIN_A" "$COPY_A" "$STORE_A" "$LOG_A"
ingest_side B "$BIN_B" "$COPY_B" "$STORE_B" "$LOG_B"
no_journal A "$STORE_A"
no_journal B "$STORE_B"
link_a_into_b

spools="$(find "$SPOOL" -maxdepth 1 -name '*.jsonl' | wc -l)"

E10P_EQ_LOG_A="$LOG_A" E10P_EQ_LOG_B="$LOG_B" \
  E10P_EQ_STORE_A="$STORE_A" E10P_EQ_STORE_B="$STORE_B" \
  E10P_EQ_BIN_A="$BIN_A" E10P_EQ_REV_A="$REV_A" \
  E10P_EQ_BIN_B="$BIN_B" E10P_EQ_REV_B="$REV_B" \
  E10P_EQ_SPOOLS="$spools" \
  python3 "$HERE/e10p_eq_report.py"
