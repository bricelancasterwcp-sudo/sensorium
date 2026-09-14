"""What `sensorium ts ingest` says a converted trace was redacted under.

Two paths, and which one a spool takes is decided by whether the RECORDER
already ran the rule:

* **The recorder ran it** (`sensorium-ts 0.5.0` and later for the
  ENVIRONMENT; 0.6.0 and later for the CAPTURES as well -- the two halves
  shipped one version apart, and `by` names whichever hand was last). The
  BOOT's own `redaction` object is what the trace says, carried through
  untouched but for the keys only the converter can fill in -- `env`, the
  name -> digest table the runtime wrote beside it, `by`, and `values`, the
  count of what the finished trace withholds. The stored environment and its
  `envHash` are the recorder's and are not recomputed.
* **The recorder did not** (every spool under `tests/fixtures/ts-spools/`,
  written by 0.1.0). Those hold the launching environment in plaintext, and
  a converter that passed them through would write today's trace with
  yesterday's secrets in it. The rule runs HERE instead, `by: "converter"`,
  under the STORE's key and under NO knobs -- the knobs are properties of a
  recording this converter did not make.

The fixtures and the machinery are `tests/ts_spools.py`, which carries the
provenance of every case; what the rest of a converted trace holds is
`tests/test_ts_ingest_meta.py`. The one case here is `async-chain`, copied
and its BOOT edited -- and, for the capture half below, with a capture
planted on its first CALL, because no recorded fixture holds a value under a
name this rule fires on (`tests/fixtures/corpus-firing-names.txt` is the
census that says so).
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
        "env": {}, "names": [], "allow": [], "by": "converter", "values": 0}
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
    # 0.6.0, because `by` is the LAST hand to apply the rule (B2): a
    # recorder that redacted its environment and left its captures in
    # plaintext is one this converter still has work to do for, and the
    # case for that one is `test_a_capture_an_older_recorder_left_in_
    # plaintext_is_taken_here` below.
    boot["version"] = "0.6.0"
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
        **RECORDED, "env": {SECRET: "1234567890abcdef"}, "by": "recorder",
        "values": 0}
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


# -- the captures the recording carries -------------------------------------
#
# The same two-path question, one layer down. Whether the RECORDER ran the
# value half of rule v1 is decided by two facts together (B2): its BOOT says
# `mode: "on"`, and it is `sensorium-ts` 0.6.0 or later -- the version the
# runtime began taking captures at. A 0.5.0 BOOT says `mode: "on"` about its
# ENVIRONMENT and nothing else, so the converter is the hand that has to run
# the rule over its captures, and `by` then says `converter` because `by` is
# the LAST hand to apply it.
#
# The CONTENT rule runs on every path (B9): it is idempotent -- a marker holds
# none of the shapes it looks for -- so a converter meeting a text a recorder
# already scanned changes nothing, and one meeting a text no recorder scanned
# takes the span out.

#: A BOOT header the recorder wrote about its own recording.
ON = {"rule": "v1", "mode": "on", "keyed": True, "key_id": "0123abcd",
      "names": [], "allow": []}

#: A plaintext capture, as a recorder that did not take captures wrote one.
TYPED = {"k": "dbg", "v": "'abc'", "trunc": False}

#: A secret shaped like §2.2's `sk` row, inside an inspected text.
SK = "sk-test-" + "A" * 24


def _spool_ingest(tmp_path, edit) -> tuple[dict, redact.Key, Trace]:
    """`async-chain` with every record passed through `edit`, ingested under
    a fresh store whose key exists. Returns (meta, the store's key, trace)."""
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / CASE, spool)
    path = spool / SPOOL_FILE
    recs = [json.loads(line) for line
            in path.read_text(encoding="utf-8").splitlines() if line]
    edit(recs)
    path.write_text("".join(json.dumps(r) + "\n" for r in recs),
                    encoding="utf-8")
    sdir = tmp_path / "sdir"
    key = redact.Key.load_or_create(sdir)
    r = run_cli(["ts", "ingest", str(spool)], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    traces = sorted((sdir / "traces").glob("*.db"))
    assert len(traces) == 1, [p.name for p in traces]
    trace = Trace.open(traces[0])
    return trace.meta, key, trace


def _recorded_by(version: str, redaction: dict | None = None):
    """An edit that makes the spool's BOOT the one `version` would write."""
    def edit(recs: list[dict]) -> None:
        recs[0]["version"] = version
        if redaction is not None:
            recs[0]["redaction"] = dict(redaction)
            recs[0]["envRedaction"] = {}
    return edit


def _args(recs: list[dict], args: dict) -> None:
    """Plant an argument map on the spool's first CALL. A CALL with an `a` is
    what a focused site writes, and the converter copies it into the event's
    `args` -- which is where the value half of the rule has to reach."""
    for rec in recs:
        if rec["e"] == "CALL":
            rec["a"] = args
            return
    raise AssertionError("the fixture has no CALL to plant on")


def _planted(trace: Trace) -> dict:
    """The planted argument map, as the trace ended up holding it."""
    found = [e.payload["args"] for e in trace.events(kind="CALL")
             if (e.payload or {}).get("args")]
    assert len(found) == 1, found
    return found[0]


def test_a_capture_an_older_recorder_left_in_plaintext_is_taken_here(tmp_path):
    """(a) A 0.5.0 spool. Its BOOT says the rule ran, and it did -- over the
    ENVIRONMENT. The captures beside it are as the program had them, so the
    converter runs the name rule over them, under the STORE's key, and says
    it was the last hand to touch the recording."""
    def edit(recs):
        _recorded_by("0.5.0", ON)(recs)
        _args(recs, {"token": dict(TYPED)})

    meta, key, trace = _spool_ingest(tmp_path, edit)
    assert _planted(trace) == {"token": {
        "k": "dbg", "v": redact.REDACTED, "trunc": False,
        "redacted": {"by": "name", "digest": key.digest("'abc'")}}}
    assert meta["redaction"]["by"] == "converter"
    assert meta["redaction"]["values"] == 1


def test_a_capture_the_recorder_already_took_is_carried_through(tmp_path):
    """(b) A 0.6.0 spool. The recorder took the value under its OWN key, and
    the converter does not touch it: re-running the name rule would digest
    the marker, and re-running the content rule over a `<redacted>` finds
    nothing. It is still counted -- `values` counts what the TRACE withholds,
    whichever hand withheld it (B3)."""
    already = {"k": "dbg", "v": redact.REDACTED, "trunc": False,
               "redacted": {"by": "name", "digest": "1234567890abcdef"}}

    def edit(recs):
        _recorded_by("0.6.0", ON)(recs)
        _args(recs, {"token": dict(already)})

    meta, _key, trace = _spool_ingest(tmp_path, edit)
    assert _planted(trace) == {"token": already}
    assert meta["redaction"]["by"] == "recorder"
    assert meta["redaction"]["values"] == 1


def test_a_plaintext_capture_on_a_0_6_0_spool_is_the_recorders_word(tmp_path):
    """The other half of (b), and the one the version gate exists for: a
    0.6.0 recorder is TRUSTED about its names. A capture it left in plaintext
    under a firing name is a name its knobs allowed, not one it missed, and
    a converter that took it anyway would overrule a recording's own knobs
    with today's environment."""
    def edit(recs):
        _recorded_by("0.6.0", ON)(recs)
        _args(recs, {"token": dict(TYPED)})

    meta, _key, trace = _spool_ingest(tmp_path, edit)
    assert _planted(trace) == {"token": TYPED}
    assert meta["redaction"]["values"] == 0


def test_a_secret_in_a_text_is_scanned_on_every_path(tmp_path):
    """(c) B9: the CONTENT rule is idempotent, so it runs whoever recorded
    the spool. A text a 0.6.0 recorder wrote without scanning -- an older
    pattern list, a name nothing fired on -- still loses the span here, and
    the count says one value is withheld."""
    def edit(recs):
        _recorded_by("0.6.0", ON)(recs)
        _args(recs, {"note": {"k": "dbg", "v": f"'key={SK}'", "trunc": False}})

    meta, _key, trace = _spool_ingest(tmp_path, edit)
    assert _planted(trace) == {"note": {
        "k": "dbg", "v": f"'key={redact.REDACTED}'", "trunc": False,
        "redacted": {"by": "content", "digest": None}}}
    assert meta["redaction"]["values"] == 1


def test_a_recording_made_with_the_rule_off_is_converted_as_it_was(tmp_path):
    """(d) B26: `mode: "off"` is a decision the person recording made, and
    the converter neither overrides it nor reports a count it did not take.
    No `values` key at all -- a zero there would say the rule ran and found
    nothing."""
    def edit(recs):
        _recorded_by("0.6.0", {"rule": "v1", "mode": "off"})(recs)
        _args(recs, {"token": {"k": "dbg", "v": f"'{SK}'", "trunc": False}})

    meta, _key, trace = _spool_ingest(tmp_path, edit)
    assert _planted(trace) == {"token": {"k": "dbg", "v": f"'{SK}'",
                                         "trunc": False}}
    assert meta["redaction"] == {"rule": "v1", "mode": "off"}
    assert "values" not in meta["redaction"]


def test_values_counts_the_captures_and_not_the_records(tmp_path):
    """`values` is a COUNT, not a flag: two withheld captures on one record
    are two, and a capture the rule left alone is none of them."""
    def edit(recs):
        _recorded_by("0.5.0", ON)(recs)
        _args(recs, {"token": dict(TYPED), "apiKey": dict(TYPED),
                     "rows": {"k": "dbg", "v": "[ 1, 2 ]", "trunc": False}})

    meta, _key, trace = _spool_ingest(tmp_path, edit)
    planted = _planted(trace)
    assert [n for n, c in planted.items() if "redacted" in c] == ["token",
                                                                 "apiKey"]
    assert planted["rows"] == {"k": "dbg", "v": "[ 1, 2 ]", "trunc": False}
    assert meta["redaction"]["values"] == 2
