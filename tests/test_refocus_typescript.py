"""`sensorium refocus` on a TypeScript trace, on fixture traces and no node.

Every test here drives the real command through `refocus_cmd.run`, or the
real function under test, over traces built as DATA (`tests/ts_traces.py`).
The one thing that cannot be real is the harness: `subprocess.run` is
patched, and the patch is ASSERTED -- what argv, from what directory, with
what environment -- because those three ARE the re-run, and a test that only
checked the verdict would pass over a suite launched from the wrong place.

The traces, the fake driver and the store reads are
`tests/refocus_ts_fixtures.py`.
"""
import time
from pathlib import Path

import pytest

from sensorium import paths
from sensorium.query import (info_cmd, refocus_cmd, refocus_rust,
                             refocus_typescript)
from sensorium.query.vocab import TYPESCRIPT
from sensorium.store.reader import Trace
from tests.refocus_ts_fixtures import (ORIG, ORIG_ENV, OTHER,
                                       OTHER_ORIGINAL, PAIR, SIBLING, STALE,
                                       _drive, _drop_meta, _never,
                                       _read_meta, args, original,
                                       other_program, refuse, task_files,
                                       two_test_files)
from tests.ts_traces import TS_CAPABILITIES


def _trace(run_id):
    return Trace.open(paths.traces_dir() / f"{run_id}.db")


# -- the seven pre-rerun refusals, in the design's order --------------------
def test_window_is_refused_first_and_nothing_is_re_run(tmp_path, monkeypatch,
                                                       capsys):
    """Refusal 1. Given ALONGSIDE the next fault (a trace recorded at
    `--tier off`), so the test pins the ORDER and not merely the sentence."""
    run, _ = original(tmp_path, monkeypatch,
                      env={**ORIG_ENV, "SENSORIUM_TIER": "off"})
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute", window="x")
    assert code == 2
    assert (f"error: cannot refocus {run}: --window is not available for a "
            "TypeScript trace (the recorder has no per-activation gate); "
            "nothing was re-run") in err


def test_a_tier_off_recording_is_refused_and_says_it_holds_no_stream(
        tmp_path, monkeypatch, capsys):
    """Refusal 2, alongside the next fault (no `harness_command`): a run
    recorded at `--tier off` has no causal stream, so the comparison the
    re-run is FOR could not be made whatever came back."""
    run, _ = original(tmp_path, monkeypatch,
                      env={**ORIG_ENV, "SENSORIUM_TIER": "off"})
    _drop_meta(tmp_path, run, "harness_command")
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert (f"run {run} was recorded at --tier off and holds no causal "
            "stream to compare against; nothing was re-run") in err


def test_a_trace_without_a_harness_command_is_refused(tmp_path, monkeypatch,
                                                      capsys):
    """Refusal 3, alongside the next fault (no `harness_cwd`). There is
    nothing to re-run, and guessing a command is guessing."""
    run, _ = original(tmp_path, monkeypatch)
    _drop_meta(tmp_path, run, "harness_command")
    _drop_meta(tmp_path, run, "harness_cwd")
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert (f"run {run} records no harness command to re-run (recorded by a "
            "driver before the key existed); nothing was re-run") in err


def test_a_trace_without_a_harness_cwd_names_the_driver_that_wrote_it(
        tmp_path, monkeypatch, capsys):
    """Refusal 4, alongside the next fault it can be given (a `root` that is
    gone -- the fifth needs a `harness_cwd` to be gone, and this trace has
    none at all). The sentence names the driver that cannot answer."""
    gone = str(tmp_path / "deleted")
    run, _ = original(tmp_path, monkeypatch, root=gone)
    _drop_meta(tmp_path, run, "harness_cwd")
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert (f"run {run} records no working directory to re-run from "
            "(recorded by sensorium ts 0.13.0 or earlier); nothing was "
            "re-run") in err


def test_a_harness_cwd_that_is_gone_is_refused_by_path(tmp_path, monkeypatch,
                                                       capsys):
    """Refusal 5, alongside the next fault (a `root` that is gone too): the
    directory the command was TYPED in is the one the re-run starts from,
    and it is checked before the project root."""
    gone = str(tmp_path / "deleted")
    run, _ = original(tmp_path, monkeypatch, harness_cwd=gone, root=gone)
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert f"directory {gone} no longer exists; nothing was re-run" in err
    assert "project root" not in err


def test_a_project_root_that_is_gone_is_refused_by_path(tmp_path, monkeypatch,
                                                        capsys):
    """Refusal 6, alongside the next fault (`test_files`): the harness's own
    working directory can still exist while the project it names does not,
    and the two are different sentences because they are different facts."""
    gone = str(tmp_path / "deleted")
    run, _ = original(tmp_path, monkeypatch, root=gone,
                      test_files=["src/a.test.ts", "src/b.test.ts"])
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert f"project root {gone} no longer exists; nothing was re-run" in err


def test_a_reused_worker_is_refused_by_its_recorded_test_files(
        tmp_path, monkeypatch, capsys):
    """Refusal 7, case (a) of ruling P3: a converter that reported several
    file starts. LAST, because it is the one refusal whose fault is about
    the harness's scheduling rather than about this call or this world."""
    run, _ = original(tmp_path, monkeypatch,
                      test_files=["src/a.test.ts", "src/b.test.ts"])
    _drop_meta(tmp_path, run, "test_file")
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert (f"run {run} ran 2 test files in one container (a reused worker); "
            "which container of a re-run would be its pair is the harness's "
            "scheduling, not a fact; nothing was re-run") in err


def test_the_seven_refusals_fire_in_the_designs_order(tmp_path, monkeypatch):
    """One trace that fails every check, asked seven times: each answer is
    the FIRST outstanding fault, and removing it uncovers the next."""
    gone = str(tmp_path / "deleted")
    run, root = original(tmp_path, monkeypatch)
    trace = _trace(run)
    meta = {"run_id": ORIG, "env": {"SENSORIUM_TIER": "off"},
            "test_files": ["a.test.ts", "b.test.ts"]}
    order = [refocus_typescript.refusal(meta, args(ORIG, window="x"), trace)]
    order.append(refocus_typescript.refusal(meta, args(ORIG), trace))
    meta["env"] = {"SENSORIUM_TIER": "call"}
    order.append(refocus_typescript.refusal(meta, args(ORIG), trace))
    meta["harness_command"] = ["npx", "vitest", "run"]
    order.append(refocus_typescript.refusal(meta, args(ORIG), trace))
    meta["harness_cwd"] = gone
    order.append(refocus_typescript.refusal(meta, args(ORIG), trace))
    meta["harness_cwd"] = str(root)
    meta["root"] = gone
    order.append(refocus_typescript.refusal(meta, args(ORIG), trace))
    meta["root"] = str(root)
    order.append(refocus_typescript.refusal(meta, args(ORIG), trace))
    assert [s.split(";")[0].split(" (")[0] for s in order] == [
        "--window is not available for a TypeScript trace",
        f"run {ORIG} was recorded at --tier off and holds no causal stream "
        "to compare against",
        f"run {ORIG} records no harness command to re-run",
        f"run {ORIG} records no working directory to re-run from",
        f"directory {gone} no longer exists",
        f"project root {gone} no longer exists",
        f"run {ORIG} ran 2 test files in one container",
    ]
    del meta["test_files"]
    assert refocus_typescript.refusal(meta, args(ORIG), trace) is None


def test_every_refusal_carries_the_typescript_note_and_never_pythons_command(
        tmp_path, monkeypatch, capsys):
    """The note under EVERY refusal is this recorder's own: `sensorium run
    --focus` cannot read a TypeScript recording, so offering it there sends
    the reader to a second refusal (the E7 needle)."""
    gone = str(tmp_path / "deleted")
    faults = [
        ({}, dict(window="x")),
        ({"env": {**ORIG_ENV, "SENSORIUM_TIER": "off"}}, {}),
        ({"harness_cwd": gone}, {}),
        ({"root": gone}, {}),
        ({"test_files": ["a.test.ts", "b.test.ts"]}, {}),
    ]
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)
    for n, (meta, call_kw) in enumerate(faults):
        run, _ = original(tmp_path, monkeypatch,
                          run_id=f"2026010{n}-000000-ts000{n}", **meta)
        code, err = refuse(capsys, run, "compute", **call_kw)
        assert code == 2
        assert "no rerun was attempted;" in err
        assert "sensorium run --focus" not in err
    assert TYPESCRIPT.no_rerun_note.startswith("no rerun was attempted;")


def test_a_trace_that_declares_no_refocus_capability_refuses_through_the_gate(
        tmp_path, monkeypatch, capsys):
    """The OLD TypeScript trace -- a driver before 0.14.0, which declared
    `capabilities.refocus: false`. It never reaches this module: the SHARED
    capability gate refuses it first, in the generic sentence, so a trace
    that cannot be refocused at all is never told about `--window`."""
    caps = {**TS_CAPABILITIES, "refocus": False}
    run, _ = original(tmp_path, monkeypatch, capabilities=caps)
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute", window="x")
    assert code == 2
    assert ("refocus needs refocus, which recorder sensorium-ts 0.4.0 "
            "declares it does not produce (capabilities.refocus: false); "
            "nothing was checked") in err
    assert "--window is not available" not in err


# -- refusal 7's second condition: the files the TRACE says its tests ran in
def test_test_files_run_names_the_test_files_its_task_roots_sit_in(
        tmp_path, monkeypatch):
    """Ruling P3 (b). The trace says which files its tests ran in: a task's
    ROOT frame is the callback vitest invoked, and its code object's file is
    the test file. Root-relative, because `meta.root` is what the harness's
    own `test_file` is relative to and two spellings of one path would read
    as two files."""
    run, _ = two_test_files(tmp_path, monkeypatch)
    assert refocus_typescript.test_files_run(_trace(run)) == [
        "src/a.test.ts", "src/b.test.ts"]


def test_a_reused_worker_is_refused_from_the_traces_own_root_frames(
        tmp_path, monkeypatch, capsys):
    """The harness this refusal EXISTS for: under `--no-isolate --maxWorkers
    1` vitest 4.1.9 runs both files in one container and the converter
    records `test_file` (singular, the first) and never `test_files`, so
    condition (a) never fires. The trace still says two test files ran."""
    run, _ = two_test_files(tmp_path, monkeypatch)
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)

    code, err = refuse(capsys, run, "asserts")
    assert code == 2
    assert (f"run {run} ran 2 test files in one container (a reused "
            "worker); which container of a re-run would be its pair is the "
            "harness's scheduling, not a fact; nothing was re-run") in err


def test_a_second_task_rooted_in_a_helper_is_not_a_second_test_file(
        tmp_path, monkeypatch):
    """The BOUND ruling P3 names (blind spot 42). Only a file whose name
    carries `.test.` or `.spec.` counts: a container whose second test roots
    in a shared helper is ONE test file as far as the trace can tell, and a
    refusal here would fire on every suite with a helper of its own."""
    run, root = two_test_files(tmp_path, monkeypatch,
                               second="src/helpers.ts")
    trace = _trace(run)
    assert refocus_typescript.test_files_run(trace) == ["src/a.test.ts"]
    assert refocus_typescript.refusal(trace.meta, args(run), trace) is None


def test_test_files_are_counted_from_the_meta_key_when_it_is_there(
        tmp_path, monkeypatch):
    """Condition (a) takes its count from `meta.test_files` -- a converter
    that DOES report several file starts is believed over the frames, which
    can only ever see the files a task rooted in."""
    run, _ = original(tmp_path, monkeypatch,
                      test_files=["a.test.ts", "b.test.ts", "c.test.ts"])
    trace = _trace(run)
    sentence = refocus_typescript.refusal(trace.meta, args(run), trace)
    assert f"run {run} ran 3 test files in one container" in sentence


def test_the_count_is_the_larger_of_what_was_declared_and_what_ran(
        tmp_path, monkeypatch):
    """Ruling P11: the two readings are an OR, not an XOR. A converter that
    reports two file starts over a container whose tests rooted in THREE
    test files has under-reported, and the count it wrote must not be able
    to mask what the frames plainly show -- so the refusal names the number
    the evidence that saw more saw."""
    run, _ = task_files(
        tmp_path, monkeypatch,
        files=("src/a.test.ts", "src/b.test.ts", "src/c.test.ts"),
        test_files=["src/a.test.ts", "src/b.test.ts"])
    trace = _trace(run)
    assert refocus_typescript.test_files_run(trace) == [
        "src/a.test.ts", "src/b.test.ts", "src/c.test.ts"]
    sentence = refocus_typescript.refusal(trace.meta, args(run), trace)
    assert f"run {run} ran 3 test files in one container" in sentence


def test_a_test_file_outside_the_recorded_root_is_named_as_recorded(
        tmp_path, monkeypatch):
    """Root-relative where it CAN be, as recorded otherwise: a file outside
    the project root has no relative spelling, and inventing one (`../../`)
    would name a path neither the trace nor the harness ever used."""
    run, _ = two_test_files(tmp_path, monkeypatch)
    trace = _trace(run)
    outside = str(Path(tmp_path) / "elsewhere" / "x.test.ts")
    root = trace.meta["root"]
    files = [outside, str(Path(root) / "src" / "a.test.ts")]
    assert refocus_typescript._relative_to_root(outside, root) == outside
    assert refocus_typescript._relative_to_root(files[1], root) == \
        "src/a.test.ts"
    assert refocus_typescript._relative_to_root(files[1], None) == files[1]


# -- the argv --------------------------------------------------------------
def test_rerun_argv_is_the_interpreter_the_link_the_tier_the_focus_and_cmd():
    meta = {"run_id": ORIG, "env": {"SENSORIUM_TIER": "call"},
            "focus": ["load"], "harness_command": ["npx", "vitest", "run"]}
    import sys
    assert refocus_typescript.rerun_argv(meta, ["dump"], ORIG) == [
        sys.executable, "-m", "sensorium", "ts", "run", "--refocus-of", ORIG,
        "--tier", "call", "--focus", "load", "--focus", "dump",
        "--", "npx", "vitest", "run"]


def test_rerun_argv_omits_the_tier_when_the_original_recorded_none():
    """Omitted, never guessed: with no `--tier` the driver applies its own
    default, and writing one here would assert a tier nothing recorded."""
    meta = {"run_id": ORIG, "env": {"PATH": "/usr/bin"},
            "harness_command": ["npx", "vitest", "run"]}
    argv = refocus_typescript.rerun_argv(meta, ["compute"], ORIG)
    assert "--tier" not in argv
    assert argv[5:9] == ["--refocus-of", ORIG, "--focus", "compute"]


def test_rerun_argv_keeps_the_originals_focus_first_and_never_drops_it():
    """A refocus only ever captures MORE (`_merged_focus`), and the order is
    the original's values then the caller's, de-duplicated."""
    meta = {"run_id": ORIG, "focus": ["a", "b"],
            "harness_command": ["npx", "vitest", "run"]}
    argv = refocus_typescript.rerun_argv(meta, ["b", "c"], ORIG)
    assert argv[argv.index("--focus"):-4] == [
        "--focus", "a", "--focus", "b", "--focus", "c"]


def test_rerun_argv_passes_the_harness_command_through_verbatim_after_a_dash():
    """`--` is what stops the driver reading the harness's own flags as its
    own, so the command goes last and untouched."""
    meta = {"run_id": ORIG,
            "harness_command": ["npx", "vitest", "run", "--no-isolate"]}
    argv = refocus_typescript.rerun_argv(meta, [], ORIG)
    assert argv[-5:] == ["--", "npx", "vitest", "run", "--no-isolate"]


def test_rerun_argv_runs_this_interpreter_and_never_a_name_on_the_path():
    """`sys.executable`, so the re-run is recorded by THIS sensorium: a
    `sensorium` on PATH could be another version entirely, and the pair
    would be compared across two recorders."""
    import sys
    meta = {"run_id": ORIG, "harness_command": ["npx", "vitest"]}
    argv = refocus_typescript.rerun_argv(meta, [], ORIG)
    assert argv[:5] == [sys.executable, "-m", "sensorium", "ts", "run"]


# -- the pair key and the pair lookup --------------------------------------
def test_pair_key_is_the_test_file_when_the_container_ran_one():
    assert refocus_typescript.pair_key(
        {"test_file": "src/config.test.ts", "argv": ["node", "x"]}) == (
            "test_file", "src/config.test.ts")


def test_pair_key_falls_back_to_the_whole_argv():
    """A container that ran no test file at all -- `node --test`, a script
    -- is identified by what it was: its argv."""
    assert refocus_typescript.pair_key({"argv": ["node", "x.js"]}) == (
        "argv", "node", "x.js")
    assert refocus_typescript.pair_key({}) == ("argv",)


def test_find_pair_returns_nothing_when_no_trace_is_linked(tmp_path,
                                                           monkeypatch):
    run, _ = original(tmp_path, monkeypatch)
    key = ("test_file", "src/config.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, 0.0, key) == ([], [])


def test_find_pair_finds_the_one_container_that_ran_the_same_test_file(
        tmp_path, monkeypatch):
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    key = ("test_file", "src/config.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, key) == ([PAIR], [])


def test_find_pair_puts_another_containers_test_file_among_the_siblings(
        tmp_path, monkeypatch):
    """The whole invocation was re-run, so every other container of it is
    linked too. They are SIBLINGS -- named on the pair line, compared to
    nothing -- and counting them as candidates would refuse every re-run of
    a suite with more than one test file in it."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    original(tmp_path, monkeypatch, run_id=SIBLING, refocus_of=run,
             start_ts=launched + 1, test_file="src/other.test.ts")
    key = ("test_file", "src/config.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, key) == ([PAIR], [SIBLING])


def test_find_pair_excludes_a_link_recorded_before_this_launch(tmp_path,
                                                               monkeypatch):
    """The mutation this filter exists for. An EARLIER refocus of the same
    original left a trace carrying the same `refocus_of`; without the
    timestamp filter every later refocus of that run would find two
    candidates and refuse -- permanently."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=STALE, refocus_of=run,
             start_ts=launched - 100)
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    key = ("test_file", "src/config.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, key) == ([PAIR], [])


def test_find_pair_excludes_a_link_to_a_DIFFERENT_original(tmp_path,
                                                           monkeypatch):
    """The link filter is an EQUALITY. A concurrent refocus of another
    original writes a trace that is linked and recent -- every condition but
    the one that matters -- and read as `if not linked` it would join this
    pair's siblings and be counted on its line."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=OTHER, refocus_of=OTHER_ORIGINAL,
             start_ts=launched + 1)
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    key = ("test_file", "src/config.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, key) == ([PAIR], [])


def test_find_pair_returns_both_when_two_containers_claim_one_test_file(
        tmp_path, monkeypatch):
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    for rid in ("20260101-000100-pairaa", "20260101-000100-pairbb"):
        original(tmp_path, monkeypatch, run_id=rid, refocus_of=run,
                 start_ts=launched + 1)
    key = ("test_file", "src/config.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, key) == (
            ["20260101-000100-pairaa", "20260101-000100-pairbb"], [])


def test_find_pair_matches_an_argv_key_against_a_container_with_no_test_file(
        tmp_path, monkeypatch):
    """A `node --test` container carries no `test_file`, so the key is its
    argv -- and a container that DOES carry one is a sibling to that key,
    never its pair."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    argv = ["/usr/bin/node", "--test", "src/config.test.ts"]
    plain = original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
                     start_ts=launched + 1, argv=argv)[0]
    original(tmp_path, monkeypatch, run_id=SIBLING, refocus_of=run,
             start_ts=launched + 1, argv=argv,
             test_file="src/other.test.ts")
    _drop_meta(tmp_path, plain, "test_file")
    key = ("argv", *argv)
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, key) == ([PAIR], [SIBLING])


def test_a_reused_worker_is_never_the_pair_of_an_argv_keyed_original(
        tmp_path, monkeypatch):
    """Design section 2.4's second bullet: an argv-keyed original pairs with
    a container that carries NEITHER `test_file` nor `test_files`. A reused
    worker whose command line happens to match is not that container -- it
    ran several files, which is the one shape refusal 7 will not let a
    reader ask about, and pairing it here would admit it through the back
    door of the re-run. It is a sibling: counted, and compared to nothing."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    argv = ["/usr/bin/node", "node_modules/.bin/vitest"]
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1, argv=argv,
             test_files=["src/a.test.ts", "src/b.test.ts"])
    _drop_meta(tmp_path, PAIR, "test_file")
    assert refocus_typescript.pair_key(
        {"argv": argv, "test_files": ["src/a.test.ts", "src/b.test.ts"]}) == (
            "test_files", "src/a.test.ts", "src/b.test.ts")
    assert refocus_typescript.find_pair(
        paths.traces_dir(), run, launched, ("argv", *argv)) == ([], [PAIR])


def test_siblings_note_says_the_count_and_that_nothing_compared_them():
    assert refocus_typescript.siblings_note(0) == (
        "siblings in the re-run: 0 (not compared; UNVERIFIED)")
    assert refocus_typescript.siblings_note(371) == (
        "siblings in the re-run: 371 (not compared; UNVERIFIED)")


# -- the launch ------------------------------------------------------------
def test_the_harness_is_launched_from_the_typed_in_directory_under_the_store(
        tmp_path, monkeypatch, capsys):
    """The three things that ARE the re-run: what was run, from where, and
    with which store. `SENSORIUM_DIR` is the ABSOLUTE store the original
    came from -- a relative one would follow the child into the project and
    write the new traces where the pair lookup never looks."""
    import os
    import sys
    run, root, code, fake = _drive(tmp_path, monkeypatch,
                                   pairs=[(PAIR, {})])
    capsys.readouterr()
    (argv, kw), = fake.calls
    assert argv == [sys.executable, "-m", "sensorium", "ts", "run",
                    "--refocus-of", run, "--tier", "call",
                    "--focus", "compute", "--", "npx", "vitest", "run",
                    "src/config"]
    assert kw["cwd"] == str(root)
    assert kw["env"]["SENSORIUM_DIR"] == str(paths.trace_root().resolve())
    assert Path(kw["env"]["SENSORIUM_DIR"]).is_absolute()
    # The caller's environment, with nothing else set or stripped.
    assert kw["env"]["PATH"] == os.environ["PATH"]
    # Nothing is captured: all three streams are INHERITED, because the
    # harness's output is what a person waiting on a suite is watching.
    assert "stdout" not in kw and "stderr" not in kw
    assert code == 0


def test_the_announced_lines_say_what_will_run_before_it_runs(tmp_path,
                                                              monkeypatch,
                                                              capsys):
    """Six lines, in this order, all BEFORE the launch: the reader watching
    a suite start must be able to see the command, the interpreter that is
    about to record it, where it will run and what the source check already
    said."""
    import sys
    run, root, _code, _fake = _drive(tmp_path, monkeypatch,
                                     pairs=[(PAIR, {})])
    out = capsys.readouterr().out
    head = out.split("--- rerunning")[0].splitlines()
    assert head[0] == (f"refocus-of: {run}   cmd: sensorium ts run "
                       f"--refocus-of {run} --tier call --focus compute -- "
                       "npx vitest run src/config")
    assert head[1] == f"via: {sys.executable} -m sensorium"
    assert head[2] == f"cwd: {root}"
    assert head[3] == "focus: compute   window: -"
    assert head[4].startswith("source: unchanged (1 file(s) compared by "
                              "content")
    assert ("--- rerunning (the harness's own output follows; the driver's "
            "run: lines print with it) ---") in out


# -- the verdict, the licence, the stamps ----------------------------------
def test_a_matching_pair_is_compared_and_stamped_into_the_new_trace(
        tmp_path, monkeypatch, capsys):
    seen = {}
    import sensorium.query.diff_cmd as diff_cmd
    inner = diff_cmd.compare

    def spy(a, b, moves=None):
        seen["pair"] = b.meta["run_id"]
        return inner(a, b, moves)
    monkeypatch.setattr(diff_cmd, "compare", spy)

    run, _root, code, _fake = _drive(tmp_path, monkeypatch,
                                     pairs=[(PAIR, {})])
    out = capsys.readouterr().out
    assert code == 0
    assert seen["pair"] == PAIR                    # compared THE pair
    assert "refocus verdict: MATCH" in out
    assert f"run: {PAIR}   invocation: 20260101-000000-111111   " \
           "siblings in the re-run: 0 (not compared; UNVERIFIED)" in out
    assert f"trace: {paths.traces_dir().resolve() / (PAIR + '.db')}" in out
    assert _read_meta(PAIR, "refocus_verdict") == "MATCH"
    assert _read_meta(PAIR, "refocus_of") == run
    assert _read_meta(PAIR, "refocus_siblings") == 0


def test_the_three_checks_that_could_not_run_are_printed_and_stamped(
        tmp_path, monkeypatch, capsys):
    """This recorder declares `output`, `children` and `threads` all false,
    so three of the licence's checks cannot run at all -- named rather than
    counted as failures, and stamped so `info` can say so afterwards."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out
    assert ("checks that could not run on this pair -- the recorder declares "
            "it does not produce them, so nothing here is evidence either "
            "way:") in out
    for marker in ("output: unverifiable (not recorded)",
                   "children: unverifiable (not witnessed)",
                   "threads: unverifiable (not witnessed)"):
        assert f"  - {marker}" in out
    assert _read_meta(PAIR, "refocus_licence_unverifiable") == [
        "output: unverifiable (not recorded)",
        "children: unverifiable (not witnessed)",
        "threads: unverifiable (not witnessed)"]


def test_the_exit_line_names_both_harness_exits_and_how_they_were_learned(
        tmp_path, monkeypatch, capsys):
    """The HARNESS's exit, which the driver waited for -- not the
    container's `exit_status`, which nobody waited for and which is null on
    every trace this recorder writes."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out
    assert "exit: rerun 0 (waited)   original 0 (waited)" in out


def test_a_diverging_pair_exits_1_and_says_which_run_is_not_the_answer(
        tmp_path, monkeypatch, capsys):
    run, _root, code, _fake = _drive(tmp_path, monkeypatch,
                                     pairs=[(PAIR, {})],
                                     build=other_program)
    out = capsys.readouterr().out
    assert code == 1
    assert "refocus verdict: DIVERGED" in out
    assert _read_meta(PAIR, "refocus_verdict") == "DIVERGED"
    assert _read_meta(PAIR, "refocus_siblings") == 0


def test_a_re_run_that_linked_nothing_is_refused_after_the_fact(
        tmp_path, monkeypatch, capsys):
    """Exit 3, not 2: the harness DID run, so no edit to the command settles
    it. The harness's exit is the reason, and its own output -- which
    streamed through uncaptured -- is where the detail is."""
    run, _root, code, _fake = _drive(tmp_path, monkeypatch, returncode=1)
    out = capsys.readouterr().out
    assert code == 3
    assert (f"refocus verdict: REFUSED -- the re-run produced 0 trace(s) "
            f"linked to {run} and none ran src/config.test.ts (harness exit "
            "1); see the harness's output above") in out
    assert "what sensorium sees at all" in out          # blind spots, still


def test_a_re_run_that_produced_only_a_sibling_names_the_test_file(
        tmp_path, monkeypatch, capsys):
    """The suite re-ran and this container's test file was not among what
    came back -- a `--maxWorkers` change, a filter, a file that no longer
    exists. The count is of what WAS linked, so the reader can see the
    re-run happened."""
    run, _root, code, _fake = _drive(
        tmp_path, monkeypatch,
        pairs=[(SIBLING, {"test_file": "src/other.test.ts"})])
    out = capsys.readouterr().out
    assert code == 3
    assert (f"the re-run produced 1 trace(s) linked to {run} and none ran "
            "src/config.test.ts (harness exit 0)") in out


def test_two_containers_claiming_one_test_file_are_refused_by_count(
        tmp_path, monkeypatch, capsys):
    pairs = [("20260101-000100-pairaa", {}), ("20260101-000100-pairbb", {})]
    run, _root, code, _fake = _drive(tmp_path, monkeypatch, pairs=pairs)
    out = capsys.readouterr().out
    assert code == 3
    assert (f"refocus verdict: REFUSED -- the re-run produced 2 traces "
            f"linked to {run} that each ran src/config.test.ts "
            "(20260101-000100-pairaa, 20260101-000100-pairbb); two "
            "containers of one invocation claiming one test file is a fact "
            "about the harness this tool will not guess through") in out


def test_a_sibling_is_counted_on_the_pair_line_and_stamped_on_the_pair(
        tmp_path, monkeypatch, capsys):
    """The other containers of the re-run invocation: counted, never
    compared, and the count lives on the PAIR's trace alone -- a sibling
    carries the driver's `refocus_of` and no verdict of its own, which is
    what UNVERIFIED means."""
    run, _root, code, _fake = _drive(
        tmp_path, monkeypatch,
        pairs=[(PAIR, {}), (SIBLING, {"test_file": "src/other.test.ts"})])
    out = capsys.readouterr().out
    assert code == 0
    assert f"run: {PAIR}   invocation: 20260101-000000-111111   " \
           "siblings in the re-run: 1 (not compared; UNVERIFIED)" in out
    assert _read_meta(PAIR, "refocus_siblings") == 1
    assert _read_meta(SIBLING, "refocus_of") == run
    assert _read_meta(SIBLING, "refocus_verdict") is None
    assert _read_meta(SIBLING, "refocus_siblings") is None


def test_the_sibling_count_is_of_the_siblings_and_not_of_the_pair(
        tmp_path, monkeypatch, capsys):
    """TWO siblings, because one is a count that every wrong reading of this
    lookup also produces: with a single sibling beside a single pair,
    `len(siblings)`, `len(candidates)` and `1` are the same number."""
    run, _root, code, _fake = _drive(
        tmp_path, monkeypatch,
        pairs=[(PAIR, {}),
               (SIBLING, {"test_file": "src/other.test.ts"}),
               ("20260101-000300-sibl02", {"test_file": "src/third.test.ts"})])
    out = capsys.readouterr().out
    assert code == 0
    assert "siblings in the re-run: 2 (not compared; UNVERIFIED)" in out
    assert _read_meta(PAIR, "refocus_siblings") == 2


def test_the_typescript_blind_spots_are_printed_after_the_verdict(
        tmp_path, monkeypatch, capsys):
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, {})])
    out = capsys.readouterr().out
    for line in TYPESCRIPT.refocus_blind_spots:
        assert f"  - {line}" in out
    assert "asyncio" not in out
    assert "cargo" not in out


# -- the stamp, replayed by `info` -----------------------------------------
def test_info_replays_the_sibling_count_after_the_terminal_has_scrolled(
        tmp_path, monkeypatch, capsys):
    """The count is stamped so it survives the scrollback; `info` says it
    under the verdict, in the SAME words the pair line used."""
    run, _root, _code, _fake = _drive(
        tmp_path, monkeypatch,
        pairs=[(PAIR, {}), (SIBLING, {"test_file": "src/other.test.ts"})])
    capsys.readouterr()
    info_cmd.run(args(PAIR))
    out = capsys.readouterr().out
    assert f"refocus-of: {run}" in out
    assert "siblings in the re-run: 1 (not compared; UNVERIFIED)" in out


def test_info_says_nothing_about_siblings_for_a_trace_without_the_stamp(
        tmp_path, monkeypatch, capsys):
    """An absent key is not a count of zero: a re-run recorded before the
    stamp existed did not have zero siblings, it has no record of them."""
    run, _ = original(tmp_path, monkeypatch)
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             refocus_verdict="MATCH")
    capsys.readouterr()
    info_cmd.run(args(PAIR))
    out = capsys.readouterr().out
    assert f"refocus-of: {run}" in out
    assert "siblings in the re-run" not in out


# -- the dispatch and the shared helpers -----------------------------------
def test_a_typescript_trace_reaches_this_branch_and_not_pythons(
        tmp_path, monkeypatch, capsys):
    """The dispatch is on the trace's own `lang` and on nothing else -- and
    the Python branch's own sentences (`original trace records no command to
    re-run`) never reach a TypeScript reader."""
    run, _ = original(tmp_path, monkeypatch)
    assert _trace(run).lang == "typescript"
    _drop_meta(tmp_path, run, "harness_command")
    monkeypatch.setattr(refocus_typescript.subprocess, "run", _never)
    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert "records no harness command to re-run" in err
    assert "original trace records no command" not in err


def test_the_refusal_after_a_re_run_is_the_one_the_rust_branch_prints():
    """Imported, never copied: "the re-run happened and produced no
    comparable pair" is one verdict with one exit code, and two spellings of
    it would be two verdicts.

    `print_unverifiable` moved to the licence's shared home when the PYTHON
    branch became its third caller (ruling R19) -- a generic branch reaching
    into the Rust one for a licence sentence is the dependency that module
    exists to prevent. All three still hold ONE object, which is what this
    pins; where it is defined is the second assertion's business."""
    from sensorium.query import refocus_licence

    assert (refocus_typescript._refused_after_rerun
            is refocus_rust._refused_after_rerun)
    assert (refocus_typescript.print_unverifiable
            is refocus_rust._print_unverifiable
            is refocus_cmd.print_unverifiable
            is refocus_licence.print_unverifiable)


@pytest.mark.parametrize("name", [
    "SENSORIUM_FOCUS", "SENSORIUM_INVOCATION", "SENSORIUM_SPOOL",
    "SENSORIUM_MANIFEST_DIR", "SENSORIUM_TIER", "SENSORIUM_TS_PKG",
    "SENSORIUM_TS_ROOT"])
def test_the_recorders_own_variables_are_recognised_as_its_own(name):
    assert refocus_typescript.is_recorder_key(name)


@pytest.mark.parametrize("name", [
    "PATH", "HOME", "NODE_ENV", "VITEST", "VITEST_POOL_ID",
    "MY_SENSORIUM_FOCUS", "SENSORIUMISH"])
def test_an_ordinary_variable_is_not_mistaken_for_the_recorders(name):
    """The rule must not swallow a variable the PROGRAM reads: a check that
    excludes too much grants a licence over a real difference."""
    assert not refocus_typescript.is_recorder_key(name)
