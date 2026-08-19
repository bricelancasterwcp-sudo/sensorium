"""`watch`: a predicate at every recorded site, and how close the run came.

Every test here is built from a REAL recorded trace, because the two things
that can go wrong are both properties of real recordings and neither shows up
against a hand-built payload:

1. State is folded FORWARD. A local that goes out of scope produces no delta,
   so a fold that reads `deltas` alone keeps a dead binding alive at its last
   value for the rest of the frame -- and `watch` then reports a HIT on a
   variable that no longer exists. `del` does it; the implicit unbind that
   ends every `except E as e:` block does it far more often. The tracer emits
   a sibling `unbound` list precisely so this command can pop them, and two
   tests below pin exactly that, each asserting the shape of the recorded
   event BEFORE asserting on output so neither can pass vacuously.

2. A site the predicate could not be evaluated at is not a site where the
   predicate was False. Silence there turns "I could not check" into "the
   invariant held", which is the worst answer this command could give. So the
   tally line is asserted alongside every verdict assertion: a verdict-text
   assertion alone does not catch a tally that has quietly changed.
"""
import shlex

from sensorium import cli
from sensorium.store import db
from sensorium.store.reader import Trace
from tests.helpers import record_script
from tests.programs import open_trace, synthetic
from tests.watch_programs import (BUFFER, CARRIER, CLIP, HANDLER, KEEP,
                                  LOOPDEL, MIXED, RECURSE)


def _rec(tmp_path, monkeypatch, src=BUFFER, extra=()):
    run_id, _trace, r = record_script(tmp_path, src, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def _line_events(run_id, qualname):
    t = open_trace(run_id)
    return [e for e in t.events(kind="LINE")
            if t.code(e.code_id).qualname == qualname]


def _hit_ids(out: str) -> list[int]:
    return [int(ln.split("  HIT   e", 1)[1].split(" ", 1)[0])
            for ln in out.splitlines() if ln.startswith("  HIT   e")]


# -- the brief's four ------------------------------------------------------
def test_watch_near_miss_when_no_hits(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "hits: 0" in out
    assert "near-misses" in out and "margin 1:" in out and "used=99" in out
    # `fill` runs 5 times; `used` -- the length right after each fill -- takes
    # 40, 70, 85, 99, 69, so the high-water mark is 99 and the closest
    # approach to 100 is exactly 1. The other 14 sites are the CALL and the
    # lines before `used` exists.
    assert "sites: 19   evaluated: 5   hits: 0   not-captured: 14" in out
    assert "margin 1: " in out and "margin 15: " in out
    assert "margin 60: " in out


def test_watch_hits_reported_with_env(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 90"]) == 0
    out = capsys.readouterr().out
    assert "HIT" in out and "used=99" in out
    assert "sites: 19   evaluated: 5   hits: 1   not-captured: 14" in out
    assert "verdict: SATISFIED at 1 of the 5 site(s)" in out
    assert "near-misses" not in out


def test_watch_counts_not_captured_sites(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)           # no focus: no locals
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "not-captured: 5" in out                # 5 CALL sites lack `used`
    assert "refocus" in out
    assert "sites: 5   evaluated: 0   hits: 0   not-captured: 5" in out
    assert "NOTHING WAS CHECKED" in out


def test_watch_bad_expr_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "__import__('os')"]) == 2
    assert "only call allowed" in capsys.readouterr().out


# -- the unbind contract ---------------------------------------------------
def test_watch_drops_a_local_unbound_at_the_end_of_an_except_handler(
        tmp_path, monkeypatch, capsys):
    """The case `unbound` exists for. `e` is rebound to an int inside the
    handler, so it really does satisfy `e > 3` for two sites -- and really
    does vanish at the third. Folding deltas alone would report three hits,
    two of them about a name that no longer exists."""
    run_id = _rec(tmp_path, monkeypatch, HANDLER,
                  extra=("--focus", "prog:stage"))
    lines = _line_events(run_id, "stage")
    # Precondition: the recording really has the shape this test is about.
    bound = [e for e in lines if (e.payload["deltas"].get("e") or {}
                                  ).get("v") == 5]
    unbinds = [e for e in lines if "e" in e.payload.get("unbound", [])]
    assert len(bound) == 1 and len(unbinds) == 3
    after = [e for e in lines if e.id > bound[0].id]
    assert len(after) >= 2                      # sites that outlive `e`

    assert cli.main(["watch", run_id, "--at", "prog:stage",
                     "--expr", "e > 3"]) == 0
    out = capsys.readouterr().out
    assert _hit_ids(out) == [bound[0].id]       # never the sites after it
    assert "sites: 21   evaluated: 3   hits: 1   not-captured: 18" in out
    # The 3 sites where `e` is the live ValueError are in scope but have no
    # comparable value -- a different fact from the 15 where it is not bound,
    # and one that no amount of refocusing would change.
    assert "not in scope at this site" in out
    assert "no comparable value" in out
    assert "refocusing cannot change that" in out


def test_watch_evaluates_a_line_whose_only_change_is_an_unbind(
        tmp_path, monkeypatch, capsys):
    """`del peak` records deltas={} with unbound=["peak"]. That event is a
    site: skipping it would silently drop both the unbind and the count."""
    run_id = _rec(tmp_path, monkeypatch, LOOPDEL,
                  extra=("--focus", "prog:scan"))
    lines = _line_events(run_id, "scan")
    pure = [e for e in lines
            if not e.payload["deltas"]
            and e.payload.get("unbound") == ["peak"]]
    assert len(pure) == 3                       # precondition, per pass

    assert cli.main(["watch", run_id, "--at", "prog:scan",
                     "--expr", "peak > 5"]) == 0
    out = capsys.readouterr().out
    assert "sites: 15   evaluated: 6   hits: 4   not-captured: 9" in out
    # peak is 3, 6, 9 across the three passes and survives exactly two sites
    # each time; without the unbind fold it would still be 6 and 9 at the
    # five sites where the name is gone.
    assert len(_hit_ids(out)) == 4
    assert all(i < pure[-1].id for i in _hit_ids(out))
    assert not set(_hit_ids(out)) & {e.id for e in pure}


# -- 0 hits must never read as "the invariant held" ------------------------
def _verdict(out: str) -> list[str]:
    """The verdict line and the line under it, exactly.

    NOT a substring match against the whole of stdout: the caveated verdict
    contains the clean verdict's closing words, so `"not a claim that the
    invariant held" in out` cannot tell which branch was taken. Measured --
    replacing the clean branch's whole second line with "(recorded sites
    only)" left the entire suite green. Five non-biting tests on this
    project shared exactly that shape.
    """
    lines = out.splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.startswith("verdict:"))
    return lines[i:i + 2]


def test_watch_zero_hits_with_unchecked_sites_refuses_the_conclusion(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "sites: 19   evaluated: 5   hits: 0   not-captured: 14" in out
    assert _verdict(out) == [
        "verdict: not satisfied at any of the 5 site(s) that could be "
        "evaluated -- but 14 of 19 recorded site(s) could NOT be evaluated,",
        "  so this is not a claim that the invariant held"]


def test_watch_zero_hits_with_every_site_checked_still_scopes_the_claim(
        tmp_path, monkeypatch, capsys):
    """Even a fully evaluated run only ever saw what was recorded.

    This is the CLEAN branch -- the one with no caveat attached -- so its
    own second line is the only thing standing between `hits: 0` and "the
    invariant held". The fixture used to be MIXED, which yields `errors: 1`
    and therefore takes the CAVEATED branch: the test was named for one
    branch and passed on the other's copy of the words.
    """
    run_id = _rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 9000"]) == 0
    out = capsys.readouterr().out
    assert "sites: 4   evaluated: 4   hits: 0   not-captured: 0   errors: 0" \
        in out
    assert _verdict(out) == [
        "verdict: not satisfied at any of the 4 recorded site(s), every one "
        "of which was evaluated",
        "  that is a fact about what was RECORDED, not a claim that the "
        "invariant held: only recorded sites were checked"]


def test_watch_verdict_says_which_sites_errored_rather_than_summing_them(
        tmp_path, monkeypatch, capsys):
    """The caveated branch reached through the ERRORS bucket rather than the
    not-captured one -- the shape the old fixture above was actually
    testing, kept here where its name matches its branch."""
    run_id = _rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 9000"]) == 0
    out = capsys.readouterr().out
    assert "sites: 2   evaluated: 1   hits: 0   not-captured: 0   errors: 1" \
        in out                                       # "five" > 9000
    assert _verdict(out) == [
        "verdict: not satisfied at any of the 1 site(s) that could be "
        "evaluated -- but 1 of 2 recorded site(s) raised while the predicate "
        "was applied,",
        "  so this is not a claim that the invariant held"]


def test_watch_warns_when_a_predicate_name_was_never_recorded_anywhere(
        tmp_path, monkeypatch, capsys):
    """The hole short-circuiting leaves. `ghost` is not in the program, let
    alone the trace, so `and` absorbs it at every site -- and without the
    warning this run reports `not-captured: 0` and the cleanest verdict the
    command has, never once naming `ghost`. A typo'd conjunct would turn an
    invariant check into a tautology that reads as maximally reassuring."""
    run_id = _rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 1000 and ghost > 1"]) == 0
    out = capsys.readouterr().out
    # Every site really did evaluate: nothing else in the output is shouting.
    assert "sites: 4   evaluated: 4   hits: 0   not-captured: 0   errors: 0" \
        in out
    assert "NEVER RECORDED: 'ghost'" in out
    assert "decided WITHOUT it" in out
    # ...and the verdict must not be the clean one. Pinned as the verdict's
    # own two lines: the clean branch's closing words appear in both.
    assert _verdict(out) == [
        "verdict: not satisfied at any of the 4 site(s) that could be "
        "evaluated -- but the predicate was decided WITHOUT 'ghost',",
        "  so this is not a claim that the invariant held"]
    # The banner sits ABOVE the verdict: the verdict cannot be read past it.
    assert out.index("NEVER RECORDED") < out.index("verdict:")


def test_watch_does_not_warn_when_every_predicate_name_was_recorded(
        tmp_path, monkeypatch, capsys):
    """The other direction: the warning must be about the trace, not a
    reflex. Same program, same shape of predicate, all names present."""
    run_id = _rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 1000 and n > 2"]) == 0
    out = capsys.readouterr().out
    assert "sites: 4   evaluated: 4   hits: 0   not-captured: 0   errors: 0" \
        in out
    assert "NEVER RECORDED" not in out
    assert "decided WITHOUT" not in out
    assert _verdict(out) == [
        "verdict: not satisfied at any of the 4 recorded site(s), every one "
        "of which was evaluated",
        "  that is a fact about what was RECORDED, not a claim that the "
        "invariant held: only recorded sites were checked"]


def test_watch_warns_about_a_phantom_name_that_rode_along_with_a_real_hit(
        tmp_path, monkeypatch, capsys):
    """The `or` mirror. It is milder only by accident -- a hit renders a
    state line naming `ghost` -- so it gets the same banner and the same
    refusal to call the verdict complete."""
    run_id = _rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 2 or ghost > 1"]) == 0
    out = capsys.readouterr().out
    # `or` only reaches `ghost` where `n` failed, so 2 sites do land in the
    # not-captured bucket -- which is exactly why this mirror is milder by
    # accident, and why it is not relied on. The banner fires regardless.
    assert "sites: 4   evaluated: 2   hits: 2   not-captured: 2   errors: 0" \
        in out
    assert "NEVER RECORDED: 'ghost'" in out
    assert "verdict: SATISFIED at 2 of the 2 site(s)" in out
    assert "do not answer the whole predicate" in out
    assert "ghost=<not in scope>" in out


def test_watch_phantom_caveat_survives_a_run_where_every_site_hit(
        tmp_path, monkeypatch, capsys):
    """Every site hits on the left of the `or`, so there is nothing else for
    the verdict to hedge about -- and the phantom clause still has to lead.
    This is the hit-path shape with no other caveat to hide behind."""
    run_id = _rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 0 or ghost > 1"]) == 0
    out = capsys.readouterr().out
    assert "sites: 4   evaluated: 4   hits: 4   not-captured: 0   errors: 0" \
        in out
    assert "NEVER RECORDED: 'ghost'" in out
    assert "verdict: SATISFIED at 4 of the 4 site(s)" in out
    assert "but the predicate was decided WITHOUT 'ghost', so these hits do " \
        "not answer the whole predicate" in out
    assert out.count("ghost=<not in scope>") == 4      # on every HIT line
    assert "every one of which was evaluated" not in out


def test_watch_never_recorded_is_judged_over_the_run_not_the_after_page(
        tmp_path, monkeypatch, capsys):
    """`peak` IS recorded in these frames. A page that happens to contain
    none of its bindings must not call it a name the trace never held.

    The page is deliberately NON-empty: the last site is the `del peak` line,
    where `peak` is out of scope and so absent from that page's captures
    entirely. A page-scoped judgement calls it never-recorded there, which is
    a false statement about the run, and the site count proves the page was
    really examined rather than skipped."""
    run_id = _rec(tmp_path, monkeypatch, LOOPDEL,
                  extra=("--focus", "prog:scan"))
    lines = _line_events(run_id, "scan")
    last_bind = max(e.id for e in lines if "peak" in e.payload["deltas"])
    tail = [e for e in lines if e.id > last_bind]
    assert len(tail) == 2 and "peak" not in tail[-1].payload["deltas"]

    assert cli.main(["watch", run_id, "--at", "prog:scan", "--expr",
                     "peak > 5", "--after", f"e{tail[0].id}"]) == 0
    out = capsys.readouterr().out
    assert "sites: 1   evaluated: 0   hits: 0   not-captured: 1   errors: 0" \
        in out
    assert "NEVER RECORDED" not in out
    # ...and the guidance still reads it as the scope fact it is.
    assert "scope, not capture depth" in out


def test_watch_tally_line_accounts_for_every_site(tmp_path, monkeypatch,
                                                  capsys):
    """sites = evaluated + not-captured + errors, checkable on the line
    itself rather than trusted."""
    run_id = _rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 3"]) == 0
    out = capsys.readouterr().out
    line = [ln for ln in out.splitlines() if ln.startswith("sites: ")][0]
    got = dict(p.split(": ") for p in line.split("   "))
    assert int(got["sites"]) == (int(got["evaluated"])
                                 + int(got["not-captured"])
                                 + int(got["errors"]))
    assert got == {"sites": "2", "evaluated": "1", "hits": "1",
                   "not-captured": "0", "errors": "1"}


def test_watch_satisfied_verdict_names_the_sites_that_raised(
        tmp_path, monkeypatch, capsys):
    """A SATISFIED verdict quoting only `evaluated` hides the sites where
    the predicate could not be applied at all -- the 0-hit path says so, and
    the hit path has to as well."""
    run_id = _rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 3"]) == 0
    out = capsys.readouterr().out
    assert "verdict: SATISFIED at 1 of the 1 site(s) the predicate could be " \
        "evaluated at" in out
    assert "but 1 of 2 recorded site(s) raised while the predicate was " \
        "applied, so these are not necessarily every time it held" in out


def test_watch_satisfied_verdict_names_the_sites_it_could_not_check(
        tmp_path, monkeypatch, capsys):
    """The mirror of the phantom hole, arriving through the hit path: a
    confident SATISFIED sitting above 14 of 19 sites that went unchecked
    reads far cleaner than the evidence supports. The 0-hit path has always
    said so; this one used to name only the errors."""
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 30"]) == 0
    out = capsys.readouterr().out
    assert ("sites: 19   evaluated: 5   hits: 5   not-captured: 14   "
            "errors: 0") in out
    assert "verdict: SATISFIED at 5 of the 5 site(s)" in out
    assert "but 14 of 19 recorded site(s) could NOT be evaluated, so these " \
        "are not necessarily every time it held" in out


def test_watch_deeply_nested_expression_fails_once_on_the_command_line(
        tmp_path, monkeypatch, capsys):
    """`_validate` recurses per node and `ast.parse` builds trees far deeper
    than it survives, so this used to be a RecursionError traceback and a
    non-2 exit -- from the one command whose contract is that a bad
    expression fails once, here, before any site is read."""
    run_id = _rec(tmp_path, monkeypatch)
    deep = "x" + " + x" * 1000 + " > 1"
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", deep]) == 2
    out = capsys.readouterr().out
    assert "error: expression nests deeper than 50 levels" in out
    assert "Traceback" not in out


def test_watch_near_below_one_is_exit_2(tmp_path, monkeypatch, capsys):
    """Consistent with --limit, and for one more reason: near-misses are the
    answer when nothing hit, so a flag that silently suppresses them would
    make a run look clean without changing anything about the run."""
    run_id = _rec(tmp_path, monkeypatch)
    for bad in ("0", "-5"):
        assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                         "used > 1", "--near", bad]) == 2
    out = capsys.readouterr().out
    assert out.count("--near must be >= 1") == 2


def test_watch_nothing_checked_says_so_instead_of_reporting_zero_hits(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "verdict: NOTHING WAS CHECKED" in out
    assert "'could not evaluate', NOT 'the invariant held'" in out
    assert "not captured at 5 of 5 site(s)" in out


def test_watch_refocus_guidance_is_an_exact_runnable_command(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    hint = [ln for ln in out.splitlines() if "sensorium run" in ln][0]
    assert "--focus prog:fill -- prog.py" in hint
    assert "MODULE" not in hint and "QUALNAME" not in hint and "<" not in hint
    assert f"cd {tmp_path}" in hint


def test_watch_does_not_offer_refocus_when_the_name_is_merely_out_of_scope(
        tmp_path, monkeypatch, capsys):
    """`used` IS recorded in these frames, just not at every site. Telling a
    reader to refocus there sends them to re-record a run that already has
    the capture they need."""
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "sensorium run" not in out
    assert "scope, not capture depth" in out


# -- what the state beside a hit may claim ---------------------------------
def _state_of_first_hit(out: str) -> str:
    line = next(ln for ln in out.splitlines() if ln.startswith("  HIT   e"))
    return line.split("state: ", 1)[1]


def test_watch_prints_an_object_as_having_no_value_rather_than_a_repr(
        tmp_path, monkeypatch, capsys):
    """A hit's state line is read as "here is what the run held". An object
    was recorded as a type and an address, so printing anything that looks
    like its value there would be inventing evidence -- and the short-circuit
    that produced this hit is exactly the case where the name is displayed
    without ever having been compared."""
    run_id = _rec(tmp_path, monkeypatch, CARRIER,
                  extra=("--focus", "prog:stage"))

    assert cli.main(["watch", run_id, "--at", "prog:stage",
                     "--expr", "depth > 0 or box == 1"]) == 0
    state = _state_of_first_hit(capsys.readouterr().out)

    assert "box=<Box; no comparable value>" in state
    assert "depth=" in state                    # the name that decided it


def test_watch_prints_a_clipped_string_as_clipped_with_what_it_holds(
        tmp_path, monkeypatch, capsys):
    """The trace holds a PREFIX. Rendering it as the value would let a reader
    compare characters that were never recorded, so the state says how much
    of it survived instead of showing it."""
    run_id = _rec(tmp_path, monkeypatch, CARRIER,
                  extra=("--focus", "prog:stage"))

    assert cli.main(["watch", run_id, "--at", "prog:stage",
                     "--expr", "depth > 0 or blob == 'x'"]) == 0
    state = _state_of_first_hit(capsys.readouterr().out)

    held = int(state.split("blob=<clipped to ", 1)[1].split(" chars>", 1)[0])
    assert 0 < held < 250, f"claimed {held} of a 250-char string"


# -- reasons a site could not be evaluated ---------------------------------
def test_watch_refuses_a_truncated_capture_rather_than_compare_a_prefix(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CLIP)
    t = open_trace(run_id)
    caps = [e.payload["args"]["msg"] for e in t.events(kind="CALL")
            if t.code(e.code_id).qualname == "note"]
    assert [c.get("trunc") for c in caps] == [True, None]   # precondition

    assert cli.main(["watch", run_id, "--at", "prog:note",
                     "--expr", "len(msg) > 100"]) == 0
    out = capsys.readouterr().out
    assert "sites: 2   evaluated: 1   hits: 0   not-captured: 1" in out
    assert "recorded truncated" in out
    assert "sensorium info" in out          # where the caps are printed
    assert "margin 95: " in out


def test_watch_bare_container_name_points_at_len(tmp_path, monkeypatch,
                                                 capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "buf > 100"]) == 0
    out = capsys.readouterr().out
    assert "sites: 19   evaluated: 0   hits: 0   not-captured: 19" in out
    assert "compare its length with len(buf)" in out
    assert "contents only sampled" in out           # why, not just what
    assert "NOTHING WAS CHECKED" in out


def test_watch_renders_a_container_by_type_and_length_not_a_bare_number(
        tmp_path, monkeypatch, capsys):
    """`buf=99` would read as "buf is 99". It is a list of 99 things."""
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "len(buf) > 90"]) == 0
    out = capsys.readouterr().out
    assert "hits: 2" in out                         # buf reaches 99 twice
    assert "buf=<list of length 99>" in out


def test_watch_renders_a_name_that_is_not_in_scope_as_such(
        tmp_path, monkeypatch, capsys):
    """A hit decided by the left half of an `or` still has to say what the
    right half was: a blank, or a stale value, would misdescribe the site."""
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 90 or spare > 1"]) == 0
    out = capsys.readouterr().out
    assert "hits: 1" in out
    assert "spare=<not in scope>" in out and "used=99" in out


def test_watch_counts_an_evaluation_error_apart_from_a_miss(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 3"]) == 0
    out = capsys.readouterr().out
    assert "sites: 2   evaluated: 1   hits: 1   not-captured: 0" in out
    assert "errors: 1 site(s) raised while applying the predicate" in out
    assert "TypeError" in out


# -- near-misses -----------------------------------------------------------
def test_watch_near_misses_are_labelled_as_misses_and_sorted_by_margin(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    margins = [float(ln.split("margin ", 1)[1].split(":", 1)[0])
               for ln in out.splitlines() if "margin " in ln]
    assert margins == [1, 15, 30, 31, 60]
    assert "every one of them FAILED" in out


def test_watch_near_miss_cap_states_what_was_withheld_with_a_command(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 100", "--near", "2"]) == 0
    out = capsys.readouterr().out
    assert out.count("margin ") == 2
    assert "3 further near-miss(es) not shown" in out
    hint = [ln for ln in out.splitlines()
            if "see them with: " in ln][0].split("see them with: ", 1)[1]
    assert "--near 5" in hint and "<" not in hint


def test_watch_says_why_an_equality_predicate_has_no_near_misses(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used == 12345"]) == 0
    out = capsys.readouterr().out
    assert "sites: 19   evaluated: 5   hits: 0   not-captured: 14" in out
    assert "no near-misses:" in out
    assert "single numeric ordering comparison" in out


# -- paging, and the shape of the command line -----------------------------
def test_watch_limit_offers_an_exact_runnable_continuation(
        tmp_path, monkeypatch, capsys):
    """Every page's hint is a fully instantiated command that resumes THIS
    watch -- same --at, same --expr, same caps -- so walking the hints reaches
    every hit exactly once and then stops offering."""
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    argv = ["watch", run_id, "--at", "prog:fill", "--expr", "used > 30",
            "--limit", "2"]
    seen, pages = [], 0
    while True:
        assert cli.main(argv) == 0
        out = capsys.readouterr().out
        pages += 1
        page = _hit_ids(out)
        assert page and not set(page) & set(seen)      # never a repeat
        if pages == 1:
            assert "3 more; continue with:" in out
        seen += page
        hints = [ln for ln in out.splitlines() if "continue with: " in ln]
        if not hints:
            break
        hint = hints[0].split("continue with: ", 1)[1]
        assert "eN" not in hint and "<" not in hint
        argv = shlex.split(hint)[1:]
        assert pages < 5
    assert pages == 3
    assert seen == sorted(seen) and len(seen) == 5      # 40 70 85 99 69


def test_watch_orders_sites_by_event_id_across_interleaved_frames(
        tmp_path, monkeypatch, capsys):
    """Frames of a recursive call nest, so their events interleave. Walking
    frames and concatenating puts the OUTERMOST activation's last site first
    -- which reverses the narrative and makes --limit and --after page
    through the run backwards."""
    run_id = _rec(tmp_path, monkeypatch, RECURSE,
                  extra=("--focus", "prog:walk"))
    t = open_trace(run_id)
    walk = [c.id for c in t.codes() if c.qualname == "walk"]
    tails = [e.id for e in _line_events(run_id, "walk")
             if "tail" in e.payload["deltas"]]
    frames = [f.id for f in t.frames(code_id=walk[0])]
    # Precondition: three nested activations, and the frame that opened FIRST
    # is the one whose `tail` site lands LAST.
    assert len(frames) == 3 and frames == sorted(frames)
    assert len(tails) == 3 and tails == sorted(tails)
    assert t.frame(t.event(tails[-1]).frame_id).id == frames[0]

    assert cli.main(["watch", run_id, "--at", "prog:walk",
                     "--expr", "tail > 100"]) == 0
    out = capsys.readouterr().out
    assert "sites: 12   evaluated: 3   hits: 3   not-captured: 9" in out
    # The innermost activation reaches `tail` first; frame order would give
    # exactly the reverse.
    assert _hit_ids(out) == tails


def test_watch_after_reports_what_it_skipped(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 30", "--after", "e13"]) == 0
    out = capsys.readouterr().out
    assert "sites: 11   evaluated: 3   hits: 3   not-captured: 8" in out
    assert "8 earlier site(s) skipped by --after e13" in out


def test_watch_malformed_after_ref_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 1", "--after", "ee13"]) == 2
    assert "not an event reference" in capsys.readouterr().err


def test_watch_limit_below_one_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 1", "--limit", "0"]) == 2
    assert "--limit must be >= 1" in capsys.readouterr().out


def test_watch_unknown_at_spec_lists_what_the_trace_actually_has(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:refil",
                     "--expr", "used > 1"]) == 1
    out = capsys.readouterr().out
    assert "no recorded code matches --at 'prog:refil'" in out
    assert "prog:fill" in out and "prog:drain" in out


def test_watch_at_accepts_a_bare_qualname(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "fill",
                     "--expr", "used > 90"]) == 0
    assert "hits: 1" in capsys.readouterr().out


# -- gates on the recording itself -----------------------------------------
def test_watch_flags_an_incomplete_recording(tmp_path, monkeypatch, capsys):
    """A run that never finalized may simply stop mid-execution, so "the
    predicate never fired" is weaker still. Say so before the tally."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "fill", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    w.add_event(0, 1, "LINE", f, c, 2, {"deltas": {"used": {"k": "num",
                                                            "v": 40}}})
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["watch", "20260101-000000-abcdef", "--at", "fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "sites: 2   evaluated: 1   hits: 0   not-captured: 1" in out


def test_watch_header_states_what_a_site_is(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 90"]) == 0
    out = capsys.readouterr().out
    assert "watch 'used > 90' at prog:fill" in out
    assert "was not checked" in out


def test_watch_unknown_run_is_exit_2(tmp_path, monkeypatch, capsys):
    _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", "nope-nope", "--at", "prog:fill",
                     "--expr", "used > 1"]) == 2
    assert "no trace matches" in capsys.readouterr().err


def test_watch_survives_a_line_payload_with_no_deltas_key(
        tmp_path, monkeypatch, capsys):
    """Defensive on the payload shape, the way every other reader here is."""
    w = synthetic(tmp_path, monkeypatch, run_id="20260101-000000-beefed")
    c = w.intern_code("/tmp/prog.py", "fill", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    w.add_event(0, 1, "LINE", f, c, 2, {"unbound": ["used"]})
    w.set_meta("incomplete", False)
    w.close()
    assert cli.main(["watch", "20260101-000000-beefed", "--at", "fill",
                     "--expr", "used > 100"]) == 0
    assert "sites: 2   evaluated: 0   hits: 0   not-captured: 2" in \
        capsys.readouterr().out


def test_watch_matches_a_method_by_class_qualname_prefix(
        tmp_path, monkeypatch, capsys):
    src = ("class Pot:\n"
           "    def add(self, n):\n"
           "        used = n * 2\n"
           "        return used\n"
           "\n"
           "def main():\n"
           "    Pot().add(60)\n"
           "\n"
           "main()\n")
    run_id = _rec(tmp_path, monkeypatch, src, extra=("--focus", "prog:Pot"))
    assert cli.main(["watch", run_id, "--at", "prog:Pot",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "hits: 1" in out and "used=120" in out


def test_watch_reports_a_trace_whose_meta_lacks_cwd_without_crashing(
        tmp_path, monkeypatch, capsys):
    """`synthetic` writes no cwd; the refocus hint must degrade, not raise."""
    w = synthetic(tmp_path, monkeypatch, run_id="20260101-000000-nocwd")
    c = w.intern_code("/tmp/prog.py", "fill", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    w.open_frame(None, c, 1, 0, 1)
    w.set_meta("incomplete", False)
    w.close()
    assert cli.main(["watch", "20260101-000000-nocwd", "--at", "fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "sensorium run --focus prog:fill -- prog.py" in out
    assert "cd " not in out


def test_watch_reads_only_recorded_state_and_never_the_live_program(
        tmp_path, monkeypatch, capsys):
    """The evaluator has no reach: the trace is a database of primitives.
    A predicate that tries to leave the language dies on the command line."""
    run_id = _rec(tmp_path, monkeypatch)
    for bad in ("used.__class__", "open('x')", "[used]", "used[0] > 1"):
        assert cli.main(["watch", run_id, "--at", "prog:fill",
                         "--expr", bad]) == 2
    out = capsys.readouterr().out
    assert out.count("error: ") == 4


def _mark_incomplete(path) -> None:
    conn = db.open_trace(path)
    db.set_meta(conn, "incomplete", True)
    conn.commit()
    conn.close()


def test_watch_incomplete_flag_survives_a_real_recording(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    path = tmp_path / "sdir" / "traces" / f"{run_id}.db"
    assert Trace.open(path).meta["incomplete"] is False    # precondition
    _mark_incomplete(path)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "sites: 19   evaluated: 5   hits: 0   not-captured: 14" in out
