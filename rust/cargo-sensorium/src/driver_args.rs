//! The driver's own argv: what `cargo sensorium` takes before cargo's argv
//! begins.
//!
//! Split out of `driver.rs` when that file reached 764 lines and the focus
//! tier needed room. A PURE move: every item here is the one `driver.rs`
//! held, re-exported from it so that no caller's spelling changed.

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
}
