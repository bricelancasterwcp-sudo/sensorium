"""What a trace says about its own coverage, read one way by every command.

Two declarations live here, because both answer the same question -- may an
absence in this trace be reported as a fact about the program? -- and both
must be read identically everywhere, or the same trace answers 1 in one
command and 3 in another.

Capability declarations (spec §5.2): a format-4 trace says what its recorder
produces. Before format 4 nothing was declared and only the Python recorder
existed, so an absent key meant "older": the sentence for it says
"predates". On a format-4 trace an absent record is a declaration, and the
sentence says so -- never "older", never a zero.

The `incomplete` flag: a recording that never reached its finalize pass
stopped mid-flight, so what it does not hold may simply be what it never got
to write. `none_status` is that fact applied to the emptiest answer a
listing command has, and `print_incomplete` is the banner that explains the
status it returns.
"""
from sensorium.exit import NEGATIVE, UNSETTLED


def witness_gap(trace, cap: str, keys: str, legacy: str) -> str:
    """Why a record is absent, in the words the trace itself supports.

    Three states of `trace.declares(cap)`, three different facts:

    - None: this trace predates the declaration outright -- no
      `capabilities` key, and it is the Python recorder's (the only one
      that existed before format 4). `legacy` is the calling site's own
      pre-format-4 sentence, passed in whole and returned unchanged: every
      trace in this state must read exactly as it did before this module
      existed.
    - False: the recorder declared it does not produce `cap`. The absence
      is what the recorder SAID, not an accident of age.
    - True: the recorder declared it DOES produce `cap`, and the witness
      key is still missing. Not a corner nobody reaches: today's Python
      recorder writes `recorder`/`lang`/`capabilities` (all True) at
      `install()` time, at the START of a run, and writes `threads_started`
      only at the finalize pass (`set_meta_final`) -- so every recording
      still in flight, or that died before finalizing, is in this state,
      and a fixture that deletes a witness key from an otherwise-finalized
      trace lands here too. The honest sentence names the contradiction; it
      must never assert `capabilities.<cap>: false` about a trace whose own
      dict says true.
    """
    declared = trace.declares(cap)
    if declared is None:
        return legacy
    if declared is False:
        return (f"recorder {trace.recorder} declares {cap} not witnessed "
                f"(capabilities.{cap}: false), so there is no {keys} record "
                "to read; absence of the record is not a record of absence")
    return (f"recorder {trace.recorder} declares {cap} witnessed, but this "
            f"trace carries no {keys} record -- the recording did not "
            "finish, or the record was removed; absence of the record is "
            "not a record of absence")


def require(trace, cap: str, command: str) -> str | None:
    """A refusal sentence when `trace` does not produce `cap`, else None.
    The instrument never answers from data it does not have: this is that
    rule applied to a whole command instead of one value."""
    declared = trace.declares(cap)
    if declared is None or declared:
        return None
    return (f"{command} needs {cap}, which recorder {trace.recorder} "
            f"declares it does not produce (capabilities.{cap}: false); "
            "nothing was checked")


def none_status(trace) -> int:
    """The status of an EMPTY answer: "none", or "I never finished looking"?

    `matches: 0`, `no frames recorded` and `sightings: 0` are the trace
    answering "no" only when the recording is whole. A run whose meta says
    `incomplete` stopped mid-flight and the events after the cut were never
    written, so an empty result there reports where the RECORDING ended, not
    what the program did -- and the fix is to record again, which is what 3
    means. Absence of the record is not a record of absence, applied to the
    emptiest answer each listing command has.

    One predicate for all of them (the general table row added 2026-09-04),
    so they cannot drift: a status decided command by command is a status
    that reads 1 in `grep` and 3 in `flow` about one trace.

    `exceptions` is deliberately not a caller. Its empty answer already
    splits three ways on facts this predicate cannot see (`no RAISE events
    recorded (see INCOMPLETE above)` is 3, `no exceptions recorded` is 1),
    and it reads the flag itself to do that.
    """
    return UNSETTLED if trace.meta.get("incomplete") else NEGATIVE


def print_incomplete(trace, consequence: str) -> None:
    """The INCOMPLETE banner, in the one wording every command shares.

    Any command that can answer "none" prints this: `none_status` turns an
    empty answer on an unfinalized trace into a 3, and a 3 whose output
    says nothing about why is a number the reader cannot act on. It is
    printed BEFORE the rows for the same reason `watch` prints its
    NEVER RECORDED banner above the verdict -- what follows cannot be read
    without it.

    `consequence` is the one clause that differs per command: what
    specifically is missing from THIS command's output. The first line is
    shared, so a trace that stopped mid-run says so in the same words
    wherever the reader meets it.
    """
    if not trace.meta.get("incomplete"):
        return
    print("INCOMPLETE: this recording never finalized, so it may stop "
          "mid-run")
    print("  " + consequence)
