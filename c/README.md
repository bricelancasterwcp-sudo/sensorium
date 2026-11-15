# c/: the sensorium recorder for C

Record what a C program actually did; ask it the same questions.

`sensorium c run -- <cmd>` instruments a debug build and writes one
sensorium trace per process. Same SQLite format 4 as the other recorders,
read by the same `sensorium` command line. v1 is Linux x86-64, gcc and
clang, at `-O0` or `-Og`.

What a trace can and cannot say is [`HONESTY.md`](HONESTY.md). The trace
contract is [`../docs/TRACE-FORMAT.md`](../docs/TRACE-FORMAT.md).

## Record

    sensorium c run -- <cmd>
    sensorium c run --strict -- make test
    sensorium-cc -O0 hello.c -o hello

Everything after `--` is your command, spawned as typed. The driver waits,
converts each process spool into a trace under `$SENSORIUM_DIR/traces`,
and exits with the command's status. A crash it waited on stores
`exit_signal` and `exit_status_basis: waited`.

For that command the driver sets:

- `CC` to the `sensorium-cc` wrapper (`sensorium.c.cc:main`).
- A `PATH` directory of shims named `gcc`, `cc` and `clang`. A build that
  calls the compiler by those names is instrumented even when it ignores
  `CC`, which is how `make` works.
- `CFLAGS`, carrying the same debug-build instrumentation the wrapper adds,
  for a recipe that passes flags but not the wrapper.
- `CMAKE_C_COMPILER_LAUNCHER` to the wrapper. CMake keeps its own compiler
  and the wrapper prefixes it: `sensorium-cc /usr/bin/gcc ...`.

The wrapper adds `-g`, a frame pointer and `-finstrument-functions`, and
it links `c/rt/sensorium_c_rt.c`. `sensorium-cc --version` exits 0. `-O2`
(and the other optimized levels) warns on stderr. `SENSORIUM_C_STRICT=1`
turns that warning into exit 2 and does not compile.

Stdout and stderr are forwarded to your terminal and stored in the trace
`output` table (`capabilities.output` is true). Those bytes are the
driver's pipes. They are not interleaved with events. See
[`HONESTY.md`](HONESTY.md).

## The .scplan file

Beside each linked image, `<image>.scplan`. Magic `SCPL`, version 1.
Addresses are unrelocated ELF `low_pc` values. The plan says, per
function, how the return comes back (void, integer registers, SSE
registers, or memory) and where each parameter sits. `FLAG_CSTR` asks the
runtime to copy a NUL-terminated string with `process_vm_readv` (a bad
pointer is a failed read, not a crash in the recorder). The on-wire spool
the runtime writes is `sensorium.c.format`.

## What v1 records

Calls, arguments, return values, and crashes, for code the wrapper
compiled.

A crash is a fatal signal (`SIGSEGV`, `SIGBUS`, `SIGFPE`, `SIGILL`,
`SIGABRT`) or an `assert`. `exceptions` reads those as `UNCAUGHT`. They
are not C++ exceptions.

`failures` reads a `test_*` frame that `longjmp` abandoned (the Unity
shape) and does not list a later `test_*` that returned.

Threads are per-thread spools. The thread the process started on is tid
1. A crash flushes every thread, so `c/sample/threads.c` (join both
workers, then a NULL deref in main) shows both workers and the signal.

`fork` records the child pid on the parent. A child that keeps running
has its own spool. v1 does not follow `exec` into a binary the wrapper
did not build.

One `sensorium c run` is one invocation. `runs` groups that command's
traces under the command you typed, not under `cargo`.

## What is not recorded

- LINE events and locals. v1 has no `--focus` tier.
- Values from `-O2` or any optimized level other than `-Og`. The wrapper
  warns. Slots are often gone, and the value is unread.
- Architectures other than Linux x86-64, and compilers other than gcc
  and clang.
- Returns that went through a CET shadow stack. The trampoline is not
  that return, and the value is unread rather than guessed.
- Macros. A function-like macro never becomes a call.
- Varargs. The plan has no types for `...`, so those arguments are unread.

## longjmp

The return trampoline replaces a saved return address. `longjmp` would
otherwise land on a trampoline whose frame is gone. The runtime
interposes `longjmp` and `siglongjmp`, drops the abandoned trampolines,
and records how many frames the jump left. The converter closes those
frames. It does not write a RAISE. `c/sample/longjmp_test.c` is the
regression: `test_one` jumps, `test_two` returns 42, the process exits 0.

## Redaction

The same name rule as the other recorders, applied to the environment
the driver stores. `API_KEY` and the other compound secret names are
stored as `<redacted>`. `redaction.mode` is `on` unless
`SENSORIUM_NO_REDACT` is set. The plaintext does not go into the trace
file.

## Samples

| File | Why it is here |
|---|---|
| `sample/stats.c` | `sum_range` skips the last element (`{2,4,6,8}` returns 12). `name_len` calls `strlen` on NULL when the name is absent. |
| `sample/assert_div.c` | `checked_div(10, 2)` returns, then `checked_div(10, 0)` asserts with a message. |
| `sample/threads.c` | Two pthreads call `worker_fn`, main joins them, then main dereferences NULL. |
| `sample/longjmp_test.c` | `test_one` fails by `longjmp`, `test_two` runs next, exit 0. |
| `sample/types.c` | An int, a double, a `struct point` returned in registers, a struct bigger than 16 bytes returned in memory, and a `const char *`, an enum and a struct passed by value. No crash. |
| `sample/fib.c` | `fib(n)` from argv, for the overhead timing below. |
| `sample/make/` | Default target builds and runs a tiny program with `$(CC)` and `$(CFLAGS)`. |
| `sample/cmake/` | One CMake target, `main` returns 0. `sensorium c run -- cmake -S . -B build` then `cmake --build build`. |
| `sample/meson/` | The same idea for meson. |

## Overhead

Measured on Linux 6.12.113+ x86_64 (8 CPUs), gcc 14.2.0, CPython 3.13.5.
`sample/fib.c` `fib(27)` is 635,622 calls (`fib` and `main`) and prints
196418. These numbers are not a gate. The same run is also in
[`../docs/overhead.md`](../docs/overhead.md).

Plain `-O0 -g -fno-inline -fno-omit-frame-pointer
-fno-optimize-sibling-calls`, best of three: 0.0018 s (0.0021, 0.0024,
0.0018).

The same flags plus `-finstrument-functions`, recording on, convert not
included, best of three: 0.432 s (0.432, 0.498, 0.537). The spool was
116,954,747 bytes each time.

One `sensorium c run` of that binary took 31.5 s wall (recording plus
convert). A separate convert of one of those spools took 84.7 s and
wrote a 176,218,112 byte trace (1,271,244 events). Convert time moved
between those two samples. The recording did not. The converter is
Python, and it is the slow part.

## Layout

`c/rt/sensorium_c_rt.c` is the runtime. A wheel ships it at
`sensorium/_c/rt/sensorium_c_rt.c` so an install without the checkout can
still compile. The driver finds the checkout copy by walking up from the
source tree; the wheel path is the extra.
