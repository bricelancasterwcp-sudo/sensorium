"""Rule v1's CONTENT half (§2.2): a fixed list of patterns over a value's
TEXT, whatever its name. Beside `redact.py`'s name rule, which decides
whether a whole value is worth redacting at all; this module decides which
SPANS inside a value's text look like a secret regardless of what it was
called.

WHAT THIS IS NOT
----------------
**Not a secret scanner.** The list is a floor: nineteen shapes, each with a
minimum length so a short benign string cannot fire. A secret that matches
none of them is stored as typed.

THE FIXTURE
-----------
`docs/trace-format/redaction-v1.json`'s `content` list holds every case, and
`sensorium-rt`'s converter (`redact_content.rs`, `regex` crate -- the
runtime stays dependency-free, §5.2) and the TypeScript recorder's suite
read the SAME file. The three implementations are the same nineteen
patterns, textually, save for the one place the three engines cannot agree
on a spelling: end-of-text in the PEM row's truncated form (`\\Z` here,
`\\z` in Rust, `$` under JavaScript's `s` flag) and inline case/dotall flags
(`(?i)`/`(?s)` here and in Rust; the `i`/`s` RegExp flags in JavaScript,
which has no inline spelling for either).

TWO OPERATIONS, ONE MODULE
---------------------------
§2.3: a name hit redacts the WHOLE value (`redact.py`); a content hit
replaces the matched SPAN and keeps everything around it
(`postgres://u:<redacted>@h/db`) -- a repr or a log line is not a value
with an identity, it is text that happened to contain one, and a partial
cannot honestly carry a digest of the whole. `hit` below means exactly
"the text changed": a pattern that matches a span already holding the
marker (an env value the name rule already redacted, then rendered
somewhere) is not a second hit, and `content` must say so, because the
converters (Task 6/7) count `values` from this flag.

This module is pure -- it imports nothing but `redact.REDACTED` -- and never
raises.
"""
import re

from sensorium.redact import REDACTED

#: (row name, compiled pattern, replaced group: 0 = whole match). Verbatim
#: from §2.2's table, in the order that table gives -- table order matters
#: exactly once, for `sk-ant` before `sk`: both match an Anthropic key, the
#: whole match is replaced either way so the two rows' `after` never differs,
#: and the order is only for which row NAME a test or a report attributes
#: the hit to.
PATTERNS: tuple[tuple[str, "re.Pattern[str]", int], ...] = (
    ("url-userinfo",
     re.compile(r"://[^/\s:@]{1,64}:([^@\s/]{1,256})@"), 1),
    # The PEM body, through the matching END line or to end of text when
    # truncated -- `\Z` is this engine's spelling of that end-of-text
    # alternative; Rust's `redact_content.rs` spells it `\z` and JavaScript's
    # spells it `$` under the `s` flag. `(?s)` is inline DOTALL: the body
    # spans real newlines.
    ("pem",
     re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----(.*?)"
                r"(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)"), 1),
    ("authorization-header",
     re.compile(r"(?i)\b(Bearer|Basic)\s+([A-Za-z0-9._~+/=-]{16,})"), 2),
    ("jwt",
     re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}"
                r"\.[A-Za-z0-9_-]{8,}"), 0),
    ("sk-ant", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), 0),
    ("sk", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), 0),
    ("stripe", re.compile(r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}"), 0),
    ("github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), 0),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), 0),
    ("gitlab", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"), 0),
    ("slack", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), 0),
    ("aws", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), 0),
    ("huggingface", re.compile(r"\bhf_[A-Za-z0-9]{20,}"), 0),
    ("npm", re.compile(r"\bnpm_[A-Za-z0-9]{20,}"), 0),
    ("pypi", re.compile(r"\bpypi-[A-Za-z0-9_-]{20,}"), 0),
    ("digitalocean", re.compile(r"\bdop_v1_[a-f0-9]{20,}"), 0),
    ("shopify", re.compile(r"\bshpat_[a-f0-9]{20,}"), 0),
    ("sendgrid",
     re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"), 0),
)

#: B18's pre-check (§12's mitigation, built in rather than waited for): the
#: literal prefix every pattern above starts with, as one alternation. A
#: string that matches none of these cannot match any of the nineteen
#: patterns either, so `content` skips the whole table rather than running
#: twenty regexes over every string a recorder ever touches.
_TRIGGER = re.compile("|".join(re.escape(p) for p in (
    "://", "-----BEGIN", "eyJ", "sk-", "sk_", "rk_", "gh", "github_pat_",
    "glpat-", "xox", "AKIA", "ASIA", "AIza", "hf_", "npm_", "pypi-",
    "dop_v1_", "shpat_", "SG.", "Bearer", "Basic", "bearer", "basic",
)))


def content(text: str) -> tuple[str, bool]:
    """`text` with every matched span replaced by `REDACTED`, and whether
    the text CHANGED -- never whether some pattern merely matched.

    That distinction is the whole of the contract: `url-userinfo` matches
    `postgres://u:<redacted>@h/db` (its group already reads as the marker),
    and replacing it with itself is not a hit. Comparing the WHOLE result to
    the input, once, at the end, is what makes that true without a special
    case for it -- the converters that count `values` from this flag rely on
    it (Task 6/7).

    Applied left to right, pattern by pattern in table order, over the
    CURRENT text -- so a later pattern sees an earlier pattern's markers,
    never the original secret twice.
    """
    if not text or not _TRIGGER.search(text):
        return text, False
    out = text
    for _, pattern, group in PATTERNS:
        out = pattern.sub(_replacer(group), out)
    return out, out != text


def _replacer(group: int):
    """One pattern's substitution function: the whole match for group 0, or
    the match with only `group`'s span swapped for `REDACTED` -- never the
    whole match when a narrower group was asked for (§2.3's span operation:
    everything around the secret is kept)."""
    if group == 0:
        return lambda m: REDACTED

    def _swap(m: "re.Match[str]") -> str:
        whole = m.group(0)
        start = m.start(group) - m.start(0)
        end = m.end(group) - m.start(0)
        return whole[:start] + REDACTED + whole[end:]

    return _swap
