import * as __srt from "RT";const __sfile=__srt.file("src/catch-escaped-expect.ts","/w/src/catch-escaped-expect.ts",[["assertFails",1,"function"]],"bbad0982bd9830ceec028b7f3e58d236198deb742f2ee0ee2a68316f24b5bfcb");export function assertFails(): void {const __sf=__srt.call(__sfile,0);try{
  try {
    risky();
  } catch (err) {__srt.handled(__sf,err,4,"catch_escaped");
    expect((err as Error).message).toBe("nope");
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
