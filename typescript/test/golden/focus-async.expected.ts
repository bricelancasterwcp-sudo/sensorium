import * as __srt from "RT";const __sfile=__srt.file("src/focus-async.ts","/w/src/focus-async.ts",[["load",2,"coroutine"]],"7756c5577d8f78cb67eb8287759058004d7f860e3b0751fba133a20d2289c408");// focus: load
export async function load(p: Promise<number>, q: Promise<void>): Promise<number> {const __sf=__srt.call(__sfile,0,["p",p,"q",q]);try{
  const a = __srt.r(__sf,await __srt.y(__sf,(p),0));__srt.line(__sf,3,["a",a]);
  __srt.r(__sf,await __srt.y(__sf,(q),0));__srt.line(__sf,4,[]);
  const b = a + 1;__srt.line(__sf,5,["b",b]);
  return __srt.ret(__sf,(b));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
