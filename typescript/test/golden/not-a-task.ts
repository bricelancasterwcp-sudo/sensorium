// A local `describe` helper, and a test whose callback is not written inline:
// neither is a task boundary, and neither is rewritten.
function describe(label: string, formula: string, value: number): string {
  return `${label}: ${formula} = ${value}`;
}

const summary = describe("attack", "1d20", 12);

test("shared", sharedCase);

it.each(table)("shared %s", sharedCase);
