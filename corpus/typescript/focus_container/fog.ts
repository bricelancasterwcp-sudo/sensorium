// Seeded bug: `render` draws the density it was handed instead of the one
// `compute` clamps, so a reading above the ceiling is drawn unclamped and the
// two methods of one class disagree about the same input. They are also the
// two the focus is asked for BY THEIR CLASS -- one name, both methods, and
// neither of them named a second time.
export class Fog {
  ceiling = 10;

  compute(raw: number): number {
    const clamped = Math.min(raw, this.ceiling);
    return clamped;
  }

  render(raw: number): string {
    const density = raw;        // BUG: the raw reading, not the clamped one
    return `fog(${density})`;
  }
}
