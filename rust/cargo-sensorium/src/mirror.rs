//! The per-unit workspace mirror at `<target>/sensorium/mirror/<-C metadata>/`.
//!
//! Cargo hands the wrapper a RELATIVE crate root and a cwd of the workspace
//! root, so an instrumented unit is compiled by chdir'ing into a tree that
//! looks exactly like the workspace at every path rustc can reach: the
//! rewritten `.rs` files materialised as real files, everything else an
//! absolute symlink to the real thing. That, plus the
//! `--remap-path-prefix=<mirror>=<workspace>` the wrapper appends, is what
//! keeps `file!()`, panic locations, backtraces, debuginfo and dep-info at
//! workspace-relative paths (findings §5.21), and dep-info at workspace-
//! relative paths is what keeps cargo's freshness working.
//!
//! **One mirror per unit.** Cargo compiles one crate root as several units —
//! `src/lib.rs` as `--crate-type lib` and again with `--test`, each with its
//! own `-C metadata` — and the `__SENSORIUM_UNIT` static the transformer
//! appends names that metadata, so the two units need DIFFERENT bytes at the
//! same workspace-relative path. Rung 1 shared one mirror keyed by source hash
//! alone; the second unit found the file "fresh" and compiled a crate root
//! whose static named its twin, mis-attributing every event that unit recorded
//! in a build that was otherwise green (findings §5.22).
//!
//! Three rules the code exists to enforce:
//!
//! 1. **Real directories only where a rewrite lives.** Everything else at each
//!    level is one symlink, so a mirror is a handful of inodes, not a copy.
//! 2. **Real directories are never downgraded**, so a second rewrite under a
//!    directory cannot un-instrument the first.
//! 3. **Idempotent.** A rewrite whose source and tool hash are unchanged is not
//!    written again, so its mtime does not move and cargo stays incurious.
//! 4. **A rewrite that stops being one is undone.** A file this run does not
//!    rewrite -- because it stopped parsing, or left the unit's module tree --
//!    becomes the symlink to the original again and loses its cache stamp.
//!    Keeping the old bytes made an instrumented build compile source a plain
//!    build rejects, in a build that exited 0 (measured 2026-09-03).

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io;
use std::os::unix::fs::symlink;
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};

use crate::sha256;

/// Never mirrored: `target/` is where the mirror itself lives (mirroring it
/// would be a cycle) and `.git/` is large and never read by rustc.
const SKIP_AT_ROOT: &[&str] = &["target", ".git"];

/// One file the wrapper rewrote: where it came from and what it now says.
pub struct Rewrite {
    /// Workspace-relative path, `/`-separated.
    pub rel: String,
    pub content: String,
    /// sha256 of the ORIGINAL bytes. Half the cache key, and the value the
    /// manifest records as `source_hashes[rel]`.
    pub source_hash: String,
}

/// Materialise `rewrites` into `mirror`, mirroring `ws`.
///
/// `tool_hash` is the other half of the cache key: a new transformer or a new
/// driver must invalidate every cached rewrite even where the source did not
/// change.
///
/// # Errors
/// Any filesystem error, with the path that caused it already in the message.
pub fn materialise(
    ws: &Path,
    mirror: &Path,
    cache: &Path,
    tool_hash: &str,
    rewrites: &[Rewrite],
) -> io::Result<()> {
    let rewritten: BTreeMap<&str, &Rewrite> =
        rewrites.iter().map(|r| (r.rel.as_str(), r)).collect();
    let mut required: BTreeSet<String> = BTreeSet::new();
    required.insert(String::new());
    for r in rewrites {
        let mut acc = String::new();
        let mut parts: Vec<&str> = r.rel.split('/').collect();
        parts.pop(); // the file itself is not a directory
        for part in parts {
            if !acc.is_empty() {
                acc.push('/');
            }
            acc.push_str(part);
            required.insert(acc.clone());
        }
    }
    fs::create_dir_all(mirror)?;
    fs::create_dir_all(cache)?;
    sync_dir(ws, mirror, cache, "", &required, &rewritten)?;
    for r in rewrites {
        write_rewrite(mirror, cache, tool_hash, r)?;
    }
    Ok(())
}

/// Sync one directory level. Recurses into a directory that is required (it
/// holds a rewrite) OR that is already a real directory in the mirror (an
/// earlier run's rewrite lives under it and its symlinks may be stale).
fn sync_dir(
    ws: &Path,
    mirror: &Path,
    cache: &Path,
    rel: &str,
    required: &BTreeSet<String>,
    rewritten: &BTreeMap<&str, &Rewrite>,
) -> io::Result<()> {
    let mirror_dir = join(mirror, rel);
    ensure_real_dir(&mirror_dir)?;
    let ws_dir = join(ws, rel);
    let mut wanted: BTreeSet<String> = BTreeSet::new();
    for entry in fs::read_dir(&ws_dir)? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().into_owned();
        if rel.is_empty() && SKIP_AT_ROOT.contains(&name.as_str()) {
            continue;
        }
        wanted.insert(name.clone());
        let child_rel = if rel.is_empty() {
            name.clone()
        } else {
            format!("{rel}/{name}")
        };
        let child_mirror = mirror_dir.join(&name);
        if rewritten.contains_key(child_rel.as_str()) {
            continue; // written as a real file below
        }
        // This unit does NOT rewrite this file in this run. If an earlier run
        // did, the mirror still holds that run's bytes -- so the stale rewrite
        // is replaced by the symlink below and its cache stamp goes with it.
        //
        // Leaving it was a real defect, measured 2026-09-03 on the probe: make
        // one file unparseable and the wrapper honestly records it in
        // `unreached_files`, but rustc never sees the broken bytes because the
        // mirror still holds the last rewrite -- the instrumented build exits 0
        // over source a plain build rejects with "unclosed delimiter". Nothing
        // is un-instrumented by dropping the stamp: a file this run DOES
        // rewrite took the `continue` above and is written by `write_rewrite`.
        let stamp = cache.join(sha256::hex(child_rel.as_bytes()));
        if stamp.exists() {
            fs::remove_file(&stamp)?;
        }
        let is_dir = entry.file_type()?.is_dir();
        let already_real_dir = matches!(fs::symlink_metadata(&child_mirror), Ok(m) if m.is_dir());
        if is_dir && (required.contains(&child_rel) || already_real_dir) {
            sync_dir(ws, mirror, cache, &child_rel, required, rewritten)?;
        } else {
            ensure_symlink(&join(ws, &child_rel), &child_mirror)?;
        }
    }
    // A source file deleted from the workspace must not linger in the mirror.
    for entry in fs::read_dir(&mirror_dir)? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().into_owned();
        if !wanted.contains(&name) {
            remove_any(&mirror_dir.join(&name))?;
        }
    }
    Ok(())
}

fn ensure_real_dir(path: &Path) -> io::Result<()> {
    match fs::symlink_metadata(path) {
        Ok(m) if m.is_dir() => Ok(()),
        Ok(_) => {
            // A symlink (or file) where a real directory is now needed: the
            // upgrade that makes a rewrite under it possible.
            fs::remove_file(path)?;
            fs::create_dir(path)
        }
        Err(_) => fs::create_dir_all(path),
    }
}

fn ensure_symlink(target: &Path, link: &Path) -> io::Result<()> {
    if let Ok(existing) = fs::read_link(link) {
        if existing == target {
            return Ok(());
        }
    }
    if fs::symlink_metadata(link).is_ok() {
        remove_any(link)?;
    }
    symlink(target, link)
}

fn remove_any(path: &Path) -> io::Result<()> {
    match fs::symlink_metadata(path) {
        Ok(m) if m.is_dir() => fs::remove_dir_all(path),
        Ok(_) => fs::remove_file(path),
        Err(_) => Ok(()),
    }
}

/// Write one rewritten file unless the cache says the identical bytes are
/// already there. Skipping is not an optimisation: rewriting would move the
/// mtime and make cargo rebuild a unit nothing changed in.
fn write_rewrite(mirror: &Path, cache: &Path, tool_hash: &str, r: &Rewrite) -> io::Result<()> {
    let key = format!("{tool_hash}:{}", r.source_hash);
    let stamp = cache.join(sha256::hex(r.rel.as_bytes()));
    let dest = join(mirror, &r.rel);
    let fresh = matches!(fs::read_to_string(&stamp), Ok(s) if s == key)
        && matches!(fs::symlink_metadata(&dest), Ok(m) if m.is_file());
    if fresh {
        return Ok(());
    }
    if fs::symlink_metadata(&dest).is_ok() {
        remove_any(&dest)?;
    }
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent)?;
    }
    let tmp = dest.with_extension("rs.sensorium-tmp");
    fs::write(&tmp, r.content.as_bytes())?;
    fs::rename(&tmp, &dest)?;
    fs::write(&stamp, key.as_bytes())?;
    Ok(())
}

fn join(base: &Path, rel: &str) -> PathBuf {
    if rel.is_empty() {
        base.to_path_buf()
    } else {
        base.join(rel)
    }
}

/// An exclusive `flock(2)` on one unit's lock file, held across that unit's
/// mirror update and its rustc run (plan decision D2).
///
/// No timeout and no staleness rule, because neither is needed and both were
/// wrong in rung 1: `flock` is released by the KERNEL when the holding
/// process dies, so a killed wrapper cannot wedge a build, and a legitimate
/// update that takes longer than any timeout would have been raided by the
/// timeout instead of waited for (findings §5.12). The only contention is two
/// cargos building the same unit at once, which is exactly what this
/// serialises.
pub struct Lock {
    file: fs::File,
}

impl Lock {
    /// Take the lock, waiting for as long as it takes.
    ///
    /// # Errors
    /// If the lock file cannot be opened, or `flock` fails for a reason other
    /// than being interrupted by a signal.
    pub fn acquire(path: &Path) -> io::Result<Lock> {
        let file = open_lock_file(path)?;
        loop {
            // SAFETY: `file` owns an open file descriptor for the whole call.
            // `flock` takes no pointer, mutates nothing this process owns, and
            // reports failure as -1 with `errno` set.
            let rc = unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX) };
            if rc == 0 {
                return Ok(Lock { file });
            }
            let err = io::Error::last_os_error();
            if err.kind() != io::ErrorKind::Interrupted {
                return Err(err);
            }
        }
    }

    /// Take the lock if it is free right now. `Ok(None)` means another open
    /// file description holds it.
    ///
    /// Test-only, and marked so rather than left in the production API: the
    /// wrapper must never poll for this lock — polling is how rung 1's lock
    /// grew a timeout and then a staleness rule that raided live holders
    /// (findings §5.12). The tests need it to observe a held lock without
    /// blocking on it.
    ///
    /// # Errors
    /// If the lock file cannot be opened, or `flock` fails for a reason other
    /// than the lock being held.
    #[cfg(test)]
    pub fn try_acquire(path: &Path) -> io::Result<Option<Lock>> {
        let file = open_lock_file(path)?;
        // SAFETY: as above; `LOCK_NB` only changes whether it blocks.
        let rc = unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) };
        if rc == 0 {
            return Ok(Some(Lock { file }));
        }
        let err = io::Error::last_os_error();
        if err.kind() == io::ErrorKind::WouldBlock {
            return Ok(None);
        }
        Err(err)
    }
}

fn open_lock_file(path: &Path) -> io::Result<fs::File> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::OpenOptions::new()
        .create(true)
        .read(true)
        .write(true)
        .truncate(false)
        .open(path)
}

impl Drop for Lock {
    fn drop(&mut self) {
        // Closing the descriptor would release it anyway; unlocking first says
        // so in the code rather than in a comment somewhere else.
        // SAFETY: `self.file` is still open here — `Drop` runs before its own
        // fields are dropped — and `flock` touches no memory.
        unsafe {
            libc::flock(self.file.as_raw_fd(), libc::LOCK_UN);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::{Command, Stdio};
    use std::time::{Duration, SystemTime};

    struct Tmp(PathBuf);

    impl Tmp {
        fn new(name: &str) -> Tmp {
            let base = std::env::temp_dir().join(format!(
                "sensorium-mirror-test-{}-{}-{name}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            fs::create_dir_all(&base).unwrap();
            Tmp(base)
        }
        fn p(&self, rel: &str) -> PathBuf {
            self.0.join(rel)
        }
        fn write(&self, rel: &str, content: &str) {
            let p = self.p(rel);
            fs::create_dir_all(p.parent().unwrap()).unwrap();
            fs::write(p, content).unwrap();
        }
    }

    impl Drop for Tmp {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn rewrite(rel: &str, content: &str, source: &str) -> Rewrite {
        Rewrite {
            rel: rel.to_owned(),
            content: content.to_owned(),
            source_hash: sha256::hex(source.as_bytes()),
        }
    }

    fn fixture(t: &Tmp) {
        t.write("ws/Cargo.toml", "[workspace]\n");
        t.write("ws/Cargo.lock", "lock\n");
        t.write("ws/a/Cargo.toml", "[package]\n");
        t.write("ws/a/src/lib.rs", "fn a() {}\n");
        t.write("ws/a/src/other.rs", "fn o() {}\n");
        t.write("ws/b/src/lib.rs", "fn b() {}\n");
        t.write("ws/target/junk", "should never be mirrored\n");
        fs::create_dir_all(t.p("ws/.git")).unwrap();
        t.write("ws/.git/HEAD", "ref: refs/heads/main\n");
    }

    fn run(t: &Tmp, rewrites: &[Rewrite], tool: &str) {
        materialise(&t.p("ws"), &t.p("mirror"), &t.p("cache"), tool, rewrites).unwrap();
    }

    #[test]
    fn only_directories_holding_a_rewrite_are_real() {
        let t = Tmp::new("shape");
        fixture(&t);
        run(
            &t,
            &[rewrite("a/src/lib.rs", "GUARDED\n", "fn a() {}\n")],
            "t1",
        );

        assert!(fs::symlink_metadata(t.p("mirror/a")).unwrap().is_dir());
        assert!(fs::symlink_metadata(t.p("mirror/a/src")).unwrap().is_dir());
        // b holds no rewrite, so it is ONE symlink, not a walked subtree.
        assert!(fs::symlink_metadata(t.p("mirror/b")).unwrap().is_symlink());
        assert_eq!(fs::read_link(t.p("mirror/b")).unwrap(), t.p("ws/b"));
        // Absolute, so the mirror is depth-independent.
        assert!(fs::read_link(t.p("mirror/Cargo.toml"))
            .unwrap()
            .is_absolute());
        assert_eq!(
            fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(),
            "GUARDED\n"
        );
        assert!(!fs::symlink_metadata(t.p("mirror/a/src/lib.rs"))
            .unwrap()
            .is_symlink());
        // A file beside it, untouched, is a symlink to the original.
        assert_eq!(
            fs::read_link(t.p("mirror/a/src/other.rs")).unwrap(),
            t.p("ws/a/src/other.rs")
        );
    }

    #[test]
    fn target_and_git_are_never_mirrored() {
        let t = Tmp::new("skip");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "G\n", "fn a() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/target")).is_err());
        assert!(fs::symlink_metadata(t.p("mirror/.git")).is_err());
    }

    /// A symlinked directory becomes real when a rewrite lands under it, and a
    /// directory that was made real stays real (rule 2) — while a FILE the unit
    /// no longer rewrites goes back to the original (rule 4).
    ///
    /// This test used to assert the opposite of that last line: that
    /// `a/src/lib.rs` still read the earlier run's `"A\n"`. That was rung 1's
    /// invariant, when one mirror was shared by every unit and a second unit's
    /// `materialise` had to not clobber the first's rewrites. Mirrors are per
    /// unit now (findings §5.22, plan decision D2), so two units never meet in
    /// one mirror and the only way a file can leave a rewrite set is that THIS
    /// unit stopped rewriting it — in which case keeping the old bytes is the
    /// defect, not the invariant.
    #[test]
    fn a_later_rewrite_upgrades_a_symlinked_directory() {
        let t = Tmp::new("upgrade");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/b")).unwrap().is_symlink());

        run(&t, &[rewrite("b/src/lib.rs", "B\n", "fn b() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/b/src")).unwrap().is_dir());
        assert_eq!(
            fs::read_to_string(t.p("mirror/b/src/lib.rs")).unwrap(),
            "B\n"
        );
        // Rule 2: the directory an earlier rewrite made real stays real, so a
        // later rewrite under it is still possible.
        assert!(fs::symlink_metadata(t.p("mirror/a/src")).unwrap().is_dir());
        // Rule 4: the file itself is the original again, and its stamp is gone.
        assert!(
            fs::symlink_metadata(t.p("mirror/a/src/lib.rs"))
                .unwrap()
                .is_symlink(),
            "a rewrite this unit no longer has must not survive as a real file"
        );
        assert_eq!(
            fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(),
            "fn a() {}\n"
        );
        assert!(!t.p("cache").join(sha256::hex(b"a/src/lib.rs")).exists());
    }

    #[test]
    fn an_unchanged_rewrite_is_not_touched_again() {
        let t = Tmp::new("idem");
        fixture(&t);
        let r = || rewrite("a/src/lib.rs", "A\n", "fn a() {}\n");
        run(&t, &[r()], "t1");
        let first = fs::metadata(t.p("mirror/a/src/lib.rs"))
            .unwrap()
            .modified()
            .unwrap();
        std::thread::sleep(Duration::from_millis(20));
        run(&t, &[r()], "t1");
        let second = fs::metadata(t.p("mirror/a/src/lib.rs"))
            .unwrap()
            .modified()
            .unwrap();
        assert_eq!(
            first, second,
            "an unchanged rewrite must not move its mtime"
        );
    }

    #[test]
    fn a_changed_source_rewrites_and_a_changed_tool_rewrites() {
        let t = Tmp::new("invalidate");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "v1")], "t1");
        run(&t, &[rewrite("a/src/lib.rs", "A2\n", "v2")], "t1");
        assert_eq!(
            fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(),
            "A2\n"
        );
        // Same source, new tool hash: the cache must NOT hold.
        run(&t, &[rewrite("a/src/lib.rs", "A3\n", "v2")], "t2");
        assert_eq!(
            fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(),
            "A3\n"
        );
    }

    #[test]
    fn a_file_deleted_from_the_workspace_leaves_the_mirror() {
        let t = Tmp::new("delete");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/a/src/other.rs")).is_ok());
        fs::remove_file(t.p("ws/a/src/other.rs")).unwrap();
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/a/src/other.rs")).is_err());
    }

    /// The defect this test was written for: a file that STOPS being rewritten
    /// must go back to being a symlink to the original, and must lose its cache
    /// stamp with it.
    ///
    /// A file leaves a unit's rewrite set when it stops parsing (the wrapper
    /// records it in `unreached_files` and instruments the rest of the unit) or
    /// when the module tree stops reaching it. Measured 2026-09-03 before the
    /// fix: the mirror kept the previous run's rewritten bytes, so an
    /// instrumented build of a workspace with an unparseable file exited **0**
    /// while a plain build of the same source failed with "this file contains
    /// an unclosed delimiter". A green build over bytes the user does not have
    /// is the one outcome this recorder must never produce.
    #[test]
    fn a_file_that_stops_being_rewritten_goes_back_to_the_original() {
        let t = Tmp::new("stale-rewrite");
        fixture(&t);
        // Run 1: `a/src/other.rs` is rewritten, and really is a real file.
        run(
            &t,
            &[
                rewrite("a/src/lib.rs", "A\n", "fn a() {}\n"),
                rewrite("a/src/other.rs", "REWRITTEN\n", "fn o() {}\n"),
            ],
            "t1",
        );
        let stamp = t.p("cache").join(sha256::hex(b"a/src/other.rs"));
        assert!(!fs::symlink_metadata(t.p("mirror/a/src/other.rs"))
            .unwrap()
            .is_symlink());
        assert!(
            stamp.exists(),
            "run 1 must leave a cache stamp to invalidate"
        );

        // The source changes to something the transformer cannot handle, so
        // run 2 rewrites the crate root and NOT this file.
        t.write("ws/a/src/other.rs", "fn o( {\n");
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");

        // The mirror entry is the symlink again, the stale bytes are gone, and
        // what rustc reads through it is the broken source it must reject.
        let meta = fs::symlink_metadata(t.p("mirror/a/src/other.rs")).unwrap();
        assert!(
            meta.is_symlink(),
            "a file that stopped being rewritten must be a symlink again"
        );
        assert_eq!(
            fs::read_link(t.p("mirror/a/src/other.rs")).unwrap(),
            t.p("ws/a/src/other.rs")
        );
        assert_eq!(
            fs::read_to_string(t.p("mirror/a/src/other.rs")).unwrap(),
            "fn o( {\n",
            "the mirror must read the ORIGINAL, never the previous run's rewrite"
        );
        assert!(
            !stamp.exists(),
            "the cache stamp must go with the rewrite, or the next run reinstates it"
        );
        // The file that IS still rewritten is untouched by any of this.
        assert_eq!(
            fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(),
            "A\n"
        );
    }

    #[test]
    fn a_file_added_to_an_already_real_directory_appears() {
        let t = Tmp::new("add");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");
        t.write("ws/a/src/added.rs", "fn added() {}\n");
        // A later run rewrites something else; a/src is not required by it, but
        // it is already a real directory, so it must be re-synced.
        run(&t, &[rewrite("b/src/lib.rs", "B\n", "fn b() {}\n")], "t1");
        assert_eq!(
            fs::read_link(t.p("mirror/a/src/added.rs")).unwrap(),
            t.p("ws/a/src/added.rs")
        );
    }

    #[test]
    fn the_lock_is_exclusive_within_one_process_and_released_on_drop() {
        let t = Tmp::new("lock");
        let path = t.p("unit.lock");
        let held = Lock::acquire(&path).unwrap();
        // A SECOND open of the same file: `flock` is per open file description,
        // so this is the same test another process would run.
        assert!(
            Lock::try_acquire(&path).unwrap().is_none(),
            "a held lock must not be handed out twice"
        );
        drop(held);
        assert!(Lock::try_acquire(&path).unwrap().is_some());
    }

    #[test]
    fn two_units_locks_do_not_contend() {
        let t = Tmp::new("per-unit");
        let a = Lock::acquire(&t.p("aaaa.lock")).unwrap();
        let b = Lock::try_acquire(&t.p("bbbb.lock")).unwrap();
        assert!(b.is_some(), "per-unit locks must be independent");
        drop((a, b));
    }

    /// The kernel releases an `flock` when the holding process dies. This is
    /// the whole reason D2 needs no staleness rule, and it is a property of the
    /// kernel, so it is tested against a real killed process rather than argued.
    #[test]
    fn a_lock_held_by_a_killed_process_is_released_by_the_kernel() {
        let t = Tmp::new("lock-death");
        let path = t.p("unit.lock");
        let ready = t.p("held");
        let mut child = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "mirror::tests::hold_a_lock_when_the_environment_asks_for_it",
            ])
            .env("SENSORIUM_TEST_LOCK", &path)
            .env("SENSORIUM_TEST_LOCK_READY", &ready)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("re-invoke this test binary as the lock holder");

        let deadline = SystemTime::now() + Duration::from_secs(30);
        while !ready.exists() {
            assert!(
                SystemTime::now() < deadline,
                "the holder never reported that it had the lock"
            );
            std::thread::sleep(Duration::from_millis(5));
        }
        assert!(
            Lock::try_acquire(&path).unwrap().is_none(),
            "another process holds it, so this must not succeed"
        );

        child.kill().unwrap();
        child.wait().unwrap();

        let deadline = SystemTime::now() + Duration::from_secs(30);
        loop {
            if Lock::try_acquire(&path).unwrap().is_some() {
                break;
            }
            assert!(
                SystemTime::now() < deadline,
                "the kernel did not release the dead holder's lock"
            );
            std::thread::sleep(Duration::from_millis(5));
        }
    }

    /// Not a test of anything on its own: the helper the test above re-invokes.
    /// Without the environment it does nothing, so the ordinary run is a no-op.
    #[test]
    fn hold_a_lock_when_the_environment_asks_for_it() {
        let (Ok(path), Ok(ready)) = (
            std::env::var("SENSORIUM_TEST_LOCK"),
            std::env::var("SENSORIUM_TEST_LOCK_READY"),
        ) else {
            return;
        };
        let _held = Lock::acquire(Path::new(&path)).unwrap();
        fs::write(&ready, b"held").unwrap();
        // Hold it until the parent kills us -- or, if the parent died first
        // (which is what a FAILING run above looks like), until we are
        // reparented to init. A fixed sleep would leave a process holding a
        // lock for a minute after every failure, including every mutation run.
        let deadline = SystemTime::now() + Duration::from_secs(60);
        while SystemTime::now() < deadline {
            // SAFETY: `getppid` takes no arguments, touches no memory, and
            // cannot fail.
            if unsafe { libc::getppid() } == 1 {
                return;
            }
            std::thread::sleep(Duration::from_millis(20));
        }
    }
}
