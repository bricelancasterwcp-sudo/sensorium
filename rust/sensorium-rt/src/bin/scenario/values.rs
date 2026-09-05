//! The value-capture edges: no `Debug`, a huge value, a `Debug` that stops
//! early, one that panics, one that writes nothing, and repeated truncation.

use std::fmt;

// ---------------------------------------------------------------------------
// Values
// ---------------------------------------------------------------------------

struct NoDbg(#[allow(dead_code)] u8);

struct PanicDbg;

/// A hand-written `Debug` impl that propagates the writer's error, which is
/// what most hand-written ones do. std's collection impls do NOT (see
/// `rust/HONESTY.md` §2), so this is the shape whose cost the cap actually
/// bounds.
struct EarlyStop(u32);

impl fmt::Debug for EarlyStop {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for i in 0..self.0 {
            write!(f, "{i},")?;
        }
        Ok(())
    }
}

impl fmt::Debug for PanicDbg {
    fn fmt(&self, _f: &mut fmt::Formatter<'_>) -> fmt::Result {
        panic!("this Debug impl panics on purpose");
    }
}

fn returns_nodebug() -> NoDbg {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 20);
    sret!(20, NoDbg(9))
}

pub(crate) fn value_nodebug() {
    let v = returns_nodebug();
    println!("returned {}", v.0);
}

fn returns_big(n: u32) -> Vec<u8> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 21);
    let big = std::hint::black_box(vec![7u8; n as usize]);
    let started = std::time::Instant::now();
    let out = sret!(21, big);
    println!("capture_ns {}", started.elapsed().as_nanos());
    out
}

pub(crate) fn value_big(n: u32) {
    let v = returns_big(n);
    println!("returned {}", v.len());
}

/// A `Debug` impl that writes nothing. Its capture is `Some("")` -- a value that
/// WAS read and renders empty -- which the wire must keep distinct from a value
/// that could not be read at all.
struct EmptyDbg;

impl fmt::Debug for EmptyDbg {
    fn fmt(&self, _f: &mut fmt::Formatter<'_>) -> fmt::Result {
        Ok(())
    }
}

fn returns_empty_debug() -> EmptyDbg {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 25);
    sret!(25, EmptyDbg)
}

pub(crate) fn value_empty_debug() {
    let v = returns_empty_debug();
    println!("returned {v:?}.");
}

fn returns_early_stop(n: u32) -> EarlyStop {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 24);
    let v = std::hint::black_box(EarlyStop(n));
    let started = std::time::Instant::now();
    let out = sret!(24, v);
    println!("capture_ns {}", started.elapsed().as_nanos());
    out
}

pub(crate) fn value_early_stop(n: u32) {
    let v = returns_early_stop(n);
    println!("returned {}", v.0);
}

fn returns_panicking_debug() -> PanicDbg {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 22);
    sret!(22, PanicDbg)
}

pub(crate) fn value_panic_debug() {
    let v = returns_panicking_debug();
    std::hint::black_box(&v);
    println!("survived 1");
}

fn returns_long(i: u32) -> Vec<u32> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 23);
    sret!(23, (0..500u32).map(|x| x + i).collect::<Vec<u32>>())
}

/// `n` returns that all truncate, so the thread header's counter has a value to
/// be wrong about.
pub(crate) fn value_truncations(n: u32) {
    for i in 0..n {
        std::hint::black_box(returns_long(i));
    }
    println!("truncations {n}");
}
