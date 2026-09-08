#!/usr/bin/env python3
"""E4′'s loop and H1-H3: the re-run, the licence word, the verdict, the pair.

PASS 2 ONLY. Nothing here records anything: the originals are E4's, copied
into the fresh store by `acceptance_e4p_store`, and the one invocation this
record makes against the subject is §1's

    sensorium refocus <run> --focus <name>

Every ceiling is a RECORDED FACT rather than an exception: a killed
invocation publishes `{"killed": true, "reason": …}` and the endpoints
already read stand (§1.4's kill rules). Nothing is gated on a wall.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402
from acceptance_e4p_read import (VERDICT_EXIT, cargo_finished_seconds,  # noqa: E402,E501
                                 licence_counts, licence_partition,
                                 pair_candidates, parse_refocus,
                                 trace_meta_ro)
from acceptance_e4p_rows import (EXPECTED_GRANTED,                 # noqa: E402
                                 EXPECTED_HARNESS_THREADS,
                                 EXPECTED_WITHHELD, GATE_N)
from acceptance_e6ppp import LOADS, logs_at, mark_load             # noqa: E402,F401
from acceptance_lib import REPO, plain_env, step                   # noqa: E402

#: Set by the runner to its own ledger, exactly as the E4 family does. Left
#: `None` so a phase that runs before the runner has set it fails loudly
#: instead of writing an hour of evidence somewhere plausible and wrong.
LOGS: Path | None = None

#: How long a signalled process group is given to die before the next
#: signal. Not a measurement -- a kill that has to be escalated is recorded
#: as one either way.
TERM_GRACE_S = 10.0
KILL_GRACE_S = 5.0

NOT_RUN_BOUND = ("the 1 h 15 min loop bound was reached before this "
                 "invocation")


def refocus_argv(name: str, run_id: str) -> list[str]:
    """§1's pass-2 argv, verbatim: `sensorium refocus <run> --focus <name>`,
    through this repository's own `.venv` Python (§1.4's lens). No other
    flag: `SENSORIUM_TIER` is not set by this record, so each refocus
    replays the tier recorded on its own original."""
    return [str(REPO / ".venv" / "bin" / "python"), "-m", "sensorium",
            "refocus", run_id, "--focus", name]


def refocus_env(paths) -> dict:
    """The environment every refocus runs under.

    `plain_env()` strips every `SENSORIUM_*` and `CARGO_TARGET_DIR` from the
    launcher's environment; three go back and NOTHING else:

    * `SENSORIUM_DIR` -- the FRESH store the copies are in and the new trace
      must land in. Never the kept store: §1.3 forbids a refocus pointing at
      it, and this function is where that is true or false.
    * `SENSORIUM_CARGO_SENSORIUM` -- how the CLI finds the driver.
    * `CARGO_TARGET_DIR` -- the child inherits this process's environment,
      so this is what puts the 61 rebuilds in the FRESH target where H4's
      census can count 61 focused keys.

    `SENSORIUM_TIER` is absent and `SENSORIUM_NO_INVOCATION_LOG` is absent,
    both by §1.4 -- properties of this function rather than of whoever
    launched the run.
    """
    return plain_env() | {
        "SENSORIUM_DIR": str(paths["sensorium_dir"]),
        "SENSORIUM_CARGO_SENSORIUM": str(paths["sensorium_driver"]),
        "CARGO_TARGET_DIR": str(paths["sensorium_e4p_target"]),
    }


def guarded(cmd, cwd, log_name, env, timeout, tag) -> dict:
    """One command, in its OWN process group, with the ceiling as a FACT.

    `subprocess.run(timeout=…)` kills the direct child only. `sensorium
    refocus` launches `cargo-sensorium`, which launches `cargo`, which
    launches `rustc`: a timeout that killed the Python would leave the build
    running and burning cores for the rest of the record -- the mutation
    harness lost sixteen cores twice to exactly that. So the child gets
    `start_new_session=True` (a session and a process GROUP of its own), the
    GROUP is signalled TERM and then KILL, and `ps -p` is what says whether
    it is gone.

    `pkill -f` is never used anywhere in this instrument: its pattern
    matches the runner's own argv, so it never reaps and can reap the wrong
    thing.

    A timeout is not raised. It comes back as `timed_out: True` with
    whatever was printed, because §1.4's kill rules make a bound reached a
    recorded not-measured rather than a crash that takes the endpoints
    already read down with it.
    """
    logs = LOGS or lib.LOGS or Path(".")
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / log_name
    t0 = time.monotonic()
    proc = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    kill = None
    try:
        out, err = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        kill = _kill_group(proc, tag)
        try:
            out, err = proc.communicate(timeout=KILL_GRACE_S)
        except subprocess.TimeoutExpired:          # pragma: no cover
            out, err = "", ""
        step(f"{tag}: KILLED at {timeout} s ({kill})")
    wall = time.monotonic() - t0
    log.write_text(
        f"$ {' '.join(str(c) for c in cmd)}\n(cwd={cwd})\n"
        + (f"--- KILLED at {timeout} s: {kill} ---\n" if timed_out else "")
        + f"--- stdout ---\n{out}\n--- stderr ---\n{err}\n"
        f"--- rc={proc.returncode} wall={wall:.3f} ---\n")
    return {"rc": None if timed_out else proc.returncode,
            "out": out or "", "err": err or "", "wall": wall,
            "log": str(log), "timed_out": timed_out, "kill_s": timeout,
            "kill": kill, "pid": proc.pid,
            "command": " ".join(str(c) for c in cmd)}


def _kill_group(proc, tag: str) -> dict:
    """TERM the GROUP, then KILL it, and census the group with `ps`.

    The pgid is read BEFORE the first signal: once the leader exits,
    `os.getpgid` raises and the group -- whose other members are the ones
    still holding cores -- would never be signalled at all.

    The leader is REAPED between the signal and the check, and the check is
    over the GROUP, not the leader's pid. Both matter and the first cost a
    red test to learn: an unreaped child of this process is a ZOMBIE, and
    `ps -p <pid>` reports a zombie as present, so a liveness check that
    asked about the leader's pid before waiting on it would report every
    successful kill as a survival. And the question this record needs
    answered is not "did the leader go" but "is anything from this group
    still running", which is what `ps -o pid= -g <pgid>` says.
    """
    record = {"pid": proc.pid, "pgid": None, "term": None, "kill": None,
              "group_survivors": None, "still_alive": None}
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:                     # pragma: no cover
        record["term"] = "the leader was already gone"
        record["still_alive"] = False
        return record
    record["pgid"] = pgid
    for name, sig, grace in (("term", signal.SIGTERM, TERM_GRACE_S),
                             ("kill", signal.SIGKILL, KILL_GRACE_S)):
        try:
            os.killpg(pgid, sig)
            record[name] = "sent"
        except ProcessLookupError:
            record[name] = "the group was already gone"
        # Reap the leader so it stops being a zombie, THEN look at the
        # group. A leader that will not die inside the grace goes round
        # again with SIGKILL.
        try:
            proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
        survivors = _group_members(pgid)
        if not survivors:
            record[name] = f"sent; the group was empty within {grace} s"
            break
    survivors = _group_members(pgid)
    record["group_survivors"] = survivors
    record["still_alive"] = bool(survivors)
    if survivors:                                  # pragma: no cover
        step(f"{tag}: process group {pgid} SURVIVED the kill with "
             f"{survivors} -- recorded, not retried")
    return record


def _group_members(pgid: int) -> list[int]:
    """Every pid still in the process group, by `ps`.

    `ps -o pid= -g <pgid>` exits non-zero with no output for an empty group,
    which is the answer this wants: an empty list. Never `pkill -f`, whose
    pattern matches this runner's own argv -- it would never reap and could
    reap the wrong process.
    """
    res = subprocess.run(["ps", "-o", "pid=", "-g", str(pgid)],
                         capture_output=True, text=True)
    return [int(x) for x in res.stdout.split() if x.strip().isdigit()]


# ------------------------------------------------------------- the loop

def refocus_one(paths, cfg, row, extra_env=None, label=None) -> dict:
    """One of the 61, and everything that came back from it.

    The pair is found in the STORE -- by `refocus_of`, the launch timestamp
    and R2's child filter (§1.4's pair rule, §3's R2) -- and the id the CLI
    printed is recorded beside it as a CROSS-CHECK, never as the source.

    **The pair is found HERE, immediately after this invocation, and never
    in a closing sweep.** E4″ re-refocuses four of its own originals under
    two control arms into the SAME store, so up to three traces end up
    naming one original in `refocus_of`; the launch timestamp taken on the
    line above is what tells them apart, and it exists only inside this
    call.

    `extra_env` is E4″'s control arms: one key added to the environment
    every refocus runs under, recorded on the row so the record says which
    arm's world each answer came from. `None` -- arm A and every E4′ row --
    leaves `refocus_env(paths)` exactly as it was.

    `label` renames this row's log and step tag, so the same row re-run
    under a second arm writes a second log instead of overwriting the
    first. `None` keeps E4′'s own names.
    """
    index, name, target, run_id = row
    cmd = refocus_argv(name, run_id)
    env = refocus_env(paths)
    if extra_env:
        env = env | dict(extra_env)
    launched_at = time.time()
    res = guarded(cmd, paths["sensorium_bloomery"],
                  f"{label or 'p2'}-{index:02d}-{name}.log", env,
                  cfg["refocus_timeout"],
                  f"E4′/{index}" if label is None else f"{label}/{index}")
    both = "\n".join((res["out"], res["err"]))
    parsed = parse_refocus(both)
    pair = pair_candidates(paths["sensorium_dir"] / "traces", run_id,
                           launched_at)
    out = {
        "index": index, "name": name, "target": target, "original": run_id,
        # Which arm's world this answer came from. `None` on arm A and on
        # every E4′ row: an arm is a fact about the invocation, and a row
        # that does not carry it is not the same row as one that does.
        "arm": label, "extra_env": dict(extra_env) if extra_env else None,
        "command": res["command"], "cwd": str(paths["sensorium_bloomery"]),
        "rc": res["rc"], "wall_s": round(res["wall"], 3),
        "timed_out": res["timed_out"], "kill_s": res["kill_s"],
        "kill": res["kill"], "log": res["log"], "launched_at": launched_at,
        "cargo_finished_s": cargo_finished_seconds(both),
        # H3: the STORE's answer, and the CLI's beside it.
        "pair": pair,
        "new_run": pair["qualifying"][0] if pair["n"] == 1 else None,
        "pair_refusal": (None if pair["n"] == 1 else
                         (f"the store holds {pair['n']} candidate trace(s) "
                          f"whose `refocus_of` is {run_id} and whose "
                          f"recording started after the launch "
                          f"({pair['qualifying']}); §1.4's pair rule needs "
                          "exactly one")),
        "printed_pair_run": parsed["pair_run"],
        "pair_agrees_with_the_printed_id": (
            pair["n"] == 1 and parsed["pair_run"] == pair["qualifying"][0]),
        # H3's second reading: R2's exclusion list, from BOTH readings.
        "excluded_children_printed": parsed["excluded_children"],
        "excluded_children_in_the_store": pair["children"],
        "stdout": res["out"], "stderr": res["err"],
        **{k: v for k, v in parsed.items() if k not in ("licence",)},
        # H1: the partition, kept apart from the printed word it contains.
        "licence_word": parsed["licence"],
        "licence_partition": licence_partition(parsed),
        "licence": licence_counts(parsed),
    }
    out["verdict_exit_expected"] = VERDICT_EXIT.get(out["verdict_word"])
    out["verdict_and_exit_agree"] = (
        None if out["verdict_word"] is None or out["rc"] is None
        else out["rc"] == VERDICT_EXIT[out["verdict_word"]])
    db = paths["sensorium_dir"] / "traces" / f"{out['new_run']}.db"
    if out["new_run"] and db.is_file():
        out["new_trace_bytes"] = db.stat().st_size
        meta = trace_meta_ro(db)
        out["new_meta"] = {k: meta.get(k) for k in
                           ("recorder", "driver_version", "capabilities",
                            "focus", "refocus_of", "refocus_verdict",
                            "refocus_licence", "refocus_licence_reasons",
                            "refocus_licence_unverifiable",
                            "refocus_children", "counts", "exit_status",
                            "threads_started", "site_marks")}
        # §1.4's version rule: the driver token is read from THE TRACE, never
        # hard-coded here. `transform` is not in the trace or the binary and
        # is taken from `Cargo.lock` by the runner, labelled with its source.
        out["driver_version_from_the_trace"] = meta.get("driver_version")
    else:
        out["new_trace_bytes"], out["new_meta"] = None, None
        out["driver_version_from_the_trace"] = None
    part = out["licence_partition"]
    step(f"E4′ {index}/{cfg['gate_n']} {name}: exit={out['rc']} "
         f"verdict={out['verdict_word']} licence={part['licence']} "
         f"program_threads={part['program_threads']} "
         f"harness={part['harness_threads']} pair={pair['n']} "
         f"wall={out['wall_s']}s")
    return out


def pass_two(paths, cfg, on_first_number=None) -> dict:
    """The 61 refocuses, in §1.1's order, under one loop bound.

    `on_first_number` is called the moment the FIRST refocus comes back
    with a reading -- a verdict word or a licence word. That is the instant
    §1.4's rules 4 and 5 part company, and the runner uses it to flip and
    FLUSH `numbers_read`: everything after it is a measurement of one of
    the 61, and kill 6 forbids relaunching from zero over a row already
    read.
    """
    mark_load("pass2")
    deadline = time.monotonic() + cfg["loop_budget_s"]
    rows, exhausted = [], []
    with logs_at(LOGS / "pass2"):
        for row in cfg["rows"]:
            index, name, target, run_id = row
            if time.monotonic() >= deadline:
                exhausted.append(name)
                # `cfg["not_run_bound"]` where the record gives one: the
                # sentence names a BOUND, and E4″'s is not E4′'s. Absent, it
                # is E4′'s own constant and this line reads as it always did.
                rows.append({"index": index, "name": name, "target": target,
                             "original": run_id,
                             "not_run": cfg.get("not_run_bound",
                                                NOT_RUN_BOUND)})
                continue
            answer = refocus_one(paths, cfg, row)
            rows.append(answer)
            if on_first_number is not None and (answer.get("verdict_word")
                                                or answer.get("licence_word")):
                on_first_number(
                    f"row {index} ({name}) came back with verdict "
                    f"{answer.get('verdict_word')!r} and licence "
                    f"{answer.get('licence_word')!r}")
    measured = [r for r in rows if "not_run" not in r]
    out = {
        "refocuses": rows, "by_name": {r["name"]: r for r in rows},
        "n": len(rows), "measured": len(measured),
        "budget_exhausted": exhausted,
        "killed": [r["name"] for r in measured if r.get("timed_out")],
        "pair_refusals": [r["name"] for r in measured
                          if r.get("pair_refusal")],
        "walls_s": {r["name"]: r.get("wall_s") for r in rows},
        "loop_budget_s": cfg["loop_budget_s"],
        "loop_deadline_monotonic": deadline,
    }
    step(f"pass 2: {out['measured']}/{out['n']} refocused; killed "
         f"{out['killed']}; pair refusals {out['pair_refusals']}")
    return out


def _measured(two: dict) -> list[dict]:
    return [r for r in two["refocuses"] if "not_run" not in r]


def _subset_reasons(two: dict) -> list[str]:
    """Why a boolean over "the 61" cannot be answered from this loop.

    Empty when the loop was whole. Otherwise every reason is NAMED, and the
    caller sets its `*_as_predicted` to `None` rather than to `False`:
    `False` is "measured, and not as predicted", and a loop that stopped at
    51 measured nothing about §1's "61 of 61". The RAW record carries this
    because Task 6 reads the raw file to write §4 -- the assembled record's
    drop rules are honest either way, but a `true` sitting beside `n: 51`
    in the raw file is a sentence waiting to be misread.
    """
    out = []
    n, measured = two.get("n"), two.get("measured")
    if n != GATE_N:
        out.append(f"the loop ran over {n} row(s), not §1.1's {GATE_N}")
    if measured is not None and n is not None and measured != n:
        out.append(f"{measured} of {n} invocation(s) ran")
    missing = two.get("budget_exhausted") or []
    if missing:
        out.append(f"{len(missing)} invocation(s) were never run -- §1.4's "
                   f"1 h 15 min loop bound was reached")
    killed = two.get("killed") or []
    if killed:
        out.append(f"{len(killed)} invocation(s) were KILLED at the 1800 s "
                   f"ceiling; their output is partial")
    return out


# ---------------------------------------------------------------------- H1

def phase_h1(two: dict) -> dict:
    """H1: does the harness rule change the licence word as predicted?

    The GATE is the partition -- granted 57, WITHHELD exactly §1.2's four,
    by name. Not a count alone: a run that withheld four DIFFERENT tests
    would score 57/4 and be a different finding entirely, so the SETS are
    compared and the symmetric difference is published either way.

    The SECOND READING is the wording, and it is reported whatever the gate
    says: each of the four names the program's own count AND states the
    harness exclusion, and each of the 57 carries the harness phrase. A
    granted line that hides the exclusion is a finding even when the word is
    the predicted one, so `hides_the_exclusion` is a list of names rather
    than a boolean.
    """
    rows = _measured(two)
    granted, withheld, unread = [], {}, []
    hides, unsubtracted, wrong_count, sides_disagree = [], [], [], []
    harness_counts, phrases = {}, set()
    sources, sourceless = {}, []
    for r in rows:
        part = r.get("licence_partition") or {}
        word = part.get("licence")
        if word is None:
            unread.append(r["name"])
            continue
        harness_counts[r["name"]] = part.get("harness_threads")
        # E4′ §5's gap 1's other half: a count is published WITH the line it
        # was read from, so a reader can check it against that line rather
        # than take the number on trust. `None` means neither line answered,
        # and that pair is NAMED -- H7 gates on the list, not on a null a
        # reader has to notice.
        sources[r["name"]] = part.get("counts_source")
        if part.get("counts_source") is None:
            sourceless.append(r["name"])
        if part.get("harness_phrase"):
            phrases.add(part["harness_phrase"])
        if part.get("sides_agree") is False:
            sides_disagree.append(r["name"])
        if word == "granted":
            granted.append(r["name"])
            if part.get("names_the_exclusion") is not True:
                hides.append(r["name"])
        else:
            withheld[r["name"]] = part.get("program_threads")
            if part.get("unsubtracted_labels"):
                unsubtracted.append(r["name"])
            expected = EXPECTED_WITHHELD.get(r["name"])
            if expected is not None and part.get("program_threads") != expected:
                wrong_count.append({"name": r["name"], "expected": expected,
                                    "measured": part.get("program_threads")})
    expected_w = set(EXPECTED_WITHHELD)
    measured_w = set(withheld)
    out = {
        "n": len(rows),
        "granted": sorted(granted), "granted_n": len(granted),
        "withheld": dict(sorted(withheld.items())),
        "withheld_n": len(withheld),
        "unread": unread,
        "expected_granted_n": len(EXPECTED_GRANTED),
        "expected_withheld": dict(sorted(EXPECTED_WITHHELD.items())),
        "withheld_set_as_predicted": measured_w == expected_w,
        "withheld_only_here": sorted(measured_w - expected_w),
        "withheld_missing": sorted(expected_w - measured_w),
        "granted_as_predicted": len(granted) == len(EXPECTED_GRANTED),
        "withheld_counts_as_predicted": not wrong_count,
        "withheld_count_mismatches": wrong_count,
        # The second reading, reported whatever the gate says.
        "hides_the_exclusion": sorted(hides),
        "reasons_that_never_subtracted": sorted(unsubtracted),
        "sides_disagree": sorted(sides_disagree),
        "harness_threads_by_name": harness_counts,
        "harness_threads_all_one": (
            bool(harness_counts)
            and set(harness_counts.values()) == {EXPECTED_HARNESS_THREADS}),
        "harness_phrases": sorted(phrases),
        "counts_source_by_name": sources,
        "counts_without_a_source_line": sorted(sourceless),
        "counts_carry_their_source_line": bool(sources) and not sourceless,
    }
    out["partition_as_predicted"] = bool(
        out["granted_as_predicted"] and out["withheld_set_as_predicted"]
        and out["withheld_counts_as_predicted"] and not unread)
    step(f"H1: granted {out['granted_n']}/{len(EXPECTED_GRANTED)}, withheld "
         f"{sorted(measured_w)}; as predicted="
         f"{out['partition_as_predicted']}; hides the exclusion="
         f"{out['hides_the_exclusion']}")
    return out


# ---------------------------------------------------------------------- H2

def phase_h2(two: dict) -> dict:
    """H2: is the verdict untouched? MATCH 61 of 61.

    The printed WORD and the process EXIT are two readings of one fact and
    are compared, never derived from each other: §1's second reading makes a
    disagreement between them a finding reported as one, "never resolved in
    favour of either".
    """
    rows = _measured(two)
    words, disagree, non_match, unread = {}, [], [], []
    for r in rows:
        word = r.get("verdict_word")
        words[r["name"]] = word
        if word is None:
            unread.append(r["name"])
            continue
        if word != "MATCH":
            non_match.append({"name": r["name"], "verdict": word,
                              "original": r.get("original"),
                              "pair": r.get("new_run"),
                              "diverged_step": r.get("diverged_step"),
                              "refused": r.get("refused_after_rerun")})
        if r.get("verdict_and_exit_agree") is False:
            disagree.append({"name": r["name"], "word": word,
                             "exit": r.get("rc"),
                             "expected_exit": r.get("verdict_exit_expected")})
    match_n = sum(1 for w in words.values() if w == "MATCH")
    dropped = _subset_reasons(two)
    out = {
        "n": len(rows), "verdicts": words, "match_n": match_n,
        "non_match": non_match, "unread": unread,
        "word_and_exit_disagree": disagree,
        "dropped": dropped,
        # `None` over a subset, never `True`: §1's gate is MATCH 61 of 61.
        "match_as_predicted": (None if dropped else
                               match_n == len(rows) and not unread),
    }
    step(f"H2: MATCH {match_n}/{len(rows)}; non-MATCH "
         f"{[x['name'] for x in non_match]}; word/exit disagreements "
         f"{len(disagree)}")
    return out


# ---------------------------------------------------------------------- H3

def phase_h3(two: dict) -> dict:
    """H3: is the pair found? 61 of 61 pairs of exactly one.

    The second reading is R2's exclusion list, read TWICE -- from the
    printed clause and from the store -- because §1.1's greps found
    `Command::new` 0 hits over the seven files, so the list is expected
    empty on all 61 and a non-empty one is a finding whichever reading
    carries it.
    """
    rows = _measured(two)
    counts, wrong, excluded, disagree = {}, [], {}, []
    for r in rows:
        pair = r.get("pair") or {}
        counts[r["name"]] = pair.get("n")
        if pair.get("n") != 1:
            wrong.append({"name": r["name"], "n": pair.get("n"),
                          "original": r.get("original"),
                          "qualifying": pair.get("qualifying"),
                          "linked": pair.get("linked"),
                          "unreadable": pair.get("unreadable")})
        printed = r.get("excluded_children_printed") or []
        in_store = r.get("excluded_children_in_the_store") or []
        if printed or in_store:
            excluded[r["name"]] = {"printed": printed, "store": in_store}
        if sorted(printed) != sorted(in_store):
            disagree.append({"name": r["name"], "printed": printed,
                             "store": in_store})
        if r.get("pair_agrees_with_the_printed_id") is False:
            disagree.append({"name": r["name"],
                             "store_pair": r.get("new_run"),
                             "printed_pair": r.get("printed_pair_run")})
    ones = sum(1 for n in counts.values() if n == 1)
    dropped = _subset_reasons(two)
    out = {
        "n": len(rows), "pair_counts": counts, "pairs_of_one": ones,
        "not_one": wrong, "dropped": dropped,
        "pairs_as_predicted": (None if dropped else
                               ones == len(rows) and not wrong),
        "excluded_children": excluded,
        "excluded_children_n": len(excluded),
        "excluded_list_empty_on_all": not excluded,
        "readings_disagree": disagree,
    }
    step(f"H3: pairs of one {ones}/{len(rows)}; excluded-children rows "
         f"{len(excluded)}; reading disagreements {len(disagree)}")
    return out


__all__ = ["LOGS", "NOT_RUN_BOUND", "guarded", "pass_two", "phase_h1",
           "phase_h2", "phase_h3", "refocus_argv", "refocus_env",
           "refocus_one"]
