//! The focus tier's LINE event: one record per completed statement of a focused
//! function, carrying the bindings that statement wrote.
//!
//! Under `cargo sensorium --focus <qualname>` the transformer splices, after
//! every statement of every matched function,
//!
//! ```ignore
//! ::sensorium_rt::line(&crate::__SENSORIUM_UNIT, <site>, &[
//!     ("x", ::sensorium_rt::probe_cap!(&x)),
//! ]);
//! ```
//!
//! and the payload that produces is `exit.rs`'s RETURN value block -- tag,
//! truncated flag, capped text -- repeated once per delta with the binding's
//! name in front of it (design 2026-09-06 §3.4):
//!
//! ```text
//! u8  flags        bit0 = deltas dropped
//! u16 n            deltas present
//! n × { u16 name_len, name UTF-8,
//!       u8 tag (0 no value | 1 debug text | 2 unread), u8 truncated,
//!       [u16 text_len, text UTF-8]   -- present iff tag == 1 }
//! ```
//!
//! **Why `probe_cap` is a macro.** `probe.rs`'s ladder specialises by autoref at
//! the CALL SITE: `(&&Probe(v)).debug_cap()` picks the `Debug` impl only where
//! the compiler can see `T: Debug`. Inside a `fn probe_cap<T>(v: &T)` there is
//! no such bound, so the fallback would answer for every value and every delta
//! in every trace would read *unread*. The test
//! `a_generic_fn_cannot_carry_the_ladder_which_is_why_probe_cap_is_a_macro`
//! measures exactly that, so the reason survives someone tidying the macro away.
//!
//! **The capture runs inside the runtime scope.** `ret` invokes its probe
//! closure inside `stash_return`, which is what keeps a workspace `Debug` impl
//! that calls instrumented code from putting rows in the trace (spec §3.6,
//! `rust/HONESTY.md` §9). A LINE's deltas are built at the call site, BEFORE
//! `line` is entered, so the scope has to travel with the capture instead:
//! `probe_cap!` formats inside [`__probe_cap_scope`]. The impl still runs -- once
//! per captured delta -- it just records nothing.
//!
//! **What a dropped delta is.** The payload is bounded by [`LINE_PAYLOAD_MAX`],
//! the same buffer `exit.rs` writes a RETURN into. When the next delta would not
//! fit, it and every later one are dropped and `flags` bit0 is set: a short
//! record says it is short. Names are never truncated, because a converter joins
//! on them; a name that does not fit drops its delta whole.

use std::sync::atomic::Ordering;

use crate::exit::{RETURN_PAYLOAD_MAX, TAG_DEBUG, TAG_UNREAD};
use crate::probe::{self, Capture};
use crate::spool::{self, KIND_LINE, OUTCOME_NONE, SITE_INDEX_MASK};
use crate::{thread, Unit, STATE, STATE_CALL};

/// `bit0` of the payload's flags byte: at least one delta did not fit and was
/// left out, along with every delta after it.
pub(crate) const FLAG_DELTAS_DROPPED: u8 = 1 << 0;

/// The payload's fixed head: `u8 flags`, `u16 n`.
const LINE_HEADER: usize = 3;

/// The most one LINE payload can carry.
///
/// The RETURN buffer's capacity, deliberately: one statement's deltas cost what
/// one returned value costs, the wire's `u16` length field is honoured with room
/// to spare, and the buffer stays a stack array a probe on every statement can
/// afford. What does not fit is dropped and said to be dropped.
pub(crate) const LINE_PAYLOAD_MAX: usize = RETURN_PAYLOAD_MAX;

/// Read one borrowed value through `probe.rs`'s ladder: capped `Debug` text, or
/// *unread* when the type has no `Debug` impl.
///
/// A macro rather than a function because the ladder specialises at the call
/// site (see this module's header). The value is read INSIDE a runtime scope, so
/// instrumented code the `Debug` impl calls records nothing.
///
/// ```ignore
/// let c = ::sensorium_rt::probe_cap!(&x);
/// ```
#[macro_export]
macro_rules! probe_cap {
    ($v:expr) => {
        $crate::__probe_cap_scope(|| {
            #[allow(unused_imports)]
            use $crate::probe::{DebugCap as _, NoDebugCap as _};
            (&&$crate::probe::Probe($v)).debug_cap()
        })
    };
}

/// [`probe_cap!`]'s body, and not otherwise part of the instrumented-code API.
///
/// `enter_runtime` rather than `try_enter_runtime`: the value is read whatever
/// the depth already is -- the promise is that the `Debug` impl runs and that
/// nothing it calls is recorded, not that it is skipped -- and the scope's `Drop`
/// puts the depth back where it found it.
#[doc(hidden)]
pub fn __probe_cap_scope(read: impl FnOnce() -> Capture) -> Capture {
    let _scope = thread::enter_runtime();
    read()
}

/// Record one completed statement of a focused function and the bindings it
/// wrote.
///
/// Inert -- no record, no allocation -- when the recorder is not recording, and
/// when the runtime is already running on this thread. Unlike `enter` it never
/// initialises the process and never registers a unit: a LINE belongs to a frame
/// some `enter` already opened, and a unit with no id has no such frame.
#[inline]
pub fn line(unit: &'static Unit, site: u32, deltas: &[(&str, Capture)]) {
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        emit_line(unit, site, deltas);
    }
}

#[inline(never)]
fn emit_line(unit: &'static Unit, site: u32, deltas: &[(&str, Capture)]) {
    // Reentrancy: a statement reached from inside the instrument records
    // nothing, the same rule `enter`, `ret` and the err sites keep (spec §3.6).
    let Some(_scope) = thread::try_enter_runtime() else {
        return;
    };
    // No registration here: a unit with no id has no open frame for this LINE to
    // belong to, and the converter attaches the row to the thread's current
    // frame.
    let Some(id) = unit.current_id() else {
        return;
    };
    // Re-reads STATE, so a recorder that went inert between `line`'s gate and
    // here still writes nothing.
    let Some(dir) = crate::ensure_dir() else {
        return;
    };
    debug_assert!(
        site <= SITE_INDEX_MASK,
        "site index {site} does not fit the wire format's 24 bits and would alias"
    );
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, _dropped) = write_line_payload(&mut buf, deltas);
    thread::emit(
        dir,
        crate::pack_site(id, site),
        KIND_LINE,
        OUTCOME_NONE,
        &buf[..len as usize],
    );
}

/// Write the deltas into `buf` and return `(payload_len, dropped)`.
///
/// Each text is capped by `cap_utf8` at [`probe::CAP`], exactly as the RETURN
/// writer caps its own -- `spool::record` refuses a payload it cannot describe
/// rather than clamping one, so every cut happens here, on a char boundary, and
/// is witnessed by the delta's `truncated` byte.
///
/// A delta that does not fit STOPS the loop rather than skipping to the next
/// one: "the first n of them" is a thing a reader can reason about, and a
/// converter that meets bit0 knows the row is a prefix of what the statement
/// wrote, not an arbitrary subset of it.
pub(crate) fn write_line_payload(
    buf: &mut [u8; LINE_PAYLOAD_MAX],
    deltas: &[(&str, Capture)],
) -> (u16, bool) {
    let mut at = LINE_HEADER;
    let mut n: u16 = 0;
    let mut dropped = false;
    for (name, capture) in deltas {
        // `Capture { text: None }` is *unread*, never "no value": a delta is a
        // binding the statement wrote, so tag 0 -- the RETURN block's "there was
        // no value at all" -- cannot arise on a LINE.
        let (tag, text, truncated) = match capture.text.as_deref() {
            None => (TAG_UNREAD, "", false),
            Some(text) => {
                let (text, cut_here) = spool::cap_utf8(text, probe::CAP);
                (TAG_DEBUG, text, capture.truncated || cut_here)
            }
        };
        let mut need = 2 + name.len() + 2;
        if tag == TAG_DEBUG {
            need += 2 + text.len();
        }
        if at + need > LINE_PAYLOAD_MAX {
            dropped = true;
            break;
        }
        buf[at..at + 2].copy_from_slice(&(name.len() as u16).to_le_bytes());
        at += 2;
        buf[at..at + name.len()].copy_from_slice(name.as_bytes());
        at += name.len();
        buf[at] = tag;
        buf[at + 1] = u8::from(truncated);
        at += 2;
        if tag == TAG_DEBUG {
            buf[at..at + 2].copy_from_slice(&(text.len() as u16).to_le_bytes());
            at += 2;
            buf[at..at + text.len()].copy_from_slice(text.as_bytes());
            at += text.len();
        }
        n += 1;
    }
    buf[0] = if dropped { FLAG_DELTAS_DROPPED } else { 0 };
    buf[1..3].copy_from_slice(&n.to_le_bytes());
    (at as u16, dropped)
}

#[cfg(test)]
mod tests {
    use super::*;

    use std::fmt::{self, Debug};
    use std::path::{Path, PathBuf};
    use std::sync::atomic::Ordering;
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
        let deltas: Vec<(&str, Capture)> =
            names.iter().map(|n| (n.as_str(), debug(&text))).collect();
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
    #[test]
    fn line_writes_one_record_when_recording_and_nothing_at_tier_off() {
        let rec = Recording::start();
        let deltas = [("x", debug("5"))];
        line(rec.unit, 11, &deltas);
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
        line(rec.unit, 11, &deltas);
        assert_eq!(
            rec.records_at(11).len(),
            1,
            "tier off writes no LINE record at all"
        );
    }

    /// A `Debug` impl that calls `line` again. The outer capture runs inside
    /// the runtime scope, so the inner call is inert: one record, not two.
    struct CallsLine(&'static Unit);

    impl Debug for CallsLine {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            line(self.0, 13, &[("inner", debug("re-entered"))]);
            f.write_str("outer")
        }
    }

    #[test]
    fn a_line_reached_from_inside_the_instrument_records_nothing() {
        let rec = Recording::start();
        line(
            rec.unit,
            12,
            &[("v", crate::probe_cap!(&CallsLine(rec.unit)))],
        );
        assert_eq!(
            rec.records_at(13).len(),
            0,
            "the Debug impl's own line() is inert: the instrument adds no rows"
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
        crate::__in_runtime(|| line(rec.unit, 14, &[("x", debug("5"))]));
        assert_eq!(rec.records_at(14).len(), 0);
    }
}
