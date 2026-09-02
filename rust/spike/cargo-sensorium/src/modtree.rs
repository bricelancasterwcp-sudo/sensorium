//! The module-tree walk: from a crate root, which files belong to this unit?
//!
//! Rust 2018 resolution, as the reference states it and as the probe workspace
//! exercises it:
//!
//! * A crate root and a `mod.rs` are "mod-rs" files: their children resolve
//!   BESIDE them (`dir/x.rs` or `dir/x/mod.rs`).
//! * Any other file `foo.rs` is not: its children live under `foo/`.
//! * `#[path = "p"]` on a `mod x;` resolves `p` against the current module
//!   directory; on an inline `mod x { .. }` it REPLACES the directory its
//!   children resolve against.
//! * Inline modules push a directory component without being a file.
//! * `#[cfg_attr(.., path = ..)]` is NOT evaluated. The module's file is
//!   recorded unreached and left unrewritten -- an honest gap, not a guess.
//!
//! Filesystem access goes through [`Fs`] so the whole walk is unit-testable
//! against an in-memory tree; the wrapper supplies [`DiskFs`].

use std::collections::BTreeSet;
use std::path::Path;

use syn::{File, Item, ItemMod};

/// The workspace tree, rooted so every path is workspace-relative.
pub trait Fs {
    fn read(&self, rel: &str) -> Option<String>;
    fn is_file(&self, rel: &str) -> bool;
}

/// The real thing: a root directory plus relative paths.
pub struct DiskFs<'a> {
    pub root: &'a Path,
}

impl Fs for DiskFs<'_> {
    fn read(&self, rel: &str) -> Option<String> {
        std::fs::read_to_string(self.root.join(rel)).ok()
    }
    fn is_file(&self, rel: &str) -> bool {
        self.root.join(rel).is_file()
    }
}

/// What the walk found.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct Walk {
    /// Workspace-relative paths: the crate root FIRST, then discovery order.
    /// This is the order site numbering runs in, so it must be deterministic.
    pub files: Vec<String>,
    /// Files this unit contains that the walk could not rewrite, each as a
    /// workspace-relative path where one is known, otherwise
    /// `<declaring file>: mod <name> (<why>)`.
    pub unreached: Vec<String>,
}

/// Walk a unit from its crate root.
pub fn walk(fs: &dyn Fs, crate_root: &str) -> Walk {
    let mut w = Walk::default();
    let mut seen = BTreeSet::new();
    visit_file(fs, crate_root, true, &mut w, &mut seen);
    w
}

fn visit_file(fs: &dyn Fs, rel: &str, is_root: bool, w: &mut Walk, seen: &mut BTreeSet<String>) {
    if !seen.insert(rel.to_owned()) {
        return;
    }
    let Some(source) = fs.read(rel) else {
        w.unreached.push(rel.to_owned());
        return;
    };
    let ast: File = match syn::parse_file(&source) {
        Ok(f) => f,
        Err(_) => {
            w.unreached.push(rel.to_owned());
            return;
        }
    };
    w.files.push(rel.to_owned());
    let dir = module_dir(rel, is_root);
    visit_items(fs, &ast.items, rel, &dir, w, seen);
}

/// The directory a file's child modules resolve against.
fn module_dir(rel: &str, is_root: bool) -> String {
    let parent = rel.rsplit_once('/').map_or("", |(p, _)| p).to_owned();
    let name = rel.rsplit_once('/').map_or(rel, |(_, n)| n);
    if is_root || name == "mod.rs" {
        parent
    } else {
        let stem = name.strip_suffix(".rs").unwrap_or(name);
        join_rel(&parent, stem)
    }
}

fn visit_items(
    fs: &dyn Fs,
    items: &[Item],
    decl_file: &str,
    dir: &str,
    w: &mut Walk,
    seen: &mut BTreeSet<String>,
) {
    for item in items {
        let Item::Mod(m) = item else { continue };
        let explicit = path_attr(m);
        if let Some((_, inner)) = &m.content {
            // Inline: never a file. On an inline module `#[path]` names the
            // DIRECTORY its children resolve against (the reference's
            // `#[path = "thread_files"] mod thread { .. }`), so the value is
            // used verbatim -- no `.rs` stem to strip.
            let child_dir = match &explicit {
                Some(p) => join_rel(dir, p),
                None => join_rel(dir, &m.ident.to_string()),
            };
            visit_items(fs, inner, decl_file, &child_dir, w, seen);
            continue;
        }
        let default_candidates = [
            join_rel(dir, &format!("{}.rs", m.ident)),
            join_rel(dir, &format!("{}/mod.rs", m.ident)),
        ];
        if has_cfg_attr_path(m) {
            // Do not evaluate cfg. Record the file we would have taken had the
            // attribute not been there, so the gap names something real.
            let known = default_candidates.iter().find(|c| fs.is_file(c));
            w.unreached.push(known.cloned().unwrap_or_else(|| {
                format!(
                    "{decl_file}: mod {} (#[cfg_attr(.., path = ..)])",
                    m.ident
                )
            }));
            continue;
        }
        let resolved = match &explicit {
            Some(p) => {
                let c = join_rel(dir, p);
                fs.is_file(&c).then_some(c)
            }
            None => default_candidates.iter().find(|c| fs.is_file(c)).cloned(),
        };
        match resolved {
            Some(file) => visit_file(fs, &file, false, w, seen),
            None => w
                .unreached
                .push(format!("{decl_file}: mod {} (unresolved)", m.ident)),
        }
    }
}

fn path_attr(m: &ItemMod) -> Option<String> {
    for attr in &m.attrs {
        if !attr.path().is_ident("path") {
            continue;
        }
        if let syn::Meta::NameValue(nv) = &attr.meta {
            if let syn::Expr::Lit(syn::ExprLit {
                lit: syn::Lit::Str(s),
                ..
            }) = &nv.value
            {
                return Some(s.value());
            }
        }
    }
    None
}

fn has_cfg_attr_path(m: &ItemMod) -> bool {
    m.attrs.iter().any(|attr| {
        attr.path().is_ident("cfg_attr")
            && attr
                .meta
                .require_list()
                .is_ok_and(|l| l.tokens.to_string().contains("path"))
    })
}

/// Lexically join `rest` onto directory `base`, resolving `.` and `..`.
/// Never touches the filesystem, so it cannot follow a symlink out of the
/// workspace by accident.
#[must_use]
pub fn join_rel(base: &str, rest: &str) -> String {
    let mut parts: Vec<&str> = Vec::new();
    for seg in base.split('/').chain(rest.split('/')) {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop();
            }
            s => parts.push(s),
        }
    }
    parts.join("/")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    struct MemFs(BTreeMap<String, String>);

    impl MemFs {
        fn new(files: &[(&str, &str)]) -> MemFs {
            MemFs(
                files
                    .iter()
                    .map(|(p, c)| ((*p).to_owned(), (*c).to_owned()))
                    .collect(),
            )
        }
    }

    impl Fs for MemFs {
        fn read(&self, rel: &str) -> Option<String> {
            self.0.get(rel).cloned()
        }
        fn is_file(&self, rel: &str) -> bool {
            self.0.contains_key(rel)
        }
    }

    #[test]
    fn a_crate_roots_children_sit_beside_it() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "mod helper;"),
            ("a/src/helper.rs", "pub fn h() {}"),
        ]);
        assert_eq!(walk(&fs, "a/src/lib.rs").files, ["a/src/lib.rs", "a/src/helper.rs"]);
    }

    #[test]
    fn a_directory_module_resolves_through_mod_rs() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "mod sub;"),
            ("a/src/sub/mod.rs", "mod leaf;"),
            ("a/src/sub/leaf.rs", "pub fn l() {}"),
        ]);
        // `leaf` is a child of a mod.rs, so it sits BESIDE mod.rs. A walker
        // that used the non-mod-rs rule would look in a/src/sub/sub/.
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/sub/mod.rs", "a/src/sub/leaf.rs"]
        );
    }

    #[test]
    fn a_non_mod_rs_files_children_live_under_its_stem() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "mod deep;"),
            ("a/src/deep.rs", "mod inner;"),
            ("a/src/deep/inner.rs", "pub fn i() {}"),
            // The trap: a sibling with the right name that must NOT be picked.
            ("a/src/inner.rs", "compile_error!(\"wrong file\");"),
        ]);
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/deep.rs", "a/src/deep/inner.rs"]
        );
    }

    #[test]
    fn a_path_attribute_is_relative_to_the_declaring_files_directory() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "#[path = \"renamed_source.rs\"] mod renamed;"),
            ("a/src/renamed_source.rs", "pub fn r() {}"),
        ]);
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/renamed_source.rs"]
        );
    }

    #[test]
    fn a_path_attribute_may_climb_out_of_the_crate() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "#[path = \"../../shared/s.rs\"] mod s;"),
            ("shared/s.rs", "pub fn s() {}"),
        ]);
        assert_eq!(walk(&fs, "a/src/lib.rs").files, ["a/src/lib.rs", "shared/s.rs"]);
    }

    #[test]
    fn an_inline_module_adds_a_directory_but_not_a_file() {
        let fs = MemFs::new(&[
            (
                "a/src/lib.rs",
                "pub mod nested { #[path = \"nested_child.rs\"] pub mod child; }",
            ),
            ("a/src/nested/nested_child.rs", "pub fn c() {}"),
            // The trap: the same name beside lib.rs, which a walker that
            // ignored the inline component would take.
            ("a/src/nested_child.rs", "compile_error!(\"wrong file\");"),
        ]);
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/nested/nested_child.rs"]
        );
    }

    #[test]
    fn a_path_attribute_on_an_inline_module_names_a_directory() {
        // The reference's own example: `#[path = "thread_files"] mod thread`.
        // The value is a DIRECTORY, used verbatim -- strip a `.rs` stem from it
        // and `tls.rs` is looked for in the wrong place.
        let fs = MemFs::new(&[
            (
                "a/src/lib.rs",
                "#[path = \"thread_files\"] mod thread { #[path = \"tls.rs\"] mod local_data; }",
            ),
            ("a/src/thread_files/tls.rs", "pub fn t() {}"),
        ]);
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/thread_files/tls.rs"]
        );
    }

    #[test]
    fn a_plain_inline_module_still_nests_its_file_children() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "pub mod outer { mod leaf; }"),
            ("a/src/outer/leaf.rs", "pub fn l() {}"),
        ]);
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/outer/leaf.rs"]
        );
    }

    #[test]
    fn cfg_attr_path_records_the_default_file_unreached_and_never_rewrites_it() {
        let fs = MemFs::new(&[
            (
                "a/src/lib.rs",
                "#[cfg_attr(windows, path = \"maybe_windows.rs\")] pub mod maybe;",
            ),
            ("a/src/maybe.rs", "pub fn m() {}"),
        ]);
        let w = walk(&fs, "a/src/lib.rs");
        assert_eq!(w.files, ["a/src/lib.rs"]);
        assert_eq!(w.unreached, ["a/src/maybe.rs"]);
    }

    #[test]
    fn an_unresolvable_mod_names_its_declaration() {
        let fs = MemFs::new(&[("a/src/lib.rs", "mod ghost;")]);
        let w = walk(&fs, "a/src/lib.rs");
        assert_eq!(w.files, ["a/src/lib.rs"]);
        assert_eq!(w.unreached, ["a/src/lib.rs: mod ghost (unresolved)"]);
    }

    #[test]
    fn an_unparseable_file_is_unreached_not_silently_dropped() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "mod broken;"),
            ("a/src/broken.rs", "fn f( {"),
        ]);
        let w = walk(&fs, "a/src/lib.rs");
        assert_eq!(w.files, ["a/src/lib.rs"]);
        assert_eq!(w.unreached, ["a/src/broken.rs"]);
    }

    #[test]
    fn a_file_reached_twice_is_listed_once() {
        let fs = MemFs::new(&[
            (
                "a/src/lib.rs",
                "mod one; #[path = \"one.rs\"] mod also_one;",
            ),
            ("a/src/one.rs", "pub fn o() {}"),
        ]);
        assert_eq!(walk(&fs, "a/src/lib.rs").files, ["a/src/lib.rs", "a/src/one.rs"]);
    }

    #[test]
    fn a_self_referential_path_terminates() {
        let fs = MemFs::new(&[("a/src/lib.rs", "#[path = \"lib.rs\"] mod me;")]);
        assert_eq!(walk(&fs, "a/src/lib.rs").files, ["a/src/lib.rs"]);
    }

    #[test]
    fn an_integration_test_root_is_a_mod_rs_style_root() {
        let fs = MemFs::new(&[
            ("app/tests/e7.rs", "mod common;"),
            ("app/tests/common.rs", "pub fn c() {}"),
        ]);
        assert_eq!(
            walk(&fs, "app/tests/e7.rs").files,
            ["app/tests/e7.rs", "app/tests/common.rs"]
        );
    }

    #[test]
    fn join_rel_normalises() {
        assert_eq!(join_rel("a/b", "../c.rs"), "a/c.rs");
        assert_eq!(join_rel("", "x.rs"), "x.rs");
        assert_eq!(join_rel("a", "./b/../c"), "a/c");
    }
}
