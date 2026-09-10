export class Fog extends Layer {
  private density = 0;
  readonly onTick = (dt: number) => {
    this.density += dt;
  };

  constructor(density: number) {
    super();
    this.density = density;
  }

  get radius(): number {
    return this.density * 2;
  }

  set radius(value: number) {
    this.density = value / 2;
  }

  static make(): Fog {
    return new Fog(0);
  }
}
