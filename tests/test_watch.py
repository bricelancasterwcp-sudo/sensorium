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

What the VERDICT is allowed to claim lives in `test_watch_verdict.py` -- the
same seam as `test_refocus.py` / `test_refocus_licence.py`.
"""
import shlex

import pytest

from sensorium import cli
from sensorium.exit import NEGATIVE, UNSETTLED
from sensorium.query.expr import OUT_OF_SCOPE
from sensorium.query.watch_cmd import _guidance
from sensorium.store import db
from sensorium.store.reader import Trace
from tests.helpers import (LEGACY_FORMAT, finalize_synthetic, record_script,
                           run_cli)
from tests.programs import open_trace, synthetic
from tests.watch_programs import (CARRIER, CLIP, HANDLER, LOOPDEL, MIXED,
                                  RECURSE, line_events, rec)


def _hit_ids(out: str) -> list[int]:
    return [int(ln.split("  HIT   e", 1)[1].split(" ", 1)[0])
            for ln in out.splitlines() if ln.startswith("  HIT   e")]


# -- the brief's four ------------------------------------------------------
def test_watch_near_miss_when_no_hits(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 90"]) == 0
    out = capsys.readouterr().out
    assert "HIT" in out and "used=99" in out
    assert "sites: 19   evaluated: 5   hits: 1   not-captured: 14" in out
    assert "verdict: SATISFIED at 1 of the 5 site(s)" in out
    assert "near-misses" not in out


def test_watch_counts_not_captured_sites(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)           # no focus: no locals
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "not-captured: 5" in out                # 5 CALL sites lack `used`
    assert "refocus" in out
    assert "sites: 5   evaluated: 0   hits: 0   not-captured: 5" in out
    assert "NOTHING WAS CHECKED" in out


def test_watch_bad_expr_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)
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
    run_id = rec(tmp_path, monkeypatch, HANDLER,
                  extra=("--focus", "prog:stage"))
    lines = line_events(run_id, "stage")
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
    run_id = rec(tmp_path, monkeypatch, LOOPDEL,
                  extra=("--focus", "prog:scan"))
    lines = line_events(run_id, "scan")
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
    run_id = rec(tmp_path, monkeypatch, CARRIER,
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
    run_id = rec(tmp_path, monkeypatch, CARRIER,
                  extra=("--focus", "prog:stage"))

    assert cli.main(["watch", run_id, "--at", "prog:stage",
                     "--expr", "depth > 0 or blob == 'x'"]) == 0
    state = _state_of_first_hit(capsys.readouterr().out)

    held = int(state.split("blob=<clipped to ", 1)[1].split(" chars>", 1)[0])
    assert 0 < held < 250, f"claimed {held} of a 250-char string"


# -- reasons a site could not be evaluated ---------------------------------
def test_watch_refuses_a_truncated_capture_rather_than_compare_a_prefix(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, CLIP)
    t = open_trace(run_id)
    caps = [e.payload["args"]["msg"] for e in t.events(kind="CALL")
            if t.code(e.code_id).qualname == "note"]
    assert [c.get("trunc") for c in caps] == [True, None]   # precondition

    assert cli.main(["watch", run_id, "--at", "prog:note",
                     "--expr", "len(msg) > 100"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "sites: 2   evaluated: 1   hits: 0   not-captured: 1" in out
    assert "recorded truncated" in out
    assert "sensorium info" in out          # where the caps are printed
    assert "margin 95: " in out


def test_watch_bare_container_name_points_at_len(tmp_path, monkeypatch,
                                                 capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "buf > 100"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "sites: 19   evaluated: 0   hits: 0   not-captured: 19" in out
    assert "compare its length with len(buf)" in out
    assert "contents only sampled" in out           # why, not just what
    assert "NOTHING WAS CHECKED" in out


def test_watch_renders_a_container_by_type_and_length_not_a_bare_number(
        tmp_path, monkeypatch, capsys):
    """`buf=99` would read as "buf is 99". It is a list of 99 things."""
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "len(buf) > 90"]) == 0
    out = capsys.readouterr().out
    assert "hits: 2" in out                         # buf reaches 99 twice
    assert "buf=<list of length 99>" in out


def test_watch_renders_a_name_that_is_not_in_scope_as_such(
        tmp_path, monkeypatch, capsys):
    """A hit decided by the left half of an `or` still has to say what the
    right half was: a blank, or a stale value, would misdescribe the site."""
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 90 or spare > 1"]) == 0
    out = capsys.readouterr().out
    assert "hits: 1" in out
    assert "spare=<not in scope>" in out and "used=99" in out


def test_watch_counts_an_evaluation_error_apart_from_a_miss(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, MIXED)
    assert cli.main(["watch", run_id, "--at", "prog:tally",
                     "--expr", "n > 3"]) == 0
    out = capsys.readouterr().out
    assert "sites: 2   evaluated: 1   hits: 1   not-captured: 0" in out
    assert "errors: 1 site(s) raised while applying the predicate" in out
    assert "TypeError" in out


# -- near-misses -----------------------------------------------------------
def test_watch_near_misses_are_labelled_as_misses_and_sorted_by_margin(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == NEGATIVE
    out = capsys.readouterr().out
    margins = [float(ln.split("margin ", 1)[1].split(":", 1)[0])
               for ln in out.splitlines() if "margin " in ln]
    assert margins == [1, 15, 30, 31, 60]
    assert "every one of them FAILED" in out


def test_watch_near_miss_cap_states_what_was_withheld_with_a_command(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 100", "--misses", "2"]) == NEGATIVE
    out = capsys.readouterr().out
    assert out.count("margin ") == 2
    assert "3 further near-miss(es) not shown" in out
    hint = [ln for ln in out.splitlines()
            if "see them with: " in ln][0].split("see them with: ", 1)[1]
    assert "--misses 5" in hint and "<" not in hint


def test_watch_near_is_rejected_as_promised_in_0_7_0(
        tmp_path, monkeypatch, capsys):
    """0.7.0 kept `--near` as a hidden, deprecated alias for `--misses` and
    said it "will be removed in 0.8.0" (see CHANGELOG.md). This release
    keeps that promise: `--near` is gone from the parser entirely, so
    passing it is an unrecognized argument like any other unknown flag --
    argparse raises `SystemExit` straight out of `parse_args`, before
    `cli.main` ever dispatches (see `cli.py`'s own docstring, and the same
    shape `test_help_epilogs.py` pins for `--help`), at the standard "fix
    the call" exit status."""
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    argv_common = ["watch", run_id, "--at", "prog:fill", "--expr",
                   "used > 100"]

    with pytest.raises(SystemExit) as excinfo:
        cli.main([*argv_common, "--near", "2"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments: --near" in err

    # `--misses` alone is unaffected: the replacement flag still works.
    status_misses = cli.main([*argv_common, "--misses", "2"])
    captured_misses = capsys.readouterr()
    assert status_misses == NEGATIVE
    assert captured_misses.err == ""


def test_watch_says_why_an_equality_predicate_has_no_near_misses(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used == 12345"]) == NEGATIVE
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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
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
    run_id = rec(tmp_path, monkeypatch, RECURSE,
                  extra=("--focus", "prog:walk"))
    t = open_trace(run_id)
    walk = [c.id for c in t.codes() if c.qualname == "walk"]
    tails = [e.id for e in line_events(run_id, "walk")
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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 30", "--after", "e13"]) == 0
    out = capsys.readouterr().out
    assert "sites: 11   evaluated: 3   hits: 3   not-captured: 8" in out
    assert "8 earlier site(s) skipped by --after e13" in out


def test_watch_malformed_after_ref_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 1", "--after", "ee13"]) == 2
    assert "not an event reference" in capsys.readouterr().err


def test_watch_limit_below_one_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill", "--expr",
                     "used > 1", "--limit", "0"]) == 2
    assert "--limit must be >= 1" in capsys.readouterr().out


def test_watch_unknown_at_spec_lists_what_the_trace_actually_has(
        tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:refil",
                     "--expr", "used > 1"]) == 1
    out = capsys.readouterr().out
    assert "no recorded code matches --at 'prog:refil'" in out
    assert "prog:fill" in out and "prog:drain" in out


def test_watch_at_accepts_a_bare_qualname(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
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
                     "--expr", "used > 100"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "sites: 2   evaluated: 1   hits: 0   not-captured: 1" in out


def test_watch_header_states_what_a_site_is(tmp_path, monkeypatch, capsys):
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 90"]) == 0
    out = capsys.readouterr().out
    assert "watch 'used > 90' at prog:fill" in out
    assert "was not checked" in out


def test_watch_unknown_run_is_exit_2(tmp_path, monkeypatch, capsys):
    rec(tmp_path, monkeypatch)
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
    finalize_synthetic(w)
    w.close()
    assert cli.main(["watch", "20260101-000000-beefed", "--at", "fill",
                     "--expr", "used > 100"]) == UNSETTLED
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
    run_id = rec(tmp_path, monkeypatch, src, extra=("--focus", "prog:Pot"))
    assert cli.main(["watch", run_id, "--at", "prog:Pot",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "hits: 1" in out and "used=120" in out


def test_watch_reports_a_trace_whose_meta_lacks_cwd_without_crashing(
        tmp_path, monkeypatch, capsys):
    """`synthetic` writes no cwd; the refocus hint must degrade, not raise.

    A missing `cwd` is a legacy shape -- format 4 requires the key on a
    finalized trace -- so the fixture claims the format it actually is."""
    w = synthetic(tmp_path, monkeypatch, run_id="20260101-000000-nocwd")
    c = w.intern_code("/tmp/prog.py", "fill", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    w.open_frame(None, c, 1, 0, 1)
    w.set_meta("trace_format", LEGACY_FORMAT)
    w.set_meta("incomplete", False)
    w.close()
    assert cli.main(["watch", "20260101-000000-nocwd", "--at", "fill",
                     "--expr", "used > 100"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "sensorium run --focus prog:fill -- prog.py" in out
    assert "cd " not in out


def test_watch_reads_only_recorded_state_and_never_the_live_program(
        tmp_path, monkeypatch, capsys):
    """The evaluator has no reach: the trace is a database of primitives.
    A predicate that tries to leave the language dies on the command line."""
    run_id = rec(tmp_path, monkeypatch)
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
    run_id = rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    path = tmp_path / "sdir" / "traces" / f"{run_id}.db"
    assert Trace.open(path).meta["incomplete"] is False    # precondition
    _mark_incomplete(path)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "sites: 19   evaluated: 5   hits: 0   not-captured: 14" in out


# -- code that opens no frame ----------------------------------------------
# Kept beside its tests rather than in `watch_programs.py`: what these two
# sources produce is a code object with CALL events and NO frame, which is a
# fact about the recorder, not a fold shape the test has to read back.
ASYNC_WATCH = """
import asyncio

async def worker(name):
    await asyncio.sleep(0)
    return name

def main():
    return asyncio.run(worker("A"))

if __name__ == "__main__":
    main()
"""

# Both kinds under one `--at`: `check` is framed (and focused, so it has
# LINEs), `worker` is a coroutine and contributes no site at all.
ASYNC_MIXED = """
import asyncio


def check(n):
    total = n * 2
    return total


async def worker(label):
    await asyncio.sleep(0)
    return check(len(label))


def main():
    return asyncio.run(worker("abc"))


if __name__ == "__main__":
    main()
"""


def test_watch_evaluates_inside_a_focused_coroutine(
        tmp_path, monkeypatch, capsys):
    """`worker` is a coroutine, but arc 2 opens a frame for it on a format-3
    trace, so its CALL and LINE are ordinary sites: `_unframed`'s join comes
    back empty, and `watch` never reaches the unframed-guidance branch at
    all. This is the positive twin of the format-2 fixture pin in
    `test_format2_fixture.py`, which keeps proving the OLD trace still says
    "opens no frame in this version"."""
    run_id = rec(tmp_path, monkeypatch, src=ASYNC_WATCH,
                 extra=("--focus", "prog:worker"))
    assert cli.main(["watch", run_id, "--at", "prog:worker",
                     "--expr", "name == 'A'"]) == 0
    out = capsys.readouterr().out
    assert "HIT" in out
    assert "NOTHING WAS CHECKED" not in out
    sites_line = next(l for l in out.splitlines() if l.startswith("sites:"))
    assert int(sites_line.split()[1]) >= 1


def test_watch_counts_the_unframed_matches_when_only_some_are_frameless(
        tmp_path, monkeypatch, capsys):
    """A module-wide `--at` spanning both kinds. On a format-3 trace, arc 2
    frames `worker` too, so it now contributes sites like `check` and
    `main` do: no code object here is unframed any more, so the
    coroutine/generator note and the NEVER RECORDED block it feeds never
    print, and the verdict is an ordinary one."""
    run_id = rec(tmp_path, monkeypatch, src=ASYNC_MIXED,
                 extra=("--focus", "prog"))
    assert cli.main(["watch", run_id, "--at", "prog",
                     "--expr", "n > 0"]) == 0
    out = capsys.readouterr().out
    assert ("sites: 12   evaluated: 3   hits: 3   not-captured: 9   "
            "errors: 0") in out
    assert "coroutine/generator code" not in out
    assert ("verdict: SATISFIED at 3 of the 3 site(s) the predicate could "
            "be evaluated at") in out
    assert "opens no frame in this version" not in out
    assert "NEVER RECORDED" not in out


def test_guidance_for_unframed_code_never_offers_a_refocus():
    """Unreachable through `run` today: when every match is unframed there
    are no sites, so `print_unavailable` returns before asking. Pinned
    directly rather than left to rot behind the guard -- re-recording cannot
    frame a coroutine, so "refocus and re-run" is the one thing this must
    never say."""
    assert _guidance(OUT_OF_SCOPE, "n", False, False, None, None, True) == [
        "no site exists for these code objects: coroutine/generator code "
        "opens no frame in this version"]


MEMBERSHIP = """
def work():
    meta = {}
    meta = {"inline_rolls": [1, 2]}
    big = {f"k{i}": i for i in range(40)}
    return len(big)

def main():
    work()

main()
"""


def test_watch_membership_and_empty_literal_predicates(tmp_path):
    """Field test on a FastAPI handler: the natural predicates over a dict
    local are `'key' in meta` and `meta != {}`. Both are decided from the
    capture -- the sample for membership, the length for emptiness -- and
    a membership question the sample cannot settle is counted as a site
    that could not be checked, with the reason, never as False."""
    run_id, _trace, r = record_script(tmp_path, MEMBERSHIP,
                                      extra=("--focus", "prog:work"))
    assert run_id, r.stderr
    sdir = tmp_path / "sdir"
    out = run_cli(["watch", run_id, "--at", "prog:work", "--expr",
                   "'inline_rolls' in meta"], cwd=tmp_path,
                  sensorium_dir=sdir).stdout
    assert "HIT" in out and "meta=" in out
    out = run_cli(["watch", run_id, "--at", "prog:work", "--expr",
                   "meta != {}"], cwd=tmp_path, sensorium_dir=sdir).stdout
    assert "HIT" in out
    out = run_cli(["watch", run_id, "--at", "prog:work", "--expr",
                   "'zzz' in big"], cwd=tmp_path, sensorium_dir=sdir).stdout
    assert "HIT" not in out
    assert "sample does not decide" in out       # 40 keys, 8 sampled


def test_watch_refuses_a_trace_that_declares_no_line_events(tmp_path, monkeypatch, capsys):
    from sensorium import cli
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"line": False})
    w.close()
    assert cli.main(["watch", "20260101-000000-abcdef", "--at", "main",
                     "--expr", "x > 1"]) == UNSETTLED
    assert "watch needs line" in capsys.readouterr().out
