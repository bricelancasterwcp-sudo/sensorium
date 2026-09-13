"""E14: does Rust's row say what its block unbound, and does the fold honour it?

    .venv/bin/python typescript/acceptance/e14_report.py <results dir>

Reads three files the operator writes into `<results dir>`; runs NOTHING. The
shapes are defined here and nowhere else:

* `corpus.json` -- one entry per case the corpus runner reported, the SAME
  file `e13_report.py` reads: `{"command": "<as run>", "exit": 0, "cases":
  {"focus_block_let": {"language": "rust", "exit": 0}, "refocus_env":
  {"language": "rust", "exit": 0}, ...}}`. A case is EQUAL when its exit is 0:
  that is what the runner means by a case whose answers match its questions.
* `vectors.json` -- `{"command": "…pytest -q tests/test_vectors.py -k v40",
  "exit": 0}`
* `refusals.json` -- `{"command": "cargo test -p cargo-sensorium spool::",
  "exit": 0}` -- the tag-3 cases: a name that is both a delta and an unbound
  in one record is a refusal naming the record and the name.

§1.6's five clauses, in its order. The fourth and fifth are read off
`corpus.json` and not off a second run: "every OTHER Rust case" is every Rust
case except `focus_block_let`, and the `refocus_*` clause is the subset of
those whose name starts with `refocus_`. Both are reported BY NAME, and both
refuse an empty set, so a corpus that silently lost its Rust cases cannot pass
by having nothing left to check.
"""
import json
import sys
from pathlib import Path

from e12_report import cell, emit, usage
from e12p_h8 import measured_claims, missing_inputs, read_input, value_of

#: The corpus case §1.6's first clause is about.
CASE = "focus_block_let"


def rust_cases(corpus: dict | None) -> dict:
    """Every case the runner called Rust, by name."""
    return {name: got for name, got in ((corpus or {}).get("cases") or {}).items()
            if got.get("language") == "rust"}


def build(results: Path) -> dict:
    corpus = read_input(results, "corpus.json")
    vectors = read_input(results, "vectors.json")
    refusals = read_input(results, "refusals.json")
    dropped = missing_inputs(results, ("corpus.json", "vectors.json",
                                       "refusals.json"))
    rust = rust_cases(corpus)
    others = {n: c for n, c in rust.items() if n != CASE}
    refocus = {n: c for n, c in rust.items() if n.startswith("refocus_")}
    moved = sorted(n for n, c in others.items() if c.get("exit") != 0)
    refocus_moved = sorted(n for n, c in refocus.items() if c.get("exit") != 0)
    claims = measured_claims(results, (
        ("corpus.json", f"`{CASE}` is green",
         lambda: rust.get(CASE, {}).get("exit") == 0),
        ("vectors.json", "`v40` round-trips", lambda: vectors["exit"] == 0),
        ("refusals.json", "the tag-3 refusal cases hold",
         lambda: refusals["exit"] == 0),
        ("corpus.json", "every other Rust corpus case is equal",
         lambda: bool(others) and not moved),
        ("corpus.json", "every `refocus_*` case is equal",
         lambda: bool(refocus) and not refocus_moved),
    ))
    return cell(value_of(claims), len(claims), dropped,
                rule="all five clauses of §1.6 hold -> PASS; any one is a STOP "
                     "recorded as a finding",
                instrument="e14_report.py", claims=claims,
                case=rust.get(CASE),
                rust_cases=sorted(rust), other_rust_cases=len(others),
                rust_cases_that_moved=moved,
                refocus_cases=sorted(refocus),
                refocus_cases_that_moved=refocus_moved,
                corpus={"command": (corpus or {}).get("command"),
                        "exit": (corpus or {}).get("exit"),
                        "cases": len((corpus or {}).get("cases") or {})},
                vectors=vectors, refusals=refusals)


def main(argv) -> int:
    if len(argv) != 2:
        usage("usage: e14_report.py <results dir>")
    results = Path(argv[1])
    if not results.is_dir():
        usage(f"no such results directory: {results}")
    payload = build(results)
    (results / "e14.json").write_text(json.dumps(payload, indent=2) + "\n",
                                      encoding="utf-8")
    emit({k: payload[k] for k in ("value", "n", "dropped", "claims")})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
