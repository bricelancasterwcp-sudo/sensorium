//! The per-unit manifest the wrapper (Task 5) writes and the converter (Task 8)
//! reads. Serialise-only: nothing in this crate reads one back.
//!
//! `<target>/sensorium/manifests/<-C metadata>.json`. It is the join between a
//! trace and the source it was recorded from -- and, for everything this
//! recorder deliberately does not do, it is the DECLARATION: `skipped` carries
//! the fn items that were left alone and why (`rust/HONESTY.md` §8 items 5 and
//! 6), `spawns` the thread-spawning shapes that were not rewritten (§3),
//! `unreached_files` the modules the walk could not reach (§8 item 8),
//! `unreached_reasons` what a file the walk DID reach failed with, and
//! `fell_back`/`fallback_reason` a unit that is not instrumented at all (§8
//! item 7).
//!
//! `unreached_reasons` (added 2026-09-03) is keyed by the same
//! workspace-relative path as `unreached_files` and holds only the entries the
//! wrapper has an actual message for -- in practice, the files
//! [`crate::transform`] returned an `Err` for. A file the transformer REFUSED
//! (an unparseable file, or one of this crate's own synthesised errors: a spawn
//! with no named item around it, a rewrite that moved a line, an ordinal that
//! disagrees with source order) is a different fact from a module path the walk
//! never resolved, and before this key both arrived at a reader as one
//! undifferentiated list with the message dropped. Nothing downstream reads it:
//! `docs/TRACE-FORMAT.md` gives it no trace key, and the converter's own
//! `Manifest` has no field for it (it ignores unknown keys) -- so it is a
//! record for a person, not an input to a join.

use std::collections::BTreeMap;

use serde::Serialize;

use crate::{RetKind, Skipped, SpawnSite, Transformed};

/// One instrumented fn item as it appears in a manifest. The manifest keys sites
/// by file, so [`crate::Site::file`] is not repeated inside.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ManifestSite {
    pub site: u32,
    pub qualname: String,
    pub firstlineno: u32,
    /// `"unit"`, `"value"` or `"never"`. The wire carries no per-site knowledge,
    /// so this is what tells the converter that a frame which stashed nothing
    /// closed `ok` with `()` rather than `none` (`rust/HONESTY.md` §1).
    pub ret: RetKind,
}

/// The unit manifest, in the shape the plan names.
#[derive(Debug, Clone, Serialize)]
pub struct Manifest {
    pub unit: String,
    pub crate_name: String,
    pub crate_type: String,
    /// Keyed by the ORIGINAL workspace-relative path, never a mirror path.
    pub files: BTreeMap<String, Vec<ManifestSite>>,
    pub skipped: Vec<Skipped>,
    pub spawns: Vec<SpawnSite>,
    /// SHA-256, hex, of each file's ORIGINAL bytes. Filled by the wrapper: this
    /// crate never opens a file, so it never sees the bytes to hash.
    pub source_hashes: BTreeMap<String, String>,
    pub fell_back: bool,
    /// Why, when `fell_back`. Filled by the wrapper, which is the only thing
    /// that can know: `rustc: <first error line>`, `lto`, `cross-target`, an
    /// absolute crate root, or `wrapper: <error>`.
    pub fallback_reason: Option<String>,
    pub unreached_files: Vec<String>,
    /// Why, for the subset of `unreached_files` the wrapper has words for: the
    /// parse error, or one of the errors this crate synthesises. A file the
    /// wrapper could not even READ is absent from here on purpose -- there is
    /// no message to quote, and an invented one would be worse than the
    /// silence. Serialised always, empty when there is nothing to say --
    /// a key that appears only when non-empty makes "no reasons" and "a reader
    /// that predates the key" the same bytes. Filled by the wrapper: this crate
    /// never opens a file and never sees its own errors come back.
    pub unreached_reasons: BTreeMap<String, String>,
    /// Per file: did the crate-root static have to be APPENDED past the end of
    /// the text, adding a final line? True only for the item-free crate roots
    /// [`crate::transform`] documents. Recorded per file because a consumer
    /// checking "no line moved" needs the exception named, not assumed away.
    pub appended_line: BTreeMap<String, bool>,
    /// The workspace this unit was compiled under (the wrapper's
    /// `SENSORIUM_WS`). A shared `CARGO_TARGET_DIR` holds every workspace's
    /// manifests in one `sensorium/manifests/` directory, and this is the
    /// only field that tells the converter which invocation a given manifest
    /// belongs to -- `Manifest::new` leaves it empty; the wrapper sets it
    /// once it knows.
    pub workspace_root: String,
}

impl Manifest {
    #[must_use]
    pub fn new(unit: &str, crate_name: &str, crate_type: &str) -> Self {
        Manifest {
            unit: unit.to_owned(),
            crate_name: crate_name.to_owned(),
            crate_type: crate_type.to_owned(),
            files: BTreeMap::new(),
            skipped: Vec::new(),
            spawns: Vec::new(),
            source_hashes: BTreeMap::new(),
            fell_back: false,
            fallback_reason: None,
            unreached_files: Vec::new(),
            unreached_reasons: BTreeMap::new(),
            appended_line: BTreeMap::new(),
            workspace_root: String::new(),
        }
    }

    /// Fold one file's result in. Everything except the key comes from the
    /// [`Transformed`] itself, so a manifest can never disagree with what was
    /// spliced.
    pub fn add_file(&mut self, path: &str, transformed: &Transformed) {
        let entry = self.files.entry(path.to_owned()).or_default();
        for site in &transformed.sites {
            entry.push(ManifestSite {
                site: site.site,
                qualname: site.qualname.clone(),
                firstlineno: site.firstlineno,
                ret: site.ret,
            });
        }
        self.skipped.extend(transformed.skipped.iter().cloned());
        self.spawns.extend(transformed.spawns.iter().cloned());
        self.appended_line
            .insert(path.to_owned(), transformed.appended_line);
    }

    /// # Errors
    /// Propagates a `serde_json` failure.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
}
