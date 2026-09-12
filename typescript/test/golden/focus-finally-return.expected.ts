import * as __srt from "RT";const __sfile=__srt.file("src/focus-finally-return.ts","/w/src/focus-finally-return.ts",[["settle",2,"function"],["note",13,"function"]],"772e9a70cd2a67cc548de609d2647aa4ee89cb557558587eb51ec2f9890a024d");// focus: settle
export function settle(flag: boolean): number {const __sf=__srt.call(__sfile,0,["flag",flag]);try{
  let cleanup = 0;__srt.line(__sf,3,["cleanup",cleanup]);
  try {
    if (flag) {return __srt.pend(__sf,(1));}__srt.line(__sf,5,[]);
    return __srt.pend(__sf,(2));
  } finally {
    cleanup = 1;__srt.line(__sf,8,["cleanup",cleanup]);
    note(cleanup);__srt.line(__sf,9,[]);
  };__srt.line(__sf,4,[]);
;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}

export function note(n: number): number {const __sf=__srt.call(__sfile,1);try{
  return __srt.ret(__sf,(n));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
