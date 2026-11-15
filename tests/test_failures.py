"""`failures`: each failed test, and the frame it failed in.

Python is built with the writer, plus one live pytest run. Rust and
TypeScript are vector-shaped traces: a panic and a vitest `expect` are
already on the frame, and this command must read them without inventing
a RAISE the recorder did not write.
"""
from sensorium import cli
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from tests.helpers import finalize_synthetic, rust_exc
from tests.programs import exc_payload, record, synthetic
from tests.rust_traces import (FILE, SITE_FILE, call, flow, fn_site, frame,
                               ret, rust_trace)
from tests.ts_traces import (call as ts_call, frame as ts_frame, raise_ev,
                             ret as ts_ret, task, ts_exc, ts_trace)

RUN = "20260101-000000-abcdef"
TS_FILE = "/w/app/src/config.ts"


def out(capsys):
    return capsys.readouterr().out


def _close(w, **meta):
    finalize_synthetic(w, **meta)
    w.close()
    return RUN


def _raise_pair(w, file, qual, line, exc, parent=None, depth=0):
    """A frame that raises `exc` at `line` and unwinds with it."""
    code = w.intern_code(file, qual, line)
    event = w.add_event(0, 1, "CALL", parent, code, line, {"args": {}})
    frame_id = w.open_frame(parent, code, event, depth, 1)
    w.add_event(0, 1, "RAISE", frame_id, code, line + 1, {"exc": exc})
    w.close_frame(frame_id, None, "unwind", exc)
    return frame_id


def _return_frame(w, file, qual, line, parent=None, depth=0):
    code = w.intern_code(file, qual, line)
    event = w.add_event(0, 1, "CALL", parent, code, line, {"args": {}})
    frame_id = w.open_frame(parent, code, event, depth, 1)
    ret_id = w.add_event(0, 1, "RETURN", frame_id, code, None,
                         {"value": None})
    w.close_frame(frame_id, ret_id, "return")
    return frame_id


# -- Python -----------------------------------------------------------------
def test_a_raised_test_maps_to_the_deepest_matching_raise(
        tmp_path, monkeypatch, capsys):
    """The escaping exception's deepest RAISE is the failure site. A test
    that returned, including one that caught an inner raise, is not a
    failure. A different exception raised and caught under the failing
    test is not the site either."""
    w = synthetic(tmp_path, monkeypatch)
    escaped = exc_payload("AssertionError", "assert 1 == 2", 11, serial=1)
    caught = exc_payload("ValueError", "kept", 22, serial=2)
    other = exc_payload("RuntimeError", "later", 33, serial=3)
    c_test = w.intern_code("/tmp/t.py", "test_adds", 1)
    e_test = w.add_event(0, 1, "CALL", None, c_test, 1, {"args": {}})
    f_test = w.open_frame(None, c_test, e_test, 0, 1)
    # caught under the failing test, then the assertion in the helper
    _raise_pair(w, "/tmp/t.py", "noise", 4, caught, parent=f_test, depth=1)
    w.add_event(0, 1, "HANDLED", f_test, c_test, 5, {"exc": caught})
    f_help = _raise_pair(w, "/tmp/t.py", "helper", 8, escaped,
                         parent=f_test, depth=1)
    w.add_event(0, 1, "RAISE", f_test, c_test, 2, {"exc": escaped})
    w.close_frame(f_test, None, "unwind", escaped)
    _return_frame(w, "/tmp/t.py", "test_ok", 20)
    c_catch = w.intern_code("/tmp/t.py", "test_catches", 30)
    e_catch = w.add_event(0, 1, "CALL", None, c_catch, 30, {"args": {}})
    f_catch = w.open_frame(None, c_catch, e_catch, 0, 1)
    _raise_pair(w, "/tmp/t.py", "boom", 34, other, parent=f_catch, depth=1)
    w.add_event(0, 1, "HANDLED", f_catch, c_catch, 32, {"exc": other})
    ret_id = w.add_event(0, 1, "RETURN", f_catch, c_catch, None,
                         {"value": None})
    w.close_frame(f_catch, ret_id, "return")
    # a method: the last segment is the test name
    c_method = w.intern_code("/tmp/t.py", "TestMath.test_eq", 40)
    e_method = w.add_event(0, 1, "CALL", None, c_method, 40, {"args": {}})
    f_method = w.open_frame(None, c_method, e_method, 0, 1)
    w.add_event(0, 1, "RAISE", f_method, c_method, 41, {"exc": other})
    w.close_frame(f_method, None, "unwind", other)
    _close(w)

    assert cli.main(["failures", RUN]) == ANSWERED
    text = out(capsys)
    assert text.splitlines()[0] == "failed (2):"
    assert "test_adds  f1 /tmp/t.py:test_adds" in text
    assert f"at f{f_help} /tmp/t.py:helper L9" in text
    assert "AssertionError('assert 1 == 2')" in text
    assert "test_eq  f" in text
    assert "at f" in text and "/tmp/t.py:TestMath.test_eq L41" in text
    assert "test_ok" not in text
    assert "test_catches" not in text
    assert "ValueError" not in text
    assert "noise" not in text


def test_a_test_that_unwound_in_untraced_code_names_the_test_frame(
        tmp_path, monkeypatch, capsys):
    """No RAISE was traced. The test frame and its unwind are the record,
    and the answer does not invent a line."""
    w = synthetic(tmp_path, monkeypatch)
    exc = exc_payload("AssertionError", "assert 0", 1, serial=4)
    code = w.intern_code("/tmp/t.py", "test_hidden", 1)
    event = w.add_event(0, 1, "CALL", None, code, 1, {"args": {}})
    frame_id = w.open_frame(None, code, event, 0, 1)
    w.close_frame(frame_id, None, "unwind", exc)
    _close(w)
    assert cli.main(["failures", RUN]) == ANSWERED
    text = out(capsys)
    assert "test_hidden  f1 /tmp/t.py:test_hidden" in text
    assert "at f1 /tmp/t.py:test_hidden\n" in text
    assert " L" not in text
    assert "AssertionError('assert 0')" in text


def test_no_test_frames_and_passing_tests_are_different_answers(
        tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    _return_frame(w, "/tmp/t.py", "main", 1)
    _close(w)
    assert cli.main(["failures", RUN]) == NEGATIVE
    assert out(capsys).strip() == "no test frames recorded"

    w = synthetic(tmp_path, monkeypatch, run_id="20260101-000000-passed1")
    _return_frame(w, "/tmp/t.py", "test_ok", 1)
    finalize_synthetic(w)
    w.close()
    assert cli.main(["failures", "20260101-000000-passed1"]) == NEGATIVE
    assert out(capsys).strip() == "no test failures recorded"


def test_an_unfinished_recording_with_a_failure_still_answers(
        tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    exc = exc_payload("AssertionError", "nope", 1, serial=1)
    _raise_pair(w, "/tmp/t.py", "test_adds", 1, exc)
    finalize_synthetic(w)
    w.set_meta("incomplete", True)
    w.close()
    assert cli.main(["failures", RUN]) == ANSWERED
    text = out(capsys)
    assert text.startswith("INCOMPLETE:")
    assert "test_adds" in text


def test_an_unfinished_recording_with_nothing_failed_is_unsettled(
        tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    _return_frame(w, "/tmp/t.py", "test_ok", 1)
    finalize_synthetic(w)
    w.set_meta("incomplete", True)
    w.close()
    assert cli.main(["failures", RUN]) == UNSETTLED
    text = out(capsys)
    assert "INCOMPLETE:" in text
    assert "no test failures recorded" in text


def test_limit_zero_is_a_bad_call_and_a_short_page_names_the_rest(
        tmp_path, monkeypatch, capsys):
    assert cli.main(["failures", RUN, "--limit", "0"]) == BAD_CALL
    assert "--limit must be >= 1" in out(capsys)

    w = synthetic(tmp_path, monkeypatch)
    for name, serial in (("test_a", 1), ("test_b", 2)):
        exc = exc_payload("AssertionError", name, serial, serial=serial)
        _raise_pair(w, "/tmp/t.py", name, serial, exc)
    _close(w)
    assert cli.main(["failures", RUN, "--limit", "1"]) == ANSWERED
    text = out(capsys)
    assert "failed (2):" in text
    assert "test_a" in text
    assert "test_b" not in text
    assert f"... 1 more; continue with: sensorium failures {RUN} --limit 2" in text


def test_a_real_pytest_failure_maps_to_the_asserting_frame(
        tmp_path, monkeypatch, capsys):
    src = '''
def helper():
    assert 1 == 2

def test_adds():
    helper()

def test_ok():
    assert 1 == 1

def test_catches():
    try:
        raise ValueError("kept")
    except ValueError:
        return None

if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-p", "no:cacheprovider", "-q"]))
'''
    run_id = record(tmp_path, monkeypatch, src)
    assert cli.main(["failures", run_id]) == ANSWERED
    text = out(capsys)
    assert "failed (1):" in text, text
    assert "test_adds" in text
    assert "helper" in text
    assert "AssertionError" in text
    assert "test_ok" not in text
    assert "test_catches" not in text
    assert "kept" not in text


# -- Rust -------------------------------------------------------------------
def _panic(msg, serial=1, loc=None):
    return rust_exc("panic", msg, serial, loc=loc, kind="panic")


def test_a_rust_panic_maps_to_the_test_and_keeps_its_location(
        tmp_path, monkeypatch, capsys):
    loc = f"{SITE_FILE}:12:5"
    msg = "assertion `left == right` failed: left: 1 right: 2"
    unwind = {**_panic(msg, loc=loc)}
    payload = {"exc": _panic(msg), "loc": loc}
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "tests::adds", 8], [FILE, "check", 12],
               [FILE, "main", 30]],
        frames=[frame(1, 1, None, unwind_exc=unwind),
                frame(2, 2, None, parent=1, depth=1, unwind_exc=unwind),
                frame(3, 4, 5)],
        events=[call(1000, 1, 8),
                call(2000, 2, 12),
                flow(3000, "RAISE", 2, 2, 12, payload),
                call(4000, 3, 30),
                ret(5000, 3, 3, "ok")],
        sites=[fn_site("tests::adds", SITE_FILE, 8, test=True),
               fn_site("check", SITE_FILE, 12),
               fn_site("main", SITE_FILE, 30, main=True)])
    assert cli.main(["failures", run_id]) == ANSWERED
    text = out(capsys)
    assert "failed (1):" in text
    assert f"tests::adds  f1 {FILE}:tests::adds" in text
    assert f"at f2 {FILE}:check L12" in text
    assert f"panic({msg!r}) at {loc}" in text
    assert "main" not in text.split("failed")[1]


def test_a_panic_the_test_caught_is_not_a_failure(
        tmp_path, monkeypatch, capsys):
    """`catch_unwind` then a normal return: the panic is on a child frame
    and the test frame itself returned."""
    unwind = _panic("caught", loc=f"{SITE_FILE}:9:1")
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "tests::recovers", 3], [FILE, "inner", 9]],
        frames=[frame(1, 1, 4),
                frame(2, 2, None, parent=1, depth=1, unwind_exc=unwind)],
        events=[call(1000, 1, 3),
                call(2000, 2, 9),
                flow(3000, "RAISE", 2, 2, 9,
                     {"exc": _panic("caught"), "loc": unwind["loc"]}),
                ret(4000, 1, 1, "ok")],
        sites=[fn_site("tests::recovers", SITE_FILE, 3, test=True),
               fn_site("inner", SITE_FILE, 9)])
    assert cli.main(["failures", run_id]) == NEGATIVE
    assert out(capsys).strip() == "no test failures recorded"


def test_a_panic_outside_any_test_is_not_a_test_failure(
        tmp_path, monkeypatch, capsys):
    """A binary's main can panic. That is not a failed test, and a test
    that returned is not one either."""
    unwind = _panic("boom", loc=f"{SITE_FILE}:30:1")
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "tests::ok", 3], [FILE, "main", 30]],
        frames=[frame(1, 1, 2),
                frame(2, 3, None, unwind_exc=unwind)],
        events=[call(1000, 1, 3),
                ret(2000, 1, 1, "ok"),
                call(3000, 2, 30),
                flow(4000, "RAISE", 2, 2, 30,
                     {"exc": _panic("boom"), "loc": unwind["loc"]})],
        sites=[fn_site("tests::ok", SITE_FILE, 3, test=True),
               fn_site("main", SITE_FILE, 30, main=True)])
    assert cli.main(["failures", run_id]) == NEGATIVE
    assert out(capsys).strip() == "no test failures recorded"


def test_a_test_marked_unwind_without_a_raise_is_still_listed(
        tmp_path, monkeypatch, capsys):
    loc = f"{SITE_FILE}:4:1"
    unwind = _panic("explicit panic", loc=loc)
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "tests::boom", 4]],
        frames=[frame(1, 1, None, unwind_exc=unwind)],
        events=[call(1000, 1, 4)],
        sites=[fn_site("tests::boom", SITE_FILE, 4, test=True)])
    assert cli.main(["failures", run_id]) == ANSWERED
    text = out(capsys)
    assert f"tests::boom  f1 {FILE}:tests::boom" in text
    assert f"at f1 {FILE}:tests::boom\n" in text
    assert " L" not in text
    assert f"panic('explicit panic') at {loc}" in text


def test_a_rust_trace_with_no_test_site_says_so(
        tmp_path, monkeypatch, capsys):
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "main", 1]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 1), ret(2000, 1, 1, "ok")],
        sites=[fn_site("main", SITE_FILE, 1, main=True)])
    assert cli.main(["failures", run_id]) == NEGATIVE
    assert out(capsys).strip() == "no test functions recorded"


# -- TypeScript -------------------------------------------------------------
def test_an_expect_failure_is_the_task_unwind_with_no_invented_raise(
        tmp_path, monkeypatch, capsys):
    """No RAISE at all: the answer is the task and the frame's unwind,
    and it does not print a line the trace does not hold."""
    exc = ts_exc("AssertionError", "expected 1 to equal 2", 7)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[TS_FILE, "adds", 4], [TS_FILE, "passes", 12]],
        tasks=[task(1, "adds two numbers"), task(2, "passes")],
        frames=[ts_frame(1, 1, unwind_exc=exc),
                ts_frame(2, 2, 3)],
        events=[ts_call(1000, 1, 4, task=1),
                ts_call(2000, 2, 12, task=2),
                ts_ret(3000, 2, 2, task=2)])
    assert cli.main(["failures", run_id]) == ANSWERED
    text = out(capsys)
    assert "failed (1):" in text, text
    assert "adds two numbers  task t1" in text
    assert f"at f1 {TS_FILE}:adds\n" in text
    assert " L" not in text
    assert "AssertionError('expected 1 to equal 2')" in text
    assert "passes" not in text


def test_a_traced_throw_in_the_failing_frame_prints_its_line(
        tmp_path, monkeypatch, capsys):
    exc = ts_exc("Error", "nope", 3)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[TS_FILE, "adds", 4]],
        tasks=[task(1, "adds two numbers")],
        frames=[ts_frame(1, 1, unwind_exc=exc)],
        events=[ts_call(1000, 1, 4, task=1),
                raise_ev(2000, 1, 1, 9, exc, task=1)])
    assert cli.main(["failures", run_id]) == ANSWERED
    text = out(capsys)
    assert f"at f1 {TS_FILE}:adds L9" in text
    assert "Error('nope')" in text


def test_a_caught_throw_is_not_a_failed_test(tmp_path, monkeypatch, capsys):
    exc = ts_exc("Error", "caught", 3)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[TS_FILE, "adds", 4], [TS_FILE, "inner", 8]],
        tasks=[task(1, "adds two numbers")],
        frames=[ts_frame(1, 1, 4),
                ts_frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[ts_call(1000, 1, 4, task=1),
                ts_call(2000, 2, 8, task=1),
                raise_ev(2500, 2, 2, 9, exc, task=1),
                ts_ret(3000, 1, 1, task=1)])
    assert cli.main(["failures", run_id]) == NEGATIVE
    assert out(capsys).strip() == "no test failures recorded"


def test_a_typescript_trace_with_no_tasks_says_so(
        tmp_path, monkeypatch, capsys):
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[TS_FILE, "main", 1]],
        frames=[ts_frame(1, 1, 2)],
        events=[ts_call(1000, 1, 1), ts_ret(2000, 1, 1)],
        tasks=[])
    assert cli.main(["failures", run_id]) == NEGATIVE
    assert out(capsys).strip() == "no tests recorded"
