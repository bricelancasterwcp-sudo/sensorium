import * as __srt from "RT";const __sfile=__srt.file("src/focus-block-scope.ts","/w/src/focus-block-scope.ts",[["pick",2,"function"]],"f2a235f269d00fe9528f0c5793ad7e409738f829f5fbf119e1891e54185df464");// focus: pick
export function pick(c: boolean): number {const __sf=__srt.call(__sfile,0,["c",c]);try{
  let out = 0;__srt.line(__sf,3,["out",out]);
  if (c) {
    const y = 1;__srt.line(__sf,5,["y",y]);
    out = y;__srt.line(__sf,6,["out",out]);
  };__srt.line(__sf,4,[],["y"]);
  out += 1;__srt.line(__sf,8,["out",out]);
  return __srt.ret(__sf,(out));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
