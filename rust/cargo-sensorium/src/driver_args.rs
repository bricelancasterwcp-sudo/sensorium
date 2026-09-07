//! The driver's own argv: what `cargo sensorium` takes before cargo's argv
//! begins.
//!
//! Split out of `driver.rs` when that file reached 764 lines and the focus
//! tier needed room. A PURE move: every item here is the one `driver.rs`
//! held, re-exported from it so that no caller's spelling changed.

use sensorium_transform::Focus;

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
    /// The `--focus` values, in the order given (design 2026-09-06 §2.1).
    /// Empty is the unfocused build.
    pub focus: Vec<String>,
    /// The run id this invocation is a re-run OF (design 2026-09-07 §2.1).
    /// `None` is an ordinary run. At most one: a re-run answers to exactly
    /// one original, and a second value would silently pick a winner.
    pub refocus_of: Option<String>,
    /// The argv handed to cargo, starting with the subcommand.
    pub cargo_args: Vec<String>,
}

impl DriverArgs {
    #[must_use]
    pub fn subcommand(&self) -> &str {
        self.cargo_args.first().map_or("", String::as_str)
    }
}

/// Split the driver's own flags out of cargo's.
///
/// `--tier`, `--focus` and `--refocus-of` are recognised only BEFORE the first
/// bare `--`, so a test binary's own `--tier`/`--focus`/`--refocus-of`
/// argument (after `cargo test -- …`) is never stolen.
///
/// # Errors
/// A usage message when the subcommand is missing or unknown, when `--tier`
/// has no value or a value this recorder does not implement, when `--focus`
/// has no qualname, or when `--refocus-of` has no run id or was given twice.
pub fn parse_args(args: &[String]) -> Result<DriverArgs, String> {
    let mut tier = Tier::Call;
    let mut focus: Vec<String> = Vec::new();
    let mut refocus_of: Option<String> = None;
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
            if let Some(v) = a.strip_prefix("--focus=") {
                focus.push(parse_focus(Some(v))?);
                i += 1;
                continue;
            }
            if a == "--focus" {
                focus.push(parse_focus(args.get(i + 1).map(String::as_str))?);
                i += 2;
                continue;
            }
            if let Some(v) = a.strip_prefix("--refocus-of=") {
                refocus_of = Some(parse_refocus_of(refocus_of.as_deref(), Some(v))?);
                i += 1;
                continue;
            }
            if a == "--refocus-of" {
                let v = args.get(i + 1).map(String::as_str);
                refocus_of = Some(parse_refocus_of(refocus_of.as_deref(), v)?);
                i += 2;
                continue;
            }
        }
        cargo_args.push(a.clone());
        i += 1;
    }
    match cargo_args.first().map(String::as_str) {
        Some("test" | "run") => Ok(DriverArgs {
            tier,
            focus,
            refocus_of,
            cargo_args,
        }),
        Some(other) => Err(format!(
            "unknown subcommand `{other}`; this version implements `cargo sensorium test` and \
             `cargo sensorium run`"
        )),
        None => Err(USAGE.to_owned()),
    }
}

pub const USAGE: &str = "usage: cargo sensorium test|run [--tier off|call] \
                         [--focus <qualname>]... [--refocus-of <run id>] [cargo args]";

/// One `--focus` value: a qualname that survives [`Focus::parse`].
///
/// An empty value is refused rather than dropped: it would match every
/// qualname's prefix, so a stray `--focus=` would instrument the whole
/// workspace instead of saying nothing was asked for. The test is
/// `Focus::parse` itself and not "non-empty after trimming", because a value
/// of only commas passes the latter and is then dropped by the former --
/// `--focus ,` used to run UNFOCUSED at exit 0, with no `focus:` line and a
/// trace whose missing LINE rows had no stated cause.
fn parse_focus(v: Option<&str>) -> Result<String, String> {
    match v.map(str::trim) {
        Some(value) if !Focus::parse(value).is_empty() => Ok(value.to_owned()),
        _ => Err("--focus needs a qualname".to_owned()),
    }
}

/// One `--refocus-of` value, against whatever an earlier one already set.
///
/// A re-run answers to exactly ONE original, so a second occurrence is
/// refused rather than resolved by last-wins: the new trace would otherwise
/// carry a link its caller did not choose, and `refocus`'s pair lookup would
/// find it under a run id nobody asked about. The DUPLICATE is reported
/// whatever the second value is -- correcting that value would only meet the
/// same refusal.
///
/// An empty value is refused rather than dropped, exactly as an empty
/// `--focus` is: a run id names a trace, and the empty string names none.
fn parse_refocus_of(already: Option<&str>, v: Option<&str>) -> Result<String, String> {
    if already.is_some() {
        return Err("--refocus-of given twice".to_owned());
    }
    match v.map(str::trim) {
        Some(value) if !value.is_empty() => Ok(value.to_owned()),
        _ => Err("--refocus-of needs a run id".to_owned()),
    }
}

fn parse_tier(v: &str) -> Result<Tier, String> {
    match v {
        "off" => Ok(Tier::Off),
        "call" => Ok(Tier::Call),
        other => Err(format!("unknown tier `{other}`; expected off or call")),
    }
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
    fn focus_values_are_taken_out_of_cargos_argv_in_the_order_given() {
        let p = parse_args(&v(&[
            "--focus",
            "a::b",
            "--focus=c",
            "test",
            "--",
            "--focus",
            "x",
        ]))
        .unwrap();
        assert_eq!(p.focus, v(&["a::b", "c"]));
        // A test binary's own `--focus` is never stolen.
        assert_eq!(p.cargo_args, v(&["test", "--", "--focus", "x"]));
    }

    #[test]
    fn no_focus_is_the_default_and_the_unfocused_build() {
        assert!(parse_args(&v(&["test", "--lib"])).unwrap().focus.is_empty());
    }

    #[test]
    fn a_focus_with_no_qualname_is_refused_rather_than_ignored() {
        // An empty value would match every qualname's prefix, so it is a typo
        // and never a request to instrument the whole workspace.
        for form in [
            v(&["--focus"]),
            v(&["--focus="]),
            v(&["--focus=", "test"]),
            v(&["--focus", "  ", "test"]),
            // Only commas: non-empty after trimming, and `Focus::parse`
            // drops it, so the run went ahead unfocused at exit 0.
            v(&["--focus", ",", "test"]),
            v(&["--focus=,,", "test"]),
            v(&["--focus", "a", "--focus", ",", "test"]),
        ] {
            assert_eq!(
                parse_args(&form).unwrap_err(),
                "--focus needs a qualname",
                "{form:?}"
            );
        }
    }

    #[test]
    fn a_repeated_focus_keeps_every_value_for_the_resolver_to_judge() {
        let p = parse_args(&v(&["--focus", "a", "--focus", "a", "run"])).unwrap();
        assert_eq!(p.focus, v(&["a", "a"]));
    }

    const ORIGINAL: &str = "20260101-000000-aaaaaa";

    #[test]
    fn refocus_of_is_taken_out_of_cargos_argv_in_both_forms() {
        for form in [
            v(&["--refocus-of", ORIGINAL, "run"]),
            v(&["--refocus-of=20260101-000000-aaaaaa", "run"]),
        ] {
            let p = parse_args(&form).unwrap();
            assert_eq!(p.refocus_of.as_deref(), Some(ORIGINAL), "{form:?}");
            assert_eq!(p.cargo_args, v(&["run"]), "{form:?}");
        }
    }

    #[test]
    fn no_refocus_of_is_the_default_and_an_ordinary_run() {
        assert!(parse_args(&v(&["test", "--lib"]))
            .unwrap()
            .refocus_of
            .is_none());
    }

    #[test]
    fn a_refocus_of_after_the_separator_belongs_to_the_test_binary() {
        let p = parse_args(&v(&["test", "--", "--refocus-of", ORIGINAL])).unwrap();
        assert!(p.refocus_of.is_none());
        assert_eq!(p.cargo_args, v(&["test", "--", "--refocus-of", ORIGINAL]));
    }

    /// A re-run answers to exactly ONE original. Last-wins would pick a
    /// winner silently and stamp the new trace with a link its caller did
    /// not choose.
    #[test]
    fn a_second_refocus_of_is_refused_rather_than_quietly_last_wins() {
        for form in [
            v(&["--refocus-of", "a", "--refocus-of", "b", "run"]),
            v(&["--refocus-of=a", "--refocus-of=b", "run"]),
            v(&["--refocus-of", "a", "--refocus-of=a", "run"]),
            // The duplicate is the fact reported, whatever the second value
            // is: fixing the value would only meet the same refusal.
            v(&["--refocus-of", "a", "--refocus-of=", "run"]),
        ] {
            assert_eq!(
                parse_args(&form).unwrap_err(),
                "--refocus-of given twice",
                "{form:?}"
            );
        }
    }

    #[test]
    fn a_refocus_of_with_no_run_id_is_refused_rather_than_ignored() {
        for form in [
            v(&["--refocus-of"]),
            v(&["--refocus-of="]),
            v(&["--refocus-of=", "run"]),
            v(&["--refocus-of", "  ", "run"]),
            v(&["--refocus-of", "", "run"]),
        ] {
            assert_eq!(
                parse_args(&form).unwrap_err(),
                "--refocus-of needs a run id",
                "{form:?}"
            );
        }
    }

    #[test]
    fn refocus_of_focus_and_tier_interleave_without_stealing_from_each_other() {
        let p = parse_args(&v(&[
            "--focus",
            "a::b",
            "--refocus-of",
            ORIGINAL,
            "--tier",
            "off",
            "--focus=c",
            "test",
            "--lib",
        ]))
        .unwrap();
        assert_eq!(p.tier, Tier::Off);
        assert_eq!(p.focus, v(&["a::b", "c"]));
        assert_eq!(p.refocus_of.as_deref(), Some(ORIGINAL));
        assert_eq!(p.cargo_args, v(&["test", "--lib"]));
    }
}
