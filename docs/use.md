# Use

Command reference. The short list is in [../README.md](../README.md).

## Use

    sensorium run -- pytest tests/test_fog.py     # record
    sensorium runs                                # what have I recorded
    sensorium info last                           # what am I looking at
    sensorium tree last --depth 3                 # what actually ran
    sensorium frame last --fn compute             # one activation, in full
    sensorium grep last compute --kind RETURN     # every event that mentions it
    sensorium exceptions last                     # what blew up, what got caught
    sensorium failures last                       # failed tests, and the frame they failed in
    sensorium flow last --value 1800              # where did that number come from
    sensorium flow last --object build_key:record # what happened to that object
    sensorium diff RUN_A RUN_B                    # where two runs part
    sensorium refocus last --focus fog:compute    # re-run deeper, verified
    sensorium redact --all --dry-run              # what an older store still holds
    sensorium mcp --allow-run                     # serve all of the above to a model (MCP, stdio)

Per-line state is opt-in at record time, so a predicate over locals needs a
run that captured them:

    sensorium run --focus fog:compute -- pytest tests/test_fog.py
    sensorium watch last --at fog:compute --expr 'visible > 100'

Asked against a run recorded without that `--focus`, `watch` does not report
zero hits. It reports `NOTHING WAS CHECKED` and prints the exact re-recording
command. Every example above was run as typed, against a small `fog.py` whose
`compute` sums cells into a `visible` local and whose `build_key(record)`
takes a dict, and a two-test `tests/test_fog.py`.

On an asyncio program `tree` groups by task, and from trace format 3 every
traced code object opens a frame (function, generator, coroutine, or async
generator alike) so a coroutine's callees nest under it exactly like a
plain function's do, tagged `[generator]`, `[coroutine]`, or
`[async_generator]` when the kind isn't `function`. A frame that suspended
carries a derived state as its tail: `~ cancelled (CancelledError thrown in
at Ln)`, `~ abandoned (GeneratorExit thrown in at Ln)`, `~ unwound by X
thrown in at Ln` for any other exception thrown in, or `~ suspended at Ln
at end of recording` for one still parked when recording stopped. A caller
named but not framed is still never re-parented. It started running before
recording began (`<- worker (no frame: started before recording)`), and a
trace from before frames existed keeps arc 1's `(unframed)` wording exactly.
`--focus`, `watch` and LINE capture all work inside `async def`: a focused
coroutine's locals are captured at every LINE and interleaved with its
`~ YIELD`/`~ RESUME` rows in `frame`'s timeline. `--window` is an ancestry flag, not a call-stack depth, so it
survives a suspension: another task's calls made while the windowed frame is
parked are outside the window, and the windowed frame's own calls after it
resumes are still inside. A generator or coroutine resumed on a *different*
thread from the one that started it (a sync generator first stepped where
it was made and finished from a thread pool, which is what a streaming
response does) keeps the frame it opened: its suspensions, its return and
anything it calls stay on that frame, and every row still names the thread
that produced it.

Recording captures calls, returns, raises and handled-events for code under
the working directory the run started in, so `sensorium run -- pytest ...`
traces your tests and your code, and not pytest's. `--focus module:qualname`
adds line-level capture with local-variable deltas for the named code;
`--window QUALNAME` limits that capture to what runs inside one function's
activations. Traces land in `~/.sensorium/traces` (or
`$SENSORIUM_DIR/traces`), one SQLite file per run. Rust, TypeScript and C
recorders write to the same directory, so one `runs` lists all four.

A run reference is a full run id, a unique prefix, or `last` (the most
recently written trace). Every query takes one, `runs` takes none and `diff`
takes two. Events are addressed as `eN` and frames as `fN`, and those ids are
stable, so an answer from one command is a runnable argument to the next:
`--fn NAME`, in both `grep` and `frame`, matches a qualname **exactly
first**, then falls back to substring over the trace's distinct qualnames,
one substring hit is used as if it had been named exactly, more than one is
an ambiguous call, refused with every candidate listed rather than guessed
among. `frame --fn NAME --nth N` picks among repeated activations and says
how many there are when `N` is out of range, and `flow --object` takes
either `e<id>:<name>` (any name captured at that event) or
`<qualname>:<name>`, which resolves to that function's **first CALL** and so
names one of its **arguments** (`<qualname>:return` follows the same
activation to what it handed back). A name that was not captured at the
event a spec resolves to is refused, with the names that *were* captured
there listed.
