//! The per-unit manifest the wrapper (Task 3) writes and the converter
//! (Task 4) reads. Serialise-only: the Python side is the only reader.

use std::collections::BTreeMap;

use serde::Serialize;

use crate::{Skipped, Transformed};

/// One instrumented fn item as it appears in a manifest. The manifest keys
/// sites by file, so [`crate::Site::file`] is not repeated inside.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ManifestSite {
    pub site: u32,
    pub qualname: String,
    pub firstlineno: u32,
}

/// `<target>/sensorium/manifests/<-C metadata>.json` (plan Task 3, verbatim).
#[derive(Debug, Clone, Serialize)]
pub struct Manifest {
    pub unit: String,
    pub crate_name: String,
    pub crate_type: String,
    /// Keyed by the ORIGINAL workspace-relative path, never a mirror path.
    pub files: BTreeMap<String, Vec<ManifestSite>>,
    pub skipped: Vec<Skipped>,
    pub fell_back: bool,
    pub unreached_files: Vec<String>,
    /// Per file: did the crate-root static have to be APPENDED past the end of
    /// the text, adding a final line? True only for the item-free crate roots
    /// [`crate::transform`] documents. Recorded per file because a consumer
    /// checking "no line moved" needs the exception named, not assumed away.
    pub appended_line: BTreeMap<String, bool>,
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
            fell_back: false,
            unreached_files: Vec::new(),
            appended_line: BTreeMap::new(),
        }
    }

    /// Fold one file's result in. The file key comes from the [`crate::Site`]s
    /// themselves, so a manifest can never disagree with what was spliced.
    pub fn add_file(&mut self, path: &str, transformed: &Transformed) {
        let entry = self.files.entry(path.to_owned()).or_default();
        for site in &transformed.sites {
            entry.push(ManifestSite {
                site: site.site,
                qualname: site.qualname.clone(),
                firstlineno: site.firstlineno,
            });
        }
        self.skipped.extend(transformed.skipped.iter().cloned());
        self.appended_line
            .insert(path.to_owned(), transformed.appended_line);
    }

    /// # Errors
    /// Propagates a `serde_json` failure.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }
}
