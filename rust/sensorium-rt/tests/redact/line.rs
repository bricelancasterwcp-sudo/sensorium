//! Wire v4: a LINE delta whose name fires (task 5). Split out of
//! `tests/redact.rs` (the crate's 800-line ceiling); `Spec`, `TempDir`,
//! `Key`, `KEY_VAR`, `HEX_KEY` and `MSG_CAP` all reach this module through
//! `super::*`, the same way `tests/redact.rs` itself reaches them.

use super::*;

/// One LINE delta, parsed from the grammar directly: name, tag, truncated,
/// text. Tag 4 (redacted, wire v4) carries a text block exactly as tag 1
/// does.
type LineDelta = (String, u8, bool, Option<String>);

/// `(flags, deltas)` of a LINE payload -- the way every wire test in this
/// crate reads its own payload, never re-derived from `src/line.rs`.
fn parse_line_deltas(payload: &[u8]) -> (u8, Vec<LineDelta>) {
    const TAG_DEBUG: u8 = 1;
    const TAG_REDACTED: u8 = 4;
    assert!(
        payload.len() >= 3,
        "a LINE payload is at least flags and n, got {payload:?}"
    );
    let flags = payload[0];
    let n = u16::from_le_bytes([payload[1], payload[2]]);
    let mut at = 3;
    let mut out = Vec::new();
    for _ in 0..n {
        let name_len = u16::from_le_bytes([payload[at], payload[at + 1]]) as usize;
        at += 2;
        let name =
            String::from_utf8(payload[at..at + name_len].to_vec()).expect("delta name is UTF-8");
        at += name_len;
        let (tag, truncated) = (payload[at], payload[at + 1] != 0);
        at += 2;
        let text = if tag == TAG_DEBUG || tag == TAG_REDACTED {
            let text_len = u16::from_le_bytes([payload[at], payload[at + 1]]) as usize;
            at += 2;
            let text = String::from_utf8(payload[at..at + text_len].to_vec())
                .expect("delta text is UTF-8");
            at += text_len;
            Some(text)
        } else {
            None
        };
        out.push((name, tag, truncated, text));
    }
    assert_eq!(
        at,
        payload.len(),
        "the payload's length and its n blocks must agree exactly"
    );
    (flags, out)
}

/// The one LINE row a `line-redact*` scenario wrote, on the main thread.
fn one_line_row(dir: &TempDir) -> Vec<u8> {
    const KIND_LINE: u8 = 6;
    let mut rows = dir.spool(1).of_kind(KIND_LINE);
    assert_eq!(rows.len(), 1, "one line() call, one LINE row: {rows:?}");
    rows.pop().unwrap().payload
}

fn find_delta<'a>(deltas: &'a [LineDelta], name: &str) -> &'a LineDelta {
    deltas
        .iter()
        .find(|(n, ..)| n == name)
        .unwrap_or_else(|| panic!("no {name:?} delta in {deltas:?}"))
}

#[test]
fn a_line_delta_whose_name_fires_is_written_redacted_with_its_digest() {
    let dir = TempDir::reserved("redact-line-keyed");
    Spec::new("line-redact")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .run();
    let (flags, deltas) = parse_line_deltas(&one_line_row(&dir));
    assert_eq!(flags, 0);

    let key = Key::from_hex(Some(HEX_KEY));
    let want_digest = key.digest("\"abc\"").expect("a keyed store digests");

    let token = find_delta(&deltas, "token");
    assert_eq!(token.1, 4, "a name that fires is tag 4");
    assert!(!token.2, "truncated is 0 on tag 4 (B1)");
    assert_eq!(token.3.as_deref(), Some(want_digest.as_str()));

    let plain = find_delta(&deltas, "plain");
    assert_eq!(plain.1, 1, "a name that does not fire is untouched, tag 1");
    assert_eq!(plain.3.as_deref(), Some("1"));

    let secret = find_delta(&deltas, "secret");
    assert_eq!(
        secret.1, 2,
        "an unread delta stays tag 2 even though its name fires (B24)"
    );
    assert_eq!(secret.3, None);
}

#[test]
fn an_unkeyed_line_delta_that_fires_is_tag_four_with_an_empty_text_block() {
    let dir = TempDir::reserved("redact-line-unkeyed");
    Spec::new("line-redact").spool(dir.path()).run();
    let (_, deltas) = parse_line_deltas(&one_line_row(&dir));
    let token = find_delta(&deltas, "token");
    assert_eq!(token.1, 4);
    assert!(!token.2);
    assert_eq!(
        token.3.as_deref(),
        Some(""),
        "unkeyed: the digest block is present and empty, text_len 0"
    );
}

#[test]
fn the_off_knob_leaves_a_line_delta_plaintext() {
    let dir = TempDir::reserved("redact-line-off");
    Spec::new("line-redact")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .env("SENSORIUM_NO_REDACT", "1")
        .run();
    let (_, deltas) = parse_line_deltas(&one_line_row(&dir));
    let token = find_delta(&deltas, "token");
    assert_eq!(token.1, 1, "the rule is off: plaintext, tag 1 (B26)");
    assert_eq!(token.3.as_deref(), Some("\"abc\""));
}

/// B24 on the CAPPED text: the digest is taken over the first [`MSG_CAP`]
/// bytes of the 300-byte value the probe actually read, computed here
/// independently of `cap_utf8` -- which is `pub(crate)` and unreachable from
/// this integration crate -- and, being pure ASCII, cut on a char boundary by
/// construction. A mutant that digested the uncapped 300 bytes fails this.
#[test]
fn a_line_deltas_digest_is_taken_over_the_capped_text_not_the_full_one() {
    let dir = TempDir::reserved("redact-line-long");
    Spec::new("line-redact-long")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .run();
    let (_, deltas) = parse_line_deltas(&one_line_row(&dir));
    assert_eq!(deltas.len(), 1);
    let (name, tag, truncated, text) = &deltas[0];
    assert_eq!(name, "token");
    assert_eq!(*tag, 4);
    assert!(!truncated);

    let full = "x".repeat(300);
    let capped = &full[..MSG_CAP];
    let key = Key::from_hex(Some(HEX_KEY));
    let want = key.digest(capped).expect("a keyed store digests");
    assert_eq!(text.as_deref(), Some(want.as_str()));
    assert_ne!(
        text.as_deref(),
        key.digest(&full).as_deref(),
        "meaningless if the capped and uncapped digests happen to agree"
    );
}
