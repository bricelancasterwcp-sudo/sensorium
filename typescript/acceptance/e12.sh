#!/usr/bin/env bash
# E12's ONE recording session: the six arms, the resolver, and the hash list.
#
#   e12.sh <lens dir> <manifest file> <store dir> <out dir>
#
# S5 rung 4's acceptance records six `vitest run` invocations of ONE lens test
# file into a store that is EMPTY at T0 -- three unfocused (U1 U2 U3) and three
# focused (F1 F2 F3), interleaved U1 F1 U2 F2 U3 F3 as the record's §1 fixes --
# and then stops recording. Every endpoint of the rung is read afterwards, off
# those traces, by `e12_report.py`, `e12_h3.py`, `e12_cost.py` and `e12_h8.sh`.
#
# The order is §1's and is not an implementation detail:
#
#   1. manifest, before      `sha256sum -c` from inside the lens; a lens that
#                            moved is not the lens the hand count was read on,
#                            and the session stops before it starts
#   2. U1 F1 U2 F2 U3 F3     each behind the slice-2 load guard (`e6pp.sh`'s:
#                            1-minute load under 4.0, up to 90 tries 20 s
#                            apart), each wall taken around the driver
#   3. the resolver          `node <pkg>/src/resolve.mjs`, timed ONCE, on the
#                            same three specs the F arms carried. Task 5 left
#                            `Resolution.wall` unpersisted, so H7's resolver
#                            reading is this script's own timing or it is
#                            nothing
#   4. manifest, after       the arms are the last thing to have touched the
#                            lens, which is what the clause is about
#   5. the hash list         `traces/*.db`, `spool/*/*.jsonl` AND
#                            `invocations.jsonl`, from the store root, in
#                            `sha256sum -c` format -- taken AFTER the arms and
#                            BEFORE any read, so the reads' own journal lines
#                            are the pre-registered delta and nothing else
#
# The store must not exist, or must be empty: §1 says "a store that is EMPTY at
# T0", and a session that recorded into somebody else's traces would hash a set
# this rung never wrote. It is created here.
#
# WHAT IS PRE-REGISTERED AND WHAT IS A DRY RUN
# --------------------------------------------
# `SUBJECT` and `FOCUS_SPECS` below are §1's, written down: the test file
# `src/lib/diceQueue.test.ts` and the three `--focus diceQueue.ts:<fn>` specs.
# `E12_TEST` and `E12_FOCUS` override them and `E12_N` (default 3) overrides
# the runs per arm -- all three are for DRY RUNS ONLY, all three are recorded
# in the JSON, and `preregistered_subject` / `preregistered_n` say in the cell
# whether this session was the pre-registered one. An instrument that can only
# be exercised on the subject is one nobody checks before the session starts.
#
# `E12_HASHES` is where the hash list goes; it defaults to the record's own
# file, and a dry run points it at its own out directory rather than at a
# committed one.
#
# This prints the session's JSON on stdout and nothing else; the logs, the two
# manifest checks, the resolver's answer and the arms table stay under <out>.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"
. "$HERE/bin.sh"

LENS_DIR="${1-}"; MANIFEST="${2-}"; STORE="${3-}"; OUT="${4-}"
[ -n "$LENS_DIR" ] && [ -n "$MANIFEST" ] && [ -n "$STORE" ] && [ -n "$OUT" ] ||
  refuse "usage: e12.sh <lens dir> <manifest file> <store dir> <out dir>"
[ -d "$LENS_DIR" ] || refuse "no such lens directory: $LENS_DIR"
[ -f "$MANIFEST" ] || refuse "no such manifest: $MANIFEST"

#: The driver sets these three itself, per container; inherited from a caller
#: they would focus, spool or manifest a run nobody asked to.
unset SENSORIUM_FOCUS SENSORIUM_SPOOL SENSORIUM_MANIFEST_DIR

#: §1's subject and §1's three specs, in this rung's own words. Overridden
#: only by a dry run, which says so in the JSON.
SUBJECT="${E12_TEST:-src/lib/diceQueue.test.ts}"
DEFAULT_FOCUS='diceQueue.ts:parseDiceGroups diceQueue.ts:forcedDiceFromSource diceQueue.ts:buildDiceQueueEntry'
FOCUS_SPECS="${E12_FOCUS:-$DEFAULT_FOCUS}"
#: Runs per arm. Three is §1's; anything else is a dry run and says so.
N="${E12_N:-3}"
case "$N" in ''|*[!0-9]*) refuse "E12_N must be a positive integer: $N" ;; esac
[ "$N" -ge 1 ] || refuse "E12_N must be a positive integer: $N"
#: What RECORDED this session, named by the caller rather than inherited from
#: `LENS.txt` -- that string names the recorder that produced the LENS, which
#: is a different recorder from the one running here (rung 3's rule, and
#: `e6pp.sh`'s refusal, in this rung's words).
E12_RECORDER="${E12_RECORDER:-}"
[ -n "$E12_RECORDER" ] ||
  refuse "E12_RECORDER is required: name the recorder that ran (its versions and its commit); the lens string names the LENS's recorder, not this one"
E12_REV="${E12_REV:-}"
[ -n "$E12_REV" ] ||
  refuse "E12_REV is required: the FULL sha of the commit the recorder ran at"
export E12_RECORDER E12_REV

#: The load guard, identical to `e6pp.sh`'s and `arms.sh`'s: two instruments
#: in one rung that guard at different thresholds do not measure the same box.
LOAD_MAX=4.0
LOAD_TRIES=90
LOAD_SLEEP=20

REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
HASHES="${E12_HASHES:-$REPO_ROOT/docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-tracehashes.txt}"

# The store: absent, or present and empty. Never somebody else's traces.
if [ -e "$STORE" ]; then
  [ -d "$STORE" ] || refuse "the store path is not a directory: $STORE"
  [ -z "$(ls -A "$STORE")" ] ||
    refuse "the store is not empty; §1 records into a store that is EMPTY at T0 -- delete it and relaunch from zero"
fi
mkdir -p "$STORE" || refuse "cannot create the store"
mkdir -p "$OUT/logs" || refuse "cannot write under $OUT"
mkdir -p "$(dirname "$HASHES")" || refuse "cannot write the hash list"

JSONL="$OUT/arms.jsonl"
: >"$JSONL"
BEFORE_CHECK="$OUT/e12-manifest-before.txt"
AFTER_CHECK="$OUT/e12-manifest-after.txt"
RESOLVE_OUT="$OUT/resolve.json"

# The three specs as `--focus` flags, and as the unit-separated variable the
# driver hands the resolver. `read -a` rather than an unquoted expansion, so
# the split is on whitespace and on nothing else.
read -r -a SPEC_ARRAY <<<"$FOCUS_SPECS"
FOCUS_FLAGS=()
for spec in "${SPEC_ARRAY[@]}"; do FOCUS_FLAGS+=(--focus "$spec"); done
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

# one_run <arm> <index> -- one guarded arm, one JSON line on `arms.jsonl`.
one_run() {
  local arm="$1" idx="$2"
  local log="$OUT/logs/e12-$arm$idx.log"
  local load start end status
  load="$(wait_for_load)"
  # `refuse` inside a command substitution kills only the substitution's own
  # shell, so the guard's refusal is re-raised here or the run would go ahead
  # under a load the pre-registration refuses.
  [ -n "$load" ] || refuse "the load guard refused before $arm$idx"
  start="$(date +%s.%N)"
  case "$arm" in
    U) ( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
           "$SENSORIUM_BIN" ts run -- npx vitest run "$SUBJECT" ) >"$log" 2>&1 ;;
    F) ( cd "$LENS_DIR" && SENSORIUM_DIR="$STORE" \
           "$SENSORIUM_BIN" ts run "${FOCUS_FLAGS[@]}" -- npx vitest run "$SUBJECT" ) >"$log" 2>&1 ;;
    *) refuse "unknown arm: $arm" ;;
  esac
  status=$?
  end="$(date +%s.%N)"
  # One JSON line per run, assembled in python because a shell that builds
  # JSON by hand gets a path with a quote in it wrong exactly once. Nothing
  # here judges the run: `run:` lines, the invocation, the two suite lines
  # and the wall, as the driver and vitest printed them.
  ARM="$arm" IDX="$idx" LOG="$log" LOAD="$load" START="$start" END="$end" \
  STATUS="$status" SUBJECT="$SUBJECT" python3 - <<'PY' >>"$JSONL"
import json, os, re, sys
from pathlib import Path
env = os.environ
log = Path(env["LOG"])
text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
lines = text.splitlines()
runs = [ln.strip() for ln in lines if ln.startswith("run: ")]
run_ids = [ln.split()[1] for ln in runs]
files_line = next((ln.rstrip() for ln in lines if ln.strip().startswith("Test Files")), None)
tests_line = next((ln.rstrip() for ln in lines if ln.strip().startswith("Tests ")), None)
duration = next((ln.strip() for ln in lines if ln.lstrip().startswith("Duration")), None)
inv = next((ln.split()[1] for ln in reversed(lines) if ln.startswith("invocation: ")), None)
# The run this rung reads is the container that ran the SUBJECT file. A
# vitest run of one file records one container, but the id is chosen by what
# the line says rather than by its position, and every `run:` line is kept so
# a second container is visible rather than silently dropped.
subject = env["SUBJECT"]
subject_runs = [ln.split()[1] for ln in runs
                if re.search(r"\bfile: (\S+)", ln)
                and re.search(r"\bfile: (\S+)", ln).group(1).endswith(subject)]
json.dump({
    "arm": env["ARM"], "run": int(env["IDX"]),
    "wall": round(float(env["END"]) - float(env["START"]), 4),
    "load_1min": float(env["LOAD"]), "exit": int(env["STATUS"]),
    "run_lines": runs, "run_ids": run_ids, "subject_run_ids": subject_runs,
    "run_id": subject_runs[0] if len(subject_runs) == 1 else None,
    "invocation": inv, "test_files_line": files_line,
    "tests_line": tests_line, "duration_line": duration,
    "log": log.name,
}, sys.stdout, sort_keys=False)
sys.stdout.write("\n")
PY
}

# 1. the manifest, before anything.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$BEFORE_CHECK" 2>&1
before_status=$?
MANIFEST_LINES="$(wc -l <"$MANIFEST" | tr -d ' ')"
before_ok="$(grep -c ': OK$' "$BEFORE_CHECK" || true)"
if [ "$before_status" -ne 0 ] || [ "$before_ok" != "$MANIFEST_LINES" ] ||
   grep -q FAILED "$BEFORE_CHECK"; then
  refuse "the lens moved: $BEFORE_CHECK reads $before_ok OK of $MANIFEST_LINES (exit $before_status); nothing is recorded on a lens that is not the one the hand count was read on"
fi

# 2. the arms, interleaved U1 F1 U2 F2 U3 F3 (plan P13).
for ((k = 1; k <= N; k++)); do one_run U "$k"; one_run F "$k"; done

# 3. the resolver, timed once, on the same three specs the F arms carried.
r_start="$(date +%s.%N)"
SENSORIUM_TS_ROOT="$LENS_DIR" SENSORIUM_FOCUS="$FOCUS_ENV" \
  node "$REPO_ROOT/typescript/src/resolve.mjs" >"$RESOLVE_OUT" 2>"$OUT/resolve-err.txt"
r_status=$?
r_end="$(date +%s.%N)"

# 4. the manifest again.
( cd "$LENS_DIR" && sha256sum -c "$MANIFEST" ) >"$AFTER_CHECK" 2>&1
after_status=$?

# 5. the hash list, from the store root: the traces, every spool line, and the
#    journal. Written before any read command runs.
( cd "$STORE" && sha256sum traces/*.db spool/*/*.jsonl invocations.jsonl ) \
  >"$HASHES" 2>"$OUT/hashes-err.txt"
hash_status=$?
JOURNAL_LINES="$(wc -l <"$STORE/invocations.jsonl" 2>/dev/null | tr -d ' ')"

# The session's own cell: what ran, what the two manifest checks read, what
# the resolver answered, and the hash list's shape. It gates nothing -- every
# endpoint is read from these artefacts afterwards -- but a session whose
# manifest moved, whose store was not empty, or whose hash list is short is a
# session the record must be able to say that about.
E12_OUT="$OUT" E12_ARMS="$JSONL" E12_STORE="$STORE" \
E12_SUBJECT="$SUBJECT" E12_FOCUS_SPECS="$FOCUS_SPECS" \
E12_DEFAULT_FOCUS="$DEFAULT_FOCUS" E12_N="$N" \
E12_RESOLVE="$RESOLVE_OUT" E12_RESOLVE_WALL="$(awk -v a="$r_start" -v b="$r_end" 'BEGIN{printf "%.4f", b-a}')" \
E12_RESOLVE_STATUS="$r_status" E12_RESOLVE_ERR="$OUT/resolve-err.txt" \
E12_MANIFEST_LINES="$MANIFEST_LINES" \
E12_MANIFEST_SHA="$(sha256sum "$MANIFEST" | cut -d' ' -f1)" \
E12_MANIFEST_BEFORE="$BEFORE_CHECK" E12_MANIFEST_AFTER="$AFTER_CHECK" \
E12_MANIFEST_BEFORE_STATUS="$before_status" \
E12_MANIFEST_AFTER_STATUS="$after_status" \
E12_HASHES_FILE="$HASHES" E12_HASHES_STATUS="$hash_status" \
E12_JOURNAL_LINES="${JOURNAL_LINES:-0}" E12_BIN="$SENSORIUM_BIN" \
E12_LOAD_MAX="$LOAD_MAX" E12_HERE="$HERE" \
  python3 - <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["E12_HERE"])
from lens import cell, emit                                    # noqa: E402

env = os.environ


def check(path: str) -> dict:
    """One `sha256sum -c` run, read back: OK lines, FAILED lines, total."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    rows = text.splitlines()
    return {"ok": sum(1 for ln in rows if ln.endswith(": OK")),
            "failed": [ln for ln in rows if "FAILED" in ln], "lines": len(rows)}


rows = [json.loads(ln) for ln in open(env["E12_ARMS"], encoding="utf-8")
        if ln.strip()]
hashes = Path(env["E12_HASHES_FILE"])
listed = [ln for ln in hashes.read_text(encoding="utf-8").splitlines() if ln.strip()]
resolver_text = Path(env["E12_RESOLVE"]).read_text(encoding="utf-8")
try:
    resolver = json.loads(resolver_text)
except json.JSONDecodeError as e:
    resolver = {"_unparsable": f"{e}", "raw": resolver_text[:400]}

want_ok = int(env["E12_MANIFEST_LINES"])
before, after = check(env["E12_MANIFEST_BEFORE"]), check(env["E12_MANIFEST_AFTER"])
n = int(env["E12_N"])
preregistered_n = n == 3
preregistered_subject = (env["E12_SUBJECT"] == "src/lib/diceQueue.test.ts"
                         and env["E12_FOCUS_SPECS"] == env["E12_DEFAULT_FOCUS"])
dropped = []
if not preregistered_n:
    dropped.append(f"E12_N={n}: a DRY RUN, not §1's three runs per arm")
if not preregistered_subject:
    dropped.append("the subject or the focus specs were overridden: a DRY "
                   "RUN, not §1's `src/lib/diceQueue.test.ts` and its three "
                   "`diceQueue.ts:` specs")
if int(env["E12_HASHES_STATUS"]) != 0:
    dropped.append("sha256sum over the store's traces, spools and journal "
                   f"exited {env['E12_HASHES_STATUS']}")
if int(env["E12_RESOLVE_STATUS"]) != 0:
    dropped.append(f"the resolver exited {env['E12_RESOLVE_STATUS']}")

# `value` is how many arms ran; `n` is how many §1 asks for. Neither is a
# verdict: the six arms are the session, and every endpoint is read off them.
emit(cell(
    len(rows), 2 * n, dropped,
    rule="six arms into an empty store, the lens unmoved, the hash list "
         "taken before any read",
    preregistered_subject=preregistered_subject, preregistered_n=preregistered_n,
    subject=env["E12_SUBJECT"], focus_specs=env["E12_FOCUS_SPECS"].split(),
    n_per_arm=n, arms=rows,
    resolver={"exit": int(env["E12_RESOLVE_STATUS"]),
              "wall": float(env["E12_RESOLVE_WALL"]),
              "stderr": Path(env["E12_RESOLVE_ERR"]).read_text(encoding="utf-8"),
              **({} if "_unparsable" in resolver else
                 {"matched": [f"{m['rel']}:{m['qualname']}"
                              for m in resolver.get("matched", [])],
                  "matched_rows": resolver.get("matched", []),
                  "unmatched": resolver.get("unmatched", []),
                  "excluded_only": resolver.get("excluded_only", []),
                  "files_scanned": resolver.get("files_scanned"),
                  "files_unparsable": resolver.get("files_unparsable")}),
              **({"unparsable": resolver["_unparsable"], "raw": resolver["raw"]}
                 if "_unparsable" in resolver else {})},
    manifest_before={**before, "exit": int(env["E12_MANIFEST_BEFORE_STATUS"]),
                     "want_ok": want_ok, "sha256": env["E12_MANIFEST_SHA"]},
    manifest_after={**after, "exit": int(env["E12_MANIFEST_AFTER_STATUS"]),
                    "want_ok": want_ok,
                    "identical": (int(env["E12_MANIFEST_AFTER_STATUS"]) == 0
                                  and not after["failed"]
                                  and after["ok"] == want_ok)},
    hash_list={"path": env["E12_HASHES_FILE"], "exit": int(env["E12_HASHES_STATUS"]),
               "lines": len(listed),
               "sha256": hashlib.sha256(hashes.read_bytes()).hexdigest(),
               "db": sum(1 for ln in listed if ln.endswith(".db")),
               "spool": sum(1 for ln in listed if "  spool/" in ln),
               "journal": sum(1 for ln in listed
                              if ln.endswith("  invocations.jsonl"))},
    journal_lines_at_hash_time=int(env["E12_JOURNAL_LINES"]),
    # The store's real path, so the assembler can verify the hash list from
    # its root. Redacted to `<store>` before anything is committed -- this
    # file is an artefact under <out>, not a committed one.
    store=env["E12_STORE"],
    load_max=float(env["E12_LOAD_MAX"]), recorder_bin=env["E12_BIN"],
    recorder=os.environ.get("E12_RECORDER"),
    recorder_rev=os.environ.get("E12_REV"),
))
PY
