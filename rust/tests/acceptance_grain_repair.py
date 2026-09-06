#!/usr/bin/env python3
"""The rung-4 grain REPAIR runner: the same H1-H6 protocol, on the repaired
reader, against `docs/superpowers/acceptance/
2026-09-05-sensorium-rung4-entry-grain-repair.md` §1.

WHY THERE IS A SECOND RUNNER AND NOT A SECOND RUN OF THE FIRST
--------------------------------------------------------------
The 2026-09-05 record read H4 **STOP**: the shape key's site was the printed
`qualname L<line>` with no file in it, and the workspace's two `sandbox`
helpers at L42 (and two `fresh_dir`s at L64) merged across processes. That
record stands as written and is never re-rolled. Ruling R-G12 repaired the
key; the repair is measured under a NEW pre-registration, which needs its own
byte-locked §1, its own ledger, its own markers and its own `results.json` --
and MUST NOT be able to overwrite the first record's.

Everything else is the first runner's, by reference and not by copy: the
oracle, the kept stores, the preflight, the five phases, the site
comparison, the schema and the renderer are `acceptance_grain`'s own objects,
imported here and called. `tests/test_acceptance_grain_repair.py` asserts
that -- every shared name is the SAME OBJECT, and the ones that differ are
exactly the list in `OVERRIDES` below.

WHAT COULD NOT BE SHARED, AND WHY
---------------------------------
`main`, `assemble_only`, `render_only` and `check_byte_lock` are written
again here. Not by preference: `acceptance_grain.main` spells its marker
names, its raw record's file name and the runner it names in that record as
LITERALS in its body, and those four values are exactly what this run must
not share. Rebinding the first runner's module globals from an import
instead would repoint a live module for every other importer in the process
-- the hazard `tests/test_acceptance_grain.py` already documents about the
shared `LOGS` pointers -- so the orchestration is restated and every phase
inside it is delegated. The phase ORDER below is the first runner's, line for
line, because a repair measured in a different order is not the same
measurement.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_grain_repair.py \
        > <ledger>/acceptance-grain-repair/logs/grain-repair.log 2>&1 &

The last act is `<ledger>/acceptance-grain-repair/grain-repair.DONE` (or
`.FAILED`) carrying `exit=<n>`, so silence is distinguishable from success.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_grain as grain                                   # noqa: E402
import acceptance_grain_phases as gph                              # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
# The first runner's own names, re-exported so a reader (and every test) can
# reach `acceptance_grain_repair.<name>` for anything this run shares. They
# are the SAME objects, never copies.
from acceptance_grain import (ARMS, DRIVER_VERSION, GRAIN_ENV,      # noqa: E402,F401
                              KILL_S, LEDGER, ORACLE, ORACLE_COMMIT,
                              ORIGINAL_LOCK, PLAN, REPO, cleanup_grain,
                              env_paths_grain, oracle, oracle_json, phase_h1,
                              phase_h2, phase_h3, phase_h4, phase_h6,
                              preflight_grain, reported)
from acceptance_lib import Refused, step                           # noqa: E402

#: This run's ledger workspace. A SIBLING of `acceptance-grain/`, so nothing
#: this run writes can land on the first record's evidence.
BASE = PLAN / "acceptance-grain-repair"
LOGS = BASE / "logs"

# Importing `acceptance_grain` above pointed the three shared log pointers at
# the FIRST record's workspace (its job, and correct for it). They are
# re-pointed here for the same reason it re-points them after its own
# imports: every log written outside a `logs_at` block would otherwise land
# beside another record. `main` re-asserts them once more, because whichever
# of the two runners was imported LAST owns these names, and this one must
# own them while it runs.
lib.LEDGER = LEDGER
lib.LOGS = LOGS
ph.LOGS = LOGS
gph.LOGS = LOGS

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-05-sensorium-rung4-entry-grain-repair.md")

#: The commit that committed THIS document's §1 ALONE, before any number
#: below was read. `None` until that commit exists, and a `None` lock REFUSES
#: rather than measuring against a pre-registration that can still be edited.
BYTE_LOCK = "9bf64df"

#: The record this run assembles. A different file from the first record's,
#: so a repair that ran twice could never be mistaken for the STOP it repairs.
RESULTS = (REPO / "docs" / "superpowers" / "acceptance"
           / "2026-09-05-sensorium-rung4-entry-grain-repair.results.json")

#: The raw facts, in the (gitignored) plan ledger beside the first run's.
RAW = "results-grain-repair-raw.json"
#: The markers a watcher polls for, and the runner this record names.
MARKER_DONE = "grain-repair.DONE"
MARKER_FAILED = "grain-repair.FAILED"
RUNNER = "rust/tests/acceptance_grain_repair.py"

#: Every name this module does NOT share with `acceptance_grain`. The
#: sibling's whole claim is that it is the same instrument pointed at another
#: document, and this list is that claim written down where a test can check
#: it (`tests/test_acceptance_grain_repair.py`).
OVERRIDES = ("DOC", "BYTE_LOCK", "BASE", "LOGS", "RESULTS", "RAW",
             "MARKER_DONE", "MARKER_FAILED", "RUNNER", "OVERRIDES",
             "grain_config", "check_byte_lock", "main", "assemble_only",
             "render_only")


def grain_config(paths) -> dict:
    """The first runner's config, with the ONE value in it that is a path
    into a ledger repointed at this run's.

    `acceptance_grain.grain_config` reads its own module's `LOGS` for H1's
    `e6_workdir`, and that name still holds the first record's workspace --
    module globals are resolved where the function was defined, not where it
    was called. Left alone, this run would copy twenty corpus cases into the
    evidence directory of the record it exists to repair. Nothing else in the
    config is a path this run writes.
    """
    cfg = grain.grain_config(paths)
    cfg["e6_workdir"] = LOGS / "e6-cases"
    return cfg


def check_byte_lock() -> dict:
    """§1 of THIS document, as committed, versus the working tree -- or a
    refusal to start. The first runner's own check reads the first
    document's lock, which is already set and is not this one."""
    if not BYTE_LOCK:
        raise Refused(
            "§1 of the repair acceptance document is not locked yet: "
            "BYTE_LOCK is None. Commit §1 ALONE, then set BYTE_LOCK to that "
            "commit's sha.")
    return rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)


def main(argv) -> int:
    """The first runner's `main`, phase for phase, writing this document's
    ledger, markers and record."""
    lib.LEDGER, lib.LOGS, ph.LOGS, gph.LOGS = LEDGER, LOGS, LOGS, LOGS
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in (MARKER_DONE, MARKER_FAILED):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": RUNNER,
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = check_byte_lock()
        paths = env_paths_grain()
        cfg = grain_config(paths)
        res["config"] = {k: str(v) if isinstance(v, Path) else v
                         for k, v in cfg.items()}
        orc = oracle(ORACLE)
        # The JSON-SAFE projection: `orc`'s per-arm tables are keyed by
        # (file, line) TUPLES, which `json.dumps` cannot write at all. The
        # tuple-keyed `orc` stays local, where the comparisons need it.
        res["oracle"] = oracle_json(orc)
        step(f"oracle: {cfg['oracle_record']} at {ORACLE_COMMIT} -- sites "
             f"{orc['sites']}, lines {orc['lines']}, tally lines "
             f"{orc['tally_lines']}")
        pins = preflight_grain(paths, cfg)
        res["pins"] = pins

        res["raw_h2"] = phase_h2(paths, cfg, orc)
        res["raw_h3"] = phase_h3(paths, cfg, orc)
        res["raw_h4"] = phase_h4(paths, cfg, orc)
        # H1 last of the reader phases and BEFORE H6: it is the only phase
        # that runs the driver, and H6's `cargo test` is the only thing that
        # could relink it.
        res["raw_e6"] = phase_h1(paths, cfg)
        res["raw_h6"] = phase_h6(paths, cfg)
        res["raw_reported"] = reported(cfg, orc, res["raw_h2"],
                                       res["raw_h3"], res["raw_h4"])
        res["cleanup"] = cleanup_grain(paths, cfg, pins)
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
            res["cleanup_after_failure"] = cleanup_grain(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(grain.LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    raw_path = LEDGER / RAW
    try:
        raw_path.write_text(json.dumps(res, indent=2, default=str))
    except (TypeError, ValueError):
        # The last act of an hour-long run, and it must not be able to lose
        # the run. `default=` does not apply to dict KEYS, so one
        # unserialisable key would otherwise raise here -- outside every try
        # -- and leave no raw record, no `results.json` and NO MARKER, which
        # is the one state the marker exists to make impossible.
        import traceback
        tb = traceback.format_exc()
        (LOGS / "raw-json-error.txt").write_text(tb)
        res["raw_json_error"] = tb.strip().splitlines()[-1]
        step("writing the raw record FAILED (logs/raw-json-error.txt); "
             "writing what CAN be serialised instead")
        raw_path.write_text(grain._partial_json(res))
        rc = rc or 6
    try:
        assemble_only(res)
        render_only()
    except Exception:                                          # noqa: BLE001
        import traceback
        (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
        step("assemble/render FAILED (logs/assemble-error.txt); the raw "
             "record is intact")
        rc = rc or 5
    (BASE / (MARKER_DONE if rc == 0 else MARKER_FAILED)).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw facts at {raw_path}")
    return rc


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema -- the FIRST runner's schema,
    so the two records are read the same way. It re-runs no phase and reads
    no new number."""
    from acceptance_grain_schema import assemble_grain               # noqa: PLC0415
    if raw is None:
        raw = json.loads((LEDGER / RAW).read_text())
    doc = assemble_grain(raw)
    doc["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": RAW,
        "by": f"{RUNNER} --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no phase was re-run and no value "
                 "re-measured"),
    }
    RESULTS.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    print(f"assembled {RESULTS} from {RAW}")
    return 0


def render_only() -> int:
    """§2 and §3, rendered from the assembled record into this run's ledger.
    The document itself is edited by hand at Task 8; this is the text it
    pastes, produced by committed code rather than by a one-off script."""
    import render_grain                                             # noqa: PLC0415
    doc = json.loads(RESULTS.read_text())
    text = "\n".join(render_grain.environment(doc) + [""]
                     + render_grain.results(doc))
    (BASE / "section-2-3.md").write_text(text + "\n")
    print(f"rendered {BASE / 'section-2-3.md'}")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only() or render_only())
    if "--render" in sys.argv[1:]:
        raise SystemExit(render_only())
    raise SystemExit(main(sys.argv[1:]))
