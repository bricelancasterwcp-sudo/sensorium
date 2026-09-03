# Reporting and timing for `rust/tests/mechanics.sh`.
#
# One line per check, and only one shape of line: `ok: <name>`,
# `FAIL: <name>: <why>` or `skip: <name>: <why>`. A check that cannot say which
# of the three it is has not run, so `note` exists for everything else and is
# never mistaken for a verdict.

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_SKIPPED=0

pass() {
  CHECKS_PASSED=$((CHECKS_PASSED + 1))
  echo "ok: $1"
}

fail() {
  CHECKS_FAILED=$((CHECKS_FAILED + 1))
  echo "FAIL: $1: $2"
}

# A check that did not run, named so its absence is visible rather than
# inferred from a shorter list.
skip() {
  CHECKS_SKIPPED=$((CHECKS_SKIPPED + 1))
  echo "skip: $1: $2"
}

# Evidence, not a verdict.
note() { echo "    $*"; }

section() {
  echo
  echo "-- $* --"
}

# <name> <condition-rc> <why-on-failure>
check() {
  if [ "$2" -eq 0 ]; then pass "$1"; else fail "$1" "$3"; fi
}

# <name> <got> <want>
check_eq() {
  if [ "$2" = "$3" ]; then pass "$1"; else fail "$1" "got '$2', expected '$3'"; fi
}

# Seconds since the epoch with milliseconds, for the phase timings the run
# prints. `date` rather than `SECONDS`, because a whole-second resolution
# cannot tell a 0.4 s phase from a 1.4 s one.
now_s() { date +%s.%N; }

# <label> <start> — elapsed since <start>, to milliseconds. awk, never bc: bc
# is not installed everywhere this has to run.
elapsed() {
  awk -v s="$2" -v e="$(now_s)" -v l="$1" 'BEGIN { printf "    [time] %-34s %7.2fs\n", l, e - s }'
}
