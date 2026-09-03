#!/usr/bin/env bash
# The Rust recorder's mechanics checks, on the probe workspace at
# `rust/probes/`.
#
# Every promise in `rust/HONESTY.md` that a small workspace can falsify in
# seconds is falsified here: E7(a) and E8(a)-(d) as pre-registered in
# `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`, plus
# the runner's witnessed exit (§5), children linked by ppid (§6), the doctest
# route through RUSTDOCFLAGS, `spawn_child` naming (§3), panics and caught
# panics (§1), a thread still blocked at process exit (§4), per-unit mirrors
# (§7) and the two channels a fallback has to appear in (§8). The same
# endpoints run against a real workspace in the acceptance document; this is
# the half that needs no clone and no preflight.
#
# One line per check: `ok: <name>`, `FAIL: <name>: <why>` or
# `skip: <name>: <why>`. Exit non-zero if any check failed. The cargo
# `Compiling`/`Fresh` lines every E8 check counts are PRINTED, not summarised
# away -- a count nobody can see is not evidence.
#
# Environment:
#   SENSORIUM_PROBE_TARGET   where the probe's artifacts go. Set it to a
#                            directory on a DIFFERENT filesystem from the
#                            sources and the run asserts that it is one -- the
#                            configuration the acceptance run uses. Unset, the
#                            probe builds into `rust/probes/ws/target` and that
#                            check is skipped BY NAME.
#   CARGO_TARGET_DIR         where the driver itself is built (the tool
#                            workspace's own target; the probe never uses it).
#   SENSORIUM_MECHANICS_KEEP=1  keep the scratch directory and every log.
#
# No box-specific path appears anywhere in this file or the probe: the second
# disk is an environment variable, not a constant.
#
# Falsification: every check here was made to FAIL once, by breaking exactly
# the mechanism it claims to test, with the breakage and its output recorded in
# the task report. The breakages are deliberately NOT wired into this script
# and there is no sabotage switch in the product: a switch that leaks into a
# real measurement is worse than no switch.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUST="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$RUST/.." && pwd)"
WS="$RUST/probes/ws"
EXT="$RUST/probes/ext"

# shellcheck source=lib/report.sh
. "$HERE/lib/report.sh"
# shellcheck source=lib/cargo.sh
. "$HERE/lib/cargo.sh"
# shellcheck source=lib/trace.sh
. "$HERE/lib/trace.sh"

# What the probe workspace is expected to contain. Pins, not derivations: a
# wrapper that stopped seeing the integration tests would otherwise pass every
# check that counts what it did see.
EXPECTED_TEST_BINARIES=9
WRAPPED_EXPECTED="abort_child app_bin blocked e7 nested_panic probe_app probe_core spawn_bin threads"

TOOL_TARGET="${CARGO_TARGET_DIR:-$RUST/target}"
DRIVER="$TOOL_TARGET/release/cargo-sensorium"
PROBE_TARGET="${SENSORIUM_PROBE_TARGET:-$WS/target}"
mkdir -p "$PROBE_TARGET"
PROBE_TARGET="$(cd "$PROBE_TARGET" && pwd)"
MANIFESTS="$PROBE_TARGET/sensorium/manifests"
MIRROR="$PROBE_TARGET/sensorium/mirror"

# Every trace this run records goes here, never into the box's own store.
SCRATCH_DIR="$(mktemp -d "$PROBE_TARGET/mechanics-XXXXXX")"
LOGS="$SCRATCH_DIR/logs"
mkdir -p "$LOGS"

# E8(b) edits a TRACKED file in the checkout. The restore must survive an
# interrupt, not just the happy path, so the backup is taken and the trap armed
# before anything else runs, and `restore_edit` comes first in every trap:
# cleanup deletes the scratch directory, which is where the backup lives.
EDIT="$WS/probe-core/src/helper.rs"
EDIT_BAK="$SCRATCH_DIR/helper.rs.orig"
cp "$EDIT" "$EDIT_BAK"
restore_edit() { if [ -f "$EDIT_BAK" ]; then cp "$EDIT_BAK" "$EDIT"; fi; return 0; }
cleanup() {
  if [ "${SENSORIUM_MECHANICS_KEEP:-0}" = "1" ]; then
    echo "kept: $SCRATCH_DIR"
    return 0
  fi
  rm -rf "$SCRATCH_DIR"
  return 0
}
trap 'restore_edit; cleanup' EXIT
trap 'restore_edit; cleanup; exit 130' INT
trap 'restore_edit; cleanup; exit 143' TERM

RUN_START="$(now_s)"
echo "== rust recorder mechanics: the probe workspace =="
echo "   probe:   $WS"
echo "   target:  $PROBE_TARGET  ($([ -n "${SENSORIUM_PROBE_TARGET:-}" ] && echo 'SENSORIUM_PROBE_TARGET' || echo 'default <probe>/target'))"
echo "   driver:  $DRIVER"
echo "   scratch: $SCRATCH_DIR"

# ---------------------------------------------------------------- driver ---

section "the driver under test"
T0="$(now_s)"
if ! ( cd "$RUST" && CARGO_TARGET_DIR="$TOOL_TARGET" cargo build --release -p cargo-sensorium ) \
     >"$LOGS/driver-build.log" 2>&1; then
  echo "FAIL: driver_builds: $(tail -3 "$LOGS/driver-build.log" | tr '\n' ' ')"
  exit 1
fi
note "driver: sha256 $(sha256sum "$DRIVER" | cut -c1-16)  built $(date -r "$DRIVER" '+%Y-%m-%d %H:%M:%S')"
elapsed "driver --release build" "$T0"

# ------------------------------------------------------------ the lens ------

section "the lens"
# The acceptance run puts the sources and the target on DIFFERENT filesystems,
# because that is the configuration a user with a small root disk has. When the
# environment asks for it, the run proves it rather than assuming it; when it
# does not, the check says so by name instead of vanishing.
if [ -n "${SENSORIUM_PROBE_TARGET:-}" ]; then
  FS_SRC="$(stat -f -c %i "$WS")"
  FS_TGT="$(stat -f -c %i "$PROBE_TARGET")"
  note "filesystem id: sources=$FS_SRC target=$FS_TGT"
  if [ "$FS_SRC" != "$FS_TGT" ]; then
    pass "probe_sources_and_target_are_on_different_filesystems"
  else
    fail "probe_sources_and_target_are_on_different_filesystems" \
      "SENSORIUM_PROBE_TARGET names a directory on the SAME filesystem as the sources ($FS_SRC)"
  fi
else
  skip "probe_sources_and_target_are_on_different_filesystems" \
    "SENSORIUM_PROBE_TARGET is unset, so the target is <probe>/target and there is only one filesystem to be on"
fi

# --------------------------------------------------------- the snapshot -----

# The manifests and the compiled/Fresh sets have to describe THIS run, so every
# probe source is touched (which recompiles both artifact sets from a known
# state) and stale manifests are removed. The mtime stamp is taken after that,
# so the "nothing was written" sentinel measures the recorder, not this line.
find "$WS" "$EXT" -name target -prune -o -type f -print0 | xargs -0 touch
rm -rf "$MANIFESTS"

STAMP="$SCRATCH_DIR/stamp"
touch "$STAMP"
tree_digest() {
  ( cd "$1" && find . -path ./target -prune -o -type f -print0 | sort -z |
      xargs -0 sha256sum ) 2>/dev/null
}
LOCK_BEFORE="$(sha256sum "$WS/Cargo.lock" | awk '{print $1}')"
{ tree_digest "$WS"; tree_digest "$EXT"; } >"$SCRATCH_DIR/tree.before"

# ------------------------------------------------------------------ E8 ------

section "E8 -- cargo freshness, and a plain build that stays plain"
T0="$(now_s)"

if plain_build "$LOGS/plain1.log"; then
  pass "the_probe_workspace_builds_plain"
else
  fail "the_probe_workspace_builds_plain" "$(tail -3 "$LOGS/plain1.log" | tr '\n' ' ')"
fi
show_counts "plain #1" "$LOGS/plain1.log"

if instr_build "$LOGS/instr1.log"; then
  pass "the_probe_workspace_builds_instrumented"
else
  fail "the_probe_workspace_builds_instrumented" "$(tail -3 "$LOGS/instr1.log" | tr '\n' ' ')"
fi
show_counts "instrumented #1" "$LOGS/instr1.log"

RC=0; instr_build "$LOGS/instr2.log" || RC=$?
show_counts "instrumented #2 (E8a)" "$LOGS/instr2.log"
expect_sets "e8a_a_second_instrumented_build_compiles_nothing" "$LOGS/instr2.log" "$RC" "" "$ALL_PKGS"

RC=0; plain_build "$LOGS/plain2.log" || RC=$?
show_counts "plain #2 (E8c)" "$LOGS/plain2.log"
expect_sets "e8c_a_plain_build_after_an_instrumented_one_compiles_nothing" "$LOGS/plain2.log" "$RC" "" "$ALL_PKGS"

# The sentinel: two artifact sets coexist, and the plain one must STAY plain.
PLAIN_EXE="$(plain_exe probe_app)"
INSTR_EXE="$(instr_exe probe_app)"
if [ -z "$PLAIN_EXE" ] || [ -z "$INSTR_EXE" ] || [ "$PLAIN_EXE" = "$INSTR_EXE" ]; then
  fail "e8c_sentinel_a_plain_binary_writes_no_spool" \
    "could not resolve two distinct probe_app test binaries (plain='$PLAIN_EXE' instrumented='$INSTR_EXE')"
  fail "e8c_sentinel_an_instrumented_binary_writes_a_spool" "no distinct binaries to compare"
else
  mkdir -p "$SCRATCH_DIR/spool-plain" "$SCRATCH_DIR/spool-instr"
  ( cd "$WS/probe-app" && SENSORIUM_SPOOL="$SCRATCH_DIR/spool-plain" SENSORIUM_TIER=call \
      "$PLAIN_EXE" >/dev/null 2>&1 ) || true
  ( cd "$WS/probe-app" && SENSORIUM_SPOOL="$SCRATCH_DIR/spool-instr" SENSORIUM_TIER=call \
      "$INSTR_EXE" >/dev/null 2>&1 ) || true
  N_PLAIN="$(find "$SCRATCH_DIR/spool-plain" -type f | wc -l)"
  N_INSTR="$(find "$SCRATCH_DIR/spool-instr" -type f | wc -l)"
  note "[sentinel] plain wrote $N_PLAIN spool files, instrumented wrote $N_INSTR"
  check "e8c_sentinel_a_plain_binary_writes_no_spool" \
    "$([ "$N_PLAIN" -eq 0 ] && echo 0 || echo 1)" \
    "$N_PLAIN file(s) under \$SENSORIUM_SPOOL: the plain artifact set is contaminated"
  check "e8c_sentinel_an_instrumented_binary_writes_a_spool" \
    "$([ "$N_INSTR" -gt 0 ] && echo 0 || echo 1)" \
    "the instrumented binary wrote nothing, so the sentinel above proves nothing"
fi

RC=0; instr_build "$LOGS/instr3.log" || RC=$?
show_counts "instrumented #3 (E8d)" "$LOGS/instr3.log"
expect_sets "e8d_an_instrumented_build_after_a_plain_one_compiles_nothing" "$LOGS/instr3.log" "$RC" "" "$ALL_PKGS"

# E8(b): edit one line, and exactly its unit and its dependents rebuild.
sed -i 's#^//! A sibling file module.*#//! A sibling file module (edited by mechanics.sh, restored below).#' "$EDIT"
RC=0; instr_build "$LOGS/instr_edit.log" || RC=$?
show_counts "instrumented after an edit (E8b)" "$LOGS/instr_edit.log"
restore_edit
# probe-core holds the edited file and probe-app depends on it; probe-ext
# depends on neither and MUST stay Fresh -- that is the half of (b) that says
# the rebuild was targeted rather than total.
expect_sets "e8b_an_edited_unit_and_its_dependents_recompile" "$LOGS/instr_edit.log" "$RC" \
  "probe-app probe-core " "probe-ext "
instr_build "$LOGS/instr_settle.log" || true   # settle the artifacts after the restore
elapsed "E8" "$T0"

# ------------------------------------------------------------------ E7 ------

section "E7(a) -- line numbers, paths and backtraces"
T0="$(now_s)"
E7_PLAIN="$(plain_exe e7)"
E7_INSTR="$(instr_exe e7)"

# Two per-run values that say nothing about E7 and would swamp it: libtest's
# wall times, and the OS thread id rustc prints in the panic header
# (`thread 'name' (2636689) panicked at ...`). The LOCATION in that same line is
# NOT masked -- it is exactly what E7 measures.
mask() {
  sed -E -e 's/finished in [0-9]+\.[0-9]+s/finished in <masked>/g' \
         -e "s/^(thread '[^']*') \\([0-9]+\\)/\\1 (<tid>)/"
}
# Every `<file>.rs:<line>` (and `:<col>`) the output mentions, in order.
# `|| true`: a run with no location in it at all is a FAILED comparison, not a
# dead script.
locations() { { grep -oE '[A-Za-z0-9_./-]+\.rs:[0-9]+(:[0-9]+)?' || true; } | tr '\n' ' '; }
run_e7() { # <exe> <outfile> <env...>
  local exe="$1" out="$2"; shift 2
  ( cd "$WS/probe-app" && env "$@" "$exe" --test-threads=1 --nocapture ) >"$out" 2>&1 || true
}

if [ -z "$E7_PLAIN" ] || [ -z "$E7_INSTR" ] || [ "$E7_PLAIN" = "$E7_INSTR" ]; then
  for name in e7_output_identical_plain_vs_off e7_output_identical_plain_vs_call \
              e7_backtrace_locations_identical_plain_vs_off \
              e7_backtrace_locations_identical_plain_vs_call \
              e7_binary_is_actually_instrumented; do
    fail "$name" "could not resolve two distinct e7 binaries (plain='$E7_PLAIN' instrumented='$E7_INSTR')"
  done
else
  run_e7 "$E7_PLAIN" "$LOGS/e7.plain" SENSORIUM_SPOOL= RUST_BACKTRACE=0
  run_e7 "$E7_INSTR" "$LOGS/e7.off"  SENSORIUM_TIER=off  SENSORIUM_SPOOL="$SCRATCH_DIR/e7-off"  RUST_BACKTRACE=0
  run_e7 "$E7_INSTR" "$LOGS/e7.call" SENSORIUM_TIER=call SENSORIUM_SPOOL="$SCRATCH_DIR/e7-call" RUST_BACKTRACE=0
  for arm in off call; do
    D="$(diff <(mask <"$LOGS/e7.plain") <(mask <"$LOGS/e7.$arm") || true)"
    check "e7_output_identical_plain_vs_$arm" \
      "$([ -z "$D" ] && echo 0 || echo 1)" "$(echo "$D" | head -6 | tr '\n' ' ')"
  done
  note "[E7] the plain arm's output, durations masked:"
  mask <"$LOGS/e7.plain" | sed 's/^/      /'

  run_e7 "$E7_PLAIN" "$LOGS/e7bt.plain" SENSORIUM_SPOOL= RUST_BACKTRACE=1
  run_e7 "$E7_INSTR" "$LOGS/e7bt.off"  SENSORIUM_TIER=off  SENSORIUM_SPOOL="$SCRATCH_DIR/e7bt-off"  RUST_BACKTRACE=1
  run_e7 "$E7_INSTR" "$LOGS/e7bt.call" SENSORIUM_TIER=call SENSORIUM_SPOOL="$SCRATCH_DIR/e7bt-call" RUST_BACKTRACE=1
  LOC_PLAIN="$(locations <"$LOGS/e7bt.plain")"
  note "[E7] backtrace locations (plain): $LOC_PLAIN"
  for arm in off call; do
    LOC_ARM="$(locations <"$LOGS/e7bt.$arm")"
    check_eq "e7_backtrace_locations_identical_plain_vs_$arm" "$LOC_ARM" "$LOC_PLAIN"
  done

  # E7 compares the OUTPUT of two binaries. If the "instrumented" one carried no
  # guards, every E7 check would pass hardest exactly when the tool did least.
  mkdir -p "$SCRATCH_DIR/e7-witness"
  ( cd "$WS/probe-app" && SENSORIUM_SPOOL="$SCRATCH_DIR/e7-witness" SENSORIUM_TIER=call \
      "$E7_INSTR" --test-threads=1 >/dev/null 2>&1 ) || true
  N_E7="$(find "$SCRATCH_DIR/e7-witness" -type f | wc -l)"
  note "[E7] the e7 binary wrote $N_E7 spool files under tier call"
  check "e7_binary_is_actually_instrumented" \
    "$([ "$N_E7" -gt 0 ] && echo 0 || echo 1)" \
    "the binary E7 diffs wrote no spool, so every E7 comparison above is vacuous"
fi
elapsed "E7" "$T0"

# -------------------------------------------------------- the doctest route --

section "the doctest route"
T0="$(now_s)"
# Cargo routes `rustc` through RUSTC_WORKSPACE_WRAPPER and says nothing about
# `rustdoc`, so a doctest links the INSTRUMENTED rlibs with no `sensorium_rt`
# in sight (findings §5.23). Every build above is `--no-run`, which never
# builds a doctest, so without this arm the RUSTDOCFLAGS route has no coverage
# at all.
DOCLOG="$LOGS/doc-call.log"
DOCRC=0
( cd "$WS" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
    CARGO_TARGET_DIR="$PROBE_TARGET" SENSORIUM_DIR="$SCRATCH_DIR/traces-doc" \
    "$DRIVER" sensorium test --doc ) >"$DOCLOG" 2>&1 || DOCRC=$?
DOCSPOOL="$(spool_of "$DOCLOG")"
grep -E '^ *(Doc-tests|test result|error)' "$DOCLOG" | sed 's/^/    [doctest] /' || true
check "doctests_compile_and_run_under_instrumentation" \
  "$([ "$DOCRC" -eq 0 ] && echo 0 || echo 1)" \
  "rc=$DOCRC: $(grep -m1 -E 'error(\[|:)' "$DOCLOG" | head -c 200)"

DOCCALLS="$(doctest_calls "$DOCSPOOL" "$MANIFESTS")"
note "[doctest] probe_core CALLs from the doctest spool: $DOCCALLS"
check "the_doctest_process_spools_a_probe_core_call" \
  "$([ "${DOCCALLS%% *}" -gt 0 ] 2>/dev/null && echo 0 || echo 1)" \
  "no CALL for a probe_core lib site in $DOCSPOOL"

# Its executable is a `/tmp/rustdoctest*/rust_out` rustdoc deletes immediately
# (findings §5.11), and on cargo 1.96 the runner is handed it anyway (plan
# decision D4) -- so the trace reads a dead exe AND a witnessed exit.
DOCPROCS="$(doctest_processes "$DOCSPOOL")"
note "[doctest] dead-exe processes: $DOCPROCS"
DOC_DEAD="$(echo "$DOCPROCS" | awk '{print $1}')"
DOC_WAITED="$(echo "$DOCPROCS" | awk '{print $2}')"
check "the_doctest_process_records_a_dead_exe" \
  "$([ "$DOC_DEAD" -gt 0 ] && echo 0 || echo 1)" \
  "no process in $DOCSPOOL carries a /tmp/rustdoctest* exe"
check "the_doctest_process_is_runner_waited" \
  "$([ "$DOC_DEAD" -gt 0 ] && [ "$DOC_WAITED" -eq "$DOC_DEAD" ] && echo 0 || echo 1)" \
  "$DOC_WAITED of $DOC_DEAD doctest processes carry a runner record; cargo 1.96 was measured to route every doctest through the runner, so a shortfall is a finding, not a tolerance"

# The control, run every time rather than once: the SAME command with the
# wrapper environment reconstructed by hand but WITHOUT RUSTDOCFLAGS must fail
# E0463. That is what makes the checks above evidence rather than coincidence,
# and it needs no sabotage switch -- the variable is simply not set.
SHIM="$(ls -d "$PROBE_TARGET"/sensorium/shim/*/cargo-sensorium 2>/dev/null | head -1 || true)"
if [ -z "$SHIM" ]; then
  fail "without_rustdocflags_the_doctest_fails_E0463" "could not locate the installed shim under $PROBE_TARGET/sensorium/shim"
else
  TOOLHASH="$(basename "$(dirname "$SHIM")")"
  NORDFRC=0
  ( cd "$WS" && env -u RUSTDOCFLAGS \
      CARGO_TARGET_DIR="$PROBE_TARGET" \
      RUSTC_WORKSPACE_WRAPPER="$SHIM" \
      SENSORIUM_TARGET="$PROBE_TARGET" SENSORIUM_WS="$WS" \
      SENSORIUM_RT_DIR="$PROBE_TARGET/sensorium/rt/$TOOLHASH" \
      SENSORIUM_TOOL_HASH="$TOOLHASH" SENSORIUM_TIER=call \
      SENSORIUM_SPOOL="$SCRATCH_DIR/spool-nordf" \
      cargo test --doc ) >"$LOGS/doc-nordf.log" 2>&1 || NORDFRC=$?
  note "[doctest] without RUSTDOCFLAGS: rc=$NORDFRC  $(grep -m1 -oE 'error\[E[0-9]+\][^\n]*' "$LOGS/doc-nordf.log" | head -c 120 || true)"
  check "without_rustdocflags_the_doctest_fails_E0463" \
    "$([ "$NORDFRC" -ne 0 ] && grep -q 'E0463' "$LOGS/doc-nordf.log" && echo 0 || echo 1)" \
    "rc=$NORDFRC and no E0463: the doctest checks above prove nothing"
fi
elapsed "doctest route" "$T0"

# ------------------------------------------------------------ recording ------

section "one recorded invocation"
T0="$(now_s)"
# `--all-targets` rather than the bare default: doctests have their own arm
# above, with their own three checks, and this run is about the nine test
# binaries and the two children they spawn.
RECLOG="$LOGS/record.log"
TRACES="$SCRATCH_DIR/traces-record/traces"
RECRC=0
( cd "$WS" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
    CARGO_TARGET_DIR="$PROBE_TARGET" SENSORIUM_DIR="$SCRATCH_DIR/traces-record" \
    "$DRIVER" sensorium test --all-targets ) >"$RECLOG" 2>&1 || RECRC=$?
RECSPOOL="$(spool_of "$RECLOG")"
grep -E '^(run:|WARN:)' "$RECLOG" | sed 's/^/    /' || true
check "the_instrumented_suite_passes" "$([ "$RECRC" -eq 0 ] && echo 0 || echo 1)" \
  "rc=$RECRC: $(grep -m1 -E '^(error|test result: FAILED)' "$RECLOG" | head -c 200)"

# The runner's witness (`rust/HONESTY.md` §5). Every process cargo started gets
# a record; every process a TEST started gets none, and reads `unwitnessed`.
RUNNERS="$(runner_report "$RECSPOOL")"
note "[runner] $RUNNERS"
R_RECORDS="$(echo "$RUNNERS" | awk '{print $1}')"
R_BAD="$(echo "$RUNNERS" | awk '{print $2}')"
R_UNWITNESSED_ROOT="$(echo "$RUNNERS" | awk '{print $3}')"
R_CHILD_RECORD="$(echo "$RUNNERS" | awk '{print $4}')"
check "every_test_binary_has_a_runner_record_reading_exit_status_0" \
  "$([ "$R_RECORDS" -eq "$EXPECTED_TEST_BINARIES" ] && [ "$R_BAD" -eq 0 ] && \
     [ "$R_UNWITNESSED_ROOT" -eq 0 ] && echo 0 || echo 1)" \
  "$R_RECORDS runner records (expected $EXPECTED_TEST_BINARIES), $R_BAD not reading exit 0, $R_UNWITNESSED_ROOT cargo-started process(es) without one"
check "no_process_a_test_spawned_carries_a_runner_record" \
  "$([ "$R_CHILD_RECORD" -eq 0 ] && echo 0 || echo 1)" \
  "$R_CHILD_RECORD child process(es) carry a runner record; a status nobody waited for must stay unwitnessed"

# The multi-binary WARN, and its absence when one target is selected.
WARN_N="$(grep -oE '^WARN: this invocation produced [0-9]+ test binaries' "$RECLOG" | awk '{print $5}' || true)"
check_eq "the_multi_binary_warn_names_every_binary" "${WARN_N:-<no WARN line>}" "$EXPECTED_TEST_BINARIES"

LIBLOG="$LOGS/record-lib.log"
LIBRC=0
( cd "$WS" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
    CARGO_TARGET_DIR="$PROBE_TARGET" SENSORIUM_DIR="$SCRATCH_DIR/traces-lib" \
    "$DRIVER" sensorium test -p probe-app --lib ) >"$LIBLOG" 2>&1 || LIBRC=$?
note "[--lib] rc=$LIBRC  $(grep -c '^run: ' "$LIBLOG" || true) trace(s), $(grep -c '^WARN: ' "$LIBLOG" || true) WARN line(s)"
check "the_multi_binary_warn_is_absent_for_a_single_target" \
  "$([ "$LIBRC" -eq 0 ] && ! grep -q '^WARN: this invocation produced' "$LIBLOG" && echo 0 || echo 1)" \
  "rc=$LIBRC and $(grep -c '^WARN: ' "$LIBLOG" || true) WARN line(s) for a one-binary selector"
elapsed "recording" "$T0"

# ------------------------------------------- what the traces have to say -----

section "naming, panics, children and durability"
T0="$(now_s)"

# `spawn_child` naming (§3). The site's LINE is read out of the source, so this
# is a check of the name AND of the line number the transformer baked in.
# The site's LINE, read out of the source. An absent call leaves it empty, and
# the check below then fails naming a task nothing could be called -- which is
# the right answer when the spawn shape the naming rests on has gone.
SPAWN_LINE="$( { grep -n 'thread::spawn(' "$WS/probe-app/tests/threads.rs" || true; } | head -1 | cut -d: -f1)"
WANT_TASK="a_spawned_thread_does_instrumented_work :: spawn@probe-app/tests/threads.rs:$SPAWN_LINE"
if TH_DB="$(trace_for "$TRACES" threads- 2>"$LOGS/trace_for.threads")"; then
  note "[naming] tasks in the threads trace:"
  tasks_of "$TH_DB" | sed 's/^/      /'
  check "the_spawned_thread_is_a_task_named_by_its_site" \
    "$(tasks_of "$TH_DB" | cut -f2 | grep -qxF "$WANT_TASK" && echo 0 || echo 1)" \
    "no task named '$WANT_TASK'"
else
  fail "the_spawned_thread_is_a_task_named_by_its_site" "$(tr '\n' ' ' <"$LOGS/trace_for.threads")"
fi

# Panics (§1): two frames deep, and one caught.
if NP_DB="$(trace_for "$TRACES" nested_panic- 2>"$LOGS/trace_for.nested")"; then
  note "[panic] panic_inner:  $(frames_of "$NP_DB" panic_inner | tr '\n' '|')"
  note "[panic] panic_outer:  $(frames_of "$NP_DB" panic_outer | tr '\n' '|')"
  note "[panic] catch_inner_panic: $(frames_of "$NP_DB" catch_inner_panic | tr '\n' '|')"
  check "the_nested_panicking_frames_close_by_unwind_with_a_panic" \
    "$(frames_of "$NP_DB" panic_inner | grep -q '^unwind panic 2 panic .* probe nested panic: deep$' &&
       frames_of "$NP_DB" panic_outer | grep -q '^unwind panic 1 panic .* probe nested panic: deep$' && echo 0 || echo 1)" \
    "panic_inner='$(frames_of "$NP_DB" panic_inner | tr '\n' '|')' panic_outer='$(frames_of "$NP_DB" panic_outer | tr '\n' '|')'"
  check "the_frame_that_caught_the_panic_closes_by_return_with_an_ok_outcome" \
    "$(frames_of "$NP_DB" catch_inner_panic | grep -q '^return - 1 ok 7 -$' && echo 0 || echo 1)" \
    "catch_inner_panic='$(frames_of "$NP_DB" catch_inner_panic | tr '\n' '|')'"
else
  fail "the_nested_panicking_frames_close_by_unwind_with_a_panic" "$(tr '\n' ' ' <"$LOGS/trace_for.nested")"
  fail "the_frame_that_caught_the_panic_closes_by_return_with_an_ok_outcome" "no nested_panic trace"
fi

# Children (§6) and an unwitnessed exit (§5): the abort child.
if AB_DB="$(trace_for "$TRACES" abort_child- 2>"$LOGS/trace_for.abort")"; then
  AB_CHILDREN="$(meta_of "$AB_DB" child_runs)"
  note "[children] abort_child child_runs: $AB_CHILDREN"
  CHILD_RUN_ID="$(echo "$AB_CHILDREN" | python3 -c 'import json,sys; v=json.load(sys.stdin); print(v[0]["run_id"] if len(v)==1 else "")' 2>/dev/null || true)"
  CHILD_EXE="$(echo "$AB_CHILDREN" | python3 -c 'import json,os,sys; v=json.load(sys.stdin); print(os.path.basename(v[0]["exe"]) if len(v)==1 else "")' 2>/dev/null || true)"
  check_eq "the_parents_child_runs_names_the_aborting_child" "$CHILD_EXE" "app-bin"
  if [ -n "$CHILD_RUN_ID" ] && [ -f "$TRACES/$CHILD_RUN_ID.db" ]; then
    CH_DB="$TRACES/$CHILD_RUN_ID.db"
    CH_BASIS="$(meta_of "$CH_DB" exit_status_basis)"
    CH_STATUS="$(meta_of "$CH_DB" exit_status)"
    CH_OPEN="$(frames_of "$CH_DB" abort_mid_frame)"
    note "[children] the child's trace: basis=$CH_BASIS exit_status=$CH_STATUS abort_mid_frame='$CH_OPEN'"
    check "the_aborted_childs_exit_is_unwitnessed_not_borrowed" \
      "$([ "$CH_BASIS" = '"unwitnessed"' ] && [ "$CH_STATUS" = "null" ] && echo 0 || echo 1)" \
      "basis=$CH_BASIS exit_status=$CH_STATUS; a status nobody waited for must be null"
    check "the_frame_the_child_died_in_is_left_open" \
      "$(echo "$CH_OPEN" | grep -q '^<open> ' && echo 0 || echo 1)" \
      "abort_mid_frame reads '$CH_OPEN'; the open frame IS the record of the death"
  else
    fail "the_aborted_childs_exit_is_unwitnessed_not_borrowed" "no child trace for run id '$CHILD_RUN_ID'"
    fail "the_frame_the_child_died_in_is_left_open" "no child trace for run id '$CHILD_RUN_ID'"
  fi
else
  for name in the_parents_child_runs_names_the_aborting_child \
              the_aborted_childs_exit_is_unwitnessed_not_borrowed \
              the_frame_the_child_died_in_is_left_open; do
    fail "$name" "$(tr '\n' ' ' <"$LOGS/trace_for.abort")"
  done
fi

# Durability (§4): a thread still blocked when the process exited.
BLOCK_LINE="$( { grep -n 'thread::spawn(' "$WS/probe-app/tests/blocked.rs" || true; } | head -1 | cut -d: -f1)"
WANT_LIVE="a_worker_blocks_past_the_end_of_the_test :: spawn@probe-app/tests/blocked.rs:$BLOCK_LINE"
if BL_DB="$(trace_for "$TRACES" blocked- 2>"$LOGS/trace_for.blocked")"; then
  BL_LIVE="$(meta_of "$BL_DB" live_threads)"
  BL_GAPS="$(meta_of "$BL_DB" seq_gaps)"
  BL_DROPPED="$(meta_of "$BL_DB" records_dropped)"
  BL_TID="$(tasks_of "$BL_DB" | grep -F "$WANT_LIVE" | cut -f1 || true)"
  BL_EVENTS=0
  if [ -n "$BL_TID" ]; then BL_EVENTS="$(events_on_thread "$BL_DB" "$BL_TID")"; fi
  note "[durability] live_threads=$BL_LIVE seq_gaps=$BL_GAPS records_dropped=$BL_DROPPED events_on_the_blocked_thread=$BL_EVENTS"
  check "the_blocked_thread_is_live_at_exit_with_its_records_on_disk" \
    "$(echo "$BL_LIVE" | grep -qF "$WANT_LIVE" && [ "$BL_EVENTS" -gt 0 ] && echo 0 || echo 1)" \
    "live_threads=$BL_LIVE, events on the blocked thread=$BL_EVENTS (wanted '$WANT_LIVE' with events)"
  check "the_blocked_threads_trace_has_no_holes" \
    "$([ "$BL_GAPS" = "0" ] && [ "$BL_DROPPED" = "{}" ] && echo 0 || echo 1)" \
    "seq_gaps=$BL_GAPS records_dropped=$BL_DROPPED; a hole makes every count in this trace a lower bound"
else
  fail "the_blocked_thread_is_live_at_exit_with_its_records_on_disk" "$(tr '\n' ' ' <"$LOGS/trace_for.blocked")"
  fail "the_blocked_threads_trace_has_no_holes" "no blocked trace"
fi
elapsed "trace checks" "$T0"

# --------------------------------------------- what actually got wrapped -----

section "what got wrapped, and what fell back"
T0="$(now_s)"
EXT_MANIFESTS="$(grep -l '"crate_name":"probe_ext"' "$MANIFESTS"/*.json 2>/dev/null | wc -l || true)"
NAMES="$(wrapped_crates "$MANIFESTS")"
note "[manifests] crates wrapped: $NAMES"
check "the_non_member_ext_crate_is_never_wrapped" \
  "$([ "$EXT_MANIFESTS" -eq 0 ] && [ -n "$NAMES" ] && echo 0 || echo 1)" \
  "$EXT_MANIFESTS manifest(s) for probe_ext; wrapped='$NAMES'"
check_eq "exactly_the_expected_units_are_wrapped" "$NAMES" "$WRAPPED_EXPECTED"

# Two ways a unit can end up uninstrumented, and BOTH have to be looked for.
# The manifest flag catches a unit rustc rejected; it does NOT catch a unit the
# WRAPPER failed on before it could write or patch a manifest, so the build logs
# are read for the one line the wrapper prints (`rust/HONESTY.md` §8).
FELL_MANIFESTS="$(grep -l '"fell_back":true' "$MANIFESTS"/*.json 2>/dev/null | wc -l || true)"
FELL_LOG="$(cat "$LOGS"/plain*.log "$LOGS"/instr*.log "$LOGS/doc-call.log" "$LOGS/record.log" "$LOGS/record-lib.log" 2>/dev/null |
  grep -c 'fell back to the real tree' || true)"
note "[fallbacks] manifests flagged: $FELL_MANIFESTS   build-log lines: $FELL_LOG"
check "no_unit_of_the_probe_fell_back_in_either_channel" \
  "$([ "$FELL_MANIFESTS" -eq 0 ] && [ "$FELL_LOG" -eq 0 ] && echo 0 || echo 1)" \
  "$FELL_MANIFESTS manifest(s) flagged, $FELL_LOG log line(s): $(cat "$LOGS"/*.log 2>/dev/null | grep -m1 'fell back to the real tree' || true)"

IDENTITY="$(unit_identity "$MANIFESTS" "$MIRROR")"
ID_BAD="$(echo "$IDENTITY" | awk '{print $1}')"
ID_CHECKED="$(echo "$IDENTITY" | awk '{print $2}')"
note "[identity] crate roots checked: $ID_CHECKED  bad: $ID_BAD  $(echo "$IDENTITY" | cut -d' ' -f3-)"
check "every_units_mirror_carries_its_own_metadata" \
  "$([ "$ID_BAD" -eq 0 ] && [ "$ID_CHECKED" -gt 0 ] && echo 0 || echo 1)" \
  "$ID_BAD wrong of $ID_CHECKED checked: $(echo "$IDENTITY" | cut -d' ' -f3-)"
elapsed "manifests" "$T0"

# --------------------------------------------------- the tree is read-only ---

section "the probe tree is read-only"
LOCK_AFTER="$(sha256sum "$WS/Cargo.lock" | awk '{print $1}')"
check_eq "the_probes_cargo_lock_is_byte_identical" "$LOCK_AFTER" "$LOCK_BEFORE"

{ tree_digest "$WS"; tree_digest "$EXT"; } >"$SCRATCH_DIR/tree.after"
check "the_probe_tree_is_byte_identical" \
  "$(diff -q "$SCRATCH_DIR/tree.before" "$SCRATCH_DIR/tree.after" >/dev/null && echo 0 || echo 1)" \
  "$(diff "$SCRATCH_DIR/tree.before" "$SCRATCH_DIR/tree.after" | head -4 | tr '\n' ' ')"

# The mtime sentinel, beside the content one: a write that put the same bytes
# back is still a write. `helper.rs` is excluded BY NAME because this script
# edits and restores it for E8(b); its content is covered by the digest above.
NEWER="$(find "$WS" "$EXT" -name target -prune -o -type f -newer "$STAMP" \
           ! -path "$EDIT" -print | head -5)"
note "[read-only] excluded from the mtime sentinel: ${EDIT#"$REPO/"} (E8(b) edits and restores it)"
check "nothing_under_the_probe_tree_was_written" \
  "$([ -z "$NEWER" ] && echo 0 || echo 1)" \
  "written during the run: $(echo "$NEWER" | tr '\n' ' ')"

GITSTATUS="$(git -C "$REPO" status --porcelain -- "$RUST/probes" || true)"
check "the_probe_tree_has_no_git_changes" \
  "$([ -z "$GITSTATUS" ] && echo 0 || echo 1)" \
  "$(echo "$GITSTATUS" | tr '\n' ' ')"

# ------------------------------------------------------------- the verdict ---

echo
elapsed "TOTAL" "$RUN_START"
echo "== $CHECKS_PASSED passed, $CHECKS_FAILED failed, $CHECKS_SKIPPED skipped =="
[ "$CHECKS_FAILED" -eq 0 ]
