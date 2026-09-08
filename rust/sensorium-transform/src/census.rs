//! What a walk COUNTS, and what it RECORDS when it splices nothing.
//!
//! Two callers ask this crate about a file without wanting the file rewritten,
//! and both are answered by the SAME visitor the transform runs, with `emit`
//! false so that not one fragment is placed:
//!
//! * [`counts`] is E2's denominator ([`Census`]): how many fn items a file
//!   holds, how many of them each skip reason takes, how many `?` the parser
//!   saw and how many it could not. Counting, and never a row.
//! * [`walk`] is the driver's `--focus` resolver ([`crate::fn_items`]): the fn
//!   ROWS the transform would mint and the skip rows it would declare, with no
//!   splice behind them.
//!
//! [`walk`] is why this module exists (design 2026-09-07 §6, ruling R7). Until
//! `sensorium-transform` 0.4.2 the resolver ran the WHOLE splicing transform on
//! every `.rs` file of a workspace -- every byte offset computed, every fragment
//! placed, every rewritten source assembled and its line count checked -- and
//! threw the source away to read two lists off the side of it. It now runs the
//! walk alone.
//!
//! # The one rule both entry points keep
//!
//! **A census is never a SECOND classifier.** `Ctx::classify` below is the only
//! place a fn item is put in a bucket and `Ctx::fn_row` ([`crate::visit`]) is
//! the only place a `Fn` row is built, so the emitting walk and the census walk
//! cannot come to disagree. If they could, the driver would accept a `--focus`
//! value the transform then silently ignores, and the trace would come back
//! empty with nothing refused. `tests/fn_census.rs` measures the two routes
//! against each other on every golden, on this repository's own `rust/` tree
//! and on the pinned clone.

use syn::visit::Visit;
use syn::Signature;

use crate::focus::Focus;
use crate::splice::stripped_prefix_len;
use crate::visit::{Ctx, Walked};
use crate::Census;

/// What a walk is FOR, read once at [`Ctx::new`].
///
/// The constructor used to take `emit` and `record_sites` as two adjacent
/// unnamed `bool`s. The three call sites wanted `true, true` / `false, false` /
/// `false, true`, and TRANSPOSING the last to `true, false` compiles silently
/// and turns the resolver's census into a full emitting walk that records no
/// rows -- mutant M4's defect, reachable by a typo rather than by a deliberate
/// edit, and `clippy::fn_params_excessive_bools` does not fire on two (review
/// N3). Three named modes make the fourth combination unspellable.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Mode {
    /// The transform: place every fragment, and record every row beside it.
    Emitting,
    /// [`walk`]: record the fn rows and the skip rows, place nothing.
    Census,
    /// [`counts`]: count, and record nothing -- E2's denominator.
    Counting,
}

impl Mode {
    /// Does this walk place fragments? Everything that decides WHERE a fragment
    /// goes -- an err-flow site, a framed closure, a spawn rename, a LINE probe
    /// -- is gated on this and on nothing else.
    pub(crate) fn emits(self) -> bool {
        matches!(self, Mode::Emitting)
    }

    /// Does this walk record fn rows and skip rows? A row is a FACT about the
    /// file, so the emitting walk records them too: this is never read instead
    /// of [`Mode::emits`], only beside it.
    pub(crate) fn records_rows(self) -> bool {
        matches!(self, Mode::Emitting | Mode::Census)
    }
}

impl Ctx<'_> {
    /// Which disjoint bucket this signature falls in, if any, counting it as it
    /// goes.
    ///
    /// The order is what makes the buckets disjoint, so that a fn is classified
    /// exactly once and `fn_items - const_fns - extern_fns` never subtracts one
    /// fn twice. (`const async fn` and `async extern fn` are both rejected by
    /// rustc, so the order is a formality, not a policy.)
    pub(crate) fn classify(&mut self, sig: &Signature) -> Option<&'static str> {
        if sig.constness.is_some() {
            self.const_fns += 1;
            return Some("const");
        }
        if sig.abi.is_some() {
            self.extern_fns += 1;
            return Some("extern");
        }
        if sig.asyncness.is_some() {
            // A guard in an `async fn` body lives inside the future, so it is
            // dropped when the future is dropped -- possibly on a different
            // thread than the one that created it, and never at the `.await`
            // boundaries the caller would read as returns. That contradicts
            // spec §3.2's "the guard's Drop is the SOLE emitter of RETURN".
            self.async_fns += 1;
            return Some("async");
        }
        None
    }

    /// The counts E2 reads, from the same classification that instrumented.
    pub(crate) fn census(&self) -> Census {
        Census {
            fn_items: self.fn_items,
            const_fns: self.const_fns,
            extern_fns: self.extern_fns,
            async_fns: self.async_fns,
            try_syn: self.try_syn,
            try_macro_tokens: self.try_macro_tokens,
            arms_propagate: self.arms[0],
            arms_panic: self.arms[1],
            arms_escaped: self.arms[2],
            arms_handled: self.arms[3],
            closures_framed: self.closures_framed,
            async_partials: self.async_partials,
            parsed: true,
        }
    }
}

/// [`crate::census()`]: the counts alone, from a walk that splices nothing.
///
/// A census classifies and never splices, so it never needs a focus: the counts
/// are the same under every one.
pub(crate) fn counts(source: &str) -> Census {
    let Ok(parsed) = syn::parse_file(source) else {
        // Four zeros with `parsed: false` -- NOT a measured zero.
        return Census::default();
    };
    let prefix = stripped_prefix_len(source, parsed.shebang.as_deref());
    let none = Focus::EMPTY;
    let mut ctx = Ctx::new(source, prefix, "", 0, Mode::Counting, &none);
    ctx.visit_file(&parsed);
    ctx.census()
}

/// The fn ROWS of one file and the skip rows beside them, from a walk that
/// splices nothing (design 2026-09-07 §6).
///
/// What the returned [`Walked`] carries, and what it deliberately does not:
///
/// * `sites` holds this file's [`crate::SiteKind::Fn`] rows and only those. No
///   err-flow, closure or LINE site is minted, because each of those is a
///   PROBE -- a decision about where a fragment goes -- and this walk places no
///   fragment. `Site::site` therefore numbers the fn rows alone and is NOT the
///   index the transform would give them; nothing reads it here.
/// * `skipped` holds every skip row the transform would declare, all four
///   reasons, in the transform's own order.
/// * `splices`, `spawns`, `partial` and `focused` are empty, by the same `emit`
///   gate that has always made a census cost nothing.
///
/// `None` when the file does not parse: it is not instrumented either, so it
/// holds nothing a focus could select -- the same none-versus-zero discipline
/// [`Census::parsed`] keeps, and never a measured empty.
///
/// # The one answer that MOVED (review N2)
///
/// A file whose WALK is clean but whose SPLICING half would fail answered
/// `[]` under 0.4.1 and answers with its full row list here. The splicing half
/// is everything this walk does not run: `assemble::assemble` (two splices
/// overlapping), `check_line_count`, `check_spawn_ordinals`, the
/// [`crate::MAX_SITE_INDEX`] guard, and `wrap_operand`'s three refusals (an
/// exit operand whose span is not a byte range, one that does not re-tokenise,
/// one whose offset falls inside a UTF-8 character) -- the same three for a
/// framed closure. Under 0.4.1 any of them made `crate::transform` return
/// `Err`, and `fn_items` collapsed that to no items at all.
///
/// **The differential in `tests/fn_census.rs` structurally cannot cover this
/// class**, and no widening of its corpora would: every condition above is a
/// construction bug in this crate or a file with more than 16.7 million sites,
/// so no real tree holds one. `tests/fn_census.rs`'s
/// `a_file_whose_splicing_half_fails_still_answers_through_the_census` reaches
/// the class through the one lever a caller can pull -- `first_site` past the
/// wire's 24-bit field -- so the difference is pinned rather than only
/// described.
///
/// It is also the better answer for focus resolution. A `--focus` naming a
/// function that is plainly in the file used to be REFUSED before cargo ran,
/// with `--focus X matches no function in this workspace`, because some other
/// file in the workspace could not be spliced. Now the resolver accepts what
/// is there and the splice failure surfaces where it belongs: as a loud
/// transform error during the build, naming the file and the offset.
pub(crate) fn walk(source: &str, file: &str) -> Option<Walked> {
    let parsed = syn::parse_file(source).ok()?;
    let prefix = stripped_prefix_len(source, parsed.shebang.as_deref());
    // No focus: a LINE probe is a splice, and this walk places none.
    let none = Focus::EMPTY;
    let mut ctx = Ctx::new(source, prefix, file, 0, Mode::Census, &none);
    ctx.visit_file(&parsed);
    // `finish` carries the walk's error discipline: an offset anomaly makes the
    // file answer NOTHING rather than answer partially, which is what the
    // splicing route did with the same `?`.
    ctx.finish().ok()
}
