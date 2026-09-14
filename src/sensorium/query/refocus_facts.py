"""The program's own output, and what a granted licence rests on.

Split out of `refocus_world`, which sat six lines under this repository's
800-line ceiling with a slice still to land in it. The seam is the one
`refocus_world`'s own header names, one step finer: everything there
establishes FACTS and nothing there decides a verdict, and these are the
facts stated POSITIVELY -- what the program printed, and what a licence may
claim once nothing has withheld it. `refocus_world` keeps `_licence_caveats`
and the checks that feed it, which is where a signal that FIRED withholds
the licence.

That is a move, not an interface: `refocus_world._verified_facts` and the
rest still resolve, to the SAME function objects, because every caller and
every test reaching for them is reaching for one command's internals and
there is still only one of each.

The import runs one way, `refocus_world` -> here. `_verified_facts` reads
three names that stay behind -- `unverifiable_checks` and the two markers it
tests against -- so it imports them inside its own body, the way
`refocus_licence` already does and for the same reason: a module-level
import back would be a cycle.
"""
from sensorium.query.refocus_threads import harness_exclusion
from sensorium.query.vocab import terms
from sensorium.store.reader import Trace


def _output_text(trace: Trace) -> dict[str, str]:
    out: dict[str, str] = {}
    for _eid, stream, data in trace.output_chunks():
        out[stream] = out.get(stream, "") + data
    return out


def _clip(s: str, cap: int = 60) -> str:
    return repr(s if len(s) <= cap else s[:cap] + "...")


def _output_difference(orig: Trace, new: Trace) -> str | None:
    """The first place the two runs' captured output parts company.

    The only cross-check that can catch a recorder-induced change in the
    program: the fingerprint is blind to the instrument by construction (see
    OBSERVER EFFECT), but a `__repr__` that counts its own calls and prints
    the total shows up right here.
    """
    a, b = _output_text(orig), _output_text(new)
    for stream in sorted(set(a) | set(b)):
        was, now = a.get(stream, ""), b.get(stream, "")
        if was == now:
            continue
        wl, nl = was.splitlines(), now.splitlines()
        for i in range(max(len(wl), len(nl))):
            x = wl[i] if i < len(wl) else "(no more output)"
            y = nl[i] if i < len(nl) else "(no more output)"
            if x != y:
                return (f"the program's own captured {stream} differs, first "
                        f"at line {i + 1}: {_clip(x)} -> {_clip(y)}")
        return f"the program's own captured {stream} differs in whitespace"
    return None


# -- what a granted licence rests on ---------------------------------------
def _spawn_witnessed(meta: dict) -> bool:
    """Whether this trace's interpreter could witness a `multiprocessing`
    spawn at all.

    False on CPython < 3.14 -- where no parent-side audit event fires for a
    spawn/forkserver child, so `spawn_syscalls == 0` cannot be read as "none
    ran" -- and on a trace recorded before the capability was noted. The
    recorder stamps the answer at record time (`boot._SPAWN_WITNESSED`).
    """
    return bool(meta.get("spawn_witnessing"))


def _verified_facts(orig: Trace, new: Trace, scope: str) -> list[str]:
    """What a granted licence is actually based on, stated positively.

    `scope` is `refocus_cmd._thread_scope`'s answer, passed in rather than
    recomputed: the same string goes into the assessment dict, and one
    derivation read twice is one derivation that can be read two ways.

    The granted line used to read "every signal sensorium can check agrees",
    which invites the reader to treat the check-list as complete -- and every
    review round has falsified that reading by finding another path through
    it. Naming the concrete, bounded findings instead cannot be falsified by
    a mechanism nobody has thought of yet: it claims these things and no
    others.
    """
    from sensorium.query.refocus_world import (UNVERIFIABLE_CHILDREN,
                                               UNVERIFIABLE_THREADS,
                                               unverifiable_checks)

    fps = new.fingerprints()
    # HOW MUCH was compared, not just how many rows. Under the per-task
    # basis a thread row covers only what ran outside every task, and the
    # commonest async shape -- an entry that does nothing but
    # `asyncio.run` -- leaves it covering the module frame, or nothing at
    # all. "Identical call shape across 1 compared fingerprint(s)" over two
    # events of scaffolding reads as a statement about the run; the count
    # and the scope are what make it a bounded claim instead.
    events = sum(c for _h, c in fps.values())
    # The noun is the recorder's, for the reason `vocab.py` exists: on a
    # Rust trace the row is outside the test and spawned threads, and
    # `asyncio` there names a runtime that never ran. `scope` decides
    # WHETHER the clause appears (one derivation, read once); `terms`
    # decides what it calls the units.
    outside = f" outside any {terms(new).task_noun}" if scope else ""
    # The thread clause is a PROVENANCE claim -- "through Python's own
    # threading/_thread" says how the threads this run did not start would
    # have come to exist -- so it comes from the trace's own vocabulary
    # table, for the reason `vocab.py` exists at all. The Python string is
    # unchanged, character for character: `PYTHON.thread_origin` IS this
    # clause, moved.
    # ...and where the recorder started a thread of its own, the clause
    # NAMES it instead of making the provenance claim: design 2026-09-07
    # section 2's line, verbatim. What a granted licence rests on is a
    # bounded list, so the harness thread appears on it as an exclusion
    # rather than being dropped from a sentence that then reads as though
    # only the main thread ever ran.
    harness, harness_clause = harness_exclusion(new)
    thread_fact = (
        f"no thread started besides the main one{harness_clause}"
        if harness else
        f"no thread started besides the main one "
        f"{terms(new).thread_origin}, and none left running when recording "
        "stopped")
    # Decided once and read by both capability guards in this function: two
    # derivations of one list is two answers to "what could this pair not
    # check".
    unverifiable = unverifiable_checks(orig, new)
    facts = [
        f"identical call shape across {len(fps)} compared fingerprint(s), "
        f"holding {events} causal event(s){outside}",
    ]
    # ...and stated only where the record it rests on exists. `relicense`
    # takes UNVERIFIABLE_THREADS out of the WITHHOLDING decision, so a pair
    # whose recorder declares it witnesses no thread can be GRANTED -- and
    # a granted licence asserting "no thread started besides the main one"
    # over bookkeeping nobody wrote is exactly the bug this file's header
    # names: a check that never ran, reported as a check that passed. The
    # child claim below is the same rule, three facts on.
    if UNVERIFIABLE_THREADS not in unverifiable:
        facts.append(thread_fact)
    # Stated only when there were tasks: a run with none must not be given
    # a fact about zero of them, and the count is the rerun's rows because
    # a stream present on one side only is a divergence, never a MATCH.
    # Spec D6's sentence in full -- the ordering clause travels with the
    # claim, because "compared by content" is only bounded by what content
    # means here.
    n_tasks = len(new.task_fingerprints())
    if n_tasks:
        facts.insert(1, f"{n_tasks} task stream(s) compared by content; "
                        "the ordering between tasks is not compared")
    # The child-witnessing claim rests on an audit event only CPython 3.14+
    # raises for a multiprocessing/forkserver spawn. If EITHER run was recorded
    # where that signal does not exist, the pair cannot vouch that no such child
    # ran, so the line is omitted rather than asserted -- the blind-spot block
    # printed on every verdict still states categorically that no child process
    # is covered, so the gap is stated, not hidden.
    #
    # The capability clause is the same rule stated where it cannot be
    # missed: a recorder that DECLARES it does not witness children can
    # never support this fact, whatever `spawn_witnessing` happens to say.
    # Today no such trace carries the key, so the clause changes no output;
    # it is here because "the pair cannot vouch for this" must not depend on
    # a second key agreeing.
    if (_spawn_witnessed(orig.meta) and _spawn_witnessed(new.meta)
            and UNVERIFIABLE_CHILDREN not in unverifiable):
        facts.append(
            "no child process witnessed, by any mechanism sensorium watches")
    return facts
