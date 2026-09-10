import * as __srt from "RT";const __sfile=__srt.file("src/callback-spread.ts","/w/src/callback-spread.ts",[["forwarded",1,"function"],["named",5,"function"],["named.<anonymous>",6,"function"]],"b9bdee6ca5451895a250973be40f8088fe10b0552f2d6aabc8515923536de74b");export function forwarded(args: [(e: unknown) => void]): Promise<void> {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(risky().catch(...args)));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function named(): Promise<void> {const __sf=__srt.call(__sfile,1);try{
  return __srt.ret(__sf,(risky().catch(__srt.catchCb(__sf,6,"catch_callback",((err) => {const __sf=__srt.call(__sfile,2);try{
    console.error(err);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}})))));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
