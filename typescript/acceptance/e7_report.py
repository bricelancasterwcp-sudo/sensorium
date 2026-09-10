"""E7''s JSON: the leak grep over the saved transcript, and the vectors.

The eight needles are the pre-registered list, and each is matched as the
LITERAL it is, case-insensitively. That matters for one of them: `python ?`
is not "the word python" -- it is `info`'s interpreter line as the spike
caught it printing on a TypeScript trace (`python ?  env:6fc1f0a9…`), the
`?` standing where a Python version would be. Matched as a regex with the
space optional, it also matches every honest sentence that names the
language, such as the `exceptions` refusal that says the Python rules index
an identity this trace does not carry -- a sentence that tells a TypeScript
user why a command refuses, which is the opposite of a leak. That misreading
was found in a dry run on `typescript/probes` and fixed here before any
number of this endpoint was read.

`threading/_thread` is the one needle matched as a pattern rather than a
literal: it names two Python module spellings, and bare `_thread` is a
substring of this recorder's own `main_thread_ident`. Word boundaries keep
it pointed at the module and off the recorder's vocabulary.

Beside the gate, and gating nothing, the transcript's bare mentions of
`python` and `rust` are counted too: a reader that names another language in
a sentence written FOR this one is worth seeing in the record even though the
pre-registration does not refuse it.

`value` is the total number of gated occurrences, whose PASS is 0.
"""
import os
import re
import sys
from pathlib import Path

from lens import cell, emit

#: The pre-registered leak list. `(name, pattern, is_regex, case_sensitive)`;
#: rung 1's eight, every one of them case-INsensitive, which is the fourth
#: field's default here and the reading that list was measured under.
NEEDLES = (
    ("asyncio", "asyncio", False, False),
    ("python ?", "python ?", False, False),
    ("cargo", "cargo", False, False),
    ("coroutine", "coroutine", False, False),
    ("Python's own", "Python's own", False, False),
    ("threading/_thread", r"\bthreading\b|\b_thread\b", True, False),
    ("Rust disposition", "Rust disposition", False, False),
    ("sensorium run --focus", "sensorium run --focus", False, False),
)

#: S5 rung 2's list, from that rung's own §1: `oid`, `chain`, `Err`,
#: `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`,
#: `Python's own`.
#:
#: THREE OF THEM ARE MATCHED AS WORDS AND CASE-SENSITIVELY, and that reading
#: was fixed before any number of that rung was read -- for exactly the
#: reason this module's docstring already records about `python ?`. `oid`,
#: `chain` and `Err` are identifiers in the OTHER recorders' vocabularies:
#: Rust's `Result::Err`, the Python reader's object ids, the Rust reader's
#: chains. Matched as case-insensitive substrings, each is satisfied by this
#: recorder's own English -- `Err` by every `Error('…')` a verdict prints,
#: `oid` by "avoid", `chain` by "describe_chain" -- so the endpoint could not
#: be passed by any answer that named an exception type, which measures
#: nothing. Word-bounded and case-sensitive, each matches the token it names.
#: The prose needles stay case-insensitive, as they were.
NEEDLES_RUNG2 = (
    ("oid", r"\boid\b", True, True),
    ("chain", r"\bchain\b", True, True),
    ("Err", r"\bErr\b", True, True),
    ("asyncio", "asyncio", False, False),
    ("python ?", "python ?", False, False),
    ("cargo", "cargo", False, False),
    ("coroutine", "coroutine", False, False),
    ("Rust disposition", "Rust disposition", False, False),
    ("Python's own", "Python's own", False, False),
)

#: `E7_NEEDLES=rung2` selects that list; anything else keeps rung 1's. Both
#: live here, committed, rather than arriving on a command line: the
#: population an endpoint counts over is part of the instrument.
LISTS = {"rung2": NEEDLES_RUNG2}

#: Counted and printed, never gated: see the module docstring.
CONTEXT = ("python", "rust", "asyncio task")


def main() -> int:
    env = os.environ
    text = Path(env["E7_TRANSCRIPT"]).read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    needles = LISTS.get(env.get("E7_NEEDLES", ""), NEEDLES)
    found = {}
    total = 0
    for name, pattern, is_regex, cased in needles:
        rx = pattern if is_regex else re.escape(pattern)
        # A case-SENSITIVE needle is matched against the text as printed; the
        # case-insensitive ones keep the lowercased copy they always used.
        hits = (re.findall(rx, text) if cased
                else re.findall(rx, lowered, flags=re.IGNORECASE))
        found[name] = len(hits)
        total += len(hits)
    context = {word: len(re.findall(re.escape(word), lowered,
                                    flags=re.IGNORECASE))
               for word in CONTEXT}

    statuses = []
    for line in Path(env["E7_STATUSES"]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        label, _, code = line.partition("\t")
        statuses.append({"command": label, "exit": int(code) if code.strip() else None})

    vectors_text = Path(env["E7_VECTORS"]).read_text(encoding="utf-8", errors="replace")
    vectors_line = next((ln for ln in reversed(vectors_text.splitlines())
                         if ln.strip()), "")

    emit(cell(
        total, len(needles),
        needle_list=env.get("E7_NEEDLES") or "rung1",
        needles={n: p for n, p, _r, _c in needles},
        case_sensitive=sorted(n for n, _p, _r, c in needles if c),
        occurrences=found,
        context_mentions_not_gated=context,
        commands=statuses,
        transcript_lines=len(text.splitlines()),
        vectors={"selector": env.get("E7_VECTORS_K"),
                 "exit": int(env["E7_VECTORS_STATUS"]),
                 "summary": vectors_line.strip(),
                 "green": int(env["E7_VECTORS_STATUS"]) == 0},
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
