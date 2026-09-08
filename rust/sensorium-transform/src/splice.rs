//! The splicer: `syn` says where the braces, the operands and the spawn callees
//! are, the original bytes are copied through, and newline-free fragments go in
//! at those offsets. The AST is a ruler, never a printer (spec §3.1).
//!
//! The VOCABULARY is here -- the fragments, [`Kind`] and [`Splice`] -- and the
//! six modules that mint splices import it from this path. The assembly itself
//! is [`crate::assemble`].
//!
//! # Where the offsets come from
//!
//! `proc-macro2` with `span-locations` gives `Span::byte_range()` outside a
//! proc-macro context, and that is what is used -- not `start()`/`end()`, whose
//! `column` counts CHARS and would mis-splice the first file with a `π` in it.
//!
//! Two adjustments are not optional:
//!
//! * `syn::parse_file` strips a BOM and a shebang line BEFORE `proc-macro2` sees
//!   the text, so every byte range is short by that prefix. `File::shebang`
//!   reports exactly what syn removed, so the prefix is measured, not guessed.
//! * Line numbers need no adjustment: syn keeps the shebang's newline in the
//!   text it parses, so line 2 stays line 2.
//!
//! Every computed offset is checked against the byte the grammar says must be
//! there (`{` for a body, `]` for an inner attribute, `(` for a call). A future
//! `proc-macro2` that changed what `byte_range()` is relative to would otherwise
//! mis-splice silently, and every measurement downstream of this crate would
//! inherit it.
//!
//! # Order
//!
//! Splices are sorted by offset, then by KIND, because several land on the same
//! byte and only one order is right. Reading [`Kind`] top to bottom is reading
//! that order: an err wrap's arm closes before an exit wrap's `)` (the err wrap
//! is INSIDE it: `ret(.., match g() { .. }?)`), that closes before the `}` of a
//! block an arm's or a closure's expression body was wrapped in (the exit wrap
//! is inside THAT: `{ guard; ret(.., f(n)) }`), all of them close before
//! anything that starts there, then the entry guard (a statement, which must
//! precede the block's value) -- with an arm-entry LINE ahead of it and a
//! parameters or statement LINE behind it (a LINE must fall inside its
//! function's CALL, so it can never precede the guard) -- then that same
//! block's `{ <statement> ` opening
//! -- ahead of an exit wrap's opening fragment, since a closure's expression
//! body is its own tail operand and both land on that byte -- then an exit
//! wrap's opening fragment, then an err wrap's `match ` (again inside it), then
//! a spawn rewrite, then the crate root's `allow` and its static. Nested wraps
//! of every kind close innermost-first, which is what the reversed `seq` in
//! `assemble::splice_order` is for; opens of one kind at one byte go
//! outermost-first, which is the walk's own order. The assembled output is
//! checked for overlap as it is built, so a mis-ordered splice is an error
//! rather than a corrupted file.

use crate::errflow::How;

/// The entry guard. Newline-free, and the ONLY place its text is written.
pub(crate) fn guard_fragment(site: u32) -> String {
    format!("let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, {site});")
}

/// The opening half of an exit wrap; the closing half is [`RET_CLOSE`].
pub(crate) fn ret_open_fragment(site: u32) -> String {
    format!(
        "::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, {site}, |__r| {{ \
         use ::sensorium_rt::probe::*; \
         ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome()) }}, "
    )
}

pub(crate) const RET_CLOSE: &str = ")";

/// The probe an `Err(..) =>` arm or an `if let Err(..)` body writes at its
/// ENTRY (design R2/R4). `bound` is the ident the pattern destructured the error
/// into, when it destructured one into exactly one name.
///
/// The two entry points differ in what the runtime can be told, not in when it
/// is called: `err_site_value` is handed the error itself and always records,
/// `err_site_unbound` records that an error was seen here and nothing more. The
/// capture is a CLOSURE for the same reason [`err_close_fragment`]'s is -- at
/// tier `off` no `Debug` impl runs.
///
/// `&e` is the right borrow for every binding mode the grammar allows: a
/// by-value `Err(e)` gives `Probe<'_, E>`, and match ergonomics' `e: &E` gives
/// `Probe<'_, &E>` whose `type_name` carries a leading `&` that design R4 has
/// the converter strip. Nothing is moved either way, so the body still owns
/// whatever it was given.
pub(crate) fn arm_probe_fragment(site: u32, how: How, bound: Option<&str>) -> String {
    match bound {
        Some(name) => format!(
            "::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, {site}, \
             ::sensorium_rt::{}, || {{ use ::sensorium_rt::probe::*; \
             (&&Probe(&{name})).err_cap_value() }});",
            how.constant()
        ),
        None => format!(
            "::sensorium_rt::err_site_unbound(&crate::__SENSORIUM_UNIT, {site}, \
             ::sensorium_rt::{});",
            how.constant()
        ),
    }
}

/// The opening half of the block an EXPRESSION body is wrapped in so that a
/// statement can go in front of it: `Err(e) => 0` becomes
/// `Err(e) => { <stmt> 0 }`, and `|n| f(n)?` becomes `{ <stmt> f(n)? }`. The
/// value of the block is the original expression, so nothing about what the arm
/// or the closure evaluates to moves.
pub(crate) fn scope_open_fragment(stmt: &str) -> String {
    format!("{{ {stmt} ")
}

/// Its closing half.
pub(crate) const SCOPE_CLOSE: &str = " }";

/// The opening half of an err wrap (design R3). Six bytes, and the whole reason
/// `tests/oracle.rs` can predict the column shift inside a wrapped operand.
pub(crate) const ERR_OPEN: &str = "match ";

/// The closing half of an err wrap: the single arm that probes the value and
/// hands it straight back. The capture is a CLOSURE, so at tier `off` the
/// runtime never renders anything.
pub(crate) fn err_close_fragment(site: u32, how: How) -> String {
    format!(
        " {{ __t => {{ ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, {site}, \
         ::sensorium_rt::{}, || {{ use ::sensorium_rt::probe::*; \
         (&&&Probe(&__t)).err_cap() }}); __t }} }}",
        how.constant()
    )
}

/// Escape a string for a one-line Rust string literal.
pub(crate) fn escape_string_literal(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        match ch {
            '\\' => out.push_str(r"\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(ch),
        }
    }
    out
}

/// What a splice is, and what has to happen first when two share a byte. The
/// DECLARATION ORDER is the tie-break order (the derived `Ord`), so this list
/// is the rule and not a description of one.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Kind {
    /// An err wrap's arm. Ordered before an exit wrap's `)` because the err
    /// wrap sits INSIDE the exit wrap (`ret(.., match g() { .. }?)`) -- an
    /// ordering that is DEFENSIVE rather than exercised: the two cannot share a
    /// byte, since an exit operand that ends where an err operand ends would
    /// have to be that err operand, and the `?` or `.ok()` between them is at
    /// least one byte wide. Unreachable by construction, ordered so that if the
    /// construction ever changes the bytes still come out nested.
    ErrClose,
    /// An exit wrap's `)`. Closes what is already open before anything new.
    Close,
    /// The `}` closing the block an arm's or a closure's EXPRESSION body was
    /// wrapped in. OUTSIDE an exit wrap's `)`, because the exit wrap goes
    /// around the block's value: a closure body `|n| f(n)` becomes
    /// `{ guard; ret(.., f(n)) }`, so the `)` closes first. Two of these can
    /// share a byte -- an arm whose body IS a `?`-bearing closure -- and the
    /// reversed `seq` in `assemble::splice_order` closes the innermost first.
    ScopeClose,
    /// A focus tier arm-entry LINE written into a BLOCK body. Ahead of an
    /// `Err(..) =>` arm's own probe at the same byte, so that the two forms of
    /// the same construct nest the same way: a bare-EXPRESSION arm body comes
    /// out `{ <LINE> { <arm probe> <expr> } }` (the LINE wrap is pushed first
    /// and is therefore outermost), and without this kind a BLOCK body would
    /// come out arm-probe-first -- the same two statements in the opposite
    /// order, for no reason a reader could name. Measured by
    /// `tests/golden_focus/focus_err_arm`.
    LineEntry,
    /// The entry guard, and an arm probe in a BLOCK body: a statement, so ahead
    /// of the block's value.
    Guard,
    /// A focus tier LINE probe: the parameters LINE, or a statement's own LINE.
    /// A statement, so ahead of the block's value -- and AFTER [`Kind::Guard`],
    /// which is design amendment A6: the parameters LINE shares the entry
    /// guard's byte and a LINE must fall INSIDE its function's CALL, so it can
    /// never precede the guard that opens the frame. An ARM-entry LINE is
    /// [`Kind::LineEntry`] (block body) or a
    /// [`Kind::ScopeOpen`]/[`Kind::ScopeClose`] pair (bare expression,
    /// amendment A1), both of which sit outside an `Err(..) =>` arm's probe
    /// rather than inside it.
    Line,
    /// The `{ <statement> ` opening that same block. Ahead of an exit wrap's
    /// opening fragment, since a closure's expression body is its own tail
    /// operand and both land on that byte.
    ScopeOpen,
    /// An exit wrap's opening fragment, outside a spawn rewrite at the same byte.
    Open,
    /// An err wrap's `match `. After an exit wrap's opening fragment at the same
    /// byte (a `?` tail is `ret(.., match g() { .. }?)`, not the other way
    /// round), and before a spawn rewrite, whose REPLACED bytes start on that
    /// same byte in `let _ = std::thread::spawn(f);` -- `assemble` walks in
    /// sorted order and refuses a splice that starts before its cut, so the
    /// zero-width insert has to come first. Both are exercised by goldens
    /// (`try_tail_and_stmt`, `spawn_thread`), not argued.
    ErrOpen,
    /// A spawn callee replaced in place.
    Replace,
    /// The spawn site string, just past the call's `(`.
    SpawnArg,
    /// The crate root's `allow`, on the last inner attribute's line. Before the
    /// static, which shares its byte on a file whose whole content is doc
    /// comments -- and an inner attribute may not follow an item.
    Allow,
    /// The crate root's unit static, past the file's last token.
    Static,
}

#[derive(Debug, Clone)]
pub(crate) struct Splice {
    pub start: usize,
    /// `== start` for an insert; past the replaced bytes otherwise.
    pub end: usize,
    pub kind: Kind,
    /// Emission order, so nested wraps close innermost-first.
    pub seq: usize,
    pub text: String,
}

/// How many bytes `syn::parse_file` removed before `proc-macro2` saw the text.
pub(crate) fn stripped_prefix_len(source: &str, shebang: Option<&str>) -> usize {
    let bom = usize::from(source.starts_with('\u{feff}')) * '\u{feff}'.len_utf8();
    bom + shebang.map_or(0, str::len)
}
