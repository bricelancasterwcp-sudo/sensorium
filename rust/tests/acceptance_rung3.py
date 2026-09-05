#!/usr/bin/env python3
"""The rung-3 acceptance runner: E6, E6', E2'', E7'', E3'', E5'' and E0'',
in the order `docs/superpowers/acceptance/
2026-09-04-sensorium-rung3-acceptance.md` §1 pre-registered, plus E1''
reported without a gate.

§1 is BYTE-LOCKED. It was committed alone at `e34623c`, before the transformer
changes; its E6' endpoint was then AMENDED, post-lock and before any E6' number
existed, at `5bc71f7` (the dated footnote in §1 keeps the original wording
visible). This runner refuses to start unless the working tree's §1 is
byte-identical to `5bc71f7`'s, and records BOTH shas -- so a reader can see
exactly what moved and when, and §4 reports the E6' count under both readings.

It re-uses the rung-2 instrument rather than restating it: `acceptance_lib` for
paths, processes and manifests; `acceptance_phases` for the protocols §1 calls
"verbatim" (`phase_e3` for E3'', `phase_e5` for E5'', `phase_walls` for E1'',
`phase_census` for the denominator's own instrument, `phase_e7a` for the
mechanics run); `acceptance.real_config` for the package, the arms and the
filter. What is NEW is in `acceptance_phases_rung3`: the E6 cross-case
collector, the E6' run and its parsed SWALLOWED lines, E2'''s `kind: "try"`
numerator, E0'''s two walls under an ARMED kill, and E7'''s operand columns.

The rung-2 and E5' ledgers are READ-ONLY for this slice: `LEDGER` and `LOGS`
are re-pointed at this plan's own workspace before anything runs.

Every location is an environment variable (`acceptance_lib.env_paths` plus
`SENSORIUM_CORPUS_TARGET`); a missing one refuses in the preflight, and no path
to a tree or a binary is written into this file. `SENSORIUM_SOURCE_BLOOMERY` is
optional to `env_paths` but REQUIRED here: it names the read-only source tree
whose HEAD and porcelain are asserted unchanged before and after, and a run
that cannot name it refuses rather than quietly assert nothing.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_rung3.py \
        > <ledger>/acceptance/logs/rung3.log 2>&1 &

The last act is `<ledger>/acceptance/logs/rung3.DONE` (or `.FAILED`) carrying
`exit=<n>`, so silence is distinguishable from success.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-04-sensorium-rung3-err-flow"
LEDGER = PLAN
LOGS = PLAN / "acceptance" / "logs"

# The rung-2 and E5' ledgers are evidence and are not written to again.
# Re-point the shared plumbing BEFORE importing the phases, so every log this
# run writes lands in this plan's own workspace.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_phases as ph                                     # noqa: E402
import acceptance_phases_rung3 as r3                               # noqa: E402
from acceptance import real_config                                 # noqa: E402
from acceptance_lib import (CLONE_PIN, E3_RUNS, LOAD_CEILING,      # noqa: E402
                            REPO_DISK_FLOOR_GB, STEPS,
                            TARGET_DISK_FLOOR_GB, Refused, dir_bytes,
                            env_paths, free_gb, git, loadavg, manifests_dir,
                            sha256_file, step)

ph.LOGS = LOGS

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-04-sensorium-rung3-acceptance.md")

#: The commit §1 is byte-locked against NOW: the amended E6' endpoint.
BYTE_LOCK = "5bc71f7"
#: The ORIGINAL lock, committed alone by Task 0 before the transformer
#: changes. §1 at this commit differs from the one above by exactly the dated
#: E6' footnote; both shas are recorded so the amendment is visible, never
#: silent.
ORIGINAL_LOCK = "e34623c"

#: §1's frozen E2'' denominator, counted by Task 0 BEFORE the lock and written
#: into §1 in words. Repeated here as the number the ratio is taken over: a
#: denominator re-derived at run time is not a frozen denominator.
TRY_SYN = 401
TRY_MACRO_TOKENS = 1


def out(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def section1(text: str) -> str:
    """§1, as `awk '/^## 1/,/^## 2/'` extracts it."""
    keep, buf = False, []
    for line in text.splitlines(keepends=True):
        if line.startswith("## 1"):
            keep = True
        if keep:
            buf.append(line)
        if keep and line.startswith("## 2"):
            break
    return "".join(buf)


def _committed(rel: str, commit: str) -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{rel}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def byte_lock_check() -> dict:
    """§1 of the acceptance document, as committed, versus the working tree.

    The endpoint is decided before the instrument exists; this is the check
    that it did not move afterwards. BOTH locks are recorded: the run refuses
    unless the tree matches `BYTE_LOCK`, and the sha at `ORIGINAL_LOCK` is
    carried beside it so the post-lock amendment is a visible fact of the
    record rather than a claim in prose."""
    rel = DOC.relative_to(REPO).as_posix()
    now_text = section1(DOC.read_text())
    locked_text = _committed(rel, BYTE_LOCK)
    if locked_text is None:
        raise Refused(f"cannot read {rel} at {BYTE_LOCK}")
    locked = section1(locked_text)
    orig_text = _committed(rel, ORIGINAL_LOCK)
    orig = section1(orig_text) if orig_text is not None else None
    rec = {
        "commit": BYTE_LOCK, "doc": rel,
        "extraction": "awk '/^## 1/,/^## 2/'",
        "locked_sha256": _sha(locked), "locked_bytes": len(locked.encode()),
        "working_tree_sha256": _sha(now_text),
        "working_tree_bytes": len(now_text.encode()),
        "identical": locked == now_text,
        "original_lock": ORIGINAL_LOCK,
        "original_lock_sha256": _sha(orig) if orig is not None else None,
        "original_lock_bytes": len(orig.encode()) if orig is not None else None,
        "amended_after_the_original_lock": (orig is not None
                                            and orig != locked),
        "amendment_bytes": (len(locked.encode()) - len(orig.encode())
                            if orig is not None else None),
    }
    if not rec["identical"]:
        raise Refused(
            f"§1 of {rel} differs from the byte-lock at {BYTE_LOCK}: "
            f"{rec['locked_sha256'][:12]} vs {rec['working_tree_sha256'][:12]}")
    step(f"byte-lock ok: §1 == {BYTE_LOCK}:{rel} "
         f"(sha256 {rec['locked_sha256'][:12]}, {rec['locked_bytes']} bytes); "
         f"original lock {ORIGINAL_LOCK} sha256 "
         f"{(rec['original_lock_sha256'] or '?')[:12]}, amended="
         f"{rec['amended_after_the_original_lock']}")
    return rec


# ------------------------------------------------------------------- config


def rung3_config(paths) -> dict:
    cfg = dict(real_config(paths))
    corpus_target = os.environ.get("SENSORIUM_CORPUS_TARGET")
    if not corpus_target:
        raise Refused("SENSORIUM_CORPUS_TARGET is unset: name the cargo target "
                      "the corpus cases build into, or E6 records into a "
                      "different tree than the one the lens states")
    cfg.update({
        "corpus_target": Path(corpus_target),
        "e6_workdir": LOGS / "e6-cases",
        "e6_record_timeout": 3600,
        "e6prime_timeout": 7200,
        "e2pp_timeout": 14400,
        "cli_timeout": 3600,
        "e3_runs": E3_RUNS,
        "wall_rounds": lib.WALL_ROUNDS,
        "try_syn": TRY_SYN,
        "try_macro_tokens": TRY_MACRO_TOKENS,
    })
    return cfg


# ---------------------------------------------------------------- preflight


def preflight(paths, cfg) -> dict:
    step("rung-3 preflight")
    clone = paths["sensorium_bloomery_clone"]
    target = paths["sensorium_acceptance_target"]
    load = loadavg()
    target_free = free_gb(target)
    repo_free = free_gb(REPO)
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{target}: {target_free:.1f} GB free < "
                      f"{TARGET_DISK_FLOOR_GB} GB floor")
    if repo_free < REPO_DISK_FLOOR_GB:
        raise Refused(f"{REPO}: {repo_free:.1f} GB free < "
                      f"{REPO_DISK_FLOOR_GB} GB floor")
    driver = Path(paths["sensorium_driver"])
    if not driver.is_file():
        raise Refused(f"no driver at {driver}")
    census = Path(paths["sensorium_census_driver"])
    if not census.is_file():
        raise Refused(f"no census driver at {census}")
    if not cfg["corpus_target"].is_dir():
        raise Refused(f"no corpus target directory at {cfg['corpus_target']}")

    head = git(paths, "rev-parse", "HEAD").strip()
    porcelain = git(paths, "status", "--porcelain")
    if head != CLONE_PIN:
        raise Refused(f"the clone is at {head}, pinned at {CLONE_PIN}")
    if porcelain.strip():
        raise Refused(f"the clone is not clean:\n{porcelain}")
    tips = {}
    for label, ref in cfg["e5_arms"]:
        tip = out("git", "-C", str(clone), "rev-parse", ref)
        if not tip:
            raise Refused(f"arm {label}: the clone cannot resolve {ref!r}")
        tips[label] = tip

    sdir = paths["sensorium_dir"]
    if sdir.exists() and any(sdir.iterdir()):
        raise Refused(f"SENSORIUM_DIR {sdir} is not empty; this run needs a "
                      "NEW traces directory")
    sdir.mkdir(parents=True, exist_ok=True)

    src = paths["source_bloomery"]
    if src is None:
        raise Refused("SENSORIUM_SOURCE_BLOOMERY is unset: name the read-only "
                      "source tree this run asserts unchanged, or the "
                      "assertion is vacuous")
    src_head = out("git", "-C", str(src), "rev-parse", "HEAD")
    src_porcelain = out("git", "-C", str(src), "status", "--porcelain")

    md = manifests_dir(paths)
    stale = sorted(p.name for p in md.glob("*.json")) if md.is_dir() else []
    step(f"preflight: {len(stale)} manifest(s) present before E2'' empties the "
         f"whole target directory")

    pins = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse",
                           "--abbrev-ref", "HEAD"),
        "repo_porcelain": out("git", "-C", str(REPO), "status", "--porcelain"),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "driver_mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                      time.localtime(driver.stat().st_mtime)),
        "census_driver": str(census),
        "census_driver_sha256": sha256_file(census),
        "rustc": out("rustc", "-V"), "cargo": out("cargo", "-V"),
        "toolchains": out("rustup", "toolchain", "list"),
        "python": out(str(REPO / ".venv" / "bin" / "python"), "-V"),
        "sensorium_version": out(
            str(REPO / ".venv" / "bin" / "python"), "-c",
            "import importlib.metadata as m; print(m.version('sensorium'))"),
        "nproc": os.cpu_count(),
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/"
                         "scaling_governor").read_text().strip(),
        "RUSTFLAGS": os.environ.get("RUSTFLAGS", ""),
        "CARGO_INCREMENTAL": os.environ.get("CARGO_INCREMENTAL", ""),
        "RUSTC_WRAPPER": os.environ.get("RUSTC_WRAPPER", ""),
        "load_1min_at_start": load,
        "target_disk_free_gb": round(target_free, 2),
        "repo_disk_free_gb": round(repo_free, 2),
        "clone": str(clone), "clone_head": head,
        "clone_porcelain_before": porcelain,
        "clone_branches_before": git(paths, "branch", "-v").strip(),
        "arm_tips": tips,
        "clone_cargo_lock_sha256_before": sha256_file(clone / "Cargo.lock"),
        "source_bloomery": str(src),
        "source_bloomery_head_before": src_head,
        "source_bloomery_porcelain_before": src_porcelain,
        "target_dir": str(target),
        "target_warm_at_start": True,
        "target_bytes_before": dir_bytes(target),
        "manifests_present_before": stale,
        "corpus_target": str(cfg["corpus_target"]),
        "corpus_target_bytes_before": dir_bytes(cfg["corpus_target"]),
        "probe_target": str(paths["sensorium_probe_target"]),
        "sensorium_dir": str(sdir),
        "packages": cfg["packages"],
        "frozen_denominator": {"try_syn": TRY_SYN,
                               "try_macro_tokens": TRY_MACRO_TOKENS,
                               "source": "§1, counted by Task 0 before the "
                                         "byte-lock"},
    }
    step(f"preflight ok: load={load} target_free={target_free:.1f}GB "
         f"driver={pins['driver_sha256'][:12]} arms={tips}")
    return pins


ARM_LOAD: list = []


def install_load_hook():
    """The 1-minute load at each arm's start, which the lens names."""
    original = ph.git

    def hooked(p, *args):
        if args and args[0] == "checkout":
            ARM_LOAD.append({"ref": args[-1], "load_1min": loadavg(),
                             "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        return original(p, *args)

    ph.git = hooked
    return original


def cleanup(paths, cfg, pins) -> dict:
    clone = paths["sensorium_bloomery_clone"]
    git(paths, "checkout", "-q", "--detach", CLONE_PIN)
    head = git(paths, "rev-parse", "HEAD").strip()
    porcelain = git(paths, "status", "--porcelain")
    src = paths["source_bloomery"]
    src_head = out("git", "-C", str(src), "rev-parse", "HEAD")
    src_porcelain = out("git", "-C", str(src), "status", "--porcelain")
    c = {
        "clone_head_after": head, "clone_restored": head == CLONE_PIN,
        "clone_porcelain_after": porcelain,
        "clone_clean_after": not porcelain.strip(),
        "clone_branches_after": git(paths, "branch", "-v").strip(),
        "clone_cargo_lock_sha256_after": sha256_file(clone / "Cargo.lock"),
        "cargo_lock_unchanged": (sha256_file(clone / "Cargo.lock")
                                 == pins.get("clone_cargo_lock_sha256_before")),
        "source_bloomery_head_after": src_head,
        "source_bloomery_porcelain_after": src_porcelain,
        "source_bloomery_unchanged": (
            src_head == pins.get("source_bloomery_head_before")
            and src_porcelain == pins.get("source_bloomery_porcelain_before")),
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
        "driver_unchanged": (sha256_file(paths["sensorium_driver"])
                             == pins.get("driver_sha256")),
        "repo_porcelain_after": out("git", "-C", str(REPO), "status",
                                    "--porcelain"),
        "target_bytes_after": dir_bytes(paths["sensorium_acceptance_target"]),
        "corpus_target_bytes_after": dir_bytes(cfg["corpus_target"]),
        "sensorium_dir_bytes": dir_bytes(paths["sensorium_dir"])
        if paths["sensorium_dir"].is_dir() else 0,
        "target_disk_free_gb_after": round(
            free_gb(paths["sensorium_acceptance_target"]), 2),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"cleanup: clone at {head[:12]} restored={c['clone_restored']} "
         f"clean={c['clone_clean_after']} "
         f"source_unchanged={c['source_bloomery_unchanged']}")
    return c


# -------------------------------------------------------------------- main


def main(argv) -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("rung3.DONE", "rung3.FAILED"):
        (LOGS / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": "rust/tests/acceptance_rung3.py",
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = byte_lock_check()
        paths = env_paths(False)
        cfg = rung3_config(paths)
        res["config"] = {k: str(v) if isinstance(v, Path) else v
                         for k, v in cfg.items()}
        pins = preflight(paths, cfg)
        res["pins"] = pins
        install_load_hook()

        # The denominator's own instrument, run over the clone and REPORTED.
        # The ratio below is taken over §1's FROZEN numbers, never over these.
        step("census: the E2'' denominator instrument, re-run and reported")
        res["raw_census"] = ph.phase_census(paths, cfg)
        res["raw_census_try"] = r3.phase_census_try(paths, cfg)

        step("E2'': from-scratch workspace build (empties the target first)")
        res["raw_e2pp"] = r3.phase_e2pp(paths, cfg)

        step("E6': the clone's --lib suite, then `exceptions` paged whole")
        res["raw_e6prime"] = r3.phase_e6prime(paths, cfg)

        step("E0'': info and diff on the E6' trace, 60 s kill armed")
        res["raw_e0pp"] = r3.phase_e0pp(paths, cfg,
                                        (res["raw_e6prime"] or {}).get("run"))

        step("E3'': the rung-2 E3 protocol verbatim")
        res["raw_e3"] = ph.phase_e3(paths, cfg)

        step("E5'': the E5' protocol verbatim (three arms, four diffs)")
        res["raw_e5"] = ph.phase_e5(paths, cfg)

        step("E7'': mechanics.sh, with the new ?-operand panic")
        res["raw_e7pp"] = r3.phase_e7pp(paths, cfg)

        step("E6: the Rust corpus cases with an `exceptions` question")
        res["raw_e6"] = r3.phase_e6(paths, cfg)

        step("E1'': the --lib plain/call walls (reported, not gated)")
        res["raw_walls"] = ph.phase_walls(paths, cfg)

        res["arm_checkout_loads"] = ARM_LOAD
        res["cleanup"] = cleanup(paths, cfg, pins)
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
            res["cleanup_after_failure"] = cleanup(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_checkout_loads"] = ARM_LOAD
    res["steps"] = STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-rung3-raw.json").write_text(
        json.dumps(res, indent=2, default=str))
    try:
        assemble_only(res)
    except Exception:                                          # noqa: BLE001
        import traceback
        (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
        step("assemble FAILED (logs/assemble-error.txt); the raw record is intact")
        rc = rc or 5
    (LOGS / ("rung3.DONE" if rc == 0 else "rung3.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw rung-3 facts at "
         f"{LEDGER / 'results-rung3-raw.json'}")
    return rc


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no arm and reads
    no new number: it exists so the assembly is reproducible from committed
    code rather than from a one-off script (the rung-2 precedent,
    `acceptance.py --assemble`)."""
    from acceptance_schema_rung3 import assemble_rung3              # noqa: PLC0415
    if raw is None:
        raw = json.loads((LEDGER / "results-rung3-raw.json").read_text())
    doc = assemble_rung3(raw)
    doc["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": "results-rung3-raw.json",
        "by": "rust/tests/acceptance_rung3.py --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no arm was re-run and no value "
                 "re-measured"),
    }
    dest = (REPO / "docs" / "superpowers" / "acceptance"
            / "2026-09-04-sensorium-rung3-acceptance.results.json")
    dest.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    print(f"assembled {dest} from results-rung3-raw.json")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only())
    raise SystemExit(main(sys.argv[1:]))
