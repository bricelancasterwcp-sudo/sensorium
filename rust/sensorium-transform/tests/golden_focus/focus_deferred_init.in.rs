//! A `let` with NO initializer writes nothing at its own line: the binding
//! appears at the assignment that first writes it. The probe after `let x;` is
//! therefore `|| []`, and it has to be -- a delta naming `x` there borrows a
//! binding rustc knows is not initialized yet (E0381) and takes the whole unit
//! down with it. `lines.rs`'s `statement_deltas` guard, `local.init.is_some()`,
//! is what makes that true.
//!
//! MEASURED (2026-09-06, the fix wave). Removing that guard makes the probe
//! read `|| [("x", probe_cap!(&x))]` at the declaration and rustc refuses
//! the file:
//! `error[E0381]: used binding `x` is possibly-uninitialized ... borrow occurs
//! due to use in closure`. Two links carry that here rather than one, and
//! neither alone would: `focus.rs` pins these BYTES against the real
//! transform's output (that is the link the mutant broke, red on two tests),
//! and `oracle.rs` hands the same bytes to the real rustc (that is the link
//! saying the pinned bytes are legal Rust). The mutant's own output was
//! compiled by hand to read the E0381 above, because the oracle compiles what
//! is checked in and a mutant changes what the transform emits.

pub fn deferred() {
    let x;
    x = 1;
    println!("{x}");
}
