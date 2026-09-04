//! Shared scaffolding for the integration tests. Every one of them drives the
//! REAL binary through `CARGO_BIN_EXE_cargo-sensorium`, so what is under test
//! is the program cargo would invoke, not a library call that resembles it.

#![allow(dead_code)]

use std::path::{Path, PathBuf};
use std::time::SystemTime;

pub mod wire;

/// A scratch directory that removes itself, named after the test so a failed
/// run leaves something a person can find in `ls /tmp`.
pub struct Scratch(pub PathBuf);

impl Scratch {
    pub fn new(name: &str) -> Scratch {
        let base = std::env::temp_dir().join(format!(
            "sensorium-it-{}-{}-{name}",
            std::process::id(),
            SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&base).unwrap();
        Scratch(base)
    }

    /// The same, but under `CARGO_TARGET_DIR` when one is set. The driver
    /// smoke test builds a real crate here, and the artifacts belong on
    /// whatever disk the build directory is on rather than on `/tmp`.
    pub fn in_build_dir(name: &str) -> Scratch {
        let base = std::env::var_os("CARGO_TARGET_DIR")
            .map_or_else(std::env::temp_dir, PathBuf::from)
            .join(format!(
                "sensorium-it-{}-{}-{name}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
        std::fs::create_dir_all(&base).unwrap();
        Scratch(base)
    }

    pub fn p(&self, rel: &str) -> PathBuf {
        self.0.join(rel)
    }

    pub fn write(&self, rel: &str, contents: &str) -> PathBuf {
        let path = self.p(rel);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, contents).unwrap();
        path
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

/// The rustc this test run should use, as an absolute PATH.
///
/// Cargo hands a workspace wrapper the rustc it resolved, which is always a
/// path; the binary reads a bare word in that position as a mistyped
/// subcommand. So a test that passes `"rustc"` would be driving a role cargo
/// never asks for.
pub fn rustc() -> String {
    if let Some(explicit) = std::env::var("RUSTC").ok().filter(|v| !v.is_empty()) {
        return explicit;
    }
    let path = std::env::var("PATH").unwrap_or_default();
    for dir in path.split(':') {
        let candidate = Path::new(dir).join("rustc");
        if candidate.is_file() {
            return candidate.to_string_lossy().into_owned();
        }
    }
    panic!("no rustc on PATH ({path})");
}

/// A `rustc` that succeeds at everything and records the argv it was handed, so
/// a test can prove the unit was still compiled without waiting for a real
/// compile. Returns its path; the log is at `<scratch>/rustc.log`.
pub fn fake_rustc(scratch: &Scratch) -> PathBuf {
    use std::os::unix::fs::PermissionsExt;
    let log = scratch.p("rustc.log");
    let path = scratch.write(
        "fake-rustc",
        &format!(
            "#!/bin/sh\nprintf '%s\\n' \"$*\" >> {}\nexit 0\n",
            log.display()
        ),
    );
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
    path
}

/// How many times the fake rustc ran.
pub fn fake_rustc_runs(scratch: &Scratch) -> usize {
    std::fs::read_to_string(scratch.p("rustc.log"))
        .map(|s| s.lines().count())
        .unwrap_or(0)
}

/// An rlib path that EXISTS and is not an rlib. `rt_build::ensure` hands back
/// anything already at the variant's path (the path is keyed by the tool hash,
/// so in a real run only this driver can have put it there), which lets a test
/// reach the "rustc rejected the rewrite" path in milliseconds instead of
/// building the runtime first.
pub fn bogus_runtime(scratch: &Scratch, rt_dir: &Path) -> PathBuf {
    let _ = scratch;
    let rlib = rt_dir.join("unwind").join("libsensorium_rt.rlib");
    std::fs::create_dir_all(rlib.parent().unwrap()).unwrap();
    std::fs::write(&rlib, b"this is not an rlib\n").unwrap();
    rlib
}

/// Read a manifest as JSON, failing with the path when it is not there.
pub fn manifest(target: &Path, metadata: &str) -> serde_json::Value {
    let path = target
        .join("sensorium/manifests")
        .join(format!("{metadata}.json"));
    let text = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("no manifest at {}: {e}", path.display()));
    serde_json::from_str(&text).unwrap()
}

pub fn manifest_exists(target: &Path, metadata: &str) -> bool {
    target
        .join("sensorium/manifests")
        .join(format!("{metadata}.json"))
        .exists()
}
