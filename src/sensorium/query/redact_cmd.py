"""`sensorium redact` -- rule v1 applied to traces that are already on disk.

Parts A and B put the rule at the three recorders' writers, so nothing NEW
reaches the store in plaintext. Everything already there still is. One pass
of this command over one trace does what a recorder would have done to it
at birth (§7): the environment through the NAME rule, with the digests
under the store's key and `env_hash` recomputed under the trace's own
language formula; every captured value the writers reach -- `args` and
`deltas` bindings, map keys, a RETURN under its callee's last qualname
segment, exception messages, `unwind_exc`, every `output` row, every
`children` element; the `redaction` stamp rewritten with `by: "retrofit"`
and `mode: "on"`; and the file left at 0600. It decides nothing itself:
`redact_store.plan` is the whole judgement and `redact_store.apply` the
only writer (C14). This module is the part a person and a script meet --
the lines, the exits, the sweep, the directory.

**The knobs are the CALLER's** (C4). `SENSORIUM_REDACT_NAMES` and
`SENSORIUM_REDACT_ALLOW` are read from this command's own environment,
because the shell that made the recording has ended and the person asking
is the one in front of the store; they are stamped, so the trace records
which pass took what. `SENSORIUM_NO_REDACT` is IGNORED -- `plan` forces it
off at the one point the knobs enter, and the reason it is forced there
rather than here is that the judgement must be incapable of obeying it:
running this command IS the decision (§7), and a stale export in somebody's
shell profile must not be able to turn a retrofit into a no-op that still
prints lines.

**`--dry-run` is `plan` alone, and its stdout is byte-identical to the real
run's** (C10) -- the same per-trace lines, the same summary, in the same
order -- with one line on STDERR saying nothing was written. That is not a
courtesy: E16's H4 reads the two stdouts and DIFFS them, so a dry run that
printed anything of its own would turn a measurement into a judgement about
wording. Both modes run the same loop with a single branch around `apply`,
so the two cannot drift. Exit codes are the real run's: 0 if anything
changed or would.

**Modes** (C11): a rewritten trace is 0600 by creation, and a trace that
needs no rewrite but sits at another mode is tightened in place and counts
as changed -- a 0644 trace is readable by everyone on the box whatever its
contents now say. `--all` also tightens `traces/` to 0700 and says so on
the summary, because a loose directory hands over every file in it; a
single-run pass never touches the directory.

**The lines** (C12) are pinned to the character: `corpus/redact_retrofit`
and E16 part C parse them, and an instrument that reads nothing reports a
green run over an unmeasured claim. One flushed line per trace as it is
finished, so a `--all` pass over a real store is watchable rather than
silent for a minute; then the summary, which names the spools as out of
reach instead of omitting them, since a count that quietly excluded them
would read as a claim about the whole disk.

**The stale-key sweep** (C13) runs once per invocation, before any trace,
in BOTH modes (P3): a `redaction.key.<pid>.tmp` left by a killed
`load_or_create` is 32 bytes of secret and not a trace, so §7's "change
nothing" does not cover it -- and skipping it under `--dry-run` would make
the two stdouts differ exactly when a reader is comparing them.

`nothing to redact` is P5's line: a trace already `mode: "on"` whose pass
finds nothing is not rewritten, even when the caller's knobs differ from
the recorded ones, because a stamp is a statement about what was taken and
rewriting one over an unchanged trace would date a file to say nothing new.
"""
import os
import sqlite3
import stat
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from sensorium import paths, redact, redact_store
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE
from sensorium.query.refocus_world import _capped
from sensorium.redact_key import Key, sweep_stale
from sensorium.redact_store import TIGHT, Plan

#: What `--all` leaves `traces/` at (C11). The files' own 0600 is
#: `redact_store.TIGHT`; a directory needs its execute bit to be entered.
DIR_TIGHT = 0o700

#: Named on every summary rather than silently left out: a count of
#: traces that quietly excluded the spools would read as a claim
#: about the whole disk (C20, §11).
SPOOLS = ("; spools under target/ and the TypeScript spool dirs are "
          "not reached")


def add_parser(sub) -> None:
    p = sub.add_parser(
        "redact", help="apply rule v1 to traces already in the store",
        epilog="exit: 0 something changed (or would), 1 nothing to do, "
               "2 a refusal (the others continue)")
    p.add_argument("run", nargs="?", default=None)
    p.add_argument("--all", action="store_true",
                   help="every trace in the store")
    p.add_argument("--dry-run", action="store_true",
                   help="print what would change; change nothing")
    # The parser itself, so `run` can refuse a call argparse cannot
    # express: `run` and `--all` are exclusive AND one is required, which
    # is two rules over a positional and a flag, not one group.
    p.set_defaults(func=run, parser=p)


def capped(names: Sequence[str]) -> str:
    """`info`'s cap -- eight names, then a count of the rest. Imported and
    not re-spelled: two commands printing the same list under two caps is
    how a reader learns to distrust both."""
    return _capped(list(names))


def _mode_clause(p: Plan) -> str:
    """`mode 600`, or the arrow that says what it was. Present on every
    line form that names a trace's contents (C12), because the mode is
    half of what a retrofit changes and the half a reader cannot see by
    querying the trace."""
    if not p.tightens:
        return f"mode {TIGHT:o}"
    return f"mode {p.mode_before:o} -> {TIGHT:o}"


def line_for(p: Plan) -> str:
    """One trace's whole outcome, in C12's words."""
    if p.refused:
        return f"run {p.run}: REFUSED: {p.refused}"
    if p.skipped:
        return f"run {p.run}: {p.skipped}, skipped"
    if p.env_names or p.values:
        return (f"run {p.run}: env {len(p.env_names)} redacted "
                f"({capped(p.env_names)}); values {p.values}; "
                f"{_mode_clause(p)}")
    return f"run {p.run}: nothing to redact; {_mode_clause(p)}"


def summary(plans: list[Plan], swept: int,
            dir_mode: tuple[int, int] | None) -> str:
    """The one line that accounts for every trace the pass reached.

    A plan that was REFUSED after its rewrite failed carries both the rows
    it wanted to write and the sentence saying it could not, so `redacted`
    is counted over the plans that were neither refused nor skipped: a
    trace whose rewrite raised was not redacted, and counting it twice --
    once as done, once as refused -- would leave the four numbers unable
    to add up to the traces walked.
    """
    skipped = sum(1 for p in plans if p.skipped)
    refused = sum(1 for p in plans if p.refused)
    done = sum(1 for p in plans
               if not p.refused and not p.skipped and p.rewrites)
    clean = len(plans) - done - skipped - refused
    line = (f"redacted {done} of {len(plans)} traces ({clean} already clean, "
            f"{skipped} skipped, {refused} refused){SPOOLS}")
    if swept:
        line += f"; swept {swept} stale key tmp file(s)"
    if dir_mode:
        line += f"; traces/ mode {dir_mode[0]:o} -> {dir_mode[1]:o}"
    return line


def _dir_mode(dry: bool) -> tuple[int, int] | None:
    """`traces/`'s mode change, applied unless this is a dry run, and
    reported either way (C11, P3). `--all` only: a pass over one trace was
    not asked about the store."""
    d = paths.traces_dir()
    before = stat.S_IMODE(d.stat().st_mode)
    if before == DIR_TIGHT:
        return None
    if not dry:
        os.chmod(d, DIR_TIGHT)
    return (before, DIR_TIGHT)


def _targets(args) -> list[Path]:
    """The traces this call names, in sorted run-id order (C12).

    `*.db` and nothing else: the converters' and the ingest's in-flight
    files are `.<run>.db.tmp` and this command's own workspace is
    `.<run>.db.redact.<pid>.tmp`, both dotfiles, both walked past (C8).
    A bad reference is `paths`' own error and reaches `cli.main`, which
    ends the call at exit 2 before any line is printed.
    """
    if args.all:
        return sorted(paths.traces_dir().glob("*.db"))
    return [paths.find_trace(args.run)]


def run(args) -> int:
    if args.run and args.all:
        args.parser.error("give a run reference or --all, not both")
    if not args.run and not args.all:
        args.parser.error("give a run reference or --all")
    root = paths.trace_root()
    # A store that cannot key records unkeyed digests (§3) -- but a DRY
    # run must leave the store exactly as it found it, and minting
    # `redaction.key` is a write. The lines are identical either way:
    # what they carry is names, counts and modes, none of which a key
    # decides.
    key = Key.load(root) if args.dry_run else Key.load_or_create(root)
    knobs = redact.Knobs.from_environ(os.environ)
    swept = len(sweep_stale(root))
    plans = []
    for path in _targets(args):
        p = redact_store.plan(path, key, knobs)
        if not args.dry_run:
            try:
                redact_store.apply(p)
            except (OSError, sqlite3.Error) as e:
                # The original is untouched (C7), so this is a refusal
                # like any other: named on its own line, the rest of the
                # pass continuing, the call ending at exit 2.
                p = replace(p, refused=f"the rewrite failed: {e}")
        plans.append(p)
        print(line_for(p), flush=True)
    dir_mode = _dir_mode(args.dry_run) if args.all else None
    print(summary(plans, swept, dir_mode))
    if args.dry_run:
        # On STDERR, so the two stdouts are the same bytes (C10).
        print("dry run: nothing was written", file=sys.stderr)
    if any(p.refused for p in plans):
        return BAD_CALL
    return ANSWERED if any(p.changes for p in plans) else NEGATIVE
