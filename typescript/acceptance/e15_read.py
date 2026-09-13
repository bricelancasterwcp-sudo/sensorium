"""E15's readers: one `refocus` answer, one `watch`, one `flow`, one survey.

Nothing here decides a verdict. Every function returns what the text SAYS,
under its own name, and `e15_report.cells` is where §1's rules turn those
facts into `holds`. The seam is the E4 family's own (`acceptance_e4_read.
parse_refocus` beside `acceptance_e4_cells`) and it exists for one reason: a
reader that decided would make an endpoint's rule depend on a regex nobody
reviewed as a rule.

WHY THIS IS NOT `acceptance_e4_read.parse_refocus`
--------------------------------------------------
That one reads a RUST pair's answer, and three of the lines E15 counts do
not exist there (ruling A2). A TypeScript refocus re-runs a whole vitest
INVOCATION and compares one container of it, so:

* the pair line carries a sibling count -- `run: <new>   invocation: <inv>
  siblings in the re-run: <n> (not compared; UNVERIFIED)` -- and H3 reads the
  linked count off it;
* the divergence is usually in the TASKS, and its step line sits inside the
  `tasks: DIVERGED -- …` sentence rather than on a `verdict: DIVERGED at
  causal step N` line of its own (measured on
  `corpus/typescript/refocus_diverged`);
* the harness prints its OWN duration -- vitest's `Duration  85ms` /
  `Duration  24.31s` -- and H9 subtracts it from the wall the runner
  measured, because neither `ts/driver._convert` nor `ts/ingest.ingest_dir`
  prints a conversion wall (controller check at 5bb41e4).

THE TWO REFUSALS ARE TWO FIELDS
--------------------------------
`refusal` is the PRE-RERUN one -- `error: cannot refocus <run>: <sentence>`
on stderr, exit 2, nothing re-run -- and it is H1's number. `refused_after_
rerun` is the one the pair lookup raises after a whole suite has run, exit 3,
and it is H3's STOP. One field carrying both would make H1 fail for H3's
reason, which is why they are read by two patterns that cannot match each
other's text.

A GRANTED LICENCE AND A WITHHELD ONE ARE TWO PATTERNS
------------------------------------------------------
`LICENCE_GRANTED` matches only `licence: verified against <run> on exactly
these points, and no others:` and `LICENCE_WITHHELD` only `licence:
WITHHELD`. A single loose pattern over `^licence: ` would read a withheld
licence as a granted one, and H5's GRANTED count and H7's whole control rest
on telling them apart.
"""
from __future__ import annotations

import re

# -- `sensorium refocus` ----------------------------------------------------

#: `refocus_typescript.run`, printed before the re-run: the original's id and
#: the driver argv as a person would type it.
REFOCUS_OF = re.compile(r"^refocus-of: (?P<run>\S+)\s+cmd: (?P<cmd>.*)$", re.M)
CWD_LINE = re.compile(r"^cwd: (?P<cwd>.*)$", re.M)
FOCUS_LINE = re.compile(r"^focus: (?P<focus>.*?)\s\s+window: (?P<window>.*)$",
                        re.M)

#: `refocus_world._source_state` and `refocus_licence.env_of`: three statuses
#: each, and the third is `unverifiable`, which is never counted as verified.
SOURCE_LINE = re.compile(r"^source: (?P<rest>.*)$", re.M)
ENV_LINE = re.compile(r"^env: (?P<rest>.*)$", re.M)
STATUSES = ("unchanged", "CHANGED", "unverifiable")

#: `refocus_typescript._verify`'s pair line -- the one line that says which
#: trace the verdict is about and how many it is NOT about (`siblings_note`).
PAIR_LINE = re.compile(r"^run: (?P<run>\S+)\s+invocation: (?P<inv>\S+)\s+"
                       r"siblings in the re-run: (?P<siblings>\d+)", re.M)
TRACE_LINE = re.compile(r"^trace: (?P<path>.*)$", re.M)
EXIT_LINE = re.compile(r"^exit: rerun (?P<rerun>.*?)\s\s+original "
                       r"(?P<original>.*?)\s*$", re.M)

#: `refocus_report.report`'s headline, in its three words. Anchored on
#: `refocus verdict:` and not on `verdict:`, which is `diff_cmd`'s own line
#: about the streams and says something narrower.
VERDICT = re.compile(r"^refocus verdict: (?P<word>MATCH|DIVERGED|REFUSED)\b"
                     r"(?P<rest>.*)$", re.M)

#: The two licence shapes, kept apart -- see the module docstring.
LICENCE_GRANTED = re.compile(r"^licence: verified against (?P<run>\S+) on "
                             r"exactly these points, and no others:$", re.M)
LICENCE_WITHHELD = re.compile(r"^licence: WITHHELD\b(?P<rest>.*)$", re.M)

#: `refocus_rust._print_unverifiable`, and the three markers a TypeScript
#: pair carries (`refocus_world.UNVERIFIABLE`). Reported, never summed into a
#: verified total.
UNVERIFIABLE_HEADER = re.compile(
    r"^checks that could not run on this pair\b.*$", re.M)
UNVERIFIABLE_OUTPUT = "output: unverifiable (not recorded)"
UNVERIFIABLE_CHILDREN = "children: unverifiable (not witnessed)"
UNVERIFIABLE_THREADS = "threads: unverifiable (not witnessed)"
UNVERIFIABLE = (UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN,
                UNVERIFIABLE_THREADS)

#: The word H5 greps a GRANTED licence's own points for, per marker. A point
#: claiming one of these while the same pair printed the marker above is the
#: R7 bug class returning: a check that could not run, reported as one that
#: passed.
UNVERIFIABLE_NEEDLE = {UNVERIFIABLE_OUTPUT: "output",
                       UNVERIFIABLE_CHILDREN: "child",
                       UNVERIFIABLE_THREADS: "thread"}

#: `refocus_report.report`'s DIVERGED block. A divergence prints NO licence
#: line at all -- the licence belongs to a MATCH -- and the world findings a
#: licence would have carried as caveats are printed under this header
#: instead. Read so that a DIVERGED control can SAY where its source finding
#: appeared; it is evidence, and no endpoint reads it as a licence.
WORLD_HEADER = ("differences in the world between the two runs, any of "
                "which may be why:")

#: `refocus_cmd._refuse`, on stderr, exit 2: nothing was re-run.
PRE_RERUN_REFUSAL = re.compile(
    r"^error: cannot refocus (?P<run>\S+): (?P<sentence>.*)$", re.M)
#: `refocus_rust._refused_after_rerun`, exit 3 -- the suite DID run.
REFUSED_AFTER = re.compile(r"^refocus verdict: REFUSED -- (?P<why>.*)$", re.M)
#: …and the half of it that is H3's STOP rather than a comparator refusal:
#: the pair LOOKUP found none or several. `refocus_typescript.run`'s two
#: sentences both carry this phrase and no other refusal does.
LOOKUP_PHRASE = "linked to"

#: The divergent step, in both spellings: `diff_cmd._print_divergence`'s own
#: line, and the `tasks: DIVERGED …` sentence a task divergence carries it
#: in. The LINE is kept whole because H4's finding has to name it.
CAUSAL_STEP = re.compile(r"at causal step (?P<i>\d+):")
DIVERGED_VERDICT = re.compile(r"^verdict: DIVERGED at causal step (?P<i>\d+)$",
                              re.M)

#: vitest's own summary line, both units. `Duration  85ms` on a one-file
#: case and `Duration  24.31s` on the lens; a reader that matched one would
#: report `None` for every row of the other.
DURATION = re.compile(r"^\s*Duration\s+(?P<n>[0-9.]+)(?P<unit>ms|s)\b", re.M)


def _status_of(rest: str | None) -> str | None:
    """Which of the three statuses a `source:`/`env:` line is, or None.

    None for a line that is none of them, never a guess: a fourth spelling is
    a change in the command, and reading it as one of these three is how a
    check that did not run gets counted as one that passed.
    """
    if rest is None:
        return None
    for status in STATUSES:
        if rest.startswith(status):
            return status
    return None


def bullets_after(text: str, header: str) -> list[str]:
    """The contiguous `  - ` bullets directly under `header`.

    Contiguity is what keeps three bullet blocks of one answer apart: the
    licence's points, the blind-spot block and the unverifiable markers all
    print as `  - `, and a scan that took every bullet would fold the
    recorder's categorical blind spots into the licence H5 then counts.
    """
    lines = text.splitlines()
    try:
        start = lines.index(header)
    except ValueError:
        return []
    out = []
    for line in lines[start + 1:]:
        if not line.startswith("  - "):
            break
        out.append(line[4:].strip())
    return out


def harness_duration_s(text: str) -> float | None:
    """vitest's OWN reported duration, in seconds, or None.

    The LAST one in the text: a `refocus` transcript holds the re-run's
    summary and nothing else, but a caller that concatenated an original's
    output would otherwise get the original's number under the re-run's name.
    """
    last = None
    for m in DURATION.finditer(text):
        value = float(m.group("n"))
        last = value / 1000.0 if m.group("unit") == "ms" else value
    return None if last is None else round(last, 4)


def parse_refocus(text: str) -> dict:
    """One `sensorium refocus <run> --focus <spec>` answer, whole.

    Decides nothing. The verdict WORD and the process's exit are never
    derived from each other -- §1's H2 and H4 make a disagreement a finding
    -- and the licence's points and the unverifiable markers are two lists
    that are never summed.
    """
    out: dict = {
        "refocus_of": None, "driver_cmd": None, "cwd": None,
        "focus": None, "window": None,
        "source_line": None, "source_status": None,
        "env_line": None, "env_status": None,
        "exit_line": None, "exit_rerun": None, "exit_original": None,
        "exit_equal": None,
        "pair": {"run": None, "invocation": None, "siblings": None},
        "trace": None,
        "verdict": None, "verdict_line": None,
        "licence": None, "licence_line": None, "licence_points": [],
        "withheld_reasons": [],
        "unverifiable": [], "unverifiable_header": None,
        "world_caveats": [],
        "refusal": None, "refusal_run": None,
        "refused_after_rerun": None, "lookup_refusal": None,
        "diverged_step": None, "divergent_line": None,
        "harness_duration_s": harness_duration_s(text),
    }
    m = REFOCUS_OF.search(text)
    if m:
        out["refocus_of"] = m.group("run")
        out["driver_cmd"] = m.group("cmd").strip()
    m = CWD_LINE.search(text)
    if m:
        out["cwd"] = m.group("cwd").strip()
    m = FOCUS_LINE.search(text)
    if m:
        focus = m.group("focus").strip()
        out["focus"] = [] if focus == "-" else [f.strip()
                                                for f in focus.split(",")]
        out["window"] = m.group("window").strip()
    m = SOURCE_LINE.search(text)
    if m:
        out["source_line"] = m.group(0).strip()
        out["source_status"] = _status_of(m.group("rest"))
    m = ENV_LINE.search(text)
    if m:
        out["env_line"] = m.group(0).strip()
        out["env_status"] = _status_of(m.group("rest"))
    m = PAIR_LINE.search(text)
    if m:
        out["pair"] = {"run": m.group("run"), "invocation": m.group("inv"),
                       "siblings": int(m.group("siblings"))}
    m = TRACE_LINE.search(text)
    if m:
        out["trace"] = m.group("path").strip()
    m = EXIT_LINE.search(text)
    if m:
        out["exit_line"] = m.group(0).strip()
        out["exit_rerun"] = m.group("rerun").strip()
        out["exit_original"] = m.group("original").strip()
        out["exit_equal"] = out["exit_rerun"] == out["exit_original"]
    m = VERDICT.search(text)
    if m:
        out["verdict"] = m.group("word")
        out["verdict_line"] = m.group(0).strip()
    m = LICENCE_GRANTED.search(text)
    if m:
        out["licence"] = "granted"
        out["licence_line"] = m.group(0)
        out["licence_points"] = bullets_after(text, m.group(0))
    else:
        m = LICENCE_WITHHELD.search(text)
        if m:
            out["licence"] = "WITHHELD"
            out["licence_line"] = m.group(0).strip()
            out["withheld_reasons"] = bullets_after(text, m.group(0))
    m = UNVERIFIABLE_HEADER.search(text)
    if m:
        out["unverifiable_header"] = m.group(0).strip()
        out["unverifiable"] = bullets_after(text, m.group(0))
    out["world_caveats"] = bullets_after(text, WORLD_HEADER)
    m = PRE_RERUN_REFUSAL.search(text)
    if m:
        out["refusal"] = m.group("sentence").strip()
        out["refusal_run"] = m.group("run")
    m = REFUSED_AFTER.search(text)
    if m:
        out["refused_after_rerun"] = m.group("why").strip()
        out["lookup_refusal"] = LOOKUP_PHRASE in m.group("why")
    m = DIVERGED_VERDICT.search(text)
    if m:
        out["diverged_step"] = int(m.group("i"))
        out["divergent_line"] = m.group(0).strip()
    else:
        for line in text.splitlines():
            hit = CAUSAL_STEP.search(line)
            if hit:
                out["diverged_step"] = int(hit.group("i"))
                out["divergent_line"] = line.strip()
                break
    return out


def claims_an_unverifiable_check(parsed: dict) -> list[str]:
    """The GRANTED licence points that name a check this pair could not run.

    §1's H5 gates this at 0. The grep is over the granted block alone -- the
    withheld reasons and the blind-spot block both legitimately name these
    words -- and only for the markers THIS pair actually printed, so the
    check is about a contradiction rather than about a vocabulary.
    """
    if parsed.get("licence") != "granted":
        return []
    needles = [UNVERIFIABLE_NEEDLE[c] for c in parsed.get("unverifiable") or []
               if c in UNVERIFIABLE_NEEDLE]
    return [point for point in parsed.get("licence_points") or []
            if any(n in point.lower() for n in needles)]


# -- the two H6 readers -----------------------------------------------------

#: `watch_cmd`'s five answer shapes. REFUSED and the no-match branch are
#: printed INSTEAD of a verdict line, so a text carrying either carries no
#: other class. The fifth is E4's own addition (`acceptance_e4_read`): `watch`
#: takes `_no_match` when no recorded code object matches `--at`, prints that
#: line and returns NEGATIVE -- and a reader without the class would report
#: `None` for an answer the command gave plainly, which is exactly what H6's
#: finding would have to name.
WATCH_CLASSES = (
    ("REFUSED", re.compile(r"^REFUSED: ", re.M)),
    ("no recorded code matches",
     re.compile(r"^error: no recorded code matches --at ", re.M)),
    ("SATISFIED", re.compile(r"^verdict: SATISFIED\b", re.M)),
    ("NOTHING WAS CHECKED", re.compile(r"^verdict: NOTHING WAS CHECKED\b",
                                       re.M)),
    ("not satisfied", re.compile(r"^verdict: not satisfied\b", re.M)),
)

#: `flow_cmd._print_footer`'s count line, which is what an empty answer says
#: instead of a verdict word: `flow` prints no "NOT FOUND", it prints
#: `sightings: 0 event(s), 0 capture(s)` and returns 1.
SIGHTINGS = re.compile(r"^sightings: (?P<n>\d+) event\(s\), "
                       r"(?P<captures>\d+) capture\(s\)", re.M)
SCOPE_LINE = re.compile(r"^scope: .*$", re.M)


def parse_watch(text: str) -> dict:
    """`watch`'s verdict WORD, and the line it was read off. Nothing else.

    The exit belongs to the process and is recorded by the runner; H6
    compares the class and the exit against the survey's prediction, and a
    reader that derived one from the other would make half the comparison
    unfalsifiable.
    """
    classes = [name for name, pat in WATCH_CLASSES if pat.search(text)]
    verdict_line = next((ln.strip() for ln in text.splitlines()
                         if ln.startswith("verdict: ")), None)
    refusal = next((ln.strip() for ln in text.splitlines()
                    if ln.startswith("REFUSED: ")
                    or ln.startswith("error: no recorded code matches ")),
                   None)
    return {"verdict": classes[0] if len(classes) == 1 else None,
            "classes": classes, "verdict_line": verdict_line,
            "refusal_line": refusal}


def parse_flow(text: str) -> dict:
    """`flow`'s answer as a class -- FOUND, NOT FOUND or REFUSED.

    The class is read off the `sightings:` count, which is the number
    `flow_cmd.run` itself branches on for the exit status, and the `scope:`
    line is carried beside it because §1's fourth read predicts the emptiness
    WITH the searched scope printed next to it.
    """
    refusal = next((ln.strip() for ln in text.splitlines()
                    if ln.startswith("REFUSED: ")), None)
    m = SIGHTINGS.search(text)
    scope = SCOPE_LINE.search(text)
    sightings = int(m.group("n")) if m else None
    if refusal:
        verdict = "REFUSED"
    elif sightings is None:
        verdict = None
    else:
        verdict = "FOUND" if sightings else "NOT FOUND"
    return {"verdict": verdict, "sightings": sightings,
            "sightings_line": m.group(0).strip() if m else None,
            "scope_line": scope.group(0).strip() if scope else None,
            "refusal_line": refusal}


# -- the survey -------------------------------------------------------------

#: Plan ruling A7's six columns, in the pre-registered order. Spelled here as
#: `tests/test_acceptance_e15_lock.py` spells it, so the parser and the lock
#: read the same header or one of them refuses.
SURVEY_HEADER = ("| n | test file | class | reason | focus spec | "
                 "resolver matched |")
SURVEY_ROW = re.compile(r"^\| \d+ \|")
SURVEY_N = re.compile(r"^N = (?P<n>\d+)$")

#: One bullet of the `### H6 reads` block: the row it is about, the command
#: in backticks, and the predicted class and exit in bold.
H6_BULLET = re.compile(r"^- \*\*Row (?P<row>\d+)(?P<tail>[^*]*)\*\*")
H6_COMMAND = re.compile(r"`(?P<cmd>(?:watch|flow) [^`]+)`")
H6_PREDICTION = re.compile(r"\*\*(?P<klass>[A-Z][A-Z ]*), exit (?P<exit>\d+)\*\*")

#: The placeholder a read's command carries for the trace it is taken on.
H6_PLACEHOLDER = re.compile(r"<row (?P<row>\d+)'s refocus>")


def _cells(line: str) -> list[str]:
    """One markdown row's cells. Split on UNESCAPED pipes only, for the lock
    test's reason: a cell that needs a `|` escapes it, and splitting on every
    pipe would give that row an extra column."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def parse_survey(text: str) -> dict:
    """The locked survey: its 31 rows, and the four reads H6 is judged on.

    Raises `ValueError` rather than returning a short table: the loop's
    population IS this parse, and a parser that silently read 30 rows would
    publish a 30-row answer under §1's 31-row gate.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == SURVEY_HEADER:
            break
    else:
        raise ValueError("the survey carries no header in the pinned order")
    rows = []
    for line in lines[i + 2:]:                      # skip the separator row
        if SURVEY_N.match(line.strip()):
            break
        if SURVEY_ROW.match(line):
            c = _cells(line)
            if len(c) != 6:
                raise ValueError(f"the survey row has {len(c)} columns: {c}")
            rows.append({"n": int(c[0]),
                         "test_file": c[1].strip("`"),
                         "klass": c[2], "reason": c[3],
                         "focus": c[4].strip("`"),
                         "resolver_matched": int(c[5])})
    last = SURVEY_N.match(lines[-1].strip())
    if not last:
        raise ValueError("the survey's last line is not `N = <count>`")
    if int(last.group("n")) != len(rows):
        raise ValueError(f"the survey says N = {last.group('n')} and carries "
                         f"{len(rows)} rows")
    return {"rows": rows, "n": len(rows), "h6": parse_h6(text)}


def parse_h6(text: str) -> list[dict]:
    """The `### H6 reads` block: four commands with their predictions.

    A bullet whose command or prediction cannot be read RAISES: H6 compares
    four answers against four predictions, and a prediction the instrument
    could not read would be a comparison that passed by default.
    """
    block = text.split("### H6 reads", 1)
    if len(block) != 2:
        raise ValueError("the survey carries no `### H6 reads` block")
    out, current = [], None
    for line in block[1].splitlines():
        head = H6_BULLET.match(line)
        if head:
            current = {"row": int(head.group("row")), "text": line,
                       "label": f"Row {head.group('row')}"
                                f"{head.group('tail')}".strip()}
            out.append(current)
        elif current is not None and line.startswith("  "):
            current["text"] += "\n" + line
        elif current is not None and not line.strip():
            continue
    for read in out:
        cmd = H6_COMMAND.search(read["text"])
        pred = H6_PREDICTION.search(read["text"])
        if not cmd or not pred:
            raise ValueError(f"the H6 bullet {read['label']!r} carries no "
                             "readable command or prediction")
        read["command"] = cmd.group("cmd").strip()
        read["kind"] = read["command"].split()[0]
        read["predicted_class"] = pred.group("klass").strip()
        read["predicted_exit"] = int(pred.group("exit"))
        read.pop("text")
    if not out:
        raise ValueError("the `### H6 reads` block names no read")
    return out


def h6_argv(command: str, trace_of_row: dict) -> list[str]:
    """One H6 read's argv, with `<row N's refocus>` replaced by that row's
    NEW trace id.

    Substituted BEFORE the split, not after: the placeholder carries an
    apostrophe and `shlex` would open a quote on it that the command's own
    `--expr '…'` then closes in the wrong place.
    """
    import shlex
    resolved = H6_PLACEHOLDER.sub(
        lambda m: str(trace_of_row.get(int(m.group("row")))), command)
    return shlex.split(resolved)
