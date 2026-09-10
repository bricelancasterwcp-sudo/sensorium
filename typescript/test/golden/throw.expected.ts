import * as __srt from "RT";const __sfile=__srt.file("src/throw.ts","/w/src/throw.ts",[["guard",1,"function"]],"298f7dc22c9c1cae5452bde2772851e6f2a9955c3fd262899ba905bb3a9ff81f");export function guard(n: number): number {const __sf=__srt.call(__sfile,0);try{
  if (n < 0) throw __srt.raise(__sf,(new RangeError("neg")),2);
  return __srt.ret(__sf,(n));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

if (typeof globalThis === "undefined") throw __srt.raise(null,(new Error("no global")),6);
