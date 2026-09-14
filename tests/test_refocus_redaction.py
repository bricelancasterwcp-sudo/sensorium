"""What the licence's environment check may claim about a value it cannot see.

Rule v1 stores a secret-named variable as `<redacted>` and keeps an HMAC of
the plaintext under the store's key, so `refocus` can still answer the only
question the licence asks of a variable -- did it change -- without holding
what it changed to. Three outcomes, and the design's §6.2 table decides
which: the digests agree (hold), they differ (withhold, exactly as a changed
variable does today), or they cannot be compared at all (say so, and do NOT
withhold).

THE THIRD IS THE ONE WITH TEETH. A check that could not run is not a finding
against the pair -- the rule `refocus_licence` already applies to a recorder
that declares it captures no output -- so an uncomparable variable is named
on the env line, named in the fact, stamped in
`refocus_licence_unverifiable`, and given no vote. The failure this prevents
is the one in the other direction: a pair whose secret really changed
reading as "unverifiable" and earning a full licence. That is why the
plaintext side is verified THROUGH the store's key (case 3) rather than
excused, and why a missing value on the plaintext side is a decided
difference and not a hole.

The pairs are built from `meta` alone. What is under test is the comparison
table and the two sentences it writes, and a recorded pair would carry
whatever the launching shell held -- the same reason
`tests/test_record_redaction.py` gives for never asserting on the SIZE of a
real `redaction.env`. `tests/test_refocus_licence.py` covers the live
plaintext path end to end, through a real re-run.
"""
import pytest

from sensorium import paths, redact
from sensorium.query.refocus_env import RedactionPair
from sensorium.query.refocus_world import (UNVERIFIABLE_ENV, _env_diff,
                                           _env_state, relicense,
                                           unverifiable_checks)
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import finalize_synthetic

#: One redacted name and one that was never redacted, so every case states
#: both halves: what the table decided AND that everything else still takes
#: the plain-equality path it always took.
NAME, PLAIN = "MY_API_KEY", "PATH"
SECRET = "s3cret"
OTHER = "0" * 16
KEY_ID = "0a1b2c3d"


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A trace store this process's `paths.trace_root()` resolves to.

    `_env_state` and `unverifiable_checks` read the STORE's key -- it is
    what verifies a digest against a plaintext side -- so a test that did
    not pin the store would be comparing against whatever key the box's
    real `~/.sensorium` happens to hold.
    """
    sdir = tmp_path / "sdir"
    sdir.mkdir(parents=True)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    return sdir


def _meta(table, key_id=KEY_ID, *, keyed=True, env=None) -> dict:
    """One side's meta: the stored environment and the rule that made it."""
    return {"env": {NAME: redact.REDACTED, PLAIN: "/usr/bin"}
                   if env is None else env,
            "redaction": {"rule": "v1", "mode": "on", "keyed": keyed,
                          "key_id": key_id, "env": table,
                          "names": [], "allow": [], "by": "recorder"}}


def _diff(was_meta, now_env, now_meta=None):
    """`_env_diff` over a pair, with the pair `_env_state` would build.

    `now_meta=None` is the live plaintext side, and the signature says so
    the same way `_env_state`'s does.
    """
    return _env_diff(was_meta["env"], now_env,
                     redaction=RedactionPair.of(
                         was_meta, now_meta,
                         redact.Key.load(paths.trace_root())))


def _trace(store, run_id, meta) -> Trace:
    """A finalized trace carrying this meta, opened."""
    path = store / "traces" / f"{run_id}.db"
    w = TraceWriter(path, batch=1)
    for k, v in meta.items():
        w.set_meta(k, v)
    finalize_synthetic(w, run_id=run_id)
    w.close()
    return Trace.open(path)


# -- case 1: two digests that agree ----------------------------------------
def test_two_sides_that_redacted_the_same_value_compare_equal(store):
    """The ordinary re-run. Both sides took the digest under the same key,
    the digests agree, and the variable is on NO list -- not changed, not
    relocated, not uncomparable. The line reads exactly as it did before
    the rule existed."""
    was, now = _meta({NAME: OTHER}), _meta({NAME: OTHER})
    changed, relocated, stripped, session, harness, uncomparable = _diff(
        was, now["env"], now)
    assert changed == [] and uncomparable == []
    assert relocated == [] and stripped == [] and session == []
    assert harness == []

    line, caveat, fact = _env_state(was, now["env"], now_meta=now)
    assert line.startswith("env: unchanged (2 variables compared;")
    assert caveat is None
    assert "not comparable" not in line and "not comparable" not in fact


# -- case 2: two digests that differ ---------------------------------------
def test_two_digests_that_differ_withhold_exactly_as_a_value_would(store):
    """A secret that changed between the runs is a changed variable. It
    reaches `changed` DIRECTLY -- the relocation, session and harness
    partitions are never consulted, because a digest cannot be rerooted and
    a name's membership of a set says nothing about a value nobody can
    read."""
    was, now = _meta({NAME: OTHER}), _meta({NAME: "f" * 16})
    changed, _rel, _str, _ses, _har, uncomparable = _diff(was, now["env"], now)
    assert changed == [NAME] and uncomparable == []

    line, caveat, fact = _env_state(was, now["env"], now_meta=now)
    assert line.startswith("env: CHANGED since the original run -- "
                           f"1 variable(s) differ: {NAME}")
    assert caveat is not None and "different input" in caveat


# -- case 3: a digest against the live plaintext ---------------------------
def test_a_live_plaintext_value_is_verified_through_the_store_key(store):
    """The Python re-run's own shape: the original is redacted and the side
    it is compared against is this process's live environment, plaintext.
    The store's key is what decides it -- and it decides, rather than
    excusing itself, which is the whole reason the key is kept."""
    key = redact.Key.load_or_create(store)
    was = _meta({NAME: key.digest(SECRET)}, key.key_id)
    live = {NAME: SECRET, PLAIN: "/usr/bin"}

    changed, _rel, _str, _ses, _har, uncomparable = _diff(was, live)
    assert changed == [] and uncomparable == []
    line, caveat, _fact = _env_state(was, live)
    assert line.startswith("env: unchanged (") and caveat is None


def test_a_live_plaintext_value_that_changed_is_a_difference(store):
    """The discriminating control for the case above. A plaintext side that
    hashes to something else is a variable that changed, and a rule that
    called the pair unverifiable here would grant a licence over exactly the
    fact the licence exists to refuse."""
    key = redact.Key.load_or_create(store)
    was = _meta({NAME: key.digest(SECRET)}, key.key_id)
    live = {NAME: "rotated", PLAIN: "/usr/bin"}

    changed, _rel, _str, _ses, _har, uncomparable = _diff(was, live)
    assert changed == [NAME] and uncomparable == []
    line, caveat, _fact = _env_state(was, live)
    assert f"1 variable(s) differ: {NAME}" in line and caveat is not None


# -- case 4: two keys, which is no comparison at all ------------------------
def test_digests_under_two_keys_are_named_and_do_not_withhold(store):
    """Two stores, two keys, two digests of the same plaintext that will
    never be equal. The names ride the line and the fact -- a reader is owed
    the name of every variable this check stopped checking -- and the caveat
    stays None, because a check that could not run is not a finding against
    the pair."""
    was, now = _meta({NAME: OTHER}, "aaaaaaaa"), _meta({NAME: "f" * 16},
                                                       "bbbbbbbb")
    changed, _rel, _str, _ses, _har, uncomparable = _diff(
        was, now["env"], now)
    assert uncomparable == [NAME] and changed == []

    line, caveat, fact = _env_state(was, now["env"], now_meta=now)
    clause = ("1 redacted variable(s) not comparable (different keys): "
              f"{NAME}")
    assert clause in line and clause in fact
    assert caveat is None


# -- case 5: no key at all --------------------------------------------------
def test_an_unkeyed_side_says_unkeyed_and_not_different_keys(store):
    """The two reasons are two different repairs: a reader told `different
    keys` goes looking for the other store's key, and one told `unkeyed`
    knows there is nothing to look for. One word for the whole list, in the
    same clause."""
    was = _meta({NAME: None}, None, keyed=False)
    now = _meta({NAME: OTHER})
    _ch, _rel, _str, _ses, _har, uncomparable = _diff(
        was, now["env"], now)
    assert uncomparable == [NAME]

    line, caveat, fact = _env_state(was, now["env"], now_meta=now)
    clause = f"1 redacted variable(s) not comparable (unkeyed): {NAME}"
    assert clause in line and clause in fact
    assert caveat is None


# -- the fence: everything else keeps the path it always had ---------------
def test_a_variable_no_side_redacted_takes_the_plain_path(store):
    """`compare` is asked about a name at least one side redacted and about
    no other. A plain variable that differs is a changed variable, by the
    same equality it always was, whatever the tables say."""
    was = _meta({NAME: OTHER})
    now = _meta({NAME: OTHER}, env={NAME: redact.REDACTED, PLAIN: "/bin"})
    changed, _rel, _str, _ses, _har, uncomparable = _diff(
        was, now["env"], now)
    assert changed == [PLAIN] and uncomparable == []


def test_a_pair_with_no_tables_at_all_builds_no_redaction_pair(store):
    """Two traces from before the rule: `RedactionPair.of` is None, the
    sixth list is empty, and every string is the one it was."""
    assert RedactionPair.of({"env": {}}, {"env": {}},
                            redact.Key.load(store)) is None
    changed, _rel, _str, _ses, _har, uncomparable = _env_diff(
        {"A": "1"}, {"A": "2"})
    assert changed == ["A"] and uncomparable == []


# -- case 6: the stamped marker --------------------------------------------
def test_the_unverifiable_marker_fires_on_two_keys_and_not_on_agreement(
        store):
    """The marker is computed from the two METAS -- it reads `meta["env"]`
    too, because a plaintext side has no table of its own -- and it is the
    fixed text `relicense` filters by. Named in `UNVERIFIABLE`, so a caveat
    carrying it can be taken back out of the withholding decision."""
    orig = _trace(store, "20260101-000000-aaaaaa",
                  _meta({NAME: OTHER}, "aaaaaaaa"))
    other = _trace(store, "20260101-000001-bbbbbb",
                   _meta({NAME: "f" * 16}, "bbbbbbbb"))
    same = _trace(store, "20260101-000002-cccccc", _meta({NAME: OTHER},
                                                         "aaaaaaaa"))
    assert UNVERIFIABLE_ENV in unverifiable_checks(orig, other)
    assert UNVERIFIABLE_ENV not in unverifiable_checks(orig, same)
    assert unverifiable_checks(orig, same) == []


def test_info_replays_the_marker_in_its_short_form(store):
    """`info`'s replay of the stamp has already said the word
    `unverifiable` once; each check keeps its own reason and only the
    repeated word goes."""
    from sensorium.query.refocus_world import unverifiable_line

    assert unverifiable_line([UNVERIFIABLE_ENV]) == (
        "licence unverifiable: env (redacted, not comparable)")


# -- case 7: and it does not withhold --------------------------------------
def test_a_match_whose_only_caveat_is_the_marker_is_granted(store):
    """The rule this whole file turns on. `relicense` takes the markers out
    of the WITHHOLDING decision, so a MATCH whose only caveat is "a redacted
    variable could not be compared" earns its licence -- and the check that
    did not run is still printed and still stamped."""
    orig = _trace(store, "20260101-000000-aaaaaa",
                  _meta({NAME: OTHER}, "aaaaaaaa"))
    new = _trace(store, "20260101-000001-bbbbbb",
                 _meta({NAME: "f" * 16}, "bbbbbbbb"))
    a = {"verdict": "MATCH", "caveats": [UNVERIFIABLE_ENV],
         "licence": "withheld", "verified": [], "thread_scope": ""}
    out = relicense(a, orig, new, [])
    assert out["caveats"] == [] and out["licence"] == "granted"
    assert out["verified"], "a granted licence rests on stated facts"
