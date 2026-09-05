//! A minimal JSON reader, for the proc header.
//!
//! Hand-written rather than a dependency: the runtime writes its header by hand
//! too, and a reader that shares no code with the writer is what makes the
//! header's shape falsifiable.

use std::collections::BTreeMap;

// ---------------------------------------------------------------------------
// A minimal JSON reader, for the proc header
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(BTreeMap<String, Json>),
}

impl Json {
    pub fn parse(s: &str) -> Json {
        let b = s.as_bytes();
        let mut at = 0usize;
        let v = parse_value(b, &mut at);
        skip_ws(b, &mut at);
        assert_eq!(
            at,
            b.len(),
            "trailing bytes after the JSON value: {:?}",
            &s[at..]
        );
        v
    }

    pub fn get(&self, key: &str) -> &Json {
        match self {
            Json::Obj(m) => m
                .get(key)
                .unwrap_or_else(|| panic!("no key {key:?} in {:?}", m.keys().collect::<Vec<_>>())),
            other => panic!("get({key:?}) on a non-object: {other:?}"),
        }
    }

    pub fn opt(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Obj(m) => m.get(key),
            other => panic!("opt({key:?}) on a non-object: {other:?}"),
        }
    }

    pub fn str(&self) -> &str {
        match self {
            Json::Str(s) => s,
            other => panic!("expected a string, got {other:?}"),
        }
    }

    pub fn u64(&self) -> u64 {
        match self {
            Json::Num(n) => *n as u64,
            other => panic!("expected a number, got {other:?}"),
        }
    }

    pub fn arr(&self) -> &[Json] {
        match self {
            Json::Arr(a) => a,
            other => panic!("expected an array, got {other:?}"),
        }
    }

    pub fn obj(&self) -> &BTreeMap<String, Json> {
        match self {
            Json::Obj(m) => m,
            other => panic!("expected an object, got {other:?}"),
        }
    }

    pub fn bool(&self) -> bool {
        match self {
            Json::Bool(b) => *b,
            other => panic!("expected a bool, got {other:?}"),
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Json::Null)
    }
}

fn skip_ws(b: &[u8], at: &mut usize) {
    while *at < b.len() && matches!(b[*at], b' ' | b'\t' | b'\n' | b'\r') {
        *at += 1;
    }
}

fn expect(b: &[u8], at: &mut usize, c: u8) {
    assert_eq!(
        b.get(*at).copied(),
        Some(c),
        "expected {:?} at byte {at}",
        c as char
    );
    *at += 1;
}

fn parse_value(b: &[u8], at: &mut usize) -> Json {
    skip_ws(b, at);
    match b.get(*at).copied().expect("unexpected end of JSON") {
        b'{' => parse_obj(b, at),
        b'[' => parse_arr(b, at),
        b'"' => Json::Str(parse_str(b, at)),
        b't' => {
            *at += 4;
            Json::Bool(true)
        }
        b'f' => {
            *at += 5;
            Json::Bool(false)
        }
        b'n' => {
            *at += 4;
            Json::Null
        }
        _ => parse_num(b, at),
    }
}

fn parse_obj(b: &[u8], at: &mut usize) -> Json {
    expect(b, at, b'{');
    let mut m = BTreeMap::new();
    skip_ws(b, at);
    if b.get(*at) == Some(&b'}') {
        *at += 1;
        return Json::Obj(m);
    }
    loop {
        skip_ws(b, at);
        let k = parse_str(b, at);
        skip_ws(b, at);
        expect(b, at, b':');
        let v = parse_value(b, at);
        m.insert(k, v);
        skip_ws(b, at);
        match b.get(*at).copied() {
            Some(b',') => *at += 1,
            Some(b'}') => {
                *at += 1;
                return Json::Obj(m);
            }
            other => panic!("expected ',' or '}}' at byte {at}, got {other:?}"),
        }
    }
}

fn parse_arr(b: &[u8], at: &mut usize) -> Json {
    expect(b, at, b'[');
    let mut a = Vec::new();
    skip_ws(b, at);
    if b.get(*at) == Some(&b']') {
        *at += 1;
        return Json::Arr(a);
    }
    loop {
        a.push(parse_value(b, at));
        skip_ws(b, at);
        match b.get(*at).copied() {
            Some(b',') => *at += 1,
            Some(b']') => {
                *at += 1;
                return Json::Arr(a);
            }
            other => panic!("expected ',' or ']' at byte {at}, got {other:?}"),
        }
    }
}

fn parse_str(b: &[u8], at: &mut usize) -> String {
    expect(b, at, b'"');
    let mut out = String::new();
    loop {
        let c = b.get(*at).copied().expect("unterminated string");
        *at += 1;
        match c {
            b'"' => return out,
            b'\\' => {
                let e = b.get(*at).copied().expect("dangling escape");
                *at += 1;
                match e {
                    b'"' => out.push('"'),
                    b'\\' => out.push('\\'),
                    b'/' => out.push('/'),
                    b'b' => out.push('\u{8}'),
                    b'f' => out.push('\u{c}'),
                    b'n' => out.push('\n'),
                    b'r' => out.push('\r'),
                    b't' => out.push('\t'),
                    b'u' => {
                        let hex = std::str::from_utf8(&b[*at..*at + 4]).expect("hex");
                        *at += 4;
                        let cp = u32::from_str_radix(hex, 16).expect("hex escape");
                        out.push(char::from_u32(cp).unwrap_or('\u{fffd}'));
                    }
                    other => panic!("unknown escape \\{}", other as char),
                }
            }
            _ => {
                // Copy the whole UTF-8 sequence this byte starts.
                let start = *at - 1;
                let extra = match c {
                    0x00..=0x7f => 0,
                    0xc0..=0xdf => 1,
                    0xe0..=0xef => 2,
                    _ => 3,
                };
                *at += extra;
                out.push_str(std::str::from_utf8(&b[start..*at]).expect("UTF-8 in a JSON string"));
            }
        }
    }
}

fn parse_num(b: &[u8], at: &mut usize) -> Json {
    let start = *at;
    while *at < b.len() && matches!(b[*at], b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E') {
        *at += 1;
    }
    let s = std::str::from_utf8(&b[start..*at]).expect("number");
    Json::Num(
        s.parse()
            .unwrap_or_else(|e| panic!("bad number {s:?}: {e}")),
    )
}
