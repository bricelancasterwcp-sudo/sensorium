//! Task 6: the Rust converter. Spools, proc headers, runner records and unit
//! manifests, in, one `trace_format = 4` SQLite file per pid, out.
//!
//! `rust/HONESTY.md` §1, §4, §5, §6, §7, §8 are this module's promises; the
//! wire format it reads is reproduced independently in [`spool`], never
//! imported from `sensorium-rt`'s writer.
//!
//! One pid is one process is one trace: `<spool>/<pid>.proc.json` is what
//! makes a pid "this invocation's", and every `<pid>.<serial>.spool` /
//! `<pid>.runner.json` is read against that set -- a spool file whose pid has
//! no proc header is an orphan and a hard error, never silently skipped.

mod chains;
mod discover;
mod errflow;
mod fingerprint;
mod focus;
mod frames;
mod manifest;
mod merge;
mod meta;
mod redaction;
// Task 2 fills this in; Task 6 wires it into `convert_one`. Module-level so
// that every item in it -- not just the ones a later task reaches first --
// stays quiet under `-D warnings` until that wiring lands.
#[allow(dead_code)]
mod redact_content;
mod runid;
mod spool;
mod sqlite;

use std::collections::BTreeMap;
use std::path::Path;

use sensorium_rt::redact::Key;
use serde_json::Value;

use crate::redaction_key;
use discover::{
    check_no_orphan_spools, child_runs, group_spool_files, is_doctest_exe, line_site_count,
    list_dir, load_all_manifests, manifest_in_scope, mint_run_ids, multi_process_warning,
    read_proc_headers, read_runner_records, site_table, uninstrumented_list,
};
use manifest::Manifest;
use spool::{InvocationRecord, ProcHeader, RunnerRecord};

/// The store this invocation reads and writes, resolved once
/// (`runid::store_root`). Spelled through this module so the driver's
/// `--refocus-of` lookup and the converter's own `traces_dir` can never
/// disagree about where `SENSORIUM_DIR` defaults to.
pub(crate) use runid::store_root;

/// One pid's worth of the report `convert_dir` prints.
pub struct TraceSummary {
    pub run_id: String,
    pub pid: u32,
    pub exe: String,
    pub events: usize,
    pub threads: usize,
    pub exit_display: String,
}

#[allow(dead_code)] // see `TraceSummary`.
pub struct Report {
    pub traces: Vec<TraceSummary>,
    /// Distinct pids the runner witnessed -- the WARN's own count.
    pub runner_processes: usize,
}

/// Convert one invocation's spool directory. Prints `run: …` to stdout (and
/// the multi-binary WARN to stderr) as a side effect, so the driver seam and
/// the standalone `convert` role produce identical output by calling this one
/// function.
///
/// `key` is the STORE's redaction key, passed in rather than resolved here:
/// the driver minted it before cargo ran and handed that same one to every
/// recorded process (`redaction_key`).
///
/// # Errors
/// Any spool, header or manifest this converter cannot read honestly, named
/// by file: a missing `invocation.json`, a missing manifests directory, an
/// orphan spool, a manifest naming a `sensorium/mirror` path, a backwards or
/// duplicate `seq`, a RETURN with no open frame, or a malformed record.
pub fn convert_dir(spool_dir: &Path, key: &Key) -> Result<Report, String> {
    let invocation = InvocationRecord::read(&spool_dir.join("invocation.json"))
        .map_err(|e| format!("cannot read invocation.json: {e}"))?;

    let entries = list_dir(spool_dir)?;
    let proc_headers = read_proc_headers(spool_dir, &entries)?;
    check_no_orphan_spools(spool_dir, &entries, &proc_headers)?;
    let spool_files_by_pid = group_spool_files(&entries);
    let runner_records = read_runner_records(spool_dir, &entries)?;

    // Nothing recorded a process at all -- `cargo sensorium test --help`, a
    // cargo failure before anything compiled, or a `target/sensorium` wiped
    // between builds while cargo stayed fingerprint-fresh. There is nothing
    // to convert, and demanding a manifests directory that was never written
    // because nothing was ever instrumented would turn a clean run into an
    // error. An invocation that DID record a process (`proc_headers` is
    // non-empty) still gets the hard error below if its manifests are gone.
    if proc_headers.is_empty() {
        return Ok(Report {
            traces: Vec::new(),
            runner_processes: runner_records.len(),
        });
    }

    let manifests_dir = Path::new(&invocation.target_dir)
        .join("sensorium")
        .join("manifests");
    if !manifests_dir.is_dir() {
        return Err(format!(
            "no manifests directory at {}",
            manifests_dir.display()
        ));
    }
    let all_manifests = load_all_manifests(&manifests_dir)?;
    // A shared `CARGO_TARGET_DIR` holds every workspace's manifests in one
    // directory (the corpus's 13 unrelated crates measured this live): a
    // manifest belongs to THIS invocation only when its `workspace_root`
    // matches `invocation.json`'s. A manifest with no `workspace_root` at all
    // predates this field (`sensorium-transform`'s `Manifest` reads it with
    // `#[serde(default)]`) and is counted here rather than silently dropped,
    // so a reader can say how many manifests are that old.
    let manifests_unscoped = all_manifests
        .values()
        .filter(|m| m.workspace_root.is_empty())
        .count();
    let uninstrumented_global = uninstrumented_list(&all_manifests, &invocation.workspace_root);

    let traces_dir = runid::traces_dir()?;
    // Every run id is assigned FIRST, so a parent's `child_runs` can name a
    // child's run id even though the parent may convert before the child.
    let run_ids = mint_run_ids(proc_headers.keys().copied(), |minted| {
        runid::mint(&traces_dir, minted)
    })?;

    let child_runs_by_parent = child_runs(&proc_headers, &run_ids);

    // Counted BEFORE the loop, not after it: every trace of this invocation
    // records how many test binaries the invocation produced
    // (`invocation_processes`, design 2026-09-07 §2.2), and it is the same
    // count the WARN below prints -- one fact, one source.
    let runner_processes = runner_records.len();

    let mut summaries = Vec::new();
    for (&pid, header) in &proc_headers {
        let summary = convert_one(ConvertOne {
            pid,
            spool_dir,
            invocation: &invocation,
            proc: header,
            all_manifests: &all_manifests,
            uninstrumented_global: &uninstrumented_global,
            manifests_unscoped,
            spool_paths: spool_files_by_pid.get(&pid).map_or(&[][..], Vec::as_slice),
            run_id: &run_ids[&pid],
            runner: runner_records.get(&pid),
            child_runs: child_runs_by_parent
                .get(&pid)
                .map_or(&[][..], Vec::as_slice),
            traces_dir: &traces_dir,
            runner_processes,
            key,
        })?;
        println!(
            "run: {}  pid: {}  exe: {}  events: {}  threads: {}  exit: {}",
            summary.run_id,
            summary.pid,
            summary.exe,
            summary.events,
            summary.threads,
            summary.exit_display
        );
        summaries.push(summary);
    }

    if runner_processes > 1 {
        // Counted here and not from `runner_processes`: see
        // [`multi_process_warning`] for why the sentence may not call a
        // doctest a test binary.
        let doctests = runner_records
            .keys()
            .filter(|pid| {
                proc_headers
                    .get(pid)
                    .is_some_and(|h| is_doctest_exe(&h.exe))
            })
            .count();
        eprintln!(
            "{}",
            multi_process_warning(runner_processes - doctests, doctests)
        );
    }

    Ok(Report {
        traces: summaries,
        runner_processes,
    })
}

/// `cargo-sensorium convert <spool dir>`.
#[must_use]
pub fn run(args: &[String]) -> i32 {
    let [dir] = args else {
        eprintln!("usage: cargo-sensorium convert <spool dir>");
        return 2;
    };
    // `load`, never `load_or_create`: this role converts a spool somebody else
    // recorded, and a key minted at conversion time would take digests nothing
    // was ever recorded under. A store root that cannot be resolved at all is
    // unkeyed here and named by `traces_dir` a moment later, which resolves
    // the same root and reports the same failure by name.
    let key = store_root().map_or_else(|_| Key::from_hex(None), |r| redaction_key::load(&r));
    match convert_dir(Path::new(dir), &key) {
        Ok(_) => 0,
        Err(e) => {
            eprintln!("cargo-sensorium: {e}");
            2
        }
    }
}

// ---------------------------------------------------------------------------
// Per-pid conversion
// ---------------------------------------------------------------------------

struct ConvertOne<'a> {
    pid: u32,
    spool_dir: &'a Path,
    invocation: &'a InvocationRecord,
    proc: &'a ProcHeader,
    all_manifests: &'a BTreeMap<String, Manifest>,
    uninstrumented_global: &'a [Value],
    manifests_unscoped: usize,
    spool_paths: &'a [String],
    run_id: &'a str,
    runner: Option<&'a RunnerRecord>,
    child_runs: &'a [Value],
    traces_dir: &'a Path,
    /// Distinct pids the runner witnessed for this invocation -- the WARN's
    /// own count, and every trace's `invocation_processes`.
    runner_processes: usize,
    /// The store's key, for a header too old to have applied the rule itself.
    key: &'a Key,
}

#[allow(clippy::too_many_lines)]
fn convert_one(c: ConvertOne<'_>) -> Result<TraceSummary, String> {
    let spool_dir = c.spool_dir;
    let mut spools = Vec::with_capacity(c.spool_paths.len());
    for name in c.spool_paths {
        spools.push(spool::read_spool_file(&spool_dir.join(name))?);
    }
    let names: BTreeMap<u32, String> = spools.iter().map(|s| (s.serial, s.name.clone())).collect();
    let headers: BTreeMap<u32, (u64, u64)> = spools
        .iter()
        .map(|s| (s.serial, (s.records_dropped, s.truncated)))
        .collect();
    // Per THREAD, because that is the granularity a spool file has: one
    // process's threads all write the same version in practice, and a reader
    // that assumed it would be reading the header of one file into another.
    let versions: BTreeMap<u32, u8> = spools.iter().map(|s| (s.serial, s.version)).collect();

    let merged = merge::merge(spools)?;

    let tmp_path = c.traces_dir.join(format!("{}.db.tmp", c.run_id));
    let writer = sqlite::TraceWriter::create(&tmp_path)?;
    writer.set_meta("trace_format", &4)?;
    writer.set_meta("incomplete", &true)?;

    let result = frames::process(
        &writer,
        &frames::Walk {
            merged: &merged,
            proc: c.proc,
            manifests: c.all_manifests,
            workspace_root: &c.invocation.workspace_root,
            pid: c.pid,
            names: &names,
            versions: &versions,
        },
    )?;

    let threads_started = names.keys().filter(|&&s| s != 1).count();
    let mut live_threads = Vec::new();
    for (serial, name) in &names {
        if !result.ended_threads.contains(serial) {
            live_threads.push(name.clone());
        }
    }

    let truncated_count: u64 = headers.values().map(|&(_, t)| t).sum();
    let records_dropped: BTreeMap<u32, u64> = headers.iter().map(|(&s, &(d, _))| (s, d)).collect();

    let start_ts = c.proc.start_realtime_ns as f64 / 1e9;
    let end_ts = merged
        .records
        .iter()
        .map(|m| m.record.ts_ns)
        .max()
        .map_or(start_ts, |max_ts| {
            start_ts + max_ts.saturating_sub(c.proc.start_ns) as f64 / 1e9
        });

    let registered = c.proc.units_in_order();
    let mut source_hashes = BTreeMap::new();
    let mut skipped = Vec::new();
    let mut partial = Vec::new();
    let mut spawns = Vec::new();
    let mut unreached_files = Vec::new();
    for metadata in &registered {
        let m = c
            .all_manifests
            .get(metadata)
            .ok_or_else(|| format!("pid {}: no manifest for registered unit {metadata}", c.pid))?;
        // NOT workspace-scoped, deliberately: `registered` already IS the
        // correct scope (this process's own proc header lists exactly the
        // units it linked), and cargo's freshness caching can leave a unit's
        // manifest on disk from an EARLIER build of the very same source --
        // possibly one that predates the `workspace_root` field entirely --
        // without the wrapper running again to refresh it (measured live on
        // the Task 10 corpus: `rust/spawned_thread`'s own cached manifest
        // carried no `workspace_root`, and scoping this loop the same way
        // `uninstrumented_list` is scoped silently dropped its own
        // `spawns` entry). A stale-but-genuinely-this-unit's manifest stays
        // visible; only the GLOBAL scan across every OTHER manifest in the
        // shared directory needs the workspace filter.
        for (k, v) in &m.source_hashes {
            source_hashes.insert(k.clone(), v.clone());
        }
        skipped.extend(m.skipped.iter().cloned());
        partial.extend(m.partial.iter().cloned());
        spawns.extend(m.spawns.iter().cloned());
        unreached_files.extend(m.unreached_files.iter().cloned());
    }
    unreached_files.sort();
    unreached_files.dedup();

    let (exit_status, exit_signal, exit_status_basis, wall) = match c.runner {
        Some(r) => (
            r.exit_status,
            r.signal,
            "waited",
            Some((r.wall_start_ts, r.wall_end_ts)),
        ),
        None => (None, None, "unwitnessed", None),
    };

    let focus = focus::record(
        &c.invocation.focus,
        c.all_manifests,
        &c.invocation.workspace_root,
    );
    let redacted = redaction::apply(c.proc, c.key);
    let meta_input = meta::MetaInput {
        run_id: c.run_id,
        argv: &c.proc.argv,
        cwd: &c.proc.cwd,
        env_hash: &redacted.env_hash,
        start_ts,
        end_ts,
        exit_status,
        truncated_count,
        source_hashes: &source_hashes,
        recorder: &c.proc.rt_version,
        threads_started,
        live_threads: &live_threads,
        env: &redacted.env,
        redaction: redacted.redaction.clone(),
        invocation: &c.invocation.invocation,
        invocation_processes: c.runner_processes,
        refocus_of: c.invocation.refocus_of.as_deref(),
        pid: c.pid,
        ppid: c.proc.ppid,
        exe: &c.proc.exe,
        toolchain: &c.invocation.toolchain,
        rustc_path: &c.invocation.rustc_path,
        cargo_args: &c.invocation.cargo_args,
        profile: &c.invocation.profile,
        workspace_root: &c.invocation.workspace_root,
        tool_hash: &c.invocation.tool_hash,
        driver_version: &c.invocation.driver_version,
        instrumented_units: &registered,
        uninstrumented: c.uninstrumented_global,
        manifests_unscoped: c.manifests_unscoped,
        skipped: &skipped,
        partial: &partial,
        sites: &site_table(&registered, c.all_manifests),
        spawns: &spawns,
        unreached_files: &unreached_files,
        refused_at: c.proc.refused.as_ref().map(|r| r.at.as_str()),
        exit_status_basis,
        exit_signal,
        wall,
        records_dropped: &records_dropped,
        seq_gaps: merged.seq_gaps,
        panics_unrecorded: result.panics_unrecorded,
        panics_outside_frames: result.panics_outside_frames,
        err_flow_raise: result.err_flow_raise,
        err_flow_handled: result.err_flow_handled,
        err_flow_outside_frames: result.err_flow_outside_frames,
        closure_frames: result.closure_frames,
        err_flow_capability: c
            .proc
            .capabilities
            .get("err_flow")
            .copied()
            .unwrap_or(false),
        focus: focus.as_ref(),
        line_sites: line_site_count(&registered, c.all_manifests),
        child_runs: c.child_runs,
    };
    for (key, value) in meta::build(&meta_input) {
        writer.set_meta(key, &value)?;
    }
    writer.set_meta("incomplete", &false)?;

    let dest = c.traces_dir.join(format!("{}.db", c.run_id));
    writer.finish(&dest)?;

    let exe_base = Path::new(&c.proc.exe)
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_else(|| c.proc.exe.clone());
    // The `run:` line's third exit form: a code when the runner waited and the
    // process exited; `signal N` when the runner waited and it was killed by
    // one (`exit_status` is null in EXACTLY that case, so a signal must be
    // checked before falling back to "unwitnessed" -- a signalled process is
    // witnessed, just not with an exit code).
    let exit_display = match (exit_status, exit_signal) {
        (Some(code), _) => code.to_string(),
        (None, Some(sig)) => format!("signal {sig}"),
        (None, None) => "unwitnessed".to_owned(),
    };

    Ok(TraceSummary {
        run_id: c.run_id.to_owned(),
        pid: c.pid,
        exe: exe_base,
        events: result.events_written,
        threads: names.len(),
        exit_display,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;

    /// Simulates two pids whose real candidates happened to collide: the
    /// fake generator hands out `"A"` twice before `"B"`, and does its OWN
    /// retry against `minted` -- exactly what `runid::mint` does -- so what
    /// this test actually pins is whether `mint_run_ids` threads the growing
    /// `minted` set from one call to the next. With the bug this fix closes
    /// (each call given an empty set instead of the accumulated one), the
    /// second call would accept `"A"` immediately and pid 2 would get pid 1's
    /// id back.
    #[test]
    fn mint_run_ids_dedupes_when_the_generator_repeats_a_candidate() {
        let mut candidates: VecDeque<String> =
            ["A", "A", "B"].iter().map(|s| (*s).to_owned()).collect();
        let ids = mint_run_ids([1u32, 2u32].into_iter(), |minted| loop {
            let c = candidates
                .pop_front()
                .ok_or_else(|| "ran out of candidates".to_owned())?;
            if !minted.contains(&c) {
                return Ok(c);
            }
        })
        .unwrap();
        assert_eq!(ids[&1], "A");
        assert_eq!(ids[&2], "B", "pid 2 must not receive pid 1's id back");
        assert!(
            candidates.is_empty(),
            "all three candidates must be consumed"
        );
    }

    /// The row this fix closes: three runner records of which one is a
    /// doctest must not be announced as three test binaries.
    #[test]
    fn the_warn_counts_doctest_processes_apart_from_test_binaries() {
        assert_eq!(
            multi_process_warning(2, 1),
            "WARN: this invocation produced 2 test binaries and 1 doctest process; a \
             single-target selector (--lib, --test X, --bin X) makes one trace the answer"
        );
        assert_eq!(
            multi_process_warning(1, 4),
            "WARN: this invocation produced 1 test binary and 4 doctest processes; a \
             single-target selector (--lib, --test X, --bin X) makes one trace the answer"
        );
        // No doctests: the sentence it always was.
        assert_eq!(
            multi_process_warning(3, 0),
            "WARN: this invocation produced 3 test binaries; a single-target selector \
             (--lib, --test X, --bin X) makes one trace the answer"
        );
    }

    #[test]
    fn a_doctest_exe_is_the_one_rustdoc_wrote_under_tmp() {
        assert!(is_doctest_exe("/tmp/rustdoctestXH1cVv/rust_out"));
        assert!(!is_doctest_exe("/w/target/debug/deps/demo-1a2b3c"));
        assert!(!is_doctest_exe("/w/target/debug/deps/doctest_helper-9f"));
        assert!(!is_doctest_exe(""));
    }

    #[test]
    fn mint_run_ids_mints_nothing_for_an_empty_pid_set() {
        let ids = mint_run_ids(std::iter::empty(), |_| {
            panic!("must not call the generator for zero pids")
        })
        .unwrap();
        assert!(ids.is_empty());
    }

    #[test]
    fn mint_run_ids_propagates_a_generator_error() {
        let err = mint_run_ids([1u32].into_iter(), |_| Err("boom".to_owned())).unwrap_err();
        assert_eq!(err, "boom");
    }
}
