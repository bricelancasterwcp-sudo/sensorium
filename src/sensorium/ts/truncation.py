"""Trace-cap meta from one ELISION spool record.

Written only when calls were dropped. No record, or a record whose elided
count is zero, leaves the trace without truncation meta, so a spool from
before caps still converts. The wire stays v1: `file` and `c` are the same
ids a CALL carries, and this module resolves them through the FILE header
the same way a CALL becomes a code object.
"""
from __future__ import annotations

from sensorium.ts.spool import SpoolError


def truncation_meta(rec: dict | None, files: dict, spool_path: str) -> dict:
    """Optional meta. ``{}`` when nothing was dropped.

    ``files`` maps a wire file id to its FILE record. A name this record
    cannot resolve is a spool this converter cannot read.
    """
    if not rec:
        return {}
    try:
        dropped = rec["callsElided"]
    except KeyError as e:
        raise _bad(spool_path, e) from None
    if not isinstance(dropped, int) or isinstance(dropped, bool) or dropped <= 0:
        return {}
    rows = []
    for row in rec.get("elisions") or []:
        rows.append(_row(row, files, spool_path))
    try:
        limits = {
            "max_events": rec["maxEvents"],
            "max_bytes": rec["maxBytes"],
            "max_calls": rec["maxCalls"],
            "hit": list(rec["hit"]),
            "events_recorded": rec["eventsRecorded"],
            "calls_elided": dropped,
        }
    except (KeyError, TypeError) as e:
        raise _bad(spool_path, e) from None
    failures = rec.get("failuresKept") or 0
    if failures:
        limits["failures_kept"] = failures
    return {
        "trace_truncated": True,
        "trace_limits": limits,
        "elisions": rows,
    }


def _row(row: dict, files: dict, spool_path: str) -> dict:
    try:
        file_id = row["file"]
        index = row["c"]
    except KeyError as e:
        raise _bad(spool_path, e) from None
    header = files.get(file_id)
    if header is None:
        raise SpoolError(
            f"{spool_path}: an ELISION names file {file_id}, which no "
            "FILE record declared")
    codes = header["codes"]
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(codes):
        raise SpoolError(
            f"{spool_path}: an ELISION names site {index} of "
            f"{header['rel']}, which declared {len(codes)}")
    qualname, line, _kind = codes[index]
    return {
        "file": header["abs"],
        "qualname": qualname,
        "firstlineno": line,
        "elided": row["elided"],
        "kept": row["kept"],
    }


def _bad(spool_path: str, err: BaseException) -> SpoolError:
    return SpoolError(
        f"{spool_path}: an ELISION record is not the shape wire 1 "
        f"declares ({type(err).__name__}: {err})")
