"""`exceptions` for `lang = typescript`: what became of every throw.

WHY THIS IS A SEPARATE MODULE
-----------------------------
The five words are the Python command's -- `swallowed`, `uncaught`,
`re-raised`, `propagated`, `ambiguous` -- and so is the rule's shape: a
handler in a frame that then returned, with no later raise of the same
exception, is the swallow candidate. What does not transfer is the
INDEXING. `exceptions_cmd.Index` keys an exception on ``exc["oid"]``, the
address CPython gave the object, and a TypeScript recording carries no
address at all; its identity is a `serial` minted per thrown object through
a `WeakMap` (`typescript/src/dbg.mjs`). And CPython fires HANDLED on
`finally` and on `await` cleanup, which is why the Python rules hedge every
handler; this recorder writes HANDLED only where a `catch` clause, a
rejection callback or a completing `finally` really took the failure, and
the `how` word says which. Running the Python rules over these rows would
have keyed every exception on a field that is not there.

WHAT THIS MODULE DECIDES, AND WHAT IT REFUSES TO
------------------------------------------------
It decides DISPOSITIONS and nothing else. IDENTITY -- which rows are one
thrown object -- is the recorder's `serial`, read and never recomputed;
whether a bound `catch` let its error escape is decided by the transform
and rides the event as `how` (design R2, `typescript/src/escape.mjs`). Two
places deriving one fact is two places for it to drift, and each of those
has its own suite.

THE FIVE DISPOSITIONS (design R7, R8)
-------------------------------------
``swallowed``   an absorbing handler took it and the frame holding that
                handler then returned. The only accusation this command
                makes, and the one E6-TS gates.
``uncaught``    the process itself reported the rejection unhandled
                (`meta.unhandled_rejections`, R1/R6).
``re-raised``   a later raise carries the same serial. Every raise still
                keeps its own block and its own tally entry, as the Python
                output does, so a tally counts raises and stays comparable
                line for line.
``propagated``  it left the traced world: out of the test's own root frame,
                where the harness got it, or out of a frame Node entered
                with nothing traced beneath it.
``ambiguous``   THE DEFAULT, each reason printed: an escaped or opaque
                handler, a handler frame that never finished, a handler
                frame that then failed for its own reasons, a primitive
                with no identity, a recording that stopped mid-run, and
                anything else. Nothing reaches SWALLOWED by falling
                through.

WHERE THE TRACE CANNOT SAY
--------------------------
A thrown PRIMITIVE has nothing to hang a serial on, so every row of one
carries a fresh number. Within one frame a primitive raise pairs with the
next handler row carrying equal type and message (design §3.1); anything
wider -- across frames, or once a second raise of the same text exists --
is ambiguous, and two primitives are never merged on text (R11).

A shape the transform does not record produces no row, and the `how`
enumeration is the declaration of which ones it does
(`docs/trace-format/TYPESCRIPT-KEYS.md`). A handler in untraced code -- the
harness, a library, `.then(fn)` -- leaves nothing, so a failure it took
reads ambiguous or propagated, never a swallow. A rejection the process
reported unhandled and no row carries is counted in the header and judged
nowhere: it has no site, and inventing one is what R1 refuses.

The literal token `SWALLOWED` is printed by ONE sentence here -- `_swallowed`'s
verdict -- and by nothing else, not even by prose saying a shape is never
one: E6-TS collects the printed SWALLOWED lines and compares the set whole
(Rust's R15), so a detail line reading "never SWALLOWED" would enter that
count as an accusation nobody made.
"""
import shlex
from pathlib import Path

from sensorium.exit import ANSWERED, UNSETTLED
from sensorium.query import caps
from sensorium.query.exceptions_cmd import Disposition
from sensorium.query.fmt import fmt_exc, more_note
from sensorium.query.vocab import terms

TAG_ORDER = ("swallowed", "uncaught", "re-raised", "propagated", "ambiguous")

#: Every reason an AMBIGUOUS line can carry, in printing order (design
#: §2.3). `unnamed` is rule 5's catch-all and the number rung 3 is
#: measured on; a reason without a key here is a test failure.
REASON_ORDER = ("escaped", "untraced catcher", "suspended", "translated",
                "primitive", "orphan", "incomplete", "unnamed")

#: The `how` words that ABSORB a failure: the clause or callback took it
#: and nothing of it left by a route the transform can see.
ABSORBING = frozenset({"catch", "sink_empty_catch", "catch_callback",
                       "sink_empty_catch_callback", "sink_finally_return"})

#: The `how` words that do NOT: the binding, or a rendering of it, left the
#: handler (R2), or the handler is a function defined elsewhere and its
#: parameter's fate was never analysed (R4). One of these anywhere for a
#: serial is enough to keep every row of it out of a swallow (R8).
ESCAPING = frozenset({"catch_escaped", "catch_callback_escaped",
                      "catch_callback_opaque"})

#: `typeof`'s words. `object` with no message is `throw null`, the one
#: primitive whose `typeof` lies.
PRIMITIVE_TYPES = frozenset({"string", "number", "boolean", "undefined",
                             "symbol", "bigint"})


def _exc(e) -> dict:
    return ((e.payload or {}).get("exc")) or {}


def _how(e) -> str:
    return (e.payload or {}).get("how") or "?"


def _is_primitive(exc: dict) -> bool:
    return (exc.get("type") in PRIMITIVE_TYPES
            or (exc.get("type") == "object" and exc.get("msg") is None))


def _text(exc: dict) -> tuple:
    return (exc.get("type"), exc.get("msg"))


def _site(trace, e) -> tuple:
    """The site an event IS: `(file, line, qualname)` -- the code object's
    file, the event's own line, and the code object's qualname.

    The identity, not the rendering: two `loadConfig` helpers in two files
    at one line print the same words and are not the same place (Rust's
    ruling R-G12, which the grouper's key is keyed on). A code object this
    trace does not carry is `("?", line, "?")`.
    """
    code = trace.code(e.code_id) if e.code_id is not None else None
    return ((code.file if code is not None else "?"), e.line,
            (code.qualname if code is not None else "?"))


def site_text(site) -> str:
    """`qualname L<line>` -- the way every verdict here names a place, and
    the only spelling of it, so the text the grouper compares cannot drift
    from the text the verdict prints."""
    _file, line, qualname = site
    return f"{qualname} L{line}"


def site_file(site) -> str:
    """The site's file, basename only: what a colliding block adds to tell
    two same-named helpers apart on one line."""
    return Path(site[0]).name


def _at(trace, e) -> str:
    return site_text(_site(trace, e))


class Raise:
    """One unit of judgement: a RAISE, or a handler row no raise minted.

    ONE PER RAISE EVENT, not one per serial (design §3.3 rule 2): a rethrow
    is its own block with its own verdict, and the origin's block says what
    became of the last raise. `raises` is every raise of this serial, so a
    unit can see the whole journey without the journey becoming the unit.
    """

    def __init__(self, origin, serial, raises, handled, escaping, absorbing,
                 *, orphan=False, primitive=False, unresolved=False):
        self.origin = origin
        self.serial = serial
        self.raises = raises                 # every RAISE of this serial
        self.handled = handled               # the handlers in THIS window
        self.escaping = escaping             # escaping handlers, anywhere
        self.absorbing = absorbing           # absorbing handlers, anywhere
        self.orphan = orphan
        self.primitive = primitive
        #: A primitive whose rows cannot be linked: another raise of the
        #: same text exists, so which row is which throw is not on the wire.
        self.primitive_rethrown = unresolved

    @property
    def next_raise(self):
        return next((r for r in self.raises if r.id > self.origin.id), None)

    @property
    def last_raise(self):
        return self.raises[-1] if self.raises else self.origin


class Index:
    """Everything the rules read, gathered in one pass.

    The pairing lives here rather than in the rules because it is a fact
    about the RECORD -- which rows are one thrown object -- and the rules
    are about what became of it. §3.1: an object's rows share a serial and
    a window runs from one raise of it to the next, so a loop that rethrows
    one object pairs each raise with its own handler; a primitive's rows
    never share one and pair only within a frame, on equal text.
    """

    def __init__(self, trace):
        self.trace = trace
        meta = trace.meta
        self.incomplete = bool(meta.get("incomplete"))
        self.rejections = {r["serial"]: r
                           for r in (meta.get("unhandled_rejections") or [])
                           if r.get("serial") is not None}
        raises, handled = [], []
        for e in trace.events(kind=("RAISE", "HANDLED")):
            if _exc(e):
                (raises if e.kind == "RAISE" else handled).append(e)
        self._raises_by_serial: dict = {}
        for r in raises:
            self._raises_by_serial.setdefault(
                _exc(r).get("serial"), []).append(r)
        self._raises = raises
        self._prim_texts = [_text(_exc(r)) for r in raises
                            if _is_primitive(_exc(r))]
        self._left = _unwound_by_serial(trace)
        self.units = self._build(raises, handled)
        self._by_origin = {u.origin.id: u for u in self.units}

    def _build(self, raises, handled) -> list:
        """One unit per raise, then one per SERIAL no raise minted.

        Per serial and not per row: two handlers of one rejection are one
        exception handled twice, and splitting them would let the absorbing
        row be judged without seeing the escaping one (R8).
        """
        claimed: set = set()
        units = [self._unit(r, handled, claimed) for r in raises]
        orphans: dict = {}
        for h in handled:
            serial = _exc(h).get("serial")
            if h.id in claimed or serial in self._raises_by_serial:
                continue
            # A row carrying no serial at all is nobody's sibling: keyed on
            # its own id, so two of them are never merged into one story.
            orphans.setdefault(serial if serial is not None else ("e", h.id),
                               []).append(h)
        units += [self._orphan(rows) for rows in orphans.values()]
        return sorted(units, key=lambda u: u.origin.id)

    def _unit(self, r, handled, claimed) -> Raise:
        exc = _exc(r)
        serial = exc.get("serial")
        if serial is None:
            return Raise(r, None, [r], [], [], [])
        if _is_primitive(exc):
            mine = _primitive_partner(r, handled, self._raises)
            claimed.update(h.id for h in mine)
            return Raise(r, serial, [r], mine, _escaping(mine),
                         _absorbing(mine), primitive=True,
                         unresolved=self._prim_texts.count(_text(exc)) > 1)
        siblings = self._raises_by_serial[serial]
        end = next((x.id for x in siblings if x.id > r.id), None)
        same = [h for h in handled if _exc(h).get("serial") == serial]
        mine = [h for h in same
                if h.id > r.id and (end is None or h.id < end)]
        claimed.update(h.id for h in mine)
        return Raise(r, serial, siblings, mine, _escaping(same),
                     _absorbing(same))

    def _orphan(self, rows) -> Raise:
        exc = _exc(rows[0])
        prim = _is_primitive(exc)
        return Raise(rows[0], exc.get("serial"), [], rows, _escaping(rows),
                     _absorbing(rows), orphan=True, primitive=prim,
                     unresolved=prim and _text(exc) in self._prim_texts)

    def unit_of(self, event) -> Raise:
        return self._by_origin[event.id]

    def left_frame(self, serial):
        """The OUTERMOST frame this serial left by throwing, or None.

        Outermost, because that is how far the failure got: every frame it
        unwound is on the wire and the one nearest the top of the stack is
        the last word the recording has about where it went.
        """
        return self._left.get(serial)

    def task_of(self, frame, event):
        """The test a frame belongs to, or None where no test was running.

        Read from the frame's own CALL row first -- that is the row the
        converter stamped when it opened the frame -- and from the event
        asking only where the frame's row carries none.
        """
        call = (self.trace.event(frame.call_event_id)
                if frame.call_event_id is not None else None)
        tid = (call.task_id if call is not None and call.task_id is not None
               else event.task_id)
        return self.trace.task(tid) if tid is not None else None


def _escaping(handled) -> list:
    return [h for h in handled if _how(h) in ESCAPING]


def _absorbing(handled) -> list:
    return [h for h in handled if _how(h) in ABSORBING]


def _primitive_partner(r, handled, raises) -> list:
    """§3.1's one admitted pairing for a primitive: the next handler row in
    the SAME frame carrying equal type and message, with NO raise between.

    Nothing wider is admitted. A primitive caught a frame up cannot be told
    from another throw of the same text, and a rule that paired them on
    text would report a swallow the recording does not establish (R11). The
    window closes at the next raise of any kind: once something else has
    been thrown, which throw a later handler row belongs to is a question
    about text, and text is not identity.
    """
    exc = _exc(r)
    end = next((x.id for x in raises if x.id > r.id), None)
    for h in handled:
        if h.id <= r.id or (end is not None and h.id > end):
            continue
        if h.frame_id == r.frame_id and _text(_exc(h)) == _text(exc):
            return [h]
    return []


def _unwound_by_serial(trace) -> dict:
    """serial -> the outermost frame that closed by throwing it."""
    out: dict = {}
    for f in trace.frames():
        if f.closed_by != "unwind":
            continue
        serial = (f.unwind_exc or {}).get("serial")
        if serial is None:
            continue
        best = out.get(serial)
        if best is None or (f.depth, f.id) < (best.depth, best.id):
            out[serial] = f
    return out


# -- the rules, in order (design §3.3) --------------------------------------
def _uncaught(trace, unit, idx) -> Disposition | None:
    """1. The process reported the rejection unhandled and no later raise
    carries the serial. It has no site of its own where no raise minted it,
    and the verdict says that rather than borrowing a handler's (R1)."""
    if unit.serial not in idx.rejections or unit.next_raise is not None:
        return None
    if unit.orphan:
        return Disposition(
            "uncaught", "UNCAUGHT -- unhandled rejection; born outside "
                        "traced code (a reject() or a library)")
    return Disposition(
        "uncaught", "UNCAUGHT -- unhandled rejection; raised at "
                    f"{_at(trace, unit.origin)}")


def _reraised(trace, unit, idx) -> Disposition | None:
    """2. A later raise carries this serial, so this row is a hop and not
    an ending. The verdict points at what became of the LAST raise, whose
    own block carries that verdict in full -- the recursion terminates
    because the last raise has no later raise to find."""
    nxt = unit.next_raise
    if nxt is None:
        return None
    tag = classify(trace, idx.unit_of(unit.last_raise), idx).tag
    # No detail: the route is the BLOCK's own last line, printed for every
    # unit that has one by `exceptions_group.print_shape` (which is where
    # the same line has always come from on a Rust block). Carrying it here
    # as well would print one journey twice under one verdict.
    return Disposition(
        "re-raised",
        f"RE-RAISED -- raised again at e{nxt.id} ({_at(trace, nxt)}) "
        f"→ {tag}")


def _unresolved(trace, unit, idx) -> Disposition | None:
    """§3.1, ahead of rules 3 and 4 because it is about IDENTITY and not
    about fate: where a second raise of the same primitive text exists, no
    row of it can be attached to any other, so neither the accusation nor
    the claim that it left the traced world is available.

    The trigger is trace-global and the sentence says both readings it
    covers: two records of one text may be one throw rethrown OR two
    unrelated throws, and nothing on the wire tells them apart (R11).
    """
    if not unit.primitive_rethrown:
        return None
    return Disposition(
        "ambiguous",
        "AMBIGUOUS -- a primitive carries no identity: two records with "
        "this text may be one throw rethrown or two throws; not followed",
        "every row of a thrown primitive carries a fresh serial, and two "
        "of one text are never merged",
        reason="primitive")


def _birth(trace, unit) -> str | None:
    """Where a handler row no raise minted came from, in the words the
    record supports: `exc.kind` is the whole of what says which."""
    if not unit.orphan:
        return None
    if _exc(unit.origin).get("kind") == "rejection":
        return "born outside a throw statement (a reject())"
    return f"born outside traced code, at {_at(trace, unit.origin)}"


def _swallowed(trace, unit, idx) -> Disposition | None:
    """3. An absorbing handler, a frame that then RETURNED, no later raise
    of the serial, and no escaping handler for it anywhere.

    The Python rule's thrown-in clause does not transfer: this wire's
    RESUME carries no `thrown` key, so a handler frame that later unwound
    for any reason is rule 5's, never this one's.
    """
    if unit.escaping or unit.next_raise is not None:
        return None
    h = next((h for h in unit.handled if _how(h) in ABSORBING), None)
    if h is None:
        return None
    f = trace.frame(h.frame_id) if h.frame_id is not None else None
    if f is None or f.closed_by != "return":
        return None
    return Disposition(
        "swallowed",
        f"SWALLOWED -- caught by {_how(h)} at e{h.id} ({_at(trace, h)}) in "
        f"f{f.id}, which returned",
        _birth(trace, unit), site=_site(trace, h))


def _still_open_absorber(trace, unit):
    """The first absorbing handler IN THIS UNIT'S OWN WINDOW whose frame
    did NOT close by returning, or None where every one of them did.

    This is §3.3 rule 4's absorbing conjunct as coded (spec §14 R15),
    scoped to the window by rung 3 (§2.2): `unit.handled` filtered to the
    absorbing set, never `unit.absorbing`. What it is about is unchanged --
    a handler that took the failure and has not finished -- and a frame
    with no row at all still counts as one, because "it returned" is
    exactly what such a row does not establish.

    An EARLIER window's handler is not read here at all. For a rethrown
    serial `unit.absorbing` carries every absorbing handler of it,
    including the one whose frame was closed BY THIS VERY RETHROW: that
    frame is the rethrow's predecessor, not an unfinished handler, and the
    origin's own block already says `re-raised → <word>` about it. Reading
    it made `catch (e) { console.error(e); throw e }` unwinding a test root
    decline rule 4 and print a reason, about a failure the harness saw.

    Rule 3's escaping conjunct and rule 4's escaping decline stay
    trace-global, exactly as rung 2 wrote them: an escaped object can be
    rethrown from anywhere, and a later accusation about it would be the
    false one the escape rule exists to prevent.
    """
    for h in [h for h in unit.handled if _how(h) in ABSORBING]:
        f = trace.frame(h.frame_id) if h.frame_id is not None else None
        if f is None or f.closed_by != "return":
            return h
    return None


def _propagated(trace, unit, idx) -> Disposition | None:
    """4. It left the traced world: the outermost frame it unwound has no
    traced caller.

    Both of §3.3's conjuncts are here, each for the same reason: this
    verdict says nothing traced took the failure, and a recording holding a
    handler row for that serial in this unit's own window (absorbing) or
    anywhere in the trace (escaping) contradicts it. An ESCAPING handler is
    rule 5's escaped verdict; an ABSORBING one whose frame never closed is
    rule 5's suspended verdict -- a parked `.catch(async …)` callback is
    ordinary JavaScript, and its frame unwinding below is not evidence that
    the handler was untraced or that the harness ever saw the failure.
    """
    if unit.escaping or _still_open_absorber(trace, unit) is not None:
        return None
    f = idx.left_frame(unit.serial)
    if f is None or f.parent_id is not None:
        return None
    task = idx.task_of(f, unit.origin)
    if task is None:
        return Disposition("propagated",
                           "PROPAGATED -- handler not in traced code")
    name = task.name or terms(trace).unnamed_task
    return Disposition(
        "propagated", f'PROPAGATED -- to the harness: test "{name}" failed')


def _untraced_catcher(trace, unit, idx) -> Disposition | None:
    """§2.1: no handler row in this window, the outermost frame the serial
    left has a traced parent, and that parent is not the raise's own frame.
    Names the footprint; claims nothing about what the untraced code did."""
    if unit.handled or unit.escaping or unit.serial in idx.rejections:
        return None
    f = idx.left_frame(unit.serial)
    if f is None or f.parent_id is None or f.parent_id == unit.origin.frame_id:
        return None
    p = trace.frame(f.parent_id)
    if p is None:
        return None
    code = trace.code(p.code_id)
    where = f"{code.qualname} ({Path(code.file).name})"
    if p.closed_by == "return":
        fate = f"its caller f{p.id} returned; not followed"
    elif p.closed_by == "unwind":
        fate = (f"its caller f{p.id} later unwound with "
                f"{fmt_exc(p.unwind_exc)}: a translation by untraced code, "
                "or a later failure, indistinguishable")
    else:
        fate = (f"its caller f{p.id} had not closed at the end of the "
                "recording; not followed")
    site = (code.file, code.firstlineno, code.qualname)     # P3
    return Disposition(
        "ambiguous",
        f"AMBIGUOUS -- caught by untraced code inside {where}: f{f.id} "
        f"unwound, {fate}",
        site=site, reason="untraced catcher")


def _ambiguous(trace, unit, idx) -> Disposition:
    """5. Everything else, with the reason printed. Ambiguous by default is
    what keeps a shape nobody wrote a rule for out of the accusation."""
    if unit.escaping:
        h = unit.escaping[0]
        return Disposition(
            "ambiguous",
            f"AMBIGUOUS -- caught at e{h.id} ({_how(h)}), and the error or "
            "a rendering of it left the handler; not followed",
            site=_site(trace, h), reason="escaped")
    named = _untraced_catcher(trace, unit, idx)
    if named is not None:
        return named
    open_h = _handler_frame(trace, unit, lambda f: f.closed_by is None)
    if open_h is not None:
        h, f = open_h
        state = trace.frame_state(f).state
        tail = ("is still suspended at the end of the recording"
                if state == "suspended"
                else "had not closed at the end of the recording")
        return Disposition("ambiguous",
                           f"AMBIGUOUS -- the handler's frame f{f.id} {tail}",
                           reason="suspended")
    gone = _handler_frame(
        trace, unit,
        lambda f: (f.closed_by == "unwind"
                   and (f.unwind_exc or {}).get("serial") != unit.serial))
    if gone is not None:
        _h, f = gone
        return Disposition(
            "ambiguous",
            f"AMBIGUOUS -- handler's frame f{f.id} later unwound with "
            f"{fmt_exc(f.unwind_exc)}: a translation or a later failure, "
            "indistinguishable",
            reason="translated")
    if idx.incomplete:
        return Disposition(
            "ambiguous",
            "AMBIGUOUS -- this recording never finalized (INCOMPLETE)",
            reason="incomplete")
    # P2: the KEY follows the SENTENCE, so an orphan is keyed `orphan` only
    # where it reaches this catch-all -- one escaping HANDLED above prints
    # the escaped sentence and is counted under `escaped` beside every
    # other verdict reading those words.
    return Disposition(
        "ambiguous",
        "AMBIGUOUS -- no rule of this recorder reaches a verdict here",
        reason="orphan" if unit.orphan else "unnamed")


def _handler_frame(trace, unit, pred):
    """The first of this unit's handlers whose frame satisfies `pred`, as
    `(handler, frame)` -- or None where no handler has such a frame."""
    for h in unit.handled:
        f = trace.frame(h.frame_id) if h.frame_id is not None else None
        if f is not None and pred(f):
            return h, f
    return None


RULES = (_uncaught, _reraised, _unresolved, _swallowed, _propagated)


def classify(trace, unit, idx) -> Disposition:
    """What the recording supports about one raise -- and nothing more."""
    for rule in RULES:
        d = rule(trace, unit, idx)
        if d is not None:
            return d
    return _ambiguous(trace, unit, idx)


# -- rendering --------------------------------------------------------------
def _hops_line(trace, unit) -> str | None:
    """One object's whole journey on one line, each stop naming the site
    that recorded it. A single-raise unit gets no line: it would repeat the
    head verbatim."""
    if len(unit.raises) < 2:
        return None
    return "hops: " + " → ".join(f"e{e.id} ({_at(trace, e)})"
                                 for e in unit.raises)


def _header(trace, idx) -> None:
    caps.print_incomplete(
        trace, "a throw whose fate was recorded after the cut is not below, "
               "and its absence here is not evidence it had none")
    if idx.rejections:
        # The same line `info` prints, in the same words. A rejection no
        # row carries is counted HERE and judged nowhere: it has no site,
        # so it opens no block (R1) and a reader who saw only the tally
        # would not know it happened.
        print(f"unhandled rejections: {len(idx.rejections)}")


def run(trace, args, after: int) -> int:
    """`exceptions` on a TypeScript trace. `exceptions_cmd.run` has already
    validated `--limit`, resolved `--after` to the event id `after` and
    opened the trace; the capability gate is the first thing that happens
    here, before any rule reads an event."""
    refusal = caps.require(trace, "err_flow", "exceptions")
    if refusal:
        # The command is spelled correctly and the trace is readable: the
        # recorder declares it wrote no throw-flow record, so the reader's
        # next move is a recording made by one that does.
        print(f"REFUSED: {refusal}")
        return UNSETTLED
    idx = Index(trace)
    _header(trace, idx)
    if not idx.units:
        # Silence on a recording that stopped mid-run is a gap, not a
        # "none" -- `caps.none_status` is the shared rule for which.
        print("no RAISE events recorded (see INCOMPLETE above)"
              if idx.incomplete else "no exceptions recorded")
        return caps.none_status(trace)

    scope = [u for u in idx.units if u.origin.id > after]
    skipped = len(idx.units) - len(scope)
    if skipped:
        print(f"raised ({len(scope)} of {len(idx.units)}; {skipped} earlier "
              f"raise(s) skipped by --after e{after}):")
    else:
        print(f"raised ({len(scope)}):")

    # One block per SHAPE, not per raise (§3.4, which adopts the Rust
    # grouper's grain): `--after` has already chosen the raises in scope,
    # and the groups form over exactly those. Fifty raises absorbed by one
    # `catch` are one fact about one place, and fifty blocks saying it are
    # the table an adjudicator would otherwise build by hand.
    #
    # Local: `exceptions_group` imports this module for its renderer, so a
    # module-level import here would be a cycle.
    from sensorium.query.exceptions_group import (TYPESCRIPT, group_units,
                                                  print_shapes)
    # Both tallies come from the grouping pass, which classified every unit
    # in scope exactly once: counting them a second time here would be a
    # second judgement of one record, and the two could disagree.
    shapes, tally, reasons = group_units(trace, scope, idx, classify,
                                         TYPESCRIPT)
    shown = print_shapes(trace, shapes, args.limit)
    # Counted over every raise in scope, not just the printed ones and not
    # per shape: the tally never shrinks because a page was clipped, and it
    # stays comparable line for line with every per-raise record already
    # written.
    print("dispositions: " + ", ".join(f"{t} {tally[t]}" for t in TAG_ORDER
                                       if tally.get(t)))
    # §2.3: under the tally, and only where there is an ambiguity to
    # explain. Zero entries are omitted -- a reason nothing wore is not a
    # fact about this run -- and the order is the table's, never the
    # counting order, so two answers are comparable key by key.
    if reasons:
        print("ambiguous by reason: " + ", ".join(
            f"{r} {reasons[r]}" for r in REASON_ORDER if reasons.get(r)))
    # Paging RAISES THE LIMIT rather than naming an event to resume after:
    # `--after` cuts raises, and a cursor that cut a group in half would
    # re-show it as a partial block still labelled with the whole count.
    # The reader's OWN `--after` is carried through (R-G7): dropping it
    # made the continuation answer over a wider scope than the question
    # asked, which is a hint that lies about what it will show.
    scoped = f"--after e{after} " if after else ""
    note = more_note(len(shapes), shown,
                     f"sensorium exceptions {shlex.quote(args.run)} "
                     f"{scoped}--limit {len(shapes)}")
    if note:
        print(note)
    return ANSWERED
