//! The cargo target-runner role, driven through the real binary.
//!
//! `rust/HONESTY.md` §5 promises that `exit_status` is this process's own
//! status and that a status in a trace is a status somebody waited for. These
//! are the falsifiers: a normal exit, a non-zero exit and a signal death each
//! have to produce the matching record AND the matching runner exit code, and
//! the child's own output has to reach the terminal byte for byte on the way.

mod common;

use std::path::Path;
use std::process::Command;

use common::Scratch;

fn runner() -> Command {
    let mut c = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"));
    c.arg("--runner");
    c
}

fn record(spool: &Path) -> serde_json::Value {
    let mut found: Vec<_> = std::fs::read_dir(spool)
        .unwrap()
        .filter_map(|e| {
            let p = e.unwrap().path();
            p.to_string_lossy().ends_with(".runner.json").then_some(p)
        })
        .collect();
    assert_eq!(found.len(), 1, "expected exactly one record: {found:?}");
    let path = found.pop().unwrap();
    let value: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
    // The file is named for the child's pid, and the record says the same.
    let stem = path.file_name().unwrap().to_string_lossy().into_owned();
    let pid: u64 = stem.split('.').next().unwrap().parse().unwrap();
    assert_eq!(value["pid"], pid, "the file name and the record disagree");
    value
}

#[test]
fn a_clean_exit_is_recorded_as_zero_and_returned_as_zero() {
    let s = Scratch::new("exit0");
    let spool = s.p("spool");
    let out = runner()
        .args(["/bin/sh", "-c", "exit 0"])
        .env("SENSORIUM_SPOOL", &spool)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));

    let r = record(&spool);
    assert_eq!(r["exit_status"], 0);
    assert_eq!(r["signal"], serde_json::Value::Null);
    assert!(
        r["wall_end_ts"].as_f64().unwrap() >= r["wall_start_ts"].as_f64().unwrap(),
        "{r}"
    );
    assert!(
        r["wall_start_ts"].as_f64().unwrap() > 1_700_000_000.0,
        "{r}"
    );
    assert_eq!(r["argv"][0], "/bin/sh");
}

#[test]
fn a_failing_exit_is_recorded_and_returned_unchanged() {
    // Not clamped, not turned into 1: cargo reads this code and so does the
    // person who ran the build.
    let s = Scratch::new("exit7");
    let spool = s.p("spool");
    let out = runner()
        .args(["/bin/sh", "-c", "exit 7"])
        .env("SENSORIUM_SPOOL", &spool)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(7));

    let r = record(&spool);
    assert_eq!(r["exit_status"], 7);
    assert_eq!(r["signal"], serde_json::Value::Null);
}

#[test]
fn a_signal_death_is_recorded_as_a_signal_and_returned_as_128_plus_it() {
    let s = Scratch::new("sigkill");
    let spool = s.p("spool");
    let out = runner()
        .args(["/bin/sh", "-c", "kill -9 $$"])
        .env("SENSORIUM_SPOOL", &spool)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(137), "128 + SIGKILL");

    let r = record(&spool);
    // `exit_status: null` with a signal is the honest shape: there was no exit
    // code to report, and a 0 here would be a fabricated success.
    assert_eq!(r["exit_status"], serde_json::Value::Null);
    assert_eq!(r["signal"], 9);
}

#[test]
fn the_record_names_the_childs_own_pid() {
    let s = Scratch::new("pid");
    let spool = s.p("spool");
    let out = runner()
        .args(["/bin/sh", "-c", "echo $$"])
        .env("SENSORIUM_SPOOL", &spool)
        .output()
        .unwrap();
    let printed: u64 = String::from_utf8_lossy(&out.stdout).trim().parse().unwrap();
    assert_eq!(
        record(&spool)["pid"],
        printed,
        "the record must name the process that ran, not the runner"
    );
}

#[test]
fn a_megabyte_of_output_passes_through_byte_identical_on_both_streams() {
    let s = Scratch::new("bytes");
    let spool = s.p("spool");
    // Not random: a fixed pattern that crosses every pipe buffer boundary, so a
    // difference is a diff a person can read.
    let payload: String = (0..1_000_000)
        .map(|i| char::from(b'a' + u8::try_from(i % 26).unwrap()))
        .collect();
    let data = s.write("payload", &payload);

    let out = runner()
        .args([
            "/bin/sh",
            "-c",
            "cat \"$1\"; cat \"$1\" >&2",
            "sh",
            &data.to_string_lossy(),
        ])
        .env("SENSORIUM_SPOOL", &spool)
        .output()
        .unwrap();

    assert_eq!(out.status.code(), Some(0));
    assert_eq!(out.stdout.len(), payload.len(), "stdout was resized");
    assert_eq!(out.stderr.len(), payload.len(), "stderr was resized");
    assert_eq!(
        out.stdout,
        payload.as_bytes(),
        "stdout is not byte-identical"
    );
    assert_eq!(
        out.stderr,
        payload.as_bytes(),
        "stderr is not byte-identical"
    );
}

#[test]
fn without_a_spool_the_binary_still_runs_and_nothing_is_written() {
    let s = Scratch::new("nospool");
    let out = runner()
        .args(["/bin/sh", "-c", "echo ran; exit 3"])
        .env_remove("SENSORIUM_SPOOL")
        .current_dir(&s.0)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(3));
    assert_eq!(String::from_utf8_lossy(&out.stdout).trim(), "ran");
    let left: Vec<_> = std::fs::read_dir(&s.0)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    assert!(left.is_empty(), "the runner wrote something: {left:?}");
}

#[test]
fn an_empty_spool_variable_is_treated_as_unset() {
    let s = Scratch::new("emptyspool");
    let out = runner()
        .args(["/bin/sh", "-c", "exit 0"])
        .env("SENSORIUM_SPOOL", "")
        .current_dir(&s.0)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    // An empty value must not become a record in the current directory.
    let left: Vec<_> = std::fs::read_dir(&s.0)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    assert!(left.is_empty(), "{left:?}");
}

#[test]
fn an_inner_runner_is_prepended_as_the_executable() {
    // A user's own runner, chained rather than replaced. Only the ENV form is
    // chained; a runner in a workspace's `.cargo/config.toml` is replaced, and
    // that is declared in `rust/HONESTY.md` §8 item 10 rather than pretended
    // away.
    let s = Scratch::new("inner");
    let spool = s.p("spool");
    let out = runner()
        .args(["/bin/echo", "--flag"])
        .env("SENSORIUM_SPOOL", &spool)
        .env("SENSORIUM_INNER_RUNNER", "/bin/echo")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(0));
    // `echo /bin/echo --flag`: the inner runner ran, with the binary first.
    assert_eq!(
        String::from_utf8_lossy(&out.stdout).trim(),
        "/bin/echo --flag"
    );
    let r = record(&spool);
    assert_eq!(
        r["argv"],
        serde_json::json!(["/bin/echo", "/bin/echo", "--flag"])
    );
}

#[test]
fn no_binary_at_all_is_refused_rather_than_reported_as_success() {
    let out = runner().output().unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&out.stderr).contains("no binary to run"),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
}

#[test]
fn a_binary_that_cannot_be_run_is_refused_rather_than_reported_as_success() {
    let s = Scratch::new("missing");
    let out = runner()
        .arg(s.p("does-not-exist"))
        .env("SENSORIUM_SPOOL", s.p("spool"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(
        !s.p("spool").exists(),
        "nothing ran, so nothing is witnessed"
    );
}
