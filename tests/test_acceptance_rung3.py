"""The rung-3 acceptance TOOLING, tested without the box.

Nothing here runs cargo, touches the clone, or reads a trace. What it tests is
the three places the acceptance run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock's extraction and comparison -- a lock that compared the
  wrong slice, or that passed on a changed §1, would let an endpoint move
  after a number was read;
* the E6 collector's reading of a case file and of one `exceptions` answer --
  in particular that the swallow-set comparison is EQUALITY (a perfect
  matching both ways) and not the subset test the corpus harness itself runs;
* the schema's none-versus-zero discipline -- a phase that did not run must
  leave `null` with a reason, never a zero that reads as measured.

Every test states the failure it would catch. The mutations that were run
against them are in the task report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_phases_rung3 as r3                              # noqa: E402
import acceptance_rung3 as runner                                 # noqa: E402
from acceptance_schema_rung3 import assemble_rung3                # noqa: E402


# -- the byte-lock ---------------------------------------------------------
DOC = """# A document

Preamble.

## 1. Pre-registration

| Id | Endpoint |
|---|---|
| E6 | 0 false accusations |

## 2. Environment

filled later
"""


def test_section1_extraction_stops_at_the_next_heading():
    """The lock must cover §1 and NOTHING else: a slice that ran to the end of
    the file would make every later edit -- §2, §3, §4, all written after the
    run -- look like a moved endpoint, and one that stopped early would leave
    part of §1 unlocked."""
    s = runner.section1(DOC)
    assert s.startswith("## 1. Pre-registration")
    assert s.rstrip().endswith("## 2. Environment")
    assert "0 false accusations" in s
    assert "filled later" not in s


def test_section1_of_a_document_without_a_second_heading_is_the_tail():
    s = runner.section1("## 1. Pre-registration\nonly this\n")
    assert s == "## 1. Pre-registration\nonly this\n"


def test_a_changed_endpoint_changes_the_lock_sha():
    """The whole point: one character of §1 must move the sha."""
    a = runner._sha(runner.section1(DOC))
    b = runner._sha(runner.section1(DOC.replace("0 false", "1 false")))
    assert a != b


def test_an_edit_outside_section1_does_not_change_the_lock_sha():
    """§2-§5 are written by Task 8 AFTER the run; if they entered the lock the
    runner could never write its own results."""
    a = runner._sha(runner.section1(DOC))
    b = runner._sha(runner.section1(DOC.replace("filled later", "measured")))
    assert a == b


def test_the_byte_lock_check_passes_on_the_real_document():
    """The committed §1 and the working tree's must agree right now: this is
    the same comparison the runner refuses on, run in the suite so a stray
    edit to §1 is caught before a run is launched rather than by a refusal
    two hours in."""
    rec = runner.byte_lock_check()
    assert rec["identical"] is True
    assert rec["commit"] == runner.BYTE_LOCK
    assert rec["original_lock"] == runner.ORIGINAL_LOCK
    # The E6' amendment is a FACT of this record, not a claim in prose.
    assert rec["amended_after_the_original_lock"] is True
    assert rec["amendment_bytes"] > 0


# -- the E6 collector ------------------------------------------------------
SWALLOW_Q = {
    "id": "which-settings-were-dropped",
    "command": ["exceptions", "$RUN"],
    "expect_contains": ["dispositions: swallowed 2"],
    "expect_count": {"SWALLOWED": 2},
    "expect_absent": ["ambiguous", "panicked"],
    "expect_line": [
        ["SWALLOWED", "sink_ok", "load L31"],
        ["SWALLOWED", "sink_let_underscore", "load L33"],
        ["RAISE", "parse_port"],
    ],
}

GOOD = """raised (2):
  e5 RAISE parse_port ...
    SWALLOWED -- absorbed by sink_ok at e9 (load L31) in f2, which returned ok
    SWALLOWED -- absorbed by sink_let_underscore at e14 (load L33) in f2, which returned ok
dispositions: swallowed 2
"""


def test_registration_reads_the_swallow_set_and_the_whole_tally():
    reg = r3.swallow_registration(SWALLOW_Q)
    assert reg["expected_swallowed"] == 2
    assert len(reg["swallow_groups"]) == 2          # the RAISE group is not one
    assert reg["tally_pinned"] == "dispositions: swallowed 2"
    assert reg["empty_set_declared"] is False


def test_an_empty_swallow_set_is_read_from_the_declared_absence():
    """The tool prints only NON-ZERO tags, so there is no `swallowed 0` line
    to assert; a case with no swallow says so with `expect_absent`. A
    collector that inferred the empty set from "no groups registered" would
    take a case that forgot to register anything as a passing zero."""
    q = {"id": "q", "command": ["exceptions", "$RUN"],
         "expect_contains": ["dispositions: ambiguous 2"],
         "expect_absent": ["SWALLOWED", "dispositions: swallowed"]}
    reg = r3.swallow_registration(q)
    assert reg["expected_swallowed"] == 0
    assert reg["empty_set_declared"] is True
    assert reg["tally_pinned"] == "dispositions: ambiguous 2"


def test_a_clean_answer_is_equal_on_all_three_conjuncts():
    got = r3.collect_e6(SWALLOW_Q, GOOD)
    assert got["printed_swallowed_count"] == 2
    assert got["swallow_set_equal"] is True
    assert got["tally_equal"] is True
    assert got["swallow_set_nonempty_ok"] is True
    assert got["extra_swallowed_lines"] == []
    assert got["missing_swallow_groups"] == []


def test_one_extra_swallowed_line_is_a_false_accusation():
    """§1's STOP condition. The extra line matches no registered group, and
    the count no longer agrees."""
    text = GOOD.replace(
        "dispositions: swallowed 2",
        "    SWALLOWED -- absorbed by sink_ok at e20 (save L44) in f3, "
        "which returned ok\ndispositions: swallowed 3")
    got = r3.collect_e6(SWALLOW_Q, text)
    assert got["printed_swallowed_count"] == 3
    assert len(got["extra_swallowed_lines"]) == 1
    assert got["swallow_set_equal"] is False


def test_a_missing_swallowed_line_is_also_a_miss():
    text = "\n".join(l for l in GOOD.splitlines()
                     if "sink_let_underscore" not in l)
    got = r3.collect_e6(SWALLOW_Q, text)
    assert got["printed_swallowed_count"] == 1
    assert len(got["missing_swallow_groups"]) == 1
    assert got["swallow_set_equal"] is False


def test_two_groups_may_not_both_claim_one_line():
    """The failure a per-group `any(...)` test cannot see, and the reason the
    matching is a MATCHING.

    Both registered groups fit the first printed line here (it names both
    sinks), and a second, unregistered line is printed. A subset check would
    call that a pass: every group found a line. Equality does not -- one group
    is left unmatched and one line unclaimed."""
    q = dict(SWALLOW_Q)
    text = ("    SWALLOWED -- absorbed by sink_ok and sink_let_underscore at "
            "e9 (load L31) (load L33), which returned ok\n"
            "    SWALLOWED -- absorbed by sink_ok at e30 (other L99), "
            "which returned ok\n"
            "dispositions: swallowed 2\n")
    got = r3.collect_e6(q, text)
    assert got["printed_swallowed_count"] == 2          # the count agrees...
    assert got["swallow_set_equal"] is False            # ...and it is still a miss
    assert len(got["missing_swallow_groups"]) == 1
    assert len(got["extra_swallowed_lines"]) == 1


def test_the_tally_is_compared_whole_not_as_a_substring():
    """`dispositions: swallowed 2` is a PREFIX of
    `dispositions: swallowed 2, ambiguous 1`. The corpus harness's own
    `expect_contains` accepts the longer line; §1 asks for equality, so a
    disposition the case never registered has to show up as a miss."""
    text = GOOD.replace("dispositions: swallowed 2",
                        "dispositions: swallowed 2, ambiguous 1")
    got = r3.collect_e6(SWALLOW_Q, text)
    assert got["swallow_set_equal"] is True
    assert got["tally_equal"] is False
    assert got["printed_tally"] == "dispositions: swallowed 2, ambiguous 1"


def test_the_empty_answer_shape_registers_that_no_tally_was_printed():
    q = {"id": "q", "command": ["exceptions", "$RUN"],
         "expect_contains": ["no exceptions recorded"],
         "expect_absent": ["SWALLOWED", "dispositions:"],
         "expect_exit": 1}
    got = r3.collect_e6(q, "no exceptions recorded\n")
    assert got["tally_equal"] is True
    assert got["swallow_set_equal"] is True
    got_bad = r3.collect_e6(q, "no exceptions recorded\ndispositions: "
                               "ambiguous 1\n")
    assert got_bad["tally_equal"] is False


def test_a_swallow_case_that_printed_nothing_is_flagged():
    got = r3.collect_e6(SWALLOW_Q, "raised (0):\ndispositions: swallowed 2\n")
    assert got["swallow_set_nonempty_ok"] is False


def test_every_real_rust_exceptions_question_has_a_readable_registration():
    """The collector against the CORPUS AS COMMITTED: every question it will
    have to read must yield a count and a whole tally, or the run would
    compare against nothing."""
    sys.path.insert(0, str(REPO))
    from corpus import run_corpus
    seen = 0
    for case in run_corpus.load_cases():
        if not case.is_cargo:
            continue
        for q in case.questions:
            if q["command"][0] != "exceptions":
                continue
            seen += 1
            reg = r3.swallow_registration(q)
            where = f"{case.name}/{q['id']}"
            assert isinstance(reg["expected_swallowed"], int), where
            if reg["empty_answer_expected"]:
                assert reg["no_tally_expected"], where
            else:
                assert reg["tally_pinned"] is not None, where
            if reg["expected_swallowed"] == 0:
                assert reg["empty_set_declared"], where
            else:
                assert len(reg["swallow_groups"]) == reg["expected_swallowed"], \
                    where
    assert seen >= 13, f"only {seen} rust `exceptions` questions found"


# -- the E6' line parser ---------------------------------------------------
def test_the_swallowed_line_parses_into_the_adjudication_columns():
    line = ("    SWALLOWED -- absorbed by arm_handled at e6 (charge L30) in "
            "f2, which returned ok")
    m = r3.SWALLOW_LINE.search(line)
    assert m and m.group("how") == "arm_handled"
    assert int(m.group("event")) == 6
    assert m.group("qualname") == "charge"
    assert int(m.group("line")) == 30
    assert m.group("frame") == "2"


def test_a_swallowed_line_without_a_named_how_still_parses():
    line = "    SWALLOWED -- absorbed at e9 (Registry::drop L120), which returned ok"
    m = r3.SWALLOW_LINE.search(line)
    assert m and m.group("how") is None
    assert m.group("qualname") == "Registry::drop"
    assert int(m.group("line")) == 120


# -- the rung-3 manifest reader --------------------------------------------
def _manifests(tmp_path: Path, *manifests) -> dict:
    d = tmp_path / "sensorium" / "manifests"
    d.mkdir(parents=True)
    for name, m in manifests:
        (d / f"{name}.json").write_text(json.dumps(m))
    return {"sensorium_acceptance_target": tmp_path}


def _unit(name, files, partial=(), fell_back=False):
    return (name, {"unit": name, "crate_name": name.split("-")[0],
                   "crate_type": "lib", "files": files, "skipped": [],
                   "partial": list(partial), "spawns": [],
                   "source_hashes": {}, "fell_back": fell_back,
                   "fallback_reason": None, "unreached_files": [],
                   "unreached_reasons": {}, "appended_line": {},
                   "workspace_root": "/ws"})


FN_ROW = {"site": 0, "qualname": "f", "kind": "fn", "firstlineno": 10,
          "ret": "value"}
TRY_ROW = {"site": 1, "qualname": "f", "kind": "try", "line": 12,
           "how": "try"}
SINK_ROW = {"site": 2, "qualname": "f", "kind": "sink", "line": 14,
            "how": "sink_ok"}


def test_the_rung2_reader_cannot_read_a_rung3_manifest(tmp_path):
    """The defect the rung-3 reader exists for, pinned so nobody quietly
    switches back. Rung 3's `ManifestSite` serialises `firstlineno` ONLY for a
    `fn` row, and `acceptance_lib.read_manifests` indexes it directly. This
    killed the first launch of the acceptance run ten seconds in."""
    from acceptance_lib import read_manifests
    paths = _manifests(tmp_path, _unit("u1", {"a.rs": [FN_ROW, TRY_ROW]}))
    with pytest.raises(KeyError):
        read_manifests(paths, None)


def test_the_rung3_reader_counts_every_site_kind(tmp_path):
    paths = _manifests(tmp_path,
                       _unit("u1", {"a.rs": [FN_ROW, TRY_ROW, SINK_ROW]}))
    m = r3.read_manifests_rung3(paths, None)
    assert m["raw_site_total"] == 3
    assert m["distinct"] == 3          # kind joins the key
    assert m["fell_back"] == []


def test_a_fn_and_a_try_on_one_line_are_two_sites(tmp_path):
    """Without `kind` in the key they would collapse into one, and the site
    count would silently shrink."""
    same_line = dict(TRY_ROW, line=10)
    paths = _manifests(tmp_path, _unit("u1", {"a.rs": [FN_ROW, same_line]}))
    assert r3.read_manifests_rung3(paths, None)["distinct"] == 2


def test_try_rows_are_deduplicated_across_the_units_that_declare_them(tmp_path):
    """Two (crate_name, crate_type) pairs declare two manifests for one unit,
    so a RAW sum double-counts one source `?`. The numerator is the distinct
    count; the raw sum is reported beside it."""
    paths = _manifests(tmp_path,
                       _unit("u1", {"a.rs": [TRY_ROW]}),
                       _unit("u2", {"a.rs": [TRY_ROW]}))
    rows = r3._try_rows(paths, None)
    assert rows["try_rows_raw"] == 2
    assert rows["try_rows_distinct"] == 1
    assert rows["site_kinds_raw"] == {"try": 2}


def test_a_unit_that_fell_back_contributes_no_try_rows(tmp_path):
    """A fallen-back unit compiled the REAL tree: none of its sites exist."""
    paths = _manifests(tmp_path,
                       _unit("u1", {"a.rs": [TRY_ROW]}, fell_back=True))
    assert r3._try_rows(paths, None)["try_rows_distinct"] == 0
    assert len(r3.read_manifests_rung3(paths, None)["fell_back"]) == 1


def test_partial_rows_are_deduplicated_and_grouped_by_file(tmp_path):
    row = {"file": "b.rs", "line": 108, "qualname": "main", "kind": "try",
           "reason": "macro-arg"}
    paths = _manifests(tmp_path,
                       _unit("u1", {"a.rs": []}, partial=[row]),
                       _unit("u2", {"a.rs": []}, partial=[row]))
    rows = r3._try_rows(paths, None)
    assert rows["partial_rows"] == 1
    assert rows["partial_by_file"] == {"b.rs": 1}
    assert rows["partial_reasons"] == {"macro-arg": 1}


# -- the schema ------------------------------------------------------------
def test_a_phase_that_did_not_run_is_null_with_a_reason_never_zero():
    """The none-versus-zero rule. A run that died before E6 must not publish
    `0 false accusations`."""
    doc = assemble_rung3({"pins": {}, "config": {"try_syn": 401}})
    for key in ("E6", "E6prime", "E2pp", "E7pp", "E3pp", "E5pp", "E0pp"):
        h = doc["endpoints"][key]["headline"]
        assert h["value"] is None, key
        assert h["dropped"], key


def test_a_measured_zero_is_a_zero():
    raw = {
        "pins": {}, "config": {"try_syn": 401, "try_macro_tokens": 1},
        "raw_e6": {"cases": [{"case": "rust/silent_swallow", "run_ids": ["r1"],
                              "record_rc": 0, "questions": [
            dict(r3.collect_e6(SWALLOW_Q, GOOD), id="q", argv=[], rc=0,
                 expect_exit=0, log="x", corpus_check_failures=[])]}]},
    }
    e6 = assemble_rung3(raw)["endpoints"]["E6"]
    assert e6["headline"]["value"] == 0
    assert e6["headline"]["dropped"] == []
    assert e6["cases_with_an_unequal_tally"]["value"] == 0


def test_the_e6prime_false_accusation_count_is_never_invented():
    """No program can adjudicate a SWALLOWED line against the clone's source,
    so the schema must not publish a number for it. It publishes the lines."""
    raw = {"pins": {}, "config": {},
           "raw_e6prime": {"swallowed_count": 3, "chains_in_scope": 40,
                           "swallowed_parsed": [], "counts": {},
                           "unparsed_swallowed": 0}}
    e = assemble_rung3(raw)["endpoints"]["E6prime"]
    assert e["headline"]["value"] is None
    assert "adjudicated by hand" in e["headline"]["dropped"][0]
    assert e["swallowed_lines"]["value"] == 3


def test_e2pp_takes_the_ratio_over_the_frozen_denominator():
    raw = {"pins": {}, "config": {"try_syn": 400, "try_macro_tokens": 1},
           "raw_census_try": {"try_syn": 401, "files": 191},
           "raw_e2pp": {"build": {}, "manifests": {"units": [], "fell_back": [],
                                                   "unreached_files": []},
                        "try": {"try_rows_distinct": 380, "try_rows_raw": 500,
                                "partial_rows": 1},
                        "fell_back_stderr_lines": []}}
    e = assemble_rung3(raw)["endpoints"]["E2pp"]
    assert e["headline"]["value"] == pytest.approx(380 / 400)
    # The re-run census is REPORTED beside it and never becomes the divisor.
    assert e["census_rerun_try_syn"]["value"] == 401
    assert e["denominator"]["value"] == 400


def test_e7pp_reads_the_operand_columns_out_of_the_mechanics_log(tmp_path):
    log = tmp_path / "e7a-mechanics.log"
    log.write_text(
        "ok: e7_output_identical_plain_vs_call\n"
        "    [E7-operand] plain: probe-app/tests/e7_operand.rs:34:21\n"
        "    [E7-operand] off: probe-app/tests/e7_operand.rs:34:27\n"
        "    [E7-operand] call: probe-app/tests/e7_operand.rs:34:27\n"
        "ok: e7_operand_line_identical_and_column_shifts_by_the_wrap_prefix\n")
    raw = {"pins": {}, "config": {},
           "raw_e7pp": _e7pp_from_log(log)}
    e = assemble_rung3(raw)["endpoints"]["E7pp"]
    assert e["operand_column_shift"]["value"] == 6
    assert e["operand_column_shift_off"]["value"] == 6
    assert e["operand_line_identical"]["value"] == 1


def _e7pp_from_log(log: Path) -> dict:
    """`phase_e7pp`'s parsing half, without the mechanics run itself."""
    import re
    body = log.read_text()
    obs = {}
    for key in ("plain", "off", "call"):
        m = re.search(rf"^\s*\[E7-operand\] {key}: (\S+):(\d+):(\d+)$",
                      body, re.M)
        obs[key] = ({"file": m.group(1), "line": int(m.group(2)),
                     "col": int(m.group(3))} if m else None)
    return {
        "rc": 0, "ok": ["e7_output_identical_plain_vs_call"], "fail": [],
        "skip": [], "log": str(log), "driver_unchanged": True,
        "operand": {
            "predicted_shift": r3.E7_PREDICTED_SHIFT, "locations": obs,
            "column_shift_call": obs["call"]["col"] - obs["plain"]["col"],
            "column_shift_off": obs["off"]["col"] - obs["plain"]["col"],
            "line_identical": obs["plain"]["line"] == obs["call"]["line"],
            "checks": [], "dropped": []},
    }


def test_the_e7pp_operand_regex_matches_what_mechanics_prints():
    """`_e7pp_from_log` above and `phase_e7pp` must read the same line shape;
    the mechanics script's own `note` prefix is four spaces."""
    import re
    line = "    [E7-operand] call: probe-app/tests/e7_operand.rs:34:27"
    assert re.search(r"^\s*\[E7-operand\] call: (\S+):(\d+):(\d+)$", line, re.M)


def test_the_mechanics_script_prints_those_three_lines():
    """The parser above is only as good as the producer: the check that the
    script really emits `[E7-operand] <arm>: ...` for all three arms, and that
    the predicted shift in the script is the one §1 registered."""
    body = (REPO / "rust" / "tests" / "mechanics.sh").read_text()
    for arm in ("plain", "off", "call"):
        assert f'[E7-operand] {arm}: ' in body, arm
    assert f"E7_OPERAND_SHIFT={r3.E7_PREDICTED_SHIFT}" in body


def test_the_probe_puts_its_panic_inside_a_try_operand():
    """A probe whose panic drifted OUT of the operand would measure a shift of
    zero and read as a pass."""
    src = (REPO / "rust" / "probes" / "ws" / "probe-app" / "tests"
           / "e7_operand.rs").read_text()
    line = next(l for l in src.splitlines() if "panic!(" in l and "?" in l)
    assert line.index("panic!") < line.index("?;")


def test_the_renderer_prints_not_measured_rather_than_a_dash():
    from render_rung3 import results
    doc = assemble_rung3({"pins": {}, "config": {},
                          "acceptance": "docs/x.md"})
    doc["acceptance"] = "docs/x.md"
    text = "\n".join(results(doc))
    assert "not measured (" in text
    assert "| E6 |" in text


def test_results_json_if_present_matches_the_committed_schema():
    """When the run has happened, the published `results.json` must still be
    the shape the renderer reads -- a document whose numbers were pasted by
    hand would not be."""
    p = (REPO / "docs" / "superpowers" / "acceptance"
         / "2026-09-04-sensorium-rung3-acceptance.results.json")
    if not p.is_file():
        pytest.skip("the acceptance run has not published results.json yet")
    r = json.loads(p.read_text())
    assert set(r["endpoints"]) == {"E6", "E6prime", "E2pp", "E7pp", "E3pp",
                                   "E5pp", "E0pp"}
    for key, e in r["endpoints"].items():
        h = e["headline"]
        assert set(h) == {"value", "n", "lens", "dropped"}, key
        if h["value"] is None:
            assert h["dropped"], key
