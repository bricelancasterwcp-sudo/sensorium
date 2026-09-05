//! Names, lines and spans read off the AST.
//!
//! Everything else in this crate answers with a byte OFFSET; these four answer
//! with the other half of a manifest row -- which line a construct starts on,
//! which token a callee path begins at, and what an `impl` block's self type is
//! called. They live apart from [`crate::visit`] so that the walk itself stays
//! about placement.

use proc_macro2::Span;
use syn::spanned::Spanned;
use syn::Type;

/// The 1-based line a span starts on.
pub(crate) fn line_of(span: Span) -> u32 {
    u32::try_from(span.start().line).unwrap_or(u32::MAX)
}

/// The span of a callee path's FIRST token: `Spanned` on the whole path would
/// answer with a join that is only as good as `proc-macro2`'s, and the line is
/// all this needs.
pub(crate) fn path_span(func: &syn::Expr) -> Span {
    match func {
        syn::Expr::Path(p) => match &p.path.leading_colon {
            Some(c) => c.spans[0],
            None => p.path.segments[0].ident.span(),
        },
        other => other.span(),
    }
}

/// The impl's self type as a bare name: no generic arguments, no path prefix.
pub(crate) fn self_type_name(ty: &Type) -> String {
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
