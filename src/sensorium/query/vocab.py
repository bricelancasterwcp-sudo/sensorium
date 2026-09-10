"""The words a reader uses about a trace, keyed on `meta["lang"]`.

WHY THIS IS A CORRECTNESS MODULE AND NOT A STYLE ONE
----------------------------------------------------
Every renderer in `query/` was written when one recorder existed, so its
sentences say `asyncio task`, `through Python's own threading/_thread` and
`python <version>` about facts that are not Python's. Rung 1 ran those
renderers over a real `sensorium-rt` trace and read back, verbatim:

    python ?
    ... (0 causal events outside any asyncio task)
    threads started: 26 besides the main one, through Python's own
    threading/_thread ...

The first names an interpreter that never ran. The last is a positive claim
about PROVENANCE the trace does not carry -- those 26 threads are libtest's,
and nothing in the file says otherwise. A reader that invents provenance is
the same failure as a reader that prints an absent record as a zero, which
is what format 4 exists to stop; this module is that rule applied to prose.

THE PYTHON COLUMN IS A MOVE, NOT A REWRITE
-------------------------------------------
Every string in `PYTHON` is the exact string the renderer printed before
this module existed, character for character. The legacy suite is the fence:
a reworded Python sentence is a regression, however much better it reads.
`RUST` is the new column, and it says only what a `sensorium-rt` trace
actually holds (`rust/HONESTY.md` sections 3 and 5).

A THIRD LANGUAGE, AND THE REFUSAL OF A FOURTH (amended 2026-09-09, S5)
----------------------------------------------------------------------
`TYPESCRIPT` is the third column, and it says only what a `sensorium-ts`
trace actually holds (`typescript/HONESTY.md` sections 1 to 6).

Until S5 `terms()` FELL BACK to `PYTHON` for a `lang` no table knew. That
was defensible only while no trace could carry an unknown value; it is a
falsehood the moment one can, because the fallback tells a reader of a
COBOL trace about `asyncio tasks` and `python ?` -- the exact rung-1 bug
this module exists for, one language further out. So the lookup is now
STRICT, and the refusal lives one level down where every command reaches
it: `db.open_trace` refuses a trace whose `lang` is outside
`db.KNOWN_LANGS`, naming the language, the recorder and this sensorium's
version (exit 2). A `KeyError` from `_TABLES` is therefore unreachable
through the CLI and means a caller built a `Trace` around the store's
back. A trace with NO `lang` key still reads as Python: nothing else
existed before the key.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Terms:
    """One language's words. Frozen: a renderer reads this table, never
    edits it, and two commands reading one trace must not differ."""

    #: `meta["lang"]` this table answers for.
    lang: str
    #: What one unit of work is called, singular.
    task_noun: str
    #: ...and in the plural, as the sentences that count them spell it.
    task_noun_plural: str
    #: The units a thread's fingerprint row leaves OUT under the per-task
    #: basis, as prose after a POSSESSIVE -- "...sequence outside its ...".
    #: Neither noun beside it fits that slot: `task_noun_plural` is written
    #: for sentences that COUNT ("2 asyncio task(s)") and its parentheses
    #: read wrongly in prose, and `blind_spot_tasks` is written for a slot
    #: with no possessive ("the order libtest's per-test threads and
    #: spawned threads interleaved in"), which after "its" would read "its
    #: libtest's". The singular slot -- "outside any ..." -- is `task_noun`
    #: and needs no field of its own.
    stream_scope: str
    #: The article `a_task` needs. "an asyncio task", "a test or spawned
    #: thread": the noun cannot carry it and the sentence must not guess.
    task_article: str
    #: How the threads this run started came to exist. Never a guess: it is
    #: the one clause that makes a provenance claim.
    thread_origin: str
    #: What a thread the RECORDER'S OWN harness started is called, and why
    #: it is left out of the counts of the program's threads -- printed
    #: wherever such a count is, so the exclusion is named and never
    #: silent. `None` for a recorder that starts no thread of its own, and
    #: then nothing is ever excluded from any count.
    harness_thread: str | None
    #: The label for a unit of work with no readable name -- and the two
    #: languages mean DIFFERENT things by it. In Python the name existed and
    #: `get_name()` raised; in Rust the thread was spawned by dependency
    #: code and has no name at all (`rust/HONESTY.md` section 3).
    unnamed_task: str
    #: How to describe the units a name cannot pick out, in `diff --task`.
    numbered_task_note: str
    #: `{name}` template for the refusal to compare a unit by a name its
    #: runtime minted rather than its program. `None` where the language
    #: mints no such names -- and then no name is ever read as "no name",
    #: because there is no numbering scheme to read it as.
    default_name_note: str | None
    #: What a reader may do INSTEAD, when `refocus` is refused. Naming a
    #: command that cannot read this trace is worse than naming none: it
    #: sends the reader to a second refusal.
    no_rerun_note: str
    #: What a `refocus` verdict on THIS recorder's traces additionally says
    #: nothing about, printed after the categorical blind-spot block. Empty
    #: where the language adds nothing to it. Each line is a bounded fact
    #: about the recorder or about the re-run mechanism, never an
    #: enumeration that could read as complete -- the categorical block
    #: above it is what bounds the claim.
    refocus_blind_spots: tuple[str, ...]
    #: The four lines of `refocus`'s categorical blind-spot block that name
    #: a LANGUAGE. The other five are the same statement about any recorder
    #: and stay in `refocus_cmd`; these four said "Python code", "Python's
    #: own threading/_thread", "site-packages / PYTHONPATH modules" and
    #: "__repr__" over a Rust verdict, which is the rung-1 bug this module
    #: exists for, printed on the one block whose whole job is to bound what
    #: a verdict claims. Each is the WHOLE line, prefix included, so the
    #: Python column stays byte-for-byte what it printed before.
    #:
    #: `blind_spot_scope` opens the block and ends in the colon the other
    #: lines hang off; the rest are bullets.
    blind_spot_scope: str
    blind_spot_threads: str
    blind_spot_outside: str
    blind_spot_footprint: str
    #: What the units of concurrent work are CALLED in the one shared
    #: blind-spot line that names them -- "the order <these> interleaved
    #: in". The rest of that line is the same statement about any recorder,
    #: so only the noun travels. Not `task_noun_plural`: that one is written
    #: for sentences that COUNT ("2 asyncio task(s)"), and its parentheses
    #: read wrongly in prose.
    blind_spot_tasks: str
    #: Why a frame has no local-variable timeline, and what to do about
    #: it. `{mod}` and `{qualname}` name the site. A language whose
    #: recorder produces no LINE events at all has no `--focus` to
    #: suggest, and says why instead of naming a command that refuses.
    timeline_hint: str
    #: `meta` key naming what executed the program, and the line's shape.
    interp_key: str
    interp_fmt: str
    #: `frames.kind` -> the word this language calls that construct, for
    #: the `[...]` marker `tree` and `frame` print. The CONTRACT's
    #: enumeration is fixed (`function`, `coroutine`, `generator`,
    #: `async_generator`, TRACE-FORMAT section 3) and a converter writes
    #: those values whatever the language; what a READER prints for them is
    #: the language's own word, and JavaScript has no coroutines. Empty
    #: where the contract's spelling is already the language's, so a
    #: `.get(kind, kind)` leaves Python's and Rust's markers untouched.
    #:
    #: A `MappingProxyType` on every column: `frozen=True` freezes the
    #: ATTRIBUTE, not what it points at, and these three tables are module
    #: singletons every renderer shares. A renderer that wrote through
    #: `terms(trace).kind_labels[...]` would silently retune every later
    #: command in the process -- the one way a table whose whole purpose is
    #: that two commands cannot differ could make them differ.
    kind_labels: Mapping[str, str]
    #: Why `exceptions` cannot judge a trace in this language, or `None`
    #: where it can. Not a vocabulary problem and not a capability one:
    #: what is missing is a set of DISPOSITION RULES, and the sentence
    #: names the rung that owes them. `None` for every language that HAS
    #: rules: Python (whose rules these are), Rust and TypeScript, each
    #: dispatched to its own rule module before the refusal is read. The
    #: field survives for a fourth language, so the refusal stays a fact
    #: about a language rather than a fallback for everything that is not
    #: Python.
    exceptions_refusal: str | None

    @property
    def a_task(self) -> str:
        return f"{self.task_article} {self.task_noun}"

    def interp_line(self, meta: dict) -> str:
        """What ran this program, from the trace's own key. `?` when the key
        is absent -- the reader does not substitute its own interpreter."""
        return self.interp_fmt.format(meta.get(self.interp_key) or "?")


PYTHON = Terms(
    lang="python",
    task_noun="asyncio task",
    task_noun_plural="asyncio task(s)",
    stream_scope="asyncio tasks",
    task_article="an",
    thread_origin="through Python's own threading/_thread",
    # `sensorium run` starts the program on the thread it was invoked from:
    # every other thread in a Python trace is the program's own.
    harness_thread=None,
    unnamed_task="(name unreadable)",
    numbered_task_note=("task(s) asyncio numbered by creation order, which "
                        "no name can pick"),
    default_name_note=("'{name}' is asyncio's default name and encodes "
                       "creation order, not identity; name the task in the "
                       "program (asyncio.create_task(..., name=...)) to "
                       "compare it by name"),
    no_rerun_note=("no rerun was attempted; `sensorium run --focus ...` "
                   "will record a fresh, UNVERIFIED trace if that is what "
                   "you want"),
    # The Python column adds nothing: the nine lines of `blind_spots` were
    # written for this recorder and already state every one of its limits.
    refocus_blind_spots=(),
    # Byte for byte the strings `refocus_cmd` held before this move. The
    # legacy suite is the fence: a reworded Python sentence is a regression.
    blind_spot_scope=(
        "what sensorium sees at all: Python code that this run traced, in "
        "files under the run's own root. Nothing else. No verdict here -- "
        "MATCH, DIVERGED or REFUSED -- says anything about:"),
    blind_spot_threads=(
        "  - any thread not started through Python's own threading/_thread"),
    blind_spot_outside=(
        "  - any code outside the run's root: the stdlib, site-packages, "
        "installed dependencies, PYTHONPATH modules, and whatever this "
        "run's own --include/--exclude filtered out"),
    blind_spot_footprint=(
        "  - the recorder's own footprint: deeper capture runs the "
        "program's __repr__ inside hooks that suppress themselves, so an "
        "instrument that changes the program leaves no mark on the "
        "fingerprint"),
    blind_spot_tasks="asyncio tasks",
    timeline_hint=("locals need line-level focus; refocus with --focus "
                   "{mod}:{qualname}"),
    interp_key="python",
    interp_fmt="python {}",
    # The contract's kind words ARE Python's: `[coroutine]`,
    # `[async_generator]` are what every Python trace has printed, and the
    # legacy suite is the fence around them.
    kind_labels=MappingProxyType({}),
    exceptions_refusal=None,
)

RUST = Terms(
    lang="rust",
    task_noun="test or spawned thread",
    task_noun_plural="tests or spawned threads",
    # A Rust thread row holds the MAIN thread's own events: every other
    # thread's stream is a `task_fingerprints` row (`convert/frames.rs`).
    # So what the row is "outside" is the test and spawned threads -- said
    # in the shortest form that survives a possessive.
    stream_scope="test and spawned threads",
    task_article="a",
    thread_origin=("as OS threads (libtest's per-test threads and threads "
                   "spawned by workspace code)"),
    # libtest runs every `#[test]` fn on a thread of its own, so a `cargo
    # test` trace carries one thread the program did not start -- and the
    # untraced-thread caveat fired on all 61 pairs of E4 for that reason
    # alone (design 2026-09-07 R1). Named, never quietly dropped: the
    # precedent is the recorder's own environment variables, which the same
    # licence already excludes by name.
    harness_thread="libtest's per-test thread, excluded as the recorder's own",
    unnamed_task="(unnamed: spawned by dependency code)",
    numbered_task_note=("task(s) with no name at all (spawned by dependency "
                        "code), which no name can pick"),
    default_name_note=None,
    # Retired with rung 4 (design 2026-09-07 section 3.2): refocus on a Rust
    # trace no longer "arrives" with anything, so the note says what a
    # reader may do INSTEAD of the re-run that was refused -- and names the
    # command that can read this trace, not `sensorium run`, which cannot.
    no_rerun_note=("no rerun was attempted; `cargo sensorium --focus ... "
                   "test|run` will record a fresh, UNVERIFIED trace if that "
                   "is what you want"),
    refocus_blind_spots=(
        "output not recorded (capabilities.output: false)",
        "threads from dependency code are unnamed",
        "the re-run's rebuild is its own cost: --focus keys a fresh shim "
        "and a rebuild of the matched units",
    ),
    # What this recorder actually sees, said in its own terms. The unit of
    # coverage is the workspace unit cargo rebuilt through the wrapper --
    # not "files under the run's root", which is Python's -- and the
    # instrument's footprint is a `Debug` impl run inside the probe, not a
    # `__repr__` run inside a suppressed hook.
    blind_spot_scope=(
        "what sensorium sees at all: Rust code in the workspace units cargo "
        "rebuilt through this recorder's wrapper. Nothing else. No verdict "
        "here -- MATCH, DIVERGED or REFUSED -- says anything about:"),
    blind_spot_threads=(
        "  - any thread whose body ran no instrumented code: it leaves no "
        "fingerprint, so it is not among the compared"),
    blind_spot_outside=(
        "  - any code outside the instrumented units: dependency crates, "
        "the standard library, build scripts and proc macros, and every "
        "unit that fell back uninstrumented"),
    blind_spot_footprint=(
        "  - the recorder's own footprint: capturing values runs the "
        "program's own Debug impls inside the probe, so an instrument that "
        "changes the program leaves no mark on the fingerprint"),
    blind_spot_tasks="libtest's per-test threads and spawned threads",
    timeline_hint=("this recorder produces no LINE events at all "
                   "(capabilities.line: false), so there is no per-line "
                   "record to focus"),
    interp_key="toolchain",
    interp_fmt="toolchain: {}",
    # A Rust trace carries `function` frames and nothing else today, and a
    # future `coroutine` there would be an `async fn` -- which is what the
    # contract's word already says. Nothing to rename.
    kind_labels=MappingProxyType({}),
    # Dispatched to `exceptions_rust` before `_language_refusal` is ever
    # read, so this column has no refusal to offer: what an older Rust
    # recording lacks is a RECORD, and `capabilities.err_flow` says so in
    # its own sentence (`v19-err-flow-capability-refusal`).
    exceptions_refusal=None,
)

TYPESCRIPT = Terms(
    lang="typescript",
    task_noun="test",
    task_noun_plural="test(s)",
    stream_scope="tests",
    task_article="a",
    # Never "the program started none": a worker thread and a forked child
    # are each their own container with their own spool, so they exist and
    # are recorded -- as separate traces this one cannot link to. The clause
    # says which of those two facts this is (`capabilities.threads: false`).
    thread_origin=("as worker threads or forked children of the harness "
                   "(not witnessed: each is its own trace)"),
    # `ts run` starts the harness, and the harness starts the containers:
    # every trace is one container, one thread, and no thread in it is the
    # recorder's own.
    harness_thread=None,
    # Not "the name was unreadable": the title expression evaluated to
    # something that is not a string, so vitest itself has no name for this
    # test either (`typescript/HONESTY.md` section 2).
    unnamed_task="(unnamed: title not a string)",
    numbered_task_note=("test(s) whose title was not a string, which no "
                        "name can pick"),
    # vitest mints no name of its own: an unnamed test is unnamed, and
    # `.each` rows are renamed by the harness into names that ARE the
    # program's. There is no numbering scheme to read as "no name".
    default_name_note=None,
    no_rerun_note=("no rerun was attempted; this recorder records one tier "
                   "and has no deeper capture to re-run for (S5 rung 3)"),
    refocus_blind_spots=(
        "output not recorded (capabilities.output: false)",
        "arguments are not read in this version (capabilities.locals: "
        "false)",
    ),
    blind_spot_scope=(
        "what sensorium sees at all: TypeScript and JavaScript files under "
        "the invocation's root that the transform edited. Nothing else. No "
        "verdict here -- MATCH, DIVERGED or REFUSED -- says anything "
        "about:"),
    blind_spot_threads=(
        "  - any container the program spawned itself: a worker thread or "
        "a child process records as its own trace, unlinked"),
    blind_spot_outside=(
        "  - any code outside the transformed files: node_modules, Node's "
        "own modules, the harness, and every file the transform excluded"),
    blind_spot_footprint=(
        "  - the recorder's own footprint: capturing values runs the "
        "program's own inspect customisations inside the probe, so an "
        "instrument that changes the program leaves no mark on the "
        "fingerprint"),
    blind_spot_tasks="tests",
    # No `{mod}`/`{qualname}`: there is no per-line record to focus, so
    # there is no site to name. `frame_cmd` still calls `.format` with both
    # keywords, which a template with no placeholder simply ignores.
    timeline_hint=("this recorder produces no LINE events "
                   "(capabilities.line: false); per-line capture is S5 "
                   "rung 3"),
    interp_key="node",
    interp_fmt="node {}",
    # JavaScript's words for the contract's kinds (`typescript/HONESTY.md`
    # section 1). `generator` is already JavaScript's own and is not
    # renamed -- which is why `tests/test_vocab.py` may not forbid that
    # word on a TypeScript trace the way it forbids `coroutine`.
    kind_labels=MappingProxyType({"coroutine": "async",
                                 "async_generator": "async generator"}),
    # Dispatched to `exceptions_typescript` before `_language_refusal` is
    # ever read, so this column has no refusal to offer either: what an
    # 0.1.x TypeScript recording lacks is a RECORD, and
    # `capabilities.err_flow` says so in its own sentence
    # (`v32-err-flow-typescript-capability-refusal`). The sentence that
    # stood here named the rules S5 rung 2 owed; rung 2 shipped them.
    exceptions_refusal=None,
)

_TABLES = {PYTHON.lang: PYTHON, RUST.lang: RUST, TYPESCRIPT.lang: TYPESCRIPT}


def terms(trace) -> Terms:
    """The table for `trace`, read from the trace and from nothing else.

    STRICT since S5: a `lang` with no column raises `KeyError` rather than
    borrowing Python's words. Nothing reachable through the CLI can do
    that -- `db.open_trace` refuses an unknown `lang` before any command
    holds a `Trace` -- so a raise here is a programming error, and the
    fallback it replaces was a wrong ANSWER (see this module's header).
    """
    return _TABLES[trace.lang]


# Five of the nine are the same statement about any recorder and live here.
# The other four NAME A LANGUAGE, and are the trace's own (`vocab.Terms`):
# printed flat, this block told a reader of a Rust verdict that what
# sensorium sees is "Python code that this run traced" and that no thread
# started "through Python's own threading/_thread" -- the rung-1 provenance
# bug, on the one block whose whole job is to bound what a verdict claims.
_SHARED_BLIND_SPOTS = (
    "  - any child process, by any mechanism. Some are noticed and listed "
    "above; an empty list is NOT evidence that none ran",
    "  - any file the program read or wrote. Only SOURCE files are hashed, "
    "so config, fixtures, databases and inputs move unseen",
    # NOT "and nothing outside the environment is compared at all": source
    # contents, stdout/stderr and exit status are all compared, and the
    # source line saying so prints twelve lines above this block.
    "  - any environment variable this run did not compare; the ones it "
    "skipped are named above",
    "  - the clock, the network, and everything else the machine did",
)

# The task clause is not decoration: this version deliberately compares task
# streams as a multiset, so an order flip comes back MATCH. The thing a
# verdict is built on NOT looking at has to be stated on every verdict, or
# the MATCH reads as "the tasks ran the same way" -- and it has to be stated
# in the words of the recorder that ran them. `{tasks}` is the ONE part of
# this line that names a language; everything else is true of any recorder,
# which is why the line lives here and the noun lives in `Terms`.
_VALUES_BLIND_SPOT = (
    "  - argument and return values, per-line state, timing, the order "
    "threads ran in relative to one another, and the order {tasks} "
    "interleaved in: recorded, never compared")


def blind_spots(trace) -> tuple[str, ...]:
    """The categorical block for `trace`, in the order it prints.

    Order is the Python column's, unchanged: scope, children, threads,
    files, outside, environment, machine, values, footprint -- then any
    line the recorder adds for itself (`refocus_blind_spots`). A recorder
    with nothing to add contributes nothing, so the Python output is what
    it always was, character for character.
    """
    t = terms(trace)
    child, files, env, machine = _SHARED_BLIND_SPOTS
    values = _VALUES_BLIND_SPOT.format(tasks=t.blind_spot_tasks)
    return ((t.blind_spot_scope, child, t.blind_spot_threads, files,
             t.blind_spot_outside, env, machine, values,
             t.blind_spot_footprint)
            + tuple(f"  - {line}" for line in t.refocus_blind_spots))


def print_blind_spots(trace) -> None:
    """Printed on EVERY verdict, and CATEGORICAL on purpose.

    An earlier version listed the mechanisms sensorium cannot see. Two more
    arrived within a day -- a `multiprocessing` child spawned through
    `_posixsubprocess.fork_exec`, and a `COLUMNS` change hidden by the
    volatile denylist -- and the list was worse than useless for them: it
    read as EXHAUSTIVE, so a reader who checked it concluded their
    multiprocessing child had been witnessed. An enumeration that looks
    complete is more dangerous than no enumeration. Every line is bounded by
    what the instrument IS rather than by what has been thought of so far,
    so the block stays true when the next mechanism appears -- and `trace`
    is required rather than defaulted for the same reason `_refuse` requires
    it: no call site may reach this line without saying which recorder it is
    speaking for.
    """
    for line in blind_spots(trace):
        print(line)


def exit_phrase(meta: dict) -> str:
    """How the recorded process ended, with the basis on which that is
    known -- `0`, `0 (waited)`, `signal 9 (waited)`, `unwitnessed`.

    `exit_status` may be NULL, and a null is not a status: rendered as
    `None` (which is what `.get` + f-string did) it reads as an exit code
    the program actually ended with. `exit_status_basis` is the key that
    tells the two apart (spec D4): "waited" means a parent -- the cargo
    runner shim -- called `wait` and read the status; "unwitnessed" means
    nobody did, which is the state of every process a test spawned itself.

    A trace with no basis key at all predates the distinction and is the
    Python recorder's, whose parent always waited; it renders exactly as it
    always has, `?` included (a run that never finalized has no status, and
    `?` is not a status either).
    """
    basis = meta.get("exit_status_basis")
    core = exit_brief(meta)
    # The basis is worth a word only where it says something the status does
    # not: `unwitnessed` already IS the basis, and a trace with no basis key
    # predates the distinction and must read exactly as it always did.
    return f"{core} ({basis})" if basis == "waited" else core


def exit_brief(meta: dict) -> str:
    """The same fact without the basis, for the one-line listing.

    `runs` gives every trace one dense row and the basis does not fit in it:
    `exit:0`, `exit:signal 9`, `exit:unwitnessed`. Nothing is hidden by the
    shortening -- `unwitnessed` is exactly the case where the basis is the
    whole answer, and it is the word printed. `info` is where `(waited)`
    belongs, beside the room to say what it means.
    """
    basis = meta.get("exit_status_basis")
    if basis is None:
        return f"{meta.get('exit_status', '?')}"
    if basis != "waited":
        # Nobody waited, so nothing about the ending is known -- not the
        # code, not the signal. Printing a signal here would name a witness
        # that does not exist.
        return "unwitnessed"
    status = meta.get("exit_status")
    if status is not None:
        return f"{status}"
    signal = meta.get("exit_signal")
    if signal is not None:
        return f"signal {signal}"
    return "?"
