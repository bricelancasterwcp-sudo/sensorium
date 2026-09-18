#!/usr/bin/env python3
"""E17's DECISION layer: §9's eight rows, as pure functions.

Split from `e17.py` on the seam E16's three parts found: everything here is
a function over rows somebody could type by hand -- no subprocess, no
clock, no knowledge of where this box keeps its files. That is what lets
`tests/test_acceptance_e17_cells.py` exercise every verdict, every STOP
included, before the measurement, which is made ONCE. Self-contained by
P14: nothing under `tests/acceptance_e16/` is imported.

A cell answers `{word, read, detail}`. The word is `PASS`, `STOP` or
`dropped`, and for the two rows §9 never gates, `reported` (H7) and
`measured` (latency). `dropped` is the answer whenever an input is `None`,
which is what a phase that did not run leaves behind: the one thing this
instrument must not be able to do is report a hole as a pass. A `0` is a
count that was taken. Each clause is ONE sentence stating what was read --
the same sentence on either side of the verdict, so a PASS and a STOP are
one reading with a different word and the number is visible either way.

STOP AS INSTRUMENT is a finding about the MEASUREMENT, not the server: a
`--compare-cli` report with no `mcp_differences` key (nothing was
compared), a conformance run that skipped (the SDK is absent), an H3 whose
CLI answer already fit under the cap (the cap never fired), an H5 with too
few pings or a group that was never alive (a cancel cannot pass by
absence), an H6 question whose own expectations failed (the case was never
in a state to count anything).
"""

from __future__ import annotations

import re

#: §9's eight rows in its own order (`latency` is the eighth: `—` in both
#: columns, never gated), and their names verbatim from its first column.
CELLS = ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "latency")
CELL_TITLES = {"H1": "H1 parity", "H2": "H2 conformance", "H3": "H3 the cap",
               "H4": "H4 the gate", "H5": "H5 liveness", "H6": "H6 secrecy",
               "H7": "H7 the deploy target", "latency": "latency"}

#: §9's PASS/STOP column for the seven H rows, copied from the record's §1
#: table. The cells test holds every clause by EQUALITY against the row's
#: own cell: a substring check cannot see a clause cut short.
RULES = {
    "H1": {"PASS": "0 failures; every read-only question byte-identical and "
                   "exit-identical; skipped set equals Task 0's locked "
                   "not-a-tool list exactly",
           "STOP": "any failure, any difference, any skip outside the list "
                   "— named per question"},
    "H2": {"PASS": "all of a–d", "STOP": "any"},
    "H3": {"PASS": "text ≤ 65536 + marker; marker names `depth, limit, "
                   "around`; head and tail both non-empty; audit "
                   "`truncated: true`", "STOP": "any"},
    "H4": {"PASS": "all", "STOP": "any"},
    "H5": {"PASS": "all", "STOP": "any"},
    "H6": {"PASS": "0 occurrences in the three places; H6b marker present, "
                   "value absent from the audit", "STOP": "any occurrence"},
    "H7": {"PASS": "the session used ≥ 3 sensorium tools and named the "
                   "swallowing frame the case's `truth` names",
           "STOP": "reported either way; a STOP names what the model did "
                   "instead"},
}

#: The not-a-tool list, locked at Task 0: three questions, all in one case.
#: `via_cli` reports them as `<case>/<id>`, which is what H1 compares.
VIA_CLI_CASE = "redact_retrofit"
LOCKED_VIA_CLI = ("what-would-the-retrofit-take", "the-retrofit-rewrites-once",
                  "a-second-pass-finds-nothing")
LOCKED_VIA_CLI_IDS = tuple(f"{VIA_CLI_CASE}/{q}" for q in LOCKED_VIA_CLI)
#: `(cases, questions)` at `0385d80`, re-counted from `load_cases()` by the
#: cells test so the lock and the corpus cannot drift apart unnoticed.
LOCKED_CENSUS = (115, 253)
#: The subject: this branch's Python package, asserted by the preflight.
EXPECTED_VERSION = "0.18.0"
#: The nine a client is always offered, and the two `--allow-run` adds.
NINE = ("runs", "info", "tree", "frame", "grep", "exceptions", "flow",
        "watch", "diff")
ELEVEN = NINE + ("refocus", "record")
#: H3's bound and H2's floor.
CAP_BYTES = 65536
H2_MIN_PASSED = 9
#: H5's clauses, in pings and seconds. `MIN_PINGS` is §1's own "at least 8
#: pings are sent before the cancel": three pings over five seconds is a
#: client that was not polling, and "every ping answered under a second"
#: would then be a claim about almost nothing.
MIN_PINGS = 8
PING_CEILING = 1.0
CANCEL_GRACE = 2.0
TIMEOUT_ANSWER = 6.0
TIMEOUT_GONE = 5.0
TIMEOUT_HEADER = ("no answer: timed out after 3 s "
                  "(server flag --timeout / --run-timeout)")
#: What the instrument writes as the header when the timeout arm produced
#: no result at all -- a STOP, never a hole: the arm ran and nothing came
#: back, which is a fact about the server.
NO_TIMEOUT_RESULT = "<no result arrived within 6 s of the send>"
#: H7's readings: §9's "≥ 3 sensorium tools", and the frame
#: `corpus/silent_swallow`'s own `truth` names as the swallower.
H7_MIN_TOOLS = 3
H7_TRUTH_FRAME = "load_all"
#: A run id as both recorders mint it, so H4 and H5 can count the traces a
#: `runs` answer lists.
RUN_ID = re.compile(r"\b\d{8}-\d{6}-[0-9a-f]{6}\b")
#: The three places §9 counts the token in, and what each key says.
H6_PLACES = (("in_texts", "the result texts"), ("in_jsonl", "`mcp.jsonl`"),
             ("in_stderr", "the stderr transcript"))
#: The row `e17_gather._proc_check` adds to H6's `checks`: §9's precondition
#: that the SERVER's own environment holds the token. It rides in `checks`
#: so that a failure reaches H6's STOP-AS-INSTRUMENT sentence, and it is
#: counted APART from the case's questions in the detail -- `checks_run`
#: must not read as one more question than `secret_in_env` has.
PROC_CHECK = "the server's own environment holds the token"


def marker_re(narrowing: tuple[str, ...]) -> re.Pattern:
    """The capped answer's marker line for a tool with these narrowing
    fields. A FUNCTION so the cells test can build the same regex from
    `tools.narrowing_fields(tools.table(True)["tree"])`: §1 locks the
    `narrow with:` list as prose, and a tool that gained or lost a field
    would otherwise leave lock and code disagreeing, unnoticed."""
    return re.compile(r"^\[\.\.\. \d[\d,]* lines \(\d[\d,]* bytes\) "
                      r"omitted; narrow with: " + ", ".join(narrowing)
                      + r" \.\.\.\]$")


#: `tree`'s, which is what §1 spells out and H3 measures.
MARKER_RE = marker_re(("depth", "limit", "around"))


def _dropped(why: str, detail: dict | None = None) -> dict:
    return {"word": "dropped", "read": why, "detail": detail or {}}


def _instrument(why: str) -> dict:
    return {"word": "STOP", "read": f"STOP as instrument: {why}",
            "detail": {"instrument": why}}


def _missing(**named) -> list[str]:
    return sorted(name for name, value in named.items() if value is None)


def _verdict(rows: list[tuple[str, bool, str]], detail: dict) -> dict:
    """PASS iff every clause held; a STOP names the ones that did not, in
    the order §1 states them."""
    bad = [row for row in rows if not row[1]]
    return {"word": "PASS" if not bad else "STOP",
            "read": "; ".join(row[2] for row in (bad or rows)),
            "detail": {**detail, "clauses": [
                {"clause": name, "word": "PASS" if ok else "STOP",
                 "read": read} for name, ok, read in rows]}}


def _named(items, cap: int = 3) -> str:
    shown = ", ".join(str(i) for i in items[:cap])
    return shown + (f", and {len(items) - cap} more" if len(items) > cap
                    else "")


#: Claude Code prefixes this server's tools as `mcp__<server>__<name>`.
_SENSORIUM_PREFIX = "mcp__sensorium__"


def _sensorium_tools(used) -> list[str]:
    """This server's tools in `used`, first-seen order, prefix stripped.

    A name is sensorium if it is one of the eleven, or the host prefix
    plus one of the eleven. Host tools (Skill, ToolSearch, ...) are
    dropped so H7 cannot count them as ours.
    """
    known = set(ELEVEN)
    seen: list[str] = []
    for name in used:
        raw = str(name)
        if raw.startswith(_SENSORIUM_PREFIX):
            raw = raw[len(_SENSORIUM_PREFIX):]
        if raw in known and raw not in seen:
            seen.append(raw)
    return seen


# -- H1: parity -------------------------------------------------------------
def h1(doc: dict | None, dry: bool = False) -> dict:
    """§9's H1, off `run_corpus.py --via mcp --compare-cli --json`. `dry`
    relaxes the census and the `via_cli` clauses and NOTHING else -- the
    rehearsal runs two cases, so those two are claims about a corpus it did
    not ask -- and the `read` says which two went unread.
    """
    if doc is None:
        return _dropped("the corpus run left no JSON report to read")
    if doc.get("via") != "mcp":
        return _instrument(f"this report is not a `--via mcp` run "
                           f"(via = {doc.get('via')!r}): no question "
                           f"reached a server")
    diffs = doc.get("mcp_differences")
    if diffs is None:
        return _instrument("the report carries no `mcp_differences` key: "
                           "`--compare-cli` was not honoured, so no "
                           "read-only question was compared at all")
    fails, errs = doc.get("failures") or [], doc.get("errors") or []
    skips, why = doc.get("skipped") or [], doc.get("exit_reason")
    via, seen = list(doc.get("via_cli", [])), (doc.get("cases"),
                                               doc.get("questions"))
    extra = [q for q in via if q not in LOCKED_VIA_CLI_IDS]
    absent = [q for q in LOCKED_VIA_CLI_IDS if q not in via]
    rows = [
        ("failures", not fails,
         f"{len(fails)} failure(s)" + (f": {_named(fails)}" if fails else "")),
        ("errors", not errs,
         f"{len(errs)} harness error(s)" + (f": {_named(errs)}" if errs
                                            else "")),
        ("exit_reason", why is None, f"exit_reason: {why}" if why
         else "no `exit_reason`"),
        ("skipped", not skips,
         f"{len(skips)} case(s) skipped" + (f": {_named(skips)}" if skips
                                            else "")),
        ("differences", diffs == [],
         f"{len(diffs)} MCP/CLI difference(s) over the read-only questions"
         + (": " + _named([f"{d['case']}/{d['id']} {d['field']} "
                           f"mcp={d['mcp']!r} cli={d['cli']!r}"
                           for d in diffs]) if diffs else "")),
    ]
    if not dry:
        rows += [
            ("via_cli", sorted(via) == sorted(LOCKED_VIA_CLI_IDS),
             f"`via_cli` holds {len(via)} question(s) against the locked "
             f"{len(LOCKED_VIA_CLI_IDS)}"
             + (f"; extra {_named(extra, 9)}" if extra else "")
             + (f"; missing {_named(absent, 9)}" if absent else "")),
            ("census", seen == LOCKED_CENSUS,
             f"{seen[0]} cases / {seen[1]} questions, against the locked "
             f"{LOCKED_CENSUS[0]} / {LOCKED_CENSUS[1]}"),
        ]
    out = _verdict(rows, {"census": list(seen), "via_cli": via,
                          "differences": diffs, "dry": dry})
    if dry:
        out["read"] += ("; DRY rehearsal: the census and `via_cli` clauses "
                        "were NOT read -- this was a subset of the corpus")
    return out


# -- H2: conformance --------------------------------------------------------
def h2(rc: int | None, passed: int | None, skipped: int | None) -> dict:
    """§9's H2: `pytest -q tests/test_mcp_conformance.py`, off its own
    summary line. A skip means the `conformance` extra is missing."""
    gone = _missing(rc=rc, passed=passed, skipped=skipped)
    if gone:
        return _dropped(f"the conformance run left no summary to parse "
                        f"({', '.join(gone)} unread)")
    if skipped:
        return _instrument(f"{skipped} conformance test(s) SKIPPED: the "
                           f"official `mcp` SDK (the `conformance` extra) "
                           f"is not in this venv, so the oracle never ran")
    return _verdict([("exit", rc == 0, f"pytest exited {rc}"),
                     ("passed", passed >= H2_MIN_PASSED,
                      f"{passed} passed, against §1's floor of "
                      f"{H2_MIN_PASSED}")],
                    {"rc": rc, "passed": passed, "skipped": skipped})


# -- H3: the cap ------------------------------------------------------------
def h3(text: str | None, cli_bytes: int | None,
       audit_last: dict | None) -> dict:
    """§9's H3, over one capped `tree` answer. The bound is measured on
    `text` after the FIRST newline with the marker line removed: §1 counts
    neither the header nor the cap's own sentence against 65536, and a
    reading that counted either would fail a cap that kept its promise.
    """
    gone = _missing(text=text, cli_bytes=cli_bytes, audit_last=audit_last)
    if gone:
        return _dropped(f"the cap call left nothing to read "
                        f"({', '.join(gone)} unread)")
    if cli_bytes <= CAP_BYTES:
        return _instrument(f"the same argv through the CLI wrote "
                           f"{cli_bytes} bytes, already under {CAP_BYTES}: "
                           f"the cap never fired and the cell measured "
                           f"nothing")
    if "\n" not in text:
        return _instrument("the result text has no second line: there is no "
                           "body to measure against the bound")
    header, body = text.split("\n", 1)
    parts = body.split("\n")
    at = [i for i, part in enumerate(parts) if MARKER_RE.match(part)]
    head = parts[:at[0]] if at else []
    tail = parts[at[0] + 1:] if at else []
    kept = "\n".join(head + tail) if at else body
    nbytes = len(kept.encode("utf-8"))
    rows = [("header", header.startswith("exit 0: "),
             f"the header line reads `{header[:60]}`"),
            ("marker", len(at) == 1,
             f"{len(at)} line(s) match §1's marker regex, which names "
             f"`depth, limit, around`")]
    if len(at) == 1:
        rows += [("bytes", nbytes <= CAP_BYTES,
                  f"{nbytes} bytes after the header with the marker line "
                  f"removed, against the {CAP_BYTES}-byte bound"),
                 ("head", any(head), f"the head is {len(head)} line(s)"),
                 ("tail", any(tail), f"the tail is {len(tail)} line(s)")]
    rows.append(("truncated", audit_last.get("truncated") is True,
                 f"the last `mcp.jsonl` line says truncated = "
                 f"{audit_last.get('truncated')!r}"))
    return _verdict(rows, {"bytes": nbytes, "cli_bytes": cli_bytes,
                           "header": header[:120], "head_lines": len(head),
                           "tail_lines": len(tail)})


# -- H4: the gate -----------------------------------------------------------
def _set_read(what: str, got, want) -> str:
    extra = sorted(set(got) - set(want))
    absent = sorted(set(want) - set(got))
    return (f"{len(got)} tools {what}" if not extra and not absent
            else f"{len(got)} tools {what}: extra {_named(extra) or 'none'}, "
                 f"missing {_named(absent) or 'none'}")


def h4(names_off, err_off, names_on, record_header, runs_text,
       exceptions_check) -> dict:
    """§9's H4: nine tools without the flag and `record` unknown, eleven
    with it, and a recording made and read back through the wire."""
    gone = _missing(names_off=names_off, names_on=names_on,
                    record_header=record_header, runs_text=runs_text,
                    exceptions_check=exceptions_check)
    if gone:
        return _dropped(f"the gate phase did not finish "
                        f"({', '.join(gone)} unread)")
    traces = sorted(set(RUN_ID.findall(runs_text)))
    err, want = err_off or {}, (-32602, "Unknown tool: record")
    return _verdict(
        [("nine", set(names_off) == set(NINE),
          _set_read("without the flag", names_off, NINE)),
         ("record-is-unknown",
          (err.get("code"), err.get("message")) == want,
          f"`tools/call record` without the flag answered "
          f"{err.get('code')!r} {err.get('message')!r}, against "
          f"-32602 'Unknown tool: record'"),
         ("eleven", set(names_on) == set(ELEVEN),
          _set_read("with `--allow-run`", names_on, ELEVEN)),
         ("record", record_header.startswith("exit 0: "),
          f"`record` answered `{record_header[:70]}`"),
         ("runs", len(traces) == 1,
          f"`runs` through the wire lists {len(traces)} trace(s)"
          + (f": {_named(traces)}" if traces else "")),
         ("exceptions", exceptions_check == [],
          "`exceptions` satisfies `what-was-dropped`" if not exceptions_check
          else f"`what-was-dropped` failed: {_named(exceptions_check)}")],
        {"names_off": list(names_off), "names_on": list(names_on),
         "traces": traces, "record_header": record_header,
         "error_off": err_off})


# -- H5: liveness -----------------------------------------------------------
def h5(pings_sent, ping_max, alive_before, group_gone_s, response_seen,
       runs_after, timeout_header, timeout_is_error, timeout_exit,
       timeout_answered_s, timeout_group_gone_s) -> dict:
    """§9's H5, both arms.

    `timeout_exit` is `None` on a PASS. The reading is R18's: the timed-out
    result's HEADER is `no answer: timed out after 3 s (server flag
    --timeout / --run-timeout)`, and `CallResult.exit` -- which the client
    parses out of that header -- is therefore `None`. So the timeout arm's
    READNESS is carried by `timeout_header`, which the instrument fills
    with `NO_TIMEOUT_RESULT` when nothing came back at all. `group_gone_s`
    is `None` when the group was still there at the deadline: a STOP, not a
    hole, since `alive_before` proves there was a group to watch.
    """
    gone = _missing(pings_sent=pings_sent, ping_max=ping_max,
                    alive_before=alive_before, response_seen=response_seen,
                    runs_after=runs_after, timeout_header=timeout_header)
    if gone:
        return _dropped(f"the liveness phase did not finish "
                        f"({', '.join(gone)} unread)")
    if pings_sent < MIN_PINGS:
        return _instrument(f"{pings_sent} ping(s) were sent before the "
                           f"cancel, under §1's floor of {MIN_PINGS}: the "
                           f"client was not polling, so 'every ping "
                           f"answered' is a claim about almost nothing")
    if alive_before is not True:
        return _instrument("`os.killpg(pgid, 0)` did not succeed before the "
                           "cancel: there was no live group, and a cancel "
                           "cannot pass by absence")
    after, answered = runs_after, timeout_answered_s
    return _verdict(
        [("pings", ping_max < PING_CEILING,
          f"{pings_sent} pings sent, the slowest answered in "
          f"{ping_max * 1000:.1f} ms (ceiling {PING_CEILING * 1000:.0f} ms)"),
         ("group-gone", group_gone_s is not None
          and group_gone_s <= CANCEL_GRACE,
          f"the child's group was gone {group_gone_s:.2f} s after the cancel"
          if group_gone_s is not None else f"the child's group was STILL "
          f"THERE {CANCEL_GRACE} s after the cancel"),
         ("no-response", response_seen is False,
          f"a response for the cancelled id arrived: {response_seen!r}"
          if response_seen else "no response for the cancelled id arrived"),
         ("runs-after", (bool(after.get("answered")),
                         after.get("traces"), after.get("incomplete"))
          == (True, 1, 1),
          f"the next `runs` answered={after.get('answered')!r}, listing "
          f"{after.get('traces')!r} trace(s), {after.get('incomplete')!r} "
          f"INCOMPLETE"),
         ("timeout-header", timeout_header == TIMEOUT_HEADER,
          f"the timeout arm's header is `{timeout_header}`"),
         ("timeout-is-error", timeout_is_error is True,
          f"the timeout result's `isError` is {timeout_is_error!r}"),
         ("timeout-exit", timeout_exit is None,
          f"the header's exit (`CallResult.exit`) is {timeout_exit!r}"),
         ("timeout-answered", answered is not None
          and answered <= TIMEOUT_ANSWER,
          f"answered {answered:.2f} s after the send (cap {TIMEOUT_ANSWER} s)"
          if answered is not None else f"no result arrived within "
          f"{TIMEOUT_ANSWER} s of the send"),
         ("timeout-group-gone", timeout_group_gone_s is not None
          and timeout_group_gone_s <= TIMEOUT_GONE,
          f"the group was gone {timeout_group_gone_s:.2f} s after the send "
          f"(cap {TIMEOUT_GONE} s)" if timeout_group_gone_s is not None
          else f"the group was STILL THERE {TIMEOUT_GONE} s after the send")],
        {"pings_sent": pings_sent, "ping_max": ping_max,
         "group_gone_s": group_gone_s, "runs_after": after,
         "timeout_answered_s": answered,
         "timeout_group_gone_s": timeout_group_gone_s})


# -- H6: secrecy ------------------------------------------------------------
def _proc_word(checks: list) -> str | None:
    """The `/proc` row's own word, or `None` when the row is not there --
    which is not the same fact as a row that passed."""
    row = next((c for c in checks if c.get("question") == PROC_CHECK), None)
    return None if row is None else ("STOP" if row.get("failures")
                                     else "PASS")


def h6(checks: list | None, counts: dict | None, h6b: dict | None) -> dict:
    """§9's H6 and H6b: the case's own expectations first, then the token's
    bytes counted in the three places. A question whose expectations failed
    is a STOP AS INSTRUMENT naming it -- the case's `expect_absent` rows
    are what prove the token was at the four value sites at all, so a count
    over a case that did not behave is a count of nothing. A file that was
    not read is `dropped` with the reason, never a 0.
    """
    gone = _missing(checks=checks, counts=counts, h6b=h6b)
    if gone:
        return _dropped(f"the secrecy phase did not finish "
                        f"({', '.join(gone)} unread)")
    failed = [c for c in checks if c.get("failures")]
    if failed:
        return _instrument(
            f"{len(failed)} question(s) of `secret_in_env` did not meet "
            f"their own expectations through the wire: "
            + _named([f"{c['question']} ({_named(c['failures'], 2)})"
                      for c in failed]))
    # `texts` and `questions` belong here with the rest. Without them an
    # absent pair made the first clause `None == None` -- a PASS over two
    # holes -- and turned the audit-lines clause into `jsonl_lines >= 0`,
    # which nothing can fail. A count nobody took is not a count.
    unread = [name for name, value in
              (("the result texts", counts.get("texts")),
               ("the case's question count", counts.get("questions")),
               ("`mcp.jsonl`", counts.get("jsonl_lines")),
               ("the stderr transcript", counts.get("stderr_bytes")),
               *((what, counts.get(key)) for key, what in H6_PLACES))
              if value is None]
    if unread:
        return _dropped(f"not read, so no count was taken: "
                        f"{', '.join(dict.fromkeys(unread))}")
    total = sum(counts[key] for key, _ in H6_PLACES)
    return _verdict(
        [("texts", counts["texts"] == counts["questions"],
          f"{counts['texts']} result text(s) counted, over the case's "
          f"{counts['questions']} question(s)"),
         ("audit-lines", counts["jsonl_lines"] >= counts["questions"],
          f"`mcp.jsonl` holds {counts['jsonl_lines']} line(s), against the "
          f"{counts['questions']} calls made"),
         ("stderr", counts["stderr_bytes"] > 0,
          f"the stderr transcript holds {counts['stderr_bytes']} byte(s)"),
         ("occurrences", total == 0,
          f"{total} occurrence(s) of the token in "
          + ", ".join(f"{counts[key]}× {what}" for key, what in H6_PLACES)),
         ("h6b-marker", h6b.get("pattern") == "<redacted>",
          f"H6b: the audit line's `arguments.pattern` is "
          f"{h6b.get('pattern')!r}"),
         ("h6b-absent", h6b.get("in_jsonl") == 0,
          f"H6b: {h6b.get('in_jsonl')!r} occurrence(s) of the token in "
          f"`mcp.jsonl` after the `grep`")],
        {"counts": counts, "h6b": h6b,
         "checks_run": len([c for c in checks
                            if c.get("question") != PROC_CHECK]),
         "proc_check": _proc_word(checks)})


# -- H7 and latency: never gated -------------------------------------------
def h7(doc: dict | None) -> dict:
    """§9's H7, `n = 1, reported not gated`. The controller runs the
    session by hand and writes `h7.json`; this reads it."""
    if doc is None:
        return _dropped("H7 not run by the controller")
    used, command = _sensorium_tools(doc.get("tools_used") or []), doc.get(
        "recorded_command")
    named, calls = doc.get("named_frame"), doc.get("sensorium_tool_calls")
    return {"word": "reported",
            "read": (f"{len(used)} sensorium tool(s) used "
                     f"({_named(used, 6) or 'none'}), "
                     f"{'≥ 3' if len(used) >= H7_MIN_TOOLS else 'fewer '
                        'than 3'}, over "
                     f"{f'{calls} sensorium call(s)' if calls is not None
                        else 'a call count that was not recorded'}; "
                     f"`record` was passed "
                     f"{command if command is not None else '(not read)'}; "
                     f"the frame the session named "
                     f"{'IS' if named is True else 'is NOT' if named is False
                        else 'was not read against'} the case's `truth` "
                     f"frame `{H7_TRUTH_FRAME}`; the deploy target opened "
                     f"with `{doc.get('handshake')}`; model "
                     f"`{doc.get('model')}` under Claude Code "
                     f"{doc.get('claude_version')}"),
            "detail": {"tools_used": used, "sensorium_tool_calls": calls,
                       "recorded_command": command,
                       "named_frame": named, "model": doc.get("model"),
                       "claude_version": doc.get("claude_version"),
                       "handshake": doc.get("handshake")}}


def latency(mcp_ms: float | None, cli_ms: float | None,
            discover_ms: float | None) -> dict:
    """§9's latency row: medians and the ratio, measured and never gated."""
    gone = _missing(mcp_ms=mcp_ms, cli_ms=cli_ms, discover_ms=discover_ms)
    if gone:
        return _dropped(f"the latency phase did not finish "
                        f"({', '.join(gone)} unread)")
    ratio = mcp_ms / cli_ms if cli_ms else None
    return {"word": "measured",
            "read": (f"median `runs` through the wire {mcp_ms:.1f} ms vs "
                     f"{cli_ms:.1f} ms through the CLI"
                     + (f", a ratio of {ratio:.2f}×" if ratio else "")
                     + f"; server spawn to the `server/discover` answer "
                       f"{discover_ms:.1f} ms"),
            "detail": {"mcp_ms": mcp_ms, "cli_ms": cli_ms, "ratio": ratio,
                       "discover_ms": discover_ms}}


#: The six rows that decide the part's word. H7 is `reported` and latency
#: is `measured`; §9 gates on neither.
GATING = ("H1", "H2", "H3", "H4", "H5", "H6")


def part_word(cells: dict) -> str:
    """The part's own word (P14). A STOP OUTRANKS A DROP: a measured
    failure is a finding about the server, a hole is a fact about the run,
    and a part word reporting the hole would bury the finding. A gating
    cell never written at all reads as absent: `INCOMPLETE`, never `DONE`.
    """
    words = [(cells.get(cell) or {}).get("word") for cell in GATING]
    if "STOP" in words:
        return "DONE-WITH-STOP"
    return "DONE" if all(word == "PASS" for word in words) else "INCOMPLETE"
