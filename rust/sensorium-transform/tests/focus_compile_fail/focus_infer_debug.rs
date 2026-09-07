//! A `let` whose head type is an INFERENCE VARIABLE that a later statement
//! resolves to a non-`Debug` type. `Vec::new()` here is `Vec<_>`; `_` becomes
//! `Opaque` at the `push` on the next line, and `Opaque` has no `Debug`.
//!
//! The probe on the `let` line runs the autoref ladder against `&Vec<_>` and
//! COMMITS the variable to the `Debug` rung, so the later resolution is an
//! E0277 and the unit does not build. `rust/HONESTY-BLIND-SPOTS.md` item 3
//! states this; this file is what measures it.
//!
//! `focus_moved_value` is the same `Vec::new()` shape resolving to a type that
//! DOES implement `Debug`, and it compiles -- so what fails here is the
//! resolution, not `Vec::new()`.

pub struct Opaque(pub i32);

pub fn collect_them() -> usize {
    let mut v = Vec::new();
    v.push(Opaque(1));
    v.len()
}
