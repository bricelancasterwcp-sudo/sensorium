"""`grep` and `exceptions`.

The `exceptions` half is organised one test per *program shape*, because the
head of the trace is byte-identical for behaviours that mean opposite things.
Six probing rounds during Tasks 6-8 established that RAISE + HANDLED with no
later RAISE is produced by a genuine swallow, by a bare `raise` re-raise, and
by an exception merely crossing a `finally` -- CPython compiles `finally` as
an implicit handler, so EXCEPTION_HANDLED fires with no `except` in sight.
Every shape below was recorded and read back before the classifier existed;
the expected strings are what the real trace supports, not what would be
convenient.
"""
import shlex

from sensorium import cli, paths
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script

# -- program shapes --------------------------------------------------------

# Genuine swallow: `except Exception: pass`. RAISE lands in parse_row's frame
# (int() is C code and untraced), HANDLED lands in load_all's frame, and
# load_all returns normally -- the only shape where closed_by == "return".
SWALLOW = """
ROWS = ["alice,10", "bob,20", "carol,x7", "dan,5", "erin,??"]

def parse_row(row):
    name, amount = row.split(",")
    return name, int(amount)

def load_all(rows):
    out = []
    for row in rows:
        try:
            out.append(parse_row(row))
        except Exception:
            pass
    return out

def main():
    rows = load_all(ROWS)
    print(f"total: {sum(a for _, a in rows)} from {len(rows)} rows")

if __name__ == "__main__":
    main()
"""

CRASH = """
def get(uid):
    return {1: "Alice"}.get(uid)

def main():
    get(1)
    get(7).title()

main()
"""

# Bare `raise` in the handler: RAISE + two HANDLED rows, no later RAISE --
# the trace head a naive classifier reads as SWALLOWED. It is not: the frame
# holding both HANDLED rows is closed_by "unwind" with the same exception.
BARE_RERAISE = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError:
        raise

def main():
    risky()

main()
"""

# Never caught anywhere, merely passes through a bare `finally`. Verified:
# two HANDLED rows and every frame closed_by "unwind". Same trace head again.
FINALLY_PASSTHROUGH = """
def inner():
    raise ValueError("boom")

def middle():
    try:
        inner()
    finally:
        pass

def main():
    middle()

main()
"""

# Caught, then replaced by a different exception.
TRANSLATED = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        raise RuntimeError("wrapped") from e

def main():
    try:
        risky()
    except RuntimeError:
        pass

main()
"""

# Genuinely swallowed, and then the same frame dies of something unrelated.
# Recorded side by side with TRANSLATED the two traces are identical apart
# from line numbers, so the classifier must reach the same verdict for both;
# claiming either "swallowed" or "propagated" here would be a false accusation
# on one of them. (`raise X from e` sets __context__ and the unrelated raise
# does not -- but capture_exc records only type/msg/oid, so the trace has no
# way to tell. Recording __context__ would separate them; that is a recorder
# change, not a query-side one.)
SWALLOW_THEN_UNRELATED = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError:
        pass
    raise RuntimeError("later, unrelated")

def main():
    try:
        risky()
    except RuntimeError:
        pass

main()
"""

# Raised inside untraced library code (json), caught in traced code.
UNTRACED_LIB = """
import json

def parse(text):
    try:
        return json.loads(text)
    except ValueError:
        return None

def main():
    print(parse('{"a": 1}'))
    print(parse('not json'))

main()
"""

# Bare re-raise whose handler lives in code the run does not trace. The trace
# records the raise and the cleanup HANDLED and then simply stops knowing.
RERAISE_CAUGHT_UNTRACED = """
import lib

def risky():
    try:
        raise ValueError("boom")
    except ValueError:
        raise

def main():
    print(lib.guarded(risky))

main()
"""

UNTRACED_LIB_SOURCE = """
def guarded(fn):
    try:
        return fn()
    except ValueError:
        return "caught in untraced library"
"""

# Raised in traced code, caught in untraced code, with no `try` in traced code
# at all: EXCEPTION_HANDLED fires in the library frame and is not recorded, so
# the trace holds a RAISE and no HANDLED whatsoever.
RAISE_CAUGHT_UNTRACED = """
import lib

def risky():
    raise ValueError("boom")

def main():
    print(lib.guarded(risky))

main()
"""

# `raise e` (by name, not bare) fires RAISE, not RERAISE, so the same object
# gets a second RAISE row -- the one shape where "raised again" is provable.
EXPLICIT_RERAISE = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        raise e

def main():
    try:
        risky()
    except ValueError:
        pass

main()
"""

# Same, but nothing catches the second raise: two RAISE rows share one
# identity and the header must name the one that actually escaped.
EXPLICIT_RERAISE_ESCAPES = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        raise e

def main():
    risky()

main()
"""

# `except E as e: return e` -- an ordinary idiom. The handler frame closes
# "return", which is the swallow signal, and yet the exception is stored,
# re-raised by the caller, and kills the process. Fix round 1: this was
# reported as "SWALLOWED ... never re-raised" two lines under a header that
# said the same exception was uncaught -- the tool contradicting itself.
STASH_AND_RERAISE = """
def stash():
    try:
        raise ValueError("x")
    except ValueError as e:
        return e

def main():
    raise stash()

main()
"""

# Three raises of an identically-typed, identically-messaged exception. Each
# must pair with its own handler, not with a neighbour's.
LOOP_SAME_MESSAGE = """
def boom(i):
    raise ValueError("same message")

def main():
    for i in range(3):
        try:
            boom(i)
        except ValueError:
            pass
    print("done")

main()
"""

# Generators are frameless by design (no frame is opened), so RAISE and
# HANDLED both carry frame_id NULL and there is no closed_by to read.
GENERATOR_HANDLES = """
def gen(items):
    for it in items:
        try:
            yield int(it)
        except ValueError:
            yield -1

def main():
    print(list(gen(["1", "x", "3"])))

main()
"""

CLEAN = """
def add(a, b):
    return a + b

def main():
    print(add(1, 2))

main()
"""


def _rec(tmp_path, monkeypatch, src, extra=(), files=()):
    for name, text in files:
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    run_id, _trace, r = record_script(tmp_path, src, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def _synthetic(tmp_path, monkeypatch, run_id="20260101-000000-abcdef"):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    return w


def _exc(type_, msg, oid):
    return {"type": type_, "msg": msg, "oid": oid}


# -- grep ------------------------------------------------------------------
def test_grep_by_value_content(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "carol"]) == 0
    out = capsys.readouterr().out
    assert "parse_row" in out and "matches:" in out


def test_grep_kind_and_fn_filters(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CRASH)
    assert cli.main(["grep", run_id, "get", "--kind", "RETURN",
                     "--fn", "get"]) == 0
    out = capsys.readouterr().out
    assert "get -> None" in out and "get -> 'Alice'" in out
    assert "CALL" not in out                      # --kind actually filtered


def test_grep_limit_offers_continuation(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    cli.main(["grep", run_id, "parse_row", "--limit", "1"])
    out = capsys.readouterr().out
    assert "more; continue with:" in out and "--after e" in out


def test_grep_continuation_is_runnable_and_reveals_the_rest(
        tmp_path, monkeypatch, capsys):
    """The hint must be a command, not a template, and paging through it must
    reproduce the unclipped result exactly -- no gap, no repeat. Task 10 was
    sent back for emitting a `--root fN` template instead of a command."""
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "parse_row"]) == 0
    full = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("e")]
    assert len(full) > 3

    pages: list[str] = []
    argv = ["grep", run_id, "parse_row", "--limit", "3"]
    for _ in range(10):                      # guard: never loop forever
        assert cli.main(argv) == 0
        out = capsys.readouterr().out
        pages += [ln for ln in out.splitlines() if ln.startswith("e")]
        tail = out.strip().splitlines()[-1]
        if "continue with: " not in tail:
            break
        hint = tail.split("continue with: ", 1)[1]
        assert "eN" not in hint and "fN" not in hint and "..." not in hint
        argv = shlex.split(hint)
        assert argv[0] == "sensorium"
        argv = argv[1:]
    assert pages == full


def test_grep_continuation_carries_every_filter(tmp_path, monkeypatch, capsys):
    """A hint that drops --kind/--fn resumes a *different* search and
    silently shows rows the first page had filtered out."""
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "parse_row", "--kind", "CALL",
                     "--fn", "parse_row", "--limit", "1"]) == 0
    out = capsys.readouterr().out
    hint = out.strip().splitlines()[-1].split("continue with: ", 1)[1]
    assert "--kind CALL" in hint and "--fn parse_row" in hint

    assert cli.main(shlex.split(hint)[1:]) == 0
    rest = capsys.readouterr().out
    rows = [ln for ln in rest.splitlines() if ln.startswith("e")]
    assert len(rows) == 1 and rows[0].split()[1] == "CALL"  # --limit carried
    assert "matches: 4" in rest                   # 5 calls, 1 already shown


def test_grep_reports_the_true_total_not_just_what_it_printed(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    cli.main(["grep", run_id, "parse_row"])
    total = int(next(ln for ln in capsys.readouterr().out.splitlines()
                     if ln.startswith("matches:")).split()[1])
    assert total > 1
    cli.main(["grep", run_id, "parse_row", "--limit", "1"])
    out = capsys.readouterr().out
    assert f"matches: {total}" in out
    assert "showing 1" in out


def test_grep_no_match_says_what_it_looked_at(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CLEAN)
    assert cli.main(["grep", run_id, "nonexistent-token"]) == 0
    out = capsys.readouterr().out
    assert "matches: 0" in out
    assert "scanned" in out and "event" in out


def test_grep_zero_match_note_owns_up_to_the_fn_filter(
        tmp_path, monkeypatch, capsys):
    """"none contained 'alice'" is a false statement about a trace in which
    three events do contain it and were removed by --fn. Every active filter
    has to appear in the line that explains the empty result."""
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "alice"]) == 0
    hits = int(next(ln for ln in capsys.readouterr().out.splitlines()
                    if ln.startswith("matches:")).split()[1])
    assert hits > 0                              # 'alice' really is in there

    assert cli.main(["grep", run_id, "alice", "--fn", "nosuchfn"]) == 0
    out = capsys.readouterr().out
    assert "matches: 0" in out
    assert "excluded by --fn 'nosuchfn'" in out
    assert "none of the remaining" in out
    assert "none contained" not in out           # the false fact


def test_grep_line_kind_with_no_line_capture_says_why(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CLEAN)      # recorded without --focus
    assert cli.main(["grep", run_id, "a", "--kind", "LINE"]) == 0
    out = capsys.readouterr().out
    assert "matches: 0" in out
    assert "--focus" in out


def test_grep_rejects_a_nonpositive_limit(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CLEAN)
    assert cli.main(["grep", run_id, "add", "--limit", "0"]) == 2
    assert "--limit" in capsys.readouterr().out


# -- exceptions: one test per program shape --------------------------------
def test_exceptions_flags_genuine_swallow(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 2          # carol,x7 and erin,??
    assert "ValueError" in out and "load_all" in out
    assert "returned normally" in out
    assert "swallowed 2" in out


def test_exceptions_reports_uncaught(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CRASH)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "uncaught: AttributeError" in out
    assert "SWALLOWED" not in out
    # pin the verdict, not merely the absence of the wrong one: a classifier
    # that fell through to some other branch would still satisfy the above
    assert "uncaught -- left the program (exit 1); not swallowed" in out
    assert "dispositions: uncaught 1" in out
    assert "raised at e" in out                  # header links to the RAISE


def test_exceptions_never_calls_a_bare_reraise_swallowed(
        tmp_path, monkeypatch, capsys):
    """RAISE + HANDLED + no later RAISE, and yet nothing was swallowed."""
    run_id = _rec(tmp_path, monkeypatch, BARE_RERAISE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    # not merely "not swallowed" -- the verdict has to be the right one
    assert "uncaught -- left the program (exit 1); not swallowed" in out
    assert "uncaught 1" in out
    assert "not a catch" in out                  # the HANDLED rows explained


def test_exceptions_never_calls_a_finally_passthrough_swallowed(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, FINALLY_PASSTHROUGH)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "uncaught: ValueError('boom')" in out
    # the shape that makes this hard: HANDLED rows really are present
    assert "HANDLED row(s)" in out


def test_exceptions_refuses_to_guess_when_the_handler_is_untraced(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, RERAISE_CAUGHT_UNTRACED,
                  extra=("--exclude", "lib.py"),
                  files=(("lib.py", UNTRACED_LIB_SOURCE),))
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "propagated (handler not in traced code)" in out


def test_exceptions_translation_and_unrelated_failure_read_the_same(
        tmp_path, monkeypatch, capsys):
    """Two programs, opposite behaviour, indistinguishable traces. The tool
    must report the same thing for both and claim neither."""
    a = _rec(tmp_path / "a", monkeypatch, TRANSLATED)
    assert cli.main(["exceptions", a]) == 0
    out_a = capsys.readouterr().out
    b = _rec(tmp_path / "b", monkeypatch, SWALLOW_THEN_UNRELATED)
    assert cli.main(["exceptions", b]) == 0
    out_b = capsys.readouterr().out

    for out in (out_a, out_b):
        # the ValueError: caught here, but the frame died of something else
        assert "unwound with RuntimeError" in out
        assert "cannot say" in out
        assert "ambiguous 1" in out
        # the RuntimeError: genuinely swallowed by main's `except: pass`
        assert out.count("SWALLOWED") == 1
        assert "swallowed 1" in out


def test_exceptions_attributes_an_untraced_library_raise_to_its_caller(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, UNTRACED_LIB)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "JSONDecodeError" in out
    assert out.count("SWALLOWED") == 1
    assert "parse L" in out                     # the traced frame that caught


def test_exceptions_reports_an_explicit_reraise_as_raised_again(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, EXPLICIT_RERAISE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "raised again at e" in out
    assert "re-raised 1" in out
    assert out.count("SWALLOWED") == 1          # main's `except: pass`


def test_exceptions_never_calls_a_stored_and_reraised_exception_swallowed(
        tmp_path, monkeypatch, capsys):
    """A returning handler frame is the swallow signal, but `return e` hands
    the exception out of that frame. With a later RAISE of the same identity
    both readings are live -- address reuse, or stored and raised again --
    so neither may be asserted."""
    run_id = _rec(tmp_path, monkeypatch, STASH_AND_RERAISE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "never re-raised" not in out          # it demonstrably was
    assert "uncaught: ValueError('x')" in out
    # the verdict names both live readings and picks neither
    assert "returned normally, but a later RAISE" in out
    assert "raised again" in out
    assert "reused address" in out
    assert "cannot tell them apart" in out
    assert "dispositions: uncaught 1, ambiguous 1" in out


def test_exceptions_output_never_contradicts_its_own_uncaught_header(
        tmp_path, monkeypatch, capsys):
    """No verdict may claim an exception ended in traced code when the
    header says that same identity left the program."""
    for src in (STASH_AND_RERAISE, EXPLICIT_RERAISE_ESCAPES, BARE_RERAISE):
        d = tmp_path / str(abs(hash(src)) % 10 ** 6)
        run_id = _rec(d, monkeypatch, src)
        assert cli.main(["exceptions", run_id]) == 0
        out = capsys.readouterr().out
        assert out.splitlines()[0].startswith("uncaught: ")
        assert "SWALLOWED" not in out, src
        assert "never re-raised" not in out, src
        # and no `swallowed N` bucket in the tally either
        tally = next(ln for ln in out.splitlines()
                     if ln.startswith("dispositions: "))
        assert "swallowed" not in tally, src


def test_exceptions_uncaught_header_names_the_raise_that_escaped(
        tmp_path, monkeypatch, capsys):
    """Two RAISE rows share one identity; the header must point at the later
    one, which is the object that actually left the program."""
    run_id = _rec(tmp_path, monkeypatch, EXPLICIT_RERAISE_ESCAPES)
    assert cli.main(["exceptions", run_id]) == 0
    lines = capsys.readouterr().out.splitlines()
    rows = [ln for ln in lines if " RAISE " in ln]
    assert len(rows) == 2
    first, last = (r.strip().split()[0] for r in rows)
    assert lines[0].endswith(f"raised at {last}")
    assert f"raised at {first}" not in lines[0]


def test_exceptions_pairs_each_loop_raise_with_its_own_handler(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, LOOP_SAME_MESSAGE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 3
    handlers = [ln.split("SWALLOWED at ")[1].split()[0]
                for ln in out.splitlines() if "SWALLOWED at " in ln]
    assert len(set(handlers)) == 3              # three distinct HANDLED rows


def test_exceptions_refuses_to_classify_a_frameless_handler(
        tmp_path, monkeypatch, capsys):
    """Generators open no frame, so there is no closed_by to read and no
    honest verdict to give -- saying so beats guessing."""
    run_id = _rec(tmp_path, monkeypatch, GENERATOR_HANDLES)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "no frame recorded" in out
    assert "generator" in out


def test_exceptions_says_so_when_nothing_was_raised(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CLEAN)
    assert cli.main(["exceptions", run_id]) == 0
    assert capsys.readouterr().out.strip() == "no exceptions recorded"


# -- exceptions: synthetic traces for shapes CPython will not reproduce ----
def test_exceptions_survives_a_recycled_oid(tmp_path, monkeypatch, capsys):
    """`oid` is `id(exc)` and CPython reuses addresses: measured live, a
    ValueError and the RuntimeError raised two lines later in the same frame
    shared an oid. Identity must therefore be (type, msg, oid) -- keyed on
    oid alone, the RuntimeError's handler would be credited to the
    ValueError and one of them would be mis-classified."""
    w = _synthetic(tmp_path, monkeypatch)
    c_risky = w.intern_code("/tmp/prog.py", "risky", 1)
    c_main = w.intern_code("/tmp/prog.py", "main", 8)
    e_call_main = w.add_event(0, 1, "CALL", None, c_main, 8, {"args": {}})
    f_main = w.open_frame(None, c_main, e_call_main, 0, 1)
    e_call = w.add_event(0, 1, "CALL", None, c_risky, 1, {"args": {}})
    f_risky = w.open_frame(f_main, c_risky, e_call, 1, 1)
    val = _exc("ValueError", "boom", 999)
    run = _exc("RuntimeError", "later", 999)          # same address, new object
    e_raise_v = w.add_event(0, 1, "RAISE", f_risky, c_risky, 3, {"exc": val})
    e_hand_v = w.add_event(0, 1, "HANDLED", f_risky, c_risky, 4, {"exc": val})
    e_raise_r = w.add_event(0, 1, "RAISE", f_risky, c_risky, 6, {"exc": run})
    w.close_frame(f_risky, None, "unwind", run)
    e_hand_r = w.add_event(0, 1, "HANDLED", f_main, c_main, 11, {"exc": run})
    e_ret = w.add_event(0, 1, "RETURN", f_main, c_main, None, {"value": None})
    w.close_frame(f_main, e_ret, "return")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    # the ValueError was not re-raised as the RuntimeError, and was not
    # swallowed either -- exactly one thing is provable about it
    v_line = next(ln for ln in out.splitlines()
                  if f"e{e_raise_v} RAISE" in ln)
    v_verdict = out.splitlines()[out.splitlines().index(v_line) + 1]
    assert "unwound with RuntimeError" in v_verdict
    assert f"e{e_raise_r}" not in v_verdict     # not "raised again"
    # the RuntimeError is swallowed by main, credited to *its* handler
    assert f"SWALLOWED at e{e_hand_r}" in out
    assert f"SWALLOWED at e{e_hand_v}" not in out


def test_exceptions_pairs_repeats_that_share_type_message_and_oid(
        tmp_path, monkeypatch, capsys):
    """A loop whose exception address *is* reused: two raises with an
    identical (type, msg, oid). Each must be credited to its own handler,
    never a neighbour's.

    Fix round 1: the first raise now under-claims. Its handler frame returned,
    but a later RAISE carries its identity, and from the trace alone that is
    either address reuse (what actually happened here) or `return e`
    stored-and-re-raised. Under-claiming on the one is the price of never
    falsely accusing the other; the last raise, with nothing after it, is
    still reported as the swallow it is."""
    w = _synthetic(tmp_path, monkeypatch)
    c_boom = w.intern_code("/tmp/prog.py", "boom", 1)
    c_main = w.intern_code("/tmp/prog.py", "main", 5)
    e_call_main = w.add_event(0, 1, "CALL", None, c_main, 5, {"args": {}})
    f_main = w.open_frame(None, c_main, e_call_main, 0, 1)
    exc = _exc("ValueError", "same message", 4242)
    handlers = []
    for _ in range(2):
        e_call = w.add_event(0, 1, "CALL", None, c_boom, 1, {"args": {}})
        f_boom = w.open_frame(f_main, c_boom, e_call, 1, 1)
        w.add_event(0, 1, "RAISE", f_boom, c_boom, 2, {"exc": exc})
        w.close_frame(f_boom, None, "unwind", exc)
        handlers.append(
            w.add_event(0, 1, "HANDLED", f_main, c_main, 8, {"exc": exc}))
    e_ret = w.add_event(0, 1, "RETURN", f_main, c_main, None, {"value": None})
    w.close_frame(f_main, e_ret, "return")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "dispositions: swallowed 1, ambiguous 1" in out
    # each verdict cites its OWN handler -- the collision never lets one
    # raise be explained by the other's HANDLED row
    first, second = handlers
    assert f"handled at e{first} main L8 -- f1 returned normally" in out
    assert f"SWALLOWED at e{second}" in out
    assert f"SWALLOWED at e{first}" not in out


def test_exceptions_will_not_conclude_from_an_incomplete_recording(
        tmp_path, monkeypatch, capsys):
    """No finalize pass means no `uncaught` and no `exit_status`; absence of
    an uncaught record is then not evidence of anything."""
    w = _synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": _exc("ValueError", "x", 7)})
    w.set_meta("incomplete", True)              # never finalized
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "SWALLOWED" not in out
    assert "propagated (handler not in traced code)" not in out
    assert "cannot say" in out


def test_exceptions_limit_offers_an_exact_runnable_continuation(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, LOOP_SAME_MESSAGE)
    assert cli.main(["exceptions", run_id, "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 1
    assert "2 more; continue with:" in out
    hint = out.strip().splitlines()[-1].split("continue with: ", 1)[1]
    assert "eN" not in hint
    assert cli.main(shlex.split(hint)[1:]) == 0
    rest = capsys.readouterr().out
    assert rest.count("SWALLOWED") == 1           # --limit 1 also carried
    assert "1 more; continue with:" in rest
    assert "skipped by --after" in rest
    assert "swallowed 2" in rest                  # tally counts all in scope


def test_exceptions_rejects_a_nonpositive_limit(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["exceptions", run_id, "--limit", "0"]) == 2
    assert "--limit" in capsys.readouterr().out


# -- the remaining refusal branches ---------------------------------------
def test_exceptions_reports_no_handler_at_all_as_propagated(
        tmp_path, monkeypatch, capsys):
    """No `try` in traced code: the catch happens in the library frame, so
    there is no HANDLED row of any kind to reason from."""
    run_id = _rec(tmp_path, monkeypatch, RAISE_CAUGHT_UNTRACED,
                  extra=("--exclude", "lib.py"),
                  files=(("lib.py", UNTRACED_LIB_SOURCE),))
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "propagated (handler not in traced code)" in out
    assert "no HANDLED row for it anywhere" in out


def test_exceptions_reraise_with_no_handled_row_says_so(
        tmp_path, monkeypatch, capsys):
    w = _synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = _exc("ValueError", "boom", 11)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    second = w.add_event(0, 1, "RAISE", f, c, 5, {"exc": exc})
    w.close_frame(f, None, "unwind", exc)
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert f"raised again at e{second}" in out
    assert "no HANDLED row in between" in out


def test_exceptions_will_not_read_a_frame_that_never_closed(
        tmp_path, monkeypatch, capsys):
    """The process died with the handler's frame still on the stack: there
    is no closed_by, so there is no verdict."""
    w = _synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = _exc("ValueError", "boom", 12)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": exc})
    w.set_meta("incomplete", False)              # frame simply never closed
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert f"f{f} never closed" in out
    assert "cannot say what it did with the exception" in out


def test_exceptions_will_not_read_an_unwind_with_no_captured_exception(
        tmp_path, monkeypatch, capsys):
    w = _synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = _exc("ValueError", "boom", 13)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": exc})
    w.close_frame(f, None, "unwind", None)       # closed, but exc not captured
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "unwound with no captured exception" in out


def test_exceptions_incomplete_run_will_not_claim_propagation(
        tmp_path, monkeypatch, capsys):
    """The cleanup-HANDLED shape that would read as `propagated` in a
    finished run proves nothing when the recording was cut short."""
    w = _synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = _exc("ValueError", "boom", 14)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": exc})
    w.close_frame(f, None, "unwind", exc)
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "propagated (handler not in traced code)" not in out
    assert "unresolved" in out
    assert "no finalize pass" in out


def test_exceptions_incomplete_run_with_no_raises_does_not_say_none(
        tmp_path, monkeypatch, capsys):
    """"no exceptions recorded" would be a claim the trace cannot support."""
    w = _synthetic(tmp_path, monkeypatch)
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "no exceptions recorded" not in out
    assert "no RAISE events recorded" in out and "INCOMPLETE" in out


def test_grep_skips_events_with_no_code_object(tmp_path, monkeypatch, capsys):
    w = _synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "add", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    w.add_event(0, 1, "CALL", None, None, 1, {"args": {}})   # no code object
    w.close()

    assert cli.main(["grep", "20260101-000000-abcdef", "CALL"]) == 0
    out = capsys.readouterr().out
    assert "matches: 1" in out
    assert "scanned" not in out
