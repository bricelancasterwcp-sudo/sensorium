//! `sensorium-transform` -- THROWAWAY SPIKE CODE for the rung-1 Rust mechanics
//! spike (`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`).
//! Evidence, not product: never merged to main, never `cargo install`ed, never
//! depended on by the sensorium Python package.
//!
//! It does one thing: put a `sensorium-rt` entry guard at the top of every
//! eligible fn body WITHOUT moving a single line number. Spec §3.1 is the whole
//! reason it exists -- re-printing the AST with `quote` collapses a file to one
//! line and destroys `line!()`, panic locations and rustc's own diagnostics, so
//! endpoint E7 would be dead on arrival. The AST is therefore a MEASURING
//! instrument only: `syn` says where the braces are, and the original bytes are
//! copied through with newline-free fragments spliced in at those offsets. The
//! AST is never printed.
//!
//! Injected as the first statement of every eligible fn body:
//!
//! ```ignore
//! let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);
//! ```
//!
//! and, when the file is the crate root, once per file:
//!
//! ```ignore
//! #[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit =
//!     ::sensorium_rt::Unit::new("<-C metadata hash>");
//! ```
//!
//! (emitted on one line -- see [`transform`] for where it lands and why).

mod manifest;
mod splice;

pub use manifest::{Manifest, ManifestSite};

/// The result of rewriting one file.
#[derive(Debug, Clone)]
pub struct Transformed {
    /// The rewritten source. Same line count as the input (see [`transform`]).
    pub source: String,
    /// One entry per injected guard, in source order, `site` contiguous from
    /// `first_site`.
    pub sites: Vec<Site>,
    /// Fn items this tier deliberately does not instrument, with the reason.
    pub skipped: Vec<Skipped>,
}

/// One instrumented fn item. Mirrors a Python `code_object` (spec §5.4).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Site {
    /// The 24-bit site INDEX. The runtime packs the unit id into bits 31..24;
    /// the transformer never does.
    pub site: u32,
    /// The workspace-relative path as the caller named it. Never a mirror path.
    pub file: String,
    /// File-local path in Python's shape: `Type::method`, `mod_a::mod_b::f`.
    pub qualname: String,
    /// 1-based line of the `fn` keyword -- not of the opening brace.
    pub firstlineno: u32,
}

/// A fn item that was parsed, understood, and deliberately left alone.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Skipped {
    pub file: String,
    pub qualname: String,
    /// 1-based line of the `fn` keyword (or of the `fn` token inside a
    /// `macro_rules!` body, for `reason = "macro"`).
    pub line: u32,
    /// `"const"`, `"extern"` or `"macro"`.
    pub reason: &'static str,
}

/// E2's denominator, counted by the same parser and the same eligibility rules
/// that do the instrumenting.
///
/// `const_fns` and `extern_fns` are DISJOINT subsets of `fn_items` (a
/// `const extern "C" fn` counts as const), so eligible is exactly
/// `fn_items - const_fns - extern_fns` with no double subtraction.
///
/// `parsed` is the none-versus-zero discipline in a struct: a file `syn` could
/// not parse yields `Census { parsed: false, .. }` with three zeros, and a
/// caller that sums it as measured-zero is lying. Check `parsed` first.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, serde::Serialize)]
pub struct Census {
    pub fn_items: usize,
    pub const_fns: usize,
    pub extern_fns: usize,
    pub parsed: bool,
}

impl Census {
    /// `fn_items - const_fns - extern_fns`; the denominator of E2.
    #[must_use]
    pub fn eligible(&self) -> usize {
        self.fn_items - self.const_fns - self.extern_fns
    }
}

/// The largest site index the wire format's 24-bit field can carry (spec §4).
pub const MAX_SITE_INDEX: u32 = 0x00FF_FFFF;

/// Rewrite one file, injecting an entry guard into every eligible fn body.
///
/// `file` is recorded verbatim in every [`Site`] and [`Skipped`] (the caller
/// passes the ORIGINAL workspace-relative path, never a mirror path).
/// `unit_metadata` is the unit's `-C metadata` hash, embedded in the crate
/// root's static. Sites are numbered from `first_site` in source order.
///
/// `is_crate_root` is the wrapper's knowledge, not a guess: only the one
/// positional `.rs` in rustc's argv is a crate root, and only it gets the
/// `__SENSORIUM_UNIT` static.
///
/// # Line numbers
///
/// `result.source.lines().count() == source.lines().count()` for every
/// non-empty input. Every injected fragment is newline-free and the static is
/// spliced immediately after the file's LAST TOKEN -- which is on the last line
/// of code, never inside a trailing comment, and never after the final newline
/// (appending after it would add a line). A file with no tokens at all takes
/// the static at offset 0, which is safe precisely because a file with no
/// tokens has no inner attributes to displace. The one documented exception is
/// an EMPTY crate root, where a zero-line file necessarily becomes a one-line
/// one; no line number can move in a file that has none.
///
/// # Errors
///
/// Returns the `syn` parse error if the source is not valid Rust, and a
/// synthesised error if the site indices would overflow 24 bits or if a
/// computed byte offset does not land where the grammar says it must (the
/// latter is a guard against a future `proc-macro2` changing what
/// `Span::byte_range()` is relative to -- a silent mis-splice would corrupt
/// every downstream measurement).
pub fn transform(
    source: &str,
    file: &str,
    unit_metadata: &str,
    first_site: u32,
    is_crate_root: bool,
) -> Result<Transformed, syn::Error> {
    splice::run(source, file, unit_metadata, first_site, is_crate_root)
}

/// Count fn items the way [`transform`] classifies them, without rewriting.
#[must_use]
pub fn census(source: &str) -> Census {
    splice::census(source)
}
