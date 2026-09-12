"""What a FOCUSED TypeScript recording converts into.

A third `test_ts_ingest` module, for the same reason there is a second: the
other two sit at their own 800-line ceiling. What is here is the focus tier
and nothing else -- the LINE row, the arguments a focused CALL carries, and
the three meta keys that say what the run was pointed at.

The fixture is `focus-lines`, and it is a RECORDING (`tests/ts_spools.py`
carries its provenance): the probe project's own `focus.probe.test.ts`
container, recorded under `probes/vitest.config.ts`'s eleven-spec focus. So
every number pinned below -- 50 LINE rows, twelve CALLs with arguments, the
`n=2` `letChain` was called with -- is a number the runtime wrote, not one
this file chose.
"""
import json

from sensorium.record.fingerprint import CAUSAL_KINDS, Fingerprint
from tests.helpers import run_cli
from tests.ts_spools import (CASES, FIXTURES, copy_tree, ingested,
                             only_trace)

__all__ = ["ingested"]      # a fixture, imported for pytest to find

CASE = "focus-lines"
SPOOL_FILE = "3264305-0.jsonl"
#: The `rel` every code object in the focused file carries, as the sanitized
#: FILE record spells it.
REL = "src/focus.probe.test.ts"


def _invocation() -> dict:
    return json.loads((FIXTURES / CASE / "invocation.json").read_text())


def _relative(path: str, root: str) -> str:
    return path[len(root) + 1:] if path.startswith(root + "/") else path


def _frame_named(trace, qualname: str):
    """The one frame whose code object is `qualname`, or an assertion."""
    codes = [c for c in trace.codes() if c.qualname == qualname]
    assert len(codes) == 1, [c.qualname for c in codes]
    frames = trace.frames(code_id=codes[0].id)
    assert len(frames) == 1, frames
    return frames[0]


def test_the_focused_case_is_one_of_the_cases_and_converts(ingested):
    """The fixture is driven by the same machinery as every other case --
    `test_ts_ingest.py` converts it and asks its questions -- and this is
    the assertion that it is actually IN that set. A case directory that
    lost its `invocation.json` would silently drop out of `CASES` and every
    question it pins would stop being asked."""
    assert CASE in CASES
    _spool, _sdir, result = ingested[CASE]
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"


# -- the LINE row ------------------------------------------------------------

def test_a_line_row_carries_the_line_it_ended_on_and_what_it_wrote(ingested):
    """`letChain`'s three statements, in order, as the probe's own `// LINE`
    markers write them down: the line each ended on and the delta each
    captured. A LINE is attached to its frame and to that frame's code
    object, like every other event in a frame."""
    _spool, sdir, _result = ingested[CASE]
    trace = only_trace(sdir)
    frame = _frame_named(trace, "letChain")
    rows = [e for e in trace.frame_events(frame.id) if e.kind == "LINE"]
    assert [e.line for e in rows] == [26, 28, 30]
    assert [e.payload["deltas"] for e in rows] == [
        {"base": {"k": "dbg", "v": "4", "trunc": False}},
        {"label": {"k": "dbg", "v": "'x'", "trunc": False}},
        {"label": {"k": "dbg", "v": "'x2'", "trunc": False}},
    ]
    assert all(e.code_id == frame.code_id for e in rows)
    assert all(e.frame_id == frame.id for e in rows)
    # Not a CALL's key, and never written empty beside deltas: a LINE that
    # unbound nothing says nothing about unbinding.
    assert all("unbound" not in e.payload for e in rows)
    assert all("unread" not in e.payload for e in rows)


def test_a_row_that_only_unbinds_a_name_says_so_with_empty_deltas(ingested):
    """`loopCounter`'s loop head, on the pass that ends the loop: `v` is out
    of scope and nothing was written. Empty deltas AND an `unbound` list is
    the shape -- a converter that dropped either would render the row as
    "nothing happened here"."""
    _spool, sdir, _result = ingested[CASE]
    trace = only_trace(sdir)
    frame = _frame_named(trace, "loopCounter")
    rows = [e for e in trace.frame_events(frame.id) if e.kind == "LINE"]
    last = rows[-1]
    assert last.line == 40
    assert last.payload == {"deltas": {}, "unbound": ["v"]}
    # The two head rows before it bound `v`, and carry no `unbound` at all.
    heads = [e for e in rows if e.line == 40]
    assert len(heads) == 3
    assert [e.payload["deltas"]["v"]["v"] for e in heads[:2]] == ["1", "2"]
    assert all("unbound" not in e.payload for e in heads[:2])


def test_every_line_row_the_runtime_wrote_is_a_row_in_the_trace(ingested):
    """50, counted in the spool and counted in the trace. The one number
    that catches a converter that silently drops a shape -- a `for…in` head,
    a `do…while` test, an `await`'s completion row."""
    spool, sdir, _result = ingested[CASE]
    wire = sum(1 for line in (spool / SPOOL_FILE).read_text().splitlines()
               if json.loads(line)["e"] == "LINE")
    assert wire == 50
    assert only_trace(sdir).counts()["LINE"] == 50


# -- the focused CALL's arguments --------------------------------------------

def test_a_focused_call_carries_its_arguments_and_no_unread_marker(ingested):
    """`a` on the wire becomes `args`, and the `unread: ["locals"]` marker
    that says nobody looked is ABSENT -- the whole point of a focus is that
    somebody did."""
    _spool, sdir, _result = ingested[CASE]
    trace = only_trace(sdir)
    call = trace.event(_frame_named(trace, "letChain").call_event_id)
    assert call.payload["args"] == {
        "n": {"k": "dbg", "v": "2", "trunc": False}}
    assert "unread" not in call.payload


def test_an_unfocused_call_in_the_same_container_still_says_nobody_looked(
        ingested):
    """The eleven test callbacks in this file are not focused, and their
    CALLs carry no `a`. They keep the marker every unfocused TypeScript CALL
    has always carried: an empty `args` there would be a positive claim that
    the function took none."""
    _spool, sdir, _result = ingested[CASE]
    trace = only_trace(sdir)
    unfocused = [e for e in trace.events(kind="CALL")
                 if trace.code(e.code_id).qualname == "<anonymous>"
                 and trace.code(e.code_id).file.endswith(REL)]
    assert len(unfocused) == 11
    for call in unfocused:
        assert call.payload["args"] == {}
        assert call.payload["unread"] == ["locals"]


def test_the_container_focused_twelve_functions_and_twelve_calls_say_so(
        ingested):
    """One CALL with arguments per focused activation, and every one of them
    a function the tally counted."""
    _spool, sdir, _result = ingested[CASE]
    trace = only_trace(sdir)
    with_args = [e for e in trace.events(kind="CALL") if e.payload["args"]]
    # `catchBinding()` takes no argument at all: it is focused, its `a` is an
    # empty map, and that is a READ that found nothing -- not an unread.
    read = [e for e in trace.events(kind="CALL")
            if "unread" not in e.payload]
    assert len(with_args) == 11 and len(read) == 12
    assert trace.meta["functions_focused"] == 12


# -- the meta keys -----------------------------------------------------------

def test_the_trace_says_where_the_project_root_was(ingested):
    """P9: every relative path in this trace is relative to `meta.root`, and
    a reader on another box cannot re-anchor them without it."""
    _spool, sdir, _result = ingested[CASE]
    assert only_trace(sdir).meta["root"] == _invocation()["root"]


def test_the_trace_says_what_was_focused_as_typed_and_as_matched(ingested):
    """Both, because they answer different questions. `focus` is what the
    caller wrote, which is what they will recognise; `focus_matched` is what
    it selected, which is what says whether it meant what they thought --
    here eleven specs that selected twelve functions, the callback the
    eleventh defines among them."""
    _spool, sdir, _result = ingested[CASE]
    inv = _invocation()
    meta = only_trace(sdir).meta
    assert meta["focus"] == inv["focus"]
    assert len(meta["focus"]) == 11
    assert meta["focus_matched"] == inv["focus_matched"]
    assert f"{REL}:nestedArrow.double" in meta["focus_matched"]


def test_the_trace_declares_the_line_and_locals_the_runtime_witnessed(
        ingested):
    """The BOOT record's own four-key declaration, carried into meta over
    the converter's floor. Without it every reader would treat the 50 rows
    below as rows a recorder that declares no `line` should not have."""
    _spool, sdir, _result = ingested[CASE]
    caps = only_trace(sdir).meta["capabilities"]
    assert caps["line"] is True and caps["locals"] is True
    assert caps["err_flow"] is True and caps["object_identity"] is True


def test_an_unfocused_run_writes_the_root_and_neither_focus_key(ingested):
    """The other side of the same rule: a spool directory whose
    `invocation.json` names no focus gets no `focus` key at all, because an
    empty list there is a run that focused nothing rather than a run nobody
    focused -- and `info` prints those two differently."""
    _spool, sdir, _result = ingested["async-chain"]
    meta = only_trace(sdir).meta
    assert meta["root"] == "/w/probes"
    assert "focus" not in meta and "focus_matched" not in meta


def test_a_run_whose_tally_never_counted_focused_functions_says_nothing(
        ingested):
    """`functions_focused` follows `files_transformed`: written only where
    somebody counted (R22, R38). `async-chain`'s tally predates the key."""
    _spool, sdir, _result = ingested["async-chain"]
    meta = only_trace(sdir).meta
    assert meta["files_transformed"] == 12
    assert "functions_focused" not in meta


# -- what a LINE is NOT ------------------------------------------------------

def test_a_line_row_is_not_causal_and_enters_no_fingerprint(ingested):
    """Spec section 4: a fingerprint hashes the CALL/RETURN/RAISE/HANDLED
    sequence, so capture depth can never change it. Rebuilt here over every
    causal event of the focused task and compared to what the converter
    wrote -- with the task's LINE rows asserted present, so this cannot pass
    by there being nothing to exclude."""
    _spool, sdir, _result = ingested[CASE]
    trace = only_trace(sdir)
    root = _invocation()["root"]
    fps = trace.task_fingerprints()
    assert fps
    for task_id, (_name, digest, count) in fps.items():
        rebuilt = Fingerprint()
        for e in trace.events():
            if e.task_id != task_id or e.kind not in CAUSAL_KINDS:
                continue
            code = trace.code(e.code_id)
            rebuilt.update(_relative(code.file, root), code.qualname, e.kind)
        assert (rebuilt.hexdigest(), rebuilt.count) == (digest, count), task_id
    lines = [e for e in trace.events(kind="LINE") if e.task_id is not None]
    assert len(lines) == 50


def test_a_line_naming_a_frame_that_had_already_closed_is_refused(tmp_path):
    """A LINE arriving for a frame that has RETURNed is not a statement of
    that frame -- the runtime's own `line()` drops it, so a spool carrying
    one was edited or is corrupt. Refused by name, like every other record
    this converter cannot place, and the spools beside it convert anyway."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    path = spool / SPOOL_FILE
    lines = path.read_text().splitlines()
    closed = None
    for i, text in enumerate(lines):
        rec = json.loads(text)
        if rec["e"] == "RETURN" and closed is None:
            closed = rec["f"]            # the first frame to close
        elif rec["e"] == "LINE" and closed is not None and rec["f"] != closed:
            rec["f"] = closed
            lines[i] = json.dumps(rec)
            break
    else:                                               # pragma: no cover
        raise AssertionError("no LINE after the first RETURN")
    path.write_text("\n".join(lines) + "\n")

    sdir = tmp_path / "sdir"
    result = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                     sensorium_dir=sdir)
    assert result.returncode == 2, f"{result.stdout}{result.stderr}"
    refused = [ln for ln in result.stdout.splitlines()
               if ln.startswith("refused: ")]
    assert len(refused) == 1, result.stdout
    assert refused[0].endswith(
        f"{SPOOL_FILE}: a LINE names frame {closed}, which had already "
        "closed"), refused[0]
    # The one spool in the directory refused, so nothing was written: a
    # reader is never shown a recording this converter would not finish.
    assert not list((sdir / "traces").glob("*.db"))
