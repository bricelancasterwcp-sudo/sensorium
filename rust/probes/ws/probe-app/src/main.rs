//! The probe's own binary, spawned by two integration tests: once to run
//! normally (`spawn_bin.rs`) and once to abort inside an open frame
//! (`abort_child.rs`). Both are children the runner did NOT start, so both
//! traces read `exit: unwitnessed` while their parent's `child_runs` names
//! them.

fn main() {
    let aborting = std::env::args().any(|a| a == "--abort");
    if aborting {
        probe_app::abort_mid_frame();
    }
    println!("app-bin: {}", probe_app::describe());
    println!("app-bin: work(3) = {}", probe_app::work(3));
}
