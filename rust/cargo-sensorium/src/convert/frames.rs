//! Walking one process's merged record stream: frame stacks, the pending-panic
//! state machine, and the fingerprint accumulation that falls out of writing
//! the same causal events to SQLite.
//!
//! `rust/HONESTY.md` §1 is this module's contract for what an outcome means
//! and how a panic is attached to the frame it unwound; TRACE-FORMAT.md §3
//! and §6 are the schema it writes to.

use std::collections::{BTreeMap, HashMap};

use serde_json::{json, Map, Value};

use crate::convert::errflow::{self, ErrFlowEvent, IndexInput};
use crate::convert::fingerprint::Fingerprint;
use crate::convert::manifest::{Manifest, RetKind, SiteInfo, SiteKind};
use crate::convert::merge::MergeResult;
use crate::convert::spool::{
    self, How, ProcHeader, KIND_CALL, KIND_HANDLED, KIND_PANIC, KIND_RAISE, KIND_RETURN,
    KIND_THREAD_END, TAG_DEBUG, TAG_NO_VALUE, TAG_UNREAD,
};
use crate::convert::sqlite::TraceWriter;

const MAIN_SERIAL: u32 = 1;

struct OpenFrame {
    frame_id: i64,
    code_id: i64,
    rel_file: String,
    qualname: String,
    /// The frame's own line, for the `loc` of an `Err` that left it.
    line: u32,
    /// `None` on a manifest row that declared no `ret` at all. A frame that
    /// never said what it returns is not one this converter may read a `()`
    /// into (`rust/HONESTY.md` §1's none-versus-zero discipline).
    ret: Option<RetKind>,
}

struct PendingPanic {
    msg: String,
    loc: String,
    serial: u64,
}

/// What the walk learned, beyond the rows it wrote.
pub struct ProcessResult {
    pub events_written: usize,
    pub panics_unrecorded: u64,
    pub panics_outside_frames: u64,
    /// RAISE and HANDLED RECORDS met on the wire -- including the ones no
    /// event was written for. The synthesised origin RAISE of a frame that
    /// closed `err` is not one of these: it is the converter's, not the
    /// runtime's, and counting it here would report a record that was never
    /// written.
    pub err_flow_raise: u64,
    pub err_flow_handled: u64,
    /// Err-flow records whose thread had no open frame: a `?` inside a skipped
    /// `async fn`, or a site whose enclosing CALL was refused. Counted, and
    /// written as no event -- the `panics_outside_frames` precedent.
    pub err_flow_outside_frames: u64,
    /// Frames opened at a `closure` site (design R5).
    pub closure_frames: u64,
    /// Serials that saw a `THREAD_END` record.
    pub ended_threads: std::collections::BTreeSet<u32>,
}

/// One process's record stream and everything needed to read it.
pub struct Walk<'a> {
    pub merged: &'a MergeResult,
    pub proc: &'a ProcHeader,
    pub manifests: &'a BTreeMap<String, Manifest>,
    pub workspace_root: &'a str,
    pub pid: u32,
    pub names: &'a BTreeMap<u32, String>,
    /// Thread serial -> the wire version of that thread's spool file.
    pub versions: &'a BTreeMap<u32, u8>,
}

/// Consume `merged` against `proc`'s registered units and `manifests`, writing
/// every `code_objects`/`frames`/`events` row and every fingerprint through
/// `writer`.
///
/// `pid` is used only for error text (`RETURN with no open frame`, per the
/// brief, names pid/serial/seq). `versions` is each thread's wire version,
/// which is what says whether an `err` RETURN carries the error type block.
///
/// # Errors
/// A site referencing an unregistered unit or an unknown site index, a
/// RETURN with no open frame on its thread, a CALL/RETURN naming a site the
/// manifest says is not a frame (or an err-flow record naming one it says is),
/// a malformed RETURN, PANIC or err-flow payload, an err-flow `how` byte no
/// runtime writes, or a wire outcome byte outside `0..=3`.
#[allow(clippy::too_many_lines)]
pub fn process(writer: &TraceWriter, w: &Walk) -> Result<ProcessResult, String> {
    let Walk {
        merged,
        proc,
        manifests,
        workspace_root,
        pid,
        names,
        versions,
    } = *w;
    let unit_by_id: HashMap<u8, &str> = proc
        .units
        .iter()
        .filter_map(|(k, v)| k.parse::<u8>().ok().map(|id| (id, v.as_str())))
        .collect();
    let site_lookup: HashMap<&str, BTreeMap<u32, SiteInfo>> = manifests
        .iter()
        .map(|(k, v)| (k.as_str(), v.sites_by_index()))
        .collect();
    // Chain identity is minted over the WHOLE stream first, because how a chain
    // ended is a fact about a later record than the events that carry it.
    let chains = errflow::build_index(&IndexInput {
        merged,
        unit_by_id: &unit_by_id,
        site_lookup: &site_lookup,
        versions,
        main_serial: MAIN_SERIAL,
    });

    let mut stacks: HashMap<u32, Vec<OpenFrame>> = HashMap::new();
    let mut pending_panic: HashMap<u32, PendingPanic> = HashMap::new();
    let mut panic_serial: HashMap<u32, u64> = HashMap::new();
    let mut code_intern: HashMap<(String, String, u32), i64> = HashMap::new();
    let mut main_fp = Fingerprint::new();
    let mut task_fp: HashMap<u32, Fingerprint> = HashMap::new();
    let mut ended_threads = std::collections::BTreeSet::new();
    let mut events_written = 0usize;
    let mut panics_unrecorded = 0u64;
    let mut panics_outside_frames = 0u64;
    let mut err_flow_raise = 0u64;
    let mut err_flow_handled = 0u64;
    let mut err_flow_outside_frames = 0u64;
    let mut closure_frames = 0u64;

    for m in &merged.records {
        let thread_id = m.thread_serial;
        let r = &m.record;
        match r.kind {
            KIND_CALL => {
                let label = format!("pid {pid} thread {thread_id} seq {}", r.seq);
                let site = resolve_site(&unit_by_id, &site_lookup, pid, &label, "CALL", r.site)?;
                site.require_frame(&label)?;
                if site.kind == SiteKind::Closure {
                    closure_frames += 1;
                }
                let abs_file = std::path::Path::new(workspace_root)
                    .join(&site.file)
                    .to_string_lossy()
                    .into_owned();
                let key = (abs_file.clone(), site.qualname.clone(), site.line);
                let code_id = match code_intern.get(&key) {
                    Some(id) => *id,
                    None => {
                        let id = writer.insert_code_object(&abs_file, &site.qualname, site.line)?;
                        code_intern.insert(key, id);
                        id
                    }
                };
                let task_id = (thread_id != MAIN_SERIAL).then_some(thread_id);
                let payload = json!({"args": {}, "unread": ["locals"]});
                let event_id = writer.insert_event(
                    r.ts_ns,
                    thread_id,
                    "CALL",
                    None,
                    Some(code_id),
                    Some(site.line),
                    Some(&payload),
                    task_id,
                )?;
                events_written += 1;
                let stack = stacks.entry(thread_id).or_default();
                let (parent_id, depth) = match stack.last() {
                    Some(top) => (Some(top.frame_id), stack_depth(stack)),
                    None => (None, 0),
                };
                let frame_id =
                    writer.insert_frame(parent_id, code_id, event_id, depth, thread_id)?;
                fp_for(&mut main_fp, &mut task_fp, thread_id).update(
                    &site.file,
                    &site.qualname,
                    "CALL",
                );
                stacks.entry(thread_id).or_default().push(OpenFrame {
                    frame_id,
                    code_id,
                    rel_file: site.file.clone(),
                    qualname: site.qualname.clone(),
                    line: site.line,
                    ret: site.ret,
                });
            }
            KIND_RETURN => {
                let top = stacks
                    .get_mut(&thread_id)
                    .and_then(Vec::pop)
                    .ok_or_else(|| {
                        format!(
                            "pid {pid} thread {thread_id} seq {}: RETURN with no open frame on this \
                             thread",
                            r.seq
                        )
                    })?;
                let label = format!("pid {pid} thread {thread_id} seq {}", r.seq);
                // The error type block rides an `err` RETURN, and only on a v3
                // spool: a v2 one's `err` payload ends after its text, and
                // reading three more bytes out of it would invent a type.
                let err_type_block =
                    r.outcome == 2 && versions.get(&thread_id).copied().unwrap_or(3) >= 3;
                let payload = spool::parse_return_payload(&label, &r.payload, err_type_block)?;
                let is_panic = r.outcome == 3;
                let task_id = (thread_id != MAIN_SERIAL).then_some(thread_id);

                let mut obj = Map::new();
                let unwind_exc = if is_panic {
                    obj.insert("outcome".to_owned(), json!("panic"));
                    // `kind` on every `exc` object, panics included (design
                    // R7): the Rust index selects a chain by it, and a rule
                    // that instead read `type == "panic"` would misread a
                    // workspace error type that happens to be spelled that way.
                    Some(match pending_panic.get(&thread_id) {
                        Some(p) => {
                            json!({"kind": "panic", "type": "panic", "msg": p.msg,
                                   "serial": p.serial, "loc": p.loc})
                        }
                        None => {
                            panics_unrecorded += 1;
                            json!({
                                "kind": "panic",
                                "type": "panic",
                                "msg": "<panic message not recorded: no PANIC record preceded this unwind>",
                                "serial": 0
                            })
                        }
                    })
                } else {
                    pending_panic.remove(&thread_id);
                    // The wire carries no per-site knowledge (`rust/HONESTY.md`
                    // §1): a `ret: unit` site whose exits are never wrapped
                    // always reads wire outcome 0 when it did not panic, and
                    // the manifest is what tells this apart from a `none` that
                    // really means "nothing was probed".
                    let is_unit_none = r.outcome == 0 && top.ret == Some(RetKind::Unit);
                    let outcome_str = match r.outcome {
                        0 if is_unit_none => "ok",
                        0 => "none",
                        1 => "ok",
                        2 => "err",
                        other => {
                            return Err(format!(
                                "{label}: RETURN outcome byte {other} is not 0..=3"
                            ))
                        }
                    };
                    obj.insert("outcome".to_owned(), json!(outcome_str));
                    if is_unit_none {
                        obj.insert("value".to_owned(), json!({"k": "dbg", "v": "()"}));
                    } else {
                        match payload.tag {
                            TAG_NO_VALUE => {}
                            TAG_DEBUG => {
                                obj.insert(
                                    "value".to_owned(),
                                    json!({"k": "dbg", "v": payload.text, "trunc": payload.truncated}),
                                );
                            }
                            TAG_UNREAD => {
                                obj.insert("value".to_owned(), json!({"k": "unread"}));
                            }
                            other => {
                                return Err(format!(
                                    "{label}: RETURN payload tag {other} is not 0..=2"
                                ))
                            }
                        }
                    }
                    None
                };
                // The origin RAISE of a chain born by RETURNING an `Err`
                // (design R1/§2a row 2), written in front of the RETURN so the
                // chain has a record of its own to be reported at. `how: exit`
                // is the converter's, and no runtime may write it.
                if let Some(chain) = chains.at_exit(thread_id, r.seq) {
                    let msg =
                        (payload.tag == TAG_DEBUG).then(|| errflow::err_debug_text(&payload.text));
                    let exc = errflow::payload(&ErrFlowEvent {
                        how: How::Exit,
                        type_name: payload.err_type.as_deref(),
                        type_truncated: payload.err_type_truncated,
                        msg,
                        msg_truncated: payload.truncated,
                        loc: format!("{}:{}", top.rel_file, top.line),
                        chain,
                    });
                    writer.insert_event(
                        r.ts_ns,
                        thread_id,
                        "RAISE",
                        Some(top.frame_id),
                        Some(top.code_id),
                        Some(top.line),
                        Some(&exc),
                        task_id,
                    )?;
                    events_written += 1;
                    fp_for(&mut main_fp, &mut task_fp, thread_id).update(
                        &top.rel_file,
                        &top.qualname,
                        "RAISE",
                    );
                }
                let closed_by = if is_panic { "unwind" } else { "return" };
                let payload_value = Value::Object(obj);
                let event_id = writer.insert_event(
                    r.ts_ns,
                    thread_id,
                    "RETURN",
                    Some(top.frame_id),
                    Some(top.code_id),
                    None,
                    Some(&payload_value),
                    task_id,
                )?;
                events_written += 1;
                writer.close_frame(top.frame_id, event_id, closed_by, unwind_exc.as_ref())?;
                fp_for(&mut main_fp, &mut task_fp, thread_id).update(
                    &top.rel_file,
                    &top.qualname,
                    "RETURN",
                );
            }
            KIND_PANIC => {
                let label = format!("pid {pid} thread {thread_id} seq {}", r.seq);
                let payload = spool::parse_panic_payload(&label, &r.payload)?;
                let serial = panic_serial.entry(thread_id).or_insert(0);
                *serial += 1;
                let this_serial = *serial;
                let has_frame = stacks.get(&thread_id).is_some_and(|s| !s.is_empty());
                if has_frame {
                    let stack = stacks.get(&thread_id).expect("checked above");
                    let top = stack.last().expect("checked above");
                    let line = split_loc(&payload.loc)
                        .and_then(|(file, line)| (file == top.rel_file).then_some(line));
                    let task_id = (thread_id != MAIN_SERIAL).then_some(thread_id);
                    let payload_value = json!({
                        "exc": {"kind": "panic", "type": "panic", "msg": payload.msg,
                                "serial": this_serial},
                        "loc": payload.loc,
                    });
                    writer.insert_event(
                        r.ts_ns,
                        thread_id,
                        "RAISE",
                        Some(top.frame_id),
                        Some(top.code_id),
                        line,
                        Some(&payload_value),
                        task_id,
                    )?;
                    events_written += 1;
                    let (rel_file, qualname) = (top.rel_file.clone(), top.qualname.clone());
                    fp_for(&mut main_fp, &mut task_fp, thread_id)
                        .update(&rel_file, &qualname, "RAISE");
                    pending_panic.insert(
                        thread_id,
                        PendingPanic {
                            msg: payload.msg,
                            loc: payload.loc,
                            serial: this_serial,
                        },
                    );
                } else {
                    panics_outside_frames += 1;
                }
            }
            KIND_RAISE | KIND_HANDLED => {
                let label = format!("pid {pid} thread {thread_id} seq {}", r.seq);
                let kind_name = if r.kind == KIND_RAISE {
                    err_flow_raise += 1;
                    "RAISE"
                } else {
                    err_flow_handled += 1;
                    "HANDLED"
                };
                let site = resolve_site(&unit_by_id, &site_lookup, pid, &label, kind_name, r.site)?;
                let how = spool::parse_how(&label, r.kind, r.outcome)?;
                site.require_err_flow(&label, how)?;
                let seen = spool::parse_errflow_payload(&label, &r.payload)?;
                // No open frame, no event: a `?` inside a skipped `async fn`, or
                // a site whose enclosing CALL was refused, has nothing to be
                // reported against. Counted instead, the way a panic outside
                // every frame is.
                let Some(top) = stacks.get(&thread_id).and_then(|s| s.last()) else {
                    err_flow_outside_frames += 1;
                    continue;
                };
                let chain = chains.at_record(thread_id, r.seq).ok_or_else(|| {
                    format!("{label}: no chain was minted for this {kind_name} record")
                })?;
                let task_id = (thread_id != MAIN_SERIAL).then_some(thread_id);
                let value = errflow::payload(&ErrFlowEvent {
                    how,
                    type_name: seen.type_name.as_deref(),
                    type_truncated: seen.type_truncated,
                    msg: seen.msg.as_deref(),
                    msg_truncated: seen.msg_truncated,
                    loc: site.loc(),
                    chain,
                });
                writer.insert_event(
                    r.ts_ns,
                    thread_id,
                    kind_name,
                    Some(top.frame_id),
                    Some(top.code_id),
                    Some(site.line),
                    Some(&value),
                    task_id,
                )?;
                events_written += 1;
                let (rel_file, qualname) = (top.rel_file.clone(), top.qualname.clone());
                fp_for(&mut main_fp, &mut task_fp, thread_id)
                    .update(&rel_file, &qualname, kind_name);
            }
            KIND_THREAD_END => {
                ended_threads.insert(thread_id);
            }
            other => {
                return Err(format!(
                    "pid {pid} thread {thread_id} seq {}: unknown record kind {other}",
                    r.seq
                ))
            }
        }
    }

    let mut tasks: Vec<u32> = task_fp.keys().copied().collect();
    tasks.sort_unstable();
    for serial in tasks {
        let fp = task_fp.remove(&serial).expect("just listed");
        let (hash, n_events) = fp.finish();
        let name = names
            .get(&serial)
            .filter(|n| !n.is_empty())
            .map(String::as_str);
        writer.insert_task(serial, name, serial)?;
        writer.insert_task_fingerprint(serial, name, &hash, n_events)?;
    }
    let (hash, n_events) = main_fp.finish();
    writer.insert_fingerprint(MAIN_SERIAL, &hash, n_events)?;

    Ok(ProcessResult {
        events_written,
        panics_unrecorded,
        panics_outside_frames,
        err_flow_raise,
        err_flow_handled,
        err_flow_outside_frames,
        closure_frames,
        ended_threads,
    })
}

/// The manifest row a record's site word names.
///
/// # Errors
/// A unit id this process never registered, a unit with no manifest loaded, or
/// a site index the manifest does not hold -- each naming `what` (the record
/// kind) so the sentence says which record could not be resolved.
fn resolve_site<'a>(
    unit_by_id: &HashMap<u8, &str>,
    site_lookup: &'a HashMap<&str, BTreeMap<u32, SiteInfo>>,
    pid: u32,
    label: &str,
    what: &str,
    site_word: u32,
) -> Result<&'a SiteInfo, String> {
    let (unit_id, site_index) = spool::unpack_site(site_word);
    let metadata = *unit_by_id.get(&unit_id).ok_or_else(|| {
        format!("{label}: {what} references unit id {unit_id}, which this process never registered")
    })?;
    let sites = site_lookup
        .get(metadata)
        .ok_or_else(|| format!("pid {pid}: no manifest loaded for unit {metadata}"))?;
    sites
        .get(&site_index)
        .ok_or_else(|| format!("{label}: unit {metadata} has no site {site_index}"))
}

fn stack_depth(stack: &[OpenFrame]) -> u32 {
    u32::try_from(stack.len()).unwrap_or(u32::MAX)
}

fn fp_for<'a>(
    main: &'a mut Fingerprint,
    tasks: &'a mut HashMap<u32, Fingerprint>,
    thread_id: u32,
) -> &'a mut Fingerprint {
    if thread_id == MAIN_SERIAL {
        main
    } else {
        tasks.entry(thread_id).or_default()
    }
}

/// `"<file>:<line>:<col>"` -> `(file, line)`, from the right so a file path
/// with no colons (the ordinary case) is read whole.
fn split_loc(loc: &str) -> Option<(&str, u32)> {
    let mut parts = loc.rsplitn(3, ':');
    let _col = parts.next()?;
    let line: u32 = parts.next()?.parse().ok()?;
    let file = parts.next()?;
    Some((file, line))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_loc_reads_file_and_line_from_the_right() {
        assert_eq!(split_loc("a/b.rs:12:5"), Some(("a/b.rs", 12)));
        assert_eq!(split_loc("bad"), None);
    }

    #[test]
    fn split_loc_rejects_a_string_with_no_line_or_column() {
        assert_eq!(split_loc(""), None);
        assert_eq!(split_loc("only-a-file"), None);
    }
}
