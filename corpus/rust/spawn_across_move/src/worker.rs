pub fn start(delta: u32) -> u32 {
    std::thread::spawn(move || crate::apply(0, delta))
        .join()
        .expect("worker joined")
}
