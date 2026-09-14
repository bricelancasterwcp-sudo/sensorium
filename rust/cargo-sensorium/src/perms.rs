//! 0700 and 0600: the two numbers everything this driver creates is created
//! WITH, and the three helpers that apply them.
//!
//! Every file and directory this recorder writes holds one of three things
//! out of somebody else's program -- the whole environment (`<pid>.proc.json`
//! and the trace's `env`), captured return values and error messages (the
//! spools, the trace), or the recorded process's full argv
//! (`<pid>.runner.json`), which is where a secret typed on a command line
//! ends up. All of them were 0644 in a 0755 directory until this slice, so a
//! recording made on a shared box was readable by every account on it.
//!
//! **At creation, never by a later `chmod`.** A file created 0644 and
//! tightened a moment later is readable for that moment, and the moment is
//! exactly when it is being filled with what it holds. `sensorium-rt`'s own
//! writer takes the same position (`spool.rs`), and these are its spellings
//! for the driver's side of the same store.
//!
//! The mode applies only to what these CREATE. A directory that already
//! exists keeps the permissions its owner chose -- a person who pointed
//! `SENSORIUM_DIR` at a directory of their own is not overruled here.

use std::fs::{File, OpenOptions};
use std::io;
use std::path::Path;

/// `create_dir_all`, but 0700 on every level it creates.
pub fn dir_all(dir: &Path) -> io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        std::fs::DirBuilder::new()
            .recursive(true)
            .mode(0o700)
            .create(dir)
    }
    #[cfg(not(unix))]
    {
        std::fs::create_dir_all(dir)
    }
}

/// A file created 0600, truncating whatever was there.
///
/// A file already at the path keeps the mode it has: `open` sets the mode of
/// a file it CREATES and nothing else, which is why every caller writes
/// through a fresh per-pid temporary and renames.
pub fn create(path: &Path) -> io::Result<File> {
    options().write(true).create(true).truncate(true).open(path)
}

/// The same, but refusing a path that already exists -- the "I am the one who
/// made this" a temporary needs before it is filled with 32 bytes of key.
pub fn create_new(path: &Path) -> io::Result<File> {
    options().write(true).create_new(true).open(path)
}

fn options() -> OpenOptions {
    let mut opts = OpenOptions::new();
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        opts.mode(0o600);
    }
    opts
}

#[cfg(test)]
mod tests {
    use super::*;

    use std::os::unix::fs::PermissionsExt;
    use std::path::PathBuf;

    struct Dir(PathBuf);

    impl Dir {
        fn new(name: &str) -> Dir {
            let base = std::env::temp_dir().join(format!(
                "sensorium-perms-{}-{}-{name}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(&base).unwrap();
            Dir(base)
        }
    }

    impl Drop for Dir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn mode_of(path: &Path) -> u32 {
        std::fs::metadata(path).unwrap().permissions().mode() & 0o7777
    }

    /// EVERY level, not just the leaf: the driver's spool path is three
    /// directories deep under a target directory that may hold none of them,
    /// and a 0755 parent of a 0700 directory still lists nothing but still
    /// tells a reader the recording happened.
    #[test]
    fn dir_all_creates_every_level_it_makes_at_0700() {
        let d = Dir::new("dirs");
        let leaf = d.0.join("sensorium/spool/20260101-000000-000000");
        dir_all(&leaf).unwrap();
        assert_eq!(mode_of(&leaf), 0o700);
        assert_eq!(mode_of(&d.0.join("sensorium/spool")), 0o700);
        assert_eq!(mode_of(&d.0.join("sensorium")), 0o700);
        // Idempotent, and it does not touch a directory that already exists.
        dir_all(&leaf).unwrap();
        assert_eq!(mode_of(&leaf), 0o700);
    }

    #[test]
    fn a_created_file_is_0600_and_create_new_refuses_an_existing_one() {
        let d = Dir::new("files");
        let path = d.0.join("f");
        create(&path).unwrap();
        assert_eq!(mode_of(&path), 0o600);
        // Truncating is the point of `create`; `create_new` is the refusal.
        create(&path).unwrap();
        let err = create_new(&path).unwrap_err();
        assert_eq!(err.kind(), io::ErrorKind::AlreadyExists);

        let fresh = d.0.join("g");
        create_new(&fresh).unwrap();
        assert_eq!(mode_of(&fresh), 0o600);
    }
}
