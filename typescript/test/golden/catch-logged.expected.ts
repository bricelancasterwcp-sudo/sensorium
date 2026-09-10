import * as __srt from "RT";const __sfile=__srt.file("src/catch-logged.ts","/w/src/catch-logged.ts",[["load",1,"function"],["rendered",10,"function"]],"f047bd9e7b7991997e5757086578fe1b57400ae177a6b1ea55115974b9e6a80d");export function load(text: string): unknown {const __sf=__srt.call(__sfile,0);try{
  try {
    return __srt.ret(__sf,(JSON.parse(text)));
  } catch (err) {__srt.handled(__sf,err,4,"catch");
    console.error("load failed", err);
  }
  return __srt.ret(__sf,(null));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function rendered(): void {const __sf=__srt.call(__sfile,1);try{
  try {
    risky();
  } catch (err) {__srt.handled(__sf,err,13,"catch");
    console.warn(`risky failed: ${String(err)}`);
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
