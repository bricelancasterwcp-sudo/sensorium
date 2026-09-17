"""An `Outcome` as the model reads it: a header, the streams, a cap.

THE HEADER IS THE FIRST LINE, ALWAYS (D19). A model branches on it
before it reads a word of prose, exactly as the debugging skills teach
it to branch on `$?`, so the words are `exit.MEANING`'s and not a second
copy of them (P3): a status whose sentence is reworded takes its header
with it, and a status that MOVED takes its sentence.

Two statuses are not the four-way contract and say so. `record` is the
CLI's `run`, whose exit is the recorded command's own -- an `exit 2`
there means the target exited 2, or that recording was refused and there
is no trace, never "the call is wrong". A child killed by a signal has
no status at all, only the signal, and reads the same on every tool.
A call that produced no exit (a timeout, a cancel, a spawn that never
happened) reads `no answer:` and the cause, because there is no number
to report and inventing one would be a lie a model acts on.

STDERR IS ALWAYS LABELLED (P4, amending D20). The spec labelled it only
when stdout was non-empty; two corpus refusals print to stderr alone,
and an unlabelled body cannot be attributed to a stream by a client that
must split the text back into `(stdout, stderr, exit)`. The label is a
line of its own, which costs one thing and one only: a stdout that
lacked its trailing newline gains one before the label, so a client
cannot reassemble THAT case byte-exactly. It is documented in `text_of`
and it is the whole of the loss.

THE CAP KEEPS A HEAD AND A TAIL (D24), not a head. `diff` and `refocus`
print their verdict and their drill-in commands LAST; a model handed
only the head of a DIVERGED answer has the exit and not the fork. Both
ends are cut back to a line boundary so neither half starts or stops
mid-record, and the marker between them names the fields this tool can
be narrowed by -- the cut is ours and named, which is the reason
`--max-output` sits under the client's own silent cap at all (D23).

This module renders. `audit.py` records; the two never import each
other, and the server is what calls both.
"""
from __future__ import annotations

import signal

from sensorium import exit as ex
from sensorium.mcp.child import Outcome
from sensorium.mcp.schema import Rejection
from sensorium.mcp.tools import Tool, narrowing_fields

#: The line that separates stdout from stderr. A line of its own, so a
#: client can split on it (P4); the corpus client does exactly that.
STDERR_LABEL = "--- stderr ---"

#: The bytes kept from the END of an over-long body, when the limit is
#: big enough to spare them (D24).
KEEP_TAIL = 4096

#: `record`'s header tail: `run`'s exit is the target's own.
_RECORDED = ("the recorded command's own status (2 and no trace when "
             "recording was refused)")

#: ...and the tail for an exit that is neither the contract's nor a
#: signal's. Never expected; named rather than rendered as an answer.
_OFF_CONTRACT = "an exit outside the query contract"


def header(tool: Tool, o: Outcome) -> str:
    """The first line of every result: what happened, in one sentence."""
    if o.exit is None:
        return f"no answer: {o.cause or 'unknown'}"
    if o.exit < 0:
        return f"exit {o.exit}: killed by {signal.Signals(-o.exit).name}"
    if tool.schema.command == "run":                       # the tool `record`
        return f"exit {o.exit}: {_RECORDED}"
    return f"exit {o.exit}: {ex.MEANING.get(o.exit, _OFF_CONTRACT)}"


def text_of(tool: Tool, o: Outcome) -> str:
    """`header`, then stdout, then stderr under `STDERR_LABEL`.

    Nothing is appended that the streams did not carry, with one
    exception: a non-empty stderr whose preceding text does not end in a
    newline gets one, so the label always starts a line. That is the
    single case a client cannot split back byte-exactly -- it recovers
    the streams, not the missing final newline of a ragged stdout.
    """
    text = header(tool, o) + "\n" + o.stdout
    if o.stderr:
        if not text.endswith("\n"):
            text += "\n"
        text += STDERR_LABEL + "\n" + o.stderr
    return text


def cap(text: str, limit: int, narrowing: tuple[str, ...]
        ) -> tuple[str, bool, int, int]:
    """`(text, truncated, omitted_lines, omitted_bytes)`, head and tail.

    The header line is never cut: the cap applies to everything after
    the first newline, so a limit smaller than the header still leaves a
    result a model can branch on. Both kept halves end and begin on a
    line boundary -- the head back to its last newline, the tail forward
    past its first -- and the marker line between them is not counted
    against the limit, being the cap's own sentence rather than the
    child's output.
    """
    nl = text.find("\n")
    head_line, body = (text, "") if nl < 0 else (text[:nl], text[nl + 1:])
    raw = body.encode("utf-8")
    if len(raw) <= limit:
        return text, False, 0, 0
    keep_tail = min(KEEP_TAIL, limit // 4)
    keep_head = limit - keep_tail
    head = raw[:keep_head]
    head = head[:head.rfind(b"\n") + 1] if b"\n" in head else head
    tail = raw[-keep_tail:]
    tail = tail[tail.find(b"\n") + 1:] if b"\n" in tail else tail
    omitted = raw[len(head):len(raw) - len(tail)]
    lines = omitted.count(b"\n")
    narrow = ", ".join(narrowing) if narrowing else "nothing on this tool"
    marker = (f"[... {lines:,} lines ({len(omitted):,} bytes) omitted; "
              f"narrow with: {narrow} ...]\n")
    out = head.decode("utf-8", "replace") + marker + tail.decode("utf-8",
                                                                 "replace")
    return head_line + "\n" + out, True, lines, len(omitted)


def call_result(tool: Tool, o: Outcome, limit: int, structured: bool,
                modern: bool) -> tuple[dict, bool]:
    """The `tools/call` result for one outcome, and whether it was cut.

    `isError` is true exactly when the exit is 2 or there is no exit
    (D22): 2 is the call the model should repair itself, which is what
    the protocol says the flag is for, while 1 and 3 are answers ABOUT
    the trace and a signal is a death, not a misuse. The key is omitted
    rather than sent false -- absent is the protocol's default.

    `_meta` is never added here (R1): the server owns the serverInfo it
    stamps on every modern result, and two hands writing one key is how
    they disagree.
    """
    text, truncated, _lines, _nbytes = cap(text_of(tool, o), limit,
                                           narrowing_fields(tool))
    out: dict = {"content": [{"type": "text", "text": text}]}
    if structured:
        out["structuredContent"] = {"exit": o.exit}
    if o.exit == 2 or o.exit is None:
        out["isError"] = True
    if modern:
        out["resultType"] = "complete"
    return out, truncated


def rejection_result(r: Rejection, structured: bool, modern: bool) -> dict:
    """A refused call, as a RESULT rather than a protocol error (P30).

    Both revisions reserve `-32602` for unknown tools and malformed
    requests and route argument-validation failures through `isError`,
    which is the channel the model sees and repairs from -- naming the
    fields in an error the client swallows would defeat the point of
    naming them. So it is an ordinary exit-2 answer, in the same words
    an exit 2 from the CLI would have used, with the rejection's own
    message under it.
    """
    text = f"exit {ex.BAD_CALL}: {ex.MEANING[ex.BAD_CALL]}\n{r.message}"
    out: dict = {"content": [{"type": "text", "text": text}]}
    if structured:
        out["structuredContent"] = {"exit": ex.BAD_CALL}
    out["isError"] = True
    if modern:
        out["resultType"] = "complete"
    return out
