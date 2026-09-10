import * as __srt from "RT";const __sfile=__srt.file("src/finally-with-catch.ts","/w/src/finally-with-catch.ts",[["caught",1,"function"]],"9adc89732108aa7cd49a4a197918cf4e7f73b45376c91c107262a243ff6094a2");export function caught(): string {const __sf=__srt.call(__sfile,0);try{
  try {
    throw __srt.raise(__sf,(new Error("gone")),3);
  } catch (err) {__srt.handled(__sf,err,4,"catch");
    console.error(err);
  } finally {__srt.handledFinally(__sf,6);
    return __srt.ret(__sf,("ok"));
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
