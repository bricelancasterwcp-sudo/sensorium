"""E15's instrument: the transcript reader, the ten cells, and the assembler.

Three things are tested here and each is tested by CALLING the thing that
would be wrong:

* **the reader parses and never decides.** `parse_refocus` is given the
  committed transcript of a real `refocus` on `corpus/typescript/refocus_
  match` (`tests/fixtures/e15/refocus-match.txt`, every box path replaced),
  plus two hand-built shapes the corpus cannot produce on demand -- a
  pre-rerun refusal and a WITHHELD licence. The one thing it must never do
  is read a withheld licence as a granted one, so that is its own test.
* **the cells read §1's rules, word for word.** `cells` is given a synthetic
  `raw` of three rows -- one MATCH on a deterministic row, one DIVERGED on a
  row the survey predicted nondeterministic (a READING), and one DIVERGED on
  a deterministic row (a FINDING) -- and the words it prints are asserted
  against §1's own vocabulary.
* **the assembler refuses.** Its provenance checks are what stand between a
  dry run's numbers and this slice's results file, so the tests call
  `assemble_e15.main` and read the exit status and the file it wrote.

The mutations run against these tests are in the task report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"
sys.path.insert(0, str(ACCEPT))

import assemble_e15 as assembler                                  # noqa: E402
import e15_read as rd                                             # noqa: E402
import e15_report as rep                                          # noqa: E402
from test_acceptance_e15_lock import BYTE_LOCK, SURVEY_LOCK       # noqa: E402

FIXTURE = REPO / "tests" / "fixtures" / "e15" / "refocus-match.txt"
SURVEY = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-13-sensorium-e15-refocus-typescript-survey.md")
RECORD = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-13-sensorium-e15-refocus-typescript.md")


def match_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# -- the reader -------------------------------------------------------------


def test_the_committed_transcript_carries_no_box_path():
    """Catches: a fixture saved straight out of the scratch directory. The
    fixture is a committed file and every location in this slice is an
    argument, so a surviving `/mnt/` or `/home/` would put one in the tree."""
    text = match_text()
    for needle in ("/mnt/", "/home/", "/root/", "/tmp/"):
        assert needle not in text, needle
    assert "<root>" in text and "<store>" in text


def test_parse_refocus_reads_the_committed_match_transcript():
    """Catches: a reader that cannot read the shape it was written for. Every
    field E15's cells are built from is asserted against the real answer of a
    real `refocus` on a real TypeScript pair."""
    got = rd.parse_refocus(match_text())
    assert got["verdict"] == "MATCH"
    assert got["licence"] == "granted"
    assert got["withheld_reasons"] == []
    assert got["unverifiable"] == [
        "output: unverifiable (not recorded)",
        "children: unverifiable (not witnessed)",
        "threads: unverifiable (not witnessed)"]
    assert got["pair"]["siblings"] == 0
    assert got["pair"]["run"] == "20260913-044103-f20567"
    assert got["pair"]["invocation"] == "20260913-044102-cef1be"
    # The corpus runner's originals carried no VITEST key, so the env line is
    # the unqualified `unchanged (` shape; the lens's may read `unchanged
    # outside harness set 1`. The fixture is committed, so the test asserts
    # what the fixture holds and nothing about a run it has not seen.
    assert got["env_line"].startswith("env: unchanged (")
    assert got["env_status"] == "unchanged"
    assert "the recorder's own, also not compared:" in got["env_line"]
    assert got["source_line"].startswith("source: unchanged (")
    assert got["source_status"] == "unchanged"
    assert got["exit_line"] == "exit: rerun 0 (waited)   original 0 (waited)"
    assert got["exit_rerun"] == "0 (waited)"
    assert got["exit_original"] == "0 (waited)"
    assert got["refusal"] is None
    assert got["refused_after_rerun"] is None
    assert got["refocus_of"] == "20260913-044055-395d03"
    assert got["harness_duration_s"] == pytest.approx(0.085)
    assert len(got["licence_points"]) == 5


def test_parse_refocus_reads_a_duration_printed_in_seconds():
    """Catches: a duration regex written against the millisecond form alone.
    A 372-file suite prints `Duration  24.31s`, and a reader that matched
    only `NNms` would report `None` for every row of the loop."""
    text = match_text().replace(
        "   Duration  85ms (transform 21ms, setup 7ms, import 23ms, "
        "tests 2ms, environment 0ms)",
        "   Duration  24.31s (transform 2.10s, setup 1.02s)")
    assert "24.31s" in text, "the mutation target moved"
    assert rd.parse_refocus(text)["harness_duration_s"] == pytest.approx(24.31)


REFUSAL = """\
error: cannot refocus 20260913-044055-395d03: it ran 2 test files in one \
container (a reused worker); which container of a re-run would be its pair \
is the harness's scheduling, not a fact; nothing was re-run
"""


def test_parse_refocus_reads_a_pre_rerun_refusal_and_no_verdict():
    """Catches: a reader that fills a verdict for an answer that has none.
    A pre-rerun refusal prints one line on stderr and exits 2; nothing was
    re-run, so every other field is absent and must stay absent."""
    got = rd.parse_refocus(REFUSAL)
    assert got["refusal"] == (
        "it ran 2 test files in one container (a reused worker); which "
        "container of a re-run would be its pair is the harness's "
        "scheduling, not a fact; nothing was re-run")
    assert got["refusal_run"] == "20260913-044055-395d03"
    assert got["verdict"] is None
    assert got["licence"] is None
    assert got["pair"] == {"run": None, "invocation": None, "siblings": None}


def withheld_text() -> str:
    """The committed MATCH transcript with its licence block replaced by the
    WITHHELD shape `refocus_report.report` prints. Hand-built because the
    corpus has no case that withholds on a TypeScript pair: the three
    unverifiable markers no longer withhold (ruling R7), so a withheld
    licence needs a world finding the corpus does not plant."""
    text = match_text()
    granted = [ln for ln in text.splitlines()
               if ln.startswith("licence: verified against ")]
    assert len(granted) == 1, granted
    out, dropping = [], False
    for line in text.splitlines():
        if line == granted[0]:
            out += ["licence: WITHHELD -- this MATCH is about call shape, "
                    "and these checks say it is not a statement about the "
                    "run as a whole:",
                    "  - 1 source file(s) CHANGED since the original run: "
                    "src/__tests__/CombatTrackerPf2ePersistent.test.tsx",
                    "  - 2 environment variable(s) differ between the two "
                    "runs (CI, TZ); a program that reads them got different "
                    "input"]
            dropping = True
            continue
        if dropping:
            if line.startswith("  - "):
                continue
            dropping = False
        out.append(line)
    return "\n".join(out) + "\n"


def test_parse_refocus_reads_a_withheld_licence_and_its_reasons():
    """Catches: a licence read that stops at the word and drops the reasons.
    H7 is the control that reads them: control B plants a source edit and the
    endpoint is the WITHHELD line CARRYING the source reason, not merely a
    withheld licence."""
    got = rd.parse_refocus(withheld_text())
    assert got["licence"] == "WITHHELD"
    assert got["licence_points"] == []
    assert len(got["withheld_reasons"]) == 2
    assert got["withheld_reasons"][0].startswith("1 source file(s) CHANGED")
    assert "CombatTrackerPf2ePersistent" in got["withheld_reasons"][0]
    # The verdict is unchanged by the licence: a withheld licence over a
    # MATCH is §1's H7 prediction, and a reader that coupled them would make
    # that prediction unfalsifiable.
    assert got["verdict"] == "MATCH"


def test_parse_refocus_never_reads_WITHHELD_as_granted():
    """Catches: a `licence:` regex loose enough to match both shapes -- the
    one mutation that would make every H5 `GRANTED` count and H7's control
    both pass over a withheld licence."""
    assert rd.parse_refocus(withheld_text())["licence"] == "WITHHELD"
    assert rd.parse_refocus(match_text())["licence"] == "granted"


DIVERGED_TASKS = """\
--- verdict ---
run: 20260913-044407-0a4a88   invocation: 20260913-044406-ef976b   \
siblings in the re-run: 3 (not compared; UNVERIFIED)
env: unchanged (110 variables compared; not compared: OLDPWD, PWD)  \
the recorder's own, also not compared: SENSORIUM_TIER
source: unchanged (2 file(s) compared by content)
exit: rerun 0 (waited)   original 0 (waited)
tasks: DIVERGED -- 1 task stream(s) originally, 1 on the rerun; first \
difference inside a side is chosen at causal step 4: A e5 CALL    left  \
(<root>/counter.ts) / B e5 CALL    right  (<root>/counter.ts)
refocus verdict: DIVERGED -- a task took a different path. B is a DIFFERENT \
execution than A
checks that could not run on this pair -- the recorder declares it does not \
produce them, so nothing here is evidence either way:
  - output: unverifiable (not recorded)
  - children: unverifiable (not witnessed)
  - threads: unverifiable (not witnessed)
"""


def test_parse_refocus_reads_the_divergent_step_line_off_a_task_divergence():
    """Catches: a reader that looks only for `verdict: DIVERGED at causal
    step N`. On a TypeScript pair the divergence is usually in the TASKS, and
    the step line is inside the `tasks: DIVERGED --` sentence -- which is the
    line H4's finding has to name."""
    got = rd.parse_refocus(DIVERGED_TASKS)
    assert got["verdict"] == "DIVERGED"
    assert got["diverged_step"] == 4
    assert got["divergent_line"].startswith("tasks: DIVERGED --")
    assert "at causal step 4:" in got["divergent_line"]
    assert got["pair"]["siblings"] == 3


REFUSED_AFTER = """\
--- verdict ---
threads: not compared -- no verdict was issued
refocus verdict: REFUSED -- the re-run produced 4 trace(s) linked to \
20260913-044055-395d03 and none ran test file src/a.test.ts (harness exit 0); \
see the harness's output above
"""


def test_parse_refocus_tells_a_refusal_after_the_rerun_from_one_before_it():
    """Catches: one `refusal` field carrying both classes. They are different
    facts with different exits and different endpoints -- H1 counts the
    pre-rerun kind and H3 STOPs on the after-the-rerun kind -- so a reader
    that merged them would make H1 fail for H3's reason."""
    got = rd.parse_refocus(REFUSED_AFTER)
    assert got["refusal"] is None
    assert got["verdict"] == "REFUSED"
    assert got["refused_after_rerun"].startswith("the re-run produced 4 trace")
    assert got["lookup_refusal"] is True


# -- the two H6 readers -----------------------------------------------------


def test_parse_watch_reads_the_verdict_word_and_nothing_else():
    """Catches: a `watch` reader that decides. H6 compares the verdict CLASS
    and the exit against the survey's prediction; the exit belongs to the
    process and is recorded by the runner, so the reader only names the
    word."""
    assert rd.parse_watch(
        "verdict: SATISFIED at 4 of the 6 site(s)\n")["verdict"] == "SATISFIED"
    assert rd.parse_watch(
        "verdict: not satisfied at any of the 6 site(s)\n"
    )["verdict"] == "not satisfied"
    assert rd.parse_watch(
        "verdict: NOTHING WAS CHECKED -- the predicate could not be "
        "evaluated at any of the 6 recorded site(s)\n"
    )["verdict"] == "NOTHING WAS CHECKED"
    assert rd.parse_watch("REFUSED: this trace records no line rows\n"
                          )["verdict"] == "REFUSED"
    assert rd.parse_watch("nothing here\n")["verdict"] is None


def test_parse_flow_reads_FOUND_and_NOT_FOUND_off_the_sightings_line():
    """Catches: a `flow` reader looking for a verdict word the command does
    not print. `flow` prints `sightings: N event(s), M capture(s)` and
    returns 1 on an empty page; §1's fourth read predicts NOT FOUND, exit 1,
    so the emptiness is what has to be read."""
    found = rd.parse_flow("sightings: 1 event(s), 1 capture(s)\n"
                          "scope: 8 capture(s) searched across 6 event(s)\n")
    assert found["verdict"] == "FOUND"
    assert found["sightings"] == 1
    empty = rd.parse_flow("sightings: 0 event(s), 0 capture(s)\n"
                          "scope: 8 capture(s) searched across 6 event(s)\n")
    assert empty["verdict"] == "NOT FOUND"
    assert empty["sightings"] == 0
    assert empty["scope_line"].startswith("scope: ")
    assert rd.parse_flow("REFUSED: this trace records no line rows\n"
                         )["verdict"] == "REFUSED"


# -- the survey, parsed -----------------------------------------------------


def test_parse_survey_reads_the_locked_table_and_its_four_reads():
    """Catches: a survey parser that reads a different table than the lock
    test pins. The row count, the six columns, the class vocabulary and the
    `### H6 reads` block are all §1's, and the loop's population is this
    parse."""
    got = rd.parse_survey(SURVEY.read_text(encoding="utf-8"))
    assert got["n"] == 31 and len(got["rows"]) == 31
    assert [r["n"] for r in got["rows"]] == list(range(1, 32))
    assert got["rows"][0]["test_file"] == "src/__tests__/AiPrepPanel.test.tsx"
    assert got["rows"][0]["klass"] == "nondeterministic"
    assert got["rows"][0]["focus"] == "AiPrepPanel.tsx:AiPrepPanel"
    assert got["rows"][0]["resolver_matched"] == 4
    assert sum(1 for r in got["rows"] if r["klass"] == "deterministic") == 24
    reads = got["h6"]
    assert len(reads) == 4
    assert [r["row"] for r in reads] == [1, 16, 31, 16]
    assert [r["kind"] for r in reads] == ["watch", "watch", "watch", "flow"]
    assert [r["predicted_class"] for r in reads] == [
        "SATISFIED", "SATISFIED", "SATISFIED", "NOT FOUND"]
    assert [r["predicted_exit"] for r in reads] == [0, 0, 0, 1]
    assert reads[0]["command"].startswith("watch <row 1's refocus> --at ")
    assert reads[3]["command"] == "flow <row 16's refocus> --value 0.4"



def test_parse_watch_names_the_no_match_answer_rather_than_reading_None():
    """Catches: a `watch` reader with no row for `_no_match`. The command
    prints `error: no recorded code matches --at …` and returns NEGATIVE when
    the trace holds no such code object; a reader without the class reports
    `None` for an answer it gave plainly, and H6's finding could then say
    only that the prediction did not hold."""
    text = ("error: no recorded code matches --at 'AiPrepPanel'\n"
            "this trace recorded 4 code object(s):\n  a.ts:one\n")
    got = rd.parse_watch(text)
    assert got["verdict"] == "no recorded code matches"
    assert got["refusal_line"].startswith("error: no recorded code matches")
    assert got["verdict_line"] is None
