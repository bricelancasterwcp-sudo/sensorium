//! `cargo-sensorium convert <spool dir>` over spool directories built to be
//! wrong: each of these must fail loudly, naming the file, rather than
//! writing a trace that looks honest and is not.

mod common;

use std::path::PathBuf;
use std::process::{Command, Output};

use common::wire::{self, site};
use common::Scratch;

const FILE: &str = "crates/demo/src/lib.rs";

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

    fn one_site_manifest(&self, metadata: &str) {
        wire::write_manifest(
            &self.manifests_dir,
            metadata,
            "demo",
            &[(FILE, &[site(0, "main", 3, "unit")])],
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
}

fn stderr(out: &Output) -> String {
    String::from_utf8_lossy(&out.stderr).into_owned()
}

/// Whether the refused run left a `.db` behind. The writer builds into a
/// `.db.tmp` and renames only after every row is written, so a refusal must
/// produce no `.db` at all -- a half-written trace a reader could open is the
/// thing the tmp+rename exists to prevent.
fn traces_exist(f: &Fixture) -> bool {
    std::fs::read_dir(f.sensorium_dir.join("traces")).is_ok_and(|entries| {
        entries
            .filter_map(Result::ok)
            .any(|e| e.path().extension().and_then(|x| x.to_str()) == Some("db"))
    })
}

#[test]
fn a_spool_file_with_no_matching_proc_header_is_an_orphan_spool_error() {
    let f = Fixture::new("orphan-spool");
    f.one_site_manifest("meta1");
    // No `<pid>.proc.json` for pid 555 at all.
    wire::SpoolBuilder::new(555, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("orphan spool"), "{err}");
    assert!(err.contains("555"), "{err}");
}

#[test]
fn a_manifest_naming_a_mirror_path_is_refused_by_name() {
    let f = Fixture::new("mirror-path");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            "target/sensorium/mirror/meta1/crates/demo/src/lib.rs",
            &[site(0, "main", 3, "unit")],
        )],
        &[],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        556,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(556, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("mirror path"), "{err}");
    assert!(err.contains("meta1.json"), "{err}");
}

#[test]
fn a_backwards_seq_within_one_spool_file_is_a_named_error() {
    let f = Fixture::new("backwards-seq");
    f.one_site_manifest("meta1");
    wire::write_proc_header(
        &f.spool_dir,
        557,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    let path = wire::SpoolBuilder::new(557, 1, "main")
        .call(5, 1000, 0, 0)
        .call(3, 1100, 0, 0) // seq goes backwards: 5 then 3
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("backwards"), "{err}");
    assert!(err.contains(&path.display().to_string()), "{err}");
}

#[test]
fn a_return_with_no_open_frame_on_its_thread_is_a_named_error() {
    let f = Fixture::new("return-no-frame");
    f.one_site_manifest("meta1");
    wire::write_proc_header(
        &f.spool_dir,
        558,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // A RETURN with no preceding CALL on this thread at all.
    wire::SpoolBuilder::new(558, 1, "main")
        .ret_none(0, 1000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("RETURN with no open frame"), "{err}");
    assert!(err.contains("pid 558"), "{err}: pid");
    assert!(err.contains("thread 1"), "{err}: thread serial");
    assert!(err.contains("seq 0"), "{err}: seq");
}

#[test]
fn a_missing_invocation_json_is_a_named_error() {
    let f = Fixture::new("missing-invocation");
    std::fs::remove_file(f.spool_dir.join("invocation.json")).unwrap();
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("invocation.json"), "{err}");
}

#[test]
fn a_missing_manifests_directory_is_a_named_error() {
    let f = Fixture::new("missing-manifests-dir");
    std::fs::remove_dir_all(&f.manifests_dir).unwrap();
    wire::write_proc_header(&f.spool_dir, 559, 1, "/w/target/deps/demo", &[], None);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("manifests"), "{err}");
}

/// Design amendment A6: the parameters LINE is spliced AFTER the entry guard,
/// so a LINE always falls inside its function's CALL. A LINE whose thread has
/// no open frame is a malformed stream, and the converter refuses it naming
/// the record rather than attaching it to a guessed frame -- and leaves no
/// trace behind for a reader to believe.
#[test]
fn a_line_record_with_no_open_frame_on_its_thread_is_a_named_error() {
    let f = Fixture::new("line-no-frame");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            FILE,
            &[site(0, "fill", 3, "unit"), wire::line_site(1, "fill", 5)],
        )],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        560,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // A LINE with no preceding CALL on this thread at all.
    wire::SpoolBuilder::new(560, 1, "main")
        .line(0, 1000, 0, 1, false, &[("x", wire::LineDelta::Unread)])
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("LINE record with no open frame"), "{err}");
    assert!(err.contains("pid 560"), "{err}: pid");
    assert!(err.contains("thread 1"), "{err}: thread serial");
    assert!(err.contains("seq 0"), "{err}: seq");
    assert!(err.contains("malformed"), "{err}");
    assert!(
        !traces_exist(&f),
        "a refused conversion leaves no .db a reader could open"
    );
}

/// A LINE may name only a `line` site. One that names the fn's own site is
/// corruption -- the manifest row and the spliced call come from the same
/// walk -- and the refusal names the SITE, which is what a person looks at.
#[test]
fn a_line_record_naming_a_site_the_manifest_says_is_a_fn_is_refused() {
    let f = Fixture::new("line-wrong-site-kind");
    f.one_site_manifest("meta1");
    wire::write_proc_header(
        &f.spool_dir,
        561,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(561, 1, "main")
        .call(0, 1000, 0, 0)
        .line(1, 1100, 0, 0, false, &[]) // site 0 is a `fn` row
        .ret_none(2, 1200, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("LINE"), "{err}");
    assert!(err.contains("crates/demo/src/lib.rs:3"), "{err}");
    assert!(err.contains("not a `line` site"), "{err}");
}

/// A LINE payload this reader cannot decode is a refusal naming the record,
/// never a row guessed from what it could read (design §3.5).
#[test]
fn a_malformed_line_payload_is_a_refusal_naming_the_record() {
    let f = Fixture::new("line-bad-payload");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            FILE,
            &[site(0, "fill", 3, "unit"), wire::line_site(1, "fill", 5)],
        )],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        562,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // `n = 1` with no delta block behind it: kind 6, site 1, raw payload.
    wire::SpoolBuilder::new(562, 1, "main")
        .call(0, 1000, 0, 0)
        .raw(1, 1100, 1, 6, 0, &[0u8, 1u8, 0u8])
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("pid 562"), "{err}");
    assert!(err.contains("seq 1"), "{err}");
    assert!(
        !traces_exist(&f),
        "no trace is written for a refused record"
    );
}

// ---------------------------------------------------------------------------
// Malformed metadata: the read path's hard errors, one fixture each
// ---------------------------------------------------------------------------

/// A well-formed one-process spool, so the malformed file below is the only
/// thing wrong with the directory.
fn one_good_process(f: &Fixture, pid: u32) {
    f.one_site_manifest("meta1");
    wire::write_proc_header(
        &f.spool_dir,
        pid,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(pid, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
}

#[test]
fn a_proc_header_whose_name_is_not_a_pid_is_refused_by_name() {
    // The shape a leftover atomic-write temp or a hand-copied file takes:
    // the `.proc.json` suffix is there and the stem is not a number. Reading
    // it as pid 0, or skipping it, would lose a whole process in silence.
    let f = Fixture::new("proc-header-not-a-pid");
    one_good_process(&f, 570);
    std::fs::write(f.spool_dir.join("notapid.proc.json"), b"{}").unwrap();
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("does not name a pid"), "{err}");
    assert!(err.contains("notapid.proc.json"), "{err}");
    assert!(!traces_exist(&f), "no trace is written for a refused read");
}

#[test]
fn a_malformed_proc_header_is_refused_and_names_the_file() {
    let f = Fixture::new("proc-header-malformed");
    one_good_process(&f, 571);
    std::fs::write(f.spool_dir.join("572.proc.json"), b"{\"exe\": ").unwrap();
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("is not a valid proc header"), "{err}");
    assert!(err.contains("572.proc.json"), "{err}");
    assert!(!traces_exist(&f), "no trace is written for a refused read");
}

#[test]
fn a_runner_record_whose_name_is_not_a_pid_is_refused_by_name() {
    let f = Fixture::new("runner-record-not-a-pid");
    one_good_process(&f, 573);
    std::fs::write(f.spool_dir.join("notapid.runner.json"), b"{}").unwrap();
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("does not name a pid"), "{err}");
    assert!(err.contains("notapid.runner.json"), "{err}");
    assert!(!traces_exist(&f), "no trace is written for a refused read");
}

#[test]
fn a_malformed_runner_record_is_refused_and_names_the_file() {
    // A runner record is where a witnessed exit status comes from. Reading a
    // broken one as "no record" would silently downgrade the trace to
    // `exit_status_basis: "unwitnessed"`, which is a claim about the world.
    let f = Fixture::new("runner-record-malformed");
    one_good_process(&f, 574);
    std::fs::write(f.spool_dir.join("574.runner.json"), b"not json at all").unwrap();
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("is not a valid runner record"), "{err}");
    assert!(err.contains("574.runner.json"), "{err}");
    assert!(!traces_exist(&f), "no trace is written for a refused read");
}

#[test]
fn a_malformed_invocation_record_is_refused_and_names_the_file() {
    // `invocation.json` is the converter's ONE source for the workspace root,
    // the toolchain and the focus; there is nothing to fall back to.
    let f = Fixture::new("invocation-malformed");
    one_good_process(&f, 575);
    std::fs::write(f.spool_dir.join("invocation.json"), b"{\"invocation\":").unwrap();
    let out = f.convert();
    assert_eq!(out.status.code(), Some(2));
    let err = stderr(&out);
    assert!(err.contains("cannot read invocation.json"), "{err}");
    assert!(err.contains("is not a valid invocation record"), "{err}");
    assert!(!traces_exist(&f), "no trace is written for a refused read");
}
