//! Assembling one process's `meta` rows. Pure: takes everything the rest of
//! `convert` learned, in a plain struct, and returns the ordered list of
//! `(key, value)` pairs [`crate::convert::mod`] writes -- `trace_format` and
//! `incomplete` are NOT here, because their ordering (`trace_format` first,
//! `incomplete = true` before any row, `false` only after every other write)
//! spans the whole trace, not just its meta.

use std::collections::BTreeMap;

use serde_json::{json, Map, Value};

use crate::convert::manifest::FocusRecord;

/// The declaration every trace this recorder writes carries. `stdin`,
/// `output` and `object_identity` are `false` at this rung; `return_value`,
/// `tasks`, `threads` and `refocus` are witnessed.
///
/// `refocus` is `true` UNCONDITIONALLY (design 2026-09-07 §2.2): it says the
/// recorder can be re-invoked, which is a fact about this driver and not
/// about one trace. Whether one particular trace can be refocused -- one
/// binary of several, a workspace since deleted -- is a refusal `refocus`
/// itself makes, with a sentence naming what is wrong, and a capability
/// that answered it would say only "no".
///
/// `line` and `locals` are `false` HERE and computed per run by
/// [`capabilities_json`]: they are true exactly when some unit of the run
/// carries a `line` site, which is a fact about the manifests, never about
/// whether a `--focus` was typed (design 2026-09-06 §2.4).
pub const CAPABILITIES: &[(&str, bool)] = &[
    ("line", false),
    ("locals", false),
    ("return_value", true),
    ("tasks", true),
    ("threads", true),
    ("children", false),
    ("stdin", false),
    ("output", false),
    ("object_identity", false),
    ("refocus", true),
];

/// Everything [`build`] needs, gathered by `mod.rs` from `invocation.json`,
/// the proc header, the runner record (when present), the manifests this
/// process registered, and the frame walk's own counters.
pub struct MetaInput<'a> {
    pub run_id: &'a str,
    pub argv: &'a [String],
    pub cwd: &'a str,
    pub env_hash: &'a str,
    pub start_ts: f64,
    pub end_ts: f64,
    pub exit_status: Option<i32>,
    pub truncated_count: u64,
    pub source_hashes: &'a BTreeMap<String, String>,
    pub recorder: &'a str,
    pub threads_started: usize,
    pub live_threads: &'a [String],
    pub env: &'a BTreeMap<String, String>,
    pub invocation: &'a str,
    /// Runner processes -- test binaries AND doctests; a single-target
    /// selector makes it 1. It is the count the driver already prints its
    /// multi-binary WARN from, which is `runner_records.len()`: cargo 1.96
    /// hands the target runner every test binary and every doctest process
    /// (`runner.rs`, `rust/HONESTY.md` §"the runner started this process",
    /// measured 2026-09-02), so a `cargo test` with doctests counts more
    /// than its test binaries. Written on every trace of the invocation, so
    /// a reader of ONE trace can tell whether it is the whole answer (design
    /// 2026-09-07 §2.2, B2); `refocus` refuses a re-run when it is not 1.
    pub invocation_processes: usize,
    /// The run id this invocation was a re-run OF, from `invocation.json`.
    /// `None` for an ordinary run, and then the key is ABSENT: `refocus`'s
    /// pair lookup asks which traces carry it, and a null would be a link to
    /// nothing.
    pub refocus_of: Option<&'a str>,
    pub pid: u32,
    pub ppid: u32,
    pub exe: &'a str,
    pub toolchain: &'a str,
    pub rustc_path: &'a str,
    pub cargo_args: &'a [String],
    pub profile: &'a str,
    /// The workspace this invocation ran in, from `invocation.json`. Only
    /// the invocation record knows it, and `refocus` re-runs the driver FROM
    /// it -- a trace that did not record it cannot be re-run at all.
    pub workspace_root: &'a str,
    pub tool_hash: &'a str,
    pub driver_version: &'a str,
    pub instrumented_units: &'a [String],
    pub uninstrumented: &'a [Value],
    /// Manifests under `<target>/sensorium/manifests/` with no
    /// `workspace_root` at all -- pre-fix manifests, counted rather than
    /// silently excluded from `uninstrumented`/`skipped`/`spawns`/
    /// `unreached_files` (a shared `CARGO_TARGET_DIR` can hold several
    /// workspaces' manifests, and this is the fact that a foreign one is
    /// missing the field to compare rather than merely not matching).
    pub manifests_unscoped: usize,
    pub skipped: &'a [Value],
    /// Err-flow sites the transformer could not reach (design R6), from the
    /// manifests of the units THIS process registered -- scoped exactly as
    /// `skipped` is, and for the same reason.
    pub partial: &'a [Value],
    /// One row per site of those units: `{unit, site, file, qualname, kind,
    /// line, how?, test, main}`. The `exceptions` reader needs `test`/`main`
    /// to say that a chain which left a frame went back to the harness rather
    /// than being lost (design R8), and there is nowhere else in a trace those
    /// marks could come from.
    pub sites: &'a [Value],
    pub spawns: &'a [Value],
    pub unreached_files: &'a [String],
    pub refused_at: Option<&'a str>,
    pub exit_status_basis: &'a str,
    pub exit_signal: Option<i32>,
    /// `(wall_start_ts, wall_end_ts)`, only when the runner ran this pid.
    pub wall: Option<(f64, f64)>,
    /// Non-zero `records_dropped` only, keyed by thread serial.
    pub records_dropped: &'a BTreeMap<u32, u64>,
    pub seq_gaps: u64,
    pub panics_unrecorded: u64,
    pub panics_outside_frames: u64,
    /// RAISE and HANDLED RECORDS on the wire, which is not the number of
    /// events: a record with no open frame is counted here and written as no
    /// event, and the origin RAISE the converter synthesises is an event that
    /// was never a record.
    pub err_flow_raise: u64,
    pub err_flow_handled: u64,
    pub err_flow_outside_frames: u64,
    pub closure_frames: u64,
    /// What the RUNTIME declared in the proc header (design R9). Passed
    /// through, never assumed: a rung-2 spool set declares nothing, and its
    /// trace must say so rather than claim a capability its records cannot
    /// support.
    pub err_flow_capability: bool,
    /// The focus this BUILD was made under: `values` as the invocation gave
    /// them (every unit of one invocation carries the same list) and `matched`
    /// the sorted union of what each unit actually focused. `None` when no
    /// manifest carried the record -- an unfocused build, or one whose
    /// transformer predates the key -- and then `focus`/`focus_matched` are
    /// ABSENT from the trace, which is a different fact from a focus that
    /// selected nothing.
    ///
    /// **Build-scoped** (ruling R-F10): the union runs over every manifest of
    /// this invocation, not just the units this process registered, because
    /// `focus_matched` answers "did this value select anything in the
    /// workspace?" -- a question about the compile. A value that matched a
    /// function in a linked unit whose code never ran did match, and a
    /// registered-scoped union would report it as `[]`, indistinguishable from
    /// a value that matched nowhere.
    pub focus: Option<&'a FocusRecord>,
    /// `line` sites in the manifests of the units this process REGISTERED --
    /// the narrower scope, deliberately (ruling R-F10). The ONLY basis for
    /// `capabilities.line`/`locals`: a focus that matched nothing produces no
    /// LINE record, so declaring the capability from the flag would promise a
    /// reader rows that cannot exist, and a LINE record can only arrive from a
    /// unit this process linked, so a non-registered unit's `line` sites
    /// promise nothing either.
    pub line_sites: usize,
    /// `{run_id, pid, exe}` for a same-invocation process whose `ppid` is
    /// this one.
    pub child_runs: &'a [Value],
}

/// In the order `db.REQUIRED_META` reports a missing key, then the witness
/// keys, then the optional shared keys, then the Rust-only ones. Order has no
/// effect on the trace itself (`meta` has no ordering); it exists so a diff of
/// two traces' meta dumps lines up key for key.
#[must_use]
pub fn build(m: &MetaInput) -> Vec<(&'static str, Value)> {
    let mut out = vec![
        ("run_id", json!(m.run_id)),
        ("argv", json!(m.argv)),
        ("cwd", json!(m.cwd)),
        ("env_hash", json!(m.env_hash)),
        ("start_ts", json!(m.start_ts)),
        ("end_ts", json!(m.end_ts)),
        ("exit_status", json!(m.exit_status)),
        ("main_thread_ident", json!(1)),
        ("fingerprint_basis", json!("per-task")),
        ("truncated_count", json!(m.truncated_count)),
        ("source_hashes", json!(m.source_hashes)),
        ("recorder", json!(m.recorder)),
        ("lang", json!("rust")),
        (
            "capabilities",
            capabilities_json(m.err_flow_capability, m.line_sites > 0),
        ),
        ("threads_started", json!(m.threads_started)),
        ("live_threads", json!(m.live_threads)),
        ("env", json!(m.env)),
        ("caps", json!({"repr": 200})),
        ("invocation", json!(m.invocation)),
        ("invocation_processes", json!(m.invocation_processes)),
        ("pid", json!(m.pid)),
        ("ppid", json!(m.ppid)),
        ("exe", json!(m.exe)),
        ("toolchain", json!(m.toolchain)),
        ("rustc_path", json!(m.rustc_path)),
        ("cargo_args", json!(m.cargo_args)),
        ("profile", json!(m.profile)),
        ("workspace_root", json!(m.workspace_root)),
        ("tool_hash", json!(m.tool_hash)),
        ("driver_version", json!(m.driver_version)),
        ("instrumented_units", json!(m.instrumented_units)),
        ("uninstrumented", json!(m.uninstrumented)),
        ("manifests_unscoped", json!(m.manifests_unscoped)),
        ("skipped", json!(m.skipped)),
        ("partial", json!(m.partial)),
        ("sites", json!(m.sites)),
        ("spawns", json!(m.spawns)),
        ("unreached_files", json!(m.unreached_files)),
        (
            "units_refused",
            json!({"refused": m.refused_at.is_some(), "at": m.refused_at}),
        ),
        ("exit_status_basis", json!(m.exit_status_basis)),
        ("exit_signal", json!(m.exit_signal)),
        ("records_dropped", records_dropped_json(m.records_dropped)),
        ("seq_gaps", json!(m.seq_gaps)),
        ("panics_unrecorded", json!(m.panics_unrecorded)),
        ("panics_outside_frames", json!(m.panics_outside_frames)),
        (
            "err_flow_records",
            json!({"raise": m.err_flow_raise, "handled": m.err_flow_handled}),
        ),
        ("err_flow_outside_frames", json!(m.err_flow_outside_frames)),
        ("closure_frames", json!(m.closure_frames)),
        ("child_runs", json!(m.child_runs)),
    ];
    if let Some((start, end)) = m.wall {
        out.push(("wall_start_ts", json!(start)));
        out.push(("wall_end_ts", json!(end)));
    }
    // Only when there was one, and never as a null: `refocus` finds the new
    // trace of a re-run by asking the store which traces carry this key, and
    // a null on every ordinary trace would make every ordinary trace an
    // answer to that question.
    if let Some(original) = m.refocus_of {
        out.push(("refocus_of", json!(original)));
    }
    // Both keys or neither, and only when a manifest carried the record: an
    // unfocused build says nothing, exactly as a Python run with no `--focus`
    // writes no `focus` beyond the empty list `boot.py` gives it. Absent and
    // empty are different facts here -- `focus: []` would say "a focus was
    // given and selected nothing".
    //
    // `focus_matched` is BUILD-scoped and `capabilities.line` above is
    // REGISTERED-scoped (ruling R-F10), so the two can honestly disagree: a
    // trace may say a value matched `Counter::bump` while declaring no `line`
    // capability, because the unit holding that match was linked but never
    // registered by this process and can therefore emit no LINE record.
    if let Some(focus) = m.focus {
        out.push(("focus", json!(focus.values)));
        out.push(("focus_matched", json!(focus.matched)));
    }
    out
}

/// The shared declaration, plus the Rust-only `err_flow` the RUNTIME declared
/// (design R9). `err_flow` is not in [`CAPABILITIES`] because that list is the
/// column Python's `boot.CAPABILITIES` also answers, and this key belongs to
/// neither: it is the runtime's own statement that its records carry err flow,
/// and a converter that wrote `true` on its own authority would be declaring a
/// capability for a spool set that has none.
/// `line` and `locals` ride on `has_line_sites`, which the caller counts off
/// the manifests: the same discipline `err_flow` follows one line below, for
/// the same reason -- a capability is a statement about what the RECORDS can
/// support, and a converter that declared one from an invocation's flag would
/// promise rows that do not exist.
fn capabilities_json(err_flow: bool, has_line_sites: bool) -> Value {
    let mut obj = Map::new();
    for (k, v) in CAPABILITIES {
        obj.insert((*k).to_owned(), json!(v));
    }
    obj.insert("line".to_owned(), json!(has_line_sites));
    obj.insert("locals".to_owned(), json!(has_line_sites));
    obj.insert("err_flow".to_owned(), json!(err_flow));
    Value::Object(obj)
}

fn records_dropped_json(dropped: &BTreeMap<u32, u64>) -> Value {
    let mut obj = Map::new();
    for (serial, n) in dropped {
        if *n > 0 {
            obj.insert(serial.to_string(), json!(n));
        }
    }
    Value::Object(obj)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal() -> MetaInput<'static> {
        MetaInput {
            run_id: "20260903-000000-abcdef",
            argv: &[],
            cwd: "/w",
            env_hash: "0000000000000000",
            start_ts: 1.0,
            end_ts: 2.0,
            exit_status: None,
            truncated_count: 0,
            source_hashes: Box::leak(Box::new(BTreeMap::new())),
            recorder: "sensorium-rt 0.1.0",
            threads_started: 0,
            live_threads: &[],
            env: Box::leak(Box::new(BTreeMap::new())),
            invocation: "20260903-000000-000000",
            invocation_processes: 1,
            refocus_of: None,
            pid: 1,
            ppid: 0,
            exe: "/w/target/x",
            toolchain: "rustc 1.96.0",
            rustc_path: "/u/bin/rustc",
            cargo_args: &[],
            profile: "dev",
            workspace_root: "/w",
            tool_hash: "0123456789abcdef",
            driver_version: "cargo-sensorium 0.1.0",
            instrumented_units: &[],
            uninstrumented: &[],
            manifests_unscoped: 0,
            skipped: &[],
            partial: &[],
            sites: &[],
            spawns: &[],
            unreached_files: &[],
            refused_at: None,
            exit_status_basis: "unwitnessed",
            exit_signal: None,
            wall: None,
            records_dropped: Box::leak(Box::new(BTreeMap::new())),
            seq_gaps: 0,
            panics_unrecorded: 0,
            panics_outside_frames: 0,
            err_flow_raise: 0,
            err_flow_handled: 0,
            err_flow_outside_frames: 0,
            closure_frames: 0,
            err_flow_capability: false,
            focus: None,
            line_sites: 0,
            child_runs: &[],
        }
    }

    fn as_map(pairs: &[(&'static str, Value)]) -> std::collections::HashMap<&'static str, Value> {
        pairs.iter().cloned().collect()
    }

    #[test]
    fn every_required_meta_key_is_present() {
        let out = as_map(&build(&minimal()));
        for key in [
            "run_id",
            "argv",
            "cwd",
            "env_hash",
            "start_ts",
            "end_ts",
            "exit_status",
            "main_thread_ident",
            "fingerprint_basis",
            "truncated_count",
            "source_hashes",
            "recorder",
            "lang",
            "capabilities",
        ] {
            assert!(out.contains_key(key), "missing required key {key}");
        }
    }

    #[test]
    fn the_witness_keys_for_threads_are_present() {
        let out = as_map(&build(&minimal()));
        assert!(out.contains_key("threads_started"));
        assert!(out.contains_key("live_threads"));
    }

    #[test]
    fn the_capabilities_dict_matches_the_pinned_declaration() {
        let out = as_map(&build(&minimal()));
        assert_eq!(
            out["capabilities"],
            json!({
                "line": false, "locals": false, "return_value": true, "tasks": true,
                "threads": true, "children": false, "stdin": false, "output": false,
                "object_identity": false, "refocus": true, "err_flow": false
            })
        );
    }

    /// `refocus` says the RECORDER can be re-invoked, which is true of every
    /// trace this driver converts -- unlike `line`/`locals`/`err_flow`, it is
    /// not computed from what the run happened to record.
    #[test]
    fn the_refocus_capability_is_true_on_every_trace_this_driver_writes() {
        let mut m = minimal();
        m.refocus_of = None;
        assert_eq!(as_map(&build(&m))["capabilities"]["refocus"], json!(true));
        m.refocus_of = Some("20260101-000000-aaaaaa");
        assert_eq!(as_map(&build(&m))["capabilities"]["refocus"], json!(true));
    }

    /// Absent, not null: `refocus` finds a re-run's new trace by asking which
    /// traces carry `refocus_of`, so a null on an ordinary trace would make
    /// every ordinary trace an answer.
    #[test]
    fn refocus_of_is_written_only_when_there_was_one() {
        assert!(
            !as_map(&build(&minimal())).contains_key("refocus_of"),
            "an ordinary run must carry no refocus_of key at all"
        );
        let mut m = minimal();
        m.refocus_of = Some("20260101-000000-aaaaaa");
        assert_eq!(
            as_map(&build(&m))["refocus_of"],
            json!("20260101-000000-aaaaaa")
        );
    }

    #[test]
    fn the_workspace_root_and_the_process_count_are_written_on_every_trace() {
        let mut m = minimal();
        m.invocation_processes = 3;
        let out = as_map(&build(&m));
        assert_eq!(out["workspace_root"], json!("/w"));
        assert_eq!(out["invocation_processes"], json!(3));
    }

    /// `err_flow` is the RUNTIME's declaration, passed through (design R9): a
    /// rung-2 spool set says nothing and its trace must not claim otherwise.
    #[test]
    fn the_err_flow_capability_is_the_runtimes_word_not_the_converters() {
        let mut m = minimal();
        m.err_flow_capability = true;
        let out = as_map(&build(&m));
        assert_eq!(out["capabilities"]["err_flow"], json!(true));
        assert_eq!(
            as_map(&build(&minimal()))["capabilities"]["err_flow"],
            json!(false)
        );
    }

    /// The three err-flow counters are records, not events, and each is
    /// present at zero rather than absent -- "none seen" and "not counted" are
    /// different facts.
    #[test]
    fn the_err_flow_counters_are_present_even_when_nothing_was_recorded() {
        let out = as_map(&build(&minimal()));
        assert_eq!(out["err_flow_records"], json!({"raise": 0, "handled": 0}));
        assert_eq!(out["err_flow_outside_frames"], json!(0));
        assert_eq!(out["closure_frames"], json!(0));

        let mut m = minimal();
        m.err_flow_raise = 3;
        m.err_flow_handled = 5;
        m.err_flow_outside_frames = 1;
        m.closure_frames = 2;
        let out = as_map(&build(&m));
        assert_eq!(out["err_flow_records"], json!({"raise": 3, "handled": 5}));
        assert_eq!(out["err_flow_outside_frames"], json!(1));
        assert_eq!(out["closure_frames"], json!(2));
    }

    /// `partial` rides beside `skipped`, and the site table beside both: an
    /// empty list is "the walk found none", which a missing key would not say.
    #[test]
    fn partial_and_the_site_table_are_always_present() {
        let out = as_map(&build(&minimal()));
        assert_eq!(out["partial"], json!([]));
        assert_eq!(out["sites"], json!([]));

        let mut m = minimal();
        let partial = vec![json!({"file": "a.rs", "line": 3, "qualname": "f",
                                  "kind": "try", "reason": "macro-arg"})];
        let sites = vec![
            json!({"unit": "u", "site": 0, "file": "a.rs", "qualname": "f",
                                "kind": "fn", "line": 1, "test": true, "main": false}),
        ];
        m.partial = Box::leak(Box::new(partial));
        m.sites = Box::leak(Box::new(sites));
        let out = as_map(&build(&m));
        assert_eq!(out["partial"][0]["reason"], json!("macro-arg"));
        assert_eq!(out["sites"][0]["test"], json!(true));
    }

    #[test]
    fn wall_keys_are_omitted_entirely_when_no_runner_ran_this_process() {
        let out = as_map(&build(&minimal()));
        assert!(!out.contains_key("wall_start_ts"));
        assert!(!out.contains_key("wall_end_ts"));
    }

    #[test]
    fn wall_keys_appear_together_when_the_runner_did_run() {
        let mut m = minimal();
        m.wall = Some((1.5, 2.5));
        let out = as_map(&build(&m));
        assert_eq!(out["wall_start_ts"], json!(1.5));
        assert_eq!(out["wall_end_ts"], json!(2.5));
    }

    #[test]
    fn units_refused_is_false_and_null_when_nothing_was_refused() {
        let out = as_map(&build(&minimal()));
        assert_eq!(out["units_refused"], json!({"refused": false, "at": null}));
    }

    #[test]
    fn units_refused_names_the_refused_unit_when_one_was() {
        let mut m = minimal();
        m.refused_at = Some("deadbeef");
        let out = as_map(&build(&m));
        assert_eq!(
            out["units_refused"],
            json!({"refused": true, "at": "deadbeef"})
        );
    }

    #[test]
    fn records_dropped_omits_zero_entries() {
        let mut dropped = BTreeMap::new();
        dropped.insert(2u32, 0u64);
        dropped.insert(3u32, 5u64);
        let mut m = minimal();
        m.records_dropped = Box::leak(Box::new(dropped));
        let out = as_map(&build(&m));
        assert_eq!(out["records_dropped"], json!({"3": 5}));
    }

    #[test]
    fn exit_status_is_null_when_unwitnessed() {
        let out = as_map(&build(&minimal()));
        assert_eq!(out["exit_status"], Value::Null);
        assert_eq!(out["exit_status_basis"], json!("unwitnessed"));
    }

    /// Design §2.4: `line` and `locals` are the RUNTIME's own statement, read
    /// off the manifests' `line` sites -- never off the presence of a focus.
    /// A focus that matched nothing in this run leaves both `false`, because
    /// no LINE record can exist for it.
    #[test]
    fn line_and_locals_are_true_only_where_a_line_site_exists() {
        let out = as_map(&build(&minimal()));
        assert_eq!(out["capabilities"]["line"], json!(false), "no focus at all");
        assert_eq!(out["capabilities"]["locals"], json!(false));

        let mut m = minimal();
        m.focus = Some(Box::leak(Box::new(FocusRecord {
            values: vec!["fill".to_owned()],
            matched: vec!["fill".to_owned()],
        })));
        m.line_sites = 4;
        let out = as_map(&build(&m));
        assert_eq!(out["capabilities"]["line"], json!(true));
        assert_eq!(out["capabilities"]["locals"], json!(true));

        // A focus was GIVEN and no unit of this run holds a `line` site: the
        // flag is not the capability, the sites are.
        let mut m = minimal();
        m.focus = Some(Box::leak(Box::new(FocusRecord {
            values: vec!["missing".to_owned()],
            matched: vec![],
        })));
        m.line_sites = 0;
        let out = as_map(&build(&m));
        assert_eq!(
            out["capabilities"]["line"],
            json!(false),
            "a focus that selected nothing declares no LINE capability"
        );
        assert_eq!(out["capabilities"]["locals"], json!(false));
    }

    /// `focus` and `focus_matched` are ABSENT when no unit carried the record
    /// -- an empty list would say "a focus was given and matched nothing",
    /// which is a different fact from "no focus was given".
    #[test]
    fn focus_keys_are_absent_without_a_focus_record_and_present_with_one() {
        let out = as_map(&build(&minimal()));
        assert!(!out.contains_key("focus"), "no focus, no key");
        assert!(!out.contains_key("focus_matched"));

        let mut m = minimal();
        m.focus = Some(Box::leak(Box::new(FocusRecord {
            values: vec!["fill".to_owned(), "missing".to_owned()],
            matched: vec!["Counter::bump".to_owned(), "fill".to_owned()],
        })));
        m.line_sites = 2;
        let out = as_map(&build(&m));
        assert_eq!(
            out["focus"],
            json!(["fill", "missing"]),
            "the values as given, in order"
        );
        assert_eq!(
            out["focus_matched"],
            json!(["Counter::bump", "fill"]),
            "the sorted union of the units' matches"
        );
    }

    #[test]
    fn manifests_unscoped_defaults_to_zero_and_carries_a_nonzero_count() {
        let out = as_map(&build(&minimal()));
        assert_eq!(out["manifests_unscoped"], json!(0));

        let mut m = minimal();
        m.manifests_unscoped = 3;
        let out = as_map(&build(&m));
        assert_eq!(out["manifests_unscoped"], json!(3));
    }
}
