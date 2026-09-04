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
