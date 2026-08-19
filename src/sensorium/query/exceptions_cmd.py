"""Every raise and what became of it. "Silently swallowed" is the headline,
which is exactly why the bar for asserting it is high.

WHY THE OBVIOUS RULE IS WRONG
-----------------------------
The tempting rule -- "a RAISE whose exception has a later HANDLED and no
later RAISE was swallowed" -- is a false accusation generator. Measured
against real recorded traces, that head shape is produced by three different
program behaviours:

  * a genuine swallow (``except Exception: pass``)
  * a bare ``raise`` re-raise inside the handler
  * an exception that was never caught at all and merely crossed a
    ``finally``

CPython compiles ``finally`` as an implicit exception handler, so
EXCEPTION_HANDLED fires on entry to a ``finally`` block that has no
``except`` anywhere near it. A never-caught exception crossing one
``finally`` produces *two* HANDLED rows. The presence of a HANDLED row
therefore means nothing on its own. (The tracer does subscribe RERAISE, but
records no event for it -- it only keeps in-flight state -- so re-raises are
not directly visible either.)

THE DISCRIMINATOR
-----------------
Every HANDLED event carries a ``frame_id``, and that frame's ``closed_by``
says how the frame ended:

  genuine swallow      -> "return"  (the frame completed normally)
  bare re-raise        -> "unwind"  (+ unwind_exc naming the exception)
  uncaught via finally -> "unwind"

So the rule is: an exception is SWALLOWED iff some HANDLED for it sits in a
frame whose ``closed_by == "return"``, and no later RAISE carries its
identity. If every HANDLED for it sits in an unwound frame, it kept going and
is never reported as swallowed.

Both halves are load-bearing. ``except E as e: return e`` closes its frame by
"return" while handing the exception *out* of that frame, so a returning
handler frame alone does not mean the exception stopped there. With exact
identity that case is resolved rather than hedged: the later RAISE is
provably the same object, so it is reported as caught here and raised again.

EXCEPTION IDENTITY
------------------
``oid`` is ``id(exc)`` and CPython recycles addresses aggressively: measured
live, a ValueError and the RuntimeError raised two lines later in the same
frame shared an oid, and an ordinary retry loop gives three distinct
ValueError objects *one* address. Identity is therefore the recorder's
``serial`` -- minted while the recorder holds the object, so one serial is one
object, provably. Traces recorded before serials existed fall back to
``(type, msg, oid)``, hedge every verdict that turns on the difference, and
say so under a ``LEGACY TRACE`` banner.

Every lookup is scoped to the events between one RAISE and the next RAISE of
the same identity, so a loop raising an identical exception repeatedly still
pairs each raise with its own handler.

WHERE A SERIAL RUNS OUT
-----------------------
A serial proves that two rows *are* the same object. It cannot prove that two
rows are *different* objects, because the recorder remembers only a bounded
number of exceptions per thread and links a re-raise only within the thread
that handled it. Stash an exception, handle enough others to push it out of
that table, raise it again, and it comes back with a fresh serial.

So a differing serial is never read here as proof of a differing object.
Wherever that inference would be load-bearing -- "never re-raised", and "the
frame unwound with some *other* exception" -- the address and type are checked
too. An object keeps both for life, so nothing that is really the same object
slips past; a different object at a recycled address can trip it, and the
result is an honest hedge naming both readings rather than a verdict the run's
own uncaught header contradicts.

WHERE THE TRACE CANNOT SAY
--------------------------
Two shapes are recorded identically and are not separated here:

  * ``except E as e: raise Wrapped() from e``  (a translation), and
  * ``except E: pass`` followed later by an unrelated ``raise``

Both leave a HANDLED in a frame that then unwinds with a *different*
exception. ``capture_exc`` records type/msg/oid only, so ``__context__`` --
which would separate them -- is not in the trace. Both are reported as what
is actually known: handled here, frame later died of something else, cause
unestablished.

Likewise, a re-raise ultimately caught by *untraced* code leaves no record of
where it was caught. That prints ``propagated (handler not in traced code)``
rather than a guess. Generators and coroutines are frameless, so a HANDLED
inside one has no ``closed_by`` at all and gets no verdict.

Control-flow exceptions (StopIteration, StopAsyncIteration, GeneratorExit)
were excluded at record time and never appear. SystemExit is not: a plain
``sys.exit()`` is a real exception and shows up here, normally as propagated
out of traced code, because the recorder's own handler is untraced.
"""
import shlex
from dataclasses import dataclass

from sensorium import paths
from sensorium.query.fmt import fmt_event, fmt_exc, more_note, parse_eref
from sensorium.store.reader import Trace

TAG_ORDER = ("swallowed", "uncaught", "re-raised", "propagated", "ambiguous")


def add_parser(sub) -> None:
    p = sub.add_parser("exceptions", help="raises, handles, swallows")
    p.add_argument("run")
    p.add_argument("--after", default=None, help="event ref to resume from")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=run)


def exc_key(exc: dict, thread_id=None) -> tuple:
    """Identity of one exception object.

    `serial` is exact: the recorder mints it while holding a strong reference
    to the object, so two distinct exceptions can never share one. It is
    per-thread, hence the thread in the key.

    `oid` is `id(exc)` and is NOT an identity -- CPython recycles addresses,
    measurably so in a plain retry loop. Traces recorded before serials
    existed fall back to it, and every verdict that would depend on the
    difference is hedged and labelled rather than asserted.
    """
    s = exc.get("serial")
    if s is not None:
        return ("serial", thread_id, s)
    return ("legacy", exc["type"], exc["msg"], exc["oid"])


def could_be_same(a: dict, b: dict) -> bool:
    """Whether `b` could be `a`'s object recorded under a lost link.

    A serial proves that two rows ARE one object. It cannot prove they are
    two, because the recorder remembers a bounded number of exceptions per
    thread and links a re-raise only within the thread that handled it: an
    object it has forgotten comes back with a fresh serial. An object's
    address and type, though, are fixed for its lifetime, so equality there is
    a necessary condition for sameness and the cheapest sound way to ask "may
    these be one object?".

    Equal serials say the recorder did link the two rows, and are handled as
    the proof they are before this is ever asked. Two legacy rows both answer
    None there, which is why this is dormant on a legacy trace -- whose
    identity already includes the address anyway.
    """
    return (a["oid"] == b["oid"] and a["type"] == b["type"]
            and a.get("serial") != b.get("serial"))


@dataclass(frozen=True)
class Disposition:
    tag: str                    # summary bucket, one of TAG_ORDER
    verdict: str                # the claim, printed under the RAISE
    detail: str | None = None   # the evidence or the refusal to conclude


@dataclass(frozen=True)
class Index:
    """Everything the classifier needs, read once."""
    all_raises: list
    raises: dict
    handled: dict
    uncaught: dict | None
    uncaught_key: tuple | None
    uncaught_origin: object | None
    exit_status: object
    incomplete: bool
    exact: bool                 # every RAISE carries a recorder serial
    by_addr: dict               # (oid, type) -> the RAISE events at it

    @classmethod
    def build(cls, trace, meta: dict) -> "Index":
        all_raises = [e for e in trace.events(kind="RAISE")
                      if (e.payload or {}).get("exc")]
        exact = all("serial" in e.payload["exc"] for e in all_raises)
        raises: dict = {}
        by_addr: dict = {}
        for r in all_raises:
            exc = r.payload["exc"]
            raises.setdefault(exc_key(exc, r.thread_id), []).append(r)
            by_addr.setdefault((exc["oid"], exc["type"]), []).append(r)
        handled: dict = {}
        for h in trace.events(kind="HANDLED"):
            exc = (h.payload or {}).get("exc")
            if exc:
                handled.setdefault(
                    exc_key(exc, h.thread_id), []).append(h)
        unc = meta.get("uncaught") or None
        # `boot` captures the uncaught record on the main thread, which is the
        # only thread whose exceptions can escape `target()`.
        ukey = exc_key(unc, trace.main_thread_id()) if unc else None
        # The escaping object's origin is the LAST raise carrying its
        # identity. With serials there is only ever one; on a legacy trace an
        # earlier match may be address reuse, so the last is the safe pick.
        origin = raises[ukey][-1] if ukey in raises else None
        return cls(all_raises, raises, handled, unc, ukey, origin,
                   meta.get("exit_status", "?"), bool(meta.get("incomplete")),
                   exact, by_addr)

    def unlinked_later(self, r) -> list:
        """Later RAISEs that could be `r`'s object under another serial.

        Every re-raise the recorder failed to link is in here -- along with,
        occasionally, an unrelated exception of the same type at a recycled
        address. That is the right way round: this list gates the one claim
        ("never re-raised") that a missed link would make false, so an extra
        entry costs a hedge rather than a false accusation.
        """
        exc = r.payload["exc"]
        return [x for x in self.by_addr.get((exc["oid"], exc["type"]), ())
                if x.id > r.id and could_be_same(exc, x.payload["exc"])]


def _at(trace, e) -> str:
    q = trace.code(e.code_id).qualname if e.code_id is not None else "?"
    return f"{q} L{e.line}"


def _frame_of(trace, e):
    return trace.frame(e.frame_id) if e.frame_id is not None else None


def _uncaught(trace, idx, handled) -> Disposition:
    detail = None
    if handled:
        ids = ", ".join(f"e{h.id}" for h in handled)
        detail = (f"the {len(handled)} HANDLED row(s) here ({ids}) sit in "
                  "frames that unwound: finally/cleanup blocks entered while "
                  "it was in flight, not a catch")
    return Disposition(
        "uncaught",
        f"uncaught -- left the program (exit {idx.exit_status}); "
        "not swallowed", detail)


def _swallowed(trace, h, frame) -> Disposition:
    return Disposition(
        "swallowed",
        f"SWALLOWED at e{h.id} {_at(trace, h)} -- caught in f{frame.id}, "
        "which returned normally; never re-raised")


def _link_lost(trace, h, frame, nxt) -> Disposition:
    """A returning handler frame, and a later RAISE of the same type at the
    same address under a *different* serial.

    One object cannot hold two serials while the recorder still remembers it,
    so either it forgot this one -- its table is bounded, and it links a
    re-raise only within the thread that handled it -- or the later raise is a
    new object at the address this one freed. The first reading makes
    "never re-raised" false; the second makes it true; the trace supports
    neither, so neither is asserted.
    """
    return Disposition(
        "ambiguous",
        f"handled at e{h.id} {_at(trace, h)} -- f{frame.id} returned "
        f"normally, but a later RAISE (e{nxt.id}) is the same exception type "
        "at the same address under a different recorder identity",
        "the recorder links a re-raise only while it still holds the handled "
        "exception, and it holds a bounded number per thread, so this is "
        "either a swallow whose address a later exception reused or this same "
        "object stored and raised again; the trace cannot tell them apart")


def _stored_or_reused(trace, h, frame, nxt, exact) -> Disposition:
    """A returning handler frame with a later RAISE of the same identity.

    `except E as e: return e` closes its frame by "return" -- the swallow
    signal -- while handing the exception out of it. With exact identity the
    trace settles it: the later RAISE is provably this same object, so it was
    caught here and raised again, and both facts are reported together.

    Without serials the two readings cannot be separated (the later raise may
    be a new object at a reused address), so neither is asserted.
    """
    if exact:
        return Disposition(
            "re-raised",
            f"handled at e{h.id} {_at(trace, h)} in f{frame.id}, which "
            f"returned normally -- then raised again at e{nxt.id}")
    return Disposition(
        "ambiguous",
        f"handled at e{h.id} {_at(trace, h)} -- f{frame.id} returned "
        f"normally, but a later RAISE (e{nxt.id}) carries the same identity",
        "either it was swallowed there and that later raise is a new object "
        "at a reused address, or it was handed out of the frame (`return e`) "
        "and raised again; this trace has no serials, so it cannot tell them "
        "apart")


def _reraised(trace, r, handled, nxt, exact) -> Disposition:
    """Two RAISE rows carrying one identity: re-raised, or address reuse?

    With serials there is no question -- one identity is one object, and this
    is a re-raise.

    Without them the answer is not derivable, and the shape that proves it is
    a handler in *untraced* code: it ends the exception's flight and frees the
    object while leaving no HANDLED row at all, after which a fresh exception
    can take the address. Measured: two provably distinct ValueError('dup')
    objects, one address, zero HANDLED rows. So on a legacy trace "no HANDLED
    row in between" says nothing about whether the object survived, and the
    same-statement test is only a heuristic.
    """
    if exact:
        if handled:
            h = handled[0]
            return Disposition(
                "re-raised",
                f"handled at e{h.id} {_at(trace, h)}, then raised again at "
                f"e{nxt.id}")
        return Disposition(
            "re-raised",
            f"the same exception object is raised again at e{nxt.id}",
            "no HANDLED row in between: the trace cannot say what caught it")
    if not handled:
        return Disposition(
            "ambiguous",
            f"e{nxt.id} carries the same type/message/oid, with no HANDLED "
            "row in between",
            "a handler in untraced code ends an exception without leaving a "
            "HANDLED row, so this is either the same object raised again or a "
            "new one at a reused address; re-record to resolve it")
    h = handled[0]
    if (r.code_id, r.line) == (nxt.code_id, nxt.line):
        return Disposition(
            "ambiguous",
            f"handled at e{h.id} {_at(trace, h)} -- e{nxt.id} carries the "
            "same identity, raised from the same statement",
            "a loop re-running one raise frees each exception before the next "
            "is allocated, so CPython hands the new one a reused address; "
            "this trace has no serials, so it cannot say which happened")
    return Disposition(
        "re-raised",
        f"handled at e{h.id} {_at(trace, h)}, then raised again at "
        f"e{nxt.id}")


def _no_handler_found(trace, idx) -> Disposition:
    if idx.incomplete:
        return Disposition(
            "ambiguous",
            "unresolved -- the recording ended before its fate was recorded",
            "no HANDLED row for it anywhere, and this run never finalized: "
            "with no uncaught record the trace cannot say whether it was "
            "caught or killed the process")
    return Disposition(
        "propagated", "propagated (handler not in traced code)",
        "no HANDLED row for it anywhere in the trace, and it did not reach "
        "the top of the program")


def _still_in_flight(trace, idx, h, frame) -> Disposition:
    evidence = (f"handled at e{h.id} {_at(trace, h)}, but f{frame.id} unwound "
                "with the same exception -- that HANDLED is a finally/cleanup "
                "block, not a catch")
    if idx.incomplete:
        return Disposition(
            "ambiguous",
            "unresolved -- the recording ended before its fate was recorded",
            evidence + "; and with no finalize pass there is no uncaught "
            "record either")
    return Disposition("propagated",
                       "propagated (handler not in traced code)", evidence)


def _maybe_still_in_flight(trace, h, frame) -> Disposition:
    """The frame unwound with an exception at this one's address and type, but
    under a different serial.

    Same reasoning as `_link_lost`, on the other side: a long cleanup that
    raises and handles more exceptions than the recorder retains can push the
    exception it is cleaning up out of the identity table, so the frame it
    finally leaves carries a fresh serial for the same object. Reporting that
    as "this one did not leave the frame" would be false about the one thing
    the reader came for.
    """
    return Disposition(
        "ambiguous",
        f"handled at e{h.id} {_at(trace, h)} -- f{frame.id} then unwound with "
        f"{fmt_exc(frame.unwind_exc)}, at this exception's address under a "
        "different recorder identity",
        "the recorder forgets an exception once it has seen a bounded number "
        "of others, so the trace cannot say whether that is this same "
        "exception still propagating or a new one that displaced it")


def _displaced(trace, h, frame) -> Disposition:
    return Disposition(
        "ambiguous",
        f"handled at e{h.id} {_at(trace, h)} -- f{frame.id} then unwound "
        f"with {fmt_exc(frame.unwind_exc)}",
        "the trace cannot say whether that replaced this exception or is "
        f"unrelated to it; only that this one did not leave f{frame.id}")


def _unreadable_frame(trace, h, frame) -> Disposition:
    if frame is None:
        return Disposition(
            "ambiguous",
            f"handled at e{h.id} {_at(trace, h)} -- no frame recorded",
            "generators and coroutines open no frame, so there is no "
            "closed_by to say whether that handler swallowed it or re-raised")
    if frame.closed_by is None:
        return Disposition(
            "ambiguous",
            f"handled at e{h.id} {_at(trace, h)} -- f{frame.id} never closed",
            "recording stopped while that frame was still running; the trace "
            "cannot say what it did with the exception")
    return Disposition(
        "ambiguous",
        f"handled at e{h.id} {_at(trace, h)} -- f{frame.id} unwound with no "
        "captured exception",
        "the trace cannot say which exception left that frame, so it cannot "
        "say what became of this one")


def classify(trace, r, idx: Index) -> Disposition:
    """What the trace supports about one RAISE -- and nothing more."""
    key = exc_key(r.payload["exc"], r.thread_id)
    later = [x for x in idx.raises.get(key, ()) if x.id > r.id]
    bound = later[0].id if later else None
    handled = [h for h in idx.handled.get(key, ())
               if h.id > r.id and (bound is None or h.id < bound)]

    # 1. The run's own uncaught record is captured from the live escaping
    #    object, and definitively rules out SWALLOWED.
    if not later and key == idx.uncaught_key:
        return _uncaught(trace, idx, handled)

    pairs = [(h, _frame_of(trace, h)) for h in handled]

    # 2. Caught in a frame that then returned normally: it stopped here --
    #    but only if nothing raises that identity again. `except E as e:
    #    return e` closes the frame by "return" while handing the exception
    #    out of it, so a later RAISE makes both readings live and neither
    #    assertable. Checked before the later-RAISE rule so that a loop whose
    #    exception address gets reused still reaches an honest verdict rather
    #    than being reported as one exception raised twice.
    for h, frame in pairs:
        if frame is not None and frame.closed_by == "return":
            if later:
                return _stored_or_reused(trace, h, frame,
                                         later[0], idx.exact)
            # "never re-raised" is the one claim a serial cannot establish on
            # its own: a stored exception the recorder forgot comes back with
            # a fresh one. Its address and type do not change, so they are
            # what stands between this verdict and a false accusation.
            unlinked = idx.unlinked_later(r)
            if unlinked:
                return _link_lost(trace, h, frame, unlinked[0])
            return _swallowed(trace, h, frame)

    # 3. The same identity raised again -- `raise e` by name, which fires
    #    RAISE where a bare `raise` would fire the unrecorded RERAISE. Only
    #    asserted where address reuse is ruled out or implausible; see
    #    _reraised.
    if later:
        return _reraised(trace, r, handled, later[0], idx.exact)

    if not pairs:
        return _no_handler_found(trace, idx)

    # 4. Handled somewhere, but every such frame unwound. If one unwound
    #    carrying this very exception, the HANDLED was cleanup and the
    #    exception kept propagating past code we can see.
    for h, frame in pairs:
        if (frame is not None and frame.unwind_exc is not None
                and exc_key(frame.unwind_exc,
                            frame.thread_id) == key):
            return _still_in_flight(trace, idx, h, frame)

    # 5. ...or with something the recorder no longer links to this exception,
    #    which can only be a lost link or a reused address.
    #    Read as "some other exception", it would deny that this one left the
    #    frame -- the same false claim rule 2 guards against, from the far
    #    side. Ranked below rule 4 so a provable match always wins.
    for h, frame in pairs:
        if (frame is not None and frame.unwind_exc is not None
                and could_be_same(r.payload["exc"], frame.unwind_exc)):
            return _maybe_still_in_flight(trace, h, frame)

    # 6. Handled, and the frame then died of something else. Translation and
    #    "swallowed, then an unrelated failure" are indistinguishable here.
    for h, frame in pairs:
        if frame is not None and frame.unwind_exc is not None:
            return _displaced(trace, h, frame)

    return _unreadable_frame(trace, *pairs[0])


def _header(trace, idx) -> None:
    if idx.all_raises and not idx.exact:
        print("LEGACY TRACE: recorded before exceptions carried a serial, so "
              "identity here falls back to (type, message, address)")
        print("  CPython recycles addresses, so repeats below are hedged "
              "rather than resolved; re-record to get exact identity")
    if idx.incomplete:
        print("INCOMPLETE: this recording never finalized, so it has no exit "
              "status and no uncaught record")
        print("  the absence of an uncaught exception below is therefore not "
              "evidence that nothing escaped")
    if idx.uncaught is None:
        return
    origin = idx.uncaught_origin
    where = (f" raised at e{origin.id}" if origin
             else " -- no recorded RAISE carries its identity")
    print(f"uncaught: {fmt_exc(idx.uncaught)} "
          f"(exit {idx.exit_status}){where}")


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return 2
    # Parsed before any work: a trace with no raises returns early below, and
    # accepting a malformed --after there would silently answer a different
    # question than the one asked.
    after = parse_eref(args.after) if args.after else 0
    trace = Trace.open(paths.find_trace(args.run))
    idx = Index.build(trace, trace.meta)
    _header(trace, idx)
    if not idx.all_raises:
        if idx.uncaught is None and not idx.incomplete:
            print("no exceptions recorded")
        elif idx.uncaught is None:
            print("no RAISE events recorded (see INCOMPLETE above)")
        return 0

    scope = [r for r in idx.all_raises if r.id > after]
    skipped = len(idx.all_raises) - len(scope)
    if skipped:
        print(f"raised ({len(scope)} of {len(idx.all_raises)}; {skipped} "
              f"earlier raise(s) skipped by --after e{after}):")
    else:
        print(f"raised ({len(scope)}):")

    tally: dict[str, int] = {}
    shown, last = 0, after
    for r in scope:
        d = classify(trace, r, idx)
        tally[d.tag] = tally.get(d.tag, 0) + 1
        if shown < args.limit:
            print("  " + fmt_event(trace, r))
            print("    " + d.verdict)
            if d.detail:
                print("      " + d.detail)
            shown, last = shown + 1, r.id
    # Counted over every raise in scope, not just the printed ones, so the
    # tally never shrinks because a page was clipped.
    print("dispositions: " + ", ".join(f"{t} {tally[t]}" for t in TAG_ORDER
                                       if tally.get(t)))
    note = more_note(len(scope), shown,
                     f"sensorium exceptions {shlex.quote(args.run)} "
                     f"--after e{last} --limit {args.limit}")
    if note:
        print(note)
    return 0
