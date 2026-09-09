"""How many exception objects a thread remembers, and the per-thread tables
that remember them.

Split out of `tracer.py` at that file's 800-line ceiling. The retention bounds
and the two tables they bound are one subject -- the only place this recorder
holds a reference to the observed program's own objects -- and the module
docstring of `tracer.py` still states the contract they implement. `_RETAIN_MAX`
and `_CONTROL_RETAIN_MAX` are re-exported from `tracer.py` so the names the
suite already imports keep resolving.
"""

import threading

# How many exception objects one thread remembers. Every one of them is held
# by a strong reference and pins its traceback, so this is a memory bound on
# the recorder's influence, not a tuning knob: raising it links more stored
# re-raises and keeps more of the program's dead frames alive. Exceeding it is
# not a silent loss -- see the module docstring and exceptions_cmd.
_RETAIN_MAX = 64

# The same bound for CONTROL-FLOW exceptions thrown into a traced frame
# (GeneratorExit, StopIteration, StopAsyncIteration). They need a serial --
# `frame_state` calls a frame abandoned only when the RESUME's thrown serial
# EQUALS the unwind's -- but they are not exceptions any query links across a
# program: `_exc_event` records no row for them, so the only rows their serial
# can ever reach are that frame's own RESUME and unwind, written within a few
# events of each other. Minting them from the table above let 70 early-exit
# generator expressions -- `any(v > 0 for v in ...)`, ordinary code -- evict a
# stashed ValueError and degrade its later re-raise to "ambiguous". A small
# table of their own costs 16 held objects per thread and cannot touch the
# real one. It is not 1: a generator's cleanup can drop other generators, so
# several of these can be in flight at once.
_CONTROL_RETAIN_MAX = 16


def _is_control_flow(exc) -> bool:
    """True for the interpreter's own iterator/generator control-flow
    exceptions, matched by TYPE IDENTITY.

    A NAME match dropped any exception whose class merely happened to be
    called ``StopIteration`` -- a user class shadowing the builtin, unrelated
    to the iterator protocol -- with no RAISE, no HANDLED and no serial, so a
    real caught exception surfaced as ``no exceptions recorded``. ``type(exc)``
    is a C-level ``Py_TYPE`` read that cannot run a dunder; ``is`` (not
    ``in (...)``) because a hostile metaclass ``__eq__`` could raise inside a
    membership test. When the type is anything else -- including one that lies
    about its name -- the exception is RECORDED, never silently dropped.
    """
    t = type(exc)
    return t is StopIteration or t is StopAsyncIteration or t is GeneratorExit


class _ExcRefs:
    """One thread's exception identity table -- and the only place this
    recorder holds a reference to an exception object.

    `serials` maps `id(exc)` -> `(exc, serial)`, insertion-ordered, capped at
    `cap` (`_RETAIN_MAX` for a thread's real table, `_CONTROL_RETAIN_MAX` for
    its control-flow side table). Holding the object is what makes `id()` a
    sound key: the address cannot be recycled underneath us, so two distinct
    exceptions can never alias onto one serial. Weak references were tried
    first and are not an option at all -- `BaseException` does not support them
    (`TypeError: cannot create weak reference to 'ValueError' object`), and
    catching that error silently disabled the whole mechanism, which is the
    kind of quiet fallback this project bans.

    `last_exc` (the exception currently in flight) lives here too, so that
    `clear` really does release everything this recorder is holding, on
    whichever thread it is called for.
    """
    __slots__ = ("last_exc", "serials", "minted", "cap", "source",
                 "__weakref__")

    def __init__(self, cap: int = _RETAIN_MAX, source=None) -> None:
        self.last_exc = None           # exception currently in flight, if any
        self.serials: dict[int, tuple] = {}
        self.minted = 0                # monotonic per-thread serial source
        self.cap = cap                 # how many objects this table remembers
        # Where serials come from, when not from this table itself. The
        # control-flow table mints from the MAIN one so a thread never issues
        # one number twice: two tables counting separately would eventually
        # give a GeneratorExit and a real exception the same serial, and a
        # frame's `unwind_exc` would then match rows belonging to neither.
        # A plain (one-way) reference, never a back-pointer: a cycle between
        # a thread's two tables would keep both -- and every exception they
        # hold -- alive past the thread, waiting for the cycle collector.
        self.source = source

    def serial_of(self, exc) -> int | None:
        """This thread's serial for `exc`, or None if it holds none.

        `id(exc)` alone is a sound key here, with no `is` re-check needed:
        object and serial go into the table together and only ever leave
        together, so while a key is present this table holds that object and
        no other object can have its address.
        """
        held = self.serials.get(id(exc))
        return held[1] if held is not None else None

    def identify(self, exc) -> int:
        """`exc`'s serial, minting and remembering one if it is new."""
        serial = self.serial_of(exc)
        if serial is not None:
            return serial
        src = self if self.source is None else self.source
        src.minted += 1
        serial = src.minted
        self.serials[id(exc)] = (exc, serial)
        while len(self.serials) > self.cap:
            oldest, held = next(iter(self.serials.items()))
            del self.serials[oldest]
            if held[0] is self.last_exc:
                # Never forget what is arming or propagating right now. An
                # exception paused inside a `finally` is not that -- its
                # EXCEPTION_HANDLED already cleared `last_exc` -- so a long
                # enough cleanup can push it out, and the query side hedges
                # rather than reading the fresh serial as another exception.
                self.serials[oldest] = held
        return serial

    def clear(self) -> None:
        self.last_exc = None
        self.serials.clear()


class _TLS(threading.local):
    """Per-thread recorder state.

    `threading.local` calls `__init__` again on every thread that touches the
    object -- which is how each thread gets a fresh `thread_serial` and how its
    `_ExcRefs` gets registered with the tracer. A recycled OS thread id is a
    NEW Python thread with its own `threading.local` storage, so it runs this
    `__init__` again and mints a NEW serial: that is what stops two short-lived
    threads sharing one recorded identity. (Without the registry, `uninstall`
    could only ever drop the exceptions held by the thread that calls it.)
    """
    def __init__(self, next_serial, register) -> None:
        self.thread_serial: int = next_serial()   # stable, never recycled
        # id(frame) -> [frame_id, code, code_id, prev_locals, depth,
        #               in_window, suspended]
        # for every OPEN frame this recorder opened on this thread. Slot 5 is
        # `--window` membership, derived from ANCESTRY at PY_START: this code
        # is the window target, or the parent entry is in the window. It is a
        # property of the ACTIVATION, so a suspended windowed frame cannot lend
        # its membership to whatever else happens to run meanwhile. Slot 6 is
        # `suspended`: True between this frame's YIELD and the RESUME that
        # answers it. It is deliberately never written out -- not at
        # `uninstall`, not anywhere (spec D1). A frame still parked when
        # recording stops leaves NO extra row, and the reader derives
        # "suspended" from the frame's last YIELD/RESUME row, which is
        # evidence the trace already holds. A written flag would be the
        # recorder's opinion competing with that evidence, and would go
        # stale for any thread still running when uninstall ran.
        # Replaces the stack that v1 used: "the last frame I opened is the
        # caller" is stack discipline, which a coroutine resumed by the event
        # loop, a generator resumed by its consumer, and a callback from C all
        # break.
        # WHY `id(frame)` IS A SOUND KEY, now that entries suspend. Arc 1
        # could argue it from stack discipline: an ordinary frame always
        # leaves through PY_RETURN or PY_UNWIND -- both subscribed -- so its
        # entry is gone before the address can die. A suspendable frame has
        # no such guarantee from the language, and the argument is now an
        # OBSERVED one: dropping a suspended generator fires
        # PY_THROW(GeneratorExit) then PY_UNWIND, and cancelling a task fires
        # PY_THROW(CancelledError) then PY_UNWIND (spec, "Measurements",
        # facts 1-2), so the entry still leaves before the frame does. What
        # backs it up is the `entry[1] is code` re-check every reader makes
        # (`_parent_of`, `_live_entry`, `_adopt`): a recycled address can
        # only answer for a frame running the very same code object.
        # THE ONE RESIDUAL is a frame still suspended when recording stops:
        # nothing terminal ever fires for it, so its entry is simply dropped
        # at `uninstall` and the reader derives "suspended at end of
        # recording" from the last YIELD row.
        # An entry does not stay here across a suspension: at YIELD it MOVES
        # to the tracer-level `_parked` table, because the thread that
        # resumes a suspended frame need not be the one that opened it, and
        # it moves into the resuming thread's map at the first lookup that
        # misses (`Tracer._park` / `_adopt`). So this map holds the frames
        # RUNNING on this thread, `_parked` holds the suspended ones, and no
        # entry is ever in both.
        self.live: dict[int, list] = {}
        self.in_hook = False
        self.origin_recorded = False   # whether the in-flight exc got a row
        self.exc = _ExcRefs()
        # Serials for control-flow exceptions THROWN INTO a traced frame,
        # kept out of the table above; see `_CONTROL_RETAIN_MAX`.
        self.cf_exc = _ExcRefs(cap=_CONTROL_RETAIN_MAX, source=self.exc)
        # (task, serial) of the last task seen on this thread
        self.task_cache: tuple | None = None
        # Both tables, so `uninstall` releases everything this recorder holds
        # on every thread. The registry is keyed only to keep entries apart
        # and is never looked up by key, so the negative key is enough.
        register(self.thread_serial, self.exc)
        register(-self.thread_serial, self.cf_exc)
