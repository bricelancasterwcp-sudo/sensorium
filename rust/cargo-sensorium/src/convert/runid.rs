//! Minting a fresh run id per trace: `YYYYMMDD-HHMMSS-xxxxxx`, local time, a
//! fresh 6-hex suffix, collision-checked against the traces directory
//! (`docs/TRACE-FORMAT.md` §2's `paths.new_run_id` shape).

use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

/// Bumped once per call within this process, so two traces minted in the same
/// invocation (a parent and a child pid, or two pids of one run) mix in a
/// different value even when the clock has not ticked.
static SALT: AtomicU32 = AtomicU32::new(0);

/// `$SENSORIUM_DIR/traces`, creating it if absent. `SENSORIUM_DIR` defaults to
/// `~/.sensorium`, `HOME` read from the environment -- there is no `dirs`
/// crate in this workspace's dependency policy, so `Path::home()`'s Python
/// equivalent is one `env::var` here.
///
/// # Errors
/// If `HOME` is unset and `SENSORIUM_DIR` is not given, or the directory
/// cannot be created.
pub fn traces_dir() -> Result<PathBuf, String> {
    let root = match std::env::var("SENSORIUM_DIR")
        .ok()
        .filter(|v| !v.is_empty())
    {
        Some(dir) => PathBuf::from(dir),
        None => {
            let home = std::env::var("HOME")
                .map_err(|_| "SENSORIUM_DIR is unset and HOME is unset too".to_owned())?;
            Path::new(&home).join(".sensorium")
        }
    };
    let dir = root.join("traces");
    std::fs::create_dir_all(&dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    Ok(dir)
}

/// Whether `id` is already spoken for: a `.db`/`.db.tmp` already on disk in
/// `dir`, or already minted earlier in THIS invocation (`minted`) -- a
/// sibling pid's id, assigned moments ago in the same loop, that has not yet
/// had a `.db`/`.db.tmp` written for the directory half of this check to see
/// (`mod.rs` mints every id before converting any pid, precisely so a
/// parent's `child_runs` can name a child's id regardless of conversion
/// order -- which means the directory alone cannot rule out a collision
/// between two ids minted in the same pass).
fn is_taken(id: &str, dir: &Path, minted: &HashSet<String>) -> bool {
    minted.contains(id)
        || dir.join(format!("{id}.db")).exists()
        || dir.join(format!("{id}.db.tmp")).exists()
}

/// A fresh id: not already a file in `dir`, and not already in `minted`.
/// Loops on collision, which a same-second, same-salt run could in principle
/// hit -- the salt changes on every call, so a real collision needs the
/// clock, the salt and `getpid()` mix to repeat, which the loop simply
/// retries past.
///
/// # Errors
/// If the local-time stamp cannot be computed (the clock is before the
/// epoch, or `localtime_r` refuses it).
pub fn mint(dir: &Path, minted: &HashSet<String>) -> Result<String, String> {
    mint_loop(dir, minted, one_candidate)
}

/// The retry loop, generic over how the next candidate is produced. Real
/// code always passes [`one_candidate`]; `tests::mint_loop_retries_past_a_
/// candidate_already_in_the_minted_set` passes a fixed sequence instead, so
/// the retry path is exercised deterministically rather than hoping the
/// clock and the salt repeat.
fn mint_loop(
    dir: &Path,
    minted: &HashSet<String>,
    mut next: impl FnMut() -> Result<String, String>,
) -> Result<String, String> {
    loop {
        let id = next()?;
        if !is_taken(&id, dir, minted) {
            return Ok(id);
        }
    }
}

fn one_candidate() -> Result<String, String> {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| format!("the clock is before the epoch: {e}"))?;
    let secs = i64::try_from(now.as_secs()).map_err(|e| format!("the clock is unreadable: {e}"))?;
    let salt = u64::from(SALT.fetch_add(1, Ordering::Relaxed));
    let mix = u64::from(now.subsec_nanos())
        ^ (u64::from(std::process::id()) << 20)
        ^ (now.as_secs() << 7)
        ^ (salt << 3);
    let stamp = crate::driver::local_stamp(secs)?;
    Ok(format!("{stamp}-{:06x}", mix & 0x00ff_ffff))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn minted_ids_have_the_run_id_shape() {
        let dir = scratch("runid-shape");
        let id = mint(&dir, &HashSet::new()).unwrap();
        let (date, rest) = id.split_once('-').unwrap();
        let (time, hex) = rest.split_once('-').unwrap();
        assert_eq!(date.len(), 8, "{id}");
        assert_eq!(time.len(), 6, "{id}");
        assert_eq!(hex.len(), 6, "{id}");
        assert!(
            id.chars().all(|c| c.is_ascii_hexdigit() || c == '-'),
            "{id}"
        );
    }

    #[test]
    fn repeated_mints_in_one_process_never_collide() {
        let dir = scratch("runid-nodup");
        let mut seen = std::collections::BTreeSet::new();
        for _ in 0..20 {
            let id = mint(&dir, &HashSet::new()).unwrap();
            std::fs::write(dir.join(format!("{id}.db")), b"").unwrap();
            assert!(seen.insert(id), "minted a duplicate id");
        }
    }

    /// `is_taken` is the predicate `mint`'s loop retries on -- tested
    /// directly, with no dependence on the clock or the salt, both for the
    /// on-disk half (a `.db`/`.db.tmp` already there) and the in-memory half
    /// (an id this invocation already minted for a sibling pid).
    #[test]
    fn is_taken_checks_both_the_directory_and_the_tmp_suffix() {
        let dir = scratch("runid-is-taken-disk");
        let id = "20260903-000000-aaaaaa";
        assert!(!is_taken(id, &dir, &HashSet::new()));
        std::fs::write(dir.join(format!("{id}.db.tmp")), b"").unwrap();
        assert!(is_taken(id, &dir, &HashSet::new()));
        assert!(
            !is_taken("20260903-000000-bbbbbb", &dir, &HashSet::new()),
            "a DIFFERENT id must not be reported taken by another id's file"
        );
    }

    #[test]
    fn is_taken_checks_the_minted_set_even_with_nothing_on_disk() {
        let dir = scratch("runid-is-taken-minted");
        let mut minted = HashSet::new();
        minted.insert("20260903-000000-cccccc".to_owned());
        assert!(is_taken("20260903-000000-cccccc", &dir, &minted));
        assert!(!is_taken("20260903-000000-dddddd", &dir, &minted));
    }

    /// The collision this fix exists for: `mod.rs` mints every sibling pid's
    /// id before any of them has a `.db`/`.db.tmp` on disk, so the retry loop
    /// must consult `minted` too, not just the directory. Driven with a fixed
    /// candidate sequence -- deterministic, no clock or salt involved -- so
    /// the retry path is forced rather than hoped for.
    #[test]
    fn mint_loop_retries_past_a_candidate_already_in_the_minted_set() {
        let dir = scratch("runid-mint-loop-retry");
        let mut minted = HashSet::new();
        minted.insert("20260903-000000-aaaaaa".to_owned());
        let mut candidates = vec![
            "20260903-000000-aaaaaa".to_owned(), // in `minted`: must be skipped
            "20260903-000000-bbbbbb".to_owned(), // fresh: must be returned
        ]
        .into_iter();
        let mut calls = 0u32;
        let id = mint_loop(&dir, &minted, || {
            calls += 1;
            Ok(candidates
                .next()
                .expect("mint_loop asked for a candidate past the fixed sequence"))
        })
        .unwrap();
        assert_eq!(id, "20260903-000000-bbbbbb");
        assert_eq!(calls, 2, "exactly one retry, not a busy loop past it");
    }

    /// `mint` itself is a one-line forward to `mint_loop` (whose retry
    /// semantics `mint_loop_retries_past_a_candidate_already_in_the_minted_
    /// set` pins deterministically), so this is a real-clock sanity check
    /// on top of that, not an independent proof: `one_candidate` mixes in a
    /// fresh salt tick every call, so 20 calls not colliding by chance
    /// proves little on its own -- what it DOES catch is `mint` itself
    /// forgetting to accumulate and pass `minted` at every call site that
    /// uses it this way, the shape `mint_run_ids` (`mod.rs`) relies on.
    #[test]
    fn mint_never_returns_an_id_already_in_the_minted_set() {
        let dir = scratch("runid-mint-minted-end-to-end");
        let mut minted = HashSet::new();
        for _ in 0..20 {
            let id = mint(&dir, &minted).unwrap();
            assert!(minted.insert(id), "mint returned an id already in `minted`");
        }
    }

    #[test]
    fn traces_dir_honours_sensorium_dir_when_set() {
        let base = std::env::temp_dir().join(format!("runid-sensorium-dir-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        // SAFETY (test-only): no other thread in this test binary reads or
        // writes SENSORIUM_DIR concurrently with this test.
        unsafe {
            std::env::set_var("SENSORIUM_DIR", &base);
        }
        let dir = traces_dir().unwrap();
        unsafe {
            std::env::remove_var("SENSORIUM_DIR");
        }
        assert_eq!(dir, base.join("traces"));
        assert!(dir.is_dir());
    }
}
