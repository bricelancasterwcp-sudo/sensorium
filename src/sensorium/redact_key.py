"""The per-store key the digests are taken under: its 32 bytes at
`<trace root>/redaction.key`, and the once-only creation that publishes that
file whole.

Split out of `redact.py`, which holds rule v1's NAME rule and is about to
hold the content rule beside it. The key is a third question -- not "which
names hold a secret" nor "which values look like one", but "what are the
digests taken under" -- and the three together would have carried one module
to this repository's 800-line ceiling. `redact.py` imports `Key`, `KEY_VAR`,
`KEY_FILE`, `KEY_BYTES` and `KEY_MODE` straight back, so `redact.Key` and
`redact.KEY_VAR` keep resolving for every caller that already spells them
that way: this is a move, not an interface.

Rule v1 replaces a secret-shaped value with `<redacted>` at the WRITER,
before anything reaches disk, and keeps an HMAC-SHA256 of the plaintext
under `<trace root>/redaction.key` so `refocus` and `diff` can still say
"this changed" without printing what it changed to (design §2, §3). That
sentence came from `redact.py`'s docstring with the code: its second half --
the file, its bytes, and the digest taken under them -- is this module, and
its first half stayed with the name rule.

Like `redact.py`, this module is pure -- it imports nothing from `record` or
`query` -- and never raises.
"""
import errno
import hashlib
import hmac
import os
import stat
from dataclasses import dataclass
from pathlib import Path

#: The hex key a driver hands a recorded process. DELETED from every
#: recorded environment rather than redacted (§3): a digest of the key under
#: the key is a pointless row, and `keyed: true` already implies it.
KEY_VAR = "SENSORIUM_REDACT_KEY"

#: `os.link` failures that mean "this filesystem cannot do that", not "this
#: went wrong": a filesystem without hard links (many network and container
#: mounts), or one that would be crossed. `os.replace` is the fallback there
#: -- atomic by name, but without `link`'s "loser cannot clobber the winner"
#: guarantee, which is why it is the fallback and not the mechanism.
_NO_LINK = frozenset({errno.EPERM, errno.ENOTSUP, errno.EXDEV})

#: The key file, a sibling of `traces/`, and its two fixed numbers.
KEY_FILE = "redaction.key"
KEY_BYTES = 32
KEY_MODE = 0o600
_ROOT_MODE = 0o700


@dataclass(frozen=True)
class Key:
    """The store's redaction key: 32 bytes, or none of them and a reason.

    Never raises, on any path. `material is None` is the whole of the
    unkeyed state -- `keyed`, `key_id` and `digest` all read from it -- and
    `problem` is the sentence `info` prints when a reader asks why.
    """
    path: Path
    material: bytes | None
    problem: str | None = None

    @property
    def keyed(self) -> bool:
        return self.material is not None

    @property
    def key_id(self) -> str | None:
        """`SHA-256(key)`, first 8 hex: whether two traces' digests are
        comparable at all (§6.2)."""
        if self.material is None:
            return None
        return hashlib.sha256(self.material).hexdigest()[:8]

    @classmethod
    def load(cls, root: Path) -> "Key":
        """Read `root/redaction.key`. Never creates it, never raises."""
        path = Path(root) / KEY_FILE
        try:
            material = path.read_bytes()
        except OSError as e:
            return cls(path, None, f"no {KEY_FILE}: {e}")
        if len(material) != KEY_BYTES:
            return cls(path, None, f"{KEY_FILE} is {len(material)} bytes, "
                                   f"expected {KEY_BYTES}")
        return cls(path, material)

    @classmethod
    def load_or_create(cls, root: Path) -> "Key":
        """The key, creating it once at 0600 if it is not there.

        The key is published BY CONTENT, never by an empty file that is
        filled in a moment later (ruling R15): 32 bytes go into a private
        `redaction.key.<pid>.tmp`, are written whole and fsynced, and only
        then does `os.link` put the finished file at its name. An `O_EXCL`
        open on the final name would be visible at 0 bytes for as long as the
        write takes -- a concurrent recorder arriving in that window reads an
        empty file and records unkeyed, and a process killed in it leaves a
        0-byte key that silently unkeys the store until a human deletes it.
        Linking cannot do either: the name appears with all 32 bytes behind
        it or not at all, and a loser's `FileExistsError` sends it to read
        the winner's file. The tmp is unlinked on every path.

        The store root is created 0700 on the way, because the first
        recording into a fresh `SENSORIUM_DIR` would otherwise be unkeyed for
        want of a directory.
        """
        root = Path(root)
        path = root / KEY_FILE
        try:
            root.mkdir(parents=True, exist_ok=True, mode=_ROOT_MODE)
        except OSError:
            pass  # the open below reports it, with the name of the file
        # A key that is already there is the answer, whatever it says: a
        # readable one is returned, and an unreadable or wrong-sized one is
        # the user's file and is never written over.
        existing = cls.load(root)
        if existing.keyed or path.exists():
            return existing
        material = os.urandom(KEY_BYTES)
        tmp = root / f"{KEY_FILE}.{os.getpid()}.tmp"
        try:
            problem = _write_key(tmp, material)
            if problem is not None:
                return cls(path, None, problem)
            return cls._publish(root, path, tmp, material)
        finally:
            _unlink(tmp)

    @classmethod
    def _publish(cls, root: Path, path: Path, tmp: Path,
                 material: bytes) -> "Key":
        """`tmp`'s finished content at `path`, or the winner's file re-read.

        `os.replace` is the fallback for a filesystem that has no hard links:
        it is atomic by name too, but it OVERWRITES, so a loser of the race
        would replace the winner's key and leave two recordings with digests
        that no longer compare. `load` afterwards is what makes that safe --
        whoever wrote last, the material returned is the material the file
        now holds, so the trace and the store never disagree.
        """
        try:
            os.link(tmp, path)
        except FileExistsError:
            return cls.load(root)
        except OSError as e:
            if e.errno not in _NO_LINK:
                return cls(path, None, f"cannot create {KEY_FILE}: {e}")
            try:
                os.replace(tmp, path)
            except OSError as e2:
                return cls(path, None, f"cannot create {KEY_FILE}: {e2}")
            return cls.load(root)
        return cls(path, material)

    @classmethod
    def from_hex(cls, text: str | None) -> "Key":
        """The key a driver handed over in `SENSORIUM_REDACT_KEY`.

        Exactly 64 hex characters and nothing else: `bytes.fromhex` accepts
        embedded whitespace, and a key that arrived down a wire between two
        implementations is checked for the shape it was promised in.
        """
        path = Path(KEY_VAR)
        if not text or len(text) != 2 * KEY_BYTES:
            return cls(path, None, f"{KEY_VAR} is not {2 * KEY_BYTES} hex "
                                   f"characters")
        try:
            return cls(path, bytes.fromhex(text))
        except ValueError:
            return cls(path, None, f"{KEY_VAR} is not hex")

    def digest(self, text: str) -> str | None:
        """`HMAC-SHA256(key, text)`, first 16 hex -- an equality identity,
        not a commitment -- or None when there is no key.

        `surrogateescape`, because an environment value arrives from
        `os.environ` with any undecodable byte held as a lone surrogate, and
        a bare `.encode()` raises on those: the whole recording would go down
        over one variable the shell happened to carry.

        `replace` behind it, because `surrogateescape` round-trips only
        U+DC80-U+DCFF: a LONE surrogate (U+D800, which `os.environ` cannot
        produce but a captured value or a value re-read from JSON can)
        raises there too, out of a module that documents that it never
        raises. Spelled here as a code point and not as an escape, because a
        docstring holding the character itself cannot be encoded by a reader
        that walks this file -- which is this rule, biting its own module. U+FFFD is the right identity for it and not merely a safe
        one -- Node's UTF-8 encoder writes exactly those bytes for the same
        string, so the two languages that can hold a lone surrogate agree on
        its digest; a Rust `String` cannot hold one at all.
        """
        if self.material is None:
            return None
        try:
            raw = text.encode("utf-8", "surrogateescape")
        except UnicodeEncodeError:
            raw = text.encode("utf-8", "replace")
        return hmac.new(self.material, raw, "sha256").hexdigest()[:16]

    def mode_note(self) -> str | None:
        """`key mode 0644 -- expected 0600` when the file is looser than it
        was created, else None. A loose key is READ anyway and named on
        `info`: refusing to record over the user's own file permissions
        helps nobody (§3). A key from `from_hex` has no file and no mode.
        """
        if self.path.name != KEY_FILE:
            return None
        try:
            mode = stat.S_IMODE(self.path.stat().st_mode)
        except OSError:
            return None
        if mode == KEY_MODE:
            return None
        return f"key mode {mode:04o} -- expected 0600"


def _write_key(tmp: Path, material: bytes) -> str | None:
    """All of `material` into a fresh `tmp`, fsynced and closed. The problem
    sentence, or None when the file on disk is whole.

    The write is a LOOP and its return value is checked: `os.write` is
    allowed to write fewer bytes than it was given, and a 20-byte key that
    memory believes is 32 is a store whose digests stop matching the day
    another process reads the file instead of inheriting the material.
    """
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, KEY_MODE)
    except OSError as e:
        return f"cannot create {KEY_FILE}: {e}"
    try:
        written = 0
        while written < len(material):
            step = os.write(fd, material[written:])
            if not step:
                return f"cannot write {KEY_FILE}: wrote {written} of "\
                       f"{len(material)} bytes"
            written += step
        os.fsync(fd)
    except OSError as e:
        return f"cannot write {KEY_FILE}: {e}"
    finally:
        try:
            os.close(fd)
        except OSError:
            pass  # the bytes are fsynced; a failing close is not a key error
    return None


def _unlink(path: Path) -> None:
    """Best effort, on every path out of `load_or_create`: a tmp left behind
    is a 32-byte secret nobody will ever read again."""
    try:
        os.unlink(path)
    except OSError:
        pass
