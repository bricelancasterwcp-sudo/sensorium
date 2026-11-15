"""Spool to trace format 4.

``convert_root`` reads ``$SENSORIUM_C_ROOT`` (the driver's ``side.json``,
per-pid directories, and the root's stdout/stderr) and writes one trace
per instrumented process. DWARF is parsed once per image. Values are
decoded from the types cached on that image.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

try:
    from elftools.common.exceptions import ELFError
except ImportError as e:  # pragma: no cover - the tests skip this case
    raise ImportError(
        "pyelftools is required to read DWARF (pip install pyelftools)"
    ) from e

from sensorium import paths, redact
from sensorium import redact_values as rv
from sensorium.c import LANG, RECORDER
from sensorium.c.decode import VOID, decode_param, decode_return
from sensorium.c.dwarf import DwarfImage, Func
from sensorium.c.format import (
    FLAG_TRUNC, KIND_ASSERT, KIND_ENTER, KIND_EXIT, KIND_FORK, KIND_LONGJMP,
    KIND_RET, KIND_SIGNAL, unpack_args, read_thread,
)
from sensorium.record.boot import git_info, hash_file
from sensorium.record.fingerprint import Fingerprint
from sensorium.redact import Key, Knobs
from sensorium.store.writer import TraceWriter

_CHUNK = 65536
_SIGNAMES = {11: "SIGSEGV", 7: "SIGBUS", 8: "SIGFPE", 4: "SIGILL", 6: "SIGABRT"}
_SEGV = {1: "SEGV_MAPERR", 2: "SEGV_ACCERR"}


def convert_root(root) -> list[str]:
    """Convert every pid directory under ``root``. Returns run ids."""
    root = Path(root)
    side = json.loads((root / "side.json").read_text(encoding="utf-8"))
    ids = []
    kids = []
    try:
        children = list(root.iterdir())
    except OSError:
        return ids
    for child in children:
        if child.is_dir() and child.name.isdigit() and (child / "threads").is_dir():
            kids.append(child)
    kids.sort(key=lambda p: int(p.name))
    for child in kids:
        ids.append(convert_spool(child, side, root))
    return ids


def convert_spool(pid_dir, side=None, root=None) -> str:
    """Convert one process directory. Returns the new run id.

    A failure deletes the partial trace so a reader never sees
    ``incomplete: false`` on a file this pass did not finish.
    """
    pid_dir = Path(pid_dir)
    root = Path(root) if root is not None else pid_dir.parent
    if side is None:
        side = json.loads((root / "side.json").read_text(encoding="utf-8"))
    run_id = paths.new_run_id()
    out = paths.traces_dir() / f"{run_id}.db"
    key = Key.load_or_create(paths.trace_root())
    knobs = Knobs.from_environ(os.environ)
    rv.install(key, knobs)
    before = rv.stats["values"]
    writer = None
    try:
        writer = TraceWriter(out, durable=False)
        _convert(writer, pid_dir, side, root, run_id, key, knobs, before)
        writer.close()
        writer = None
        return run_id
    except Exception:
        if writer is not None:
            try:
                writer.discard()
            except Exception:
                pass
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(str(out) + suffix).unlink()
            except OSError:
                pass
        raise
    finally:
        rv.reset()


def _convert(writer, pid_dir, side, root, run_id, key, knobs, before) -> None:
    pid = int(pid_dir.name)
    cwd = side.get("cwd") or ""
    argv = _json(pid_dir / "argv.json", None)
    if not isinstance(argv, list):
        argv = ["?"]
    exe = _exe_path(side, pid_dir, argv, cwd)
    conv = _Conv(writer, pid_dir, side, root, pid, cwd, exe)
    conv.run()
    conv.finish_meta(run_id, key, knobs, before, argv)


class _Frame:
    __slots__ = ("fid", "cid", "file", "name", "line", "rel", "fn")

    def __init__(self, fid, cid, file, name, line, rel, fn):
        self.fid = fid
        self.cid = cid
        self.file = file
        self.name = name
        self.line = line
        self.rel = rel
        self.fn = fn


class _Conv:
    def __init__(self, writer, pid_dir, side, root, pid, cwd, exe):
        self.w = writer
        self.pid_dir = pid_dir
        self.side = side
        self.root = root
        self.pid = pid
        self.cwd = cwd
        self.exe = exe
        self.objs = _objs(pid_dir / "objs.txt")
        self.images: dict[str, DwarfImage | None] = {}
        self.stacks: dict[int, list] = {}
        self.pending: dict[int, tuple] = {}
        self.asserts: dict[int, str | None] = {}
        self.jmp_serial: dict[int, int] = {}
        self.fps: dict[int, Fingerprint] = {}
        self.framed: set[int] = set()
        self.real_file: set[int] = set()
        self.forks: list[int] = []
        self.trunc = 0

    def run(self) -> None:
        recs = []
        threads = self.pid_dir / "threads"
        try:
            paths_ = sorted(threads.iterdir())
        except OSError:
            paths_ = []
        for path in paths_:
            if not path.is_file():
                continue
            tid, rows = read_thread(path)
            for rec in rows:
                recs.append((rec.seq, tid, rec))
        recs.sort(key=lambda item: (item[0], item[1]))
        for _seq, tid, rec in recs:
            if rec.kind != KIND_RET:
                self._flush(tid, None)
            self._one(tid, rec)
        for tid in list(self.pending):
            self._flush(tid, None)
        for tid, fp in self.fps.items():
            if fp.count == 0 and tid not in self.real_file:
                continue
            if tid not in self.framed and fp.count == 0:
                continue
            self.w.write_fingerprint(tid, fp.hexdigest(), fp.count)
        if self._is_root():
            self._output(self.root / "stdout.bin", "stdout")
            self._output(self.root / "stderr.bin", "stderr")

    def _one(self, tid, rec) -> None:
        kind = rec.kind
        if kind == KIND_ENTER:
            self._enter(tid, rec)
        elif kind == KIND_EXIT:
            self._exit(tid, rec)
        elif kind == KIND_RET:
            self._flush(tid, rec)
        elif kind == KIND_SIGNAL:
            self._signal(tid, rec)
        elif kind == KIND_ASSERT:
            self.asserts[tid] = _assert_msg(rec.extra, rec.a)
        elif kind == KIND_LONGJMP:
            self._longjmp(tid, rec)
        elif kind == KIND_FORK:
            self.forks.append(int(rec.a))

    def _enter(self, tid, rec) -> None:
        self.asserts[tid] = None
        fn = self._fn(rec.a)
        stack = self.stacks.setdefault(tid, [])
        rel = _rel(fn.file, self.cwd)
        cid = self.w.intern_code(fn.file, fn.name, int(fn.line or 0))
        if fn.file and fn.file not in ("<unknown>", "?"):
            self.real_file.add(tid)
        args = self._args(fn, rec.extra)
        payload = {"args": args}
        if stack:
            payload["caller_code"] = stack[-1].cid
        else:
            payload["caller"] = "untraced"
        _count(payload)
        eid = self.w.add_event(
            rec.ts, tid, "CALL", None, cid, int(fn.line or 0), payload)
        parent = stack[-1].fid if stack else None
        fid = self.w.open_frame(parent, cid, eid, len(stack), tid, "function")
        frame = _Frame(fid, cid, fn.file, fn.name, int(fn.line or 0), rel, fn)
        stack.append(frame)
        self._fp(tid, frame, "CALL")

    def _exit(self, tid, rec) -> None:
        stack = self.stacks.get(tid) or []
        if not stack:
            return
        self.pending[tid] = (stack.pop(), rec.ts)

    def _flush(self, tid, value_rec) -> None:
        got = self.pending.pop(tid, None)
        if got is None:
            return
        frame, ts = got
        payload: dict = {}
        if value_rec is not None:
            ts = value_rec.ts
            fn = frame.fn
            value = decode_return(
                fn.ret_type, fn.ret_class, value_rec.a, value_rec.b,
                value_rec.c, value_rec.d, value_rec.extra)
            if value is not None:
                if isinstance(value, dict):
                    value = rv.named_return(frame.name, value)
                payload = {"value": value}
        _count(payload)
        eid = self.w.add_event(
            ts, tid, "RETURN", frame.fid, frame.cid, None, payload)
        self.w.close_frame(frame.fid, eid, "return")
        self._fp(tid, frame, "RETURN")

    def _signal(self, tid, rec) -> None:
        asserted = self.asserts.get(tid)
        self.asserts[tid] = None
        signo = int(rec.a)
        if asserted:
            name = "SIGABRT"
            msg = asserted
        else:
            name, msg = _sig_msg(signo, int(rec.b), int(rec.d))
        exc = rv.exc({
            "kind": "signal", "type": name, "msg": msg, "serial": 1,
            "signal": 6 if asserted else signo,
        })
        loc = self._loc(rec)
        payload = {"exc": exc, "loc": loc}
        unwind = {**exc, "loc": loc}
        _count(payload)
        stack = self.stacks.get(tid) or []
        if stack:
            top = stack[-1]
            line = top.line
            where = self._exe_line(int(rec.c))
            if where and where[0] == top.file:
                line = where[1]
            eid = self.w.add_event(
                rec.ts, tid, "RAISE", top.fid, top.cid, line, payload)
            self._fp(tid, top, "RAISE")
            # The event id is the RAISE. Frames close without a return id.
            _ = eid
        else:
            self._unframed_raise(tid, rec, payload)
        while stack:
            frame = stack.pop()
            self.w.close_frame(frame.fid, None, "unwind", unwind)

    def _unframed_raise(self, tid, rec, payload) -> None:
        fn = self._fn(int(rec.c))
        cid = self.w.intern_code(fn.file, fn.name, int(fn.line or 0))
        where = self._exe_line(int(rec.c))
        line = where[1] if where else int(fn.line or 0)
        self.w.add_event(rec.ts, tid, "RAISE", None, cid, line, payload)

    def _longjmp(self, tid, rec) -> None:
        stack = self.stacks.get(tid) or []
        n = int(rec.d)
        if n <= 0 or not stack:
            return
        serial = self.jmp_serial.get(tid, 0) + 1
        self.jmp_serial[tid] = serial
        exc = {
            "kind": "longjmp", "type": "longjmp",
            "msg": "longjmp abandoned this frame", "serial": serial,
        }
        for _ in range(min(n, len(stack))):
            frame = stack.pop()
            self.w.close_frame(frame.fid, None, "unwind", exc)

    def _args(self, fn, extra) -> dict:
        try:
            blob = unpack_args(extra) if extra else []
        except ValueError:
            blob = []
        out = {}
        for i, param in enumerate(fn.params):
            flags = 0
            if i < len(blob):
                arg = blob[i]
                flags = arg.flags
                val = decode_param(param.typ, arg.raw, arg.slen, arg.sbytes)
            else:
                val = {"k": "unread"}
            saw = bool(isinstance(val, dict) and val.get("trunc"))
            if flags & FLAG_TRUNC:
                saw = True
                if isinstance(val, dict) and val.get("k") == "str" and "trunc" not in val:
                    val = dict(val)
                    val["trunc"] = True
            if isinstance(val, dict):
                val = rv.named(param.name, val)
            if saw:
                self.trunc += 1
            out[param.name] = val
        return out

    def _fn(self, pc: int) -> Func:
        bias, _name, image = self._place(pc)
        unrel = pc - bias
        fn = image.funcs.get(unrel) if image is not None else None
        if fn is not None:
            return fn
        sym = image.symbol_at(unrel) if image is not None else None
        return Func(unrel, sym or hex(unrel), "<unknown>", 0, [], VOID)

    def _loc(self, rec) -> str:
        pc = int(rec.c)
        if self._in_exe(pc):
            where = self._exe_line(pc)
            if where:
                return f"{where[0]}:{where[1]}"
            return hex(pc)
        bias, name, image = self._place(pc)
        base = os.path.basename(name) if name else "?"
        sym = None
        if image is not None:
            sym = image.symbol_at(pc - bias)
        if not sym:
            sym = hex(pc - bias)
        loc = f"{base}!{sym} (not instrumented)"
        extra = rec.extra or b""
        exe_bias = self._exe_bias()
        exe = self._image(self.exe)
        for j in range(0, len(extra) - 7, 8):
            ra = int.from_bytes(extra[j:j + 8], "little")
            if not ra or not self._in_exe(ra) or exe is None:
                continue
            cw = exe.line_at(ra - 1 - exe_bias) or exe.line_at(ra - exe_bias)
            if cw:
                loc += f", called from {cw[0]}:{cw[1]}"
                break
        return loc

    def _exe_line(self, pc):
        if not self._in_exe(pc):
            return None
        image = self._image(self.exe)
        if image is None:
            return None
        return image.line_at(pc - self._exe_bias())

    def _in_exe(self, pc) -> bool:
        found = _owner(self.objs, pc)
        if found is None:
            return False
        name = found[1]
        if name == "<exe>":
            return True
        if not self.exe:
            return False
        try:
            return os.path.abspath(name) == os.path.abspath(self.exe)
        except OSError:
            return False

    def _exe_bias(self) -> int:
        for bias, name in self.objs:
            if name == "<exe>":
                return bias
            if self.exe and name == self.exe:
                return bias
        return 0

    def _place(self, pc):
        found = _owner(self.objs, pc)
        if found is None:
            return 0, "", self._image(self.exe)
        bias, name = found
        path = self.exe if name == "<exe>" else name
        return bias, name, self._image(path)

    def _image(self, path):
        if not path:
            return None
        if path in self.images:
            return self.images[path]
        image = None
        try:
            if os.path.isfile(path):
                image = DwarfImage(path)
        except (OSError, ELFError, ValueError):
            image = None
        self.images[path] = image
        return image

    def _fp(self, tid, frame, kind) -> None:
        fp = self.fps.get(tid)
        if fp is None:
            fp = Fingerprint()
            self.fps[tid] = fp
        fp.update(frame.rel, frame.name, kind)
        self.framed.add(tid)

    def _output(self, path: Path, stream: str) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            return
        for i in range(0, len(data), _CHUNK):
            text = data[i:i + _CHUNK].decode("utf-8", "replace")
            if not text:
                continue
            text, hit = rv.text(text)
            if hit:
                rv.stats["values"] += 1
            if text:
                self.w.add_output(self.w.last_event_id or 0, stream, text)

    def _is_root(self) -> bool:
        root = self.side.get("root_pid")
        try:
            return root is not None and int(root) == self.pid
        except (TypeError, ValueError):
            return False

    def finish_meta(self, run_id, key, knobs, before, argv) -> None:
        boot = _json(self.pid_dir / "boot.json", {}) or {}
        exitj = _json(self.pid_dir / "exit.json", {}) or {}
        start = boot.get("start_ts", self.side.get("start_ts"))
        end = exitj.get("end_ts", self.side.get("end_ts", start))
        if start is None:
            start = 0
        if end is None:
            end = start
        status, signal, basis = _ending(self.pid, self.side, exitj)
        stored, table = redact.env(os.environ, key, knobs)
        redaction = redact.meta(key, knobs, table, by="converter")
        if redaction.get("mode") == "on":
            redaction = {**redaction, "values": rv.stats["values"] - before}
        caps = _capabilities(self)
        meta = {
            "run_id": run_id,
            "argv": argv,
            "cwd": self.cwd,
            "env": stored,
            "env_hash": hashlib.sha256(
                json.dumps(stored, sort_keys=True).encode()).hexdigest()[:16],
            "start_ts": start,
            "end_ts": end,
            "exit_status": status,
            "exit_status_basis": basis,
            "main_thread_ident": 1,
            "fingerprint_basis": "per-thread",
            "truncated_count": self.trunc,
            "source_hashes": _hashes(self.w.interned_files()),
            "recorder": RECORDER,
            "lang": LANG,
            "capabilities": caps,
            "redaction": redaction,
            "exe": self.exe,
        }
        if signal is not None:
            meta["exit_signal"] = signal
        for name in ("invocation", "driver_command", "harness_exit", "compiler"):
            if name in self.side:
                meta[name] = self.side[name]
        if "build_warnings" in self.side:
            meta["build_warnings"] = self.side["build_warnings"]
        if caps["threads"]:
            info = _json(self.pid_dir / "threads.json", {}) or {}
            meta["threads_started"] = int(info.get("started") or 0)
            live = info.get("live") or []
            meta["live_threads"] = [str(item) for item in live]
        if caps["children"]:
            kids = _fork_list(self.pid_dir / "forks.json")
            meta["children"] = [["(forked pid)", pid] for pid in kids]
            meta["spawn_syscalls"] = len(kids)
            meta["audit_errors"] = 0
        try:
            info = git_info(Path(self.cwd or "."))
        except OSError:
            info = {"git_sha": None, "git_dirty_hash": None}
        meta.update(info)
        meta["output_timing"] = "post"
        meta["incomplete"] = False
        for k, v in meta.items():
            self.w.set_meta(k, v)


def _capabilities(conv: _Conv) -> dict:
    warn = ""
    try:
        warn = (conv.pid_dir / "warn.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        warn = ""
    retval = "cet:" not in warn and not conv.side.get("no_retval")
    threads = _threads_started(conv.pid_dir / "threads.json") > 0
    children = bool(_fork_list(conv.pid_dir / "forks.json"))
    return {
        "line": False,
        "locals": False,
        "return_value": retval,
        "tasks": False,
        "threads": threads,
        "children": children,
        "stdin": False,
        "output": conv._is_root(),
        "object_identity": False,
        "refocus": False,
        "err_flow": False,
    }


def _threads_started(path: Path) -> int:
    info = _json(path, None)
    if not isinstance(info, dict):
        return 0
    try:
        return int(info.get("started") or 0)
    except (TypeError, ValueError):
        return 0


def _fork_list(path: Path) -> list[str]:
    info = _json(path, None)
    if not isinstance(info, list) or not info:
        return []
    return [str(item) for item in info]


def _ending(pid, side, exitj):
    root = side.get("root_pid")
    try:
        is_root = root is not None and int(root) == int(pid)
    except (TypeError, ValueError):
        is_root = False
    if is_root:
        harness = side.get("harness_exit")
        if isinstance(harness, dict) and harness.get("signal"):
            return None, int(harness["signal"]), "waited"
        if isinstance(harness, dict) and "status" in harness and harness["status"] is not None:
            return harness["status"], None, "waited"
        return None, None, "unwitnessed"
    if isinstance(exitj, dict) and exitj.get("signal"):
        return None, int(exitj["signal"]), "on_exit"
    if isinstance(exitj, dict) and "status" in exitj and exitj["status"] is not None:
        return exitj["status"], None, "on_exit"
    return None, None, "unwitnessed"


def _hashes(files) -> dict:
    out = {}
    for name in files:
        if not name or name in ("<unknown>", "?"):
            continue
        digest = hash_file(name)
        if digest:
            out[name] = digest
    return out


def _exe_path(side, pid_dir, argv, cwd) -> str:
    cand = side.get("exe")
    if isinstance(cand, str) and cand:
        return cand if os.path.isabs(cand) else os.path.abspath(os.path.join(cwd, cand))
    link = Path(pid_dir) / "exe"
    if link.exists():
        try:
            return os.fspath(link.resolve())
        except OSError:
            return os.path.abspath(link)
    if argv and isinstance(argv[0], str) and argv[0] not in ("", "?"):
        arg = argv[0]
        return arg if os.path.isabs(arg) else os.path.abspath(os.path.join(cwd, arg))
    return ""


def _objs(path: Path):
    out = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        bias, _, name = line.partition(" ")
        try:
            out.append((int(bias, 16), name.strip()))
        except ValueError:
            continue
    return out


def _owner(objs, pc):
    best = None
    for bias, name in objs:
        if "vdso" in name:
            continue
        if bias <= pc and (best is None or bias > best[0]):
            best = (bias, name)
    return best


def _rel(file, cwd) -> str:
    if not file or file.startswith("<"):
        return file or "<unknown>"
    if not cwd:
        return file
    try:
        cf = os.path.abspath(file)
        cc = os.path.abspath(cwd)
        if os.path.commonpath([cf, cc]) == cc:
            return os.path.relpath(cf, cc)
    except (ValueError, OSError):
        pass
    return file


def _assert_msg(extra: bytes, line) -> str:
    parts = (extra or b"").decode("utf-8", "replace").split("\0")
    assertion = parts[0] if parts else ""
    file = parts[1] if len(parts) > 1 else "?"
    func = parts[2] if len(parts) > 2 else "?"
    return f"{file}:{line}: {func}: Assertion `{assertion}' failed."


def _sig_msg(signo, addr, code):
    name = _SIGNAMES.get(signo, f"SIG{signo}")
    if code >= 1 << 63:
        code -= 1 << 64
    if signo == 11:
        how = _SEGV.get(code, str(code))
        return name, f"invalid memory access at {hex(addr)} ({how})"
    if signo == 6:
        return name, "abort() called"
    return name, f"fault at {hex(addr)}"


def _json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return default


def _count(payload) -> None:
    rv.stats["values"] += rv.count(payload)
