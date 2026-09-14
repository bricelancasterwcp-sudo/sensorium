"""How a capture the redaction rule TOOK renders, everywhere values print.

One helper decides it (`fmt._redacted_marker`) and `fmt_value` reads it
before its kind dispatch, so `grep`, `tree`, `frame`, `flow` and `watch`'s
state lines all say the same thing about one capture. That ordering is the
whole point: a name-redacted `num` holds the STRING `<redacted>` in its `v`,
and the `num` arm would print it through `repr` as `'<redacted>'` -- a
number rendered as a quoted string, which reads as a value the program held.

What the marker carries, and what it must never carry:

  * The first EIGHT hex of the digest, so two captures taken from the same
    value can be told apart by eye (`token=<redacted #01234567>` twice is
    the same secret twice). Never the whole sixteen: a full digest printed
    beside the name it belongs to is an offline guessing target for any
    short value, which is the same rule `info`'s `env:` field keeps.
  * Nothing at all where there is no digest -- a container's value was
    taken but never hashed (there is no one text to hash), and a kind the
    rule did not recognise is withheld whole without one.

A CONTENT hit is not this case and does not render a marker: the rule
replaced a span INSIDE a text the recorder kept, so what the trace holds is
the text, and the reader prints the text it holds.
"""
from sensorium.query.fmt import _redacted_marker, fmt_args, fmt_exc, fmt_value

#: The planted digest, sixteen hex characters -- `redact.Key.digest`'s shape.
DIGEST = "0123456789abcdef"
HEAD = "01234567"


def by_name(digest=DIGEST) -> dict:
    return {"by": "name", "digest": digest}


BY_CONTENT = {"by": "content", "digest": None}

#: What the writer stores in the field the marker replaced (`redact.REDACTED`
#: -- spelled out rather than imported so a change to either side shows up
#: here as a failure rather than as two constants agreeing with themselves).
STORED = "<redacted>"


# -- the six renderings (design B12) ---------------------------------------
def test_a_redacted_string_renders_the_first_eight_hex_of_its_digest():
    """The digest is what makes two takings comparable, and eight hex is
    enough to compare by eye. It is NOT the quoted `'<redacted>'` the `str`
    arm would print, which reads as a string the program held."""
    v = {"k": "str", "v": STORED, "redacted": by_name()}
    assert fmt_value(v) == f"<redacted #{HEAD}>"


def test_a_redacted_number_renders_the_marker_and_not_a_quoted_string():
    """The `num` arm prints `repr(v["v"])`, and a taken number's `v` is the
    marker TEXT -- so reaching that arm renders `'<redacted>'`, a number
    shown as a quoted string. The check runs before the dispatch."""
    v = {"k": "num", "v": STORED, "redacted": by_name("fedcba9876543210")}
    assert fmt_value(v) == "<redacted #fedcba98>"


def test_a_redacted_rendered_text_renders_the_marker():
    """`dbg` is the Rust and TypeScript recorders' kind: the text IS the
    capture, so a taken one has no text left to print."""
    v = {"k": "dbg", "v": STORED, "trunc": False, "redacted": by_name()}
    assert fmt_value(v) == f"<redacted #{HEAD}>"


def test_a_taken_value_with_no_digest_says_only_that_it_was_taken():
    """`<redacted #None>` would be a reader inventing a digest out of a
    null. A container is hashed as nothing (there is no one text to hash),
    and so is a kind the rule did not recognise and withheld whole."""
    assert fmt_value({"k": "str", "v": STORED,
                      "redacted": by_name(None)}) == STORED


def test_a_redacted_container_keeps_its_type_and_its_length():
    """Its size is a fact about the program, not about the value -- the
    writer keeps it on purpose (B4), so the reader prints it. `[3]` and the
    marker in place of the members is the shape a reader can act on."""
    v = {"k": "seq", "type": "list", "len": 3, "oid": 5,
         "redacted": by_name(None)}
    assert fmt_value(v) == f"list[3]={STORED}"


def test_a_redacted_container_whose_length_was_never_read_prints_a_question():
    """`_size`'s rule, kept: `len` is None exactly when the object's own
    `__len__` raised, and printing 0 there would be the reader inventing a
    size the recording does not hold."""
    v = {"k": "map", "type": "dict", "len": None, "oid": 5,
         "redacted": by_name(None)}
    assert fmt_value(v) == f"dict[?]={STORED}"


def test_a_redacted_object_renders_exactly_as_it_did_before():
    """An object's identity is not its value. The rule takes the `repr` and
    leaves `type`/`oid`, which is all this rendering ever read -- so
    `Cfg#7` here is the same bytes as `Cfg#7` from an untouched capture, and
    `flow --object` can still follow it."""
    v = {"k": "obj", "type": "Cfg", "oid": 7, "repr": STORED,
         "redacted": by_name()}
    assert fmt_value(v) == "Cfg#7"
    assert fmt_value({"k": "obj", "type": "Cfg", "oid": 7,
                      "repr": "Cfg(...)"}) == "Cfg#7"


def test_a_content_hit_prints_the_text_the_trace_actually_holds():
    """The rule replaced a SPAN; the rest of the text is what the program
    had, and it is the reason the content rule exists at all -- a reader
    seeing `postgres://u:<redacted>@h/db` knows the host and the database
    and not the password. Quoted, because it is still a string capture."""
    v = {"k": "str", "v": "postgres://u:<redacted>@h/db",
         "redacted": BY_CONTENT}
    assert fmt_value(v) == "'postgres://u:<redacted>@h/db'"


# -- the helper itself, and the callers that read through it ---------------
def test_the_helper_answers_none_for_everything_it_does_not_mark():
    """`None` is "this kind renders as it always did", and it is what keeps
    the check ahead of the dispatch from swallowing the ordinary cases: an
    untouched capture, a content hit, and a redacted object all fall
    through to the arms below it."""
    assert _redacted_marker({"k": "str", "v": "hunter2"}) is None
    assert _redacted_marker({"k": "str", "v": "a<redacted>b",
                             "redacted": BY_CONTENT}) is None
    assert _redacted_marker({"k": "obj", "type": "Cfg", "oid": 7,
                             "repr": STORED, "redacted": by_name()}) is None


def test_the_argument_list_marks_only_the_argument_that_was_taken():
    """One call, two arguments, one rule firing. The point of naming the
    argument beside its marker is that a reader can see WHICH value went --
    a line that hid both would be a worse record than one that hid none."""
    args = {"token": {"k": "str", "v": STORED, "redacted": by_name()},
            "url": {"k": "str", "v": "postgres://u:<redacted>@h/db",
                    "redacted": BY_CONTENT},
            "retries": {"k": "num", "v": 3}}
    assert fmt_args(args) == (
        f"token=<redacted #{HEAD}>, url='postgres://u:<redacted>@h/db', "
        "retries=3")


def test_an_exception_message_prints_the_text_the_recorder_stored():
    """A message is a sentence the program wrote, and the content rule
    replaces a span in it -- there is no name rule over a message, so there
    is no marker here and `fmt_exc` prints what it is handed."""
    e = {"type": "ValueError", "msg": "bad token <redacted>",
         "oid": 1, "redacted": BY_CONTENT}
    assert fmt_exc(e) == "ValueError('bad token <redacted>')"


def test_the_whole_digest_is_never_printed():
    """The fence. Eight hex compares; sixteen guesses -- and a rendering
    that leaked the whole digest would put it on every line every reader
    sees, which is a wider leak than `info`'s one field."""
    for v in ({"k": "str", "v": STORED, "redacted": by_name()},
              {"k": "num", "v": STORED, "redacted": by_name()},
              {"k": "dbg", "v": STORED, "trunc": False,
               "redacted": by_name()}):
        assert DIGEST not in fmt_value(v)
