"""`sensorium redact` -- the retrofit's command, through the real CLI.

Every assertion here is made on a SUBPROCESS's stdout, stderr, exit status
and the files it left behind, because that is the whole of what this
command is: the judgement is `redact_store.plan`'s (tested in
`tests/test_redact_store_plan.py`) and the writing is `apply`'s (tested in
`tests/test_redact_store_apply.py`). What is under test below is the part
a reader and a script actually meet -- the LINES (C12), the exits (§7),
the byte-identity of `--dry-run` (C10), the modes (C11), the stale-key
sweep in BOTH modes (C13, P3) -- and the three commands that have to be
able to read a retrofitted trace afterwards.

The spellings are pinned to the character on purpose. `corpus/redact_retrofit`
and E16 part C both PARSE these lines: a line reworded here is an
instrument that reads nothing there, and the failure mode of an instrument
that reads nothing is a green run over an unmeasured claim.

Traces are built synthetically (C15) by Task 2's `_python`, into a scratch
directory and then COPIED into the store under the run id each test needs
-- `_python` writes one fixed run id, and `--all` has nothing to say
unless the store holds more than one trace.
"""
import argparse
import json
import re
import shutil
import sqlite3
import stat
import sys
from pathlib import Path

from sensorium import redact, redact_key, redact_store
from sensorium.query import redact_cmd
from sensorium.store import db
from sensorium.store.writer import TraceWriter
from tests.helpers import finalize_synthetic, record_script, run_cli
from tests.refocus_programs import LOOP
from tests.test_redact_store_plan import (ENV, KNOBS, RUN, _dead_pid,
                                          _json_hash, _key, _python,
                                          _rewrite, _set_meta)

# The instrument's own regex, imported rather than re-spelled: E16 part C
# PARSES these lines, and a line form this suite pins that `e16c_cells.LINE`
# cannot match is an instrument reading nothing under a green run.
sys.path.insert(0, str(Path(__file__).resolve().parent / "acceptance_e16"))
from e16c_cells import LINE                                       # noqa: E402

#: The one line the whole command exists to print, exactly as C12 spells it
#: and as `_python`'s trace makes it true: one firing env name, six values
#: (a bound argument, a map value, a RETURN, a RAISE message, an unwind
#: message, one output row), and the mode every trace in the store sits at.
ONE = re.compile(
    r"^run \S+: env 1 redacted \(API_KEY\); values 6; mode 644 -> 600$", re.M)

SUMMARY_TAIL = ("); spools under target/ and the TypeScript spool dirs are "
                "not reached")


def _cli(tmp_path, args, **kw):
    return run_cli(args, cwd=tmp_path, sensorium_dir=Path(tmp_path) / "sdir",
                   **kw)


def _traces(tmp_path) -> Path:
    """The store's `traces/`, at the 0700 `paths.traces_dir` would have
    created it at. Explicit because `mkdir` without a mode takes the
    umask, which would leave every `--all` test below quietly exercising
    C11's directory tightening -- and after R11 quietly exiting 0 for it.
    A test that wants a loose directory says so."""
    d = Path(tmp_path) / "sdir" / "traces"
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)
    return d


def _args(**kw) -> argparse.Namespace:
    """`run`'s parsed arguments, for the two cases that cannot be driven
    through `run_cli`: an `apply` and a `plan` that RAISE are reachable
    only by substitution, and the CLI runs in a subprocess where this
    process's monkeypatches are not."""
    return argparse.Namespace(**{"run": None, "all": False,
                                 "dry_run": False, **kw})


def _plant(tmp_path, stem, *, mode=0o644, settled=False, key=None, **kw):
    """One `_python` trace in the store under `stem`, sidecars and all.

    Built in a scratch directory of its own and copied in, because
    `_python` writes one run id and `--all` needs several. `settled` runs
    Task 2's in-place rewrite first, which is the only way to state the
    trace a SECOND pass meets: everything already taken, under the store's
    own key.
    """
    src = _python(Path(tmp_path) / f"build-{stem}",
                  env=kw.pop("env", None) or dict(ENV), **kw)
    if settled:
        _rewrite(src, redact_store.plan(src, key, KNOBS))
    return _copy_in(tmp_path, src, stem, mode)


def _copy_in(tmp_path, src, stem, mode) -> Path:
    """`src` and its sidecars into the store under `stem`, at `mode`."""
    dst = _traces(tmp_path) / f"{stem}.db"
    for suffix in ("", "-wal", "-shm"):
        beside = src.with_name(src.name + suffix)
        if beside.exists():
            shutil.copy(beside, dst.with_name(dst.name + suffix))
    dst.chmod(mode)
    return dst


def _plant_bare(tmp_path, stem, *, mode=0o600) -> Path:
    """A trace holding NOTHING rule v1 takes, stamped `mode: "off"`.

    The one shape `_python` cannot state: every value is a number or a
    benign string, the environment is `HOME` alone, and the stamp says the
    rule was off when it was recorded. A pass over it takes no name and no
    value and still REWRITES it, because P5 stamps a trace that was not
    already `mode: "on"` -- which is the case the per-trace line used to
    call `nothing to redact` while the summary counted it redacted.

    Planted at 0600 by default, so the rewrite is the ONLY thing that can
    make the call exit 0: a mode clause would give the exit somewhere else
    to come from and the test would no longer discriminate.
    """
    src = Path(tmp_path) / f"build-{stem}" / "sdir" / "traces" / f"{RUN}.db"
    w = TraceWriter(src, batch=1)
    code = w.intern_code("prog.py", "add", 1)
    call = w.add_event(1, 1, "CALL", None, code, 1,
                       {"args": {"n": {"k": "num", "v": 1}}})
    frame = w.open_frame(None, code, call, 0, 1)
    ret = w.add_event(2, 1, "RETURN", frame, code, None,
                      {"value": {"k": "num", "v": 2}})
    w.close_frame(frame, ret, "return")
    w.add_output(ret, "stdout", "2\n")
    env = {"HOME": "/tmp/u"}
    finalize_synthetic(w, env=dict(env), env_hash=_json_hash(env),
                       children=[], redaction={"rule": "v1", "mode": "off"})
    w.close()
    return _copy_in(tmp_path, src, stem, mode)


def _mode(path) -> int:
    return stat.S_IMODE(Path(path).stat().st_mode)


def _meta(path) -> dict:
    conn = sqlite3.connect(path)
    try:
        return db.all_meta(conn)
    finally:
        conn.close()


# -- one trace ------------------------------------------------------------

def test_one_trace_line_and_exit_zero(tmp_path):
    _key(tmp_path)
    _plant(tmp_path, RUN)

    r = _cli(tmp_path, ["redact", RUN])

    assert r.returncode == 0, r.stdout + r.stderr
    assert ONE.search(r.stdout), r.stdout


def test_dry_run_stdout_is_byte_identical_and_writes_nothing(tmp_path):
    """C10, the clause H4 is a diff of two stdouts. A dry run that printed
    even one character the real run does not would turn that measurement
    into a judgement about wording.

    The store starts with NO `redaction.key`, so "writes nothing" is
    tested at its strongest: minting the key is a write, and a dry run
    that minted one would leave a 32-byte secret in a store whose owner
    had asked for nothing to change (ruling R1). It is also what makes
    C10 unconditional -- the lines carry names, counts and modes, none of
    which a key decides, so an unkeyed dry run and a keyed real run print
    the same bytes.

    What the dry run DOES leave is asserted beside what it does not (R19):
    the trace's bytes and mode are untouched and no key is minted, but the
    call is logged to `invocations.jsonl` like every other -- which is why
    the stderr line says `no trace was changed` rather than claiming
    nothing was written at all.
    """
    path = _plant(tmp_path, RUN)
    before = path.read_bytes()
    log = Path(tmp_path) / "sdir" / "invocations.jsonl"
    assert not log.exists()

    dry = _cli(tmp_path, ["redact", RUN, "--dry-run"])

    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert path.read_bytes() == before
    assert _mode(path) == 0o644
    assert dry.stderr.splitlines() == ["dry run: no trace was changed"]
    assert not (Path(tmp_path) / "sdir" / redact_key.KEY_FILE).exists()
    # what it left: its own row in the log, naming the flag it ran under
    logged = json.loads(log.read_text().splitlines()[-1])
    assert logged["argv"] == ["redact", RUN, "--dry-run"]
    assert logged["exit"] == 0

    real = _cli(tmp_path, ["redact", RUN])

    assert real.stdout == dry.stdout
    assert (Path(tmp_path) / "sdir" / redact_key.KEY_FILE).exists()
    assert "dry run" not in real.stderr
    assert path.read_bytes() != before
    assert _mode(path) == 0o600

    settled = path.read_bytes()
    after = _cli(tmp_path, ["redact", RUN, "--dry-run"])

    assert f"run {RUN}: nothing to redact; mode 600" in after.stdout
    assert path.read_bytes() == settled


def test_a_trace_rewritten_only_for_its_stamp_prints_the_counted_form(
        tmp_path):
    """R19, and the closing of T4's untested `env 0 redacted ()` form.

    A `mode: "off"` trace holding nothing the rule takes is REWRITTEN all
    the same: P5 stamps any trace that was not already `mode: "on"`, so the
    file changes, the summary counts it among the redacted and the call
    exits 0. The line has to say the same thing. `nothing to redact` there
    was the one sentence in the pass claiming nothing happened -- printed
    over a file whose bytes had just changed, beside a summary saying
    otherwise -- so a reader comparing the three got two answers.

    The zeros are the point: the line is C12's counted form with the counts
    it actually took, and `e16c_cells.LINE` reads it, which is what keeps
    E16 part C's clause 1 able to see such a trace at all.
    """
    _key(tmp_path)
    path = _plant_bare(tmp_path, "bare-run")
    before = path.read_bytes()

    r = _cli(tmp_path, ["redact", "bare-run"])

    assert r.returncode == 0, r.stdout + r.stderr
    line = next(ln for ln in r.stdout.splitlines()
                if ln.startswith("run bare-run: "))
    assert line == "run bare-run: env 0 redacted (); values 0; mode 600"
    assert f"redacted 1 of 1 traces (0 already clean, 0 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in r.stdout
    # the file really did change, and into the shape the line claims
    assert path.read_bytes() != before
    stamp = _meta(path)["redaction"]
    assert (stamp["by"], stamp["mode"], stamp["values"]) == ("retrofit",
                                                             "on", 0)
    # and the instrument can read the form: `LINE` accepts an empty
    # name list, so clause 1 sees this trace rather than skipping it
    m = LINE.match(line)
    assert m, line
    assert (m.group("id"), m.group("n"), m.group("names")) == ("bare-run",
                                                               "0", "")
    assert (m.group("v"), m.group("mode")) == ("0", "600")


def test_a_dry_run_on_an_absent_store_creates_it(tmp_path):
    """The other half of R19's stderr wording, and the reason it does not
    say "nothing was written": looking for the traces CREATES the store.

    `paths.traces_dir()` makes the root and `traces/` at 0700 on the way to
    globbing them, so a `--dry-run --all` against a store that does not
    exist leaves an empty one behind. Nothing here is a trace -- which is
    exactly what the line now claims, and all it claims.
    """
    sdir = Path(tmp_path) / "sdir"
    assert not sdir.exists()

    r = _cli(tmp_path, ["redact", "--all", "--dry-run"])

    assert r.returncode == 1, r.stdout + r.stderr
    assert f"redacted 0 of 0 traces (0 already clean, 0 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in r.stdout
    assert r.stderr.splitlines() == ["dry run: no trace was changed"]
    assert (sdir / "traces").is_dir()
    assert _mode(sdir / "traces") == 0o700
    assert (sdir / "invocations.jsonl").exists()
    # and still no key and no trace: R1 holds, and the store is empty
    assert not (sdir / redact_key.KEY_FILE).exists()
    assert list((sdir / "traces").iterdir()) == []


def test_the_second_run_says_nothing_to_redact_and_exits_one(tmp_path):
    """P5's other half: a trace already `on` whose pass finds nothing is
    not rewritten and not a change, so a script can ask "is there anything
    left to do here" and read the answer off the exit status."""
    _key(tmp_path)
    _plant(tmp_path, RUN)
    assert _cli(tmp_path, ["redact", RUN]).returncode == 0

    r = _cli(tmp_path, ["redact", RUN])

    assert r.returncode == 1, r.stdout + r.stderr
    assert f"run {RUN}: nothing to redact; mode 600" in r.stdout


# -- the whole store ------------------------------------------------------

def test_all_processes_every_trace_in_sorted_order_and_prints_the_summary(
        tmp_path):
    key = _key(tmp_path)
    # Planted in REVERSE, so `sorted` is what puts them in order rather
    # than the order they were created in: a directory walk returns
    # whatever the filesystem holds, and a test that plants a, b, c and
    # reads back a, b, c cannot tell the two apart.
    _plant(tmp_path, "c-run", settled=True, key=key, mode=0o600)
    _plant(tmp_path, "a-run")
    _plant(tmp_path, "b-run")

    r = _cli(tmp_path, ["redact", "--all"])

    assert r.returncode == 0, r.stdout + r.stderr
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("run ")]
    assert [ln.split(":")[0] for ln in lines] == [
        "run a-run", "run b-run", "run c-run"]
    assert lines[0].endswith("env 1 redacted (API_KEY); values 6; "
                             "mode 644 -> 600")
    assert lines[2] == "run c-run: nothing to redact; mode 600"
    assert f"redacted 2 of 3 traces (1 already clean, 0 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in r.stdout


def test_all_tightens_the_traces_directory_and_says_so(tmp_path):
    """C11 and R11. A store whose directory is 0755 hands every trace in
    it to anyone on the box, whatever the files themselves are set to --
    and `--dry-run` says so without doing it, which is the only way a
    reader can find out before deciding.

    Every trace here is already settled at 0600, so the DIRECTORY is the
    only thing this pass changes and the exit status has nowhere else to
    come from: R11 says a tightened directory is a change, and exit 1
    would tell a script the pass was a no-op on the store it just shut.
    """
    key = _key(tmp_path)
    _plant(tmp_path, RUN, settled=True, key=key, mode=0o600)
    traces = _traces(tmp_path)
    traces.chmod(0o755)

    dry = _cli(tmp_path, ["redact", "--all", "--dry-run"])

    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert f"run {RUN}: nothing to redact; mode 600" in dry.stdout
    assert f"redacted 0 of 1 traces (1 already clean, 0 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in dry.stdout
    assert dry.stdout.rstrip("\n").endswith("; traces/ mode 755 -> 700")
    assert _mode(traces) == 0o755

    real = _cli(tmp_path, ["redact", "--all"])

    assert real.returncode == 0, real.stdout + real.stderr
    assert real.stdout == dry.stdout
    assert _mode(traces) == 0o700


def test_a_refused_trace_is_named_and_the_run_exits_two_with_the_others_done(
        tmp_path):
    """C9. One refusal ends the trace it names and nothing else: an `--all`
    pass that stopped at the first unreadable file would leave a store
    half-retrofitted and say so only by what it did not print."""
    _key(tmp_path)
    good = _plant(tmp_path, "a-run")
    bad = _plant(tmp_path, "b-run")
    _set_meta(bad, trace_format=5)
    bad_bytes = bad.read_bytes()

    r = _cli(tmp_path, ["redact", "--all"])

    assert r.returncode == 2, r.stdout + r.stderr
    refusal = next(ln for ln in r.stdout.splitlines()
                   if ln.startswith("run b-run: "))
    assert refusal.startswith("run b-run: REFUSED: ")
    assert "newer than this sensorium reads" in refusal
    assert bad.read_bytes() == bad_bytes
    assert "run a-run: env 1 redacted (API_KEY)" in r.stdout
    assert _mode(good) == 0o600
    assert f"redacted 1 of 2 traces (0 already clean, 0 skipped, " \
           f"1 refused{SUMMARY_TAIL}" in r.stdout


def test_a_clean_trace_at_0644_is_tightened_and_counted_clean(tmp_path):
    """C11's second sentence, which has no other test at this level: a
    trace with nothing left to redact but sitting at 0644 is readable by
    everyone on the box, so tightening it IS the change -- and it is
    still "already clean" in the count, because nothing was redacted."""
    key = _key(tmp_path)
    path = _plant(tmp_path, RUN, settled=True, key=key, mode=0o644)

    r = _cli(tmp_path, ["redact", RUN])

    assert r.returncode == 0, r.stdout + r.stderr
    assert f"run {RUN}: nothing to redact; mode 644 -> 600" in r.stdout
    assert f"redacted 0 of 1 traces (1 already clean, 0 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in r.stdout
    assert _mode(path) == 0o600


def test_a_failed_rewrite_is_refused_and_the_walk_continues(
        tmp_path, monkeypatch, capsys):
    """C7's promise on the one path no store can be made to take on
    demand: `apply` raised, so the original is whole, the trace is
    refused by sentence, the REST of the pass still happens and the call
    ends at exit 2.

    Driven in process, because the only lever is substitution and
    `run_cli` runs the CLI in a subprocess where a monkeypatch is not.
    It also pins R9's count: this plan carries its rows AND a refusal, and
    counting it as redacted would claim a rewrite that did not happen.
    """
    key = _key(tmp_path)
    first = _plant(tmp_path, "a-run")
    second = _plant(tmp_path, "b-run")
    before = second.read_bytes()
    monkeypatch.setenv("SENSORIUM_DIR", str(Path(tmp_path) / "sdir"))
    whole = redact_store.apply

    def failing(p):
        if p.path == second:
            raise OSError("boom")
        whole(p)

    monkeypatch.setattr(redact_store, "apply", failing)

    status = redact_cmd.run(_args(all=True))

    out = capsys.readouterr().out
    assert status == 2
    assert "run b-run: REFUSED: the rewrite failed: boom" in out
    assert "run a-run: env 1 redacted (API_KEY); values 6; " \
           "mode 644 -> 600" in out
    assert f"redacted 1 of 2 traces (0 already clean, 0 skipped, " \
           f"1 refused{SUMMARY_TAIL}" in out
    assert _meta(first)["redaction"]["by"] == "retrofit"
    assert second.read_bytes() == before
    assert _mode(second) == 0o644
    assert key.key_id


def test_a_judgement_that_raises_is_refused_and_named(
        tmp_path, monkeypatch, capsys):
    """R10. `plan` answers every condition it foresees with a sentence on
    the Plan, but sqlite reads pages lazily: a corrupt row can surface
    from inside the walk, after the file opened cleanly. C9 says the
    others continue, so an unforeseen condition is a refusal too and not
    a traceback that ends a pass over 273 traces at the second one.
    """
    _key(tmp_path)
    first = _plant(tmp_path, "a-run")
    second = _plant(tmp_path, "b-run")
    monkeypatch.setenv("SENSORIUM_DIR", str(Path(tmp_path) / "sdir"))
    whole = redact_store.plan

    def failing(path, key, knobs):
        if path == second:
            raise sqlite3.DatabaseError("database disk image is malformed")
        return whole(path, key, knobs)

    monkeypatch.setattr(redact_store, "plan", failing)

    status = redact_cmd.run(_args(all=True))

    out = capsys.readouterr().out
    assert status == 2
    assert ("run b-run: REFUSED: cannot judge: database disk image is "
            "malformed") in out
    assert "run a-run: env 1 redacted (API_KEY)" in out
    assert _mode(first) == 0o600
    assert f"redacted 1 of 2 traces (0 already clean, 0 skipped, " \
           f"1 refused{SUMMARY_TAIL}" in out


def test_a_non_string_env_value_is_refused_and_the_walk_continues(
        tmp_path, monkeypatch, capsys):
    """R19, the same promise as the test above for a trace nobody has to
    substitute anything to produce.

    `meta.env` is JSON, so a value in it can be a number, and
    `key.digest()` calls `.encode()` on what it is handed: an `AttributeError`
    out of the environment pass, which is not an `OSError`, a `sqlite3.Error`
    or a `ValueError`. Under the tuple guard that ONE trace ended an `--all`
    pass with a traceback, taking the 272 after it with it -- C9 says the
    others continue, and the only guard that can promise that over a
    judgement is the one that catches everything an exception can be.

    In process, because the assertion is about what the guard does with a
    raise and `run_cli`'s subprocess would report it as a traceback either
    way.
    """
    _key(tmp_path)
    first = _plant(tmp_path, "a-run")
    second = _plant(tmp_path, "b-run", env={"API_KEY": 12345})
    before = second.read_bytes()
    monkeypatch.setenv("SENSORIUM_DIR", str(Path(tmp_path) / "sdir"))

    status = redact_cmd.run(_args(all=True))

    out = capsys.readouterr().out
    assert status == 2
    refusal = next(ln for ln in out.splitlines()
                   if ln.startswith("run b-run: "))
    assert refusal.startswith("run b-run: REFUSED: cannot judge: "), refusal
    assert second.read_bytes() == before
    assert "run a-run: env 1 redacted (API_KEY)" in out
    assert _mode(first) == 0o600
    assert f"redacted 1 of 2 traces (0 already clean, 0 skipped, " \
           f"1 refused{SUMMARY_TAIL}" in out


def test_an_old_sidecar_left_behind_is_a_note_and_the_trace_still_counts(
        tmp_path, monkeypatch, capsys):
    """R19. Past the rename the rewrite has LANDED: the trace on disk is
    the redacted one, and a `-wal` that could not be unlinked is a second
    problem, not a failed rewrite.

    `REFUSED: the rewrite failed` there would tell a reader to go looking
    for plaintext in a database that no longer holds any, and say nothing
    about the log that still does. So `apply` raises `SidecarLeft`, the
    command prints the note on STDERR -- off the stdout `--dry-run` is
    diffed against (C10) -- and counts the trace as rewritten, which it is.
    """
    _key(tmp_path)
    path = _plant(tmp_path, RUN)
    monkeypatch.setenv("SENSORIUM_DIR", str(Path(tmp_path) / "sdir"))
    whole = redact_store._unlink_sidecars

    def failing(target):
        # The POST-REPLACE call alone: the tmp's own sidecars are removed
        # inside `_copy_and_rewrite`, and a failure there is a failed
        # rewrite like any other.
        if redact_store.TMP_SUFFIX in Path(target).name:
            return whole(target)
        raise OSError("Device or resource busy")

    monkeypatch.setattr(redact_store, "_unlink_sidecars", failing)

    status = redact_cmd.run(_args(run=RUN))

    captured = capsys.readouterr()
    assert status == 0
    assert (f"run {RUN}: env 1 redacted (API_KEY); values 6; "
            f"mode 644 -> 600") in captured.out
    assert f"redacted 1 of 1 traces (0 already clean, 0 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in captured.out
    assert captured.err.splitlines() == [
        f"run {RUN}: old sidecar not removed: Device or resource busy"]
    # the rewrite is on disk: the note is about the log beside it
    assert _meta(path)["env"]["API_KEY"] == redact.REDACTED
    assert _mode(path) == 0o600


def test_an_incomplete_trace_is_skipped(tmp_path):
    """C8. The Python recorder writes in place, so an incomplete trace is
    a file another process is holding open in WAL mode right now."""
    _key(tmp_path)
    path = _plant(tmp_path, RUN)
    _set_meta(path, incomplete=True)
    before = path.read_bytes()

    r = _cli(tmp_path, ["redact", "--all"])

    assert r.returncode == 1, r.stdout + r.stderr
    assert f"run {RUN}: in flight (incomplete), skipped" in r.stdout
    assert f"redacted 0 of 1 traces (0 already clean, 1 skipped, " \
           f"0 refused{SUMMARY_TAIL}" in r.stdout
    assert path.read_bytes() == before
    assert _mode(path) == 0o644


# -- the caller's knobs ---------------------------------------------------

def test_no_redact_in_the_callers_environment_is_ignored(tmp_path):
    """C4. Running the command IS the decision (§7), so the one knob that
    could quietly turn it into a no-op does not reach it: a retrofit that
    obeyed `SENSORIUM_NO_REDACT` would leave a shell's stale export
    standing between a user and the secrets they asked to be taken out."""
    _key(tmp_path)
    path = _plant(tmp_path, RUN)

    r = _cli(tmp_path, ["redact", RUN],
             env_extra={redact.OFF_VAR: "1"})

    assert r.returncode == 0, r.stdout + r.stderr
    assert ONE.search(r.stdout), r.stdout
    stamp = _meta(path)["redaction"]
    assert stamp["mode"] == "on"
    assert stamp["by"] == "retrofit"
    assert _meta(path)["env"]["API_KEY"] == redact.REDACTED


def test_the_callers_names_and_allow_knobs_are_read_and_stamped(tmp_path):
    """C4's other half. The two knobs that SHAPE the pass are the caller's
    own environment, read now -- the recording's knobs described a shell
    that has since ended, and the person asking is the one in front of the
    store."""
    _key(tmp_path)
    path = _plant(tmp_path, RUN, env={"MYCO_DSN": "postgres://u:pw@h/db",
                                      "API_KEY": ENV["API_KEY"],
                                      "HOME": "/tmp/u"})

    r = _cli(tmp_path, ["redact", RUN],
             env_extra={redact.NAMES_VAR: "myco_dsn",
                        redact.ALLOW_VAR: "api_key"})

    assert r.returncode == 0, r.stdout + r.stderr
    assert f"run {RUN}: env 1 redacted (MYCO_DSN); values 6; " \
           f"mode 644 -> 600" in r.stdout
    meta = _meta(path)
    assert meta["env"]["MYCO_DSN"] == redact.REDACTED
    assert meta["env"]["API_KEY"] == ENV["API_KEY"]
    assert meta["redaction"]["names"] == [redact.normalise("myco_dsn")]
    assert meta["redaction"]["allow"] == [redact.normalise("api_key")]


# -- the call itself ------------------------------------------------------

def test_a_bad_reference_exits_two_without_touching_a_trace(tmp_path):
    """A TRACE, which is what §7's "change nothing" is about -- not the
    whole store. The key is minted and the sweep has already run by the
    time `find_trace` refuses, both deliberately (R1's ruling is about
    the DRY run, and P3's sweep is not a trace); naming the test after
    "anything" promised more than it checked.
    """
    path = _plant(tmp_path, RUN)
    before = path.read_bytes()

    r = _cli(tmp_path, ["redact", "nope"])

    assert r.returncode == 2
    assert r.stdout == ""
    assert r.stderr.startswith("error: ")
    assert path.read_bytes() == before
    assert _mode(path) == 0o644
    assert (Path(tmp_path) / "sdir" / redact_key.KEY_FILE).exists()


def test_run_and_all_are_exclusive_and_one_is_required(tmp_path):
    _key(tmp_path)
    _plant(tmp_path, RUN)

    neither = _cli(tmp_path, ["redact"])
    both = _cli(tmp_path, ["redact", RUN, "--all"])

    assert (neither.returncode, both.returncode) == (2, 2)
    assert (neither.stdout, both.stdout) == ("", "")
    # Named, not merely rejected: "invalid choice" would mean the command
    # is not registered at all and this test is passing on absence.
    assert neither.stderr.rstrip().endswith(
        "error: give a run reference or --all")
    assert both.stderr.rstrip().endswith(
        "error: give a run reference or --all, not both")


def test_the_stale_key_tmp_is_swept_and_counted(tmp_path):
    """C13, P3. The sweep runs under `--dry-run` too: a dead process's
    32-byte leftover is not a trace, and keeping the sweep out of the dry
    run would make the two stdouts differ exactly when a reader is
    comparing them."""
    _key(tmp_path)
    _plant(tmp_path, RUN)
    litter = (Path(tmp_path) / "sdir"
              / f"{redact_key.KEY_FILE}.{_dead_pid()}.tmp")
    litter.write_bytes(b"x" * 32)

    dry = _cli(tmp_path, ["redact", RUN, "--dry-run"])

    assert "; swept 1 stale key tmp file(s)" in dry.stdout
    assert not litter.exists()

    litter.write_bytes(b"x" * 32)
    real = _cli(tmp_path, ["redact", RUN])

    assert "; swept 1 stale key tmp file(s)" in real.stdout
    assert not litter.exists()


def test_the_invocation_is_logged_argv_only(tmp_path):
    _key(tmp_path)
    _plant(tmp_path, RUN)

    _cli(tmp_path, ["redact", RUN])

    lines = (Path(tmp_path) / "sdir" / "invocations.jsonl").read_text()
    entry = json.loads(lines.splitlines()[-1])
    assert entry["argv"] == ["redact", RUN]
    assert entry["exit"] == 0
    assert set(entry) == {"utc", "argv", "exit", "error"}


# -- what the three readers say about a retrofitted trace -----------------

def test_info_on_the_result_says_by_retrofit_and_counts(tmp_path):
    """§4.3's LAST hand. A reader who is told a trace is redacted and not
    told by whom cannot tell a recording made under the rule from one
    brought under it afterwards -- and only the second kind has a window
    in which the plaintext was on disk."""
    key = _key(tmp_path)
    _plant(tmp_path, RUN)
    assert _cli(tmp_path, ["redact", RUN]).returncode == 0

    r = _cli(tmp_path, ["info", RUN])

    assert r.returncode == 0, r.stdout + r.stderr
    assert (f"redaction: rule v1, keyed (key {key.key_id}), by retrofit; "
            f"values redacted: 6") in r.stdout
    env_line = next(ln for ln in r.stdout.splitlines() if "env:" in ln)
    assert "1 redacted: API_KEY" in env_line


def test_grep_on_the_result_shows_the_marker_and_never_the_value(tmp_path):
    _key(tmp_path)
    _plant(tmp_path, RUN)
    assert _cli(tmp_path, ["redact", RUN]).returncode == 0

    r = _cli(tmp_path, ["grep", RUN, "get_api_key", "--kind", "RETURN"])

    assert r.returncode == 0, r.stdout + r.stderr
    assert "<redacted #" in r.stdout
    assert "tok_plain_value" not in r.stdout


def test_refocus_compares_the_retrofitted_env_by_name(tmp_path):
    """The retrofit's digests are what `refocus` compares afterwards, so a
    variable it took is still checkable by NAME on a re-run: equal holds
    the licence, rotated withholds it and names the variable.

    Both halves, because only the pair discriminates. A test that showed
    the granted run alone could not tell a digest that was compared and
    agreed from one that was never looked at -- and "never looked at"
    granting a full licence over a rotated secret is the failure §6.2
    exists to refuse.
    """
    live = "MY_API_KEY"
    secret = "sk-live-0123456789abcdef0123"
    run_id, _trace, rec = record_script(
        tmp_path, LOOP, env_extra={live: secret, redact.OFF_VAR: "1"})
    assert run_id, rec.stderr + rec.stdout
    sdir = Path(tmp_path) / "sdir"
    assert _cli(tmp_path, ["redact", run_id]).returncode == 0
    assert _meta(sdir / "traces" / f"{run_id}.db")["env"][live] == \
        redact.REDACTED

    same = _cli(tmp_path, ["refocus", run_id, "--focus", "prog:accumulate"],
                env_extra={live: secret, redact.OFF_VAR: "1"})
    rotated = _cli(tmp_path, ["refocus", run_id, "--focus", "prog:accumulate"],
                   env_extra={live: "rotated", redact.OFF_VAR: "1"})

    assert same.returncode == 0, same.stdout + same.stderr
    unchanged = next(ln for ln in same.stdout.splitlines()
                     if ln.startswith("env: "))
    assert unchanged.startswith("env: unchanged ("), unchanged
    assert live not in unchanged
    assert "licence: WITHHELD" not in same.stdout

    changed = next(ln for ln in rotated.stdout.splitlines()
                   if ln.startswith("env: "))
    assert "env: CHANGED since the original run -- 1 variable(s) differ: " \
           f"{live}" in changed
    assert "licence: WITHHELD" in rotated.stdout
