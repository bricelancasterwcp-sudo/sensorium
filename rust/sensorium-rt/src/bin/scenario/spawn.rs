//! `spawn_child` and thread lifetime: the names children carry, a thread that
//! panics having recorded nothing, and one whose first spool opens mid-unwind.
//!
//! The `SITE_*` site strings this module prints live in the dispatch file
//! (`super`) because `file!()` is part of their value: `tests/spawn.rs` pins the
//! `<file>:<line>` shape against the binary's own source file name.

use crate::{SITE_CHILD, SITE_GRANDCHILD, SITE_PANIC, SITE_VALUE};

// ---------------------------------------------------------------------------
// spawn_child
// ---------------------------------------------------------------------------

/// libtest's shape: it names the thread it runs a `#[test]` on with the test's
/// own path, and a thread that test spawns is what rung 1 found unnamed.
const WORKER: &str = "sensorium_rt::tests::worker";

/// A child of the MAIN thread. Main is not a task, so the child's name is its
/// site alone -- no `main :: ` prefix.
pub(crate) fn spawn_from_main() {
    // `main` is instrumented too, so the main thread has a spool of its own to
    // be unnamed-as-a-task in.
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 206);
    println!("site {SITE_CHILD}");
    let h = sensorium_rt::spawn_child(SITE_CHILD, || {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 200);
        // The OS thread name is std's own -- `spawn_child` names the TASK, in a
        // thread-local of its own, and a child of `std::thread::spawn` has no OS
        // name. An implementation that reached for `Builder::name` instead would
        // be changing something the program itself can see.
        println!(
            "child_os_name {}",
            std::thread::current().name().unwrap_or("<none>")
        );
    });
    h.join().expect("join");
}

/// A parent whose OS name is the empty string. An empty name is no name: the
/// header writes an unnamed thread as zero bytes, so a derived `" :: spawn@..."`
/// would name a parent no reader could ever see.
pub(crate) fn spawn_empty_named_parent() {
    println!("site {SITE_CHILD}");
    std::thread::Builder::new()
        .name(String::new())
        .spawn(|| {
            let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 208);
            let child = sensorium_rt::spawn_child(SITE_CHILD, || {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 209);
            });
            child.join().expect("join the child");
        })
        .expect("spawn")
        .join()
        .expect("join the empty-named parent");
}

/// A thread that panics having recorded NOTHING. The hook opens no spool -- that
/// is what makes it unable to fail, and so unable to abort a panicking process
/// (`src/panic.rs`) -- so this thread leaves no file at all.
/// A local whose `Drop` runs instrumented code, so this thread's FIRST spool is
/// opened during the unwind -- after the hook has already cut an over-long panic
/// message it had nowhere to write.
struct EntersOnDrop;

impl Drop for EntersOnDrop {
    fn drop(&mut self) {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 211);
    }
}

/// The hook cuts a 6000-byte message on a thread with no spool, and the spool
/// that thread opens a moment later must not carry a truncation counter for a
/// record that was never written.
pub(crate) fn panic_truncated_before_spool() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 212);
    let h = std::thread::spawn(|| {
        let _local = EntersOnDrop;
        let msg = "\u{20ac}".repeat(2000);
        println!("msg_bytes {}", msg.len());
        panic!("{msg}");
    });
    h.join().expect_err("the child must have panicked");
    println!("survived 1");
}

pub(crate) fn panic_unrecorded_thread() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 210);
    let h = std::thread::spawn(|| panic!("orphan boom"));
    h.join().expect_err("the child must have panicked");
    println!("survived 1");
}

/// A named thread, its child and its grandchild: three names, two `::` joins.
pub(crate) fn spawn_grandchild() {
    println!("site_child {SITE_CHILD}");
    println!("site_grandchild {SITE_GRANDCHILD}");
    println!("parent {WORKER}");
    std::thread::Builder::new()
        .name(WORKER.to_owned())
        .spawn(|| {
            let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 201);
            let child = sensorium_rt::spawn_child(SITE_CHILD, || {
                let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 202);
                let grandchild = sensorium_rt::spawn_child(SITE_GRANDCHILD, || {
                    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 203);
                });
                grandchild.join().expect("join the grandchild");
            });
            child.join().expect("join the child");
        })
        .expect("spawn")
        .join()
        .expect("join the worker");
}

/// The handle is std's own: it carries the closure's value back.
pub(crate) fn spawn_value() {
    let h = sensorium_rt::spawn_child(SITE_VALUE, || {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 204);
        41u32
    });
    println!("joined {}", h.join().expect("join"));
}

/// And it re-raises the child's panic, payload unchanged, without touching the
/// thread that joined.
pub(crate) fn spawn_panics() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 207);
    println!("site {SITE_PANIC}");
    let h = sensorium_rt::spawn_child(SITE_PANIC, || {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 205);
        panic!("child boom");
    });
    let payload = h.join().expect_err("the child must have panicked");
    let msg = payload
        .downcast_ref::<&str>()
        .copied()
        .unwrap_or("<not a &str>");
    println!("join_msg {msg}");
    println!("join_err 1");
    println!("survived 1");
}
