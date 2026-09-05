//! What `golden.rs`, `errflow.rs`, `oracle.rs` and `manifest.rs` share: the
//! golden case list, the per-case runner, and the placeholder expansion that
//! pins every injected fragment IN THE TESTS rather than reading it back out of
//! the implementation under test.
//!
//! * `@G(<site>)`  -- the entry guard for that site.
//! * `@R(<site>)`  -- the opening half of an exit wrap.
//! * `@E`          -- its closing `)`.
//! * `@U`          -- the crate root's `__SENSORIUM_UNIT` static.
//! * `@W`          -- the crate root's `clippy::match_single_binding` allow.
//! * `@C`          -- the rewritten spawn callee.
//! * `@A(<site>)`  -- the plain spawn site argument.
//! * `@I(<use path>;<site>)` -- the spawn site argument that keeps the callee's
//!   import alive, for a callee path that is not rooted at the `std` crate.
//! * `@T(<site>)` .. `@TE`  -- an err wrap around a `?` operand.
//! * `@S(<site>,<HOW>)` .. `@SE` -- an err wrap around a sink receiver, `<HOW>`
//!   spelled as the runtime constant the fragment must name.
//! * `@L(<site>)` .. `@LE`  -- an err wrap around a `let _ =` value.
//! * `@P(<site>,<HOW>[,<name>])` -- the probe statement an `Err(..) =>` arm or
//!   an `if let Err(..)` body writes at its entry. With a third argument it is
//!   the BOUND form and `<name>` is the ident the pattern destructured into;
//!   without one it is the unbound form. The braces an expression body is
//!   wrapped in are spelled out in the golden itself, so an `.out.rs` shows
//!   exactly the block that was added.
//! * `@K(<site>)` -- the guard of a CLOSURE frame. The same bytes `@G` expands
//!   to, under a name that says which kind of frame a golden is pinning.
//!
//! The three err-wrap pairs are one fragment with three `how` bytes, so they
//! share an expansion; the marker still has to MATCH its opener, which is what
//! catches a golden written with a `@TE` closing a `@S(`.
#![allow(dead_code)]

use std::fs;
use std::path::PathBuf;

use sensorium_transform::{transform_file, FileRole, RetKind, SiteKind, Transformed};

pub const META: &str = "d41d8cd98f00b204";
pub const FILE: &str = "src/lib.rs";

pub fn guard(site: u32) -> String {
    format!("let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, {site});")
}

pub fn ret_open(site: u32) -> String {
    format!(
        "::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, {site}, |__r| {{ \
         use ::sensorium_rt::probe::*; \
         ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome()) }}, "
    )
}

/// The opening half of an err wrap: six bytes, and nothing else.
pub const ERR_OPEN: &str = "match ";

/// The probe an `Err(..) =>` arm or an `if let Err(..)` body writes at its
/// entry. `bound` is the ident the pattern destructured the error into, when
/// the pattern destructured one into exactly one name.
pub fn arm_probe(site: u32, how: &str, bound: Option<&str>) -> String {
    match bound {
        Some(name) => format!(
            "::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, {site}, \
             ::sensorium_rt::{how}, || {{ use ::sensorium_rt::probe::*; \
             (&&Probe(&{name})).err_cap_value() }});"
        ),
        None => format!(
            "::sensorium_rt::err_site_unbound(&crate::__SENSORIUM_UNIT, {site}, \
             ::sensorium_rt::{how});"
        ),
    }
}

/// The crate root's allow, with the leading space that keeps it off the
/// previous attribute's `]`. Two lints: every wrap is a single-binding `match`,
/// and on a non-`Result` operand the runtime ladder's by-value fallback makes
/// the fragment's three `&` look needless.
pub const CRATE_ALLOW: &str = " #![allow(clippy::match_single_binding, clippy::needless_borrow)]";

/// The closing half of an err wrap. `how` is the `sensorium_rt` constant the
/// fragment names, spelled out here so a golden shows which `how` it writes.
pub fn err_close(site: u32, how: &str) -> String {
    format!(
        " {{ __t => {{ ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, {site}, \
         ::sensorium_rt::{how}, || {{ use ::sensorium_rt::probe::*; \
         (&&&Probe(&__t)).err_cap() }}); __t }} }}"
    )
}

/// The static as it is emitted on a crate root with nowhere on an existing
/// line to put the `allow`: the file has no tokens, or its last inner
/// attribute is a line doc comment running to EOF. Such a file has no items,
/// so an inner attribute may still legally sit in front of the static.
pub fn unit_static_with_allow(metadata: &str) -> String {
    format!(
        "#![allow(clippy::match_single_binding, clippy::needless_borrow)] {}",
        unit_static(metadata)
    )
}

pub fn unit_static(metadata: &str) -> String {
    format!(
        "#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = \
         ::sensorium_rt::Unit::new(\"{metadata}\");"
    )
}

/// Expand the placeholders in an expected file.
pub fn expand(template: &str) -> String {
    let mut out = String::with_capacity(template.len() + 1024);
    // Open err wraps, innermost last: `(marker, site, how)`.
    let mut open_wraps: Vec<(&str, u32, String)> = Vec::new();
    let mut rest = template;
    while let Some(at) = rest.find('@') {
        out.push_str(&rest[..at]);
        let tail = &rest[at..];
        if let Some(after) = tail.strip_prefix("@G(") {
            let (arg, next) = split_arg(after, "@G(");
            out.push_str(&guard(arg.parse().expect("@G( non-numeric site )")));
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@R(") {
            let (arg, next) = split_arg(after, "@R(");
            out.push_str(&ret_open(arg.parse().expect("@R( non-numeric site )")));
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@A(") {
            let (arg, next) = split_arg(after, "@A(");
            out.push_str(&format!("\"{arg}\", "));
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@I(") {
            let (arg, next) = split_arg(after, "@I(");
            let (path, site) = arg.split_once(';').expect("@I( needs <use path>;<site> )");
            out.push_str(&format!(
                "{{ #[allow(unused_imports)] use {path} as _; \"{site}\" }}, "
            ));
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@T(") {
            let (arg, next) = split_arg(after, "@T(");
            open_wraps.push(("T", parse_site(arg, "@T("), "HOW_TRY".to_owned()));
            out.push_str(ERR_OPEN);
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@L(") {
            let (arg, next) = split_arg(after, "@L(");
            open_wraps.push((
                "L",
                parse_site(arg, "@L("),
                "HOW_SINK_LET_UNDERSCORE".to_owned(),
            ));
            out.push_str(ERR_OPEN);
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@S(") {
            let (arg, next) = split_arg(after, "@S(");
            let (site, how) = arg.split_once(',').expect("@S( needs <site>,<HOW> )");
            open_wraps.push(("S", parse_site(site, "@S("), how.to_owned()));
            out.push_str(ERR_OPEN);
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@P(") {
            let (arg, next) = split_arg(after, "@P(");
            let mut parts = arg.split(',');
            let site = parse_site(parts.next().expect("@P( needs a site )"), "@P(");
            let how = parts.next().expect("@P( needs <site>,<HOW> )");
            out.push_str(&arm_probe(site, how, parts.next()));
            assert!(
                parts.next().is_none(),
                "@P( takes at most three arguments )"
            );
            rest = next;
        } else if let Some(after) = tail.strip_prefix("@K(") {
            let (arg, next) = split_arg(after, "@K(");
            out.push_str(&guard(parse_site(arg, "@K(")));
            rest = next;
        } else if let Some((marker, after)) = close_marker(tail) {
            let (opened, site, how) = open_wraps
                .pop()
                .unwrap_or_else(|| panic!("@{marker}E with no wrap open"));
            assert_eq!(
                opened, marker,
                "@{marker}E closes a wrap opened by @{opened}("
            );
            out.push_str(&err_close(site, &how));
            rest = after;
        } else if let Some(after) = tail.strip_prefix("@E") {
            out.push(')');
            rest = after;
        } else if let Some(after) = tail.strip_prefix("@U") {
            out.push_str(&unit_static(META));
            rest = after;
        } else if let Some(after) = tail.strip_prefix("@W") {
            out.push_str(CRATE_ALLOW);
            rest = after;
        } else if let Some(after) = tail.strip_prefix("@C") {
            out.push_str("::sensorium_rt::spawn_child");
            rest = after;
        } else {
            out.push('@');
            rest = &tail[1..];
        }
    }
    assert!(
        open_wraps.is_empty(),
        "{} err wrap(s) opened and never closed",
        open_wraps.len()
    );
    out.push_str(rest);
    out
}

/// `@TE`, `@SE` or `@LE`, and what follows it.
fn close_marker(tail: &str) -> Option<(&'static str, &str)> {
    for marker in ["@TE", "@SE", "@LE"] {
        if let Some(after) = tail.strip_prefix(marker) {
            return Some((&marker[1..2], after));
        }
    }
    None
}

fn parse_site(arg: &str, what: &str) -> u32 {
    arg.parse()
        .unwrap_or_else(|_| panic!("{what} non-numeric site )"))
}

fn split_arg<'a>(after: &'a str, what: &str) -> (&'a str, &'a str) {
    let close = after
        .find(')')
        .unwrap_or_else(|| panic!("{what} without a closing paren"));
    (&after[..close], &after[close + 1..])
}

pub fn golden_path(case: &str, ext: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/golden")
        .join(format!("{case}.{ext}.rs"))
}

pub fn read(case: &str, ext: &str) -> String {
    let path = golden_path(case, ext);
    fs::read_to_string(&path).unwrap_or_else(|e| panic!("reading {}: {e}", path.display()))
}

/// Run one golden case and assert the invariants every case shares: exact
/// output, line count preserved, the result re-parses, and the unit static is a
/// real top-level item rather than text inside a comment.
///
/// **Every case is transformed as a crate root**, so every `.out.rs` is a
/// self-contained crate `tests/oracle.rs` can hand to the real rustc -- and
/// every one of them carries the crate-root `allow` as well as the static.
pub fn run(case: &str, first_site: u32) -> Transformed {
    run_role(
        case,
        first_site,
        FileRole {
            is_crate_root: true,
            is_bin_root: false,
        },
    )
}

/// [`run`] with the caller's [`FileRole`]. The marks it carries change the
/// manifest ROWS and never a byte of the source, so every case's `.out.rs` is
/// the same whichever role it is transformed under -- which is what
/// `golden_errflow.rs::the_marks_change_no_byte_of_the_source` measures.
pub fn run_role(case: &str, first_site: u32, role: FileRole) -> Transformed {
    let input = read(case, "in");
    let expected = expand(&read(case, "out"));
    let t = transform_file(&input, FILE, META, first_site, role)
        .unwrap_or_else(|e| panic!("{case}: transform failed: {e}"));

    assert_eq!(t.source, expected, "{case}: transformed source differs");
    assert_eq!(
        t.source.lines().count(),
        input.lines().count() + usize::from(t.appended_line),
        "{case}: line count moved (appended_line = {})",
        t.appended_line
    );
    syn::parse_file(&t.source)
        .unwrap_or_else(|e| panic!("{case}: transformed source does not re-parse: {e}"));
    assert!(
        top_level_unit_static(&t.source),
        "{case}: the unit static must be a real top-level item, not commented out"
    );
    t
}

/// The FN sites of a result: `(site, qualname, firstlineno, ret)`. Err-flow
/// sites take numbers from the same counter and are read by [`err_sites`], so
/// that a case which grows a `?` does not renumber every assertion about its
/// functions.
pub fn sites(t: &Transformed) -> Vec<(u32, &str, u32, RetKind)> {
    t.sites
        .iter()
        .filter(|s| s.kind == SiteKind::Fn)
        .map(|s| {
            (
                s.site,
                s.qualname.as_str(),
                s.firstlineno,
                s.ret.expect("a fn row carries what its signature returns"),
            )
        })
        .collect()
}

/// The ERR-FLOW sites of a result: `(site, qualname, line, kind, how)`.
pub fn err_sites(t: &Transformed) -> Vec<(u32, &str, u32, SiteKind, &'static str)> {
    t.sites
        .iter()
        .filter(|s| !matches!(s.kind, SiteKind::Fn | SiteKind::Closure))
        .map(|s| {
            (
                s.site,
                s.qualname.as_str(),
                s.firstlineno,
                s.kind,
                s.how.expect("an err-flow row carries the how it writes"),
            )
        })
        .collect()
}

/// The CLOSURE frames of a result: `(site, qualname, line)`. Their `ret` is
/// always `value` -- a closure declares no return type to read -- so it is not
/// repeated per row.
pub fn closure_sites(t: &Transformed) -> Vec<(u32, &str, u32)> {
    t.sites
        .iter()
        .filter(|s| s.kind == SiteKind::Closure)
        .map(|s| {
            assert_eq!(
                s.ret,
                Some(RetKind::Value),
                "a closure frame's exits are wrapped like a value fn's"
            );
            (s.site, s.qualname.as_str(), s.firstlineno)
        })
        .collect()
}

/// The MARKS of a result's fn rows: `(qualname, test, main)`, for the rows that
/// carry one. A row with neither is not listed: the marks are the exception.
pub fn marked(t: &Transformed) -> Vec<(&str, bool, bool)> {
    t.sites
        .iter()
        .filter(|s| s.test || s.main)
        .map(|s| (s.qualname.as_str(), s.test, s.main))
        .collect()
}

/// The `partial` rows of a result: `(line, qualname, kind, reason)`.
pub fn partials(t: &Transformed) -> Vec<(u32, &str, SiteKind, &'static str)> {
    t.partial
        .iter()
        .map(|p| (p.line, p.qualname.as_str(), p.kind, p.reason))
        .collect()
}

/// Parse a source and look for `__SENSORIUM_UNIT` as a real top-level ITEM. A
/// `source.contains("__SENSORIUM_UNIT")` check passes on a commented-out static,
/// which is exactly the defect this exists to catch.
pub fn top_level_unit_static(source: &str) -> bool {
    let Ok(file) = syn::parse_file(source) else {
        return false;
    };
    file.items.iter().any(|item| match item {
        syn::Item::Static(s) => s.ident == "__SENSORIUM_UNIT",
        _ => false,
    })
}

/// Every golden case. `golden.rs` and `errflow.rs` assert one test per entry
/// and `oracle.rs` compiles every entry, so a case added here is covered by
/// both.
pub const CASES: &[&str] = &[
    "async_block_try",
    "async_fn",
    "attr_operand",
    "block_tail",
    "body_attr",
    "body_inner_doc",
    "closure_no_try",
    "closure_try",
    "composite_diverging",
    "const_fn",
    "crate_root",
    "crate_root_docs",
    "crate_root_docs2",
    "crate_root_attrs",
    "crate_root_docs_todo",
    "diverging_tails",
    "empty_body",
    "err_arm_escaped",
    "err_arms_three_ways",
    "extern_fn",
    "format_tail",
    "free_fn",
    "generic_fn",
    "if_let_err",
    "impl_method",
    "inner_attr",
    "let_underscore",
    "loop_tail",
    "macro_rules",
    "mixed_arms",
    "nested_fn",
    "nested_mod",
    "never_fn",
    "one_line_body",
    "return_in_blocks",
    "return_in_closure",
    "run_drop_order",
    "run_err_drop_order",
    "run_mutex_guard",
    "shebang_utf8",
    "sink_place_receiver",
    "sinks",
    "spawn_ordinals",
    "spawn_shapes",
    "spawn_thread",
    "struct_literal_partial",
    "struct_tail",
    "test_fn",
    "test_marks",
    "trait_default",
    "try_in_macro_arg",
    "try_option",
    "try_stmt",
    "try_tail",
    "try_tail_and_stmt",
    "unit_fn",
    "unsafe_fn",
    "value_tail",
];

/// The cases `oracle.rs` compiles as a BINARY and runs, comparing the
/// transformed build's stdout against the untransformed build's.
pub const RUN_CASES: &[&str] = &["run_drop_order", "run_err_drop_order", "run_mutex_guard"];
