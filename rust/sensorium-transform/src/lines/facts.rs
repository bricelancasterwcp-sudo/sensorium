//! The statement facts the LINE walk asks about: pure questions over `syn`
//! nodes, no state and no splices.
//!
//! Each one answers something the walk in [`crate::lines`] needs before it can
//! decide where a LINE probe goes and what it reports -- where a statement's
//! span starts once its attributes are skipped, whether the statement diverges,
//! whether `cfg` may delete it, which names it binds or reassigns. Nothing here
//! reads or writes the walk's state, which is why it can be read on its own.
//!
//! Split out of `lines.rs` at 762 of its 800 lines. Seven of these are
//! `pub(super)` because the parent module calls them; the other seven are
//! private, called only by their siblings here.

use std::sync::atomic::{AtomicUsize, Ordering};

use proc_macro2::Span;
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{
    Attribute, BinOp, Block, Expr, ExprAsync, ExprBreak, ExprClosure, ExprConst, ExprForLoop,
    ExprIf, ExprLoop, ExprWhile, Item, Lifetime, Pat, Stmt,
};

use crate::arms::bound_names;
use crate::exits;

/// Is this expression one whose statement form ends in `}`?
pub(super) fn is_block_like(expr: &Expr) -> bool {
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
pub(super) fn statement_span(stmt: &Stmt) -> Span {
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
pub(super) fn stmt_diverges(expr: &Expr) -> bool {
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
pub(super) fn is_conditionally_compiled(stmt: &Stmt) -> bool {
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

/// How many `Expr` variants [`expr_attrs`] has met and does not enumerate.
///
/// Zero, for as long as this crate's `syn` defines no variant the match above
/// has not been taught. It is a counter rather than only an `eprintln!`
/// because "it stayed at zero" and "it fired" are both claims a test can
/// check, and a line on stderr is neither.
static UNENUMERATED_EXPRS: AtomicUsize = AtomicUsize::new(0);

/// The line [`unenumerated`] is to print, or `None` because it has printed one
/// already.
///
/// Counts every call and reports on the 0 -> 1 transition only. The walk
/// visits every statement of every file of a unit, so a variant this match
/// does not enumerate would otherwise print one line per OCCURRENCE and bury
/// the build log the message exists to be visible in. The count keeps rising
/// either way, so "how many" is still answerable; only the shouting is capped.
///
/// Separated from the printing so that "it reports once" is a claim a test can
/// check, which a line on stderr is not.
fn unenumerated_report(at: Span) -> Option<String> {
    if UNENUMERATED_EXPRS.fetch_add(1, Ordering::Relaxed) > 0 {
        return None;
    }
    let start = at.start();
    Some(format!(
        "sensorium: sensorium-transform does not enumerate this syn::Expr \
         variant (line {}, column {}); a `#[cfg]` on that statement was not \
         seen, and its LINE probe may not survive the strip",
        start.line, start.column
    ))
}

/// The loud half of [`expr_attrs`]'s catch-all.
///
/// Says on stderr that a `#[cfg]` may have gone unseen, counts that it
/// happened, and answers "no attributes" anyway: the cost of being wrong is
/// one LINE probe on a statement a `cfg` could strip, which is not worth
/// failing somebody's build over. The old behaviour was the same answer with
/// nothing said (`docs/CARRIED-DEBT-ARCHIVE-2.md`, "any future `syn` variant
/// in `expr_attrs`").
fn unenumerated(at: Span) -> &'static [Attribute] {
    if let Some(line) = unenumerated_report(at) {
        eprintln!("{line}");
    }
    &[]
}

/// One expression's own outer attributes.
///
/// `syn` gives every `Expr` variant but `Verbatim` an `attrs` field and no way
/// to reach it generically, so this is the match. The catch-all is required --
/// `syn::Expr` is `#[non_exhaustive]` -- and answers "no attributes", which is
/// what a variant this crate has never seen would have to be assumed to have;
/// the cost of being wrong is one probe on a statement a `cfg` could strip.
///
/// It no longer answers that in SILENCE. `Verbatim` is enumerated by name,
/// because "no attributes" is the truth for it rather than an assumption;
/// everything else reaching the catch-all is a variant `syn` added after this
/// match was written, and [`unenumerated`] says so on stderr and counts
/// itself.
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
        Expr::RawAddr(e) => &e.attrs,
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
        // The one variant with no `attrs` field at all: `syn` parked tokens it
        // could not parse, so there is nothing an attribute could be hiding in.
        Expr::Verbatim(_) => &[],
        // KNOWN-SURVIVING MUTANT, on purpose: no test can reach this arm.
        // `syn::Expr` is `#[non_exhaustive]`, so no test can construct a
        // variant that is neither matched above nor `Verbatim`, and restoring
        // the old `_ => &[]` here leaves the whole suite green. What IS fenced
        // is the message itself -- `unenumerated_report`'s own test pins its
        // wording, its counting and its report-once rule -- and the
        // `Verbatim` arm above, whose removal reddens that test. The day
        // `syn` grows a variant, this arm is what turns silence into a line.
        other => unenumerated(other.span()),
    }
}

/// The deltas of one statement (design §3.2).
pub(super) fn statement_deltas(stmt: &Stmt) -> Vec<String> {
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

/// The names a block-like statement unbinds on completion (design §5.2), in
/// source order, each once: its own head pattern's names (`for`/`if let`/
/// `while let`/each `match` arm's pattern, via [`binding_names`]/
/// [`let_bindings`]) and every `Stmt::Local` pattern in each of its DIRECT
/// blocks, whichever comes first in the source.
///
/// [`statement_deltas`]'s twin, and the reason it is a separate walk: a delta
/// is what a statement WROTE and an unbind is what its scope TOOK WITH IT, and
/// only the second can name a binding the statement itself never touched.
///
/// # What it declines, and why
///
/// * **A nested block-like statement's blocks.** That statement has a
///   completion row of its own and unbinds its own names there; collecting
///   them here too would say each name died twice, at two different sites.
/// * **A closure's or `async` block's `let`s.** The LINE walk stops at both
///   ([`crate::lines`]'s `visit_expr_closure`/`visit_expr_async`), so no probe
///   ever bound those names -- and design §5.2 is explicit that a row saying a
///   name went out of scope where none came in is a row that invents. The walk
///   here never descends into an expression at all, so this falls out rather
///   than being tested for.
/// * **An `Expr::Async` or `Expr::Const` STATEMENT**, for the same reason read
///   from the other side: it is block-like, so it takes a LINE, but nothing
///   inside it was ever probed. Its list is empty.
/// * **A `cfg`'d `let`.** [`is_conditionally_compiled`] declines its delta and
///   declines its unbind, symmetrically: `cfg` may take the statement out of
///   the build, and a name that never entered may not be said to leave.
/// * **A name [`is_binding_name`] rejects**, via the two collectors -- `None`
///   in `match o { None => {} }` is a path pattern and binds nothing.
///
/// Empty for an expression that is not block-like, so the caller may ask about
/// any `Stmt::Expr` and is not the one holding the `is_block_like` list.
///
/// # The order
///
/// SOURCE order, which is what §5.2's lead clause says; its bullets happen to
/// list the inner `let`s first, and where the two readings part -- a `match`
/// arm, whose pattern precedes its body -- the lead clause governs (ruling
/// P7). `corpus/rust/focus_block_let` pins `unbound:n,big` on that shape and
/// `tests/golden_focus/focus_unbound_match` pins the same pair in the bytes.
pub(super) fn unbound_of(expr: &Expr) -> Vec<String> {
    let mut names = Vec::new();
    match expr {
        Expr::Block(e) => block_lets(&e.block, &mut names),
        Expr::Unsafe(e) => block_lets(&e.block, &mut names),
        Expr::TryBlock(e) => block_lets(&e.block, &mut names),
        Expr::Loop(e) => block_lets(&e.body, &mut names),
        Expr::If(e) => if_scope(e, &mut names),
        Expr::While(e) => {
            names.extend(let_bindings(&e.cond));
            block_lets(&e.body, &mut names);
        }
        Expr::ForLoop(e) => {
            names.extend(binding_names(&e.pat));
            block_lets(&e.body, &mut names);
        }
        Expr::Match(e) => {
            for arm in &e.arms {
                names.extend(binding_names(&arm.pat));
                // A bare-expression arm body holds no statements, so there is
                // nothing there for a `Stmt::Local` rule to find. The block the
                // LINE walk WRAPS such a body in (amendment A1) adds only the
                // probe, never a `let`.
                if let Expr::Block(body) = &*arm.body {
                    block_lets(&body.block, &mut names);
                }
            }
        }
        // `Expr::Async` and `Expr::Const` are block-like and unbind nothing;
        // everything else is not block-like and unbinds nothing either.
        _ => {}
    }
    once_each(names)
}

/// An `if`'s own scope: the condition's `let` bindings, then the `then`
/// block's `let`s, then the `else` branch's.
///
/// An `else if` is an `Expr::If` sitting in `else_branch`, which is itself
/// block-like -- so this does not descend into it. Its head pattern's names
/// and its body's `let`s are therefore unbound by NO row, because an `else if`
/// is not a statement and has no completion row of its own. That is a stated
/// gap rather than a row invented at the outer `if`'s site, which is a
/// different scope ending at a different moment.
fn if_scope(node: &ExprIf, out: &mut Vec<String>) {
    out.extend(let_bindings(&node.cond));
    block_lets(&node.then_branch, out);
    if let Some((_, otherwise)) = &node.else_branch {
        if let Expr::Block(e) = &**otherwise {
            block_lets(&e.block, out);
        }
    }
}

/// The names the `let` statements of ONE block bind, in source order.
///
/// Direct statements only: this never recurses, which is what makes "a nested
/// block-like statement unbinds its own" a fact about this function rather
/// than a rule applied on top of it. A `let`-`else` is a `Stmt::Local` like
/// any other and binds like one. A `let` with no initialiser is here too --
/// unlike [`statement_deltas`], which declines it because a DELTA there would
/// borrow a binding rustc knows is uninitialised (E0381); an unbind names the
/// binding and never reads it, so the same guard would only lose the row for
/// `{ let x; x = 1; }`.
fn block_lets(block: &Block, out: &mut Vec<String>) {
    for stmt in &block.stmts {
        if let Stmt::Local(local) = stmt {
            if !is_conditionally_compiled(stmt) {
                out.extend(binding_names(&local.pat));
            }
        }
    }
}

/// One binding is one entry, at the position of its FIRST mention.
///
/// The same de-duplication [`binding_names`] and [`let_bindings`] each need --
/// an or-pattern binds one name in every alternative, and a name bound in both
/// a head pattern and an inner `let` is one name that ends once.
fn once_each(names: Vec<String>) -> Vec<String> {
    let mut seen: Vec<String> = Vec::with_capacity(names.len());
    for name in names {
        if !seen.contains(&name) {
            seen.push(name);
        }
    }
    seen
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
pub(super) fn binding_names(pat: &Pat) -> Vec<String> {
    let mut names = Vec::new();
    bound_names(pat, &mut names);
    names.retain(|name| is_binding_name(name));
    once_each(names)
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
pub(super) fn let_bindings(cond: &Expr) -> Vec<String> {
    let mut names = Vec::new();
    collect_let_bindings(cond, &mut names);
    once_each(names)
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

#[cfg(test)]
mod tests {
    use super::*;

    fn stmt(source: &str) -> Stmt {
        syn::parse_str(source).expect("a statement")
    }

    /// [`unbound_of`] reads an EXPRESSION; the rule is about STATEMENTS, and
    /// every fixture below reads as one. A block-like statement is a
    /// `Stmt::Expr` with or without a `;` and the rule keys on neither.
    fn unbound(source: &str) -> Vec<String> {
        match stmt(source) {
            Stmt::Expr(expr, _) => unbound_of(&expr),
            _ => panic!("not an expression statement: {source}"),
        }
    }

    /// [`unbound`]'s sibling for the two shapes that cannot be SPELLED as a
    /// statement: `const { .. }` at statement position parses as a `const`
    /// ITEM (`syn`, and rustc, resolve the ambiguity that way), and `async
    /// { .. }` is kept beside it so the pair reads together.
    fn unbound_expr(source: &str) -> Vec<String> {
        unbound_of(&syn::parse_str::<Expr>(source).expect("an expression"))
    }

    /// A plain block, and the direct-blocks-only rule: the nested `if` is a
    /// block-like STATEMENT and unbinds its own `y` on its own row.
    #[test]
    fn a_block_unbinds_its_direct_lets_and_leaves_a_nested_statement_its_own() {
        assert_eq!(unbound("{ let x = 2; let y = 3; }"), ["x", "y"]);
        assert_eq!(unbound("{ let x = 2; if c { let y = 3; } }"), ["x"]);
        assert_eq!(unbound("if c { let y = 3; }"), ["y"]);
        assert_eq!(unbound("{ }"), Vec::<String>::new());
    }

    /// `unsafe`, `loop` and a `try` block are the block-likes with no head
    /// pattern: their body's `let`s and nothing else.
    #[test]
    fn the_headless_block_likes_unbind_their_bodys_lets() {
        assert_eq!(unbound("unsafe { let a = 1; }"), ["a"]);
        assert_eq!(unbound("loop { let a = 1; break; }"), ["a"]);
        assert_eq!(unbound("try { let a = 1; }"), ["a"]);
    }

    /// Every head pattern, each with a body `let` after it, so the SOURCE
    /// ORDER is visible in each answer (ruling P7): the head comes first.
    #[test]
    fn a_head_pattern_is_unbound_before_the_lets_of_the_body_it_opened() {
        assert_eq!(unbound("for item in v { let seen = 1; }"), ["item", "seen"]);
        assert_eq!(
            unbound("if let Some(first) = v.first() { let seen = 1; }"),
            ["first", "seen"]
        );
        assert_eq!(
            unbound("while let Some(next) = it.next() { let seen = 1; }"),
            ["next", "seen"]
        );
    }

    /// A `match` is the shape design §5.2's bullets and its lead clause
    /// disagree about, and the lead clause governs: the arm's pattern is
    /// written before the arm body's `let`, so it is listed before it. Each
    /// arm contributes in turn, and an arm that binds nothing contributes
    /// nothing -- `None` is a path pattern, not a binding.
    #[test]
    fn a_match_unbinds_arm_by_arm_pattern_before_body() {
        assert_eq!(
            unbound("match n { n if n > 1 => { let big = n; } _ => {} }"),
            ["n", "big"]
        );
        assert_eq!(
            unbound("match o { Some(a) => { let p = 1; } None => { let q = 2; } }"),
            ["a", "p", "q"]
        );
        // A bare-expression arm body holds no statements to find.
        assert_eq!(unbound("match o { Some(a) => a * 2, None => 0 }"), ["a"]);
    }

    /// An `if`'s whole scope: the condition's `let`s, the `then` block's and
    /// the `else` block's. An `else if` is a nested block-like and is NOT
    /// descended into -- its own names are unbound by no row at all, because
    /// an `else if` is not a statement (declared in `if_scope`'s docs).
    #[test]
    fn an_if_reaches_both_branches_and_stops_at_an_else_if() {
        assert_eq!(
            unbound("if let Some(a) = o { let p = 1; } else { let q = 2; }"),
            ["a", "p", "q"]
        );
        assert_eq!(
            unbound("if c { let p = 1; } else if d { let q = 2; }"),
            ["p"]
        );
    }

    /// The symmetric rule: `cfg` may take the statement out of the build, so
    /// the name it would have bound is neither a delta nor an unbind. Its
    /// neighbour is unbound normally, which is what says the filter is narrow.
    #[test]
    fn a_cfg_stripped_let_is_not_unbound() {
        assert_eq!(unbound("{ #[cfg(any())] let a = 1; let b = 2; }"), ["b"]);
        assert_eq!(
            unbound("{ #[allow(unused)] let a = 1; }"),
            ["a"],
            "only `cfg` and `cfg_attr` can remove the statement"
        );
    }

    /// One binding is one entry, at its first mention: a name bound in BOTH a
    /// head pattern and an inner `let` ends once, and an or-pattern's repeated
    /// name is one name.
    #[test]
    fn a_name_bound_twice_is_unbound_once() {
        assert_eq!(unbound("for x in v { let x = 1; }"), ["x"]);
        assert_eq!(unbound("match r { Ok(v) | Err(v) => { } }"), ["v"]);
    }

    /// Design §5.2's "a row that said a name went out of scope where none came
    /// in would be a row that invents", read three ways. A closure's and an
    /// `async` block's `let`s were never probed, and an `async` or `const`
    /// STATEMENT unbinds nothing at all.
    #[test]
    fn nothing_a_probe_never_bound_is_unbound() {
        assert_eq!(
            unbound("{ let f = |x: i32| { let inner = x; }; }"),
            ["f"],
            "the closure's `inner` was never bound by a probe"
        );
        assert_eq!(unbound_expr("async { let a = 1; }"), Vec::<String>::new());
        assert_eq!(unbound_expr("const { let a = 1; }"), Vec::<String>::new());
    }

    /// A `let`-`else` is a `Stmt::Local` and binds like a `let`; a `let` with
    /// no initialiser is bound at its first assignment and popped here too.
    #[test]
    fn a_let_else_and_a_deferred_let_both_bind_for_the_purpose_of_unbinding() {
        assert_eq!(unbound("{ let Some(a) = o else { return; }; }"), ["a"]);
        assert_eq!(unbound("{ let a; a = 1; }"), ["a"]);
    }

    /// The caller asks about any `Stmt::Expr` and is not the one holding the
    /// `is_block_like` list, so an expression that is not block-like answers
    /// with an empty list rather than with a panic.
    #[test]
    fn an_expression_that_is_not_block_like_unbinds_nothing() {
        assert_eq!(unbound("f(1);"), Vec::<String>::new());
        assert_eq!(unbound("a += 1;"), Vec::<String>::new());
    }

    /// The rule `expr_attrs` serves: `#[cfg]` can delete the statement and
    /// `#[allow]` cannot, and both are read off the EXPRESSION.
    #[test]
    fn a_cfg_on_an_expression_statement_is_seen_and_an_allow_is_not() {
        assert!(is_conditionally_compiled(&stmt("#[cfg(unix)] foo();")));
        assert!(is_conditionally_compiled(&stmt(
            "#[cfg_attr(test, allow(unused))] foo();"
        )));
        assert!(!is_conditionally_compiled(&stmt("#[allow(unused)] foo();")));
    }

    /// The one arm no `syn` variant can reach today, reached by hand.
    ///
    /// ONE test, because [`UNENUMERATED_EXPRS`] is process-global and this is
    /// the only test that touches it: split in two, the two halves would race
    /// each other for the 0 -> 1 transition.
    #[test]
    fn the_catch_all_reports_itself_once_and_verbatim_is_not_the_catch_all() {
        assert_eq!(
            UNENUMERATED_EXPRS.load(Ordering::Relaxed),
            0,
            "this test owns the counter: nothing else may have bumped it"
        );

        // `Verbatim` is answered by name, so it must not count.
        let verbatim = Expr::Verbatim(proc_macro2::TokenStream::new());
        assert!(expr_attrs(&verbatim).is_empty());
        assert_eq!(
            UNENUMERATED_EXPRS.load(Ordering::Relaxed),
            0,
            "`Expr::Verbatim` is answered by name, not fallen through"
        );

        // The first unknown variant reports, and the message says which
        // position it was at.
        let first = unenumerated_report(Span::call_site());
        let first = first.expect("the first unknown variant must report");
        assert!(
            first.starts_with(
                "sensorium: sensorium-transform does not enumerate this syn::Expr variant"
            ),
            "{first}"
        );
        assert!(first.contains("`#[cfg]`"), "{first}");
        assert_eq!(UNENUMERATED_EXPRS.load(Ordering::Relaxed), 1);

        // The second does NOT report -- the walk visits every statement of
        // every file, so one line per occurrence would bury the build log the
        // message exists to be visible in -- but it is still COUNTED.
        assert_eq!(
            unenumerated_report(Span::call_site()),
            None,
            "the message is once per process, not once per statement"
        );
        assert_eq!(
            UNENUMERATED_EXPRS.load(Ordering::Relaxed),
            2,
            "counting does not stop when reporting does"
        );

        // And the arm's own answer is unchanged either way.
        assert!(unenumerated(Span::call_site()).is_empty());
        assert_eq!(UNENUMERATED_EXPRS.load(Ordering::Relaxed), 3);
    }
}
