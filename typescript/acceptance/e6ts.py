"""E6-TS: are the corpus's verdicts the pre-registered ones?

    .venv/bin/python typescript/acceptance/e6ts.py <work dir> [case name]...

A case name filters the run to those cases and labels the cell `filtered_to`,
which is what a DRY run is; the endpoint passes none and asks every case.

Every TypeScript corpus case that asks an `exceptions` question is recorded
through the driver -- `run_corpus`'s own machinery, so the recording this
reads is the recording the corpus suite reads -- and the printed answer is
compared against the table §1 locked BEFORE any case existed.

WHAT IS COMPARED, AND WHY NOT THE QUESTIONS' OWN PINS
-----------------------------------------------------
The cases' `questions.yaml` pin their verdict lines with `expect_line`,
which is a SUBSTRING match by design: an assertion about wording that broke
on every improvement would have been loosened away years ago. But a
substring is the wrong instrument for THIS endpoint. `dispositions:
swallowed 1` is a substring of `dispositions: swallowed 1, re-raised 1`, so
a case whose tally grew a disposition would pass its own question and pass
an endpoint that reused it (Task 6's review, M4). So nothing here reuses a
pin: the printed `dispositions:` line is parsed WHOLE into its terms, and
the SWALLOWED lines are counted out of the output directly.

Two independent derivations of one number, and both must agree with the
locked table:

  * how many lines of the answer begin `SWALLOWED --` -- the literal token
    is printed by exactly one sentence in `exceptions_typescript` (its
    module docstring says so, and this is the endpoint that relies on it);
  * the `swallowed` term of the parsed tally line.

A case where those two disagree is a case where the tool's own tally does
not describe its own output, which is a difference and therefore a STOP --
so it is reported as such rather than resolved by preferring one.

WHAT S5 RUNG 3 ADDED
--------------------
Three things, all of them the same shape as the above -- a WHOLE printed line
compared against a table locked before the answer existed:

  * the four new cases (`untraced_catcher`, `untraced_catcher_rejection`,
    `untraced_catcher_later_failure`, `logged_rethrow_to_harness`), each
    pre-registered at 0 SWALLOWED lines;
  * the `ambiguous by reason:` line, whole, for the five cases rung 3's
    pre-registration and its own new cases pin one -- INCLUDING the case
    that must print none at all, which a table of expected strings alone
    could not state;
  * each case's own `expect_line`/`expect_absent` pins, run through the
    corpus harness's own `check_question` over this very output. §1's rule
    has two halves ("set equality with the rung-2 locked table; every new
    pin green"), and checking both off one recording is what keeps the two
    halves about the same run.

`value` is how many cases matched the locked table, out of the cases asked.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from corpus.run_corpus import (TS_DIR, _cli, _copy_case,  # noqa: E402
                               _record_both, check_question, load_cases,
                               sub_run_ids, ts_ready)
from lens import cell, emit, usage  # noqa: E402

#: §1's locked table: the SWALLOWED count each case's answer must print.
#: "every other case 0" is written out per case rather than defaulted, so a
#: case this collector fails to see is a KeyError and not a silent zero.
PRE_REGISTERED = {
    "silent_swallow": 1,
    "logged_catch": 1,
    "callback_sink": 1,
    "callback_handled": 1,
    "await_rejection_caught": 1,
    "finally_return": 1,
    "dependency_throw": 1,
    "rethrow_hop": 1,
    "escaped_catch": 0,
    "asserted_catch": 0,
    "translated": 0,
    "callback_escaped": 0,
    "callback_opaque": 0,
    "test_failed": 0,
    "unhandled_rejection_in_info": 0,
    "primitive_rethrow": 0,
    "suspended_handler": 0,
    # S5 rung 3's four, pre-registered at 0 each. None of them swallows
    # anything: three are untraced-catcher shapes and the fourth is a
    # logged rethrow that reaches the harness.
    "untraced_catcher": 0,
    "untraced_catcher_rejection": 0,
    "untraced_catcher_later_failure": 0,
    "logged_rethrow_to_harness": 0,
}

#: S5 rung 3: the `ambiguous by reason:` line each case must print, WHOLE.
#: `None` is "no such line at all", which is a claim of its own -- a verdict
#: the tool reaches with confidence grows no reason line, and `logged_rethrow
#: _to_harness` exists to pin that. A case absent from this table is not
#: checked for a reason line, because rung 2's seventeen were locked before
#: the line existed and their answers are not this rung's to move.
#:
#: `translated` is the one rung-2 case whose line §1 pre-registers: its
#: wrapper block reads the untraced-catcher reason beside the original's
#: escaped one.
PRE_REGISTERED_REASON_LINE = {
    "translated": "ambiguous by reason: escaped 1, untraced catcher 1",
    "untraced_catcher": "ambiguous by reason: untraced catcher 1",
    "untraced_catcher_rejection": "ambiguous by reason: untraced catcher 1",
    "untraced_catcher_later_failure": "ambiguous by reason: untraced catcher 1",
    "logged_rethrow_to_harness": None,
}

#: The cases §1 names as swallow cases: their set must be non-empty, which
#: is the rule's second clause and not a restatement of the first (a table
#: edited to zeroes would satisfy equality and nothing else).
SWALLOW_CASES = frozenset(k for k, v in PRE_REGISTERED.items() if v)


def reason_of(text: str) -> str | None:
    """The printed `ambiguous by reason:` line, whole, or None where the
    answer printed none."""
    return next((ln.strip() for ln in text.splitlines()
                 if ln.strip().startswith("ambiguous by reason:")), None)


def tally_of(text: str) -> tuple[str | None, dict]:
    """The printed `dispositions:` line, and its terms parsed WHOLE.

    `dispositions: swallowed 1, re-raised 1` -> `{"swallowed": 1,
    "re-raised": 1}`. A term this cannot read leaves the line unparsed and
    the caller reports the whole line rather than a partial reading.
    """
    line = next((ln.strip() for ln in text.splitlines()
                 if ln.strip().startswith("dispositions:")), None)
    if line is None:
        return None, {}
    terms = {}
    for part in line[len("dispositions:"):].split(","):
        word, _, count = part.strip().rpartition(" ")
        if not word or not count.isdigit():
            return line, {}
        terms[word] = int(count)
    return line, terms


def ask(case, wd: Path, sdir: Path) -> dict:
    """Record one case and run its `exceptions` question. Raw facts only."""
    _copy_case(case, wd)
    first, second, err = _record_both(case, wd, sdir, None)
    if not first:
        return {"error": f"recording failed: {err[:800]}"}
    spec = next((q for q in case.questions if q["command"][0] == "exceptions"),
                None)
    if spec is None:
        return {"error": "no exceptions question"}
    run2 = second[0] if second else (first[1] if len(first) > 1 else None)
    q = sub_run_ids(spec, first[0], run2)
    cmd = [str(a) for a in q["command"]]
    out = _cli(cmd, wd, sdir)
    text = out.stdout + out.stderr
    return {"question": q["id"], "command": " ".join(cmd),
            "exit": out.returncode, "text": text,
            # The case's OWN pins, checked by the corpus harness's own
            # checker over this very output: §1's E6-TS rule has two halves
            # ("set equality ... ; every new pin green") and one recording
            # answers both, rather than recording the corpus twice.
            "pin_failures": check_question(q, text, out.returncode)}


def judge(name: str, raw: dict) -> dict:
    """One case's row: the two derivations, the tally, and whether it matched."""
    want = PRE_REGISTERED[name]
    if "error" in raw:
        return {"case": name, "expected": want, "equal": None,
                "why": [raw["error"]]}
    text = raw["text"]
    lines = [ln.strip() for ln in text.splitlines()
             if ln.strip().startswith("SWALLOWED --")]
    line, terms = tally_of(text)
    reason = reason_of(text)
    got = terms.get("swallowed", 0) if line is not None else None
    why = []
    if line is None:
        why.append("the answer printed no `dispositions:` line")
    elif not terms:
        why.append(f"the tally line could not be parsed whole: {line!r}")
    if len(lines) != want:
        why.append(f"{len(lines)} SWALLOWED line(s), the locked table says {want}")
    if got != want:
        why.append(f"the tally says swallowed {got}, the locked table says {want}")
    if got is not None and got != len(lines):
        why.append(f"the tally says swallowed {got} and the answer prints "
                   f"{len(lines)} SWALLOWED line(s): the tool's own tally does "
                   "not describe its own output")
    if name in SWALLOW_CASES and not lines:
        why.append("a pre-registered swallow case whose SWALLOWED set is empty")
    if name in PRE_REGISTERED_REASON_LINE:
        want_reason = PRE_REGISTERED_REASON_LINE[name]
        if reason != want_reason:
            why.append(f"the reason line reads {reason!r}, the locked table "
                       f"says {want_reason!r}")
    for failure in raw.get("pin_failures") or []:
        why.append(f"a pin of the case's own question failed: {failure}")
    return {"case": name, "expected": want, "swallowed_lines": len(lines),
            "tally_swallowed": got, "tally_line": line, "tally": terms,
            "reason_line": reason,
            "expected_reason_line": PRE_REGISTERED_REASON_LINE.get(name, "-"),
            "pin_failures": raw.get("pin_failures") or [],
            "exit": raw["exit"], "question": raw["question"],
            "command": raw["command"], "lines": lines,
            "equal": not why, "why": why}


def collect(workdir: Path, only: frozenset[str]) -> list[dict]:
    rows = []
    for case in load_cases(only_dir=TS_DIR):
        if not any(q["command"][0] == "exceptions" for q in case.questions):
            continue
        # `load_cases` names a case by its directory PAIR (`typescript/x`);
        # the locked table names the case, which is the leaf.
        name = case.name.rpartition("/")[2]
        if only and name not in only:
            continue
        wd = workdir / name
        raw = ask(case, wd, wd / ".sensorium")
        rows.append(judge(name, raw) | {"corpus_case": case.name})
        shutil.rmtree(wd, ignore_errors=True)
    return rows


def main(argv) -> int:
    if len(argv) < 2:
        usage("usage: e6ts.py <work dir> [case name]...   "
              "(a case name makes it a DRY RUN, labelled `filtered_to` in the "
              "cell; the endpoint runs every case)")
    # A helper script inherits whatever the shell was carrying; a stray
    # spool or manifest directory once polluted a probe run, and these two
    # would send every recording below into somebody else's store.
    for stray in ("SENSORIUM_SPOOL", "SENSORIUM_MANIFEST_DIR"):
        os.environ.pop(stray, None)
    if not ts_ready():
        emit(cell(None, 0, ["the TypeScript recorder cannot run on this box "
                            "(no corpus/typescript/node_modules, or node is "
                            "below the floor): no case was asked"]))
        return 0
    work = Path(argv[1])
    work.mkdir(parents=True, exist_ok=True)
    only = frozenset(argv[2:])
    rows = collect(Path(tempfile.mkdtemp(prefix="e6ts-", dir=work)), only)
    dropped = [f"{r['case']}: " + "; ".join(r["why"]) for r in rows
               if r["equal"] is None]
    asked = [r for r in rows if r["equal"] is not None]
    emit(cell(sum(1 for r in asked if r["equal"]), len(asked), dropped,
              filtered_to=sorted(only) or None,
              pre_registered=PRE_REGISTERED,
              pre_registered_reason_line=PRE_REGISTERED_REASON_LINE,
              recorder=os.environ.get("E6TS_RECORDER"),
              recorder_rev=os.environ.get("E6TS_REV"),
              differences=[{"case": r["case"], "why": r["why"]}
                           for r in asked if not r["equal"]],
              per_case=rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
