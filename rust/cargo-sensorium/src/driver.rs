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

use sensorium_transform::Focus;

use crate::invocation::{
    invocation_id, profile, toolchain_and_host, write_invocation, Invocation, DRIVER_VERSION,
};
use crate::launch;
use crate::refocus_of;
use crate::resolve;
use crate::rt_build::{self, Panic};
use crate::rt_src;

// The argv parse moved to `driver_args.rs` when this file reached 764 lines
// and the focus tier needed room. The two items other modules spell through
// this one are re-exported so that no caller's path changed; `DriverArgs`
// and `Tier` are named from `driver_args` itself, which is the only place
// that needs them.
pub use crate::driver_args::{parse_args, USAGE};

// The invocation record and the facts that fill it moved to `invocation.rs`
// when this file reached the 800-line ceiling (design 2026-09-07 §6, R7).
// `stamped_id` is re-exported for the same reason `parse_args` is: it is
// spelled through this module by `convert::runid`, and a pure move must not
// move a caller's path. (`local_stamp` was re-exported here for the same
// caller until it started spelling the whole mix through `stamped_id`.)
pub use crate::invocation::stamped_id;

// The cargo child's environment and launch moved to `launch.rs` in the same
// split. `cargo_path` went with it and is re-exported for the same reason
// `stamped_id` is: `resolve` spells it through this module.
pub(crate) use crate::launch::cargo_path;

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
    // Before the focus resolution below, and so before the runtime, the shim,
    // the spool and cargo: a link to a trace the store does not hold is worth
    // no build at all (design 2026-09-07 §2.1).
    if !refocus_of::gate(parsed.refocus_of.as_deref())? {
        return Ok(2);
    }
    let ws = workspace_root()?;
    let focus = parsed_focus(&parsed.focus)?;
    // BEFORE everything (design 2026-09-06 §2.2): before the runtime is
    // compiled, before the shim is installed, before a spool directory exists
    // and before cargo is invoked. A focus is a compile-time decision, so a
    // value that names nothing would otherwise cost a full instrumented build
    // and hand back a trace with no LINE row and no reason.
    if !focus.is_empty() {
        let resolved = resolve::resolve_focus(&ws, &focus)?;
        if resolved.refuses() {
            report_refusal(&resolved);
            return Ok(2);
        }
        // One line per matched qualname, on stderr, so that a record of a run
        // can quote what the focus actually selected rather than what was
        // typed.
        for qualname in &resolved.matched {
            eprintln!("focus: {qualname}");
        }
    }
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
    // The focus joins the shim's path, not just the mirror's cache key: see
    // `install_shim`. An unfocused build keeps the bare tool hash it has
    // always had, so nothing about it moves.
    let shim_key = if focus.is_empty() {
        tool_hash.clone()
    } else {
        format!("{tool_hash}-{}", focus.focus_hash())
    };
    let shim = rt_build::install_shim(&target, &exe, &shim_key)?;

    let invocation = invocation_id()?;
    let spool = target.join("sensorium").join("spool").join(&invocation);
    std::fs::create_dir_all(&spool)
        .map_err(|e| format!("cannot create {}: {e}", spool.display()))?;

    let mut record = Invocation {
        invocation: invocation.clone(),
        subcommand: parsed.subcommand().to_owned(),
        cargo_args: parsed.cargo_args.clone(),
        tier: parsed.tier.as_str().to_owned(),
        // The canonical list, not `parsed.focus`: this is byte-for-byte what
        // `SENSORIUM_FOCUS` carries and therefore what each manifest records
        // as its `focus.values`, which is what R-F11 compares against.
        focus: focus.values().to_vec(),
        refocus_of: refocus_of::canonical(parsed.refocus_of.as_deref()),
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

    let status = launch::run_cargo(&launch::Ground {
        cargo_args: &parsed.cargo_args,
        ws: &ws,
        rlib: &rlib,
        shim: &shim,
        host: &host,
        spool: &spool,
        tier: parsed.tier.as_str(),
        focus: &focus,
        target: &target,
        rt: &rt,
        tool_hash: &tool_hash,
        invocation: &invocation,
    })?;

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

/// The `--focus` values as a [`Focus`], refusing a list that parses to nothing.
///
/// `Focus::parse` drops an empty entry -- an empty value would match every
/// qualname's prefix and focus the whole workspace -- and `--focus ,` is
/// non-empty after trimming, so it reaches here and then vanishes. Without
/// this check the run went ahead UNFOCUSED at exit 0, with no `focus:` line
/// and a trace whose missing LINE rows had no stated cause.
///
/// # Errors
/// The same sentence `parse_args` gives an empty value, since it is the same
/// mistake: a value that names no function.
fn parsed_focus(values: &[String]) -> Result<Focus, String> {
    let focus = Focus::parse(&values.join(","));
    if !values.is_empty() && focus.is_empty() {
        return Err("--focus needs a qualname".to_owned());
    }
    Ok(focus)
}

/// §2.2's refusal, one line per offending value, and nothing built.
fn report_refusal(resolved: &resolve::Resolution) {
    for (value, closest) in &resolved.unmatched {
        // `Closest:` is dropped only when the workspace holds no eligible
        // function at all; an empty list would read as a claim that nothing
        // is near, which is a different and wrong statement.
        let suggestion = if closest.is_empty() {
            String::new()
        } else {
            format!(" Closest: {}", closest.join(", "))
        };
        eprintln!(
            "REFUSED: --focus {value} matches no function in the workspace; nothing was \
             built.{suggestion}"
        );
    }
    for (value, hits) in &resolved.skipped_only {
        // Every one of them, not just the first: a person told only about the
        // first would fix it and meet the same refusal again.
        let named = hits
            .iter()
            .map(|(qualname, reason)| format!("{qualname} ({reason})"))
            .collect::<Vec<_>>()
            .join(", ");
        eprintln!(
            "REFUSED: --focus {value} matches only functions the transform skips: {named}; \
             nothing was built."
        );
    }
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
    fn the_rustc_is_resolved_to_a_path_rather_than_recorded_as_a_bare_word() {
        // `invocation.json` carries this, and "rustc" would name no compiler in
        // particular. `RUSTC` is honoured verbatim, as cargo honours it.
        let resolved = resolve_on_path("rustc").expect("a rustc on PATH");
        assert!(resolved.contains('/'), "{resolved}");
        assert!(Path::new(&resolved).is_file(), "{resolved}");
        assert_eq!(resolve_on_path("no-such-program-anywhere-at-all"), None);
    }

    /// The belt to `parse_focus`'s braces: any list of values that survives
    /// argv parsing and still leaves an EMPTY focus is refused here rather
    /// than run unfocused. `--focus ,` is the case that reached production --
    /// exit 0, no `focus:` line, a trace with no LINE row and nothing
    /// anywhere saying the flag had been discarded.
    #[test]
    fn a_focus_that_parses_to_nothing_is_refused_rather_than_silently_dropped() {
        for form in [v(&[","]), v(&[",,"]), v(&[" "])] {
            assert_eq!(
                parsed_focus(&form).unwrap_err(),
                "--focus needs a qualname",
                "{form:?}"
            );
        }
    }

    #[test]
    fn no_focus_values_is_the_unfocused_build_and_not_an_error() {
        assert!(parsed_focus(&[]).unwrap().is_empty());
        assert_eq!(parsed_focus(&v(&["b", "a"])).unwrap().values(), ["b", "a"]);
    }
}
