"""Rule v1 applied to a CAPTURE: the two operations of §2.3, at every text
a recorder stores.

`redact.py` answers "is this a secret-shaped NAME" and `redact_content.py`
answers "does this text hold a secret-shaped SPAN". Neither knows what a
payload looks like. This module is the one place that does: it takes the
capture dialect (`{"k": "str", "v": …}`, a `seq`/`map` sample, an `exc`
object, an output chunk) and applies whichever operation the rule calls for.

TWO OPERATIONS, NEVER BOTH
--------------------------
A NAME hit takes the whole capture (B4): the text becomes `<redacted>` and a
`redacted` object carries the digest of what was taken, so `diff`, `refocus`
and `watch` can still say "this is the same value" without printing it. A
CONTENT hit replaces only the matched span and keeps the sentence around it
(`postgres://u:<redacted>@h/db`), and carries no digest -- a partial cannot
honestly commit to the whole. The two never land on one capture: a value
already taken by name has no text left to scan, and the content rule refuses
anything already carrying `redacted` (§2.3).

THE STATE
---------
One module-level `State` (B6). `boot.run_target` installs the store key and
the knobs it read before the target resolved; a process that never installs
-- an in-process recording, the TypeScript ingest -- gets the default, which
is the rule ON and UNKEYED. That default is deliberate: "no key" must mean
"redacted, with no digest to compare", never "plaintext".

THE COUNT
---------
Nothing here counts. The transforms are pure: they take a capture and give
one back. `count(payload)` and `count_capture(capture)` READ a finished
payload and say how many values it withholds, and the recorder adds that at
each WRITE -- `tracer` at every `add_event`, the unwind exception it hands
`close_frame`, `boot` at the uncaught record, the tee at a chunk it stores.
`boot` publishes the run's delta as `redaction.values` (B3).

That shape is the whole of the count's honesty. The rule runs over values
the trace does not keep (`_on_line` re-captures every local at every line
and stores only the ones that CHANGED), and building a capture inside a
capture runs the observed program's own `__repr__`, which may itself print
-- reaching the tee, and the count -- from inside the window. A counter
bumped as the rule fires had to be rolled back for the dropped ones, and an
absolute roll-back erases whatever else landed in that window. Counting what
was WRITTEN needs no window: `values` is a function of the trace, which is
what B3 says it is and what the two converters independently compute.

This module imports `redact` and `redact_content` only -- nothing from
`record` or `query` -- and never raises. Like `capture.py`, everything here
runs from inside a `sys.monitoring` callback, so it touches nothing but
plain dicts, plain strings and the compiled patterns: every capture it is
handed has already been normalised (`capture.plain_str`, `plain_num`), and
no value in one can run the observed program's code.
"""
from dataclasses import dataclass
from pathlib import Path

from sensorium import redact
from sensorium.redact_content import content

#: Which rule took a value. The `redacted` object is exactly `{"by", "digest"}`
#: and nothing else, in every language that writes one (§4.2).
BY_NAME = "name"
BY_CONTENT = "content"

#: Where each capture kind keeps the value a NAME hit takes: the field the
#: marker replaces, and the field the digest is over (`num` through `repr`,
#: see `_text_of`).
_MARKER_FIELD = {"str": "v", "num": "v", "dbg": "v", "obj": "repr"}

#: Where the CONTENT rule reads. `num` is absent on purpose: a number holds
#: no text for a pattern to match, and scanning `repr(v)` would be scanning
#: a rendering the trace does not hold.
_SCAN_FIELD = {"str": "v", "dbg": "v", "obj": "repr"}

#: The kinds that withhold nothing, so the name rule leaves them alone: a
#: `None`, a truth value, and a value the object refused to hand over at all.
#: Redacting one would cost a reader a fact and hide no secret.
_WITHHOLDS_NOTHING = frozenset({"none", "bool", "unread"})

#: The same judgement over a TEXT, for the one kind that has no type of its
#: own (ruling R19). `undefined` and `null` are how node's inspector spells a
#: function that returned nothing; `()` is how Rust's `Debug` does (R17), and
#: this module reads both dialects. Whole texts, never a shape: `NaN` is a
#: value the program had, and a text that merely contains one of these is
#: taken like any other.
_DBG_WITHHOLDS_NOTHING = frozenset({"undefined", "null", "()"})

#: What a redacted container keeps (B4). Its size and its address are facts
#: about the program, not about the value; the sample is the value.
_CONTAINER_KEEPS = frozenset({"k", "type", "len", "oid"})

#: Every capture kind this module has a rule for. `record/capture.py`
#: produces all of these but `dbg`, which is the Rust and TypeScript
#: recorders' kind, and `tests/test_redact_values.py` pins that containment
#: against `capture.py` itself -- a kind added there without a rule here
#: would otherwise be stored as typed under a name that fires.
KINDS = frozenset(_MARKER_FIELD) | {"seq", "map"} | _WITHHOLDS_NOTHING

#: Where a payload keeps a capture, and where it keeps a map of them. Every
#: payload this recorder writes is built from these five keys.
_PAYLOAD_CAPTURES = ("value", "exc", "thrown")
_PAYLOAD_MAPS = ("args", "deltas")


@dataclass(frozen=True)
class State:
    """The key the digests are taken under, and the knobs the recording was
    made under -- read once, at the start of a run, and never re-read."""
    key: redact.Key
    knobs: redact.Knobs


#: The never-installed state: rule ON, no key, and a `problem` that says why
#: rather than pretending a key was looked for.
_UNINSTALLED = State(redact.Key(Path("unset"), None, "not installed"),
                     redact.Knobs(False, frozenset(), frozenset()))

_state = _UNINSTALLED

#: Read by `boot` as a before/after delta, exactly as `capture_stats` is.
#: Added to by the WRITE sites, from `count`/`count_capture` below -- never
#: by the transforms in this module.
stats = {"values": 0}


def install(key: redact.Key, knobs: redact.Knobs) -> None:
    global _state
    _state = State(key, knobs)


def reset() -> None:
    global _state
    _state = _UNINSTALLED


def state() -> State:
    return _state


def last_segment(qualname: str) -> str:
    """The name a returned value was asked for by (B7): `Cls.get_api_key` ->
    `get_api_key`, `outer.<locals>.inner` -> `inner`.

    `<lambda>`, `<module>` and `<genexpr>` come through unchanged and fire on
    nothing -- their segments are words in no set -- which is the answer, not
    a special case.
    """
    return qualname.rpartition(".")[2] or qualname


def _text_of(capture: dict) -> str | None:
    """The text this capture holds, or None where it holds none.

    A container's sample is not text: it is other captures, each with its
    own. That is why a redacted container has `digest: null` rather than a
    digest of some rendering the trace never held.
    """
    kind = capture.get("k")
    field = _MARKER_FIELD.get(kind)
    if field is None:
        return None
    text = capture.get(field)
    if kind == "num":
        # A number's text is its `repr`, computed here rather than stored:
        # the capture holds the number itself, and `1234` and `"1234"` must
        # not share a digest.
        return None if text is None else repr(text)
    return text if isinstance(text, str) else None


def digest_of(capture: dict) -> str | None:
    """`HMAC(key, the capture's own text)`, or None with no key and None for
    a kind that stores no text.

    Over the CLIPPED text, because that is what the trace would otherwise
    have held (§2.3): a digest of the 300 characters the program had could
    never be checked against a trace that only ever stores 200.
    """
    text = _text_of(capture)
    return None if text is None else _state.key.digest(text)


def named(name: str, capture: dict) -> dict:
    """`capture` under the name it was bound to: taken whole if the NAME rule
    fires, else offered to the content rule.

    The argument is never mutated, and an untouched capture is returned as it
    arrived -- the recorder compares captures with `!=` to find a line's
    deltas, and a copy that differed in nothing would still be a copy.
    """
    st = _state
    if st.knobs.off or "redacted" in capture:
        return capture
    if not redact.fires(name, st.knobs):
        return value(capture)
    kind = capture.get("k")
    if kind in _WITHHOLDS_NOTHING:
        return capture
    if kind == "dbg" and capture.get("v") in _DBG_WITHHOLDS_NOTHING:
        return capture
    return _taken(capture, kind)


def named_return(qualname: str, capture: dict) -> dict:
    """A RETURN value, under the last segment of the callee's qualname."""
    return named(last_segment(qualname), capture)


def _taken(capture: dict, kind: str) -> dict:
    """B4's per-kind table: the whole value, gone, and a digest of it."""
    digest = digest_of(capture)
    if kind in ("seq", "map"):
        out = {n: v for n, v in capture.items() if n in _CONTAINER_KEEPS}
    elif kind in _MARKER_FIELD:
        out = dict(capture)
        out.pop("trunc", None)          # nothing was clipped: it was taken
        out[_MARKER_FIELD[kind]] = redact.REDACTED
        if kind == "dbg":
            # Always present on a `dbg` capture, so it is written FALSE
            # rather than dropped: a reader that met it missing would have
            # to guess whether the formatter had been cut short.
            out["trunc"] = False
    else:
        # A kind this rule has never heard of, under a name that fires. The
        # only honest answer to "I do not know this shape" is to withhold
        # the whole of it: keeping it would store a secret the rule was
        # asked to take, and this control's failure direction has to be a
        # lost fact, never a kept secret. The kind itself stays -- a reader
        # has to be able to see WHAT was withheld -- and there is no digest,
        # because nothing here knows which field held the value.
        out = {n: v for n, v in capture.items() if n == "k"}
        digest = None
    out["redacted"] = {"by": BY_NAME, "digest": digest}
    return out


def value(capture: dict) -> dict:
    """`capture` with the CONTENT rule run over every text it holds --
    its own, and recursively those of a `seq`/`map` sample's captures.

    A capture already carrying `redacted` is returned as is: it was taken by
    name, so there is no text left to scan, and re-marking it would claim a
    second operation that never happened.
    """
    if _state.knobs.off or "redacted" in capture:
        return capture
    kind = capture.get("k")
    field = _SCAN_FIELD.get(kind)
    if field is not None:
        return _scanned(capture, field)
    if kind == "seq":
        return _sampled(capture, _item)
    if kind == "map":
        return _sampled(capture, _pair)
    # A kind with no text this scanner knows, `none`/`bool`/`unread`
    # included. Pass-through is right HERE and wrong in `named`: the content
    # rule replaces a span it FOUND, and it found nothing; the name rule was
    # told the whole value is a secret.
    return capture


def _scanned(capture: dict, field: str) -> dict:
    text = capture.get(field)
    if not isinstance(text, str):
        return capture
    after, hit = content(text)
    if not hit:
        return capture
    out = dict(capture)
    out[field] = after
    # `trunc` stays: the text WAS clipped, and a span inside it was replaced.
    out["redacted"] = {"by": BY_CONTENT, "digest": None}
    return out


def _sampled(capture: dict, through) -> dict:
    """The container, with `through` applied to each sampled entry.

    A depth-capped or unreadable capture has no `sample` at all (never an
    empty one), so this is a read with `.get`, and a container whose entries
    all came back untouched is returned untouched itself.
    """
    sample = capture.get("sample")
    if not isinstance(sample, list):
        return capture
    after = [through(entry) for entry in sample]
    if all(a is b for a, b in zip(after, sample)):
        return capture
    out = dict(capture)
    out["sample"] = after
    return out


def _item(entry):
    return value(entry) if isinstance(entry, dict) else entry


def _pair(entry):
    """One `map` sample pair. B8: a value held under a firing KEY is a secret
    held under a name, exactly as a local is -- a header dict's
    `authorization` entry is the case this exists for. The key itself is a
    name, not a secret, so only the content rule reaches it.
    """
    if not isinstance(entry, list) or len(entry) != 2:
        return entry
    key_cap, value_cap = entry
    if not isinstance(key_cap, dict) or not isinstance(value_cap, dict):
        return entry
    name = key_cap.get("v") if key_cap.get("k") == "str" else None
    after_key = value(key_cap)
    after_value = (named(name, value_cap) if isinstance(name, str)
                   else value(value_cap))
    if after_key is key_cap and after_value is value_cap:
        return entry
    return [after_key, after_value]


def exc(e: dict) -> dict:
    """One captured exception, with the content rule over its message.

    A message is a sentence the program wrote, not a value with an identity,
    so a hit is marked on the `exc` object itself and carries no digest --
    the same span operation, at the one text the format holds outside a
    capture. A message that could not be READ is left alone: there is no
    text to run the rule over, and there is nothing to withhold.
    """
    if _state.knobs.off or "redacted" in e:
        return e
    return _scanned(e, "msg")


def text(chunk: str) -> tuple[str, bool]:
    """One output chunk, as the program wrote it, with the content rule over
    it -- and whether anything CHANGED.

    The pair is `redact_content.content`'s own shape, and it is what lets the
    tee count a chunk it stores without comparing two strings it has already
    compared inside the rule.

    One `write()` at a time, which is the boundary the tee has: a secret
    split across two writes is not seen. A known limit of this rule, not an
    accident of it -- the tee holds no state between writes, and one that
    did would be a buffer of the program's output living in the instrument.
    """
    if _state.knobs.off or not isinstance(chunk, str):
        return chunk, False
    return content(chunk)


def count_capture(capture) -> int:
    """How many values one capture withholds: itself if it carries a
    `redacted` object, else however many its sample's captures do.

    A capture taken by NAME has no sample left, and a container is never a
    content hit (it stores no text of its own), so the early return cannot
    hide a nested count. A `map` pair is a two-element list and both halves
    are asked: a key can be a content hit while its value is a name hit, and
    that is two values withheld, not one.
    """
    if not isinstance(capture, dict):
        return 0
    if "redacted" in capture:
        return 1
    sample = capture.get("sample")
    if not isinstance(sample, list):
        return 0
    return sum(count_capture(x) for entry in sample
               for x in (entry if isinstance(entry, list) else (entry,)))


def count(payload) -> int:
    """How many values a finished payload withholds -- the number the writer
    adds to `stats` as it stores that payload.

    Reads the payload's own vocabulary (`args`, `deltas`, `value`, `exc`,
    `thrown`) rather than walking it blind: a payload key that is not a
    capture (`unbound`, `unread`, `caller`, `chain`) must never be counted,
    and a key that becomes one has to be added HERE, deliberately.
    """
    if not isinstance(payload, dict):
        return 0
    total = sum(count_capture(payload.get(k)) for k in _PAYLOAD_CAPTURES)
    for name in _PAYLOAD_MAPS:
        group = payload.get(name)
        if isinstance(group, dict):
            total += sum(count_capture(c) for c in group.values())
    return total
