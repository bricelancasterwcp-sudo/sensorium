//! The focus tier's LINE event: one record per completed statement of a focused
//! function, carrying the bindings that statement wrote.
//!
//! Under `cargo sensorium --focus <qualname>` the transformer splices, after
//! every statement of every matched function,
//!
//! ```ignore
//! ::sensorium_rt::line(&crate::__SENSORIUM_UNIT, <site>, || {
//!     [("x", ::sensorium_rt::probe_cap!(&x))]
//! });
//! ```
//!
//! and the payload that produces is `exit.rs`'s RETURN value block -- tag,
//! truncated flag, capped text -- repeated once per delta with the binding's
//! name in front of it (design 2026-09-06 §3.4):
//!
//! ```text
//! u8  flags        bit0 = the row is short: something did not fit
//! u16 n            blocks present -- the deltas, then the unbound names
//! n × { u16 name_len, name UTF-8,
//!       u8 tag (0 no value | 1 debug text | 2 unread | 3 unbound),
//!       u8 truncated,
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
//! **The deltas are a CLOSURE, and that is the whole reason a `Debug` impl is
//! never invoked at tier `off`** -- the same sentence `exit.rs` opens with, and
//! the same shape: `ret` takes `cap: impl FnOnce(&T)`, `line` takes
//! `impl FnOnce() -> [..; N]`. The closure is called inside the `STATE ==
//! STATE_CALL` gate AND inside the runtime scope, after the unit and the spool
//! directory have answered -- so a focused workspace run at `--tier off`
//! formats nothing, allocates nothing, and runs no `Debug` side effect, even
//! though the probes are spliced unconditionally at compile time (the focus is
//! a compile-time decision, design F2). Design amendment A5, 2026-09-06.
//!
//! **And it formats inside the runtime scope.** `ret` invokes its probe closure
//! inside `stash_return`, which is what keeps a workspace `Debug` impl that
//! calls instrumented code from putting rows in the trace (spec §3.6,
//! `rust/HONESTY.md` §9). Two things keep that true here: `emit_line` takes the
//! scope BEFORE it calls the closure, and `probe_cap!` formats inside
//! [`__probe_cap_scope`] as well -- so the promise holds even for a capture
//! somebody builds outside a `line` call. The impl still runs -- once per
//! captured delta -- it just records nothing.
//!
//! **What a dropped delta is.** The payload is bounded by [`LINE_PAYLOAD_MAX`],
//! the same buffer `exit.rs` writes a RETURN into. When the next delta would not
//! fit, it and every later one are dropped and `flags` bit0 is set: a short
//! record says it is short. Names are never truncated, because a converter joins
//! on them; a name that does not fit drops its delta whole.
//!
//! **What an unbound name is.** A block-like statement -- a `{ .. }`, an `if`,
//! a `match`, a loop -- kills the bindings its inner blocks and its own head
//! pattern made. Its probe calls [`line_unbinding`] rather than [`line`] and
//! hands over those names, which ride the SAME payload as tag-3 blocks after
//! the deltas: name only, no value, no new record kind and no header change
//! (design 2026-09-12 R3). A reader that folds `deltas` forward pops them at
//! this row, so a dead `let` stops answering where it is dead. The budget is
//! over the whole payload and the stop rule is the delta's: a name that does
//! not fit sets bit0 and ends the row, which stays a prefix of what the
//! statement did. `line` never writes one -- the fragment of a statement that
//! unbinds nothing is byte for byte the fragment 0.4.1 spliced (R5).

use std::path::Path;
use std::sync::atomic::Ordering;

use crate::exit::{TAG_DEBUG, TAG_UNREAD};
use crate::probe::{self, Capture};
use crate::spool::{self, KIND_LINE, OUTCOME_NONE, SITE_INDEX_MASK};
use crate::{thread, Unit, STATE, STATE_CALL};

/// `bit0` of the payload's flags byte: at least one delta did not fit and was
/// left out, along with every delta after it.
pub(crate) const FLAG_DELTAS_DROPPED: u8 = 1 << 0;

/// `bit0..` unchanged. The fourth delta tag: a name with no value that went out
/// of scope on this row (design 2026-09-12 R3).
///
/// `exit.rs` owns 0..=2, the RETURN value block's tags that a delta reuses; 3 is
/// this module's alone, because a returned value cannot go out of scope.
pub(crate) const TAG_UNBOUND: u8 = 3;

/// The payload's fixed head: `u8 flags`, `u16 n`.
const LINE_HEADER: usize = 3;

/// The most one LINE payload can carry: room for eight capped deltas with
/// their names (design amendment A5, 2026-09-06).
///
/// A delta costs `2 + name + 1 + 1 + 2 + text` bytes, so a fully capped one with
/// an eight-character name is 214 and eight of them plus the three-byte head are
/// 1_715 -- the sizing this number is chosen for. It is NOT `exit.rs`'s
/// [`crate::exit::RETURN_PAYLOAD_MAX`] (325, which fits exactly one capped
/// delta): a
/// statement can write several bindings, and a bound that drops the second one
/// of a `let (a, b) = ..` would make the honest `flags.bit0` a routine event
/// rather than a rare one. Still far inside the wire's `u16` payload length, and
/// still a stack array -- one built in `write_and_emit`, which is `#[inline(never)]`
/// and reached only when the recorder is live, so the inert path never grows a
/// 2 KiB frame. What does not fit is dropped and said to be dropped.
pub(crate) const LINE_PAYLOAD_MAX: usize = 2048;

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
/// `deltas` is a closure returning an array of `(name, capture)` -- the array
/// the transformer writes as a literal, `|| [("x", probe_cap!(&x))]`, and `|| []`
/// for a statement that wrote nothing (a parameters LINE of a function with no
/// parameters, design amendment A2). It is called ONLY when this thread is
/// actually about to write the record, so at tier `off` no `Debug` impl runs.
///
/// Inert -- no record, no capture, no allocation -- when the recorder is not
/// recording, and when the runtime is already running on this thread. Unlike
/// `enter` it never initialises the process and never registers a unit: a LINE
/// belongs to a frame some `enter` already opened, and a unit with no id has no
/// such frame.
#[inline]
pub fn line<const N: usize>(
    unit: &'static Unit,
    site: u32,
    deltas: impl FnOnce() -> [(&'static str, Capture); N],
) {
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        emit_line(unit, site, deltas);
    }
}

/// A block-like statement's LINE: the deltas it wrote AND the names its inner
/// blocks and its own head pattern bound, which are dead after it.
///
/// `unbound` is written after the deltas as tag-3 blocks (design 2026-09-12 R3,
/// §5.3); `line` is unchanged and never writes one. The names are
/// `&'static [&'static str]` because the transformer splices them as a literal,
/// `&["a", "b"]` (plan decision A6): the runtime allocates nothing to carry
/// them, and a statement with nothing to unbind gets `line` instead.
///
/// Everything else is [`line`]'s: the same gate, the same reentrancy rule, the
/// same closure called only when the record is actually about to be written --
/// so at tier `off` a block-like statement formats no `Debug` either.
#[inline]
pub fn line_unbinding<const N: usize>(
    unit: &'static Unit,
    site: u32,
    deltas: impl FnOnce() -> [(&'static str, Capture); N],
    unbound: &'static [&'static str],
) {
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        emit_line_unbinding(unit, site, deltas, unbound);
    }
}

/// [`line`]'s emitter: [`emit_line_unbinding`] with nothing to unbind.
///
/// One body writes both records rather than two that drift: the gate, the
/// reentrancy scope, the unit id, the spool directory and the probe's one call
/// site are stated once, and `line`'s bytes are `line_unbinding`'s with an empty
/// name list -- which is what makes R5's "the fragment of a statement that
/// unbinds nothing is unchanged" a fact about this file rather than a promise.
#[inline]
fn emit_line<const N: usize>(
    unit: &'static Unit,
    site: u32,
    deltas: impl FnOnce() -> [(&'static str, Capture); N],
) {
    emit_line_unbinding(unit, site, deltas, &[]);
}

#[inline(never)]
fn emit_line_unbinding<const N: usize>(
    unit: &'static Unit,
    site: u32,
    deltas: impl FnOnce() -> [(&'static str, Capture); N],
    unbound: &'static [&'static str],
) {
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
    // The probe runs HERE and nowhere earlier: inside the tier gate, inside the
    // runtime scope, and after the unit and the spool directory have answered.
    // A `Debug` impl this formats therefore records nothing, and one that is
    // never formatted has no side effect to have.
    let deltas = deltas();
    write_and_emit(dir, crate::pack_site(id, site), &deltas, unbound);
}

/// Everything about writing a LINE record that does NOT depend on the call
/// site: the payload buffer, the writer and the spool append.
///
/// Split out of [`emit_line_unbinding`] because that one is monomorphised per call site
/// -- a fresh copy for every `(N, closure type)`, and the transformer emits one
/// call per statement of a focused function. This tail is compiled ONCE for the
/// whole program, so what each copy costs is four checks and a call rather than
/// a 2 KiB frame and an inlined payload writer.
#[inline(never)]
fn write_and_emit(dir: &Path, site: u32, deltas: &[(&'static str, Capture)], unbound: &[&str]) {
    let mut buf = [0u8; LINE_PAYLOAD_MAX];
    let (len, _dropped) = write_line_payload(&mut buf, deltas, unbound);
    thread::emit(dir, site, KIND_LINE, OUTCOME_NONE, &buf[..len as usize]);
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
///
/// `unbound` -- the names a block-like statement killed -- is written AFTER the
/// deltas, one tag-3 block each, and `n` counts both kinds. The budget covers
/// the whole payload and the stop rule is the same one, so a row that dropped a
/// delta writes no name after it: the prefix reading holds across both lists.
pub(crate) fn write_line_payload(
    buf: &mut [u8; LINE_PAYLOAD_MAX],
    deltas: &[(&str, Capture)],
    unbound: &[&str],
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
    // Only if every delta got in: a name written after a dropped delta would
    // sit behind a gap, and `n` would no longer count a prefix of the row.
    if !dropped {
        for name in unbound {
            // No value, so no text block and no cap to apply: `2 + name + 2`.
            if at + 2 + name.len() + 2 > LINE_PAYLOAD_MAX {
                dropped = true;
                break;
            }
            buf[at..at + 2].copy_from_slice(&(name.len() as u16).to_le_bytes());
            at += 2;
            buf[at..at + name.len()].copy_from_slice(name.as_bytes());
            at += name.len();
            buf[at] = TAG_UNBOUND;
            // A name was never read, so it was never cut: the byte is there
            // because every block has it, and it is always 0.
            buf[at + 1] = 0;
            at += 2;
            n += 1;
        }
    }
    buf[0] = if dropped { FLAG_DELTAS_DROPPED } else { 0 };
    buf[1..3].copy_from_slice(&n.to_le_bytes());
    (at as u16, dropped)
}

#[cfg(test)]
mod tests;
