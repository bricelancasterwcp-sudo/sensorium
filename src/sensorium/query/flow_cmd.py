"""Value provenance: where a value was seen, and what consumed it.

WHAT THIS COMMAND CLAIMS
------------------------
``--value`` lists every recorded capture that compares EQUAL to a literal.
``--object`` lists every recorded capture at one memory address with one type.
Both are identity-based lineage over what was captured, never true dataflow
analysis: nothing here proves that one sighting produced another. Two calls
that both received 1800 may have got it from the same place or from nowhere
near each other -- the trace records values, not the edges between them.

OBJECT IDENTITY, AND WHY IT IS ONLY ALMOST AN IDENTITY
-----------------------------------------------------
``capture_value`` records ``id(obj)`` as ``oid``. That is a memory address,
and CPython recycles addresses. Measured in this project's own fixtures: three
dicts made and dropped in a plain loop share ONE address, and a ``Draft`` and
a ``Final`` instance alternate on one address four times in six lines of
entirely ordinary code. Matching on ``oid`` alone splices those unrelated
objects into a single lineage and prints it as one object's story -- the worst
failure this command can have, because the output looks exactly like a correct
answer.

So identity here is ``(oid, type)``, never ``oid`` alone. An object's type is
fixed for its life, so the pair costs nothing and it separates the most common
false splice. It is still not an identity, and the header says so on every run
rather than leaving it to this docstring.

Task 11 solved the same problem exactly for exceptions, by having the tracer
mint a monotonic serial while holding a strong reference to the object. That
does not transfer here: it works because an in-flight exception is one object
the recorder can afford to retain, bounded at 64 per thread. ``flow`` would
have to retain every object the program touches. So ``flow`` is honest instead
of exact.

WHAT THE TRACE CAN STILL CORROBORATE
------------------------------------
Between two consecutive sightings of one ``(oid, type)`` this reports what the
trace supports, and only that:

  * ADDRESS REUSED -- some capture strictly in between records a DIFFERENT
    type at this same address. Two live objects never share an address, so the
    earlier object was already freed by then: the sightings on either side are
    provably different objects. That is a hard fact and it is printed loudly.

  * NEW OBJECT -- a constructor for this type ran ON this address inside the
    gap: a ``T.__init__`` whose receiver is here, or a ``T.__new__`` that
    returned here. Ordinarily that means the object seen afterwards was born
    at that moment, and it is the one signal that catches a same-type reuse,
    which ADDRESS REUSED cannot see and a spanning binding actively hides. It
    is measured, not hypothetical: a plain four-iteration loop building one
    object per pass puts two of them on one address, and without this the
    whole run reads as a single lineage with ``Node.__init__`` sitting
    unremarked in the middle of it.

    Only the RECEIVER counts, never another argument: ``Wrapper.__init__(
    self, payload)`` passes an existing object into a constructor, and reading
    that as "payload was born here" would split one real object's lineage and
    assert two -- the mirror of the bug this catches.

    It is reported as strong evidence rather than proof, because "re-running a
    constructor on a live object is pathological" is false in one ordinary
    idiom. Measured: the textbook caching ``__new__``

        class Config:
            _inst = None
            def __new__(cls):
                if cls._inst is None: cls._inst = super().__new__(cls)
                return cls._inst
            def __init__(self): self.n = 1

    records ``Config.__new__`` returning ONE address twice and
    ``Config.__init__`` running on that same live object twice, with
    ``a is b`` true. Calling that two objects would be exactly the false
    claim this command exists to avoid, so when the trace records a
    ``__new__`` that can hand back a live instance of this type, the line says
    the trace cannot tell rather than asserting a split. A metaclass
    ``__call__`` doing the same is not detected and is named in the line's
    residual instead.

  * spanned by fN -- a recorded argument or local of a frame that was open
    across the whole gap was bound to this address before it, and NO DIFFERING
    CAPTURE of that name was recorded during it. A live frame's local holds a
    strong reference, so for as long as the name really did hold the address
    it could not have been recycled underneath it.

    This is evidence, not proof, and the exact residual matters. The tracer
    emits a LINE delta by comparing CAPTURES, not objects
    (``tracer.py``: ``if prev.get(name) != cap``). A capture carries the
    address, so rebinding a name to a different object almost always changes
    it -- but rebinding to a NEW object that took the same address and has
    equal content produces an identical capture and therefore NO delta and no
    LINE event at all. A loop that frees and rebuilds an equal object reaches
    that in ordinary code, and ADDRESS REUSED cannot catch it because the type
    is the same. ``--window`` can also gate LINE recording off for part of a
    frame's life. So "no differing capture recorded" is exactly what is
    claimed, and the header caveat says what it does not rule out. A frame
    with no line capture at all is weaker still, and its line says so.

  * unwitnessed -- none of the above. Nothing in the trace holds the address
    across the gap, so the object may have died there and the later sighting
    may be a different object at the same address. These are counted and named
    in the footer rather than smoothed over.

Ranked in that order, strongest evidence first: a proven reuse outranks a
constructor, and either outranks a binding -- a binding that appears to span a
constructor is precisely the case where the binding is wrong.

Only top-level name bindings count as holders. A container captured holding the
object is a real reference too, but the trace does not record whether that
container was mutated in between, so it is not used as evidence.

WHAT IS SEARCHED
----------------
CALL args, RETURN values and LINE local deltas -- every place a value is
captured. The ``unbound`` names on a LINE event are deliberately NOT searched:
they name locals that went out of scope at that step, and listing one as a
sighting would assert a binding that had just ended.

A capture can be smaller than the value it stands for: over-cap containers,
depth-capped containers (which carry no ``sample`` key at all) and clipped
strings all carry ``trunc``. Those parts were never recorded and cannot be
searched, so the footer says how many were passed over instead of implying the
list is complete. A clipped string is never reported as equal to anything: the
real string is strictly longer than what was recorded, so it cannot be equal to
the literal it was compared against.
"""
import re
import shlex
from dataclasses import dataclass

from sensorium import paths
from sensorium.query.caps import require
from sensorium.query.fmt import fmt_event, fmt_value, more_note, parse_eref
from sensorium.store.reader import Trace

CONTAINER_KINDS = ("obj", "seq", "map")
ROLES_SEARCHED = "CALL args, RETURN values and LINE local deltas"
IDENTITY_CAVEAT = (
    "identity-based lineage, not true dataflow analysis",
    "object identity is the memory address plus type; CPython recycles "
    "addresses,",
    "so a sighting after the object was freed may be a different object that "
    "reused it",
    "a 'spanned by' line below is evidence, not proof: local deltas compare "
    "captures, so a name",
    "rebound to a new object at the same address with equal content records "
    "no change at all",
)
_NUMERIC = re.compile(r"[+-]?(\d[\d_]*\.?[\d_]*|\.\d[\d_]*)([eE][+-]?\d+)?")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_MAX_OTHER_REFS = 5
_MAX_NAMED_GAPS = 6
_CTORS = (".__init__", ".__new__")


@dataclass(frozen=True)
class ObjTarget:
    """One object, as well as this trace can name one."""
    oid: int
    type: str


@dataclass(frozen=True)
class Sighting:
    event: object
    labels: tuple           # ("arg items[1].grams", "return", ...)


@dataclass(frozen=True)
class Binding:
    """A name recorded as holding the target address over [start, end)."""
    frame_id: int
    name: str
    start: int
    end: int
    lines: bool             # the frame recorded LINE events at all


@dataclass(frozen=True)
class Gap:
    a: int
    b: int
    reuse: tuple | None     # (event id, the other type seen at this address)
    born: tuple | None      # (event id, ctor qualname, caching __new__?)
    held: Binding | None


def parse_literal(s: str):
    """The literal `--value` names.

    Digits are a number, so quote to force a string (`--value "'1800'"`) --
    otherwise a string of digits would be unsearchable. Words that `float()`
    happens to accept ("nan", "inf", "infinity") stay strings: silently
    turning a search for the word into a search for the float would report
    zero sightings for a value the trace may well hold.
    """
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        return s[1:-1]
    if s == "None":
        return None
    if s in ("True", "False"):
        return s == "True"
    if not _NUMERIC.fullmatch(s):
        return s
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def matches(cap: dict, target) -> bool:
    """Whether one capture is a sighting of `target`.

    Bools and numbers are kept apart on the capture's own kind, because
    `True == 1` in Python and a trace holding both must not report one as a
    sighting of the other. A clipped string never matches: what was recorded
    is a strict prefix of the real string, so the real string is longer than
    -- and therefore unequal to -- anything it is compared with.
    """
    k = cap.get("k")
    if isinstance(target, ObjTarget):
        return (k in CONTAINER_KINDS and cap.get("oid") == target.oid
                and cap.get("type") == target.type)
    if target is None:
        return k == "none"
    if isinstance(target, bool):
        return k == "bool" and cap.get("v") == target
    if isinstance(target, (int, float)):
        return k == "num" and cap.get("v") == target
    return k == "str" and not cap.get("trunc") and cap.get("v") == target


def _key_step(kcap: dict) -> str:
    """How to render "the value under this key" in a path label."""
    v = kcap.get("v")
    if (kcap.get("k") == "str" and not kcap.get("trunc")
            and isinstance(v, str) and _IDENT.fullmatch(v)):
        return f".{v}"
    return f"[{fmt_value(kcap)}]"


def _walk(v: dict, path: str = ""):
    """Every capture inside `v`, with the path that names it.

    A depth-capped container omits `sample` entirely rather than supplying an
    empty list, so it is always read with `.get` -- never `v["sample"]`.
    """
    yield path, v
    k = v.get("k")
    if k == "seq":
        for i, x in enumerate(v.get("sample", [])):
            yield from _walk(x, f"{path}[{i}]")
    elif k == "map":
        for i, pair in enumerate(v.get("sample", [])):
            kcap, vcap = pair
            yield from _walk(kcap, f"{path}[key {i}]")
            yield from _walk(vcap, path + _key_step(kcap))


def find_in_value(v: dict, target, path: str = "") -> list[str]:
    """The paths inside `v` at which `target` was captured."""
    return [p for p, cap in _walk(v, path) if matches(cap, target)]


def roles(e) -> list[tuple[str, dict]]:
    """The (role, capture) pairs an event records.

    LINE `unbound` names are not roles: they name locals that went OUT of
    scope at this step, and a sighting is a claim about a live binding.
    """
    p = e.payload or {}
    if e.kind == "CALL":
        return [(f"arg {n}", v) for n, v in p.get("args", {}).items()]
    if e.kind == "RETURN":
        v = p.get("value")
        return [("return", v)] if v is not None else []
    if e.kind == "LINE":
        return [(f"local {n}", v) for n, v in p.get("deltas", {}).items()]
    return []


def scan(events, target) -> tuple[list[Sighting], int, int, int]:
    """(sightings, events searched, captures searched, truncated captures)."""
    found: list[Sighting] = []
    searched = seen = trunc = 0
    for e in events:
        pairs = roles(e)
        if pairs:
            searched += 1
        labels = []
        for role, v in pairs:
            for path, cap in _walk(v):
                seen += 1
                if cap.get("trunc"):
                    trunc += 1
                if matches(cap, target):
                    labels.append(role + path)
        if labels:
            found.append(Sighting(e, tuple(labels)))
    return found, searched, seen, trunc


class Index:
    """Every event read once, plus the lookups the gap analysis needs."""

    def __init__(self, trace) -> None:
        self.trace = trace
        self.events = trace.events()
        self.by_id = {e.id: e for e in self.events}
        self.by_frame: dict[int, list] = {}
        for e in self.events:
            if e.frame_id is not None:
                self.by_frame.setdefault(e.frame_id, []).append(e)
        self.last_id = self.events[-1].id if self.events else 0
        self.has_line = any(e.kind == "LINE" for e in self.events)
        self.incomplete = bool(trace.meta.get("incomplete"))


def _frame_end(idx: Index, f) -> int:
    """The first event id at which `f` is no longer known to be open.

    An unwound frame records no end event, so the last event recorded inside
    it is used: that is a lower bound on how long it lived, which understates
    the frame's reach rather than overstating what it can witness.
    """
    if f.return_event_id is not None:
        return f.return_event_id + 1
    if f.closed_by is None:
        return idx.last_id + 1              # never closed: open to the end
    evs = idx.by_frame.get(f.id, ())
    return (evs[-1].id if evs else f.call_event_id) + 1


def bindings(idx: Index, target: ObjTarget) -> list[Binding]:
    """Every recorded name binding that held the target address.

    Only top-level bindings: a container that was captured holding the object
    also holds a reference, but the trace cannot say it was never mutated.
    """
    out: list[Binding] = []
    for f in idx.trace.frames():
        evs = idx.by_frame.get(f.id, [])
        lines = any(e.kind == "LINE" for e in evs)
        steps: list[tuple[int, dict, tuple]] = []
        call = idx.by_id.get(f.call_event_id)
        if call is not None:
            steps.append((call.id, (call.payload or {}).get("args", {}), ()))
        for e in evs:
            if e.kind == "LINE":
                p = e.payload or {}
                steps.append((e.id, p.get("deltas", {}),
                              tuple(p.get("unbound", ()))))
        held: dict[str, int] = {}
        for eid, binds, gone in steps:
            for name, cap in binds.items():
                if matches(cap, target):
                    held.setdefault(name, eid)
                elif name in held:
                    out.append(Binding(f.id, name, held.pop(name), eid, lines))
            for name in gone:
                if name in held:
                    out.append(Binding(f.id, name, held.pop(name), eid, lines))
        end = _frame_end(idx, f)
        for name, start in held.items():
            out.append(Binding(f.id, name, start, end, lines))
    return out


def address_reuses(idx: Index, target: ObjTarget) -> dict[int, str]:
    """event id -> a DIFFERENT type captured at the target's address.

    Two live objects never share an address, so any such capture proves the
    target object had already been freed by then.
    """
    out: dict[int, str] = {}
    for e in idx.events:
        for _role, v in roles(e):
            for _path, cap in _walk(v):
                if (cap.get("k") in CONTAINER_KINDS
                        and cap.get("oid") == target.oid
                        and cap.get("type") != target.type):
                    out.setdefault(e.id, cap["type"])
    return out


def constructions(trace, idx: Index, target: ObjTarget) -> dict[int, str]:
    """event id -> the constructor recorded running ON the target's address.

    A `T.__init__` whose RECEIVER is at this address, or a `T.__new__` that
    RETURNED it. Only the receiver -- the first parameter, which is what
    `capture_value` records first because the tracer walks `co_varnames` in
    order. Any other argument is an existing object being handed *into* a
    constructor (`Wrapper.__init__(self, payload)`), and reading that as
    "payload was born here" would split one real object's lineage.

    `__new__` is read from its RETURN, not its CALL: at call time the instance
    does not exist yet and the first argument is the class.
    """
    out: dict[int, str] = {}
    for e in idx.events:
        if e.code_id is None:
            continue
        q = trace.code(e.code_id).qualname
        p = e.payload or {}
        if e.kind == "CALL" and q.endswith(".__init__"):
            recv = next(iter((p.get("args") or {}).values()), None)
            if recv is not None and matches(recv, target):
                out[e.id] = q
        elif e.kind == "RETURN" and q.endswith(".__new__"):
            if p.get("value") is not None and matches(p["value"], target):
                out[e.id] = q
    return out


def caching_new(trace, idx: Index, target: ObjTarget) -> bool:
    """Whether this run defines a `__new__` that hands back instances of the
    target's type -- the one ordinary idiom in which a constructor running on
    a live object does NOT mean a new object.

    Measured on the textbook caching singleton: `Config.__new__` returns one
    address twice and `Config.__init__` then runs on that same live object
    twice. Without this check the two would be reported as different objects,
    which is the false claim this command exists to avoid.
    """
    for e in idx.events:
        if e.kind != "RETURN" or e.code_id is None:
            continue
        if not trace.code(e.code_id).qualname.endswith(".__new__"):
            continue
        v = (e.payload or {}).get("value") or {}
        if v.get("type") == target.type:
            return True
    return False


def gaps(sights: list[Sighting], binds: list[Binding], reuses: dict[int, str],
         ctors: dict[int, str] = {}, cached: bool = False) -> list[Gap]:
    out = []
    for prev, nxt in zip(sights, sights[1:]):
        a, b = prev.event.id, nxt.event.id
        reuse = next(((eid, t) for eid, t in sorted(reuses.items())
                      if a < eid < b), None)
        # `a < c <= b`, not `< b`: the constructor is very often the later
        # SIGHTING itself -- `Node.__init__(self=Node#A)` is both a capture at
        # the address and the proof that what is there now was just built. Its
        # presence at `a` says nothing, since that is the object already seen.
        born = None if reuse else next(
            ((eid, q, cached) for eid, q in sorted(ctors.items())
             if a < eid <= b), None)
        held = None
        if reuse is None and born is None:
            # `end > b`, not `>=`: a binding observed ending exactly at the
            # later sighting is not read as having held the address across
            # the gap. It very likely did -- but that turns on what happened
            # inside the single line that rebound it, which the trace does
            # not record, and an under-claimed witness costs a hedge while an
            # over-claimed one costs a false "same object".
            cands = [x for x in binds if x.start <= a and x.end > b]
            # A frame with line capture is the better witness of the two: a
            # rebinding that CHANGED the capture would have been recorded
            # there. It is not a guarantee -- an identical re-capture records
            # nothing anywhere -- only strictly more than a frame that could
            # not have recorded a rebinding at all.
            held = min(cands, key=lambda x: (not x.lines, x.start),
                       default=None)
        out.append(Gap(a, b, reuse, born, held))
    return out


def _witness(g: Gap):
    return (g.held.frame_id, g.held.name, g.held.start) if g.held else None


def held_line(h: Binding, a: int, b: int) -> str:
    """What a covering binding supports -- stated as the fact it is.

    Never "held by" and never "no rebinding recorded": both are literally
    true of the trace and both read as affirmative continuity evidence, and a
    reader skimming rows meets this line without the header. Deltas compare
    captures,
    so a name rebound to a new object at the same address with equal content
    records nothing to see. What the trace supports is that no DIFFERING
    capture of the name was recorded, and that is what is printed.
    """
    span = f"spanned by f{h.frame_id} across e{a}..e{b}: {h.name!r} bound " \
           f"at e{h.start}"
    if h.lines:
        return (span + f", no differing capture of {h.name!r} recorded "
                f"through e{b}")
    return (span + f"; f{h.frame_id} has no line capture at all, so nothing "
            f"there could have recorded a rebinding before e{b}")


def gap_lines(gs: list[Gap]) -> dict[int, str]:
    """The annotation to print after sighting `i`, for the gaps worth one.

    A run of consecutive gaps held by the SAME binding is one fact, not one
    per gap: it is emitted once, at the end of the run, naming the whole span
    it covers. Unwitnessed gaps get no line here -- there is nothing to say
    about them beyond the count and the named list in the footer.
    """
    out: dict[int, str] = {}
    for i, g in enumerate(gs):
        if g.reuse:
            eid, typ = g.reuse
            out[i] = (f"ADDRESS REUSED between e{g.a} and e{g.b}: e{eid} "
                      f"captured a {typ} at this address -- two live objects "
                      "never share one, so these are different objects")
        elif g.born:
            eid, q, cached = g.born
            out[i] = (
                f"CONSTRUCTOR RAN between e{g.a} and e{g.b}: e{eid} is {q} on "
                f"this address, but this run defines {q.rsplit('.', 1)[0]}"
                ".__new__, which hands back instances of this type -- "
                "a caching __new__ re-runs __init__ on a LIVE object, so "
                "the trace cannot say a new one was born here"
                if cached else
                f"NEW OBJECT between e{g.a} and e{g.b}: e{eid} is {q} on this "
                "address -- an object was constructed there, so these are "
                "different objects unless a constructor was re-run on a live "
                "one (a caching __new__ or metaclass __call__ does that)")
        elif g.held:
            start = i
            while start > 0 and _witness(gs[start - 1]) == _witness(g):
                start -= 1
            # Keyed on where the run BEGINS, which is what collapses it: each
            # further gap of the run overwrites the same entry, extending the
            # span, and the line ends up announced once at the sighting that
            # established the binding.
            out[start] = held_line(g.held, gs[start].a, g.b)
    return out


def continuity_line(gs: list[Gap]) -> str:
    unwit = [g for g in gs
             if g.reuse is None and g.born is None and g.held is None]
    named = ", ".join(f"e{g.a}->e{g.b}" for g in unwit[:_MAX_NAMED_GAPS])
    extra = len(unwit) - _MAX_NAMED_GAPS
    if named:
        named = f" ({named}{f', +{extra} more' if extra > 0 else ''})"
    parts = [f"{sum(1 for g in gs if g.held)} gap(s) spanned by a recorded "
             "binding", f"{len(unwit)} unwitnessed{named}"]
    reused = sum(1 for g in gs if g.reuse)
    if reused:
        parts.append(f"{reused} crossed a proven address reuse")
    born = sum(1 for g in gs if g.born)
    if born:
        parts.append(f"{born} crossed a recorded construction")
    return "continuity: " + ", ".join(parts)


def resolve_object(trace, idx: Index, spec: str):
    """(target, canonical ref, resolution note, error)."""
    ref, sep, name = spec.rpartition(":")
    if not sep or not ref or not name:
        return None, None, None, (
            f"object spec must be e<id>:<name> or <qualname>:<name>; "
            f"got {spec!r}")
    note = None
    if ref[0] == "e" and ref[1:].isdigit():
        ev = idx.by_id.get(int(ref[1:]))
        if ev is None:
            return None, None, None, f"no event {ref} in this trace"
    else:
        calls = [e for e in idx.events
                 if e.kind == "CALL" and e.code_id is not None
                 and trace.code(e.code_id).qualname == ref]
        if not calls:
            return None, None, None, f"no CALL of {ref!r} was recorded"
        ev = calls[0]
        note = (f"resolved {spec!r} at e{ev.id} -- the first of {len(calls)} "
                f"recorded CALL(s) of {ref}")
        if len(calls) > 1:
            others = [f"e{c.id}" for c in calls[1:1 + _MAX_OTHER_REFS]]
            extra = len(calls) - 1 - len(others)
            note += ("; others: " + ", ".join(others)
                     + (f" (+{extra} more)" if extra else ""))
    v, at, err = _capture_at(trace, idx, ev, name)
    if err:
        return None, None, None, err
    if at is not ev and note:
        note += f"; its return is captured at e{at.id}"
    if v.get("k") not in CONTAINER_KINDS:
        return None, None, None, (
            f"{name!r} at e{at.id} is a primitive ({fmt_value(v)}) and has no "
            f"identity to follow; use --value {fmt_value(v)}")
    return ObjTarget(v["oid"], v["type"]), f"e{at.id}:{name}", note, None


def _capture_at(trace, idx: Index, ev, name: str):
    """(capture, the event carrying it, error).

    A qualname resolves to a CALL, which is where args live but never a
    return value -- so `<qualname>:return` follows that activation's frame to
    its RETURN rather than reporting the name as uncaptured.
    """
    p = ev.payload or {}
    v = p.get("args", {}).get(name) or p.get("deltas", {}).get(name)
    if v is not None:
        return v, ev, None
    if name == "return":
        if p.get("value") is not None:
            return p["value"], ev, None
        ret = _return_of(trace, idx, ev)
        if ret is not None and (ret.payload or {}).get("value") is not None:
            return ret.payload["value"], ret, None
    avail = list(p.get("args", {})) + list(p.get("deltas", {}))
    where = (f"; captured there: {', '.join(avail)}" if avail
             else "; that event captured no named values")
    return None, ev, f"{name!r} is not captured at e{ev.id}{where}"


def _return_of(trace, idx: Index, ev):
    """The RETURN event of the activation this CALL opened, if it returned."""
    if ev.kind != "CALL":
        return None
    f = trace.frame_containing(ev.id)
    if f is None or f.return_event_id is None:
        return None
    return idx.by_id.get(f.return_event_id)


def continue_cmd(args, ref: str | None, last: int) -> str:
    """The exact command that shows the next page of *this* flow."""
    sel = (f"--object={shlex.quote(ref)}" if ref is not None
           else f"--value={shlex.quote(args.value)}")
    return (f"sensorium flow {shlex.quote(args.run)} {sel} "
            f"--limit {args.limit} --after e{last}")


def add_parser(sub) -> None:
    p = sub.add_parser("flow", help="provenance of a value or an object")
    p.add_argument("run")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--value", default=None,
                   help="literal matched by equality; quote to force a "
                        "string, as in \"'1800'\"")
    g.add_argument("--object", default=None,
                   help="e<id>:<name>, where <name> was captured at that "
                        "event (a CALL's argument, a LINE's local); or "
                        "<qualname>:<name>, which resolves to that "
                        "function's first CALL and so names one of its "
                        "ARGUMENTS -- plus <qualname>:return for what that "
                        "activation returned")
    p.add_argument("--after", default=None, help="event ref to resume from")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=run)


def _header(trace, idx: Index, args) -> tuple:
    """(target, canonical ref, header lines, error)."""
    if args.object is not None:
        target, ref, note, err = resolve_object(trace, idx, args.object)
        if err:
            return None, None, None, err
        head = [f"flow of object #{target.oid} ({target.type}) in "
                f"{trace.path.stem}"]
        head += ["  " + s for s in IDENTITY_CAVEAT]
        if note:
            head.append("  " + note)
        return target, ref, head, None
    target = parse_literal(args.value)
    return target, None, [
        f"flow of {target!r} ({type(target).__name__}) in {trace.path.stem}",
        "  captured-value equality, not true dataflow analysis: the trace "
        "records values, not the edges between them"], None


def _notes(idx: Index, seen: int, trunc: int) -> list[str]:
    out = []
    if trunc:
        out.append(f"note: {trunc} of {seen} capture(s) searched were "
                   "truncated (over-cap or depth-capped containers, or "
                   "clipped strings); the parts not recorded could not be "
                   "compared, so a value present only there is not listed")
    if not idx.has_line:
        out.append("note: this run recorded no LINE events, so no local was "
                   "ever captured; a value that only lived in a local between "
                   "call and return is not in this trace (re-record with "
                   "--focus MODULE[:QUALNAME])")
    return out


def page_gaps(all_gaps: list[Gap], start: int, shown: int) -> tuple:
    """(gaps this page must account for, gaps it can annotate, lead offset).

    `start` is the index in the full sighting list of this page's first row.
    A page after the first has a gap LEADING INTO its first row -- the one
    crossing the page boundary -- which is as much part of its story as any
    gap between its own rows: on page 2 of a lineage split by an ADDRESS
    REUSED, that gap is the whole point. So it is annotated above the first
    row and counted in this page's footer, instead of existing only in the
    previous page's output.
    """
    lead = 1 if start else 0
    first = start - lead
    end = start + max(shown - 1, 0)
    return all_gaps[first:], all_gaps[first:max(end, first + lead)], lead


def _print_rows(trace, shown, notes: dict, lead: int) -> None:
    if lead and 0 in notes:
        print("  " + notes[0])          # the gap crossing into this page
    for i, s in enumerate(shown):
        print(f"  {fmt_event(trace, s.event)}   [{', '.join(s.labels)}]")
        if lead + i in notes:
            print("  " + notes[lead + i])


def _print_footer(args, ref, idx, counts, scope, shown, gs, after) -> None:
    found, searched, seen, trunc = counts
    # Counted over every sighting in scope, never over the printed page: a
    # total that shrank with --limit would be a false fact about the run.
    tail = ""
    if len(shown) < len(scope):
        tail += f" (showing {len(shown)})"
    skipped = found - len(scope)
    if skipped:
        tail += f" ({skipped} earlier sighting(s) skipped by --after e{after})"
    print(f"sightings: {len(scope)} event(s), "
          f"{sum(len(s.labels) for s in scope)} capture(s){tail}")
    if gs:
        print(continuity_line(gs))
    print(f"scope: {seen} capture(s) searched across {searched} event(s) in "
          f"{ROLES_SEARCHED}")
    for note in _notes(idx, seen, trunc):
        print(note)
    last = shown[-1].event.id if shown else after
    note = more_note(len(scope), len(shown), continue_cmd(args, ref, last))
    if note:
        print(note)


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return 2
    after = parse_eref(args.after) if args.after else 0
    trace = Trace.open(paths.find_trace(args.run))
    refusal = ((require(trace, "object_identity", "flow --object")
                if args.object is not None else None)
               or require(trace, "line", "flow"))
    if refusal:
        print(f"REFUSED: {refusal}")
        return 2
    idx = Index(trace)
    target, ref, head, err = _header(trace, idx, args)
    if err:
        print(f"error: {err}")
        return 1
    if idx.incomplete:
        print("INCOMPLETE: this recording never finalized, so it may stop "
              "mid-run")
        print("  what is missing below is not evidence about the rest of the "
              "run")
    for line in head:
        print(line)

    found, searched, seen, trunc = scan(idx.events, target)
    scope = [s for s in found if s.event.id > after]
    shown = scope[:args.limit]
    # Gaps are computed over EVERY sighting, then sliced to the page, so the
    # one crossing the page boundary is not lost with --after.
    all_gaps = (gaps(found, bindings(idx, target), address_reuses(idx, target),
                     constructions(trace, idx, target),
                     caching_new(trace, idx, target))
                if isinstance(target, ObjTarget) else [])
    counted, visible, lead = page_gaps(all_gaps, len(found) - len(scope),
                                       len(shown))
    _print_rows(trace, shown, gap_lines(visible), lead)
    _print_footer(args, ref, idx, (len(found), searched, seen, trunc),
                  scope, shown, counted, after)
    return 0
