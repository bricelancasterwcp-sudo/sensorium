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

QUESTIONS RUN IN FILE ORDER, AND SOME OF THEM DEPEND ON IT
----------------------------------------------------------
A question can change the store the next one reads: `refocus` records a
second trace, so a later `runs` question can see a verdict the earlier
question created. That coupling is real and invisible in a plain list, and a
list with hidden order coupling gets reordered eventually. `depends_on`
names the earlier question a question relies on, and `load_cases` refuses a
file where the named question does not appear STRICTLY EARLIER -- so a
reorder fails at load with a message naming both ids, instead of failing
later as a puzzling missing-output error.

UNKNOWN KEYS ARE AN ERROR
-------------------------
A typo'd key that is silently ignored turns an assertion into a comment: the
question keeps passing while checking nothing. Both the top level and each
question are validated against a closed key set, every required key is
checked, question ids must be unique within a file, and a question that
asserts nothing at all (no `expect_contains`, no `expect_line`, no
`expect_count`) is rejected outright rather than counted as a pass.

TWO RECORDERS, ONE HARNESS
--------------------------
`program: main.py` records with `sensorium run` -- the Python recorder.
`program: cargo` records with `cargo sensorium <cargo_args>` -- the Rust
recorder -- and the case directory is a self-contained crate
(`corpus/rust/<case>/{Cargo.toml, src/…, questions.yaml}`) that this harness
copies whole, exactly as it copies a Python case's directory. `record`
(`--focus` / `--window`) belongs to the Python recorder alone and is refused
on a cargo case rather than silently dropped: a focus that does not reach
the recorder is a case that quietly stops testing what it says it tests.

The driver is `$SENSORIUM_CARGO_SENSORIUM`, else `cargo-sensorium` on PATH.
Where neither exists -- the Python CI matrix has no Rust toolchain -- the
cargo cases are SKIPPED BY NAME and counted as skipped in the summary. They
are never counted as passed: "27 cases could not run" and "27 cases passed"
are the two facts this harness exists to keep apart. `CARGO_TARGET_DIR` is
inherited from the environment when it is set (one warm target directory
across the cases is the difference between seconds and minutes) and left to
cargo's own default -- `<workdir>/<case>/target`, inside the disposable copy
-- when it is not.

$RUN AND $RUN2, AND WHY THE SECOND ONE HAS TWO SOURCES
------------------------------------------------------
One `cargo sensorium` invocation records ONE TRACE PER OS PROCESS, and
prints one `run:` line for each, in pid order. So a second run id can come
from either of two places, and the rule is:

* `$RUN`  -- the first `run:` line of the first recording, always.
* `$RUN2` -- the SECOND `run:` line of that same invocation when the
             invocation produced two traces and the case declares no
             `second_run` (`rust/abort`: a parent and the child it spawned).
             Otherwise the first `run:` line of the second recording.

A Python recording prints exactly one `run:` line, so for a Python case the
rule reduces to the one it always had, and `load_cases` still refuses a
Python case that uses `$RUN2` without declaring `second_run`. A cargo case
cannot be checked that way at load time -- how many processes an invocation
records is not knowable from the YAML -- so it is checked at run time
instead, against the ids the recording actually produced.
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
                  "expect_absent", "expect_exit", "depends_on"}
ALLOWED_TOP_KEYS = {"program", "argv", "record", "second_run", "questions",
                    "cargo_args"}
#: `program:` value that selects the Rust recorder instead of the Python one.
CARGO = "cargo"
#: Subdirectory of the corpus holding the cargo cases. Their names carry it
#: (`rust/panic`), so a Rust port and its Python original never collide in
#: `--only`, in the per-case report line, or in the (case, question id)
#: uniqueness the suite checks.
RUST_DIR = "rust"
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
    #: argv after `cargo sensorium`, for a `program: cargo` case.
    cargo_args: list = field(default_factory=list)

    @property
    def is_cargo(self) -> bool:
        return self.program == CARGO


@dataclass
class CaseResult:
    name: str
    failures: list = field(default_factory=list)
    # Why this case did not run, if it did not. A skipped case asks no
    # questions and reports no failures, and the summary counts it in its own
    # column: a suite that cannot run 13 of its cases must not print a line
    # that reads the same as one where all 33 passed.
    skipped: str | None = None
    # Deliberately NOT called `passed`: this counts questions ASKED, and a
    # field named `passed` that also counts the ones that failed is the same
    # kind of dishonest reporting the tool under test exists to prevent.
    asked: int = 0
    # A crash in the harness itself (a broken copytree, a bug in a check),
    # kept distinct from a failed question -- "the tool answered wrong" and
    # "the harness could not ask" are different facts.
    error: str | None = None


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
    if "depends_on" in q and not isinstance(q["depends_on"], str):
        raise ValueError(f"{where}:{qid}: depends_on must be the id of an "
                         "earlier question in this file")
    # A question with no assertion is a question that always passes. That is
    # the single worst thing a corpus can contain, so it is refused at load
    # time rather than counted.
    if not any(q.get(k) for k in ASSERTING_KEYS):
        raise ValueError(
            f"{where}:{qid}: asserts nothing -- needs a non-empty "
            f"{' / '.join(ASSERTING_KEYS)}")


def _validate_top(where: str, spec: dict) -> None:
    """The keys that mean different things to the two recorders.

    Each recorder ignores the other's keys, and an ignored key is the failure
    this module refuses everywhere else: `record: {focus: …}` on a cargo case
    would read as a line-focused recording and produce a call-tier one, with
    every question still passing because none of them can tell.
    """
    extra = set(spec) - ALLOWED_TOP_KEYS
    if extra:
        raise ValueError(f"{where}: unknown keys {sorted(extra)}")
    if "program" not in spec or "questions" not in spec:
        raise ValueError(f"{where}: needs both 'program' and 'questions'")
    if spec["program"] != CARGO:
        if "cargo_args" in spec:
            raise ValueError(f"{where}: cargo_args belongs to a "
                             f"'program: {CARGO}' case; this one runs "
                             f"{spec['program']!r} through the Python "
                             "recorder, which never sees it")
        return
    for key in ("record", "argv"):
        if key in spec:
            raise ValueError(
                f"{where}: {key!r} is the Python recorder's key and the "
                f"'{CARGO}' driver never receives it; a cargo case says what "
                "it runs in cargo_args (arguments for the program itself go "
                "after `--`)")
    args = spec.get("cargo_args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"{where}: a 'program: {CARGO}' case needs a "
                         "non-empty cargo_args list (the argv after "
                         "`cargo sensorium`)")
    second = spec.get("second_run")
    if second is not None and not second.get("cargo_args"):
        raise ValueError(f"{where}: second_run of a '{CARGO}' case needs its "
                         "own cargo_args")


def _question_files(root: Path) -> list[Path]:
    """Every case file, Python cases first and cargo cases after them.

    Two levels, not a recursive glob: a case is a directory of a corpus, and
    `rust/` is the one that holds cargo cases. A `**` glob would also sweep
    up anything a case's own build left behind.
    """
    return (sorted(Path(root).glob("*/questions.yaml"))
            + sorted(Path(root).glob(f"{RUST_DIR}/*/questions.yaml")))


def load_cases(root: Path = ROOT) -> list[Case]:
    cases = []
    for qfile in _question_files(Path(root)):
        spec = yaml.safe_load(qfile.read_text())
        _validate_top(str(qfile), spec)
        seen = set()
        for q in spec["questions"]:
            _validate_question(str(qfile), q)
            if q["id"] in seen:
                raise ValueError(f"{qfile}: duplicate question id {q['id']!r}")
            # Checked against the ids seen SO FAR, which is what makes a
            # reorder an error rather than a silent behaviour change: a
            # dependency naming a later question -- or itself -- is not yet
            # in `seen`.
            dep = q.get("depends_on")
            if dep is not None and dep not in seen:
                raise ValueError(
                    f"{qfile}:{q['id']}: depends_on {dep!r} must name a "
                    "question earlier in this file; questions run in file "
                    f"order and {dep!r} is not among the ones before it")
            seen.add(q["id"])
            # A Python recording is exactly one process and prints exactly
            # one `run:` line, so `$RUN2` without a `second_run` can only be
            # a mistake and is refused here. A cargo invocation records one
            # trace per PROCESS, so the same expression is legitimate there
            # (`rust/abort`: parent and child) and is checked at run time
            # against the ids the recording really produced.
            if (spec["program"] != CARGO and "$RUN2" in q["command"]
                    and spec.get("second_run") is None):
                raise ValueError(f"{qfile}:{q['id']}: uses $RUN2 but the case "
                                 "declares no second_run")
        cases.append(Case(str(qfile.parent.relative_to(Path(root))),
                          qfile.parent, spec["program"],
                          spec.get("argv", []), spec.get("record") or {},
                          spec.get("second_run"), spec["questions"],
                          spec.get("cargo_args") or []))
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


#: Why the cargo cases could not run, in the words the summary prints.
NO_DRIVER = "no cargo-sensorium"


def cargo_driver() -> str | None:
    """The `cargo-sensorium` this run will record with, or None.

    `SENSORIUM_CARGO_SENSORIUM` first (CI's `rust` job builds one and names
    it; so does a developer with a release build on the second disk), then
    PATH. Returning None is not an error: it is the ordinary state of the
    Python CI matrix, which has no Rust toolchain, and the cases it cannot
    record are reported as skipped BY NAME rather than passed.
    """
    return os.environ.get("SENSORIUM_CARGO_SENSORIUM") or shutil.which(
        "cargo-sensorium")


def _run_ids(stdout: str) -> list[str]:
    """Every `run:` line's id, in the order the recorder printed them.

    Not anchored at the end of the line: the Rust driver's line carries pid,
    exe, event and thread counts and the exit status after the id, and it
    prints ONE PER PROCESS -- so this returns a list where the Python
    recorder always yields exactly one.
    """
    return re.findall(r"^run: (\S+)", stdout, re.M)


def _diagnostic(argv, r) -> str:
    """What a recording that produced no `run:` line has to say for itself.

    The command and the EXIT CODE first, because a recorder can fail
    silently: a driver that is not the driver (a stale path, a shim, a
    `/bin/false`) writes nothing at all, and `recording failed: ` with an
    empty tail after it names neither what ran nor that it refused. The
    output follows when there is any.
    """
    out = (r.stdout + r.stderr).strip()
    return (f"`{' '.join(str(a) for a in argv)}` exited {r.returncode}"
            + (f"\n{out}" if out else " and wrote nothing"))


def _record(case: Case, wd: Path, sdir: Path, argv) -> tuple[list[str], str]:
    rec = ["run"]
    for f in case.record.get("focus") or []:
        rec += ["--focus", f]
    if case.record.get("window"):
        rec += ["--window", case.record["window"]]
    rec += ["--", case.program, *[str(a) for a in argv]]
    r = _cli(rec, wd, sdir)
    return _run_ids(r.stdout), _diagnostic([sys.executable, "-m", "sensorium",
                                            *rec], r)


def _record_cargo(driver: str, wd: Path, sdir: Path,
                  cargo_args) -> tuple[list[str], str]:
    """One `cargo sensorium <cargo_args>` invocation in the copied crate.

    CARGO_TARGET_DIR is whatever the environment says (unset -> cargo's own
    `<wd>/target`, inside the disposable copy), so a caller can point every
    case at one warm target directory without this file naming a path that
    exists on one machine.
    """
    argv = [driver, "sensorium", *[str(a) for a in cargo_args]]
    r = subprocess.run(
        argv, cwd=wd, capture_output=True, text=True,
        env={**os.environ, "SENSORIUM_DIR": str(sdir),
             "PYTHONDONTWRITEBYTECODE": "1"})
    return _run_ids(r.stdout), _diagnostic(argv, r)


def sub_run_ids(value, run_id: str, run_id2: str | None):
    """`$RUN` / `$RUN2` -> the ids this recording produced, everywhere in a
    question -- command, expect_contains, expect_line groups, expect_absent
    and expect_count keys -- not only the command.

    A run id is minted at conversion time, so a question that wants to assert
    a fact NAMING one (`rust/abort`: the parent's `info` prints
    `child runs: 1 -- <the child's id>`) cannot spell it literally, and
    without this it could only assert the prefix and leave the id itself
    unchecked -- which is the difference between "a child is linked" and
    "THAT child is linked".

    `$RUN2` first, the same rule `tests/test_rust_convert.py` keeps:
    substituting `$RUN` first turns `$RUN2` into `<run-id>2`, a silently
    wrong lookup instead of an absent one.
    """
    if isinstance(value, str):
        if run_id2 is not None:
            return value.replace("$RUN2", run_id2).replace("$RUN", run_id)
        # With no second id there is nothing to put there, and `$RUN` must
        # not eat the prefix of `$RUN2` and leave `<run-id>2` behind: split
        # on it, substitute around it, put it back. The caller refuses such
        # a question by name before it is ever asked; this keeps the
        # function from quietly manufacturing a wrong id if that guard is
        # ever moved.
        return "$RUN2".join(part.replace("$RUN", run_id)
                            for part in value.split("$RUN2"))
    if isinstance(value, list):
        return [sub_run_ids(v, run_id, run_id2) for v in value]
    if isinstance(value, dict):
        # Keys as well as values: `expect_count` is keyed by the substring
        # being counted, and that substring is where a run id would appear.
        # A non-string value (an `expect_count` tally, an `expect_exit`)
        # comes back untouched.
        return {sub_run_ids(k, run_id, run_id2): sub_run_ids(v, run_id,
                                                             run_id2)
                for k, v in value.items()}
    return value


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


def _record_both(case: Case, wd: Path, sdir: Path,
                 driver: str | None) -> tuple[list[str], list[str], str]:
    """Record the case, and its `second_run` if it declares one.

    Returns (ids of the first recording, ids of the second, error text).
    """
    if case.is_cargo:
        first, err = _record_cargo(driver, wd, sdir, case.cargo_args)
    else:
        first, err = _record(case, wd, sdir, case.argv)
    if not first or case.second_run is None:
        return first, [], err
    if case.is_cargo:
        second, err2 = _record_cargo(driver, wd, sdir,
                                     case.second_run["cargo_args"])
    else:
        second, err2 = _record(case, wd, sdir,
                               case.second_run.get("argv", []))
    return first, second, err2


def run_case(case: Case, workdir: Path,
             driver: str | None = None) -> CaseResult:
    res = CaseResult(case.name)
    if case.is_cargo and driver is None:
        driver = cargo_driver()
        if driver is None:
            res.skipped = NO_DRIVER
            return res
    wd = Path(workdir) / case.name
    # `target` and `Cargo.lock` are a cargo case's build output, not its
    # source: copying a local build into the disposable workdir would carry a
    # stale binary in and make the run depend on what happened to be lying
    # around.
    shutil.copytree(case.dir, wd, ignore=shutil.ignore_patterns(
        "__pycache__", "target", "Cargo.lock", ".sensorium"))
    sdir = wd / ".sensorium"
    first, second, err = _record_both(case, wd, sdir, driver)
    if not first:
        res.failures.append(f"{case.name}: recording failed: {err[:_EXCERPT]}")
        return res
    if case.second_run is not None and not second:
        res.failures.append(
            f"{case.name}: second recording failed: {err[:_EXCERPT]}")
        return res
    # $RUN2 from the second recording where there is one, else from the
    # second PROCESS of the first -- see the module docstring. `None` when
    # neither exists, and a question that uses it then fails by name.
    run_id = first[0]
    run_id2 = second[0] if second else (first[1] if len(first) > 1 else None)
    for spec in case.questions:
        res.asked += 1
        if "$RUN2" in str(spec) and run_id2 is None:
            res.failures.append(
                f"{case.name}/{spec['id']}: uses $RUN2, but this case "
                f"declares no second_run and the recording produced "
                f"{len(first)} trace(s)")
            continue
        q = sub_run_ids(spec, run_id, run_id2)
        cmd = [str(a) for a in q["command"]]
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
def _repo_root_on_path() -> None:
    """Make `corpus._bench` importable however this file was invoked.

    Running it as a script -- which is how the README documents it -- puts
    `corpus/` on `sys.path` rather than the repo root, so the package import
    below fails with `No module named 'corpus'`. Under pytest the root is
    already there (`pythonpath = ["."]`), which is exactly why this cannot be
    left to the test suite to notice.
    """
    root = str(ROOT.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="run the sensorium corpus")
    ap.add_argument("--only", default=None, help="run one case by name")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show", action="store_true",
                    help="print each question's ask, command and ground truth")
    ap.add_argument("--bench", action="store_true",
                    help="report recording overhead and exit 0")
    args = ap.parse_args(argv)
    if args.bench:
        # Reports, never gates: overhead is a tracked fact about a machine
        # and a workload, so there is no number here that can fail.
        _repo_root_on_path()
        from corpus._bench import bench
        bench.report()
        return 0
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
            try:
                results.append(run_case(case, Path(tmp)))
            except Exception as e:
                # Isolate the crash to this case: an unhandled raise here would
                # abandon the loop before the summary, silently dropping every
                # case already run. Record it as an error and carry on.
                results.append(CaseResult(case.name,
                                          error=f"{type(e).__name__}: {e}"))
    failures = [f for r in results for f in r.failures]
    errors = [r for r in results if r.error]
    skipped = [r for r in results if r.skipped]
    # Every distinct reason, named. "13 skipped" alone would leave a reader
    # to guess whether the cases are broken or the toolchain is absent.
    why = ", ".join(sorted({r.skipped for r in skipped}))
    if args.json:
        print(json.dumps({"cases": len(results),
                          "questions": sum(r.asked for r in results),
                          "skipped": [{"case": r.name, "reason": r.skipped}
                                      for r in skipped],
                          "failures": failures,
                          "errors": [{"case": r.name, "error": r.error}
                                     for r in errors]}, indent=2))
    else:
        for r in results:
            mark = ("ERR" if r.error else "skip" if r.skipped
                    else "FAIL" if r.failures else "ok")
            print(f"{mark:>4}  {r.name}  ({r.asked} questions)"
                  + (f"  {r.skipped}" if r.skipped else ""))
            if r.error:
                print(f"        harness error: {r.error}")
        for f in failures:
            print("  " + f)
        print(f"\n{len(results)} cases"
              + (f" ({len(skipped)} skipped: {why})" if skipped else "")
              + f", {sum(r.asked for r in results)} questions, "
              f"{len(failures)} failures, {len(errors)} error(s)")
    return 1 if (failures or errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
