"""The meta a converted trace carries, the spools `sensorium ts ingest`
refuses, and the command's own surfaces.

The fixtures and the machinery that drives them are `tests/ts_spools.py`,
which also carries the provenance of every case. What a converted trace
HOLDS -- events, frames, fingerprints -- is `tests/test_ts_ingest.py`, and
how the converter RUNS its work -- the pool, and a worker that dies -- is
`tests/test_ts_ingest_pool.py`; the three are one suite, split twice at the
800-line ceiling.
"""
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.helpers import run_cli
from tests.ts_spools import (CASES, FIXTURES, REFUSING, copy_tree,
                             ingest_case, ingested, only_trace,
                             run_ids_in)

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
    assert meta["exit_self_reported"] == {"code": None, "signal": "SIGTERM"}


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


def test_a_second_boot_met_late_leaves_no_trace_behind(ingested):
    """The refusal above moved into the WALK (A3), and a build already under
    way is what pays for it: the second BOOT is met after the builder has
    written rows, so `convert` aborts the build and unlinks the temporary
    file it had reserved. What the store holds afterwards is the sibling
    spool's trace and nothing else -- no `.tmp` trio, no half-written `.db`
    that `runs` would list."""
    _spool, sdir, result = ingested["duplicate-boot"]
    assert result.returncode == 2
    line = next(ln for ln in result.stdout.splitlines()
                if ln.startswith("refused: "))
    assert REFUSING["duplicate-boot"] in line
    assert sorted(q.suffix for q in (sdir / "traces").iterdir()) == [".db"]


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


def _without_counter(spool: Path, harness: str) -> None:
    """Strip every record the setup file writes, and say which harness ran.

    A spool with no SEEN and no FILE_START is what `node --test` leaves:
    that harness runs no setup file at all. No fixture is one, because
    every recorded fixture came from a vitest probe, so one is made here
    out of a vitest spool with the setup file's records taken back out.
    """
    path = next(spool.glob("*.jsonl"))
    kept = [line for line in path.read_text().splitlines()
            if json.loads(line)["e"] not in ("SEEN", "FILE_START")]
    path.write_text("\n".join(kept) + "\n")
    record = json.loads((spool / "invocation.json").read_text())
    record["harness"] = harness
    record["vitest"] = None
    (spool / "invocation.json").write_text(json.dumps(record, indent=2) + "\n")


def test_a_spool_whose_counter_never_ran_carries_no_count(tmp_path):
    """R38. `tests_seen` was written from a counter initialised at zero,
    whatever the spool said, so every `node --test` trace claimed a
    measurement nobody took. The key is written only where something in
    the spool says the counter ran -- a SEEN or a FILE_START -- or where
    the invocation was vitest, whose setup file always runs."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / "each-names", spool)
    _without_counter(spool, "node-test")
    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, f"{r.stdout}{r.stderr}"
    meta = only_trace(sdir).meta
    assert "tests_seen" not in meta
    # The container's other counts are untouched: this is one key, not a
    # verdict about the spool.
    assert meta["task_name_conflicts"] == 0
    assert [t.name for t in only_trace(sdir).tasks()]


def test_a_vitest_spool_that_registered_nothing_still_counts_its_zero(
        tmp_path):
    """The other side of the same rule. vitest's setup file runs whether
    or not the file registers a test, so a vitest invocation's zero IS a
    measurement -- and dropping it would lose the shortfall the clause
    exists to state."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / "each-names", spool)
    _without_counter(spool, "vitest")
    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, f"{r.stdout}{r.stderr}"
    assert only_trace(sdir).meta["tests_seen"] == 0


# --------------------------------------------------------------------------
# fix round 1


def test_a_container_that_saw_its_own_ending_says_so(ingested):
    """R21. `process.on('exit')` reports a code the container chose, not the
    status it was reaped with, so it is not `exit_status` -- but it IS a
    thing the container witnessed about itself, and a witnessed fact this
    converter read and dropped would be the founding failure wearing the
    opposite hat. It is kept under a name that says whose observation it is,
    beside an `exit_status` that stays null."""
    _spool, sdir, _result = ingested["outside-frame-throw"]
    meta = only_trace(sdir).meta
    assert meta["exit_self_reported"] == {"code": 1, "signal": None}
    assert meta["exit_status"] is None
    assert meta["exit_status_basis"] == "unwitnessed"


def test_a_container_torn_down_by_a_signal_still_says_how(ingested):
    """R13 and R21 together: vitest's teardown signals its workers, and a
    container that caught the signal wrote an EXIT with no code and the
    signal's name. That EXIT finalizes the trace -- the container lived long
    enough to say what happened to it."""
    _spool, sdir, _result = ingested["capped-names"]
    meta = only_trace(sdir).meta
    assert meta["exit_self_reported"] == {"code": None, "signal": "SIGTERM"}
    assert meta["incomplete"] is False


def test_a_container_that_never_got_to_say_carries_no_claim(ingested):
    """...and the key is ABSENT where there was no EXIT at all. A `code`
    of null there would read as a container that ended without choosing
    one, which is a different fact from a container that was killed before
    it could speak."""
    _spool, sdir, _result = ingested["killed-mid-file"]
    meta = only_trace(sdir).meta
    assert "exit_self_reported" not in meta
    assert meta["incomplete"] is True


#: Every table a converted trace holds rows in. The durable and the
#: non-durable writer must produce the same trace, table for table: the mode
#: is about WHEN rows become visible outside the connection, never about
#: which rows there are.
TRACE_TABLES = ("code_objects", "frames", "events", "output", "tasks",
                "fingerprints", "task_fingerprints")

#: Every fixture whose spool CONVERTS, which is the whole set minus the three
#: the converter must refuse: those end at exit 2 with no second trace to
#: compare. `killed-mid-file` stays in -- its spool is torn mid-line, the
#: Builder finishes it as an `incomplete` trace, and an incomplete trace is
#: exactly the shape a reader would least expect two writers to agree on.
DURABLE_CASES = [case for case in CASES if case not in REFUSING]


def sole_spool(case: str) -> Path:
    """The one `<pid>-<threadId>.jsonl` a converting fixture holds."""
    spools = sorted((FIXTURES / case).glob("*.jsonl"))
    assert len(spools) == 1, f"{case} holds {len(spools)} spools, not 1"
    return spools[0]


@pytest.mark.parametrize("case", DURABLE_CASES)
def test_a_trace_is_identical_whether_the_writer_was_durable(case, tmp_path):
    """A1's equivalence, at the smallest scale the gate is made of.

    The converter builds with `durable=False` -- one transaction, no fsync
    per batch -- and the equivalence gate (spec 3.5) says the trace it
    produces must not have changed. Here the same spool is built twice with
    the same minted run id, once in each mode, and every row of every table
    plus the whole `meta` table is compared. A faster converter that writes
    a different trace has changed the product, not the cost.

    Spec 6 asks this of the `tests/fixtures/ts-spools/` fixtures rather than
    of one of them, and the difference is not decoration: `async-chain` alone
    exercises no `UNWIND`, no capped name, no `#2` activation, no torn tail
    and no missing EXIT, and the gate it stands in for converted 372 spools
    of every shape the lens had.
    """
    from sensorium.ts import build, invocation, spool

    inv = invocation.Invocation.from_json(json.loads(
        (FIXTURES / case / "invocation.json").read_text()))
    paths = {}
    for durable in (True, False):
        # Read the spool afresh for each build: the builder consumes it.
        sp = spool.read(sole_spool(case))
        path = tmp_path / f"durable-{durable}.db"
        build.Builder(sp, inv, None, None, path, "20260101-000000-aaaaaa",
                      durable=durable).build()
        paths[durable] = path

    a = sqlite3.connect(paths[True])
    b = sqlite3.connect(paths[False])
    try:
        written = {}
        for table in TRACE_TABLES:
            sql = f"SELECT * FROM {table} ORDER BY rowid"
            rows = a.execute(sql).fetchall()
            assert rows == b.execute(sql).fetchall(), table
            written[table] = len(rows)
        # A comparison over empty tables proves nothing, so what every case
        # must actually have filled is pinned: the three tables no converted
        # spool can leave empty. `output` is empty on all of them -- the
        # TypeScript recorder declares no output capability -- and an empty
        # pair is still one of the seven the gate compares.
        assert min(written["code_objects"], written["frames"],
                   written["events"]) > 0, written
        assert written["output"] == 0
        sql = "SELECT key, value FROM meta ORDER BY key"
        assert a.execute(sql).fetchall() == b.execute(sql).fetchall()
    finally:
        a.close()
        b.close()


def test_the_incomplete_claim_is_written_before_anything_is_read(tmp_path):
    """R22a, the contract's literal rule: `incomplete` is written TRUE at
    the start and false only after the finalize pass. A build that dies half
    way must leave a trace that CLAIMS to be unfinished -- an absent key
    reads as the finalized value, and the refusal rule would then wave
    through a file with every required key missing."""
    from sensorium.store import db
    from sensorium.ts import build, invocation, spool

    sp = spool.read(FIXTURES / "each-names" / "439934-0.jsonl")
    inv = invocation.Invocation.from_json(
        json.loads((FIXTURES / "each-names" / "invocation.json").read_text()))
    path = tmp_path / "half.db"
    builder = build.Builder(sp, inv, None, None, path, "20260101-000000-aaaaaa")
    # Nothing converted yet: exactly the state an interrupted build leaves.
    assert db.get_meta(builder.w._conn, "incomplete") is True
    builder.abort()


def test_the_cap_is_counted_wherever_it_bit(ingested):
    """R14a. Three flags say a consumer string was cut and they are three
    different facts: `name_trunc` on a test's name, `trunc` on a message,
    `type_trunc` on a type name. `truncated_count` is how many captures the
    caps clipped, so every one of them counts once."""
    _spool, sdir, _result = ingested["capped-names"]
    trace = only_trace(sdir)
    # one SEEN + one TASK name_trunc, one trunc and one type_trunc on the
    # RAISE's exc; the UNWIND's copy of that exc counts too, since it is a
    # second capture the cap bit.
    assert trace.meta["truncated_count"] == 6

    raise_events = list(trace.events(kind=("RAISE",)))
    assert len(raise_events) == 1
    exc = raise_events[0].payload["exc"]
    assert exc["trunc"] is True and exc["type_trunc"] is True
    assert len(exc["msg"].encode()) == 200
    assert len(exc["type"].encode()) == 200

    (frame,) = [f for f in trace.frames() if f.closed_by == "unwind"]
    assert frame.unwind_exc["type_trunc"] is True


def test_a_repeated_activation_keeps_the_number_the_recorder_gave_it(
        ingested):
    """R17. `#k` tells two runs of ONE test apart, it is the recorder's own
    suffix rather than the harness's, and it is added after the cut -- so it
    travels into the `tasks` row exactly as the wire spelled it."""
    _spool, sdir, _result = ingested["capped-names"]
    trace = only_trace(sdir)
    names = [t.name for t in trace.tasks()]
    assert names[1] == "retries the flaky one#2"
    assert len(names[0].encode()) == 200
    assert {name for name, _h, _n in trace.task_fingerprints().values()} == \
        set(names)


def test_a_run_id_is_claimed_by_creating_the_file(tmp_path):
    """R22c. Two spawn workers convert two containers of one invocation, so
    they mint from the same second and collide on the stamp by design. The
    `O_EXCL` create is one atomic step: the loser draws again, where a pair
    that merely LOOKED could both have looked before either wrote."""
    from sensorium.ts import ingest as ingest_mod

    traces = tmp_path / "traces"
    traces.mkdir()
    run_id, tmp = ingest_mod._reserve(traces, 1788965244.0)
    assert tmp.exists() and tmp.stat().st_size == 0
    assert tmp.name == f".{run_id}.db.tmp"
    # A second reservation cannot take the name the first one holds.
    second, tmp2 = ingest_mod._reserve(traces, 1788965244.0)
    assert second != run_id and tmp2 != tmp


def test_a_worker_that_dies_still_leaves_the_marker(tmp_path, monkeypatch):
    """P6 does not care WHY a run stopped. Traces that converted before the
    failure are in the store, and the marker is the only record of which
    ones -- without it a re-ingest would mint a second run id for a
    container that already converted."""
    from sensorium.ts import ingest as ingest_mod

    spool = _two_good_spools(tmp_path)
    real = ingest_mod._worker
    calls = []

    def flaky(job):
        calls.append(job)
        if len(calls) == 2:
            raise RuntimeError("the disk went away")
        return real(job)

    monkeypatch.setattr(ingest_mod, "_worker", flaky)
    sdir = tmp_path / "sdir"
    with pytest.raises(ingest_mod.IngestError) as e:
        ingest_mod.ingest_dir(spool, sdir, jobs=1)
    assert "RuntimeError: the disk went away" in str(e.value)

    # The first container's trace is in the store...
    dbs = sorted((sdir / "traces").glob("*.db"))
    assert len(dbs) == 1, [p.name for p in dbs]
    # ...and the marker names it and says what stopped the run.
    marker = json.loads((spool / "ingested.json").read_text())
    assert marker["run_ids"] == [dbs[0].stem]
    assert marker["refused"] == []
    assert marker["error"] == "RuntimeError: the disk went away"


def test_a_run_that_died_is_still_a_run_that_happened(tmp_path, monkeypatch):
    """...and a re-ingest of that directory is refused by name, exactly as a
    re-ingest of a run that finished. The marker is the claim, and a partial
    ingest is the case where converting again would do the most damage."""
    from sensorium.ts import ingest as ingest_mod

    spool = _two_good_spools(tmp_path)
    monkeypatch.setattr(ingest_mod, "_worker",
                        lambda job: (_ for _ in ()).throw(RuntimeError("nope")))
    with pytest.raises(ingest_mod.IngestError):
        ingest_mod.ingest_dir(spool, tmp_path / "sdir", jobs=1)

    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2
    assert "ingested.json" in (r.stdout + r.stderr)


def _two_good_spools(tmp_path):
    """A spool directory with two containers that both convert: `no-boot`'s
    whole spool, and a copy of it re-stamped with a second pid."""
    spool = tmp_path / "spool"
    spool.mkdir(parents=True)
    (spool / "invocation.json").write_bytes(
        (FIXTURES / "no-boot" / "invocation.json").read_bytes())
    lines = (FIXTURES / "no-boot" / "7102-0.jsonl").read_text().splitlines()
    (spool / "7102-0.jsonl").write_text("\n".join(lines) + "\n")
    boot = json.loads(lines[0])
    boot["pid"] = 7103
    (spool / "7103-0.jsonl").write_text(
        "\n".join([json.dumps(boot)] + lines[1:]) + "\n")
    return spool


# -- what `info` prints about those endings ---------------------------------
# The three keys above are two different processes' endings plus what this
# one said about its own, and the tests above check that the CONVERTER keeps
# them apart. These check that the READER does too: a fact kept apart in
# meta and merged on the screen is merged.


def _info_of(sdir):
    trace = only_trace(sdir)
    r = run_cli(["info", trace.meta["run_id"]], cwd=sdir.parent,
                sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_info_prints_a_self_reported_code_saying_nobody_waited(ingested):
    """The code the container chose, with the words that stop it being read
    as a status somebody observed -- beside a harness exit that WAS."""
    _spool, sdir, _result = ingested["outside-frame-throw"]
    out = _info_of(sdir)
    assert "container exit: self-reported code 1 (nobody waited)" in out, out
    assert "exit: unwitnessed" in out, out


def test_info_prints_a_self_reported_signal_by_name(ingested):
    """A container torn down by a signal chose no code, and the line says
    the signal instead. Printing `code None` here is the failure the whole
    exit rule exists to stop."""
    _spool, sdir, _result = ingested["capped-names"]
    out = _info_of(sdir)
    assert ("container exit: self-reported signal SIGTERM (nobody waited)"
            in out), out
    assert "code None" not in out and "code null" not in out, out


def test_info_prints_no_container_exit_line_where_there_was_no_record(
        ingested):
    """Absent key, absent line: a container killed before it could speak is
    not one that ended at 0, and the reader says nothing rather than a
    zero."""
    _spool, sdir, _result = ingested["killed-mid-file"]
    out = _info_of(sdir)
    assert "container exit:" not in out, out
    assert "INCOMPLETE" in out, out


def _ts_trace(tmp_path, **meta):
    """A minimal TypeScript trace, built through the vector builder so a
    test and a vector cannot describe two different trace shapes."""
    from tests.vectors import build
    base = json.loads((VECTOR_DIR / "v29-runs-file-header.json").read_text())
    body = {**base, "meta": {**base["meta"], **meta}}
    sdir = tmp_path / "sdir"
    build(body, sdir, [VECTOR_RUN])
    return sdir


VECTOR_DIR = (FIXTURES.parent.parent.parent / "docs" / "trace-format"
              / "vectors")
VECTOR_RUN = "20260101-000000-aaaaaa"


def test_info_says_an_exit_record_carried_neither_rather_than_dropping_it(
        tmp_path):
    """The third state of `exit_self_reported`. An EXIT record that named
    neither a code nor a signal is a record, and a missing line means "no
    EXIT record" -- so this one is said rather than silently dropped, the
    same way `focus` distinguishes an absent key from a recorded empty one.
    """
    sdir = _ts_trace(tmp_path,
                     exit_self_reported={"code": None, "signal": None})
    out = _info_of(sdir)
    assert ("container exit: self-reported, but the record carries neither "
            "a code nor a signal") in out, out
    assert "code None" not in out, out


def test_an_older_converter_s_trace_prints_none_of_these_lines(tmp_path):
    """Every line of the TypeScript block is gated on the meta key it
    reports, never on the language -- the rule the rest of `info` follows.
    A trace whose converter wrote none of them says less, and says nothing
    it cannot support.

    `tests:` is the one line with a half that is not a meta key. Its task
    count comes from the trace's own TASK rows, so it prints on any
    TypeScript trace that has them; what the missing `tests_seen` takes
    away is the CLAUSE, which is the half that is a claim about the
    harness (R38). Asserted below rather than dropped, because "the line
    is gone" and "the line lost its clause" are different outcomes and
    only one of them is this one.
    """
    dropped = {k: None for k in
               ("harness", "harness_args", "harness_exit", "pid", "ppid",
                "thread_id_os", "is_main_thread", "test_file", "vitest",
                "environment", "exit_self_reported", "tests_seen",
                "task_name_basis", "task_name_conflicts",
                "files_transformed", "transform_excluded",
                "unhandled_rejections", "throw_flow_outside_frames")}
    base = json.loads((VECTOR_DIR / "v29-runs-file-header.json").read_text())
    meta = {k: v for k, v in base["meta"].items() if k not in dropped}
    from tests.vectors import build
    sdir = tmp_path / "sdir"
    build({**base, "meta": meta}, sdir, [VECTOR_RUN])
    out = _info_of(sdir)
    for absent in ("harness:", "container:", "container exit:",
                   "files:", "unhandled rejections:",
                   "throw flow outside frames:"):
        assert absent not in out, f"{absent!r} on a trace with no key\n{out}"
    # The task count is the trace's own; the harness clause is not there.
    assert "tests: 1 as tasks\n" in out, out
    assert "seen by the harness" not in out, out
    # ...and the interpreter line still names what it does know, with no
    # empty parenthesis where the harness and environment would have been.
    assert "node v24.16.0  env:" in out, out


def test_info_withholds_the_rejection_count_on_an_incomplete_trace(ingested):
    """The zero is measured only where the counting finished. A container
    killed mid-file counted as far as it got, and a printed `unhandled
    rejections: 0` there would read as proof none happened -- the
    `late_writes` precedent, on a count whose complete form IS printed at
    zero two lines up in this file."""
    _spool, sdir, _result = ingested["killed-mid-file"]
    out = _info_of(sdir)
    assert "INCOMPLETE" in out, out
    assert "unhandled rejections:" not in out, out
    # ...and the harness's own signalled ending still prints, because the
    # DRIVER witnessed that and it is not this container's to lose.
    assert "harness: vitest run src/async.probe.test.ts  exit: signal " \
           "SIGKILL (waited)" in out, out


# -- the command as typed (R26) ---------------------------------------------

def test_the_command_the_reader_is_shown_is_the_one_that_was_typed(ingested):
    """R26. `harness` is a KIND and `harness_args` is what survived the
    driver's own consumption; joining them builds a command nobody ran --
    it drops the `npx` this run was started with, and elsewhere the user's
    `--root`. `invocation.json` carries the typed tokens and the converter
    spends them on `meta.harness_command`, which is what both readers
    print."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    assert trace.meta["harness_command"] == [
        "npx", "vitest", "run", "src/async.probe.test.ts"]
    assert trace.meta["harness"] == "vitest"          # the kind, unchanged
    assert trace.meta["harness_args"] == ["run", "src/async.probe.test.ts"]
    out = _info_of(sdir)
    assert ("harness: npx vitest run src/async.probe.test.ts  "
            "exit: 0 (waited)") in out, out
    assert "harness: vitest run" not in out, out
    r = run_cli(["runs"], cwd=sdir.parent, sensorium_dir=sdir)
    assert ("npx vitest run src/async.probe.test.ts  exit:0 (waited)"
            in r.stdout), r.stdout
    assert ": vitest run" not in r.stdout, r.stdout


def test_a_spool_record_that_predates_the_key_still_names_a_command(
        ingested):
    """The fallback, and the ten fixtures that exercise it. Only
    `async-chain`'s `invocation.json` carries `command`; the rest are the
    OLDER record shape, and `Invocation.from_json` reads its absence as
    `[]` rather than refusing a spool directory it can otherwise finish.
    The converter then writes no `harness_command` key at all -- an absent
    key is a record that was never written -- and the readers fall back to
    what they printed before, which is the best a trace that never stored
    the tokens allows."""
    _spool, sdir, _result = ingested["each-names"]
    trace = only_trace(sdir)
    assert "harness_command" not in trace.meta
    out = _info_of(sdir)
    assert "harness: vitest run src/each.probe.test.ts" in out, out
    # ...and `runs`' header falls back to the same words, not to nothing:
    # a header naming no program at all is worse than one naming a
    # reconstruction, because the reader cannot see that a fallback happened.
    r = run_cli(["runs"], cwd=sdir.parent, sensorium_dir=sdir)
    assert (": vitest run src/each.probe.test.ts\n"
            in r.stdout), r.stdout
