"""Rule v1 over a CAPTURE: `redact_values`, on hand-built captures.

The two operations of §2.3 meet the recorder's payload dialect here. A NAME
hit redacts the whole capture per B4's per-kind table (`str`/`num`/`obj`/`dbg`
lose their text, a container loses its sample); a CONTENT hit replaces the
matched span inside whatever text the capture holds and leaves the rest.
Neither is allowed to touch the caller's dict, and every one of them bumps
`stats["values"]` exactly once -- the count a trace publishes as
`redaction.values`, which is a witness and not an estimate.

Captures are built by hand, never by recording something: the unit under
test is the rule, and a capture built from a live object would also be
testing `capture.py`'s caps and guards. The end-to-end reading -- that a
real recorder applies this at every site -- is
`tests/test_record_values_redaction.py`.
"""
import copy

import pytest

from sensorium import redact, redact_values as rv

#: A key with no store behind it: `Key.from_hex` is the shape a driver hands
#: down a wire, and it makes the digests in this module reproducible without
#: creating a file.
KEY = redact.Key.from_hex("ab" * 32)
ON = redact.Knobs(False, frozenset(), frozenset())
OFF = redact.Knobs(True, frozenset(), frozenset())

SECRET = "s3cret"

#: A value the CONTENT rule sees whatever it is called (`sk` row, §2.2).
TOKEN = "sk-" + "a" * 24


@pytest.fixture(autouse=True)
def installed():
    """Every test runs under one known key and knobs, and leaves none."""
    rv.install(KEY, ON)
    before = rv.stats["values"]
    yield before
    rv.reset()


def counted(before: int) -> int:
    return rv.stats["values"] - before


def unchanged(fn, capture: dict):
    """`fn(capture)`'s result, having proved the ARGUMENT was not mutated."""
    was = copy.deepcopy(capture)
    out = fn(capture)
    assert capture == was, "the argument was mutated"
    return out


# -- B4's table, one row at a time -----------------------------------------

def test_a_firing_name_takes_a_str_whole(installed):
    cap = {"k": "str", "v": SECRET, "trunc": True}
    out = unchanged(lambda c: rv.named("api_key", c), cap)
    assert out == {"k": "str", "v": redact.REDACTED,
                   "redacted": {"by": "name", "digest": KEY.digest(SECRET)}}
    assert "trunc" not in out          # nothing was clipped: it was taken
    assert counted(installed) == 1


def test_a_firing_name_takes_a_num_and_digests_its_repr(installed):
    out = unchanged(lambda c: rv.named("api_key", c), {"k": "num", "v": 1234})
    assert out == {"k": "num", "v": redact.REDACTED,
                   "redacted": {"by": "name", "digest": KEY.digest("1234")}}
    assert counted(installed) == 1


def test_a_firing_name_takes_an_obj_repr_and_keeps_its_identity(installed):
    cap = {"k": "obj", "type": "Cfg", "oid": 7, "repr": f"Cfg({SECRET!r})",
           "trunc": True}
    out = unchanged(lambda c: rv.named("credentials", c), cap)
    assert out == {"k": "obj", "type": "Cfg", "oid": 7,
                   "repr": redact.REDACTED,
                   "redacted": {"by": "name",
                                "digest": KEY.digest(f"Cfg({SECRET!r})")}}
    assert counted(installed) == 1


def test_a_firing_name_takes_a_dbg_text_and_says_it_is_not_clipped(installed):
    """`dbg` is the Rust/TypeScript capture kind: the text IS the value.

    `trunc` is FALSE rather than absent, because that key is always present
    on a `dbg` capture and a reader that met it missing would have to guess.
    """
    cap = {"k": "dbg", "v": f"'{SECRET}'", "trunc": True}
    out = unchanged(lambda c: rv.named("apiKey", c), cap)
    assert out == {"k": "dbg", "v": redact.REDACTED, "trunc": False,
                   "redacted": {"by": "name",
                                "digest": KEY.digest(f"'{SECRET}'")}}
    assert counted(installed) == 1


@pytest.mark.parametrize("kind, sample", [
    ("seq", [{"k": "str", "v": SECRET}]),
    ("map", [[{"k": "str", "v": "a"}, {"k": "str", "v": SECRET}]]),
])
def test_a_firing_name_takes_a_containers_sample_and_keeps_its_shape(
        installed, kind, sample):
    """A container has no stored text, so it has no digest -- but its size
    and its address are facts about the program, not about the secret."""
    cap = {"k": kind, "type": "T", "len": 3, "oid": 9, "sample": sample,
           "trunc": True, "unread": ["len"]}
    out = unchanged(lambda c: rv.named("secret_map", c), cap)
    assert out == {"k": kind, "type": "T", "len": 3, "oid": 9,
                   "redacted": {"by": "name", "digest": None}}
    assert counted(installed) == 1


@pytest.mark.parametrize("cap", [
    {"k": "none"},
    {"k": "bool", "v": True},
    {"k": "unread", "type": "Weird", "oid": 4, "unread": ["value"]},
])
def test_a_firing_name_leaves_a_value_that_withholds_nothing(installed, cap):
    """`None`, a truth value and a value nothing could be read from carry no
    secret to take: redacting them would cost a reader a fact and hide
    nothing."""
    out = unchanged(lambda c: rv.named("password", c), cap)
    assert out == cap
    assert "redacted" not in out
    assert counted(installed) == 0


# -- names, and the names inside a container -------------------------------

def test_a_map_value_under_a_firing_key_is_redacted_by_that_name(installed):
    """B8: a header dict's `authorization` entry is a secret held under a
    name, exactly as a local would be. Python only -- the other two
    recorders capture a rendering, where there is no key to read."""
    cap = {"k": "map", "type": "dict", "len": 1, "oid": 3, "sample": [
        [{"k": "str", "v": "authorization"}, {"k": "str", "v": "tok"}]]}
    out = unchanged(rv.value, cap)
    key_cap, value_cap = out["sample"][0]
    assert key_cap == {"k": "str", "v": "authorization"}    # the NAME stays
    assert value_cap == {"k": "str", "v": redact.REDACTED,
                         "redacted": {"by": "name",
                                      "digest": KEY.digest("tok")}}
    assert out["len"] == 1 and out["oid"] == 3
    assert "redacted" not in out       # the container itself withheld nothing
    assert counted(installed) == 1


def test_content_reaches_a_str_inside_a_seq_sample(installed):
    cap = {"k": "seq", "type": "list", "len": 2, "oid": 1, "sample": [
        {"k": "str", "v": "plain"}, {"k": "str", "v": f"use {TOKEN} now"}]}
    out = unchanged(rv.value, cap)
    assert out["sample"][0] == {"k": "str", "v": "plain"}
    assert out["sample"][1] == {
        "k": "str", "v": f"use {redact.REDACTED} now",
        "redacted": {"by": "content", "digest": None}}
    assert counted(installed) == 1


def test_content_reaches_an_obj_repr(installed):
    cap = {"k": "obj", "type": "Cfg", "oid": 7, "repr": f"Cfg({TOKEN!r})"}
    out = unchanged(rv.value, cap)
    assert out["repr"] == f"Cfg({redact.REDACTED!r})"
    assert out["redacted"] == {"by": "content", "digest": None}
    assert out["type"] == "Cfg" and out["oid"] == 7
    assert counted(installed) == 1


def test_named_reaches_the_content_rule_when_the_name_does_not_fire(
        installed):
    out = unchanged(lambda c: rv.named("headers", c),
                    {"k": "str", "v": TOKEN})
    assert out == {"k": "str", "v": redact.REDACTED,
                   "redacted": {"by": "content", "digest": None}}
    assert counted(installed) == 1


def test_named_return_reads_the_last_segment(installed):
    """The name a value is returned from is the name it was asked for by --
    the last segment of the qualname, never the class or the module."""
    cap = {"k": "str", "v": SECRET}
    fired = rv.named_return("Cls.get_api_key", cap)
    assert fired["v"] == redact.REDACTED
    assert fired["redacted"]["by"] == "name"
    assert rv.named_return("<lambda>", cap) == cap
    assert rv.named_return("main", cap) == cap
    assert rv.named_return("Cls.<locals>.main", cap) == cap
    # And the other direction, which is the reason this reads a segment at
    # all: a class whose own name fires does not make every method's return
    # a secret. `ApiKey.load` returns a config, not a key.
    assert rv.named_return("ApiKey.load", cap) == cap
    assert counted(installed) == 1
    assert rv.last_segment("Cls.get_api_key") == "get_api_key"
    assert rv.last_segment("ApiKey.load") == "load"
    assert rv.last_segment("main") == "main"


def test_the_content_rule_never_touches_a_name_redacted_capture(installed):
    """§2.3: a partial replacement cannot honestly carry a digest of the
    whole, so the two operations never both land on one capture."""
    taken = rv.named("api_key", {"k": "str", "v": f"{TOKEN} and more"})
    assert taken["redacted"]["by"] == "name"
    assert rv.value(taken) is taken
    assert counted(installed) == 1     # the name hit, and nothing after it


def test_the_content_rule_does_not_descend_into_a_taken_container(installed):
    taken = rv.named("secrets", {"k": "map", "type": "dict", "len": 1,
                                 "oid": 2, "sample": [
                                     [{"k": "str", "v": "authorization"},
                                      {"k": "str", "v": TOKEN}]]})
    assert "sample" not in taken       # there is nothing left to descend into
    assert rv.value(taken) == taken
    assert counted(installed) == 1


# -- the knobs, the key, the count, and the other two texts ----------------

def test_off_is_identity_and_counts_nothing(installed):
    rv.install(KEY, OFF)
    cap = {"k": "str", "v": TOKEN, "trunc": True}
    assert rv.named("api_key", cap) is cap
    assert rv.named_return("get_secret", cap) is cap
    assert rv.value(cap) is cap
    exc = {"type": "ValueError", "msg": TOKEN, "oid": 1}
    assert rv.exc(exc) is exc
    assert rv.text(TOKEN) == TOKEN
    assert counted(installed) == 0


def test_unkeyed_redacts_with_a_null_digest(installed):
    """No key is a lost COMPARISON, never a lost redaction."""
    rv.install(redact.Key.from_hex(None), ON)
    out = rv.named("api_key", {"k": "str", "v": SECRET})
    assert out == {"k": "str", "v": redact.REDACTED,
                   "redacted": {"by": "name", "digest": None}}
    assert counted(installed) == 1


def test_the_default_state_is_the_rule_on_and_unkeyed(installed):
    """B6: a recorder that never installed still redacts. The ingest and any
    in-process recording read this state, and a rule that defaulted off
    would make "no key" mean "plaintext"."""
    rv.reset()
    assert rv.state().knobs == ON
    assert rv.state().key.keyed is False
    assert rv.state().key.problem is not None
    out = rv.named("api_key", {"k": "str", "v": SECRET})
    assert out["v"] == redact.REDACTED
    assert out["redacted"] == {"by": "name", "digest": None}


def test_exc_hit_marks_the_exc_object(installed):
    e = {"type": "ValueError", "msg": f"bad key {TOKEN}", "oid": 5,
         "serial": 2}
    out = unchanged(rv.exc, e)
    assert out == {"type": "ValueError",
                   "msg": f"bad key {redact.REDACTED}", "oid": 5,
                   "serial": 2,
                   "redacted": {"by": "content", "digest": None}}
    assert counted(installed) == 1


def test_an_exc_message_with_nothing_in_it_is_left_alone(installed):
    e = {"type": "KeyError", "msg": "no such row", "oid": 5}
    assert rv.exc(e) is e
    # A message that could not be read at all is not a message with no
    # secret in it: there is no text to run the rule over, and inventing one
    # would be the instrument reporting on a read it never made.
    unreadable = {"type": "E", "oid": 1, "unread": ["msg"]}
    assert rv.exc(unreadable) is unreadable
    assert counted(installed) == 0


def test_an_output_chunk_is_content_ruled(installed):
    assert rv.text(f"token={TOKEN}\n") == f"token={redact.REDACTED}\n"
    assert counted(installed) == 1
    assert rv.text("hello\n") == "hello\n"
    assert counted(installed) == 1


def test_stats_count_every_operation_once(installed):
    rv.named("api_key", {"k": "str", "v": SECRET})            # a name hit
    rv.value({"k": "str", "v": TOKEN})                        # a content hit
    rv.exc({"type": "E", "msg": TOKEN, "oid": 1})             # an exc hit
    rv.text(TOKEN)                                            # an output hit
    assert counted(installed) == 4


def test_digest_of_reads_each_kinds_own_text(installed):
    assert rv.digest_of({"k": "str", "v": SECRET}) == KEY.digest(SECRET)
    assert rv.digest_of({"k": "num", "v": 1234}) == KEY.digest("1234")
    assert rv.digest_of({"k": "dbg", "v": "x"}) == KEY.digest("x")
    assert rv.digest_of({"k": "obj", "type": "T", "oid": 1,
                         "repr": "T()"}) == KEY.digest("T()")
    for cap in ({"k": "seq", "len": 1}, {"k": "map", "len": 1},
                {"k": "none"}, {"k": "bool", "v": False},
                {"k": "unread", "unread": ["value"]}):
        assert rv.digest_of(cap) is None
