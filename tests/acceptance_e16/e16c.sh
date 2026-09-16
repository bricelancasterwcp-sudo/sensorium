#!/usr/bin/env bash
# E16 part C's launcher: start `e16c.py` DETACHED and print where to look.
#
#   e16c.sh <work root> <out dir> <run label>
#
# Part C copies this box's own store, runs `sensorium redact --all` over the
# copy twice -- once with `--dry-run`, once for real -- greps the copy for
# the token's bytes before and after, opens every trace again and reads the
# modes. §1's amendment caps it at 45 minutes, so it outlives the terminal
# it was started from and the only honest way to read it is to wait for the
# marker rather than for the process. `setsid` puts it in a session of its
# own, `nohup` detaches it from this terminal's HUP, and everything it
# prints goes to `<out>/e16c.log`.
#
# THREE ARGUMENTS, NOT FIVE: part C records nothing, so there is no node
# directory and no driver to rebuild (R37's phase has no subject here). The
# only binary is `$REPO/.venv/bin/python`, and `preflight` refuses unless
# `importlib.metadata` reads this branch's version out of it.
#
# `<run label>` names this run's own directories under the work root:
# `store-<label>` and `<label>-transcripts`. One work root can then hold a
# measurement and a re-measurement side by side without either sweeping the
# other's files.
#
# Nothing here is a location. Both paths are arguments, and the work root is
# where every byte this measurement writes goes -- the copy, the transcripts
# and the raw record.
#
#   E16_LIVE   The store to COPY OUT OF, default `~/.sensorium`. Read only:
#              the instrument copies out of it and never writes into it, and
#              the retrofit of the live store is a post-merge chore that is
#              Brice's to run (C18).
#
#   E16_DRY_FINDINGS
#              What the dry run that preceded THIS measurement found, one
#              finding per line, carried into the raw record so §4 can say
#              it. §1's record has to show a dry-run reading; a field beats
#              somebody remembering to type one.
#
#   E16_DRY=1  REHEARSALS ONLY -- fabricate three synthetic traces carrying
#              a `dry-` decoy INSTEAD of copying the live store (P11), cap
#              every timer at a tenth, and stamp `dry_run: true` in the raw
#              record, which `assemble_e16c.py` refuses. Point it at a work
#              root of its own: a rehearsal leaves a store behind, and the
#              measurement is made into a FRESH one.
#
# Read nothing before `<out>/e16c.DONE` (or `.FAILED`) exists: a raw record
# written mid-phase is a partial record, and it says so in its own `status`.
#
# The token's value is never printed -- not by this file, not by `e16c.py`,
# not into the log -- and the record cites `sha256(value)[:8]` only.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

refuse() { printf 'refused: %s\n' "$1" >&2; exit 2; }

WORK="${1-}"; OUT="${2-}"; LABEL="${3-}"
[ -n "$WORK" ] && [ -n "$OUT" ] && [ -n "$LABEL" ] ||
  refuse "usage: e16c.sh <work root> <out dir> <run label>"
case "$LABEL" in
  *[!a-z0-9]*) refuse "run label must be lowercase letters and digits: $LABEL" ;;
esac
[ -x "$REPO/.venv/bin/python" ] ||
  refuse "no $REPO/.venv/bin/python: part C runs under this branch's own venv"

LIVE="${E16_LIVE:-$HOME/.sensorium}"
[ -d "$LIVE/traces" ] || refuse "no traces directory under $LIVE"
[ -f "$LIVE/redaction.key" ] || refuse "no redaction.key under $LIVE"

# The copy is made ONCE, into a fresh directory: a store left by an earlier
# attempt is at whatever state that attempt's retrofit left it in, and
# measuring into it would read `already clean` for every trace.
[ -e "$WORK/store-$LABEL" ] &&
  refuse "$WORK/store-$LABEL exists: part C is measured ONCE, into a fresh copy; delete it before measuring again"
[ -e "$OUT/e16c.DONE" ] || [ -e "$OUT/e16c.FAILED" ] &&
  refuse "$OUT already holds a marker from an earlier run"

mkdir -p "$WORK" || refuse "cannot write under $WORK"
mkdir -p "$OUT" || refuse "cannot write under $OUT"

# Absolute, so a relative argument cannot resolve against the runner's cwd.
WORK="$(cd "$WORK" && pwd)"
OUT="$(cd "$OUT" && pwd)"
LIVE="$(cd "$LIVE" && pwd)"

export E16_WORK="$WORK" E16_OUT="$OUT" E16_LIVE="$LIVE"
export E16_LABEL="$LABEL"
export E16_DRY="${E16_DRY:-0}"
export E16_DRY_FINDINGS="${E16_DRY_FINDINGS:-}"
export PYTHONDONTWRITEBYTECODE=1

setsid nohup "$REPO/.venv/bin/python" "$HERE/e16c.py" \
  > "$OUT/e16c.log" 2>&1 &
pid=$!

printf 'e16c launched: pid %s\n' "$pid"
printf '  work:    %s\n' "$WORK"
printf '  out:     %s\n' "$OUT"
printf '  copied:  %s\n' "$LIVE"
printf '  log:     %s/e16c.log\n' "$OUT"
printf '  raw:     %s/results-c.json\n' "$OUT"
printf '  markers: %s/e16c.DONE | %s/e16c.FAILED\n' "$OUT" "$OUT"
printf '  label:   %s\n' "$LABEL"
printf '  dry run: %s\n' "$E16_DRY"
printf '  dry findings carried: %s\n' \
  "$(printf '%s' "$E16_DRY_FINDINGS" | grep -c . || true)"
