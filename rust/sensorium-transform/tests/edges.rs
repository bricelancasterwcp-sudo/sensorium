//! The rules no golden PAIR can hold: what the crate-root static does on files
//! whose whole content is comments, how offsets survive a BOM and CRLF endings,
//! where site numbering stops, and the census that is E2's denominator.
//!
//! These are here rather than in `golden.rs` because their inputs are one-line
//! strings: a `.in.rs`/`.out.rs` pair for `""` would be a file that is not
//! there.

mod common;

use common::{read, top_level_unit_static, FILE, META};

use sensorium_transform::{census, transform};

// ---------------------------------------------------------------------------
// The crate-root static, off the golden files
// ---------------------------------------------------------------------------

#[test]
fn a_trailing_block_doc_comment_still_takes_the_static_in_place() {
    // A `/*! .. */` crate doc is safe -- its span already ends after the `*/`.
    let t = transform("/*! Crate docs. */\n", FILE, META, 0, true).expect("transform");
    assert_eq!(
        t.source,
        format!("/*! Crate docs. */{}\n", common::unit_static(META))
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
    let t = transform("// nothing here\n", FILE, META, 0, true).expect("transform");
    assert_eq!(
        t.source,
        format!("{}// nothing here\n", common::unit_static(META))
    );
    assert_eq!(t.source.lines().count(), 1);
    syn::parse_file(&t.source).expect("re-parses");
}

#[test]
fn an_empty_crate_root_is_the_one_documented_line_count_exception() {
    let t = transform("", FILE, META, 0, true).expect("transform");
    assert_eq!(t.source, common::unit_static(META));
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
    // qualname and this site's ordinal in it (plan decision N1). The file path
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
    assert!(
        t.source.contains(r#"spawn_child("f#1", "#),
        "got: {}",
        t.source
    );
    assert!(
        !t.source.contains("a\\\"b"),
        "the path is not baked into the rewritten source: {}",
        t.source
    );
    // It is still what the manifest's entry says, spelled as the caller gave it.
    assert_eq!(t.spawns[0].file, "src\\a\"b.rs");
    assert_eq!(t.spawns[0].qualname, "f");
    assert_eq!(t.spawns[0].ordinal, Some(1));
    syn::parse_file(&t.source).expect("re-parses");
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
        assert_eq!(
            c.eligible(),
            t.sites.len() + c.async_fns,
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
    assert_eq!(t.source, format!("//! docs\n{}", common::unit_static(META)));
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
    assert_eq!(t.source, format!("{input}\n{}", common::unit_static(META)));
    assert!(t.appended_line);
    assert!(
        top_level_unit_static(&t.source),
        "the static must be a real item, not part of the shebang: {}",
        t.source
    );
    assert_eq!(t.source.lines().count(), input.lines().count() + 1);
}
