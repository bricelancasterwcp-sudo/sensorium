# sensorium-rt

Runtime linked into every instrumented unit of the [sensorium](https://github.com/bricelancasterwcp-sudo/sensorium) Rust recorder.

Zero dependencies. The driver compiles these sources with one bare `rustc` line and links the rlib into the target build. Linux only: thread serials come from `gettid()`/`getpid()` and each spool is a `MAP_SHARED` mapping.

Install the driver, not this crate by itself:

    cargo install cargo-sensorium

Then `cargo sensorium test` or `cargo sensorium run` from a workspace. Query traces with the Python `sensorium` CLI (`pip install sensorium-trace`).
