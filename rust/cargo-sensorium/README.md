# cargo-sensorium

The [sensorium](https://github.com/bricelancasterwcp-sudo/sensorium) Rust recorder: `cargo sensorium test` and `cargo sensorium run`.

It instruments your workspace's own crates at build time and writes one [trace format 4](https://github.com/bricelancasterwcp-sudo/sensorium/blob/main/docs/TRACE-FORMAT.md) SQLite file per process, the same format the Python recorder writes.

## Install

Linux, rustc 1.96 or newer:

    cargo install cargo-sensorium

That puts `cargo-sensorium` on `PATH`, which is what makes `cargo sensorium` a cargo subcommand.

The runtime is Linux-only (`MAP_SHARED` spools, `gettid`). macOS and Windows are not supported.

Reading traces needs the Python CLI:

    pip install sensorium-trace

## Record

From a Cargo workspace:

    cargo sensorium test
    cargo sensorium run
    cargo sensorium test --focus path::to::fn

Traces land in `~/.sensorium/traces` (or `$SENSORIUM_DIR/traces`). Then:

    sensorium exceptions last
    sensorium failures last
    sensorium tree last --depth 3

Full usage, honesty limits, and what v1 does not see: [rust/README.md](https://github.com/bricelancasterwcp-sudo/sensorium/blob/main/rust/README.md).
