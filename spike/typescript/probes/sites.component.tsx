// THROWAWAY E4 site probe, the TSX sibling.
import React from 'react';

// SITE S19Component
export function S19Component(props: { n: number }): React.ReactElement {
  return <div data-n={props.n}>{props.n}</div>;
}
