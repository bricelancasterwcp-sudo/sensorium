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
