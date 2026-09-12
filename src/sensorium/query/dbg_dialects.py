"""Which language's formatter wrote a `dbg` capture, and the pair that
reads and writes it.

A `dbg` capture is TEXT, and the text alone cannot say what it spells:
`'rate'` is the string rate to `util.inspect` and a five-character word to
Rust's `Debug`, and `5` is an integer in one and could be either in the
other. Two commands read that text -- `watch --expr` through
`expr.resolve`, `flow --value` through `flow_values.matches` -- and both
must ask the TRACE which dialect wrote it, never the text and never a
`lang` branch of their own (the discipline design 2026-09-06 section 4.1
set for the first two recorders and this rung keeps for the third).

So the word lives in the vocabulary table, beside every other sentence
keyed on `meta["lang"]`, and this module is the one place it becomes a
pair of functions. A recorder whose captures are TYPED rather than
rendered -- Python's -- names no dialect at all: no Python trace carries a
`dbg` capture, so the pair such a trace would hand out is never used.
`RUST` is the default for a caller that passes none, which keeps every
call written before the second dialect existed reading exactly as it did
(plan P10).
"""
from collections import namedtuple

from sensorium.query.js_inspect import inspect_text, read_inspect
from sensorium.query.rust_debug import debug_text, read_debug
from sensorium.query.vocab import terms

#: `read(text) -> value` and `write(literal) -> text | None`, inverses over
#: the literal domain a command accepts (amendment A11). They travel
#: together because a reader and a writer that disagree about one capture
#: let `flow` report a sighting the predicate at that site then denies.
Dialect = namedtuple("Dialect", "read write")

RUST = Dialect(read_debug, debug_text)
INSPECT = Dialect(read_inspect, inspect_text)
BY_NAME = {"rust": RUST, "inspect": INSPECT}


def for_trace(trace) -> Dialect:
    """The dialect this trace's captures were written in.

    A trace whose vocabulary names none is one whose recorder writes no
    `dbg` capture at all, and Rust's pair is what every caller got before
    this module existed: handing it back keeps a Python trace's answers
    byte-identical while never actually being consulted.
    """
    name = terms(trace).dbg_dialect
    return BY_NAME[name] if name else RUST
