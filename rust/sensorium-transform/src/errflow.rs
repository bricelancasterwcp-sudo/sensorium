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
//! * **A place-expression receiver of one of the four sinks IS wrapped**
//!   (design R2 as amended 2026-09-04). All four take `self` BY VALUE, so the
//!   original call moves the receiver exactly as the wrap does: an E0507 the
//!   wrap could cause is one the sink caused already. Re-measured in
//!   `tests/oracle.rs`.
//! * **A parenthesised operand is descended into** ([`strip_parens`]):
//!   `match (g()) { .. }` is `unused_parens`, which is a build error under a
//!   workspace's own `#![deny(warnings)]`; `(match g() { .. })?` is clean.
//! * **An operand that would put a struct literal in an exterior position of
//!   the scrutinee is not wrapped** and is declared `partial` with reason
//!   [`STRUCT_LITERAL`]. rustc forbids one in EVERY exterior position, not
//!   just the leftmost: `match C { v: 1 }.go() { .. }`,
//!   `match 1 + C { v: 1 }.v { .. }`, `match 1..C { v: 1 }.v { .. }` and
//!   `match || C { v: 1 } { .. }` are all "struct literals are not allowed
//!   here", and none of them parses. [`leads_with_struct_literal`] is the fast
//!   path for the first shape; [`Ctx::err_wrap`]'s RE-PARSE is what decides the
//!   rest, because a syntactic rule this crate re-derived by hand would be a
//!   rule with a hole in it.
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

/// A site whose operand would put a struct literal in an EXTERIOR position of
/// the wrap's `match` scrutinee, which rustc does not allow (see the module
/// docs). Not in design R6's original list of reasons: it is added because the
/// alternative is emitting a file that does not parse, and a `?` that was not
/// reached is a `?` to declare whatever the cause.
pub(crate) const STRUCT_LITERAL: &str = "struct-literal";

/// A `?` inside an `async {}` block or an `async` closure (design R5/R6). The
/// future may be polled on a thread other than the one that built it, so a
/// probe there would record the site against whichever thread happened to
/// poll -- the same reason an `async fn` gets no guard. A plain closure created
/// INSIDE an async block is a different thing: its body runs when it is CALLED,
/// so `Ctx::in_async` is cleared on entering one and its `?` is wrapped.
pub(crate) const ASYNC_BLOCK: &str = "async-block";

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
    /// An `Err(..) =>` arm or `if let Err(..)` body whose error leaves the
    /// frame (design R2). RAISE, written at the arm's ENTRY.
    ArmPropagate,
    /// One whose bound name never escapes, or that binds nothing. HANDLED --
    /// and so a SWALLOWED candidate, which is why the escape test is
    /// deliberately strict.
    ArmHandled,
    /// One whose bound name escapes: HANDLED-class, but never a SWALLOWED
    /// candidate. The design's mechanical form of "bound to a name and stored".
    ArmAmbiguous,
}

impl How {
    /// The name the manifest row carries, and the name the converter reads.
    pub(crate) fn name(self) -> &'static str {
        match self {
            How::Try => "try",
            How::SinkOk => "sink_ok",
            How::SinkUnwrapOr => "sink_unwrap_or",
            How::SinkLetUnderscore => "sink_let_underscore",
            How::ArmPropagate => "arm_propagate",
            How::ArmHandled => "arm_handled",
            How::ArmAmbiguous => "arm_ambiguous",
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
            How::ArmPropagate => "HOW_ARM_PROPAGATE",
            How::ArmHandled => "HOW_ARM_HANDLED",
            How::ArmAmbiguous => "HOW_ARM_AMBIGUOUS",
        }
    }

    /// Which manifest `kind` a site with this `how` is.
    pub(crate) fn site_kind(self) -> SiteKind {
        match self {
            How::Try => SiteKind::Try,
            How::SinkOk | How::SinkUnwrapOr | How::SinkLetUnderscore => SiteKind::Sink,
            How::ArmPropagate | How::ArmHandled | How::ArmAmbiguous => SiteKind::Arm,
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
/// The one rule that still turns on this: `let _ = <place>;` is left alone,
/// because `_` does not bind, so that statement moves nothing, drops nothing
/// and absorbs no error -- there is no sink there to miss.
///
/// It is NOT a rule about sink RECEIVERS any more. Design R2 used to decline
/// those, with E0507 as the reason; re-measured on rustc 1.96 (2026-09-04) the
/// E0507 does not exist for the four written sinks, which all take `self` by
/// value -- a receiver the wrap cannot move is one the sink could not move
/// either (`t.last.ok()` on a `&T` is E0507 with or without the wrap), and
/// every place receiver that compiles plain compiles wrapped. The asymmetry is
/// real only for the `&self` PREDICATES `.is_err()`/`.is_ok()`, which R2
/// refuses to probe for exactly that reason.
/// `tests/oracle.rs::a_place_receiver_is_not_the_e0507_the_predicates_are` is
/// where the measurement lives.
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

/// Does the wrap this crate would emit around `operand` parse at all?
///
/// The scrutinee is the only part of the fragment that can fail, and it fails
/// for exactly one reason (an exterior struct literal), so the arm is the
/// shortest one that keeps the shape: `match <operand> { __t => __t }`. `syn`
/// applies the same no-struct-literal restriction to a `match` scrutinee that
/// rustc does, which is what makes this a faithful pre-flight rather than an
/// approximation of one.
///
/// A false NEGATIVE costs one declared site and nothing else; a false positive
/// costs the unit its instrumentation, which is why the answer comes from the
/// parser rather than from a rule.
fn wrap_reparses(operand: &str) -> bool {
    syn::parse_str::<Expr>(&format!("match {operand} {{ __t => __t }}")).is_ok()
}

/// Is this expression a leading atom followed only by POSTFIX operators?
///
/// Such an expression can hold a struct literal only in its leading position --
/// which [`leads_with_struct_literal`] has already answered -- or inside a
/// bracket, where it is protected. Everything else is re-parsed.
fn is_postfix_chain(e: &Expr) -> bool {
    match e {
        // Leading atoms. A parenthesised or macro-delimited expression carries
        // its own brackets, so whatever is inside is protected.
        Expr::Path(_) | Expr::Lit(_) | Expr::Paren(_) | Expr::Group(_) | Expr::Macro(_) => true,
        Expr::Call(c) => is_postfix_chain(&c.func),
        Expr::MethodCall(m) => is_postfix_chain(&m.receiver),
        Expr::Field(f) => is_postfix_chain(&f.base),
        Expr::Index(i) => is_postfix_chain(&i.expr),
        Expr::Try(t) => is_postfix_chain(&t.expr),
        Expr::Await(a) => is_postfix_chain(&a.base),
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
    pub(crate) fn err_qualname(&self) -> String {
        match self.closure_frames.last() {
            // Inside a FRAMED closure the err-flow rows belong to the closure:
            // a `?` there returns from the closure, so the RAISE the converter
            // reads has to name the frame it actually left (design R5, and the
            // task-3 invariant `closure_try` pins).
            Some(name) => name.clone(),
            None => self.item_qualname(),
        }
    }

    /// The enclosing NAMED ITEM's qualname, ignoring any closure frame -- what a
    /// closure's own `{{closure}}#k` name is built from, and what an err-flow
    /// row falls back to.
    pub(crate) fn item_qualname(&self) -> String {
        self.enclosing_qualname()
            .unwrap_or_else(|| self.scope_path())
    }

    /// Declare an err-flow site the transformer knows about and cannot reach
    /// (design R6). Honesty over coverage: `info` prints these, and E2''s
    /// numerator is measured against them.
    pub(crate) fn declare_partial(&mut self, line: u32, kind: SiteKind, reason: &'static str) {
        let qualname = self.err_qualname();
        self.partial.push(Partial {
            file: self.file.to_owned(),
            line,
            qualname,
            kind,
            reason,
        });
    }

    /// Mint a site index for an err-flow site and record its manifest row. Err
    /// sites take their numbers from the SAME per-unit counter as fn items
    /// (design R1b), which is why `kind` has to be on the row.
    pub(crate) fn mint_err_site(&mut self, how: How, line: u32, span: Span) -> Option<u32> {
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
            test: false,
            main: false,
        });
        Some(site)
    }

    /// The two splices of one err wrap: `match ` before the operand and the arm
    /// after it. The program's own `?`, `.ok()` or `;` is left OUTSIDE both.
    ///
    /// # The struct-literal fence
    ///
    /// A `match` scrutinee may not contain a struct literal in any EXTERIOR
    /// position, and the operand becomes one. The fence is a POST-CONDITION
    /// rather than a syntactic rule this crate re-derives: the wrap is built,
    /// the wrapped SCRUTINEE is handed back to `syn` -- the same parser that
    /// read the file -- and a site whose wrap does not re-parse is declared
    /// instead of emitted. A hand-written rule that missed a shape would emit a
    /// file rustc rejects, and the whole unit would fall back.
    ///
    /// Two things keep it cheap. [`leads_with_struct_literal`] answers the
    /// common shape without a parse at all, and the re-parse itself is skipped
    /// for an operand that is a pure postfix chain
    /// ([`is_postfix_chain`]) -- a chain can only hold a struct literal in a
    /// leading position, which the fast path already saw, or inside brackets,
    /// where it is protected. A `let _ = <value>` is re-parsed whatever its
    /// shape: it is the one site whose operand can be an arbitrary expression.
    fn err_wrap(&mut self, target: &Expr, how: How, line: u32) {
        let span = target.span();
        if leads_with_struct_literal(target) {
            // `match C { v: 1 }.go() { .. }` is "struct literals are not
            // allowed here" -- the wrapped file would not parse at all.
            self.declare_partial(line, how.site_kind(), STRUCT_LITERAL);
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
        let Some(text) = self.source.get(start..end) else {
            self.fail(
                span,
                "err-flow operand span is not a byte range of the source",
            );
            return;
        };
        let must_check = how == How::SinkLetUnderscore || !is_postfix_chain(target);
        if must_check && !wrap_reparses(text) {
            self.declare_partial(line, how.site_kind(), STRUCT_LITERAL);
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
    /// method call stays outside.
    ///
    /// A PLACE-expression receiver is wrapped like any other -- all four sinks
    /// take `self` by value, so the call moves the receiver exactly as the wrap
    /// does (see [`is_place_expression`] for the measurement that retired the
    /// old exception).
    pub(crate) fn sink_site(&mut self, node: &ExprMethodCall, how: How) {
        let line = line_of(node.method.span());
        let target = strip_parens(&node.receiver);
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
            self.declare_partial(line_of(span), SiteKind::Try, MACRO_ARG);
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
