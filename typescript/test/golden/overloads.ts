export function pick(value: string): string;
export function pick(value: number): number;
export function pick(value: string | number): string | number {
  return value;
}

declare function ambient(value: string): void;

export abstract class Shape {
  abstract area(): number;

  describeArea(): string {
    return String(this.area());
  }
}
