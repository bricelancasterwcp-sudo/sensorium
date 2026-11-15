"""Payload text, including the optional string table.

A payload is JSON. When the same long text is stored again, the writer
keeps the first copy inline and writes later copies as ``#<id>``, where
``<id>`` is a row in the optional ``strings`` table (``body`` is that
JSON text). Traces without the table, and every payload that does not
start with ``#`` followed by digits, are read exactly as before.

``TRACE_FORMAT`` stays 4. The table is an access path for repeated text,
created only once a duplicate exists. A reader that does not know the
table still sees the first copy of every distinct payload as JSON.
"""
from __future__ import annotations

import json
import sqlite3

# Long enough that a short test payload is never rewritten, and short
# enough that a repeated repr (the 200-byte capture cap) is.
INTERN_MIN = 120


def looks_interned(text: str) -> bool:
    return len(text) > 1 and text[0] == "#" and text[1:].isdigit()


def load_strings(conn: sqlite3.Connection) -> dict[int, str]:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='strings'"
    ).fetchone()
    if row is None:
        return {}
    return {i: body for i, body in conn.execute("SELECT id, body FROM strings")}


def expand(text: str | None, strings: dict[int, str]) -> str | None:
    """The JSON text a payload cell stores, after one intern lookup."""
    if text is None or not strings or not looks_interned(text):
        return text
    body = strings.get(int(text[1:]))
    return text if body is None else body


def decode(text: str | None, strings: dict[int, str] | None = None):
    """``json.loads`` of a payload cell. ``None`` stays ``None``."""
    text = expand(text, strings or {})
    return None if text is None else json.loads(text)


def drop_unreferenced(conn: sqlite3.Connection) -> None:
    """Delete ``strings`` rows no event still points at.

    ``redact`` rewrites a payload from ``#<id>`` back to JSON. The row it
    replaced would otherwise keep the pre-redaction text in the file.
    """
    if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='strings'"
    ).fetchone() is None:
        return
    used: set[int] = set()
    for (text,) in conn.execute(
            "SELECT payload FROM events WHERE payload IS NOT NULL"):
        if text and looks_interned(text):
            used.add(int(text[1:]))
    if not used:
        conn.execute("DELETE FROM strings")
        return
    marks = ",".join("?" * len(used))
    conn.execute(f"DELETE FROM strings WHERE id NOT IN ({marks})", tuple(used))
