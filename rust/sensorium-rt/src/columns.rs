//! Map an instrumented panic column back to the original source column.
//!
//! The transformer splices newline-free fragments, so `file!()` and `line!()`
//! stay put and a panic's line does too. A column moves when bytes were
//! inserted earlier on that same line. `Location::column()` is what
//! `panicked at` prints: a 1-based display column (tab width 4, the same
//! character widths rustc 1.96 uses). The transformer counts those widths
//! when it builds [`ColInsert`] rows, so this module only subtracts.
//!
//! A column strictly before an insertion is unchanged. The insertion's own
//! first column is the boundary: it, and every column inside the new text,
//! stays the instrumented column (a panic in the probe itself). A column at
//! or past the end of the new text moves by `added - removed` for each such
//! insertion. Insertions on other lines do not apply.

use std::io::Write;
use std::sync::Mutex;

use crate::ffi;

/// One newline-free splice on a line, in instrumented display columns.
///
/// `start` is the first instrumented column of the new text (1-based). The
/// new text occupies `added` columns. `removed` is the display width of the
/// original bytes it replaced; an insert has `removed == 0`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ColInsert {
    pub line: u32,
    pub start: u32,
    pub added: u32,
    pub removed: u32,
}

struct Registered {
    file: String,
    inserts: Vec<ColInsert>,
}

static MAP: Mutex<Vec<Registered>> = Mutex::new(Vec::new());

fn lock() -> std::sync::MutexGuard<'static, Vec<Registered>> {
    MAP.lock().unwrap_or_else(|poisoned| poisoned.into_inner())
}

/// Remember one file's insertions. A second registration of the same path is
/// ignored, so a duplicate `.init_array` cannot apply the shift twice. This
/// does not install the panic hook; the registration calls
/// [`ensure_panic_hook`] itself. Paths are the workspace-relative path the
/// transformer was given, which is what `Location::file()` prints.
pub fn register_columns(file: &str, inserts: &[ColInsert]) {
    let mut map = lock();
    if map.iter().any(|entry| entry.file == file) {
        return;
    }
    let mut rows = inserts.to_vec();
    rows.sort_by(|a, b| a.line.cmp(&b.line).then(a.start.cmp(&b.start)));
    map.push(Registered {
        file: file.to_owned(),
        inserts: rows,
    });
}

/// Install the panic hook if nothing has yet.
///
/// The column-map registration calls this from `.init_array`, before user
/// code, so a tier `off` build still maps columns. A recording `enter` calls
/// the same install when no registration did.
pub fn ensure_panic_hook() {
    crate::panic::install();
}

/// The original display column for an instrumented one, or `inst_col` when
/// this file was not registered. An absolute path matches a registered
/// relative path on a `/` boundary, and the other way round; an exact path
/// wins.
#[must_use]
pub fn original_column(file: &str, line: u32, inst_col: u32) -> u32 {
    let map = lock();
    let inserts = lookup(&map, file);
    original_column_in(inserts, line, inst_col)
}

/// [`original_column`] over an explicit row list. `inserts` for one line must
/// be sorted by `start` (registration sorts them).
#[must_use]
pub fn original_column_in(inserts: &[ColInsert], line: u32, inst_col: u32) -> u32 {
    let mut shift: i64 = 0;
    for ins in inserts.iter().filter(|ins| ins.line == line) {
        if inst_col < ins.start {
            break;
        }
        let end = ins.start.saturating_add(ins.added);
        // Inside the new text, including its first column. Earlier insertions
        // on the line are not subtracted: this column is not original text.
        if inst_col < end {
            return inst_col;
        }
        shift += i64::from(ins.added) - i64::from(ins.removed);
    }
    let mapped = i64::from(inst_col) - shift;
    if mapped < 1 {
        1
    } else if mapped > i64::from(u32::MAX) {
        u32::MAX
    } else {
        mapped as u32
    }
}

fn lookup<'a>(map: &'a [Registered], file: &str) -> &'a [ColInsert] {
    if let Some(hit) = map.iter().find(|entry| entry.file == file) {
        return &hit.inserts;
    }
    let mut best: &[ColInsert] = &[];
    let mut best_len = 0usize;
    for entry in map {
        let n = suffix_match_len(&entry.file, file);
        if n > best_len {
            best = &entry.inserts;
            best_len = n;
        }
    }
    best
}

/// How many bytes of the shorter path match, when one path is the other plus
/// a `/` boundary. Zero when they merely share a suffix with no slash.
fn suffix_match_len(registered: &str, file: &str) -> usize {
    if registered.len() < file.len()
        && file.as_bytes().get(file.len() - registered.len() - 1) == Some(&b'/')
        && file.ends_with(registered)
    {
        return registered.len();
    }
    if file.len() < registered.len()
        && registered.as_bytes().get(registered.len() - file.len() - 1) == Some(&b'/')
        && registered.ends_with(file)
    {
        return file.len();
    }
    0
}

/// Chain to `previous`. When the mapped column differs, capture what it wrote
/// to stderr and rewrite only the first `panicked at <file>:<line>:<col>`
/// column. Every other byte, including the message, the thread name, the note
/// and backtrace frames, is written back unchanged. When the column did not
/// move, `previous` is called directly so the bytes are the hook's own.
pub(crate) fn report(
    previous: &impl Fn(&std::panic::PanicHookInfo<'_>),
    info: &std::panic::PanicHookInfo<'_>,
) {
    let Some(at) = info.location() else {
        previous(info);
        return;
    };
    let from = at.column();
    let to = original_column(at.file(), at.line(), from);
    if from == to {
        previous(info);
        return;
    }
    let file = at.file();
    let line = at.line();
    match capture_stderr(|| previous(info)) {
        Some(buf) => {
            let rewritten = rewrite_panicked_at_column(&buf, file, line, from, to);
            write_all_fd(ffi::STDERR_FILENO, &rewritten);
        }
        // The redirect could not be set up. Print on the real stderr.
        None => previous(info),
    }
}

/// Replace the column in the first `panicked at <file>:<line>:<from>` whose
/// next byte is not a digit. Backtrace frames are `at <file>:<line>:<col>`
/// and are left alone. A missing needle returns `buf` unchanged.
#[must_use]
pub(crate) fn rewrite_panicked_at_column(
    buf: &[u8],
    file: &str,
    line: u32,
    from_col: u32,
    to_col: u32,
) -> Vec<u8> {
    if from_col == to_col {
        return buf.to_vec();
    }
    let needle = format!("panicked at {file}:{line}:{from_col}");
    let Some(at) = find_column(buf, needle.as_bytes()) else {
        return buf.to_vec();
    };
    let prefix = format!("panicked at {file}:{line}:");
    let mut out = Vec::with_capacity(buf.len() + 4);
    out.extend_from_slice(&buf[..at]);
    out.extend_from_slice(prefix.as_bytes());
    out.extend_from_slice(to_col.to_string().as_bytes());
    out.extend_from_slice(&buf[at + needle.len()..]);
    out
}

fn find_column(buf: &[u8], needle: &[u8]) -> Option<usize> {
    let mut start = 0;
    while start < buf.len() {
        let rel = find_subseq(&buf[start..], needle)?;
        let at = start + rel;
        let next = at + needle.len();
        if next >= buf.len() || !buf[next].is_ascii_digit() {
            return Some(at);
        }
        start = at + 1;
    }
    None
}

fn find_subseq(hay: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || hay.len() < needle.len() {
        return None;
    }
    hay.windows(needle.len()).position(|w| w == needle)
}

/// Run `body` with fd 2 pointing at a memfd, then restore it and return what
/// was written. `None` if the redirect could not be installed; `body` has not
/// run in that case. An empty buffer means the hook wrote somewhere other
/// than fd 2 (libtest's capture sink): the caller writes nothing, and that
/// sink already has the message.
fn capture_stderr(body: impl FnOnce()) -> Option<Vec<u8>> {
    // SAFETY: the name is a nul-terminated literal. `memfd_create` does not
    // retain it. `MFD_CLOEXEC` keeps the fd out of children.
    let mem = unsafe { ffi::memfd_create(c"sensorium".as_ptr().cast(), ffi::MFD_CLOEXEC) };
    if mem < 0 {
        return None;
    }
    // SAFETY: dup of a live stderr fd. A negative return is failure.
    let saved = unsafe { ffi::dup(ffi::STDERR_FILENO) };
    if saved < 0 {
        unsafe { ffi::close(mem) };
        return None;
    }
    // SAFETY: both fds are open. On failure, stderr is untouched.
    if unsafe { ffi::dup2(mem, ffi::STDERR_FILENO) } < 0 {
        unsafe {
            ffi::close(saved);
            ffi::close(mem);
        }
        return None;
    }
    struct Restore(i32);
    impl Drop for Restore {
        fn drop(&mut self) {
            // Flush while fd 2 still points at the memfd, then put the real
            // stderr back. The lock is taken only for the flush, after the
            // hook has returned it.
            let _ = std::io::stderr().flush();
            unsafe {
                ffi::dup2(self.0, ffi::STDERR_FILENO);
                ffi::close(self.0);
            }
        }
    }
    let restore = Restore(saved);
    body();
    drop(restore);
    // SAFETY: `mem` is the memfd just written. Rewind, then read until EOF.
    unsafe { ffi::lseek(mem, 0, ffi::SEEK_SET) };
    let mut buf = Vec::new();
    let mut tmp = [0u8; 8192];
    loop {
        // SAFETY: `tmp` is a live buffer of that length. `read` writes at most
        // that many bytes.
        let n = unsafe { ffi::read(mem, tmp.as_mut_ptr().cast(), tmp.len()) };
        if n < 0 {
            if std::io::Error::last_os_error().kind() == std::io::ErrorKind::Interrupted {
                continue;
            }
            break;
        }
        if n == 0 {
            break;
        }
        buf.extend_from_slice(&tmp[..n as usize]);
    }
    unsafe { ffi::close(mem) };
    Some(buf)
}

fn write_all_fd(fd: i32, mut buf: &[u8]) {
    while !buf.is_empty() {
        // SAFETY: `buf` is a live byte slice. `write` reads at most that many.
        let n = unsafe { ffi::write(fd, buf.as_ptr().cast(), buf.len()) };
        if n < 0 {
            if std::io::Error::last_os_error().kind() == std::io::ErrorKind::Interrupted {
                continue;
            }
            return;
        }
        if n == 0 {
            return;
        }
        buf = &buf[n as usize..];
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ins(line: u32, start: u32, added: u32, removed: u32) -> ColInsert {
        ColInsert {
            line,
            start,
            added,
            removed,
        }
    }

    /// A 6-column insertion at column 10. Before it: unchanged. The boundary
    /// is the insertion's first column and stays instrumented, as does every
    /// column of the new text. The first column after it moves back by 6.
    #[test]
    fn a_six_character_insertion_maps_back_to_the_original_column() {
        let rows = [ins(1, 10, 6, 0)];
        assert_eq!(original_column_in(&rows, 1, 9), 9, "before the insertion");
        assert_eq!(
            original_column_in(&rows, 1, 10),
            10,
            "boundary: the first column of the insertion stays"
        );
        assert_eq!(
            original_column_in(&rows, 1, 15),
            15,
            "inside the inserted text"
        );
        assert_eq!(
            original_column_in(&rows, 1, 16),
            10,
            "the first original column after the insertion"
        );
        assert_eq!(
            original_column_in(&rows, 1, 20),
            14,
            "further along, still minus 6"
        );
        assert_eq!(
            original_column_in(&rows, 2, 20),
            20,
            "a different line is untouched"
        );
    }

    /// A second insertion later on the line adds its own width. A column
    /// inside that second fragment does not subtract the earlier one.
    #[test]
    fn a_second_insertion_on_the_line_accumulates() {
        let rows = [ins(1, 10, 6, 0), ins(1, 20, 4, 0)];
        assert_eq!(original_column_in(&rows, 1, 19), 13);
        assert_eq!(
            original_column_in(&rows, 1, 20),
            20,
            "inside the second fragment: do not subtract the first"
        );
        assert_eq!(original_column_in(&rows, 1, 23), 23);
        assert_eq!(original_column_in(&rows, 1, 24), 14, "24 - 6 - 4");
    }

    /// A replacement shifts by `added - removed`, not by `added` alone.
    #[test]
    fn a_replacement_shifts_by_added_minus_removed() {
        // `std::thread::spawn` (18) replaced by `::sensorium_rt::spawn_child` (28).
        let rows = [ins(1, 1, 28, 18)];
        assert_eq!(original_column_in(&rows, 1, 1), 1, "inside the new text");
        assert_eq!(
            original_column_in(&rows, 1, 28),
            28,
            "last column of the new text"
        );
        assert_eq!(original_column_in(&rows, 1, 29), 19, "29 - (28 - 18)");
    }

    #[test]
    fn the_registered_path_matches_exactly_or_on_a_slash_boundary() {
        let path = "sensorium-colmap/probe-app/tests/e7_operand.rs";
        register_columns(path, &[ins(33, 13, 6, 0)]);
        // A second registration must not apply the 6 twice.
        register_columns(path, &[ins(33, 13, 6, 0), ins(33, 13, 6, 0)]);
        assert_eq!(original_column(path, 33, 30), 24);
        assert_eq!(
            original_column(&format!("/ws/{path}"), 33, 30),
            24,
            "an absolute path with this relative suffix"
        );
        assert_eq!(
            original_column("tests/e7_operand.rs", 33, 30),
            24,
            "a shorter path the registered one ends with"
        );
        assert_eq!(
            original_column("not-e7_operand.rs", 33, 30),
            30,
            "a shared suffix with no slash is not a match"
        );
        assert_eq!(original_column("other.rs", 33, 30), 30);
    }

    #[test]
    fn only_the_panicked_at_column_is_rewritten() {
        let buf = b"\nthread 'main' (7) panicked at src/a.rs:33:30:\n\
operand probe panic\n\
note: run with RUST_BACKTRACE=1 environment variable to display a backtrace\n   \
2: src/a.rs:33:30\n";
        let out = rewrite_panicked_at_column(buf, "src/a.rs", 33, 30, 24);
        let text = std::str::from_utf8(&out).expect("utf-8");
        assert!(text.starts_with('\n'), "the leading newline stays");
        assert!(text.contains("thread 'main' (7) panicked at src/a.rs:33:24:\n"));
        assert!(text.contains("operand probe panic\n"));
        assert!(text.contains("note: run with RUST_BACKTRACE=1"));
        assert!(
            text.contains("2: src/a.rs:33:30\n"),
            "a backtrace frame is not a panicked-at line: {text}"
        );
        assert_eq!(
            text.matches("src/a.rs:33:24").count(),
            1,
            "only the first panicked-at column moves"
        );
    }

    #[test]
    fn a_shorter_column_does_not_rewrite_a_longer_one() {
        let buf = b"panicked at src/a.rs:3:30:\npanicked at src/a.rs:3:3:\n";
        let out = rewrite_panicked_at_column(buf, "src/a.rs", 3, 3, 9);
        assert_eq!(
            std::str::from_utf8(&out).unwrap(),
            "panicked at src/a.rs:3:30:\npanicked at src/a.rs:3:9:\n"
        );
    }

    #[test]
    fn a_missing_needle_is_returned_unchanged() {
        let buf = b"thread 'main' panicked at somewhere else\n";
        assert_eq!(rewrite_panicked_at_column(buf, "src/a.rs", 1, 2, 4), buf);
    }
}
