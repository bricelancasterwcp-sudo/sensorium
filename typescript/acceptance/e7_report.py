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

#: The pre-registered leak list. `(name, pattern, is_regex)`; every match is
#: case-insensitive.
NEEDLES = (
    ("asyncio", "asyncio", False),
    ("python ?", "python ?", False),
    ("cargo", "cargo", False),
    ("coroutine", "coroutine", False),
    ("Python's own", "Python's own", False),
    ("threading/_thread", r"\bthreading\b|\b_thread\b", True),
    ("Rust disposition", "Rust disposition", False),
    ("sensorium run --focus", "sensorium run --focus", False),
)

#: Counted and printed, never gated: see the module docstring.
CONTEXT = ("python", "rust", "asyncio task")


def main() -> int:
    env = os.environ
    text = Path(env["E7_TRANSCRIPT"]).read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    found = {}
    total = 0
    for name, pattern, is_regex in NEEDLES:
        rx = pattern if is_regex else re.escape(pattern)
        hits = re.findall(rx, lowered, flags=re.IGNORECASE)
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
        total, len(NEEDLES),
        occurrences=found,
        context_mentions_not_gated=context,
        commands=statuses,
        transcript_lines=len(text.splitlines()),
        vectors={"exit": int(env["E7_VECTORS_STATUS"]),
                 "summary": vectors_line.strip(),
                 "green": int(env["E7_VECTORS_STATUS"]) == 0},
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
