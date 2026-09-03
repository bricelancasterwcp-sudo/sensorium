//! The runtime's source, embedded in the driver binary.
//!
//! Plan decision D1: `sensorium-rt` is never a dependency of the workspace
//! under test, never in its `Cargo.lock`, and never built by cargo during a
//! recorded build. The driver writes these bytes out and compiles them with one
//! bare `rustc` line, so the runtime's version is the driver's version by
//! construction — there is no way to run a driver against a runtime it was not
//! built from.
//!
//! Every file `src/lib.rs` declares as a module must be here: the bare `rustc`
//! line has no cargo to find them for it. [`tests::every_module_the_crate_root_declares_is_embedded`]
//! is the check, and it reads the module list out of the embedded `lib.rs`
//! rather than out of a list somebody has to remember to update.

/// `(path under src/, contents)`. `lib.rs` is first, which is also the file the
/// bare `rustc` line is pointed at.
pub const FILES: &[(&str, &str)] = &[
    ("lib.rs", include_str!("../../sensorium-rt/src/lib.rs")),
    ("ffi.rs", include_str!("../../sensorium-rt/src/ffi.rs")),
    ("panic.rs", include_str!("../../sensorium-rt/src/panic.rs")),
    ("probe.rs", include_str!("../../sensorium-rt/src/probe.rs")),
    (
        "sha256.rs",
        include_str!("../../sensorium-rt/src/sha256.rs"),
    ),
    ("spool.rs", include_str!("../../sensorium-rt/src/spool.rs")),
    ("tasks.rs", include_str!("../../sensorium-rt/src/tasks.rs")),
    (
        "thread.rs",
        include_str!("../../sensorium-rt/src/thread.rs"),
    ),
];

/// The crate root, which is what the bare `rustc` line compiles.
pub const CRATE_ROOT: &str = "lib.rs";

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_crate_root_is_first_and_is_the_file_rustc_is_pointed_at() {
        assert_eq!(FILES[0].0, CRATE_ROOT);
    }

    /// A module added to the runtime and not added here compiles fine under
    /// cargo (which finds the file on disk) and fails under the driver's bare
    /// `rustc` line (which only sees what was written out) — in a target
    /// workspace, on somebody else's machine. So the list is checked against
    /// the crate root's own `mod` declarations, here.
    #[test]
    fn every_module_the_crate_root_declares_is_embedded() {
        let root = syn::parse_file(FILES[0].1).expect("the embedded lib.rs must parse");
        let declared: Vec<String> = root
            .items
            .iter()
            .filter_map(|item| match item {
                // `content: None` is `mod x;` — a module that lives in a file.
                // An inline `mod x { .. }` (the crate's own `#[cfg(test)] mod
                // tests`) is not a file and must not be looked for.
                syn::Item::Mod(m) if m.content.is_none() => Some(m.ident.to_string()),
                _ => None,
            })
            .collect();
        assert!(
            !declared.is_empty(),
            "the crate root declares no file modules, so this check proves nothing"
        );
        for name in &declared {
            let want = format!("{name}.rs");
            assert!(
                FILES.iter().any(|(path, _)| *path == want),
                "src/lib.rs declares `mod {name};` but {want} is not embedded; \
                 the driver's bare rustc line would fail to find it"
            );
        }
    }

    #[test]
    fn nothing_embedded_is_empty() {
        for (path, contents) in FILES {
            assert!(!contents.is_empty(), "{path} is embedded as empty bytes");
        }
    }

    #[test]
    fn the_embedded_root_is_the_runtime_and_not_some_other_crate() {
        // A pinned line rather than a shape: if `include_str!` is ever pointed
        // at the wrong file this fails, where a "parses as Rust" check would
        // not.
        assert!(
            FILES[0].1.contains("pub use tasks::spawn_child;"),
            "the embedded lib.rs is not sensorium-rt's"
        );
    }
}
