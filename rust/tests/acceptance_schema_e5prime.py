"""E5' raw acceptance facts -> `results.json` in the pre-registered shape.

Split out of `acceptance_schema.py` at that file's own `E5'` banner on
2026-09-08, when it reached the 800-line ceiling. Same rules as
`acceptance_schema.assemble` and `acceptance_schema_rung3.assemble_rung3`:
every measurement is `{"value", "n", "lens", "dropped"}`, a `null` value with
a non-empty `dropped` list is the ONLY representation of not-measured, `0` is
measured-and-zero, and nothing here decides a verdict.

The two committed helpers this document shares with the first file are
imported from it and never copied, in `acceptance_schema_rung3.py:20`'s
idiom: one copy of a rule is the whole point of a shared schema module.

Reached as `acceptance_schema.assemble_e5prime`, which that file re-exports --
`acceptance_e5prime.py:577` imports it from there, and the §2 sentence
`render_acceptance.py:401` renders names it there.
"""

from __future__ import annotations

from collections import Counter

from acceptance_lib import meas
from acceptance_schema import _drop, _e5


# ------------------------------------------------------------------- E5'


E5PRIME_DOC = ("docs/superpowers/acceptance/"
               "2026-09-03-sensorium-rung3-entry-e5prime.md")

# The reading of the A/B verdict line, ruled BEFORE the run (ledger, Task 3;
# `t5-context.md` §4) and repeated here so `results.json` carries it: on a
# trace whose causal events all live in tasks, the literal `MATCH modulo
# location` string prints only on the thread-stream branch, which is empty
# here. §1's label denotes the class the committed rung-2 schema `_e5`
# already encodes -- verdict token startswith MATCH, moved >= 1, 0 added,
# 0 removed, every task paired -- and that is how the condition is judged.
AB_READING = (
    "§1's label `MATCH modulo location` denotes the committed rung-2 `_e5` "
    "condition class (verdict token startswith MATCH; >= 1 moved; 0 added; "
    "0 removed; every task paired), because on a trace whose causal events "
    "all live in tasks the literal string prints only on the thread-stream "
    "branch. Ruled in the ledger before the run, not after the number.")


def _e5prime_env(raw: dict) -> dict:
    """§2's facts: what was measured, with what, on what."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or {}
    arms = (raw.get("raw_e5") or {}).get("arms") or {}
    return {
        "byte_lock": raw.get("byte_lock"),
        "driver": pins.get("driver"), "driver_sha256": pins.get("driver_sha256"),
        "driver_mtime": pins.get("driver_mtime"),
        "driver_unchanged_after": cl.get("driver_unchanged"),
        "repo_commit": pins.get("repo_commit"), "repo_branch": pins.get("repo_branch"),
        "repo_porcelain": pins.get("repo_porcelain"),
        "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
        "python": pins.get("python"),
        "sensorium_version": pins.get("sensorium_version"),
        "nproc": pins.get("nproc"), "governor": pins.get("governor"),
        "clone": pins.get("clone"), "clone_head": pins.get("clone_head"),
        "arm_tips": pins.get("arm_tips"),
        "arm_heads": {k: v.get("head") for k, v in arms.items()},
        "clone_porcelain_before": pins.get("clone_porcelain_before"),
        "clone_porcelain_after": cl.get("clone_porcelain_after"),
        "clone_restored": cl.get("clone_restored"),
        "cargo_lock_unchanged": cl.get("cargo_lock_unchanged"),
        "target_dir": pins.get("target_dir"), "target_warm": pins.get("target_warm"),
        "manifests_cleared_before_arm_a": len(
            pins.get("manifests_cleared_before_arm_a") or []),
        "manifests_cleared_bytes": pins.get("manifests_cleared_bytes"),
        "sensorium_dir": pins.get("sensorium_dir"),
        "source_bloomery": pins.get("source_bloomery"),
        "source_bloomery_head_before": pins.get("source_bloomery_head_before"),
        "source_bloomery_head_after": cl.get("source_bloomery_head_after"),
        "source_bloomery_porcelain_before":
            pins.get("source_bloomery_porcelain_before"),
        "source_bloomery_porcelain_after": cl.get("source_bloomery_porcelain_after"),
        "source_bloomery_unchanged": cl.get("source_bloomery_unchanged"),
        "load_1min_at_start": pins.get("load_1min_at_start"),
        "load_at_each_arm": raw.get("arm_checkout_loads"),
        "target_disk_free_gb": pins.get("target_disk_free_gb"),
        "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
        "unused_env": pins.get("unused_env"),
    }


def _e5prime_main(raw: dict) -> dict:
    """E5': the six committed rung-2 `_e5` conditions plus §1's `all ten task
    streams` clause, read on the A/B `--ignore-moves` diff."""
    base = _e5(raw, False)
    d = (raw.get("raw_e5") or {}).get("diffs") or {}
    ab, ac = d.get("ab_ignore_moves") or {}, d.get("ac_ignore_moves") or {}
    conds = dict(base["conditions"])
    conds["ab_all_ten_task_streams_paired"] = (
        ab.get("tasks_all_matched") is True and ab.get("tasks_each_side") == 10)
    failed = [k for k, v in conds.items() if not v]
    have = bool(ab) and bool(ac)
    lens = ("three arms on three trees of the clone (A = e209ed9, B = e5-split, "
            "C = e5-planted), each `cargo sensorium test -p bloomery-daemon --lib "
            "-- task::registry` under the driver of §2 on the warm rung-2 target; "
            "verdicts from `sensorium diff --ignore-moves`. " + AB_READING)
    return {
        "headline": meas(len(failed) if have else None, len(conds),
                         f"pre-registered E5' conditions not met, of "
                         f"{len(conds)}; " + lens,
                         _drop(raw, "raw_e5")
                         or ([] if have else ["a diff did not run"])),
        "conditions": conds, "conditions_failed": failed,
        "ab_reading": AB_READING,
        "ab_verdict": ab.get("verdict"), "ab_verdict_line": ab.get("verdict_line"),
        "ac_verdict": ac.get("verdict"), "ac_verdict_line": ac.get("verdict_line"),
        "ab_plain_verdict": (d.get("ab_plain") or {}).get("verdict"),
        "ab_plain_verdict_line": (d.get("ab_plain") or {}).get("verdict_line"),
        "ac_task_verdict": (d.get("ac_task") or {}).get("verdict"),
        "ac_task_verdict_line": (d.get("ac_task") or {}).get("verdict_line"),
        "ab_moved": meas(ab.get("moved"), 1,
                         "code objects paired across a move by qualname (A/B "
                         "`--ignore-moves`, from the `key:` line)"),
        "ab_tasks_each_side": meas(
            ab.get("tasks_each_side"), ab.get("tasks_each_side"),
            "task streams on each side of the A/B `--ignore-moves` diff, "
            "compared by content as (name, hash) -- the tool's own `tasks:` line"),
        "arms": base.get("arms"), "diffs": base.get("diffs"),
    }


def _e5prime_names(raw: dict) -> dict:
    """E5'-names: the predicted string on both sides, and A's multiset of
    `(name, hash)` equal to B's.

    Two numbers, because §1's sentence has two conjuncts and they read
    differently. The hash read here is the STORED `task_fingerprints.hash`,
    which TRACE-FORMAT §7 defines as a blake2b over `(file, qualname, kind)`
    per causal event -- so a file move changes it by construction, and
    `diff --ignore-moves` re-hashes both sides at query time rather than
    trusting it. Both readings are carried; neither is silently chosen."""
    n = raw.get("names") or {}
    e = raw.get("names_endpoint") or {}
    d = (raw.get("raw_e5") or {}).get("diffs") or {}
    ab = d.get("ab_ignore_moves") or {}
    dropped = e.get("dropped") or []
    a, b = n.get("A") or {}, n.get("B") or {}
    total = (a.get("spawn_count") or 0) + (b.get("spawn_count") or 0)
    bad = len(e.get("not_as_predicted") or [])
    pairs_differing = None
    if e.get("a_multiset") is not None and e.get("b_multiset") is not None:
        # A true multiset difference over the WHOLE (name, hash) pair: how many
        # of A's pairs have no equal pair left in B. Reported post-run as a
        # positional zip over two hash-sorted lists, which is not a pairing --
        # A [(x,h1),(x,h2)] against B [(x,h2),(x,h3)] would have read 2, not 1.
        # The value on this record is unchanged (4 of 4); only the definition is.
        ma = Counter(tuple(x) for x in e["a_multiset"])
        mb = Counter(tuple(x) for x in e["b_multiset"])
        pairs_differing = sum((ma - mb).values())
    name_lens = ("every task name containing `spawn@` on arms A and B, read from "
                 "each arm's own trace with `select task_id, name, hash, n_events "
                 "from task_fingerprints order by task_id` against "
                 "`$SENSORIUM_DIR/traces/<run>.db` opened read-only (the CLI has "
                 "no `tasks` command); compared to "
                 "`task::registry::tests::<test> :: spawn@TaskRegistry::"
                 "spawn_task#1`")
    hash_lens = ("the STORED `task_fingerprints.hash` of the same four children, "
                 "A against B as a multiset of (name, hash). TRACE-FORMAT §7: the "
                 "stored hash is a blake2b over `file\\x1fqualname\\x1fkind` per "
                 "causal event, so a file move changes it by construction; "
                 "`diff --ignore-moves` re-hashes both sides at query time "
                 "instead of reading this column; counted as the multiset "
                 "difference A - B over whole (name, hash) pairs, i.e. A-pairs "
                 "with no equal pair left in B, not a positional zip")
    conjuncts = {
        "every_spawn_name_is_the_predicted_string": (
            None if dropped else bad == 0 and total > 0),
        "stored_name_hash_multiset_a_equals_b": (
            None if dropped else e.get("multiset_equal") is True),
    }
    missed = ([k for k, v in conjuncts.items() if v is False]
              if not dropped else [])
    return {
        "predicted_shape": e.get("predicted_shape"),
        "conjuncts": conjuncts, "conjuncts_missed": missed,
        "headline": meas(len(missed) if not dropped else None, len(conjuncts),
                         "§1 E5'-names conjuncts missed, of 2 — (a) every "
                         "spawn@ name is the predicted string, (b) the multiset "
                         "of (name, hash) pairs on A equals B's. Each conjunct's "
                         "own number is in the table below; the hash conjunct is "
                         "read on the STORED column, which is the source §1's "
                         "Method names", dropped),
        "names_not_as_predicted": meas(bad if not dropped else None, total,
                                       "spawned-child task names that are NOT the "
                                       "predicted string, of the four on A plus "
                                       "the four on B; " + name_lens, dropped),
        "names_as_predicted": meas((total - bad) if not dropped else None, total,
                                   "spawned-child task names equal to the "
                                   "predicted string; " + name_lens, dropped),
        "spawn_tasks_a": meas(a.get("spawn_count"), a.get("task_count"),
                              "task streams on arm A whose name contains "
                              "`spawn@`, of every task stream in that trace"),
        "spawn_tasks_b": meas(b.get("spawn_count"), b.get("task_count"),
                              "task streams on arm B whose name contains "
                              "`spawn@`, of every task stream in that trace"),
        "stored_hash_pairs_differing": meas(
            pairs_differing, len(e.get("a_multiset") or []),
            "of the four (name, hash) pairs, those whose HASH component differs "
            "between A and B; " + hash_lens,
            dropped),
        "stored_multiset_equal": e.get("multiset_equal"),
        "a_multiset": e.get("a_multiset"), "b_multiset": e.get("b_multiset"),
        "not_as_predicted": e.get("not_as_predicted"),
        "differ_tasks_line": ab.get("verdict_line") and next(
            (l for l in (ab.get("stdout") or "").splitlines()
             if l.startswith("tasks: ")), None),
        "differ_all_matched": ab.get("tasks_all_matched"),
        "names": {k: {"run": (n.get(k) or {}).get("run"),
                      "query": (n.get(k) or {}).get("query"),
                      "task_count": (n.get(k) or {}).get("task_count"),
                      "spawn_tasks": (n.get(k) or {}).get("spawn_tasks")}
                  for k in ("A", "B", "C")},
    }


def _e5prime_coverage(raw: dict) -> dict:
    """E5'-coverage: units that fell back to the real tree, across the arms."""
    cov = raw.get("coverage_endpoint") or {}
    am = raw.get("arm_manifests") or {}
    per_arm = cov.get("per_arm_fell_back") or {}
    n = sum((v.get("units_seen") or 0) for v in am.values())
    written = sum((v.get("units_written_during_this_arm") or 0) for v in am.values())
    lens = (f"`fell_back: true` over the manifests each arm's build left in "
            f"`<target>/sensorium/manifests/`, snapshotted the moment that arm's "
            f"build returned; the directory was cleared before arm A, so no "
            f"rung-2 manifest can enter the count. n counts unit-manifests read "
            f"across the three arms ({written} of them written by the arm that "
            f"read them; the rest were units cargo found fresh and did not "
            f"recompile, so no new manifest was written for them)")
    return {
        "headline": meas(cov.get("units_fell_back"), n, lens,
                         cov.get("dropped") or []),
        "units_fell_back": meas(cov.get("units_fell_back"), n, lens,
                                cov.get("dropped") or []),
        "per_arm_fell_back": per_arm,
        "units_seen_per_arm": cov.get("units_seen"),
        "unit_manifests_written_by_their_own_arm": written,
        "unreached_reasons": cov.get("unreached_reasons"),
        "spawn_sites_wrapped_per_arm": {
            k: (v.get("read_manifests_summary") or {}).get("spawns_wrapped")
            for k, v in am.items()},
        "spawn_sites_declared_unwrapped_per_arm": {
            k: len((v.get("read_manifests_summary") or {}).get("spawns_declared")
                   or []) for k, v in am.items()},
        "unreached_files_per_arm": {
            k: (v.get("read_manifests_summary") or {}).get("unreached_files")
            for k, v in am.items()},
        "units": {k: [{"crate_name": u["crate_name"],
                       "crate_type": u["crate_type"],
                       "fell_back": u["fell_back"],
                       "fallback_reason": u["fallback_reason"],
                       "files": u["files"], "sites": u["sites"],
                       "spawns": len(u["spawns"]),
                       "written_during_this_arm": u["written_during_this_arm"]}
                      for u in (v.get("units") or [])]
                  for k, v in am.items()},
    }


def assemble_e5prime(raw: dict) -> dict:
    """Raw E5' facts -> the E5' document's `results.json`.

    Same shape and same rules as `assemble`: every measurement is
    {value, n, lens, dropped}, a null value with a reason is the ONLY
    not-measured, and 0 is measured-and-zero. Nothing here decides a verdict;
    §4 of the E5' document is written by hand against §1's rules."""
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null value "
                   "plus a dropped reason is the ONLY not-measured; 0 is "
                   "measured-and-zero"),
        "acceptance": E5PRIME_DOC,
        "runner": raw.get("runner"),
        "byte_lock": raw.get("byte_lock"),
        "pins": raw.get("pins"),
        "environment": _e5prime_env(raw),
        "endpoints": {"E5prime": _e5prime_main(raw),
                      "E5prime_names": _e5prime_names(raw),
                      "E5prime_coverage": _e5prime_coverage(raw)},
        "reported": {
            "arm_walls_s": {k: (v or {}).get("wall")
                            for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                         or {}).items()},
            "arm_events": {k: (v or {}).get("events")
                           for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                        or {}).items()},
            "arm_threads": {k: (v or {}).get("threads")
                            for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                         or {}).items()},
            "arm_tests": {k: len((v or {}).get("tests") or [])
                          for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                       or {}).items()},
            "arm_run_lines": raw.get("arm_run_lines"),
            "ab_plain_verdict": ((raw.get("raw_e5") or {}).get("diffs")
                                 or {}).get("ab_plain", {}).get("verdict"),
            "ac_task_verdict": ((raw.get("raw_e5") or {}).get("diffs")
                                or {}).get("ac_task", {}).get("verdict"),
        },
        "cleanup": raw.get("cleanup"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"),
        "error": raw.get("error"),
        "started": raw.get("started"),
        "finished": raw.get("finished"),
    }
