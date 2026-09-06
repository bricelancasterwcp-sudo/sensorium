//! Which manifests speak for THIS invocation's focus (design A9, ruling
//! R-F11).
//!
//! Its own module because the rule is small, load-bearing and was got wrong
//! once: a manifests directory accumulates one manifest per focus a workspace
//! was ever built under (A8), and every one of them is equally "in scope".

use std::collections::BTreeMap;

use sensorium_transform::canonical_values;

use super::manifest::{FocusRecord, Manifest};
use super::manifest_in_scope;

/// The focus of a run.
///
/// `values` is **the invocation's own list** and is never read from a
/// manifest. Because the focus joins the shim's path (A8), every focus gets
/// its own `-C metadata` and its own manifest, and those accumulate: a
/// manifests directory holds one per focus the workspace was ever built
/// under, all equally in scope. Reading `values` from any of them made an
/// unfocused run of `corpus/rust/silent_swallow` report `focus: ["load"]`
/// from a previous invocation (measured 2026-09-06). An empty list is `None`
/// -- `focus`/`focus_matched` absent, not empty, because `focus: []` would
/// say "a focus was given and selected nothing".
///
/// `matched` is the sorted, de-duplicated union of `matched` over the
/// manifests of THIS workspace (`workspace_root` matches -- a shared
/// `CARGO_TARGET_DIR` holds every workspace's) whose `focus.values` EQUALS
/// that list; a manifest with no record counts as the empty list. A build
/// under another focus therefore cannot speak here.
///
/// **Registration is deliberately not a criterion**, unlike
/// [`line_site_count`]: `focus_matched` is a fact about what the TRANSFORMER
/// matched while compiling, not about what ran. A unit built under this focus
/// whose code never executed still matched, and excluding it would make a
/// value that selected only a never-executed function indistinguishable from
/// one that selected nothing in the workspace at all -- the one question
/// `focus_matched` exists to answer. `capabilities.line`/`locals` keep the
/// narrower registered scope, because a LINE ROW cannot arrive from a unit
/// this process never linked.
pub fn record(
    invocation_focus: &[String],
    manifests: &BTreeMap<String, Manifest>,
    invocation_workspace_root: &str,
) -> Option<FocusRecord> {
    if invocation_focus.is_empty() {
        return None;
    }
    // A SET comparison (design A10): `focus_hash` sorts and de-duplicates
    // before hashing, so two orders of the same values are ONE build, sharing
    // a shim path, artifacts and manifests. Compared as ordered `Vec`s the
    // second order read `focus_matched: []` off a build with LINE rows.
    let wanted = canonical_values(invocation_focus);
    let mut matched: Vec<String> = Vec::new();
    for m in manifests.values() {
        if !manifest_in_scope(m, invocation_workspace_root) {
            continue;
        }
        let Some(focus) = m.focus.as_ref() else {
            continue;
        };
        if canonical_values(&focus.values) != wanted {
            continue;
        }
        matched.extend(focus.matched.iter().cloned());
    }
    matched.sort();
    matched.dedup();
    Some(FocusRecord {
        values: invocation_focus.to_vec(),
        matched,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    /// One fixture row: `(metadata, workspace_root, focus values, focus
    /// matched)`. A `None` focus is a unit built without one.
    type Row<'a> = (&'a str, &'a str, Option<(&'a [&'a str], &'a [&'a str])>);

    /// Through the real `Deserialize`, so the fixture cannot say anything a
    /// manifest on disk could not.
    fn manifests(rows: &[Row<'_>]) -> BTreeMap<String, Manifest> {
        rows.iter()
            .map(|(metadata, ws, focus)| {
                let record = focus.map_or_else(String::new, |(values, matched)| {
                    format!(
                        r#","focus":{{"values":{},"matched":{}}}"#,
                        json!(values),
                        json!(matched)
                    )
                });
                let text = format!(
                    r#"{{"unit":"u","crate_name":"c","fell_back":false,
                         "fallback_reason":null,"workspace_root":"{ws}"{record}}}"#
                );
                (
                    (*metadata).to_owned(),
                    serde_json::from_str(&text).expect("a manifest"),
                )
            })
            .collect()
    }

    /// R-F11 (design A9). Three manifests of one workspace, as A8's
    /// accumulation leaves them: M1 carries no record and is the REGISTERED
    /// one, M2 was built under `["load"]` and never registered, M3 under
    /// `["other"]`. What a run's `focus` is comes from the INVOCATION, and
    /// `focus_matched` unions only manifests built under that same list.
    fn a9_matrix() -> BTreeMap<String, Manifest> {
        manifests(&[
            ("m1", "/w", None),
            ("m2", "/w", Some((&["load"], &["load"]))),
            ("m3", "/w", Some((&["other"], &["other"]))),
        ])
    }

    fn under(focus: &[&str]) -> Option<FocusRecord> {
        let invocation: Vec<String> = focus.iter().map(|s| (*s).to_owned()).collect();
        super::record(&invocation, &a9_matrix(), "/w")
    }

    /// Measured 2026-09-06 on `corpus/rust/silent_swallow` before R-F11: an
    /// unfocused run reported `focus: ["load"]` from a previous invocation's
    /// manifest. An unfocused invocation says nothing at all.
    #[test]
    fn an_unfocused_invocation_borrows_no_previous_builds_focus() {
        assert_eq!(
            under(&[]),
            None,
            "both keys absent: an unfocused run has no focus to report"
        );
    }

    /// The registered unit here (M1) carries NO record, and M2 -- which does,
    /// under this invocation's list -- never registered. Registration is not
    /// the criterion (A9): a unit built under this focus whose code never ran
    /// still matched, or a value that selected only a never-executed function
    /// would be indistinguishable from one that selected nothing anywhere.
    #[test]
    fn the_invocations_list_is_the_focus_and_only_its_own_manifests_matched() {
        let r = under(&["load"]).expect("a focused invocation reports its focus");
        assert_eq!(r.values, ["load"]);
        assert_eq!(r.matched, ["load"], "M3 was built under another focus");

        let r = under(&["other"]).expect("a record");
        assert_eq!(r.values, ["other"]);
        assert_eq!(r.matched, ["other"], "M2 was built under another focus");
    }

    /// A focus the workspace has no manifest for at all: the invocation still
    /// reports what was asked for, and `matched` is honestly empty.
    #[test]
    fn a_focus_no_manifest_was_built_under_matches_nothing() {
        let r = under(&["never"]).expect("a record");
        assert_eq!(r.values, ["never"]);
        assert!(r.matched.is_empty());
    }

    /// Another workspace sharing the `CARGO_TARGET_DIR` cannot contribute,
    /// however exactly its focus agrees.
    #[test]
    fn another_workspaces_manifest_never_speaks_for_this_one() {
        let m = manifests(&[
            ("mine", "/w", Some((&["f"], &["a::f"]))),
            ("theirs", "/other", Some((&["f"], &["z::f"]))),
        ]);
        let r = super::record(&["f".to_owned()], &m, "/w").expect("a record");
        assert_eq!(r.matched, ["a::f"]);
    }

    /// A focus is a SET (design A10). `focus_hash` sorts and de-duplicates
    /// before hashing, so `--focus main --focus load` and `--focus load
    /// --focus main` share a shim path, artifacts and manifests -- and
    /// measured 2026-09-06 on `corpus/rust/silent_swallow`, the second order
    /// then read `focus_matched: []` off a build with six LINE rows and
    /// `line: true`, the exact reading A9 exists to forbid. Both sides of the
    /// comparison are canonicalised the same way; `values` still records what
    /// was typed.
    #[test]
    fn the_order_the_values_were_typed_in_is_not_part_of_the_comparison() {
        let m = manifests(&[("m", "/w", Some((&["load", "main"], &["load", "main"])))]);
        let r = super::record(&["main".to_owned(), "load".to_owned()], &m, "/w").expect("a record");
        assert_eq!(r.values, ["main", "load"], "as GIVEN, not canonicalised");
        assert_eq!(r.matched, ["load", "main"]);
    }

    /// A repeated value is the same set too -- `focus_hash` de-duplicates.
    #[test]
    fn a_repeated_value_is_the_same_focus() {
        let m = manifests(&[("m", "/w", Some((&["a"], &["a::f"])))]);
        let r = super::record(&["a".to_owned(), "a".to_owned()], &m, "/w").expect("a record");
        assert_eq!(r.matched, ["a::f"]);
    }
}
