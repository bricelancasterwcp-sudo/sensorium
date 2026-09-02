"""Tests for `rust/spike/convert.py` (THROWAWAY SPIKE CODE, Task 4).

Two tiers, cheapest first (the third -- end to end, the real driver and the
real `sensorium` CLI -- lives in `test_convert_e2e.py`; split purely to keep
both files under the project's 800-line cap):

1. Wire parser + k-way merge: synthetic byte buffers and synthetic
   `SpoolFile`/`Record` objects, no filesystem, no sqlite.
2. Frame reconstruction / meta: `convert_process` and `convert_dir` against
   a real (temp-file) `TraceWriter`, read back through the real
   `sensorium.store.reader.Trace` -- exercises the same write path
   production code uses, never a fake.

Run: `.venv/bin/python -m pytest rust/spike/tests/test_convert.py -q`, or
`rust/spike/tests/` for both files together (from the repo root;
`conftest.py` in this directory puts `rust/spike` on `sys.path` so
`import convert` resolves).
"""
import json
import struct
from pathlib import Path

import pytest

import convert
from sensorium.store import db
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter

# ---------------------------------------------------------------------------
# Shared byte-level helpers
# ---------------------------------------------------------------------------


def _site(unit_id: int, index: int) -> int:
    """Independently reimplements the wire format's bit packing (never
    calls into `convert`'s own constants) so a mutated shift/mask in
    `convert.py` shows up as a decode mismatch, not as agreement with
    itself."""
    return (unit_id << 24) | index


def build_spool_bytes(serial: int, name: str, records: list) -> bytes:
    """`records`: list of `(seq, ts_ns, site, kind, outcome)` tuples.
    Mirrors `sensorium-rt/src/spool.rs::Spool::open`/`record` byte for
    byte."""
    name_b = name.encode("utf-8")
    buf = bytearray()
    buf += b"SNSR"
    buf += bytes([1])                      # version
    buf += struct.pack("<I", serial)
    buf += struct.pack("<H", len(name_b))
    buf += name_b
    for seq, ts_ns, site, kind, outcome in records:
        buf += struct.pack("<QQIBBH", seq, ts_ns, site, kind, outcome, 0)
    return bytes(buf)


def make_manifest(unit, crate_name="c", crate_type="lib", fell_back=False,
                  sites=None, skipped=None) -> "convert.ManifestInfo":
    return convert.ManifestInfo(unit=unit, crate_name=crate_name,
                                crate_type=crate_type, fell_back=fell_back,
                                sites=sites or {}, skipped=skipped or [])


def rec(seq, site, kind, outcome=0, ts=None):
    return convert.Record(seq, ts if ts is not None else seq * 100, site,
                          kind, outcome)


CALL, RETURN, END = convert.KIND_CALL, convert.KIND_RETURN, convert.KIND_THREAD_END


class TestRecordSlots:
    """A binary with ~10^6 events instantiates that many `Record`s; an
    unslotted dataclass costs several hundred MB peak at that count. A
    regression guard, since `slots=True` leaves no other trace to assert on
    besides "there is no per-instance __dict__ any more"."""

    def test_record_instances_have_no_dict(self):
        r = rec(0, 0, CALL)
        assert not hasattr(r, "__dict__")

    def test_record_is_still_frozen(self):
        r = rec(0, 0, CALL)
        with pytest.raises(AttributeError):
            r.seq = 1


# ===========================================================================
# 1. Wire parser
# ===========================================================================

class TestParseSpoolBytes:
    def test_parses_header_and_records(self):
        data = build_spool_bytes(3, "tests::foo", [
            (0, 1000, _site(0, 1), CALL, 0),
            (1, 2000, _site(0, 1), RETURN, 0),
            (2, 3000, 0, END, 0),
        ])
        sp = convert.parse_spool_bytes(data)
        assert sp.serial == 3
        assert sp.name == "tests::foo"
        assert len(sp.records) == 3
        assert sp.records[0] == convert.Record(0, 1000, _site(0, 1), CALL, 0)
        assert sp.ended is True

    def test_empty_name_thread_parses_to_empty_string(self):
        data = build_spool_bytes(2, "", [(0, 1, 0, END, 0)])
        sp = convert.parse_spool_bytes(data)
        assert sp.name == ""

    def test_no_trailing_thread_end_is_not_ended(self):
        data = build_spool_bytes(2, "w", [(0, 1, _site(0, 0), CALL, 0)])
        sp = convert.parse_spool_bytes(data)
        assert sp.ended is False

    def test_header_only_spool_has_no_records_and_is_not_ended(self):
        data = build_spool_bytes(2, "w", [])
        sp = convert.parse_spool_bytes(data)
        assert sp.records == []
        assert sp.ended is False

    def test_rejects_bad_magic(self):
        data = b"XXXX" + build_spool_bytes(1, "", [])[4:]
        with pytest.raises(convert.ConverterError, match="magic"):
            convert.parse_spool_bytes(data)

    def test_rejects_unknown_version(self):
        data = bytearray(build_spool_bytes(1, "", []))
        data[4] = 2
        with pytest.raises(convert.ConverterError, match="version"):
            convert.parse_spool_bytes(bytes(data))

    def test_rejects_nonzero_reserved_field(self):
        data = bytearray(build_spool_bytes(1, "", [(0, 1, 0, END, 0)]))
        # The reserved u16 is the last two bytes of the one record.
        data[-2:] = struct.pack("<H", 7)
        with pytest.raises(convert.ConverterError, match="reserved"):
            convert.parse_spool_bytes(bytes(data))

    def test_rejects_trailing_partial_record(self):
        data = build_spool_bytes(1, "", [(0, 1, 0, END, 0)]) + b"\x00" * 5
        with pytest.raises(convert.ConverterError, match="trailing"):
            convert.parse_spool_bytes(data)

    def test_rejects_truncated_header(self):
        with pytest.raises(convert.ConverterError, match="short"):
            convert.parse_spool_bytes(b"SNSR")

    def test_parse_spool_reads_a_real_file(self, tmp_path):
        p = tmp_path / "123.4.spool"
        p.write_bytes(build_spool_bytes(4, "t", [(0, 1, 0, END, 0)]))
        sp = convert.parse_spool(p)
        assert sp.serial == 4
        assert sp.ended is True


# ===========================================================================
# 2. The k-way merge
# ===========================================================================

class TestMergeRecords:
    def test_orders_by_seq_across_threads(self):
        s2 = convert.SpoolFile(None, 2, "a", [rec(0, 0, CALL), rec(2, 0, RETURN)],
                               False)
        s3 = convert.SpoolFile(None, 3, "b", [rec(1, 0, CALL), rec(3, 0, RETURN)],
                               False)
        merged = convert.merge_records([s2, s3])
        assert [seq for _serial, seq in
               ((serial, r.seq) for serial, r in merged)] == [0, 1, 2, 3]
        assert [serial for serial, _r in merged] == [2, 3, 2, 3]

    def test_empty_spool_list_merges_to_nothing(self):
        assert convert.merge_records([]) == []

    def test_a_spool_with_no_records_contributes_nothing(self):
        s = convert.SpoolFile(None, 2, "a", [], False)
        assert convert.merge_records([s]) == []

    def test_duplicate_seq_across_threads_is_a_converter_error(self):
        """seq is one AtomicU64 shared by the whole process: two spools
        naming the same seq is the invariant broken, not a coincidence."""
        s2 = convert.SpoolFile(None, 2, "a", [rec(5, 0, CALL)], False)
        s3 = convert.SpoolFile(None, 3, "b", [rec(5, 0, CALL)], False)
        with pytest.raises(convert.ConverterError, match="seq 5"):
            convert.merge_records([s2, s3])

    def test_decreasing_seq_within_one_spool_is_a_converter_error(self):
        s = convert.SpoolFile(None, 2, "a", [rec(5, 0, CALL), rec(3, 0, RETURN)],
                              False)
        with pytest.raises(convert.ConverterError, match="strictly greater"):
            convert.merge_records([s])


# ===========================================================================
# 3. Frame reconstruction (`convert_process`), against a real TraceWriter
# ===========================================================================


def _run_process(tmp_path, proc, spools, manifests, workspace_root=Path("/ws"),
                 name="t"):
    path = tmp_path / f"{name}.db"
    w = TraceWriter(path)
    try:
        summary = convert.convert_process(w, proc, spools, manifests,
                                          workspace_root)
    finally:
        w.close()
    return summary, Trace.open(path)


class TestConvertProcessFrames:
    def test_call_return_on_the_main_thread_builds_a_root_frame(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a/b.rs", "foo", 10)})}
        spools = [convert.SpoolFile(None, 1, "", [rec(0, _site(0, 0), CALL),
                                                  rec(1, _site(0, 0), RETURN)],
                                    False)]
        proc = {"units": {"0": "m"}}
        summary, tr = _run_process(tmp_path, proc, spools, manifests)

        frames = tr.frames()
        assert len(frames) == 1
        f = frames[0]
        assert f.parent_id is None
        assert f.depth == 0
        assert f.closed_by == "return"
        assert f.kind == "function"
        assert f.thread_id == 1
        code = tr.code(f.code_id)
        assert code.file == str(Path("/ws/a/b.rs"))
        assert code.qualname == "foo"
        assert code.firstlineno == 10
        assert tr.tasks() == []
        fps = tr.fingerprints()
        assert fps[1][1] == 2                    # 2 causal events, main
        assert summary["events"] == 2

    def test_call_payload_declares_locals_unread_not_empty_args(self, tmp_path):
        """`locals: false`: `args: {}` alone would read as "this fn takes no
        arguments" (fmt.py's CALL rendering), the opposite of the truth for
        e.g. `work(n: u32)`. TRACE-FORMAT.md's `unread: ["locals"]` says
        "unread", not "none" -- see also the e2e
        `test_grep_shows_the_unread_locals_marker_and_never_bare_args`."""
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 1, "", [rec(0, _site(0, 0), CALL),
                                                  rec(1, _site(0, 0), RETURN)],
                                    False)]
        proc = {"units": {"0": "m"}}
        _summary, tr = _run_process(tmp_path, proc, spools, manifests)
        call = tr.events(kind="CALL")[0]
        assert call.payload == {"args": {}, "unread": ["locals"]}
        # RETURN is unaffected by this fix -- return_value: false already
        # omits "value" entirely (§5: a key a recorder cannot fill is
        # omitted, never a placeholder), so there's nothing there to mark.
        ret = tr.events(kind="RETURN")[0]
        assert ret.payload == {}

    def test_nested_calls_build_parent_child_frames_with_depth(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={
            0: ("a.rs", "outer", 1), 1: ("a.rs", "inner", 5)})}
        spools = [convert.SpoolFile(None, 1, "", [
            rec(0, _site(0, 0), CALL),
            rec(1, _site(0, 1), CALL),
            rec(2, _site(0, 1), RETURN),
            rec(3, _site(0, 0), RETURN),
        ], False)]
        proc = {"units": {"0": "m"}}
        _summary, tr = _run_process(tmp_path, proc, spools, manifests)

        frames = sorted(tr.frames(), key=lambda f: f.id)
        outer, inner = frames
        assert outer.parent_id is None and outer.depth == 0
        assert inner.parent_id == outer.id and inner.depth == 1
        assert tr.code(outer.code_id).qualname == "outer"
        assert tr.code(inner.code_id).qualname == "inner"

    def test_panic_outcome_closes_with_unwind_and_the_panic_payload(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "boom", 1)})}
        spools = [convert.SpoolFile(None, 1, "", [
            rec(7, _site(0, 0), CALL),
            rec(9, _site(0, 0), RETURN, outcome=convert.OUTCOME_PANIC),
        ], False)]
        proc = {"units": {"0": "m"}}
        _summary, tr = _run_process(tmp_path, proc, spools, manifests)

        f = tr.frames()[0]
        assert f.closed_by == "unwind"
        assert f.unwind_exc == {"type": "panic", "msg": "", "serial": 9,
                                "oid": 9}

    def test_return_with_no_open_frame_is_a_converter_error(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 1, "", [rec(0, _site(0, 0), RETURN)],
                                    False)]
        proc = {"units": {"0": "m"}}
        with pytest.raises(convert.ConverterError, match="no open frame"):
            _run_process(tmp_path, proc, spools, manifests)

    def test_a_frame_still_open_at_end_of_spool_stays_open(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 2, "leaky", [rec(0, _site(0, 0), CALL)],
                                    False)]
        proc = {"units": {"0": "m"}}
        summary, tr = _run_process(tmp_path, proc, spools, manifests)
        f = tr.frames()[0]
        assert f.closed_by is None
        assert f.return_event_id is None
        assert summary["live_threads"] == ["leaky"]
        assert summary["spools_without_end"] == 1


class TestConvertProcessTasks:
    def test_a_named_non_main_thread_becomes_a_task_and_a_fingerprint(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 2, "worker", [
            rec(0, _site(0, 0), CALL), rec(1, _site(0, 0), RETURN)], True)]
        proc = {"units": {"0": "m"}}
        summary, tr = _run_process(tmp_path, proc, spools, manifests)

        tasks = tr.tasks()
        assert len(tasks) == 1
        assert tasks[0].id == 2
        assert tasks[0].name == "worker"
        assert tasks[0].thread_id == 2
        tfps = tr.task_fingerprints()
        assert tfps[2][0] == "worker"
        assert tfps[2][2] == 2                    # n_events
        # Events on a task thread carry task_id and stay OUT of the main
        # thread's zero-count fingerprint row.
        events = tr.events(kind="CALL")
        assert events[0].task_id == 2
        assert tr.fingerprints()[1] == (convert.Fingerprint().hexdigest(), 0)

    def test_an_unnamed_thread_gets_a_null_task_name(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 2, "", [
            rec(0, _site(0, 0), CALL), rec(1, _site(0, 0), RETURN)], True)]
        proc = {"units": {"0": "m"}}
        _summary, tr = _run_process(tmp_path, proc, spools, manifests)
        assert tr.tasks()[0].name is None

    def test_main_thread_with_no_spool_still_gets_a_zero_count_fingerprint(
            self, tmp_path):
        manifests = {}
        proc = {"units": {}}
        summary, tr = _run_process(tmp_path, proc, [], manifests)
        assert tr.fingerprints()[1] == (convert.Fingerprint().hexdigest(), 0)
        assert tr.tasks() == []
        assert summary["events"] == 0
        assert summary["threads"] == 1
        assert summary["threads_started"] == 0

    def test_a_thread_with_a_clean_thread_end_is_not_in_live_threads(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 2, "worker", [
            rec(0, _site(0, 0), CALL), rec(1, _site(0, 0), RETURN),
            rec(2, 0, END)], True)]
        proc = {"units": {"0": "m"}}
        summary, _tr = _run_process(tmp_path, proc, spools, manifests)
        assert summary["live_threads"] == []
        assert summary["spools_without_end"] == 0
        assert summary["threads_started"] == 1


class TestConvertProcessErrors:
    def test_call_names_an_unregistered_unit_is_a_converter_error(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 1, "", [rec(0, _site(9, 0), CALL)],
                                    False)]
        proc = {"units": {"0": "m"}}          # unit 9 was never registered
        with pytest.raises(convert.ConverterError, match="never registered"):
            _run_process(tmp_path, proc, spools, manifests)

    def test_call_names_a_unit_with_no_manifest_is_a_converter_error(self, tmp_path):
        spools = [convert.SpoolFile(None, 1, "", [rec(0, _site(0, 0), CALL)],
                                    False)]
        proc = {"units": {"0": "ghost"}}      # no manifest for "ghost"
        with pytest.raises(convert.ConverterError, match="no manifest"):
            _run_process(tmp_path, proc, spools, {})

    def test_call_names_an_unknown_site_is_a_converter_error(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 1, "", [rec(0, _site(0, 99), CALL)],
                                    False)]
        proc = {"units": {"0": "m"}}
        with pytest.raises(convert.ConverterError, match="no site 99"):
            _run_process(tmp_path, proc, spools, manifests)

    def test_unknown_record_kind_is_a_converter_error(self, tmp_path):
        proc = {"units": {}}
        spools = [convert.SpoolFile(None, 1, "", [rec(0, 0, 42)], False)]
        with pytest.raises(convert.ConverterError, match="unknown record kind"):
            _run_process(tmp_path, proc, spools, {})

    def test_unknown_outcome_is_a_converter_error(self, tmp_path):
        manifests = {"m": make_manifest("m", sites={0: ("a.rs", "f", 1)})}
        spools = [convert.SpoolFile(None, 1, "", [
            rec(0, _site(0, 0), CALL),
            rec(1, _site(0, 0), RETURN, outcome=1)], False)]
        proc = {"units": {"0": "m"}}
        with pytest.raises(convert.ConverterError, match="unknown outcome"):
            _run_process(tmp_path, proc, spools, manifests)


# ===========================================================================
# 2b. Manifest loading (disk) and global meta aggregation
# ===========================================================================


def _write_manifest_file(target: Path, metadata: str, crate_name: str,
                         crate_type: str, files: dict, fell_back=False,
                         skipped=None) -> None:
    mdir = target / "sensorium" / "manifests"
    mdir.mkdir(parents=True, exist_ok=True)
    doc = {"unit": metadata, "crate_name": crate_name, "crate_type": crate_type,
          "files": files, "skipped": skipped or [], "fell_back": fell_back,
          "unreached_files": [],
          "appended_line": {f: False for f in files}}
    (mdir / f"{metadata}.json").write_text(json.dumps(doc), encoding="utf-8")


class TestLoadManifests:
    def test_loads_sites_keyed_by_index(self, tmp_path):
        target = tmp_path / "target"
        _write_manifest_file(target, "metaA", "app", "bin", {
            "src/main.rs": [{"site": 0, "qualname": "main", "firstlineno": 1},
                            {"site": 1, "qualname": "helper", "firstlineno": 5}]})
        manifests = convert.load_manifests(target)
        m = manifests["metaA"]
        assert m.crate_name == "app"
        assert m.sites[0] == ("src/main.rs", "main", 1)
        assert m.sites[1] == ("src/main.rs", "helper", 5)

    def test_a_mirror_path_in_the_manifest_is_a_converter_error(self, tmp_path):
        target = tmp_path / "target"
        _write_manifest_file(target, "metaA", "app", "lib", {
            "target/sensorium/mirror/metaA/src/lib.rs":
                [{"site": 0, "qualname": "f", "firstlineno": 1}]})
        with pytest.raises(convert.ConverterError, match="MIRROR path"):
            convert.load_manifests(target)

    def test_uninstrumented_units_are_the_fell_back_ones(self, tmp_path):
        target = tmp_path / "target"
        _write_manifest_file(target, "metaA", "app", "bin", {})
        _write_manifest_file(target, "metaB", "lost", "lib", {}, fell_back=True)
        manifests = convert.load_manifests(target)
        assert convert.uninstrumented_units(manifests) == ["metaB"]

    def test_all_skipped_aggregates_every_manifest_sorted_by_unit(self, tmp_path):
        target = tmp_path / "target"
        _write_manifest_file(target, "metaB", "b", "lib", {},
                             skipped=[{"file": "b.rs", "qualname": "y",
                                      "line": 2, "reason": "const"}])
        _write_manifest_file(target, "metaA", "a", "lib", {},
                             skipped=[{"file": "a.rs", "qualname": "x",
                                      "line": 1, "reason": "macro"}])
        manifests = convert.load_manifests(target)
        skipped = convert.all_skipped(manifests)
        # sorted by unit ("metaA" before "metaB"), so a's entry comes first.
        assert [s["qualname"] for s in skipped] == ["x", "y"]

    def test_a_missing_manifests_directory_is_a_converter_error(self, tmp_path):
        """Almost always means `--target` does not match the
        `CARGO_TARGET_DIR` the driver actually built into -- raised here,
        once, by name, instead of surfacing much later as a confusing
        per-CALL "unit ... has no manifest" error."""
        target = tmp_path / "target"          # target/sensorium/manifests/
        target.mkdir()                        # never created
        with pytest.raises(convert.ConverterError,
                           match="no manifests found"):
            convert.load_manifests(target)

    def test_an_existing_but_empty_manifests_directory_is_not_an_error(
            self, tmp_path):
        """A different, legitimate fact from a MISSING directory: a build
        that instrumented nothing. Must not be conflated with the case
        above."""
        target = tmp_path / "target"
        (target / "sensorium" / "manifests").mkdir(parents=True)
        assert convert.load_manifests(target) == {}


# ===========================================================================
# 2c. `convert_dir`: the full meta pass + `db.missing_required`
# ===========================================================================


@pytest.fixture()
def sensorium_home(tmp_path, monkeypatch):
    home = tmp_path / "sensorium-home"
    monkeypatch.setenv("SENSORIUM_DIR", str(home))
    return home


def _write_spool_file(spool_dir: Path, pid: int, serial: int, name: str,
                      records: list) -> None:
    tuples = [(r.seq, r.ts_ns, r.site, r.kind, r.outcome) for r in records]
    (spool_dir / f"{pid}.{serial}.spool").write_bytes(
        build_spool_bytes(serial, name, tuples))


class TestConvertDir:
    def _build_scene(self, tmp_path):
        """One process, one instrumented unit, one worker thread with a
        clean end, one thread that leaked. Returns (spool_dir, target)."""
        ws = tmp_path / "ws"
        target = ws / "target"
        _write_manifest_file(target, "metaA", "app", "test", {
            "src/lib.rs": [{"site": 0, "qualname": "tests::t", "firstlineno": 3},
                          {"site": 1, "qualname": "work", "firstlineno": 8}]})
        spool_dir = tmp_path / "spool" / "20260101-000000-abcdef"
        spool_dir.mkdir(parents=True)
        pid = 4242
        proc = {"pid": pid, "ppid": 1, "exe": "/tmp/build/app-abc123",
               "argv": ["/tmp/build/app-abc123"], "cwd": str(ws),
               "start_ns": 1_000_000, "units": {"0": "metaA"}}
        (spool_dir / f"{pid}.proc.json").write_text(json.dumps(proc),
                                                     encoding="utf-8")
        _write_spool_file(spool_dir, pid, 2, "tests::t", [
            rec(0, _site(0, 0), CALL, ts=1_000_100),
            rec(1, _site(0, 1), CALL, ts=1_000_200),
            rec(2, _site(0, 1), RETURN, ts=1_000_300),
            rec(3, _site(0, 0), RETURN, ts=1_000_400),
            rec(4, 0, END, ts=1_000_500),
        ])
        _write_spool_file(spool_dir, pid, 3, "leaked", [
            rec(5, _site(0, 1), CALL, ts=1_000_600),
        ])
        return spool_dir, target, pid

    def test_produces_a_trace_that_opens_without_refusal(self, tmp_path,
                                                          sensorium_home):
        spool_dir, target, _pid = self._build_scene(tmp_path)
        lines = convert.convert_dir(spool_dir, target, cargo_exit=0,
                                    cargo_args=["test"])
        assert len(lines) == 1
        run_id = lines[0].split()[1]
        trace_path = sensorium_home / "traces" / f"{run_id}.db"
        conn = db.open_trace(trace_path)          # raises TraceFormatError on refusal
        assert db.missing_required(conn) == []
        conn.close()

    def test_report_line_matches_the_documented_shape(self, tmp_path,
                                                       sensorium_home):
        spool_dir, target, pid = self._build_scene(tmp_path)
        lines = convert.convert_dir(spool_dir, target, cargo_exit=0,
                                    cargo_args=["test"])
        assert len(lines) == 1
        parts = lines[0].split()
        assert parts[0] == "run:"
        assert parts[2] == "pid:" and parts[3] == str(pid)
        assert parts[4] == "exe:" and parts[5] == "app-abc123"
        assert parts[6] == "events:" and parts[7] == "5"
        assert parts[8] == "threads:" and parts[9] == "3"
        assert parts[10] == "spools_without_end:" and parts[11] == "1"

    def test_meta_matches_the_brief_exactly(self, tmp_path, sensorium_home):
        spool_dir, target, pid = self._build_scene(tmp_path)
        lines = convert.convert_dir(spool_dir, target, cargo_exit=17,
                                    cargo_args=["test", "-p", "app"])
        run_id = lines[0].split()[1]
        tr = Trace.open(sensorium_home / "traces" / f"{run_id}.db")
        m = tr.meta
        assert m["run_id"] == run_id
        assert m["argv"] == ["/tmp/build/app-abc123"]
        assert m["cwd"] == str(target.parent)
        assert m["exit_status"] == 17
        assert m["main_thread_ident"] == 1
        assert m["fingerprint_basis"] == "per-task"
        assert m["truncated_count"] == 0
        assert m["records_dropped"] == {}
        assert m["source_hashes"] == {}
        assert m["recorder"] == "sensorium-rt 0.0.0-spike"
        assert m["lang"] == "rust"
        assert m["capabilities"] == convert.CAPABILITIES
        assert m["threads_started"] == 2
        assert m["live_threads"] == ["leaked"]
        assert m["invocation"] == spool_dir.name
        assert m["pid"] == pid
        assert m["ppid"] == 1
        assert m["exe"] == "/tmp/build/app-abc123"
        assert m["cargo_args"] == ["test", "-p", "app"]
        assert m["profile"] == "debug"
        assert m["instrumented_units"] == ["metaA"]
        assert m["incomplete"] is False
        assert isinstance(m["toolchain"], str) and m["toolchain"]
        assert isinstance(m["env_hash"], str) and m["env_hash"]
        assert set(db.REQUIRED_META) <= set(m)

    def test_release_flag_in_argv_sets_the_release_profile(self, tmp_path,
                                                            sensorium_home):
        spool_dir, target, _pid = self._build_scene(tmp_path)
        lines = convert.convert_dir(spool_dir, target, cargo_exit=0,
                                    cargo_args=["test", "--release"])
        run_id = lines[0].split()[1]
        tr = Trace.open(sensorium_home / "traces" / f"{run_id}.db")
        assert tr.meta["profile"] == "release"

    def test_uninstrumented_and_skipped_are_global_not_per_process(
            self, tmp_path, sensorium_home):
        spool_dir, target, _pid = self._build_scene(tmp_path)
        # A second, fell-back unit this process never touched.
        _write_manifest_file(target, "metaZ", "lost", "lib", {},
                             fell_back=True,
                             skipped=[{"file": "z.rs", "qualname": "weird",
                                      "line": 9, "reason": "extern"}])
        lines = convert.convert_dir(spool_dir, target, cargo_exit=0,
                                    cargo_args=["test"])
        run_id = lines[0].split()[1]
        tr = Trace.open(sensorium_home / "traces" / f"{run_id}.db")
        m = tr.meta
        assert m["uninstrumented"] == ["metaZ"]
        assert [s["qualname"] for s in m["skipped"]] == ["weird"]
        # This process's own units map never named metaZ.
        assert m["instrumented_units"] == ["metaA"]

    def test_code_objects_file_is_parent_of_target_join_manifest_path(
            self, tmp_path, sensorium_home):
        spool_dir, target, _pid = self._build_scene(tmp_path)
        lines = convert.convert_dir(spool_dir, target, cargo_exit=0,
                                    cargo_args=["test"])
        run_id = lines[0].split()[1]
        tr = Trace.open(sensorium_home / "traces" / f"{run_id}.db")
        files = {c.file for c in tr.codes()}
        assert files == {str(target.parent / "src" / "lib.rs")}

    def test_a_process_with_no_spool_files_at_all_converts_to_an_empty_trace(
            self, tmp_path, sensorium_home):
        ws = tmp_path / "ws"
        target = ws / "target"
        (target / "sensorium" / "manifests").mkdir(parents=True)
        spool_dir = tmp_path / "spool" / "run1"
        spool_dir.mkdir(parents=True)
        proc = {"pid": 1, "ppid": 0, "exe": "/bin/true", "argv": ["/bin/true"],
               "cwd": str(ws), "start_ns": 0, "units": {}}
        (spool_dir / "1.proc.json").write_text(json.dumps(proc))
        lines = convert.convert_dir(spool_dir, target, cargo_exit=0)
        assert len(lines) == 1
        assert "events: 0" in lines[0]
        assert "spools_without_end: 0" in lines[0]

    def test_a_converter_error_leaves_no_partial_trace_behind(self, tmp_path,
                                                              sensorium_home):
        ws = tmp_path / "ws"
        target = ws / "target"
        (target / "sensorium" / "manifests").mkdir(parents=True)
        spool_dir = tmp_path / "spool" / "run1"
        spool_dir.mkdir(parents=True)
        pid = 99
        proc = {"pid": pid, "ppid": 0, "exe": "/bin/x", "argv": ["/bin/x"],
               "cwd": str(ws), "start_ns": 0, "units": {}}
        (spool_dir / f"{pid}.proc.json").write_text(json.dumps(proc))
        # A RETURN with no matching CALL: convert_process must raise.
        _write_spool_file(spool_dir, pid, 2, "bad", [rec(0, 0, RETURN)])
        with pytest.raises(convert.ConverterError):
            convert.convert_dir(spool_dir, target, cargo_exit=0)
        assert list((sensorium_home / "traces").glob("*.db")) == []

    def test_a_spool_file_with_no_matching_proc_json_is_a_converter_error(
            self, tmp_path, sensorium_home):
        """`*.proc.json` is written before any spool file for that pid can
        exist, so an orphan spool means the header was lost or never
        written -- worth raising loudly by name, not silently dropping,
        with ~70 processes converted per bloomery invocation."""
        spool_dir, target, _pid = self._build_scene(tmp_path)
        # A spool file for a pid that never got a proc.json at all.
        _write_spool_file(spool_dir, 9999, 2, "ghost", [rec(0, 0, END)])
        with pytest.raises(convert.ConverterError,
                           match=r"9999\.2\.spool"):
            convert.convert_dir(spool_dir, target, cargo_exit=0,
                                cargo_args=["test"])
        # No trace was written for the (otherwise valid) known process
        # either -- the orphan check runs before the loop, so this refuses
        # the whole invocation rather than convert some and drop one.
        assert list((sensorium_home / "traces").glob("*.db")) == []


class TestOrphanSpools:
    def test_a_spool_whose_pid_has_a_proc_json_is_not_an_orphan(self, tmp_path):
        spool_dir = tmp_path
        (spool_dir / "1.proc.json").write_text("{}")
        (spool_dir / "1.2.spool").write_bytes(b"")
        proc_paths = sorted(spool_dir.glob("*.proc.json"))
        assert convert.orphan_spools(spool_dir, proc_paths) == []

    def test_a_spool_with_no_matching_proc_json_is_named(self, tmp_path):
        spool_dir = tmp_path
        (spool_dir / "1.proc.json").write_text("{}")
        (spool_dir / "1.2.spool").write_bytes(b"")
        (spool_dir / "2.3.spool").write_bytes(b"")     # pid 2 has no header
        proc_paths = sorted(spool_dir.glob("*.proc.json"))
        orphans = convert.orphan_spools(spool_dir, proc_paths)
        assert [p.name for p in orphans] == ["2.3.spool"]

    def test_no_spool_files_at_all_has_no_orphans(self, tmp_path):
        (tmp_path / "1.proc.json").write_text("{}")
        proc_paths = sorted(tmp_path.glob("*.proc.json"))
        assert convert.orphan_spools(tmp_path, proc_paths) == []


class TestEnvAndCli:
    def test_env_hash_is_stable_for_the_same_environment(self):
        env = {"A": "1", "B": "2"}
        assert convert.build_env_hash(env) == convert.build_env_hash(dict(env))

    def test_env_hash_changes_with_the_environment(self):
        assert (convert.build_env_hash({"A": "1"})
               != convert.build_env_hash({"A": "2"}))

    def test_cli_argv_flag_swallows_dashed_cargo_args(self):
        args = convert.parse_args(["/some/spool", "--target", "/some/target",
                                   "--cargo-exit", "3",
                                   "--argv", "test", "-p", "app", "--lib"])
        assert args.cargo_exit == 3
        assert args.argv == ["test", "-p", "app", "--lib"]

    def test_cli_argv_defaults_to_empty(self):
        args = convert.parse_args(["/some/spool", "--target", "/some/target"])
        assert args.argv == []
        assert args.cargo_exit == 0


