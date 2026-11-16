"""`refocus --compact`: the verdict and the finding, not the essay.

The long report stays the CLI default, because the existing snapshots
are of that report. Compact is a wording of the same assessment: the
same exit code, with a withheld licence or a divergence still visible
in one line, and without the catalogue.

The compact report itself is at most four lines (verdict, the concrete
why or the licence line, and a single world line when the world is why
a divergence happened). The CLI also prints the rerun preamble, which
is not the essay; the bound below is on the verdict block, and a whole-
command ceiling sits beside it so the essay cannot sneak back in front
of the banner.
"""
from sensorium.exit import NEGATIVE
from sensorium.query.diff_cmd import compare
from sensorium.query import refocus_cmd
from sensorium.store.reader import Trace
from tests.refocus_programs import COUNTER, LOOP, rec, refocus, synthetic


def _verdict_block(out: str) -> list[str]:
    return out.split("--- verdict ---", 1)[1].strip().splitlines()


def test_verbose_refocus_still_lists_the_licence_and_the_blind_spots(
        tmp_path):
    """The CLI default is the long report. Compact must not become what
    a person gets by typing the command they already type."""
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "what sensorium sees at all" in r.stdout
    assert "licence: verified against" in r.stdout
    assert "on exactly these points" in r.stdout
    assert "identical call shape" in r.stdout


def test_compact_match_is_the_verdict_and_a_short_licence(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate", "--compact")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "verdict: MATCH" in r.stdout
    assert "licence: verified against" in r.stdout
    assert "what sensorium sees at all" not in r.stdout
    assert "on exactly these points" not in r.stdout
    assert "identical call shape" not in r.stdout
    assert "a MATCH does not say the two runs scheduled" not in r.stdout
    verdict = _verdict_block(r.stdout)
    assert len(verdict) < 12, verdict
    # Preamble plus a two-line verdict. The essay is what pushed the
    # long report past a screen; this ceiling is the regression gate.
    assert len(r.stdout.splitlines()) < 16, r.stdout


def test_compact_divergence_names_the_why_and_exits_negative(tmp_path):
    run_id, sdir = rec(tmp_path, COUNTER)
    r = refocus(sdir, run_id, "--focus", "prog:bump", "--compact")
    assert r.returncode == NEGATIVE, r.stdout + r.stderr
    assert ("refocus verdict: DIVERGED -- the compared thread took a "
            "different path") in r.stdout
    assert "causal step" in r.stdout
    assert "a divergence can also be caused by the deeper capture" \
        not in r.stdout
    assert "what sensorium sees at all" not in r.stdout
    assert len(_verdict_block(r.stdout)) < 12, r.stdout


def test_compact_renderer_withholds_in_one_line(tmp_path, capsys):
    """A withheld licence is still the exit's meaning. One line names
    how many checks failed and the first reason, not the catalogue."""
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-cmpcta")
    b = synthetic(sdir, "20260101-000000-cmpctb")
    ta, tb = Trace.open(a), Trace.open(b)
    res = compare(ta, tb)
    assessed = refocus_cmd.assess(
        ta, tb, res, ["the sky turned green", "and the sea"])

    verbose = refocus_cmd.report(ta, tb, res, a.stem, b.stem, assessed)
    verbose_out = capsys.readouterr().out
    assert verbose == 0
    assert "what sensorium sees at all" in verbose_out
    assert "  - the sky turned green" in verbose_out
    assert "  - and the sea" in verbose_out

    compact = refocus_cmd.report(
        ta, tb, res, a.stem, b.stem, assessed, compact=True)
    out = capsys.readouterr().out
    assert compact == 0
    assert "verdict: MATCH" in out
    assert ("licence: WITHHELD -- 2 check(s) failed; first: "
            "the sky turned green") in out
    assert "  - and the sea" not in out
    assert "what sensorium sees at all" not in out
    assert len(out.splitlines()) < 12, out


def test_compact_renderer_grants_without_the_fact_list(tmp_path, capsys):
    sdir = tmp_path / "sdir"
    a = synthetic(sdir, "20260101-000000-cmpctc")
    b = synthetic(sdir, "20260101-000000-cmpctd")
    ta, tb = Trace.open(a), Trace.open(b)
    res = compare(ta, tb)
    assessed = refocus_cmd.assess(ta, tb, res)

    rc = refocus_cmd.report(
        ta, tb, res, a.stem, b.stem, assessed, compact=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines() == [
        "refocus verdict: MATCH -- every recorded thread produced the "
        "identical CALL/RETURN/RAISE/HANDLED sequence",
        f"licence: verified against {a.stem}",
    ]
    assert "identical call shape" not in out
