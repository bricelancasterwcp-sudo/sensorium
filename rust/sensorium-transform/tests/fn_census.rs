//! `fn_items` answers from the CENSUS walk (`sensorium-transform` 0.4.2), and
//! answers exactly what the splicing transform answered before it.
//!
//! Design 2026-09-07 §6, ruling R7. The driver's `--focus` resolver asks this
//! crate "which functions would you instrument, and which would you skip and
//! why?" for every `.rs` file of a workspace, before cargo is invoked at all.
//! Until 0.4.2 it got that answer by running the WHOLE transform on every file
//! -- computing every splice, assembling every rewritten source, checking every
//! line count -- and throwing the source away. 0.4.2 runs the same visitor with
//! its splicing half switched off.
//!
//! **The whole risk of that change is a second classifier**: a census that
//! decides eligibility on its own would let the driver accept a `--focus` the
//! transform then silently ignores, and the trace would come back empty with no
//! refusal. So the pin here is DIFFERENTIAL and not a golden: [`transform_route`]
//! below is 0.4.1's `fn_items`, written out in the test, and every case asserts
//! the two routes name the same items in the same order.
//!
//! Three corpora, none of them a box path: every golden pair's input, this
//! repository's own `rust/` tree (real files, a few thousand fn items), and --
//! when `SENSORIUM_BLOOMERY_CLONE` names it -- the pinned clone `tests/census.rs`
//! measures E2 on. The clone pass SKIPS BY NAME when the variable is unset; it
//! is never a silent pass.
//!
//! Neither test writes anything, and neither starts a subprocess.

mod common;

use std::fs;
use std::path::{Path, PathBuf};

use common::{read, read_compile_fail, read_focus, CASES, COMPILE_FAIL_CASES, FILE, FOCUS_CASES};

use sensorium_transform::{fn_items, transform, FnItem, Focus, SiteKind};

/// `fn_items` exactly as `sensorium-transform` 0.4.1 computed it: the whole
/// splicing transform, run for its `sites` and `skipped` lists, with the
/// rewritten source discarded.
///
/// Written out here rather than imported, on purpose. This is the ANSWER under
/// comparison -- the one the driver's resolver gave for every focus resolved
/// before 0.4.2 -- so it has to survive the implementation it is checking. A
/// test that called the new `fn_items` twice would pin nothing.
fn transform_route(source: &str, file: &str) -> Vec<FnItem> {
    let Ok(t) = transform(source, file, "", 0, false, &Focus::EMPTY) else {
        // A file that does not parse yields no items by either route: it is not
        // instrumented either, so it holds nothing a focus could select.
        return Vec::new();
    };
    let mut items: Vec<FnItem> = t
        .sites
        .iter()
        .filter(|site| site.kind == SiteKind::Fn)
        .map(|site| FnItem {
            qualname: site.qualname.clone(),
            skipped: None,
        })
        .collect();
    items.extend(t.skipped.iter().map(|s| FnItem {
        qualname: s.qualname.clone(),
        skipped: Some(s.reason),
    }));
    items
}

/// Assert the two routes agree on one source, and return how many items they
/// agreed on -- so a corpus pass can say it measured something rather than
/// having walked an empty directory.
fn agree(source: &str, file: &str, what: &str) -> usize {
    let census = fn_items(source, file);
    let splicing = transform_route(source, file);
    assert_eq!(
        census, splicing,
        "{what}: the census route and the splicing transform name different items"
    );
    census.len()
}

// ---------------------------------------------------------------------------
// The goldens
// ---------------------------------------------------------------------------

#[test]
fn every_golden_input_names_the_same_items_by_either_route() {
    let mut items = 0;
    for case in CASES {
        items += agree(&read(case, "in"), FILE, case);
        // The `.out.rs` too: an already-transformed file is valid Rust with
        // fn items of its own, and it is the one shape in this repository
        // whose bodies are full of the fragments the splicing route emits.
        items += agree(&read(case, "out"), FILE, &format!("{case}.out"));
    }
    for (case, _) in FOCUS_CASES {
        items += agree(&read_focus(case, "in"), FILE, case);
    }
    for (case, _, _) in COMPILE_FAIL_CASES {
        items += agree(&read_compile_fail(case), FILE, case);
    }
    assert!(items > 100, "the golden corpus named only {items} items");
    println!("goldens: {items} items agreed");
}

/// The census route's own edges, stated rather than left to the corpora: a file
/// that does not parse, an empty file, and every skip reason at once.
#[test]
fn the_two_routes_agree_on_the_shapes_a_corpus_may_not_hold() {
    assert!(fn_items("fn (", FILE).is_empty(), "an unparseable file");
    agree("fn (", FILE, "unparseable");
    agree("", FILE, "empty");
    agree("// nothing but a comment\n", FILE, "comment only");
    agree(
        "mod m {\n    pub fn f() {}\n    pub async fn g() {}\n    pub const fn c() {}\n\
         \n    extern \"C\" fn e() {}\n}\n\
         macro_rules! mac {\n    () => {\n        fn inside() {}\n    };\n}\n\
         #[test]\nfn t() {}\n#[bench]\nfn b(_: &mut u8) {}\n\
         fn main() {}\nstruct S;\nimpl S {\n    fn k(&self) -> u8 { 1 }\n}\n\
         trait T {\n    fn d(&self) {}\n    fn bodiless(&self);\n}\n",
        FILE,
        "every reason at once",
    );
}

// ---------------------------------------------------------------------------
// Real trees
// ---------------------------------------------------------------------------

/// Every `.rs` under `dir`, recursively, in a deterministic order.
///
/// A symlinked directory is not followed (a loop would turn a read-only walk
/// into a hang), and a `target` directory is never entered: it is build output,
/// it is not a unit of any workspace, and on this box it is measured in
/// gigabytes.
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
            if path.file_name().is_some_and(|n| n == "target") {
                continue;
            }
            walk_rs(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

/// Assert both routes over a whole tree, returning `(files, items)`.
fn agree_over_tree(root: &Path) -> (usize, usize) {
    let mut files = Vec::new();
    walk_rs(root, &mut files);
    let mut items = 0;
    for path in &files {
        let Ok(source) = fs::read_to_string(path) else {
            continue;
        };
        let rel = path.strip_prefix(root).unwrap_or(path).to_string_lossy();
        items += agree(&source, &rel, &rel);
    }
    (files.len(), items)
}

/// This repository's own `rust/` tree: three crates, their tests, and every
/// golden fixture in them. No environment variable, no clone, no box path --
/// the corpus travels with the checkout, so this is the pass that runs on every
/// machine.
#[test]
fn the_repositorys_own_rust_tree_names_the_same_items_by_either_route() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("the crate directory has a parent")
        .to_path_buf();
    let (files, items) = agree_over_tree(&root);
    assert!(files > 40, "the rust/ tree held only {files} .rs files");
    assert!(items > 1000, "the rust/ tree named only {items} items");
    println!("rust/: {files} files, {items} items agreed");
}

/// The pinned bloomery clone `tests/census.rs` measures E2 on, when
/// `SENSORIUM_BLOOMERY_CLONE` names it. The 2051 eligible fn items that test
/// pins are the widest corpus this crate has, and every one of them is a
/// qualname the driver's resolver would have to match.
///
/// **The variable is the only way to name it** (plan §Global Constraints: no
/// box path is committed), so an unset variable is a SKIP with the reason in
/// this test's own name, never a pass over nothing.
#[test]
fn the_bloomery_clone_names_the_same_items_by_either_route_or_is_skipped_by_name() {
    let Some(root) = std::env::var_os("SENSORIUM_BLOOMERY_CLONE")
        .filter(|p| !p.is_empty())
        .map(PathBuf::from)
    else {
        println!("SKIPPED: SENSORIUM_BLOOMERY_CLONE is unset; no clone to walk");
        return;
    };
    let (files, items) = agree_over_tree(&root.join("crates"));
    assert!(files > 100, "the clone held only {files} .rs files");
    println!("clone: {files} files, {items} items agreed");
}
