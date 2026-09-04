//! Run probe: a `MutexGuard` held across a wrapped tail, and one that is a
//! temporary of the tail itself. A second thread's `try_lock` must succeed and
//! fail at exactly the same points in both builds.

use std::sync::{Arc, Mutex};
use std::thread;

fn try_from_another_thread(m: &Arc<Mutex<u32>>) -> bool {@G(7)
    let mine = Arc::clone(m);
    @R(7)@C(@I(thread::spawn;src/lib.rs:10)move || mine.try_lock().is_ok()).join().unwrap()@E
}

fn held_across_tail(m: &Arc<Mutex<u32>>, log: &mut Vec<String>) -> u32 {@G(8)
    let guard = m.lock().expect("not poisoned");
    log.push(format!("inside, free: {}", try_from_another_thread(m)));
    @R(8)*guard + 1@E
}

fn temporary_in_tail(m: &Arc<Mutex<u32>>) -> u32 {@G(9)
    @R(9)*m.lock().expect("not poisoned") + 2@E
}

fn main() {@G(10)
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
}@U
