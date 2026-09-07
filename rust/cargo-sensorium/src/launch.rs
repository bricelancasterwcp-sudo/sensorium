//! The cargo child: the ground it is given, and the launch.
//!
//! Cargo stays the builder and the runner of everything. Once the driver has
//! prepared the ground -- the runtime rlib, the shim, an invocation id, a
//! spool directory -- what remains is one `Command`, and this module is it:
//! the one place every variable this recorder sets on cargo can be read at
//! once, in the order it sets them.
//!
//! Moved out of `driver.rs` when that file reached its 800-line ceiling
//! (design 2026-09-07 §6, ruling R7). A pure move: the variables, their
//! values and their order are what they were, and the only edits are the
//! reference shapes that a block lifted out of `go` needs.

use std::path::Path;
use std::process::{Command, ExitStatus};

use sensorium_transform::Focus;

/// What the cargo child is given.
///
/// A struct rather than twelve arguments: the fields carry the driver's own
/// local names, so the launch below is the block that stood inside `go`,
/// unchanged.
#[derive(Clone, Copy)]
pub(crate) struct Ground<'a> {
    pub(crate) cargo_args: &'a [String],
    pub(crate) ws: &'a Path,
    pub(crate) rlib: &'a Path,
    pub(crate) shim: &'a Path,
    pub(crate) host: &'a str,
    pub(crate) spool: &'a Path,
    pub(crate) tier: &'a str,
    pub(crate) focus: &'a Focus,
    pub(crate) target: &'a Path,
    pub(crate) rt: &'a Path,
    pub(crate) tool_hash: &'a str,
    pub(crate) invocation: &'a str,
}

/// Run cargo with the argv the user typed, and wait for it.
///
/// # Errors
/// If cargo cannot be run at all. A cargo that RAN and failed is not an error
/// here: its status is the answer, and the driver records it.
pub(crate) fn run_cargo(ground: &Ground<'_>) -> Result<ExitStatus, String> {
    let Ground {
        cargo_args,
        ws,
        rlib,
        shim,
        host,
        spool,
        tier,
        focus,
        target,
        rt,
        tool_hash,
        invocation,
    } = *ground;
    Command::new(cargo_path())
        .args(cargo_args)
        .current_dir(ws)
        // Doctests are not routed through `RUSTC_WORKSPACE_WRAPPER` — cargo
        // says nothing about rustdoc — but they DO link the instrumented rlibs
        // and they DO spool, so without this a doctest fails with E0463
        // (findings §5.23). Appended to the user's own, never replacing it.
        .env("RUSTDOCFLAGS", rustdoc_flags(rlib))
        .env("RUSTC_WORKSPACE_WRAPPER", shim)
        .env(runner_env_var(host), format!("{} --runner", shim.display()))
        .env("SENSORIUM_SPOOL", spool)
        .env("SENSORIUM_TIER", tier)
        // Design §2.3: the values as given, comma-joined; qualnames cannot
        // contain a comma. Always set, so an outer run's focus can never leak
        // into this one -- empty is exactly "no focus" to the wrapper.
        .env("SENSORIUM_FOCUS", focus.values().join(","))
        .env("SENSORIUM_TARGET", target)
        .env("SENSORIUM_WS", ws)
        .env("SENSORIUM_RT_DIR", rt)
        .env("SENSORIUM_TOOL_HASH", tool_hash)
        .env("SENSORIUM_INVOCATION", invocation)
        .status()
        .map_err(|e| format!("cannot run cargo: {e}"))
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

pub(crate) fn cargo_path() -> String {
    // Cargo sets `CARGO` when it invokes a subcommand, so `cargo +nightly
    // sensorium test` uses the nightly cargo rather than whatever is on PATH.
    std::env::var("CARGO")
        .ok()
        .filter(|v| !v.is_empty())
        .unwrap_or_else(|| "cargo".to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

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
}
