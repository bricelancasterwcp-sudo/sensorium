"""A target directory that MOVED, a fragment the RECORDER wrote, and the
session a re-run was LAUNCHED from -- each told apart from a world that
changed.

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


# -- session set 1: where a process was STARTED, not what it computes ------
#: The version of the set below. It is a NUMBER in the printed line on
#: purpose: an exemption from the licence's default is a claim, and a claim
#: a reader can date and argue with is a different thing from a silent one.
#: A key found to bear on what a program computes leaves the set with a
#: date; a key found to differ between shells joins it with one.
SESSION_SET = 1

#: Session set 1, exact names, in the order they are printed and read.
#:
#: Every one is a handle to a bus, a window, a terminal, a connection, a
#: service manager's invocation or an agent session -- the identity of WHERE
#: a process was started, never input to what it computes. A re-run launched
#: from another shell differs on these and on very little else: measured
#: 2026-09-08 (names only) against kept E4 original 20260907-111144-33d30c,
#: 73 keys equal, 0 added, 3 missing (the previous launcher's own pins) and
#: exactly ONE changed, `CLAUDE_CODE_SESSION_ID`. That is the whole of the
#: problem E4' amendment A1 carried.
#:
#: A POSITIVE list, and short. The design first written here kept the
#: opposite -- a list of variables that "bear" on a program, everything else
#: let through -- and the suite already held its falsifier:
#: `test_refocus_withholds_the_licence_when_the_environment_differs`
#: records under `REFOCUS_TEST_LIMIT` and refocuses without it, a variable
#: the program demonstrably READS, and `REFOCUS_TEST_LIMIT` is on no bearing
#: list anyone would write. That design would have granted a licence over a
#: program that got different input: the direction that claims MORE, which
#: is the one thing the licence exists to refuse. The tool cannot know which
#: variables a program reads, so the default stands -- any differing key
#: withholds -- and this is the one enumerated exception.
SESSION_ORDER: tuple[str, ...] = (
    "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID", "TERM_SESSION_ID",
    "WINDOWID", "TMUX", "TMUX_PANE", "SSH_AGENT_PID", "SSH_AUTH_SOCK",
    "SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY", "INVOCATION_ID",
    "JOURNAL_STREAM", "SYSTEMD_EXEC_PID")
SESSION_EXACT = frozenset(SESSION_ORDER)

#: The one prefix. An agent session mints its own variables per session and
#: their names are not knowable in advance, which is what a prefix is for --
#: and why there is exactly one: a prefix admits names nobody enumerated, so
#: each one is a hole and each one has to earn its place.
SESSION_PREFIXES = ("CLAUDE_CODE_",)


def is_session_key(name: str) -> bool:
    """Whether `name` identifies the session a process was launched from.

    Exact membership or one of the prefixes, and nothing looser: a family
    resemblance would exempt variables nobody put on the list.
    `XDG_SESSION_IDX` is not `XDG_SESSION_ID`, and `CLAUDE_CODEX` does not
    carry the `CLAUDE_CODE_` prefix.
    """
    return (name in SESSION_EXACT
            or any(name.startswith(p) for p in SESSION_PREFIXES))


# -- the recorder's OWN fragment, which is not the world's -----------------
#: `RUSTDOCFLAGS` as `cargo sensorium` writes it, and the one thing in the
#: compared environment that is the RECORDER's rather than the world's. The
#: driver links the runtime in by hand -- `--extern` plus the `-L
#: dependency=` that resolves it -- and the directory carries a digest of
#: the driver binary and the `sensorium-rt` sources, so the hash MOVES with
#: every driver build. E4' measured the cost of not knowing that: all 61
#: pairs withheld on this one key, under a driver that had simply been
#: rebuilt (that record's section 5, blind spot 27).
#:
#: The shape is the fence. `sensorium_rt` by name, `/sensorium/rt/` followed
#: by exactly sixteen hex characters and one of the two panic strategies,
#: `libsensorium_rt.rlib`, and -- the rule that makes it ours -- a
#: BACKREFERENCE: the two tokens must name ONE directory. Two tokens that
#: name two directories are not a thing this recorder has ever written, so
#: they are left for the world's compare. `(?:^| )` and `(?= |$)` bound the
#: match at token edges, and the leading space is consumed with it so the
#: remainder needs no re-spacing.
RECORDER_FRAGMENT = re.compile(
    r"(?:^| )--extern sensorium_rt=(?P<dir>\S+/sensorium/rt/[0-9a-f]{16}/"
    r"(?:unwind|abort))/libsensorium_rt\.rlib -L dependency=(?P=dir)(?= |$)")


def strip_recorder_fragment(value: str) -> tuple[str, int]:
    """`value` with every occurrence of our fragment removed, and how many
    were removed.

    The count is returned rather than inferred from the remainder, because
    the count is what puts the key on the printed strip list: a removal
    that did not report itself would be an exclusion by name, hidden --
    the thing the relocation rule above exists to avoid.

    Only the space the regex consumed goes with the match; the world's own
    spacing inside what is left is untouched, so two values that differ by
    whitespace still differ after the strip.
    """
    out, count = RECORDER_FRAGMENT.subn("", value)
    return out.strip(), count


#: The phrase that both WRITES the strip note and RECOGNISES it, on the
#: `_RELOCATED` pattern and for the same reason: one constant, so the
#: sentence and its reader cannot drift apart.
#:
#: It lives here rather than in `vocab.py` because it is not language-
#: bearing. `vocab` holds the sentences that say what Python or Rust means;
#: this one says what this TOOL does to its own footprint before comparing,
#: and it reads the same whichever recorder wrote the trace.
_STRIPPED = "the recorder's own fragment stripped before comparing: "


def stripped_clause(names: list[str]) -> str:
    """What the env line and the verified fact both say about the keys the
    strip touched. Empty when it touched none -- so a Python pair, which
    can never carry the fragment, reads exactly as it always did.

    Named, never counted, and never silent: a variable this tool removed
    part of before comparing is a variable it checked less of, and a reader
    is owed the name.
    """
    if not names:
        return ""
    return f"{_STRIPPED}{', '.join(names)}"


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
    """Whether a world-fact carries the names a rule of this module
    explained -- by EITHER rule: the target directory that moved, or the
    recorder's own fragment removed before the compare.

    A withheld licence records no verified facts -- it rests on nothing --
    but the keys this check EXPLAINED are a finding of its own, and the
    terminal already prints them beside the accusation. Without this the
    trace kept only the accusation, and `info` replayed a licence whose
    screen had said more than the record does.

    Recognised by the phrases `relocated_clause` and `stripped_clause`
    build, from the same constants they build them from, so a rewording
    moves both halves together and cannot leave this reading a sentence
    that no longer exists.
    """
    return _RELOCATED in fact or _STRIPPED in fact
