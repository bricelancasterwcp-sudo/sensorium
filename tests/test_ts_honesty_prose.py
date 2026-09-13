"""The honesty ledgers' falsifiers are read as structure, not as a list.

A promise moved OUT of `HONESTY.md` is still a promise a test reads (design
§6.3). `typescript/HONESTY.md` §10 became `typescript/HONESTY-BLIND-SPOTS.md`
2026-09-10 and §9 became `typescript/HONESTY-COST.md` 2026-09-11, both on the
precedent `rust/HONESTY-BLIND-SPOTS.md` set 2026-09-05 -- three files of
promises that, until this test, no test read at all.

What is pinned here is the SHAPE the entries already have, never a
hard-coded inventory: the checkers below enumerate whatever the file holds
today, so an entry ADDED tomorrow is checked tomorrow without editing this
file, and an entry whose falsifier rots is named by the entry's own number.
Counts are asserted only as floors (`>=`), for the same reason -- an exact
count would make every new blind spot a failing test, which is how a ledger
learns to stop growing.

**A failure here is drift in the DOCUMENT, not in this test.** The entry
names a file that moved or a test title that was renamed; the fix is to
correct the ledger so the falsifier points at what falsifies it today.

The three dialects, and how a falsifier is classified:

* a **path** -- a token with a `/` or a suffix, resolved against the repo
  root, or against the ledger's own directory when it starts `../`. It must
  exist. A `{a,b}` brace list is every path it spells; a `*` glob is a
  pattern and must match at least one file anywhere in the tree (Rust's
  `tests/common/*.rs` is a per-crate cargo convention, not one path).
* an **acceptance endpoint** -- `E2'`, `E6-TS'`, `H6` and their kin, which
  are names of measurements rather than files. The record that measured one
  is a file under `docs/superpowers/acceptance/`, so the endpoint is checked
  by its name appearing in some record there.
* a **title** -- the parenthesised note a citation may carry, italic
  (`(*a statement of the finally mints its row*)`) or backticked
  (``(`stack pops at yield`)``). Its text must appear verbatim in the file
  the citation names, which is what makes a renamed test a failure here.
"""
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[1]

TS_BLIND_SPOTS = REPO / "typescript" / "HONESTY-BLIND-SPOTS.md"
TS_COST = REPO / "typescript" / "HONESTY-COST.md"
RUST_BLIND_SPOTS = REPO / "rust" / "HONESTY-BLIND-SPOTS.md"

# `1. **` opens an entry; `2. ~~**` opens a struck one. Both are entries --
# a struck item keeps its number precisely so a reader who last met the list
# under an older version sees which hole closed (the files say so).
_ENTRY = re.compile(r"(?m)^\s*(\d+)\. (~~)?\*\*")

# Both ledgers' vocabulary for the same clause. `rust/HONESTY-BLIND-SPOTS.md`
# says *Falsified by*; TypeScript says *Falsifier:* -- except item 39, which
# is Rust item 32's twin and was written in Rust's dialect.
_FALSIFIER = re.compile(r"\*(?:Falsifier:|Falsified by)\*")

# A citation is a backticked token plus the parenthesised note that follows
# it directly. The note may itself contain one level of parentheses -- blind
# spot 38 cites a title that ends "(blind spot 38 closed)".
_CITATION = re.compile(r"`([^`]+)`(?:\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\))?")

_ENDPOINT = re.compile(r"^E\d+(?:-TS)?[′″‴]*$|^H\d+$")

# The prefixes that make a Rust entry's backtick a citation of a test rather
# than prose: the workspace's own test dirs, the top-level pytest suite, and
# the corpus.
_RUST_TEST_PREFIXES = ("tests/", "corpus/")


class Entry:
    """One numbered item of a blind-spots ledger."""

    def __init__(self, number: int, struck: bool, body: str):
        self.number = number
        self.struck = struck
        self.body = body

    @property
    def falsifier(self) -> str | None:
        """Everything after the LAST *Falsifier:* marker in the entry.

        The last, not the first: a struck entry carries its original
        falsifier and then the closing note's, and the closing note's is
        the one that describes the tree as it stands.
        """
        marks = list(_FALSIFIER.finditer(self.body))
        return self.body[marks[-1].end():] if marks else None

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"<entry {self.number}{' struck' if self.struck else ''}>"


def entries(path: Path) -> list[Entry]:
    """Every numbered entry of a ledger, in file order, struck ones included.

    The body of an entry runs to the start of the next one, so a closing
    note that follows a struck entry's own text belongs to that entry.
    """
    text = path.read_text()
    marks = [(m.start(), int(m.group(1)), bool(m.group(2)))
             for m in _ENTRY.finditer(text)]
    out = []
    for i, (start, number, struck) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append(Entry(number, struck, " ".join(text[start:end].split())))
    return out


def _spellings(token: str) -> list[str]:
    """A `{a,b,c}` brace list is every path it spells, one each.

    Item 27 cites four corpus cases as
    `corpus/typescript/{translated,untraced_catcher,...}`, wrapped across
    lines, so the alternatives are stripped of the whitespace the wrap left.
    """
    brace = re.search(r"\{([^}]*)\}", token)
    if not brace:
        return [token]
    return [token[:brace.start()] + alt.strip() + token[brace.end():]
            for alt in brace.group(1).split(",")]


def _looks_like_a_path(token: str) -> bool:
    return "/" in token or re.search(r"\.\w+$", token) is not None


def _resolve(token: str, doc_dir: Path) -> Path:
    """Repo-root-relative, unless it starts `../` -- then relative to the
    ledger's own directory, which is how both files spell a path that
    leaves their subtree."""
    token = token.rstrip("/")
    if token.startswith("../"):
        return (doc_dir / token).resolve()
    return REPO / token


def _exists(token: str, doc_dir: Path) -> bool:
    if any(c in token for c in "*?["):
        pattern = token.lstrip("./")
        return any(REPO.glob(pattern)) or any(REPO.glob("**/" + pattern))
    return _resolve(token, doc_dir).exists()


def _haystack(path: Path) -> str:
    """The text a title must appear in.

    A citation may name a DIRECTORY -- `typescript/test/golden/` is the
    goldens as a body of evidence, not one file -- and then the title has
    to be findable in some file under it.
    """
    if path.is_file():
        return path.read_text(errors="replace")
    return "\n".join(p.read_text(errors="replace")
                     for p in sorted(path.rglob("*")) if p.is_file())


def _titles(note: str) -> list[str]:
    """The title(s) a parenthesised note carries: italic first, then
    backticked. A note with neither (item 28's "the present row and the
    absent value, pinned from both sides") states WHY the citation
    falsifies and pins nothing further, so it yields none."""
    return re.findall(r"\*([^*]+)\*", note) + re.findall(r"`([^`]+)`", note)


def _acceptance_text() -> str:
    records = REPO / "docs" / "superpowers" / "acceptance"
    return "\n".join(p.read_text(errors="replace")
                     for p in sorted(records.rglob("*")) if p.is_file())


def falsifier_problems(path: Path, doc_dir: Path | None = None) -> list[str]:
    """Every way the live entries of a blind-spots ledger fail to point at
    what falsifies them, as lines a failure message can carry.

    Takes the ledger's path so a mutated COPY can be checked by exactly
    this code -- which is what proves the checker bites (see the mutation
    tests at the foot of this file).
    """
    doc_dir = doc_dir or path.parent
    acceptance = None
    problems = []
    for entry in entries(path):
        if entry.struck:
            continue
        tail = entry.falsifier
        if tail is None:
            problems.append(f"item {entry.number}: names no falsifier")
            continue
        for match in _CITATION.finditer(tail):
            token, note = match.group(1), match.group(2)
            for spelling in _spellings(token):
                if _ENDPOINT.match(spelling):
                    if acceptance is None:
                        acceptance = _acceptance_text()
                    if spelling not in acceptance:
                        problems.append(
                            f"item {entry.number}: endpoint {spelling} is "
                            f"named by no acceptance record")
                    continue
                if not _looks_like_a_path(spelling):
                    continue
                if not _exists(spelling, doc_dir):
                    problems.append(
                        f"item {entry.number}: {spelling} does not exist")
                    continue
                if not note:
                    continue
                hay = _haystack(_resolve(spelling, doc_dir))
                for title in _titles(note):
                    if title not in hay:
                        problems.append(
                            f"item {entry.number}: {spelling} does not "
                            f"contain the title {title!r}")
    return problems


# --------------------------------------------------------------------------
# typescript/HONESTY-BLIND-SPOTS.md
# --------------------------------------------------------------------------

def test_the_typescript_ledger_parses_into_numbered_entries():
    """The floor is what the file held when this test was written (39
    entries, 33 of them live), asserted as a floor so the next rung's
    blind spot does not fail this test for existing."""
    items = entries(TS_BLIND_SPOTS)
    assert len(items) >= 39, len(items)
    assert [e.number for e in items] == sorted(e.number for e in items)
    assert len([e for e in items if not e.struck]) >= 33


def test_every_live_typescript_entry_names_a_falsifier():
    """The claim each entry makes is that this is the whole of the hole;
    the falsifier is what could show it is not. An entry without one
    promises something nothing can contradict."""
    missing = [e.number for e in entries(TS_BLIND_SPOTS)
               if not e.struck and e.falsifier is None]
    assert missing == [], missing


def test_every_typescript_falsifier_points_at_what_exists_today():
    """Paths exist, endpoints are named by a record, titles are in the
    files that carry them. A failure is drift in the LEDGER."""
    problems = falsifier_problems(TS_BLIND_SPOTS)
    assert problems == [], "\n".join(problems)


def test_the_struck_typescript_entries_are_skipped_by_name():
    """Struck entries keep their numbers and their old falsifiers, which
    may name a shape the tree no longer has -- so they are skipped, and
    the skip is PRINTED rather than silent (`pytest -s`, or any failure in
    this file), because a reader of this suite should be able to see which
    promises stopped being checked.
    """
    struck = [e.number for e in entries(TS_BLIND_SPOTS) if e.struck]
    print("skipped (struck) in typescript/HONESTY-BLIND-SPOTS.md: "
          + ", ".join(str(n) for n in struck))
    assert struck, "no entry is struck -- has the strike notation changed?"
    # Every struck entry is struck where it stands: none was deleted, so
    # the numbering has no holes.
    numbers = [e.number for e in entries(TS_BLIND_SPOTS)]
    assert numbers == list(range(1, len(numbers) + 1)), numbers


# --------------------------------------------------------------------------
# typescript/HONESTY-COST.md
# --------------------------------------------------------------------------

def test_every_acceptance_record_the_cost_ledger_cites_exists():
    """§9 is the section that grows at every rung, and what it grows by is
    a Measured block citing the record that measured it. A citation that
    no longer resolves is a cost number with no evidence behind it."""
    text = TS_COST.read_text()
    cited = sorted({t for t in re.findall(r"`([^`]+)`", text)
                    if "docs/superpowers/acceptance/" in t})
    assert len(cited) >= 3, cited
    missing = [t for t in cited if not _exists(t, TS_COST.parent)]
    assert missing == [], missing


# --------------------------------------------------------------------------
# rust/HONESTY-BLIND-SPOTS.md
# --------------------------------------------------------------------------

def _rust_cited_tests(entry: Entry) -> list[str]:
    """The test paths one Rust entry cites.

    Rust's entries do not all carry a *Falsified by* clause -- several say
    in prose that no case in the tree pins the shape -- so the citation is
    read from the whole entry, narrowed to the prefixes that mean "a test
    of this repo": the workspace crates' own `tests/` dirs, the top-level
    pytest suite, and the corpus.
    """
    out = []
    for token in re.findall(r"`([^`]+)`", entry.body):
        if "<" in token or ">" in token or " " in token.strip():
            continue  # a command line or a prose fragment, not a path
        if token.startswith(_RUST_TEST_PREFIXES) or (
                token.startswith("rust/") and "/tests/" in token):
            out.append(token)
    return out


def test_the_rust_ledger_parses_into_numbered_entries():
    items = entries(RUST_BLIND_SPOTS)
    assert len(items) >= 33, len(items)
    assert [e.number for e in items] == list(range(1, len(items) + 1))


def test_every_rust_test_path_exists_and_every_named_test_is_in_its_file():
    """Rust cites a test either as a path or as `<path>::<test fn>`. The
    `::` form is the same promise the TypeScript ledger makes with a
    parenthesised title: the named test must still be in the file."""
    problems = []
    for entry in entries(RUST_BLIND_SPOTS):
        for token in _rust_cited_tests(entry):
            path, _, name = token.partition("::")
            for spelling in _spellings(path):
                if not _exists(spelling, RUST_BLIND_SPOTS.parent):
                    problems.append(
                        f"item {entry.number}: {spelling} does not exist")
                elif name and name not in _haystack(
                        _resolve(spelling, RUST_BLIND_SPOTS.parent)):
                    problems.append(
                        f"item {entry.number}: {spelling} has no {name}")
    assert problems == [], "\n".join(problems)


def test_the_rust_entries_citing_no_test_are_listed():
    """Listed, not skipped (design §6.3). Several of these say in their own
    words that no case in the tree pins the shape -- which is an honest
    entry, and exactly the kind this list keeps visible."""
    items = entries(RUST_BLIND_SPOTS)
    uncited = [e.number for e in items if not _rust_cited_tests(e)]
    print("rust/HONESTY-BLIND-SPOTS.md entries citing no test path: "
          + ", ".join(str(n) for n in uncited))
    assert len(uncited) < len(items), "no entry cites a test at all"


# --------------------------------------------------------------------------
# The checkers bite: a mutated COPY, never the tracked file
# --------------------------------------------------------------------------

def _mutant(tmp_path: Path, old: str, new: str) -> Path:
    """`typescript/HONESTY-BLIND-SPOTS.md` with one substitution, written
    where a failing assertion cannot damage the tracked ledger."""
    text = TS_BLIND_SPOTS.read_text()
    assert text.count(old) == 1, (old, text.count(old))
    copy = tmp_path / TS_BLIND_SPOTS.name
    copy.write_text(text.replace(old, new))
    return copy


def test_a_renamed_test_title_is_caught(tmp_path):
    """Item 39 cites `bindings.test.mjs` by the title of the test that
    falsifies it. Rename the test and forget the ledger, and the ledger
    still points somewhere -- which is the drift this file exists to
    catch, so the checker must fail on it and not on the path."""
    copy = _mutant(
        tmp_path,
        "declaredIn a block that SHADOWS an outer binding still lists the name",
        "declaredIn a block that SHADOWS an outer binding lists nothing")
    problems = falsifier_problems(copy, doc_dir=TS_BLIND_SPOTS.parent)
    assert len(problems) == 1, problems
    assert "item 39" in problems[0] and "does not contain the title" in problems[0]


def test_a_moved_falsifier_file_is_caught(tmp_path):
    """The other half: the title is untouched and the file it names is
    not there."""
    copy = _mutant(tmp_path, "corpus/typescript/timer_callback_parentless",
                   "corpus/typescript/timer_callback_moved_away")
    problems = falsifier_problems(copy, doc_dir=TS_BLIND_SPOTS.parent)
    assert len(problems) == 1, problems
    assert ("item 14: corpus/typescript/timer_callback_moved_away does not "
            "exist") == problems[0]


def test_an_entry_that_names_no_falsifier_at_all_is_caught(tmp_path):
    """A promise nothing can contradict."""
    copy = _mutant(tmp_path, "*Falsifier:* `tests/test_ts_ingest.py`, `E0′`.",
                   "Nothing could show otherwise.")
    problems = falsifier_problems(copy, doc_dir=TS_BLIND_SPOTS.parent)
    assert problems == ["item 4: names no falsifier"], problems


def test_an_unmeasured_endpoint_is_caught(tmp_path):
    """An endpoint is a measurement's name; if no record carries it, the
    entry cites evidence that was never written down."""
    copy = _mutant(tmp_path, "`corpus/typescript/object_identity`, `E12` H6,",
                   "`corpus/typescript/object_identity`, `E99` H6,")
    problems = falsifier_problems(copy, doc_dir=TS_BLIND_SPOTS.parent)
    assert len(problems) == 1, problems
    assert "endpoint E99 is named by no acceptance record" in problems[0]
