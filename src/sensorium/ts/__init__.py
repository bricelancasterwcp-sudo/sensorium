"""Reading what the TypeScript recorder wrote.

The recorder itself is `typescript/` -- a transform, a runtime and the
harness wiring, all of it JavaScript. What it leaves behind is a directory
of JSONL spools, one per container, plus the driver's own record of the
invocation. This package is the other half: `spool` reads the wire,
`ingest` writes format-4 traces through the store's own `TraceWriter` so
the schema has exactly one home, and `cli` is the `sensorium ts`
subcommand.
"""
