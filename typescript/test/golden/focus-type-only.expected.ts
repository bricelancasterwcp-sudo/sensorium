import * as __srt from "RT";const __sfile=__srt.file("src/focus-type-only.ts","/w/src/focus-type-only.ts",[["shapes",2,"function"]],"fc0f4b44dd5243a73a42dfc231601cd42429cb4e1b16a9d6150429e2d2c7534b");// focus: shapes
export function shapes(n: number): number {const __sf=__srt.call(__sfile,0,["n",n]);try{
  interface Point { x: number }
  type Pair = [number, number];
  enum Colour { Red = 1 };__srt.line(__sf,5,[]);
  declare const later: number;
  const p: Point = { x: n };__srt.line(__sf,7,["p",p]);
  const q: Pair = [n, later];__srt.line(__sf,8,["q",q]);
  return __srt.ret(__sf,(p.x + q[0] + Colour.Red));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
