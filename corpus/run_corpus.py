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

WHAT A CASE IS, AND WHERE THAT LIVES
------------------------------------
The schema -- the closed key sets, `Case`, and the refusals that keep one
recorder's keys off another recorder's case -- is `corpus/cases.py`, split
out when the TypeScript cases pushed this module past the repo's 800-line
ceiling. Every name that module owns is imported below and re-exported, so
`run_corpus.load_cases` and `run_corpus.Case` mean what they always meant.

THREE RECORDERS, ONE HARNESS
----------------------------
`program: main.py` records with `sensorium run` -- the Python recorder.
`program: cargo` records with `cargo sensorium <cargo_args>` -- the Rust
recorder -- and the case directory is a self-contained crate
(`corpus/rust/<case>/{Cargo.toml, src/…, questions.yaml}`) that this harness
copies whole, exactly as it copies a Python case's directory. `record`
(`--focus` / `--window`) belongs to the Python recorder alone and is refused
on a cargo case rather than silently dropped: a focus that does not reach
the recorder is a case that quietly stops testing what it says it tests.

`program: vitest` records with `sensorium ts run -- npx vitest run …` -- the
TypeScript recorder -- and is the one case shape that is NOT a directory
this harness can copy on its own. A vitest run needs the project around the
case: the config vitest reads, the `package.json` that names its version,
and an installed `node_modules`. So `corpus/typescript/` is ONE vitest
project and a case is a directory inside it; the harness copies the WHOLE
project minus `node_modules` (symlinked to the real one -- an installed tree
is hundreds of megabytes and copying it per case would dominate the run)
and minus `.sensorium`, and the case's `harness_args` name the tokens after
`vitest` that select its own test files.

Each recorder's keys are refused on the other two rather than ignored:
`cargo_args` on a vitest case, `harness_args` on a cargo case, `record` or
`argv` on either. An ignored key is a case that silently stops testing what
it says it tests, whichever recorder drops it.

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

One `sensorium ts run` invocation records ONE TRACE PER TEST FILE, so a
vitest case with two test files reads the same way -- with one difference
that its `truth` has to state: the two `run:` lines are in spool-name (pid)
order, which is NOT the order vitest ran the files in and is not stable
across runs. A question there may assert only what holds of EITHER file, or
the case declares a `second_run` and compares two invocations instead.

A Python recording prints exactly one `run:` line, so for a Python case the
rule reduces to the one it always had, and `load_cases` still refuses a
Python case that uses `$RUN2` without declaring `second_run`. A cargo or
vitest case cannot be checked that way at load time -- how many processes
or test files an invocation records is not knowable from the YAML -- so it
is checked at run time instead, against the ids the recording actually
produced.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# `corpus/cases.py` is a sibling, and this file is run BOTH ways: as a
# script (`python corpus/run_corpus.py`, which the README documents) and as
# `corpus.run_corpus` (pytest, with the repo root on the path). Only the
# second resolves a package import, so the first is given what it needs
# here -- the same rule `_repo_root_on_path` applies for `corpus._bench`,
# applied at import time because this import is a module-level one.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# `Case`, `CaseResult` and `load_cases` are imported for this module's own
# use AND re-exported: `tests/`, `corpus/_bench` and the acceptance suite all
# reach them as `run_corpus.<name>`, which is where they lived before the
# split, and a caller should not have to know which half of the harness owns
# a name.
from corpus.cases import (ROOT, RUST_DIR, TS_DIR,               # noqa: E402
                          TS_HARNESS_WORD, Case, CaseResult, load_cases)
from sensorium.driver import cargo_sensorium                    # noqa: E402
from sensorium.ts.pkg import (NODE_FLOOR, PackageError,         # noqa: E402
                              node_version)

#: How much of a command's output a failure report quotes.
_EXCERPT = 1200


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

#: ...and why the vitest cases could not. One reason for two conditions,
#: because both are the same fact to a reader: this box cannot run the
#: TypeScript recorder, and the cases were not asked.
NO_TS = "no corpus/typescript/node_modules (npm ci) or node < 24"


def cargo_driver() -> str | None:
    """The `cargo-sensorium` this run will record with, or None.

    One line, because the rule lives in `sensorium.driver` now: the driver a
    case records with and the driver its `refocus` question re-runs with
    have to be the same binary, and they were the same binary only for as
    long as three copies of a two-line rule stayed in step. The import runs
    the safe way round -- this file already requires `sensorium` to be
    importable, since it records by running `python -m sensorium`.

    Returning None is not an error: it is the ordinary state of the Python
    CI matrix, which has no Rust toolchain, and the cases it cannot record
    are reported as skipped BY NAME rather than passed.
    """
    return cargo_sensorium()


def ts_ready(root: Path = ROOT) -> bool:
    """Whether the vitest cases can be recorded on this box.

    Two conditions, and neither is checkable from the YAML: the corpus
    project's dependencies have to be installed (one `npm ci` for all
    thirteen cases -- they share one project) and node has to be at least
    the version the recorder was measured on. The floor is imported from
    the recorder itself rather than spelled again here, so a corpus that
    skips and a driver that refuses cannot disagree about which node is
    old enough.

    False is not an error: it is the ordinary state of a CI matrix with no
    Node, and the cases it cannot record are reported as skipped BY NAME.
    """
    if not (Path(root) / TS_DIR / "node_modules" / "vitest").is_dir():
        return False
    try:
        _reported, parts = node_version()
    except PackageError:
        return False
    return bool(parts) and parts[0] >= NODE_FLOOR


#: A run id as both recorders mint it: `paths.new_run_id` is
#: `%Y%m%d-%H%M%S` plus six hex characters of a uuid4, and the driver's
#: `runid::mint` writes the same shape. Not `\S+`: see `RUN_LINE`.
RUN_ID = r"\d{8}-\d{6}-[0-9a-f]{6}"

#: The THREE shapes this tool prints a `run:` line in, and which two this
#: key accepts:
#:
#:   1. `run: <id>` alone -- `sensorium run` (`cli.py`), and `refocus` when
#:      the re-run set no trace aside (`refocus_cmd`);
#:   2. `run: <id>  pid: ... exit: ...`, one line PER PROCESS --
#:      `cargo-sensorium convert` (`convert/mod.rs`);
#:   3. `run: <id>   <note>` -- `refocus_rust`'s pair line, three spaces and
#:      then the child runs it excluded (pinned by
#:      `corpus/rust/refocus_child_run`).
#:
#: Shape 3 is DELIBERATELY refused, and refusing it costs nothing: this
#: harness keys a RECORDING's stdout and never a refocus's -- `_run_ids` is
#: called from `_record` and `_record_cargo` only, and a case's `refocus`
#: question reads the pair through `runs` or through `$RUN`/`last`. Letting
#: the third shape in would mean accepting `run: <id>` followed by prose,
#: which is the whole class this key was narrowed to exclude. If a caller
#: ever needs a refocus's line, it wants its own pattern rather than a
#: looser version of this one. `tests/test_rust_convert.py` pins shape 3's
#: exact spacing among the near-misses this must refuse, so a widening
#: reddens there.
#:
#: Keyed this narrowly because it was once keyed `^run: (\S+)`, and a case
#: whose own program printed `run: Err(..)` had that read as a trace id --
#: the case worked around it rather than the reader being fixed. A corpus
#: case's stdout is the program's, and a reader of it that accepts anything
#: after `run: ` is reading the program's output as the tool's.
#:
#: The tail is anchored too (end of line, or the converter's `  pid: `), so
#: `run: <id> and then some prose` is not a match either. Shape 2 is
#: pinned byte for byte on the converter side by
#: `tests/test_rust_convert.py`, and this pattern is checked against that
#: same literal there, so the two cannot drift apart silently.
RUN_LINE = re.compile(rf"^run: ({RUN_ID})(?:$|  pid: )", re.M)


def _run_ids(stdout: str) -> list[str]:
    """Every `run:` line's id, in the order the recorder printed them.

    A list, not one id: the Rust driver prints one line per process, where
    the Python recorder always yields exactly one.
    """
    return RUN_LINE.findall(stdout)


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


def _record_vitest(wd: Path, sdir: Path,
                   harness_args) -> tuple[list[str], str]:
    """One `sensorium ts run -- npx vitest run <args>` in the copied project.

    A NON-ZERO exit here is not a recording failure. `sensorium ts run`
    returns the harness's own status by design, so a case whose planted
    truth is a failing test -- or an unhandled rejection vitest fails the
    file for -- exits 1 with a complete recording behind it. What decides
    whether the recording happened is the `run:` lines, which is what this
    returns; zero of them is the failure, and `run_case` reports it with
    the exit code and the output attached.
    """
    argv = [sys.executable, "-m", "sensorium", "ts", "run", "--",
            "npx", "vitest", TS_HARNESS_WORD,
            *[str(a) for a in harness_args[1:]]]
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
    elif case.is_vitest:
        first, err = _record_vitest(wd, sdir, case.harness_args)
    else:
        first, err = _record(case, wd, sdir, case.argv)
    if not first or case.second_run is None:
        return first, [], err
    if case.is_cargo:
        second, err2 = _record_cargo(driver, wd, sdir,
                                     case.second_run["cargo_args"])
    elif case.is_vitest:
        second, err2 = _record_vitest(wd, sdir,
                                      case.second_run["harness_args"])
    else:
        second, err2 = _record(case, wd, sdir,
                               case.second_run.get("argv", []))
    return first, second, err2


def _copy_case(case: Case, wd: Path) -> None:
    """The disposable copy a case is recorded in.

    `target` and `Cargo.lock` are a cargo case's build output, not its
    source: copying a local build into the workdir would carry a stale
    binary in and make the run depend on what happened to be lying around.
    A vitest case needs the project around it and is copied by the function
    below.
    """
    if case.is_vitest:
        _copy_ts_project(case, wd)
        return
    shutil.copytree(case.dir, wd, ignore=shutil.ignore_patterns(
        "__pycache__", "target", "Cargo.lock", ".sensorium"))


def _copy_ts_project(case: Case, wd: Path) -> None:
    """The WHOLE vitest project into the work dir, `node_modules` linked.

    A vitest case is a directory inside one project and cannot be copied on
    its own: the config vitest reads, the `package.json` that names its
    version and the installed tree all live one level up. So the project is
    what travels, every case's directory with it -- `harness_args` is what
    selects this case's files -- and the copy is where the recording runs,
    which is what keeps a case's own writes (a marker file, a spool) out of
    the checkout.

    `node_modules` is SYMLINKED and not copied: an installed vitest is
    hundreds of megabytes and thirteen copies of it would be the whole cost
    of the run. The driver writes its wrapper under
    `<root>/node_modules/.sensorium/` and removes it in a `finally`, so the
    link means that one directory appears in the real tree for the length of
    one recording; the cases run one at a time, and `.sensorium` is ignored
    by the copy so a leftover one is never carried in.
    """
    project = case.dir.parent
    shutil.copytree(project, wd, ignore=shutil.ignore_patterns(
        "__pycache__", "node_modules", ".sensorium"))
    (wd / "node_modules").symlink_to(project / "node_modules",
                                     target_is_directory=True)


def run_case(case: Case, workdir: Path,
             driver: str | None = None) -> CaseResult:
    res = CaseResult(case.name)
    if case.is_cargo and driver is None:
        driver = cargo_driver()
        if driver is None:
            res.skipped = NO_DRIVER
            return res
    if case.is_vitest and not ts_ready():
        res.skipped = NO_TS
        return res
    wd = Path(workdir) / case.name
    _copy_case(case, wd)
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


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="run the sensorium corpus")
    ap.add_argument("--only", default=None, help="run one case by name")
    ap.add_argument("--only-dir", default=None, metavar="DIR",
                    choices=(".", RUST_DIR, TS_DIR),
                    help="run one corpus directory: '.' the Python cases, "
                         f"'{RUST_DIR}' the cargo ones, '{TS_DIR}' the "
                         "vitest ones. One recorder's cases can then be "
                         "gated with --require-driver while another "
                         "recorder's driver is absent")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show", action="store_true",
                    help="print each question's ask, command and ground truth")
    ap.add_argument("--bench", action="store_true",
                    help="report recording overhead and exit 0")
    ap.add_argument("--require-driver", action="store_true",
                    help="exit 1 if any case could not be run")
    return ap


def _run_all(cases, show: bool) -> list:
    """Every case in its own directory of one disposable tree."""
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            if show:
                for q in case.questions:
                    print(f"{case.name}/{q['id']}: {q['ask']}")
                    print("    $ sensorium "
                          + " ".join(str(a) for a in q["command"]))
            try:
                results.append(run_case(case, Path(tmp)))
            except Exception as e:
                # Isolate the crash to this case: an unhandled raise here
                # would abandon the loop before the summary, silently
                # dropping every case already run. Record it as an error and
                # carry on.
                results.append(CaseResult(case.name,
                                          error=f"{type(e).__name__}: {e}"))
    return results


def _report_json(results, failures, skipped, errors, args, unrun) -> None:
    doc = {"cases": len(results),
           "questions": sum(r.asked for r in results),
           "skipped": [{"case": r.name, "reason": r.skipped}
                       for r in skipped],
           "failures": failures,
           "errors": [{"case": r.name, "error": r.error} for r in errors],
           "require_driver": args.require_driver}
    # Present only when the flag actually decided the exit code: a key that
    # is always there says nothing about whether it mattered.
    if unrun:
        doc["exit_reason"] = unrun
    print(json.dumps(doc, indent=2))


def _report_text(results, failures, skipped, errors, unrun) -> None:
    for r in results:
        mark = ("ERR" if r.error else "skip" if r.skipped
                else "FAIL" if r.failures else "ok")
        print(f"{mark:>4}  {r.name}  ({r.asked} questions)"
              + (f"  {r.skipped}" if r.skipped else ""))
        if r.error:
            print(f"        harness error: {r.error}")
    for f in failures:
        print("  " + f)
    # Every distinct reason, named. "13 skipped" alone would leave a reader
    # to guess whether the cases are broken or the toolchain is absent.
    why = ", ".join(sorted({r.skipped for r in skipped}))
    print(f"\n{len(results)} cases"
          + (f" ({len(skipped)} skipped: {why})" if skipped else "")
          + f", {sum(r.asked for r in results)} questions, "
          f"{len(failures)} failures, {len(errors)} error(s)"
          + (f"; {unrun}" if unrun else ""))


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.bench:
        # Reports, never gates: overhead is a tracked fact about a machine
        # and a workload, so there is no number here that can fail.
        _repo_root_on_path()
        from corpus._bench import bench
        bench.report()
        return 0
    cases = [c for c in load_cases(only_dir=args.only_dir)
             if args.only is None or c.name == args.only]
    if not cases:
        print("no cases found", file=sys.stderr)
        return 2
    results = _run_all(cases, args.show)
    failures = [f for r in results for f in r.failures]
    errors = [r for r in results if r.error]
    skipped = [r for r in results if r.skipped]
    # `--require-driver` turns a skip into a verdict on the RUN. Reporting a
    # case by name and exiting 0 is right where nobody could have run it (the
    # Python CI matrix has no Rust toolchain, and none has Node unless it
    # installed one); it is wrong where a caller built a driver so that those
    # cases would run, because a driver that went missing would leave a green
    # summary over cases nobody recorded. Any skip counts, not only a missing
    # cargo driver: the flag says every case ran, so a reason invented later
    # needs no second flag to be caught.
    unrun = (f"--require-driver was given and {len(skipped)} case(s) "
             "could not run") if args.require_driver and skipped else None
    if args.json:
        _report_json(results, failures, skipped, errors, args, unrun)
    else:
        _report_text(results, failures, skipped, errors, unrun)
    return 1 if (failures or errors or unrun) else 0


if __name__ == "__main__":
    raise SystemExit(main())
