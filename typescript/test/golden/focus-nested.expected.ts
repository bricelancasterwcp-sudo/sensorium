import * as __srt from "RT";const __sfile=__srt.file("src/focus-nested.ts","/w/src/focus-nested.ts",[["outer",2,"function"],["outer.f",3,"function"]],"d27efe3b0b594586d296ca0114c39e5a75cd80fad601b05812eb2f4a0b1602bb");// focus: outer
export function outer(): number {const __sf=__srt.call(__sfile,0,[]);try{
  const f = (n: number): number => {const __sf=__srt.call(__sfile,1,["n",n]);try{
    const m = n * 2;__srt.line(__sf,4,["m",m]);
    return __srt.ret(__sf,(m));
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}};__srt.line(__sf,3,["f",f]);
  return __srt.ret(__sf,(f(1)));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
