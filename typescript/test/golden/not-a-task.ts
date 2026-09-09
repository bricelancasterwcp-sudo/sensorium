// Ordinary source: `describe` here is the consumer's own helper, and nothing in
// this file is a task, whatever shape the second argument takes.
function describe(label: string, formula: string, value: number): string {
  return `${label}: ${formula} = ${value}`;
}

const summary = describe("attack", "1d20", 12);

const mapped = describe("x", () => 1, 2);

test("shared", sharedCase);

it.each(table)("shared %s", sharedCase);
