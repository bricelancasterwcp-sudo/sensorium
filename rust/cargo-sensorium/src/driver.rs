//! The driver role: `cargo sensorium test|run [--tier off|call] [cargo args…]`.
//!
//! Cargo stays the builder and the runner of everything. The driver only
//! prepares the ground — the runtime rlib, the shim cargo will call as its
//! workspace wrapper and as its target runner, an invocation id, a spool
//! directory and the environment — and then runs cargo with the argv the user
//! typed, unchanged.

use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;

use crate::rt_build::{self, Panic};
use crate::rt_src;

/// This binary's name and version, as it reaches a trace.
pub const DRIVER_VERSION: &str = concat!("cargo-sensorium ", env!("CARGO_PKG_VERSION"));

/// How much the runtime records. `off` is the inert arm E1 measures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Off,
    Call,
}

impl Tier {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Tier::Off => "off",
            Tier::Call => "call",
        }
    }
}

/// What the driver was asked to do.
#[derive(Debug, PartialEq, Eq)]
pub struct DriverArgs {
    pub tier: Tier,
    /// The argv handed to cargo, starting with the subcommand.
    pub cargo_args: Vec<String>,
}

impl DriverArgs {
    #[must_use]
    pub fn subcommand(&self) -> &str {
        self.cargo_args.first().map_or("", String::as_str)
    }
}

/// `invocation.json`, written before cargo starts and completed after it exits.
/// The converter reads it: it is where a trace's workspace root, toolchain,
/// profile and cargo argv come from, none of which the runtime can see.
#[derive(Debug, Serialize)]
pub struct Invocation {
    pub invocation: String,
    pub subcommand: String,
    pub cargo_args: Vec<String>,
    pub tier: String,
    /// `rustc -vV`'s first line, from the rustc this invocation actually used.
    pub toolchain: String,
    /// Which rustc that was: `RUSTC` when set, otherwise whatever `rustc` on
    /// `PATH` resolved to. The runtime the units link was compiled by it.
    pub rustc_path: String,
    pub host: String,
    pub profile: String,
    pub workspace_root: String,
    pub target_dir: String,
    pub tool_hash: String,
    pub driver_version: String,
    pub start_ts: f64,
    pub end_ts: Option<f64>,
    pub cargo_exit: Option<i32>,
}

/// Split the driver's own flags out of cargo's.
///
/// `--tier` is recognised only BEFORE the first bare `--`, so a test binary's
/// own `--tier` argument (after `cargo test -- …`) is never stolen.
///
/// # Errors
/// A usage message when the subcommand is missing or unknown, or when `--tier`
/// has no value or a value this recorder does not implement.
pub fn parse_args(args: &[String]) -> Result<DriverArgs, String> {
    let mut tier = Tier::Call;
    let mut cargo_args: Vec<String> = Vec::new();
    let mut past_separator = false;
    let mut i = 0;
    while i < args.len() {
        let a = &args[i];
        if a == "--" {
            past_separator = true;
        }
        if !past_separator {
            if let Some(v) = a.strip_prefix("--tier=") {
                tier = parse_tier(v)?;
                i += 1;
                continue;
            }
            if a == "--tier" {
                let v = args
                    .get(i + 1)
                    .ok_or_else(|| "--tier needs a value (off or call)".to_owned())?;
                tier = parse_tier(v)?;
                i += 2;
                continue;
            }
        }
        cargo_args.push(a.clone());
        i += 1;
    }
    match cargo_args.first().map(String::as_str) {
        Some("test" | "run") => Ok(DriverArgs { tier, cargo_args }),
        Some(other) => Err(format!(
            "unknown subcommand `{other}`; this version implements `cargo sensorium test` and \
             `cargo sensorium run`"
        )),
        None => Err(USAGE.to_owned()),
    }
}

pub const USAGE: &str = "usage: cargo sensorium test|run [--tier off|call] [cargo args]";

fn parse_tier(v: &str) -> Result<Tier, String> {
    match v {
        "off" => Ok(Tier::Off),
        "call" => Ok(Tier::Call),
        other => Err(format!("unknown tier `{other}`; expected off or call")),
    }
}

/// The cargo profile this invocation builds, as the trace records it.
///
/// `--release` and `-r` name the `release` profile; `--profile <name>` names
/// whatever it says, verbatim, because a custom profile is a real answer and
/// "dev" would be a wrong one. Everything after a bare `--` belongs to the
/// binary cargo runs, not to cargo.
#[must_use]
pub fn profile(cargo_args: &[String]) -> String {
    let mut i = 0;
    while i < cargo_args.len() {
        let a = &cargo_args[i];
        if a == "--" {
            break;
        }
        if a == "--release" || a == "-r" {
            return "release".to_owned();
        }
        if let Some(v) = a.strip_prefix("--profile=") {
            return v.to_owned();
        }
        if a == "--profile" {
            if let Some(v) = cargo_args.get(i + 1) {
                return v.clone();
            }
        }
        i += 1;
    }
    "dev".to_owned()
}

/// Cargo's per-target runner variable for a host triple: the triple uppercased
/// with `-` replaced by `_`.
#[must_use]
pub fn runner_env_var(host: &str) -> String {
    let mut out = String::from("CARGO_TARGET_");
    for c in host.chars() {
        out.push(if c == '-' {
            '_'
        } else {
            c.to_ascii_uppercase()
        });
    }
    out.push_str("_RUNNER");
    out
}

/// `rustc -vV`: the first line (the toolchain) and the `host:` line's value.
///
/// # Errors
/// If rustc cannot be run, fails, or prints no `host:` line.
pub fn toolchain_and_host(rustc: &str) -> Result<(String, String), String> {
    let out = Command::new(rustc)
        .arg("-vV")
        .output()
        .map_err(|e| format!("cannot run {rustc}: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "{rustc} -vV failed ({}): {}",
            out.status,
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let text = String::from_utf8_lossy(&out.stdout);
    parse_version_verbose(&text)
}

/// The pure half of [`toolchain_and_host`], so the parse is testable against
/// real captured output rather than against whatever rustc is on this box.
///
/// # Errors
/// If there is no first line or no `host:` line.
pub fn parse_version_verbose(text: &str) -> Result<(String, String), String> {
    let toolchain = text
        .lines()
        .next()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .ok_or_else(|| "rustc -vV printed nothing".to_owned())?
        .to_owned();
    let host = text
        .lines()
        .find_map(|l| l.strip_prefix("host:"))
        .map(str::trim)
        .filter(|h| !h.is_empty())
        .ok_or_else(|| "rustc -vV printed no `host:` line".to_owned())?
        .to_owned();
    Ok((toolchain, host))
}

/// `YYYYMMDD-HHMMSS-<6 hex>` in LOCAL time: sensorium's run-id shape, the same
/// one `paths.new_run_id` mints on the Python side. The shape is what groups a
/// day's traces in a listing, so it is local time there and local time here.
///
/// # Errors
/// If the C library cannot convert the timestamp.
pub fn invocation_id() -> Result<String, String> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| format!("the clock is before the epoch: {e}"))?;
    let secs = i64::try_from(now.as_secs()).map_err(|e| format!("the clock is unreadable: {e}"))?;
    let nanos = u64::from(now.subsec_nanos());
    let mix = nanos ^ (u64::from(std::process::id()) << 20) ^ (now.as_secs() << 7);
    Ok(format!("{}-{:06x}", local_stamp(secs)?, mix & 0x00ff_ffff))
}

/// `YYYYMMDD-HHMMSS` for a Unix timestamp, in the local zone.
///
/// # Errors
/// If `localtime_r` refuses the timestamp.
pub fn local_stamp(secs: i64) -> Result<String, String> {
    let time: libc::time_t = secs;
    // SAFETY: `libc::tm` is a `repr(C)` struct of plain integers, and the
    // all-zero bit pattern is a valid value for every field in it (unlike a
    // struct carrying a reference, a `bool` is not, but `tm` has none) —
    // `localtime_r` below overwrites every field it uses before this value is
    // read.
    let mut tm: libc::tm = unsafe { std::mem::zeroed() };
    // SAFETY: `time` and `tm` are owned locals of the right types, live for the
    // whole call, and `localtime_r` is the reentrant form: it writes only
    // through the `tm` pointer we give it and touches no static buffer.
    let result = unsafe { libc::localtime_r(&time, &mut tm) };
    if result.is_null() {
        return Err(format!("localtime_r refused the timestamp {secs}"));
    }
    Ok(format!(
        "{:04}{:02}{:02}-{:02}{:02}{:02}",
        tm.tm_year + 1900,
        tm.tm_mon + 1,
        tm.tm_mday,
        tm.tm_hour,
        tm.tm_min,
        tm.tm_sec
    ))
}

/// Run the driver. Returns the exit code to leave with.
pub fn run(args: &[String]) -> i32 {
    match go(args) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("cargo-sensorium: {e}");
            2
        }
    }
}

fn go(args: &[String]) -> Result<i32, String> {
    let parsed = parse_args(args)?;
    let ws = workspace_root()?;
    let target = target_dir(&ws);
    // Cargo splits `CARGO_TARGET_<HOST>_RUNNER` and `RUSTDOCFLAGS` on
    // whitespace, and both carry a path under `<target>`. A target directory
    // with a space in it would silently become two arguments, so it is refused
    // rather than mis-run.
    if target.to_string_lossy().chars().any(char::is_whitespace) {
        return Err(format!(
            "the target directory {} contains whitespace; cargo splits the runner and rustdoc \
             flags on whitespace, so this recorder refuses it rather than mis-run the build",
            target.display()
        ));
    }

    let rustc = rustc_path();
    let (toolchain, host) = toolchain_and_host(&rustc)?;
    let exe = std::env::current_exe().map_err(|e| format!("cannot find own path: {e}"))?;
    let tool_hash = rt_build::tool_hash(&exe, rt_src::FILES)?;
    let rt = rt_build::rt_dir(&target, &tool_hash);
    // `unwind` now, because almost every unit wants it and a serial build up
    // front beats N wrappers racing for it. `abort` is built by the wrapper
    // that first meets a `-C panic=abort` unit, and most workspaces never do.
    let rlib = rt_build::ensure(&rt, &rustc, Panic::Unwind, rt_src::FILES)?;
    let shim = rt_build::install_shim(&target, &exe, &tool_hash)?;

    let invocation = invocation_id()?;
    let spool = target.join("sensorium").join("spool").join(&invocation);
    std::fs::create_dir_all(&spool)
        .map_err(|e| format!("cannot create {}: {e}", spool.display()))?;

    let mut record = Invocation {
        invocation: invocation.clone(),
        subcommand: parsed.subcommand().to_owned(),
        cargo_args: parsed.cargo_args.clone(),
        tier: parsed.tier.as_str().to_owned(),
        toolchain,
        rustc_path: rustc.clone(),
        host: host.clone(),
        profile: profile(&parsed.cargo_args),
        workspace_root: ws.to_string_lossy().into_owned(),
        target_dir: target.to_string_lossy().into_owned(),
        tool_hash: tool_hash.clone(),
        driver_version: DRIVER_VERSION.to_owned(),
        start_ts: now(),
        end_ts: None,
        cargo_exit: None,
    };
    let invocation_json = spool.join("invocation.json");
    // Written BEFORE cargo, so a build that is killed still leaves a spool
    // directory that says what it was.
    write_invocation(&invocation_json, &record)?;

    let status = Command::new(cargo_path())
        .args(&parsed.cargo_args)
        .current_dir(&ws)
        // Doctests are not routed through `RUSTC_WORKSPACE_WRAPPER` — cargo
        // says nothing about rustdoc — but they DO link the instrumented rlibs
        // and they DO spool, so without this a doctest fails with E0463
        // (findings §5.23). Appended to the user's own, never replacing it.
        .env("RUSTDOCFLAGS", rustdoc_flags(&rlib))
        .env("RUSTC_WORKSPACE_WRAPPER", &shim)
        .env(
            runner_env_var(&host),
            format!("{} --runner", shim.display()),
        )
        .env("SENSORIUM_SPOOL", &spool)
        .env("SENSORIUM_TIER", parsed.tier.as_str())
        .env("SENSORIUM_TARGET", &target)
        .env("SENSORIUM_WS", &ws)
        .env("SENSORIUM_RT_DIR", &rt)
        .env("SENSORIUM_TOOL_HASH", &tool_hash)
        .env("SENSORIUM_INVOCATION", &invocation)
        .status()
        .map_err(|e| format!("cannot run cargo: {e}"))?;

    // `exec` would be cheaper, but then nothing could run after cargo: the
    // process would be gone. Cargo is a child, waited for, and reported on.
    let code = status.code().unwrap_or(101);
    record.end_ts = Some(now());
    record.cargo_exit = Some(code);
    write_invocation(&invocation_json, &record)?;

    // The converter runs here, in-process, over `spool`: it prints its own
    // `run:` lines and the multi-binary WARN. A conversion error is reported
    // but does not overrule cargo's own status: cargo's non-zero exit is what
    // a caller already understands, and this recorder does not get to make a
    // green build red because writing its trace failed.
    let mut exit_code = code;
    if let Err(e) = crate::convert::convert_dir(&spool) {
        eprintln!("cargo-sensorium: {e}");
        if code == 0 {
            exit_code = 2;
        }
    }
    eprintln!("spool: {}", spool.display());
    eprintln!("cargo exit: {code}");
    Ok(exit_code)
}

/// `RUSTDOCFLAGS` for the doctest units, preserving the user's own.
///
/// **Both flags, and `-L dependency` is not belt and braces.** The same pair
/// the wrapper appends (`wrapper.rs`), for the same reason: `--extern` binds a
/// name the crate being compiled may write, while a crate reached through
/// another crate's metadata is resolved through the search path. The doctest
/// crate does not name `sensorium_rt` -- it depends on a workspace rlib that
/// does -- so with `--extern` alone every doctest fails
/// `error[E0463]: can't find crate for 'sensorium_rt'`, and with
/// `-L dependency=<the rlib's directory>` alone it passes (measured
/// 2026-09-03, rustc 1.96, `rust/tests/mechanics.sh` on the probe). Both are
/// sent, so the direct name is bound as well as findable.
///
/// Plan decision D1 as amended requires both here AND in the wrapper: the
/// wrapper needed the search path too, for a unit whose own dependencies are
/// instrumented (measured on the bloomery clone the same day).
///
/// The directory is the rlib's own per-variant one
/// (`<rt dir>/<unwind|abort>/`) and holds exactly one rlib -- the runtime is
/// built there by one bare rustc invocation and has no dependencies (D1) -- so
/// there is no "multiple candidates" hazard in putting it on the search path.
///
/// The user's own `RUSTDOCFLAGS` come FIRST and are never replaced.
#[must_use]
pub fn rustdoc_flags(rlib: &Path) -> String {
    let dir = rlib.parent().unwrap_or_else(|| Path::new("."));
    let mine = format!(
        "--extern sensorium_rt={} -L dependency={}",
        rlib.display(),
        dir.display()
    );
    match std::env::var("RUSTDOCFLAGS") {
        Ok(existing) if !existing.trim().is_empty() => format!("{existing} {mine}"),
        _ => mine,
    }
}

/// Where cargo will put its artifacts, which is also where everything this
/// recorder writes goes (`rust/HONESTY.md` §9: nothing is written under a
/// workspace except `<target>/`).
fn target_dir(ws: &Path) -> PathBuf {
    std::env::var_os("CARGO_TARGET_DIR").map_or_else(|| ws.join("target"), PathBuf::from)
}

/// The rustc this invocation compiles the runtime with, as a path.
///
/// Resolved rather than left as the bare word `rustc`, because
/// `invocation.json` records it and a trace that says `"rustc"` says nothing:
/// the runtime linked into every unit was built by ONE compiler, and which one
/// is part of what the trace is a record of. `RUSTC` wins where it is set,
/// which is also what cargo itself honours.
fn rustc_path() -> String {
    if let Some(explicit) = std::env::var("RUSTC").ok().filter(|v| !v.is_empty()) {
        return explicit;
    }
    resolve_on_path("rustc").unwrap_or_else(|| "rustc".to_owned())
}

/// The first executable of that name on `PATH`, absolute where `PATH` is.
fn resolve_on_path(program: &str) -> Option<String> {
    let path = std::env::var_os("PATH")?;
    std::env::split_paths(&path)
        .map(|dir| dir.join(program))
        .find(|candidate| candidate.is_file())
        .map(|found| found.to_string_lossy().into_owned())
}

fn cargo_path() -> String {
    // Cargo sets `CARGO` when it invokes a subcommand, so `cargo +nightly
    // sensorium test` uses the nightly cargo rather than whatever is on PATH.
    std::env::var("CARGO")
        .ok()
        .filter(|v| !v.is_empty())
        .unwrap_or_else(|| "cargo".to_owned())
}

fn write_invocation(path: &Path, record: &Invocation) -> Result<(), String> {
    let json = serde_json::to_string(record)
        .map_err(|e| format!("cannot serialise the invocation record: {e}"))?;
    std::fs::write(path, json.as_bytes())
        .map_err(|e| format!("cannot write {}: {e}", path.display()))
}

fn workspace_root() -> Result<PathBuf, String> {
    let out = Command::new(cargo_path())
        .args(["locate-project", "--workspace", "--message-format", "plain"])
        .output()
        .map_err(|e| format!("cannot run cargo locate-project: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "cargo locate-project failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let manifest = String::from_utf8_lossy(&out.stdout).trim().to_owned();
    Path::new(&manifest)
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| format!("cargo located a manifest with no parent: {manifest}"))
}

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |d| d.as_secs_f64())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| (*s).to_owned()).collect()
    }

    #[test]
    fn the_default_tier_is_call() {
        let p = parse_args(&v(&["test", "--lib"])).unwrap();
        assert_eq!(p.tier, Tier::Call);
        assert_eq!(p.cargo_args, v(&["test", "--lib"]));
    }

    #[test]
    fn tier_off_is_taken_out_of_cargos_argv() {
        for form in [v(&["--tier", "off", "test"]), v(&["test", "--tier=off"])] {
            let p = parse_args(&form).unwrap();
            assert_eq!(p.tier, Tier::Off);
            assert_eq!(p.cargo_args, v(&["test"]));
        }
    }

    #[test]
    fn a_tier_after_the_separator_belongs_to_the_test_binary() {
        let p = parse_args(&v(&["test", "--", "--tier", "off"])).unwrap();
        assert_eq!(p.tier, Tier::Call);
        assert_eq!(p.cargo_args, v(&["test", "--", "--tier", "off"]));
    }

    #[test]
    fn a_bad_tier_is_refused_not_defaulted() {
        assert!(parse_args(&v(&["--tier", "loud", "test"])).is_err());
        assert!(parse_args(&v(&["--tier"])).is_err());
    }

    #[test]
    fn test_and_run_are_the_two_subcommands() {
        assert_eq!(parse_args(&v(&["test"])).unwrap().subcommand(), "test");
        assert_eq!(parse_args(&v(&["run"])).unwrap().subcommand(), "run");
        assert!(parse_args(&v(&["build"])).is_err());
        assert!(parse_args(&v(&["bench"])).is_err());
        assert!(parse_args(&[]).is_err());
    }

    #[test]
    fn the_profile_is_dev_unless_the_argv_says_otherwise() {
        assert_eq!(profile(&v(&["test", "--lib"])), "dev");
        assert_eq!(profile(&v(&["test", "--release"])), "release");
        assert_eq!(profile(&v(&["test", "-r"])), "release");
        assert_eq!(profile(&v(&["test", "--profile", "bench"])), "bench");
        assert_eq!(profile(&v(&["test", "--profile=bench"])), "bench");
    }

    #[test]
    fn a_release_flag_after_the_separator_is_the_binarys_own() {
        assert_eq!(profile(&v(&["run", "--", "--release"])), "dev");
    }

    #[test]
    fn the_runner_variable_is_the_triple_uppercased_with_underscores() {
        assert_eq!(
            runner_env_var("x86_64-unknown-linux-gnu"),
            "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER"
        );
        assert_eq!(
            runner_env_var("aarch64-apple-darwin"),
            "CARGO_TARGET_AARCH64_APPLE_DARWIN_RUNNER"
        );
    }

    #[test]
    fn the_toolchain_and_host_come_off_rustcs_own_output() {
        // Captured verbatim from `rustc -vV` on this box.
        let text = "rustc 1.96.0 (ac68faa20 2026-05-25)\nbinary: rustc\ncommit-hash: \
                    ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96\ncommit-date: \
                    2026-05-25\nhost: x86_64-unknown-linux-gnu\nrelease: 1.96.0\nLLVM version: \
                    22.1.2\n";
        let (toolchain, host) = parse_version_verbose(text).unwrap();
        assert_eq!(toolchain, "rustc 1.96.0 (ac68faa20 2026-05-25)");
        assert_eq!(host, "x86_64-unknown-linux-gnu");
    }

    #[test]
    fn rustc_output_without_a_host_line_is_an_error_not_a_guess() {
        assert!(parse_version_verbose("rustc 1.96.0\nrelease: 1.96.0\n").is_err());
        assert!(parse_version_verbose("").is_err());
    }

    #[test]
    fn the_live_rustc_agrees_with_the_captured_shape() {
        // The pin above is a string; this is the same parse against whatever
        // rustc is actually here, so a changed `-vV` format cannot pass unseen.
        let rustc = std::env::var("RUSTC").unwrap_or_else(|_| "rustc".to_owned());
        let (toolchain, host) = toolchain_and_host(&rustc).unwrap();
        assert!(toolchain.starts_with("rustc "), "{toolchain}");
        assert!(host.contains('-'), "{host}");
    }

    /// The run-id stamp is LOCAL time. `date -d @<secs>` is the oracle, and it
    /// is deterministic: no instant is read twice.
    #[test]
    fn the_run_id_stamp_is_the_local_time_date_prints() {
        // A summer instant and a winter one, so a zone with daylight saving
        // gets both of its offsets. On a UTC box they are both UTC and the
        // check still holds -- it is `date` that decides, not this file.
        for secs in [1_756_771_200_i64, 1_703_980_800, 0, 1_711_843_200] {
            let out = Command::new("date")
                .args([&format!("-d@{secs}"), "+%Y%m%d-%H%M%S"])
                .output()
                .expect("run date");
            let want = String::from_utf8_lossy(&out.stdout).trim().to_owned();
            assert_eq!(local_stamp(secs).unwrap(), want, "at {secs}");
        }
    }

    #[test]
    fn the_stamp_is_not_utc_wherever_the_box_is_not_utc() {
        let secs = 1_756_771_200_i64;
        let utc = Command::new("date")
            .args(["-u", &format!("-d@{secs}"), "+%Y%m%d-%H%M%S"])
            .output()
            .expect("run date");
        let utc = String::from_utf8_lossy(&utc.stdout).trim().to_owned();
        let ours = local_stamp(secs).unwrap();
        if ours == utc {
            // A UTC box cannot tell the two apart. Say so rather than claim a
            // check that did not happen.
            eprintln!("note: this box is on UTC, so local and UTC are the same stamp");
            return;
        }
        assert_ne!(ours, utc, "the stamp must be local, not UTC");
    }

    #[test]
    fn the_stamp_agrees_with_date_at_the_same_instant() {
        // The live form the plan names. `date` is read after our own stamp, so
        // the only legal disagreement is one second at a boundary.
        let ours = local_stamp(
            i64::try_from(
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
            )
            .unwrap(),
        )
        .unwrap();
        let out = Command::new("date")
            .arg("+%Y%m%d-%H%M%S")
            .output()
            .expect("run date");
        let theirs = String::from_utf8_lossy(&out.stdout).trim().to_owned();
        if ours == theirs {
            return;
        }
        // One second apart at most: parse both back and compare.
        let secs = |s: &str| -> i64 {
            let h: i64 = s[9..11].parse().unwrap();
            let m: i64 = s[11..13].parse().unwrap();
            let sec: i64 = s[13..15].parse().unwrap();
            h * 3600 + m * 60 + sec
        };
        assert!(
            (secs(&theirs) - secs(&ours)).abs() <= 1,
            "ours {ours}, date {theirs}"
        );
    }

    #[test]
    fn an_invocation_id_has_the_run_id_shape() {
        let id = invocation_id().unwrap();
        let (date, rest) = id.split_once('-').unwrap();
        let (time, hex) = rest.split_once('-').unwrap();
        assert_eq!(date.len(), 8, "{id}");
        assert_eq!(time.len(), 6, "{id}");
        assert_eq!(hex.len(), 6, "{id}");
        assert!(
            id.chars().all(|c| c.is_ascii_hexdigit() || c == '-'),
            "{id}"
        );
    }

    /// Both flags, in that order, and the user's own in front of both.
    ///
    /// One test, not two, because `rustdoc_flags` reads `RUSTDOCFLAGS` and the
    /// environment is per PROCESS while libtest runs tests in threads: a second
    /// test that set the variable would race a first that expected it unset.
    /// Splitting them was tried and the mutation run caught the race, which is
    /// why this comment exists instead of the split.
    #[test]
    fn rustdoc_flags_carry_the_extern_and_the_search_path_after_the_users_own() {
        const RLIB: &str = "/t/rt/abc/unwind/libsensorium_rt.rlib";
        const OURS: &str = "--extern sensorium_rt=/t/rt/abc/unwind/libsensorium_rt.rlib \
                            -L dependency=/t/rt/abc/unwind";
        let key = "RUSTDOCFLAGS";
        let restore = std::env::var(key).ok();
        // SAFETY (test-only): no other thread in this test binary reads or
        // writes RUSTDOCFLAGS -- `rustdoc_flags` is the only reader and this is
        // its only test.
        unsafe {
            std::env::remove_var(key);
        }
        // rustdoc resolves `sensorium_rt` as a TRANSITIVE dependency of a
        // workspace rlib, which goes through the search path and not the extern
        // map: `--extern` alone fails E0463 (measured -- see `rustdoc_flags`).
        let bare = rustdoc_flags(Path::new(RLIB));
        unsafe {
            std::env::set_var(key, "--cfg docsrs");
        }
        let appended = rustdoc_flags(Path::new(RLIB));
        unsafe {
            match restore {
                Some(v) => std::env::set_var(key, v),
                None => std::env::remove_var(key),
            }
        }
        assert_eq!(bare, OURS);
        // The order is the promise: a flag the user set is never overridden by
        // one of ours.
        assert_eq!(appended, format!("--cfg docsrs {OURS}"));
    }

    #[test]
    fn the_rustc_is_resolved_to_a_path_rather_than_recorded_as_a_bare_word() {
        // `invocation.json` carries this, and "rustc" would name no compiler in
        // particular. `RUSTC` is honoured verbatim, as cargo honours it.
        let resolved = resolve_on_path("rustc").expect("a rustc on PATH");
        assert!(resolved.contains('/'), "{resolved}");
        assert!(Path::new(&resolved).is_file(), "{resolved}");
        assert_eq!(resolve_on_path("no-such-program-anywhere-at-all"), None);
    }

    #[test]
    fn the_driver_version_is_the_crates_own() {
        assert_eq!(DRIVER_VERSION, "cargo-sensorium 0.2.0");
    }

    #[test]
    fn an_invocation_record_serialises_to_the_shape_the_converter_reads() {
        let record = Invocation {
            invocation: "20260903-070000-abcdef".to_owned(),
            subcommand: "test".to_owned(),
            cargo_args: vec!["test".to_owned(), "--lib".to_owned()],
            tier: "call".to_owned(),
            toolchain: "rustc 1.96.0".to_owned(),
            rustc_path: "/u/bin/rustc".to_owned(),
            host: "x86_64-unknown-linux-gnu".to_owned(),
            profile: "dev".to_owned(),
            workspace_root: "/w".to_owned(),
            target_dir: "/t".to_owned(),
            tool_hash: "0123456789abcdef".to_owned(),
            driver_version: DRIVER_VERSION.to_owned(),
            start_ts: 1.0,
            end_ts: None,
            cargo_exit: None,
        };
        let value: serde_json::Value =
            serde_json::from_str(&serde_json::to_string(&record).unwrap()).unwrap();
        assert_eq!(value["invocation"], "20260903-070000-abcdef");
        assert_eq!(value["subcommand"], "test");
        assert_eq!(value["cargo_args"], serde_json::json!(["test", "--lib"]));
        assert_eq!(value["tier"], "call");
        assert_eq!(value["host"], "x86_64-unknown-linux-gnu");
        assert_eq!(value["profile"], "dev");
        assert_eq!(value["workspace_root"], "/w");
        assert_eq!(value["target_dir"], "/t");
        assert_eq!(value["tool_hash"], "0123456789abcdef");
        assert_eq!(value["driver_version"], "cargo-sensorium 0.2.0");
        assert_eq!(value["rustc_path"], "/u/bin/rustc");
        // Null, not absent: the converter tells "cargo has not finished" from
        // "cargo exited 0" by the value, and an absent key is neither.
        assert_eq!(value["end_ts"], serde_json::Value::Null);
        assert_eq!(value["cargo_exit"], serde_json::Value::Null);
    }
}
