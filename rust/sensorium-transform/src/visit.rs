//! The walk: which fn items exist, what each one is, and where its guard, its
//! exit operands and its spawn callees are.
//!
//! The AST is a MEASURING instrument here and nowhere a printer (spec §3.1):
//! every answer this module produces is a byte OFFSET into the original source,
//! handed to `splice.rs` to put a newline-free fragment at. Nothing is
//! re-rendered, so `line!()`, panic locations, backtraces and rustc's own
//! diagnostics are the plain build's.
//!
//! Every computed offset is checked against the byte the grammar says must be
//! there (`{` for a body, `]` for an inner attribute, `(` for a call). A future
//! `proc-macro2` that changed what `Span::byte_range()` is relative to would
//! otherwise mis-splice silently, and every measurement downstream of this crate
//! would inherit it.

use std::collections::HashMap;

use proc_macro2::Span;
use syn::visit::Visit;
use syn::{
    Arm, AttrStyle, Attribute, Block, ExprAsync, ExprCall, ExprClosure, ExprConst, ExprIf,
    ExprMacro, ExprMethodCall, ExprTry, ImplItemConst, ImplItemFn, ItemConst, ItemFn, ItemImpl,
    ItemMacro, ItemMod, ItemStatic, ItemTrait, Local, Pat, Signature, StmtMacro, TraitItemConst,
    TraitItemFn,
};

use crate::attrs::{inner_attr_end, scan_macro_fns};
use crate::exits::{self, Operand};
use crate::names::{line_of, path_span, self_type_name};
use crate::spawn;
use crate::splice::{guard_fragment, ret_open_fragment, Kind, Splice, RET_CLOSE};
use crate::{arms, closures, errflow, marks};
use crate::{Census, Partial, RetKind, Site, SiteKind, Skipped, SpawnSite, MAX_SITE_INDEX};

/// What one walk found: everything `splice.rs` needs and nothing it does not.
pub(crate) struct Walked {
    pub sites: Vec<Site>,
    pub skipped: Vec<Skipped>,
    pub partial: Vec<Partial>,
    /// Byte offset (for source order) and the site.
    pub spawns: Vec<(usize, SpawnSite)>,
    pub splices: Vec<Splice>,
}

/// One frame of the scope stack.
///
/// `named_item` is what tells a spawn which item to blame. A `fn`, a `const`, a
/// `static` and an associated `const` all NAME the code inside them, and an
/// expression can sit directly in one. A `mod`, an `impl` and a `trait` only
/// hold items -- an expression cannot sit directly in one -- so they contribute
/// their name to a qualname without ever being the innermost frame a spawn is
/// attributed to.
struct Frame {
    name: String,
    named_item: bool,
}

/// The walk's state.
///
/// The fields are `pub(crate)` rather than private because the err-flow half of
/// the walk lives in [`crate::errflow`] (this file is at the 800-line ceiling
/// with the rung-1 and rung-2 halves in it). Nothing outside the crate can see
/// them, and `Ctx` itself is still only constructed here and in
/// [`crate::splice`].
pub(crate) struct Ctx<'a> {
    pub(crate) source: &'a str,
    pub(crate) prefix: usize,
    pub(crate) file: &'a str,
    /// Push/pop of `mod`, `impl` self type, `trait`, enclosing fn, `const` and
    /// `static` names -- see [`Frame`].
    scope: Vec<Frame>,
    /// How many WRAPPED spawn sites each enclosing qualname has had so far.
    /// `Ctx` is per file, so this is the per-`(file, qualname)` counter plan
    /// decision N1 names, and `splice::run` re-derives it from source order
    /// afterwards rather than trusting it (N4).
    pub(crate) spawn_ordinals: HashMap<String, u32>,
    pub(crate) next_site: u32,
    /// False in census mode: classification runs, splicing does not.
    pub(crate) emit: bool,
    pub(crate) sites: Vec<Site>,
    skipped: Vec<Skipped>,
    /// Err-flow sites the walk met and could not reach (design R6).
    pub(crate) partial: Vec<Partial>,
    /// True inside a `const fn` body, a `const`/`static` initialiser or a
    /// `const { .. }` block -- and false again inside a closure within one,
    /// whose body runs when the closure is CALLED.
    ///
    /// No err-flow probe is placed in a const context: `err_site` is not a
    /// `const fn`, so a wrap there is E0015 (measured on rustc 1.96,
    /// 2026-09-04). It costs nothing measurable, because `?` and the four
    /// sinks are themselves rejected in const contexts ("`?` is not allowed
    /// ... in constant functions", "cannot call conditionally-const method
    /// `Result::<u8, u8>::unwrap_or`"); the one shape that does reach here is
    /// `let _ = <expr>;`, which absorbs nothing anyway.
    pub(crate) const_ctx: bool,
    /// True inside an `async {}` block or an `async` closure body, and false
    /// again inside a plain closure within one -- whose body runs when the
    /// closure is CALLED, on the caller's thread, not when the future is
    /// polled. A `?` met while this is set is DECLARED, never wrapped
    /// (`errflow::ASYNC_BLOCK`), and no closure is framed while it is set.
    pub(crate) in_async: bool,
    /// The unit's crate root is a BINARY's, so a file-scope `fn main` here is
    /// the program's entry (design R1b). Set by [`crate::splice::run`] from the
    /// caller's [`crate::FileRole`]; false for every file whose caller does not
    /// know.
    pub(crate) is_bin_root: bool,
    /// The qualnames of the FRAMED closures the walk is currently inside,
    /// innermost last. An err-flow row inside one belongs to the closure rather
    /// than to the item ([`Ctx::err_qualname`]); a spawn does not, so this is
    /// deliberately separate from `scope`.
    pub(crate) closure_frames: Vec<String>,
    /// How many FRAMED closures each enclosing ITEM qualname has had, which is
    /// the `#k` of a closure's `{{closure}}#k` name (design R5). Keyed by the
    /// item, never by an enclosing closure, so the names stay flat.
    pub(crate) closure_ordinals: HashMap<String, u32>,
    /// Byte offset (for source order) and the site.
    pub(crate) spawns: Vec<(usize, SpawnSite)>,
    splices: Vec<Splice>,
    fn_items: usize,
    const_fns: usize,
    extern_fns: usize,
    async_fns: usize,
    /// Census only (see [`Census::try_syn`]): counted on every walk, read only
    /// through [`Ctx::census`], and never a splice. Rung 3's transformer adds the
    /// instrumenting side of `?` separately, gated on `emit`.
    try_syn: usize,
    /// Census only (see [`Census::try_macro_tokens`]).
    pub(crate) try_macro_tokens: usize,
    /// Counted on every walk, by the same classification that places the arm
    /// probes: `[propagate, panic, escaped, handled]` (see [`Census`]).
    pub(crate) arms: [usize; 4],
    /// Counted on every walk: closures given a frame, and `?` inside an async
    /// block. Both are decisions, not splices, so a census sees them too.
    pub(crate) closures_framed: usize,
    pub(crate) async_partials: usize,
    error: Option<syn::Error>,
}

impl<'a> Ctx<'a> {
    pub(crate) fn new(
        source: &'a str,
        prefix: usize,
        file: &'a str,
        first_site: u32,
        emit: bool,
    ) -> Self {
        Ctx {
            source,
            prefix,
            file,
            scope: Vec::new(),
            spawn_ordinals: HashMap::new(),
            next_site: first_site,
            emit,
            sites: Vec::new(),
            skipped: Vec::new(),
            partial: Vec::new(),
            const_ctx: false,
            in_async: false,
            is_bin_root: false,
            closure_frames: Vec::new(),
            closure_ordinals: HashMap::new(),
            spawns: Vec::new(),
            splices: Vec::new(),
            fn_items: 0,
            const_fns: 0,
            extern_fns: 0,
            async_fns: 0,
            try_syn: 0,
            try_macro_tokens: 0,
            arms: [0; 4],
            closures_framed: 0,
            async_partials: 0,
            error: None,
        }
    }

    /// The walk's result, or the first offset anomaly it met.
    ///
    /// # Errors
    /// A computed offset did not land where the grammar says it must, or the
    /// site indices would overflow the wire format's 24-bit field.
    pub(crate) fn finish(self) -> Result<Walked, syn::Error> {
        if let Some(err) = self.error {
            return Err(err);
        }
        Ok(Walked {
            sites: self.sites,
            skipped: self.skipped,
            partial: self.partial,
            spawns: self.spawns,
            splices: self.splices,
        })
    }

    /// The counts E2 reads, from the same classification that instrumented.
    pub(crate) fn census(&self) -> Census {
        Census {
            fn_items: self.fn_items,
            const_fns: self.const_fns,
            extern_fns: self.extern_fns,
            async_fns: self.async_fns,
            try_syn: self.try_syn,
            try_macro_tokens: self.try_macro_tokens,
            arms_propagate: self.arms[0],
            arms_panic: self.arms[1],
            arms_escaped: self.arms[2],
            arms_handled: self.arms[3],
            closures_framed: self.closures_framed,
            async_partials: self.async_partials,
            parsed: true,
        }
    }

    pub(crate) fn fail(&mut self, span: Span, msg: &str) {
        if self.error.is_none() {
            self.error = Some(syn::Error::new(span, msg));
        }
    }

    pub(crate) fn start_of(&self, span: Span) -> usize {
        self.prefix + span.byte_range().start
    }

    pub(crate) fn end_of(&self, span: Span) -> usize {
        self.prefix + span.byte_range().end
    }

    pub(crate) fn push(&mut self, start: usize, end: usize, kind: Kind, text: String) {
        let seq = self.splices.len();
        self.splices.push(Splice {
            start,
            end,
            kind,
            seq,
            text,
        });
    }

    /// `mod_a::mod_b::Type::fn_name` -- the file-local path in Python's shape.
    fn qualname(&self, name: &str) -> String {
        if self.scope.is_empty() {
            return name.to_owned();
        }
        let mut out = self.scope_path();
        out.push_str("::");
        out.push_str(name);
        out
    }

    /// Every frame's name joined -- containers included, since `Type::method`
    /// is what the manifest spells.
    pub(crate) fn scope_path(&self) -> String {
        self.scope
            .iter()
            .map(|f| f.name.as_str())
            .collect::<Vec<_>>()
            .join("::")
    }

    /// The qualname of the NAMED ITEM a spawn call sits in (plan decision N5,
    /// as amended in fix round 1).
    ///
    /// A spawn is an expression, and almost every expression sits inside a
    /// named item: a `fn` body, or a `const`/`static`/associated-const
    /// initialiser (`pub static F: fn() = || { thread::spawn(..); };` compiles,
    /// and the closure is what makes it legal -- the spawn runs when `F` is
    /// CALLED, not at const-evaluation time). Closures, blocks and `match` arms
    /// push no scope, so for those the stack's innermost frame IS that item.
    ///
    /// For a fn the answer is exactly that fn's [`Site::qualname`]; for a
    /// `const`/`static` it is the item's own file-local path (`m::H`, `T::F`),
    /// which no `Site` carries because a const is not a fn item.
    ///
    /// `None` when the innermost frame is a `mod`, an `impl` or a `trait`, or
    /// when there is no frame at all. That is REACHABLE in valid Rust, and
    /// `tests/edges.rs` is the falsifier: an enum DISCRIMINANT and an array
    /// LENGTH in a struct field's type are both expressions that sit in a `mod`
    /// body with no fn/const/static frame between them and the `mod`, and both
    /// compile on rustc 1.96 with `-D warnings` with a spawning closure inside.
    /// Such a file is REFUSED -- it costs that file its instrumentation -- in
    /// preference to naming the child after a container, which would put it in
    /// the same counter as an unrelated `fn m()` and give the manifest a
    /// qualname no item has.
    pub(crate) fn enclosing_qualname(&self) -> Option<String> {
        if !self.scope.last()?.named_item {
            return None;
        }
        Some(self.scope_path())
    }

    /// The byte offset the guard goes at, with the grammar checked.
    pub(crate) fn body_offset(&mut self, attrs: &[Attribute], block: &Block) -> Option<usize> {
        let open = block.brace_token.span.open();
        let open_start = self.start_of(open);
        if self.source.as_bytes().get(open_start) != Some(&b'{') {
            self.fail(
                open,
                "byte offset does not land on the body's opening brace -- \
                 Span::byte_range() is not relative to what this crate assumes",
            );
            return None;
        }
        let mut offset = self.end_of(open);

        // `#![..]` must remain the first thing in the block, so the guard goes
        // after the last inner attribute rather than ahead of it.
        for attr in attrs {
            if !matches!(attr.style, AttrStyle::Inner(_)) {
                continue;
            }
            let end = self.inner_attr_end(attr)?;
            if end > offset {
                offset = end;
            }
        }
        if !self.source.is_char_boundary(offset) {
            self.fail(open, "splice offset falls inside a UTF-8 character");
            return None;
        }
        Some(offset)
    }

    /// [`inner_attr_end`] with this walk's source, failing the file rather than
    /// answering with a guess.
    fn inner_attr_end(&mut self, attr: &Attribute) -> Option<usize> {
        match inner_attr_end(self.source, self.prefix, attr) {
            Ok(end) => Some(end),
            Err(msg) => {
                self.fail(attr.bracket_token.span.close(), msg);
                None
            }
        }
    }

    /// Which disjoint bucket this signature falls in, if any, counting it as it
    /// goes.
    ///
    /// The order is what makes the buckets disjoint, so that a fn is classified
    /// exactly once and `fn_items - const_fns - extern_fns` never subtracts one
    /// fn twice. (`const async fn` and `async extern fn` are both rejected by
    /// rustc, so the order is a formality, not a policy.)
    fn classify(&mut self, sig: &Signature) -> Option<&'static str> {
        if sig.constness.is_some() {
            self.const_fns += 1;
            return Some("const");
        }
        if sig.abi.is_some() {
            self.extern_fns += 1;
            return Some("extern");
        }
        if sig.asyncness.is_some() {
            // A guard in an `async fn` body lives inside the future, so it is
            // dropped when the future is dropped -- possibly on a different
            // thread than the one that created it, and never at the `.await`
            // boundaries the caller would read as returns. That contradicts
            // spec §3.2's "the guard's Drop is the SOLE emitter of RETURN".
            self.async_fns += 1;
            return Some("async");
        }
        None
    }

    /// Classify one fn item with a body, and instrument it if it is eligible.
    fn fn_item(&mut self, sig: &Signature, attrs: &[Attribute], block: &Block, name: &str) {
        self.fn_items += 1;
        let line = line_of(sig.fn_token.span);
        let qualname = self.qualname(name);

        if let Some(reason) = self.classify(sig) {
            if self.emit {
                self.skipped.push(Skipped {
                    file: self.file.to_owned(),
                    qualname,
                    line,
                    reason,
                });
            }
            return;
        }
        if !self.emit {
            return;
        }
        if self.next_site > MAX_SITE_INDEX {
            self.fail(
                sig.fn_token.span,
                "site index past 24 bits: the runtime's site word cannot carry it",
            );
            return;
        }
        let Some(offset) = self.body_offset(attrs, block) else {
            return;
        };
        let site = self.next_site;
        self.next_site += 1;
        self.push(offset, offset, Kind::Guard, guard_fragment(site));

        let ret = exits::ret_kind(sig);
        if ret == RetKind::Value {
            for operand in exits::operands(block) {
                self.wrap_operand(site, operand, sig.fn_token.span);
            }
        }

        self.sites.push(Site {
            site,
            file: self.file.to_owned(),
            qualname,
            firstlineno: line,
            ret: Some(ret),
            kind: SiteKind::Fn,
            how: None,
            test: marks::is_test_fn(attrs),
            // A `main` inside a `mod`, an `impl` or another fn is an ordinary
            // fn: the scope stack being EMPTY is what says this one is the
            // crate root's, and only the caller knows the root is a binary's.
            main: self.is_bin_root && self.scope.is_empty() && name == "main",
        });
    }

    /// The two splices of one exit wrap, with the operand's own outer attributes
    /// left outside: an attribute belongs to the statement, and
    /// `f(#[cfg(x)] e)` is not Rust.
    pub(crate) fn wrap_operand(&mut self, site: u32, operand: Operand, span: Span) {
        let start = self.prefix + operand.start;
        let end = self.prefix + operand.end;
        let Some(text) = self.source.get(start..end) else {
            self.fail(span, "exit operand span is not a byte range of the source");
            return;
        };
        let Some(attrs_len) = exits::attribute_prefix_len(text) else {
            self.fail(span, "exit operand does not re-tokenise as an expression");
            return;
        };
        let open = start + attrs_len;
        if !self.source.is_char_boundary(open) || !self.source.is_char_boundary(end) {
            self.fail(span, "exit operand offset falls inside a UTF-8 character");
            return;
        }
        self.push(open, open, Kind::Open, ret_open_fragment(site));
        self.push(end, end, Kind::Close, RET_CLOSE.to_owned());
    }

    /// Descend into an item whose body or initialiser holds EXPRESSIONS: a fn, a
    /// `const`, a `static`, an associated const. A spawn met inside is named
    /// after it.
    fn in_item<F: FnOnce(&mut Self)>(&mut self, name: String, f: F) {
        self.in_frame(name, true, f);
    }

    /// Descend into a container whose body holds ITEMS only: a `mod`, an
    /// `impl`, a `trait`. It contributes its name to a qualname and can never
    /// be what a spawn is named after.
    fn in_container<F: FnOnce(&mut Self)>(&mut self, name: String, f: F) {
        self.in_frame(name, false, f);
    }

    fn in_frame<F: FnOnce(&mut Self)>(&mut self, name: String, named_item: bool, f: F) {
        self.scope.push(Frame { name, named_item });
        f(self);
        self.scope.pop();
    }

    /// Descend with [`Ctx::const_ctx`] set, and put it back afterwards. A
    /// `const fn` inside a plain one sets it; a closure inside a `const fn`
    /// clears it.
    pub(crate) fn in_const<F: FnOnce(&mut Self)>(&mut self, const_ctx: bool, f: F) {
        let saved = self.const_ctx;
        self.const_ctx = const_ctx;
        f(self);
        self.const_ctx = saved;
    }

    /// The same for [`Ctx::in_async`]. Set on an `async` block or an `async`
    /// closure, CLEARED on a plain closure inside one.
    fn in_async_scope<F: FnOnce(&mut Self)>(&mut self, in_async: bool, f: F) {
        let saved = self.in_async;
        self.in_async = in_async;
        f(self);
        self.in_async = saved;
    }
}

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
        if !self.emit {
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
