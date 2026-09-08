#!/usr/bin/env python3
"""E4″'s eight phases: the partition (H1), the fragment (H2), the verdict
and the pair (H3), the session set (H4), the two controls (H5, H6), the
instrument itself (H7) and what did not move (H8).

Three of them are E4′'s, unchanged and imported rather than copied -- H1 is
`eph.phase_h1` outright, and H3 is E4′'s H2 and H3 read together, which is
the translation §1.2 names. The rest are this record's own.

TWO RULES EVERY PHASE HERE KEEPS
--------------------------------
* **Every phase returns a `verdict`** -- `PASS`, `STOP` or `REPORTED` --
  beside its cells, so §1.4's kill sentences are mechanical rather than a
  reading of the numbers. `REPORTED` is for a phase with no gate.
* **`None` is not zero, and a killed pair contributes nothing.** A cell the
  phase could not read is `None` and its reason is on `dropped`; a cell it
  read and found empty is `0` or `[]`. A pair whose invocation was killed
  leaves no measured-looking cell anywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4p_phases as eph                                # noqa: E402
import acceptance_e4pp_rows as e4pp                                # noqa: E402
from acceptance_e4p_read import rt_hash_of, trace_meta_ro          # noqa: E402
from acceptance_e4p_schema import licence_verified_counts          # noqa: E402
from acceptance_e6ppp import logs_at, mark_load                    # noqa: E402
from acceptance_e4pp_phases2 import (corpus_case_names,           # noqa: E402,F401
                                     phase_h8_nothing_else)
from acceptance_lib import step                                   # noqa: E402
from sensorium.query.refocus_env import is_session_key             # noqa: E402

LOGS: Path | None = None

#: The one sentence a bounded reading publishes as its lens (§1.4's kill 7).
CAPPED = (f"the printed name list is capped at {e4pp.NAME_CAP} names with a "
          "`+M more` tail, so the COUNT is authoritative and the names are "
          "short: the by-name half of this reading went UNREAD and the "
          "bounded reading is never reported as the full one")


def _measured(block: dict) -> list[dict]:
    """Every row of an arm that actually ran. A row the loop bound cut off
    carries `not_run` and has no reading of any kind."""
    return [r for r in (block or {}).get("refocuses") or []
            if "not_run" not in r]


def _verdict(ok) -> str:
    """`None` is not a pass. A gate whose cells could not be read is a STOP
    of whatever it gates, never a silent PASS."""
    return "PASS" if ok is True else "STOP"


def subset_reasons(block: dict, expected_n: int, label: str) -> list[str]:
    """Why a count over an arm's rows may not be trusted, NAMED.

    E4′ guarded exactly this (`acceptance_e4p_phases._subset_reasons`) and
    said why: "a `true` sitting beside `n: 51` in the raw file is a
    sentence waiting to be misread". Every gate of this record is over a
    LOCKED denominator -- §1.1's 61 for arm A, §1.3's 4 for each control --
    so a loop that stopped at 59 measured nothing about "61 of 61", and its
    `as_predicted` is `None` rather than a `False` that reads as a subject
    finding or a `True` that reads as a whole one.

    Four shapes, four sentences: a table that was not the locked one, an
    arm whose rows did not all run, a bound reached, and a killed
    invocation whose output is partial.
    """
    block = block or {}
    out = []
    n, measured = block.get("n"), block.get("measured")
    if n != expected_n:
        out.append(f"the {label} ran over {n} row(s), not §1's "
                   f"{expected_n}")
    missing = block.get("budget_exhausted") or []
    if missing:
        out.append(f"the {label}: {len(missing)} invocation(s) were never "
                   f"run -- §1.4's 1 h 30 min loop bound was reached "
                   f"({missing[:3]})")
    if (measured is not None and n is not None and measured != n
            and not missing):
        out.append(f"the {label}: {measured} of {n} invocation(s) ran")
    killed = block.get("killed") or []
    if killed:
        out.append(f"the {label}: {len(killed)} invocation(s) were KILLED "
                   f"at the 1800 s ceiling ({killed[:3]}); their output is "
                   "partial")
    return out


def phase_h1(two: dict) -> dict:
    """H1: E4′'s partition, under E4″'s subset guard.

    The arithmetic is E4′'s `phase_h1` unchanged -- this record measures
    the same partition over the same 61 originals. What is added is the
    guard the other seven phases keep: a loop that killed two WITHHELD
    rows could still count 57 granted and read as §1.2's partition, so
    `partition_as_predicted` goes `None` with its reason rather than
    `True` over fewer rows than the gate names.
    """
    out = eph.phase_h1(two)
    out["dropped"] = subset_reasons(two, e4pp.GATE_N, "arm-A loop")
    if out["dropped"]:
        out["partition_as_predicted"] = None
    out["verdict"] = _verdict(out["partition_as_predicted"])
    return out


def read_rt_hashes(paths, block: dict) -> dict:
    """§1.5's two tool hashes, per pair, read from the TRACES.

    The printed `env:` line names keys and never values, so the hash the
    recorder's fragment carries is not on it. It is read instead out of
    each side's recorded environment: the ORIGINAL's from the copy in the
    fresh store (written by `cargo-sensorium` 0.5.0) and the RE-RUN's from
    the trace this invocation produced (by the 0.5.2 the preflight built).

    Attached to the rows in place, immediately after the arm that made
    them, so a pair whose trace is later joined by another arm's is not
    read twice. `None` with its reason where either side could not be read
    -- a hash nobody read is not a hash that matched.
    """
    traces = Path(paths["sensorium_dir"]) / "traces"
    for r in (block or {}).get("refocuses") or []:
        if "not_run" in r:
            continue
        r["original_rt_hash"] = rt_hash_of(
            trace_meta_ro(traces / f"{r.get('original')}.db").get("env"))
        r["rerun_rt_hash"] = (
            rt_hash_of(trace_meta_ro(
                traces / f"{r['new_run']}.db").get("env"))
            if r.get("new_run") else
            {"key": "RUSTDOCFLAGS", "value": None, "fragments": 0,
             "occurrences": 0, "hashes": [],
             "reason": "no pair was found, so there is no re-run trace to "
                       "read a hash out of"})
        a = r["original_rt_hash"]["value"]
        b = r["rerun_rt_hash"]["value"]
        r["rt_hashes_differ"] = (None if a is None or b is None else a != b)
    return block


# ---------------------------------------------------------------------- H2

def phase_h2_fragment(two: dict) -> dict:
    """H2: is the recorder's fragment gone from the compare?

    Three cells, all gated. `RUSTDOCFLAGS` appears in NO pair's changed
    list; the strip clause NAMES it on every pair; and the relocated set is
    E4′'s measured four on every pair. The third is a name list and not a
    count on purpose: a run that relocated four DIFFERENT keys would score
    61/61 on a count and be another finding entirely.

    The changed list is CAPPED at eight names, so on a longer one the
    absence of `RUSTDOCFLAGS` from the NAMES is not its absence from the
    list. Such a pair is named on `changed_lists_bounded` and the
    membership cell goes `None` with its reason (§1.4's kill 7), which
    fails the gate rather than passing on a reading nobody could make.

    The second reading is §1.5's two rt hashes, per pair and per side. They
    are REPORTED: a pair whose two hashes were EQUAL is a pair whose strip
    could not have been tested, and that is a fact about the subject rather
    than a gate on it.
    """
    mark_load("H2")
    rows = _measured(two)
    in_changed, missing, bounded, changed_by_pair = [], [], [], {}
    sets, hashes, equal, unread, differ = {}, {}, [], [], 0
    for r in rows:
        name = r["name"]
        changed = r.get("env_changed_keys") or []
        if changed:
            changed_by_pair[name] = changed
        if r.get("env_changed_keys_truncated"):
            bounded.append(name)
        elif e4pp.STRIP_KEY in changed:
            in_changed.append(name)
        if e4pp.STRIP_KEY not in (r.get("env_stripped_keys") or []):
            missing.append(name)
        sets[name] = sorted(r.get("env_relocated_keys") or [])
        a = (r.get("original_rt_hash") or {}).get("value")
        b = (r.get("rerun_rt_hash") or {}).get("value")
        hashes[name] = {"original": a, "rerun": b}
        # Three outcomes, never two. A pair whose either side could not be
        # read is on NEITHER list: counted as "not differing" it would make
        # an unreadable run and a single-build run print the same number,
        # which is the one thing §1.5 exists to tell apart.
        if a is None or b is None:
            unread.append(name)
        elif a != b:
            differ += 1
        else:
            equal.append(name)
    distinct = sorted({tuple(v) for v in sets.values()})
    expected = list(e4pp.EXPECTED_RELOCATED)
    matches = sum(1 for v in sets.values() if v == expected)
    dropped = subset_reasons(two, e4pp.GATE_N, "arm-A loop")
    if unread:
        dropped.append(
            f"{len(unread)} pair(s) rt hash could not be read on one side "
            f"or both ({unread[:3]}), so they are counted as neither "
            "differing nor equal; `hashes_differ` is over the readable "
            f"{len(rows) - len(unread)}")
    if bounded:
        dropped.append(f"{len(bounded)} pair(s) printed a changed list at "
                       f"its cap ({bounded[:3]}); " + CAPPED)
    if len(distinct) > 1:
        dropped.append(
            f"the pairs did not agree on the relocated set: "
            f"{[list(d) for d in distinct]}. A single set is published only "
            "where every pair printed the same one; the per-pair sets are "
            "under `relocated_by_pair`")
    out = {
        "n": len(rows),
        "rustdocflags_in_changed": (None if bounded else len(in_changed)),
        "rustdocflags_in_changed_pairs": sorted(in_changed),
        "changed_lists_bounded": sorted(bounded),
        "changed_by_pair": changed_by_pair,
        "strip_clause_named": len(rows) - len(missing),
        "strip_clause_missing": sorted(missing),
        "relocated_set": (list(distinct[0]) if len(distinct) == 1 else None),
        "relocated_sets_seen": [list(d) for d in distinct],
        "relocated_by_pair": sets,
        "relocated_set_matches": matches,
        "expected_relocated_set": expected,
        # §1.5, reported and never gated.
        "rt_hashes_by_pair": hashes,
        "hashes_differ": differ,
        "hashes_equal_so_the_strip_was_untested": sorted(equal),
        "hashes_unread": sorted(unread),
        "hashes_readable": len(rows) - len(unread),
        "dropped": dropped,
        "gate": ("RUSTDOCFLAGS in 0 changed lists, the strip clause naming "
                 "it on 61 of 61, and E4′'s four relocated keys on 61 of "
                 "61"),
    }
    # What BLOCKS a reading, told apart from what merely qualifies it. A
    # short loop and a capped changed list are both not-measured (§1.4 gives
    # H2 no reduced reading to fall back on, unlike H4's K-alone branch);
    # the unread rt hashes qualify a REPORTED cell and never the gate.
    blocking = subset_reasons(two, e4pp.GATE_N, "arm-A loop") + [
        f"the membership question could not be answered on {len(bounded)} "
        f"pair(s) whose changed list printed at its cap"] * bool(bounded)
    out["as_predicted"] = None if blocking else bool(
        out["rustdocflags_in_changed"] == e4pp.EXPECTED_RUSTDOCFLAGS_IN_CHANGED
        and out["strip_clause_named"] == e4pp.EXPECTED_STRIP_CLAUSE_NAMED
        and out["relocated_set"] == expected
        and matches == e4pp.GATE_N)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H2: RUSTDOCFLAGS in {out['rustdocflags_in_changed']} changed "
         f"list(s); strip clause named on {out['strip_clause_named']}/"
         f"{len(rows)}; relocated set {out['relocated_set']}; hashes differ "
         f"on {differ}/{len(rows)}; {out['verdict']}")
    return out


# ---------------------------------------------------------------------- H3

def phase_h3_verdict_pair(two: dict) -> dict:
    """H3: is the verdict untouched and the pair still found?

    E4′'s H2 and H3 read together -- §1.2's named translation -- because
    neither the comparator nor the pairing is changed by this slice, and a
    record that gated them apart would report one endpoint twice.

    The printed WORD and the process EXIT are two readings of one fact and
    are never derived from each other: a disagreement is the finding, and
    it is reported as one rather than resolved in favour of either.
    """
    mark_load("H3")
    rows = _measured(two)
    words, disagree, non_match, unread = {}, [], [], []
    counts, wrong, excluded = {}, [], {}
    for r in rows:
        name = r["name"]
        word = r.get("verdict_word")
        words[name] = word
        if word is None:
            unread.append(name)
        elif word != "MATCH":
            non_match.append({"name": name, "verdict": word,
                              "original": r.get("original"),
                              "pair": r.get("new_run")})
        if r.get("verdict_and_exit_agree") is False:
            disagree.append({"name": name, "word": word, "exit": r.get("rc")})
        pair = r.get("pair") or {}
        counts[name] = pair.get("n")
        if pair.get("n") != 1:
            wrong.append({"name": name, "n": pair.get("n"),
                          "original": r.get("original"),
                          "qualifying": pair.get("qualifying"),
                          "linked": pair.get("linked")})
        children = r.get("excluded_children_in_the_store") or []
        if children:
            excluded[name] = children
    match_n = sum(1 for w in words.values() if w == "MATCH")
    ones = sum(1 for c in counts.values() if c == 1)
    out = {
        "n": len(rows), "headline": match_n, "verdicts": words,
        "non_match": non_match, "unread": unread,
        "word_and_exit_disagree": disagree,
        "pairs_of_one": ones, "pair_counts": counts, "not_one": wrong,
        "excluded_children": len(excluded),
        "excluded_children_by_pair": excluded,
        "dropped": subset_reasons(two, e4pp.GATE_N, "arm-A loop"),
        "gate": "MATCH 61 of 61 and 61 pairs of exactly one",
    }
    # `not wrong` beside `ones == len(rows)`: two readings of the same
    # fact, and a gate that kept only one of them survived the mutation
    # that flipped the other's comparison.
    out["as_predicted"] = None if out["dropped"] else bool(
        match_n == e4pp.EXPECTED_MATCH and ones == e4pp.EXPECTED_PAIRS_OF_ONE
        and not wrong and not unread)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H3: MATCH {match_n}/{len(rows)}; pairs of one {ones}/{len(rows)}; "
         f"word/exit disagreements {len(disagree)}; excluded-children rows "
         f"{len(excluded)}; {out['verdict']}")
    return out


# ---------------------------------------------------------------------- H4

def _session_keys_cited(row: dict) -> list[str]:
    """The session-set keys a WITHHELD pair's environment caveat named.

    Read from the `env:` line's CHANGED list -- the same names the caveat
    prints in its brackets -- because that list is the one that withholds.
    A granted pair cites nothing by construction and is not consulted.
    """
    if (row.get("licence_partition") or {}).get("licence") != "WITHHELD":
        return []
    return sorted(k for k in (row.get("env_changed_keys") or [])
                  if is_session_key(k))


def phase_h4_session(two: dict, session_differs) -> dict:
    """H4: do session differences stay outside the vote?

    Compared against `pins.session_keys_differing`, recorded at PREFLIGHT
    and passed in here -- never against a set read out of the same printed
    lines this phase is checking, which would make the check circular.

    §1.4's kill 7 is PRE-COMMITTED for this row: where any pair printed its
    session list at the cap, `session_names` goes `null` with its reason
    and the gate is decided on K ALONE. The reduced reading is published as
    the lens and the record states plainly that the by-name half went
    unread.
    """
    mark_load("H4")
    rows = _measured(two)
    pin = sorted(session_differs or [])
    names_by, k_by, bounded, cites, empty = {}, {}, [], [], []
    unread = []
    line, fact = None, None
    for r in rows:
        name = r["name"]
        # `None` is UNREAD, and `[]` is "the line printed none". Turning the
        # first into the second made an unread line MATCH an empty pin --
        # the one place this endpoint could count a reading nobody made.
        printed = r.get("env_session_keys")
        names_by[name] = None if printed is None else sorted(printed)
        k_by[name] = r.get("env_session_n")
        if printed is None or k_by[name] is None:
            unread.append(name)
            continue
        if r.get("env_session_keys_truncated"):
            bounded.append(name)
        if not names_by[name] and not k_by[name]:
            empty.append(name)
        cited = _session_keys_cited(r)
        if cited:
            cites.append({"name": name, "keys": cited})
        if line is None and (r.get("licence_partition") or {}).get(
                "licence") == "granted":
            line = r.get("env_line")
            fact = next((f for f in (r.get("licence_facts") or [])
                         if "environment variable" in f
                         or "session set" in f), None)
    distinct = sorted({tuple(v) for v in names_by.values() if v is not None})
    dropped = subset_reasons(two, e4pp.GATE_N, "arm-A loop")
    if unread:
        dropped.append(
            f"{len(unread)} pair(s) printed no session clause this reader "
            f"could read ({unread[:3]}); an unread line matches no pin, so "
            "they count towards neither the names nor K")
    if bounded:
        dropped.append(f"{len(bounded)} pair(s) printed a session list at "
                       f"its cap ({bounded[:3]}); " + CAPPED
                       + " -- H4 is decided on K alone")
    elif len(distinct) > 1:
        dropped.append(
            "the pairs did not agree on the printed session set: "
            f"{[list(d) for d in distinct]}; the per-pair sets are under "
            "`session_names_by_name`")
    out = {
        "n": len(rows),
        "session_names": (None if bounded or unread or len(distinct) != 1
                          else list(distinct[0])),
        "session_names_seen": [list(d) for d in distinct],
        "session_names_by_name": names_by,
        "session_names_unread": sorted(unread),
        "session_names_match": sum(1 for v in names_by.values()
                                   if v is not None and v == pin),
        "session_k": (None if len({k for k in k_by.values()
                                   if k is not None}) != 1
                      else next(k for k in k_by.values() if k is not None)),
        "session_k_by_name": k_by,
        "session_k_match": sum(1 for v in k_by.values()
                               if v is not None and v == len(pin)),
        "withholding_cites_a_session_key": cites,
        "pin": pin, "pin_n": len(pin),
        "decided_on_k_alone": bool(bounded),
        "names_bounded": sorted(bounded),
        # The second reading, §1.4's own: the exact line and fact on a
        # granted pair, and the pairs whose session set was EMPTY (which on
        # this box §1.3's rule 3 says it should not be).
        "line_on_a_granted_pair": line,
        "fact_on_a_granted_pair": fact,
        "pairs_with_an_empty_session_set": len(empty),
        "empty_session_set_pairs": sorted(empty),
        "dropped": dropped,
        "gate": ("the printed session set equals `pins.session_keys_"
                 "differing` by name and by size on 61 of 61, and no "
                 "withholding reason cites a key of session set 1"),
    }
    by_name_ok = (out["session_names_match"] == e4pp.GATE_N
                  if not bounded else True)
    # The CAP does not block: §1.4 pre-commits the reduced reading -- names
    # null with their reason, the gate decided on K alone. A short loop and
    # an unread line do block, because neither leaves a reading to reduce.
    blocking = subset_reasons(two, e4pp.GATE_N, "arm-A loop") + (
        [f"{len(unread)} pair(s) printed no session clause this reader could "
         "read"] if unread else [])
    out["as_predicted"] = None if blocking else bool(
        by_name_ok and out["session_k_match"] == e4pp.GATE_N and not cites)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H4: names {out['session_names']} (match "
         f"{out['session_names_match']}/{len(rows)}), K {out['session_k']} "
         f"(match {out['session_k_match']}/{len(rows)}) against the pin "
         f"{pin}; withholdings citing a session key {len(cites)}; "
         f"{out['verdict']}")
    return out


# ---------------------------------------------------------------------- H5

def phase_h5_input(arm_b: dict) -> dict:
    """H5: does the licence still bite outside the set?

    Arm B is WITHHELD 4 of 4, each env caveat naming `E4PP_INPUT`. ANY
    granted line here is a STOP: the exemption ate the rule, and the slice
    would have bought its own control's silence.

    The second reading is `thread_reason_kept` -- the pager row still
    carries its one-program-thread reason alongside the env caveat. A
    control that SILENCED the thread reason is a finding, and it is
    reported rather than gated.
    """
    mark_load("H5")
    rows = _measured(arm_b)
    key = (arm_b or {}).get("key")
    withheld, granted, names_key, unread, bounded = [], [], [], [], []
    for r in rows:
        word = (r.get("licence_partition") or {}).get("licence")
        if word is None:
            unread.append(r["name"])
            continue
        if word == "granted":
            granted.append(r["name"])
            continue
        withheld.append(r["name"])
        # The printed changed list is capped at eight names, exactly as H2's
        # is: on a longer one the key's absence from the NAMES is not its
        # absence from the list, and the by-name half of this reading cannot
        # be made at all.
        if r.get("env_changed_keys_truncated"):
            bounded.append(r["name"])
        elif key in (r.get("env_changed_keys") or []):
            names_key.append(r["name"])
    pager = (arm_b or {}).get("by_name", {}).get(
        "a_pager_can_be_shared_across_threads") or {}
    pager_threads = (pager.get("licence_partition") or {}).get(
        "program_threads")
    # `False` said "the control silenced the thread reason", which is a
    # FINDING about the control. A row whose licence never printed says
    # nothing of the kind, so it is `None` with the reason instead.
    thread_kept = None if not pager or pager_threads is None else (
        pager_threads == 1)
    thread_reason = (
        None if thread_kept is not None else
        ("arm B ran no `a_pager_can_be_shared_across_threads` row"
         if not pager else
         "the pager row's licence printed no thread count, so whether its "
         "thread reason survived the env caveat could not be read"))
    dropped = subset_reasons(arm_b, e4pp.ARM_N, "arm B")
    if bounded:
        dropped.append(f"{len(bounded)} pair(s) printed a changed list at "
                       f"its cap ({bounded[:3]}); " + CAPPED)
    out = {
        "n": len(rows), "key": key,
        "headline": len(withheld), "withheld": sorted(withheld),
        "granted": sorted(granted), "unread": unread,
        "env_caveat_names_the_key": (None if bounded else len(names_key)),
        "env_caveat_missing_the_key": sorted(
            set(withheld) - set(names_key) - set(bounded)),
        "changed_lists_bounded": sorted(bounded),
        "verdicts": {r["name"]: r.get("verdict_word") for r in rows},
        "thread_reason_kept": thread_kept,
        "thread_reason_reason": thread_reason,
        "dropped": dropped,
        "gate": (f"WITHHELD 4 of 4, each env caveat naming `{key}`; any "
                 "granted line is a STOP"),
    }
    blocking = subset_reasons(arm_b, e4pp.ARM_N, "arm B") + [
        f"the by-name half could not be read on {len(bounded)} pair(s) whose "
        f"changed list printed at its cap"] * bool(bounded)
    out["as_predicted"] = None if blocking else bool(
        len(withheld) == e4pp.ARM_N and not granted
        and out["env_caveat_names_the_key"] == e4pp.ARM_N)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H5: WITHHELD {out['headline']}/{len(rows)}; caveat names {key} on "
         f"{out['env_caveat_names_the_key']}; thread reason kept "
         f"{thread_kept}; {out['verdict']}")
    return out


# ---------------------------------------------------------------------- H6

def phase_h6_session_key(two: dict, arm_c: dict, session_differs,
                         key) -> dict:
    """H6: is the session count exact, and the word unmoved?

    `key` is `pins.injected_session_key`, DERIVED from the preflight and
    never re-chosen here: the gate reads the pin and the second reading
    reports the cell, so the two cannot differ. The expected set is the
    preflight's ∪ the chosen key, with K exactly one greater.

    Arm A's word for the same ROW is the comparison, so a row is compared
    against itself under two environments and never against §1.2's
    expectation, which arm A has already been gated on.
    """
    mark_load("H6")
    rows = _measured(arm_c)
    by_a = {r["name"]: r for r in _measured(two)}
    pin = sorted(session_differs or [])
    expected = sorted(set(pin) | ({key} if key else set()))
    same, moved, names_by, k_by, bounded = [], [], {}, {}, []
    unread = []
    for r in rows:
        name = r["name"]
        word = (r.get("licence_partition") or {}).get("licence")
        arm_a_word = ((by_a.get(name) or {}).get("licence_partition")
                      or {}).get("licence")
        (same if word is not None and word == arm_a_word else moved).append(
            {"name": name, "arm_c": word, "arm_a": arm_a_word})
        # `None` is UNREAD here for the same reason it is in H4: a line
        # nobody read matches no expected set.
        printed = r.get("env_session_keys")
        names_by[name] = None if printed is None else sorted(printed)
        k_by[name] = r.get("env_session_n")
        if printed is None or k_by[name] is None:
            unread.append(name)
            continue
        if r.get("env_session_keys_truncated"):
            bounded.append(name)
    distinct = sorted({tuple(v) for v in names_by.values() if v is not None})
    dropped = (subset_reasons(arm_c, e4pp.ARM_N, "arm C")
               + subset_reasons(two, e4pp.GATE_N, "arm-A loop this arm is "
                                                  "compared against"))
    if unread:
        dropped.append(
            f"{len(unread)} pair(s) printed no session clause this reader "
            f"could read ({unread[:3]}); an unread line matches no expected "
            "set")
    if bounded:
        dropped.append(f"{len(bounded)} pair(s) printed a session list at "
                       f"its cap ({bounded[:3]}); " + CAPPED)
    if len(distinct) > 1:
        dropped.append(
            "the pairs did not agree on the printed session set: "
            f"{[list(d) for d in distinct]}; the per-pair sets are under "
            "`session_names_by_name`")
    out = {
        "n": len(rows), "headline": len(same),
        "word_matches_arm_a": same, "word_moved": moved,
        "injected_key": key,
        # MEASURED, even when it is not the expected one. §1.3: a `null`
        # with a reason is the only not-measured, and a set every pair
        # printed WAS measured -- that it disagrees with the pin ∪ the key
        # is what `session_names_match` and the verdict are for.
        "session_names": (None if bounded or unread or len(distinct) != 1
                          else list(distinct[0])),
        "session_names_seen": [list(d) for d in distinct],
        "session_names_by_name": names_by,
        "session_names_unread": sorted(unread),
        "session_names_match": sum(1 for v in names_by.values()
                                   if v is not None and v == expected),
        "session_k": (None if len({k for k in k_by.values()
                                   if k is not None}) != 1
                      else next(k for k in k_by.values() if k is not None)),
        "session_k_by_name": k_by,
        "session_k_match": sum(1 for v in k_by.values()
                               if v is not None and v == len(expected)),
        "expected_session_names": expected, "pin": pin,
        "expected_k": len(expected),
        "dropped": dropped,
        "gate": ("the licence word equals arm A's on 4 of 4, and the "
                 "printed session set is `pins.session_keys_differing` ∪ "
                 "{`pins.injected_session_key`} with K exactly one greater"),
    }
    blocking = (subset_reasons(arm_c, e4pp.ARM_N, "arm C")
                + subset_reasons(two, e4pp.GATE_N,
                                 "arm-A loop this arm is compared against")
                + [f"{len(unread)} unread session clause(s)"] * bool(unread)
                + [f"{len(bounded)} capped session list(s)"] * bool(bounded))
    out["as_predicted"] = None if blocking else bool(
        not moved and out["session_names_match"] == e4pp.ARM_N
        and out["session_k_match"] == e4pp.ARM_N and key)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H6: word matches arm A on {out['headline']}/{len(rows)}; session "
         f"names {out['session_names']} (expected {expected}); K "
         f"{out['session_k']}; injected {key}; {out['verdict']}")
    return out


# ---------------------------------------------------------------------- H7

def _null_partition_cells(block: dict, arm: str) -> list[dict]:
    """Every pair whose licence PRINTED but whose thread arithmetic did
    not. The three cells H1 reads, and no others: whether the licence's own
    sentence named the exclusion is a fact about the WORDING and is H1's
    second reading, not an instrument failure."""
    out = []
    for r in _measured(block):
        part = r.get("licence_partition") or {}
        if part.get("licence") is None:
            continue
        missing = [c for c in ("program_threads", "harness_threads",
                               "counts_source") if part.get(c) is None]
        if missing:
            out.append({"name": r["name"], "arm": arm, "cells": missing,
                        "reason": part.get("counts_unread_reason")})
    return out


def phase_h7_instrument(raw: dict) -> dict:
    """H7: is the instrument honest? A STOP here is a STOP OF THE
    INSTRUMENT, and the record says so rather than reporting it as a
    finding about the subject.

    Four gates, and each closes one of E4′ §5's own gaps:

    * no partition cell is `None` on a pair whose licence printed (gap 1);
    * every thread count carries the line it came from (gap 1's other
      half);
    * `licence_verified_counts` is non-null (gap 7 -- E4′ named a field
      every reader found null);
    * the version probe is a token, or `null` WITH its reason, and never an
      empty string (gap 2).
    """
    mark_load("H7")
    arms_blocks = (("armA", raw.get("raw_pass2")),
                   ("armB", raw.get("raw_arm_b")),
                   ("armC", raw.get("raw_arm_c")))
    nulls, sources, sourceless = [], {}, []
    for arm, block in arms_blocks:
        if not block:
            continue
        nulls += _null_partition_cells(block, arm)
        for r in _measured(block):
            part = r.get("licence_partition") or {}
            if part.get("licence") is None:
                continue
            sources[f"{arm}/{r['name']}"] = part.get("counts_source")
            if part.get("counts_source") is None:
                sourceless.append(f"{arm}/{r['name']}")
    counts = licence_verified_counts(raw)
    probe = ((raw.get("pins") or {}).get("sensorium_version_metadata_probe")
             or {})
    token, reason = probe.get("token"), probe.get("reason")
    probe_ok = bool(token) or (token is None and bool(reason))
    out = {
        "headline": len(nulls), "null_cells": nulls,
        # The denominator this endpoint's numbers are over: every row of
        # every arm that came back with a licence WORD. Not the 61, and not
        # 69 either -- a row whose licence never printed has no partition to
        # be honest or dishonest about.
        "censused": len(sources),
        "counts_source_by_row": sources,
        "counts_without_a_source_line": sorted(sourceless),
        "counts_carry_their_source_line": bool(sources) and not sourceless,
        "licence_verified_counts": counts,
        "version_probe": {"token": token, "reason": reason,
                          "rc": probe.get("rc"),
                          "command": probe.get("command")},
        "version_probe_ok": probe_ok,
        "dropped_lists": _every_dropped(raw),
        "stop_is_of_the": ("instrument, not of the subject: §1.4's kill 2 "
                           "distinguishes the two in the record"),
        "dropped": [],
        "gate": ("0 null partition cells on a printed licence, every count "
                 "carrying its source line, non-null verified counts, and a "
                 "version probe that is a token or null WITH its reason"),
    }
    out["as_predicted"] = bool(
        not nulls and out["counts_carry_their_source_line"]
        and counts is not None and probe_ok)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H7: {len(nulls)} null partition cell(s); source lines carried "
         f"{out['counts_carry_their_source_line']}; verified counts "
         f"{'present' if counts else 'MISSING'}; probe token {token!r} "
         f"reason {reason!r}; {out['verdict']}")
    return out


def _every_dropped(raw: dict) -> dict:
    """Every `dropped` list this run wrote, by phase -- H7's second reading.

    A record whose drops are scattered through eight blocks is one nobody
    reads; collected here, "what this run could not measure" is one list.
    """
    out = {}
    for key, block in sorted((raw or {}).items()):
        if key.startswith("raw_") and isinstance(block, dict):
            reasons = block.get("dropped")
            if reasons:
                out[key] = list(reasons)
    return out


__all__ = ["CAPPED", "LOGS", "corpus_case_names", "phase_h1",
           "read_rt_hashes", "subset_reasons",
           "phase_h2_fragment", "phase_h3_verdict_pair", "phase_h4_session",
           "phase_h5_input", "phase_h6_session_key", "phase_h7_instrument",
           "phase_h8_nothing_else"]
