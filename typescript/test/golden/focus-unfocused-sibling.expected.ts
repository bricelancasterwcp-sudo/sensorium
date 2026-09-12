import * as __srt from "RT";const __sfile=__srt.file("src/focus-unfocused-sibling.ts","/w/src/focus-unfocused-sibling.ts",[["watched",2,"function"],["ignored",7,"function"]],"9d4d87c82ee9cc16880e2d9ccfd2933409e111bbe79761e7bacd44c53048cbb0");// focus: watched
export function watched(a: number): number {const __sf=__srt.call(__sfile,0,["a",a]);try{
  const b = a + 1;__srt.line(__sf,3,["b",b]);
  return __srt.ret(__sf,(b));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function ignored(a: number): number {const __sf=__srt.call(__sfile,1);try{
  const b = a + 1;
  return __srt.ret(__sf,(b));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
