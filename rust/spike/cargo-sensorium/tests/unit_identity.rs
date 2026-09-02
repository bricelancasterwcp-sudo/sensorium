//! One crate root, several units: each must carry its OWN `-C metadata`.
//!
//! Cargo compiles `src/lib.rs` as `--crate-type lib` and again with `--test`,
//! each with its own `-C metadata`. The `__SENSORIUM_UNIT` static the
//! transformer appends names that metadata, so the two units need different
//! bytes at the same workspace-relative path. With one shared mirror the first
//! writer won and the second compiled a static naming the wrong unit -- silent
//! in E7 and E8, and it mis-attributed every event that unit recorded.

use std::path::{Path, PathBuf};
use std::process::Command;

fn tmpdir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!(
        "sensorium-identity-{}-{}-{name}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&d).unwrap();
    d
}

fn compile_unit(root: &Path, metadata: &str, extra: &[&str]) {
    let out = root.join(format!("out-{metadata}"));
    std::fs::create_dir_all(&out).unwrap();
    let status = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .arg(std::env::var("RUSTC").unwrap_or_else(|_| "rustc".to_owned()))
        .args(["--crate-name", "ident", "--edition=2021", "src/lib.rs"])
        .args(extra)
        .args(["-C", &format!("metadata={metadata}"), "-C", "debuginfo=0"])
        .arg("--out-dir")
        .arg(&out)
        .current_dir(root.join("ws"))
        .env("SENSORIUM_TARGET", root.join("target"))
        .env("SENSORIUM_RT_RLIB", root.join("rt/libsensorium_rt.rlib"))
        .env("SENSORIUM_RT_DEPS", root.join("rt"))
        .env("SENSORIUM_TOOL_HASH", "identhash")
        .status()
        .expect("run the wrapper");
    // rustc will fail (there is no real rt rlib) and the wrapper will fall back;
    // the mirror it materialised first is what this test is about.
    let _ = status;
}

#[test]
fn two_units_of_one_crate_root_each_get_their_own_metadata() {
    let root = tmpdir("two-units");
    std::fs::create_dir_all(root.join("ws/src")).unwrap();
    std::fs::write(root.join("ws/src/lib.rs"), "pub fn f() -> u8 { 7 }\n").unwrap();

    compile_unit(&root, "aaaa1111", &["--crate-type", "lib"]);
    compile_unit(&root, "bbbb2222", &["--test"]);

    let a = std::fs::read_to_string(root.join("target/sensorium/mirror/aaaa1111/src/lib.rs"))
        .expect("the lib unit's mirror");
    let b = std::fs::read_to_string(root.join("target/sensorium/mirror/bbbb2222/src/lib.rs"))
        .expect("the test unit's mirror");

    assert!(a.contains("Unit::new(\"aaaa1111\")"), "lib unit static: {a}");
    assert!(b.contains("Unit::new(\"bbbb2222\")"), "test unit static: {b}");
    // The failure this pins is not "b is missing a static" -- it is "b carries
    // a's metadata", which reads as a perfectly healthy build.
    assert!(!b.contains("aaaa1111"), "the test unit inherited the lib's identity: {b}");
    assert!(!a.contains("bbbb2222"), "the lib unit inherited the test's identity: {a}");

    // Both are real files, one per unit, at the same workspace-relative path.
    assert_ne!(a, b);
    std::fs::remove_dir_all(&root).ok();
}
