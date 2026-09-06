"""What the rung-4 entry run READS: an `exceptions` answer, and the record.

Split out of `acceptance_grain.py` because no file in this repository may
pass 800 lines, and because the split falls on a real seam: nothing here runs
a process, opens a socket or writes a byte. Every function takes text (or a
committed JSON record, or a trace opened read-only) and returns numbers, so
every one of them is testable without the box -- which is what
`tests/test_acceptance_grain.py` does.

Three things live here and are worth naming before the code:

* **the shape parser.** `exceptions` prints one block per SHAPE since 0.8.2
  (design N3-N6), and the block's bracket is where the CHAIN COUNT went. H2,
  H3 and H4 all add those counts up, so a bracket read wrongly -- a missing
  one as zero, `[in <run>]` as anything but one -- moves every number in the
  record.
* **the site.** The verdict names a qualname and a line; the E6⁗ record names
  a FILE and a line. The bridge is the trace's own `events` -> `code_objects`
  join, which is `acceptance_phases_rung3._sink_files`' query narrowed to the
  two columns a site needs.
* **the oracle.** The published record, read and never re-measured. Its one
  trap is none-versus-zero: a process that printed NO tally line is `None`
  there -- 30 per arm printed `no exceptions recorded` -- and summing that as
  `swallowed 0` would invent 30 measurements and put a tag in an arm's sum
  that no process ever printed.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

#: The three kept stores, and what §1 says each holds. `endpoint` is the
#: oracle's key; `traces` is the count the preflight refuses on; `run` is the
#: primary process the record names; `invocation` is the id H4 asks for
#: (`None` for the single-process arm, which has no invocation question).
ARMS = {
    "a": {"endpoint": "E6qA", "traces": 1,
          "run": "20260905-091115-5da3dc", "invocation": None},
    "ws": {"endpoint": "E6qWS", "traces": 144,
           "run": "20260905-091125-fcd2d2",
           "invocation": "20260905-091115-9e8e5a"},
    "ws0": {"endpoint": "E6qWS0", "traces": 144,
            "run": "20260905-091219-056f6a",
            "invocation": "20260905-091209-bfa73c"},
}
#: The arms H3 walks process by process, and H4 asks one invocation question
#: of. `a` is one process and has neither.
MULTI = ("ws", "ws0")

#: The `ws` process whose 0.8.1 output §1 reports beside this run's. Its
#: BEFORE bytes are the record's `sweep_processes[].stdout_bytes`; 0.8.1 is
#: not installed here and is never asked.
BUSIEST_WS_RUN = "20260905-091125-fc7302"

# ------------------------------------------------------------- the parsers

#: A block's head line: `  e340 HANDLED tests::fresh_dir handled … L156`.
HEAD = re.compile(r"^ {2}e(?P<id>\d+) (?P<kind>[A-Z]+) ")
#: A block's verdict line, at exactly four spaces. `print_shape` prints the
#: head at two, the verdict at four and everything under it at six, in both
#: single-run and invocation mode, so the indent is the grammar.
VERDICT = re.compile(r"^ {4}(?P<verdict>\S.*)$")
#: A line under the verdict: detail, hops, or a vary flag.
UNDER = re.compile(r"^ {6}(?P<line>\S.*)$")

#: The site the verdict is ABOUT, as every verdict that names one spells it:
#: `absorbed by <how> at e340 (tests::fresh_dir L156)`, `absorbed at e412
#: (…)`, `an Err(..) arm at e11 (collect L43)`. This is the SINK for a
#: swallow -- the id the E6⁗ record's own collector resolved to a file
#: (`acceptance_phases_rung3.SWALLOW_LINE`) -- and the ARM for an escaped
#: `Err`. It is NOT the origin: the bracket's ids are origins.
#: Since R-G12 the parenthetical may also carry the site's FILE, where two
#: shapes of one answer print the same `qualname L<line>`:
#: `absorbed by sink_let_underscore at e5 (sandbox L42 in
#: task_exec_run_test.rs)`. The trailing group is OPTIONAL, so an answer with
#: nothing to disambiguate parses exactly as it always did -- and the
#: basename is CAPTURED rather than skipped over, because it is the fact the
#: block adds and §1′ reports how many blocks carry it. Without this the
#: colliding blocks parsed to `(None, None, None)`, `measure_sites` dropped
#: each into `unresolved`, and H4′ would have STOPped on an artifact of its
#: own instrument -- on precisely the shapes the repair exists for (review
#: fix, 2026-09-05).
SITE = re.compile(r"\bat e(?P<event>\d+) \((?P<qualname>.+?) "
                  r"L(?P<line>\d+)(?: in (?P<file>[^)]*))?\)")

#: `exceptions_group.bracket`: `  [×4: e412, e417, …, … +44]`.
B_IDS = re.compile(r" {2}\[×(?P<n>\d+): (?P<ids>[^\]]*)\]$")
#: `exceptions_invocation.bracket`, the merged form.
B_OVER = re.compile(r" {2}\[×(?P<n>\d+) over (?P<m>\d+) process(?:es)?: "
                    r"first e(?P<first>\d+) in (?P<run>[^,\]]+), "
                    r"\+(?P<more>\d+)\]$")
#: …and its once-seen form (ruling R-G9): one chain, in a named process.
B_IN = re.compile(r" {2}\[in (?P<run>[^\]]+)\]$")

#: The four vary lines `exceptions_group.vary_lines` can print, by the word
#: that names what varied (rulings R-G3, R-G5, R-G6). Named as a TUPLE, and
#: the regex built from it, so the pattern and the ungated count cannot drift
#: apart: every kind is reported, and one that never fired is a measured 0
#: rather than an absent key (fix round 1, 2026-09-05 -- the first draft
#: dropped `details` from the published count because no block printed it,
#: which reads as "not measured" and was measured-and-zero).
VARY_KINDS = ("origins", "messages", "details", "routes")
VARY = re.compile(r"^(" + "|".join(VARY_KINDS) + r")\b")

INV = re.compile(r"^invocation (?P<id>\S+): cargo(?P<args>.*?) -- "
                 r"(?P<n>\d+) process(?:es)?, (?P<k>\d+) with Err chains, "
                 r"(?P<m>\d+) with none$", re.M)
#: The INCOMPLETE line an INVOCATION answer prints per member
#: (`exceptions_invocation._header`), which NAMES the process.
INCOMPLETE = re.compile(r"^INCOMPLETE: (?P<run>\S+) never finalized", re.M)
#: The banner a SINGLE-RUN answer prints instead (`caps.print_incomplete`),
#: which names no process because the ref the reader typed is the process.
#: It is a different sentence and the member regex does not match it (checked
#: 2026-09-05, fix round 1), so a run that stopped mid-flight was invisible to
#: H2 and H3 until this line existed -- and an empty answer on an unfinalized
#: recording reports where the RECORDING ended, not what the program did.
INCOMPLETE_BANNER = re.compile(
    r"^INCOMPLETE: this recording never finalized", re.M)
RAISED_INV = re.compile(r"^raised \((?P<chains>\d+) chains over "
                        r"(?P<procs>\d+) process(?:es)?, (?P<sites>\d+) "
                        r"swallowing sites\):$", re.M)
RAISED = re.compile(r"^raised \((?P<n>\d+)(?:[^)]*)\):$", re.M)
EMPTY_INV = re.compile(r"^no exceptions recorded across (?P<n>\d+) "
                       r"process(?:es)?$", re.M)
TALLY = "dispositions: "
SWALLOWED = "SWALLOWED"


def tally_counts(line: str | None) -> dict:
    """`dispositions: swallowed 14, ambiguous 8` -> `{...}`. `None` in, `{}`
    out -- and the CALLER decides whether an absent line means zero. It does
    not: `exceptions` prints only non-zero tags, and a process that printed
    no tally line printed `no exceptions recorded` instead."""
    counts: dict = {}
    if not line or not line.startswith(TALLY):
        return counts
    for part in line[len(TALLY):].split(", "):
        head, _, num = part.rpartition(" ")
        if head and num.isdigit():
            counts[head] = int(num)
    return counts


def _bracket(verdict: str) -> dict:
    """The bracket at the end of a verdict line, in whichever form it is.

    A verdict with NO bracket is a group of ONE -- single-run mode prints a
    lone chain's block bare. Reading that as zero would silently drop every
    unrepeated shape (five of E6⁗-A's fourteen lines) while still printing a
    total, so the miss would look like a measurement.
    """
    m = B_OVER.search(verdict)
    if m:
        return {"bracket": m.group(0), "n": int(m.group("n")),
                "processes": int(m.group("m")),
                "first_origin": int(m.group("first")),
                "run": m.group("run"), "ids": []}
    m = B_IN.search(verdict)
    if m:
        return {"bracket": m.group(0), "n": 1, "processes": 1,
                "first_origin": None, "run": m.group("run"), "ids": []}
    m = B_IDS.search(verdict)
    if m:
        ids = [int(i) for i in re.findall(r"e(\d+)", m.group("ids"))]
        return {"bracket": m.group(0), "n": int(m.group("n")),
                "processes": None, "first_origin": ids[0] if ids else None,
                "run": None, "ids": ids}
    return {"bracket": None, "n": 1, "processes": None,
            "first_origin": None, "run": None, "ids": []}


def parse_shapes(stdout: str) -> list[dict]:
    """Every printed block, as `exceptions` prints one per SHAPE (N3-N6).

    `n` is CHAINS -- what the tally counts and what the record's per-site
    table counts. `event` is the id the verdict names (the sink for a
    swallow); `first_origin` is the bracket's first id, which is an ORIGIN
    and a different thing. `run` is the process an invocation-mode bracket
    names, and is the trace `event` must be resolved in.
    """
    shapes: list[dict] = []
    head = None
    for line in stdout.splitlines():
        h = HEAD.match(line)
        if h:
            head = {"head": line.strip(), "head_event": int(h.group("id")),
                    "head_kind": h.group("kind")}
            continue
        v = VERDICT.match(line)
        if v:
            verdict = v.group("verdict")
            tag = verdict.split(" -- ")[0]
            site = SITE.search(verdict)
            shapes.append({
                "tag": tag, "verdict": verdict, "line": line,
                "swallowed": SWALLOWED in verdict,
                "event": int(site.group("event")) if site else None,
                "qualname": site.group("qualname") if site else None,
                "site_line": int(site.group("line")) if site else None,
                "site_file": site.group("file") if site else None,
                "vary": [], **_bracket(verdict), **(head or {})})
            head = None
            continue
        u = UNDER.match(line)
        if u and shapes and VARY.match(u.group("line")):
            shapes[-1]["vary"].append(u.group("line"))
    return shapes


def swallowed_shapes(stdout: str) -> list[dict]:
    """Only the accusations. `exceptions_rust` pins that the token
    `SWALLOWED` is printed by exactly one sentence, so this is the whole set
    the record's per-site table was built from."""
    return [s for s in parse_shapes(stdout) if s["swallowed"]]


def disambiguated_shapes(stdout: str) -> int:
    """How many printed blocks name their site's FILE -- §1′'s ungated
    collision count (R-G12).

    Blocks that NAME A FILE, never blocks: a count of every block could not
    report zero and would say nothing about how ambiguous the answer was.
    Read off the answer itself rather than recomputed from the traces,
    because what §1′ asks is how many blocks a READER sees a file on.
    """
    return sum(1 for s in parse_shapes(stdout) if s["site_file"])


def vary_counts(stdout: str) -> dict:
    """How many blocks printed each kind of vary line -- §1's ungated honesty
    count. A group whose members differ in something the key did not look at
    is FLAGGED, and this counts the flags."""
    counts: Counter = Counter()
    for s in parse_shapes(stdout):
        for line in s["vary"]:
            counts[VARY.match(line).group(1)] += 1
    return dict(counts)


def with_every_vary_kind(counts) -> dict:
    """`{kind: n}` for EVERY spelling `VARY` can match, zero-filled.

    A kind no block printed is measured-and-zero, and a published count that
    simply omits it cannot be told apart from one that never looked. Used by
    `reported` for a fresh run and by `acceptance_grain_schema.assemble_grain`
    for a record already on disk, so the same record assembles the same way
    whenever it is re-derived.
    """
    return {kind: int((counts or {}).get(kind, 0)) for kind in VARY_KINDS}


def parse_tally(stdout: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith(TALLY):
            return line
    return None


def parse_header(stdout: str) -> dict:
    """The answer's frame: the invocation line and its counts, every
    INCOMPLETE member by name, the `raised (…)` line, the tally, and whether
    this was the empty-answer shape.

    Single-run answers have no invocation line and get `None` for its fields
    -- never a 1, which would report 288 processes as 288 invocations.
    """
    inv = INV.search(stdout)
    raised_inv = RAISED_INV.search(stdout)
    raised = RAISED.search(stdout)
    empty_inv = EMPTY_INV.search(stdout)
    tally_line = parse_tally(stdout)
    chains = None
    if raised_inv:
        chains = int(raised_inv.group("chains"))
    elif raised:
        chains = int(raised.group("n"))
    return {
        "invocation": inv.group("id") if inv else None,
        "cargo": inv.group("args").strip() if inv else None,
        "processes": int(inv.group("n")) if inv else None,
        "with_chains": int(inv.group("k")) if inv else None,
        "without_chains": int(inv.group("m")) if inv else None,
        "incomplete": INCOMPLETE.findall(stdout),
        "incomplete_banner": bool(INCOMPLETE_BANNER.search(stdout)),
        "chains": chains,
        "over_processes": (int(raised_inv.group("procs")) if raised_inv
                           else None),
        "swallowing_sites": (int(raised_inv.group("sites")) if raised_inv
                             else None),
        "tally_line": tally_line, "tally": tally_counts(tally_line),
        "empty": bool(empty_inv) or "no exceptions recorded" in stdout,
        "empty_across": int(empty_inv.group("n")) if empty_inv else None,
        "partial_line": next((ln for ln in stdout.splitlines()
                              if ln.startswith("partial: ")), None),
        "panics_line": next((ln for ln in stdout.splitlines()
                             if ln.startswith("panics: ")), None),
        "more_note": next((ln for ln in stdout.splitlines()
                           if ln.startswith("... ")), None),
    }


# ------------------------------------------------------------ the site join


def sites_of_events(db_path, event_ids) -> dict:
    """`{event id: (file, line)}` for one trace, in one query.

    The join is `acceptance_phases_rung3._sink_files`' -- `events` LEFT JOIN
    `code_objects` on `code_id` -- narrowed to the two columns a site needs.
    The verdict sentence carries a qualname and a line; the record's table
    carries a FILE, and nothing but this join bridges them. Read-only.
    """
    ids = [int(i) for i in event_ids]
    db = Path(db_path)
    if not db.is_file() or not ids:
        return {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        marks = ",".join("?" * len(ids))
        rows = con.execute(
            "select e.id, c.file, e.line "
            "from events e left join code_objects c on c.id = e.code_id "
            f"where e.id in ({marks})", ids).fetchall()
    finally:
        con.close()
    return {r[0]: (r[1], r[2]) for r in rows}


def site_of_event(db_path, event_id) -> tuple:
    """One event's `(file, line)`, or `(None, None)` when the trace does not
    hold it -- which is a HOLE in the evidence and is reported as one, never
    folded into the multiset as an extra site."""
    return sites_of_events(db_path, [event_id]).get(int(event_id),
                                                    (None, None))


def store_paths(paths, label: str) -> dict:
    """A `paths` dict pointing at ONE kept store.

    `sensorium_cli` and `acceptance_phases_rung3._sink_files` both resolve a
    store through `paths["sensorium_dir"]`, so this is the whole of what an
    arm needs. It is deliberately NOT `paths["sensorium_dir"]` itself: that
    one is the fresh directory H1's preflight requires to be empty, and an
    arm reading it would find no traces at all."""
    return dict(paths) | {"sensorium_dir": paths["e6q_stores"] / label}


def trace_db(paths, run_id: str) -> Path:
    return paths["sensorium_dir"] / "traces" / f"{run_id}.db"


# --------------------------------------------------------------- the oracle


def oracle(results_json) -> dict:
    """The PUBLISHED E6⁗ record, read as the per-arm tables H2-H4 compare
    against. Nothing here measures anything.

    Per arm: the per-SINK-SITE multiset over the primary process's SWALLOWED
    lines AND the sweep's (the record splits them; a reader of one half would
    miss 781 of E6⁗-WS's 782), the per-process tally line, the per-process
    swallow count, and the summed tally.

    A process that printed NO tally line is `None` in `per_process` and
    contributes NOTHING to the sum. That is not a zero: `exceptions` prints
    only non-zero tags, and those 30 processes per arm printed `no exceptions
    recorded` instead. Summing them as `swallowed 0` would invent a
    measurement and put a tag in an arm's sum that no process ever printed.
    """
    doc = (results_json if isinstance(results_json, dict)
           else json.loads(Path(results_json).read_text()))
    ep = doc.get("endpoints") or {}
    orc: dict = {"record": (None if isinstance(results_json, dict)
                            else str(results_json)),
                 "sites": {}, "lines": {}, "tallies": {}, "per_process": {},
                 "swallowed_count": {}, "stdout_bytes": {}, "runs": {},
                 "processes": {}, "tally_lines": {},
                 "without_a_tally_line": {}}
    for label, spec in ARMS.items():
        e = ep.get(spec["endpoint"]) or {}
        primary = e.get("run")
        sites: Counter = Counter()
        for p in e.get("swallowed") or []:
            s = p.get("sink") or {}
            sites[(s.get("file"), s.get("line"))] += 1
        for p in e.get("swallowed_sweep") or []:
            s = p.get("sink") or {}
            sites[(s.get("file"), s.get("line"))] += 1
        per_process = {primary: e.get("tally_line")}
        counts = {primary: len(e.get("swallowed") or [])}
        stdout_bytes: dict = {}
        for sp in e.get("sweep_processes") or []:
            per_process[sp["run"]] = sp.get("tally_line")
            counts[sp["run"]] = sp.get("swallowed_count")
            stdout_bytes[sp["run"]] = sp.get("stdout_bytes")
        summed: Counter = Counter()
        printed = 0
        for line in per_process.values():
            if line is None:
                continue
            printed += 1
            summed.update(tally_counts(line))
        orc[label] = sites
        orc["sites"][label] = len(sites)
        orc["lines"][label] = sum(sites.values())
        orc["tallies"][label] = dict(summed)
        orc["per_process"][label] = per_process
        orc["swallowed_count"][label] = counts
        orc["stdout_bytes"][label] = stdout_bytes
        orc["runs"][label] = primary
        orc["processes"][label] = len(per_process)
        orc["tally_lines"][label] = printed
        orc["without_a_tally_line"][label] = len(per_process) - printed
    return orc


def site_table(sites) -> dict:
    """A per-site multiset with STRING keys: `{"<file>:<line>": n}`.

    `oracle`'s and `measure_sites`' tables are keyed by `(file, line)`
    TUPLES, because that is the key a multiset comparison needs. JSON has no
    such key: `json.dumps` raises `TypeError: keys must be str, int, float,
    bool or None, not tuple`, and `default=` never applies to KEYS, so no
    fallback rescues it. Everything that goes into the raw record passes
    through here first (fix round 1: the raw-json write is the last act of an
    hour-long run and was outside the try, so one tuple key lost the whole
    record AND both markers).
    """
    return {f"{f}:{ln}": n for (f, ln), n in sorted(sites.items(), key=str)}


def oracle_json(orc: dict) -> dict:
    """`oracle()`'s record, with the three per-arm site tables stringified so
    the whole thing serialises. Every other value it holds is already a
    scalar, a list or a string-keyed dict."""
    out = dict(orc)
    for label in ARMS:
        if isinstance(out.get(label), dict):
            out[label] = site_table(out[label])
    return out


def compare_sites(measured: Counter, expected: Counter) -> dict:
    """Two per-site multisets, compared as multisets.

    A site the record has and the view does not is MISSING; one the view has
    and the record does not is EXTRA; a site both hold at different counts is
    a COUNT DIFF -- three different failures, never added together and never
    ignored. `equal` is true only when all three are empty: a comparison that
    checked the site SET alone would pass a view that found the record's 91
    sites and put any number of lines under them.
    """
    missing = [{"site": s, "expected": expected[s]}
               for s in sorted(set(expected) - set(measured), key=str)]
    extra = [{"site": s, "measured": measured[s]}
             for s in sorted(set(measured) - set(expected), key=str)]
    diffs = [{"site": s, "measured": measured[s], "expected": expected[s]}
             for s in sorted(set(measured) & set(expected), key=str)
             if measured[s] != expected[s]]
    return {"equal": not (missing or extra or diffs),
            "differences": len(missing) + len(extra) + len(diffs),
            "missing": missing, "extra": extra, "count_diffs": diffs,
            "measured_sites": len(measured), "expected_sites": len(expected),
            "measured_lines": sum(measured.values()),
            "expected_lines": sum(expected.values())}



def measure_sites(store: dict, stdout: str, default_run: str) -> dict:
    """The per-SINK-SITE multiset of one answer.

    Each SWALLOWED group contributes its CHAIN COUNT at the site its verdict
    names, resolved through the trace's own join. In invocation mode the
    bracket names the process the printed block belongs to and that is the
    trace the id is resolved in; in single-run mode there is one.

    `store` is a `paths` dict already pointed at ONE kept store
    (`acceptance_grain.store_paths`), so nothing here needs to know which arm
    it is reading.
    """
    sp = store
    shapes = swallowed_shapes(stdout)
    # Whether this is an invocation answer is read off the ANSWER, not passed
    # in: a caller that could say which mode it was reading could say it
    # wrongly, and the header is the answer's own word for it.
    invocation = parse_header(stdout)["invocation"] is not None
    sites: Counter = Counter()
    by_run: dict = {}
    unresolved = []
    for s in shapes:
        run_id = s["run"] or (None if invocation else default_run)
        if run_id is None:
            # In invocation mode EVERY block carries a bracket naming its
            # process (ruling R-G9), so a block without one is a bracket this
            # parser could not read. Falling back to the primary would look
            # its sink id up in the FIRST member's trace and return a REAL
            # but WRONG (file, line) -- a wrong site is worse than a missing
            # one, because nothing downstream can tell it from a measurement.
            unresolved.append({
                "run": None, "event": s["event"], "verdict": s["verdict"],
                "n": s["n"],
                "why": "the block named no process, and in invocation mode "
                       "there is no primary trace to fall back to"})
            continue
        by_run.setdefault(run_id, []).append(s)
    for run_id, group in by_run.items():
        found = sites_of_events(trace_db(sp, run_id),
                                [s["event"] for s in group
                                 if s["event"] is not None])
        for s in group:
            file, line = found.get(s["event"], (None, None))
            if file is None or line is None:
                unresolved.append({"run": run_id, "event": s["event"],
                                   "verdict": s["verdict"], "n": s["n"]})
                continue
            sites[(file, line)] += s["n"]
    return {"sites": sites, "groups": len(shapes),
            "chains": sum(s["n"] for s in shapes),
            "unresolved": unresolved, "unresolved_count": len(unresolved),
            "runs_named": sorted(by_run)}




# ---------------------------------------------------------------- reported


def reported(cfg, orc, h2, h3, h4) -> dict:
    """§1's ungated numbers. Each says which side it came from: the 0.8.1
    figures are the RECORD's and were never re-measured here."""
    busiest = cfg["busiest_ws_run"]
    row = next((r for r in ((h3.get("arms") or {}).get("ws") or {}).get(
        "rows") or [] if r["run"] == busiest), None)
    ws = ((h3.get("arms") or {}).get("ws") or {})
    inv = ((h4.get("arms") or {}).get("ws") or {})
    # Every answer this run actually READ, named. The first draft summed H2,
    # the H3 arms and H4's `ws` only -- `ws0`'s invocation answer, one of the
    # two the slice exists to produce, was silently outside the total.
    vary: Counter = Counter({kind: 0 for kind in VARY_KINDS})
    counted = []
    # R-G12's count is kept PER ANSWER, not summed: §1′ predicts >= 2 in each
    # invocation arm (`sandbox L42`, `fresh_dir L64`), and one total could
    # not be read against that. A phase that recorded no count is absent from
    # the dict rather than a 0 -- not-looked-at is not measured-and-zero.
    disambiguated: dict = {}
    if h2:
        vary.update(h2.get("vary") or {})
        counted.append("H2")
        if h2.get("disambiguated") is not None:
            disambiguated["H2"] = h2["disambiguated"]
    for label, a in sorted((h3.get("arms") or {}).items()):
        vary.update((a or {}).get("vary") or {})
        counted.append(f"H3/{label}")
        if (a or {}).get("disambiguated") is not None:
            disambiguated[f"H3/{label}"] = a["disambiguated"]
    for label, a in sorted((h4.get("arms") or {}).items()):
        vary.update((a or {}).get("vary") or {})
        counted.append(f"H4/{label}")
        if (a or {}).get("disambiguated") is not None:
            disambiguated[f"H4/{label}"] = a["disambiguated"]
    return {
        "busiest_ws_process": {
            "run": busiest,
            "bytes_0_8_1": (orc["stdout_bytes"]["ws"] or {}).get(busiest),
            "bytes_0_8_2": (row or {}).get("stdout_bytes"),
            "lines_0_8_2": (row or {}).get("stdout_lines"),
            "groups_0_8_2": (row or {}).get("groups"),
            "chains_0_8_2": (row or {}).get("chains"),
            "swallowed_lines_0_8_1": (
                orc["swallowed_count"]["ws"] or {}).get(busiest),
            "lines_0_8_1": None,
            "note": ("the 0.8.1 bytes and swallow count are the E6⁗ record's "
                     "`sweep_processes[]` row for this run, read and never "
                     "re-measured -- 0.8.1 is not installed here; the record "
                     "carries no LINE count for it, so that half is absent "
                     "rather than derived"),
        },
        "per_process_versus_invocation": {
            "per_process_bytes_total": ws.get("stdout_bytes_total"),
            "per_process_lines_total": ws.get("stdout_lines_total"),
            "processes": ws.get("processes"),
            "invocation_bytes": inv.get("stdout_bytes"),
            "invocation_lines": inv.get("stdout_lines"),
            "note": "both halves measured by THIS run, under 0.8.2",
        },
        "disambiguated_shapes": disambiguated,
        "disambiguated_lens": (
            "printed blocks whose site parenthetical carries ` in <file>` "
            "because their site text named more than one place in THAT "
            "answer (R-G12), one number per answer read; an honesty count, "
            "not a gate. An answer absent from this map recorded no count "
            "rather than a zero."),
        "vary_lines_by_kind": with_every_vary_kind(vary),
        "vary_counted_over": counted,
        "vary_lens": ("blocks that printed a vary line, summed over EVERY "
                      "answer this run read and named in `vary_counted_over` "
                      "(" + ", ".join(counted) + "); every spelling is "
                      "reported, so a kind at 0 printed none rather than "
                      "going unlooked-at; an honesty count, not a gate"),
    }


