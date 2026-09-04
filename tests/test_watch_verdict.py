"""`watch`: what the verdict is allowed to claim.

The same seam as `test_refocus.py` / `test_refocus_licence.py`, for the same
reason. The other file covers what `watch` DOES -- which sites it finds, how
it folds state, how it pages. This one covers the sentence it prints at the
end, which is the only place "I could not check that" can quietly become
"the invariant held".

Every verdict assertion here extracts the verdict's own lines and compares
them exactly. Substring-matching the whole of stdout cannot tell the two
verdict branches apart: the caveated one contains the clean one's closing
words, and replacing the clean branch's entire second line with "(recorded
sites only)" once left the whole suite green.

Each case's exit status is pinned beside those lines, by name, because the
status IS the verdict: SATISFIED answers yes (ANSWERED), "not satisfied"
answers no about what was recorded (NEGATIVE), and NOTHING WAS CHECKED is
the trace unable to answer at all (UNSETTLED). A reader who branches on the
number never reaches the prose above, so a case whose sentence and whose
status disagreed would tell two different stories to two different readers.
"""
from sensorium import cli
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from tests.watch_programs import KEEP, LOOPDEL, MIXED, line_events, rec

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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 9000"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 9000"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 1000 and ghost > 1"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 1000 and n > 2"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 2 or ghost > 1"]) == ANSWERED
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
    run_id = rec(tmp_path, monkeypatch, KEEP)
    assert cli.main(["watch", run_id, "--at", "prog:keep",
                     "--expr", "n > 0 or ghost > 1"]) == ANSWERED
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
    run_id = rec(tmp_path, monkeypatch, LOOPDEL,
                  extra=("--focus", "prog:scan"))
    lines = line_events(run_id, "scan")
    last_bind = max(e.id for e in lines if "peak" in e.payload["deltas"])
    tail = [e for e in lines if e.id > last_bind]
    assert len(tail) == 2 and "peak" not in tail[-1].payload["deltas"]

    assert cli.main(["watch", run_id, "--at", "prog:scan", "--expr",
                     "peak > 5", "--after", f"e{tail[0].id}"]) == UNSETTLED
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
    run_id = rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 3"]) == ANSWERED
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
    run_id = rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 3"]) == ANSWERED
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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 30"]) == ANSWERED
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
    run_id = rec(tmp_path, monkeypatch)
    deep = "x" + " + x" * 1000 + " > 1"
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", deep]) == BAD_CALL
    out = capsys.readouterr().out
    assert "error: expression nests deeper than 50 levels" in out
    assert "Traceback" not in out


def test_watch_misses_below_one_is_exit_2(tmp_path, monkeypatch, capsys):
    """Consistent with --limit, and for one more reason: near-misses are the
    answer when nothing hit, so a flag that silently suppresses them would
    make a run look clean without changing anything about the run."""
    run_id = rec(tmp_path, monkeypatch)
    for bad in ("0", "-5"):
        assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                         "used > 1", "--misses", bad]) == BAD_CALL
    out = capsys.readouterr().out
    assert out.count("--misses must be >= 1") == 2


def test_watch_nothing_checked_says_so_instead_of_reporting_zero_hits(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "verdict: NOTHING WAS CHECKED" in out
    assert "'could not evaluate', NOT 'the invariant held'" in out
    assert "not captured at 5 of 5 site(s)" in out


def test_watch_refocus_guidance_is_an_exact_runnable_command(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == UNSETTLED
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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "sensorium run" not in out
    assert "scope, not capture depth" in out

