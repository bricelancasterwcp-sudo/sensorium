//! The unit manifests: what the transformer wrote about a unit's sites, read
//! back by the converter.
//!
//! A separate module from [`crate::convert::spool`] because it is a separate
//! contract: the spool's wire format is bytes this reader mirrors
//! independently of the writer, while a manifest is JSON whose keys the
//! transformer and this reader agree on by name. What they share is only that
//! both are inputs, and both are read defensively -- an unknown key is
//! ignored, and a missing one is a fact about the version that wrote it (design
//! R1b: a 0.2.0 manifest has no `kind`, and every site in it was a fn).

use std::collections::BTreeMap;
use std::path::Path;

use serde::Deserialize;

use crate::convert::spool::How;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RetKind {
    Unit,
    Value,
    Never,
}

/// What a manifest row says a site IS (design R1b). A row with no `kind` at
/// all is a 0.2.0 manifest's, where every site was a fn item -- which is what
/// [`Default`] says here.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SiteKind {
    #[default]
    Fn,
    Closure,
    Try,
    Sink,
    Arm,
}

impl SiteKind {
    /// `fn` and `closure` sites carry a guard, so a CALL/RETURN may name one
    /// and a RAISE/HANDLED may not. The three err-flow kinds are the mirror.
    #[must_use]
    pub fn is_frame(self) -> bool {
        matches!(self, SiteKind::Fn | SiteKind::Closure)
    }

    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            SiteKind::Fn => "fn",
            SiteKind::Closure => "closure",
            SiteKind::Try => "try",
            SiteKind::Sink => "sink",
            SiteKind::Arm => "arm",
        }
    }
}

/// One row of a manifest's `files` map.
///
/// Everything but `site`, `qualname` and `kind` is optional because a row's
/// SHAPE depends on its kind (design R1b): a fn row carries `firstlineno` and
/// `ret`, an err-flow row carries `line` and `how`, and a 0.2.0 manifest
/// carries neither `kind` nor the marks. Defaults here are what makes an old
/// manifest readable; they are never a substitute for a fact the manifest
/// could have stated.
#[derive(Debug, Deserialize)]
pub struct ManifestSite {
    pub site: u32,
    pub qualname: String,
    #[serde(default)]
    pub kind: SiteKind,
    /// A fn item's own first line. Absent on every row that is not a fn ITEM,
    /// closures included.
    #[serde(default)]
    pub firstlineno: Option<u32>,
    /// The `?`, the sink's method name, the `Err` pattern, or a closure's `|`.
    #[serde(default)]
    pub line: Option<u32>,
    #[serde(default)]
    pub how: Option<String>,
    /// A signature's answer, so only a frame row has one.
    #[serde(default)]
    pub ret: Option<RetKind>,
    #[serde(default)]
    pub test: bool,
    #[serde(default)]
    pub main: bool,
}

/// `<target>/sensorium/manifests/<metadata>.json`, read back. A separate type
/// from `sensorium_transform::Manifest`, which is serialise-only.
#[derive(Debug, Deserialize)]
pub struct Manifest {
    /// The manifest's own filename already names this (its stem is the
    /// metadata); kept for the same reason as [`ProcHeader::pid`].
    #[allow(dead_code)]
    pub unit: String,
    pub crate_name: String,
    #[serde(default)]
    pub files: BTreeMap<String, Vec<ManifestSite>>,
    #[serde(default)]
    pub skipped: Vec<serde_json::Value>,
    /// Err-flow sites the transformer could not reach (design R6). Passed
    /// through verbatim, registered-unit-scoped like `skipped`; `#[serde(
    /// default)]` so a 0.2.0 manifest -- written before the key existed --
    /// reads as an empty list rather than refusing the whole unit.
    #[serde(default)]
    pub partial: Vec<serde_json::Value>,
    #[serde(default)]
    pub spawns: Vec<serde_json::Value>,
    #[serde(default)]
    pub source_hashes: BTreeMap<String, String>,
    pub fell_back: bool,
    pub fallback_reason: Option<String>,
    #[serde(default)]
    pub unreached_files: Vec<String>,
    /// The workspace the wrapper compiled this unit under
    /// (`SENSORIUM_WS`). `#[serde(default)]` so a manifest written before
    /// this field existed deserialises as `""` -- treated as "not in scope
    /// of any invocation" by `manifest_in_scope`, and counted in the meta
    /// key `manifests_unscoped` rather than silently excluded with no trace.
    #[serde(default)]
    pub workspace_root: String,
}

/// One site, as the converter needs it: which file it is in (the manifest's
/// own key -- workspace-relative), and everything the manifest says about it.
///
/// `line` is the row's ONE line number, whichever key the manifest spelled it
/// under: `firstlineno` on a fn item, `line` on everything else. The two keys
/// are different facts in a manifest (an item's start against an operator's
/// position) and every consumer here wants the same thing from them -- where
/// to point a person at.
pub struct SiteInfo {
    pub file: String,
    pub qualname: String,
    pub line: u32,
    pub kind: SiteKind,
    pub how: Option<String>,
    pub ret: Option<RetKind>,
    pub test: bool,
    pub main: bool,
}

impl SiteInfo {
    /// `<file>:<line>`, the `loc` an `exc` object carries.
    #[must_use]
    pub fn loc(&self) -> String {
        format!("{}:{}", self.file, self.line)
    }

    /// # Errors
    /// This site cannot open a frame: a CALL or RETURN naming it is malformed
    /// (design R1b), and the error names the site rather than the record so a
    /// person can go and look at it.
    pub fn require_frame(&self, what: &str) -> Result<(), String> {
        if self.kind.is_frame() {
            return Ok(());
        }
        Err(format!(
            "{what} names site {}:{} ({}), which the manifest says is a `{}` site, not a frame",
            self.file,
            self.line,
            self.qualname,
            self.kind.as_str()
        ))
    }

    /// # Errors
    /// This site is a frame, so no err-flow record may name it (design R1b) --
    /// or the `how` the record carries is not the one the manifest says this
    /// site writes. The transformer wrote the row and the runtime wrote the
    /// byte from the SAME splice, so a disagreement is corruption, and the
    /// check is the one place the two halves of R2 are held against each other.
    pub fn require_err_flow(&self, what: &str, how: How) -> Result<(), String> {
        if self.kind.is_frame() {
            return Err(format!(
                "{what} names site {}:{} ({}), which the manifest says is a `{}` frame site, not \
                 an err-flow site",
                self.file,
                self.line,
                self.qualname,
                self.kind.as_str()
            ));
        }
        match &self.how {
            Some(declared) if declared != how.as_str() => Err(format!(
                "{what} carries how `{}`, but the manifest says site {}:{} ({}) writes `{declared}`",
                how.as_str(),
                self.file,
                self.line,
                self.qualname,
            )),
            _ => Ok(()),
        }
    }
}

impl Manifest {
    /// # Errors
    /// A filesystem or JSON failure, or a file key naming a path under
    /// `sensorium/mirror` -- a manifest that names the internal mirror tree
    /// instead of the workspace-relative source is a hard error naming the
    /// manifest file, not a value this converter passes through.
    pub fn read(path: &Path) -> Result<Manifest, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let m: Manifest = serde_json::from_str(&text)
            .map_err(|e| format!("{} is not a valid manifest: {e}", path.display()))?;
        for rel in m
            .files
            .keys()
            .chain(m.unreached_files.iter())
            .chain(m.source_hashes.keys())
        {
            if rel.contains("sensorium/mirror") {
                return Err(format!(
                    "{}: names a mirror path {rel:?}, not a workspace-relative one",
                    path.display()
                ));
            }
        }
        Ok(m)
    }

    /// Flatten `files` into a lookup by the unit-relative site index the wire
    /// format's `site` word carries.
    #[must_use]
    pub fn sites_by_index(&self) -> BTreeMap<u32, SiteInfo> {
        let mut out = BTreeMap::new();
        for (file, sites) in &self.files {
            for s in sites {
                out.insert(
                    s.site,
                    SiteInfo {
                        file: file.clone(),
                        qualname: s.qualname.clone(),
                        // A fn row spells it `firstlineno` and an err-flow row
                        // spells it `line`; a row with neither is a manifest
                        // that stated no position at all, and 0 is what this
                        // reader has to say about it (`<file>:0`), not a line
                        // it made up.
                        line: s.firstlineno.or(s.line).unwrap_or(0),
                        kind: s.kind,
                        how: s.how.clone(),
                        ret: s.ret,
                        test: s.test,
                        main: s.main,
                    },
                );
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_manifest_naming_a_mirror_path_is_refused() {
        let dir = std::env::temp_dir().join(format!("manifest-mirror-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(
            &path,
            r#"{"unit":"a","crate_name":"c","crate_type":"lib","files":{"target/sensorium/mirror/a/src/lib.rs":[]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,"fallback_reason":null,"unreached_files":[]}"#,
        )
        .unwrap();
        let err = Manifest::read(&path).unwrap_err();
        assert!(err.contains("mirror path"), "{err}");
    }

    #[test]
    fn sites_by_index_flattens_across_files() {
        let dir = std::env::temp_dir().join(format!("manifest-sites-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(
            &path,
            r#"{"unit":"a","crate_name":"c","crate_type":"lib",
               "files":{"a/lib.rs":[{"site":0,"qualname":"root","firstlineno":1,"ret":"unit"}],
                        "a/m.rs":[{"site":1,"qualname":"one","firstlineno":2,"ret":"value"}]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,"fallback_reason":null,"unreached_files":[]}"#,
        )
        .unwrap();
        let m = Manifest::read(&path).unwrap();
        let sites = m.sites_by_index();
        assert_eq!(sites[&0].qualname, "root");
        assert_eq!(sites[&0].file, "a/lib.rs");
        assert_eq!(sites[&1].ret, Some(RetKind::Value));
    }

    /// The wrapper writes `unreached_reasons` (why a file the walk reached was
    /// still not rewritten) and this converter has nothing to say about it: the
    /// trace format carries no such key. That only works because this struct
    /// does NOT deny unknown fields -- add `#[serde(deny_unknown_fields)]` and
    /// every manifest the current wrapper writes becomes unreadable, taking the
    /// whole unit's sites down with it.
    #[test]
    fn a_manifest_key_this_converter_has_no_field_for_is_ignored_not_refused() {
        let dir = std::env::temp_dir().join(format!("manifest-unknown-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(
            &path,
            r#"{"unit":"a","crate_name":"c","crate_type":"lib",
               "files":{"a/lib.rs":[{"site":0,"qualname":"root","firstlineno":1,"ret":"unit"}]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,"fallback_reason":null,
               "unreached_files":["a/bad.rs"],
               "unreached_reasons":{"a/bad.rs":"spawn site outside any named item"}}"#,
        )
        .unwrap();
        let m = Manifest::read(&path).expect("a manifest with an extra key still reads");
        assert_eq!(m.unreached_files, ["a/bad.rs"]);
        assert_eq!(m.sites_by_index()[&0].qualname, "root");
    }

    fn write(name: &str, body: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("manifest-{name}-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("m.json");
        std::fs::write(&path, body).unwrap();
        path
    }

    /// A 0.2.0 manifest has no `kind`, no marks and no `line`: every site in it
    /// WAS a fn, and reading it as anything else would take a whole unit's
    /// sites down (design R1b).
    #[test]
    fn a_manifest_written_before_kinds_existed_reads_as_all_fn() {
        let path = write(
            "pre-kind",
            r#"{"unit":"a","crate_name":"c","crate_type":"lib",
               "files":{"a/lib.rs":[{"site":0,"qualname":"root","firstlineno":4,"ret":"unit"}]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,
               "fallback_reason":null,"unreached_files":[]}"#,
        );
        let m = Manifest::read(&path).unwrap();
        let sites = m.sites_by_index();
        assert_eq!(sites[&0].kind, SiteKind::Fn);
        assert!(sites[&0].kind.is_frame());
        assert_eq!(sites[&0].line, 4, "a fn row's line is its `firstlineno`");
        assert_eq!(sites[&0].ret, Some(RetKind::Unit));
        assert!(!sites[&0].test);
        assert!(!sites[&0].main);
        assert_eq!(sites[&0].how, None);
        assert!(m.partial.is_empty(), "an absent `partial` is an empty one");
    }

    /// The 0.3.0 shapes: an err-flow row spells its position `line` and carries
    /// the `how` it writes; a closure row is a FRAME that also spells it
    /// `line`; a fn row can carry the marks.
    #[test]
    fn the_typed_rows_read_their_own_keys() {
        let path = write(
            "typed",
            r#"{"unit":"a","crate_name":"c","crate_type":"bin",
               "files":{"a/lib.rs":[
                 {"site":0,"qualname":"main","kind":"fn","firstlineno":1,"ret":"value","main":true},
                 {"site":1,"qualname":"t","kind":"fn","firstlineno":9,"ret":"unit","test":true},
                 {"site":2,"qualname":"main::{{closure}}#0","kind":"closure","line":3,"ret":"value"},
                 {"site":3,"qualname":"main","kind":"try","line":5,"how":"try"},
                 {"site":4,"qualname":"main","kind":"sink","line":6,"how":"sink_ok"},
                 {"site":5,"qualname":"main","kind":"arm","line":7,"how":"arm_handled"}]},
               "skipped":[],"partial":[{"file":"a/lib.rs","line":8,"qualname":"main",
                                        "kind":"try","reason":"macro-arg"}],
               "spawns":[],"source_hashes":{},"fell_back":false,
               "fallback_reason":null,"unreached_files":[]}"#,
        );
        let m = Manifest::read(&path).unwrap();
        let sites = m.sites_by_index();
        assert!(sites[&0].main);
        assert!(sites[&1].test);
        assert_eq!(sites[&2].kind, SiteKind::Closure);
        assert!(sites[&2].kind.is_frame(), "a closure carries a guard");
        assert_eq!(sites[&2].line, 3, "a closure spells its position `line`");
        assert_eq!(sites[&3].kind, SiteKind::Try);
        assert!(!sites[&3].kind.is_frame());
        assert_eq!(sites[&3].line, 5);
        assert_eq!(sites[&3].how.as_deref(), Some("try"));
        assert_eq!(sites[&4].kind, SiteKind::Sink);
        assert_eq!(sites[&5].kind, SiteKind::Arm);
        assert_eq!(sites[&3].ret, None, "an err-flow site has no signature");
        assert_eq!(m.partial.len(), 1);
        assert_eq!(m.partial[0]["reason"], "macro-arg");
    }

    /// `<file>:<line>`, the `loc` every `exc` object carries.
    #[test]
    fn a_sites_loc_is_its_file_and_its_own_line() {
        let s = SiteInfo {
            file: "a/lib.rs".to_owned(),
            qualname: "f".to_owned(),
            line: 12,
            kind: SiteKind::Try,
            how: Some("try".to_owned()),
            ret: None,
            test: false,
            main: false,
        };
        assert_eq!(s.loc(), "a/lib.rs:12");
    }

    fn site_of(kind: SiteKind, how: Option<&str>) -> SiteInfo {
        SiteInfo {
            file: "a/lib.rs".to_owned(),
            qualname: "f".to_owned(),
            line: 12,
            kind,
            how: how.map(str::to_owned),
            ret: None,
            test: false,
            main: false,
        }
    }

    /// Design R1b: a CALL or RETURN naming a site that carries no guard is
    /// malformed, and the refusal names the SITE, because that is what a
    /// person has to go and look at.
    #[test]
    fn a_frame_record_on_an_err_flow_site_is_refused_by_name() {
        for kind in [SiteKind::Try, SiteKind::Sink, SiteKind::Arm] {
            let err = site_of(kind, Some("try"))
                .require_frame("CALL")
                .unwrap_err();
            assert!(err.contains("CALL"), "{err}");
            assert!(err.contains("a/lib.rs:12"), "{err}");
            assert!(err.contains("(f)"), "{err}");
            assert!(err.contains(kind.as_str()), "{err}");
            assert!(err.contains("not a frame"), "{err}");
        }
        assert!(site_of(SiteKind::Fn, None).require_frame("CALL").is_ok());
        assert!(site_of(SiteKind::Closure, None)
            .require_frame("CALL")
            .is_ok());
    }

    #[test]
    fn an_err_flow_record_on_a_frame_site_is_refused_by_name() {
        for kind in [SiteKind::Fn, SiteKind::Closure] {
            let err = site_of(kind, None)
                .require_err_flow("RAISE", How::Try)
                .unwrap_err();
            assert!(err.contains("RAISE"), "{err}");
            assert!(err.contains("a/lib.rs:12"), "{err}");
            assert!(err.contains(kind.as_str()), "{err}");
            assert!(err.contains("not an err-flow site"), "{err}");
        }
    }

    /// The manifest row and the wire byte were written by the same splice, so
    /// the two disagreeing is corruption -- and a row that declares no `how`
    /// (a 0.2.0 manifest) makes no claim to contradict.
    #[test]
    fn a_how_the_manifest_contradicts_is_refused_and_a_silent_row_is_not() {
        let err = site_of(SiteKind::Sink, Some("sink_unwrap_or"))
            .require_err_flow("HANDLED", How::SinkOk)
            .unwrap_err();
        assert!(err.contains("how `sink_ok`"), "{err}");
        assert!(err.contains("writes `sink_unwrap_or`"), "{err}");
        assert!(site_of(SiteKind::Sink, Some("sink_ok"))
            .require_err_flow("HANDLED", How::SinkOk)
            .is_ok());
        assert!(site_of(SiteKind::Sink, None)
            .require_err_flow("HANDLED", How::SinkOk)
            .is_ok());
    }

    /// The two line keys are different facts, and a reader that wants one
    /// number must take whichever the row spelled -- with 0 for a row that
    /// spelled neither, which is a silence, not a line.
    #[test]
    fn a_row_with_no_line_at_all_reads_as_zero_rather_than_a_guess() {
        let path = write(
            "no-line",
            r#"{"unit":"a","crate_name":"c","crate_type":"lib",
               "files":{"a/lib.rs":[{"site":0,"qualname":"f","kind":"try","how":"try"}]},
               "skipped":[],"spawns":[],"source_hashes":{},"fell_back":false,
               "fallback_reason":null,"unreached_files":[]}"#,
        );
        let m = Manifest::read(&path).unwrap();
        assert_eq!(m.sites_by_index()[&0].line, 0);
    }
}
