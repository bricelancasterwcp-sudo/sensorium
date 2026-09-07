//! Resolving a `--focus` against the workspace, BEFORE anything is built.
//!
//! Design 2026-09-06 §2.2. A focus is a compile-time decision (ruling F2), so
//! a value that names nothing has already cost a full build by the time the
//! trace is empty. This module answers "does this value select anything?"
//! from the sources alone -- no cargo build, no rewrite, no spool -- and the
//! driver refuses with exit 2 before cargo is invoked at all.
//!
//! Eligibility is not this module's opinion. It is the TRANSFORM's own
//! classification, read back through [`sensorium_transform::fn_items`]: a
//! qualname is eligible exactly when the transform would mint a `Fn` site for
//! it, and skipped exactly when the transform names a reason
//! (`const`/`extern`/`async`/`macro`). Anything else would let the driver
//! accept a value the transform then silently ignores.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::process::Command;

use sensorium_transform::{fn_items, Focus};

use crate::modtree::{self, DiskFs};

/// How many "did you mean" qualnames a refusal offers.
const CLOSEST: usize = 3;

/// What the workspace said about each value of a focus.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct Resolution {
    /// Every eligible qualname some value selected: sorted, de-duplicated.
    pub matched: Vec<String>,
    /// `(value, up to three closest eligible qualnames)` for a value that
    /// selected nothing at all.
    pub unmatched: Vec<(String, Vec<String>)>,
    /// `(value, every (qualname, skip reason) it found)` for a value whose
    /// only hits are functions the transform never instruments.
    ///
    /// EVERY hit, in qualname order, because §2.2's refusal names them: a
    /// person told only the first of a `mod` of three `async fn`s would fix
    /// that one and meet the same refusal twice more. The value is carried
    /// beside them because for a CONTAINER value (`--focus m` where `m` holds
    /// only `async fn g`) the value and the qualname are different words.
    pub skipped_only: Vec<(String, Vec<(String, String)>)>,
}

impl Resolution {
    /// Nothing was selected and something was asked for: the driver refuses.
    #[must_use]
    pub fn refuses(&self) -> bool {
        !self.unmatched.is_empty() || !self.skipped_only.is_empty()
    }
}

/// Match each value of `focus` against every fn item the workspace holds.
///
/// # Errors
/// When `cargo metadata` cannot be run or does not answer with the package
/// list this needs. A workspace whose files cannot be read is not an error:
/// an unreadable file is one the wrapper would not instrument either, so it
/// contributes no eligible qualname and nothing else changes.
pub fn resolve_focus(ws_root: &Path, focus: &Focus) -> Result<Resolution, String> {
    let (eligible, skipped) = fn_inventory(ws_root)?;
    let mut resolution = Resolution::default();
    let mut matched: BTreeSet<String> = BTreeSet::new();
    for value in focus.values() {
        // One value at a time, through `Focus`'s own boundary rule, so that
        // the resolver and the transform can never disagree about what
        // `--focus Counter` selects.
        let one = Focus::parse(value);
        let hits: Vec<&String> = eligible.iter().filter(|q| one.matches(q)).collect();
        if !hits.is_empty() {
            matched.extend(hits.into_iter().cloned());
            continue;
        }
        let skipped_hits: Vec<(String, String)> = skipped
            .iter()
            .filter(|(q, _)| one.matches(q))
            .map(|(q, reason)| (q.clone(), (*reason).to_owned()))
            .collect();
        if !skipped_hits.is_empty() {
            resolution.skipped_only.push((value.clone(), skipped_hits));
            continue;
        }
        resolution
            .unmatched
            .push((value.clone(), closest(&eligible, value)));
    }
    resolution.matched = matched.into_iter().collect();
    Ok(resolution)
}

/// Every fn item of the workspace: the eligible qualnames, and the skipped
/// ones with the transform's reason.
fn fn_inventory(
    ws_root: &Path,
) -> Result<(BTreeSet<String>, BTreeMap<String, &'static str>), String> {
    let mut eligible: BTreeSet<String> = BTreeSet::new();
    let mut skipped: BTreeMap<String, &'static str> = BTreeMap::new();
    for rel in workspace_files(ws_root)? {
        let Ok(source) = std::fs::read_to_string(ws_root.join(&rel)) else {
            continue;
        };
        for item in fn_items(&source, &rel) {
            match item.skipped {
                None => {
                    eligible.insert(item.qualname);
                }
                Some(reason) => {
                    // First reason wins: two files can spell the same
                    // file-local qualname, and either answer is true of one of
                    // them.
                    skipped.entry(item.qualname).or_insert(reason);
                }
            }
        }
    }
    Ok((eligible, skipped))
}

/// Every `.rs` file the workspace's own targets reach, workspace-relative.
///
/// The SAME walk the wrapper uses per unit ([`modtree::walk`] from a crate
/// root), started from every target `cargo metadata` names, so the resolver's
/// file set is the set the build would instrument and not a directory guess.
/// A target whose source sits outside the workspace root is skipped: the
/// mirror is workspace-relative, so such a file is never instrumented either.
fn workspace_files(ws_root: &Path) -> Result<Vec<String>, String> {
    let fs = DiskFs { root: ws_root };
    let mut files: BTreeSet<String> = BTreeSet::new();
    for root in crate_roots(ws_root)? {
        files.extend(modtree::walk(&fs, &root).files);
    }
    Ok(files.into_iter().collect())
}

/// The workspace-relative crate root of every target of every workspace
/// member, from `cargo metadata --no-deps`.
fn crate_roots(ws_root: &Path) -> Result<Vec<String>, String> {
    let out = Command::new(crate::driver::cargo_path())
        .args(["metadata", "--no-deps", "--format-version", "1"])
        .arg("--manifest-path")
        .arg(ws_root.join("Cargo.toml"))
        .current_dir(ws_root)
        .output()
        .map_err(|e| format!("cannot run cargo metadata: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "cargo metadata failed ({}): {}",
            out.status,
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let value: serde_json::Value = serde_json::from_slice(&out.stdout)
        .map_err(|e| format!("cargo metadata printed something this driver cannot read: {e}"))?;
    let packages = value["packages"]
        .as_array()
        .ok_or_else(|| "cargo metadata printed no `packages` array".to_owned())?;
    let mut roots: Vec<String> = Vec::new();
    for package in packages {
        let Some(targets) = package["targets"].as_array() else {
            continue;
        };
        for target in targets {
            let Some(src) = target["src_path"].as_str() else {
                continue;
            };
            let Ok(rel) = Path::new(src).strip_prefix(ws_root) else {
                continue;
            };
            let rel = rel
                .components()
                .map(|c| c.as_os_str().to_string_lossy().into_owned())
                .collect::<Vec<_>>()
                .join("/");
            if !roots.contains(&rel) {
                roots.push(rel);
            }
        }
    }
    Ok(roots)
}

/// The eligible qualnames nearest `value`: most trailing `::` segments in
/// common first, then lexicographic.
///
/// A value that shares NO segment with anything ties every candidate at zero,
/// and the list is then simply the first three eligible qualnames in order --
/// which is the right answer to "what could I have typed?" when the answer is
/// "not that". The list is empty only when the workspace holds no eligible
/// function at all, and only then does the refusal drop its `Closest:`.
fn closest(eligible: &BTreeSet<String>, value: &str) -> Vec<String> {
    let want: Vec<&str> = value.split("::").collect();
    let mut scored: Vec<(usize, &String)> = eligible
        .iter()
        .map(|q| (shared_suffix_segments(&want, q), q))
        .collect();
    scored.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(b.1)));
    scored
        .into_iter()
        .take(CLOSEST)
        .map(|(_, q)| q.clone())
        .collect()
}

/// How many trailing `::` segments `qualname` shares with `want`.
fn shared_suffix_segments(want: &[&str], qualname: &str) -> usize {
    let have: Vec<&str> = qualname.split("::").collect();
    let mut n = 0;
    while n < want.len() && n < have.len() && want[want.len() - 1 - n] == have[have.len() - 1 - n] {
        n += 1;
    }
    n
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;
    use std::time::SystemTime;

    /// The fixture §2.2's cases are stated against: three eligible fns
    /// (`m::f`, `h`, `S::k`) and one the transform skips (`m::g`, async).
    const LIB: &str = "mod m {\n    pub fn f() {}\n    pub async fn g() {}\n}\nfn h() {}\n\
                       struct S;\nimpl S {\n    fn k(&self) {}\n}\n";

    struct Tmp(PathBuf);

    impl Tmp {
        fn new(name: &str) -> Tmp {
            Tmp::with(name, LIB)
        }

        fn with(name: &str, lib: &str) -> Tmp {
            let base = std::env::temp_dir().join(format!(
                "sensorium-resolve-test-{}-{}-{name}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir_all(base.join("src")).unwrap();
            fs::write(
                base.join("Cargo.toml"),
                "[package]\nname = \"focus-fixture\"\nversion = \"0.0.0\"\nedition = \"2021\"\n\
                 \n[lib]\nname = \"focus_fixture\"\npath = \"src/lib.rs\"\n",
            )
            .unwrap();
            fs::write(base.join("src/lib.rs"), lib).unwrap();
            Tmp(base)
        }
    }

    impl Drop for Tmp {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn resolve(t: &Tmp, csv: &str) -> Resolution {
        resolve_focus(&t.0, &Focus::parse(csv)).expect("the fixture workspace resolves")
    }

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| (*s).to_owned()).collect()
    }

    #[test]
    fn a_container_value_selects_the_eligible_functions_under_it() {
        let t = Tmp::new("container");
        let r = resolve(&t, "m");
        // `m::g` is async, so `m` selects `m::f` and nothing else.
        assert_eq!(r.matched, v(&["m::f"]));
        assert!(!r.refuses(), "{r:?}");
    }

    #[test]
    fn an_impl_self_type_is_a_container_like_any_other() {
        let t = Tmp::new("impl");
        assert_eq!(resolve(&t, "S").matched, v(&["S::k"]));
        assert_eq!(resolve(&t, "S::k").matched, v(&["S::k"]));
    }

    #[test]
    fn several_values_are_one_sorted_de_duplicated_matched_set() {
        let t = Tmp::new("several");
        let r = resolve(&t, "m::f,S::k,S");
        assert_eq!(r.matched, v(&["S::k", "m::f"]));
    }

    #[test]
    fn a_value_that_names_only_a_skipped_function_refuses_with_the_reason() {
        let t = Tmp::new("skipped");
        let r = resolve(&t, "m::g");
        assert!(r.matched.is_empty());
        assert_eq!(r.unmatched, vec![]);
        assert_eq!(
            r.skipped_only,
            vec![(
                "m::g".to_owned(),
                vec![("m::g".to_owned(), "async".to_owned())]
            )]
        );
        assert!(r.refuses());
    }

    #[test]
    fn a_value_that_names_nothing_refuses_with_the_closest_eligible_names() {
        let t = Tmp::new("unmatched");
        let r = resolve(&t, "zz");
        assert!(r.matched.is_empty());
        assert!(r.skipped_only.is_empty());
        // Nothing shares a segment, so every eligible name ties and the first
        // three in order are offered.
        assert_eq!(
            r.unmatched,
            vec![("zz".to_owned(), v(&["S::k", "h", "m::f"]))]
        );
        assert!(r.refuses());
    }

    #[test]
    fn closest_prefers_the_names_sharing_the_longest_trailing_segments() {
        let t = Tmp::new("closest");
        let r = resolve(&t, "wrong::f");
        assert_eq!(
            r.unmatched,
            vec![("wrong::f".to_owned(), v(&["m::f", "S::k", "h"]))],
            "`m::f` shares the trailing segment `f`; the rest tie at zero"
        );
    }

    #[test]
    fn every_value_is_judged_so_one_bad_name_does_not_hide_another() {
        let t = Tmp::new("all");
        let r = resolve(&t, "m::f,zz,m::g");
        assert_eq!(r.matched, v(&["m::f"]));
        assert_eq!(r.unmatched.len(), 1);
        assert_eq!(r.skipped_only.len(), 1);
        assert!(r.refuses(), "a partial match still refuses");
    }

    #[test]
    fn the_suffix_score_counts_whole_segments_and_not_characters() {
        assert_eq!(shared_suffix_segments(&["f"], "m::f"), 1);
        assert_eq!(shared_suffix_segments(&["f"], "m::ff"), 0);
        assert_eq!(shared_suffix_segments(&["a", "b"], "m::a::b"), 2);
        assert_eq!(shared_suffix_segments(&["a", "b"], "m::x::b"), 1);
        assert_eq!(shared_suffix_segments(&["zz"], "m::f"), 0);
    }

    /// Every skipped function the value found, not just the first: a person
    /// told "`m` matches only `m::a`" over a `mod m` of three `async fn`s
    /// would fix `m::a` and meet the same refusal twice more.
    #[test]
    fn a_value_that_finds_only_skipped_functions_names_all_of_them() {
        let t = Tmp::with(
            "many-skipped",
            "mod m {\n    pub async fn a() {}\n    pub async fn b() {}\n    \
             pub const fn c() -> u8 { 1 }\n}\nfn keep() {}\n",
        );
        let r = resolve(&t, "m");
        assert!(r.matched.is_empty());
        assert_eq!(
            r.skipped_only,
            vec![(
                "m".to_owned(),
                vec![
                    ("m::a".to_owned(), "async".to_owned()),
                    ("m::b".to_owned(), "async".to_owned()),
                    ("m::c".to_owned(), "const".to_owned()),
                ]
            )]
        );
        assert!(r.refuses());
    }
}
