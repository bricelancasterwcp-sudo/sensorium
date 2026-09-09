"""The meta a converted trace carries, the spools `sensorium ts ingest`
refuses, and the command's own surfaces.

The fixtures and the machinery that drives them are `tests/ts_spools.py`,
which also carries the provenance of every case. What a converted trace
HOLDS -- events, frames, fingerprints -- is `tests/test_ts_ingest.py`; the
two are one suite split at the 800-line ceiling.
"""
import json
import multiprocessing
import re
import subprocess
import sys
import time

import pytest

from tests.helpers import run_cli
from tests.ts_spools import (FIXTURES, REFUSING, copy_tree, ingest_case,
                             ingested, only_trace, run_ids_in)

__all__ = ["ingested"]      # a fixture, imported for pytest to find


def test_the_declaration_is_this_recorders_own(ingested):
    _spool, sdir, _result = ingested["async-chain"]
    meta = only_trace(sdir).meta
    assert meta["lang"] == "typescript"
    assert meta["recorder"] == "sensorium-ts 0.1.0"
    assert meta["fingerprint_basis"] == "per-task"
    assert meta["main_thread_ident"] == 1
    assert meta["capabilities"] == {
        "line": False, "locals": False, "return_value": True, "tasks": True,
        "threads": False, "children": False, "stdin": False, "output": False,
        "object_identity": False, "refocus": False, "err_flow": False}
    assert meta["caps"] == {"dbg": 200, "depth": 2, "sample": 8, "str": 100}
    assert meta["wire"] == 1
    assert meta["driver_version"] == "0.1.0"
    assert meta["node"] == "v24.16.0"
    assert meta["vitest"] == "4.1.9"
    assert meta["environment"] == "node"
    assert meta["harness"] == "vitest"
    assert meta["harness_args"] == ["run", "src/async.probe.test.ts"]
    assert meta["invocation"] == "20260909-094718-0a1b2c"
    assert meta["pid"] == 439886
    assert meta["thread_id_os"] == 0
    assert meta["is_main_thread"] is True
    assert meta["tests_seen"] == 6
    assert meta["files_transformed"] == 12
    assert meta["transform_excluded"] == {}
    assert meta["throw_flow_outside_frames"] == 0
    assert meta["unhandled_rejections"] == []


def test_harness_exit_rides_every_trace_that_was_witnessed(ingested):
    """The driver waits for the harness, not for its workers. What it
    witnessed is written where it was witnessed, on every trace of the
    invocation -- and the key is ABSENT when no `harness.json` exists,
    because a status nobody observed is not written at all."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    assert trace.meta["harness_exit"] == {"status": 0, "signal": None,
                                          "basis": "waited"}
    assert trace.meta["exit_status"] is None
    assert trace.meta["exit_status_basis"] == "unwitnessed"

    _spool2, sdir2, _r2 = ingested["each-names"]
    assert "harness_exit" not in only_trace(sdir2).meta


def test_test_file_is_root_relative(ingested):
    """`FILE_START` carries the absolute path vitest handed it; what the
    trace carries is the path relative to the invocation root, which is what
    `runs` prints and what a reader can compare across boxes."""
    _spool, sdir, _result = ingested["async-chain"]
    meta = only_trace(sdir).meta
    assert meta["test_file"] == "src/async.probe.test.ts"
    assert "test_files" not in meta


def test_truncated_values_are_counted_and_passed_through(ingested):
    """R14a: a `trunc` the runtime set rides into the trace untouched, and
    every one of them is counted once in `truncated_count`."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    cut = 0
    for e in trace.events(kind=("RETURN",)):
        value = (e.payload or {}).get("value") or {}
        if value.get("trunc"):
            cut += 1
    assert cut > 0, "the fanout's Timeout capture is cut by the 200-byte cap"
    assert trace.meta["truncated_count"] == cut


def test_source_hashes_are_keyed_by_the_absolute_path(ingested):
    _spool, sdir, _result = ingested["async-chain"]
    hashes = only_trace(sdir).meta["source_hashes"]
    assert set(hashes) == {"/w/probes/setup.mjs",
                           "/w/probes/src/async.probe.test.ts"}
    assert all(len(h) == 64 for h in hashes.values())


def test_a_run_id_is_stamped_with_the_container_s_own_start(ingested):
    """Not with the conversion's clock. Every trace of one invocation then
    sorts under the run it belongs to, whatever order the pool happened to
    convert them in."""
    _spool, sdir, result = ingested["async-chain"]
    run_id = run_ids_in(result.stdout)[0]
    meta = only_trace(sdir).meta
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(meta["start_ts"]))
    assert run_id.startswith(stamp + "-"), run_id
    assert re.fullmatch(r"[0-9a-f]{6}", run_id[len(stamp) + 1:]), run_id


def test_two_naming_rules_in_one_container_are_reported_as_mixed(ingested):
    """`task_name_basis` says which rule named THIS trace's tests. One
    container that used both is `mixed`, and neither of the two is a fair
    answer for it."""
    _spool, sdir, _result = ingested["outside-frame-throw"]
    meta = only_trace(sdir).meta
    assert meta["task_name_basis"] == "mixed"
    assert meta["task_name_conflicts"] == 1
    assert meta["tests_seen"] == 2


def test_the_end_of_a_cut_recording_is_dated_from_the_last_record(ingested):
    """No EXIT means nobody read the wall clock at the end. What can still be
    dated is the last record the container managed to write: its monotonic
    distance from BOOT, added to BOOT's wall clock. `info` prints that as the
    duration of the RECORDING, which is what it is."""
    _spool, sdir, _result = ingested["killed-mid-file"]
    meta = only_trace(sdir).meta
    records = [json.loads(ln) for ln in
               (FIXTURES / "killed-mid-file" / "439886-0.jsonl")
               .read_text().splitlines()[:-1] if ln.strip()]
    boot = records[0]
    last = [r for r in records if "ts" in r][-1]
    expected = boot["startTs"] + (last["ts"] - boot["ts"]) / 1e9
    assert meta["end_ts"] == pytest.approx(expected)
    assert meta["end_ts"] > meta["start_ts"]


@pytest.mark.parametrize("case", sorted(REFUSING))
def test_a_refused_spool_is_named_and_the_rest_still_convert(case, ingested):
    """R16 and the no-BOOT rule: the spool that cannot be read is refused BY
    NAME, the other spools in the same directory are converted anyway, and
    the run ends at exit 2 so nobody reads a partial ingest as a whole one."""
    _spool, sdir, result = ingested[case]
    assert result.returncode == 2
    bad = REFUSING[case]
    refused = [ln for ln in result.stdout.splitlines()
               if ln.startswith("refused: ")]
    assert len(refused) == 1, result.stdout
    assert bad in refused[0], refused[0]
    # ...and the good one is there, converted.
    assert len(run_ids_in(result.stdout)) == 1, result.stdout
    assert len(sorted((sdir / "traces").glob("*.db"))) == 1


def test_two_boot_records_name_two_runtimes(ingested):
    _spool, _sdir, result = ingested["duplicate-boot"]
    line = next(ln for ln in result.stdout.splitlines()
                if ln.startswith("refused: "))
    assert "two BOOT records" in line
    assert "two runtime instances wrote one spool" in line


def test_a_record_naming_a_frame_no_call_opened_is_refused(ingested):
    """Never a guessed frame. A row attached to the wrong activation is a
    confident wrong answer about the program, which is worse than a spool
    this converter says it could not read."""
    _spool, _sdir, result = ingested["unknown-frame"]
    line = next(ln for ln in result.stdout.splitlines()
                if ln.startswith("refused: "))
    assert "7301-0.jsonl" in line
    assert "names frame 9, which no CALL opened" in line


def test_a_record_that_is_not_the_shape_the_wire_declares_is_refused(tmp_path):
    """A record missing a key wire 1 declares is a spool this converter
    cannot read: named and refused, never a traceback out of a worker that
    takes the pool and every spool beside it down with it."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / "each-names", spool)
    path = spool / "439934-0.jsonl"
    lines = path.read_text().splitlines()
    broken = [ln for ln in lines]
    for i, ln in enumerate(broken):
        rec = json.loads(ln)
        if rec["e"] == "CALL":
            del rec["p"]
            broken[i] = json.dumps(rec)
            break
    path.write_text("\n".join(broken) + "\n")

    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                sensorium_dir=sdir)
    assert r.returncode == 2, f"{r.stdout}{r.stderr}"
    assert "is not the shape wire 1 declares" in r.stdout, r.stdout
    assert "KeyError" in r.stdout, r.stdout
    # ...and the half-written trace is not left behind for `runs` to list.
    assert sorted((sdir / "traces").glob("*")) == []


def test_re_ingesting_refuses_and_names_the_marker(tmp_path):
    """P6: `ingested.json` is the record that this directory has been
    converted. A second ingest would mint a second set of run ids for one
    recording, and the store would hold each container twice."""
    spool, sdir, first = ingest_case("each-names", tmp_path)
    assert first.returncode == 0, f"{first.stdout}{first.stderr}"
    marker = json.loads((spool / "ingested.json").read_text())
    assert marker["run_ids"] == run_ids_in(first.stdout)
    assert marker["refused"] == []

    again = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                    sensorium_dir=sdir)
    assert again.returncode == 2
    assert "ingested.json" in (again.stdout + again.stderr)


def test_a_refused_spool_is_recorded_in_the_marker(tmp_path):
    spool, _sdir, result = ingest_case("no-boot", tmp_path)
    assert result.returncode == 2
    marker = json.loads((spool / "ingested.json").read_text())
    assert marker["refused"] == ["7101-0.jsonl"]
    assert marker["run_ids"] == run_ids_in(result.stdout)


def test_a_missing_spool_directory_is_a_bad_call(tmp_path):
    r = run_cli(["ts", "ingest", str(tmp_path / "nope")], cwd=tmp_path,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2
    assert "nope" in r.stderr


def test_a_directory_with_no_invocation_record_is_a_bad_call(tmp_path):
    spool = tmp_path / "spool"
    spool.mkdir()
    (spool / "1-0.jsonl").write_text("")
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2
    assert "invocation.json" in r.stderr


def test_a_spool_with_no_boot_names_the_file():
    from sensorium.ts import spool
    with pytest.raises(spool.SpoolError) as e:
        spool.read(FIXTURES / "no-boot" / "7101-0.jsonl")
    assert "7101-0.jsonl" in str(e.value)


def test_a_torn_final_line_is_dropped_and_not_refused(ingested):
    """A container killed mid-`appendFileSync` leaves half a line. That is
    the tail this recorder declares unknowable, not a corrupt file: the line
    is dropped, the trace says `incomplete`, and nothing counts the loss."""
    from sensorium.ts import spool as spool_mod
    sp = spool_mod.read(FIXTURES / "killed-mid-file" / "439886-0.jsonl")
    assert sp.torn_tail is True
    assert sp.exit is None
    assert len(sp.records) == 119   # 120 whole lines, one of them BOOT


def test_a_malformed_line_anywhere_else_is_a_refusal(tmp_path):
    """...and only the LAST line gets that benefit. A broken line in the
    middle is a corrupt file, and reading past it would silently drop a
    record the container did finish writing."""
    from sensorium.ts import spool as spool_mod
    good = (FIXTURES / "each-names" / "439934-0.jsonl").read_text().splitlines()
    bad = tmp_path / "9-0.jsonl"
    bad.write_text("\n".join(good[:5] + ["{not json"] + good[5:]) + "\n")
    with pytest.raises(spool_mod.SpoolError) as e:
        spool_mod.read(bad)
    assert "line 6" in str(e.value)
    assert "9-0.jsonl" in str(e.value)


def test_a_line_that_is_not_a_record_is_refused(tmp_path):
    """Every line carries an `e` naming its kind, and it is a string. A
    line that carries something else is not a record this converter can
    dispatch on."""
    from sensorium.ts import spool as spool_mod
    bad = tmp_path / "9-0.jsonl"
    bad.write_text('{"e": 7}\n')
    with pytest.raises(spool_mod.SpoolError) as e:
        spool_mod.read(bad)
    assert "line 1 is not a record" in str(e.value)


def test_the_pool_and_the_single_process_answer_the_same(tmp_path):
    """`--jobs 1` runs in this process; anything more runs a pool. Two paths
    to one answer, held on a directory with more than one spool so the pool
    is really taken -- and one of those spools is refused, which is the part
    worth checking across a process boundary: a refusal must come back as a
    VALUE the parent can print, not as an exception that kills the pool."""
    _s1, sdir1, one = ingest_case("no-boot", tmp_path / "one", jobs=1)
    _s2, sdir2, many = ingest_case("no-boot", tmp_path / "many", jobs=4)
    assert one.returncode == many.returncode == 2
    assert _refusals(one.stdout) == _refusals(many.stdout)
    a = only_trace(sdir1)
    b = only_trace(sdir2)
    assert a.task_fingerprints() == b.task_fingerprints()
    assert a.fingerprints() == b.fingerprints()
    assert a.meta["truncated_count"] == b.meta["truncated_count"]


def _refusals(stdout: str) -> list[str]:
    """The refusal lines, with the spool's absolute path -- which differs
    between two ingests of two copies -- taken back out."""
    return [ln.split(": ", 2)[-1].rsplit("/", 1)[-1]
            for ln in stdout.splitlines() if ln.startswith("refused: ")]


def test_the_help_speaks_this_recorders_language_and_no_other(tmp_path):
    """Every word a reader of a TypeScript trace meets is this recorder's.
    A help line that said `asyncio`, `coroutine` or `cargo` would be naming
    machinery this command has nothing to do with."""
    for args in (["ts", "--help"], ["ts", "ingest", "--help"]):
        r = subprocess.run([sys.executable, "-m", "sensorium", *args],
                           cwd=tmp_path, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        low = r.stdout.lower()
        for word in ("asyncio", "coroutine", "python", "rust", "cargo",
                     "generator", "sys.monitoring"):
            assert word not in low, f"{args}: {word!r} in\n{r.stdout}"


def test_invocation_round_trips_through_json():
    from sensorium.ts.invocation import Invocation
    data = json.loads((FIXTURES / "async-chain" / "invocation.json").read_text())
    inv = Invocation.from_json(data)
    assert inv.harness == "vitest"
    assert inv.harness_args == ["run", "src/async.probe.test.ts"]
    assert inv.root == "/w/probes"
    assert inv.to_json() == data


def test_the_pool_is_spawned_not_forked():
    """A forked worker inherits the parent's threads, its sqlite handles and
    its signal dispositions; `spawn` is the only context this converter is
    written against."""
    from sensorium.ts import ingest
    assert ingest.CONTEXT == "spawn"
    assert multiprocessing.get_context(ingest.CONTEXT) is not None
