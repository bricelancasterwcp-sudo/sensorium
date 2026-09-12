import * as __srt from "RT";const __sfile=__srt.file("src/focus-destructure.ts","/w/src/focus-destructure.ts",[["take",2,"function"]],"f8b474dfd825aae0a1944342a80de9c7417e14562a563ca77ed85584859f5b37");// focus: take
export function take(o: any, ...rest: number[]): number {const __sf=__srt.call(__sfile,0,["o",o,"rest",rest]);try{
  const { a, b: [c] = [0], ...r } = o;__srt.line(__sf,3,["a",a,"c",c,"r",r]);
  let x;__srt.line(__sf,4,["x",x]);
  x = a + c + rest.length;__srt.line(__sf,5,["x",x]);
  return __srt.ret(__sf,(x + Object.keys(r).length));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
