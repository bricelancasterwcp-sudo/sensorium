//! The unit manifest, read back as JSON.
//!
//! The manifest is the join between a trace and the source it was recorded
//! from, and the converter (Task 8) is its only reader. This test asserts the
//! shape the plan wrote down -- keys, nesting and value spellings -- against the
//! serialised text, not against the Rust struct, so a rename that keeps the type
//! compiling still fails here.

mod common;

use common::{read, META};

use sensorium_transform::{transform, Manifest};

fn manifest_json() -> serde_json::Value {
    let mut m = Manifest::new(META, "bloomery_daemon", "lib");
    let root = transform(&read("spawn_thread", "in"), "src/lib.rs", META, 0, true)
        .expect("transform the root");
    m.add_file("src/lib.rs", &root);
    let other = transform(
        &read("async_fn", "in"),
        "src/other.rs",
        META,
        u32::try_from(root.sites.len()).expect("fits"),
        false,
    )
    .expect("transform the second file");
    m.add_file("src/other.rs", &other);
    m.source_hashes
        .insert("src/lib.rs".to_owned(), "00".repeat(32));
    m.unreached_files.push("src/never_walked.rs".to_owned());
    serde_json::from_str(&m.to_json().expect("serialise")).expect("valid JSON")
}

#[test]
fn the_manifest_has_the_shape_the_plan_names() {
    let j = manifest_json();
    assert_eq!(j["unit"], META);
    assert_eq!(j["crate_name"], "bloomery_daemon");
    assert_eq!(j["crate_type"], "lib");

    let sites = j["files"]["src/lib.rs"].as_array().expect("files entry");
    assert_eq!(sites.len(), 2);
    assert_eq!(sites[0]["site"], 0);
    assert_eq!(sites[0]["qualname"], "fully_qualified");
    assert_eq!(sites[0]["firstlineno"], 5);
    assert_eq!(sites[0]["ret"], "value");
    // A `Site`'s own `file` is not repeated inside a manifest entry: the map key
    // is the file, and two spellings of one fact are one fact too many.
    assert!(sites[0].get("file").is_none());

    let skipped = j["skipped"].as_array().expect("skipped");
    assert_eq!(skipped.len(), 3);
    assert_eq!(skipped[0]["file"], "src/other.rs");
    assert_eq!(skipped[0]["qualname"], "plain");
    assert_eq!(skipped[0]["line"], 1);
    assert_eq!(skipped[0]["reason"], "async");

    let spawns = j["spawns"].as_array().expect("spawns");
    assert_eq!(spawns.len(), 2);
    assert_eq!(spawns[0]["file"], "src/lib.rs");
    assert_eq!(spawns[0]["line"], 6);
    assert_eq!(spawns[0]["wrapped"], true);
    assert!(spawns[0]["reason"].is_null());

    assert_eq!(j["source_hashes"]["src/lib.rs"], "00".repeat(32));
    assert_eq!(j["fell_back"], false);
    assert!(j["fallback_reason"].is_null());
    assert_eq!(j["unreached_files"][0], "src/never_walked.rs");
    assert_eq!(j["appended_line"]["src/lib.rs"], false);
    assert_eq!(j["appended_line"]["src/other.rs"], false);
}

#[test]
fn every_key_the_plan_names_is_present_and_no_others_are() {
    let j = manifest_json();
    let mut keys: Vec<&str> = j
        .as_object()
        .expect("object")
        .keys()
        .map(String::as_str)
        .collect();
    keys.sort_unstable();
    assert_eq!(
        keys,
        [
            "appended_line",
            "crate_name",
            "crate_type",
            "fallback_reason",
            "fell_back",
            "files",
            "skipped",
            "source_hashes",
            "spawns",
            "unit",
            "unreached_files",
        ]
    );
}

#[test]
fn ret_kinds_serialise_as_the_three_words_the_converter_reads() {
    let mut m = Manifest::new(META, "k", "lib");
    let t = transform(&read("never_fn", "in"), "src/never.rs", META, 0, false).expect("transform");
    m.add_file("src/never.rs", &t);
    let t = transform(&read("unit_fn", "in"), "src/unit.rs", META, 2, false).expect("transform");
    m.add_file("src/unit.rs", &t);
    let t =
        transform(&read("value_tail", "in"), "src/value.rs", META, 5, false).expect("transform");
    m.add_file("src/value.rs", &t);
    let j: serde_json::Value =
        serde_json::from_str(&m.to_json().expect("serialise")).expect("JSON");
    assert_eq!(j["files"]["src/never.rs"][0]["ret"], "never");
    assert_eq!(j["files"]["src/unit.rs"][0]["ret"], "unit");
    assert_eq!(j["files"]["src/value.rs"][0]["ret"], "value");
}

#[test]
fn a_manifest_cannot_disagree_with_what_was_spliced() {
    // The file key comes from the caller, but every site inside comes from the
    // `Transformed` the splicer produced, so the two can never drift.
    let mut m = Manifest::new(META, "k", "lib");
    let t = transform(&read("value_tail", "in"), "src/value.rs", META, 40, false).unwrap();
    m.add_file("src/value.rs", &t);
    let j: serde_json::Value = serde_json::from_str(&m.to_json().unwrap()).unwrap();
    let sites = j["files"]["src/value.rs"].as_array().unwrap();
    assert_eq!(sites.len(), t.sites.len());
    for (got, want) in sites.iter().zip(&t.sites) {
        assert_eq!(got["site"], want.site);
        assert_eq!(got["qualname"], want.qualname);
        assert_eq!(got["firstlineno"], want.firstlineno);
    }
}
