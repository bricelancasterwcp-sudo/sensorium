import * as __srt from "RT";const __sfile=__srt.file("src/yield.ts","/w/src/yield.ts",[["counter",1,"generator"],["stream",7,"async_generator"]],"2957dbb7853a7943f99f1954d2afea0bd77f59432d13ace2a9d2b6acd4ad2e98");export function* counter(): Generator<number> {const __sf=__srt.call(__sfile,0);try{
  __srt.r(__sf,yield __srt.y(__sf,(1),1));
  __srt.r(__sf,yield __srt.y(__sf,(undefined),1));
  __srt.r(__sf,yield* __srt.y(__sf,(inner()),1));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.gclose(__sf)}}

export async function* stream(): AsyncGenerator<number> {const __sf=__srt.call(__sfile,1);try{
  __srt.r(__sf,yield __srt.y(__sf,(__srt.r(__sf,await __srt.y(__sf,(next()),0))),1));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.gclose(__sf)}}
