"""S5 rung 2's cells, gathered into its acceptance record's results file.

    python3 assemble_rung2.py <results dir> <out> <recorder> <rev> [PATH=LABEL]...

Every instrument writes ONE cell per measurement into the store's `results/`
directory, so a cell nobody measured is a MISSING FILE rather than a key
somebody forgot -- and this assembler turns a missing file into `{value:
null, dropped: [...]}` naming it, never into an omission and never into a
zero. It shares `assemble.py`'s `redact`, `offenders` and `FORBIDDEN`: the
results file is COMMITTED, so a box path surviving redaction is a REFUSAL and
not a warning.

Three cells are DERIVED here rather than read, because their instrument is a
table of runs or a census rather than a single measurement:

  E2″   the ratio, out of `census_catch.mjs`'s two halves over the lens
  E5″   the two harnesses: the E6-TS′ call run's suite lines (the plan's
        order says that one run doubles as this endpoint's vitest half) and
        the `node --test` probe checker's own JSON
  E1‴  the three arms' medians and the two ratios, over `arms.jsonl`, by
        `assemble.py`'s own `e1` -- the same derivation rung 1 used, so the
        two rungs' numbers are comparable because they are the same
        arithmetic and not merely the same word

Nothing here is gated by this file. The verdict words are the RULE's, written
by hand into the record's §4 beside the rule that produced them; what this
assembles is the numbers those verdicts are read off.

PROVENANCE, AND WHY IT IS STAMPED HERE
--------------------------------------
Slice 2's final review found cells attributed to the WRONG recorder: `lens.
LENS` names the recorder that produced the LENS, which is a different and
older one than any later slice runs, and a cell carrying only that reads as
if the lens's recorder had taken the measurement. Three instruments already
record their own (`e6tsp_report.py`, `e8pp.py`, `e10p_report.py`); the rest
do not, so `<recorder>` and `<rev>` are REQUIRED arguments here and are
stamped onto every cell that carries none, with `recorder_basis` saying that
the stamp is the assembler's and not the instrument's. A cell that records
its own is never overwritten.
"""
import json
import sys
from pathlib import Path

from assemble import FORBIDDEN, arms_table, e1, offenders, redact  # noqa: F401
from lens import LENS, cell

#: The endpoint cells that are read straight from an instrument's JSON.
GATED_FILES = {
    "E6-TS": "e6ts.json",
    "E6-TS′": "e6tsp.json",
    "E8″": "e8pp.json",
    "E3-TS″": "e3.json",
    "E10″-suite": "e10pp-suite.json",
    "E10″-file": "e10pp-file.json",
}

#: The record's §3 row order.
ORDER = ["E6-TS", "E6-TS′", "E8″", "E2″", "E3-TS″", "E5″", "E7″", "E1‴",
         "E10″-suite", "E10″-file"]


#: What a cell's `recorder_basis` says about where its provenance came from.
#: EVERY cell gets one, including the ones that recorded their own: a record
#: that says "these two read `own`" and a file in which `own` never appears is
#: the same defect as the wrong recorder, one level up (fix round 1).
STAMPED = ("stamped by the assembler from the session's own invocation; this "
           "instrument does not record its recorder itself")
OWN = "own"


def stamp(node, recorder: str, rev: str):
    """Give every cell a `recorder_basis`, and a recorder if it has none.

    A cell is anything with the record's four keys. Walks the whole payload
    so a cell nested under `reported` is stamped like a top-level one. A cell
    that recorded its own recorder keeps it and is marked `own`; one that did
    not is given the session's and is marked as stamped. Neither branch
    touches `value`, `n`, `lens` or `dropped`.
    """
    if isinstance(node, list):
        return [stamp(x, recorder, rev) for x in node]
    if not isinstance(node, dict):
        return node
    out = {k: stamp(v, recorder, rev) for k, v in node.items()}
    if all(k in out for k in ("value", "n", "lens", "dropped")):
        if out.get("recorder"):
            out["recorder_basis"] = OWN
        else:
            out["recorder"] = recorder
            out["recorder_rev"] = rev
            out["recorder_basis"] = STAMPED
    return out


def load(path: Path):
    """One cell's JSON, or `_absent` with a reason that carries NO path.

    `str(OSError)` spells the whole filename it failed on, and this file is
    committed: a missing cell would otherwise smuggle the store's box path
    into `dropped` and the redaction refusal would fire on the one branch
    that is supposed to explain itself.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        return {"_absent": f"{path.name} could not be read: {e.strerror}"}
    except json.JSONDecodeError as e:
        return {"_absent": f"{path.name} is not JSON: {e.msg} "
                           f"(line {e.lineno}, column {e.colno})"}


def read_cell(results: Path, name: str, filename: str) -> dict:
    """One instrument's cell, or a null naming the file that was not there."""
    data = load(results / filename)
    if "_absent" in data:
        return cell(None, 0, [f"{name} was not measured: {data['_absent']}"])
    return data


def e2(results: Path) -> dict:
    """E2″: spliced / seen over the lens, after the NAMED exclusions.

    The census prints both halves and its own ratio; this reads them into
    the record's schema and carries the two lists -- the sanctioned
    exclusions and the misses -- whole, because "1.000 after named
    exclusions" is a claim about those lists and not only about the number.
    """
    raw = load(results / "e2pp-census.json")
    if "_absent" in raw:
        return cell(None, 0, [f"E2″ was not measured: {raw['_absent']}"])
    dropped = [f"{m['file']}:{m['line']} ({m['kind']}) is unspliced: {m['reason']}"
               for m in raw.get("unspliced", [])]
    dropped += [f"the census could not read {f['file']}: {f['error']}"
                for f in raw.get("failed", [])]
    return cell(raw.get("ratio"), raw.get("eligible", 0), dropped,
                files=raw.get("files"), seen_total=raw.get("seen_total"),
                spliced_total=raw.get("spliced_total"),
                by_site_kind={"catch_clauses": raw.get("catch_clauses"),
                              "callback_sites": raw.get("callback_sites"),
                              "then_sites": raw.get("then_sites"),
                              "finally_completing": raw.get("finally_completing")},
                spliced=raw.get("spliced"), by_how=raw.get("by_how"),
                excluded_by_design=raw.get("excluded_by_design"),
                unspliced=raw.get("unspliced"),
                excluded_files=raw.get("excluded"),
                parse_error=raw.get("parse_error"))


def e7(results: Path) -> dict:
    """E7″: the leak grep over BOTH transcripts §1 names.

    §1's rule is "0 occurrences … over the E6-TS′ transcript and over one
    single-trace `exceptions` transcript", so the cell's value is the total
    over the two and each transcript's own counts are carried whole. Summing
    them here rather than gating one and reporting the other keeps the number
    the record prints the number the rule asks for.
    """
    reader = load(results / "e7.json")
    invocation = load(results / "e7-invocation.json")
    dropped, total = [], 0
    per = {}
    for name, data in (("single_trace_reader", reader),
                       ("e6tsp_invocation", invocation)):
        if "_absent" in data:
            dropped.append(f"the {name} half was not measured: {data['_absent']}")
            per[name] = None
            continue
        per[name] = {"occurrences": data.get("occurrences"),
                     "total": data.get("value"),
                     "transcript_lines": data.get("transcript_lines"),
                     "context_mentions_not_gated":
                         data.get("context_mentions_not_gated")}
        total += data.get("value") or 0
    return cell(None if dropped else total,
                len(per), dropped,
                rule="0 occurrences of the nine needles over both transcripts; "
                     "plus v30-v33 green",
                needles=reader.get("needles") if "_absent" not in reader else None,
                case_sensitive=(reader.get("case_sensitive")
                                if "_absent" not in reader else None),
                halves=per,
                commands=reader.get("commands") if "_absent" not in reader else None,
                vectors=reader.get("vectors") if "_absent" not in reader else None)


def e5(results: Path) -> dict:
    """E5″: the vitest suite (E6-TS′'s one run) and the `node --test` probes."""
    sweep = load(results / "e6tsp.json")
    nodetest = load(results / "e5pp-nodetest.json")
    dropped, vitest_ok, node_ok = [], None, None
    run = {}
    if "_absent" in sweep:
        dropped.append("the vitest half was not measured: "
                       f"{sweep['_absent']}")
    else:
        run = sweep.get("call_run") or {}
        vitest_ok = bool(run.get("ok"))
    if "_absent" in nodetest:
        dropped.append(f"the node --test half was not measured: {nodetest['_absent']}")
    else:
        node_ok = bool(nodetest.get("ok"))
    claims = {"vitest_full_suite_green": vitest_ok,
              "node_test_probe_green": node_ok}
    return cell(sum(1 for v in claims.values() if v), len(claims), dropped,
                claims=claims,
                vitest={k: run.get(k) for k in
                        ("exit", "suite_files_ok", "suite_tests_ok", "ok",
                         "duration_line", "invocation")},
                node_test=({} if "_absent" in nodetest else
                           {"ok": nodetest.get("ok"),
                            "mode": nodetest.get("mode"),
                            "spools": nodetest.get("spools"),
                            "checks": len(nodetest.get("checks", [])),
                            "failures": nodetest.get("failures", [])}))


def reported(results: Path) -> dict:
    """§1's two ungated numbers, plus what a run costs to keep."""
    sweep = load(results / "e6tsp.json")
    census = load(results / "e2pp-census.json")
    out = {}
    if "_absent" in sweep:
        out["handled_by_how_on_the_lens_run"] = cell(
            None, 0, [f"not measured: {sweep['_absent']}"])
        out["lens_run_spool"] = cell(None, 0, [f"not measured: {sweep['_absent']}"])
    else:
        by_how = sweep.get("handled_by_how") or {}
        counts = by_how.get("counts") or {}
        out["handled_by_how_on_the_lens_run"] = cell(
            sum(counts.values()) if by_how.get("read") else None,
            by_how.get("members") or 0,
            [] if by_how.get("read") else [by_how.get("why", "not read")],
            counts=counts, recording=sweep.get("recorder"),
            recording_rev=sweep.get("recorder_rev"))
        run = sweep.get("call_run") or {}
        out["lens_run_spool"] = cell(
            run.get("spool_bytes"), 1,
            [] if run.get("spool_bytes") is not None else
            ["the call run left no spool this instrument could measure"],
            unit="bytes", spool_files=run.get("spool_files"),
            spool_lines=run.get("spool_lines"),
            harness_wall=run.get("harness_wall"), driver_wall=run.get("wall"),
            recording=sweep.get("recorder"),
            recording_rev=sweep.get("recorder_rev"))
    if "_absent" in census:
        out["catch_escaped_share"] = cell(None, 0,
                                          [f"not measured: {census['_absent']}"])
    else:
        by_how = census.get("by_how") or {}
        clauses = (census.get("spliced") or {}).get("catch_clause") or 0
        escaped = by_how.get("catch_escaped", 0)
        out["catch_escaped_share"] = cell(
            round(escaped / clauses, 4) if clauses else None, clauses,
            [] if clauses else ["no catch clause was spliced, so there is no "
                                "share to take"],
            rule="catch clauses the transform wrote `catch_escaped` on, over "
                 "the catch clauses it spliced (the escape rule's own verdict "
                 "distribution over the lens; no run has to happen to read it)",
            by_how=by_how)
    return out


def build(results: Path) -> dict:
    arms = results / "arms.jsonl"
    payload = {
        "record": "docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md",
        "lens": LENS,
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value with a non-empty dropped list is the only "
                   "representation of 'not measured'; 0 is measured-and-zero"),
        "gated": {"E2″": e2(results), "E5″": e5(results),
                  "E7″": e7(results)},
        "reported": reported(results),
    }
    payload["gated"]["E1‴"] = (
        e1(arms_table(arms)) if arms.is_file()
        else cell(None, 0, ["E1‴ was not measured: arms.jsonl is not there"]))
    for name, filename in GATED_FILES.items():
        payload["gated"][name] = read_cell(results, name, filename)
    payload["gated"] = {k: payload["gated"][k] for k in ORDER
                        if k in payload["gated"]}
    return payload


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 4:
        sys.stderr.write("usage: assemble_rung2.py <results dir> <out> "
                         "<recorder> <rev> [PATH=LABEL]...\n")
        return 2
    recorder, rev = args[2], args[3]
    if len(rev) != 40:
        sys.stderr.write("the rev is the FULL 40-character sha the cells were "
                         f"recorded at, not {rev!r}\n")
        return 2
    pairs = []
    for spec in args[4:]:
        if "=" not in spec:
            sys.stderr.write(f"a redaction is PATH=LABEL, not {spec!r}\n")
            return 2
        needle, _, label = spec.partition("=")
        pairs.append((needle, label))
    # Longest needle first: the worktree's own `sensorium` sits UNDER the
    # worktree, and the shorter prefix would half-rewrite it.
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    payload = build(Path(args[0]))
    payload["recorded_by"] = {"recorder": recorder, "commit": rev}
    payload = redact(stamp(payload, recorder, rev), pairs)
    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble_rung2: a box path survived redaction and "
                         "this file is committed; add a PATH=LABEL for it:\n")
        for where, value in bad[:10]:
            sys.stderr.write(f"  {where}: {value[:160]}\n")
        return 2
    Path(args[1]).write_text(json.dumps(payload, indent=2) + "\n",
                             encoding="utf-8")
    sys.stderr.write(f"wrote {args[1]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
