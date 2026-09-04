//! Run probe: a `MutexGuard` held across a wrapped tail, and one that is a
//! temporary of the tail itself. A second thread's `try_lock` must succeed and
//! fail at exactly the same points in both builds.

use std::sync::{Arc, Mutex};
use std::thread;

fn try_from_another_thread(m: &Arc<Mutex<u32>>) -> bool {
    let mine = Arc::clone(m);
    thread::spawn(move || mine.try_lock().is_ok()).join().unwrap()
}

fn held_across_tail(m: &Arc<Mutex<u32>>, log: &mut Vec<String>) -> u32 {
    let guard = m.lock().expect("not poisoned");
    log.push(format!("inside, free: {}", try_from_another_thread(m)));
    *guard + 1
}

fn temporary_in_tail(m: &Arc<Mutex<u32>>) -> u32 {
    *m.lock().expect("not poisoned") + 2
}

fn main() {
    let m = Arc::new(Mutex::new(41u32));
    let mut log = Vec::new();
    let a = held_across_tail(&m, &mut log);
    log.push(format!("after, free: {}", try_from_another_thread(&m)));
    let b = temporary_in_tail(&m);
    log.push(format!("after temporary, free: {}", try_from_another_thread(&m)));
    for line in &log {
        println!("{line}");
    }
    println!("values {a} {b}");
}
