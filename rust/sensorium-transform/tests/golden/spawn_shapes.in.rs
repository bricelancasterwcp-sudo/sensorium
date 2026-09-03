//! Spawn shapes left alone, each declared with its reason -- and one `.spawn()`
//! that is not a thread at all.

use std::thread;

pub fn builder() -> u8 {
    thread::Builder::new()
        .name("worker".to_owned())
        .spawn(|| 3u8)
        .expect("spawn")
        .join()
        .unwrap()
}

pub fn scoped() -> u8 {
    let mut total = 0u8;
    thread::scope(|s| {
        let h = s.spawn(|| 4u8);
        total = h.join().unwrap();
    });
    total
}

pub fn command_spawn_is_not_a_thread() -> std::io::Result<std::process::Child> {
    std::process::Command::new("true").spawn()
}
