//! The focus tier's statement walk: one LINE probe after every statement of a
//! focused function, carrying the bindings that statement wrote.
//!
//! This is the second walk over a focused function's body. [`crate::visit`]'s
//! is the first: it places the entry guard, the exit wraps, the err-flow probes
//! and the spawn rewrites, and it descends into nested items. This one runs
//! from [`crate::visit::Ctx::fn_item`] the moment a function is found to be in
//! the focus, and it does exactly one thing -- put point splices where the
//! design's §3.1/§3.2 tables say a LINE goes. It lives in its own module because
//! `visit.rs` is at the 800-line ceiling, and because "where a LINE goes" is a
//! separate rule from "where a frame goes".
//!
//! # What it emits (design amendment A7, verbatim)
//!
//! ```ignore
//! ::sensorium_rt::line(&crate::__SENSORIUM_UNIT, <site>, || [("x", ::sensorium_rt::probe_cap!(&x))]);
//! ```
//!
//! and `|| []` for a statement that wrote nothing -- the row still says the line
//! ran. Every fragment is newline-free and every splice is a POINT splice: the
//! statement itself is never re-rendered, so no line, column, panic location or
//! `line!()` moves (spec §3.1).
//!
//! # Where a probe goes
//!
//! * The **parameters LINE**, at the body offset the entry guard uses and
//!   ordered AFTER it ([`crate::splice::Kind::Line`] sorts after
//!   [`crate::splice::Kind::Guard`]) -- amendment A6: a LINE must fall inside
//!   its function's CALL, so it cannot precede the guard that opens the frame.
//!   A function with no parameters still mints it, with `|| []` (amendment A2).
//! * After **every statement** of every block at every depth: the body, `if` and
//!   `else` blocks, `loop`/`while`/`for` bodies, `match` arm blocks, plain and
//!   `unsafe` blocks. The splice goes after the statement's `;`, or after the
//!   closing `}` of a block-like expression statement.
//! * At the **entry of an arm or loop body whose pattern binds** at least one
//!   identifier (`match` arm, `if let`, `while let`, `for`): a probe as the
//!   body's first statement, at the arm's or loop's line, once per entry or
//!   iteration. A pattern that binds nothing mints nothing (amendment A3), and
//!   a bare-expression arm body is wrapped in a block to give the statement
//!   somewhere to stand (amendment A1), exactly as an `Err(..) =>` arm's probe
//!   already is.
//!
//! # What it declines, and why (design §3.1/§3.3 plus this task's rulings)
//!
//! * **Closure bodies, `async` blocks, `const` blocks**: the walk stops at
//!   them. A closure's statements run when it is CALLED, an `async` block's when
//!   it is polled, and `sensorium_rt::line` is not a `const fn`.
//! * **Nested items**: a `fn`, `impl`, `mod`, `const` or `static` written inside
//!   a body is a separate item with its own qualname, and [`crate::visit`] will
//!   reach it and focus it on its own merits. A `Stmt::Item` therefore mints no
//!   LINE either -- an item declaration is not on any execution path, so a row
//!   for it would say a line ran that never runs.
//! * **A diverging statement** (`return`, `break`, `continue`, `panic!(..)`,
//!   `std::process::exit(..)`, a `loop` NO `break` leaves, and the composites
//!   [`crate::exits`] already
//!   classifies): the probe after it would be unreachable code -- a WARNING,
//!   which under a workspace's `#![deny(warnings)]` is a build error and costs
//!   the unit its instrumentation. Design §3.1 says the same thing from the
//!   other side: such a statement's exit is already the RETURN or RAISE row.
//! * **The tail expression**, which is not a statement: its value is the
//!   block's, and a statement placed after it would be placed after the block's
//!   value. Its own sub-blocks are still walked.
//! * **A statement a `cfg` can remove**: `#[cfg(unix)] let a = 1;` is one
//!   statement to `syn` and zero or one to rustc, and the probe -- spliced
//!   AFTER it -- survives a `cfg` that strips it. A probe naming `a` would then
//!   not compile, and even an empty one would claim a line ran that was never
//!   built. Only `#[cfg]` and `#[cfg_attr]` can do that: `#[allow(..)]`,
//!   `#[rustfmt::skip]` and the rest leave the statement in the build and take
//!   their LINE like any other ([`is_conditionally_compiled`]).
//! * **A place write** (`*p = e`, `a.b = e`, `v[i] = e`) and a `&mut` mutation
//!   are not deltas (design §3.2), so those statements mint `|| []`.
//! * **A name that is not a plausible binding**: `syn` cannot tell the pattern
//!   `None` (a unit variant) from the pattern `other` (a binding) -- both parse
//!   as `Pat::Ident`, and resolution is rustc's job, not a parser's. A delta for
//!   `None` would emit `probe_cap!(&None)`, whose type is unconstrained. So a
//!   name whose first character is uppercase is read as a path pattern and not
//!   as a binding, which is Rust's own naming convention (`non_snake_case` is a
//!   warn-by-default lint). The cost is a missed delta for a binding written
//!   against that convention; the alternative is a workspace that does not
//!   compile under a focus.
//!
//! # Borrow safety
//!
//! Each value is taken by shared borrow immediately after the write, inside the
//! probe call, and the temporary ends at the probe's `;` (design §3.2). The
//! capture precedes any later statement, so no move has happened yet, and the
//! probe touches only the names the statement itself wrote, so no live `&mut`
//! to another binding is crossed. `tests/oracle.rs` measures this on a moved
//! value rather than arguing it.

use proc_macro2::Span;
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{
    Arm, Attribute, BinOp, Block, Expr, ExprAsync, ExprBreak, ExprClosure, ExprConst, ExprForLoop,
    ExprIf, ExprLoop, ExprWhile, FnArg, Item, Lifetime, MacroDelimiter, Pat, Signature, Stmt,
};

use crate::arms::bound_names;
use crate::exits;
use crate::names::line_of;
use crate::splice::{scope_open_fragment, Kind, SCOPE_CLOSE};
use crate::visit::Ctx;
use crate::{Site, SiteKind, MAX_SITE_INDEX};

/// The LINE probe, as amendment A7 spells it. The ONLY place its text is
/// written -- `tests/common/mod.rs` writes it a second time, so a golden diff
/// fails the moment the two disagree.
///
/// The unit path is spelled exactly as [`crate::splice::guard_fragment`] and
/// [`crate::splice::ret_open_fragment`] spell it: the fragments share one
/// static, and a second spelling of it would be a second static.
fn line_fragment(site: u32, names: &[String]) -> String {
    let mut deltas = String::new();
    for (i, name) in names.iter().enumerate() {
        if i > 0 {
            deltas.push_str(", ");
        }
        deltas.push_str(&format!(
            "(\"{name}\", ::sensorium_rt::probe_cap!(&{name}))"
        ));
    }
    format!("::sensorium_rt::line(&crate::__SENSORIUM_UNIT, {site}, || [{deltas}]);")
}

/// Splice one focused function's LINE probes.
///
/// `body_offset` is the offset [`crate::visit::Ctx::fn_item`] already computed
/// for the entry guard -- past the body's `{` and past any inner attribute. It
/// is passed rather than recomputed so that the parameters LINE cannot land
/// anywhere but where the guard landed (amendment A6), and so that this module
/// never has to reason about `#![..]` a second time.
pub(crate) fn walk_body(
    ctx: &mut Ctx,
    sig: &Signature,
    block: &Block,
    fn_qualname: &str,
    body_offset: usize,
) {
    let mut walk = Walk {
        ctx,
        qualname: fn_qualname,
    };
    walk.parameters(sig, body_offset);
    walk.visit_block(block);
}

/// The walk's state: the shared [`Ctx`] every splice and site goes into, and the
/// qualname every LINE site is named after -- the ENCLOSING FUNCTION's, at every
/// block depth, because a LINE belongs to the frame the guard opened.
struct Walk<'a, 'b> {
    ctx: &'a mut Ctx<'b>,
    qualname: &'a str,
}

impl Walk<'_, '_> {
    /// The parameters LINE (design §3.2's last-but-one row, amendments A2/A6).
    fn parameters(&mut self, sig: &Signature, body_offset: usize) {
        let mut names: Vec<String> = Vec::new();
        for arg in &sig.inputs {
            match arg {
                // `self`, `&self`, `&mut self` and `mut self` are all read the
                // same way: amendment A7 verified `probe_cap!(&self)` for a
                // reference receiver and for a by-value one.
                FnArg::Receiver(_) => names.push("self".to_owned()),
                FnArg::Typed(t) => names.extend(binding_names(&t.pat)),
            }
        }
        self.emit(
            body_offset,
            line_of(sig.fn_token.span),
            &names,
            sig.fn_token.span,
        );
    }

    /// Mint a site and put one probe at `at`. Nothing is emitted if the site
    /// index would overflow the wire format's 24 bits.
    fn emit(&mut self, at: usize, line: u32, names: &[String], span: Span) {
        self.emit_kind(at, line, names, span, Kind::Line);
    }

    /// [`Walk::emit`] with the splice kind said out loud -- the one thing that
    /// differs between a statement's LINE and an arm-entry's.
    fn emit_kind(&mut self, at: usize, line: u32, names: &[String], span: Span, kind: Kind) {
        let Some(site) = self.mint(line, span) else {
            return;
        };
        self.ctx.push(at, at, kind, line_fragment(site, names));
    }

    fn mint(&mut self, line: u32, span: Span) -> Option<u32> {
        if self.ctx.next_site > MAX_SITE_INDEX {
            self.ctx.fail(
                span,
                "site index past 24 bits: the runtime's site word cannot carry it",
            );
            return None;
        }
        let site = self.ctx.next_site;
        self.ctx.next_site += 1;
        self.ctx.sites.push(Site {
            site,
            file: self.ctx.file.to_owned(),
            qualname: self.qualname.to_owned(),
            firstlineno: line,
            // A LINE is not a frame and has no signature: `ret` and `how` are
            // silences here, not defaults.
            ret: None,
            kind: SiteKind::Line,
            how: None,
            test: false,
            main: false,
        });
        Some(site)
    }

    /// One statement's probe: after its last byte, with the names it wrote.
    fn statement(&mut self, stmt: &Stmt, is_tail: bool) {
        if is_conditionally_compiled(stmt) {
            return;
        }
        let Some(at) = self.statement_end(stmt, is_tail) else {
            return;
        };
        let names = statement_deltas(stmt);
        let span = statement_span(stmt);
        self.emit(at, line_of(span), &names, span);
    }

    /// Where the probe goes, or `None` when this statement takes none.
    fn statement_end(&mut self, stmt: &Stmt, is_tail: bool) -> Option<usize> {
        match stmt {
            // A `let` always ends in a `;`, `let`-`else` included.
            Stmt::Local(local) => Some(self.ctx.end_of(local.semi_token.span)),
            // A nested item declaration is not on an execution path.
            Stmt::Item(_) => None,
            Stmt::Expr(expr, Some(semi)) => {
                (!stmt_diverges(expr)).then(|| self.ctx.end_of(semi.span))
            }
            // No semicolon: either the block's TAIL (not a statement), or a
            // block-like expression used as one.
            Stmt::Expr(expr, None) => {
                if is_tail || stmt_diverges(expr) {
                    return None;
                }
                self.block_like_end(expr)
            }
            Stmt::Macro(mac) => {
                if exits::diverging_macro(&mac.mac) {
                    return None;
                }
                match (&mac.semi_token, &mac.mac.delimiter) {
                    (Some(semi), _) => Some(self.ctx.end_of(semi.span)),
                    // `foo! { .. }` in statement position needs no `;`.
                    (None, MacroDelimiter::Brace(brace)) => {
                        Some(self.ctx.end_of(brace.span.close()))
                    }
                    (None, _) => None,
                }
            }
        }
    }

    /// The end of a block-like expression statement, with the byte the grammar
    /// says must be there checked -- the same discipline every other offset in
    /// this crate is computed under.
    fn block_like_end(&mut self, expr: &Expr) -> Option<usize> {
        if !is_block_like(expr) {
            return None;
        }
        let span = expr.span();
        let end = self.ctx.end_of(span);
        if self.ctx.source.as_bytes().get(end.checked_sub(1)?) != Some(&b'}') {
            self.ctx.fail(
                span,
                "byte offset does not land past a block statement's closing brace -- \
                 Span::byte_range() is not relative to what this crate assumes",
            );
            return None;
        }
        Some(end)
    }

    /// The arm-entry / loop-entry probe (design §3.2, amendments A1 and A3).
    ///
    /// Placed exactly where an `Err(..) =>` arm's probe is placed
    /// (`arms::place_arm_probe`): inside a block body the arm already has, or
    /// inside one this wrap adds. A LABELLED block is wrapped rather than
    /// written into, for the same reason: a `break '<label> <value>` would
    /// leave past a statement placed within it.
    fn entry(&mut self, names: &[String], line: u32, body: EntryBody<'_>, span: Span) {
        if names.is_empty() {
            return;
        }
        let block = match body {
            EntryBody::Block(b) => Some((&[][..], b)),
            EntryBody::Expr(Expr::Block(b)) if b.label.is_none() => {
                Some((b.attrs.as_slice(), &b.block))
            }
            EntryBody::Expr(_) => None,
        };
        if let Some((attrs, block)) = block {
            if let Some(offset) = self.ctx.body_offset(attrs, block) {
                // `Kind::LineEntry`, not `Kind::Line`: an `Err(..) =>` arm's
                // own probe lands on this byte too, and the arm-entry LINE goes
                // in front of it -- which is where the bare-expression form
                // (A1) puts it, and the two forms must not disagree.
                self.emit_kind(offset, line, names, span, Kind::LineEntry);
            }
            return;
        }
        let EntryBody::Expr(expr) = body else {
            unreachable!("a block body took the branch above")
        };
        self.wrap_expression_body(expr, names, line);
    }

    /// Amendment A1: `Some(n) => n * 2,` becomes `Some(n) => { <probe> n * 2 }`
    /// -- two point splices, so the arm still evaluates to exactly what it did.
    fn wrap_expression_body(&mut self, expr: &Expr, names: &[String], line: u32) {
        let span = expr.span();
        let start = self.ctx.start_of(span);
        let end = self.ctx.end_of(span);
        if !self.ctx.source.is_char_boundary(start) || !self.ctx.source.is_char_boundary(end) {
            self.ctx
                .fail(span, "arm body offset falls inside a UTF-8 character");
            return;
        }
        let Some(site) = self.mint(line, span) else {
            return;
        };
        let probe = line_fragment(site, names);
        self.ctx
            .push(start, start, Kind::ScopeOpen, scope_open_fragment(&probe));
        self.ctx
            .push(end, end, Kind::ScopeClose, SCOPE_CLOSE.to_owned());
    }
}

/// Which body an entry probe goes into.
enum EntryBody<'a> {
    Block(&'a Block),
    Expr(&'a Expr),
}

impl<'ast> Visit<'ast> for Walk<'_, '_> {
    /// Every block at every depth, and the ONE place a statement probe is
    /// decided: the last statement of a block is its tail unless it carries a
    /// `;`, and a tail is not a statement.
    fn visit_block(&mut self, node: &'ast Block) {
        let last = node.stmts.len().wrapping_sub(1);
        for (i, stmt) in node.stmts.iter().enumerate() {
            self.visit_stmt(stmt);
            self.statement(stmt, i == last);
        }
    }

    fn visit_arm(&mut self, node: &'ast Arm) {
        let names = binding_names(&node.pat);
        self.entry(
            &names,
            line_of(node.pat.span()),
            EntryBody::Expr(&node.body),
            node.pat.span(),
        );
        syn::visit::visit_arm(self, node);
    }

    /// `if let PAT = ..` -- the bindings enter the THEN block. A plain `if` and
    /// an `else` branch bind nothing and mint nothing.
    fn visit_expr_if(&mut self, node: &'ast ExprIf) {
        let names = let_bindings(&node.cond);
        self.entry(
            &names,
            line_of(node.if_token.span),
            EntryBody::Block(&node.then_branch),
            node.if_token.span,
        );
        syn::visit::visit_expr_if(self, node);
    }

    /// `while let PAT = ..` -- once per iteration, like an arm.
    fn visit_expr_while(&mut self, node: &'ast ExprWhile) {
        let names = let_bindings(&node.cond);
        self.entry(
            &names,
            line_of(node.while_token.span),
            EntryBody::Block(&node.body),
            node.while_token.span,
        );
        syn::visit::visit_expr_while(self, node);
    }

    fn visit_expr_for_loop(&mut self, node: &'ast ExprForLoop) {
        let names = binding_names(&node.pat);
        self.entry(
            &names,
            line_of(node.for_token.span),
            EntryBody::Block(&node.body),
            node.for_token.span,
        );
        syn::visit::visit_expr_for_loop(self, node);
    }

    /// A closure's statements run when it is CALLED. Call-level instrumentation
    /// only (design §3.3), so the walk stops here.
    fn visit_expr_closure(&mut self, _: &'ast ExprClosure) {}

    /// An `async` block's statements run when the future is polled, on whatever
    /// thread polls it; the same reason `async fn` is not focusable.
    fn visit_expr_async(&mut self, _: &'ast ExprAsync) {}

    /// `sensorium_rt::line` is not a `const fn`, so nothing goes in a `const`
    /// block -- the same fence `Ctx::const_ctx` holds for the err-flow probes.
    fn visit_expr_const(&mut self, _: &'ast ExprConst) {}

    /// A nested item is a separate item with its own qualname; the main walk
    /// reaches it and focuses it on its own merits.
    fn visit_item(&mut self, _: &'ast Item) {}
}

/// Is this expression one whose statement form ends in `}`?
fn is_block_like(expr: &Expr) -> bool {
    matches!(
        expr,
        Expr::Block(_)
            | Expr::Unsafe(_)
            | Expr::If(_)
            | Expr::Match(_)
            | Expr::Loop(_)
            | Expr::While(_)
            | Expr::ForLoop(_)
            | Expr::TryBlock(_)
            | Expr::Async(_)
            | Expr::Const(_)
    )
}

/// The span whose line a statement's LINE site reports: the first token AFTER
/// its outer attributes.
///
/// `Spanned` on a `Stmt` starts at the `#` of an attribute, so
/// `#[allow(unused_mut)]\n let mut c = 3;` would report the attribute's line
/// for a statement a reader sees on the next one. `let` and a macro's path are
/// reachable directly; an attributed EXPRESSION statement is not, and reports
/// the attribute's line -- declared rather than guessed at.
fn statement_span(stmt: &Stmt) -> Span {
    match stmt {
        Stmt::Local(local) => local.let_token.span,
        Stmt::Macro(mac) => mac.mac.path.span(),
        Stmt::Expr(expr, _) => expr.span(),
        Stmt::Item(_) => stmt.span(),
    }
}

/// Does this statement fail to complete normally, so that a probe after it
/// would be unreachable code?
///
/// [`crate::exits::diverges`] answers a DIFFERENT question -- "would wrapping
/// this operand put the `ret` call after code of type `!`" -- and the two
/// answers part company on exactly one construct: `loop`. There the test is
/// `has_valued_break`, because a loop only YIELDS a value through `break
/// <expr>`; so `loop { if c { break; } }` is "diverging" to `exits` even though
/// it plainly completes as a statement -- the `break` leaves it and the next
/// statement runs. Reusing that predicate here dropped the LINE of every
/// `loop`-with-a-plain-`break` and of the statement's own row -- a §3.1
/// violation found in review (fix round 1, I1).
///
/// So `loop` is answered here -- it diverges only when NO `break` targets it,
/// valued or not -- and everything else still delegates. What still delegates
/// and is therefore still wrong is a `loop { break; }` buried inside a
/// COMPOSITE (`unsafe { loop { break; } }`, a `match` all of whose arms are
/// such a loop): `exits::diverges` recurses with its own rule. That costs those
/// statements their LINE and never costs a build, and is declared rather than
/// fixed by duplicating `exits`'s composite walk here.
fn stmt_diverges(expr: &Expr) -> bool {
    match expr {
        Expr::Paren(inner) => stmt_diverges(&inner.expr),
        Expr::Group(inner) => stmt_diverges(&inner.expr),
        Expr::Loop(l) => !has_break(l),
        other => exits::diverges(other),
    }
}

/// Does any `break` -- with a value or without -- leave THIS loop?
fn has_break(l: &ExprLoop) -> bool {
    let mut walk = BreakWalk {
        label: l.label.as_ref().map(|l| &l.name),
        nested: 0,
        found: false,
    };
    walk.visit_block(&l.body);
    walk.found
}

/// The walk `has_break` runs. A sibling of `exits.rs`'s `BreakWalk` and not a
/// reuse of it: that one requires `break <expr>` and counts only `loop` as a
/// nesting level, and both differences are wrong for this question. An
/// unlabelled `break` targets the innermost `loop`/`while`/`for`, so all three
/// count here.
struct BreakWalk<'a> {
    label: Option<&'a Lifetime>,
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
        if self.targets_this_loop(node) {
            self.found = true;
        }
        syn::visit::visit_expr_break(self, node);
    }

    fn visit_expr_loop(&mut self, node: &'ast ExprLoop) {
        self.nested += 1;
        syn::visit::visit_expr_loop(self, node);
        self.nested -= 1;
    }

    fn visit_expr_while(&mut self, node: &'ast ExprWhile) {
        self.nested += 1;
        syn::visit::visit_expr_while(self, node);
        self.nested -= 1;
    }

    fn visit_expr_for_loop(&mut self, node: &'ast ExprForLoop) {
        self.nested += 1;
        syn::visit::visit_expr_for_loop(self, node);
        self.nested -= 1;
    }

    // A `break` cannot cross any of these, so neither does the walk.
    fn visit_expr_closure(&mut self, _: &'ast ExprClosure) {}
    fn visit_expr_async(&mut self, _: &'ast ExprAsync) {}
    fn visit_expr_const(&mut self, _: &'ast ExprConst) {}
    fn visit_item(&mut self, _: &'ast Item) {}
}

/// Can `cfg` REMOVE this statement from the build?
///
/// Only `#[cfg]` and `#[cfg_attr]` can, and the probe is spliced AFTER the
/// statement, so it survives a strip that takes the statement (and its
/// bindings) away. Every other attribute -- `#[allow(..)]`, `#[rustfmt::skip]`,
/// a doc comment -- leaves the statement in the build and takes its LINE
/// normally. Fix round 1 (I2): this used to be "the statement's first byte is
/// `#`", which cost `#[allow(unused)] let c = 3;` its row and its `c` delta,
/// and `#[allow]` on a statement is far more common than `#[cfg]`.
fn is_conditionally_compiled(stmt: &Stmt) -> bool {
    let attrs = match stmt {
        Stmt::Local(local) => local.attrs.as_slice(),
        Stmt::Macro(mac) => mac.attrs.as_slice(),
        Stmt::Expr(expr, _) => expr_attrs(expr),
        // Never probed anyway -- `statement_end` declines an item statement
        // before its attributes could matter.
        Stmt::Item(_) => return false,
    };
    attrs
        .iter()
        .any(|a| a.path().is_ident("cfg") || a.path().is_ident("cfg_attr"))
}

/// One expression's own outer attributes.
///
/// `syn` gives every `Expr` variant but `Verbatim` an `attrs` field and no way
/// to reach it generically, so this is the match. The catch-all is required --
/// `syn::Expr` is `#[non_exhaustive]` -- and answers "no attributes", which is
/// what a variant this crate has never seen would have to be assumed to have;
/// the cost of being wrong is one probe on a statement a `cfg` could strip.
fn expr_attrs(expr: &Expr) -> &[Attribute] {
    match expr {
        Expr::Array(e) => &e.attrs,
        Expr::Assign(e) => &e.attrs,
        Expr::Async(e) => &e.attrs,
        Expr::Await(e) => &e.attrs,
        Expr::Binary(e) => &e.attrs,
        Expr::Block(e) => &e.attrs,
        Expr::Break(e) => &e.attrs,
        Expr::Call(e) => &e.attrs,
        Expr::Cast(e) => &e.attrs,
        Expr::Closure(e) => &e.attrs,
        Expr::Const(e) => &e.attrs,
        Expr::Continue(e) => &e.attrs,
        Expr::Field(e) => &e.attrs,
        Expr::ForLoop(e) => &e.attrs,
        Expr::Group(e) => &e.attrs,
        Expr::If(e) => &e.attrs,
        Expr::Index(e) => &e.attrs,
        Expr::Infer(e) => &e.attrs,
        Expr::Let(e) => &e.attrs,
        Expr::Lit(e) => &e.attrs,
        Expr::Loop(e) => &e.attrs,
        Expr::Macro(e) => &e.attrs,
        Expr::Match(e) => &e.attrs,
        Expr::MethodCall(e) => &e.attrs,
        Expr::Paren(e) => &e.attrs,
        Expr::Path(e) => &e.attrs,
        Expr::Range(e) => &e.attrs,
        Expr::Reference(e) => &e.attrs,
        Expr::Repeat(e) => &e.attrs,
        Expr::Return(e) => &e.attrs,
        Expr::Struct(e) => &e.attrs,
        Expr::Try(e) => &e.attrs,
        Expr::TryBlock(e) => &e.attrs,
        Expr::Tuple(e) => &e.attrs,
        Expr::Unary(e) => &e.attrs,
        Expr::Unsafe(e) => &e.attrs,
        Expr::While(e) => &e.attrs,
        Expr::Yield(e) => &e.attrs,
        _ => &[],
    }
}

/// The deltas of one statement (design §3.2).
fn statement_deltas(stmt: &Stmt) -> Vec<String> {
    match stmt {
        // `let x;` writes nothing HERE -- `x` appears at its first assignment.
        Stmt::Local(local) if local.init.is_some() => binding_names(&local.pat),
        Stmt::Expr(expr, Some(_)) => assign_target(expr).into_iter().collect(),
        _ => Vec::new(),
    }
}

/// `x = e;` and `x += e;` where the left-hand side is a bare local identifier.
///
/// A place write (`*p = e`, `a.b = e`, `v[i] = e`) answers `None` and the
/// statement mints an empty LINE: design §3.2 declares place writes out of the
/// deltas, and the row still says the line ran.
///
/// `syn` 2 has no `ExprAssignOp` -- a compound assignment is an `ExprBinary`
/// whose operator is one of the ten `*Assign` variants -- so both spellings are
/// read off `Expr::Binary` here.
fn assign_target(expr: &Expr) -> Option<String> {
    let left = match expr {
        Expr::Assign(assign) => &*assign.left,
        Expr::Binary(binary) if is_assign_op(binary.op) => &*binary.left,
        _ => return None,
    };
    let Expr::Path(path) = left else {
        return None;
    };
    if path.qself.is_some() || path.path.leading_colon.is_some() || path.path.segments.len() != 1 {
        return None;
    }
    let segment = &path.path.segments[0];
    if !segment.arguments.is_none() {
        return None;
    }
    let name = segment.ident.to_string();
    is_binding_name(&name).then_some(name)
}

fn is_assign_op(op: BinOp) -> bool {
    matches!(
        op,
        BinOp::AddAssign(_)
            | BinOp::SubAssign(_)
            | BinOp::MulAssign(_)
            | BinOp::DivAssign(_)
            | BinOp::RemAssign(_)
            | BinOp::BitXorAssign(_)
            | BinOp::BitAndAssign(_)
            | BinOp::BitOrAssign(_)
            | BinOp::ShlAssign(_)
            | BinOp::ShrAssign(_)
    )
}

/// Every identifier a pattern binds, in source order, once each.
///
/// [`crate::arms::bound_names`] is the walk -- the same one the escape test
/// uses, so a destructuring pattern is read the same way in both places. Two
/// filters sit on top of it here and nowhere there, because a delta becomes
/// EMITTED CODE and an escape-test name does not:
///
/// * an or-pattern binds the same name in every alternative (`Ok(v) | Err(v)`),
///   and one binding must be one delta;
/// * a name that is not a plausible binding is a path pattern (see the module
///   docs).
fn binding_names(pat: &Pat) -> Vec<String> {
    let mut names = Vec::new();
    bound_names(pat, &mut names);
    names.retain(|name| is_binding_name(name));
    let mut seen: Vec<String> = Vec::with_capacity(names.len());
    for name in names {
        if !seen.contains(&name) {
            seen.push(name);
        }
    }
    seen
}

/// Does this identifier read as a binding rather than as a unit variant or a
/// constant? Rust's own convention decides, because `syn` cannot: `None` and
/// `other` are both `Pat::Ident` and only name resolution separates them.
fn is_binding_name(name: &str) -> bool {
    name.chars()
        .next()
        .is_some_and(|c| c == '_' || c.is_lowercase())
}

/// The bindings of every `let` in an `if`/`while` condition.
///
/// Edition 2021 admits exactly one -- the condition IS the `let` -- so the walk
/// through `&&` and parentheses is what a 2024 let-chain would need and costs
/// nothing until then. Anything else in the condition (a nested `if let` inside
/// a call, say) is a different scope and is not collected.
fn let_bindings(cond: &Expr) -> Vec<String> {
    let mut names = Vec::new();
    collect_let_bindings(cond, &mut names);
    let mut seen: Vec<String> = Vec::with_capacity(names.len());
    for name in names {
        if !seen.contains(&name) {
            seen.push(name);
        }
    }
    seen
}

fn collect_let_bindings(cond: &Expr, out: &mut Vec<String>) {
    match cond {
        Expr::Let(let_expr) => out.extend(binding_names(&let_expr.pat)),
        Expr::Paren(paren) => collect_let_bindings(&paren.expr, out),
        Expr::Binary(binary) if matches!(binary.op, BinOp::And(_)) => {
            collect_let_bindings(&binary.left, out);
            collect_let_bindings(&binary.right, out);
        }
        _ => {}
    }
}
