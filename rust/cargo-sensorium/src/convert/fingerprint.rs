//! Rolling blake2b-16 fingerprints over the causal-event stream.
//!
//! TRACE-FORMAT.md §7: `h.update(f"{file}\x1f{qualname}\x1f{kind}\n")` per
//! causal event (`CALL`, `RETURN`, `RAISE`; `HANDLED` never appears on a Rust
//! trace, rung 3's), where `file` is the **workspace-relative** path (D9) --
//! never `code_objects.file`, which is absolute. One [`Fingerprint`] per
//! `fingerprints`/`task_fingerprints` row, so a thread or task that ran no
//! causal event still has a `finish()`-able hasher: `hashlib.blake2b(b"",
//! digest_size=16).hexdigest()`.

use blake2::digest::consts::U16;
use blake2::{Blake2b, Digest};

type Blake2b16 = Blake2b<U16>;

/// A rolling fingerprint under construction: the hasher and the count of
/// updates fed to it (`n_events`, the row's own column).
pub struct Fingerprint {
    hasher: Blake2b16,
    n_events: u64,
}

impl Fingerprint {
    #[must_use]
    pub fn new() -> Fingerprint {
        Fingerprint {
            hasher: Blake2b16::new(),
            n_events: 0,
        }
    }

    /// One causal event: `CALL`, `RETURN` or `RAISE`.
    pub fn update(&mut self, file: &str, qualname: &str, kind: &str) {
        self.hasher.update(file.as_bytes());
        self.hasher.update(b"\x1f");
        self.hasher.update(qualname.as_bytes());
        self.hasher.update(b"\x1f");
        self.hasher.update(kind.as_bytes());
        self.hasher.update(b"\n");
        self.n_events += 1;
    }

    /// The stored `(hash, n_events)` pair, lower-case hex.
    #[must_use]
    pub fn finish(self) -> (String, u64) {
        let digest = self.hasher.finalize();
        (hex(&digest), self.n_events)
    }
}

impl Default for Fingerprint {
    fn default() -> Fingerprint {
        Fingerprint::new()
    }
}

fn hex(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The three pins (task-6-brief.md, computed 2026-09-02 with
    /// `hashlib.blake2b(digest_size=16)`): empty input, one CALL update, then a
    /// RETURN update on the same file/qualname.
    #[test]
    fn the_empty_fingerprint_matches_the_python_pin() {
        let (hash, n) = Fingerprint::new().finish();
        assert_eq!(hash, "cae66941d9efbd404e4d88758ea67670");
        assert_eq!(n, 0);
    }

    #[test]
    fn one_call_update_matches_the_python_pin() {
        let mut f = Fingerprint::new();
        f.update("crates/demo/src/lib.rs", "main", "CALL");
        let (hash, n) = f.finish();
        assert_eq!(hash, "f71e39f5d40e5af43313cbbfba9a01d2");
        assert_eq!(n, 1);
    }

    #[test]
    fn a_call_then_a_return_update_matches_the_python_pin() {
        let mut f = Fingerprint::new();
        f.update("crates/demo/src/lib.rs", "main", "CALL");
        f.update("crates/demo/src/lib.rs", "main", "RETURN");
        let (hash, n) = f.finish();
        assert_eq!(hash, "57227ad2c76269e0e899ed211a58ba96");
        assert_eq!(n, 2);
    }

    #[test]
    fn different_qualnames_produce_different_hashes() {
        let mut a = Fingerprint::new();
        a.update("f.rs", "one", "CALL");
        let mut b = Fingerprint::new();
        b.update("f.rs", "two", "CALL");
        assert_ne!(a.finish().0, b.finish().0);
    }
}
