//! Optional trace meta from `<spool>/<pid>.elision.json`.
//!
//! The runtime writes the sidecar when it dropped at least one call. A
//! spool from before caps has no file, and conversion still succeeds with
//! no truncation meta. The site rows name a unit id and a site index; the
//! file, qualname and first line come from the manifest the converter
//! already loaded. Nothing here is part of the required meta list, and the
//! base schema is untouched.

use std::collections::BTreeMap;
use std::path::Path;

use serde::Deserialize;
use serde_json::{json, Value};

use crate::convert::manifest::Manifest;

#[derive(Deserialize)]
struct Sidecar {
    max_events: u64,
    max_bytes: u64,
    max_calls: u64,
    hit: Vec<String>,
    events_recorded: u64,
    calls_elided: u64,
    #[serde(default)]
    failures_kept: u64,
    #[serde(default)]
    sites: Vec<SidecarSite>,
}

#[derive(Deserialize)]
struct SidecarSite {
    unit: u32,
    site: u32,
    elided: u64,
    kept: u64,
}

const HIT_NAMES: &[&str] = &["max_calls", "max_events", "max_bytes"];

/// Meta rows for one process, or `None` when nothing was dropped.
///
/// # Errors
/// The sidecar exists and is not the object this converter writes, a hit
/// name is not one of the three caps, or a site is not in the unit's
/// manifest.
pub fn meta(
    spool_dir: &Path,
    pid: u32,
    units: &BTreeMap<String, String>,
    manifests: &BTreeMap<String, Manifest>,
    workspace_root: &str,
) -> Result<Option<Vec<(&'static str, Value)>>, String> {
    let path = spool_dir.join(format!("{pid}.elision.json"));
    if !path.is_file() {
        return Ok(None);
    }
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    let side: Sidecar = serde_json::from_str(&text)
        .map_err(|e| format!("{} is not an elision sidecar: {e}", path.display()))?;
    if side.calls_elided == 0 {
        return Ok(None);
    }
    for name in &side.hit {
        if !HIT_NAMES.contains(&name.as_str()) {
            return Err(format!(
                "{}: hit {name:?} is not max_calls, max_events or max_bytes",
                path.display()
            ));
        }
    }
    let mut elisions = Vec::new();
    for row in &side.sites {
        if row.elided == 0 {
            continue;
        }
        let metadata = units.get(&row.unit.to_string()).ok_or_else(|| {
            format!(
                "pid {pid}: elision unit {} is not in the proc header",
                row.unit
            )
        })?;
        let manifest = manifests
            .get(metadata)
            .ok_or_else(|| format!("pid {pid}: no manifest for elision unit {metadata}"))?;
        let sites = manifest.sites_by_index();
        let info = sites.get(&row.site).ok_or_else(|| {
            format!(
                "pid {pid}: elision site {}:{} is not in the manifest",
                row.unit, row.site
            )
        })?;
        let file = std::path::Path::new(workspace_root)
            .join(&info.file)
            .to_string_lossy()
            .into_owned();
        elisions.push(json!({
            "file": file,
            "qualname": info.qualname,
            "firstlineno": info.line,
            "elided": row.elided,
            "kept": row.kept,
        }));
    }
    let mut limits = json!({
        "max_events": side.max_events,
        "max_bytes": side.max_bytes,
        "max_calls": side.max_calls,
        "hit": side.hit,
        "events_recorded": side.events_recorded,
        "calls_elided": side.calls_elided,
    });
    if side.failures_kept > 0 {
        limits["failures_kept"] = json!(side.failures_kept);
    }
    Ok(Some(vec![
        ("trace_truncated", json!(true)),
        ("trace_limits", limits),
        ("elisions", Value::Array(elisions)),
    ]))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::convert::manifest::Manifest;

    fn manifest() -> Manifest {
        serde_json::from_str(
            r#"{"unit":"abc","crate_name":"demo","fell_back":false,"fallback_reason":null,
                "files":{"src/lib.rs":[{"site":7,"qualname":"leaf","firstlineno":4,"ret":"unit"}]}}"#,
        )
        .unwrap()
    }

    fn units() -> BTreeMap<String, String> {
        let mut u = BTreeMap::new();
        u.insert("0".to_owned(), "abc".to_owned());
        u
    }

    fn manifests() -> BTreeMap<String, Manifest> {
        let mut m = BTreeMap::new();
        m.insert("abc".to_owned(), manifest());
        m
    }

    fn scratch(name: &str) -> std::path::PathBuf {
        let dir =
            std::env::temp_dir().join(format!("sensorium-elision-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn a_missing_sidecar_writes_no_truncation_meta() {
        let dir = scratch("missing");
        let got = meta(&dir, 1, &units(), &manifests(), "/w").unwrap();
        assert!(got.is_none());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_sidecar_becomes_truncation_meta_joined_to_the_manifest() {
        let dir = scratch("join");
        std::fs::write(
            dir.join("9.elision.json"),
            r#"{"max_events":0,"max_bytes":0,"max_calls":3,"hit":["max_calls"],
                "events_recorded":8,"calls_elided":17,
                "sites":[{"unit":0,"site":7,"elided":17,"kept":3}]}"#,
        )
        .unwrap();
        let rows = meta(&dir, 9, &units(), &manifests(), "/w")
            .unwrap()
            .unwrap();
        assert_eq!(rows[0].0, "trace_truncated");
        assert_eq!(rows[0].1, json!(true));
        let limits = &rows[1].1;
        assert_eq!(limits["hit"], json!(["max_calls"]));
        assert_eq!(limits["calls_elided"], json!(17));
        assert_eq!(limits["max_calls"], json!(3));
        assert!(limits.get("failures_kept").is_none());
        let row = &rows[2].1[0];
        assert_eq!(row["qualname"], "leaf");
        assert_eq!(row["firstlineno"], 4);
        assert_eq!(row["elided"], 17);
        assert_eq!(row["kept"], 3);
        assert_eq!(row["file"], "/w/src/lib.rs");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn failures_kept_is_copied_only_when_present() {
        let dir = scratch("fail");
        std::fs::write(
            dir.join("1.elision.json"),
            r#"{"max_events":0,"max_bytes":0,"max_calls":3,"hit":["max_calls"],
                "events_recorded":9,"calls_elided":1,"failures_kept":1,
                "sites":[{"unit":0,"site":7,"elided":1,"kept":4}]}"#,
        )
        .unwrap();
        let rows = meta(&dir, 1, &units(), &manifests(), "/w")
            .unwrap()
            .unwrap();
        assert_eq!(rows[1].1["failures_kept"], json!(1));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_zero_elided_count_writes_nothing() {
        let dir = scratch("zero");
        std::fs::write(
            dir.join("1.elision.json"),
            r#"{"max_events":0,"max_bytes":0,"max_calls":3,"hit":[],
                "events_recorded":4,"calls_elided":0,"sites":[]}"#,
        )
        .unwrap();
        assert!(meta(&dir, 1, &units(), &manifests(), "/w")
            .unwrap()
            .is_none());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
