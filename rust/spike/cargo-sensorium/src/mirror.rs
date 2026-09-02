//! The workspace-root mirror at `<target>/sensorium/mirror/`.
//!
//! Cargo hands the wrapper a RELATIVE crate root and cwd = the workspace root
//! (verified: see the task report's captured argv). So an instrumented unit is
//! compiled by chdir'ing into a tree that looks exactly like the workspace at
//! every path rustc can reach, with the rewritten `.rs` files materialised and
//! everything else an absolute symlink to the real thing. That is what keeps
//! `file!()`, panic locations, debuginfo and dep-info at workspace-relative
//! paths (E7), and dep-info workspace-relative is what keeps cargo's freshness
//! working (E8).
//!
//! Three rules the code exists to enforce:
//!
//! 1. **Real directories only where a rewrite lives.** Everything else at each
//!    level is one symlink, so the mirror is a handful of inodes, not a copy.
//! 2. **Real directories are never downgraded.** Unit B must not replace the
//!    real `mirror/app/src` that unit A created with a symlink -- that would
//!    silently un-instrument A. Directories only ever go symlink -> real.
//! 3. **Idempotent.** A rewrite whose source and tool hash are unchanged is not
//!    written again, so its mtime does not move and cargo stays incurious.
//!
//! Cargo runs the wrapper `-j N` in parallel, so the structural update is
//! serialised by a lock directory (`fs::create_dir` is atomic on every
//! filesystem we care about).

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io;
use std::os::unix::fs::symlink;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

use crate::sha256;

/// Never mirrored: `target/` is where the mirror itself lives (mirroring it
/// would be a cycle) and `.git/` is large and never read by rustc.
const SKIP_AT_ROOT: &[&str] = &["target", ".git"];

/// One file the wrapper rewrote: where it came from and what it now says.
pub struct Rewrite {
    /// Workspace-relative path, `/`-separated.
    pub rel: String,
    pub content: String,
    /// sha256 of the ORIGINAL bytes: half the cache key.
    pub source_hash: String,
}

/// Materialise `rewrites` into `mirror`, mirroring `ws`.
///
/// `tool_hash` is the other half of the cache key: a new transformer must
/// invalidate every cached rewrite even where the source did not change.
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
    let rewritten: BTreeMap<&str, &Rewrite> = rewrites.iter().map(|r| (r.rel.as_str(), r)).collect();
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
/// holds a rewrite) OR that is already a real directory in the mirror (a
/// previous unit's rewrite lives under it and its symlinks may be stale).
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
        // A rewrite materialised by an EARLIER unit. This directory is being
        // re-synced only because it is already real, and the current unit knows
        // nothing about this file -- symlinking over it would silently
        // un-instrument the other unit. The cache stamp is the record that we
        // put a real file there on purpose.
        if cache.join(sha256::hex(child_rel.as_bytes())).exists() {
            continue;
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
            // upgrade that makes a second unit's rewrite possible.
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

/// A lock directory held for the length of one mirror update.
///
/// `fs::create_dir` is the atomic test-and-set. A lock older than
/// [`STALE_AFTER`] is assumed to belong to a killed wrapper and is broken --
/// a spike must not deadlock a build because a process died.
pub struct Lock {
    path: PathBuf,
}

const STALE_AFTER: Duration = Duration::from_secs(120);

impl Lock {
    /// # Errors
    /// Only if the lock cannot be taken within `timeout`.
    pub fn acquire(path: &Path, timeout: Duration) -> io::Result<Lock> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let deadline = SystemTime::now() + timeout;
        loop {
            match fs::create_dir(path) {
                Ok(()) => {
                    return Ok(Lock {
                        path: path.to_path_buf(),
                    })
                }
                Err(e) if e.kind() == io::ErrorKind::AlreadyExists => {}
                Err(e) => return Err(e),
            }
            if let Ok(age) = fs::metadata(path).and_then(|m| m.modified()) {
                if SystemTime::now()
                    .duration_since(age)
                    .is_ok_and(|d| d > STALE_AFTER)
                {
                    let _ = fs::remove_dir(path);
                    continue;
                }
            }
            if SystemTime::now() > deadline {
                return Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    format!("mirror lock at {} held too long", path.display()),
                ));
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }
}

impl Drop for Lock {
    fn drop(&mut self) {
        let _ = fs::remove_dir(&self.path);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
        run(&t, &[rewrite("a/src/lib.rs", "GUARDED\n", "fn a() {}\n")], "t1");

        assert!(fs::symlink_metadata(t.p("mirror/a")).unwrap().is_dir());
        assert!(fs::symlink_metadata(t.p("mirror/a/src")).unwrap().is_dir());
        // b holds no rewrite, so it is ONE symlink, not a walked subtree.
        assert!(fs::symlink_metadata(t.p("mirror/b")).unwrap().is_symlink());
        assert_eq!(fs::read_link(t.p("mirror/b")).unwrap(), t.p("ws/b"));
        // Absolute, so the mirror is depth-independent.
        assert!(fs::read_link(t.p("mirror/Cargo.toml")).unwrap().is_absolute());
        // The rewrite is a real file with the new bytes.
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

    #[test]
    fn a_second_unit_upgrades_a_symlinked_directory_without_losing_the_first() {
        let t = Tmp::new("upgrade");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/b")).unwrap().is_symlink());

        // A different unit, rewriting under b/. This is the pinned behaviour:
        // b must become a real directory AND a's rewrite must survive.
        run(&t, &[rewrite("b/src/lib.rs", "B\n", "fn b() {}\n")], "t1");
        assert!(fs::symlink_metadata(t.p("mirror/b/src")).unwrap().is_dir());
        assert_eq!(fs::read_to_string(t.p("mirror/b/src/lib.rs")).unwrap(), "B\n");
        assert_eq!(fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(), "A\n");
        assert!(!fs::symlink_metadata(t.p("mirror/a/src/lib.rs"))
            .unwrap()
            .is_symlink());
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
        assert_eq!(first, second, "an unchanged rewrite must not move its mtime");
    }

    #[test]
    fn a_changed_source_rewrites_and_a_changed_tool_rewrites() {
        let t = Tmp::new("invalidate");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "v1")], "t1");
        run(&t, &[rewrite("a/src/lib.rs", "A2\n", "v2")], "t1");
        assert_eq!(fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(), "A2\n");
        // Same source, new tool hash: the cache must NOT hold.
        run(&t, &[rewrite("a/src/lib.rs", "A3\n", "v2")], "t2");
        assert_eq!(fs::read_to_string(t.p("mirror/a/src/lib.rs")).unwrap(), "A3\n");
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

    #[test]
    fn a_file_added_to_an_already_real_directory_appears() {
        let t = Tmp::new("add");
        fixture(&t);
        run(&t, &[rewrite("a/src/lib.rs", "A\n", "fn a() {}\n")], "t1");
        t.write("ws/a/src/added.rs", "fn added() {}\n");
        // A later unit rewrites something else entirely; a/src is not required
        // by it, but it is already a real directory, so it must be re-synced.
        run(&t, &[rewrite("b/src/lib.rs", "B\n", "fn b() {}\n")], "t1");
        assert_eq!(
            fs::read_link(t.p("mirror/a/src/added.rs")).unwrap(),
            t.p("ws/a/src/added.rs")
        );
    }

    #[test]
    fn the_lock_is_exclusive_and_released_on_drop() {
        let t = Tmp::new("lock");
        let path = t.p("lock.d");
        let held = Lock::acquire(&path, Duration::from_millis(50)).unwrap();
        assert!(Lock::acquire(&path, Duration::from_millis(20)).is_err());
        drop(held);
        assert!(Lock::acquire(&path, Duration::from_millis(50)).is_ok());
    }
}
