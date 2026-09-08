//! Building the runtime rlib, and installing the wrapper shim.
//!
//! Plan decision D1: `sensorium-rt` has no dependencies and is compiled by one
//! bare `rustc` line from source embedded in this binary
//! ([`crate::rt_src`]), into
//! `<target>/sensorium/rt/<tool hash>/<unwind|abort>/libsensorium_rt.rlib`.
//! The wrapper then adds `--extern sensorium_rt=<rlib>` and
//! `-L dependency=<the rlib's own per-variant directory>` -- the second
//! because a unit whose DEPENDENCIES are instrumented resolves their
//! `sensorium_rt` through the search path, not the extern map (measured on the
//! bloomery clone 2026-09-03; D1 as amended). That directory holds exactly one
//! rlib and the runtime has no dependencies, so the search path cannot offer a
//! second candidate -- which is how rung 1's two-`libc` graph and its
//! single-candidate hazard stay removed (findings §5.24).
//!
//! Two variants, selected from the unit's own `-C panic`. Measured on rustc
//! 1.96 (the table on
//! [`tests::the_abort_variant_is_the_one_an_abort_unit_needs_and_the_one_no_other_unit_may_have`]):
//! an `abort` runtime handed to a unit that is not abort is a hard rustc
//! error, while an `unwind` runtime links into either — so the selection is
//! load-bearing in one direction, and the abort variant exists both for that
//! direction and because the runtime's own code has to be compiled for the
//! strategy it will run under (`catch_unwind` is inert under abort;
//! `rust/HONESTY.md` §2). `unwind` is built by the driver before cargo starts;
//! `abort` is built by the WRAPPER, the first time a unit's argv asks for it,
//! under its own per-variant lock.
//!
//! The tool hash is sha256 of the driver binary's own bytes and of every
//! embedded source file. It keys the rt directory AND the shim path, so a
//! changed driver or a changed runtime rebuilds both — and cargo, which keys
//! `RUSTC_WORKSPACE_WRAPPER` by PATH rather than by content, sees a different
//! wrapper and rebuilds the units too.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::mirror::Lock;
use sensorium_rt::sha256;

/// The panic strategy an rlib was built for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Panic {
    Unwind,
    Abort,
}

impl Panic {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Panic::Unwind => "unwind",
            Panic::Abort => "abort",
        }
    }

    /// The variant a unit whose argv carries (or does not carry)
    /// `-C panic=abort` must link.
    #[must_use]
    pub fn for_unit(panic_abort: bool) -> Panic {
        if panic_abort {
            Panic::Abort
        } else {
            Panic::Unwind
        }
    }
}

/// `<target>/sensorium/rt/<tool hash>`: the source and both variants.
#[must_use]
pub fn rt_dir(target: &Path, tool_hash: &str) -> PathBuf {
    target.join("sensorium").join("rt").join(tool_hash)
}

/// Where one variant's rlib lives under an rt directory.
#[must_use]
pub fn rlib(rt_dir: &Path, panic: Panic) -> PathBuf {
    rt_dir.join(panic.as_str()).join("libsensorium_rt.rlib")
}

/// sha256 of the driver binary and every embedded source file, first 16 hex.
///
/// The path is fed in beside the contents so that moving a line from one file
/// to another changes the hash: a digest over concatenated contents alone
/// would not.
///
/// # Errors
/// If the binary cannot be read.
pub fn tool_hash(exe: &Path, files: &[(&str, &str)]) -> Result<String, String> {
    let mut h = sha256::Sha256::new();
    let bytes = std::fs::read(exe).map_err(|e| format!("cannot read {}: {e}", exe.display()))?;
    h.update(&bytes);
    for (path, contents) in files {
        h.update(path.as_bytes());
        h.update(b"\0");
        h.update(contents.as_bytes());
        h.update(b"\0");
    }
    Ok(sha256::to_hex(&h.finish())[..16].to_owned())
}

/// Make sure `<rt_dir>/<panic>/libsensorium_rt.rlib` exists, building it with
/// one bare `rustc` line if it does not. Returns its path.
///
/// A build that is already there is a no-op down to the rlib's mtime: the
/// directory is keyed by the tool hash, so an rlib at that path was built from
/// exactly these bytes by exactly this driver.
///
/// # Errors
/// If the sources cannot be written, the lock cannot be taken, rustc cannot be
/// run, or rustc fails — with rustc's own output in the message.
pub fn ensure(
    rt_dir: &Path,
    rustc: &str,
    panic: Panic,
    files: &[(&str, &str)],
) -> Result<PathBuf, String> {
    let out = rlib(rt_dir, panic);
    if out.is_file() {
        return Ok(out);
    }
    std::fs::create_dir_all(rt_dir)
        .map_err(|e| format!("cannot create {}: {e}", rt_dir.display()))?;
    let _lock = Lock::acquire(&rt_dir.join(format!("{}.lock", panic.as_str())))
        .map_err(|e| format!("cannot lock the {} runtime build: {e}", panic.as_str()))?;
    // Another process may have built it while we waited.
    if out.is_file() {
        return Ok(out);
    }
    write_sources(rt_dir, files)?;
    let out_dir = rt_dir.join(panic.as_str());
    std::fs::create_dir_all(&out_dir)
        .map_err(|e| format!("cannot create {}: {e}", out_dir.display()))?;
    let tmp = out_dir.join(format!("libsensorium_rt.rlib.tmp-{}", std::process::id()));
    let result = Command::new(rustc)
        .current_dir(rt_dir)
        .args([
            "--crate-name",
            "sensorium_rt",
            "--crate-type",
            "rlib",
            "--edition",
            "2021",
            "-C",
            "opt-level=3",
            "-C",
        ])
        .arg(format!("panic={}", panic.as_str()))
        .arg(format!("src/{}", crate::rt_src::CRATE_ROOT))
        .arg("-o")
        .arg(&tmp)
        .output()
        .map_err(|e| format!("cannot run {rustc} to build the runtime: {e}"))?;
    if !result.status.success() {
        let _ = std::fs::remove_file(&tmp);
        return Err(format!(
            "building the {} runtime failed ({}):\n{}",
            panic.as_str(),
            result.status,
            String::from_utf8_lossy(&result.stderr)
        ));
    }
    // Rename last, so no other process ever sees a half-written rlib at the
    // path it is about to hand rustc.
    std::fs::rename(&tmp, &out)
        .map_err(|e| format!("cannot move the runtime into {}: {e}", out.display()))?;
    Ok(out)
}

/// Write the embedded sources under `<rt_dir>/src/`, leaving a file whose bytes
/// are already right alone.
fn write_sources(rt_dir: &Path, files: &[(&str, &str)]) -> Result<(), String> {
    let src = rt_dir.join("src");
    std::fs::create_dir_all(&src).map_err(|e| format!("cannot create {}: {e}", src.display()))?;
    for (path, contents) in files {
        let dest = src.join(path);
        if matches!(std::fs::read_to_string(&dest), Ok(existing) if existing == *contents) {
            continue;
        }
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("cannot create {}: {e}", parent.display()))?;
        }
        std::fs::write(&dest, contents.as_bytes())
            .map_err(|e| format!("cannot write {}: {e}", dest.display()))?;
    }
    Ok(())
}

/// Install the running binary at `<target>/sensorium/shim/<key>/cargo-sensorium`
/// -- a hard link where it can be, a copy where it cannot.
///
/// Cargo keys `RUSTC_WORKSPACE_WRAPPER` by path and not by content, so the
/// hash has to be IN the path: that is what makes a rebuilt driver rebuild the
/// units it wrapped.
///
/// **The bytes are the same bytes, so they are stored once** (R3, design
/// 2026-09-07 §0). One key per focus meant one ~40 MB copy per focus: slice 2
/// measured 62 shim entries under one target directory totalling
/// 2 506 729 440 bytes, all of them this binary. A hard link keeps the
/// per-key PATH cargo needs without a per-key copy. Sharing the driver's
/// inode is safe because `key` already hashes the driver's own bytes
/// ([`tool_hash`]): a replaced driver takes a different key, so no live shim
/// is ever written through.
///
/// **Nothing here writes the driver's inode.** The chmod belongs to the copy
/// path alone: on the link path the shim IS the driver, already carrying the
/// driver's own mode, and a `set_permissions` there would be the one line in
/// this recorder that reached back and changed the binary it was installing
/// (R3's ruling conceded that cost; it bought nothing, so it is not paid).
///
/// The copy is the answer on any error, and the one that matters is `EXDEV`:
/// a `CARGO_TARGET_DIR` on another mount than the driver is an ordinary thing
/// to have. When BOTH fail, both failures are named: the link's error is why
/// the fallback was reached at all, and it is free information.
///
/// `key` is the tool hash for an unfocused build and `<tool hash>-<focus
/// hash>` for a focused one. **The focus has to be in this path**, and the
/// per-file mirror stamp of design §2.3 is not enough on its own: cargo
/// decides whether to invoke the wrapper AT ALL before the wrapper can decide
/// anything, and `SENSORIUM_FOCUS` is not part of any cargo fingerprint.
/// Measured on cargo 1.96, 2026-09-06, on `corpus/rust/silent_swallow`:
/// `--focus load run` then `run` then `--focus main run` left cargo printing
/// `Finished in 0.00s` for the second and third, so all three invocations ran
/// the FIRST build's binary and all three traces claimed `focus: ["load"]`.
///
/// # Errors
/// Any filesystem failure, naming the path.
pub fn install_shim(target: &Path, exe: &Path, key: &str) -> Result<PathBuf, String> {
    use std::os::unix::fs::PermissionsExt;
    let dir = target.join("sensorium").join("shim").join(key);
    std::fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    let shim = dir.join("cargo-sensorium");
    if shim.is_file() {
        // The path encodes a hash of the binary's own bytes, and the install
        // below is atomic, so anything at this path is this binary.
        return Ok(shim);
    }
    let tmp = dir.join(format!("cargo-sensorium.tmp-{}", std::process::id()));
    // Cleared FIRST, and not merely for `hard_link`'s sake (it refuses an
    // existing destination, which alone would only cost a needless copy). A
    // leftover `tmp` from a run that died between install and rename may
    // ITSELF be a link to the driver, and `fs::copy` onto it truncates what it
    // opens -- which would be the driver. Unlink, then create.
    //
    // A clear that FAILS stops the install. Anything but `NotFound` means the
    // name is still there and this process could not remove it, so the copy
    // below would open exactly the survivor the unlink was meant to destroy.
    match std::fs::remove_file(&tmp) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => return Err(format!("cannot clear the leftover {}: {e}", tmp.display())),
    }
    if let Err(link_err) = std::fs::hard_link(exe, &tmp) {
        std::fs::copy(exe, &tmp).map_err(|copy_err| {
            format!(
                "cannot install {} at {}: the link failed ({link_err}) and so did the copy \
                 ({copy_err})",
                exe.display(),
                tmp.display()
            )
        })?;
        // The copy path only. `fs::copy` creates its destination, and cargo
        // has to be able to exec what ends up at the shim's name; stating the
        // mode is cheaper than depending on the source's.
        std::fs::set_permissions(&tmp, std::fs::Permissions::from_mode(0o755))
            .map_err(|e| format!("cannot chmod {}: {e}", tmp.display()))?;
    }
    std::fs::rename(&tmp, &shim)
        .map_err(|e| format!("cannot move the shim into {}: {e}", shim.display()))?;
    Ok(shim)
}

#[cfg(test)]
mod tests;
