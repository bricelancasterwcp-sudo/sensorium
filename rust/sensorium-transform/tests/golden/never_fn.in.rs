//! `-> !` has no value to probe: a guard, no wrap, and `ret: never`.

pub fn stop() -> ! {
    panic!("stop");
}

pub fn spin() -> ! {
    loop {
        std::hint::spin_loop();
    }
}
