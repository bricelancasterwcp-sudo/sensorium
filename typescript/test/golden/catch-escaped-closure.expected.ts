import * as __srt from "RT";const __sfile=__srt.file("src/catch-escaped-closure.ts","/w/src/catch-escaped-closure.ts",[["later",1,"function"],["later.<anonymous>",5,"function"]],"28459473a8cec3f1b42cbf7ba73cac5a05d7cb026c1293d85c8a18c4a727e1da");export function later(): void {const __sf=__srt.call(__sfile,0);try{
  try {
    risky();
  } catch (err) {__srt.handled(__sf,err,4,"catch_escaped");
    queueMicrotask(() => {const __sf=__srt.call(__sfile,1);try{return __srt.ret(__sf,(console.error(err)))}catch(__se){__srt.thr(__sf,__se);throw __se}});
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
