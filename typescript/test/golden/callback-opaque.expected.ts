import * as __srt from "RT";const __sfile=__srt.file("src/callback-opaque.ts","/w/src/callback-opaque.ts",[["delegated",1,"function"]],"27db11d0372be8f2b7a5059af5c9e1c0b213e980bbc467180013dedf219b32ac");export function delegated(handler: (e: unknown) => void): Promise<void> {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(risky().catch(__srt.catchCb(__sf,2,"catch_callback_opaque",(handler)))));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
