"""`exceptions` for `lang = rust`: what became of every `Err` that travelled.

WHY THIS IS A SEPARATE MODULE
-----------------------------
An `Err` is a VALUE being returned, not an exception unwinding, and almost
nothing the Python rules know transfers. `exceptions_cmd.Index` reads
``exc["oid"]`` (Rust has no object identity), it lists RAISE events only (so
an `Err` returned by ``return Err(..)`` and absorbed by a caller's ``.ok()``
would come back as "no exceptions recorded"), and its rule 2 -- "a handler
frame that returned normally swallowed it" -- would report SWALLOWED for
every frame that re-returned an `Err` without ``?``. Each of those is a
confident wrong answer, which is why `exceptions` refused a Rust trace
outright until these rules existed (design R9).

WHAT THIS MODULE DECIDES, AND WHAT IT REFUSES TO
------------------------------------------------
It decides DISPOSITIONS and nothing else. Chain IDENTITY -- which recorded
`Err` continues which, how many frames it crossed, whether the type changed
on the way, whether it was born in instrumented code -- is minted by the
converter's chain machine (`rust/cargo-sensorium/src/convert/chains`, design
§2a) and rides the events as ``chain``; how a chain ENDED rides its LAST
event as ``chain.terminal``. Those are facts about a record stream. This
module reads them and recomputes none of them: two places deriving one
verdict is two places for it to drift, and the converter's own suite is
where the machine is pinned.

``terminal`` is deliberately not spelled in verdict words.
``swallowed_candidate`` says a sink absorbed the chain and its holder frame
then returned ok, which is what a SWALLOWED verdict is made OF. The verdict
is issued here, with the wording that says how much the recording actually
supports.

THE FIVE DISPOSITIONS (design R8)
---------------------------------
``swallowed``  a written sink absorbed the chain and its frame returned ok.
               The only accusation this command makes, and the one E6 gates.
``panicked``   the frame holding the chain unwound. The verdict says that,
               never that the panic happened BECAUSE of the `Err`.
``returned-to-harness``
               the chain left a frame the manifest marks ``test`` or
               ``main`` -- it went back to libtest or out of `fn main`.
``propagated`` still open when the thread ended, on a frame that is neither.
               Only reachable where the thread was still live when the
               recording ended (`live_threads`) or its frames were not all
               instrumented, and the verdict says so -- never "INCOMPLETE",
               which `info` keeps for a recording that never finalized.
``ambiguous``  THE DEFAULT, for everything else and for every terminal these
               rules do not know: a merged window, a bound-and-escaped arm,
               an ok close with no sink, a sink whose frame then failed
               anyway, a chain that left a spawned thread into a
               `JoinHandle`. Nothing reaches SWALLOWED by falling through.

WHERE THE TRACE CANNOT SAY
--------------------------
There is no error identity on the wire, so a chain is followed by
``(holder frame, type, Debug text)``: two `Err`s of one type with identical
text in one window are one chain, and a window holding two DIFFERENT `Err`s
is `merged` -- reported as ambiguous, never as a swallow. A truncated text
is no identity at all and matching falls back to the type alone, which can
only ever merge two chains, never split one.

The shapes the transformer does not probe (``let ... else``,
``while let Err(..)``, ``.err()``, ``matches!``, or-patterns, let-chains,
`.is_err()`/`.is_ok()`) record nothing, so an `Err` they absorb reads
ambiguous -- `rust/HONESTY.md` names them. A `?` site the transformer could
not REACH is worse than unprobed and is reported at the top of the output
from ``meta.partial``: its silence would otherwise read as "nothing
happened there".
"""
import shlex

from sensorium.exit import ANSWERED, UNSETTLED
from sensorium.query import caps
from sensorium.query.exceptions_cmd import Disposition
from sensorium.query.fmt import fmt_exc, more_note

TAG_ORDER = ("swallowed", "panicked", "returned-to-harness", "propagated",
             "ambiguous")

# The literal token `SWALLOWED` is printed by ONE sentence in this module --
# `_swallowed`'s verdict -- and by nothing else, not even by prose saying a
# shape is never one. E6's cross-case collector counts printed SWALLOWED
# lines and compares the set whole (design R15), so a detail line reading
# "never SWALLOWED" would enter that count as a false accusation nobody
# made. Every other mention is spelled "a swallow".

# How many `partial` rows the header names before it starts counting. The
# list is one row per unreachable `?` site across every registered unit --
# order 400 on a real workspace -- and a header that scrolled the answer off
# the screen would be worse than the silence it exists to break.
PARTIAL_SHOWN = 3


class Chain:
    """Every event of one `Err` chain, in trace order.

    Keyed by ``(thread, chain.serial)``: chain serials are minted PER THREAD
    (from ``1 << 32``), so two threads legitimately carry the same number
    and merging them would report two programs' errors as one.
    """

    def __init__(self, key, events):
        self.key = key
        self.events = events

    @property
    def origin(self):
        return self.events[0]

    @property
    def last(self):
        return self.events[-1]

    @property
    def terminal(self):
        """How the chain ended, read off its LAST event and nowhere else.

        Absent is a real answer: a chain the machine never closed carries
        no terminal, and inventing one here would put a verdict in the
        converter's mouth.
        """
        return _chain(self.last).get("terminal")

    @property
    def born_outside(self) -> bool:
        return _chain(self.origin).get("origin") == "outside"

    @property
    def hops(self) -> int:
        """The furthest hop any of this chain's events reached. Read, not
        counted: an event that absorbs a chain without crossing a frame
        carries the hop it happened AT, so `len(events)` is not it."""
        return max((_chain(e).get("hop") or 1) for e in self.events)


def _chain(event) -> dict:
    return ((event.payload or {}).get("chain")) or {}


def _how(event) -> str:
    return (event.payload or {}).get("how") or "?"


def _at(trace, e) -> str:
    q = trace.code(e.code_id).qualname if e.code_id is not None else "?"
    return f"{q} L{e.line}"


class Index:
    """Everything the disposition rules read, gathered in one pass.

    Selection is by ``exc.kind == "err"`` and never by ``type == "panic"``
    (design R7): a workspace error type spelled `panic` is an `Err` like any
    other, and a panic RAISE is not a chain at all. The panics are counted
    rather than dropped -- an answer of "no exceptions recorded" about a run
    that panicked is a false negative.
    """

    def __init__(self, trace):
        self.trace = trace
        meta = trace.meta
        self.incomplete = bool(meta.get("incomplete"))
        self.partial = meta.get("partial")
        self.marks = _marks(meta)
        self.panics = 0
        groups: dict = {}
        for e in trace.events(kind=("RAISE", "HANDLED")):
            exc = (e.payload or {}).get("exc") or {}
            kind = exc.get("kind")
            if kind == "panic":
                self.panics += 1
                continue
            if kind != "err":
                continue
            serial = _chain(e).get("serial")
            # A chain object a converter failed to write leaves the event
            # its own chain of one rather than dropping it: an unreported
            # `Err` is the one outcome this command must never produce.
            key = (e.thread_id, serial) if serial is not None else ("e", e.id)
            groups.setdefault(key, []).append(e)
        self.chains = sorted((Chain(k, v) for k, v in groups.items()),
                             key=lambda c: c.origin.id)

    def frame_of(self, e):
        return (self.trace.frame(e.frame_id)
                if e.frame_id is not None else None)

    def unwound_holder(self, e):
        """The frame that unwound while holding this chain.

        The holder is not on the wire, and it is not always the frame the
        chain's last event fired in -- a chain hops UP when its frame closes
        `err`, and the close is a RETURN, which is no event of the chain's.
        But every frame between the last event's frame and the holder closed
        by RETURNING (that is what `err`/`none`/`ok` are), so the INNERMOST
        frame that unwound, walking outward from the last event's frame, is
        the holder. Derived rather than assumed, and `None` where the walk
        finds nothing -- in which case the verdict quotes no panic.
        """
        f = self.frame_of(e)
        seen = 0
        while f is not None and seen < 512:      # a cycle is a corrupt trace
            if f.closed_by == "unwind" and f.unwind_exc:
                return f
            f = (self.trace.frame(f.parent_id)
                 if f.parent_id is not None else None)
            seen += 1
        return None

    def harness_holder(self, e):
        """The frame a chain that ended at THREAD_END was sitting in, as
        `(frame, mark, still_open)`; `(None, None, False)` where there is no
        frame to name.

        NOT "the innermost MARKED ancestor", which is the fix-round-1 bug:
        a `#[test] fn t()` calling a bin crate's `main()` that re-returns an
        `Err` puts the chain's last event inside `main` -- marked `main` --
        while §2a moved the holder OUT of `main` the moment it closed `err`,
        into `t`. Naming the innermost mark reported the binary's entry
        point for a chain the test harness received.

        The converter's own rule (`chains`, M4) is the one followed here:
        the holder is the frame the chain SITS in whenever that frame is
        still on the stack, and the frame it LEFT once the holder is gone.
        A frame still on the stack at THREAD_END is one with no close
        recorded, so the search is for the innermost ancestor-or-self that
        is still open; with every ancestor closed, the frame it left is the
        last event's own -- which is where an `Err` returned out of a
        `#[test]` fn puts it.

        The mark is then taken from THAT frame and no other. Walking on to
        find a mark is what produced the wrong answer, so an unmarked holder
        earns the no-mark verdict rather than a borrowed claim.
        """
        f = self.frame_of(e)
        holder, seen = None, 0
        while f is not None and seen < 512:
            if f.closed_by is None and f.return_event_id is None:
                holder = f
                break
            f = (self.trace.frame(f.parent_id)
                 if f.parent_id is not None else None)
            seen += 1
        still_open = holder is not None
        if holder is None:
            holder = self.frame_of(e)
        if holder is None:
            return None, None, False
        code = (self.trace.code(holder.code_id)
                if holder.code_id is not None else None)
        mark = self.marks.get((code.qualname, code.file)) if code else None
        return holder, mark, still_open


def _marks(meta) -> dict:
    """`(qualname, absolute file)` -> `"test"` / `"main"`, from `meta.sites`.

    The site table's `file` is workspace-relative and a trace's
    `code_objects.file` is absolute, so the join is a path-segment suffix
    (`"/w/demo/src/lib.rs"` ends with `"/demo/src/lib.rs"`) rather than a
    bare `in`, which would let `oo/src/lib.rs` match `foo/src/lib.rs`. The
    dict is keyed lazily: `Index.marked_holder` asks with the absolute path
    it has, so the lookup is built as a callable-shaped dict of exactly the
    pairs the site table declares -- see `_MarkTable`.
    """
    rows = meta.get("sites") or []
    return _MarkTable([r for r in rows
                       if r.get("kind") in (None, "fn", "closure")
                       and (r.get("test") or r.get("main"))])


class _MarkTable:
    """A lookup whose keys are `(qualname, absolute file)` pairs it has
    never seen: `get` resolves the suffix join on demand. Two rows of one
    qualname that disagree resolve to NO mark rather than to whichever was
    listed first -- a mark this table cannot pin down is one the verdict
    must not claim."""

    def __init__(self, rows):
        self._rows = rows

    def get(self, key, default=None):
        qualname, file = key
        found = {("main" if r.get("main") else "test") for r in self._rows
                 if r.get("qualname") == qualname
                 and _same_file(file, r.get("file") or "")}
        return found.pop() if len(found) == 1 else default


def _same_file(absolute: str, relative: str) -> bool:
    return bool(relative) and (absolute == relative
                               or absolute.endswith("/" + relative))


# -- the disposition table (design R8) --------------------------------------
# The `how` values that ABSORB an `Err` -- the sinks of design R2 plus a
# handling arm. `_absorbed` names the site only for these: a terminal that
# says a chain was absorbed can ride any event a converter chooses to put it
# on, and naming a `?` as the thing that swallowed an `Err` would be this
# command inventing a site from a key it merely happened to read.
ABSORBING_HOWS = ("sink_ok", "sink_unwrap_or", "sink_let_underscore",
                  "arm_handled")


def _absorbed(trace, h) -> str:
    if _how(h) in ABSORBING_HOWS:
        return f"absorbed by {_how(h)} at e{h.id} ({_at(trace, h)})"
    return f"absorbed at e{h.id} ({_at(trace, h)})"


def _swallowed(trace, chain, idx) -> Disposition:
    """The one accusation this command makes, and the whole reason its bar
    is high: a WRITTEN sink absorbed the chain and the frame holding it then
    returned ok. The sink is the chain's last event, so the frame it fired
    in IS the holder (§2a admits an absorb only where the two are one)."""
    h = chain.last
    fid = h.frame_id
    where = f" in f{fid}" if fid is not None else ""
    # R8, amended 2026-09-04 (Task 7's `join_handle`): the chain machine is
    # PER THREAD, so a HANDLED that opens no chain means only that no chain
    # was open ON THIS THREAD -- the `Err` may have been made in dependency
    # code, or in an instrumented frame on another thread and carried across
    # a `JoinHandle`. The wording before the amendment named dependency
    # code outright, and asserted that about both.
    detail = (f"born outside this thread's instrumented frames; absorbed at "
              f"{_how(h)}" if chain.born_outside else None)
    return Disposition(
        "swallowed",
        f"SWALLOWED -- {_absorbed(trace, h)}{where}, which returned ok",
        detail, site=_at(trace, h))


def _panicked(trace, chain, idx) -> Disposition:
    f = idx.unwound_holder(chain.last)
    if f is None:
        return Disposition(
            "panicked", "panicked -- the frame holding it unwound",
            "no unwound frame is recorded on this chain's own frame or any "
            "of its callers, so the panic cannot be quoted")
    return Disposition(
        "panicked",
        f"panicked -- the frame holding it unwound "
        f"(f{f.id}, {fmt_exc(f.unwind_exc)})",
        f"the trace says f{f.id} unwound while holding this Err, not that "
        "the Err caused the panic")


_MARK_WORDS = {"test": "a #[test] fn", "main": "the bin crate's fn main"}


def _returned_to_harness(trace, chain, idx) -> Disposition:
    """The chain went back to libtest or out of `fn main`.

    Two verbs, because two things happen. A frame that CLOSED handed the
    `Err` out of itself -- "it left f3". A frame still on the stack when the
    thread ended never returned at all, and the chain is sitting in it --
    "it came to rest in f1", with the detail saying the recording stopped
    before that frame finished. Printing "left" there would claim a return
    this trace never saw.
    """
    f, mark, still_open = idx.harness_holder(chain.last)
    if f is None or mark is None:
        return Disposition(
            "returned-to-harness",
            "returned to the harness -- it left a frame the recording marks "
            "as a test or main entry point",
            "the site table carries no row naming which of the two, so the "
            "disposition stands without the claim")
    q = trace.code(f.code_id).qualname
    if still_open:
        return Disposition(
            "returned-to-harness",
            f"returned to the harness -- it came to rest in f{f.id} ({q}), "
            f"which the manifest marks as {_MARK_WORDS[mark]}",
            f"f{f.id} had not returned when the recording ended, so what the "
            "harness did with the Err is the next thing that would have "
            "happened, not something this trace watched")
    return Disposition(
        "returned-to-harness",
        f"returned to the harness -- it left f{f.id} ({q}), which the "
        f"manifest marks as {_MARK_WORDS[mark]}")


def _propagated(trace, chain, idx) -> Disposition:
    return Disposition(
        "propagated",
        f"propagated -- {chain.hops} hops, and still open when the thread "
        "ended",
        "a chain still open at the end of a thread means the thread was "
        "still live when the recording ended (`live_threads`) or its frames "
        "were not all instrumented; every hop it took is listed below")


#: The one sentence the tool prints under an escaped arm. It is a QUOTATION
#: of `rust/HONESTY.md` §11's SWALLOWED definition (design N2, 2026-09-05):
#: reading the error -- a guard, a predicate -- does not carry it out of the
#: arm; only a value derived from it leaving the arm does.
ESCAPED_DETAIL = ("a bound error that is stored, returned or moved out of the arm "
                  "is not a swallow; an arm that only reads it (a guard, a "
                  "predicate), formats or logs it and continues is one")


def _escaped(trace, chain, idx) -> Disposition:
    """Two shapes wear one terminal, and the `how` of the last event says
    which: an `arm_ambiguous` HANDLED bound the error to a name and let the
    name escape, and anything else is a frame that returned ok with nothing
    recorded absorbing what it held.

    Only the MOVE is ambiguous. An arm that borrows the error to format it
    and then carries on is an `arm_handled` and reaches `_swallowed`: the
    failure never got past that arm, and the log is where it went
    (`rust/HONESTY.md` §11, the definition's one home).
    `corpus/rust/err_stored` and `corpus/rust/logged_arm` are the two sides
    of that line.
    """
    e = chain.last
    if _how(e) == "arm_ambiguous":
        return Disposition(
            "ambiguous",
            f"ambiguous -- an Err(..) arm at e{e.id} ({_at(trace, e)}) bound "
            "it to a name and let the name escape",
            ESCAPED_DETAIL, site=_at(trace, e))
    return Disposition(
        "ambiguous",
        "ambiguous -- the frame holding it returned ok with no sink recorded",
        "it left the grammar this recorder watches (rust/HONESTY.md names "
        "the shapes that are not probed); no sink recorded is not evidence "
        "that nothing absorbed it")


def _merged(trace, chain, idx) -> Disposition:
    return Disposition(
        "ambiguous",
        "ambiguous -- it shared a frame's window with another, different Err",
        "identity across hops is (type, Debug text) and a window holding two "
        "distinct Errs cannot be split, so a merged window is never reported "
        "as a swallow")


def _handled_then_failed(trace, chain, idx) -> Disposition:
    h = chain.last
    fid = h.frame_id
    where = f" in f{fid}" if fid is not None else ""
    tail = f"f{fid} then failed anyway" if fid is not None else (
        "its frame then failed anyway")
    return Disposition(
        "ambiguous",
        f"ambiguous -- {_absorbed(trace, h)}{where}, but {tail}",
        "handled, then the frame failed for another reason -- the "
        "cleanup-then-fail blind spot (design R8): a genuine swallow in a "
        "frame that later fails reads ambiguous, not a swallow",
        site=_at(trace, h))


def _left_thread(trace, chain, idx) -> Disposition:
    return Disposition(
        "ambiguous",
        "ambiguous -- it left its thread into a JoinHandle; whether it was "
        "ever read is not recorded",
        "the parent may have unwrapped it, logged it or dropped the handle; "
        "a spawned thread's return value leaves no record of being read")


RULES = {
    "swallowed_candidate": _swallowed,
    "panicked": _panicked,
    "returned_to_harness": _returned_to_harness,
    "propagated": _propagated,
    "ambiguous_escaped": _escaped,
    "merged": _merged,
    "handled_then_failed": _handled_then_failed,
    "left_thread": _left_thread,
}


def classify(trace, chain, idx) -> Disposition:
    """What the recording supports about one chain -- and nothing more.

    Everything the table does not decide is AMBIGUOUS, including a terminal
    a newer converter invented. Falling through to a verdict is how a tool
    ends up making an accusation nobody wrote a rule for.
    """
    terminal = chain.terminal
    if terminal is None:
        return Disposition(
            "ambiguous",
            "ambiguous -- the recording records no ending for this chain",
            "chain.terminal rides a chain's last event and this one carries "
            "none, so the converter's machine never closed it")
    rule = RULES.get(terminal)
    if rule is None:
        return Disposition(
            "ambiguous",
            f"ambiguous -- this recording ends the chain with {terminal!r}, "
            "which these rules do not know",
            "a terminal a newer converter wrote and these rules do not "
            "decide reads ambiguous by design, never a swallow")
    return rule(trace, chain, idx)


# -- rendering --------------------------------------------------------------
def _hops_line(trace, chain) -> str | None:
    """The chain's whole journey on one line, each stop naming the site that
    recorded it. R8: the head prints the ORIGIN's type and each hop its own,
    with a type change labelled `translated` -- so a hop that changed the
    error type carries the new type here and nowhere else.

    A one-event chain gets no line: it would repeat the head verbatim.
    """
    if len(chain.events) < 2:
        return None
    parts = []
    for e in chain.events:
        part = f"e{e.id} {_at(trace, e)} {_how(e)}"
        if _chain(e).get("translated"):
            exc = (e.payload or {}).get("exc") or {}
            part += f" (translated to {exc.get('type', '?')})"
        parts.append(part)
    return "hops: " + " -> ".join(parts)


def _header(trace, idx) -> None:
    caps.print_incomplete(
        trace, "an Err whose fate was recorded after the cut is not below, "
               "and its absence here is not evidence it had none")
    if idx.panics:
        # An answer of "no exceptions recorded" about a run that panicked
        # is a false negative, and a tally with no panic in it reads as one
        # even when chains ARE listed.
        print(f"panics: {idx.panics} recorded -- this command judges Err "
              "flow; a panic is a frame's unwind, printed by `tree` and "
              "`frame`")
    _print_partial(idx.partial)


def _print_partial(rows) -> None:
    """`meta.partial` (design R6): `?` sites the transformer could not
    reach. Printed BEFORE the answer because it qualifies the whole of it --
    an `Err` raised at one of these sites is recorded by nothing, so its
    absence from the list below says nothing about the program."""
    if not rows:
        return
    noun = "?-site" if len(rows) == 1 else "?-sites"
    print(f"partial: {len(rows)} {noun} the transformer could not reach -- "
          "an Err raised at one is recorded by nothing and appears nowhere "
          "below")
    for r in rows[:PARTIAL_SHOWN]:
        print(f"  {r.get('qualname', '?')} {r.get('file', '?')}:"
              f"{r.get('line', '?')} ({r.get('reason', '?')})")
    if len(rows) > PARTIAL_SHOWN:
        print(f"  ... {len(rows) - PARTIAL_SHOWN} more (sensorium info)")


def run(trace, args, after: int) -> int:
    """`exceptions` on a Rust trace. `exceptions_cmd.run` has already
    validated `--limit`, resolved `--after` to the event id `after`, and
    opened the trace; the capability gate is the first thing that happens
    here, before any rule reads an event."""
    refusal = caps.require(trace, "err_flow", "exceptions")
    if refusal:
        # The command is spelled correctly and the trace is readable: the
        # recorder declares it wrote no err-flow record, so the reader's
        # next move is a recording made by one that does.
        print(f"REFUSED: {refusal}")
        return UNSETTLED
    idx = Index(trace)
    _header(trace, idx)
    if not idx.chains:
        # `caps.none_status`: "none" only where the recording is whole. An
        # empty answer on a run that stopped mid-flight reports where the
        # RECORDING ended, not what the program did.
        print("no exceptions recorded")
        return caps.none_status(trace)

    scope = [c for c in idx.chains if c.origin.id > after]
    skipped = len(idx.chains) - len(scope)
    if skipped:
        print(f"raised ({len(scope)} of {len(idx.chains)}; {skipped} earlier "
              f"chain(s) skipped by --after e{after}):")
    else:
        print(f"raised ({len(scope)}):")

    # One block per SHAPE, not per chain (design N3): `--after` has already
    # chosen the CHAINS in scope, and the groups form over exactly those.
    #
    # Local: `exceptions_group` imports `_at` and `_hops_line` from this
    # module, so a module-level import here would be a cycle.
    from sensorium.query.exceptions_group import group_chains, print_shapes
    shapes, tally = group_chains(trace, scope, idx, classify)
    shown = print_shapes(trace, shapes, args.limit)
    # Counted over every chain in scope, not just the printed ones and not
    # per shape: the tally never shrinks because a page was clipped, and it
    # stays comparable line-for-line with every record already written (N5).
    print("dispositions: " + ", ".join(f"{t} {tally[t]}" for t in TAG_ORDER
                                       if tally.get(t)))
    # Paging RAISES THE LIMIT rather than naming an event to resume after:
    # `--after` cuts chains, and a cursor that cut a group in half would
    # re-show it as a partial block still labelled with the whole count.
    # The reader's OWN `--after` is carried through (ruling R-G7): dropping
    # it made the continuation answer over a wider scope than the question
    # asked, which is a hint that lies about what it will show.
    scoped = f"--after e{after} " if after else ""
    note = more_note(len(shapes), shown,
                     f"sensorium exceptions {shlex.quote(args.run)} "
                     f"{scoped}--limit {len(shapes)}")
    if note:
        print(note)
    return ANSWERED
