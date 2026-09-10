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

`value` is how many cases matched the locked table, out of the cases asked.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from corpus.run_corpus import (TS_DIR, _cli, _copy_case,  # noqa: E402
                               _record_both, load_cases, sub_run_ids,
                               ts_ready)
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
}

#: The cases §1 names as swallow cases: their set must be non-empty, which
#: is the rule's second clause and not a restatement of the first (a table
#: edited to zeroes would satisfy equality and nothing else).
SWALLOW_CASES = frozenset(k for k, v in PRE_REGISTERED.items() if v)


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
    return {"question": q["id"], "command": " ".join(cmd),
            "exit": out.returncode, "text": out.stdout + out.stderr}


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
    return {"case": name, "expected": want, "swallowed_lines": len(lines),
            "tally_swallowed": got, "tally_line": line, "tally": terms,
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
              differences=[{"case": r["case"], "why": r["why"]}
                           for r in asked if not r["equal"]],
              per_case=rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
