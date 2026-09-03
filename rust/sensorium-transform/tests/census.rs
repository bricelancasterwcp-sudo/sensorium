//! E2's identity, measured on a real workspace: the numerator and the
//! denominator come from the same parser, per file and in aggregate.
//!
//! The measurement target is the LOCAL CLONE of bloomery pinned at `e209ed9`
//! (plan §Global Constraints). `/home/brice/workspace/bloomery` itself is
//! read-only for this plan and is never the target here. The clone's path
//! defaults to the one the plan names and is overridable with
//! `SENSORIUM_RUNG2_BLOOMERY`; when it is absent -- CI has no clone -- this test
//! SKIPS BY NAME and says so, because a silently empty property test is worse
//! than none.
//!
//! The default is a measurement location, not configuration: no build reads it,
//! nothing is written to it, and pointing it elsewhere changes only which
//! workspace the identity below is measured over.
//!
//! This test opens files for reading and does nothing else: it creates no
//! directory, writes no file, and never touches `Cargo.lock` or `target/`.
//!
//! Run with `-- --nocapture` to see the numbers.

mod common;

use std::fs;
use std::path::{Path, PathBuf};

use sensorium_transform::{census, transform};

const META: &str = "b100meryb100mery";
const DEFAULT_CLONE: &str = "/mnt/extra/sensorium-rung2/bloomery";

/// The spawn spelling `spawns[..].wrapped` must account for, counted in the raw
/// text by something that is not the transformer.
const LITERAL_SPAWN: &str = "std::thread::spawn(";

fn clone_root() -> PathBuf {
    match std::env::var_os("SENSORIUM_RUNG2_BLOOMERY") {
        Some(p) if !p.is_empty() => PathBuf::from(p),
        _ => PathBuf::from(DEFAULT_CLONE),
    }
}

/// Every `.rs` under `dir`, recursively, in a deterministic order. Symlinked
/// directories are not followed: a loop would turn a read-only walk into a hang.
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

fn collect(root: &Path) -> Vec<PathBuf> {
    let mut files = Vec::new();
    let Ok(crates) = fs::read_dir(root.join("crates")) else {
        return files;
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
    files.sort();
    files
}

fn head(v: &[String]) -> String {
    let shown: Vec<&str> = v.iter().take(8).map(String::as_str).collect();
    if v.len() > shown.len() {
        format!("{shown:#?} (+{} more)", v.len() - shown.len())
    } else {
        format!("{shown:#?}")
    }
}

#[derive(Default)]
struct Totals {
    files: usize,
    fn_items: usize,
    const_fns: usize,
    extern_fns: usize,
    async_fns: usize,
    macro_skips: usize,
    eligible: usize,
    instrumented: usize,
    spawns_wrapped: usize,
    spawns_declared: usize,
    literal_spawns: usize,
}

#[test]
fn the_clone_instruments_every_eligible_fn_without_moving_a_line() {
    let root = clone_root();
    if !root.join("crates").is_dir() {
        eprintln!(
            "SKIP the_clone_instruments_every_eligible_fn_without_moving_a_line: \
             no bloomery clone at {} (set SENSORIUM_RUNG2_BLOOMERY)",
            root.display()
        );
        return;
    }
    let files = collect(&root);
    assert!(
        !files.is_empty(),
        "the clone is present at {} but the walk found no .rs files -- the walk is broken",
        root.display()
    );

    let mut t = Totals::default();
    let mut next_site: u32 = 0;
    let mut unreadable: Vec<String> = Vec::new();
    let mut unparseable: Vec<String> = Vec::new();
    let mut line_moves: Vec<String> = Vec::new();
    let mut reparse_failures: Vec<String> = Vec::new();
    let mut missing_static: Vec<String> = Vec::new();
    let mut per_file_mismatch: Vec<String> = Vec::new();
    let mut appended: Vec<String> = Vec::new();
    let mut spawn_mismatch: Vec<String> = Vec::new();

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
        t.files += 1;
        t.fn_items += c.fn_items;
        t.const_fns += c.const_fns;
        t.extern_fns += c.extern_fns;
        t.async_fns += c.async_fns;
        t.eligible += c.eligible();
        let literal = source.matches(LITERAL_SPAWN).count();
        t.literal_spawns += literal;

        // Every file is transformed BOTH ways: the crate-root static is the rule
        // most likely to break on real trailing comments, so it is exercised on
        // all of them, not just on the handful of real roots.
        for is_crate_root in [false, true] {
            let out = transform(&source, &rel, META, next_site, is_crate_root)
                .unwrap_or_else(|e| panic!("{rel} (crate_root={is_crate_root}): {e}"));
            if out.source.lines().count() != source.lines().count() + usize::from(out.appended_line)
            {
                line_moves.push(format!(
                    "{rel} (crate_root={is_crate_root}): {} -> {}",
                    source.lines().count(),
                    out.source.lines().count()
                ));
            }
            if out.appended_line {
                appended.push(format!("{rel} (crate_root={is_crate_root})"));
            }
            match syn::parse_file(&out.source) {
                Err(e) => reparse_failures.push(format!("{rel} (root={is_crate_root}): {e}")),
                Ok(parsed) => {
                    let declared = parsed.items.iter().any(|item| match item {
                        syn::Item::Static(st) => st.ident == "__SENSORIUM_UNIT",
                        _ => false,
                    });
                    if declared != is_crate_root {
                        missing_static
                            .push(format!("{rel} (root={is_crate_root}): declared={declared}"));
                    }
                }
            }
            if is_crate_root {
                continue;
            }
            t.instrumented += out.sites.len();
            t.macro_skips += out.skipped.iter().filter(|s| s.reason == "macro").count();
            let wrapped = out.spawns.iter().filter(|s| s.wrapped).count();
            t.spawns_wrapped += wrapped;
            t.spawns_declared += out.spawns.len() - wrapped;
            if wrapped != literal {
                spawn_mismatch.push(format!("{rel}: {wrapped} wrapped vs {literal} literal"));
            }
            // PER FILE, not just in aggregate: a file that over-instruments and
            // another that under-instruments would cancel in the sum.
            if out.sites.len() + c.async_fns != c.eligible() {
                per_file_mismatch.push(format!(
                    "{rel}: sites {} + async {} != eligible {}",
                    out.sites.len(),
                    c.async_fns,
                    c.eligible()
                ));
            }
            next_site += u32::try_from(out.sites.len()).expect("site count fits u32");
        }
    }

    println!("clone root:           {}", root.display());
    println!("files walked:         {}", files.len());
    println!("files measured:       {}", t.files);
    println!("fn items (with body): {}", t.fn_items);
    println!("  const fn skipped:   {}", t.const_fns);
    println!("  extern fn skipped:  {}", t.extern_fns);
    println!("  async fn skipped:   {}", t.async_fns);
    println!("  macro_rules bodies: {}", t.macro_skips);
    println!("eligible (E2 denom):  {}", t.eligible);
    println!("instrumented:         {}", t.instrumented);
    println!("spawn sites wrapped:  {}", t.spawns_wrapped);
    println!("spawn sites declared: {}", t.spawns_declared);
    println!("literal `{LITERAL_SPAWN}`: {}", t.literal_spawns);
    println!("line moves:           {}", line_moves.len());
    println!("re-parse failures:    {}", reparse_failures.len());
    println!(
        "appended_line:        {} {}",
        appended.len(),
        head(&appended)
    );

    assert!(unreadable.is_empty(), "unreadable: {}", head(&unreadable));
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
    assert!(
        missing_static.is_empty(),
        "the unit static was not a top-level item exactly when it should be: {}",
        head(&missing_static)
    );
    assert!(
        per_file_mismatch.is_empty(),
        "sites + async != eligible in: {}",
        head(&per_file_mismatch)
    );
    assert!(
        spawn_mismatch.is_empty(),
        "wrapped spawn sites do not match the literal spelling in: {}",
        head(&spawn_mismatch)
    );
    assert_eq!(
        t.instrumented + t.async_fns,
        t.eligible,
        "instrumented + async != eligible over the clone"
    );
    assert_eq!(
        t.spawns_wrapped, t.literal_spawns,
        "every literal `{LITERAL_SPAWN}` must be rewritten, and nothing else"
    );
    // Every real source file contains at least one item, so none of them can
    // reach the appended-final-line shape.
    assert!(
        appended.is_empty(),
        "a real source file needed a final line appended: {}",
        head(&appended)
    );
}
