//! The property test: run the transformer over every Rust file in bloomery's
//! workspace and check the two invariants that make E7 possible at all --
//! the line count never moves and the result still parses.
//!
//! Bloomery is READ-ONLY for this plan (plan §Global Constraints). This test
//! opens files for reading and does nothing else; it creates no directory,
//! writes no file, and never touches `Cargo.lock` or `target/`.
//!
//! Run with `-- --nocapture` to see the census numbers E2 will use.

use std::fs;
use std::path::{Path, PathBuf};

use sensorium_transform::{census, transform};

const META: &str = "b100meryb100mery";

fn bloomery_root() -> PathBuf {
    if let Ok(p) = std::env::var("SENSORIUM_SPIKE_BLOOMERY") {
        return PathBuf::from(p);
    }
    // rust/spike/sensorium-transform -> rust/spike -> rust -> sensorium -> workspace
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../../bloomery")
}

/// Every `.rs` under `dir`, recursively, in a deterministic order. Symlinked
/// directories are not followed: a loop would turn a read-only walk into a
/// hang, and bloomery has no symlinked source anyway.
fn walk_rs(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<_> = entries.filter_map(Result::ok).collect();
    entries.sort_by_key(std::fs::DirEntry::path);
    for entry in entries {
        let path = entry.path();
        let Ok(meta) = entry.metadata() else { continue };
        if meta.file_type().is_symlink() {
            continue;
        }
        if meta.is_dir() {
            walk_rs(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// The first few of a failure list, so a broken invariant reports a readable
/// diagnosis instead of every file in the workspace.
fn head(v: &[String]) -> String {
    let shown: Vec<&str> = v.iter().take(8).map(String::as_str).collect();
    if v.len() > shown.len() {
        format!("{shown:#?} (+{} more)", v.len() - shown.len())
    } else {
        format!("{shown:#?}")
    }
}

fn collect() -> (PathBuf, Vec<PathBuf>) {
    let root = bloomery_root();
    let mut files = Vec::new();
    let Ok(crates) = fs::read_dir(root.join("crates")) else {
        return (root, files);
    };
    let mut crate_dirs: Vec<PathBuf> = crates
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    crate_dirs.sort();
    for c in crate_dirs {
        walk_rs(&c.join("src"), &mut files);
        walk_rs(&c.join("tests"), &mut files);
    }
    files.sort_by_key(|p| p.to_string_lossy().into_owned());
    (root, files)
}

#[test]
fn transforming_bloomery_never_moves_a_line() {
    let (root, files) = collect();
    if !root.join("crates").is_dir() {
        eprintln!(
            "SKIP: bloomery not found at {} (set SENSORIUM_SPIKE_BLOOMERY)",
            root.display()
        );
        return;
    }
    assert!(
        !files.is_empty(),
        "bloomery is present at {} but the walk found no .rs files -- the walk is broken, \
         and a silently empty property test is worse than none",
        root.display()
    );

    let mut next_site: u32 = 0;
    let mut instrumented = 0usize;
    let mut eligible = 0usize;
    let mut fn_items = 0usize;
    let mut const_fns = 0usize;
    let mut extern_fns = 0usize;
    let mut macro_skips = 0usize;
    let mut eligible_src = 0usize;
    let mut eligible_tests = 0usize;
    let mut files_src = 0usize;
    let mut files_tests = 0usize;
    let mut unreadable: Vec<String> = Vec::new();
    let mut unparseable: Vec<String> = Vec::new();
    let mut line_moves: Vec<String> = Vec::new();
    let mut reparse_failures: Vec<String> = Vec::new();

    for path in &files {
        let rel = path
            .strip_prefix(&root)
            .unwrap_or(path)
            .to_string_lossy()
            .into_owned();
        let Ok(source) = fs::read_to_string(path) else {
            unreadable.push(rel);
            continue;
        };

        let c = census(&source);
        if !c.parsed {
            unparseable.push(rel);
            continue;
        }
        fn_items += c.fn_items;
        const_fns += c.const_fns;
        extern_fns += c.extern_fns;
        eligible += c.eligible();
        // The plan derived E2's floor from "756 items"; the split says where a
        // different denominator would come from.
        if rel.contains("/tests/") {
            eligible_tests += c.eligible();
            files_tests += 1;
        } else {
            eligible_src += c.eligible();
            files_src += 1;
        }

        // Every file is transformed BOTH ways: the crate-root static is the
        // rule most likely to break on real trailing comments, so it is
        // exercised on all of them, not just on the handful of real roots.
        for is_crate_root in [false, true] {
            let t = transform(&source, &rel, META, next_site, is_crate_root)
                .unwrap_or_else(|e| panic!("{rel} (crate_root={is_crate_root}): {e}"));
            if t.source.lines().count() != source.lines().count() {
                line_moves.push(format!(
                    "{rel} (crate_root={is_crate_root}): {} -> {}",
                    source.lines().count(),
                    t.source.lines().count()
                ));
            }
            if let Err(e) = syn::parse_file(&t.source) {
                reparse_failures.push(format!("{rel} (crate_root={is_crate_root}): {e}"));
            }
            if !is_crate_root {
                instrumented += t.sites.len();
                macro_skips += t.skipped.iter().filter(|s| s.reason == "macro").count();
                next_site += u32::try_from(t.sites.len()).expect("site count fits u32");
            }
        }
    }

    println!("bloomery root:        {}", root.display());
    println!("files walked:         {}", files.len());
    println!("fn items (with body): {fn_items}");
    println!("  const fn skipped:   {const_fns}");
    println!("  extern fn skipped:  {extern_fns}");
    println!("  macro_rules bodies: {macro_skips}");
    println!("eligible (E2 denom):  {eligible}");
    println!("  in crates/*/src:    {eligible_src} over {files_src} files");
    println!("  in crates/*/tests:  {eligible_tests} over {files_tests} files");
    println!("instrumented:         {instrumented}");
    println!(
        "unreadable:           {} {}",
        unreadable.len(),
        head(&unreadable)
    );
    println!(
        "unparseable:          {} {}",
        unparseable.len(),
        head(&unparseable)
    );

    assert!(
        unreadable.is_empty(),
        "unreadable files: {}",
        head(&unreadable)
    );
    assert!(
        unparseable.is_empty(),
        "syn could not parse: {}",
        head(&unparseable)
    );
    assert!(
        line_moves.is_empty(),
        "line count moved: {}",
        head(&line_moves)
    );
    assert!(
        reparse_failures.is_empty(),
        "transformed source did not re-parse: {}",
        head(&reparse_failures)
    );
    // Same-parser identity: over a whole real workspace, every eligible fn item
    // got exactly one guard.
    assert_eq!(
        instrumented, eligible,
        "instrumented != eligible over bloomery"
    );
}
