//! What `golden.rs`, `oracle.rs` and `manifest.rs` share: the golden case list,
//! and the placeholder expansion that pins every injected fragment IN THE TESTS
//! rather than reading it back out of the implementation under test.
//!
//! * `@G(<site>)`  -- the entry guard for that site.
//! * `@R(<site>)`  -- the opening half of an exit wrap.
//! * `@E`          -- its closing `)`.
//! * `@U`          -- the crate root's `__SENSORIUM_UNIT` static.
//! * `@C`          -- the rewritten spawn callee.
//! * `@A(<site>)`  -- the plain spawn site argument.
//! * `@I(<use path>;<site>)` -- the spawn site argument that keeps the callee's
//!   import alive, for a callee path that is not rooted at the `std` crate.
#![allow(dead_code)]

use std::fs;
use std::path::PathBuf;

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

pub fn unit_static(metadata: &str) -> String {
    format!(
        "#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = \
         ::sensorium_rt::Unit::new(\"{metadata}\");"
    )
}

/// Expand the placeholders in an expected file.
pub fn expand(template: &str) -> String {
    let mut out = String::with_capacity(template.len() + 1024);
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
        } else if let Some(after) = tail.strip_prefix("@E") {
            out.push(')');
            rest = after;
        } else if let Some(after) = tail.strip_prefix("@U") {
            out.push_str(&unit_static(META));
            rest = after;
        } else if let Some(after) = tail.strip_prefix("@C") {
            out.push_str("::sensorium_rt::spawn_child");
            rest = after;
        } else {
            out.push('@');
            rest = &tail[1..];
        }
    }
    out.push_str(rest);
    out
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

/// Every golden case. `golden.rs` asserts one test per entry and `oracle.rs`
/// compiles every entry, so a case added here is covered by both.
pub const CASES: &[&str] = &[
    "async_fn",
    "attr_operand",
    "body_attr",
    "body_inner_doc",
    "const_fn",
    "crate_root",
    "crate_root_docs",
    "crate_root_docs2",
    "crate_root_docs_todo",
    "diverging_tails",
    "empty_body",
    "extern_fn",
    "format_tail",
    "free_fn",
    "generic_fn",
    "impl_method",
    "inner_attr",
    "loop_tail",
    "macro_rules",
    "nested_fn",
    "nested_mod",
    "never_fn",
    "one_line_body",
    "return_in_blocks",
    "return_in_closure",
    "run_drop_order",
    "run_mutex_guard",
    "shebang_utf8",
    "spawn_shapes",
    "spawn_thread",
    "struct_tail",
    "test_fn",
    "trait_default",
    "try_tail",
    "unit_fn",
    "unsafe_fn",
    "value_tail",
];

/// The cases `oracle.rs` compiles as a BINARY and runs, comparing the
/// transformed build's stdout against the untransformed build's.
pub const RUN_CASES: &[&str] = &["run_drop_order", "run_mutex_guard"];
