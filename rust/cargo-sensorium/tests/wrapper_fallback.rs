//! Every way a unit can end up compiled UNINSTRUMENTED, driven end to end
//! through the real binary.
//!
//! The promise being falsified is `rust/HONESTY.md` §8 item 7: *every* fallback
//! path writes or patches a manifest with `fell_back: true` and a
//! `fallback_reason`. Rung 1 had one path — an absolute crate root — that
//! reported to the log channel only, and a coverage check reading manifests
//! alone would have scored that unit as instrumented (findings §5.29). So each
//! test here reads the manifest, not the log, and then also requires the unit
//! to have been compiled anyway: falling back is a retry, not a failure.
//!
//! It carries one positive control beside them, because a file of negatives can
//! pass while nothing is ever instrumented: the argv the wrapper hands rustc
//! for a unit it DID instrument, read off a fake rustc that records what it was
//! given.

mod common;

use std::path::Path;
use std::process::{Command, Output};

use common::{bogus_runtime, fake_rustc, fake_rustc_runs, manifest, manifest_exists, Scratch};

const METADATA: &str = "fa11bacc";

/// A one-file crate at `<scratch>/ws`, plus the rustc argv cargo would build
/// for it.
fn fixture(s: &Scratch, extra: &[&str]) -> Vec<String> {
    s.write("ws/src/lib.rs", "pub fn f() -> u8 { 7 }\n");
    std::fs::create_dir_all(s.p("out")).unwrap();
    let mut args: Vec<String> = [
        "--crate-name",
        "probe_fallback",
        "--edition=2021",
        "src/lib.rs",
        "--crate-type",
        "lib",
        "-C",
        "debuginfo=0",
        "-C",
    ]
    .iter()
    .map(|a| (*a).to_owned())
    .collect();
    args.push(format!("metadata={METADATA}"));
    args.extend(extra.iter().map(|a| (*a).to_owned()));
    args.push("--out-dir".to_owned());
    args.push(s.p("out").to_string_lossy().into_owned());
    args
}

/// Run the wrapper the way cargo would: rustc in argv[1], cwd at the workspace
/// root, the driver's environment in place.
fn wrap(s: &Scratch, rustc: &Path, args: &[String], rt_dir: Option<&Path>) -> Output {
    let mut cmd = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"));
    cmd.arg(rustc)
        .args(args)
        .current_dir(s.p("ws"))
        .env("SENSORIUM_TARGET", s.p("target"))
        .env("SENSORIUM_TOOL_HASH", "testhash")
        .env_remove("SENSORIUM_RT_DIR");
    if let Some(rt) = rt_dir {
        cmd.env("SENSORIUM_RT_DIR", rt);
    }
    cmd.output().expect("run the wrapper")
}

fn stderr(out: &Output) -> String {
    String::from_utf8_lossy(&out.stderr).into_owned()
}

fn assert_declared_on_both_channels(out: &Output, s: &Scratch, reason_starts_with: &str) {
    let log = stderr(out);
    assert!(
        log.contains(&format!(
            "unit probe_fallback ({METADATA}) fell back to the real tree"
        )),
        "the build log does not name the fallback: {log}"
    );
    let m = manifest(&s.p("target"), METADATA);
    assert_eq!(m["fell_back"], true, "manifest: {m}");
    let reason = m["fallback_reason"].as_str().unwrap_or_default();
    assert!(
        reason.starts_with(reason_starts_with),
        "reason {reason:?} does not start with {reason_starts_with:?}"
    );
}

#[test]
fn an_lto_unit_falls_back_with_the_lto_reason_and_is_still_compiled() {
    let s = Scratch::new("lto");
    let rustc = fake_rustc(&s);
    let args = fixture(&s, &["-C", "lto=fat"]);
    let out = wrap(&s, &rustc, &args, Some(&s.p("rt")));

    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(fake_rustc_runs(&s), 1, "the unit must still be compiled");
    assert_declared_on_both_channels(&out, &s, "lto");
    // Nothing was mirrored: an LTO unit is refused before any work is done.
    assert!(!s.p("target/sensorium/mirror").exists());
}

#[test]
fn a_cross_target_unit_falls_back_with_the_cross_target_reason() {
    let s = Scratch::new("cross");
    let rustc = fake_rustc(&s);
    let args = fixture(&s, &["--target", "aarch64-unknown-linux-gnu"]);
    let out = wrap(&s, &rustc, &args, Some(&s.p("rt")));

    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(fake_rustc_runs(&s), 1);
    assert_declared_on_both_channels(&out, &s, "cross-target");
}

/// Findings §5.29, the whole reason this file exists in its current shape.
#[test]
fn an_absolute_crate_root_falls_back_with_a_manifest_and_not_only_a_log_line() {
    let s = Scratch::new("absroot");
    let rustc = fake_rustc(&s);
    s.write("ws/src/lib.rs", "pub fn f() -> u8 { 7 }\n");
    std::fs::create_dir_all(s.p("out")).unwrap();
    let absolute = s.p("ws/src/lib.rs").to_string_lossy().into_owned();
    let args: Vec<String> = [
        "--crate-name",
        "probe_fallback",
        "--edition=2021",
        &absolute,
        "--crate-type",
        "lib",
        "-C",
        "debuginfo=0",
        "-C",
        &format!("metadata={METADATA}"),
        "--out-dir",
        &s.p("out").to_string_lossy(),
    ]
    .iter()
    .map(|a| (*a).to_owned())
    .collect();

    let out = wrap(&s, &rustc, &args, Some(&s.p("rt")));

    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(fake_rustc_runs(&s), 1);
    assert_declared_on_both_channels(&out, &s, "absolute-crate-root");
}

#[test]
fn a_rustc_that_rejects_the_rewrite_falls_back_with_rustcs_own_first_line() {
    // The runtime rlib at the path is not an rlib, so the instrumented compile
    // fails the way a rejected rewrite would, in milliseconds. The unit is then
    // compiled from the REAL tree by the real rustc, which succeeds because the
    // real tree references no runtime.
    let s = Scratch::new("rustc-rejects");
    let rt = s.p("rt");
    bogus_runtime(&s, &rt);
    let args = fixture(&s, &[]);
    let out = wrap(&s, Path::new(&common::rustc()), &args, Some(&rt));

    assert!(
        out.status.success(),
        "the unit must still be compiled: {}",
        stderr(&out)
    );
    assert!(
        s.p("out/libprobe_fallback.rlib").exists(),
        "no rlib was produced: {}",
        stderr(&out)
    );
    assert_declared_on_both_channels(&out, &s, "rustc: ");
    // The sites the wrapper had worked out stay on the record: what WOULD have
    // been instrumented is evidence, not noise.
    let m = manifest(&s.p("target"), METADATA);
    assert_eq!(m["files"]["src/lib.rs"][0]["qualname"], "f", "{m}");
    assert!(m["source_hashes"]["src/lib.rs"].is_string(), "{m}");
}

#[test]
fn a_wrapper_io_failure_falls_back_with_a_wrapper_reason_and_still_compiles() {
    // The mirror directory's parent occupied by a FILE: `materialise` fails
    // AFTER the manifest has been written saying `fell_back: false`, which is
    // exactly the state a patch has to correct.
    let s = Scratch::new("wrapper-io");
    let rt = s.p("rt");
    bogus_runtime(&s, &rt);
    std::fs::create_dir_all(s.p("target/sensorium")).unwrap();
    std::fs::write(s.p("target/sensorium/mirror"), b"not a directory").unwrap();
    let args = fixture(&s, &[]);
    let out = wrap(&s, Path::new(&common::rustc()), &args, Some(&rt));

    assert!(out.status.success(), "{}", stderr(&out));
    assert!(s.p("out/libprobe_fallback.rlib").exists());
    assert_declared_on_both_channels(&out, &s, "wrapper: ");
    let m = manifest(&s.p("target"), METADATA);
    assert_eq!(m["files"]["src/lib.rs"][0]["qualname"], "f", "{m}");
}

#[test]
fn a_missing_linkage_environment_leaves_a_stub_manifest_not_silence() {
    // `read_env` refuses before any manifest is written. Without the stub this
    // unit would be compiled uninstrumented and leave NO record at all: no
    // coverage check would know it existed.
    let s = Scratch::new("no-env");
    let args = fixture(&s, &[]);
    let out = wrap(&s, Path::new(&common::rustc()), &args, None);

    assert!(out.status.success(), "{}", stderr(&out));
    assert!(s.p("out/libprobe_fallback.rlib").exists());
    assert_declared_on_both_channels(&out, &s, "wrapper: ");
    let m = manifest(&s.p("target"), METADATA);
    assert_eq!(m["crate_name"], "probe_fallback");
    assert_eq!(m["crate_type"], "lib");
    assert_eq!(m["files"], serde_json::json!({}), "{m}");
}

#[test]
fn a_runtime_that_cannot_be_built_falls_back_rather_than_failing_the_build() {
    // An rt directory that cannot be created (a file sits at its path) is a
    // wrapper error like any other: one line, one manifest, one compiled unit.
    let s = Scratch::new("rt-build");
    let rt = s.p("rt");
    std::fs::write(&rt, b"not a directory").unwrap();
    let args = fixture(&s, &[]);
    let out = wrap(&s, Path::new(&common::rustc()), &args, Some(&rt));

    assert!(out.status.success(), "{}", stderr(&out));
    assert!(s.p("out/libprobe_fallback.rlib").exists());
    assert_declared_on_both_channels(&out, &s, "wrapper: ");
}

/// Task-1 review finding B: a file the transformer REFUSED used to be
/// indistinguishable from one the walk never opened. Both channels now, the
/// same two a fallback uses: one stderr line a person reads, and a manifest key
/// a check reads. Not a fallback — one file of one unit is left unrewritten and
/// the rest is still instrumented — which is exactly why the reason has to be
/// somewhere: `fell_back` stays false and `fallback_reason` stays null.
#[test]
fn a_file_the_transformer_refused_names_its_reason_on_both_channels() {
    let s = Scratch::new("refused-file");
    let rt = s.p("rt");
    bogus_runtime(&s, &rt);
    let rustc = fake_rustc(&s);
    s.write("ws/src/lib.rs", "pub mod m;\npub fn f() -> u8 { 7 }\n");
    // Valid Rust, and a spawn with no NAMED ITEM around it: an enum
    // discriminant's expression sits in a module body, not in a fn, a const or
    // a static, so there is no qualname to name the child by and the
    // transformer refuses the file (`visit.rs`'s `spawn_shape`).
    s.write(
        "ws/src/m.rs",
        "pub enum E {\n\
         A = { let f: fn() = || { std::thread::spawn(|| ()).join().unwrap(); }; let _ = f; 1 },\n\
         }\n",
    );
    std::fs::create_dir_all(s.p("out")).unwrap();
    let mut args: Vec<String> = [
        "--crate-name",
        "probe_fallback",
        "--edition=2021",
        "src/lib.rs",
        "--crate-type",
        "lib",
        "-C",
        "debuginfo=0",
        "-C",
    ]
    .iter()
    .map(|a| (*a).to_owned())
    .collect();
    args.push(format!("metadata={METADATA}"));
    args.push("--out-dir".to_owned());
    args.push(s.p("out").to_string_lossy().into_owned());

    let out = wrap(&s, &rustc, &args, Some(&rt));

    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(fake_rustc_runs(&s), 1, "one compile, not a fallback retry");
    let log = stderr(&out);
    assert!(
        log.contains(&format!(
            "sensorium: unit probe_fallback ({METADATA}): src/m.rs: \
             spawn site outside any named item"
        )),
        "the build log does not name the refused file: {log}"
    );
    let m = manifest(&s.p("target"), METADATA);
    assert_eq!(
        m["unreached_reasons"]["src/m.rs"], "spawn site outside any named item",
        "{m}"
    );
    assert_eq!(m["unreached_files"], serde_json::json!(["src/m.rs"]), "{m}");
    // The unit itself is instrumented: this is one refused FILE, not a unit
    // that fell back, and nothing but `unreached_reasons` would say so.
    assert_eq!(m["fell_back"], false, "{m}");
    assert_eq!(m["fallback_reason"], serde_json::Value::Null, "{m}");
    assert_eq!(m["files"]["src/lib.rs"][0]["qualname"], "f", "{m}");
}

/// Passing through is not falling back. These argvs are not units this recorder
/// has anything to say about, and several carry no `-C metadata` to key a
/// manifest by, so writing one would invent a unit that does not exist.
#[test]
fn a_passthrough_unit_writes_no_manifest_and_no_log_line() {
    let s = Scratch::new("passthrough");
    let rustc = fake_rustc(&s);
    let args = fixture(&s, &["--crate-type", "proc-macro"]);
    let out = wrap(&s, &rustc, &args, Some(&s.p("rt")));

    assert!(out.status.success(), "{}", stderr(&out));
    assert_eq!(fake_rustc_runs(&s), 1, "the unit must still be compiled");
    assert!(
        !manifest_exists(&s.p("target"), METADATA),
        "a proc macro is not a unit and must not get a manifest"
    );
    assert!(!stderr(&out).contains("fell back"), "{}", stderr(&out));
}

/// The positive control. THREE flags are appended, in this order, and nothing
/// else:
///
/// 1. `--extern sensorium_rt=<rlib>` — binds the name this unit's own rewritten
///    crate root writes.
/// 2. `-L dependency=<the rlib's directory>` — how rustc resolves
///    `sensorium_rt` as a TRANSITIVE crate, which is what a unit that merely
///    *uses* an instrumented workspace crate needs. Measured 2026-09-03 on the
///    bloomery clone: without it, a unit whose submodule opens with
///    `use bloomery_core::journal::Journal;` fails `E0463` on the dependency,
///    because reading that crate's instrumented rmeta needs ITS runtime. D1 is
///    amended to require both flags. The directory holds exactly one rlib and
///    the runtime has no dependencies, so there is no multiple-candidates
///    hazard in putting it on the search path.
/// 3. `--remap-path-prefix=<mirror>=<workspace>` — load-bearing rather than
///    belt and braces: without it every backtrace frame prints a mirror path
///    (findings §5.21).
///
/// The order matters enough to pin: the argv cargo built comes first and is
/// untouched, and ours are appended after it.
#[test]
fn an_instrumented_units_argv_gains_the_three_flags_in_order_and_nothing_else() {
    let s = Scratch::new("appended");
    let rt = s.p("rt");
    let rlib = bogus_runtime(&s, &rt);
    let rustc = fake_rustc(&s);
    let args = fixture(&s, &[]);
    let out = wrap(&s, &rustc, &args, Some(&rt));

    assert!(out.status.success(), "{}", stderr(&out));
    assert!(
        !stderr(&out).contains("fell back"),
        "this unit is the instrumented case: {}",
        stderr(&out)
    );
    let log = std::fs::read_to_string(s.p("rustc.log")).expect("the fake rustc's log");
    assert_eq!(log.lines().count(), 1, "one compile, not two: {log}");

    let extern_flag = format!("--extern sensorium_rt={}", rlib.display());
    let search_flag = format!(
        "-L dependency={}",
        rlib.parent().expect("the rlib has a directory").display()
    );
    let remap_flag = format!(
        "--remap-path-prefix={}={}",
        s.p("target/sensorium/mirror").join(METADATA).display(),
        s.p("ws").display()
    );
    for flag in [&extern_flag, &search_flag, &remap_flag] {
        assert!(log.contains(flag.as_str()), "missing {flag}: {log}");
    }
    // In that order, and each exactly once: a repeated `-L` would mean the
    // wrapper appended per call rather than per unit, and a reordering would
    // mean one of ours landed inside the argv cargo built.
    let at = |flag: &str| log.find(flag).expect("just asserted present");
    assert!(
        at(&extern_flag) < at(&search_flag) && at(&search_flag) < at(&remap_flag),
        "the appended flags are out of order: {log}"
    );
    assert_eq!(log.matches("-L dependency=").count(), 1, "{log}");
    assert_eq!(log.matches("--extern sensorium_rt=").count(), 1, "{log}");
    // The ONLY search path is the runtime's own directory. The fixture's argv
    // carries none, so anything else here came from this wrapper.
    assert_eq!(log.matches("-L ").count(), 1, "{log}");
    // And the argv cargo built is otherwise untouched, still in front.
    assert!(log.contains("--crate-name probe_fallback"), "{log}");
    assert!(log.contains("-C metadata=fa11bacc"), "{log}");
    assert!(
        at("--crate-name probe_fallback") < at(&extern_flag),
        "{log}"
    );
}

#[test]
fn cargos_own_version_probe_passes_straight_through() {
    let s = Scratch::new("vV");
    let rustc = fake_rustc(&s);
    std::fs::create_dir_all(s.p("ws")).unwrap();
    let out = wrap(&s, &rustc, &["-vV".to_owned()], Some(&s.p("rt")));
    assert!(out.status.success());
    assert_eq!(fake_rustc_runs(&s), 1);
    assert!(!s.p("target/sensorium").exists(), "nothing was written");
}
