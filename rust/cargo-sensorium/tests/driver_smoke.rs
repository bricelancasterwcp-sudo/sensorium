//! `cargo sensorium test`, end to end, on a crate this test writes.
//!
//! Everything else in this crate's suite drives one role in isolation. This
//! drives the whole chain the way a person would: the driver builds the
//! runtime, installs the shim, mints an invocation, and hands cargo an argv;
//! cargo calls the shim as its workspace wrapper for the units and as its
//! target runner for the test binary; the runtime spools; and what is left on
//! disk is what Task 6's converter reads. If the seam the converter attaches to
//! is not there, this is where it shows.
//!
//! Not bloomery and not the probe workspace (Task 7's job): two functions and
//! one test, so the whole chain costs a few seconds.

mod common;

use std::path::Path;
use std::process::Command;

use common::Scratch;

const LIB: &str = r#"//! A crate small enough to read and big enough to record.

pub fn add(a: u8, b: u8) -> u8 {
    a + b
}

pub fn double(x: u8) -> u8 {
    add(x, x)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doubling_three_is_six() {
        assert_eq!(double(3), 6);
    }
}
"#;

fn entries_ending_in(dir: &Path, suffix: &str) -> Vec<std::path::PathBuf> {
    let mut found: Vec<_> = std::fs::read_dir(dir)
        .unwrap_or_else(|e| panic!("no {}: {e}", dir.display()))
        .filter_map(|e| {
            let p = e.unwrap().path();
            p.file_name()
                .map(|n| n.to_string_lossy().ends_with(suffix))
                .unwrap_or(false)
                .then_some(p)
        })
        .collect();
    found.sort();
    found
}

fn read_json(path: &Path) -> serde_json::Value {
    let text = std::fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("cannot read {}: {e}", path.display()));
    serde_json::from_str(&text)
        .unwrap_or_else(|e| panic!("{} is not JSON: {e}\n{text}", path.display()))
}

#[test]
fn cargo_sensorium_test_records_a_two_function_crate() {
    let s = Scratch::in_build_dir("driver-smoke");
    // `[workspace]` so this crate is its own root wherever the scratch lands,
    // and `cargo locate-project --workspace` cannot walk up into somebody
    // else's tree.
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"smoke\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", LIB);
    let target = s.p("target");

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["sensorium", "test"])
        .current_dir(s.p("ws"))
        .env("CARGO_TARGET_DIR", &target)
        // Whatever ran THIS test must not leak into the build under test.
        .env_remove("RUSTC_WORKSPACE_WRAPPER")
        .env_remove("RUSTC_WRAPPER")
        .env_remove("RUSTFLAGS")
        .env_remove("RUSTDOCFLAGS")
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .env_remove("SENSORIUM_INNER_RUNNER")
        .output()
        .expect("run the driver");

    let stdout = String::from_utf8_lossy(&out.stdout).into_owned();
    let stderr = String::from_utf8_lossy(&out.stderr).into_owned();
    let context = format!("--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}");
    assert_eq!(out.status.code(), Some(0), "{context}");
    assert!(stdout.contains("test result: ok"), "{context}");
    assert!(stderr.contains("cargo exit: 0"), "{context}");
    assert!(
        !stderr.contains("fell back"),
        "no unit of a plain crate should fall back:\n{context}"
    );

    // One invocation, one spool directory, named in the run-id shape.
    let spools = s.p("target/sensorium/spool");
    let invocations: Vec<_> = std::fs::read_dir(&spools)
        .expect("a spool directory")
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(invocations.len(), 1, "{invocations:?}");
    let spool = &invocations[0];
    let id = spool.file_name().unwrap().to_string_lossy().into_owned();
    assert!(
        stderr.contains(&format!("spool: {}", spool.display())),
        "the driver must print where it put the spool:\n{context}"
    );

    // `invocation.json`, completed after cargo exited.
    let invocation = read_json(&spool.join("invocation.json"));
    assert_eq!(invocation["invocation"], id.as_str());
    assert_eq!(invocation["subcommand"], "test");
    assert_eq!(invocation["cargo_args"], serde_json::json!(["test"]));
    assert_eq!(invocation["tier"], "call");
    assert_eq!(invocation["profile"], "dev");
    assert_eq!(invocation["driver_version"], "cargo-sensorium 0.1.0");
    assert_eq!(invocation["cargo_exit"], 0);
    assert_eq!(
        invocation["workspace_root"],
        s.p("ws").to_string_lossy().as_ref()
    );
    assert_eq!(invocation["target_dir"], target.to_string_lossy().as_ref());
    assert!(
        invocation["toolchain"]
            .as_str()
            .unwrap()
            .starts_with("rustc "),
        "{invocation}"
    );
    assert!(invocation["host"].as_str().unwrap().contains('-'));
    assert!(invocation["rustc_path"].as_str().unwrap().contains("rustc"));
    assert_eq!(invocation["tool_hash"].as_str().unwrap().len(), 16);
    let start = invocation["start_ts"].as_f64().unwrap();
    let end = invocation["end_ts"].as_f64().unwrap();
    assert!(end >= start && start > 1_700_000_000.0, "{invocation}");

    // The runtime, built by the bare rustc line at the hashed path.
    let rlib = target
        .join("sensorium/rt")
        .join(invocation["tool_hash"].as_str().unwrap())
        .join("unwind/libsensorium_rt.rlib");
    assert!(rlib.is_file(), "no runtime at {}", rlib.display());

    // The units: a manifest each, none fallen back, sites in the lib.
    let manifests = entries_ending_in(&target.join("sensorium/manifests"), ".json");
    assert!(!manifests.is_empty(), "no manifests were written");
    let mut lib_sites = 0usize;
    for path in &manifests {
        let m = read_json(path);
        assert_eq!(m["fell_back"], false, "{} fell back: {m}", path.display());
        assert_eq!(m["crate_name"], "smoke");
        if let Some(sites) = m["files"]["src/lib.rs"].as_array() {
            lib_sites += sites.len();
            assert!(m["source_hashes"]["src/lib.rs"].is_string(), "{m}");
        }
    }
    assert!(
        lib_sites >= 2,
        "add and double must both have sites: {lib_sites}"
    );

    // The process wrote a header and at least one thread spool.
    let procs = entries_ending_in(spool, ".proc.json");
    assert!(
        !procs.is_empty(),
        "no process header in {}",
        spool.display()
    );
    let spool_files = entries_ending_in(spool, ".spool");
    assert!(!spool_files.is_empty(), "nothing was recorded");

    // And the runner witnessed the test binary's exit, which is the thing no
    // amount of instrumentation inside the process could have seen.
    let runners = entries_ending_in(spool, ".runner.json");
    assert_eq!(
        runners.len(),
        1,
        "one test binary, one witnessed exit: {runners:?}"
    );
    let r = read_json(&runners[0]);
    assert_eq!(r["exit_status"], 0, "{r}");
    assert_eq!(r["signal"], serde_json::Value::Null);
    let argv0 = r["argv"][0].as_str().unwrap();
    assert!(argv0.contains("smoke"), "the runner ran {argv0}");
    // The process that spooled is the process the runner waited for.
    let pid = r["pid"].as_u64().unwrap();
    assert!(
        procs
            .iter()
            .any(|p| p.file_name().unwrap().to_string_lossy() == format!("{pid}.proc.json")),
        "no process header for the pid the runner waited for ({pid}): {procs:?}"
    );

    // Nothing was written into the workspace itself.
    let ws_entries: Vec<String> = std::fs::read_dir(s.p("ws"))
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    let mut expected = vec!["Cargo.toml".to_owned(), "src".to_owned()];
    // Cargo writes a lock file for the crate it builds; that is cargo's, and
    // it is the only thing that may appear.
    expected.push("Cargo.lock".to_owned());
    for entry in &ws_entries {
        assert!(
            expected.contains(entry),
            "the recorder wrote {entry} into the workspace; only {expected:?} may be there"
        );
    }
}

#[test]
fn a_second_run_reuses_the_runtime_and_the_shim() {
    // The tool hash keys both, so the second invocation must not rebuild
    // either. This is also the freshness promise in miniature: cargo keys the
    // workspace wrapper by PATH, and a moving path would rebuild every unit.
    let s = Scratch::in_build_dir("driver-twice");
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"twice\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", "pub fn one() -> u8 { 1 }\n");
    let target = s.p("target");

    let run = || {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["sensorium", "test"])
            .current_dir(s.p("ws"))
            .env("CARGO_TARGET_DIR", &target)
            .env_remove("RUSTC_WORKSPACE_WRAPPER")
            .env_remove("RUSTC_WRAPPER")
            .env_remove("RUSTFLAGS")
            .env_remove("RUSTDOCFLAGS")
            .env_remove("SENSORIUM_SPOOL")
            .output()
            .expect("run the driver")
    };

    let first = run();
    assert_eq!(
        first.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    let rt_dirs: Vec<_> = std::fs::read_dir(target.join("sensorium/rt"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(rt_dirs.len(), 1, "{rt_dirs:?}");
    let rlib = rt_dirs[0].join("unwind/libsensorium_rt.rlib");
    let before = std::fs::metadata(&rlib).unwrap().modified().unwrap();

    let second = run();
    assert_eq!(second.status.code(), Some(0));
    let after = std::fs::metadata(&rlib).unwrap().modified().unwrap();
    assert_eq!(before, after, "the runtime was rebuilt for no reason");
    // Two invocations, two spool directories: an invocation is never reused.
    let spools: Vec<_> = std::fs::read_dir(target.join("sensorium/spool"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(spools.len(), 2, "{spools:?}");
}

#[test]
fn a_target_directory_with_a_space_in_it_is_refused_rather_than_mis_run() {
    // Cargo splits the runner variable and RUSTDOCFLAGS on whitespace, so a
    // path with a space in it would silently become two arguments.
    let s = Scratch::in_build_dir("spacey");
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"spacey\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", "pub fn one() -> u8 { 1 }\n");

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["sensorium", "test"])
        .current_dir(s.p("ws"))
        .env("CARGO_TARGET_DIR", s.p("a target"))
        .output()
        .expect("run the driver");

    assert_eq!(out.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("contains whitespace"), "{stderr}");
    assert_eq!(
        stderr.lines().count(),
        1,
        "one line, not a lecture: {stderr}"
    );
}

#[test]
fn an_unknown_subcommand_is_refused_with_the_usage_line() {
    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["sensorium", "build"])
        .output()
        .expect("run the driver");
    assert_eq!(out.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("unknown subcommand `build`"), "{stderr}");
}

/// `CARGO_TARGET_DIR` reached through a SYMLINK, not named directly.
///
/// **Choice, pinned by an assertion below rather than left implicit**:
/// `invocation.json`'s `target_dir` records the path exactly AS GIVEN --
/// the symlink, not its canonical resolution. `driver.rs` never
/// canonicalizes: every path this process derives (`SENSORIUM_TARGET`, the
/// spool/manifests/mirror/rt/shim paths, the value written to
/// `invocation.json`) is built by joining onto whatever `CARGO_TARGET_DIR`
/// said, and every `std::fs` call downstream follows a symlink component
/// transparently -- there is no correctness reason to resolve it, and doing
/// so would make `target_dir` a path the environment never actually named.
/// The one thing that has to hold for the converter (Task 6) is that a
/// single value is used consistently everywhere within one invocation, which
/// is what the "reachable both ways, and only one real copy exists" checks
/// below are for.
#[test]
fn a_symlinked_cargo_target_dir_is_followed_not_duplicated() {
    let s = Scratch::in_build_dir("symlink-target");
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"symlinked\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", "pub fn one() -> u8 { 1 }\n");

    let real_target = s.p("real-target");
    std::fs::create_dir_all(&real_target).unwrap();
    let link = s.p("target-link");
    std::os::unix::fs::symlink(&real_target, &link).unwrap();

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["sensorium", "test"])
        .current_dir(s.p("ws"))
        .env("CARGO_TARGET_DIR", &link)
        .env_remove("RUSTC_WORKSPACE_WRAPPER")
        .env_remove("RUSTC_WRAPPER")
        .env_remove("RUSTFLAGS")
        .env_remove("RUSTDOCFLAGS")
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .env_remove("SENSORIUM_INNER_RUNNER")
        .output()
        .expect("run the driver");

    let stdout = String::from_utf8_lossy(&out.stdout).into_owned();
    let stderr = String::from_utf8_lossy(&out.stderr).into_owned();
    let context = format!("--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}");
    assert_eq!(out.status.code(), Some(0), "{context}");
    assert!(stdout.contains("test result: ok"), "{context}");

    // Everything landed under the REAL directory: no code path may have
    // quietly materialised a second, parallel tree at the link's own path.
    assert!(
        real_target.join("sensorium/manifests").is_dir(),
        "{context}"
    );
    assert!(real_target.join("sensorium/mirror").is_dir(), "{context}");
    let spools: Vec<_> = std::fs::read_dir(real_target.join("sensorium/spool"))
        .expect("a spool directory under the real target")
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(spools.len(), 1, "{spools:?}");
    let rt_dirs: Vec<_> = std::fs::read_dir(real_target.join("sensorium/rt"))
        .expect("an rt directory under the real target")
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(rt_dirs.len(), 1, "{rt_dirs:?}");
    assert!(rt_dirs[0].join("unwind/libsensorium_rt.rlib").is_file());
    let shim_dirs: Vec<_> = std::fs::read_dir(real_target.join("sensorium/shim"))
        .expect("a shim directory under the real target")
        .map(|e| e.unwrap().path())
        .collect();
    assert_eq!(shim_dirs.len(), 1, "{shim_dirs:?}");
    assert!(shim_dirs[0].join("cargo-sensorium").is_file());

    // ...and everything is reachable the SAME way, through the link.
    assert!(link.join("sensorium/manifests").is_dir(), "{context}");
    assert_eq!(
        std::fs::read_dir(link.join("sensorium/spool"))
            .unwrap()
            .count(),
        1,
        "the spool must be reachable through the symlink too"
    );

    // `invocation.json` records the path AS GIVEN -- see the doc comment
    // above for why that, and not a canonicalised path, is the choice.
    let invocation: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(spools[0].join("invocation.json")).unwrap())
            .unwrap();
    assert_eq!(
        invocation["target_dir"],
        link.to_string_lossy().as_ref(),
        "{invocation}"
    );

    // Nothing was written BESIDE the link: its parent holds exactly the
    // workspace, the real target, and the link -- no accidental duplicate
    // directory at, or beside, the link's own path, and the link itself was
    // never replaced by a real directory.
    let scratch_entries: std::collections::BTreeSet<String> = std::fs::read_dir(&s.0)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    assert_eq!(
        scratch_entries,
        ["ws", "real-target", "target-link"]
            .into_iter()
            .map(str::to_owned)
            .collect(),
        "unexpected entries beside the symlink: {scratch_entries:?}"
    );
    assert!(
        std::fs::symlink_metadata(&link).unwrap().is_symlink(),
        "the link itself must still be a symlink, not replaced by a real directory"
    );

    // The workspace tree itself is untouched.
    let ws_entries: Vec<String> = std::fs::read_dir(s.p("ws"))
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    let expected = ["Cargo.toml", "src", "Cargo.lock"];
    for entry in &ws_entries {
        assert!(
            expected.contains(&entry.as_str()),
            "the recorder wrote {entry} into the workspace: only {expected:?} may be there"
        );
    }
}
