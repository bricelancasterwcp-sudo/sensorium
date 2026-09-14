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

The first half's pairs are built from `meta` alone. What is under test there
is the comparison table and the two sentences it writes, and a recorded pair
would carry whatever the launching shell held -- the same reason
`tests/test_record_redaction.py` gives for never asserting on the SIZE of a
real `redaction.env`.

The second half re-runs a real program through `sensorium refocus`, because
what it tests is the Python branch's own WIRING -- which of the licence's
two hands the branch calls, and what the environment it compares against is
-- and neither of those is visible from a meta-built pair. Those tests
assert on membership and never on counts, for the reason above.
"""
import pytest

from sensorium import paths, redact
from sensorium.query.refocus_env import RedactionPair
from sensorium.query.refocus_world import (UNVERIFIABLE_ENV, _env_diff,
                                           _env_state, relicense,
                                           unverifiable_checks)
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import finalize_synthetic, record_script, run_cli
from tests.refocus_programs import LOOP, new_run

#: One redacted name and one that was never redacted, so every case states
#: both halves: what the table decided AND that everything else still takes
#: the plain-equality path it always took.
NAME, PLAIN = "MY_API_KEY", "PATH"
#: A session-set name that ALSO fires rule v1 (`AUTH` is one of its
#: segments), which is what makes ruling R21 a real case and not a
#: hypothetical: every shell on this box carries it.
SESSION = "SSH_AUTH_SOCK"
#: A harness-set name. NOTHING in harness set 1 fires the name rule by
#: itself -- `VITEST`, `POOL`, `WORKER`, `ID` are in no segment set -- so a
#: redacted one arrives only through `SENSORIUM_REDACT_NAMES`, and the meta
#: below records that knob the way the recorder stamps it.
HARNESS = "VITEST_POOL_ID"
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


def _meta(table, key_id=KEY_ID, *, keyed=True, env=None, names=()) -> dict:
    """One side's meta: the stored environment and the rule that made it.

    `names` is `SENSORIUM_REDACT_NAMES` as the recorder stamped it --
    normalised, sorted -- which is the only way a name the rule does not
    fire on by itself comes to be redacted at all.
    """
    return {"env": {NAME: redact.REDACTED, PLAIN: "/usr/bin"}
                   if env is None else env,
            "redaction": {"rule": "v1", "mode": "on", "keyed": keyed,
                          "key_id": key_id, "env": table,
                          "names": sorted(names), "allow": [],
                          "by": "recorder"}}


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


# -- the Python branch, end to end -----------------------------------------
#: A name whose segments fire the rule, planted in the RECORDED process's
#: own environment (`env_extra`), because this process's environment is not
#: the one under test -- the recorder runs in a subprocess.
LIVE = "MY_API_KEY"


def _record(tmp_path, value=SECRET, sdir=None):
    """Record `LOOP` with `LIVE` planted, into `tmp_path/sdir`."""
    run_id, _trace, r = record_script(tmp_path, LOOP, env_extra={LIVE: value})
    assert run_id, r.stderr + r.stdout
    return run_id, (sdir or tmp_path / "sdir")


def _refocus(tmp_path, sdir, run_id, **env_extra):
    """Re-run through the real CLI. `LIVE` is planted on the live side too
    unless a test overrides it: the ordinary case is one shell re-running
    its own recording, where the secret is still there and still the same,
    and a test that silently dropped it would be measuring a variable that
    VANISHED -- which is a difference, and a verified one."""
    r = run_cli(["refocus", run_id, "--focus", "prog:accumulate"],
                cwd=tmp_path, sensorium_dir=sdir,
                env_extra={LIVE: SECRET, **env_extra})
    assert r.returncode == 0, r.stdout + r.stderr
    return r, Trace.open(sdir / "traces" / f"{new_run(r.stdout)}.db").meta


def _env_line(out: str) -> str:
    return next(ln for ln in out.splitlines() if ln.startswith("env: "))


def _unkeyed_original(tmp_path):
    """A pair whose two sides can never be compared, re-run for real.

    The store's key is a ZERO-BYTE file when the original is recorded (the
    shape `Key.load_or_create` refuses to write over: it is the user's
    file), so that recording is unkeyed and its digests are `null`. The key
    is then removed, and the re-run mints a real one -- two sides that can
    never be compared, over variables that in fact never changed.
    """
    sdir = tmp_path / "sdir"
    (sdir / "traces").mkdir(parents=True)
    (sdir / redact.KEY_FILE).write_bytes(b"")
    run_id, _ = _record(tmp_path)
    (sdir / redact.KEY_FILE).unlink()
    return (*_refocus(tmp_path, sdir, run_id), sdir)


def test_a_pair_whose_digests_cannot_be_compared_is_still_granted(tmp_path):
    """R19. The Python branch performs its own re-run and used to keep the
    unverifiable markers in the WITHHOLDING decision, because it never
    called `relicense` -- so a store whose key was gone when the original
    was recorded withheld the licence over a check that could not run,
    which is the one thing §6.2 says the marker must not do.
    """
    r, meta, _sdir = _unkeyed_original(tmp_path)
    line = _env_line(r.stdout)
    assert line.startswith("env: unchanged (")
    assert "redacted variable(s) not comparable (unkeyed): " in line
    assert LIVE in line
    assert "licence: WITHHELD" not in r.stdout
    assert meta["refocus_licence"] == "granted"
    assert meta["refocus_licence_unverifiable"] == [UNVERIFIABLE_ENV]


def test_info_replays_the_python_pair_s_unverifiable_check(tmp_path):
    """The other half of R19: the Python branch STAMPS the markers too, so
    `info` on the re-run says which check the granted licence does not rest
    on. Without the stamp a reader of the trace was told the licence was
    granted and never told what went unchecked."""
    _r, meta, sdir = _unkeyed_original(tmp_path)

    out = run_cli(["info", meta["run_id"]], cwd=tmp_path, sensorium_dir=sdir)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "licence unverifiable: env (redacted, not comparable)" in out.stdout
    assert "licence: granted" in out.stdout


def test_a_redacted_variable_that_really_changed_still_withholds(tmp_path):
    """The discriminating control, and the reason R19 is a narrow change: a
    digest that DIFFERS under one key is a variable that changed, and it
    withholds exactly as it always did. `relicense` removes the markers'
    vote and nothing else's -- a licence granted over a rotated secret is
    the failure this whole check exists to refuse."""
    run_id, sdir = _record(tmp_path)
    r, meta = _refocus(tmp_path, sdir, run_id, **{LIVE: "rotated"})

    assert f"env: CHANGED since the original run -- 1 variable(s) differ: " \
           f"{LIVE}" in _env_line(r.stdout)
    assert "licence: WITHHELD" in r.stdout
    assert meta["refocus_licence"] == "withheld"
    assert meta["refocus_licence_unverifiable"] == []


def test_the_key_variable_is_not_compared_on_the_live_side(tmp_path):
    """R20. Every recorder DELETES `SENSORIUM_REDACT_KEY` from what it
    records (`redact.env`), so a trace never holds it -- but the Python
    branch compares against this process's live environment, where a driver
    that handed the key down has left it set. Compared as it arrives, it is
    a variable that appeared out of nowhere and withholds the licence over
    the tool's own plumbing. Popped from the snapshot, the live side is the
    same view of the environment the recorder took."""
    run_id, sdir = _record(tmp_path)
    r, meta = _refocus(tmp_path, sdir, run_id, **{redact.KEY_VAR: "ab" * 32})

    assert _env_line(r.stdout).startswith("env: unchanged (")
    assert redact.KEY_VAR not in r.stdout
    assert meta["refocus_licence"] == "granted"


# -- R21: the two sets are judgements about the NAME -----------------------
def test_a_redacted_session_variable_keeps_its_exemption(store):
    """`SSH_AUTH_SOCK` is in session set 1 AND fires rule v1. Read as a
    plain change, a re-run from another terminal would withhold on every
    trace recorded after the rule and grant on every one recorded before
    it -- the same pair, two answers, decided by whether the value was
    stored or digested. Set membership is a judgement about the name, so a
    differing digest is partitioned exactly as a differing value is."""
    env = {SESSION: redact.REDACTED, PLAIN: "/usr/bin"}
    was = _meta({SESSION: OTHER}, env=env)
    now = _meta({SESSION: "f" * 16}, env=env)
    changed, _rel, _str, session, harness, unsure = _diff(
        was, now["env"], now)
    assert session == [SESSION] and changed == [] and unsure == []
    assert harness == []

    line, caveat, fact = _env_state(was, now["env"], now_meta=now)
    assert line.startswith("env: unchanged outside session set 1 (")
    assert f"1 session variable(s) differ: {SESSION}" in line
    assert f"1 session variable(s) differ: {SESSION}" in fact
    assert caveat is None


def test_a_redacted_harness_variable_keeps_its_exemption(store):
    """The same rule for the other set. No name in harness set 1 fires rule
    v1 on its own, so this case reaches a real store only through
    `SENSORIUM_REDACT_NAMES` -- recorded in `redaction.names`, which is why
    the knob is stamped at all: a reader has to be able to see why a name
    nobody would call secret was digested."""
    env = {HARNESS: redact.REDACTED, PLAIN: "/usr/bin"}
    knob = [redact.normalise(HARNESS)]
    was = _meta({HARNESS: OTHER}, env=env, names=knob)
    now = _meta({HARNESS: "f" * 16}, env=env, names=knob)
    changed, _rel, _str, session, harness, unsure = _diff(
        was, now["env"], now)
    assert harness == [HARNESS] and changed == [] and unsure == []
    assert session == []

    line, caveat, _fact = _env_state(was, now["env"], now_meta=now)
    assert line.startswith("env: unchanged outside harness set 1 (")
    assert f"1 harness variable(s) differ: {HARNESS}" in line
    assert caveat is None


# -- R22: the count says how many were actually compared -------------------
def test_the_compared_count_excludes_the_uncomparable(store):
    """A line that says "2 variables compared" and then names one of the
    two as not comparable has counted a check it did not run. The count is
    the plain one MINUS the uncomparable names, on the line and in the
    stamped fact alike -- two channels carrying one number."""
    was = _meta({NAME: OTHER}, "aaaaaaaa")
    now = _meta({NAME: "f" * 16}, "bbbbbbbb")
    line, _caveat, fact = _env_state(was, now["env"], now_meta=now)

    compared = len(set(was["env"]) | set(now["env"])) - len([NAME])
    assert compared == 1
    assert line.startswith(f"env: unchanged ({compared} variables compared;")
    assert fact.startswith(f"{compared} environment variable(s) compared "
                           "and unchanged")


# -- R19 parity: the terminal is told what the trace was stamped with ------
def test_the_python_branch_prints_the_checks_that_could_not_run(tmp_path):
    """Stamped AND printed, where the other two branches print it. A reader
    watching the run was told the licence held and never told which check
    the verdict does not rest on; the trace said more than the screen."""
    r, _meta, _sdir = _unkeyed_original(tmp_path)
    assert "checks that could not run on this pair" in r.stdout
    assert f"  - {UNVERIFIABLE_ENV}" in r.stdout
