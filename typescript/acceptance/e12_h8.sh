#!/usr/bin/env bash
# H8: did nothing else move?
#
#   e12_h8.sh <out dir>
#
# §1's H8, clause by clause, each run once and each exit status carried into
# the cell:
#
#   * `corpus/run_corpus.py --require-driver` -- every case of all three
#     directories (Python, Rust, TypeScript, the ten new focus cases
#     included). `--require-driver` is what turns "could not run" into a
#     failure instead of a silence;
#   * `.venv/bin/python -m pytest -q` -- the Python suite;
#   * `cargo test --workspace`;
#   * `npm --prefix typescript test`;
#   * `npm --prefix typescript/probes run probe` -- the probe project wires
#     the recorder itself and REQUIRES `SENSORIUM_SPOOL` and
#     `SENSORIUM_MANIFEST_DIR`, so this script gives it two fresh directories
#     under <out> rather than inheriting a caller's;
#   * `e7_report.py` with `E7_NEEDLES=rung2` over EVERY transcript of §1.5's
#     reads, at 0 occurrences.
#
# THE TRANSCRIPTS ARE COPIED BEFORE THEY ARE READ. `e7_report.py` writes a
# `<transcript>.rules` sibling naming how each needle is matched, and the
# transcripts this rung commits are the redacted ones -- so the grep runs over
# a COPY under <out>/h8/transcripts and the committed set gains no sibling it
# did not ask for. Each copy's sha256 is carried in the cell, so "the same
# transcript" is a hash and not a claim.
#
# `CARGO_TARGET_DIR` is inherited, never set here: this box keeps its target
# directory off the root disk and a committed instrument carries no box path.
# The cell records only WHETHER one was set.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/lens.sh"

OUT="${1-}"
[ -n "$OUT" ] || refuse "usage: e12_h8.sh <out dir>"
[ -d "$OUT" ] || refuse "no such out directory: $OUT"
READS="$OUT/reads-redacted"
[ -d "$READS" ] || refuse "no transcripts at $READS: H8's needle grep is over the reads, and the reads come first"

REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
H8="$OUT/h8"
mkdir -p "$H8/logs" "$H8/transcripts" "$H8/e7" || refuse "cannot write under $H8"

#: The store, the focus and the spool belong to whoever set them; none of the
#: suites below reads this rung's store, and an inherited one would point a
#: corpus case or a probe at traces it never wrote.
unset SENSORIUM_DIR SENSORIUM_FOCUS SENSORIUM_SPOOL SENSORIUM_MANIFEST_DIR
export PYTHONDONTWRITEBYTECODE=1

STATUSES="$H8/statuses.txt"
: >"$STATUSES"

# suite_in <dir> <label> <command...> -- run one clause from <dir>, log it,
# record its exit. The directory is a parameter because the cargo workspace's
# manifest is `rust/Cargo.toml`: run from the repository root, `cargo test
# --workspace` exits 101 with "could not find `Cargo.toml`", which a dry run
# on the probe project caught before any number of H8 was read.
suite_in() {
  local dir="$1" label="$2"; shift 2
  local log="$H8/logs/$label.log"
  ( cd "$dir" && "$@" ) >"$log" 2>&1
  local status=$?
  printf '%s\t%s\n' "$label" "$status" >>"$STATUSES"
  return 0
}

# suite <label> <command...> -- the same, from the repository root.
suite() { local label="$1"; shift; suite_in "$REPO_ROOT" "$label" "$@"; }

suite corpus .venv/bin/python corpus/run_corpus.py --require-driver
suite pytest .venv/bin/python -m pytest -q -p no:cacheprovider
suite_in "$REPO_ROOT/rust" cargo cargo test --workspace
suite npm-typescript npm --prefix typescript test
(
  export SENSORIUM_SPOOL="$H8/probe-spool" SENSORIUM_MANIFEST_DIR="$H8/probe-manifests"
  export SENSORIUM_TIER=call
  mkdir -p "$SENSORIUM_SPOOL" "$SENSORIUM_MANIFEST_DIR"
  suite npm-probes npm --prefix typescript/probes run probe
)

# The vectors, for the E7 cell's second half: every one of them, run once.
VECTORS="$H8/vectors.txt"
( cd "$REPO_ROOT" && .venv/bin/python -m pytest -q -p no:cacheprovider \
    tests/test_vectors.py ) >"$VECTORS" 2>&1
vectors_status=$?
printf '%s\t%s\n' vectors "$vectors_status" >>"$STATUSES"

# The needle grep, one E7 cell per transcript, over copies.
for src in "$READS"/*.txt; do
  [ -e "$src" ] || continue
  name="$(basename "$src" .txt)"
  cp "$src" "$H8/transcripts/$name.txt"
  E7_TRANSCRIPT="$H8/transcripts/$name.txt" E7_STATUSES="$STATUSES" \
  E7_VECTORS="$VECTORS" E7_VECTORS_STATUS="$vectors_status" \
  E7_VECTORS_K="(none: every vector)" E7_NEEDLES=rung2 \
  E7_RECORDER="${E12_RECORDER:-}" E7_REV="${E12_REV:-}" \
    python3 "$HERE/e7_report.py" >"$H8/e7/$name.json"
done

E12_H8="$H8" E12_OUT="$OUT" E12_STATUSES="$STATUSES" E12_HERE="$HERE" \
E12_CARGO_TARGET_SET="$([ -n "${CARGO_TARGET_DIR:-}" ] && echo yes || echo no)" \
  python3 - <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["E12_HERE"])
from lens import cell, emit                                    # noqa: E402

env = os.environ
h8 = Path(env["E12_H8"])
status = {}
for line in Path(env["E12_STATUSES"]).read_text(encoding="utf-8").splitlines():
    label, _, code = line.partition("\t")
    if label:
        status[label] = int(code)


def tail(name: str, n: int = 3) -> list[str]:
    path = h8 / "logs" / f"{name}.log"
    if not path.is_file():
        return []
    rows = [ln for ln in path.read_text(encoding="utf-8",
                                        errors="replace").splitlines()
            if ln.strip()]
    return rows[-n:]


needles = {}
total = 0
for path in sorted((h8 / "e7").glob("*.json")):
    body = json.loads(path.read_text(encoding="utf-8"))
    src = h8 / "transcripts" / f"{path.stem}.txt"
    needles[path.stem] = {
        "occurrences": body["value"], "needles": body["n"],
        "list": body.get("needle_list"),
        "per_needle": {k: v for k, v in (body.get("occurrences") or {}).items()
                       if v},
        "lines": body.get("transcript_lines"),
        "sha256": hashlib.sha256(src.read_bytes()).hexdigest()
        if src.is_file() else None,
    }
    total += body["value"]

SUITES = ("corpus", "pytest", "cargo", "npm-typescript", "npm-probes")
claims = {f"`{name}` green": status.get(name) == 0 for name in SUITES}
claims["E7's needles at 0 over every read transcript"] = (
    total == 0 and bool(needles))
dropped = []
if not needles:
    dropped.append("no read transcript was found to grep: 0 needles here "
                   "would be 0 files searched, not 0 found")
for name in SUITES:
    if name not in status:
        dropped.append(f"`{name}` never ran")

payload = cell(
    sum(1 for v in claims.values() if v), len(claims), dropped,
    rule="every corpus case equal, the four suites green, E7's needle grep "
         "at 0 over every transcript -> else STOP",
    claims=claims,
    suites={name: {"exit": status.get(name), "tail": tail(name)}
            for name in SUITES},
    vectors={"exit": status.get("vectors"),
             "tail": [ln for ln in (h8 / "vectors.txt").read_text(
                 encoding="utf-8", errors="replace").splitlines()
                 if ln.strip()][-2:]},
    needle_total=total, transcripts=len(needles), per_transcript=needles,
    cargo_target_dir_set=env["E12_CARGO_TARGET_SET"],
    recorder=os.environ.get("E12_RECORDER"),
    recorder_rev=os.environ.get("E12_REV"))
Path(env["E12_OUT"], "e12-h8.json").write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8")
emit({"value": payload["value"], "n": payload["n"],
      "dropped": payload["dropped"], "claims": payload["claims"],
      "needle_total": total, "transcripts": len(needles)})
PY
