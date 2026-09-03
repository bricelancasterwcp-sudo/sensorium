//! Building the runtime rlib, and installing the wrapper shim.
//!
//! Plan decision D1: `sensorium-rt` has no dependencies and is compiled by one
//! bare `rustc` line from source embedded in this binary
//! ([`crate::rt_src`]), into
//! `<target>/sensorium/rt/<tool hash>/<unwind|abort>/libsensorium_rt.rlib`.
//! The wrapper then adds a single `--extern sensorium_rt=<rlib>` and no
//! `-L dependency` at all, which is what removes rung 1's two-`libc` graph and
//! its single-candidate hazard (findings §5.24).
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
use crate::sha256;

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

/// Copy the running binary to
/// `<target>/sensorium/shim/<tool hash>/cargo-sensorium`.
///
/// Cargo keys `RUSTC_WORKSPACE_WRAPPER` by path and not by content, so the
/// hash has to be IN the path: that is what makes a rebuilt driver rebuild the
/// units it wrapped.
///
/// # Errors
/// Any filesystem failure, naming the path.
pub fn install_shim(target: &Path, exe: &Path, tool_hash: &str) -> Result<PathBuf, String> {
    use std::os::unix::fs::PermissionsExt;
    let dir = target.join("sensorium").join("shim").join(tool_hash);
    std::fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    let shim = dir.join("cargo-sensorium");
    if shim.is_file() {
        // The path encodes a hash of the binary's own bytes, and the copy below
        // is atomic, so anything at this path is this binary.
        return Ok(shim);
    }
    let tmp = dir.join(format!("cargo-sensorium.tmp-{}", std::process::id()));
    std::fs::copy(exe, &tmp)
        .map_err(|e| format!("cannot copy {} to {}: {e}", exe.display(), tmp.display()))?;
    std::fs::set_permissions(&tmp, std::fs::Permissions::from_mode(0o755))
        .map_err(|e| format!("cannot chmod {}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, &shim)
        .map_err(|e| format!("cannot move the shim into {}: {e}", shim.display()))?;
    Ok(shim)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::SystemTime;

    struct Tmp(PathBuf);

    impl Tmp {
        fn new(name: &str) -> Tmp {
            let base = std::env::temp_dir().join(format!(
                "sensorium-rt-build-test-{}-{}-{name}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(&base).unwrap();
            Tmp(base)
        }
    }

    impl Drop for Tmp {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn rustc() -> String {
        std::env::var("RUSTC").unwrap_or_else(|_| "rustc".to_owned())
    }

    /// A stand-in for the real runtime: the same shape (one crate root, one
    /// child module) and a fraction of the compile time, so the build-behaviour
    /// tests below stay cheap. The real bytes get their own test.
    const TINY: &[(&str, &str)] = &[
        ("lib.rs", "mod helper;\npub fn f() -> u8 { helper::g() }\n"),
        ("helper.rs", "pub fn g() -> u8 { 7 }\n"),
    ];

    #[test]
    fn the_rlib_path_names_the_variant() {
        assert_eq!(
            rlib(Path::new("/t/rt/abcd"), Panic::Abort),
            Path::new("/t/rt/abcd/abort/libsensorium_rt.rlib")
        );
        assert_eq!(
            rlib(Path::new("/t/rt/abcd"), Panic::Unwind),
            Path::new("/t/rt/abcd/unwind/libsensorium_rt.rlib")
        );
    }

    #[test]
    fn a_unit_that_asks_for_abort_gets_the_abort_variant() {
        assert_eq!(Panic::for_unit(true), Panic::Abort);
        assert_eq!(Panic::for_unit(false), Panic::Unwind);
    }

    #[test]
    fn the_rt_directory_is_keyed_by_the_tool_hash() {
        assert_eq!(
            rt_dir(Path::new("/t/target"), "0123456789abcdef"),
            Path::new("/t/target/sensorium/rt/0123456789abcdef")
        );
    }

    #[test]
    fn building_twice_at_the_same_hash_does_not_touch_the_rlib() {
        let t = Tmp::new("noop");
        let dir = t.0.join("rt");
        let first = ensure(&dir, &rustc(), Panic::Unwind, TINY).unwrap();
        let before = std::fs::metadata(&first).unwrap().modified().unwrap();
        std::thread::sleep(std::time::Duration::from_millis(20));
        let second = ensure(&dir, &rustc(), Panic::Unwind, TINY).unwrap();
        assert_eq!(first, second);
        let after = std::fs::metadata(&second).unwrap().modified().unwrap();
        assert_eq!(before, after, "an unchanged runtime must not be rebuilt");
    }

    #[test]
    fn a_changed_embedded_source_changes_the_hash_and_therefore_the_directory() {
        // The rebuild trigger is not a timestamp comparison: a changed source
        // is a different tool hash, which is a different rt directory, which
        // has no rlib in it yet.
        let exe = std::env::current_exe().unwrap();
        let before = tool_hash(&exe, TINY).unwrap();
        let changed: Vec<(&str, &str)> = vec![TINY[0], ("helper.rs", "pub fn g() -> u8 { 8 }\n")];
        let after = tool_hash(&exe, &changed).unwrap();
        assert_ne!(before, after);

        let t = Tmp::new("rebuild");
        let a = ensure(&t.0.join(&before), &rustc(), Panic::Unwind, TINY).unwrap();
        let b = ensure(&t.0.join(&after), &rustc(), Panic::Unwind, &changed).unwrap();
        assert_ne!(a, b);
        assert!(a.is_file() && b.is_file());
        assert_ne!(
            std::fs::read(&a).unwrap(),
            std::fs::read(&b).unwrap(),
            "two different sources must not produce the same rlib"
        );
    }

    #[test]
    fn moving_a_line_between_files_changes_the_hash() {
        // A digest over concatenated CONTENTS alone would not see this.
        let exe = std::env::current_exe().unwrap();
        let a = tool_hash(&exe, &[("lib.rs", "mod m;"), ("m.rs", "pub fn g() {}")]).unwrap();
        let b = tool_hash(&exe, &[("lib.rs", "mod m;pub fn g() {}"), ("m.rs", "")]).unwrap();
        assert_ne!(a, b);
    }

    #[test]
    fn both_panic_variants_coexist_under_one_hash() {
        let t = Tmp::new("variants");
        let dir = t.0.join("rt");
        let unwind = ensure(&dir, &rustc(), Panic::Unwind, TINY).unwrap();
        let abort = ensure(&dir, &rustc(), Panic::Abort, TINY).unwrap();
        assert!(unwind.is_file() && abort.is_file());
        assert_ne!(unwind, abort);
        // And they share one copy of the source.
        assert!(dir.join("src/lib.rs").is_file());
    }

    /// The rule the variant selection has to obey, MEASURED on rustc 1.96
    /// rather than assumed — and it is not the rule this test was first
    /// written for.
    ///
    /// | runtime built | consumer built | rustc |
    /// |---|---|---|
    /// | unwind | abort  | **accepts** |
    /// | abort  | abort  | accepts |
    /// | abort  | unwind | **refuses**: "the crate `sensorium_rt` requires panic strategy `abort` which is incompatible with this crate's strategy of `unwind`" |
    ///
    /// So the asymmetry runs the other way: an unwind runtime would link
    /// everywhere, and handing the ABORT runtime to a unit that is not abort is
    /// the error. That is what makes selecting the variant from the unit's own
    /// `-C panic` load-bearing rather than optional — and it is why the abort
    /// variant is built lazily, only for a unit that asked for abort. The
    /// variant is also not cosmetic on its own terms: the runtime's code has to
    /// be compiled for the strategy it will run under, which is what makes
    /// `catch_unwind` inert there (`rust/HONESTY.md` §2), and the two rlibs are
    /// different bytes.
    #[test]
    fn the_abort_variant_is_the_one_an_abort_unit_needs_and_the_one_no_other_unit_may_have() {
        let t = Tmp::new("panic-link");
        let dir = t.0.join("rt");
        let unwind = ensure(&dir, &rustc(), Panic::Unwind, TINY).unwrap();
        let abort = ensure(&dir, &rustc(), Panic::Abort, TINY).unwrap();
        assert_ne!(
            std::fs::read(&unwind).unwrap(),
            std::fs::read(&abort).unwrap(),
            "the two variants are the same artifact, so one of them is pointless"
        );

        // The check fires when a final artifact is linked, so the consumer is a
        // binary; an rlib consumer accepts either and proves nothing.
        let consumer = t.0.join("consumer.rs");
        std::fs::write(
            &consumer,
            "fn main() { assert_eq!(sensorium_rt::f(), 7); }\n",
        )
        .unwrap();
        let build = |rt: &Path, panic: Panic, out: &str| {
            Command::new(rustc())
                .args([
                    "--crate-name",
                    "consumer",
                    "--crate-type",
                    "bin",
                    "--edition",
                    "2021",
                ])
                .arg("-C")
                .arg(format!("panic={}", panic.as_str()))
                .arg("--extern")
                .arg(format!("sensorium_rt={}", rt.display()))
                .arg(&consumer)
                .arg("-o")
                .arg(t.0.join(out))
                .output()
                .unwrap()
        };

        let abort_into_abort = build(&abort, Panic::Abort, "a-a");
        assert!(
            abort_into_abort.status.success(),
            "an abort unit must be able to link the abort runtime: {}",
            String::from_utf8_lossy(&abort_into_abort.stderr)
        );

        let abort_into_unwind = build(&abort, Panic::Unwind, "a-u");
        let message = String::from_utf8_lossy(&abort_into_unwind.stderr).into_owned();
        assert!(
            !abort_into_unwind.status.success(),
            "handing the abort runtime to an unwind unit must fail; if it stops \
             failing, the variant choice has stopped being load-bearing"
        );
        assert!(
            message.contains("panic strategy"),
            "expected a panic-strategy refusal, got: {message}"
        );

        let unwind_into_unwind = build(&unwind, Panic::Unwind, "u-u");
        assert!(
            unwind_into_unwind.status.success(),
            "{}",
            String::from_utf8_lossy(&unwind_into_unwind.stderr)
        );
    }

    /// The one test that compiles the REAL embedded bytes. Everything else here
    /// uses a stand-in, so without this the bare `rustc` line is only ever
    /// exercised against two lines of Rust.
    #[test]
    fn the_real_embedded_runtime_compiles_with_the_bare_line() {
        let t = Tmp::new("real");
        let out = ensure(
            &t.0.join("rt"),
            &rustc(),
            Panic::Unwind,
            crate::rt_src::FILES,
        )
        .unwrap();
        assert!(out.is_file());
        assert!(
            std::fs::metadata(&out).unwrap().len() > 1024,
            "an rlib that small is not a compiled runtime"
        );
    }

    #[test]
    fn a_runtime_that_does_not_compile_is_an_error_carrying_rustcs_own_words() {
        let t = Tmp::new("broken");
        let err = ensure(
            &t.0.join("rt"),
            &rustc(),
            Panic::Unwind,
            &[("lib.rs", "pub fn f( {\n")],
        )
        .expect_err("a syntax error must not be reported as a built runtime");
        assert!(err.contains("error"), "{err}");
        assert!(!rlib(&t.0.join("rt"), Panic::Unwind).exists());
    }

    #[test]
    fn the_shim_is_a_copy_of_this_binary_at_a_hashed_path() {
        let t = Tmp::new("shim");
        let exe = std::env::current_exe().unwrap();
        let shim = install_shim(&t.0, &exe, "0123456789abcdef").unwrap();
        assert_eq!(
            shim,
            t.0.join("sensorium/shim/0123456789abcdef/cargo-sensorium")
        );
        assert_eq!(std::fs::read(&shim).unwrap(), std::fs::read(&exe).unwrap());
        // Installing again is a no-op that still answers with the same path.
        assert_eq!(install_shim(&t.0, &exe, "0123456789abcdef").unwrap(), shim);
        // No temporary is left behind for cargo to trip over.
        let leftovers: Vec<_> = std::fs::read_dir(shim.parent().unwrap())
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
            .filter(|n| n != "cargo-sensorium")
            .collect();
        assert!(leftovers.is_empty(), "left behind: {leftovers:?}");
    }

    #[test]
    fn the_shim_is_executable() {
        use std::os::unix::fs::PermissionsExt;
        let t = Tmp::new("shim-mode");
        let exe = std::env::current_exe().unwrap();
        let shim = install_shim(&t.0, &exe, "abcdef0123456789").unwrap();
        let mode = std::fs::metadata(&shim).unwrap().permissions().mode();
        assert_eq!(mode & 0o111, 0o111, "cargo must be able to exec the shim");
    }
}
