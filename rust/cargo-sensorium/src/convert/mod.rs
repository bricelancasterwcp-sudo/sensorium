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

mod fingerprint;
mod frames;
mod merge;
mod meta;
mod runid;
mod spool;
mod sqlite;

use std::collections::BTreeMap;
use std::path::Path;

use serde_json::{json, Value};

use spool::{InvocationRecord, Manifest, ProcHeader, RunnerRecord};

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
/// # Errors
/// Any spool, header or manifest this converter cannot read honestly, named
/// by file: a missing `invocation.json`, a missing manifests directory, an
/// orphan spool, a manifest naming a `sensorium/mirror` path, a backwards or
/// duplicate `seq`, a RETURN with no open frame, or a malformed record.
pub fn convert_dir(spool_dir: &Path) -> Result<Report, String> {
    let invocation = InvocationRecord::read(&spool_dir.join("invocation.json"))
        .map_err(|e| format!("cannot read invocation.json: {e}"))?;

    let entries = list_dir(spool_dir)?;
    let proc_headers = read_proc_headers(spool_dir, &entries)?;
    check_no_orphan_spools(spool_dir, &entries, &proc_headers)?;
    let spool_files_by_pid = group_spool_files(&entries);
    let runner_records = read_runner_records(spool_dir, &entries)?;

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
    let uninstrumented_global = uninstrumented_list(&all_manifests);

    let traces_dir = runid::traces_dir()?;
    // Every run id is assigned FIRST, so a parent's `child_runs` can name a
    // child's run id even though the parent may convert before the child.
    let mut run_ids: BTreeMap<u32, String> = BTreeMap::new();
    for &pid in proc_headers.keys() {
        run_ids.insert(pid, runid::mint(&traces_dir)?);
    }

    let child_runs_by_parent = child_runs(&proc_headers, &run_ids);

    let mut summaries = Vec::new();
    for (&pid, header) in &proc_headers {
        let summary = convert_one(ConvertOne {
            pid,
            spool_dir,
            invocation: &invocation,
            proc: header,
            all_manifests: &all_manifests,
            uninstrumented_global: &uninstrumented_global,
            spool_paths: spool_files_by_pid.get(&pid).map_or(&[][..], Vec::as_slice),
            run_id: &run_ids[&pid],
            runner: runner_records.get(&pid),
            child_runs: child_runs_by_parent
                .get(&pid)
                .map_or(&[][..], Vec::as_slice),
            traces_dir: &traces_dir,
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

    let runner_processes = runner_records.len();
    if runner_processes > 1 {
        eprintln!(
            "WARN: this invocation produced {runner_processes} test binaries; a single-target \
             selector (--lib, --test X, --bin X) makes one trace the answer"
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
    match convert_dir(Path::new(dir)) {
        Ok(_) => 0,
        Err(e) => {
            eprintln!("cargo-sensorium: {e}");
            2
        }
    }
}

// ---------------------------------------------------------------------------
// Discovery
// ---------------------------------------------------------------------------

fn list_dir(dir: &Path) -> Result<Vec<String>, String> {
    std::fs::read_dir(dir)
        .map_err(|e| format!("cannot read {}: {e}", dir.display()))?
        .map(|e| {
            e.map(|e| e.file_name().to_string_lossy().into_owned())
                .map_err(|e| format!("cannot read an entry of {}: {e}", dir.display()))
        })
        .collect()
}

fn read_proc_headers(dir: &Path, entries: &[String]) -> Result<BTreeMap<u32, ProcHeader>, String> {
    let mut out = BTreeMap::new();
    for name in entries {
        let Some(pid_str) = name.strip_suffix(".proc.json") else {
            continue;
        };
        let pid: u32 = pid_str
            .parse()
            .map_err(|_| format!("{}: {name} does not name a pid", dir.display()))?;
        out.insert(pid, ProcHeader::read(&dir.join(name))?);
    }
    Ok(out)
}

/// `<pid>.<serial>.spool` -> `(pid, serial)`.
fn parse_spool_filename(name: &str) -> Option<(u32, u32)> {
    let stem = name.strip_suffix(".spool")?;
    let (pid, serial) = stem.rsplit_once('.')?;
    Some((pid.parse().ok()?, serial.parse().ok()?))
}

fn check_no_orphan_spools(
    dir: &Path,
    entries: &[String],
    proc_headers: &BTreeMap<u32, ProcHeader>,
) -> Result<(), String> {
    for name in entries {
        if let Some((pid, _)) = parse_spool_filename(name) {
            if !proc_headers.contains_key(&pid) {
                return Err(format!(
                    "orphan spool: {} has no matching {pid}.proc.json",
                    dir.join(name).display()
                ));
            }
        }
    }
    Ok(())
}

fn group_spool_files(entries: &[String]) -> BTreeMap<u32, Vec<String>> {
    let mut out: BTreeMap<u32, Vec<String>> = BTreeMap::new();
    for name in entries {
        if let Some((pid, _)) = parse_spool_filename(name) {
            out.entry(pid).or_default().push(name.clone());
        }
    }
    out
}

fn read_runner_records(
    dir: &Path,
    entries: &[String],
) -> Result<BTreeMap<u32, RunnerRecord>, String> {
    let mut out = BTreeMap::new();
    for name in entries {
        let Some(pid_str) = name.strip_suffix(".runner.json") else {
            continue;
        };
        let pid: u32 = pid_str
            .parse()
            .map_err(|_| format!("{}: {name} does not name a pid", dir.display()))?;
        out.insert(pid, RunnerRecord::read(&dir.join(name))?);
    }
    Ok(out)
}

fn load_all_manifests(dir: &Path) -> Result<BTreeMap<String, Manifest>, String> {
    let mut out = BTreeMap::new();
    for entry in
        std::fs::read_dir(dir).map_err(|e| format!("cannot read {}: {e}", dir.display()))?
    {
        let entry = entry.map_err(|e| format!("cannot read an entry of {}: {e}", dir.display()))?;
        let path = entry.path();
        if path.extension().and_then(std::ffi::OsStr::to_str) != Some("json") {
            continue;
        }
        let metadata = path
            .file_stem()
            .map(|s| s.to_string_lossy().into_owned())
            .ok_or_else(|| format!("{}: no file stem", path.display()))?;
        out.insert(metadata, Manifest::read(&path)?);
    }
    Ok(out)
}

fn uninstrumented_list(manifests: &BTreeMap<String, Manifest>) -> Vec<Value> {
    manifests
        .iter()
        .filter(|(_, m)| m.fell_back)
        .map(|(metadata, m)| {
            json!({
                "unit": metadata,
                "crate_name": m.crate_name,
                "reason": m.fallback_reason.clone().unwrap_or_default(),
            })
        })
        .collect()
}

fn child_runs(
    proc_headers: &BTreeMap<u32, ProcHeader>,
    run_ids: &BTreeMap<u32, String>,
) -> BTreeMap<u32, Vec<Value>> {
    let mut out: BTreeMap<u32, Vec<Value>> = BTreeMap::new();
    for (&pid, header) in proc_headers {
        if proc_headers.contains_key(&header.ppid) {
            out.entry(header.ppid).or_default().push(json!({
                "run_id": run_ids[&pid],
                "pid": pid,
                "exe": header.exe,
            }));
        }
    }
    out
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
    spool_paths: &'a [String],
    run_id: &'a str,
    runner: Option<&'a RunnerRecord>,
    child_runs: &'a [Value],
    traces_dir: &'a Path,
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

    let merged = merge::merge(spools)?;

    let tmp_path = c.traces_dir.join(format!("{}.db.tmp", c.run_id));
    let writer = sqlite::TraceWriter::create(&tmp_path)?;
    writer.set_meta("trace_format", &4)?;
    writer.set_meta("incomplete", &true)?;

    let result = frames::process(
        &writer,
        &merged,
        c.proc,
        c.all_manifests,
        &c.invocation.workspace_root,
        c.pid,
        &names,
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
    let mut spawns = Vec::new();
    let mut unreached_files = Vec::new();
    for metadata in &registered {
        let m = c
            .all_manifests
            .get(metadata)
            .ok_or_else(|| format!("pid {}: no manifest for registered unit {metadata}", c.pid))?;
        for (k, v) in &m.source_hashes {
            source_hashes.insert(k.clone(), v.clone());
        }
        skipped.extend(m.skipped.iter().cloned());
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

    let meta_input = meta::MetaInput {
        run_id: c.run_id,
        argv: &c.proc.argv,
        cwd: &c.proc.cwd,
        env_hash: &c.proc.env_hash,
        start_ts,
        end_ts,
        exit_status,
        truncated_count,
        source_hashes: &source_hashes,
        recorder: &c.proc.rt_version,
        threads_started,
        live_threads: &live_threads,
        env: &c.proc.env,
        invocation: &c.invocation.invocation,
        pid: c.pid,
        ppid: c.proc.ppid,
        exe: &c.proc.exe,
        toolchain: &c.invocation.toolchain,
        rustc_path: &c.invocation.rustc_path,
        cargo_args: &c.invocation.cargo_args,
        profile: &c.invocation.profile,
        tool_hash: &c.invocation.tool_hash,
        driver_version: &c.invocation.driver_version,
        instrumented_units: &registered,
        uninstrumented: c.uninstrumented_global,
        skipped: &skipped,
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
    let exit_display =
        exit_status.map_or_else(|| "unwitnessed".to_owned(), |code| code.to_string());

    Ok(TraceSummary {
        run_id: c.run_id.to_owned(),
        pid: c.pid,
        exe: exe_base,
        events: result.events_written,
        threads: names.len(),
        exit_display,
    })
}
