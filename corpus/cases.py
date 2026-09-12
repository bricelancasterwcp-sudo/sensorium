"""A corpus case, and the closed schema it is loaded under.

Split out of `run_corpus` when the TypeScript cases pushed that module past
the repo's 800-line ceiling, at the seam it already had: this half decides
what a case IS and refuses a file that does not say so, and `run_corpus`
decides what happens when one is run. `run_corpus` re-exports every name
here that a caller outside the corpus already imported from it, so the
split is invisible to them.

THREE RECORDERS, THREE SETS OF KEYS
-----------------------------------
`program:` picks the recorder, and each recorder has keys the other two
never receive: `argv` is the Python recorder's, `cargo_args` is the Rust
driver's, `harness_args` is the TypeScript driver's. Every one of them is
REFUSED on a case that runs another recorder rather than ignored, because
an ignored key is a case that silently stops testing what it says it tests
-- `record: {focus: ...}` on a CARGO case would read as a line-focused
recording and produce a call-tier one, with every question still passing
because none of them can tell.

`record` is the ONE key two recorders share, and only in part: the Python
recorder takes `focus` and `window`, `sensorium ts run` has `--focus` and
no `--window`, and the Rust driver has neither. So `record: {focus: [...]}`
is admitted on a vitest case and `window` under it is refused by name --
"the vitest driver takes focus" and "the vitest driver takes record" are
different rules, and only the first one is true. `run_corpus`'s own
docstring says what each recorder then does with its keys.

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


"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ALLOWED_Q_KEYS = {"id", "ask", "truth", "why_logs_fail", "command",
                  "expect_contains", "expect_line", "expect_count",
                  "expect_absent", "expect_exit", "depends_on"}
ALLOWED_TOP_KEYS = {"program", "argv", "record", "second_run", "questions",
                    "cargo_args", "harness_args"}
#: `program:` value that selects the Rust recorder instead of the Python one.
CARGO = "cargo"
#: ...and the one that selects the TypeScript recorder.
VITEST = "vitest"
#: Subdirectory of the corpus holding the cargo cases. Their names carry it
#: (`rust/panic`), so a Rust port and its Python original never collide in
#: `--only`, in the per-case report line, or in the (case, question id)
#: uniqueness the suite checks.
RUST_DIR = "rust"
#: ...and the one holding the vitest cases, which is ALSO the vitest project
#: they all run inside (see the module docstring).
TS_DIR = "typescript"
#: The token every vitest case's `harness_args` starts with, because
#: `_record_vitest` re-issues it: a case is recorded once and `vitest watch`
#: would never return. Checked at load time so a case that spelled something
#: else is refused by name rather than silently recorded as a `run`.
TS_HARNESS_WORD = "run"
# `expect_contains` is deliberately NOT in this list, unlike the original
# schema. Requiring it by name while allowing it to be `[]` makes a question
# that asserts nothing pass validation, which is the exact failure this
# harness cannot have. The rule that replaces it -- at least one non-empty
# asserting key -- is strictly stronger, and lets a question that is properly
# expressed as a line group say so instead of carrying a token substring.
REQUIRED_Q_KEYS = ("id", "ask", "truth", "why_logs_fail", "command")
ASSERTING_KEYS = ("expect_contains", "expect_line", "expect_count")


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
    #: argv after `vitest`, for a `program: vitest` case.
    harness_args: list = field(default_factory=list)

    @property
    def is_cargo(self) -> bool:
        return self.program == CARGO

    @property
    def is_vitest(self) -> bool:
        return self.program == VITEST


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
    """The keys that mean different things to the three recorders.

    Each recorder ignores the other two's keys, and an ignored key is the
    failure this module refuses everywhere else: `record: {focus: …}` on a
    cargo case would read as a line-focused recording and produce a
    call-tier one, with every question still passing because none of them
    can tell.
    """
    extra = set(spec) - ALLOWED_TOP_KEYS
    if extra:
        raise ValueError(f"{where}: unknown keys {sorted(extra)}")
    if "program" not in spec or "questions" not in spec:
        raise ValueError(f"{where}: needs both 'program' and 'questions'")
    program = spec["program"]
    if program == CARGO:
        _validate_cargo(where, spec)
    elif program == VITEST:
        _validate_vitest(where, spec)
    else:
        _validate_python(where, spec)


def _validate_python(where: str, spec: dict) -> None:
    """The two driver keys the Python recorder never receives.

    The `cargo_args` sentence is the one this rule has always printed, word
    for word: `tests/test_corpus.py` reads it, and a message rewritten in
    passing is a test that stops checking the thing it names.
    """
    if "cargo_args" in spec:
        raise ValueError(f"{where}: cargo_args belongs to a "
                         f"'program: {CARGO}' case; this one runs "
                         f"{spec['program']!r} through the Python "
                         "recorder, which never sees it")
    if "harness_args" in spec:
        raise ValueError(f"{where}: harness_args belongs to a "
                         f"'program: {VITEST}' case; this one runs "
                         f"{spec['program']!r} through the Python "
                         "recorder, which never sees it")


def _validate_cargo(where: str, spec: dict) -> None:
    for key in ("record", "argv"):
        if key in spec:
            raise ValueError(
                f"{where}: {key!r} is the Python recorder's key and the "
                f"'{CARGO}' driver never receives it; a cargo case says what "
                "it runs in cargo_args (arguments for the program itself go "
                "after `--`)")
    if "harness_args" in spec:
        raise ValueError(
            f"{where}: harness_args is the '{VITEST}' driver's key and the "
            f"'{CARGO}' driver never receives it")
    args = spec.get("cargo_args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"{where}: a 'program: {CARGO}' case needs a "
                         "non-empty cargo_args list (the argv after "
                         "`cargo sensorium`)")
    second = spec.get("second_run")
    if second is not None and not second.get("cargo_args"):
        raise ValueError(f"{where}: second_run of a '{CARGO}' case needs its "
                         "own cargo_args")


def _validate_vitest(where: str, spec: dict) -> None:
    """`harness_args` is the whole of what a vitest case says it RUNS.

    ...and `record: {focus: [...]}` is the one thing it may say about how
    that run was RECORDED. `sensorium ts run --focus <spec>` is the same
    flag with the same spelling as the Python recorder's, so a vitest case
    declares a line-focused recording the same way a Python case does, and
    `_record_vitest` turns each entry into its own `--focus` before the
    `--`. Everything else under `record` -- `window` above all -- is the
    Python recorder's alone: `sensorium ts run` has no such flag, so a case
    carrying one would record with the key silently dropped and every
    question would still pass.

    `argv` is refused whole for the same reason it always was, and
    `cargo_args` is the Rust driver's. The first harness token is checked
    because `_record_vitest` re-issues it: a case is recorded once, so
    `watch` would never return, and a case that spelled one and was silently
    run as the other would be a case testing something nobody wrote.
    """
    if "argv" in spec:
        raise ValueError(
            f"{where}: 'argv' is the Python recorder's key and the "
            f"'{VITEST}' driver never receives it; a vitest case says "
            "what it runs in harness_args (the tokens after `vitest`)")
    _check_record(where, spec.get("record"))
    if "cargo_args" in spec:
        raise ValueError(
            f"{where}: cargo_args is the '{CARGO}' driver's key and the "
            f"'{VITEST}' driver never receives it")
    _check_harness_args(where, spec.get("harness_args"), "")
    second = spec.get("second_run")
    if second is not None:
        _check_harness_args(where, second.get("harness_args"),
                            "second_run of a ")


def _check_record(where: str, record) -> None:
    """The one key a vitest case's `record` may carry, and its shape.

    A closed key set rather than "focus is read and the rest ignored": an
    ignored `window` is a case whose file says it recorded one window and
    whose recording covered everything, with every question still green.
    """
    if record is None:
        return
    if not isinstance(record, dict):
        raise ValueError(f"{where}: record must be a mapping holding one "
                         f"key, 'focus', for a 'program: {VITEST}' case")
    extra = sorted(set(record) - {"focus"})
    if extra:
        raise ValueError(
            f"{where}: record {', '.join(repr(k) for k in extra)} is the "
            f"Python recorder's and the '{VITEST}' driver never receives "
            "it; the only key a vitest case's record may carry is 'focus', "
            "whose entries become `sensorium ts run --focus <spec>`")
    focus = record.get("focus")
    if (not isinstance(focus, list) or not focus
            or not all(isinstance(f, str) for f in focus)):
        raise ValueError(
            f"{where}: record: focus must be a non-empty list of function "
            "specs (strings) -- <qualname>, <file>:<qualname>, or a "
            "container name, exactly as `sensorium ts run --focus` takes "
            f"them; got {focus!r}")


def _check_harness_args(where: str, args, prefix: str) -> None:
    if not isinstance(args, list) or not args:
        raise ValueError(f"{where}: a {prefix}'program: {VITEST}' case needs "
                         "a non-empty harness_args list (the tokens after "
                         "`vitest`)")
    if args[0] != TS_HARNESS_WORD:
        raise ValueError(
            f"{where}: harness_args starts {args[0]!r}, and this harness "
            f"re-issues {TS_HARNESS_WORD!r}: a corpus case records once, so "
            f"only `vitest {TS_HARNESS_WORD} …` is run here")


def _question_files(root: Path, only_dir: str | None = None) -> list[Path]:
    """Every case file: Python cases first, then cargo, then vitest.

    Two levels, not a recursive glob: a case is a directory of a corpus, and
    `rust/` and `typescript/` are the ones that hold another recorder's
    cases. A `**` glob would also sweep up anything a case's own build or
    `npm ci` left behind.

    `only_dir` names ONE of the three -- `rust`, `typescript`, or `.` for
    the Python cases at the top level -- so a CI job that has one recorder's
    driver can gate that recorder's cases with `--require-driver` while
    another recorder's is absent. It selects the GLOB rather than filtering
    the loaded cases, so a directory that holds no case file yields no case
    and the caller reports that, instead of a filter quietly matching
    nothing. `--only-dir` is an argparse `choices` on the CLI, so an unknown
    name never reaches here from a command line; a caller that passes one
    anyway gets the same empty list.
    """
    dirs = {".": "*/questions.yaml",
            RUST_DIR: f"{RUST_DIR}/*/questions.yaml",
            TS_DIR: f"{TS_DIR}/*/questions.yaml"}
    if only_dir is not None:
        globs = [dirs[only_dir]] if only_dir in dirs else []
    else:
        globs = list(dirs.values())
    return [f for g in globs for f in sorted(Path(root).glob(g))]


def load_cases(root: Path = ROOT, only_dir: str | None = None) -> list[Case]:
    cases = []
    for qfile in _question_files(Path(root), only_dir):
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
            if (spec["program"] not in (CARGO, VITEST)
                    and "$RUN2" in q["command"]
                    and spec.get("second_run") is None):
                raise ValueError(f"{qfile}:{q['id']}: uses $RUN2 but the case "
                                 "declares no second_run")
        cases.append(Case(str(qfile.parent.relative_to(Path(root))),
                          qfile.parent, spec["program"],
                          spec.get("argv", []), spec.get("record") or {},
                          spec.get("second_run"), spec["questions"],
                          spec.get("cargo_args") or [],
                          spec.get("harness_args") or []))
    return cases


