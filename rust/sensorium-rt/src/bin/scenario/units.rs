//! Two units in one process, and the 256-unit ceiling.

use sensorium_rt::{enter, Unit};

use crate::UNIT_B;

/// 253 distinct units. With the crate's own unit and `UNIT_255` that is 255
/// registrations, so `UNIT_256` is the one that must be refused.
static MANY: [Unit; 253] = [const { Unit::new("many") }; 253];
static UNIT_255: Unit = Unit::new("the-255th-unit");
static UNIT_256: Unit = Unit::new("the-256th-unit");

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

pub(crate) fn two_units() {
    let _a = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 80);
    let _b = ::sensorium_rt::enter(&UNIT_B, 81);
}

/// 1 + 253 + 1 = 255 registrations, then a 256th that must be refused, then two
/// more `enter`s that must record nothing: one on a brand-new unit and one on a
/// unit that registered successfully long before the refusal.
///
/// The frame at site 300 is held OPEN across the refusal, because refusal gates
/// `enter` and never the closing of a frame that is already open -- if it did,
/// a converter's frame stack would go negative.
pub(crate) fn unit_ceiling() {
    let _outer = enter(&crate::__SENSORIUM_UNIT, 300);
    for (i, unit) in MANY.iter().enumerate() {
        let _g = enter(unit, i as u32);
    }
    {
        let _g = enter(&UNIT_255, 254);
    }
    {
        let _g = enter(&UNIT_256, 255);
    }
    {
        let _g = enter(&UNIT_B, 256);
    }
    {
        let _g = enter(&MANY[0], 257);
    }
    println!("attempted 258");
}
