import * as __srt from "RT";const __sfile=__srt.file("src/then-spread.ts","/w/src/then-spread.ts",[["forwarded",1,"function"],["forwarded.<anonymous>",2,"function"],["leading",5,"function"],["leading.<anonymous>",6,"function"]],"5b84543a59ad21a5282c24e836fb69bdc3551c0bf1086a8f40c39ae1ba485903");export function forwarded(rest: [(e: unknown) => void]): Promise<string> {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(risky().then((value) => {const __sf=__srt.call(__sfile,1);try{return __srt.ret(__sf,(String(value)))}catch(__se){__srt.thr(__sf,__se);throw __se}}, ...rest)));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function leading(rest: [(v: string) => string]): Promise<string> {const __sf=__srt.call(__sfile,2);try{
  return __srt.ret(__sf,(risky().then(...rest, (err) => {const __sf=__srt.call(__sfile,3);try{return __srt.ret(__sf,(String(err)))}catch(__se){__srt.thr(__sf,__se);throw __se}})));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
