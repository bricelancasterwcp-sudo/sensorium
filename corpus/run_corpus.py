"""Record each corpus program, run its pre-registered questions, and verify
the answers against known ground truth.

This is the tool's regression suite. Every question was registered BEFORE its
output was looked at, and the ground truth is known because the bug was
planted deliberately. Each question also carries `why_logs_fail`: if a
`print()` in the right place would have answered it, the case does not
justify the tool and belongs somewhere else.

WHAT AN ASSERTION MAY BE MADE OF
--------------------------------
Command output text is the only thing this harness can see, and much of that
text was rewritten repeatedly to be precise about what it does and does not
claim. So expectations name SUBSTANTIVE facts -- verdicts, counts, names,
event ids, rendered values -- and never incidental phrasing. A corpus that
breaks whenever wording improves gets its expectations loosened, and a
loosened corpus is not a regression suite any more.

Four assertion forms, in order of how tightly they bind:

* `expect_line`   -- groups of substrings that must ALL appear on ONE line.
                     This is the default choice. Plain whole-output
                     substring matching is satisfied by the WRONG line
                     (four such non-biting tests shipped earlier in this
                     project), so an assertion about "the call that got
                     1000 returned 95.0" must be pinned to a single line or
                     it is not that assertion.
* `expect_count`  -- exact number of occurrences of a substring. The only
                     honest way to assert "charge ran twice".
* `expect_contains` -- whole-output substring. For facts that genuinely are
                     whole-output facts: a tally line, a verdict, a header.
* `expect_absent` -- must not appear anywhere. The bug's counterfactual:
                     `gold` must not appear in the frame that took `silver`.

`expect_exit` defaults to 0 and is checked for every question, so a command
that answers correctly by accident while exiting 2 still fails.

UNKNOWN KEYS ARE AN ERROR
-------------------------
A typo'd key that is silently ignored turns an assertion into a comment: the
question keeps passing while checking nothing. Both the top level and each
question are validated against a closed key set, every required key is
checked, question ids must be unique within a file, and a question that
asserts nothing at all (no `expect_contains`, no `expect_line`, no
`expect_count`) is rejected outright rather than counted as a pass.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ALLOWED_Q_KEYS = {"id", "ask", "truth", "why_logs_fail", "command",
                  "expect_contains", "expect_line", "expect_count",
                  "expect_absent", "expect_exit"}
ALLOWED_TOP_KEYS = {"program", "argv", "record", "second_run", "questions"}
# `expect_contains` is deliberately NOT in this list, unlike the original
# schema. Requiring it by name while allowing it to be `[]` makes a question
# that asserts nothing pass validation, which is the exact failure this
# harness cannot have. The rule that replaces it -- at least one non-empty
# asserting key -- is strictly stronger, and lets a question that is properly
# expressed as a line group say so instead of carrying a token substring.
REQUIRED_Q_KEYS = ("id", "ask", "truth", "why_logs_fail", "command")
ASSERTING_KEYS = ("expect_contains", "expect_line", "expect_count")
_EXCERPT = 1200


@dataclass
class Case:
    name: str
    dir: Path
    program: str
    argv: list = field(default_factory=list)
    record: dict = field(default_factory=dict)
    second_run: dict | None = None
    questions: list = field(default_factory=list)


@dataclass
class CaseResult:
    name: str
    failures: list = field(default_factory=list)
    # Deliberately NOT called `passed`: this counts questions ASKED, and a
    # field named `passed` that also counts the ones that failed is the same
    # kind of dishonest reporting the tool under test exists to prevent.
    asked: int = 0


# -- loading and validation -------------------------------------------------
def _validate_question(where: str, q) -> None:
    if not isinstance(q, dict):
        raise ValueError(f"{where}: question must be a mapping, got {type(q)}")
    bad = set(q) - ALLOWED_Q_KEYS
    if bad:
        raise ValueError(f"{where}:{q.get('id')}: unknown {sorted(bad)}")
    for required in REQUIRED_Q_KEYS:
        if required not in q:
            raise ValueError(f"{where}: question missing {required!r}")
    qid = q["id"]
    if not isinstance(q["command"], list) or not q["command"]:
        raise ValueError(f"{where}:{qid}: command must be a non-empty list")
    for key in ("expect_contains", "expect_absent"):
        if key in q and not isinstance(q[key], list):
            raise ValueError(f"{where}:{qid}: {key} must be a list")
    for group in q.get("expect_line") or []:
        if not isinstance(group, list) or not group:
            raise ValueError(f"{where}:{qid}: each expect_line entry must be "
                             "a non-empty list of substrings")
    if not isinstance(q.get("expect_count", {}), dict):
        raise ValueError(f"{where}:{qid}: expect_count must be a mapping "
                         "of substring -> exact count")
    # A question with no assertion is a question that always passes. That is
    # the single worst thing a corpus can contain, so it is refused at load
    # time rather than counted.
    if not any(q.get(k) for k in ASSERTING_KEYS):
        raise ValueError(
            f"{where}:{qid}: asserts nothing -- needs a non-empty "
            f"{' / '.join(ASSERTING_KEYS)}")


def load_cases(root: Path = ROOT) -> list[Case]:
    cases = []
    for qfile in sorted(Path(root).glob("*/questions.yaml")):
        spec = yaml.safe_load(qfile.read_text())
        extra = set(spec) - ALLOWED_TOP_KEYS
        if extra:
            raise ValueError(f"{qfile}: unknown keys {sorted(extra)}")
        if "program" not in spec or "questions" not in spec:
            raise ValueError(f"{qfile}: needs both 'program' and 'questions'")
        seen = set()
        for q in spec["questions"]:
            _validate_question(str(qfile), q)
            if q["id"] in seen:
                raise ValueError(f"{qfile}: duplicate question id {q['id']!r}")
            seen.add(q["id"])
            if "$RUN2" in q["command"] and spec.get("second_run") is None:
                raise ValueError(f"{qfile}:{q['id']}: uses $RUN2 but the case "
                                 "declares no second_run")
        cases.append(Case(qfile.parent.name, qfile.parent, spec["program"],
                          spec.get("argv", []), spec.get("record") or {},
                          spec.get("second_run"), spec["questions"]))
    return cases


# -- running ---------------------------------------------------------------
def _cli(args, cwd, sdir):
    """The real CLI, in a subprocess, against a disposable trace store.

    SENSORIUM_DIR is what keeps the corpus out of the user's own trace
    store; PYTHONDONTWRITEBYTECODE keeps stale bytecode from surviving a
    same-second rewrite of a corpus program.
    """
    return subprocess.run(
        [sys.executable, "-m", "sensorium", *args], cwd=cwd,
        capture_output=True, text=True,
        env={**os.environ, "SENSORIUM_DIR": str(sdir),
             "PYTHONDONTWRITEBYTECODE": "1"})


def _record(case: Case, wd: Path, sdir: Path, argv) -> tuple[str | None, str]:
    rec = ["run"]
    for f in case.record.get("focus") or []:
        rec += ["--focus", f]
    if case.record.get("window"):
        rec += ["--window", case.record["window"]]
    rec += ["--", case.program, *[str(a) for a in argv]]
    r = _cli(rec, wd, sdir)
    m = re.search(r"^run: (\S+)$", r.stdout, re.M)
    return (m.group(1) if m else None), (r.stdout + r.stderr)


def _lines_matching(text: str, group: list) -> list[str]:
    return [ln for ln in text.splitlines() if all(n in ln for n in group)]


def check_question(q: dict, text: str, returncode: int) -> list[str]:
    """Every expectation this question registered, against one command's
    output. Returns a list of failure descriptions -- ALL of them, not the
    first: a question that misses three facts should say so once."""
    bad = []
    expect_exit = q.get("expect_exit", 0)
    if returncode != expect_exit:
        bad.append(f"exit {returncode} != {expect_exit}")
    for needle in q.get("expect_contains") or []:
        if needle not in text:
            bad.append(f"missing {needle!r}")
    for group in q.get("expect_line") or []:
        if not _lines_matching(text, group):
            bad.append("no single line contains all of "
                       + ", ".join(repr(n) for n in group))
    for needle, want in (q.get("expect_count") or {}).items():
        got = text.count(needle)
        if got != want:
            bad.append(f"{needle!r} appears {got} time(s), expected {want}")
    for needle in q.get("expect_absent") or []:
        if needle in text:
            bad.append(f"unexpected {needle!r}")
    return bad


def run_case(case: Case, workdir: Path) -> CaseResult:
    res = CaseResult(case.name)
    wd = Path(workdir) / case.name
    shutil.copytree(case.dir, wd,
                    ignore=shutil.ignore_patterns("__pycache__"))
    sdir = wd / ".sensorium"
    run_id, err = _record(case, wd, sdir, case.argv)
    if run_id is None:
        res.failures.append(f"{case.name}: recording failed: {err[:_EXCERPT]}")
        return res
    run_id2 = None
    if case.second_run is not None:
        run_id2, err2 = _record(case, wd, sdir,
                                case.second_run.get("argv", []))
        if run_id2 is None:
            res.failures.append(
                f"{case.name}: second recording failed: {err2[:_EXCERPT]}")
            return res
    subs = {"$RUN": run_id, "$RUN2": run_id2}
    for q in case.questions:
        res.asked += 1
        if "$RUN2" in q["command"] and run_id2 is None:
            res.failures.append(
                f"{case.name}/{q['id']}: uses $RUN2 but no second_run "
                "declared")
            continue
        cmd = [subs.get(a, str(a)) for a in q["command"]]
        out = _cli(cmd, wd, sdir)
        text = out.stdout + out.stderr
        bad = check_question(q, text, out.returncode)
        if bad:
            res.failures.append(
                f"{case.name}/{q['id']}: " + "; ".join(bad)
                + f"\n    ask: {q['ask']}"
                + f"\n    cmd: sensorium {' '.join(cmd)}"
                + f"\n    got: {text[:_EXCERPT]}")
    return res


# -- driving ---------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="run the sensorium corpus")
    ap.add_argument("--only", default=None, help="run one case by name")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show", action="store_true",
                    help="print each question's ask, command and ground truth")
    args = ap.parse_args(argv)
    cases = [c for c in load_cases()
             if args.only is None or c.name == args.only]
    if not cases:
        print("no cases found", file=sys.stderr)
        return 2
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            if args.show:
                for q in case.questions:
                    print(f"{case.name}/{q['id']}: {q['ask']}")
                    print(f"    $ sensorium {' '.join(str(a) for a in q['command'])}")
            results.append(run_case(case, Path(tmp)))
    failures = [f for r in results for f in r.failures]
    if args.json:
        print(json.dumps({"cases": len(results),
                          "questions": sum(r.asked for r in results),
                          "failures": failures}, indent=2))
    else:
        for r in results:
            mark = "FAIL" if r.failures else "ok"
            print(f"{mark:>4}  {r.name}  ({r.asked} questions)")
        for f in failures:
            print("  " + f)
        print(f"\n{len(results)} cases, "
              f"{sum(r.asked for r in results)} questions, "
              f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
