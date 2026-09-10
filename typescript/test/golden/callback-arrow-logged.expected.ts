import * as __srt from "RT";const __sfile=__srt.file("src/callback-arrow-logged.ts","/w/src/callback-arrow-logged.ts",[["warned",1,"function"],["warned.<anonymous>",2,"function"]],"7f4b1d62c352c991a801a888856eaa4a43eecf0b91b36bc343ebaecb7274ab6a");export function warned(): Promise<void> {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(risky().catch(__srt.catchCb(__sf,2,"catch_callback",((err) => {const __sf=__srt.call(__sfile,1);try{
    console.warn(err);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}})))));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
