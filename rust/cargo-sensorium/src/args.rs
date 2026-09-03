//! Pure argv analysis. Nothing here touches the filesystem, so every rule the
//! wrapper's behaviour turns on is a unit test with a pinned line.
//!
//! Two jobs: decide which ROLE this process is playing, and decide what a rustc
//! argv says about the unit being compiled — its name, crate types,
//! `-C metadata`, panic strategy and the one positional `.rs` crate root — and
//! then which of three things to do with it (instrument, fall back with a
//! recorded reason, or pass through with nothing recorded at all).

use std::path::Path;

/// Which of the binary's lives this invocation is.
///
/// Cargo's contracts make this decidable without env sniffing: the workspace
/// wrapper is always called with the real rustc's path in `argv[1]`, which is
/// never `test`, never `run`, and never starts with `-`; the target runner is
/// always called with the value the driver put in
/// `CARGO_TARGET_<HOST>_RUNNER`, whose second word is `--runner`.
#[derive(Debug, PartialEq, Eq)]
pub enum Role {
    /// `cargo sensorium test …`, `cargo-sensorium run …`. Carries the args
    /// after the binary's own name and after cargo's subcommand word.
    Driver(Vec<String>),
    /// Cargo's `RUSTC_WORKSPACE_WRAPPER` contract. `rustc` is `argv[1]`; `args`
    /// is what rustc itself would have been given.
    Wrapper { rustc: String, args: Vec<String> },
    /// Cargo's `CARGO_TARGET_<HOST>_RUNNER` contract, after our own
    /// `--runner` marker: the binary to run and its arguments.
    Runner(Vec<String>),
    /// Nothing to do but say what this is.
    Help,
}

/// Decide the role from the whole argv (including `argv[0]`).
#[must_use]
pub fn role(argv: &[String]) -> Role {
    match argv.get(1).map(String::as_str) {
        None => Role::Help,
        // `cargo sensorium test …` reaches us as
        // `cargo-sensorium sensorium test …`: cargo passes its subcommand word
        // through, so everything after it is ours for certain and an unknown
        // word is a mistyped subcommand rather than a compiler.
        Some("sensorium") => match argv.get(2).map(String::as_str) {
            None => Role::Help,
            Some("--runner") => Role::Runner(argv[3..].to_vec()),
            Some(_) => Role::Driver(argv[2..].to_vec()),
        },
        Some("--runner") => Role::Runner(argv[2..].to_vec()),
        Some(a) if a == "test" || a == "run" || a.starts_with('-') => {
            Role::Driver(argv[1..].to_vec())
        }
        // Cargo invokes a workspace wrapper with the rustc it resolved, which
        // is a PATH. A bare word here is a mistyped subcommand, and saying so
        // beats trying to execute it as a compiler and reporting whatever the
        // shell says about it.
        Some(rustc) if rustc.contains('/') => Role::Wrapper {
            rustc: rustc.to_owned(),
            args: argv[2..].to_vec(),
        },
        Some(_) => Role::Driver(argv[1..].to_vec()),
    }
}

/// What a rustc argv says about the unit being compiled.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct UnitArgs {
    pub crate_name: Option<String>,
    pub crate_types: Vec<String>,
    /// The `-C metadata=<hash>` value: the manifest's key and the unit's
    /// identity everywhere downstream (spec §2.4).
    pub metadata: Option<String>,
    /// Every positional argument, in order. The crate root is the one that
    /// ends in `.rs`.
    pub positionals: Vec<String>,
    pub is_test: bool,
    pub has_print: bool,
    pub has_version_verbose: bool,
    /// `-C panic=abort`. Decides which of the two runtime rlibs this unit links
    /// (plan decision D1). Measured on rustc 1.96: handing the ABORT runtime to
    /// a unit that is not abort is a hard error, so reading this off the argv
    /// is what keeps the abort variant where it belongs.
    pub panic_abort: bool,
    /// A `-C lto` that is actually on. LTO cannot consume a plain rlib built
    /// outside the build graph, so such a unit falls back (D1).
    pub lto: bool,
    /// `--target <triple>`: the runtime rlib is built for the host only.
    pub cross_target: bool,
}

/// The identity of one unit, as the manifest records it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Unit {
    pub crate_name: String,
    pub crate_type: String,
    pub metadata: String,
    /// As cargo wrote it. Relative to cargo's cwd for a workspace member, which
    /// is what the mirror needs; an absolute one is a fallback reason.
    pub crate_root: String,
    pub panic_abort: bool,
}

/// The wrapper's decision for one unit.
#[derive(Debug, PartialEq, Eq)]
pub enum Plan {
    /// Run rustc unchanged and record NOTHING. Not a unit this recorder has
    /// anything to say about: cargo's own probes, build scripts, proc macros.
    PassThrough(&'static str),
    /// Run rustc unchanged and record that we did: a unit this recorder would
    /// have instrumented and deliberately did not. The reason reaches the trace
    /// through the manifest's `fallback_reason` (`rust/HONESTY.md` §8 item 7).
    Fallback(Unit, &'static str),
    /// Mirror, splice, and compile from the mirror.
    Instrument(Unit),
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

/// Split a rustc argv into what the wrapper needs. `args` is what rustc itself
/// would see: it excludes both our own `argv[0]` and the rustc path.
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
            // A valueless short or compound flag: `-vV`, `-g`.
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
        ("--target", Some(_)) => out.cross_target = true,
        ("-C" | "--codegen", Some(v)) => codegen(out, v),
        ("--print", _) => out.has_print = true,
        ("--test", _) => out.is_test = true,
        ("-vV", _) => out.has_version_verbose = true,
        _ => {}
    }
}

/// One `-C` value. `lto` may be written bare, `=on`/`=true`/`=thin`/`=fat`, or
/// switched off with `=off`/`=false` — only the last two are not LTO.
fn codegen(out: &mut UnitArgs, value: &str) {
    let (key, val) = match value.split_once('=') {
        Some((k, v)) => (k, Some(v)),
        None => (value, None),
    };
    match key {
        "metadata" => out.metadata = val.map(str::to_owned),
        "panic" => out.panic_abort = val == Some("abort"),
        "lto" => out.lto = !matches!(val, Some("off" | "false" | "no" | "n")),
        _ => {}
    }
}

/// The wrapper's decision, in the order the rules are checked.
///
/// Passthrough first: those argvs are not units at all, and several of them
/// carry no `-C metadata` to key a manifest by. Then the three fallbacks that
/// are decidable from the argv alone — `-C lto` and `--target` because the
/// runtime rlib cannot be linked into such a unit (D1), and an absolute crate
/// root because the mirror is built from workspace-relative paths.
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
    let Some(crate_name) = u.crate_name.clone() else {
        return Plan::PassThrough("no --crate-name");
    };
    if crate_name == "___" {
        return Plan::PassThrough("probe crate ___");
    }
    if crate_name.starts_with("build_script_") {
        return Plan::PassThrough("build script");
    }
    let roots: Vec<&String> = u
        .positionals
        .iter()
        .filter(|p| p.ends_with(".rs"))
        .collect();
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
    // A `--test` unit carries no `--crate-type`: cargo compiles it as a test
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
    let unit = Unit {
        crate_name,
        crate_type,
        metadata,
        crate_root: (*root).clone(),
        panic_abort: u.panic_abort,
    };
    if u.lto {
        return Plan::Fallback(unit, "lto");
    }
    if u.cross_target {
        return Plan::Fallback(unit, "cross-target");
    }
    if Path::new(&unit.crate_root).is_absolute() {
        return Plan::Fallback(unit, "absolute-crate-root");
    }
    Plan::Instrument(unit)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn v(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| (*s).to_owned()).collect()
    }

    fn unit(args: &[String]) -> Unit {
        match plan(args) {
            Plan::Instrument(u) => u,
            other => panic!("expected Instrument, got {other:?}"),
        }
    }

    /// Captured verbatim from cargo 1.96 building a workspace member with a
    /// dumping `RUSTC_WORKSPACE_WRAPPER`. If this stops parsing, cargo's
    /// wrapper contract has moved and everything downstream of it is wrong.
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
            unit(&real_lib_argv()),
            Unit {
                crate_name: "probe_core".to_owned(),
                crate_type: "lib".to_owned(),
                metadata: "a98bc0df34adbff2".to_owned(),
                crate_root: "probe-core/src/lib.rs".to_owned(),
                panic_abort: false,
            }
        );
    }

    #[test]
    fn check_cfg_values_are_not_mistaken_for_positionals() {
        // `cfg(feature, values())` follows `--check-cfg` as a SEPARATE argv
        // entry and does not start with `-`. Drop `--check-cfg` from the
        // value-flag table and this argument becomes a second crate root.
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
        assert_eq!(unit(&args).crate_type, "test");
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
        assert_eq!(unit(&args).crate_root, "real/src/lib.rs");
    }

    #[test]
    fn attached_and_separated_c_metadata_read_the_same() {
        let a = parse(&v(&["-Cmetadata=abc"]));
        let b = parse(&v(&["-C", "metadata=abc"]));
        assert_eq!(a.metadata.as_deref(), Some("abc"));
        assert_eq!(a.metadata, b.metadata);
    }

    #[test]
    fn version_verbose_passes_through() {
        assert_eq!(plan(&v(&["-vV"])), Plan::PassThrough("-vV"));
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
        let args = v(&[
            "--crate-name",
            "x",
            "x.rs",
            "--print",
            "cfg",
            "-C",
            "metadata=a",
        ]);
        assert_eq!(plan(&args), Plan::PassThrough("--print"));
    }

    /// The three argv-decidable fallbacks. Each is a unit this recorder WOULD
    /// have instrumented, so each keeps its identity and gets a manifest —
    /// findings §5.29: a fallback that reports to the log channel only is
    /// scored as instrumented by any check that reads manifests.
    #[test]
    fn an_lto_unit_falls_back_with_a_reason_and_keeps_its_identity() {
        let args = v(&[
            "--crate-name",
            "x",
            "src/lib.rs",
            "--crate-type",
            "lib",
            "-C",
            "metadata=a",
            "-C",
            "lto",
        ]);
        match plan(&args) {
            Plan::Fallback(u, reason) => {
                assert_eq!(reason, "lto");
                assert_eq!(u.metadata, "a");
                assert_eq!(u.crate_name, "x");
            }
            other => panic!("expected Fallback, got {other:?}"),
        }
    }

    #[test]
    fn lto_off_is_not_lto() {
        for form in ["lto=off", "lto=false", "lto=no"] {
            let args = v(&[
                "--crate-name",
                "x",
                "src/lib.rs",
                "--crate-type",
                "lib",
                "-C",
                "metadata=a",
                "-C",
                form,
            ]);
            assert!(
                matches!(plan(&args), Plan::Instrument(_)),
                "-C {form} must not be read as LTO"
            );
        }
    }

    #[test]
    fn lto_thin_and_fat_and_attached_are_all_lto() {
        for form in ["-Clto", "-Clto=thin", "-Clto=fat", "-Clto=true"] {
            let args = v(&[
                "--crate-name",
                "x",
                "src/lib.rs",
                "--crate-type",
                "lib",
                "-C",
                "metadata=a",
                form,
            ]);
            assert!(
                matches!(plan(&args), Plan::Fallback(_, "lto")),
                "{form} must be read as LTO"
            );
        }
    }

    #[test]
    fn a_cross_target_unit_falls_back_with_a_reason() {
        let args = v(&[
            "--crate-name",
            "x",
            "src/lib.rs",
            "--crate-type",
            "lib",
            "-C",
            "metadata=a",
            "--target",
            "aarch64-unknown-linux-gnu",
        ]);
        assert!(matches!(plan(&args), Plan::Fallback(_, "cross-target")));
    }

    #[test]
    fn an_absolute_crate_root_falls_back_with_a_reason() {
        // Cargo hands workspace members a RELATIVE root; an absolute one is not
        // the shape the mirror was designed for. Rung 1 passed this through
        // with NO manifest at all (findings §5.29) -- the one fallback that was
        // invisible to a manifest-reading coverage check.
        let args = v(&[
            "--crate-name",
            "x",
            "/elsewhere/src/lib.rs",
            "--crate-type",
            "lib",
            "-C",
            "metadata=a",
        ]);
        match plan(&args) {
            Plan::Fallback(u, reason) => {
                assert_eq!(reason, "absolute-crate-root");
                assert_eq!(u.crate_root, "/elsewhere/src/lib.rs");
            }
            other => panic!("expected Fallback, got {other:?}"),
        }
    }

    #[test]
    fn panic_abort_is_read_off_the_argv() {
        let args = v(&[
            "--crate-name",
            "x",
            "src/lib.rs",
            "--crate-type",
            "lib",
            "-C",
            "metadata=a",
            "-C",
            "panic=abort",
        ]);
        assert!(unit(&args).panic_abort);
        assert!(!unit(&real_lib_argv()).panic_abort);
    }

    #[test]
    fn role_is_the_wrapper_when_argv1_is_a_rustc_path() {
        let argv = v(&[
            "/t/shim/cargo-sensorium",
            "/home/x/.rustup/bin/rustc",
            "-vV",
        ]);
        assert_eq!(
            role(&argv),
            Role::Wrapper {
                rustc: "/home/x/.rustup/bin/rustc".to_owned(),
                args: v(&["-vV"]),
            }
        );
    }

    #[test]
    fn role_is_the_driver_for_the_cargo_subcommand_form() {
        assert_eq!(
            role(&v(&["cargo-sensorium", "sensorium", "test", "--lib"])),
            Role::Driver(v(&["test", "--lib"]))
        );
    }

    #[test]
    fn role_is_the_driver_for_the_direct_form_and_for_flags_first() {
        assert_eq!(
            role(&v(&["cargo-sensorium", "test", "--lib"])),
            Role::Driver(v(&["test", "--lib"]))
        );
        assert_eq!(
            role(&v(&["cargo-sensorium", "--tier", "off", "run"])),
            Role::Driver(v(&["--tier", "off", "run"]))
        );
    }

    #[test]
    fn role_is_the_runner_after_the_runner_marker() {
        // Cargo splits `CARGO_TARGET_<HOST>_RUNNER` on whitespace and appends
        // the binary, so this is exactly the argv cargo builds.
        assert_eq!(
            role(&v(&[
                "/t/shim/cargo-sensorium",
                "--runner",
                "/t/deps/x-1",
                "--nocapture"
            ])),
            Role::Runner(v(&["/t/deps/x-1", "--nocapture"]))
        );
    }

    #[test]
    fn the_runner_marker_beats_the_leading_dash_driver_rule() {
        // `--runner` starts with `-`, so a rule that checked the driver first
        // would run cargo instead of the test binary -- and the invocation
        // would recurse.
        assert!(matches!(
            role(&v(&["cargo-sensorium", "--runner", "/t/x"])),
            Role::Runner(_)
        ));
    }

    #[test]
    fn a_mistyped_subcommand_is_the_drivers_to_refuse_not_a_compiler_to_run() {
        // Both forms. Reading `build` as a rustc path made the binary try to
        // exec it and report the shell's "No such file or directory" instead of
        // "unknown subcommand `build`".
        assert_eq!(
            role(&v(&["cargo-sensorium", "sensorium", "build"])),
            Role::Driver(v(&["build"]))
        );
        assert_eq!(
            role(&v(&["cargo-sensorium", "build"])),
            Role::Driver(v(&["build"]))
        );
    }

    #[test]
    fn a_rustc_path_is_still_the_wrapper_in_both_spellings() {
        // Cargo hands a workspace wrapper the rustc it resolved, and that is a
        // path. Relative counts.
        for path in ["/usr/bin/rustc", "./rustc", "../toolchain/bin/rustc"] {
            assert_eq!(
                role(&v(&["cargo-sensorium", path, "-vV"])),
                Role::Wrapper {
                    rustc: path.to_owned(),
                    args: v(&["-vV"]),
                },
                "{path}"
            );
        }
    }

    #[test]
    fn no_arguments_at_all_is_help() {
        assert_eq!(role(&v(&["cargo-sensorium"])), Role::Help);
        assert_eq!(role(&v(&["cargo-sensorium", "sensorium"])), Role::Help);
    }
}
