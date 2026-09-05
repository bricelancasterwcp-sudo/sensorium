//! Two token-level readings the walk needs and `splice.rs` shares: where one
//! inner attribute ENDS, and which lines inside a `macro_rules!` body hold a
//! `fn` token.
//!
//! They live here rather than in [`crate::visit`] because that file carries the
//! walk itself and is at the 800-line ceiling; neither is about the walk's
//! state, and both are pure functions of the tokens they are handed.

use proc_macro2::{Span, TokenStream, TokenTree};
use syn::Attribute;

/// The byte offset just past one inner attribute.
///
/// Three forms reach here, and only the first ends on a `]`:
///
/// * `#![allow(..)]` -- a real attribute; the span covers the brackets.
/// * `//! doc` -- `syn` reports a doc comment as an `AttrStyle::Inner`
///   attribute whose bracket span covers the COMMENT TEXT. Its end is inside a
///   line comment, so the caller moves past that line's newline; the fragment
///   is still newline-free and the line count still holds. Both forms are legal
///   Rust and both appear in real code, so rejecting the file (which is what
///   requiring `]` did) is not an option.
/// * `/*! doc */` -- the same, except the span already ends after the `*/`.
///
/// # Errors
/// The span is not a byte range of the source, an unterminated line doc
/// comment (there is no next line to move onto), or an attribute that does not
/// end where its span says.
pub(crate) fn inner_attr_end(
    source: &str,
    prefix: usize,
    attr: &Attribute,
) -> Result<usize, &'static str> {
    let start = prefix + attr.bracket_token.span.join().byte_range().start;
    let end = prefix + attr.bracket_token.span.close().byte_range().end;
    let Some(text) = source.get(start..end) else {
        return Err("inner attribute span is not a byte range of the source");
    };
    if text.starts_with("//") {
        // Past the comment's own newline.
        return match source[end..].find('\n') {
            Some(nl) => Ok(end + nl + 1),
            None => Err("inner line doc comment is not terminated by a newline"),
        };
    }
    if text.starts_with("/*") {
        return Ok(end);
    }
    if end == 0 || source.as_bytes().get(end - 1) != Some(&b']') {
        return Err("inner attribute does not end where its span says");
    }
    Ok(end)
}

/// Lines of `fn` tokens inside a macro body, skipping fn-POINTER types
/// (`fn(u8) -> u8`), whose `fn` is followed by `(`.
pub(crate) fn scan_macro_fns(tokens: &TokenStream, out: &mut Vec<u32>) {
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
