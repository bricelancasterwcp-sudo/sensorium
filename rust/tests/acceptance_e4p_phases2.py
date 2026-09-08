#!/usr/bin/env python3
"""E4′'s H4-H6: the shim census, `schema_version`, and what did not move."""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4p_read import shim_census                       # noqa: E402
from acceptance_e4p_rows import EXPECTED_SHIM_KEYS                # noqa: E402
from acceptance_e6ppp import logs_at, mark_load                   # noqa: E402
from acceptance_lib import REPO, plain_env, sha256_file, step     # noqa: E402

LOGS: Path | None = None

#: The two records whose renderers H5's second reading asks to print their
#: own `schema_version`, and the token each is expected to carry. The
#: expectation is a COMPARISON TARGET: the value published is what the
#: renderer printed, never this constant.
DRY_ASSEMBLE = (("e9", "e9/1"), ("e4", "e4/1"))


def phase_h4(paths, two: dict) -> dict:
    """H4: does the shim link?

    61 focused keys under `<CARGO_TARGET_DIR>/sensorium/shim/*`, and for
    every key the `st_ino` of its `cargo-sensorium` equal to the driver's.
    A distinct inode where a link was POSSIBLE -- same `st_dev`, so the
    fallback was not forced by a filesystem boundary -- is a finding, not a
    STOP, and is recorded with its count.

    The second reading is three numbers printed SEPARATELY: entries,
    distinct inodes, and bytes counted ONCE PER INODE. The byte total is
    never the sum of the per-entry sizes -- under R3 that would report 61
    copies of a binary that exists once, which is the measurement error this
    endpoint is about.
    """
    mark_load("H4")
    census = shim_census(paths["sensorium_e4p_target"],
                         paths["sensorium_driver"])
    measured = [r for r in two["refocuses"] if "not_run" not in r]
    linked = census.get("linked_to_the_driver")
    entries = census.get("entries")
    out = {
        "census": census,
        "expected_keys": EXPECTED_SHIM_KEYS,
        "keys": census.get("keys"),
        "entries": entries,
        "distinct_inodes": census.get("distinct_inodes"),
        "bytes_once_per_inode": census.get("bytes_once_per_inode"),
        "driver_inode": census.get("driver_inode"),
        "linked_to_the_driver": linked,
        "not_linked": census.get("not_linked"),
        "same_device": census.get("same_device"),
        "keys_as_predicted": census.get("keys") == EXPECTED_SHIM_KEYS,
        # The denominator is the KEYS, never the entries. §1's gate is "61
        # focused keys, and FOR EVERY KEY the `st_ino` of its
        # `cargo-sensorium` equals the driver's" -- and a key directory
        # holding no binary has no `st_ino` at all. Comparing `linked` to
        # `entries` drops that key out of the denominator and publishes
        # "every key linked" over a census that did not cover every key.
        "all_linked": (None if not census.get("exists") or entries is None
                       else linked == census.get("keys")),
        "entries_cover_every_key": census.get("entries_cover_every_key"),
        "keys_without_a_binary": census.get("keys_without_a_binary"),
        "refocuses_measured": len(measured),
    }
    # The finding branch, and the one condition §1.2 says disables it.
    if census.get("keys_without_a_binary"):
        # Told apart from a copy: an install that made the key directory
        # and could not put the binary in it (`4edd5c7`) is not R3 falling
        # back to a copy, and the two must not read the same.
        out["finding"] = (
            f"{len(census['keys_without_a_binary'])} shim key(s) hold NO "
            f"`cargo-sensorium` at all: {census['keys_without_a_binary']}. "
            "A key with no binary has no `st_ino`, so H4's gate -- for "
            "EVERY key -- is not met, and the key is counted in the "
            "denominator rather than dropped out of it")
    elif out["all_linked"] is False and census.get("same_device") is True:
        out["finding"] = (
            f"{len(census.get('not_linked') or [])} shim key(s) hold a "
            "DISTINCT inode from the driver on the same filesystem, where a "
            "hard link was possible: R3's fallback-to-copy was taken "
            "without a boundary forcing it")
    elif out["all_linked"] is False:
        out["finding"] = (
            "the shim and the driver are on different filesystems "
            f"(devices {census.get('devices')}), so R3's fallback was forced "
            "and §1.2's finding branch does not apply")
    else:
        out["finding"] = None
    out["as_predicted"] = bool(out["keys_as_predicted"]
                               and out["all_linked"]
                               and out["entries_cover_every_key"])
    step(f"H4: {out['keys']} key(s), {out['entries']} entr(ies), "
         f"{out['distinct_inodes']} distinct inode(s), "
         f"{out['bytes_once_per_inode']} byte(s) once per inode; linked "
         f"{linked}; finding={out['finding'] is not None}")
    return out


def phase_h5(raw_schema: str, assembled_schema: str) -> dict:
    """H5: is `schema_version` present?

    The GATE is this record's own two files: the raw record and the
    assembled record both carry `e4p/1`. The values passed in are what the
    runner and the assembler ACTUALLY stamped -- read back from the objects,
    never re-asserted here -- so a runner that stamped nothing publishes
    `None` and fails the gate rather than being papered over by a constant.

    The SECOND READING is a DRY ASSEMBLE: the E9 and E4 renderers are asked
    to print their own `schema_version` fields with no file written. Their
    committed `results.json` are NOT re-derived and are not expected to
    carry the field -- the R-F15/R-G15 precedent is that a derivation is
    STATED, never rewritten -- and that they predate it is recorded as a
    fact rather than repaired.
    """
    mark_load("H5")
    dry = {}
    for name, expected in DRY_ASSEMBLE:
        dry[name] = _dry_assemble(name, expected)
    out = {
        "raw_schema_version": raw_schema,
        "assembled_schema_version": assembled_schema,
        "expected": "e4p/1",
        "raw_as_predicted": raw_schema == "e4p/1",
        "assembled_as_predicted": assembled_schema == "e4p/1",
        "both_present": bool(raw_schema and assembled_schema),
        "dry_assemble": dry,
        "renderers_print_their_field": all(
            d.get("renderer_prints_it") for d in dry.values()),
        "committed_records_predate_the_field": {
            name: d.get("committed_carries_it") is False
            for name, d in dry.items()},
    }
    out["as_predicted"] = bool(out["raw_as_predicted"]
                               and out["assembled_as_predicted"])
    step(f"H5: raw={raw_schema} assembled={assembled_schema}; renderers "
         f"print their field={out['renderers_print_their_field']}")
    return out


def _dry_assemble(which: str, expected: str) -> dict:
    """One renderer's `schema_version`, with NOTHING written.

    The record is built in memory from the assembler's own output over a
    minimal raw stub, so the committed `results.json` is neither read as an
    input nor touched as an output. What the committed file carries is read
    separately and reported: the point of this reading is that the two files
    PREDATE the field, and a reading that repaired them would erase it.
    """
    out = {"record": which, "expected": expected, "assembler_stamps": None,
           "renderer_prints_it": None, "committed": None,
           "committed_carries_it": None, "error": None}
    try:
        module = __import__(f"acceptance_{which}_schema")
        renderer = __import__(f"render_{which}")
        assemble = getattr(module, f"assemble_{which}")
        record = assemble({"schema_version": expected})
        out["assembler_stamps"] = (record.get("assembled") or {}).get(
            "schema_version")
        out["schema_version"] = record.get("schema_version")
        record.setdefault("environment", {})
        record.setdefault("byte_lock", {})
        text = "\n".join(renderer.environment(record))
        out["sentence"] = next((ln for ln in text.splitlines()
                                if ln.startswith("**Schema.**")), None)
        # `and assembler_stamps == expected`, not the token's presence
        # alone: the stub is SEEDED with `expected`, so an assembler
        # stamping `e9/2` would print "re-derived under `e9/2` from a raw
        # written under `e9/1`" and the token would still be in the
        # sentence. The reading has to be about the assembler.
        out["renderer_prints_it"] = bool(
            out["sentence"] and out["assembler_stamps"] == expected)
        committed = REPO / "docs" / "superpowers" / "acceptance" / (
            Path(record["acceptance"]).with_suffix("").name + ".results.json")
        out["committed"] = str(committed)
        if committed.is_file():
            out["committed_carries_it"] = "schema_version" in _json.loads(
                committed.read_text())
    except Exception as e:                                     # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def phase_h6(paths, cfg) -> dict:
    """H6: did nothing else move? THIS repository, never the clone.

    Three commands, each with its own ceiling and its own log: the corpus
    collector over every case (R2's new `refocus_child_run` included), the
    whole Python suite, and `cargo test --workspace`. H6 runs LAST because
    `cargo test --workspace` shares the driver's target and could relink the
    binary every other phase measured with.
    """
    from acceptance_e4p_phases import guarded
    mark_load("H6")
    driver = str(paths["sensorium_driver"])
    py = str(REPO / ".venv" / "bin" / "python")
    with logs_at(LOGS / "h6"):
        step("H6(corpus): the collector over every case")
        corpus = guarded(
            [py, "corpus/run_corpus.py", "--json"], REPO, "h6-corpus.log",
            plain_env() | {"PYTHONDONTWRITEBYTECODE": "1",
                           "SENSORIUM_CARGO_SENSORIUM": driver,
                           "CARGO_TARGET_DIR": str(cfg["corpus_target"])},
            cfg["corpus_timeout"], "h6-corpus")
        step("H6(python): the whole suite")
        suite = guarded(
            [py, "-m", "pytest", "-q", "-p", "no:cacheprovider"], REPO,
            "h6-pytest.log",
            plain_env() | {"PYTHONDONTWRITEBYTECODE": "1",
                           "SENSORIUM_CARGO_SENSORIUM": driver},
            cfg["pytest_timeout"], "h6-pytest")
        step("H6(rust): cargo test --workspace")
        cargo = guarded(
            ["cargo", "test", "--workspace"], REPO / "rust", "h6-cargo.log",
            plain_env() | {"PYTHONDONTWRITEBYTECODE": "1",
                           "CARGO_TARGET_DIR":
                               str(paths["sensorium_rust_target"])},
            cfg["cargo_test_timeout"], "h6-cargo")
    try:
        parsed = _json.loads(corpus["out"])
    except (ValueError, TypeError):
        parsed = None
    tail = [ln for ln in "\n".join((suite["out"], suite["err"])).splitlines()
            if ln.strip()]
    summary = next((ln for ln in reversed(tail)
                    if " passed" in ln or " failed" in ln or " error" in ln),
                   None)
    results = [ln for ln in "\n".join(
        (cargo["out"], cargo["err"])).splitlines()
        if ln.startswith("test result:")]
    out = {
        "corpus": {"rc": corpus["rc"], "wall_s": round(corpus["wall"], 3),
                   "log": corpus["log"], "timed_out": corpus["timed_out"],
                   "command": corpus["command"],
                   "target": str(cfg["corpus_target"]), "json": parsed,
                   "cases": (parsed or {}).get("cases"),
                   "questions": (parsed or {}).get("questions"),
                   "failures": (parsed or {}).get("failures"),
                   "errors": (parsed or {}).get("errors"),
                   "skipped": (parsed or {}).get("skipped"),
                   # R2's new case, named: §8's H6 asks for it by name.
                   "refocus_child_run_present": _case_present(
                       parsed, "refocus_child_run")},
        "python": {"rc": suite["rc"], "wall_s": round(suite["wall"], 3),
                   "summary": summary, "log": suite["log"],
                   "timed_out": suite["timed_out"],
                   "command": suite["command"]},
        "cargo": {"rc": cargo["rc"], "wall_s": round(cargo["wall"], 3),
                  "result_lines": results, "log": cargo["log"],
                  "timed_out": cargo["timed_out"], "command": cargo["command"],
                  "target": str(paths["sensorium_rust_target"])},
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
    }
    out["all_green"] = (corpus["rc"] == 0 and suite["rc"] == 0
                        and cargo["rc"] == 0)
    step(f"H6: corpus rc {corpus['rc']} ({out['corpus']['cases']} cases); "
         f"pytest rc {suite['rc']} ({summary}); cargo rc {cargo['rc']}")
    return out


def _case_present(parsed, name: str):
    """Whether the corpus JSON names a case. `None` -- not `False` -- when
    the JSON could not be read at all: "the collector printed nothing" and
    "the case is missing" are different facts."""
    if not isinstance(parsed, dict):
        return None
    for key in ("cases", "case_names", "names"):
        value = parsed.get(key)
        if isinstance(value, list):
            return any(name in str(v) for v in value)
    return None


__all__ = ["LOGS", "DRY_ASSEMBLE", "phase_h4", "phase_h5", "phase_h6"]
