"""One `exceptions` block per SHAPE on a Rust trace (design N3-N5).

WHY THE GRAIN MOVED
-------------------
`exceptions` printed one block per CHAIN, and on real work that is the
wrong unit. In the E6'''' workspace record the busiest process printed 54
blocks, 52 of them about ONE sink (`http.rs:236`), and the adjudicator who
had to read 782 such lines built a 91-row per-site table BY HAND before any
of it could be answered. That table is the grain the question is asked at,
so the tool prints it: two chains that earned the same disposition at the
same site, with the same words once their ids are masked, are one shape.

WHAT A GROUP IS KEYED ON, AND WHAT IT DELIBERATELY IS NOT
---------------------------------------------------------
The key is `(tag, site, masked verdict, route)`. The SITE is the one the
verdict is ABOUT -- the sink for a swallow, the arm for an escaped `Err`,
and the chain's ORIGIN for every verdict that names no site -- and it comes
from the classifier (`Disposition.site`), never from parsing the sentence back
out of itself.

The head and the detail are NOT in the key. Neither is the ROUTE, for a
verdict that names a site: keying a sink on the path would split it into as
many rows as there are ways to reach it, which is precisely the split the
hand-built table had to undo. But where the verdict names NO site -- where
the fallback site is the chain's own origin -- the route JOINS the key
(ruling R-G2, 2026-09-05), because there the recorded journey is what the
question is about: `corpus/rust/macro_arg_partial` pins a chain whose
MISSING hop is the visible consequence of a declared instrumentation gap,
and `outcome_generic` pins one recorded route against one that stops at a
signature. Merging those would have deleted the answer.

A group whose members differ in something the key did not look at is
FLAGGED rather than silently merged -- one extra line per differing set,
in the order `origins:` / `messages:` / `details vary` / `routes:`. Each
names how many distinct ones there are and where the reader can see one:
`(first shown)`, or `(this one has none)` where the printed member has no
such line (ruling R-G5) -- a flag must not point at a line that is not
there. `origins` counts SITES and `messages` the errors' rendered text
(ruling R-G6): one head line carries both, so counting heads called two
errors raised at one site "2 distinct origins". The route's line is spelled
`routes:` and not `hops:` (ruling R-G3): the corpus caught the first
spelling sharing its prefix with the real `hops:` line, where it
double-counted under every counter.

Ids are masked (`e412` -> `e#`, `f204` -> `f#`) everywhere a set is
compared: two chains absorbed by the same `.ok()` differ in every id they
carry, and a comparison that saw those differences would report every
group as varying and say nothing.

WHAT IS PRINTED, AND WHY IT IS STILL TRUE
-----------------------------------------
A group of N > 1 prints the FIRST member's block exactly as a lone chain
would be printed -- its head, its verdict with its own ids, its detail, its
hops -- and appends a bracket naming the group. Every printed sentence
therefore remains true of a NAMED chain; the bracket adds one fact (how
many, and which) rather than rewriting the sentence into a claim about all
of them, which would need a rewrite rule per verdict and could misstate a
member (design N4, amended before implementation).

The bracket lists each member's ORIGIN event id: the id on the head line
above it, the id `--after` filters on, and the id `grep`/`tree` take. Its
first entry is always the head's own id, so a reader can see at a glance
which member the block's sentences are about.
"""
import re
from dataclasses import dataclass, field

# `exceptions_rust` imports this module INSIDE `run` (the house idiom of
# `exceptions_cmd`), so these two are safe to take at module level: `_at`
# names a site the way every verdict in that module does, and `_hops_line`
# is the block's own last line. Rendering them a second time here would be
# two spellings of one journey.
from sensorium.query.exceptions_rust import _at, _hops_line
from sensorium.query.fmt import fmt_event, fmt_exc

#: An event or frame reference in printed text. Anchored on word boundaries
#: so `e412` masks and `kind: NotFound` does not, and guarded against the
#: Rust FLOAT TYPE NAMES (ruling R-G8): `f32`/`f64` are spellings a panic
#: message or an error text carries -- *"expected f64, found f32"* -- and
#: masking them to `f#` merged two verdicts that name different types.
#: Keying on the classifier's own components instead of on masked prose is
#: the better answer and is CARRIED-DEBT, not this slice.
MASK = re.compile(r"\b(?!f(?:16|32|64|128)\b)([ef])\d+\b")

#: How many ids a bracket names before it says only how many more there
#: are. A group of 303 is a fact about a site, not a list to read.
MAX_IDS = 8


@dataclass
class Shape:
    """One printed block: the first chain of a group, and the group."""
    key: tuple                  # (tag, site, masked verdict, route)
    tag: str
    first: object               # the first Chain of the shape, origin order
    disposition: object         # ITS Disposition -- the one printed
    chains: list = field(default_factory=list)
    origins: set = field(default_factory=set)    # origin SITES, `q L<line>`
    messages: set = field(default_factory=set)   # the origin errors' text
    details: set = field(default_factory=set)    # masked details (None ok)
    hops: set = field(default_factory=set)       # masked routes (None ok)
    #: The FIRST member's detail and route, so a vary line can say whether
    #: the block above it actually shows one of the things it counts.
    first_detail: str | None = None
    first_route: str | None = None


def mask(text: str) -> str:
    """`e412` -> `e#`, `f204` -> `f#`, in printed text only. `f64` and its
    three siblings are type names, not frames, and are left alone."""
    return MASK.sub(r"\1#", text)


def _masked(text: str | None) -> str | None:
    """A line that may not exist. `None` is a member of these sets: a chain
    of one event has no hops line and a verdict may carry no detail, and
    collapsing that to `""` would make "some members have hops and some do
    not" read as "they all agree"."""
    return None if text is None else mask(text)


def _message(event) -> str:
    """The origin error as the head line renders it: `type('msg')`. Every
    chain event carries an `exc` (the index selects on `exc.kind == "err"`),
    and this is the same `fmt_exc` call `fmt_event` makes for a RAISE or a
    HANDLED, so the set counts exactly what a reader sees."""
    exc = (event.payload or {}).get("exc")
    return fmt_exc(exc) if exc else "?"


def site_of(trace, chain, d) -> str:
    """The site the verdict is ABOUT.

    The classifier names it where the sentence does (the sink, the arm);
    everywhere else the verdict speaks of the chain rather than of a place,
    and the chain's ORIGIN is the site a reader would group it by.
    """
    return d.site if d.site is not None else _at(trace, chain.origin)


def group_chains(trace, chains, idx, classify):
    """`(shapes, tally)` -- shapes in order of FIRST APPEARANCE, which is
    origin order because `chains` is; the tally counts CHAINS.

    The key is `(tag, site, masked verdict, route)`, where `route` is the
    masked hops line for a verdict that names no site and `None` for one
    that does (R-G2). Four components always, so one dict holds both kinds
    without a branch at the lookup.

    The tally is deliberately not a count of shapes: every record this tool
    has produced reports dispositions per chain, and a tally that started
    counting sites would stop being comparable with any of them (N5).
    """
    shapes: list[Shape] = []
    by_key: dict[tuple, Shape] = {}
    tally: dict[str, int] = {}
    for chain in chains:
        d = classify(trace, chain, idx)
        tally[d.tag] = tally.get(d.tag, 0) + 1
        hops = _masked(_hops_line(trace, chain))
        # R-G2: the ROUTE is part of the key exactly where the verdict
        # names no site of its own -- there the chain's journey is the
        # information the reader came for, and `None` (no hops line at all)
        # is a route like any other. Where the verdict DOES name a site,
        # the route stays out and a difference is flagged instead.
        key = (d.tag, site_of(trace, chain, d), mask(d.verdict),
               hops if d.site is None else None)
        shape = by_key.get(key)
        if shape is None:
            shape = Shape(key=key, tag=d.tag, first=chain, disposition=d,
                          first_detail=d.detail, first_route=hops)
            by_key[key] = shape
            shapes.append(shape)
        shape.chains.append(chain)
        # R-G6: two sets, not one masked head line. A head carries the site
        # AND the error's text, so counting heads reported two errors from
        # ONE site as two origins -- `corpus/rust/err_stored`'s retry loop
        # raises twice at `attempt L14` with `Refused(1)` and `Refused(2)`,
        # which is one origin and two messages. Neither is masked: a site
        # and an error's rendering carry no ids this tool assigned.
        shape.origins.add(_at(trace, chain.origin))
        shape.messages.add(_message(chain.origin))
        shape.details.add(_masked(d.detail))
        shape.hops.add(hops)
    return shapes, tally


def bracket(shape: Shape, max_ids: int = MAX_IDS) -> str:
    """`  [×4: e412, e417, e420, e443]`, or `""` for a group of one.

    Two leading spaces: it is appended to the verdict line, and a verdict
    that ran straight into a bracket would read as part of the sentence.
    """
    n = len(shape.chains)
    if n == 1:
        return ""
    ids = ", ".join(f"e{c.origin.id}" for c in shape.chains[:max_ids])
    more = f", … +{n - max_ids}" if n > max_ids else ""
    return f"  [×{n}: {ids}{more}]"


def _which(present: bool) -> str:
    """`(first shown)` -- unless the printed member has no such line at all,
    in which case saying "first shown" points at nothing (ruling R-G5). A
    flag whose parenthetical is false about the block it sits under is
    worse than no flag."""
    return "first shown" if present else "this one has none"


def vary_lines(shape: Shape) -> list[str]:
    """What the key did not look at and the members do not agree on.

    Only the sets with more than one member speak. A group that varies in
    nothing prints nothing, so these lines mean something when they appear.
    Order: where it came from (site, then error), then what the tool said
    about it (detail), then how it travelled (route).
    """
    lines = []
    if len(shape.origins) > 1:
        lines.append(f"origins: {len(shape.origins)} distinct (first shown)")
    if len(shape.messages) > 1:
        lines.append(f"messages: {len(shape.messages)} distinct "
                     "(first shown)")
    if len(shape.details) > 1:
        lines.append(f"details vary ({len(shape.details)} distinct; "
                     f"{_which(shape.first_detail is not None)})")
    if len(shape.hops) > 1:
        lines.append(f"routes: {len(shape.hops)} distinct "
                     f"({_which(shape.first_route is not None)})")
    return lines


def print_shape(trace, shape: Shape, bracket_text: str | None = None) -> None:
    """One shape's block: the first member's chain, printed exactly as a
    lone chain would be, plus the bracket naming the group.

    `bracket_text` is passed by INVOCATION mode (`exceptions_invocation`),
    whose bracket names processes rather than sibling event ids -- an id
    list would name events of traces the reader did not ask about. The
    block itself is the same one in both modes, printed here and nowhere
    else: two renderers of one block are two places for the sentences to
    drift apart.
    """
    chain, d = shape.first, shape.disposition
    text = bracket(shape) if bracket_text is None else bracket_text
    print("  " + fmt_event(trace, chain.origin))
    print("    " + d.verdict + text)
    if d.detail:
        print("      " + d.detail)
    hops = _hops_line(trace, chain)
    if hops:
        print("      " + hops)
    for line in vary_lines(shape):
        print("      " + line)


def print_shapes(trace, shapes, limit: int) -> int:
    """Print up to `limit` shapes; return how many were printed.

    `limit` counts SHAPES (N5): a page that clipped chains would show part
    of a group and name it `×52`, which is a printed block contradicting
    its own bracket.
    """
    shown = 0
    for shape in shapes:
        if shown >= limit:
            break
        print_shape(trace, shape)
        shown += 1
    return shown
