"""A spool directory in, one trace per container out.

`ingest` is deterministic and re-runnable over a directory the driver left
behind, so a driver killed between the harness's exit and the conversion
leaves nothing that cannot be finished by hand. What makes that safe is the
marker it writes at the end (`ingested.json`): a second ingest of one
recording would mint a second set of run ids for the same containers, and
the store would hold each of them twice with nothing to say which was
which. So a directory that carries the marker is REFUSED, by name.

Spools convert in parallel, one worker per spool, over a `spawn` context.
`fork` would hand each worker the parent's threads, its open sqlite
handles and its signal dispositions; nothing here needs any of that, and a
converter that inherits a database handle it did not open is a converter
one bug away from writing into somebody else's file.

The pool is a `ProcessPoolExecutor` and not a `multiprocessing.Pool`,
because a worker can die of a signal it never gets to handle -- the OOM
killer is the ordinary way -- and `Pool.imap` waits for a result that is
never coming. The executor raises `BrokenProcessPool` instead, and a
refusal is a thing a caller can read.
"""
import concurrent.futures
import json
import multiprocessing
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from sensorium.ts import build, invocation, spool

#: The multiprocessing start method. Named so a test can hold it: see the
#: module docstring for why it is not `fork`.
CONTEXT = "spawn"

MARKER = "ingested.json"
MANIFEST_DIR = "manifests"

#: The invocation-wide tally, written by the Vite plugin. vitest transforms
#: in ONE process for the whole run, so its count is every container's.
TALLY = "_tally.json"

#: One container's own, `_tally-<pid>.json`, written by the `node --test`
#: loader hook. That harness runs one child process per test file, each with
#: its own hook thread and its own transform, so the count on such a trace is
#: that container's -- and one shared name would be N writers over one number.
TALLY_PREFIX = "_tally-"

#: How many times a run id is re-minted before the converter gives up. Two
#: containers of one invocation start in the same second, so the stamp
#: collides by design and only the token separates them; a collision is a
#: 1-in-16-million event and a second draw settles it.
MINT_TRIES = 8


class IngestError(Exception):
    """The call cannot proceed: no such directory, no invocation record, or
    a directory that has already been converted. Always names the file."""


@dataclass(frozen=True)
class Summary:
    """One spool's outcome.

    A refusal is a Summary too, with `refused` naming why and the other
    fields left at their empty values. One list of these is the whole
    result of an ingest, so a caller never has to zip two sequences back
    together to find out what happened to a given file.
    """

    file: str
    run_id: str | None = None
    pid: int | None = None
    test_file: str | None = None
    events: int = 0
    tasks: int = 0
    incomplete: bool = False
    refused: str | None = None

    def line(self) -> str:
        """The one line an ingest prints per spool (P7). Two spaces between
        fields, because `corpus.run_corpus.RUN_LINE` reads the first two of
        them and the corpus learns what it just recorded from this string."""
        if self.refused is not None:
            return f"refused: {self.file}  {self.refused}"
        return (f"run: {self.run_id}  pid: {self.pid}  "
                f"file: {self.test_file or '-'}  events: {self.events}  "
                f"tasks: {self.tasks}")


@dataclass
class Ingested:
    """What one ingest did, as the marker records it."""

    summaries: list[Summary] = field(default_factory=list)

    @property
    def refused(self) -> list[str]:
        return [s.file for s in self.summaries if s.refused is not None]

    @property
    def run_ids(self) -> list[str]:
        return [s.run_id for s in self.summaries if s.refused is None]


# --------------------------------------------------------------------------
# one spool


def convert(spool_path, invocation_data: dict, harness_data: dict | None,
            store_dir, tally: dict | None = None) -> Summary:
    """Convert one spool into one trace under `store_dir`.

    `store_dir` is the trace ROOT -- the directory `$SENSORIUM_DIR` names --
    and the trace lands in its `traces/` subdirectory, exactly where
    `paths.find_trace` looks. The two records are passed as plain dicts
    rather than as dataclasses because this function is the body of a
    `spawn`ed worker and everything it is handed is pickled to get there.

    The trace is written under a dotted temporary name and renamed into
    place at the end, so a conversion that refuses half way through leaves
    no `.db` behind for `runs` to list.
    """
    spool_path = Path(spool_path)
    inv = invocation.Invocation.from_json(invocation_data)
    harness = (None if harness_data is None
               else invocation.HarnessExit.from_json(harness_data))
    sp = spool.read(spool_path)

    traces = Path(store_dir) / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    run_id, tmp = _reserve(traces, sp.boot["startTs"])
    builder = build.Builder(sp, inv, harness, tally, tmp, run_id)
    try:
        meta = builder.build()
    except BaseException:
        builder.abort()
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, traces / f"{run_id}.db")
    return Summary(file=spool_path.name, run_id=run_id, pid=sp.boot["pid"],
                   test_file=meta.get("test_file"), events=builder.events,
                   tasks=len(builder.tasks),
                   incomplete=meta["incomplete"])


def _reserve(traces: Path, start_ts: float) -> tuple[str, Path]:
    """A run id no trace in this store holds, CLAIMED before it is returned.

    The temporary file is created here, `O_EXCL`, and that creation IS the
    reservation: two spawn workers converting two containers of one
    invocation mint from the same second, so they collide on the stamp by
    design and only the token separates them -- and a pair that looked with
    `exists()` and then wrote could both have looked before either wrote.
    `O_EXCL` is one atomic step and the loser simply draws again.

    The empty file is handed straight to `TraceWriter`; sqlite opens a
    zero-length file as a new database and lays the schema into it, which is
    exactly what it would have done had it created the file itself.
    """
    for _ in range(MINT_TRIES):
        run_id = build.mint_run_id(start_ts, secrets.token_hex(3))
        tmp = traces / f".{run_id}.db.tmp"
        if (traces / f"{run_id}.db").exists():
            continue
        try:
            os.close(os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
        except FileExistsError:
            continue
        return run_id, tmp
    raise IngestError(f"could not mint a free run id in {traces} after "
                      f"{MINT_TRIES} tries")


def _worker(job: tuple) -> Summary:
    """One spool, in its own process. Refusals come back as values, not as
    exceptions: a spool this converter cannot read must not stop the ones
    beside it, and the run's exit status is decided once, at the end, over
    the whole list."""
    path, inv, harness, store_dir, tally = job
    try:
        return convert(path, inv, harness, store_dir, tally)
    except spool.SpoolError as e:
        return Summary(file=Path(path).name, refused=str(e))


# --------------------------------------------------------------------------
# the directory


def ingest_dir(spool_dir, store_dir, jobs: int | None = None) -> list[Summary]:
    """Every spool in `spool_dir`, converted into `store_dir`.

    Spools are converted in NAME order and the summaries come back in that
    order, so two ingests of one directory print their lines the same way
    round however the pool scheduled them.
    """
    spool_dir = Path(spool_dir)
    if not spool_dir.is_dir():
        raise IngestError(f"{spool_dir} is not a directory")
    marker = spool_dir / MARKER
    if marker.exists():
        raise IngestError(
            f"{marker} already exists: this spool directory has been "
            "converted, and converting it again would mint a second run id "
            "for every container in it")

    inv = invocation.read_invocation(spool_dir)
    harness = invocation.read_harness(spool_dir)
    shared = _tally(spool_dir)
    spools = sorted(spool_dir.glob("*.jsonl"))
    if not spools:
        raise IngestError(_no_spools(spool_dir))

    jobs = max(1, min(jobs or os.cpu_count() or 1, len(spools)))
    payload = (inv.to_json(),
               None if harness is None else harness.to_json(),
               str(store_dir))
    work = [(str(p), *payload, _tally_for(spool_dir, p, shared))
            for p in spools]
    summaries: list[Summary] = []
    try:
        _map(jobs, work, summaries)
    except Exception as e:
        # Whatever this was, traces are already in the store and P6's marker
        # is the only record of which ones. Writing it here is what keeps a
        # re-ingest from minting a SECOND run id for a container that already
        # converted -- the failure mode the marker exists to stop does not
        # care why the run stopped.
        _write_marker(marker, summaries, f"{type(e).__name__}: {e}")
        raise IngestError(
            f"{type(e).__name__}: {e} -- {len(summaries)} spool(s) converted "
            f"before it; {marker} records them") from e
    _write_marker(marker, summaries, None)
    return summaries


def _write_marker(marker: Path, summaries: list[Summary],
                  error: str | None) -> None:
    """P6's record of what this directory converted to.

    `error` is present only on a run that did not finish, and names what
    stopped it: a marker that said nothing about it would read as a complete
    ingest of a directory only part of which was converted.
    """
    result = Ingested(summaries=summaries)
    body: dict = {"run_ids": result.run_ids, "refused": result.refused}
    if error is not None:
        body["error"] = error
    marker.write_text(json.dumps(body, indent=2) + "\n")


def _map(jobs: int, work: list[tuple], out: list[Summary]) -> None:
    """The pool, or no pool at all for a single job, appending to `out`.

    The accumulator is the CALLER's, and results are taken one at a time
    (`map`, in order), so a worker that dies of something this converter
    did not anticipate does not also take the record of what had already
    converted: a call that returned a list or nothing at all is what would
    leave the marker unwritable.

    `ProcessPoolExecutor` and not `multiprocessing.Pool` (R42). A worker
    SIGKILLed -- by the OOM killer, by a `kill -9`, by any signal it
    cannot catch -- never puts a result on the queue, and `Pool.imap`
    waits for one FOREVER: the driver hung with no output and nothing to
    interrupt but itself. The executor notices its child is gone and
    raises `BrokenProcessPool`, which the caller's `except Exception`
    turns into the marker plus a named refusal at exit 2. Measured: 60 s
    of nothing under `imap`, immediate under the executor.

    One spool through a process pool costs a whole interpreter start to
    save nothing, and a caller who asked for one job usually wants one
    process -- a debugger's stack, a profiler's numbers.
    """
    if jobs == 1:
        for job in work:
            out.append(_worker(job))
        return
    ctx = multiprocessing.get_context(CONTEXT)
    with concurrent.futures.ProcessPoolExecutor(jobs, mp_context=ctx) as ex:
        for summary in ex.map(_worker, work):
            out.append(summary)


#: What a directory with no spool in it says when its tallies explain
#: nothing: the run may have gone wrong anywhere between the harness and the
#: disk, and this converter does not guess which.
NOTHING_RECORDED = ("nothing was recorded, or the recorder wrote somewhere "
                    "else")


def _no_spools(spool_dir: Path) -> str:
    """The refusal for a directory holding no spool at all (R45).

    A CommonJS-only suite runs GREEN under `node --test` and records
    nothing -- every file the hook met was excluded before it was parsed --
    and `NOTHING_RECORDED` names neither that cause nor its fix. The
    tallies beside the missing spools do: when every one of them counted
    zero transforms and at least one exclusion, that IS what happened, and
    the refusal says so by reason and by count.

    Anything else keeps the old sentence. A run that transformed a file and
    still wrote no spool went wrong somewhere no tally can see, and naming
    CommonJS there would be a guess dressed as a diagnosis.
    """
    tallies = [_read_tally(p) for p in _tally_files(spool_dir)]
    counts: dict[str, int] = {}
    for tally in tallies:
        if tally.get("files_transformed") != 0 or not tally.get("excluded"):
            counts = {}
            break
        for reason, n in tally["excluded"].items():
            counts[reason] = counts.get(reason, 0) + n
    if not counts:
        return f"no spools in {spool_dir}: {NOTHING_RECORDED}"
    reasons = ", ".join(f"{reason} x{n}" for reason, n in sorted(counts.items()))
    line = (f"no spools in {spool_dir}: this run transformed 0 files and "
            f"excluded {sum(counts.values())} ({reasons} across "
            f"{len(tallies)} tallies)")
    if "commonjs" in counts:
        line += ("; this recorder instruments ES modules only, so a "
                 "CommonJS-only suite records nothing")
    return line


def _tally_files(spool_dir: Path) -> list[Path]:
    """Every tally an invocation left, the shared one first: what the two
    harnesses wrote between them, whichever of them ran."""
    manifests = spool_dir / MANIFEST_DIR
    shared = [manifests / TALLY] if (manifests / TALLY).is_file() else []
    return shared + sorted(manifests.glob(f"{TALLY_PREFIX}*.json"))


def _tally(spool_dir: Path) -> dict:
    """The invocation's own count of what the transform covered, or `{}`.

    Written by the Vite plugin on exit into `SENSORIUM_MANIFEST_DIR`, which
    the driver points at `<spool>/manifests`. Absent when the harness never
    transformed anything, or when the plugin could not write it -- and an
    absent tally is written as no meta key at all, never as a zero, because
    "nothing was transformed" and "nobody counted" are different facts.
    """
    return _read_tally(spool_dir / MANIFEST_DIR / TALLY)


def _tally_for(spool_dir: Path, spool: Path, shared: dict) -> dict:
    """This container's own count, falling back to the invocation's.

    A spool is named `<pid>-<threadId>.jsonl`, and under `node --test` that
    pid is also the pid of the process that did the transforming: the
    harness runs one child per test file, so what a container was told
    about is what that child transformed. vitest transforms once for the
    whole run and writes the invocation-wide file instead, which every
    container of it shares.
    """
    pid = spool.name.split("-")[0]
    if pid.isdigit():
        own = _read_tally(spool_dir / MANIFEST_DIR
                          / f"{TALLY_PREFIX}{pid}.json")
        if own:
            return own
    return shared


def _read_tally(path: Path) -> dict:
    """One tally file, or `{}`. Unreadable JSON is a refusal and not a
    zero: a count nobody can read is not a count of nothing."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise IngestError(f"{path} is not readable JSON: {e}") from None
    return data if isinstance(data, dict) else {}
