//! The driver role: `cargo sensorium test [cargo args...]`.
//!
//! Cargo stays the runner (spec 2.5). The driver only prepares the ground --
//! runtime rlib, shim path, invocation id, spool directory, environment -- and
//! then runs `cargo test` with the argv the user typed, unchanged.

use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::rt_build;

/// `SENSORIUM_TIER` values this spike knows.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Off,
    Call,
}

impl Tier {
    fn as_str(self) -> &'static str {
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
    /// The argv handed to cargo, starting with the subcommand (`test`).
    pub cargo_args: Vec<String>,
}

/// Split the driver's own flags out of cargo's.
///
/// `--tier` is recognised only BEFORE the first bare `--`, so a test binary's
/// own `--tier` argument (after `cargo test -- ...`) is never stolen.
///
/// # Errors
/// A usage message when the subcommand is missing or unknown, or when `--tier`
/// has no or a bad value.
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
        Some("test") => Ok(DriverArgs { tier, cargo_args }),
        Some(other) => Err(format!(
            "unknown subcommand `{other}`; this spike implements `cargo sensorium test` only"
        )),
        None => Err("usage: cargo sensorium test [--tier off|call] [cargo test args]".to_owned()),
    }
}

fn parse_tier(v: &str) -> Result<Tier, String> {
    match v {
        "off" => Ok(Tier::Off),
        "call" => Ok(Tier::Call),
        other => Err(format!("unknown tier `{other}`; expected off or call")),
    }
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
    let target = std::env::var_os("CARGO_TARGET_DIR")
        .map_or_else(|| ws.join("target"), PathBuf::from);
    let spike = spike_root();
    let rt = rt_build::build(&spike)?;
    let exe = std::env::current_exe().map_err(|e| format!("cannot find own path: {e}"))?;
    let hash = rt_build::tool_hash(&exe, &rt.rlib)?;
    let shim = rt_build::install_shim(&target, &exe, &hash)?;

    let invocation = invocation_id();
    let spool = target.join("sensorium").join("spool").join(&invocation);
    std::fs::create_dir_all(&spool).map_err(|e| format!("cannot create {}: {e}", spool.display()))?;

    // MEASURED GAP (rung 1): cargo does NOT route rustdoc through
    // RUSTC_WORKSPACE_WRAPPER, so a doctest links the instrumented rlib with no
    // `sensorium_rt` in sight and fails with E0463. Doctest snippets are not
    // instrumented -- they only need the runtime on the search path -- so the
    // fix is the two linkage flags again, this time via RUSTDOCFLAGS. Appended
    // to whatever the user already set, never replacing it.
    let rustdocflags = rustdoc_flags(&rt.rlib, &rt.deps_dir);

    let status = Command::new("cargo")
        .args(&parsed.cargo_args)
        .current_dir(&ws)
        .env("RUSTDOCFLAGS", &rustdocflags)
        .env("RUSTC_WORKSPACE_WRAPPER", &shim)
        .env("SENSORIUM_SPOOL", &spool)
        .env("SENSORIUM_TIER", parsed.tier.as_str())
        .env("SENSORIUM_TARGET", &target)
        .env("SENSORIUM_WS", &ws)
        .env("SENSORIUM_RT_RLIB", &rt.rlib)
        .env("SENSORIUM_RT_DEPS", &rt.deps_dir)
        .env("SENSORIUM_TOOL_HASH", &hash)
        .env("SENSORIUM_INVOCATION", &invocation)
        .status()
        .map_err(|e| format!("cannot run cargo: {e}"))?;

    // `exec` would be cheaper, but then nothing could print after cargo: the
    // process would be gone. Cargo is a child, waited for, and reported on.
    let code = status.code().unwrap_or(101);
    eprintln!("spool: {}", spool.display());
    eprintln!("cargo exit: {code}");
    Ok(code)
}

/// `RUSTDOCFLAGS` for the doctest units, preserving the user's own.
#[must_use]
pub fn rustdoc_flags(rlib: &Path, deps: &Path) -> String {
    let mine = format!(
        "--extern sensorium_rt={} -L dependency={}",
        rlib.display(),
        deps.display()
    );
    match std::env::var("RUSTDOCFLAGS") {
        Ok(existing) if !existing.trim().is_empty() => format!("{existing} {mine}"),
        _ => mine,
    }
}

fn workspace_root() -> Result<PathBuf, String> {
    let out = Command::new("cargo")
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

/// Where `sensorium-rt` is built from. Baked in at compile time because this
/// is a spike binary that is never installed; `SENSORIUM_SPIKE_ROOT` overrides.
fn spike_root() -> PathBuf {
    std::env::var_os("SENSORIUM_SPIKE_ROOT").map_or_else(
        || {
            Path::new(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .expect("cargo-sensorium always has a parent directory")
                .to_path_buf()
        },
        PathBuf::from,
    )
}

/// `YYYYMMDD-HHMMSS-<6 hex>`: sensorium's run-id shape (`paths.new_run_id`).
/// UTC, where the Python mints local time -- the SHAPE is what groups traces.
#[must_use]
pub fn invocation_id() -> String {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let nanos = now.subsec_nanos() as u64;
    let mix = nanos ^ (u64::from(std::process::id()) << 20) ^ (now.as_secs() << 7);
    format!("{}-{:06x}", utc_stamp(now.as_secs()), mix & 0x00ff_ffff)
}

/// `YYYYMMDD-HHMMSS` for a Unix timestamp, UTC. Howard Hinnant's civil-from-
/// days, which is exact for every date this box will ever see.
#[must_use]
pub fn utc_stamp(secs: u64) -> String {
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!(
        "{y:04}{m:02}{d:02}-{:02}{:02}{:02}",
        rem / 3600,
        (rem % 3600) / 60,
        rem % 60
    )
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
    fn only_test_is_implemented() {
        assert!(parse_args(&v(&["build"])).is_err());
        assert!(parse_args(&[]).is_err());
    }

    #[test]
    fn rustdoc_flags_carry_both_linkage_flags() {
        let f = rustdoc_flags(Path::new("/t/deps/librt.rlib"), Path::new("/t/deps"));
        assert!(f.contains("--extern sensorium_rt=/t/deps/librt.rlib"), "{f}");
        assert!(f.contains("-L dependency=/t/deps"), "{f}");
    }

    #[test]
    fn the_utc_stamp_matches_known_instants() {
        // `date -u -d @<n> +%Y%m%d-%H%M%S` for each.
        assert_eq!(utc_stamp(0), "19700101-000000");
        assert_eq!(utc_stamp(1_000_000_000), "20010909-014640");
        assert_eq!(utc_stamp(1_756_771_200), "20250902-000000");
        // A leap day, which a naive 365-day loop gets wrong.
        assert_eq!(utc_stamp(1_709_164_800), "20240229-000000");
        // The last day of a 31-day month: the month formula `(5*doy+2)/153`
        // rolls over exactly here, and an off-by-one in that constant is
        // invisible on every other date a test is likely to pick.
        assert_eq!(utc_stamp(1_711_843_200), "20240331-000000");
        // The last day of a year, where the civil-from-days year correction
        // (`if m <= 2 { y + 1 }`) must NOT fire.
        assert_eq!(utc_stamp(1_703_980_800), "20231231-000000");
        // A century that is not a leap year: 2100 is divisible by 100, not 400.
        assert_eq!(utc_stamp(4_107_542_400), "21000301-000000");
        // The LAST day of a 400-year era (the era starts 1600-03-01, so this is
        // day 146096 of it). Only the `doe / 146_096` term keeps it out of the
        // next era; drop that term and this date alone goes wrong.
        assert_eq!(utc_stamp(951_782_400), "20000229-000000");
    }

    #[test]
    fn an_invocation_id_has_the_run_id_shape() {
        let id = invocation_id();
        let (date, rest) = id.split_once('-').unwrap();
        let (time, hex) = rest.split_once('-').unwrap();
        assert_eq!(date.len(), 8, "{id}");
        assert_eq!(time.len(), 6, "{id}");
        assert_eq!(hex.len(), 6, "{id}");
        assert!(id.chars().all(|c| c.is_ascii_hexdigit() || c == '-'), "{id}");
    }
}
