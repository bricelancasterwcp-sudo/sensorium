import * as __srt from "RT";const __sfile=__srt.file("src/finally-return.ts","/w/src/finally-return.ts",[["swallow",1,"function"]],"e935fb7c3a48a5c1e1a0d5a23c45334f2cc46226b7322b3da2ebe5732112ff00");export function swallow(): string {const __sf=__srt.call(__sfile,0);try{
  try {
    throw __srt.raise(__sf,(new Error("gone")),3);
  } catch(__sfe){__srt.mark(__sf,__sfe);throw __sfe}finally {__srt.handledFinally(__sf,4);
    return __srt.ret(__sf,("ok"));
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
