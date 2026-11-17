# sensorium-transform

Source transformer for the [sensorium](https://github.com/bricelancasterwcp-sudo/sensorium) Rust recorder.

It splices entry guards, exit operands, err-flow probes, spawn sites, and (under a `--focus`) per-statement LINE probes into the original bytes at syn's offsets, without moving a line.

This crate is a library the driver uses. Install the driver:

    cargo install cargo-sensorium
