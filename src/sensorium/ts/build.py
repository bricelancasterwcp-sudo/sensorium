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
#: A FLOOR, not the last word: `err_flow` is the one key the BOOT record's
#: own `capabilities` map (`_meta`) rides OVER this constant, because
#: whether RAISE/HANDLED rows carry what the `exceptions` rules need is the
#: runtime's statement to make, not a fact this converter can assert on its
#: own authority. A spool whose BOOT carries no such map declares the
#: constant alone -- `err_flow: false` included.
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
                 path, run_id: str, durable: bool = False) -> None:
        self.spool = spool
        self.inv = invocation
        self.harness = harness
        self.tally = tally or {}
        self.run_id = run_id
        # Non-durable by default because this is the CONVERTER's builder:
        # `convert` writes under a temporary name and renames into place only
        # after `build()` closes the writer, so no reader can be shown a
        # committed row before then and a build that dies leaves a temporary
        # file `convert` unlinks. The argument exists so a caller that wants
        # the recorder's per-batch commits can say so.
        self.w = TraceWriter(path, durable=durable)

        self._frames: dict[int, Frame] = {}
        self._files: dict[int, dict] = {}
        self._codes: dict[tuple[int, int], tuple[int, str, str, int]] = {}
        self._fps: dict[int | None, Fingerprint] = {None: Fingerprint()}
        self.tasks: list[int] = []

        self.source_hashes: dict[str, str] = {}
        self.truncated = 0
        self.tests_seen = 0
        # Whether anything in this spool says the counter RAN. A `node --test`
        # container runs no setup file, so nothing ever calls `seen()` -- and
        # a zero written anyway is a measurement nobody took (R38).
        self.counter_ran = False
        self.outside_frames = 0
        self.rejections: list[dict] = []
        self.file_starts: list[str] = []
        self.environments: set[str] = set()
        self.bases: set[str] = set()
        self.conflicts = 0
        self.events = 0
        self.last_ts: int | None = None
        # The contract's literal rule (TRACE-FORMAT section 4): `incomplete`
        # is written TRUE at the start of a run and false only after the
        # finalize pass. Written here, before a single record is read, so a
        # build that dies half way leaves a trace that CLAIMS to be
        # unfinished rather than one with no claim at all -- an absent key
        # reads as "not incomplete", which is the finalized reading, and the
        # refusal rule would then let it through with every meta key missing.
        self.w.set_meta("incomplete", True)

    # -- the pass -----------------------------------------------------------

    def abort(self) -> None:
        """Let go of a trace that will not be finished.

        `discard()` and not `close()`: the writer's transaction is rolled
        back rather than committed, because a commit here would checkpoint
        the whole trace out of the WAL and into a file the caller is about
        to unlink. A mid-file refusal (a second BOOT, a record the wire does
        not declare) comes through here with rows already written, and that
        is exactly the build whose commit buys nothing.

        The file is the caller's to remove -- it reserved the name -- and a
        second failure while unwinding would replace the exception that
        actually says what went wrong, so this one is not allowed to
        propagate.
        """
        try:
            self.w.discard()
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
        self.counter_ran = True
        self.file_starts.append(relative(rec["path"], self.inv.root))
        if rec.get("environment"):
            self.environments.add(rec["environment"])

    def _on_seen(self, rec: dict) -> None:
        self.counter_ran = True
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
        """No row. The record is read in `_meta` instead, under a name that
        says whose observation it is (R21).

        It does NOT become `exit_status`: what `process.on('exit')` reports
        is the code chosen so far, not the status the process was reaped
        with, and a container that borrowed a number it did not witness is
        the Rust D4 failure wearing a different hat. But it is a fact the
        container observed about ITSELF, and dropping a witnessed fact is
        the other failure -- so it is kept, named `exit_self_reported`, and
        `exit_status` stays null with basis `unwitnessed`.
        """

    # -- frames -------------------------------------------------------------

    def _on_call(self, rec: dict) -> None:
        code_id, rel, qualname, line, kind = self._code(rec)
        if "a" in rec:
            # A focused site read its own arguments, so the trace HOLDS
            # them and the unread marker would be a lie about a read that
            # happened. An `a` that is an empty map is still a read --
            # `catchBinding()` takes nothing, and "read, found none" is a
            # different fact from "nobody looked" (the marker's whole job).
            payload = {"args": rec["a"]}
            for v in rec["a"].values():
                self._trunc(v)
        else:
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

    def _on_line(self, rec: dict) -> None:
        """One completed statement of a focused function.

        `d` is what the statement wrote and `u` the names the transform
        knows are out of scope at it. `u` is written by the runtime only
        when there IS such a name, and it is copied on the same terms: an
        empty `unbound` beside empty deltas would read as "nothing went out
        of scope here", which is a claim nobody made. Empty deltas WITH an
        `unbound` list is a real row -- a loop head on the pass that ends
        the loop -- and is never dropped for looking empty.

        A LINE naming a frame that has closed is refused. The runtime's own
        `line()` drops such a row before it is written (`rt.mjs`: "a frame
        that has closed reports no statement"), so a spool carrying one was
        edited or is corrupt, and attaching it to the closed frame anyway
        would put a statement after that frame's RETURN.
        """
        frame = self._frame(rec, rec["f"])
        if frame.closed:
            raise ConversionError(
                f"{self.spool.path}: a LINE names frame {rec['f']}, which "
                "had already closed")
        payload = {"deltas": rec["d"]}
        if rec.get("u"):
            payload["unbound"] = list(rec["u"])
        for v in rec["d"].values():
            self._trunc(v)
        self.w.add_event(rec["ts"], THREAD, "LINE", frame.db_id,
                         frame.code_id, rec["l"], payload, self._task(rec))
        # No fingerprint update: a LINE is not causal, and a fingerprint
        # that moved with capture depth could not compare a focused run
        # with an unfocused one (spec section 4).
        self.events += 1

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
            "capabilities": {**CAPABILITIES,
                             **(self.spool.boot.get("capabilities") or {})},
            "caps": dict(CAPS),
            "incomplete": self.spool.exit is None,
        }
        if self.spool.exit is not None:
            # Present only where the container lived long enough to say it.
            # An absent key is a container that never got to observe its own
            # ending, which is not the same fact as one that ended at 0.
            meta["exit_self_reported"] = {
                "code": self.spool.exit.get("code"),
                "signal": self.spool.exit.get("signal"),
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
            "task_name_conflicts": self.conflicts,
            "unhandled_rejections": self.rejections,
            "throw_flow_outside_frames": self.outside_frames,
        }
        if self.counter_ran or self.inv.harness == "vitest":
            # Written only where somebody counted (R38). The setup file is
            # vitest's, and its FILE_START or SEEN records are the evidence
            # that it ran; a vitest invocation whose file registered no test
            # at all still counted, and its zero is a measurement. Under
            # `node --test` there is no setup file and no counter, and the
            # key is ABSENT -- "nobody counted" and "counted none" are
            # different facts, and only one of them can be subtracted from
            # the task count.
            meta["tests_seen"] = self.tests_seen
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
        # Plan P9. Every `rel` in this trace -- the fingerprint's paths, the
        # test file, a `focus_matched` entry -- was made relative to this
        # directory, and a reader on another box cannot re-anchor any of
        # them without it. Unconditional: the driver always knew it.
        meta["root"] = self.inv.root
        if self.inv.focus:
            # Both, because they answer different questions. `focus` is what
            # was TYPED, which is what its author recognises; `focus_matched`
            # is what it selected, which is what says whether the spelling
            # meant what they thought. Written only when there was a focus:
            # an empty list is a run that focused nothing, and no key at all
            # is a run nobody focused -- `info` prints the two differently,
            # and every unfocused TypeScript run is the second.
            meta["focus"] = list(self.inv.focus)
            meta["focus_matched"] = list(self.inv.focus_matched)
        if self.inv.command:
            # The command as typed, which is the only one the reader may
            # print (R26). Omitted when the spool's record predates the
            # field, and the readers then fall back to what they said
            # before -- an absent key is a record that was never written,
            # not a run that was started by nothing.
            meta["harness_command"] = list(self.inv.command)
        if self.inv.vitest is not None:
            meta["vitest"] = self.inv.vitest
        if self.harness is not None:
            meta["harness_exit"] = self.harness.meta()
        if "files_transformed" in self.tally:
            meta["files_transformed"] = self.tally["files_transformed"]
            meta["transform_excluded"] = self.tally.get("excluded", {})
        if "functions_focused" in self.tally:
            # R22, and the same rule as its neighbour: written only where
            # somebody counted. A tally written by a transform that predates
            # the key carries no zero, and a zero invented here would say
            # the focus selected nothing -- which is a run the driver would
            # have refused before spawning anything.
            meta["functions_focused"] = self.tally["functions_focused"]
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
