//! The splicer: `syn` says where the braces, the operands and the spawn callees
//! are, the original bytes are copied through, and newline-free fragments go in
//! at those offsets. The AST is a ruler, never a printer (spec §3.1).
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
//! there (`{` for a body, `]` for an inner attribute, `(` for a call). A future
//! `proc-macro2` that changed what `byte_range()` is relative to would otherwise
//! mis-splice silently, and every measurement downstream of this crate would
//! inherit it.
//!
//! # Order
//!
//! Splices are sorted by offset, then by KIND, because several land on the same
//! byte and only one order is right: an exit wrap's closing `)` before anything
//! that starts there, then the entry guard (a statement, which must precede the
//! block's value), then an exit wrap's opening fragment, then a spawn rewrite,
//! then the crate-root static. Nested wraps close innermost-first. The
//! assembled output is checked for overlap as it is built, so a mis-ordered
//! splice is an error rather than a corrupted file.

use std::cmp::Ordering;
use std::collections::HashMap;
use std::str::FromStr;

use proc_macro2::{Span, TokenStream};
use syn::visit::Visit;

use crate::visit::Ctx;
use crate::{Census, SpawnSite, Transformed};

/// The entry guard. Newline-free, and the ONLY place its text is written.
pub(crate) fn guard_fragment(site: u32) -> String {
    format!("let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, {site});")
}

/// The opening half of an exit wrap; the closing half is [`RET_CLOSE`].
pub(crate) fn ret_open_fragment(site: u32) -> String {
    format!(
        "::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, {site}, |__r| {{ \
         use ::sensorium_rt::probe::*; \
         ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome()) }}, "
    )
}

pub(crate) const RET_CLOSE: &str = ")";

/// The crate root's unit declaration. Newline-free -- which is why a newline in
/// the metadata is escaped rather than passed through: a Rust string literal
/// happily spans lines, and one that did would move every line below it.
fn unit_static(metadata: &str) -> String {
    format!(
        "#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = \
         ::sensorium_rt::Unit::new(\"{}\");",
        escape_string_literal(metadata)
    )
}

/// Escape a string for a one-line Rust string literal.
pub(crate) fn escape_string_literal(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        match ch {
            '\\' => out.push_str(r"\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(ch),
        }
    }
    out
}

/// What a splice is, and what has to happen first when two share a byte.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum Kind {
    /// An exit wrap's `)`. Closes what is already open before anything new.
    Close,
    /// The entry guard: a statement, so ahead of the block's value.
    Guard,
    /// An exit wrap's opening fragment, outside a spawn rewrite at the same byte.
    Open,
    /// A spawn callee replaced in place.
    Replace,
    /// The spawn site string, just past the call's `(`.
    SpawnArg,
    /// The crate root's unit static, past the file's last token.
    Static,
}

#[derive(Debug, Clone)]
pub(crate) struct Splice {
    pub start: usize,
    /// `== start` for an insert; past the replaced bytes otherwise.
    pub end: usize,
    pub kind: Kind,
    /// Emission order, so nested wraps close innermost-first.
    pub seq: usize,
    pub text: String,
}

fn splice_order(a: &Splice, b: &Splice) -> Ordering {
    a.start
        .cmp(&b.start)
        .then(a.kind.cmp(&b.kind))
        .then_with(|| {
            if a.kind == Kind::Close {
                // The wrap opened LAST closes first.
                b.seq.cmp(&a.seq)
            } else {
                a.seq.cmp(&b.seq)
            }
        })
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
    let walked = ctx.finish()?;

    let mut splices = walked.splices;
    let mut appended_line = false;
    if is_crate_root {
        let placement = static_splice(source, prefix, parsed.shebang.is_some());
        appended_line = placement.appended_line;
        splices.push(placement.splice(
            checked_static_offset(source, placement.offset)?,
            unit_metadata,
        ));
    }
    splices.sort_by(splice_order);

    let out = assemble(source, &splices)?;
    check_line_count(source, &out, appended_line)?;

    let mut spawns = walked.spawns;
    spawns.sort_by_key(|(offset, _)| *offset);
    check_spawn_ordinals(&spawns)?;

    Ok(Transformed {
        source: out,
        sites: walked.sites,
        skipped: walked.skipped,
        spawns: spawns.into_iter().map(|(_, s)| s).collect(),
        appended_line,
    })
}

/// Copy the original bytes through, putting each fragment in at its offset and
/// skipping the bytes a replacement covers.
///
/// # Errors
/// Two splices that overlap. They cannot, by construction -- inserts have no
/// width and no two replacements share a byte -- so this is the check that says
/// so rather than corrupting a file if construction is ever wrong.
fn assemble(source: &str, splices: &[Splice]) -> Result<String, syn::Error> {
    let mut out = String::with_capacity(source.len() + splices.len() * 96);
    let mut cut = 0usize;
    for s in splices {
        if s.start < cut {
            return Err(syn::Error::new(
                Span::call_site(),
                format!(
                    "splices overlap at byte {} (a {:?} after a splice ending at {cut}) -- \
                     the transformer would corrupt this file rather than rewrite it",
                    s.start, s.kind
                ),
            ));
        }
        out.push_str(&source[cut..s.start]);
        out.push_str(&s.text);
        cut = s.end;
    }
    out.push_str(&source[cut..]);
    Ok(out)
}

/// Plan decision N4: the ordinals the walk assigned, re-derived from SOURCE
/// ORDER and compared.
///
/// The walk counts in DFS order and N1 promises source order. They agree for
/// every construct the goldens exercise, but "agree" is an argument and this is
/// the measurement: `spawns` arrives sorted by byte offset, so ranking the
/// wrapped sites of one qualname as they are met here IS source order.
///
/// A disagreement costs this unit its instrumentation -- the driver sees the
/// error, marks the unit `fell_back` and names the site -- rather than shipping
/// a task under a name that is not the one the manifest promises.
///
/// # Errors
/// A wrapped site's ordinal is not its rank among the wrapped sites of its
/// qualname.
fn check_spawn_ordinals(spawns: &[(usize, SpawnSite)]) -> Result<(), syn::Error> {
    let mut ranks: HashMap<&str, u32> = HashMap::new();
    for (_, site) in spawns {
        if !site.wrapped {
            continue;
        }
        let rank = ranks.entry(site.qualname.as_str()).or_insert(0);
        *rank += 1;
        if site.ordinal == Some(*rank) {
            continue;
        }
        let walked = site
            .ordinal
            .map_or_else(|| "none".to_owned(), |k| k.to_string());
        return Err(syn::Error::new(
            Span::call_site(),
            format!(
                "spawn ordinal for {} at line {}: walk said #{walked}, source order says #{rank}",
                site.qualname, site.line,
            ),
        ));
    }
    Ok(())
}

/// The promise of `rust/HONESTY.md` §9, enforced where it is made rather than
/// only downstream: a fragment that carried a newline -- an unescaped metadata
/// string, a future fragment written across two lines -- would move every line
/// below it, and every `line!()`, panic location and backtrace frame with them.
///
/// # Errors
/// The output has a different number of lines than `appended_line` accounts
/// for. Refusing here costs one unit a fallback; not refusing costs every
/// measurement that unit contributes to.
fn check_line_count(source: &str, out: &str, appended_line: bool) -> Result<(), syn::Error> {
    let expected = source.lines().count() + usize::from(appended_line);
    if out.lines().count() == expected {
        return Ok(());
    }
    Err(syn::Error::new(
        Span::call_site(),
        format!(
            "the rewrite moved lines: {} in, {} out, appended_line = {appended_line} -- \
             an injected fragment is not newline-free",
            source.lines().count(),
            out.lines().count(),
        ),
    ))
}

pub(crate) fn census(source: &str) -> Census {
    let Ok(parsed) = syn::parse_file(source) else {
        // Four zeros with `parsed: false` -- NOT a measured zero.
        return Census::default();
    };
    let prefix = stripped_prefix_len(source, parsed.shebang.as_deref());
    let mut ctx = Ctx::new(source, prefix, "", 0, false);
    ctx.visit_file(&parsed);
    ctx.census()
}

/// How many bytes `syn::parse_file` removed before `proc-macro2` saw the text.
fn stripped_prefix_len(source: &str, shebang: Option<&str>) -> usize {
    let bom = usize::from(source.starts_with('\u{feff}')) * '\u{feff}'.len_utf8();
    bom + shebang.map_or(0, str::len)
}

/// Where the `__SENSORIUM_UNIT` static goes: immediately after the file's LAST
/// TOKEN -- with two corrections that are not optional.
///
/// Not "on the last line": a file whose last line is `// a comment` would
/// swallow the static. Not "after the final newline" either: that adds a line,
/// which is the one thing this crate exists to avoid.
///
/// The first correction, and it is a silent one: `proc-macro2` hands a `//!` or
/// `///` doc comment back as tokens whose span covers the COMMENT TEXT, not the
/// `#[doc = ".."]` it desugars to. When the last token is one of those, "after
/// the last token" is INSIDE a line comment, and the static is commented out --
/// the file still parses, still has the same line count, and simply has no
/// unit. (A `/*! .. */` doc comment is safe: its span ends after the `*/`.) So
/// when the last token's own text starts with `//`, the static moves past that
/// line's newline instead.
///
/// The second: when that comment runs to EOF with NO newline after it, there is
/// no line to move past, so the fragment carries one. A SHEBANG that runs to
/// EOF is the same shape and takes the same correction -- "after the last
/// token" is the end of the shebang line, and a static appended there is part
/// of the shebang. This is the only fragment this crate ever emits that
/// contains a newline, and it can only ever add a FINAL line -- which is what
/// `appended_line` says.
///
/// `appended_line` is true exactly when the insertion adds a line, which a
/// newline-free fragment does only at EOF in an empty file or after a trailing
/// newline. Every such file has no items, hence no `mod` declarations, hence no
/// other file in its unit, hence no guard anywhere that could reference the
/// static. No existing line moves in any of them.
struct StaticPlacement {
    offset: usize,
    /// The fragment must bring its own newline (see above).
    lead_newline: bool,
    appended_line: bool,
}

fn static_splice(source: &str, prefix: usize, has_shebang: bool) -> StaticPlacement {
    let plain = |offset: usize| StaticPlacement {
        offset,
        lead_newline: false,
        appended_line: adds_a_final_line(source, offset),
    };
    match last_token(&source[prefix..]) {
        Some((end, false)) => plain(prefix + end),
        Some((end, true)) => match source[prefix + end..].find('\n') {
            Some(nl) => plain(prefix + end + nl + 1),
            // The comment runs to EOF with no newline at all, so the static
            // needs one of its own or it is commented out.
            None => StaticPlacement {
                offset: source.len(),
                lead_newline: true,
                appended_line: true,
            },
        },
        // Past the shebang's own newline, so the static cannot land inside it.
        None if source.as_bytes().get(prefix) == Some(&b'\n') => plain(prefix + 1),
        // A shebang with nothing after it at all: no newline to move past, so
        // the fragment brings one rather than becoming part of the shebang.
        None if has_shebang && prefix == source.len() => StaticPlacement {
            offset: source.len(),
            lead_newline: true,
            appended_line: true,
        },
        None => plain(prefix),
    }
}

/// The crate-root static's offset, checked for the one thing every other splice
/// producer checks and this one did not: that it lands on a character boundary.
/// The failure mode without it is a slice panic inside [`assemble`], not the
/// synthesised error the guards in `visit.rs` return.
///
/// # Errors
/// The offset falls inside a UTF-8 character.
fn checked_static_offset(source: &str, offset: usize) -> Result<usize, syn::Error> {
    if source.is_char_boundary(offset) {
        return Ok(offset);
    }
    Err(syn::Error::new(
        Span::call_site(),
        "the crate-root static's offset falls inside a UTF-8 character -- \
         Span::byte_range() is not relative to what this crate assumes",
    ))
}

/// Does inserting a newline-free fragment at `offset` give the file one more
/// line than it had? Only at the very end, and only when the text before it
/// already ended a line -- which includes the empty file, whose zero lines
/// become one.
impl StaticPlacement {
    fn splice(&self, offset: usize, unit_metadata: &str) -> Splice {
        let mut text = unit_static(unit_metadata);
        if self.lead_newline {
            text.insert(0, '\n');
        }
        Splice {
            start: offset,
            end: offset,
            kind: Kind::Static,
            seq: usize::MAX,
            text,
        }
    }
}

fn adds_a_final_line(source: &str, offset: usize) -> bool {
    offset == source.len() && (source.is_empty() || source.ends_with('\n'))
}

/// The end of the file's last token, and whether that token's own text is a
/// `//`-form comment (see [`static_splice`]).
fn last_token(content: &str) -> Option<(usize, bool)> {
    let stream = TokenStream::from_str(content).ok()?;
    // A `Group`'s span covers its delimiters, so this is the closing brace of
    // the final item, not the token before it.
    let last = stream.into_iter().last()?;
    let range = last.span().byte_range();
    let is_line_comment = content
        .get(range.start..range.end)
        .is_some_and(|text| text.starts_with("//"));
    Some((range.end, is_line_comment))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn splice(start: usize, end: usize, kind: Kind, text: &str) -> Splice {
        Splice {
            start,
            end,
            kind,
            seq: 0,
            text: text.to_owned(),
        }
    }

    /// `assemble`'s overlap guard cannot be reached from `transform`: inserts
    /// have no width and no two replacements share a byte. It is still the
    /// difference between a corrupted file and a declared fallback if that ever
    /// stops being true, so it is driven directly rather than asserted.
    #[test]
    fn overlapping_splices_are_refused_rather_than_corrupting_the_file() {
        let source = "std::thread::spawn(f)";
        let good = [
            splice(0, 18, Kind::Replace, "X"),
            splice(19, 19, Kind::SpawnArg, "\"s\", "),
        ];
        assert_eq!(assemble(source, &good).expect("disjoint"), "X(\"s\", f)");

        let bad = [
            splice(0, 18, Kind::Replace, "X"),
            splice(5, 5, Kind::Open, "Y"),
        ];
        let err = assemble(source, &bad).expect_err("a splice inside a replaced range");
        assert!(err.to_string().contains("overlap"), "unhelpful: {err}");
    }

    /// The same guard for two replacements that share a byte.
    #[test]
    fn two_replacements_that_share_a_byte_are_refused() {
        let source = "abcdef";
        let bad = [
            splice(0, 4, Kind::Replace, "X"),
            splice(2, 6, Kind::Replace, "Y"),
        ];
        assert!(assemble(source, &bad).is_err());
    }

    /// The crate-root static is the one splice producer whose offset is not
    /// computed by `visit.rs`'s guarded paths, so its boundary check is driven
    /// directly -- a bad offset there panics in `assemble`'s slicing rather
    /// than returning an error a unit can fall back on.
    #[test]
    fn a_static_offset_inside_a_character_is_refused() {
        let source = "// π\n";
        // `π` is two bytes at 3..5; 4 is inside it.
        assert_eq!(checked_static_offset(source, 3).expect("a boundary"), 3);
        assert_eq!(checked_static_offset(source, 5).expect("a boundary"), 5);
        let err = checked_static_offset(source, 4).expect_err("inside the character");
        assert!(
            err.to_string().contains("UTF-8 character"),
            "unhelpful: {err}"
        );
    }

    fn spawn(offset: usize, qualname: &str, line: u32, ordinal: Option<u32>) -> (usize, SpawnSite) {
        (
            offset,
            SpawnSite {
                file: "src/lib.rs".to_owned(),
                line,
                wrapped: ordinal.is_some(),
                reason: None,
                qualname: qualname.to_owned(),
                ordinal,
            },
        )
    }

    fn declared(offset: usize, qualname: &str, line: u32) -> (usize, SpawnSite) {
        let mut s = spawn(offset, qualname, line, None);
        s.1.wrapped = false;
        s.1.reason = Some("builder");
        s
    }

    /// N4's re-derivation. The walk and the source order agree for every
    /// construct the goldens exercise, so the DISAGREEMENT is built here by
    /// hand -- the check cannot be weakened to make it reachable, and a
    /// disagreement that only ever showed up in the field would ship a task
    /// under the wrong name.
    #[test]
    fn a_walk_assigned_ordinal_that_is_not_the_source_order_rank_is_refused() {
        let good = [
            spawn(10, "a", 3, Some(1)),
            declared(20, "a", 4),
            spawn(30, "a", 5, Some(2)),
            spawn(40, "T::m", 9, Some(1)),
        ];
        check_spawn_ordinals(&good).expect("the ranks the walk assigned");

        // The second site of `a` says #3 where source order says #2.
        let bad = [
            spawn(10, "a", 3, Some(1)),
            declared(20, "a", 4),
            spawn(30, "a", 5, Some(3)),
        ];
        let err = check_spawn_ordinals(&bad).expect_err("a rank that is not the walk's");
        assert_eq!(
            err.to_string(),
            "spawn ordinal for a at line 5: walk said #3, source order says #2"
        );

        // A declared shape that consumed an ordinal would renumber the wrapped
        // sites after it, which is exactly what N1 promises it does not.
        let counted = [spawn(10, "a", 3, Some(1)), spawn(30, "a", 5, Some(3))];
        let err = check_spawn_ordinals(&counted).expect_err("a declared shape was counted");
        assert!(
            err.to_string().contains("spawn ordinal"),
            "unhelpful: {err}"
        );

        // Two files' worth of one qualname never mix here: `Ctx` is per file.
        let per_qualname = [spawn(10, "a", 3, Some(1)), spawn(20, "b", 4, Some(1))];
        check_spawn_ordinals(&per_qualname).expect("each qualname counts from 1");
    }

    /// `check_line_count` is the enforcement of `rust/HONESTY.md` §9 at the
    /// point the promise is made, so it is driven directly too.
    #[test]
    fn a_fragment_that_moved_a_line_is_refused() {
        check_line_count("a\nb\n", "a\nb\n", false).expect("unchanged");
        check_line_count("a\nb\n", "a\nb\nc", true).expect("one appended line");
        let err = check_line_count("a\nb\n", "a\nX\nb\n", false).expect_err("a line was added");
        assert!(err.to_string().contains("moved lines"), "unhelpful: {err}");
    }
}
