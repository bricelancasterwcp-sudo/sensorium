from tests.helpers import record_inproc

ADD = """
def add(a, b):
    return a + b

def main():
    return add(2, 3)
"""

SWALLOW = """
def parse(s):
    return int(s)

def main():
    try:
        parse("x7")
    except ValueError:
        pass
"""

BOOM = """
def boom():
    raise RuntimeError("dead")

def main():
    boom()
"""

STDLIB = """
import json

def main():
    return json.dumps({"a": 1})
"""

GEN = """
def gen():
    yield 1
    yield 2

def main():
    return list(gen())
"""


def test_calls_returns_args_and_frames(tmp_path):
    t, err = record_inproc(tmp_path, ADD)
    assert err is None
    kinds = [e.kind for e in t.events()]
    assert kinds.count("CALL") == 2 and kinds.count("RETURN") == 2
    add_call = next(e for e in t.events(kind="CALL")
                    if t.code(e.code_id).qualname == "add")
    assert add_call.payload["args"]["a"] == {"k": "num", "v": 2}
    assert add_call.frame_id is None                 # CALL: frame links back
    f = t.frame_containing(add_call.id)
    assert f is not None and f.depth == 1 and f.closed_by == "return"
    ret = t.event(f.return_event_id)
    assert ret.payload["value"] == {"k": "num", "v": 5}


def test_raise_and_handled_share_oid(tmp_path):
    t, err = record_inproc(tmp_path, SWALLOW)
    assert err is None
    raises = t.events(kind="RAISE")
    handles = t.events(kind="HANDLED")
    assert len(raises) == 1 and len(handles) == 1
    assert raises[0].payload["exc"]["type"] == "ValueError"
    assert raises[0].payload["exc"]["oid"] == handles[0].payload["exc"]["oid"]


def test_exc_events_carry_traced_program_line_numbers(tmp_path):
    # Regression: the exception callbacks must report the line in the *traced*
    # program, not a line inside the tracer's own callback plumbing.
    t, err = record_inproc(tmp_path, SWALLOW)
    n_lines = len(SWALLOW.splitlines())
    raise_ev = t.events(kind="RAISE")[0]
    assert raise_ev.line == 3                    # "    return int(s)"
    for e in t.events():
        assert e.line is None or 1 <= e.line <= n_lines


def test_uncaught_closes_frames_by_unwind(tmp_path):
    t, err = record_inproc(tmp_path, BOOM)
    assert type(err).__name__ == "RuntimeError"
    boom_code = next(c for c in t.codes() if c.qualname == "boom")
    f = t.frames(code_id=boom_code.id)[0]
    assert f.closed_by == "unwind"
    assert f.unwind_exc["type"] == "RuntimeError"


def test_stdlib_not_traced(tmp_path):
    t, err = record_inproc(tmp_path, STDLIB)
    files = {t.code(e.code_id).file for e in t.events() if e.code_id}
    assert all(str(tmp_path) in f for f in files)


def test_generators_recorded_frameless(tmp_path):
    t, err = record_inproc(tmp_path, GEN)
    assert err is None
    gen_calls = [e for e in t.events(kind="CALL")
                 if t.code(e.code_id).qualname == "gen"]
    assert len(gen_calls) == 1
    gen_code = next(c for c in t.codes() if c.qualname == "gen")
    assert t.frames(code_id=gen_code.id) == []


def test_fingerprint_deterministic_across_runs(tmp_path):
    t1, _ = record_inproc(tmp_path / "a", ADD)
    t2, _ = record_inproc(tmp_path / "b", ADD)
    h1 = next(iter(t1.fingerprints().values()))
    h2 = next(iter(t2.fingerprints().values()))
    assert h1[0] != "" and h1 == h2
