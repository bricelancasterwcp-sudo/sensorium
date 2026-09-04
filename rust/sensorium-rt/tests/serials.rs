//! Thread serials and the process-global sequence.

mod common;

use common::{Spec, TempDir, KIND_CALL};

#[test]
fn main_is_serial_one_even_when_a_spawned_thread_emits_first() {
    let dir = TempDir::reserved("serials-spawnfirst");
    Spec::new("spawn-first").spool(dir.path()).run();
    let spools = dir.spools();
    assert_eq!(spools.len(), 2);

    let main = dir.spool(1);
    assert_eq!(main.name, "main");
    assert_eq!(
        main.of_kind(KIND_CALL)[0].site_index(),
        51,
        "serial 1 is the main thread's, whatever emitted first"
    );

    let worker = dir.spool(2);
    assert_eq!(
        worker.name, "wörker-✓",
        "the header carries the thread name as UTF-8"
    );
    assert_eq!(worker.of_kind(KIND_CALL)[0].site_index(), 50);
    assert!(
        worker.records[0].seq < main.records[0].seq,
        "the worker really did emit first: worker seq {} vs main seq {}",
        worker.records[0].seq,
        main.records[0].seq
    );
}

#[test]
fn two_threads_share_one_gapless_strictly_increasing_sequence() {
    const PER_THREAD: u64 = 400;
    let dir = TempDir::reserved("serials-two");
    let run = Spec::new("two-threads")
        .arg(&PER_THREAD.to_string())
        .spool(dir.path())
        .run();
    assert_eq!(run.says_u64("per_thread"), PER_THREAD);

    let spools = dir.spools();
    assert_eq!(spools.len(), 2);
    let mut seqs: Vec<u64> = spools
        .iter()
        .flat_map(|s| s.records.iter().map(|r| r.seq))
        .collect();
    let total = seqs.len() as u64;
    // 2 threads x PER_THREAD frames x (CALL + RETURN), plus one THREAD_END each.
    assert_eq!(total, 2 * PER_THREAD * 2 + 2);
    seqs.sort_unstable();
    assert!(
        seqs.windows(2).all(|w| w[0] < w[1]),
        "sequence numbers are unique across threads"
    );
    assert_eq!(
        seqs,
        (0..total).collect::<Vec<u64>>(),
        "one fetch_add per record and nothing dropped means no holes"
    );
    for s in &spools {
        assert!(
            s.records.windows(2).all(|w| w[0].seq < w[1].seq),
            "within one thread the sequence is also increasing"
        );
        assert!(s.has_thread_end());
    }
}

#[test]
fn threads_that_come_and_go_each_get_their_own_serial() {
    const THREADS: u32 = 8;
    let dir = TempDir::reserved("serials-sequential");
    let run = Spec::new("sequential-threads")
        .arg(&THREADS.to_string())
        .spool(dir.path())
        .run();
    assert_eq!(run.says_u64("threads"), u64::from(THREADS));

    let spools = dir.spools();
    assert_eq!(
        spools.len(),
        THREADS as usize,
        "the main thread emitted nothing, so it has no spool"
    );
    let serials: Vec<u32> = spools.iter().map(|s| s.serial).collect();
    assert_eq!(
        serials,
        (2..2 + THREADS).collect::<Vec<u32>>(),
        "serials are minted from 2 up and never reused, however the OS recycles thread ids"
    );
    let mut names: Vec<&str> = spools.iter().map(|s| s.name.as_str()).collect();
    names.sort_unstable();
    let mut expected: Vec<String> = (0..THREADS).map(|i| format!("seq-{i}")).collect();
    expected.sort_unstable();
    assert_eq!(
        names,
        expected.iter().map(String::as_str).collect::<Vec<_>>()
    );
}
