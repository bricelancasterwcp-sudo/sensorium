//! E2's identity, measured on a real workspace: the numerator and the
//! denominator come from the same parser, per file and in aggregate.
//!
//! The measurement target is the LOCAL CLONE of bloomery pinned at
//! `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` (plan §Global Constraints).
//! `/home/brice/workspace/bloomery` itself is read-only for this plan and is
//! never the target here.
//!
//! **The clone's path comes from `SENSORIUM_BLOOMERY_CLONE` and from nowhere
//! else.** There is no default: no box path is committed (plan §Global
//! Constraints), so a run that does not set the variable measures nothing, and
//! this test's NAME is what says so on a CI row that libtest prints as `ok`
//! with the skip line captured.
//!
//! **The pins are the point.** `instrumented + async == eligible` is an
//! identity a walk that silently covered three files would also satisfy, so the
//! five numbers the plan measured -- 191 files, 2051 eligible fn items, 8
//! rewritten spawn sites, 401 `syn`-visible `?` and 1 `?` token inside a macro
//! invocation -- are asserted outright, and they are asserted only against the
//! commit they were measured on: a clone at any other HEAD skips with that
//! named reason rather than re-pinning itself.
//!
//! The second test is the CHECKED-IN INSTRUMENT's identity: `src/bin/census.rs`
//! is what an acceptance record's E2″ denominator is produced by, so its rows
//! are compared field for field against a direct [`census`] call on the same
//! file. It is the only thing here that starts a subprocess.
//!
//! Neither test writes: they open files for reading, create no directory, write
//! no file, and never touch `Cargo.lock` or the target tree.
//!
//! Run with `-- --nocapture` to see the numbers.

mod common;

use std::fs;
use std::path::{Path, PathBuf};

use sensorium_transform::{census, transform, SiteKind};

const META: &str = "b100meryb100mery";

/// The environment variable that names the clone, and the only way to name it.
const CLONE_VAR: &str = "SENSORIUM_BLOOMERY_CLONE";

/// The commit the five pins below were measured on. A clone at any other HEAD
/// is a different measurement, and these tests skip rather than assert someone
/// else's numbers against it.
const PINNED_COMMIT: &str = "e209ed9b00f7eef647fb31d0b0895a5ad3b90807";

/// What the plan measured at [`PINNED_COMMIT`], asserted rather than printed.
const PINNED_FILES: usize = 191;
const PINNED_ELIGIBLE: usize = 2051;
const PINNED_SPAWNS_WRAPPED: usize = 8;
/// E2″'s denominator, measured before rung 3's pre-registration was byte-locked:
/// every `?` `syn` gives an [`syn::ExprTry`] node for.
const PINNED_TRY_SYN: usize = 401;
/// And the blind spot beside it: `?` tokens inside macro invocations, which no
/// AST node exists for. One, at `crates/bloomery-bench/src/main.rs:108` -- the
/// last token of a `println!` argument. Reported, never subtracted.
const PINNED_TRY_MACRO: usize = 1;

/// What rung 3 pins beside them: every `?` `syn` sees is WRAPPED, and the one
/// `?` token inside a macro invocation is DECLARED. The identity that makes
/// E2's `?` ratio a ratio over ONE set is `try rows == try_syn` per file, with
/// any `?` the transformer had to decline subtracted by name -- and on this
/// tree there are none, which is the third pin.
const PINNED_PARTIAL_STRUCT_LITERAL: usize = 0;

/// Every written sink on this tree is wrapped, and none is declined. Before the
/// R2 erratum of 2026-09-04 this read 291 wrapped and 11 declined
/// (`sink-place`); the eleven were place-expression receivers of by-value
/// sinks, which move exactly as the wrap does.
const PINNED_SINKS_WRAPPED: usize = 302;

/// The spawn spelling `spawns[..].wrapped` must account for, counted in the raw
/// text by something that is not the transformer.
const LITERAL_SPAWN: &str = "std::thread::spawn(";

fn clone_root() -> Option<PathBuf> {
    match std::env::var_os(CLONE_VAR) {
        Some(p) if !p.is_empty() => Some(PathBuf::from(p)),
        _ => None,
    }
}

/// The clone's HEAD commit, read from `.git` rather than by running `git`, so
/// the test starts no subprocess. `None` when `.git` is not a shape this
/// understands -- which is a skip with a reason, never a pass.
fn head_commit(root: &Path) -> Option<String> {
    let head = fs::read_to_string(root.join(".git/HEAD")).ok()?;
    let head = head.trim();
    match head.strip_prefix("ref: ") {
        // A symbolic HEAD: follow it into `.git/<ref>`, or into the packed
        // refs a fresh clone may still be using.
        Some(reference) => match fs::read_to_string(root.join(".git").join(reference)) {
            Ok(sha) => Some(sha.trim().to_owned()),
            Err(_) => {
                let packed = fs::read_to_string(root.join(".git/packed-refs")).ok()?;
                packed.lines().find_map(|l| {
                    let (sha, name) = l.split_once(' ')?;
                    (name == reference).then(|| sha.to_owned())
                })
            }
        },
        // A detached HEAD is the commit itself.
        None => Some(head.to_owned()),
    }
}

/// Every `.rs` under `dir`, recursively, in a deterministic order. Symlinked
/// directories are not followed: a loop would turn a read-only walk into a hang.
fn walk_rs(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<_> = entries.filter_map(Result::ok).collect();
    entries.sort_by_key(std::fs::DirEntry::path);
    for entry in entries {
        let path = entry.path();
        let Ok(meta) = entry.metadata() else { continue };
        if meta.file_type().is_symlink() {
            continue;
        }
        if meta.is_dir() {
            walk_rs(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

fn collect(root: &Path) -> Vec<PathBuf> {
    let mut files = Vec::new();
    let Ok(crates) = fs::read_dir(root.join("crates")) else {
        return files;
    };
    let mut crate_dirs: Vec<PathBuf> = crates
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    crate_dirs.sort();
    for c in crate_dirs {
        walk_rs(&c.join("src"), &mut files);
        walk_rs(&c.join("tests"), &mut files);
    }
    files.sort();
    files
}

fn head(v: &[String]) -> String {
    let shown: Vec<&str> = v.iter().take(8).map(String::as_str).collect();
    if v.len() > shown.len() {
        format!("{shown:#?} (+{} more)", v.len() - shown.len())
    } else {
        format!("{shown:#?}")
    }
}

#[derive(Default)]
struct Totals {
    files: usize,
    fn_items: usize,
    const_fns: usize,
    extern_fns: usize,
    async_fns: usize,
    try_syn: usize,
    try_macro_tokens: usize,
    macro_skips: usize,
    eligible: usize,
    instrumented: usize,
    try_sites: usize,
    sink_sites: usize,
    arm_sites: usize,
    closure_sites: usize,
    arms_propagate: usize,
    arms_panic: usize,
    arms_escaped: usize,
    arms_handled: usize,
    closures_framed: usize,
    async_partials: usize,
    partial_macro_arg: usize,
    partial_struct_literal: usize,
    partial_async_block: usize,
    spawns_wrapped: usize,
    spawns_declared: usize,
    literal_spawns: usize,
}

/// The three reasons this measurement does not run, each named rather than
/// silent. libtest captures a passing test's output, so the reason a CI row
/// says `ok` is carried by the test's NAME as well as by these lines.
fn skip(why: &str) {
    eprintln!(
        "SKIP census_on_the_bloomery_clone_or_skipped_when_SENSORIUM_BLOOMERY_CLONE_is_unset: \
         {why}"
    );
}

#[test]
fn census_on_the_bloomery_clone_or_skipped_when_sensorium_bloomery_clone_is_unset() {
    let Some(root) = clone_root() else {
        skip(&format!("{CLONE_VAR} is unset; nothing was measured"));
        return;
    };
    if !root.join("crates").is_dir() {
        skip(&format!(
            "{CLONE_VAR}={} has no crates/ directory; nothing was measured",
            root.display()
        ));
        return;
    }
    match head_commit(&root) {
        None => {
            skip(&format!(
                "could not read {}/.git/HEAD; the pins below belong to {PINNED_COMMIT} and \
                 were not checked",
                root.display()
            ));
            return;
        }
        Some(sha) if sha != PINNED_COMMIT => {
            skip(&format!(
                "the clone at {} is at {sha}, not the pinned {PINNED_COMMIT}; \
                 the plan's numbers were not checked against someone else's tree",
                root.display()
            ));
            return;
        }
        Some(_) => {}
    }

    let files = collect(&root);
    assert!(
        !files.is_empty(),
        "the clone is present at {} but the walk found no .rs files -- the walk is broken",
        root.display()
    );

    let mut t = Totals::default();
    let mut next_site: u32 = 0;
    let mut unreadable: Vec<String> = Vec::new();
    let mut unparseable: Vec<String> = Vec::new();
    let mut line_moves: Vec<String> = Vec::new();
    let mut reparse_failures: Vec<String> = Vec::new();
    let mut missing_static: Vec<String> = Vec::new();
    let mut per_file_mismatch: Vec<String> = Vec::new();
    let mut try_mismatch: Vec<String> = Vec::new();
    let mut appended: Vec<String> = Vec::new();
    let mut spawn_mismatch: Vec<String> = Vec::new();

    for path in &files {
        let rel = path
            .strip_prefix(&root)
            .unwrap_or(path)
            .to_string_lossy()
            .into_owned();
        let Ok(source) = fs::read_to_string(path) else {
            unreadable.push(rel);
            continue;
        };
        let c = census(&source);
        if !c.parsed {
            unparseable.push(rel);
            continue;
        }
        t.files += 1;
        t.fn_items += c.fn_items;
        t.const_fns += c.const_fns;
        t.extern_fns += c.extern_fns;
        t.async_fns += c.async_fns;
        t.try_syn += c.try_syn;
        t.try_macro_tokens += c.try_macro_tokens;
        t.arms_propagate += c.arms_propagate;
        t.arms_panic += c.arms_panic;
        t.arms_escaped += c.arms_escaped;
        t.arms_handled += c.arms_handled;
        t.closures_framed += c.closures_framed;
        t.async_partials += c.async_partials;
        t.eligible += c.eligible();
        let literal = source.matches(LITERAL_SPAWN).count();
        t.literal_spawns += literal;

        // Every file is transformed BOTH ways: the crate-root static is the rule
        // most likely to break on real trailing comments, so it is exercised on
        // all of them, not just on the handful of real roots.
        for is_crate_root in [false, true] {
            let out = transform(&source, &rel, META, next_site, is_crate_root)
                .unwrap_or_else(|e| panic!("{rel} (crate_root={is_crate_root}): {e}"));
            if out.source.lines().count() != source.lines().count() + usize::from(out.appended_line)
            {
                line_moves.push(format!(
                    "{rel} (crate_root={is_crate_root}): {} -> {}",
                    source.lines().count(),
                    out.source.lines().count()
                ));
            }
            if out.appended_line {
                appended.push(format!("{rel} (crate_root={is_crate_root})"));
            }
            match syn::parse_file(&out.source) {
                Err(e) => reparse_failures.push(format!("{rel} (root={is_crate_root}): {e}")),
                Ok(parsed) => {
                    let declared = parsed.items.iter().any(|item| match item {
                        syn::Item::Static(st) => st.ident == "__SENSORIUM_UNIT",
                        _ => false,
                    });
                    if declared != is_crate_root {
                        missing_static
                            .push(format!("{rel} (root={is_crate_root}): declared={declared}"));
                    }
                }
            }
            if is_crate_root {
                continue;
            }
            let kinds = |k: SiteKind| out.sites.iter().filter(|s| s.kind == k).count();
            let fn_sites = kinds(SiteKind::Fn);
            let try_sites = kinds(SiteKind::Try);
            let partial = |reason: &str| out.partial.iter().filter(|p| p.reason == reason).count();
            let macro_arg = partial("macro-arg");
            // A `struct-literal` row can mark a sink as well as a `?`, so the
            // identity subtracts only the ones whose KIND is `try` -- and, since
            // rung 3's task 3, the `async-block` rows beside them: a `?` inside
            // a future is a `syn::ExprTry` that was deliberately not wrapped.
            let struct_literal = out
                .partial
                .iter()
                .filter(|p| {
                    p.kind == SiteKind::Try && matches!(p.reason, "struct-literal" | "async-block")
                })
                .count();
            t.instrumented += fn_sites;
            t.try_sites += try_sites;
            t.sink_sites += kinds(SiteKind::Sink);
            t.arm_sites += kinds(SiteKind::Arm);
            t.closure_sites += kinds(SiteKind::Closure);
            t.partial_macro_arg += macro_arg;
            t.partial_struct_literal += struct_literal;
            t.partial_async_block += partial("async-block");
            // Rung 3's identity, PER FILE. `try_syn` counts the `?` the parser
            // gave a node for, and every one of those is either wrapped or
            // declined by name; the `?` TOKENS inside macro invocations are a
            // disjoint set -- no node exists for them -- and are matched
            // against their own count.
            if try_sites + struct_literal != c.try_syn || macro_arg != c.try_macro_tokens {
                try_mismatch.push(format!(
                    "{rel}: try {try_sites} + struct-literal {struct_literal} vs try_syn {}, \
                     macro-arg {macro_arg} vs try_macro_tokens {}",
                    c.try_syn, c.try_macro_tokens
                ));
            }
            t.macro_skips += out.skipped.iter().filter(|s| s.reason == "macro").count();
            let wrapped = out.spawns.iter().filter(|s| s.wrapped).count();
            t.spawns_wrapped += wrapped;
            t.spawns_declared += out.spawns.len() - wrapped;
            if wrapped != literal {
                spawn_mismatch.push(format!("{rel}: {wrapped} wrapped vs {literal} literal"));
            }
            // PER FILE, not just in aggregate: a file that over-instruments and
            // another that under-instruments would cancel in the sum.
            if fn_sites + c.async_fns != c.eligible() {
                per_file_mismatch.push(format!(
                    "{rel}: fn sites {fn_sites} + async {} != eligible {}",
                    c.async_fns,
                    c.eligible()
                ));
            }
            next_site += u32::try_from(out.sites.len()).expect("site count fits u32");
        }
    }

    println!("clone root:           {}", root.display());
    println!("files walked:         {}", files.len());
    println!("files measured:       {}", t.files);
    println!("fn items (with body): {}", t.fn_items);
    println!("  const fn skipped:   {}", t.const_fns);
    println!("  extern fn skipped:  {}", t.extern_fns);
    println!("  async fn skipped:   {}", t.async_fns);
    println!("  macro_rules bodies: {}", t.macro_skips);
    println!("eligible (E2 denom):  {}", t.eligible);
    println!("`?` as syn nodes:     {}", t.try_syn);
    println!("`?` in macro tokens:  {}", t.try_macro_tokens);
    println!("instrumented (fns):   {}", t.instrumented);
    println!("`?` sites wrapped:    {}", t.try_sites);
    println!("sink sites wrapped:   {}", t.sink_sites);
    // Rung 3 task 3, REPORTED and not pinned: what a real tree's arms are
    // classified as is a property of that tree, and a pin on it would only say
    // the tree had not changed. The identities below are what is asserted.
    println!("arm sites:            {}", t.arm_sites);
    println!("  arms propagate:     {}", t.arms_propagate);
    println!("  arms panic (unprobed): {}", t.arms_panic);
    println!("  arms escaped:       {}", t.arms_escaped);
    println!("  arms handled:       {}", t.arms_handled);
    println!("closure frames:       {}", t.closure_sites);
    println!("partial macro-arg:    {}", t.partial_macro_arg);
    println!("partial struct-lit:   {}", t.partial_struct_literal);
    println!("partial async-block:  {}", t.partial_async_block);
    println!("spawn sites wrapped:  {}", t.spawns_wrapped);
    println!("spawn sites declared: {}", t.spawns_declared);
    println!("literal `{LITERAL_SPAWN}`: {}", t.literal_spawns);
    println!("line moves:           {}", line_moves.len());
    println!("re-parse failures:    {}", reparse_failures.len());
    println!(
        "appended_line:        {} {}",
        appended.len(),
        head(&appended)
    );

    assert!(unreadable.is_empty(), "unreadable: {}", head(&unreadable));
    assert!(
        unparseable.is_empty(),
        "syn could not parse: {}",
        head(&unparseable)
    );
    assert!(
        line_moves.is_empty(),
        "line count moved: {}",
        head(&line_moves)
    );
    assert!(
        reparse_failures.is_empty(),
        "transformed source did not re-parse: {}",
        head(&reparse_failures)
    );
    assert!(
        missing_static.is_empty(),
        "the unit static was not a top-level item exactly when it should be: {}",
        head(&missing_static)
    );
    assert!(
        per_file_mismatch.is_empty(),
        "sites + async != eligible in: {}",
        head(&per_file_mismatch)
    );
    assert!(
        spawn_mismatch.is_empty(),
        "wrapped spawn sites do not match the literal spelling in: {}",
        head(&spawn_mismatch)
    );
    assert!(
        try_mismatch.is_empty(),
        "the `?` the walk counted and the `?` it wrapped are not one set in: {}",
        head(&try_mismatch)
    );
    assert_eq!(
        t.instrumented + t.async_fns,
        t.eligible,
        "instrumented + async != eligible over the clone"
    );
    // Rung 3 task 3's identities over the clone: one decision behind each
    // counter and each site, so these cannot drift apart without one of the two
    // being wrong.
    assert_eq!(
        t.arms_propagate + t.arms_escaped + t.arms_handled,
        t.arm_sites,
        "classified arms and arm sites disagree over the clone \
         ({} panic arms are deliberately unprobed)",
        t.arms_panic
    );
    assert_eq!(
        t.closures_framed, t.closure_sites,
        "framed closures and closure sites disagree over the clone"
    );
    assert_eq!(
        t.async_partials, t.partial_async_block,
        "`?` inside an async block, counted and declared, disagree over the clone"
    );
    assert_eq!(
        t.spawns_wrapped, t.literal_spawns,
        "every literal `{LITERAL_SPAWN}` must be rewritten, and nothing else"
    );

    // The pins. Everything above is an IDENTITY, and a walk that silently
    // covered three files satisfies every one of them; these three numbers are
    // what say the measurement is the one the plan made, on the tree it made it
    // on (checked above).
    assert_eq!(
        files.len(),
        PINNED_FILES,
        "the walk covered {} files, not the {PINNED_FILES} measured at {PINNED_COMMIT}",
        files.len()
    );
    assert_eq!(
        t.files, PINNED_FILES,
        "{} of those parsed; all {PINNED_FILES} did at {PINNED_COMMIT}",
        t.files
    );
    assert_eq!(
        t.eligible, PINNED_ELIGIBLE,
        "eligible fn items moved: {} against the {PINNED_ELIGIBLE} measured at {PINNED_COMMIT}",
        t.eligible
    );
    assert_eq!(
        t.spawns_wrapped, PINNED_SPAWNS_WRAPPED,
        "rewritten spawn sites moved: {} against the {PINNED_SPAWNS_WRAPPED} measured at \
         {PINNED_COMMIT}",
        t.spawns_wrapped
    );
    assert_eq!(
        t.try_syn, PINNED_TRY_SYN,
        "syn-visible `?` moved: {} against the {PINNED_TRY_SYN} measured at {PINNED_COMMIT}; \
         E2\u{2033}'s denominator was pre-registered from that number",
        t.try_syn
    );
    assert_eq!(
        t.try_macro_tokens, PINNED_TRY_MACRO,
        "`?` tokens inside macro invocations moved: {} against the {PINNED_TRY_MACRO} measured \
         at {PINNED_COMMIT}",
        t.try_macro_tokens
    );
    // Rung 3, in aggregate: every `syn`-visible `?` on this tree is instrumented
    // and the one macro-argument `?` is declared. The third number is what makes
    // the first two a ratio over ONE set -- a `?` the transformer had to decline
    // for a reason of its own would show up here rather than quietly shrinking
    // the numerator.
    assert_eq!(
        t.try_sites, PINNED_TRY_SYN,
        "wrapped `?` sites: {} against the {PINNED_TRY_SYN} `?` nodes at {PINNED_COMMIT}",
        t.try_sites
    );
    assert_eq!(
        t.partial_macro_arg, PINNED_TRY_MACRO,
        "declared macro-argument `?`: {} against {PINNED_TRY_MACRO}",
        t.partial_macro_arg
    );
    assert_eq!(
        t.partial_struct_literal, PINNED_PARTIAL_STRUCT_LITERAL,
        "a `?` was declined for an exterior struct literal: {} at {PINNED_COMMIT}",
        t.partial_struct_literal
    );
    assert_eq!(
        t.sink_sites, PINNED_SINKS_WRAPPED,
        "wrapped sink sites: {} against the {PINNED_SINKS_WRAPPED} measured at \
         {PINNED_COMMIT}",
        t.sink_sites
    );
    // Every real source file contains at least one item, so none of them can
    // reach the appended-final-line shape.
    assert!(
        appended.is_empty(),
        "a real source file needed a final line appended: {}",
        head(&appended)
    );
}

/// The nine keys `src/bin/census.rs` documents, in the order it writes them. A
/// consumer of the JSON reads by key, so a renamed or dropped key is a broken
/// instrument even when every number is right.
const ROW_KEYS: [&str; 9] = [
    "file",
    "parsed",
    "fn_items",
    "const_fns",
    "extern_fns",
    "async_fns",
    "eligible",
    "try_syn",
    "try_macro_tokens",
];

fn skip_bin(why: &str) {
    eprintln!("SKIP the_census_binary_agrees_with_a_direct_census_call_per_file: {why}");
}

/// The checked-in instrument's identity.
///
/// `src/bin/census.rs` is what produces an acceptance record's E2″ denominator,
/// so what it prints has to be what [`census`] returns -- not approximately, and
/// not in aggregate. Every row is matched to the file it names and compared
/// column by column, and the row SET is compared to the walk's file set, so a
/// binary that silently skipped a directory fails here rather than shrinking a
/// denominator later.
///
/// [`transform`] is deliberately not involved: this is the counting path alone.
#[test]
fn the_census_binary_agrees_with_a_direct_census_call_per_file() {
    let Some(root) = clone_root() else {
        skip_bin(&format!("{CLONE_VAR} is unset; nothing was measured"));
        return;
    };
    if !root.join("crates").is_dir() {
        skip_bin(&format!(
            "{CLONE_VAR}={} has no crates/ directory; nothing was measured",
            root.display()
        ));
        return;
    }
    match head_commit(&root) {
        None => {
            skip_bin(&format!(
                "could not read {}/.git/HEAD; the identity below belongs to {PINNED_COMMIT} \
                 and was not checked",
                root.display()
            ));
            return;
        }
        Some(sha) if sha != PINNED_COMMIT => {
            skip_bin(&format!(
                "the clone at {} is at {sha}, not the pinned {PINNED_COMMIT}; the identity \
                 was not checked against someone else's tree",
                root.display()
            ));
            return;
        }
        Some(_) => {}
    }

    let out = std::process::Command::new(env!("CARGO_BIN_EXE_census"))
        .arg(&root)
        .output()
        .expect("running the census binary");
    assert!(
        out.status.success(),
        "census exited {:?}: {}",
        out.status.code(),
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(
        out.stderr.is_empty(),
        "census wrote to stderr: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8(out.stdout).expect("census prints UTF-8");

    let rows: Vec<serde_json::Value> = stdout
        .lines()
        .map(|l| serde_json::from_str(l).unwrap_or_else(|e| panic!("row is not JSON: {l:?}: {e}")))
        .collect();

    // The row set is the walk's file set: at PINNED_COMMIT every `.rs` in the
    // clone lives under `crates/*/{src,tests}`, so the binary's whole-tree walk
    // and `collect`'s narrower one must name exactly the same files.
    let files = collect(&root);
    let expected: Vec<String> = files
        .iter()
        .map(|p| {
            p.strip_prefix(&root)
                .unwrap_or(p)
                .to_string_lossy()
                .into_owned()
        })
        .collect();
    let named: Vec<String> = rows
        .iter()
        .map(|r| {
            r["file"]
                .as_str()
                .unwrap_or_else(|| panic!("a row has no string `file`: {r}"))
                .to_owned()
        })
        .collect();
    assert_eq!(
        named,
        expected,
        "the binary named {} files, the walk {}",
        named.len(),
        expected.len()
    );

    let mut mismatched: Vec<String> = Vec::new();
    for (row, path) in rows.iter().zip(&files) {
        let keys: Vec<&str> = row
            .as_object()
            .expect("a row is a JSON object")
            .keys()
            .map(String::as_str)
            .collect();
        let mut sorted_keys = keys.clone();
        sorted_keys.sort_unstable();
        let mut want = ROW_KEYS;
        want.sort_unstable();
        assert_eq!(
            sorted_keys,
            want.to_vec(),
            "a row's keys are not the nine documented ones: {row}"
        );

        let source = fs::read_to_string(path).expect("the walk just listed this file");
        let c = census(&source);
        let got = [
            ("parsed", u64::from(c.parsed)),
            ("fn_items", c.fn_items as u64),
            ("const_fns", c.const_fns as u64),
            ("extern_fns", c.extern_fns as u64),
            ("async_fns", c.async_fns as u64),
            ("eligible", c.eligible() as u64),
            ("try_syn", c.try_syn as u64),
            ("try_macro_tokens", c.try_macro_tokens as u64),
        ];
        for (key, want) in got {
            let printed = match &row[key] {
                serde_json::Value::Bool(b) => u64::from(*b),
                serde_json::Value::Number(n) => n.as_u64().unwrap_or(u64::MAX),
                other => panic!("{key} is neither a bool nor a number: {other}"),
            };
            if printed != want {
                mismatched.push(format!(
                    "{}: {key} printed {printed}, census() says {want}",
                    row["file"]
                ));
            }
        }
    }
    assert!(
        mismatched.is_empty(),
        "the binary disagrees with census(): {}",
        head(&mismatched)
    );
    println!("rows checked: {}", rows.len());
}
