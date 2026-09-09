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
"""
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
TALLY = "_tally.json"

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
    tally = _tally(spool_dir)
    spools = sorted(spool_dir.glob("*.jsonl"))
    if not spools:
        raise IngestError(f"no spools in {spool_dir}: nothing was recorded, "
                          "or the recorder wrote somewhere else")

    jobs = max(1, min(jobs or os.cpu_count() or 1, len(spools)))
    payload = (inv.to_json(),
               None if harness is None else harness.to_json(),
               str(store_dir), tally)
    summaries: list[Summary] = []
    try:
        _map(jobs, [(str(p), *payload) for p in spools], summaries)
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
    (`imap`, in order), so a worker that dies of something this converter
    did not anticipate does not also take the record of what had already
    converted: `pool.map` returns a list or nothing at all, and nothing at
    all is what would leave the marker unwritable.

    One spool through a process pool costs a whole interpreter start to
    save nothing, and a caller who asked for one job usually wants one
    process -- a debugger's stack, a profiler's numbers.
    """
    if jobs == 1:
        for job in work:
            out.append(_worker(job))
        return
    ctx = multiprocessing.get_context(CONTEXT)
    with ctx.Pool(jobs) as pool:
        for summary in pool.imap(_worker, work):
            out.append(summary)


def _tally(spool_dir: Path) -> dict:
    """The transform's own count of what it covered, or `{}`.

    Written by the Vite plugin on exit into `SENSORIUM_MANIFEST_DIR`, which
    the driver points at `<spool>/manifests`. Absent when the harness never
    transformed anything, or when the plugin could not write it -- and an
    absent tally is written as no meta key at all, never as a zero, because
    "nothing was transformed" and "nobody counted" are different facts.
    """
    path = spool_dir / MANIFEST_DIR / TALLY
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise IngestError(f"{path} is not readable JSON: {e}") from None
    return data if isinstance(data, dict) else {}
