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

A THIRD LANGUAGE
----------------
`terms()` falls back to `PYTHON` for a `lang` neither table knows, which is
the same default `Trace.lang` itself takes for a trace with no key -- and it
is a KNOWN limit, not a claim: a third recorder brings a third column with
it, and until then no trace in this format can carry a third value (format 4
requires `lang`, and only two recorders write it).
"""
from dataclasses import dataclass


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
    #: The article `a_task` needs. "an asyncio task", "a test or spawned
    #: thread": the noun cannot carry it and the sentence must not guess.
    task_article: str
    #: How the threads this run started came to exist. Never a guess: it is
    #: the one clause that makes a provenance claim.
    thread_origin: str
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
    #: Why a frame has no local-variable timeline, and what to do about
    #: it. `{mod}` and `{qualname}` name the site. A language whose
    #: recorder produces no LINE events at all has no `--focus` to
    #: suggest, and says why instead of naming a command that refuses.
    timeline_hint: str
    #: `meta` key naming what executed the program, and the line's shape.
    interp_key: str
    interp_fmt: str

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
    task_article="an",
    thread_origin="through Python's own threading/_thread",
    unnamed_task="(name unreadable)",
    numbered_task_note=("task(s) asyncio numbered by creation order, which "
                        "no name can pick"),
    default_name_note=("'{name}' is asyncio's default name and encodes "
                       "creation order, not identity; name the task in the "
                       "program (asyncio.create_task(..., name=...)) to "
                       "compare it by name"),
    timeline_hint=("locals need line-level focus; refocus with --focus "
                   "{mod}:{qualname}"),
    interp_key="python",
    interp_fmt="python {}",
)

RUST = Terms(
    lang="rust",
    task_noun="test or spawned thread",
    task_noun_plural="tests or spawned threads",
    task_article="a",
    thread_origin=("as OS threads (libtest's per-test threads and threads "
                   "spawned by workspace code)"),
    unnamed_task="(unnamed: spawned by dependency code)",
    numbered_task_note=("task(s) with no name at all (spawned by dependency "
                        "code), which no name can pick"),
    default_name_note=None,
    timeline_hint=("this recorder produces no LINE events at all "
                   "(capabilities.line: false), so there is no per-line "
                   "record to focus"),
    interp_key="toolchain",
    interp_fmt="toolchain: {}",
)

_TABLES = {PYTHON.lang: PYTHON, RUST.lang: RUST}


def terms(trace) -> Terms:
    """The table for `trace`, read from the trace and from nothing else."""
    return _TABLES.get(trace.lang, PYTHON)


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
    if basis is None:
        return f"{meta.get('exit_status', '?')}"
    if basis != "waited":
        # Nobody waited, so nothing about the ending is known -- not the
        # code, not the signal. Printing a signal here would name a witness
        # that does not exist.
        return "unwitnessed"
    status = meta.get("exit_status")
    if status is not None:
        return f"{status} ({basis})"
    signal = meta.get("exit_signal")
    if signal is not None:
        return f"signal {signal} ({basis})"
    return f"? ({basis})"
