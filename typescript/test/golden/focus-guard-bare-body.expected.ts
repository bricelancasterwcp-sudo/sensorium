import * as __srt from "RT";const __sfile=__srt.file("src/focus-guard-bare-body.ts","/w/src/focus-guard-bare-body.ts",[["probe",2,"function"]],"b034c2f3e86352991cd2bc7b1688bfb00c424e9fafcc979c3614aac35dcefe2e");// focus: probe
export function probe(n: number): number {const __sf=__srt.call(__sfile,0,["n",n]);try{
  let x = 0;__srt.line(__sf,3,["x",x]);
  let count = 0;__srt.line(__sf,4,["count",count]);
  let m = n;__srt.line(__sf,5,["m",m]);
  if ((x = n)) {__srt.line(__sf,6,["x",x]);x = 2;__srt.line(__sf,6,["x",x]);}__srt.line(__sf,6,["x",x]);
  while ((m = m - 1) > 0) {__srt.line(__sf,7,["m",m]);count += 1;__srt.line(__sf,7,["count",count]);}__srt.line(__sf,7,["m",m]);
  return __srt.ret(__sf,(x + count));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
