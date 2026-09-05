"""The rung-3 acceptance phases: E6, E6', E2'', E0'' and E7''.

A NEW module rather than more of `acceptance_phases.py`, for two reasons.
`acceptance_phases.py` is the instrument the rung-2 record rests on and is
left byte-unchanged; and it is already 643 lines, so the ~380 added here
would put it past the repo's 800-line ceiling. Everything rung 2 measured the
same way is IMPORTED from it (`phase_e3`, `phase_e5`, `phase_walls`,
`phase_census`, `_build`, `_verdict`), never re-implemented: E3'' and E5'' are
"the rung-2 protocol verbatim" and a second copy of a protocol is a second
protocol.

Each phase returns RAW FACTS. Nothing here decides a verdict -- §4 of
`docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md` is
written by hand against §1's rules, and `acceptance_schema_rung3.assemble_rung3`
turns these facts into the none-versus-zero `results.json`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from acceptance_lib import (REPO, Refused, driver_cmd, manifests_dir,  # noqa: F401
                            plain_env, rmtree, run, run_lines,
                            sensorium_cli, spool_of, step, target_env,
                            trace_bytes, trace_meta)
from acceptance_phases import _build, _verdict, verdict_line           # noqa: F401

# ------------------------------------------------------------------ E6

#: The one substring `exceptions` prints for an accusation. `exceptions_rust`
#: pins that this token appears in exactly one sentence, so counting lines
#: that contain it counts accusations.
SWALLOWED = "SWALLOWED"

#: The tally line's prefix. `exceptions_rust.run` prints only NON-ZERO tags,
#: so an empty swallow set is registered as an ABSENCE by the case, never as
#: `swallowed 0` (there is no such line to assert).
TALLY = "dispositions: "

#: The answer shape that carries no tally line at all.
EMPTY_ANSWER = "no exceptions recorded"


def _corpus_module():
    """`corpus/run_corpus.py`, imported as the corpus's own module.

    The case list, the `$RUN` substitution and the corpus's own
    `check_question` reading all come from the committed harness rather than
    from a copy here: a collector that re-derived them could disagree with
    the suite about what a case says."""
    root = str(REPO)
    if root not in sys.path:
        sys.path.insert(0, root)
    from corpus import run_corpus                                  # noqa: PLC0415
    return run_corpus


def swallow_registration(q: dict) -> dict:
    """One question's PRE-REGISTERED swallow set and tally, from the case file.

    The shape is the one `tests/test_corpus.py::
    test_every_rust_exceptions_question_preregisters_its_swallow_set` enforces,
    read here rather than re-invented:

    * the swallow set is the `expect_line` groups whose FIRST needle is
      `SWALLOWED`, and `expect_count["SWALLOWED"]` pins how many there are;
    * an EMPTY swallow set is said, not left to absence: `SWALLOWED` and
      `dispositions: swallowed` both in `expect_absent`;
    * the tally is the ONE `expect_contains` entry starting `dispositions: `,
      registered as a whole line;
    * the `no exceptions recorded` shape registers that NO tally was printed.
    """
    contains = q.get("expect_contains") or []
    absent = q.get("expect_absent") or []
    groups = [g for g in (q.get("expect_line") or []) if g and g[0] == SWALLOWED]
    tally = [c for c in contains if c.startswith(TALLY)]
    empty_answer = EMPTY_ANSWER in contains
    count = (q.get("expect_count") or {}).get(SWALLOWED)
    if count is None:
        count = 0 if SWALLOWED in absent else len(groups)
    return {
        "swallow_groups": groups,
        "expected_swallowed": count,
        "empty_set_declared": SWALLOWED in absent,
        "tally_pinned": tally[0] if len(tally) == 1 else None,
        "tally_pins": tally,
        "empty_answer_expected": empty_answer,
        "no_tally_expected": empty_answer and TALLY.rstrip() in absent,
        "expect_absent": absent,
    }


def _match_groups(groups: list, lines: list) -> dict:
    """A PERFECT matching between registered groups and printed lines.

    Equality, not containment, is what §1 asks for, and a group-by-group
    `any(...)` is not equality: two registered groups can both match ONE
    printed line while a second printed line goes unclaimed, and a subset
    test would call that a pass. This is the standard augmenting-path
    matching over a tiny bipartite graph (at most two groups per case), so
    every group gets its OWN line or is reported unmatched, and every line
    not claimed by some group is reported as an extra -- which is the false
    accusation E6 exists to catch."""
    fits = [[i for i, ln in enumerate(lines) if all(n in ln for n in g)]
            for g in groups]
    owner: dict[int, int] = {}          # line index -> group index

    def assign(g: int, seen: set) -> bool:
        for li in fits[g]:
            if li in seen:
                continue
            seen.add(li)
            if li not in owner or assign(owner[li], seen):
                owner[li] = g
                return True
        return False

    for gi in range(len(groups)):
        assign(gi, set())
    matched = {gi: li for li, gi in owner.items()}
    return {
        "pairs": [{"group": groups[gi], "line": lines[li]}
                  for gi, li in sorted(matched.items())],
        "unmatched_groups": [groups[gi] for gi in range(len(groups))
                             if gi not in matched],
        "unclaimed_lines": [ln for li, ln in enumerate(lines)
                            if li not in owner],
    }


def collect_e6(q: dict, text: str) -> dict:
    """One `exceptions` answer against one question's registration.

    Returns raw facts and the three conjuncts §1 names, each as its own
    boolean beside the numbers that produced it. It decides no verdict."""
    reg = swallow_registration(q)
    printed = [ln for ln in text.splitlines() if SWALLOWED in ln]
    tallies = [ln for ln in text.splitlines() if ln.startswith(TALLY)]
    m = _match_groups(reg["swallow_groups"], printed)
    equal = (len(printed) == reg["expected_swallowed"]
             and not m["unmatched_groups"] and not m["unclaimed_lines"])
    if reg["empty_answer_expected"]:
        tally_equal = not tallies
        tally_read = "no tally line printed (the `no exceptions recorded` shape)"
    else:
        tally_equal = (len(tallies) == 1 and reg["tally_pinned"] is not None
                       and tallies[0] == reg["tally_pinned"])
        tally_read = "the printed `dispositions:` line == the pinned whole line"
    return {
        **reg,
        "printed_swallowed": printed,
        "printed_swallowed_count": len(printed),
        "extra_swallowed_lines": m["unclaimed_lines"],
        "missing_swallow_groups": m["unmatched_groups"],
        "matched_pairs": m["pairs"],
        "swallow_set_equal": equal,
        "swallow_set_nonempty_ok": (reg["expected_swallowed"] == 0
                                    or len(printed) > 0),
        "printed_tally": tallies[0] if len(tallies) == 1 else None,
        "printed_tallies": tallies,
        "tally_equal": tally_equal,
        "tally_reading": tally_read,
        # The corpus's own reading of the same output, for free: a substring
        # check where §1 asks for equality. Reported, never gated.
        "corpus_check_failures": None,
    }


def _record_corpus_case(paths, cfg, case, wd: Path, sdir: Path) -> dict:
    """One `cargo sensorium <cargo_args>` recording of one copied case.

    `plain_env()` first, so no `SENSORIUM_*` of the acceptance run leaks into
    a corpus recording: the only two this invocation may see are the ones set
    here."""
    argv = [str(paths["sensorium_driver"]), "sensorium",
            *[str(a) for a in case.cargo_args]]
    env = plain_env() | {"CARGO_TARGET_DIR": str(cfg["corpus_target"]),
                         "SENSORIUM_DIR": str(sdir),
                         "PYTHONDONTWRITEBYTECODE": "1"}
    res = run(argv, wd, f"e6-{case.name.replace('/', '-')}-record.log", env,
              timeout=cfg.get("e6_record_timeout", 1800))
    return res


def _reader(paths, args, cwd: Path, sdir: Path, label: str, timeout=600) -> dict:
    """The Python reader, from the repo's venv, against a case's own store."""
    env = plain_env() | {"SENSORIUM_DIR": str(sdir),
                         "PYTHONDONTWRITEBYTECODE": "1"}
    return run([str(REPO / ".venv" / "bin" / "python"), "-m", "sensorium",
                *args], cwd, f"e6-{label}.log", env, timeout)


def phase_e6(paths, cfg) -> dict:
    """E6: every `corpus/rust/*` case with an `exceptions` question, recorded
    ONCE under the rung-3 driver, and every printed SWALLOWED line and
    `dispositions:` tally compared with that case's pre-registered set."""
    rc = _corpus_module()
    cases = [c for c in rc.load_cases()
             if c.is_cargo and any(q["command"][0] == "exceptions"
                                   for q in c.questions)]
    workroot = Path(cfg["e6_workdir"])
    rmtree(workroot)
    workroot.mkdir(parents=True, exist_ok=True)
    out = {"corpus_root": str(REPO / "corpus"),
           "cases_selected": [c.name for c in cases],
           "driver": str(paths["sensorium_driver"]),
           "corpus_target": str(cfg["corpus_target"]),
           "workdir": str(workroot), "cases": []}
    for case in cases:
        wd = workroot / case.name.replace("/", "-")
        shutil.copytree(case.dir, wd, ignore=shutil.ignore_patterns(
            "__pycache__", "target", "Cargo.lock", ".sensorium"))
        sdir = wd / ".sensorium"
        rec = _record_corpus_case(paths, cfg, case, wd, sdir)
        ids = rc._run_ids(rec["out"])
        row = {"case": case.name, "cargo_args": case.cargo_args,
               "record_rc": rec["rc"], "record_wall": round(rec["wall"], 3),
               "run_ids": ids, "log": rec["log"], "questions": []}
        if not ids:
            row["dropped"] = ("the recording produced no `run:` line: "
                              f"exit {rec['rc']}")
            out["cases"].append(row)
            step(f"E6 {case.name}: DROPPED (no trace; exit {rec['rc']})")
            continue
        run_id = ids[0]
        run_id2 = ids[1] if len(ids) > 1 else None
        for spec in case.questions:
            if spec["command"][0] != "exceptions":
                continue
            q = rc.sub_run_ids(spec, run_id, run_id2)
            argv = [str(a) for a in q["command"]]
            label = f"{case.name.replace('/', '-')}-{q['id']}"
            r = _reader(paths, argv, wd, sdir, label)
            text = r["out"] + r["err"]
            got = collect_e6(q, text)
            got["corpus_check_failures"] = rc.check_question(q, text, r["rc"])
            got.update({"id": q["id"], "argv": argv, "rc": r["rc"],
                        "expect_exit": q.get("expect_exit", 0),
                        "log": r["log"]})
            row["questions"].append(got)
            step(f"E6 {case.name}/{q['id']}: swallowed "
                 f"{got['printed_swallowed_count']}/"
                 f"{got['expected_swallowed']} equal={got['swallow_set_equal']} "
                 f"tally={got['tally_equal']}")
        out["cases"].append(row)
    return out


# ------------------------------------------------------------------ E6'

SWALLOW_LINE = re.compile(
    r"SWALLOWED -- (?:absorbed by (?P<how>\S+) at |absorbed at )"
    r"e(?P<event>\d+) \((?P<qualname>.+?) L(?P<line>\d+)\)"
    r"(?: in f(?P<frame>\d+))?")


def _sink_files(paths, run_id: str, event_ids: list[int]) -> dict:
    """The FILE each SWALLOWED line's sink event sits in.

    The verdict sentence carries the qualname and the line but not the path,
    and the adjudication in §4 is against a file. Read from the trace's own
    `events` -> `code_objects` join, read-only."""
    db = paths["sensorium_dir"] / "traces" / f"{run_id}.db"
    if not db.is_file() or not event_ids:
        return {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        marks = ",".join("?" * len(event_ids))
        rows = con.execute(
            "select e.id, e.line, e.kind, c.file, c.qualname, "
            "       e.payload, e.frame_id, e.thread_id "
            "from events e left join code_objects c on c.id = e.code_id "
            f"where e.id in ({marks})", event_ids).fetchall()
    finally:
        con.close()
    return {r[0]: {"event": r[0], "line": r[1], "kind": r[2], "file": r[3],
                   "qualname": r[4], "payload": r[5], "frame_id": r[6],
                   "thread_id": r[7]} for r in rows}


def _trace_counts(paths, run_id: str) -> dict:
    """The reported-without-a-gate counts of the E6' trace, read directly."""
    db = paths["sensorium_dir"] / "traces" / f"{run_id}.db"
    if not db.is_file():
        return {"dropped": f"no trace file at {db}"}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        kinds = dict(con.execute("select kind, count(*) from events "
                                 "group by kind"))
        total = sum(kinds.values())
        frame_kinds = dict(con.execute(
            "select coalesce(kind, '<null>'), count(*) from frames "
            "group by coalesce(kind, '<null>')"))
        codes = con.execute("select count(*) from code_objects").fetchone()[0]
    finally:
        con.close()
    meta = trace_meta(paths, run_id)
    sites = meta.get("sites")
    site_kinds: dict = {}
    if isinstance(sites, list):
        for s in sites:
            k = (s or {}).get("kind", "?")
            site_kinds[k] = site_kinds.get(k, 0) + 1
    nbytes = trace_bytes(paths, run_id)
    return {
        "event_kinds": kinds, "events": total,
        "raise": kinds.get("RAISE", 0), "handled": kinds.get("HANDLED", 0),
        "frame_kinds": frame_kinds,
        "closure_frames": frame_kinds.get("closure", 0),
        "code_objects": codes,
        "partial_rows": len(meta.get("partial") or []),
        "site_kinds": site_kinds,
        "sites": len(sites) if isinstance(sites, list) else None,
        "meta_sites_bytes": len(json.dumps(sites)) if sites is not None else 0,
        "trace_bytes": nbytes,
        "bytes_per_record": round(nbytes / total, 3) if total else None,
        "incomplete": meta.get("incomplete"),
        "dropped": None,
    }


def phase_e6prime(paths, cfg) -> dict:
    """E6': `cargo sensorium test -p bloomery-daemon --lib` on the clone, then
    `sensorium exceptions <run> --limit 100000` captured WHOLE.

    The adjudication is not here: §4 of the acceptance document is written by
    hand against the clone's source. What this returns is every SWALLOWED
    line, parsed into the fields that table needs."""
    step("E6': one instrumented --lib run of the clone")
    res = run(driver_cmd(paths, *cfg["pkg"], "--lib"),
              paths["sensorium_bloomery_clone"], "e6prime-run.log",
              target_env(paths), timeout=cfg.get("e6prime_timeout", 7200))
    lines = run_lines(res)
    pick = max(lines, key=lambda r: r["events"]) if lines else None
    out = {"rc": res["rc"], "wall": round(res["wall"], 3),
           "processes": len(lines), "per_process": lines,
           "spool": spool_of(res), "log": res["log"],
           "run": pick["run"] if pick else None,
           "events": pick["events"] if pick else None,
           "threads": pick["threads"] if pick else None}
    if pick is None:
        out["dropped"] = "the invocation recorded no process"
        step("E6': DROPPED -- no trace recorded")
        return out
    step(f"E6': run={out['run']} events={out['events']}")
    cli = sensorium_cli(paths, ["exceptions", out["run"], "--limit", "100000"],
                        "e6prime-exceptions", timeout=cfg.get("cli_timeout", 3600))
    text = cli["out"] + cli["err"]
    printed = [ln.strip() for ln in cli["out"].splitlines() if SWALLOWED in ln]
    parsed = []
    for ln in printed:
        m = SWALLOW_LINE.search(ln)
        parsed.append({"line": ln,
                       "how": m.group("how") if m else None,
                       "event": int(m.group("event")) if m else None,
                       "qualname": m.group("qualname") if m else None,
                       "site_line": int(m.group("line")) if m else None,
                       "frame": m.group("frame") if m else None,
                       "unparsed": m is None})
    sinks = _sink_files(paths, out["run"],
                        [p["event"] for p in parsed if p["event"] is not None])
    for p in parsed:
        p["sink"] = sinks.get(p["event"])
    tallies = [ln for ln in cli["out"].splitlines() if ln.startswith(TALLY)]
    raised = re.search(r"^raised \((\d+)(?:[^)]*)\):", cli["out"], re.M)
    tally_counts = {}
    if tallies:
        for part in tallies[0][len(TALLY):].split(", "):
            bits = part.rsplit(" ", 1)
            if len(bits) == 2 and bits[1].isdigit():
                tally_counts[bits[0]] = int(bits[1])
    out.update({
        "exceptions_rc": cli["rc"], "exceptions_wall": round(cli["wall"], 3),
        "exceptions_log": cli["log"],
        "exceptions_stdout_bytes": len(cli["out"]),
        "exceptions_stdout": cli["out"],
        "swallowed_lines": printed, "swallowed_count": len(printed),
        "swallowed_parsed": parsed,
        "unparsed_swallowed": sum(1 for p in parsed if p["unparsed"]),
        "tally_line": tallies[0] if tallies else None,
        "tally": tally_counts,
        "chains_in_scope": int(raised.group(1)) if raised else None,
        "partial_line": next((ln for ln in cli["out"].splitlines()
                              if ln.startswith("partial: ")), None),
        "panics_line": next((ln for ln in cli["out"].splitlines()
                             if ln.startswith("panics: ")), None),
        "more_note": next((ln for ln in cli["out"].splitlines()
                           if ln.startswith("... ")), None),
        "counts": _trace_counts(paths, out["run"]),
        "text_len": len(text),
    })
    step(f"E6': {len(printed)} SWALLOWED line(s); tally {tally_counts}; "
         f"chains {out['chains_in_scope']}")
    return out


# ------------------------------------------------------------------ E0''

E0_KILL_S = 60.0


def phase_e0pp(paths, cfg, run_id: str | None) -> dict:
    """E0'': `info <run>` and `diff <run> <run>` on the E6' trace, wall-timed,
    with E0's 60 s kill ARMED -- a command that hits it is killed and reported
    as over the ceiling, never waited out."""
    if not run_id:
        return {"dropped": "E6' recorded no trace to read"}
    out = {"kill_s": E0_KILL_S, "run": run_id, "arms": {}}
    for label, args in (("info", ["info", run_id]),
                        ("diff", ["diff", run_id, run_id])):
        try:
            res = sensorium_cli(paths, args, f"e0pp-{label}", timeout=E0_KILL_S)
            out["arms"][label] = {
                "argv": args, "rc": res["rc"], "wall": round(res["wall"], 3),
                "killed": False, "under_ceiling": res["wall"] < E0_KILL_S,
                "verdict_line": verdict_line(res["out"]),
                "log": res["log"], "stdout_bytes": len(res["out"])}
        except subprocess.TimeoutExpired:
            out["arms"][label] = {
                "argv": args, "rc": None, "wall": None, "killed": True,
                "under_ceiling": False,
                "dropped": f"killed at the armed {E0_KILL_S:.0f} s ceiling"}
        a = out["arms"][label]
        step(f"E0'' {label}: {a.get('wall')}s killed={a['killed']}")
    return out


# ------------------------------------------------------------------ E2''


def phase_census_try(paths, cfg) -> dict:
    """The census binary's `try_syn` / `try_macro_tokens` columns, re-run over
    the clone and REPORTED.

    `acceptance_phases.phase_census` sums the rung-2 columns and drops these
    two, so this reads the same one-JSON-row-per-file output for them. It is
    NOT the denominator: §1 froze `try_syn` before the lock and the ratio is
    taken over that number. This exists so a reader can see whether the
    instrument still says the same thing, and a difference would be a finding
    about the census, not a moved denominator."""
    res = run([str(paths["sensorium_census_driver"]),
               str(paths["sensorium_bloomery_clone"])],
              paths["sensorium_bloomery_clone"], "census-try.log", plain_env())
    rows = []
    for line in res["out"].splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    try_syn = sum(r.get("try_syn", 0) for r in rows)
    try_macro = sum(r.get("try_macro_tokens", 0) for r in rows)
    step(f"census(try): files={len(rows)} try_syn={try_syn} "
         f"try_macro_tokens={try_macro} "
         f"(§1 froze {cfg['try_syn']} / {cfg['try_macro_tokens']})")
    return {"rc": res["rc"], "files": len(rows),
            "parsed": sum(1 for r in rows if r.get("parsed")),
            "try_syn": try_syn, "try_macro_tokens": try_macro,
            "frozen_try_syn": cfg["try_syn"],
            "frozen_try_macro_tokens": cfg["try_macro_tokens"],
            "agrees_with_the_frozen_denominator":
                try_syn == cfg["try_syn"] and try_macro == cfg["try_macro_tokens"],
            "try_by_file": {r["file"]: r.get("try_syn", 0) for r in rows
                            if r.get("try_syn")},
            "macro_by_file": {r["file"]: r.get("try_macro_tokens", 0)
                              for r in rows if r.get("try_macro_tokens")},
            "log": res["log"]}


def phase_e2pp(paths, cfg) -> dict:
    """E2'': the from-scratch workspace build whose manifests carry the
    numerator, counted as `kind: "try"` ROWS.

    The target directory is emptied first for the reason
    `acceptance_phases.phase_e2_workspace` states: cargo does not invoke the
    wrapper for a fingerprint-fresh unit, so only a build that compiles every
    unit leaves a complete manifest set (and a complete `-C metadata=` scope
    in its own `cargo -v` log)."""
    target = paths["sensorium_acceptance_target"]
    removed = sum(rmtree(child) for child in sorted(target.iterdir()))
    emptied_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    step(f"E2'': emptied the target ({removed} bytes) at {emptied_at}")
    res, b = _build(paths, cfg, [*cfg["workspace_sel"], "--no-run"],
                    "e2pp-workspace.log", True,
                    timeout=cfg.get("e2pp_timeout", 10800))
    if res["rc"] != 0:
        return {"dropped": f"the from-scratch workspace build exited {res['rc']}",
                "build": b, "target_emptied_bytes": removed,
                "target_emptied_at": emptied_at}
    m = read_manifests_rung3(paths, b["metadata_units"])
    rows = _try_rows(paths, b["metadata_units"])
    step(f"E2'': try rows {rows['try_rows_distinct']} distinct "
         f"({rows['try_rows_raw']} raw) over {len(m['units'])} units; "
         f"fell_back {len(m['fell_back'])}; partial {rows['partial_rows']}")
    return {"build": b, "manifests": m, "try": rows,
            "target_emptied_bytes": removed, "target_emptied_at": emptied_at,
            "fell_back_stderr_lines": [
                ln for ln in Path(b["log"]).read_text().splitlines()
                if "fell back to the real tree" in ln]}


def read_manifests_rung3(paths, scope: list[str] | None) -> dict:
    """`acceptance_lib.read_manifests`, made able to read a RUNG-3 manifest.

    The rung-2 reader keys a site on `(file, qualname, firstlineno)` and
    indexes `e["firstlineno"]` directly. Rung 3's `ManifestSite` serialises
    `firstlineno` only for a `kind: "fn"` row and carries `line` for the
    others (`manifest.rs`: `firstlineno: is_fn.then_some(..)`,
    `line: (!is_fn).then_some(..)`), so the rung-2 reader raises `KeyError`
    on the first `try`/`sink`/`arm` row it meets -- measured on the first
    launch of this run, 2026-09-05, on a workspace build whose manifests
    carried 2364 such rows.

    `acceptance_lib.py` is the rung-2 record's instrument and is left
    byte-unchanged; this is the rung-3 reader. `kind` joins the key, because
    a `fn` site and a `try` site can share a file and a line and are two
    different sites."""
    d = manifests_dir(paths)
    sites, sites_by_file, raw = set(), {}, 0
    units, fell, unreached, skipped = [], [], set(), []
    spawns_wrapped, spawns_declared = 0, []
    out_of_scope, declaring = [], set()
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        if scope is not None and p.stem not in scope:
            out_of_scope.append(p.stem)
            continue
        m = json.loads(p.read_text())
        units.append({"unit": m["unit"], "crate_name": m["crate_name"],
                      "crate_type": m["crate_type"],
                      "fell_back": m["fell_back"],
                      "fallback_reason": m.get("fallback_reason"),
                      "files": len(m["files"]),
                      "sites": sum(len(v) for v in m["files"].values()),
                      "partial": len(m.get("partial", [])),
                      "unreached_files": m.get("unreached_files", []),
                      "workspace_root": m.get("workspace_root", ""),
                      "source_hashes": len(m.get("source_hashes", {})),
                      "skipped": len(m.get("skipped", []))})
        declaring.add((m["crate_name"], m["crate_type"]))
        unreached |= set(m.get("unreached_files", []))
        skipped += m.get("skipped", [])
        for s in m.get("spawns", []):
            if s.get("wrapped"):
                spawns_wrapped += 1
            else:
                spawns_declared.append(s)
        if m["fell_back"]:
            fell.append({"unit": m["unit"], "reason": m.get("fallback_reason")})
            continue
        for rel, entries in m["files"].items():
            raw += len(entries)
            for e in entries:
                # `firstlineno` for a fn row, `line` for every other kind:
                # exactly one of the two is serialised.
                where = e.get("firstlineno", e.get("line"))
                sites.add((rel, e["qualname"], where, e.get("kind", "fn")))
                sites_by_file.setdefault(rel, set()).add(
                    (e["qualname"], where, e.get("kind", "fn")))
    return {"distinct": len(sites),
            "sites_by_file": {k: len(v) for k, v in sites_by_file.items()},
            "raw_site_total": raw, "units": units, "fell_back": fell,
            "unreached_files": sorted(unreached), "skipped": skipped,
            "spawns_wrapped": spawns_wrapped,
            "spawns_declared": spawns_declared,
            "out_of_scope_manifests": sorted(out_of_scope),
            "declaring_pairs": sorted(declaring)}


def _try_rows(paths, scope: list[str]) -> dict:
    """`kind: "try"` manifest rows, and the `partial` rows beside them.

    DISTINCT by `(file, line)` as well as raw: two `(crate_name, crate_type)`
    pairs declare two manifests for one unit, so a raw sum double-counts the
    same source `?`. The ratio §1 gates is over the source's `?` sites, so
    the distinct count is the numerator and the raw sum is reported beside
    it."""
    d = manifests_dir(paths)
    distinct, raw, per_file = set(), 0, {}
    partial_rows, partial_by_file, partial_kinds = [], {}, {}
    kinds: dict = {}
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        if scope is not None and p.stem not in scope:
            continue
        m = json.loads(p.read_text())
        if m["fell_back"]:
            continue
        for rel, entries in m["files"].items():
            for e in entries:
                k = e.get("kind", "fn")
                kinds[k] = kinds.get(k, 0) + 1
                if k != "try":
                    continue
                raw += 1
                line = e.get("line", e.get("firstlineno"))
                if (rel, line) not in distinct:
                    per_file[rel] = per_file.get(rel, 0) + 1
                distinct.add((rel, line))
        for row in m.get("partial", []):
            key = (row.get("file"), row.get("line"), row.get("kind"),
                   row.get("reason"))
            if key in {(r.get("file"), r.get("line"), r.get("kind"),
                        r.get("reason")) for r in partial_rows}:
                continue
            partial_rows.append(row)
            partial_by_file[row.get("file")] = \
                partial_by_file.get(row.get("file"), 0) + 1
            partial_kinds[row.get("reason")] = \
                partial_kinds.get(row.get("reason"), 0) + 1
    return {"try_rows_distinct": len(distinct), "try_rows_raw": raw,
            "try_rows_by_file": per_file, "site_kinds_raw": kinds,
            "partial_rows": len(partial_rows),
            "partial_by_file": partial_by_file,
            "partial_reasons": partial_kinds,
            "partial_detail": partial_rows}


# ------------------------------------------------------------------ E7''

#: The wrap prefix `crate::splice::ERR_OPEN`, and therefore §1's predicted
#: column shift for a panic inside a `?` operand. Written here as the number
#: §1 pre-registered, not read from the source at run time: a check that
#: derives its own prediction from the thing under test predicts nothing.
E7_PREDICTED_SHIFT = 6

PANIC_AT = re.compile(r"panicked at ([A-Za-z0-9_./-]+\.rs):(\d+):(\d+)")


def phase_e7pp(paths, cfg) -> dict:
    """E7'': `rust/tests/mechanics.sh`, whose E7 section now carries BOTH the
    unchanged checks on the probe's existing panics and the new
    `?`-operand-panic check with its pre-registered +6 column.

    `acceptance_phases.phase_e7a` is not reused: it reads `ok:`/`FAIL:` lines
    generically, and E7'' needs the operand check's three numbers (plain
    location, instrumented location, the shift) out of the same run."""
    from acceptance_phases import phase_e7a                        # noqa: PLC0415
    out = phase_e7a(paths)
    body = Path(out["log"]).read_text()
    obs = {}
    for key in ("plain", "off", "call"):
        m = re.search(rf"^\s*\[E7-operand\] {key}: (\S+):(\d+):(\d+)$",
                      body, re.M)
        obs[key] = ({"file": m.group(1), "line": int(m.group(2)),
                     "col": int(m.group(3))} if m else None)
    shift = None
    if obs["plain"] and obs["call"]:
        shift = obs["call"]["col"] - obs["plain"]["col"]
    out["operand"] = {
        "predicted_shift": E7_PREDICTED_SHIFT,
        "locations": obs,
        "column_shift_call": shift,
        "column_shift_off": (obs["off"]["col"] - obs["plain"]["col"]
                             if obs["off"] and obs["plain"] else None),
        "line_identical": (bool(obs["plain"]) and bool(obs["call"])
                           and obs["plain"]["line"] == obs["call"]["line"]),
        "checks": [c for c in out["ok"] + out["fail"]
                   if c.startswith("e7_operand")],
        "dropped": [] if (obs["plain"] and obs["call"]) else
        ["the mechanics log carries no `[E7-operand]` location for "
         + ", ".join(k for k, v in obs.items() if v is None)],
    }
    step(f"E7'': operand plain={obs['plain']} call={obs['call']} "
         f"shift={shift} (predicted {E7_PREDICTED_SHIFT})")
    return out
