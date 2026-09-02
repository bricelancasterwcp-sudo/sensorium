//! THROWAWAY SPIKE CODE. Thread serials and the global sequence.

mod common;

use std::collections::BTreeSet;

/// Serial 1 belongs to the main thread even when a spawned thread emits first.
#[test]
fn serial_one_is_the_main_thread_even_when_a_spawned_thread_emits_first() {
    let (dir, _run) = common::run_recording("spawn-first");
    let spools = dir.spools();
    assert_eq!(spools.len(), 2, "one spool per emitting thread: {spools:?}");

    let main = dir.spool(1);
    assert_eq!(
        main.name, "main",
        "serial 1 must be the main thread, not the thread that emitted first"
    );
    let worker = dir.spool(2);
    assert_eq!(worker.name, "wörker-✓");

    // The proof that this is not an accident of ordering: the worker emitted
    // and finished BEFORE main's first event, so the worker's records carry
    // lower sequence numbers than main's -- yet main still holds serial 1.
    let worker_max = worker.records.iter().map(|r| r.seq).max().expect("worker records");
    let main_first_call = main
        .records
        .first()
        .expect("main records")
        .seq;
    assert!(
        worker_max < main_first_call,
        "the scenario must have the worker emit first: worker max seq {worker_max}, \
         main's first seq {main_first_call}"
    );
}

/// Serial 1 stays reserved for the main thread even when the main thread never
/// emits at all: the first spawned thread takes 2, not 1.
#[test]
fn serial_one_stays_reserved_when_the_main_thread_never_emits() {
    let (dir, _run) = common::run_recording("clean-thread");
    let spools = dir.spools();
    assert_eq!(
        spools.len(),
        1,
        "only the worker emits, so only one spool exists: {spools:?}"
    );
    assert_eq!(
        spools[0].serial, 2,
        "the first non-main thread mints 2; 1 is the main thread's whether it emits or not"
    );
    assert_eq!(spools[0].name, "worker");
}

/// Sequence numbers are unique and strictly increasing across two threads'
/// merged records, and strictly increasing within each thread's own spool.
#[test]
fn sequence_numbers_are_strictly_increasing_across_two_threads() {
    let (dir, _run) = common::run_recording("two-threads");
    let spools = dir.spools();
    assert_eq!(spools.len(), 2, "two emitting threads: {spools:?}");

    let mut all: Vec<u64> = Vec::new();
    for spool in &spools {
        assert!(
            spool.records.len() > 100,
            "the scenario must produce enough records to interleave: {}",
            spool.records.len()
        );
        let mut previous: Option<u64> = None;
        for r in &spool.records {
            if let Some(p) = previous {
                assert!(
                    r.seq > p,
                    "sequence went backwards inside {}: {} after {p}",
                    spool.path.display(),
                    r.seq
                );
            }
            previous = Some(r.seq);
            all.push(r.seq);
        }
    }

    let unique: BTreeSet<u64> = all.iter().copied().collect();
    assert_eq!(
        unique.len(),
        all.len(),
        "two threads shared a sequence number: {} records, {} distinct",
        all.len(),
        unique.len()
    );

    let merged: Vec<u64> = unique.into_iter().collect();
    for w in merged.windows(2) {
        assert!(w[1] > w[0], "merged sequence is not strictly increasing");
    }
    assert_eq!(
        merged[0], 0,
        "the global sequence starts at 0 for the process's first record"
    );
    assert_eq!(
        *merged.last().unwrap(),
        merged.len() as u64 - 1,
        "one fetch_add per record leaves no gaps: {} records spanning 0..={}",
        merged.len(),
        merged.last().unwrap()
    );
}
