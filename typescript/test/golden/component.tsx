import { useCallback } from "react";

export function Badge({ items }: { items: string[] }) {
  const onClick = useCallback(() => {
    report("click");
  }, []);
  return (
    <ul onClick={onClick}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}
