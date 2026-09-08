"""What `refocus` SAYS: the stamp it writes, and the report it prints.

Split out of `refocus_cmd` at that file's 800-line ceiling, along the seam
the material has: nothing here decides anything. Every fact these four
functions print or stamp was settled by `assess`, which stays with the
verdict; `res` is read only for the VALUES `assess` has already ruled
apply. That is the whole reason the split is safe -- the terminal line,
the stamped label and the exit code still come from one reading, and this
file is where that one reading is put into words.
"""
from pathlib import Path

from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from sensorium.query.diff_cmd import print_comparison, task_drill_lines
from sensorium.query.refocus_world import harness_note, uncompared_threads
from sensorium.query.vocab import print_blind_spots, terms
from sensorium.store import db
from sensorium.store.reader import Trace


def _stamp(path: Path, res: dict, a: dict) -> None:
    """Label the new trace with its verdict AND its licence, permanently.

    The licence is stamped for the same reason the verdict is: a listing
    that shows a bare `verdict:MATCH` for a run whose licence was withheld
    on every count is the "reads as a pedigree" failure one level down.
    """
    conn = db.open_trace(path)
    try:
        db.set_meta(conn, "refocus_verdict", a["verdict"])
        # `thread_stream_parted` is False when the divergence is not a step
        # of the compared thread's stream at all (the tasks parted and that
        # stream did not). Writing the index anyway would persist "diverged
        # at step None" as if it were a position, and the task description
        # below is the real one. `res` is read only for the VALUES; whether
        # they apply is `assess`'s answer, so the label and the printed line
        # cannot come from two different readings.
        if a["thread_stream_parted"]:
            db.set_meta(conn, "refocus_diverge_index", res["index"])
            db.set_meta(conn, "refocus_diverge_a", res["a_desc"])
            db.set_meta(conn, "refocus_diverge_b", res["b_desc"])
        elif a["verdict"] == "REFUSED":
            db.set_meta(conn, "refocus_refused_reasons", res["reasons"])
        if a["threads"]:
            db.set_meta(conn, "refocus_thread_divergence", a["threads"])
        if a["task_divergence"]:
            db.set_meta(conn, "refocus_diverge_tasks", a["task_divergence"])
        if a["licence"]:
            db.set_meta(conn, "refocus_licence", a["licence"])
            db.set_meta(conn, "refocus_licence_reasons", a["caveats"])
            db.set_meta(conn, "refocus_licence_verified", a["verified"])
        conn.commit()
    finally:
        conn.close()


def _print_thread_line(orig: Trace, new: Trace, a: dict) -> None:
    """The `threads:` line, in the four shapes it comes in."""
    if a["threads"]:
        print(f"threads: DIVERGED -- {a['threads']}")
    elif a["thread_stream_parted"]:
        # Keyed on whether the compared STREAM parted, not on the verdict: a
        # DIVERGED with no index is a divergence of the tasks, and the
        # compared thread stream matched. Saying it "already diverged" there
        # would be false, and would hide that every thread row did match.
        print("threads: not compared -- the compared thread already diverged")
    elif new.fingerprints():
        # NOT "all N threads matched". That sentence asserted completeness
        # this tool cannot have: a thread whose body is entirely stdlib
        # leaves no fingerprint, so it is not among the N and was never
        # compared. Say how many were compared, and say plainly when more
        # existed than that.
        n = len(new.fingerprints())
        # `uncompared_threads` and not `threads_started + 1 - n`: that was
        # arithmetic across two populations. This converter writes one
        # thread row and puts every other thread in `task_fingerprints`, so
        # the old sum reported EVERY non-main Rust thread as one that "ran
        # no traced code" -- including the thread the code under test runs
        # on, whose call shape had just been compared. None from either
        # side means the count cannot be established, and then the clause
        # is absent rather than derived from a key that was never written.
        counts = [uncompared_threads(t) for t in (orig, new)]
        unseen = None if None in counts else max(counts)
        tail = (f"; {unseen} further thread(s) ran no traced code, left no "
                "fingerprint, and were NOT compared" if unseen else "")
        print(f"threads: {n} recorded fingerprint(s) compared"
              f"{a['thread_scope']}, all matching{tail}{harness_note(new)}")
    else:
        print("threads: no per-thread fingerprints were recorded on either "
              "side -- there was nothing to compare beyond the stream above")


def _diverged_why(a: dict) -> str:
    """What this DIVERGED is attributed to, in the report's own words."""
    if a["threads"]:
        return "a thread other than the compared one took a different path"
    if a["thread_stream_parted"]:
        return "the compared thread took a different path"
    if a["task_divergence"]:
        # "took a different path" presumes both sides ran one. When a side
        # ran no task stream at all there is no path to have differed, and
        # naming which side is the whole finding.
        t = a["tasks"] or {}
        if t.get("n_a") == 0:
            return "the rerun ran a task stream the original did not"
        if t.get("n_b") == 0:
            return "the original ran a task stream the rerun did not"
        return "a task took a different path"
    # Unreachable through `compare()`, which reports DIVERGED with no index
    # only when the tasks parted. Stated rather than assumed, for the same
    # reason `final_verdict` never downgrades a DIVERGED: if the two modules
    # ever disagree, the honest line is the one that does not name a culprit
    # it has not found.
    return ("the comparison reported a divergence this report could not "
            "attribute to a thread or a task")


def report(orig: Trace, new: Trace, res: dict, orig_name: str, new_name: str,
           a: dict) -> int:
    """Print the comparison and the verdict; return the exit code."""
    # `tasks=False`: the task finding is printed below, in the words that
    # are also stamped into the trace, with the drill-in commands beside
    # them. Letting `diff` print its own version too gave this output two
    # `tasks:` lines that said different amounts about one finding.
    print_comparison(orig, new, res, orig_name, new_name, tasks=False)
    # `res` belongs to `print_comparison` above and to nothing else here:
    # every fact this function decides on comes from `assess`.
    verdict, threads = a["verdict"], a["threads"]
    task_divergence, tasks = a["task_divergence"], a["tasks"] or {}

    if verdict == "REFUSED":
        print("threads: not compared -- no verdict was issued")
        print(f"refocus verdict: REFUSED -- {new_name} was recorded and is "
              f"queryable, but it could NOT be verified against "
              f"{orig_name}: treat it as a separate, UNVERIFIED execution")
        # Stated here too: "on every verdict" has to include the verdict
        # that says nothing, or the sentence is not true.
        print_blind_spots(new)
        # The second gate (X4). The program DID re-run -- the new trace
        # exists and is queryable -- and what failed is the verification
        # against the original. No edit to this command changes that; a
        # recording the comparison can stand on does, which is what 3
        # means. The pre-rerun refusals in `_refuse` keep 2.
        return UNSETTLED

    _print_thread_line(orig, new, a)

    if task_divergence:
        # The only `tasks:` line in this output, and the same sentence
        # `_stamp` writes -- so what the terminal says and what `info`
        # replays afterwards cannot drift apart.
        print(f"tasks: DIVERGED -- {task_divergence}")
        for line in task_drill_lines(tasks.get("pair"), orig_name, new_name):
            print(line)
    elif tasks.get("verdict") == "MATCH":
        print(f"tasks: {tasks['n_b']} task stream(s) compared by content, "
              "all matching; the ordering between tasks is not compared")

    if verdict == "DIVERGED":
        why = _diverged_why(a)
        print(f"refocus verdict: DIVERGED -- {why}. {new_name} is a "
              f"DIFFERENT execution than {orig_name}; it is still queryable, "
              f"every `sensorium info {new_name}` says so, and nothing it "
              f"shows is a fact about {orig_name}")
        # Only the WORLD findings, never the trace-derived ones: differing
        # output and a differing exit status are consequences of a
        # divergence, and offering a consequence as a possible cause would
        # send the reader looking in the wrong direction.
        if a["world"]:
            print("differences in the world between the two runs, any of "
                  "which may be why:")
            for caveat in a["world"]:
                print(f"  - {caveat}")
        print("note: a divergence can also be caused by the deeper capture "
              "itself -- capturing values runs the program's own __repr__ "
              "and slows the run down; the fingerprint cannot tell that "
              "apart from the program genuinely taking another path")
        print_blind_spots(new)
        return NEGATIVE

    # The headline may claim only what was compared. Under the per-task
    # basis the thread rows cover what ran OUTSIDE every task, so for a run
    # with tasks the unqualified sentence is false in the most misleading
    # direction available: the raw per-thread sequence of an order-flipped
    # rerun genuinely differs, and it is the SPLIT -- each thread outside
    # its tasks, plus the task multiset -- that matched.
    if a["thread_scope"]:
        print("refocus verdict: MATCH -- every recorded thread produced the "
              "identical CALL/RETURN/RAISE/HANDLED sequence outside its "
              f"{terms(new).stream_scope}, and every task stream matched "
              "by content")
    else:
        print("refocus verdict: MATCH -- every recorded thread produced the "
              "identical CALL/RETURN/RAISE/HANDLED sequence")
    # The hazard E4" section 5.3 MEASURED, named where the verdict is read.
    # On 1 of its 61 pairs the per-task assignment moved between the two
    # runs -- the workers carried (216, 205, 151, 233, 151) events on one
    # side and (216, 205, 233, 151, 151) on the other, 956 both sides --
    # while the multiset of (name, hash) was identical, so the comparator
    # reported MATCH. That is the comparator working exactly as designed,
    # and it is also a claim this verdict does not make: "every recorded
    # thread produced the identical sequence" reads as a statement about
    # the run's schedule, and no printed line said otherwise.
    #
    # Only where more than one stream was compared, and EACH POPULATION is
    # asked separately. The hazard is a permutation WITHIN one of them --
    # the same shapes arriving on differently numbered members of the same
    # multiset -- so one thread stream beside one task stream is not it:
    # there is a single member on each side and nothing to permute. Summing
    # the two reached 2 on exactly that pair and printed the note where the
    # sentence above says it must not, which is arithmetic across two
    # populations reported as a measurement: this project's own bug class,
    # on the line that exists to bound a claim.
    #
    # With one member there is nothing for a schedule to have assigned
    # differently, and a caveat that cannot apply is noise on every
    # single-threaded pair -- the same rule that took libtest's thread out
    # of the untraced-thread clause.
    #
    # And the NOUN is the population that fired, for the same reason the
    # gate asks them separately. `stream_scope` is the task word ("asyncio
    # tasks" on Python), so a two-thread, zero-task pair printed a caveat
    # about tasks that pair did not have: true of the mechanism, false of
    # the run in front of the reader, and unfalsifiable by anything they
    # could look at. A Rust trace carries exactly one `fingerprints` row --
    # the main thread's, every other thread being a task row
    # (`convert/frames.rs`) -- so `threads` is unreachable there and the
    # Rust sentence is the one it always was.
    threads_permutable = len(new.fingerprints()) > 1
    tasks_permutable = (tasks.get("n_b") or 0) > 1
    if threads_permutable or tasks_permutable:
        scope = terms(new).stream_scope
        if threads_permutable and tasks_permutable:
            carried = f"threads and {scope}"
        elif threads_permutable:
            carried = "threads"
        else:
            carried = scope
        print("note: a MATCH does not say the two runs scheduled the same "
              "way -- the streams are compared as a multiset of (name, "
              "hash), so the same shapes carried by differently numbered "
              f"{carried} match, and which carried which is "
              "recorded and never compared")
    if a["caveats"]:
        print("licence: WITHHELD -- this MATCH is about call shape, and "
              "these checks say it is not a statement about the run as a "
              "whole:")
        for caveat in a["caveats"]:
            print(f"  - {caveat}")
    else:
        print(f"licence: verified against {orig_name} on exactly these "
              "points, and no others:")
        for fact in a["verified"]:
            print(f"  - {fact}")
    print_blind_spots(new)
    return ANSWERED
