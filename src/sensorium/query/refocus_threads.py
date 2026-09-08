"""Which threads a run started, and which of them the comparison saw.

Split out of `refocus_world` at that file's 800-line ceiling, along the seam
CARRIED-DEBT named for it: the thread bookkeeping. Everything here answers
one question -- how many threads were there, and whose were they -- and the
answers are read by three callers that print them (`refocus_report`'s
`threads:` line, `info_cmd`, `diff_notes`) and by `refocus_world`'s own
caveats. Nothing here decides a verdict or prints one.

`compared_threads` travels with them although CARRIED-DEBT's seam names only
the four: it is `uncompared_threads`' only helper, and leaving it behind
would make this module import `refocus_world` back, which is a cycle and a
second direction for one command's internals to travel in.

The names stay reachable as `refocus_world.<name>` -- the re-export there is
the same one `refocus_cmd` uses for `refocus_world` and `refocus_report`.
These are one command's internals living in four files, not four modules
with four surfaces.
"""
# The site-mark lookup, imported rather than rebuilt. `meta.sites` joins to
# `code_objects` on a workspace-relative path against an absolute one, and
# two implementations of that join are two ways for one trace to be read.
from sensorium.query.exceptions_rust import _marks as _site_marks
from sensorium.query.vocab import terms
from sensorium.store.reader import Trace


def harness_threads(trace: Trace) -> set[int]:
    """The threads this trace's RECORDER started, not the program.

    `cargo test` runs every `#[test]` function on a thread libtest spawns
    for it, so a `cargo test` trace always carries one non-main thread the
    program did not start -- and the untraced-thread caveat below fired on
    all 61 pairs of E4 for that reason and no other (E4 section 5.2, design
    2026-09-07 R1). A clause that cannot NOT fire is not a finding, and the
    precedent for taking it out is one this licence already sets: the
    recorder's own environment variables are excluded from the environment
    comparison, by name.

    A harness thread is a NON-MAIN thread whose FIRST root frame's site the
    manifest marks `#[test]` and whose task the runtime did NOT name at a
    spawn site. Each clause is load-bearing:

    * the ROOT: a marked fn called from deeper on another thread says
      nothing about who started that thread;
    * the FIRST root: a thread that runs one instrumented fn to completion
      and then another has two, and only the first is how it began;
    * NOT spawn-named: the mark is no proof the other way. `#[test] fn` is
      an ordinary fn to rustc, so `thread::spawn(|| a_test_fn())` puts a
      MARKED root on a thread the PROGRAM started -- the closure holds no
      `?`, so it opens no frame of its own -- and subtracting it GRANTED
      this licence over a program thread until 2026-09-08 (blind spot 28,
      design R3). `sensorium-rt` names a workspace spawn at its site
      (`spawn@<qualname>#<k>`, or `<parent> :: spawn@...`), the recorded
      fact that tells two identical-looking roots apart.

    An `async` test fn carries no site row -- the transform classifies it
    `async` and skips it whole, `#[tokio::test]` with it -- so it has no
    mark and its thread is COUNTED as the program's, which claims less.

    Empty for a recorder whose traces carry no site marks at all -- every
    Python trace -- and empty unless the main thread is a RECORDED fact.
    `main_thread_id()` never reports "the trace does not say": it falls
    back to the thread of whichever event got id 1, which under `--focus`
    filtering or ordinary scheduling jitter can name a worker. Subtracting
    on a guess is the one way this rule can take a thread out of a count it
    was never in, so `main_thread_basis()` -- "recorded", "inferred", or
    None for a trace with no events at all -- is what the exclusion rests
    on. Neither empty case is a harness thread that went unfound: both
    leave every count exactly as it was, the direction that claims less.
    """
    if trace.main_thread_basis() != "recorded":
        return set()
    main = trace.main_thread_id()
    marks = _site_marks(trace.meta)
    found, decided = set(), {main}
    # `decided` holds the main thread from the start (never the harness's)
    # and every other thread from its FIRST root: `roots()` is frame-id
    # ordered, so a later root of a thread already decided never votes.
    for root in trace.roots():
        thread = root.thread_id
        if thread in decided:
            continue
        decided.add(thread)
        # A thread with no task row, or one whose name could not be read
        # (`Task.name` is nullable by schema), carries no spawn name to
        # read: it is decided on its root's mark alone, as every thread was
        # before this rule.
        task = trace.task(thread)
        name = "" if task is None or task.name is None else task.name
        if name.startswith("spawn@") or " :: spawn@" in name:
            continue
        code = trace.code(root.code_id)
        if marks.get((code.qualname, code.file)) == "test":
            found.add(thread)
    return found


def harness_exclusion(trace: Trace) -> tuple[int, str]:
    """How many threads this recorder started itself, and the clause that
    NAMES them wherever one of its thread counts is printed.

    The clause travels with the count on purpose. A subtraction that showed
    only its result would put a smaller number where a larger one used to
    be with nothing on the line to say why -- a number that looks measured
    standing in for a fact that was removed, which is this project's own
    bug class one level up.
    """
    phrase = terms(trace).harness_thread
    if phrase is None:
        return 0, ""
    n = len(harness_threads(trace))
    if not n:
        return 0, ""
    return n, f" and {n} harness thread{'' if n == 1 else 's'} ({phrase})"


def harness_note(trace: Trace) -> str:
    """The harness exclusion as a clause of its OWN, for a line whose counts
    it is not one of.

    `harness_exclusion`'s clause follows a count and joins it (" and 1
    harness thread ..."); on a line that counts what was NOT compared, the
    same words would say the harness thread is one of them. Same fact, same
    vocabulary, a grammatical slot that does not lie. Empty where the
    recorder starts no thread of its own.
    """
    n, _clause = harness_exclusion(trace)
    if not n:
        return ""
    plural, verb = ("", "is") if n == 1 else ("s", "are")
    return (f"; {n} harness thread{plural} ({terms(trace).harness_thread}) "
            f"{verb} not among these counts")


def compared_threads(trace: Trace) -> set[int]:
    """The threads whose call shape this trace actually had compared.

    NOT `fingerprints()`. The Rust converter writes exactly ONE thread row
    -- the main thread's -- and routes every other thread's events into
    `task_fingerprints` (`convert/frames.rs`), so a count of thread rows
    reported every non-main Rust thread as one that "ran no traced code,
    left no fingerprint, and was NOT compared" while its whole call shape
    had been compared, on the very thread the code under test runs on.

    A task row is followed back to its thread through the `tasks` table
    rather than assumed to be one: in Python a task is an asyncio task and
    many of them share a thread, so adding task rows to a thread count
    would be the same error facing the other way. A task whose `tasks` row
    is missing names no thread and adds none -- that reports MORE
    uncompared threads, which is the direction that claims less.
    """
    threads = set(trace.fingerprints())
    thread_of = {task.id: task.thread_id for task in trace.tasks()}
    for task_id in trace.task_fingerprints():
        thread = thread_of.get(task_id)
        if thread is not None:
            threads.add(thread)
    return threads


def uncompared_threads(trace: Trace) -> int | None:
    """How many threads this trace records STARTING and did not compare.

    None when it does not record how many threads it started: absence of
    the record is not a record of absence, and a count derived from a
    missing key is the one number a line about what went uncompared must
    never print.

    Harness threads are the recorder's own, so they are not among the
    program's uncompared threads -- but only the ones NOT already compared
    are subtracted, or a harness thread whose stream WAS compared (the
    ordinary case: it is the thread the `#[test]` fn runs on) would come
    off the count twice. Clamped at zero rather than printed negative: a
    thread can leave a fingerprint without the audit hook counting its
    creation -- a C extension's thread in Python -- and a negative here
    would be arithmetic across two populations reported as a measurement.
    """
    started = trace.meta.get("threads_started")
    if started is None:
        return None
    compared = compared_threads(trace)
    unfound_harness = harness_threads(trace) - compared
    return max(started - len(compared - {trace.main_thread_id()})
               - len(unfound_harness), 0)
