//! Assembling one process's `meta` rows. Pure: takes everything the rest of
//! `convert` learned, in a plain struct, and returns the ordered list of
//! `(key, value)` pairs [`crate::convert::mod`] writes -- `trace_format` and
//! `incomplete` are NOT here, because their ordering (`trace_format` first,
//! `incomplete = true` before any row, `false` only after every other write)
//! spans the whole trace, not just its meta.

use std::collections::BTreeMap;

use serde_json::{json, Map, Value};

/// The fixed declaration every trace this recorder writes carries. `line`,
/// `locals`, `stdin`, `output`, `object_identity` and `refocus` are `false` at
/// this rung; `return_value`, `tasks` and `threads` are witnessed.
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
    ("refocus", false),
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
    pub pid: u32,
    pub ppid: u32,
    pub exe: &'a str,
    pub toolchain: &'a str,
    pub rustc_path: &'a str,
    pub cargo_args: &'a [String],
    pub profile: &'a str,
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
        ("capabilities", capabilities_json(m.err_flow_capability)),
        ("threads_started", json!(m.threads_started)),
        ("live_threads", json!(m.live_threads)),
        ("env", json!(m.env)),
        ("caps", json!({"repr": 200})),
        ("invocation", json!(m.invocation)),
        ("pid", json!(m.pid)),
        ("ppid", json!(m.ppid)),
        ("exe", json!(m.exe)),
        ("toolchain", json!(m.toolchain)),
        ("rustc_path", json!(m.rustc_path)),
        ("cargo_args", json!(m.cargo_args)),
        ("profile", json!(m.profile)),
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
    out
}

/// The shared declaration, plus the Rust-only `err_flow` the RUNTIME declared
/// (design R9). `err_flow` is not in [`CAPABILITIES`] because that list is the
/// column Python's `boot.CAPABILITIES` also answers, and this key belongs to
/// neither: it is the runtime's own statement that its records carry err flow,
/// and a converter that wrote `true` on its own authority would be declaring a
/// capability for a spool set that has none.
fn capabilities_json(err_flow: bool) -> Value {
    let mut obj = Map::new();
    for (k, v) in CAPABILITIES {
        obj.insert((*k).to_owned(), json!(v));
    }
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
            pid: 1,
            ppid: 0,
            exe: "/w/target/x",
            toolchain: "rustc 1.96.0",
            rustc_path: "/u/bin/rustc",
            cargo_args: &[],
            profile: "dev",
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
                "object_identity": false, "refocus": false, "err_flow": false
            })
        );
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
