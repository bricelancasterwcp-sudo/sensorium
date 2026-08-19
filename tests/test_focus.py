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

# `del a` on line 5. Nothing else changes on the following line, so without an
# unbind marker that line emits no event at all and the deletion vanishes.
DEL_LOCAL = """
def watched(n):
    a = n
    b = a + 1
    del a
    c = b + 1
    return c

def main():
    return watched(1)
"""

# `except ... as e` unbinds e implicitly when the handler ends. This is the
# shape that matters: the stale binding would otherwise survive exactly into
# the region someone debugging an exception is reading.
EXC_UNBIND = """
def watched(xs):
    try:
        v = xs[5]
    except IndexError as e:
        m = str(e)
    n = 1
    return m + str(n)

def main():
    return watched([])
"""

# __repr__ calls a *traced* function, so enabling focus makes user code run
# many extra times inside capture. The fingerprint still must not move.
REPR_CALLS_TRACED = """
class Weird:
    def __init__(self, n):
        self.n = n
    def __repr__(self):
        return helper(self.n)

def helper(n):
    return "W%d" % n

def watched(n):
    w = Weird(n)
    m = w
    k = m
    return k

def main():
    return watched(4)
"""

# raise -> bare re-raise in a handler -> caught in main. Exercises the RAISE
# origin de-dupe, RERAISE re-arm and EXCEPTION_HANDLED disarm all at once.
EXC_CHAIN = """
def leaf(n):
    step = n
    raise ValueError("boom-%d" % step)

def middle(n):
    try:
        return leaf(n)
    except ValueError:
        raise

def main():
    try:
        return middle(1)
    except ValueError as e:
        return str(e)
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
        assert e.frame_id is not None
        # An event carries a change: new/changed bindings, names that went
        # away, or both. An unbind-only event has empty deltas and is valid.
        assert e.payload["deltas"] or e.payload.get("unbound")
        assert t.code(e.code_id).qualname == "accumulate"
    # This program never unbinds, so here every event must carry deltas.
    assert all(e.payload["deltas"] for e in t.events(kind="LINE"))
    assert not any("unbound" in e.payload for e in t.events(kind="LINE"))


def test_line_number_is_the_line_about_to_execute(tmp_path):
    # Pins the contract Task 10 renders: `line` is the line ABOUT TO RUN, and
    # the deltas are what the PRECEDING line produced.
    t, err = record_inproc(tmp_path, LOOP, focus=["prog:accumulate"])
    assert err is None
    seq = [(e.line, {n: v.get("v", v.get("type"))
                     for n, v in e.payload["deltas"].items()})
           for e in t.events(kind="LINE")]
    assert seq == [
        (3, {"ops": "list"}),   # about to run `total = 0`; the CALL bound ops
        (4, {"total": 0}),      # about to run the `for`; line 3 set total
        (5, {"op": 5}),         # about to run the body; the `for` bound op
        (4, {"total": 5}),      # back at the `for`; line 5 set total
        (5, {"op": 10}),
        (4, {"total": 15}),
        (5, {"op": 20}),
        (4, {"total": 35}),
    ]
    # `return total` (line 6) changed nothing, so it emitted no event at all.
    assert 6 not in [line for line, _ in seq]


def test_explicit_del_is_reported_as_unbound(tmp_path):
    t, err = record_inproc(tmp_path, DEL_LOCAL, focus=["prog:watched"])
    assert err is None
    unbinds = [(e.line, e.payload["unbound"]) for e in t.events(kind="LINE")
               if e.payload.get("unbound")]
    assert unbinds == [(6, ["a"])]
    # ...and the event exists even though NOTHING else changed on that line,
    # which is the case that used to be dropped entirely.
    ev = [e for e in t.events(kind="LINE") if e.payload.get("unbound")][0]
    assert ev.payload["deltas"] == {}
    assert ev.frame_id is not None


def test_except_as_implicit_unbind_is_reported(tmp_path):
    t, err = record_inproc(tmp_path, EXC_UNBIND, focus=["prog:watched"])
    assert err is None
    lines = t.events(kind="LINE")
    # e is bound by the except clause...
    assert any("e" in e.payload["deltas"] for e in lines)
    # ...and CPython unbinds it when the handler ends; that must be visible,
    # on the same event that reports the next binding.
    unbound = [e for e in lines if e.payload.get("unbound")]
    assert len(unbound) == 1
    assert unbound[0].payload["unbound"] == ["e"]
    assert "m" in unbound[0].payload["deltas"]
    # Folding deltas in order must not leave e alive past its unbind.
    live: dict = {}
    for e in lines:
        live.update(e.payload["deltas"])
        for name in e.payload.get("unbound", ()):
            live.pop(name, None)
    assert "e" not in live and "m" in live


def test_unfocused_run_has_no_line_events(tmp_path):
    t, _ = record_inproc(tmp_path, LOOP)
    assert t.events(kind="LINE") == []


def test_focus_does_not_change_fingerprint(tmp_path):
    t1, _ = record_inproc(tmp_path / "a", LOOP)
    t2, _ = record_inproc(tmp_path / "b", LOOP, focus=["prog:accumulate"])
    assert t2.events(kind="LINE"), "focus silently no-opped; nothing is proven"
    assert (next(iter(t1.fingerprints().values()))
            == next(iter(t2.fingerprints().values())))


def test_capture_side_effects_do_not_change_fingerprint(tmp_path):
    # The headline promise, adversarially: a captured local's __repr__ calls a
    # traced function, so focus makes user code run many extra times inside
    # capture. Neither the hash nor the event count may move.
    runs = {}
    for tag, kw in (("plain", {}),
                    ("focus", {"focus": ["prog:watched"]}),
                    ("focus+window", {"focus": ["prog:watched"],
                                      "window": "main"})):
        t, err, _ = record_inproc_full(tmp_path / tag, REPR_CALLS_TRACED, **kw)
        assert err is None
        runs[tag] = (next(iter(t.fingerprints().values())), t.counts())
    assert runs["plain"][1].get("LINE", 0) == 0
    assert runs["focus"][1].get("LINE", 0) > 0
    assert runs["focus+window"][1].get("LINE", 0) > 0
    # hash AND n_events byte-identical across all three
    assert len({fp for fp, _ in runs.values()}) == 1
    # helper() ran inside capture many times and produced no event either way
    assert {tag: c["CALL"] for tag, (_, c) in runs.items()} == {
        "plain": 3, "focus": 3, "focus+window": 3}


def test_focus_does_not_disturb_the_exception_state_machine(tmp_path):
    # Every tracer.py exception test runs with E.LINE off. This one turns focus
    # on over a raise/re-raise/handle chain and demands the same recording.
    def shape(tr):
        return [(e.kind, tr.code(e.code_id).qualname, e.payload["exc"]["type"],
                 e.line) for e in tr.events(kind=("RAISE", "HANDLED"))]

    def frames(tr):
        return [(tr.code(f.code_id).qualname, f.closed_by)
                for f in tr.frames()]

    plain, err_a = record_inproc(tmp_path / "plain", EXC_CHAIN)
    focused, err_b = record_inproc(
        tmp_path / "focus", EXC_CHAIN,
        focus=["prog:leaf", "prog:middle", "prog:main"])
    assert err_a is None and err_b is None
    assert focused.events(kind="LINE"), "focus did not engage; nothing proven"
    assert shape(plain) == shape(focused)
    assert frames(plain) == frames(focused)
    assert (next(iter(plain.fingerprints().values()))
            == next(iter(focused.fingerprints().values())))


def test_window_limits_line_capture_to_dynamic_extent(tmp_path):
    # focus on inner, but window on outer: both inner activations are inside
    # outer, so both captured
    t_in, _ = record_inproc(tmp_path / "a", NESTED,
                            focus=["prog:inner"], window="outer")
    lines = t_in.events(kind="LINE")
    assert len(lines) > 0
    assert {t_in.code(e.code_id).qualname for e in lines} == {"inner"}
    # BOTH activations, not just the first: inner(3) then inner(6).
    assert len({e.frame_id for e in lines}) == 2
    xs = [e.payload["deltas"]["x"]["v"] for e in lines
          if "x" in e.payload["deltas"]]
    assert xs == [3, 6]
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
