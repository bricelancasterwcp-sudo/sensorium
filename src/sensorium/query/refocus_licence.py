"""The licence code a SECOND driver language needs, at a shared home.

Every name here was written for the Rust branch and none of them is about
Rust: what they encode is what a licence may claim when a check could not
run, how the pair's own record says so, and what "the environment" means for
a re-run this process did not perform. A copy of any of them in the
TypeScript branch would be two spellings of one licence rule, which is how
two languages come to grant two different licences over the same evidence
(design 2026-09-07, G2, one layer down).

Split from `refocus_world` rather than added to it, because that file was
within twelve lines of this project's 800-line ceiling when the four
arrived. The names stay reachable as `refocus_world.<name>` -- the
re-export there is the same one `refocus_cmd` uses for `refocus_world` and
`refocus_report`. These are one command's internals across its files, not
separate modules with surfaces of their own.

WHY THE `refocus_world` IMPORTS ARE INSIDE THE FUNCTIONS
--------------------------------------------------------
`refocus_world` imports this module at its top, to re-export these names.
Two of the three functions below need `refocus_world`'s back --
`_verified_facts` is what a granted licence rests on and `_env_state` is the
environment compare itself, and neither can move here (both have callers of
their own, and `_env_state` is `refocus_cmd`'s Python branch). Imported at
the top that would be a hard cycle, and imported at the BOTTOM of
`refocus_world` it would be a cycle that only breaks when a caller happens
to import this module first. So they are taken at call time, which is the
idiom `refocus_rust` already uses for `refocus_cmd` and for the same reason.
The DIRECTION is still one way: nothing here runs at import time, and
`refocus_world` never has to know this file exists except to name it.
"""
from pathlib import Path

from sensorium.store import db
from sensorium.store.reader import Trace

#: The meta key `_stamp` may not write, because the checks it records are
#: NOT reasons a licence was withheld -- they are checks that could not run.
#: Stamped beside `refocus_licence_reasons` rather than inside it, so a
#: reader of the trace and a reader of the terminal are told the same thing.
UNVERIFIABLE_KEY = "refocus_licence_unverifiable"


def relicense(a: dict, orig: Trace, new: Trace, world_verified) -> dict:
    """Take the UNVERIFIABLE markers out of the WITHHOLDING decision.

    `_licence_caveats` reports them, because a reader of the licence must be
    told which checks did not run. But a caveat withholds the licence, and
    withholding it here would say the recorder's declared absence of output
    capture is a finding AGAINST this pair -- it is not a finding at all.
    The markers are printed and stamped separately (`print_unverifiable`,
    `UNVERIFIABLE_KEY`), so nothing is hidden by the removal; what is
    removed is only their vote.

    The verified list is rebuilt exactly as `assess` builds it -- the
    world's fact spliced after the first -- because two splices of one list
    is two orders for the same evidence.

    Was `refocus_rust._relicense`, which imports it under that name.
    """
    from sensorium.query.refocus_world import UNVERIFIABLE, _verified_facts

    caveats = [c for c in a["caveats"] if c not in UNVERIFIABLE]
    if caveats == a["caveats"]:
        return a
    licence, verified = a["licence"], a["verified"]
    if a["verdict"] == "MATCH" and not caveats:
        licence = "granted"
        facts = _verified_facts(orig, new, a["thread_scope"])
        verified = facts[:1] + list(world_verified) + facts[1:]
    return {**a, "caveats": caveats, "licence": licence,
            "verified": verified}


def stamp_unverifiable(path: Path, checks: list[str]) -> None:
    """Write the unrun checks into the new trace, beside the licence.

    Stamped even when the list is empty -- and even when the licence is
    withheld for other reasons -- so `info` on any re-run says which checks
    the verdict does NOT rest on, rather than leaving a reader to infer it
    from the absence of a key.

    Was `refocus_rust._stamp_unverifiable`, which imports it under that name.
    """
    conn = db.open_trace(path)
    try:
        db.set_meta(conn, UNVERIFIABLE_KEY, checks)
        conn.commit()
    finally:
        conn.close()


def print_unverifiable(checks: list[str]) -> None:
    """The unrun checks, on the terminal, under everything the report said.

    Beside `stamp_unverifiable` and for its reason: what a pair could not
    check is one sentence, and a branch spelling it for itself is how two
    branches come to report the same fact differently. It was
    `refocus_rust._print_unverifiable` while two branches used it; the
    Python branch is the third (ruling R19), and a generic branch reaching
    into the Rust one for a licence sentence is the dependency this module
    exists to prevent.

    Silent on an empty list: the block announces checks, and a heading over
    nothing reads as a finding.

    THE PREAMBLE IS EXACT FOR THREE OF THE FOUR MARKERS AND FALSE FOR THE
    FOURTH. Output, children and threads are checks the recorder declares it
    does not produce -- there is no record, and nothing a reader can do about
    it. `UNVERIFIABLE_ENV` is the other shape: the recorder redacted the
    variable exactly as asked, and what is missing is a KEY -- either none
    took the digests (`unkeyed`, and they are null) or the one that took
    them belongs to another store (`different keys`). Same word, opposite
    repairs -- and the two reasons have different repairs from EACH OTHER,
    which is why the line points at the env line (which carries the reason
    word) rather than naming one. `redact.uncomparable` is where those two
    words come from.

    The preamble stays byte for byte what it was -- three acceptance readers
    parse it, and every pair that carries no redaction marker still reads
    exactly as it did -- and the one extra line goes UNDER the list, printed
    only for the marker it is about.
    """
    from sensorium.query.refocus_world import UNVERIFIABLE_ENV

    if not checks:
        return
    print("checks that could not run on this pair -- the recorder declares "
          "it does not produce them, so nothing here is evidence either "
          "way:")
    for check in checks:
        print(f"  - {check}")
    if UNVERIFIABLE_ENV in checks:
        print("  the env one does not fit the heading above: those "
              "variables WERE redacted, and what is missing is the key that "
              "decides them -- the env line names them and says which repair "
              "it is (`unkeyed`: record again under a key; `different keys`:"
              " find the other store's redaction.key).")


def env_of(meta: dict, new: Trace,
           is_recorder_key) -> tuple[str, str | None, str | None]:
    """(status line, caveat, fact) for the environment, from BOTH traces.

    Design section 3.2's `reads` column: a driver language's environment
    check is `env` recorded in both traces, not the caller's process
    environment. Comparing the recorded harness environment against this
    CLI's would diff the harness's own variables against their absence and
    report a changed world on every single run -- a check that always fires
    says nothing.

    `is_recorder_key` is the CALLER's, because which variables are the
    recorder's own bookkeeping is the one thing here that is not shared:
    cargo's shim names are not vitest's. Everything done with the answer is
    shared, which is why it is a parameter and not a second copy of this.

    Was `refocus_rust._env_of`, which read its own module's predicate.
    """
    from sensorium.query.refocus_world import _UNCOMPARED_ENV, _env_state

    was, now = meta.get("env"), new.meta.get("env")
    if not isinstance(now, dict):
        return ("env: unverifiable -- the re-run's trace records no "
                "environment to compare against",
                "the environment could not be checked at all -- the "
                "re-run's trace holds none to compare -- so nothing rules "
                "out the two runs getting different input through it", None)
    # `_UNCOMPARED_ENV`'s names are already printed by `_env_state`; listing
    # them twice would read as two separate holes in one check.
    mine = sorted({k for k in ((was if isinstance(was, dict) else {}) | now)
                   if is_recorder_key(k) and k not in _UNCOMPARED_ENV})
    # `new.meta` whole, beside the FILTERED environment: the recorder's own
    # keys are taken out of the compare, but the re-run's `redaction` table
    # is how a redacted variable is compared at all, and a side handed no
    # meta would be read as the live plaintext one -- which a driver
    # language's re-run never is.
    line, caveat, fact = _env_state(
        {**meta, "env": {k: v for k, v in was.items()
                         if not is_recorder_key(k)}}
        if isinstance(was, dict) else meta,
        {k: v for k, v in now.items() if not is_recorder_key(k)},
        now_meta=new.meta)
    if mine:
        named = f"; the recorder's own, also not compared: {', '.join(mine)}"
        line += f"  {named[2:]}"
        fact = f"{fact}{named}" if fact else fact
    return line, caveat, fact
