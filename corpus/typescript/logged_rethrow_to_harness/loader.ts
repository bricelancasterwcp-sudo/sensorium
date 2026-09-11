// Seeded bug: the test itself logs the failure and rethrows it, and the
// rethrow reaches the harness. One thrown object, two RAISE rows -- the
// origin at `load` and the rethrow inside the test's own callback -- and
// the shape is `rethrow_hop`'s journey read to its OTHER ending: rung 2's
// hop always stopped at a `catch` that returned, so the recorder never had
// to say where a rethrow that ESCAPES lands. This case is a red suite by
// design: the point is a rethrow whose journey ends PROPAGATED, with the
// `console.error` line sitting right next to the throw and answering
// nothing about identity.
export function load(): number {
  throw new Error('disk offline');
}
