// E4's twentieth shape: a JSX-returning component, in the `.tsx` sibling that
// forces the transform's TSX parse mode. There is no React here on purpose —
// the probe project's dependencies are vitest, jsdom and TypeScript, and the
// question is whether a JSX function keeps its line, not whether React renders.
// `tsconfig.json` points the classic JSX factory at `h`, three lines down.

type Node = { tag: string; props: Record<string, unknown> };

function h(tag: string, props: Record<string, unknown> | null): Node {
  return { tag, props: props ?? {} };
}

// SITE S19Component
export function S19Component(props: { n: number }): Node {
  return <div data-n={props.n} />;
}
