//! Park one async frame across polls.
//!
//! Wire kind 7 (SUSPEND) pops the open frame and remembers it by async id.
//! Kind 8 (RESUME) pushes that same frame onto the thread that polled it,
//! which may be a different worker. The SQLite rows are YIELD and RESUME.
//! Neither updates a fingerprint: a poll is not a new call, and folding the
//! polls is the point of parking the frame instead of leaving it open.

use std::collections::HashMap;

use serde_json::json;

use super::frames::{OpenFrame, MAIN_SERIAL};
use super::spool::RawRecord;
use super::sqlite::TraceWriter;

/// One arm in the converter: kind 7 parks, kind 8 restores.
pub(crate) fn apply(
    writer: &TraceWriter,
    pid: u32,
    thread_id: u32,
    r: &RawRecord,
    stacks: &mut HashMap<u32, Vec<OpenFrame>>,
    parked: &mut HashMap<u64, OpenFrame>,
) -> Result<usize, String> {
    if r.kind == super::spool::KIND_SUSPEND {
        on_suspend(writer, pid, thread_id, r, stacks, parked)
    } else {
        on_resume(writer, pid, thread_id, r, stacks, parked)
    }
}

pub(crate) fn on_suspend(
    writer: &TraceWriter,
    pid: u32,
    thread_id: u32,
    r: &RawRecord,
    stacks: &mut HashMap<u32, Vec<OpenFrame>>,
    parked: &mut HashMap<u64, OpenFrame>,
) -> Result<usize, String> {
    let async_id = async_id(pid, thread_id, r, "SUSPEND")?;
    if parked.contains_key(&async_id) {
        return Err(format!(
            "pid {pid} thread {thread_id} seq {}: SUSPEND async id {async_id} is already parked",
            r.seq
        ));
    }
    let top = stacks
        .get_mut(&thread_id)
        .and_then(Vec::pop)
        .ok_or_else(|| {
            format!(
                "pid {pid} thread {thread_id} seq {}: SUSPEND with no open frame on this thread",
                r.seq
            )
        })?;
    let payload = json!({"async_id": async_id});
    writer.insert_event(
        r.ts_ns,
        thread_id,
        "YIELD",
        Some(top.frame_id),
        Some(top.code_id),
        None,
        Some(&payload),
        task_id(thread_id),
    )?;
    parked.insert(async_id, top);
    Ok(1)
}

pub(crate) fn on_resume(
    writer: &TraceWriter,
    pid: u32,
    thread_id: u32,
    r: &RawRecord,
    stacks: &mut HashMap<u32, Vec<OpenFrame>>,
    parked: &mut HashMap<u64, OpenFrame>,
) -> Result<usize, String> {
    let async_id = async_id(pid, thread_id, r, "RESUME")?;
    let frame = parked.remove(&async_id).ok_or_else(|| {
        format!(
            "pid {pid} thread {thread_id} seq {}: RESUME for async id {async_id}, which is not \
             parked",
            r.seq
        )
    })?;
    let payload = json!({"async_id": async_id});
    writer.insert_event(
        r.ts_ns,
        thread_id,
        "RESUME",
        Some(frame.frame_id),
        Some(frame.code_id),
        None,
        Some(&payload),
        task_id(thread_id),
    )?;
    stacks.entry(thread_id).or_default().push(frame);
    Ok(1)
}

fn task_id(thread_id: u32) -> Option<u32> {
    (thread_id != MAIN_SERIAL).then_some(thread_id)
}

fn async_id(pid: u32, thread_id: u32, r: &RawRecord, what: &str) -> Result<u64, String> {
    let bytes: [u8; 8] = r.payload.as_slice().try_into().map_err(|_| {
        format!(
            "pid {pid} thread {thread_id} seq {}: {what} payload is {} bytes, not the 8-byte \
             async id",
            r.seq,
            r.payload.len()
        )
    })?;
    Ok(u64::from_le_bytes(bytes))
}
