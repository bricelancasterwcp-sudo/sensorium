"""The E6⁗ acceptance TOOLING, tested without the box.

Nothing here runs cargo, touches the clone or a target, reads a real trace
that it did not itself build in `tmp_path`, or needs an environment variable
to be set by whoever launched pytest. What it tests is the places this run
could report a wrong number while every command it ran succeeded:

* the §1 byte-lock -- a lock that compared the wrong slice, that passed on a
  changed §1, or that fell through while `BYTE_LOCK` is still `None`, lets an
  endpoint move after a number is read;
* the three arms' identity -- A and WS differ only in the selector and the
  `--lib` tail; WS0 is WS under the BASE driver in its OWN target and trace
  store, and a control sharing either would be the repaired driver run
  against itself (design B5);
* the two prep builds -- each is one half of the flip diff, and they must not
  overwrite each other's log or each other's driver and target;
* the flip diff's arithmetic -- a transition mislabelled, a row present in
  one build only, or a named row missing and assumed flipped, each turns
  E-flip's gate into one that cannot fail;
* the provenance of every published number -- `source: "§1"` covers the five
  numbers §1 freezes and no sixth;
* none-versus-zero -- no arm's false-accusation count and no control verdict
  may ever be invented (§1 asks for a reading of the clone's source), and
  every null carries its reason.

Every test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_e6q as runner                                    # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused, driver_cmd                     # noqa: E402
from acceptance_schema_e6q import assemble_e6q                     # noqa: E402

# Importing the runner re-points the SHARED log pointers at THIS document's
# workspace (the runner's job; the reload test at the end pins it). But
# `tests/test_acceptance_e6ppp.py` asserts the SAME invariant for ITS runner
# and both modules are imported at COLLECTION time, so whichever pytest
# collected last would own the pointer and the sibling assertion would fail on
# collection order alone. Restoring E6‴'s pointers here makes both suites
# order-independent and costs nothing: every phase runs inside a `logs_at`.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS


# -- the byte-lock on the new document -------------------------------------


def _require_lock_commits(*shas):
    """The real-document lock tests read `git show <sha>:<doc>`; a shallow
    checkout (CI at depth 1, a `--depth` clone) has no such commit, and before
    Task 4's Step 7 there is no lock sha at all. Skip BY NAME rather than pass
    on a missing commit -- a skipped lock check must never look like a passed
    one."""
    import subprocess
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) -- the "
                        "byte-lock test is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) -- the byte-lock test is skipped "
                        "BY NAME, not passed")


def test_the_e6q_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a stray
    edit to §1 is caught before a run is launched rather than by a refusal
    with a target already emptied."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True


def test_the_e6q_lock_is_one_sha_and_records_no_amendment():
    """§1 of THIS document is committed once and never amended. E6‴'s §1 was
    amended (dated, pre-measurement) and carries two shas; a record that
    silently reported an amendment here would be describing another
    document."""
    _require_lock_commits(runner.BYTE_LOCK)
    assert runner.ORIGINAL_LOCK is None
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    # No footnote is referenced by this §1, so the extended range and §1 are
    # the same bytes -- asserted, because a footnote added later would
    # silently widen the locked range.
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"]


def test_the_e6q_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself, on THIS document. A check that computes two
    shas, reports them unequal and proceeds is not a lock."""
    if not runner.DOC.is_file():
        pytest.skip("the acceptance document does not exist yet (§1 is "
                    "committed ALONE by a later step) -- skipped BY NAME, "
                    "not passed")
    text = runner.DOC.read_text()
    moved = text.replace("**0 false accusations**", "**1 false accusations**",
                         1)
    assert moved != text
    doc = tmp_path / "doc.md"
    doc.write_text(moved)
    with pytest.raises(rung3.Refused):
        rung3.byte_lock_check(doc, "aaaaaaa", None, lambda rel, commit: text)


def test_the_runner_REFUSES_to_measure_while_section_1_is_unlocked(
        monkeypatch):
    """Between Step 6 and Step 8 of the acceptance-tooling task the runner
    exists and §1 does not. A `None` lock that fell through to "no commit to
    compare with, carry on" would measure against a pre-registration that
    could still be edited -- which is the one thing the lock exists to
    prevent."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked" in str(e.value)


# -- the three arms --------------------------------------------------------


def _paths(tmp_path) -> dict:
    return {"sensorium_driver": tmp_path / "cargo-sensorium",
            "sensorium_dir": tmp_path / "sdir",
            "sensorium_acceptance_target": tmp_path / "target",
            "sensorium_bloomery_clone": tmp_path / "clone",
            "sensorium_base_driver": tmp_path / "base" / "cargo-sensorium",
            "sensorium_base_worktree": tmp_path / "base-worktree",
            "sensorium_control_target": tmp_path / "target-control"}


def test_the_two_head_arms_differ_only_in_the_selector_and_the_lib_tail(
        tmp_path):
    """A WS arm that quietly kept `--lib` would measure E6‴-W again -- the arm
    that reached 2 of 29 blast-radius arms -- and the shapes B1 repairs live
    behind the integration tests `--lib` does not run."""
    p = _paths(tmp_path)
    a = driver_cmd(p, *runner.ARM_A["selector"], *runner.ARM_A["tail"])
    ws = driver_cmd(p, *runner.ARM_WS["selector"], *runner.ARM_WS["tail"])
    assert a[-3:] == ["-p", "bloomery-daemon", "--lib"]
    assert ws[-1:] == ["--workspace"] and "--lib" not in ws
    assert a[:-3] == ws[:-1]


def test_the_control_arm_is_the_ws_arm_under_the_base_driver_in_its_own_target_and_store(
        tmp_path):
    """Design B5: the SAME command under the PRE-repair driver. Sharing the
    acceptance target would run test binaries the HEAD driver compiled (the
    transformer's output is baked in); sharing the trace store would let the
    sweep read the other arm's processes."""
    p = _paths(tmp_path)
    ws = runner.arm_paths_for(p, runner.ARM_WS)
    ws0 = runner.arm_paths_for(p, runner.ARM_WS0)
    assert runner.ARM_WS0["selector"] == runner.ARM_WS["selector"]
    assert runner.ARM_WS0["tail"] == runner.ARM_WS["tail"]
    assert ws0["sensorium_driver"] == p["sensorium_base_driver"] != ws["sensorium_driver"]
    assert ws0["sensorium_acceptance_target"] == p["sensorium_control_target"] != ws["sensorium_acceptance_target"]
    assert ws0["sensorium_dir"] != ws["sensorium_dir"]


def test_a_head_arm_keeps_the_head_driver_and_the_acceptance_target(tmp_path):
    """The other direction of the same substitution: only the arm whose
    `driver` is `base` is moved. An `arm_paths_for` that moved every arm would
    measure the pre-repair driver three times and report it as the repair."""
    p = _paths(tmp_path)
    for arm in (runner.ARM_A, runner.ARM_WS):
        ap = runner.arm_paths_for(p, arm)
        assert ap["sensorium_driver"] == p["sensorium_driver"]
        assert ap["sensorium_acceptance_target"] == p["sensorium_acceptance_target"]
        assert ap["sensorium_dir"] == p["sensorium_dir"] / arm["label"]


def test_each_arm_records_into_its_own_trace_directory(tmp_path):
    p = _paths(tmp_path)
    dirs = {runner.arm_paths_for(p, a)["sensorium_dir"]
            for a in (runner.ARM_A, runner.ARM_WS, runner.ARM_WS0)}
    assert len(dirs) == 3
    assert all(d.is_dir() and d.parent == p["sensorium_dir"] for d in dirs)


# -- the environment the control needs -------------------------------------


def test_the_three_control_locations_are_refused_TOGETHER_when_unset(
        monkeypatch, tmp_path):
    """One launch reports every missing variable, not one per attempt
    (`env_paths`' own rule). A control launched with two of the three set
    would run the base driver into the ACCEPTANCE target."""
    for k in ("SENSORIUM_BLOOMERY_CLONE", "SENSORIUM_ACCEPTANCE_TARGET",
              "SENSORIUM_DIR", "SENSORIUM_DRIVER", "SENSORIUM_CENSUS_DRIVER",
              "SENSORIUM_PROBE_TARGET"):
        monkeypatch.setenv(k, str(tmp_path / k.lower()))
    for k in runner.CONTROL_ENV:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_e6q()
    for k in runner.CONTROL_ENV:
        assert k in str(e.value)


def test_the_control_locations_land_under_the_names_the_arms_read(
        monkeypatch, tmp_path):
    for k in ("SENSORIUM_BLOOMERY_CLONE", "SENSORIUM_ACCEPTANCE_TARGET",
              "SENSORIUM_DIR", "SENSORIUM_DRIVER", "SENSORIUM_CENSUS_DRIVER",
              "SENSORIUM_PROBE_TARGET"):
        monkeypatch.setenv(k, str(tmp_path / k.lower()))
    for k in runner.CONTROL_ENV:
        monkeypatch.setenv(k, str(tmp_path / k.lower()))
    p = runner.env_paths_e6q()
    for k, name in runner.CONTROL_ENV.items():
        assert p[name] == tmp_path / k.lower()


# -- the base driver's identity --------------------------------------------


def _base_driver(tmp_path):
    d = tmp_path / "base" / "cargo-sensorium"
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_bytes(b"not really a driver")
    return d


def test_the_base_driver_is_verified_by_its_worktrees_commit_never_by_running_it(
        tmp_path):
    """`cargo-sensorium` has no `--version` flag (measured at Task 0): a runner
    that invoked the binary would crash or accept whatever it printed. The
    identity is the worktree's HEAD plus the binary's sha256; the version
    string is read AFTER the run, out of the trace the arm wrote."""
    p = _paths(tmp_path)
    p["sensorium_base_driver"] = _base_driver(tmp_path)
    p["sensorium_control_target"].mkdir()
    calls = []

    def fake_git(worktree, *args):
        calls.append(args)
        return runner.BASE_COMMIT + "e20353a8ef" if args[0] == "rev-parse" else ""

    rec = runner.verify_base_driver(p, git=fake_git)
    assert rec["head_matches"] is True and rec["clean"] is True
    assert rec["driver_sha256"] == lib.sha256_file(p["sensorium_base_driver"])
    assert rec["expected_commit"] == runner.BASE_COMMIT
    # Not one of the calls is an invocation of the binary itself.
    assert all(a[0] in ("rev-parse", "status") for a in calls)


def test_a_base_worktree_at_the_wrong_commit_is_REFUSED(tmp_path):
    """The control's whole claim is "this is the driver from before the
    repair". A worktree moved to another commit would make the control a
    second measurement of the new rule."""
    p = _paths(tmp_path)
    p["sensorium_base_driver"] = _base_driver(tmp_path)
    p["sensorium_control_target"].mkdir()
    with pytest.raises(Refused):
        runner.verify_base_driver(
            p, git=lambda wt, *a: ("deadbeefdeadbeef" if a[0] == "rev-parse"
                                   else ""))


def test_a_dirty_base_worktree_is_REFUSED(tmp_path):
    """A porcelain line means the built binary may not be that commit's."""
    p = _paths(tmp_path)
    p["sensorium_base_driver"] = _base_driver(tmp_path)
    p["sensorium_control_target"].mkdir()
    with pytest.raises(Refused):
        runner.verify_base_driver(
            p, git=lambda wt, *a: (runner.BASE_COMMIT + "e2"
                                   if a[0] == "rev-parse"
                                   else " M rust/src/lib.rs\n"))


def _trace_meta(paths, run_id, meta: dict):
    d = paths["sensorium_dir"] / "traces"
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / f"{run_id}.db")
    con.execute("create table meta (key text primary key, value text)")
    for k, v in meta.items():
        con.execute("insert into meta values (?,?)", (k, json.dumps(v)))
    con.commit()
    con.close()


def test_each_arms_driver_version_is_read_from_the_trace_that_arm_wrote(
        tmp_path):
    """The record must show `cargo-sensorium 0.3.0` for the control and the
    repaired version for the HEAD arms. The only place the driver says what it
    is, is the trace it wrote."""
    p = _paths(tmp_path)
    _trace_meta(p, "r1", {"driver_version": "cargo-sensorium 0.3.0",
                          "tool_hash": "abc"})
    got = runner.driver_identity(p, ["r1"])
    assert got["driver_versions"] == ["cargo-sensorium 0.3.0"]
    assert got["driver_version_per_run"] == {"r1": "cargo-sensorium 0.3.0"}
    assert got["traces_missing"] == []


def test_a_run_whose_trace_is_missing_reports_a_hole_not_a_version(tmp_path):
    p = _paths(tmp_path)
    got = runner.driver_identity(p, ["nope"])
    assert got["traces_missing"] == ["nope"]
    assert got["driver_versions"] == []


# -- the BEFORE/AFTER flip diff --------------------------------------------


def row(file, line, how) -> dict:
    """One `kind: "arm"` manifest row in `acceptance_e6ppp.arm_rows`' shape."""
    return {"file": file, "line": line, "qualname": "f", "hows": [how],
            "units": 1}


def test_flip_diff_counts_handled_to_ambiguous_and_names_every_other_transition():
    before = {"rows": [row("a.rs", 1, "arm_handled"), row("a.rs", 2, "arm_handled"),
                       row("b.rs", 3, "arm_propagate"), row("c.rs", 9, "arm_handled")]}
    after = {"rows": [row("a.rs", 1, "arm_ambiguous"), row("a.rs", 2, "arm_handled"),
                      row("b.rs", 3, "arm_propagate"), row("c.rs", 9, "arm_propagate"),
                      row("d.rs", 4, "arm_ambiguous")]}
    d = runner.flip_diff(before, after)
    assert d["changed_count"] == 2
    assert d["transitions"] == {"arm_handled->arm_ambiguous": 1, "arm_handled->arm_propagate": 1}
    assert d["only_handled_to_ambiguous"] is False
    assert d["only_before"] == [] and d["only_after"] == [{"file": "d.rs", "line": 4, "how": "arm_ambiguous"}]


def test_a_transition_out_of_arm_propagate_is_not_reported_as_one_out_of_arm_handled():
    """§1's gate is "no transition other than `arm_handled -> arm_ambiguous`".
    A diff that keyed every transition by the AFTER how, or that assumed the
    before how, would report a propagate -> ambiguous move -- a rule change
    the repair did not intend -- as the very transition the gate allows."""
    d = runner.flip_diff({"rows": [row("a.rs", 1, "arm_propagate")]},
                         {"rows": [row("a.rs", 1, "arm_ambiguous")]})
    assert d["transitions"] == {"arm_propagate->arm_ambiguous": 1}
    assert d["only_handled_to_ambiguous"] is False
    assert d["changed"][0]["before"] == "arm_propagate"


def test_a_diff_with_no_changed_row_is_not_a_passing_flip():
    """"Every changed row is handled -> ambiguous" over zero changed rows is
    vacuously true and would read as "the predicted flip happened". The cell
    says True only when there is at least one transition and every one of them
    is the allowed one."""
    d = runner.flip_diff({"rows": [row("a.rs", 1, "arm_handled")]},
                         {"rows": [row("a.rs", 1, "arm_handled")]})
    assert d["changed_count"] == 0
    assert d["only_handled_to_ambiguous"] is False


def test_flip_diff_reports_the_two_api_v1_rows_by_name():
    before = {"rows": [row("crates/bloomery-daemon/src/api_v1.rs", 396, "arm_handled"),
                       row("crates/bloomery-daemon/src/api_v1.rs", 515, "arm_handled")]}
    after = {"rows": [row("crates/bloomery-daemon/src/api_v1.rs", 396, "arm_ambiguous"),
                      row("crates/bloomery-daemon/src/api_v1.rs", 515, "arm_ambiguous")]}
    d = runner.flip_diff(before, after)
    assert d["named"]["crates/bloomery-daemon/src/api_v1.rs:396"] == {"before": "arm_handled", "after": "arm_ambiguous", "flipped": True}
    assert d["named_all_flipped"] is True


def test_a_named_row_missing_from_a_build_is_reported_not_assumed_flipped():
    d = runner.flip_diff({"rows": []}, {"rows": []})
    assert d["named"]["crates/bloomery-daemon/src/api_v1.rs:515"]["flipped"] is None
    assert d["named_all_flipped"] is False


def test_a_row_carrying_two_hows_is_reported_and_kept_out_of_the_transitions():
    """One `(file, line)` can be declared by two units. If they disagree about
    the `how` there is no single before-or-after class, and folding it into a
    transition would invent one."""
    before = {"rows": [{"file": "a.rs", "line": 1, "qualname": "f",
                        "hows": ["arm_handled", "arm_ambiguous"], "units": 2}]}
    after = {"rows": [row("a.rs", 1, "arm_ambiguous")]}
    d = runner.flip_diff(before, after)
    assert d["transitions"] == {} and d["changed_count"] == 0
    assert d["multi_how"] == [{"file": "a.rs", "line": 1, "side": "before",
                               "hows": ["arm_handled", "arm_ambiguous"]}]


def test_the_flip_set_feeds_the_committed_executed_vs_static_reader():
    """§1 reports which of the flipped arms EXECUTED, named one by one. The
    join is the committed E6‴ reader, so the flip rows are shaped for it
    rather than joined a second way."""
    flip = {"changed": [{"file": "src/a.rs", "line": 10, "qualname": "f",
                         "before": "arm_handled", "after": "arm_ambiguous"},
                        {"file": "src/z.rs", "line": 99, "qualname": "z",
                         "before": "arm_handled", "after": "arm_ambiguous"}]}
    ex = {"sites": [{"file": "/clone/src/a.rs", "line": 10,
                     "hows": ["arm_ambiguous"], "events": 3}],
          "distinct_sites": 1}
    got = e6ppp.executed_vs_static(runner.flip_resolved(flip), ex, "/clone")
    assert got["executed"] == 1 and got["static"] == 2
    assert [r["file"] for r in got["not_executed_rows"]] == ["src/z.rs"]


# -- the control's computed evidence ---------------------------------------


def test_control_lines_at_flipped_sites_is_computed_only_over_the_flip_set():
    flip = {"changed": [{"file": "crates/x/src/a.rs", "line": 5}]}
    parsed = [{"sink": "/clone/crates/x/src/a.rs:5"}, {"sink": "/clone/crates/x/src/a.rs:7"}, {"sink": None}]
    out = runner.lines_at_flipped_sites(parsed, flip, "/clone")
    assert out["count"] == 1 and out["unresolved"] == 1


def test_lines_at_flipped_sites_reads_the_sink_dict_the_collector_actually_writes():
    """`_sink_files` attaches the sink as a DICT, not a `"<file>:<line>"`
    string. A reader that understood one shape only would count 0 on the real
    record and read as "the control reached nothing" -- the strongest possible
    wrong answer for a discrimination control."""
    flip = {"changed": [{"file": "crates/x/src/a.rs", "line": 5}]}
    parsed = [{"sink": {"file": "/clone/crates/x/src/a.rs", "line": 5,
                        "qualname": "f"}},
              {"sink": {"file": "/clone/crates/x/src/b.rs", "line": 5}}]
    out = runner.lines_at_flipped_sites(parsed, flip, "/clone")
    assert out["count"] == 1 and out["unresolved"] == 0
    assert out["lines"][0]["file"] == "crates/x/src/a.rs"


def test_a_sink_outside_the_clone_root_is_counted_and_reported():
    """If the path shape ever changes, the join silently stops matching."""
    flip = {"changed": [{"file": "crates/x/src/a.rs", "line": 5}]}
    parsed = [{"sink": "/elsewhere/crates/x/src/a.rs:5"}]
    out = runner.lines_at_flipped_sites(parsed, flip, "/clone")
    assert out["count"] == 0
    assert out["not_under_the_clone_root"] == 1 and out["unresolved"] == 1


# -- the two prep builds ---------------------------------------------------


def test_each_prep_build_logs_under_its_OWN_directory(tmp_path, monkeypatch):
    """`phase_prep_build` re-points logging INSIDE itself, resolving
    `acceptance_e6ppp.LOGS` in ITS namespace. Left at this document's log
    root, BOTH preps write `logs/prep/prep-workspace.log`: the BASE prep (it
    runs second) destroys the HEAD prep's `cargo -v` log -- the evidence of
    which units that build compiled -- and the record publishes one file under
    two names. The wrapper binds the global and restores it."""
    seen = []

    def fake_prep(p, cfg):
        seen.append(e6ppp.LOGS)
        return {"build": {"log": str(e6ppp.LOGS / "prep" /
                                     "prep-workspace.log")}}

    monkeypatch.setattr(runner, "phase_prep_build", fake_prep)
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    before = e6ppp.LOGS
    p = _paths(tmp_path)
    head = runner._prep(p, {}, "head")
    base = runner._prep(p, {}, "base", runner.ARM_WS0)
    assert seen == [tmp_path / "logs" / "prep-head",
                    tmp_path / "logs" / "prep-base"]
    assert len(set(seen)) == 2
    assert head["build"]["log"] != base["build"]["log"]
    assert e6ppp.LOGS == before                      # restored, both times


def test_the_prep_wrapper_restores_the_shared_pointer_even_when_the_build_raises(
        tmp_path, monkeypatch):
    """A prep that raises must not leave every later phase logging into
    `prep-base/`."""
    def boom(p, cfg):
        raise RuntimeError("cargo died")

    monkeypatch.setattr(runner, "phase_prep_build", boom)
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    before = e6ppp.LOGS
    with pytest.raises(RuntimeError):
        runner._prep(_paths(tmp_path), {}, "head")
    assert e6ppp.LOGS == before


def test_the_two_preps_run_under_their_own_driver_and_target(tmp_path,
                                                             monkeypatch):
    """The BASE prep must build with the pre-repair driver into the control
    target: it is the BEFORE half of the flip diff, and a BEFORE built by the
    HEAD driver would make E-flip a diff of one build against itself."""
    seen = []
    monkeypatch.setattr(runner, "phase_prep_build",
                        lambda p, cfg: seen.append(
                            (p["sensorium_driver"],
                             p["sensorium_acceptance_target"])) or {})
    monkeypatch.setattr(runner, "LOGS", tmp_path / "logs")
    p = _paths(tmp_path)
    runner._prep(p, {}, "head")
    runner._prep(p, {}, "base", runner.ARM_WS0)
    assert seen == [(p["sensorium_driver"], p["sensorium_acceptance_target"]),
                    (p["sensorium_base_driver"], p["sensorium_control_target"])]


# -- the schema ------------------------------------------------------------


RAW_ARMS = {
    "raw_arm_a": {
        "swallowed_count": 3, "chains_in_scope": 9, "processes": 1,
        "union_swallowed_count": 3, "unparsed_swallowed": 0,
        "tally": {"swallowed": 3}, "tally_line": "dispositions: swallowed 3",
        "selector": ["-p", "bloomery-daemon"], "tail": ["--lib"],
        "driver_role": "head",
        "sweep": {"swallowed_count": 0, "processes_swept": 0, "swept": [],
                  "swallowed_parsed": []}},
    "raw_arm_ws": {
        "swallowed_count": 2, "chains_in_scope": 5, "processes": 40,
        "union_swallowed_count": 9, "unparsed_swallowed": 0,
        "tally": {"swallowed": 2}, "tally_line": "dispositions: swallowed 2",
        "selector": ["--workspace"], "tail": [], "driver_role": "head",
        "sweep": {"swallowed_count": 7, "processes_swept": 39,
                  "swallowed_parsed": [{"unparsed": False}] * 7,
                  "swept": [{"tally_line": "dispositions: swallowed 3"},
                            {"tally_line": "dispositions: swallowed 4, "
                                           "ambiguous 2"}]}},
    "raw_arm_ws0": {
        "swallowed_count": 4, "chains_in_scope": 6, "processes": 40,
        "union_swallowed_count": 11, "unparsed_swallowed": 0,
        "tally": {"swallowed": 4}, "tally_line": "dispositions: swallowed 4",
        "selector": ["--workspace"], "tail": [], "driver_role": "base",
        "sweep": {"swallowed_count": 7, "processes_swept": 39,
                  "swallowed_parsed": [{"unparsed": False}] * 7,
                  "swept": []}},
}


def test_neither_ws_arms_false_accusation_count_is_ever_invented():
    doc = assemble_e6q({"raw_arm_a": {"swallowed_count": 3, "union_swallowed_count": 3}, "raw_arm_ws": {"swallowed_count": 1, "union_swallowed_count": 9}, "raw_arm_ws0": {"swallowed_count": 2, "union_swallowed_count": 11}})
    for k in ("E6qA", "E6qWS", "E6qWS0"):
        assert doc["endpoints"][k]["headline"]["value"] is None
        assert doc["endpoints"][k]["headline"]["dropped"]


def test_the_control_verdict_is_not_measured_until_the_hand_adjudication_is_pasted():
    doc = assemble_e6q({"raw_arm_ws0": {"swallowed_count": 0, "union_swallowed_count": 0}})
    assert doc["endpoints"]["E6qWS0"]["discriminating"]["value"] is None


def test_the_controls_computed_evidence_is_published_beside_its_null_verdict():
    """A null verdict with nothing beside it leaves the hand adjudication no
    numbers to work from: the COUNT is computed, the verdict is not."""
    doc = assemble_e6q({"raw_arm_ws0": {"swallowed_count": 4,
                                        "union_swallowed_count": 11},
                        "raw_flip_lines": {"ws0": {"count": 2, "lines": [],
                                                   "unresolved": 0,
                                                   "flip_sites": 11}}})
    m = doc["endpoints"]["E6qWS0"]["lines_at_flipped_sites"]
    assert m["value"] == 2 and m["dropped"] == []
    assert doc["endpoints"]["E6qWS0"]["discriminating"]["value"] is None


def test_the_flip_gate_cells_carry_the_frozen_delta_and_the_measured_count():
    doc = assemble_e6q({"raw_flip": {"changed_count": 7, "only_handled_to_ambiguous": True, "named_all_flipped": True}, "frozen_census": {"arms_handled_before": 65, "arms_handled_after": 58}})
    assert doc["endpoints"]["Eflip"]["changed_equals_delta"]["value"] is True
    assert doc["endpoints"]["Eflip"]["changed_equals_delta"]["n"] == 7


def test_the_flip_headline_counts_the_transitions_the_gate_forbids():
    doc = assemble_e6q({"raw_flip": {"changed_count": 3,
                                     "transitions": {
                                         "arm_handled->arm_ambiguous": 2,
                                         "arm_handled->arm_propagate": 1},
                                     "only_handled_to_ambiguous": False,
                                     "named_all_flipped": True},
                        "frozen_census": runner.FROZEN_CENSUS})
    e = doc["endpoints"]["Eflip"]
    assert e["headline"]["value"] == 1 and e["headline"]["n"] == 3
    assert e["changed_equals_delta"]["value"] is False


def test_a_flip_diff_without_a_transition_table_is_null_not_a_clean_zero():
    doc = assemble_e6q({"raw_flip": {"changed_count": 7,
                                     "only_handled_to_ambiguous": True}})
    h = doc["endpoints"]["Eflip"]["headline"]
    assert h["value"] is None and h["dropped"]


def test_the_frozen_census_is_the_five_numbers_section_1_actually_carries():
    """The delta the flip gate is taken against is FROZEN before the lock. A
    runner that re-derived it at run time would have no frozen denominator at
    all -- and a number stamped `source: "§1"` that §1 does not carry would
    give a ledger line the standing of a pre-registered pin."""
    assert runner.FROZEN_CENSUS == {
        "arms_handled_before": 65, "arms_handled_after": 54,
        "arms_escaped_before": 121, "arms_escaped_after": 132,
        "arm_sites": 225, "source": "§1"}
    assert (runner.FROZEN_CENSUS["arms_handled_before"]
            - runner.FROZEN_CENSUS["arms_handled_after"]) == 11
    # §1 freezes five numbers and no sixth.
    assert "arms_propagate" not in runner.FROZEN_CENSUS
    assert len(runner.FROZEN_CENSUS) == 6                # five + the source
    doc = (runner.DOC.read_text() if runner.DOC.is_file() else "")
    if doc:
        s1 = doc[doc.index("## 1. Pre-registration"):doc.index("\n## 2. ")]
        for k, v in runner.FROZEN_CENSUS.items():
            if k != "source":
                assert f"`{k} = {v}`" in s1, k
        assert "arms_propagate" not in s1


def test_the_census_number_section_1_does_not_freeze_carries_its_own_source():
    """`arms_propagate` is a T0/T1 ledger line, published beside the frozen
    five and never under their label."""
    assert runner.LEDGER_CENSUS["arms_propagate"] == 39
    assert "NOT frozen in §1" in runner.LEDGER_CENSUS["source"]
    doc = assemble_e6q({"frozen_census": runner.FROZEN_CENSUS,
                        "ledger_census": runner.LEDGER_CENSUS})
    env = doc["environment"]
    assert env["frozen_census"] == runner.FROZEN_CENSUS
    assert env["ledger_census"] == runner.LEDGER_CENSUS
    assert "arms_propagate" not in env["frozen_census"]


def test_the_schemas_arm_descriptions_match_the_runners_arms():
    """The schema names each arm's command in prose (it may not import the
    runner: the runner imports it). A drift between the two would put one
    command in the lens and another in the record."""
    import acceptance_schema_e6q as schema
    for key, arm in (("E6qA", runner.ARM_A), ("E6qWS", runner.ARM_WS),
                     ("E6qWS0", runner.ARM_WS0)):
        spec = schema.ARMS[key]
        assert spec["key"] == f"raw_arm_{arm['label']}"
        assert spec["selector"] == " ".join(arm["selector"])
        assert spec["tail"] == " ".join(arm["tail"])
        assert spec["driver"] == arm["driver"]


def test_the_union_is_the_primary_plus_the_sweep():
    doc = assemble_e6q(RAW_ARMS)
    ws = doc["endpoints"]["E6qWS"]
    assert ws["swallowed_lines"]["value"] == 2
    assert ws["sweep_swallowed_lines"]["value"] == 7
    assert ws["union_swallowed_lines"]["value"] == 9


def test_an_arm_that_swept_nothing_reports_null_not_a_measured_zero():
    doc = assemble_e6q(RAW_ARMS)
    a = doc["endpoints"]["E6qA"]["sweep_swallowed_lines"]
    assert a["value"] is None and a["n"] == 0
    assert any("0 of 0" in d for d in a["dropped"]), a["dropped"]


def test_the_guarded_arm_count_is_published_with_its_provenance():
    """Design B4 wants the guarded-arm count beside both readings. It RESTATES
    the hand adjudication §4.4 of this document carries (§5.3 repeats it), so
    an arm that RAN names that provenance and drops nothing, while an arm that
    never ran has nothing to restate and stays null with a reason."""
    doc, none = assemble_e6q(RAW_ARMS), assemble_e6q({})
    for key, want in (("E6qA", 2), ("E6qWS", 374), ("E6qWS0", 374)):
        g = doc["endpoints"][key]["guarded_arms"]
        assert g["value"] == want and g["dropped"] == []
        assert "§5" in g["provenance"]
        assert none["endpoints"][key]["guarded_arms"]["value"] is None


def test_a_phase_that_did_not_run_is_null_with_a_reason_never_zero():
    doc = assemble_e6q({})
    for key in ("E6qA", "E6qWS", "E6qWS0"):
        m = doc["endpoints"][key]["swallowed_lines"]
        assert m["value"] is None and m["dropped"]
    assert doc["endpoints"]["E6again"]["headline"]["value"] is None
    assert doc["endpoints"]["Eflip"]["changed_count"]["value"] is None
    assert doc["endpoints"]["E0ppp"]["headline"]["value"] is None


def test_e6again_and_e7q_and_e0ppp_are_the_committed_rung3_schema_not_copies():
    """§1 calls them "verbatim". A second schema would be a second protocol,
    free to disagree with the one the rung-3 and E6‴ records used."""
    from acceptance_schema_rung3 import _e0pp, _e6 as rung3_e6, _e7pp
    raw = {"raw_e6": {"cases": [{"case": "rust/x", "questions": [{
        "id": "q", "printed_swallowed_count": 1, "expected_swallowed": 1,
        "swallow_set_equal": True, "printed_tally": "dispositions: swallowed 1",
        "tally_pinned": "dispositions: swallowed 1", "tally_equal": True,
        "extra_swallowed_lines": [], "missing_swallow_groups": [],
        "swallow_set_nonempty_ok": True, "corpus_check_failures": [],
        "rc": 0, "expect_exit": 0, "printed_swallowed": ["SWALLOWED -- x"],
    }]}]},
        "raw_e7pp": {"ok": ["e7_a"], "fail": [], "skip": [], "rc": 0},
        "raw_e0ppp": {"kill_s": 60.0, "run": "r1", "arms": {
            "info": {"wall": 1.0, "under_ceiling": True},
            "diff": {"wall": 2.0, "under_ceiling": True}}}}
    doc = assemble_e6q(raw)
    assert doc["endpoints"]["E6again"] == rung3_e6(raw)
    assert doc["endpoints"]["E7q"] == _e7pp(raw)
    # E0‴ is the committed block with ONLY its lens rewritten (below).
    from acceptance_schema_e6q import E0_LENS_IS, E0_LENS_WAS
    got, want = doc["endpoints"]["E0ppp"], _e0pp({"raw_e0pp": raw["raw_e0ppp"]})
    assert set(got) == set(want)
    for k, v in want.items():
        if isinstance(v, dict) and isinstance(v.get("lens"), str):
            assert got[k] == dict(v, lens=v["lens"].replace(E0_LENS_WAS,
                                                            E0_LENS_IS))
        else:
            assert got[k] == v


def test_the_e0ppp_lens_names_the_trace_this_run_actually_read():
    """The rung-3 string says "the E6' trace". This run passes the E6⁗-WS
    arm's process with the most events, and a lens naming another document's
    arm would misdescribe every wall in the row."""
    doc = assemble_e6q({"raw_e0ppp": {"kill_s": 60.0, "run": "r1", "arms": {
        "info": {"wall": 1.0, "under_ceiling": True}}}})
    for k in ("headline", "info_wall_s", "diff_wall_s", "max_wall_s"):
        lens = doc["endpoints"]["E0ppp"][k]["lens"]
        assert "E6⁗-WS process with the most events" in lens, k
        assert "E6' trace" not in lens, k


def test_a_reported_cell_that_did_not_run_carries_its_reason_not_an_empty_list():
    """A `null` with an empty `dropped` renders as `not measured (no reason
    recorded)` — this module's own rule broken at the two cells that say how
    much of the tree each build declared and which flipped arms each arm
    reached."""
    rep = assemble_e6q({})["reported"]
    for key in ("prep_head", "prep_base"):
        m = rep[key]["arm_sites_distinct"]
        assert m["value"] is None and m["dropped"], key
    for label, e in rep["executed_flipped_arms"].items():
        assert e["executed"]["value"] is None and e["executed"]["dropped"], label
    # ... and a cell that DID run keeps its measured value with no reason.
    ran = assemble_e6q({"raw_prep_head": {"arms": {"distinct": 7}}})
    m = ran["reported"]["prep_head"]["arm_sites_distinct"]
    assert m["value"] == 7 and m["dropped"] == []


def test_the_renderer_prints_not_measured_rather_than_a_dash():
    """A dash in a results table is indistinguishable from a zero at a
    glance. The renderer must say what was not measured and why."""
    from render_e6q import results
    doc = assemble_e6q(RAW_ARMS)
    doc["acceptance"] = "x.md"
    text = "\n".join(results(doc))
    assert "not measured (adjudicated by hand" in text
    assert "E6⁗-A" in text and "E6⁗-WS" in text and "E6⁗-WS0" in text
    assert "not measured (decided by the hand adjudication" in text


def test_results_json_if_present_matches_the_committed_schema():
    """After the run, the published `results.json` must be reproducible from
    the raw record by the committed assembler -- not by a one-off script."""
    p = (REPO / "docs" / "superpowers" / "acceptance"
         / "2026-09-05-sensorium-rung3-e6q.results.json")
    if not p.is_file():
        pytest.skip("not measured yet")
    doc = json.loads(p.read_text())
    assert doc["acceptance"].endswith("2026-09-05-sensorium-rung3-e6q.md")
    assert set(doc["endpoints"]) == {"E6qA", "E6qWS", "E6qWS0", "Eflip",
                                     "E6again", "E7q", "E0ppp"}
    for key in ("E6qA", "E6qWS", "E6qWS0"):
        assert doc["endpoints"][key]["headline"]["value"] is None


# -- the shared log pointer ------------------------------------------------


def test_logs_at_moves_the_shared_log_directory_and_restores_it(tmp_path):
    before = lib.LOGS
    with runner.logs_at(tmp_path / "arm-ws"):
        assert lib.LOGS == tmp_path / "arm-ws"
        assert lib.LOGS.is_dir()
    assert lib.LOGS == before


def test_importing_the_runner_leaves_the_shared_log_pointer_on_THIS_document():
    """`acceptance_rung3` AND `acceptance_e6ppp` re-point
    `acceptance_lib.LOGS`/`LEDGER` in their module bodies, and
    `e6ppp.phase_prep_build` resolves `e6ppp.LOGS`/`BASE` in ITS namespace.
    All five must land on THIS document or a log lands beside another record
    (the E6‴ §2 lesson). Reloaded rather than read off the session, because
    the sibling suite asserts the same invariant and both modules are imported
    at collection time; the pointers are restored afterwards."""
    saved = (lib.LOGS, lib.LEDGER, ph.LOGS, e6ppp.LOGS, e6ppp.BASE)
    try:
        importlib.reload(runner)
        assert lib.LOGS == runner.LOGS
        assert lib.LEDGER == runner.LEDGER
        assert ph.LOGS == runner.LOGS
        assert e6ppp.LOGS == runner.LOGS
        assert e6ppp.BASE == runner.BASE
    finally:
        lib.LOGS, lib.LEDGER, ph.LOGS, e6ppp.LOGS, e6ppp.BASE = saved
