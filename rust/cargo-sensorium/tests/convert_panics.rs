//! The panic path over spool bytes written by NUMBER, not by helper.
//!
//! Every other panic fixture in this suite reaches the wire through
//! `common::wire`'s typed builders (`panic_record`, `ret_panic`). That makes
//! the converter and the test fixture agree by construction: if the builder
//! and the reader drifted the same way, no test here would notice. These two
//! write the same records with the field values `sensorium-rt/src/spool.rs`'s
//! format block states -- kind 2 RETURN with outcome 3 `panic`, kind 3 PANIC
//! with outcome 0 and site 0 -- so what is pinned is the WIRE FORMAT the
//! converter reads, not the builder that happens to produce it.
//!
//! The second fixture pins the other half the ledger left open: the serial a
//! PANIC record consumes when there is no open frame to attach it to.

mod common;

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use common::wire::{self, site};
use common::Scratch;
use rusqlite::Connection;

const FILE: &str = "crates/demo/src/lib.rs";
const QUALNAME: &str = "main";

/// The wire values `sensorium-rt/src/spool.rs`'s format block names, spelled
/// here rather than imported: this file's whole purpose is to be a second,
/// independent statement of them.
const KIND_RETURN: u8 = 2;
const KIND_PANIC: u8 = 3;
const OUTCOME_OK: u8 = 1;
const OUTCOME_PANIC: u8 = 3;

/// A scratch tree with a real `target` (so a manifests directory can live on
/// disk), one invocation's spool directory under it, and an isolated
/// `SENSORIUM_DIR` this test's traces land in.
#[allow(dead_code)] // `scratch` is held only for its Drop cleanup; `target` documents the layout.
struct Fixture {
    scratch: Scratch,
    target: PathBuf,
    spool_dir: PathBuf,
    manifests_dir: PathBuf,
    sensorium_dir: PathBuf,
}

impl Fixture {
    fn new(name: &str) -> Fixture {
        let scratch = Scratch::in_build_dir(name);
        let target = scratch.p("target");
        let spool_dir = target.join("sensorium/spool/20260903-000000-000000");
        let manifests_dir = target.join("sensorium/manifests");
        let sensorium_dir = scratch.p("sensorium-dir");
        std::fs::create_dir_all(&spool_dir).unwrap();
        std::fs::create_dir_all(&manifests_dir).unwrap();
        wire::write_invocation(
            &spool_dir,
            "20260903-000000-000000",
            "/w",
            &target.to_string_lossy(),
        );
        Fixture {
            scratch,
            target,
            spool_dir,
            manifests_dir,
            sensorium_dir,
        }
    }

    /// The single-site manifest every non-error fixture below builds on:
    /// `crates/demo/src/lib.rs :: main`, the exact strings the blake2b pins
    /// are computed over.
    fn one_site_manifest(&self, metadata: &str, ret: &'static str) {
        wire::write_manifest(
            &self.manifests_dir,
            metadata,
            "demo",
            &[(FILE, &[site(0, QUALNAME, 3, ret)])],
            &[(FILE, "deadbeef")],
            false,
            None,
            &[],
        );
    }

    fn convert(&self) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["convert", &self.spool_dir.to_string_lossy()])
            .env("SENSORIUM_DIR", &self.sensorium_dir)
            .output()
            .expect("run cargo-sensorium convert")
    }

    fn traces(&self) -> Vec<PathBuf> {
        let dir = self.sensorium_dir.join("traces");
        let mut found: Vec<PathBuf> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", dir.display()))
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
            .collect();
        found.sort();
        found
    }
}

fn open(db: &Path) -> Connection {
    Connection::open(db).unwrap_or_else(|e| panic!("cannot open {}: {e}", db.display()))
}

fn meta(conn: &Connection, key: &str) -> serde_json::Value {
    let raw: String = conn
        .query_row("SELECT value FROM meta WHERE key = ?1", [key], |r| r.get(0))
        .unwrap_or_else(|e| panic!("no meta key {key}: {e}"));
    serde_json::from_str(&raw).unwrap()
}

fn context(out: &Output) -> String {
    format!(
        "status: {:?}\n--- stdout ---\n{}\n--- stderr ---\n{}",
        out.status.code(),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

/// A PANIC record's payload, by the format block: `u16 loc_len`, the location
/// bytes, then the message bytes. Written here rather than taken from
/// `wire::panic_record`, for the reason this file exists.
fn panic_payload(loc: &str, msg: &str) -> Vec<u8> {
    let mut payload = u16::try_from(loc.len())
        .expect("a short loc")
        .to_le_bytes()
        .to_vec();
    payload.extend_from_slice(loc.as_bytes());
    payload.extend_from_slice(msg.as_bytes());
    payload
}

/// A RETURN payload with no value: `u8 tag = 0`, `u8 truncated = 0`.
const RET_NO_VALUE: [u8; 2] = [0, 0];

// ---------------------------------------------------------------------------
// The RETURN tag and outcome a panicked frame closes on
// ---------------------------------------------------------------------------

#[test]
fn a_return_written_with_the_wire_formats_own_panic_outcome_closes_the_frame_as_an_unwind() {
    let f = Fixture::new("panic-wire-outcome");
    f.one_site_manifest("meta1", "value");
    wire::write_proc_header(
        &f.spool_dir,
        901,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // Unit 0, site index 0: `site` is `unit_id << 24 | index`, so 0.
    wire::SpoolBuilder::new(901, 1, "main")
        .call(0, 1000, 0, 0)
        .raw(
            1,
            1500,
            0,
            KIND_PANIC,
            0,
            &panic_payload(&format!("{FILE}:3:5"), "boom"),
        )
        .raw(2, 2000, 0, KIND_RETURN, OUTCOME_PANIC, &RET_NO_VALUE)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let (closed_by, unwind_exc): (String, String) = conn
        .query_row(
            "SELECT closed_by, unwind_exc FROM frames LIMIT 1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(closed_by, "unwind", "outcome 3 on a RETURN is the unwind");
    let u: serde_json::Value = serde_json::from_str(&unwind_exc).unwrap();
    assert_eq!(u["type"], "panic");
    assert_eq!(u["msg"], "boom");
    assert_eq!(u["serial"], 1);
    assert_eq!(meta(&conn, "panics_unrecorded"), 0);
}

#[test]
fn the_same_return_with_the_ok_outcome_is_a_return_and_not_an_unwind() {
    // The discriminating half: byte for byte the fixture above with one field
    // changed, so what the first test proves is the OUTCOME and not the shape
    // of the record around it. A converter that read any RETURN after a PANIC
    // record as an unwind would pass the first test and fail this one.
    let f = Fixture::new("panic-wire-outcome-ok");
    f.one_site_manifest("meta1", "value");
    wire::write_proc_header(
        &f.spool_dir,
        902,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(902, 1, "main")
        .call(0, 1000, 0, 0)
        .raw(
            1,
            1500,
            0,
            KIND_PANIC,
            0,
            &panic_payload(&format!("{FILE}:3:5"), "boom"),
        )
        .raw(2, 2000, 0, KIND_RETURN, OUTCOME_OK, &RET_NO_VALUE)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let (closed_by, unwind_exc): (String, Option<String>) = conn
        .query_row(
            "SELECT closed_by, unwind_exc FROM frames LIMIT 1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(closed_by, "return");
    assert_eq!(unwind_exc, None, "an ok RETURN carries no unwind");
}

// ---------------------------------------------------------------------------
// The serial a panic outside every frame consumes
// ---------------------------------------------------------------------------

#[test]
fn a_panic_with_no_open_frame_still_consumes_its_threads_panic_serial() {
    // The serial is a per-thread counter bumped for every PANIC record the
    // thread writes, whether or not there is a frame to attach it to: the
    // number a reader sees is "the nth panic on this thread", not "the nth
    // panic that reached a frame". Two panics here -- the first with the
    // thread's only frame already closed, the second inside a new one -- so
    // the second must read serial 2. Bumping the counter only on the
    // attached branch would give it 1, and no other fixture would notice.
    let f = Fixture::new("panic-outside-serial");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            FILE,
            &[site(0, QUALNAME, 3, "unit"), site(1, "second", 9, "value")],
        )],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        903,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(903, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 1100, 0, 0)
        // Nothing open: counted in `panics_outside_frames`, written as no
        // event -- and it takes serial 1.
        .raw(
            2,
            1200,
            0,
            KIND_PANIC,
            0,
            &panic_payload(&format!("{FILE}:5:1"), "orphan"),
        )
        .call(3, 1300, 0, 1)
        .raw(
            4,
            1400,
            0,
            KIND_PANIC,
            0,
            &panic_payload(&format!("{FILE}:9:1"), "second"),
        )
        .raw(5, 1500, 1, KIND_RETURN, OUTCOME_PANIC, &RET_NO_VALUE)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(meta(&conn, "panics_outside_frames"), 1);
    assert_eq!(meta(&conn, "panics_unrecorded"), 0);

    // Read back off the RAISE the attached panic wrote...
    let payload: String = conn
        .query_row("SELECT payload FROM events WHERE kind = 'RAISE'", [], |r| {
            r.get(0)
        })
        .unwrap();
    let p: serde_json::Value = serde_json::from_str(&payload).unwrap();
    assert_eq!(p["exc"]["msg"], "second");
    assert_eq!(
        p["exc"]["serial"], 2,
        "the orphaned panic took serial 1: {p}"
    );
    // ...and off the frame it unwound, which must be the same number.
    let unwind_exc: String = conn
        .query_row(
            "SELECT unwind_exc FROM frames WHERE closed_by = 'unwind'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let u: serde_json::Value = serde_json::from_str(&unwind_exc).unwrap();
    assert_eq!(u["serial"], 2, "{u}");
}
