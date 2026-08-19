"""Focus tier: LINE events carrying local deltas, and --window gating."""
from tests.helpers import record_inproc, record_inproc_full

LOOP = """
def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    return accumulate([5, 10, 20])
"""

NESTED = """
def inner(x):
    y = x * 2
    return y

def outer(x):
    a = inner(x)
    b = inner(a)
    return b

def main():
    return outer(3)
"""

# One code location entered outside, then inside, then outside the window.
REENTRY = """
def watched(tag):
    v = tag
    return v

def inside():
    return watched("in")

def main():
    watched("before")
    inside()
    watched("after")
    return 0
"""

# A generator started but never exhausted, and kept alive so the interpreter
# cannot throw GeneratorExit into it during the recording.
ABANDONED_GEN = """
KEEP = []

def numbers():
    yield 1
    yield 2

def watched(n):
    total = n
    return total

def main():
    g = numbers()
    next(g)          # runs numbers() up to the first yield, no further
    KEEP.append(g)   # ...and it is never resumed or closed
    return watched(7)
"""


def _deltas(trace):
    out = []
    for e in trace.events(kind="LINE"):
        out.append({n: v for n, v in e.payload["deltas"].items()})
    return out


def test_focused_function_yields_local_deltas(tmp_path):
    t, err = record_inproc(tmp_path, LOOP, focus=["prog:accumulate"])
    assert err is None
    seen = _deltas(t)
    assert {"total": {"k": "num", "v": 0}} in seen
    totals = [d["total"]["v"] for d in seen if "total" in d]
    assert totals == [0, 5, 15, 35]


def test_line_events_only_deltas_and_have_frames(tmp_path):
    t, _ = record_inproc(tmp_path, LOOP, focus=["prog:accumulate"])
    assert t.events(kind="LINE"), "no LINE events; the checks below are vacuous"
    for e in t.events(kind="LINE"):
        assert e.frame_id is not None and e.payload["deltas"]
        assert t.code(e.code_id).qualname == "accumulate"


def test_unfocused_run_has_no_line_events(tmp_path):
    t, _ = record_inproc(tmp_path, LOOP)
    assert t.events(kind="LINE") == []


def test_focus_does_not_change_fingerprint(tmp_path):
    t1, _ = record_inproc(tmp_path / "a", LOOP)
    t2, _ = record_inproc(tmp_path / "b", LOOP, focus=["prog:accumulate"])
    assert (next(iter(t1.fingerprints().values()))
            == next(iter(t2.fingerprints().values())))


def test_window_limits_line_capture_to_dynamic_extent(tmp_path):
    # focus on inner, but window on outer: both inner activations are inside
    # outer, so both captured
    t_in, _ = record_inproc(tmp_path / "a", NESTED,
                            focus=["prog:inner"], window="outer")
    assert len(t_in.events(kind="LINE")) > 0
    # window on a function that never runs: no LINE events at all
    t_out, _ = record_inproc(tmp_path / "b", NESTED,
                             focus=["prog:inner"], window="never_runs")
    assert t_out.events(kind="LINE") == []


def test_window_reentry_captures_a_location_missed_the_first_time(tmp_path):
    # watched() runs three times: before, inside, and after the window. Being
    # outside the window must not DISABLE the location, or the middle call --
    # the only one that matters -- would be silently lost.
    t, err = record_inproc(tmp_path, REENTRY,
                           focus=["prog:watched"], window="inside")
    assert err is None
    tags = [e.payload["deltas"]["tag"]["v"]
            for e in t.events(kind="LINE") if "tag" in e.payload["deltas"]]
    assert tags == ["in"]


def test_abandoned_generator_does_not_wedge_window_open(tmp_path):
    # A generator is frameless: no frame is opened for it, and PY_RETURN never
    # arrives if it is abandoned mid-iteration. Its qualname must therefore
    # never move window_depth, or the window stays open for the rest of the run
    # and every later focused call is captured as if it were inside it.
    t, err, tracer = record_inproc_full(
        tmp_path / "windowed", ABANDONED_GEN,
        focus=["prog:watched"], window="numbers")
    assert err is None
    assert tracer._tls.window_depth == 0
    assert t.events(kind="LINE") == []      # watched() ran outside the window
    # ...and the emptiness above is not vacuous: with no window at all, the
    # very same program does yield LINE events for watched().
    ctl, _ = record_inproc(tmp_path / "control", ABANDONED_GEN,
                           focus=["prog:watched"])
    quals = [ctl.code(e.code_id).qualname for e in ctl.events(kind="LINE")]
    assert quals and set(quals) == {"watched"}
