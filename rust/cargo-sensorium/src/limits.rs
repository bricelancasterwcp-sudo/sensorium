//! Recording caps for one `cargo sensorium` invocation, resolved here
//! because the driver has `serde_json` and the runtime does not.
//!
//! Order, first value wins: a CLI flag, then the environment, then
//! `$SENSORIUM_DIR/config.json` (or `~/.sensorium/config.json`), then the
//! built-in default. `0` is unlimited. `--no-cap` is unlimited for every
//! knob the command did not set.
//!
//! Size suffixes `K`/`M`/`G`, `KB`/`MB`/`GB` and `KiB`/`MiB`/`GiB` are all
//! powers of 1024, matching `sensorium.limits.parse_size`. The resolved
//! values are plain decimal integers on the cargo child's environment.

use std::collections::BTreeMap;
use std::path::Path;

use serde_json::{Map, Value};

use sensorium_rt::{DEFAULT_MAX_BYTES, DEFAULT_MAX_CALLS, DEFAULT_MAX_EVENTS};

const ENV_EVENTS: &str = "SENSORIUM_MAX_EVENTS";
const ENV_BYTES: &str = "SENSORIUM_MAX_BYTES";
const ENV_CALLS: &str = "SENSORIUM_MAX_CALLS";

const SUFFIXES: &[(&str, u64)] = &[
    ("gib", 1024 * 1024 * 1024),
    ("mib", 1024 * 1024),
    ("kib", 1024),
    ("gb", 1024 * 1024 * 1024),
    ("mb", 1024 * 1024),
    ("kb", 1024),
    ("g", 1024 * 1024 * 1024),
    ("m", 1024 * 1024),
    ("k", 1024),
];

/// What the command line set. `None` means the flag was not passed.
pub struct CapFlags<'a> {
    pub max_events: Option<&'a str>,
    pub max_bytes: Option<&'a str>,
    pub max_calls: Option<&'a str>,
    pub no_cap: bool,
}

/// The integers the runtime will read. `0` is unlimited.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Limits {
    pub max_events: u64,
    pub max_bytes: u64,
    pub max_calls: u64,
}

/// Resolve against the process environment and the store config file.
///
/// # Errors
/// A size that cannot be read, or a config file that exists and is not a
/// JSON object.
pub fn resolve(flags: &CapFlags<'_>) -> Result<Limits, String> {
    let env: BTreeMap<String, String> = std::env::vars().collect();
    let config = load_config()?;
    resolve_with(flags, &env, &config)
}

/// `config` is the object already loaded. Tests pass it directly so they
/// do not race on the process environment.
///
/// # Errors
/// A size that cannot be read.
pub fn resolve_with(
    flags: &CapFlags<'_>,
    env: &BTreeMap<String, String>,
    config: &Map<String, Value>,
) -> Result<Limits, String> {
    let mut max_events = flags.max_events.map(str::to_owned);
    let mut max_bytes = flags.max_bytes.map(str::to_owned);
    let mut max_calls = flags.max_calls.map(str::to_owned);
    if flags.no_cap {
        if max_events.is_none() {
            max_events = Some("0".to_owned());
        }
        if max_bytes.is_none() {
            max_bytes = Some("0".to_owned());
        }
        if max_calls.is_none() {
            max_calls = Some("0".to_owned());
        }
    }
    Ok(Limits {
        max_events: pick(
            max_events.as_deref(),
            env_text(env, ENV_EVENTS),
            config.get("max_events"),
            DEFAULT_MAX_EVENTS,
        )?,
        max_bytes: pick(
            max_bytes.as_deref(),
            env_text(env, ENV_BYTES),
            config.get("max_bytes"),
            DEFAULT_MAX_BYTES,
        )?,
        max_calls: pick(
            max_calls.as_deref(),
            env_text(env, ENV_CALLS),
            config.get("max_calls"),
            DEFAULT_MAX_CALLS,
        )?,
    })
}

fn env_text<'a>(env: &'a BTreeMap<String, String>, name: &str) -> Option<&'a str> {
    env.get(name)
        .map(String::as_str)
        .filter(|s| !s.trim().is_empty())
}

fn pick(
    cli: Option<&str>,
    env_text: Option<&str>,
    config: Option<&Value>,
    default: u64,
) -> Result<u64, String> {
    if let Some(cli) = cli {
        return parse_size_str(cli);
    }
    if let Some(env_text) = env_text {
        return parse_size_str(env_text);
    }
    if let Some(config) = config {
        return parse_size_value(config);
    }
    Ok(default)
}

/// Bytes or a count. `0` is unlimited. Suffixes are powers of 1024.
///
/// # Errors
/// Empty, negative, or not a number.
pub fn parse_size_str(text: &str) -> Result<u64, String> {
    let shown = text;
    let mut raw = text.trim().to_ascii_lowercase().replace('_', "");
    if raw.is_empty() {
        return Err("empty size".to_owned());
    }
    let mut mult = 1u64;
    for (suffix, factor) in SUFFIXES {
        if raw.ends_with(suffix) && raw.len() > suffix.len() {
            raw.truncate(raw.len() - suffix.len());
            raw = raw.trim().to_owned();
            mult = *factor;
            break;
        }
    }
    if raw.is_empty() {
        return Err(format!("not a size: {shown:?}"));
    }
    if raw.contains('.') {
        let number: f64 = raw.parse().map_err(|_| format!("not a size: {shown:?}"))?;
        return scale_f64(number, mult, shown);
    }
    let number: u64 = raw.parse().map_err(|_| format!("not a size: {shown:?}"))?;
    number
        .checked_mul(mult)
        .ok_or_else(|| format!("size overflows: {shown:?}"))
}

fn scale_f64(number: f64, mult: u64, shown: &str) -> Result<u64, String> {
    if !number.is_finite() || number < 0.0 {
        return Err(format!("size must be >= 0 (got {shown:?})"));
    }
    let scaled = number * mult as f64;
    if !scaled.is_finite() || scaled > u64::MAX as f64 {
        return Err(format!("size overflows: {shown:?}"));
    }
    Ok(scaled as u64)
}

fn parse_size_value(value: &Value) -> Result<u64, String> {
    match value {
        Value::Number(n) => {
            if let Some(i) = n.as_u64() {
                return Ok(i);
            }
            if let Some(i) = n.as_i64() {
                if i < 0 {
                    return Err(format!("size must be >= 0 (got {i})"));
                }
            }
            match n.as_f64() {
                Some(f) => scale_f64(f, 1, &n.to_string()),
                None => Err(format!("not a size: {n}")),
            }
        }
        Value::String(s) => parse_size_str(s),
        other => Err(format!("not a size: {other}")),
    }
}

fn load_config() -> Result<Map<String, Value>, String> {
    let root = match crate::convert::store_root() {
        Ok(root) => root,
        Err(_) => return Ok(Map::new()),
    };
    let path = root.join("config.json");
    if !path.is_file() {
        return Ok(Map::new());
    }
    read_config_file(&path)
}

/// A missing file is the caller's concern. A file that is not a JSON object
/// is an error: ignoring it would record on a policy the user thought they
/// had written.
///
/// # Errors
/// Unreadable, not JSON, or JSON that is not an object.
pub fn read_config_file(path: &Path) -> Result<Map<String, Value>, String> {
    let text = std::fs::read_to_string(path)
        .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    let value: Value =
        serde_json::from_str(&text).map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    match value {
        Value::Object(map) => Ok(map),
        _ => Err(format!("{} must be a JSON object", path.display())),
    }
}

/// After a run, when a retention rule is set in the environment or the
/// store config. Failure is printed and ignored. The child's status is not
/// touched. No rule means do not spawn a process.
pub fn maybe_gc() {
    if !gc_requested() {
        return;
    }
    let Some(mut cmd) = gc_command() else {
        eprintln!("sensorium: gc failed: sensorium is not on PATH");
        return;
    };
    match cmd.status() {
        Ok(_) => {}
        Err(e) => eprintln!("sensorium: gc failed: {e}"),
    }
}

fn gc_requested() -> bool {
    fn set(name: &str) -> bool {
        std::env::var_os(name).is_some_and(|v| !v.is_empty())
    }
    if set("SENSORIUM_STORE_BUDGET") || set("SENSORIUM_GC_KEEP") || set("SENSORIUM_GC_OLDER_THAN") {
        return true;
    }
    match load_config() {
        Ok(map) => config_has_store_policy(&map),
        Err(_) => false,
    }
}

fn config_has_store_policy(config: &Map<String, Value>) -> bool {
    ["store_budget", "gc_keep", "gc_older_than_days"]
        .iter()
        .any(|key| matches!(config.get(*key), Some(value) if !value.is_null()))
}

fn gc_command() -> Option<std::process::Command> {
    if let Some(path) = on_path("sensorium") {
        let mut cmd = std::process::Command::new(path);
        cmd.arg("gc");
        return Some(cmd);
    }
    if let Some(path) = on_path("python3") {
        let mut cmd = std::process::Command::new(path);
        cmd.args(["-m", "sensorium", "gc"]);
        return Some(cmd);
    }
    None
}

fn on_path(name: &str) -> Option<std::path::PathBuf> {
    let path = std::env::var_os("PATH")?;
    std::env::split_paths(&path)
        .map(|dir| dir.join(name))
        .find(|candidate| candidate.is_file())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn flags<'a>(
        events: Option<&'a str>,
        bytes: Option<&'a str>,
        calls: Option<&'a str>,
        no_cap: bool,
    ) -> CapFlags<'a> {
        CapFlags {
            max_events: events,
            max_bytes: bytes,
            max_calls: calls,
            no_cap,
        }
    }

    #[test]
    fn suffixes_are_powers_of_1024() {
        assert_eq!(parse_size_str("0").unwrap(), 0);
        assert_eq!(
            parse_size_str("1.5M").unwrap(),
            (1.5 * 1024.0 * 1024.0) as u64
        );
        assert_eq!(parse_size_str("2KiB").unwrap(), 2048);
        assert_eq!(parse_size_str("1KB").unwrap(), 1024);
        assert_eq!(parse_size_str("4_096").unwrap(), 4096);
        assert_eq!(parse_size_str("1GiB").unwrap(), 1024u64.pow(3));
        assert!(parse_size_str("-1").is_err());
        assert!(parse_size_str("nope").is_err());
        assert!(parse_size_str("").is_err());
    }

    #[test]
    fn cli_beats_env_beats_config_beats_default() {
        let mut env = BTreeMap::new();
        env.insert(ENV_EVENTS.to_owned(), "20".to_owned());
        env.insert(ENV_BYTES.to_owned(), "2K".to_owned());
        env.insert(ENV_CALLS.to_owned(), "8".to_owned());
        let config = json!({"max_events": 10, "max_bytes": "1K", "max_calls": 4});
        let config = config.as_object().unwrap();
        let cli = resolve_with(
            &flags(Some("30"), Some("3K"), Some("9"), false),
            &env,
            config,
        )
        .unwrap();
        assert_eq!(
            cli,
            Limits {
                max_events: 30,
                max_bytes: 3 * 1024,
                max_calls: 9
            }
        );
        let from_env = resolve_with(&flags(None, None, None, false), &env, config).unwrap();
        assert_eq!(
            from_env,
            Limits {
                max_events: 20,
                max_bytes: 2 * 1024,
                max_calls: 8
            }
        );
        let from_cfg =
            resolve_with(&flags(None, None, None, false), &BTreeMap::new(), config).unwrap();
        assert_eq!(
            from_cfg,
            Limits {
                max_events: 10,
                max_bytes: 1024,
                max_calls: 4
            }
        );
        let defaults = resolve_with(
            &flags(None, None, None, false),
            &BTreeMap::new(),
            &Map::new(),
        )
        .unwrap();
        assert_eq!(defaults.max_events, DEFAULT_MAX_EVENTS);
        assert_eq!(defaults.max_bytes, DEFAULT_MAX_BYTES);
        assert_eq!(defaults.max_calls, DEFAULT_MAX_CALLS);
    }

    #[test]
    fn no_cap_zeroes_only_the_knobs_the_command_did_not_set() {
        let mut env = BTreeMap::new();
        env.insert(ENV_CALLS.to_owned(), "3".to_owned());
        let got = resolve_with(&flags(None, None, Some("5"), true), &env, &Map::new()).unwrap();
        assert_eq!(got.max_calls, 5);
        assert_eq!(got.max_events, 0);
        assert_eq!(got.max_bytes, 0);
    }

    #[test]
    fn a_config_file_that_is_not_an_object_is_an_error() {
        let dir = std::env::temp_dir().join(format!("sensorium-cap-cfg-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("config.json");
        std::fs::write(&path, b"[1, 2]").unwrap();
        let err = read_config_file(&path).unwrap_err();
        assert!(err.contains("must be a JSON object"), "{err}");
        std::fs::write(&path, b"{\"max_calls\": 3, \"ignored\": true}").unwrap();
        let map = read_config_file(&path).unwrap();
        assert_eq!(map.get("max_calls").and_then(Value::as_u64), Some(3));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_store_policy_in_config_is_a_gc_request() {
        let config = json!({"store_budget": "1M", "max_calls": 4});
        assert!(config_has_store_policy(config.as_object().unwrap()));
        let days = json!({"gc_older_than_days": 2});
        assert!(config_has_store_policy(days.as_object().unwrap()));
        let keep = json!({"gc_keep": 3});
        assert!(config_has_store_policy(keep.as_object().unwrap()));
        let caps_only = json!({"max_events": 10, "store_budget": null});
        assert!(!config_has_store_policy(caps_only.as_object().unwrap()));
        assert!(!config_has_store_policy(&Map::new()));
    }

    #[test]
    fn a_bool_config_value_is_not_a_size() {
        let config = json!({"max_events": true});
        let err = resolve_with(
            &flags(None, None, None, false),
            &BTreeMap::new(),
            config.as_object().unwrap(),
        )
        .unwrap_err();
        assert!(err.contains("not a size"), "{err}");
    }
}
