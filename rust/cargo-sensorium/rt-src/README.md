Vendored copy of `sensorium-rt/src/*.rs`.

`build.rs` embeds these files into the `cargo-sensorium` binary so `cargo install cargo-sensorium` can compile the runtime with a bare `rustc` line without a git checkout. In the workspace, `build.rs` prefers the sibling `sensorium-rt/src` so an edit there rebuilds the driver; a unit test fails if this directory drifts from that sibling.
