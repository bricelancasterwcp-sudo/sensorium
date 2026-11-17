//! Locate `sensorium-rt`'s sources and embed them in this binary.
//!
//! Plan decision D1: the driver writes these bytes out and compiles them with
//! one bare `rustc` line. `include_str!` of `../sensorium-rt/src/...` only
//! works in this workspace. An installed crate has no sibling, so the sources
//! shipped in `rt-src/` (and, when present, the path-dep sibling) are copied
//! into `OUT_DIR` and `src/rt_src.rs` includes the generated list.
//!
//! Watching the sibling DIRECTORY closes a hole rustc's dep-info cannot: add
//! `sensorium-rt/src/new_module.rs` and declare it in the crate root, and
//! nothing about this crate's own files has changed. A new file in that
//! directory is a change to it.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=rt-src");
    println!("cargo:rerun-if-changed=../sensorium-rt/src");

    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let src = locate_rt_src(&manifest_dir);
    let dest = out_dir.join("rt-src");
    fs::create_dir_all(&dest).unwrap_or_else(|e| panic!("cannot create {}: {e}", dest.display()));

    let mut names: Vec<String> = fs::read_dir(&src)
        .unwrap_or_else(|e| panic!("cannot read {}: {e}", src.display()))
        .map(|e| e.unwrap())
        .filter(|e| e.path().extension().and_then(|s| s.to_str()) == Some("rs"))
        .map(|e| {
            e.file_name()
                .into_string()
                .expect("utf-8 runtime source name")
        })
        .collect();
    names.sort();
    assert!(
        names.iter().any(|n| n == "lib.rs"),
        "{} has no lib.rs",
        src.display()
    );
    // `lib.rs` first: that is the file the bare `rustc` line is pointed at.
    names.sort_by(|a, b| {
        (b.as_str() == "lib.rs")
            .cmp(&(a.as_str() == "lib.rs"))
            .then(a.cmp(b))
    });

    let mut gen = String::from(
        "/// `(path under src/, contents)`. `lib.rs` is first, which is also the file the\n\
         /// bare `rustc` line is pointed at.\n\
         pub const FILES: &[(&str, &str)] = &[\n",
    );
    for name in &names {
        let from = src.join(name);
        let to = dest.join(name);
        fs::copy(&from, &to)
            .unwrap_or_else(|e| panic!("cannot copy {} to {}: {e}", from.display(), to.display()));
        gen.push_str(&format!(
            "    ({name:?}, include_str!(concat!(env!(\"OUT_DIR\"), \"/rt-src/{name}\"))),\n"
        ));
    }
    gen.push_str("];\n");
    fs::write(out_dir.join("rt_embed.rs"), gen)
        .unwrap_or_else(|e| panic!("cannot write rt_embed.rs: {e}"));
}

fn locate_rt_src(manifest_dir: &Path) -> PathBuf {
    let sibling = manifest_dir.join("../sensorium-rt/src");
    if sibling.join("lib.rs").is_file() {
        return sibling;
    }
    let vendored = manifest_dir.join("rt-src");
    if vendored.join("lib.rs").is_file() {
        return vendored;
    }
    panic!(
        "cannot find sensorium-rt sources at {} or {}",
        sibling.display(),
        vendored.display()
    );
}
