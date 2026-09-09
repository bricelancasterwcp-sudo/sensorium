export async function load(url: string): Promise<string> {
  const res = await fetch(url);
  return await res.text();
}

export const boot = async () => await load("/x");
