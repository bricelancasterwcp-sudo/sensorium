//! The store's `redaction.key`: read it, or mint it once, and never fail.
//!
//! The runtime deliberately does neither (`sensorium-rt/src/redact.rs`, "THE
//! KEY"): creating a key means a directory, a temporary, a link and a race,
//! and the runtime is linked into somebody else's program. The driver is the
//! process that owns the store, so the driver is where that work lives, and
//! `SENSORIUM_REDACT_KEY` is the one hop between them.
//!
//! This is `src/sensorium/redact.py::Key.load` / `.load_or_create` in Rust,
//! behaviour for behaviour: both languages write and read ONE
//! `<store>/redaction.key`, so a Python trace and a Rust trace of the same
//! box carry digests a reader can compare. A difference here is a store whose
//! two halves silently stop comparing, which is why the protocol below is
//! stated rather than reinvented.

use std::io::Read;
use std::path::{Path, PathBuf};

use sensorium_rt::redact::{Key, KEY_BYTES};

use crate::perms;

/// The key's name under the store root, the same name
/// `src/sensorium/redact.py` writes and reads.
pub const KEY_FILE: &str = "redaction.key";

/// Where 32 random bytes come from. `getrandom(2)` through the file
/// interface, which std reaches without a dependency and which this crate's
/// zero-dependency neighbours already set the tone for. A short read is
/// caught by `read_exact`, so a key is 32 bytes or it is a named failure.
const URANDOM: &str = "/dev/urandom";

/// The key at `<root>/redaction.key`, if there is one.
///
/// Never creates, never fails, and SAYS NOTHING when there is no key. A
/// store with no key file is an ordinary state for this door -- the
/// standalone `cargo sensorium convert` reads a spool somebody else recorded,
/// and a key minted at CONVERSION time would take digests nothing was ever
/// recorded under. What an unkeyed conversion produces already says so in the
/// place a reader will meet it: the trace's `redaction.keyed` is false and
/// `info` prints `UNKEYED (no redaction.key in the store)`. A line on stderr
/// here would fire on every conversion of a modern spool, whose key this
/// function is not even consulted for.
pub fn load(root: &Path) -> Key {
    read(root).key
}

/// The key at `<root>/redaction.key`, creating it once if it is not there.
///
/// Published BY CONTENT, never by an empty file filled in a moment later
/// (ruling R15): 32 bytes go into a private `redaction.key.<pid>.tmp`, are
/// written whole and fsynced, and only then does `hard_link` put the finished
/// file at its name. An `O_EXCL` open on the final name would leave it
/// visible at 0 bytes for as long as the write takes -- a concurrent recorder
/// arriving in that window reads an empty file and records unkeyed, and a
/// process killed in it leaves a 0-byte key that silently unkeys the store
/// until a human deletes it. Linking can do neither: the name appears with
/// all 32 bytes behind it or not at all.
///
/// Never fails, on any path. A store that cannot be keyed still records --
/// the names are still redacted, the header says `keyed: false`, and the one
/// line this prints says which file was not there and why. Unlike [`load`],
/// an unkeyed result HERE is a failure and not a state: this door was asked
/// to make the file and could not.
pub fn load_or_create(root: &Path) -> Key {
    announce(root, read_or_create(root))
}

/// The 64-character form `SENSORIUM_REDACT_KEY` carries, or `None` when there
/// is no key and the recorded process is to be told nothing.
///
/// A thin pass to the runtime's own formatter on purpose: the driver spells
/// every part of key handling through this module, and the hex is the runtime
/// crate's because the runtime is what parses it back.
#[must_use]
pub fn to_hex(key: &Key) -> Option<String> {
    key.to_hex()
}

/// A key and, when there is none, the sentence saying why.
struct Outcome {
    key: Key,
    problem: Option<String>,
}

impl Outcome {
    fn keyed(material: &[u8]) -> Outcome {
        Outcome {
            key: Key::from_bytes(material),
            problem: None,
        }
    }

    fn unkeyed(problem: String) -> Outcome {
        Outcome {
            key: Key::from_hex(None),
            problem: Some(problem),
        }
    }
}

/// ONE line, on the way out of [`load_or_create`], and only when there is no
/// key. A driver that said nothing would leave a store whose digests are all
/// absent with nothing anywhere explaining it; a driver that said it per
/// recorded process would say it once per pid of a `cargo test`.
fn announce(root: &Path, outcome: Outcome) -> Key {
    if let Some(problem) = &outcome.problem {
        eprintln!(
            "sensorium: no redaction key at {} ({problem}); digests will be absent",
            key_path(root).display()
        );
    }
    outcome.key
}

fn key_path(root: &Path) -> PathBuf {
    root.join(KEY_FILE)
}

/// `<root>/redaction.key`'s 32 bytes, or the reason there are none.
fn read(root: &Path) -> Outcome {
    let path = key_path(root);
    let material = match std::fs::read(&path) {
        Ok(bytes) => bytes,
        Err(e) => return Outcome::unkeyed(e.to_string()),
    };
    if material.len() != KEY_BYTES {
        return Outcome::unkeyed(format!(
            "the file is {} bytes, expected {KEY_BYTES}",
            material.len()
        ));
    }
    Outcome::keyed(&material)
}

fn read_or_create(root: &Path) -> Outcome {
    // 0700, and before the read: the first recording into a fresh
    // `SENSORIUM_DIR` would otherwise be unkeyed for want of a directory. A
    // failure here is not reported -- the open below reports it, with the
    // name of the file a reader would go looking for.
    let _ = perms::dir_all(root);
    let path = key_path(root);
    // A key that is already there is the answer, whatever it says. A readable
    // one is returned; an unreadable or wrong-sized one is the USER's file and
    // is never written over, because replacing it would invalidate every
    // digest already in the store.
    let existing = read(root);
    if existing.key.keyed() || path.exists() {
        return existing;
    }
    let material = match mint() {
        Ok(material) => material,
        Err(problem) => return Outcome::unkeyed(problem),
    };
    // Per pid, so two drivers minting at once cannot write into one another's
    // temporary. Removed on every path out.
    let tmp = root.join(format!("{KEY_FILE}.{}.tmp", std::process::id()));
    let outcome = match write_tmp(&tmp, &material) {
        Some(problem) => Outcome::unkeyed(problem),
        None => publish(root, &tmp, material),
    };
    // A leftover temporary is a second copy of 32 bytes nobody will ever read
    // again. Errors ignored: there is nothing useful to say about a file that
    // was already gone.
    let _ = std::fs::remove_file(&tmp);
    outcome
}

fn mint() -> Result<[u8; KEY_BYTES], String> {
    let mut material = [0u8; KEY_BYTES];
    std::fs::File::open(URANDOM)
        .and_then(|mut f| f.read_exact(&mut material))
        .map_err(|e| format!("cannot read {URANDOM}: {e}"))?;
    Ok(material)
}

/// All of `material` into a fresh `tmp`, fsynced and closed. The problem
/// sentence, or `None` when the file on disk is whole.
///
/// `sync_all` before the link, not after: the name is published by the link,
/// and a name that appears before its bytes are durable is the empty-key
/// hazard this protocol exists to avoid, one power cut further out.
fn write_tmp(tmp: &Path, material: &[u8; KEY_BYTES]) -> Option<String> {
    use std::io::Write;
    let write = || -> std::io::Result<()> {
        let mut f = perms::create_new(tmp)?;
        f.write_all(material)?;
        f.sync_all()
    };
    match write() {
        Ok(()) => None,
        Err(e) => Some(format!("cannot write {}: {e}", tmp.display())),
    }
}

/// `tmp`'s finished content at `<root>/redaction.key`, or the winner's file
/// re-read.
///
/// `rename` is the fallback for a filesystem with no hard links (many network
/// and container mounts): it is atomic by name too, but it OVERWRITES, so a
/// loser of the race would replace the winner's key and leave two recordings
/// with digests that no longer compare. Re-reading the file afterwards is
/// what makes that safe -- whoever wrote last, the material returned is the
/// material the file now HOLDS, so the trace and the store never disagree.
fn publish(root: &Path, tmp: &Path, material: [u8; KEY_BYTES]) -> Outcome {
    match std::fs::hard_link(tmp, key_path(root)) {
        Ok(()) => Outcome::keyed(&material),
        // Another writer got there between this one's existence check and
        // this link. Its file is the store's key, and this one adopts it.
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => read(root),
        Err(_) => match std::fs::rename(tmp, key_path(root)) {
            Ok(()) => read(root),
            Err(e) => Outcome::unkeyed(format!("cannot create it: {e}")),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    use std::os::unix::fs::PermissionsExt;
    use std::path::PathBuf;

    /// A private scratch directory, removed on drop.
    struct Dir(PathBuf);

    impl Dir {
        fn new(name: &str) -> Dir {
            let base = std::env::temp_dir().join(format!(
                "sensorium-key-{}-{}-{name}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::SystemTime::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            ));
            std::fs::create_dir_all(&base).unwrap();
            Dir(base)
        }

        fn root(&self) -> PathBuf {
            self.0.join("store")
        }
    }

    impl Drop for Dir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn mode_of(path: &std::path::Path) -> u32 {
        std::fs::metadata(path).unwrap().permissions().mode() & 0o7777
    }

    /// `load` answers the question "what does this store hold", and a store
    /// that holds no key is a fact, not a request to make one: the standalone
    /// `cargo sensorium convert` reads a spool somebody else recorded, and a
    /// key minted at conversion time would take digests nothing was recorded
    /// under.
    #[test]
    fn load_of_an_absent_file_is_unkeyed_and_creates_nothing() {
        let d = Dir::new("load-absent");
        let key = load(&d.root());
        assert!(!key.keyed());
        assert_eq!(key.key_id(), None);
        assert!(!d.root().exists(), "load created the store root");
    }

    /// The two doors differ in what they SAY, not only in what they make. An
    /// unkeyed `load` is an ordinary state -- `cargo sensorium convert` over a
    /// store nothing keyed has ever been recorded into -- and a line there
    /// would fire on every conversion of a modern spool, whose key `load` is
    /// not even consulted for. An unkeyed `load_or_create` is a failure: that
    /// door was asked to make the file.
    #[test]
    fn only_the_door_that_was_asked_to_make_the_key_reports_not_having_one() {
        let d = Dir::new("problem");
        assert!(read(&d.root()).problem.is_some(), "absent");
        assert!(read_or_create(&d.root()).problem.is_none(), "created");
        assert!(read(&d.root()).problem.is_none(), "present");
        std::fs::write(d.root().join(KEY_FILE), b"short").unwrap();
        let problem = read_or_create(&d.root()).problem.expect("wrong size");
        assert!(problem.contains("5 bytes"), "{problem}");
        assert!(problem.contains("expected 32"), "{problem}");
    }

    #[test]
    fn load_or_create_mints_a_32_byte_key_at_0600_under_a_0700_root() {
        let d = Dir::new("create");
        let key = load_or_create(&d.root());
        assert!(key.keyed());
        let path = d.root().join(KEY_FILE);
        assert_eq!(std::fs::read(&path).unwrap().len(), KEY_BYTES);
        assert_eq!(mode_of(&path), 0o600, "the key file");
        assert_eq!(mode_of(&d.root()), 0o700, "the store root");
        // The tmp is unlinked on every path: a leftover is a second copy of
        // 32 bytes nobody will ever read again.
        let leftovers: Vec<_> = std::fs::read_dir(d.root())
            .unwrap()
            .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
            .filter(|n| n != KEY_FILE)
            .collect();
        assert!(leftovers.is_empty(), "{leftovers:?}");
    }

    #[test]
    fn load_or_create_returns_the_same_key_the_second_time() {
        let d = Dir::new("idempotent");
        let first = load_or_create(&d.root());
        let bytes = std::fs::read(d.root().join(KEY_FILE)).unwrap();
        let second = load_or_create(&d.root());
        assert_eq!(first.key_id(), second.key_id());
        assert!(first.key_id().is_some());
        assert_eq!(std::fs::read(d.root().join(KEY_FILE)).unwrap(), bytes);
        assert_eq!(load(&d.root()).key_id(), first.key_id());
    }

    /// A file of the wrong size is the USER's file and is never written over:
    /// replacing it would invalidate every digest already in the store, and
    /// the recording that follows says `keyed: false` instead.
    #[test]
    fn a_key_file_that_is_not_32_bytes_is_unkeyed_and_is_never_overwritten() {
        let d = Dir::new("short");
        std::fs::create_dir_all(d.root()).unwrap();
        std::fs::write(d.root().join(KEY_FILE), b"seven!!").unwrap();
        let key = load_or_create(&d.root());
        assert!(!key.keyed());
        assert_eq!(
            std::fs::read(d.root().join(KEY_FILE)).unwrap(),
            b"seven!!".to_vec()
        );
    }

    /// The race `publish` exists for: another writer's key appeared at the
    /// name between this one's existence check and its own `hard_link`. The
    /// loser reads the WINNER's file, so both recordings' digests are taken
    /// under one key -- and the winner's bytes are still the ones on disk.
    ///
    /// Driven through `publish` directly rather than through two threads: the
    /// window is a few instructions wide, and a test that raced for it would
    /// pass by luck most runs and prove nothing on the rest.
    #[test]
    fn publish_hands_back_the_winners_key_when_the_name_was_taken() {
        let d = Dir::new("race");
        std::fs::create_dir_all(d.root()).unwrap();
        let winner = [7u8; KEY_BYTES];
        std::fs::write(d.root().join(KEY_FILE), winner).unwrap();

        let mine = [9u8; KEY_BYTES];
        let tmp = d.root().join("redaction.key.test.tmp");
        std::fs::write(&tmp, mine).unwrap();
        let out = publish(&d.root(), &tmp, mine);

        assert_eq!(
            out.key.key_id(),
            Key::from_bytes(&winner).key_id(),
            "the loser must adopt the winner's key, not its own"
        );
        assert_eq!(
            std::fs::read(d.root().join(KEY_FILE)).unwrap(),
            winner.to_vec(),
            "the loser must not overwrite the winner's file"
        );
        assert!(out.problem.is_none(), "{:?}", out.problem);
    }

    /// The hex is exactly the form `SENSORIUM_REDACT_KEY` promises, checked
    /// against the runtime's own parser rather than against this module's
    /// idea of one.
    #[test]
    fn to_hex_is_the_form_the_runtimes_own_parser_accepts() {
        let d = Dir::new("hex");
        let key = load_or_create(&d.root());
        let hex = to_hex(&key).expect("a minted key has a hex form");
        assert_eq!(hex.len(), 2 * KEY_BYTES);
        assert!(hex
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_uppercase()));
        assert_eq!(
            sensorium_rt::redact::Key::from_hex(Some(&hex)).key_id(),
            key.key_id()
        );
        assert_eq!(to_hex(&Key::from_hex(None)), None);
    }
}
