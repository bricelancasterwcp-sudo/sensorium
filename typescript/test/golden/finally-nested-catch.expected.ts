import * as __srt from "RT";const __sfile=__srt.file("src/finally-nested-catch.ts","/w/src/finally-nested-catch.ts",[["nested",1,"function"]],"59ecc93a073e7fef11557df257e658a1e167ba283236d5bda69b393a97be06eb");export function nested(): number {const __sf=__srt.call(__sfile,0);try{
  try {
    try {
      throw __srt.raise(__sf,(new Error("a")),4);
    } catch(__sce) {__srt.handled(__sf,__sce,5,"sink_empty_catch");}
    work();
  } catch(__sfe){__srt.mark(__sf,__sfe);throw __sfe}finally {__srt.handledFinally(__sf,7);
    return __srt.ret(__sf,(1));
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
