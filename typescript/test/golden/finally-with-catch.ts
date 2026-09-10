export function caught(): string {
  try {
    throw new Error("gone");
  } catch (err) {
    console.error(err);
  } finally {
    return "ok";
  }
}
