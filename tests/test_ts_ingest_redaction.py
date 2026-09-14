"""What `sensorium ts ingest` says a converted trace was redacted under.

Two paths, and which one a spool takes is decided by whether the RECORDER
already ran the rule:

* **The recorder ran it** (`sensorium-ts 0.5.0` and later). The BOOT's own
  `redaction` object is what the trace says, carried through untouched but
  for the two keys only the converter can fill in -- `env`, the name ->
  digest table the runtime wrote beside it, and `by`, the last hand that
  applied the rule. The stored environment and its `envHash` are the
  recorder's and are not recomputed.
* **The recorder did not** (every spool under `tests/fixtures/ts-spools/`,
  written by 0.1.0). Those hold the launching environment in plaintext, and
  a converter that passed them through would write today's trace with
  yesterday's secrets in it. The rule runs HERE instead, `by: "converter"`,
  under the STORE's key and under NO knobs -- the knobs are properties of a
  recording this converter did not make.

The fixtures and the machinery are `tests/ts_spools.py`, which carries the
provenance of every case; what the rest of a converted trace holds is
`tests/test_ts_ingest_meta.py`. The one case here is `async-chain`, copied
and its BOOT edited, because the question is about the BOOT and about
nothing else in the spool.
"""
import hashlib
import json
import os
import stat
from pathlib import Path

from sensorium import redact
from sensorium.store.reader import Trace
from tests.helpers import run_cli
from tests.ts_spools import FIXTURES, copy_tree

CASE = "async-chain"
SPOOL_FILE = "439886-0.jsonl"

#: A name whose segments are `MY`, `API`, `KEY` -- the rule fires -- beside
#: one whose single segment is in nothing, so every test states both halves
#: of the judgement: what was redacted AND what was left alone.
SECRET, PLAIN = "MY_API_KEY", "PLAIN"
VALUE = "abc"


def _ts_env_hash(env: dict) -> str:
    """The TypeScript recorder's recipe, spelled out here rather than
    imported: a test that recomputed the hash with the module under test
    would pass whatever that module did."""
    body = "\n".join(f"{k}={v}" for k, v in sorted(env.items()))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _ingest(tmp_path, edit=None) -> tuple[dict, redact.Key, Path]:
    """`async-chain`, its BOOT optionally edited, ingested under a fresh
    store whose key exists. Returns (meta, the store's key, the trace)."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    if edit is not None:
        path = spool / SPOOL_FILE
        lines = path.read_text(encoding="utf-8").split("\n")
        boot = json.loads(lines[0])
        edit(boot)
        lines[0] = json.dumps(boot)
        path.write_text("\n".join(lines), encoding="utf-8")
    sdir = tmp_path / "sdir"
    key = redact.Key.load_or_create(sdir)
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    traces = sorted((sdir / "traces").glob("*.db"))
    assert len(traces) == 1, [p.name for p in traces]
    return Trace.open(traces[0]).meta, key, traces[0]


def _plant(boot: dict) -> None:
    boot["env"] = {**boot["env"], SECRET: VALUE, PLAIN: "x"}


# -- a BOOT written before the rule existed ---------------------------------

def test_an_older_boot_is_redacted_by_the_converter(tmp_path):
    """The fixture's own environment (`{"PATH": "/usr/bin"}`) fires on
    nothing, so what this pins is the STATEMENT: the rule ran here, under
    the store's key and under no knobs, and the trace says which hand
    applied it."""
    meta, key, _trace = _ingest(tmp_path)
    assert meta["redaction"] == {
        "rule": "v1", "mode": "on", "keyed": True, "key_id": key.key_id,
        "env": {}, "names": [], "allow": [], "by": "converter"}
    assert meta["env"] == {"PATH": "/usr/bin"}


def test_a_secret_name_in_an_older_boot_is_stored_redacted_with_a_digest(
        tmp_path):
    meta, key, _trace = _ingest(tmp_path, _plant)
    assert meta["env"][SECRET] == redact.REDACTED
    assert meta["env"][PLAIN] == "x"
    assert meta["redaction"]["env"] == {SECRET: key.digest(VALUE)}
    assert meta["redaction"]["by"] == "converter"


def test_the_env_hash_is_recomputed_over_what_the_trace_now_holds(tmp_path):
    """The recorder hashed the plaintext it wrote; the trace no longer holds
    it. A hash left as recorded would report a world change whose evidence
    the trace does not carry -- and would differ from the hash the same
    environment gets on the next run, when the recorder redacts it itself.
    """
    meta, _key, _trace = _ingest(tmp_path, _plant)
    boot = json.loads((FIXTURES / CASE / SPOOL_FILE).read_text(
        encoding="utf-8").split("\n")[0])
    assert meta["env_hash"] == _ts_env_hash(meta["env"])
    assert meta["env_hash"] != boot["envHash"]


def test_the_key_variable_never_reaches_the_trace(tmp_path):
    """A driver hands the recorder a key in the environment. An older
    recorder stored it like any other variable, so the converter is the
    hand that has to take it out."""
    def plant(boot):
        boot["env"] = {**boot["env"], redact.KEY_VAR: "ab" * 32}

    meta, _key, _trace = _ingest(tmp_path, plant)
    assert redact.KEY_VAR not in meta["env"]
    assert redact.KEY_VAR not in meta["redaction"]["env"]


def test_a_store_with_no_key_still_redacts_and_says_the_digest_is_absent(
        tmp_path):
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    path = spool / SPOOL_FILE
    lines = path.read_text(encoding="utf-8").split("\n")
    boot = json.loads(lines[0])
    _plant(boot)
    lines[0] = json.dumps(boot)
    path.write_text("\n".join(lines), encoding="utf-8")

    sdir = tmp_path / "sdir"           # no key file, and ingest never mints one
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (sdir / redact.KEY_FILE).exists()
    meta = Trace.open(sorted((sdir / "traces").glob("*.db"))[0]).meta
    assert meta["env"][SECRET] == redact.REDACTED
    assert meta["redaction"]["keyed"] is False
    assert meta["redaction"]["env"] == {SECRET: None}


# -- a BOOT the recorder already redacted -----------------------------------

RECORDED = {"rule": "v1", "mode": "on", "keyed": True, "key_id": "0123abcd",
            "names": ["MYCOTHING"], "allow": []}


def _carried(boot: dict) -> None:
    boot["env"] = {**boot["env"], SECRET: redact.REDACTED}
    boot["envRedaction"] = {SECRET: "1234567890abcdef"}
    boot["redaction"] = dict(RECORDED)


def test_the_recorders_own_redaction_is_carried_through(tmp_path):
    """The recorder's word, plus the two keys the converter owns. The
    environment is NOT re-run through the rule: §5.4 -- a converter meeting
    a `mode: on` header trusts it, and re-running the rule over an already
    redacted environment would digest the marker."""
    meta, _key, _trace = _ingest(tmp_path, _carried)
    assert meta["redaction"] == {
        **RECORDED, "env": {SECRET: "1234567890abcdef"}, "by": "recorder"}
    assert meta["env"][SECRET] == redact.REDACTED


def test_a_carried_header_keeps_the_hash_the_recorder_took(tmp_path):
    boot = json.loads((FIXTURES / CASE / SPOOL_FILE).read_text(
        encoding="utf-8").split("\n")[0])
    meta, _key, _trace = _ingest(tmp_path, _carried)
    # The runtime hashed what it wrote, and a second hash taken here could
    # only differ by being wrong.
    assert meta["env_hash"] == boot["envHash"]


def test_mode_off_passes_through_as_the_two_keys_it_was_written_as(tmp_path):
    """A header that named a key or a knob list while claiming to have
    applied nothing would invite a reader to believe the plaintext beside it
    had been considered."""
    def off(boot):
        boot["env"] = {**boot["env"], SECRET: VALUE}
        boot["envRedaction"] = {}
        boot["redaction"] = {"rule": "v1", "mode": "off"}

    meta, _key, _trace = _ingest(tmp_path, off)
    assert meta["redaction"] == {"rule": "v1", "mode": "off"}
    assert meta["env"][SECRET] == VALUE


# -- the file the converter creates -----------------------------------------

def test_the_ingested_trace_is_the_users_own_to_read(tmp_path):
    _meta, _key, trace = _ingest(tmp_path)
    assert stat.S_IMODE(os.stat(trace).st_mode) == 0o600
