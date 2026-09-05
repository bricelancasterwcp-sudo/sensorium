"""The E6‴ acceptance TOOLING, tested without the box.

Nothing here runs cargo, touches the clone, or reads a real trace. What it
tests is the four places this run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock on the NEW document -- a lock that compared the wrong
  slice, or that passed on a changed §1, would let an endpoint move after a
  number was read;
* the two arms' identity -- E6‴-A and E6‴-W differ only in the package
  selector, and each must record into its OWN trace directory or one arm's
  evidence overwrites the other's;
* the blast radius's arithmetic -- the reviewer's static list, its resolution
  against the build's own arm rows, and the EXECUTED half read from traces.
  A static entry silently dropped, or an unexecuted arm quietly counted
  executed, would turn "31 arms, 1 measured" into a number that reads as
  coverage;
* the schema's none-versus-zero discipline -- neither arm's false-accusation
  count may ever be invented, because §1 asks for a reading of the clone's
  source.

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

import acceptance_e6ppp as runner                                  # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import driver_cmd                              # noqa: E402
from acceptance_schema_e6ppp import assemble_e6ppp                 # noqa: E402


# -- the byte-lock on the new document -------------------------------------


def test_the_e6ppp_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a stray
    edit to §1 is caught before a run is launched rather than by a refusal
    with the target already emptied."""
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True


def test_the_e6ppp_lock_carries_BOTH_shas_and_says_it_was_amended():
    """§1 was amended once, dated, before any number was read. A record that
    carried only the current sha would make that invisible -- the amendment
    would be a claim in prose with nothing behind it."""
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is True
    assert rec["amendment_bytes"] > 0
    assert rec["original_lock_sha256"] != rec["locked_sha256"]
    # No footnote is referenced by this §1, so the extended range and §1 are
    # the same bytes -- stated as an assertion, because a footnote added later
    # would silently widen the locked range.
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"]


def test_the_e6ppp_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself, on THIS document's locks. A check that
    computes two shas, reports them unequal and proceeds is not a lock."""
    text = runner.DOC.read_text()
    moved = text.replace("**0 false accusations**", "**1 false accusations**",
                         1)
    assert moved != text
    doc = tmp_path / "doc.md"
    doc.write_text(moved)
    with pytest.raises(rung3.Refused):
        rung3.byte_lock_check(doc, "aaaaaaa", "aaaaaaa",
                              lambda rel, commit: text)


# -- the two arms ----------------------------------------------------------


def _paths(tmp_path) -> dict:
    return {"sensorium_driver": tmp_path / "cargo-sensorium",
            "sensorium_dir": tmp_path / "sdir",
            "sensorium_acceptance_target": tmp_path / "target",
            "sensorium_bloomery_clone": tmp_path / "clone"}


def test_the_two_arms_differ_only_in_the_package_selector(tmp_path):
    """§1 states one difference between E6‴-A and E6‴-W: `-p bloomery-daemon`
    becomes `--workspace`. If the W arm quietly grew another flag the two
    numbers would stop being comparable line for line, which is the whole
    reason the A arm is re-measured at all."""
    p = _paths(tmp_path)
    a = driver_cmd(p, *["-p", "bloomery-daemon"], "--lib")
    w = driver_cmd(p, *["--workspace"], "--lib")
    assert a[-3:] == ["-p", "bloomery-daemon", "--lib"]
    assert w[-2:] == ["--workspace", "--lib"]
    assert a[:-3] == w[:-2]


def test_each_arm_records_into_its_own_trace_directory(tmp_path):
    """Two arms sharing one `SENSORIUM_DIR` would interleave their traces, and
    the sweep would then read the OTHER arm's processes as its own."""
    p = _paths(tmp_path)
    p["sensorium_dir"].mkdir()
    a = runner.arm_paths(p, "a")
    w = runner.arm_paths(p, "w")
    assert a["sensorium_dir"] != w["sensorium_dir"]
    assert a["sensorium_dir"].is_dir() and w["sensorium_dir"].is_dir()
    assert a["sensorium_dir"].parent == p["sensorium_dir"]
    # every other location is shared, unchanged
    assert a["sensorium_acceptance_target"] == p["sensorium_acceptance_target"]


def test_logs_at_moves_the_shared_log_directory_and_restores_it(tmp_path):
    """`acceptance_lib.run` writes to a module global. Without the move, both
    arms write `e6prime-run.log` to one directory and the second overwrites
    the first -- the evidence of one arm silently replaced by the other's."""
    import acceptance_lib as lib
    before = lib.LOGS
    with runner.logs_at(tmp_path / "arm-a"):
        assert lib.LOGS == tmp_path / "arm-a"
        assert lib.LOGS.is_dir()
    assert lib.LOGS == before


# -- the static blast list -------------------------------------------------


def test_the_static_list_is_the_reviewers_list_as_written():
    """The list is an INPUT, not a result. A duplicate would inflate the
    denominator of "executed of static"; a dropped entry would shrink it."""
    assert len(runner.STATIC_BLAST) == 29
    assert len(set(runner.STATIC_BLAST)) == 29
    assert len(runner.STATIC_BLAST_UNLOCATED) == 2
    # 31 entries in total, which is what the reviewer's list enumerates.
    assert len(runner.STATIC_BLAST) + len(runner.STATIC_BLAST_UNLOCATED) == 31
    assert ("memory.rs", 131) in runner.STATIC_BLAST


ARMS = {"rows": [
    {"file": "crates/bloomery-daemon/src/memory.rs", "line": 131,
     "qualname": "build_memory", "hows": ["arm_ambiguous"], "units": 1},
    {"file": "crates/bloomery-daemon/tests/common/memory.rs", "line": 131,
     "qualname": "helper", "hows": ["arm_handled"], "units": 1},
    {"file": "crates/bloomery-daemon/src/task/exec.rs", "line": 181,
     "qualname": "run", "hows": ["arm_handled"], "units": 1},
]}


def test_resolve_static_matches_a_suffix_and_keeps_the_how(tmp_path):
    r = runner.resolve_static(ARMS, [("exec.rs", 181)])
    assert r["resolved_count"] == 1
    assert r["resolved"][0]["file"] == "crates/bloomery-daemon/src/task/exec.rs"
    assert r["resolved"][0]["hows"] == ["arm_handled"]
    assert r["in_blast_radius_now_count"] == 0          # not arm_ambiguous


def test_only_an_arm_ambiguous_row_is_in_the_blast_radius_now():
    """The R2 amendment's whole effect is HANDLED -> ESCAPED, and ESCAPED is
    spelled `arm_ambiguous` on the wire. Counting every resolved arm as moved
    would report the repair's reach as the size of the list."""
    r = runner.resolve_static(ARMS, [("exec.rs", 181), ("memory.rs", 131)])
    assert r["resolved_count"] == 2
    assert r["in_blast_radius_now_count"] == 1
    assert r["in_blast_radius_now"][0]["qualname"] == "build_memory"


def test_a_suffix_matching_two_files_is_reported_ambiguous():
    """`drift.rs`, `swap.rs` and `memory.rs` each name two files in this
    workspace. Silently taking the first would make the resolution a coin
    toss that the record could not see."""
    r = runner.resolve_static(ARMS, [("memory.rs", 131)])
    assert r["ambiguous"] and len(r["ambiguous"][0]["files"]) == 2
    assert r["resolved"][0]["ambiguous"] is True


def test_a_static_entry_that_matches_no_arm_site_is_reported_not_dropped():
    """An entry that resolves to nothing is evidence about the list or the
    build, and must not vanish into a smaller denominator."""
    r = runner.resolve_static(ARMS, [("llama.rs", 406)])
    assert r["resolved_count"] == 0
    assert r["unmatched"] == [{"suffix": "llama.rs", "line": 406}]


def test_the_unlocated_entries_are_counted_but_never_matched():
    r = runner.resolve_static(ARMS, [("exec.rs", 181)])
    assert r["static_entries_located"] == 1
    assert r["static_entries_unlocated"] == 2
    assert r["static_entries_total"] == 3


# -- the manifest arm reader -----------------------------------------------


def _manifest(paths, name, files, fell_back=False):
    d = paths["sensorium_acceptance_target"] / "sensorium" / "manifests"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({
        "unit": name, "crate_name": "c", "crate_type": "lib",
        "fell_back": fell_back, "files": files}))


def test_arm_rows_keeps_the_how_and_deduplicates_across_units(tmp_path):
    """Two `(crate_name, crate_type)` pairs declare two manifests for one
    unit, so a raw sum double-counts the same source arm. The `how` is the
    field this whole check turns on and the rung-3 reader drops it."""
    p = _paths(tmp_path)
    site = {"site": 1, "qualname": "f", "kind": "arm", "line": 10,
            "how": "arm_ambiguous"}
    _manifest(p, "aaa", {"src/a.rs": [site]})
    _manifest(p, "bbb", {"src/a.rs": [site]})
    got = runner.arm_rows(p, ["aaa", "bbb"])
    assert got["distinct"] == 1 and got["raw"] == 2
    assert got["by_how"] == {"arm_ambiguous": 1}
    assert got["rows"][0]["units"] == 2


def test_arm_rows_ignores_every_kind_that_is_not_an_arm(tmp_path):
    p = _paths(tmp_path)
    _manifest(p, "aaa", {"src/a.rs": [
        {"site": 1, "qualname": "f", "kind": "fn", "firstlineno": 3},
        {"site": 2, "qualname": "f", "kind": "try", "line": 5},
        {"site": 3, "qualname": "f", "kind": "arm", "line": 7,
         "how": "arm_handled"}]})
    got = runner.arm_rows(p, ["aaa"])
    assert got["distinct"] == 1 and got["by_how"] == {"arm_handled": 1}


def test_a_unit_that_fell_back_contributes_no_arm_rows(tmp_path):
    """A fallen-back unit was compiled from the REAL tree: it has no
    instrumented arms, and counting its declared sites would credit the
    transformer with reach it did not have."""
    p = _paths(tmp_path)
    _manifest(p, "aaa", {"src/a.rs": [
        {"site": 1, "qualname": "f", "kind": "arm", "line": 7,
         "how": "arm_ambiguous"}]}, fell_back=True)
    got = runner.arm_rows(p, ["aaa"])
    assert got["distinct"] == 0 and got["units_in_scope"] == 1


def test_a_manifest_outside_this_builds_scope_is_not_read(tmp_path):
    """A different tool hash leaves its manifests behind; folding them in
    would count arms from a build that is not the one under measurement."""
    p = _paths(tmp_path)
    _manifest(p, "aaa", {"src/a.rs": [
        {"site": 1, "qualname": "f", "kind": "arm", "line": 7,
         "how": "arm_ambiguous"}]})
    _manifest(p, "old", {"src/b.rs": [
        {"site": 1, "qualname": "g", "kind": "arm", "line": 9,
         "how": "arm_ambiguous"}]})
    assert runner.arm_rows(p, ["aaa"])["distinct"] == 1


# -- the executed half -----------------------------------------------------


def _trace(paths, run_id, events):
    d = paths["sensorium_dir"] / "traces"
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / f"{run_id}.db")
    con.execute("create table code_objects (id integer primary key, "
                "file text, qualname text)")
    con.execute("create table events (id integer primary key, kind text, "
                "code_id integer, line integer, payload text)")
    files = {}
    for i, (kind, file, qualname, line, how) in enumerate(events, 1):
        cid = files.setdefault(file, len(files) + 1)
        con.execute("insert or ignore into code_objects values (?,?,?)",
                    (cid, file, qualname))
        con.execute("insert into events values (?,?,?,?,?)",
                    (i, kind, cid, line,
                     json.dumps({"how": how}) if how else None))
    con.commit()
    con.close()


def test_executed_arms_reads_only_arm_events(tmp_path):
    """A RAISE or a sink HANDLED at some other line is not an arm firing.
    Counting them would report arms as executed that never ran."""
    p = _paths(tmp_path)
    _trace(p, "r1", [
        ("HANDLED", "/clone/src/a.rs", "f", 10, "arm_ambiguous"),
        ("HANDLED", "/clone/src/a.rs", "f", 10, "arm_ambiguous"),
        ("HANDLED", "/clone/src/b.rs", "g", 20, "sink_let_underscore"),
        ("RAISE", "/clone/src/c.rs", "h", 30, None)])
    got = runner.executed_arms(p, ["r1"])
    assert got["distinct_sites"] == 1
    assert got["sites"][0]["events"] == 2
    assert got["arm_events_per_run"] == {"r1": 2}


def test_executed_arms_reports_a_run_whose_trace_is_missing(tmp_path):
    """A trace that is not there is not a zero: it is a hole in the evidence
    and must say so."""
    p = _paths(tmp_path)
    got = runner.executed_arms(p, ["nope"])
    assert got["traces_missing"] == ["nope"]
    assert got["distinct_sites"] == 0


RESOLVED = {"resolved": [
    {"suffix": "a.rs", "line": 10, "file": "src/a.rs", "hows": ["arm_ambiguous"],
     "qualname": "f", "ambiguous": False},
    {"suffix": "z.rs", "line": 99, "file": "src/z.rs", "hows": ["arm_ambiguous"],
     "qualname": "z", "ambiguous": False}],
    "resolved_count": 2, "static_entries_total": 4}


def test_executed_vs_static_joins_on_the_workspace_relative_path():
    """Traces carry absolute paths and manifests carry workspace-relative
    ones. Joining them without stripping the clone root gives 0 executed on
    every run -- a zero that would read as "the run reached nothing"."""
    ex = {"sites": [{"file": "/clone/src/a.rs", "line": 10,
                     "hows": ["arm_ambiguous"], "events": 3}],
          "distinct_sites": 1}
    got = runner.executed_vs_static(RESOLVED, ex, "/clone")
    assert got["executed"] == 1 and got["static"] == 2
    assert got["trace_paths_not_under_the_clone_root"] == 0
    assert [r["file"] for r in got["not_executed_rows"]] == ["src/z.rs"]


def test_a_trace_path_outside_the_clone_root_is_counted_and_reported():
    """If the path shape ever changes, the join silently stops matching. The
    count of unstripped paths is what turns that into a visible fact."""
    ex = {"sites": [{"file": "/elsewhere/src/a.rs", "line": 10,
                     "hows": ["arm_ambiguous"], "events": 1}],
          "distinct_sites": 1}
    got = runner.executed_vs_static(RESOLVED, ex, "/clone")
    assert got["executed"] == 0
    assert got["trace_paths_not_under_the_clone_root"] == 1


def test_an_arm_the_run_never_reached_is_not_counted_executed():
    got = runner.executed_vs_static(RESOLVED, {"sites": [],
                                               "distinct_sites": 0}, "/clone")
    assert got["executed"] == 0
    assert len(got["not_executed_rows"]) == 2


# -- the schema ------------------------------------------------------------


RAW_ARM = {
    "raw_e6ppp_a": {
        "swallowed_count": 3, "chains_in_scope": 9, "processes": 1,
        "union_swallowed_count": 3, "unparsed_swallowed": 0,
        "tally": {"swallowed": 3}, "tally_line": "dispositions: swallowed 3",
        "selector": ["-p", "bloomery-daemon"],
        "sweep": {"swallowed_count": 0, "processes_swept": 0, "swept": [],
                  "swallowed_parsed": []}},
    "raw_e6ppp_w": {
        "swallowed_count": 2, "chains_in_scope": 5, "processes": 3,
        "union_swallowed_count": 6, "unparsed_swallowed": 0,
        "tally": {"swallowed": 2}, "tally_line": "dispositions: swallowed 2",
        "selector": ["--workspace"],
        "sweep": {"swallowed_count": 4, "processes_swept": 2,
                  "swallowed_parsed": [{"unparsed": False}] * 4,
                  "swept": [{"tally_line": "dispositions: swallowed 3"},
                            {"tally_line": "dispositions: swallowed 1, "
                                           "ambiguous 2"}]}},
}


def test_neither_arms_false_accusation_count_is_ever_invented():
    """§1 asks for a reading of the clone's SOURCE. A schema that published a
    number here would publish one nobody derived -- the exact failure the
    rung-3 record avoided for E6′, and there are two arms to lose it in now."""
    doc = assemble_e6ppp(RAW_ARM)
    for key in ("E6pppA", "E6pppW"):
        h = doc["endpoints"][key]["headline"]
        assert h["value"] is None
        assert h["dropped"] and "adjudicated by hand" in h["dropped"][0]
    # ... and the lines that HAD to be adjudicated are published as numbers.
    assert doc["endpoints"]["E6pppA"]["swallowed_lines"]["value"] == 3
    assert doc["endpoints"]["E6pppW"]["union_swallowed_lines"]["value"] == 6


def test_the_union_is_the_primary_plus_the_sweep():
    """The gate is adjudicated over the union. A union that silently equalled
    the primary would drop every process `--workspace --lib` added, which is
    the only thing E6‴-W measures that E6‴-A does not."""
    doc = assemble_e6ppp(RAW_ARM)
    w = doc["endpoints"]["E6pppW"]
    assert w["swallowed_lines"]["value"] == 2
    assert w["sweep_swallowed_lines"]["value"] == 4
    assert w["union_swallowed_lines"]["value"] == 6


def test_the_dispositions_block_sums_every_processs_tally():
    """§1 reports the tallies without a gate so the widening's cost in volume
    is visible. Reporting only the primary's would hide it."""
    doc = assemble_e6ppp(RAW_ARM)
    d = doc["reported"]["dispositions"]["E6‴-W"]
    assert d["primary_tally"] == {"swallowed": 2}
    assert d["all_processes_tally"] == {"swallowed": 6, "ambiguous": 2}


def test_a_phase_that_did_not_run_is_null_with_a_reason_never_zero():
    """A zero here reads as measured-and-clean. It is the difference between
    "no false accusation" and "no measurement"."""
    doc = assemble_e6ppp({})
    for key in ("E6pppA", "E6pppW"):
        m = doc["endpoints"][key]["swallowed_lines"]
        assert m["value"] is None and m["dropped"]
    assert doc["endpoints"]["E6again"]["headline"]["value"] is None


def test_e6again_is_the_committed_rung3_schema_not_a_copy():
    """§1 calls E6-again "E6's protocol verbatim". A second schema would be a
    second protocol, free to disagree with the one the rung-3 record used."""
    from acceptance_schema_rung3 import _e6 as rung3_e6
    raw = {"raw_e6": {"cases": [{"case": "rust/x", "questions": [{
        "id": "q", "printed_swallowed_count": 1, "expected_swallowed": 1,
        "swallow_set_equal": True, "printed_tally": "dispositions: swallowed 1",
        "tally_pinned": "dispositions: swallowed 1", "tally_equal": True,
        "extra_swallowed_lines": [], "missing_swallow_groups": [],
        "swallow_set_nonempty_ok": True, "corpus_check_failures": [],
        "rc": 0, "expect_exit": 0, "printed_swallowed": ["SWALLOWED -- x"],
    }]}]}}
    assert assemble_e6ppp(raw)["endpoints"]["E6again"] == rung3_e6(raw)


def test_the_renderer_prints_not_measured_rather_than_a_dash():
    """A dash in a results table is indistinguishable from a zero at a
    glance. The renderer must say what was not measured and why."""
    from render_e6ppp import results
    doc = assemble_e6ppp(RAW_ARM)
    doc["acceptance"] = "x.md"
    text = "\n".join(results(doc))
    assert "not measured (adjudicated by hand" in text
    assert "E6‴-A" in text and "E6‴-W" in text


def test_results_json_if_present_matches_the_committed_schema():
    """After the run, the published `results.json` must be reproducible from
    the raw record by the committed assembler -- not by a one-off script."""
    p = (REPO / "docs" / "superpowers" / "acceptance"
         / "2026-09-05-sensorium-rung3-e6ppp.results.json")
    if not p.is_file():
        pytest.skip("not measured yet")
    doc = json.loads(p.read_text())
    assert doc["acceptance"].endswith("2026-09-05-sensorium-rung3-e6ppp.md")
    assert set(doc["endpoints"]) == {"E6pppA", "E6pppW", "E6again", "E7ppp"}
    for key in ("E6pppA", "E6pppW"):
        assert doc["endpoints"][key]["headline"]["value"] is None
