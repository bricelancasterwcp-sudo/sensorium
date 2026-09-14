//! Discovery: what one spool directory HOLDS, read before anything of it is
//! converted.
//!
//! Split out of `convert/mod.rs` at this repository's 800-line ceiling, along
//! the seam that file's own section banner already drew. Everything here reads
//! a directory or a manifest set and answers a question about the INVOCATION
//! -- which pids it produced, which spool files belong to each, which
//! manifests are this workspace's, which run id each pid is given, what the
//! multi-process WARN should say -- and nothing here opens a trace or writes a
//! row. `convert_dir` asks these questions in order and hands the answers to
//! `convert_one`, which is the half that stayed.
//!
//! Every function reached from outside is `pub(super)` and is named one by
//! one in `mod.rs`'s `use`, never through a glob: the thirteen `convert_dir`
//! and `convert_one` call, and `manifest_in_scope`, which `focus.rs` asks for
//! through `super::` and which is re-exported for it. `parse_spool_filename`
//! is read only from in here and stays private.

use std::collections::BTreeMap;
use std::path::Path;

use serde_json::{json, Value};

use crate::convert::manifest::{Manifest, SiteKind};
use crate::convert::spool::{ProcHeader, RunnerRecord};

pub(super) fn list_dir(dir: &Path) -> Result<Vec<String>, String> {
    std::fs::read_dir(dir)
        .map_err(|e| format!("cannot read {}: {e}", dir.display()))?
        .map(|e| {
            e.map(|e| e.file_name().to_string_lossy().into_owned())
                .map_err(|e| format!("cannot read an entry of {}: {e}", dir.display()))
        })
        .collect()
}

pub(super) fn read_proc_headers(
    dir: &Path,
    entries: &[String],
) -> Result<BTreeMap<u32, ProcHeader>, String> {
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

pub(super) fn check_no_orphan_spools(
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

pub(super) fn group_spool_files(entries: &[String]) -> BTreeMap<u32, Vec<String>> {
    let mut out: BTreeMap<u32, Vec<String>> = BTreeMap::new();
    for name in entries {
        if let Some((pid, _)) = parse_spool_filename(name) {
            out.entry(pid).or_default().push(name.clone());
        }
    }
    out
}

/// Is this process one rustdoc built for a doctest and then deleted?
///
/// The rule the repo already reads a doctest process by: rustdoc compiles each
/// doctest to a `/tmp/rustdoctest*/rust_out` and unlinks it immediately (rung-2
/// spike findings §5.11), and `rust/tests/lib/trace.sh::doctest_processes`
/// matches on the same substring -- deliberately the same rule, so the shell
/// instrument and the converter cannot drift apart on what a doctest is.
///
/// It is a path substring and nothing stronger: a workspace with a crate
/// literally named `rustdoctest*` would have its own binary counted as a
/// doctest. That miscount is the same size as the one this closes and in the
/// other direction, and no such crate has been met; a tighter rule would have
/// to pin rustdoc's `rust_out` filename, which is not a promise rustdoc makes.
pub(super) fn is_doctest_exe(exe: &str) -> bool {
    exe.contains("/rustdoctest")
}

/// The sentence the multi-process WARN prints.
///
/// `invocation_processes` counts every process the runner started, doctests
/// included -- that is what the field means and what `refocus` reads. This
/// SENTENCE said "N test binaries" over the same number, and on cargo 1.96 the
/// runner is handed every doctest process too, so it overstated by the doctest
/// count (rung-3 inbox: "`convert/mod.rs:141-147`'s WARN counts runner
/// records"). The two kinds are counted apart and both are named: a doctest is
/// not a test binary, and an invocation of one test binary and four doctests
/// still produced five traces, so dropping the doctests from the sentence
/// entirely would trade one wrong number for a missing one.
pub(super) fn multi_process_warning(test_binaries: usize, doctests: usize) -> String {
    let tests = format!(
        "{test_binaries} test binar{}",
        if test_binaries == 1 { "y" } else { "ies" }
    );
    let docs = match doctests {
        0 => String::new(),
        1 => " and 1 doctest process".to_owned(),
        n => format!(" and {n} doctest processes"),
    };
    format!(
        "WARN: this invocation produced {tests}{docs}; a single-target selector \
         (--lib, --test X, --bin X) makes one trace the answer"
    )
}

pub(super) fn read_runner_records(
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

pub(super) fn load_all_manifests(dir: &Path) -> Result<BTreeMap<String, Manifest>, String> {
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

/// A manifest is THIS invocation's only when its `workspace_root` matches
/// `invocation.json`'s -- a shared `CARGO_TARGET_DIR` holds every workspace's
/// manifests in one directory, and an empty `workspace_root` (a manifest that
/// predates the field) can never match a real one.
pub(super) fn manifest_in_scope(m: &Manifest, invocation_workspace_root: &str) -> bool {
    !m.workspace_root.is_empty() && m.workspace_root == invocation_workspace_root
}

pub(super) fn uninstrumented_list(
    manifests: &BTreeMap<String, Manifest>,
    invocation_workspace_root: &str,
) -> Vec<Value> {
    manifests
        .iter()
        .filter(|(_, m)| m.fell_back && manifest_in_scope(m, invocation_workspace_root))
        .map(|(metadata, m)| {
            json!({
                "unit": metadata,
                "crate_name": m.crate_name,
                "reason": m.fallback_reason.clone().unwrap_or_default(),
            })
        })
        .collect()
}

/// Mint one run id per pid in `order`, deduplicated WITHIN this call: none of
/// these ids has a `.db`/`.db.tmp` on disk yet (every id is assigned before
/// any pid converts, so a parent's `child_runs` can name a child's id
/// regardless of conversion order), so the directory a single `mint_one` call
/// checks cannot see a sibling minted moments earlier in this same loop --
/// only the growing `minted` set threaded through every call can.
///
/// `mint_one` is `runid::mint` in production, bound to a fixed `traces_dir`;
/// a fake generator in `tests::mint_run_ids_dedupes_when_the_generator_
/// repeats_a_candidate` forces the collision this function exists to close
/// without depending on the clock or the salt to actually repeat.
///
/// # Errors
/// Whatever `mint_one` returns.
pub(super) fn mint_run_ids(
    order: impl Iterator<Item = u32>,
    mut mint_one: impl FnMut(&std::collections::HashSet<String>) -> Result<String, String>,
) -> Result<BTreeMap<u32, String>, String> {
    let mut run_ids: BTreeMap<u32, String> = BTreeMap::new();
    let mut minted_ids: std::collections::HashSet<String> = std::collections::HashSet::new();
    for pid in order {
        let id = mint_one(&minted_ids)?;
        minted_ids.insert(id.clone());
        run_ids.insert(pid, id);
    }
    Ok(run_ids)
}

pub(super) fn child_runs(
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

/// The site table the `exceptions` reader joins a frame to its marks with
/// (design R1b/R8): one row per site of the units THIS process registered.
///
/// Registered-unit-scoped for the same reason `skipped` is -- the proc header
/// lists exactly the units this process linked -- and it carries every kind,
/// not just the frames, because the row an err-flow event was recorded at is
/// what names the sink a chain was absorbed at.
pub(super) fn site_table(
    registered: &[String],
    manifests: &BTreeMap<String, Manifest>,
) -> Vec<Value> {
    let mut out = Vec::new();
    for metadata in registered {
        let Some(m) = manifests.get(metadata) else {
            continue;
        };
        for (file, sites) in &m.files {
            for s in sites {
                let mut row = serde_json::Map::new();
                row.insert("unit".to_owned(), json!(metadata));
                row.insert("site".to_owned(), json!(s.site));
                row.insert("file".to_owned(), json!(file));
                row.insert("qualname".to_owned(), json!(s.qualname));
                row.insert("kind".to_owned(), json!(s.kind.as_str()));
                row.insert("line".to_owned(), json!(s.firstlineno.or(s.line)));
                if let Some(how) = &s.how {
                    row.insert("how".to_owned(), json!(how));
                }
                row.insert("test".to_owned(), json!(s.test));
                row.insert("main".to_owned(), json!(s.main));
                out.push(Value::Object(row));
            }
        }
    }
    out
}

/// The focus THIS BUILD was made under (design 2026-09-06 §2.4, ruling R-F10),
/// gathered from every manifest of this invocation.
///
/// **Build-scoped, deliberately -- unlike [`site_table`] and
/// [`line_site_count`], which are registered-unit-scoped.** `focus_matched` is
/// a fact about what the TRANSFORMER matched while compiling, not about what
/// this process ran: a focus value that selected a function in a linked unit
/// whose code never executed still matched. Unioning only over registered
/// units would report `focus: ["fill"], focus_matched: []` for it --
/// indistinguishable from a value that matched nowhere in the workspace, which
/// is the one question `focus_matched` exists to answer.
///
/// `capabilities.line`/`locals` keep the narrower scope on purpose: a LINE
/// RECORD can only come from a unit this process linked and registered, so a
/// capability read off registered units cannot promise rows that cannot exist.
///
/// How many `line` sites the units this process REGISTERED hold. The whole
/// basis for `capabilities.line`/`locals`: a run with none cannot produce a
/// LINE row, whatever was typed on the command line.
///
/// Narrower than [`focus_record`]'s scope on purpose (ruling R-F10): a LINE
/// record can only arrive from a unit this process linked, so counting a
/// non-registered unit's `line` sites here would declare a capability whose
/// rows could never appear.
pub(super) fn line_site_count(
    registered: &[String],
    manifests: &BTreeMap<String, Manifest>,
) -> usize {
    registered
        .iter()
        .filter_map(|metadata| manifests.get(metadata))
        .flat_map(|m| m.files.values())
        .flatten()
        .filter(|s| s.kind == SiteKind::Line)
        .count()
}
