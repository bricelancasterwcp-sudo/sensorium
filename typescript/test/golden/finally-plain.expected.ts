import * as __srt from "RT";const __sfile=__srt.file("src/finally-plain.ts","/w/src/finally-plain.ts",[["cleanupOnly",1,"function"]],"a45cfde511ee61e35f394de799eb8e145d55eb50c90192fd0f6bb0554343840d");export function cleanupOnly(): void {const __sf=__srt.call(__sfile,0);try{
  try {
    risky();
  } finally {
    cleanup();
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

for (const item of items) {
  try {
    risky();
  } finally {
    break;
  }
}
