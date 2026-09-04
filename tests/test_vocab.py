"""No Python word is printed about a trace no Python recorded.

Rung 1 measured the failure this file exists to stop. Verbatim from
`sensorium info` and `sensorium diff` on a real `sensorium-rt` trace:
`python ?`; "0 causal events outside any **asyncio** task"; "threads
started: 26 besides the main one, **through Python's own
threading/_thread**". The last of those is a positive claim about
provenance the trace does not carry, and the first names an interpreter
that never ran -- so this is a correctness suite, not a style one.

The vectors pin the SENTENCES (`v13-lang-keyed-prose` asks for the Rust
words by name). This file pins the ABSENCE across every Rust-shaped
vector in the contract and every command that can reach one, so a
renderer added later cannot reintroduce a Python word at a site no vector
happens to ask about.
"""
import shutil

import pytest

from sensorium.query.vocab import (PYTHON, RUST, exit_brief,
                                   exit_phrase, terms)
from sensorium.store.reader import Trace
from tests.helpers import run_cli
from tests.vectors import build, load_all

# The words that are true of a Python recording and of nothing else. Each
# one was printed about a Rust trace before this arc (findings 5.5).
FORBIDDEN = ("asyncio", "Python's own", "threading/_thread", "coroutine",
             "generator", "python ?")

RUN_IDS = ["20260101-000000-aaaaaa", "20260101-000001-bbbbbb"]

RUST_VECTORS = [v for v in load_all() if v["meta"].get("lang") == "rust"]

# Every command of the rung-2 six, instantiated against a built vector.
# `grep ""` matches every rendered line, which is the widest net this
# command can cast over one trace.
COMMANDS = (
    ["runs"],
    ["info", RUN_IDS[0]],
    ["tree", RUN_IDS[0]],
    ["frame", RUN_IDS[0], "--fn", "main"],
    ["grep", RUN_IDS[0], ""],
    ["diff", RUN_IDS[0], RUN_IDS[1]],
)


def _build_two(vector, tmp_path):
    """One vector on disk twice, so `diff` and `runs` have something to do."""
    sdir = tmp_path / "sdir"
    path = build(vector, sdir, RUN_IDS)
    shutil.copy(path, path.with_name(f"{RUN_IDS[1]}.db"))
    return sdir


@pytest.mark.parametrize("vector", RUST_VECTORS,
                         ids=[v["id"] for v in RUST_VECTORS])
@pytest.mark.parametrize("command", COMMANDS, ids=[c[0] for c in COMMANDS])
def test_no_python_word_reaches_a_rust_trace(vector, command, tmp_path):
    sdir = _build_two(vector, tmp_path)
    r = run_cli(command, cwd=tmp_path, sensorium_dir=sdir)
    text = r.stdout + r.stderr
    found = [w for w in FORBIDDEN if w in text]
    assert not found, (f"{vector['id']} / {' '.join(command)}: {found}\n"
                       f"{text}")


def test_the_rust_vectors_actually_exercise_these_commands():
    """A guard on the guard: if `load_all` stopped returning Rust vectors,
    or the ids changed, every test above would pass by having nothing to
    check. The count is a floor, not a pin -- adding vectors is fine."""
    ids = {v["id"] for v in RUST_VECTORS}
    assert len(ids) >= 12, ids
    for wanted in ("v08-return-outcome-dbg-value", "v13-lang-keyed-prose",
                   "v14-rust-refusals"):
        assert wanted in ids, ids


def test_python_terms_are_the_words_the_readers_printed_before():
    """The Python half of the table is a MOVE, never a rewrite: these are
    the exact strings `info`, `tree` and `diff` printed before `vocab`
    existed, and the whole legacy suite is the fence around them."""
    assert PYTHON.task_noun == "asyncio task"
    assert PYTHON.a_task == "an asyncio task"
    assert PYTHON.thread_origin == "through Python's own threading/_thread"
    assert PYTHON.unnamed_task == "(name unreadable)"
    assert PYTHON.interp_line({"python": "3.14.4"}) == "python 3.14.4"
    assert PYTHON.interp_line({}) == "python ?"


def test_rust_terms_name_what_a_rust_trace_actually_has():
    assert RUST.task_noun == "test or spawned thread"
    assert RUST.a_task == "a test or spawned thread"
    assert RUST.unnamed_task == "(unnamed: spawned by dependency code)"
    assert RUST.default_name_note is None, (
        "Rust mints no default names: there is no note to print")
    assert RUST.interp_line({"toolchain": "rustc 1.96.0"}) \
        == "toolchain: rustc 1.96.0"


def test_terms_are_chosen_by_the_trace_and_not_by_the_caller(tmp_path):
    """`terms()` reads `meta["lang"]`. A trace with no `lang` key at all is
    the Python recorder's -- nothing else existed before the key."""
    rust = _rust_vector()
    t = Trace.open(build(rust, tmp_path / "r", RUN_IDS))
    assert terms(t) is RUST
    py = {**rust, "meta": {**rust["meta"], "lang": "python"}}
    t2 = Trace.open(build(py, tmp_path / "p", RUN_IDS))
    assert terms(t2) is PYTHON


_UNREAD_VECTOR = "v12-call-unread-marker-in-tree-and-frame"


def _rust_vector():
    return next(v for v in RUST_VECTORS if v["id"] == _UNREAD_VECTOR)


def test_exit_phrase_reads_the_basis_and_never_invents_a_status():
    """The four shapes `info` and `runs` can print. A Python trace has no
    basis key and renders exactly as it always did -- including the `?` of
    a run that never finalized, which is not a status."""
    assert exit_phrase({"exit_status": 0}) == "0"
    assert exit_phrase({}) == "?"
    assert exit_phrase({"exit_status": 0,
                        "exit_status_basis": "waited"}) == "0 (waited)"
    assert exit_phrase({"exit_status": 101,
                        "exit_status_basis": "waited"}) == "101 (waited)"
    assert exit_phrase({"exit_status": None, "exit_signal": 9,
                        "exit_status_basis": "waited"}) == "signal 9 (waited)"
    assert exit_phrase({"exit_status": None, "exit_signal": None,
                        "exit_status_basis": "unwitnessed"}) == "unwitnessed"
    # A signalled process nobody waited on: the basis wins. Printing
    # "signal 9" here would claim a witness that does not exist.
    assert exit_phrase({"exit_status": None, "exit_signal": 9,
                        "exit_status_basis": "unwitnessed"}) == "unwitnessed"


def test_exit_brief_is_the_status_without_the_basis():
    """What `runs` prints. `unwitnessed` keeps its whole word -- there the
    basis IS the answer, so nothing is shortened away."""
    assert exit_brief({"exit_status": 0}) == "0"
    assert exit_brief({}) == "?"
    assert exit_brief({"exit_status": 0,
                       "exit_status_basis": "waited"}) == "0"
    assert exit_brief({"exit_status": None, "exit_signal": 9,
                       "exit_status_basis": "waited"}) == "signal 9"
    assert exit_brief({"exit_status": None,
                       "exit_status_basis": "unwitnessed"}) == "unwitnessed"


def test_a_signalled_exit_is_printed_by_info_and_runs(tmp_path):
    """The signalled arm of `v10-exit-status-unwitnessed`'s rule, which one
    vector cannot carry: a vector describes ONE trace, and the unwitnessed
    and signalled shapes are two different `meta` dicts. Built with the same
    builder and run through the same real CLI as a vector."""
    base = next(v for v in RUST_VECTORS
                if v["id"] == "v10-exit-status-unwitnessed")
    killed = {**base, "meta": {**base["meta"], "exit_status": None,
                               "exit_signal": 9,
                               "exit_status_basis": "waited"}}
    sdir = _build_two(killed, tmp_path)
    info = run_cli(["info", RUN_IDS[0]], cwd=tmp_path, sensorium_dir=sdir)
    assert "exit: signal 9 (waited)" in info.stdout, info.stdout
    assert "exit: None" not in info.stdout
    # The listing prints the bare form: one dense row per trace, and the
    # basis is `info`'s to explain.
    runs = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    assert "exit:signal 9  " in runs.stdout, runs.stdout
    assert "(waited)" not in runs.stdout, runs.stdout
