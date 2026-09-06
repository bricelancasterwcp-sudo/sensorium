"""Rust `Debug` text: read one way, written one way, one escape table.

A `dbg` capture is what a probe got out of a value's own `Debug` impl --
TEXT, and the only thing a recorder can get for a type it cannot decompose.
Two commands have to make sense of that text and they must not disagree:
`watch --expr` READS it (`read_debug`, the value the text spells) and
`flow --value` WRITES it (`debug_text`, the rendering a literal would have).
An escape undone in one and re-applied differently in the other would report
a sighting that the predicate at the same site then denies, so both live
here, over one table.

WHAT IS PINNED, AND HOW IT WAS ESTABLISHED
------------------------------------------
Rust's spellings were MEASURED with `rustc` (2026-09-06), not assumed, and
two of them differ from Python's `repr` in ways no reader would guess:

    2.0        -> "2.0"        (same as repr)
    1e20       -> "1e20"       (repr says `1e+20`)
    1e-5       -> "1e-5"       (repr says `1e-05`)
    "café"     -> "café"       (Debug escapes neither: non-ASCII is printable)
    inf/-inf   -> "inf"/"-inf"  and NaN -> "NaN" (measured, all three)
    "a\"b"     -> "a\\"b"      (`"` and `\\` are escaped, `'` is NOT)
    '\\x07'     -> "\\u{7}"      (unprintables, minimal lowercase hex)
    None       -> "None"       (an `Option`, printed as the word)

THE TWO DIRECTIONS ARE INVERSES ON THE LITERAL DOMAIN
-----------------------------------------------------
Design amendment A11: `read_debug` parses exactly what `debug_text` can
spell, so `resolve(dbg(debug_text(L))) == L` for every literal `L` a
command accepts. This is not tidiness -- it is the fix for a measured
disagreement. With `read_debug` stopping at the decimal forms, `flow
--value 1e20` reported a sighting of a capture that `watch --expr x ==
1e20` at that same site then denied (a plain False out of comparing text
with a float), and the same went for `1e400`/`inf` and for `None`. One
instrument answering yes and no about one capture is worse than either
answer, so the domains are pinned together: integers, floats in every
Debug spelling Rust uses (`2.5`, `1e20`, `1e-5`, `inf`, `-inf`, `NaN`),
`true`/`false`, the bare `None`, and quoted strings.

THE ONE THING NEITHER DIRECTION DOES
------------------------------------
Guess. `read_debug` returns the text itself whenever the text spells no
literal (a struct, an enum, a `Vec`), because the text is what the trace
holds; `debug_text` returns None for a target that has no Rust spelling,
and a capture then matches nothing rather than matching approximately.
"""
import re

# A Debug integer, and a Debug float -- a decimal POINT, an EXPONENT, or
# both, which is every shape Rust prints (`2.5`, `1e20`, `1e-5`, `1.5e-7`).
# The integer is tried first, so `5` is an int and never a float.
_INT = re.compile(r"-?\d+")
_FLOAT = re.compile(r"-?\d+\.\d+([eE][-+]?\d+)?|-?\d+([eE][-+]?\d+)")
# The three floats Rust spells as words rather than digits (measured).
_WORD_FLOATS = {"inf": float("inf"), "-inf": float("-inf"),
                "NaN": float("nan")}
# Python's repr writes an exponent's sign and pads it to two digits; Rust
# writes neither. `1e+20` -> `1e20`, `1e-05` -> `1e-5`.
_EXP = re.compile(r"e\+?(-?)0*(\d)")

# `\'` never appears in a string's Debug (Rust escapes a single quote only
# inside a char's), and it is read anyway: undoing an escape the writer did
# not have to make is harmless, refusing one is not.
_UNESCAPE = {"n": "\n", "t": "\t", "r": "\r", "0": "\0",
             "\\": "\\", '"': '"', "'": "'"}
_ESCAPE = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t",
           "\r": "\\r", "\0": "\\0"}
_HEX = "0123456789abcdefABCDEF"


def read_debug(text: str):
    """The value a Debug text spells: int, float, bool, None, str, or text.

    The caller has already dealt with truncation -- a clipped rendering is
    not a rendering, and nothing here may be applied to a prefix.
    """
    if _INT.fullmatch(text):
        return int(text)
    if _FLOAT.fullmatch(text):
        return float(text)
    if text in _WORD_FLOATS:
        return _WORD_FLOATS[text]
    if text in ("true", "false"):
        return text == "true"
    if text == "None":
        # `Option::None`, and the one way a reader can name it: `flow
        # --value None` already searches for this text, so a predicate at
        # the same site has to see the same thing (A11).
        return None
    if len(text) >= 2 and text[0] == '"' == text[-1]:
        return unescape_debug(text[1:-1])
    return text


def unescape_debug(inner: str) -> str:
    r"""The characters a Debug string's body stands for.

    Hand-written rather than `codecs.decode(.., "unicode_escape")`, which
    decodes latin-1 and so turns every non-ASCII character Rust printed
    literally into mojibake -- `"café"` would come back as `cafÃ©` and
    compare unequal to the string the program held.

    An escape this table does not know is left EXACTLY as it was read: a
    reader comparing against text sees the same characters the trace holds,
    rather than a silent reinterpretation of them.
    """
    out: list[str] = []
    i, n = 0, len(inner)
    while i < n:
        ch = inner[i]
        if ch != "\\" or i + 1 >= n:
            out.append(ch)
            i += 1
            continue
        nxt = inner[i + 1]
        if nxt in _UNESCAPE:
            out.append(_UNESCAPE[nxt])
            i += 2
            continue
        if nxt == "u" and inner[i + 2:i + 3] == "{":
            end = inner.find("}", i + 3)
            digits = inner[i + 3:end] if end != -1 else ""
            if digits and all(c in _HEX for c in digits):
                try:
                    out.append(chr(int(digits, 16)))
                except ValueError:
                    pass                     # beyond U+10FFFF: leave it read
                else:
                    i = end + 1
                    continue
        out.append(ch)
        i += 1
    return "".join(out)


def escape_debug(s: str) -> str:
    """A string's characters as Rust's `Debug` prints them, without quotes.

    `str::escape_debug` escapes `\\` `"` and the unprintables and leaves
    everything else alone; `'` is escaped only in a char's Debug, never in a
    string's. `str.isprintable()` is Python's name for the same category
    test (Cc, Cf, Cs, Co, Cn, Zl, Zp and the non-space Zs are not printable
    in either language), so the two agree on which characters need `\\u{..}`.
    """
    out = []
    for ch in s:
        esc = _ESCAPE.get(ch)
        if esc is not None:
            out.append(esc)
        elif ch.isprintable():
            out.append(ch)
        else:
            out.append(f"\\u{{{ord(ch):x}}}")
    return "".join(out)


def debug_text(target) -> str | None:
    """How Rust's `Debug` would spell this literal, or None if it would not.

    None is the honest answer for anything with no Rust spelling (an
    `ObjTarget`, say): a capture then matches it nowhere, rather than
    matching something adjacent.
    """
    if target is None:
        return "None"                        # `Option::None`, as Rust prints
    if isinstance(target, bool):             # before int: a bool IS an int
        return "true" if target else "false"
    if isinstance(target, int):
        return str(target)
    if isinstance(target, float):
        if target != target:
            return "NaN"                     # `repr` says `nan`; Rust `NaN`
        return _EXP.sub(r"e\1\2", repr(target))
    if isinstance(target, str):
        return '"' + escape_debug(target) + '"'
    return None
