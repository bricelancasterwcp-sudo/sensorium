//! Declared with `#[cfg_attr(windows, path = "maybe_windows.rs")]`. The
//! wrapper does not evaluate `cfg`, so it reports this module unreached and
//! never rewrites this file. Its fns are therefore NOT instrumented -- a
//! declared gap (plan decision D3), visible in the manifest's
//! `unreached_files` and printed by `sensorium info`.

pub fn maybe_marker() -> &'static str {
    "maybe"
}
