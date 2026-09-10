"""Whether a spool's own `capabilities` declaration rides the BOOT record
into `meta`.

A separate file, not folded into `test_ts_ingest_meta.py`: that module is
at 777 of its own 800-line ceiling, with no room left for a third concern
(P12 of the throw-flow plan).
"""
import json

from tests.helpers import run_cli
from tests.ts_spools import FIXTURES, copy_tree, only_trace

#: `src.sensorium.ts.build.CAPABILITIES`, held here rather than imported so
#: this test notices a drift in either direction -- an import would let the
#: constant and its test drift together and prove nothing.
CONSTANT = {
    "line": False, "locals": False, "return_value": True, "tasks": True,
    "threads": False, "children": False, "stdin": False, "output": False,
    "object_identity": False, "refocus": False, "err_flow": False,
}

CASE = "async-chain"
SPOOL_FILE = "439886-0.jsonl"


def _boot_with_capabilities(spool, value) -> None:
    """Rewrite line 1 (BOOT) of `CASE`'s spool file to carry `capabilities:
    value`, leaving every other line, and the trailing newline, untouched."""
    path = spool / SPOOL_FILE
    lines = path.read_text().splitlines()
    boot = json.loads(lines[0])
    boot["capabilities"] = value
    lines[0] = json.dumps(boot)
    path.write_text("\n".join(lines) + "\n")


def test_the_recorders_own_declaration_rides_over_the_constant(tmp_path):
    """`sensorium-ts` 0.2.0's BOOT declares `err_flow: true`; the converter
    carries that into `meta.capabilities` over the constant's floor, and
    every OTHER key stays the constant's -- this BOOT declared only one."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    _boot_with_capabilities(spool, {"err_flow": True})
    sdir = tmp_path / "sdir"
    result = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                     sensorium_dir=sdir)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    caps = only_trace(sdir).meta["capabilities"]
    assert caps["err_flow"] is True
    other = {k: v for k, v in caps.items() if k != "err_flow"}
    assert other == {k: v for k, v in CONSTANT.items() if k != "err_flow"}


def test_a_spool_with_no_capabilities_map_declares_the_constant_alone(tmp_path):
    """A 0.1.x spool's BOOT carries no `capabilities` key at all, so the
    converted trace declares nothing beyond the constant -- `err_flow`
    included, still `false`."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    sdir = tmp_path / "sdir"
    result = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                     sensorium_dir=sdir)
    assert result.returncode == 0, f"{result.stdout}{result.stderr}"
    assert only_trace(sdir).meta["capabilities"] == CONSTANT


def test_a_capabilities_value_that_is_not_a_map_is_refused_by_name(tmp_path):
    """A BOOT whose `capabilities` is not an object is not a declaration
    this converter can merge over anything -- refused, naming the file, the
    same shape as every other malformed-record refusal in this module."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    _boot_with_capabilities(spool, 7)
    sdir = tmp_path / "sdir"
    result = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path,
                     sensorium_dir=sdir)
    assert result.returncode == 2, f"{result.stdout}{result.stderr}"
    refused = [ln for ln in result.stdout.splitlines()
              if ln.startswith("refused: ")]
    assert len(refused) == 1, result.stdout
    assert SPOOL_FILE in refused[0], refused[0]
    assert "BOOT carries a capabilities value that is not a map" in refused[0]
