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
* the flip diff's arithmetic -- a transition mislabelled, a row present in
  one build only, or a named row missing and assumed flipped, each turns
  E-flip's gate into one that cannot fail;
* the two prep builds -- each is one half of the flip diff, and they must not
  overwrite each other's driver, target or log.

What the run WRITES -- every field the results document publishes, the
provenance of each number, none-versus-zero -- is the sibling
`test_acceptance_e6q_record.py`'s, split off at the `# -- the schema` banner
on 2026-09-08.

Every test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

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

# Importing the runner re-points the SHARED log pointers at THIS document's
# workspace (the runner's job; the reload test in the `_record` sibling pins
# it). But `tests/test_acceptance_e6ppp.py` asserts the SAME invariant for ITS
# runner and every such module is imported at COLLECTION time, so whichever
# pytest collected last would own the pointer and the sibling assertion would
# fail on collection order alone. Restoring E6‴'s pointers here makes the
# suites order-independent and costs nothing: every phase runs inside a
# `logs_at`.
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


def test_arm_As_selector_IS_the_shared_configs_package(monkeypatch):
    """A1's review minors: `ARM_A["selector"]` and `acceptance.real_config`'s
    `pkg` are written out separately and nothing said they must agree, so a
    package rename would move one and leave this arm measuring another
    crate under E6⁗-A's name."""
    import acceptance
    monkeypatch.setattr(acceptance, "workspace_packages", lambda root: [])
    cfg = acceptance.real_config({"sensorium_bloomery_clone": Path("/nowhere")})
    assert runner.ARM_A["selector"] == cfg["pkg"]
    assert runner.ARM_WS["selector"] == cfg["workspace_sel"]


def test_the_base_drivers_sha256_is_RE_CHECKED_at_cleanup(tmp_path):
    """A1's review minors: the shared cleanup re-checks the HEAD driver and
    nothing re-checked the control's, so a base binary rebuilt or replaced
    mid-run would have left the record naming a pre-repair driver it no
    longer had. Reported, never a refusal -- by cleanup the numbers are in.
    """
    drv = tmp_path / "cargo-sensorium"
    drv.write_bytes(b"base")
    p = {"sensorium_base_driver": drv}
    from acceptance_lib import sha256_file
    same = runner.base_driver_cleanup(p, {"driver_sha256": sha256_file(drv)})
    assert same["base_driver_unchanged"] is True
    assert same["base_driver_unchanged_reason"] is None
    moved = runner.base_driver_cleanup(p, {"driver_sha256": "0" * 64})
    assert moved["base_driver_unchanged"] is False
    assert moved["base_driver_sha256_after"] == sha256_file(drv)
    # None-vs-False, both ways round.
    drv.unlink()
    gone = runner.base_driver_cleanup(p, {"driver_sha256": "0" * 64})
    assert gone["base_driver_unchanged"] is None
    assert "no longer a file" in gone["base_driver_unchanged_reason"]
    drv.write_bytes(b"base")
    unpinned = runner.base_driver_cleanup(p, {})
    assert unpinned["base_driver_unchanged"] is None
    assert "nothing recorded" in unpinned["base_driver_unchanged_reason"] or \
           "no base driver sha256" in unpinned["base_driver_unchanged_reason"]


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
    """The only place a driver says what it IS, is the trace it wrote, and
    the record shows that string per run.

    It does not discriminate: the run read `cargo-sensorium 0.3.0` on all
    three arms (record §5.7), because the crate moves to 0.3.1 in the
    release task, which runs after this measurement. What this reader must
    get right is therefore that the string is read from the arm's own trace
    and that `tool_hash` -- the reading that DOES tell the binaries apart --
    is read beside it, per run."""
    p = _paths(tmp_path)
    _trace_meta(p, "r1", {"driver_version": "cargo-sensorium 0.3.0",
                          "tool_hash": "abc"})
    got = runner.driver_identity(p, ["r1"])
    assert got["driver_versions"] == ["cargo-sensorium 0.3.0"]
    assert got["driver_version_per_run"] == {"r1": "cargo-sensorium 0.3.0"}
    assert got["tool_hash_per_run"] == {"r1": "abc"}
    assert got["tool_hashes"] == ["abc"]
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

