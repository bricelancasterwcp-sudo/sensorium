//! Rule v1's CONTENT half (§2.2), in the CONVERTER and never in
//! `sensorium-rt`: the runtime stays dependency-free (§5.2), so the
//! nineteen patterns live here, applied once, at conversion time, to a
//! value's TEXT whatever its name -- beside `redaction.rs`'s NAME half,
//! which decides whether a whole value is worth redacting at all.
//!
//! WHAT THIS IS NOT
//! ----------------
//! **Not a secret scanner.** The list is a floor: nineteen shapes, each
//! with a minimum length so a short benign string cannot fire. A secret
//! that matches none of them is stored as typed.
//!
//! THE FIXTURE
//! -----------
//! `docs/trace-format/redaction-v1.json`'s `content` list holds every
//! case, and `src/sensorium/redact_content.py`'s suite and
//! `typescript/test/redact.test.mjs` read the SAME file. The three
//! implementations are the same nineteen patterns, textually, save for the
//! one place the three engines cannot agree on a spelling: end-of-text in
//! the PEM row's truncated form (`\z` here, `\Z` in Python, `$` under
//! JavaScript's `s` flag) and inline case/dotall flags (`(?i)`/`(?s)` here
//! and in Python; the `i`/`s` RegExp flags in JavaScript, which has no
//! inline spelling for either).
//!
//! TWO OPERATIONS, ONE MODULE
//! ---------------------------
//! §2.3: a name hit redacts the WHOLE value; a content hit replaces the
//! matched SPAN and keeps everything around it
//! (`postgres://u:<redacted>@h/db`) -- a repr or a log line is not a value
//! with an identity, it is text that happened to contain one. `hit` below
//! means exactly "the text changed": a pattern that matches a span already
//! holding the marker (an env value the name rule already redacted, then
//! rendered somewhere) is not a second hit, and `content` must say so,
//! because Task 6/7's converters count `values` from this flag.

use std::borrow::Cow;
use std::sync::OnceLock;

use regex::{Captures, Regex};
use sensorium_rt::redact::REDACTED;

/// One row of §2.2's table: its name (for a test or a report to attribute a
/// hit to), its compiled pattern, and which group a match replaces (`0` is
/// the whole match).
struct Pattern {
    name: &'static str,
    regex: Regex,
    group: usize,
}

/// Verbatim from §2.2's table, in the order that table gives -- table order
/// matters exactly once, for `sk-ant` before `sk`: both match an Anthropic
/// key, the whole match is replaced either way so the two rows' output
/// never differs, and the order is only for which row NAME a test or a
/// report attributes the hit to. Compiled once: nineteen `Regex::new` calls
/// are not cheap, and every recorded value in a store meets this list.
fn patterns() -> &'static [Pattern] {
    static PATTERNS: OnceLock<Vec<Pattern>> = OnceLock::new();
    PATTERNS.get_or_init(|| {
        let compile = |name: &'static str, source: &str, group: usize| Pattern {
            name,
            regex: Regex::new(source)
                .unwrap_or_else(|e| panic!("redact_content pattern {name:?}: {e}")),
            group,
        };
        vec![
            compile("url-userinfo", r"://[^/\s:@]{1,64}:([^@\s/]{1,256})@", 1),
            // The PEM body, through the matching END line or to end of text
            // when truncated -- `\z` is this engine's spelling of that
            // end-of-text alternative; the Python suite spells it `\Z` and
            // JavaScript's spells it `$` under the `s` flag. `(?s)` is
            // inline DOTALL: the body spans real newlines.
            compile(
                "pem",
                r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----(.*?)(?:-----END [A-Z ]*PRIVATE KEY-----|\z)",
                1,
            ),
            compile(
                "authorization-header",
                r"(?i)\b(Bearer|Basic)\s+([A-Za-z0-9._~+/=-]{16,})",
                2,
            ),
            compile(
                "jwt",
                r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
                0,
            ),
            compile("sk-ant", r"\bsk-ant-[A-Za-z0-9_-]{20,}", 0),
            compile("sk", r"\bsk-[A-Za-z0-9_-]{20,}", 0),
            compile("stripe", r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}", 0),
            compile("github", r"\bgh[pousr]_[A-Za-z0-9]{20,}", 0),
            compile("github-pat", r"\bgithub_pat_[A-Za-z0-9_]{20,}", 0),
            compile("gitlab", r"\bglpat-[A-Za-z0-9_-]{20,}", 0),
            compile("slack", r"\bxox[abprs]-[A-Za-z0-9-]{10,}", 0),
            compile("aws", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b", 0),
            compile("google", r"\bAIza[0-9A-Za-z_-]{35}\b", 0),
            compile("huggingface", r"\bhf_[A-Za-z0-9]{20,}", 0),
            compile("npm", r"\bnpm_[A-Za-z0-9]{20,}", 0),
            compile("pypi", r"\bpypi-[A-Za-z0-9_-]{20,}", 0),
            compile("digitalocean", r"\bdop_v1_[a-f0-9]{20,}", 0),
            compile("shopify", r"\bshpat_[a-f0-9]{20,}", 0),
            compile(
                "sendgrid",
                r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
                0,
            ),
        ]
    })
}

/// B18's pre-check (§12's mitigation, built in rather than waited for): the
/// literal prefix every pattern above starts with, as one alternation. A
/// string that matches none of these cannot match any of the nineteen
/// patterns either, so [`content`] skips the whole table rather than
/// running twenty regexes over every string a conversion ever touches.
fn trigger() -> &'static Regex {
    static TRIGGER: OnceLock<Regex> = OnceLock::new();
    TRIGGER.get_or_init(|| {
        let literals = [
            "://",
            "-----BEGIN",
            "eyJ",
            "sk-",
            "sk_",
            "rk_",
            "gh",
            "github_pat_",
            "glpat-",
            "xox",
            "AKIA",
            "ASIA",
            "AIza",
            "hf_",
            "npm_",
            "pypi-",
            "dop_v1_",
            "shpat_",
            "SG.",
            "Bearer",
            "Basic",
            "bearer",
            "basic",
        ];
        let source: String = literals
            .iter()
            .map(|l| regex::escape(l))
            .collect::<Vec<_>>()
            .join("|");
        Regex::new(&source).expect("_TRIGGER: an alternation of literal strings always compiles")
    })
}

/// `text` with every matched span replaced by [`REDACTED`], and whether the
/// text CHANGED -- never whether some pattern merely matched.
///
/// That distinction is the whole of the contract: `url-userinfo` matches
/// `postgres://u:<redacted>@h/db` (its group already reads as the marker),
/// and replacing it with itself is not a hit. Comparing the WHOLE result to
/// the input, once, at the end, is what makes that true without a special
/// case for it -- Task 6/7's converters count `values` from this flag.
///
/// Applied left to right, pattern by pattern in table order, over the
/// CURRENT text -- so a later pattern sees an earlier pattern's markers,
/// never the original secret twice.
#[must_use]
pub fn content(text: &str) -> (Cow<'_, str>, bool) {
    if text.is_empty() || !trigger().is_match(text) {
        return (Cow::Borrowed(text), false);
    }
    let mut out = text.to_owned();
    for pattern in patterns() {
        out = apply(pattern, &out);
    }
    let hit = out != text;
    (Cow::Owned(out), hit)
}

/// One pattern's substitution over `text`: the whole match for group `0`,
/// or the match with only its group's span swapped for [`REDACTED`] --
/// never the whole match when a narrower group was asked for (§2.3's span
/// operation: everything around the secret is kept).
fn apply(pattern: &Pattern, text: &str) -> String {
    if pattern.group == 0 {
        return pattern.regex.replace_all(text, REDACTED).into_owned();
    }
    pattern
        .regex
        .replace_all(text, |caps: &Captures| {
            let whole = caps.get(0).unwrap_or_else(|| {
                panic!(
                    "redact_content pattern {:?}: group 0 always matches",
                    pattern.name
                )
            });
            let group = caps.get(pattern.group).unwrap_or_else(|| {
                panic!(
                    "redact_content pattern {:?}: group {} did not participate",
                    pattern.name, pattern.group
                )
            });
            let start = group.start() - whole.start();
            let end = group.end() - whole.start();
            let whole_str = whole.as_str();
            format!("{}{REDACTED}{}", &whole_str[..start], &whole_str[end..])
        })
        .into_owned()
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;
    use std::path::Path;

    use serde_json::Value;

    use super::{content, patterns, trigger, REDACTED};

    /// The shared fixture, read the way the Python and TypeScript suites
    /// read it: off disk, from the repository root, never imported from a
    /// build artefact.
    fn fixture() -> Vec<Value> {
        let path = Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../docs/trace-format/redaction-v1.json"
        ));
        let text =
            std::fs::read_to_string(path).unwrap_or_else(|e| panic!("{e}: {}", path.display()));
        let root: Value = serde_json::from_str(&text).unwrap_or_else(|e| panic!("{e}"));
        root["content"].as_array().cloned().unwrap_or_default()
    }

    fn text_of(case: &Value) -> &str {
        case["text"]
            .as_str()
            .unwrap_or_else(|| panic!("{case}: no text"))
    }

    fn after_of(case: &Value) -> &str {
        case["after"]
            .as_str()
            .unwrap_or_else(|| panic!("{case}: no after"))
    }

    fn pattern_of(case: &Value) -> &str {
        case["pattern"]
            .as_str()
            .unwrap_or_else(|| panic!("{case}: no pattern"))
    }

    #[test]
    fn every_content_case_in_the_shared_fixture() {
        let cases = fixture();
        assert!(!cases.is_empty(), "the fixture has content cases");
        for case in &cases {
            let (text, after) = (text_of(case), after_of(case));
            let (out, hit) = content(text);
            assert_eq!(out, after, "pattern {:?}", pattern_of(case));
            assert_eq!(hit, after != text, "pattern {:?}", pattern_of(case));
        }
    }

    /// A pattern with no positive is a pattern nothing here proves fires; a
    /// pattern with no negative is a pattern nothing here proves has a
    /// floor.
    #[test]
    fn every_pattern_has_a_positive_and_a_negative_row() {
        let cases = fixture();
        let mut by_pattern: HashMap<&str, Vec<bool>> = HashMap::new();
        for case in &cases {
            by_pattern
                .entry(pattern_of(case))
                .or_default()
                .push(after_of(case) != text_of(case));
        }
        for pattern in patterns() {
            let hits = by_pattern.get(pattern.name).cloned().unwrap_or_default();
            assert!(
                hits.iter().any(|&h| h),
                "{:?} has no positive row",
                pattern.name
            );
            assert!(
                hits.iter().any(|&h| !h),
                "{:?} has no negative row",
                pattern.name
            );
        }
    }

    /// B18's pre-check: a positive case the trigger misses is a secret the
    /// content rule would silently never look at.
    #[test]
    fn every_positive_passes_the_trigger() {
        for case in &fixture() {
            let (text, after) = (text_of(case), after_of(case));
            if after != text {
                assert!(
                    trigger().is_match(text),
                    "{:?}'s positive does not pass the trigger: {text:?}",
                    pattern_of(case)
                );
            }
        }
    }

    /// A text that has been through the rule once holds no trigger the rule
    /// would act on again -- the marker itself contains none of §2.2's
    /// shapes.
    #[test]
    fn the_rule_is_a_fixed_point() {
        for case in &fixture() {
            let after = after_of(case);
            assert_eq!(content(after).0, after, "pattern {:?}", pattern_of(case));
        }
    }

    #[test]
    fn a_marker_is_never_re_redacted() {
        let (out, hit) = content(REDACTED);
        assert_eq!(out, REDACTED);
        assert!(!hit);
    }

    /// §2.3's boundary case: `hit` means the TEXT CHANGED, not that a
    /// pattern matched. `url-userinfo` matches
    /// `postgres://u:<redacted>@h/db` (its group is already the marker),
    /// and the converter (Task 6/7) counts on this staying a no-op.
    #[test]
    fn a_url_userinfo_marker_in_context_is_a_no_op() {
        let text = format!("postgres://u:{REDACTED}@h/db");
        let (out, hit) = content(&text);
        assert_eq!(out, text);
        assert!(!hit);
    }

    #[test]
    fn empty_string_is_a_no_op() {
        let (out, hit) = content("");
        assert_eq!(out, "");
        assert!(!hit);
    }
}
