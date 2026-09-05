//! `Err(..) =>` arms and `if let Err(..)` bodies: how each one is classified,
//! and what the classification writes (design R2).
//!
//! The probe goes at the arm's ENTRY, as a statement, so that what the arm
//! evaluates to is untouched:
//!
//! ```ignore
//! Err(e) => { ::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, <site>,
//!     ::sensorium_rt::HOW_ARM_PROPAGATE,
//!     || { use ::sensorium_rt::probe::*; (&&Probe(&e)).err_cap_value() }); <body> }
//! ```
//!
//! A block body takes the statement after its `{`; an expression body is
//! wrapped in a block whose value is that expression. Either way the line count
//! is unchanged, which is the whole point of the splicer.
//!
//! # The four classes, and why the order they are tested in is the rule
//!
//! Tested in this order, first match wins:
//!
//! 1. **PROPAGATE** -- the body holds a `?` at its own closure depth, a
//!    `return Err(..)`, or its tail is `Err(..)`. The error leaves the frame, so
//!    the arm opens a RAISE. Tested FIRST because `Err(e) => Err(e)` also
//!    mentions `e` outside a borrow and would otherwise read as ESCAPED, which
//!    would be true of the letter and false of the fact.
//! 2. **PANIC** -- one of the four DIVERGING macros (`panic!`, `unreachable!`,
//!    `todo!`, `unimplemented!`) at the body's own depth. Such an arm gets NO
//!    probe at all: the panic hook records the panic, and a statement in front
//!    of the `panic!` would move its own COLUMN, which endpoint E7 measures.
//!    `assert!` is deliberately not in the set (ruling, 2026-09-04) -- an assert
//!    may pass, and an arm that only asserts still handles its error.
//! 3. **ESCAPED** -- the pattern binds a name and that name appears anywhere
//!    other than the two uses design R2 calls provable: a format-family macro's
//!    argument, and a shared borrow `&e`. Writes `arm_ambiguous`, which is
//!    HANDLED-class but never a SWALLOWED candidate.
//! 4. **HANDLED** -- everything else. This is the only class that can become a
//!    SWALLOWED verdict, which is why 3 is deliberately generous: a false
//!    ESCAPED costs one AMBIGUOUS, a false HANDLED costs a false accusation
//!    (endpoint E6's whole subject).
//!
//! # What is NOT an `Err` arm here
//!
//! An or-pattern (`Err(A) | Err(B) =>`), a `while let Err(..)`, a `let .. else`
//! and a `matches!(x, Err(_))` are none of them classified: they are design
//! R16's named blind spots, and an `Err` that passes through one reads
//! AMBIGUOUS with no record, which is the designed default.

use proc_macro2::{Ident, Spacing, TokenStream, TokenTree};
use syn::spanned::Spanned;
use syn::visit::Visit;
use syn::{Block, Expr, ExprPath, ExprReturn, Macro, Pat, Stmt};

use crate::errflow::How;
use crate::names::line_of;
use crate::splice::{arm_probe_fragment, scope_open_fragment, Kind, SCOPE_CLOSE};
use crate::visit::Ctx;

/// The macros whose argument list is a provable SHARED BORROW of what it names.
///
/// `format_args!` -- which every one of these expands through -- takes each
/// argument by reference, so an argument that is exactly `e` cannot escape
/// through it. The `log`/`tracing` five are here because they are the other
/// spelling of "print the error and carry on", which is the shape design R2's
/// HANDLED class exists for.
///
/// Being ON this list is what makes an arm a SWALLOWED candidate, so the list
/// is short on purpose: a workspace macro that happened to be called `debug!`
/// and stored its argument is the cost, and it is bounded by the fact that its
/// argument still has to be the BARE name (see [`format_arg_escapes`]).
const FORMAT_MACROS: [&str; 13] = [
    "format",
    "format_args",
    "print",
    "println",
    "eprint",
    "eprintln",
    "write",
    "writeln",
    "error",
    "warn",
    "info",
    "debug",
    "trace",
];

/// The four macros whose call never returns -- the PANIC classifier's whole
/// set (design R2, ruling of 2026-09-04). `assert!` is not one of them.
const DIVERGING_MACROS: [&str; 4] = ["panic", "unreachable", "todo", "unimplemented"];

/// What a classified arm writes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Class {
    Propagate,
    /// The one class that writes NOTHING.
    Panic,
    Escaped,
    Handled,
}

impl Class {
    /// Which `how` byte, or `None` for the class that is not probed.
    fn how(self) -> Option<How> {
        match self {
            Class::Propagate => Some(How::ArmPropagate),
            Class::Panic => None,
            Class::Escaped => Some(How::ArmAmbiguous),
            Class::Handled => Some(How::ArmHandled),
        }
    }

    /// This class's slot in [`Ctx::arms`], in the order [`crate::Census`]
    /// spells them.
    fn slot(self) -> usize {
        match self {
            Class::Propagate => 0,
            Class::Panic => 1,
            Class::Escaped => 2,
            Class::Handled => 3,
        }
    }
}

/// An arm body, which is an expression, or an `if let` body, which is a block.
/// The classification is identical; only where the probe goes differs.
#[derive(Clone, Copy)]
pub(crate) enum Body<'a> {
    Expr(&'a Expr),
    Block(&'a Block),
}

impl<'a> Body<'a> {
    fn walk<V: Visit<'a>>(self, v: &mut V) {
        match self {
            Body::Expr(e) => v.visit_expr(e),
            Body::Block(b) => v.visit_block(b),
        }
    }

    /// The body's value, when it has one that is a plain expression.
    fn tail(self) -> Option<&'a Expr> {
        match self {
            Body::Expr(e) => tail_expr(e),
            Body::Block(b) => block_tail(b),
        }
    }
}

// ---------------------------------------------------------------------------
// Placing the sites
// ---------------------------------------------------------------------------

impl Ctx<'_> {
    /// Classify one `Err(..)` pattern's body and probe it, or -- for a PANIC
    /// arm -- deliberately leave it alone. A pattern that is not an `Err(..)`
    /// is not an arm this rung sees, and nothing happens.
    pub(crate) fn err_arm(&mut self, pat: &Pat, body: Body<'_>) {
        let Some(inner) = err_payload(pat) else {
            return;
        };
        let mut names = Vec::new();
        bound_names(inner, &mut names);
        let class = classify(body, &names);
        self.arms[class.slot()] += 1;
        let Some(how) = class.how() else {
            // A PANIC arm: the panic hook has it, and a probe here would shift
            // the `panic!`'s own column (endpoint E7).
            return;
        };
        if !self.emit {
            return;
        }
        let span = pat.span();
        let Some(site) = self.mint_err_site(how, line_of(span), span) else {
            return;
        };
        let stmt = arm_probe_fragment(site, how, probe_binding(inner).as_deref());
        self.place_arm_probe(body, stmt);
    }

    /// The probe is a STATEMENT, so it goes inside a block: after the `{` of one
    /// the body already has, or inside one the wrap adds.
    fn place_arm_probe(&mut self, body: Body<'_>, stmt: String) {
        let block = match body {
            Body::Block(b) => Some((&[][..], b)),
            // An unlabelled block body already IS the statement's home. A
            // labelled one is wrapped instead: a `break '<label> <value>` would
            // leave past a statement placed within it, which is the same reason
            // `exits::descend_bare_block` refuses one.
            Body::Expr(Expr::Block(b)) if b.label.is_none() => Some((b.attrs.as_slice(), &b.block)),
            Body::Expr(_) => None,
        };
        if let Some((attrs, block)) = block {
            if let Some(offset) = self.body_offset(attrs, block) {
                self.push(offset, offset, Kind::Guard, stmt);
            }
            return;
        }
        let Body::Expr(expr) = body else {
            unreachable!("a block body took the branch above")
        };
        let span = expr.span();
        let start = self.start_of(span);
        let end = self.end_of(span);
        if !self.source.is_char_boundary(start) || !self.source.is_char_boundary(end) {
            self.fail(span, "arm body offset falls inside a UTF-8 character");
            return;
        }
        self.push(start, start, Kind::ScopeOpen, scope_open_fragment(&stmt));
        self.push(end, end, Kind::ScopeClose, SCOPE_CLOSE.to_owned());
    }
}

// ---------------------------------------------------------------------------
// The pattern
// ---------------------------------------------------------------------------

/// The payload pattern of an `Err(..)`, or `None` when this is not one.
///
/// The path's LAST segment is what is matched, so `Err`, `Result::Err` and
/// `std::result::Result::Err` are one thing. An or-pattern is not matched at
/// all (see the module docs).
fn err_payload(pat: &Pat) -> Option<&Pat> {
    match pat {
        Pat::Paren(p) => err_payload(&p.pat),
        Pat::TupleStruct(t)
            if t.path.segments.last().is_some_and(|s| s.ident == "Err") && t.elems.len() == 1 =>
        {
            t.elems.first()
        }
        _ => None,
    }
}

/// Every name the payload binds, in any position.
///
/// The escape test runs over ALL of them: `Err(MyErr { source })` binds
/// `source`, and a `source` that escapes is an error that escaped whether or
/// not the probe could name it.
fn bound_names(pat: &Pat, out: &mut Vec<String>) {
    struct Walk<'a>(&'a mut Vec<String>);
    impl<'ast> Visit<'ast> for Walk<'_> {
        fn visit_pat_ident(&mut self, node: &'ast syn::PatIdent) {
            self.0.push(node.ident.to_string());
            syn::visit::visit_pat_ident(self, node);
        }
    }
    Walk(out).visit_pat(pat);
}

/// The one name the probe can be handed, when the payload IS a name.
///
/// A destructuring payload (`Err(MyErr(inner))`, `Err(E { .. })`) has no single
/// error value to hand over, so it takes the unbound entry point (design R4)
/// even though its parts are still tested for escape.
fn probe_binding(pat: &Pat) -> Option<String> {
    match pat {
        Pat::Ident(id) if id.subpat.is_none() => Some(id.ident.to_string()),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// The classification
// ---------------------------------------------------------------------------

fn classify(body: Body<'_>, names: &[String]) -> Class {
    let mut depth = DepthWalk::default();
    body.walk(&mut depth);
    if depth.propagates || body.tail().is_some_and(is_err_call) {
        return Class::Propagate;
    }
    if depth.panics {
        return Class::Panic;
    }
    if !names.is_empty() && escapes(body, names) {
        return Class::Escaped;
    }
    Class::Handled
}

/// PROPAGATE and PANIC evidence at the body's OWN closure depth.
///
/// A `?` inside a nested closure returns from that closure, and a `panic!`
/// inside one happens when the closure is called and not here, so the walk
/// stops at every construct whose body is not this arm's code.
#[derive(Default)]
struct DepthWalk {
    propagates: bool,
    panics: bool,
}

impl<'ast> Visit<'ast> for DepthWalk {
    fn visit_expr_try(&mut self, node: &'ast syn::ExprTry) {
        self.propagates = true;
        syn::visit::visit_expr_try(self, node);
    }

    fn visit_expr_return(&mut self, node: &'ast ExprReturn) {
        if node.expr.as_deref().is_some_and(is_err_call) {
            self.propagates = true;
        }
        syn::visit::visit_expr_return(self, node);
    }

    fn visit_macro(&mut self, node: &'ast Macro) {
        if node
            .path
            .segments
            .last()
            .is_some_and(|s| DIVERGING_MACROS.contains(&s.ident.to_string().as_str()))
        {
            self.panics = true;
        }
    }

    fn visit_expr_closure(&mut self, _node: &'ast syn::ExprClosure) {}
    fn visit_expr_async(&mut self, _node: &'ast syn::ExprAsync) {}
    fn visit_expr_const(&mut self, _node: &'ast syn::ExprConst) {}
    fn visit_item(&mut self, _node: &'ast syn::Item) {}
}

/// `Err(..)` as an EXPRESSION: the constructor call, not the pattern.
fn is_err_call(e: &Expr) -> bool {
    match strip(e) {
        Expr::Call(c) => match strip(&c.func) {
            Expr::Path(p) => p.path.segments.last().is_some_and(|s| s.ident == "Err"),
            _ => false,
        },
        _ => false,
    }
}

fn strip(e: &Expr) -> &Expr {
    match e {
        Expr::Paren(p) => strip(&p.expr),
        Expr::Group(g) => strip(&g.expr),
        other => other,
    }
}

fn tail_expr(e: &Expr) -> Option<&Expr> {
    match e {
        Expr::Paren(p) => tail_expr(&p.expr),
        Expr::Group(g) => tail_expr(&g.expr),
        Expr::Block(b) if b.label.is_none() => block_tail(&b.block),
        Expr::Unsafe(u) => block_tail(&u.block),
        other => Some(other),
    }
}

fn block_tail(b: &Block) -> Option<&Expr> {
    match b.stmts.last()? {
        Stmt::Expr(e, None) => tail_expr(e),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// The escape test
// ---------------------------------------------------------------------------

fn escapes(body: Body<'_>, names: &[String]) -> bool {
    let mut walk = EscapeWalk {
        names,
        escaped: false,
    };
    body.walk(&mut walk);
    walk.escaped
}

struct EscapeWalk<'a> {
    names: &'a [String],
    escaped: bool,
}

impl EscapeWalk<'_> {
    fn is_name(&self, e: &Expr) -> bool {
        bare_name(e).is_some_and(|n| self.names.contains(&n))
    }
}

impl<'ast> Visit<'ast> for EscapeWalk<'_> {
    fn visit_expr_path(&mut self, node: &'ast ExprPath) {
        if path_name(node).is_some_and(|n| self.names.contains(&n)) {
            self.escaped = true;
        }
    }

    /// `&e` -- a SHARED borrow of exactly the name -- is design R2's second
    /// provable non-escape: the arm still owns the error afterwards, and a
    /// `&E` cannot be stored past the arm without a lifetime the arm does not
    /// have. `&mut e` is not on that list and is walked like anything else.
    fn visit_expr_reference(&mut self, node: &'ast syn::ExprReference) {
        if node.mutability.is_none() && self.is_name(&node.expr) {
            return;
        }
        syn::visit::visit_expr_reference(self, node);
    }

    /// A macro's tokens are opaque to `syn`, so nothing below would see a name
    /// inside one. A format-family macro's arguments are read (see
    /// [`format_arg_escapes`]); every other macro is treated as an escape the
    /// moment it so much as mentions the name.
    fn visit_macro(&mut self, node: &'ast Macro) {
        let format_family = node
            .path
            .segments
            .last()
            .is_some_and(|s| FORMAT_MACROS.contains(&s.ident.to_string().as_str()));
        if !format_family {
            if tokens_mention(&node.tokens, self.names) {
                self.escaped = true;
            }
            return;
        }
        if format_arg_escapes(&node.tokens, self.names) {
            self.escaped = true;
        }
    }

    /// A nested `fn`, `impl` or `mod` cannot capture the arm's binding, so a
    /// same-named parameter inside one is a different name entirely.
    fn visit_item(&mut self, _node: &'ast syn::Item) {}
}

/// A path expression that is exactly one plain segment: `e`, never `E::e`,
/// `<T>::e` or `::e`.
fn bare_name(e: &Expr) -> Option<String> {
    match strip(e) {
        Expr::Path(p) => path_name(p),
        _ => None,
    }
}

fn path_name(p: &ExprPath) -> Option<String> {
    if p.qself.is_some() || p.path.leading_colon.is_some() || p.path.segments.len() != 1 {
        return None;
    }
    let seg = p.path.segments.first()?;
    seg.arguments.is_none().then(|| seg.ident.to_string())
}

/// Does any argument of a format-family macro use one of the names in a way
/// that is not a shared borrow?
///
/// An argument that is exactly the bare name is safe: `format_args!` takes each
/// of its arguments by reference, so `println!("{}", e)` cannot move `e`. An
/// argument that MENTIONS the name in any other shape -- `take(e)`,
/// `e.to_string()`, `&mut e` -- is put through the ordinary escape walk, and one
/// that does not parse as an expression at all (a `tracing` key-value, say) is
/// an escape by default rather than a guess. A name captured implicitly by the
/// format string (`"{e}"`) is not a token at this level and is never seen, which
/// is correct: that capture is a shared borrow too.
fn format_arg_escapes(tokens: &TokenStream, names: &[String]) -> bool {
    for arg in top_level_args(tokens) {
        let arg = strip_named_argument(arg);
        if !tokens_mention_slice(&arg, names) {
            continue;
        }
        let stream: TokenStream = arg.into_iter().collect();
        let Ok(expr) = syn::parse2::<Expr>(stream) else {
            return true;
        };
        if bare_name(&expr).is_some_and(|n| names.contains(&n)) {
            continue;
        }
        let mut walk = EscapeWalk {
            names,
            escaped: false,
        };
        walk.visit_expr(&expr);
        if walk.escaped {
            return true;
        }
    }
    false
}

/// Split a macro's tokens at its top-level commas. A delimited group is one
/// token tree, so nothing inside brackets is ever split.
fn top_level_args(tokens: &TokenStream) -> Vec<Vec<TokenTree>> {
    let mut out: Vec<Vec<TokenTree>> = vec![Vec::new()];
    for tt in tokens.clone() {
        match &tt {
            TokenTree::Punct(p) if p.as_char() == ',' && p.spacing() == Spacing::Alone => {
                out.push(Vec::new());
            }
            _ => out.last_mut().expect("one group always exists").push(tt),
        }
    }
    out
}

/// `name = <expr>` is a named format argument; the name is the FORMAT's, not
/// the program's, so only what follows the `=` is an expression. `==` is left
/// alone: its first `=` is `Spacing::Joint`.
fn strip_named_argument(arg: Vec<TokenTree>) -> Vec<TokenTree> {
    let named = matches!(
        (arg.first(), arg.get(1)),
        (Some(TokenTree::Ident(_)), Some(TokenTree::Punct(p)))
            if p.as_char() == '=' && p.spacing() == Spacing::Alone
    );
    if named {
        return arg.into_iter().skip(2).collect();
    }
    arg
}

fn tokens_mention(tokens: &TokenStream, names: &[String]) -> bool {
    tokens.clone().into_iter().any(|tt| match tt {
        TokenTree::Ident(id) => mentions(&id, names),
        TokenTree::Group(g) => tokens_mention(&g.stream(), names),
        _ => false,
    })
}

fn tokens_mention_slice(arg: &[TokenTree], names: &[String]) -> bool {
    arg.iter().any(|tt| match tt {
        TokenTree::Ident(id) => mentions(id, names),
        TokenTree::Group(g) => tokens_mention(&g.stream(), names),
        _ => false,
    })
}

fn mentions(id: &Ident, names: &[String]) -> bool {
    names.contains(&id.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn arm(text: &str) -> syn::Arm {
        let expr: syn::ExprMatch = syn::parse_str(&format!("match x {{ {text} }}"))
            .unwrap_or_else(|e| panic!("parsing {text:?}: {e}"));
        expr.arms.into_iter().next().expect("one arm")
    }

    fn class_of(text: &str) -> Option<Class> {
        let a = arm(text);
        let inner = err_payload(&a.pat)?;
        let mut names = Vec::new();
        bound_names(inner, &mut names);
        Some(classify(Body::Expr(&a.body), &names))
    }

    #[test]
    fn propagate_is_a_question_mark_a_return_err_or_an_err_tail() {
        for text in [
            "Err(e) => Err(e),",
            "Err(e) => return Err(e),",
            "Err(_) => { let v = f()?; Ok(v) },",
            "Err(e) => { log(&e); Err(e) },",
            "Err(e) => Err(e.into()),",
            "Err(e) => { if c { return Err(e); } Ok(0) },",
        ] {
            assert_eq!(class_of(text), Some(Class::Propagate), "{text}");
        }
    }

    #[test]
    fn a_question_mark_inside_a_nested_closure_is_not_this_arms() {
        // It returns from the CLOSURE, so the arm handles its error rather
        // than propagating it -- and the name is only borrowed, so HANDLED.
        assert_eq!(
            class_of("Err(_) => { let f = || g()?; drop(f); 0 },"),
            Some(Class::Handled)
        );
    }

    #[test]
    fn panic_is_the_four_diverging_macros_and_assert_is_not_one() {
        for text in [
            "Err(e) => panic!(\"{e}\"),",
            "Err(_) => unreachable!(),",
            "Err(_) => todo!(),",
            "Err(_) => unimplemented!(),",
            "Err(e) => { eprintln!(\"{e}\"); panic!(\"stop\") },",
        ] {
            assert_eq!(class_of(text), Some(Class::Panic), "{text}");
        }
        for text in [
            "Err(_) => { assert!(flag); 0 },",
            "Err(_) => { assert_eq!(a, b); 0 },",
            "Err(_) => { debug_assert!(flag); 0 },",
        ] {
            assert_eq!(class_of(text), Some(Class::Handled), "{text}");
        }
    }

    #[test]
    fn escaped_is_any_use_that_is_not_a_format_argument_or_a_shared_borrow() {
        for text in [
            "Err(e) => { v.push(e); 0 },",
            "Err(e) => { take(e); 0 },",
            "Err(e) => { last = Some(e); 0 },",
            "Err(e) => { let kept = e; drop(kept); 0 },",
            "Err(e) => { s = e.to_string(); 0 },",
            "Err(e) => { f(&mut e); 0 },",
            "Err(e) => { store!(e); 0 },",
            "Err(e) => { println!(\"{}\", consume(e)); 0 },",
            "Err(e) => { assert!(e.is_timeout()); 0 },",
            "Err(MyErr(inner)) => { v.push(inner); 0 },",
        ] {
            assert_eq!(class_of(text), Some(Class::Escaped), "{text}");
        }
    }

    #[test]
    fn handled_is_a_format_argument_a_shared_borrow_or_no_use_at_all() {
        for text in [
            "Err(e) => { println!(\"{e}\"); 0 },",
            "Err(e) => { println!(\"{}\", e); 0 },",
            "Err(e) => { println!(\"{}\", &e); 0 },",
            "Err(e) => { eprintln!(\"failed: {e:?}\"); 0 },",
            "Err(e) => { tracing::error!(\"{}\", e); 0 },",
            "Err(e) => { note(&e); 0 },",
            "Err(_e) => 0,",
            "Err(_) => 0,",
            "Err(..) => 0,",
            "Err(MyErr::Timeout) => 0,",
        ] {
            assert_eq!(class_of(text), Some(Class::Handled), "{text}");
        }
    }

    #[test]
    fn a_pattern_that_is_not_an_err_is_not_an_arm_this_rung_sees() {
        for text in [
            "Ok(v) => v,",
            "_ => 0,",
            "Err(a) | Err(b) => { drop(a); drop(b); 0 },",
            "Some(e) => { v.push(e); 0 },",
        ] {
            assert_eq!(class_of(text), None, "{text}");
        }
    }

    #[test]
    fn the_probe_binding_is_the_payload_only_when_the_payload_is_a_name() {
        for (text, expected) in [
            ("Err(e) => 0,", Some("e")),
            ("Err(ref e) => 0,", Some("e")),
            ("Err(mut e) => 0,", Some("e")),
            ("Err(ref mut e) => 0,", Some("e")),
            ("Err(_) => 0,", None),
            ("Err(..) => 0,", None),
            ("Err(MyErr::Timeout) => 0,", None),
            ("Err(MyErr { .. }) => 0,", None),
            ("Err(MyErr(inner)) => 0,", None),
            ("Err(e @ MyErr::Timeout) => 0,", None),
        ] {
            let a = arm(text);
            let inner = err_payload(&a.pat).expect("an Err payload");
            assert_eq!(probe_binding(inner).as_deref(), expected, "{text}");
        }
    }
}
