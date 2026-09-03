//! Task names: what a thread the workspace spawned is called, and what the
//! spool header carries.
//!
//! Rung 1 measured the hole this closes: in a bloomery `--lib` trace, 53 of 57
//! emitting non-main threads carried the test's own name -- libtest names the
//! thread it runs a `#[test]` on -- and **4 carried nothing at all**, because
//! nothing names a thread a *test* spawns (findings §5.20). A task with no name
//! is one `diff` can compare only as a member of an unnamed multiset and one
//! `tree` prints without an address. [`spawn_child`] is what names them; a
//! thread a *dependency* spawned still has none, and `rust/HONESTY.md` §3 says
//! so rather than inventing one.
//!
//! **Main is not a task.** §3 makes the main thread serial 1 and a task row
//! belongs to every *non-main* thread that emits, so a child of main inherits no
//! `main :: ` prefix even though std names the main thread `"main"`. The spool
//! *header* is a different field -- it carries the thread's name, `"main"`
//! included -- and the converter is what turns headers into task rows.

use std::cell::RefCell;
use std::thread::JoinHandle;

use crate::ffi;

thread_local! {
    /// The task name [`spawn_child`] gave this thread. `None` on the main
    /// thread, on threads libtest named, and on threads a dependency spawned.
    static TASK_NAME: RefCell<Option<Box<str>>> = const { RefCell::new(None) };
}

/// `std::thread::spawn` with a name, and nothing else changed.
///
/// The transformer rewrites `std::thread::spawn(f)` at an instrumented site to
/// `::sensorium_rt::spawn_child(SITE, f)`, where `SITE` is the
/// `"<workspace-relative file>:<line>"` it bakes in. The child's task name is
/// `"<parent task name> :: spawn@<site>"`, or `"spawn@<site>"` when the
/// spawning thread has no task name of its own, and a grandchild carries both
/// segments.
///
/// **A drop-in.** The bounds, the `JoinHandle`, the value `join()` returns, the
/// panic it re-raises and the child's OS thread name (std gives it none) are
/// `std::thread::spawn`'s own. When the recorder is not recording this *is*
/// `std::thread::spawn`: no name is derived and nothing is allocated.
///
/// The name is set in the child, before `f` runs, so it is in place before the
/// first instrumented statement of `f` -- which is what writes the spool header.
pub fn spawn_child<F, T>(site: &'static str, f: F) -> JoinHandle<T>
where
    F: FnOnce() -> T + Send + 'static,
    T: Send + 'static,
{
    if !crate::recording() {
        return std::thread::spawn(f);
    }
    let name = derive(site);
    std::thread::spawn(move || {
        set_task_name(name);
        f()
    })
}

/// The child's name, derived on the PARENT thread: the parent's own task name
/// is a thread-local, and the child does not have one yet.
fn derive(site: &str) -> String {
    match parent_task_name() {
        Some(parent) => format!("{parent} :: spawn@{site}"),
        None => format!("spawn@{site}"),
    }
}

/// The task name to inherit from this thread: the override first, then the OS
/// thread name -- except on the main thread, which is not a task.
///
/// An empty OS name is treated as none. The header writes an unnamed thread as
/// zero bytes, so a name of `" :: spawn@…"` would claim a parent that no reader
/// could ever see.
fn parent_task_name() -> Option<String> {
    if let Some(name) = override_name() {
        return Some(name);
    }
    if ffi::is_main_thread() {
        return None;
    }
    match std::thread::current().name() {
        Some(n) if !n.is_empty() => Some(n.to_owned()),
        _ => None,
    }
}

fn override_name() -> Option<String> {
    TASK_NAME
        .try_with(|c| c.borrow().as_deref().map(str::to_owned))
        .ok()
        .flatten()
}

fn set_task_name(name: String) {
    let _ = TASK_NAME.try_with(|c| {
        if let Ok(mut slot) = c.try_borrow_mut() {
            *slot = Some(name.into_boxed_str());
        }
    });
}

/// The name this thread's spool header carries: the task name when it has one,
/// else the OS thread name (`"main"` on the main thread, whatever `Builder` was
/// given elsewhere), else empty.
pub(crate) fn header_name() -> String {
    match override_name() {
        Some(name) => name,
        None => std::thread::current().name().unwrap_or("").to_owned(),
    }
}
