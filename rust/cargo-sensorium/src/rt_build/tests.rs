//! `rt_build`'s tests: the runtime build, the tool hash, and the shim.
//!
//! Split out of `rt_build.rs` when R3's fix round pushed that file past its
//! working ceiling -- the same shape `convert::spool` uses. The tests are
//! unchanged by the move.

use super::*;
use std::time::SystemTime;
struct Tmp(PathBuf);

impl Tmp {
    fn new(name: &str) -> Tmp {
        Tmp::under(&std::env::temp_dir(), name)
    }

    /// A directory on a NAMED filesystem rather than on whatever `TMPDIR`
    /// happens to point at. The shim tests below choose their mount --
    /// the driver's own for the link, a tmpfs for the copy -- because
    /// "the same filesystem" is the thing they are pinning.
    fn under(parent: &Path, name: &str) -> Tmp {
        let base = parent.join(format!(
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

/// Named for what it pins -- the bytes and the path -- and no longer for
/// the mechanism: since R3 the shim is a LINK wherever it can be, and a
/// test called "is a copy" would be a false sentence about a passing
/// check. What it asserts is unchanged.
#[test]
fn the_shim_is_this_binarys_bytes_at_a_hashed_path() {
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

/// R3 (design 2026-09-07 §0, §4): the shim SHARES the driver's inode
/// wherever it can. Slice 2 measured 62 shim entries under one target
/// directory totalling 2 506 729 440 bytes -- one ~40 MB copy of the
/// driver per focus hash, because cargo keys `RUSTC_WORKSPACE_WRAPPER` by
/// PATH, so the path has to stay per-hash even though the bytes never
/// differ.
///
/// The fixture is made BESIDE the driver rather than under `TMPDIR`, so
/// that "one filesystem" is true by construction: a check that quietly
/// skipped itself wherever `/tmp` is its own mount would pin nothing on
/// the box where the 2.5 GB was measured.
#[test]
fn the_shim_is_a_hard_link_to_the_driver_where_they_share_a_filesystem() {
    use std::os::unix::fs::MetadataExt;
    let exe = std::env::current_exe().unwrap();
    let beside = exe.parent().expect("the driver has a directory").to_owned();
    let t = Tmp::under(&beside, "shim-link");
    let shim = install_shim(&t.0, &exe, "0123456789abcdef").unwrap();
    let driver = std::fs::metadata(&exe).unwrap();
    let installed = std::fs::metadata(&shim).unwrap();
    assert_eq!(
        installed.dev(),
        driver.dev(),
        "the fixture must put the shim on the driver's own filesystem"
    );
    assert_eq!(
        installed.ino(),
        driver.ino(),
        "the shim must be a hard link to the driver, not another {} bytes",
        driver.len()
    );
    // One inode, so `nlink` counts both names...
    assert!(installed.nlink() >= 2, "nlink {}", installed.nlink());
    // ...and the bytes read back through the shim's name are the driver's.
    assert_eq!(std::fs::read(&shim).unwrap(), std::fs::read(&exe).unwrap());
}

/// ...and a COPY where it cannot be a link. `/dev/shm` is a tmpfs, so a
/// shim installed there and a driver under the target directory cannot
/// share an inode: `hard_link` fails `EXDEV` and the copy answers, which
/// is why the fallback exists at all (a `CARGO_TARGET_DIR` on another
/// mount is an ordinary thing to have).
///
/// Skipped BY NAME where `/dev/shm` is not mounted, or is somehow the
/// driver's own filesystem: a check that did not run says so rather than
/// passing.
#[test]
fn the_shim_is_a_copy_where_it_cannot_be_a_link() {
    use std::os::unix::fs::MetadataExt;
    let exe = std::env::current_exe().unwrap();
    let driver = std::fs::metadata(&exe).unwrap();
    let shm = Path::new("/dev/shm");
    let Ok(other) = std::fs::metadata(shm) else {
        eprintln!(
            "note: the_shim_is_a_copy_where_it_cannot_be_a_link did not run: /dev/shm is \
             not mounted, so this box offers no second filesystem to cross"
        );
        return;
    };
    if other.dev() == driver.dev() {
        eprintln!(
            "note: the_shim_is_a_copy_where_it_cannot_be_a_link did not run: /dev/shm is \
             the driver's own filesystem, so there is no boundary here to cross"
        );
        return;
    }
    let t = Tmp::under(shm, "shim-copy");
    let shim = install_shim(&t.0, &exe, "0123456789abcdef").unwrap();
    let installed = std::fs::metadata(&shim).unwrap();
    assert_ne!(
        installed.dev(),
        driver.dev(),
        "the fixture crosses no mount"
    );
    // `dev()` IS the discriminator: a hard link cannot cross it, so the
    // fallback is the only way this file exists. Inode numbers are only
    // meaningful within one device, so they are not compared across two;
    // what a copy promises is a name of its own.
    assert_eq!(installed.nlink(), 1, "a copy is one name, not two");
    assert_eq!(std::fs::read(&shim).unwrap(), std::fs::read(&exe).unwrap());
}

/// The hazard R3's link introduces, pinned rather than merely commented.
///
/// A run that dies between the install and the rename leaves
/// `cargo-sensorium.tmp-<pid>` behind, and since R3 that leftover may
/// itself be a LINK to the driver. `fs::copy` truncates what it opens, so
/// an install that met the leftover, failed to link onto it (`EEXIST`) and
/// fell back to the copy would empty the driver through its second name.
/// `install_shim` unlinks the temporary first.
///
/// The "driver" here is a file the fixture makes, not this test binary:
/// truncating the running executable to prove a point would be a worse
/// failure than the one under test.
#[test]
fn a_leftover_temporary_is_unlinked_rather_than_written_through() {
    let exe = std::env::current_exe().unwrap();
    let beside = exe.parent().expect("the driver has a directory").to_owned();
    let t = Tmp::under(&beside, "shim-stale-tmp");
    // A stand-in driver on the same filesystem, so the link path is the
    // one taken -- as it is in the case this guards.
    let stand_in = t.0.join("driver");
    std::fs::write(&stand_in, b"the driver's bytes").unwrap();
    let key = "fedcba9876543210";
    let dir = t.0.join("sensorium").join("shim").join(key);
    std::fs::create_dir_all(&dir).unwrap();
    // What a run that died before its rename leaves behind.
    let leftover = dir.join(format!("cargo-sensorium.tmp-{}", std::process::id()));
    std::fs::hard_link(&stand_in, &leftover).unwrap();

    let shim = install_shim(&t.0, &stand_in, key).unwrap();

    assert_eq!(
        std::fs::read(&stand_in).unwrap(),
        b"the driver's bytes",
        "the driver was written through its own second name"
    );
    assert_eq!(std::fs::read(&shim).unwrap(), b"the driver's bytes");
    assert!(!leftover.exists(), "the temporary outlived the rename");
}

/// The unlink-first guard's promise is UNCONDITIONAL, so its failure is
/// reported rather than swallowed. A leftover this process cannot clear --
/// `EACCES` on a shim directory another uid wrote, `EROFS`, or (as here) a
/// DIRECTORY standing where the temporary's name belongs -- must abort the
/// install. Falling through would put `fs::copy` onto the survivor with
/// `O_TRUNC`, and after R3 the survivor may be a second name for the
/// driver: the exact truncation the guard exists to prevent, reported as
/// a success.
///
/// The abort has to happen AT the clear, which is why the sentence is
/// pinned: an install that got as far as the copy has already opened the
/// thing it was supposed to refuse to touch.
#[test]
fn a_leftover_that_cannot_be_cleared_aborts_the_install() {
    let exe = std::env::current_exe().unwrap();
    let beside = exe.parent().expect("the driver has a directory").to_owned();
    let t = Tmp::under(&beside, "shim-stuck-tmp");
    let stand_in = t.0.join("driver");
    std::fs::write(&stand_in, b"the driver's bytes").unwrap();
    let key = "0f1e2d3c4b5a6978";
    let dir = t.0.join("sensorium").join("shim").join(key);
    std::fs::create_dir_all(&dir).unwrap();
    // `unlink` refuses a directory on every uid, root included, so this
    // leftover cannot be cleared however the test is run.
    let stuck = dir.join(format!("cargo-sensorium.tmp-{}", std::process::id()));
    std::fs::create_dir(&stuck).unwrap();

    let err = install_shim(&t.0, &stand_in, key)
        .expect_err("an uncleanable leftover must not be installed through");

    assert!(
        err.starts_with("cannot clear the leftover"),
        "the install must stop at the clear, not report a later failure: {err}"
    );
    assert!(err.contains(&stuck.display().to_string()), "{err}");
    assert_eq!(std::fs::read(&stand_in).unwrap(), b"the driver's bytes");
    assert!(
        !dir.join("cargo-sensorium").exists(),
        "a shim was installed"
    );
}

/// When the link fails AND the copy fails, BOTH failures are named. The
/// link's error is why the fallback was reached at all, and a report that
/// mentioned only the copy would leave the reader to guess it.
///
/// A directory as the source fails both ways on every uid -- Linux permits
/// no hard link to a directory at all, and `fs::copy` refuses a source
/// that is not a file -- so the sentence is pinned without arranging a
/// permission that root would walk straight through.
#[test]
fn an_install_that_can_neither_link_nor_copy_names_both_failures() {
    let t = Tmp::new("shim-both-fail");
    let not_a_file = t.0.join("driver");
    std::fs::create_dir(&not_a_file).unwrap();

    let err = install_shim(&t.0, &not_a_file, "9876543210fedcba")
        .expect_err("a source that can be neither linked nor copied is not an install");

    assert!(err.contains("the link failed ("), "{err}");
    assert!(err.contains("and so did the copy ("), "{err}");
}

/// The only cost R3's ruling conceded -- that `set_permissions` on a
/// linked shim writes the DRIVER's own inode -- bought nothing, so it is
/// gone from the link path. The link IS the driver's inode and carries the
/// driver's mode by construction; the chmod is the copy path's alone.
///
/// The driver here is a stand-in with a mode this test chose, so the
/// assertion is about a mode and not about whatever the test binary
/// happens to carry -- and so that a regression rewrites the fixture's
/// inode rather than the real driver's.
#[test]
fn a_linked_shim_leaves_the_drivers_mode_alone() {
    use std::os::unix::fs::MetadataExt;
    use std::os::unix::fs::PermissionsExt;
    let exe = std::env::current_exe().unwrap();
    let beside = exe.parent().expect("the driver has a directory").to_owned();
    let t = Tmp::under(&beside, "shim-link-mode");
    let stand_in = t.0.join("driver");
    std::fs::write(&stand_in, b"the driver's bytes").unwrap();
    std::fs::set_permissions(&stand_in, std::fs::Permissions::from_mode(0o700)).unwrap();

    let shim = install_shim(&t.0, &stand_in, "abcdefabcdef0123").unwrap();

    let driver = std::fs::metadata(&stand_in).unwrap();
    let installed = std::fs::metadata(&shim).unwrap();
    // The fixture must have taken the link path, or this pins nothing.
    assert_eq!(installed.ino(), driver.ino(), "the fixture did not link");
    assert_eq!(
        driver.permissions().mode() & 0o777,
        0o700,
        "installing a shim rewrote the driver's own mode"
    );
    // One inode, so one mode -- and it is the driver's.
    assert_eq!(installed.permissions().mode(), driver.permissions().mode());
}

/// What this pins after R3 is the COPY path: `fs::copy` creates the
/// destination, and cargo has to be able to exec what lands at the shim's
/// name. On the link path the mode is the driver's by construction (see
/// `a_linked_shim_leaves_the_drivers_mode_alone`).
#[test]
fn the_shim_is_executable() {
    use std::os::unix::fs::PermissionsExt;
    let t = Tmp::new("shim-mode");
    let exe = std::env::current_exe().unwrap();
    let shim = install_shim(&t.0, &exe, "abcdef0123456789").unwrap();
    let mode = std::fs::metadata(&shim).unwrap().permissions().mode();
    assert_eq!(mode & 0o111, 0o111, "cargo must be able to exec the shim");
}
