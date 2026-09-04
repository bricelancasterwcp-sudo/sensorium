//! `census <dir>` -- one JSON line per `.rs` file under `<dir>`.
//!
//! This is E2/E2″'s DENOMINATOR instrument, checked in rather than typed at a
//! shell, so the number in an acceptance record can be reproduced by running the
//! same binary again on the same tree. It calls [`census`] and nothing else: the
//! transformer is not involved, no file is written, no subprocess is started,
//! and the tree is only ever opened for reading.
//!
//! Each line is one object, in this key order:
//!
//! ```text
//! {"file":"crates/c/src/lib.rs","parsed":true,"fn_items":12,"const_fns":0,
//!  "extern_fns":0,"async_fns":3,"eligible":12,"try_syn":7,"try_macro_tokens":1}
//! ```
//!
//! `file` is relative to `<dir>`, so the output carries no absolute path and two
//! runs on two clones of the same commit are byte-comparable. `eligible` is
//! `Census::eligible()` written out, so a reader summing a column never has to
//! re-derive it. `parsed` is false for a file `syn` could not parse, and every
//! count on such a line is a zero that was never measured -- check `parsed`
//! first (`Census`'s own none-versus-zero discipline).
//!
//! A file that cannot be READ is a hard failure, not a `parsed: false` row: an
//! unreadable file would silently shrink every total, and a denominator that
//! shrinks silently is the failure mode the pins in `tests/census.rs` exist to
//! catch.

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use sensorium_transform::census;

/// One file's row. Field order is the JSON key order.
#[derive(serde::Serialize)]
struct Row<'a> {
    file: &'a str,
    parsed: bool,
    fn_items: usize,
    const_fns: usize,
    extern_fns: usize,
    async_fns: usize,
    eligible: usize,
    try_syn: usize,
    try_macro_tokens: usize,
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let [_, dir] = args.as_slice() else {
        eprintln!("usage: census <dir>    (one JSON line per .rs file under <dir>)");
        return ExitCode::from(2);
    };
    let root = PathBuf::from(dir);
    if !root.is_dir() {
        eprintln!("census: {dir} is not a directory");
        return ExitCode::from(2);
    }

    let mut files = Vec::new();
    walk_rs(&root, &mut files);
    files.sort();

    for path in &files {
        let rel = path
            .strip_prefix(&root)
            .unwrap_or(path)
            .to_string_lossy()
            .into_owned();
        let source = match std::fs::read_to_string(path) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("census: cannot read {rel}: {e}");
                return ExitCode::FAILURE;
            }
        };
        let c = census(&source);
        let row = Row {
            file: &rel,
            parsed: c.parsed,
            fn_items: c.fn_items,
            const_fns: c.const_fns,
            extern_fns: c.extern_fns,
            async_fns: c.async_fns,
            eligible: c.eligible(),
            try_syn: c.try_syn,
            try_macro_tokens: c.try_macro_tokens,
        };
        match serde_json::to_string(&row) {
            Ok(line) => println!("{line}"),
            Err(e) => {
                eprintln!("census: cannot serialise the row for {rel}: {e}");
                return ExitCode::FAILURE;
            }
        }
    }
    ExitCode::SUCCESS
}

/// Every `.rs` under `dir`, recursively. Symlinked directories are not followed:
/// a loop would turn a read-only walk into a hang. A directory that cannot be
/// listed is skipped silently HERE and caught by the pins, which is the same
/// discipline `tests/census.rs` uses for its own walk.
fn walk_rs(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
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
