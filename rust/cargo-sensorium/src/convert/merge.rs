//! The k-way merge across one process's spool files, by `seq` -- the
//! process-global sequence every thread's records share -- and the gap count
//! that falls out of it (`rust/HONESTY.md` §4).
//!
//! `seq` is minted by one `AtomicU64` per process, so the true order of every
//! record this process wrote is simply "sorted by `seq`": no interleaving
//! heuristic is needed once the strictly-increasing-per-file invariant
//! (`spool::parse_spool_bytes`) has already ruled out corruption within one
//! file.

use crate::convert::spool::{RawRecord, SpoolFile};

/// One record, with the thread it came from attached.
#[derive(Debug)]
pub struct MergedRecord {
    pub thread_serial: u32,
    pub record: RawRecord,
}

#[derive(Debug)]
pub struct MergeResult {
    /// Every complete record from every spool, ascending by `seq`.
    pub records: Vec<MergedRecord>,
    /// `seq` values in `[0, max]` that no spool holds a complete record for --
    /// each one a record minted (`SEQ.fetch_add`) and never found, the
    /// one-per-thread crash bound counted rather than silently absorbed.
    ///
    /// A record the runtime REFUSED is not one of these: the number is minted
    /// inside `Spool::record`, after the record is known writable, so a
    /// witnessed drop takes no number with it and is counted once, by
    /// `records_dropped` alone (`rust/HONESTY.md` §4).
    pub seq_gaps: u64,
}

/// # Errors
/// Two records across different spools sharing (or reversing) the same `seq`
/// -- `SEQ` is one atomic per process, so two threads can never legitimately
/// mint the same value; seeing one is corruption, named by both threads'
/// serials.
pub fn merge(spools: Vec<SpoolFile>) -> Result<MergeResult, String> {
    let mut records: Vec<MergedRecord> = Vec::new();
    for spool in spools {
        let serial = spool.serial;
        for r in spool.records {
            records.push(MergedRecord {
                thread_serial: serial,
                record: r,
            });
        }
    }
    records.sort_by_key(|m| m.record.seq);

    for pair in records.windows(2) {
        let (a, b) = (&pair[0], &pair[1]);
        if a.record.seq == b.record.seq {
            return Err(format!(
                "seq {} appears in both thread {} and thread {}'s spool",
                a.record.seq, a.thread_serial, b.thread_serial
            ));
        }
    }

    let seq_gaps = match records.last() {
        None => 0,
        Some(last) => (last.record.seq + 1).saturating_sub(records.len() as u64),
    };

    Ok(MergeResult { records, seq_gaps })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spool(serial: u32, seqs: &[u64]) -> SpoolFile {
        SpoolFile {
            serial,
            name: String::new(),
            records_dropped: 0,
            truncated: 0,
            records: seqs
                .iter()
                .map(|&seq| RawRecord {
                    seq,
                    ts_ns: seq * 10,
                    site: 0,
                    kind: 1,
                    outcome: 0,
                    payload: vec![],
                })
                .collect(),
        }
    }

    #[test]
    fn a_complete_run_of_seqs_has_no_gaps() {
        let r = merge(vec![spool(1, &[0, 2, 4]), spool(2, &[1, 3])]).unwrap();
        assert_eq!(r.seq_gaps, 0);
        assert_eq!(
            r.records.iter().map(|m| m.record.seq).collect::<Vec<_>>(),
            vec![0, 1, 2, 3, 4]
        );
    }

    #[test]
    fn a_missing_seq_counts_as_one_gap() {
        // 0, 1, [2 missing], 3
        let r = merge(vec![spool(1, &[0, 1, 3])]).unwrap();
        assert_eq!(r.seq_gaps, 1);
    }

    #[test]
    fn three_missing_seqs_across_two_gaps_count_as_three() {
        // 0, [1, 2 missing], 3, [4 missing], 5 -- two GAPS (a run of missing
        // seqs each count once), three missing SEQS total.
        let r = merge(vec![spool(1, &[0, 3, 5])]).unwrap();
        assert_eq!(r.seq_gaps, 3);
    }

    #[test]
    fn no_records_at_all_is_zero_gaps() {
        let r = merge(vec![spool(1, &[])]).unwrap();
        assert_eq!(r.seq_gaps, 0);
        assert!(r.records.is_empty());
    }

    #[test]
    fn a_seq_shared_by_two_threads_is_a_named_error() {
        let err = merge(vec![spool(1, &[0, 2]), spool(2, &[2, 4])]).unwrap_err();
        assert!(err.contains('2'), "{err}");
        assert!(
            err.contains("thread 1") && err.contains("thread 2"),
            "{err}"
        );
    }

    #[test]
    fn threads_interleave_by_seq_not_by_arrival_order() {
        let r = merge(vec![spool(9, &[3]), spool(1, &[0])]).unwrap();
        assert_eq!(r.records[0].thread_serial, 1);
        assert_eq!(r.records[1].thread_serial, 9);
    }
}
