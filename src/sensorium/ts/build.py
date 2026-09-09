"""One spool, one format-4 trace.

Every row this module writes goes through `store.writer.TraceWriter`, the
same writer the Python recorder uses, so the schema has exactly one home
and a column added there is a column both recorders get. What is local to
this file is the MAPPING: which wire record becomes which event, which
frame, which meta key, and -- as often -- which record becomes nothing at
all and is counted instead.

Three of those "counted instead" rules are the reason this file is worth
reading:

* an `UNHANDLED` record becomes a `meta.unhandled_rejections` entry and
  never an event, because a causal event with no `code_id` is refused by
  the contract and a synthetic code object would put a site in the program
  that has none (design D7);
* a `RAISE`/`HANDLED` whose `f` is null becomes a tick of
  `meta.throw_flow_outside_frames` and no event, because there is no frame
  to attach it to and inventing one would be a claim about where the throw
  happened;
* an `UNWIND` closes its frame and writes no event: how a frame ended is
  evidence the reader derives (`closed_by`, `unwind_exc`), not a row.

Loss is never counted. A container killed by SIGKILL did not get to count
what it was about to write, so the trace carries `incomplete: true` and no
`records_dropped` (typescript/HONESTY.md section 5).
"""
import time
from dataclasses import dataclass

from sensorium.record.fingerprint import Fingerprint
from sensorium.store.writer import TraceWriter
from sensorium.ts.spool import Spool, SpoolError

#: What this recorder produces, and what it does not (design section 5.2).
#: `err_flow` is false although RAISE/HANDLED rows exist: the key is the
#: runtime's statement that its records carry what the `exceptions` rules
#: need, and no TypeScript rules exist yet.
CAPABILITIES = {
    "line": False, "locals": False, "return_value": True, "tasks": True,
    "threads": False, "children": False, "stdin": False, "output": False,
    "object_identity": False, "refocus": False, "err_flow": False,
}

#: The capture caps in force in the runtime (`typescript/src/dbg.mjs`).
CAPS = {"dbg": 200, "depth": 2, "sample": 8, "str": 100}

LANG = "typescript"
#: Every container is one thread as far as a trace is concerned: a worker
#: thread and a forked child are each their own container with their own
#: spool, so no trace ever holds two.
THREAD = 1

#: What a suspension parked ON, per wire kind. `await` parks on a promise;
#: `yield` parks on whoever is pulling the generator. Neither is a type the
#: recorder read off a value -- they are what the KEYWORD means.
AWAITING = {"await": "Promise", "yield": "consumer"}


class ConversionError(SpoolError):
    """A record cannot be turned into a row. A subclass of `SpoolError`
    because both are the same thing to a caller -- this spool did not
    convert, here is why, the rest of the invocation still will."""


@dataclass
class Frame:
    db_id: int
    code_id: int
    depth: int
    rel: str
    qualname: str
    closed: bool = False


class Builder:
    """Reads one `Spool`, writes one trace. Single-threaded and single-use.

    Held together by three tables: `_frames` maps a wire frame id to the row
    it opened (closed frames included -- a throw-flow record may name one),
    `_files` maps a wire file id to its FILE header, and `_fps` holds one
    `Fingerprint` per task plus the thread's own.
    """

    def __init__(self, spool: Spool, invocation, harness, tally: dict | None,
                 path, run_id: str) -> None:
        self.spool = spool
        self.inv = invocation
        self.harness = harness
        self.tally = tally or {}
        self.run_id = run_id
        self.w = TraceWriter(path)

        self._frames: dict[int, Frame] = {}
        self._files: dict[int, dict] = {}
        self._codes: dict[tuple[int, int], tuple[int, str, str, int]] = {}
        self._fps: dict[int | None, Fingerprint] = {None: Fingerprint()}
        self.tasks: list[int] = []

        self.source_hashes: dict[str, str] = {}
        self.truncated = 0
        self.tests_seen = 0
        self.outside_frames = 0
        self.rejections: list[dict] = []
        self.file_starts: list[str] = []
        self.environments: set[str] = set()
        self.bases: set[str] = set()
        self.conflicts = 0
        self.events = 0
        self.last_ts: int | None = None

    # -- the pass -----------------------------------------------------------

    def abort(self) -> None:
        """Let go of a trace that will not be finished.

        The file is the caller's to remove -- it reserved the name -- and a
        second failure while unwinding would replace the exception that
        actually says what went wrong, so this one is not allowed to
        propagate.
        """
        try:
            self.w.close()
        except Exception:                                   # pragma: no cover
            pass

    def build(self) -> dict:
        """Convert, finalize, close. Returns the meta that was written."""
        for rec in self.spool.records:
            self._one(rec)
        self._fingerprints()
        meta = self._meta()
        for key, value in meta.items():
            self.w.set_meta(key, value)
        self.w.close()
        return meta

    def _one(self, rec: dict) -> None:
        handler = getattr(self, "_on_" + rec["e"].lower(), None)
        if handler is None:
            raise ConversionError(
                f"{self.spool.path}: no rule for a {rec['e']} record -- this "
                f"spool is wire {self.spool.boot.get('wire')}, which this "
                "sensorium does not fully read")
        if "ts" in rec:
            self.last_ts = rec["ts"]
        try:
            handler(rec)
        except ConversionError:
            raise
        except (KeyError, TypeError, IndexError) as e:
            # A record missing a key this wire version declares is a spool
            # this converter cannot read, not a crash: named, refused, and
            # the spools beside it convert anyway.
            raise ConversionError(
                f"{self.spool.path}: a {rec['e']} record is not the shape "
                f"wire {self.spool.boot.get('wire')} declares "
                f"({type(e).__name__}: {e})") from None

    # -- headers ------------------------------------------------------------

    def _on_file(self, rec: dict) -> None:
        self._files[rec["id"]] = rec
        self.source_hashes[rec["abs"]] = rec["sha"]

    def _on_file_start(self, rec: dict) -> None:
        self.file_starts.append(relative(rec["path"], self.inv.root))
        if rec.get("environment"):
            self.environments.add(rec["environment"])

    def _on_seen(self, rec: dict) -> None:
        self.tests_seen += 1
        self.truncated += bool(rec.get("name_trunc"))

    def _on_task(self, rec: dict) -> None:
        self.w.add_task(rec["id"], rec["name"], THREAD)
        self.tasks.append(rec["id"])
        self._fps[rec["id"]] = Fingerprint()
        self.bases.add(rec["basis"])
        self.conflicts += bool(rec.get("conflict"))
        self.truncated += bool(rec.get("name_trunc"))

    def _on_exit(self, rec: dict) -> None:
        """Nothing to write. The EXIT record's own `code` is deliberately
        not carried into `exit_status`: a process cannot witness its own
        ending, and what `process.on('exit')` reports is the code chosen so
        far, not the status the process was reaped with. The status that WAS
        witnessed rides `harness_exit`, where the driver put it."""

    # -- frames -------------------------------------------------------------

    def _on_call(self, rec: dict) -> None:
        code_id, rel, qualname, line, kind = self._code(rec)
        payload = {"args": {}, "unread": ["locals"]}
        parent = None
        depth = 0
        if rec["p"] is None:
            # The truthful answer to "who called this?" when the frame was
            # entered on an empty stack: Node's own machinery did.
            payload["caller"] = "untraced"
        else:
            parent = self._frame(rec, rec["p"])
            depth = parent.depth + 1
        task = self._task(rec)
        eid = self.w.add_event(rec["ts"], THREAD, "CALL", None, code_id, line,
                               payload, task)
        self.events += 1
        self._fps[task].update(rel, qualname, "CALL")
        db_id = self.w.open_frame(parent.db_id if parent else None, code_id,
                                  eid, depth, THREAD, kind)
        self._frames[rec["f"]] = Frame(db_id, code_id, depth, rel, qualname)

    def _on_return(self, rec: dict) -> None:
        frame = self._close(rec)
        task = self._task(rec)
        self._trunc(rec.get("v"))
        eid = self.w.add_event(rec["ts"], THREAD, "RETURN", frame.db_id,
                               frame.code_id, None,
                               {"value": rec["v"], "outcome": "ok"}, task)
        self.events += 1
        self._fps[task].update(frame.rel, frame.qualname, "RETURN")
        self.w.close_frame(frame.db_id, eid, "return")

    def _on_unwind(self, rec: dict) -> None:
        """A frame left by throwing. The evidence is the frame row -- how it
        ended is what the reader derives from `closed_by` and `unwind_exc`
        -- so no event is written and nothing enters the fingerprint."""
        frame = self._close(rec)
        self._trunc(rec.get("x"))
        self.w.close_frame(frame.db_id, None, "unwind", rec["x"])

    def _on_yield(self, rec: dict) -> None:
        frame = self._frame(rec, rec["f"])
        self.w.add_event(rec["ts"], THREAD, "YIELD", frame.db_id,
                         frame.code_id, None,
                         {"awaiting": AWAITING[rec["k"]]}, self._task(rec))
        self.events += 1

    def _on_resume(self, rec: dict) -> None:
        frame = self._frame(rec, rec["f"])
        self.w.add_event(rec["ts"], THREAD, "RESUME", frame.db_id,
                         frame.code_id, None, {}, self._task(rec))
        self.events += 1

    # -- throw flow ---------------------------------------------------------

    def _on_raise(self, rec: dict) -> None:
        self._throw(rec, "RAISE")

    def _on_handled(self, rec: dict) -> None:
        self._throw(rec, "HANDLED")

    def _throw(self, rec: dict, kind: str) -> None:
        self._trunc(rec.get("x"))
        if rec["f"] is None:
            # No frame to attach it to, so no event: the count is the only
            # trace of it, read the way Rust's err_flow_outside_frames is.
            self.outside_frames += 1
            return
        frame = self._frame(rec, rec["f"])
        task = self._task(rec)
        self.w.add_event(rec["ts"], THREAD, kind, frame.db_id, frame.code_id,
                         rec["l"], {"exc": rec["x"], "how": rec["how"]}, task)
        self.events += 1
        self._fps[task].update(frame.rel, frame.qualname, kind)

    def _on_unhandled(self, rec: dict) -> None:
        exc = rec["x"]
        self._trunc(exc)
        self.rejections.append({"type": exc["type"], "msg": exc["msg"],
                                "serial": exc["serial"]})

    # -- lookups ------------------------------------------------------------

    def _code(self, rec: dict) -> tuple[int, str, str, int, str]:
        """`(code_id, rel, qualname, firstlineno, frame kind)` for a CALL.

        Interned against the ABSOLUTE path, which is what `code_objects.file`
        holds; `rel` travels beside it because the fingerprint hashes the
        root-relative path instead (TRACE-FORMAT section 7).
        """
        key = (rec["file"], rec["c"])
        cached = self._codes.get(key)
        header = self._files.get(rec["file"])
        if header is None:
            raise ConversionError(
                f"{self.spool.path}: a CALL names file {rec['file']}, which "
                "no FILE record declared")
        codes = header["codes"]
        if not 0 <= rec["c"] < len(codes):
            raise ConversionError(
                f"{self.spool.path}: a CALL names site {rec['c']} of "
                f"{header['rel']}, which declared {len(codes)}")
        qualname, line, kind = codes[rec["c"]]
        if cached is None:
            cached = (self.w.intern_code(header["abs"], qualname, line),
                      header["rel"], qualname, line)
            self._codes[key] = cached
        return (*cached, kind)

    def _frame(self, rec: dict, wire_id: int) -> Frame:
        frame = self._frames.get(wire_id)
        if frame is None:
            raise ConversionError(
                f"{self.spool.path}: a {rec['e']} names frame {wire_id}, "
                "which no CALL opened")
        return frame

    def _close(self, rec: dict) -> Frame:
        frame = self._frame(rec, rec["f"])
        if frame.closed:
            raise ConversionError(
                f"{self.spool.path}: a {rec['e']} closes frame {rec['f']}, "
                "which had already closed")
        frame.closed = True
        return frame

    def _task(self, rec: dict) -> int | None:
        task = rec["t"]
        if task is not None and task not in self._fps:
            raise ConversionError(
                f"{self.spool.path}: a {rec['e']} names test {task}, which no "
                "TASK record opened")
        return task

    def _trunc(self, obj) -> None:
        if isinstance(obj, dict):
            self.truncated += bool(obj.get("trunc"))
            self.truncated += bool(obj.get("type_trunc"))

    # -- finalize -----------------------------------------------------------

    def _fingerprints(self) -> None:
        """One thread row and one row per test, zero counts included.

        A zero-count thread row is a fact with content -- this container ran
        traced code, all of it inside tests -- and is not the same fact as
        having no row, which every reader takes to mean nothing ran here.
        """
        thread = self._fps[None]
        self.w.write_fingerprint(THREAD, thread.hexdigest(), thread.count)
        self.w.write_task_fingerprints(
            [(tid, self._fps[tid].hexdigest(), self._fps[tid].count)
             for tid in self.tasks])

    def _meta(self) -> dict:
        boot = self.spool.boot
        meta = {
            "run_id": self.run_id,
            "argv": boot["argv"],
            "cwd": boot["cwd"],
            "env": boot["env"],
            "env_hash": boot["envHash"],
            "start_ts": boot["startTs"],
            "end_ts": self._end_ts(),
            "exit_status": None,
            "exit_status_basis": "unwitnessed",
            "main_thread_ident": THREAD,
            "fingerprint_basis": "per-task",
            "truncated_count": self.truncated,
            "source_hashes": self.source_hashes,
            "recorder": self._recorder(),
            "lang": LANG,
            "capabilities": dict(CAPABILITIES),
            "caps": dict(CAPS),
            "incomplete": self.spool.exit is None,
        }
        meta.update(self._container_meta())
        meta.update(self._invocation_meta())
        return meta

    def _container_meta(self) -> dict:
        boot = self.spool.boot
        meta = {
            "pid": boot["pid"],
            "ppid": boot["ppid"],
            "thread_id_os": boot["threadId"],
            "is_main_thread": boot["isMainThread"],
            "node": boot["node"],
            "wire": boot["wire"],
            "tests_seen": self.tests_seen,
            "task_name_conflicts": self.conflicts,
            "unhandled_rejections": self.rejections,
            "throw_flow_outside_frames": self.outside_frames,
        }
        if len(self.file_starts) == 1:
            meta["test_file"] = self.file_starts[0]
        elif self.file_starts:
            meta["test_files"] = self.file_starts
        if len(self.environments) == 1:
            meta["environment"] = next(iter(self.environments))
        if self.bases:
            meta["task_name_basis"] = (self.bases.pop() if len(self.bases) == 1
                                       else "mixed")
        return meta

    def _invocation_meta(self) -> dict:
        meta = {
            "invocation": self.inv.invocation,
            "harness": self.inv.harness,
            "harness_args": self.inv.harness_args,
            "driver_version": self.inv.driver_version,
        }
        if self.inv.vitest is not None:
            meta["vitest"] = self.inv.vitest
        if self.harness is not None:
            meta["harness_exit"] = self.harness.meta()
        if "files_transformed" in self.tally:
            meta["files_transformed"] = self.tally["files_transformed"]
            meta["transform_excluded"] = self.tally.get("excluded", {})
        return meta

    def _end_ts(self) -> float:
        """Wall-clock seconds at the end of the recording.

        With an EXIT record the container read its own clock and said so.
        Without one it was killed, and the last thing it managed to write is
        the last thing that can be dated: the monotonic distance from BOOT
        to that record, added to BOOT's wall clock. That is an estimate of
        when the RECORDING ended, which is all `info` prints it as -- not a
        claim about when the process died.
        """
        if self.spool.exit is not None:
            return self.spool.exit["endTs"]
        boot = self.spool.boot
        if self.last_ts is None:
            return boot["startTs"]
        return boot["startTs"] + (self.last_ts - boot["ts"]) / 1e9

    def _recorder(self) -> str:
        """Who wrote the spool (R5). BOOT names its own writer, and that is
        the authority; the driver's reading of the package version is the
        fallback for a spool old enough not to carry one."""
        version = self.spool.boot.get("version")
        if version:
            return f"sensorium-ts {version}"
        return self.inv.recorder


def relative(path: str, root: str) -> str:
    """`path` under `root`, or `path` unchanged when it is not under it.

    Never `../..`: a file outside the project root is named absolutely,
    because a relative path that climbs out of the root is not something a
    reader on another box can resolve, and pretending otherwise would make
    two different files look like one.
    """
    root = root.rstrip("/")
    if path == root:
        return "."
    prefix = root + "/"
    if path.startswith(prefix):
        return path[len(prefix):]
    return path


def mint_run_id(start_ts: float, token: str) -> str:
    """`YYYYMMDD-HHMMSS-xxxxxx`, stamped with the container's OWN start.

    Not the conversion's clock: every trace of one invocation then sorts
    under the invocation it belongs to, and `runs` groups what actually ran
    together rather than what happened to convert together.
    """
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(start_ts)) + "-" + token
