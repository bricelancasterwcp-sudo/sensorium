# What a C trace can and cannot say

v1, Linux x86-64, gcc and clang, debug builds (`-O0` or `-Og`). Read this
before trusting an answer. The command and the spool are
[`README.md`](README.md). The trace contract is
[`../docs/TRACE-FORMAT.md`](../docs/TRACE-FORMAT.md).

## What it can say

A call the wrapper compiled, the arguments the capture plan could read,
and the return value the trampoline recorded. A crash: a fatal signal
(`SIGSEGV`, `SIGBUS`, `SIGFPE`, `SIGILL`, `SIGABRT`) or an `assert` whose
text the runtime copied. `exceptions` reads those as uncaught. It does
not invent a catch.

A `test_*` frame that `longjmp` abandoned is a failed test for
`failures`. A later `test_*` that returned is not.

## Crashes are signals and asserts

There is no C++ exception in this recording. `SIGABRT` from `assert` is
an abort, not a thrown type. A C++ `throw` that unwinds through a C frame
is outside what v1 records, and the trace does not describe it as one.

## longjmp is not a RAISE

`longjmp` and `siglongjmp` close the frames the jump abandoned and repair
the return trampoline so the next call can still return. That close is
not a RAISE. Nothing was thrown. `c/sample/longjmp_test.c` is the case:
`test_one` jumps, `test_two` runs, the process exits 0.

## Output is the driver's pipes

Stdout and stderr in the trace are the bytes the driver read from the
pipes it gave the process. They are forwarded to the terminal as well.
They are not interleaved with call events, and an `after_event_id` on an
output row is not a claim that the program printed at that call.

## Optimized builds

`-O2` and the other optimized levels warn on stderr. Frame slots the plan
wanted are often gone, so a value may be unread. Unread is the answer,
not a reconstructed one. `SENSORIUM_C_STRICT=1` refuses the compile
(exit 2) instead of warning. `-O0` and `-Og` are the builds whose values
v1 claims to read.

## An uninstrumented frame

A PC in libc or any other object compiled without the wrapper is not a
frame the runtime entered. The converter names it from that PC (the
symbol, when the object has one) and from a callsite walk: the first
saved return address that lands in the instrumented program. That is not
a DWARF unwind and not a full stack. It is a hint about who called out.

## What is absent on purpose

No LINE events and no locals. No other architecture. No macro expansion
(a function-like macro is not a call). No types for `...`, so varargs are
unread. A return that went through a CET shadow stack is not recorded.
The value is unread rather than guessed.
