import * as __srt from "RT";const __sfile=__srt.file("src/class.ts","/w/src/class.ts",[["Fog.onTick",3,"function"],["Fog.constructor",7,"function"],["Fog.radius",12,"function"],["Fog.radius",16,"function"],["Fog.make",20,"function"]],"d16153d1aab78a7a203133322f63efd6400a10efd5d52f283238d0b7196ca7c4");export class Fog extends Layer {
  private density = 0;
  readonly onTick = (dt: number) => {const __sf=__srt.call(__sfile,0);try{
    this.density += dt;
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}};

  constructor(density: number) {const __sf=__srt.call(__sfile,1);try{
    super();
    this.density = density;
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

  get radius(): number {const __sf=__srt.call(__sfile,2);try{
    return __srt.ret(__sf,(this.density * 2));
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

  set radius(value: number) {const __sf=__srt.call(__sfile,3);try{
    this.density = value / 2;
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

  static make(): Fog {const __sf=__srt.call(__sfile,4);try{
    return __srt.ret(__sf,(new Fog(0)));
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
}
