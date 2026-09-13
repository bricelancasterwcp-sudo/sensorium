"""The two invocation facts a re-run needs, and the capability that says a
re-run may be asked for at all.

A separate file, not folded into `test_ts_ingest_meta.py`: that module is at
785 of its own 800-line ceiling (`wc -l tests/test_ts_ingest_meta.py`,
2026-09-13), which is no room for a third concern -- the same reason
`test_ts_ingest_caps.py` was split out the day before, and its docstring
carries the warning about trusting the digits.

What is checked here is what the CONVERTER lifts out of `invocation.json`:
`harness_cwd`, which every record has always carried as `cwd`, and
`refocus_of`, which the driver writes only when `--refocus-of` was given.
The flag itself is `tests/test_ts_driver_refocus.py`.
"""
import json

from tests.helpers import run_cli
from tests.ts_spools import FIXTURES, copy_tree, only_trace

CASE = "async-chain"
ORIGINAL = "20260101-000000-orig01"

#: Where the fixture's record says the person was standing. The recorded
#: spool has `cwd == root == /w/probes`, and those are the one pair
#: `harness_cwd` must not be read from: a converter that took it from `root`
#: would pass every assertion below unchanged. So the copy is moved one
#: directory up -- `npx vitest run probes/src/...` typed from the workspace
#: -- and the two facts are then two different strings.
TYPED_IN = "/w"
ROOT = "/w/probes"


def _ingest(tmp_path, **record_extra):
    """Copy the case's spool somewhere writable, rewrite its
    `invocation.json`, ingest it with the REAL CLI, and hand back the one
    trace's meta. The copy matters for the same reason it does in
    `ts_spools.ingest_case`: `ingest` writes into the directory it read."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    path = spool / "invocation.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["cwd"] = TYPED_IN
    record.update(record_extra)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    return sdir, only_trace(sdir).meta


def test_the_link_and_the_typed_in_directory_ride_every_trace(tmp_path):
    """Design section 2.2. Both keys come off the invocation record, so
    every container of one `sensorium ts run` carries the same two."""
    _sdir, meta = _ingest(tmp_path, refocus_of=ORIGINAL)
    assert meta["refocus_of"] == ORIGINAL
    assert meta["harness_cwd"] == TYPED_IN
    # Beside it, and not instead of it: the plan's root is what every `rel`
    # in the trace is relative to, and the harness command's own relative
    # arguments are relative to neither the root nor the container's `cwd`.
    assert meta["root"] == ROOT
    assert meta["cwd"] == ROOT


def test_a_run_nobody_linked_carries_no_link_at_all(tmp_path):
    """R10's other half. An absent key is a run that was typed by a person;
    `refocus_of: null` would be a re-run of nothing, and `info` and `runs`
    both branch on the key's presence."""
    _sdir, meta = _ingest(tmp_path)
    assert "refocus_of" not in meta
    # The directory is not conditional on the link: it is what a re-run of
    # ANY recording would have to be launched from.
    assert meta["harness_cwd"] == TYPED_IN


def test_this_converter_declares_every_trace_refocusable(tmp_path):
    """R10. True for every trace this converter writes -- whether one
    PARTICULAR trace can be re-run is a refusal the reader raises, and a
    capability that said otherwise would refuse the command before any of
    those refusals got to name their own reason."""
    _sdir, meta = _ingest(tmp_path)
    assert meta["capabilities"]["refocus"] is True


def test_info_prints_the_directory_the_command_was_typed_in(tmp_path):
    """The line goes under the harness line, because it says where that
    command's relative arguments were relative to."""
    sdir, meta = _ingest(tmp_path)
    out = run_cli(["info", meta["run_id"]], cwd=tmp_path,
                  sensorium_dir=sdir).stdout
    lines = out.splitlines()
    i = next((n for n, line in enumerate(lines)
              if line.startswith("harness: ")), None)
    assert i is not None, out
    assert lines[i + 1] == f"harness cwd: {TYPED_IN}", out
