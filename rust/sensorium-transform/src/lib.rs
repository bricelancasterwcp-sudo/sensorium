//! `sensorium-transform` -- the sensorium Rust recorder's source rewriter.
//!
//! It puts five things into a workspace's own source, WITHOUT moving a single
//! line number: an entry guard at the top of every eligible fn body, a capture
//! around every exit operand of a value-returning fn, a probe around every `?`
//! operand and every written sink's value, a named `spawn_child` in place of
//! `std::thread::spawn`, and one `allow` attribute on the crate root.
//!
//! Spec §3.1 is the whole reason it works this way -- re-printing the AST with
//! `quote` collapses a file to one line and destroys `line!()`, panic locations
//! and rustc's own diagnostics. The AST is therefore a MEASURING instrument
//! only: `syn` says where the braces and the operands are, and the original
//! bytes are copied through with newline-free fragments spliced in at those
//! offsets. The AST is never printed.
//!
//! Injected as the first statement of every eligible fn body:
//!
//! ```ignore
//! let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);
//! ```
//!
//! around the tail expression and every `return <e>` at closure depth 0 of a
//! [`RetKind::Value`] fn -- two splices, an opening fragment before the operand
//! and a `)` after it:
//!
//! ```ignore
//! ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, <site>, |__r| {
//!     use ::sensorium_rt::probe::*;
//!     ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
//! }, <e>)
//! ```
//!
//! around the operand of every `?`, the receiver of every written sink and the
//! value of every `let _ = <value expression>` -- an opening `match ` before the
//! operand and the arm after it, so that the program's own `?` and `.ok()` stay
//! OUTSIDE the wrap and nothing about its control flow moves (`errflow`, design
//! R2/R3):
//!
//! ```ignore
//! match <operand> { __t => {
//!     ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, <site>, <how>,
//!         || { use ::sensorium_rt::probe::*; (&&&Probe(&__t)).err_cap() });
//!     __t
//! } }
//! ```
//!
//! over the callee of a `std::thread::spawn` call, so the child thread has a
//! name (`rust/HONESTY.md` §3):
//!
//! ```ignore
//! ::sensorium_rt::spawn_child("<file>:<line>", <f>)
//! ```
//!
//! and, when the file is the crate root, once per file -- the static past the
//! last token, the `allow` on the same line as the last inner attribute (every
//! wrap above is a `match` with one binding, which is what clippy's
//! `match_single_binding` is about):
//!
//! ```ignore
//! #![allow(clippy::match_single_binding)]
//! #[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit =
//!     ::sensorium_rt::Unit::new("<-C metadata hash>");
//! ```
//!
//! (each emitted on one line -- see [`transform`] for where they land and why).
//!
//! **What this crate promises**, and where each promise is falsified:
//! `rust/HONESTY.md` §1 (what an outcome means), §3 (spawn shapes that are
//! declared rather than rewritten), §8 items 5 and 6 (the declared skips) and §9
//! (line numbers, temporary lifetimes, drop order, and no new diagnostics).
//! `tests/golden.rs` pins the bytes, `tests/oracle.rs` compiles and RUNS them
//! through the real rustc, and `tests/census.rs` measures the identity on a real
//! workspace.

mod errflow;
mod exits;
mod manifest;
mod names;
mod spawn;
mod splice;
mod visit;

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
    /// Err-flow sites the transformer could not reach, with the reason
    /// (design R6). Empty is a measured empty: the walk ran and found none.
    pub partial: Vec<Partial>,
    /// Every spawn shape the file contains, in source order: the ones that were
    /// rewritten and the ones that were left alone with a reason.
    pub spawns: Vec<SpawnSite>,
    /// True when the crate-root static had to be placed past the end of the
    /// text, so the file gained a FINAL line where there was none. No existing
    /// line moves. See [`transform`]'s "Line numbers" for the only shapes that
    /// do this; callers that assert the line-count invariant must add this.
    pub appended_line: bool,
}

/// What a fn item returns, which decides whether its exits are wrapped.
///
/// Serialised into the manifest as `"unit"`, `"value"` or `"never"`, and read
/// back by the converter: the wire carries no per-site knowledge, so `ret` is
/// what separates "closed `ok` with the value `()`" from "closed `none` because
/// nothing was probed" (`rust/HONESTY.md` §1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum RetKind {
    /// No return type, or `-> ()`. There is no exit operand to probe.
    Unit,
    /// Any other return type. The exits were wrapped.
    Value,
    /// `-> !`. The function has no value to return.
    Never,
}

/// What one site IS. Every kind takes its number from the same per-unit
/// counter (design R1b), so a manifest reader needs this to know which records
/// may name it: a CALL/RETURN belongs to a `fn` site, a RAISE/HANDLED to a
/// `try` or `sink` one.
///
/// A manifest written before this field existed (transform 0.2.0) reads every
/// site as [`SiteKind::Fn`], which is what it had.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum SiteKind {
    /// An instrumented fn item: an entry guard, and exit wraps when it returns
    /// a value.
    Fn,
    /// The operand of a `?` (design R2).
    Try,
    /// A written sink: `.ok()`, `.unwrap_or*()`, `let _ = <value expr>`.
    Sink,
}

/// One instrumented site. A [`SiteKind::Fn`] one mirrors a Python
/// `code_object` (spec §5.4); the others are the err-flow sites of design R2.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Site {
    /// The 24-bit site INDEX. The runtime packs the unit id into bits 31..24;
    /// the transformer never does.
    pub site: u32,
    /// The workspace-relative path as the caller named it. Never a mirror path.
    pub file: String,
    /// File-local path in Python's shape: `Type::method`, `mod_a::mod_b::f`.
    /// For an err-flow site, the enclosing named item's.
    pub qualname: String,
    /// The site's own 1-based line: the `fn` keyword for a [`SiteKind::Fn`]
    /// (not the opening brace), the `?` for a try site, the method name for a
    /// sink, the `let` for a `let _`. The manifest spells it `firstlineno` on a
    /// fn row and `line` on the others, because those are two different facts.
    pub firstlineno: u32,
    /// What the signature says the fn returns. `None` on an err-flow site:
    /// there is no signature there, and `unit` would be an answer rather than
    /// a silence.
    pub ret: Option<RetKind>,
    /// Which kind of site this is.
    pub kind: SiteKind,
    /// The `how` this site writes, by name (`"try"`, `"sink_ok"`,
    /// `"sink_unwrap_or"`, `"sink_let_underscore"`). `None` on a fn site.
    pub how: Option<&'static str>,
}

/// An err-flow site the transformer knows is there and cannot reach, declared
/// rather than dropped (design R6). Registered-unit-scoped, like [`Skipped`].
///
/// `reason` is one of:
///
/// * `"macro-arg"` -- a `?` inside a macro invocation's tokens. `syn` gives an
///   invocation an opaque token stream, so no `syn::ExprTry` node exists for
///   it; these are the `?` [`Census::try_macro_tokens`] counts.
/// * `"sink-place"` -- a written sink whose receiver is a place expression
///   (design R2; see `errflow::is_place_expression` for the re-measurement).
/// * `"struct-literal"` -- a site whose operand's leading token opens a struct
///   literal, which a `match` scrutinee may not contain outside parentheses.
///
/// A `let _ = <place expression>;` is NOT here: `_` does not bind, so that
/// statement moves nothing and drops nothing, and no error is absorbed at it.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Partial {
    pub file: String,
    /// 1-based line of the `?`, or of the sink's method name.
    pub line: u32,
    /// The enclosing named item's file-local path, or the enclosing container's
    /// when there is no named item between the site and the file.
    pub qualname: String,
    pub reason: &'static str,
}

/// A fn item that was parsed, understood, and deliberately left alone.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct Skipped {
    pub file: String,
    pub qualname: String,
    /// 1-based line of the `fn` keyword (or of the `fn` token inside a
    /// `macro_rules!` body, for `reason = "macro"`).
    pub line: u32,
    /// `"const"`, `"extern"`, `"async"` or `"macro"`.
    pub reason: &'static str,
}

/// One thread-spawning shape the file contains.
///
/// A shape that is not rewritten is still listed, with the reason: a child
/// thread that gets no name is a task `diff` can only compare as a member of an
/// unnamed multiset, and `rust/HONESTY.md` §3 requires that limit to travel with
/// the trace rather than be discovered.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
pub struct SpawnSite {
    /// The workspace-relative path as the caller named it.
    pub file: String,
    /// 1-based line of the callee: the path's first token for a path call, the
    /// method name for a method call.
    pub line: u32,
    /// True when the callee was replaced with `::sensorium_rt::spawn_child`.
    pub wrapped: bool,
    /// Why not, for the shapes that were left alone: `"builder"` for a
    /// `Builder::..spawn(f)` chain, `"scoped"` for `thread::scope(..)`,
    /// `"method"` for any other one-argument `.spawn(f)`, and `"arity"` for a
    /// path that ends in `thread::spawn` but takes a number of arguments
    /// `std::thread::spawn` does not (which valid code cannot contain, and which
    /// is listed rather than dropped). `None` when `wrapped`.
    pub reason: Option<&'static str>,
    /// The enclosing NAMED ITEM's file-local qualname (plan decision N5, as
    /// amended in fix round 1). A closure, block or `match` arm pushes no scope
    /// of its own, so a spawn inside one belongs to the item around it.
    ///
    /// For a spawn in a fn body this is exactly that fn's [`Site::qualname`]
    /// (`Type::method`, `outer::inner`, `tests::t`), which is what joins a task
    /// to a recorded frame. For a spawn in a `const`/`static`/associated-const
    /// INITIALISER it is that item's own file-local path (`F`, `m::H`, `T::F`)
    /// -- a shape [`Site`] never carries, because a const is not a fn item and
    /// nothing about it is instrumented; only the child it spawns is named.
    pub qualname: String,
    /// The 1-based rank of this site among the WRAPPED spawn sites of this
    /// `(file, qualname)`, in byte-offset source order -- the `<k>` of the
    /// `"<qualname>#<k>"` the child thread is named. `None` for a declared
    /// shape: it is not rewritten, so it takes no name and consumes no ordinal
    /// from the wrapped sites around it (plan decision N1).
    pub ordinal: Option<u32>,
}

/// E2's denominator, counted by the same parser and the same eligibility rules
/// that do the instrumenting.
///
/// `const_fns`, `extern_fns` and `async_fns` are DISJOINT subsets of `fn_items`,
/// so nothing is ever subtracted twice.
///
/// [`Census::eligible`] subtracts only const and extern, because that is what
/// endpoint E2 pre-registered as "eligible" before `async` was ruled a skip. The
/// pre-registration is not edited after the fact: `async_fns` is reported
/// alongside, and the honest identity a caller checks is
/// `instrumented + async_fns == eligible`.
///
/// `parsed` is the none-versus-zero discipline in a struct: a file `syn` could
/// not parse yields `Census { parsed: false, .. }` with every count at zero, and
/// a caller that sums it as measured-zero is lying. Check `parsed` first.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, serde::Serialize)]
pub struct Census {
    pub fn_items: usize,
    pub const_fns: usize,
    pub extern_fns: usize,
    /// Skipped at this tier (plan decision D6), but INSIDE `eligible()`.
    pub async_fns: usize,
    /// Every `syn::ExprTry` the walk meets, in any position: E2″'s denominator.
    ///
    /// These are the `?` the transformer CAN see, because `syn` parsed them into
    /// an AST node. A `?` the walk meets inside a closure, a nested item or a
    /// `const` initialiser counts the same as one in a fn's own body: the
    /// question E2″ asks is how many of the `?` that exist as nodes were reached,
    /// not where they sat.
    pub try_syn: usize,
    /// `?` PUNCT TOKENS inside the token stream of a macro INVOCATION: the `?`
    /// the transformer cannot see, and so the size of the `partial` blind spot.
    ///
    /// A macro invocation's `tokens` are opaque to `syn` -- `println!("{}", f()?)`
    /// holds no [`syn::ExprTry`] node at all -- so these are counted as raw
    /// tokens, recursively through every delimited group. The counted set is
    /// exactly the `syn::Macro` of an `Expr::Macro`, a `Stmt::Macro` and an
    /// `Item::Macro`, minus two exclusions and no others:
    ///
    /// * a `?` immediately followed by the ident `Sized` (a `?Sized` bound in a
    ///   macro argument is a token of a trait bound, not a fallible operation);
    /// * the whole token stream of a `macro_rules!` DEFINITION, where `$( .. )?`
    ///   makes `?` a repetition operator rather than an operation. A definition
    ///   is not an invocation, and the walk never counts one.
    ///
    /// Nothing else is excluded: a `?` inside a nested group, inside a string's
    /// neighbouring tokens, or in an argument that never expands is still a `?`
    /// the transformer did not instrument, and hiding it would flatter the
    /// measurement.
    pub try_macro_tokens: usize,
    pub parsed: bool,
}

impl Census {
    /// `fn_items - const_fns - extern_fns`; the denominator of E2, exactly as
    /// pre-registered. `async_fns` is deliberately NOT subtracted.
    #[must_use]
    pub fn eligible(&self) -> usize {
        self.fn_items - self.const_fns - self.extern_fns
    }
}

/// The largest site index the wire format's 24-bit field can carry (spec §4).
pub const MAX_SITE_INDEX: u32 = 0x00FF_FFFF;

/// Rewrite one file.
///
/// `file` is recorded verbatim in every [`Site`], [`Skipped`] and [`SpawnSite`],
/// and is baked into the spawn site strings (the caller passes the ORIGINAL
/// workspace-relative path, never a mirror path). `unit_metadata` is the unit's
/// `-C metadata` hash, embedded in the crate root's static. Sites are numbered
/// from `first_site` in source order.
///
/// `is_crate_root` is the wrapper's knowledge, not a guess: only the one
/// positional `.rs` in rustc's argv is a crate root, and only it gets the
/// `__SENSORIUM_UNIT` static.
///
/// # Eligibility
///
/// `ItemFn`, `ImplItemFn` and `TraitItemFn` WITH A BODY, at any nesting.
/// Declared in `skipped` and not instrumented: `const fn` (`"const"`), fns with
/// an ABI (`"extern"`), `async fn` (`"async"` -- a guard inside a future is
/// dropped with the future, possibly on another thread, which contradicts spec
/// §3.2's sole-emitter rule), and `fn` tokens inside a `macro_rules!` body
/// (`"macro"`, invisible to `syn` as items). A bodiless trait fn is none of
/// these: there is nothing to instrument and nothing to excuse.
///
/// Closures get no guard at this rung (spec §3.3's closure frames are rung 3),
/// and are not counted as fn items.
///
/// # Exits
///
/// Only a [`RetKind::Value`] fn has exits to wrap: its tail expression, and
/// every `return <e>` at closure depth 0 of its body. See [`exits`] for the
/// operands that are left alone because they diverge, and for the two shapes
/// measured to produce a rustc diagnostic when they are wrapped.
///
/// # Line numbers
///
/// `result.source.lines().count() == source.lines().count() +
/// usize::from(result.appended_line)`, and `appended_line` is false for every
/// file that contains an item. Every injected fragment is newline-free; the
/// guard goes after the body's `{` (or past its last inner attribute) and the
/// static after the file's last token.
///
/// Two placements are corrections, not conveniences, and both exist because a
/// doc comment reaches this code as a TOKEN whose span covers the comment text:
///
/// * The static moves past a trailing `//!`/`///` line's newline, or it is
///   commented out -- silently, since the file still parses.
/// * The guard moves past an inner `//!` line's newline for the same reason.
///
/// Three shapes cannot hold the line count and are documented rather than
/// hidden: an EMPTY crate root (a zero-line file necessarily becomes a one-line
/// one), and a crate root whose entire token content is line doc comments with
/// nothing after them. Each sets `appended_line`; each has no items, hence no
/// `mod` declarations, hence no other file in its unit, hence no guard anywhere
/// that could reference the static. No EXISTING line moves in any of them.
///
/// # Errors
///
/// Returns the `syn` parse error if the source is not valid Rust, and a
/// synthesised error if the site indices would overflow 24 bits or if a computed
/// byte offset does not land where the grammar says it must (the latter is a
/// guard against a future `proc-macro2` changing what `Span::byte_range()` is
/// relative to -- a silent mis-splice would corrupt every downstream
/// measurement).
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
