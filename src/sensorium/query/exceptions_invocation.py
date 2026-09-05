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
within one -- the disposition, the site the verdict is about, the verdict's
own words once ids are masked. Nothing else is merged: the block that is
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

A member that is not a Rust trace refuses likewise. Only the Rust driver
writes `meta.invocation`, so an invocation of Python traces cannot exist --
but the refusal is written rather than assumed, because the alternative to
an impossible-case refusal is an impossible-case crash, and the rules below
are the Rust disposition rules and nothing else.
"""
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from sensorium import paths
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from sensorium.query import caps, exceptions_rust, runs_cmd
from sensorium.query.exceptions_group import Shape, group_chains, print_shape
from sensorium.query.fmt import more_note
from sensorium.store.reader import Trace


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
    vary sets are unioned with the others' as they arrive. `trace` and
    `run_id` are that member's, because the block's ids are its ids.
    """
    shape: Shape
    trace: object
    run_id: str
    n: int = 0                                    # chains, over all members
    processes: list = field(default_factory=list)  # run ids, member order


def _processes(n: int) -> str:
    return f"{n} process" if n == 1 else f"{n} processes"


def _member_refusal(run_id: str, trace) -> str | None:
    """Why this member's record cannot be judged, or None.

    Language first: what a non-Rust member is missing is a rule, not a
    record, and the capability sentence would name the wrong repair.
    """
    if trace.lang != "rust":
        return (f"REFUSED: exceptions across an invocation is defined for "
                f"Rust traces; member {run_id} is {trace.lang}")
    refusal = caps.require(trace, "err_flow", "exceptions")
    return f"REFUSED: {refusal} (member {run_id})" if refusal else None


def _merge(members) -> tuple[list[Merged], dict]:
    """`(merged shapes in first-appearance order, summed chain tally)`.

    `members` is `(run_id, trace, index)` in member order. The first member
    to show a key owns the printed block; every later member adds its
    chains to the count, its run id to the processes, and its differences
    to the vary sets -- which is what makes `origins: 7 distinct` mean
    "across this invocation" rather than "in whichever process printed".
    """
    merged: list[Merged] = []
    by_key: dict[tuple, Merged] = {}
    tally: dict[str, int] = {}
    for run_id, trace, idx in members:
        shapes, member_tally = group_chains(trace, idx.chains, idx,
                                            exceptions_rust.classify)
        for tag, n in member_tally.items():
            tally[tag] = tally.get(tag, 0) + n
        for shape in shapes:
            m = by_key.get(shape.key)
            if m is None:
                m = Merged(shape=shape, trace=trace, run_id=run_id)
                by_key[shape.key] = m
                merged.append(m)
            else:
                m.shape.origins |= shape.origins
                m.shape.messages |= shape.messages
                m.shape.details |= shape.details
                m.shape.hops |= shape.hops
            m.n += len(shape.chains)
            m.processes.append(run_id)
    return merged, tally


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
    """Every member's unreachable `?` sites, in member order, each row
    naming the process it came from.

    The cap's continuation hint names a member only when every hidden row
    is that member's; otherwise `sensorium info` takes a run id this list
    cannot supply, and the plain form is the honest one.
    """
    rows, runs = [], []
    for run_id, _trace, idx in members:
        for row in (idx.partial or []):
            rows.append(row)
            runs.append(run_id)
    hidden = set(runs[exceptions_rust.PARTIAL_SHOWN:])
    hint = (f"sensorium info {hidden.pop()}" if len(hidden) == 1
            else "sensorium info")
    exceptions_rust._print_partial(rows, runs, hint)


def _header(members) -> int:
    """The invocation line, the INCOMPLETE members, the partial union and
    the panic sum. Returns how many members recorded at least one chain."""
    with_chains = sum(1 for _r, _t, idx in members if idx.chains)
    n = len(members)
    # The invocation line is `runs`' own, extended with the counts: one
    # spelling of "which cargo command was this", not two.
    print(f"{runs_cmd._header(members[0][1].meta)} -- {_processes(n)}, "
          f"{with_chains} with Err chains, {n - with_chains} with none")
    for run_id, _trace, idx in members:
        if idx.incomplete:
            # Named BEFORE anything about chains: what this process did
            # after its cut is not below, and a reader who met that fact
            # after the answer would have already believed the answer.
            print(f"INCOMPLETE: {run_id} never finalized -- its Err chains "
                  "after the cut are not below")
    _print_partial(members)
    exceptions_rust._print_panics(sum(idx.panics for _r, _t, idx in members))
    return with_chains


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
        refusal = _member_refusal(run_id, trace)
        if refusal:
            # Before any classification, and the whole answer: a merged
            # count is only as honest as its least honest member.
            print(refusal)
            return UNSETTLED
    indexed = [(run_id, t, exceptions_rust.Index(t)) for run_id, t in opened]
    with_chains = _header(indexed)
    incomplete = any(idx.incomplete for _r, _t, idx in indexed)
    if not with_chains:
        # `caps.none_status`, applied to a set: "none" only where every
        # recording is whole. One member that stopped mid-flight makes the
        # invocation's silence a gap rather than an answer.
        print(f"no exceptions recorded across {_processes(len(indexed))}")
        return UNSETTLED if incomplete else NEGATIVE

    merged, tally = _merge(indexed)
    chains = sum(m.n for m in merged)
    sites = sum(1 for m in merged if m.shape.tag == "swallowed")
    print(f"raised ({chains} chains over {_processes(with_chains)}, "
          f"{sites} swallowing sites):")
    shown = 0
    for m in merged:
        if shown >= args.limit:
            break
        print_shape(m.trace, m.shape, bracket(m))
        shown += 1
    print("dispositions: " + ", ".join(f"{t} {tally[t]}"
                                       for t in exceptions_rust.TAG_ORDER
                                       if tally.get(t)))
    # Paging raises the limit, as in single-run mode, and the ref carried
    # through is the INVOCATION's: a continuation that named one member
    # would answer a smaller question than the one asked.
    note = more_note(len(merged), shown,
                     f"sensorium exceptions {shlex.quote(invocation_id)} "
                     f"--limit {len(merged)}")
    if note:
        print(note)
    return ANSWERED
