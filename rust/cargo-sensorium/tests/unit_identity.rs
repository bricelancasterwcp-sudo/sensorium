//! One crate root, several units: each must carry its OWN `-C metadata`.
//!
//! Cargo compiles `src/lib.rs` as `--crate-type lib` and again with `--test`,
//! each with its own `-C metadata`. The `__SENSORIUM_UNIT` static the
//! transformer appends names that metadata, so the two units need different
//! bytes at the same workspace-relative path. Rung 1 shared one mirror keyed by
//! source hash alone: the first writer won, the second compiled a static naming
//! its twin, and every event that unit recorded was attributed to the wrong
//! unit in a build that was green and a trace that looked healthy
//! (findings §5.22).
//!
//! The check counts what it checked and requires that count to be non-zero.
//! Rung 1's version asserted only that a bad list was empty, so it passed
//! vacuously when it had found nothing to look at (findings §5.29).

mod common;

use std::path::Path;
use std::process::Command;

use common::{bogus_runtime, Scratch};

/// Compile one unit through the wrapper. The runtime rlib is deliberately
/// bogus, so rustc rejects the instrumented build and the wrapper falls back —
/// the mirror it materialised first is what this test is about, and reaching it
/// costs milliseconds instead of a runtime build.
fn compile_unit(s: &Scratch, metadata: &str, extra: &[&str]) {
    let out = s.p(&format!("out-{metadata}"));
    std::fs::create_dir_all(&out).unwrap();
    let status = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .arg(common::rustc())
        .args(["--crate-name", "ident", "--edition=2021", "src/lib.rs"])
        .args(extra)
        .args(["-C", &format!("metadata={metadata}"), "-C", "debuginfo=0"])
        .arg("--out-dir")
        .arg(&out)
        .current_dir(s.p("ws"))
        .env("SENSORIUM_TARGET", s.p("target"))
        .env("SENSORIUM_RT_DIR", s.p("rt"))
        .env("SENSORIUM_TOOL_HASH", "identhash")
        .status()
        .expect("run the wrapper");
    let _ = status;
}

#[test]
fn two_units_of_one_crate_root_each_get_their_own_metadata() {
    let s = Scratch::new("two-units");
    s.write("ws/src/lib.rs", "pub fn f() -> u8 { 7 }\n");
    bogus_runtime(&s, &s.p("rt"));

    compile_unit(&s, "aaaa1111", &["--crate-type", "lib"]);
    compile_unit(&s, "bbbb2222", &["--test"]);

    let a = std::fs::read_to_string(s.p("target/sensorium/mirror/aaaa1111/src/lib.rs"))
        .expect("the lib unit's mirror");
    let b = std::fs::read_to_string(s.p("target/sensorium/mirror/bbbb2222/src/lib.rs"))
        .expect("the test unit's mirror");

    assert!(
        a.contains("Unit::new(\"aaaa1111\")"),
        "lib unit static: {a}"
    );
    assert!(
        b.contains("Unit::new(\"bbbb2222\")"),
        "test unit static: {b}"
    );
    // The failure this pins is not "b has no static" -- it is "b carries a's
    // metadata", which reads as a perfectly healthy build.
    assert!(
        !b.contains("aaaa1111"),
        "the test unit inherited the lib's identity: {b}"
    );
    assert!(
        !a.contains("bbbb2222"),
        "the lib unit inherited the test's identity: {a}"
    );
    assert_ne!(a, b);

    // Both units also get their own manifest, keyed the same way.
    assert_eq!(
        common::manifest(&s.p("target"), "aaaa1111")["unit"],
        "aaaa1111"
    );
    assert_eq!(
        common::manifest(&s.p("target"), "bbbb2222")["crate_type"],
        "test"
    );
}

/// The same shape one level up, over every crate root in every mirror: a
/// mirrored crate root must name the unit whose mirror it is in. Rung 1's
/// version of this check counted nothing and passed.
#[test]
fn every_units_mirror_carries_its_own_metadata() {
    let s = Scratch::new("all-units");
    s.write(
        "ws/src/lib.rs",
        "mod helper;\npub fn f() -> u8 { helper::g() }\n",
    );
    s.write("ws/src/helper.rs", "pub fn g() -> u8 { 7 }\n");
    bogus_runtime(&s, &s.p("rt"));

    for metadata in ["1111aaaa", "2222bbbb", "3333cccc"] {
        compile_unit(&s, metadata, &["--crate-type", "lib"]);
    }

    let mirrors = s.p("target/sensorium/mirror");
    let mut checked = 0usize;
    let mut wrong: Vec<String> = Vec::new();
    for entry in std::fs::read_dir(&mirrors).expect("a mirror directory") {
        let dir = entry.unwrap().path();
        if !dir.is_dir() {
            continue;
        }
        let metadata = dir.file_name().unwrap().to_string_lossy().into_owned();
        let root = dir.join("src/lib.rs");
        let text = std::fs::read_to_string(&root)
            .unwrap_or_else(|e| panic!("no crate root at {}: {e}", root.display()));
        checked += 1;
        if !text.contains(&format!("Unit::new(\"{metadata}\")")) {
            wrong.push(metadata);
        }
    }
    assert!(
        checked > 0,
        "no crate root was checked, so this check proves nothing"
    );
    assert_eq!(checked, 3, "one mirror per unit");
    assert!(wrong.is_empty(), "mirrors naming the wrong unit: {wrong:?}");

    // And one LOCK per unit (plan decision D2). A single shared lock would
    // serialise a sixteen-way build on nothing: per-unit mirrors have no
    // shared mutable state.
    let mut locks: Vec<String> = std::fs::read_dir(&mirrors)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .filter(|n| n.ends_with(".lock"))
        .collect();
    locks.sort();
    assert_eq!(locks, ["1111aaaa.lock", "2222bbbb.lock", "3333cccc.lock"]);
}

/// The child files of a unit are rewritten too, and they do NOT get a static —
/// they reference the crate root's.
#[test]
fn a_units_child_module_is_rewritten_in_the_same_mirror() {
    let s = Scratch::new("children");
    s.write(
        "ws/src/lib.rs",
        "mod helper;\npub fn f() -> u8 { helper::g() }\n",
    );
    s.write("ws/src/helper.rs", "pub fn g() -> u8 { 7 }\n");
    bogus_runtime(&s, &s.p("rt"));

    compile_unit(&s, "cccc3333", &["--crate-type", "lib"]);

    let helper = std::fs::read_to_string(s.p("target/sensorium/mirror/cccc3333/src/helper.rs"))
        .expect("the child module's mirror");
    assert!(helper.contains("::sensorium_rt::enter"), "{helper}");
    assert!(!helper.contains("static __SENSORIUM_UNIT"), "{helper}");
    // And the manifest knows both files.
    let m = common::manifest(&s.p("target"), "cccc3333");
    assert!(m["files"]["src/lib.rs"].is_array(), "{m}");
    assert!(m["files"]["src/helper.rs"].is_array(), "{m}");
    assert!(m["source_hashes"]["src/helper.rs"].is_string(), "{m}");
}

/// The mirror is a symlink tree, not a copy: a workspace file this unit did not
/// rewrite is one symlink to the original.
#[test]
fn the_mirror_symlinks_everything_it_did_not_rewrite() {
    let s = Scratch::new("symlinks");
    s.write("ws/src/lib.rs", "pub fn f() -> u8 { 7 }\n");
    s.write("ws/Cargo.toml", "[package]\n");
    s.write("ws/assets/data.txt", "not rust\n");
    bogus_runtime(&s, &s.p("rt"));

    compile_unit(&s, "dddd4444", &["--crate-type", "lib"]);

    let mirror = s.p("target/sensorium/mirror/dddd4444");
    assert!(std::fs::symlink_metadata(mirror.join("Cargo.toml"))
        .unwrap()
        .is_symlink());
    assert!(std::fs::symlink_metadata(mirror.join("assets"))
        .unwrap()
        .is_symlink());
    assert!(!std::fs::symlink_metadata(mirror.join("src/lib.rs"))
        .unwrap()
        .is_symlink());
    assert_eq!(
        std::fs::read_link(mirror.join("Cargo.toml")).unwrap(),
        s.p("ws/Cargo.toml")
    );
    let _ = Path::new("");
}
