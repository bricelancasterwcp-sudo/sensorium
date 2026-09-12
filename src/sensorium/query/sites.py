"""One recorded site: how a reader names it, and how a reader is shown it.

A SITE is a code object -- a file and a qualname -- and three commands have
to agree about how it is written down: `watch --at` reads a spelling from
the command line, `watch`'s no-match listing and its re-record guidance
write one back, and `sensorium ts run --focus` (a different program, in a
different language) reads one before a run. A reader who focused a function
and then asks about it types the SAME characters both times, or the second
command answers "no recorded code matches" about the function they just
recorded.

So the spelling lives here, once, keyed on the trace's own vocabulary:

  * `"module"` -- Python's dotted module name, derived from the run's root,
    which is what `watch` has always printed and what Rust's listings quote
    (plan P8: the design's `"stem"` for Rust would move a closed record's
    bytes for no gain).
  * `"rel"` -- the path relative to the invocation's root, which is what a
    TypeScript `--focus` is typed with and what `meta.focus_matched`
    records.

WHAT `--at` ACCEPTS, AND WHY IT IS WIDER THAN WHAT IT PRINTS
------------------------------------------------------------
Matching is deliberately wider than spelling: the file half of a spec may
be the dotted module, the stem, the basename or the root-relative path, in
every language. That is additive -- nothing that matched before stops
matching -- and it is what makes every `--focus` spelling an `--at`
spelling. It stays a real boundary all the same: `lib` is a directory,
`src/cache.ts` is a path this trace does not hold, and neither selects
`src/lib/cache.ts`. Answering about a file the reader did not name is worse
than refusing, because the answer looks right.

TWO IMPLEMENTATIONS OF ONE RULE, ON PURPOSE
-------------------------------------------
`typescript/src/focus.mjs` applies the same rule to source before a run;
this applies it to a recorded trace after one. They cannot be one function
-- they are in different languages and see different inputs -- so they are
held to one example table instead,
`typescript/test/fixtures/site-spellings.json`, which a JS test and vector
`v39-site-spellings` both read (design 2026-09-11 section 4.3, ruling R7).
"""
import shlex
from pathlib import Path

from sensorium.query.vocab import terms
from sensorium.record.tracer import module_name_for


def _anchor(trace) -> Path | None:
    """The directory every relative path in this trace is relative to.

    `root` is the invocation's, written by the TypeScript driver because
    every `rel` in that trace -- the fingerprint's paths, the test file, a
    `focus_matched` entry -- was made relative to it (plan P9); `cwd` is
    what the Python recorder has always had. A trace with neither can still
    be matched by stem and basename, which need no anchor at all.
    """
    root = trace.meta.get("root") or trace.meta.get("cwd")
    return Path(root).resolve() if root else None


def _relative(file: str, anchor: Path | None) -> str | None:
    """This file as the invocation named it, or None if it lies outside."""
    if anchor is None:
        return None
    try:
        return Path(file).resolve().relative_to(anchor).as_posix()
    except ValueError:
        return None


def _rel_site(trace, code) -> str:
    rel = _relative(code.file, _anchor(trace))
    # The basename is the honest fallback for a file outside the root (or a
    # trace that records none): it is still a spelling `--at` accepts, and
    # it never claims a path this recording cannot support.
    return f"{rel or Path(code.file).name}:{code.qualname}"


def _module_site(trace, code) -> str:
    anchor = _anchor(trace)
    mod = module_name_for(code.file, anchor) if anchor else None
    return f"{mod or Path(code.file).stem}:{code.qualname}"


_SPELLERS = {"rel": _rel_site, "module": _module_site}


def spell_site(trace, code) -> str:
    """`<file>:<qualname>`, in this recorder's own spelling.

    Strict, like `vocab.terms` itself: a `site_spelling` no speller answers
    for is a programming error, not a trace a user can produce -- the
    vocabulary table is closed and `tests/test_vocab.py` pins every
    column's word.
    """
    return _SPELLERS[terms(trace).site_spelling](trace, code)


def file_names(trace, code) -> set[str]:
    """Every spelling of this code object's FILE that `--at` accepts."""
    path = Path(code.file)
    anchor = _anchor(trace)
    names = {path.stem, path.name}
    if anchor is not None:
        names.add(module_name_for(code.file, anchor))
        names.add(_relative(code.file, anchor))
    names.discard(None)
    return names


def _qual_matches(qualname: str, spec: str) -> bool:
    """`Pot` selects `Pot.add`, and `Counter` selects `Counter::new`.

    A prefix counts only where it ends at a BOUNDARY -- Python's `.` or
    Rust's `::` -- or `--at Counter` would quietly answer about
    `Counters::new`, a different function the reader never named. One rule
    holding both separators, and no `lang` branch anywhere near it: `watch`
    takes the qualname its own recorder printed (design 2026-09-06 §4.1).
    JavaScript's boundary is `.` as well, so the third recorder needed no
    third separator -- `Fog` selects `Fog.compute` and `Fogs` selects
    neither.

    This is the only prefix rule in `query/`. `flow --object
    <qualname>:<name>` names ONE function and resolves it by equality, so
    there is no second copy of the rule to keep in step with this one; the
    recorder's own focus matchers (`record/tracer`,
    `typescript/src/focus.mjs`) are a different question, asked of source
    before a run rather than of a recorded trace.
    """
    return (qualname == spec or qualname.startswith(spec + ".")
            or qualname.startswith(spec + "::"))


def site_matches(code, at: str, trace) -> bool:
    """Whether `--at <at>` selects this code object."""
    mod, sep, qual = at.partition(":")
    if sep:
        if qual and not _qual_matches(code.qualname, qual):
            return False
        return not mod or mod in file_names(trace, code)
    return (_qual_matches(code.qualname, at)
            or at in file_names(trace, code))


def rerun_command(trace, codes) -> str:
    """The exact command that records this run again with these frames'
    locals.

    Fully instantiated, including the run's own command line and any focus
    it already had: a hint carrying a literal MODULE:QUALNAME placeholder is
    a template, not an answer, and an agent reading it has to guess. The
    focus already in the meta travels AS TYPED -- that is what its author
    will recognise -- and the sites asked about are added in this
    recorder's own spelling, which is what its `--focus` resolves.
    """
    words = terms(trace)
    meta = trace.meta
    specs = [*(meta.get("focus") or []),
             *(spell_site(trace, c) for c in codes)]
    focus = "".join(f" --focus {shlex.quote(s)}" for s in specs)
    command = " ".join(shlex.quote(str(a))
                       for a in (meta.get(words.command_key) or []))
    # `rstrip`, because a template whose `{command}` came back empty would
    # otherwise end in a space -- and the Python column's bytes, which the
    # legacy suite fences, have never had one (ruling R3).
    body = words.rerun_command.format(focus=focus, command=command).rstrip()
    cwd = meta.get("cwd")
    return f"cd {shlex.quote(cwd)} && {body}" if cwd else body
