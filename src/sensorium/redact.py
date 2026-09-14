"""Rule v1: which NAMES hold a secret, the knobs that amend that judgement,
and the per-store key the digests are taken under.

Every recorder stored the whole process environment in plaintext until this
slice, so a trace of any program launched from this box's shell held a live
`CLAUDE_CODE_MESSAGING_TOKEN` at 0644. Rule v1 replaces such a value with
`<redacted>` at the WRITER, before anything reaches disk, and keeps an
HMAC-SHA256 of the plaintext under `<trace root>/redaction.key` so `refocus`
and `diff` can still say "this changed" without printing what it changed to
(design §2, §3).

WHAT THIS IS NOT
----------------
**Not a secret scanner.** The rule fires on a name's SEGMENTS, so a secret
in a variable called `x`, or one this set has never heard of, is stored as
typed; the content rule (patterns inside a value, whatever the name) is
PR B's and is a floor too. `SENSORIUM_REDACT_NAMES` is the remedy for a
name this misses and `SENSORIUM_REDACT_ALLOW` for one it wrongly fires on,
and both are recorded so a reader sees what the recording was made under.
Matching is segment-exact, never substring: substring `KEY` would fire on
`MONKEY_PATCH` and substring `PASS` on `BYPASS_CACHE`. The false positives
that do fire (`SSH_AUTH_SOCK`, `GPG_KEY_ID`: a path and an id) cost one
plaintext path in a trace, which the digest still makes comparable.

THE FIXTURE
-----------
`docs/trace-format/redaction-v1.json` holds every `split` and `fires` case,
and `sensorium-rt`'s and the TypeScript recorder's suites read the SAME
file. A case belongs there, not in a test module: three implementations of
one rule agree only on what all three are asked.

This module is pure -- it imports nothing from `record` or `query` -- and
never raises.
"""
import re
from collections.abc import Mapping
from dataclasses import dataclass

# The store key, split out at this module's own seam: the name rule
# above and the content rule beside it both grow in here, and the key is
# neither of them. Re-exported so `redact.Key` and `redact.KEY_VAR` keep
# resolving: these are one rule's internals across two files, not
# separate modules with surfaces of their own.
from sensorium.redact_key import (  # noqa: F401
    KEY_BYTES, KEY_FILE, KEY_MODE, KEY_VAR, Key)

#: The rule's identity, stamped in every trace it touches. A later rule is
#: v2; v1 is never amended, because a trace that says `v1` has to mean one
#: thing forever.
RULE = "v1"

#: What a whole-redacted value reads as. The spelling this repo's renderers
#: already use for a withheld thing (`<unread>`, `<not in scope>`).
REDACTED = "<redacted>"

OFF_VAR = "SENSORIUM_NO_REDACT"
NAMES_VAR = "SENSORIUM_REDACT_NAMES"
ALLOW_VAR = "SENSORIUM_REDACT_ALLOW"

#: §2.1's set, plus `PWD` (ruling R10, below). A segment here fires the rule;
#: every one of them has a firing case in the fixture, and `test_the_fixture_
#: gives_every_segment_of_the_rule_a_firing_case` is what keeps that true. The
#: four compounds (`APIKEY`, `ACCESSKEY`, `SECRETKEY`, `AUTHTOKEN`) exist
#: because a name written as one word -- `apikey` -- splits into one segment
#: that none of `API`, `KEY` matches.
SEGMENTS = frozenset("""
KEY APIKEY TOKEN SECRET SECRETS PASSWORD PASSWD PASSPHRASE PASS
AUTH AUTHORIZATION CREDENTIAL CREDENTIALS CREDS PRIVATE
COOKIE COOKIES SIGNATURE BEARER JWT DSN ACCESSKEY SECRETKEY AUTHTOKEN
PWD
""".split())

#: `PWD` fires only as a segment of a LONGER name: `MYSQL_PWD` and `DB_PWD`
#: are passwords, and `PWD` and `OLDPWD` are the shell's working directory,
#: on every machine that has ever run a shell. §2.1 names both of those as
#: non-firing and they still are -- one segment, so this condition holds them
#: out while the two-segment database variables come in.
_PWD = "PWD"

#: Whole NORMALISED names that fire whatever their segments say. Segment-exact
#: matching cannot see inside a compound word: `PGPASSWORD` splits into the
#: single segment `PGPASSWORD`, which is neither `PG` nor `PASSWORD`, and
#: libpq's standard password variable was stored in plaintext by rule v1 until
#: the census of `tests/fixtures/benign-env-names.txt` said so. Kept apart
#: from `SEGMENTS` because it is a different question -- "is this word one of
#: the few known one-word secrets" rather than "does this name have a
#: secret-shaped part" -- and because a name dropped in here silently would
#: otherwise widen the segment rule for every name that contains it. Short by
#: design: a name earns a place only when a census or a report shows it
#: matters, never on imagination.
EXACT: frozenset[str] = frozenset({"PGPASSWORD"})

#: The two camelCase boundaries, in this order: an uppercase RUN followed by
#: Upper+lower (`HTTPToken` -> `HTTP Token`), then lower-or-digit followed by
#: upper (`apiKey` -> `api Key`). Verbatim from §2.1, because three
#: implementers would otherwise spell them three ways.
_CAMEL_RUN = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_STEP = re.compile(r"([a-z0-9])([A-Z])")
_SEPARATOR = re.compile(r"[^A-Za-z0-9]+")


def split(name: str) -> list[str]:
    """`name`'s uppercased segments: `apiKey` -> `[API, KEY]`,
    `SSH_AUTH_SOCK` -> `[SSH, AUTH, SOCK]`, `XAUTHORITY` -> `[XAUTHORITY]`.

    Empty segments are dropped, so `__init__` is `[INIT]` and `""` is `[]`.
    """
    spaced = _CAMEL_STEP.sub(r"\1 \2", _CAMEL_RUN.sub(r"\1 \2", name))
    return [part.upper() for part in _SEPARATOR.split(spaced) if part]


def normalise(name: str) -> str:
    """The comparison form the two knobs use: the segments, joined. So
    `myco_dsn`, `MYCO_DSN` and `mycoDsn` are one name to a user's list."""
    return "".join(split(name))


@dataclass(frozen=True)
class Knobs:
    """The three environment variables, as read once at record time.

    `names` and `allow` are held NORMALISED, so a comparison against a
    variable's own normalised form is exact and case-blind at once.
    """
    off: bool
    names: frozenset[str]
    allow: frozenset[str]

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> "Knobs":
        """`SENSORIUM_NO_REDACT` reads like `SENSORIUM_NO_INVOCATION_LOG`
        (`invocations._log_disabled`): any non-empty value other than `"0"`
        turns the rule off, and `=0`, empty and unset all leave it on."""
        off = environ.get(OFF_VAR)
        return cls(bool(off) and off != "0",
                   _listed(environ, NAMES_VAR), _listed(environ, ALLOW_VAR))

    def meta(self) -> dict:
        return {"names": sorted(self.names), "allow": sorted(self.allow)}


def _listed(environ: Mapping[str, str], var: str) -> frozenset[str]:
    """A comma list, stripped, empties dropped, each entry normalised. An
    entry that normalises to nothing (`","`, `"-"`) is dropped too -- an
    empty string in the set would match a nameless value."""
    raw = (environ.get(var) or "").split(",")
    return frozenset(n for n in (normalise(part.strip()) for part in raw) if n)


def fires(name: str, knobs: Knobs) -> bool:
    """Whether the name rule fires on `name`.

    Allow first, and it WINS over `names` -- a user's statement about their
    own variable outranks their own list (§2.3). Then `EXACT`, then the
    segments. `knobs.off` is not read here: turning the whole rule off is
    `env`'s business, one level up, so that this function stays the answer to
    "is this a secret-shaped name".
    """
    segments = split(name)
    normalised = "".join(segments)
    if normalised in knobs.allow:
        return False
    if normalised in knobs.names:
        return True
    if normalised in EXACT:
        return True
    multi = len(segments) > 1
    return any(segment in SEGMENTS and (multi or segment != _PWD)
               for segment in segments)


def env(environ: Mapping[str, str], key: Key,
        knobs: Knobs) -> tuple[dict[str, str], dict[str, str | None]]:
    """(the environment to STORE, the name -> digest table for `redaction`).

    A NEW dict either way -- the caller's mapping is never touched -- minus
    `KEY_VAR`. With the rule off, that deletion is the only thing that
    happens, and `meta` says `mode: "off"` so a reader knows the plaintext
    was recorded on purpose. Applied to an ALREADY redacted environment this
    would digest the marker; §5.4 is why that never happens -- a converter
    meeting a `mode: "on"` header trusts it and does not re-run the rule.

    The table's keys are SORTED (R13) so that one environment gives one
    table, byte for byte, whichever language wrote it -- Rust's `BTreeMap`
    and the TypeScript implementation sort too. The stored environment keeps
    the order it arrived in; only the table is ordered.
    """
    stored = {name: value for name, value in environ.items()
              if name != KEY_VAR}
    if knobs.off:
        return stored, {}
    table: dict[str, str | None] = {}
    for name in sorted(stored):
        if fires(name, knobs):
            table[name] = key.digest(stored[name])
            stored[name] = REDACTED
    return stored, table


def meta(key: Key, knobs: Knobs, table: dict[str, str | None],
         by: str = "recorder") -> dict:
    """The trace's `redaction` key (§4.3). `by` is the LAST hand that applied
    the rule: `recorder`, `converter` or `retrofit`."""
    if knobs.off:
        return {"rule": RULE, "mode": "off"}
    return {"rule": RULE, "mode": "on", "keyed": key.keyed,
            "key_id": key.key_id, "env": table, **knobs.meta(), "by": by}


#: One side's account of one name: its digest, the key that digest was taken
#: under, and whether that side had a key at all. `None` in place of a Side
#: means the side did not redact the name -- its value is plaintext.
Side = tuple[str | None, str | None, bool]


def compare(before: str | None, after: str | None, was: Side | None,
            now: Side | None, key: Key) -> bool | None:
    """§6.2's table, once, for one name: True equal, False differs, None
    unverifiable.

    `before`/`after` are the two sides' stored values -- read only on a side
    that did NOT redact, where the value is the plaintext itself. A value
    missing from the plaintext side is a DIFFERENCE and a verified one (the
    variable vanished), never an unverifiability.

    Called only for a name at least one side redacted; plain equality is
    the caller's answer for every other name, as it always was.
    """
    if was is not None and now is not None:
        (mine, my_key, my_keyed), (theirs, their_key, their_keyed) = was, now
        if not (my_keyed and their_keyed) or my_key != their_key:
            return None
        if mine is None or theirs is None:
            return None
        return mine == theirs
    if was is None and now is None:
        return before == after
    side, plain = (was, after) if was is not None else (now, before)
    digest, under, keyed = side
    if digest is None or not keyed or not key.keyed or key.key_id != under:
        return None
    if plain is None:
        return False
    return key.digest(plain) == digest


def uncomparable(was_meta: dict, now_meta: dict | None,
                 key: Key) -> tuple[list[str], str | None]:
    """The redacted names whose comparison `compare` cannot decide, sorted,
    and the reason word -- `([], None)` when there are none.

    `now_meta is None` is a live plaintext side with no table of its own
    (the Python re-run): its names are verifiable under the store's key,
    and appear here only when that key is gone or is not the one that wrote
    the digests.
    """
    was_table, was_env = _table(was_meta), _stored(was_meta)
    now_table, now_env = _table(now_meta), _stored(now_meta)
    names, unkeyed = [], False
    for name in sorted(set(was_table) | set(now_table)):
        mine, theirs = _side(was_meta, name), _side(now_meta, name)
        if compare(was_env.get(name), now_env.get(name),
                   mine, theirs, key) is not None:
            continue
        names.append(name)
        unkeyed = unkeyed or _unkeyed(mine) or _unkeyed(theirs)
        if mine is None or theirs is None:
            # One side is plaintext, so the STORE's key is the one doing the
            # verifying and its absence is the reason.
            unkeyed = unkeyed or not key.keyed
    if not names:
        return [], None
    return names, "unkeyed" if unkeyed else "different keys"


def _redaction(meta_dict: dict | None) -> dict:
    return ((meta_dict or {}).get("redaction") or {})


def _table(meta_dict: dict | None) -> dict:
    return _redaction(meta_dict).get("env") or {}


def _stored(meta_dict: dict | None) -> dict:
    return (meta_dict or {}).get("env") or {}


def _side(meta_dict: dict | None, name: str) -> Side | None:
    table = _table(meta_dict)
    if name not in table:
        return None
    redaction = _redaction(meta_dict)
    return table[name], redaction.get("key_id"), bool(redaction.get("keyed"))


def _unkeyed(side: Side | None) -> bool:
    return side is not None and (not side[2] or side[0] is None)
