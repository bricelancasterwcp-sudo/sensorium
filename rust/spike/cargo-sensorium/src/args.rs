//! Pure argv analysis. Nothing here touches the filesystem, so every rule the
//! wrapper's behaviour turns on is a unit test with a pinned line.
//!
//! Two jobs: decide which ROLE this process is playing, and decide what a
//! rustc argv is (crate name, crate types, `-C metadata`, the one positional
//! `.rs` crate root) and whether it must be passed through untouched.

/// Which of the binary's two lives this invocation is.
#[derive(Debug, PartialEq, Eq)]
pub enum Role {
    /// `cargo sensorium <args>` or `cargo-sensorium <args>`. Carries the args
    /// AFTER the subcommand word, if any.
    Driver(Vec<String>),
    /// Cargo's `RUSTC_WORKSPACE_WRAPPER` contract: `argv[1]` is the real rustc.
    Wrapper,
    /// No arguments at all.
    Help,
}

/// Decide the role from the whole argv (including `argv[0]`).
///
/// Cargo's contract makes this decidable without env sniffing: it always calls
/// the wrapper with the rustc PATH in `argv[1]`, which is never `sensorium`,
/// never `test`, and never starts with `-`.
#[must_use]
pub fn role(argv: &[String]) -> Role {
    match argv.get(1).map(String::as_str) {
        None => Role::Help,
        // `cargo sensorium test ...` -- cargo passes the subcommand word.
        Some("sensorium") => Role::Driver(argv[2..].to_vec()),
        Some(a) if a == "test" || a.starts_with('-') => Role::Driver(argv[1..].to_vec()),
        Some(_) => Role::Wrapper,
    }
}

/// What a rustc argv says about the unit being compiled.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct UnitArgs {
    pub crate_name: Option<String>,
    pub crate_types: Vec<String>,
    /// The `-C metadata=<hash>` value: the manifest's key and the unit's
    /// identity everywhere downstream (spec 2.4).
    pub metadata: Option<String>,
    /// Every positional argument, in order. The crate root is the one that
    /// ends in `.rs`.
    pub positionals: Vec<String>,
    pub is_test: bool,
    pub has_print: bool,
    pub has_version_verbose: bool,
}

/// The wrapper's decision for one unit.
#[derive(Debug, PartialEq, Eq)]
pub enum Plan {
    /// Run rustc unchanged. The `&'static str` is the reason, for the record.
    PassThrough(&'static str),
    /// Instrument: `crate_root` is relative to cargo's cwd (the workspace root).
    Instrument {
        crate_name: String,
        crate_type: String,
        metadata: String,
        crate_root: String,
    },
}

/// Long options that consume the NEXT argv entry when not written `--opt=val`.
const LONG_VALUE_FLAGS: &[&str] = &[
    "--crate-name",
    "--crate-type",
    "--edition",
    "--emit",
    "--out-dir",
    "--target",
    "--cfg",
    "--check-cfg",
    "--extern",
    "--sysroot",
    "--error-format",
    "--json",
    "--color",
    "--diagnostic-width",
    "--remap-path-prefix",
    "--explain",
    "--cap-lints",
    "--print",
    "--codegen",
    "--warn",
    "--allow",
    "--deny",
    "--forbid",
    "--extern-location",
];

/// Short options that consume a value, either attached (`-Cfoo`) or next.
const SHORT_VALUE_FLAGS: &[&str] = &["-C", "-L", "-l", "-Z", "-W", "-A", "-D", "-F", "-o"];

/// Split a rustc argv into what the wrapper needs. `args` excludes `argv[0]`
/// and the rustc path, i.e. it is what rustc itself would see.
#[must_use]
pub fn parse(args: &[String]) -> UnitArgs {
    let mut out = UnitArgs::default();
    let mut i = 0;
    while i < args.len() {
        let arg = &args[i];
        // A lone `-` is rustc's "read the crate from stdin", and a positional.
        if arg == "-" {
            out.positionals.push(arg.clone());
            i += 1;
            continue;
        }
        if let Some(rest) = arg.strip_prefix("--") {
            let (name, attached) = match rest.split_once('=') {
                Some((n, v)) => (format!("--{n}"), Some(v.to_owned())),
                None => (arg.clone(), None),
            };
            let value = match (attached, LONG_VALUE_FLAGS.contains(&name.as_str())) {
                (Some(v), _) => Some(v),
                (None, true) => {
                    i += 1;
                    args.get(i).cloned()
                }
                (None, false) => None,
            };
            record(&mut out, &name, value.as_deref());
            i += 1;
            continue;
        }
        if arg.starts_with('-') && arg.len() >= 2 {
            let flag = &arg[..2];
            if SHORT_VALUE_FLAGS.contains(&flag) {
                let value = if arg.len() > 2 {
                    Some(arg[2..].to_owned())
                } else {
                    i += 1;
                    args.get(i).cloned()
                };
                record(&mut out, flag, value.as_deref());
                i += 1;
                continue;
            }
            // A valueless short/compound flag: `-vV`, `-g`, `--test` handled above.
            record(&mut out, arg, None);
            i += 1;
            continue;
        }
        out.positionals.push(arg.clone());
        i += 1;
    }
    out
}

fn record(out: &mut UnitArgs, name: &str, value: Option<&str>) {
    match (name, value) {
        ("--crate-name", Some(v)) => out.crate_name = Some(v.to_owned()),
        ("--crate-type", Some(v)) => out.crate_types.push(v.to_owned()),
        ("-C", Some(v)) => {
            if let Some(m) = v.strip_prefix("metadata=") {
                out.metadata = Some(m.to_owned());
            }
        }
        ("--print", _) => out.has_print = true,
        ("--test", _) => out.is_test = true,
        ("-vV", _) => out.has_version_verbose = true,
        _ => {}
    }
}

/// The passthrough rules of spec 2.1, in the order they are checked.
#[must_use]
pub fn plan(args: &[String]) -> Plan {
    let u = parse(args);
    if u.has_version_verbose {
        return Plan::PassThrough("-vV");
    }
    if u.has_print {
        return Plan::PassThrough("--print");
    }
    if u.positionals.iter().any(|p| p == "-") {
        return Plan::PassThrough("stdin");
    }
    if u.crate_types.iter().any(|t| t == "proc-macro") {
        return Plan::PassThrough("proc-macro");
    }
    let Some(name) = u.crate_name.clone() else {
        return Plan::PassThrough("no --crate-name");
    };
    if name == "___" {
        return Plan::PassThrough("probe crate ___");
    }
    if name.starts_with("build_script_") {
        return Plan::PassThrough("build script");
    }
    let roots: Vec<&String> = u.positionals.iter().filter(|p| p.ends_with(".rs")).collect();
    let [root] = roots.as_slice() else {
        return if roots.is_empty() {
            Plan::PassThrough("no crate root")
        } else {
            Plan::PassThrough("ambiguous crate root")
        };
    };
    let Some(metadata) = u.metadata.clone() else {
        return Plan::PassThrough("no -C metadata");
    };
    // A `--test` unit carries no `--crate-type`; cargo compiles it as a test
    // harness binary, and the manifest must say which of the two it is.
    let crate_type = if u.crate_types.is_empty() {
        if u.is_test {
            "test".to_owned()
        } else {
            "unknown".to_owned()
        }
    } else {
        u.crate_types.join("+")
    };
    Plan::Instrument {
        crate_name: name,
        crate_type,
        metadata,
        crate_root: (*root).clone(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| (*s).to_owned()).collect()
    }

    /// Captured verbatim from cargo 1.96 building the probe workspace with a
    /// dumping `RUSTC_WORKSPACE_WRAPPER` (see the task report). If this ever
    /// stops parsing, the wrapper's whole contract has moved.
    fn real_lib_argv() -> Vec<String> {
        v(&[
            "--crate-name",
            "probe_core",
            "--edition=2021",
            "probe-core/src/lib.rs",
            "--error-format=json",
            "--json=diagnostic-rendered-ansi,artifacts,future-incompat",
            "--crate-type",
            "lib",
            "--emit=dep-info,metadata,link",
            "-C",
            "embed-bitcode=no",
            "-C",
            "debuginfo=2",
            "--check-cfg",
            "cfg(docsrs,test)",
            "--check-cfg",
            "cfg(feature, values())",
            "-C",
            "metadata=a98bc0df34adbff2",
            "-C",
            "extra-filename=-422a3f00d4b3c5c8",
            "--out-dir",
            "/tmp/dumptarget/debug/deps",
            "-C",
            "incremental=/tmp/dumptarget/debug/incremental",
            "-L",
            "dependency=/tmp/dumptarget/debug/deps",
        ])
    }

    #[test]
    fn a_real_lib_argv_yields_root_metadata_and_type() {
        assert_eq!(
            plan(&real_lib_argv()),
            Plan::Instrument {
                crate_name: "probe_core".to_owned(),
                crate_type: "lib".to_owned(),
                metadata: "a98bc0df34adbff2".to_owned(),
                crate_root: "probe-core/src/lib.rs".to_owned(),
            }
        );
    }

    #[test]
    fn check_cfg_values_are_not_mistaken_for_positionals() {
        // `cfg(feature, values())` follows `--check-cfg` as a SEPARATE argv
        // entry and does not start with `-`. Drop --check-cfg from the
        // value-flag table and this argument becomes a positional.
        let u = parse(&real_lib_argv());
        assert_eq!(u.positionals, v(&["probe-core/src/lib.rs"]));
    }

    #[test]
    fn a_test_unit_has_no_crate_type_and_is_named_test() {
        let args = v(&[
            "--crate-name",
            "e7",
            "--edition=2021",
            "probe-app/tests/e7.rs",
            "--emit=dep-info,link",
            "--test",
            "-C",
            "metadata=deadbeef",
        ]);
        assert_eq!(
            plan(&args),
            Plan::Instrument {
                crate_name: "e7".to_owned(),
                crate_type: "test".to_owned(),
                metadata: "deadbeef".to_owned(),
                crate_root: "probe-app/tests/e7.rs".to_owned(),
            }
        );
    }

    #[test]
    fn version_verbose_passes_through() {
        assert_eq!(plan(&v(&["-vV"])), Plan::PassThrough("-vV"));
    }

    #[test]
    fn the_stdin_probe_passes_through() {
        // Captured verbatim: cargo's crate-type probe reads from stdin.
        let args = v(&[
            "-",
            "--crate-name",
            "___",
            "--print=file-names",
            "--crate-type",
            "bin",
            "--crate-type",
            "proc-macro",
            "--print=sysroot",
            "-Wwarnings",
        ]);
        // `--print` is checked before stdin, and both before `___`: any of the
        // three is sufficient, so assert only that it is not instrumented.
        assert!(matches!(plan(&args), Plan::PassThrough(_)));
    }

    #[test]
    fn a_bare_stdin_unit_passes_through() {
        let args = v(&["-", "--crate-name", "x", "-C", "metadata=a"]);
        assert_eq!(plan(&args), Plan::PassThrough("stdin"));
    }

    #[test]
    fn the_underscore_probe_passes_through() {
        let args = v(&["--crate-name", "___", "x.rs", "-C", "metadata=a"]);
        assert_eq!(plan(&args), Plan::PassThrough("probe crate ___"));
    }

    #[test]
    fn a_build_script_passes_through() {
        let args = v(&[
            "--crate-name",
            "build_script_build",
            "bench-caller/build.rs",
            "-C",
            "metadata=a",
            "--crate-type",
            "bin",
        ]);
        assert_eq!(plan(&args), Plan::PassThrough("build script"));
    }

    #[test]
    fn a_proc_macro_passes_through() {
        let args = v(&[
            "--crate-name",
            "derive_thing",
            "src/lib.rs",
            "--crate-type",
            "proc-macro",
            "-C",
            "metadata=a",
        ]);
        assert_eq!(plan(&args), Plan::PassThrough("proc-macro"));
    }

    #[test]
    fn a_print_query_passes_through_even_with_a_crate_root() {
        let args = v(&["--crate-name", "x", "x.rs", "--print", "cfg", "-C", "metadata=a"]);
        assert_eq!(plan(&args), Plan::PassThrough("--print"));
    }

    #[test]
    fn attached_and_separated_c_metadata_read_the_same() {
        let a = parse(&v(&["-Cmetadata=abc"]));
        let b = parse(&v(&["-C", "metadata=abc"]));
        assert_eq!(a.metadata.as_deref(), Some("abc"));
        assert_eq!(a.metadata, b.metadata);
    }

    #[test]
    fn an_out_dir_that_ends_in_rs_is_not_a_crate_root() {
        // `--out-dir` consumes its value, so a directory called `weird.rs`
        // never becomes the crate root.
        let args = v(&[
            "--crate-name",
            "x",
            "--out-dir",
            "/tmp/weird.rs",
            "real/src/lib.rs",
            "-C",
            "metadata=a",
            "--crate-type",
            "lib",
        ]);
        match plan(&args) {
            Plan::Instrument { crate_root, .. } => assert_eq!(crate_root, "real/src/lib.rs"),
            other => panic!("expected Instrument, got {other:?}"),
        }
    }

    #[test]
    fn role_is_the_wrapper_when_argv1_is_a_rustc_path() {
        let argv = v(&["/t/shim/cargo-sensorium", "/home/x/.rustup/bin/rustc", "-vV"]);
        assert_eq!(role(&argv), Role::Wrapper);
    }

    #[test]
    fn role_is_the_driver_for_the_cargo_subcommand_form() {
        let argv = v(&["cargo-sensorium", "sensorium", "test", "--lib"]);
        assert_eq!(role(&argv), Role::Driver(v(&["test", "--lib"])));
    }

    #[test]
    fn role_is_the_driver_for_the_direct_form_and_for_flags_first() {
        assert_eq!(
            role(&v(&["cargo-sensorium", "test", "--lib"])),
            Role::Driver(v(&["test", "--lib"]))
        );
        assert_eq!(
            role(&v(&["cargo-sensorium", "--tier", "off", "test"])),
            Role::Driver(v(&["--tier", "off", "test"]))
        );
    }
}
