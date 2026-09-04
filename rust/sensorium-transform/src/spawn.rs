//! Thread-spawning shapes: the one that is rewritten, and the ones that are
//! declared instead.
//!
//! Rung 1 measured the hole this closes: in a bloomery `--lib` trace, 4 of 57
//! emitting non-main threads carried no name at all, because nothing names a
//! thread a test spawns (findings §5.20). `::sensorium_rt::spawn_child` is what
//! names them, and it is a drop-in for `std::thread::spawn` -- same bounds, same
//! `JoinHandle`, same panic propagation, and literally `std::thread::spawn`
//! again when the recorder is not recording.
//!
//! # Rewritten
//!
//! A CALL whose callee is a PATH ending in `thread::spawn` (at least two
//! segments, so `std::thread::spawn` and `thread::spawn` match and a bare
//! `spawn` does not) and which takes exactly one argument. Two splices, both
//! newline-free: the callee path becomes `::sensorium_rt::spawn_child`, and the
//! site argument goes in just past the call's `(`. The bytes BETWEEN the path
//! and the paren are left exactly as they were, so a comment or a newline there
//! survives -- which one splice covering both could not promise.
//!
//! **The site argument keeps the callee's import alive.** Replacing
//! `thread::spawn` deletes the file's only use of a `use std::thread;`, and
//! rustc then reports `unused_imports` -- a NEW diagnostic, which
//! `rust/HONESTY.md` §9 promises there are none of, and a hard error under a
//! workspace's own `#![deny(warnings)]`. Measured on rustc 1.96, 2026-09-02, by
//! `tests/oracle.rs`, which is what caught it. So when the callee path could
//! name an import -- anything not rooted at the `std` crate -- the site argument
//! is a block that re-states it:
//!
//! ```ignore
//! ::sensorium_rt::spawn_child({ #[allow(unused_imports)] use thread::spawn as _; "src/a.rs:11" }, f)
//! ```
//!
//! `as _` binds no name, the `use` is an item and costs nothing at runtime, and
//! the path is rendered from the syn `Path`'s IDENTS (never the source bytes),
//! so it can carry no newline and no turbofish. A `std::`-rooted path names the
//! crate, not an import, and gets the plain string the plan wrote.
//!
//! # Declared, not rewritten (`rust/HONESTY.md` §3)
//!
//! * `"builder"` -- a one-argument `.spawn(f)` whose receiver chain mentions
//!   `Builder`. It returns `io::Result<JoinHandle<T>>` and carries a name of its
//!   own, so it is a different function, not a different spelling.
//! * `"scoped"` -- a call of `thread::scope`. It spawns nothing itself; the
//!   `.spawn` inside it is the next case.
//! * `"method"` -- any other one-argument `.spawn(f)`, which is what
//!   `scope.spawn(f)` is.
//! * `"arity"` -- a path ending in `thread::spawn` taking a number of arguments
//!   `std::thread::spawn` does not. Valid code cannot contain one; it is listed
//!   rather than dropped so that nothing the suffix rule matched is ever
//!   silently ignored.
//!
//! A `.spawn()` with NO argument is `std::process::Command::spawn` (or another
//! zero-argument method of that name). It is not a thread, and listing it would
//! put a lie in the manifest, so it is not a spawn shape at all.

use syn::{Expr, ExprCall, ExprMethodCall};

/// Where a rewritten spawn's two splices go, as RAW `Span::byte_range()`
/// offsets.
#[derive(Debug, Clone)]
pub(crate) struct Rewrite {
    /// The callee path's first byte.
    pub path_start: usize,
    /// Just past the callee path's last byte.
    pub path_end: usize,
    /// Just past the call's opening `(`.
    pub paren_open_end: usize,
    /// Its opening `(`'s first byte, which the caller checks against the source.
    pub paren_open_start: usize,
    /// The callee path, rendered from its idents, when replacing it could
    /// orphan an import (see the module docs). `None` for a `std::`-rooted path.
    pub use_path: Option<String>,
}

/// One spawn shape the file contains.
#[derive(Debug, Clone)]
pub(crate) enum Shape {
    /// Rewrite the callee and give the child a name.
    Rewrite(Rewrite),
    /// Leave it alone and say why.
    Declare(&'static str),
}

/// The fragment the callee path is replaced with. Newline-free, and the only
/// place its text is written.
pub(crate) const CALLEE: &str = "::sensorium_rt::spawn_child";

/// The site argument the rewritten callee is given, spliced just past the `(`.
/// The file path is escaped: a workspace path with a quote or a backslash in it
/// must not end the literal early, and a newline in one must not move a line.
pub(crate) fn site_argument(file: &str, line: u32, use_path: Option<&str>) -> String {
    let site = format!("\"{}:{line}\"", crate::splice::escape_string_literal(file));
    match use_path {
        None => format!("{site}, "),
        Some(path) => {
            format!("{{ #[allow(unused_imports)] use {path} as _; {site} }}, ")
        }
    }
}

/// Classify a path call: `std::thread::spawn(f)`, or `thread::scope(..)`.
pub(crate) fn classify_call(call: &ExprCall) -> Option<Shape> {
    let Expr::Path(p) = call.func.as_ref() else {
        return None;
    };
    if p.qself.is_some() {
        // `<T as Trait>::..` is not a module path and cannot be `thread::spawn`.
        return None;
    }
    let segments = &p.path.segments;
    let n = segments.len();
    if n < 2 {
        return None;
    }
    let last = segments[n - 1].ident.to_string();
    let parent = &segments[n - 2].ident;
    if parent != "thread" {
        return None;
    }
    match last.as_str() {
        "spawn" if call.args.len() == 1 => {
            let path = p.path.span_range();
            let open = call.paren_token.span.open().byte_range();
            Some(Shape::Rewrite(Rewrite {
                path_start: path.0,
                path_end: path.1,
                paren_open_start: open.start,
                paren_open_end: open.end,
                use_path: import_path(&p.path),
            }))
        }
        "spawn" => Some(Shape::Declare("arity")),
        "scope" => Some(Shape::Declare("scoped")),
        _ => None,
    }
}

/// Classify a method call: `Builder::new()..spawn(f)`, `scope.spawn(f)`.
pub(crate) fn classify_method_call(call: &ExprMethodCall) -> Option<Shape> {
    if call.method != "spawn" || call.args.len() != 1 {
        return None;
    }
    if mentions_builder(&call.receiver) {
        return Some(Shape::Declare("builder"));
    }
    Some(Shape::Declare("method"))
}

/// Does the receiver chain name `Builder` anywhere? `thread::Builder::new()`,
/// `Builder::new().name(..).stack_size(..)` and every intermediate step of such
/// a chain all answer yes.
fn mentions_builder(receiver: &Expr) -> bool {
    match receiver {
        Expr::Path(p) => p.path.segments.iter().any(|s| s.ident == "Builder"),
        Expr::Call(c) => mentions_builder(&c.func),
        Expr::MethodCall(m) => mentions_builder(&m.receiver),
        Expr::Paren(p) => mentions_builder(&p.expr),
        Expr::Group(g) => mentions_builder(&g.expr),
        Expr::Try(t) => mentions_builder(&t.expr),
        Expr::Reference(r) => mentions_builder(&r.expr),
        _ => false,
    }
}

/// The `use` path that keeps this callee's import alive, or `None` when the
/// path is rooted at the `std` crate and so names no import.
///
/// Rendered from the idents, never from the source bytes: a `use` path takes no
/// turbofish, and a rendered one can carry no newline.
fn import_path(path: &syn::Path) -> Option<String> {
    let first = path.segments.first()?;
    if first.ident == "std" {
        return None;
    }
    let mut out = String::new();
    if path.leading_colon.is_some() {
        out.push_str("::");
    }
    for (i, seg) in path.segments.iter().enumerate() {
        if i > 0 {
            out.push_str("::");
        }
        out.push_str(&seg.ident.to_string());
    }
    Some(out)
}

/// The byte range of a `Path`, without going through `Spanned` -- a path's own
/// first and last tokens, so a leading `::` is included and a following `(` is
/// not.
trait PathRange {
    fn span_range(&self) -> (usize, usize);
}

impl PathRange for syn::Path {
    fn span_range(&self) -> (usize, usize) {
        let start = match &self.leading_colon {
            Some(c) => c.spans[0].byte_range().start,
            None => self.segments[0].ident.span().byte_range().start,
        };
        let last = self.segments.last().expect("a path has a segment");
        let end = if matches!(last.arguments, syn::PathArguments::None) {
            last.ident.span().byte_range().end
        } else {
            // A turbofish (`thread::spawn::<F, T>`) is part of the callee and
            // has to go with it, so the whole segment's span is the end.
            use syn::spanned::Spanned;
            last.span().byte_range().end
        };
        (start, end)
    }
}
