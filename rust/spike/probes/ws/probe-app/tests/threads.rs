//! An integration test that spawns a thread: the shape the runtime's per-thread
//! serials and spools have to survive.

use std::thread;

#[test]
fn a_spawned_thread_does_work() {
    let handle = thread::Builder::new()
        .name("probe-worker".to_owned())
        .spawn(|| probe_app::work(3))
        .expect("spawn");
    assert_eq!(handle.join().expect("join"), 8);
}

#[test]
fn the_main_thread_also_works() {
    assert_eq!(probe_app::describe(), "3+ext+deep+nested");
}
