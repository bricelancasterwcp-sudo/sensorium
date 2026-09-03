//! `-> !` has no value to probe: a guard, no wrap, and `ret: never`.

pub fn stop() -> ! {@G(7)
    panic!("stop");
}

pub fn spin() -> ! {@G(8)
    loop {
        std::hint::spin_loop();
    }
}@U
