"""`flow --value`: every capture that compares EQUAL to a literal.

Equality over CAPTURED values, which is not the same as equality over the
program's values: a capture can be clipped or capped, a local that was never
recorded is not searchable at all, and none of it says one sighting produced
another. Every test here pins a claim the command makes about that boundary,
because the failure mode is not a wrong answer -- it is a confident silence.

The identity half of `flow` lives in `test_flow_identity.py`, split off at
this file's 800-line ceiling along the seam the material has.
"""
import shlex

from sensorium import cli
from sensorium.exit import NEGATIVE, UNSETTLED
from sensorium.query import flow_cmd
from tests.programs import (ALIAS, GRAMS, flow_rows, flow_shown_ids,
                            open_trace, record, synthetic)

# `payload` is 12 long (sample cap is 8); `deep` and `nest` both go past the
# depth cap of 3, in a dict chain and a list chain. The capture of each is
# marked truncated and the 1800 inside is never recorded at all -- and the
# capped node carries no `sample` key whatsoever, in either shape.
TRUNCATED = """
def widen(payload):
    return len(payload)

def descend(deep):
    return deep["a"]["b"]["c"]["d"]

def dig(nest):
    return nest[0][0][0][0]

def main():
    widen([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1800, 11])
    descend({"a": {"b": {"c": {"d": 1800}}}})
    dig([[[[1800]]]])

if __name__ == "__main__":
    main()
"""
# `del` unbinds a local: the LINE event after it carries `unbound: [token]`
# and no delta for it. That event must never be listed as a sighting of the
# value the name used to hold.
DEL_LOCAL = """
def watched():
    token = "sk-live-42"
    box = {"token": token}
    del token
    return box

def main():
    print(watched())

if __name__ == "__main__":
    main()
"""

FLAGS = """
def check(flag, count):
    return flag, count

def main():
    check(True, 1)
    check(False, 0)

if __name__ == "__main__":
    main()
"""

ODD_KEYS = """
def load(cfg):
    return cfg["max-weight"]

def main():
    load({"max-weight": 1800, 7: "seven"})

if __name__ == "__main__":
    main()
"""

BOOM = """
def risky(tag):
    raise ValueError(tag)

def main():
    try:
        risky("boom")
    except ValueError:
        pass

if __name__ == "__main__":
    main()
"""

# -- --value ---------------------------------------------------------------
def test_flow_value_traces_a_number_through_calls(tmp_path, monkeypatch,
                                                 capsys):
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    out = capsys.readouterr().out
    assert "item_weight -> 1800" in out
    assert "shipping_cost(weight_kg=1800)" in out
    assert "sightings:" in out and "not true dataflow" in out
    assert "[return]" in out and "[arg weight_kg]" in out


def test_flow_value_labels_where_inside_a_container_it_matched(
        tmp_path, monkeypatch, capsys):
    """A sighting inside a captured container has to say WHERE inside it --
    "the call got 1800 somewhere" is not an answer."""
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    out = capsys.readouterr().out
    assert "[arg items[1].grams]" in out          # list index, then dict key
    assert "[arg item.grams]" in out


def test_flow_value_reports_the_role_of_every_hit_on_one_event(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, ALIAS, extra=("--focus", "prog"))
    assert cli.main(["flow", run_id, "--value", "1"]) == 0
    out = capsys.readouterr().out
    # main's last LINE event shows both `prod` and `sand` at timeout 1
    assert "[local prod.timeout, local sand.timeout]" in out


def test_flow_value_keeps_bools_and_numbers_apart(tmp_path, monkeypatch,
                                                  capsys):
    """`True == 1` in Python. A trace where both were recorded must not
    report one as a sighting of the other."""
    run_id = record(tmp_path, monkeypatch, FLAGS)
    assert cli.main(["flow", run_id, "--value", "True"]) == 0
    out = capsys.readouterr().out
    assert "check(flag=True, count=1)" in out
    assert "[arg flag]" in out and "[arg count]" not in out

    assert cli.main(["flow", run_id, "--value", "1"]) == 0
    out = capsys.readouterr().out
    assert "[arg count]" in out and "[arg flag]" not in out


def test_flow_value_parses_none_and_quoted_strings(tmp_path, monkeypatch,
                                                   capsys):
    assert flow_cmd.parse_literal("None") is None
    assert flow_cmd.parse_literal("1800") == 1800
    assert flow_cmd.parse_literal("4.5") == 4.5
    assert flow_cmd.parse_literal("True") is True
    assert flow_cmd.parse_literal("False") is False
    assert flow_cmd.parse_literal("mug") == "mug"
    # digits are a number unless quoted -- otherwise a string of digits is
    # unsearchable
    assert flow_cmd.parse_literal("'1800'") == "1800"
    assert flow_cmd.parse_literal('"1800"') == "1800"
    # words float() happens to accept are NOT numbers here
    assert flow_cmd.parse_literal("nan") == "nan"
    assert flow_cmd.parse_literal("inf") == "inf"
    assert flow_cmd.parse_literal("infinity") == "infinity"
    # and a malformed number is searched as the string it actually is
    assert flow_cmd.parse_literal("1_.") == "1_."

    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "mug"]) == 0
    out = capsys.readouterr().out
    assert "[arg items[0].name]" in out
    assert "(str)" in out


def test_flow_value_none_matches_only_none(tmp_path, monkeypatch, capsys):
    """None matches None and nothing else -- asserted where the claim lives.

    The run id is pinned to one whose TIMESTAMP contains 1800. `flow`'s
    header names the run, so a whole-output `"1800" not in out` was a claim
    about the header as much as about the rows, and failed whenever a real
    recording happened to be made at 18:00:00-18:00:59 or at HH:18:00-09 --
    about 300 seconds of every day. Pinning the id makes that collision
    permanent rather than occasional, and the assertion moves to the rows,
    which is what "matches only None" is about.
    """
    run_id = record(tmp_path, monkeypatch, GRAMS,
                    extra=["--run-id", "20260101-180000-abcdef"])
    assert cli.main(["flow", run_id, "--value", "None"]) == 0
    out = capsys.readouterr().out
    assert "flow of None (NoneType)" in out
    assert "main -> None" in out and "[return]" in out
    assert "1800" in run_id and run_id in out    # the collision, pinned
    rows = "\n".join(ln for ln in out.splitlines() if run_id not in ln)
    assert "1800" not in rows and "-> 5569.0" not in rows


def test_flow_value_labels_keys_that_are_not_identifiers(
        tmp_path, monkeypatch, capsys):
    """`cfg.max-weight` would be a lie about the shape of the key. A key that
    is not a plain name is rendered as a subscript instead."""
    run_id = record(tmp_path, monkeypatch, ODD_KEYS)
    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    assert "[arg cfg['max-weight']]" in capsys.readouterr().out

    assert cli.main(["flow", run_id, "--value", "seven"]) == 0
    assert "[arg cfg[7]]" in capsys.readouterr().out


def test_find_in_value_reports_paths_and_never_matches_a_clipped_string():
    """The exported search over one capture. A clipped string is a strict
    prefix of the real one, so the real string is longer than -- and so not
    equal to -- whatever it is compared with; reporting it as a hit would be
    a false equality claim."""
    cap = {"k": "map", "type": "dict", "len": 2, "oid": 1, "sample": [
        [{"k": "str", "v": "grams"}, {"k": "num", "v": 1800}],
        [{"k": "str", "v": "rows"},
         {"k": "seq", "type": "list", "len": 2, "oid": 2, "sample": [
             {"k": "num", "v": 1800}, {"k": "none"}]}]]}
    assert flow_cmd.find_in_value(cap, 1800) == [".grams", ".rows[0]"]
    assert flow_cmd.find_in_value(cap, None) == [".rows[1]"]
    assert flow_cmd.find_in_value(cap, "grams") == ["[key 0]"]
    assert flow_cmd.find_in_value(cap, 1800, "arg cfg") == [
        "arg cfg.grams", "arg cfg.rows[0]"]

    clipped = {"k": "str", "v": "abc", "trunc": True}
    assert flow_cmd.matches(clipped, "abc") is False
    assert flow_cmd.matches({"k": "str", "v": "abc"}, "abc") is True


def test_flow_does_not_search_exception_payloads(tmp_path, monkeypatch,
                                                 capsys):
    """A RAISE payload holds a message, not a captured value. Listing it as a
    sighting of the string would claim the exception *carried* that value as
    data, which the trace does not record."""
    run_id = record(tmp_path, monkeypatch, BOOM)
    trace = open_trace(run_id)
    raises = trace.events(kind="RAISE")
    assert raises and raises[0].payload["exc"]["msg"] == "boom"

    assert cli.main(["flow", run_id, "--value", "'boom'"]) == 0
    out = capsys.readouterr().out
    assert "[arg tag]" in out                        # the argument is a hit
    assert raises[0].id not in flow_shown_ids(out)       # the RAISE is not


def test_flow_value_says_what_it_searched_when_nothing_matched(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "999999"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "sightings: 0" in out
    assert "capture(s) searched" in out
    assert "CALL args, RETURN values and LINE local deltas" in out


def test_flow_value_admits_the_run_captured_no_locals(tmp_path, monkeypatch,
                                                      capsys):
    """Recorded without --focus, a value that only ever lived in a local is
    not in the trace at all. Silence there reads as "it never existed"."""
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    out = capsys.readouterr().out
    assert "no LINE events" in out and "--focus" in out

    focused = record(tmp_path / "b", monkeypatch, GRAMS,
                     extra=("--focus", "prog"))
    assert cli.main(["flow", focused, "--value", "1800"]) == 0
    assert "no LINE events" not in capsys.readouterr().out


def test_flow_value_owns_up_to_captures_it_could_not_search(
        tmp_path, monkeypatch, capsys):
    """Over-cap and depth-capped containers hold values that were never
    recorded. Reporting "0 sightings" over them without saying so claims the
    value is absent from the RUN when it is only absent from the CAPTURE."""
    run_id = record(tmp_path, monkeypatch, TRUNCATED)
    trace = open_trace(run_id)
    caps = [e.payload["args"] for e in trace.events(kind="CALL")
            if (e.payload or {}).get("args")]
    wide = next(a["payload"] for a in caps if "payload" in a)
    deep = next(a["deep"] for a in caps if "deep" in a)
    nest = next(a["nest"] for a in caps if "nest" in a)
    assert wide["trunc"] and len(wide["sample"]) == 8    # 1800 is at index 10
    node = deep
    while "sample" in node:                             # down to the cap
        node = node["sample"][0][1]
    assert node["trunc"] and node["k"] == "map"         # and no sample at all
    node = nest
    while "sample" in node:
        node = node["sample"][0]
    assert node["trunc"] and node["k"] == "seq"         # the list shape too

    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    out = capsys.readouterr().out
    # the only sightings are the value coming back out; no container's
    # unrecorded interior is claimed either way
    assert "sightings: 2 event(s)" in out
    assert "descend -> 1800" in out and "dig -> 1800" in out
    assert "[arg payload" not in out and "[arg deep" not in out
    assert "[arg nest" not in out
    assert "3 of" in out and "truncated" in out          # wide, deep, nest
    assert "the parts not recorded could not be compared" in out


def test_flow_limit_withholds_nothing_silently(tmp_path, monkeypatch, capsys):
    """The continuation has to be a runnable command, and paging through it
    must reproduce the unclipped list exactly -- no gap, no repeat."""
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    full = flow_rows(capsys.readouterr().out)
    assert len(full) > 2

    pages: list[str] = []
    argv = ["flow", run_id, "--value", "1800", "--limit", "2"]
    for n in range(10):                       # guard: never loop forever
        assert cli.main(argv) == 0
        out = capsys.readouterr().out
        # the total never shrinks to the size of the page it printed
        assert f"sightings: {len(full) - 2 * n} event(s)" in out
        if n:
            assert f"{2 * n} earlier sighting(s) skipped by --after" in out
        pages += flow_rows(out)
        tail = out.strip().splitlines()[-1]
        if "continue with: " not in tail:
            break
        hint = tail.split("continue with: ", 1)[1]
        assert "eN" not in hint and "..." not in hint
        argv = shlex.split(hint)
        assert argv[0] == "sensorium"
        argv = argv[1:]
    assert pages == full


def test_flow_rejects_a_nonpositive_limit(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "1800", "--limit", "0"]) == 2
    assert "--limit" in capsys.readouterr().out


def test_flow_skips_locals_that_went_out_of_scope(tmp_path, monkeypatch,
                                                  capsys):
    """A LINE event carrying `unbound: [token]` records a name going AWAY.
    Listing it as a sighting claims a live binding that had just ended."""
    run_id = record(tmp_path, monkeypatch, DEL_LOCAL,
                    extra=("--focus", "prog:watched"))
    trace = open_trace(run_id)
    gone = [e for e in trace.events(kind="LINE")
            if "token" in (e.payload or {}).get("unbound", [])]
    assert len(gone) == 1, "the fixture must actually unbind a local"

    assert cli.main(["flow", run_id, "--value", "'sk-live-42'"]) == 0
    out = capsys.readouterr().out
    assert "[local token]" in out                    # it was live earlier
    assert gone[0].id not in flow_shown_ids(out)     # ...but not at the unbind


def test_flow_flags_an_incomplete_run(tmp_path, monkeypatch, capsys):
    """A run whose recording never finalized may simply stop mid-program, so
    an empty result is not evidence the value never appeared."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "add", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["flow", "20260101-000000-abcdef",
                     "--value", "1"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "sightings: 0" in out


def test_flow_refuses_a_trace_that_declares_no_line_events(tmp_path, monkeypatch, capsys):
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"line": False, "object_identity": False})
    w.close()
    assert cli.main(["flow", "20260101-000000-abcdef",
                     "--value", "1"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "flow needs line" in out and "sensorium-rt 0.0" in out
    assert cli.main(["flow", "20260101-000000-abcdef",
                     "--object", "0x1:int"]) == UNSETTLED
    assert "flow --object needs object_identity" in capsys.readouterr().out
