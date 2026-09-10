#!/usr/bin/env bash
# Superseded by e6pp.sh (E6″, slice 2); kept as E6′'s instrument.
# E6': is a plain run contaminated?
#
#   e6.sh <lens dir> <manifest file> <out dir> <plain band lo> <plain band hi>
#
# Run LAST, after every instrumented run of the acceptance, because that is
# the only order in which it can see what they left behind. Four facts:
#
#   manifest   `sha256sum -c` of the pre-run manifest -- identical, 0 failed
#   plain      one plain `npx vitest run`: 372/4278, and its wall inside the
#              plain arm's own band (its min..max, passed in)
#   markers    `grep -rl __srt` -- the runtime's own token, which only
#              instrumented source carries -- over every cache directory a
#              vite/vitest run writes: `node_modules/.vite*`, `.vite`,
#              `node_modules/.vitest*`. Zero files.
#   wrapper    `node_modules/.sensorium` gone
#
# The band is passed in rather than recomputed here: it is the plain arm's,
# and an instrument that derived its own band from its own single run would
# be comparing a number against itself.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

LENS_DIR="${1-}"; MANIFEST="${2-}"; OUT="${3-}"; LO="${4-}"; HI="${5-}"
[ -n "$LENS_DIR" ] && [ -n "$MANIFEST" ] && [ -n "$OUT" ] && [ -n "$LO" ] && [ -n "$HI" ] ||
  refuse "usage: e6.sh <lens dir> <manifest file> <out dir> <band lo> <band hi>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"
[ -f "$MANIFEST" ] || refuse "no such manifest: $MANIFEST"

mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
CHECK="$OUT/logs/e6-manifest-check.txt"
PLAIN="$OUT/logs/e6-plain-after.log"
MARKERS="$OUT/logs/e6-markers.txt"

# 1. the manifest, verified where it was taken
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$CHECK" 2>&1
manifest_status=$?

# 2. one plain run
start="$(date +%s.%N)"
( cd "$LENS_DIR" && npx vitest run ) >"$PLAIN" 2>&1
plain_status=$?
end="$(date +%s.%N)"

# 3. the marker grep, over every cache directory a vite/vitest run writes
: >"$MARKERS"
for d in "$LENS_DIR"/node_modules/.vite* "$LENS_DIR"/.vite "$LENS_DIR"/node_modules/.vitest*; do
  [ -e "$d" ] || continue
  printf 'searched: %s\n' "${d#"$LENS_DIR"/}" >>"$MARKERS"
  grep -rl -- '__srt' "$d" 2>/dev/null | sed "s#^$LENS_DIR/#hit: #" >>"$MARKERS"
done

# 4. the wrapper directory
wrapper='absent'
[ -e "$LENS_DIR/node_modules/.sensorium" ] && wrapper='present'

E6_CHECK="$CHECK" E6_PLAIN="$PLAIN" E6_MARKERS="$MARKERS" \
E6_MANIFEST_STATUS="$manifest_status" E6_PLAIN_STATUS="$plain_status" \
E6_WALL="$(python3 -c 'import sys; print(float(sys.argv[2])-float(sys.argv[1]))' "$start" "$end")" \
E6_LO="$LO" E6_HI="$HI" E6_WRAPPER="$wrapper" \
  python3 "$HERE/e6_report.py"
