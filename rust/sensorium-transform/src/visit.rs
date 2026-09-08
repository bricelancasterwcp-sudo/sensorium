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
use syn::{AttrStyle, Attribute, Block, Signature};

use crate::attrs::inner_attr_end;
use crate::census::Mode;
use crate::exits::{self, Operand};
use crate::focus::Focus;
use crate::names::line_of;
use crate::splice::{guard_fragment, ret_open_fragment, Kind, Splice, RET_CLOSE};
use crate::{lines, marks};
use crate::{Partial, RetKind, Site, SiteKind, Skipped, SpawnSite, MAX_SITE_INDEX};

/// The `syn::visit::Visit` impl -- the 22 `visit_*` methods that drive the walk
/// -- lives in `visit/walk.rs`. `Ctx` and everything that measures stay here,
/// because eight other modules import `Ctx` from this path.
mod walk;

/// What one walk found: everything `splice.rs` needs and nothing it does not.
pub(crate) struct Walked {
    pub sites: Vec<Site>,
    pub skipped: Vec<Skipped>,
    pub partial: Vec<Partial>,
    /// Byte offset (for source order) and the site.
    pub spawns: Vec<(usize, SpawnSite)>,
    pub splices: Vec<Splice>,
    /// The qualnames of the fn items this walk FOCUSED, in source order. Empty
    /// under an empty focus, and the manifest's `focus.matched` for this file.
    pub focused: Vec<String>,
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
    /// Which functions carry LINE probes (design 2026-09-06 §2.1). Empty for a
    /// census and for every unfocused build, and the ONE thing that makes the
    /// transformer's output depend on more than the source.
    focus: &'a Focus,
    /// The qualnames the focus matched here, in source order.
    focused: Vec<String>,
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
    /// Record the fn ROWS and the skip rows, independently of `emit` (design
    /// 2026-09-07 §6). True on the walk [`crate::census::walk`] runs for the
    /// driver's `--focus` resolver, which needs the rows and not one byte of
    /// the rewrite that would carry them; false on a counting census, which
    /// needs neither.
    ///
    /// The emitting walk records them too, so the flag is read as `emit ||
    /// record_sites` and never instead of `emit`: what it gates is the ROW, and
    /// what `emit` gates is the SPLICE. With `emit` false the row's
    /// `Site::site` numbers the fn rows alone -- no err-flow, closure or LINE
    /// site is minted to take a number from the same counter -- so it is not
    /// the index the transform would give that function, and nothing reads it.
    pub(crate) record_sites: bool,
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
    // The counters [`crate::census`] reads back through `Ctx::census`. They are
    // `pub(crate)` for the same reason the err-flow fields above are: the half
    // of the walk that reads them lives in another module, because this file is
    // at its 800-line ceiling.
    pub(crate) fn_items: usize,
    pub(crate) const_fns: usize,
    pub(crate) extern_fns: usize,
    pub(crate) async_fns: usize,
    /// Census only (see [`crate::Census::try_syn`]): counted on every walk, read
    /// only through `Ctx::census`, and never a splice. Rung 3's transformer adds
    /// the instrumenting side of `?` separately, gated on `emit`.
    pub(crate) try_syn: usize,
    /// Census only (see [`crate::Census::try_macro_tokens`]).
    pub(crate) try_macro_tokens: usize,
    /// Counted on every walk, by the same classification that places the arm
    /// probes: `[propagate, panic, escaped, handled]` (see [`crate::Census`]).
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
        mode: Mode,
        focus: &'a Focus,
    ) -> Self {
        Ctx {
            source,
            focus,
            focused: Vec::new(),
            prefix,
            file,
            scope: Vec::new(),
            spawn_ordinals: HashMap::new(),
            next_site: first_site,
            // Derived once, here, and read as two fields everywhere else: what
            // `emit` gates is the SPLICE and what `record_sites` gates is the
            // ROW (design 2026-09-07 §6).
            emit: mode.emits(),
            record_sites: mode.records_rows(),
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
            focused: self.focused,
        })
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

    /// Classify one fn item with a body, and instrument it if it is eligible.
    fn fn_item(&mut self, sig: &Signature, attrs: &[Attribute], block: &Block, name: &str) {
        self.fn_items += 1;
        let line = line_of(sig.fn_token.span);
        let qualname = self.qualname(name);

        if let Some(reason) = self.classify(sig) {
            if self.emit || self.record_sites {
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
            if self.record_sites {
                // The census walk: the row the emitting walk below would mint,
                // and not one byte of the rewrite that would carry it. The
                // index is the fn rows' own here -- see `Ctx::record_sites`.
                let site = self.next_site;
                self.next_site += 1;
                let row = self.fn_row(site, qualname, line, exits::ret_kind(sig), attrs, name);
                self.sites.push(row);
            }
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

        let row = self.fn_row(site, qualname.clone(), line, ret, attrs, name);
        self.sites.push(row);

        // The focus is read AFTER `classify`, so an `async`/`const`/`extern` fn
        // is never focused (design §2.2), and the LINE sites are minted after
        // this fn's own so that `sites` stays in site-index order. `offset` is
        // the guard's byte: the parameters LINE goes there too and sorts behind
        // it (amendment A6).
        if self.focus.matches(&qualname) {
            lines::walk_body(self, sig, block, &qualname, offset);
            self.focused.push(qualname);
        }
    }

    /// The `Fn` row for one eligible fn item.
    ///
    /// ONE construction, read by both walks (design 2026-09-07 §6): the
    /// emitting walk mints it beside the guard it splices, and the census walk
    /// [`crate::census::walk`] runs mints it with no splice at all. A second
    /// construction for the census is exactly the drift [`crate::fn_items`]
    /// exists to rule out -- a `--focus` the driver accepts and the transform
    /// then ignores.
    fn fn_row(
        &self,
        site: u32,
        qualname: String,
        line: u32,
        ret: RetKind,
        attrs: &[Attribute],
        name: &str,
    ) -> Site {
        Site {
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
            // crate root's, and only the caller knows the root is a binary's --
            // so a census row, whose caller is the resolver, never carries it.
            main: self.is_bin_root && self.scope.is_empty() && name == "main",
        }
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
