// The measured `util.inspect` table, written by the recorder itself.
//
// `inspect-table.json` is a MEASUREMENT, not a guess: every row's text is what
// `dbg()` -- the one function that writes every capture this recorder puts on
// the wire -- produced for that value under this Node. So the fixture cannot
// drift from the recorder's own `INSPECT` options (module-private in
// `src/dbg.mjs`) or from its 200-byte wire cap: both are exercised by calling
// `dbg` rather than by restating what it does.
//
// `tests/test_js_inspect.py` reads the committed file and holds the Python
// reader (`query/js_inspect.py`) to it. Regenerate with:
//
//     node typescript/test/fixtures/gen-inspect-table.mjs
//
// and commit the result; a row that moves is a measurement that moved.
//
// ROW SHAPE
// ---------
//   {"literal": <the value, as JSON>, "text": <dbg(v).v>, "trunc": <dbg(v).trunc>}
//
// Most values are their own JSON. The ones JSON cannot spell carry a one-key
// marker object instead, and the reader on the Python side knows the six:
//
//   {"bigint": "123"}   {"undefined": true}   {"nan": true}
//   {"inf": 1 | -1}     {"negzero": true}     {"opaque": "<label>"}
//
// `opaque` is a value with no literal at all -- a function, a class, a Map, a
// Date -- kept in the table because what the READER must do with such a text
// (hand it back as text, never as a value) is exactly what those rows pin.
// The array and object rows are ordinary JSON and are read the same way; no
// literal object in this table uses one of the six marker names as a key.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { dbg } from '../../src/dbg.mjs';

class Foo {
  constructor() {
    this.x = 1;
  }
}

/** @param {number} a */
function foo(a) {
  return a;
}

/** C0, DEL and one C1 character: every class node spells `\xHH`. */
const CONTROLS = 'a\u0000b\u001Bc\u007Fd\u0085e';

/** @type {{literal: unknown, value: unknown}[]} */
const CASES = [
  // strings: the three quote choices, the escapes, non-ASCII, empty, and one
  // past `maxStringLength` (100) so inspect's own tail is measured
  { literal: 'abc', value: 'abc' },
  { literal: "it's", value: "it's" },
  { literal: 'it\'s "x"', value: 'it\'s "x"' },
  { literal: 'a\nb\tc\\d', value: 'a\nb\tc\\d' },
  { literal: 'café', value: 'café' },
  { literal: '', value: '' },
  { literal: 'x'.repeat(150), value: 'x'.repeat(150) },
  // the bare words
  { literal: { undefined: true }, value: undefined },
  { literal: null, value: null },
  { literal: true, value: true },
  { literal: false, value: false },
  // every number spelling `Number::toString` can produce
  { literal: 5, value: 5 },
  { literal: -5, value: -5 },
  { literal: 2.5, value: 2.5 },
  { literal: 1e21, value: 1e21 },
  { literal: 1e-7, value: 1e-7 },
  { literal: { negzero: true }, value: -0 },
  { literal: 0.000001, value: 0.000001 },
  { literal: 123456789.123, value: 123456789.123 },
  { literal: 1.5e300, value: 1.5e300 },
  { literal: 5e-324, value: 5e-324 },
  { literal: { nan: true }, value: NaN },
  { literal: { inf: 1 }, value: Infinity },
  { literal: { inf: -1 }, value: -Infinity },
  { literal: { bigint: '123' }, value: 123n },
  // and the values a text can only stand for
  { literal: [1, 2], value: [1, 2] },
  { literal: {}, value: {} },
  { literal: { a: 1, b: 'x' }, value: { a: 1, b: 'x' } },
  { literal: { opaque: 'function' }, value: foo },
  { literal: { opaque: 'class' }, value: Foo },
  { literal: { opaque: 'Map' }, value: new Map([['a', 1]]) },
  { literal: { opaque: 'Date' }, value: new Date(0) },
  {
    literal: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    value: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
  },
  // The escape table, measured rather than assumed -- three rows beyond the
  // design's own list, because the two sides of a `flow --value` comparison
  // must agree character for character and this is where they could differ
  // silently. `\v` is the row that matters: node names `\n \t \r \b \f` and
  // spells the vertical tab `\x0B`, so a writer that emitted `\v` would spell
  // a string this recorder never writes and sight nothing.
  { literal: 'it\'s "x" `y`', value: 'it\'s "x" `y`' },
  { literal: 'a\bb\fc\vd', value: 'a\bb\fc\vd' },
  { literal: CONTROLS, value: CONTROLS },
];

const rows = CASES.map(({ literal, value }) => {
  const cap = dbg(value);
  if (cap.k !== 'dbg') throw new Error(`dbg refused to read ${String(literal)}`);
  return { literal, text: cap.v, trunc: cap.trunc };
});

const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'inspect-table.json');
fs.writeFileSync(out, `${JSON.stringify(rows, null, 2)}\n`);
process.stdout.write(`${out}: ${rows.length} rows\n`);
