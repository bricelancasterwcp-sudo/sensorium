//! The `syn::visit::Visit` impl that drives the walk: the 22 `visit_*` methods
//! that decide what [`Ctx`](crate::visit::Ctx) is shown and in what order.
//!
//! Nothing here measures or splices. Each method recognises a shape, hands it
//! to the `Ctx` method that knows what to do with it, and recurses -- so the
//! grammar this transformer understands is readable in one file, and the state
//! it threads is readable in the parent.
//!
//! Split out of `visit.rs` at 773 of its 800 lines. A child module sees its
//! parent's private items, so `Ctx` kept every visibility it had.

use syn::visit::Visit;
use syn::{
    Arm, ExprAsync, ExprCall, ExprClosure, ExprConst, ExprIf, ExprMacro, ExprMethodCall, ExprTry,
    ImplItemConst, ImplItemFn, ItemConst, ItemFn, ItemImpl, ItemMacro, ItemMod, ItemStatic,
    ItemTrait, Local, Pat, StmtMacro, TraitItemConst, TraitItemFn,
};

use super::Ctx;
use crate::attrs::scan_macro_fns;
use crate::names::{line_of, path_span, self_type_name};
use crate::spawn;
use crate::{arms, closures, errflow};
use crate::{SiteKind, Skipped};

impl<'ast> Visit<'ast> for Ctx<'_> {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        let name = node.sig.ident.to_string();
        self.fn_item(&node.sig, &node.attrs, &node.block, &name);
        let is_const = node.sig.constness.is_some();
        // Nested items (a `fn` in a `fn`, an `impl` in a `fn`) are fn items too.
        self.in_item(name, |ctx| {
            ctx.in_const(is_const, |ctx| syn::visit::visit_block(ctx, &node.block));
        });
    }

    fn visit_impl_item_fn(&mut self, node: &'ast ImplItemFn) {
        let name = node.sig.ident.to_string();
        self.fn_item(&node.sig, &node.attrs, &node.block, &name);
        let is_const = node.sig.constness.is_some();
        self.in_item(name, |ctx| {
            ctx.in_const(is_const, |ctx| syn::visit::visit_block(ctx, &node.block));
        });
    }

    fn visit_trait_item_fn(&mut self, node: &'ast TraitItemFn) {
        // `fn name(&self);` has no body: nothing to instrument, and nothing to
        // excuse either -- it is not a fn item for E2's purposes.
        let Some(block) = node.default.as_ref() else {
            return;
        };
        let name = node.sig.ident.to_string();
        self.fn_item(&node.sig, &node.attrs, block, &name);
        let is_const = node.sig.constness.is_some();
        self.in_item(name, |ctx| {
            ctx.in_const(is_const, |ctx| syn::visit::visit_block(ctx, block));
        });
    }

    fn visit_item_impl(&mut self, node: &'ast ItemImpl) {
        // `impl<T> Holder<T>` -> `Holder`: the self type without generics or
        // path, which is what Python's `Type::method` looks like (spec §5.4).
        self.in_container(self_type_name(&node.self_ty), |ctx| {
            for item in &node.items {
                ctx.visit_impl_item(item);
            }
        });
    }

    fn visit_item_trait(&mut self, node: &'ast ItemTrait) {
        self.in_container(node.ident.to_string(), |ctx| {
            for item in &node.items {
                ctx.visit_trait_item(item);
            }
        });
    }

    fn visit_item_mod(&mut self, node: &'ast ItemMod) {
        // `mod foo;` is another file's problem; only inline modules nest here.
        let Some((_, items)) = node.content.as_ref() else {
            return;
        };
        self.in_container(node.ident.to_string(), |ctx| {
            for item in items {
                ctx.visit_item(item);
            }
        });
    }

    // A `const`/`static` initialiser is the ONE place besides a fn body where an
    // expression -- and so a spawn -- can sit. `pub static F: fn() = || {
    // thread::spawn(..); };` compiles on rustc 1.96 with `-D warnings`; the
    // closure is what makes it legal, since the spawn runs when `F` is CALLED
    // and never at const-evaluation time. Each pushes its own name so the spawn
    // is attributed to the item rather than to the `mod` or `impl` around it.
    //
    // None of these is a fn item, so none of them touches the census, the site
    // numbering or `skipped`: the frame is the whole effect.

    fn visit_item_const(&mut self, node: &'ast ItemConst) {
        self.in_item(node.ident.to_string(), |ctx| {
            ctx.in_const(true, |ctx| syn::visit::visit_item_const(ctx, node));
        });
    }

    fn visit_item_static(&mut self, node: &'ast ItemStatic) {
        self.in_item(node.ident.to_string(), |ctx| {
            ctx.in_const(true, |ctx| syn::visit::visit_item_static(ctx, node));
        });
    }

    fn visit_impl_item_const(&mut self, node: &'ast ImplItemConst) {
        self.in_item(node.ident.to_string(), |ctx| {
            ctx.in_const(true, |ctx| syn::visit::visit_impl_item_const(ctx, node));
        });
    }

    fn visit_trait_item_const(&mut self, node: &'ast TraitItemConst) {
        self.in_item(node.ident.to_string(), |ctx| {
            ctx.in_const(true, |ctx| syn::visit::visit_trait_item_const(ctx, node));
        });
    }

    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if self.emit {
            if let Some(shape) = spawn::classify_call(node) {
                let span = path_span(&node.func);
                let line = line_of(span);
                self.spawn_shape(&shape, line, span);
            }
        }
        syn::visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        if self.emit {
            if let Some(shape) = spawn::classify_method_call(node) {
                let span = node.method.span();
                self.spawn_shape(&shape, line_of(span), span);
            }
            if !self.const_ctx {
                if let Some(how) = errflow::sink_how(node) {
                    self.sink_site(node, how);
                }
            }
        }
        syn::visit::visit_expr_method_call(self, node);
    }

    /// Every `?` the parser turned into a node: counted for the census, and --
    /// on the emitting side, outside a const context -- probed. The count and
    /// the probe are the same set by construction, which is the identity
    /// `tests/census.rs` measures on a real workspace.
    fn visit_expr_try(&mut self, node: &'ast ExprTry) {
        self.try_syn += 1;
        if self.in_async {
            // Inside a future: declared, never wrapped (design R5/R6). Counted
            // on every walk so that a census sees the blind spot too.
            self.async_partials += 1;
            if self.emit {
                let line = line_of(node.question_token.spans[0]);
                self.declare_partial(line, SiteKind::Try, errflow::ASYNC_BLOCK);
            }
        } else if self.emit && !self.const_ctx {
            self.try_site(node);
        }
        syn::visit::visit_expr_try(self, node);
    }

    /// `let _ = <value expression>;` -- the third written sink (design R2).
    ///
    /// Only the bare `_` pattern: `let _: T = e;` is a different spelling the
    /// design does not name, and it is left alone rather than guessed at.
    fn visit_local(&mut self, node: &'ast Local) {
        if self.emit && !self.const_ctx && matches!(node.pat, Pat::Wild(_)) {
            if let Some(init) = node.init.as_ref() {
                self.let_underscore_site(&init.expr, node.let_token.span);
            }
        }
        syn::visit::visit_local(self, node);
    }

    /// `const { .. }` is a const context: nothing inside it may call
    /// `err_site`.
    fn visit_expr_const(&mut self, node: &'ast ExprConst) {
        self.in_const(true, |ctx| syn::visit::visit_expr_const(ctx, node));
    }

    /// `foo!(bar()?)` in expression position: the `?` is a TOKEN, not a node.
    fn visit_expr_macro(&mut self, node: &'ast ExprMacro) {
        self.macro_question_tokens(&node.mac.tokens);
        syn::visit::visit_expr_macro(self, node);
    }

    /// The same in statement position (`assert!(f()?);`).
    fn visit_stmt_macro(&mut self, node: &'ast StmtMacro) {
        self.macro_question_tokens(&node.mac.tokens);
        syn::visit::visit_stmt_macro(self, node);
    }

    /// Every `match` arm: an `Err(..) =>` one is classified and probed
    /// (design R2), and everything else is walked unchanged.
    fn visit_arm(&mut self, node: &'ast Arm) {
        if !self.const_ctx {
            self.err_arm(&node.pat, arms::Body::Expr(&node.body));
        }
        syn::visit::visit_arm(self, node);
    }

    /// `if let Err(..) = <scrutinee> { .. }`: the THEN block is classified
    /// exactly as an arm body is. An `else` branch is not an `Err` body and is
    /// left alone -- `syn::visit` walks it as usual.
    fn visit_expr_if(&mut self, node: &'ast ExprIf) {
        if !self.const_ctx {
            if let syn::Expr::Let(cond) = &*node.cond {
                self.err_arm(&cond.pat, arms::Body::Block(&node.then_branch));
            }
        }
        syn::visit::visit_expr_if(self, node);
    }

    /// A closure body is not a const context, whatever it sits in: a closure
    /// declared in a `const fn` may call a non-const fn, because its body runs
    /// when the closure is CALLED (measured on rustc 1.96, 2026-09-04). For the
    /// same reason a PLAIN closure inside an `async` block is not async code:
    /// its body runs on whichever thread calls it, so `in_async` is cleared.
    ///
    /// A closure holding a `?` at its own depth is given a frame (design R5)
    /// WHEREVER it was written -- inside an async block included, since its body
    /// still runs on whichever thread calls it. An `async` closure never is, and
    /// the `?` inside one is declared.
    fn visit_expr_closure(&mut self, node: &'ast ExprClosure) {
        let is_async = node.asyncness.is_some();
        let framed = !is_async && closures::holds_try(&node.body);
        if framed {
            self.closures_framed += 1;
        }
        let pushed = framed && self.frame_closure(node);
        self.in_async_scope(is_async, |ctx| {
            ctx.in_const(false, |ctx| syn::visit::visit_expr_closure(ctx, node));
        });
        if pushed {
            self.closure_frames.pop();
        }
    }

    /// An `async {}` block: never framed, and every `?` inside is declared
    /// rather than wrapped (design R5/R6).
    fn visit_expr_async(&mut self, node: &'ast ExprAsync) {
        self.in_async_scope(true, |ctx| syn::visit::visit_expr_async(ctx, node));
    }

    fn visit_item_macro(&mut self, node: &'ast ItemMacro) {
        // An item-position macro INVOCATION. Its tokens are opaque, so a `?` in
        // them is one the transformer cannot see -- counted, like the expression
        // and statement forms above. A `macro_rules!` DEFINITION falls through to
        // the skip scan below and its `?`s are never counted: there, `$( .. )?`
        // is a repetition operator (`Census::try_macro_tokens`).
        if !node.mac.path.is_ident("macro_rules") {
            self.macro_question_tokens(&node.mac.tokens);
            return;
        }
        if !self.emit && !self.record_sites {
            return;
        }
        // A fn inside a `macro_rules!` body is not an AST fn item -- `syn` sees
        // an opaque token stream -- so it can never be instrumented and is never
        // in the census either. It is declared anyway, so a reader can see that
        // the transformer knew it was there.
        let name = node
            .ident
            .as_ref()
            .map_or_else(|| "macro_rules".to_owned(), ToString::to_string);
        let mut lines = Vec::new();
        scan_macro_fns(&node.mac.tokens, &mut lines);
        for line in lines {
            self.skipped.push(Skipped {
                file: self.file.to_owned(),
                qualname: format!("{name}!"),
                line,
                reason: "macro",
            });
        }
    }
}
