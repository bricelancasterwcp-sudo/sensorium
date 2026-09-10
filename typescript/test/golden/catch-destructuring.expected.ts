import * as __srt from "RT";const __sfile=__srt.file("src/catch-destructuring.ts","/w/src/catch-destructuring.ts",[["fields",1,"function"]],"3cd89a9599e72d20916cc9958a32866e67f462bd1bacd358fa3b32a5d510dd2a");export function fields(): void {const __sf=__srt.call(__sfile,0);try{
  try {
    risky();
  } catch ({ message }) {__srt.handled(__sf,undefined,4,"catch_escaped");
    report(message);
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
