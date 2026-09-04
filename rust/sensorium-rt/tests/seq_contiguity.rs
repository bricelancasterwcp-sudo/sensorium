//! A refused record consumes no sequence number (`rust/HONESTY.md` §4).
//!
//! The property, stated over a whole process because the counter is
//! process-global and the only thing one thread can promise is that its own
//! seqs ascend: **the union of the seqs every spool of a process WROTE is
//! `0..=max` with nothing missing.** The number is minted inside
//! `Spool::record`, after the record is known writable, so a record the spool
//! refused takes no number with it -- which is what makes `records_dropped`
//! (witnessed by the writer) and `seq_gaps` (inferred by the converter's merge)
//! disjoint rather than overlapping, and what bounds `seq_gaps` at one lost
//! mid-write per thread.
//!
//! **Why a test binary of its own, and why this scenario.** Forcing a refusal
//! needs `SENSORIUM_TEST_SPOOL_LIMIT`, which exists only under `test-hooks`;
//! and the assertion has to run against a CHILD process, because in-process it
//! would be reading a counter that every other test in the binary is also
//! minting from. The scenario must be MULTI-THREADED to have any content: on a
//! single thread the spool breaks and stays broken, so every refusal falls
//! after that thread's last write and `0..=max` is contiguous however the seq
//! is minted (measured: with the seq minted before the check -- the defect this
//! pins -- `spool-limit 6000` still reads 0 gaps, while `two-threads 3000`
//! reads 1282). Only refusals on one spool INTERLEAVED with writes on another
//! leave an interior hole, so that interleaving is asserted as a precondition
//! below rather than assumed: if it ever degenerates this test goes red, not
//! vacuously green.
#![cfg(feature = "test-hooks")]

mod common;

use common::{Spec, SpoolFile, TempDir};

/// Small enough that both threads' spools break well before their loops end.
const LIMIT: u64 = 65_536;
/// Enough iterations that each thread writes ~2600 records and refuses ~1700.
const PER_THREAD: u32 = 3_000;

fn max_seq(s: &SpoolFile) -> Option<u64> {
    s.records.iter().map(|r| r.seq).max()
}

#[test]
fn a_refused_record_consumes_no_sequence_number() {
    assert_contiguous("two-threads", PER_THREAD, "seq-contiguity");
}

/// The same property with kinds 4 and 5 in the stream. The seq is minted inside
/// `Spool::record`, which every kind goes through -- so an err record refused by
/// a broken spool must take no number with it either, and this is what says so.
#[test]
fn a_refused_err_record_consumes_no_sequence_number() {
    assert_contiguous("errflow-two-threads", PER_THREAD, "seq-contiguity-errflow");
}

fn assert_contiguous(scenario: &str, per_thread: u32, label: &str) {
    let dir = TempDir::reserved(label);
    let run = Spec::new(scenario)
        .arg(&per_thread.to_string())
        .spool(dir.path())
        .env("SENSORIUM_TEST_SPOOL_LIMIT", LIMIT.to_string())
        .run();
    assert_eq!(run.says_u64("per_thread"), u64::from(per_thread));

    let spools = dir.spools();
    assert_eq!(
        spools.len(),
        2,
        "main and the worker each emit; found serials {:?}",
        spools.iter().map(|s| s.serial).collect::<Vec<_>>()
    );

    // Precondition 1: the limit bit, so there are refusals to account for.
    let dropped: u64 = spools.iter().map(|s| s.records_dropped).sum();
    assert!(
        dropped > 0,
        "no record was refused in this run, so contiguity pins nothing"
    );

    // Precondition 2: at least one record was WRITTEN somewhere after a record
    // was REFUSED somewhere -- i.e. a spool that dropped records is not the one
    // holding the highest seq. Without this the refusals are all past the last
    // write and the property below is vacuous.
    let overall_max = spools
        .iter()
        .filter_map(max_seq)
        .max()
        .expect("the process wrote records");
    assert!(
        spools
            .iter()
            .any(|s| s.records_dropped > 0 && max_seq(s) < Some(overall_max)),
        "every refusal fell after the last write, so nothing here would notice a \
         refused record taking a number; spools: {:?}",
        spools
            .iter()
            .map(|s| (s.serial, s.records.len(), s.records_dropped, max_seq(s)))
            .collect::<Vec<_>>()
    );

    // The property.
    let mut seqs: Vec<u64> = spools
        .iter()
        .flat_map(|s| s.records.iter().map(|r| r.seq))
        .collect();
    seqs.sort_unstable();
    assert_eq!(
        seqs.len() as u64,
        overall_max + 1,
        "{} seqs written across {} spools with a maximum of {overall_max}: \
         {dropped} refused record(s) took numbers with them",
        seqs.len(),
        spools.len()
    );
    for (i, &seq) in seqs.iter().enumerate() {
        assert_eq!(
            seq, i as u64,
            "the written sequence is not 0..={overall_max}: a hole at {i}"
        );
    }
}
