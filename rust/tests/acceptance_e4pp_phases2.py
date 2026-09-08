#!/usr/bin/env python3
"""E4″'s H8: did nothing else move?

A module of its own for the reason `acceptance_e4p_phases2` is one -- this
project's 800-line ceiling, which `acceptance_e4pp_phases` reached when the
subset guard and the unread-reading branches landed in fix round 1. H8 is
the natural cut: it is the only phase that runs COMMANDS rather than
reading rows, and the only one that is about this repository rather than
about the subject.
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4p_phases2 as eph2                              # noqa: E402
import acceptance_e4pp_rows as e4pp                                # noqa: E402
from acceptance_lib import REPO, step                              # noqa: E402

LOGS: Path | None = None


def _verdict(ok) -> str:
    """`None` is not a pass -- `acceptance_e4pp_phases._verdict`'s rule,
    spelled here so this module stands alone."""
    return "PASS" if ok is True else "STOP"


# ---------------------------------------------------------------------- H8

def corpus_case_names(paths) -> dict:
    """The corpus collector's OWN case list, by name.

    `run_corpus.py --json` publishes counts, not names -- E4′ §5's gap 3,
    which left `refocus_child_run_present` null and H6's "the new case
    included" unchecked. §1.4 makes the same reading a GATE here, so the
    names come from `load_cases()`, the very function the run iterates,
    asked in a child of its own. Cheap, and it builds nothing.
    """
    from acceptance_e4p_preflight import out_err
    py = str(REPO / ".venv" / "bin" / "python")
    res = out_err(py, "-c",
                  "import json, sys; sys.path.insert(0, '.'); "
                  "from corpus.run_corpus import load_cases; "
                  "print(json.dumps(sorted(c.name for c in load_cases())))")
    rec = {"command": res["command"], "rc": res["rc"], "names": None,
           "reason": None, "stderr": res["err"] or None}
    if res["rc"] != 0 or not res["out"]:
        rec["reason"] = (res["err"].splitlines()[-1].strip() if res["err"]
                         else f"the listing exited {res['rc']} and printed "
                              "nothing")
        return rec
    try:
        rec["names"] = _json.loads(res["out"].splitlines()[-1])
    except (ValueError, TypeError) as e:
        rec["reason"] = f"the listing did not parse as JSON: {e}"
    return rec


def phase_h8_nothing_else(paths, cfg) -> dict:
    """H8: did nothing else move? THIS repository, never the clone.

    E4′'s H6 with two differences §1.4 requires. The corpus runs WITH the
    driver (`--require-driver`, so a case nobody could run is a verdict on
    the run rather than a skip inside a green summary), and
    `spawned_test_fn_present` is read from the collector's own case list
    instead of from a JSON that publishes no names.

    Three commands, three return codes, each its own field: a summary line
    is prose and does not decide a gate.
    """
    rec = eph2.phase_h6(paths, cfg)
    listing = corpus_case_names(paths)
    corpus, python, cargo = (rec.get("corpus") or {}, rec.get("python") or {},
                             rec.get("cargo") or {})
    names = listing.get("names")
    present = (None if names is None else e4pp.SPAWNED_CASE in names)
    skipped = [s for s in ((corpus.get("json") or {}).get("skipped") or [])
               if isinstance(s, dict)]
    out = {
        "corpus_rc": corpus.get("rc"),
        "pytest_rc": python.get("rc"),
        "cargo_rc": cargo.get("rc"),
        "pytest_summary": python.get("summary"),
        "corpus_cases": corpus.get("cases"),
        "corpus_failures": corpus.get("failures"),
        "corpus_errors": corpus.get("errors"),
        "corpus_skipped": skipped,
        "corpus_require_driver": (corpus.get("json") or {}).get(
            "require_driver"),
        "corpus_args": list(cfg.get("corpus_args") or []),
        "spawned_test_fn": e4pp.SPAWNED_CASE,
        "spawned_test_fn_present": present,
        "spawned_test_fn_skipped": [s for s in skipped
                                    if s.get("case") == e4pp.SPAWNED_CASE],
        "case_listing": listing,
        "cargo_result_lines": cargo.get("result_lines"),
        "logs": {"corpus": corpus.get("log"), "pytest": python.get("log"),
                 "cargo": cargo.get("log")},
        "raw": rec,
        "dropped": ([] if names is not None else
                    [f"the corpus case listing could not be read "
                     f"({listing.get('reason')}), so whether "
                     f"`{e4pp.SPAWNED_CASE}` is present went UNREAD"]),
        "gate": ("corpus rc 0 with `--require-driver` and the spawned-test "
                 "case present, pytest rc 0, `cargo test --workspace` rc 0"),
    }
    out["as_predicted"] = bool(
        out["corpus_rc"] == 0 and out["pytest_rc"] == 0
        and out["cargo_rc"] == 0 and present is True)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H8: corpus rc {out['corpus_rc']} (args {out['corpus_args']}, "
         f"{e4pp.SPAWNED_CASE} present={present}); pytest rc "
         f"{out['pytest_rc']}; cargo rc {out['cargo_rc']}; {out['verdict']}")
    return out


__all__ = ["LOGS", "corpus_case_names", "phase_h8_nothing_else"]
