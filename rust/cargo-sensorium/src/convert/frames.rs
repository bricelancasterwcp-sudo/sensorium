//! Walking one process's merged record stream: frame stacks, the pending-panic
//! state machine, and the fingerprint accumulation that falls out of writing
//! the same causal events to SQLite.
//!
//! `rust/HONESTY.md` §1 is this module's contract for what an outcome means
//! and how a panic is attached to the frame it unwound; TRACE-FORMAT.md §3
//! and §6 are the schema it writes to.

use std::collections::{BTreeMap, HashMap};

use serde_json::{json, Map, Value};

use crate::convert::fingerprint::Fingerprint;
use crate::convert::merge::MergeResult;
use crate::convert::spool::{
    self, Manifest, ProcHeader, RetKind, SiteInfo, KIND_CALL, KIND_PANIC, KIND_RETURN,
    KIND_THREAD_END, TAG_DEBUG, TAG_NO_VALUE, TAG_UNREAD,
};
use crate::convert::sqlite::TraceWriter;

const MAIN_SERIAL: u32 = 1;

struct OpenFrame {
    frame_id: i64,
    code_id: i64,
    rel_file: String,
    qualname: String,
    ret: RetKind,
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
    /// Serials that saw a `THREAD_END` record.
    pub ended_threads: std::collections::BTreeSet<u32>,
}

/// Consume `merged` against `proc`'s registered units and `manifests`, writing
/// every `code_objects`/`frames`/`events` row and every fingerprint through
/// `writer`.
///
/// `pid` is used only for error text (`RETURN with no open frame`, per the
/// brief, names pid/serial/seq).
///
/// # Errors
/// A site referencing an unregistered unit or an unknown site index, a
/// RETURN with no open frame on its thread, a malformed RETURN or PANIC
/// payload, or a wire outcome byte outside `0..=3`.
pub fn process(
    writer: &TraceWriter,
    merged: &MergeResult,
    proc: &ProcHeader,
    manifests: &BTreeMap<String, Manifest>,
    workspace_root: &str,
    pid: u32,
    names: &BTreeMap<u32, String>,
) -> Result<ProcessResult, String> {
    let unit_by_id: HashMap<u8, &str> = proc
        .units
        .iter()
        .filter_map(|(k, v)| k.parse::<u8>().ok().map(|id| (id, v.as_str())))
        .collect();
    let site_lookup: HashMap<&str, BTreeMap<u32, SiteInfo>> = manifests
        .iter()
        .map(|(k, v)| (k.as_str(), v.sites_by_index()))
        .collect();

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

    for m in &merged.records {
        let thread_id = m.thread_serial;
        let r = &m.record;
        match r.kind {
            KIND_CALL => {
                let (unit_id, site_index) = spool::unpack_site(r.site);
                let metadata = *unit_by_id.get(&unit_id).ok_or_else(|| {
                    format!(
                        "pid {pid} thread {thread_id} seq {}: CALL references unit id {unit_id}, \
                         which this process never registered",
                        r.seq
                    )
                })?;
                let sites = site_lookup
                    .get(metadata)
                    .ok_or_else(|| format!("pid {pid}: no manifest loaded for unit {metadata}"))?;
                let site = sites.get(&site_index).ok_or_else(|| {
                    format!(
                        "pid {pid} thread {thread_id} seq {}: unit {metadata} has no site {site_index}",
                        r.seq
                    )
                })?;
                let abs_file = std::path::Path::new(workspace_root)
                    .join(&site.file)
                    .to_string_lossy()
                    .into_owned();
                let key = (abs_file.clone(), site.qualname.clone(), site.firstlineno);
                let code_id = match code_intern.get(&key) {
                    Some(id) => *id,
                    None => {
                        let id = writer.insert_code_object(
                            &abs_file,
                            &site.qualname,
                            site.firstlineno,
                        )?;
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
                    Some(site.firstlineno),
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
                let payload = spool::parse_return_payload(&label, &r.payload)?;
                let is_panic = r.outcome == 3;
                let task_id = (thread_id != MAIN_SERIAL).then_some(thread_id);

                let mut obj = Map::new();
                let unwind_exc = if is_panic {
                    obj.insert("outcome".to_owned(), json!("panic"));
                    Some(match pending_panic.get(&thread_id) {
                        Some(p) => {
                            json!({"type": "panic", "msg": p.msg, "serial": p.serial, "loc": p.loc})
                        }
                        None => {
                            panics_unrecorded += 1;
                            json!({
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
                    let is_unit_none = r.outcome == 0 && top.ret == RetKind::Unit;
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
                        "exc": {"type": "panic", "msg": payload.msg, "serial": this_serial},
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
        ended_threads,
    })
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
