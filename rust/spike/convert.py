#!/usr/bin/env python3
"""THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike, Task 4). Converts
`sensorium-rt` spool directories to format-4 sensorium traces.

This is a stand-in for the real Rust recorder rung 2 will build: it exists
so a real trace can be produced and read by the real `sensorium` CLI before
that recorder is written. It is never imported by `sensorium` itself and is
not referenced from `pyproject.toml` -- see `rust/spike/README.md`.

Wire format (verbatim from Task 1, `sensorium-rt/src/spool.rs`):

    file header:  b"SNSR" u8 version=1  u32 thread_serial  u16 name_len  name_bytes
    record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 reserved=0
    kind:         1 = CALL, 2 = RETURN, 255 = THREAD_END
    outcome:      0 = none, 3 = panic   (1 = ok and 2 = err are reserved for rung 2)
    site:         unit_id in bits 31..24, site index in bits 23..0
    proc header:  {"pid":int,"ppid":int,"exe":str,"argv":[str],"cwd":str,
                   "start_ns":int,"units":{"<unit_id>":"<metadata>"}}

Everything is little-endian. `seq` is a single process-wide counter (one
`AtomicU64`, shared by every thread in the process), so merging every
thread's records by `seq` recovers the process's whole causal order -- the
k-way merge below is exactly that.

CLI:

    python convert.py <spool-dir> --target <target-dir> \\
        [--cargo-exit N] [--argv CARGO ARGS...]

`<spool-dir>` holds one `<pid>.proc.json` and zero or more
`<pid>.<serial>.spool` files per process (a `cargo sensorium test` run's
`target/sensorium/spool/<invocation>/`). `--target` is the same
`CARGO_TARGET_DIR` the driver built into; `<target>/sensorium/manifests/`
holds the manifests Task 3 wrote. One trace is produced per pid, one line
printed per trace:

    run: <id>  pid: <pid>  exe: <basename>  events: <n>  threads: <k>  spools_without_end: <m>

MAPPING DECISIONS worth a comment where the brief left room:

* `--target`'s PARENT directory is the workspace root (Controller ruling):
  manifest file paths are workspace-relative, so `code_objects.file` is
  `parent(target) / <manifest path>`, absolute.
* Every non-main thread (serial != 1) that emits at least one CALL becomes
  exactly one `tasks` row, id = its own thread serial -- libtest already
  gives each `#[test]` its own thread, so "thread" and "unit of work" are
  the same fact here, and reusing the serial as the task id needs no
  separate counter. The main thread's causal events (task_id NULL) get the
  `fingerprints` row; every task gets `task_fingerprints`.
* `--argv` (repeatable, taken from wherever it appears on the command line
  onward) becomes meta `cargo_args` -- the Rust-only key documented in
  TRACE-FORMAT.md -- not the REQUIRED_META `argv`, which is this PROCESS's
  own argv from its proc header. The two are different facts: `cargo_args`
  is what was typed after `cargo sensorium`; `argv` is what this recorded
  process itself saw as `env::args()`.
* `env_hash` is computed from the CONVERTER's own environment at
  conversion time, standing in for "the driver's environment" -- the wire
  format does not carry env at all (a rung-2 gap, same family as
  `exit_status`). `toolchain` runs `rustc --version` at conversion time for
  the same reason.
* `instrumented_units` is scoped to the PROCESS (the metadata hashes its
  own proc header registered -- a unit only appears there once something on
  this process actually called into it). `uninstrumented` and `skipped` are
  scoped to the WHOLE manifest set under `--target`, because a crate that
  `fell_back` never calls `Unit::new()` and so never appears in ANY
  process's `units` map -- the only way to see it is to scan the manifests
  directly, and once that scan runs it may as well answer for the whole
  invocation rather than be repeated per pid.
"""
import argparse
import hashlib
import heapq
import itertools
import json
import os
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from sensorium import paths
from sensorium.record.fingerprint import Fingerprint
from sensorium.store.writer import TraceWriter

# --------------------------------------------------------------------------
# Wire format
# --------------------------------------------------------------------------

MAGIC = b"SNSR"
VERSION = 1

KIND_CALL = 1
KIND_RETURN = 2
KIND_THREAD_END = 255

OUTCOME_NONE = 0
OUTCOME_PANIC = 3

RECORD_LEN = 24
_RECORD_STRUCT = struct.Struct("<QQIBBH")
_HEADER_FIXED_LEN = 4 + 1 + 4 + 2   # magic + version + serial + name_len

SITE_INDEX_MASK = 0x00FF_FFFF
UNIT_ID_SHIFT = 24

# The declaration this converter's recorder makes -- spec §5.1 §5.2 verbatim
# from the task brief. `tasks` and `threads` are true; everything this tier
# cannot produce is declared false, never omitted.
CAPABILITIES = {"line": False, "locals": False, "return_value": False,
                "tasks": True, "threads": True, "children": False,
                "stdin": False, "output": False, "object_identity": False,
                "refocus": False}

RECORDER = "sensorium-rt 0.0.0-spike"
LANG = "rust"
MAIN_SERIAL = 1


class ConverterError(Exception):
    """A spool, proc header, or manifest this converter cannot read
    honestly. Never caught and papered over -- a converter that guessed
    would put a wrong trace in front of a reader who trusts it."""


@dataclass(frozen=True, slots=True)
class Record:
    seq: int
    ts_ns: int
    site: int
    kind: int
    outcome: int


@dataclass(frozen=True)
class SpoolFile:
    path: Path | None
    serial: int
    name: str            # "" when the thread had no name of its own
    records: list         # list[Record], in on-disk (ascending seq) order
    ended: bool           # True iff the last record is THREAD_END


def parse_spool(path: Path) -> SpoolFile:
    """Parse one `<pid>.<serial>.spool` file in full."""
    data = path.read_bytes()
    return parse_spool_bytes(data, source=str(path))


def parse_spool_bytes(data: bytes, source: str = "<bytes>") -> SpoolFile:
    """The parser proper, over raw bytes -- split from `parse_spool` so a
    unit test can hand it a hand-built buffer with no file on disk."""
    if len(data) < _HEADER_FIXED_LEN:
        raise ConverterError(f"{source}: too short to hold a spool header "
                             f"({len(data)} byte(s))")
    if data[:4] != MAGIC:
        raise ConverterError(f"{source}: bad magic {data[:4]!r}, expected "
                             f"{MAGIC!r}")
    version = data[4]
    if version != VERSION:
        raise ConverterError(f"{source}: wire version {version}, this "
                             f"converter reads version {VERSION}")
    serial = struct.unpack_from("<I", data, 5)[0]
    name_len = struct.unpack_from("<H", data, 9)[0]
    end_of_name = _HEADER_FIXED_LEN + name_len
    if end_of_name > len(data):
        raise ConverterError(f"{source}: header claims a {name_len}-byte "
                             "name past the end of the file")
    try:
        name = data[_HEADER_FIXED_LEN:end_of_name].decode("utf-8")
    except UnicodeDecodeError as e:
        raise ConverterError(f"{source}: thread name is not valid UTF-8: "
                             f"{e}") from e
    off = end_of_name
    records = []
    while off + RECORD_LEN <= len(data):
        seq, ts_ns, site, kind, outcome, reserved = _RECORD_STRUCT.unpack_from(
            data, off)
        if reserved != 0:
            raise ConverterError(f"{source}: record at offset {off} has a "
                                 f"non-zero reserved field ({reserved}); "
                                 "this converter reads wire version 1, "
                                 "which never sets it")
        records.append(Record(seq, ts_ns, site, kind, outcome))
        off += RECORD_LEN
    if off != len(data):
        raise ConverterError(f"{source}: {len(data) - off} trailing byte(s) "
                             "after the last complete 24-byte record")
    ended = bool(records) and records[-1].kind == KIND_THREAD_END
    return SpoolFile(None, serial, name, records, ended)


def load_proc_header(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        header = json.load(f)
    for key in ("pid", "ppid", "exe", "argv", "cwd", "start_ns", "units"):
        if key not in header:
            raise ConverterError(f"{path}: proc header missing {key!r}")
    return header


# --------------------------------------------------------------------------
# Manifests (Task 3's output; see sensorium-transform/src/manifest.rs)
# --------------------------------------------------------------------------

@dataclass
class ManifestInfo:
    unit: str
    crate_name: str
    crate_type: str
    fell_back: bool
    # site index -> (workspace-relative file, qualname, firstlineno)
    sites: dict = field(default_factory=dict)
    skipped: list = field(default_factory=list)


def load_manifests(target: Path) -> dict:
    """Every manifest under `<target>/sensorium/manifests/*.json`, keyed by
    unit metadata (the `-C metadata` hash). A manifest naming a MIRROR path
    is a converter error (Controller ruling): a mirror path must never reach
    a trace.

    A missing manifests directory is a converter error too, not a silently
    empty result: it almost always means `--target` does not match the
    `CARGO_TARGET_DIR` the driver actually built into, and letting `{}`
    through here used to surface as a confusing "unit ... has no manifest"
    error much later, per-CALL, instead of naming the real problem once. An
    EXISTING-but-empty directory (a build that instrumented nothing) is a
    different, legitimate fact and is not an error."""
    mdir = target / "sensorium" / "manifests"
    if not mdir.is_dir():
        raise ConverterError(
            f"no manifests found under {mdir} -- check --target: it should "
            "be the exact CARGO_TARGET_DIR the driver built into")
    out: dict = {}
    for p in sorted(mdir.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        sites: dict = {}
        for rel_file, entries in m.get("files", {}).items():
            if "sensorium/mirror" in rel_file:
                raise ConverterError(
                    f"{p}: manifest names a MIRROR path {rel_file!r} -- "
                    "code_objects.file must be a workspace path, never a "
                    "mirror path")
            for e in entries:
                sites[e["site"]] = (rel_file, e["qualname"], e["firstlineno"])
        out[m["unit"]] = ManifestInfo(
            unit=m["unit"], crate_name=m["crate_name"],
            crate_type=m["crate_type"], fell_back=bool(m.get("fell_back")),
            sites=sites, skipped=list(m.get("skipped", [])))
    return out


def uninstrumented_units(manifests: dict) -> list:
    """Units that `fell_back` to compiling the real (unmirrored) tree: they
    never call `Unit::new()`, so no process's proc header can ever name
    them -- the only way to see them is this scan."""
    return sorted(u for u, m in manifests.items() if m.fell_back)


def all_skipped(manifests: dict) -> list:
    out = []
    for u in sorted(manifests):
        out.extend(manifests[u].skipped)
    return out


# --------------------------------------------------------------------------
# The k-way merge
# --------------------------------------------------------------------------

def merge_records(spools: list) -> list:
    """Every record across every spool in `spools`, in strictly increasing
    `seq` order, as `(thread_serial, Record)` pairs.

    `seq` is one `AtomicU64` shared by the whole process, so this recovers
    the process's actual causal order across threads. Two records sharing a
    seq, or seq going backwards, means that invariant was violated -- a
    converter error, not a warning, because silently accepting it would
    hand a reader an order the recorder never produced.

    The heap tuples carry a monotonic tie-breaker (`itertools.count`) ahead
    of the payload so Python is never asked to compare two `Record` objects
    (they carry no `__lt__`) or two file iterators when a `seq` collides --
    exactly the case the strictly-increasing check below exists to catch.
    """
    heap: list = []
    tie = itertools.count()
    for s in spools:
        it = iter(s.records)
        first = next(it, None)
        if first is not None:
            heapq.heappush(heap, (first.seq, next(tie), s.serial, first, it))
    out = []
    last_seq = -1
    while heap:
        seq, _tie, serial, rec, it = heapq.heappop(heap)
        if seq <= last_seq:
            raise ConverterError(
                f"thread {serial}: seq {seq} is not strictly greater than "
                f"the previously merged seq {last_seq} -- the wire format's "
                "process-wide sequence counter was violated")
        last_seq = seq
        out.append((serial, rec))
        nxt = next(it, None)
        if nxt is not None:
            heapq.heappush(heap, (nxt.seq, next(tie), serial, nxt, it))
    return out


# --------------------------------------------------------------------------
# Frame reconstruction: one process's spools -> events, frames, tasks,
# fingerprints in `writer`.
# --------------------------------------------------------------------------

@dataclass
class _StackEntry:
    frame_id: int
    code_id: int
    file: str
    qualname: str


def convert_process(writer: TraceWriter, proc: dict, spools: list,
                    manifests: dict, workspace_root: Path) -> dict:
    """Write one process's events/frames/tasks/fingerprints into `writer`.

    Returns `{"events", "threads_started", "threads", "live_threads",
    "spools_without_end"}` for the CLI's one-line report.
    """
    units = proc.get("units", {})
    stacks: dict = {}                       # serial -> [_StackEntry]
    fp_main = Fingerprint()
    fp_task: dict = {}                      # serial -> Fingerprint
    registered_tasks: set = set()
    thread_names = {s.serial: s.name for s in spools}

    for serial, rec in merge_records(spools):
        if rec.kind == KIND_THREAD_END:
            continue
        if rec.kind not in (KIND_CALL, KIND_RETURN):
            raise ConverterError(
                f"thread {serial}: unknown record kind {rec.kind} at "
                f"seq {rec.seq}")
        if rec.outcome not in (OUTCOME_NONE, OUTCOME_PANIC):
            raise ConverterError(
                f"thread {serial}: unknown outcome {rec.outcome} at "
                f"seq {rec.seq} (1=ok and 2=err are reserved for rung 2; "
                "this converter has never seen either produced)")
        is_main = serial == MAIN_SERIAL
        task_id = None if is_main else serial
        fp = fp_main if is_main else fp_task.setdefault(serial, Fingerprint())

        if rec.kind == KIND_CALL:
            unit_id = rec.site >> UNIT_ID_SHIFT
            site_index = rec.site & SITE_INDEX_MASK
            metadata = units.get(str(unit_id))
            if metadata is None:
                raise ConverterError(
                    f"thread {serial}: CALL at seq {rec.seq} names unit "
                    f"{unit_id}, which this process's proc header never "
                    "registered")
            manifest = manifests.get(metadata)
            if manifest is None:
                raise ConverterError(
                    f"thread {serial}: unit {unit_id} ({metadata}) has no "
                    f"manifest under sensorium/manifests/{metadata}.json")
            site = manifest.sites.get(site_index)
            if site is None:
                raise ConverterError(
                    f"thread {serial}: unit {unit_id} ({metadata}) has no "
                    f"site {site_index} in its manifest")
            rel_file, qualname, firstlineno = site
            abs_file = str(workspace_root / rel_file)
            code_id = writer.intern_code(abs_file, qualname, firstlineno)

            if not is_main and serial not in registered_tasks:
                writer.add_task(serial, thread_names.get(serial) or None,
                                serial)
                registered_tasks.add(serial)

            # `locals: false` (this recorder never reads a frame's
            # arguments): `args: {}` alone would read as "this fn takes no
            # arguments", the opposite of the truth for e.g. `work(n: u32)`.
            # TRACE-FORMAT.md §5's escape hatch -- `unread: ["locals"]`,
            # exactly what the Python recorder writes when it cannot read a
            # frame's locals (record/tracer.py) -- says "unread", not "none".
            eid = writer.add_event(
                rec.ts_ns, serial, "CALL", None, code_id, firstlineno,
                {"args": {}, "unread": ["locals"]}, task_id)
            stack = stacks.setdefault(serial, [])
            parent_id = stack[-1].frame_id if stack else None
            depth = len(stack)
            fid = writer.open_frame(parent_id, code_id, eid, depth, serial,
                                    "function")
            stack.append(_StackEntry(fid, code_id, abs_file, qualname))
            fp.update(abs_file, qualname, "CALL")
            continue

        # RETURN
        stack = stacks.get(serial) or []
        if not stack:
            raise ConverterError(
                f"thread {serial}: RETURN at seq {rec.seq} with no open "
                "frame on this thread")
        top = stack.pop()
        closed_by = "return"
        unwind_exc = None
        if rec.outcome == OUTCOME_PANIC:
            closed_by = "unwind"
            unwind_exc = {"type": "panic", "msg": "", "serial": rec.seq,
                          "oid": rec.seq}
        eid = writer.add_event(rec.ts_ns, serial, "RETURN", top.frame_id,
                               top.code_id, None, {}, task_id)
        writer.close_frame(top.frame_id, eid, closed_by, unwind_exc)
        fp.update(top.file, top.qualname, "RETURN")

    threads_started = sum(1 for s in spools if s.serial != MAIN_SERIAL)
    live_threads = [s.name for s in spools if not s.ended]

    writer.write_fingerprint(MAIN_SERIAL, fp_main.hexdigest(), fp_main.count)
    writer.write_task_fingerprints(
        [(serial, fp_task[serial].hexdigest(), fp_task[serial].count)
         for serial in sorted(fp_task)])

    return {
        "events": writer.last_event_id,
        "threads_started": threads_started,
        "threads": threads_started + 1,
        "live_threads": live_threads,
        "spools_without_end": len(live_threads),
    }


# --------------------------------------------------------------------------
# Per-invocation context: env, toolchain, profile
# --------------------------------------------------------------------------

def build_env_hash(env: dict | None = None) -> str:
    """A short digest of the converter's own environment, standing in for
    "the driver's environment" -- the wire format carries no env at all."""
    items = sorted((env if env is not None else os.environ).items())
    blob = "\n".join(f"{k}={v}" for k, v in items)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def detect_toolchain() -> str:
    try:
        out = subprocess.run(["rustc", "--version"], capture_output=True,
                             text=True, timeout=10, check=True)
        return out.stdout.strip()
    except Exception as e:                          # noqa: BLE001 -- best effort
        return f"unknown (rustc --version failed at conversion time: {e})"


# --------------------------------------------------------------------------
# One converter invocation: a whole spool dir -> one trace per pid
# --------------------------------------------------------------------------

def orphan_spools(spool_dir: Path, proc_paths: list) -> list:
    """`<pid>.<serial>.spool` files under `spool_dir` whose pid names no
    file in `proc_paths` -- a process this converter has no header for, and
    so no `argv`/`cwd`/`units` map to build a trace from. `*.proc.json` is
    written before any spool file for that pid can exist (`ensure_dir`
    creates it inside the same `DIR_READY.call_once` that gates the first
    `emit`), so an orphan means the header was lost or never written, not
    ordinary races -- worth raising loudly, not silently dropping, with
    ~70 processes converted per bloomery invocation."""
    known_pids = {p.name.removesuffix(".proc.json") for p in proc_paths}
    return sorted(p for p in spool_dir.glob("*.spool")
                 if p.name.split(".", 1)[0] not in known_pids)


def convert_dir(spool_dir: Path, target: Path, cargo_exit: int = 0,
                cargo_args: list | None = None) -> list:
    """Convert every process under `spool_dir` into its own trace file
    under `$SENSORIUM_DIR/traces/`. Returns the printed report lines, in
    the order the traces were written (pid file discovery order, sorted)."""
    spool_dir = Path(spool_dir)
    target = Path(target)
    cargo_args = list(cargo_args or [])

    manifests = load_manifests(target)
    workspace_root = target.resolve().parent
    invocation = spool_dir.name
    uninstrumented = uninstrumented_units(manifests)
    skipped = all_skipped(manifests)
    env_hash = build_env_hash()
    toolchain = detect_toolchain()
    profile = "release" if "--release" in cargo_args else "debug"
    conversion_ts = time.time()

    proc_paths = sorted(spool_dir.glob("*.proc.json"))
    orphans = orphan_spools(spool_dir, proc_paths)
    if orphans:
        raise ConverterError(
            "spool file(s) with no matching <pid>.proc.json (an orphan "
            "means a process's header was never written, or was lost -- "
            "converting the rest and silently dropping these would hide "
            "that): " + ", ".join(p.name for p in orphans))

    lines = []
    for proc_path in proc_paths:
        proc = load_proc_header(proc_path)
        pid = proc["pid"]
        spools = [parse_spool(p)
                 for p in sorted(spool_dir.glob(f"{pid}.*.spool"))]

        run_id = paths.new_run_id()
        trace_path = paths.traces_dir() / f"{run_id}.db"
        writer = TraceWriter(trace_path)
        try:
            summary = _write_one_trace(
                writer, proc, spools, manifests, workspace_root,
                run_id=run_id, invocation=invocation, cargo_exit=cargo_exit,
                env_hash=env_hash, toolchain=toolchain,
                cargo_args=cargo_args, profile=profile,
                uninstrumented=uninstrumented, skipped=skipped,
                conversion_ts=conversion_ts)
        except Exception:
            writer.close()
            trace_path.unlink(missing_ok=True)
            raise
        writer.close()

        exe_base = Path(proc.get("exe", "")).name
        lines.append(
            f"run: {run_id}  pid: {pid}  exe: {exe_base}  "
            f"events: {summary['events']}  threads: {summary['threads']}  "
            f"spools_without_end: {summary['spools_without_end']}")
    return lines


def _write_one_trace(writer, proc, spools, manifests, workspace_root, *,
                     run_id, invocation, cargo_exit, env_hash, toolchain,
                     cargo_args, profile, uninstrumented, skipped,
                     conversion_ts) -> dict:
    """The meta pass around one process's `convert_process` call. Every
    `db.REQUIRED_META` key is written, plus the `threads` witness keys
    (`capabilities.threads` is true), plus the Rust-only keys the trace
    format document lists for this recorder. `incomplete` is written LAST,
    the finalize marker, as the Python recorder's own `set_meta_final`
    convention does."""
    summary = convert_process(writer, proc, spools, manifests, workspace_root)

    # CONVERTER-TIME APPROXIMATIONS, not recorded facts: the wire format
    # carries no wall-clock timestamp at all (`ts_ns` is CLOCK_MONOTONIC,
    # with no fixed epoch this converter can anchor). `end_ts` is pinned to
    # THIS CONVERSION's own wall-clock time (shared by every trace one
    # `convert_dir()` call produces) and `start_ts` is backdated by the
    # process's own recorded span, so `info`'s "duration: N.NNs" is that
    # span, not a measurement of when the process actually ran. Same rung-2
    # gap family as `exit_status` (§ the task report's meta section).
    elapsed_s = 0.0
    all_ts = [r.ts_ns for s in spools for r in s.records]
    if all_ts:
        elapsed_s = (max(all_ts) - min(all_ts)) / 1e9
    end_ts = conversion_ts
    start_ts = end_ts - elapsed_s

    writer.set_meta("run_id", run_id)
    writer.set_meta("argv", proc.get("argv", []))
    writer.set_meta("cwd", proc.get("cwd", ""))
    writer.set_meta("env_hash", env_hash)
    writer.set_meta("start_ts", start_ts)
    writer.set_meta("end_ts", end_ts)
    writer.set_meta("exit_status", cargo_exit)
    writer.set_meta("main_thread_ident", MAIN_SERIAL)
    writer.set_meta("fingerprint_basis", "per-task")
    writer.set_meta("truncated_count", 0)
    writer.set_meta("records_dropped", {})
    writer.set_meta("source_hashes", {})
    writer.set_meta("recorder", RECORDER)
    writer.set_meta("lang", LANG)
    writer.set_meta("capabilities", CAPABILITIES)
    writer.set_meta("threads_started", summary["threads_started"])
    writer.set_meta("live_threads", summary["live_threads"])
    writer.set_meta("invocation", invocation)
    writer.set_meta("pid", proc["pid"])
    writer.set_meta("ppid", proc.get("ppid"))
    writer.set_meta("exe", proc.get("exe", ""))
    writer.set_meta("toolchain", toolchain)
    writer.set_meta("cargo_args", cargo_args)
    writer.set_meta("profile", profile)
    writer.set_meta("instrumented_units",
                    sorted(set(proc.get("units", {}).values())))
    writer.set_meta("uninstrumented", uninstrumented)
    writer.set_meta("skipped", skipped)
    writer.set_meta("incomplete", False)
    return summary


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="convert.py",
        description="Convert a sensorium-rt spool directory to format-4 "
                    "sensorium traces (THROWAWAY SPIKE CODE).")
    p.add_argument("spool_dir", type=Path,
                   help="the invocation's spool directory "
                        "(target/sensorium/spool/<invocation>/)")
    p.add_argument("--target", type=Path, required=True,
                   help="the CARGO_TARGET_DIR the driver built into; its "
                        "PARENT is taken as the workspace root")
    p.add_argument("--cargo-exit", type=int, default=0,
                   help="the cargo test exit status, recorded as "
                        "exit_status for every process of this invocation")
    p.add_argument("--argv", nargs=argparse.REMAINDER, default=[],
                   help="the cargo args this invocation ran, recorded as "
                        "meta.cargo_args -- MUST be the last flag: it "
                        "consumes every token after it, dashes included")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        lines = convert_dir(args.spool_dir, args.target, args.cargo_exit,
                            args.argv)
    except ConverterError as e:
        print(f"convert.py: {e}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
