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

-- and by the count of sites it could not check, with the reason. The tally
line carries every bucket (`sites` = `evaluated` + `not-captured` + `errors`)
so the arithmetic is checkable rather than trusted. A user reading "0 hits"
as "the invariant held" when the truth was "I could not check" is the single
worst outcome this command has, and every design choice below is aimed at it.

That includes a hole that short-circuiting leaves open: a name the trace has
no record of ANYWHERE is absorbed silently by `and`/`or` and never reaches
the not-captured count. `print_never_recorded` closes it, above the verdict,
and the verdict refuses to come back clean while such a name is in play.

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
import argparse
import shlex
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from sensorium import paths
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from sensorium.query.caps import print_incomplete, require
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


class _NearAlias(argparse.Action):
    """`--near`, kept as a hidden alias for `--misses` (removed in 0.8.0).

    Shares `--misses`'s `dest` so the rest of the command never branches on
    which spelling was used, and records that the alias fired: argparse's
    default store action never says which option string reached a shared
    dest, and this is the one place that can still catch it, to print the
    deprecation line exactly once in `run` rather than matching argv text
    there.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        namespace.near_alias_used = True


def add_parser(sub) -> None:
    p = sub.add_parser(
        "watch", help="predicate over captured state",
        epilog="exit: 0 yes, 1 no, 2 fix the call, 3 change the recording")
    p.add_argument("run")
    p.add_argument("--at", required=True, help="module:qualname or qualname")
    p.add_argument("--expr", required=True,
                   help="names, literals, one comparison, and/or/not, "
                        "arithmetic, len(name)")
    p.add_argument("--after", default=None, help="event ref to resume from")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--misses", type=int, default=5, dest="misses",
                   help="how many near-misses to show when nothing hit")
    # Hidden alias for one release (X9): `--near N` collided with a
    # location filter's usual meaning elsewhere in this CLI. `--misses` is
    # the real flag; `--near` only still works so an existing script does
    # not break mid-release, and `run` prints the deprecation line above
    # whenever `near_alias_used` says it fired.
    p.add_argument("--near", type=int, dest="misses", action=_NearAlias,
                   help=argparse.SUPPRESS)
    p.set_defaults(func=run, near_alias_used=False)


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


def _unframed(trace, c) -> bool:
    """Coroutine/generator code: CALL events recorded, no frame ever opened.

    One predicate for both callers below, so the note and the flag that
    rewrites the NEVER RECORDED block can never disagree about which code
    objects they are talking about -- the block's "(see the line above the
    verdict)" points at a line only this decides to print.
    """
    return (bool(trace.unframed_calls(code_id=c.id))
            and not trace.frames(code_id=c.id))


def unframed_note(trace, codes) -> list[str]:
    """Which of the `--at` matches are coroutine/generator code -- recorded
    as calls, never framed, so they contribute NO site. Returned as
    (lines, all_unframed) would be two things; callers get the lines and
    test `all_unframed_codes` separately."""
    unf = [c for c in codes if _unframed(trace, c)]
    if not unf:
        return []
    names = ", ".join(c.qualname for c in unf)
    if len(unf) == len(codes):
        return [f"--at matched only coroutine/generator code ({names}), which "
                "opens no frame in this version: watch sites are frames, so "
                "there are no sites here at all, and refocusing cannot change "
                "that"]
    return [f"{len(unf)} of the {len(codes)} matched code object(s) ({names}) "
            "are coroutine/generator code: recorded as calls, never framed, "
            "and contributed no site"]


def all_unframed_codes(trace, codes) -> bool:
    return bool(codes) and all(_unframed(trace, c) for c in codes)


def _guidance(reason: str, name: str, ever: bool, has_line: bool,
              trace, codes, all_unframed: bool = False) -> list[str]:
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
        if all_unframed:
            return ["no site exists for these code objects: coroutine/"
                    "generator code opens no frame in this version"]
        return ["no local of these frames was recorded at all -- line capture "
                "is opt-in at record time",
                "refocus and re-run: " + refocus_cmd(trace, codes)]
    return [f"this run recorded locals for these frames but never a "
            f"{name!r}; check the spelling, or widen --at"]


def print_never_recorded(ghosts: list[str],
                         all_unframed: bool = False) -> None:
    """Names the predicate needs that NO site in these frames ever bound.

    The hole short-circuiting leaves, and it defeats the rule this command is
    built on. `n > 1000 and ghost > 1` is decided entirely by `n` at every
    site where `n` is small -- logically sound, and it means a typo'd or
    never-focused conjunct is absorbed in SILENCE: the tally reports
    `not-captured: 0` and the verdict comes back as strong as this command can
    make it, with no mention of `ghost` anywhere. A predicate the reader
    believes is checking two things, checking one, and reading as maximally
    clean, is exactly the "could not evaluate" masquerading as "the invariant
    held" that everything else here is built to prevent.

    The `or` mirror is milder only by accident (a hit renders a state line
    naming the name), so it is not relied on: both are warned, above the
    verdict, and the verdict itself refuses to come back clean.
    """
    if not ghosts:
        return
    names = ", ".join(repr(g) for g in ghosts)
    print(f"NEVER RECORDED: {names} -- named by the predicate, captured at NO "
          "site in these frames")
    print("  every result below was decided WITHOUT it: nothing in this trace "
          "witnesses that name")
    if all_unframed:
        print("  there are no frames here at all: --at matched only "
              "coroutine/generator code, which opens no frame in this version "
              "(see the line above the verdict)")
    else:
        print("  either it is misspelled, or it lives in frames this run did "
              "not record")


def print_unavailable(trace, out: Outcome, sites, ever, codes,
                      n_sites: int, all_unframed: bool = False) -> None:
    if not out.unavailable:
        return
    has_line = any(s.event.kind == "LINE" for s in sites)
    print(f"not captured at {out.not_captured} of {n_sites} site(s) -- the "
          "predicate could not be checked there:")
    for (name, reason), n in sorted(out.unavailable.items(),
                                    key=lambda kv: (-kv[1], kv[0])):
        print(f"  {name}: {reason.replace('NAME', name)}   [{n} site(s)]")
        for line in _guidance(reason, name, name in ever, has_line,
                              trace, codes, all_unframed):
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


def unchecked_caveats(out: Outcome, n_sites: int) -> list[str]:
    """The buckets that make ANY verdict partial, hit or no hit.

    Named separately rather than summed: "could not be evaluated" and "raised
    while being applied" have different causes and different fixes, and a
    reader discounting a verdict needs to know which one they are looking at.

    Both paths use this. The hit path used to name only the errors, so a
    confident SATISFIED could sit above 14 of 20 sites that went unchecked --
    the same "reads cleaner than the evidence supports" failure as a phantom
    name, arriving through the other branch.
    """
    caveats = []
    if out.not_captured:
        caveats.append(f"{out.not_captured} of {n_sites} recorded site(s) "
                       "could NOT be evaluated")
    if out.errors:
        caveats.append(f"{len(out.errors)} of {n_sites} recorded site(s) "
                       "raised while the predicate was applied")
    return caveats


class Says(Enum):
    """Which of three things a verdict says, as its own value.

    The split that has to survive into the exit status is the module
    docstring's last one: `hits: 0` because every evaluated site failed
    (NOT_SATISFIED) versus `hits: 0` because nothing could be evaluated at
    all (NOTHING_CHECKED). An agent branching on the status never reaches
    the prose, so a NOTHING_CHECKED leaving as a 0 is "I could not check"
    read as "the invariant held" -- this command's worst outcome, arriving
    through the one channel the prose cannot qualify.

    A partially-checked run is NOT a fourth class. Some sites evaluated and
    some did not is still the trace answering "no" about the ones it could
    check, so it reads NOT_SATISFIED, and the count it could not check is
    carried in the caveat line rather than in the status (plan X7). Only a
    run where NOTHING evaluated has no answer to give.
    """
    SATISFIED = auto()
    NOT_SATISFIED = auto()
    NOTHING_CHECKED = auto()


# The convention, applied once. NOT_SATISFIED is the trace answering "no"
# about what it recorded; NOTHING_CHECKED is the trace unable to answer at
# all, which is fixed by recording again, not by asking differently.
STATUS = {Says.SATISFIED: ANSWERED,
          Says.NOT_SATISFIED: NEGATIVE,
          Says.NOTHING_CHECKED: UNSETTLED}


@dataclass(frozen=True)
class Verdict:
    """What the verdict says, and which of the three it is.

    The class travels WITH the lines because only `verdict` knows which
    branch it took. `run` could recover it by matching "NOTHING WAS CHECKED"
    in the printed text -- and then the exit status would depend on the
    wording of a sentence this command rewrites whenever it can be made
    clearer, silently turning a 3 back into a 0 on the next rewording. The
    same reasoning, and the same shape, as `frame._resolve`.
    """
    says: Says
    lines: list[str]


def verdict(out: Outcome, n_sites: int, ghosts: list[str]) -> Verdict:
    decided_without = ("the predicate was decided WITHOUT "
                       + ", ".join(repr(g) for g in ghosts))
    caveats = unchecked_caveats(out, n_sites)
    if out.hits:
        lines = [f"verdict: SATISFIED at {len(out.hits)} of the "
                 f"{out.evaluated} site(s) the predicate could be evaluated "
                 "at"]
        if caveats:
            lines.append("  but " + ", and ".join(caveats) + ", so these are "
                         "not necessarily every time it held")
        if ghosts:
            lines.append(("  and " if caveats else "  but ") + decided_without
                         + ", so these hits do not answer the whole predicate")
        return Verdict(Says.SATISFIED, lines)
    if out.evaluated == 0:
        return Verdict(Says.NOTHING_CHECKED, [
            "verdict: NOTHING WAS CHECKED -- the predicate could not be "
            f"evaluated at any of the {n_sites} recorded site(s)",
            "  'hits: 0' here means 'could not evaluate', NOT 'the "
            "invariant held'"])
    if ghosts:
        caveats.append(decided_without)
    if caveats:
        return Verdict(Says.NOT_SATISFIED, [
            f"verdict: not satisfied at any of the {out.evaluated} site(s)"
            f" that could be evaluated -- but " + ", and ".join(caveats)
            + ",",
            "  so this is not a claim that the invariant held"])
    return Verdict(Says.NOT_SATISFIED, [
        f"verdict: not satisfied at any of the {n_sites} recorded "
        "site(s), every one of which was evaluated",
        "  that is a fact about what was RECORDED, not a claim that the "
        "invariant held: only recorded sites were checked"])


def continue_cmd(args, **over) -> str:
    """The exact command that shows more of *this* watch."""
    opts = {"--at": args.at, "--expr": args.expr, "--limit": str(args.limit),
            "--misses": str(args.misses), **over}
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
    shown = out.near[:args.misses]
    print(f"near-misses -- the {len(shown)} closest approach(es); every one "
          "of them FAILED the predicate:")
    for m, s in shown:
        print(f"  margin {m:g}: {fmt_event(trace, s.event)}   "
              f"state: {state_of(expr, s)}")
    withheld = len(out.near) - len(shown)
    if withheld > 0:
        print(f"... {withheld} further near-miss(es) not shown; see them "
              f"with: {continue_cmd(args, **{'--misses': len(out.near)})}")


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
    # The trace answering "no": it holds code, and none of it is what --at
    # named. The listing above is what it does hold, so the next move is a
    # different --at, not a different recording.
    return NEGATIVE


def run(args) -> int:
    if args.near_alias_used:
        # Printed exactly once per invocation, above everything else this
        # command prints, regardless of how many times --near appeared or
        # what value it carried -- one alias use, one warning.
        print("sensorium: --near is deprecated; use --misses "
              "(removed in 0.8.0)", file=sys.stderr)
    for flag, val in (("--limit", args.limit), ("--misses", args.misses)):
        if val < 1:
            # `--misses 0` is refused for the same reason as `--limit 0`,
            # and for one more: near-misses are the answer when nothing hit,
            # so a flag that silently suppresses them is a way to make a run
            # look clean without changing a thing about the run.
            print(f"{flag} must be >= 1 (got {val}); "
                  "there is no useful zero-row page")
            return BAD_CALL
    try:
        expr = compile_expr(args.expr)
    except ExprError as e:
        print(f"error: {e}")
        return BAD_CALL
    after = parse_eref(args.after) if args.after else 0
    trace = Trace.open(paths.find_trace(args.run))
    refusal = require(trace, "line", "watch")
    if refusal:
        print(f"REFUSED: {refusal}")
        # UNSETTLED, not BAD_CALL: the command is spelled correctly and the
        # trace is readable -- it simply holds no LINE event, because the
        # recorder said it produces none. Nothing about the call can fix
        # that; only a recording that captures lines can.
        return UNSETTLED
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
    # Computed over the WHOLE run, never the --after page: a name recorded
    # only before the cut is a scope fact, not a name the trace never held.
    ever = {nm for s in all_sites for nm in s.caps}
    ghosts = sorted(expr.names - ever)

    print(f"watch {args.expr!r} at {args.at} in {trace.path.stem}")
    for line in CLAIM:
        print("  " + line)
    print_incomplete(trace, "the sites below are not all the sites this "
                            "run had")
    # Every bucket, so the arithmetic is checkable: sites = evaluated +
    # not-captured + errors.
    print(f"sites: {n}   evaluated: {out.evaluated}   hits: {len(out.hits)}"
          f"   not-captured: {out.not_captured}   errors: {len(out.errors)}")
    skipped = len(all_sites) - n
    if skipped:
        print(f"({skipped} earlier site(s) skipped by --after e{after})")
    for line in unframed_note(trace, codes):
        print(line)
    all_unf = all_unframed_codes(trace, codes)
    # Above the verdict on purpose: the verdict cannot be read without it.
    print_never_recorded(ghosts, all_unf)
    v = verdict(out, n, ghosts)
    for line in v.lines:
        print(line)
    print_hits(trace, expr, out, args)
    print_unavailable(trace, out, sites, ever, codes, n, all_unf)
    print_errors(out)
    print_near(trace, expr, out, args)
    # The status IS the verdict, mapped once: the sentence above and the
    # number the caller branches on must never be able to disagree.
    return STATUS[v.says]
