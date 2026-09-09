import * as __srt from "RT";const __sfile=__srt.file("src/await.ts","/w/src/await.ts",[["load",1,"coroutine"],["boot",6,"coroutine"]],"8633909100e82fd911a32c86c03361cab09d2fed5a65c53d039ff135d669a255");export async function load(url: string): Promise<string> {const __sf=__srt.call(__sfile,0);try{
  const res = __srt.r(__sf,await __srt.y(__sf,(fetch(url)),0));
  return __srt.ret(__sf,(__srt.r(__sf,await __srt.y(__sf,(res.text()),0))));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export const boot = async () => {const __sf=__srt.call(__sfile,1);try{return __srt.ret(__sf,(__srt.r(__sf,await __srt.y(__sf,(load("/x")),0))))}catch(__se){__srt.thr(__sf,__se);throw __se}};
