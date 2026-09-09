import { vi } from "vitest";

vi.mock("./api", () => ({
  fetchUser: vi.fn(() => Promise.resolve({ id: 1 })),
}));

const seed = vi.hoisted(() => {
  return 7;
});

export function useSeed(): number {
  return seed;
}
