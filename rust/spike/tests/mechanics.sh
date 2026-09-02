#!/usr/bin/env bash
# THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike): E7 and E8 on the PROBE
# workspace. Task 5 runs the same checks against bloomery under its own
# preflight; nothing here touches bloomery.
#
# One line per check: `ok: <name>` or `FAIL: <name>: <why>`. Exit non-zero if
# any check failed. The cargo `Compiling`/`Fresh` lines every E8 check counted
# are PRINTED, not summarised away -- a count nobody can see is not evidence.
#
# Env:
#   SENSORIUM_MECHANICS_TARGET  reuse a target dir instead of a fresh one
#   SENSORIUM_MECHANICS_KEEP=1  keep the target dir and the logs
#
# Falsification: every check here was made to FAIL once, by breaking exactly the
# mechanism it claims to test. The breakages and their output are recorded in
# the task report; they are deliberately NOT wired into this script, because a
# sabotage switch that leaks into a real measurement is worse than no switch.

set -uo pipefail

SPIKE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$SPIKE/probes/ws"
EXT="$SPIKE/probes/ext"
DRIVER="$SPIKE/target/debug/cargo-sensorium"

FAILS=0
pass() { echo "ok: $1"; }
fail() { echo "FAIL: $1: $2"; FAILS=$((FAILS + 1)); }

LOGS="$(mktemp -d)"
if [ -n "${SENSORIUM_MECHANICS_TARGET:-}" ]; then
  TARGET="$SENSORIUM_MECHANICS_TARGET"
  OWN_TARGET=0
else
  TARGET="$(mktemp -d)"
  OWN_TARGET=1
fi
cleanup() {
  if [ "${SENSORIUM_MECHANICS_KEEP:-0}" = "1" ]; then
    echo "kept: logs=$LOGS target=$TARGET"
    return
  fi
  rm -rf "$LOGS"
  if [ "$OWN_TARGET" = "1" ]; then rm -rf "$TARGET"; fi
  return 0
}
trap cleanup EXIT

export CARGO_TARGET_DIR="$TARGET"
export SENSORIUM_SPIKE_ROOT="$SPIKE"

# ---------------------------------------------------------------- helpers ---

# Workspace packages cargo said it COMPILED (as opposed to found Fresh).
compiled() { grep -hE '^ *Compiling (probe-core|probe-app|probe-ext) ' "$1" | awk '{print $2}' | sort -u | tr '\n' ' '; }
freshset() { grep -hE '^ *Fresh (probe-core|probe-app|probe-ext) ' "$1" | awk '{print $2}' | sort -u | tr '\n' ' '; }

show_counts() {
  echo "    [$1] Compiling: $(compiled "$2")| Fresh: $(freshset "$2")"
}

plain_build() { (cd "$WS" && cargo test --no-run -v) >"$1" 2>&1; }
instr_build() { (cd "$WS" && "$DRIVER" sensorium test --no-run -v) >"$1" 2>&1; }

# The path of one test executable, by target name, from cargo's JSON stream.
exe_of() {
  python3 -c '
import json, sys
want = sys.argv[1]
found = None
for line in sys.stdin:
    try:
        v = json.loads(line)
    except Exception:
        continue
    if v.get("reason") != "compiler-artifact":
        continue
    if v.get("target", {}).get("name") != want:
        continue
    if not v.get("profile", {}).get("test"):
        continue
    if v.get("executable"):
        found = v["executable"]
print(found or "")
' "$1"
}

plain_exe() { (cd "$WS" && cargo test --no-run --message-format=json 2>/dev/null) | exe_of "$1"; }
instr_exe() { (cd "$WS" && "$DRIVER" sensorium test --no-run --message-format=json 2>/dev/null) | exe_of "$1"; }

# Two per-run values that say nothing about E7 and would swamp it: libtest's
# wall times, and the OS thread id rustc 1.96 prints in the panic header
# (`thread 'name' (2636689) panicked at ...`). The LOCATION in that same line is
# NOT masked -- it is exactly what E7 measures.
mask() {
  sed -E -e 's/finished in [0-9]+\.[0-9]+s/finished in <masked>/g' \
         -e "s/^(thread '[^']*') \\([0-9]+\\)/\\1 (<tid>)/"
}
# Every `<file>.rs:<line>` (and `:<col>`) the output mentions, in order.
locations() { grep -oE '[A-Za-z0-9_./-]+\.rs:[0-9]+(:[0-9]+)?' | tr '\n' ' '; }

tree_digest() {
  ( cd "$1" && find . -path ./target -prune -o -type f -print0 | sort -z |
      xargs -0 sha256sum ) 2>/dev/null
}

echo "== rung-1 mechanics: probe workspace =="
echo "   spike=$SPIKE"
echo "   target=$TARGET"

# ---------------------------------------------------------------- driver ---
if ! (cd "$SPIKE" && env -u CARGO_TARGET_DIR cargo build -p cargo-sensorium >"$LOGS/driver-build.log" 2>&1); then
  echo "FAIL: driver_builds: $(tail -3 "$LOGS/driver-build.log")"
  exit 1
fi

LOCK_BEFORE="$(sha256sum "$WS/Cargo.lock" | awk '{print $1}')"
TREE_BEFORE="$LOGS/tree.before"
{ tree_digest "$WS"; tree_digest "$EXT"; } > "$TREE_BEFORE"

# ------------------------------------------------------------------ E8 ------

if plain_build "$LOGS/plain1.log"; then pass "probe_workspace_builds_plain"; else
  fail "probe_workspace_builds_plain" "$(tail -3 "$LOGS/plain1.log" | tr '\n' ' ')"; fi
show_counts "plain #1" "$LOGS/plain1.log"

if instr_build "$LOGS/instr1.log"; then pass "probe_workspace_builds_instrumented"; else
  fail "probe_workspace_builds_instrumented" "$(tail -3 "$LOGS/instr1.log" | tr '\n' ' ')"; fi
show_counts "instrumented #1" "$LOGS/instr1.log"

instr_build "$LOGS/instr2.log"
show_counts "instrumented #2 (E8a)" "$LOGS/instr2.log"
if [ -z "$(compiled "$LOGS/instr2.log")" ]; then
  pass "e8a_second_instrumented_build_compiles_nothing"
else
  fail "e8a_second_instrumented_build_compiles_nothing" "recompiled: $(compiled "$LOGS/instr2.log")"
fi

plain_build "$LOGS/plain2.log"
show_counts "plain #2 (E8c)" "$LOGS/plain2.log"
if [ -z "$(compiled "$LOGS/plain2.log")" ]; then
  pass "e8c_plain_build_after_instrumented_compiles_nothing"
else
  fail "e8c_plain_build_after_instrumented_compiles_nothing" "recompiled: $(compiled "$LOGS/plain2.log")"
fi

# --- the sentinel: an artifact set that coexists must also STAY plain --------
PLAIN_EXE="$(plain_exe probe_app)"
INSTR_EXE="$(instr_exe probe_app)"
if [ -z "$PLAIN_EXE" ] || [ -z "$INSTR_EXE" ]; then
  fail "sentinel_plain_binary_writes_no_spool" "could not locate a probe_app test binary (plain='$PLAIN_EXE' instr='$INSTR_EXE')"
  fail "sentinel_instrumented_binary_writes_a_spool" "could not locate a probe_app test binary"
else
  if [ "$PLAIN_EXE" = "$INSTR_EXE" ]; then
    fail "sentinel_plain_binary_writes_no_spool" "plain and instrumented resolve to the SAME binary: $PLAIN_EXE"
  fi
  SP1="$LOGS/spool-plain"; SP2="$LOGS/spool-instr"
  mkdir -p "$SP1" "$SP2"
  (cd "$WS/probe-app" && SENSORIUM_SPOOL="$SP1" SENSORIUM_TIER=call "$PLAIN_EXE" >/dev/null 2>&1)
  (cd "$WS/probe-app" && SENSORIUM_SPOOL="$SP2" SENSORIUM_TIER=call "$INSTR_EXE" >/dev/null 2>&1)
  N1=$(find "$SP1" -type f | wc -l); N2=$(find "$SP2" -type f | wc -l)
  echo "    [sentinel] plain wrote $N1 spool files, instrumented wrote $N2"
  if [ "$N1" -eq 0 ]; then pass "sentinel_plain_binary_writes_no_spool"; else
    fail "sentinel_plain_binary_writes_no_spool" "$N1 files under \$SENSORIUM_SPOOL"; fi
  if [ "$N2" -gt 0 ]; then pass "sentinel_instrumented_binary_writes_a_spool"; else
    fail "sentinel_instrumented_binary_writes_a_spool" "no spool written"; fi
fi

instr_build "$LOGS/instr3.log"
show_counts "instrumented #3 (E8d)" "$LOGS/instr3.log"
if [ -z "$(compiled "$LOGS/instr3.log")" ]; then
  pass "e8d_instrumented_after_plain_compiles_nothing"
else
  fail "e8d_instrumented_after_plain_compiles_nothing" "recompiled: $(compiled "$LOGS/instr3.log")"
fi

# --- E8(b): edit one line; exactly its unit and its dependents rebuild -------
EDIT="$WS/probe-core/src/helper.rs"
cp "$EDIT" "$LOGS/helper.rs.orig"
sed -i 's#^//! A sibling file module.*#//! A sibling file module (edited by mechanics.sh, restored below).#' "$EDIT"
instr_build "$LOGS/instr_touch.log"
show_counts "instrumented after edit (E8b)" "$LOGS/instr_touch.log"
GOT="$(compiled "$LOGS/instr_touch.log")"
cp "$LOGS/helper.rs.orig" "$EDIT"
if [ "$GOT" = "probe-app probe-core " ]; then
  pass "e8b_edited_unit_and_dependents_recompile"
else
  fail "e8b_edited_unit_and_dependents_recompile" "expected 'probe-app probe-core ', got '$GOT'"
fi
instr_build "$LOGS/instr4.log"   # settle after the restore

# --- the non-member must never be wrapped -----------------------------------
MANIFESTS="$TARGET/sensorium/manifests"
EXT_MANIFESTS=$(grep -l '"crate_name":"probe_ext"' "$MANIFESTS"/*.json 2>/dev/null | wc -l)
NAMES=$(python3 -c '
import glob, json, sys
names = sorted({json.load(open(f))["crate_name"] for f in glob.glob(sys.argv[1] + "/*.json")})
print(" ".join(names))
' "$MANIFESTS")
echo "    [manifests] crates wrapped: $NAMES"
if [ "$EXT_MANIFESTS" -eq 0 ] && [ -n "$NAMES" ]; then
  pass "non_member_ext_is_never_wrapped"
else
  fail "non_member_ext_is_never_wrapped" "$EXT_MANIFESTS manifest(s) for probe_ext; wrapped=$NAMES"
fi

FELL=$(grep -l '"fell_back":true' "$MANIFESTS"/*.json 2>/dev/null | wc -l)
if [ "$FELL" -eq 0 ]; then pass "no_unit_fell_back"; else
  fail "no_unit_fell_back" "$FELL unit(s) fell back to the real tree"; fi

# ------------------------------------------------------------------ E7 ------

E7_PLAIN="$(plain_exe e7)"
E7_INSTR="$(instr_exe e7)"
if [ -z "$E7_PLAIN" ] || [ -z "$E7_INSTR" ]; then
  fail "e7_output_identical_plain_vs_off" "no e7 binary (plain='$E7_PLAIN' instr='$E7_INSTR')"
  fail "e7_output_identical_plain_vs_call" "no e7 binary"
  fail "e7_backtrace_locations_identical" "no e7 binary"
else
  run_e7() { # <exe> <outfile> [env...]
    local exe="$1" out="$2"; shift 2
    (cd "$WS/probe-app" && env "$@" "$exe" --test-threads=1 --nocapture) >"$out" 2>&1
  }
  run_e7 "$E7_PLAIN" "$LOGS/e7.plain" SENSORIUM_SPOOL= RUST_BACKTRACE=0
  run_e7 "$E7_INSTR" "$LOGS/e7.off"   SENSORIUM_TIER=off  SENSORIUM_SPOOL="$LOGS/e7spool-off"  RUST_BACKTRACE=0
  run_e7 "$E7_INSTR" "$LOGS/e7.call"  SENSORIUM_TIER=call SENSORIUM_SPOOL="$LOGS/e7spool-call" RUST_BACKTRACE=0
  for arm in off call; do
    D=$(diff <(mask <"$LOGS/e7.plain") <(mask <"$LOGS/e7.$arm"))
    if [ -z "$D" ]; then
      pass "e7_output_identical_plain_vs_$arm"
    else
      fail "e7_output_identical_plain_vs_$arm" "$(echo "$D" | head -6 | tr '\n' ' ')"
    fi
  done
  echo "    [E7] plain output, durations masked:"
  mask <"$LOGS/e7.plain" | sed 's/^/      /'

  run_e7 "$E7_PLAIN" "$LOGS/e7bt.plain" SENSORIUM_SPOOL= RUST_BACKTRACE=1
  run_e7 "$E7_INSTR" "$LOGS/e7bt.off"   SENSORIUM_TIER=off  SENSORIUM_SPOOL="$LOGS/e7spool-bt-off"  RUST_BACKTRACE=1
  run_e7 "$E7_INSTR" "$LOGS/e7bt.call"  SENSORIUM_TIER=call SENSORIUM_SPOOL="$LOGS/e7spool-bt-call" RUST_BACKTRACE=1
  LP=$(locations <"$LOGS/e7bt.plain"); LO=$(locations <"$LOGS/e7bt.off"); LC=$(locations <"$LOGS/e7bt.call")
  echo "    [E7] backtrace locations (plain): $LP"
  if [ "$LP" = "$LO" ] && [ "$LP" = "$LC" ]; then
    pass "e7_backtrace_locations_identical"
  else
    fail "e7_backtrace_locations_identical" "plain='$LP' off='$LO' call='$LC'"
  fi
fi

# --------------------------------------------------- the tree is read-only ---

LOCK_AFTER="$(sha256sum "$WS/Cargo.lock" | awk '{print $1}')"
if [ "$LOCK_BEFORE" = "$LOCK_AFTER" ]; then
  pass "cargo_lock_byte_identical"
else
  fail "cargo_lock_byte_identical" "$LOCK_BEFORE -> $LOCK_AFTER"
fi

TREE_AFTER="$LOGS/tree.after"
{ tree_digest "$WS"; tree_digest "$EXT"; } > "$TREE_AFTER"
if diff -q "$TREE_BEFORE" "$TREE_AFTER" >/dev/null; then
  pass "no_writes_under_the_workspace_outside_target"
else
  fail "no_writes_under_the_workspace_outside_target" "$(diff "$TREE_BEFORE" "$TREE_AFTER" | head -4 | tr '\n' ' ')"
fi

echo "== $FAILS failed =="
[ "$FAILS" -eq 0 ]
