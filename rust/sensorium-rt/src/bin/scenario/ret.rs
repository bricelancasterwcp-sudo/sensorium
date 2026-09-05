//! Shapes with no return value, the exit-operand (`ret`) outcomes, the `Drop`
//! races around a closing frame, and the header/site-word edges.

// ---------------------------------------------------------------------------
// Shapes with no return value
// ---------------------------------------------------------------------------

/// One guard on the main thread. Site index 7.
pub(crate) fn main_only() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 7);
}

/// An `enter` reached from inside the runtime must be inert; the one after it
/// must not be.
pub(crate) fn reentrant() {
    sensorium_rt::__in_runtime(|| {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 90);
    });
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 91);
}

/// A `-> ()` function: the transformer emits an `enter` and NO `ret`, so its
/// RETURN carries outcome 0 and tag 0. Site index 15.
pub(crate) fn ret_unit_scenario() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 15);
    std::hint::black_box(1u8);
}

// ---------------------------------------------------------------------------
// Outcomes
// ---------------------------------------------------------------------------

/// The injected exit-operand form written out longhand, once, so the `sret!`
/// macro below it is provably the same text.
fn ret_verbatim() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 10);
    ::sensorium_rt::ret(
        &crate::__SENSORIUM_UNIT,
        10,
        |__r| {
            use ::sensorium_rt::probe::*;
            ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
        },
        Ok(3),
    )
}

pub(crate) fn ret_ok_scenario() {
    let r = ret_verbatim();
    println!("returned {r:?}");
}

fn returns_err() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 11);
    sret!(11, Err("x".to_owned()))
}

pub(crate) fn ret_err_scenario() {
    let r = returns_err();
    println!("returned {r:?}");
}

/// Site 12 returns `Err`; site 13's `?` propagates it, so site 13's tail is
/// never reached and its frame closes with nothing stashed.
fn question_inner() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 12);
    sret!(12, Err("propagated".to_owned()))
}

fn question_outer() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 13);
    let v = question_inner()?;
    sret!(13, Ok(v))
}

pub(crate) fn ret_question_scenario() {
    let r = question_outer();
    println!("returned {r:?}");
}

/// The `panic!` and the `line!()` that reports it are the SAME source line, so
/// a test compares the hook's location against the source rather than against a
/// number written down twice. `#[rustfmt::skip]` is what keeps them there.
#[rustfmt::skip]
fn panics() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 14);
    println!("panic_site {}:{}", file!(), line!()); panic!("boom");
}

/// No hook of its own: the runtime's hook is the one under test, and the
/// message the previous hook prints is what E7 compares.
pub(crate) fn ret_panic_scenario() {
    let r = std::panic::catch_unwind(panics);
    assert!(r.is_err(), "the scenario must actually unwind");
    println!("unwound 1");
}

/// A stash that belongs to no open frame. Site 60's `ret` runs while site 60
/// has no guard -- the shape instrumented code takes when an `enter`'s CALL
/// could not be written (a broken spool) but the wrapped exit operand still
/// runs. The next frame to close, site 61, must NOT take that value.
pub(crate) fn ret_mismatch_scenario() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 61);
    let orphan: Result<u8, String> = sret!(60, Ok(7));
    println!("orphan {orphan:?}");
}

// ---------------------------------------------------------------------------
// A `Drop` that runs instrumented code between an exit operand and its guard
// ---------------------------------------------------------------------------

/// A local whose `Drop` calls instrumented code. Declared AFTER the guard, so it
/// drops BEFORE it -- which is the window in which a single-slot stash gets
/// wiped and the outer frame silently reads `none`.
struct DropCallsInstrumented;

impl Drop for DropCallsInstrumented {
    fn drop(&mut self) {
        inner_unit_fn();
    }
}

/// A `-> ()` fn: `enter` and no `ret`, so it stashes nothing of its own.
fn inner_unit_fn() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 71);
}

fn outer_with_dropping_local() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 70);
    let _local = DropCallsInstrumented;
    sret!(70, Err("outer".to_owned()))
}

pub(crate) fn drop_calls_instrumented_scenario() {
    let r = outer_with_dropping_local();
    println!("returned {r:?}");
}

/// A `Drop` that calls the SAME instrumented function one level down. Both
/// frames are site 72; only their depths tell them apart.
struct DropRecurses(u8);

impl Drop for DropRecurses {
    fn drop(&mut self) {
        if self.0 > 0 {
            let _ = std::hint::black_box(recursive_frame(self.0 - 1));
        }
    }
}

fn recursive_frame(n: u8) -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 72);
    let _local = DropRecurses(n);
    sret!(72, Ok(n))
}

pub(crate) fn drop_recurses_scenario(n: u8) {
    let r = recursive_frame(n);
    println!("returned {r:?}");
    println!("frames {}", u32::from(n) + 1);
}

/// The same shape, except the inner frame leaves by `?` and so stashes NOTHING.
/// Matching on the site alone would let it take the OUTER frame's capture --
/// same site, still pending -- and report `Ok(9)` as its own while the outer
/// frame closed `none`. The depth is what forbids it.
struct DropRecursesBypass(bool);

impl Drop for DropRecursesBypass {
    fn drop(&mut self) {
        if self.0 {
            let _ = std::hint::black_box(bypass_frame(false));
        }
    }
}

fn returns_err_at_75() -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 75);
    sret!(75, Err("bypass".to_owned()))
}

fn bypass_frame(recurse: bool) -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 74);
    let _local = DropRecursesBypass(recurse);
    if !recurse {
        let v = returns_err_at_75()?;
        return sret!(74, Ok(v));
    }
    sret!(74, Ok(9))
}

pub(crate) fn drop_recurses_bypass_scenario() {
    let r = bypass_frame(true);
    println!("returned {r:?}");
}

// ---------------------------------------------------------------------------
// Header and site-word edges
// ---------------------------------------------------------------------------

/// A site index that needs all 24 of its bits.
pub(crate) fn wide_site() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 0x00ab_cdef);
}

/// A thread with no name at all: `name_len` is 0 and records start at byte 28.
pub(crate) fn unnamed_thread() {
    let h = std::thread::spawn(|| {
        let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 76);
    });
    h.join().expect("join");
}
