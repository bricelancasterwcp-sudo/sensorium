#!/usr/bin/env bash
# E7': does the reader speak this recorder's words?
#
#   e7.sh <store> <run A> <run B> <out dir> <transcript> <repo root> \
#         <fn> <grep pattern> <watch at> <watch expr> <flow value>
#
# Runs every reader command on a product trace, keeps the transcript
# verbatim, and greps it for the eight words that would mean the reader had
# told a TypeScript user about machinery that is not there:
#
#   asyncio  "python ?"  cargo  coroutine  "Python's own"  threading/_thread
#   "Rust disposition"  "sensorium run --focus"
#
# The rule is 0 occurrences, and the count is over the transcript AS SAVED.
# Three literal paths are rewritten before the grep and before the file is
# committed -- the store root to `<store>`, the recorded project root to
# `<lens>` and the home directory to `<home>` -- because a committed file
# carries no box path. `info` prints the container's own command line and
# working directory, which is where they come from. Nothing else is touched:
# the transcript is what the commands printed.
#
# The second half is the reader's own vectors, `v23` and `v24`, which pin
# the TypeScript vocabulary in the test suite.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

STORE="${1-}"; RUN_A="${2-}"; RUN_B="${3-}"; OUT="${4-}"; TRANSCRIPT="${5-}"
REPO="${6-}"; FN="${7-}"; PATTERN="${8-}"; WATCH_AT="${9-}"; WATCH_EXPR="${10-}"
FLOW_VALUE="${11-}"
[ -n "$STORE" ] && [ -n "$RUN_A" ] && [ -n "$RUN_B" ] && [ -n "$OUT" ] &&
  [ -n "$TRANSCRIPT" ] && [ -n "$REPO" ] && [ -n "$FN" ] && [ -n "$PATTERN" ] &&
  [ -n "$WATCH_AT" ] && [ -n "$WATCH_EXPR" ] && [ -n "$FLOW_VALUE" ] ||
  refuse "usage: e7.sh <store> <run A> <run B> <out dir> <transcript> <repo root> <fn> <grep pattern> <watch at> <watch expr> <flow value>"

#: The reader under measurement. Default is the global tool; a rung that ships
#: a new reader passes its own, because "does the reader speak THIS recorder's
#: words" is a question about the reader this branch built.
SENSORIUM_BIN="${SENSORIUM_BIN:-sensorium}"
#: The interpreter that reads the trace's recorded project root, which is
#: one of the three literal paths rewritten out of the COMMITTED
#: transcript. It needs `sensorium` importable; the system python is not
#: obliged to have it, and a lookup that quietly failed would leave a box
#: path in a committed file.
E7_PYTHON="${E7_PYTHON:-python3}"
#: Which vectors the second half runs, as a `-k` expression. The default is
#: rung 1's pair; a later rung passes its own pre-registered list.
E7_VECTORS_K="${E7_VECTORS_K:-v23 or v24}"

mkdir -p "$OUT" "$(dirname "$TRANSCRIPT")" || refuse "cannot write the transcript"
RAW="$OUT/e7-raw.txt"
STATUSES="$OUT/e7-statuses.txt"
: >"$RAW"; : >"$STATUSES"

# say <label> -- run a reader command, printing it as typed above its output.
say() {
  local label="$1"; shift
  {
    printf '\n$ sensorium %s\n' "$*"
    SENSORIUM_DIR="$STORE" "$SENSORIUM_BIN" "$@" 2>&1
    printf -- '--- exit %s\n' "$?"
  } >>"$RAW"
  printf '%s\t%s\n' "$label" "$(tail -2 "$RAW" | sed -n 's/^--- exit \([0-9]*\)$/\1/p')" >>"$STATUSES"
}

{
  printf '# E7'"'"' — every reader command on one product trace\n'
  printf '#\n'
  printf '# Lens: %s\n' "$ACCEPT_LENS"
  printf '# Trace: a full-suite call-arm recording of one VTT test file.\n'
  printf '# Three literal paths are rewritten: the store root reads <store>,\n'
  printf '# the project root <lens> and the home directory <home>.\n'
  printf '# Taken: %s\n' "$(date -Iseconds)"
} >"$RAW"

say runs   runs
say info   info "$RUN_A"
say tree   tree "$RUN_A" --depth 3
say frame  frame "$RUN_A" --fn "$FN"
say grep   grep "$RUN_A" "$PATTERN" --limit 10
say excs   exceptions "$RUN_A" --limit 10
say watch  watch "$RUN_A" --at "$WATCH_AT" --expr "$WATCH_EXPR" --limit 10
say flow   flow "$RUN_A" --value "$FLOW_VALUE" --limit 10
say diff   diff "$RUN_A" "$RUN_B"
say refocus refocus "$RUN_A" --focus "$FN"

# The two rewrites, then the transcript is final.
LENS_ROOT="$(SENSORIUM_DIR="$STORE" "$E7_PYTHON" -c '
import sys
from sensorium.store.reader import Trace
from sensorium import paths
print(Trace.open(paths.find_trace(sys.argv[1])).meta.get("cwd", ""))' "$RUN_A" 2>/dev/null || true)"
python3 - "$RAW" "$TRANSCRIPT" "$STORE" "$LENS_ROOT" "$HOME" <<'PY'
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

# The vectors.
VECTORS="$OUT/e7-vectors.txt"
( cd "$REPO" && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
    -p no:cacheprovider tests/test_vectors.py -k "$E7_VECTORS_K" ) >"$VECTORS" 2>&1
vectors_status=$?

E7_TRANSCRIPT="$TRANSCRIPT" E7_STATUSES="$STATUSES" E7_VECTORS="$VECTORS" \
E7_VECTORS_K="$E7_VECTORS_K" \
E7_VECTORS_STATUS="$vectors_status" python3 "$HERE/e7_report.py"
