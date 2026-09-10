import * as __srt from "RT";const __sfile=__srt.file("src/catch-no-binding.ts","/w/src/catch-no-binding.ts",[["quiet",1,"function"]],"f615d1b76fb3dcca45f9faf66f24f982b93d1a6411e6ceb691e92c3008900d08");export function quiet(): void {const __sf=__srt.call(__sfile,0);try{
  try {
    risky();
  } catch(__sce) {__srt.handled(__sf,__sce,4,"catch");
    report("failed");
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
