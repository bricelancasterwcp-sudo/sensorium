# Building the probe workspace, plain and instrumented, and reading what cargo
# says it did.
#
# Every E8 check counts cargo's own `Compiling` and `Fresh` lines from a `-v`
# build and asserts BOTH sets. Asserting only "compiled nothing" is vacuous: a
# build that dies before cargo prints its first `Compiling` line also compiled
# nothing, which is why `expect_sets` refuses a non-zero build first.

# Every workspace package cargo builds for the probe, as the Fresh set reads
# when nothing recompiles. Trailing space: the sets are built by `tr '\n' ' '`.
ALL_PKGS="probe-app probe-core probe-ext "

# Workspace packages cargo said it COMPILED, as a sorted space-separated set.
# `|| true` on the pipeline, not on the grep: an empty set is the expected
# answer for a build that recompiled nothing, and `pipefail` would otherwise
# make "nothing matched" an error.
compiled() {
  { grep -hE '^ *Compiling (probe-core|probe-app|probe-ext) ' "$1" 2>/dev/null || true; } |
    awk '{print $2}' | sort -u | tr '\n' ' '
}

# ...and the ones it found Fresh.
freshset() {
  { grep -hE '^ *Fresh (probe-core|probe-app|probe-ext) ' "$1" 2>/dev/null || true; } |
    awk '{print $2}' | sort -u | tr '\n' ' '
}

show_counts() {
  note "[$1] Compiling: $(compiled "$2")| Fresh: $(freshset "$2")"
}

# <ws> <target> <log> [extra cargo args…] — a plain `cargo test --no-run` of
# any workspace, with no recorder anywhere near it.
plain_build_at() {
  local ws="$1" target="$2" log="$3"
  shift 3
  ( cd "$ws" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
      CARGO_TARGET_DIR="$target" cargo test --no-run "$@" ) >"$log" 2>&1
}

# <ws> <target> <traces dir> <log> [extra cargo args…] — the same, through the
# driver. The traces directory is an argument because every recording this
# script makes goes somewhere fresh, never into the box's own trace store.
instr_build_at() {
  local ws="$1" target="$2" traces="$3" log="$4"
  shift 4
  ( cd "$ws" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
      CARGO_TARGET_DIR="$target" SENSORIUM_DIR="$traces" \
      "$DRIVER" sensorium test --no-run "$@" ) >"$log" 2>&1
}

# <log> — the probe workspace, plain, `-v` so E8 can count what cargo did.
plain_build() { plain_build_at "$WS" "$PROBE_TARGET" "$1" -v; }

# <log> — the probe workspace, instrumented.
instr_build() {
  instr_build_at "$WS" "$PROBE_TARGET" "$SCRATCH_DIR/traces-norun" "$1" -v
}

# <check> <log> <build rc> <expected compiled> <expected fresh>
expect_sets() {
  local name="$1" log="$2" rc="$3" want_c="$4" want_f="$5" got_c got_f
  got_c="$(compiled "$log")"
  got_f="$(freshset "$log")"
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

# The path of one test executable, by target name, out of cargo's JSON stream.
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

# `|| true` around the build: a build that fails names no executable, and the
# check that reads this must say so rather than take the shell down with it.
plain_exe() {
  { ( cd "$WS" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
        CARGO_TARGET_DIR="$PROBE_TARGET" cargo test --no-run --message-format=json 2>/dev/null ) || true; } |
    exe_of "$1"
}

instr_exe() {
  { ( cd "$WS" && env -u RUSTC_WORKSPACE_WRAPPER -u RUSTDOCFLAGS \
        CARGO_TARGET_DIR="$PROBE_TARGET" SENSORIUM_DIR="$SCRATCH_DIR/traces-norun" \
        "$DRIVER" sensorium test --no-run --message-format=json 2>/dev/null ) || true; } |
    exe_of "$1"
}

# The `spool: <path>` line the driver prints on stderr, from a captured log.
spool_of() { grep '^spool: ' "$1" | tail -1 | sed 's/^spool: //'; }
