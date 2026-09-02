//! Building `libsensorium_rt-<hash>.rlib` and installing the wrapper shim.
//!
//! Spec 2.3: the runtime is never in the target's `Cargo.toml`, so its
//! `Cargo.lock` is untouched. The driver builds it in the SPIKE workspace at
//! `opt-level = 3` (the spike's lens: the runtime is optimised whatever profile
//! the target uses) and the wrapper appends `--extern sensorium_rt=<rlib>` plus
//! `-L dependency=<the rlib's own deps dir>` so rustc can find the runtime's
//! transitive rlibs -- notably `libc`, which the target may ALSO depend on at a
//! different `-C metadata`. Whether two libc crates can coexist in one unit is
//! a measured question, not an assumed one (see the task report).
//!
//! Cargo keys `RUSTC_WORKSPACE_WRAPPER` by PATH, not content (spec 2.1), so the
//! shim lives at a path that encodes the hash of the driver binary AND the rt
//! rlib. Change either and cargo sees a different wrapper and rebuilds.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::sha256;

/// Where the runtime ended up.
pub struct Runtime {
    pub rlib: PathBuf,
    /// The directory the rlib sits in: `-L dependency=` for its own deps.
    pub deps_dir: PathBuf,
}

/// Build `sensorium-rt` in `spike_root` and return its rlib.
///
/// # Errors
/// A string describing the cargo failure, including cargo's own stderr.
pub fn build(spike_root: &Path) -> Result<Runtime, String> {
    let target_dir = spike_root.join("target");
    let out = Command::new("cargo")
        .current_dir(spike_root)
        .args([
            "build",
            "--release",
            "-p",
            "sensorium-rt",
            "--message-format=json-render-diagnostics",
        ])
        .arg("--target-dir")
        .arg(&target_dir)
        // A stray CARGO_TARGET_DIR (mechanics.sh sets one for the probe) must
        // not scatter the runtime into the target workspace's tree, and the
        // wrapper env must never reach the runtime's own build.
        .env_remove("CARGO_TARGET_DIR")
        .env_remove("RUSTC_WORKSPACE_WRAPPER")
        .env_remove("SENSORIUM_SPOOL")
        .output()
        .map_err(|e| format!("cannot run cargo to build sensorium-rt: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "building sensorium-rt failed ({}):\n{}",
            out.status,
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    let stdout = String::from_utf8_lossy(&out.stdout);
    let rlib = rlib_from_cargo_json(&stdout)
        .ok_or_else(|| "cargo built sensorium-rt but reported no .rlib artifact".to_owned())?;
    let rlib = PathBuf::from(rlib);
    if !rlib.is_file() {
        return Err(format!(
            "cargo reported the runtime rlib at {} but no such file exists",
            rlib.display()
        ));
    }
    let deps_dir = rlib
        .parent()
        .ok_or_else(|| format!("rlib {} has no parent directory", rlib.display()))?
        .to_path_buf();
    Ok(Runtime { rlib, deps_dir })
}

/// Pull the `sensorium-rt` rlib path out of `cargo --message-format=json`
/// output, as it sits in the DEPS directory.
///
/// Two wrinkles cargo 1.96 actually has, both observed on this box:
/// the artifact's `target.name` is the LIB target name (`sensorium_rt`, with an
/// underscore), not the package name; and `filenames` lists the UPLIFTED
/// `target/release/libsensorium_rt.rlib`, whose parent is not the deps
/// directory rustc needs on `-L dependency=`. The hashed twin in `deps/` is the
/// one to hand out, and the `.rmeta` entry names it.
#[must_use]
pub fn rlib_from_cargo_json(stdout: &str) -> Option<String> {
    for line in stdout.lines() {
        let Ok(v) = serde_json::from_str::<serde_json::Value>(line) else {
            continue;
        };
        if v.get("reason").and_then(|r| r.as_str()) != Some("compiler-artifact") {
            continue;
        }
        let name = v.pointer("/target/name").and_then(|n| n.as_str())?;
        if name != "sensorium_rt" && name != "sensorium-rt" {
            continue;
        }
        let files: Vec<&str> = v
            .get("filenames")
            .and_then(|f| f.as_array())?
            .iter()
            .filter_map(serde_json::Value::as_str)
            .collect();
        if let Some(f) = files
            .iter()
            .find(|f| f.ends_with(".rlib") && f.contains("/deps/"))
        {
            return Some((*f).to_owned());
        }
        if let Some(f) = files
            .iter()
            .find(|f| f.ends_with(".rmeta") && f.contains("/deps/"))
        {
            return Some(format!("{}.rlib", f.trim_end_matches(".rmeta")));
        }
        if let Some(f) = files.iter().find(|f| f.ends_with(".rlib")) {
            return Some((*f).to_owned());
        }
    }
    None
}

/// The tool hash: sha256 of the driver binary and the rt rlib, first 16 hex.
///
/// # Errors
/// If either file cannot be read.
pub fn tool_hash(exe: &Path, rlib: &Path) -> Result<String, String> {
    let mut h = sha256::Sha256::new();
    for p in [exe, rlib] {
        let bytes = std::fs::read(p).map_err(|e| format!("cannot read {}: {e}", p.display()))?;
        h.update(&bytes);
    }
    let full = sha256::to_hex(&h.finish());
    Ok(full[..16].to_owned())
}

/// Copy the running binary to `<target>/sensorium/shim/<hash>/cargo-sensorium`.
///
/// # Errors
/// Any filesystem failure, naming the path.
pub fn install_shim(target: &Path, exe: &Path, hash: &str) -> Result<PathBuf, String> {
    use std::os::unix::fs::PermissionsExt;
    let dir = target.join("sensorium").join("shim").join(hash);
    std::fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    let shim = dir.join("cargo-sensorium");
    let src_len = std::fs::metadata(exe)
        .map_err(|e| format!("cannot stat {}: {e}", exe.display()))?
        .len();
    let up_to_date = matches!(std::fs::metadata(&shim), Ok(m) if m.len() == src_len);
    if !up_to_date {
        std::fs::copy(exe, &shim)
            .map_err(|e| format!("cannot copy {} to {}: {e}", exe.display(), shim.display()))?;
        std::fs::set_permissions(&shim, std::fs::Permissions::from_mode(0o755))
            .map_err(|e| format!("cannot chmod {}: {e}", shim.display()))?;
    }
    Ok(shim)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Captured verbatim from `cargo build --release -p sensorium-rt
    /// --message-format=json` on this box (paths shortened).
    const REAL: &str = concat!(
        r#"{"reason":"compiler-artifact","target":{"name":"libc"},"filenames":["/t/release/deps/liblibc-21f1.rlib","/t/release/deps/liblibc-21f1.rmeta"]}"#,
        "\n",
        r#"{"reason":"compiler-artifact","target":{"name":"sensorium_rt"},"filenames":["/t/release/libsensorium_rt.rlib","/t/release/deps/libsensorium_rt-7c78.rmeta"]}"#,
        "\n",
        r#"{"reason":"build-finished","success":true}"#,
        "\n",
    );

    #[test]
    fn the_deps_copy_is_chosen_over_the_uplifted_one() {
        // The uplifted `/t/release/libsensorium_rt.rlib` comes first and is a
        // real .rlib -- taking it would put `-L dependency=/t/release` on the
        // argv, where libc's rlib is not, and the unit would not link.
        assert_eq!(
            rlib_from_cargo_json(REAL).as_deref(),
            Some("/t/release/deps/libsensorium_rt-7c78.rlib")
        );
    }

    #[test]
    fn libcs_rlib_is_never_mistaken_for_the_runtimes() {
        // libc's artifact line comes FIRST and its rlib IS in deps/.
        assert!(!rlib_from_cargo_json(REAL).unwrap().contains("libc"));
    }

    #[test]
    fn a_hashed_rlib_in_deps_is_taken_directly() {
        let stdout = r#"{"reason":"compiler-artifact","target":{"name":"sensorium-rt"},"filenames":["/t/release/deps/libsensorium_rt-9.rlib"]}"#;
        assert_eq!(
            rlib_from_cargo_json(stdout).as_deref(),
            Some("/t/release/deps/libsensorium_rt-9.rlib")
        );
    }

    #[test]
    fn no_rlib_is_none_not_a_guess() {
        let stdout = r#"{"reason":"build-finished","success":true}"#;
        assert_eq!(rlib_from_cargo_json(stdout), None);
    }

    #[test]
    fn non_json_lines_are_skipped_not_fatal() {
        let stdout = concat!(
            "warning: something cargo printed\n",
            r#"{"reason":"compiler-artifact","target":{"name":"sensorium_rt"},"filenames":["/t/deps/libsensorium_rt-9.rlib"]}"#,
            "\n",
        );
        assert_eq!(
            rlib_from_cargo_json(stdout).as_deref(),
            Some("/t/deps/libsensorium_rt-9.rlib")
        );
    }
}
