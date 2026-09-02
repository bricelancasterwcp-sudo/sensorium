"""Capability declarations (spec §5.2), read one way by every command.

A format-4 trace says what its recorder produces. Before format 4 nothing
was declared and only the Python recorder existed, so an absent key meant
"older": the sentence for it says "predates". On a format-4 trace an absent
record is a declaration, and the sentence says so -- never "older", never a
zero.
"""


def witness_gap(trace, cap: str, keys: str) -> str:
    """Why a record is absent, in the words the trace itself supports.

    Only a declaration of exactly False licenses the "declares ... not
    witnessed" sentence -- a caller reaches here because a witness key is
    physically missing, and on a well-formed trace that happens for a
    declared-False capability or for one that predates declarations
    (`declares` is None) alike. `declares(cap) is True` with the key still
    missing is neither of those: the trace's own record disagrees with
    itself, and the honest sentence is the same "no explanation on file"
    one `None` gets -- never the declared-False sentence, which would
    assert `capabilities.<cap>: false` about a trace that says true.
    """
    if trace.declares(cap) is False:
        return (f"recorder {trace.recorder} declares {cap} not witnessed "
                f"(capabilities.{cap}: false), so there is no {keys} record to "
                "read; absence of the record is not a record of absence")
    return (f"predates the recorder's {keys} bookkeeping, so absence of "
            "the record is not a record of absence")


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
