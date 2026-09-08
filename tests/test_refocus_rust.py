"""`sensorium refocus` on a Rust trace, on fixture traces and no cargo.

Every test here drives the real command through `refocus_cmd.run`, or the
real function under test, over traces built as DATA (`tests/rust_traces.py`).
The one thing that cannot be real is the driver: `subprocess.run` is patched,
and the patch is asserted -- what argv, from what directory, with what
environment -- because those three ARE the re-run, and a test that only
checked the verdict would pass over a driver invoked from the wrong place.

The traces, the fake driver and the store reads are
`tests/refocus_rust_fixtures.py`; what the licence may CLAIM about a Rust
pair is `tests/test_refocus_licence_rust.py`, and the rule that keeps a
re-run's own child process out of the pair is
`tests/test_refocus_rust_children.py`.
"""
import subprocess
import time
from pathlib import Path

import pytest

from sensorium import paths
from sensorium.query import refocus_cmd, refocus_rust
from sensorium.query.vocab import PYTHON, RUST
from sensorium.store import db
from sensorium.store.reader import Trace
from tests.helpers import RUST_CAPABILITIES
from tests.refocus_rust_fixtures import (ORIG, OTHER, OTHER_ORIGINAL, PAIR,
                                         STALE, FakeDriver, _drive,
                                         _drop_meta, _never, _read_meta, args,
                                         original, refuse, rust_digest,
                                         workspace)

# -- the five pre-rerun refusals, in the design's order ---------------------
def test_window_is_refused_first_and_nothing_is_re_run(tmp_path, monkeypatch,
                                                       capsys):
    """Refusal 1. Given ALONGSIDE a second fault (no driver), so the test
    pins the ORDER and not merely the sentence."""
    run, _ = original(tmp_path, monkeypatch)
    monkeypatch.delenv("SENSORIUM_CARGO_SENSORIUM", raising=False)
    monkeypatch.setattr(refocus_rust.shutil, "which", lambda _n: None)
    monkeypatch.setattr(refocus_rust.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute", window="x")
    assert code == 2
    assert (f"error: cannot refocus {run}: --window is not available for a "
            "Rust trace (rung 4 leaves it out); nothing was re-run") in err


def test_a_multi_process_invocation_is_refused_and_names_the_count(
        tmp_path, monkeypatch, capsys):
    """Refusal 2, with design amendment B2's wording: the count is the
    invocation's RUNNER processes, test binaries and doctests alike."""
    run, _ = original(tmp_path, monkeypatch, invocation_processes=2)
    monkeypatch.setenv("SENSORIUM_CARGO_SENSORIUM", "/bin/true")
    monkeypatch.setattr(refocus_rust.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert (f"run {run} is one of 2 processes of its invocation (test "
            "binaries and doctests); refocus needs an invocation with a "
            "single-target selector (--lib, --test X, --bin X) so one trace "
            "is the answer; nothing was re-run") in err


def test_an_unrecorded_process_count_is_named_as_unrecorded(tmp_path,
                                                            monkeypatch):
    """The same refusal when the key is absent -- and the count is NAMED as
    unrecorded rather than rendered as `None` or defaulted to a number."""
    meta = {"workspace_root": "/w", "run_id": ORIG}
    sentence = refocus_rust.refusal(meta, args(ORIG), "/bin/true")
    assert sentence.startswith(
        f"run {ORIG} is one of an unrecorded number of processes")
    assert "None" not in sentence


def test_a_trace_without_workspace_root_is_refused(tmp_path, monkeypatch,
                                                   capsys):
    """Refusal 3. `workspace_root` arrived with cargo-sensorium 0.5.0, and
    the sentence says which recorder cannot answer."""
    run, root = original(tmp_path, monkeypatch)
    _drop_meta(tmp_path, run, "workspace_root")
    monkeypatch.setenv("SENSORIUM_CARGO_SENSORIUM", "/bin/true")
    monkeypatch.setattr(refocus_rust.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert (f"run {run} records no workspace_root (recorded by "
            "cargo-sensorium 0.4.0 or earlier); nothing was re-run") in err


def test_a_workspace_that_is_gone_is_refused_by_path(tmp_path, monkeypatch,
                                                     capsys):
    """Refusal 4. The workspace, not the cwd: a Rust re-run starts where
    cargo was invoked, and that is the directory that must still exist."""
    gone = str(tmp_path / "deleted")
    run, _ = original(tmp_path, monkeypatch, workspace_root=gone)
    monkeypatch.setenv("SENSORIUM_CARGO_SENSORIUM", "/bin/true")
    monkeypatch.setattr(refocus_rust.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert f"workspace {gone} no longer exists; nothing was re-run" in err


def test_no_driver_is_refused_and_names_both_ways_to_supply_one(
        tmp_path, monkeypatch, capsys):
    """Refusal 5, and LAST: it is the only one of the five that a reader
    cannot act on without a toolchain, so the four cheaper faults are
    reported ahead of it."""
    run, _ = original(tmp_path, monkeypatch)
    monkeypatch.delenv("SENSORIUM_CARGO_SENSORIUM", raising=False)
    monkeypatch.setattr(refocus_rust.shutil, "which", lambda _n: None)
    monkeypatch.setattr(refocus_rust.subprocess, "run", _never)

    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert ("no cargo-sensorium to re-run with -- set "
            "SENSORIUM_CARGO_SENSORIUM or put cargo-sensorium on PATH; "
            "nothing was re-run") in err


def test_the_five_refusals_fire_in_the_designs_order(tmp_path, monkeypatch):
    """One trace that fails every check, asked five times: each answer is
    the FIRST outstanding fault, and removing it uncovers the next."""
    gone = str(tmp_path / "deleted")
    meta = {"run_id": ORIG, "invocation_processes": 3}
    order = []
    order.append(refocus_rust.refusal(meta, args(ORIG, window="x"), None))
    order.append(refocus_rust.refusal(meta, args(ORIG), None))
    meta["invocation_processes"] = 1
    order.append(refocus_rust.refusal(meta, args(ORIG), None))
    meta["workspace_root"] = gone
    order.append(refocus_rust.refusal(meta, args(ORIG), None))
    meta["workspace_root"] = str(tmp_path)
    order.append(refocus_rust.refusal(meta, args(ORIG), None))
    assert [s.split(";")[0].split(" (")[0] for s in order] == [
        "--window is not available for a Rust trace",
        f"run {ORIG} is one of 3 processes of its invocation",
        f"run {ORIG} records no workspace_root",
        f"workspace {gone} no longer exists",
        "no cargo-sensorium to re-run with -- set "
        "SENSORIUM_CARGO_SENSORIUM or put cargo-sensorium on PATH",
    ]
    meta["run_id"] = ORIG
    assert refocus_rust.refusal(meta, args(ORIG), "/bin/true") is None


def test_a_rust_trace_that_declares_no_refocus_capability_still_refuses(
        tmp_path, monkeypatch, capsys):
    """The OLD Rust trace -- cargo-sensorium 0.4.0 or earlier, which
    declared `capabilities.refocus: false`. It never reaches this module:
    the shared capability gate refuses it, in the generic sentence, and the
    note beside it no longer promises rung 4."""
    caps = {**RUST_CAPABILITIES, "refocus": False}
    run, _ = original(tmp_path, monkeypatch, capabilities=caps)
    code, err = refuse(capsys, run, "compute")
    assert code == 2
    assert ("refocus needs refocus, which recorder sensorium-rt 0.4.0 "
            "declares it does not produce (capabilities.refocus: false); "
            "nothing was checked") in err
    assert "arrives with rung 4" not in err
    assert "cargo sensorium --focus ... test|run" in err


def test_the_retired_note_is_gone_from_the_tree():
    """`RUST.no_rerun_note` is retired (design section 3.2). Grepped rather
    than asserted on the constant alone: a string that survives in a doc or
    a fixture is a promise the tool no longer keeps."""
    root = Path(__file__).resolve().parent.parent
    here = Path(__file__).resolve()
    hits = [p for d in ("src", "tests", "corpus")
            for p in (root / d).rglob("*.py")
            if p != here and "arrives with rung 4" in p.read_text()]
    assert hits == []
    assert "arrives with rung 4" not in RUST.no_rerun_note
    assert RUST.no_rerun_note.startswith("no rerun was attempted; `cargo "
                                         "sensorium --focus ...")


# -- the argv --------------------------------------------------------------
def test_rerun_argv_is_the_driver_the_link_the_tier_the_focus_and_cargo():
    meta = {"run_id": ORIG, "env": {"SENSORIUM_TIER": "off"},
            "focus": ["load"], "cargo_args": ["test", "--test", "smoke"]}
    assert refocus_rust.rerun_argv(meta, ["dump"], "/d/cargo-sensorium") == [
        "/d/cargo-sensorium", "--refocus-of", ORIG, "--tier", "off",
        "--focus", "load", "--focus", "dump", "test", "--test", "smoke"]


def test_rerun_argv_omits_the_tier_when_the_original_recorded_none():
    """Omitted, never guessed: with no `--tier` the driver applies its own
    default, and writing one here would assert a tier nothing recorded."""
    meta = {"run_id": ORIG, "env": {"PATH": "/usr/bin"},
            "cargo_args": ["run"]}
    assert refocus_rust.rerun_argv(meta, ["compute"], "d") == [
        "d", "--refocus-of", ORIG, "--focus", "compute", "run"]


def test_rerun_argv_keeps_the_originals_focus_first_and_never_drops_it():
    """A refocus only ever captures MORE (`_merged_focus`), and the order is
    the original's values then the caller's. A caller who re-types a value
    the original already had collapses it, which is what the driver's own
    set rule would have done with it."""
    meta = {"run_id": ORIG, "focus": ["a", "b"], "cargo_args": ["run"]}
    assert refocus_rust.rerun_argv(meta, ["b", "c"], "d") == [
        "d", "--refocus-of", ORIG,
        "--focus", "a", "--focus", "b", "--focus", "c", "run"]


def test_rerun_argv_passes_cargo_args_through_verbatim():
    meta = {"run_id": ORIG, "cargo_args": ["test", "--lib", "--", "--nocapture"]}
    argv = refocus_rust.rerun_argv(meta, [], "d")
    assert argv[-4:] == ["test", "--lib", "--", "--nocapture"]
    assert argv[:3] == ["d", "--refocus-of", ORIG]


# -- the pair lookup ---------------------------------------------------------
def test_find_pair_returns_nothing_when_no_trace_is_linked(tmp_path,
                                                           monkeypatch):
    run, _ = original(tmp_path, monkeypatch)
    assert refocus_rust.find_pair(paths.traces_dir(), run, 0.0) == ([], [])


def test_find_pair_finds_the_one_trace_the_re_run_wrote(tmp_path,
                                                        monkeypatch):
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [])


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
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [])


def test_find_pair_excludes_a_link_to_a_DIFFERENT_original(tmp_path,
                                                           monkeypatch):
    """The link filter is an EQUALITY, and only this case says so. A refocus
    of a DIFFERENT original, running at the same time and into the same
    store, writes a trace that is linked and whose recording started after
    this launch -- every condition but the one that matters. Read as `if not
    linked` it would join this pair, and a re-run that produced exactly one
    trace would be refused by count, naming the single-target selector at a
    caller whose selector was already single."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=OTHER, refocus_of=OTHER_ORIGINAL,
             start_ts=launched + 1)
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [])


def test_find_pair_returns_both_when_the_invocation_wrote_two(tmp_path,
                                                              monkeypatch):
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    for rid in ("20260101-000100-pairaa", "20260101-000100-pairbb"):
        original(tmp_path, monkeypatch, run_id=rid, refocus_of=run,
                 start_ts=launched + 1)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        ["20260101-000100-pairaa", "20260101-000100-pairbb"], [])


def test_find_pair_excludes_a_trace_it_cannot_open(tmp_path, monkeypatch):
    """`start_ts` is REQUIRED meta, so a format-4 trace without it is one
    `db.open_trace` refuses outright -- and a file this process cannot open
    is not a trace the driver just wrote. Named for the mechanism that
    actually fires: the type guard below is a different one."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts=launched + 1)
    _drop_meta(tmp_path, PAIR, "start_ts")
    with pytest.raises(db.TraceFormatError):
        db.open_trace(paths.traces_dir() / f"{PAIR}.db")
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [], [])


def test_find_pair_excludes_a_start_time_that_is_not_a_time(tmp_path,
                                                            monkeypatch):
    """Present but unreadable: `missing_required` asks whether the key is
    there, not what is in it. A start time that is not a number cannot be
    compared against the launch, and "cannot be compared" is not "recent" --
    without the type guard this is a `TypeError` out of a query command."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             start_ts="soon")
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [], [])


# -- the launch ------------------------------------------------------------
def test_the_driver_is_launched_from_the_workspace_under_the_same_store(
        tmp_path, monkeypatch, capsys):
    """The three things that ARE the re-run: what was run, from where, and
    with which store. `SENSORIUM_DIR` is the ABSOLUTE store the original
    came from -- a relative one would follow the child into the workspace
    and write the new trace where nothing looks for it."""
    pair = [(PAIR, ORIG)]
    run, root, code, fake = _drive(tmp_path, monkeypatch, pairs=pair)
    capsys.readouterr()
    (argv, kw), = fake.calls
    assert argv == ["/d/cargo-sensorium", "--refocus-of", run,
                    "--focus", "compute", "run"]
    assert kw["cwd"] == str(root)
    assert kw["env"]["SENSORIUM_DIR"] == str(paths.trace_root().resolve())
    assert Path(kw["env"]["SENSORIUM_DIR"]).is_absolute()
    # The caller's environment, with nothing else set or stripped.
    assert kw["env"]["PATH"] == __import__("os").environ["PATH"]
    # stderr is NOT captured: a rebuild's progress belongs to the person
    # waiting for it. stdout is, so the `run:` lines can be reported.
    assert kw["stderr"] is None
    assert kw["stdout"] is subprocess.PIPE
    assert code == 0


def test_a_re_run_that_produced_no_linked_trace_is_refused_after_the_fact(
        tmp_path, monkeypatch, capsys):
    """Exit 3, not 2: the driver DID run, so no edit to the command settles
    it. The driver's exit code is the reason, and its own output -- which
    streamed through uncaptured -- is where the detail is."""
    run, _root, code, _fake = _drive(tmp_path, monkeypatch, returncode=101)
    out = capsys.readouterr().out
    assert code == 3
    assert (f"refocus verdict: REFUSED -- the re-run produced no trace "
            f"linked to {run} (driver exit 101); see the driver's output "
            "above") in out
    assert "what sensorium sees at all" in out          # blind spots, still


def test_two_linked_traces_are_refused_with_the_single_target_sentence(
        tmp_path, monkeypatch, capsys):
    """`cargo test` on a crate with two test binaries. Which trace is "the"
    re-run has no answer, and inventing one is the whole failure mode."""
    pairs = [("20260101-000100-pairaa", ORIG), ("20260101-000100-pairbb",
                                                ORIG)]
    run, _root, code, _fake = _drive(tmp_path, monkeypatch, pairs=pairs)
    out = capsys.readouterr().out
    assert code == 3
    assert (f"refocus verdict: REFUSED -- the re-run produced 2 traces "
            f"linked to {run} (20260101-000100-pairaa, "
            "20260101-000100-pairbb); refocus needs an invocation with a "
            "single-target selector (--lib, --test X, --bin X) so one trace "
            "is the answer") in out


# -- the verdict, the licence, the stamps ----------------------------------
def test_a_matching_pair_is_compared_and_stamped_into_the_new_trace(
        tmp_path, monkeypatch, capsys):
    seen = {}
    real = refocus_rust.__dict__  # the import is inside `_verify`; wrap it
    import sensorium.query.diff_cmd as diff_cmd
    inner = diff_cmd.compare

    def spy(a, b, moves=None):
        seen["pair"] = (Path(a.path).stem if hasattr(a, "path") else None,
                        b.meta["run_id"])
        return inner(a, b, moves)
    monkeypatch.setattr(diff_cmd, "compare", spy)

    run, _root, code, _fake = _drive(tmp_path, monkeypatch,
                                     pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert code == 0
    assert seen["pair"][1] == PAIR                 # compared THE pair
    assert "refocus verdict: MATCH" in out
    assert f"run: {PAIR}" in out
    assert _read_meta(PAIR, "refocus_verdict") == "MATCH"
    assert _read_meta(PAIR, "refocus_of") == run
    assert real is refocus_rust.__dict__


def test_the_rust_blind_spots_are_printed_after_the_verdict(tmp_path,
                                                            monkeypatch,
                                                            capsys):
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    for line in RUST.refocus_blind_spots:
        assert f"  - {line}" in out
    assert RUST.refocus_blind_spots[2].startswith(
        "the re-run's rebuild is its own cost")
    assert PYTHON.refocus_blind_spots == ()


def test_the_driver_run_lines_are_reported_and_decide_nothing(
        tmp_path, monkeypatch, capsys):
    """The link comes from the store, never from this line -- but the line
    is printed, because a reader watching a rebuild should see what the
    driver said it recorded."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert "driver reported: run: x  pid: 1  exit: 0" in out
    assert f"run: {PAIR}" in out          # ...and the id the STORE answered


def test_the_source_check_reads_the_rust_digest_width(tmp_path, monkeypatch,
                                                      capsys):
    """`cargo-sensorium` writes all 64 hex characters of the sha256; the
    Python recorder writes the first 16. Compared at the recorded width,
    both are exact -- compared with `!=`, every Rust file read as changed."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert "source: unchanged (1 file(s) compared by content" in out
    assert "source: CHANGED" not in out


def test_the_environment_is_compared_between_the_two_traces(tmp_path,
                                                            monkeypatch,
                                                            capsys):
    """Design section 3.2's `reads` column: `env` recorded in BOTH traces.
    Comparing the recorded test-binary environment against this CLI's own
    would diff cargo's variables against their absence and report a changed
    world on every run."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert "env: unchanged (1 variables compared" in out
    assert "env: CHANGED" not in out


def test_a_pair_whose_trace_records_no_environment_says_so(tmp_path,
                                                           monkeypatch):
    """A re-run whose trace holds no `env` cannot be compared against the
    original's, and the honest answer is unverifiable -- never a diff
    against an empty dict, which would report every variable as removed."""
    run, _root = original(tmp_path, monkeypatch)
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run)
    _drop_meta(tmp_path, PAIR, "env")
    orig = Trace.open(paths.traces_dir() / f"{run}.db")
    new = Trace.open(paths.traces_dir() / f"{PAIR}.db")

    line, caveat, fact = refocus_rust._env_of(orig.meta, new)
    assert line == ("env: unverifiable -- the re-run's trace records no "
                    "environment to compare against")
    assert "nothing rules out the two runs getting different input" in caveat
    assert fact is None


# -- the dispatch ----------------------------------------------------------
def test_a_python_trace_never_reaches_the_rust_branch(tmp_path, monkeypatch):
    """The dispatch is on the trace's own `lang` and on nothing else."""
    from tests.helpers import RUST_CAPABILITIES as _caps
    assert _caps["refocus"] is True
    run, _ = original(tmp_path, monkeypatch)
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert t.lang == "rust"


@pytest.mark.parametrize("key", ["workspace_root", "invocation_processes"])
def test_the_fixture_carries_the_keys_the_driver_writes(tmp_path, monkeypatch,
                                                        key):
    run, _ = original(tmp_path, monkeypatch)
    assert _read_meta(run, key) is not None
    assert _read_meta(run, "refocus_of") is None       # absent, never null


# -- the recorder's own environment ----------------------------------------
@pytest.mark.parametrize("name", [
    "SENSORIUM_FOCUS", "SENSORIUM_INVOCATION", "SENSORIUM_SPOOL",
    "SENSORIUM_TIER", "SENSORIUM_CARGO_SENSORIUM", "RUSTC_WORKSPACE_WRAPPER",
    "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER"])
def test_the_recorders_own_variables_are_recognised_as_its_own(name):
    assert refocus_rust._is_recorder_key(name)


@pytest.mark.parametrize("name", [
    "PATH", "HOME", "CARGO", "CARGO_MANIFEST_DIR", "RUSTC", "CARGO_TARGET_DIR",
    "SENSORIUMISH", "MY_SENSORIUM_FOCUS"])
def test_an_ordinary_variable_is_not_mistaken_for_the_recorders(name):
    """The rule must not swallow a variable the PROGRAM reads: a check that
    excludes too much grants a licence over a real difference."""
    assert not refocus_rust._is_recorder_key(name)


def test_the_recorders_own_variables_are_named_and_never_withhold(
        tmp_path, monkeypatch, capsys):
    """A focused re-run changes `SENSORIUM_FOCUS` BY DEFINITION, mints a new
    invocation and spool, and -- because `--focus` keys a fresh shim --
    hands cargo a different wrapper and runner. Compared, those fire on
    every Rust refocus and the licence is withheld permanently on the
    instrument's own footprint. Excluded, and NAMED: the same judgement
    `_UNCOMPARED_ENV` already makes about SENSORIUM_DIR."""
    mine = {"SENSORIUM_FOCUS": "load", "SENSORIUM_SPOOL": "/a",
            "RUSTC_WORKSPACE_WRAPPER": "/shim/one"}
    theirs = {"SENSORIUM_FOCUS": "load,dump", "SENSORIUM_SPOOL": "/b",
              "RUSTC_WORKSPACE_WRAPPER": "/shim/two"}
    run, _ = original(tmp_path, monkeypatch, env={"PATH": "/usr/bin", **mine})
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             env={"PATH": "/usr/bin", **theirs})
    orig = Trace.open(paths.traces_dir() / f"{run}.db")
    new = Trace.open(paths.traces_dir() / f"{PAIR}.db")

    line, caveat, fact = refocus_rust._env_of(orig.meta, new)
    assert caveat is None                       # nothing real differed
    assert "env: unchanged (1 variables compared" in line
    for name in sorted(mine):
        assert name in line and name in fact    # named, never hidden
    assert "the recorder's own, also not compared" in line


def test_a_real_environment_difference_still_fires_beside_the_recorders_own(
        tmp_path, monkeypatch):
    """The exclusion is of the instrument's variables and of nothing else."""
    run, _ = original(tmp_path, monkeypatch,
                      env={"PATH": "/usr/bin", "TZ": "UTC",
                           "SENSORIUM_FOCUS": "load"})
    original(tmp_path, monkeypatch, run_id=PAIR, refocus_of=run,
             env={"PATH": "/usr/bin", "TZ": "CET",
                  "SENSORIUM_FOCUS": "load,dump"})
    orig = Trace.open(paths.traces_dir() / f"{run}.db")
    new = Trace.open(paths.traces_dir() / f"{PAIR}.db")

    line, caveat, fact = refocus_rust._env_of(orig.meta, new)
    assert "env: CHANGED since the original run -- 1 variable(s) differ: TZ" \
        in line
    assert "1 environment variable(s) differ between the two runs (TZ)" \
        in caveat
    assert fact is None


# -- the categorical blind-spot block, per recorder ------------------------
PYTHON_BOUND = ("Python code that this run traced",
                "Python's own threading/_thread",
                "site-packages", "PYTHONPATH",
                "__repr__ inside hooks",
                "asyncio")


def _diverging_pair(tmp_path, monkeypatch, **kw):
    """A re-run that recorded a DIFFERENT program: another causal stream, so
    the pair diverges on shape rather than on anything in the world."""
    from tests.rust_traces import swallow_trace
    return swallow_trace(tmp_path, monkeypatch, **kw)


def _assert_rust_block(out):
    assert ("what sensorium sees at all: Rust code in the workspace units "
            "cargo rebuilt through this recorder's wrapper") in out
    assert ("  - any thread whose body ran no instrumented code: it leaves "
            "no fingerprint, so it is not among the compared") in out
    assert ("  - any code outside the instrumented units: dependency "
            "crates, the standard library, build scripts and proc macros, "
            "and every unit that fell back uninstrumented") in out
    assert ("  - the recorder's own footprint: capturing values runs the "
            "program's own Debug impls inside the probe") in out
    # The one shared line that names the units of concurrent work says
    # them in this recorder's words -- the same rule as the four above, on
    # a line whose other clauses are true of any recorder.
    assert ("the order libtest's per-test threads and spawned threads "
            "interleaved in: recorded, never compared") in out
    for line in RUST.refocus_blind_spots:
        assert f"  - {line}" in out
    for phrase in PYTHON_BOUND:
        assert phrase not in out


def test_a_rust_match_prints_the_rust_blind_spots_and_no_python_ones(
        tmp_path, monkeypatch, capsys):
    _run, _root, code, _fake = _drive(tmp_path, monkeypatch,
                                      pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert code == 0 and "refocus verdict: MATCH" in out
    _assert_rust_block(out)


def test_a_rust_divergence_prints_the_rust_blind_spots_and_no_python_ones(
        tmp_path, monkeypatch, capsys):
    _run, _root, code, _fake = _drive(tmp_path, monkeypatch,
                                      pairs=[(PAIR, ORIG)],
                                      build=_diverging_pair)
    out = capsys.readouterr().out
    assert code == 1 and "refocus verdict: DIVERGED" in out
    _assert_rust_block(out)


def test_a_rust_refusal_after_the_rerun_prints_the_rust_blind_spots(
        tmp_path, monkeypatch, capsys):
    """REFUSED is a verdict, so the block that bounds what a verdict claims
    prints here too -- and "the re-run's rebuild is its own cost" is the
    most relevant line there is for a reader whose re-run produced nothing
    (design section 3.2 said the lines print after a Rust verdict; this is
    the third of the three)."""
    _run, _root, code, _fake = _drive(tmp_path, monkeypatch, returncode=101)
    out = capsys.readouterr().out
    assert code == 3 and "refocus verdict: REFUSED" in out
    _assert_rust_block(out)


def test_the_python_block_is_what_it_always_printed(tmp_path, monkeypatch):
    """The legacy fence. `PYTHON`'s four language-bound lines are the
    strings `refocus_cmd` held before they moved, character for character,
    and the Python column adds nothing after them."""
    from types import SimpleNamespace

    from sensorium.query.vocab import blind_spots
    run, _ = original(tmp_path, monkeypatch)
    rust = Trace.open(paths.traces_dir() / f"{run}.db")
    assert len(blind_spots(rust)) == 9 + len(RUST.refocus_blind_spots)

    # `blind_spots` reads `trace.lang` and nothing else, which is what makes
    # the block a statement about the RECORDER rather than about this run.
    lines = blind_spots(SimpleNamespace(lang="python"))
    assert len(lines) == 9                      # Python adds nothing
    assert lines[0] == (
        "what sensorium sees at all: Python code that this run traced, in "
        "files under the run's own root. Nothing else. No verdict here -- "
        "MATCH, DIVERGED or REFUSED -- says anything about:")
    assert lines[2] == (
        "  - any thread not started through Python's own threading/_thread")
    assert lines[4] == (
        "  - any code outside the run's root: the stdlib, site-packages, "
        "installed dependencies, PYTHONPATH modules, and whatever this "
        "run's own --include/--exclude filtered out")
    assert lines[7] == (
        "  - argument and return values, per-line state, timing, the order "
        "threads ran in relative to one another, and the order asyncio "
        "tasks interleaved in: recorded, never compared")
    assert lines[8] == (
        "  - the recorder's own footprint: deeper capture runs the "
        "program's __repr__ inside hooks that suppress themselves, so an "
        "instrument that changes the program leaves no mark on the "
        "fingerprint")
    assert PYTHON.refocus_blind_spots == ()


# -- one driver resolution, three copies of it -----------------------------
def _driver_copies():
    """The three places this project resolves `cargo-sensorium`. They are
    separate ON PURPOSE -- `corpus/` is not in the wheel, so the query
    command cannot import it -- which makes drift between them silent."""
    import importlib.util
    from tests.test_focus_refusal import _driver as focus_refusal_driver
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "_run_corpus_for_drift", root / "corpus" / "run_corpus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return (refocus_rust.driver, mod.cargo_driver, focus_refusal_driver)


@pytest.mark.parametrize("env,which,expected", [
    ("/from/env", "/from/path", "/from/env"),      # the variable wins
    (None, "/from/path", "/from/path"),            # then PATH
    (None, None, None),                            # then nothing, honestly
    ("", "/from/path", "/from/path"),              # empty is not a driver
])
def test_all_three_driver_resolutions_agree(monkeypatch, env, which,
                                            expected):
    import shutil as _shutil
    if env is None:
        monkeypatch.delenv("SENSORIUM_CARGO_SENSORIUM", raising=False)
    else:
        monkeypatch.setenv("SENSORIUM_CARGO_SENSORIUM", env)
    monkeypatch.setattr(_shutil, "which", lambda _n: which)
    answers = [fn() for fn in _driver_copies()]
    assert answers == [expected, expected, expected]


# -- the digest floor ------------------------------------------------------
@pytest.mark.parametrize("digest", ["", "abc", "0" * 15])
def test_a_digest_too_short_to_identify_a_file_is_unverifiable(tmp_path,
                                                               digest):
    """A prefix comparison against a narrow digest matches almost anything,
    and `""` matches EVERY file: without a floor, a trace recording an empty
    digest would read `source: unchanged` over code nobody ever hashed --
    the check-that-did-not-run reported as a check that passed."""
    from sensorium.query.refocus_world import _source_state
    (tmp_path / "lib.rs").write_text("fn main() {}\n")
    line, caveat, fact = _source_state(
        {"source_hashes": {str(tmp_path / "lib.rs"): digest}})
    assert "source: unverifiable" in line
    assert "digest too short to identify their contents" in line
    assert "would match files this run never saw" in caveat
    assert fact is None
    assert "unchanged" not in line


def test_a_digest_at_the_floor_is_compared_normally(tmp_path):
    """16 hex characters is what `boot.hash_file` writes, so the floor must
    not refuse a trace this project's own Python recorder produced."""
    import hashlib as _h
    from sensorium.query.refocus_world import _source_state
    f = tmp_path / "lib.rs"
    f.write_text("fn main() {}\n")
    full = _h.sha256(f.read_bytes()).hexdigest()
    for width in (16, 64):
        line, caveat, fact = _source_state(
            {"source_hashes": {str(f): full[:width]}})
        assert "source: unchanged (1 file(s) compared by content" in line
        assert caveat is None and fact is not None
