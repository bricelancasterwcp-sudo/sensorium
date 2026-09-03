//! A child that dies inside an open frame.
//!
//! The test spawns `app-bin --abort`, which calls `std::process::abort()` from
//! inside an instrumented fn. Three things follow, and each is a check: the
//! child's records are on disk anyway (the spool is a `MAP_SHARED` mapping the
//! kernel owns), its trace reads `exit_status_basis: unwitnessed` because
//! sensorium's runner did not start it, and its parent's `child_runs` names it
//! (`rust/HONESTY.md` §4, §5, §6).

use std::process::Command;

#[test]
fn the_bin_aborts_inside_a_frame() {
    let out = Command::new(env!("CARGO_BIN_EXE_app-bin"))
        .arg("--abort")
        .output()
        .expect("spawn app-bin --abort");
    // SIGABRT is 6, and a shell reports it as 134. `code()` is None for a
    // signalled child, which is the case being set up here.
    assert!(
        out.status.code().is_none(),
        "app-bin --abort exited normally with {:?}; the abort did not happen",
        out.status.code()
    );
    let stdout = String::from_utf8(out.stdout).expect("utf-8");
    assert!(
        stdout.contains("app-bin: aborting after work(1)"),
        "the child did not reach the abort: {stdout}"
    );
}
