//! Golden pairs for the byte-offset splicer.
//!
//! Every `.out.rs` is written with two placeholders so the fragments the
//! transformer emits are pinned HERE, by the test, and not read back out of the
//! implementation that is under test:
//!
//! * `@G(<site>)` -- the entry guard for that site.
//! * `@U`         -- the crate root's `__SENSORIUM_UNIT` static.
//!
//! Change the fragment in the implementation and every golden diff fails, which
//! is the point.

use std::fs;
use std::path::PathBuf;

use sensorium_transform::{census, transform, Transformed};

const META: &str = "d41d8cd98f00b204";
const FILE: &str = "src/lib.rs";

fn guard(site: u32) -> String {
    format!("let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, {site});")
}

fn unit_static(metadata: &str) -> String {
    format!(
        "#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = \
         ::sensorium_rt::Unit::new(\"{metadata}\");"
    )
}

/// Expand `@G(n)` and `@U` in an expected file.
fn expand(template: &str) -> String {
    let mut out = String::with_capacity(template.len() + 256);
    let mut rest = template;
    while let Some(at) = rest.find('@') {
        out.push_str(&rest[..at]);
        let tail = &rest[at..];
        if let Some(after) = tail.strip_prefix("@G(") {
            let close = after.find(')').expect("@G( without )");
            let site: u32 = after[..close].parse().expect("@G( non-numeric site )");
            out.push_str(&guard(site));
            rest = &after[close + 1..];
        } else if let Some(after) = tail.strip_prefix("@U") {
            out.push_str(&unit_static(META));
            rest = after;
        } else {
            out.push('@');
            rest = &tail[1..];
        }
    }
    out.push_str(rest);
    out
}

fn golden_path(case: &str, ext: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/golden")
        .join(format!("{case}.{ext}.rs"))
}

fn read(case: &str, ext: &str) -> String {
    let path = golden_path(case, ext);
    fs::read_to_string(&path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()))
}

/// Run one golden case and assert the three invariants every case shares:
/// exact output, line count preserved, result re-parses.
fn run(case: &str, first_site: u32, is_crate_root: bool) -> Transformed {
    let input = read(case, "in");
    let expected = expand(&read(case, "out"));
    let t = transform(&input, FILE, META, first_site, is_crate_root)
        .unwrap_or_else(|e| panic!("{case}: transform failed: {e}"));

    assert_eq!(t.source, expected, "{case}: transformed source differs");
    assert_eq!(
        t.source.lines().count(),
        input.lines().count(),
        "{case}: line count moved"
    );
    syn::parse_file(&t.source)
        .unwrap_or_else(|e| panic!("{case}: transformed source does not re-parse: {e}"));
    t
}

fn sites(t: &Transformed) -> Vec<(u32, &str, u32)> {
    t.sites
        .iter()
        .map(|s| (s.site, s.qualname.as_str(), s.firstlineno))
        .collect()
}

fn skips(t: &Transformed) -> Vec<(&str, u32, &str)> {
    t.skipped
        .iter()
        .map(|s| (s.qualname.as_str(), s.line, s.reason))
        .collect()
}

// ---------------------------------------------------------------------------
// The twelve cases the brief names, plus the four the brief's edge cases imply.
// ---------------------------------------------------------------------------

#[test]
fn free_fn() {
    let t = run("free_fn", 7, false);
    assert_eq!(sites(&t), [(7, "add", 3), (8, "main_ish", 7)]);
    assert!(t.skipped.is_empty());
    assert!(t.sites.iter().all(|s| s.file == FILE));
}

#[test]
fn impl_method() {
    let t = run("impl_method", 7, false);
    assert_eq!(
        sites(&t),
        [
            (7, "Counter::new", 6),
            (8, "Counter::bump", 10),
            // `impl<T> Holder<T>` renders as the bare self type: no generics
            // (the ident never carries them) ...
            (9, "Holder::push", 21),
            // ... and `impl self::deep::Nested` drops the path, which the
            // generic case cannot pin -- Python's `Type::method` (spec §5.4).
            (10, "Nested::pathed", 31),
        ]
    );
}

#[test]
fn trait_default() {
    let t = run("trait_default", 7, false);
    // `fn name(&self) -> String;` has no body: not a site, and not a skip
    // either -- there is nothing there to instrument or to excuse.
    assert_eq!(sites(&t), [(7, "Greeter::greet", 4)]);
    assert!(t.skipped.is_empty());
}

#[test]
fn nested_mod() {
    let t = run("nested_mod", 7, false);
    assert_eq!(
        sites(&t),
        [(7, "outer::top", 2), (8, "outer::inner::deep", 5)]
    );
}

#[test]
fn const_fn_is_skipped() {
    let t = run("const_fn", 7, false);
    assert_eq!(sites(&t), [(7, "runtime", 9)]);
    assert_eq!(skips(&t), [("limit", 1, "const"), ("doubled", 5, "const")]);
}

#[test]
fn extern_fn_is_skipped() {
    let t = run("extern_fn", 7, false);
    assert_eq!(sites(&t), [(7, "ordinary", 10)]);
    // The `fn abs(..);` inside `extern "C" { .. }` has no body at all, so it is
    // neither instrumented nor excused; only the `extern "C" fn` with a body is.
    assert_eq!(skips(&t), [("callback", 2, "extern")]);
}

#[test]
fn generic_fn() {
    let t = run("generic_fn", 7, false);
    // `where_clause`'s brace is on line 10; `firstlineno` is the `fn` keyword.
    assert_eq!(sites(&t), [(7, "show", 3), (8, "where_clause", 7)]);
}

#[test]
fn unsafe_fn() {
    let t = run("unsafe_fn", 7, false);
    assert_eq!(sites(&t), [(7, "raw", 1), (8, "later", 5)]);
    assert_eq!(skips(&t), [("frozen", 9, "const")]);
}

#[test]
fn body_starting_with_an_attribute_or_doc_comment() {
    let t = run("body_attr", 7, false);
    assert_eq!(
        sites(&t),
        [
            (7, "with_inner_stmt_attr", 1),
            (8, "with_doc_on_first_item", 7)
        ]
    );
}

#[test]
fn empty_body() {
    let t = run("empty_body", 7, false);
    assert_eq!(
        sites(&t),
        [(7, "nothing", 3), (8, "Empty::also_nothing", 6)]
    );
}

#[test]
fn one_line_body() {
    let t = run("one_line_body", 7, false);
    assert_eq!(sites(&t), [(7, "f", 1), (8, "g", 3)]);
}

#[test]
fn test_fn() {
    let t = run("test_fn", 7, false);
    assert_eq!(
        sites(&t),
        [
            (7, "under_test", 1),
            (8, "tests::setup", 9),
            (9, "tests::it_works", 14),
        ]
    );
}

#[test]
fn inner_attribute_at_body_start() {
    // `#![..]` must stay the first thing in the block: a guard spliced ahead of
    // it is E0752-class garbage rustc rejects, which would show up as an E2
    // fallback rather than as the transformer bug it is.
    let t = run("inner_attr", 7, false);
    assert_eq!(
        sites(&t),
        [(7, "with_inner_attr", 1), (8, "two_inner_attrs", 7)]
    );
}

#[test]
fn nested_fn_and_impl_inside_a_fn_body() {
    let t = run("nested_fn", 7, false);
    assert_eq!(
        sites(&t),
        [
            (7, "outer", 1),
            (8, "outer::helper", 2),
            (9, "outer::Local::method", 9),
        ]
    );
}

#[test]
fn macro_rules_body_is_skipped() {
    let t = run("macro_rules", 7, false);
    assert_eq!(sites(&t), [(7, "ordinary", 11)]);
    assert_eq!(skips(&t), [("make_fn!", 3, "macro")]);
}

#[test]
fn shebang_and_non_ascii_offsets() {
    // `syn::parse_file` strips the BOM and the shebang before `proc-macro2`
    // ever sees the text, so every span offset is short by that prefix; and
    // `Span::start().column` counts CHARS, not bytes. Either mistake mis-splices
    // this file.
    let t = run("shebang_utf8", 7, false);
    assert_eq!(sites(&t), [(7, "ünïcödé", 4), (8, "after", 8)]);
}

// ---------------------------------------------------------------------------
// The crate-root static
// ---------------------------------------------------------------------------

#[test]
fn crate_root_static_lands_after_the_last_token() {
    // The file's last LINE is a comment. Appending there would comment the
    // static out; appending after the final newline would add a line. The last
    // TOKEN is the only point that is both.
    let t = run("crate_root", 7, true);
    assert_eq!(sites(&t), [(7, "root_fn", 3)]);
    assert!(t
        .source
        .contains("}#[doc(hidden)] pub static __SENSORIUM_UNIT"));
    assert!(t
        .source
        .ends_with("// Another one, and then a blank line.\n\n"));
}

#[test]
fn a_non_root_file_gets_no_static() {
    let input = read("crate_root", "in");
    let t = transform(&input, FILE, META, 7, false).expect("transform");
    assert!(
        !t.source.contains("pub static __SENSORIUM_UNIT"),
        "only the crate root declares the unit"
    );
    assert_eq!(t.source.lines().count(), input.lines().count());
}

#[test]
fn a_file_with_no_tokens_takes_the_static_at_offset_zero() {
    // No tokens means no inner attributes to displace, so the head of the file
    // is safe -- and it keeps the line count, which appending would not.
    let t = transform("// nothing here\n", FILE, META, 0, true).expect("transform");
    assert_eq!(t.source, format!("{}// nothing here\n", unit_static(META)));
    assert_eq!(t.source.lines().count(), 1);
    syn::parse_file(&t.source).expect("re-parses");
}

#[test]
fn an_empty_crate_root_is_the_one_documented_line_count_exception() {
    let t = transform("", FILE, META, 0, true).expect("transform");
    assert_eq!(t.source, unit_static(META));
    assert_eq!("".lines().count(), 0);
    assert_eq!(t.source.lines().count(), 1);
}

#[test]
fn the_metadata_is_escaped_into_the_static() {
    let t = transform("fn f() {}\n", FILE, "a\"b\\c", 0, true).expect("transform");
    assert!(
        t.source.contains(r#"Unit::new("a\"b\\c")"#),
        "got: {}",
        t.source
    );
    syn::parse_file(&t.source).expect("re-parses");
}

#[test]
fn a_newline_in_the_metadata_cannot_move_a_line() {
    // A Rust string literal spans lines happily, so an unescaped newline here
    // would push every line below the static down by one.
    let input = "fn f() {}\n";
    let t = transform(input, FILE, "a\nb\r\tc", 0, true).expect("transform");
    assert!(
        t.source.contains(r#"Unit::new("a\nb\r\tc")"#),
        "got: {}",
        t.source
    );
    assert_eq!(t.source.lines().count(), input.lines().count());
    syn::parse_file(&t.source).expect("re-parses");
}

// ---------------------------------------------------------------------------
// Offsets under byte-vs-char and line-ending hazards
// ---------------------------------------------------------------------------

#[test]
fn crlf_line_endings_keep_their_offsets() {
    let input = "fn f() -> u8 {\r\n    1\r\n}\r\n";
    let t = transform(input, FILE, META, 3, false).expect("transform");
    assert_eq!(
        t.source,
        format!("fn f() -> u8 {{{}\r\n    1\r\n}}\r\n", guard(3))
    );
    assert_eq!(t.source.lines().count(), input.lines().count());
}

#[test]
fn a_byte_order_mark_shifts_every_offset() {
    let input = "\u{feff}fn f() {}\n";
    let t = transform(input, FILE, META, 3, false).expect("transform");
    assert_eq!(t.source, format!("\u{feff}fn f() {{{}}}\n", guard(3)));
}

// ---------------------------------------------------------------------------
// Numbering
// ---------------------------------------------------------------------------

#[test]
fn sites_are_contiguous_from_first_site_in_source_order() {
    let input = read("test_fn", "in");
    let t = transform(&input, FILE, META, 1000, false).expect("transform");
    let got: Vec<u32> = t.sites.iter().map(|s| s.site).collect();
    assert_eq!(got, [1000, 1001, 1002]);
    let lines: Vec<u32> = t.sites.iter().map(|s| s.firstlineno).collect();
    assert!(
        lines.windows(2).all(|w| w[0] <= w[1]),
        "sites must be in source order, got {lines:?}"
    );
}

#[test]
fn a_site_index_past_24_bits_is_refused() {
    let input = read("free_fn", "in");
    // The first fn fits at 0x00FF_FFFF; the second would be 0x0100_0000, which
    // the runtime's `site` field cannot carry -- it would silently alias unit 1.
    let err = transform(&input, FILE, META, 0x00FF_FFFF, false)
        .expect_err("a 25-bit site index must be refused, not truncated");
    assert!(
        err.to_string().contains("site index"),
        "unhelpful error: {err}"
    );
    // One site exactly at the ceiling is fine.
    let t = transform("fn f() {}\n", FILE, META, 0x00FF_FFFF, false).expect("ceiling is legal");
    assert_eq!(t.sites[0].site, 0x00FF_FFFF);
}

// ---------------------------------------------------------------------------
// Census (E2's denominator)
// ---------------------------------------------------------------------------

#[test]
fn census_counts_const_and_extern_as_disjoint_subsets() {
    let c = census(&read("const_fn", "in"));
    assert!(c.parsed);
    assert_eq!((c.fn_items, c.const_fns, c.extern_fns), (3, 2, 0));
    assert_eq!(c.eligible(), 1);

    let c = census(&read("extern_fn", "in"));
    assert_eq!((c.fn_items, c.const_fns, c.extern_fns), (2, 0, 1));
    assert_eq!(c.eligible(), 1);

    // `const unsafe fn frozen` is const AND has no abi; `async fn` is ordinary.
    let c = census(&read("unsafe_fn", "in"));
    assert_eq!((c.fn_items, c.const_fns, c.extern_fns), (3, 1, 0));

    // A bodiless trait fn is not a fn item for this purpose.
    let c = census(&read("trait_default", "in"));
    assert_eq!((c.fn_items, c.const_fns, c.extern_fns), (1, 0, 0));

    // A `const extern "C" fn` is counted once, as const, so `eligible()` never
    // subtracts it twice.
    let c = census("const extern \"C\" fn both() {}\n");
    assert_eq!((c.fn_items, c.const_fns, c.extern_fns), (1, 1, 0));
    assert_eq!(c.eligible(), 0);
}

#[test]
fn the_census_agrees_with_what_was_instrumented() {
    for case in [
        "free_fn",
        "impl_method",
        "trait_default",
        "nested_mod",
        "const_fn",
        "extern_fn",
        "generic_fn",
        "unsafe_fn",
        "body_attr",
        "empty_body",
        "one_line_body",
        "test_fn",
        "inner_attr",
        "nested_fn",
        "macro_rules",
        "crate_root",
    ] {
        let input = read(case, "in");
        let c = census(&input);
        let t = transform(&input, FILE, META, 0, false).expect("transform");
        assert!(c.parsed, "{case}: census must report parsed");
        assert_eq!(
            c.eligible(),
            t.sites.len(),
            "{case}: E2's numerator and denominator must come from the same parser"
        );
    }
}

#[test]
fn an_unparseable_file_censuses_as_not_measured_not_as_zero() {
    let c = census("fn f( {");
    assert!(!c.parsed);
    assert_eq!((c.fn_items, c.const_fns, c.extern_fns), (0, 0, 0));
    assert!(transform("fn f( {", FILE, META, 0, false).is_err());
}
