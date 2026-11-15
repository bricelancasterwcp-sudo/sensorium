//! A short same-site loop. The integration test sets `SENSORIUM_MAX_CALLS`
//! and reads how many argument closures actually ran.

use std::cell::Cell;

pub(crate) fn cap_loop() {
    let formatted = Cell::new(0u32);
    for _ in 0..6 {
        let _sens_guard = sensorium_rt::enter_args(&crate::__SENSORIUM_UNIT, 70, || {
            formatted.set(formatted.get() + 1);
            []
        });
    }
    println!("formatted {}", formatted.get());
}
