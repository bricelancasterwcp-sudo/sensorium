"""No Python word is printed about a trace no Python recorded.

Rung 1 measured the failure this file exists to stop. Verbatim from
`sensorium info` and `sensorium diff` on a real `sensorium-rt` trace:
`python ?`; "0 causal events outside any **asyncio** task"; "threads
started: 26 besides the main one, **through Python's own
threading/_thread**". The last of those is a positive claim about
provenance the trace does not carry, and the first names an interpreter
that never ran -- so this is a correctness suite, not a style one.

The vectors pin the SENTENCES (`v13-lang-keyed-prose` asks for the Rust
words by name, `v23-lang-typescript-prose` the TypeScript ones). This file
pins the ABSENCE across every Rust-shaped and every TypeScript-shaped
vector in the contract and every command that can reach one, so a
renderer added later cannot reintroduce another language's word at a site
no vector happens to ask about.

Two scans, two forbidden lists, and they are NOT the same list. What is
forbidden is what would be a false claim about THAT recording: `cargo` and
`libtest` are true of a Rust trace and are lies on a TypeScript one, and
`generator` is a Python word on a Rust trace and JavaScript's own word on
a TypeScript one -- `[generator]` is what a `function*` frame must print.
A shared list would have to drop every word one language legitimately
uses, which is how a scan quietly stops scanning.
"""
import argparse
import shutil
from dataclasses import MISSING, fields

import pytest

from sensorium import cli
from tests.rust_traces import focused_trace

from sensorium.query.vocab import (PYTHON, RUST, TYPESCRIPT, Terms,
                                   exit_brief, exit_phrase, terms)
from sensorium.store.reader import Trace
from sensorium.ts import cli as ts_cli
from tests.helpers import run_cli
from tests.vectors import build, load_all

# The words that are true of a Python recording and of nothing else. Each
# one was printed about a Rust trace before this arc (findings 5.5).
FORBIDDEN = ("asyncio", "Python's own", "threading/_thread", "coroutine",
             "generator", "python ?")

RUN_IDS = ["20260101-000000-aaaaaa", "20260101-000001-bbbbbb"]

RUST_VECTORS = [v for v in load_all() if v["meta"].get("lang") == "rust"]

# The words that would be a false claim about a TypeScript recording. The
# first five are Python's (`generator` is deliberately NOT among them: see
# the module header); the last five are Rust's and this recorder's own
# refusals' -- `cargo` and `libtest` name machinery that never ran,
# `toolchain:` is the interpreter line of a compiler that was never
# invoked, `Rust disposition` was the sentence `exceptions` printed at any
# non-Python trace before S5, and `sensorium run --focus` sends the reader
# to a recorder that cannot read this trace.
FORBIDDEN_TS = ("asyncio", "Python's own", "threading/_thread", "coroutine",
                "python ?", "cargo", "Rust disposition", "toolchain:",
                "sensorium run --focus", "libtest")

TS_VECTORS = [v for v in load_all()
              if v["meta"].get("lang") == "typescript"]

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


@pytest.mark.parametrize("vector", TS_VECTORS,
                         ids=[v["id"] for v in TS_VECTORS])
@pytest.mark.parametrize("command", COMMANDS, ids=[c[0] for c in COMMANDS])
def test_no_other_language_s_word_reaches_a_typescript_trace(
        vector, command, tmp_path):
    """The same scan, one language further out.

    The spike measured every one of these on a real converted TypeScript
    trace before this task: `python ?` on the interpreter line, "outside
    any asyncio task", `invocation ...: cargo`, `[coroutine]` on an `async
    function`, and `exceptions` refusing because the trace "needs the Rust
    disposition rules". Each is a claim about machinery that never ran.
    """
    sdir = _build_two(vector, tmp_path)
    r = run_cli(command, cwd=tmp_path, sensorium_dir=sdir)
    text = r.stdout + r.stderr
    found = [w for w in FORBIDDEN_TS if w in text]
    assert not found, (f"{vector['id']} / {' '.join(command)}: {found}\n"
                       f"{text}")


def _every_parser(sub):
    """Every parser under `sub`, its own nested subcommands included.

    `sensorium ts` has a second level (`ts run`, `ts ingest`), and a flat
    walk of `sub.choices` scans the group's one-line help and none of the
    text a reader actually meets when they type `sensorium ts run --help`.
    """
    for name, parser in sub.choices.items():
        yield name, parser
        for action in parser._subparsers._group_actions if \
                parser._subparsers else ():
            for sub_name, sub_parser in action.choices.items():
                yield f"{name} {sub_name}", sub_parser


def test_no_python_word_reaches_a_subcommand_s_own_help():
    """The scan above drives commands against a TRACE; `--help` answers
    before any trace is opened, and nothing scanned it.

    `diff --task` read "compare one asyncio task's stream by name" -- the
    one help string in the tool that named a language, printed to whoever
    typed `sensorium diff --help` on a box whose only recordings are Rust.
    A help text has no trace to take `terms()` from, so the repair is not a
    second table: it is the word that belongs to no recorder, `task`, which
    is the wire's own (the `tasks` table), with `info` named as the place a
    reader learns what one IS for the run in hand.

    Extended 2026-09-09 (S5) to the `ts` group and its two subcommands,
    which a flat walk of `sub.choices` never reached: `sensorium ts run
    --help` is the longest help text in the tool and was scanned by
    nothing. Both lists are applied, because a help string has no trace and
    so belongs to no recorder: a word forbidden of either language's traces
    is forbidden of every help text.
    """
    parser = argparse.ArgumentParser(prog="sensorium")
    sub = parser.add_subparsers(dest="cmd", required=True)
    cli._add_run_parser(sub)
    ts_cli.add_parser(sub)
    for mod in cli._QUERY_MODULES:
        mod.add_parser(sub)
    scanned = dict(_every_parser(sub))
    assert len(scanned) >= 14, scanned            # the guard on the guard
    for expected in ("ts", "ts run", "ts ingest"):
        assert expected in scanned, scanned
    for name, p in scanned.items():
        text = p.format_help()
        found = [w for w in FORBIDDEN + FORBIDDEN_TS if w in text]
        assert not found, f"{name} --help: {found}\n{text}"


def test_the_interpreter_line_says_question_mark_for_a_key_it_cannot_read():
    """`interp_line`'s `or "?"`, on both tables and in both shapes it has.

    `.get(key, "?")` would cover the ABSENT key alone. The `or` also covers
    a key that is PRESENT and empty -- a converter that wrote the field and
    had nothing to put in it -- and that branch had no fixture. The reader
    never substitutes an interpreter of its own in either case.
    """
    for table, key, absent in ((PYTHON, "python", "python ?"),
                               (RUST, "toolchain", "toolchain: ?"),
                               (TYPESCRIPT, "node", "node ?")):
        assert table.interp_line({}) == absent
        assert table.interp_line({key: ""}) == absent
        assert table.interp_line({key: None}) == absent


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


def test_typescript_terms_name_what_a_typescript_trace_has():
    """The third column, against `typescript/HONESTY.md`.

    Every string here is a fact about what a `sensorium-ts` trace holds,
    and three of them are facts about what it does NOT: this recorder
    starts no thread of its own (`harness_thread is None` -- nothing is
    ever excluded from a count of the program's threads), vitest mints no
    default name to be read as no name (`default_name_note is None`), and
    an unnamed task is unnamed because the TITLE was not a string, which is
    a different fact from Python's "the name existed and `get_name()`
    raised".
    """
    assert TYPESCRIPT.task_noun == "test"
    assert TYPESCRIPT.a_task == "a test"
    assert TYPESCRIPT.task_noun_plural == "test(s)"
    assert TYPESCRIPT.stream_scope == "tests"
    assert TYPESCRIPT.blind_spot_tasks == "tests"
    assert TYPESCRIPT.unnamed_task == "(unnamed: title not a string)"
    assert TYPESCRIPT.harness_thread is None, (
        "this recorder starts no thread of its own: nothing may be "
        "excluded from a count of the program's threads")
    assert TYPESCRIPT.default_name_note is None, (
        "vitest mints no default names: there is no note to print")
    assert TYPESCRIPT.interp_line({"node": "v24.16.0"}) == "node v24.16.0"
    # JavaScript's words for the contract's kinds -- and `generator` is
    # deliberately not renamed, because it is already JavaScript's own.
    assert TYPESCRIPT.kind_labels == {"coroutine": "async",
                                      "async_generator": "async generator"}
    assert "generator" not in TYPESCRIPT.kind_labels
    assert TYPESCRIPT.exceptions_refusal is None, (
        "this column carried a refusal naming the rules the throw-flow "
        "rung owed; that rung shipped them, and a TypeScript trace is now "
        "dispatched to `exceptions_typescript` before `_language_refusal` "
        "is read")


def test_no_language_with_rules_carries_an_exceptions_refusal():
    """Python's rules ARE this command's, and Rust and TypeScript are each
    dispatched to their own rule module before the refusal is ever read
    (design R9, and the throw-flow rung for the third). A refusal on any of
    the three columns would be a sentence printed about a trace that can be
    judged -- an 0.1.x recording of either of the two is refused through
    `capabilities.err_flow` instead, which is a fact about the RECORD.

    The field itself stays: a fourth language will have words before it has
    rules, and this is the sentence it gets in the meantime.
    """
    assert PYTHON.exceptions_refusal is None
    assert RUST.exceptions_refusal is None
    assert TYPESCRIPT.exceptions_refusal is None
    assert PYTHON.kind_labels == {} and RUST.kind_labels == {}, (
        "the contract's kind words are already these two languages' own; a "
        "mapping here would reword markers the legacy suite pins")


def test_terms_refuses_a_language_it_has_no_column_for():
    """Strict since S5. The fallback this replaces returned the PYTHON
    column for any unknown `lang`, which told a reader of such a trace
    about `asyncio tasks` and `python ?` -- the rung-1 bug one language
    further out. Nothing reachable through the CLI gets here (the store
    refuses the trace at open), so the raise is a programming error and
    not a user-facing path."""
    class _Fake:
        lang = "cobol"
    with pytest.raises(KeyError):
        terms(_Fake())


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


def test_a_harness_key_on_another_language_s_trace_is_not_read(tmp_path):
    """`vitest` and `environment` are ONE recorder's keys, and `info`'s
    interpreter parenthesis is gated on the trace's language, not on the
    keys being present. A Rust trace that happened to carry them -- a
    converter reusing a name, a hand-edited fixture -- must still print
    `toolchain: ...` and nothing else: reading another recorder's key off
    this trace is the same class of error as reading another recorder's
    WORD off it, which is what this whole file is about."""
    base = _rust_vector()
    dressed = {**base, "meta": {**base["meta"], "vitest": "4.1.9",
                                "environment": "jsdom"}}
    sdir = _build_two(dressed, tmp_path)
    r = run_cli(["info", RUN_IDS[0]], cwd=tmp_path, sensorium_dir=sdir)
    assert "toolchain: " in r.stdout, r.stdout
    assert "vitest" not in r.stdout and "jsdom" not in r.stdout, r.stdout


def test_runs_reads_the_language_and_never_sniffs_for_a_key(tmp_path):
    """R27a. `info` has always chosen its language blocks by `trace.lang`;
    `runs` shipped choosing its header by the presence of `harness` and its
    member line by the presence of `test_file`.

    A key name is not a recorder's signature. A Rust trace that carried
    either -- a converter reusing a name, a hand-edited fixture, a future
    recorder with a `harness` of its own -- would have been headed by a
    TypeScript header and listed by a file it never ran, which is the same
    class of error as reading another recorder's WORD off it. Two commands
    over one trace must not disagree about who wrote it.
    """
    # A Rust vector that carries an `invocation`, so `runs` really does
    # reach the header branch: without one every row is listed in place.
    base = next(v for v in RUST_VECTORS if v["id"] == "v13-lang-keyed-prose")
    dressed = {**base, "meta": {**base["meta"],
                                "harness": "vitest",
                                "harness_args": ["run"],
                                "harness_command": ["npx", "vitest", "run"],
                                "harness_exit": {"status": 1, "signal": None,
                                                 "basis": "waited"},
                                "test_file": "src/fog/compute.test.ts"}}
    sdir = _build_two(dressed, tmp_path)
    r = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    assert ": cargo" in r.stdout, r.stdout
    assert "cmd: " in r.stdout, r.stdout
    for borrowed in ("vitest", "file: src/fog", "(waited)", "npx"):
        assert borrowed not in r.stdout, (
            f"{borrowed!r} read off a Rust trace\n{r.stdout}")


def test_the_kind_label_table_cannot_be_written_through(tmp_path):
    """R27b. `frozen=True` freezes the ATTRIBUTE, not the mapping it points
    at, and all three columns are module singletons every renderer in the
    process shares. A renderer that wrote through
    `terms(trace).kind_labels[...]` would retune every later command --
    the one way a table whose whole purpose is that two commands cannot
    differ could make them differ. `MappingProxyType` refuses."""
    for table in (PYTHON, RUST, TYPESCRIPT):
        with pytest.raises(TypeError):
            table.kind_labels["coroutine"] = "borrowed"
        with pytest.raises(TypeError):
            del table.kind_labels["coroutine"]
    trace = Trace.open(build(_rust_vector(), tmp_path / "r", RUN_IDS))
    with pytest.raises(TypeError):
        terms(trace).kind_labels["function"] = "fn"
    assert dict(TYPESCRIPT.kind_labels) == {
        "coroutine": "async", "async_generator": "async generator"}


def test_the_typescript_vectors_actually_exercise_these_commands():
    """A guard on the guard, as for the Rust scan: if `load_all` stopped
    returning TypeScript vectors, or the ids changed, the scan above would
    pass by having nothing to check. The count is a floor, not a pin."""
    ids = {v["id"] for v in TS_VECTORS}
    assert len(ids) >= 5, ids
    for wanted in ("v23-lang-typescript-prose", "v26-kind-labels",
                   "v29-runs-file-header"):
        assert wanted in ids, ids


def test_a_reused_worker_is_listed_by_its_file_count(tmp_path):
    """The `test_files` arm of `v29-runs-file-header`'s rule, which one
    vector cannot carry: a vector describes ONE trace, and a container that
    ran one file and a reused worker that ran two are two different `meta`
    dicts. Built with the same builder and run through the same real CLI as
    a vector -- the `v10`/signalled-exit precedent above.

    The count, not the list: a `runs` row is one line, and `info` is where
    the files themselves have room. A worker that ran NO file keeps its
    argv, and that absence is the recorder's statement (HONESTY §6).
    """
    base = next(v for v in TS_VECTORS if v["id"] == "v29-runs-file-header")
    meta = {k: v for k, v in base["meta"].items() if k != "test_file"}
    reused = {**base, "meta": {**meta,
                               "test_files": ["src/fog/compute.test.ts",
                                              "src/fog/blend.test.ts"]}}
    sdir = _build_two(reused, tmp_path)
    r = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    assert "files: 2" in r.stdout, r.stdout
    assert "cmd: " not in r.stdout, r.stdout
    assert "file: src/fog" not in r.stdout, r.stdout
    # `info` says the same thing about the same trace: two commands reading
    # one trace must not answer the same question differently.
    i = run_cli(["info", RUN_IDS[0]], cwd=tmp_path, sensorium_dir=sdir)
    assert "files: 2" in i.stdout, i.stdout
    # And with neither key the row falls back to the argv it always had,
    # and `info`'s container line simply stops after the thread.
    plain = {**base, "meta": meta}
    sdir2 = _build_two(plain, tmp_path / "plain")
    r2 = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir2)
    assert "cmd: /usr/bin/node " in r2.stdout, r2.stdout
    assert "files:" not in r2.stdout and "file:" not in r2.stdout, r2.stdout
    i2 = run_cli(["info", RUN_IDS[0]], cwd=tmp_path, sensorium_dir=sdir2)
    assert "container: pid 4247  thread 0 (main)\n" in i2.stdout, i2.stdout


def test_a_harness_killed_by_a_signal_is_headed_by_the_signal(tmp_path):
    """The signalled arm of the invocation header, which one vector cannot
    carry for the same reason as the row above: `status` and `signal` are
    exclusive, so they are two `meta` dicts. A harness the driver waited
    for and found dead of a signal chose no status, and printing
    `exit:None` for one is what the whole exit rule exists to stop."""
    base = next(v for v in TS_VECTORS if v["id"] == "v28-harness-exit-waited")
    killed = {**base, "meta": {**base["meta"],
                               "harness_exit": {"status": None,
                                                "signal": "SIGINT",
                                                "basis": "waited"}}}
    sdir = _build_two(killed, tmp_path)
    r = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir)
    assert "exit:signal SIGINT (waited)" in r.stdout, r.stdout
    assert "exit:None" not in r.stdout, r.stdout
    i = run_cli(["info", RUN_IDS[0]], cwd=tmp_path, sensorium_dir=sdir)
    assert "exit: signal SIGINT (waited)" in i.stdout, i.stdout
    # ...and a driver killed before the harness returned recorded no ending
    # at all, which is not a harness that ended at 0.
    unrecorded = {**base,
                  "meta": {k: v for k, v in base["meta"].items()
                           if k != "harness_exit"}}
    sdir2 = _build_two(unrecorded, tmp_path / "unrecorded")
    r2 = run_cli(["runs"], cwd=tmp_path, sensorium_dir=sdir2)
    assert "npx vitest run src/fail.test.ts\n" in r2.stdout, r2.stdout
    assert "exit:0" not in r2.stdout, r2.stdout
    i2 = run_cli(["info", RUN_IDS[0]], cwd=tmp_path, sensorium_dir=sdir2)
    assert ("harness: npx vitest run src/fail.test.ts\n"
            in i2.stdout), i2.stdout


# -- the five fields the readers of rung 4 ask for --------------------------
def test_every_column_answers_every_field_and_none_may_be_defaulted():
    """The completeness rule, enumerated from the dataclass rather than
    from a list someone remembered to extend.

    No field may carry a DEFAULT. A default is how a fourth column would
    silently inherit another language's word -- the exact failure `terms()`
    was made strict for -- and it is also how a field added for one
    recorder would go unanswered by the other two.
    """
    for name in Terms.__dataclass_fields__:
        for column in (PYTHON, RUST, TYPESCRIPT):
            assert hasattr(column, name), f"{column.lang} lacks {name}"
    for f in fields(Terms):
        assert f.default is MISSING and f.default_factory is MISSING, f.name


def test_the_dialect_a_reader_parses_a_dbg_capture_in():
    """`dbg` is one kind and two languages write it, so the TEXT alone
    cannot say what it spells: `'a'` is the string a in one dialect and a
    quoted word in the other. Python has no dialect at all -- its captures
    are typed, and a `dbg` never reaches a Python trace."""
    assert PYTHON.dbg_dialect is None
    assert RUST.dbg_dialect == "rust"
    assert TYPESCRIPT.dbg_dialect == "inspect"


def test_how_each_language_spells_one_recorded_site():
    """Plan P8. `module` is the dotted name Python's recorder derives and
    Rust's printed listings already quote; `rel` is the root-relative path
    a TypeScript `--focus` is typed with, so `--at` and `--focus` share one
    spelling."""
    assert PYTHON.site_spelling == "module"
    assert RUST.site_spelling == "module"
    assert TYPESCRIPT.site_spelling == "rel"


def test_what_object_identity_rests_on_in_each_language():
    """CPython recycles addresses, so Python's `flow --object` is a hedged
    claim; a TypeScript serial is minted once per object and never reused,
    so it is an exact one. Rust records no identity at all, and the word
    for that is not "address"."""
    assert PYTHON.identity_basis == "address"
    assert RUST.identity_basis == "none"
    assert TYPESCRIPT.identity_basis == "serial"


def test_the_command_that_records_this_trace_again():
    """A hint carrying a placeholder is a template, not an answer -- so the
    template lives here and is instantiated from the trace's own meta, and
    the key that holds the command differs per recorder."""
    assert PYTHON.rerun_command == "sensorium run{focus} -- {command}"
    assert TYPESCRIPT.rerun_command == "sensorium ts run{focus} -- {command}"
    assert RUST.rerun_command == "cargo sensorium{focus} {command}"
    assert PYTHON.command_key == "argv"
    assert TYPESCRIPT.command_key == "harness_command"
    assert RUST.command_key == "cargo_args"


def test_the_typescript_notes_name_the_command_this_rung_shipped():
    """Both sentences said rung 3 had no deeper capture to re-run for.
    Rung 4 gave this recorder one, so both name it -- and neither may name
    `sensorium run --focus`, which cannot read a TypeScript trace (the E7
    needle `FORBIDDEN_TS` keeps guarding that)."""
    for text in (TYPESCRIPT.no_rerun_note, TYPESCRIPT.timeline_hint):
        assert "sensorium ts run --focus" in text
        assert "S5 rung 3" not in text and "rung 3" not in text
        assert "capabilities.line: false" not in text
    assert TYPESCRIPT.no_rerun_note == (
        "no rerun was attempted; refocus is not yet this recorder's -- "
        "record again with `sensorium ts run --focus <file>:<qualname> -- "
        "<harness command>`")
    assert TYPESCRIPT.timeline_hint == (
        "record again with `sensorium ts run --focus {mod}:{qualname} -- "
        "<harness command>`; per-statement capture is opt-in at record time")


def test_the_matched_focus_line_is_gated_on_the_keys_and_not_on_a_language(
        tmp_path, monkeypatch, capsys):
    """`info`'s `focus matched:` line reaches a RUST trace too (ruling R32).

    `meta.focus_matched` is not a TypeScript key: `cargo sensorium --focus`
    writes it as well (`convert/meta.rs`), and it means the same thing
    there -- what the spec SELECTED, beside what was typed. So the line is
    gated on the keys and not on `lang`, and this pins its exact text on a
    focused Rust recording rather than leaving it to a report sentence. A
    language gate here would be the one thing this module exists to
    prevent, arriving from the other side: a true sentence withheld from a
    trace that supports it.

    `functions_focused` is the transform's own count and no Rust converter
    writes one, so the parenthetical never appears on this side.

    It lives in this file rather than in `tests/test_runs_info.py` -- which
    owns `info`'s other assertions -- because that module is at 790 of the
    repository's 800-line ceiling, and because what is pinned here is which
    SENTENCE reaches which language, which is this module's subject.
    """
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    text = capsys.readouterr().out
    assert "focus: fill, Counter    window: -" in text
    assert "focus matched: 2 \u2014 Counter::new, fill" in text
    assert "function(s) focused by the transform" not in text
