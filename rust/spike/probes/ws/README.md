# `probes/ws` — the rung-1 mechanics probe workspace

THROWAWAY SPIKE CODE (`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`).
Nothing here is product. It exists so E7 and E8 have something small, fast and
fully understood to be measured on before bloomery is touched (Task 5).

Run the checks:

```
rust/spike/tests/mechanics.sh
```

## Its own workspace

`probes/ws` is excluded from `rust/spike`'s workspace (`exclude = ["probes"]`)
because the driver treats it as a *target* workspace: `cargo sensorium test` is
run from here, and `RUSTC_WORKSPACE_WRAPPER` must see these packages as the
members. It has its own `Cargo.lock`, committed, and E8 checks it is
byte-identical before and after every run.

## Layout, and what each piece is for

```
probes/
├── ext/                       probe-ext  — NOT a workspace member
│   └── src/lib.rs
└── ws/
    ├── Cargo.toml             members = probe-core, probe-app
    ├── Cargo.lock             committed; byte-identity is a check
    ├── probe-core/
    │   └── src/
    │       ├── lib.rs         crate root: mod-rs rules
    │       ├── helper.rs      a sibling file module
    │       ├── renamed_source.rs   reached only via #[path]
    │       └── sub/
    │           ├── mod.rs     a directory module
    │           └── leaf.rs    child of a mod.rs — BESIDE it, not under sub/sub/
    └── probe-app/
        ├── src/
        │   ├── lib.rs         crate root; libc use; an inline mod
        │   ├── deep.rs        a NON-mod-rs file …
        │   ├── deep/inner.rs  … whose children live under its stem
        │   ├── nested/nested_child.rs   #[path] inside an inline mod
        │   ├── maybe.rs       declared with #[cfg_attr(windows, path = …)]
        │   ├── maybe_windows.rs
        │   └── main.rs        the [[bin]] app-bin
        └── tests/
            ├── threads.rs     spawns a named thread
            ├── spawn_bin.rs   spawns app-bin via CARGO_BIN_EXE_app-bin
            └── e7.rs          the two E7 probes
```

Deliberate choices, each with a reason:

- **`probe-core`, not `core`.** A lib *target* named `core` collides with the
  sysroot crate and the unit does not build at all. The package names differ
  from the brief's `core`/`app` for that reason only.
- **`probe-ext` lives outside `ws/`.** Cargo auto-adopts path dependencies that
  reside *inside* the workspace directory as members. Putting it at
  `probes/ext` is the only placement that makes "not a member" a property of
  the layout rather than of an `exclude` list. E8 checks that no manifest is
  ever written for it: cargo never hands a non-member to the wrapper.
- **`probe-app` depends on `libc`.** So the unit the wrapper links
  `sensorium_rt` into already has a `libc` in its graph — at a *different*
  `-C metadata` from the one the runtime was built against. Whether two `libc`
  crates can coexist in one unit is measured here, not assumed.
- **`sensorium-rt` is NOT a dependency.** Linkage is the wrapper's job; a
  declared dependency would make the measurement circular and would put the
  runtime in `Cargo.lock`.
- **The E7 tests are `#[should_panic]`.** The panic hook still prints
  `panicked at <file>:<line>:<col>` and the backtrace under `--nocapture` —
  which is the text E7 diffs — while the suite stays green in all three arms.
- **`maybe.rs` is a documented gap.** `#[cfg_attr(.., path = ..)]` is not
  evaluated by the wrapper, so the module is reported in `unreached_files` and
  its fns are never instrumented. The manifest says so out loud.
