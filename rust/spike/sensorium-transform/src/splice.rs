//! The splicer: `syn` says where the braces are, the original bytes are copied
//! through, and newline-free fragments go in at those offsets. The AST is a
//! ruler, never a printer (spec §3.1).
//!
//! # Where the offsets come from
//!
//! `proc-macro2` with `span-locations` gives `Span::byte_range()` outside a
//! proc-macro context, and that is what is used -- not `start()`/`end()`, whose
//! `column` counts CHARS and would mis-splice the first file with a `π` in it.
//!
//! Two adjustments are not optional:
//!
//! * `syn::parse_file` strips a BOM and a shebang line BEFORE `proc-macro2` sees
//!   the text, so every byte range is short by that prefix. `File::shebang`
//!   reports exactly what syn removed, so the prefix is measured, not guessed.
//! * Line numbers need no adjustment: syn keeps the shebang's newline in the
//!   text it parses, so line 2 stays line 2.
//!
//! Every computed offset is checked against the byte the grammar says must be
//! there (`{` for a body, `]` for an inner attribute). A future `proc-macro2`
//! that changed what `byte_range()` is relative to would otherwise mis-splice
//! silently, and every measurement downstream of this crate would inherit it.

use std::str::FromStr;

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::visit::Visit;
use syn::{
    AttrStyle, Attribute, Block, ImplItemFn, ItemFn, ItemImpl, ItemMacro, ItemMod, ItemTrait,
    Signature, TraitItemFn, Type,
};

use crate::{Census, Site, Skipped, Transformed, MAX_SITE_INDEX};

/// The entry guard. Newline-free, and the ONLY place its text is written.
fn guard_fragment(site: u32) -> String {
    format!("let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, {site});")
}

/// The crate root's unit declaration. Newline-free -- which is why a newline in
/// the metadata is escaped rather than passed through: a Rust string literal
/// happily spans lines, and one that did would move every line below it.
fn unit_static(metadata: &str) -> String {
    let mut escaped = String::with_capacity(metadata.len());
    for ch in metadata.chars() {
        match ch {
            '\\' => escaped.push_str(r"\\"),
            '"' => escaped.push_str("\\\""),
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            _ => escaped.push(ch),
        }
    }
    format!(
        "#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = \
         ::sensorium_rt::Unit::new(\"{escaped}\");"
    )
}

pub(crate) fn run(
    source: &str,
    file: &str,
    unit_metadata: &str,
    first_site: u32,
    is_crate_root: bool,
) -> Result<Transformed, syn::Error> {
    let parsed = syn::parse_file(source)?;
    let prefix = stripped_prefix_len(source, parsed.shebang.as_deref());

    let mut ctx = Ctx::new(source, prefix, file, first_site, true);
    ctx.visit_file(&parsed);
    if let Some(err) = ctx.error {
        return Err(err);
    }

    let mut inserts = ctx.inserts;
    if is_crate_root {
        // LAST, and never sorted afterwards: the visitor yields guards in source
        // order, and the static's offset (end of the file's last token) is past
        // every body it contains, so the list is already ascending. A sort here
        // would be code no test can reach -- the assertion states the invariant
        // instead, and the slicing below panics loudly if it is ever violated.
        inserts.push((static_offset(source, prefix), unit_static(unit_metadata)));
    }
    debug_assert!(
        inserts.windows(2).all(|w| w[0].0 <= w[1].0),
        "splice offsets must ascend; the visitor and the static guarantee it"
    );

    let mut out = String::with_capacity(source.len() + inserts.len() * 80);
    let mut cut = 0usize;
    for (offset, fragment) in &inserts {
        out.push_str(&source[cut..*offset]);
        out.push_str(fragment);
        cut = *offset;
    }
    out.push_str(&source[cut..]);

    Ok(Transformed {
        source: out,
        sites: ctx.sites,
        skipped: ctx.skipped,
    })
}

pub(crate) fn census(source: &str) -> Census {
    let Ok(parsed) = syn::parse_file(source) else {
        // Three zeros with `parsed: false` -- NOT a measured zero.
        return Census::default();
    };
    let prefix = stripped_prefix_len(source, parsed.shebang.as_deref());
    let mut ctx = Ctx::new(source, prefix, "", 0, false);
    ctx.visit_file(&parsed);
    Census {
        fn_items: ctx.fn_items,
        const_fns: ctx.const_fns,
        extern_fns: ctx.extern_fns,
        parsed: true,
    }
}

/// How many bytes `syn::parse_file` removed before `proc-macro2` saw the text.
fn stripped_prefix_len(source: &str, shebang: Option<&str>) -> usize {
    let bom = usize::from(source.starts_with('\u{feff}')) * '\u{feff}'.len_utf8();
    bom + shebang.map_or(0, str::len)
}

/// Where the `__SENSORIUM_UNIT` static goes: immediately after the file's LAST
/// TOKEN.
///
/// Not "on the last line": a file whose last line is `// a comment` would
/// swallow the static. Not "after the final newline" either: that adds a line,
/// which is the one thing this crate exists to avoid. The last token is on the
/// last line of CODE, is never inside a comment, and is always at item level --
/// the file is a sequence of items, so its final token closes the final one.
///
/// A file with no tokens at all has no items and no inner attributes to
/// displace, so the head of the text is safe (and, unlike appending, keeps the
/// line count).
fn static_offset(source: &str, prefix: usize) -> usize {
    if let Some(end) = last_token_end(&source[prefix..]) {
        return prefix + end;
    }
    // Past the shebang's own newline, so the static cannot land inside it.
    if source.as_bytes().get(prefix) == Some(&b'\n') {
        prefix + 1
    } else {
        prefix
    }
}

fn last_token_end(content: &str) -> Option<usize> {
    let stream = TokenStream::from_str(content).ok()?;
    // A `Group`'s span covers its delimiters, so this is the closing brace of
    // the final item, not the token before it.
    stream
        .into_iter()
        .last()
        .map(|tt| tt.span().byte_range().end)
}

// ---------------------------------------------------------------------------
// The visitor
// ---------------------------------------------------------------------------

struct Ctx<'a> {
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
    inserts: Vec<(usize, String)>,
    fn_items: usize,
    const_fns: usize,
    extern_fns: usize,
    error: Option<syn::Error>,
}

impl<'a> Ctx<'a> {
    fn new(source: &'a str, prefix: usize, file: &'a str, first_site: u32, emit: bool) -> Self {
        Ctx {
            source,
            prefix,
            file,
            scope: Vec::new(),
            next_site: first_site,
            emit,
            sites: Vec::new(),
            skipped: Vec::new(),
            inserts: Vec::new(),
            fn_items: 0,
            const_fns: 0,
            extern_fns: 0,
            error: None,
        }
    }

    fn fail(&mut self, span: Span, msg: &str) {
        if self.error.is_none() {
            self.error = Some(syn::Error::new(span, msg));
        }
    }

    fn line_of(&self, span: Span) -> u32 {
        u32::try_from(span.start().line).unwrap_or(u32::MAX)
    }

    fn start_of(&self, span: Span) -> usize {
        self.prefix + span.byte_range().start
    }

    fn end_of(&self, span: Span) -> usize {
        self.prefix + span.byte_range().end
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
            let close = attr.bracket_token.span.close();
            let end = self.end_of(close);
            if end == 0 || self.source.as_bytes().get(end - 1) != Some(&b']') {
                self.fail(close, "inner attribute does not end where its span says");
                return None;
            }
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

    /// Classify one fn item with a body, and instrument it if it is eligible.
    fn fn_item(&mut self, sig: &Signature, attrs: &[Attribute], block: &Block, name: &str) {
        self.fn_items += 1;
        let line = self.line_of(sig.fn_token.span);
        let qualname = self.qualname(name);

        // const and extern are disjoint buckets, const first, so that
        // `fn_items - const_fns - extern_fns` never subtracts one fn twice.
        let reason = if sig.constness.is_some() {
            self.const_fns += 1;
            Some("const")
        } else if sig.abi.is_some() {
            self.extern_fns += 1;
            Some("extern")
        } else {
            None
        };
        if let Some(reason) = reason {
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
        self.inserts.push((offset, guard_fragment(site)));
        self.sites.push(Site {
            site,
            file: self.file.to_owned(),
            qualname,
            firstlineno: line,
        });
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

    fn visit_item_macro(&mut self, node: &'ast ItemMacro) {
        if !self.emit || !node.mac.path.is_ident("macro_rules") {
            return;
        }
        // A fn inside a `macro_rules!` body is not an AST fn item -- `syn` sees
        // an opaque token stream -- so it can never be instrumented and is
        // never in the census either. It is declared anyway, so E2's reader can
        // see that the transformer knew it was there.
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

/// Lines of `fn` tokens inside a macro body, skipping fn-POINTER types
/// (`fn(u8) -> u8`), whose `fn` is followed by `(`.
fn scan_macro_fns(tokens: &TokenStream, out: &mut Vec<u32>) {
    let mut pending: Option<Span> = None;
    for tt in tokens.clone() {
        if let Some(span) = pending.take() {
            let is_fn_pointer = matches!(&tt, TokenTree::Group(g) if g.delimiter() == proc_macro2::Delimiter::Parenthesis);
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
