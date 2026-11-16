//! Display columns for the panic-column map.
//!
//! rustc 1.96 prints `Location::column()` as a 1-based display column:
//! `1 + sum(char_width)` of the characters strictly before that byte on the
//! line. Tab is width 4. The control characters rustc draws as a visible
//! stand-in are width 1. Everything else is `unicode-width` 0.2.2, which is
//! the crate `rustc_span` uses, with `None` (a non-printing character) counted
//! as 1. For the ASCII prefixes this transformer emits, that width is the
//! byte length.
//!
//! Each row is in instrumented coordinates: a splice's `start` is the original
//! display column plus the net width of splices earlier on that line. The
//! registration itself is not a row. Its length depends on the rows, and
//! nothing panickable follows it.

use std::collections::HashMap;

use unicode_width::UnicodeWidthChar;

use crate::splice::{escape_string_literal, Kind, Splice};

/// Opening of the `.init_array` registration. Goldens strip from here through
/// the static's closing `};` before comparing bytes. The leading space keeps
/// it off a preceding `}`.
pub const COLUMN_MAP_PREFIX: &str =
    " #[used] #[link_section = \".init_array\"] static __SENSORIUM_COLMAP_INIT:";

/// One row of the map the registration will register. Widths, not bytes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct ColRow {
    pub line: u32,
    pub start: u32,
    pub added: u32,
    pub removed: u32,
}

/// Display width of one character, matching rustc 1.96 `char_width`.
pub(crate) fn char_width(ch: char) -> usize {
    match ch {
        '\t' => 4,
        // The control points rustc replaces before printing. Kept in step
        // with `rustc_span::char_width` (1.96.0). Newline and tab are not in
        // this list: tab is the arm above, and a newline never reaches here
        // because a splice that contains one is not a row.
        '\u{0000}' | '\u{0001}' | '\u{0002}' | '\u{0003}' | '\u{0004}' | '\u{0005}'
        | '\u{0006}' | '\u{0007}' | '\u{0008}' | '\u{000B}' | '\u{000C}' | '\u{000D}'
        | '\u{000E}' | '\u{000F}' | '\u{0010}' | '\u{0011}' | '\u{0012}' | '\u{0013}'
        | '\u{0014}' | '\u{0015}' | '\u{0016}' | '\u{0017}' | '\u{0018}' | '\u{0019}'
        | '\u{001A}' | '\u{001B}' | '\u{001C}' | '\u{001D}' | '\u{001E}' | '\u{001F}'
        | '\u{007F}' | '\u{202A}' | '\u{202B}' | '\u{202D}' | '\u{202E}' | '\u{2066}'
        | '\u{2067}' | '\u{2068}' | '\u{202C}' | '\u{2069}' => 1,
        _ => UnicodeWidthChar::width(ch).unwrap_or(1),
    }
}

pub(crate) fn display_width(s: &str) -> u32 {
    s.chars()
        .fold(0u32, |n, ch| n.saturating_add(char_width(ch) as u32))
}

/// 1-based display column of `byte`, or `None` when `byte` is not a character
/// boundary.
pub(crate) fn display_col_at(source: &str, byte: usize) -> Option<u32> {
    let head = source.get(..byte)?;
    let line_start = head.rfind('\n').map(|i| i + 1).unwrap_or(0);
    Some(1 + display_width(&head[line_start..]))
}

fn line_of(source: &str, byte: usize) -> u32 {
    match source.get(..byte) {
        Some(head) => 1 + head.bytes().filter(|b| *b == b'\n').count() as u32,
        None => 1,
    }
}

/// Rows for `splices`, which must already be in assemble order. A splice whose
/// text or replaced bytes contain a newline is skipped: the only such fragment
/// is the crate-root static's leading newline, and it adds a final line rather
/// than moving a column. [`Kind::ColMap`] is skipped so the registration is
/// not an input to itself.
pub(crate) fn rows_from_splices(source: &str, splices: &[Splice]) -> Vec<ColRow> {
    let mut net: HashMap<u32, i64> = HashMap::new();
    let mut rows = Vec::new();
    for s in splices {
        if matches!(s.kind, Kind::ColMap) {
            continue;
        }
        if s.text.contains('\n') || s.text.contains('\r') {
            continue;
        }
        let removed = if s.start == s.end {
            ""
        } else {
            match source.get(s.start..s.end) {
                Some(text) if !text.contains('\n') && !text.contains('\r') => text,
                _ => continue,
            }
        };
        let Some(orig) = display_col_at(source, s.start) else {
            continue;
        };
        let line = line_of(source, s.start);
        let extra = net.get(&line).copied().unwrap_or(0);
        let inst = i64::from(orig) + extra;
        if !(1..=i64::from(u32::MAX)).contains(&inst) {
            continue;
        }
        let added = display_width(&s.text);
        let removed_w = display_width(removed);
        if added == 0 && removed_w == 0 {
            continue;
        }
        rows.push(ColRow {
            line,
            start: inst as u32,
            added,
            removed: removed_w,
        });
        *net.entry(line).or_insert(0) += i64::from(added) - i64::from(removed_w);
    }
    rows
}

/// The newline-free `.init_array` item that registers `rows` for `file`.
/// `#[used]` is the stable attribute; `#[used(linker)]` is unstable on 1.96.
pub(crate) fn registration(file: &str, rows: &[ColRow]) -> String {
    let mut out = String::from(COLUMN_MAP_PREFIX);
    out.push_str(
        " unsafe extern \"C\" fn() = { unsafe extern \"C\" fn __sensorium_colmap_init() { \
         ::sensorium_rt::register_columns(\"",
    );
    out.push_str(&escape_string_literal(file));
    out.push_str("\", &[");
    for (i, row) in rows.iter().enumerate() {
        if i > 0 {
            out.push_str(", ");
        }
        out.push_str(&format!(
            "::sensorium_rt::ColInsert {{ line: {}, start: {}, added: {}, removed: {} }}",
            row.line, row.start, row.added, row.removed
        ));
    }
    out.push_str("]); ::sensorium_rt::ensure_panic_hook(); } __sensorium_colmap_init };");
    debug_assert!(!out.contains('\n') && !out.contains('\r'));
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::splice::Splice;

    fn splice(start: usize, end: usize, kind: Kind, text: &str) -> Splice {
        Splice {
            start,
            end,
            kind,
            seq: 0,
            text: text.to_owned(),
        }
    }

    #[test]
    fn display_columns_follow_rustc_not_bytes() {
        assert_eq!(char_width('\t'), 4);
        assert_eq!(char_width('π'), 1, "two UTF-8 bytes, width 1");
        assert_eq!(char_width('€'), 1);
        assert_eq!(char_width('😀'), 2, "four UTF-8 bytes, width 2");
        assert_eq!(display_col_at("\tlet", 1), Some(5), "one tab, then 'l'");
        assert_eq!(display_col_at("\t\tX", 2), Some(9), "two tabs");

        let pi = "let _ = \"π\";";
        let semi = pi.find(';').unwrap();
        assert_eq!(display_col_at(pi, semi), Some(12));
        assert_ne!(semi as u32 + 1, 12, "a byte column would count π as two");

        let face = "let _ = \"😀\";";
        let semi = face.find(';').unwrap();
        assert_eq!(display_col_at(face, semi), Some(13));
        assert_eq!(
            semi as u32 + 1,
            15,
            "the byte column is two past the display column"
        );
    }

    #[test]
    fn a_match_prefix_is_six_columns_at_the_operands_column() {
        let source = "    let v = compute(|| panic!(\"x\"))?;\n";
        let at = source.find("compute").unwrap();
        let rows = rows_from_splices(source, &[splice(at, at, Kind::ErrOpen, "match ")]);
        assert_eq!(
            rows,
            vec![ColRow {
                line: 1,
                start: 13,
                added: 6,
                removed: 0,
            }]
        );
        let panic_at = source.find("panic!").unwrap();
        let plain = display_col_at(source, panic_at).unwrap();
        let mapped = sensorium_rt::original_column_in(
            &[sensorium_rt::ColInsert {
                line: 1,
                start: 13,
                added: 6,
                removed: 0,
            }],
            1,
            plain + 6,
        );
        assert_eq!(mapped, plain);
    }

    #[test]
    fn a_replacement_and_a_later_insert_share_the_line() {
        let source = "std::thread::spawn(f);\n";
        let callee = "::sensorium_rt::spawn_child";
        let arg = "\"s\", ";
        let rows = rows_from_splices(
            source,
            &[
                splice(0, 18, Kind::Replace, callee),
                splice(19, 19, Kind::SpawnArg, arg),
            ],
        );
        assert_eq!(rows[0].start, 1);
        assert_eq!(rows[0].added, display_width(callee));
        assert_eq!(rows[0].removed, display_width("std::thread::spawn"));
        assert_eq!(rows[1].removed, 0);
        assert_eq!(rows[1].added, display_width(arg));
        // Original column of `f` plus the replacement's net width.
        assert_eq!(
            rows[1].start,
            display_col_at(source, 19).unwrap() + rows[0].added - rows[0].removed
        );
    }

    #[test]
    fn a_newline_splice_and_the_registration_itself_are_not_rows() {
        let source = "fn f() {}\n";
        let rows = rows_from_splices(
            source,
            &[
                splice(0, 0, Kind::Static, "\nstatic unit;"),
                splice(7, 7, Kind::ColMap, " #[used] registration"),
            ],
        );
        assert!(rows.is_empty(), "{rows:?}");
    }

    #[test]
    fn the_registration_is_one_line_and_names_the_file() {
        let text = registration(
            "probe-app/tests/e7_operand.rs",
            &[ColRow {
                line: 33,
                start: 13,
                added: 6,
                removed: 0,
            }],
        );
        assert!(!text.contains('\n'), "{text}");
        assert!(text.starts_with(COLUMN_MAP_PREFIX));
        assert!(text.contains("register_columns(\"probe-app/tests/e7_operand.rs\""));
        assert!(text.contains("line: 33, start: 13, added: 6, removed: 0"));
        assert!(text.contains("ensure_panic_hook()"));
        assert!(!text.contains("used(linker)"));
        assert!(text.ends_with("__sensorium_colmap_init };"));
    }

    #[test]
    fn a_quote_in_the_path_is_escaped_inside_the_registration() {
        let text = registration("a\"b.rs", &[]);
        assert!(text.contains(r#"register_columns("a\"b.rs""#), "{text}");
        assert!(!text.contains('\n'));
    }

    #[test]
    fn transforming_a_try_operand_keeps_the_line_count_and_registers_the_shift() {
        let source = "fn compute(f: impl Fn() -> u32) -> Result<u32, String> { Ok(f()) }\n\
fn run_operand() -> Result<u32, String> {\n\
    let v = compute(|| panic!(\"operand probe panic\"))?;\n\
    Ok(v)\n\
}\n";
        let t = crate::transform(source, "src/lib.rs", "meta", 0, true, &crate::Focus::EMPTY)
            .expect("transform");
        assert_eq!(t.source.lines().count(), source.lines().count());
        assert!(
            t.source.contains(COLUMN_MAP_PREFIX),
            "no registration:\n{}",
            t.source
        );
        let plain = display_col_at(source, source.find("panic!").unwrap()).unwrap();
        let inst = display_col_at(&t.source, t.source.find("panic!").unwrap()).unwrap();
        assert!(
            inst > plain,
            "the wrap did not move the column: {plain} -> {inst}"
        );
        let rows = parse_rows(&t.source);
        let inserts: Vec<sensorium_rt::ColInsert> = rows
            .iter()
            .map(|r| sensorium_rt::ColInsert {
                line: r.line,
                start: r.start,
                added: r.added,
                removed: r.removed,
            })
            .collect();
        let panic_line = line_of(source, source.find("panic!").unwrap());
        assert_eq!(
            sensorium_rt::original_column_in(&inserts, panic_line, inst),
            plain,
            "rows {rows:?} did not map {inst} back to {plain}"
        );
    }

    fn parse_rows(source: &str) -> Vec<ColRow> {
        let mut rows = Vec::new();
        let mut rest = source;
        let marker = "ColInsert { line: ";
        while let Some(at) = rest.find(marker) {
            rest = &rest[at + marker.len()..];
            let line = take_u32(&mut rest);
            rest = rest.strip_prefix(", start: ").expect("start");
            let start = take_u32(&mut rest);
            rest = rest.strip_prefix(", added: ").expect("added");
            let added = take_u32(&mut rest);
            rest = rest.strip_prefix(", removed: ").expect("removed");
            let removed = take_u32(&mut rest);
            rows.push(ColRow {
                line,
                start,
                added,
                removed,
            });
        }
        assert!(!rows.is_empty(), "no ColInsert in:\n{source}");
        rows
    }

    fn take_u32(rest: &mut &str) -> u32 {
        let end = rest
            .find(|c: char| !c.is_ascii_digit())
            .unwrap_or(rest.len());
        let n = rest[..end].parse().expect("digits");
        *rest = &rest[end..];
        n
    }
}
