// The vitest setup file: the harness's own names, on the runtime's terms.
// Two copies of this text exist and exactly one line differs between them — the
// runtime's import specifier. `src/setup.mjs` is the template the driver writes
// out with the package placeholder resolved; `probes/setup.mjs` is the same text
// with the in-tree relative path, so the probes run with no driver at all.
// `test/setup.test.mjs` holds the two to that single difference.
import { beforeEach, expect } from 'vitest';
import * as rt from '__PKG__/src/rt.mjs';
rt.nameProvider(() => expect.getState().currentTestName ?? null);
rt.fileStart(expect.getState().testPath ?? null, expect.getState().environment ?? null);
beforeEach(() => { rt.seen(expect.getState().currentTestName ?? null); });
