#!/usr/bin/env python3
"""E4″'s additions to the E4′ reader: R1's strip clause, R4's session
clause, and the rt hash the recorder's own fragment carries.

A module of its own for two reasons. `acceptance_e4p_read` is the E4′
record's evidence and had reached this project's 800-line ceiling; and
everything here is read for E4″'s endpoints -- H2 (is the fragment gone
from the compare?), H4 and H6 (is the session count exact?) and §1.5's two
tool hashes -- so it belongs with the record that gates on it.

`parse_refocus` calls `read_e4pp_clauses` on the one `env:` line it found,
so the fields land in the same parsed answer every other reading does. The
strip and the session set are read APART from the CHANGED list, which is
still the only one that withholds.
"""

from __future__ import annotations

import re


# ------------------------------------------- E4″: R1's strip, R4's session

#: R1's clause, `refocus_env.stripped_clause` verbatim -- the keys whose
#: value had the RECORDER's own `RUSTDOCFLAGS` fragment removed before the
#: compare. E4′ withheld all 61 pairs on that fragment alone; H2 asks
#: whether it is gone from the compare, so the clause has to be readable as
#: itself. `[^;)\n]` bounds it at the clause join (`; `) the relocated
#: clause is on the other side of, and at the closing bracket of the
#: `unchanged (...)` branch.
ENV_STRIPPED = re.compile(
    r"the recorder's own fragment stripped before comparing: "
    r"(?P<names>[^;)\n]+)")

#: R4/A-§3's session clause, `refocus_world._env_state`'s `told`. It appears
#: in TWO grammatical slots -- inside the brackets of the `unchanged outside
#: session set N (...)` branch, and after `(names only)` on the CHANGED one
#: -- so the pattern is anchored on its terminators rather than on either
#: line: a closing bracket, the two spaces that begin the clause join, or
#: the end of the line. A `[^)\n]+` alone would swallow `4 variable(s)
#: differ only by ...` on a CHANGED line and stop inside `variable(s)`.
ENV_SESSION = re.compile(
    r"(?P<k>\d+) session variable\(s\) differ: (?P<names>[^)\n]+?)"
    r"(?=\)|\s{2}|$)", re.M)
#: `refocus_world._capped`'s tail, shared with the CHANGED name list: the
#: printed list stops at eight names and counts the rest, so the COUNT is
#: authoritative and the names may be short (§1.4's kill 7).
ENV_SESSION_MORE = re.compile(r",\s*\+(?P<n>\d+) more$")
#: The `unchanged outside session set N` branch, which is the whole of R4:
#: an environment that differs ONLY on session set 1 does not withhold.
ENV_UNCHANGED_OUTSIDE = re.compile(
    r"^env: unchanged outside session set (?P<set>\d+) \(", re.M)

#: The 16 hex characters `cargo sensorium` puts in the fragment's directory
#: -- a digest of the driver binary and the `sensorium-rt` sources, so it
#: MOVES with every driver build. §1.5 publishes it per side per pair,
#: because the two being DIFFERENT is the one condition E4′ could not
#: create and the whole reason E4″ exists.
#:
#: This instrument's OWN pattern, deliberately narrower than
#: `refocus_env.RECORDER_FRAGMENT` and never imported from it: a reader
#: that read the rule under test would agree with it by construction.
RT_HASH = re.compile(r"/sensorium/rt/(?P<hash>[0-9a-f]{16})/(?:unwind|abort)"
                     r"(?=/|$|\s)")
#: How many FRAGMENTS a value carries, which is not how many times the hash
#: appears in it: one fragment names its directory twice (`--extern
#: sensorium_rt=<dir>/libsensorium_rt.rlib -L dependency=<dir>`), and §1.4's
#: H2 second reading asks for fragments per key per side. The printed clause
#: names the keys and never counts them, so this count is the INSTRUMENT's
#: own reading and is labelled as one.
RT_FRAGMENT_TOKEN = re.compile(r"--extern sensorium_rt=")


def read_e4pp_clauses(line: str, out: dict) -> None:
    """E4″'s two readings of the same `env:` line: what R1 STRIPPED before
    comparing, and what R4 exempted as session set 1.

    Both are `[]`/`0` -- never `None` -- once the line has been read: the
    line WAS read and it named none. `None` survives only where there is no
    `env:` line at all, which `parse_refocus`'s defaults carry.

    The session names are read BESIDE their count and never instead of it.
    `_capped` prints at most eight and appends `, +N more`, so on a set
    larger than that the count is the whole of it and the list is short --
    which §1.4's kill 7 makes a LENS fact rather than a smaller answer.
    """
    m = ENV_STRIPPED.search(line)
    out["env_stripped_keys"] = ([k.strip() for k in m.group("names").split(",")
                                 if k.strip()] if m else [])
    m = ENV_UNCHANGED_OUTSIDE.search(line)
    out["env_unchanged_outside_session"] = bool(m)
    out["env_session_set"] = int(m.group("set")) if m else None
    m = ENV_SESSION.search(line)
    if not m:
        out["env_session_keys"], out["env_session_n"] = [], 0
        out["env_session_keys_truncated"] = False
        return
    shown = m.group("names").strip()
    more = ENV_SESSION_MORE.search(shown)
    if more:
        shown = shown[:more.start()]
    out["env_session_keys"] = [k.strip() for k in shown.split(",")
                               if k.strip()]
    out["env_session_n"] = int(m.group("k"))
    out["env_session_keys_truncated"] = bool(more)


def rt_hash_of(env: dict | None) -> dict:
    """The rt hash the recorder's own fragment carries in ONE recorded
    environment (§1.5), or `null` with the reason there is none.

    Read from the trace's `meta.env`, per side, per pair: the original was
    written by `cargo-sensorium` 0.5.0 and the re-run by 0.5.2, the hash is
    a digest of the driver binary and the runtime sources, and their being
    DIFFERENT is what makes H2's strip testable at all. Two equal hashes on
    a pair mean that pair's strip was never tested, which H2's second
    reading reports rather than hides.
    """
    out = {"key": "RUSTDOCFLAGS", "value": None, "fragments": 0,
           "occurrences": 0, "reason": None, "hashes": []}
    if not isinstance(env, dict):
        out["reason"] = ("no recorded environment to read `RUSTDOCFLAGS` "
                         "out of")
        return out
    value = env.get("RUSTDOCFLAGS")
    if not isinstance(value, str) or not value:
        out["reason"] = ("the recorded environment carries no `RUSTDOCFLAGS` "
                         "value, so it carries no fragment of ours")
        return out
    hashes = [m.group("hash") for m in RT_HASH.finditer(value)]
    out["hashes"] = hashes
    out["occurrences"] = len(hashes)
    out["fragments"] = len(RT_FRAGMENT_TOKEN.findall(value))
    if not hashes:
        out["reason"] = ("`RUSTDOCFLAGS` is set but carries no "
                         "`/sensorium/rt/<16 hex>/<unwind|abort>` component, "
                         "so this recorder wrote no fragment into it")
        return out
    if len(set(hashes)) > 1:
        out["reason"] = (f"`RUSTDOCFLAGS` carries {len(set(hashes))} "
                         f"DIFFERENT rt hashes ({sorted(set(hashes))}); the "
                         "first is reported and the rest are recorded beside "
                         "it, never averaged")
    out["value"] = hashes[0]
    return out


__all__ = ["ENV_SESSION", "ENV_SESSION_MORE", "ENV_STRIPPED",
           "ENV_UNCHANGED_OUTSIDE", "RT_FRAGMENT_TOKEN", "RT_HASH",
           "read_e4pp_clauses", "rt_hash_of"]
