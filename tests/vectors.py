"""Build a trace from a conformance vector (docs/trace-format/vectors).

A vector is a JSON description of a trace -- meta, code objects, frames,
events, tasks -- plus the questions the CLI must answer about it. This
module turns one into a real trace file through the ordinary `TraceWriter`,
so what the vectors pin is the format itself and not a second, parallel
writer. Frame and event ids are their 1-based positions in the vector's
lists, which is what lets a vector refer to `e2` or `f1` by hand.
"""
import json
from pathlib import Path

from sensorium.record.fingerprint import Fingerprint
from sensorium.store.writer import TraceWriter

VECTORS = Path(__file__).resolve().parent.parent / "docs" / "trace-format" / "vectors"


def load_all() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(VECTORS.glob("v*.json"))]


def sub(text: str, run_ids: list[str]) -> str:
    """`$RUN` / `$RUN2` -> the run ids this vector was built with.

    `$RUN2` is substituted FIRST: replacing `$RUN` first turns `$RUN2` into
    `<run-id>2`, which resolves to no trace at all -- and does it silently,
    as a lookup failure that reads like a vector-authoring mistake."""
    if len(run_ids) > 1:
        text = text.replace("$RUN2", run_ids[1])
    return text.replace("$RUN", run_ids[0])


def _subst(v, run_ids):
    if isinstance(v, str):
        return sub(v, run_ids)
    if isinstance(v, list):
        return [_subst(x, run_ids) for x in v]
    if isinstance(v, dict):
        return {k: _subst(x, run_ids) for k, x in v.items()}
    return v


def _frame_id(ev: dict, fids: list[int]) -> int | None:
    """The row's `frame_id` -- always NULL on a CALL, whatever the vector says.

    A frame-opening CALL is written with `frame_id` NULL by the recorder
    (`tracer._on_start`): the frame does not exist yet when the event is
    written, and the link runs the other way, through
    `frames.call_event_id`. Only the rows a recorder emits INSIDE an open
    frame -- RETURN, RAISE, HANDLED, LINE, YIELD, RESUME -- carry one. A
    vector that named a frame on a CALL would describe a row no recorder
    produces, so it is refused rather than quietly built.
    """
    if ev["kind"] == "CALL":
        if ev.get("frame"):
            raise ValueError(
                f"CALL event names frame f{ev['frame']}: a CALL row carries "
                "frame_id NULL (the frame links back through "
                "frames.call_event_id), so drop the key from the vector")
        return None
    return fids[ev["frame"] - 1] if ev.get("frame") else None


def build(vector: dict, sdir: Path, run_ids: list[str]) -> Path:
    path = Path(sdir) / "traces" / f"{run_ids[0]}.db"
    w = TraceWriter(path, batch=1)
    codes = [w.intern_code(f, q, ln) for f, q, ln in vector.get("codes", [])]
    fids = []
    for fr in vector.get("frames", []):
        fids.append(w.open_frame(fr["parent"], codes[fr["code"] - 1], fr["call"],
                                 fr["depth"], fr["thread"], fr.get("kind", "function")))
    for ev in vector.get("events", []):
        w.add_event(ev.get("ts", 0), ev["thread"], ev["kind"],
                    _frame_id(ev, fids),
                    codes[ev["code"] - 1] if ev.get("code") else None,
                    ev.get("line"), ev.get("payload"), ev.get("task"))
    for fr, fid in zip(vector.get("frames", []), fids):
        if fr.get("return") is not None or fr.get("closed_by"):
            w.close_frame(fid, fr.get("return"), fr.get("closed_by", "return"),
                          fr.get("unwind_exc"))
    for tid, name, thread in vector.get("tasks", []):
        w.add_task(tid, name, thread)
    if vector.get("fingerprints") == "compute":
        _compute_fingerprints(w, vector)
    meta = _subst(vector.get("meta", {}), run_ids)
    for k, v in meta.items():
        if k == "incomplete":
            continue                      # written last, like the recorder
        w.set_meta(k, v)
    if "incomplete" in meta:
        w.set_meta("incomplete", meta["incomplete"])
    w.close()
    return path


def _compute_fingerprints(w, vector) -> None:
    """One fingerprint row per thread and one per task, over the same
    `(file, qualname, kind)` sequence the recorder hashes -- events that ran
    in a task go to that task's row, the rest to the thread's (the
    `per-task` basis).

    `threads_with_rows` is how a vector says a thread must have a row even
    though it emitted nothing: the recorder writes a zero-count row for
    every thread it saw, and a main thread whose work all happened in tasks
    is exactly the case `diff` has to handle.

    Tasks need no such key: TRACE-FORMAT §6 requires a row for every minted
    unit of work, "a unit that ran no causal event gets a zero-count
    fingerprint row rather than no row", so the rows are driven off the
    vector's `tasks` list and not off the events. Deriving them from the
    events instead left a silent task unable to be expressed at all -- the
    builder could not write the one shape the rule is about.
    """
    per_thread: dict[int, Fingerprint] = {}
    per_task: dict[int, Fingerprint] = {}
    for ev in vector.get("events", []):
        if ev["kind"] not in ("CALL", "RETURN", "RAISE", "HANDLED"):
            continue
        f, q, _ = vector["codes"][ev["code"] - 1]
        target = (per_task.setdefault(ev["task"], Fingerprint()) if ev.get("task")
                  else per_thread.setdefault(ev["thread"], Fingerprint()))
        target.update(f, q, ev["kind"])
    threads = (vector.get("threads_with_rows")
               or sorted({ev["thread"] for ev in vector.get("events", [])}))
    for thread in threads:
        fp = per_thread.get(thread, Fingerprint())
        w.write_fingerprint(thread, fp.hexdigest(), fp.count)
    # Declared order first, then any task only the events name -- a vector
    # that forgot to declare one still gets its row rather than losing it.
    tids = [tid for tid, _name, _thread in vector.get("tasks", [])]
    tids += sorted(t for t in per_task if t not in tids)
    w.write_task_fingerprints([(t, per_task.get(t, Fingerprint()).hexdigest(),
                                per_task.get(t, Fingerprint()).count)
                               for t in tids])
