//! The `RUSTC_WORKSPACE_WRAPPER` role. Cargo's contract: `argv[1]` is the real
//! rustc, `argv[2..]` is what rustc would have been given, the cwd is the
//! workspace root, and a workspace member's crate root is a relative path.
//!
//! One unit in, one rustc run out. The argv cargo built is passed through
//! UNCHANGED except for three appended flags — `--extern sensorium_rt=<rlib>`,
//! `-L dependency=<the rlib's directory>` and
//! `--remap-path-prefix=<mirror>=<workspace>` — which is why `file!()`, panic
//! locations, backtraces and dep-info all still say what a plain build says.

use std::collections::BTreeSet;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use sensorium_transform::{transform, Manifest};

use crate::args::{self, Plan, Unit};
use crate::fallback::{self, manifest_path, write_manifest};
use crate::mirror::{self, Lock, Rewrite};
use crate::modtree::{self, DiskFs};
use crate::rt_build::{self, Panic};
use crate::sha256;

/// Run the wrapper. Returns the exit code to leave with.
pub fn run(rustc: &str, args: &[String]) -> i32 {
    match args::plan(args) {
        Plan::PassThrough(_) => passthrough(rustc, args),
        Plan::Fallback(unit, reason) => {
            declare_fallback(&unit, reason);
            passthrough(rustc, args)
        }
        Plan::Instrument(unit) => match instrument(rustc, args, &unit) {
            Ok(code) => code,
            Err(e) => {
                // The unit is about to be compiled UNINSTRUMENTED. Any manifest
                // this wrapper already wrote still says `fell_back: false`, and
                // a coverage check would count a unit that recorded nothing as
                // one that recorded everything.
                declare_fallback(
                    &unit,
                    &format!("wrapper: {}", e.lines().next().unwrap_or("error")),
                );
                passthrough(rustc, args)
            }
        },
    }
}

/// Both channels, always: the manifest a check reads, and the build log a
/// person reads.
fn declare_fallback(unit: &Unit, reason: &str) {
    fallback::announce(unit, reason);
    if let Err(e) = record_fallback(unit, reason) {
        eprintln!(
            "sensorium: could not record the fallback for {} ({}): {e}",
            unit.crate_name, unit.metadata
        );
    }
}

/// Patch or write the manifest. The target directory is recomputed from the
/// environment rather than taken from [`Env`], because the failure being
/// recorded may be that [`read_env`] itself refused.
fn record_fallback(unit: &Unit, reason: &str) -> Result<(), String> {
    let ws = std::env::current_dir().map_err(|e| format!("cannot read cwd: {e}"))?;
    let target = target_dir(&ws);
    fallback::mark_fallen_back(&manifest_path(&target, &unit.metadata), unit, reason)
}

/// Run rustc exactly as cargo asked, from cargo's own cwd.
fn passthrough(rustc: &str, args: &[String]) -> i32 {
    Command::new(rustc)
        .args(args)
        .status()
        .map_or(101, |s| s.code().unwrap_or(101))
}

fn target_dir(ws: &Path) -> PathBuf {
    std::env::var_os("SENSORIUM_TARGET").map_or_else(|| ws.join("target"), PathBuf::from)
}

/// What the driver told the wrapper through the environment.
struct Env {
    ws: PathBuf,
    target: PathBuf,
    rt_dir: PathBuf,
    tool_hash: String,
}

fn read_env(ws: &Path) -> Result<Env, String> {
    let rt_dir = std::env::var_os("SENSORIUM_RT_DIR")
        .map(PathBuf::from)
        .ok_or_else(|| "SENSORIUM_RT_DIR is unset: the driver did not set up linkage".to_owned())?;
    let tool_hash = std::env::var("SENSORIUM_TOOL_HASH").map_err(|_| {
        "SENSORIUM_TOOL_HASH is unset: the driver did not set up linkage".to_owned()
    })?;
    Ok(Env {
        ws: ws.to_path_buf(),
        target: target_dir(ws),
        rt_dir,
        tool_hash,
    })
}

fn instrument(rustc: &str, args: &[String], unit: &Unit) -> Result<i32, String> {
    let ws = std::env::current_dir().map_err(|e| format!("cannot read cwd: {e}"))?;
    let env = read_env(&ws)?;
    let sens = env.target.join("sensorium");

    // The runtime variant this unit can link. `unwind` was built by the driver;
    // `abort` is built here, the first time any unit asks for it, under its own
    // lock so sixteen wrappers meeting it at once build it once.
    let panic = Panic::for_unit(unit.panic_abort);
    let rlib = rt_build::ensure(&env.rt_dir, rustc, panic, crate::rt_src::FILES)?;

    let walk = modtree::walk(&DiskFs { root: &env.ws }, &unit.crate_root);
    let root_for_read = env.ws.clone();
    let UnitPlan {
        mut manifest,
        rewrites,
    } = build_unit(
        &move |rel: &str| std::fs::read_to_string(root_for_read.join(rel)).ok(),
        &walk,
        unit,
    );

    let manifest_file = manifest_path(&env.target, &unit.metadata);
    write_manifest(&manifest_file, &manifest)?;

    // ONE MIRROR PER UNIT, keyed by `-C metadata` (findings §5.22), under one
    // `flock` held across the materialise AND the rustc run (D2): the compile
    // reads the tree the materialise just wrote, so releasing between them
    // would let a concurrent run of the same unit rewrite it mid-compile.
    let mirror_dir = sens.join("mirror").join(&unit.metadata);
    let _lock = Lock::acquire(&sens.join("mirror").join(format!("{}.lock", unit.metadata)))
        .map_err(|e| format!("mirror lock: {e}"))?;
    mirror::materialise(
        &env.ws,
        &mirror_dir,
        &sens.join("cache").join(&unit.metadata),
        &env.tool_hash,
        &rewrites,
    )
    .map_err(|e| format!("mirror: {e}"))?;

    let mut instrumented: Vec<String> = args.to_vec();
    instrumented.push("--extern".to_owned());
    instrumented.push(format!("sensorium_rt={}", rlib.display()));
    // BOTH, and the search path is the load-bearing one for a unit whose
    // DEPENDENCIES are instrumented. `--extern` binds a name this unit may
    // write; `sensorium_rt` is a TRANSITIVE crate for anything that merely uses
    // an instrumented workspace crate, and rustc resolves a transitive crate
    // through the `-L dependency` search paths.
    //
    // Measured 2026-09-03 on the bloomery clone: `bloomery-daemon`'s units
    // failed `E0463: can't find crate for bloomery_core` -- the daemon's own
    // rewritten crate root binds `sensorium_rt`, but the FIRST item of a
    // submodule is `use bloomery_core::journal::Journal;`, and resolving
    // `bloomery_core`'s instrumented rmeta needs ITS `sensorium_rt`, which
    // `--extern` alone does not supply. The probe workspace passed the same
    // shape by resolver-order luck. Plan decision D1 is amended to say both
    // flags; RUSTDOCFLAGS has carried both since the doctest defect.
    //
    // No single-candidate hazard: this directory is `<rt dir>/<panic
    // strategy>/`, which the driver and `rt_build::ensure` fill with exactly
    // one `libsensorium_rt.rlib` and nothing else, because the runtime has no
    // dependencies at all (D1).
    instrumented.push("-L".to_owned());
    instrumented.push(format!(
        "dependency={}",
        rlib.parent().unwrap_or_else(|| Path::new(".")).display()
    ));
    // MEASURED, not belt and braces (findings §5.21): rustc records the
    // compilation directory in DWARF (`DW_AT_comp_dir`), and that directory is
    // the mirror. `file!()` and panic locations survive the mirror without this
    // flag; std's backtrace printer resolves frames against comp_dir, and does
    // not.
    instrumented.push(format!(
        "--remap-path-prefix={}={}",
        mirror_dir.display(),
        env.ws.display()
    ));

    let out = Command::new(rustc)
        .args(&instrumented)
        .current_dir(&mirror_dir)
        .stdin(Stdio::inherit())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("cannot run rustc: {e}"))?;
    if out.status.success() {
        // Captured only so a failure can be withheld from cargo before it
        // parses it; on success every byte is forwarded verbatim, warnings
        // included.
        let _ = std::io::stdout().write_all(&out.stdout);
        let _ = std::io::stderr().write_all(&out.stderr);
        return Ok(0);
    }

    let stderr = String::from_utf8_lossy(&out.stderr);
    let reason = format!("rustc: {}", fallback::first_error_line(&stderr));
    fallback::announce(unit, &reason);
    manifest.fell_back = true;
    manifest.fallback_reason = Some(reason);
    write_manifest(&manifest_file, &manifest)?;
    Ok(passthrough(rustc, args))
}

/// The manifest and the rewrites for one unit: everything the wrapper decides
/// before it touches the filesystem, so it can be tested without one.
pub struct UnitPlan {
    pub manifest: Manifest,
    pub rewrites: Vec<Rewrite>,
}

/// Transform every file of a unit, in the walk's order (crate root FIRST).
///
/// Site indices run contiguously across the unit's files from 0 — spec §2.4
/// packs a site id as `unit_id:8 | site:24`, so a unit's sites must be one
/// range, not one range per file. A file that cannot be read or cannot be
/// parsed goes to `unreached_files` and is left unrewritten; the mirror then
/// symlinks the original, so the unit still compiles minus those guards.
pub fn build_unit(
    read: &dyn Fn(&str) -> Option<String>,
    walk: &modtree::Walk,
    unit: &Unit,
) -> UnitPlan {
    let mut manifest = Manifest::new(&unit.metadata, &unit.crate_name, &unit.crate_type);
    manifest.unreached_files.clone_from(&walk.unreached);
    let mut rewrites: Vec<Rewrite> = Vec::new();
    let mut next_site: u32 = 0;
    for (i, rel) in walk.files.iter().enumerate() {
        let Some(source) = read(rel) else {
            manifest.unreached_files.push(rel.clone());
            continue;
        };
        match transform(&source, rel, &unit.metadata, next_site, i == 0) {
            Ok(t) => {
                next_site += u32::try_from(t.sites.len()).unwrap_or(u32::MAX);
                manifest.add_file(rel, &t);
                let source_hash = sha256::hex(source.as_bytes());
                // The bytes a trace's `firstlineno` values refer to. Rung 1
                // left this empty, so nothing in a trace pinned the source it
                // was recorded against (findings §5.3).
                manifest
                    .source_hashes
                    .insert(rel.clone(), source_hash.clone());
                rewrites.push(Rewrite {
                    rel: rel.clone(),
                    content: t.source,
                    source_hash,
                });
            }
            Err(_) => manifest.unreached_files.push(rel.clone()),
        }
    }
    dedup(&mut manifest.unreached_files);
    // The crate root is where `__SENSORIUM_UNIT` lives. If it could not be
    // rewritten but its children were, every guard in the unit references a
    // static that does not exist: a guaranteed rustc failure, a guaranteed
    // fallback, and the unit compiled twice to end up where doing nothing would
    // have left it. Instrument all of a unit or none of it.
    let root_rewritten = walk
        .files
        .first()
        .is_some_and(|root| rewrites.first().is_some_and(|r| &r.rel == root));
    if !root_rewritten {
        rewrites.clear();
        manifest.files.clear();
        manifest.skipped.clear();
        manifest.spawns.clear();
        manifest.source_hashes.clear();
        manifest.appended_line.clear();
    }
    UnitPlan { manifest, rewrites }
}

fn dedup(v: &mut Vec<String>) {
    let mut seen = BTreeSet::new();
    v.retain(|s| seen.insert(s.clone()));
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unit() -> Unit {
        Unit {
            crate_name: "demo".to_owned(),
            crate_type: "lib".to_owned(),
            metadata: "deadbeef".to_owned(),
            crate_root: "a/src/lib.rs".to_owned(),
            panic_abort: false,
        }
    }

    fn plan_of(files: &[(&str, &str)], unreached: &[&str]) -> UnitPlan {
        let map: std::collections::BTreeMap<String, String> = files
            .iter()
            .map(|(p, c)| ((*p).to_owned(), (*c).to_owned()))
            .collect();
        let walk = modtree::Walk {
            files: files.iter().map(|(p, _)| (*p).to_owned()).collect(),
            unreached: unreached.iter().map(|s| (*s).to_owned()).collect(),
        };
        build_unit(&move |rel: &str| map.get(rel).cloned(), &walk, &unit())
    }

    fn json(plan: &UnitPlan) -> serde_json::Value {
        serde_json::from_str(&plan.manifest.to_json().unwrap()).unwrap()
    }

    #[test]
    fn the_manifest_has_the_wire_shape_the_converter_reads() {
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m;\npub fn root() {}\n"),
                (
                    "a/src/m.rs",
                    "pub fn one() {}\npub const fn two() -> u8 { 2 }\n",
                ),
            ],
            &["a/src/ghost.rs"],
        );
        let v = json(&plan);
        assert_eq!(v["unit"], "deadbeef");
        assert_eq!(v["crate_name"], "demo");
        assert_eq!(v["crate_type"], "lib");
        assert_eq!(v["fell_back"], false);
        assert_eq!(v["fallback_reason"], serde_json::Value::Null);
        assert_eq!(v["unreached_files"], serde_json::json!(["a/src/ghost.rs"]));
        // Keyed by the ORIGINAL workspace-relative path, never a mirror path.
        assert_eq!(v["files"]["a/src/lib.rs"][0]["qualname"], "root");
        assert_eq!(v["files"]["a/src/lib.rs"][0]["site"], 0);
        assert_eq!(v["files"]["a/src/m.rs"][0]["qualname"], "one");
        assert_eq!(v["files"]["a/src/m.rs"][0]["site"], 1);
        // The `const fn` is declared, not silently absent.
        assert_eq!(v["skipped"][0]["reason"], "const");
        assert_eq!(v["appended_line"]["a/src/lib.rs"], false);
    }

    /// Rung 1 shipped `source_hashes: {}` in every trace, so nothing pinned the
    /// source a `firstlineno` referred to (findings §5.3).
    #[test]
    fn every_rewritten_file_is_hashed_by_its_original_bytes() {
        let root = "mod m;\npub fn root() {}\n";
        let child = "pub fn one() {}\n";
        let plan = plan_of(&[("a/src/lib.rs", root), ("a/src/m.rs", child)], &[]);
        let v = json(&plan);
        assert_eq!(
            v["source_hashes"]["a/src/lib.rs"],
            serde_json::Value::String(sha256::hex(root.as_bytes()))
        );
        assert_eq!(
            v["source_hashes"]["a/src/m.rs"],
            serde_json::Value::String(sha256::hex(child.as_bytes()))
        );
        // The hash is of the ORIGINAL bytes, not of what was spliced.
        assert_ne!(
            v["source_hashes"]["a/src/lib.rs"],
            serde_json::Value::String(sha256::hex(plan.rewrites[0].content.as_bytes()))
        );
    }

    #[test]
    fn site_indices_run_contiguously_across_the_units_files() {
        // Spec §2.4 packs `unit_id:8 | site:24`, so a unit's sites are ONE
        // range. Number per file and the second file restarts at 0, colliding
        // with the first file's sites in every downstream join.
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m;\nfn a() {}\nfn b() {}\n"),
                ("a/src/m.rs", "fn c() {}\nfn d() {}\n"),
            ],
            &[],
        );
        let mut sites: Vec<u32> = plan
            .manifest
            .files
            .values()
            .flatten()
            .map(|s| s.site)
            .collect();
        sites.sort_unstable();
        assert_eq!(sites, [0, 1, 2, 3]);
    }

    #[test]
    fn only_the_crate_root_gets_the_unit_static() {
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m;\nfn a() {}\n"),
                ("a/src/m.rs", "fn c() {}\n"),
            ],
            &[],
        );
        let root = &plan.rewrites[0];
        let child = &plan.rewrites[1];
        assert_eq!(root.rel, "a/src/lib.rs");
        assert!(
            root.content
                .contains("__SENSORIUM_UNIT: ::sensorium_rt::Unit"),
            "{}",
            root.content
        );
        assert!(
            !child.content.contains("static __SENSORIUM_UNIT"),
            "{}",
            child.content
        );
        assert!(
            child.content.contains("::sensorium_rt::enter"),
            "{}",
            child.content
        );
    }

    #[test]
    fn the_unit_static_carries_this_units_metadata() {
        let plan = plan_of(&[("a/src/lib.rs", "fn a() {}\n")], &[]);
        assert!(
            plan.rewrites[0].content.contains("Unit::new(\"deadbeef\")"),
            "{}",
            plan.rewrites[0].content
        );
    }

    #[test]
    fn an_unparseable_file_is_unreached_and_is_not_rewritten() {
        let plan = plan_of(
            &[("a/src/lib.rs", "fn a() {}\n"), ("a/src/bad.rs", "fn ( {")],
            &[],
        );
        assert_eq!(plan.manifest.unreached_files, ["a/src/bad.rs"]);
        assert_eq!(plan.rewrites.len(), 1);
        assert_eq!(plan.rewrites[0].rel, "a/src/lib.rs");
    }

    #[test]
    fn a_unit_whose_crate_root_cannot_be_rewritten_is_left_wholly_alone() {
        // The root does not parse, so it gets no `__SENSORIUM_UNIT` static.
        // Rewriting the child anyway would splice guards referencing a static
        // that is not there: rustc fails, the fallback fires, and the unit is
        // compiled twice to end up exactly where doing nothing would.
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m; fn ( {"),
                ("a/src/m.rs", "fn c() {}\n"),
            ],
            &[],
        );
        assert!(plan.rewrites.is_empty());
        assert!(plan.manifest.files.is_empty());
        assert!(plan.manifest.source_hashes.is_empty());
        assert_eq!(plan.manifest.unreached_files, ["a/src/lib.rs"]);
    }

    #[test]
    fn a_file_the_reader_cannot_open_is_unreached_not_silently_skipped() {
        let walk = modtree::Walk {
            files: vec!["a/src/lib.rs".to_owned(), "a/src/gone.rs".to_owned()],
            unreached: vec![],
        };
        let plan = build_unit(
            &|rel: &str| (rel == "a/src/lib.rs").then(|| "fn a() {}\n".to_owned()),
            &walk,
            &unit(),
        );
        assert_eq!(plan.manifest.unreached_files, ["a/src/gone.rs"]);
    }

    #[test]
    fn dedup_keeps_first_occurrence_order() {
        let mut v = vec!["b".to_owned(), "a".to_owned(), "b".to_owned()];
        dedup(&mut v);
        assert_eq!(v, ["b", "a"]);
    }
}
