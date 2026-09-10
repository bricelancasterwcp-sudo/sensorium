"""The wire: one JSONL spool, streamed back into records.

One file per container -- `<pid>-<threadId>.jsonl` -- one JSON object per
line, in the order the runtime observed the events. This module does the
reading and the two refusals that belong to it, and nothing else: what a
record MEANS is `ingest`'s.

The file is WALKED, never materialised (A3). BOOT is read eagerly, from
line 1, because nothing downstream can start without it; every later record
is yielded as the file is read, so the converter holds one record at a time
and not a list of two million. `exit` and `torn_tail` are therefore facts
only once the walk is DONE -- which is where the builder reads them, after
its loop.

Three properties of the file this module turns into facts:

* **The first record is BOOT**, because a spool that does not say what
  wrote it, under what environment, at what wall clock, is not a recording
  anybody can date or place. A spool with no BOOT is refused by name, and
  so is one whose BOOT is not on line 1: a reader that streams has already
  handed records to its caller by the time a later BOOT turns up.
* **There is exactly one BOOT** (R16). Two runtime instances writing one
  spool means two module graphs resolved the runtime by two specifiers,
  and every frame id, task id and file id in the file is then two
  independent counters interleaved. Nothing downstream can untangle that,
  so the spool is refused rather than converted into a plausible lie. The
  second BOOT is met mid-walk, which aborts a build already under way --
  `ingest.convert` unlinks the temporary file it had reserved, and the
  refusal comes back from the worker as a value, exactly as before.
* **The last line may be torn.** A container killed by SIGKILL loses
  whatever `appendFileSync` had not finished writing. A final line with no
  newline after it is that tail, and it is dropped -- the trace is then
  `incomplete`, which is the honest artifact. A malformed line ANYWHERE
  ELSE is a refusal: that is a corrupt file, not a killed process.
"""
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path


class SpoolError(Exception):
    """A spool cannot be read as one container's recording. Always names
    the file: `ingest` prints it beside the spool it refused, and the other
    spools of the same invocation are converted anyway."""


@dataclass
class Spool:
    """One container's records, in the order they were written."""

    path: Path
    boot: dict
    #: Every record after BOOT, in wire order, YIELDED as the file is
    #: walked. BOOT is not among them: it is the header, and every caller
    #: wants it by name. Consumable once, like any iterator -- a second
    #: reader of one spool calls `read` again.
    records: Iterator[dict] = field(default_factory=lambda: iter(()))
    #: The EXIT record, or None. Its presence is what `incomplete` is read
    #: from (R13) -- an EXIT with a `signal` still finalizes the trace,
    #: because the container lived long enough to say how it ended. Known
    #: once `records` is exhausted, which is where the builder reads it.
    exit: dict | None = None
    #: Whether the file's last line was cut mid-write. Known once
    #: `records` is exhausted.
    torn_tail: bool = False


def read(path) -> Spool:
    """`path` opened and its BOOT read, or `SpoolError` naming it.

    What comes back is a `Spool` whose `records` walks the rest of the file
    as it is iterated; the handle it holds is closed when the walk ends, by
    exhaustion or by refusal.
    """
    path = Path(path)
    try:
        fh = open(path, "rb")
    except OSError as e:
        raise SpoolError(f"{path} cannot be read as a spool: {e}") from None
    try:
        boot = _boot(path, fh)
    except BaseException:
        # Every refusal above the walk closes the handle here: the generator
        # that would otherwise have closed it is never created.
        fh.close()
        raise
    sp = Spool(path=path, boot=boot)
    sp.records = _stream(sp, fh)
    return sp


def _boot(path: Path, fh) -> dict:
    """Line 1, which is BOOT or the end of this spool's reading."""
    first = fh.readline()
    if not first.endswith(b"\n") or not first.strip():
        # No first line at all, nothing but a torn one, or a blank one: in
        # none of those cases does the file open with a BOOT record.
        raise SpoolError(f"no BOOT record in {path}: the spool does not say "
                         "what wrote it")
    boot = _parse(path, 1, _decode(path, 1, first))
    if boot.get("e") != "BOOT":
        raise SpoolError(f"no BOOT record in {path}: line 1 is a "
                         f"{boot['e']} record, and the spool does not say "
                         "what wrote it")
    caps = boot.get("capabilities")
    if caps is not None and not isinstance(caps, dict):
        # Present but not a map is not a declaration `build._meta` can merge
        # over the constant -- refused here, where BOOT is read, rather than
        # a worker crashing deep inside the merge.
        raise SpoolError(f"{path}: BOOT carries a capabilities value that "
                         "is not a map")
    return boot


def _stream(sp: Spool, fh) -> Iterator[dict]:
    """Every record after BOOT, yielded as `fh` is walked.

    `sp` is filled in as the walk goes: `torn_tail` when the last line has
    no newline after it, `exit` when the EXIT record goes past. Both are
    read by the builder AFTER its loop, which is the first point at which
    either is known. The handle is closed on every way out of here --
    exhaustion, torn tail, refusal, or a caller that stops early.
    """
    lineno = 1
    with fh:
        for raw in fh:
            lineno += 1
            if not raw.endswith(b"\n"):
                sp.torn_tail = True         # the tail a SIGKILL cut; dropped
                return
            line = _decode(sp.path, lineno, raw)
            if not line.strip():
                continue
            rec = _parse(sp.path, lineno, line)
            if rec.get("e") == "BOOT":
                raise SpoolError(f"two BOOT records in {sp.path}: two runtime "
                                 "instances wrote one spool")
            if rec.get("e") == "EXIT":
                sp.exit = rec
            yield rec


def _decode(path: Path, lineno: int, raw: bytes) -> str:
    """One line's bytes as text, or a refusal naming the line.

    The file is read as bytes so the walk never holds more than a line of
    it; a line that is not UTF-8 is then named where it is, which is more
    than the whole-file decode this replaced could say.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SpoolError(f"{path} line {lineno} is not UTF-8: {e} -- a spool "
                         "this recorder wrote is UTF-8 throughout") from None


def _parse(path: Path, lineno: int, line: str) -> dict:
    try:
        rec = json.loads(line)
    except json.JSONDecodeError as e:
        raise SpoolError(f"{path} line {lineno} is not readable JSON: {e} -- "
                         "a spool this recorder wrote is one object per "
                         "line") from None
    if not isinstance(rec, dict) or not isinstance(rec.get("e"), str):
        raise SpoolError(f"{path} line {lineno} is not a record: every line "
                         "carries an `e` naming its kind")
    return rec
