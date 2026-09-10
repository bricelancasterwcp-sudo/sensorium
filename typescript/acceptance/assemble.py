"""Every instrument's JSON, gathered into the acceptance record's results file.

    python3 assemble.py <results dir> <arms.jsonl> <out> [--redact PATH=LABEL]...

This is the only place a number reaches the record. Each gated endpoint is
one cell in the record's schema -- `{value, n, lens, dropped}` -- read from
the instrument that produced it; an instrument whose file is absent becomes
a `null` value with a `dropped` reason naming the file, never a zero and
never a missing key.

Two endpoints are DERIVED here rather than read, because their instrument is
a table of runs rather than a single measurement:

  E1'  the three arms' medians and the two ratios, over `arms.jsonl`. The
       plain arm is timed by the runner's own clock; the driver arms by the
       HARNESS wall out of `harness.json`, which excludes conversion, as the
       rule says. The driver's total wall is carried beside it, ungated.
  E5'  the call arm's suite being green (from the same table) and the
       `node --test` probe's checker being green (from its own JSON).

Trailing `PATH=LABEL` arguments rewrite a literal path to a label everywhere
in the output. The file is committed, so it must carry no box path at all: after
redaction the assembler REFUSES to write if any string still holds one.
"""
import json
import statistics
import sys
from pathlib import Path

from lens import LENS, cell

#: Files this assembler expects, and the record cell each becomes.
GATED_FILES = {
    "E0'": "e0.json",
    "E3-TS": "e3.json",
    "E4'": "e4-sites.json",
    "E6'": "e6.json",
    "E7'": "e7.json",
    "E8'": "e8.json",
    "E9": "e9.json",
}

#: The record has one row per endpoint, in this order.
ORDER = ["E0'", "E1'", "E2'", "E3-TS", "E4'", "E5'", "E6'", "E7'", "E8'",
         "E9", "E10", "E11"]
CONTROL_FILES = {"E5-TS, the split": "control-split.json",
                 "The planted change": "control-planted.json"}

#: Any of these left in a string means a box path survived redaction.
FORBIDDEN = ("/mnt/", "/home/", "/root/", "/tmp/")


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"_absent": f"{path.name} could not be read: {e}"}


def gated(results: Path, name: str, filename: str) -> dict:
    data = load(results / filename)
    if "_absent" in data:
        return cell(None, 0, [f"{name} was not measured: {data['_absent']}"])
    return data


# -- E1', derived from the arms table ---------------------------------------


def arms_table(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def arm_stats(rows: list[dict], arm: str, key: str) -> dict:
    """One arm's walls, and why any run of it was dropped."""
    mine = [r for r in rows if r["arm"] == arm]
    dropped = [f"{arm} run {r['run']}: " + "; ".join(r.get("why_not_ok", ["not ok"]))
               for r in mine if not r["ok"]]
    walls = []
    for r in mine:
        if not r["ok"]:
            continue
        w = r.get(key)
        if w is None:
            dropped.append(f"{arm} run {r['run']}: no {key} was recorded")
            continue
        walls.append(w)
    return {"runs": len(mine), "walls": walls, "dropped": dropped,
            # The load reading taken immediately before each run of this arm,
            # in run order. Carried rather than dropped: E1' is a timing
            # endpoint whose pre-registration refuses a run above 4.0, and a
            # guard whose readings never reach the record is a guard nobody
            # can audit.
            "loads": [r["load_1min"] for r in mine],
            "median": round(statistics.median(walls), 4) if walls else None,
            "min": min(walls) if walls else None,
            "max": max(walls) if walls else None,
            "mean": round(statistics.fmean(walls), 4) if walls else None,
            "stdev": (round(statistics.stdev(walls), 4) if len(walls) > 1
                      else None)}


def e1(rows: list[dict], want_n: int = 5) -> dict:
    plain = arm_stats(rows, "plain", "wall")
    off = arm_stats(rows, "off", "harness_wall")
    call = arm_stats(rows, "call", "harness_wall")
    off_total = arm_stats(rows, "off", "wall")
    call_total = arm_stats(rows, "call", "wall")

    dropped = []
    for name, arm in (("plain", plain), ("off", off), ("call", call)):
        dropped.extend(arm["dropped"])
        if len(arm["walls"]) < want_n:
            dropped.append(f"the {name} arm has {len(arm['walls'])} usable "
                           f"runs, fewer than the {want_n} the rule requires: "
                           "the arm is null")
            arm["median"] = None

    ratio = lambda x, y: (None if x is None or not y else round(x / y, 4))
    # Every load reading of the whole series, flat and in the order taken,
    # with the highest of them beside it -- so "all under the 4.0 refusal" is
    # a claim a reader can check against the numbers rather than take.
    readings = [{"arm": r["arm"], "batch": r["batch"], "run": r["run"],
                 "load_1min": r["load_1min"]} for r in rows]
    return cell(
        ratio(off["median"], plain["median"]),
        min(len(plain["walls"]), len(off["walls"]), len(call["walls"])),
        dropped,
        rule_arm="off/plain, harness wall, conversion excluded",
        load_guard={"threshold": 4.0, "n": len(readings),
                    "max": max((r["load_1min"] for r in readings),
                               default=None),
                    "min": min((r["load_1min"] for r in readings),
                               default=None),
                    "all_under_threshold": all(r["load_1min"] < 4.0
                                               for r in readings),
                    "readings": readings},
        arms={"plain": plain, "off": off, "call": call},
        driver_total_wall={"off": off_total, "call": call_total},
        off_over_plain=ratio(off["median"], plain["median"]),
        call_over_plain=ratio(call["median"], plain["median"]),
        off_total_over_plain=ratio(off_total["median"], plain["median"]),
        call_total_over_plain=ratio(call_total["median"], plain["median"]),
    )


# -- E2', derived from the census -------------------------------------------


def e2(results: Path) -> dict:
    raw = load(results / "e2-census.json")
    if "_absent" in raw:
        return cell(None, 0, [f"E2' was not measured: {raw['_absent']}"])
    return cell(raw["ratio"], raw["eligible"],
                files=raw["files"], instrumented=raw["instrumented"],
                eligible=raw["eligible"], failed=raw["failed"],
                parse_error=raw["parse_error"], excluded=raw["excluded"],
                by_kind=raw["by_kind"], bloat=raw["bloat"])


# -- E5', the two harnesses -------------------------------------------------


def e5(rows: list[dict], results: Path) -> dict:
    call = [r for r in rows if r["arm"] == "call"]
    green = [r for r in call if r["ok"]]
    nodetest = load(results / "e5-nodetest.json")
    dropped = []
    node_ok = None
    if "_absent" in nodetest:
        dropped.append(f"the node --test half was not measured: {nodetest['_absent']}")
    else:
        node_ok = bool(nodetest.get("ok"))
    claims = {"vitest_full_suite_green": bool(call) and len(green) == len(call),
              "node_test_probe_green": node_ok}
    return cell(sum(1 for v in claims.values() if v), len(claims), dropped,
                claims=claims,
                vitest={"call_runs": len(call), "green": len(green),
                        "runs": [{"run": r["run"], "ok": r["ok"],
                                  "exit": r["exit"],
                                  "files": r["suite_files_ok"],
                                  "tests": r["suite_tests_ok"]}
                                 for r in call]},
                node_test=({} if "_absent" in nodetest else
                           {"ok": nodetest.get("ok"),
                            "spools": nodetest.get("spools"),
                            "checks": len(nodetest.get("checks", [])),
                            "failures": nodetest.get("failures", [])}))


# -- E10 and E11, each two instrument runs under one record row -------------


def e10(results: Path) -> dict:
    """The two ingest lenses in one cell: the full-suite spool set, which the
    rule compares against the plain wall, and one file's, which is reported."""
    suite = load(results / "e10-suite.json")
    one = load(results / "e10-file.json")
    dropped = []
    for label, data in (("the full-suite ingest", suite), ("the one-file ingest", one)):
        if "_absent" in data:
            dropped.append(f"{label} was not measured: {data['_absent']}")
    return cell(None if "_absent" in suite else suite["value"],
                0 if "_absent" in suite else suite["n"], dropped,
                full_suite=None if "_absent" in suite else suite,
                one_file=None if "_absent" in one else one)


def e11(results: Path) -> dict:
    """Both halves of the loss model in one cell. `value` is how many of the
    two halves' claims held, out of every claim either half made -- a cell
    that reported only the half that passed would be the shape of dishonesty
    this endpoint exists to rule out."""
    a = load(results / "e11a.json")
    b = load(results / "e11b.json")
    dropped = []
    total = held = 0
    for label, data in (("half (a)", a), ("half (b)", b)):
        if "_absent" in data:
            dropped.append(f"E11 {label} was not measured: {data['_absent']}")
            continue
        dropped.extend(data.get("dropped", []))
        total += data["n"]
        held += data["value"] or 0
    return cell(None if total == 0 else held, total, dropped,
                half_a=None if "_absent" in a else a,
                half_b=None if "_absent" in b else b)


# -- reported without a gate ------------------------------------------------


def wire_costs(rows: list[dict]) -> dict:
    call = [r for r in rows if r["arm"] == "call" and r["ok"]
            and r.get("spool_lines")]
    if not call:
        return {"bytes_per_line": cell(None, 0, ["no call-arm run reported a spool"]),
                "lines_per_second": cell(None, 0, ["no call-arm run reported a spool"])}
    per_run_bpl = [r["spool_bytes"] / r["spool_lines"] for r in call]
    per_run_lps = [r["spool_lines"] / r["harness_wall"] for r in call
                   if r.get("harness_wall")]
    return {
        "bytes_per_line": cell(round(statistics.median(per_run_bpl), 2),
                               len(per_run_bpl),
                               per_run=[round(x, 2) for x in per_run_bpl],
                               total_bytes=sum(r["spool_bytes"] for r in call),
                               total_lines=sum(r["spool_lines"] for r in call)),
        "lines_per_second": cell(round(statistics.median(per_run_lps), 1)
                                 if per_run_lps else None,
                                 len(per_run_lps),
                                 per_run=[round(x, 1) for x in per_run_lps]),
    }


def transform_seconds(rows: list[dict]) -> dict:
    out = {}
    for arm in ("plain", "off", "call"):
        vals = [r["transform_s"] for r in rows
                if r["arm"] == arm and r["ok"] and r.get("transform_s") is not None]
        out[arm] = cell(round(statistics.median(vals), 4) if vals else None,
                        len(vals),
                        [] if vals else [f"no {arm} run printed a transform time"],
                        per_run=vals)
    return out


# -- the whole file ---------------------------------------------------------


def redact(node, pairs):
    if isinstance(node, str):
        for needle, label in pairs:
            node = node.replace(needle, label)
        return node
    if isinstance(node, list):
        return [redact(x, pairs) for x in node]
    if isinstance(node, dict):
        return {redact(k, pairs): redact(v, pairs) for k, v in node.items()}
    return node


def offenders(node, path="$"):
    if isinstance(node, str):
        return [(path, node)] if any(f in node for f in FORBIDDEN) else []
    if isinstance(node, list):
        return [o for i, x in enumerate(node) for o in offenders(x, f"{path}[{i}]")]
    if isinstance(node, dict):
        return [o for k, v in node.items() for o in offenders(v, f"{path}.{k}")]
    return []


def build(results: Path, arms_path: Path) -> dict:
    rows = arms_table(arms_path)
    payload = {
        "record": "docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md",
        "lens": LENS,
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value with a non-empty dropped list is the only "
                   "representation of 'not measured'; 0 is measured-and-zero"),
        "gated": {"E1'": e1(rows), "E2'": e2(results), "E5'": e5(rows, results),
                  "E10": e10(results), "E11": e11(results)},
        "controls": {name: gated(results, name, f)
                     for name, f in CONTROL_FILES.items()},
        "first_use": gated(results, "first use", "firstuse.json"),
        "reported": {},
    }
    for name, filename in GATED_FILES.items():
        payload["gated"][name] = gated(results, name, filename)
    payload["gated"] = {k: payload["gated"][k] for k in ORDER
                        if k in payload["gated"]}

    reported = load(results / "reported.json")
    payload["reported"] = {
        **wire_costs(rows),
        "vitest_transform_seconds_per_arm": transform_seconds(rows),
        "census_bloat": cell(
            payload["gated"]["E2'"].get("bloat"),
            payload["gated"]["E2'"].get("files"),
            [] if payload["gated"]["E2'"].get("bloat") is not None
            else ["the census was not measured"]),
        "info_and_diff_latency": (
            cell(None, 0, [f"not measured: {reported['_absent']}"])
            if "_absent" in reported
            else cell(reported["largest"]["info_median_s"],
                      reported["largest"]["n"], largest=reported["largest"])),
        "diverged_pairs_two_full_suite_runs": (
            cell(None, 0, [f"not measured: {reported['_absent']}"])
            if "_absent" in reported else reported),
    }
    return payload


def main(argv) -> int:
    args = argv[1:]
    if len(args) < 3:
        sys.stderr.write("usage: assemble.py <results dir> <arms.jsonl> <out> "
                         "[PATH=LABEL]...\n")
        return 2
    pairs = []
    for spec in args[3:]:
        if "=" not in spec:
            sys.stderr.write(f"a redaction is PATH=LABEL, not {spec!r}\n")
            return 2
        needle, _, label = spec.partition("=")
        pairs.append((needle, label))
    # Longest needle first: a store under the lens would otherwise be
    # half-rewritten by the lens's own, shorter prefix.
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    payload = redact(build(Path(args[0]), Path(args[1])), pairs)
    bad = offenders(payload)
    if bad:
        sys.stderr.write("assemble: a box path survived redaction and this "
                         "file is committed; add a PATH=LABEL for it:\n")
        for where, value in bad[:10]:
            sys.stderr.write(f"  {where}: {value[:160]}\n")
        return 2
    Path(args[2]).write_text(json.dumps(payload, indent=2) + "\n",
                             encoding="utf-8")
    sys.stderr.write(f"wrote {args[2]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
