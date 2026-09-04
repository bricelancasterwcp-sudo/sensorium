//! The module-tree walk: given a crate root, which source files belong to this
//! compilation unit?
//!
//! Rust 2018 module resolution, as the reference states it:
//!
//! * A crate root and a `mod.rs` are "mod-rs" files: their child modules
//!   resolve BESIDE them (`dir/x.rs` or `dir/x/mod.rs`).
//! * Any other file `foo.rs` is not: its children live under `foo/`.
//! * `#[path = "p"]` on a `mod x;` resolves `p` against the current module
//!   directory. On an INLINE `mod x { .. }` it names the directory the module's
//!   children resolve against, and is used verbatim.
//! * An inline module pushes a directory component without being a file.
//! * `#[cfg_attr(.., path = ..)]` is NOT evaluated (plan decision D3). The file
//!   the walk would otherwise have taken is recorded unreached and left
//!   unrewritten: an honest gap rather than a guess (findings §5.26).
//!
//! Filesystem access goes through [`Fs`], so the whole walk is testable against
//! an in-memory tree; the wrapper supplies [`DiskFs`].

use std::collections::BTreeSet;
use std::path::Path;

use syn::{File, Item, ItemMod};

/// The workspace tree, rooted so every path in the walk is
/// workspace-relative — the key the manifest and the mirror both use.
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
    /// Site numbering runs in this order, so it has to be deterministic.
    pub files: Vec<String>,
    /// Files this unit contains that the walk could not rewrite — each as a
    /// workspace-relative path where one is known, otherwise
    /// `<declaring file>: mod <name> (<why>)`. Reaches the trace as the
    /// manifest's `unreached_files` (`rust/HONESTY.md` §8 item 8).
    pub unreached: Vec<String>,
}

/// Walk one unit from its crate root.
#[must_use]
pub fn walk(fs: &dyn Fs, crate_root: &str) -> Walk {
    let mut found = Walk::default();
    let mut seen = BTreeSet::new();
    visit_file(fs, crate_root, true, &mut found, &mut seen);
    found
}

fn visit_file(
    fs: &dyn Fs,
    rel: &str,
    is_root: bool,
    found: &mut Walk,
    seen: &mut BTreeSet<String>,
) {
    if !seen.insert(rel.to_owned()) {
        return;
    }
    let Some(source) = fs.read(rel) else {
        found.unreached.push(rel.to_owned());
        return;
    };
    let ast: File = match syn::parse_file(&source) {
        Ok(f) => f,
        Err(_) => {
            found.unreached.push(rel.to_owned());
            return;
        }
    };
    found.files.push(rel.to_owned());
    let dir = module_dir(rel, is_root);
    visit_items(fs, &ast.items, rel, &dir, found, seen);
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
    found: &mut Walk,
    seen: &mut BTreeSet<String>,
) {
    for item in items {
        let Item::Mod(m) = item else { continue };
        let explicit = path_attr(m);
        if let Some((_, inner)) = &m.content {
            // Inline: never a file of its own. `#[path]` here names the
            // DIRECTORY the children resolve against (the reference's
            // `#[path = "thread_files"] mod thread { .. }`), so it is used
            // verbatim — there is no `.rs` stem to strip.
            let child_dir = match &explicit {
                Some(p) => join_rel(dir, p),
                None => join_rel(dir, &m.ident.to_string()),
            };
            visit_items(fs, inner, decl_file, &child_dir, found, seen);
            continue;
        }
        let defaults = [
            join_rel(dir, &format!("{}.rs", m.ident)),
            join_rel(dir, &format!("{}/mod.rs", m.ident)),
        ];
        if has_cfg_attr_path(m) {
            // D3: do not evaluate `cfg`. Name the file that would have been
            // taken without the attribute, so the gap points at something real.
            let known = defaults.iter().find(|c| fs.is_file(c));
            found.unreached.push(known.cloned().unwrap_or_else(|| {
                format!("{decl_file}: mod {} (#[cfg_attr(.., path = ..)])", m.ident)
            }));
            continue;
        }
        let resolved = match &explicit {
            Some(p) => {
                let candidate = join_rel(dir, p);
                fs.is_file(&candidate).then_some(candidate)
            }
            None => defaults.iter().find(|c| fs.is_file(c)).cloned(),
        };
        match resolved {
            Some(file) => visit_file(fs, &file, false, found, seen),
            None => found
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

/// Over-match rather than under-match: any `cfg_attr` whose tokens mention
/// `path` sends the module to `unreached_files`. A conditional path this walk
/// guessed at would put a file's guards in another file's unit.
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
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/helper.rs"]
        );
    }

    #[test]
    fn a_directory_module_resolves_through_mod_rs() {
        let fs = MemFs::new(&[
            ("a/src/lib.rs", "mod sub;"),
            ("a/src/sub/mod.rs", "mod leaf;"),
            ("a/src/sub/leaf.rs", "pub fn l() {}"),
        ]);
        // `leaf` is a child of a mod.rs, so it sits BESIDE mod.rs. A walker
        // using the non-mod-rs rule would look in a/src/sub/sub/.
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
            (
                "a/src/lib.rs",
                "#[path = \"renamed_source.rs\"] mod renamed;",
            ),
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
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "shared/s.rs"]
        );
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
    fn a_cfg_attr_path_with_no_file_on_disk_names_its_declaration() {
        let fs = MemFs::new(&[(
            "a/src/lib.rs",
            "#[cfg_attr(windows, path = \"w.rs\")] mod ghost;",
        )]);
        assert_eq!(
            walk(&fs, "a/src/lib.rs").unreached,
            ["a/src/lib.rs: mod ghost (#[cfg_attr(.., path = ..)])"]
        );
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
        assert_eq!(
            walk(&fs, "a/src/lib.rs").files,
            ["a/src/lib.rs", "a/src/one.rs"]
        );
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
    fn a_crate_root_that_does_not_exist_is_unreached_and_yields_no_files() {
        let fs = MemFs::new(&[]);
        let w = walk(&fs, "a/src/lib.rs");
        assert!(w.files.is_empty());
        assert_eq!(w.unreached, ["a/src/lib.rs"]);
    }

    #[test]
    fn join_rel_normalises() {
        assert_eq!(join_rel("a/b", "../c.rs"), "a/c.rs");
        assert_eq!(join_rel("", "x.rs"), "x.rs");
        assert_eq!(join_rel("a", "./b/../c"), "a/c");
    }
}
