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
    "café 日"  -> "café 日"    (Debug escapes neither: non-ASCII is printable)
    "a\"b"     -> "a\\"b"      (`"` and `\\` are escaped, `'` is NOT)
    '\\x07'     -> "\\u{7}"      (unprintables, minimal lowercase hex)
    None       -> "None"       (an `Option`, printed as the word)

`inf` and `NaN` are Rust's own spellings for the two floats that are not
decimal, and `read_debug` deliberately leaves them as TEXT: a predicate
comparing against the word `inf` is one a reader can see, and a float
silently conjured out of a word is not.

THE ONE THING NEITHER DIRECTION DOES
------------------------------------
Guess. `read_debug` returns the text itself whenever the text spells no
literal (a struct, an enum, a `Vec`), because the text is what the trace
holds; `debug_text` returns None for a target that has no Rust spelling,
and a capture then matches nothing rather than matching approximately.
"""
import re

# A Debug integer, and a Debug float -- which requires a decimal POINT. Rust
# prints an exponent form for the extremes (`1e20`), and those stay text on
# purpose: reading `1e20` as a float would make `x > 3` answer at a site
# whose capture the reader has no reason to believe is numeric.
_INT = re.compile(r"-?\d+")
_FLOAT = re.compile(r"-?\d+\.\d+([eE][-+]?\d+)?")
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
    """The value a Debug text spells: int, float, bool, str, or the text.

    The caller has already dealt with truncation -- a clipped rendering is
    not a rendering, and nothing here may be applied to a prefix.
    """
    if _INT.fullmatch(text):
        return int(text)
    if _FLOAT.fullmatch(text):
        return float(text)
    if text in ("true", "false"):
        return text == "true"
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
        return _EXP.sub(r"e\1\2", repr(target))
    if isinstance(target, str):
        return '"' + escape_debug(target) + '"'
    return None
