//! `spawn_child`: the names threads spawned by workspace code carry, and the
//! proof that carrying them changes nothing else about the spawn.
//!
//! Rung 1 measured the hole this closes: 4 of 57 emitting non-main threads in a
//! bloomery `--lib` trace carried no name at all, because libtest names the
//! thread it runs a test on and nothing names a thread a *test* spawns
//! (findings §5.20). A task with no name is a task `diff` can only compare as
//! one of an unnamed multiset, and `tree` prints one the reader cannot identify.
//!
//! The names are read out of the spool header, which is written at the thread's
//! FIRST event -- so every arm here is also a check that the name was set before
//! any instrumented code ran in the child.

mod common;

use common::{Spec, TempDir, KIND_PANIC, OUTCOME_PANIC};

#[test]
fn a_child_spawned_from_main_is_named_for_its_site_alone() {
    let dir = TempDir::reserved("spawn-from-main");
    let run = Spec::new("spawn-from-main").spool(dir.path()).run();
    let site = run.says("site");
    assert!(
        site.contains("scenario.rs:"),
        "the site is the transformer's <file>:<line>, got {site:?}"
    );
    let child = dir.spool_named(&format!("spawn@{site}"));
    assert_ne!(child.serial, 1, "the child is not the main thread");
    assert_eq!(
        run.says("child_os_name"),
        "<none>",
        "the task name is the recorder's; the child's OS thread name is what          `std::thread::spawn` gives it, which is nothing"
    );
    assert_eq!(
        dir.spool(1).name,
        "main",
        "and the main thread is NOT a task: its name is std's own, and a child \
         of main inherits no `main :: ` prefix"
    );
}

#[test]
fn a_child_of_a_named_thread_carries_its_name_and_a_grandchild_carries_both() {
    let dir = TempDir::reserved("spawn-grandchild");
    let run = Spec::new("spawn-grandchild").spool(dir.path()).run();
    let parent = run.says("parent");
    let child_site = run.says("site_child");
    let grandchild_site = run.says("site_grandchild");
    assert_ne!(child_site, grandchild_site, "two distinct spawn sites");

    let child_name = format!("{parent} :: spawn@{child_site}");
    let grandchild_name = format!("{child_name} :: spawn@{grandchild_site}");
    let names: Vec<String> = dir.spools().into_iter().map(|s| s.name).collect();
    assert!(
        names.contains(&child_name),
        "no spool named {child_name:?}; found {names:?}"
    );
    assert!(
        names.contains(&grandchild_name),
        "a grandchild carries both segments; no spool named {grandchild_name:?} \
         among {names:?}"
    );
}

#[test]
fn a_parent_with_an_empty_name_is_a_parent_with_no_name() {
    let dir = TempDir::reserved("spawn-empty-parent");
    let run = Spec::new("spawn-empty-named-parent")
        .spool(dir.path())
        .run();
    let site = run.says("site");
    let names: Vec<String> = dir.spools().into_iter().map(|s| s.name).collect();
    assert!(
        names.contains(&format!("spawn@{site}")),
        "an empty parent name is no parent name, not a `\" :: \"` prefix onto \
         nothing; found {names:?}"
    );
}

#[test]
fn a_thread_spawned_the_ordinary_way_carries_no_name_at_all() {
    let dir = TempDir::reserved("spawn-dependency-shaped");
    Spec::new("unnamed-thread").spool(dir.path()).run();
    let names: Vec<String> = dir.spools().into_iter().map(|s| s.name).collect();
    assert!(
        names.contains(&String::new()),
        "a `std::thread::spawn` the transformer did not rewrite -- the shape a \
         dependency's own thread has -- is unnamed, and the trace says so \
         rather than inventing one; found {names:?}"
    );
}

#[test]
fn the_join_handle_returns_the_closures_value() {
    let dir = TempDir::reserved("spawn-value");
    let run = Spec::new("spawn-value").spool(dir.path()).run();
    assert_eq!(run.says("joined"), "41");
}

#[test]
fn spawn_child_is_a_drop_in_when_the_recorder_is_not_recording() {
    let sandbox = TempDir::created("spawn-off-sandbox");
    let dir = TempDir::reserved("spawn-off");
    let run = Spec::new("spawn-value")
        .sandbox(sandbox.path())
        .spool(dir.path())
        .tier("off")
        .run();
    assert_eq!(
        run.says("joined"),
        "41",
        "the handle is std's own, whatever the tier"
    );
    assert!(
        !dir.exists(),
        "tier off derives no name and records nothing"
    );
    sandbox.assert_untouched("spawn_child at tier off");
}

#[test]
fn a_child_that_panics_re_raises_through_join_exactly_as_std_does() {
    let dir = TempDir::reserved("spawn-panics");
    let run = Spec::new("spawn-panics").spool(dir.path()).run();
    assert_eq!(run.says("join_err"), "1", "join() returned the panic");
    assert_eq!(
        run.says("join_msg"),
        "child boom",
        "and the payload the child panicked with, unchanged"
    );
    assert_eq!(run.says("survived"), "1", "the parent was not unwound");

    // The same run with no recorder at all: the propagation is identical, which
    // is the half of "drop-in" a spool cannot show.
    let plain = Spec::new("spawn-panics").run();
    assert_eq!(plain.says("join_err"), run.says("join_err"));
    assert_eq!(plain.says("join_msg"), run.says("join_msg"));

    let site = run.says("site");
    let child = dir.spool_named(&format!("spawn@{site}"));
    let panics = child.of_kind(KIND_PANIC);
    assert_eq!(
        panics.len(),
        1,
        "the PANIC record is on the panicking thread's OWN spool"
    );
    assert_eq!(panics[0].panic_value().1, "child boom");
    assert_eq!(child.the_return(205).outcome, OUTCOME_PANIC);
    assert!(
        dir.spool(1).of_kind(KIND_PANIC).is_empty(),
        "and not on the thread that joined it"
    );
}
