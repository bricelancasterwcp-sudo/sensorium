#!/usr/bin/env python3
"""The E6⁗ runner: E6⁗-A, E6⁗-WS, E6⁗-WS0, E-flip, E6-again′, E7⁗ and E0‴,
in the order `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`
§1 pre-registers them.

A SIBLING of `acceptance_e6ppp.py`, not a fork of it. Everything §1 calls
"verbatim" is a COMMITTED function, CALLED: `acceptance_phases_rung3.
phase_e6prime` is all three arms (it gained an explicit selector `tail` so an
arm can be `--workspace` with no `--lib`; the E6‴ runner keeps the default),
`phase_e6` is E6-again′, `phase_e7pp` is E7⁗, `phase_e0pp` is E0‴;
`acceptance_e6ppp`'s driver build, prep build, manifest arm reader, sweep and
executed-arm reader are imported; `acceptance_rung3`'s byte-lock, preflight
and cleanup are re-used with THIS document's own lock. A second copy of a
protocol is a second protocol, so nothing here re-implements one.

What is NEW:

* **the third arm.** E6⁗-WS0 is E6⁗-WS's command under the driver built from
  the PRE-repair commit, into its OWN target (which its own prep build
  empties) and its OWN trace store. It is the discrimination control of
  design B5: an endpoint that cannot be shown able to fail can license the
  mistake it was written to prevent. It gates nothing.
* **the flip diff.** Two from-scratch `--workspace --no-run` builds -- base
  driver into the control target, HEAD driver into the acceptance target --
  and a diff of their `kind: "arm"` manifest rows keyed `(file, line)`, with
  the `how` each writes. This is the "different sets" question rung 3 left
  open, answered by taking the manifest diff rather than comparing two
  census totals.
* **the control's computed evidence.** `lines_at_flipped_sites` counts the
  control arm's SWALLOWED lines whose sink lands at a site the flip diff
  lists. It is EVIDENCE for §4's hand adjudication and never its verdict:
  §1's WS0 endpoint is "≥ 1 FALSE accusation at a flip-set arm", and false
  is a reading of the clone's source, not a count.
* **the base driver's identity.** `cargo-sensorium` has no `--version` flag
  (measured at Task 0), so the control driver is identified by its worktree's
  HEAD plus the binary's sha256 -- the binary is never invoked to ask what it
  is. What the driver says about ITSELF is read AFTER the run out of the
  trace each arm wrote (`meta.driver_version`), so the record can show
  `cargo-sensorium 0.3.0` for WS0 beside the repaired version for A and WS.

Every location is an environment variable; no box path appears in this file.
The three the control adds (`SENSORIUM_BASE_DRIVER`,
`SENSORIUM_BASE_WORKTREE`, `SENSORIUM_CONTROL_TARGET`) are refused TOGETHER
when missing, as `acceptance_lib.env_paths` refuses its own.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_e6q.py \
        > <ledger>/acceptance-e6q/logs/e6q.log 2>&1 &

The last act is `<ledger>/acceptance-e6q/e6q.DONE` (or `.FAILED`) carrying
`exit=<n>`, so silence is distinguishable from success.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-05-sensorium-rung3-borrow-repair"
LEDGER = PLAN
BASE = PLAN / "acceptance-e6q"
LOGS = BASE / "logs"

# Every earlier ledger is evidence and is not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_phases_rung3 as r3                               # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_e6ppp import (LOADS, arm_rows, build_driver,       # noqa: E402,F401
                              executed_arms, logs_at, mark_load,
                              phase_prep_build, sweep_other_runs)
from acceptance_lib import (Refused, driver_cmd, free_gb,          # noqa: E402,F401
                            plain_env, run, sha256_file, step)

# Re-asserted AFTER the imports above, and not only before them. Importing
# `acceptance_rung3` points `acceptance_lib.LEDGER`/`LOGS` at the RUNG-3
# slice's workspace, and importing `acceptance_e6ppp` points them at the E6‴
# document's; without this second assignment every log written outside a
# `logs_at` block would land beside another record (measured on the
# 2026-09-05 E6‴ run, §2 of that document). `e6ppp.LOGS` and `e6ppp.BASE` are
# module globals that `build_driver` and `phase_prep_build` resolve in THEIR
# namespace, so they move too.
lib.LEDGER = LEDGER
lib.LOGS = LOGS
ph.LOGS = LOGS
e6ppp.LOGS = LOGS
e6ppp.BASE = BASE

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-05-sensorium-rung3-e6q.md")

#: The commit that committed §1 ALONE, before any E6⁗ number was read. `None`
#: until that commit exists, and a `None` lock REFUSES rather than measuring
#: against a pre-registration that can still be edited.
BYTE_LOCK = "559e617"
#: §1 of this document is committed once and never amended, so there is no
#: second sha to carry. E6‴'s §1 was amended (dated, pre-measurement) and its
#: record carries both; a `None` here says this one was not.
ORIGINAL_LOCK = None

#: The pre-repair `main` the control driver is built from (design B4/B5).
BASE_COMMIT = "d1b1b57"

#: The three arms of design B4. `selector` and `tail` are what
#: `phase_e6prime` puts after `cargo sensorium test`; `driver` says which
#: binary and which target the arm runs under.
ARM_A = {"label": "a", "selector": ["-p", "bloomery-daemon"],
         "tail": ["--lib"], "driver": "head"}
ARM_WS = {"label": "ws", "selector": ["--workspace"], "tail": [],
          "driver": "head"}
ARM_WS0 = {"label": "ws0", "selector": ["--workspace"], "tail": [],
           "driver": "base"}
ARMS = [ARM_A, ARM_WS, ARM_WS0]

#: The two rows §1 predicts by name: the clone's `map_error(&e, ..)` arms,
#: which must read `arm_handled` BEFORE and `arm_ambiguous` AFTER. Named here
#: so a build that never declared them is reported as MISSING rather than
#: assumed flipped.
NAMED_ROWS = ["crates/bloomery-daemon/src/api_v1.rs:396",
              "crates/bloomery-daemon/src/api_v1.rs:515"]

#: The transition §1's E-flip gate allows, spelled as the diff keys it.
HANDLED, AMBIGUOUS = "arm_handled", "arm_ambiguous"
ALLOWED_TRANSITION = f"{HANDLED}->{AMBIGUOUS}"

#: §1's frozen census: the FIVE numbers §1 freezes, measured by Tasks 0 and 1
#: on the clone across the repair, read BEFORE the lock and repeated here as
#: the pins the record cites rather than re-derives. The E-flip gate's delta
#: is `arms_handled_before - arms_handled_after` = 11.
FROZEN_CENSUS = {"arms_handled_before": 65, "arms_handled_after": 54,
                 "arms_escaped_before": 121, "arms_escaped_after": 132,
                 "arm_sites": 225, "source": "§1"}

#: A census number the T0/T1 runs also read, which §1 does NOT freeze. It is
#: published beside the frozen five and never under their label: a number
#: stamped "§1" that §1 does not carry would give a ledger line the standing
#: of a pre-registered pin.
LEDGER_CENSUS = {"arms_propagate": 39,
                 "source": "T0/T1 ledger census lines (unchanged across the "
                           "repair); NOT frozen in §1"}

#: The three locations the control arm adds, and the `paths` keys they land
#: under. Missing ones are refused together.
CONTROL_ENV = {"SENSORIUM_BASE_DRIVER": "sensorium_base_driver",
               "SENSORIUM_BASE_WORKTREE": "sensorium_base_worktree",
               "SENSORIUM_CONTROL_TARGET": "sensorium_control_target"}


# ------------------------------------------------------------ lock and paths


def check_byte_lock() -> dict:
    """§1, as committed, versus the working tree -- or a refusal to start.

    The endpoint is decided before the instrument exists; this is the check
    that it did not move afterwards. An unset `BYTE_LOCK` is not "nothing to
    compare with": it is a runner asked to measure against a pre-registration
    that is still editable, and it refuses."""
    if not BYTE_LOCK:
        raise Refused(
            "§1 of the acceptance document is not locked yet: BYTE_LOCK is "
            "None. Commit §1 ALONE, then set BYTE_LOCK to that commit's sha.")
    return rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)


def env_paths_e6q() -> dict:
    """`acceptance_lib.env_paths` plus the control arm's three locations."""
    paths = lib.env_paths(False)
    missing = [k for k in CONTROL_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(
            "unset environment variable(s): " + ", ".join(missing)
            + " -- the control arm needs its own driver, the worktree that "
              "driver was built from, and its own target directory")
    for k, name in CONTROL_ENV.items():
        paths[name] = Path(os.environ[k])
    return paths


def _git_out(worktree, *args) -> str:
    return subprocess.run(["git", "-C", str(worktree), *args],
                          capture_output=True, text=True).stdout


def verify_base_driver(paths, git=_git_out) -> dict:
    """The control driver's identity, WITHOUT invoking it.

    `cargo-sensorium` has no `--version` flag at any commit in its history
    (Task 0), so the identity is: the worktree it was built from is at
    `BASE_COMMIT` and clean, and the binary's sha256 and mtime. What the
    driver reports about ITSELF is read after the run, from the trace it
    wrote (`driver_identity`) -- a string the run produced rather than one
    the operator typed.

    The control's target directory is checked here too, because it is the
    other half of the same substitution: a control that ran into the
    acceptance target would run test binaries the HEAD driver compiled."""
    wt = Path(paths["sensorium_base_worktree"])
    driver = Path(paths["sensorium_base_driver"])
    target = Path(paths["sensorium_control_target"])
    if not driver.is_file():
        raise Refused(f"no base driver at {driver}")
    if not target.is_dir():
        raise Refused(f"no control target directory at {target}")
    head = git(wt, "rev-parse", "HEAD").strip()
    porcelain = git(wt, "status", "--porcelain")
    rec = {
        "worktree": str(wt), "expected_commit": BASE_COMMIT,
        "head": head, "head_matches": head.startswith(BASE_COMMIT),
        "porcelain": porcelain, "clean": not porcelain.strip(),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "driver_mtime": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime(driver.stat().st_mtime)),
        "control_target": str(target),
        "version_read": ("after the run, from each arm's own trace "
                         "(`meta.driver_version`): `cargo-sensorium` has no "
                         "`--version` flag and is never invoked to identify "
                         "itself"),
    }
    if not rec["head_matches"]:
        raise Refused(f"the base worktree {wt} is at {head or '?'}, not "
                      f"{BASE_COMMIT}: the control would measure another "
                      f"driver than the pre-repair one")
    if not rec["clean"]:
        raise Refused(f"the base worktree {wt} is not clean:\n{porcelain}")
    step(f"base driver: worktree at {head[:12]} clean; "
         f"sha256 {(rec['driver_sha256'] or '?')[:12]}")
    return rec


def arm_paths_for(paths, arm) -> dict:
    """One arm's locations: its own trace directory always, and for the
    control arm its own driver and its own target."""
    p = e6ppp.arm_paths(paths, arm["label"])
    if arm["driver"] == "base":
        p["sensorium_driver"] = paths["sensorium_base_driver"]
        p["sensorium_acceptance_target"] = paths["sensorium_control_target"]
    return p


def e6q_config(paths) -> dict:
    cfg = dict(rung3.rung3_config(paths))
    cfg.update({
        "e6_workdir": LOGS / "e6-cases",
        "arms": {a["label"]: a for a in ARMS},
        "frozen_census": FROZEN_CENSUS,
        "ledger_census": LEDGER_CENSUS,
        "base_commit": BASE_COMMIT,
        "named_rows": list(NAMED_ROWS),
    })
    return cfg


# ------------------------------------------------------- what a driver says


def driver_identity(paths, run_ids) -> dict:
    """What the driver reported about ITSELF into each trace of one arm.

    `meta.driver_version` is written by the converter from the driver's own
    `DRIVER_VERSION` constant, so it is the run's evidence of which binary
    instrumented it -- the control arm's traces must say `cargo-sensorium
    0.3.0` and the HEAD arms' the repaired version. A missing trace is a hole
    in the evidence and is reported, never defaulted."""
    per_run, hashes, missing = {}, {}, []
    for run_id in run_ids:
        meta = lib.trace_meta(paths, run_id)
        if not meta:
            missing.append(run_id)
            continue
        per_run[run_id] = meta.get("driver_version")
        hashes[run_id] = meta.get("tool_hash")
    return {"driver_version_per_run": per_run,
            "driver_versions": sorted({v for v in per_run.values() if v}),
            "tool_hash_per_run": hashes,
            "tool_hashes": sorted({h for h in hashes.values() if h}),
            "traces_missing": missing}


# ----------------------------------------------------------------- the arms


def phase_arm(paths, cfg, arm) -> dict:
    """One E6⁗ arm: §1's protocol (the committed `phase_e6prime`, with this
    arm's selector tail), then the sweep over every other process the arm
    recorded, then the arm's executed arm sites and the driver identity its
    own traces carry."""
    label = arm["label"]
    mark_load(f"E6⁗-{label.upper()}")
    ap = arm_paths_for(paths, arm)
    acfg = dict(cfg) | {"pkg": list(arm["selector"])}
    tail = tuple(arm["tail"])
    step(f"E6⁗-{label.upper()}: "
         f"{' '.join(str(c) for c in driver_cmd(ap, *acfg['pkg'], *tail))}")
    with logs_at(LOGS / f"arm-{label}"):
        out = r3.phase_e6prime(ap, acfg, tail=tail)
        out.update({
            "arm": label, "selector": list(arm["selector"]),
            "tail": list(tail), "driver_role": arm["driver"],
            "driver": str(ap["sensorium_driver"]),
            "driver_sha256": sha256_file(ap["sensorium_driver"]),
            "target": str(ap["sensorium_acceptance_target"]),
            "sensorium_dir": str(ap["sensorium_dir"]),
        })
        if out.get("dropped"):
            return out
        out["sweep"] = sweep_other_runs(
            ap, acfg, out.get("run"), out.get("per_process") or [], label)
    runs = [r["run"] for r in (out.get("per_process") or [])]
    out["executed_arms"] = executed_arms(ap, runs)
    out["driver_identity"] = driver_identity(ap, runs)
    out["union_swallowed_count"] = (out["swallowed_count"]
                                    + out["sweep"]["swallowed_count"])
    out["union_swallowed_parsed"] = (list(out.get("swallowed_parsed") or [])
                                     + list(out["sweep"].get(
                                         "swallowed_parsed") or []))
    step(f"E6⁗-{label.upper()}: primary {out['swallowed_count']} + sweep "
         f"{out['sweep']['swallowed_count']} = {out['union_swallowed_count']} "
         f"SWALLOWED line(s) over {out['processes']} process(es)")
    return out


# ------------------------------------------------------------ the flip diff


def _by_site(build: dict, side: str) -> tuple[dict, list]:
    """One build's arm rows keyed `(file, line)`, with the single `how` each
    writes. A row that carries more than one `how` (two units declaring the
    same source line, disagreeing) has no single class and is reported under
    `multi_how` rather than folded into a transition."""
    rows, multi = {}, []
    for r in build.get("rows") or []:
        hows = r.get("hows") or []
        key = (r.get("file"), r.get("line"))
        if len(hows) != 1:
            multi.append({"file": r.get("file"), "line": r.get("line"),
                          "side": side, "hows": list(hows)})
            continue
        rows[key] = {"file": r.get("file"), "line": r.get("line"),
                     "qualname": r.get("qualname"), "how": hows[0]}
    return rows, multi


def flip_diff(before: dict, after: dict, named=NAMED_ROWS) -> dict:
    """The BEFORE/AFTER `kind: "arm"` manifest diff §1's E-flip endpoint asks
    for: which arms the repair moved, exactly.

    Keyed `(file, line)`, which is the identity a source arm has in both
    builds. A row present in one build only is REPORTED (`only_before` /
    `only_after`) rather than counted as a transition -- it is evidence about
    the builds, not about the rule.

    `only_handled_to_ambiguous` is True only when there is at least one
    transition AND every one of them is `arm_handled -> arm_ambiguous`. Over
    an empty transition set the claim is vacuously true and would read as
    "the predicted flip happened", so an empty diff is not a pass here."""
    b, mb = _by_site(before, "before")
    a, ma = _by_site(after, "after")
    changed, transitions = [], {}
    for key in sorted(set(b) & set(a)):
        bh, ah = b[key]["how"], a[key]["how"]
        if bh == ah:
            continue
        changed.append({"file": key[0], "line": key[1],
                        "qualname": a[key]["qualname"] or b[key]["qualname"],
                        "before": bh, "after": ah})
        t = f"{bh}->{ah}"
        transitions[t] = transitions.get(t, 0) + 1
    only_before = [{"file": b[k]["file"], "line": b[k]["line"],
                    "how": b[k]["how"]} for k in sorted(set(b) - set(a))]
    only_after = [{"file": a[k]["file"], "line": a[k]["line"],
                   "how": a[k]["how"]} for k in sorted(set(a) - set(b))]
    rows = {}
    for name in named:
        file, _, line = name.rpartition(":")
        key = (file, int(line))
        bh = (b.get(key) or {}).get("how")
        ah = (a.get(key) or {}).get("how")
        flipped = (None if bh is None or ah is None
                   else (bh == HANDLED and ah == AMBIGUOUS))
        rows[name] = {"before": bh, "after": ah, "flipped": flipped}
    return {
        "changed": changed, "changed_count": len(changed),
        "transitions": transitions,
        "only_handled_to_ambiguous": (bool(transitions)
                                      and set(transitions) == {
                                          ALLOWED_TRANSITION}),
        "only_before": only_before, "only_after": only_after,
        "only_before_count": len(only_before),
        "only_after_count": len(only_after),
        "named": rows,
        "named_all_flipped": bool(rows) and all(
            v["flipped"] is True for v in rows.values()),
        "multi_how": mb + ma,
        "sites_before": len(b), "sites_after": len(a),
    }


def flip_resolved(flip: dict) -> dict:
    """The flip set in the shape `acceptance_e6ppp.executed_vs_static` reads,
    so §1's "which of the flipped arms EXECUTED" is answered by the COMMITTED
    join (absolute trace paths against workspace-relative manifest paths)
    rather than by a second one written here."""
    rows = [{"suffix": r["file"].rsplit("/", 1)[-1], "line": r["line"],
             "file": r["file"], "qualname": r.get("qualname"),
             "hows": [r.get("after")], "ambiguous": False}
            for r in flip.get("changed") or []]
    return {"resolved": rows, "resolved_count": len(rows),
            "static_entries_located": len(rows),
            "static_entries_total": len(rows),
            "static_entries_unlocated": 0, "unlocated": [],
            "unmatched": [], "ambiguous": []}


def _sink_site(sink, root: str):
    """One SWALLOWED line's sink as `(workspace-relative file, line)`.

    The collector attaches the sink as a DICT (`_sink_files`); the same field
    is a `"<file>:<line>"` string wherever a caller carries it flattened.
    Both are read, and a sink that is neither -- or that is missing -- is
    UNRESOLVED, which is a different fact from "not at a flipped site"."""
    if isinstance(sink, dict):
        file, line = sink.get("file"), sink.get("line")
    elif isinstance(sink, str):
        file, _, num = sink.rpartition(":")
        line = int(num) if num.isdigit() else None
    else:
        return None, False
    if not file or line is None:
        return None, False
    under = file.startswith(root)
    return (file[len(root):] if under else file, line), under


def lines_at_flipped_sites(parsed: list, flip: dict, clone_root: str) -> dict:
    """Of one arm's SWALLOWED lines, those that land at a site E-flip lists.

    COMPUTED EVIDENCE for §4's hand adjudication of the control (design B5),
    and never its verdict: §1's WS0 endpoint is "≥ 1 FALSE accusation at a
    flip-set arm", and whether an accusation is false is a reading of the
    clone's source. A count here is a count of lines to READ, and the schema
    publishes it beside a `null` verdict."""
    root = clone_root.rstrip("/") + "/"
    want = {(r.get("file"), r.get("line")) for r in flip.get("changed") or []}
    lines, unresolved, outside = [], 0, 0
    for p in parsed:
        site, under = _sink_site(p.get("sink"), root)
        if site is None:
            unresolved += 1
            continue
        if not under:
            outside += 1
            unresolved += 1
            continue
        if site in want:
            lines.append({"file": site[0], "line": site[1],
                          "how": p.get("how"), "run": p.get("run"),
                          "swallowed_line": p.get("line")})
    return {"count": len(lines), "lines": lines, "unresolved": unresolved,
            "not_under_the_clone_root": outside,
            "flip_sites": len(want), "read": len(parsed),
            "clone_root": clone_root}


# -------------------------------------------------------------------- main


def _prep(paths, cfg, label: str, arm=None) -> dict:
    """One from-scratch `--workspace --no-run` build, in its own log
    directory. PREP, never an endpoint: it empties its target so every unit
    is compiled by THAT build's driver and the manifest set is complete.

    `e6ppp.LOGS` is bound to this prep's directory for the duration, and not
    only `lib.LOGS`/`ph.LOGS` through `logs_at`: `phase_prep_build` opens its
    OWN `logs_at(LOGS / "prep")` block, and that `LOGS` resolves in
    `acceptance_e6ppp`'s namespace (that is the phase owning where it logs --
    the E6‴ §2 lesson). With the module global left at this document's root
    BOTH preps would write `prep/prep-workspace.log`, the BASE prep would
    destroy the HEAD prep's `cargo -v` log, and the record would publish one
    file under two names."""
    p = paths if arm is None else arm_paths_for(paths, arm)
    here = LOGS / f"prep-{label}"
    step(f"prep ({label}): from-scratch --workspace --no-run into "
         f"{p['sensorium_acceptance_target']}")
    saved = e6ppp.LOGS
    try:
        e6ppp.LOGS = here
        with logs_at(here):
            out = phase_prep_build(p, cfg)
    finally:
        e6ppp.LOGS = saved
    out["driver"] = str(p["sensorium_driver"])
    out["driver_sha256"] = sha256_file(p["sensorium_driver"])
    out["target"] = str(p["sensorium_acceptance_target"])
    out["label"] = label
    return out


def main(argv) -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("e6q.DONE", "e6q.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": "rust/tests/acceptance_e6q.py",
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS),
                 "frozen_census": FROZEN_CENSUS,
                 "ledger_census": LEDGER_CENSUS}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = check_byte_lock()
        paths = env_paths_e6q()
        cfg = e6q_config(paths)
        res["config"] = {k: str(v) if isinstance(v, Path) else v
                         for k, v in cfg.items()}
        res["raw_base_driver"] = verify_base_driver(paths)
        res["raw_built_from"] = build_driver(paths)
        pins = rung3.preflight(paths, cfg)
        res["pins"] = pins

        res["raw_prep_head"] = _prep(paths, cfg, "head")
        res["raw_prep_base"] = _prep(paths, cfg, "base", ARM_WS0)
        arms_after = (res["raw_prep_head"] or {}).get("arms") or {}
        arms_before = (res["raw_prep_base"] or {}).get("arms") or {}
        res["raw_flip"] = flip_diff(arms_before, arms_after)
        step(f"E-flip: {res['raw_flip']['changed_count']} changed row(s); "
             f"transitions {res['raw_flip']['transitions']}; named "
             f"{ {k: v['flipped'] for k, v in res['raw_flip']['named'].items()} }")

        for arm in ARMS:
            res[f"raw_arm_{arm['label']}"] = phase_arm(paths, cfg, arm)

        clone = str(paths["sensorium_bloomery_clone"])
        res["raw_flip_lines"] = {
            label: lines_at_flipped_sites(
                (res.get(f"raw_arm_{label}") or {}).get(
                    "union_swallowed_parsed") or [],
                res["raw_flip"], clone)
            for label in ("ws", "ws0")}
        res["raw_executed_flipped"] = {
            arm["label"]: e6ppp.executed_vs_static(
                flip_resolved(res["raw_flip"]),
                (res.get(f"raw_arm_{arm['label']}") or {}).get(
                    "executed_arms") or {},
                clone)
            for arm in ARMS}
        step("flip set: executed "
             + ", ".join(f"{k} {v.get('executed')}/{v.get('static')}"
                         for k, v in res["raw_executed_flipped"].items())
             + f"; control lines at flipped sites "
               f"{res['raw_flip_lines']['ws0']['count']} "
               f"(WS {res['raw_flip_lines']['ws']['count']})")

        with logs_at(LOGS / "e6-again"):
            mark_load("E6-again′")
            step("E6-again′: the Rust corpus cases with an `exceptions` "
                 "question")
            res["raw_e6"] = r3.phase_e6(paths, cfg)

        with logs_at(LOGS / "e7q"):
            mark_load("E7⁗")
            step("E7⁗: mechanics.sh, lines and columns")
            res["raw_e7pp"] = r3.phase_e7pp(paths, cfg)

        with logs_at(LOGS / "e0ppp"):
            mark_load("E0‴")
            step("E0‴: info and diff on the WS arm's largest process, 60 s "
                 "kill armed")
            res["raw_e0ppp"] = r3.phase_e0pp(
                arm_paths_for(paths, ARM_WS), cfg,
                (res.get("raw_arm_ws") or {}).get("run"))

        res["arm_loads"] = list(LOADS)
        res["cleanup"] = rung3.cleanup(paths, cfg, pins)
    except Refused as e:
        step(f"REFUSED: {e}")
        res["refused"] = str(e)
        rc = 3
    except Exception:                                          # noqa: BLE001
        import traceback
        step("ERROR: " + traceback.format_exc().strip().splitlines()[-1])
        res["error"] = traceback.format_exc()
        rc = 4
    if paths and cfg and res.get("cleanup") is None and pins is not None:
        try:
            res["cleanup_after_failure"] = rung3.cleanup(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-e6q-raw.json").write_text(
        json.dumps(res, indent=2, default=str))
    try:
        assemble_only(res)
    except Exception:                                          # noqa: BLE001
        import traceback
        (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
        step("assemble FAILED (logs/assemble-error.txt); the raw record is "
             "intact")
        rc = rc or 5
    (BASE / ("e6q.DONE" if rc == 0 else "e6q.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw E6⁗ facts at "
         f"{LEDGER / 'results-e6q-raw.json'}")
    return rc


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no arm and reads
    no new number."""
    from acceptance_schema_e6q import assemble_e6q                  # noqa: PLC0415
    if raw is None:
        raw = json.loads((LEDGER / "results-e6q-raw.json").read_text())
    doc = assemble_e6q(raw)
    doc["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": "results-e6q-raw.json",
        "by": "rust/tests/acceptance_e6q.py --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no arm was re-run and no value "
                 "re-measured"),
    }
    dest = (REPO / "docs" / "superpowers" / "acceptance"
            / "2026-09-05-sensorium-rung3-e6q.results.json")
    dest.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    print(f"assembled {dest} from results-e6q-raw.json")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only())
    raise SystemExit(main(sys.argv[1:]))
