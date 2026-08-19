"""Exception identity: what the recorder can and cannot prove is one object.

Split out of `test_exceptions.py` at that file's 800-line ceiling, along the
seam the material actually has: these shapes are not about which verdict a
handler earns but about whether two rows are the same exception at all. Three
fix rounds of false accusations all reduced to that question, and every shape
here is one the recorder's identity machinery gets right or is forced to
admit it cannot answer.

The recorder-side halves live in `test_tracer.py` (serials, the retention
table and its bound); these assert what `sensorium exceptions` may say once
identity is exact, lost, or bounded away.
"""
from sensorium import cli, paths
from sensorium.store.reader import Trace
from tests.programs import (
    CLEANUP_RAISES_ITS_OWN, IN_FLIGHT_PAST_RETENTION, RETENTION_NOISE_COUNT,
    STASH_AND_RERAISE, STASH_NOISE_RERAISE, STASH_PAST_RETENTION, exc_payload,
    record, synthetic)


def _verdict_under(out: str, event_id: int) -> str:
    """The verdict line printed under RAISE event `event_id`."""
    lines = out.splitlines()
    i = next(n for n, ln in enumerate(lines) if ln.startswith(f"  e{event_id} "))
    return lines[i + 1]


def test_exceptions_keeps_a_stash_linked_across_an_unrelated_exception(
        tmp_path, monkeypatch, capsys):
    """Fix round 4's Critical. One stored exception, one unrelated exception
    handled in between, and then the stash is raised. The recorder must still
    recognise the object -- a single last-handled slot loses it, mints a second
    serial, and the classifier then reports SWALLOWED for an exception its own
    header says left the program."""
    run_id = record(tmp_path, monkeypatch, STASH_NOISE_RERAISE)
    trace = Trace.open(paths.find_trace(run_id))
    vals = [e for e in trace.events(kind="RAISE")
            if e.payload["exc"]["type"] == "ValueError"]
    assert len(vals) == 2
    assert len({v.payload["exc"]["serial"] for v in vals}) == 1, (
        "one object must keep one serial across the intervening RuntimeError")
    # and the interloper really did arm and get handled in between
    noise = [e for e in trace.events(kind="HANDLED")
             if e.payload["exc"]["type"] == "RuntimeError"]
    assert len(noise) == 1 and vals[0].id < noise[0].id < vals[1].id

    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("uncaught: ValueError('x')")
    verdict = _verdict_under(out, vals[0].id)
    assert "SWALLOWED" not in verdict and "never re-raised" not in verdict
    assert "returned normally -- then raised again at e" in verdict
    assert out.count("SWALLOWED") == 1            # only noise() swallows
    assert "dispositions: swallowed 1, uncaught 1, re-raised 1" in out


def test_exceptions_serial_survives_a_raise_inside_cleanup(
        tmp_path, monkeypatch, capsys):
    """The mirror of the above: nothing is stored, but a `finally` raises and
    handles an exception of its own while another is still in flight. With one
    "current serial" slot the interloper's serial was stamped onto the outer
    exception's later rows, and the classifier read the outer exception's own
    unwind as some other exception displacing it."""
    run_id = record(tmp_path, monkeypatch, CLEANUP_RAISES_ITS_OWN)
    trace = Trace.open(paths.find_trace(run_id))
    serials = {}
    for e in trace.events(kind="RAISE") + trace.events(kind="HANDLED"):
        serials.setdefault(e.payload["exc"]["type"], set()).add(
            e.payload["exc"]["serial"])
    # the shape needs the interloper to have really run inside the flight
    assert set(serials) == {"ValueError", "KeyError"}
    assert len(serials["ValueError"]) == 1, "one object, one serial"
    assert not serials["ValueError"] & serials["KeyError"]

    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    # the old self-contradiction: the frame "then unwound with" the very
    # exception whose fate was being explained
    assert "unwound with ValueError('outer')" not in out
    caught = [h for h in trace.events(kind="HANDLED")
              if h.payload["exc"]["type"] == "ValueError"][-1]
    assert (f"SWALLOWED at e{caught.id} main L16 -- caught in f2, which "
            "returned normally; never re-raised") in out
    assert "dispositions: swallowed 2" in out


def test_exceptions_will_not_call_a_forgotten_stash_swallowed(
        tmp_path, monkeypatch, capsys):
    """Past the recorder's retention bound the link is genuinely gone: the
    same object is raised again under a fresh serial. The recorder cannot fix
    that -- retention is bounded on purpose -- so the classifier must refuse
    the swallow verdict rather than hand back the round-3 false accusation
    with a higher price of admission."""
    run_id = record(tmp_path, monkeypatch, STASH_PAST_RETENTION)
    trace = Trace.open(paths.find_trace(run_id))
    kept = [e for e in trace.events(kind="RAISE")
            if e.payload["exc"]["type"] == "ValueError"]
    assert len(kept) == 2
    first, second = (e.payload["exc"] for e in kept)
    # the coincidence this test rests on: provably one object (it was stashed
    # in a local and raised again), and the recorder really did lose the link
    assert first["oid"] == second["oid"]
    assert first["serial"] != second["serial"], (
        "the retention bound was not exceeded; this shape tests nothing")

    assert cli.main(["exceptions", run_id, "--limit", "200"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("uncaught: ValueError('kept')")
    verdict = _verdict_under(out, kept[0].id)
    assert "SWALLOWED" not in verdict and "never re-raised" not in verdict
    assert ("same exception type at the same address under a different "
            "recorder identity") in verdict
    assert "the trace cannot tell them apart" in out
    assert (f"dispositions: swallowed {RETENTION_NOISE_COUNT}, uncaught 1, "
            "ambiguous 1") in out


def test_exceptions_will_not_deny_an_unwind_it_can_no_longer_link(
        tmp_path, monkeypatch, capsys):
    """The retention bound crossed from the other side. A long cleanup pushes
    the exception it is cleaning up out of the recorder's table, so the frame
    that exception leaves carries a fresh serial for it. Calling that "some
    other exception" would deny -- of the very exception being named -- that it
    left the frame."""
    run_id = record(tmp_path, monkeypatch, IN_FLIGHT_PAST_RETENTION)
    trace = Trace.open(paths.find_trace(run_id))
    raised = [e for e in trace.events(kind="RAISE")
              if e.payload["exc"]["type"] == "ValueError"]
    assert len(raised) == 1
    unwound = [f.unwind_exc for f in trace.frames()
               if f.unwind_exc and f.unwind_exc["type"] == "ValueError"]
    assert len(unwound) == 1
    # the coincidence this test rests on: one object, and the link really lost
    assert unwound[0]["oid"] == raised[0].payload["exc"]["oid"]
    assert unwound[0]["serial"] != raised[0].payload["exc"]["serial"], (
        "the retention bound was not exceeded; this shape tests nothing")

    assert cli.main(["exceptions", run_id, "--limit", "200"]) == 0
    out = capsys.readouterr().out
    verdict = _verdict_under(out, raised[0].id)
    assert "at this exception's address under a different recorder identity" \
        in verdict
    assert "did not leave f" not in out          # the false denial
    assert "cannot say whether that is this same exception" in out
    assert (f"dispositions: swallowed {RETENTION_NOISE_COUNT}, "
            "ambiguous 1") in out


def test_exceptions_never_calls_an_escaping_object_swallowed(
        tmp_path, monkeypatch, capsys):
    """Per-object form of the header invariant, which is what the round-3
    regression needed: a run may legitimately contain swallows, so the check
    that bites is on the verdict of every RAISE carrying the *escaping
    object's* address -- whatever serial the recorder gave it."""
    for name, src in (("stash", STASH_AND_RERAISE),
                      ("noise", STASH_NOISE_RERAISE),
                      ("forgotten", STASH_PAST_RETENTION)):
        run_id = record(tmp_path / name, monkeypatch, src)
        trace = Trace.open(paths.find_trace(run_id))
        oid = trace.meta["uncaught"]["oid"]
        rows = [e for e in trace.events(kind="RAISE")
                if e.payload["exc"]["oid"] == oid]
        assert len(rows) == 2, name          # raised, stored, raised again
        assert cli.main(["exceptions", run_id, "--limit", "200"]) == 0
        out = capsys.readouterr().out
        for r in rows:
            verdict = _verdict_under(out, r.id)
            assert "SWALLOWED" not in verdict, (name, verdict)
            assert "never re-raised" not in verdict, (name, verdict)




def test_exceptions_reused_address_with_a_different_type_is_still_a_swallow(
        tmp_path, monkeypatch, capsys):
    """The other half of the address check, and the reason it is not on the
    address alone: a type never changes, so a later raise of a DIFFERENT type
    at this address cannot be this object however far the recorder's memory
    ran. Hedging there would trade a false accusation for a needless refusal.

    Synthetic because the recorder pins an address for as long as it remembers
    the object, so a natural trace only recycles one after the bound is
    exceeded -- and which address CPython then hands out is not a thing to
    build an assertion on."""
    w = synthetic(tmp_path, monkeypatch)
    c_risky = w.intern_code("/tmp/prog.py", "risky", 1)
    c_main = w.intern_code("/tmp/prog.py", "main", 8)
    e_call_main = w.add_event(0, 1, "CALL", None, c_main, 8, {"args": {}})
    f_main = w.open_frame(None, c_main, e_call_main, 0, 1)
    val = exc_payload("ValueError", "boom", 999, serial=1)
    run = exc_payload("RuntimeError", "later", 999, serial=2)   # same address
    w.add_event(0, 1, "RAISE", f_main, c_risky, 3, {"exc": val})
    hand = w.add_event(0, 1, "HANDLED", f_main, c_main, 9, {"exc": val})
    w.add_event(0, 1, "RAISE", f_main, c_risky, 11, {"exc": run})
    w.add_event(0, 1, "HANDLED", f_main, c_main, 12, {"exc": run})
    e_ret = w.add_event(0, 1, "RETURN", f_main, c_main, None, {"value": None})
    w.close_frame(f_main, e_ret, "return")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert f"SWALLOWED at e{hand} main L9" in out
    assert "different recorder identity" not in out
    assert "dispositions: swallowed 2" in out
