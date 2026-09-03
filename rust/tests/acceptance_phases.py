"""The rung-2 acceptance phases, in the pre-registered protocol order.

Each phase returns raw facts only. Nothing here decides a verdict: §4 of
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` is
written by hand against the rules, and `acceptance_schema.py` turns these
facts into the none-versus-zero `results.json` the renderer prints.
"""

from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path

from acceptance_lib import (COOLDOWN_S, LOAD_CEILING, LOGS, Refused, cargo_exit_of,
                            dir_bytes, driver_cmd, git, loadavg, metadata_set,
                            mirror_identity, parse_spool, plain_env,
                            read_manifests, rmtree, run, run_lines,
                            sensorium_cli, sha256_file, spool_of, step,
                            target_env, trace_bytes, trace_meta, unit_sets)

# --------------------------------------------------------------------- E8


def _build(paths, cfg, args, log, instrumented, timeout=7200):
    cmd = (driver_cmd(paths, *args, "-v") if instrumented
           else ["cargo", "test", *args, "-v"])
    res = run(cmd, paths["sensorium_bloomery_clone"], log,
              target_env(paths), timeout)
    comp, fresh = unit_sets(res, cfg["packages"])
    return res, {"rc": res["rc"], "wall": round(res["wall"], 3),
                 "compiled": comp, "fresh": fresh,
                 "cargo_exit": cargo_exit_of(res) if instrumented else res["rc"],
                 "metadata_units": metadata_set(res), "log": res["log"]}


def _test_exe(paths, cfg, instrumented, target_name, label):
    """One test executable's path, by target name, from cargo's own JSON."""
    args = [*cfg["pkg"], "--lib", "--no-run", "--message-format=json"]
    cmd = (driver_cmd(paths, *args, tier="off") if instrumented
           else ["cargo", "test", *args])
    res = run(cmd, paths["sensorium_bloomery_clone"], f"exe-{label}.log",
              target_env(paths))
    found = None
    for line in res["out"].splitlines():
        try:
            v = json.loads(line)
        except ValueError:
            continue
        if (v.get("reason") == "compiler-artifact"
                and v.get("target", {}).get("name") == target_name
                and v.get("profile", {}).get("test") and v.get("executable")):
            found = v["executable"]
    return found


def phase_e8(paths, cfg) -> dict:
    """(a) -> (c)+sentinel -> (d) on the measured workspace, then (b) on its
    own branch. The target directory was emptied in the preflight, so the
    plain build below is a genuinely clean build of the whole build graph."""
    out: dict = {"checks": {}, "builds": {}}
    pkg = cfg["pkg"]

    step("E8: plain --no-run #1 (the baseline build wall, cold target)")
    p1, out["builds"]["plain1"] = _build(paths, cfg, [*pkg, "--no-run"],
                                         "e8-plain1.log", False)
    if p1["rc"] != 0:
        raise Refused(f"plain --no-run failed: {p1['err'][-2000:]}")
    expected_fresh = sorted(set(out["builds"]["plain1"]["compiled"])
                            | set(out["builds"]["plain1"]["fresh"]))
    out["expected_fresh_set"] = expected_fresh
    step(f"E8: plain #1 wall={p1['wall']:.2f}s compiled={out['builds']['plain1']['compiled']}")

    step("E8: instrumented --no-run #1")
    i1, out["builds"]["instr1"] = _build(paths, cfg, [*pkg, "--no-run"],
                                         "e8-instr1.log", True)
    if i1["rc"] != 0:
        raise Refused(f"instrumented --no-run failed: {i1['err'][-3000:]}")
    step(f"E8: instr #1 wall={i1['wall']:.2f}s units={len(out['builds']['instr1']['metadata_units'])}")

    def freshness(name, log, instrumented):
        _res, b = _build(paths, cfg, [*pkg, "--no-run"], log, instrumented)
        out["builds"][name] = b
        ok = b["rc"] == 0 and b["compiled"] == [] and b["fresh"] == expected_fresh
        step(f"E8[{name}]: compiled={b['compiled']} fresh={b['fresh']} -> {ok}")
        return {"pass": ok, "rc": b["rc"], "compiled": b["compiled"],
                "fresh": b["fresh"], "expected_fresh": expected_fresh}

    out["checks"]["a_second_instrumented_compiles_nothing"] = freshness(
        "instr2", "e8-instr2.log", True)
    out["checks"]["c_plain_after_instrumented_compiles_nothing"] = freshness(
        "plain2", "e8-plain2.log", False)

    step("E8(c) sentinel: both --lib binaries run with SENSORIUM_SPOOL set")
    plain_exe = _test_exe(paths, cfg, False, cfg["lib_target"], "plain")
    instr_exe = _test_exe(paths, cfg, True, cfg["lib_target"], "instr")
    sent = {"plain_exe": plain_exe, "instrumented_exe": instr_exe}
    if not plain_exe or not instr_exe or plain_exe == instr_exe:
        sent.update({"pass": False,
                     "why": "could not resolve two distinct --lib binaries"})
    else:
        for name, exe in (("plain", plain_exe), ("instrumented", instr_exe)):
            sp = LOGS / f"sentinel-spool-{name}"
            rmtree(sp)
            sp.mkdir(parents=True)
            env = plain_env() | {"SENSORIUM_SPOOL": str(sp),
                                 "SENSORIUM_TIER": "call"}
            r = run([exe], paths["sensorium_bloomery_clone"],
                    f"e8-sentinel-{name}.log", env)
            sent[name] = len([q for q in sp.rglob("*") if q.is_file()])
            sent[name + "_rc"] = r["rc"]
            if name == "instrumented":
                sent["instrumented_spool_bytes"] = dir_bytes(sp)
            rmtree(sp)
        sent["plain_exe_bytes"] = Path(plain_exe).stat().st_size
        sent["instrumented_exe_bytes"] = Path(instr_exe).stat().st_size
        sent["pass"] = sent["plain"] == 0 and sent["instrumented"] > 0
    out["checks"]["c_sentinel"] = sent
    step(f"E8(c) sentinel: plain={sent.get('plain')} instrumented={sent.get('instrumented')}")

    out["checks"]["d_instrumented_after_plain_compiles_nothing"] = freshness(
        "instr3", "e8-instr3.log", True)

    # The manifests of the FROM-SCRATCH instrumented build, read here --
    # before (b) touches a source file -- and scoped to that build's own unit
    # set. Everything E2' reads about the package build comes from this.
    out["package_manifests"] = read_manifests(
        paths, out["builds"]["instr1"]["metadata_units"])
    out["package_mirror_identity"] = mirror_identity(
        paths, out["package_manifests"]["units"])
    step(f"E2[package build]: distinct={out['package_manifests']['distinct']} "
         f"units={len(out['package_manifests']['units'])} "
         f"fell_back={len(out['package_manifests']['fell_back'])} "
         f"mirror_checked={out['package_mirror_identity']['checked']}")

    out["checks"]["b_touch_recompiles_that_unit_and_its_dependents"] = _e8b(
        paths, cfg, expected_fresh)

    fell = []
    for b in out["builds"].values():
        fell += [ln for ln in Path(b["log"]).read_text().splitlines()
                 if "fell back to the real tree" in ln]
    out["fell_back_stderr_lines"] = fell
    return out


def _e8b(paths, cfg, expected_fresh) -> dict:
    """(b): append one comment line to a dependency's crate root; exactly that
    package and its dependents must recompile; restore."""
    clone = paths["sensorium_bloomery_clone"]
    touched = clone / cfg["touch_file"]
    if cfg["git"]:
        git(paths, "checkout", "-b", cfg["e8_branch"])
    before = touched.read_bytes()
    touched.write_bytes(before + b"\n// sensorium rung-2 E8(b): one appended comment line\n")
    step(f"E8(b): touched {cfg['touch_file']}")
    _res, b = _build(paths, cfg, [*cfg["pkg"], "--no-run"], "e8-touch.log", True)
    expect_compiled = sorted(cfg["touch_expect_compiled"])
    expect_fresh = sorted(set(expected_fresh) - set(expect_compiled))
    ok = (b["rc"] == 0 and b["compiled"] == expect_compiled
          and b["fresh"] == expect_fresh)
    if cfg["git"]:
        git(paths, "checkout", "--", cfg["touch_file"])
        git(paths, "checkout", "--detach", cfg["arm_a"])
        git(paths, "branch", "-D", cfg["e8_branch"])
    else:
        touched.write_bytes(before)
    restored = touched.read_bytes() == before
    step(f"E8(b): compiled={b['compiled']} fresh={b['fresh']} -> {ok}; restored={restored}")
    return {"pass": ok and restored, "rc": b["rc"], "compiled": b["compiled"],
            "fresh": b["fresh"], "expected_compiled": expect_compiled,
            "expected_fresh": expect_fresh, "source_restored": restored,
            "porcelain_after": git(paths, "status", "--porcelain") if cfg["git"] else None}


# --------------------------------------------------------------------- E2'


def phase_census(paths, cfg) -> dict:
    """The denominator, from `sensorium-transform`'s own census -- the parser
    that did the instrumenting -- over the same tree, one JSON row per file."""
    res = run([str(paths["sensorium_census_driver"]),
               str(paths["sensorium_bloomery_clone"])], paths["sensorium_bloomery_clone"],
              "census.log", plain_env())
    rows = []
    for line in res["out"].splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    tot = {k: sum(r[k] for r in rows)
           for k in ("fn_items", "const_fns", "extern_fns", "async_fns", "eligible")}
    reached = cfg["reached_prefixes"]
    scoped = [r for r in rows if r["file"].startswith(tuple(reached))]
    step(f"census: files={len(rows)} eligible={tot['eligible']} "
         f"reached={sum(r['eligible'] for r in scoped)} over {len(scoped)} files")
    return {"rc": res["rc"], "files": len(rows),
            "parsed": sum(1 for r in rows if r["parsed"]), "totals": tot,
            "reached_prefixes": list(reached),
            "reached_files": len(scoped),
            "reached_eligible": sum(r["eligible"] for r in scoped),
            "per_file": {r["file"]: r["eligible"] for r in rows},
            "log": res["log"]}


def phase_e2_workspace(paths, cfg) -> dict:
    """The workspace-wide instrumented `--no-run` whose manifests carry E2''s
    numerator.

    The whole target directory is emptied first, not just the manifests. Two
    reasons, and the second is why the stronger act is the correct one:

    * a manifest left by an earlier tool hash would inflate the numerator
      (the wrapper's path is hashed into cargo's `-C metadata`), and
    * cargo does not invoke the wrapper for a fingerprint-FRESH unit, so a
      cleared manifests directory over a warm target would silently LOSE
      every unit the E8 sequence had already compiled -- the numerator would
      then be missing exactly the units that were measured hardest. Emptying
      the target makes this build compile every unit, which is also what
      makes the `-C metadata=` set in its own `cargo -v` log complete."""
    target = paths["sensorium_acceptance_target"]
    removed = sum(rmtree(child) for child in sorted(target.iterdir()))
    emptied_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    step(f"E2: emptied the target ({removed} bytes, manifests included) at "
         f"{emptied_at}, so the measured build compiles every unit")
    res, b = _build(paths, cfg, [*cfg["workspace_sel"], "--no-run"],
                    "e2-workspace.log", True)
    if res["rc"] != 0:
        return {"dropped": f"cargo exit {res['rc']}", "build": b,
                "target_emptied_bytes": removed, "target_emptied_at": emptied_at}
    m = read_manifests(paths, b["metadata_units"])
    mi = mirror_identity(paths, m["units"])
    step(f"E2[workspace build]: distinct={m['distinct']} units={len(m['units'])} "
         f"fell_back={len(m['fell_back'])} unreached={len(m['unreached_files'])} "
         f"mirror_checked={mi['checked']}")
    return {"build": b, "manifests": m, "mirror_identity": mi,
            "target_emptied_bytes": removed, "target_emptied_at": emptied_at,
            "manifests_dir_empty_before": True}


# --------------------------------------------------------------------- E3


def phase_e3(paths, cfg) -> dict:
    """One build, then N recorded runs of the same binary with its sha256
    re-asserted before every one, then N-1 diffs against the first."""
    exe = _test_exe(paths, cfg, True, cfg["lib_target"], "e3")
    if not exe:
        return {"dropped": "could not resolve the instrumented --lib binary"}
    first = sha256_file(exe)
    runs, mismatches = [], []
    for i in range(1, cfg["e3_runs"] + 1):
        now = sha256_file(exe)
        if now != first:
            mismatches.append({"run": i, "sha256": now})
            runs.append({"i": i, "dropped": "test binary sha256 changed"})
            continue
        res = run(driver_cmd(paths, *cfg["pkg"], "--lib"),
                  paths["sensorium_bloomery_clone"], f"e3-run{i:02d}.log",
                  target_env(paths))
        lines = run_lines(res)
        pick = max(lines, key=lambda r: r["events"]) if lines else None
        runs.append({"i": i, "rc": res["rc"], "wall": round(res["wall"], 3),
                     "cargo_exit": cargo_exit_of(res),
                     "processes": len(lines),
                     "run": pick["run"] if pick else None,
                     "events": pick["events"] if pick else None,
                     "threads": pick["threads"] if pick else None,
                     "spool": spool_of(res)})
        if pick is None:
            runs[-1]["dropped"] = "the invocation recorded no process"
        step(f"E3 run {i}: {runs[-1].get('run')} events={runs[-1].get('events')}")
    ids = [r.get("run") for r in runs]
    diffs = []
    if ids and ids[0]:
        for k in range(2, len(ids) + 1):
            if not ids[k - 1]:
                diffs.append({"k": k, "verdict": None,
                              "dropped": "run k recorded no trace"})
                continue
            res = sensorium_cli(paths, ["diff", ids[0], ids[k - 1]], f"e3-diff{k:02d}")
            verdict = _verdict(res["out"])
            diffs.append({"k": k, "a": ids[0], "b": ids[k - 1], "rc": res["rc"],
                          "verdict": verdict, "stdout": res["out"].strip()})
            step(f"E3 diff 1 vs {k}: {verdict} (rc={res['rc']})")
    return {"exe": exe, "sha256": first, "sha256_mismatches": mismatches,
            "runs": runs, "diffs": diffs}


def _verdict(stdout: str) -> str | None:
    """The verdict a `diff` reached, from its own verdict line.

    The line is a sentence, not a token: a run whose causal work all happened
    inside tasks prints `verdict: MATCH -- no causal event ran outside a task
    ...` and, when those tasks differ, `verdict: the thread stream held no
    causal events on either side; DIVERGED on the tasks (below)`. DIVERGED is
    read first for exactly that second shape, which also contains MATCH."""
    line = next((l for l in stdout.splitlines() if l.startswith("verdict: ")), None)
    if line is None:
        return None
    for token in ("DIVERGED", "REFUSED", "MATCH modulo location", "MATCH"):
        if token in line:
            return token
    return line[len("verdict: "):]


def verdict_line(stdout: str) -> str | None:
    return next((l for l in stdout.splitlines() if l.startswith("verdict: ")), None)


# ------------------------------------------------------------------- walls


def phase_walls(paths, cfg) -> dict:
    """Plain vs call on the same selector, interleaved, order alternating,
    with a cool-down and the 1-minute load recorded at each arm's start."""
    step("walls: pre-building both arms")
    run(["cargo", "test", *cfg["pkg"], "--lib", "--no-run"],
        paths["sensorium_bloomery_clone"], "walls-prebuild-plain.log",
        target_env(paths))
    run(driver_cmd(paths, *cfg["pkg"], "--lib", "--no-run"),
        paths["sensorium_bloomery_clone"], "walls-prebuild-call.log",
        target_env(paths))
    cmds = {"P": lambda: ["cargo", "test", *cfg["pkg"], "--lib"],
            "C": lambda: driver_cmd(paths, *cfg["pkg"], "--lib")}
    runs, first = [], True
    for rnd in range(1, cfg["wall_rounds"] + 1):
        order = ("P", "C") if rnd % 2 else ("C", "P")
        for arm in order:
            if not first:
                time.sleep(COOLDOWN_S)
            first = False
            load = loadavg()
            rec = {"round": rnd, "arm": arm, "order": "".join(order),
                   "load_1min": load}
            if load > LOAD_CEILING:
                rec.update({"wall": None,
                            "dropped": f"1-min load {load} > {LOAD_CEILING} at arm start"})
                runs.append(rec)
                step(f"walls r{rnd} {arm}: DROPPED (load {load})")
                continue
            res = run(cmds[arm](), paths["sensorium_bloomery_clone"],
                      f"wall-r{rnd}-{arm}.log", target_env(paths))
            rec["rc"] = res["rc"]
            sp = spool_of(res)
            if sp:
                rec["spool_bytes"] = dir_bytes(Path(sp))
                rec["events"] = sum(r["events"] for r in run_lines(res))
                rmtree(Path(sp))
            if res["rc"] != 0:
                rec.update({"wall": None,
                            "dropped": f"exit {res['rc']} (infrastructure, not scored)"})
            else:
                rec["wall"] = round(res["wall"], 3)
            runs.append(rec)
            step(f"walls r{rnd} {arm}: {rec.get('wall')}s (load {load})")
    return {"runs": runs}


def wall_summary(runs, arm) -> dict:
    walls = [r["wall"] for r in runs if r["arm"] == arm and r.get("wall") is not None]
    dropped = [f"round {r['round']} {r['arm']}: {r['dropped']}" for r in runs
               if r["arm"] == arm and r.get("dropped")]
    if not walls:
        return {"median": None, "min": None, "max": None, "n": 0,
                "walls": [], "dropped": dropped}
    return {"median": round(statistics.median(walls), 3), "min": min(walls),
            "max": max(walls), "n": len(walls), "walls": walls,
            "dropped": dropped}


# --------------------------------------------------------------------- E7


DURATION = re.compile(r"finished in [0-9.]+s")
TID = re.compile(r"\(\d+\)")
TIME_SUFFIX = re.compile(r"\b\d+\.\d\ds\b")


def _mask(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = DURATION.sub("finished in <masked>", line)
        line = TID.sub("(<tid>)", line)
        line = TIME_SUFFIX.sub("<masked>", line)
        out.append(line)
    return out


def _libtest_section(stdout: str) -> list[str]:
    lines = stdout.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r"^running \d+ tests?", l)), None)
    end = next((i for i, l in enumerate(lines) if l.startswith("test result:")), None)
    if start is None or end is None:
        return []
    return lines[start:end + 1]


PANIC = re.compile(r"panicked at ([^\s:]+:\d+:\d+)")


def phase_e7b(paths, cfg) -> dict:
    """The same `--lib` suite, single-threaded, plain and instrumented: the
    libtest section and every panic location must be identical."""
    arms = {}
    for name, cmd in (("plain", ["cargo", "test", *cfg["pkg"], "--lib", "--",
                                 "--test-threads=1"]),
                      ("call", driver_cmd(paths, *cfg["pkg"], "--lib", "--",
                                          "--test-threads=1"))):
        res = run(cmd, paths["sensorium_bloomery_clone"], f"e7b-{name}.log",
                  target_env(paths))
        arms[name] = {"rc": res["rc"],
                      "section": _mask("\n".join(_libtest_section(res["out"]))),
                      "panics": PANIC.findall(res["err"]),
                      "result_line": next((l for l in res["out"].splitlines()
                                           if l.startswith("test result:")), None),
                      "log": res["log"]}
        if name == "call":
            sp = spool_of(res)
            arms[name]["spool_files"] = (
                len([q for q in Path(sp).rglob("*") if q.is_file()]) if sp else 0)
    a, b = arms["plain"]["section"], arms["call"]["section"]
    diff = [f"-{x}" for x in a if x not in b] + [f"+{y}" for y in b if y not in a]
    pa, pb = arms["plain"]["panics"], arms["call"]["panics"]
    out = {"arms": arms, "section_differences": diff,
           "section_lines": len(a),
           "panic_locations_plain": pa, "panic_locations_call": pb,
           "panic_location_differences": (0 if pa == pb else 1),
           "result_line_differs": int(_mask(arms["plain"]["result_line"] or "")
                                      != _mask(arms["call"]["result_line"] or "")),
           "differences": len(diff) + (0 if pa == pb else 1)
           + int(_mask(arms["plain"]["result_line"] or "")
                 != _mask(arms["call"]["result_line"] or ""))}
    step(f"E7(b): {out['differences']} differences over {len(a)} masked lines, "
         f"{len(pa)}/{len(pb)} panic locations, "
         f"{arms['call'].get('spool_files')} spool files under call")
    return out


def phase_e7a(paths) -> dict:
    """E7(a) and the probe half of E8: `rust/tests/mechanics.sh`, with the
    driver's sha256 asserted unchanged across it."""
    before = sha256_file(paths["sensorium_driver"])
    env = plain_env() | {"SENSORIUM_PROBE_TARGET": str(paths["sensorium_probe_target"]),
                         "CARGO_TARGET_DIR": str(Path(paths["sensorium_driver"]).parents[1])}
    res = run(["bash", str(Path(__file__).resolve().parent / "mechanics.sh")],
              Path(__file__).resolve().parents[2], "e7a-mechanics.log", env)
    body = res["out"] + res["err"]
    ok = re.findall(r"^ok: (\S+)$", body, re.M)
    bad = re.findall(r"^FAIL: (.+)$", body, re.M)
    skipped = re.findall(r"^skip: (.+)$", body, re.M)
    lines = body.splitlines()
    marks = [i for i, l in enumerate(lines)
             if l.startswith(("ok: e7", "FAIL: e7")) or "[E7]" in l]
    after = sha256_file(paths["sensorium_driver"])
    step(f"E7(a): {len(ok)} ok, {len(bad)} FAIL, {len(skipped)} skip, rc={res['rc']}")
    return {"rc": res["rc"], "ok": ok, "fail": bad, "skip": skipped,
            "e7_checks": [c for c in ok if c.startswith("e7")],
            "e7_lines": lines[marks[0]:marks[-1] + 1] if marks else [],
            "driver_sha256_before": before, "driver_sha256_after": after,
            "driver_unchanged": before == after, "log": res["log"]}


# --------------------------------------------------------------------- E5


def phase_e5(paths, cfg) -> dict:
    """Three arms on three trees: the original, the split, and the split plus
    one planted swap. The verifier is what has to tell them apart."""
    arms = {}
    for label, ref in cfg["e5_arms"]:
        if cfg["git"]:
            if label == "A":
                git(paths, "checkout", "-q", "--detach", ref)
            else:
                git(paths, "checkout", "-q", ref)
            head = git(paths, "rev-parse", "HEAD").strip()
        else:
            head = "(no git: the same tree three times -- dry run)"
        run(driver_cmd(paths, *cfg["pkg"], "--lib", "--no-run"),
            paths["sensorium_bloomery_clone"], f"e5-{label}-build.log",
            target_env(paths))
        res = run(driver_cmd(paths, *cfg["pkg"], "--lib", "--", cfg["e5_filter"]),
                  paths["sensorium_bloomery_clone"], f"e5-{label}-run.log",
                  target_env(paths))
        lines = run_lines(res)
        pick = max(lines, key=lambda r: r["events"]) if lines else None
        arms[label] = {"ref": ref, "head": head, "rc": res["rc"],
                       "wall": round(res["wall"], 3),
                       "run": pick["run"] if pick else None,
                       "events": pick["events"] if pick else None,
                       "threads": pick["threads"] if pick else None,
                       "tests": _test_names(res["out"]),
                       "log": res["log"]}
        step(f"E5 arm {label} ({ref}): run={arms[label]['run']} "
             f"events={arms[label]['events']}")
    if cfg["git"]:
        git(paths, "checkout", "-q", "--detach", cfg["arm_a"])
    ids = {k: v["run"] for k, v in arms.items()}
    diffs = {}
    if ids.get("A") and ids.get("B"):
        diffs["ab_ignore_moves"] = _diff(paths, ["diff", "--ignore-moves",
                                                 ids["A"], ids["B"]], "e5-ab-moves")
        diffs["ab_plain"] = _diff(paths, ["diff", ids["A"], ids["B"]], "e5-ab-plain")
    if ids.get("A") and ids.get("C"):
        diffs["ac_ignore_moves"] = _diff(paths, ["diff", "--ignore-moves",
                                                 ids["A"], ids["C"]], "e5-ac-moves")
        task = cfg.get("e5_task")
        if task:
            diffs["ac_task"] = _diff(paths, ["diff", "--ignore-moves", "--task",
                                             task, ids["A"], ids["C"]], "e5-ac-task")
    for k, v in diffs.items():
        step(f"E5 {k}: {v['verdict']} (rc={v['rc']})")
    return {"arms": arms, "diffs": diffs}


def _diff(paths, args, label) -> dict:
    res = sensorium_cli(paths, args, label)
    out = res["out"]
    moved = re.search(r"with (\d+) code object\(s\) paired", out)
    tasks_all = re.search(r"tasks: (\d+) task stream\(s\) on each side.*all matched", out)
    return {"argv": args, "rc": res["rc"], "verdict": _verdict(out),
            "verdict_line": verdict_line(out),
            "moved": int(moved.group(1)) if moved else None,
            "added": bool(re.search(r"^  added \(only in B\):", out, re.M)),
            "removed": bool(re.search(r"^  removed \(only in A\):", out, re.M)),
            "unpaired": bool(re.search(r"^  unpaired ", out, re.M)),
            "tasks_all_matched": bool(tasks_all),
            "tasks_each_side": int(tasks_all.group(1)) if tasks_all else None,
            "stdout": out.rstrip(), "stderr": res["err"].strip()[-2000:]}


def _test_names(stdout: str) -> list[str]:
    return re.findall(r"^test (\S+) \.\.\. ok$", stdout, re.M)


# ------------------------------------------------- the whole invocation


def phase_whole(paths, cfg) -> dict:
    """One `cargo sensorium test -p <package>`: every binary, every child, and
    what the traces say about themselves afterwards."""
    step("whole invocation: pre-building every test binary, so the timed part "
         "is the run and its conversion, not a build")
    pre = run(driver_cmd(paths, *cfg["pkg"], "--no-run"),
              paths["sensorium_bloomery_clone"], "whole-prebuild.log",
              target_env(paths))
    step(f"whole invocation: pre-build wall={pre['wall']:.2f}s rc={pre['rc']}")
    step("whole invocation: one instrumented run of every test binary")
    res = run(driver_cmd(paths, *cfg["pkg"]), paths["sensorium_bloomery_clone"],
              "whole-invocation.log", target_env(paths))
    lines = run_lines(res)
    spool = spool_of(res)
    warn = [l for l in res["err"].splitlines() if l.startswith("WARN:")]
    step(f"whole invocation: rc={res['rc']} processes={len(lines)} "
         f"events={sum(l['events'] for l in lines)}")

    metas, basis, child_runs, live, torn = {}, {}, 0, [], []
    seq_gaps = dropped = truncated = panics_unrecorded = unscoped = 0
    for l in lines:
        m = trace_meta(paths, l["run"])
        metas[l["run"]] = {k: m.get(k) for k in
                           ("exit_status", "exit_status_basis", "exit_signal",
                            "live_threads", "threads_started", "seq_gaps",
                            "records_dropped", "truncated_count",
                            "panics_unrecorded", "panics_outside_frames",
                            "manifests_unscoped", "child_runs", "incomplete",
                            "exe", "pid", "ppid")}
        basis[m.get("exit_status_basis")] = basis.get(m.get("exit_status_basis"), 0) + 1
        child_runs += len(m.get("child_runs") or [])
        live += [{"run": l["run"], "thread": t} for t in (m.get("live_threads") or [])]
        seq_gaps += m.get("seq_gaps") or 0
        dropped += sum((m.get("records_dropped") or {}).values())
        truncated += m.get("truncated_count") or 0
        panics_unrecorded += m.get("panics_unrecorded") or 0
        unscoped += m.get("manifests_unscoped") or 0

    spools = []
    if spool:
        for f in sorted(Path(spool).rglob("*.spool")):
            s = parse_spool(f)
            spools.append(s)
            if s.get("parsed") and not s.get("thread_end") and s.get("torn_last_record"):
                torn.append(s["file"])

    step("whole invocation: re-converting the same spool to time the conversion")
    conv = run([str(paths["sensorium_driver"]), "convert", spool],
               paths["sensorium_bloomery_clone"], "whole-reconvert.log",
               target_env(paths)) if spool else None

    total_events = sum(l["events"] for l in lines)
    tbytes = sum(trace_bytes(paths, l["run"]) for l in lines)
    return {"rc": res["rc"], "wall": round(res["wall"], 3), "spool": spool,
            "prebuild_wall": round(pre["wall"], 3), "prebuild_rc": pre["rc"],
            "warn_lines": warn, "processes": len(lines),
            "runner_binaries": len({l["exe"] for l in lines}),
            "events": total_events, "trace_bytes": tbytes,
            "spool_bytes": dir_bytes(Path(spool)) if spool else 0,
            "conversion_wall": round(conv["wall"], 3) if conv else None,
            "conversion_rc": conv["rc"] if conv else None,
            "conversion_processes": len(run_lines(conv)) if conv else None,
            "exit_status_basis": basis, "child_runs_total": child_runs,
            "live_threads": live, "live_thread_count": len(live),
            "spool_files": len(spools),
            "spools_without_thread_end": sum(1 for s in spools
                                             if s.get("parsed") and not s["thread_end"]),
            "spools_with_torn_last_record": torn,
            "seq_gaps": seq_gaps, "records_dropped": dropped,
            "truncated_count": truncated, "panics_unrecorded": panics_unrecorded,
            "manifests_unscoped": unscoped, "metas": metas,
            "per_process": lines}


def phase_costs(paths, cfg) -> dict:
    """The driver's own fixed cost, and the runtime rlib's build wall."""
    step("costs: driver fixed overhead (3 no-op builds each way)")
    plain, instr = [], []
    for i in range(3):
        plain.append(run(["cargo", "test", *cfg["pkg"], "--no-run"],
                         paths["sensorium_bloomery_clone"],
                         f"cost-plain-{i}.log", target_env(paths))["wall"])
        instr.append(run(driver_cmd(paths, *cfg["pkg"], "--no-run", tier="off"),
                         paths["sensorium_bloomery_clone"],
                         f"cost-instr-{i}.log", target_env(paths))["wall"])
    warm = statistics.median(instr)
    rt = paths["sensorium_acceptance_target"] / "sensorium" / "rt"
    removed = rmtree(rt)
    cold = run(driver_cmd(paths, *cfg["pkg"], "--no-run", tier="off"),
               paths["sensorium_bloomery_clone"], "cost-rt-cold.log",
               target_env(paths))
    step(f"costs: driver {round(warm - statistics.median(plain), 3)}s, "
         f"rt rebuild {round(cold['wall'] - warm, 3)}s")
    return {"plain_walls": [round(w, 3) for w in plain],
            "instrumented_walls": [round(w, 3) for w in instr],
            "plain_median": round(statistics.median(plain), 3),
            "instrumented_median": round(warm, 3),
            "driver_overhead_s": round(warm - statistics.median(plain), 3),
            "rt_removed_bytes": removed,
            "rt_cold_wall": round(cold["wall"], 3),
            "rt_build_s": round(cold["wall"] - warm, 3),
            "rt_rc": cold["rc"]}
