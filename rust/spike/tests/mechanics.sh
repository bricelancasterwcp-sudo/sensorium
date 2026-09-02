#!/usr/bin/env bash
# THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike): E7 and E8 on the PROBE
# workspace. Task 5 runs the same checks against bloomery under its own
# preflight; nothing here touches bloomery.
#
# 21 checks. One line per check: `ok: <name>` or `FAIL: <name>: <why>`. Exit non-zero if
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
# E8(b) edits a TRACKED file in the checkout. The restore must survive an
# interrupt, not just the happy path, so the backup is taken and the trap armed
# before anything else runs. restore_edit comes first in every trap: cleanup
# deletes $LOGS, which is where the backup lives.
EDIT="$WS/probe-core/src/helper.rs"
EDIT_BAK="$LOGS/helper.rs.orig"
cp "$EDIT" "$EDIT_BAK"
restore_edit() { if [ -f "$EDIT_BAK" ]; then cp "$EDIT_BAK" "$EDIT"; fi; return 0; }
trap 'restore_edit; cleanup' EXIT
trap 'restore_edit; cleanup; exit 130' INT
trap 'restore_edit; cleanup; exit 143' TERM

MANIFESTS="$TARGET/sensorium/manifests"

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

# Every workspace package, as the Fresh set must read when nothing recompiles.
# Asserting only "compiled nothing" is vacuous: a build that dies before cargo
# prints its first `Compiling` line also compiled nothing.
ALL_PKGS="probe-app probe-core probe-ext "

# <check> <log> <build rc> <expected compiled> <expected fresh>
expect_sets() {
  local name="$1" log="$2" rc="$3" want_c="$4" want_f="$5"
  local got_c got_f
  got_c="$(compiled "$log")"; got_f="$(freshset "$log")"
  if [ "$rc" -ne 0 ]; then
    fail "$name" "the build FAILED (rc=$rc), so an empty compiled set proves nothing: $(tail -3 "$log" | tr '\n' ' ')"
  elif [ "$got_c" != "$want_c" ]; then
    fail "$name" "compiled '$got_c', expected '$want_c'"
  elif [ "$got_f" != "$want_f" ]; then
    fail "$name" "Fresh set was '$got_f', expected '$want_f'"
  else
    pass "$name"
  fi
}

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

instr_build "$LOGS/instr2.log"; RC=$?
show_counts "instrumented #2 (E8a)" "$LOGS/instr2.log"
expect_sets "e8a_second_instrumented_build_compiles_nothing" "$LOGS/instr2.log" "$RC" "" "$ALL_PKGS"

plain_build "$LOGS/plain2.log"; RC=$?
show_counts "plain #2 (E8c)" "$LOGS/plain2.log"
expect_sets "e8c_plain_build_after_instrumented_compiles_nothing" "$LOGS/plain2.log" "$RC" "" "$ALL_PKGS"

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

instr_build "$LOGS/instr3.log"; RC=$?
show_counts "instrumented #3 (E8d)" "$LOGS/instr3.log"
expect_sets "e8d_instrumented_after_plain_compiles_nothing" "$LOGS/instr3.log" "$RC" "" "$ALL_PKGS"

# --- E8(b): edit one line; exactly its unit and its dependents rebuild -------
sed -i 's#^//! A sibling file module.*#//! A sibling file module (edited by mechanics.sh, restored below).#' "$EDIT"
instr_build "$LOGS/instr_touch.log"; RC=$?
show_counts "instrumented after edit (E8b)" "$LOGS/instr_touch.log"
restore_edit
# probe-core holds the edited file; probe-app depends on it. probe-ext depends
# on neither and MUST stay Fresh -- that is the half of (b) that says the
# rebuild was targeted rather than total.
expect_sets "e8b_edited_unit_and_dependents_recompile" "$LOGS/instr_touch.log" "$RC" \
  "probe-app probe-core " "probe-ext "
instr_build "$LOGS/instr4.log"   # settle after the restore

# --- the non-member must never be wrapped: checked at the end, see below -----
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

  # E7 compares the OUTPUT of two binaries. If the "instrumented" one carried
  # no guards, every E7 check would pass hardest exactly when the tool did
  # least (falsification 4 showed this). The sentinel above covers the
  # probe_app lib-test binary; this covers the binary E7 actually reads.
  SPE7="$LOGS/spool-e7"; mkdir -p "$SPE7"
  (cd "$WS/probe-app" && SENSORIUM_SPOOL="$SPE7" SENSORIUM_TIER=call "$E7_INSTR" --test-threads=1 >/dev/null 2>&1)
  NE7=$(find "$SPE7" -type f | wc -l)
  echo "    [E7] the e7 binary wrote $NE7 spool files under call"
  if [ "$NE7" -gt 0 ]; then
    pass "e7_binary_is_actually_instrumented"
  else
    fail "e7_binary_is_actually_instrumented" "the e7 binary E7 diffs wrote no spool: E7 would be vacuous"
  fi

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

# ------------------------------------------------------- the doctest route ---
# Cargo does NOT route rustdoc through RUSTC_WORKSPACE_WRAPPER, so a doctest
# links the INSTRUMENTED rlib with no sensorium_rt in sight. Everything above
# runs `--no-run`, which never builds a doctest, so without this arm the
# RUSTDOCFLAGS fix has zero coverage -- and bloomery's `cargo test -p
# bloomery-daemon` runs doctests.
DOCLOG="$LOGS/doc-call.log"
(cd "$WS" && "$DRIVER" sensorium test --doc) >"$DOCLOG" 2>&1; DOCRC=$?
DOCSPOOL=$(grep '^spool: ' "$DOCLOG" | tail -1 | sed 's/^spool: //')
grep -E '^ *(Doc-tests|test result)' "$DOCLOG" | sed 's/^/    [doctest] /'
if [ "$DOCRC" -eq 0 ] && grep -q 'Doc-tests probe_core' "$DOCLOG"; then
  pass "doctests_compile_and_run_under_instrumentation"
else
  fail "doctests_compile_and_run_under_instrumentation" "rc=$DOCRC: $(grep -m1 -E 'error(\[|:)' "$DOCLOG" | head -c 200)"
fi

# The doctest process is a WITNESS, not just a compile check: it links the
# instrumented rlibs, so it spools real CALLs. (The report's earlier claim that
# doctest processes produce spools with no sites was wrong; this is the check
# that would have caught it.) Its exe is a /tmp/rustdoctest*/rust_out that is
# deleted before any converter runs -- Task 4 needs to expect that.
DOCCALLS=$(python3 - "$DOCSPOOL" "$MANIFESTS" <<'PY'
import glob, json, os, struct, sys
spool, mdir = sys.argv[1], sys.argv[2]
want = set()
for f in glob.glob(mdir + "/*.json"):
    m = json.load(open(f))
    if m["crate_name"] == "probe_core" and m["crate_type"] == "lib":
        want.add(m["unit"])
total, who = 0, []
for ph in sorted(glob.glob(spool + "/*.proc.json")):
    h = json.load(open(ph))
    ids = {int(k) for k, v in h.get("units", {}).items() if v in want}
    if not ids:
        continue
    calls = 0
    for sp in glob.glob("%s/%s.*.spool" % (spool, h["pid"])):
        b = open(sp, "rb").read()
        if b[:4] != b"SNSR":
            continue
        off = 11 + struct.unpack_from("<H", b, 9)[0]
        while off + 24 <= len(b):
            _seq, _ts, site, kind, _o, _r = struct.unpack_from("<QQIBBH", b, off)
            off += 24
            if kind == 1 and (site >> 24) in ids:
                calls += 1
    if calls:
        who.append("%s(%d)" % (os.path.basename(h["exe"]), calls))
        total += calls
if total == 0:
    # A check that fails must say what it saw, or the next person re-runs it
    # blind. Dump every process in the spool and its unit map.
    seen = []
    for ph in sorted(glob.glob(spool + "/*.proc.json")):
        h = json.load(open(ph))
        seen.append("%s:%s:units=%s:spools=%d" % (
            h["pid"], os.path.basename(h["exe"]), h.get("units"),
            len(glob.glob("%s/%s.*.spool" % (spool, h["pid"])))))
    allm = sorted((json.load(open(f))["crate_name"], json.load(open(f))["crate_type"],
                   json.load(open(f))["unit"]) for f in glob.glob(mdir + "/*.json"))
    who.append("want=%s seen=[%s] manifests=%s" % (
        sorted(want), "; ".join(seen) or "nothing", allm))
print("%d %s" % (total, ",".join(who) or "-"))
PY
)
echo "    [doctest] probe_core CALLs from the doctest spool: $DOCCALLS"
if [ "${DOCCALLS%% *}" -gt 0 ] 2>/dev/null; then
  pass "the_doctest_process_spools_a_probe_core_call"
else
  fail "the_doctest_process_spools_a_probe_core_call" "no CALL for a probe_core lib site in $DOCSPOOL"
fi

# The falsification, run deliberately and every time: the SAME command with the
# wrapper env but WITHOUT RUSTDOCFLAGS must fail E0463. This is what makes the
# check above evidence rather than a coincidence -- and it needs no sabotage
# switch in the binary, because RUSTDOCFLAGS is simply not set.
SHIM=$(ls -d "$TARGET"/sensorium/shim/*/cargo-sensorium 2>/dev/null | head -1)
RTRLIB=$(ls "$SPIKE"/target/release/deps/libsensorium_rt-*.rlib 2>/dev/null | head -1)
if [ -z "$SHIM" ] || [ -z "$RTRLIB" ]; then
  fail "without_rustdocflags_the_doctest_fails_E0463" "could not locate shim='$SHIM' rlib='$RTRLIB'"
else
  TOOLHASH=$(basename "$(dirname "$SHIM")")
  (cd "$WS" && env RUSTC_WORKSPACE_WRAPPER="$SHIM" SENSORIUM_TARGET="$TARGET" SENSORIUM_WS="$WS" \
      SENSORIUM_RT_RLIB="$RTRLIB" SENSORIUM_RT_DEPS="$(dirname "$RTRLIB")" \
      SENSORIUM_TOOL_HASH="$TOOLHASH" SENSORIUM_TIER=call \
      SENSORIUM_SPOOL="$LOGS/spool-nordf" \
      cargo test --doc) >"$LOGS/doc-nordf.log" 2>&1; NORDFRC=$?
  echo "    [doctest] without RUSTDOCFLAGS: rc=$NORDFRC  $(grep -m1 -oE 'error\[E[0-9]+\][^\n]*' "$LOGS/doc-nordf.log" | head -c 120)"
  if [ "$NORDFRC" -ne 0 ] && grep -q 'E0463' "$LOGS/doc-nordf.log"; then
    pass "without_rustdocflags_the_doctest_fails_E0463"
  else
    fail "without_rustdocflags_the_doctest_fails_E0463" "rc=$NORDFRC and no E0463: the doctest check above proves nothing"
  fi
fi

# ------------------------------------------------- what actually got wrapped ---
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

# The exact set, not just "probe_ext is absent". A wrapper that stopped seeing
# the integration tests, or started seeing something new, would otherwise pass
# every check above. rustdoc is NOT wrapped, so the doctest arm below adds
# nothing here: these six are lib/bin/test units only.
WRAPPED_EXPECTED="app_bin e7 probe_app probe_core spawn_bin threads"
if [ "$NAMES" = "$WRAPPED_EXPECTED" ]; then
  pass "exactly_the_expected_units_are_wrapped"
else
  fail "exactly_the_expected_units_are_wrapped" "wrapped '$NAMES', expected '$WRAPPED_EXPECTED'"
fi

# Two ways a unit can end up uninstrumented, and BOTH have to be looked for.
# The manifest flag catches a unit rustc rejected. It does NOT catch a unit the
# WRAPPER failed on before it could write or patch a manifest -- so the build
# logs are read for the one line ruling 6 requires the wrapper to print.
FELL=$(grep -l '"fell_back":true' "$MANIFESTS"/*.json 2>/dev/null | wc -l)
BUILD_LOGS=$(ls "$LOGS"/plain*.log "$LOGS"/instr*.log "$LOGS"/doc-call.log 2>/dev/null)
FELL_LOG=$(grep -hc 'fell back to the real tree' $BUILD_LOGS 2>/dev/null | paste -sd+ | bc)
FELL_LOG=${FELL_LOG:-0}
if [ "$FELL" -eq 0 ] && [ "$FELL_LOG" -eq 0 ]; then
  pass "no_unit_fell_back"
else
  fail "no_unit_fell_back" "$FELL manifest(s) flagged, $FELL_LOG stderr line(s): $(grep -h 'fell back to the real tree' $BUILD_LOGS 2>/dev/null | head -1)"
fi

# The invariant behind unit identity (spec 2.4), asserted directly and
# deterministically rather than left to the doctest arm's coin flip: the crate
# root in each unit's mirror must name THAT unit. One shared mirror cannot hold
# two units of the same crate root, and the loser reads as a healthy build.
BADID=$(python3 - "$MANIFESTS" "$TARGET/sensorium/mirror" <<'PY'
import glob, json, os, sys
mdir, mirror = sys.argv[1], sys.argv[2]
bad, checked = [], 0
for f in sorted(glob.glob(mdir + "/*.json")):
    m = json.load(open(f))
    roots = [p for p in m["files"] if p.endswith(("lib.rs", "main.rs")) or "/tests/" in p]
    for rel in sorted(m["files"]):
        path = os.path.join(mirror, m["unit"], rel)
        if not os.path.exists(path):
            bad.append("%s %s: no mirror file" % (m["crate_name"], rel))
            continue
        text = open(path).read()
        if 'Unit::new("' in text:
            checked += 1
            if 'Unit::new("%s")' % m["unit"] not in text:
                got = text.split('Unit::new("')[1].split('"')[0]
                bad.append("%s/%s %s carries %s" % (m["crate_name"], m["crate_type"], rel, got))
    del roots
print("%d %d %s" % (len(bad), checked, "; ".join(bad[:3])))
PY
)
echo "    [identity] crate roots checked: ${BADID#* }"
if [ "${BADID%% *}" = "0" ]; then
  pass "every_units_mirror_carries_its_own_metadata"
else
  fail "every_units_mirror_carries_its_own_metadata" "$BADID"
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
