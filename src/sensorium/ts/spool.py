"""The wire: one JSONL spool, read back into records.

One file per container -- `<pid>-<threadId>.jsonl` -- one JSON object per
line, in the order the runtime observed the events. This module does the
reading and the two refusals that belong to it, and nothing else: what a
record MEANS is `ingest`'s.

Three properties of the file this module turns into facts:

* **The first record is BOOT**, because a spool that does not say what
  wrote it, under what environment, at what wall clock, is not a recording
  anybody can date or place. A spool with no BOOT is refused by name.
* **There is exactly one BOOT** (R16). Two runtime instances writing one
  spool means two module graphs resolved the runtime by two specifiers,
  and every frame id, task id and file id in the file is then two
  independent counters interleaved. Nothing downstream can untangle that,
  so the spool is refused rather than converted into a plausible lie.
* **The last line may be torn.** A container killed by SIGKILL loses
  whatever `appendFileSync` had not finished writing. A final line with no
  newline after it is that tail, and it is dropped -- the trace is then
  `incomplete`, which is the honest artifact. A malformed line ANYWHERE
  ELSE is a refusal: that is a corrupt file, not a killed process.
"""
import json
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
    #: Every record after BOOT, in wire order. BOOT is not among them: it
    #: is the header, and every caller wants it by name.
    records: list[dict] = field(default_factory=list)
    #: The EXIT record, or None. Its presence is what `incomplete` is read
    #: from (R13) -- an EXIT with a `signal` still finalizes the trace,
    #: because the container lived long enough to say how it ended.
    exit: dict | None = None
    #: Whether the file's last line was cut mid-write.
    torn_tail: bool = False


def read(path) -> Spool:
    """`path` read into a `Spool`, or `SpoolError` naming it."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise SpoolError(f"{path} cannot be read as a spool: {e}") from None
    lines, torn = _lines(text)

    boot = None
    records: list[dict] = []
    exit_rec = None
    for lineno, line in lines:
        rec = _parse(path, lineno, line)
        if rec.get("e") == "BOOT":
            if boot is not None:
                raise SpoolError(
                    f"two BOOT records in {path}: two runtime instances "
                    "wrote one spool")
            boot = rec
            continue
        if rec.get("e") == "EXIT":
            exit_rec = rec
        records.append(rec)
    if boot is None:
        raise SpoolError(f"no BOOT record in {path}: the spool does not say "
                         "what wrote it")
    return Spool(path=path, boot=boot, records=records, exit=exit_rec,
                 torn_tail=torn)


def _lines(text: str) -> tuple[list[tuple[int, str]], bool]:
    """`(lineno, line)` for every line worth parsing, and whether the last
    one was dropped as a torn tail."""
    if not text:
        return [], False
    torn = not text.endswith("\n")
    raw = text.split("\n")
    if torn:
        raw = raw[:-1]
    return ([(i, ln) for i, ln in enumerate(raw, start=1) if ln.strip()],
            torn)


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
