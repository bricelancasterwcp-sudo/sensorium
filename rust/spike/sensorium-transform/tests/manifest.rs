//! The manifest is the wrapper's (Task 3) output and the converter's (Task 4)
//! input, so its JSON shape is a contract between two crates in two languages.
//! It is pinned here, against the plan's verbatim schema.

use sensorium_transform::{transform, Manifest};

const META: &str = "d41d8cd98f00b204";

#[test]
fn a_manifest_carries_every_site_keyed_by_its_original_path() {
    let root = "pub fn a() {}\nconst fn c() -> u8 {\n    1\n}\n";
    let other = "pub mod m {\n    pub fn b() {}\n}\n";

    let mut manifest = Manifest::new(META, "demo", "lib");
    let t_root = transform(root, "src/lib.rs", META, 0, true).expect("root");
    let t_other = transform(other, "src/m.rs", META, 1, false).expect("other");
    manifest.add_file("src/lib.rs", &t_root);
    manifest.add_file("src/m.rs", &t_other);

    let json: serde_json::Value =
        serde_json::from_str(&manifest.to_json().expect("serialise")).expect("valid json");

    assert_eq!(json["unit"], META);
    assert_eq!(json["crate_name"], "demo");
    assert_eq!(json["crate_type"], "lib");
    assert_eq!(json["fell_back"], false);
    assert_eq!(json["unreached_files"], serde_json::json!([]));

    // Keyed by the ORIGINAL workspace-relative path, never a mirror path.
    assert_eq!(
        json["files"]["src/lib.rs"],
        serde_json::json!([{"site": 0, "qualname": "a", "firstlineno": 1}])
    );
    assert_eq!(
        json["files"]["src/m.rs"],
        serde_json::json!([{"site": 1, "qualname": "m::b", "firstlineno": 2}])
    );

    // Skips from every file land in one list, each naming its own file.
    assert_eq!(
        json["skipped"],
        serde_json::json!([
            {"file": "src/lib.rs", "qualname": "c", "line": 2, "reason": "const"}
        ])
    );
}
