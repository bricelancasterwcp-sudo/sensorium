//! The `line` module's tests. Split out of `line.rs` (fix round 2): the module
//! file passed 750 lines and the crate's limit is 800.
//!
//! `#[cfg(test)]`, so the driver's bare `rustc` line -- which compiles the
//! EMBEDDED copy of this runtime with no `--test` and no cfg -- never resolves
//! this module and never needs the file (`cargo-sensorium/src/rt_src.rs`
//! embeds `line.rs` alone, and its own test derives that name from the `mod`
//! declaration in `lib.rs`).

use super::*;

use std::cell::Cell;
use std::fmt::{self, Debug};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::{Mutex, MutexGuard, OnceLock};

use crate::probe::Capture;
use crate::spool::{HEADER_FIXED, KIND_LINE, RECORD_FIXED};
use crate::{Unit, STATE, STATE_CALL, STATE_OFF, STATE_UNINIT};

// -----------------------------------------------------------------------
// (z) the ladder, applied to one borrowed value
// -----------------------------------------------------------------------

struct NoDebug;

/// What a `Debug` impl can see about the runtime while it is being read.
struct AsksIfInRuntime;

impl Debug for AsksIfInRuntime {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", crate::thread::in_runtime())
    }
}

#[test]
fn probe_cap_reads_a_value_that_has_a_debug_impl() {
    let c = crate::probe_cap!(&5u8);
    assert_eq!(c.text.as_deref(), Some("5"));
    assert!(!c.truncated);
}

#[test]
fn probe_cap_reads_unread_from_a_value_with_no_debug_impl() {
    let c = crate::probe_cap!(&NoDebug);
    assert_eq!(c.text, None);
    assert!(!c.truncated);
}

/// Why `probe_cap` is a macro and not the `fn probe_cap<T>(v: &T)` the task
/// asked for: the ladder specialises on the CALL SITE's type. Inside a
/// generic fn there is no `T: Debug` bound, so the specialised impl is not
/// applicable and the fallback answers for every type -- including `u8`.
// `(&&Probe(v))` is `probe_cap!`'s call site, character for character.
// Clippy calls the second `&` needless HERE -- because in a generic fn the
// specialised impl can never win -- and taking its advice would delete the
// measurement.
#[allow(clippy::needless_borrow)]
fn ladder_inside_a_generic_fn<T>(v: &T) -> Capture {
    // `DebugCap` is unused HERE, and that is the finding: the specialised
    // impl is not applicable inside a generic fn, so importing it changes
    // nothing. Dropping the import would hide what this test measures.
    #[allow(unused_imports)]
    use crate::probe::{DebugCap as _, NoDebugCap as _};
    (&&crate::probe::Probe(v)).debug_cap()
}

#[test]
fn a_generic_fn_cannot_carry_the_ladder_which_is_why_probe_cap_is_a_macro() {
    assert_eq!(
        ladder_inside_a_generic_fn(&5u8).text,
        None,
        "a plain generic fn reads every value unread; the macro is not a style choice"
    );
    assert_eq!(crate::probe_cap!(&5u8).text.as_deref(), Some("5"));
}

/// The capture runs INSIDE the runtime scope, so instrumented code a
/// workspace `Debug` impl calls records nothing (spec §3.6, HONESTY §9).
/// The impl still runs.
#[test]
fn probe_cap_reads_the_value_inside_the_runtime_scope() {
    assert!(!crate::thread::in_runtime(), "the test thread starts clean");
    let c = crate::probe_cap!(&AsksIfInRuntime);
    assert_eq!(c.text.as_deref(), Some("true"));
    assert!(
        !crate::thread::in_runtime(),
        "and the scope is released again"
    );
}

// -----------------------------------------------------------------------
// (a)-(c) the payload
// -----------------------------------------------------------------------

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

/// One delta as the payload carries it: name, tag, truncated, text.
#[derive(Debug, PartialEq, Eq)]
struct Delta {
    name: String,
    tag: u8,
    truncated: u8,
    text: Option<String>,
}

/// Read the payload back exactly as the grammar spells it, and PANIC on a
/// short read: a block that runs off the end is the partial write the
/// dropping rule exists to prevent.
fn parse(payload: &[u8]) -> (u8, Vec<Delta>) {
    let flags = payload[0];
    let n = u16::from_le_bytes([payload[1], payload[2]]);
    let mut at = 3;
    let mut deltas = Vec::new();
    for i in 0..n {
        let name_len = u16::from_le_bytes([payload[at], payload[at + 1]]) as usize;
        at += 2;
        let name = std::str::from_utf8(&payload[at..at + name_len])
            .unwrap_or_else(|e| panic!("delta {i} name is not UTF-8: {e}"))
            .to_owned();
        at += name_len;
        let (tag, truncated) = (payload[at], payload[at + 1]);
        at += 2;
        let text = if tag == 1 {
            let text_len = u16::from_le_bytes([payload[at], payload[at + 1]]) as usize;
            at += 2;
            let text = std::str::from_utf8(&payload[at..at + text_len])
                .unwrap_or_else(|e| panic!("delta {i} text is not UTF-8: {e}"))
                .to_owned();
            at += text_len;
            Some(text)
        } else {
            None
        };
        deltas.push(Delta {
            name,
            tag,
            truncated,
            text,
        });
    }
    assert_eq!(
        at,
        payload.len(),
        "the payload's length and its `n` blocks must agree exactly"
    );
    (flags, deltas)
}

/// The bytes, by hand from the grammar. Anything that moves the shape of a
/// LINE payload has to move this vector too -- and then the converter.
#[test]
fn two_deltas_encode_to_the_bytes_the_wire_format_names() {
    let deltas = [("x", debug("5")), ("buf", unread())];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &deltas);
    assert!(!dropped);
    #[rustfmt::skip]
    let want: Vec<u8> = vec![
        0x00,                    // flags: nothing dropped
        0x02, 0x00,              // n = 2
        0x01, 0x00, b'x',        // name_len 1, "x"
        0x01, 0x00,              // tag 1 (debug text), truncated 0
        0x01, 0x00, b'5',        // text_len 1, "5"
        0x03, 0x00, b'b', b'u', b'f', // name_len 3, "buf"
        0x02, 0x00,              // tag 2 (unread), truncated 0
    ];
    assert_eq!(&buf[..len as usize], &want[..]);
    assert_eq!(len as usize, 18);
}

#[test]
fn a_statement_that_wrote_nothing_is_three_bytes_and_still_a_row() {
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &[]);
    assert_eq!((len, dropped), (3, false));
    assert_eq!(&buf[..3], &[0, 0, 0]);
}

#[test]
fn an_over_long_text_is_cut_at_the_cap_on_a_char_boundary_and_flagged() {
    // 300 bytes, and 'é' is two of them: a cut that did not step back would
    // not be UTF-8.
    let deltas = [("s", debug(&"é".repeat(150)))];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &deltas);
    assert!(!dropped, "one capped delta fits; nothing is dropped");
    let (flags, deltas) = parse(&buf[..len as usize]);
    assert_eq!(flags, 0);
    assert_eq!(deltas.len(), 1);
    assert_eq!(deltas[0].truncated, 1, "the writer that cut says it cut");
    assert_eq!(
        deltas[0].text.as_deref().map(str::len),
        Some(crate::probe::CAP)
    );
    assert_eq!(deltas[0].text.as_deref(), Some("é".repeat(100).as_str()));
}

/// The twin of `exit.rs`'s `an_empty_debug_rendering_is_a_read_value_not_an_unread_one`.
/// A `Debug` impl that renders nothing was READ and rendered nothing (tag 1,
/// empty text); a type with no `Debug` impl was not read at all (tag 2). A
/// reader that cannot tell them apart cannot tell "the value is `()`-ish" from
/// "sensorium could not see this value" -- so the writer must not fold the two.
/// Pinned in bytes, because `None | Some("") => TAG_UNREAD` passes every other
/// test in this file.
#[test]
fn an_empty_debug_rendering_is_a_read_value_not_an_unread_one() {
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &[("s", debug(""))]);
    assert!(!dropped);
    #[rustfmt::skip]
    let want: Vec<u8> = vec![
        0x00,               // flags
        0x01, 0x00,         // n = 1
        0x01, 0x00, b's',   // name_len 1, "s"
        0x01, 0x00,         // tag 1 (debug text, NOT 2), truncated 0
        0x00, 0x00,         // text_len 0
    ];
    assert_eq!(&buf[..len as usize], &want[..]);
    assert_eq!(len as usize, 3 + 2 + 1 + 2 + 2);
    let (_, deltas) = parse(&buf[..len as usize]);
    assert_eq!(deltas[0].tag, 1, "tag 1 with no text, never tag 2");
    assert_eq!(deltas[0].text.as_deref(), Some(""));
}

#[test]
fn a_capture_that_was_already_cut_stays_flagged_truncated() {
    let deltas = [(
        "s",
        Capture {
            text: Some("abc".to_owned()),
            truncated: true,
        },
    )];
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, _) = write_line_payload(&mut buf, &deltas);
    let (_, deltas) = parse(&buf[..len as usize]);
    assert_eq!(deltas[0].truncated, 1);
    assert_eq!(deltas[0].text.as_deref(), Some("abc"));
}

#[test]
fn deltas_that_do_not_fit_are_dropped_whole_and_the_flag_says_so() {
    let names: Vec<String> = (0..40).map(|i| format!("d{i:02}")).collect();
    let text = "x".repeat(190);
    let deltas: Vec<(&str, Capture)> = names.iter().map(|n| (n.as_str(), debug(&text))).collect();
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, dropped) = write_line_payload(&mut buf, &deltas);
    assert!(dropped, "forty 190-byte deltas do not fit one record");
    assert!(len as usize <= LINE_PAYLOAD_MAX);
    let (flags, written) = parse(&buf[..len as usize]);
    assert_eq!(flags & 1, 1, "bit0 is the dropped flag");
    assert!(
        !written.is_empty() && written.len() < 40,
        "some deltas were written and some were not, {} of 40",
        written.len()
    );
    for (i, delta) in written.iter().enumerate() {
        assert_eq!(delta.name, names[i], "deltas keep their order");
        assert_eq!(delta.tag, 1);
        assert_eq!(
            delta.text.as_deref(),
            Some(text.as_str()),
            "a written delta is whole: no block is cut short to make room"
        );
    }
}

/// (g) The boundary [`LINE_PAYLOAD_MAX`] was sized for (A5): eight fully
/// capped deltas WITH their names fit, and nothing is dropped. The exact
/// boundary at that shape -- an eight-character name and a 200-byte text,
/// 214 bytes a delta -- is nine; the tenth is dropped. Both sides pinned,
/// so a change to the constant has to come here and say what it did.
// The four assertions below are constant BY DESIGN: they hold the boundary
// arithmetic against `LINE_PAYLOAD_MAX` itself, so moving the constant has
// to move this test.
#[allow(clippy::assertions_on_constants)]
#[test]
fn eight_fully_capped_deltas_fit_and_the_boundary_is_nine() {
    const PER_DELTA: usize = 2 + 8 + 1 + 1 + 2 + 200;
    assert_eq!(
        PER_DELTA, 214,
        "u16 name_len, name, tag, truncated, u16 text_len, text"
    );
    assert_eq!(3 + 9 * PER_DELTA, 1929);
    assert!(3 + 9 * PER_DELTA <= LINE_PAYLOAD_MAX, "nine fit");
    assert!(3 + 10 * PER_DELTA > LINE_PAYLOAD_MAX, "ten do not");

    for (k, want_dropped, want_n) in [(8usize, false, 8), (9, false, 9), (10, true, 9)] {
        let names: Vec<String> = (0..k).map(|i| format!("delta_{i:02}")).collect();
        let text = "t".repeat(crate::probe::CAP);
        let deltas: Vec<(&str, Capture)> = names
            .iter()
            .map(|n| {
                assert_eq!(n.len(), 8, "the arithmetic above assumes an 8-byte name");
                (n.as_str(), debug(&text))
            })
            .collect();
        let mut buf = [0u8; LINE_PAYLOAD_MAX];
        let (len, dropped) = write_line_payload(&mut buf, &deltas);
        assert_eq!(dropped, want_dropped, "k={k}");
        let (flags, written) = parse(&buf[..len as usize]);
        assert_eq!(flags & 1, u8::from(want_dropped), "k={k}");
        assert_eq!(written.len(), want_n, "k={k}");
        for delta in &written {
            assert_eq!(
                delta.truncated, 0,
                "k={k}: a 200-byte text is at the cap, not over it"
            );
            assert_eq!(delta.text.as_deref().map(str::len), Some(crate::probe::CAP));
        }
    }
}

#[test]
fn the_payload_bound_fits_the_wire_formats_length_field() {
    assert!(LINE_PAYLOAD_MAX <= u16::MAX as usize, "{LINE_PAYLOAD_MAX}");
}

// -----------------------------------------------------------------------
// (d)-(e) the entry point
// -----------------------------------------------------------------------

/// The tests below drive the process-global recorder state, so they hold
/// this for the whole of their run. Nothing else in the crate's unit tests
/// reads `STATE`.
static GATE: Mutex<()> = Mutex::new(());
static UNIT: OnceLock<&'static Unit> = OnceLock::new();

/// One spool directory for the whole test binary: `SPOOL_DIR` is a
/// `OnceLock`, so it can only ever be one.
fn spool_dir() -> &'static Path {
    static DIR: OnceLock<PathBuf> = OnceLock::new();
    DIR.get_or_init(|| {
        let root = match std::env::var_os("CARGO_TARGET_DIR") {
            Some(t) if !t.is_empty() => PathBuf::from(t),
            _ => std::env::temp_dir(),
        };
        let dir = root
            .join("rt-unit")
            .join(format!("line-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).expect("scratch dir");
        let _ = crate::SPOOL_DIR.set(dir.clone());
        dir
    })
    .as_path()
}

/// A live recorder, without the transformer: `STATE_CALL`, a spool
/// directory and one registered unit. Restores `STATE` on drop, so a
/// failing test cannot leave the recorder on for the next one.
struct Recording {
    _gate: MutexGuard<'static, ()>,
    dir: &'static Path,
    unit: &'static Unit,
}

impl Recording {
    fn start() -> Recording {
        let gate = GATE.lock().unwrap_or_else(|e| e.into_inner());
        let dir = spool_dir();
        let unit = *UNIT.get_or_init(|| &*Box::leak(Box::new(Unit::new("line-tests"))));
        STATE.store(STATE_CALL, Ordering::Release);
        let ready = crate::ensure_dir().expect("the test set SPOOL_DIR and STATE_CALL");
        crate::unit_id(unit, ready).expect("the first unit registers");
        Recording {
            _gate: gate,
            dir,
            unit,
        }
    }

    /// The site word a record written for `site` carries.
    fn packed(&self, site: u32) -> u32 {
        crate::pack_site(self.unit.current_id().expect("registered"), site)
    }

    /// Every record in the directory written for `site`, whichever thread's
    /// spool it landed in.
    fn records_at(&self, site: u32) -> Vec<(u8, Vec<u8>)> {
        let want = self.packed(site);
        let mut out = Vec::new();
        for entry in std::fs::read_dir(self.dir).expect("spool dir") {
            let path = entry.expect("dir entry").path();
            if path.extension().and_then(|e| e.to_str()) != Some("spool") {
                continue;
            }
            let bytes = std::fs::read(&path).expect("read spool");
            if bytes.len() < HEADER_FIXED {
                continue;
            }
            let name_len = u16::from_le_bytes([bytes[6], bytes[7]]) as usize;
            let mut at = HEADER_FIXED + name_len;
            while at + RECORD_FIXED <= bytes.len() {
                let kind = bytes[at + 20];
                if kind == 0 {
                    break;
                }
                let site =
                    u32::from_le_bytes(bytes[at + 16..at + 20].try_into().expect("four bytes"));
                let len = u16::from_le_bytes([bytes[at + 22], bytes[at + 23]]) as usize;
                let payload = bytes[at + RECORD_FIXED..at + RECORD_FIXED + len].to_vec();
                if site == want {
                    out.push((kind, payload));
                }
                at += RECORD_FIXED + len;
            }
        }
        out
    }
}

impl Drop for Recording {
    fn drop(&mut self) {
        STATE.store(STATE_UNINIT, Ordering::Release);
    }
}

/// The positive control and the negative one in the same test, at the same
/// site: a `line` that writes nothing at tier `off` proves nothing unless
/// the same call writes something when the recorder is on.
/// (e) The deltas closure is called exactly once when the record is
/// written, and NOT AT ALL when it is not: at tier `off` a focused
/// workspace formats no `Debug`, allocates nothing and runs no `Debug` side
/// effect, although the probes are spliced unconditionally.
#[test]
fn line_writes_one_record_when_recording_and_nothing_at_tier_off() {
    let rec = Recording::start();
    let probes = Cell::new(0u32);
    line(rec.unit, 11, || {
        probes.set(probes.get() + 1);
        [("x", debug("5"))]
    });
    assert_eq!(
        probes.get(),
        1,
        "the probe ran once, for the record written"
    );
    let written = rec.records_at(11);
    assert_eq!(written.len(), 1, "one statement, one record");
    assert_eq!(written[0].0, KIND_LINE);
    assert_eq!(written[0].0, 6, "LINE is wire kind 6");
    let (flags, parsed) = parse(&written[0].1);
    assert_eq!(flags, 0);
    assert_eq!(parsed.len(), 1);
    assert_eq!(parsed[0].name, "x");
    assert_eq!(parsed[0].text.as_deref(), Some("5"));

    STATE.store(STATE_OFF, Ordering::Release);
    line(rec.unit, 11, || {
        probes.set(probes.get() + 1);
        [("x", debug("5"))]
    });
    assert_eq!(
        rec.records_at(11).len(),
        1,
        "tier off writes no LINE record at all"
    );
    assert_eq!(
        probes.get(),
        1,
        "and tier off does not even CALL the probe: no Debug impl runs"
    );
}

/// A2: a statement that wrote nothing -- the parameters LINE of a function
/// with no parameters -- splices `|| []`, which has to type-check with no
/// turbofish and no annotation.
#[test]
fn an_empty_delta_array_is_still_a_record() {
    let rec = Recording::start();
    line(rec.unit, 15, || []);
    let written = rec.records_at(15);
    assert_eq!(written.len(), 1);
    assert_eq!(written[0].1, vec![0, 0, 0], "flags 0, n 0");
}

/// (f) A `Debug` impl that calls `line` again. The outer capture runs
/// inside the runtime scope, so the inner call is inert -- and its probe
/// closure is never called either.
static INNER_PROBES: AtomicU32 = AtomicU32::new(0);

struct CallsLine(&'static Unit);

impl Debug for CallsLine {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        line(self.0, 13, || {
            INNER_PROBES.fetch_add(1, Ordering::Relaxed);
            [("inner", debug("re-entered"))]
        });
        f.write_str("outer")
    }
}

#[test]
fn a_line_reached_from_inside_the_instrument_records_nothing() {
    let rec = Recording::start();
    INNER_PROBES.store(0, Ordering::Relaxed);
    line(rec.unit, 12, || {
        [("v", crate::probe_cap!(&CallsLine(rec.unit)))]
    });
    assert_eq!(
        rec.records_at(13).len(),
        0,
        "the Debug impl's own line() is inert: the instrument adds no rows"
    );
    assert_eq!(
        INNER_PROBES.load(Ordering::Relaxed),
        0,
        "and an inert line() never calls its probe"
    );
    let written = rec.records_at(12);
    assert_eq!(written.len(), 1, "exactly one record, the outer one");
    let (_, parsed) = parse(&written[0].1);
    assert_eq!(parsed[0].text.as_deref(), Some("outer"));
}

/// The same rule through the runtime's own test hook, with no `Debug` impl
/// in the way.
#[test]
fn line_is_inert_while_the_runtime_is_already_running() {
    let rec = Recording::start();
    let probes = Cell::new(0u32);
    crate::__in_runtime(|| {
        line(rec.unit, 14, || {
            probes.set(probes.get() + 1);
            [("x", debug("5"))]
        })
    });
    assert_eq!(rec.records_at(14).len(), 0);
    assert_eq!(probes.get(), 0, "an inert line() calls no probe");
}
