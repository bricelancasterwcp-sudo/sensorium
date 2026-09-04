//! The cargo target-runner role (plan decision D4).
//!
//! The runtime cannot observe its own process's exit status: a test binary's
//! normal return and `std::process::exit` both bypass every destructor, and
//! rung 1 papered over that by writing CARGO's status onto all 119 traces of
//! one invocation, so every process claimed the same number (findings §5.1).
//! The parent CAN see it. Cargo already has the hook, and on cargo 1.96 it
//! hands the runner every test binary AND every doctest process (measured
//! 2026-09-02).
//!
//! So the driver sets `CARGO_TARGET_<HOST>_RUNNER=<shim> --runner`, and this
//! role spawns the binary with stdio inherited and the environment untouched,
//! waits for it, writes `<spool>/<child pid>.runner.json`, and exits with the
//! child's own status. A process nobody waited for gets no file, and its trace
//! says `exit: unwitnessed` rather than a borrowed zero (`rust/HONESTY.md` §5).

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;

/// What the runner witnessed. Exactly one of `exit_status` and `signal` is set.
#[derive(Debug, Serialize)]
pub struct RunnerRecord {
    pub pid: u32,
    pub exit_status: Option<i32>,
    pub signal: Option<i32>,
    pub wall_start_ts: f64,
    pub wall_end_ts: f64,
    pub argv: Vec<String>,
}

/// Run the binary and report on it. Returns the exit code to leave with.
pub fn run(args: &[String]) -> i32 {
    let Some((program, rest)) = args.split_first() else {
        eprintln!("cargo-sensorium --runner: no binary to run");
        return 2;
    };

    // A runner the user had configured is chained by running it as the
    // executable with the binary as its first argument. Only the ENV form is
    // chained; a runner in a workspace's `.cargo/config.toml` is replaced, and
    // that is a declared v1 limitation (`rust/HONESTY.md` §8 item 10).
    let inner = non_empty_env("SENSORIUM_INNER_RUNNER");
    let (exe, argv) = match &inner {
        Some(inner) => {
            let mut argv = vec![program.clone()];
            argv.extend_from_slice(rest);
            (inner.clone(), argv)
        }
        None => (program.clone(), rest.to_vec()),
    };

    let wall_start_ts = now();
    let child = Command::new(&exe)
        .args(&argv)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn();
    let mut child = match child {
        Ok(c) => c,
        Err(e) => {
            eprintln!("cargo-sensorium --runner: cannot run {exe}: {e}");
            return 2;
        }
    };
    let pid = child.id();
    let status = match child.wait() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("cargo-sensorium --runner: cannot wait for {exe}: {e}");
            return 2;
        }
    };
    let wall_end_ts = now();

    if let Some(spool) = non_empty_env("SENSORIUM_SPOOL") {
        let mut full = vec![exe.clone()];
        full.extend(argv);
        let record = RunnerRecord {
            pid,
            exit_status: status.code(),
            signal: signal_of(&status),
            wall_start_ts,
            wall_end_ts,
            argv: full,
        };
        if let Err(e) = write_record(Path::new(&spool), pid, &record) {
            // Bookkeeping never changes the program's own status: the trace
            // loses a witnessed exit, the build does not lose a result.
            eprintln!("cargo-sensorium --runner: {e}");
        }
    }

    exit_code(&status)
}

/// `<spool>/<pid>.runner.json`.
#[must_use]
pub fn record_path(spool: &Path, pid: u32) -> PathBuf {
    spool.join(format!("{pid}.runner.json"))
}

/// Where the record is written before it is renamed into place. It must NOT be
/// a name the converter matches: the converter takes every file whose name ends
/// in `.runner.json`, and a temporary that also did would be read as a second,
/// half-written record for the same process.
#[must_use]
pub fn tmp_record_path(spool: &Path, pid: u32) -> PathBuf {
    spool.join(format!("{pid}.runner.json.tmp"))
}

/// Write the record where the converter will look for it.
///
/// Through a temporary and a rename, so a runner killed mid-write leaves no
/// half-parsed JSON at a name the converter matches. The temporary's name does
/// not end in `.runner.json`, so it is not one of those names.
///
/// # Errors
/// Any filesystem or serialisation failure, naming the path.
fn write_record(spool: &Path, pid: u32, record: &RunnerRecord) -> Result<(), String> {
    std::fs::create_dir_all(spool)
        .map_err(|e| format!("cannot create {}: {e}", spool.display()))?;
    let json = serde_json::to_string(record)
        .map_err(|e| format!("cannot serialise the runner record: {e}"))?;
    let dest = record_path(spool, pid);
    let tmp = tmp_record_path(spool, pid);
    std::fs::write(&tmp, json.as_bytes())
        .map_err(|e| format!("cannot write {}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, &dest).map_err(|e| format!("cannot write {}: {e}", dest.display()))
}

/// The shell's convention, and cargo's: a process killed by signal `n` is
/// reported as `128 + n`.
#[must_use]
pub fn exit_code(status: &std::process::ExitStatus) -> i32 {
    match (status.code(), signal_of(status)) {
        (Some(code), _) => code,
        (None, Some(sig)) => 128 + sig,
        // Neither: the platform told us nothing. 101 is rustc's own "something
        // went wrong" code, and is not mistakable for the child's success.
        (None, None) => 101,
    }
}

fn signal_of(status: &std::process::ExitStatus) -> Option<i32> {
    use std::os::unix::process::ExitStatusExt;
    status.signal()
}

fn non_empty_env(name: &str) -> Option<String> {
    std::env::var(name).ok().filter(|v| !v.is_empty())
}

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |d| d.as_secs_f64())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::process::ExitStatusExt;

    #[test]
    fn the_record_path_is_keyed_by_the_childs_pid() {
        assert_eq!(
            record_path(Path::new("/t/spool/2026-run"), 4242),
            Path::new("/t/spool/2026-run/4242.runner.json")
        );
    }

    #[test]
    fn an_ordinary_exit_code_is_passed_through() {
        assert_eq!(exit_code(&std::process::ExitStatus::from_raw(7 << 8)), 7);
        assert_eq!(exit_code(&std::process::ExitStatus::from_raw(0)), 0);
    }

    #[test]
    fn a_signal_death_is_reported_as_128_plus_the_signal() {
        // SIGKILL is 9; the shell, cargo and libtest all read this as 137.
        assert_eq!(exit_code(&std::process::ExitStatus::from_raw(9)), 137);
    }

    #[test]
    fn the_temporary_is_not_a_name_the_converter_matches() {
        let spool = Path::new("/t/spool");
        let tmp = tmp_record_path(spool, 4242);
        let name = tmp.file_name().unwrap().to_string_lossy().into_owned();
        assert!(
            !name.ends_with(".runner.json"),
            "{name} would be read as a second record"
        );
        assert_ne!(tmp, record_path(spool, 4242));
        assert_eq!(tmp.parent(), record_path(spool, 4242).parent());
    }

    #[test]
    fn a_record_serialises_to_the_shape_the_converter_reads() {
        let record = RunnerRecord {
            pid: 7,
            exit_status: Some(0),
            signal: None,
            wall_start_ts: 1.5,
            wall_end_ts: 2.5,
            argv: vec!["/t/x".to_owned(), "--nocapture".to_owned()],
        };
        let v: serde_json::Value =
            serde_json::from_str(&serde_json::to_string(&record).unwrap()).unwrap();
        assert_eq!(v["pid"], 7);
        assert_eq!(v["exit_status"], 0);
        assert_eq!(v["signal"], serde_json::Value::Null);
        assert_eq!(v["wall_start_ts"], 1.5);
        assert_eq!(v["wall_end_ts"], 2.5);
        assert_eq!(v["argv"], serde_json::json!(["/t/x", "--nocapture"]));
    }
}
