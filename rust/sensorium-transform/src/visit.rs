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

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::visit::Visit;
use syn::{
    AttrStyle, Attribute, Block, ExprCall, ExprMethodCall, ImplItemFn, ItemFn, ItemImpl, ItemMacro,
    ItemMod, ItemTrait, Signature, TraitItemFn, Type,
};

use crate::exits::{self, Operand};
use crate::spawn::{self, Rewrite, Shape};
use crate::splice::{guard_fragment, ret_open_fragment, Kind, Splice, RET_CLOSE};
use crate::{Census, RetKind, Site, Skipped, SpawnSite, MAX_SITE_INDEX};

/// What one walk found: everything `splice.rs` needs and nothing it does not.
pub(crate) struct Walked {
    pub sites: Vec<Site>,
    pub skipped: Vec<Skipped>,
    /// Byte offset (for source order) and the site.
    pub spawns: Vec<(usize, SpawnSite)>,
    pub splices: Vec<Splice>,
}

pub(crate) struct Ctx<'a> {
    source: &'a str,
    prefix: usize,
    file: &'a str,
    /// Push/pop of `mod`, `impl` self type, `trait` and enclosing fn names.
    scope: Vec<String>,
    next_site: u32,
    /// False in census mode: classification runs, splicing does not.
    emit: bool,
    sites: Vec<Site>,
    skipped: Vec<Skipped>,
    /// Byte offset (for source order) and the site.
    spawns: Vec<(usize, SpawnSite)>,
    splices: Vec<Splice>,
    fn_items: usize,
    const_fns: usize,
    extern_fns: usize,
    async_fns: usize,
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
            next_site: first_site,
            emit,
            sites: Vec::new(),
            skipped: Vec::new(),
            spawns: Vec::new(),
            splices: Vec::new(),
            fn_items: 0,
            const_fns: 0,
            extern_fns: 0,
            async_fns: 0,
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
            parsed: true,
        }
    }

    fn fail(&mut self, span: Span, msg: &str) {
        if self.error.is_none() {
            self.error = Some(syn::Error::new(span, msg));
        }
    }

    fn start_of(&self, span: Span) -> usize {
        self.prefix + span.byte_range().start
    }

    fn end_of(&self, span: Span) -> usize {
        self.prefix + span.byte_range().end
    }

    fn push(&mut self, start: usize, end: usize, kind: Kind, text: String) {
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
        let mut out = self.scope.join("::");
        out.push_str("::");
        out.push_str(name);
        out
    }

    /// The byte offset the guard goes at, with the grammar checked.
    fn body_offset(&mut self, attrs: &[Attribute], block: &Block) -> Option<usize> {
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

    /// The byte offset just past one inner attribute of a body.
    ///
    /// Three forms reach here, and only the first ends on a `]`:
    ///
    /// * `#![allow(..)]` -- a real attribute; the span covers the brackets.
    /// * `//! doc` -- `syn` reports a doc comment as an `AttrStyle::Inner`
    ///   attribute whose bracket span covers the COMMENT TEXT. Its end is inside
    ///   a line comment, so the guard moves past that line's newline; the
    ///   fragment is still newline-free and the line count still holds. Both
    ///   forms are legal Rust and both appear in real code, so rejecting the
    ///   file (which is what requiring `]` did) is not an option.
    /// * `/*! doc */` -- the same, except the span already ends after the `*/`.
    fn inner_attr_end(&mut self, attr: &Attribute) -> Option<usize> {
        let close = attr.bracket_token.span.close();
        let start = self.start_of(attr.bracket_token.span.join());
        let end = self.end_of(close);
        let Some(text) = self.source.get(start..end) else {
            self.fail(
                close,
                "inner attribute span is not a byte range of the source",
            );
            return None;
        };
        if text.starts_with("//") {
            // Past the comment's own newline.
            return match self.source[end..].find('\n') {
                Some(nl) => Some(end + nl + 1),
                None => {
                    self.fail(
                        close,
                        "inner line doc comment is not terminated by a newline",
                    );
                    None
                }
            };
        }
        if text.starts_with("/*") {
            return Some(end);
        }
        if end == 0 || self.source.as_bytes().get(end - 1) != Some(&b']') {
            self.fail(close, "inner attribute does not end where its span says");
            return None;
        }
        Some(end)
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
            ret,
        });
    }

    /// The two splices of one exit wrap, with the operand's own outer attributes
    /// left outside: an attribute belongs to the statement, and
    /// `f(#[cfg(x)] e)` is not Rust.
    fn wrap_operand(&mut self, site: u32, operand: Operand, span: Span) {
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

    /// Record one spawn shape, rewriting the callee when it is the one spelling
    /// this rung rewrites.
    fn spawn_shape(&mut self, shape: &Shape, line: u32, span: Span) {
        match shape {
            Shape::Declare(reason) => {
                let offset = self.start_of(span);
                self.declare_spawn(offset, line, Some(reason));
            }
            Shape::Rewrite(r) => self.rewrite_spawn(r, line, span),
        }
    }

    fn declare_spawn(&mut self, offset: usize, line: u32, reason: Option<&'static str>) {
        self.spawns.push((
            offset,
            SpawnSite {
                file: self.file.to_owned(),
                line,
                wrapped: reason.is_none(),
                reason,
            },
        ));
    }

    /// The callee path becomes `::sensorium_rt::spawn_child` and the site
    /// argument goes in past the `(`; the bytes between them are untouched.
    fn rewrite_spawn(&mut self, r: &Rewrite, line: u32, span: Span) {
        let path_start = self.prefix + r.path_start;
        let path_end = self.prefix + r.path_end;
        let paren_start = self.prefix + r.paren_open_start;
        let paren_end = self.prefix + r.paren_open_end;
        if self.source.as_bytes().get(paren_start) != Some(&b'(') {
            self.fail(
                span,
                "spawn call's opening paren is not where its span says",
            );
            return;
        }
        if !self.source.is_char_boundary(path_start) || !self.source.is_char_boundary(path_end) {
            self.fail(span, "spawn callee offset falls inside a UTF-8 character");
            return;
        }
        self.push(
            path_start,
            path_end,
            Kind::Replace,
            spawn::CALLEE.to_owned(),
        );
        self.push(
            paren_end,
            paren_end,
            Kind::SpawnArg,
            spawn::site_argument(self.file, line, r.use_path.as_deref()),
        );
        self.declare_spawn(path_start, line, None);
    }

    fn in_scope<F: FnOnce(&mut Self)>(&mut self, name: String, f: F) {
        self.scope.push(name);
        f(self);
        self.scope.pop();
    }
}

impl<'ast> Visit<'ast> for Ctx<'_> {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        let name = node.sig.ident.to_string();
        self.fn_item(&node.sig, &node.attrs, &node.block, &name);
        // Nested items (a `fn` in a `fn`, an `impl` in a `fn`) are fn items too.
        self.in_scope(name, |ctx| syn::visit::visit_block(ctx, &node.block));
    }

    fn visit_impl_item_fn(&mut self, node: &'ast ImplItemFn) {
        let name = node.sig.ident.to_string();
        self.fn_item(&node.sig, &node.attrs, &node.block, &name);
        self.in_scope(name, |ctx| syn::visit::visit_block(ctx, &node.block));
    }

    fn visit_trait_item_fn(&mut self, node: &'ast TraitItemFn) {
        // `fn name(&self);` has no body: nothing to instrument, and nothing to
        // excuse either -- it is not a fn item for E2's purposes.
        let Some(block) = node.default.as_ref() else {
            return;
        };
        let name = node.sig.ident.to_string();
        self.fn_item(&node.sig, &node.attrs, block, &name);
        self.in_scope(name, |ctx| syn::visit::visit_block(ctx, block));
    }

    fn visit_item_impl(&mut self, node: &'ast ItemImpl) {
        // `impl<T> Holder<T>` -> `Holder`: the self type without generics or
        // path, which is what Python's `Type::method` looks like (spec §5.4).
        self.in_scope(self_type_name(&node.self_ty), |ctx| {
            for item in &node.items {
                ctx.visit_impl_item(item);
            }
        });
    }

    fn visit_item_trait(&mut self, node: &'ast ItemTrait) {
        self.in_scope(node.ident.to_string(), |ctx| {
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
        self.in_scope(node.ident.to_string(), |ctx| {
            for item in items {
                ctx.visit_item(item);
            }
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
        }
        syn::visit::visit_expr_method_call(self, node);
    }

    fn visit_item_macro(&mut self, node: &'ast ItemMacro) {
        if !self.emit || !node.mac.path.is_ident("macro_rules") {
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

/// The 1-based line a span starts on.
fn line_of(span: Span) -> u32 {
    u32::try_from(span.start().line).unwrap_or(u32::MAX)
}

/// The span of a callee path's FIRST token: `Spanned` on the whole path would
/// answer with a join that is only as good as `proc-macro2`'s, and the line is
/// all this needs.
fn path_span(func: &syn::Expr) -> Span {
    match func {
        syn::Expr::Path(p) => match &p.path.leading_colon {
            Some(c) => c.spans[0],
            None => p.path.segments[0].ident.span(),
        },
        other => {
            use syn::spanned::Spanned;
            other.span()
        }
    }
}

/// Lines of `fn` tokens inside a macro body, skipping fn-POINTER types
/// (`fn(u8) -> u8`), whose `fn` is followed by `(`.
fn scan_macro_fns(tokens: &TokenStream, out: &mut Vec<u32>) {
    let mut pending: Option<Span> = None;
    for tt in tokens.clone() {
        if let Some(span) = pending.take() {
            let is_fn_pointer = matches!(&tt, TokenTree::Group(g)
                if g.delimiter() == proc_macro2::Delimiter::Parenthesis);
            if !is_fn_pointer {
                out.push(u32::try_from(span.start().line).unwrap_or(u32::MAX));
            }
        }
        match tt {
            TokenTree::Ident(ref id) if id == "fn" => pending = Some(id.span()),
            TokenTree::Group(ref g) => scan_macro_fns(&g.stream(), out),
            _ => {}
        }
    }
    // A trailing `fn` with nothing after it cannot be a fn pointer.
    if let Some(span) = pending {
        out.push(u32::try_from(span.start().line).unwrap_or(u32::MAX));
    }
}

/// The impl's self type as a bare name: no generic arguments, no path prefix.
fn self_type_name(ty: &Type) -> String {
    match ty {
        Type::Path(p) => p
            .path
            .segments
            .last()
            .map_or_else(|| "<type>".to_owned(), |s| s.ident.to_string()),
        Type::Reference(r) => self_type_name(&r.elem),
        Type::Ptr(p) => self_type_name(&p.elem),
        Type::Paren(p) => self_type_name(&p.elem),
        Type::Group(g) => self_type_name(&g.elem),
        Type::Slice(s) => format!("[{}]", self_type_name(&s.elem)),
        Type::Array(a) => format!("[{}]", self_type_name(&a.elem)),
        Type::Tuple(t) => {
            let inner: Vec<String> = t.elems.iter().map(self_type_name).collect();
            format!("({})", inner.join(", "))
        }
        Type::Never(_) => "!".to_owned(),
        Type::TraitObject(t) => {
            let name = t
                .bounds
                .iter()
                .find_map(|b| match b {
                    syn::TypeParamBound::Trait(tr) => {
                        tr.path.segments.last().map(|s| s.ident.to_string())
                    }
                    _ => None,
                })
                .unwrap_or_else(|| "<type>".to_owned());
            format!("dyn {name}")
        }
        _ => "<type>".to_owned(),
    }
}
