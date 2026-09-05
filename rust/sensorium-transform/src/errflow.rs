//! Which expressions are err-flow sites, and what each one writes.
//!
//! Rung 3 puts a probe around three things the grammar can point at (design R2):
//! the operand of every `?`, the receiver of the four written sinks, and the
//! value of a `let _ = <value expression>`. All three take the SAME wrap -- a
//! `match` whose single arm hands the value straight back:
//!
//! ```ignore
//! match <operand> { __t => {
//!     ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, <site>, <how>,
//!         || { use ::sensorium_rt::probe::*; (&&&Probe(&__t)).err_cap() });
//!     __t
//! } }
//! ```
//!
//! -- and differ only in the `how` byte and in where the wrap's two halves go
//! (the real `?` and the real `.ok()` stay OUTSIDE it, so nothing about the
//! program's own control flow moves). The capture is a CLOSURE: at tier `off`
//! the runtime never calls it, so a probed site costs one atomic load
//! (`sensorium-rt`'s `err_site`).
//!
//! # What this module decides, and what each decision was measured against
//!
//! Every claim below was measured on rustc 1.96 at `-D warnings` on 2026-09-04;
//! `tests/oracle.rs` is where the measurements live as tests.
//!
//! * **Place-expression sink receivers are not wrapped** and are declared
//!   `partial` with reason [`SINK_PLACE`] (design R2, brief invariant 2). See
//!   [`is_place_expression`] for what the re-measurement found.
//! * **A parenthesised operand is descended into** ([`strip_parens`]):
//!   `match (g()) { .. }` is `unused_parens`, which is a build error under a
//!   workspace's own `#![deny(warnings)]`; `(match g() { .. })?` is clean.
//! * **An operand whose leading token opens a struct literal is not wrapped**
//!   ([`leads_with_struct_literal`]) and is declared `partial` with reason
//!   [`STRUCT_LITERAL`]: `match C { v: 1 }.go() { .. }` is
//!   "struct literals are not allowed here", which does not even parse.
//! * **`.is_err()`/`.is_ok()` are never sinks** (design R2): they take `&self`,
//!   so the original autorefs where the wrap moves --
//!   `match t.last { __t => .. }.is_err()` on a `&T` is E0507 where
//!   `t.last.is_err()` is fine (re-measured 2026-09-04, and the one place the
//!   E0507 asymmetry does reproduce).

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::spanned::Spanned;
use syn::{Expr, ExprMethodCall, ExprTry, UnOp};

use crate::names::line_of;
use crate::splice::{err_close_fragment, Kind, ERR_OPEN};
use crate::visit::Ctx;
use crate::{Partial, Site, SiteKind, MAX_SITE_INDEX};

/// A `?` inside the token stream of a macro INVOCATION: no `syn::ExprTry` node
/// exists for it, so the transformer cannot reach it (design R6).
pub(crate) const MACRO_ARG: &str = "macro-arg";

/// A written sink whose receiver is a place expression (design R2).
pub(crate) const SINK_PLACE: &str = "sink-place";

/// A site whose operand's leading token opens a struct literal, which a `match`
/// scrutinee may not (see the module docs). Not in design R6's list of reasons:
/// it is added here because the alternative is emitting a file that does not
/// parse, and a `?` that was not reached is a `?` to declare whatever the cause.
pub(crate) const STRUCT_LITERAL: &str = "struct-literal";

/// The `how` byte a site writes, as the transformer knows it: a name for the
/// manifest and the constant's own spelling for the fragment.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum How {
    /// `?` on the operand. RAISE.
    Try,
    /// `.ok()`. HANDLED.
    SinkOk,
    /// `.unwrap_or(..)`, `.unwrap_or_else(..)`, `.unwrap_or_default()`. HANDLED.
    SinkUnwrapOr,
    /// `let _ = <value expression>;`. HANDLED.
    SinkLetUnderscore,
}

impl How {
    /// The name the manifest row carries, and the name the converter reads.
    pub(crate) fn name(self) -> &'static str {
        match self {
            How::Try => "try",
            How::SinkOk => "sink_ok",
            How::SinkUnwrapOr => "sink_unwrap_or",
            How::SinkLetUnderscore => "sink_let_underscore",
        }
    }

    /// The `sensorium_rt` constant the injected fragment names. The fragment
    /// spells the CONSTANT rather than the number so that a runtime that
    /// renumbered a `how` could not silently disagree with instrumented source.
    pub(crate) fn constant(self) -> &'static str {
        match self {
            How::Try => "HOW_TRY",
            How::SinkOk => "HOW_SINK_OK",
            How::SinkUnwrapOr => "HOW_SINK_UNWRAP_OR",
            How::SinkLetUnderscore => "HOW_SINK_LET_UNDERSCORE",
        }
    }

    /// Which manifest `kind` a site with this `how` is.
    pub(crate) fn site_kind(self) -> SiteKind {
        match self {
            How::Try => SiteKind::Try,
            How::SinkOk | How::SinkUnwrapOr | How::SinkLetUnderscore => SiteKind::Sink,
        }
    }
}

/// The four written sinks, by method name AND arity.
///
/// The arity is checked because a workspace's own `ok(self, x)` is not
/// `Result::ok`, and a turbofish is refused for the same reason: neither
/// `Result::ok` nor `Option::unwrap_or` takes a type argument, so
/// `.ok::<T>()` is somebody else's method. Wrapping one costs nothing at
/// runtime (the ladder's fallback writes nothing), but it would put a `sink`
/// row in the manifest where the program has no sink.
pub(crate) fn sink_how(node: &ExprMethodCall) -> Option<How> {
    if node.turbofish.is_some() {
        return None;
    }
    match (node.method.to_string().as_str(), node.args.len()) {
        ("ok", 0) => Some(How::SinkOk),
        ("unwrap_or", 1) | ("unwrap_or_else", 1) | ("unwrap_or_default", 0) => {
            Some(How::SinkUnwrapOr)
        }
        _ => None,
    }
}

/// Strip the wrappers that carry no meaning of their own, so the wrap goes
/// INSIDE a parenthesised operand.
///
/// `match (g()) { .. }` trips `unused_parens` -- a build error under a
/// workspace's own `#![deny(warnings)]` -- while `(match g() { .. })?` is
/// clean, and the source's own parentheses are left exactly where they were.
pub(crate) fn strip_parens(e: &Expr) -> &Expr {
    match e {
        Expr::Paren(p) => strip_parens(&p.expr),
        Expr::Group(g) => strip_parens(&g.expr),
        other => other,
    }
}

/// Is this expression a PLACE expression -- a path, a field, an index, a deref?
///
/// Design R2 does not wrap a sink whose receiver is one, and the brief's
/// invariant 2 gives the reason as E0507. **Re-measured 2026-09-04 (rustc
/// 1.96), and the E0507 does not reproduce for these four sinks**: they all
/// take `self` by value, so a receiver the wrap cannot move is one the sink
/// could not move either (`t.last.ok()` on a `&T` is E0507 with or without the
/// wrap), and the shapes that do compile -- a `Copy` field behind a `&`, an
/// owned local, a slice index of a `Copy` element, `*p` -- compile wrapped too.
/// The asymmetry is real only for the `&self` PREDICATES `.is_err()`/`.is_ok()`,
/// which design R2 already refuses to probe for exactly this reason.
///
/// The rule is kept as ruled -- it is the conservative direction, and the sites
/// it declines are declared rather than dropped ([`SINK_PLACE`]) -- but the
/// justification in the design is an erratum, and lifting the rule would raise
/// sink coverage. `tests/oracle.rs::a_wrapped_place_receiver_is_not_the_e0507`
/// is where the re-measurement lives.
pub(crate) fn is_place_expression(e: &Expr) -> bool {
    match strip_parens(e) {
        Expr::Path(_) | Expr::Field(_) | Expr::Index(_) => true,
        Expr::Unary(u) => matches!(u.op, UnOp::Deref(_)),
        _ => false,
    }
}

/// Does this expression's LEADING token open a struct literal?
///
/// A `match` scrutinee may not contain one outside parentheses -- rustc reads
/// the `{` as the match body and reports "struct literals are not allowed
/// here", so the wrapped file does not parse at all. The recursion follows the
/// same edges rustc's own `contains_exterior_struct_lit` does: everything that
/// can have an expression to its LEFT, stopping at anything parenthesised or
/// bracketed, where the literal is already protected.
pub(crate) fn leads_with_struct_literal(e: &Expr) -> bool {
    match e {
        Expr::Struct(_) => true,
        Expr::MethodCall(m) => leads_with_struct_literal(&m.receiver),
        Expr::Field(f) => leads_with_struct_literal(&f.base),
        Expr::Index(i) => leads_with_struct_literal(&i.expr),
        Expr::Try(t) => leads_with_struct_literal(&t.expr),
        Expr::Await(a) => leads_with_struct_literal(&a.base),
        Expr::Binary(b) => leads_with_struct_literal(&b.left),
        Expr::Cast(c) => leads_with_struct_literal(&c.expr),
        Expr::Assign(a) => leads_with_struct_literal(&a.left),
        Expr::Unary(u) => leads_with_struct_literal(&u.expr),
        Expr::Reference(r) => leads_with_struct_literal(&r.expr),
        Expr::Range(r) => r.start.as_deref().is_some_and(leads_with_struct_literal),
        // A parenthesised or bracketed literal is protected, and everything
        // else either cannot have an expression to its left or is not legal
        // Rust with one.
        _ => false,
    }
}

/// The spans of the `?` PUNCT tokens inside a macro invocation's token stream,
/// recursively through every delimited group.
///
/// The ONE exclusion is `?Sized`: a `?` immediately followed by the ident
/// `Sized` is part of a trait bound (`impl_for!(T: ?Sized)`), never a fallible
/// operation. Nothing else is excluded here -- in particular this function is
/// never called on a `macro_rules!` DEFINITION's tokens, which is where
/// `$( .. )?` would otherwise be miscounted
/// ([`crate::Census::try_macro_tokens`] states both).
pub(crate) fn question_tokens(tokens: &TokenStream, out: &mut Vec<Span>) {
    let mut pending: Option<Span> = None;
    for tt in tokens.clone() {
        if let Some(span) = pending.take() {
            let sized = matches!(&tt, TokenTree::Ident(id) if id == "Sized");
            if !sized {
                out.push(span);
            }
        }
        match tt {
            TokenTree::Punct(ref p) if p.as_char() == '?' => pending = Some(p.span()),
            TokenTree::Group(ref g) => question_tokens(&g.stream(), out),
            _ => {}
        }
    }
    // A `?` with nothing after it cannot be a `?Sized`.
    if let Some(span) = pending {
        out.push(span);
    }
}

// ---------------------------------------------------------------------------
// Placing the sites
// ---------------------------------------------------------------------------

/// The err-flow half of the walk. It lives here rather than in
/// [`crate::visit`] because that file already carries the rung-1 and rung-2
/// halves and is at the 800-line ceiling; the `Visit` overrides that call these
/// are still there, where the rest of the walk is.
impl Ctx<'_> {
    /// The name an err-flow row is filed under: the enclosing NAMED ITEM's
    /// file-local path, or the enclosing container's when there is no named
    /// item between the site and the file.
    ///
    /// Unlike a spawn -- which is REFUSED with no named item, because the child
    /// thread would take a name no item has -- an err-flow qualname is
    /// descriptive only, so the container's path is a better answer than
    /// failing the file over it. At file scope with no container at all the
    /// answer is the empty string, which says exactly that.
    fn err_qualname(&self) -> String {
        self.enclosing_qualname()
            .unwrap_or_else(|| self.scope_path())
    }

    /// Declare an err-flow site the transformer knows about and cannot reach
    /// (design R6). Honesty over coverage: `info` prints these, and E2''s
    /// numerator is measured against them.
    pub(crate) fn declare_partial(&mut self, line: u32, reason: &'static str) {
        let qualname = self.err_qualname();
        self.partial.push(Partial {
            file: self.file.to_owned(),
            line,
            qualname,
            reason,
        });
    }

    /// Mint a site index for an err-flow site and record its manifest row. Err
    /// sites take their numbers from the SAME per-unit counter as fn items
    /// (design R1b), which is why `kind` has to be on the row.
    fn mint_err_site(&mut self, how: How, line: u32, span: Span) -> Option<u32> {
        if self.next_site > MAX_SITE_INDEX {
            self.fail(
                span,
                "site index past 24 bits: the runtime's site word cannot carry it",
            );
            return None;
        }
        let site = self.next_site;
        self.next_site += 1;
        let qualname = self.err_qualname();
        self.sites.push(Site {
            site,
            file: self.file.to_owned(),
            qualname,
            firstlineno: line,
            ret: None,
            kind: how.site_kind(),
            how: Some(how.name()),
        });
        Some(site)
    }

    /// The two splices of one err wrap: `match ` before the operand and the arm
    /// after it. The program's own `?`, `.ok()` or `;` is left OUTSIDE both.
    fn err_wrap(&mut self, target: &Expr, how: How, line: u32) {
        let span = target.span();
        if leads_with_struct_literal(target) {
            // `match C { v: 1 }.go() { .. }` is "struct literals are not
            // allowed here" -- the wrapped file would not parse at all.
            self.declare_partial(line, STRUCT_LITERAL);
            return;
        }
        let range = span.byte_range();
        let start = self.prefix + range.start;
        let end = self.prefix + range.end;
        if !self.source.is_char_boundary(start) || !self.source.is_char_boundary(end) {
            self.fail(
                span,
                "err-flow operand offset falls inside a UTF-8 character",
            );
            return;
        }
        let Some(site) = self.mint_err_site(how, line, span) else {
            return;
        };
        self.push(start, start, Kind::ErrOpen, ERR_OPEN.to_owned());
        self.push(end, end, Kind::ErrClose, err_close_fragment(site, how));
    }

    /// A `?`: the wrap goes around its OPERAND, and the `?` itself stays
    /// outside, so what the operator does is untouched. Its line is the `?`'s
    /// own, which is what the reader prints as the site's `loc`.
    pub(crate) fn try_site(&mut self, node: &ExprTry) {
        let line = line_of(node.question_token.spans[0]);
        let target = strip_parens(&node.expr);
        self.err_wrap(target, How::Try, line);
    }

    /// One of the four written sinks: the wrap goes around the RECEIVER and the
    /// method call stays outside. A place-expression receiver is declared
    /// rather than wrapped (see [`is_place_expression`]).
    pub(crate) fn sink_site(&mut self, node: &ExprMethodCall, how: How) {
        let line = line_of(node.method.span());
        let target = strip_parens(&node.receiver);
        if is_place_expression(target) {
            self.declare_partial(line, SINK_PLACE);
            return;
        }
        self.err_wrap(target, how, line);
    }

    /// The `?` PUNCT tokens of one macro INVOCATION: counted for the census,
    /// and declared `partial` on the emitting side. There is no `syn::ExprTry`
    /// node for any of them, so this is the whole of what the transformer can
    /// say about them (design R6).
    pub(crate) fn macro_question_tokens(&mut self, tokens: &TokenStream) {
        let mut spans = Vec::new();
        question_tokens(tokens, &mut spans);
        self.try_macro_tokens += spans.len();
        if !self.emit {
            return;
        }
        for span in spans {
            self.declare_partial(line_of(span), MACRO_ARG);
        }
    }

    /// `let _ = <value expression>;`.
    ///
    /// A PLACE expression is left alone and is not declared: `_` does not bind,
    /// so `let _ = x;` moves nothing, drops nothing, and absorbs no error --
    /// there is no sink there to miss.
    pub(crate) fn let_underscore_site(&mut self, expr: &Expr, let_span: Span) {
        let target = strip_parens(expr);
        if is_place_expression(target) {
            return;
        }
        self.err_wrap(target, How::SinkLetUnderscore, line_of(let_span));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn expr(text: &str) -> Expr {
        syn::parse_str(text).unwrap_or_else(|e| panic!("parsing {text:?}: {e}"))
    }

    fn method(text: &str) -> ExprMethodCall {
        match expr(text) {
            Expr::MethodCall(m) => m,
            other => panic!("{text:?} is not a method call: {other:?}"),
        }
    }

    #[test]
    fn the_four_written_sinks_are_recognised_by_name_and_arity() {
        assert_eq!(sink_how(&method("f().ok()")), Some(How::SinkOk));
        assert_eq!(
            sink_how(&method("f().unwrap_or(0)")),
            Some(How::SinkUnwrapOr)
        );
        assert_eq!(
            sink_how(&method("f().unwrap_or_else(|_| 0)")),
            Some(How::SinkUnwrapOr)
        );
        assert_eq!(
            sink_how(&method("f().unwrap_or_default()")),
            Some(How::SinkUnwrapOr)
        );
    }

    #[test]
    fn nothing_else_is_a_sink() {
        // The two predicates design R2 refuses, `unwrap`/`expect` (derived from
        // the panic instead), and the arity/turbofish fences that keep a
        // workspace's own `ok` out of the manifest.
        for text in [
            "f().is_err()",
            "f().is_ok()",
            "f().unwrap()",
            "f().expect(\"x\")",
            "f().err()",
            "f().ok(1)",
            "f().unwrap_or()",
            "f().unwrap_or(1, 2)",
            "f().unwrap_or_default(1)",
            "f().ok::<u8>()",
        ] {
            assert_eq!(sink_how(&method(text)), None, "{text} must not be a sink");
        }
    }

    #[test]
    fn place_expressions_are_the_four_shapes_and_survive_parentheses() {
        for text in ["x", "self.field", "a.0", "v[0]", "*p", "(x)", "((self.f))"] {
            assert!(is_place_expression(&expr(text)), "{text} is a place");
        }
        for text in [
            "f()",
            "x.method()",
            "f()?",
            "{ f() }",
            "Err(1)",
            "Ok(1)",
            "1",
            "&x",
            "if c { a() } else { b() }",
        ] {
            assert!(!is_place_expression(&expr(text)), "{text} is a value");
        }
    }

    #[test]
    fn a_leading_struct_literal_is_found_through_every_edge_that_can_have_one() {
        for text in [
            "C { v: 1 }",
            "C { v: 1 }.go()",
            "C { v: 1 }.field",
            "C { v: 1 }.field[0]",
            "C { v: 1 }.go()?",
            "C { v: 1 }.a + 1",
            "&C { v: 1 }.a",
            "-C { v: 1 }.a",
        ] {
            assert!(
                leads_with_struct_literal(&expr(text)),
                "{text} leads with one"
            );
        }
        // Protected by brackets of some kind, or not there at all.
        for text in [
            "(C { v: 1 }).go()",
            "f(C { v: 1 })",
            "[C { v: 1 }][0]",
            "g()",
            "1 + C { v: 1 }.a",
        ] {
            assert!(
                !leads_with_struct_literal(&expr(text)),
                "{text} does not lead with one"
            );
        }
    }

    #[test]
    fn strip_parens_reaches_the_expression_the_wrap_goes_around() {
        assert!(matches!(strip_parens(&expr("((f()))")), Expr::Call(_)));
        assert!(matches!(strip_parens(&expr("f()")), Expr::Call(_)));
    }
}
