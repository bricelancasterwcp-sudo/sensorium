//! The one JSON string escaper, for the two modules that write the header by
//! hand.
//!
//! It lives in its own module rather than in `spool.rs` because `redact.rs`
//! writes the header's `env_redaction` and `redaction` siblings and needs the
//! same escaping: a second escaper beside the first is how two writers of one
//! file end up disagreeing about a backslash. Nothing here knows what a
//! sensorium header is -- it escapes a string, and the two callers decide what
//! the strings mean.
//!
//! Hand-written because this crate takes no dependencies (plan decision D1);
//! `sensorium-rt`'s test suite reads the header back with a parser that shares
//! no code with it.

/// `s` as a JSON string, quotes included, appended to `out`.
///
/// The five named escapes JSON requires, then `\u00XX` for the rest of the C0
/// range. Everything else -- every non-ASCII character included -- goes out as
/// itself: the header is written as UTF-8 and read as UTF-8.
pub(crate) fn push_json_str(out: &mut String, s: &str) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let cp = c as u32;
                out.push_str("\\u00");
                out.push(char::from_digit(cp >> 4, 16).unwrap());
                out.push(char::from_digit(cp & 0xf, 16).unwrap());
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_strings_escape_what_json_requires() {
        let mut out = String::new();
        push_json_str(&mut out, "a\"b\\c\nd\te\u{1}f\u{e9}");
        assert_eq!(out, "\"a\\\"b\\\\c\\nd\\te\\u0001f\u{e9}\"");
    }
}
