import * as __srt from "RT";const __sfile=__srt.file("src/catch-escaped-return.ts","/w/src/catch-escaped-return.ts",[["reason",1,"function"]],"d649c66eb6e8f0bd24b7862441f7ca72495b3bfa16b11c3536214e5e1591ada2");export function reason(): string {const __sf=__srt.call(__sfile,0);try{
  try {
    risky();
  } catch (err) {__srt.handled(__sf,err,4,"catch_escaped");
    return __srt.ret(__sf,(String(err)));
  }
  return __srt.ret(__sf,(""));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
