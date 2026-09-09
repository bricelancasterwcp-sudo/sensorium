import * as __srt from "RT";const __sfile=__srt.file("src/catch.ts","/w/src/catch.ts",[["parse",1,"function"],["ignore",9,"function"],["destructured",16,"function"],["sink",24,"function"],["sink.<anonymous>",25,"function"]],"a9ce1e256c3d1bacc013a209bc226613ab882288b8555f2ffa5ab01de64c228d");export function parse(text: string): unknown {const __sf=__srt.call(__sfile,0);try{
  try {
    return __srt.ret(__sf,(JSON.parse(text)));
  } catch (err) {__srt.handled(__sf,err,4,"catch");
    return __srt.ret(__sf,(null));
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function ignore(): void {const __sf=__srt.call(__sfile,1);try{
  try {
    risky();
  } catch(__sce) {__srt.handled(__sf,__sce,12,"sink_empty_catch");
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function destructured(): void {const __sf=__srt.call(__sfile,2);try{
  try {
    risky();
  } catch ({ message }) {__srt.handled(__sf,undefined,19,"catch");
    report(message);
  }
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function sink(): Promise<void> {const __sf=__srt.call(__sfile,3);try{
  return __srt.ret(__sf,(risky().catch(__srt.emptyCatch(__sf,25,() => {const __sf=__srt.call(__sfile,4);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}))));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

try {
  risky();
} catch (err) {__srt.handled(null,err,30,"catch");
  report(err);
}
