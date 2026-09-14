"""What `info` says about the rule a recording was made under.

Two fields, and they answer two different questions. The `env:` field says
what the rule TOOK OUT of this trace's environment -- names only, never the
digest, because a digest printed beside the name it belongs to is an offline
guessing target for a short value and this command's whole purpose is to be
readable over someone's shoulder. The `redaction:` line says what the rule
WAS: which rule, whether the store could key it, and whose hand last applied
it -- the parameters of the recording, printed beside the other declared
parameters (`caps:`) rather than left to be inferred from the presence of a
marker further down.

A trace with no `redaction` key at all gets ONE new line and nothing else:
every other byte `info` printed for it before this slice is printed still.
That is the fence `test_a_trace_from_before_the_rule_gains_exactly_one_line`
holds, and it is what lets a reader trust that the absence of the field is
the recorder's silence rather than this command's.

The traces are hand-built: what is under test is the rendering of a `meta`
shape, and a recording made through `sensorium run` would carry whatever the
launching shell happened to hold (`tests/test_record_redaction.py` states
why an exact count of a real environment is a test of whoever's shell ran
it). The shapes here are the four the recorder can write.
"""
import os
import stat
from pathlib import Path

from sensorium import redact
from sensorium.store.writer import TraceWriter
from tests.helpers import finalize_synthetic, run_cli

RUN = "20260101-000000-aaaaaa"
HASH = "3c2cfb29aaaaaaaa"

#: The planted digest. Sixteen hex characters, the shape `Key.digest`
#: returns, and it must never reach the terminal -- the `env:` field prints
#: the NAME of a redacted variable and nothing else about it.
DIGEST = "0123456789abcdef"

#: One firing name and one that does not fire, so every assertion below
#: states both halves of the judgement: what was redacted AND what was left.
SECRET, PLAIN = "SECRET_TOKEN", "HOME"

ENV = {SECRET: redact.REDACTED, PLAIN: "/h"}


def _on(table, *, keyed=True, key_id="0a1b2c3d", by="recorder",
        values=None) -> dict:
    """The `redaction` object a recorder writes with the rule ON.

    `values` is omitted unless a test asks for it: a recorder that never
    counted writes no such key at all, and the difference between "took
    none" and "did not count" is one of the things the line must keep
    saying.
    """
    out = {"rule": "v1", "mode": "on", "keyed": keyed, "key_id": key_id,
           "env": table, "names": [], "allow": [], "by": by}
    if values is not None:
        out["values"] = values
    return out


def _info(tmp_path, env=None, redaction=None, *, store=None) -> str:
    """Build one trace carrying `env`/`redaction` and run `info` on it.

    `redaction=None` writes NO key, which is a trace from before the rule
    existed -- not the same thing as one whose rule was turned off.
    """
    sdir = Path(store or Path(tmp_path) / "sdir")
    w = TraceWriter(sdir / "traces" / f"{RUN}.db", batch=1)
    w.set_meta("env", ENV if env is None else env)
    if redaction is not None:
        w.set_meta("redaction", redaction)
    finalize_synthetic(w, run_id=RUN, env_hash=HASH)
    w.close()
    r = run_cli(["info", RUN], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def _line(out: str, prefix: str) -> str:
    return next(ln for ln in out.splitlines() if ln.startswith(prefix))


# -- the `redaction:` line, all four forms ---------------------------------
def test_the_keyed_line_names_the_rule_the_key_and_the_hand(tmp_path):
    """The ordinary recording. The key id is what makes two traces'
    digests comparable at all, so it is printed rather than implied by the
    word `keyed`, and `by` is the LAST hand that applied the rule."""
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST}))
    assert _line(out, "redaction:") == (
        "redaction: rule v1, keyed (key 0a1b2c3d), by recorder")


def test_the_redaction_line_sits_directly_under_the_caps_line(tmp_path):
    """It is a parameter of the recording, and it prints where the other
    declared parameters print. Adjacency, not mere presence: a line that
    drifted to the bottom of the output would still contain the words."""
    lines = _info(tmp_path, redaction=_on({SECRET: DIGEST})).splitlines()
    at = next(i for i, ln in enumerate(lines) if ln.startswith("caps: "))
    assert lines[at + 1].startswith("redaction: ")


def test_an_unkeyed_recording_names_the_file_the_store_is_missing(tmp_path):
    """UNKEYED in capitals and the file by name: a reader whose digests
    will not compare needs to know which file to look for, and a recording
    made without one can never be made comparable after the fact."""
    out = _info(tmp_path,
                redaction=_on({SECRET: None}, keyed=False, key_id=None))
    assert _line(out, "redaction:") == (
        "redaction: rule v1, UNKEYED (no redaction.key in the store); "
        "by recorder")


def test_the_rule_turned_off_says_what_that_cost(tmp_path):
    """`mode: off` is a decision somebody made, and the line states its
    consequence in words rather than leaving `OFF` to be read as tidy."""
    out = _info(tmp_path, redaction={"rule": "v1", "mode": "off"})
    assert _line(out, "redaction:") == (
        "redaction: OFF (SENSORIUM_NO_REDACT) -- the environment and every "
        "captured value are stored in plaintext")


def test_a_trace_from_before_the_rule_says_so(tmp_path):
    """Absence of the key is not absence of secrets. An old trace holds a
    live environment in plaintext and the line says which of the two
    silences this is."""
    out = _info(tmp_path)
    assert _line(out, "redaction:") == (
        "redaction: none -- recorded before redaction existed; plaintext "
        "throughout")


def test_a_trace_from_before_the_rule_gains_exactly_one_line(tmp_path):
    """The fence. An older trace prints everything it printed before this
    slice plus the one `none` line -- so the `env:` field is the bare hash,
    with no count and no parenthesis, and nothing else moved."""
    out = _info(tmp_path)
    assert f"env:{HASH}  exit:" in out
    assert out.count("redaction:") == 1
    assert "vars," not in out and "redacted" not in out


# -- the `env:` field ------------------------------------------------------
def test_the_env_field_names_the_variables_the_rule_took(tmp_path):
    """Counted over the STORED environment and named: `2 vars` is what the
    trace holds, `1 redacted` is what the rule fired on, and the name is
    what a reader needs to judge whether the rule fired on the right thing.
    """
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST}))
    assert f"env:{HASH} (2 vars, 1 redacted: {SECRET})  exit:" in out


def test_the_digest_is_never_printed(tmp_path):
    """The one thing this field must never leak. A digest is an equality
    identity, not a commitment: printed beside the name it belongs to it is
    an offline guessing target for any short value."""
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST}))
    assert DIGEST not in out


def test_the_env_field_states_a_measured_zero(tmp_path):
    """`0 redacted` and not silence: the rule RAN and fired on nothing,
    which is a different fact from a trace that predates it -- and the two
    must not print the same."""
    out = _info(tmp_path, env={PLAIN: "/h"}, redaction=_on({}))
    assert f"env:{HASH} (1 vars, 0 redacted)  exit:" in out


def test_the_env_field_is_the_bare_hash_when_the_rule_was_off(tmp_path):
    """Nothing was taken, so there is nothing to name. The `redaction:`
    line below carries the whole of that fact."""
    out = _info(tmp_path, redaction={"rule": "v1", "mode": "off"})
    assert f"env:{HASH}  exit:" in out


def test_nine_redacted_names_print_eight_and_count_the_rest(tmp_path):
    """`_capped`'s semantics, reused rather than re-spelled: at most eight
    names, then the count of what was not shown. The count beside the list
    is always the whole of it."""
    names = [f"TOKEN_{i}" for i in range(9)]
    out = _info(tmp_path, env={n: redact.REDACTED for n in names},
                redaction=_on({n: DIGEST for n in names}))
    assert (f"env:{HASH} (9 vars, 9 redacted: " + ", ".join(sorted(names)[:8])
            + ", +1 more)  exit:") in out


# -- the store key's own file mode -----------------------------------------
def test_a_key_looser_than_0600_is_named_on_the_keyed_line(tmp_path):
    """A key the store reads at 0644 is READ anyway -- refusing to compare
    over a user's own file permissions helps nobody -- and named, because a
    world-readable key makes every digest in the store guessable."""
    sdir = Path(tmp_path) / "sdir"
    key = redact.Key.load_or_create(sdir)
    os.chmod(key.path, 0o644)
    assert stat.S_IMODE(key.path.stat().st_mode) == 0o644
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST},
                                        key_id=key.key_id), store=sdir)
    assert _line(out, "redaction:") == (
        f"redaction: rule v1, keyed (key {key.key_id}), by recorder "
        "(key mode 0644 -- expected 0600)")


def test_a_loose_key_that_did_not_write_these_digests_is_not_named(tmp_path):
    """The note is about THIS trace's key. A store whose key has been
    replaced since the recording says nothing about the mode of a file that
    never touched it -- the digests do not compare either way, and naming
    the mode there would send a reader to the wrong file."""
    sdir = Path(tmp_path) / "sdir"
    key = redact.Key.load_or_create(sdir)
    os.chmod(key.path, 0o644)
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST},
                                        key_id="ffffffff"), store=sdir)
    assert _line(out, "redaction:") == (
        "redaction: rule v1, keyed (key ffffffff), by recorder")


# -- the count of captured values the rule took ----------------------------
def test_the_keyed_line_counts_the_values_the_rule_took(tmp_path):
    """`redaction.values` is written by the recorder at the WRITE, so it is
    a count of what actually went to disk rather than of what the rule was
    asked about. It rides the `redaction:` line and not the `env:` field
    because it is a fact about the whole recording -- captures, output
    chunks and exception messages -- not about the environment."""
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST}, values=12))
    assert _line(out, "redaction:") == (
        "redaction: rule v1, keyed (key 0a1b2c3d), by recorder; "
        "values redacted: 12")


def test_the_unkeyed_line_counts_them_too(tmp_path):
    """Whether the store could key the digests says nothing about how many
    values were taken. A clause that appeared on only one of the two forms
    would make an unkeyed recording read as one the rule never fired in."""
    out = _info(tmp_path, redaction=_on({SECRET: None}, keyed=False,
                                        key_id=None, values=3))
    assert _line(out, "redaction:") == (
        "redaction: rule v1, UNKEYED (no redaction.key in the store); "
        "by recorder; values redacted: 3")


def test_a_measured_zero_is_printed_rather_than_left_out(tmp_path):
    """The rule RAN and took nothing, which is a different fact from a
    recorder that never counted -- and the two must not print the same, for
    the reason the `env:` field's own measured zero exists."""
    out = _info(tmp_path, redaction=_on({}, values=0))
    assert _line(out, "redaction:").endswith("; values redacted: 0")


def test_a_recorder_that_never_counted_says_nothing(tmp_path):
    """The fence around every trace written before the count existed: with
    no `values` key the line is byte-identical to what it was, and a `0`
    invented here would be a measurement this recording never made."""
    out = _info(tmp_path, redaction=_on({SECRET: DIGEST}))
    assert _line(out, "redaction:") == (
        "redaction: rule v1, keyed (key 0a1b2c3d), by recorder")
    assert "values redacted:" not in out


def test_the_clause_never_rides_a_rule_that_did_not_run(tmp_path):
    """`OFF` and `none` state that nothing was taken in words. A count
    beside either would be a second, weaker way of saying it -- and on the
    `none` line it would be a claim about a recorder that had no rule."""
    for i, redaction in enumerate(({"rule": "v1", "mode": "off",
                                    "values": 4}, None)):
        # A store apiece: both arms write the same run id, and one trace
        # file cannot be built twice.
        out = _info(tmp_path, redaction=redaction,
                    store=Path(tmp_path) / f"sdir{i}")
        assert "values redacted:" not in out
