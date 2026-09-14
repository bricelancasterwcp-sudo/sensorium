"""Turn a `case.json` description into a real spool directory `cargo-
sensorium convert` can read: `invocation.json`, `<pid>.proc.json`,
`<pid>.<serial>.spool` (wire format v2 by default, v3 or v4 where a case or
a thread says `"version": 3` / `"version": 4`) and the unit manifests under
`<target>/sensorium/manifests/`.

Every byte this module writes is encoded from the wire block reproduced in
`rust/cargo-sensorium/src/convert/spool/mod.rs`'s doc comment and
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

# The wire version a case gets when it does not ask for one. v2, not v3:
# every case checked in before rung 3 describes a rung-2 recording, and
# writing a 3 into their headers would change what the converter reads out
# of their `err` RETURN payloads (v3 puts a type block there) -- a fixture
# would then be pinning a recording no runtime of its era produced.
DEFAULT_VERSION = 2

# The `how` byte of a RAISE/HANDLED record, which the header's otherwise idle
# `outcome` byte carries (design R2). 8 (`exit`) is deliberately absent: it is
# the converter's own synthesised origin and never appears on the wire, so a
# case cannot write one by name.
_HOW = {"try": 1, "sink_ok": 2, "sink_unwrap_or": 3, "sink_let_underscore": 4,
        "arm_propagate": 5, "arm_handled": 6, "arm_ambiguous": 7}
_RAISE_HOWS = frozenset({"try", "arm_propagate"})

# The `err` RETURN's type-block flag bits, and -- a DIFFERENT byte with a
# different layout -- the RAISE/HANDLED payload's.
_RET_TYPE_PRESENT = 1 << 0
_RET_TYPE_TRUNCATED = 1 << 1
_ERR_MSG_PRESENT = 1 << 0
_ERR_MSG_TRUNCATED = 1 << 1
_ERR_TYPE_TRUNCATED = 1 << 2
_ERR_TYPE_PRESENT = 1 << 3

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
    # Rule v1's two header siblings (`sensorium-rt 0.6.0` on): the name ->
    # digest table and the object saying what the rule did. Absent by default,
    # which is exactly what a header written before the rule existed looks
    # like -- and the case where the converter applies the rule itself rather
    # than carrying the recorder's word for it. `redacted-env` is the case
    # that carries them.
    "env_redaction": {},
    "redaction": None,
    "units": {},
    "refused": None,
    "rt_version": "sensorium-rt 0.1.0",
    # The Rust-only capability keys the RUNTIME declared (design R9), passed
    # into the trace's `capabilities` untouched. Empty by default because a
    # rung-2 header carried none, and `err_flow` absent is what makes an old
    # trace read as "not witnessed" rather than as a capability it never had.
    "capabilities": {},
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


def _err_return_payload(tag: int, truncated: bool, text: str,
                        err_type: str | None,
                        type_truncated: bool = False) -> bytes:
    """A v3 `err` RETURN: the two fixed bytes, then the error TYPE block, then
    the value's text.

    The block is `u8 type_flags (bit0 present, bit1 truncated) u16 type_len`
    and it rides an `err` RETURN and nothing else -- it is what lets the
    converter synthesise an origin RAISE for an `Err` born by being returned
    (design R1). `err_type: None` writes the block with its present bit clear
    and no bytes: the exit probe met a `Result` whose `E` the ladder could not
    name, which is a different fact from a v2 spool having no block at all.
    """
    type_b = err_type.encode() if err_type is not None else b""
    flags = ((_RET_TYPE_PRESENT if err_type is not None else 0)
             | (_RET_TYPE_TRUNCATED if type_truncated else 0))
    return (bytes([tag, 1 if truncated else 0, flags])
            + struct.pack("<H", len(type_b)) + type_b + text.encode())


def _errflow_payload(type_name: str | None, msg: str | None,
                     type_truncated: bool = False,
                     msg_truncated: bool = False) -> bytes:
    """A RAISE/HANDLED payload: `u8 flags u16 type_len type msg`.

    `None` is UNREAD, never empty: the flags byte is the only thing that
    separates a `Debug` that rendered nothing from a ladder rung that could
    not read the value at all, and the converter refuses a payload whose
    flags contradict its bytes -- so a case that says a field is absent must
    carry none of it.
    """
    flags = 0
    type_b = b""
    if type_name is not None:
        flags |= _ERR_TYPE_PRESENT
        type_b = type_name.encode()
    if type_truncated:
        flags |= _ERR_TYPE_TRUNCATED
    msg_b = b""
    if msg is not None:
        flags |= _ERR_MSG_PRESENT
        msg_b = msg.encode()
    if msg_truncated:
        flags |= _ERR_MSG_TRUNCATED
    return bytes([flags]) + struct.pack("<H", len(type_b)) + type_b + msg_b


def _how_byte(op: dict, kind_name: str) -> int:
    """The `how` of an err-flow op, refused by name when the op's record kind
    and its `how` disagree.

    The transformer writes the manifest row and the runtime writes this byte
    from one splice, so the two can never disagree in a real recording; a
    fixture that spelled `{"op": "raise", "how": "sink_ok"}` would be
    describing corruption, and the converter refuses it. Catching it here
    says which fixture line is wrong instead.
    """
    how = op["how"]
    if how not in _HOW:
        raise ValueError(f"gen.py: unknown err-flow how {how!r}")
    if (how in _RAISE_HOWS) != (kind_name == "raise"):
        raise ValueError(
            f"gen.py: how {how!r} belongs to a "
            f"{'raise' if how in _RAISE_HOWS else 'handled'} record, not a "
            f"{kind_name}")
    return _HOW[how]


def _panic_payload(loc: str, msg: str) -> bytes:
    loc_b = loc.encode()
    return struct.pack("<H", len(loc_b)) + loc_b + msg.encode()


# The LINE payload's delta tags. 0 (no value) is deliberately absent: it is
# legal in the grammar and no runtime writes it for a delta, so a case cannot
# spell one by name. 4 is wire v4's REDACTED BY NAME, whose text block holds a
# 16-hex digest instead of the value the delta captured -- a case that uses it
# must declare `"version": 4`, because a v2 or v3 spool carrying the tag is
# corruption and the converter refuses it as such.
_TAG_DEBUG = 1
_TAG_UNREAD = 2
_TAG_UNBOUND = 3
_TAG_REDACTED = 4


def _line_block(name: str, tag: int, truncated: bool,
                text: str | None) -> bytes:
    """`u16 name_len, name, u8 tag, u8 truncated, [u16 text_len, text]` --
    the text block present exactly for the two tags that carry one."""
    name_b = name.encode()
    out = (struct.pack("<H", len(name_b)) + name_b
           + bytes([tag, 1 if truncated else 0]))
    if text is not None:
        text_b = text.encode()
        out += struct.pack("<H", len(text_b)) + text_b
    return out


def _delta_block(delta: dict) -> bytes:
    """One delta block, from what the case says about the binding:

      {"name": n, "text": t}            the value as the probe rendered it
      {"name": n, "redacted": "<hex>"}  taken by the RECORDER, digest and all
      {"name": n, "unread": true}       no `Debug` impl to read it with

    `truncated` is forced to 0 on a redacted block, as the runtime forces it:
    a digest never says whether the value it stands for was cut.
    """
    name = delta["name"]
    if delta.get("unread"):
        return _line_block(name, _TAG_UNREAD, False, None)
    if "redacted" in delta:
        return _line_block(name, _TAG_REDACTED, False, delta["redacted"])
    return _line_block(name, _TAG_DEBUG, delta.get("truncated", False),
                       delta["text"])


def _line_payload(deltas: list[dict], unbound: list[str],
                  dropped: bool = False) -> bytes:
    """`u8 flags, u16 n`, then the deltas and then the unbound names -- the
    order the runtime writes them in, which is what a reader's `n` counts."""
    blocks = ([_delta_block(d) for d in deltas]
              + [_line_block(n, _TAG_UNBOUND, False, None) for n in unbound])
    return (bytes([1 if dropped else 0]) + struct.pack("<H", len(blocks))
            + b"".join(blocks))


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
    if kind == "ret_err_typed":
        # v3 only: on a v2 spool the converter reads the payload's third byte
        # as the first byte of the value's text, so a case using this op must
        # declare `"version": 3`.
        site = _site(op["unit"], op["site"])
        payload = _err_return_payload(1, op.get("truncated", False),
                                      op["text"], op.get("err_type"),
                                      op.get("type_truncated", False))
        return _record(seq, ts, site, 2, 2, payload)
    if kind == "ret_panic":
        site = _site(op["unit"], op["site"])
        return _record(seq, ts, site, 2, 3, bytes([0, 0]))
    if kind in ("raise", "handled"):
        site = _site(op["unit"], op["site"])
        payload = _errflow_payload(op.get("type"), op.get("msg"),
                                   op.get("type_truncated", False),
                                   op.get("msg_truncated", False))
        return _record(seq, ts, site, 4 if kind == "raise" else 5,
                       _how_byte(op, kind), payload)
    if kind == "line":
        site = _site(op["unit"], op["site"])
        payload = _line_payload(op.get("deltas", []), op.get("unbound", []),
                                op.get("dropped", False))
        return _record(seq, ts, site, 6, 0, payload)
    if kind == "panic":
        payload = _panic_payload(op["loc"], op["msg"])
        return _record(seq, ts, 0, 3, 0, payload)
    if kind == "thread_end":
        return _record(seq, ts, 0, 255, 0, b"")
    raise ValueError(f"gen.py: unknown record op {kind!r}")


def _encode_spool(serial: int, name: str, records: list[dict],
                  records_dropped: int = 0, truncated: int = 0,
                  version: int = DEFAULT_VERSION) -> bytes:
    name_b = name.encode()
    header = b"SNSR" + struct.pack("<BBHIQQ", version, 0, len(name_b), serial,
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
            # Beside `env_hash`, where the runtime writes them. `redaction`
            # is written as JSON `null` when a case declares none, which the
            # converter reads as the absent key it is (`#[serde(default)]`
            # over `Option<Value>`) -- a header from before the rule.
            "env_redaction": merged_proc["env_redaction"],
            "redaction": merged_proc["redaction"],
            "units": merged_proc["units"],
            "refused": merged_proc["refused"],
            "rt_version": merged_proc["rt_version"],
            "capabilities": merged_proc["capabilities"],
        })
        for thread in proc.get("threads", []):
            # Per THREAD, falling back to the case's: the wire version is a
            # property of one spool file, and a directory holding both is a
            # shape the converter reads (`SpoolFile.version`).
            version = thread.get("version",
                                 case.get("version", DEFAULT_VERSION))
            data = _encode_spool(thread["serial"], thread.get("name", ""),
                                 thread.get("records", []),
                                 thread.get("records_dropped", 0),
                                 thread.get("truncated", 0), version)
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
