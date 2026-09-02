"""Query-time rename detection for `diff --ignore-moves`.

A behaviour-preserving refactor that moves a function to another file
changes the `file` of every one of its events, and the causal stream is
compared on (file, qualname, kind), so the plain verdict is DIVERGED at the
first moved CALL (observed 2026-09-01 on bloomery's Python-trio split: the
verification fell back to comparing `info` counts by eye).

This module pairs code objects that LEFT one file on side A with the
same-named code objects that APPEARED in another file on side B -- and
only when that pairing is the only one possible. A qualname that is A-only
under two files, or B-only under two files, is not paired: it is listed as
unpaired and its events keep their recorded keys, so any divergence inside
it is still a divergence. Nothing here changes what is stored; the stored
fingerprints are untouched and `diff` without the flag reads them as before.

A file's own `<module>` code object is never paired: it is file identity,
not a function, and a split creates new files whose import-time frame exists
on one side BY CONSTRUCTION. Those frames are listed in `one_sided_modules`
and dropped from both compared streams -- only the `<module>` frames
themselves, so anything module-level code CALLS is still compared and an
import-time side effect still diverges.
"""
from collections import defaultdict
from dataclasses import dataclass, replace

from sensorium.record.fingerprint import Fingerprint

Key = tuple[str, str]           # (file, qualname)

MODULE = "<module>"             # the qualname CPython gives module-level code


@dataclass(frozen=True)
class Moves:
    mapping: dict[Key, Key]                 # A key -> B key, unique pairs only
    moved: list[tuple[str, str, str]]       # (qualname, file_a, file_b)
    added: list[Key]                        # B-only, not paired
    removed: list[Key]                      # A-only, not paired
    unpaired: list[str]                     # qualnames refused for ambiguity
    one_sided_modules: list[tuple[str, str]]  # ("A"|"B", file), <module> only


def detect_moves(trace_a, trace_b) -> Moves:
    """Pair A-only (file, qualname) keys with B-only ones by qualname, and
    only where that pairing is unique on BOTH sides. Everything refused --
    for ambiguity, or for having no counterpart at all -- is reported
    rather than dropped, because an unreported refusal reads as a MATCH."""
    ka = {(c.file, c.qualname) for c in trace_a.codes()}
    kb = {(c.file, c.qualname) for c in trace_b.codes()}
    only_a, only_b = ka - kb, kb - ka
    one_sided_modules = sorted(
        [("A", f) for f, q in only_a if q == MODULE]
        + [("B", f) for f, q in only_b if q == MODULE])
    by_q_a: dict[str, list[str]] = defaultdict(list)
    by_q_b: dict[str, list[str]] = defaultdict(list)
    for f, q in only_a:
        if q != MODULE:
            by_q_a[q].append(f)
    for f, q in only_b:
        if q != MODULE:
            by_q_b[q].append(f)
    mapping: dict[Key, Key] = {}
    moved, unpaired = [], []
    for q in sorted(by_q_a):
        if q not in by_q_b:
            continue
        fa, fb = by_q_a[q], by_q_b[q]
        if len(fa) == 1 and len(fb) == 1:
            mapping[(fa[0], q)] = (fb[0], q)
            moved.append((q, fa[0], fb[0]))
        else:
            # Two files could each be the destination (or the origin), and
            # picking one would hide a divergence inside the other.
            unpaired.append(q)
    paired_b = set(mapping.values())
    removed = sorted(k for k in only_a if k not in mapping and k[1] != MODULE)
    added = sorted(k for k in only_b if k not in paired_b and k[1] != MODULE)
    return Moves(mapping, moved, added, removed, unpaired, one_sided_modules)


def project(stream, moves: Moves) -> list[tuple]:
    """Drop the `<module>` steps of files that exist on one side only, then
    rewrite each remaining (file, qualname, kind, eid) step through
    `moves.mapping`; unmapped steps pass through unchanged.

    The B side is projected too, through a `Moves` whose mapping is empty:
    the dropping is symmetric (a one-sided file's frames must leave BOTH
    streams), the rewriting is not (it names A's keys with B's files)."""
    dropped = {f for _side, f in moves.one_sided_modules}
    if not moves.mapping and not dropped:
        return list(stream)
    out = []
    for file, qual, kind, eid in stream:
        if qual == MODULE and file in dropped:
            continue
        file, qual = moves.mapping.get((file, qual), (file, qual))
        out.append((file, qual, kind, eid))
    return out


def for_b(moves: Moves | None) -> Moves | None:
    """The same `Moves` as seen from the B side: one-sided module frames
    still dropped, nothing rewritten. `mapping` names A's keys with B's
    files, so applying it to B would rewrite keys that already ARE B's."""
    return None if moves is None else replace(moves, mapping={})


def hash_stream(stream) -> str:
    """The same rolling hash the recorder uses, over a query-time stream.
    Both sides of a `--ignore-moves` comparison are hashed here, never one
    side here and the other from the stored row: the recorder hashes a
    root-relative file, this hashes what `code_objects` holds."""
    fp = Fingerprint()
    for file, qual, kind, _eid in stream:
        fp.update(file, qual, kind)
    return fp.hexdigest()


MOVE_LIST_CAP = 12


def _base(file: str) -> str:
    """The file's basename: this section lists files by name, and the
    absolute path is already on the header and divergence lines."""
    return file.rsplit("/", 1)[-1]


def short(key) -> str:
    file, qual = key
    return f"{_base(file)}:{qual}"


def _listed(items, render=str) -> str:
    """`items` rendered, capped, and MARKED when the cap cut something. A
    truncated list with nothing to say it was truncated reads as the whole
    list -- the silent under-report this block exists to prevent."""
    shown = ", ".join(render(i) for i in items[:MOVE_LIST_CAP])
    over = len(items) - MOVE_LIST_CAP
    return f"{shown}, ... +{over} more" if over > 0 else shown


def print_key_line(moves: Moves | None) -> None:
    """The key a move-aware verdict was reached through, printed under the
    headers so the verdict below is never read as a comparison of the keys
    AS RECORDED. Pairing is by qualname alone -- `kind` is part of the
    comparison key, not of the criterion. No-op when not move-aware."""
    if not moves:
        return
    print(f"key: (file, qualname, kind), with {len(moves.moved)} code "
          "object(s) paired across a move by qualname -- see moves below")


def print_moves_section(moves: Moves | None) -> None:
    """The `moves:` block under a verdict; no-op when there is none, so
    every print path can call it unconditionally."""
    if not moves:
        return
    print("moves:")
    print_moves(moves)


def print_moves(moves: Moves) -> None:
    """What was paired, what was not, and why -- printed on every verdict
    under --ignore-moves, so a MATCH never hides how it was reached."""
    for qual, fa, fb in moves.moved[:MOVE_LIST_CAP]:
        print(f"  moved: {qual}  {_base(fa)} -> {_base(fb)}")
    if len(moves.moved) > MOVE_LIST_CAP:
        print(f"  ... +{len(moves.moved) - MOVE_LIST_CAP} more moved")
    if moves.removed:
        print("  removed (only in A): " + _listed(moves.removed, short))
    if moves.added:
        print("  added (only in B): " + _listed(moves.added, short))
    if moves.unpaired:
        print("  unpaired (same name in several files on one side, not "
              "paired; a divergence inside them is reported as one): "
              + _listed(moves.unpaired))
    if moves.one_sided_modules:
        only_a = [_base(f) for s, f in moves.one_sided_modules if s == "A"]
        only_b = [_base(f) for s, f in moves.one_sided_modules if s == "B"]
        print(f"  module frames not compared: "
              f"{len(moves.one_sided_modules)} (files only in B: "
              f"{', '.join(only_b) or '-'}; only in A: "
              f"{', '.join(only_a) or '-'}) -- a new file's own import-time "
              "frame exists on one side by construction; what it called is "
              "still compared")


def task_hashes(trace,
                moves: Moves | None) -> dict[int, tuple[str | None, str]]:
    """{task_id: (name, hash)} on the basis the comparison counts on: the
    STORED hash when comparing as recorded, a query-time hash over the
    projected stream under `--ignore-moves`.

    The two bases are not interchangeable -- the recorder hashed a
    root-relative file, this hashes what `code_objects` holds -- so a task
    looked up by a hash from the other basis is simply not found. Every
    site that turns a hash back into a task id therefore reads it from
    here, with the same `moves` the shapes were counted with."""
    fps = trace.task_fingerprints()
    if moves is None:
        return {t: (n, h) for t, (n, h, _c) in fps.items()}
    return {t: (n, hash_stream(project(trace.task_stream(t), moves)))
            for t, (n, _h, _c) in fps.items()}
