//! Seeded bug: the ingest worker fails, its `Err` goes into the
//! `JoinHandle`, and the parent turns it into a plausible zero.
//!
//! Two verdicts, one error, and the split is the point. In the CHILD the
//! chain leaves the thread's outermost frame: whether anybody ever read the
//! handle is not something the child's own recording knows, so that end is
//! ambiguous. In the PARENT the value is absorbed by a sink in a frame that
//! then returned normally, which is a swallow.

use std::thread;

fn ingest(rows: u32) -> Result<u32, String> {
    Err(format!("ingest refused {rows} rows"))
}

fn worker(rows: u32) -> Result<u32, String> {
    let n = ingest(rows)?;
    Ok(n)
}

fn collect() -> u32 {
    let handle = thread::spawn(|| worker(9));
    match handle.join() {
        // BUG: a worker that failed and a worker that ingested nothing are
        // the same number here.
        Ok(result) => result.unwrap_or(0),
        Err(_) => 0,
    }
}

fn main() {
    println!("ingested: {}", collect());
}
