import * as __srt from "RT";const __sfile=__srt.file("src/callback-arrow-escaped.ts","/w/src/callback-arrow-escaped.ts",[["collect",1,"function"],["collect.<anonymous>",2,"function"]],"a905c2a5f7f1ee506579aa63fe5464dbdc1e12c6cc4a9933cf7b3c7276c2f417");export function collect(seen: unknown[]): Promise<void> {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(risky().catch(__srt.catchCb(__sf,2,"catch_callback_escaped",((err) => {const __sf=__srt.call(__sfile,1);try{
    seen.push(err);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}})))));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
