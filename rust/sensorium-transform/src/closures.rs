//! Closures that contain a `?`, and the frame each one gets (design R5).
//!
//! A `?` inside a closure returns from the CLOSURE, not from the function
//! around it. Without a frame of its own the RAISE that `?` writes would be
//! read as leaving whatever fn the walk happened to be in, and the chain
//! machine would follow an `Err` out of a frame it never left. So a closure
//! whose body holds a `?` at its own depth is instrumented exactly as a fn is:
//!
//! ```ignore
//! |n| { let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);
//!       ::sensorium_rt::ret(.., Ok(match one() { __t => { .. } }? + n)) }
//! ```
//!
//! A block body takes the guard after its `{`; an EXPRESSION body is wrapped in
//! a block whose value is that expression, because a statement needs somewhere
//! to stand. Its exits are wrapped like a value-returning fn's -- a closure has
//! no declared return type to read, so the manifest row says `ret: "value"` and
//! the runtime ladder is what decides at the site whether there was anything to
//! record.
//!
//! # What is NOT framed
//!
//! * A closure with no `?`. It would cost a CALL/RETURN pair per call for
//!   nothing, and `tests/golden/closure_no_try` is the fence.
//! * An `async` closure. Its body is a future, which runs on whichever thread
//!   polls it -- the same reason `async fn` gets no guard -- so it is never
//!   framed and the `?` inside it is declared (`Ctx::in_async`). A PLAIN closure
//!   written INSIDE an async block is framed like any other: where it was
//!   written says nothing about when it runs, and its body runs synchronously on
//!   whichever thread calls it. `tests/golden/async_block_try` is that pair.
//! * A `?` inside a NESTED closure does not frame the outer one: it belongs to
//!   the inner closure's own depth, and the inner closure gets its own frame.

use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{Expr, ExprClosure};

use crate::exits;
use crate::names::line_of;
use crate::splice::{guard_fragment, scope_open_fragment, Kind, SCOPE_CLOSE};
use crate::visit::Ctx;
use crate::{RetKind, Site, SiteKind, MAX_SITE_INDEX};

/// Does this closure body hold a `?` at its OWN depth?
///
/// The walk stops at every construct whose body is not this closure's code: a
/// nested closure (whose `?` returns from IT), an `async` block (whose `?` is
/// declared, not wrapped), a `const` block, and a nested item.
pub(crate) fn holds_try(body: &Expr) -> bool {
    let mut walk = TryWalk { found: false };
    walk.visit_expr(body);
    walk.found
}

struct TryWalk {
    found: bool,
}

impl<'ast> Visit<'ast> for TryWalk {
    fn visit_expr_try(&mut self, node: &'ast syn::ExprTry) {
        self.found = true;
        syn::visit::visit_expr_try(self, node);
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {}
    fn visit_expr_async(&mut self, _node: &'ast syn::ExprAsync) {}
    fn visit_expr_const(&mut self, _node: &'ast syn::ExprConst) {}
    fn visit_item(&mut self, _node: &'ast syn::Item) {}
}

impl Ctx<'_> {
    /// Give one `?`-bearing closure a frame, and push its qualname so that every
    /// err-flow row inside belongs to the CLOSURE rather than to the item.
    ///
    /// Returns whether it pushed: the caller pops exactly when this says it did,
    /// so a closure whose body this crate could not reach leaves the stack as it
    /// found it.
    pub(crate) fn frame_closure(&mut self, node: &ExprClosure) -> bool {
        if !self.emit {
            return false;
        }
        let span = node.or1_token.span;
        if self.next_site > MAX_SITE_INDEX {
            self.fail(
                span,
                "site index past 24 bits: the runtime's site word cannot carry it",
            );
            return false;
        }
        // The placement is decided BEFORE a site index is spent, so a body this
        // crate cannot reach costs nothing and renumbers nothing.
        let Some(placement) = self.closure_placement(node) else {
            return false;
        };
        let site = self.next_site;
        self.next_site += 1;

        // `{{closure}}#k` is numbered per enclosing ITEM, never per enclosing
        // closure, so two nested `?`-bearing closures in one fn read `#1` and
        // `#2` rather than nesting their names.
        let owner = self.item_qualname();
        let ordinal = *self
            .closure_ordinals
            .entry(owner.clone())
            .and_modify(|k| *k += 1)
            .or_insert(1);
        let qualname = format!("{owner}::{{{{closure}}}}#{ordinal}");

        match placement {
            Placement::Statement(offset) => {
                self.push(offset, offset, Kind::Guard, guard_fragment(site));
            }
            Placement::Wrapped { start, end } => {
                self.push(
                    start,
                    start,
                    Kind::ScopeOpen,
                    scope_open_fragment(&guard_fragment(site)),
                );
                self.push(end, end, Kind::ScopeClose, SCOPE_CLOSE.to_owned());
            }
        }
        for operand in self.closure_operands(node) {
            self.wrap_operand(site, operand, span);
        }

        self.sites.push(Site {
            site,
            file: self.file.to_owned(),
            qualname: qualname.clone(),
            firstlineno: line_of(span),
            // A closure declares no return type, so there is nothing to read:
            // its exits are wrapped like a value-returning fn's and the runtime
            // ladder decides at the site what there was to record.
            ret: Some(RetKind::Value),
            kind: SiteKind::Closure,
            how: None,
            test: false,
            main: false,
        });
        self.closure_frames.push(qualname);
        true
    }

    /// Where the guard goes: after an existing `{`, or inside a block the wrap
    /// adds around an expression body.
    fn closure_placement(&mut self, node: &ExprClosure) -> Option<Placement> {
        if let Expr::Block(b) = &*node.body {
            if b.label.is_none() {
                return self
                    .body_offset(&b.attrs, &b.block)
                    .map(Placement::Statement);
            }
        }
        let span = node.body.span();
        let start = self.start_of(span);
        let end = self.end_of(span);
        if !self.source.is_char_boundary(start) || !self.source.is_char_boundary(end) {
            self.fail(span, "closure body offset falls inside a UTF-8 character");
            return None;
        }
        Some(Placement::Wrapped { start, end })
    }

    /// The closure's own exits: its tail and every `return` at its own depth.
    fn closure_operands(&self, node: &ExprClosure) -> Vec<exits::Operand> {
        match &*node.body {
            Expr::Block(b) if b.label.is_none() => exits::operands(&b.block),
            other => exits::expr_operands(other),
        }
    }
}

enum Placement {
    /// A byte offset just past a `{` the body already had.
    Statement(usize),
    /// The expression body's span, which the wrap puts a block around.
    Wrapped { start: usize, end: usize },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn closure(text: &str) -> ExprClosure {
        match syn::parse_str::<Expr>(text).unwrap_or_else(|e| panic!("parsing {text:?}: {e}")) {
            Expr::Closure(c) => c,
            other => panic!("{text:?} is not a closure: {other:?}"),
        }
    }

    #[test]
    fn a_question_mark_at_the_closures_own_depth_is_what_frames_it() {
        for text in [
            "|| f()?",
            "|| { let v = f()?; Ok(v) }",
            "|n| Ok(f(n)? + 1)",
            "|| { if c { g()?; } Ok(()) }",
            "move || { f()?; Ok(()) }",
        ] {
            assert!(holds_try(&closure(text).body), "{text} holds a `?`");
        }
    }

    #[test]
    fn a_question_mark_belonging_to_something_else_does_not() {
        for text in [
            "|| 1",
            "|n| n + 1",
            // The inner closure's `?` is the INNER closure's.
            "|| { let g = || f()?; g() }",
            // An async block's `?` is declared, not wrapped, and frames nothing.
            "|| async { f()?; Ok(()) }",
            // A nested item is its own fn item with its own site.
            "|| { fn inner() -> Result<u8, u8> { Ok(f()?) } inner() }",
        ] {
            assert!(!holds_try(&closure(text).body), "{text} holds no own `?`");
        }
    }
}
