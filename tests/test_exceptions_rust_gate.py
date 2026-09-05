"""`exceptions` on a Rust trace: what it refuses, counts and pages.

Not a disposition among them. The `err_flow` capability gate (design R9)
and its exit 3, the lang-keyed refusal a third language still gets, the
index's selection on `exc.kind` rather than on a type spelled `panic`, the
two empty answers and the statuses they earn, `--after`/`--limit`, the
fixed tally order, and the `partial` header that says what the recording
was not watching.

Split from `test_exceptions_rust.py` at the 800-line ceiling; the verdicts
are in that file and in `test_exceptions_rust_ambiguous.py`.
"""
from sensorium import cli
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from tests.helpers import RUST_CAPABILITIES, rust_exc
from tests.rust_traces import (FILE, S1, SITE_FILE, call, err_flow,
                               five_dispositions, flow, fn_site, frame, out,
                               ret, rust_trace, swallow_trace)


# -- the five dispositions, the tally, and paging ---------------------------
def five_dispositions(tmp_path, monkeypatch):
    """One trace holding every disposition, on five threads so each shape
    is minimal. The chains are laid out in REVERSE tally order, so a tally
    printed in encounter order would come out backwards."""
    unwind = {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1}
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "escapes", 5], [FILE, "inner", 18], [FILE, "stuck", 9],
               [FILE, "run", 3], [FILE, "crash", 40], [FILE, "swallow", 60]],
        frames=[
            frame(1, 1, 5),                                   # f1 escapes
            frame(2, 2, 4, parent=1, depth=1),                # f2 inner
            frame(3, 6, None, closed_by=None, thread=2),      # f3 stuck
            frame(2, 7, 9, parent=3, depth=1, thread=2),      # f4 inner
            frame(4, 10, 15, thread=3),                       # f5 run
            frame(2, 11, 13, parent=5, depth=1, thread=3),    # f6 inner
            frame(5, 16, None, thread=4, unwind_exc=unwind),  # f7 crash
            frame(2, 17, 19, parent=7, depth=1, thread=4),    # f8 inner
            frame(6, 20, 22, thread=5),                       # f9 swallow
        ],
        events=[
            # thread 1 -- ambiguous (ok close, no sink)
            call(1000, 1, 5),
            call(1100, 2, 18),
            flow(1200, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "A", S1, hop=1,
                          terminal="ambiguous_escaped")),
            ret(1300, 2, 2, "err", "Err(A)"),
            ret(1400, 1, 1, "ok", "None"),
            # thread 2 -- propagated (still open at the end)
            call(2000, 3, 9, thread=2),
            call(2100, 2, 18, thread=2),
            flow(2200, "RAISE", 4, 2, 18,
                 err_flow("exit", "demo::Boom", "B", S1, hop=1,
                          terminal="propagated"), thread=2),
            ret(2300, 4, 2, "err", "Err(B)", thread=2),
            # thread 3 -- returned to harness
            call(3000, 4, 3, thread=3),
            call(3100, 2, 18, thread=3),
            flow(3200, "RAISE", 6, 2, 18,
                 err_flow("exit", "demo::Boom", "C", S1, hop=1), thread=3),
            ret(3300, 6, 2, "err", "Err(C)", thread=3),
            flow(3400, "RAISE", 5, 4, 3,
                 err_flow("exit", "demo::Boom", "C", S1, hop=2,
                          terminal="returned_to_harness"), thread=3),
            ret(3500, 5, 4, "err", "Err(C)", thread=3),
            # thread 4 -- panicked
            call(4000, 5, 40, thread=4),
            call(4100, 2, 18, thread=4),
            flow(4200, "RAISE", 8, 2, 18,
                 err_flow("exit", "demo::Boom", "D", S1, hop=1,
                          terminal="panicked"), thread=4),
            ret(4300, 8, 2, "err", "Err(D)", thread=4),
            # thread 5 -- swallowed
            call(5000, 6, 60, thread=5),
            flow(5100, "HANDLED", 9, 6, 62,
                 err_flow("sink_ok", "demo::Boom", "E", S1, hop=1,
                          terminal="swallowed_candidate"), thread=5),
            ret(5200, 9, 6, "ok", "()", thread=5),
        ],
        sites=[fn_site("run", SITE_FILE, 3, test=True)],
        incomplete=True, live_threads=[2])


def test_the_tally_is_printed_in_the_pinned_order(
        tmp_path, monkeypatch, capsys):
    run_id = five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("dispositions: swallowed 1, panicked 1, returned-to-harness 1, "
            "propagated 1, ambiguous 1") in o, o
    assert "raised (5):" in o, o

def test_limit_clips_the_rows_but_never_the_tally(
        tmp_path, monkeypatch, capsys):
    run_id = five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id, "--limit", "2"]) == ANSWERED
    o = out(capsys)
    assert "e3 RAISE" in o and "e8 RAISE" in o, o
    assert "e12 RAISE" not in o and "e18 RAISE" not in o, o
    # every chain in scope is counted, printed or not
    assert ("dispositions: swallowed 1, panicked 1, returned-to-harness 1, "
            "propagated 1, ambiguous 1") in o, o
    assert ("... 3 more; continue with: sensorium exceptions "
            f"{run_id} --after e8 --limit 2") in o, o

def test_after_resumes_from_a_chains_origin_and_says_what_it_skipped(
        tmp_path, monkeypatch, capsys):
    run_id = five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id, "--after", "e8"]) == ANSWERED
    o = out(capsys)
    assert ("raised (3 of 5; 2 earlier chain(s) skipped by --after e8):"
            in o), o
    assert "e3 RAISE" not in o and "e8 RAISE" not in o, o
    assert "dispositions: swallowed 1, panicked 1, returned-to-harness 1" in o
    assert "propagated" not in o, o

# -- the Index selects on exc.kind, never on a type spelled "panic" ---------
def test_an_err_type_spelled_panic_is_judged_and_a_panic_raise_is_not(
        tmp_path, monkeypatch, capsys):
    """R7: the Rust index selects by `exc.kind`. A workspace error type
    literally named `panic` is a chain; a panic RAISE is not one, and is
    named rather than silently dropped."""
    unwind = {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1}
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "weird", 18]],
        frames=[frame(1, 1, None, thread=1, unwind_exc=unwind),
                frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "panic", "Deliberate", S1, hop=1,
                          terminal="panicked")),
            ret(4000, 2, 2, "err", "Err(Deliberate)"),
            {"ts": 5000, "thread": 1, "kind": "RAISE", "frame": 1, "code": 1,
             "line": 5,
             "payload": {"exc": rust_exc("panic", "boom", 1,
                                         loc="demo/src/lib.rs:5:9",
                                         kind="panic")},
             "task": None},
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (1):" in o, o           # the err, not the panic
    assert "weird raise panic('Deliberate') L18" in o, o
    assert "panicked -- the frame holding it unwound (f1, panic('boom'))" in o
    # the panic RAISE is not a chain, and the answer says it exists
    assert ("panics: 1 recorded -- this command judges Err flow; a panic is "
            "a frame's unwind, printed by `tree` and `frame`") in o, o

# -- R9: the capability gate, before any rule runs --------------------------
def test_a_rust_trace_whose_recorder_declares_no_err_flow_is_refused(
        tmp_path, monkeypatch, capsys):
    """A rung-2 recording holds no err-flow record, so what would have to
    change is the recording. Exit 3, the standard capability sentence, and
    nothing judged."""
    caps = {"line": False, "locals": False, "return_value": True,
            "tasks": True, "threads": True, "children": False,
            "stdin": False, "output": False, "object_identity": False,
            "refocus": False}
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")],
        recorder="sensorium-rt 0.2.0", capabilities=caps,
        run_id="20260101-000000-rung02")
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions needs err_flow, which recorder "
            "sensorium-rt 0.2.0 declares it does not produce "
            "(capabilities.err_flow: false); nothing was checked") in o, o
    assert "no exceptions recorded" not in o, o
    assert "raised (" not in o and "dispositions:" not in o, o
    # the retired rung-2 sentence must not come back for a Rust trace
    assert "needs the Rust disposition rules" not in o, o

def test_the_capability_gate_runs_before_any_rule_sees_a_chain(
        tmp_path, monkeypatch, capsys):
    """The same trace as the swallow case, with the declaration removed:
    a refusal, not a verdict computed from records the recorder disowns."""
    caps = dict(RUST_CAPABILITIES)
    caps.pop("err_flow")
    run_id = swallow_trace(tmp_path, monkeypatch, capabilities=caps,
                            recorder="sensorium-rt 0.2.0")
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert "capabilities.err_flow: false" in o, o

# -- the empty answers ------------------------------------------------------
def test_a_finalized_rust_trace_with_no_err_chains_answers_none(
        tmp_path, monkeypatch, capsys):
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")])
    assert cli.main(["exceptions", run_id]) == NEGATIVE
    o = out(capsys)
    assert "no exceptions recorded" in o, o

def test_an_incomplete_rust_trace_with_no_err_chains_is_unsettled(
        tmp_path, monkeypatch, capsys):
    """`caps.none_status`: an empty answer on a recording that stopped
    mid-flight reports where the RECORDING ended, not what the program
    did."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, None, closed_by=None)],
        events=[call(1000, 1, 3)],
        incomplete=True, live_threads=[1])
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert "INCOMPLETE: this recording never finalized" in o, o
    assert "no exceptions recorded" in o, o

# -- R6: `?` sites the transformer could not reach --------------------------
def test_a_partial_fn_is_named_rather_than_guessed_about(
        tmp_path, monkeypatch, capsys):
    """Corpus `macro_arg_partial`: an `Err` at an unreachable `?` site is
    recorded by nothing, so `exceptions` says the site exists instead of
    letting its silence read as "nothing happened there"."""
    run_id = swallow_trace(
        tmp_path, monkeypatch,
        partial=[{"file": SITE_FILE, "line": 21, "qualname": "load",
                  "kind": "try", "reason": "macro-arg"}])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("partial: 1 ?-site the transformer could not reach -- an Err "
            "raised at one is recorded by nothing and appears nowhere "
            "below") in o, o
    assert f"load {SITE_FILE}:21 (macro-arg)" in o, o

def test_a_trace_with_no_partial_key_says_nothing_about_partial_sites(
        tmp_path, monkeypatch, capsys):
    run_id = swallow_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    assert "partial:" not in out(capsys)

# -- a third language keeps the lang-keyed refusal --------------------------
def test_a_language_with_no_rules_at_all_still_gets_the_lang_refusal(
        tmp_path, monkeypatch, capsys):
    """R9: only the `rust` branch of `_language_refusal` retires."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")],
        lang="go", recorder="sensorium-go 0.1.0")
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions on a go trace needs the Rust disposition "
            "rules (rung 3); the Python rules would misread Err values as "
            "exceptions; nothing was judged") in o, o
