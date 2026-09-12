"""E13: is a finally after a return recorded, and only where the shape exists?

    .venv/bin/python typescript/acceptance/e13_report.py <results dir>

Reads four files the operator writes into `<results dir>`; runs NOTHING. Each
shape is defined here and nowhere else:
* `census.json` -- `census_deferred.mjs`'s output, its three roots in the
  census's own table order (probes, corpus, lens):
  `{"roots": [{"root": "<label>", "files_scanned": 21, "deferred":
  [{"rel": "<file, as the census spells it>", "qualname": "settle",
  "line": 7}]}, ...]}`
* `transform-diff.json` -- `transform_diff.mjs`'s own output over the
  census's two in-tree roots: `{"files_compared": 84, "changed": 1, "files":
  [{"file": "<rel>", "changed": true, "functions": ["settle"]}, ...]}`
* `corpus.json` -- one entry per case the corpus runner reported:
  `{"command": "<as run>", "exit": 0, "cases": {"focus_finally_return":
  {"language": "typescript", "exit": 0}}}`
* `honesty-cost.diff` -- the literal stdout of `git diff --stat <base> --
  typescript/HONESTY-COST.md`. EMPTY is the clause: the seam and the seal
  change no unfocused wrapper, so its cited numbers do not move.
§1.5's four clauses, in its order. The census's own table is the sha-pinned
hand file, read from the repository and never from `<results dir>`: a
prediction an operator could hand in is not a prediction.
"""
import json
import sys
from pathlib import Path

from e12_report import cell, emit, usage
from e12p_h8 import census_matches, missing_inputs, read_input
from e12p_pre import RECORD

#: The hand census, sha-pinned as §1's last line (A5), and the corpus case
#: §1.5's third clause is about.
CENSUS = RECORD.with_name("2026-09-12-sensorium-s5-rung4-debts-census.md")
CASE = "focus_finally_return"


def as_census_spells_it(census_files, rel: str) -> str:
    """A diff row's file, under the name the census gives it: the two agree on
    a `/`-boundary suffix (`transform_diff.mjs` spells a file relative to the
    ROOT it was handed, the census relative to the repository). A file the
    census never named keeps its own spelling and so shows up by name."""
    return next((f for f in census_files
                 if f == rel or f.endswith("/" + rel)), rel)


def build(results: Path) -> dict:
    census = results / "census.json"
    diff = read_input(results, "transform-diff.json")
    corpus = read_input(results, "corpus.json")
    cost = read_input(results, "honesty-cost.diff")
    dropped = missing_inputs(results, ("census.json", "transform-diff.json",
                                       "corpus.json", "honesty-cost.diff"))
    matched = census_matches(CENSUS, census) if census.is_file() else {
        "holds": False, "missing": [], "extra": [], "per_table": {}}
    want: dict[str, list] = {}
    for table in matched["per_table"].values():
        for file, qualname, _line in (tuple(row) for row in table["hand"]):
            want.setdefault(file, []).append(qualname)
    want = {f: sorted(v) for f, v in want.items()}
    changed = {as_census_spells_it(want, row["file"]):
               sorted(row.get("functions") or [])
               for row in (diff or {}).get("files", []) if row.get("changed")}
    cases = (corpus or {}).get("cases") or {}
    claims = {
        "`census_deferred.mjs` prints the three pinned lists exactly":
            matched["holds"],
        "the transform diff changes exactly the census's files and wrappers":
            diff is not None and changed == want,
        f"`{CASE}` is green": cases.get(CASE, {}).get("exit") == 0,
        "`HONESTY-COST.md`'s cited numbers are untouched":
            cost is not None and cost.strip() == "",
    }
    return cell(sum(1 for v in claims.values() if v), len(claims), dropped,
                rule="all four clauses of §1.5 hold -> PASS; any one is a STOP "
                     "recorded as a finding",
                instrument="e13_report.py", claims=claims, census=matched,
                census_file=CENSUS.name,
                transform_diff={"changed": changed, "expected": want,
                                "files_compared":
                                    (diff or {}).get("files_compared")},
                corpus={"command": (corpus or {}).get("command"),
                        "case": cases.get(CASE)}, honesty_cost_diff=cost)


def main(argv) -> int:
    if len(argv) != 2:
        usage("usage: e13_report.py <results dir>")
    results = Path(argv[1])
    if not results.is_dir():
        usage(f"no such results directory: {results}")
    payload = build(results)
    (results / "e13.json").write_text(json.dumps(payload, indent=2) + "\n",
                                      encoding="utf-8")
    emit({k: payload[k] for k in ("value", "n", "dropped", "claims")})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
