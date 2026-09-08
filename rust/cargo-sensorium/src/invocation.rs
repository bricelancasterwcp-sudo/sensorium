//! The invocation record: what a run of the driver was, and how it is written.
//!
//! `invocation.json` is the converter's ONE source for a trace's workspace
//! root, toolchain, profile, focus and cargo argv -- none of which the runtime
//! inside the recorded process can see. This module holds the record's shape,
//! the facts that fill it (the profile the argv names, the rustc that will
//! compile the runtime, the run-id stamp in local time) and the write.
//!
//! Moved out of `driver.rs` when that file reached its 800-line ceiling
//! (design 2026-09-07 §6, ruling R7). A pure move: nothing about the record,
//! its field order or its serialisation changed.

use std::path::Path;
use std::process::Command;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::Serialize;

/// This binary's name and version, as it reaches a trace.
pub const DRIVER_VERSION: &str = concat!("cargo-sensorium ", env!("CARGO_PKG_VERSION"));

/// `invocation.json`, written before cargo starts and completed after it exits.
/// The converter reads it: it is where a trace's workspace root, toolchain,
/// profile and cargo argv come from, none of which the runtime can see.
#[derive(Debug, Serialize)]
pub struct Invocation {
    pub invocation: String,
    pub subcommand: String,
    pub cargo_args: Vec<String>,
    pub tier: String,
    /// The `--focus` values, de-duplicated and in the order typed. The
    /// converter's ONE source for a trace's `focus` (design A9): the driver
    /// knows what it was asked for, and the manifests -- one per focus the
    /// workspace was ever built under (A8) -- cannot say which is this run's.
    pub focus: Vec<String>,
    /// The run id this invocation is a re-run OF (design 2026-09-07 §2.1),
    /// validated against the store before anything was built. ABSENT rather
    /// than null for an ordinary run: `refocus`'s pair lookup asks which
    /// traces carry the key, and a null would be a link to nothing.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub refocus_of: Option<String>,
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
    stamped_id(now, 0)
}

/// A run id for an instant: `YYYYMMDD-HHMMSS-<6 hex>`, the stamp in local time
/// and the hex a mix of the sub-second nanos, this pid and the whole seconds.
///
/// ONE mix for both minters. The driver mints one id per invocation
/// ([`invocation_id`]) and the converter mints one per trace inside it
/// (`convert::runid::mint`); the converter is the only one that can be asked
/// for two ids at the same instant, so it passes a `salt` that ticks on every
/// call and the driver passes `0`, which shifts to nothing and leaves the mix
/// exactly what it was before the two were factored together (rung-3 inbox:
/// "`runid`/driver id-mix helper -- a small duplication ... not yet factored
/// out"). Everything else has to agree, or the two would print ids of
/// different shapes into the same store.
///
/// # Errors
/// If the instant is unreadable as seconds, or `localtime_r` refuses it.
pub fn stamped_id(now: Duration, salt: u64) -> Result<String, String> {
    let secs = i64::try_from(now.as_secs()).map_err(|e| format!("the clock is unreadable: {e}"))?;
    let mix = u64::from(now.subsec_nanos())
        ^ (u64::from(std::process::id()) << 20)
        ^ (now.as_secs() << 7)
        ^ (salt << 3);
    Ok(format!("{}-{:06x}", local_stamp(secs)?, mix & 0x00ff_ffff))
}

/// `YYYYMMDD-HHMMSS` for a Unix timestamp, in the local zone.
///
/// Private to this module: [`stamped_id`] is the whole run-id shape and is
/// what every caller outside `invocation.rs` wants. It was `pub` while
/// `convert::runid` spelled the stamp and the mix separately.
///
/// # Errors
/// If `localtime_r` refuses the timestamp.
fn local_stamp(secs: i64) -> Result<String, String> {
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

pub(crate) fn write_invocation(path: &Path, record: &Invocation) -> Result<(), String> {
    let json = serde_json::to_string(record)
        .map_err(|e| format!("cannot serialise the invocation record: {e}"))?;
    std::fs::write(path, json.as_bytes())
        .map_err(|e| format!("cannot write {}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| (*s).to_owned()).collect()
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

    /// The dedupe's own pin: `stamped_id(now, 0)` must be byte-for-byte the
    /// expression `invocation_id` spelled before the two minters were factored
    /// together, and the salt must be the only thing the converter adds.
    #[test]
    fn the_shared_mix_is_the_drivers_old_one_and_the_salt_is_the_only_addition() {
        let now = Duration::new(1_756_771_200, 123_456_789);
        // Re-derived here, not read out of the implementation under test.
        let old_mix = u64::from(now.subsec_nanos())
            ^ (u64::from(std::process::id()) << 20)
            ^ (now.as_secs() << 7);
        let stamp = local_stamp(i64::try_from(now.as_secs()).unwrap()).unwrap();
        assert_eq!(
            stamped_id(now, 0).unwrap(),
            format!("{stamp}-{:06x}", old_mix & 0x00ff_ffff),
            "salt 0 must leave the driver's mix exactly as it was"
        );
        // Deterministic in the instant: the same instant and salt mint the
        // same id, which is why the converter has to tick a salt at all.
        assert_eq!(stamped_id(now, 0).unwrap(), stamped_id(now, 0).unwrap());
        assert_ne!(
            stamped_id(now, 0).unwrap(),
            stamped_id(now, 1).unwrap(),
            "one salt tick must move the hex"
        );
        // And the shape both minters promise.
        let id = stamped_id(now, 7).unwrap();
        let (date, rest) = id.split_once('-').unwrap();
        let (time, hex) = rest.split_once('-').unwrap();
        assert_eq!((date.len(), time.len(), hex.len()), (8, 6, 6), "{id}");
        assert!(hex.chars().all(|c| c.is_ascii_hexdigit()), "{id}");
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

    #[test]
    fn the_driver_version_is_the_crates_own() {
        assert_eq!(DRIVER_VERSION, "cargo-sensorium 0.5.3");
    }

    #[test]
    fn an_invocation_record_serialises_to_the_shape_the_converter_reads() {
        let mut record = Invocation {
            invocation: "20260903-070000-abcdef".to_owned(),
            subcommand: "test".to_owned(),
            cargo_args: vec!["test".to_owned(), "--lib".to_owned()],
            tier: "call".to_owned(),
            focus: vec!["load".to_owned()],
            refocus_of: None,
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
        // The converter's only source for a trace's `focus` (R-F11).
        assert_eq!(value["focus"], serde_json::json!(["load"]));
        assert_eq!(value["host"], "x86_64-unknown-linux-gnu");
        assert_eq!(value["profile"], "dev");
        assert_eq!(value["workspace_root"], "/w");
        assert_eq!(value["target_dir"], "/t");
        assert_eq!(value["tool_hash"], "0123456789abcdef");
        assert_eq!(value["driver_version"], "cargo-sensorium 0.5.3");
        assert_eq!(value["rustc_path"], "/u/bin/rustc");
        // Null, not absent: the converter tells "cargo has not finished" from
        // "cargo exited 0" by the value, and an absent key is neither.
        assert_eq!(value["end_ts"], serde_json::Value::Null);
        assert_eq!(value["cargo_exit"], serde_json::Value::Null);
        // ABSENT, not null (design 2026-09-07 §2.1): `refocus` finds a
        // re-run's new trace by asking the store which traces carry
        // `refocus_of`, and a null on every ordinary run would answer that
        // question with every trace ever recorded.
        assert!(
            value.get("refocus_of").is_none(),
            "an ordinary run must write no refocus_of key at all: {value}"
        );
        // ...and present, by name, when there was one.
        record.refocus_of = Some("20260101-000000-aaaaaa".to_owned());
        let value: serde_json::Value =
            serde_json::from_str(&serde_json::to_string(&record).unwrap()).unwrap();
        assert_eq!(value["refocus_of"], "20260101-000000-aaaaaa");
    }
}
