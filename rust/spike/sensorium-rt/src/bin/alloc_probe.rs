//! THROWAWAY SPIKE CODE. Counts heap allocations on the inert `enter` path.
//!
//! "Inert means no allocation on the `enter` path beyond the guard value
//! itself" is otherwise an unfalsifiable claim; a counting global allocator
//! turns it into a number. Prints that number and nothing else on stdout.
//!
//! The first `enter` reads the environment (which does allocate), so the
//! counter is zeroed after a warm-up call.

use std::alloc::{GlobalAlloc, Layout, System};
use std::hint::black_box;
use std::sync::atomic::{AtomicUsize, Ordering};

use sensorium_rt::{enter, Unit};

static ALLOCS: AtomicUsize = AtomicUsize::new(0);

struct Counting;

// SAFETY: every method forwards to `System`, which is a valid allocator; the
// counter has no effect on the returned pointers.
unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::Relaxed);
        System.alloc(layout)
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        System.dealloc(ptr, layout);
    }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::Relaxed);
        System.realloc(ptr, layout, new_size)
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::Relaxed);
        System.alloc_zeroed(layout)
    }
}

#[global_allocator]
static ALLOCATOR: Counting = Counting;

static UNIT: Unit = Unit::new("alloc-probe");

const ITERATIONS: u32 = 1000;

fn main() {
    // Warm-up: this is the call that reads the environment.
    {
        let g = enter(&UNIT, 0);
        black_box(&g);
    }
    ALLOCS.store(0, Ordering::Relaxed);
    for i in 0..ITERATIONS {
        let g = enter(&UNIT, black_box(i));
        black_box(&g);
    }
    let n = ALLOCS.load(Ordering::Relaxed);
    // One `println!` allocates; read the counter first.
    println!("{n}");
}
