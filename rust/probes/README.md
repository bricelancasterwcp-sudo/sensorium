# `probes/` — the mechanics probe workspace

A workspace small enough to read whole and shaped to make every promise in
[`rust/HONESTY.md`](../HONESTY.md) falsifiable in a few seconds. It is what
[`rust/tests/mechanics.sh`](../tests/mechanics.sh) records, builds twice,
edits, aborts, blocks and diffs; the same endpoints run against a real
workspace in
[the acceptance document](../../docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md).

Run the checks:

    rust/tests/mechanics.sh

They build into `$SENSORIUM_PROBE_TARGET` when that is set — point it at a
directory on a different filesystem from these sources and the run proves that
it is one, which is the configuration the acceptance run uses — and into
`ws/target` otherwise.

## Its own workspace

`probes/ws` is excluded from `rust/`'s workspace (`exclude = ["probes"]`)
because the driver treats it as a *target* workspace: `cargo sensorium test` is
run from here, and `RUSTC_WORKSPACE_WRAPPER` must see these packages as the
members. It has its own `Cargo.lock`, committed, and byte-identity of that file
across a whole run is one of the checks.

## Layout, and what each piece is for

```
probes/
├── README.md                       this file
├── ext/                            probe-ext — NOT a workspace member
│   ├── Cargo.toml
│   └── src/lib.rs                  the control: cargo compiles it, never wraps it
└── ws/
    ├── Cargo.toml                  members = probe-core, probe-app
    ├── Cargo.lock                  committed; byte-identity is a check
    ├── probe-core/
    │   └── src/
    │       ├── lib.rs              crate root: mod-rs rules, and the doctest
    │       ├── helper.rs           a sibling file module
    │       ├── values.rs           Result, !Debug and Debug-panicking returns
    │       ├── renamed_source.rs   reached only via #[path]
    │       └── sub/
    │           ├── mod.rs          a directory module
    │           └── leaf.rs         child of a mod.rs — BESIDE it, not under sub/sub/
    └── probe-app/
        ├── src/
        │   ├── lib.rs              crate root; an inline mod; the check bodies
        │   ├── deep.rs             a NON-mod-rs file …
        │   ├── deep/inner.rs       … whose children live under its stem
        │   ├── nested/nested_child.rs   #[path] inside an inline mod
        │   ├── maybe.rs            declared with #[cfg_attr(windows, path = …)]
        │   ├── maybe_windows.rs
        │   └── main.rs             the [[bin]] app-bin, `--abort` and all
        └── tests/
            ├── e7.rs               the two E7(a) probes
            ├── threads.rs          std::thread::spawn — the naming check
            ├── spawn_bin.rs        spawns app-bin — the child_runs check
            ├── nested_panic.rs     a panic two frames deep, and one caught
            ├── abort_child.rs      a child that aborts inside an open frame
            └── blocked.rs          a worker still blocked at process exit
```

## Why each piece is shaped the way it is

- **`probe-core`, not `core`.** A lib *target* named `core` collides with the
  sysroot crate and the unit does not build at all.
- **`probe-ext` lives outside `ws/`.** Cargo auto-adopts path dependencies that
  reside *inside* the workspace directory as members. Putting it at
  `probes/ext` makes "not a member" a property of the layout rather than of an
  `exclude` list. No manifest may ever be written for it: cargo never hands a
  non-member to the wrapper.
- **No registry dependency.** The probe carried `libc` so that a unit the
  wrapper links `sensorium_rt` into already had a `libc` in its graph at a
  different `-C metadata` — rung 1's open question. Plan decision D1 closed it
  by construction (`sensorium-rt` has no dependencies and is built by one bare
  rustc invocation), so the second `libc` cannot exist and the dependency only
  cost every CI run a network round trip. `probe-ext` still covers "a crate
  cargo compiles and the wrapper never sees".
- **`sensorium-rt` is NOT a dependency.** Linkage is the wrapper's job; a
  declared dependency would make the measurement circular and would put the
  runtime in `Cargo.lock`.
- **The E7 tests are `#[should_panic]`.** The panic hook still prints
  `panicked at <file>:<line>:<col>` and the backtrace under `--nocapture` —
  which is the text E7 diffs — while the suite stays green in all three arms.
- **`threads.rs` uses `std::thread::spawn`, not `Builder`.** Only the plain
  path form is rewritten to `::sensorium_rt::spawn_child`; the builder form
  carries a name of its own and is declared rather than rewritten
  (`rust/HONESTY.md` §3). The check reads the name the rewrite derives.
- **`abort_child.rs` spawns a child rather than aborting in-process.** A test
  binary that aborted would take libtest and every other check with it. The
  child is also the case the recorder has to be honest about twice over: its
  own exit is `unwitnessed` (sensorium's runner did not start it) and its
  records survive anyway, because a spool is a `MAP_SHARED` mapping the kernel
  owns.
- **`blocked.rs` hands back a handshake, not a sleep.** The worker reports that
  its instrumented work is done before it blocks, so the check is deterministic
  where a timeout would have been a guess.
- **`maybe.rs` is a declared gap.** `#[cfg_attr(.., path = ..)]` is not
  evaluated by the wrapper (plan decision D3), so the module is reported in
  `unreached_files` and its fns are never instrumented. The manifest says so
  out loud, and `sensorium info` prints it.
