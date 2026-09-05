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
naming how many distinct ones there are and saying that the first is what
is shown. The route's line is spelled `routes:` and not `hops:` (ruling
R-G3): the corpus caught the first spelling sharing its prefix with the
real `hops:` line, where it double-counted under every counter.

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
from sensorium.query.fmt import fmt_event

#: An event or frame reference in printed text. Anchored on word boundaries
#: so `e412` masks and `kind: NotFound` does not.
MASK = re.compile(r"\b([ef])\d+\b")

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
    heads: set = field(default_factory=set)      # masked head lines
    details: set = field(default_factory=set)    # masked details (None ok)
    hops: set = field(default_factory=set)       # masked routes (None ok)


def mask(text: str) -> str:
    """`e412` -> `e#`, `f204` -> `f#`, in printed text only."""
    return MASK.sub(r"\1#", text)


def _masked(text: str | None) -> str | None:
    """A line that may not exist. `None` is a member of these sets: a chain
    of one event has no hops line and a verdict may carry no detail, and
    collapsing that to `""` would make "some members have hops and some do
    not" read as "they all agree"."""
    return None if text is None else mask(text)


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
            shape = Shape(key=key, tag=d.tag, first=chain, disposition=d)
            by_key[key] = shape
            shapes.append(shape)
        shape.chains.append(chain)
        shape.heads.add(mask(fmt_event(trace, chain.origin)))
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


def vary_lines(shape: Shape) -> list[str]:
    """What the key did not look at and the members do not agree on.

    Only the sets with more than one member speak. A group that varies in
    nothing prints nothing, so these lines mean something when they appear.
    """
    lines = []
    if len(shape.heads) > 1:
        lines.append(f"origins: {len(shape.heads)} distinct (first shown)")
    if len(shape.details) > 1:
        lines.append(f"details vary ({len(shape.details)} distinct; "
                     "first shown)")
    if len(shape.hops) > 1:
        lines.append(f"routes: {len(shape.hops)} distinct (first shown)")
    return lines


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
        chain, d = shape.first, shape.disposition
        print("  " + fmt_event(trace, chain.origin))
        print("    " + d.verdict + bracket(shape))
        if d.detail:
            print("      " + d.detail)
        hops = _hops_line(trace, chain)
        if hops:
            print("      " + hops)
        for line in vary_lines(shape):
            print("      " + line)
        shown += 1
    return shown
