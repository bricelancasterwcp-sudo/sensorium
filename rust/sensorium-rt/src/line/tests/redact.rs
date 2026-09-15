//! Wire v4: a `write_line_payload` delta whose name fires rule v1 (task 5,
//! design 2026-09-14). Split out of `tests.rs` (the crate's 800-line ceiling):
//! everything this module needs from `line.rs` and from `tests.rs`'s own
//! helpers (`debug`, `unread`, `parse`, `unkeyed`, `rule_on`, `HEX_KEY`) is
//! reachable through `super::*`, the same way `tests.rs` reaches `line.rs`'s.

use super::*;

/// This test's twin of `two_deltas_encode_to_the_bytes_the_wire_format_names`
/// for the fifth tag: `token` fires rule v1 and is written REDACTED, with its
/// digest in the text block where the value would have gone; `plain` does not
/// fire and is untouched, still tag 1. Hand-encoded byte for byte, so a
/// mutant that wrote tag 3 (unbound) instead of 4, or that dropped the text
/// block, fails here directly.
#[test]
fn a_delta_whose_name_fires_encodes_to_tag_four_and_its_digest() {
    let key = Key::from_hex(Some(HEX_KEY));
    let knobs = rule_on();
    let want_digest = key.digest("\"abc\"").expect("a keyed store digests");
    assert_eq!(want_digest.len(), 16, "a digest is 16 hex characters");

    let deltas = [("token", debug("\"abc\"")), ("plain", debug("1"))];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &deltas, &[], &key, &knobs);
    assert!(!dropped);

    let mut want: Vec<u8> = vec![
        0x00, 0x02, 0x00, // flags 0, n = 2
        0x05, 0x00, b't', b'o', b'k', b'e', b'n', // name_len 5, "token"
        0x04, 0x00, // tag 4 (REDACTED BY NAME), truncated 0
    ];
    want.extend_from_slice(&(want_digest.len() as u16).to_le_bytes());
    want.extend_from_slice(want_digest.as_bytes());
    want.extend_from_slice(&[
        0x05, 0x00, b'p', b'l', b'a', b'i', b'n', // name_len 5, "plain"
        0x01, 0x00, // tag 1 (debug text), truncated 0
        0x01, 0x00, b'1', // text_len 1, "1"
    ]);
    assert_eq!(&buf[..len as usize], &want[..]);
}

/// B1: `truncated` is 0 on tag 4 whatever the ORIGINAL text's length was --
/// the digest never reveals whether the value it stands for was cut, so the
/// byte carries nothing to reveal it with.
#[test]
fn a_redacted_deltas_truncated_byte_is_always_zero() {
    let key = Key::from_hex(Some(HEX_KEY));
    let deltas = [(
        "token",
        Capture {
            text: Some("\"abc\"".to_owned()),
            truncated: true,
        },
    )];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, _) = write_line_payload(&mut buf, &deltas, &[], &key, &rule_on());
    let (_, parsed) = parse(&buf[..len as usize]);
    assert_eq!(parsed[0].tag, 4);
    assert_eq!(
        parsed[0].truncated, 0,
        "a Capture that arrived already truncated is still tag 4, truncated 0"
    );
}

/// An unkeyed store still redacts a firing name -- the digest just has
/// nothing to be taken under, so the text block is present and empty
/// (`text_len 0`, never absent: a redacted delta is still tag 4).
#[test]
fn an_unkeyed_store_redacts_a_firing_name_with_an_empty_text_block() {
    let deltas = [("token", debug("\"abc\""))];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) =
        write_line_payload(&mut buf, &deltas, &[], &Key::from_hex(None), &rule_on());
    assert!(!dropped);
    let want: Vec<u8> = vec![
        0x00, 0x01, 0x00, // flags 0, n = 1
        0x05, 0x00, b't', b'o', b'k', b'e', b'n', // name_len 5, "token"
        0x04, 0x00, // tag 4, truncated 0
        0x00, 0x00, // text_len 0
    ];
    assert_eq!(&buf[..len as usize], &want[..]);
}

/// B26: `knobs.off` leaves a firing name exactly as it would have read with
/// no rule at all -- plaintext, tag 1, whatever key the store carries.
#[test]
fn the_off_knob_leaves_a_firing_name_plaintext_and_tag_one() {
    let off = Knobs::from_values(Some("1"), None, None);
    assert!(off.off);
    let deltas = [("token", debug("\"abc\""))];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) =
        write_line_payload(&mut buf, &deltas, &[], &Key::from_hex(Some(HEX_KEY)), &off);
    assert!(!dropped);
    let (_, parsed) = parse(&buf[..len as usize]);
    assert_eq!(parsed[0].tag, 1, "the rule is off: plaintext, never tag 4");
    assert_eq!(parsed[0].text.as_deref(), Some("\"abc\""));
}

/// B24: an UNREAD delta is untouched by rule v1 even when its name fires --
/// nothing was read, so nothing is withheld. Stays tag 2, same as it always
/// was.
#[test]
fn an_unread_delta_stays_tag_two_even_when_its_name_fires() {
    let deltas = [("token", unread())];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(
        &mut buf,
        &deltas,
        &[],
        &Key::from_hex(Some(HEX_KEY)),
        &rule_on(),
    );
    assert!(!dropped);
    let (_, parsed) = parse(&buf[..len as usize]);
    assert_eq!(
        parsed[0].tag, 2,
        "unread stays unread, whatever the name is"
    );
    assert_eq!(parsed[0].text, None);
}

/// B24 on the CAPPED text: a mutant that digested the 300-byte value before
/// capping it would produce a different 16 hex characters than one taken over
/// the first [`probe::CAP`] bytes -- this test tells the two apart.
/// `tests/redact.rs` holds the same claim end to end, off a real child spool;
/// this is the fast, in-process half.
#[test]
fn a_redacted_digest_is_taken_over_the_capped_text_not_the_full_one() {
    let key = Key::from_hex(Some(HEX_KEY));
    let full = "x".repeat(300);
    let capped = &full[..crate::probe::CAP];
    let want = key.digest(capped).expect("a keyed store digests");
    assert_ne!(
        want,
        key.digest(&full).expect("a keyed store digests"),
        "the test is meaningless if capping the text does not change its digest"
    );

    let deltas = [("token", debug(&full))];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &deltas, &[], &key, &rule_on());
    assert!(!dropped);
    let (_, parsed) = parse(&buf[..len as usize]);
    assert_eq!(parsed[0].tag, 4);
    assert_eq!(parsed[0].text.as_deref(), Some(want.as_str()));
}
