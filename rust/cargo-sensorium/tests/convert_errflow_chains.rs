//! §2a's chain machine through the REAL binary: hand-built spools whose
//! CONVERTED events carry the serial, hop, origin, `translated` label and
//! terminal the design's table calls for.
//!
//! The machine itself is pinned as a pure function next to it
//! (`src/convert/chains/tests.rs`, one test per row). This file is the other
//! half the design's §2a closing line asks for -- the same shapes as SPOOLS, so
//! that the parse, the pre-pass, the writer and the machine are pinned
//! together rather than one at a time.

mod common;

use common::spooldir::{
    events, meta, Fixture, HOW_ARM_PROPAGATE, HOW_SINK_OK, HOW_TRY, KIND_HANDLED, KIND_RAISE,
};
use common::wire::{self, err_site, marked_site, site};

/// Every RAISE/HANDLED payload in `events.id` order, for the assertions that
/// are about a chain rather than about one event.
fn chain_events(conn: &rusqlite::Connection) -> Vec<serde_json::Value> {
    events(conn)
        .into_iter()
        .filter(|(k, _, _)| k == "RAISE" || k == "HANDLED")
        .map(|(_, _, p)| p)
        .collect()
}

/// Design R8: a chain whose recorded type changes on the way out is ONE chain,
/// each hop printing its own type, and the change is labelled. The synthesised
/// origin RAISE at the translating frame's exit carries the NEW type -- the
/// chain's birth type is what `chain.serial` already ties it to.
#[test]
fn a_hop_that_changes_the_error_type_is_the_same_chain_labelled_translated() {
    let f = Fixture::new("errflow-translated");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "inner", 10, "value"),
        err_site(2, "outer", 8, "arm", "arm_propagate"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        616,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(616, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .err_flow(
            3,
            1300,
            0,
            2,
            KIND_RAISE,
            HOW_ARM_PROPAGATE,
            Some("demo::E"),
            Some("E1"),
        )
        .ret_err_typed(4, 1400, 0, 0, Some("demo::AppError"), Some("Err(Wrapped)"))
        .thread_end(5, 1500)
        .write(&f.spool_dir);
    let rows = events(&f.converted());
    let raises: Vec<&serde_json::Value> = rows
        .iter()
        .filter(|(k, _, _)| k == "RAISE")
        .map(|(_, _, p)| p)
        .collect();
    assert_eq!(raises.len(), 3, "origin, arm, and the translating exit");
    let serial = raises[0]["exc"]["serial"].clone();
    assert!(
        raises.iter().all(|r| r["exc"]["serial"] == serial),
        "one chain across the translation: {raises:#?}"
    );
    assert_eq!(raises[0]["exc"]["type"], serde_json::json!("demo::E"));
    assert_eq!(raises[1]["chain"]["hop"], serde_json::json!(2));
    assert_eq!(
        raises[2]["exc"]["type"],
        serde_json::json!("demo::AppError"),
        "each hop prints the type IT recorded"
    );
    assert_eq!(raises[2]["exc"]["msg"], serde_json::json!("Wrapped"));
    assert_eq!(raises[2]["chain"]["translated"], serde_json::json!(true));
    assert_eq!(raises[2]["chain"]["hop"], serde_json::json!(3));
    assert_eq!(raises[0]["chain"]["translated"], serde_json::json!(false));
}

/// A chain left open on a `#[test]` fn went back to the harness (design R8),
/// and that is the fact the trace carries.
#[test]
fn a_chain_that_left_a_test_fn_is_recorded_as_returned_to_the_harness() {
    let f = Fixture::new("errflow-returned-to-harness");
    f.manifest(&[
        marked_site(0, "tests::t", 3, "value", true, false),
        site(1, "inner", 10, "value"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        611,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(611, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .ret_err_typed(3, 1300, 0, 0, Some("demo::E"), Some("Err(E1)"))
        .thread_end(4, 1400)
        .write(&f.spool_dir);
    let rows = events(&f.converted());
    let last_raise = rows
        .iter()
        .rfind(|(k, _, _)| k == "RAISE")
        .expect("two RAISEs");
    assert_eq!(
        last_raise.2["chain"]["terminal"],
        serde_json::json!("returned_to_harness")
    );
    assert_eq!(last_raise.2["chain"]["hop"], serde_json::json!(2));
}

/// The same chain on a SPAWNED thread went into a `JoinHandle` instead
/// (design R8): the thread it ran on is the only fact outside the record
/// stream that tells the two apart.
#[test]
fn a_chain_that_left_a_spawned_threads_outermost_frame_is_recorded_as_left_thread() {
    let f = Fixture::new("errflow-left-thread");
    f.manifest(&[site(0, "worker", 3, "value"), site(1, "inner", 10, "value")]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        615,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    // The main thread does nothing; thread 2 is the spawned one.
    wire::SpoolBuilder::new(615, 1, "main")
        .version(3)
        .thread_end(0, 900)
        .write(&f.spool_dir);
    wire::SpoolBuilder::new(615, 2, "worker")
        .version(3)
        .call(1, 1000, 0, 0)
        .call(2, 1100, 0, 1)
        .ret_err_typed(3, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .ret_err_typed(4, 1300, 0, 0, Some("demo::E"), Some("Err(E1)"))
        .thread_end(5, 1400)
        .write(&f.spool_dir);
    let rows = events(&f.converted());
    let last_raise = rows
        .iter()
        .rfind(|(k, _, _)| k == "RAISE")
        .expect("two RAISEs");
    assert_eq!(
        last_raise.2["chain"]["terminal"],
        serde_json::json!("left_thread")
    );
}

/// §2a row 1, `Open(c)` with a DIFFERENT text -- the `interleaved_chains`
/// shape, as a SPOOL. Two `Err`s alive in one frame's window are two serials in
/// a merged window, and every member of it ends `merged`: never a swallow, which
/// is the false accusation design R8 closes here.
#[test]
fn two_errs_in_one_frames_window_convert_to_two_merged_chains() {
    let f = Fixture::new("errflow-chains-merged");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "inner", 10, "value"),
        err_site(2, "outer", 5, "try", "try"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        620,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(620, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        // The first `Err` is born by `inner` returning it, and now sits in `outer`.
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        // A SECOND, different `Err` is raised in the same window.
        .err_flow(
            3,
            1300,
            0,
            2,
            KIND_RAISE,
            HOW_TRY,
            Some("demo::E"),
            Some("E2"),
        )
        .ret_ok_dbg(4, 1400, 0, 0, "Ok(())", false)
        .thread_end(5, 1500)
        .write(&f.spool_dir);
    let conn = f.converted();
    let raises = chain_events(&conn);

    assert_eq!(raises.len(), 2, "{raises:#?}");
    let a = &raises[0]["chain"];
    let b = &raises[1]["chain"];
    assert_ne!(a["serial"], b["serial"], "two Errs are two serials");
    assert_eq!(b["serial"], serde_json::json!((1_u64 << 32) + 1));
    assert_eq!(a["hop"], serde_json::json!(1));
    assert_eq!(b["hop"], serde_json::json!(1), "a member, not a hop");
    assert_eq!(a["terminal"], serde_json::json!("merged"));
    assert_eq!(b["terminal"], serde_json::json!("merged"));
    assert!(
        !raises
            .iter()
            .any(|r| r["chain"]["terminal"] == "swallowed_candidate"),
        "a merged window is never a swallow: {raises:#?}"
    );
}

/// §2a row 1, `None` in a CALLEE: a callee raising its own `Err` while an outer
/// chain is in flight opens a NESTED chain (the stack), never a merge -- and
/// each keeps its own type, its own hops and its own end.
#[test]
fn a_callee_raising_its_own_err_converts_to_a_second_stacked_chain() {
    let f = Fixture::new("errflow-chains-nested");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "first", 10, "value"),
        site(2, "second", 20, "value"),
        err_site(3, "second", 21, "try", "try"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        621,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(621, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        // Chain A is born in `first` and comes to rest in `outer`.
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .call(3, 1300, 0, 2)
        // Chain B is raised inside `second`, which holds no chain of its own.
        .err_flow(
            4,
            1400,
            0,
            3,
            KIND_RAISE,
            HOW_TRY,
            Some("demo::Other"),
            Some("E2"),
        )
        // `second` returns by the `?` bypass, so B changes hands to `outer`
        // -- which now holds BOTH, innermost last.
        .ret_none(5, 1500, 0, 2)
        .ret_ok_dbg(6, 1600, 0, 0, "Ok(())", false)
        .thread_end(7, 1700)
        .write(&f.spool_dir);
    let rows = chain_events(&f.converted());

    assert_eq!(rows.len(), 2, "{rows:#?}");
    let (a, b) = (&rows[0]["chain"], &rows[1]["chain"]);
    assert_ne!(a["serial"], b["serial"], "the nested chain is its own");
    assert_eq!(b["serial"], serde_json::json!((1_u64 << 32) + 1));
    assert_eq!(b["hop"], serde_json::json!(1), "born in the callee");
    for chain in [a, b] {
        assert_ne!(
            chain["terminal"],
            serde_json::json!("merged"),
            "a nested chain is never merged with the one in flight: {rows:#?}"
        );
        assert_eq!(
            chain["terminal"],
            serde_json::json!("ambiguous_escaped"),
            "each ends where its holder returned ok with no sink: {rows:#?}"
        );
    }
    assert_eq!(rows[0]["exc"]["type"], serde_json::json!("demo::E"));
    assert_eq!(
        rows[1]["exc"]["type"],
        serde_json::json!("demo::Other"),
        "each chain keeps the type it was born with"
    );
}

/// The other half of the stack: when a frame holds an older chain AND a nested
/// one, a sink absorbs the chain whose `Err` it NAMES. Reading only the
/// innermost would report this as a chainless swallow of an `Err` "born outside
/// instrumented code" (design R8) -- a claim about a value this recording
/// watched `first` produce.
#[test]
fn a_sink_absorbs_the_held_chain_it_names_over_the_nested_one() {
    let f = Fixture::new("errflow-chains-nested-sink");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "first", 10, "value"),
        site(2, "second", 20, "value"),
        err_site(3, "second", 21, "try", "try"),
        err_site(4, "outer", 6, "sink", "sink_ok"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        625,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(625, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        // Chain A is born in `first` and comes to rest in `outer`.
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .call(3, 1300, 0, 2)
        // Chain B is raised in `second` and hops up into `outer` on top of A.
        .err_flow(
            4,
            1400,
            0,
            3,
            KIND_RAISE,
            HOW_TRY,
            Some("demo::Other"),
            Some("E2"),
        )
        .ret_none(5, 1500, 0, 2)
        // The sink names A's `Err`, not the one on top.
        .err_flow(
            6,
            1600,
            0,
            4,
            KIND_HANDLED,
            HOW_SINK_OK,
            Some("demo::E"),
            Some("E1"),
        )
        .ret_ok_dbg(7, 1700, 0, 0, "Ok(())", false)
        .thread_end(8, 1800)
        .write(&f.spool_dir);
    let rows = chain_events(&f.converted());

    assert_eq!(rows.len(), 3, "{rows:#?}");
    let (a_origin, nested, sink) = (&rows[0], &rows[1], &rows[2]);
    assert_eq!(
        sink["chain"]["serial"], a_origin["chain"]["serial"],
        "the sink absorbed the chain it named: {rows:#?}"
    );
    assert_ne!(nested["chain"]["serial"], a_origin["chain"]["serial"]);
    assert_eq!(
        sink["chain"]["terminal"],
        serde_json::json!("swallowed_candidate")
    );
    assert_eq!(
        sink["chain"]["origin"],
        serde_json::json!("workspace"),
        "the Err was made in `first`, which this recording watched: {rows:#?}"
    );
    assert_eq!(
        nested["chain"]["terminal"],
        serde_json::json!("ambiguous_escaped"),
        "the nested chain was never absorbed"
    );
}

/// §2a row 1, `None` column: a `?` in a frame that holds no chain OPENS one,
/// born at an instrumented site -- `workspace`, never `outside`. (`outside` is
/// a HANDLED with nothing to continue and nothing else: design R8's "born in
/// dependency code", which is a claim about where the `Err` was MADE.)
#[test]
fn a_try_with_no_open_chain_converts_to_a_workspace_chain() {
    let f = Fixture::new("errflow-chains-workspace-origin");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        err_site(1, "outer", 5, "try", "try"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        622,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(622, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .err_flow(
            1,
            1100,
            0,
            1,
            KIND_RAISE,
            HOW_TRY,
            Some("io::Error"),
            Some("ENOENT"),
        )
        .ret_none(2, 1200, 0, 0)
        .thread_end(3, 1300)
        .write(&f.spool_dir);
    let rows = chain_events(&f.converted());
    assert_eq!(rows.len(), 1, "{rows:#?}");
    assert_eq!(
        rows[0]["chain"]["origin"],
        serde_json::json!("workspace"),
        "a `?` is an instrumented site: the Err was raised where this recording \
         could see it"
    );
    assert_eq!(rows[0]["chain"]["hop"], serde_json::json!(1));
    assert_eq!(rows[0]["exc"]["type"], serde_json::json!("io::Error"));
}

/// §2a row 8 judges the frame the chain SITS in. On an INCOMPLETE thread that
/// frame never closed, and judging the frame the chain last LEFT instead would
/// report a `#[test]` fn that was still running as a propagation -- the
/// disposition R8 reserves for a thread whose frames were not all instrumented.
#[test]
fn a_chain_still_inside_an_unclosed_test_frame_returned_to_the_harness() {
    let f = Fixture::new("errflow-chains-incomplete");
    f.manifest(&[
        marked_site(0, "tests::t", 3, "value", true, false),
        site(1, "inner", 10, "value"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        623,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    // No RETURN for the test frame and no THREAD_END: the recording stops
    // inside it, which is what an INCOMPLETE trace looks like.
    wire::SpoolBuilder::new(623, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(E1)"))
        .write(&f.spool_dir);
    // ONE conversion: each call mints a new run id and writes another trace.
    let conn = f.converted();
    let rows = chain_events(&conn);
    assert_eq!(rows.len(), 1, "{rows:#?}");
    assert_eq!(
        rows[0]["chain"]["terminal"],
        serde_json::json!("returned_to_harness"),
        "the holder is the test frame, which never closed: {rows:#?}"
    );
    assert_eq!(
        meta(&conn, "live_threads"),
        serde_json::json!(["main"]),
        "and the trace says the thread never ended, so a reader is not \
         reading this as a complete recording"
    );
}

/// Design B3 (2026-09-05): a frame closing `err` while holding two chains
/// hands the exit hop to the chain whose text the RETURN carries.
#[test]
fn an_err_close_holding_two_chains_hops_the_one_whose_text_it_returns() {
    let f = Fixture::new("errflow-chains-keep-first-error");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "first", 10, "value"),
        site(2, "second", 20, "value"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        626,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(626, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(B1)"))
        .call(3, 1300, 0, 2)
        .ret_err_typed(4, 1400, 0, 2, Some("demo::E"), Some("Err(C1)"))
        // `outer` returns the FIRST error while holding both chains.
        .ret_err_typed(5, 1500, 0, 0, Some("demo::E"), Some("Err(B1)"))
        .thread_end(6, 1600)
        .write(&f.spool_dir);
    let rows = chain_events(&f.converted());

    let b1 = rows[0]["chain"]["serial"].clone();
    let exits: Vec<_> = rows
        .iter()
        .filter(|r| r["chain"]["hop"] == serde_json::json!(2))
        .collect();
    assert_eq!(exits.len(), 1, "one exit hop: {rows:#?}");
    assert_eq!(
        exits[0]["chain"]["serial"], b1,
        "the hop is the first error's: {rows:#?}"
    );
    assert_eq!(exits[0]["chain"]["translated"], serde_json::json!(false));
}

/// A cut `Debug` rendering has no closing `)` left. `exc.msg` still means the
/// ERROR's own text -- the `Result`'s wrapper was never part of it -- and
/// `trunc` is what says the text is short.
#[test]
fn a_cut_exit_rendering_still_reports_the_errors_own_message() {
    let f = Fixture::new("errflow-chains-cut-text");
    f.manifest(&[site(0, "outer", 3, "value")]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        624,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(624, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .ret_err_typed_cut(1, 1100, 0, 0, "demo::E", "Err(Boom { detail: \"aaa")
        .thread_end(2, 1200)
        .write(&f.spool_dir);
    let rows = chain_events(&f.converted());
    assert_eq!(rows.len(), 1, "{rows:#?}");
    assert_eq!(
        rows[0]["exc"]["msg"],
        serde_json::json!("Boom { detail: \"aaa"),
        "the wrapper goes even when the text was cut: {rows:#?}"
    );
    assert_eq!(rows[0]["exc"]["trunc"], serde_json::json!(true));
    assert_eq!(rows[0]["exc"]["type"], serde_json::json!("demo::E"));
}
