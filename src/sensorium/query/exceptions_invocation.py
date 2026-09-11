"""`exceptions <invocation-id>`: one answer for a whole invocation (N6).

WHY A WHOLE INVOCATION IS A UNIT
--------------------------------
`cargo sensorium test --workspace` writes one trace per PROCESS. The E6''''
record's adjudicator therefore asked this command 144 separate questions and
added the answers up by hand -- 144 headers, 144 tallies, and a per-site
table built with a text editor -- to learn one thing: what became of the
workspace's `Err`s. The question was never about a process. `runs` already
prints the invocation id above the group it names, so that id is the ref
this mode takes: a spelling the reader has already seen, for a unit they
already think in.

WHAT MERGING MEANS HERE, AND WHAT IT REFUSES TO MEAN
----------------------------------------------------
Shapes merge across processes on the SAME key `exceptions_group` uses
within one -- the disposition, the site the verdict is about as
`(file, line, qualname)`, the verdict's own words once ids are masked. The
FILE is in that key because of this mode: within one process two helpers
sharing a qualname and a line are rare, and across 144 they are not. The
first measurement keyed on the printed `qualname L<line>` and merged two
`sandbox L42`s that were in different test files, booking 18 chains under
one of them and printing the other nowhere (ruling R-G12). Where two shapes
of ONE answer still print the same site text, each verdict now names its
file. Nothing else is merged: the block that is
printed is the FIRST member's first chain, rendered by the one renderer
both modes share, so every printed sentence stays true of a NAMED chain in
a NAMED process. The bracket is what changes. Within one trace it lists the
group's sibling event ids; across an invocation those ids belong to traces
the reader did not open, and a list of them would read as one sequence when
it is eleven. So it names the spread and one entry point instead:
`[×303 over 11 processes: first e1204 in 20260905-091125-fc7302, +302]`.

WHAT IS COUNTED ONCE AND WHAT IS COUNTED PER PROCESS
-----------------------------------------------------
The tally is the sum of the members' chain tallies, so it stays comparable
line-for-line with every per-process record already written. The panics are
summed for the same reason. The `partial` rows are the UNION, each row
naming its own process -- a site the reader cannot go and look at is a
fact they cannot use. And every member that never finalized is NAMED above
the answer: an unfinalized process is a gap in the whole, and a header that
counted it as "with none" would report where a recording stopped as
something a program did.

WHAT THIS MODE REFUSES
----------------------
`--after` takes an event id, and an event id belongs to one process; ids
from 144 processes are not one sequence to resume in. Paging here raises
`--limit`, which counts shapes.

A member whose recorder declares `err_flow: false` refuses the WHOLE
answer, naming it: a merged count that silently dropped one process would
be a number missing an unknown amount of the program, which is worse than
no number.

TWO LANGUAGES, ONE GROUPER
--------------------------
Both drivers write `meta.invocation`: `cargo sensorium test --workspace`
writes one trace per test binary, and `sensorium ts run -- npx vitest run`
one per forked worker. So this mode dispatches PER MEMBER on `meta.lang`
(`LANGUAGES` below) -- the language's index, its rules, its renderer and
its tally order -- and the merge itself is `exceptions_group.group_units`,
which is written about units and sites and knows no language at all.

A member of any OTHER language refuses by name: what it is missing is a
rule, not a record, and the capability sentence would name the wrong
repair. A member set of TWO languages refuses likewise. One invocation is
one driver's, so that set cannot exist -- but the refusal is written rather
than assumed, because the alternative to an impossible-case refusal is an
impossible-case answer, judged by one language's rules over another's
records.
"""
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from sensorium import paths
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from sensorium.query import (caps, exceptions_group, exceptions_rust,
                             exceptions_typescript, runs_cmd)
from sensorium.query.exceptions_group import (Shape, collisions, group_units,
                                              print_shape)
from sensorium.query.fmt import more_note
from sensorium.store.reader import Trace


@dataclass(frozen=True)
class Language:
    """Everything this mode needs to know about a member, in ONE row.

    Four lookup tables keyed on `lang` would be four places to forget when
    a fourth recorder arrives; one row is a thing a reader can check is
    complete. Nothing here is decided by sniffing a key: `meta["lang"]` is
    the whole of the dispatch (R27a), as it is in `runs` and `info`.
    """
    index: object       # (trace) -> that language's Index
    units: object       # (index) -> the units to judge, in origin order
    classify: object    # (trace, unit, index) -> Disposition
    render: object      # `exceptions_group.Renderer`
    #: The noun the `raised (...)` line counts, singular and plural.
    #: Rust's pair is deliberately the SAME word twice: that line has read
    #: `N chains` since it shipped, two acceptance records quote it, and
    #: correcting `1 chains` is a change to a Rust answer that this task --
    #: which promised to move no byte of one -- is not the place for.
    raised: tuple
    #: What a member HAS, and what a member's cut therefore hides.
    held: str


LANGUAGES = {
    "rust": Language(exceptions_rust.Index, lambda idx: idx.chains,
                     exceptions_rust.classify, exceptions_group.RUST,
                     ("chains", "chains"), "Err chains"),
    "typescript": Language(exceptions_typescript.Index,
                           lambda idx: idx.units,
                           exceptions_typescript.classify,
                           exceptions_group.TYPESCRIPT,
                           ("raise", "raises"), "throws"),
}


class InvocationLookupError(paths.TraceLookupError):
    """A ref that named no trace and no invocation either.

    A subclass of `TraceLookupError` on purpose: `cli.main` already renders
    that one as `error: <sentence>` on stderr with exit 2, which is exactly
    what a ref this command cannot resolve deserves. A second rendering
    would be a second way for one condition to look, and the reader would
    have to learn both.
    """


def resolve_invocation(ref: str) -> tuple[str, list[Path]]:
    """`(invocation id, member paths in file-name order)`.

    Every trace whose `meta.invocation` equals `ref`, or -- when none does
    -- whose invocation uniquely STARTS with it. Exact wins over prefix, so
    an invocation id that happens to prefix another's still answers for
    itself.

    Opens every trace in the store once: the invocation is recorded inside
    each trace and nothing indexes it, which is the honest cost of not
    keeping a second, drift-prone table of what is already in the files.

    Member order is trace file-name order -- the order `runs` prints, and
    the order that decides which member's block is the one printed for a
    merged shape.
    """
    files = sorted(paths.traces_dir().glob("*.db"), key=lambda p: p.name)
    invs = []
    for f in files:
        inv = Trace.open(f).meta.get("invocation")
        invs.append(inv if isinstance(inv, str) else None)
    exact = [f for f, inv in zip(files, invs) if inv == ref]
    if exact:
        return ref, exact
    ids = sorted({inv for inv in invs if inv and inv.startswith(ref)})
    if len(ids) > 1:
        # Answering for either would be a guess about which question was
        # asked; the ids are named so the next call can pick one.
        raise InvocationLookupError(f"{ref!r} is ambiguous: "
                                    + ", ".join(ids))
    if not ids:
        # Both namespaces were looked in, and the sentence says so: a
        # reader told only "no trace matches" would not know an invocation
        # id was also tried.
        raise InvocationLookupError(f"no trace or invocation matches {ref!r}")
    return ids[0], [f for f, inv in zip(files, invs) if inv == ids[0]]


@dataclass
class Merged:
    """One shape, seen across an invocation.

    `shape` is the FIRST member's -- the block that is printed, and whose
    vary sets and CHAINS are unioned with the others' as they arrive, so a
    merged shape is internally consistent: `len(shape.chains)` is the count
    the bracket prints. `trace` and `run_id` are the first member's,
    because the block's ids are its ids.

    Its `chains` therefore span traces, and `exceptions_group.bracket` must
    never be called on one: that bracket LISTS event ids, and ids from
    different processes are not one sequence. `bracket(merged)` below is
    this mode's, and it names processes instead.
    """
    shape: Shape
    trace: object
    run_id: str
    processes: list = field(default_factory=list)  # run ids, member order

    @property
    def n(self) -> int:
        """Chains, over every member: the shape's own list, so there is no
        second count here to drift away from it."""
        return len(self.shape.chains)


def _processes(n: int) -> str:
    return f"{n} process" if n == 1 else f"{n} processes"


def _units(n: int, words: tuple) -> str:
    """`2 raises` / `1 raise` -- what the `raised (...)` line counts, in the
    members' own language's noun. A count that reads `1 raises` is the tell
    that a number was printed by a template rather than said by anyone."""
    return f"{n} {words[0] if n == 1 else words[1]}"


def _shapes(n: int) -> str:
    """What the header counts, in the noun that says what it is.

    It read `N swallowing sites`, and N is the number of printed BLOCKS --
    merged shapes whose disposition is swallowed. The two are not equal on
    a real sweep: the E6″′ record has 91 and 98 distinct sites where
    this header printed 103 and 105, and R-G12 widened that gap by making
    the addressing right. The phrase was frozen through both measurements
    deliberately and is free to correct now. `shape` is this command's own
    word for a merged block, printed already by the continuation note. It
    also said `sites` at N=1.
    """
    return f"{n} swallowed shape" if n == 1 else f"{n} swallowed shapes"


def _member_refusal(run_id: str, trace, head) -> str | None:
    """Why this member's record cannot be judged, or None. `head` is the
    `(run id, trace)` of the FIRST member, which the set is one of.

    Language first: what a member of an unruled language is missing is a
    rule, not a record, and the capability sentence would name the wrong
    repair. Then the SET's own coherence, before anything any one member
    declares: a mixed set is not a member's problem to report.
    """
    if trace.lang not in LANGUAGES:
        return (f"REFUSED: exceptions across an invocation is defined for "
                f"Rust and TypeScript traces; member {run_id} is "
                f"{trace.lang}, which is not ruled")
    if trace.lang != head[1].lang:
        # `runs` groups one invocation and one driver writes it, so this
        # cannot happen -- and if it ever did, judging it would mean
        # reading one language's records by another language's rules.
        return (f"REFUSED: an invocation is one driver's; member {run_id} "
                f"is {trace.lang} and {head[0]} is {head[1].lang}")
    refusal = caps.require(trace, "err_flow", "exceptions")
    return f"REFUSED: {refusal} (member {run_id})" if refusal else None


def _merge(members, lang: Language) -> tuple[list[Merged], dict, dict]:
    """`(merged shapes in first-appearance order, summed unit tally, summed
    reason tally)`.

    `members` is `(run_id, trace, index)` in member order. The first member
    to show a key owns the printed block; every later member adds its
    units to the count, its run id to the processes, and its differences
    to the vary sets -- which is what makes `origins: 7 distinct` mean
    "across this invocation" rather than "in whichever process printed".

    One key space, because the set is ONE language: `Shape.key` carries no
    `lang`, and it does not need to.

    The reasons are summed exactly as the dispositions are, and for the
    same reason: an adjudicator asking what this invocation could not
    settle wants ONE number per reason, not 144 of them to add up. A Rust
    member contributes nothing to it -- the field is TypeScript's -- so a
    Rust answer grows no line.
    """
    merged: list[Merged] = []
    by_key: dict[tuple, Merged] = {}
    tally: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for run_id, trace, idx in members:
        shapes, member_tally, member_reasons = group_units(
            trace, lang.units(idx), idx, lang.classify, lang.render)
        for tag, n in member_tally.items():
            tally[tag] = tally.get(tag, 0) + n
        for reason, n in member_reasons.items():
            reasons[reason] = reasons.get(reason, 0) + n
        for shape in shapes:
            m = by_key.get(shape.key)
            if m is None:
                m = Merged(shape=shape, trace=trace, run_id=run_id)
                by_key[shape.key] = m
                merged.append(m)
            else:
                m.shape.chains.extend(shape.chains)
                m.shape.origins |= shape.origins
                m.shape.messages |= shape.messages
                m.shape.details |= shape.details
                m.shape.hops |= shape.hops
            m.processes.append(run_id)
    return merged, tally, reasons


def bracket(m: Merged) -> str:
    """`  [×303 over 11 processes: first e1204 in <run-id>, +302]`.

    No id list: the members' origin ids belong to eleven different traces,
    and printing them together would read as one sequence a reader could
    page through. What is named instead is where to START -- the process
    and the id of the block printed above -- and how many more there are.

    A shape seen once still names its process. Within one trace a group of
    one needs no bracket, because the process is the ref the reader typed;
    here it is one of many, and a block that did not say which would be an
    accusation nobody could go and check.
    """
    if m.n == 1:
        return f"  [in {m.run_id}]"
    return (f"  [×{m.n} over {_processes(len(m.processes))}: first "
            f"e{m.shape.first.origin.id} in {m.run_id}, +{m.n - 1}]")


def _print_partial(members) -> None:
    """The DISTINCT unreachable `?` sites across the invocation, in
    first-appearance order, each row saying where it was seen.

    A union, not a concatenation (ruling R-G10). `meta.partial` holds, per
    process, the sites of every unit that process LINKED, so in a workspace
    each shared crate's unreachable sites are repeated in every trace that
    links it: concatenating 144 members announced `partial: 432 ?-sites`
    for 3 distinct ones, showed 3 rows all from the first member, and hid
    429 copies. The count a reader needs is how many PLACES the recorder
    could not watch.

    Where each site was seen still matters, so a site carried by exactly
    one process names it -- that is the trace to go and read -- and one
    carried by several says how many, rather than listing run ids that
    would outgrow the row.
    """
    rows, seen_at = [], []
    at: dict[tuple, int] = {}
    for run_id, _trace, idx in members:
        for row in (idx.partial or []):
            key = (row.get("qualname"), row.get("file"), row.get("line"),
                   row.get("reason"))
            i = at.get(key)
            if i is None:
                at[key] = len(rows)
                rows.append(row)
                seen_at.append([run_id])
            elif seen_at[i][-1] != run_id:
                seen_at[i].append(run_id)
    wheres = [runs[0] if len(runs) == 1 else _processes(len(runs))
              for runs in seen_at]
    # The hint names the FIRST hidden row's process: it is the one a reader
    # continuing the list opens next, and it is a run id `info` takes.
    hidden = seen_at[exceptions_rust.PARTIAL_SHOWN:]
    hint = f"sensorium info {hidden[0][0]}" if hidden else "sensorium info"
    exceptions_rust._print_partial(rows, wheres, hint)


def _ambient(members, lang: Language) -> None:
    """What the RECORDING was not watching, summed over the members --
    each language's own, and nothing standing in for what a recorder does
    not produce.

    Rust: the union of the `?` sites the transformer could not reach, and
    the panic events. TypeScript: the rejections the process itself
    reported unhandled, which carry no site and so open no block (R1) --
    counted here or counted nowhere, because a merged answer that dropped
    them would be the only place they are said at all.
    """
    if lang is LANGUAGES["rust"]:
        _print_partial(members)
        exceptions_rust._print_panics(
            sum(idx.panics for _r, _t, idx in members))
        return
    rejections = sum(len(idx.rejections) for _r, _t, idx in members)
    if rejections:
        print(f"unhandled rejections: {rejections}")


def _header(members, lang: Language) -> int:
    """The invocation line, the INCOMPLETE members and the ambient counts.
    Returns how many members recorded at least one unit."""
    with_units = sum(1 for _r, _t, idx in members if lang.units(idx))
    n = len(members)
    # The invocation line is `runs`' own, extended with the counts: one
    # spelling of "which command was this", not two. The language travels
    # with the meta because `runs` chooses the header's SHAPE by it and
    # never by sniffing a key (R27a), and passing the trace's own `lang`
    # keeps that a fact about the trace rather than an assumption here.
    head = members[0][1]
    print(f"{runs_cmd._header(head.meta, head.lang)} -- {_processes(n)}, "
          f"{with_units} with {lang.held}, {n - with_units} with none")
    for run_id, _trace, idx in members:
        if idx.incomplete:
            # Named BEFORE anything about units: what this process did
            # after its cut is not below, and a reader who met that fact
            # after the answer would have already believed the answer.
            print(f"INCOMPLETE: {run_id} never finalized -- its {lang.held} "
                  "after the cut are not below")
    _ambient(members, lang)
    return with_units


def run(args, invocation_id: str, members: list) -> int:
    """`exceptions` over one invocation's traces. `exceptions_cmd.run` has
    validated `--limit` and resolved the ref; `--after` is parsed there too
    but refused here, before a single member is opened."""
    if args.after:
        # An event id is minted per process. Resuming after one would mean
        # "after this id in every trace", which is not a place.
        print(f"--after names an event of one process; this answer spans "
              f"{_processes(len(members))} -- page with --limit")
        return BAD_CALL
    opened = [(p.stem, Trace.open(p)) for p in members]
    for run_id, trace in opened:
        refusal = _member_refusal(run_id, trace, opened[0])
        if refusal:
            # Before any classification, and the whole answer: a merged
            # count is only as honest as its least honest member.
            print(refusal)
            return UNSETTLED
    # Every member is this language: the loop above refused the set that
    # was not, so the row can be taken from the first member and used for
    # all of them.
    lang = LANGUAGES[opened[0][1].lang]
    indexed = [(run_id, t, lang.index(t)) for run_id, t in opened]
    with_chains = _header(indexed, lang)
    incomplete = any(idx.incomplete for _r, _t, idx in indexed)
    if not with_chains:
        # `caps.none_status`, applied to a set: "none" only where every
        # recording is whole. One member that stopped mid-flight makes the
        # invocation's silence a gap rather than an answer.
        print(f"no exceptions recorded across {_processes(len(indexed))}")
        return UNSETTLED if incomplete else NEGATIVE

    merged, tally, reasons = _merge(indexed, lang)
    chains = sum(m.n for m in merged)
    shapes = sum(1 for m in merged if m.shape.tag == "swallowed")
    print(f"raised ({_units(chains, lang.raised)} over "
          f"{_processes(with_chains)}, {_shapes(shapes)}):")
    # Over the whole ANSWER, never per member: the collision this mode
    # exists to have caught is between processes -- `sandbox L42` in two
    # test files, one process each -- so a set computed inside a member
    # would be empty in exactly the case that needs it (R-G12).
    colliding = collisions([m.shape for m in merged])
    shown = 0
    for m in merged:
        if shown >= args.limit:
            break
        print_shape(m.trace, m.shape, bracket(m), m.shape.key in colliding)
        shown += 1
    # The members' language's order, which is what the tally is a tally
    # in: no disposition of one recorder appears in another's line.
    print("dispositions: " + ", ".join(f"{t} {tally[t]}"
                                       for t in lang.render.tag_order
                                       if tally.get(t)))
    # §2.3, summed: under the tally it explains, printed once for the whole
    # invocation, and absent where nothing was ambiguous -- the same three
    # rules single-run mode prints it by, spelled a second time here for
    # the same reason the `dispositions:` line above is (P7: the grouper
    # prints blocks; a tally belongs to the mode that summed it).
    # `REASON_ORDER` is TypeScript's table and there is no other: a Rust
    # member contributes no reason at all, so this dict is empty and the
    # line is never reached for one.
    if reasons:
        print("ambiguous by reason: " + ", ".join(
            f"{r} {reasons[r]}"
            for r in exceptions_typescript.REASON_ORDER if reasons.get(r)))
    # Paging raises the limit, as in single-run mode, and the ref carried
    # through is the INVOCATION's: a continuation that named one member
    # would answer a smaller question than the one asked.
    note = more_note(len(merged), shown,
                     f"sensorium exceptions {shlex.quote(invocation_id)} "
                     f"--limit {len(merged)}")
    if note:
        print(note)
    return ANSWERED
