//! Rule v1 in the runtime: the name rule, the keyed digest, and what a
//! recorded child actually writes into its proc header.
//!
//! **The `split` and `fires` cases are not written here.** They live in
//! `docs/trace-format/redaction-v1.json`, which the Python recorder's suite
//! and the TypeScript recorder's suite read too: three implementations of one
//! rule agree only on what all three are asked. A case that belongs to the
//! rule belongs in the fixture; a case that belongs to THIS implementation --
//! the header it writes, the modes it creates files at -- belongs here.

mod common;

use std::os::unix::fs::PermissionsExt;
use std::path::Path;

use common::{Spec, TempDir};
use sensorium_rt::redact::{
    fires, hmac_sha256, redact_env, redaction_json, split, Key, Knobs, KEY_VAR, REDACTED, RULE,
};
use sensorium_rt::sha256::to_hex;
use serde_json::Value;

/// The fixture, embedded rather than read at run time: `include_str!` makes it
/// a compile-time input, so a fixture edit rebuilds this suite instead of
/// silently testing yesterday's cases.
const FIXTURE: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../docs/trace-format/redaction-v1.json"
));

/// A key with no meaning beyond being 64 hex characters.
///
/// `KEY_ID` and the two digests were computed by PYTHON's `hashlib`/`hmac`
/// (`hmac.new(key, msg, "sha256").hexdigest()[:16]`), not by this crate: a
/// digest this crate checks against its own output would agree with any
/// mistake it makes.
const HEX_KEY: &str = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff";
const KEY_ID: &str = "4773d12e";
const DIGEST_ABC: &str = "c523adb6e8584aa9";
const DIGEST_DEF: &str = "c19438645a9373e5";

fn fixture() -> Value {
    serde_json::from_str(FIXTURE).expect("the redaction fixture is valid JSON")
}

/// The knobs of a process nobody set a knob on.
fn plain() -> Knobs {
    Knobs::from_values(None, None, None)
}

fn owned(pairs: &[(&str, &str)]) -> Vec<(String, String)> {
    pairs
        .iter()
        .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
        .collect()
}

fn seen(env: &[(String, String)]) -> Vec<(&str, &str)> {
    env.iter().map(|(k, v)| (k.as_str(), v.as_str())).collect()
}

/// A fixture case's knob list, back in the comma form the environment carries
/// it in -- so the fixture exercises the parsing too, and not just the set.
fn commas(values: &Value) -> String {
    values
        .as_array()
        .expect("a knob entry list")
        .iter()
        .map(|v| v.as_str().expect("a knob entry").to_owned())
        .collect::<Vec<_>>()
        .join(",")
}

fn case_knobs(case: &Value) -> Knobs {
    match case.get("knobs") {
        None => plain(),
        Some(k) => Knobs::from_values(None, Some(&commas(&k["names"])), Some(&commas(&k["allow"]))),
    }
}

// ---------------------------------------------------------------------------
// The fixture
// ---------------------------------------------------------------------------

#[test]
fn every_split_case_in_the_fixture() {
    let f = fixture();
    let cases = f["split"]
        .as_array()
        .expect("the fixture has `split` cases");
    assert!(
        cases.len() >= 10,
        "the fixture went thin ({} split cases); this test would prove nothing",
        cases.len()
    );
    for case in cases {
        let name = case["name"].as_str().expect("a case name");
        let want: Vec<String> = case["segments"]
            .as_array()
            .expect("the case's segments")
            .iter()
            .map(|s| s.as_str().expect("a segment").to_owned())
            .collect();
        assert_eq!(split(name), want, "split({name:?})");
    }
}

#[test]
fn every_fires_case_in_the_fixture() {
    let f = fixture();
    let cases = f["names"]
        .as_array()
        .expect("the fixture has `names` cases");
    assert!(
        cases.len() >= 40,
        "the fixture went thin ({} name cases); this test would prove nothing",
        cases.len()
    );
    for case in cases {
        let name = case["name"].as_str().expect("a case name");
        let want = case["fires"].as_bool().expect("the case's verdict");
        let knobs = case_knobs(case);
        assert_eq!(
            fires(name, &knobs),
            want,
            "fires({name:?}) under names={:?} allow={:?}",
            knobs.names,
            knobs.allow
        );
    }
}

// ---------------------------------------------------------------------------
// `split`, against the two substitution passes it is specified as
// ---------------------------------------------------------------------------

/// `split` as `src/sensorium/redact.py` SPELLS it: two regex substitution
/// passes over the whole name, then a split on runs of non-alphanumerics.
///
/// The implementation under test walks the name once and decides each boundary
/// in place, which is a different shape of program; this is the shape the rule
/// is written in, so the two agreeing over every short name is what says the
/// rewrite kept the rule.
fn reference_split(name: &str) -> Vec<String> {
    camel_step(&camel_run(name))
        .split(|c: char| !c.is_ascii_alphanumeric())
        .filter(|part| !part.is_empty())
        .map(str::to_ascii_uppercase)
        .collect()
}

/// `re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)`.
///
/// The greedy `[A-Z]+` takes the whole uppercase run starting here and then
/// gives back exactly one character, because `[A-Z][a-z]` needs the character
/// after its uppercase to be lowercase and every earlier give-back leaves an
/// uppercase there. So a match exists at `i` only when the uppercase run from
/// `i` is at least two long and the character after it is lowercase, and
/// scanning resumes after the two characters the second group took.
fn camel_run(name: &str) -> String {
    let c: Vec<char> = name.chars().collect();
    let mut out = String::new();
    let mut i = 0;
    while i < c.len() {
        if c[i].is_ascii_uppercase() {
            let mut m = i;
            while m + 1 < c.len() && c[m + 1].is_ascii_uppercase() {
                m += 1;
            }
            if m > i && m + 1 < c.len() && c[m + 1].is_ascii_lowercase() {
                out.extend(&c[i..m]);
                out.push(' ');
                out.push(c[m]);
                out.push(c[m + 1]);
                i = m + 2;
                continue;
            }
        }
        out.push(c[i]);
        i += 1;
    }
    out
}

/// `re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)`.
fn camel_step(name: &str) -> String {
    let c: Vec<char> = name.chars().collect();
    let mut out = String::new();
    let mut i = 0;
    while i < c.len() {
        if i + 1 < c.len()
            && (c[i].is_ascii_lowercase() || c[i].is_ascii_digit())
            && c[i + 1].is_ascii_uppercase()
        {
            out.push(c[i]);
            out.push(' ');
            out.push(c[i + 1]);
            i += 2;
        } else {
            out.push(c[i]);
            i += 1;
        }
    }
    out
}

#[test]
fn split_agrees_with_the_two_substitution_passes_on_every_short_name() {
    // One lowercase, two uppercase (so an uppercase RUN can form), another
    // lowercase, a digit and a separator: every character class the two
    // patterns can tell apart, in every arrangement up to five long.
    const ALPHABET: [char; 6] = ['a', 'B', 'C', 'd', '4', '_'];
    let mut names = vec![String::new()];
    let mut frontier = vec![String::new()];
    for _ in 0..5 {
        let mut next = Vec::with_capacity(frontier.len() * ALPHABET.len());
        for base in &frontier {
            for ch in ALPHABET {
                let mut n = base.clone();
                n.push(ch);
                next.push(n);
            }
        }
        names.extend(next.iter().cloned());
        frontier = next;
    }
    assert_eq!(names.len(), 9331, "the generator lost names");
    for name in &names {
        assert_eq!(split(name), reference_split(name), "split({name:?})");
    }
}

// ---------------------------------------------------------------------------
// The knobs
// ---------------------------------------------------------------------------

#[test]
fn the_off_knob_reads_like_every_other_sensorium_off_switch() {
    assert!(!plain().off, "unset leaves the rule on");
    assert!(
        !Knobs::from_values(Some(""), None, None).off,
        "empty is unset"
    );
    assert!(
        !Knobs::from_values(Some("0"), None, None).off,
        "0 is off-off"
    );
    assert!(Knobs::from_values(Some("1"), None, None).off);
    assert!(
        Knobs::from_values(Some("no"), None, None).off,
        "any other value"
    );
}

#[test]
fn a_knob_list_is_normalised_sorted_and_deduplicated() {
    let k = Knobs::from_values(
        None,
        Some(" myco_dsn , mycoDsn,,MYCO_DSN , a_b "),
        Some("-, ,x"),
    );
    assert_eq!(k.names, vec!["AB".to_owned(), "MYCODSN".to_owned()]);
    assert_eq!(
        k.allow,
        vec!["X".to_owned()],
        "an entry that normalises to nothing is dropped -- it would match a nameless value"
    );
}

// ---------------------------------------------------------------------------
// The digest
// ---------------------------------------------------------------------------

#[test]
fn hmac_sha256_is_the_rfc_4231_construction() {
    // Test case 2: a key shorter than the block, zero-padded.
    assert_eq!(
        to_hex(&hmac_sha256(b"Jefe", b"what do ya want for nothing?")),
        "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    );
    // Test case 6: a key LONGER than the block, which is hashed first. No key
    // this runtime accepts is that long, but the branch exists and an untested
    // branch is a rumour.
    assert_eq!(
        to_hex(&hmac_sha256(
            &[0xaa; 131],
            b"Test Using Larger Than Block-Size Key - Hash Key First"
        )),
        "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"
    );
}

#[test]
fn a_key_is_sixty_four_hex_characters_and_nothing_else() {
    for bad in [
        None,
        Some(""),
        Some("0011"),
        Some("00112233445566778899aabbccddeeff00112233445566778899aabbccddee"),
        Some("00112233445566778899aabbccddeeff00112233445566778899aabbccddeeffff"),
        Some("00112233445566778899aabbccddeegg00112233445566778899aabbccddeeff"),
        Some("00112233445566778899aabbccddeeff00112233445566778899aabbccddee f"),
    ] {
        let k = Key::from_hex(bad);
        assert!(!k.keyed(), "{bad:?} is not a key");
        assert_eq!(k.key_id(), None);
        assert_eq!(k.digest("abc"), None, "an unkeyed store digests nothing");
    }

    let k = Key::from_hex(Some(HEX_KEY));
    assert!(k.keyed());
    assert_eq!(k.key_id().as_deref(), Some(KEY_ID), "sha256(key), 8 hex");
    assert_eq!(k.digest("abc").as_deref(), Some(DIGEST_ABC));
    assert_eq!(k.digest("def").as_deref(), Some(DIGEST_DEF));
    assert_eq!(
        Key::from_hex(Some(&HEX_KEY.to_ascii_uppercase()))
            .key_id()
            .as_deref(),
        Some(KEY_ID),
        "hex is hex in either case"
    );
}

// ---------------------------------------------------------------------------
// The environment
// ---------------------------------------------------------------------------

#[test]
fn redact_env_replaces_the_value_tables_the_digest_and_deletes_the_key() {
    let key = Key::from_hex(Some(HEX_KEY));
    let env = owned(&[
        ("HOME", "/home/someone"),
        ("MY_API_KEY", "abc"),
        (KEY_VAR, HEX_KEY),
        ("PATH", "/usr/bin"),
        ("Z_TOKEN", "def"),
    ]);
    let (stored, table) = redact_env(env, &key, &plain());
    assert_eq!(
        seen(&stored),
        vec![
            ("HOME", "/home/someone"),
            ("MY_API_KEY", REDACTED),
            ("PATH", "/usr/bin"),
            ("Z_TOKEN", REDACTED),
        ],
        "the two secret-shaped names are replaced and the key variable is gone"
    );
    assert_eq!(
        table,
        vec![
            ("MY_API_KEY".to_owned(), Some(DIGEST_ABC.to_owned())),
            ("Z_TOKEN".to_owned(), Some(DIGEST_DEF.to_owned())),
        ],
        "only the names that fired are tabled, in the order they arrived"
    );
}

#[test]
fn an_unkeyed_store_still_redacts_and_tables_the_name() {
    let (stored, table) = redact_env(
        owned(&[("MY_API_KEY", "abc")]),
        &Key::from_hex(None),
        &plain(),
    );
    assert_eq!(seen(&stored), vec![("MY_API_KEY", REDACTED)]);
    assert_eq!(
        table,
        vec![("MY_API_KEY".to_owned(), None)],
        "no key, so no digest -- but the reader is still told the value was withheld"
    );
}

#[test]
fn the_off_knob_keeps_plaintext_and_still_deletes_the_key() {
    let off = Knobs::from_values(Some("1"), None, None);
    let (stored, table) = redact_env(
        owned(&[("MY_API_KEY", "abc"), (KEY_VAR, HEX_KEY)]),
        &Key::from_hex(Some(HEX_KEY)),
        &off,
    );
    assert_eq!(seen(&stored), vec![("MY_API_KEY", "abc")]);
    assert!(
        table.is_empty(),
        "nothing was redacted, so nothing is tabled"
    );
}

#[test]
fn the_knobs_amend_which_names_fire() {
    let knobs = Knobs::from_values(None, Some("myco_thing"), Some("api_key"));
    let (stored, table) = redact_env(
        owned(&[("API_KEY", "plain"), ("MYCO_THING", "abc")]),
        &Key::from_hex(Some(HEX_KEY)),
        &knobs,
    );
    assert_eq!(
        seen(&stored),
        vec![("API_KEY", "plain"), ("MYCO_THING", REDACTED)]
    );
    assert_eq!(
        table,
        vec![("MYCO_THING".to_owned(), Some(DIGEST_ABC.to_owned()))]
    );
}

#[test]
fn redaction_json_is_the_header_object_the_format_names() {
    assert_eq!(
        redaction_json(
            &Key::from_hex(Some(HEX_KEY)),
            &Knobs::from_values(Some("1"), None, None)
        ),
        r#"{"rule":"v1","mode":"off"}"#,
        "off is two keys: a reader must not be told about a key that was not applied"
    );
    assert_eq!(
        redaction_json(&Key::from_hex(None), &plain()),
        r#"{"rule":"v1","mode":"on","keyed":false,"key_id":null,"names":[],"allow":[]}"#
    );
    assert_eq!(
        redaction_json(
            &Key::from_hex(Some(HEX_KEY)),
            &Knobs::from_values(None, Some("myco_thing,a_b"), Some("api_key"))
        ),
        concat!(
            r#"{"rule":"v1","mode":"on","keyed":true,"key_id":"4773d12e","#,
            r#""names":["AB","MYCOTHING"],"allow":["APIKEY"]}"#
        ),
        "the key order is the format's, not a map's"
    );
}

// ---------------------------------------------------------------------------
// A recorded child
// ---------------------------------------------------------------------------

fn mode_of(path: &Path) -> u32 {
    std::fs::metadata(path)
        .unwrap_or_else(|e| panic!("stat {}: {e}", path.display()))
        .permissions()
        .mode()
        & 0o777
}

#[test]
fn a_recorded_child_redacts_its_own_environment_into_its_proc_header() {
    let dir = TempDir::reserved("redact-child");
    let run = Spec::new("main-only")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .env("MY_API_KEY", "abc")
        .run();

    let h = dir.proc_header(run.pid);
    assert_eq!(
        h.get("env").get("MY_API_KEY").str(),
        REDACTED,
        "the value never reached the disk"
    );
    assert!(
        h.get("env").opt(KEY_VAR).is_none(),
        "the key is DELETED from the recorded environment, never redacted"
    );
    assert_eq!(
        h.get("env").get("SENSORIUM_SPOOL").str(),
        dir.path().to_string_lossy(),
        "a name the rule does not fire on is recorded as it always was"
    );
    assert_eq!(
        h.get("env_redaction").get("MY_API_KEY").str(),
        DIGEST_ABC,
        "and the digest is the one Python's hmac takes under the same key"
    );

    let r = h.get("redaction");
    assert_eq!(r.get("rule").str(), RULE);
    assert_eq!(r.get("mode").str(), "on");
    assert!(r.get("keyed").bool());
    assert_eq!(r.get("key_id").str(), KEY_ID);
    assert!(r.get("names").arr().is_empty());
    assert!(r.get("allow").arr().is_empty());
}

#[test]
fn the_env_redaction_table_is_written_in_sorted_name_order() {
    let dir = TempDir::reserved("redact-sorted");
    let run = Spec::new("main-only")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .env("ZZ_TOKEN", "abc")
        .env("AA_TOKEN", "abc")
        .env("MM_TOKEN", "abc")
        .run();

    // Read the TEXT: the JSON reader is a map and would sort the names for
    // free, which is the very thing under test (R13).
    let text = dir.proc_header_text(run.pid);
    let table_at = text
        .find("\"env_redaction\":{")
        .expect("the header has an env_redaction table");
    let mut found: Vec<(&str, usize)> = Vec::new();
    for name in ["ZZ_TOKEN", "MM_TOKEN", "AA_TOKEN"] {
        let needle = format!("\"{name}\":");
        let at = text[table_at..]
            .find(&needle)
            .unwrap_or_else(|| panic!("{name} is not in the table; header: {text}"))
            + table_at;
        found.push((name, at));
    }
    found.sort_by_key(|(_, at)| *at);
    assert_eq!(
        found.iter().map(|(n, _)| *n).collect::<Vec<_>>(),
        vec!["AA_TOKEN", "MM_TOKEN", "ZZ_TOKEN"],
        "the table is written in sorted name order (R13), whatever order the \
         environment arrived in"
    );
}

#[test]
fn the_env_hash_is_taken_over_the_redacted_environment() {
    let dir = TempDir::reserved("redact-envhash");
    let a = Spec::new("main-only")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .env("MY_API_KEY", "abc")
        .run();
    let b = Spec::new("main-only")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .env("MY_API_KEY", "def")
        .run();

    let (ha, hb) = (dir.proc_header(a.pid), dir.proc_header(b.pid));
    assert_eq!(
        ha.get("env_hash").str(),
        hb.get("env_hash").str(),
        "both runs stored <redacted>, so the hash of what they stored is one hash"
    );
    assert_eq!(ha.get("env_redaction").get("MY_API_KEY").str(), DIGEST_ABC);
    assert_eq!(
        hb.get("env_redaction").get("MY_API_KEY").str(),
        DIGEST_DEF,
        "and the digests still tell the two runs apart"
    );
}

#[test]
fn a_child_with_no_key_redacts_unkeyed_and_says_so() {
    let dir = TempDir::reserved("redact-unkeyed");
    let run = Spec::new("main-only")
        .spool(dir.path())
        .env("MY_API_KEY", "abc")
        .run();

    let h = dir.proc_header(run.pid);
    assert_eq!(h.get("env").get("MY_API_KEY").str(), REDACTED);
    assert!(
        h.get("env_redaction").get("MY_API_KEY").is_null(),
        "no key, no digest -- and the name is still tabled"
    );
    let r = h.get("redaction");
    assert!(!r.get("keyed").bool());
    assert!(r.get("key_id").is_null());
}

#[test]
fn a_child_with_the_rule_off_records_plaintext_and_a_two_key_object() {
    let dir = TempDir::reserved("redact-off");
    let run = Spec::new("main-only")
        .spool(dir.path())
        .env("SENSORIUM_NO_REDACT", "1")
        .env(KEY_VAR, HEX_KEY)
        .env("MY_API_KEY", "abc")
        .run();

    let h = dir.proc_header(run.pid);
    assert_eq!(
        h.get("env").get("MY_API_KEY").str(),
        "abc",
        "the rule was turned off, so the plaintext is there ON PURPOSE"
    );
    assert!(
        h.get("env").opt(KEY_VAR).is_none(),
        "the key is deleted whatever the knob says"
    );
    assert!(h.get("env_redaction").obj().is_empty());
    let r = h.get("redaction");
    assert_eq!(
        r.obj().keys().collect::<Vec<_>>(),
        vec!["mode", "rule"],
        "exactly two keys: an off header claims nothing about a key or a list"
    );
    assert_eq!(r.get("rule").str(), RULE);
    assert_eq!(r.get("mode").str(), "off");
}

#[test]
fn a_childs_knobs_are_recorded_with_the_names_they_amended() {
    let dir = TempDir::reserved("redact-knobs");
    let run = Spec::new("main-only")
        .spool(dir.path())
        .env(KEY_VAR, HEX_KEY)
        .env("SENSORIUM_REDACT_NAMES", "myco_thing")
        .env("SENSORIUM_REDACT_ALLOW", "api_key")
        .env("MYCO_THING", "abc")
        .env("API_KEY", "plain")
        .run();

    let h = dir.proc_header(run.pid);
    assert_eq!(h.get("env").get("MYCO_THING").str(), REDACTED);
    assert_eq!(
        h.get("env").get("API_KEY").str(),
        "plain",
        "allow wins over the rule the user did not write"
    );
    let r = h.get("redaction");
    let names: Vec<&str> = r.get("names").arr().iter().map(|j| j.str()).collect();
    let allow: Vec<&str> = r.get("allow").arr().iter().map(|j| j.str()).collect();
    assert_eq!(
        names,
        vec!["MYCOTHING"],
        "recorded normalised, so a reader can compare"
    );
    assert_eq!(allow, vec!["APIKEY"]);
}

/// The directory case here is the one where the RUNTIME creates it: a
/// hand-launched or test binary with `SENSORIUM_SPOOL` pointing at a path that
/// does not exist yet (`TempDir::reserved`). Under the driver the directory is
/// created by `cargo-sensorium` BEFORE the instrumented build launches, so the
/// runtime's `DirBuilder` never applies to it and its mode is the driver's to
/// set -- asserted end to end in the driver's own tests (ruling R23), not
/// here. The two file modes are the runtime's on both routes.
#[test]
fn the_spool_the_header_and_the_spool_directory_are_private() {
    let dir = TempDir::reserved("redact-modes");
    let run = Spec::new("main-only").spool(dir.path()).run();

    assert_eq!(
        mode_of(&dir.path().join(format!("{}.1.spool", run.pid))),
        0o600,
        "a spool holds captured values and is the owner's alone"
    );
    assert_eq!(
        mode_of(&dir.path().join(format!("{}.proc.json", run.pid))),
        0o600,
        "and so is the header, which holds the environment"
    );
    assert_eq!(
        mode_of(dir.path()),
        0o700,
        "the directory the runtime created is the owner's alone too"
    );
}
