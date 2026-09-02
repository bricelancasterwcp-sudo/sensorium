//! An integration test that spawns the package's OWN binary. Cargo exports its
//! path as `CARGO_BIN_EXE_<name>` to integration tests only, and the child
//! inherits `SENSORIUM_SPOOL`, so an instrumented child spools beside its
//! parent.

use std::process::Command;

#[test]
fn the_bin_runs_and_prints() {
    let out = Command::new(env!("CARGO_BIN_EXE_app-bin"))
        .output()
        .expect("spawn app-bin");
    assert!(out.status.success(), "app-bin exited {:?}", out.status);
    let stdout = String::from_utf8(out.stdout).expect("utf-8");
    assert!(
        stdout.contains("app-bin: 3+ext+deep+nested"),
        "unexpected stdout: {stdout}"
    );
}
