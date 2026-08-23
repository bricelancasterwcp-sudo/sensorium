"""Per-thread AND per-task causal fingerprints: a rolling hash over the
(code, kind) sequence. Values, timing, and LINE events are deliberately
excluded so capture depth can never alter the fingerprint (spec section 4).

One class, two uses (spec D6): a thread's fingerprint covers the causal
events that ran in NO asyncio task, and every task serial owns one of its
own. Which events go where is the tracer's decision (`_fp_for`), not this
file's -- what a hash covers is recorded in the trace's `fingerprint_basis`
so a reader is never left to infer it from the digest.
"""
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
