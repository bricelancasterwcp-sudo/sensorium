//! `--refocus-of <run-id>`, validated against the store BEFORE anything is
//! rewritten or built (design 2026-09-07 §2.1).
//!
//! The link a re-run carries is only worth what it points at: a value naming
//! no trace would cost a full instrumented build and then stamp the new trace
//! with a run id nothing in the store answers to, which `refocus`'s pair
//! lookup would read as "the driver produced nothing". So the check runs in
//! the same place, and with the same "nothing was built." ending, as the
//! focus refusal one line below it.

use std::path::Path;

/// Ok exactly when `<store>/traces/<run_id>.db` is a plain file.
///
/// `store` is the resolved `SENSORIUM_DIR` -- the root, not its `traces`
/// subdirectory -- because that is what a person set and therefore what the
/// refusal has to name back to them.
///
/// # Errors
/// The two §2.1 refusals, ready to print: a value that is not a run id at
/// all, and a run id the store does not hold.
pub fn check(store: &Path, run_id: &str) -> Result<(), String> {
    // The SHAPE refusal quotes what was typed, before any normalisation: a
    // person who typed `/abs/path/x.db` should be shown their own value.
    let stem = run_id_of(run_id);
    if !is_run_id(run_id) || stem.is_empty() {
        return Err(format!(
            "REFUSED: --refocus-of {run_id} is not a run id; nothing was built."
        ));
    }
    // `is_file`, not `exists`: a DIRECTORY at that path is not a trace, and
    // accepting it would hand `refocus` a pair lookup that can never resolve.
    if store.join("traces").join(format!("{stem}.db")).is_file() {
        return Ok(());
    }
    // The STORE-MISS refusal quotes the run id the value NAMES, which is what
    // was looked up -- so `<id>.db.db` is told that `<id>.db` is not there,
    // naming the file the store was actually asked for.
    Err(format!(
        "REFUSED: --refocus-of {stem} names no trace in {}; nothing was built.",
        store.display()
    ))
}

/// The run id a `--refocus-of` value NAMES: itself, with ONE trailing `.db`
/// removed (design B2). Tab-completing the trace file is the ordinary way to
/// get a run id onto the command line, so `<id>.db` names `<id>`; stripping
/// once and not repeatedly keeps `<id>.db.db` naming `<id>.db`, which the
/// store does not hold and which the store-miss refusal then quotes back.
#[must_use]
pub fn run_id_of(value: &str) -> &str {
    value.strip_suffix(".db").unwrap_or(value)
}

/// The value as the invocation RECORDS it, and therefore as every trace's
/// `refocus_of` carries it: the run id it names, never the spelling typed.
///
/// Recording `<id>.db` would defeat the whole point of the check one line
/// above -- `refocus`'s pair lookup asks the store for traces whose
/// `refocus_of` equals a run id, and `<id>.db` equals none of them. A link
/// that passed validation and then could not be resolved is exactly the
/// failure [`is_run_id`] exists to prevent.
#[must_use]
pub fn canonical(value: Option<&str>) -> Option<String> {
    value.map(|v| run_id_of(v).to_owned())
}

/// The §2.1 gate as the driver runs it: resolve the store, check the value,
/// and print the refusal where there is one. `Ok(false)` means "refused,
/// leave with 2"; the `Err` arm is reserved for a store that cannot be
/// resolved at all, which is the driver's ordinary error path and not a
/// refusal about this flag.
///
/// Here rather than in `driver.rs` because that file is at its 800-line
/// ceiling and because the refusal's wording, its store resolution and its
/// "nothing was built." promise are one subject.
///
/// # Errors
/// If `SENSORIUM_DIR` is unset and `HOME` is unset too.
pub fn gate(refocus_of: Option<&str>) -> Result<bool, String> {
    let Some(run_id) = refocus_of else {
        return Ok(true);
    };
    if let Err(refusal) = check(&crate::convert::store_root()?, run_id) {
        eprintln!("{refusal}");
        return Ok(false);
    }
    Ok(true)
}

/// A run id is a trace file's STEM: it names a file inside the store's
/// `traces` directory and never a path to one. A value carrying a separator
/// or a `..` would otherwise reach out of the store -- `--refocus-of
/// ../../x` would happily "find" a `.db` anywhere on the disk and stamp the
/// new trace with a run id no store lookup can resolve.
fn is_run_id(value: &str) -> bool {
    !value.is_empty() && !value.contains("..") && !value.contains(['/', '\\']) && value != "."
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    const RUN: &str = "20260101-000000-aaaaaa";

    fn scratch(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("refocus-of-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join("traces")).unwrap();
        dir
    }

    #[test]
    fn a_run_id_the_store_holds_is_accepted() {
        let store = scratch("present");
        std::fs::write(store.join("traces").join(format!("{RUN}.db")), b"").unwrap();
        assert_eq!(check(&store, RUN), Ok(()));
    }

    #[test]
    fn a_run_id_the_store_does_not_hold_is_refused_by_name() {
        let store = scratch("absent");
        assert_eq!(
            check(&store, RUN).unwrap_err(),
            format!(
                "REFUSED: --refocus-of {RUN} names no trace in {}; nothing was built.",
                store.display()
            )
        );
    }

    /// The `.tmp` half-written form is not a trace either: the converter
    /// renames it into place only once the trace is finished.
    #[test]
    fn a_half_written_trace_is_not_a_trace() {
        let store = scratch("tmp");
        std::fs::write(store.join("traces").join(format!("{RUN}.db.tmp")), b"").unwrap();
        assert!(check(&store, RUN).is_err());
    }

    #[test]
    fn a_directory_where_the_trace_would_be_is_not_a_trace() {
        let store = scratch("dir");
        std::fs::create_dir_all(store.join("traces").join(format!("{RUN}.db"))).unwrap();
        assert!(
            check(&store, RUN).is_err(),
            "a directory is not a trace file"
        );
    }

    #[test]
    fn a_value_that_is_not_a_run_id_is_refused_before_the_store_is_consulted() {
        // No store at all: the shape refusal must not depend on one.
        let store = PathBuf::from("/nonexistent-store");
        for value in ["../x", "a/b", "/abs", "..", "a\\b", ""] {
            assert_eq!(
                check(&store, value).unwrap_err(),
                format!("REFUSED: --refocus-of {value} is not a run id; nothing was built."),
                "{value:?}"
            );
        }
    }

    /// Tab-completing the trace file is how a run id usually reaches the
    /// command line, so `<id>.db` names `<id>` (design B2). Stripping ONCE
    /// and not repeatedly is what keeps the refusal honest below.
    #[test]
    fn a_trailing_db_suffix_names_the_run_the_file_holds() {
        let store = scratch("db-suffix");
        std::fs::write(store.join("traces").join(format!("{RUN}.db")), b"").unwrap();
        assert_eq!(check(&store, &format!("{RUN}.db")), Ok(()));
        assert_eq!(run_id_of(&format!("{RUN}.db")), RUN);
    }

    /// One `.db` off, not every `.db` off: `<id>.db.db` names `<id>.db`,
    /// which the store does not hold -- and the refusal says so by that
    /// name, so a reader is told which file was looked for.
    #[test]
    fn only_one_db_suffix_is_stripped_and_the_refusal_names_what_was_sought() {
        let store = scratch("db-suffix-twice");
        std::fs::write(store.join("traces").join(format!("{RUN}.db")), b"").unwrap();
        assert_eq!(
            check(&store, &format!("{RUN}.db.db")).unwrap_err(),
            format!(
                "REFUSED: --refocus-of {RUN}.db names no trace in {}; nothing was built.",
                store.display()
            )
        );
    }

    /// A bare `.db` names no run at all -- stripping it leaves nothing, and
    /// an empty stem would look up `traces/.db`.
    #[test]
    fn a_bare_db_suffix_is_not_a_run_id() {
        let store = scratch("db-only");
        assert_eq!(
            check(&store, ".db").unwrap_err(),
            "REFUSED: --refocus-of .db is not a run id; nothing was built."
        );
    }

    /// What the invocation RECORDS is the run id, never the spelling: a
    /// `refocus_of` of `<id>.db` would pass validation and then match no
    /// trace in the store's pair lookup.
    #[test]
    fn what_is_recorded_is_the_run_id_and_not_the_spelling_typed() {
        assert_eq!(canonical(None), None);
        assert_eq!(canonical(Some(RUN)).as_deref(), Some(RUN));
        assert_eq!(canonical(Some(&format!("{RUN}.db"))).as_deref(), Some(RUN));
    }

    /// A run id that escapes the store must be refused for its SHAPE, not
    /// merely fail to be found: `../<store>/traces/<run>.db` resolves to a
    /// real trace, and accepting it would stamp a link the store cannot
    /// look up.
    #[test]
    fn an_escaping_path_is_refused_even_when_it_resolves_to_a_real_trace() {
        let store = scratch("escape");
        std::fs::write(store.join("traces").join(format!("{RUN}.db")), b"").unwrap();
        let escape = format!("../traces/{RUN}");
        assert_eq!(
            check(&store, &escape).unwrap_err(),
            format!("REFUSED: --refocus-of {escape} is not a run id; nothing was built.")
        );
    }
}
