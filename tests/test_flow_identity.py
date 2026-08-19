"""`flow --object`: one object followed across a trace, honestly.

`oid` is `id(obj)` and CPython recycles addresses, so every shape here is
recorded from a REAL program whose addresses actually collide -- verified,
not imagined. `TWO_TYPES_ONE_ADDRESS` puts four objects on one address in six
lines of ordinary code, and `REUSED_ADDRESS` gives three dicts one address in
a plain loop. A command matching on `oid` alone reports those as one object's
story, which is exactly the failure this file exists to prevent.

The equality half of `flow` lives in `test_flow.py`; this is the split the
exceptions tests made for the same reason, along the same kind of seam.
"""
import shlex

from sensorium import cli
from sensorium.query import flow_cmd
from tests.programs import (ALIAS, GRAMS, flow_rows, flow_shown_ids,
                            interleaved_address, obj_captures, open_trace,
                            record, synthetic)

# Two classes with the same instance layout, allocated and freed alternately.
# Measured (three runs, identical): one address hosts Draft, Final, Draft,
# Final in turn -- four distinct objects, one `oid`.
TWO_TYPES_ONE_ADDRESS = """
class Draft:
    def __init__(self, v):
        self.v = v

class Final:
    def __init__(self, v):
        self.v = v

def make_draft(v):
    return Draft(v)

def make_final(v):
    return Final(v)

def take(x):
    return x.v

def main():
    for i in range(3):
        take(make_draft(i))
        take(make_final(i))

if __name__ == "__main__":
    main()
"""

# Three dicts, never bound to a local, each freed before the next is made.
# Measured (three runs, identical): all three share one address.
REUSED_ADDRESS = """
def make(tag):
    return {"tag": tag}

def take(d):
    return d["tag"]

def main():
    for tag in ("a", "b", "c"):
        print(take(make(tag)))

if __name__ == "__main__":
    main()
"""
# The only recorded binding of the returned object is the callee's own local,
# which is live right up to and including the RETURN event that hands it out.
RETURNED = """
def build():
    box = {"tag": "x"}
    return box

def main():
    print(build()["tag"])

if __name__ == "__main__":
    main()
"""
# The object is an argument of a frame that never returns: the exception
# unwinds it, so no RETURN event is ever recorded for it.
UNWOUND = """
def blow(cfg):
    cfg["x"] = 1
    raise ValueError("boom")

def main():
    blow({"a": 1})

if __name__ == "__main__":
    main()
"""

# One name, two objects, then neither: the binding that holds an address has
# to end at the rebinding, and the next one at the `del`.
REBIND = """
def make(tag):
    return {"tag": tag}

def main():
    box = make("a")
    box = make("b")
    del box
    return None

if __name__ == "__main__":
    main()
"""

# The hole under `held by fN`. `x` is dropped and rebuilt on ONE physical
# line, so no LINE event fires between the two statements -- and the tracer
# emits a delta by comparing CAPTURES, so the second dict, at the same address
# with equal content, produces a capture identical to the first and therefore
# no delta at all. Two objects, one address, one recorded binding, and nothing
# in the trace that distinguishes them. ADDRESS REUSED cannot catch it either:
# the type never changes. Measured identical across three runs.
REBIND_TO_EQUAL = """
def build():
    return {"n": 1}

def use(box):
    return box["n"]

def main():
    x = build()
    use(x)
    x = None; x = build()
    use(x)

if __name__ == "__main__":
    main()
"""


# A plain loop, one object per pass. Measured identical across three runs: two
# of the four Nodes land on ONE address. Same type throughout, so ADDRESS
# REUSED is blind to it -- but `Node.__init__` runs on that address between the
# two objects' sightings, and the trace records it.
CTOR_REUSE = """
class Node:
    def __init__(self, v):
        self.v = v

def make(v):
    return Node(v)

def use(n):
    return n.v

def main():
    for i in range(4):
        use(make(i))

if __name__ == "__main__":
    main()
"""

# The counterexample to "re-running a constructor on a live object is
# pathological". The textbook caching-__new__ singleton: `Config.__new__`
# returns ONE address twice and `Config.__init__` then runs on that same LIVE
# object twice, with `a is b` true. Reporting two objects here would be a
# false split -- the mirror of the lineage the constructor signal catches.
CACHING_NEW = """
class Config:
    _inst = None
    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst
    def __init__(self):
        self.n = 1

def get():
    return Config()

def main():
    a = get()
    b = get()
    print(a is b, a.n)

if __name__ == "__main__":
    main()
"""

# An existing object handed INTO a constructor. `data` is the second argument
# of `Box.__init__`, not its receiver, so nothing was constructed at `data`'s
# address and the lineage must not be split there.
CTOR_ARG = """
class Box:
    def __init__(self, payload):
        self.payload = payload

def main():
    data = {"n": 1}
    box = Box(data)
    print(box.payload["n"], data["n"])

if __name__ == "__main__":
    main()
"""

# The ranking case. `x` holds the address across the whole loop body, and its
# capture never changes -- `repr(Node(...))` is just the address, so two Nodes
# at one address are captured identically and no delta is ever emitted. The
# binding therefore spans a gap in which a Node was demonstrably rebuilt.
# Measured identical across three runs: one address hosts two of the four.
CTOR_HIDDEN = """
class Node:
    def __init__(self, v):
        self.v = v

def make(v):
    return Node(v)

def use(n):
    return n.v

def main():
    x = None
    for i in range(4):
        x = None; x = make(i)
        use(x)

if __name__ == "__main__":
    main()
"""


# -- --object --------------------------------------------------------------
def test_flow_object_shows_aliasing(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, ALIAS)
    assert cli.main(["flow", run_id, "--object", "derive_sandbox:cfg"]) == 0
    out = capsys.readouterr().out
    assert "make_default ->" in out          # same oid seen at creation...
    assert "derive_sandbox(cfg=" in out      # ...and entering the mutator
    assert "flow of object #" in out


def test_flow_object_reveals_that_the_callers_config_changed(
        tmp_path, monkeypatch, capsys):
    """The aliasing shape the command exists for: `derive_sandbox` mutates
    the dict it was handed, so the caller's `prod` changes without the caller
    touching it. Identity is what shows it -- `prod` and `sand` are one
    object, and a frame that held it names the gap it covers."""
    run_id = record(tmp_path, monkeypatch, ALIAS, extra=("--focus", "prog"))
    trace = open_trace(run_id)
    main_f = next(f for f in trace.frames()
                  if trace.code(f.code_id).qualname == "main")

    assert cli.main(["flow", run_id, "--object", "derive_sandbox:cfg"]) == 0
    out = capsys.readouterr().out
    assert "[local prod]" in out and "[arg cfg]" in out
    assert "[local prod, local sand]" in out
    assert "'timeout': 1" in out and "'timeout': 30" in out
    assert f"spanned by f{main_f.id} across e" in out
    assert "'prod' bound at e" in out
    # the claim is what the trace supports, not affirmative continuity
    assert "no differing capture of 'prod' recorded through e" in out
    assert "no rebinding recorded" not in out
    assert out.count("spanned by f") == 1, "one run of gaps is one fact"
    # only the hop from make_default's return into main's local is unwitnessed
    assert "continuity: 6 gap(s) spanned by a recorded binding, " \
        "1 unwitnessed" in out


def test_flow_object_never_claims_a_rebinding_would_have_been_recorded(
        tmp_path, monkeypatch, capsys):
    """The strongest positive claim `flow` makes, held to what is true.

    `main` really does hold two different dicts here -- `build()` allocates a
    fresh one each call -- and the trace records NOTHING that separates them:
    the second took the freed address and has equal content, so its capture is
    identical to the first's and the tracer emits no delta (it compares
    captures, not objects). ADDRESS REUSED cannot fire either, because the
    type never changed.

    So the covering binding is still worth reporting -- it is the only
    continuity evidence there is -- but it must not be reported as a rebinding
    having been ruled out. It was not; the trace simply has nothing to show.
    """
    run_id = record(tmp_path, monkeypatch, REBIND_TO_EQUAL,
                    extra=("--focus", "prog:main"))
    trace = open_trace(run_id)
    built = [e.payload["value"] for e in trace.events(kind="RETURN")
             if (e.payload or {}).get("value", {}).get("k") == "map"]
    assert len(built) == 2, "two separate build() activations must be recorded"
    assert built[0]["oid"] == built[1]["oid"], (
        f"this test needs the rebuilt dict at the freed address: {built}")
    # ...and the trace is genuinely blind to the swap: one delta for `x`, ever
    xs = [e for e in trace.events(kind="LINE")
          if "x" in (e.payload or {}).get("deltas", {})
          or "x" in (e.payload or {}).get("unbound", [])]
    assert len(xs) == 1, f"the rebinding must leave no record at all: {xs}"

    assert cli.main(["flow", run_id, "--object", "build:return"]) == 0
    out = capsys.readouterr().out
    assert "no rebinding recorded" not in out, "it was not ruled out"
    assert "no differing capture of 'x' recorded through e10" in out
    # and the header says outright what such a line does not rule out
    assert "evidence, not proof" in out
    assert "equal content records no change at all" in out


def test_flow_object_on_primitive_is_clear_error(tmp_path, monkeypatch,
                                                 capsys):
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--object",
                     "shipping_cost:weight_kg"]) == 1
    assert "use --value" in capsys.readouterr().out


def test_flow_object_states_the_identity_residual_in_its_own_output(
        tmp_path, monkeypatch, capsys):
    """Another agent reads this text as evidence. The caveat has to be in the
    output, not only in a docstring."""
    run_id = record(tmp_path, monkeypatch, ALIAS)
    assert cli.main(["flow", run_id, "--object", "derive_sandbox:cfg"]) == 0
    out = capsys.readouterr().out
    assert "identity-based lineage, not true dataflow analysis" in out
    assert "memory address plus type" in out
    assert "recycles addresses" in out
    assert "may be a different object that reused it" in out


def test_flow_object_never_fuses_two_types_at_one_address(
        tmp_path, monkeypatch, capsys):
    """`oid` alone is not an identity. This trace really does put a Draft and
    a Final on one address; matching on `oid` alone splices their histories
    into one lineage and prints it as one object's story."""
    run_id = record(tmp_path, monkeypatch, TWO_TYPES_ONE_ADDRESS)
    trace = open_trace(run_id)
    _addr, at_addr = interleaved_address(trace, "Draft", "Final")
    drafts = [eid for eid, typ in at_addr if typ == "Draft"]
    finals = [eid for eid, typ in at_addr if typ == "Final"]
    assert len(drafts) >= 2 and len(finals) >= 1

    assert cli.main(["flow", run_id, "--object", f"e{drafts[0]}:self"]) == 0
    out = capsys.readouterr().out
    shown = flow_shown_ids(out)
    assert set(drafts) <= shown
    assert not set(finals) & shown, "a Final was listed in a Draft lineage"
    assert "(Draft)" in out


def test_flow_object_reports_a_proven_address_reuse(tmp_path, monkeypatch,
                                                    capsys):
    """Two live objects never share an address, so a different type captured
    at this one between two sightings PROVES the earlier object was gone.
    That is the one identity fact the trace can settle, and it must be said
    loudly rather than left to the general caveat."""
    run_id = record(tmp_path, monkeypatch, TWO_TYPES_ONE_ADDRESS)
    trace = open_trace(run_id)
    _addr, at_addr = interleaved_address(trace, "Draft", "Final")
    drafts = [eid for eid, typ in at_addr if typ == "Draft"]
    finals = [eid for eid, typ in at_addr if typ == "Final"]
    # the shape needs a Final strictly between two Draft sightings
    split = [eid for eid in finals if drafts[0] < eid < drafts[-1]]
    assert split, f"fixture no longer interleaves: {at_addr}"

    assert cli.main(["flow", run_id, "--object", f"e{drafts[0]}:self"]) == 0
    out = capsys.readouterr().out
    assert "ADDRESS REUSED" in out
    assert f"e{split[0]} captured a Final at this address" in out
    assert "different objects" in out
    assert "1 crossed a proven address reuse" in out


def test_flow_object_page_two_accounts_for_the_gap_it_starts_after(
        tmp_path, monkeypatch, capsys):
    """A later page must stand on its own terms. The gap crossing the page
    boundary is what precedes its first row -- and when that gap is a proven
    address reuse it is the most important thing on the page -- so it is
    annotated above the first row and counted in that page's footer, not left
    behind in the previous page's output."""
    run_id = record(tmp_path, monkeypatch, TWO_TYPES_ONE_ADDRESS)
    trace = open_trace(run_id)
    _addr, at_addr = interleaved_address(trace, "Draft", "Final")
    drafts = [eid for eid, typ in at_addr if typ == "Draft"]
    spec = f"e{drafts[0]}:self"

    assert cli.main(["flow", run_id, "--object", spec, "--limit", "3"]) == 0
    page1 = capsys.readouterr().out
    hint = page1.strip().splitlines()[-1]
    assert "continue with: " in hint
    argv = shlex.split(hint.split("continue with: ", 1)[1])[1:]

    assert cli.main(argv) == 0
    page2 = capsys.readouterr().out
    rows = flow_rows(page2)
    assert [int(r.split()[0][1:]) for r in rows] == drafts[3:]
    assert "ADDRESS REUSED" in page2               # carried onto this page
    assert page2.count("ADDRESS REUSED") == 1      # once, and attached once
    assert "1 crossed a proven address reuse" in page2   # and into its tally
    # ...announced above the first row it leads into, not after it
    body = page2.splitlines()
    reuse_at = next(i for i, ln in enumerate(body) if "ADDRESS REUSED" in ln)
    first_row = next(i for i, ln in enumerate(body)
                     if ln.strip().startswith(f"e{drafts[3]} "))
    assert reuse_at < first_row


def test_flow_object_splits_where_a_constructor_ran_on_the_address(
        tmp_path, monkeypatch, capsys):
    """The same-type reuse that nothing else catches.

    Two Nodes share one address, so `(oid, type)` cannot separate them and
    ADDRESS REUSED never fires -- the type never changes. But `Node.__init__`
    ran on that address between the two objects' sightings, and that is in the
    trace. Without it the run reads as one continuous lineage with a
    constructor sitting unremarked in the middle of it.
    """
    run_id = record(tmp_path, monkeypatch, CTOR_REUSE)
    trace = open_trace(run_id)
    at = {}
    for eid, oid, typ in obj_captures(trace):
        at.setdefault(oid, []).append(eid)
    shared = [oid for oid, ids in at.items() if len(ids) > 3]
    assert len(shared) == 1, f"this test needs two Nodes on one address: {at}"
    sightings = at[shared[0]]
    inits = [e.id for e in trace.events(kind="CALL")
             if trace.code(e.code_id).qualname == "Node.__init__"
             and e.payload["args"]["self"]["oid"] == shared[0]]
    assert len(inits) == 2, "two constructions at one address is the shape"

    assert cli.main(["flow", run_id, "--object", f"e{inits[0]}:self"]) == 0
    out = capsys.readouterr().out
    assert set(sightings) == flow_shown_ids(out)      # one apparent lineage...
    # ...split exactly once, at the second construction and nowhere else. The
    # first construction is the left end of the first gap, and a constructor
    # there says only that the object already seen was built -- splitting on
    # it would cut a real object's lineage in two.
    assert out.count("NEW OBJECT") == 1
    assert f"e{inits[1]} is Node.__init__ on this address" in out
    assert "different objects" in out
    assert "0 gap(s) spanned by a recorded binding" in out
    assert "4 unwitnessed" in out          # the split gap is not one of them
    assert "1 crossed a recorded construction" in out
    body = out.splitlines()
    split_at = next(i for i, ln in enumerate(body) if "NEW OBJECT" in ln)
    born_at = next(i for i, ln in enumerate(body)
                   if ln.strip().startswith(f"e{inits[1]} "))
    assert split_at < born_at


def test_flow_object_ranks_a_constructor_above_a_binding_that_spans_it(
        tmp_path, monkeypatch, capsys):
    """A binding that appears to span a construction is exactly the case in
    which the binding is wrong.

    `x` holds this address across the whole loop body and never changes
    capture -- `repr` of an instance is just its address, so two Nodes at one
    address are recorded identically and no delta is ever emitted. Reading
    that as continuity is the round-1 hole; the constructor in the middle of
    it is the evidence that settles the question, so it must out-rank the
    binding and be counted as its own thing rather than as a spanned gap.
    """
    run_id = record(tmp_path, monkeypatch, CTOR_HIDDEN,
                    extra=("--focus", "prog:main"))
    trace = open_trace(run_id)
    at = {}
    for eid, oid, typ in obj_captures(trace):
        at.setdefault(oid, []).append(eid)
    shared = [oid for oid, ids in at.items() if len(ids) > 4]
    assert len(shared) == 1, f"this test needs two Nodes on one address: {at}"
    # the binding really is blind here: `x` is recorded once and never again
    deltas = [e for e in trace.events(kind="LINE")
              if (e.payload or {}).get("deltas", {}).get("x", {}).get("oid")
              == shared[0]]
    assert len(deltas) == 1, f"identical re-captures emit no delta: {deltas}"

    assert cli.main(["flow", run_id, "--object",
                     f"e{at[shared[0]][0]}:self"]) == 0
    out = capsys.readouterr().out
    assert "NEW OBJECT" in out and out.count("NEW OBJECT") == 1
    assert "spanned by f" in out                    # the binding is still real
    assert "3 gap(s) spanned by a recorded binding" in out   # but not that gap
    assert "1 crossed a recorded construction" in out


def test_flow_object_will_not_split_a_caching_new_that_reinits_a_live_object(
        tmp_path, monkeypatch, capsys):
    """The counterexample to treating a constructor as proof.

    A caching `__new__` hands back a LIVE instance and Python re-runs
    `__init__` on it, so `Config.__init__` runs twice on one address that
    never held two objects -- the program itself prints `a is b` as True.
    Asserting "different objects" here would be the same false claim, pointed
    the other way, so the trace's own evidence of the idiom downgrades it.
    """
    run_id = record(tmp_path, monkeypatch, CACHING_NEW)
    trace = open_trace(run_id)
    news = [e for e in trace.events(kind="RETURN")
            if e.code_id is not None
            and trace.code(e.code_id).qualname == "Config.__new__"]
    inits = [e for e in trace.events(kind="CALL")
             if e.code_id is not None
             and trace.code(e.code_id).qualname == "Config.__init__"]
    assert len(news) == 2 and len(inits) == 2
    one = {e.payload["value"]["oid"] for e in news}
    assert one == {e.payload["args"]["self"]["oid"] for e in inits}
    assert len(one) == 1, "the idiom needs one address throughout"

    assert cli.main(["flow", run_id, "--object", "get:return"]) == 0
    out = capsys.readouterr().out
    assert "NEW OBJECT" not in out, "there is provably one object here"
    assert "different objects" not in out
    assert "CONSTRUCTOR RAN" in out                   # still surfaced...
    assert "Config.__new__, which hands back instances of this type" in out
    assert "the trace cannot say a new one was born here" in out
    # both __init__ calls AND the second __new__ return are construction
    # evidence: 3 of the 5 gaps, with only 2 left unaccounted for
    assert "e13 is Config.__new__ on this address" in out
    assert "2 unwitnessed" in out
    assert "3 crossed a recorded construction" in out

    # ...and the class object those same constructors were called *about* is
    # at another address: neither signal may reach across to it
    cls_call = next(e for e in trace.events(kind="CALL")
                    if e.code_id is not None
                    and trace.code(e.code_id).qualname == "Config.__new__")
    assert cls_call.payload["args"]["cls"]["oid"] not in one
    assert cli.main(["flow", run_id, "--object", f"e{cls_call.id}:cls"]) == 0
    other = capsys.readouterr().out
    assert "(type)" in other
    assert "CONSTRUCTOR RAN" not in other and "NEW OBJECT" not in other


def test_flow_object_does_not_split_on_a_constructor_argument(
        tmp_path, monkeypatch, capsys):
    """Only the RECEIVER is the object being constructed. `Box.__init__(self,
    payload)` hands an existing dict into a constructor; reading that as
    "payload was born here" splits one real object's lineage and asserts two
    -- the mirror of the bug the signal exists to catch."""
    run_id = record(tmp_path, monkeypatch, CTOR_ARG,
                    extra=("--focus", "prog:main"))
    trace = open_trace(run_id)
    init = next(e for e in trace.events(kind="CALL")
                if e.code_id is not None
                and trace.code(e.code_id).qualname == "Box.__init__")
    assert list(init.payload["args"]) == ["self", "payload"]
    assert init.payload["args"]["payload"]["k"] == "map"   # the target...
    assert init.payload["args"]["self"]["type"] == "Box"   # ...is not first

    assert cli.main(["flow", run_id, "--object",
                     f"e{init.id}:payload"]) == 0
    out = capsys.readouterr().out
    assert "NEW OBJECT" not in out and "CONSTRUCTOR RAN" not in out
    assert "spanned by f" in out
    assert "0 unwitnessed" in out


def test_flow_object_hedges_a_gap_nothing_in_the_trace_holds(
        tmp_path, monkeypatch, capsys):
    """Three dicts, one address, and no local ever bound to them. The trace
    cannot tell them apart, and the honest report is a named gap -- not one
    continuous lineage, and not a claim that the address was reused either,
    which this trace does not prove."""
    run_id = record(tmp_path, monkeypatch, REUSED_ADDRESS)
    trace = open_trace(run_id)
    maps = [(e.id, e.payload["value"]["oid"])
            for e in trace.events(kind="RETURN")
            if (e.payload or {}).get("value", {}).get("k") == "map"]
    assert len({oid for _e, oid in maps}) == 1, (
        f"this test needs the three dicts to share one address: {maps}")

    assert cli.main(["flow", run_id, "--object", f"e{maps[0][0]}:return"]) == 0
    out = capsys.readouterr().out
    assert "unwitnessed" in out
    assert "ADDRESS REUSED" not in out           # not proven by this trace
    assert "0 gap(s) spanned by a recorded binding" in out


def test_flow_object_qualname_resolves_to_the_first_call_and_says_so(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, TWO_TYPES_ONE_ADDRESS)
    trace = open_trace(run_id)
    calls = [e.id for e in trace.events(kind="CALL")
             if e.code_id is not None
             and trace.code(e.code_id).qualname == "take"]
    assert len(calls) == 6

    assert cli.main(["flow", run_id, "--object", "take:x"]) == 0
    out = capsys.readouterr().out
    assert "the first of 6 recorded CALL(s) of take" in out
    assert f"e{calls[1]}" in out             # the others are named, exactly
    assert "<id>" not in out and "eN" not in out


def test_flow_object_follows_what_a_call_handed_back(tmp_path, monkeypatch,
                                                     capsys):
    """A qualname resolves to a CALL, where a return value never lives.
    `<qualname>:return` has to follow that activation to its RETURN instead of
    refusing -- "where did the dict this made end up" is the whole question."""
    run_id = record(tmp_path, monkeypatch, ALIAS)
    trace = open_trace(run_id)
    ret = next(e for e in trace.events(kind="RETURN")
               if (e.payload or {}).get("value", {}).get("k") == "map")

    assert cli.main(["flow", run_id, "--object", "make_default:return"]) == 0
    out = capsys.readouterr().out
    assert f"its return is captured at e{ret.id}" in out
    assert "derive_sandbox(cfg=" in out
    assert ret.id in flow_shown_ids(out)


def test_flow_object_bad_specs_fail_loudly(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, ALIAS)
    assert cli.main(["flow", run_id, "--object", "cfg"]) == 1
    assert "e<id>:<name>" in capsys.readouterr().out

    assert cli.main(["flow", run_id, "--object", "nosuchfn:cfg"]) == 1
    assert "no CALL of 'nosuchfn'" in capsys.readouterr().out

    assert cli.main(["flow", run_id, "--object", "e99999:cfg"]) == 1
    assert "no event e99999" in capsys.readouterr().out

    assert cli.main(["flow", run_id, "--object", "derive_sandbox:nope"]) == 1
    out = capsys.readouterr().out
    assert "'nope' is not captured" in out and "captured there: cfg" in out

    # ":return" is only followed through a CALL; a LINE event has no return
    focused = record(tmp_path / "b", monkeypatch, ALIAS,
                     extra=("--focus", "prog:main"))
    line = open_trace(focused).events(kind="LINE")[0]
    assert cli.main(["flow", focused, "--object", f"e{line.id}:return"]) == 1
    assert f"'return' is not captured at e{line.id}" in capsys.readouterr().out


def test_flow_object_witnesses_across_a_frame_that_unwound(
        tmp_path, monkeypatch, capsys):
    """An unwound frame records no RETURN event, so there is no end id to
    read. Treating it as ending at its CALL would drop every witness inside
    it and report a continuous, fully-held lineage as unwitnessed."""
    run_id = record(tmp_path, monkeypatch, UNWOUND,
                    extra=("--focus", "prog:blow"))
    trace = open_trace(run_id)
    blow_f = next(f for f in trace.frames()
                  if trace.code(f.code_id).qualname == "blow")
    assert blow_f.closed_by == "unwind" and blow_f.return_event_id is None

    assert cli.main(["flow", run_id, "--object", "blow:cfg"]) == 0
    out = capsys.readouterr().out
    assert f"spanned by f{blow_f.id} across e" in out
    assert "0 unwitnessed" in out

    # ...and that frame handed nothing back, so there is no return to follow
    assert cli.main(["flow", run_id, "--object", "blow:return"]) == 1
    assert "'return' is not captured" in capsys.readouterr().out


def test_flow_object_counts_a_local_as_held_through_its_own_return(
        tmp_path, monkeypatch, capsys):
    """A local is live right up to and including the RETURN event that hands
    it out -- that event is inside the frame, not after it. Ending the frame
    one event early loses the only witness a returned object usually has."""
    run_id = record(tmp_path, monkeypatch, RETURNED,
                    extra=("--focus", "prog:build"))
    trace = open_trace(run_id)
    build_f = next(f for f in trace.frames()
                   if trace.code(f.code_id).qualname == "build")

    assert cli.main(["flow", run_id, "--object", "build:return"]) == 0
    out = capsys.readouterr().out
    assert f"spanned by f{build_f.id} across e" in out
    assert f"..e{build_f.return_event_id}:" in out       # through the RETURN
    assert "0 unwitnessed" in out


def test_flow_object_treats_a_frame_that_never_closed_as_open(
        tmp_path, monkeypatch, capsys):
    """A frame with no close at all was open at every event after its call --
    the recording simply stopped first. Ending it early would invent a gap."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "hold", 1)
    obj = {"k": "map", "type": "dict", "len": 1, "oid": 999, "sample": []}
    first = w.add_event(0, 1, "CALL", None, c, 1, {"args": {"cfg": obj}})
    fid = w.open_frame(None, c, first, 0, 1)          # never closed
    last = w.add_event(0, 1, "CALL", None, c, 2, {"args": {"cfg": obj}})
    # frames are flushed before events, so an unclean death can leave a frame
    # whose CALL row never landed: it must be stepped over, not crashed on
    w.open_frame(None, c, 9999, 0, 1)
    w.add_event(0, 1, "CALL", None, None, 3, {"args": {}})   # no code object
    w.close()

    assert cli.main(["flow", "20260101-000000-abcdef", "--object",
                     f"e{first}:cfg"]) == 0
    out = capsys.readouterr().out
    assert f"spanned by f{fid} across e{first}..e{last}" in out
    assert "has no line capture" in out              # and says why it is weak
    assert "0 unwitnessed" in out


def test_bindings_end_at_a_rebinding_and_at_a_del(tmp_path, monkeypatch):
    """A frame's local witnesses continuity only while it still holds the
    address. Carrying the binding to the end of the frame would let a name
    that was reassigned -- or deleted -- vouch for an address it no longer
    holds, which is precisely the window in which CPython reuses one."""
    run_id = record(tmp_path, monkeypatch, REBIND,
                    extra=("--focus", "prog:main"))
    trace = open_trace(run_id)
    idx = flow_cmd.Index(trace)
    made = [e.payload["value"] for e in trace.events(kind="RETURN")
            if (e.payload or {}).get("value", {}).get("k") == "map"]
    assert len(made) == 2 and made[0]["oid"] != made[1]["oid"], (
        "the two dicts overlap in life, so they cannot share an address")

    lines = trace.events(kind="LINE")
    rebind = next(e for e in lines
                  if e.payload["deltas"].get("box", {}).get("oid")
                  == made[1]["oid"])
    unbind = next(e for e in lines
                  if "box" in (e.payload or {}).get("unbound", []))
    main_f = next(f for f in trace.frames()
                  if trace.code(f.code_id).qualname == "main")

    for cap, ends_at in ((made[0], rebind.id), (made[1], unbind.id)):
        target = flow_cmd.ObjTarget(cap["oid"], cap["type"])
        held = [b for b in flow_cmd.bindings(idx, target) if b.name == "box"]
        assert len(held) == 1, held
        assert held[0].end == ends_at
        assert held[0].end < main_f.return_event_id      # not the frame's end
