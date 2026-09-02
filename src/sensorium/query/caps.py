"""Capability declarations (spec §5.2), read one way by every command.

A format-4 trace says what its recorder produces. Before format 4 nothing
was declared and only the Python recorder existed, so an absent key meant
"older": the sentence for it says "predates". On a format-4 trace an absent
record is a declaration, and the sentence says so -- never "older", never a
zero.
"""


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
