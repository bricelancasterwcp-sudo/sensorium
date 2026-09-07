"""The E9 acceptance TOOLING, tested without the box.

Nothing here runs cargo, the driver or the query CLI, opens the clone, reads
anything under `/mnt`, or needs an environment variable to be set by whoever
launched pytest. The only real files it opens are this repository's own: the
acceptance document (for the byte-lock) and the instrument's modules (for the
path scan).

What it tests is the places an E9 run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock — a lock that compared the wrong slice, that passed on a
  changed §1, or that fell through while `BYTE_LOCK` is `None`, lets an
  endpoint move after a number is read;
* none-versus-zero — a phase that did not run is `null` with a reason, a
  killed recording or reader publishes nulls with the kill as the reason, and
  no cell is ever filled from §1's predictions, which are the numbers already
  in the room;
* the locations the run touches, each one an environment variable, refused
  together when missing and refused when a fresh one is not fresh;
* each phase's log root in ITS OWN namespace — the wiring the entry slice's
  first launch died on.

The parsers and the sqlite joins are in `tests/test_acceptance_e9_read.py`;
the schema and the renderer are in `tests/test_acceptance_e9_record.py`. Each
mirrors the module it tests, and this file was split along that seam when it
reached the repository's 800-line ceiling.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_e9 as runner                                     # noqa: E402
import acceptance_e9_phases as phases                              # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

# Importing this runner re-points the SHARED log pointers at THIS document's
# workspace (its job). The sibling suites assert the same invariant for THEIR
# runners and all of them are imported at COLLECTION time, so whichever
# pytest collected last would own the pointer. Restoring E6‴'s pointers here
# makes every suite order-independent and costs nothing: each phase runs
# inside a `logs_at` block.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS

#: The locked range's sha256 at the AMENDED lock (`ffaed19`) -- what the
#: runner refuses on -- and at the ORIGINAL lock (`a4264b5`), carried beside
#: it so the amendment is a checkable fact rather than a claim.
DOC_SHA = "473f86203189bede2b56b19068770dbedba34f012b2c4a7f79012593d8960163"
ORIGINAL_DOC_SHA = ("15f0537587f55ec949a60c86543e6c4e1f7a0929cc57eb4a1"
                    "5320424185b67a5")

INSTRUMENT = ("acceptance_e9.py", "acceptance_e9_cells.py",
              "acceptance_e9_phases.py", "acceptance_e9_read.py",
              "acceptance_e9_schema.py", "render_e9.py")


# -- the byte-lock ---------------------------------------------------------


def _require_lock_commits(*shas):
    """The lock tests read `git show <sha>:<doc>`; a shallow checkout has no
    such commit. Skip BY NAME rather than pass on a missing commit — a
    skipped lock check must never look like a passed one."""
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) — the "
                        "byte-lock test is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) — skipped BY NAME, not passed")


def test_the_runner_carries_BOTH_locks():
    """The two facts the whole pre-registration hangs on.

    `BYTE_LOCK` is what the runner refuses on -- the AMENDED §1, whose §1.4
    lens names the reader the instrument runs (`flow --limit 1000`, R-F13).
    `ORIGINAL_LOCK` is Task 0's commit, before the instrument existed. Both
    are carried so the amendment is visible in the record; a runner that
    dropped the original would make a post-lock edit indistinguishable from
    no edit at all, and one that refused on the original would refuse on the
    document as it now stands."""
    assert runner.BYTE_LOCK == "ffaed19"
    assert runner.ORIGINAL_LOCK == "a4264b5"
    assert runner.BYTE_LOCK != runner.ORIGINAL_LOCK


def test_the_e9_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a
    stray edit to §1 is caught before a run is launched rather than by a
    refusal with a clone already built."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_sha256"] == DOC_SHA


def test_the_e9_record_carries_both_shas_and_the_amendment_flag():
    """§1.4's lens was amended after the original lock and before any number
    was read. The record must say so with two shas and a flag: a record that
    reported no amendment would be describing another document, and one that
    referenced a footnote would have a hole at exactly the sentence the lock
    exists to pin."""
    _require_lock_commits(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is True
    assert rec["locked_sha256"] == rec["section1_sha256"] == DOC_SHA
    assert rec["original_lock_sha256"] == ORIGINAL_DOC_SHA
    assert rec["original_lock"] == "a4264b5"
    # The amendment ADDED a paragraph; it did not shrink or replace §1.
    assert rec["amendment_bytes"] > 0
    assert rec["locked_bytes"] == (rec["original_lock_bytes"]
                                   + rec["amendment_bytes"])
    assert rec["footnotes_in_range"] == []


def test_the_amendment_moved_no_ROW_of_the_pre_registration():
    """The rule the amendment lives by: a lens may name the reader that was
    measured; an endpoint, a method or a derivation may not move after a
    lock. Every table row of §1 at the original lock is a row of §1 now --
    the four runs, H1-H7 with both readings, §1.1's 26 lines, §1.2's three
    triples and §1.3's two sightings, byte for byte."""
    _require_lock_commits(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)

    def rows(sha):
        rel = runner.DOC.relative_to(REPO).as_posix()
        text = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                              capture_output=True, text=True).stdout
        return [ln for ln in rung3.locked_range(text).splitlines()
                if ln.startswith("|")]

    before, after = rows(runner.ORIGINAL_LOCK), rows(runner.BYTE_LOCK)
    assert before == after, "a row moved after the lock"
    # A row count, so a comparison of two EMPTY lists could not pass: the
    # four runs, H1-H7, §1.1's table, §1.2's triples and §1.3's sightings.
    assert len(after) > 50, len(after)


def test_the_amendment_is_ONE_dated_paragraph_and_nothing_else():
    """What R-F13 permits is a dated lens paragraph. A diff that also touched
    a sentence of §1.4's rules -- or anything outside §1 -- would be an
    endpoint moving under cover of a lens note."""
    _require_lock_commits(runner.BYTE_LOCK, runner.ORIGINAL_LOCK)
    rel = runner.DOC.relative_to(REPO).as_posix()
    diff = subprocess.run(
        ["git", "diff", f"{runner.ORIGINAL_LOCK}..{runner.BYTE_LOCK}", "--",
         rel], cwd=REPO, capture_output=True, text=True).stdout
    removed = [ln for ln in diff.splitlines()
               if ln.startswith("-") and not ln.startswith("---")]
    added = [ln for ln in diff.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    assert removed == [], removed
    assert added, "the amendment changed nothing"
    assert any("Amended 2026-09-06" in ln for ln in added), added
    assert any("--limit 1000" in ln for ln in added), added


def test_the_e9_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself. A check that computes two shas, reports them
    unequal and proceeds is not a lock."""
    text = runner.DOC.read_text()
    doc = tmp_path / "e9.md"
    doc.write_text(text.replace("N = 26", "N = 27", 1))
    assert doc.read_text() != text, "the fixture did not change a byte"
    with pytest.raises(Refused) as e:
        rung3.byte_lock_check(doc, runner.BYTE_LOCK, runner.ORIGINAL_LOCK,
                              read_committed=lambda rel, c: text)
    assert "differs from the byte-lock" in str(e.value)


def test_an_unset_lock_REFUSES_rather_than_measuring(monkeypatch):
    """A `None` lock must stop the run. Falling through would measure
    against a pre-registration that can still be edited — which is the
    whole failure the lock exists to prevent."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked yet" in str(e.value)


# -- the locations ---------------------------------------------------------


def test_every_missing_location_is_named_in_ONE_refusal(monkeypatch):
    """One launch must report all of them. A preflight that refused on the
    first would cost five launches to discover five unset variables."""
    for key in runner.E9_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_e9()
    for key in runner.E9_ENV:
        assert key in str(e.value)


def test_the_five_locations_are_the_ones_the_run_touches(monkeypatch,
                                                         tmp_path):
    """Each variable lands under the key the phases resolve, and no location
    is compiled in. A key that did not match would send a recording into the
    wrong target while every command still succeeded."""
    for key, name in runner.E9_ENV.items():
        monkeypatch.setenv(key, str(tmp_path / name))
    p = runner.env_paths_e9()
    assert set(p) == set(runner.E9_ENV.values())
    assert p["sensorium_dir"] == tmp_path / "sensorium_dir"
    assert p["sensorium_bloomery"] == tmp_path / "sensorium_bloomery"
    assert p["sensorium_e9_target"] == tmp_path / "sensorium_e9_target"


def test_a_fresh_location_that_is_not_fresh_is_REFUSED(tmp_path):
    """§1.4 says FRESH. A warm target would record H2's build against
    another run's artifacts and a warm store could answer with another run's
    trace."""
    d = tmp_path / "warm"
    d.mkdir()
    (d / "leftover").write_text("x")
    with pytest.raises(Refused) as e:
        runner._require_fresh(d, "SENSORIUM_DIR")
    assert "not empty" in str(e.value)
    # and an absent one is created rather than refused
    runner._require_fresh(tmp_path / "cold", "SENSORIUM_DIR")
    assert (tmp_path / "cold").is_dir()


def test_the_corpus_target_is_derived_from_an_env_var_when_unset(
        monkeypatch, tmp_path):
    """§1.4 requires H7's corpus target to be FRESH but names no variable
    for it. The derived default must still be a location the environment
    chose — a constant here would be a box path in the instrument."""
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    paths = {"sensorium_e9_target": tmp_path / "t"}
    cfg = runner.e9_config(paths)
    assert cfg["corpus_target"] == tmp_path / "t-corpus"
    assert cfg["corpus_target_from_env"] is False
    monkeypatch.setenv("SENSORIUM_CORPUS_TARGET", str(tmp_path / "named"))
    cfg = runner.e9_config(paths)
    assert cfg["corpus_target"] == tmp_path / "named"
    assert cfg["corpus_target_from_env"] is True


def test_the_config_records_TMPDIR_as_observed(monkeypatch, tmp_path):
    """§1.4: `TMPDIR` is EXPECTED unset and RECORDED as observed. A config
    that assumed it was unset would build W1/W3/S1/S2 against the wrong
    prefix and report four MISSES on a correct recorder."""
    paths = {"sensorium_e9_target": tmp_path / "t"}
    monkeypatch.delenv("TMPDIR", raising=False)
    cfg = runner.e9_config(paths)
    assert cfg["tmpdir_observed"] is None and cfg["temp_root"] == "/tmp"
    monkeypatch.setenv("TMPDIR", "/scratch")
    cfg = runner.e9_config(paths)
    assert cfg["tmpdir_observed"] == "/scratch"
    assert cfg["temp_root"] == "/scratch"
    assert phases.watch_triples(cfg)[0]["expr"] == (
        'dir == "/scratch/bloomery-pager-contract"')
    assert phases.flow_sightings(cfg)[1]["literal"] == (
        "/scratch/bloomery-pager-contract2/j.jsonl")


def test_a_driver_outside_a_cargo_profile_directory_is_REFUSED(tmp_path,
                                                               monkeypatch):
    """§1.4 has the runner BUILD the driver. The profile is read from the
    binary's own parent so the build lands where `SENSORIUM_DRIVER` points;
    a path that names no profile would otherwise refresh the OTHER profile
    and report `rebuilt: False` about a stale binary — the pre-repair-binary
    trap of the E6⁗ record.

    `run` is replaced with a raise, so the refusal must happen BEFORE any
    command is issued: a check that ran cargo first and refused afterwards
    would have spent a build on a path it was going to reject, and this
    suite would no longer be box-free."""
    def no_commands(*a, **k):
        raise AssertionError("the refusal must precede every command")

    monkeypatch.setattr(runner, "run", no_commands)
    d = tmp_path / "somewhere"
    d.mkdir()
    (d / "cargo-sensorium").write_text("")
    with pytest.raises(Refused) as e:
        runner.build_driver_e9({"sensorium_driver": d / "cargo-sensorium"})
    assert "cargo profile" in str(e.value)


# -- the four runs ---------------------------------------------------------


def test_the_four_run_commands_are_exactly_ones_1_names(tmp_path):
    """The argv column of §1's run table. A `--focus` placed after the
    subcommand would be handed to cargo, and a focused run would record
    unfocused at exit 0 — the failure `parsed_focus` exists to catch."""
    p = {"sensorium_driver": tmp_path / "cargo-sensorium"}
    d = str(p["sensorium_driver"])
    assert phases.argv_of(p, "U1") == [
        d, "sensorium", "test", "-p", "bloomery-daemon",
        "--test", "pager_obligation_test"]
    assert phases.argv_of(p, "F1") == [
        d, "sensorium", "--focus", phases.FOCUS_A, "test",
        "-p", "bloomery-daemon", "--test", "pager_obligation_test"]
    assert phases.argv_of(p, "U2") == [
        d, "sensorium", "test", "-p", "bloomery-daemon",
        "--test", "pager_codec_gate_test"]
    assert phases.argv_of(p, "F2") == [
        d, "sensorium", "--focus", phases.FOCUS_B, "test",
        "-p", "bloomery-daemon", "--test", "pager_codec_gate_test"]


def test_the_recording_environment_re_adds_only_what_1_names(tmp_path):
    """§1.4 leaves `SENSORIUM_TIER` at its default and does NOT silence the
    audit log. `plain_env()` strips every `SENSORIUM_*`, so a variable put
    back here is the only way either could be set — and an inherited
    `CARGO_TARGET_DIR` would build somewhere the record does not name."""
    p = {"sensorium_e9_target": tmp_path / "t",
         "sensorium_dir": tmp_path / "s"}
    env = phases.record_env(p)
    assert env["CARGO_TARGET_DIR"] == str(tmp_path / "t")
    assert env["SENSORIUM_DIR"] == str(tmp_path / "s")
    assert "SENSORIUM_TIER" not in env
    assert "SENSORIUM_NO_INVOCATION_LOG" not in env
    assert [k for k in env if k.startswith("SENSORIUM_")] == ["SENSORIUM_DIR"]


def test_the_test_binarys_process_is_picked_by_a_stated_rule():
    """A `cargo test --test <t>` can leave more than one converted process
    behind, and every number is about the test binary. Picking silently
    would let a build script's trace answer H1's LINE count."""
    lines = [{"run": "a", "exe": "/t/debug/deps/build-script-build",
              "events": 900},
             {"run": "b", "exe": "/t/debug/deps/pager_obligation_test-9f",
              "events": 12}]
    got = phases.pick_run(lines, "pager_obligation_test")
    assert got["run"] == "b"
    assert "exe basename" in got["rule"]
    # and when no exe says so, the fallback NAMES itself
    fb = phases.pick_run(lines, "other_test")
    assert fb["run"] == "a" and fb["rule"].startswith("FALLBACK")
    assert phases.pick_run([], "x")["run"] is None


def test_H5_asks_flow_for_a_page_big_enough_to_hold_the_answer(tmp_path,
                                                               monkeypatch):
    """§1.3 spells `flow <run> --value <literal>` with no `--limit`, and the
    CLI's default page is 50. Every H5 number is read off the PRINTED rows,
    so the command as spelled would gate on part of an answer whenever the
    literal is sighted more than fifty times — and the page guard would then
    have to null a gate that a bigger page would have measured."""
    asked = []
    monkeypatch.setattr(phases, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(phases, "_read", lambda p, args, tag, cfg: (
        asked.append(args) or {"rc": 0, "out": "sightings: 0 event(s), "
                               "0 capture(s)\n", "err": "", "wall": 0.0,
                               "log": "l", "timed_out": False,
                               "command": "sensorium " + " ".join(args),
                               "kill_s": 120}))
    monkeypatch.setattr(phases, "has_trace", lambda *a, **k: True)
    records = {"runs": {"F1": {"run": "r", "timed_out": False, "rc": 0}}}
    phases.phase_h5({}, {"temp_root": "/tmp", "flow_limit": 1000,
                         "reader_timeout": 120}, records)
    assert asked, "phase_h5 issued no command"
    for args in asked:
        assert "--limit" in args, args
        assert args[args.index("--limit") + 1] == "1000", args


def test_a_run_line_without_a_trace_on_disk_is_a_DROP_and_not_a_crash(
        tmp_path):
    """A KILLED `cargo sensorium` can still have printed a `run:` line for a
    process the converter never finished writing, and
    `sqlite3.connect(..., mode=ro)` on a missing file RAISES — which would
    take the whole run down inside a phase and lose every endpoint already
    measured, instead of leaving a drop in the record."""
    paths = {"sensorium_dir": tmp_path / "store"}
    (tmp_path / "store" / "traces").mkdir(parents=True)
    assert phases.has_trace(paths, {"run": None}) is False
    assert phases.has_trace(paths, {"run": "20260906-x"}) is False
    (tmp_path / "store" / "traces" / "20260906-x.db").write_text("")
    assert phases.has_trace(paths, {"run": "20260906-x"}) is True


def test_the_watch_triples_and_sightings_are_ones_1_2_and_1_3_pin():
    """The predictions, spelled once. A triple whose predicted exit did not
    match its class would make H4's disagreement field meaningless."""
    cfg = {"temp_root": "/tmp"}
    ws = phases.watch_triples(cfg)
    assert [(t["id"], t["run"], t["predicted_class"], t["predicted_exit"],
             t["line"]) for t in ws] == [
        ("W1", "F1", "SATISFIED", 0, 251),
        ("W2", "F1", "NOTHING WAS CHECKED", 3, 282),
        ("W3", "F2", "not satisfied", 1, 22)]
    assert ws[1]["expr"] == "len(events) == 0"
    ss = phases.flow_sightings(cfg)
    assert [(s["id"], s["literal"], s["line"]) for s in ss] == [
        ("S1", "/tmp/bloomery-pager-contract", 251),
        ("S2", "/tmp/bloomery-pager-contract2/j.jsonl", 264)]


def _table_from_the_locked_document() -> dict:
    """§1.1's per-line table, read out of the LOCKED document.

    The `awk '/^### 1.1/,/^### 1.2/'` slice, then the `| <line> | … | 1 |`
    rows: the header row (`| source line | … | + |`) and the total row
    (`| **N** | | **26** |`) do not match, because neither begins with a
    bare number."""
    import re
    text, keep, buf = runner.DOC.read_text(), False, []
    for line in text.splitlines():
        if line.startswith("### 1.1"):
            keep = True
        elif line.startswith("### 1.2"):
            break
        if keep:
            buf.append(line)
    rows = re.findall(r"^\| (\d+) \|.*\| (\d+) \|\s*$", "\n".join(buf),
                      re.M)
    return {int(ln): int(n) for ln, n in rows}


def test_the_expected_line_table_IS_1_1s_table_row_for_row():
    """N is 26 because §1.1 counted 26 specific lines, and the diff names
    lines against them. A constant retyped from prose can drift by one row
    and still sum to 26 — a `286 -> 285` typo would make H3 report a missing
    line and an unexpected one on a correct recorder, and read as the
    §3.1/§3.2 under-specification §1.1 accounts for.

    So the table is DERIVED from the byte-locked document here and asserted
    equal to the instrument's constant. The runner keeps the constant (it
    must not parse prose at run time, and the lock is what makes the constant
    trustworthy); this is the pin between them."""
    _require_lock_commits(runner.BYTE_LOCK)
    from_doc = _table_from_the_locked_document()
    assert len(from_doc) == 26, from_doc
    assert from_doc == runner.EXPECTED_BY_LINE
    assert sum(from_doc.values()) == runner.GATE_N == 26
    # the two lines §1.1 deliberately does NOT count -- the arms not taken
    assert 260 not in from_doc and 280 not in from_doc
    assert runner.ACCOUNTED_N == frozenset({25, 26, 27})


def test_the_derived_table_actually_reads_the_document():
    """The pin above is only worth anything if the derivation can fail. A
    regex that matched nothing would make `from_doc == EXPECTED_BY_LINE`
    an assertion about two empty dicts."""
    from_doc = _table_from_the_locked_document()
    assert from_doc, "the §1.1 slice yielded no rows"
    assert min(from_doc) == 250 and max(from_doc) == 300
    assert all(v == 1 for v in from_doc.values())


def test_a_kill_is_recorded_as_a_fact_and_not_raised(tmp_path, monkeypatch):
    """§1's kill criteria make a timed-out arm a recorded not-measured. A
    `TimeoutExpired` that escaped would take every later phase down with it
    and lose the endpoints already read to one slow command — and
    `acceptance_lib.run` writes its log only after the call returns, so a
    killed command otherwise leaves no evidence at all."""
    def killed(*a, **k):
        # BYTES, which is what `subprocess.run(text=True)` attaches on some
        # platforms; the branch that decodes them is the one that carried a
        # `LookupError` on a sibling runner.
        raise subprocess.TimeoutExpired(["cargo"], 3600, output=b"partial\n")

    monkeypatch.setattr(phases, "run", killed)
    monkeypatch.setattr(lib, "LOGS", tmp_path / "logs")
    res = phases.guarded(["cargo", "x"], tmp_path, "u1.log", {}, 3600, "U1")
    assert res["timed_out"] is True and res["rc"] is None
    assert res["out"] == "partial\n" and res["kill_s"] == 3600
    assert Path(res["log"]).is_file()
    assert "KILLED at 3600 s" in Path(res["log"]).read_text()


# -- the log root ----------------------------------------------------------


def test_the_runner_gives_the_phases_module_the_runs_log_root():
    """The wiring the entry slice's first detached launch died on: the
    phases open `logs_at(LOGS / "<phase>")` in the namespace they live in,
    and a front door that assigned only the shared pointers left that third
    name unset — a `NameError` fourteen seconds in, after the byte-lock and
    the preflight and before one number was measured."""
    assert phases.LOGS == runner.LOGS
    assert runner.LOGS == runner.BASE / "logs"
    # `acceptance_e6ppp.LOGS`/`BASE` are the FOURTH and FIFTH pointers —
    # `build_driver` and `logs_at` resolve them where they are defined — but
    # their runtime values belong to whichever runner was imported last at
    # collection time, so the assignment is asserted at the source rather
    # than at a value another suite owns.
    src = (REPO / "rust" / "tests" / "acceptance_e9.py").read_text()
    for assignment in ("lib.LOGS = LOGS", "ph.LOGS = LOGS",
                       "eph.LOGS = LOGS", "e6ppp.LOGS = LOGS",
                       "e6ppp.BASE = BASE"):
        assert src.count(assignment) >= 1, assignment


def test_the_phases_module_declares_the_name_and_owns_no_location():
    """The other half, where the runner's assignment cannot mask it: a FRESH
    load, with no front door to hand it a pointer. A default copied from
    `acceptance_lib.LOGS` would equal this run's root today by import order
    and silently stop doing so on any reorder."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "acceptance_e9_phases__fresh",
        REPO / "rust" / "tests" / "acceptance_e9_phases.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "LOGS" in vars(mod)
    assert mod.LOGS is None


def test_no_module_of_this_instrument_names_a_box_path():
    """Every location is an environment variable. A path compiled into the
    runner would make the record unreproducible and the file wrong on any
    other machine. The only box strings allowed anywhere are this test's own
    literals."""
    for name in INSTRUMENT:
        text = (REPO / "rust" / "tests" / name).read_text()
        assert "/mnt/" not in text, name
        assert "/home/" not in text, name


def _crate_test_files():
    """Every test file of every Rust crate, `golden*/` fixtures excluded.

    A fixture under `golden/` or `golden_focus/` is transformer OUTPUT compared
    byte for byte, so a string in one is data and not a location the suite
    would go looking for."""
    for pattern in ("rust/*/tests/**/*.rs", "rust/*/tests/**/*.py"):
        for path in sorted(REPO.glob(pattern)):
            if any(part.startswith("golden") for part in path.parts):
                continue
            yield path


def test_no_rust_crate_test_file_names_a_box_path():
    """The scan above reaches six instrument modules and nothing else, which is
    how a box path sat in `sensorium-transform/tests/census.rs` since `089768d`
    with no test able to see it (final review, item 6). This walks every crate's
    tests instead.

    Widening it is the coverage half of that debt; the neutral wording in
    `census.rs` is the other half, and neither alone would have caught the
    next one."""
    offenders = []
    for path in _crate_test_files():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if "/mnt/" in line or "/home/" in line:
                offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert not offenders, (
        "a box-local path in a committed test file makes the suite wrong on "
        "any other machine:\n" + "\n".join(offenders))


def test_the_widened_scan_actually_reaches_the_file_that_motivated_it():
    """A scan that matched nothing would pass for the wrong reason -- an empty
    walk is not a clean tree. `census.rs` is the file the debt named, so the
    walk has to contain it, and the walk has to be more than the instrument."""
    reached = {p.relative_to(REPO).as_posix() for p in _crate_test_files()}
    assert "rust/sensorium-transform/tests/census.rs" in reached
    assert len(reached) > len(INSTRUMENT)
    assert not any("/golden" in name for name in reached), reached


# -- fix round 1 -----------------------------------------------------------


def test_kill_1_is_a_COMPILE_failure_and_not_the_other_two():
    """§1's kill 1 is "a compile failure of a focused unit". A libtest
    failure (the unit compiled, ran and reported) and the driver's own
    `--focus` refusal (exit 2, printed before cargo is invoked at all) are
    different findings, and labelling either "a compile failure of a focused
    unit" would stop the rung on the wrong fact — a failing assertion in the
    clone's own suite, or a mistyped qualname.

    The discriminator is libtest's own summary line: a unit that printed one
    was compiled and run."""
    summary = [{"failed": 1, "libtest_secs": 1.0}]
    base = {"timed_out": False, "kill_s": 3600, "focus_refusal": None}

    # compiled and ran, one test failed -> NOT kill 1
    got = phases._outcome_class({**base, "rc": 101}, summary, {})
    assert got["outcome_class"] == phases.TEST_FAILURE
    assert "compiled and ran" in got["outcome_class_why"]

    # never ran: non-zero and NO summary line -> kill 1
    got = phases._outcome_class({**base, "rc": 101}, [], {})
    assert got["outcome_class"] == phases.COMPILE_FAILURE
    assert "never ran" in got["outcome_class_why"]

    # the driver refused the focus before cargo -> a third case
    got = phases._outcome_class({**base, "rc": 2}, [], {})
    assert got["outcome_class"] == phases.REFUSAL
    got = phases._outcome_class(
        {**base, "rc": 101,
         "focus_refusal": "REFUSED: --focus nope matches no function"},
        summary, {})
    assert got["outcome_class"] == phases.REFUSAL

    assert phases._outcome_class({**base, "rc": 0}, summary, {})[
        "outcome_class"] == phases.COMPLETED
    assert phases._outcome_class(
        {**base, "rc": None, "timed_out": True}, [], {})[
            "outcome_class"] == phases.KILLED


def test_libtest_time_is_None_when_no_summary_reported_one():
    """H6's first reading. `0.0` compares equal to a run that reported
    nothing and renders in §3 as "the focused binary took no time at all"."""
    from acceptance_e9_read import test_results
    rows = test_results("test result: ok. 1 passed; 0 failed; 0 ignored; "
                        "0 measured; 0 filtered out\n")
    assert rows and rows[0]["libtest_secs"] is None
    assert all(s["libtest_secs"] is not None for s in test_results(
        "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; "
        "0 filtered out; finished in 0.4s\n"))


def test_the_driver_build_goes_through_the_guard(tmp_path, monkeypatch):
    """A build that hits the hour ceiling must be a RECORDED `timed_out`
    with its partial output kept, not a `TimeoutExpired` raised out of the
    preflight — which leaves no log at all, because `acceptance_lib.run`
    writes its log after the call returns."""
    import subprocess as sp

    def killed(*a, **k):
        raise sp.TimeoutExpired(["cargo"], 3600, output=b"partial\n")

    monkeypatch.setattr(phases, "run", killed)
    monkeypatch.setattr(lib, "LOGS", tmp_path / "logs")
    # `build_driver_e9` opens `logs_at(LOGS / "built-from")` in the RUNNER's
    # namespace, so the run's own log root has to move too — otherwise this
    # box-free test writes its kill log into the real ledger.
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    d = tmp_path / "t" / "debug"
    d.mkdir(parents=True)
    (d / "cargo-sensorium").write_text("")
    with pytest.raises(Refused) as e:
        runner.build_driver_e9({"sensorium_driver": d / "cargo-sensorium"})
    assert "KILLED" in str(e.value)
    log = tmp_path / "logs" / "built-from" / "built-from.log.KILLED.log"
    assert log.is_file() and "KILLED at 3600 s" in log.read_text()


def test_a_REFUSED_run_assembles_nothing(tmp_path, monkeypatch):
    """A refusal measured NOTHING. Assembling would write a TRACKED
    `results.json` full of not-measured cells into `docs/`, where the next
    reader would take it for the record of a run and Task 8 would have to
    notice and delete it."""
    calls = []
    monkeypatch.setattr(runner, "assemble_only",
                        lambda *a, **k: calls.append("assemble"))
    monkeypatch.setattr(runner, "render_only",
                        lambda *a, **k: calls.append("render"))
    monkeypatch.setattr(runner, "BASE", tmp_path)
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner, "RAW", tmp_path / "raw.json")
    monkeypatch.setattr(runner, "check_byte_lock",
                        lambda: (_ for _ in ()).throw(Refused("no lock")))
    assert runner.main([]) == 3
    assert calls == [], "a refusal must assemble and render nothing"
    assert (tmp_path / "e9.FAILED").read_text().startswith("exit=3")
    # ...and the raw record and the marker ARE the evidence
    assert json.loads((tmp_path / "raw.json").read_text())["refused"]


def test_cleanup_reports_None_for_a_store_that_is_not_there(tmp_path):
    """`None` is "there is nothing there to count"; `0` is "counted, and
    zero". A store the run never created and one it created and left empty
    are different facts, and a 0 for both reports the first as the second."""
    paths = {"sensorium_bloomery": tmp_path / "clone",
             "sensorium_dir": tmp_path / "gone",
             "sensorium_e9_target": tmp_path / "gone2",
             "sensorium_driver": tmp_path / "no-driver"}
    (tmp_path / "clone").mkdir()
    cfg = {"corpus_target": tmp_path / "gone3"}
    c = runner.cleanup_e9(paths, cfg, {"clone_cargo_lock_sha256": None})
    assert c["store_bytes"] is None
    assert c["traces_recorded"] is None
    assert c["invocations_jsonl_lines"] is None
    assert c["e9_target_bytes"] is None and c["corpus_target_bytes"] is None
    assert str(tmp_path / "gone") in c["absent_after_the_run"]


def test_stdout_and_stderr_are_joined_with_a_newline():
    """`out + err` glues the last line of one to the first of the other:
    `…filtered out` + `focus: fill` becomes one line that neither regex
    matches, and both facts vanish from the record."""
    import re
    for name in ("acceptance_e9_phases.py",):
        text = (REPO / "rust" / "tests" / name).read_text()
        assert not re.search(r'\["out"\]\s*\+\s*\w+\["err"\]', text), name
