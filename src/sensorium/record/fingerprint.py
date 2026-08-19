"""Per-thread causal fingerprints: a rolling hash over the (code, kind)
sequence. Values, timing, and LINE events are deliberately excluded so
capture depth can never alter the fingerprint (spec section 4)."""
import hashlib

CAUSAL_KINDS = ("CALL", "RETURN", "RAISE", "HANDLED")


class Fingerprint:
    def __init__(self) -> None:
        self._h = hashlib.blake2b(digest_size=16)
        self.count = 0

    def update(self, file: str, qualname: str, kind: str) -> None:
        self._h.update(f"{file}\x1f{qualname}\x1f{kind}\n".encode())
        self.count += 1

    def hexdigest(self) -> str:
        return self._h.hexdigest()
