//! The escape test: does an `Err` arm's bound name leave the arm?
//!
//! Split out of [`crate::arms`] in the 2026-09-05 repair slice so that both
//! files stay under the crate's 800-line ceiling. The rule it implements is
//! design R2's ESCAPED class: an arm that binds the error and uses the name
//! anywhere other than a provably non-escaping position writes `arm_ambiguous`
//! and can never become a SWALLOWED verdict.
//!
//! # The two provable non-escapes, as the borrow repair of 2026-09-05 leaves them
//!
//! 1. A LOGGING macro's BARE argument (`println!("{}", e)`): `format_args!`
//!    takes it by reference and the macro's own value is `()`. See
//!    [`LOGGING_MACROS`].
//! 2. A shared borrow `&<bound name>` that is a DIRECT argument of a call or
//!    method call whose PRODUCT is provably dropped -- an expression statement
//!    ending in `;`, a `let _ = ..;` (typed or not, no `else`), or a logging
//!    macro's argument. See [`EscapeWalk::visit_stmt`].
//!
//! Rule 2 replaced an older one on 2026-09-05 -- the borrow repair, design B1
//! of `docs/superpowers/specs/2026-09-05-sensorium-rung3-borrow-repair-design.md`
//! §2, which closes blind spot 23 (c). A `&e` used to be exempt WHEREVER it
//! stood. That proved the BORROW could not outlive the arm and said nothing
//! about the borrowing call's VALUE: `let (status, body) = map_error(&e, ..);
//! json(status, body)` -- the bloomery clone's `api_v1.rs:396` and `:515` --
//! hands the caller the failure as an HTTP status and body and still read
//! `arm_handled`, which is a false accusation waiting to be printed. "Dropped
//! at the semicolon" is the only syntactic fact that closes the product
//! channel, so it is now the whole of the rule: a `&e` anywhere else walks
//! into the name and escapes.
//!
//! What the repaired rule still cannot see is named rather than hidden (blind
//! spot 23 (d)): a callee that STORES a rendering of what it is handed,
//! through `&self`, a capture or a global -- `self.record(&e);` -- is
//! invisible to a syntactic test, and such an arm still reads `arm_handled`.
//! Closing that channel needs the inter-procedural analysis this recorder does
//! not do, so it is recorded in `rust/HONESTY-BLIND-SPOTS.md` instead.

use proc_macro2::{Ident, Spacing, TokenStream, TokenTree};
use syn::visit::Visit;
use syn::{Expr, ExprPath, Macro, Pat, Stmt};

use crate::arms::{strip, Body};

/// The macros whose bare argument is a provable SHARED BORROW of what it
/// names: the LOGGING family, and only it.
///
/// `format_args!` -- which every one of these expands through -- takes each
/// argument by reference, so an argument that is exactly `e` cannot escape
/// through it. These nine are here because their own value is `()` and their
/// text goes to a sink OUTSIDE the program's values: printing the error and
/// carrying on is exactly the shape design R2's HANDLED class exists for, and
/// design R15's clarification of 2026-09-05 says out loud that such an arm is
/// a true swallow (`corpus/rust/logged_arm`).
///
/// Being ON this list is what makes an arm a SWALLOWED candidate, so the list
/// is short on purpose: a workspace macro that happened to be called `debug!`
/// and stored its argument is the cost, and it is bounded by the fact that its
/// argument still has to be the BARE name (see [`format_arg_escapes`]).
/// Why this is a LIST and not "the format family" (the R2 amendment of
/// 2026-09-05, after endpoint E6' STOPped on `build_memory` at
/// `memory.rs:131` of the bloomery clone). The old exemption was true of the
/// BORROW and silent about the PRODUCT:
///
/// ```ignore
/// Err(e) => Arc::new(MemoryContext {
///     disabled_reason: Some(format!("memory store unreadable: {e}")),
///     store: None,
/// })
/// ```
///
/// takes `e` by reference and still carries a rendering of the failure to
/// every caller, so calling that arm HANDLED made the tool report a frame that
/// had reported its failure as having absorbed it. `format!`, `format_args!`,
/// `write!` and `writeln!` left the exemption for that reason -- and, in fix
/// round 1, so did every OTHER macro: `anyhow!("{e}")`, `bail!`,
/// `format_err!` and any workspace macro expanding through `format_args!`
/// return a value carrying the rendering exactly as `format!` does, and
/// nothing here can tell one from a macro that drops what it is handed.
///
/// The cost is stated in design R16: an arm that renders the error into a
/// local it then drops reads AMBIGUOUS -- the safe direction, since a false
/// ESCAPED costs one AMBIGUOUS and a false HANDLED costs a false accusation.
const LOGGING_MACROS: [&str; 9] = [
    "print", "println", "eprint", "eprintln", "error", "warn", "info", "debug", "trace",
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

    /// `&<bound name>` -- a SHARED borrow of exactly one of the names, with
    /// nothing else around it. `&mut e`, `&&e` and `&e.source` are all false.
    fn is_shared_borrow_of_name(&self, e: &Expr) -> bool {
        matches!(strip(e), Expr::Reference(r) if r.mutability.is_none() && self.is_name(&r.expr))
    }

    /// Walk `f(.., &e, ..)` or `x.f(.., &e, ..)` at a dropped site, exempting
    /// exactly the arguments that are a shared borrow of a bound name. Returns
    /// `false`, having walked nothing, when `e` is not a call at all -- the
    /// caller then walks the statement the ordinary way.
    fn walk_dropped_call(&mut self, e: &Expr) -> bool {
        match strip(e) {
            Expr::Call(c) => {
                self.visit_expr(&c.func);
                for a in &c.args {
                    self.visit_arg(a);
                }
                true
            }
            Expr::MethodCall(m) => {
                self.visit_expr(&m.receiver);
                for a in &m.args {
                    self.visit_arg(a);
                }
                true
            }
            _ => false,
        }
    }

    /// One argument of a dropped call: `&e` is exempt outside a `move`
    /// capture; anything else is walked.
    fn visit_arg(&mut self, a: &Expr) {
        if self.moved == 0 && self.is_shared_borrow_of_name(a) {
            return;
        }
        self.visit_expr(a);
    }
}

impl<'ast> Visit<'ast> for EscapeWalk<'_> {
    fn visit_expr_path(&mut self, node: &'ast ExprPath) {
        if path_name(node).is_some_and(|n| self.names.contains(&n)) {
            self.escaped = true;
        }
    }

    /// The DROPPED call sites, and with them the whole of the shared-borrow
    /// exemption (the borrow repair of 2026-09-05, design B1; see the module
    /// docs). A statement is dropped when it is an expression statement ending
    /// in `;`, or a `let _ = ..;` -- a plain wildcard pattern, with or without
    /// a type ascription, and no `else` block. A call or method call that IS
    /// such a statement may take a shared borrow of a bound name as a DIRECT
    /// argument without escaping it: the borrow cannot outlive the arm, and
    /// the call's product dies at the semicolon, so neither channel carries
    /// the failure out. Everything else in the statement -- the callee, the
    /// receiver, every other argument, and anything nested inside an argument
    /// -- is walked as usual, and a `&e` met anywhere else escapes.
    ///
    /// Inside a `move` closure the borrow is of the closure's OWN copy, which
    /// the closure took by value: `move || { note(&e); }` moves `e` out of the
    /// arm, so the exemption does not apply there (see [`EscapeWalk::moved`]).
    ///
    /// What this cannot see is design B2's residual, blind spot 23 (d): a
    /// callee that stores a rendering of the borrow through a side channel.
    fn visit_stmt(&mut self, node: &'ast Stmt) {
        let dropped: Option<&'ast Expr> = match node {
            Stmt::Expr(e, Some(_)) => Some(e),
            Stmt::Local(l) => match &l.init {
                Some(init) if init.diverge.is_none() && is_wild(&l.pat) => Some(&init.expr),
                _ => None,
            },
            _ => None,
        };
        match dropped {
            Some(e) if self.walk_dropped_call(e) => {}
            _ => syn::visit::visit_stmt(self, node),
        }
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
    /// inside one. A LOGGING macro's arguments are read (see
    /// [`format_arg_escapes`]); every other macro is treated as an escape the
    /// moment it so much as mentions the name, in a token OR in a format
    /// string's placeholder (design R2's amendment of 2026-09-05 and its fix
    /// round 1).
    fn visit_macro(&mut self, node: &'ast Macro) {
        if self.moved > 0 {
            // Inside a `move` closure there is no exemption to apply, and the
            // name may not be a token at all: `move || println!("{e}")`
            // captures `e` through the format STRING. Literals are read too.
            if tokens_mention_deep(&node.tokens, self.names) {
                self.escaped = true;
            }
            return;
        }
        let name = node.path.segments.last().map(|s| s.ident.to_string());
        let name = name.as_deref().unwrap_or("");
        if !LOGGING_MACROS.contains(&name) {
            // Everything that is not a logging macro: ANY mention of the name
            // escapes, and the mention may be implicit -- `format!("{e}")`,
            // `anyhow!("open failed: {e}")` and a workspace `render!("{e}")`
            // hold no `e` token at all, because the name is written inside the
            // format string. So the whole token stream is read, literals
            // included (fix round 1 of the R2 amendment).
            if tokens_mention_deep(&node.tokens, self.names) {
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

/// `_` or `_: T` -- the `let` patterns whose value is dropped by construction.
fn is_wild(p: &Pat) -> bool {
    match p {
        Pat::Wild(_) => true,
        Pat::Type(t) => is_wild(&t.pat),
        _ => false,
    }
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

/// Does any argument of a LOGGING macro use one of the names in a way that is
/// not a shared borrow?
///
/// Only the logging family reaches here: since the R2 amendment of 2026-09-05
/// and its fix round 1, a mention inside ANY other macro escapes outright,
/// because a macro that is not one of the nine may hand the arm the rendered
/// text (`format!`, `anyhow!`, a workspace `render!`) and nothing at this
/// level can tell that from a macro that drops it.
///
/// An argument that is exactly the bare name is safe: `format_args!` takes each
/// of its arguments by reference, so `println!("{}", e)` cannot move `e`. An
/// argument that MENTIONS the name in any other shape -- `take(e)`,
/// `e.to_string()`, `&mut e` -- is put through the ordinary escape walk, and one
/// that does not parse as an expression at all (a `tracing` key-value, say) is
/// an escape by default rather than a guess. A name captured implicitly by the
/// format string (`"{e}"`) is not a token at this level and is never seen, which
/// is correct HERE and only here: outside a `move` closure a logging macro's
/// implicit capture is a shared borrow of a value nothing keeps. Inside one it
/// is a MOVE, and this function is never reached -- [`EscapeWalk::visit_macro`]
/// reads the whole token stream, literals included, the moment
/// [`EscapeWalk::moved`] is raised. It is not reached for any non-logging
/// macro either, for the same reason read the other way round: their implicit
/// capture may build a value the arm is then holding.
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
        // A bare `&e` goes to `format_args!` by reference and the macro's
        // value is `()`: exempt, as the bare name is. A CALL taking `&e` as a
        // direct argument is treated as a dropped call site -- the logging
        // macro prints its product and keeps nothing (design B1 (3)).
        let mut walk = EscapeWalk::new(names);
        if walk.is_shared_borrow_of_name(&expr) {
            continue;
        }
        if !walk.walk_dropped_call(&expr) {
            walk.visit_expr(&expr);
        }
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

/// Every mention of a name in a macro's tokens, INCLUDING one that is only
/// part of a string literal.
///
/// Two callers, one reason: a name can be named by a format string rather than
/// by a token. `move || println!("{e}")` holds no `e` token at all -- the
/// capture is written inside the literal, and inside a `move` closure it is a
/// capture by VALUE -- and `format!("{e}")`, `anyhow!("{e}")` or a workspace
/// `render!("{e}")` hide the same mention in the same place while RETURNING
/// the text they built. A whole-word search of each
/// literal is what finds both. The search is deliberately loose -- a literal
/// `"e"` that means something else reads as an escape -- because a false
/// ESCAPED costs one AMBIGUOUS and a false HANDLED costs a false accusation.
fn tokens_mention_deep(tokens: &TokenStream, names: &[String]) -> bool {
    tokens.clone().into_iter().any(|tt| match tt {
        TokenTree::Ident(id) => mentions(&id, names),
        TokenTree::Literal(lit) => literal_mentions(&lit.to_string(), names),
        TokenTree::Group(g) => tokens_mention_deep(&g.stream(), names),
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
