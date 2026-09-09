"""The TypeScript spool fixtures, and the machinery both `test_ts_ingest`
modules drive them with.

Every fixture under `tests/fixtures/ts-spools/<case>/` is a spool directory
as the driver leaves one -- `invocation.json`, an optional `harness.json`,
one `<pid>-<threadId>.jsonl` per container, an optional
`manifests/_tally.json`. Both test modules drive the REAL command line
against the traces those convert to, exactly as `tests/test_rust_convert.py`
does for the Rust converter.

PROVENANCE OF THE FIXTURES
--------------------------
Five cases are RECORDED, not written. `typescript/probes/README.md` gives
the recipe; each was run with `SENSORIUM_TIER=call`, the spool was
identified by its `FILE_START` path, and it was then passed through
`tests/fixtures/ts-spools/sanitize.py` (the recorded root -> `/w/probes`,
the node binary's directory -> `/usr/bin`, `BOOT.env` ->
`{"PATH": "/usr/bin"}`, `envHash` deliberately left as recorded):

    async-chain           src/async.probe.test.ts     E3 S1-S4 + T1/T2
    each-names            src/each.probe.test.ts      `test.each`, three rows
    unhandled-rejection   src/swallow3.probe.test.ts  E8 shape 3
    throw-flow            src/swallow.probe.test.ts   E8 shapes 1, 2, 4, 5
    generator-yield       src/sites.probe.test.ts     E4's 20 shapes

`killed-mid-file` is `async-chain`'s spool cut where a SIGKILL would cut it:
its first 120 whole lines plus the first 30 bytes of line 121, so both the
torn tail and the missing EXIT are exercised by one file.

`outside-frame-throw`, `capped-names`, `no-boot`, `duplicate-boot` and
`unknown-frame` are hand-written, small enough to read. `unknown-frame`
carries the one wire record no probe produces: NOTHING under `probes/` lets
an exception leave a frame -- every shape there swallows what it throws --
so an `UNWIND` has no recorded example and is written by hand.
`capped-names` is the other limbs no probe reaches: a title and a type name
the 200-byte cap bit, a second activation carrying the recorder's `#2`, and
a container vitest tore down with a signal.

`invocation.json` is hand-written for every case: no driver exists yet
(Task 6), and the contract these fixtures hold is
`sensorium.ts.invocation`'s, not a recording's.
"""
import re
from pathlib import Path

import pytest

from sensorium.store.reader import Trace
from tests.helpers import run_cli

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ts-spools"

CASES = sorted(p.name for p in FIXTURES.iterdir()
               if (p / "invocation.json").is_file())

#: Cases whose directory holds a spool the converter must refuse, and so
#: whose `ingest` ends at exit 2 with the rest of the directory converted
#: anyway.
REFUSING = {"no-boot": "7101-0.jsonl", "duplicate-boot": "7201-0.jsonl",
            "unknown-frame": "7301-0.jsonl"}

#: The `run:` line of P7, field by field. `corpus.run_corpus.RUN_LINE` reads
#: the first two fields of this same line, and one test holds the two to
#: each other -- the corpus learns what it just recorded from this string.
RUN_LINE = re.compile(
    r"^run: (?P<run_id>\S+)  pid: (?P<pid>\d+)  file: (?P<file>\S+)  "
    r"events: (?P<events>\d+)  tasks: (?P<tasks>\d+)$", re.MULTILINE)


def ingest_case(case: str, tmp_path: Path, jobs: int | None = None):
    """Copy one case's spool directory somewhere writable and ingest it with
    the REAL CLI. Returns `(spool_dir, sdir, CompletedProcess)`.

    The copy matters: `ingest` writes `ingested.json` into the directory it
    read, and a fixture directory is not the converter's to write in.
    """
    spool = tmp_path / "spool"
    copy_tree(FIXTURES / case, spool)
    sdir = tmp_path / "sdir"
    args = ["ts", "ingest", str(spool)]
    if jobs is not None:
        args += ["--jobs", str(jobs)]
    return spool, sdir, run_cli(args, cwd=tmp_path, sensorium_dir=sdir)


def copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.is_dir():
            copy_tree(child, dst / child.name)
        else:
            (dst / child.name).write_bytes(child.read_bytes())


@pytest.fixture(scope="module")
def ingested(tmp_path_factory):
    """Every case ingested once, shared by the tests that only read the
    result. Module-scoped because conversion spawns a process pool and the
    read-only tests would otherwise pay for it a dozen times."""
    out = {}
    for case in CASES:
        base = tmp_path_factory.mktemp(f"ts-{case}")
        out[case] = ingest_case(case, base)
    return out


def run_ids_in(stdout: str) -> list[str]:
    return [m.group("run_id") for m in RUN_LINE.finditer(stdout)]


def open_run(sdir: Path, run_id: str) -> Trace:
    return Trace.open(sdir / "traces" / f"{run_id}.db")


def only_trace(sdir: Path) -> Trace:
    dbs = sorted((sdir / "traces").glob("*.db"))
    assert len(dbs) == 1, [p.name for p in dbs]
    return Trace.open(dbs[0])


def sub(value, ids: list[str]):
    """`$RUN` / `$RUN2` -> the ids this case converted to, over every string
    in a question. `$RUN2` first: substituting `$RUN` first turns `$RUN2`
    into `<id>2`, a silent wrong lookup instead of an absent one."""
    if isinstance(value, str):
        if len(ids) > 1:
            value = value.replace("$RUN2", ids[1])
        return value.replace("$RUN", ids[0])
    if isinstance(value, list):
        return [sub(v, ids) for v in value]
    if isinstance(value, dict):
        return {k: sub(v, ids) for k, v in value.items()}
    return value
