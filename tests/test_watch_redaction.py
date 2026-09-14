"""`watch` over a value the redaction rule took: what it refuses to compare.

A name-redacted capture holds a MARKER where the value was. Every kind's
marker text is the same five characters, so a predicate applied to it would
be applied to `<redacted>` -- and `token == '<redacted>'` would come back
SATISFIED at every site where the rule fired, which is a hit reported about
a value nobody recorded. Worse, it would be reported about EVERY secret
alike: two different tokens redact to one string, so one predicate would
"hold" across values that are not equal to each other.

So a taken value resolves to a marker of its own (`expr.REDACTED`) and every
path into a name refuses it by name, with the reason travelling on the
exception the way every other uncheckable site's does. The site lands in the
`unavailable` bucket, is counted in the tally, and -- when it is the only
kind of site there is -- reaches the verdict this command keeps for a
question it could not answer at all: NOTHING WAS CHECKED, exit 3.

A CONTENT hit is the opposite case and is deliberately NOT refused. The rule
replaced a span inside a text the recorder kept; what the trace holds IS the
text, so `url == 'postgres://u:<redacted>@h/db'` compares the characters the
trace holds and answers. Refusing it would cost a reader an answer the
recording can give.

The traces are hand-built: what is under test is how one capture SHAPE is
read, and recording a program that happens to hold a secret would be a test
of whoever's shell ran it (`tests/test_record_redaction.py` says why).
"""
import pytest

from sensorium import cli
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from sensorium.query import watch_cmd
from sensorium.query.expr import (REDACTED, REDACTED_REASON, NotCaptured,
                                  compile_expr, resolve)
from sensorium.query.watch_cmd import _render, evaluate, sites_for
from tests.flow_programs import open_trace
from tests.helpers import finalize_synthetic
from tests.programs import synthetic

RUN = "20260101-000000-abcdef"
AT = "prog:leak"

#: What the writer leaves behind in the field it took (`redact.REDACTED`).
STORED = "<redacted>"
URL = "postgres://u:<redacted>@h/db"


def taken(digest="0123456789abcdef") -> dict:
    """A `str` capture the NAME rule took whole."""
    return {"k": "str", "v": STORED, "redacted": {"by": "name",
                                                  "digest": digest}}


def content_hit() -> dict:
    """A `str` capture the CONTENT rule replaced a span inside."""
    return {"k": "str", "v": URL, "redacted": {"by": "content",
                                               "digest": None}}


def trace_with(tmp_path, monkeypatch, args: dict, deltas: dict | None = None):
    """One frame of `prog:leak`: a CALL carrying `args`, and -- when
    `deltas` is given -- one LINE carrying them, which is a second site."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "leak", 1)
    call = w.add_event(0, 1, "CALL", None, c, 1, {"args": args})
    fid = w.open_frame(None, c, call, 0, 1)
    if deltas is not None:
        w.add_event(0, 1, "LINE", fid, c, 2, {"deltas": deltas})
    ret = w.add_event(0, 1, "RETURN", fid, c, None, {"value": {"k": "none"}})
    w.close_frame(fid, ret, "return")
    finalize_synthetic(w, run_id=RUN)
    w.close()
    return open_trace(RUN)


def one_site(trace, names):
    sites = sites_for(trace, [c.id for c in trace.codes()], names)
    return sites[0]


def verdict_lines(out: str) -> list[str]:
    """The verdict line and the one under it -- never a substring match
    over the whole screen: the caveated verdict contains the clean one's
    closing words (`tests/test_watch_verdict.py` measured that)."""
    lines = out.splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.startswith("verdict:"))
    return lines[i:i + 2]


# -- a taken value is not a value ------------------------------------------
def test_a_taken_capture_resolves_to_its_own_marker(tmp_path, monkeypatch):
    """Before the kind dispatch, so it cannot be read as the kind's value:
    a taken `num` holds the marker TEXT in `v`, and the `num` arm would
    hand the predicate the string `<redacted>` as if it were a number."""
    assert resolve(taken()) is REDACTED
    assert resolve({"k": "num", "v": STORED,
                    "redacted": {"by": "name", "digest": None}}) is REDACTED
    assert resolve({"k": "seq", "type": "list", "len": 3, "oid": 1,
                    "redacted": {"by": "name", "digest": None}}) is REDACTED


def test_every_path_into_a_taken_name_refuses_it_with_one_reason():
    """Three ways to reach a name -- the bare name, `len(name)` and
    `literal in name` -- and one reason, so a reader who moves from one to
    the next is told the same thing rather than three different things."""
    env = {"token": REDACTED}
    for src in ("token == 'x'", "len(token) > 3", "'ab' in token"):
        with pytest.raises(NotCaptured) as caught:
            compile_expr(src).eval(env)
        assert caught.value.name == "token"
        assert caught.value.reason == REDACTED_REASON


def test_the_site_lands_in_the_unavailable_bucket_by_name(
        tmp_path, monkeypatch):
    """Counted, not skipped: `sites = evaluated + not-captured + errors` is
    the arithmetic this command prints, and a site quietly dropped would
    make that line false."""
    trace = trace_with(tmp_path, monkeypatch, {"token": taken()})
    expr = compile_expr("token == 'x'")
    out = evaluate(sites_for(trace, [c.id for c in trace.codes()],
                             expr.names), expr)
    assert out.unavailable == {("token", REDACTED_REASON): 1}
    assert out.evaluated == 0 and not out.errors


def test_the_state_line_names_the_rule_rather_than_printing_the_marker(
        tmp_path, monkeypatch):
    """`fmt_value` would print `<redacted #01234567>` here, which is the
    right answer for a listing and the wrong one for a state line: what a
    predicate's state must say is that there was nothing to compare."""
    trace = trace_with(tmp_path, monkeypatch, {"token": taken()})
    site = one_site(trace, {"token"})
    assert _render("token", site) == "<redacted; no comparable value>"


# -- the verdict, and the status a caller branches on ----------------------
def test_a_predicate_that_meets_only_taken_values_checked_nothing(
        tmp_path, monkeypatch, capsys):
    """The whole point. `hits: 0` here means "could not evaluate", and the
    status says so -- a 1 would be the trace answering "no" about a
    question it never got to ask."""
    trace_with(tmp_path, monkeypatch, {"token": taken()})
    assert cli.main(["watch", RUN, "--at", AT,
                     "--expr", "token == 'x'"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "sites: 1   evaluated: 0   hits: 0   not-captured: 1" in out
    assert verdict_lines(out) == [
        "verdict: NOTHING WAS CHECKED -- the predicate could not be "
        "evaluated at any of the 1 recorded site(s)",
        "  'hits: 0' here means 'could not evaluate', NOT 'the invariant "
        "held'"]
    assert f"token: {REDACTED_REASON}   [1 site(s)]" in out


def test_the_guidance_says_the_rule_ran_at_the_recorder(
        tmp_path, monkeypatch, capsys):
    """Without an arm of its own this reason falls through to "recorded at
    other sites in these frames, so this is scope, not capture depth",
    which sends a reader to look for a scope bug that is not there. The
    rule runs before anything reaches disk; no re-reading of this trace
    changes it."""
    trace_with(tmp_path, monkeypatch, {"token": taken()})
    cli.main(["watch", RUN, "--at", AT, "--expr", "token == 'x'"])
    out = capsys.readouterr().out
    assert "<redacted; no comparable value>" in out
    assert "before anything reached disk" in out
    assert "this is scope, not capture depth" not in out


def test_one_taken_site_beside_one_checked_site_is_still_a_no(
        tmp_path, monkeypatch, capsys):
    """A partially checked run is not a fourth verdict class: the trace
    answered "no" about the site it could check, and the site it could not
    is carried in the caveat rather than in the status (plan X7)."""
    trace_with(tmp_path, monkeypatch, {"token": taken()},
               deltas={"token": {"k": "str", "v": "y"}})
    assert cli.main(["watch", RUN, "--at", AT,
                     "--expr", "token == 'x'"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "sites: 2   evaluated: 1   hits: 0   not-captured: 1" in out
    assert verdict_lines(out) == [
        "verdict: not satisfied at any of the 1 site(s) that could be "
        "evaluated -- but 1 of 2 recorded site(s) could NOT be evaluated,",
        "  so this is not a claim that the invariant held"]


# -- a content hit is still an answerable value ----------------------------
def test_a_content_hit_is_compared_as_the_text_the_trace_holds(
        tmp_path, monkeypatch, capsys):
    """The rule took a span, not the value. The host and the database are
    still recorded, and a predicate over them is answered -- refusing here
    would cost a reader an answer this recording can give."""
    assert resolve(content_hit()) == URL
    trace_with(tmp_path, monkeypatch, {"url": content_hit()})
    assert cli.main(["watch", RUN, "--at", AT,
                     "--expr", f"url == '{URL}'"]) == ANSWERED
    out = capsys.readouterr().out
    assert "sites: 1   evaluated: 1   hits: 1   not-captured: 0" in out
    assert f"state: url='{URL}'" in out


def test_the_marker_is_not_a_value_a_predicate_can_meet(
        tmp_path, monkeypatch, capsys):
    """The failure this exists to prevent, stated as its own case: asking
    for the marker text does not find a taken value. Two different secrets
    redact to one string, so a hit here would "hold" across values that are
    not equal to each other."""
    trace_with(tmp_path, monkeypatch, {"token": taken()})
    assert cli.main(["watch", RUN, "--at", AT,
                     "--expr", f"token == '{STORED}'"]) == UNSETTLED
    assert "hits: 0" in capsys.readouterr().out


def test_the_reason_is_one_sentence_the_whole_reader_shares():
    """Spelled once, in `expr`, because `watch` prints it and the tests
    above assert it: a second copy is how the two drift apart."""
    assert REDACTED_REASON == "redacted by rule v1; no comparable value"
    assert watch_cmd.REDACTED_REASON is REDACTED_REASON
