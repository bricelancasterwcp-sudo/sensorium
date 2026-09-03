//! Hand-built wire-format v2 bytes and the JSON siblings, for `tests/convert.rs`.
//!
//! Every byte here is written from the wire block in
//! `.superpowers/sdd/2026-09-02-sensorium-rung2-recorder-v1/task-6-brief.md`
//! (reproduced in `rust/HONESTY.md` §4 and `rust/cargo-sensorium/src/convert/
//! spool.rs`'s doc comment) -- never by running the runtime. A converter bug
//! that also existed in the runtime's writer would pass a fixture built from
//! the writer; it cannot pass one built from the spec.

#![allow(dead_code)]

use std::path::{Path, PathBuf};

const HEADER_FIXED: usize = 28;

/// One `<pid>.<serial>.spool` file under construction.
pub struct SpoolBuilder {
    pid: u32,
    serial: u32,
    name: String,
    records_dropped: u64,
    truncated: u64,
    body: Vec<u8>,
}

impl SpoolBuilder {
    #[must_use]
    pub fn new(pid: u32, serial: u32, name: &str) -> SpoolBuilder {
        SpoolBuilder {
            pid,
            serial,
            name: name.to_owned(),
            records_dropped: 0,
            truncated: 0,
            body: Vec::new(),
        }
    }

    #[must_use]
    pub fn records_dropped(mut self, n: u64) -> SpoolBuilder {
        self.records_dropped = n;
        self
    }

    #[must_use]
    pub fn truncated(mut self, n: u64) -> SpoolBuilder {
        self.truncated = n;
        self
    }

    /// unit_id in bits 31..24, site index in bits 23..0.
    #[must_use]
    pub fn call(self, seq: u64, ts_ns: u64, unit_id: u8, site_index: u32) -> SpoolBuilder {
        let site = (u32::from(unit_id) << 24) | (site_index & 0x00ff_ffff);
        self.raw(seq, ts_ns, site, 1, 0, &[])
    }

    fn ret(
        self,
        seq: u64,
        ts_ns: u64,
        unit_id: u8,
        site_index: u32,
        outcome: u8,
        payload: &[u8],
    ) -> SpoolBuilder {
        let site = (u32::from(unit_id) << 24) | (site_index & 0x00ff_ffff);
        self.raw(seq, ts_ns, site, 2, outcome, payload)
    }

    /// RETURN, outcome `ok`, tag 1 (debug text).
    #[must_use]
    pub fn ret_ok_dbg(
        self,
        seq: u64,
        ts_ns: u64,
        unit_id: u8,
        site_index: u32,
        text: &str,
        truncated: bool,
    ) -> SpoolBuilder {
        let mut payload = vec![1u8, u8::from(truncated)];
        payload.extend_from_slice(text.as_bytes());
        self.ret(seq, ts_ns, unit_id, site_index, 1, &payload)
    }

    /// RETURN, outcome `err`, tag 1 (debug text).
    #[must_use]
    pub fn ret_err_dbg(
        self,
        seq: u64,
        ts_ns: u64,
        unit_id: u8,
        site_index: u32,
        text: &str,
    ) -> SpoolBuilder {
        let mut payload = vec![1u8, 0u8];
        payload.extend_from_slice(text.as_bytes());
        self.ret(seq, ts_ns, unit_id, site_index, 2, &payload)
    }

    /// RETURN, outcome `none`, tag 0 (no value) -- what a `-> ()` fn's guard
    /// writes (the transformer never wraps its exits), and what a `?`-bypass
    /// on a value fn writes too.
    #[must_use]
    pub fn ret_none(self, seq: u64, ts_ns: u64, unit_id: u8, site_index: u32) -> SpoolBuilder {
        self.ret(seq, ts_ns, unit_id, site_index, 0, &[0u8, 0u8])
    }

    /// RETURN, tag 2 (unread: no `Debug` impl, or one that panicked), at
    /// whatever `outcome` the value's own `Result` shape produced.
    #[must_use]
    pub fn ret_unread(
        self,
        seq: u64,
        ts_ns: u64,
        unit_id: u8,
        site_index: u32,
        outcome: u8,
    ) -> SpoolBuilder {
        self.ret(seq, ts_ns, unit_id, site_index, outcome, &[2u8, 0u8])
    }

    /// RETURN, outcome `panic` (a frame that unwound).
    #[must_use]
    pub fn ret_panic(self, seq: u64, ts_ns: u64, unit_id: u8, site_index: u32) -> SpoolBuilder {
        self.ret(seq, ts_ns, unit_id, site_index, 3, &[0u8, 0u8])
    }

    #[must_use]
    pub fn panic_record(self, seq: u64, ts_ns: u64, loc: &str, msg: &str) -> SpoolBuilder {
        let mut payload = (loc.len() as u16).to_le_bytes().to_vec();
        payload.extend_from_slice(loc.as_bytes());
        payload.extend_from_slice(msg.as_bytes());
        self.raw(seq, ts_ns, 0, 3, 0, &payload)
    }

    #[must_use]
    pub fn thread_end(self, seq: u64, ts_ns: u64) -> SpoolBuilder {
        self.raw(seq, ts_ns, 0, 255, 0, &[])
    }

    /// Any record, by the raw wire fields -- what the "backwards seq" and
    /// "torn tail" fixtures need, since those are not shapes the typed
    /// helpers above can produce on purpose.
    #[must_use]
    pub fn raw(
        mut self,
        seq: u64,
        ts_ns: u64,
        site: u32,
        kind: u8,
        outcome: u8,
        payload: &[u8],
    ) -> SpoolBuilder {
        self.body.extend_from_slice(&seq.to_le_bytes());
        self.body.extend_from_slice(&ts_ns.to_le_bytes());
        self.body.extend_from_slice(&site.to_le_bytes());
        self.body.push(kind);
        self.body.push(outcome);
        self.body
            .extend_from_slice(&(payload.len() as u16).to_le_bytes());
        self.body.extend_from_slice(payload);
        self
    }

    /// Append `n` zero bytes: an unwritten (kind-0) tail, or -- for the
    /// "record past EOF" shape -- an unfinished trailing chunk.
    #[must_use]
    pub fn zero_tail(mut self, n: usize) -> SpoolBuilder {
        self.body.extend(std::iter::repeat_n(0u8, n));
        self
    }

    #[must_use]
    pub fn bytes(&self) -> Vec<u8> {
        let mut out = vec![0u8; HEADER_FIXED];
        out[0..4].copy_from_slice(b"SNSR");
        out[4] = 2; // version
        out[5] = 0; // flags
        out[6..8].copy_from_slice(&(self.name.len() as u16).to_le_bytes());
        out[8..12].copy_from_slice(&self.serial.to_le_bytes());
        out[12..20].copy_from_slice(&self.records_dropped.to_le_bytes());
        out[20..28].copy_from_slice(&self.truncated.to_le_bytes());
        out.extend_from_slice(self.name.as_bytes());
        out.extend_from_slice(&self.body);
        out
    }

    /// Write `<dir>/<pid>.<serial>.spool`.
    pub fn write(&self, dir: &Path) -> PathBuf {
        std::fs::create_dir_all(dir).unwrap();
        let path = dir.join(format!("{}.{}.spool", self.pid, self.serial));
        std::fs::write(&path, self.bytes()).unwrap();
        path
    }
}

/// `<dir>/<pid>.proc.json`.
pub fn write_proc_header(
    dir: &Path,
    pid: u32,
    ppid: u32,
    exe: &str,
    units: &[(u8, &str)],
    refused: Option<&str>,
) -> PathBuf {
    let units_obj: serde_json::Map<String, serde_json::Value> = units
        .iter()
        .map(|(id, metadata)| (id.to_string(), serde_json::json!(metadata)))
        .collect();
    let refused_val = refused.map_or(serde_json::Value::Null, |m| serde_json::json!({"at": m}));
    let body = serde_json::json!({
        "pid": pid,
        "ppid": ppid,
        "exe": exe,
        "argv": [exe],
        "cwd": "/w",
        "start_ns": 1_000_000_000u64,
        "start_realtime_ns": 1_700_000_000_000_000_000u64,
        "env": {},
        "env_hash": "0000000000000000",
        "units": units_obj,
        "refused": refused_val,
        "rt_version": "sensorium-rt 0.1.0",
    });
    let path = dir.join(format!("{pid}.proc.json"));
    std::fs::create_dir_all(dir).unwrap();
    std::fs::write(&path, serde_json::to_vec(&body).unwrap()).unwrap();
    path
}

/// `<dir>/<pid>.runner.json`.
pub fn write_runner_record(
    dir: &Path,
    pid: u32,
    exit_status: Option<i32>,
    signal: Option<i32>,
) -> PathBuf {
    let body = serde_json::json!({
        "pid": pid,
        "exit_status": exit_status,
        "signal": signal,
        "wall_start_ts": 1.0,
        "wall_end_ts": 2.0,
        "argv": ["/w/target/deps/bin"],
    });
    let path = dir.join(format!("{pid}.runner.json"));
    std::fs::create_dir_all(dir).unwrap();
    std::fs::write(&path, serde_json::to_vec(&body).unwrap()).unwrap();
    path
}

/// `<dir>/invocation.json`.
pub fn write_invocation(dir: &Path, invocation: &str, workspace_root: &str, target_dir: &str) {
    let body = serde_json::json!({
        "invocation": invocation,
        "subcommand": "test",
        "cargo_args": ["test"],
        "tier": "call",
        "toolchain": "rustc 1.96.0",
        "rustc_path": "/u/bin/rustc",
        "host": "x86_64-unknown-linux-gnu",
        "profile": "dev",
        "workspace_root": workspace_root,
        "target_dir": target_dir,
        "tool_hash": "0123456789abcdef",
        "driver_version": "cargo-sensorium 0.1.0",
        "start_ts": 1_700_000_000.0,
        "end_ts": 1_700_000_001.0,
        "cargo_exit": 0,
    });
    std::fs::create_dir_all(dir).unwrap();
    std::fs::write(
        dir.join("invocation.json"),
        serde_json::to_vec(&body).unwrap(),
    )
    .unwrap();
}

/// One site entry of a manifest's `files` map.
pub struct SiteSpec {
    pub site: u32,
    pub qualname: &'static str,
    pub firstlineno: u32,
    pub ret: &'static str,
}

#[must_use]
pub fn site(site: u32, qualname: &'static str, firstlineno: u32, ret: &'static str) -> SiteSpec {
    SiteSpec {
        site,
        qualname,
        firstlineno,
        ret,
    }
}

/// `<manifests dir>/<metadata>.json`.
#[allow(clippy::too_many_arguments)] // test scaffolding mirroring the JSON shape 1:1
pub fn write_manifest(
    manifests_dir: &Path,
    metadata: &str,
    crate_name: &str,
    files: &[(&str, &[SiteSpec])],
    source_hashes: &[(&str, &str)],
    fell_back: bool,
    fallback_reason: Option<&str>,
    unreached_files: &[&str],
) {
    let files_obj: serde_json::Map<String, serde_json::Value> = files
        .iter()
        .map(|(file, sites)| {
            let arr: Vec<serde_json::Value> = sites
                .iter()
                .map(|s| serde_json::json!({"site": s.site, "qualname": s.qualname, "firstlineno": s.firstlineno, "ret": s.ret}))
                .collect();
            ((*file).to_owned(), serde_json::json!(arr))
        })
        .collect();
    let hashes_obj: serde_json::Map<String, serde_json::Value> = source_hashes
        .iter()
        .map(|(f, h)| ((*f).to_owned(), serde_json::json!(h)))
        .collect();
    let body = serde_json::json!({
        "unit": metadata,
        "crate_name": crate_name,
        "crate_type": "lib",
        "files": files_obj,
        "skipped": [],
        "spawns": [],
        "source_hashes": hashes_obj,
        "fell_back": fell_back,
        "fallback_reason": fallback_reason,
        "unreached_files": unreached_files,
        "appended_line": {},
    });
    std::fs::create_dir_all(manifests_dir).unwrap();
    std::fs::write(
        manifests_dir.join(format!("{metadata}.json")),
        serde_json::to_vec(&body).unwrap(),
    )
    .unwrap();
}
