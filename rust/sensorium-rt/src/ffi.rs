//! The libc surface this crate uses, declared by hand.
//!
//! `sensorium-rt` has NO dependencies (plan decision D1): the driver compiles
//! it with one bare `rustc --crate-type rlib --edition 2021 -C opt-level=3
//! src/lib.rs` invocation into a directory of its own, and the wrapper links
//! it into a target build with `--extern sensorium_rt=<rlib>` plus
//! `-L dependency=<that directory>`. Having no dependencies is what makes the
//! search path safe: the directory holds exactly one rlib and offers rustc
//! nothing to choose between, whereas a `libc` crate in the graph would have
//! to be resolved, versioned and picked -- exactly the single-candidate hazard
//! D1 removes. Seven `extern "C"` lines cost less.
//!
//! Every constant below names the header it is transcribed from. v1 is
//! Linux-only (spec §4: thread serials come from `gettid()`/`getpid()`), and
//! `lib.rs` refuses to compile anywhere else, so these are the Linux/glibc
//! values on the one ABI this crate supports. `gettid` as a libc function needs
//! glibc 2.30 or newer.

#![allow(non_camel_case_types)]

use std::ffi::c_void;

/// `<bits/types.h>`: `__pid_t` is a 32-bit signed integer on Linux.
pub type pid_t = i32;
/// `<bits/types.h>`: `__off_t` is 64 bits on every 64-bit Linux ABI.
pub type off_t = i64;

/// `<bits/types/struct_timespec.h>`.
#[repr(C)]
pub struct timespec {
    pub tv_sec: i64,
    pub tv_nsec: i64,
}

/// `<bits/time.h>`: wall-clock time since the epoch, which steps and jumps.
pub const CLOCK_REALTIME: i32 = 0;
/// `<bits/time.h>`: a monotonic clock, which is what every `ts_ns` is.
pub const CLOCK_MONOTONIC: i32 = 1;

/// `<bits/mman-linux.h>`.
pub const PROT_READ: i32 = 0x1;
/// `<bits/mman-linux.h>`.
pub const PROT_WRITE: i32 = 0x2;
/// `<bits/mman-linux.h>`: writes go to the file, and the kernel owns the pages
/// from the moment they are dirtied -- which is the whole durability claim of
/// `rust/HONESTY.md` §4.
pub const MAP_SHARED: i32 = 0x01;

/// `<sys/mman.h>`: `mmap` reports failure as `(void *) -1`, not as null.
pub const MAP_FAILED: *mut c_void = usize::MAX as *mut c_void;

extern "C" {
    /// `<unistd.h>`. Linux: the main thread is the one whose thread id equals
    /// the process id.
    pub fn gettid() -> pid_t;
    /// `<unistd.h>`.
    pub fn getpid() -> pid_t;
    /// `<unistd.h>`.
    pub fn getppid() -> pid_t;
    /// `<time.h>`.
    pub fn clock_gettime(clock_id: i32, tp: *mut timespec) -> i32;
    /// `<sys/mman.h>`.
    pub fn mmap(
        addr: *mut c_void,
        length: usize,
        prot: i32,
        flags: i32,
        fd: i32,
        offset: off_t,
    ) -> *mut c_void;
    /// `<sys/mman.h>`.
    pub fn munmap(addr: *mut c_void, length: usize) -> i32;
    /// `<unistd.h>`.
    pub fn ftruncate(fd: i32, length: off_t) -> i32;
}

/// `CLOCK_MONOTONIC` nanoseconds: every record's `ts_ns`.
#[must_use]
pub fn now_ns() -> u64 {
    clock_ns(CLOCK_MONOTONIC)
}

/// `CLOCK_REALTIME` nanoseconds since the epoch: the proc header's
/// `start_realtime_ns`, read at the same instant as `start_ns` so a reader can
/// place the monotonic timeline on a wall clock.
#[must_use]
pub fn now_realtime_ns() -> u64 {
    clock_ns(CLOCK_REALTIME)
}

fn clock_ns(clock_id: i32) -> u64 {
    let mut ts = timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    // SAFETY: `ts` is a live, fully initialised `timespec` this frame owns, and
    // `clock_gettime` writes at most that many bytes through the pointer.
    unsafe {
        clock_gettime(clock_id, &mut ts);
    }
    (ts.tv_sec as u64)
        .wrapping_mul(1_000_000_000)
        .wrapping_add(ts.tv_nsec as u64)
}

/// True on the thread the process started on.
#[must_use]
pub fn is_main_thread() -> bool {
    // SAFETY: neither call takes an argument, touches memory, or can fail.
    unsafe { gettid() == getpid() }
}

/// This process's parent.
#[must_use]
pub fn parent_pid() -> pid_t {
    // SAFETY: takes no argument, touches no memory, cannot fail.
    unsafe { getppid() }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_monotonic_clock_moves_forward() {
        let a = now_ns();
        let b = now_ns();
        assert!(a > 0 && b >= a, "{a} then {b}");
    }

    #[test]
    fn the_realtime_clock_is_epoch_nanoseconds() {
        // Later than 2020-09-13 and earlier than 2065; a `tv_sec`/`tv_nsec` mix-up
        // lands far outside both ends.
        let t = now_realtime_ns();
        assert!(t > 1_600_000_000_000_000_000, "{t}");
        assert!(t < 3_000_000_000_000_000_000, "{t}");
    }

    #[test]
    fn the_test_harness_runs_this_on_a_spawned_thread() {
        // libtest runs each `#[test]` on its own thread, so this is a real
        // reading of `is_main_thread` and not a tautology.
        assert!(!is_main_thread());
        assert!(!std::thread::spawn(is_main_thread).join().unwrap());
    }

    #[test]
    fn the_parent_pid_is_not_this_process() {
        let p = parent_pid();
        assert!(p > 0);
        // SAFETY: see `is_main_thread`.
        assert_ne!(p, unsafe { getpid() });
    }
}
