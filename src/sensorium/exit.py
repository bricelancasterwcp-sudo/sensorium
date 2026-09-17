"""The query CLI's exit status is the caller's next action, not a health code.

0 the question was answered affirmatively: the trace says yes.
1 the question was answered negatively: the trace says no, or none.
2 the call is wrong: edit the command and ask again.
3 the trace cannot settle it: change the recording and re-record.
"""

ANSWERED = 0
"""The trace answered affirmatively -- what was asked for is in the output."""

NEGATIVE = 1
"""The trace answered negatively -- no match, no frame, no exception, none."""

BAD_CALL = 2
"""The call is wrong -- a bad flag, a bad ref, an unreadable trace."""

UNSETTLED = 3
"""The trace cannot settle the question -- record again with what it lacks."""

#: Each status as the sentence a caller is told, for a surface
#: that hands back a status instead of printing this module's
#: docstring: an MCP client shows the four words, never the
#: convention. Keyed by the constants, so a status that moved
#: takes its sentence with it.
MEANING = {
    ANSWERED: "the trace answered affirmatively",
    NEGATIVE: "the trace answered negatively -- no match, no frame, "
              "no exception, none",
    BAD_CALL: "the call is wrong -- fix the arguments and ask again",
    UNSETTLED: "the trace cannot settle it -- change the recording "
               "and re-record",
}
