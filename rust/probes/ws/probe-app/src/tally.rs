//! A unit that USES an instrumented dependency, with the use at the very top.
//!
//! This is bloomery's shape, and it is here because the probe did not have it.
//! The first item of this module is a `use` of a crate the wrapper
//! instruments, so rustc resolves `probe_core`'s rmeta -- and with it
//! `probe_core`'s own `sensorium_rt` -- before it ever meets this crate's
//! `::sensorium_rt::Unit` static. A transitive crate is resolved through the
//! `-L dependency` search paths, not through `--extern`, so with `--extern`
//! alone this module fails `E0463: can't find crate for sensorium_rt which
//! probe_core depends on`.
//!
//! Measured 2026-09-03: `bloomery-daemon` failed exactly here, on a submodule
//! opening with `use bloomery_core::journal::Journal;`, while every unit of
//! this probe compiled -- the probe's own crate roots happened to bind
//! `sensorium_rt` before their `probe_core` uses, and passed on resolver-order
//! luck. This module removes the luck.

use probe_core::Counter;

/// Instrumented work through a type that came from an instrumented crate.
#[must_use]
pub fn tally(n: u32) -> u32 {
    let mut counter = Counter::new();
    for _ in 0..n {
        counter.bump();
    }
    counter.bump()
}
