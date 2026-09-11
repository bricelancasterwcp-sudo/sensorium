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
The key is the language's (`Renderer.key`): Rust's is `(tag, site, masked
verdict, route)` and TypeScript's `(tag, reason, site, origin site)`, which
reads no sentence at all (§3.1, and `_typescript_key` for what the prose
key cost). The SITE is in both, and it is the one the verdict is ABOUT --
the sink for a swallow, the arm for an escaped `Err`, and the unit's ORIGIN
for every verdict that names no site -- and it comes from the classifier
(`Disposition.site`), never from parsing the sentence back out of itself.

A site is `(file, line, qualname)`, not the `qualname L<line>` a verdict
PRINTS (ruling R-G12, 2026-09-05). The first rung-4 measurement keyed on the
printed text and the E6⁗ workspace had two `sandbox` helpers at L42 in
different test files, and two `fresh_dir`s at L64: 21 chains were booked
under a sibling file, with every count conserved, and one file vanished from
the answer entirely. Where the SAME answer prints two shapes whose site text
collides, each of their verdicts names its file -- `(sandbox L42 in
task_exec_run_test.rs)` -- and where nothing collides, which is every corpus
case and every answer a reader has already read, the notation does not move
at all.

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

# Both rule modules import this one INSIDE `run` (the house idiom of
# `exceptions_cmd`), so both are safe to take at module level here: `_at`
# names a site the way every verdict in those modules does, and
# `_hops_line` is the block's own last line. Rendering either a second time
# here would be two spellings of one journey.
from sensorium.query import exceptions_rust, exceptions_typescript
from sensorium.query.fmt import fmt_event, fmt_exc

#: An event or frame reference in printed text. Anchored on word boundaries
#: so `e412` masks and `kind: NotFound` does not, and guarded against the
#: Rust FLOAT TYPE NAMES (ruling R-G8): `f32`/`f64` are spellings a panic
#: message or an error text carries -- *"expected f64, found f32"* -- and
#: masking them to `f#` merged two verdicts that name different types.
#: Keying on the classifier's own components instead of on masked prose is
#: the better answer, and rung 3 took it for TypeScript
#: (`_typescript_key`), where this guard had split one sink three ways.
#: Rust's key is still prose and still has to live with both halves of the
#: trade (design R3).
MASK = re.compile(r"\b(?!f(?:16|32|64|128)\b)([ef])\d+\b")

#: How many ids a bracket names before it says only how many more there
#: are. A group of 303 is a fact about a site, not a list to read.
MAX_IDS = 8


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


@dataclass(frozen=True)
class Renderer:
    """The seven things this module has to ask a UNIT, in one row per
    language (design P5).

    The grouping GRAIN is not Rust's and never was -- two verdicts about
    one place that say the same thing are one shape in any language. What
    IS each language's own is how a place and a journey are SPELLED, and
    -- since rung 3 -- what "the same thing" is decided on: Rust compares
    its verdicts' masked prose, TypeScript the classifier's own components
    (§3.1). Every one of those spellings already exists in that language's
    rules module beside the verdicts that use it. Passing the functions
    rather than re-deriving them here is what keeps the text the grouper
    compares identical to the text the verdict prints: a second renderer
    would be a second place for a site to be named, and the first thing
    that drifts is the key.

    `tag_order` rides along because the mode that groups a whole invocation
    prints a tally, and its order is the members' language's (§4.3).

    The fields are TRANSPOSABLE -- six callables in a row -- so both rows
    below are built with keywords: a positional list whose site and whose
    site text swapped would type-check, run, and key every shape on the
    wrong spelling (rung-2 review).
    """
    at: object                  # (trace, event) -> `qualname L<line>`
    hops_line: object           # (trace, unit) -> the route line, or None
    site: object                # (trace, event) -> (file, line, qualname)
    site_text: object           # (site) -> `qualname L<line>`
    site_file: object           # (site) -> the basename
    tag_order: tuple            # the dispositions, in printing order
    key: object                 # (trace, unit, d, site, hops) -> the key


def _rust_key(trace, unit, d, site, hops):
    """`(tag, site, masked verdict, route)` -- today's tuple, verbatim.

    Rust keeps the prose key (design R3, decision P6). Its answers are
    quoted by two acceptance records, by nineteen fenced tests and by every
    Rust corpus case, and the component key is a rung-3 TypeScript change:
    moving Rust to it would move bytes this slice promised not to.
    `tests/test_exceptions_typescript_grouping.py` states this very tuple
    as an equality, so a rewrite here fails a test rather than a record.

    R-G2: the ROUTE is part of the key exactly where the verdict names no
    site of its own -- there the chain's journey is the information the
    reader came for, and `None` (no hops line at all) is a route like any
    other. Where the verdict DOES name a site, the route stays out and a
    difference is flagged instead.
    """
    return (d.tag, site, mask(d.verdict), hops if d.site is None else None)


def _typescript_key(trace, unit, d, site, hops):
    """`(disposition, reason, site, origin site)` -- the classifier's own
    parts, and no sentence at all (§3.1).

    The prose key split ONE place three ways on the rung-2 lens: three
    throws absorbed by one `catch` in `useAiAssist`, whose verdicts differ
    only in the frame id they name, and `f32` and `f128` are two of the
    four ids `mask` leaves alone because Rust spells its float types that
    way (R-G8). Nothing here is read back out of a sentence, so no guard
    of the mask's can reach the grain again.

    Four components for TypeScript too, so one dict holds every shape
    without a branch at the lookup -- but not the same four. The REASON
    joins, because two ambiguities at one site that say no more for
    different reasons are two facts: a handler that let a rendering out is
    not a handler nobody traced. The route does not, and `hops` is unread
    here: the ORIGIN's site is the fourth component for every disposition,
    which is what the route was carrying for a verdict that names no site
    of its own.
    """
    return (d.tag, d.reason, site,
            exceptions_typescript._site(trace, unit.origin))


RUST = Renderer(at=exceptions_rust._at,
                hops_line=exceptions_rust._hops_line,
                site=exceptions_rust._site,
                site_text=exceptions_rust.site_text,
                site_file=exceptions_rust.site_file,
                tag_order=exceptions_rust.TAG_ORDER,
                key=_rust_key)

TYPESCRIPT = Renderer(at=exceptions_typescript._at,
                      hops_line=exceptions_typescript._hops_line,
                      site=exceptions_typescript._site,
                      site_text=exceptions_typescript.site_text,
                      site_file=exceptions_typescript.site_file,
                      tag_order=exceptions_typescript.TAG_ORDER,
                      key=_typescript_key)


@dataclass
class Shape:
    """One printed block: the first chain of a group, and the group."""
    key: tuple                  # the renderer's own components (`Renderer`)
    tag: str
    first: object               # the first Chain of the shape, origin order
    disposition: object         # ITS Disposition -- the one printed
    #: The site this shape is keyed on, `(file, line, qualname)`.
    #:
    #: Handed in by `group_units`, which passes the very same local to the
    #: key function -- so a shape whose site and whose key disagree cannot
    #: be built, which is what reading it out of `key[1]` used to
    #: guarantee. Reading it out is no longer possible: the key's SHAPE is
    #: the language's since rung 3, and TypeScript's second component is
    #: the reason, not a place. Where it is not given it still IS `key[1]`,
    #: which is Rust's own key and every `Shape` a test builds by hand.
    site: tuple | None = None
    #: The language that produced these units, so every printer below
    #: reaches the right spelling from the shape it is handed rather than
    #: from a parameter each caller would have to keep passing.
    render: Renderer = RUST
    chains: list = field(default_factory=list)
    origins: set = field(default_factory=set)    # origin SITES, `q L<line>`
    messages: set = field(default_factory=set)   # the origin errors' text
    details: set = field(default_factory=set)    # masked details (None ok)
    hops: set = field(default_factory=set)       # masked routes (None ok)
    #: The FIRST member's detail and route, so a vary line can say whether
    #: the block above it actually shows one of the things it counts.
    first_detail: str | None = None
    first_route: str | None = None

    def __post_init__(self) -> None:
        if self.site is None:
            self.site = self.key[1]


def _message(event) -> str:
    """The origin error as the head line renders it: `type('msg')`. Every
    chain event carries an `exc` (the index selects on `exc.kind == "err"`),
    and this is the same `fmt_exc` call `fmt_event` makes for a RAISE or a
    HANDLED, so the set counts exactly what a reader sees."""
    exc = (event.payload or {}).get("exc")
    return fmt_exc(exc) if exc else "?"


def site_of(trace, unit, d, render: Renderer = RUST) -> tuple:
    """The site the verdict is ABOUT, as `(file, line, qualname)`.

    The classifier names it where the sentence does (the sink, the arm, the
    escaped handler); everywhere else the verdict speaks of the unit rather
    than of a place, and its ORIGIN is the site a reader would group it by
    -- read here as the same triple, so both kinds of key hold the same
    kind of thing.
    """
    return d.site if d.site is not None else render.site(trace, unit.origin)


def collisions(shapes) -> set:
    """The keys of the shapes whose printed site text names more than one
    PLACE in this answer.

    PLACES, not shapes. One site can wear several shapes without being
    ambiguous at all -- two sinks on one line (`sink_ok` and
    `sink_unwrap_or` at `load L31`), or a swallow and a
    `handled_then_failed` at one place -- and those blocks already tell
    themselves apart by their words. Counting shapes instead of places put
    `in lib.rs` into answers that had nothing to disambiguate, which is the
    byte-identity R-G12 promises to every answer that never collides
    (review fix, 2026-09-05). What is ambiguous is a site TEXT that names
    two different `(file, line, qualname)`s: both blocks say `sandbox L42`
    and a reader cannot tell which sink each accuses.

    The set is computed over the whole answer -- every shape the grouping
    produced, not the page `--limit` will print -- because a block whose
    sentence changed when the limit was raised would be a sentence about
    the page rather than about the run.
    """
    at: dict[str, set] = {}
    for shape in shapes:
        at.setdefault(shape.render.site_text(shape.site),
                      set()).add(shape.site)
    ambiguous = {text for text, places in at.items() if len(places) > 1}
    return {shape.key for shape in shapes
            if shape.render.site_text(shape.site) in ambiguous}


def group_units(trace, units, idx, classify, render: Renderer):
    """`(shapes, tally, reasons)` -- shapes in order of FIRST APPEARANCE,
    which is origin order because `units` is; the tally counts UNITS by
    disposition and `reasons` counts the ambiguities by reason.

    A UNIT is whatever the language's rules judge one at a time: a Rust
    `Err` chain, a TypeScript RAISE. All this needs of one is an `origin`
    event, and all it needs of the language is `render` -- so the rule that
    two verdicts about one place with the same words are one block is
    stated once and holds for both.

    The KEY is the renderer's (`Renderer.key`): Rust's masked prose, or
    TypeScript's classifier components. Four components either way, so one
    dict holds every shape without a branch at the lookup. `lang` is
    deliberately NOT in it: a member set is one language
    (`exceptions_invocation` refuses a mixed one), so two languages' keys
    are never in one dict to collide.

    The tally is deliberately not a count of shapes: every record this tool
    has produced reports dispositions per unit, and a tally that started
    counting sites would stop being comparable with any of them (N5).

    Both tallies are counted HERE and printed by the callers (P7): this is
    the one pass that classifies every unit, and a caller that classified
    them a second time to count them would be a second judgement of the
    same record -- which is what rung 3's first cut shipped as an interim
    and this replaces.
    """
    shapes: list[Shape] = []
    by_key: dict[tuple, Shape] = {}
    tally: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for unit in units:
        d = classify(trace, unit, idx)
        tally[d.tag] = tally.get(d.tag, 0) + 1
        # By the REASON, not by the tag: a Rust ambiguity carries none (the
        # field is TypeScript's, §2.3), and counting tags here would grow a
        # line in a Rust answer two acceptance records quote. That every
        # TypeScript ambiguity HAS one is enforced at the source instead,
        # by the reason-table test that walks `exceptions_typescript` for a
        # verdict built without it -- a count cannot enforce it here
        # without accusing the other language of a defect.
        if d.reason is not None:
            reasons[d.reason] = reasons.get(d.reason, 0) + 1
        hops = _masked(render.hops_line(trace, unit))
        site = site_of(trace, unit, d, render)
        key = render.key(trace, unit, d, site, hops)
        shape = by_key.get(key)
        if shape is None:
            shape = Shape(key=key, tag=d.tag, first=unit, disposition=d,
                          site=site, render=render, first_detail=d.detail,
                          first_route=hops)
            by_key[key] = shape
            shapes.append(shape)
        shape.chains.append(unit)
        # R-G6: two sets, not one masked head line. A head carries the site
        # AND the error's text, so counting heads reported two errors from
        # ONE site as two origins -- `corpus/rust/err_stored`'s retry loop
        # raises twice at `attempt L14` with `Refused(1)` and `Refused(2)`,
        # which is one origin and two messages. Neither is masked: a site
        # and an error's rendering carry no ids this tool assigned.
        shape.origins.add(render.at(trace, unit.origin))
        shape.messages.add(_message(unit.origin))
        shape.details.add(_masked(d.detail))
        shape.hops.add(hops)
    return shapes, tally, reasons


def group_chains(trace, chains, idx, classify):
    """`group_units` over Rust `Err` chains, as `(shapes, tally)` -- the
    name AND the arity every Rust caller and every Rust test already
    types, kept so this generalisation moved no byte of the answer they
    pin. A Rust disposition carries no reason, so the third value is always
    empty and dropping it here loses nothing (P5)."""
    shapes, tally, _reasons = group_units(trace, chains, idx, classify, RUST)
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


def _disambiguated(verdict: str, shape: Shape) -> str:
    """The verdict with the file added to the site it names:
    `(sandbox L42)` -> `(sandbox L42 in task_exec_run_test.rs)`.

    A substitution rather than a rewrite, and only of the FIRST occurrence:
    the sentence goes on being a sentence about the block's own named
    chain, with one more fact in the parenthetical it already had. A verdict
    that names no site of its own carries no such parenthetical, and then
    nothing is substituted -- the block keeps today's words, because there
    is no place in it to put the file that would still be true.

    Anchored on ` at e<id> (` -- the SITE EVENT's own id, which is what
    makes that parenthetical the site's. Every verdict that names a place
    spells it that way (`absorbed by <how> at e5 (...)`, `an Err(..) arm at
    e11 (...)`), and an unanchored match would fire on the first
    parenthetical that happened to read the same way and put the file in a
    clause it is not true of (review fix, 2026-09-05).
    """
    text = shape.render.site_text(shape.site)
    at_site = re.compile(r"( at e\d+ \()" + re.escape(text) + r"(\))")
    named = f"{text} in {shape.render.site_file(shape.site)}"
    # A function replacement, not a template: a file name is data and a
    # backslash in one would be read as a group reference by `re.sub`.
    return at_site.sub(lambda m: m.group(1) + named + m.group(2), verdict,
                       count=1)


def print_shape(trace, shape: Shape, bracket_text: str | None = None,
                disambiguate: bool = False) -> None:
    """One shape's block: the first member's chain, printed exactly as a
    lone chain would be, plus the bracket naming the group.

    `bracket_text` is passed by INVOCATION mode (`exceptions_invocation`),
    whose bracket names processes rather than sibling event ids -- an id
    list would name events of traces the reader did not ask about. The
    block itself is the same one in both modes, printed here and nowhere
    else: two renderers of one block are two places for the sentences to
    drift apart.

    `disambiguate` is set by the caller for a shape whose site text is not
    unique in this answer (`collisions`), and adds the file's basename to
    the verdict's parenthetical. It is off by default and off for every
    answer with nothing to tell apart, which is why the corpus, the vectors
    and every block a reader has already read print the same bytes as
    before (R-G12).
    """
    chain, d = shape.first, shape.disposition
    text = bracket(shape) if bracket_text is None else bracket_text
    verdict = _disambiguated(d.verdict, shape) if disambiguate else d.verdict
    print("  " + fmt_event(trace, chain.origin))
    print("    " + verdict + text)
    if d.detail:
        print("      " + d.detail)
    hops = shape.render.hops_line(trace, chain)
    if hops:
        print("      " + hops)
    for line in vary_lines(shape):
        print("      " + line)


def print_shapes(trace, shapes, limit: int) -> int:
    """Print up to `limit` shapes; return how many were printed.

    `limit` counts SHAPES (N5): a page that clipped chains would show part
    of a group and name it `×52`, which is a printed block contradicting
    its own bracket.

    The collision set is computed over every shape of the answer before the
    first block is printed, so which blocks name their file does not depend
    on how many of them fit.
    """
    colliding = collisions(shapes)
    shown = 0
    for shape in shapes:
        if shown >= limit:
            break
        print_shape(trace, shape, disambiguate=shape.key in colliding)
        shown += 1
    return shown
