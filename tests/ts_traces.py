"""The TypeScript traces the `exceptions` rule tests are written against.

`tests/programs.py` holds the Python programs the Python rules are tested
on and `tests/rust_traces.py` the Rust recordings the Rust rules are; this
is the same idea for the third recorder. Each builder states one recording
as DATA -- the vector vocabulary of `tests/vectors.py` -- so a unit test and
a conformance vector can never describe two different trace shapes, and a
rule test never depends on Node, vitest or a transform running.

The meta is `docs/trace-format/vectors/v25-exc-kind-throw-rejection.json`'s,
moved to `sensorium-ts` 0.3.0 with `capabilities.err_flow: true` and
`object_identity: true`: 0.2.0 was the first recorder whose BOOT declares
the throw-flow records and 0.3.0 the first whose captures carry an identity,
and every rule test here is about a trace that carries them. A test that
wants the REFUSAL passes `recorder=` and `capabilities=` back down to a
0.1.x shape.
"""
from tests.vectors import build
from pathlib import Path

FILE = "/w/app/src/config.ts"
THREAD = 1               # the converter writes one thread and only one

#: A thrown primitive's `exc.type` is `typeof`'s word, and `null`'s is
#: `object` with no message at all -- the two shapes `Raise.primitive` is
#: about, stated here so a test and the rule module read one list.
PRIMITIVE_TYPES = ("string", "number", "boolean", "undefined", "symbol",
                   "bigint")

#: A 0.3.0 recording with no focus: `object_identity` is declared at every
#: tier this recorder records at, because a capture carries its object's
#: serial whether or not any statement was instrumented; `line` and `locals`
#: stay false, since a run without a focus has no LINE rows to read.
TS_CAPABILITIES = {
    "line": False, "locals": False, "return_value": True, "tasks": True,
    "threads": False, "children": False, "stdin": False, "output": False,
    "object_identity": True, "refocus": False, "err_flow": True,
}

#: What a 0.1.x recording declared: the throw-flow rows were written and no
#: rule read them, so the capability was false and `exceptions` refuses
#: through it. `object_identity` goes back down with it -- no recorder
#: before 0.3.0 put a serial on a capture, and a fixture that said otherwise
#: would be describing a recording that never existed.
TS_CAPABILITIES_0_1 = {**TS_CAPABILITIES, "err_flow": False,
                       "object_identity": False}

TS_META = {
    "trace_format": 4, "run_id": "$RUN",
    "argv": ["/usr/bin/node",
             "/w/app/node_modules/vitest/dist/workers/forks.js"],
    "cwd": "/w/app", "env_hash": "0" * 16, "start_ts": 0.0, "end_ts": 1.0,
    "exit_status": None, "exit_status_basis": "unwitnessed",
    "main_thread_ident": 1, "fingerprint_basis": "per-task",
    "truncated_count": 0, "source_hashes": {},
    "recorder": "sensorium-ts 0.3.0", "lang": "typescript",
    "capabilities": TS_CAPABILITIES,
    "caps": {"dbg": 200, "depth": 2, "sample": 8, "str": 100},
    "invocation": "20260101-000000-111111",
    "harness": "vitest",
    "harness_command": ["npx", "vitest", "run", "src/config"],
    "harness_args": ["run", "src/config"],
    "harness_exit": {"status": 1, "signal": None, "basis": "waited"},
    "driver_version": "0.2.0", "node": "v24.16.0", "vitest": "4.1.9",
    "environment": "node", "wire": 1, "pid": 4242, "ppid": 4241,
    "thread_id_os": 0, "is_main_thread": True,
    "test_file": "src/config.test.ts",
    "exit_self_reported": {"code": 1, "signal": None},
    "tests_seen": 1, "task_name_basis": "vitest", "task_name_conflicts": 0,
    "files_transformed": 3, "transform_excluded": {},
    "unhandled_rejections": [], "throw_flow_outside_frames": 0,
    "incomplete": False,
}


def ts_exc(type_, msg, serial, kind="throw", unread=None):
    """One `exc` object as `sensorium-ts` writes it (TYPESCRIPT-KEYS.md).

    `kind` is on EVERY one -- a kindless `exc` is read as Python's -- and
    `msg=None` writes the key as null, which is what `throw null` records
    (`type: "object"`, no message to read).
    """
    exc = {"kind": kind, "type": type_, "msg": msg, "serial": serial}
    if unread is not None:
        exc["unread"] = unread
    return exc


def call(ts, code, line, task=None, caller="untraced", args=None):
    """A frame-opening CALL. `caller: "untraced"` is on a frame entered on
    an empty stack -- the truthful answer to "who called this?" when the
    answer is Node's own machinery (`ts/build.py`), and the mark this
    module's `task_root` reads.

    `args` is a FOCUSED activation's arguments, and a CALL that carries
    them carries no `unread`: the names WERE read, so nothing about this
    row is unread (design 2026-09-11 section 3.3). Absent, the row is the
    call tier's -- empty args and `unread: ["locals"]`, which is what every
    unfocused CALL this recorder writes.
    """
    payload = {"args": args if args is not None else {}}
    if args is None:
        payload["unread"] = ["locals"]
    if caller is not None:
        payload["caller"] = caller
    return {"ts": ts, "thread": THREAD, "kind": "CALL", "code": code,
            "line": line, "payload": payload, "task": task}


def line_ev(ts, frame, code, line, deltas, unbound=None, task=None):
    """One statement's row: the names it WROTE, and the names that went out
    of scope when the block holding them ended.

    `unbound` is written only where a block ended, and the key is absent
    otherwise -- an empty list would say a step ended a scope and unbound
    nothing, which is a different record. A row may carry EMPTY deltas and
    a non-empty `unbound` (a block whose last statement wrote nothing) and
    is a site like any other.
    """
    payload = {"deltas": deltas}
    if unbound is not None:
        payload["unbound"] = unbound
    return {"ts": ts, "thread": THREAD, "kind": "LINE", "frame": frame,
            "code": code, "line": line, "payload": payload, "task": task}


def ret(ts, frame, code, value="undefined", task=None):
    return {"ts": ts, "thread": THREAD, "kind": "RETURN", "frame": frame,
            "code": code, "line": None,
            "payload": {"value": {"k": "dbg", "v": value}, "outcome": "ok"},
            "task": task}


def raise_ev(ts, frame, code, line, exc, task=None, how="throw"):
    """The RAISE a `throw` statement writes when it fires."""
    return {"ts": ts, "thread": THREAD, "kind": "RAISE", "frame": frame,
            "code": code, "line": line, "payload": {"exc": exc, "how": how},
            "task": task}


def handled_ev(ts, frame, code, line, exc, how, task=None):
    """The HANDLED a catch clause, a rejection callback or a completing
    `finally` writes. `how` is the shape that recorded it, decided at
    transform time -- the whole of what rule 3 reads."""
    return {"ts": ts, "thread": THREAD, "kind": "HANDLED", "frame": frame,
            "code": code, "line": line, "payload": {"exc": exc, "how": how},
            "task": task}


def yield_ev(ts, frame, code, task=None, awaiting="Promise"):
    """A suspension. `line` is null on this recorder's YIELD rows, and the
    row is what makes `frame_state` say `suspended` rather than `open`."""
    return {"ts": ts, "thread": THREAD, "kind": "YIELD", "frame": frame,
            "code": code, "line": None, "payload": {"awaiting": awaiting},
            "task": task}


def frame(code, call_ev, ret_ev=None, parent=None, depth=0,
          closed_by="return", unwind_exc=None, kind="function"):
    """One frame row. A frame left by throwing carries `closed_by:
    "unwind"` and the thrown value in `unwind_exc`, and no return event --
    `ts/build.py` writes no event for an unwind at all."""
    fr = {"parent": parent, "code": code, "call": call_ev, "depth": depth,
          "thread": THREAD, "kind": kind}
    if ret_ev is not None:
        fr["return"] = ret_ev
    if closed_by is not None and ret_ev is not None:
        fr["closed_by"] = closed_by
    if unwind_exc is not None:
        fr["closed_by"] = "unwind"
        fr["unwind_exc"] = unwind_exc
    return fr


def task(tid, name):
    """One `tasks` row. A TypeScript unit of work is a test, and its name
    is the harness's title -- which is what a PROPAGATED verdict names."""
    return (tid, name, THREAD)


def rejection(type_, msg, serial):
    """One `meta.unhandled_rejections` entry: no site, so no event (R1)."""
    return {"type": type_, "msg": msg, "serial": serial}


def ts_trace(tmp_path, monkeypatch, *, codes, events, frames=(), tasks=(),
             run_id="20260101-000000-ts0001", **meta):
    """Build a TypeScript-shaped trace from a vector body and point the CLI
    at it.

    `codes`/`frames`/`events` are the vector vocabulary (ids are 1-based
    positions; see docs/trace-format/VECTORS.md). Anything in `meta`
    overrides `TS_META`, so a test can drop `err_flow`, mark the trace
    incomplete or name a 0.1.0 recorder in one keyword.
    """
    body = {"id": "adhoc-ts", "codes": codes, "frames": list(frames),
            "events": events, "tasks": [tuple(t) for t in tasks],
            "threads_with_rows": [THREAD], "fingerprints": "compute",
            "meta": {**TS_META, **meta}}
    sdir = Path(tmp_path) / "sdir"
    build(body, sdir, [run_id])
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    return run_id


def out(capsys):
    return capsys.readouterr().out
