import { describe, it, test } from "vitest";

const sharedCase = () => {};

describe("shared", () => {
  test("identifier callback", sharedCase);

  it.each(table)("row %s", sharedCase);
});
