//! Meta-key content this recorder's own honesty promises name, over
//! hand-built fixtures: `uninstrumented` (a fallen-back unit still reaches
//! the trace, `rust/HONESTY.md` §8 item 7), `panics_outside_frames` (a
//! PANIC record with no open frame is counted, not silently dropped, §1),
//! and the workspace scoping of `uninstrumented` (and ONLY `uninstrumented`
//! -- see below) -- a shared `CARGO_TARGET_DIR` holds every workspace's
//! manifests in one `sensorium/manifests/` directory (measured live on the
//! Task 10 corpus: 13 unrelated crates sharing one target, each trace's
//! `info` printing another crate's `fell back` line).
//!
//! `skipped`/`spawns`/`unreached_files`/`source_hashes` are gathered ONLY
//! for the units `c.proc.units_in_order()` registered and are deliberately
//! NOT workspace-filtered: that scope is already correct by construction,
//! and cargo's freshness caching can leave a registered unit's OWN manifest
//! on disk from a build old enough to predate `workspace_root` entirely
//! (the same corpus caught this: `rust/spawned_thread`'s own cached
//! manifest carried no `workspace_root`, and filtering this loop the same
//! way `uninstrumented` is filtered silently dropped its own spawn site).

mod common;

use std::path::PathBuf;
use std::process::{Command, Output};

use common::wire::{self, site};
use common::Scratch;
use rusqlite::Connection;

const FILE: &str = "crates/demo/src/lib.rs";

#[allow(dead_code)]
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

    fn convert(&self) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["convert", &self.spool_dir.to_string_lossy()])
            .env("SENSORIUM_DIR", &self.sensorium_dir)
            .output()
            .expect("run cargo-sensorium convert")
    }

    fn only_trace(&self) -> Connection {
        let dir = self.sensorium_dir.join("traces");
        let found: Vec<PathBuf> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", dir.display()))
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
            .collect();
        assert_eq!(found.len(), 1, "{found:?}");
        Connection::open(&found[0]).unwrap()
    }
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

#[test]
fn a_fallen_back_unit_reaches_uninstrumented_even_though_this_process_never_registered_it() {
    let f = Fixture::new("uninstrumented-meta");
    // The unit this pid actually registered and ran.
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    // A SIBLING unit that fell back -- no process ever registers it, since a
    // fallen-back unit links no runtime at all, but the trace must still say
    // it happened.
    wire::write_manifest(
        &f.manifests_dir,
        "meta2",
        "helper",
        &[],
        &[],
        true,
        Some("rustc: E0999 something"),
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        1101,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1101, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();
    let uninstrumented = meta(&conn, "uninstrumented");
    let arr = uninstrumented.as_array().unwrap();
    assert_eq!(arr.len(), 1, "{uninstrumented}");
    assert_eq!(arr[0]["unit"], "meta2");
    assert_eq!(arr[0]["crate_name"], "helper");
    assert_eq!(arr[0]["reason"], "rustc: E0999 something");
}

#[test]
fn a_panic_record_with_no_open_frame_is_counted_and_never_written_as_an_event() {
    let f = Fixture::new("panics-outside-frames");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        1102,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // A CALL and its RETURN close the only frame this thread ever opens, and
    // THEN a PANIC record fires with nothing open on the stack -- e.g. code
    // that runs after the last traced call returns.
    wire::SpoolBuilder::new(1102, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .panic_record(2, 2500, &format!("{FILE}:9:1"), "orphaned panic")
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();
    assert_eq!(meta(&conn, "panics_outside_frames"), 1);
    assert_eq!(meta(&conn, "panics_unrecorded"), 0);
    // The stray PANIC never became a RAISE event: a causal event must carry
    // a code_id, and there was no frame to attach one from.
    let raises: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM events WHERE kind = 'RAISE'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(raises, 0);
    let total_events: i64 = conn
        .query_row("SELECT COUNT(*) FROM events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(total_events, 2, "only the CALL and the RETURN");
}

#[test]
fn a_foreign_workspace_manifest_is_excluded_from_uninstrumented_but_never_registered_either() {
    let f = Fixture::new("foreign-workspace-scoped-out");
    // In scope AND registered: this invocation's own workspace ("/w",
    // `Fixture::new`'s `write_invocation`), with its own skip.
    wire::write_manifest_scoped(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
        &[(FILE, "in_scope_const", 5, "const")],
        Some("/w"),
    );
    // A DIFFERENT workspace's leftover manifest in the same shared target:
    // fell back, and carries a skip. It cannot reach `uninstrumented` (the
    // GLOBAL scan `uninstrumented_list` builds is filtered by
    // `workspace_root`) -- and separately, `skipped` cannot see it either,
    // because a fallen-back unit never links the runtime, so no process ever
    // REGISTERS it (`skipped`/`spawns`/`unreached_files` are read only for
    // units `c.proc.units_in_order()` names, never workspace-filtered; see
    // `a_registered_units_manifest_still_contributes_skipped_even_with_no_
    // workspace_root_at_all` below for the case that distinction actually
    // guards).
    wire::write_manifest_scoped(
        &f.manifests_dir,
        "meta2",
        "unrelated-crate",
        &[],
        &[],
        true,
        Some("rustc: E0999 something"),
        &[],
        &[("other/src/lib.rs", "foreign_fn", 9, "async")],
        Some("/other-workspace"),
    );
    wire::write_proc_header(
        &f.spool_dir,
        1201,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1201, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();

    let uninstrumented = meta(&conn, "uninstrumented");
    assert_eq!(
        uninstrumented,
        serde_json::json!([]),
        "the foreign-workspace fallback must not reach this trace: {uninstrumented}"
    );

    let skipped = meta(&conn, "skipped");
    let skipped_arr = skipped.as_array().unwrap();
    assert_eq!(skipped_arr.len(), 1, "{skipped}");
    assert_eq!(skipped_arr[0]["qualname"], "in_scope_const");
    assert!(
        skipped.to_string().contains("in_scope_const"),
        "the in-scope skip must still be there: {skipped}"
    );
    assert!(
        !skipped.to_string().contains("foreign_fn"),
        "an unregistered unit's skip must not reach this trace: {skipped}"
    );

    // The foreign manifest HAS a workspace_root -- just not this one -- so it
    // is excluded, not counted as predating the field.
    assert_eq!(meta(&conn, "manifests_unscoped"), 0);
}

/// The fix for the fix: cargo's freshness caching can leave a REGISTERED
/// unit's own manifest on disk from a build old enough to predate the
/// `workspace_root` field entirely, without the wrapper running again to
/// write a fresh one (measured live on the Task 10 corpus:
/// `rust/spawned_thread`'s own cached manifest carried no `workspace_root`).
/// `skipped`/`spawns`/`unreached_files`/`source_hashes` must still see it --
/// `registered` is already the correct scope, and filtering this loop by
/// `workspace_root` too silently dropped a unit's OWN data.
#[test]
fn a_registered_units_manifest_still_contributes_skipped_even_with_no_workspace_root_at_all() {
    let f = Fixture::new("registered-unit-stale-manifest");
    wire::write_manifest_scoped(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
        &[(FILE, "cached_const", 5, "const")],
        None, // no `workspace_root` key at all -- a pre-fix, cargo-cached manifest
    );
    wire::write_proc_header(
        &f.spool_dir,
        1301,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1301, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();

    let skipped = meta(&conn, "skipped");
    assert!(
        skipped.to_string().contains("cached_const"),
        "a registered unit's own skip must survive even with no workspace_root: {skipped}"
    );
    // The manifest itself still predates the field, and is still counted --
    // `manifests_unscoped` is a fact about the manifest, not about whether
    // this specific loop happened to use it.
    assert_eq!(meta(&conn, "manifests_unscoped"), 1);
}

#[test]
fn a_manifest_with_no_workspace_root_key_at_all_is_counted_in_manifests_unscoped() {
    let f = Fixture::new("manifest-predates-workspace-root");
    wire::write_manifest_scoped(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
        &[],
        Some("/w"),
    );
    // No `workspace_root` key at all -- the shape a manifest written before
    // this field existed has. `#[serde(default)]` reads it as `""`, which
    // `manifest_in_scope` treats as not-in-scope of anything.
    wire::write_manifest_scoped(
        &f.manifests_dir,
        "meta2",
        "old-crate",
        &[],
        &[],
        true,
        Some("rustc: some old failure"),
        &[],
        &[],
        None,
    );
    wire::write_proc_header(
        &f.spool_dir,
        1202,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1202, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();

    assert_eq!(meta(&conn, "manifests_unscoped"), 1);
    assert_eq!(
        meta(&conn, "uninstrumented"),
        serde_json::json!([]),
        "a fell-back manifest with no workspace_root is not in scope of THIS trace either"
    );
}

/// The converter carries a manifest `spawns` entry as opaque JSON
/// (`convert/spool.rs`'s `Vec<serde_json::Value>`), so the two fields the
/// transformer added in this slice -- `qualname` (always) and `ordinal` (an
/// integer for a wrapped site, `null` for a declared one) -- reach the trace
/// with no code that names them. That is exactly why it needs a test: nothing
/// downstream would fail if they were dropped, and `docs/TRACE-FORMAT.md` §4
/// promises the whole entry.
#[test]
fn a_manifest_spawn_entry_reaches_the_trace_verbatim_including_qualname_and_ordinal() {
    let f = Fixture::new("spawn-entry-passthrough");
    // Written as a literal, not through `wire::write_manifest`: the claim is
    // about bytes the wrapper wrote reaching the trace unchanged, so the
    // fixture spells the entry out.
    std::fs::write(
        f.manifests_dir.join("meta1.json"),
        r#"{"unit":"meta1","crate_name":"demo","crate_type":"lib",
            "files":{"crates/demo/src/lib.rs":[{"site":0,"qualname":"main","firstlineno":3,"ret":"unit"}]},
            "skipped":[],
            "spawns":[{"file":"src/lib.rs","line":9,"wrapped":true,"reason":null,"qualname":"a","ordinal":2},
                      {"file":"src/lib.rs","line":14,"wrapped":false,"reason":"builder","qualname":"b","ordinal":null}],
            "source_hashes":{"crates/demo/src/lib.rs":"deadbeef"},
            "fell_back":false,"fallback_reason":null,"unreached_files":[],
            "appended_line":{},"workspace_root":"/w"}"#,
    )
    .unwrap();
    wire::write_proc_header(
        &f.spool_dir,
        1401,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1401, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();

    let spawns = meta(&conn, "spawns");
    assert_eq!(
        spawns,
        serde_json::json!([
            {"file":"src/lib.rs","line":9,"wrapped":true,"reason":null,"qualname":"a","ordinal":2},
            {"file":"src/lib.rs","line":14,"wrapped":false,"reason":"builder","qualname":"b","ordinal":null}
        ]),
        "the manifest's spawn entries did not reach the trace verbatim: {spawns}"
    );
    // Named one at a time as well as compared whole: an entry that lost
    // `ordinal` would fail the whole-value assertion with a diff a reader has
    // to squint at, and these two fields are the point of this test.
    assert_eq!(spawns[0]["qualname"], "a");
    assert_eq!(spawns[0]["ordinal"], 2);
    assert_eq!(spawns[1]["qualname"], "b");
    assert_eq!(spawns[1]["ordinal"], serde_json::Value::Null);
}
