//! What the wrapper writes when a unit is compiled UNINSTRUMENTED.
//!
//! Every fallback path writes or patches that unit's manifest with
//! `fell_back: true` and a `fallback_reason`. Rung 1 had one path — an
//! absolute crate root — that reported to the log channel only, so a coverage
//! check reading manifests alone would have scored an uninstrumented unit as
//! instrumented (findings §5.29). `rust/HONESTY.md` §8 item 7 is the promise
//! this module keeps, and it is the reason the reason is a value in a file
//! rather than a sentence on stderr.
//!
//! Passing through is a different thing and writes nothing: cargo's own probes,
//! build scripts and proc macros are not units this recorder has anything to
//! say about, and several of them carry no `-C metadata` to key a manifest by.

use std::path::{Path, PathBuf};

use sensorium_transform::Manifest;

use crate::args::Unit;

/// `<target>/sensorium/manifests/<-C metadata>.json`.
#[must_use]
pub fn manifest_path(target: &Path, metadata: &str) -> PathBuf {
    target
        .join("sensorium")
        .join("manifests")
        .join(format!("{metadata}.json"))
}

/// Write a manifest, creating its directory.
///
/// # Errors
/// Any filesystem or serialisation failure, naming the path.
pub fn write_manifest(path: &Path, manifest: &Manifest) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("cannot create {}: {e}", parent.display()))?;
    }
    let json = manifest
        .to_json()
        .map_err(|e| format!("cannot serialise manifest: {e}"))?;
    std::fs::write(path, json).map_err(|e| format!("cannot write {}: {e}", path.display()))
}

/// Record that `unit` was compiled uninstrumented, and why.
///
/// A manifest already on disk is PATCHED, so the sites the wrapper had worked
/// out stay on the record as what would have been instrumented. Otherwise a
/// stub: a unit with no manifest at all is invisible to a coverage check and to
/// the converter, which is the one outcome worse than an empty manifest.
///
/// `workspace_root` is written (or re-written) either way: the PATCH branch
/// sets it too, not only the stub branch, so a manifest predating this field
/// picks it up the moment ANY wrapper of this invocation touches it again --
/// belt and braces alongside the fresh write every `instrument()` call
/// already makes.
///
/// # Errors
/// If the manifest cannot be written.
pub fn mark_fallen_back(
    path: &Path,
    unit: &Unit,
    reason: &str,
    workspace_root: &str,
) -> Result<(), String> {
    if let Ok(text) = std::fs::read_to_string(path) {
        if let Ok(mut v) = serde_json::from_str::<serde_json::Value>(&text) {
            v["fell_back"] = serde_json::Value::Bool(true);
            v["fallback_reason"] = serde_json::Value::String(reason.to_owned());
            v["workspace_root"] = serde_json::Value::String(workspace_root.to_owned());
            let json = serde_json::to_string(&v)
                .map_err(|e| format!("cannot re-serialise {}: {e}", path.display()))?;
            return std::fs::write(path, json)
                .map_err(|e| format!("cannot write {}: {e}", path.display()));
        }
    }
    let mut stub = Manifest::new(&unit.metadata, &unit.crate_name, &unit.crate_type);
    stub.fell_back = true;
    stub.fallback_reason = Some(reason.to_owned());
    stub.workspace_root = workspace_root.to_owned();
    write_manifest(path, &stub)
}

/// The one stderr line a fallback prints. Never hidden: a unit that recorded
/// nothing has to be visible in the build log as well as in the manifest,
/// because those are the two channels a reader has.
pub fn announce(unit: &Unit, reason: &str) {
    eprintln!(
        "sensorium: unit {} ({}) fell back to the real tree: {reason}",
        unit.crate_name, unit.metadata
    );
}

/// The one line of rustc's output that says what went wrong.
///
/// Cargo drives rustc with `--error-format=json`, so prefer the first error
/// message's `message` field; fall back to the first non-empty line for a
/// plain-text rustc.
#[must_use]
pub fn first_error_line(stderr: &str) -> String {
    for line in stderr.lines() {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
            if v.get("level").and_then(|l| l.as_str()) == Some("error") {
                if let Some(m) = v.get("message").and_then(|m| m.as_str()) {
                    return m.to_owned();
                }
            }
            continue;
        }
        let trimmed = line.trim();
        if !trimmed.is_empty() {
            return trimmed.to_owned();
        }
    }
    "rustc failed with no diagnostic".to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::SystemTime;

    fn unit() -> Unit {
        Unit {
            crate_name: "demo".to_owned(),
            crate_type: "lib".to_owned(),
            metadata: "abc".to_owned(),
            crate_root: "a/src/lib.rs".to_owned(),
            panic_abort: false,
        }
    }

    fn tmpdir(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!(
            "sensorium-fallback-test-{}-{}-{name}",
            std::process::id(),
            SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    fn read(path: &Path) -> serde_json::Value {
        serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
    }

    #[test]
    fn the_manifest_path_is_derived_once_for_every_writer() {
        assert_eq!(
            manifest_path(Path::new("/t/target"), "a98bc0df34adbff2"),
            Path::new("/t/target/sensorium/manifests/a98bc0df34adbff2.json")
        );
    }

    #[test]
    fn marking_an_existing_manifest_keeps_its_sites_and_records_the_reason() {
        let d = tmpdir("existing");
        let path = d.join("abc.json");
        let mut m = Manifest::new("abc", "demo", "lib");
        m.unreached_files.push("a/src/ghost.rs".to_owned());
        write_manifest(&path, &m).unwrap();
        assert_eq!(read(&path)["fell_back"], false);

        mark_fallen_back(&path, &unit(), "lto", "/w").unwrap();

        let v = read(&path);
        assert_eq!(v["fell_back"], true);
        assert_eq!(v["fallback_reason"], "lto");
        // What WOULD have been instrumented stays on the record.
        assert_eq!(v["unreached_files"], serde_json::json!(["a/src/ghost.rs"]));
        // The patch branch sets `workspace_root` too, not only the stub one.
        assert_eq!(v["workspace_root"], "/w");
        std::fs::remove_dir_all(&d).ok();
    }

    #[test]
    fn marking_writes_a_stub_when_the_wrapper_never_got_that_far() {
        let d = tmpdir("stub");
        let path = d.join("abc.json");
        mark_fallen_back(&path, &unit(), "wrapper: SENSORIUM_RT_DIR is unset", "/w").unwrap();
        let v = read(&path);
        assert_eq!(v["fell_back"], true);
        assert_eq!(v["fallback_reason"], "wrapper: SENSORIUM_RT_DIR is unset");
        assert_eq!(v["unit"], "abc");
        assert_eq!(v["crate_name"], "demo");
        assert_eq!(v["crate_type"], "lib");
        assert_eq!(v["files"], serde_json::json!({}));
        assert_eq!(v["workspace_root"], "/w");
        std::fs::remove_dir_all(&d).ok();
    }

    #[test]
    fn marking_replaces_a_manifest_that_is_not_readable_json() {
        let d = tmpdir("corrupt");
        let path = d.join("abc.json");
        std::fs::write(&path, b"{ this is not json").unwrap();
        mark_fallen_back(&path, &unit(), "cross-target", "/w").unwrap();
        let v = read(&path);
        assert_eq!(v["fell_back"], true);
        assert_eq!(v["fallback_reason"], "cross-target");
        std::fs::remove_dir_all(&d).ok();
    }

    #[test]
    fn the_first_json_error_is_the_reported_line() {
        let stderr = concat!(
            r#"{"level":"warning","message":"unused variable"}"#,
            "\n",
            r#"{"level":"error","message":"cannot find crate `sensorium_rt`"}"#,
            "\n",
        );
        assert_eq!(first_error_line(stderr), "cannot find crate `sensorium_rt`");
    }

    #[test]
    fn plain_stderr_falls_back_to_its_first_non_empty_line() {
        assert_eq!(
            first_error_line("\n\nerror: boom\nnote: x\n"),
            "error: boom"
        );
    }

    #[test]
    fn silence_is_reported_as_silence_not_as_success() {
        assert_eq!(first_error_line(""), "rustc failed with no diagnostic");
    }
}
