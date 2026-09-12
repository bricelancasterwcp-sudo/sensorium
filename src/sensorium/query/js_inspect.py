r"""JavaScript `util.inspect` text: read one way, written one way, one table.

The sibling of `rust_debug`, and for the same reason. A `dbg` capture is
what a probe got out of the language's own formatter -- TEXT, and the only
thing a recorder can get for a value it will not decompose. Two commands
have to make sense of that text and they must not disagree: `watch --expr`
READS it (`read_inspect`, the value the text spells) and `flow --value`
WRITES it (`inspect_text`, the rendering a literal would have). An escape
undone in one and re-applied differently in the other reports a sighting
that the predicate at the same site then denies, so both live here, over one
table.

WHAT IS PINNED, AND HOW IT WAS ESTABLISHED
------------------------------------------
By GENERATION, not by reading JavaScript's specification and hoping. Every
spelling below came out of `dbg()` -- the one function every capture this
recorder puts on the wire goes through -- under node v24.16.0 with the
recorder's own inspect options, and is committed as
`typescript/test/fixtures/inspect-table.json`
(`typescript/test/fixtures/gen-inspect-table.mjs` regenerates it).
`tests/test_js_inspect.py` holds this module to that file row by row. Four
of the rows would have been guessed wrong:

    5.0        -> "5"          (JavaScript has one number type; Rust's
                                Debug prints `2.0` for 2.0 -- A12's
                                opposite, and deliberate)
    1e21       -> "1e+21"      (`1e-7` keeps its sign and drops the pad;
                                `0.000001` is written out in full)
    -0         -> "-0"         (`String(-0)` is "0"; inspect is not String)
    "a\vb"     -> "'a\\x0Bb'"  (node names \n \t \r \b \f and NOTHING else;
                                every other control character, DEL and the
                                C1 block are \xHH in UPPERCASE hex, while
                                U+2028, U+00A0 and the rest are printable
                                to node and are not escaped at all)

THE TWO DIRECTIONS ARE INVERSES ON THE LITERAL DOMAIN
-----------------------------------------------------
Design amendment A11, applied to the second dialect: `read_inspect` parses
exactly what `inspect_text` can spell, so `resolve(dbg(inspect_text(L))) ==
L` for every literal `L` a command accepts. The domain is integers, floats
in every spelling `Number::toString` produces, `true`/`false`, `null`, and
quoted strings up to the recorder's 100-character string cap.

TWO THINGS NEITHER DIRECTION DOES
---------------------------------
Guess, and compare a prefix. `read_inspect` hands back the text itself
whenever the text spells no literal (an object, a function, a `Map`,
a `Date`), because the text is what the trace holds; `inspect_text` returns
None for a target that has no JavaScript spelling, and a capture then
matches nothing rather than matching approximately.

A string past inspect's own `maxStringLength` is the prefix case, and it is
the one place this dialect cannot read truncation off the capture's `trunc`
flag: inspect cut the STRING long before the 200-byte wire cap looked at
the rendering, so `trunc` is false and the only evidence is the
`... N more characters` tail inspect appends outside the closing quote.
Reading that tail as TRUNCATED, and refusing to spell one (plan P7), is
what keeps a prefix from being compared as a value.
"""
import math
import re
from decimal import Decimal

from sensorium.query.expr import TRUNCATED, UNDEFINED, _DbgText

#: Inspect's own string cap, from the recorder's options (`src/dbg.mjs`).
#: A longer string is cut by inspect before the wire cap is applied.
MAX_STRING = 100

# The three floats JavaScript spells as words rather than digits, and the
# one zero that carries a sign into its rendering.
_WORD_FLOATS = {"NaN": float("nan"), "Infinity": math.inf,
                "-Infinity": -math.inf}
# A BigInt, an integer, and a float -- a decimal POINT, an EXPONENT, or
# both. The BigInt is tried first (its `n` would otherwise be text), then
# the integer, so `5` is an int and never a float.
_BIGINT = re.compile(r"-?\d+n")
_INT = re.compile(r"-?\d+")
_FLOAT = re.compile(r"-?\d+(\.\d+)?[eE][-+]?\d+|-?\d+\.\d+")
# What inspect appends OUTSIDE the closing quote when it cut the string.
_MORE = re.compile(r"\.\.\. \d+ more characters?\Z")
#: The three quotes inspect chooses between, in the order it chooses them.
QUOTES = "'\"`"

# Read wider than written, on purpose. `\v` and `\0` never appear in a text
# this recorder wrote (node spells them `\x0B` and `\x00`), and they are
# read anyway: undoing an escape the writer did not have to make is
# harmless, refusing one is not -- the rule `rust_debug` states for `\'`.
_UNESCAPE = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f",
             "v": "\v", "0": "\0", "\\": "\\", "'": "'", '"': '"', "`": "`"}
# The five node NAMES. Everything else unprintable is `\xHH`; see `_escape`.
_ESCAPE = {"\\": "\\\\", "\n": "\\n", "\t": "\\t", "\r": "\\r",
           "\b": "\\b", "\f": "\\f"}
_HEX = "0123456789abcdefABCDEF"
#: Sentinel: the text is a quoted string whose rendering inspect cut.
_CLIPPED = object()


def js_number(x) -> str:
    """How JavaScript spells this number: ECMAScript's `Number::toString`.

    Ported rather than approximated, because `repr` disagrees with it in
    four places a reader would meet on the first run: `2.0` (JavaScript has
    one number type and prints `2`), `1e+20` (JavaScript writes the digits
    out to 1e21), `1e-05` (no pad, and written out down to 1e-6) and `-0.0`.
    """
    if x != x:
        return "NaN"
    if x == math.inf:
        return "Infinity"
    if x == -math.inf:
        return "-Infinity"
    if x == 0:
        # `-0` is a rendering, not a value: `String(-0)` is "0" and
        # `util.inspect(-0)` is `-0`, and what a capture holds is the
        # inspect text.
        return "-0" if math.copysign(1.0, x) < 0 else "0"
    sign = "-" if x < 0 else ""
    m = abs(x)
    if (isinstance(m, int) or m.is_integer()) and m < 1e21:
        return sign + str(int(m))
    # The shortest digits that read back as this number, and where the point
    # goes among them -- the spec's `n` (the point's position) and `k` (how
    # many digits there are). `repr` is Python's shortest round-trip, which
    # is JavaScript's too.
    t = Decimal(repr(m)).as_tuple()
    digits = "".join(str(d) for d in t.digits)
    k = len(digits)
    n = t.exponent + k
    if k <= n <= 21:
        # ECMAScript's first placement, and unreachable here: every value it
        # answers for is an integer of at most 21 digits, and the shortcut
        # above answered it. Kept so the four steps read as the spec writes
        # them -- and so that removing the shortcut cannot silently change
        # an answer.
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * -n + digits
    else:
        e = n - 1
        body = (digits[0] + ("." + digits[1:] if k > 1 else "")
                + "e" + ("+" if e >= 0 else "-") + str(abs(e)))
    return sign + body


def _escape(ch: str, quote: str) -> str:
    """One character as inspect writes it inside `quote`.

    NOT `str.isprintable()`, which is what the Rust dialect uses: node
    escapes the C0 controls, DEL and the C1 block and nothing else, so
    U+2028, U+00A0 and U+200B -- all unprintable to Python -- are written
    literally. Measured; a `\\u2028` here would spell a text this recorder
    never writes.
    """
    if ch == quote:
        return "\\" + ch
    esc = _ESCAPE.get(ch)
    if esc is not None:
        return esc
    o = ord(ch)
    if o < 0x20 or 0x7F <= o <= 0x9F:
        return f"\\x{o:02X}"
    return ch


def quote_js(s: str) -> str:
    """A string as inspect quotes it: single, else double where the text
    holds a single quote, else backticks where it holds both -- and single
    with `\\'` escaped where it holds all three."""
    if "'" not in s:
        quote = "'"
    elif '"' not in s:
        quote = '"'
    elif "`" not in s:
        quote = "`"
    else:
        quote = "'"
    return quote + "".join(_escape(ch, quote) for ch in s) + quote


def inspect_text(target) -> str | None:
    """How `util.inspect` would spell this literal, or None if it would not.

    None is the honest answer for anything with no JavaScript spelling (an
    `ObjTarget`, an over-long string): a capture then matches it nowhere,
    rather than matching something adjacent.
    """
    if target is None:
        return "null"
    if isinstance(target, bool):             # before int: a bool IS an int
        return "true" if target else "false"
    if isinstance(target, int):
        return str(target)
    if isinstance(target, float):
        return js_number(target)
    if isinstance(target, str):
        if len(target) > MAX_STRING:
            # What the recorder wrote for such a string is a PREFIX with a
            # tail, and a prefix equals nothing (plan P7). Spelling the tail
            # here would report a sighting of characters never recorded.
            return None
        return quote_js(target)
    return None


def _body(text: str):
    """What is inside inspect's quotes: the body, `_CLIPPED` where inspect
    cut the string, or None where this text is not a quoted string.

    The closing quote is what tells a cut string from a string whose
    CONTENT ends `... 50 more characters`: inspect appends its tail after
    the quote, so the second one ends with a quote and the first does not.
    """
    m = _MORE.search(text)
    head = text[:m.start()] if m else text
    if not (len(head) >= 2 and head[0] == head[-1] and head[0] in QUOTES):
        return None
    return _CLIPPED if m else head[1:-1]


def read_inspect(text: str):
    """The value an inspect text spells: int, float, bool, None, the
    UNDEFINED marker, str, TRUNCATED, or the text itself.

    The caller has already dealt with the WIRE truncation -- a rendering
    clipped at 200 bytes is not a rendering. Inspect's own string cut is
    this function's to notice, because nothing else can see it.
    """
    if text == "null":
        return None
    if text == "undefined":
        # JavaScript's second absence, and not Python's: a name bound to
        # `undefined` is bound, which `x == null` must not answer yes for.
        return UNDEFINED
    if text in ("true", "false"):
        return text == "true"
    if text in _WORD_FLOATS:
        return _WORD_FLOATS[text]
    if text == "-0":
        # Before the integer rule, which would read it as the int 0 and
        # lose the sign the rendering carries.
        return -0.0
    if _BIGINT.fullmatch(text):
        # A BigInt is an arbitrary-precision integer, and Python's int is
        # the same thing: `x == 123` answers at a site that holds `123n`.
        return int(text[:-1])
    if _INT.fullmatch(text):
        return int(text)
    if _FLOAT.fullmatch(text):
        return float(text)
    body = _body(text)
    if body is _CLIPPED:
        return TRUNCATED
    if body is not None:
        return unescape_inspect(body)
    return _DbgText(text)


def unescape_inspect(inner: str) -> str:
    r"""The characters an inspect string's body stands for.

    Hand-written rather than `codecs.decode(.., "unicode_escape")`, which
    decodes latin-1 and so turns every non-ASCII character node printed
    literally into mojibake -- `'café'` would come back as `cafÃ©` and
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
        if nxt == "x":
            digits = inner[i + 2:i + 4]
            if len(digits) == 2 and all(c in _HEX for c in digits):
                out.append(chr(int(digits, 16)))
                i += 4
                continue
        elif nxt == "u" and inner[i + 2:i + 3] == "{":
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
        elif nxt == "u":
            digits = inner[i + 2:i + 6]
            if len(digits) == 4 and all(c in _HEX for c in digits):
                out.append(chr(int(digits, 16)))
                i += 6
                continue
        out.append(ch)
        i += 1
    return "".join(out)
