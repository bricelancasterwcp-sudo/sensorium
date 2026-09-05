//! A hand-built spool directory, converted through the REAL `cargo-sensorium`
//! binary, and the SQLite reads every assertion over it is made from.
//!
//! Shared by the two `convert_errflow*` suites, which are two halves of one
//! subject: `convert_errflow.rs` asks what a record becomes (events, payloads,
//! refusals, meta), and `convert_errflow_chains.rs` asks what a SEQUENCE of
//! them becomes (§2a's chain identity, end to end). They were one file until it
//! passed 800 lines.
//!
//! Every spool is written from the wire block in [`super::wire`], never by
//! running the runtime -- a bug shared by the writer and the reader would pass
//! a fixture built by the writer and cannot pass one built from the format.

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use rusqlite::Connection;

use super::wire::{self, err_site, site, SiteSpec};
use super::Scratch;

pub const FILE: &str = "crates/demo/src/lib.rs";

/// Record kinds and `how` bytes as NUMBERS: these are wire-format values, and
/// asserting them against the converter's own constants would pin nothing.
pub const KIND_RAISE: u8 = 4;
pub const KIND_HANDLED: u8 = 5;
pub const HOW_TRY: u8 = 1;
pub const HOW_SINK_OK: u8 = 2;
pub const HOW_ARM_PROPAGATE: u8 = 5;
pub const HOW_ARM_AMBIGUOUS: u8 = 7;

#[allow(dead_code)] // `scratch` is held only for its Drop cleanup.
pub struct Fixture {
    scratch: Scratch,
    pub spool_dir: PathBuf,
    manifests_dir: PathBuf,
    sensorium_dir: PathBuf,
}

impl Fixture {
    pub fn new(name: &str) -> Fixture {
        let scratch = Scratch::in_build_dir(name);
        let target = scratch.p("target");
        let spool_dir = target.join("sensorium/spool/20260904-000000-000000");
        let manifests_dir = target.join("sensorium/manifests");
        let sensorium_dir = scratch.p("sensorium-dir");
        std::fs::create_dir_all(&spool_dir).unwrap();
        std::fs::create_dir_all(&manifests_dir).unwrap();
        wire::write_invocation(
            &spool_dir,
            "20260904-000000-000000",
            "/w",
            &target.to_string_lossy(),
        );
        Fixture {
            scratch,
            spool_dir,
            manifests_dir,
            sensorium_dir,
        }
    }

    pub fn manifest(&self, sites: &[SiteSpec]) {
        wire::write_manifest(
            &self.manifests_dir,
            "meta1",
            "demo",
            &[(FILE, sites)],
            &[(FILE, "deadbeef")],
            false,
            None,
            &[],
        );
    }

    pub fn convert(&self) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["convert", &self.spool_dir.to_string_lossy()])
            .env("SENSORIUM_DIR", &self.sensorium_dir)
            .output()
            .expect("run cargo-sensorium convert")
    }

    /// Convert, insisting it succeeded, and open the single trace it wrote.
    pub fn converted(&self) -> Connection {
        let out = self.convert();
        assert!(out.status.success(), "{}", context(&out));
        let dir = self.sensorium_dir.join("traces");
        let mut found: Vec<PathBuf> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", dir.display()))
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
            .collect();
        found.sort();
        assert_eq!(found.len(), 1, "one trace, got {found:?}");
        open(&found[0])
    }

    pub fn refusal(&self) -> String {
        let out = self.convert();
        assert!(
            !out.status.success(),
            "expected a refusal: {}",
            context(&out)
        );
        String::from_utf8_lossy(&out.stderr).into_owned()
    }
}

pub fn open(db: &Path) -> Connection {
    Connection::open(db).unwrap_or_else(|e| panic!("cannot open {}: {e}", db.display()))
}

pub fn context(out: &Output) -> String {
    format!(
        "status: {:?}\n--- stdout ---\n{}\n--- stderr ---\n{}",
        out.status.code(),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

pub fn meta(conn: &Connection, key: &str) -> serde_json::Value {
    let raw: String = conn
        .query_row("SELECT value FROM meta WHERE key = ?1", [key], |r| r.get(0))
        .unwrap_or_else(|e| panic!("no meta key {key}: {e}"));
    serde_json::from_str(&raw).unwrap()
}

/// Every event, in id order: `(kind, line, payload)`.
pub fn events(conn: &Connection) -> Vec<(String, Option<i64>, serde_json::Value)> {
    let mut stmt = conn
        .prepare("SELECT kind, line, payload FROM events ORDER BY id")
        .unwrap();
    let rows = stmt
        .query_map([], |r| {
            let payload: Option<String> = r.get(2)?;
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, Option<i64>>(1)?,
                payload.map_or(serde_json::Value::Null, |p| {
                    serde_json::from_str(&p).unwrap()
                }),
            ))
        })
        .unwrap();
    rows.map(Result::unwrap).collect()
}

pub fn kinds(conn: &Connection) -> Vec<String> {
    events(conn).into_iter().map(|(k, _, _)| k).collect()
}

/// `outer` calls `inner`; `inner` returns `Err`; `outer`'s `?` re-raises it and
/// `outer` returns by the `?` bypass (wire outcome `none`). The manifest below
/// is the one every fixture in this file starts from.
pub fn two_fns_and_a_try() -> Vec<SiteSpec> {
    vec![
        site(0, "outer", 3, "value"),
        site(1, "inner", 10, "value"),
        err_site(2, "outer", 5, "try", "try"),
    ]
}
