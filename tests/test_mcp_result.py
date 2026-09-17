"""What the model reads: the header, the stderr label, and the cap.

`result.py` is the only place an `Outcome` becomes prose, so these tests
are about STRINGS and dict keys -- never about processes, which is
`test_mcp_child.py`'s subject, and never about files, which is
`test_mcp_audit.py`'s. The header is the line a model branches on before
it reads anything else (D19/P3), so each of its five forms is pinned
against `exit.MEANING` rather than against a retyped sentence: a status
whose wording moves must take the header with it.

The cap's numbers are worked out in the test rather than recomputed from
the implementation (D23/D24). A 200-line body of exactly 1000-byte lines
under a 65536-byte limit keeps 61 head lines and 4 tail lines and omits
135 -- arithmetic a reader can check by hand, which is the point: a cap
that agreed with its own off-by-one would pass a test that asked the
implementation what it thought.

PRE-REGISTERED MUTATIONS (task 4, step 6), each with the test that
catches it:

* `cap` keeps the head only (drop the tail, emit `head + marker`) ->
  `test_cap_keeps_head_and_tail_on_line_boundaries`. The last four lines
  of the body are gone, so the tail clause fails -- and with them the
  `diff`/`refocus` verdict D24 exists to preserve.
* `isError` on exit 3 as well as 2 (`o.exit in (2, 3)`) ->
  `test_call_result_is_error_iff_exit_two_or_none`. Exit 3 is an answer
  about the trace, not a broken call.
* the stderr label only when stdout is non-empty (D20's original rule,
  before P4) -> `test_text_of_labels_stderr_whenever_non_empty`. An
  argparse refusal prints to stderr alone and would arrive unlabelled,
  which the corpus client cannot split back.
* `_signal_name` without its guard (a bare `signal.Signals(n).name`) ->
  `test_header_for_a_real_time_signal_does_not_raise`. `Signals` names
  1-34 and 64 only; a child killed by `SIGRTMIN+1` raises `ValueError`
  out of `header`, and the whole `tools/call` fails to render (R11).
* `keep_tail` without its `max(1, ...)` floor ->
  `test_cap_with_a_tiny_limit_still_truncates`. Under a limit of 4,
  `limit // 4` is 0 and `raw[-0:]` is the WHOLE buffer: the cap emits
  everything it claimed to cut, with the marker glued mid-line.
* re-add `structuredContent` to `call_result` (`out["structuredContent"]
  = {"exit": o.exit}`) -> `test_call_result_never_carries_structured_
  content_and_result_type_only_when_modern` (task 12, R18). The deploy
  target passes the model a result's structured content INSTEAD of its
  text, so a server that sends both sends the exit and hides the answer.
"""
import re
import signal

import pytest

from sensorium import exit as ex
from sensorium.mcp import result, schema, tools
from sensorium.mcp.child import Outcome

#: The tool table, built once: `table(True)` so `record` is in it.
TABLE = tools.table(True)

#: The timeout cause `child.run` composes, verbatim (`{:g}`, so `3.0`
#: renders `3`).
TIMED_OUT = "timed out after 3 s (server flag --timeout / --run-timeout)"


def _o(status, stdout="", stderr="", cause=None, **kw):
    return Outcome(exit=status, stdout=stdout, stderr=stderr, cause=cause,
                   ms=7, **kw)


def _marker_re(narrowing):
    """The H3 regex, built from a narrowing tuple the way §9's row and
    Task 9's cells build it -- from the code's own `narrowing_fields`,
    never from a retyped list."""
    return re.compile(r"^\[\.\.\. [\d,]+ lines \([\d,]+ bytes\) omitted; "
                      r"narrow with: " + re.escape(", ".join(narrowing))
                      + r" \.\.\.\]$")


# -- the header (D19, P3, P10) ---------------------------------------------
def test_header_for_each_query_exit():
    """The four contract statuses say `exit.MEANING`'s sentence; a signal
    says which signal; anything else is named as off-contract rather than
    dressed up as an answer."""
    tool = TABLE["grep"]
    for status, sentence in ex.MEANING.items():
        assert result.header(tool, _o(status)) == f"exit {status}: {sentence}"
    assert result.header(tool, _o(0)) == ("exit 0: the trace answered "
                                          "affirmatively")
    assert result.header(tool, _o(-signal.SIGTERM)) == ("exit -15: killed by "
                                                        "SIGTERM")
    assert result.header(tool, _o(7)) == ("exit 7: an exit outside the query "
                                          "contract")


def test_header_for_record():
    """`record` is the CLI's `run`: its exit is the TARGET's, not the
    four-way contract, so it never borrows a MEANING sentence."""
    tool = TABLE["record"]
    tail = ("the recorded command's own status (2 and no trace when "
            "recording was refused)")
    assert result.header(tool, _o(0)) == f"exit 0: {tail}"
    assert result.header(tool, _o(2)) == f"exit 2: {tail}"
    assert result.header(tool, _o(42)) == f"exit 42: {tail}"
    assert ex.MEANING[2] not in result.header(tool, _o(2))
    # ...but a signal reads the same on every tool: a killed child has no
    # status of its own to report.
    assert result.header(tool, _o(-signal.SIGKILL)) == ("exit -9: killed by "
                                                        "SIGKILL")


def test_header_for_a_real_time_signal_does_not_raise():
    """R11. `signal.Signals` names 1-34 and 64; `WTERMSIG` on Linux
    reaches 64, so 35 and 40 are statuses a real child can come back
    with. A header that raised on one would take the whole call down."""
    for tool in (TABLE["grep"], TABLE["record"]):
        assert result.header(tool, _o(-35)) == "exit -35: killed by signal 35"
        assert result.header(tool, _o(-40)) == "exit -40: killed by signal 40"
        # the named ones are unchanged at either end of the range
        assert result.header(tool, _o(-1)) == "exit -1: killed by SIGHUP"
        assert result.header(tool, _o(-64)) == "exit -64: killed by SIGRTMAX"
    # ...and it renders all the way out, not just in `header`
    d, _ = result.call_result(TABLE["grep"], _o(-35), 65536, True)
    assert d["content"][0]["text"] == "exit -35: killed by signal 35\n"


def test_header_for_no_answer():
    """No exit was PRODUCED, so there is no status to render: the cause
    stands in its place, whatever the cause was."""
    tool = TABLE["grep"]
    timed = _o(None, cause=TIMED_OUT, timed_out=True)
    assert result.header(tool, timed) == f"no answer: {TIMED_OUT}"
    cancelled = _o(None, cause="cancelled", cancelled=True)
    assert result.header(tool, cancelled) == "no answer: cancelled"
    spawn = _o(None, cause="[Errno 2] No such file or directory: 'python9'")
    assert result.header(tool, spawn) == ("no answer: [Errno 2] No such file "
                                          "or directory: 'python9'")
    assert result.header(tool, _o(None)) == "no answer: unknown"


# -- the stderr label (P4, R10) --------------------------------------------
def test_text_of_labels_stderr_whenever_non_empty():
    """P4 amends D20: the label appears whenever stderr is non-empty,
    stdout empty or not, so the corpus client can always attribute a body
    to a stream."""
    tool = TABLE["grep"]
    head = f"exit 1: {ex.MEANING[1]}"

    # stdout empty (an argparse refusal): header, label, stderr.
    only_err = result.text_of(tool, _o(1, "", "error: no trace matches\n"))
    assert only_err == (f"{head}\n{result.STDERR_LABEL}\n"
                        "error: no trace matches\n")

    # both: header, stdout, label, stderr.
    both = result.text_of(tool, _o(1, "a line\n", "a warning\n"))
    assert both == (f"{head}\na line\n{result.STDERR_LABEL}\na warning\n")

    # stderr empty: no label at all, and no trailing newline invented.
    assert result.text_of(tool, _o(1, "a line\n")) == f"{head}\na line\n"
    assert result.text_of(tool, _o(1, "a line")) == f"{head}\na line"
    assert result.text_of(tool, _o(1)) == f"{head}\n"

    # the one case a client cannot split back byte-exactly: a stdout that
    # lacked its trailing newline gains one, so the label starts a line.
    ragged = result.text_of(tool, _o(1, "no newline", "boom\n"))
    assert ragged == f"{head}\nno newline\n{result.STDERR_LABEL}\nboom\n"
    assert f"\n{result.STDERR_LABEL}\n" in ragged


# -- the cap (D23, D24, P28) -----------------------------------------------
def test_cap_keeps_head_and_tail_on_line_boundaries():
    """200 lines of exactly 1000 bytes under a 65536-byte limit.

    keep_tail = min(4096, 16384) = 4096 and keep_head = 61440, so the head
    cuts back to line 60's newline (61 lines, 61000 bytes) and the tail
    forward to line 196's start (4 lines, 4000 bytes): 135 lines and
    135000 bytes omitted, and 61 + 135 + 4 = 200.
    """
    limit = 65536
    body = "".join(f"{i:04d}" + "x" * 995 + "\n" for i in range(200))
    assert len(body.encode()) == 200_000
    head_line = f"exit 0: {ex.MEANING[0]}"
    narrowing = tools.narrowing_fields(TABLE["tree"])
    assert narrowing == ("depth", "limit", "around")     # P28's order

    text, truncated, lines, nbytes = result.cap(
        head_line + "\n" + body, limit, narrowing)

    assert truncated is True
    assert (lines, nbytes) == (135, 135_000)
    first, rest = text.split("\n", 1)
    assert first == head_line                       # the header, intact
    parts = rest.split("\n")
    marker = [ln for ln in parts if ln.startswith("[...")]
    assert len(marker) == 1
    assert _marker_re(narrowing).match(marker[0]), marker[0]
    assert marker[0] == ("[... 135 lines (135,000 bytes) omitted; "
                         "narrow with: depth, limit, around ...]")
    # the invariant: the body, minus the marker line, is inside the limit
    without = rest.replace(marker[0] + "\n", "")
    assert len(without.encode()) <= limit
    assert len(without.encode()) == 65_000
    kept_head, kept_tail = without.split("0196", 1)
    assert kept_head.startswith("0000") and kept_head.endswith("\n")
    assert kept_head.count("\n") == 61              # head ends on a boundary
    assert without.endswith("0199" + "x" * 995 + "\n")
    assert ("0196" + kept_tail).count("\n") == 4    # tail starts on one
    assert "0061" not in without and "0195" not in without


def test_cap_never_cuts_the_header_line():
    """The limit is 16 bytes and the header is 40: the header still
    arrives whole, because the cap applies to the text AFTER it."""
    head_line = f"exit 0: {ex.MEANING[0]}"
    assert len(head_line.encode()) > 16
    text, truncated, lines, nbytes = result.cap(
        head_line + "\n" + "line\n" * 20, 16, ("limit",))
    assert truncated is True
    assert text.split("\n")[0] == head_line
    assert text.startswith(head_line + "\nline\nline\n[... ")
    assert (lines, nbytes) == (18, 90)


def test_cap_with_a_tiny_limit_still_truncates():
    """A limit below 4 is the case `limit // 4 == 0` broke: `raw[-0:]` is
    the whole buffer, so the "cap" re-emitted every byte it had just
    reported as omitted, with the marker glued onto a partial line.

    With the floor, limit 1 gives keep_tail 1 and keep_head 0: the head
    is empty, the tail's single byte is the body's last newline and is
    consumed by the forward cut, so all 100 bytes and all 20 lines are
    omitted and the body is the marker line alone -- 0 bytes of child
    output under a 1-byte limit.
    """
    head_line = "exit 0: fine"
    text, truncated, lines, nbytes = result.cap(
        head_line + "\n" + "line\n" * 20, 1, ("limit",))

    assert truncated is True
    assert (lines, nbytes) == (20, 100)          # every byte accounted for
    assert text == (head_line + "\n[... 20 lines (100 bytes) omitted; "
                    "narrow with: limit ...]\n")
    body = text.split("\n", 1)[1]
    marker_line = body.splitlines()[0]
    # the brief's invariant, at its tightest: nothing but the marker
    assert len(body.replace(marker_line + "\n", "").encode()) == 0
    assert body == marker_line + "\n"            # no child output survived


def test_cap_under_limit_is_identity():
    """Nothing is added to a text that fits -- not a marker, not a
    newline -- and a text with no newline at all has an empty body."""
    text = "exit 0: fine\nsmall\n"
    assert result.cap(text, 65536, ("limit",)) == (text, False, 0, 0)
    assert result.cap("header only", 65536, ()) == ("header only", False, 0, 0)
    assert result.cap("", 65536, ()) == ("", False, 0, 0)


def test_cap_marker_names_nothing_for_runs():
    """`runs` has no narrowing field, and the marker says so rather than
    printing an empty list after `narrow with:`."""
    narrowing = tools.narrowing_fields(TABLE["runs"])
    assert narrowing == ()
    text, truncated, _lines, _nbytes = result.cap(
        "exit 0: fine\n" + "line\n" * 20, 16, narrowing)
    assert truncated is True
    marker = [ln for ln in text.split("\n") if ln.startswith("[...")]
    assert len(marker) == 1
    assert marker[0] == ("[... 18 lines (90 bytes) omitted; narrow with: "
                         "nothing on this tool ...]")


# -- the tools/call result dict (D21, D22, R1) -----------------------------
def test_call_result_is_error_iff_exit_two_or_none():
    """2 is the call the model should repair; 1 and 3 are answers about
    the trace; a signal is not a bad call either. No exit at all is."""
    tool = TABLE["grep"]
    for status in (0, 1, 3, -15):
        d, _ = result.call_result(tool, _o(status), 65536, True)
        assert "isError" not in d, status
    for o in (_o(2), _o(None, cause="cancelled", cancelled=True),
              _o(None, cause=TIMED_OUT, timed_out=True)):
        d, _ = result.call_result(tool, o, 65536, True)
        assert d["isError"] is True


def test_call_result_never_carries_structured_content_and_result_type_only_when_modern():  # noqa: E501 - the name is the assertion
    """R18: the exit rides the header line and nowhere else.

    The deploy target (Claude Code 2.1.258) passes the model a result's
    `structuredContent` INSTEAD of its text whenever one is present, so
    a `{"exit": N}` beside the answer is not a second copy of the exit:
    it is what the model reads in place of the answer. No revision and
    no exit gets one. `resultType` is still modern-only, and the `_meta`
    the server alone adds (R1) is on none of them.
    """
    tool = TABLE["grep"]
    o = _o(1, "a line\n", "a warning\n")
    text = result.text_of(tool, o)

    plain, truncated = result.call_result(tool, o, 65536, False)
    assert truncated is False
    assert plain == {"content": [{"type": "text", "text": text}]}

    modern, _ = result.call_result(tool, o, 65536, True)
    assert set(modern) == {"content", "resultType"}
    assert modern["resultType"] == "complete"
    assert "_meta" not in modern

    # every exit the four-way contract has, plus a signal and no answer
    # at all, on both eras: none of them carries the key.
    for status in (0, 1, 2, 3, -15, None):
        for is_modern in (False, True):
            d, _ = result.call_result(tool, _o(status, cause="cancelled"),
                                      65536, is_modern)
            assert "structuredContent" not in d, (status, is_modern)

    # ...and `truncated` is the cap's, reported back to the caller that
    # writes the audit line.
    long, cut = result.call_result(tool, _o(0, "line\n" * 20), 16, True)
    assert cut is True
    assert "[... " in long["content"][0]["text"]


# -- a rejected call is a result, not a protocol error (P30) ---------------
def test_rejection_result_is_an_is_error_exit_two_carrying_the_message():
    tool = TABLE["grep"]
    with pytest.raises(schema.Rejection) as caught:
        tools.command_argv(tool, {"regex": "x"})
    r = caught.value

    d = result.rejection_result(r, True)

    assert d["isError"] is True
    assert "structuredContent" not in d          # R18, as for every result
    assert d["resultType"] == "complete"
    assert set(d) == {"content", "isError", "resultType"}
    assert "_meta" not in d
    text = d["content"][0]["text"]
    assert text == f"exit 2: {ex.MEANING[2]}\n{r.message}"
    assert text.startswith("exit 2: the call is wrong -- fix the arguments "
                           "and ask again\nunknown field 'regex' for grep; "
                           "fields: ")

    legacy = result.rejection_result(r, False)
    assert set(legacy) == {"content", "isError"}     # isError is not optional
