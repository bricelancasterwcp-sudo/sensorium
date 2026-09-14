"""What `flow` PRINTS: the rows, the footer, and the notes under it.

Split out of `flow_cmd.py` at that file's 800-line ceiling, along the seam
the material has -- the same seam `refocus_report` sits on. Nothing here
decides anything: every fact these five functions put into words was settled
before they were called, by `scan`, `gaps` and `run`. `page_gaps` is the one
that looks like a decision and is not -- it slices a list that is already
computed, so that the gap crossing a page boundary is printed with the page
it leads into rather than lost with `--after`.

`continuity_line` travels with `_print_footer`, its only caller, and
`_MAX_NAMED_GAPS`, `ROLES_SEARCHED` and `EXACT_CONTINUITY` travel with the
two of them, which are the only things that read any of the three.
Everything here is re-exported by `flow_cmd`, so a caller (or a test) that
reaches for `flow_cmd.page_gaps` still finds it, and finds the same function
object.

The import runs one way, `flow_cmd` -> here. `_print_footer` calls one name
that stays behind (`continue_cmd`, which spells the command a reader would
type next), so it imports that inside its own body, the way
`refocus_licence` already does and for the same reason: a module-level
import back would be a cycle. `Gap` and `Index` appear only in annotations,
which `from __future__ import annotations` leaves unevaluated -- so they are
named under `TYPE_CHECKING` and are never imported at run time at all.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sensorium.query.fmt import fmt_event, more_note

if TYPE_CHECKING:
    from sensorium.query.flow_cmd import Gap, Index

_MAX_NAMED_GAPS = 6
ROLES_SEARCHED = "CALL args, RETURN values and LINE local deltas"
#: The footer line for an identity that needs no corroborating.
EXACT_CONTINUITY = "continuity: exact (serial identity)"


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


def _print_footer(args, ref, idx, counts, scope, shown, gs, after,
                  exact: bool = False) -> None:
    from sensorium.query.flow_cmd import continue_cmd

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
    if exact:
        print(EXACT_CONTINUITY)
    elif gs:
        print(continuity_line(gs))
    print(f"scope: {seen} capture(s) searched across {searched} event(s) in "
          f"{ROLES_SEARCHED}")
    for note in _notes(idx, seen, trunc):
        print(note)
    last = shown[-1].event.id if shown else after
    note = more_note(len(scope), len(shown), continue_cmd(args, ref, last))
    if note:
        print(note)
