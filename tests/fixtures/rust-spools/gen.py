"""Turn a `case.json` description into a real spool directory `cargo-
sensorium convert` can read: `invocation.json`, `<pid>.proc.json`,
`<pid>.<serial>.spool` (wire format v2) and the unit manifests under
`<target>/sensorium/manifests/`.

Every byte this module writes is encoded from the wire block reproduced in
`rust/cargo-sensorium/src/convert/spool.rs`'s doc comment and
`rust/HONESTY.md` §4 -- never by running the runtime or importing
`sensorium-rt`'s writer. This is the Python-side counterpart of
`rust/cargo-sensorium/tests/common/wire.rs`'s `SpoolBuilder`; the two are
independent encoders of the same spec, on purpose (`tests/test_vectors.py`'s
module docstring states the same principle for the trace-format vectors).

`materialize(case, root)` is the library entry point `test_rust_convert.py`
calls per case, into a fresh `tmp_path`: a case fixture cannot carry this
box's paths (`invocation.json`'s `workspace_root`/`target_dir` must be real
paths that exist), so `case.json` is checked in as data and the paths are
filled in at test time.

Run directly for hand use: `python gen.py <case dir> <output root>` prints
the spool directory it wrote.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

HEADER_FIXED = 28

# Default field values shared by every case, so a case.json only states what
# is meaningful for the behaviour it pins.
_INVOCATION_DEFAULTS = {
    "invocation": "20260101-000000-100000",
    "subcommand": "test",
    "cargo_args": ["test"],
    "tier": "call",
    "toolchain": "rustc 1.96.0",
    "rustc_path": "/usr/bin/rustc",
    "host": "x86_64-unknown-linux-gnu",
    "profile": "dev",
    "tool_hash": "0123456789abcdef",
    "driver_version": "cargo-sensorium 0.1.0",
    "start_ts": 1_700_000_000.0,
    "end_ts": 1_700_000_001.0,
    "cargo_exit": 0,
}

_PROC_DEFAULTS = {
    "ppid": 1,
    "cwd": ".",
    "start_ns": 1_000_000_000,
    "start_realtime_ns": 1_700_000_000_000_000_000,
    "env": {},
    "env_hash": "0" * 16,
    "units": {},
    "refused": None,
    "rt_version": "sensorium-rt 0.1.0",
}

_RUNNER_DEFAULTS = {
    "signal": None,
    "wall_start_ts": 1.0,
    "wall_end_ts": 2.0,
}

_MANIFEST_DEFAULTS = {
    "crate_name": "fixture",
    "crate_type": "lib",
    "files": {},
    "skipped": [],
    "spawns": [],
    "source_hashes": {},
    "fell_back": False,
    "fallback_reason": None,
    "unreached_files": [],
    # Present and empty, exactly as the wrapper writes it: a file the walk
    # reached and the transformer refused is keyed here with the message, and
    # the converter has no field for this key at all (it ignores it). A case
    # carrying one is therefore also a check that an unknown manifest key does
    # not make the manifest unreadable.
    "unreached_reasons": {},
    "appended_line": {},
    # `materialize` layers the REAL `workspace_root` in ahead of this dict (a
    # case fixture cannot know that path ahead of time), so every case's own
    # manifests are in scope of its own invocation by default. A case that
    # wants to pin the foreign-workspace/missing-field scoping rule
    # (`rust/cargo-sensorium/src/convert/mod.rs::manifest_in_scope`) sets
    # `workspace_root` in its own manifest dict to override that layer.
}


def _write_json(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


def _site(unit: int, index: int) -> int:
    """`unit_id<<24 | site index`, the wire's packed `site` word."""
    return ((unit & 0xFF) << 24) | (index & 0x00FF_FFFF)


def _record(seq: int, ts_ns: int, site: int, kind: int, outcome: int,
           payload: bytes) -> bytes:
    return struct.pack("<QQIBBH", seq, ts_ns, site, kind, outcome,
                       len(payload)) + payload


def _return_payload(tag: int, truncated: bool, text: str) -> bytes:
    return bytes([tag, 1 if truncated else 0]) + text.encode()


def _panic_payload(loc: str, msg: str) -> bytes:
    loc_b = loc.encode()
    return struct.pack("<H", len(loc_b)) + loc_b + msg.encode()


# One encoder per symbolic op a case's thread `records` list can name,
# mirroring `SpoolBuilder`'s typed helpers one for one.
def _encode_op(op: dict) -> bytes:
    kind = op["op"]
    seq, ts = op["seq"], op["ts"]
    if kind == "call":
        site = _site(op["unit"], op["site"])
        return _record(seq, ts, site, 1, 0, b"")
    if kind == "ret_ok_dbg":
        site = _site(op["unit"], op["site"])
        payload = _return_payload(1, op.get("truncated", False), op["text"])
        return _record(seq, ts, site, 2, 1, payload)
    if kind == "ret_err_dbg":
        site = _site(op["unit"], op["site"])
        payload = _return_payload(1, op.get("truncated", False), op["text"])
        return _record(seq, ts, site, 2, 2, payload)
    if kind == "ret_none":
        site = _site(op["unit"], op["site"])
        return _record(seq, ts, site, 2, 0, bytes([0, 0]))
    if kind == "ret_unread":
        site = _site(op["unit"], op["site"])
        payload = bytes([2, 0])
        return _record(seq, ts, site, 2, op["outcome"], payload)
    if kind == "ret_panic":
        site = _site(op["unit"], op["site"])
        return _record(seq, ts, site, 2, 3, bytes([0, 0]))
    if kind == "panic":
        payload = _panic_payload(op["loc"], op["msg"])
        return _record(seq, ts, 0, 3, 0, payload)
    if kind == "thread_end":
        return _record(seq, ts, 0, 255, 0, b"")
    raise ValueError(f"gen.py: unknown record op {kind!r}")


def _encode_spool(serial: int, name: str, records: list[dict],
                  records_dropped: int = 0, truncated: int = 0) -> bytes:
    name_b = name.encode()
    header = b"SNSR" + struct.pack("<BBHIQQ", 2, 0, len(name_b), serial,
                                   records_dropped, truncated)
    assert len(header) == HEADER_FIXED, len(header)
    body = b"".join(_encode_op(r) for r in records)
    return header + name_b + body


def materialize(case: dict, root: Path) -> Path:
    """Write `case` under `root`: `<root>/spool` (returned), `<root>/ws`
    (workspace_root) and `<root>/target` (target_dir, manifests included).
    """
    root = Path(root)
    spool_dir = root / "spool"
    workspace_root = root / "ws"
    target_dir = root / "target"
    manifests_dir = target_dir / "sensorium" / "manifests"
    spool_dir.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    # Always created, even with no manifests: `convert_dir` requires the
    # directory to exist the moment any process was recorded at all, whether
    # or not that process registered a unit.
    manifests_dir.mkdir(parents=True, exist_ok=True)

    inv = {**_INVOCATION_DEFAULTS, **case.get("invocation", {})}
    _write_json(spool_dir / "invocation.json", {
        **inv,
        "workspace_root": str(workspace_root),
        "target_dir": str(target_dir),
    })

    for metadata, m in case.get("manifests", {}).items():
        defaults = {**_MANIFEST_DEFAULTS, "workspace_root": str(workspace_root)}
        merged = {**defaults, **m, "unit": metadata}
        _write_json(manifests_dir / f"{metadata}.json", merged)

    for proc in case["processes"]:
        pid = proc["pid"]
        merged_proc = {**_PROC_DEFAULTS, **proc}
        exe = merged_proc.get("exe", f"/w/target/debug/deps/fixture-{pid}")
        _write_json(spool_dir / f"{pid}.proc.json", {
            "pid": pid,
            "ppid": merged_proc["ppid"],
            "exe": exe,
            "argv": merged_proc.get("argv", [exe]),
            "cwd": merged_proc["cwd"],
            "start_ns": merged_proc["start_ns"],
            "start_realtime_ns": merged_proc["start_realtime_ns"],
            "env": merged_proc["env"],
            "env_hash": merged_proc["env_hash"],
            "units": merged_proc["units"],
            "refused": merged_proc["refused"],
            "rt_version": merged_proc["rt_version"],
        })
        for thread in proc.get("threads", []):
            data = _encode_spool(thread["serial"], thread.get("name", ""),
                                 thread.get("records", []),
                                 thread.get("records_dropped", 0),
                                 thread.get("truncated", 0))
            (spool_dir / f"{pid}.{thread['serial']}.spool").write_bytes(data)
        runner = proc.get("runner")
        if runner is not None:
            merged_runner = {**_RUNNER_DEFAULTS, **runner}
            _write_json(spool_dir / f"{pid}.runner.json", {
                "pid": pid,
                "exit_status": merged_runner.get("exit_status"),
                "signal": merged_runner["signal"],
                "wall_start_ts": merged_runner["wall_start_ts"],
                "wall_end_ts": merged_runner["wall_end_ts"],
                "argv": merged_runner.get("argv", merged_proc.get("argv", [exe])),
            })

    return spool_dir


def _main() -> None:
    if len(sys.argv) != 3:
        print("usage: gen.py <case dir with case.json> <output root>",
              file=sys.stderr)
        raise SystemExit(2)
    case_dir, out_root = Path(sys.argv[1]), Path(sys.argv[2])
    case = json.loads((case_dir / "case.json").read_text())
    spool_dir = materialize(case, out_root)
    print(spool_dir)


if __name__ == "__main__":
    _main()
