//! The `RUSTC_WORKSPACE_WRAPPER` role. Cargo's contract: `argv[1]` is the real
//! rustc, `argv[2..]` is what rustc would have been given, cwd is the workspace
//! root and the crate root is a workspace-relative path.
//!
//! One unit in, one rustc run out. The argv cargo built is passed through
//! UNCHANGED except for two appended linkage flags -- that is the whole reason
//! `file!()`, panic locations and dep-info survive (E7, E8).

use std::collections::BTreeSet;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

use sensorium_transform::{transform, Manifest};

use crate::args::{self, Plan};
use crate::mirror::{self, Lock, Rewrite};
use crate::modtree::{self, DiskFs};
use crate::sha256;

/// How long a unit waits for another unit's mirror update before giving up.
const LOCK_TIMEOUT: Duration = Duration::from_secs(120);

/// Run the wrapper. Returns the exit code to leave with.
pub fn run(argv: &[String]) -> i32 {
    let rustc = &argv[1];
    let rest = &argv[2..];
    match args::plan(rest) {
        Plan::PassThrough(_) => passthrough(rustc, rest),
        Plan::Instrument {
            crate_name,
            crate_type,
            metadata,
            crate_root,
        } => match instrument(rustc, rest, &crate_name, &crate_type, &metadata, &crate_root) {
            Ok(code) => code,
            Err(e) => {
                eprintln!("sensorium: wrapper error on {crate_name} ({metadata}): {e}");
                eprintln!("sensorium: unit {crate_name} ({metadata}) fell back to the real tree: wrapper error");
                passthrough(rustc, rest)
            }
        },
    }
}

/// Run rustc exactly as cargo asked, from cargo's own cwd.
fn passthrough(rustc: &str, rest: &[String]) -> i32 {
    Command::new(rustc)
        .args(rest)
        .status()
        .map_or(101, |s| s.code().unwrap_or(101))
}

struct Env {
    ws: PathBuf,
    target: PathBuf,
    rlib: String,
    deps: String,
    tool_hash: String,
}

fn read_env(ws: &Path) -> Result<Env, String> {
    let target = std::env::var_os("SENSORIUM_TARGET")
        .map_or_else(|| ws.join("target"), PathBuf::from);
    let rlib = std::env::var("SENSORIUM_RT_RLIB")
        .map_err(|_| "SENSORIUM_RT_RLIB is unset: the driver did not set up linkage".to_owned())?;
    let deps = std::env::var("SENSORIUM_RT_DEPS")
        .map_err(|_| "SENSORIUM_RT_DEPS is unset: the driver did not set up linkage".to_owned())?;
    let tool_hash = std::env::var("SENSORIUM_TOOL_HASH").unwrap_or_else(|_| "unknown".to_owned());
    Ok(Env {
        ws: ws.to_path_buf(),
        target,
        rlib,
        deps,
        tool_hash,
    })
}

fn instrument(
    rustc: &str,
    rest: &[String],
    crate_name: &str,
    crate_type: &str,
    metadata: &str,
    crate_root: &str,
) -> Result<i32, String> {
    let ws = std::env::current_dir().map_err(|e| format!("cannot read cwd: {e}"))?;
    let env = read_env(&ws)?;
    if Path::new(crate_root).is_absolute() {
        // Cargo passes workspace members a RELATIVE root. An absolute one means
        // this is not the shape the mirror was designed for; say so and do not
        // pretend to instrument it.
        eprintln!(
            "sensorium: unit {crate_name} ({metadata}) fell back to the real tree: absolute crate root {crate_root}"
        );
        return Ok(passthrough(rustc, rest));
    }

    let sens = env.target.join("sensorium");
    let walk = modtree::walk(&DiskFs { root: &env.ws }, crate_root);
    let ws_for_read = env.ws.clone();
    let UnitPlan {
        mut manifest,
        rewrites,
    } = build_unit(
        &move |rel: &str| std::fs::read_to_string(ws_for_read.join(rel)).ok(),
        &walk,
        metadata,
        crate_name,
        crate_type,
    );

    let manifest_path = sens.join("manifests").join(format!("{metadata}.json"));
    write_manifest(&manifest_path, &manifest)?;

    let mirror_dir = sens.join("mirror");
    {
        let _lock = Lock::acquire(&sens.join("mirror.lock"), LOCK_TIMEOUT)
            .map_err(|e| format!("mirror lock: {e}"))?;
        mirror::materialise(
            &env.ws,
            &mirror_dir,
            &sens.join("cache"),
            &env.tool_hash,
            &rewrites,
        )
        .map_err(|e| format!("mirror: {e}"))?;
    }

    let mut instrumented: Vec<String> = rest.to_vec();
    instrumented.push("--extern".to_owned());
    instrumented.push(format!("sensorium_rt={}", env.rlib));
    instrumented.push("-L".to_owned());
    instrumented.push(format!("dependency={}", env.deps));
    // MEASURED, not belt and braces (spec 2.2 called it optional): rustc
    // records the compilation directory in DWARF (`DW_AT_comp_dir`), and that
    // is the mirror. `file!()` and panic locations stay workspace-relative
    // without this -- but std's backtrace printer resolves frames against
    // comp_dir, so E7's backtrace frames came out as absolute mirror paths
    // until this flag was added. It is load-bearing.
    instrumented.push(format!(
        "--remap-path-prefix={}={}",
        mirror_dir.display(),
        env.ws.display()
    ));

    let out = Command::new(rustc)
        .args(&instrumented)
        .current_dir(&mirror_dir)
        .stdin(Stdio::inherit())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("cannot run rustc: {e}"))?;
    if out.status.success() {
        // Captured only so a failure can be swallowed before cargo parses it;
        // on success every byte is forwarded verbatim, warnings included.
        let _ = std::io::stdout().write_all(&out.stdout);
        let _ = std::io::stderr().write_all(&out.stderr);
        return Ok(0);
    }

    let stderr = String::from_utf8_lossy(&out.stderr);
    eprintln!(
        "sensorium: unit {crate_name} ({metadata}) fell back to the real tree: {}",
        first_error_line(&stderr)
    );
    manifest.fell_back = true;
    write_manifest(&manifest_path, &manifest)?;
    Ok(passthrough(rustc, rest))
}

/// The manifest and the rewrites for one unit: everything the wrapper decides
/// before it touches the filesystem, so it can be tested without one.
pub struct UnitPlan {
    pub manifest: Manifest,
    pub rewrites: Vec<Rewrite>,
}

/// Transform every file of a unit, in the walk's order (crate root FIRST).
///
/// Site indices run contiguously across the unit's files from 0 -- spec 2.4:
/// a site id is `unit_id:8 | site:24`, so a unit's sites must be one range, not
/// one range per file. A file that cannot be read or cannot be parsed goes to
/// `unreached_files` and is left unrewritten; the mirror then symlinks the
/// original, so the unit still compiles minus those guards.
pub fn build_unit(
    read: &dyn Fn(&str) -> Option<String>,
    walk: &modtree::Walk,
    metadata: &str,
    crate_name: &str,
    crate_type: &str,
) -> UnitPlan {
    let mut manifest = Manifest::new(metadata, crate_name, crate_type);
    manifest.unreached_files = walk.unreached.clone();
    let mut rewrites: Vec<Rewrite> = Vec::new();
    let mut next_site: u32 = 0;
    for (i, rel) in walk.files.iter().enumerate() {
        let Some(source) = read(rel) else {
            manifest.unreached_files.push(rel.clone());
            continue;
        };
        match transform(&source, rel, metadata, next_site, i == 0) {
            Ok(t) => {
                next_site += u32::try_from(t.sites.len()).unwrap_or(u32::MAX);
                manifest.add_file(rel, &t);
                rewrites.push(Rewrite {
                    rel: rel.clone(),
                    content: t.source,
                    source_hash: sha256::hex(source.as_bytes()),
                });
            }
            Err(_) => manifest.unreached_files.push(rel.clone()),
        }
    }
    dedup(&mut manifest.unreached_files);
    // The crate root is where `__SENSORIUM_UNIT` lives. If it could not be
    // rewritten but its children were, every guard in the unit references a
    // static that does not exist: a guaranteed rustc failure, a guaranteed
    // fallback, and the unit compiled twice for nothing. Instrument all of a
    // unit or none of it.
    let root_rewritten = walk
        .files
        .first()
        .is_some_and(|root| rewrites.first().is_some_and(|r| &r.rel == root));
    if !root_rewritten {
        rewrites.clear();
        manifest.files.clear();
        manifest.skipped.clear();
        manifest.appended_line.clear();
    }
    UnitPlan { manifest, rewrites }
}

fn write_manifest(path: &Path, manifest: &Manifest) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("cannot create {}: {e}", parent.display()))?;
    }
    let json = manifest
        .to_json()
        .map_err(|e| format!("cannot serialise manifest: {e}"))?;
    std::fs::write(path, json).map_err(|e| format!("cannot write {}: {e}", path.display()))
}

fn dedup(v: &mut Vec<String>) {
    let mut seen = BTreeSet::new();
    v.retain(|s| seen.insert(s.clone()));
}

/// The one line of rustc's output that says what went wrong. Cargo drives
/// rustc with `--error-format=json`, so prefer the first message's `rendered`
/// or `message` field; fall back to the first non-empty line.
#[must_use]
pub fn first_error_line(stderr: &str) -> String {
    for line in stderr.lines() {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
            if v.get("level").and_then(|l| l.as_str()) == Some("error") {
                if let Some(m) = v.get("message").and_then(|m| m.as_str()) {
                    return m.to_owned();
                }
            }
            continue;
        }
        let t = line.trim();
        if !t.is_empty() {
            return t.to_owned();
        }
    }
    "rustc failed with no diagnostic".to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_first_json_error_is_the_reported_line() {
        let stderr = concat!(
            r#"{"level":"warning","message":"unused variable"}"#,
            "\n",
            r#"{"level":"error","message":"cannot find crate `sensorium_rt`"}"#,
            "\n",
        );
        assert_eq!(first_error_line(stderr), "cannot find crate `sensorium_rt`");
    }

    #[test]
    fn plain_stderr_falls_back_to_its_first_non_empty_line() {
        assert_eq!(first_error_line("\n\nerror: boom\nnote: x\n"), "error: boom");
    }

    #[test]
    fn silence_is_reported_as_silence_not_as_success() {
        assert_eq!(first_error_line(""), "rustc failed with no diagnostic");
    }

    fn plan_of(files: &[(&str, &str)], unreached: &[&str]) -> UnitPlan {
        let map: std::collections::BTreeMap<String, String> = files
            .iter()
            .map(|(p, c)| ((*p).to_owned(), (*c).to_owned()))
            .collect();
        let walk = crate::modtree::Walk {
            files: files.iter().map(|(p, _)| (*p).to_owned()).collect(),
            unreached: unreached.iter().map(|s| (*s).to_owned()).collect(),
        };
        build_unit(
            &move |rel: &str| map.get(rel).cloned(),
            &walk,
            "deadbeef",
            "demo",
            "lib",
        )
    }

    #[test]
    fn the_manifest_has_the_wire_shape_the_converter_reads() {
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m;\npub fn root() {}\n"),
                ("a/src/m.rs", "pub fn one() {}\npub const fn two() -> u8 { 2 }\n"),
            ],
            &["a/src/ghost.rs"],
        );
        let json: serde_json::Value =
            serde_json::from_str(&plan.manifest.to_json().unwrap()).unwrap();
        assert_eq!(json["unit"], "deadbeef");
        assert_eq!(json["crate_name"], "demo");
        assert_eq!(json["crate_type"], "lib");
        assert_eq!(json["fell_back"], false);
        assert_eq!(json["unreached_files"], serde_json::json!(["a/src/ghost.rs"]));
        // Keyed by the ORIGINAL workspace-relative path, never a mirror path.
        assert_eq!(
            json["files"]["a/src/lib.rs"],
            serde_json::json!([{"site": 0, "qualname": "root", "firstlineno": 2}])
        );
        assert_eq!(
            json["files"]["a/src/m.rs"],
            serde_json::json!([{"site": 1, "qualname": "one", "firstlineno": 1}])
        );
        // The `const fn` is declared, not silently absent.
        assert_eq!(json["skipped"][0]["reason"], "const");
        assert_eq!(json["skipped"][0]["file"], "a/src/m.rs");
        // `appended_line` is recorded per file, and false where a file has items.
        assert_eq!(json["appended_line"]["a/src/lib.rs"], false);
        assert_eq!(json["appended_line"]["a/src/m.rs"], false);
    }

    #[test]
    fn site_indices_run_contiguously_across_the_units_files() {
        // Spec 2.4 packs `unit_id:8 | site:24`, so a unit's sites are ONE
        // range. Number per file and the second file restarts at 0, colliding
        // with the first file's sites in every downstream join.
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m;\nfn a() {}\nfn b() {}\n"),
                ("a/src/m.rs", "fn c() {}\nfn d() {}\n"),
            ],
            &[],
        );
        let sites: Vec<u32> = plan
            .manifest
            .files
            .values()
            .flatten()
            .map(|s| s.site)
            .collect();
        let mut sorted = sites.clone();
        sorted.sort_unstable();
        assert_eq!(sorted, [0, 1, 2, 3], "got {sites:?}");
    }

    #[test]
    fn only_the_crate_root_gets_the_unit_static() {
        let plan = plan_of(
            &[
                ("a/src/lib.rs", "mod m;\nfn a() {}\n"),
                ("a/src/m.rs", "fn c() {}\n"),
            ],
            &[],
        );
        let root = &plan.rewrites[0];
        let child = &plan.rewrites[1];
        assert_eq!(root.rel, "a/src/lib.rs");
        assert!(root.content.contains("__SENSORIUM_UNIT: ::sensorium_rt::Unit"), "{}", root.content);
        assert!(!child.content.contains("static __SENSORIUM_UNIT"), "{}", child.content);
        assert!(child.content.contains("::sensorium_rt::enter"), "{}", child.content);
    }

    #[test]
    fn an_unparseable_file_is_unreached_and_is_not_rewritten() {
        let plan = plan_of(
            &[("a/src/lib.rs", "fn a() {}\n"), ("a/src/bad.rs", "fn ( {")],
            &[],
        );
        assert_eq!(plan.manifest.unreached_files, ["a/src/bad.rs"]);
        assert_eq!(plan.rewrites.len(), 1);
        assert_eq!(plan.rewrites[0].rel, "a/src/lib.rs");
    }

    #[test]
    fn a_unit_whose_crate_root_cannot_be_rewritten_is_left_wholly_alone() {
        // The root does not parse, so it gets no `__SENSORIUM_UNIT` static.
        // Rewriting the child anyway would splice guards that reference a
        // static that is not there: rustc fails, the fallback fires, and the
        // unit is compiled twice to end up exactly where doing nothing would
        // have left it.
        let plan = plan_of(&[("a/src/lib.rs", "mod m; fn ( {"), ("a/src/m.rs", "fn c() {}\n")], &[]);
        assert!(plan.rewrites.is_empty(), "{:?}", plan.rewrites.iter().map(|r| &r.rel).collect::<Vec<_>>());
        assert!(plan.manifest.files.is_empty());
        assert_eq!(plan.manifest.unreached_files, ["a/src/lib.rs"]);
    }

    #[test]
    fn a_file_the_reader_cannot_open_is_unreached_not_silently_skipped() {
        let walk = crate::modtree::Walk {
            files: vec!["a/src/lib.rs".to_owned(), "a/src/gone.rs".to_owned()],
            unreached: vec![],
        };
        let plan = build_unit(
            &|rel: &str| (rel == "a/src/lib.rs").then(|| "fn a() {}\n".to_owned()),
            &walk,
            "m",
            "demo",
            "lib",
        );
        assert_eq!(plan.manifest.unreached_files, ["a/src/gone.rs"]);
    }

    #[test]
    fn dedup_keeps_first_occurrence_order() {
        let mut v = vec!["b".to_owned(), "a".to_owned(), "b".to_owned()];
        dedup(&mut v);
        assert_eq!(v, ["b", "a"]);
    }
}
