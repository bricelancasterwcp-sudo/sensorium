"""A predicate at every recorded site, and how close the run came to it.

WHAT THIS COMMAND CLAIMS
------------------------
A SITE is one recorded event in a matching frame: a CALL, carrying that
activation's arguments, or a LINE, carrying that frame's locals folded
forward. At each site the predicate is applied to the state the trace records
there, and the site lands in exactly one bucket: HIT, miss, could-not-check,
or errored. Nothing is skipped, and every bucket is counted in one tally line.

WHAT IT REFUSES TO CLAIM
------------------------
That an invariant held. It cannot: a trace holds what was recorded, and
between two recorded sites the program ran code this command never saw. So
`hits: 0` is never printed on its own. It is always accompanied by a verdict
that says which of three different things happened --

  * every recorded site was evaluated and none satisfied the predicate
    (a fact about the recording, still not a proof about the run),
  * some sites could not be evaluated, so the question is open, or
  * NOTHING was checked at all, and `hits: 0` means "could not evaluate".

-- and by the count of sites it could not check, with the reason. A user
reading "0 hits" as "the invariant held" when the truth was "I could not
check" is the single worst outcome this command has, and every design choice
below is aimed at it.

FOLDING STATE FORWARD, AND THE KEY THAT MAKES IT HONEST
-------------------------------------------------------
LINE payloads carry only the locals whose capture CHANGED. To know what was
in scope at a site, this command folds those deltas forward through the
frame. A local that goes AWAY produces no delta -- so a fold that reads
`deltas` alone keeps a deleted variable alive at its last value for the rest
of the frame, and reports a HIT on a variable that no longer exists.

The tracer emits a sibling `unbound` list for exactly this consumer, and it
is not a rare case: `del x` does it, and the implicit unbind that ends every
`except E as e:` block does it far more often. Measured on a three-pass loop
whose handler rebinds `e` to an int, ignoring `unbound` turns one true hit
into three. A LINE event may also carry EMPTY deltas and a non-empty
`unbound` -- a `del` on a line that changes nothing else -- so such an event
is a site like any other and is never skipped for having no deltas.

TRUNCATION
----------
A clipped string capture is a PREFIX; comparing it, or taking its length, is
a claim about characters the trace does not hold. Those sites are refused and
counted, not quietly answered. Container captures are unaffected: their
recorded length is exact even when the sample was capped, and nothing here
reads a `sample` key (a depth-capped capture omits it entirely).
"""
import shlex
from dataclasses import dataclass
from pathlib import Path

from sensorium import paths
from sensorium.query.expr import (CLIPPED, CONTAINER, NO_VALUE, NOT_CAPTURED,
                                  OUT_OF_SCOPE, TRUNCATED, EvalError,
                                  ExprError, NotCaptured, _Sized, compile_expr,
                                  resolve)
from sensorium.query.fmt import fmt_event, fmt_value, more_note, parse_eref
from sensorium.record.tracer import module_name_for
from sensorium.store.reader import Trace

_MAX_LISTED_CODES = 20
_MAX_LISTED_ERRORS = 5

CLAIM = (
    "a site is one RECORDED event in a matching frame: a CALL (its arguments)",
    "or a LINE (that frame's locals, folded forward and dropped again when a",
    "name goes out of scope). Whatever ran between two recorded sites",
    "was not checked, and code this run never recorded is not in this trace.",
)


def add_parser(sub) -> None:
    p = sub.add_parser("watch", help="predicate over captured state")
    p.add_argument("run")
    p.add_argument("--at", required=True, help="module:qualname or qualname")
    p.add_argument("--expr", required=True,
                   help="names, literals, one comparison, and/or/not, "
                        "arithmetic, len(name)")
    p.add_argument("--after", default=None, help="event ref to resume from")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--near", type=int, default=5,
                   help="how many near-misses to show when nothing hit")
    p.set_defaults(func=run)


# -- selecting sites -------------------------------------------------------
def _qual_matches(qualname: str, spec: str) -> bool:
    """`Pot` selects `Pot.add`, the same way `--focus` reads a qualname."""
    return qualname == spec or qualname.startswith(spec + ".")


def site_matches(code, at: str, module: str | None) -> bool:
    mod, sep, qual = at.partition(":")
    if sep:
        if qual and not _qual_matches(code.qualname, qual):
            return False
        return not mod or mod in (module, Path(code.file).stem)
    return (_qual_matches(code.qualname, at)
            or at in (module, Path(code.file).stem))


@dataclass(frozen=True)
class Site:
    """One recorded event, with the state the predicate sees there."""
    event: object
    env: dict         # name -> resolved value (or a marker saying why not)
    caps: dict        # name -> the raw capture behind it, for rendering


def _bind(env: dict, caps: dict, deltas: dict, wanted: set) -> None:
    for n, v in deltas.items():
        if n in wanted:
            env[n] = resolve(v)
            caps[n] = v


def sites_for(trace, code_ids, wanted: set) -> list[Site]:
    """Every recorded site in the matching frames, state folded forward.

    Only the predicate's own names are tracked, which bounds the copy per
    site and keeps a wide frame from carrying its whole scope into memory.
    """
    frames = sorted((f for cid in code_ids for f in trace.frames(code_id=cid)),
                    key=lambda f: f.id)
    out: list[Site] = []
    for f in frames:
        env: dict = {}
        caps: dict = {}
        call = trace.event(f.call_event_id)
        if call is not None:
            _bind(env, caps, (call.payload or {}).get("args", {}), wanted)
            out.append(Site(call, dict(env), dict(caps)))
        for e in trace.frame_events(f.id):
            if e.kind != "LINE":
                continue
            p = e.payload or {}
            _bind(env, caps, p.get("deltas", {}), wanted)
            # THE fold that makes this command honest -- see the module
            # docstring. Never conditional on there being deltas: a `del` on
            # an otherwise inert line records an empty `deltas` and this list.
            for n in p.get("unbound", []):
                env.pop(n, None)
                caps.pop(n, None)
            out.append(Site(e, dict(env), dict(caps)))
    out.sort(key=lambda s: s.event.id)
    return out


# -- applying the predicate ------------------------------------------------
@dataclass
class Outcome:
    hits: list
    near: list                    # (margin, Site), closest first
    misses: int
    unavailable: dict             # (name, reason) -> site count
    errors: list                  # (Site, EvalError)

    @property
    def evaluated(self) -> int:
        return len(self.hits) + self.misses

    @property
    def not_captured(self) -> int:
        return sum(self.unavailable.values())

    @property
    def unchecked(self) -> int:
        return self.not_captured + len(self.errors)


def evaluate(sites: list[Site], expr) -> Outcome:
    out = Outcome([], [], 0, {}, [])
    for s in sites:
        try:
            got = expr.eval(s.env)
        except NotCaptured as nc:
            key = (nc.name, nc.reason)
            out.unavailable[key] = out.unavailable.get(key, 0) + 1
            continue
        except EvalError as ee:
            out.errors.append((s, ee))
            continue
        if got:
            out.hits.append(s)
            continue
        out.misses += 1
        m = expr.margin(s.env)
        if m is not None:
            out.near.append((m, s))
    out.near.sort(key=lambda t: (t[0], t[1].event.id))
    return out


# -- rendering -------------------------------------------------------------
def _render(name: str, site: Site) -> str:
    if name not in site.env:
        return "<not in scope>"
    v = site.env[name]
    cap = site.caps.get(name) or {}
    if v is NOT_CAPTURED:
        return f"<{cap.get('type', 'object')}; no comparable value>"
    if v is TRUNCATED:
        return f"<clipped to {len(cap.get('v', ''))} chars>"
    if isinstance(v, _Sized):
        return f"<{cap.get('type', 'container')} of length {v.n}>"
    return fmt_value(cap)


def state_of(expr, site: Site) -> str:
    return "  ".join(f"{n}={_render(n, site)}" for n in sorted(expr.names))


def refocus_cmd(trace, codes) -> str:
    """The exact command that re-records this run with these frames' locals.

    Fully instantiated, including the run's own argv and any focus it already
    had: a hint carrying a literal MODULE:QUALNAME placeholder is a template,
    not an answer, and an agent reading it has to guess.
    """
    m = trace.meta
    cwd = m.get("cwd")
    root = Path(cwd).resolve() if cwd else None
    specs = []
    for c in codes:
        mod = module_name_for(c.file, root) if root else None
        specs.append(f"{mod or Path(c.file).stem}:{c.qualname}")
    parts = ["sensorium", "run"]
    for spec in [*(m.get("focus") or []), *specs]:
        parts += ["--focus", shlex.quote(spec)]
    parts += ["--", *(shlex.quote(a) for a in m.get("argv") or [])]
    cmd = " ".join(parts)
    return f"cd {shlex.quote(cwd)} && {cmd}" if cwd else cmd


def _guidance(reason: str, name: str, ever: bool, has_line: bool,
              trace, codes) -> list[str]:
    """What to actually do about a name that could not be evaluated.

    The distinction that matters most: a name recorded at OTHER sites in
    these frames is a scope fact, and telling a reader to refocus there sends
    them to re-record a run that already holds what they need.
    """
    if reason == CONTAINER:
        return ["its length was recorded and its contents only sampled; "
                "compare the length instead"]
    if reason == NO_VALUE:
        return ["only its type and repr were recorded, so there is nothing to "
                "compare; refocusing cannot change that"]
    if reason == CLIPPED:
        return ["the capture is a prefix cut at the string cap, so the value "
                "itself was never recorded",
                f"see the caps this run used with: sensorium info "
                f"{shlex.quote(trace.path.stem)}"]
    if ever:
        return ["recorded at other sites in these frames, so this is scope, "
                "not capture depth:",
                "at those sites it was not bound yet, or had gone out of "
                "scope again (`del`, or the",
                "implicit unbind that ends an `except E as e:` block)"]
    if not has_line:
        return ["no local of these frames was recorded at all -- line capture "
                "is opt-in at record time",
                "refocus and re-run: " + refocus_cmd(trace, codes)]
    return [f"this run recorded locals for these frames but never a "
            f"{name!r}; check the spelling, or widen --at"]


def print_unavailable(trace, out: Outcome, sites, codes,
                      n_sites: int) -> None:
    if not out.unavailable:
        return
    ever = {n for s in sites for n in s.caps}
    has_line = any(s.event.kind == "LINE" for s in sites)
    print(f"not captured at {out.not_captured} of {n_sites} site(s) -- the "
          "predicate could not be checked there:")
    for (name, reason), n in sorted(out.unavailable.items(),
                                    key=lambda kv: (-kv[1], kv[0])):
        print(f"  {name}: {reason.replace('NAME', name)}   [{n} site(s)]")
        for line in _guidance(reason, name, name in ever, has_line,
                              trace, codes):
            print(f"      {line}")


def print_errors(out: Outcome) -> None:
    if not out.errors:
        return
    print(f"errors: {len(out.errors)} site(s) raised while applying the "
          "predicate (neither a hit nor a miss):")
    for site, err in out.errors[:_MAX_LISTED_ERRORS]:
        print(f"  e{site.event.id}: {err}")
    extra = len(out.errors) - _MAX_LISTED_ERRORS
    if extra > 0:
        print(f"  ... {extra} further site(s) raised the same way")


def verdict(out: Outcome, n_sites: int) -> list[str]:
    if out.hits:
        return [f"verdict: SATISFIED at {len(out.hits)} of the "
                f"{out.evaluated} site(s) the predicate could be evaluated at"]
    if out.evaluated == 0:
        return ["verdict: NOTHING WAS CHECKED -- the predicate could not be "
                f"evaluated at any of the {n_sites} recorded site(s)",
                "  'hits: 0' here means 'could not evaluate', NOT 'the "
                "invariant held'"]
    if out.unchecked:
        return [f"verdict: not satisfied at any of the {out.evaluated} site(s)"
                f" that could be evaluated -- but {out.unchecked} of "
                f"{n_sites} recorded site(s) could NOT be,",
                "  so this is not a claim that the invariant held"]
    return [f"verdict: not satisfied at any of the {n_sites} recorded "
            "site(s), every one of which was evaluated",
            "  that is a fact about what was RECORDED, not a claim that the "
            "invariant held: only recorded sites were checked"]


def continue_cmd(args, **over) -> str:
    """The exact command that shows more of *this* watch."""
    opts = {"--at": args.at, "--expr": args.expr, "--limit": str(args.limit),
            "--near": str(args.near), **over}
    parts = ["sensorium", "watch", shlex.quote(args.run)]
    for flag, val in opts.items():
        parts += [flag, shlex.quote(str(val))]
    return " ".join(parts)


def print_near(trace, expr, out: Outcome, args) -> None:
    if out.hits:
        return
    if not out.near:
        if not expr.has_boundary:
            print("no near-misses: a near-miss distance is only defined for a "
                  "single numeric ordering comparison")
            print(f"  ({args.expr!r} has no boundary to approach; try one of "
                  "< <= > >= over numbers)")
        return
    shown = out.near[:max(args.near, 0)]
    print(f"near-misses -- the {len(shown)} closest approach(es); every one "
          "of them FAILED the predicate:")
    for m, s in shown:
        print(f"  margin {m:g}: {fmt_event(trace, s.event)}   "
              f"state: {state_of(expr, s)}")
    withheld = len(out.near) - len(shown)
    if withheld > 0:
        print(f"... {withheld} further near-miss(es) not shown; see them "
              f"with: {continue_cmd(args, **{'--near': len(out.near)})}")


def print_hits(trace, expr, out: Outcome, args) -> None:
    shown = out.hits[:args.limit]
    for s in shown:
        print(f"  HIT   {fmt_event(trace, s.event)}   "
              f"state: {state_of(expr, s)}")
    if not shown:
        return
    last = f"e{shown[-1].event.id}"
    note = more_note(len(out.hits), len(shown),
                     continue_cmd(args, **{"--after": last}))
    if note:
        print(note)


def _no_match(trace, args, mod_of) -> int:
    print(f"error: no recorded code matches --at {args.at!r}")
    names = sorted({f"{mod_of(c) or Path(c.file).stem}:{c.qualname}"
                    for c in trace.codes()})
    print(f"this trace recorded {len(names)} code object(s):")
    for n in names[:_MAX_LISTED_CODES]:
        print(f"  {n}")
    extra = len(names) - _MAX_LISTED_CODES
    if extra > 0:
        print(f"  ... and {extra} more (sensorium info "
              f"{shlex.quote(args.run)} lists the hot ones)")
    return 1


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return 2
    try:
        expr = compile_expr(args.expr)
    except ExprError as e:
        print(f"error: {e}")
        return 2
    after = parse_eref(args.after) if args.after else 0
    trace = Trace.open(paths.find_trace(args.run))
    m = trace.meta
    root = Path(m["cwd"]).resolve() if m.get("cwd") else None

    def mod_of(code):
        return module_name_for(code.file, root) if root else None

    codes = [c for c in trace.codes() if site_matches(c, args.at, mod_of(c))]
    if not codes:
        return _no_match(trace, args, mod_of)

    all_sites = sites_for(trace, [c.id for c in codes], expr.names)
    sites = [s for s in all_sites if s.event.id > after]
    out = evaluate(sites, expr)
    n = len(sites)

    print(f"watch {args.expr!r} at {args.at} in {trace.path.stem}")
    for line in CLAIM:
        print("  " + line)
    if m.get("incomplete"):
        print("INCOMPLETE: this recording never finalized, so it may stop "
              "mid-run")
        print("  the sites below are not all the sites this run had")
    print(f"sites: {n}   evaluated: {out.evaluated}   hits: {len(out.hits)}"
          f"   not-captured: {out.not_captured}")
    skipped = len(all_sites) - n
    if skipped:
        print(f"({skipped} earlier site(s) skipped by --after e{after})")
    for line in verdict(out, n):
        print(line)
    print_hits(trace, expr, out, args)
    print_unavailable(trace, out, sites, codes, n)
    print_errors(out)
    print_near(trace, expr, out, args)
    return 0
