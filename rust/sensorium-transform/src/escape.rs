//! The escape test: does an `Err` arm's bound name leave the arm?
//!
//! Split out of [`crate::arms`] in the 2026-09-05 repair slice, unchanged, so
//! that both files stay under the crate's 800-line ceiling. The rule it
//! implements is design R2's ESCAPED class: an arm that binds the error and
//! uses the name anywhere other than a provably non-escaping position writes
//! `arm_ambiguous` and can never become a SWALLOWED verdict.

use proc_macro2::{Ident, Spacing, TokenStream, TokenTree};
use syn::visit::Visit;
use syn::{Expr, ExprPath, Macro};

use crate::arms::{strip, Body};

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

pub(crate) fn escapes(body: Body<'_>, names: &[String]) -> bool {
    let mut walk = EscapeWalk::new(names);
    body.walk(&mut walk);
    walk.escaped
}

struct EscapeWalk<'a> {
    names: &'a [String],
    escaped: bool,
    /// How many `move` closures the walk is currently inside.
    ///
    /// Both exemptions below are arguments about a BORROW that cannot outlive
    /// the arm. A `move` closure breaks that argument outright: it takes the
    /// error by value, and the closure can be spawned, boxed or stored, so
    /// `move || eprintln!("{e}")` is a way of keeping `e`, not a way of
    /// printing it. Inside one, every mention of a bound name escapes --
    /// including one that is only a token of a format string, which is where
    /// implicit capture hides it (the reviewer's three measured
    /// false-HANDLED generators, 2026-09-04).
    ///
    /// A counter rather than a flag, and never reset by a nested plain
    /// closure: a `||` inside a `move ||` borrows from a copy that has already
    /// left the arm.
    moved: usize,
}

impl EscapeWalk<'_> {
    fn new(names: &[String]) -> EscapeWalk<'_> {
        EscapeWalk {
            names,
            escaped: false,
            moved: 0,
        }
    }

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
    ///
    /// Inside a `move` closure the borrow is of the closure's OWN copy, which
    /// the closure took by value: `move || note(&e)` moves `e` out of the arm,
    /// so the exemption does not apply there (see [`EscapeWalk::moved`]).
    fn visit_expr_reference(&mut self, node: &'ast syn::ExprReference) {
        if self.moved == 0 && node.mutability.is_none() && self.is_name(&node.expr) {
            return;
        }
        syn::visit::visit_expr_reference(self, node);
    }

    /// A `move` closure takes what it names BY VALUE, so inside one neither
    /// exemption holds. Everything below is walked with
    /// [`EscapeWalk::moved`] raised.
    fn visit_expr_closure(&mut self, node: &'ast syn::ExprClosure) {
        let takes = usize::from(node.capture.is_some());
        self.moved += takes;
        syn::visit::visit_expr_closure(self, node);
        self.moved -= takes;
    }

    /// `async move { .. }` is the same capture by another spelling -- the
    /// future owns what it named and can be spawned or stored -- so it raises
    /// [`EscapeWalk::moved`] too. A plain `async { .. }` borrows, exactly as a
    /// plain closure does, and keeps both exemptions.
    ///
    /// (An `async move` CLOSURE needs nothing here: `ExprClosure::capture` is
    /// what it sets, and the override above already reads it.)
    fn visit_expr_async(&mut self, node: &'ast syn::ExprAsync) {
        let takes = usize::from(node.capture.is_some());
        self.moved += takes;
        syn::visit::visit_expr_async(self, node);
        self.moved -= takes;
    }

    /// A macro's tokens are opaque to `syn`, so nothing below would see a name
    /// inside one. A format-family macro's arguments are read (see
    /// [`format_arg_escapes`]); every other macro is treated as an escape the
    /// moment it so much as mentions the name.
    fn visit_macro(&mut self, node: &'ast Macro) {
        if self.moved > 0 {
            // Inside a `move` closure there is no exemption to apply, and the
            // name may not be a token at all: `move || println!("{e}")`
            // captures `e` through the format STRING. Literals are read too.
            if tokens_mention_captured(&node.tokens, self.names) {
                self.escaped = true;
            }
            return;
        }
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
/// is correct HERE and only here: outside a `move` closure that capture is a
/// shared borrow. Inside one it is a MOVE, and this function is never reached
/// -- [`EscapeWalk::visit_macro`] reads the whole token stream, literals
/// included, the moment [`EscapeWalk::moved`] is raised.
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
        let mut walk = EscapeWalk::new(names);
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

/// Every mention of a name inside a `move` closure's macro tokens, INCLUDING
/// one that is only part of a string literal.
///
/// `move || println!("{e}")` holds no `e` token at all: the capture is written
/// inside the format string, and it is a capture by VALUE. A whole-word search
/// of each literal is what finds it. The search is deliberately loose -- a
/// literal `"e"` that means something else reads as an escape -- because a
/// false ESCAPED costs one AMBIGUOUS and a false HANDLED costs a false
/// accusation.
fn tokens_mention_captured(tokens: &TokenStream, names: &[String]) -> bool {
    tokens.clone().into_iter().any(|tt| match tt {
        TokenTree::Ident(id) => mentions(&id, names),
        TokenTree::Literal(lit) => literal_mentions(&lit.to_string(), names),
        TokenTree::Group(g) => tokens_mention_captured(&g.stream(), names),
        TokenTree::Punct(_) => false,
    })
}

/// Does this literal's text hold one of the names as a WHOLE word?
fn literal_mentions(text: &str, names: &[String]) -> bool {
    let ident_char = |c: char| c.is_alphanumeric() || c == '_';
    names.iter().any(|name| {
        text.match_indices(name.as_str()).any(|(at, _)| {
            let before = text[..at].chars().next_back();
            let after = text[at + name.len()..].chars().next();
            !before.is_some_and(ident_char) && !after.is_some_and(ident_char)
        })
    })
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
