import * as __srt from "RT";const __sfile=__srt.file("src/focus-loop.ts","/w/src/focus-loop.ts",[["sum",2,"function"]],"fbbf6d6bc05d6ad09eff860a4bfb394e1ca628b736190c32d6a90a309c5a1966");// focus: sum
export function sum(xs: number[]): number {const __sf=__srt.call(__sfile,0,["xs",xs]);try{
  let total = 0;__srt.line(__sf,3,["total",total]);
  for (const v of xs) {__srt.line(__sf,4,["v",v]);
    total += v;__srt.line(__sf,5,["total",total]);
  };__srt.line(__sf,4,[],["v"]);
  return __srt.ret(__sf,(total));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
