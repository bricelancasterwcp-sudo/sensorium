//! The rules no golden PAIR can hold: what the crate-root static does on files
//! whose whole content is comments, how offsets survive a BOM and CRLF endings,
//! where site numbering stops, and the census that is E2's denominator.
//!
//! These are here rather than in `golden.rs` because their inputs are one-line
//! strings: a `.in.rs`/`.out.rs` pair for `""` would be a file that is not
//! there.

mod common;

use std::collections::BTreeMap;

use common::{partials, read, top_level_unit_static, FILE, META};

use sensorium_transform::{census, transform, SiteKind, SpawnSite, MAX_SITE_INDEX};

// ---------------------------------------------------------------------------
// The crate-root static, off the golden files
// ---------------------------------------------------------------------------

#[test]
fn a_trailing_block_doc_comment_still_takes_the_static_in_place() {
    // A `/*! .. */` crate doc is safe -- its span already ends after the `*/`.
    // A `/*! .. */` IS an inner attribute, so the `allow` sits just past its
    // `*/` -- on the line that was already there.
    let t = transform("/*! Crate docs. */\n", FILE, META, 0, true).expect("transform");
    assert_eq!(
        t.source,
        format!(
            "/*! Crate docs. */{}{}\n",
            common::CRATE_ALLOW,
            common::unit_static(META)
        )
    );
    assert!(!t.appended_line);
    assert!(top_level_unit_static(&t.source));
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
    // A `//` comment is not a token at all, so there is no first token for the
    // `allow` to sit in front of: it rides on the static's own fragment, which
    // is legal because a file with no tokens has no items either.
    let t = transform("// nothing here\n", FILE, META, 0, true).expect("transform");
    assert_eq!(
        t.source,
        format!("{}// nothing here\n", common::unit_static_with_allow(META))
    );
    assert_eq!(t.source.lines().count(), 1);
    syn::parse_file(&t.source).expect("re-parses");
}

#[test]
fn an_empty_crate_root_is_the_one_documented_line_count_exception() {
    let t = transform("", FILE, META, 0, true).expect("transform");
    assert_eq!(t.source, common::unit_static_with_allow(META));
    assert_eq!("".lines().count(), 0);
    assert_eq!(t.source.lines().count(), 1);
    assert!(t.appended_line);
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
        format!(
            "fn f() -> u8 {{{}\r\n    {}1)\r\n}}\r\n",
            common::guard(3),
            common::ret_open(3)
        )
    );
    assert_eq!(t.source.lines().count(), input.lines().count());
}

#[test]
fn a_byte_order_mark_shifts_every_offset() {
    let input = "\u{feff}fn f() -> u8 { 1 }\n";
    let t = transform(input, FILE, META, 3, false).expect("transform");
    assert_eq!(
        t.source,
        format!(
            "\u{feff}fn f() -> u8 {{{} {}1) }}\n",
            common::guard(3),
            common::ret_open(3)
        )
    );
}

#[test]
fn the_spawn_site_string_is_the_qualname_and_ordinal_not_the_path() {
    // The site string names the TASK, not the location: the enclosing fn item's
    // qualname of the enclosing NAMED ITEM and its ordinal (N1). The file path
    // is not in it -- the manifest's `spawns` entry keeps that -- so a path with
    // a quote or a backslash in it cannot reach the literal at all.
    let t = transform(
        "fn f() { std::thread::spawn(|| ()); }\n",
        "src\\a\"b.rs",
        META,
        0,
        false,
    )
    .expect("transform");
    // Asserted FIRST, and on a substring BOTH spellings share, so an unescaped
    // leak (`a"b.rs`) is caught as well as an escaped one (`a\\"b.rs`) -- and
    // so this is the assertion that reports when a path reaches the source at
    // all.
    assert!(
        !t.source.contains("b.rs"),
        "the path is not baked into the rewritten source: {}",
        t.source
    );
    assert!(
        t.source.contains(r#"spawn_child("f#1", "#),
        "got: {}",
        t.source
    );
    // It is still what the manifest's entry says, spelled as the caller gave it.
    assert_eq!(t.spawns[0].file, "src\\a\"b.rs");
    assert_eq!(t.spawns[0].qualname, "f");
    assert_eq!(t.spawns[0].ordinal, Some(1));
    syn::parse_file(&t.source).expect("re-parses");
}

/// A spawn whose innermost scope is a CONTAINER -- a `mod`, an `impl`, a
/// `trait` -- has no named item to belong to, and is refused rather than named
/// after the container (which would share a counter with an unrelated fn of the
/// same name).
///
/// Fix round 1 ruled this branch "unreachable in valid Rust". It is not, and
/// this test is the falsifier: both shapes below compile on rustc 1.96 with
/// `-D warnings`, and both put an expression inside a `mod` body with no fn,
/// `const` or `static` frame between it and the `mod` -- an enum DISCRIMINANT
/// and an array LENGTH in a struct field's type. So the branch is measured
/// here rather than assumed away, and the cost is stated: one file's
/// instrumentation, not a task named `m#1`.
#[test]
fn a_spawn_with_no_enclosing_named_item_is_refused_not_named_after_the_container() {
    let discriminant = "pub mod m {\n\
                        pub enum E {\n\
                        A = { let f: fn() = || { std::thread::spawn(|| ()).join().unwrap(); }; \
                        let _ = f; 1 },\n\
                        }\n\
                        }\n";
    let array_len = "pub mod m {\n\
                     pub struct S {\n\
                     pub a: [u8; { let f: fn() = || { std::thread::spawn(|| ()).join().unwrap(); }; \
                     let _ = f; 2 }],\n\
                     }\n\
                     }\n";
    for (what, source) in [("discriminant", discriminant), ("array length", array_len)] {
        syn::parse_file(source).unwrap_or_else(|e| panic!("{what} is not valid Rust: {e}"));
        let err = transform(source, FILE, META, 0, false)
            .err()
            .unwrap_or_else(|| panic!("{what}: a spawn inside `mod m` must not be named `m#1`"));
        assert_eq!(
            err.to_string(),
            "spawn site outside any named item",
            "{what}"
        );
    }
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

    // `const unsafe fn frozen` is const AND has no abi; `async fn later` is a
    // fourth, disjoint bucket that `eligible()` does NOT subtract.
    let c = census(&read("unsafe_fn", "in"));
    assert_eq!(
        (c.fn_items, c.const_fns, c.extern_fns, c.async_fns),
        (3, 1, 0, 1)
    );
    assert_eq!(c.eligible(), 2, "eligible() must not subtract async");

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
    for case in common::CASES {
        let input = read(case, "in");
        let c = census(&input);
        let t = transform(&input, FILE, META, 0, false).expect("transform");
        assert!(c.parsed, "{case}: census must report parsed");
        // `eligible()` is E2 as pre-registered (const and extern only), so the
        // identity carries the async skip explicitly rather than by moving the
        // denominator under it.
        let fn_sites = t.sites.iter().filter(|s| s.kind == SiteKind::Fn).count();
        assert_eq!(
            c.eligible(),
            fn_sites + c.async_fns,
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

#[test]
fn a_trailing_line_doc_comment_with_no_newline_gets_one_rather_than_swallowing_the_static() {
    // "After the last token" is inside the comment, and there is no newline to
    // move past. The static brings one -- the only fragment this crate emits
    // that contains a newline, and it can only ever add a FINAL line.
    let t = transform("//! docs", FILE, META, 0, true).expect("transform");
    assert_eq!(
        t.source,
        format!("//! docs\n{}", common::unit_static_with_allow(META))
    );
    assert!(t.appended_line);
    assert!(
        top_level_unit_static(&t.source),
        "the static must not be commented out: {}",
        t.source
    );
    assert_eq!(t.source.lines().count(), "//! docs".lines().count() + 1);
}

#[test]
fn a_shebang_only_crate_root_reports_the_line_it_gains() {
    let input = "#!/usr/bin/env run-cargo-script\n";
    let t = transform(input, FILE, META, 0, true).expect("transform");
    assert!(t.appended_line, "the static lands past the final newline");
    assert_eq!(
        t.source.lines().count(),
        input.lines().count() + 1,
        "and `appended_line` is what accounts for it"
    );
    assert!(top_level_unit_static(&t.source));
}

#[test]
fn a_file_that_ends_without_a_newline_gains_no_line() {
    let input = "fn f() {}";
    let t = transform(input, FILE, META, 0, true).expect("transform");
    assert!(!t.appended_line);
    assert_eq!(t.source.lines().count(), input.lines().count());
}

#[test]
fn a_shebang_with_no_trailing_newline_gets_one_rather_than_swallowing_the_static() {
    // The same shape as the trailing `//!` above: "after the last token" is the
    // end of the shebang LINE, and a static appended there becomes part of the
    // shebang -- the file parses, the line count holds, and the unit is gone.
    let input = "#!/usr/bin/env run-cargo-script";
    let t = transform(input, FILE, META, 0, true).expect("transform");
    assert_eq!(
        t.source,
        format!("{input}\n{}", common::unit_static_with_allow(META))
    );
    assert!(t.appended_line);
    assert!(
        top_level_unit_static(&t.source),
        "the static must be a real item, not part of the shebang: {}",
        t.source
    );
    assert_eq!(t.source.lines().count(), input.lines().count() + 1);
}

// ---------------------------------------------------------------------------
// The `?` counts (E2''s denominator and the `partial` blind spot beside it)
// ---------------------------------------------------------------------------

#[test]
fn census_counts_every_syn_visible_question_mark_wherever_it_sits() {
    let src = "\
fn tail() -> Result<u8, u8> { Ok(one()?) }
fn stmt() -> Result<u8, u8> { let v = one()?; Ok(v) }
fn closure() -> Result<u8, u8> {
    let f = |x: u8| -> Result<u8, u8> { Ok(chain(x)?) };
    f(1)
}
fn nested() -> Result<u8, u8> {
    fn inner() -> Result<u8, u8> { Ok(one()?) }
    inner()
}
";
    let c = census(src);
    assert!(c.parsed);
    // A tail, a `let`, one inside a CLOSURE and one inside a NESTED fn: the
    // count is of nodes the walk met, not of fn bodies it entered.
    assert_eq!(c.try_syn, 4);
    assert_eq!(c.try_macro_tokens, 0);
    assert_eq!(c.fn_items, 5, "the closure is not a fn item; `inner` is");
}

#[test]
fn a_question_mark_inside_a_macro_invocation_is_a_token_and_never_a_node() {
    // `syn` hands a macro invocation an opaque token stream, so there is no
    // `ExprTry` here at all -- which is exactly why `partial` exists.
    let stmt = census("fn f() { println!(\"{}\", one()?); }\n");
    assert_eq!((stmt.try_syn, stmt.try_macro_tokens), (0, 1));

    let expr = census("fn f() -> u8 { ok(assert_ok!(two()?)) }\n");
    assert_eq!((expr.try_syn, expr.try_macro_tokens), (0, 1));

    // Item position counts too: the tokens are just as opaque there.
    let item = census("some_macro!(f()?);\nfn g() {}\n");
    assert!(item.parsed);
    assert_eq!((item.try_syn, item.try_macro_tokens), (0, 1));

    // And a `?` in a macro argument does not stop the walk seeing a real one
    // beside it.
    let both = census("fn f() -> Result<u8, u8> { println!(\"{}\", one()?); Ok(two()?) }\n");
    assert_eq!((both.try_syn, both.try_macro_tokens), (1, 1));
}

#[test]
fn the_macro_token_count_excludes_question_sized_and_never_reads_a_macro_rules_body() {
    // Exclusion 1: `?Sized` is a trait bound's token, not an operation. The
    // second half is the falsifier -- a `?` before any OTHER ident is counted,
    // so this is a rule about `Sized` and not about `?` before an ident.
    assert_eq!(
        census("fn f() { bound!(T: ?Sized); }\n").try_macro_tokens,
        0
    );
    assert_eq!(
        census("fn f() { bound!(T: ?Unpin); }\n").try_macro_tokens,
        1
    );

    // Exclusion 2: inside a `macro_rules!` DEFINITION `$( .. )?` is a repetition
    // operator, and a definition is not an invocation. The falsifier is the same
    // token stream under a name that IS an invocation.
    let definition = "macro_rules! rep {\n    ($a:expr $(, $b:expr)?) => { $a };\n}\n";
    assert_eq!(census(definition).try_macro_tokens, 0);
    let invocation = definition.replacen("macro_rules!", "rep_like!", 1);
    assert_eq!(census(&invocation).try_macro_tokens, 1);
}

#[test]
fn an_unparseable_file_counts_no_question_marks_either() {
    let c = census("fn f( { one()?; }\n");
    assert!(!c.parsed);
    assert_eq!((c.try_syn, c.try_macro_tokens), (0, 0));
}

// ---------------------------------------------------------------------------
// The crate root's `allow` (rung 3): where it goes, and what it costs
// ---------------------------------------------------------------------------

#[test]
fn the_crate_root_allow_shares_the_last_inner_attributes_line() {
    // Not a line of its own: `rust/HONESTY.md` §9 promises no line moves, and
    // an attribute that needed one would move every line below it.
    let t = transform("#![no_std]\nfn f() {}\n", FILE, META, 0, true).expect("transform");
    assert!(
        t.source
            .starts_with("#![no_std] #![allow(clippy::match_single_binding)]\n"),
        "got: {}",
        t.source
    );
    assert_eq!(t.source.lines().count(), 2);
    syn::parse_file(&t.source).expect("re-parses");
}

#[test]
fn with_no_inner_attribute_the_allow_goes_in_front_of_the_first_token() {
    // Including when that token is an OUTER attribute or a doc comment on the
    // first item: an inner attribute has to precede every item, and this is
    // the only offset that does so without adding a line.
    for (src, head) in [
        (
            "fn f() {}\n",
            " #![allow(clippy::match_single_binding)]fn f()",
        ),
        (
            "#[allow(dead_code)]\nfn f() {}\n",
            " #![allow(clippy::match_single_binding)]#[allow(dead_code)]",
        ),
        (
            "/// doc\npub fn f() {}\n",
            " #![allow(clippy::match_single_binding)]/// doc",
        ),
    ] {
        let t = transform(src, FILE, META, 0, true).expect("transform");
        assert!(t.source.starts_with(head), "got: {}", t.source);
        assert_eq!(
            t.source.lines().count(),
            src.lines().count(),
            "no line moved: {}",
            t.source
        );
        syn::parse_file(&t.source).expect("re-parses");
    }
}

#[test]
fn a_module_file_of_the_same_unit_carries_no_allow() {
    // It is a CRATE-level attribute: the root's covers every file of the unit,
    // and a second one in a module would not even be legal there.
    let t = transform("fn f() {}\n", FILE, META, 0, false).expect("transform");
    assert!(
        !t.source.contains("match_single_binding"),
        "got: {}",
        t.source
    );
}

// ---------------------------------------------------------------------------
// Err-flow sites the transformer declines (rung 3)
// ---------------------------------------------------------------------------

#[test]
fn a_leading_struct_literal_is_declared_rather_than_made_a_match_scrutinee() {
    // `match C { v: 1 }.go() { .. }` is "struct literals are not allowed here"
    // -- the wrapped file would not parse at all (measured on rustc 1.96,
    // 2026-09-04) -- so the site is DECLARED. Zero of these on the bloomery
    // clone (`tests/census.rs`), which is why the identity there is exact.
    let src = "\
fn f() -> Result<u8, u8> {
    let v = C { v: 1 }.go()?;
    let _ = C { v: 1 }.go();
    C { v: 1 }.go().ok();
    Ok(v)
}
";
    let t = transform(src, FILE, META, 0, false).expect("transform");
    assert!(
        !t.source.contains("err_site"),
        "not one of these may be wrapped: {}",
        t.source
    );
    assert_eq!(
        partials(&t),
        [
            (2, "f", "struct-literal"),
            (3, "f", "struct-literal"),
            (4, "f", "struct-literal"),
        ]
    );
    // The census still counts the `?`, which is why the identity subtracts the
    // declared ones by name rather than pretending they were never there.
    assert_eq!(census(src).try_syn, 1);
}

#[test]
fn parentheses_protect_a_struct_literal_and_the_site_is_wrapped() {
    // The fence for the rule above: rustc's own suggestion is the parentheses,
    // and with them the scrutinee is ordinary.
    let src = "fn f() -> Result<u8, u8> { let v = (C { v: 1 }).go()?; Ok(v) }\n";
    let t = transform(src, FILE, META, 0, false).expect("transform");
    assert!(t.partial.is_empty(), "{:?}", t.partial);
    assert_eq!(t.source.matches("::sensorium_rt::err_site(").count(), 1);
}

#[test]
fn a_const_context_gets_no_err_probe_and_a_closure_inside_one_does() {
    // `err_site` is not a `const fn`, so a wrap in a const context is E0015
    // (measured on rustc 1.96, 2026-09-04). `?` and all four sinks are
    // themselves rejected in const contexts, so `let _ = <expr>;` is the only
    // shape that reaches this rule -- and it absorbs nothing anyway.
    //
    // A CLOSURE resets it: a closure declared in a `const fn` may call a
    // non-const fn, because its body runs when the closure is called (measured
    // the same day).
    let src = "\
pub const fn c() -> u8 {
    let _ = 1 + 1;
    2
}

pub const TABLE: u8 = {
    let _ = 1 + 1;
    3
};

pub static F: fn() = || {
    let _ = one();
};

pub const fn holds_a_closure() -> fn() -> u8 {
    || {
        let _ = one();
        1
    }
}

fn one() -> u8 {
    1
}
";
    let t = transform(src, FILE, META, 0, false).expect("transform");
    assert_eq!(
        t.source.matches("::sensorium_rt::err_site(").count(),
        2,
        "only the two CLOSURE bodies: {}",
        t.source
    );
    assert!(
        t.partial.is_empty(),
        "a const context is not a partial site"
    );
    assert_eq!(
        t.sites
            .iter()
            .filter(|s| s.kind == SiteKind::Sink)
            .map(|s| (s.site, s.qualname.as_str(), s.firstlineno))
            .collect::<Vec<_>>(),
        // `c` and `holds_a_closure` are `const fn`, so they are skipped and
        // take no site at all; the two sink sites are the first two numbers.
        [(0, "F", 12), (1, "holds_a_closure", 17)]
    );
}

// ---------------------------------------------------------------------------
// Numbering, with err sites in the same space
// ---------------------------------------------------------------------------

#[test]
fn err_sites_take_their_numbers_from_the_same_counter_as_fn_items() {
    // Design R1b. The wrapper adds `t.sites.len()` to its running index, so the
    // UNION has to be contiguous from `first_site` -- not the fn rows alone.
    let src = "\
fn f() -> Result<u8, u8> {
    let _ = g();
    let v = g()?;
    Ok(v)
}

fn g() -> Result<u8, u8> {
    Ok(1)
}
";
    let t = transform(src, FILE, META, 1000, false).expect("transform");
    assert_eq!(
        t.sites
            .iter()
            .map(|s| (s.site, s.kind, s.how))
            .collect::<Vec<_>>(),
        [
            (1000, SiteKind::Fn, None),
            (1001, SiteKind::Sink, Some("sink_let_underscore")),
            (1002, SiteKind::Try, Some("try")),
            (1003, SiteKind::Fn, None),
        ]
    );
}

#[test]
fn an_err_site_index_past_24_bits_is_refused_too() {
    // The fn takes the last legal index and its `?` would be the first illegal
    // one, which the runtime's 24-bit site word cannot carry.
    let src = "fn f() -> Result<u8, u8> { let v = g()?; Ok(v) }\n";
    let err = transform(src, FILE, META, MAX_SITE_INDEX, false)
        .expect_err("the `?` site would be a 25-bit index");
    assert!(
        err.to_string().contains("site index"),
        "unhelpful error: {err}"
    );
}

#[test]
fn a_macro_argument_question_mark_outside_any_named_item_is_still_declared() {
    // The qualname falls back to the enclosing CONTAINER, and to the empty
    // string at file scope -- which says exactly that, rather than naming an
    // item that does not exist.
    let t = transform("some_macro!(f()?);\nfn g() {}\n", FILE, META, 0, false).expect("transform");
    assert_eq!(partials(&t), [(1, "", "macro-arg")]);
    let t =
        transform("mod m {\n    some_macro!(f()?);\n}\n", FILE, META, 0, false).expect("transform");
    assert_eq!(partials(&t), [(2, "m", "macro-arg")]);
}

// ---------------------------------------------------------------------------
// Rules about the golden SET rather than about one pair
// ---------------------------------------------------------------------------

#[test]
fn every_wrapped_ordinal_is_that_sites_source_order_rank_in_its_qualname() {
    // The rule N1 states, re-derived from the OUTSIDE for every golden that has
    // a spawn: rank the wrapped entries of one qualname by line, and the
    // ordinal must be that rank. A declared shape carries no ordinal at all.
    let mut with_spawns = 0usize;
    for case in common::CASES {
        let t = transform(&read(case, "in"), FILE, META, 7, true)
            .unwrap_or_else(|e| panic!("{case}: transform failed: {e}"));
        if t.spawns.is_empty() {
            continue;
        }
        with_spawns += 1;
        for s in &t.spawns {
            assert_eq!(
                s.wrapped,
                s.ordinal.is_some(),
                "{case}: only a wrapped site has an ordinal ({s:?})"
            );
        }
        let mut by_qualname: BTreeMap<&str, Vec<&SpawnSite>> = BTreeMap::new();
        for s in t.spawns.iter().filter(|s| s.wrapped) {
            by_qualname.entry(s.qualname.as_str()).or_default().push(s);
        }
        for (qualname, mut group) in by_qualname {
            // `t.spawns` is already in byte-offset order and this sort is
            // stable, so two sites on one line keep their source order.
            group.sort_by_key(|s| s.line);
            for (rank, s) in group.iter().enumerate() {
                let expected = u32::try_from(rank + 1).expect("a small rank");
                assert_eq!(
                    s.ordinal,
                    Some(expected),
                    "{case}: {qualname} at line {} is rank {expected} in source order",
                    s.line
                );
            }
        }
    }
    assert!(
        with_spawns >= 4,
        "only {with_spawns} goldens have spawns: this test is checking nothing"
    );
}

#[test]
fn every_golden_case_on_disk_is_in_the_list_the_oracle_compiles() {
    // The list `oracle.rs` compiles and the files on disk must agree, or a
    // golden could be added and silently never compiled.
    let mut on_disk: Vec<String> =
        std::fs::read_dir(common::golden_path("free_fn", "in").parent().unwrap())
            .expect("golden directory")
            .filter_map(Result::ok)
            .filter_map(|e| {
                let name = e.file_name().to_string_lossy().into_owned();
                name.strip_suffix(".in.rs").map(ToOwned::to_owned)
            })
            .collect();
    on_disk.sort();
    let mut listed: Vec<String> = common::CASES.iter().map(|s| (*s).to_owned()).collect();
    listed.sort();
    assert_eq!(on_disk, listed, "tests/golden and common::CASES disagree");
    for case in common::RUN_CASES {
        assert!(common::CASES.contains(case), "{case} is not a golden");
    }
}
