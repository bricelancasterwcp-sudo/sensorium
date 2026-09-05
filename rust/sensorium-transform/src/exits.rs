//! Where a value-returning function's exits are, and which of them are wrapped.
//!
//! The exit form (plan decision, replacing spec §3.2's `match` wrap, which trips
//! `unused_parens`):
//!
//! ```ignore
//! ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, <site>, |__r| {
//!     use ::sensorium_rt::probe::*;
//!     ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
//! }, <e>)
//! ```
//!
//! The capture closure comes BEFORE the operand, so a diverging operand leaves
//! nothing unreachable after it; the operand is a call ARGUMENT, which is a
//! coercion site, so `Box<dyn T>` and `&String -> &str` tails still coerce; and
//! nothing is ever `let`-hoisted, so a `MutexGuard` in the operand is released
//! exactly where it was (`rust/HONESTY.md` §9, measured by
//! `tests/oracle.rs`'s two run probes).
//!
//! # What is wrapped
//!
//! The tail expression, and every `return <e>` at closure depth 0, of a
//! [`RetKind::Value`] function. Depth 0 means: not inside a closure, an `async`
//! block or a `const` block -- a `return` in any of those leaves that construct,
//! not this function -- and not inside a nested item, which is its own fn item
//! with its own site.
//!
//! # What is not, and why
//!
//! Operands that are syntactically diverging. Wrapping one makes the `ret` call
//! itself unreachable, which rustc reports as `unreachable_code` (measured on
//! rustc 1.96 under `-D warnings`, 2026-09-02) -- and under a workspace's own
//! `#![deny(warnings)]` that is a build error, so the whole unit would fall
//! back. The frame closes `none`, which is exactly what `rust/HONESTY.md` §1
//! says `none` means:
//!
//! * a `return`, `break` or `continue` expression;
//! * a `loop` with no `break` that gives IT a value (a valued `break` in a
//!   nested loop, or one carrying another loop's label, does not count);
//! * a macro call whose path ends in `panic`, `unreachable`, `todo` or
//!   `unimplemented`;
//! * a call whose callee path ends in `process::exit` or `process::abort`.
//!
//! Everything else is an ordinary expression and is wrapped -- `format!`,
//! `vec!`, `if`, `match`, a struct literal, a `?`, a labelled `loop` with a
//! valued `break`.
//!
//! **Two shapes beyond the plan's list ARE handled here, by ruling F3**, both
//! measured on rustc 1.96 (2026-09-02):
//!
//! * a plain block `{ e }` as the operand would trip `unused_braces` if wrapped
//!   whole, so `descend_bare_block` (below) descends into it and the wrap goes
//!   on `e` -- a labelled block is left alone, because a `break '<label> <v>`
//!   would leave past a wrap placed inside it. Golden: `block_tail`
//!   (`tests/golden.rs::a_bare_block_tail_is_wrapped_inside_its_braces`);
//! * a block, `if` or `match` all of whose arms diverge would make the `ret`
//!   call unreachable, so `diverges_compositely` (below) treats it as diverging
//!   and it is not wrapped at all. One value-carrying arm is enough to make the
//!   operand ordinary. Goldens: `composite_diverging` and the `mixed_arms`
//!   fence (`tests/golden.rs::a_composite_every_arm_of_which_diverges_is_not_wrapped`).

use proc_macro2::{Delimiter, TokenStream, TokenTree};
use std::str::FromStr;
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{
    Block, Expr, ExprBreak, ExprLoop, Item, Lifetime, Macro, ReturnType, Signature, Stmt,
    StmtMacro, Type,
};

use crate::RetKind;

/// One exit operand, as RAW `Span::byte_range()` offsets -- the caller adds the
/// prefix `syn::parse_file` stripped before `proc-macro2` saw the text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Operand {
    /// The operand's first byte, outer attributes included.
    pub start: usize,
    /// Just past its last byte.
    pub end: usize,
}

/// Macro paths whose call never returns.
const DIVERGING_MACROS: [&str; 4] = ["panic", "unreachable", "todo", "unimplemented"];
/// Function paths, under a `process` segment, whose call never returns.
const DIVERGING_PROCESS_FNS: [&str; 2] = ["exit", "abort"];

/// What a signature says the function returns.
pub(crate) fn ret_kind(sig: &Signature) -> RetKind {
    match &sig.output {
        ReturnType::Default => RetKind::Unit,
        ReturnType::Type(_, ty) => from_type(ty),
    }
}

fn from_type(ty: &Type) -> RetKind {
    match ty {
        Type::Tuple(t) if t.elems.is_empty() => RetKind::Unit,
        Type::Never(_) => RetKind::Never,
        Type::Paren(p) => from_type(&p.elem),
        Type::Group(g) => from_type(&g.elem),
        _ => RetKind::Value,
    }
}

/// Every operand of one function body, in source order.
pub(crate) fn operands(block: &Block) -> Vec<Operand> {
    let mut walk = ReturnWalk { out: Vec::new() };
    walk.visit_block(block);
    let mut out = walk.out;
    if let Some(tail) = tail_operand(block) {
        out.push(tail);
    }
    out.sort_unstable_by_key(|o| (o.start, o.end));
    out
}

/// Every operand of one closure's EXPRESSION body, in source order.
///
/// A block-bodied closure goes through [`operands`] like a fn; this is the
/// other shape, where the body IS the tail. A `return` inside it is still this
/// closure's exit, so [`ReturnWalk`] runs over the expression too -- and stops
/// at a nested closure exactly as it does inside a block.
pub(crate) fn expr_operands(e: &Expr) -> Vec<Operand> {
    let mut walk = ReturnWalk { out: Vec::new() };
    walk.visit_expr(e);
    let mut out = walk.out;
    if let Some(tail) = operand_of(e) {
        out.push(tail);
    }
    out.sort_unstable_by_key(|o| (o.start, o.end));
    out
}

/// The block's value, when it has one and it is worth probing.
fn tail_operand(block: &Block) -> Option<Operand> {
    match block.stmts.last()? {
        Stmt::Expr(e, None) => operand_of(e),
        // A BRACE-delimited macro invocation in statement position is a
        // `Stmt::Macro`, not an expression -- `m!{1}` and `m!(1)` are the same
        // value and different syn nodes, so the tail walk has to know both.
        Stmt::Macro(m) if m.semi_token.is_none() => macro_operand(m),
        _ => None,
    }
}

fn operand_of(e: &Expr) -> Option<Operand> {
    // A bare `{ e }` is descended INTO rather than wrapped whole.
    let e = descend_bare_block(e);
    if diverges(e) {
        return None;
    }
    let range = e.span().byte_range();
    Some(Operand {
        start: range.start,
        end: range.end,
    })
}

fn macro_operand(m: &StmtMacro) -> Option<Operand> {
    if diverging_macro(&m.mac) {
        return None;
    }
    let range = m.mac.span().byte_range();
    Some(Operand {
        start: range.start,
        end: range.end,
    })
}

/// `{ e }` -- an unlabelled block whose entire content is one unsemicoloned
/// expression -- yields exactly what `e` yields, so the wrap goes on `e`,
/// INSIDE the braces. Nested bare blocks unwrap all the way down.
///
/// Wrapping the block whole would put braces around a call argument, which
/// rustc reports as `unused_braces` (measured on rustc 1.96, 2026-09-02).
/// Note what that lint also means: `fn f() -> u8 { { 1 } }` **already** warns
/// in the untransformed source ("unnecessary braces around block return
/// value"), so the shape cannot occur in a warning-clean workspace at all.
/// Descending is what makes sure the transformer is not the one that puts a
/// second, different diagnostic there.
///
/// A LABELLED block is left alone. `unused_braces` does not fire on one, and a
/// `break '<label> <value>` inside would leave past a wrap placed within it.
fn descend_bare_block(e: &Expr) -> &Expr {
    let Expr::Block(b) = e else {
        return e;
    };
    if b.label.is_some() {
        return e;
    }
    match b.block.stmts.as_slice() {
        [Stmt::Expr(inner, None)] => descend_bare_block(inner),
        _ => e,
    }
}

/// How many bytes of `text` are the operand's OUTER ATTRIBUTES.
///
/// The splice has to go between the attributes and the expression: an attribute
/// belongs to the statement, and `f(#[cfg(x)] e)` is not Rust. The text is
/// re-tokenised rather than matched against forty `Expr` variants, and a doc
/// comment is handled by the same two tokens every attribute is, because
/// `proc-macro2` hands `/// x` back as `#` plus a bracketed group.
pub(crate) fn attribute_prefix_len(text: &str) -> Option<usize> {
    let tokens: Vec<TokenTree> = TokenStream::from_str(text).ok()?.into_iter().collect();
    let mut i = 0;
    while i + 1 < tokens.len() {
        let TokenTree::Punct(p) = &tokens[i] else {
            break;
        };
        if p.as_char() != '#' {
            break;
        }
        let TokenTree::Group(g) = &tokens[i + 1] else {
            break;
        };
        if g.delimiter() != Delimiter::Bracket {
            break;
        }
        i += 2;
    }
    if i == 0 {
        return Some(0);
    }
    Some(tokens.get(i)?.span().byte_range().start)
}

// ---------------------------------------------------------------------------
// Divergence
// ---------------------------------------------------------------------------

/// Strip the wrappers that carry no meaning of their own, so `(return 1)` is
/// still a `return`.
fn strip(e: &Expr) -> &Expr {
    match e {
        Expr::Paren(p) => strip(&p.expr),
        Expr::Group(g) => strip(&g.expr),
        other => other,
    }
}

fn diverges(e: &Expr) -> bool {
    let e = strip(e);
    diverges_directly(e) || diverges_compositely(e)
}

/// An operand that is itself one of the diverging constructs.
fn diverges_directly(e: &Expr) -> bool {
    match e {
        Expr::Return(_) | Expr::Break(_) | Expr::Continue(_) => true,
        Expr::Loop(l) => !has_valued_break(l),
        Expr::Macro(m) => diverging_macro(&m.mac),
        Expr::Call(c) => diverging_call(&c.func),
        _ => false,
    }
}

/// A composite EVERY ONE of whose arms diverges. rustc calls the `ret` call
/// after such an operand unreachable -- `unreachable_code`, measured on rustc
/// 1.96 under `-D warnings`, 2026-09-02 -- and a warning is a build error under
/// a workspace's own `#![deny(warnings)]`, which would drop the whole unit to a
/// fallback.
///
/// One value-carrying arm is enough to make the operand ordinary:
/// `match x { A => panic!(), B => 1 }` IS wrapped, and
/// `tests/golden/mixed_arms` is the fence that says so.
fn diverges_compositely(e: &Expr) -> bool {
    match e {
        Expr::Block(b) => block_diverges(&b.block) && !escapes_by_label(b),
        Expr::Unsafe(u) => block_diverges(&u.block),
        Expr::If(i) => match &i.else_branch {
            Some((_, otherwise)) => block_diverges(&i.then_branch) && diverges(otherwise),
            // With no `else` the whole `if` is `()`, so it is not a
            // value-returning function's operand and it does not diverge.
            None => false,
        },
        Expr::Match(m) => !m.arms.is_empty() && m.arms.iter().all(|a| diverges(&a.body)),
        _ => false,
    }
}

/// Does a block's own value diverge? Its LAST statement decides -- a diverging
/// statement anywhere earlier already makes the original source warn, so it is
/// not this crate's to find.
fn block_diverges(b: &Block) -> bool {
    match b.stmts.last() {
        Some(Stmt::Expr(e, _)) => diverges(e),
        Some(Stmt::Macro(m)) => diverging_macro(&m.mac),
        _ => false,
    }
}

/// A labelled block that a `break '<label> <value>` can leave does not diverge,
/// however its tail ends.
fn escapes_by_label(b: &syn::ExprBlock) -> bool {
    let Some(label) = &b.label else {
        return false;
    };
    let mut walk = BreakWalk {
        label: Some(&label.name),
        // A block is not a loop: an unlabelled `break` inside targets the
        // nearest LOOP, so only a labelled one can leave this block. Starting
        // past zero is what says so.
        nested: 1,
        found: false,
    };
    walk.visit_block(&b.block);
    walk.found
}

fn diverging_macro(mac: &Macro) -> bool {
    mac.path
        .segments
        .last()
        .is_some_and(|s| DIVERGING_MACROS.contains(&s.ident.to_string().as_str()))
}

/// `std::process::exit`, `process::abort` -- a suffix match over at least two
/// segments, so a workspace's own `exit()` is not mistaken for one.
fn diverging_call(func: &Expr) -> bool {
    let Expr::Path(p) = strip(func) else {
        return false;
    };
    let n = p.path.segments.len();
    if n < 2 {
        return false;
    }
    p.path.segments[n - 2].ident == "process"
        && DIVERGING_PROCESS_FNS.contains(&p.path.segments[n - 1].ident.to_string().as_str())
}

/// Does any `break` give THIS loop a value?
fn has_valued_break(l: &ExprLoop) -> bool {
    let mut walk = BreakWalk {
        label: l.label.as_ref().map(|l| &l.name),
        nested: 0,
        found: false,
    };
    walk.visit_block(&l.body);
    walk.found
}

struct BreakWalk<'a> {
    label: Option<&'a Lifetime>,
    /// Loops between the `break` and the loop under test. An unlabelled `break`
    /// targets the innermost one, so it is this loop's only at depth 0.
    nested: usize,
    found: bool,
}

impl BreakWalk<'_> {
    fn targets_this_loop(&self, b: &ExprBreak) -> bool {
        match (&b.label, self.label) {
            (Some(l), Some(mine)) => l.ident == mine.ident,
            (Some(_), None) => false,
            (None, _) => self.nested == 0,
        }
    }
}

impl<'ast> Visit<'ast> for BreakWalk<'_> {
    fn visit_expr_break(&mut self, node: &'ast ExprBreak) {
        if node.expr.is_some() && self.targets_this_loop(node) {
            self.found = true;
        }
        syn::visit::visit_expr_break(self, node);
    }

    fn visit_expr_loop(&mut self, node: &'ast ExprLoop) {
        self.nested += 1;
        syn::visit::visit_expr_loop(self, node);
        self.nested -= 1;
    }

    fn visit_expr_while(&mut self, node: &'ast syn::ExprWhile) {
        self.nested += 1;
        syn::visit::visit_expr_while(self, node);
        self.nested -= 1;
    }

    fn visit_expr_for_loop(&mut self, node: &'ast syn::ExprForLoop) {
        self.nested += 1;
        syn::visit::visit_expr_for_loop(self, node);
        self.nested -= 1;
    }

    fn visit_expr_closure(&mut self, _node: &'ast syn::ExprClosure) {}
    fn visit_expr_async(&mut self, _node: &'ast syn::ExprAsync) {}
    fn visit_expr_const(&mut self, _node: &'ast syn::ExprConst) {}
    fn visit_item(&mut self, _node: &'ast Item) {}
}

// ---------------------------------------------------------------------------
// `return <e>` at closure depth 0
// ---------------------------------------------------------------------------

struct ReturnWalk {
    out: Vec<Operand>,
}

impl<'ast> Visit<'ast> for ReturnWalk {
    fn visit_expr_return(&mut self, node: &'ast syn::ExprReturn) {
        if let Some(e) = node.expr.as_deref() {
            if let Some(op) = operand_of(e) {
                self.out.push(op);
            }
        }
        // Keep going: a `return` nested inside a returned expression is another
        // exit of this same function, and both are wrapped.
        syn::visit::visit_expr_return(self, node);
    }

    /// A `return` in a closure leaves the CLOSURE. Closure frames are rung 3
    /// (spec §3.3), and wrapping this would stash a capture the enclosing
    /// frame's guard would take as its own.
    fn visit_expr_closure(&mut self, _node: &'ast syn::ExprClosure) {}

    /// Same for an `async` block: the `return` leaves the future.
    fn visit_expr_async(&mut self, _node: &'ast syn::ExprAsync) {}

    /// `return` is not allowed in a `const` block, and its body is not this
    /// function's code.
    fn visit_expr_const(&mut self, _node: &'ast syn::ExprConst) {}

    /// A nested `fn`, `impl` or `mod` is its own fn item with its own site; the
    /// visitor in `splice.rs` reaches it separately.
    fn visit_item(&mut self, _node: &'ast Item) {}
}
