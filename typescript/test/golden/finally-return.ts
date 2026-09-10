export function swallow(): string {
  try {
    throw new Error("gone");
  } finally {
    return "ok";
  }
}
