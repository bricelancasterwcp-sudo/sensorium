"""A target directory that MOVED, told apart from a world that changed.

Split out of `refocus_world` rather than added to it: the licence's
environment clause now has a rule of its own, and `refocus_world` is the
file that was already nearest this project's 800-line ceiling.

WHY THIS RULE EXISTS
--------------------
`refocus` re-runs the program, and a re-run happens under whatever
`CARGO_TARGET_DIR` the caller gives it -- E4' gives it a fresh one on
purpose, because the kept store is never written and the re-run must build
somewhere else. Cargo then hands the test binary four variables that embed
the target root, so the two recorded environments differ on all four and
the env clause fired on every pair Task 5's dry run measured:

    CARGO_TARGET_DIR   the root itself
    CARGO_BIN_EXE_*    one path under it, per binary target
    LD_LIBRARY_PATH    a colon list whose first entry is under it
    RUSTDOCFLAGS       a flag string carrying one

A clause that cannot not fire is not a finding -- the same rule R1 applied
to libtest's per-test thread, one check along. Ruling (controller,
2026-09-07): a re-run from another target directory is a normal use of the
tool, and this clause must not read the target root's RELOCATION as a
change the world made.

AND WHY IT IS NOT A LIST OF EXCLUDED NAMES
-------------------------------------------
Excluding those four by name would be the cheap fix and the wrong one: a
program that really is handed a different `LD_LIBRARY_PATH` -- one extra
directory on the loader's path -- would then earn a full licence. So
nothing is excluded by name. Each key that DIFFERS is asked one question:
does the difference disappear when the original's target root is rewritten
to the re-run's? If it does, the key is named as relocated and the licence
still holds. If anything else about the value moved, it is a change, and it
withholds exactly as it did before.
"""
import re

#: The variable that names the root every other one embeds. Present only on
#: a trace `cargo sensorium` recorded, which is what makes the whole rule a
#: no-op on a Python trace: no root, nothing to normalise, and every string
#: below is the one it was before this module existed.
TARGET_ROOT = "CARGO_TARGET_DIR"

#: The phrase that both WRITES the relocation note and RECOGNISES it. One
#: constant, so the sentence and the reader of the sentence cannot drift.
_RELOCATED = "differ only by the target directory: "


def relocation(was: dict, now: dict) -> tuple[str, str] | None:
    """The (original, re-run) target roots, or None when there is nothing
    to normalise.

    None the moment either side lacks the key -- and a root of `/` after
    the trailing separator is stripped is also None, because a root that
    prefixes every absolute path on the machine would explain any
    difference at all, which is the opposite of a check.
    """
    old = (was.get(TARGET_ROOT) or "").rstrip("/")
    new = (now.get(TARGET_ROOT) or "").rstrip("/")
    if not old or not new:
        return None
    return old, new


#: What may appear INSIDE a path component. A root preceded by one of
#: these is the tail of a longer name, not the name itself -- `mytarget-a`
#: ends with `target-a` and is a different directory. A root preceded by a
#: separator, a space, an `=` or nothing at all begins a component and is
#: the root.
_NAME_CHAR = re.compile(r"[A-Za-z0-9_.+~@-]")


def _reroot(segment: str, old: str, new: str) -> str:
    """`segment` with every path rooted at `old` re-rooted at `new`.

    Where the root NAMES A PATH and nowhere else, anchored on BOTH sides:
    followed by a separator or the end of the segment, and preceded by the
    start of the segment or a character no path component may contain.
    A substitution that skipped either anchor would grant a licence over a
    directory that really did move -- `/build/target-abc` is not
    `/build/target-a` relocated on the right, and `/ws/mytarget-a` is not
    `target-a` relocated on the left. The left anchor matters most for a
    RELATIVE root (`CARGO_TARGET_DIR=target-a`), which carries no leading
    separator of its own to stand in for it.

    Only the root is re-rooted, never a component that repeats it: `/a/a`
    under `/a` -> `/z` is `/z/a`, because the second `/a` is the child.
    """
    out, i = [], 0
    while True:
        at = segment.find(old, i)
        if at < 0:
            break
        end = at + len(old)
        begins = at == 0 or not _NAME_CHAR.match(segment[at - 1])
        ends = end == len(segment) or segment[end] == "/"
        if begins and ends:
            out.append(segment[i:at])
            out.append(new)
            i = end
        else:
            # Advance by ONE, not past the whole occurrence: a root that
            # overlaps itself would otherwise lose its second start.
            out.append(segment[i:at + 1])
            i = at + 1
    out.append(segment[i:])
    return "".join(out)


def differs_only_by_root(was: str, now: str, old: str, new: str) -> bool:
    """Whether the ONLY difference between two values is where the target
    directory is.

    Compared entry by entry, splitting on the separator a `PATH`-like list
    uses, because the count of entries is itself a fact: a list that gained
    or lost one is a change however the rest of it reads, and comparing the
    joined strings instead would let an added directory ride in behind a
    relocation. A single path is a list of one and takes the same route.

    An entry that differs must both CONTAIN the old root and match after
    the substitution; the trailing separator is forgiven on that entry
    alone, because the two recorders may spell one directory `<root>` and
    `<root>/` and that is a difference in the spelling, not in the world.
    """
    entries_was, entries_now = was.split(":"), now.split(":")
    if len(entries_was) != len(entries_now):
        return False
    explained = False
    for before, after in zip(entries_was, entries_now):
        if before == after:
            continue
        if old not in before:
            return False
        if _reroot(before, old, new).rstrip("/") != after.rstrip("/"):
            return False
        explained = True
    return explained


def relocated_clause(names: list[str]) -> str:
    """What the env line and the verified fact both say about the keys the
    rule explained. Empty when it explained none, so a pair that never
    moved reads exactly as it always did.

    The names are printed, not counted. "4 variables were fine" is not
    something a reader can judge, and these four are the ones a reader most
    needs to see named: they are the difference between "the tool re-ran
    your program somewhere else" and "your environment changed".
    """
    if not names:
        return ""
    return (f"{len(names)} variable(s) {_RELOCATED}"
            f"{', '.join(names)}; treated as unchanged")


def is_relocation_note(fact: str) -> bool:
    """Whether a world-fact carries the names this rule explained.

    A withheld licence records no verified facts -- it rests on nothing --
    but the keys this check EXPLAINED are a finding of its own, and the
    terminal already prints them beside the accusation. Without this the
    trace kept only the accusation, and `info` replayed a licence whose
    screen had said more than the record does.

    Recognised by the one phrase `relocated_clause` builds, from the same
    constant, so a rewording moves both halves together and cannot leave
    this reading a sentence that no longer exists.
    """
    return _RELOCATED in fact
