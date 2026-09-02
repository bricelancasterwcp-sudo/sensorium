//! The wrapper's ERROR path, driven end to end through the real binary.
//!
//! Not the rustc-rejected-the-rewrite path (mechanics.sh falsification 1 covers
//! that): this is the path where the WRAPPER itself fails -- a mirror lock that
//! times out, an I/O error, a missing linkage environment -- and the unit is
//! compiled uninstrumented anyway. The manifest has to say so. On bloomery,
//! with ~70 units contending on one mirror lock, this is the failure that
//! actually happens, and a manifest reading `fell_back: false` for a unit that
//! recorded nothing would put a silent lie into E2's numerator.

use std::path::{Path, PathBuf};
use std::process::Command;

fn tmpdir(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!(
        "sensorium-fallback-{}-{}-{name}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&d).unwrap();
    d
}

fn rustc() -> String {
    std::env::var("RUSTC").unwrap_or_else(|_| "rustc".to_owned())
}

/// A one-file crate, plus the argv cargo would hand the wrapper for it.
fn fixture(root: &Path) -> Vec<String> {
    std::fs::create_dir_all(root.join("ws/src")).unwrap();
    std::fs::write(root.join("ws/src/lib.rs"), "pub fn f() -> u8 { 7 }\n").unwrap();
    std::fs::create_dir_all(root.join("out")).unwrap();
    [
        "--crate-name",
        "probe_fallback",
        "--edition=2021",
        "src/lib.rs",
        "--crate-type",
        "lib",
        "-C",
        "metadata=fa11bacc",
        "-C",
        "debuginfo=0",
        "--out-dir",
    ]
    .iter()
    .map(|s| (*s).to_owned())
    .chain([root.join("out").to_string_lossy().into_owned()])
    .collect()
}

fn manifest(root: &Path) -> serde_json::Value {
    let p = root.join("target/sensorium/manifests/fa11bacc.json");
    let text = std::fs::read_to_string(&p)
        .unwrap_or_else(|e| panic!("no manifest at {}: {e}", p.display()));
    serde_json::from_str(&text).unwrap()
}

#[test]
fn a_wrapper_io_failure_still_compiles_the_unit_and_says_it_fell_back() {
    let root = tmpdir("mirror-blocked");
    let args = fixture(&root);

    // The mirror path occupied by a FILE: `create_dir_all` cannot proceed, so
    // `materialise` fails AFTER the manifest has been written saying
    // `fell_back: false`. Deterministic, and it takes milliseconds -- unlike
    // the 120 s lock timeout it stands in for.
    std::fs::create_dir_all(root.join("target/sensorium")).unwrap();
    std::fs::write(root.join("target/sensorium/mirror"), b"not a directory").unwrap();

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .arg(rustc())
        .args(&args)
        .current_dir(root.join("ws"))
        .env("SENSORIUM_TARGET", root.join("target"))
        .env("SENSORIUM_RT_RLIB", root.join("nonexistent.rlib"))
        .env("SENSORIUM_RT_DEPS", root.join("nonexistent"))
        .env("SENSORIUM_TOOL_HASH", "testhash")
        .output()
        .expect("run the wrapper");

    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(out.status.success(), "the unit must still compile: {stderr}");
    assert!(
        root.join("out/libprobe_fallback.rlib").exists(),
        "rustc produced no rlib; stderr: {stderr}"
    );
    // Never hide the retry (ruling 6): one line, naming the unit.
    assert!(
        stderr.contains("unit probe_fallback (fa11bacc) fell back to the real tree"),
        "stderr did not name the fallback: {stderr}"
    );

    let m = manifest(&root);
    assert_eq!(m["fell_back"], true, "manifest: {m}");
    // The manifest written before the failure is PATCHED, not replaced: what
    // would have been instrumented stays on the record.
    assert_eq!(m["files"]["src/lib.rs"][0]["qualname"], "f", "manifest: {m}");
    std::fs::remove_dir_all(&root).ok();
}

#[test]
fn a_missing_linkage_environment_leaves_a_stub_manifest_not_silence() {
    let root = tmpdir("no-env");
    let args = fixture(&root);

    // `read_env` refuses before any manifest is written. Without the stub this
    // unit would be compiled uninstrumented and leave NO trace at all: E2 would
    // never know it existed, and the converter would map its spool to nothing.
    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .arg(rustc())
        .args(&args)
        .current_dir(root.join("ws"))
        .env("SENSORIUM_TARGET", root.join("target"))
        .env_remove("SENSORIUM_RT_RLIB")
        .env_remove("SENSORIUM_RT_DEPS")
        .output()
        .expect("run the wrapper");

    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(out.status.success(), "the unit must still compile: {stderr}");
    assert!(
        stderr.contains("unit probe_fallback (fa11bacc) fell back to the real tree"),
        "stderr did not name the fallback: {stderr}"
    );

    let m = manifest(&root);
    assert_eq!(m["fell_back"], true, "manifest: {m}");
    assert_eq!(m["crate_name"], "probe_fallback");
    assert_eq!(m["files"], serde_json::json!({}), "manifest: {m}");
    std::fs::remove_dir_all(&root).ok();
}
