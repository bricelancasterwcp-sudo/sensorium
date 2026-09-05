"""The Rust traces the `exceptions` rule tests are written against.

`tests/programs.py` holds the Python programs the Python rules are tested
on; this is the same idea for a recorder whose traces cannot be produced by
running Python. Each builder states one recording as DATA -- the vector
vocabulary of `tests/vectors.py`, through `tests.helpers.rust_trace` -- so a
unit test and a conformance vector can never describe two different trace
shapes.

Split out of `test_exceptions_rust.py` when that file reached the 800-line
ceiling, along the seam the material has: the shapes are shared by three
suites (the accusation family, the ambiguous family, and the gate) and
belong to none of them.
"""
from tests.helpers import err_flow, fn_site, rust_trace

FILE = "/w/demo/src/lib.rs"
SITE_FILE = "demo/src/lib.rs"
S1 = 4294967296          # 1 << 32: the first chain serial on a thread
S2 = 4294967297
S3 = 4294967298


def call(ts, code, line, thread=1):
    return {"ts": ts, "thread": thread, "kind": "CALL", "code": code,
            "line": line, "payload": {"args": {}, "unread": ["locals"]},
            "task": None}


def ret(ts, frame, code, outcome, value="()", thread=1):
    return {"ts": ts, "thread": thread, "kind": "RETURN", "frame": frame,
            "code": code, "line": None,
            "payload": {"outcome": outcome,
                        "value": {"k": "dbg", "v": value, "trunc": False}},
            "task": None}


def flow(ts, kind, frame, code, line, payload, thread=1):
    return {"ts": ts, "thread": thread, "kind": kind, "frame": frame,
            "code": code, "line": line, "payload": payload, "task": None}


def frame(code, call_ev, ret_ev=None, parent=None, depth=0, thread=1,
          closed_by="return", unwind_exc=None):
    fr = {"parent": parent, "code": code, "call": call_ev, "depth": depth,
          "thread": thread, "kind": "function"}
    if ret_ev is not None:
        fr["return"] = ret_ev
    if closed_by is not None and ret_ev is not None:
        fr["closed_by"] = closed_by
    if unwind_exc is not None:
        fr["closed_by"] = "unwind"
        fr["unwind_exc"] = unwind_exc
    return fr


def out(capsys):
    return capsys.readouterr().out

def swallow_trace(tmp_path, monkeypatch, **meta):
    """`load()` calls `read_config()`, which returns `Err`; `load` sinks it
    with `.ok()` and returns ok. The one shape reported as a swallow."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, "read_config", 12]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S1,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(4000, 2, 2, "err", 'Err(Missing("port"))'),
            flow(5000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "demo::ConfigError", 'Missing("port")',
                          S1, hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:31")),
            ret(6000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("load", SITE_FILE, 30), fn_site("read_config",
                                                       SITE_FILE, 12)],
        **meta)

def panic_trace(tmp_path, monkeypatch, unwind_exc):
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "inner", 18]],
        frames=[frame(1, 1, None, closed_by=None, unwind_exc=unwind_exc),
                frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1,
                          terminal="panicked")),
            ret(4000, 2, 2, "err", "Err(Boom(7))"),
        ])

def harness_trace(tmp_path, monkeypatch, *, test=True, main=False,
                   sites=None):
    """`#[test] fn run()` takes an `Err` by `?` and returns it."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "inner", 18]],
        frames=[frame(1, 1, 7, closed_by="return"),
                frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(9)", S1, hop=1)),
            ret(4000, 2, 2, "err", "Err(Boom(9))"),
            flow(5000, "RAISE", 1, 1, 6,
                 err_flow("try", "demo::Boom", "Boom(9)", S1, hop=2)),
            flow(6000, "RAISE", 1, 1, 3,
                 err_flow("exit", "demo::Boom", "Boom(9)", S1, hop=3,
                          terminal="returned_to_harness")),
            ret(7000, 1, 1, "err", "Err(Boom(9))"),
        ],
        sites=(sites if sites is not None else
               [fn_site("run", SITE_FILE, 3, test=test, main=main),
                fn_site("inner", SITE_FILE, 18)]))

def five_dispositions(tmp_path, monkeypatch):
    """One trace holding every disposition, on five threads so each shape
    is minimal. The chains are laid out in REVERSE tally order, so a tally
    printed in encounter order would come out backwards."""
    unwind = {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1}
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "escapes", 5], [FILE, "inner", 18], [FILE, "stuck", 9],
               [FILE, "run", 3], [FILE, "crash", 40], [FILE, "swallow", 60]],
        frames=[
            frame(1, 1, 5),                                   # f1 escapes
            frame(2, 2, 4, parent=1, depth=1),                # f2 inner
            frame(3, 6, None, closed_by=None, thread=2),      # f3 stuck
            frame(2, 7, 9, parent=3, depth=1, thread=2),      # f4 inner
            frame(4, 10, 15, thread=3),                       # f5 run
            frame(2, 11, 13, parent=5, depth=1, thread=3),    # f6 inner
            frame(5, 16, None, thread=4, unwind_exc=unwind),  # f7 crash
            frame(2, 17, 19, parent=7, depth=1, thread=4),    # f8 inner
            frame(6, 20, 22, thread=5),                       # f9 swallow
        ],
        events=[
            # thread 1 -- ambiguous (ok close, no sink)
            call(1000, 1, 5),
            call(1100, 2, 18),
            flow(1200, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "A", S1, hop=1,
                          terminal="ambiguous_escaped")),
            ret(1300, 2, 2, "err", "Err(A)"),
            ret(1400, 1, 1, "ok", "None"),
            # thread 2 -- propagated (still open at the end)
            call(2000, 3, 9, thread=2),
            call(2100, 2, 18, thread=2),
            flow(2200, "RAISE", 4, 2, 18,
                 err_flow("exit", "demo::Boom", "B", S1, hop=1,
                          terminal="propagated"), thread=2),
            ret(2300, 4, 2, "err", "Err(B)", thread=2),
            # thread 3 -- returned to harness
            call(3000, 4, 3, thread=3),
            call(3100, 2, 18, thread=3),
            flow(3200, "RAISE", 6, 2, 18,
                 err_flow("exit", "demo::Boom", "C", S1, hop=1), thread=3),
            ret(3300, 6, 2, "err", "Err(C)", thread=3),
            flow(3400, "RAISE", 5, 4, 3,
                 err_flow("exit", "demo::Boom", "C", S1, hop=2,
                          terminal="returned_to_harness"), thread=3),
            ret(3500, 5, 4, "err", "Err(C)", thread=3),
            # thread 4 -- panicked
            call(4000, 5, 40, thread=4),
            call(4100, 2, 18, thread=4),
            flow(4200, "RAISE", 8, 2, 18,
                 err_flow("exit", "demo::Boom", "D", S1, hop=1,
                          terminal="panicked"), thread=4),
            ret(4300, 8, 2, "err", "Err(D)", thread=4),
            # thread 5 -- swallowed
            call(5000, 6, 60, thread=5),
            flow(5100, "HANDLED", 9, 6, 62,
                 err_flow("sink_ok", "demo::Boom", "E", S1, hop=1,
                          terminal="swallowed_candidate"), thread=5),
            ret(5200, 9, 6, "ok", "()", thread=5),
        ],
        sites=[fn_site("run", SITE_FILE, 3, test=True)],
        incomplete=True, live_threads=[2])
