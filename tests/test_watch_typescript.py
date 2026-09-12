"""`watch` over a FOCUSED TypeScript trace: one site spelling, one dialect.

Three claims, and each is a place where the command could answer wrongly
rather than refuse:

  * **A site has ONE spelling.** Every form `sensorium ts run --focus`
    accepts is a form `--at` accepts, and the forms it does not accept are
    still refused: `src/cache.ts:Fog` names a file this trace does not
    hold, and answering about `src/lib/cache.ts` instead would be an answer
    about code the reader did not name. The rule has two implementations --
    `typescript/src/focus.mjs` selects functions before a run, `query/sites`
    matches codes after one -- and they are held to ONE example table
    (`typescript/test/fixtures/site-spellings.json`), which is what keeps
    two languages' matchers from drifting apart (design section 4.3, ruling
    R7).

  * **A capture is read in the recorder's own dialect.** `key == 'rate'` is
    SATISFIED here because `'rate'` is how `util.inspect` spells the string
    rate. Read as Rust's `Debug` -- the reader's only dialect before this
    rung -- the same text spells the four-character text `'rate'`, and the
    predicate would come back a quiet, wrong `False` at every site.

  * **A block-scoped name goes away.** The row that ends a block lists what
    it unbound, and a fold that ignored it would report a HIT on a `const`
    that no longer exists. The recorded shape is asserted BEFORE the output
    is, so the test cannot pass vacuously.

The re-record guidance is the fourth: the command it prints must be one
THIS recorder can run. `sensorium run --focus` cannot read a TypeScript
trace at all, so a hint naming it sends the reader to a second refusal --
which is why `tests/test_vocab.py`'s TypeScript scan carries that string as
a forbidden needle.
"""
import json
from pathlib import Path

import pytest

from sensorium import cli
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from sensorium.query import sites
from sensorium.query.watch_cmd import refocus_cmd, site_matches
from tests.flow_programs import open_trace
from tests.helpers import finalize_synthetic
from tests.programs import synthetic
from tests.ts_traces import (TS_CAPABILITIES, call, frame, line_ev, out, ret,
                             task, ts_trace)

FIXTURE = (Path(__file__).resolve().parents[1] / "typescript" / "test"
           / "fixtures" / "site-spellings.json")
SPELLINGS = json.loads(FIXTURE.read_text())

ROOT = "/w/app"
FILE = "/w/app/src/lib/cache.ts"
TEST_FILE = "/w/app/src/lib/cache.test.ts"

#: What a container records under a focus: `line` and `locals` are declared
#: because the transform instrumented statements, and `object_identity` was
#: already true at every tier.
FOCUSED_CAPS = {**TS_CAPABILITIES, "line": True, "locals": True}


def dbg(text, **extra):
    return {"k": "dbg", "v": text, "trunc": False, **extra}


def focused_trace(tmp_path, monkeypatch, **meta):
    """One container of `npx vitest run src/config`, focused on `refresh`.

    `Fog.compute` is in the same file and was NOT focused: it is called, its
    CALL says its locals were unread, and it opens a frame with no statement
    row in it. That is the ordinary shape of a focused run -- a focus names
    functions, not files -- and it is what the re-record guidance is for.
    """
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "refresh", 12], [FILE, "Fog.compute", 40],
               [TEST_FILE, "cache > refreshes", 5]],
        frames=[frame(3, 1, 9),
                frame(1, 2, 6, parent=1, depth=1),
                frame(2, 7, 8, parent=1, depth=1)],
        events=[
            call(1000, 3, 5, task=1),
            call(2000, 1, 12, task=1, caller=None,
                 args={"key": dbg("'rate'")}),
            line_ev(3000, 2, 1, 13, {"base": dbg("4")}, task=1),
            line_ev(4000, 2, 1, 15, {"scaled": dbg("8")}, task=1),
            line_ev(5000, 2, 1, 17, {}, unbound=["scaled"], task=1),
            ret(6000, 2, 1, "100", task=1),
            call(7000, 2, 40, task=1, caller=None),
            ret(8000, 3, 2, "7", task=1),
            ret(9000, 1, 3, task=1),
        ],
        tasks=[task(1, "cache > refreshes")],
        capabilities=FOCUSED_CAPS, root=ROOT,
        focus=["cache.ts:refresh"],
        focus_matched=["src/lib/cache.ts:refresh"],
        **meta)


def code_named(trace, qualname):
    return next(c for c in trace.codes() if c.qualname == qualname)


# -- (a) one site spelling, held to the fixture both matchers read ---------
@pytest.mark.parametrize("spec", SPELLINGS["matching"])
def test_every_spelling_the_focus_flag_accepts_selects_the_code(
        spec, tmp_path, monkeypatch):
    run_id = focused_trace(tmp_path, monkeypatch)
    trace = open_trace(run_id)
    code = code_named(trace, SPELLINGS["qualname"])
    assert code.file.endswith(SPELLINGS["rel"])
    assert site_matches(code, spec, trace) is True


@pytest.mark.parametrize("spec", SPELLINGS["not_matching"])
def test_every_spelling_the_fixture_refuses_is_refused_here_too(
        spec, tmp_path, monkeypatch):
    run_id = focused_trace(tmp_path, monkeypatch)
    trace = open_trace(run_id)
    assert site_matches(code_named(trace, SPELLINGS["qualname"]),
                        spec, trace) is False


@pytest.mark.parametrize("spec", ["refresh", "cache:refresh",
                                  "cache.ts:refresh",
                                  "src/lib/cache.ts:refresh"])
def test_the_four_spellings_all_answer_the_same_question(
        spec, tmp_path, monkeypatch, capsys):
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", spec,
                     "--expr", "base == 4"]) == ANSWERED
    text = out(capsys)
    assert "sites: 4   evaluated: 3   hits: 3   not-captured: 1" in text
    assert "verdict: SATISFIED at 3 of the 3 site(s)" in text


def test_a_file_the_trace_does_not_hold_is_not_answered_about(
        tmp_path, monkeypatch, capsys):
    """`lib` is a DIRECTORY, not a spelling of this file. The listing that
    follows is the trace's own sites, each in the spelling `--at` and
    `--focus` share -- never the dotted module name, which no TypeScript
    reader would type."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "lib:refresh",
                     "--expr", "base == 4"]) == NEGATIVE
    text = out(capsys)
    assert "error: no recorded code matches --at 'lib:refresh'" in text
    assert "  src/lib/cache.ts:refresh" in text
    assert "  src/lib/cache.ts:Fog.compute" in text
    assert "  src/lib/cache.test.ts:cache > refreshes" in text
    assert "src.lib.cache" not in text


# -- (b) the dialect, end to end -------------------------------------------
def test_a_focused_calls_argument_is_read_in_this_recorders_dialect(
        tmp_path, monkeypatch, capsys):
    """`'rate'` is inspect's spelling of a string. Rust's `Debug` writes
    `"rate"` for the same value, so a reader with one dialect answers False
    here -- at every site, quietly, with a state line that looks right."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "refresh",
                     "--expr", "key == 'rate'"]) == ANSWERED
    text = out(capsys)
    assert "sites: 4   evaluated: 4   hits: 4   not-captured: 0" in text
    assert "state: key='rate'" in text


def test_the_predicate_constants_reach_a_typescript_trace(
        tmp_path, monkeypatch, capsys):
    """`undefined` is a value this recorder writes and this predicate can
    name. The RETURN is not a site, so the question is asked of a local."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "refresh",
                     "--expr", "base == undefined"]) == NEGATIVE
    text = out(capsys)
    assert "sites: 4   evaluated: 3   hits: 0   not-captured: 1" in text
    assert "NEVER RECORDED" not in text


# -- (c) a block-scoped name goes away -------------------------------------
def test_a_const_in_a_block_is_gone_after_the_row_that_unbound_it(
        tmp_path, monkeypatch, capsys):
    """The recorded shape first: the third row carries EMPTY deltas and a
    non-empty `unbound`, which is the row a "skip events with no deltas"
    fold drops -- taking the unbind with it and reporting two hits."""
    run_id = focused_trace(tmp_path, monkeypatch)
    trace = open_trace(run_id)
    rows = [e for e in trace.events() if e.kind == "LINE"]
    assert [e.payload.get("unbound") for e in rows] == [None, None, ["scaled"]]
    assert rows[-1].payload["deltas"] == {}
    assert cli.main(["watch", run_id, "--at", "refresh",
                     "--expr", "scaled == 8"]) == ANSWERED
    text = out(capsys)
    assert "sites: 4   evaluated: 1   hits: 1   not-captured: 3" in text
    assert "verdict: SATISFIED at 1 of the 1 site(s)" in text
    assert "scaled: not in scope at this site   [3 site(s)]" in text


# -- (d) the command a reader is told to run -------------------------------
def test_the_re_record_guidance_names_this_recorders_own_command(
        tmp_path, monkeypatch):
    """An UNFOCUSED container: nothing was focused, so the command carries
    exactly the one site the reader asked about, spelled the way
    `--focus` takes it, and the harness command as it was typed."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "refresh", 12]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 12), ret(2000, 1, 1, "100")],
        root=ROOT)
    trace = open_trace(run_id)
    assert refocus_cmd(trace, [code_named(trace, "refresh")]) == (
        "cd /w/app && sensorium ts run --focus src/lib/cache.ts:refresh "
        "-- npx vitest run src/config")


def test_a_focus_the_run_already_had_travels_into_the_guidance(
        tmp_path, monkeypatch, capsys):
    """End to end, on the ordinary shape: `refresh` was focused and
    `Fog.compute` was not, so its frame recorded no local at all and the
    command that would record one keeps the focus this run had -- as it was
    TYPED -- and adds the site asked about."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "Fog.compute",
                     "--expr", "n > 0"]) == UNSETTLED
    text = out(capsys)
    assert "no local of these frames was recorded at all" in text
    assert ("refocus and re-run: cd /w/app && sensorium ts run "
            "--focus cache.ts:refresh --focus src/lib/cache.ts:Fog.compute "
            "-- npx vitest run src/config") in text
    assert "sensorium run --focus" not in text


def test_the_python_guidance_is_the_command_it_always_was(
        tmp_path, monkeypatch):
    """The fence. Python's template is a MOVE into the vocabulary table,
    not a rewrite: this is the string `refocus_cmd` built before `sites.py`
    existed, and `tests/test_watch.py` holds the same bytes end to end."""
    w = synthetic(tmp_path, monkeypatch, run_id="20260101-000000-python")
    code = w.intern_code("/w/py/pkg/prog.py", "fill", 3)
    w.add_event(0, 1, "CALL", None, code, 3, {"args": {}})
    w.open_frame(None, code, 1, 0, 1)
    finalize_synthetic(w, cwd="/w/py", argv=["prog.py", "--fast"])
    w.close()
    trace = open_trace("20260101-000000-python")
    assert refocus_cmd(trace, list(trace.codes())) == (
        "cd /w/py && sensorium run --focus pkg.prog:fill -- prog.py --fast")


def test_the_spelling_helper_is_the_one_the_listing_and_the_command_share(
        tmp_path, monkeypatch):
    """One helper, so a site cannot be spelled one way in a listing and
    another in the command that re-records it."""
    run_id = focused_trace(tmp_path, monkeypatch)
    trace = open_trace(run_id)
    assert sites.spell_site(trace, code_named(trace, "refresh")) == \
        "src/lib/cache.ts:refresh"
    assert sites.spell_site(trace, code_named(trace, "cache > refreshes")) == \
        "src/lib/cache.test.ts:cache > refreshes"
