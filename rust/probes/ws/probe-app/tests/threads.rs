//! The naming check's probe: a thread spawned by `std::thread::spawn` inside a
//! test, doing instrumented work.
//!
//! The transformer rewrites the callee to `::sensorium_rt::spawn_child` and
//! bakes the site in. The site is the enclosing named item's qualname and this
//! spawn's rank among that item's wrapped spawns, so the child's task name is
//! `<the test's own name> :: spawn@<the test's own name>#1` -- the spawn is
//! directly in this test's body and is the only one in it (`rust/HONESTY.md`
//! §3). `std::thread::spawn`, not `Builder::spawn`: the builder form carries a
//! name of its own and is declared rather than rewritten.

use std::thread;

#[test]
fn a_spawned_thread_does_instrumented_work() {
    let handle = thread::spawn(|| probe_app::work(3));
    assert_eq!(handle.join().expect("join"), 8);
}

#[test]
fn the_main_thread_also_works() {
    assert_eq!(probe_app::describe(), "3+ext+deep+nested");
}
