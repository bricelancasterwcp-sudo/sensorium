//! Scenarios that write a LINE record by hand: no `--focus` transformer
//! splices one yet, so these call `sensorium_rt::line` directly, the way
//! `src/line/tests.rs`'s in-crate tests build a `Capture` rather than reading
//! one off a real value through the ladder. What they exist for is wire v4
//! (task 5, design 2026-09-14): `tests/redact.rs`'s child helper runs one of
//! these under whatever redaction knobs a test set in its environment and
//! reads the LINE row back.

use sensorium_rt::probe::Capture;

fn debug(text: &str) -> Capture {
    Capture {
        text: Some(text.to_owned()),
        truncated: false,
    }
}

fn unread() -> Capture {
    Capture {
        text: None,
        truncated: false,
    }
}

/// One LINE row, three deltas: `token` (a name that fires rule v1), `plain`
/// (one that does not) and `secret` (a name that fires, but was never read --
/// B24). One `enter` first, only to register the unit: `line` itself needs no
/// open frame (`src/line.rs`).
pub(crate) fn line_redact() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 220);
    ::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 221, || {
        [
            ("token", debug("\"abc\"")),
            ("plain", debug("1")),
            ("secret", unread()),
        ]
    });
}

/// One LINE row, one delta, on a name that fires: 300 bytes of captured text,
/// wider than the probe's own cap. What this proves is which text the digest
/// is taken over -- `tests/redact.rs` computes the CAPPED text independently
/// and checks the digest against that, not against the 300 bytes the probe
/// read.
pub(crate) fn line_redact_long() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 230);
    let text = "x".repeat(300);
    ::sensorium_rt::line(&crate::__SENSORIUM_UNIT, 231, || [("token", debug(&text))]);
}
