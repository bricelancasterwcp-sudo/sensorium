//! The two halves of err flow that are not the chain machine itself: the
//! PRE-PASS that hands [`crate::convert::chains`] one thread's records, and the
//! event payload a RAISE/HANDLED row carries.
//!
//! **Why a pre-pass.** Every chain fact but one is known at the record itself,
//! and [`crate::convert::frames`] writes events as it walks. The exception is
//! the terminal: how a chain ENDED is a fact about a later record (the holder
//! frame's close, or the thread's end), and an event already written cannot
//! grow one. So the whole stream is walked twice -- once here, to mint chain
//! identity per thread, and once by `frames.rs`, which looks each event's
//! chain up by `(thread, seq)`. The alternative, an `UPDATE` over `events`
//! after the fact, would write the same row twice and make the payload a
//! moving target for anything reading the file mid-conversion.
//!
//! **This pass never refuses.** A record it cannot resolve -- an unregistered
//! unit, an unknown site, a malformed payload -- is skipped silently HERE,
//! because `frames.rs` meets the same record and refuses the whole trace with
//! pid, thread and seq. Two error paths for one defect would only give a
//! person two different sentences for it.

use std::collections::{BTreeMap, HashMap};

use serde_json::{json, Map, Value};

use crate::convert::chains::{self, At, ChainEvent, ErrText, Input, Outcome, Rec};
use crate::convert::manifest::{RetKind, SiteInfo};
use crate::convert::merge::MergeResult;
use crate::convert::spool::{
    self, How, KIND_CALL, KIND_HANDLED, KIND_RAISE, KIND_RETURN, KIND_THREAD_END,
};

/// Wire version 3: the only one whose `err` RETURN carries the error type
/// block, and so the only one a synthesised origin RAISE can be built from.
const VERSION_V3: u8 = 3;

/// Every thread's chain events, by the `(thread, seq)` the writer knows them
/// by. Two maps rather than one keyed by [`At`]: an `err` RETURN's seq carries
/// BOTH the synthesised origin RAISE and (never at once, but the index must
/// not assume it) whatever the record itself minted.
pub struct ChainIndex {
    by_record: HashMap<(u32, u64), ChainEvent>,
    by_exit: HashMap<(u32, u64), ChainEvent>,
}

impl ChainIndex {
    /// The chain fact for the err-flow record at `(thread, seq)`.
    #[must_use]
    pub fn at_record(&self, thread: u32, seq: u64) -> Option<&ChainEvent> {
        self.by_record.get(&(thread, seq))
    }

    /// The chain fact for the origin RAISE synthesised in front of the RETURN
    /// at `(thread, seq)`.
    #[must_use]
    pub fn at_exit(&self, thread: u32, seq: u64) -> Option<&ChainEvent> {
        self.by_exit.get(&(thread, seq))
    }
}

/// What the pre-pass needs to read a record: the same lookups `frames.rs`
/// builds, plus each thread's wire version.
pub struct IndexInput<'a> {
    pub merged: &'a MergeResult,
    pub unit_by_id: &'a HashMap<u8, &'a str>,
    pub site_lookup: &'a HashMap<&'a str, BTreeMap<u32, SiteInfo>>,
    /// Thread serial -> the wire version of that thread's spool file.
    pub versions: &'a BTreeMap<u32, u8>,
    /// The serial the main thread has; every other is a spawned one, which is
    /// what tells an `Err` left in a `JoinHandle` from one that propagated.
    pub main_serial: u32,
}

/// Walk every record once, per thread, and mint chain identity.
#[must_use]
pub fn build_index(input: &IndexInput) -> ChainIndex {
    let mut per_thread: BTreeMap<u32, Vec<Input>> = BTreeMap::new();
    // One `ret` per open frame, so a `-> ()` fn's wire outcome 0 is read as the
    // `ok` close it is -- exactly the `is_unit_none` rule `frames.rs` applies
    // to the same record, and the difference between a chain ENDING in that
    // frame and one merely passing through it.
    let mut rets: HashMap<u32, Vec<Option<RetKind>>> = HashMap::new();

    for m in &input.merged.records {
        let thread = m.thread_serial;
        let r = &m.record;
        let version = input.versions.get(&thread).copied().unwrap_or(VERSION_V3);
        let rec = match r.kind {
            KIND_CALL => {
                let Some(site) = site_of(input, r.site) else {
                    continue;
                };
                rets.entry(thread).or_default().push(site.ret);
                Rec::Call {
                    test: site.test,
                    main: site.main,
                }
            }
            KIND_RETURN => {
                let ret = rets.entry(thread).or_default().pop().flatten();
                let typed_err = r.outcome == 2 && version >= VERSION_V3;
                let text = if typed_err {
                    match spool::parse_return_payload("", &r.payload, true) {
                        Ok(p) => ErrText {
                            msg: err_debug(&p),
                            type_name: p.err_type,
                        },
                        Err(_) => continue,
                    }
                } else {
                    ErrText::default()
                };
                Rec::Return {
                    outcome: outcome_of(r.outcome, typed_err, ret),
                    text,
                }
            }
            KIND_RAISE | KIND_HANDLED => {
                let Ok(how) = spool::parse_how("", r.kind, r.outcome) else {
                    continue;
                };
                let Ok(p) = spool::parse_errflow_payload("", &r.payload) else {
                    continue;
                };
                Rec::ErrFlow {
                    how,
                    // A text the probe had to cut is not an identity: comparing
                    // one 200-byte prefix against another would split a chain
                    // whose two sites cut at different places. Unknown falls
                    // back to matching on the type alone, which is the reading
                    // that can only ever merge (AMBIGUOUS), never split.
                    text: ErrText {
                        type_name: p.type_name,
                        msg: if p.msg_truncated { None } else { p.msg },
                    },
                }
            }
            KIND_THREAD_END => Rec::ThreadEnd,
            _ => continue,
        };
        per_thread
            .entry(thread)
            .or_default()
            .push(Input { seq: r.seq, rec });
    }

    let mut by_record = HashMap::new();
    let mut by_exit = HashMap::new();
    for (thread, records) in per_thread {
        for event in chains::mint(&records, thread != input.main_serial) {
            let map = match event.at {
                At::Record => &mut by_record,
                At::ExitBefore => &mut by_exit,
            };
            map.insert((thread, event.seq), event);
        }
    }
    ChainIndex { by_record, by_exit }
}

/// The ERROR's own `Debug` text out of an `err` RETURN's payload.
///
/// The two probes read two different values: an err-flow site reads the `Err`'s
/// payload (`Os { code: 2 }`), while a frame's exit reads the whole `Result`
/// (`Err(Os { code: 2 })`), because that is what the fn returned. `Result`'s
/// `Debug` is derived, so the second is exactly `"Err("` + the first + `")"`,
/// and unwrapping it is what lets one chain be recognised across a frame
/// boundary at all -- and what makes `exc.msg` mean the same thing on every
/// event.
///
/// `None` -- unread -- for a value the probe could not read, one it had to cut
/// (a cut text is a prefix, not an identity), and one that does not have the
/// shape at all, which no `Result` produces but a future `impl Try` might.
fn err_debug(p: &spool::ReturnPayload) -> Option<String> {
    if p.tag != spool::TAG_DEBUG || p.truncated {
        return None;
    }
    Some(unwrap_err_debug(&p.text)?.to_owned())
}

/// `Err(<inner>)` -> `<inner>`, for IDENTITY: both delimiters must be there,
/// because a rendering the probe had to cut is a PREFIX of an identity and not
/// one (two sites cutting at different lengths would split one chain).
fn unwrap_err_debug(text: &str) -> Option<&str> {
    text.strip_prefix("Err(")?.strip_suffix(')')
}

/// The same unwrapping, for DISPLAY, where a cut rendering is still the error's
/// text: only the closing `)` is missing, and keeping `Err(` on it would make
/// `exc.msg` mean the error on every event except a truncated one. The `trunc`
/// flag beside it is what says the text is short; the `Result`'s wrapper was
/// never part of the error.
#[must_use]
pub fn err_debug_text(text: &str) -> &str {
    match text.strip_prefix("Err(") {
        Some(inner) => inner.strip_suffix(')').unwrap_or(inner),
        None => text,
    }
}

fn site_of<'a>(input: &'a IndexInput, site_word: u32) -> Option<&'a SiteInfo> {
    let (unit_id, index) = spool::unpack_site(site_word);
    let metadata = input.unit_by_id.get(&unit_id)?;
    input.site_lookup.get(metadata)?.get(&index)
}

/// The wire's outcome byte as the chain machine reads it.
///
/// Two readings are not the byte's own: wire outcome 0 on a `ret: unit` frame
/// is the `ok` close that fn actually made (`rust/HONESTY.md` §1), and an
/// `err` with no type block is a v2 spool's, which carries no origin RAISE and
/// so cannot be a chain's birth -- it moves a chain it holds up to the caller
/// exactly as a `none` does.
fn outcome_of(byte: u8, typed_err: bool, ret: Option<RetKind>) -> Outcome {
    match byte {
        0 if ret == Some(RetKind::Unit) => Outcome::Ok,
        1 => Outcome::Ok,
        2 if typed_err => Outcome::Err,
        3 => Outcome::Panic,
        _ => Outcome::None,
    }
}

// ---------------------------------------------------------------------------
// The event payload
// ---------------------------------------------------------------------------

/// Everything a RAISE/HANDLED row says, gathered from the record, the manifest
/// and the chain machine.
pub struct ErrFlowEvent<'a> {
    pub how: How,
    pub type_name: Option<&'a str>,
    pub type_truncated: bool,
    pub msg: Option<&'a str>,
    pub msg_truncated: bool,
    /// `<file>:<line>` of the SITE, from the manifest row.
    pub loc: String,
    pub chain: &'a ChainEvent,
}

/// The payload of one RAISE/HANDLED event.
///
/// `exc.type` and `exc.msg` are required of every exception a reader renders
/// (TRACE-FORMAT §5: `fmt_exc` indexes both), and the sanctioned way to omit
/// one is to say so in `unread`. So a probe that could read neither -- an
/// `Err(_) =>` arm, which binds nothing (design R4) -- reports the type of the
/// chain it continues, or the bare `"Err"` with both fields declared unread.
/// It never invents one.
#[must_use]
pub fn payload(e: &ErrFlowEvent) -> Value {
    let mut exc = Map::new();
    let mut unread: Vec<&str> = Vec::new();
    exc.insert("kind".to_owned(), json!("err"));
    match e.type_name.or(e.chain.origin_type.as_deref()) {
        Some(t) => {
            exc.insert("type".to_owned(), json!(t));
        }
        None => {
            exc.insert("type".to_owned(), json!("Err"));
            unread.push("type");
        }
    }
    if e.type_truncated {
        exc.insert("type_trunc".to_owned(), json!(true));
    }
    match e.msg {
        Some(m) => {
            exc.insert("msg".to_owned(), json!(m));
            if e.msg_truncated {
                exc.insert("trunc".to_owned(), json!(true));
            }
        }
        None => unread.push("msg"),
    }
    exc.insert("serial".to_owned(), json!(e.chain.serial));
    exc.insert("loc".to_owned(), json!(e.loc));
    if !unread.is_empty() {
        exc.insert("unread".to_owned(), json!(unread));
    }

    let mut chain = Map::new();
    chain.insert("serial".to_owned(), json!(e.chain.serial));
    chain.insert("hop".to_owned(), json!(e.chain.hop));
    chain.insert("origin".to_owned(), json!(e.chain.origin.as_str()));
    chain.insert("translated".to_owned(), json!(e.chain.translated));
    if let Some(t) = e.chain.terminal {
        chain.insert("terminal".to_owned(), json!(t.as_str()));
    }

    json!({"exc": Value::Object(exc), "how": e.how.as_str(), "chain": Value::Object(chain)})
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::convert::chains::Origin;

    fn chain_event() -> ChainEvent {
        ChainEvent {
            seq: 7,
            at: At::Record,
            serial: 1 << 32,
            hop: 2,
            origin: Origin::Workspace,
            translated: false,
            terminal: None,
            origin_type: Some("io::Error".to_owned()),
        }
    }

    #[test]
    fn a_read_error_carries_its_type_message_serial_and_loc() {
        let chain = chain_event();
        let v = payload(&ErrFlowEvent {
            how: How::Try,
            type_name: Some("io::Error"),
            type_truncated: false,
            msg: Some("Os { code: 2 }"),
            msg_truncated: false,
            loc: "a/src/lib.rs:12".to_owned(),
            chain: &chain,
        });
        assert_eq!(
            v,
            json!({
                "exc": {"kind": "err", "type": "io::Error", "msg": "Os { code: 2 }",
                        "serial": 4_294_967_296u64, "loc": "a/src/lib.rs:12"},
                "how": "try",
                "chain": {"serial": 4_294_967_296u64, "hop": 2, "origin": "workspace",
                          "translated": false},
            })
        );
    }

    /// The ladder named the type but could not read the value: `unread` is the
    /// only honest way to omit `msg` (TRACE-FORMAT §5).
    #[test]
    fn a_message_the_probe_could_not_read_is_declared_unread() {
        let chain = chain_event();
        let v = payload(&ErrFlowEvent {
            how: How::SinkOk,
            type_name: Some("E"),
            type_truncated: false,
            msg: None,
            msg_truncated: false,
            loc: "a.rs:1".to_owned(),
            chain: &chain,
        });
        assert_eq!(v["exc"]["unread"], json!(["msg"]));
        assert_eq!(v["exc"]["type"], json!("E"));
        assert!(v["exc"].get("msg").is_none());
    }

    /// An `Err(_) =>` arm binds nothing, so its type comes from the chain it
    /// continues (design R4) -- never invented, never the record's own.
    #[test]
    fn an_unbound_arm_takes_the_type_of_the_chain_it_continues() {
        let chain = chain_event();
        let v = payload(&ErrFlowEvent {
            how: How::ArmPropagate,
            type_name: None,
            type_truncated: false,
            msg: None,
            msg_truncated: false,
            loc: "a.rs:1".to_owned(),
            chain: &chain,
        });
        assert_eq!(v["exc"]["type"], json!("io::Error"));
        assert_eq!(v["exc"]["unread"], json!(["msg"]));
    }

    /// With no chain type either, the type is declared unread rather than
    /// guessed -- and `"Err"` is what a renderer prints, not a claim.
    #[test]
    fn an_unbound_arm_with_no_chain_type_declares_both_fields_unread() {
        let mut chain = chain_event();
        chain.origin_type = None;
        let v = payload(&ErrFlowEvent {
            how: How::ArmPropagate,
            type_name: None,
            type_truncated: false,
            msg: None,
            msg_truncated: false,
            loc: "a.rs:1".to_owned(),
            chain: &chain,
        });
        assert_eq!(v["exc"]["type"], json!("Err"));
        assert_eq!(v["exc"]["unread"], json!(["type", "msg"]));
    }

    /// The chain's own origin, not a constant: a HANDLED that continues no
    /// chain says the `Err` was made somewhere this recording never saw.
    #[test]
    fn a_chain_born_outside_instrumented_code_says_so_in_its_payload() {
        let mut chain = chain_event();
        chain.origin = Origin::Outside;
        let v = payload(&ErrFlowEvent {
            how: How::SinkLetUnderscore,
            type_name: Some("io::Error"),
            type_truncated: false,
            msg: Some("ENOENT"),
            msg_truncated: false,
            loc: "a.rs:1".to_owned(),
            chain: &chain,
        });
        assert_eq!(v["chain"]["origin"], json!("outside"));
        assert_eq!(v["how"], json!("sink_let_underscore"));
    }

    #[test]
    fn a_truncated_type_and_message_are_both_flagged() {
        let chain = chain_event();
        let v = payload(&ErrFlowEvent {
            how: How::Try,
            type_name: Some("Loooong"),
            type_truncated: true,
            msg: Some("cut"),
            msg_truncated: true,
            loc: "a.rs:1".to_owned(),
            chain: &chain,
        });
        assert_eq!(v["exc"]["trunc"], json!(true));
        assert_eq!(v["exc"]["type_trunc"], json!(true));
    }

    /// The terminal is written only where the machine put one: on the chain's
    /// last event.
    #[test]
    fn a_chains_terminal_rides_the_event_the_machine_marked() {
        let mut chain = chain_event();
        chain.terminal = Some(chains::Terminal::SwallowedCandidate);
        let v = payload(&ErrFlowEvent {
            how: How::SinkOk,
            type_name: Some("E"),
            type_truncated: false,
            msg: Some("x"),
            msg_truncated: false,
            loc: "a.rs:1".to_owned(),
            chain: &chain,
        });
        assert_eq!(v["chain"]["terminal"], json!("swallowed_candidate"));
    }

    #[test]
    fn a_unit_frames_wire_outcome_zero_is_the_ok_close_it_made() {
        assert_eq!(outcome_of(0, false, Some(RetKind::Unit)), Outcome::Ok);
        assert_eq!(outcome_of(0, false, Some(RetKind::Value)), Outcome::None);
        assert_eq!(outcome_of(0, false, None), Outcome::None);
    }

    /// A v2 `err` RETURN has no type block, so it is no chain's birth: it moves
    /// a chain up to the caller exactly as a `none` does.
    #[test]
    fn an_untyped_err_close_is_read_as_a_none_close() {
        assert_eq!(outcome_of(2, false, Some(RetKind::Value)), Outcome::None);
        assert_eq!(outcome_of(2, true, Some(RetKind::Value)), Outcome::Err);
    }

    /// The exit probe reads the whole `Result`; every err-flow probe reads the
    /// `Err`'s payload. Unwrapping the one into the other is what makes a chain
    /// recognisable across the frame boundary it was born at.
    #[test]
    fn the_error_debug_is_unwrapped_out_of_the_results_own_rendering() {
        assert_eq!(
            unwrap_err_debug("Err(Os { code: 2 })"),
            Some("Os { code: 2 }")
        );
        assert_eq!(unwrap_err_debug("Ok(())"), None);
        assert_eq!(
            unwrap_err_debug("Err(x"),
            None,
            "a cut rendering is not one"
        );
    }

    /// Display is the other half of the same rule: identity refuses a cut
    /// rendering (above), and `exc.msg` still shows the error's own text out of
    /// it -- so `msg` means the same thing on every event, truncated or not.
    #[test]
    fn a_cut_rendering_still_loses_the_results_wrapper_when_it_is_displayed() {
        assert_eq!(err_debug_text("Err(Os { code: 2 })"), "Os { code: 2 }");
        assert_eq!(err_debug_text("Err(Os { code: 2"), "Os { code: 2");
        assert_eq!(err_debug_text("Ok(())"), "Ok(())", "not an Err rendering");
        assert_eq!(err_debug_text(""), "");
    }

    fn ret_payload(tag: u8, truncated: bool, text: &str) -> spool::ReturnPayload {
        spool::ReturnPayload {
            tag,
            truncated,
            text: text.to_owned(),
            err_type: None,
            err_type_truncated: false,
        }
    }

    /// A cut text is a prefix of an identity, not one: two sites cutting at
    /// different lengths would split one chain in two.
    #[test]
    fn a_cut_or_unread_error_text_is_no_identity_at_all() {
        assert_eq!(
            err_debug(&ret_payload(spool::TAG_DEBUG, false, "Err(E)")),
            Some("E".to_owned())
        );
        assert_eq!(
            err_debug(&ret_payload(spool::TAG_DEBUG, true, "Err(E)")),
            None
        );
        assert_eq!(err_debug(&ret_payload(spool::TAG_UNREAD, false, "")), None);
        assert_eq!(
            err_debug(&ret_payload(spool::TAG_NO_VALUE, false, "")),
            None
        );
    }
}
