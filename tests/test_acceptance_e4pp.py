"""The E4″ runner against its byte-locked pre-registration.

Everything a launch would discover expensively, discovered here instead:
the lock, the paths, the ceilings, the dry run's shape, the kill wording,
and the rule that no module of this instrument names a box path.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4pp as runner                                   # noqa: E402
import acceptance_e4pp_arms as arms                                # noqa: E402
import acceptance_e4pp_lock as lock                                # noqa: E402
import acceptance_e4pp_rows as e4pp                                # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

#: DERIVED, never listed: a hand-written list is a guard that goes stale
#: the next time a module is added.
INSTRUMENT = tuple(sorted(
    p.name for p in RUST_TESTS.glob("acceptance_e4pp*.py"))) + (
        "render_e4pp.py",)


def test_the_scanned_module_list_covers_every_module_of_this_instrument():
    assert len(INSTRUMENT) >= 7, INSTRUMENT
    for name in ("acceptance_e4pp.py", "acceptance_e4pp_arms.py",
                 "acceptance_e4pp_phases.py", "acceptance_e4pp_preflight.py",
                 "acceptance_e4pp_schema.py", "acceptance_e4pp_lock.py",
                 "render_e4pp.py"):
        assert name in INSTRUMENT


# ---------------------------------------------------------------- the lock

def test_the_runner_refuses_while_the_lock_is_unset(monkeypatch):
    """A pre-registration that can still be edited is not one."""
    monkeypatch.setattr(lock, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked" in str(e.value)


def test_the_runner_takes_its_LOCK_from_the_lock_module_and_not_its_own():
    """One place holds the sha, so the runner and the suite cannot
    disagree about which commit §1 is locked against."""
    src = (RUST_TESTS / "acceptance_e4pp.py").read_text()
    assert "BYTE_LOCK = \"" not in src
    assert "acceptance_e4pp_lock" in src
    assert runner.DOC == lock.DOC
    assert runner.RESULTS == lock.RESULTS


def test_H7_is_computed_AFTER_every_other_phase_it_censuses():
    """H7's second reading is "every `dropped` list this run wrote", so a
    phase computed after it would not be in that census."""
    main = (RUST_TESTS / "acceptance_e4pp.py").read_text()
    body = main[main.index("def main(argv)"):]
    for earlier in ("phase_h1(", "phase_h2_fragment(", "phase_h3_verdict_pair(",
                    "phase_h4_session(", "phase_h5_input(",
                    "phase_h6_session_key(", "phase_h8_nothing_else("):
        assert body.index(earlier) < body.index("phase_h7_instrument("), earlier


def test_the_lock_and_the_rows_digest_are_BOTH_checked_before_any_number():
    main = (RUST_TESTS / "acceptance_e4pp.py").read_text()
    body = main[main.index("def main(argv)"):]
    assert body.index("check_byte_lock()") < body.index("preflight_e4pp(")
    assert body.index("check_rows_digest()") < body.index("preflight_e4pp(")
    assert body.index("preflight_e4pp(") < body.index("copy_originals(")


def test_the_byte_lock_PASSES_on_the_real_document():
    ok = subprocess.run(["git", "cat-file", "-e", f"{lock.BYTE_LOCK}^{{commit}}"],
                        cwd=REPO, capture_output=True).returncode == 0
    if not ok:
        pytest.skip(f"lock commit {lock.BYTE_LOCK} is not in this checkout "
                    "— skipped BY NAME, not passed")
    rec = runner.check_byte_lock()
    assert rec["identical"] is True


# --------------------------------------------------------------- the paths

def test_every_location_is_an_environment_variable(monkeypatch):
    for key in runner.E4PP_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_e4pp()
    for key in runner.E4PP_ENV:
        assert key in str(e.value), key


def test_the_shared_phases_TARGET_key_is_the_one_E4prime_already_reads():
    """`SENSORIUM_E4PP_TARGET` lands under `sensorium_e4p_target` because
    `refocus_env` and `shim_census` read that key: the variable moved, the
    `paths` key did not."""
    assert runner.E4PP_ENV["SENSORIUM_E4PP_TARGET"] == "sensorium_e4p_target"
    assert set(runner.E4PP_ENV) == {
        "SENSORIUM_DRIVER", "SENSORIUM_E4_STORE", "SENSORIUM_BLOOMERY",
        "SENSORIUM_E4PP_TARGET", "SENSORIUM_DIR", "SENSORIUM_RUST_TARGET"}


def test_a_DRY_run_moves_every_location_to_its_own_sibling(monkeypatch):
    for key in runner.E4PP_ENV:
        monkeypatch.setenv(key, f"/nowhere/{key.lower()}")
    wet = runner.env_paths_e4pp()
    dry = runner.env_paths_e4pp(dry=True)
    assert dry["sensorium_dir"].name.endswith("-dry")
    assert dry["sensorium_e4p_target"].name.endswith("-dry")
    # ...and nothing else moves: the kept store, the clone and the driver
    # are the same inputs a real run reads.
    for key in ("sensorium_e4_store", "sensorium_bloomery",
                "sensorium_driver", "sensorium_rust_target"):
        assert dry[key] == wet[key], key


# -------------------------------------------------------------- the config

def test_the_corpus_target_is_a_FRESH_sibling_of_the_run_target(monkeypatch):
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    paths = {"sensorium_e4p_target": Path("/t/bloomery-target-e4pp")}
    cfg = runner.e4pp_config(paths)
    assert cfg["corpus_target"] == Path("/t/bloomery-target-e4pp-corpus")
    assert cfg["corpus_target_from_env"] is False


def test_the_corpus_carries_require_driver(monkeypatch):
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4pp_config({"sensorium_e4p_target": Path("/t/x")})
    assert cfg["corpus_args"] == list(e4pp.CORPUS_ARGS)
    assert "--require-driver" in cfg["corpus_args"]


def test_the_ceilings_are_section_1_4s(monkeypatch):
    """1800 s per `sensorium refocus`, and the whole LOOP bounded at 1 h 30
    min — §1.4's bounds, verbatim."""
    assert runner.REFOCUS_TIMEOUT == 1800
    assert runner.LOOP_BUDGET_S == 5400
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4pp_config({"sensorium_e4p_target": Path("/t/x")})
    assert cfg["refocus_timeout"] == 1800
    assert cfg["loop_budget_s"] == 5400


def test_the_full_row_table_is_section_1_1s_61(monkeypatch):
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4pp_config({"sensorium_e4p_target": Path("/t/x")})
    assert cfg["gate_n"] == 61 == cfg["gate_n_locked"]
    assert len(cfg["rows"]) == 61


def test_the_DRY_row_table_is_the_two_pairs_section_1_3_names():
    """"One expected granted, and `a_pager_can_be_shared_across_threads`" —
    and the dry run must show the strip clause fire, which is why the
    granted row is a real one from the table rather than a stub."""
    rows = runner.dry_rows()
    assert len(rows) == 2
    assert rows[0][1] == e4pp.ROWS[0][1]
    assert rows[1][1] == arms.PAGER_ROW
    assert rows[1][1] in e4pp.EXPECTED_WITHHELD
    assert rows[0][1] not in e4pp.EXPECTED_WITHHELD


def test_a_dry_config_carries_the_dry_flag_through(monkeypatch):
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4pp_config({"sensorium_e4p_target": Path("/t/x-dry")},
                             rows=runner.dry_rows())
    assert cfg["gate_n"] == 2
    assert cfg["gate_n_locked"] == 61


# --------------------------------------------------------------- the kills

def test_a_KILLED_invocation_is_named_by_the_KILLS_words_not_by_H1():
    stops = runner._stops({
        "numbers_read": True,
        "raw_pass2": {"killed": ["a_pager_can_be_shared_across_threads"],
                      "budget_exhausted": [], "n": 61, "measured": 61},
        "raw_h1": {"partition_as_predicted": False, "granted_n": 60,
                   "n": 61, "expected_granted_n": 57}})
    first = stops[0]
    assert "KILLED" in first
    assert "a number had already been read" in first
    assert "STOP" in first
    assert "kill 1" not in first
    assert any("kill 1" in s for s in stops[1:])


def test_a_kill_BEFORE_any_number_is_named_as_the_INFRASTRUCTURE_kill():
    stops = runner._stops({
        "numbers_read": False,
        "raw_pass2": {"killed": ["x"], "budget_exhausted": [], "n": 61,
                      "measured": 61}})
    assert stops
    assert "infrastructure" in stops[0]
    assert "relaunched from zero" in stops[0]
    assert "STOP" not in stops[0]


@pytest.mark.parametrize("phase, number", [
    ("raw_h2", "H2"), ("raw_h3", "H3"), ("raw_h4", "H4"),
    ("raw_h5", "H5"), ("raw_h6", "H6"), ("raw_h8", "H8")])
def test_a_miss_on_any_gated_phase_is_a_STOP_with_ITS_NUMBER(phase, number):
    """§1.4's kill 2: "a miss on H2, H3, H4, H5, H6 or H8 is a STOP with its
    number"."""
    stops = runner._stops({"numbers_read": True,
                           phase: {"verdict": "STOP", "as_predicted": False,
                                   "gate": "the gate"}})
    assert any(s.startswith(number) for s in stops), stops


def test_a_gated_miss_with_a_WHOLE_reading_is_a_STOP_of_the_subject():
    """The control for the two below: a phase that read everything it asked
    for and simply did not match the gate missed on the side the endpoint
    measures, and the sentence is the one it always was."""
    res = {"numbers_read": True,
           "raw_h3": {"verdict": "STOP", "as_predicted": False,
                      "gate": "the gate", "dropped": []}}
    assert any("This is a STOP of the subject" in s
               for s in runner._stops(res))
    side = runner.stop_sides(res)[0]
    assert (side["declared"], side["derived"]) == ("subject", "subject")
    assert side["agree"] is True


def test_a_gated_miss_the_READER_could_not_make_names_BOTH_sides():
    """E4″ gap 2. The `stop` sentence and the `.FAILED` marker both ended
    "This is a STOP of the subject" because the label hung off the endpoint
    id; on the real run H8's miss was this instrument's -- three green
    return codes and a case that had run. A phase that recorded a reason it
    could not READ something missed on the instrument's side, whatever the
    endpoint is gated on, and §1.4's kill 2 asks for both."""
    res = {"numbers_read": True,
           "raw_h8": {"verdict": "STOP", "as_predicted": False,
                      "gate": "the gate",
                      "dropped": ["`x` is among the 63 name(s) the listing "
                                  "printed under neither spelling"]}}
    stops = runner._stops(res)
    assert any("INSTRUMENT" in s and "under neither spelling" in s
               for s in stops), stops
    # BOTH, never one instead of the other.
    assert any("subject" in s for s in stops), stops
    side = runner.stop_sides(res)[0]
    assert (side["declared"], side["derived"]) == ("subject", "instrument")
    assert side["agree"] is False


def test_a_BLOCKED_reading_is_the_instruments_miss_too():
    """`as_predicted` null -- a short loop, a killed row -- is a reading
    nobody made, and naming it a STOP of the subject reports a finding
    about the tool from a number the run never got."""
    res = {"numbers_read": True,
           "raw_h2": {"verdict": "STOP", "as_predicted": None,
                      "gate": "the gate",
                      "dropped": ["59 of 61 invocation(s) ran"]}}
    side = runner.stop_sides(res)[0]
    assert side["derived"] == "instrument" and side["blocked"] is True


def test_a_miss_on_H7_is_a_STOP_OF_THE_INSTRUMENT_and_says_so():
    """§1.4's kill 2 again: a miss on H7 is distinguished IN THE RECORD from
    a STOP of the subject."""
    stops = runner._stops({"numbers_read": True,
                           "raw_h7": {"verdict": "STOP",
                                      "as_predicted": False,
                                      "gate": "the gate"}})
    assert any("INSTRUMENT" in s for s in stops), stops
    assert any("not of the subject" in s for s in stops), stops


def test_a_phase_that_PASSED_is_no_stop_at_all():
    assert runner._stops({"numbers_read": True,
                          "raw_h2": {"verdict": "PASS",
                                     "as_predicted": True}}) == []


def test_a_KEPT_STORE_that_changed_is_a_STOP():
    stops = runner._stops({"numbers_read": True,
                           "cleanup": {"kept_store_unchanged": False,
                                       "kept_census_differences": ["x"]}})
    assert any("KEPT store" in s for s in stops)


# ------------------------------------------------------- no box path here

BOX_PATHS = ("/" + "mnt/", "/" + "home/brice", "/" + "tmp/claude")


@pytest.mark.parametrize("name", INSTRUMENT)
def test_no_module_of_this_instrument_names_a_box_path(name):
    text = (RUST_TESTS / name).read_text()
    for needle in BOX_PATHS:
        assert needle not in text, f"{name} names {needle}"


@pytest.mark.parametrize("name", INSTRUMENT)
def test_every_module_of_this_instrument_is_under_800_lines(name):
    n = len((RUST_TESTS / name).read_text().splitlines())
    assert n <= 800, f"{name} is {n} lines"


TEST_FILES = sorted(p.name for p in (REPO / "tests").glob(
    "test_acceptance_e4pp*.py"))


@pytest.mark.parametrize("name", TEST_FILES)
def test_no_test_of_this_instrument_names_a_box_path(name):
    text = (REPO / "tests" / name).read_text()
    for needle in BOX_PATHS:
        assert needle not in text, f"{name} names {needle}"


@pytest.mark.parametrize("name", TEST_FILES)
def test_every_test_of_this_instrument_is_under_800_lines(name):
    """The ceiling above reads the INSTRUMENT's modules; this one reads the
    suite's own, which nothing did until 2026-09-08 --
    `test_acceptance_e4pp_phases.py` crossed 800 at `8dab703`, reached 932 by
    `e48e4e5`, and rode a release note that said every touched file was under
    the ceiling. The scan is derived from the same glob as the box-path scan,
    so a file added next slice is checked without anyone remembering to."""
    n = len((REPO / "tests" / name).read_text().splitlines())
    assert n <= 800, f"{name} is {n} lines"


def test_the_scan_would_actually_CATCH_a_box_path():
    sample = "STORE = Path('" + BOX_PATHS[0] + "extra/sensorium-dir/e4pp')"
    assert any(n in sample for n in BOX_PATHS)
    assert all(n not in "STORE = Path(os.environ['SENSORIUM_DIR'])"
               for n in BOX_PATHS)


# ------------------------------------------------------------ the launcher

def test_the_launcher_exports_every_variable_the_runner_REFUSES_without():
    """The launcher is ledger-local (gitignored), so this skips BY NAME
    where it is absent rather than passing over nothing. Where it is
    there, every one of the six locations, the three pins the guard needs
    and the `unset TMPDIR` are checked mechanically -- a launch that
    forgot one costs a detached run to discover."""
    launch = (REPO / ".superpowers" / "sdd"
              / "2026-09-08-sensorium-rung4-footprint" / "acceptance-e4pp"
              / "launch.sh")
    if not launch.is_file():
        pytest.skip("the launcher is ledger-local and not in this checkout")
    text = launch.read_text()
    for key in runner.E4PP_ENV:
        assert f"export {key}=" in text, key
    # The CLI resolves the driver through its own variable, and the phases
    # re-add it per child because `plain_env()` strips every `SENSORIUM_*`.
    assert "export SENSORIUM_CARGO_SENSORIUM=" in text
    # The three the scan of the 61 found: the guard refuses on any of them,
    # and the launcher satisfies it by EXPORTING rather than exempting.
    for key in ("PYTHONDONTWRITEBYTECODE", "SSL_CERT_DIR", "SSL_CERT_FILE"):
        assert f"export {key}=" in text, key
    assert "unset TMPDIR" in text
    assert "acceptance_e4pp.py" in text


def test_the_launcher_forwards_its_argv_so_a_DRY_run_is_reachable():
    launch = (REPO / ".superpowers" / "sdd"
              / "2026-09-08-sensorium-rung4-footprint" / "acceptance-e4pp"
              / "launch.sh")
    if not launch.is_file():
        pytest.skip("the launcher is ledger-local and not in this checkout")
    text = launch.read_text()
    assert '"$@"' in text
    # ...and passes NOTHING by default, so the measurement cannot take the
    # dry path by accident.
    assert "--dry\n" not in text.replace("\r", "")


# ------------------------------------------------- the entry's control flow

def _harness(monkeypatch, tmp_path, **over):
    """`main()` with every expensive step stubbed: the control flow is what
    is under test, and it is the thing most likely to break 1 h 20 into a
    detached run rather than here."""
    import time
    import acceptance_e4p_phases as eph
    import acceptance_e4pp_phases as ph
    import acceptance_e4pp_preflight as e4pre
    import acceptance_e4p_rows as rows
    sys.path.insert(0, str(REPO / "tests"))
    from test_acceptance_e4pp_phases import INJECTED, SESSION_PIN, _arm, _two

    base = tmp_path / "acceptance-e4pp"
    monkeypatch.setattr(runner, "BASE", base)
    monkeypatch.setattr(runner, "LOGS", base / "logs")
    monkeypatch.setattr(runner, "LEDGER", tmp_path)
    monkeypatch.setattr(runner, "RAW", tmp_path / "results-e4pp-raw.json")
    monkeypatch.setattr(runner, "RESULTS", tmp_path / "tracked.results.json")
    monkeypatch.setattr(runner, "check_byte_lock",
                        lambda: {"identical": True, "doc": "d.md"})
    monkeypatch.setattr(runner, "check_rows_digest",
                        lambda: {"identical": True, "sha256": "abc"})
    monkeypatch.setattr(runner, "env_paths_e4pp",
                        lambda dry=False: {k: tmp_path / k
                                           for k in runner.E4PP_ENV.values()})
    monkeypatch.setattr(e4pre, "preflight_e4pp", lambda paths, cfg: {
        "session_keys_differing": SESSION_PIN,
        "injected_session_key": INJECTED,
        "injected_session_key_choice": {"key": INJECTED, "skipped": []},
        "sensorium_version_metadata_probe": {"token": "0.8.5",
                                             "reason": None, "rc": 0}})
    monkeypatch.setattr(runner, "store_census", lambda store: {"n": 122})
    monkeypatch.setattr(runner, "copy_originals",
                        lambda kept, fresh, rows_: {"copied": len(rows_)})
    calls = {"arms": [], "h8": 0, "render": 0, "deadlines": []}

    def fake_pass_two(paths, cfg, on_first_number=None):
        if on_first_number:
            on_first_number("row 1 came back")
        two = _two()
        two["loop_deadline_monotonic"] = time.monotonic() + cfg[
            "loop_budget_s"]
        if len(cfg["rows"]) < 61:
            two["refocuses"] = two["refocuses"][:len(cfg["rows"])]
            two["n"] = two["measured"] = len(cfg["rows"])
        return two

    monkeypatch.setattr(runner, "pass_two", fake_pass_two)
    def fake_hashes(paths, block):
        for r in (block or {}).get("refocuses") or []:
            r.setdefault("rt_hashes_differ", over.get("hashes_differ", True))
        return block

    monkeypatch.setattr(ph, "read_rt_hashes", fake_hashes)

    def fake_run_arm(paths, cfg, arm_rows_, key, value, tag, deadline=None):
        calls["arms"].append((key, value, tag))
        calls["deadlines"].append(deadline)
        names = [r["name"] for r in arm_rows_]
        if tag == "armB":
            rec = _arm(key, value,
                       {n: {"licence": "WITHHELD", "changed": [key]}
                        for n in names})
        else:
            rec = _arm(key, value,
                       {n: {"session": SESSION_PIN + [INJECTED],
                            "arm": "armC"} for n in names}, arm="armC")
        rec["measured"], rec["budget_exhausted"] = rec["n"], []
        if not over.get("arm_pairs", True):
            for a in rec["refocuses"]:
                a["new_run"] = None
        return rec

    monkeypatch.setattr(runner.arms, "run_arm", fake_run_arm)

    def fake_h8(paths, cfg):
        calls["h8"] += 1
        return {"corpus_rc": 0, "pytest_rc": 0, "cargo_rc": 0,
                "spawned_test_fn_present": True, "verdict": "PASS",
                "as_predicted": True, "dropped": [], "gate": "g"}

    monkeypatch.setattr(ph, "phase_h8_nothing_else", fake_h8)
    monkeypatch.setattr(runner, "cleanup",
                        lambda paths, cfg, pins, kept: {
                            "kept_store_unchanged": True})
    monkeypatch.setattr(runner, "render_only",
                        lambda: calls.__setitem__("render",
                                                  calls["render"] + 1))
    monkeypatch.setattr(eph, "phase_h1", eph.phase_h1)
    return base, calls


def test_a_whole_run_writes_the_marker_the_raw_record_and_the_results(
        monkeypatch, tmp_path):
    base, calls = _harness(monkeypatch, tmp_path)
    rc = runner.main([])
    assert rc == 0, (tmp_path / "results-e4pp-raw.json").read_text()[:2000]
    assert (base / "e4pp.DONE").read_text().startswith("exit=0")
    assert not (base / "e4pp.FAILED").exists()
    raw = json.loads((tmp_path / "results-e4pp-raw.json").read_text())
    assert raw["numbers_read"] is True
    for key in ("raw_pass2", "raw_arm_b", "raw_arm_c", "raw_h1", "raw_h2",
                "raw_h3", "raw_h4", "raw_h5", "raw_h6", "raw_h7", "raw_h8"):
        assert key in raw, key
    assert [t for _k, _v, t in calls["arms"]] == ["armB", "armC"]
    assert calls["arms"][0][0] == arms.ARM_B_KEY
    assert calls["arms"][1][0] == "TMUX"          # the PIN's key, not a new one
    assert calls["h8"] == 1 and calls["render"] == 1
    record = json.loads((tmp_path / "tracked.results.json").read_text())
    assert record["endpoints"]["H6"]["injected_key"]["value"] == "TMUX"


def test_a_PLAIN_DRY_run_runs_neither_arm_nor_H8(monkeypatch, tmp_path):
    """§1.3's dry, as pre-registered: two pairs, arm A only."""
    base, calls = _harness(monkeypatch, tmp_path)
    rc = runner.main(["--dry"])
    assert rc == 0
    assert (base / "e4pp-dry.DONE").exists()
    assert not (base / "e4pp.DONE").exists()
    assert calls["arms"] == [] and calls["h8"] == 0
    raw = json.loads((tmp_path / "results-e4pp-raw-dry.json").read_text())
    assert raw["dry_arms"] is False
    assert raw["dry_check"]["arms_rehearsed"] is False
    assert raw["dry_check"]["arms_ok"] is None


def test_DRY_ARMS_rehearses_BOTH_arms_over_the_same_two_rows(monkeypatch,
                                                             tmp_path):
    """§1.3's dry is a MINIMUM, not a ceiling (controller, fix round 1).
    Four control invocations otherwise go unrehearsed until an hour into
    the real run."""
    base, calls = _harness(monkeypatch, tmp_path)
    rc = runner.main(["--dry-arms"])
    assert rc == 0
    assert (base / "e4pp-dry.DONE").exists()
    assert [t for _k, _v, t in calls["arms"]] == ["armB", "armC"]
    assert calls["h8"] == 0                    # H8 still does not run
    assert not (tmp_path / "tracked.results.json").exists()
    raw = json.loads((tmp_path / "results-e4pp-raw-dry.json").read_text())
    assert raw["dry_run"] is True and raw["dry_arms"] is True
    assert raw["dry_check"]["arms_rehearsed"] is True
    assert raw["dry_check"]["arms_ok"] is True
    assert "both control arms produced a pair" in raw["dry_check"]["reading"]


def test_a_DRY_ARM_that_produced_NO_PAIR_is_INFRASTRUCTURE(monkeypatch,
                                                           tmp_path):
    """"Each arm produced a pair for each row without exception" -- and an
    arm failure in a dry is infrastructure, not a STOP."""
    base, calls = _harness(monkeypatch, tmp_path, arm_pairs=False)
    rc = runner.main(["--dry-arms"])
    assert rc == 9
    assert (base / "e4pp-dry.FAILED").read_text().count("INFRASTRUCTURE")
    raw = json.loads((tmp_path / "results-e4pp-raw-dry.json").read_text())
    assert raw["dry_check"]["arms_ok"] is False
    assert raw["dry_check"]["arms"]["B"]["rows_without_a_pair"]


def test_a_DRY_run_never_writes_the_tracked_file(monkeypatch, tmp_path):
    base, calls = _harness(monkeypatch, tmp_path)
    rc = runner.main(["--dry"])
    assert rc == 0
    assert calls["render"] == 0
    assert not (tmp_path / "tracked.results.json").exists()
    assert (tmp_path / "results-e4pp-dry.results.json").is_file()
    raw = json.loads((tmp_path / "results-e4pp-raw-dry.json").read_text())
    assert raw["dry_run"] is True
    assert len(raw["config"]["rows"]) == 2
    # H5, H6 and H8 publish null WITH a reason -- the shape a dry run
    # exists to check.
    dry = json.loads((tmp_path / "results-e4pp-dry.results.json").read_text())
    for endpoint in ("H5", "H6", "H8"):
        for name in ("headline", "corpus_rc"):
            cell = dry["endpoints"][endpoint].get(name)
            if cell is None:
                continue
            assert cell["value"] is None and cell["dropped"], endpoint


def test_a_REFUSED_run_assembles_NOTHING_and_marks_FAILED(monkeypatch,
                                                          tmp_path):
    """A refusal measured nothing. Assembling would write a TRACKED
    `results.json` full of not-measured cells into `docs/`, where the next
    reader would take it for a record of a run."""
    base, calls = _harness(monkeypatch, tmp_path)

    def refuse():
        raise Refused("arm C has no key to inject")
    monkeypatch.setattr(runner, "check_rows_digest", refuse)
    rc = runner.main([])
    assert rc == 3
    assert (base / "e4pp.FAILED").read_text().startswith("exit=3")
    assert not (tmp_path / "tracked.results.json").exists()
    raw = json.loads((tmp_path / "results-e4pp-raw.json").read_text())
    assert "arm C has no key" in raw["refused"]


def test_a_STOP_marks_FAILED_and_STILL_writes_the_record(monkeypatch,
                                                         tmp_path):
    """§1.4's rule 5: the numbers already read stand."""
    import acceptance_e4pp_phases as ph
    base, calls = _harness(monkeypatch, tmp_path)
    monkeypatch.setattr(ph, "phase_h8_nothing_else", lambda paths, cfg: {
        "corpus_rc": 1, "pytest_rc": 0, "cargo_rc": 0,
        "spawned_test_fn_present": True, "verdict": "STOP",
        "as_predicted": False, "dropped": [], "gate": "three green"})
    rc = runner.main([])
    assert rc == 7
    assert (base / "e4pp.FAILED").read_text().startswith("exit=7")
    record = json.loads((tmp_path / "tracked.results.json").read_text())
    assert "H8 (kill 2)" in record["stop"]
    assert record["endpoints"]["H1"]["headline"]["value"] == 57


def test_a_DRY_run_that_does_NOT_show_the_strip_fire_is_INFRASTRUCTURE(
        monkeypatch, tmp_path):
    """§1.3: "a dry run under one build is not a dry run of this
    instrument, which is precisely E4′'s lesson. A dry run that does not
    show it has not checked the instrument: the launch does not happen, and
    that is infrastructure, not a STOP"."""
    base, calls = _harness(monkeypatch, tmp_path, hashes_differ=False)
    rc = runner.main(["--dry"])
    assert rc == 9
    marker = (base / "e4pp-dry.FAILED").read_text()
    assert "INFRASTRUCTURE, not a STOP" in marker
    raw = json.loads((tmp_path / "results-e4pp-raw-dry.json").read_text())
    assert raw["dry_check"]["ok"] is False
    assert raw["dry_check"]["did_not_show_it"]
    assert "stop" not in raw


def test_a_DRY_run_is_never_judged_by_the_SUBJECTS_gates():
    """A two-row table cannot meet §1.2's "granted 57", and an rc that said
    so would report a STOP where no measurement was made at all."""
    res = {"dry_run": True, "numbers_read": True,
           "raw_h1": {"partition_as_predicted": False, "granted_n": 2,
                      "n": 2, "expected_granted_n": 57},
           "raw_h2": {"verdict": "STOP", "gate": "g"}}
    assert runner._stops(res) == []
    assert runner._stops(dict(res, dry_run=False)) != []


def test_both_arms_run_under_the_LOOPs_OWN_deadline(monkeypatch, tmp_path):
    """§1.4 bounds "the whole loop", and arms B and C are part of it: they
    are handed `pass_two`'s own monotonic deadline, not a fresh one."""
    base, calls = _harness(monkeypatch, tmp_path)
    assert runner.main([]) == 0
    raw = json.loads((tmp_path / "results-e4pp-raw.json").read_text())
    assert calls["deadlines"] == [raw["raw_pass2"]["loop_deadline_monotonic"]] * 2
    assert all(d is not None for d in calls["deadlines"])


def test_an_INFRASTRUCTURE_kill_exits_9_and_a_STOP_exits_7():
    """§1.4's rules 4 and 5 part company on `numbers_read`, and so must the
    exit codes: one code for both made a relaunch-from-zero and a finding
    read the same to whatever is watching the marker."""
    before = {"numbers_read": False,
              "raw_pass2": {"killed": ["x"], "budget_exhausted": []}}
    after = {"numbers_read": True,
             "raw_pass2": {"killed": ["x"], "budget_exhausted": []}}
    assert runner._infrastructure(before) is True
    assert runner._infrastructure(after) is False
    assert runner._infrastructure({"numbers_read": False}) is False


def test_a_kill_BEFORE_any_number_exits_9_not_7(monkeypatch, tmp_path):
    import acceptance_e4pp_phases as ph
    base, calls = _harness(monkeypatch, tmp_path)

    def fake_pass_two(paths, cfg, on_first_number=None):
        """A loop that read NOTHING: every row killed before it printed a
        verdict or a licence, which is the only shape §1.4's rule 4
        describes."""
        rows_ = [{"index": i, "name": f"n{i}", "timed_out": True,
                  "kill_s": 1800, "verdict_word": None, "licence_word": None,
                  "licence_partition": {"licence": None}, "wall_s": 1800.0,
                  "pair": {"n": 0}}
                 for i in range(1, 62)]
        return {"refocuses": rows_, "n": 61, "measured": 61,
                "budget_exhausted": [], "loop_deadline_monotonic": 1.0,
                "killed": [r["name"] for r in rows_]}

    monkeypatch.setattr(runner, "pass_two", fake_pass_two)
    rc = runner.main([])
    assert rc == 9
    marker = (base / "e4pp.FAILED").read_text()
    assert "infrastructure" in marker
    assert "relaunched from zero" in marker
    raw = json.loads((tmp_path / "results-e4pp-raw.json").read_text())
    assert raw["kill_is_infrastructure"] is True


def test_a_kill_AFTER_a_number_still_exits_7(monkeypatch, tmp_path):
    base, calls = _harness(monkeypatch, tmp_path)

    def fake_pass_two(paths, cfg, on_first_number=None):
        sys.path.insert(0, str(REPO / "tests"))
        from test_acceptance_e4pp_phases import _two
        if on_first_number:
            on_first_number("row 1 came back")
        two = _two()
        two["killed"] = ["a_pager_can_be_shared_across_threads"]
        two["loop_deadline_monotonic"] = 1.0
        return two

    monkeypatch.setattr(runner, "pass_two", fake_pass_two)
    assert runner.main([]) == 7
    raw = json.loads((tmp_path / "results-e4pp-raw.json").read_text())
    assert raw["kill_is_infrastructure"] is False


# ================== fix round 2 ==================================

def test_a_cut_off_row_carries_THIS_records_bound_and_not_E4primes(
        monkeypatch, tmp_path):
    """Item 1. `run_arm` and `pass_two` both wrote E4′'s constant -- "the
    1 h 15 min loop bound was reached" -- into a record whose bound is
    1 h 30 min. The sentence comes from `cfg` now, derived from
    `LOOP_BUDGET_S`."""
    import acceptance_e4p_phases as eph
    monkeypatch.delenv("SENSORIUM_CORPUS_TARGET", raising=False)
    cfg = runner.e4pp_config({"sensorium_e4p_target": Path("/t/x")})
    assert cfg["not_run_bound"] == e4pp.bound_sentence(runner.LOOP_BUDGET_S)
    assert "1 h 30 min" in cfg["not_run_bound"]
    assert cfg["not_run_bound"] != eph.NOT_RUN_BOUND


def test_the_arms_write_that_sentence_and_not_the_imported_constant(
        monkeypatch):
    import time as _t
    import acceptance_e4p_phases as eph
    import acceptance_e4pp_arms as a
    import acceptance_e4p_rows as r
    monkeypatch.setattr(a.eph, "refocus_one",
                        lambda *args, **kw: pytest.fail("past the deadline"))
    rec = a.run_arm({}, {"not_run_bound": "the 1 h 30 min loop bound was "
                                          "reached before this invocation"},
                    a.arm_rows(r.ROWS), "K", "v", "armB",
                    deadline=_t.monotonic() - 1)
    said = {x["not_run"] for x in rec["refocuses"]}
    assert said == {"the 1 h 30 min loop bound was reached before this "
                    "invocation"}
    assert eph.NOT_RUN_BOUND not in said


def test_pass_two_takes_the_sentence_from_cfg_when_one_is_given():
    """The same fix on arm A's side, in the shared loop -- E4′ passes no
    such key and its sentence is byte for byte what it was."""
    src = (RUST_TESTS / "acceptance_e4p_phases.py").read_text()
    assert 'cfg.get("not_run_bound",' in src
    assert 'NOT_RUN_BOUND = ("the 1 h 15 min loop bound' in src


def test_EVERY_module_with_a_LOGS_name_is_assigned_by_the_runner():
    """Item 5. E4′'s first launch died fourteen seconds in on exactly this:
    a phase opening `logs_at(LOGS / …)` in a namespace nobody had set."""
    src = (RUST_TESTS / "acceptance_e4pp.py").read_text()
    main = src[:src.index("RUNNER = ")]
    for module in ("acceptance_e4pp_phases", "acceptance_e4pp_phases2",
                   "acceptance_e4pp_arms", "acceptance_e4pp_preflight"):
        text = (RUST_TESTS / f"{module}.py").read_text()
        if "LOGS: Path | None = None" not in text:
            continue
        alias = next(ln.split(" as ")[1].split()[0] for ln in main.splitlines()
                     if ln.startswith(f"import {module} as "))
        assert f"{alias}.LOGS = LOGS" in main, module


def test_the_marker_says_what_its_EXIT_CODE_MEANS(monkeypatch, tmp_path):
    """Item 6. 9 has two shapes and both are "relaunch from zero"; 7 is the
    one where the numbers stand. A marker carrying only the number left
    that to a reader's memory."""
    base, calls = _harness(monkeypatch, tmp_path, hashes_differ=False)
    assert runner.main(["--dry"]) == 9
    marker = (base / "e4pp-dry.FAILED").read_text()
    assert marker.startswith("exit=9\n")
    assert "RELAUNCH FROM ZERO" in marker
    assert "the launch does not happen" in marker


def test_the_marker_tells_the_two_shapes_of_9_APART(monkeypatch, tmp_path):
    base, calls = _harness(monkeypatch, tmp_path)

    def no_readings(paths, cfg, on_first_number=None):
        rows_ = [{"index": i, "name": f"n{i}", "timed_out": True,
                  "kill_s": 1800, "verdict_word": None, "licence_word": None,
                  "licence_partition": {"licence": None}, "wall_s": 1800.0,
                  "pair": {"n": 0}} for i in range(1, 62)]
        return {"refocuses": rows_, "n": 61, "measured": 61,
                "budget_exhausted": [], "loop_deadline_monotonic": 1.0,
                "killed": [r["name"] for r in rows_]}

    monkeypatch.setattr(runner, "pass_two", no_readings)
    assert runner.main([]) == 9
    marker = (base / "e4pp.FAILED").read_text()
    assert "RELAUNCH FROM ZERO" in marker
    assert "rule 4" in marker
    assert "the launch does not happen" not in marker


def test_a_STOP_marker_says_the_numbers_STAND(monkeypatch, tmp_path):
    import acceptance_e4pp_phases2 as ph2
    base, calls = _harness(monkeypatch, tmp_path)
    monkeypatch.setattr(ph2, "phase_h8_nothing_else", lambda paths, cfg: {
        "corpus_rc": 1, "pytest_rc": 0, "cargo_rc": 0,
        "spawned_test_fn_present": True, "verdict": "STOP",
        "as_predicted": False, "dropped": [], "gate": "three green"})
    monkeypatch.setattr(runner.ph, "phase_h8_nothing_else",
                        ph2.phase_h8_nothing_else)
    assert runner.main([]) == 7
    marker = (base / "e4pp.FAILED").read_text()
    assert "the numbers already read STAND" in marker
    assert "RELAUNCH FROM ZERO" not in marker
