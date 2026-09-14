"""Rule v1's name rule, its knobs, and the store key -- pinned to the one
fixture all three implementations read.

`docs/trace-format/redaction-v1.json` is the contract between this module,
`sensorium-rt`'s `redact.rs` and `typescript/src/redact.mjs`: the same
`split` cases and the same `fires` cases, so a rule all three suites pass is
a rule all three recorders keep. The cases live in the fixture and not in
this file for exactly that reason -- a case added here would be a case the
other two never see.

`tests/fixtures/benign-env-names.txt` is the false-positive census
(design §8, plan A6): 177 real environment names -- this box's shell plus
the usual CI and toolchain names -- with the subset the rule is EXPECTED to
fire on written at its top by hand. `test_census_fires_on_exactly_the_
listed_subset` is the check of that hand: a rule that grows a false positive
fires on a name the header does not list, and a rule that loses a true
positive stops firing on one it does. Names only: the file carries no value,
and a test below asserts it never will.
"""
import errno
import hashlib
import hmac
import json
import os
import stat
from pathlib import Path

import pytest

from sensorium import redact
from sensorium.redact import KEY_VAR, REDACTED, Key, Knobs

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "docs" / "trace-format" / "redaction-v1.json"
CENSUS = Path(__file__).resolve().parent / "fixtures" / "benign-env-names.txt"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))

#: Every digest asserted below is computed under this key, in the test, from
#: `hmac` directly -- never from `Key.digest`, which is what is on trial.
MATERIAL = b"\x01" * 32

PLAIN = Knobs(False, frozenset(), frozenset())


def _key(tmp_path, material=MATERIAL):
    return Key(tmp_path / redact.KEY_FILE, material)


def _knobs(case):
    """The fixture's knobs as a USER types them, through `from_environ` --
    so the normalisation of `api_key` into `APIKEY` is on trial too."""
    knobs = case.get("knobs") or {}
    return Knobs.from_environ(
        {redact.NAMES_VAR: ",".join(knobs.get("names", [])),
         redact.ALLOW_VAR: ",".join(knobs.get("allow", []))})


def _ids(cases):
    return [f"{i}-{c['name'] or 'empty'}" for i, c in enumerate(cases)]


@pytest.mark.parametrize("case", CASES["split"], ids=_ids(CASES["split"]))
def test_split(case):
    assert redact.split(case["name"]) == case["segments"]


@pytest.mark.parametrize("case", CASES["names"], ids=_ids(CASES["names"]))
def test_fires(case):
    assert redact.fires(case["name"], _knobs(case)) is case["fires"]


def test_the_fixture_gives_every_segment_of_the_rule_a_firing_case():
    """A segment added to `SEGMENTS` without a case in the fixture is a
    segment the Rust and TypeScript suites never test."""
    covered = set()
    for case in CASES["names"]:
        if case["fires"] and not case.get("knobs"):
            covered |= set(redact.split(case["name"])) & redact.SEGMENTS
    assert covered == set(redact.SEGMENTS)


def test_the_fixture_gives_every_exact_name_a_firing_case():
    """`EXACT` is the short list of one-word names the segment rule cannot
    see into; a name added to it without a case is a name the Rust and
    TypeScript suites never test."""
    firing = {redact.normalise(case["name"]) for case in CASES["names"]
              if case["fires"] and not case.get("knobs")}
    assert set(redact.EXACT) <= firing


def test_the_fixtures_content_rows_hold_the_shape_the_content_rule_reads():
    """PR A left `content` empty; PR B fills it (`test_redact_content.py`
    is the suite that reads every row's VALUES -- this is only the SHAPE
    every row must hold, the same three keys the Rust and TypeScript
    suites read off the identical file)."""
    assert CASES["content"], "PR B must fill this list"
    for case in CASES["content"]:
        assert set(case) == {"pattern", "text", "after"}
        assert isinstance(case["pattern"], str) and case["pattern"]
        assert isinstance(case["text"], str)
        assert isinstance(case["after"], str)


def test_env_replaces_value_and_tables_digest(tmp_path):
    environ = {"API_KEY": "abc", "HOME": "/h", KEY_VAR: "00" * 32}
    stored, table = redact.env(environ, _key(tmp_path), PLAIN)
    assert stored == {"API_KEY": REDACTED, "HOME": "/h"}
    assert table == {"API_KEY":
                     hmac.new(MATERIAL, b"abc", "sha256").hexdigest()[:16]}
    # The key variable is DELETED, never redacted and never tabled: a digest
    # of the key under the key is a pointless row (§3).
    assert KEY_VAR not in stored and KEY_VAR not in table
    assert environ == {"API_KEY": "abc", "HOME": "/h", KEY_VAR: "00" * 32}


def test_the_table_is_sorted_whatever_the_environment_order(tmp_path):
    """R13: one environment, one table, whichever language wrote it."""
    stored, table = redact.env({"Z_TOKEN": "z", "A_KEY": "a", "HOME": "/h"},
                               _key(tmp_path), PLAIN)
    assert list(table) == ["A_KEY", "Z_TOKEN"]
    assert list(stored) == ["Z_TOKEN", "A_KEY", "HOME"]


def test_env_off_keeps_plaintext_but_drops_key_var(tmp_path):
    stored, table = redact.env({"API_KEY": "abc", KEY_VAR: "00" * 32},
                               _key(tmp_path),
                               Knobs(True, frozenset(), frozenset()))
    assert stored == {"API_KEY": "abc"}
    assert table == {}


def test_env_is_unkeyed_but_still_redacts_without_a_key(tmp_path):
    """The fallback loses comparability and never loses safety (§3)."""
    stored, table = redact.env({"API_KEY": "abc"}, _key(tmp_path, None), PLAIN)
    assert stored == {"API_KEY": REDACTED}
    assert table == {"API_KEY": None}


def test_env_honours_both_knobs(tmp_path):
    knobs = Knobs.from_environ({redact.NAMES_VAR: "myco_thing",
                                redact.ALLOW_VAR: "api_key"})
    stored, table = redact.env(
        {"API_KEY": "abc", "MYCO_THING": "m", "HOME": "/h"},
        _key(tmp_path), knobs)
    assert stored == {"API_KEY": "abc", "MYCO_THING": REDACTED, "HOME": "/h"}
    assert list(table) == ["MYCO_THING"]


def test_digest_hashes_surrogateescaped_bytes(tmp_path):
    """`os.environ` hands back undecodable bytes as lone surrogates; a bare
    `.encode()` raises on them and would take the whole recording down."""
    raw = b"caf\xe9"
    value = raw.decode("utf-8", "surrogateescape")
    assert _key(tmp_path).digest(value) == hmac.new(
        MATERIAL, raw, "sha256").hexdigest()[:16]


def test_digest_never_raises_on_a_lone_surrogate(tmp_path):
    """`surrogateescape` round-trips only U+DC80-U+DCFF, so a LONE surrogate
    raises there -- and this module never raises. U+FFFD is the identity
    Node's encoder gives the same string (R14)."""
    key = _key(tmp_path)
    assert key.digest("\ud800") == hmac.new(
        MATERIAL, "\ud800".encode("utf-8", "replace"),
        "sha256").hexdigest()[:16]
    stored, table = redact.env({"API_KEY": "\ud800", "HOME": "/h"},
                               key, PLAIN)
    assert stored == {"API_KEY": REDACTED, "HOME": "/h"}
    assert table == {"API_KEY": key.digest("\ud800")}


def test_key_load_or_create_is_0600_and_idempotent(tmp_path):
    root = tmp_path / "store"
    absent = Key.load(root)
    assert absent.keyed is False and absent.key_id is None
    assert absent.digest("x") is None and absent.problem
    key = Key.load_or_create(root)
    assert key.keyed and len(key.material) == 32
    assert key.problem is None
    assert stat.S_IMODE((root / redact.KEY_FILE).stat().st_mode) == 0o600
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert Key.load_or_create(root).material == key.material
    assert Key.load(root).material == key.material


def test_a_created_key_is_published_whole_and_leaves_no_tmp(tmp_path):
    """R15: the name appears with all 32 bytes behind it, and the private
    file it was written in is gone."""
    key = Key.load_or_create(tmp_path)
    path = tmp_path / redact.KEY_FILE
    assert len(key.material) == 32 and path.read_bytes() == key.material
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert sorted(p.name for p in tmp_path.iterdir()) == [redact.KEY_FILE]


def test_an_empty_key_file_is_unkeyed_and_never_written_over(tmp_path):
    """The 0-byte key an interrupted writer used to leave behind: it is the
    user's file, so it is reported and not replaced."""
    (tmp_path / redact.KEY_FILE).touch()
    key = Key.load_or_create(tmp_path)
    assert key.keyed is False and key.digest("x") is None
    assert key.problem == "redaction.key is 0 bytes, expected 32"
    assert (tmp_path / redact.KEY_FILE).read_bytes() == b""
    assert not list(tmp_path.glob("*.tmp"))


def test_a_loser_of_the_creation_race_reads_the_winners_key(tmp_path,
                                                            monkeypatch):
    """The window the old `O_EXCL` open left open, closed: another writer
    finishes its own key while this one is between write and link."""
    winner = b"\x07" * 32

    def racing_link(src, dst):
        Path(dst).write_bytes(winner)
        raise FileExistsError(errno.EEXIST, "File exists", str(dst))

    monkeypatch.setattr(os, "link", racing_link)
    key = Key.load_or_create(tmp_path)
    assert key.material == winner
    assert not list(tmp_path.glob("*.tmp"))


def test_a_filesystem_without_hard_links_falls_back_to_replace(tmp_path,
                                                               monkeypatch):
    def no_link(src, dst):
        raise OSError(errno.EPERM, "Operation not permitted")

    monkeypatch.setattr(os, "link", no_link)
    key = Key.load_or_create(tmp_path)
    path = tmp_path / redact.KEY_FILE
    assert key.keyed and len(key.material) == 32
    # Whoever wrote last, the material returned is the material on disk.
    assert path.read_bytes() == key.material
    assert not list(tmp_path.glob("*.tmp"))


def test_key_id_is_sha256_prefix(tmp_path):
    assert _key(tmp_path).key_id == hashlib.sha256(
        MATERIAL).hexdigest()[:8]


def test_a_key_file_of_the_wrong_size_is_unkeyed_and_says_why(tmp_path):
    (tmp_path / redact.KEY_FILE).write_bytes(b"short")
    key = Key.load(tmp_path)
    assert key.keyed is False and key.digest("x") is None
    assert key.problem == "redaction.key is 5 bytes, expected 32"


def test_from_hex_accepts_64_hex_and_refuses_everything_else():
    assert Key.from_hex("01" * 32).material == MATERIAL
    for bad in (None, "", "zz" * 32, "01" * 16, "01" * 33, " " + "01" * 32):
        key = Key.from_hex(bad)
        assert key.keyed is False and key.problem, bad


def test_mode_note_names_a_loose_key(tmp_path):
    key = Key.load_or_create(tmp_path)
    assert key.mode_note() is None
    (tmp_path / redact.KEY_FILE).chmod(0o644)
    assert Key.load(tmp_path).mode_note() == (
        "key mode 0644 -- expected 0600")
    assert Key.from_hex("01" * 32).mode_note() is None


def test_meta_off_and_on_shapes(tmp_path):
    key = _key(tmp_path)
    assert redact.meta(key, Knobs(True, frozenset(), frozenset()),
                       {}) == {"rule": "v1", "mode": "off"}
    knobs = Knobs.from_environ({redact.NAMES_VAR: "myco_dsn",
                                redact.ALLOW_VAR: "api_key, pass_count"})
    on = redact.meta(key, knobs, {"API_KEY": "ab" * 8})
    assert on == {"rule": "v1", "mode": "on", "keyed": True,
                  "key_id": key.key_id, "env": {"API_KEY": "ab" * 8},
                  "names": ["MYCODSN"], "allow": ["APIKEY", "PASSCOUNT"],
                  "by": "recorder"}
    assert list(on) == ["rule", "mode", "keyed", "key_id", "env", "names",
                        "allow", "by"]
    assert redact.meta(key, PLAIN, {}, by="converter")["by"] == "converter"
    unkeyed = redact.meta(_key(tmp_path, None), PLAIN, {"A": None})
    assert unkeyed["keyed"] is False and unkeyed["key_id"] is None


def _meta(table, key_id, keyed=True):
    return {"env": {name: REDACTED for name in table},
            "redaction": {"rule": "v1", "mode": "on", "keyed": keyed,
                          "key_id": key_id, "env": table}}


def test_uncomparable_three_rows(tmp_path):
    key = _key(tmp_path)
    mine = _meta({"API_KEY": key.digest("abc")}, key.key_id)
    assert redact.uncomparable(mine, mine, key) == ([], None)
    theirs = _meta({"API_KEY": "0" * 16, "TOKEN_B": "1" * 16}, "deadbeef")
    assert redact.uncomparable(mine, theirs, key) == (
        ["API_KEY", "TOKEN_B"], "different keys")
    unkeyed = _meta({"API_KEY": None}, None, keyed=False)
    assert redact.uncomparable(mine, unkeyed, key) == (["API_KEY"], "unkeyed")


def test_uncomparable_against_a_live_plaintext_side(tmp_path):
    """`now_meta=None` is the Python re-run: its side is plaintext, so the
    names are verifiable under the store key and nothing is unverifiable --
    unless the store's key is gone or is not the one that wrote them."""
    key = _key(tmp_path)
    mine = _meta({"API_KEY": key.digest("abc")}, key.key_id)
    assert redact.uncomparable(mine, None, key) == ([], None)
    assert redact.uncomparable(mine, None, _key(tmp_path, b"\x02" * 32)) == (
        ["API_KEY"], "different keys")
    assert redact.uncomparable(mine, None, _key(tmp_path, None)) == (
        ["API_KEY"], "unkeyed")


def test_compare_verifies_a_plaintext_side_under_the_store_key(tmp_path):
    key = _key(tmp_path)
    side = (key.digest("abc"), key.key_id, True)
    assert redact.compare(REDACTED, "abc", side, None, key) is True
    assert redact.compare(REDACTED, "xyz", side, None, key) is False
    assert redact.compare("abc", REDACTED, None, side, key) is True
    # The variable is gone from the plaintext side: a difference, and a
    # verified one -- never an unverifiability.
    assert redact.compare(REDACTED, None, side, None, key) is False
    assert redact.compare(REDACTED, "abc", side, None,
                          _key(tmp_path, b"\x02" * 32)) is None
    assert redact.compare(REDACTED, "abc", side, None,
                          _key(tmp_path, None)) is None
    assert redact.compare(REDACTED, REDACTED, side,
                          (None, key.key_id, True), key) is None


def _census():
    expected, names = set(), []
    for line in CENSUS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            body = line[1:].strip()
            if body and body != "fires:":
                expected.add(body)
        elif line.strip():
            names.append(line.strip())
    return expected, names


def test_census_fires_on_exactly_the_listed_subset():
    expected, names = _census()
    assert len(names) > 150 and len(set(names)) == len(names)
    assert expected <= set(names)
    assert {n for n in names if redact.fires(n, PLAIN)} == expected


def test_the_census_file_holds_names_and_no_values():
    """A harvest that pasted `NAME=value` lines would commit this box's
    environment into the repository."""
    assert "=" not in CENSUS.read_text(encoding="utf-8")
